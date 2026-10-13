"""Keep ordinary live work in order; bound overload and end-of-session work."""
from datetime import datetime

POLICY = 'lite_live_realtime_v1'
LATEST_POLICY = 'lite_live_realtime_v2'


def enabled(task):
    return task.get('kind', 'live') == 'live' and task.get('inspection_policy') in {POLICY, LATEST_POLICY}


def current(task):
    return task.get('kind', 'live') == 'live' and task.get('inspection_policy') == LATEST_POLICY


def skip(store, conn, segment, code, now):
    segment.update(review_status='skipped', skip_code=code, skip_reason=code, asr_final=True)
    store._write_segment(conn, segment['id'], segment)
    conn.execute("UPDATE media_jobs SET status='skipped',lease_token=NULL,lease_until=NULL,last_error_code=?,updated_at=? "
                 "WHERE session_id=? AND segment_id=? AND status NOT IN ('succeeded','failed','skipped')",
                 (code, now, store.session_id, segment['id']))


def advance(store, conn, task, now):
    if current(task):return advance_current(store, conn, task, now)
    from runtime import live_review, finishing
    from runtime.store import ASR_DONE, interval_ms
    state = task.get('finishing', {})
    if state.get('phase') == 'completed':
        return state
    live_review.initialize(conn)
    batches = [b for b in live_review.rows(conn, store.session_id) if b['status'] in live_review.ACTIVE]
    occupied = {int(sid) for b in batches for sid in b['targets']}
    segments = store._segments(conn)
    for segment in segments:
        if segment['review_status'] in {'done','skipped'}:continue
        if now >= segment.get('asr_execution_deadline_at', float('inf')) and segment['asr_status'] not in ASR_DONE:
            segment.update(asr_status='timed_out', asr_final=True, asr_diagnostic={'category':'ASR_EXECUTION_DEADLINE'})
            store._write_segment(conn, segment['id'], segment)
            conn.execute("UPDATE media_jobs SET status='skipped',lease_token=NULL,lease_until=NULL,last_error_code='asr_deadline',updated_at=? "
                         "WHERE session_id=? AND segment_id=? AND kind='audio'", (now, store.session_id, segment['id']))
        if (task.get('image_inspection') is False and segment['id'] not in occupied
                and segment['asr_status'] in ASR_DONE and not any(str(u.get('text','')).strip() for u in segment.get('subtitles', []))):
            skip(store, conn, segment, 'NO_SPEECH_EVIDENCE', now)

    ending = task.get('stop_requested') or task.get('capture_status') in finishing.TERMINAL or state
    if not ending:
        waiting = sorted((s for s in segments if s['review_status'] not in {'done','skipped'} and s['id'] not in occupied),
                         key=lambda s: (s['start_ms'], s['id']))
        if interval_ms(waiting) > 180000:
            retained = 0
            for segment in reversed(waiting):
                retained += segment['end_ms']-segment['start_ms']
                if retained > 120000:skip(store, conn, segment, 'LIVE_BACKLOG_SKIPPED', now)
        return state

    started = state.get('started_at', now)
    for value in (task.get('stop_requested_at'), task.get('live_ended_at')):
        if value:
            try:
                started = min(started, float(value) if isinstance(value, (int, float)) else datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp())
            except (ValueError, TypeError):pass
    if not task.get('stop_requested') and task.get('capture_epoch') and task.get('capture_end_ms') is not None:
        started = min(started, task['capture_epoch'] + task['capture_end_ms']/1000)
    if state.get('mode') != 'bounded':
        if batches:
            targets = [int(sid) for sid in min(batches, key=lambda b:(b['status']=='allocated', b['created_at']))['targets']]
        else:
            targets = []
        state = {'phase':'draining', 'mode':'bounded', 'started_at':started, 'review_targets':targets,
                 'deadline_at':started+30, 'quality_deadline_at':started+60, 'recap_deadline_at':started+120}
        task['finishing'] = state
        task.setdefault('monitor_ended_at', started)
        task.setdefault('monitored_duration_ms', max(0, round((started-task.get('capture_epoch', started))*1000)))
        finishing.freeze_media(store, conn, task, now)
    expired = now >= state['deadline_at'] or task.get('stop_immediately')
    for segment in store._segments(conn):
        if segment['review_status'] not in {'done','skipped'} and (expired or segment['id'] not in state['review_targets']):
            skip(store, conn, segment, 'USER_DISCARD' if task.get('stop_immediately') else 'LIVE_FINISH_SKIPPED', now)
    if task.get('stop_immediately') and task.get('stop_audit'):
        task['stop_audit']['discarded_segments'] = sum(s.get('skip_code') == 'USER_DISCARD' for s in store._segments(conn))
    settled = all(s['review_status'] in {'done','skipped'} for s in store._segments(conn))
    if settled:
        state.update(phase='completed', completed_at=now, reason='deadline' if expired else 'reviewed')
    for batch in batches:
        if settled or not set(map(int, batch['targets'])).intersection(state['review_targets']):
            running = batch.get('executor') == 'child' and batch['status'] in {'dispatching','running','cancelling'}
            batch.update(status='cancelling' if running else 'expired')
            live_review.save(conn, store.session_id, batch)
    task['finishing'] = state
    store._set_task(conn, task)
    return state


def advance_current(store, conn, task, now):
    """Drain every captured segment; only explicit immediate stop discards work."""
    from runtime import finishing
    from runtime.store import ASR_DONE, FRAME_DONE
    state = task.get('finishing', {})
    if state.get('phase') == 'completed':return state
    segments = store._segments(conn)
    terminal = task.get('capture_status') in finishing.TERMINAL
    if task.get('stop_immediately'):
        for segment in segments:
            if segment['review_status'] not in {'done','skipped'}:
                skip(store, conn, segment, 'USER_DISCARD', now)
        if task.get('stop_audit'):
            task['stop_audit']['discarded_segments'] = sum(s.get('skip_code') == 'USER_DISCARD' for s in store._segments(conn))
    elif terminal and task.get('worker_status') in {'done','failed','stopped'}:
        for segment in segments:
            if segment['review_status'] in {'done','skipped'}:continue
            changed=False
            if segment['asr_status'] not in ASR_DONE:
                segment.update(asr_status='failed', asr_final=True,
                               asr_diagnostic={'category':'ASR_WORKER_STOPPED'})
                changed=True
            if segment['frame_status'] not in FRAME_DONE:
                segment['frame_status']='unavailable'
                changed=True
            if changed:
                store._write_segment(conn, segment['id'], segment)
    if not (task.get('stop_requested') or terminal):return state
    if not state:
        state = {'phase':'draining','mode':'drain','started_at':now}
    if task.get('stop_immediately'):state['mode']='immediate'
    segments = store._segments(conn)
    state['waiting_for_asr'] = any(s['review_status'] not in {'done','skipped'} and s['asr_status'] not in ASR_DONE for s in segments)
    state['waiting_for_frames'] = any(s['review_status'] not in {'done','skipped'} and s['frame_status'] == 'pending' for s in segments)
    if terminal and task.get('worker_status') in {'done','failed','stopped'} and all(s['review_status'] in {'done','skipped'} for s in segments):
        state.update(phase='completed',completed_at=now,reason='user_immediate' if task.get('stop_immediately') else 'drained')
    task['finishing']=state
    store._set_task(conn,task)
    return state
