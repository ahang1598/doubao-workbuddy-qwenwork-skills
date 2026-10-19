"""Transactional review assignments with serial compatibility and observed host dispatch."""
import contextlib
import json
import time
import uuid

from runtime import full_live

from runtime import review_dispatch

ACTIVE = review_dispatch.ACTIVE
LEGACY_CHILD_STATES = {'allocated', 'dispatching', 'running', 'returned', 'cancelling'}


def initialize(conn):
    conn.execute(
        "CREATE TABLE IF NOT EXISTS review_batches "
        "(session_id TEXT NOT NULL,id TEXT NOT NULL,data TEXT NOT NULL,"
        "PRIMARY KEY(session_id,id))"
    )


def rows(conn, session):
    return [json.loads(value[0]) for value in conn.execute(
        'SELECT data FROM review_batches WHERE session_id=?', (session,)
    )]


def row(conn, session, batch_id):
    value = conn.execute(
        'SELECT data FROM review_batches WHERE session_id=? AND id=?',
        (session, batch_id),
    ).fetchone()
    return json.loads(value[0]) if value else None


def save(conn, session, batch):
    conn.execute(
        'INSERT OR REPLACE INTO review_batches VALUES(?,?,?)',
        (session, batch['id'], json.dumps(batch, ensure_ascii=False)),
    )


def _retire_legacy_child_batches(conn, store, batches):
    """Fence obsolete child work so the current Agent can safely re-claim it."""
    for batch in batches:
        if batch.get('executor') != 'child' or batch.get('status') not in LEGACY_CHILD_STATES:
            continue
        batch.update(status='retry', failures=batch.get('failures', 0) + 1)
        batch.pop('context_id', None)
        batch.pop('host_task_id', None)
        batch.pop('result_path', None)
        save(conn, store.session_id, batch)


def context_record(conn, store, context_id):
    value = conn.execute('SELECT data FROM review_contexts WHERE id=? AND session_id=?',
                         (context_id, store.session_id)).fetchone()
    if not value: raise ValueError('stale or missing review context')
    return json.loads(value[0])


def save_context(conn, store, context_id, context):
    conn.execute('UPDATE review_contexts SET data=? WHERE id=? AND session_id=?',
                 (json.dumps(context, ensure_ascii=False), context_id, store.session_id))


def check_context(conn, store, context_id):
    context = context_record(conn, store, context_id)
    batch = row(conn, store.session_id, context['batch_id'])
    if context.get('recovery'):
        raise ValueError('review context superseded')
    if not batch or batch['generation'] != context['generation'] or batch.get('context_id') != context_id:
        if (context['rules_version'] != store._task(conn)['rules_snapshot']['version'] or
                any((store._segment(conn, int(sid)) or {}).get('evidence_revision') != revision
                    for sid, revision in context['targets'].items())):
            raise ValueError('evidence changed; read segment again')
        raise ValueError('stale or missing review batch')
    return context


def claim(store, known_rules_version=None, limit=2, dispatcher_id="main", *,
          conn=None, source_context=None, target_batch_id=None):
    # Fence continuation in the allocation transaction, including duplicate submissions.
    with store.connection(True) if conn is None else contextlib.nullcontext(conn) as transaction:
        from runtime.realtime_policy import current
        task = store._task(transaction)
        if current(task) and task.get('finishing', {}).get('phase') == 'completed':
            return _claim(store, transaction, known_rules_version, limit, dispatcher_id, target_batch_id)
        context = check_context(transaction, store, source_context) if source_context else None
        if context and context.get('continuation'):
            return context['continuation']
        result = _claim(store, transaction, known_rules_version, limit, dispatcher_id, target_batch_id)
        if context is not None:
            context = context_record(transaction, store, source_context)
            context['continuation'] = result
            save_context(transaction, store, source_context, context)
        return result


