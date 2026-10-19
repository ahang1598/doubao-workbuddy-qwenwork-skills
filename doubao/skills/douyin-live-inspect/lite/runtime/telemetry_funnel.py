"""Current task funnel snapshots, committed before best-effort delivery.

Only newly instrumented tasks participate. Snapshots describe current evidence,
not historical maxima: a resume or evidence change can invalidate a receipt.
"""
import json
import uuid
from runtime import task_telemetry as events
from runtime.telemetry_keys import FUNNEL
from runtime.telemetry_context import dimensions


def token(task, segments):
    from runtime.recap import evidence_input
    return evidence_input(task, segments)['evidence_version']


def video_fingerprint(store, task, segments, status=None):
    from runtime.static_delivery import FrozenStore
    from runtime.video_report import snapshot_key
    from runtime.ui import build_report
    # Use this transaction's data; opening another connection would see the old report.
    frozen = FrozenStore(store, snapshot=(task, segments,
        status if status is not None else store._status(task, segments)))
    return snapshot_key(frozen, build_report(frozen))


def state(store, task, segments, connection):
    status = store._status(task, segments)
    effective = any(s.get('review_status') == 'done' and bool(s.get('review_result')) for s in segments)
    ready = bool(effective and status['report_ready'])
    quality = recap = 'none'
    recap_status = {'status':'not_required'}
    outcome, failure_stage, failure_reason = 'unknown', 'none', 'none'
    delivery_error = 'none'
    if task.get('kind') == 'video':
        receipt = task.get('_funnel_video_receipt', {})
        # Both resume and same-run report changes invalidate a previous delivery.
        if (receipt and receipt.get('report_run') == task.get('video_report_run', 1)
                and receipt.get('run_index') == (task.get('_telemetry') or {}).get('run_index', 1)
                and receipt.get('token') == token(task, segments)
                and receipt.get('fingerprint') == video_fingerprint(store, task, segments, status)):
            ready |= bool(effective and receipt.get('ready'))
            quality = 'ready' if ready and receipt.get('status') == 'delivered' else 'none'
            delivery_error = 'host' if receipt.get('status') == 'failed' else 'none'
        complete = quality == 'ready'
    else:
        from runtime.recap import evidence_input, state as recap_state
        recap_status = recap_state(task, evidence_input(task, segments))
        receipts = task.get('report_deliveries', {})
        if receipts:
            from runtime.recap import evidence_input, state as recap_state
            source = evidence_input(task, segments)
            version = source['evidence_version']
            recap_status = recap_state(task, source)
            for kind in ('quality', 'recap'):
                receipt = receipts.get(kind, {})
                receipt_outcome = receipt.get('outcome', 'ready')
                if receipt.get('evidence_version') != version:
                    continue
                if kind == 'quality':
                    quality = 'ready' if receipt_outcome == 'ready' and ready else 'failed' if receipt_outcome == 'failed' and status.get('report_blocked_reason') else 'none'
                else:
                    from runtime.realtime_policy import current
                    failure_available = (recap_status['status'] == 'blocked' or
                        recap_status.get('terminal_failure', False) or
                        (not current(task) and recap_status['status'] == 'failed'))
                    if receipt_outcome == 'ready' and recap_status.get('available'):
                        recap = 'ready'
                    elif receipt_outcome == 'failed' and failure_available:
                        recap = 'failed'
        complete = quality == 'ready' and recap == 'ready' and recap_status.get('status') == 'ready'
        if complete and task.get('review_dispatch_version') == 2 and not task.get('media_frozen'):
            from runtime.report_completion import has_active_review_child
            complete = not has_active_review_child(connection, store.session_id)
    terminal = task.get('worker_status') in {'done','failed','stopped'} and task.get('capture_status') in {'ended','failed','stopped'}
    if complete:
        outcome = 'success'
    elif delivery_error == 'host':
        outcome, failure_stage, failure_reason = 'failed', 'delivery', 'HOST_DELIVERY_FAILED'
    elif terminal and not ready and (task.get('capture_status') == 'failed' or task.get('worker_status') == 'failed') and any(
            (task.get(key) or {}).get('code') == 'OUT_OF_MEMORY' or (task.get(key) or {}).get('category') == 'MemoryError'
            for key in ('capture_diagnostic', 'failure_diagnostic', 'stream_diagnostic')):
        outcome, failure_stage, failure_reason = 'failed', 'inspection', 'OUT_OF_MEMORY'
    elif recap_status.get('status') == 'insufficient':
        outcome, failure_stage, failure_reason = 'insufficient', 'recap', 'CONTENT_INSUFFICIENT'
    elif recap_status.get('terminal_failure'):
        outcome, failure_stage, failure_reason = 'failed', 'recap', 'RECAP_FAILED'
    elif terminal and not ready and task.get('capture_status') == 'failed':
        code = task.get('source_error_code')
        outcome, failure_stage, failure_reason = 'failed', 'inspection', code if code and code != 'none' else 'TASK_FAILED'
    elif terminal and not ready and task.get('worker_status') == 'failed':
        exhausted = any(s.get('skip_code') == 'ASR_RETRY_EXHAUSTED' for s in segments)
        outcome, failure_stage, failure_reason = 'failed', 'inspection', 'ASR_RETRY_EXHAUSTED' if exhausted else 'TASK_FAILED'
    elif recap_status.get('status') == 'blocked':
        outcome, failure_stage, failure_reason = 'insufficient', 'recap', recap_status.get('code', 'CONTENT_INSUFFICIENT')
    elif terminal and not ready:
        outcome, failure_stage, failure_reason = 'insufficient', 'quality', 'NO_REVIEWED_CONTENT' if segments else 'NO_CAPTURED_CONTENT'
    elif quality == 'failed' or recap == 'failed':
        outcome, failure_stage, failure_reason = 'failed', 'quality' if quality == 'failed' else 'recap', 'TASK_FAILED'
    return {'flow_result':outcome, 'failure_stage':failure_stage, 'failure_reason':failure_reason,
            'recap_status':recap_status.get('status','missing'), 'effective_result': int(effective), 'quality_ready': int(ready),
            'quality_delivery': quality, 'recap_delivery': recap,
            'workflow_success': int(complete), 'delivery_error': delivery_error,
            'quality_blocked': int(bool(status.get('report_blocked_reason'))),
            'funnel_run': (task.get('_telemetry') or {}).get('run_index', 1)}


