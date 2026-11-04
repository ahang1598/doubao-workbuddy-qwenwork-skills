"""管理 Lite 任务与复盘的尝试标记、轮次及生命周期事件，按已有业务结果判断结束分类。
生成开始、恢复、结束等事实及可选遥测状态，不直接发送；避免升级后重复生成历史事件。
"""
from datetime import datetime
import json
import os
import re
import uuid
from runtime.bridge import TASK, _CONTEXT
from runtime.context import dimensions

def now():
    from runtime.transaction import now
    return now()

def _valid_owner_uid(value):
    return isinstance(value, str) and value.isascii() and value.isdigit() and 1 <= len(value) <= 64

def _valid_owner_email(value):
    return isinstance(value, str) and len(value) <= 254 and re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', value) is not None


def _valid_owner_username(value):
    return (isinstance(value, str) and 1 <= len(value) <= 64 and "@" not in value
            and not any(ch.isspace() for ch in value))

def owner():
    try:
        value = json.loads(os.environ.get(_CONTEXT, '{}'))
        identity = {}
        uid = value.get('doubao_user_id')
        if _valid_owner_uid(uid):
            identity['doubao_user_id'] = uid
        email = value.get('doubao_email')
        if _valid_owner_email(email):
            identity['doubao_email'] = email
        username = value.get('doubao_username')
        if _valid_owner_username(username):
            identity['doubao_username'] = username
        return identity
    except (ValueError, TypeError, AttributeError):
        return {}

def new_record(kind, started_at=None, parent=None):
    record = {'telemetry_task_id': str(uuid.uuid4()), 'task_type': kind,
              'task_started_at': started_at or now(), 'run_index': 1, 'owner': owner()}
    if kind != 'live_recap':
        record['funnel_schema_version'] = 1
    if parent:
        record['parent_task_id'] = parent
    return record

def _event(record, key):
    phase = key.rsplit(".", 1)[-1]
    record.setdefault('attempted', []).append(f"{record['run_index']}:{phase}")
    extra = {k: record[k] for k in ('telemetry_task_id', 'task_type', 'task_started_at',
             'run_index', 'parent_task_id', 'task_finished_at', 'task_result', 'task_elapsed_ms',
             'recap_attempt', 'recap_retry_count', 'recap_failure_reason', 'recap_final') if k in record}
    if record.get('funnel_schema_version') == 1:
        extra['funnel_schema_version'] = 1
    extra.update(record.get('dimensions', {}))
    extra.update(record.get('owner') or {})
    extra['lifecycle_event_id'] = str(uuid.uuid5(uuid.UUID(record['telemetry_task_id']), f"{record['run_index']}:{phase}"))
    return {'command': key, 'extra': extra}

def record_event(key, record, result=None):
    """Build a lifecycle event and claim it once; send only after business commit.

    Call with TASK.STARTED / RESUMED / FINISHED from the shared registry.
    Existing IDs and persisted phase markers remain compatible across upgrades.
    """
    if key == TASK.STARTED:
        if f"{record['run_index']}:started" in record.get('attempted', []):
            return None
    elif key == TASK.RESUMED:
        if not record.get('task_finished_at'):
            return None
        record['run_index'] += 1
        for field in ('task_finished_at', 'task_result', 'task_elapsed_ms'):
            record.pop(field, None)
    elif key == TASK.FINISHED:
        if result not in {'completed', 'partial', 'stopped', 'failed'}:
            raise ValueError('Invalid task result')
        if record.get('task_finished_at'):
            return None
        finished = now()
        elapsed = datetime.fromisoformat(finished.replace('Z', '+00:00')) - datetime.fromisoformat(record['task_started_at'].replace('Z', '+00:00'))
        record.update(task_finished_at=finished, task_result=result,
                      task_elapsed_ms=max(0, round(elapsed.total_seconds() * 1000)))
    else:
        raise ValueError('Unknown lifecycle event')
    return _event(record, key)