def _claim(store, conn, known_rules_version, limit, dispatcher_id, target_batch_id=None):
    from runtime.finishing import advance, closed

    initialize(conn)
    finish = advance(store, conn)
    task = store._task(conn)
    dispatch_v2 = review_dispatch.enabled(task)
    if dispatch_v2 and closed(finish):
        dispatch = dict(task.get('review_dispatch', {}))
        review_dispatch.own(dispatch, dispatcher_id, time.time())
        task['review_dispatch'] = dispatch
        store._set_task(conn, task)
    if closed(finish):
        batches = rows(conn, store.session_id)
        for batch in batches:
            if batch.get('status') in ACTIVE:
                batch['status'] = ('cancelling' if dispatch_v2 and batch.get('executor') == 'child'
                                   and batch['status'] in {'dispatching', 'running', 'cancelling'} else 'skipped')
                save(conn, store.session_id, batch)
        return {
            'task_id': store.task_id,
            'segments': [],
            'inspection_finished': True,
            'next_action': 'report',
            **({'cancel_batches': [_host_batch(b) for b in rows(conn, store.session_id) if b['status'] == 'cancelling']} if dispatch_v2 else {}),
        }

    store._ensure_rule_defaults(conn)
    task = store._task(conn)
    now = time.time()
    dispatch = dict(task.get('review_dispatch', {}))
    if task.get('inspection_policy') in {'lite_live_realtime_v1','lite_live_realtime_v2'}:
        dispatch['worker_ceiling'] = min(2, dispatch.get('worker_ceiling', 0))
    batches = rows(conn, store.session_id)
    if dispatch_v2:
        review_dispatch.own(dispatch, dispatcher_id, now)
        for batch in batches:
            if batch.get('executor') != 'child':
                continue
            if batch['status'] == 'allocated' and (
                finish or now - batch['created_at'] >= 60
                or dispatch.get('capability_state') != 'ready'
                or dispatch.get('worker_ceiling', 0) <= 0
            ):
                batch['status'] = 'retry'
            elif batch['status'] == 'running' and now - batch['started_at'] > 180:
                batch['status'] = 'cancelling'
            save(conn, store.session_id, batch)
    else:
        for obsolete in ('capability', 'probe_started_at', 'bootstrap_state', 'quiet_rounds', 'backlog_samples'):
            dispatch.pop(obsolete, None)
        dispatch.update(owner='main', heartbeat_at=now,
                        reduction_reason='serial_default', slots=1, ceiling=1, mode='serial')
        _retire_legacy_child_batches(conn, store, batches)
    batches = rows(conn, store.session_id)
    segments = store._segments(conn)
    lookup = {segment['id']: segment for segment in segments}
    snapshot = task['rules_snapshot']

    for batch in batches:
        if batch.get('status') not in ACTIVE:
            continue
        if all(
            lookup[int(segment_id)]['review_status'] == 'done'
            and lookup[int(segment_id)]['evidence_revision'] == revision
            for segment_id, revision in batch['targets'].items()
        ):
            batch['status'] = 'done'
            save(conn, store.session_id, batch)
        elif (
            batch['rules_version'] != snapshot['version']
            or any(
                lookup[int(segment_id)]['evidence_revision'] != revision
                for segment_id, revision in batch['targets'].items()
            )
        ):
            dispatch['progress_baseline_at'] = now
            batch['status'] = ('cancelling' if dispatch_v2 and batch.get('executor') == 'child'
                               and batch['status'] in {'dispatching', 'running', 'cancelling'} else 'retry')
            if batch['status'] == 'retry':
                batch.pop('context_id', None)
            save(conn, store.session_id, batch)

    batches = rows(conn, store.session_id)
    allocated = [
        batch for batch in batches
        if batch.get('status') == 'allocated'
    ]
    ready = [
        segment for segment in segments
        if segment['review_status'] == 'pending' and full_live.ready(task, segment)
    ]
    if dispatch_v2:
        review_dispatch.refresh(dispatch, batches, segments, ready, now)
        review_dispatch.retire_excess_allocations(conn, store, dispatch, batches)
    occupied = {
        int(segment_id)
        for batch in batches if batch['status'] in ACTIVE
        for segment_id in batch['targets']
    }
    waiting = sorted((segment for segment in ready if segment['id'] not in occupied),
                     key=lambda s: (s.get('asr_ready_at', now), s['start_ms'], s['id']))
    if ready:
        dispatch.setdefault('progress_baseline_at', now)
    else:
        dispatch.pop('progress_baseline_at', None)

    executor = 'main'
    if dispatch_v2:
        allocated, executor, slots = review_dispatch.selection(dispatch, batches, waiting, finish, now)
        dispatch.update(slots=slots, mode='parallel' if slots > 1 else 'serial')
    task['review_dispatch'] = dispatch
    store._set_task(conn, task)

    if not allocated and waiting and executor:
        waiting_ids = {segment['id'] for segment in waiting}
        retry = next((
            batch for batch in batches
            if batch.get('status') == 'retry'
            and any(int(segment_id) in waiting_ids for segment_id in batch['targets'])
        ), None)
        chosen = waiting[:min(20 if task.get('inspection_policy') == 'lite_live_realtime_v2' else 2 if executor == 'child' else 4, max(1, limit))]
        if task.get('inspection_policy') == 'lite_live_realtime_v1':
            chosen = [s for i, s in enumerate(chosen) if sum(x['end_ms']-x['start_ms'] for x in chosen[:i+1]) <= 120000]

        batch = {
            'id': retry['id'] if retry else uuid.uuid4().hex,
            'generation': retry['generation'] + 1 if retry else 1,
            'targets': {
                str(segment['id']): segment['evidence_revision']
                for segment in chosen
            },
            'rules_version': snapshot['version'],
            'status': 'allocated',
            'executor': executor,
            'created_at': now,
            'failures': retry.get('failures', 0) if retry else 0,
        }
        save(conn, store.session_id, batch)
        allocated = [batch]

    result = {
        'task_id': store.task_id,
        'mode': dispatch['mode'],
        'slots': dispatch['slots'],
        'inflight_batches': [
            {
                'batch_id': batch['id'],
                'generation': batch['generation'],
                'status': batch['status'],
                'context_id': batch.get('context_id'),
                **({'host_task_id': batch.get('host_task_id')} if dispatch_v2 else {}),
            }
            for batch in rows(conn, store.session_id) if batch['status'] in ACTIVE
        ],
        'segments': [],
        'finishing': finish,
        'poll_after_seconds': 3,
        'reduction_reason': dispatch.get('reduction_reason'),
    }
    if dispatch_v2 and task.get('inspection_policy') not in {'lite_live_realtime_v1','lite_live_realtime_v2'} and dispatch.get('capability_state', 'unverified') == 'unverified' and not finish:
        result['capability_check'] = {
            'next_action':'verify-host-capability-once','budget_seconds':60,
            'prepare':{'dispatcher_id':dispatcher_id,'action':'prepare'},
            'unavailable':{'dispatcher_id':dispatcher_id,'action':'degrade'},
            'instruction':'串行批次立即继续。无子任务工具登记 degrade；有工具先 prepare，实际核验读证据、结构化返回、完成和取消能力后按 live-dispatch.md 登记 probe，不能伪造能力。'}
    if dispatch_v2:
        current = rows(conn, store.session_id)
        result.update(dispatcher_id=dispatcher_id,
                      capability_state=dispatch.get('capability_state', 'unverified'),
                      acceptance_state=dispatch.get('acceptance_state', 'parallel_unverified'),
                      reconcile_required=dispatch.get('reconcile_required', False),
                      cancel_batches=[_host_batch(b) for b in current if b['status'] == 'cancelling'],
                      reconcile_batches=[_host_batch(b) for b in current if b['status'] == 'dispatching'])
    if not allocated:
        result.setdefault('next_action', 'status')
        from runtime.review_execution import bind_result
        bind_result(store, conn, result)
        return result

    if target_batch_id:
        allocated = [b for b in allocated if b['id'] == target_batch_id]
        if not allocated: raise ValueError('stale or missing review batch')
    batch = allocated[0]
    result.update(batch_id=batch['id'], generation=batch['generation'], executor=batch['executor'])
    from runtime.adaptive_segments import enabled as adaptive
    target_ids = batch['targets']
    if adaptive(task) or task.get('inspection_policy') in {'lite_live_realtime_v1','lite_live_realtime_v2'}:
        target_ids = sorted(target_ids, key=lambda sid: (lookup[int(sid)]['start_ms'], int(sid)))
        result['reading_order'] = '按时间连贯理解本批字幕，逐片段返回结果；只引用该片段允许的证据，不重复计入相邻片段。'
    for segment_id in target_ids:
        segment = dict(lookup[int(segment_id)])
        if segment['review_status'] in {'done','skipped'}:
            continue
        segment['context_subtitles'] = [
            utterance
            for previous in segments
            if previous['end_ms'] <= segment['start_ms']
            and previous['end_ms'] > segment['start_ms'] - 15000
            for utterance in previous.get('subtitles', [])
            if utterance['start_ms'] > segment['start_ms'] - 15000
            and utterance['end_ms'] <= segment['start_ms']
        ]
        segment['context_is_coverage'] = False
        segment['image_checklist'] = segment.get('frames', [])
        segment.update(batch_id=batch['id'], generation=batch['generation'])
        from runtime.review_contract import enabled as protocol_v2
        if protocol_v2(task) and segment.get('speech_reviewed') and segment.get('previous_review_result'):
            segment['review_kind'] = 'visual_supplement'
            segment['saved_decisions'] = segment['previous_review_result']['rules']
            segment.pop('subtitles', None)
            segment.pop('context_subtitles', None)
        result['segments'].append(segment)
        if not segment.get('review_started_at'):
            store._update_segment(conn, segment['id'], review_started_at=now)

    cached = known_rules_version == snapshot['version'] and batch['executor'] == 'main'
    if cached:
        result['rules'] = {
            'version': snapshot['version'],
            'cached': True,
            'rule_ids': [rule['id'] for rule in snapshot['rules']],
        }
    else:
        from runtime.rules import review_snapshot
        result['rules'] = review_snapshot(snapshot, compact=task.get('inspection_policy') in {'lite_live_realtime_v1','lite_live_realtime_v2'})
    from runtime.review_contract import enabled as protocol_v2, attach
    if protocol_v2(task):
        attach(store, conn, batch, result, snapshot)
    if batch['executor'] == 'child':
        binding = {'dispatcher_id': dispatcher_id, 'batch_id': batch['id'], 'generation': batch['generation']}
        result['dispatch_contract'] = {
            'before_spawn': {**binding, 'action': 'dispatching'},
            'after_spawn': {**binding, 'action': 'bound', 'host_task_id': None},
            'after_started': {**binding, 'action': 'started', 'host_task_id': None, 'running_confirmed': True},
            'after_return': {**binding, 'action': 'returned', 'host_task_id': None},
            'instructions': '先登记 dispatching，再调用宿主。取得真实任务ID后登记 bound，实际运行确认后登记 started；返回后登记 returned，按合同提交。未知派发禁止重派。Worker只填合同，不领取或提交。',
        }
    result['next_action'] = 'dispatch-review-batch' if batch['executor'] == 'child' else 'review-submit'
    from runtime.review_execution import bind_result
    bind_result(store, conn, result)
    return result


def bind(conn, store, payload, segment):
    initialize(conn)
    batch = row(conn, store.session_id, payload.get('batch_id'))
    if not batch or batch['generation'] != payload.get('generation') or batch['status'] not in ACTIVE:
        raise ValueError('stale or missing review batch')
    if batch.get('executor') != 'main':
        if not review_dispatch.enabled(store._task(conn)):
            raise ValueError('legacy child review batch must be reclaimed')
        if (batch['status'] not in {'running', 'returned'} or not batch.get('host_task_id')
                or payload.get('host_task_id') != batch['host_task_id']):
            raise ValueError('host task binding mismatch')
    if (
        batch['targets'].get(str(segment['id'])) != segment['evidence_revision']
        or batch['rules_version'] != store._task(conn)['rules_snapshot']['version']
    ):
        raise ValueError('evidence changed; read segment again')


def _host_batch(batch):
    return {'batch_id': batch['id'], 'generation': batch['generation'],
            'status': batch['status'], 'host_task_id': batch.get('host_task_id'),
            'context_id': batch.get('context_id')}
