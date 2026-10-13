"""Observed coordinator timing; never infer model compute time from segment latency."""
import time
from pathlib import Path
from runtime import full_live

def metrics(task,segments,batches,now=None):
    from runtime.store import interval_ms
    from runtime.live_review import ACTIVE
    now=time.time() if now is None else now
    dispatch_v2 = task.get('review_dispatch_version') == 2
    active=[b for b in batches if b['status'] in ACTIVE and (dispatch_v2 or b.get('executor') == 'main')]
    occupied={int(s) for b in active for s in b['targets']}
    ready=[s for s in segments if s['review_status']=='pending' and full_live.ready(task,s)]
    waiting=[s for s in ready if s['id'] not in occupied]
    recent=[s for s in segments if 'speech_review_completed_at' in s and now-300 <= s['speech_review_completed_at'] <= now]
    completed=interval_ms(recent)
    minute_buckets=[{'from_seconds_ago':n*60,'to_seconds_ago':(n-1)*60,
        'completed_media_ms':interval_ms([s for s in recent if now-n*60 < s['speech_review_completed_at'] <= now-(n-1)*60])} for n in range(5,0,-1)]
    backlog=interval_ms(ready)
    samples=task.get('review_dispatch',{}).get('backlog_samples',[])
    baseline=next((s for s in samples if now-306<=s['at']<now),None)
    change=backlog-baseline['ms'] if baseline else None
    dispatch=task.get('review_dispatch',{})
    closed=task.get('finishing',{}).get('phase')=='completed'
    activity = max([v for v in (dispatch.get('heartbeat_at'), dispatch.get('last_review_attempt_at'),
                               dispatch.get('last_review_success_at')) if isinstance(v, (int, float))] or [0])
    progress = max([v for v in (dispatch.get('last_review_success_at'), dispatch.get('progress_baseline_at'))
                    if isinstance(v, (int, float))] or
                   [min([s.get('asr_ready_at', s.get('review_started_at', now)) for s in ready] or [now])])
    # A new queue after an idle interval must not inherit an old success deadline.
    if ready:
        progress = max(progress, min(s.get('asr_ready_at', s.get('review_started_at', progress)) for s in ready))
    without_progress = max(0, now - progress) if ready else 0
    interrupted = bool(ready) and bool(activity) and now - activity > 180
    stalled = bool(ready) and without_progress >= 60
    # Conservation of ready media over the observed window: arrivals = completions + queue growth.
    # ponytail: use existing samples; report unknown until a full five-minute window is observed.
    window = [s for s in samples if now-306 <= s['at'] <= now]
    observed = (bool(baseline) and now - baseline['at'] >= 297 and bool(window)
                and now-window[-1]['at'] <= 6
                and all(b['at']-a['at'] <= 6 for a,b in zip(window,window[1:])))
    elapsed = now - baseline['at'] if observed else 0
    window_completed = interval_ms([s for s in segments if baseline['at'] < s.get('speech_review_completed_at',0) <= now]) if observed else 0
    arrival_rate = round(max(0, window_completed + change) / elapsed * .06, 2) if observed else None
    service_rate = round(window_completed / elapsed * .06, 2) if observed else None
    gap = round(max(0, arrival_rate - service_rate), 2) if observed else None
    unknown_work = (interrupted or (stalled and not window_completed) or dispatch.get('reconcile_required')
                    or any(b['status'] in {'dispatching','cancelling'} for b in active))
    ceiling = max(1, dispatch.get('worker_ceiling', 0))
    at_capacity = dispatch.get('slots', 1) >= ceiling
    capacity = ('unknown' if not observed or unknown_work else
                'insufficient' if ready and change > 0 and at_capacity else
                'catching_up' if ready and change < 0 else
                'growing' if ready and change > 0 else 'balanced')
    skipped=[s for s in segments if s.get('skip_code')=='finish_deadline']
    unresolved = [b for b in active if b.get('last_review_error')]
    last_error = max(unresolved, key=lambda b: b.get('validation_finished_at', 0))['last_review_error'] if unresolved else dispatch.get('last_review_error')
    return {'capacity_status':capacity, 'arrival_media_seconds_per_minute':arrival_rate,
            'service_media_seconds_per_minute':service_rate, 'capacity_gap_seconds_per_minute':gap,
            'unassigned_segments':len(waiting),'inflight_segments':len(occupied),
            'inflight_batches':len(active),'target_slots':dispatch.get('slots',1),
            'cancelling_batches':sum(b['status']=='cancelling' for b in active),
            'oldest_unassigned_wait_seconds':max([max(0,now-s.get('asr_ready_at',now)) for s in waiting]+[0]),
            'oldest_inflight_seconds':max([max(0,now-b['created_at']) for b in active]+[0]),
            'judgment_backlog_ms':backlog,
            'asr_backlog_ms':interval_ms([s for s in segments if s['review_status']!='skipped' and not full_live.ready(task,s)]),
            'completed_media_by_minute':minute_buckets,
            'batch_timings':[{k:b[k] for k in ('id','generation','status','created_at','dispatch_at','started_at','returned_at','validation_finished_at','submitted_at','completed_at','failures','validation_failures','error_counts') if k in b} for b in sorted(batches,key=lambda b:b['created_at'])[-20:]],
            'completed_media_ms_5m':completed,'completed_media_seconds_per_minute_5m':round(completed/5000,2),
            'backlog_change_ms_5m':change,'backlog_trend':'unknown' if change is None else 'growing' if change>0 else 'shrinking' if change<0 else 'stable',
            'execution_mode':'mixed' if any(b.get('executor')=='child' for b in active) and any(b.get('executor')=='main' for b in active) else 'child' if any(b.get('executor')=='child' for b in active) else 'main',
            'dispatch_preparation_state':dispatch.get('capability_state','unverified') if dispatch_v2 else 'not_required',
            'parallel_verified':dispatch.get('parallel_verified',False),
            'acceptance_state':dispatch.get('acceptance_state','parallel_unverified') if dispatch_v2 else 'serial',
            'stable_pair_rounds':dispatch.get('stable_pair_rounds',0),
            'serial_fallback_reason':dispatch.get('reduction_reason'),
            'last_review_submitted_at':max([b.get('submitted_at',0) for b in batches]+[0]) or None,
            'dispatcher_status':'launch_unknown' if any(b['status']=='dispatching' for b in active) else 'reconciling' if dispatch.get('reconcile_required') or any(b['status']=='cancelling' for b in active) else 'closed' if closed else 'interrupted' if interrupted else 'stalled' if stalled else 'active' if dispatch.get('owner') else 'not_started',
            'last_review_attempt_at':dispatch.get('last_review_attempt_at'),
            'seconds_since_review_attempt':max(0,now-dispatch['last_review_attempt_at']) if dispatch.get('last_review_attempt_at') is not None else None,
            'seconds_since_review_success':max(0,now-dispatch['last_review_success_at']) if dispatch.get('last_review_success_at') is not None else None,
            'review_validation_failures':sum(b.get('validation_failures',0) for b in batches),
            'last_review_error':last_error,
            'seconds_without_progress':without_progress,
            'finish_unreviewed_segments':len(skipped),'finish_unreviewed_ms':interval_ms(skipped),
            'delivery_message':f'已完成 {sum(s.get("speech_reviewed",False) for s in segments)} 段判定，结束未检 {len(skipped)} 段；结论仅适用于已判定范围。' if skipped else '以已判定范围为准；尚未结束时不能声明全场检测完成。'}

