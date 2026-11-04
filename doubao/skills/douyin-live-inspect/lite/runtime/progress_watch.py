"""Persist progress checkpoints; recover absent workers, never duplicate live owners."""
import sqlite3
import time
import uuid
from datetime import datetime

START_SECONDS = 180
REPORT_SECONDS = 360
MAX_ATTEMPTS = 2


def enabled(task):
    return task.get('kind','live') == 'live' and task.get('inspection_policy') == 'lite_live_realtime_v2'


def created(task, now):
    try:return min(now, datetime.fromisoformat(task['created_at'].replace('Z','+00:00')).timestamp())
    except (KeyError,ValueError,TypeError):return now


def diagnostic(task, state, component, reason, outcome, now):
    """Fixed enums and stable IDs only; progress never includes media or raw errors."""
    key = '_progress_diagnostic' if component in {'startup_watch','runtime_watch'} else '_report_diagnostic'
    detail=dict(failure_component=component, failure_reason=reason, recovery_outcome=outcome,
        watchdog_stage=state['stage'], blocking_reason=state.get('blocking_reason','none'),
        recovery_action=state.get('action','await_host'), recovery_attempts=state.get('attempts',0),
        recovery_elapsed_ms=max(0,round((now-state.get('incident_at',now))*1000)))
    detail.update({k:state[k] for k in ('reviewed_segments','unresolved_segments','recap_input_code','json_line','json_column') if k in state})
    identity=f"{component}:{state.get('incident_at',now)}:{reason}:{outcome}:{state.get('attempts',0)}"
    if state.get('recap_input_code'):
        identity += f":{state['recap_input_code']}:{state.get('json_line','')}:{state.get('json_column','')}"
    detail['diagnostic_event_id']=str(uuid.uuid5(uuid.UUID(hex=task.get('task_id') or task['id']),identity))
    task[key]=detail


def startup(store, launch_worker=None):
    from runtime.platform_support import file_lock
    from runtime.stop_signal import read
    # One observer owns checking + reservation + spawn; the worker owns its own
    # lock. The persisted grace also fences a watcher crash after ambiguous spawn.
    try:
        with file_lock(store.root/'.progress-watch.lock',timeout=0):
            return _startup(store, launch_worker, file_lock, read)
    except (OSError,TimeoutError,sqlite3.Error):return store.task().get('progress_health',{})


def startup_stage(task, segments):
    from runtime.full_live import ready
    stage=('first_media' if not segments else 'first_transcript' if not any(s.get('subtitles') or ready(task,s) for s in segments)
           else 'first_review' if not any(s['review_status']=='done' for s in segments) else 'complete')
    pending=[s for s in segments if s['review_status'] not in {'done','skipped'}]
    if stage=='complete' and pending:
        stage='review_processing' if any(ready(task,s) for s in pending) else 'media_processing'
    component='runtime_watch' if stage in {'media_processing','review_processing','complete'} else 'startup_watch'
    # Upstream capture continuing is not progress toward the first transcript
    # or judgment. Only crossing that milestone renews its observation clock.
    signature=([stage,sum(s['review_status']=='done' for s in segments)] if stage=='review_processing'
               else [stage,sum(ready(task,s) for s in segments)] if stage=='media_processing' else stage)
    return stage, component, signature


