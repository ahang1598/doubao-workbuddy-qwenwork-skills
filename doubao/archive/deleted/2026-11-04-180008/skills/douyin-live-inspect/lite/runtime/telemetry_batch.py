"""Batch lifecycle aggregation, after child commits and outside child locks."""
from contextlib import contextmanager
from contextvars import ContextVar
import json
from runtime.telemetry_keys import TASK
import os
from pathlib import Path
import time
from runtime import task_telemetry as events_api

_PARENT = ContextVar("telemetry_batch", default=None)
_BATCH_OPERATION = ContextVar("telemetry_batch_operation", default=None)

@contextmanager
def batch_context(root, data):
    record = data.get('_telemetry') if events_api.enabled() else None
    token = _PARENT.set((root, record['telemetry_task_id'], data['id']) if record else None)
    try:
        yield
    finally:
        _PARENT.reset(token)


@contextmanager
def batch_operation(directory):
    root = Path(directory).expanduser().resolve()
    state = {'root': root, 'changed': False, 'children': {}}
    token = _BATCH_OPERATION.set(state)
    try:
        yield
    finally:
        _BATCH_OPERATION.reset(token)
        if state['changed'] or state['children']:
            observe_batch(root, changed=state['changed'], children=state['children'])


@contextmanager
def batch_changes(data):
    if not events_api.enabled():
        yield
        return
    try:
        before = json.dumps(data, sort_keys=True)
    except Exception:
        yield
        return
    try:
        yield
    finally:
        # Optional bookkeeping must neither fail a command nor mask its error.
        try:
            state = _BATCH_OPERATION.get()
            if state is not None and events_api.enabled() and before != json.dumps(data, sort_keys=True):
                state['changed'] = True
        except Exception:
            pass


def notify_parent(store, events):
    if not events or not events_api.enabled():
        return
    try:
        child = store.task().get('_telemetry', {})
        directory = child.get('batch_directory')
        if directory and any(e['extra'].get('telemetry_task_id') == child.get('telemetry_task_id') for e in events):
            observe_batch(directory, children={child['telemetry_task_id']: child['run_index']})
    except Exception:
        pass


def observe_batch(directory, created=False, changed=False, children=None):
    """Reconcile actual transitions; queries never manufacture lifecycle history."""
    if not events_api.enabled() or not (created or changed or children):
        return
    try:
        root = Path(directory).expanduser().resolve()
        state = _BATCH_OPERATION.get()
        if state is not None and state['root'] == root:
            # Same-thread callbacks cannot acquire their enclosing command's lock.
            state['changed'] |= changed
            state['children'].update(children or {})
            return
        _observe_batch(root, created, children or {})
    except Exception:
        pass


def _observe_batch(root, created, children):
    from runtime.store import Store, atomic_json
    from runtime.platform_support import fcntl, nofollow_open
    events = []
    fd = nofollow_open(root / '.batch.lock', os.O_CREAT | os.O_RDWR, 0o600)
    with os.fdopen(fd, 'w') as lock:
        # A concurrent status reader owns the same short-lived lock. Let the
        # completion callback survive ordinary contention without a replay queue.
        deadline = time.monotonic() + 1
        while True:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    return
                time.sleep(0.01)
        data = json.loads((root / 'batch.json').read_text(encoding='utf-8'))
        record = data.get('_telemetry')
        if not record:
            if not created:
                return
            record = data['_telemetry'] = events_api.new_record('video_batch')
            events.append(events_api.record_event(TASK.STARTED, record))
        from runtime.telemetry_context import dimensions
        previous_dimensions = record.get('dimensions')
        record['dimensions'] = dimensions(data, batch=True)
        if events:
            events[0]['extra'].update(record['dimensions'])
        observed = record.setdefault('child_runs', {})
        child_resumed = any(run > observed.get(identity, 1) for identity, run in children.items())
        for identity, run in children.items():
            observed[identity] = max(run, observed.get(identity, 0))
        if record.get('task_finished_at') and child_resumed:
            events.append(events_api.record_event(TASK.RESUMED, record))
        if not record.get('task_finished_at'):
            results = []
            active = False
            for index, item in enumerate(data['videos']):
                path = root / 'tasks' / f'{index + 1:04d}'
                if (path / 'inspection.db').is_file():
                    child = Store(path).task().get('_telemetry', {})
                    results.append(child.get('task_result'))
                    active |= child.get('task_result') is None
                else:
                    results.append('failed' if item['status'] == 'failed' else None)
            result = None
            if data['stopped'] and not active:
                result = 'completed'
            elif results and all(results):
                result = 'completed' if all(r == 'completed' for r in results) else 'failed' if all(r == 'failed' for r in results) else 'partial'
            if result:
                events.append(events_api.record_event(TASK.FINISHED, record, result))
        try:
            from runtime.telemetry_funnel import payload, batch_state
            if record.get('funnel_schema_version') == 1:
                funnel = payload(record, batch_state(root, data), dimensions(data, batch=True))
                if funnel: events.append(funnel)
        except Exception:
            pass  # Projection failure must preserve existing lifecycle transitions.
        if events or children or previous_dimensions != record['dimensions']:
            atomic_json(root / 'batch.json', data)
    events_api.send(events)