def record(store,payload,result=None,error=None):
    """One record per segment result; durations belong to the containing batch."""
    from runtime.live_review import initialize, row, save
    from runtime.review_errors import review_error
    now=time.time()
    with store.connection(True) as conn:
        initialize(conn)
        batch=row(conn,store.session_id,payload.get('batch_id'))
        if not batch or batch['generation']!=payload.get('generation'):return
        task=store._task(conn)
        dispatch=dict(task.get('review_dispatch',{}))
        dispatch['last_review_attempt_at']=now
        if error:
            detail=review_error(error,fallback=True,protocol_v2=True)
            batch['last_review_error']={k:detail[k] for k in ('code','field') if k in detail}
            dispatch['last_review_error']={k:detail[k] for k in ('code','field') if k in detail}
        elif result and result.get('status')=='saved':
            dispatch['last_review_success_at']=now
            dispatch.pop('last_review_error',None)
        task['review_dispatch']=dispatch
        store._set_task(conn,task)
        valid_host = batch.get('executor') != 'child' or (payload.get('host_task_id') == batch.get('host_task_id') and bool(batch.get('host_task_id')) and batch['status'] in {'running','returned'})
        if valid_host:
            batch.setdefault('returned_at',now)
        if batch['status']=='running' and valid_host:
            # A submitted result proves the worker returned, even if the host
            # omitted its separate returned acknowledgement.
            batch['status']='returned'
        batch['validation_finished_at']=now
        if error:
            detail=review_error(error,fallback=True,protocol_v2=True)
            batch['validation_failures']=batch.get('validation_failures',0)+1
            counts=batch.setdefault('error_counts',{});counts[detail['code']]=counts.get(detail['code'],0)+1
        elif result and result.get('status')=='saved':
            batch['submitted_at']=now
            segments={str(s['id']):s for s in store._segments_by_ids(
                conn,[int(sid) for sid in batch['targets']])}
            if all(segments[sid]['review_status']=='done' and segments[sid]['evidence_revision']==rev for sid,rev in batch['targets'].items()):
                batch.update(status='done',completed_at=now)
                batch.pop('last_review_error',None)
        save(conn,store.session_id,batch)


def record_attempt(store, *, context_id=None, input_path=None, error=None, count_error=True):
    """Attribute parse errors to exactly one active context or its bound input path."""
    from runtime.live_review import initialize, rows, save, ACTIVE
    now=time.time()
    with store.connection(True) as conn:
        initialize(conn)
        task=store._task(conn)
        dispatch=dict(task.get('review_dispatch',{}))
        dispatch['last_review_attempt_at']=now
        task['review_dispatch']=dispatch
        candidates=[]
        for candidate in rows(conn,store.session_id):
            if candidate['status'] not in ACTIVE:
                continue
            expected=candidate.get('input_path')
            context_matches=context_id is None or candidate.get('context_id')==context_id
            path_matches=input_path is None or (expected and Path(input_path).resolve()==Path(expected).resolve())
            if (context_id is not None or input_path is not None) and context_matches and path_matches:
                candidates.append(candidate)
        batch=candidates[0] if len(candidates)==1 else None
        if batch and error:
            # Never persist exception messages, user prose or transport values.
            safe={k:error[k] for k in ('code','field','line','column') if k in error}
            dispatch['last_review_error']=safe
            batch['last_review_error']=safe
            batch['validation_finished_at']=now
            if count_error:
                batch['validation_failures']=batch.get('validation_failures',0)+1
                counts=batch.setdefault('error_counts',{})
                counts[safe['code']]=counts.get(safe['code'],0)+1
            save(conn,store.session_id,batch)
        store._set_task(conn,task)
    return {'recorded':batch is not None}
