"""Explicit state-transition rules registered by the Store mutation entry points."""
import copy
import json
from runtime.telemetry_keys import TASK
from runtime import task_telemetry as events
from runtime.telemetry_context import dimensions

def inspection_result(task, segments):
    from runtime.store import ASR_DONE, FRAME_DONE, capture_coverage
    capture_ended = task.get('capture_status') in {'ended', 'stopped', 'failed'}
    if task.get('kind','live')=='live' and task.get('finishing',{}).get('phase')=='draining':
        return None
    from runtime.realtime_policy import current
    if current(task) and task.get('media_frozen') and task.get('finishing', {}).get('phase') == 'completed':
        if task.get('stop_audit', {}).get('reason') == 'user_request' or task.get('stop_reason') == 'user_request':return 'completed'
        return 'partial' if any(s.get('review_status') == 'done' and s.get('review_result') for s in segments) else 'failed'
    if capture_ended and task.get('finishing', {}).get('phase') == 'completed' and any(s.get('review_status') == 'skipped' for s in segments):
        # Logical completion may precede worker cleanup; report the result once.
        return 'completed' if task.get('stop_requested') else 'partial'
    terminal = capture_ended and task.get('worker_status') in {'done', 'failed', 'stopped'}
    if not terminal:
        return None
    if task.get('stop_requested'):
        return 'completed'
    if task.get('worker_status') == 'stopped':
        return 'stopped'
    ready = bool(segments) and all(s.get('review_status')=='skipped' or (s.get('review_status') == 'done' and s.get('asr_status') in ASR_DONE and s.get('frame_status') in FRAME_DONE) for s in segments)
    if ready:
        coverage = capture_coverage(task, segments)
        gaps = not coverage['complete'] or bool(coverage['analysis_gaps']) or any(
            s.get('review_status')=='skipped' or s.get('asr_status') not in ('success', 'no_audio') or s.get('frame_status') != 'success'
            or any(r.get('status', r.get('result')) == 'insufficient' for r in s.get('review_result', {}).get('rules', [])) for s in segments)
        return 'partial' if gaps or task.get('capture_status') == 'failed' or task.get('worker_status') == 'failed' else 'completed'
    if not segments or task.get('worker_status') == 'failed':
        return 'failed'
    return None


# Only state that can change task outcome participates in completion checks.
TASK_STATE = {'capture_status', 'worker_status', 'stop_requested', 'finishing',
              'capture_start_ms', 'capture_end_ms', 'capture_spans', 'capture_active_span', 'capture_observed_ms'}
SEGMENT_STATE = {'review_status', 'asr_status', 'frame_status', 'review_result', 'skip_code'}

# Exclude only known control-plane fields, rather than maintaining an incomplete
# allowlist of report inputs. Unknown/new fields still invalidate the receipt.
VIDEO_TASK_CONTROL = {'server_pid', 'server_port', 'worker_pid', 'capture_pid'}
VIDEO_SEGMENT_CONTROL = {'claim_token', 'lease_until'}


def _report_changed(before, after, control_fields):
    before = before or {}
    return any(before.get(k) != after.get(k) for k in (before.keys() | after.keys()) - control_fields)


def _pending(connection):
    return connection.telemetry if events.enabled() else None


def _save_task(tx, task):
    # Metadata writes must bypass business mutation hooks and revision changes.
    tx.connection.execute('UPDATE live_sessions SET data=? WHERE id=?',
                          (json.dumps(task, ensure_ascii=False), tx.store.session_id))


def check_inspection_completion(store, connection):
    """Register before a relevant mutation; evaluate only its final committed state."""
    tx = _pending(connection)
    if tx is None or 'completion' in tx.baselines:
        return
    task = store._task(connection)
    if not task.get('_telemetry'):
        return
    tx.baselines['completion'] = inspection_result(task, store._segments(connection))
    tx.defer('completion', lambda: _finish_inspection(tx))


