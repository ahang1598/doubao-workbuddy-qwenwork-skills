"""Best-effort lifecycle records; business commits always precede network I/O.

The persisted markers mean 'attempt claimed', not 'server accepted'. There is no
retry queue: a crash between commit and send deliberately loses the event.
"""
from datetime import datetime, timezone
import json
import os
from runtime.telemetry_transport import send
import uuid
from runtime.telemetry_keys import TASK

_CONTEXT = 'BYTEDLIVE_LITE_TELEMETRY_IDENTITY'


def enabled():
    return os.environ.get('BYTEDLIVE_TELEMETRY_DISABLED', '').strip().lower() not in ('1', 'true') and _CONTEXT in os.environ


def now():
    return datetime.now(timezone.utc).isoformat()


def _valid_owner_uid(value):
    return isinstance(value, str) and value.isascii() and value.isdigit() and 1 <= len(value) <= 64


def _valid_owner_email(value):
    return (isinstance(value, str) and 1 <= len(value) <= 254 and value.count("@") == 1
            and not any(ch.isspace() for ch in value)
            and "@" in value and "." in value.split("@", 1)[1])


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
             'run_index', 'parent_task_id', 'task_finished_at', 'task_result', 'task_elapsed_ms') if k in record}
    if record.get('funnel_schema_version') == 1:
        extra['funnel_schema_version'] = 1
    extra.update(record.get('dimensions', {}))
    extra.update(record['owner'])
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
        elapsed = datetime.fromisoformat(finished) - datetime.fromisoformat(record['task_started_at'])
        record.update(task_finished_at=finished, task_result=result,
                      task_elapsed_ms=max(0, round(elapsed.total_seconds() * 1000)))
    else:
        raise ValueError('Unknown lifecycle event')
    return _event(record, key)


def start_store(store):
    if not enabled():
        return
    try:
        with store.connection(True) as c:
            task = store._task(c)
            if task.get('_telemetry'):
                return
            parent = _PARENT.get()
            record = new_record('video_inspection' if task['kind'] == 'video' else 'live_inspection', task['created_at'], parent[1] if parent else None)
            record['task_id'] = parent[2] if parent else task['task_id']
            if parent:
                record['batch_directory'] = str(parent[0])  # local only; never emitted
            from runtime.telemetry_context import dimensions
            task['_telemetry'] = record
            record['dimensions'] = dimensions(task, batch=bool(parent))
            payload = record_event(TASK.STARTED, record)
            c.execute('UPDATE live_sessions SET data=? WHERE id=?', (json.dumps(task, ensure_ascii=False), store.session_id))
        send([payload])
    except Exception:
        pass


# Stable facade for business callers; batch rules depend only on the event API.
from runtime.telemetry_batch import (batch_context, batch_operation, batch_changes,
    observe_batch, notify_parent, _PARENT)
