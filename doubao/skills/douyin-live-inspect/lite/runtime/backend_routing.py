"""Sticky task preferences; only a successful failover changes a route.

Generation checks prevent older concurrent segments from undoing a newer choice.
The frozen task identities and each segment's durable choice remain authoritative.
"""
import time


def choice(task, kind, default):
    return task.get(kind + '_route') or {'backend': default, 'generation': 0}


def promote(store, kind, backend, generation, default, *, job=None):
    from runtime.finishing import advance, closed
    with store.connection(True) as conn:
        if closed(advance(store, conn)): return False
        if job and not conn.execute("""SELECT 1 FROM media_jobs WHERE id=? AND session_id=?
                AND status='running' AND lease_token=? AND lease_until>?""",
                (job['id'], store.session_id, job['lease_token'], time.time())).fetchone():
            return False
        task = store._task(conn)
        route = choice(task, kind, default)
        if route['generation'] != generation or route['backend'] == backend: return False
        task[kind + '_route'] = {'backend': backend, 'generation': generation + 1}
        store._set_task(conn, task)
        return True


def credential_state(store):
    from runtime.credentials import status
    state = status(store.workspace_root)
    return state.get('version') or state['status']


def remote_choice(store, kind, key, *, now=None, budget=60):
    """Reserve one recovery probe atomically; capture never reserves probes.

    The caller journals this selection with its evidence before doing any I/O.
    Generations fence late results from concurrent work and expired probes.
    """
    now = time.time() if now is None else now
    version = credential_state(store)
    with store.connection(True) as conn:
        task = store._task(conn)
        state = dict(task.get(kind + '_remote_route') or {'generation': 0, 'state': 'closed'})
        local = 'ffmpeg' if kind == 'frames' else 'local'
        selected = {'backend': local, 'generation': state['generation'], 'key': str(key), 'credential_version': version}
        if state['state'] == 'closed':
            return {**selected, 'backend': 'mediakit'}
        if state.get('blocked_version') == version or now < state.get('retry_at', 0):
            return selected
        if state.get('probe_key') is not None:
            if now < state.get('probe_deadline_at', 0):
                return selected
            state['generation'] += 1
        state.update(state='half_open', probe_key=str(key), probe_deadline_at=now + budget)
        task[kind + '_remote_route'] = state
        store._set_task(conn, task)
        return {**selected, 'backend': 'mediakit', 'generation': state['generation']}


def remote_result(store, kind, selection, success, *, category=None, now=None, job=None):
    """Only the current generation may close/open a circuit; no raw diagnostics."""
    if selection.get('backend') != 'mediakit': return
    now = time.time() if now is None else now
    with store.connection(True) as conn:
        from runtime.finishing import advance, closed
        if closed(advance(store, conn)): return
        if job and not conn.execute("SELECT 1 FROM media_jobs WHERE id=? AND session_id=? "
                "AND status='running' AND lease_token=? AND lease_until>?",
                (job['id'],store.session_id,job['lease_token'],time.time())).fetchone():return
        task = store._task(conn)
        state = dict(task.get(kind + '_remote_route') or {'generation': 0, 'state': 'closed'})
        if state['generation'] != selection['generation']: return
        if state.get('probe_key') is not None and state['probe_key'] != selection['key']: return
        if success:
            if state['state'] == 'closed': return
            state = {'state': 'closed', 'generation': state['generation'] + 1}
        else:
            state = {'state': 'open', 'generation': state['generation'] + 1, 'retry_at': now + 60}
            if category in {'authentication_rejected', 'credentials_unavailable', 'CLOUD_ASR_AUTH_UNAVAILABLE'}:
                state['blocked_version'] = selection['credential_version']
        task[kind + '_remote_route'] = state
        store._set_task(conn, task)