def _finish_inspection(tx):
    task = tx.store._task(tx.connection)
    record = task.get('_telemetry')
    if not record or record.get('task_finished_at'):
        return
    segments = tx.store._segments(tx.connection)
    result = inspection_result(task, segments)
    if result and not tx.baselines['completion']:
        # Freeze the final source state even when completion runs before dimension refresh.
        record["dimensions"] = dimensions(task, batch=bool(record.get("batch_directory")))
        payload = events.record_event(TASK.FINISHED, record, result)
        skipped = [s for s in segments if s.get('skip_code') == 'ASR_RETRY_EXHAUSTED' and s.get('review_status') == 'skipped']
        payload['extra'].update(asr_skipped_segments=len(skipped),
                               asr_skipped_ms=sum(s['end_ms']-s['start_ms'] for s in skipped))
        _save_task(tx, task)
        tx.events.append(payload)


def task_changing(store, connection, before, after):
    """Called by the common task-state writer, before the actual write."""
    try:
        tx = _pending(connection)
        if tx is None:
            return
        if before.get('_telemetry'):
            tx.defer('dimensions', lambda: _refresh_dimensions(tx))
        from runtime.telemetry_funnel import register
        if (any(before.get(k) != after.get(k) for k in TASK_STATE | {'media_frozen','report_deliveries','recap'})
                or (before.get('_funnel_video_receipt') and _report_changed(before, after, VIDEO_TASK_CONTROL))):
            register(tx)
        if any(before.get(k) != after.get(k) for k in TASK_STATE):
            check_inspection_completion(store, connection)
        if before.get('worker_status') != after.get('worker_status'):
            tx.baselines.setdefault('worker_status', before.get('worker_status'))
            tx.defer('resume', lambda: _resume_inspection(tx))
        if before.get('recap') != after.get('recap'):
            tx.baselines.setdefault('recap', copy.deepcopy(before.get('recap') or {}))
            tx.defer('recap', lambda: _recap_transition(tx))
    except Exception:
        pass  # Registering optional events cannot reject a business write.


def _resume_inspection(tx):
    task = tx.store._task(tx.connection)
    record = task.get('_telemetry')
    if (record and record.get('task_finished_at')
            and tx.baselines['worker_status'] in {'done', 'failed', 'stopped'}
            and task.get('worker_status') in {'preparing', 'pending', 'running'}):
        record['dimensions'] = dimensions(task, batch=bool(record.get('batch_directory')))
        tx.events.append(events.record_event(TASK.RESUMED, record))
        _save_task(tx, task)


def _recap_transition(tx):
    task = tx.store._task(tx.connection)
    old = tx.baselines['recap']
    recap = task.get('recap') or {}
    record = task.get('_recap_telemetry')
    if recap.get('status') == 'generating' and (old.get('status') != 'generating' or old.get('evidence_version') != recap.get('evidence_version')):
        if record and record.get('task_finished_at'):
            tx.events.append(events.record_event(TASK.RESUMED, record))
        elif not record:
            record = events.new_record('live_recap', parent=(task.get('_telemetry') or {}).get('telemetry_task_id'))
            record['dimensions'] = dimensions(task)
            task['_recap_telemetry'] = record
            tx.events.append(events.record_event(TASK.STARTED, record))
    if record:
        record['dimensions'] = dimensions(task)
    if record and not record.get('task_finished_at') and old.get('status') == 'generating' and recap.get('status') in {'ready', 'insufficient', 'failed'}:
        tx.events.append(events.record_event(TASK.FINISHED, record, {'ready': 'completed', 'insufficient': 'partial', 'failed': 'failed'}[recap['status']]))
    _save_task(tx, task)


def segment_changing(store, connection, sid, before, after):
    """Segment writes can finish a task; they no longer emit per-segment events."""
    try:
        tx = _pending(connection)
        if tx is None:
            return
        tx.defer('dimensions', lambda: _refresh_dimensions(tx))
        if _report_changed(before, after, VIDEO_SEGMENT_CONTROL) and store._task(connection).get('_funnel_video_receipt'):
            from runtime.telemetry_funnel import register
            register(tx)
        if before is None or any(before.get(k) != after.get(k) for k in SEGMENT_STATE | {'subtitles','evidence_revision'}):
            from runtime.telemetry_funnel import register
            register(tx)
            check_inspection_completion(store, connection)
    except Exception:
        pass


def _refresh_dimensions(tx):
    task = tx.store._task(tx.connection)
    record = task.get('_telemetry')
    if record:
        record['dimensions'] = dimensions(task, batch=bool(record.get('batch_directory')))
    if task.get('_recap_telemetry'):
        task['_recap_telemetry']['dimensions'] = dimensions(task)
    _save_task(tx, task)
