"""Host-observed dispatch lifecycle. Unknown launches retain their evidence slots."""
import time

ACTIVE = {'allocated', 'dispatching', 'running', 'returned', 'cancelling'}


def enabled(task):
    return task.get('review_dispatch_version') == 2


def own(dispatch, owner, now):
    if not isinstance(owner, str) or not owner.strip():
        raise ValueError('dispatcher ID required')
    previous = dispatch.get('owner')
    if previous not in (None, owner) and now - dispatch.get('heartbeat_at', now) <= 180:
        raise ValueError('dispatcher binding mismatch')
    changed = previous not in (None, owner)
    dispatch.update(owner=owner, heartbeat_at=now)
    if changed:
        dispatch['reconcile_required'] = True


def retire_excess_allocations(conn, store, dispatch, batches):
    """A reduced ceiling fences unlaunched children without releasing live hosts."""
    from runtime.live_review import save
    ceiling = dispatch.get('worker_ceiling', 0) if dispatch.get('capability_state') == 'ready' else 0
    if dispatch.get('reconcile_required') or any(b['status'] in {'dispatching', 'cancelling'} for b in batches):
        ceiling = 0
    live = sum(b.get('executor') == 'child' and b['status'] in ACTIVE
               and b['status'] != 'allocated' for b in batches)
    remaining = max(0, ceiling - live)
    for batch in sorted(batches, key=lambda b: b['created_at']):
        if batch.get('executor') == 'child' and batch['status'] == 'allocated':
            if remaining:
                remaining -= 1
            else:
                batch['status'] = 'retry'
                save(conn, store.session_id, batch)