def payload(record, current, dims):
    if record.get('funnel_schema_version') != 1:
        return None
    previous = record.get('funnel_snapshot', {})
    if previous.get('state') == current:
        return None
    revision = previous.get('revision', 0) + 1
    record['funnel_snapshot'] = {'revision': revision, 'state': current}
    extra = {k: record[k] for k in ('telemetry_task_id','task_type','task_started_at','run_index')}
    # A bounded identity independent of event arrival time / command invocation.
    extra.update(dims)
    extra.update(record.get('owner', {}))
    extra.update(current)
    extra.update(funnel_schema_version=1, funnel_revision=revision,
                 lifecycle_event_id=str(uuid.uuid5(uuid.UUID(record['telemetry_task_id']), f'funnel:{revision}')))
    return {'command': FUNNEL.SNAPSHOT, 'extra': extra}


def register(tx):
    if tx is None or not events.enabled():
        return
    if tx.store._task(tx.connection).get('_telemetry', {}).get('funnel_schema_version') == 1:
        tx.defer('funnel', lambda: _safe_prepare(tx))


def _safe_prepare(tx):
    # Keep a new funnel-projection failure from discarding existing lifecycle events.
    c = tx.connection
    before = len(tx.events)
    c.execute('SAVEPOINT optional_funnel')
    try:
        _prepare(tx)
    except Exception:
        c.execute('ROLLBACK TO optional_funnel')
        del tx.events[before:]
    finally:
        c.execute('RELEASE optional_funnel')


