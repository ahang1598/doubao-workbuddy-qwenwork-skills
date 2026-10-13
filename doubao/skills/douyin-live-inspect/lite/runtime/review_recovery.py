"""Explicit takeover using the existing batch generation and receipt ledger."""
import json
from pathlib import Path

from runtime import live_review
from runtime.review_execution import bind_request, input_bytes, identifier, current_recovery
from runtime.store import Store


def recover(root, context_id, dispatcher_id):
    store = Store(root).for_session()
    identifier(context_id)
    with store.connection(True) as conn:
        context = live_review.context_record(conn, store, context_id)
        task = store._task(conn)
        if task.get('review_dispatch', {}).get('owner', 'main') != dispatcher_id:
            raise ValueError('dispatcher binding mismatch')
        batch = live_review.row(conn, store.session_id, context['batch_id'])
        if not batch or batch.get('executor') != 'main':
            raise ValueError('serial review recovery required')
        if context.get('recovery'):
            result = current_recovery(conn, store.session_id, context['recovery'])
            bind_request(conn, store.session_id, context_id=context_id, recovery_receipt=result)
            return result
        live_review.check_context(conn, store, context_id)
        from runtime.finishing import advance, closed
        finish = advance(store, conn)
        task = store._task(conn)
        lookup = {s['id']: s for s in store._segments(conn)}
        pending = [int(sid) for sid in context['targets']
                   if lookup[int(sid)]['review_status'] == 'pending']
        stopped = (closed(finish) or task.get('media_frozen') or task.get('stop_immediately')) if task.get('inspection_policy')=='lite_live_realtime_v2' else (
            closed(finish) or task.get('media_frozen') or task.get('stop_requested')
            or task.get('capture_status') in {'failed', 'stopped', 'ended'} or bool(finish))
        unchanged = (context['rules_version'] == task['rules_snapshot']['version'] and
                     all(lookup[int(sid)]['evidence_revision'] == revision
                         for sid, revision in context['targets'].items()))
        if not stopped and not unchanged:
            raise ValueError('evidence changed; read segment again')

        # Read only the bound draft. A malformed draft cannot invalidate saved results.
        draft = None
        if pending and not stopped and batch.get('input_path'):
            try:
                value = json.loads(input_bytes(batch['input_path']))
                items = value.get('segments') if isinstance(value, dict) else None
                if (value.get('task_id') == task['id'] and value.get('context_id') == context_id
                        and isinstance(items, list) and all(isinstance(s, dict) for s in items)):
                    ids = [s.get('segment_id') for s in items]
                    if all(type(i) is int for i in ids) and len(ids) == len(set(ids)):
                        draft = {s['segment_id']: s for s in items}
            except (OSError, ValueError, TypeError, AttributeError, RecursionError):
                pass
        batch['generation'] += 1
        batch.pop('context_id', None)
        if stopped:
            batch['status'] = 'skipped' if pending else 'done'
            live_review.save(conn, store.session_id, batch)
            result = {'status':'stopped', 'next_action':'report' if closed(finish) else 'status',
                      'task_id':task['id'], 'segments':[]}
        elif not pending:
            batch['status'] = 'done'
            live_review.save(conn, store.session_id, batch)
            result = context.get('continuation') or live_review.claim(
                store, dispatcher_id=dispatcher_id, limit=20 if task.get('inspection_policy')=='lite_live_realtime_v2' else 4, conn=conn)
        else:
            batch.update(status='allocated', targets={str(sid):context['targets'][str(sid)] for sid in pending})
            live_review.save(conn, store.session_id, batch)
            result = live_review.claim(store, dispatcher_id=dispatcher_id, limit=20 if task.get('inspection_policy')=='lite_live_realtime_v2' else 4,
                                       conn=conn, target_batch_id=batch['id'])
            contract = result['submission_contract']
            if draft:
                template = contract['template']
                copied = {**template, 'segments':[draft.get(s['segment_id'], s) for s in template['segments']]}
                from runtime.store import atomic_json
                atomic_json(Path(contract['input_path']), copied)
                contract['draft_state'] = 'recovered'
        result = {**result, 'recovered_from_context_id':context_id}
        from runtime.report_delivery import bounded_output
        bounded_output(store, 'review-recover', result)  # Persist paging before committing the receipt.
        context['recovery'] = result
        live_review.save_context(conn, store, context_id, context)
        bind_request(conn, store.session_id, context_id=context_id, recovery_receipt=result)
        return result