def inspection_result(task, segments, coverage=None, *, reviewed=None):
    def has_review():
        return bool(reviewed) if reviewed is not None else any(s.get('review_status')=='done' and s.get('review_result') for s in segments)
    from runtime.store import ASR_DONE, FRAME_DONE, capture_coverage
    capture_ended = task.get('capture_status') in {'ended', 'stopped', 'failed'}
    if task.get('kind') == 'video' and capture_ended:
        closed = (task.get('finishing', {}).get('phase') == 'completed' or
                  (task.get('worker_status') in {'done','failed','stopped'} and
                   all(s.get('review_status') in {'done','skipped','deferred'} for s in segments)))
        if closed and not has_review():
            return 'failed'
    if task.get('kind','live')=='live' and task.get('finishing',{}).get('phase')=='draining':
        return None
    from runtime.realtime_policy import current
    if current(task) and task.get('media_frozen') and task.get('finishing', {}).get('phase') == 'completed':
        if task.get('stop_audit', {}).get('reason') == 'user_request' or task.get('stop_reason') == 'user_request':return 'completed'
        return 'partial' if has_review() else 'failed'
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
        if coverage is None:coverage = capture_coverage(task, segments)
        # Only an explicitly disabled image modality can excuse absent frames.
        complete_frames = {'success', 'not_required'} if task.get('image_inspection') is False else {'success'}
        gaps = not coverage['complete'] or bool(coverage['analysis_gaps']) or any(
            s.get('review_status')=='skipped' or s.get('asr_status') not in ('success', 'no_audio') or s.get('frame_status') not in complete_frames
            or any((r.get('status') or r.get('result')) == 'insufficient' for r in (s.get('review_result') or {}).get('rules', [])) for s in segments)
        return 'partial' if gaps or task.get('capture_status') == 'failed' or task.get('worker_status') == 'failed' else 'completed'
    if not segments or task.get('worker_status') == 'failed':
        return 'failed'
    return None

def recap_transition(task, old, emitted):
    recap = task.get('recap') or {}
    record = task.get('_recap_telemetry')
    if (record and record.get('task_finished_at') and old.get('status') == 'failed'
            and old.get('failure_code') == 'RECAP_TIMEOUT' and recap.get('status') in {'ready', 'insufficient'}):
        # A valid late report supersedes an old deadline failure in a new run.
        record_event(TASK.RESUMED, record)
    if recap.get('status') == 'generating' and (old.get('status') != 'generating' or old.get('evidence_version') != recap.get('evidence_version')):
        if record:
            # Freeze this attempt's fields before constructing a resumed payload.
            attempt = recap.get('attempts', 1)
            record.update(recap_final=False, recap_attempt=attempt, recap_retry_count=max(0, attempt - 1))
            if old.get('evidence_version') != recap.get('evidence_version'):
                record['recap_failure_reason'] = 'none'
        if record and record.get('task_finished_at'):
            resumed = record_event(TASK.RESUMED, record)
            # Old installations closed a lifecycle on every failed attempt.
            # Advance that legacy run locally; only the final result is sent.
            if old.get('status') != 'failed':
                emitted.append(resumed)
        elif not record:
            record = new_record('live_recap', parent=(task.get('_telemetry') or {}).get('telemetry_task_id'))
            record['dimensions'] = dimensions(task)
            task['_recap_telemetry'] = record
            emitted.append(record_event(TASK.STARTED, record))
    if record:
        record['dimensions'] = dimensions(task)
        attempt = recap.get('attempts', 1)
        record.update(recap_attempt=attempt, recap_retry_count=max(0, attempt - 1))
        if not record.get('task_finished_at'):
            record['recap_final'] = False
        if recap.get('status') == 'failed':
            record['recap_failure_reason'] = ('RECAP_TIMEOUT' if recap.get('failure_code') == 'RECAP_TIMEOUT'
                                               else 'RECAP_ATTEMPT_FAILED')
        else:
            record.setdefault('recap_failure_reason', 'none')
    changed = old.get('status') != recap.get('status') or old.get('attempts') != recap.get('attempts')
    from runtime.realtime_policy import current
    receipt = task.get('report_deliveries', {}).get('recap', {})
    final_failure = recap.get('status') == 'failed' and (
        (current(task) and recap.get('attempts', 1) >= 3 and recap.get('failure_code') != 'RECAP_TIMEOUT') or
        (not current(task) and receipt.get('outcome') == 'failed' and
         receipt.get('evidence_version') == recap.get('evidence_version')))
    if record and (changed or final_failure):
        retryable = recap.get('status') == 'failed' and not final_failure
        retry_started = recap.get('status') == 'generating' and old.get('status') == 'failed'
        if retryable or retry_started:
            # Local-only diagnostics must not close the online lifecycle or create
            # a new run. The Node boundary validates and bypasses the SDK entirely.
            import uuid
            extra = {k: record[k] for k in ('telemetry_task_id', 'task_type', 'task_started_at',
                     'run_index', 'parent_task_id', 'recap_attempt', 'recap_retry_count', 'recap_failure_reason') if k in record}
            extra.update(record['dimensions'])
            extra.update(recap_final=False, recap_attempt_state='failed' if retryable else 'retrying',
                         lifecycle_event_id=str(uuid.uuid5(uuid.UUID(record['telemetry_task_id']),
                             f"recap-attempt:{attempt}:{recap['status']}")))
            emitted.append({'command': TASK.FINISHED if retryable else TASK.RESUMED,
                              'local_only': True, 'extra': extra})
        elif not record.get('task_finished_at') and recap.get('status') in {'ready', 'insufficient', 'failed'}:
            record['recap_final'] = True
            emitted.append(record_event(TASK.FINISHED, record,
                {'ready': 'completed', 'insufficient': 'partial', 'failed': 'failed'}[recap['status']]))