def _prepare(tx):
    task = tx.store._task(tx.connection)
    record = task.get('_telemetry', {})
    current = state(tx.store, task, tx.store._segments(tx.connection), tx.connection)
    event = payload(record, current, dimensions(task))
    if event:
        tx.connection.execute('UPDATE live_sessions SET data=? WHERE id=?',
                              (json.dumps(task, ensure_ascii=False), tx.store.session_id))
        tx.events.append(event)


def observe_video_delivery(store, receipt, frozen):
    """Called only after a validated report/receipt file commit, never by a query."""
    if not events.enabled():
        return
    try:
        with store.connection(True) as conn:
            task = store._task(conn)
            if task.get('_telemetry', {}).get('funnel_schema_version') != 1:
                return
            from runtime.video_report import receipt_matches_run
            if not receipt_matches_run(receipt, frozen):
                return
            frozen_task = frozen.task()
            if receipt['report_run'] != task.get('video_report_run', 1):
                return
            frozen_run = (frozen_task.get('_telemetry') or {}).get('run_index')
            if frozen_run != task['_telemetry']['run_index']:
                return  # A delayed observer must not replace this run's receipt.
            fingerprint = receipt.get('fingerprint')
            segments = store._segments(conn)
            evidence = token(frozen_task, frozen.segments())
            if (evidence != token(task, segments) or not fingerprint
                    or fingerprint != video_fingerprint(store, task, segments)):
                return  # Same-run delayed observations must not replace newer reports either.
            task['_funnel_video_receipt'] = {'fingerprint': fingerprint, 'token': evidence,
                'report_run': receipt['report_run'],
                # Use the report's frozen run, not a possibly resumed current task.
                'run_index': frozen_run,
                'ready': receipt['result'].get('status') == 'ready', 'status': receipt['delivery_status']}
            # Optional state only: no business revision or lifecycle side effects.
            conn.execute('UPDATE live_sessions SET data=? WHERE id=?', (json.dumps(task), store.session_id))
            register(conn.telemetry)
    except Exception:
        pass


def batch_state(root, data):
    from runtime.store import Store
    children = []
    for index, _ in enumerate(data['videos']):
        path = root / 'tasks' / f'{index + 1:04d}'
        if not (path / 'inspection.db').is_file():
            children.append({})
            continue
        children.append(Store(path).task().get('_telemetry', {}).get('funnel_snapshot', {}).get('state', {}))
    all_flag = lambda key: int(bool(children) and all(c.get(key) == 1 for c in children))
    delivered = bool(children) and all(c.get('quality_delivery') == 'ready' for c in children)
    failed = next((c for c in children if c.get('flow_result') == 'failed'), None)
    insufficient = next((c for c in children if c.get('flow_result') == 'insufficient'), None)
    cause = failed or insufficient or {}
    missing_failed = any(v.get('status') == 'failed' and not children[i] for i,v in enumerate(data['videos']))
    return {'flow_result':'success' if delivered else 'failed' if failed or missing_failed else 'insufficient' if insufficient else 'unknown',
            'failure_stage':cause.get('failure_stage','startup' if missing_failed else 'none'),
            'failure_reason':cause.get('failure_reason','TASK_FAILED' if missing_failed else 'none'),
            'recap_status':'not_required', 'effective_result': all_flag('effective_result'), 'quality_ready': all_flag('quality_ready'),
            'quality_delivery': 'ready' if delivered else 'none', 'recap_delivery': 'none',
            'workflow_success': int(delivered), 'delivery_error': 'host' if any(c.get('delivery_error') == 'host' for c in children) else 'none',
            'quality_blocked': int(any(c.get('quality_blocked') for c in children)),
            'funnel_run': data['_telemetry']['run_index'], 'expected_children': len(children),
            'observed_children': sum(bool(c) for c in children)}