def _startup(store, launch_worker, file_lock, read_stop):
    now=time.time();launch=False
    task = store.task()
    if (not enabled(task) or task.get('stop_requested') or read_stop(store.root)
            or task.get('media_frozen') or task.get('capture_status') in {'ended','stopped','failed'}
            or task.get('model_waiting') or task.get('worker_status') in {'setup_pending','preparing'}):
        return {}
    segments = store._read_with_retry(lambda conn: store._segments(conn))
    stage, _, signature = startup_stage(task, segments)
    old = task.get('progress_health', {})
    if (old.get('signature') == signature and old.get('stage') == stage
            and old.get('reviewed_segments') == sum(s['review_status']=='done' for s in segments)
            and old.get('unresolved_segments') == sum(s['review_status'] not in {'done','skipped'} for s in segments)
            and (stage == 'complete' or now-old.get('last_progress_at', 0) < START_SECONDS)):
        return old
    with store.connection(True,timeout=0) as conn:
        task=store._task(conn);segments=store._segments(conn)
        if (not enabled(task) or task.get('stop_requested') or read_stop(store.root)
                or task.get('media_frozen') or task.get('capture_status') in {'ended','stopped','failed'}
                or task.get('model_waiting') or task.get('worker_status') in {'setup_pending','preparing'}):
            return {}
        from runtime.full_live import ready
        stage, component, signature = startup_stage(task, segments)
        old=task.get('progress_health',{})
        state=dict(old) if old else dict(stage=stage,last_progress_at=now if component=='runtime_watch' else created(task,now),signature=signature,attempts=0,status='healthy')
        progress=bool(old) and (old['stage']!=stage or old['signature']!=signature)
        state['reviewed_segments']=sum(s['review_status']=='done' for s in segments)
        state['unresolved_segments']=sum(s['review_status'] not in {'done','skipped'} for s in segments)
        if progress:
            if old.get('status') in {'blocked','recovering'}:
                diagnostic(task,state,'runtime_watch' if old['stage'] in {'media_processing','review_processing'} else 'startup_watch','progress_recovered','success',now)
            state.update(stage=stage,last_progress_at=now,signature=signature,status='healthy',blocking_reason='none')
            state.pop('incident_at',None);state.pop('reported',None)
        state['next_action']='review-next' if stage in {'first_review','review_processing'} else 'status'
        if stage!='complete' and now-state['last_progress_at']>=START_SECONDS:
            state.setdefault('incident_at',now)
            state.update(status='blocked',blocking_reason=stage+'_stalled',action='await_host')
            # Known submitted recognition keeps its own deadline. Starting a new
            # worker cannot make a live remote query finish faster.
            remote_wait=any(s.get('asr_task_id') and s.get('asr_cloud_deadline_at',0)>now for s in segments)
            recent=now-task.get('worker_heartbeat',0)<30
            if stage not in {'first_review','review_processing'} and not remote_wait and not recent:
                if state['attempts']>=MAX_ATTEMPTS:
                    state['blocking_reason']='recovery_exhausted'
                elif now-state.get('last_attempt_at',0)<60:
                    state.update(status='recovering',action='restart_worker')
                else:
                    try:
                        with file_lock(store.root/'.worker.lock',timeout=0):
                            # All decisions and the reservation are in one DB
                            # transaction; the child will recheck stop intent.
                            state.update(status='recovering',action='restart_worker',
                                attempts=state['attempts']+1,last_attempt_at=now)
                            launch=True
                    except TimeoutError:state['blocking_reason']='worker_unresponsive'
                    except OSError:state['blocking_reason']='worker_lock_unavailable'
            reason='recovery_exhausted' if state['blocking_reason']=='recovery_exhausted' else 'progress_stalled'
            # Emit once per incident/recovery attempt, not once per status poll.
            marker=(reason,state['attempts'])
            if list(marker)!=state.get('reported'):
                diagnostic(task,state,component,reason,'failed' if reason=='recovery_exhausted' else 'pending',now)
                state['reported']=list(marker)
        task['progress_health']=state
        if task!=store._task(conn):store._set_task(conn,task)
    if launch:
        if read_stop(store.root) or store.task().get('stop_requested'):return state
        try:
            if launch_worker is None:
                from runtime.cli import launch as spawn
                launch_worker=lambda:spawn('worker',store)
            launch_worker()
        except Exception:
            with store.connection(True,timeout=0) as conn:
                task=store._task(conn);state=task['progress_health']
                state.update(status='blocked',blocking_reason='worker_launch_failed')
                diagnostic(task,state,component,'recovery_launch_failed','failed',now)
                store._set_task(conn,task)
    return state