def control(store, value):
    from runtime.live_review import initialize, rows, row, save
    with store.connection(True) as conn:
        initialize(conn)
        task = store._task(conn)
        if not enabled(task):
            raise ValueError('dispatch v2 required; existing tasks stay serial')
        now = time.time()
        dispatch = dict(task.get('review_dispatch', {}))
        own(dispatch, value.get('dispatcher_id'), now)
        action = value.get('action')
        batches = rows(conn, store.session_id)
        stopping = (task.get('stop_requested') or task.get('finishing')
                    or task.get('capture_status') in {'ended', 'stopped', 'failed'})
        if action in {'dispatching', 'probe'} and stopping:
            raise ValueError('stopping inspection cannot launch new workers')
        if action in {'dispatching', 'started', 'probe'} and task.get('finishing', {}).get('mode') == 'immediate':
            raise ValueError('inspection already stopped')
        if action == 'prepare':
            dispatch.setdefault('probe_started_at', now)
            dispatch.setdefault('capability_state', 'checking')
        elif action == 'probe':
            probe = value.get('probe', {})
            checks = ['text_read', 'structured_result', 'completion_observable', 'cancellation_observable']
            if task.get('frame_required'):
                checks.append('image_read')
            if (dispatch.get('capability_state') != 'checking'
                    or now - dispatch.get('probe_started_at', now) >= 60):
                raise ValueError('capability check expired or already completed')
            if not isinstance(probe, dict) or not all(probe.get(k) is True for k in checks):
                raise ValueError('host capability not verified')
            if not all(isinstance(probe.get(k), str) and probe[k].strip() for k in ('host', 'probe_id')):
                raise ValueError('observed host and probe ID required')
            dispatch.update(capability_state='ready', worker_ceiling=2 if task.get('inspection_policy') in {'lite_live_realtime_v1','lite_live_realtime_v2'} else 3, startup_failures=0)
            # Store capability booleans only, never transport data or arbitrary prose.
        elif action == 'degrade':
            dispatch.update(capability_state='degraded', worker_ceiling=0,
                            reduction_reason='host_unavailable')
        elif action == 'reconcile':
            if any(b['status'] in {'dispatching', 'cancelling'} for b in batches):
                raise ValueError('unknown launches or cancellations still require reconciliation')
            expected = {b['id']: b.get('host_task_id') for b in batches
                        if b['status'] in {'running', 'returned'}}
            observed = value.get('observed_batches')
            if not isinstance(observed, dict) or observed != expected:
                raise ValueError('all live host task bindings must be observed')
            dispatch['reconcile_required'] = False
        else:
            batch = row(conn, store.session_id, value.get('batch_id'))
            if not batch or batch['generation'] != value.get('generation') or batch.get('executor') != 'child':
                raise ValueError('stale or missing host batch')
            host_id = value.get('host_task_id')
            if batch.get('host_task_id') and host_id != batch['host_task_id']:
                raise ValueError('host task binding mismatch')
            state = batch['status']
            if action == 'dispatching':
                if state != 'allocated':
                    raise ValueError('batch already dispatched')
                if (dispatch.get('capability_state') != 'ready'
                        or dispatch.get('worker_ceiling', 0) <= 0
                        or dispatch.get('reconcile_required')
                        or any(b['id'] != batch['id'] and b['status'] in {'dispatching', 'cancelling'} for b in batches)):
                    raise ValueError('worker dispatch disabled or reconciliation required')
                if sum(b.get('executor') == 'child' and b['status'] in ACTIVE for b in batches) > dispatch['worker_ceiling']:
                    raise ValueError('worker ceiling exceeded')
                batch.update(status='dispatching', dispatch_at=now)
            elif action in {'bound', 'started'}:
                allowed = {'dispatching', 'cancelling'} if action == 'bound' else {'dispatching'}
                if state not in allowed or not isinstance(host_id, str) or not host_id.strip():
                    raise ValueError('observed host task ID required')
                if any(b['id'] != batch['id'] and b.get('host_task_id') == host_id for b in batches):
                    raise ValueError('host task ID already bound')
                batch['host_task_id'] = host_id
                if action == 'started':
                    if value.get('running_confirmed') is not True:
                        raise ValueError('host execution must be observed; a queued ID is not running')
                    batch.update(status='running', started_at=now)
                    dispatch['startup_failures'] = 0
                    if sum(b['id'] != batch['id'] and b.get('executor') == 'child'
                           and b['status'] == 'running' for b in batches) >= 2:
                        dispatch.setdefault('third_trial_at', now)
            elif action == 'returned':
                if state not in {'running', 'returned'}:
                    raise ValueError('batch not running')
                batch.update(status='returned')
                batch.setdefault('returned_at', now)
            elif action == 'cancel_requested':
                if state not in {'dispatching', 'running', 'cancelling'}:
                    raise ValueError('batch not cancellable')
                batch['status'] = 'cancelling'
            elif action in {'failed', 'cancelled'}:
                if state not in ACTIVE or value.get('exit_confirmed') is not True:
                    raise ValueError('host exit must be confirmed')
                # A failed launch without an ID needs explicit confirmation that no host task exists.
                if not batch.get('host_task_id') and value.get('not_started_confirmed') is not True:
                    raise ValueError('unknown launch cannot release its slot')
                batch.update(status='retry', failures=batch.get('failures', 0) + 1)
                dispatch['stable_since'] = now
                if action == 'failed' and 'started_at' not in batch:
                    dispatch['startup_failures'] = dispatch.get('startup_failures', 0) + 1
                    if dispatch['startup_failures'] >= 2:
                        dispatch.update(worker_ceiling=0, reduction_reason='startup_failures')
                if value.get('resource_limited'):
                    dispatch.update(worker_ceiling=min(dispatch.get('worker_ceiling', 3), 2),
                                    reduction_reason='resource_limited')
            else:
                raise ValueError('unsupported dispatcher action')
            save(conn, store.session_id, batch)
        retire_excess_allocations(conn, store, dispatch, rows(conn, store.session_id))
        task['review_dispatch'] = dispatch
        store._set_task(conn, task)
        result = {'status':'dispatcher_updated', 'next_action':{
            'dispatching':'spawn-review-worker','bound':'observe-review-worker',
            'returned':'review-submit','cancel_requested':'cancel-review-worker'}.get(action,'review-next')}
        from runtime.review_execution import bind_result
        bind_result(store, conn, result)
    return result


def paired_rounds(batches):
    """Disjoint successful pairs whose host execution intervals genuinely overlap."""
    successful = sorted([b for b in batches if b.get('executor') == 'child'
                         and b['status'] == 'done' and 'started_at' in b and 'returned_at' in b],
                        key=lambda b: b['started_at'])
    used, pairs = set(), []
    for first in successful:
        if first['id'] in used:
            continue
        second = next((b for b in successful if b['id'] not in used and b['id'] != first['id']
                       and max(first['started_at'], b['started_at']) < min(first['returned_at'], b['returned_at'])), None)
        if second:
            used.update((first['id'], second['id']))
            pairs.append((first, second))
    return pairs


def sample_backlog(dispatch, ready, now):
    from runtime.store import interval_ms
    samples = dispatch.setdefault('backlog_samples', [])
    if not samples or now - samples[-1]['at'] >= 3:
        samples.append({'at':now,'ms':interval_ms(ready)})