def report(store):
    """Recompute the missing step from durable evidence/receipts on every entry.

    Never execute host AI work or acknowledge delivery from a background timer.
    """
    task=store.task()
    if not enabled(task):return {}
    status=store.status()
    if not (status['report_ready'] or status.get('report_blocked_reason')):return {}
    from runtime.report_completion import completion
    from runtime.recap import recap_report
    result=completion(store);recap=recap_report(store)
    stage=('complete' if result['workflow_complete'] else 'inspection_blocked' if status.get('report_blocked_reason')
           else 'delivery_pending' if recap.get('available') or recap.get('terminal_failure')
           else 'recap_blocked' if recap.get('recovery_blocked') or recap.get('status')=='blocked' else 'recap_generating' if recap.get('status')=='generating' else 'recap_pending')
    if stage=='delivery_pending' and task.get('delivery_mode')!='chat':
        from runtime.report_completion import exported
        for kind,artifact in (('quality','quality'),('recap','review')):
            if kind in result['pending_reports'] and not exported(store,recap.get('evidence_version'),{artifact}):
                stage=kind+'_export_pending';break
    blocked_reason={'NO_CAPTURED_CONTENT':'no_captured_content','NO_SPEECH':'no_speech',
                    'NO_USABLE_TRANSCRIPT':'no_transcript','NO_REVIEWED_CONTENT':'no_reviewed_content'}.get(status.get('report_blocked_reason') or (recap.get('code') if recap.get('status')=='blocked' else None),stage)
    action=result['completion_next_action']
    signature=[stage,blocked_reason,recap.get('evidence_version'),result['pending_reports'],task.get('recap',{}).get('attempts'),
               task.get('recap',{}).get('updated_at'),action,bool(status['report_ready']),recap.get('status')]
    now=time.time()
    old = task.get('report_checkpoint', {})
    if (old.get('signature') == signature and stage not in {'inspection_blocked', 'recap_blocked'}
            and (stage == 'complete' or now-old.get('last_progress_at', 0) < REPORT_SECONDS)):
        return old
    with store.connection(True,timeout=0) as conn:
        current=store._task(conn)
        # Do not commit a checkpoint computed before a concurrent submission/ack.
        if any(current.get(k)!=task.get(k) for k in ('recap','recap_recovery','report_deliveries')):return current.get('report_checkpoint',{})
        old=current.get('report_checkpoint',{})
        state=dict(old) if old else dict(last_progress_at=max(task.get('finishing',{}).get('completed_at',now), task.get('recap',{}).get('updated_at',0)),status='healthy',attempts=0)
        if old and old.get('signature')!=signature:
            if old.get('status')=='blocked':diagnostic(current,state,'report_watch','report_resumed','success',now)
            state.update(last_progress_at=now,status='healthy',blocking_reason='none')
            state.pop('incident_at',None)
            for key in ('recap_input_code','json_line','json_column','draft_stamp'):state.pop(key,None)
        state.update(stage=stage,signature=signature,next_action=action,delivery_next_action=result['delivery_next_action'],
            pending_reports=result['pending_reports'],workflow_complete=result['workflow_complete'],
            evidence_version=recap.get('evidence_version'))
        if stage in {'inspection_blocked','recap_blocked'} or (stage!='complete' and now-state['last_progress_at']>=REPORT_SECONDS):
            state.update(status='blocked',blocking_reason=blocked_reason,action='resume_report')
            first = not state.get('incident_at')
            if first:state['incident_at']=now
            previous_input = [state.get(k) for k in ('recap_input_code','json_line','json_column')]
            if stage == 'recap_generating':
                from runtime.recap_submission import read_submission, RecapInputError
                path = store.root / 'recap-result.json'
                try:
                    info = path.stat()
                    stamp = [info.st_mtime_ns, info.st_size]
                except OSError:
                    stamp = None
                if first or state.get('draft_stamp') != stamp:
                    for key in ('json_line','json_column'):state.pop(key,None)
                    try:
                        if not path.exists():
                            state['recap_input_code'] = 'RECAP_INPUT_REQUIRED'
                        else:
                            read_submission(path)
                            state['recap_input_code'] = 'RECAP_JSON_READY'
                    except RecapInputError as error:
                        state['recap_input_code'] = error.code
                        if error.line is not None:
                            state.update(json_line=error.line, json_column=error.column)
                    state['draft_stamp'] = stamp
            if first or previous_input != [state.get(k) for k in ('recap_input_code','json_line','json_column')]:
                diagnostic(current,state,'report_watch','report_blocked','pending',now)
        state['quality_ready']=bool(status['report_ready'])
        state['recap_status']=recap.get('status')
        current['report_checkpoint']=state
        if current!=store._task(conn):store._set_task(conn,current)
    return state


def observe(store, *, recover=True):
    """Optional diagnosis must not turn a valid report into a command failure."""
    result={}
    try:
        health=startup(store) if recover else store.task().get('progress_health',{})
        if health:result['progress_health']=health
        checkpoint=report(store)
        if checkpoint:result['report_checkpoint']=checkpoint
    except (OSError,ValueError,sqlite3.Error):pass
    return result