def observe_backlog(store, now=None):
    """Watcher observations are not coordinator heartbeats or review successes."""
    from runtime import full_live
    now = time.time() if now is None else now
    task = store.task()
    if not enabled(task) or task.get('finishing', {}).get('phase') == 'completed':return
    samples = task.get('review_dispatch', {}).get('backlog_samples', [])
    if samples and now-samples[-1]['at'] < 3:return
    with store.connection(True) as conn:
        from runtime.finishing import advance
        advance(store,conn,now)
        task=store._task(conn)
        if task.get('finishing', {}).get('phase') == 'completed':return
        dispatch=task.setdefault('review_dispatch', {})
        ready=[s for s in store._segments(conn) if s['review_status']=='pending' and full_live.ready(task,s)]
        sample_backlog(dispatch,ready,now)
        dispatch['backlog_samples']=[s for s in dispatch['backlog_samples'] if s['at'] >= now-600]
        store._set_task(conn,task)


def refresh(dispatch, batches, segments, ready, now):
    from runtime.store import interval_ms
    if dispatch.get('capability_state') == 'checking' and now - dispatch['probe_started_at'] >= 60:
        dispatch.update(capability_state='degraded', worker_ceiling=0, reduction_reason='capability_timeout')
    pairs = paired_rounds(batches)
    dispatch['parallel_verified'] = bool(pairs)
    stable = dispatch.get('stable_since', 0)
    dispatch['stable_pair_rounds'] = sum(min(a['started_at'], b['started_at']) >= stable for a, b in pairs)
    dispatch['acceptance_state'] = 'parallel_unverified'
    sample_backlog(dispatch,ready,now)
    samples = dispatch['backlog_samples']
    trial = dispatch.get('third_trial_at')
    if trial is not None and now >= trial + 300 and not dispatch.get('third_evaluated'):
        window = [s for s in samples if trial - 300 <= s['at'] <= trial + 300]
        continuous = (window and window[0]['at'] <= trial - 297 and window[-1]['at'] >= trial + 297
                      and all(s['ms'] > 0 for s in window)
                      and all(b['at'] - a['at'] <= 6 for a, b in zip(window, window[1:])))
        dispatch['third_evaluated'] = True
        if continuous:
            before = interval_ms([s for s in segments if trial - 300 < s.get('speech_review_completed_at', 0) <= trial])
            after = interval_ms([s for s in segments if trial < s.get('speech_review_completed_at', 0) <= trial + 300])
            if (before <= 0 or after < before * 1.2) and dispatch.get('worker_ceiling', 3) > 2:
                dispatch.update(worker_ceiling=2, reduction_reason='no_throughput_gain')
        else:
            dispatch['throughput_observation'] = 'unknown'
            if dispatch.get('worker_ceiling', 3) > 2:
                dispatch.update(worker_ceiling=2,reduction_reason='insufficient_throughput_observation')
    # Keep the fixed trial baseline until evaluation, including a delayed poll.
    cutoff = trial - 300 if trial is not None and not dispatch.get('third_evaluated') else now - 600
    dispatch['backlog_samples'] = [s for s in samples if s['at'] >= cutoff]


def selection(dispatch, batches, waiting, finish, now):
    """Unknown host outcomes block new children, but never consume unowned evidence."""
    active = [b for b in batches if b['status'] in ACTIVE]
    unknown = any(b['status'] in {'dispatching', 'cancelling'} for b in active)
    mains = [b for b in active if b.get('executor') == 'main']
    allocated = [b for b in active if b['status'] == 'allocated']
    if allocated:
        return allocated, None, dispatch.get('slots', 1)
    if mains:
        return [], None, dispatch.get('slots', 1)
    eligible = (dispatch.get('capability_state') == 'ready' and dispatch.get('worker_ceiling', 0) > 0
                and not unknown and not dispatch.get('reconcile_required') and not finish)
    if not eligible:
        return [], 'main' if waiting else None, 1
    success = any(b.get('executor') == 'child' and b['status'] == 'done' for b in batches)
    slots = 2 if success else 1
    oldest = max([now - s.get('asr_ready_at', now) for s in waiting] or [0])
    if dispatch.get('stable_pair_rounds', 0) >= 3 and oldest > 60:
        slots = 3
    slots = min(slots, dispatch.get('worker_ceiling', 3))
    if len(active) >= slots:
        return [], None, slots
    return [], 'child' if waiting else None, slots
