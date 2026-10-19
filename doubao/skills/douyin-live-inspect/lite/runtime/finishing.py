"""Drain live evidence by default; explicit cancellation fences writes atomically."""
import json
import math
import time
from datetime import datetime

REASON = '结束后未完成检测'
TERMINAL = {'ended', 'stopped', 'failed'}
IMMEDIATE_REASON = '用户主动停止，未完成检测'


def enabled(task):
    return task.get('kind', 'live') == 'live' or (task.get('pipeline_version') == 2 and bool(task.get('stop_requested')))


def freeze_media(store, conn, task, now):
    """Close media writes, retaining every saved caption for semantic review."""
    if task.get('media_frozen') or task.get('finishing', {}).get('phase') == 'completed':return
    segments = store._segments(conn)
    start = task.get('capture_epoch')
    if not start:
        try:start = datetime.fromisoformat(task['created_at'].replace('Z', '+00:00')).timestamp()
        except (KeyError, ValueError):start = now
    if not task.get('stop_requested') and task.get('capture_epoch') and task.get('capture_end_ms') is not None:
        now=min(now,start+task['capture_end_ms']/1000)
    now = task.get('monitor_ended_at', now)
    task.update(media_frozen=True, media_frozen_at=time.time(), monitor_ended_at=now,
                monitored_duration_ms=max(0, round((now-start)*1000)),
                capture_end_ms=task.get('capture_end_ms') if task.get('capture_end_ms') is not None else
                    max([task.get('capture_observed_ms', 0)] + [s['end_ms'] for s in segments]),
                recovery_state=None)
    for segment in segments:
        if segment['asr_status'] not in {'success','no_audio'}:
            segment.update(asr_status='failed', asr_final=True)
            segment.setdefault('asr_diagnostic', {'category':'ASR_STOPPED'})
        if segment['frame_status'] not in {'success','disabled','not_required','not_scheduled'}:
            segment['frame_status']='unavailable'
        if not any(str(u.get('text','')).strip() for u in segment.get('subtitles', [])) and segment['review_status'] not in {'done','skipped'}:
            segment.update(review_status='skipped', skip_reason='结束时无可用语音文字', skip_code='NO_SPEECH_EVIDENCE')
        elif segment['review_status'] == 'deferred':
            segment['review_status']='pending'
            segment.pop('review_defer', None)
        store._write_segment(conn, segment['id'], segment)
    conn.execute("""UPDATE media_jobs SET status='skipped',lease_token=NULL,lease_until=NULL,
        last_error_code='media_frozen',updated_at=? WHERE session_id=?
        AND status IN ('queued','running','retry_wait','submitting','submitted')""", (now,store.session_id))
    store._set_task(conn,task)


def advance(store, conn, now=None):
    now = time.time() if now is None else now
    task = store._task(conn)
    from runtime.stop_signal import read as read_stop, request as signal_stop
    signal = read_stop(store.root)
    if task.get('kind','live') == 'live' and signal and not task.get('stop_requested'):
        task.update(stop_requested=True,stop_requested_at=signal['requested_at'],bounded_finishing=True)
        task.setdefault('stop_reason', signal['reason'])
        store._set_task(conn,task)
    if task.get('kind','live') == 'live' and task.get('freeze_on_end') and task.get('capture_status') in TERMINAL and not signal:
        signal_stop(store.root,origin='runtime',reason='source_ended',instruction=None)
    from runtime import realtime_policy
    if realtime_policy.enabled(task) or task.get('bounded_finishing'):
        return realtime_policy.advance(store, conn, task, now)
    if task.get('kind','live') == 'live' and task.get('freeze_on_end') and task.get('capture_status') in TERMINAL:
        freeze_media(store,conn,task,now)
    if task.get('media_frozen'):return advance_live(store,conn,task,now)
    from runtime import full_live
    if full_live.enabled(task):return full_live.advance(store,conn,task,now)
    from runtime.sampling import enabled as sampled, tick
    if sampled(task):return tick(store, conn, now)
    if task.get('kind','live')=='live' and (task.get('stop_immediately') or task.get('finishing_policy')=='drain'):
        return advance_live(store,conn,task,now)
    if not task.get('inspection_policy') and task.get('pipeline_version') != 2:
        return legacy_advance(store, conn, now)
    if task.get('kind', 'live') == 'live':
        return advance_live(store, conn, task, now)
    if not enabled(task):
        return {}
    state = task.get('finishing', {})
    if state.get('phase') == 'completed':
        return state
    terminal = task.get('capture_status') in TERMINAL
    if not state and not (task.get('stop_requested') or task.get('live_ended_at') or terminal):
        return {}
    segments = store._segments(conn)
    if not state:
        # Historical completed reports remain untouched.
        if terminal and task.get('worker_status') in {'done', 'failed'} and all(s['review_status'] == 'done' for s in segments):
            return {}
        started = now
        for value in (task.get('stop_requested_at'), task.get('live_ended_at'), task.get('finished_at')):
            if value:
                try:
                    started = min(started, float(value) if isinstance(value, (float, int)) else datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp())
                except (ValueError, TypeError):
                    pass
        state = {'phase': 'draining', 'started_at': started, 'deadline_at': started + 30}
    # ASR failover may need the existing bounded model download plus queued
    # inference. Give it a fixed budget, never a sliding heartbeat deadline.
    if task.get('pipeline_version')==2:
        media_pending = not terminal or any(s['review_status'] not in {'done','skipped'} and
            (s['asr_status'] not in {'success','no_audio','failed','timed_out','submission_unknown'} or
             s['frame_status'] not in {'success','failed'}) for s in segments)
        if 'media_deadline_at' not in state:
            state.update(media_deadline_at=state['started_at']+30, waiting_for_asr=True)
        if state.get('waiting_for_asr') and (not media_pending or now>=state['media_deadline_at']):
            for s in segments:
                if s['review_status'] in {'done','skipped'}:continue
                if s['asr_status'] not in {'success','no_audio','failed','timed_out','submission_unknown'}:
                    s.update(asr_status='failed',subtitles=[],asr_final=True,asr_diagnostic={'category':'ASR_FINISH_TIMEOUT'})
                if s['frame_status'] not in {'success','failed'}:s['frame_status']='failed'
                store._write_segment(conn,s['id'],s)
            state.update(waiting_for_asr=False,deadline_at=min(now,state['media_deadline_at'])+30)
        elif state.get('waiting_for_asr'):
            state['deadline_at']=state['media_deadline_at']
    elif task.get('asr_policy')=='local_first' and task.get('asr_backend')=='local':
        from runtime.media import asr_needs_processing
        from runtime.model_preparation import MAX_SECONDS
        from runtime.mediakit import config
        active_segments=[s for s in segments if s['review_status'] not in {'done','skipped'}]
        pending_asr = any(s.get('asr_status') in {'pending','running','fallback_pending'}
                          or asr_needs_processing(s) for s in active_segments)
        pending_frames = any(s.get('frame_status') not in {'success','failed'} for s in active_segments)
        pending = pending_asr or pending_frames
        active = task.get('worker_status') not in {'failed','stopped','done','setup_pending'}
        if pending and active and 'asr_deadline_at' not in state:
            remote_budget = max(0, float(config(task, 'asr_timeout_seconds', 600))) + 60
            # Include one final capture segment that may still be registering.
            durations = [(s['end_ms']-s['start_ms'])/1000 for s in segments] + [180]
            from runtime.frame_router import CLOUD_SECONDS
            interval = max(1, float(config(task,'frame_interval_seconds',20)))
            budget = MAX_SECONDS + sum(remote_budget + 2 * (duration + 160)
                + 3 * (CLOUD_SECONDS + 90 + 60 * max(1,math.ceil(duration/interval))) for duration in durations)
            state = {**state, 'asr_deadline_at': now + budget}
        waiting = pending and active and now < state.get('asr_deadline_at', 0)
        if waiting:
            state = {**state, 'waiting_for_asr': pending_asr, 'waiting_for_frames': pending_frames,
                     'deadline_at': state['asr_deadline_at']}
        elif state.get('waiting_for_asr') or state.get('waiting_for_frames'):
            state = {**state, 'waiting_for_asr': False, 'waiting_for_frames': False, 'deadline_at': now + 30}
    expired = now >= state['deadline_at']
    if expired:
        for segment in segments:
            if segment['review_status'] in {'done', 'skipped'}:
                continue
            segment.update(review_status='skipped', skip_reason=REASON)
            store._write_segment(conn,segment['id'],segment)
        conn.execute("""UPDATE media_jobs SET status='skipped',lease_token=NULL,lease_until=NULL,
                        last_error_code='finish_deadline',updated_at=?
                        WHERE session_id=? AND status IN ('queued','running','retry_wait','submitting','submitted')""", (now, store.session_id))
    settled = all(s['review_status'] in {'done', 'skipped'} for s in segments)
    capture_closed = terminal and (task.get('capture_start_ms') is None or task.get('capture_end_ms') is not None or task.get('worker_status') in {'done','failed','stopped'})
    if capture_closed and (expired or (settled and task.get('worker_status') in {'done', 'failed'})):
        state = {**state, 'phase': 'completed', 'completed_at': now,
                 'reason': 'deadline' if expired else 'drained'}
    if task.get('finishing') != state:
        task['finishing'] = state
        store._set_task(conn, task)
    return state


def advance_live(store, conn, task, now):
    state = task.get('finishing', {})
    # Never reopen a sealed historical report or reinterpret its old deadline.
    if state.get('phase') == 'completed':
        return state
    terminal = task.get('capture_status') in TERMINAL
    if not state and not (task.get('stop_requested') or task.get('live_ended_at') or terminal):
        return {}
    immediate = bool(task.get('stop_immediately'))
    segments = store._segments(conn)
    # Already settled legacy tasks have no finishing state; keep their existing semantics.
    if not state and not immediate and terminal and task.get('worker_status') in {'done','failed'} and all(s['review_status'] in {'done','skipped'} for s in segments):
        return {}
    active = [s for s in segments if s['review_status'] not in {'done', 'skipped'}]
    from runtime.store import ASR_DONE, FRAME_DONE
    state = {'phase': 'draining', 'started_at': state.get('started_at', now),
             'mode': 'immediate' if immediate else 'drain',
             'waiting_for_asr': not immediate and any(s['asr_status'] not in ASR_DONE for s in active),
             'waiting_for_frames': not immediate and any(s['frame_status'] not in FRAME_DONE for s in active)}
    if immediate:
        for segment in active:
            segment.update(review_status='skipped', skip_reason=IMMEDIATE_REASON, skip_code='USER_DISCARD')
            store._write_segment(conn,segment['id'],segment)
        conn.execute("""UPDATE media_jobs SET status='skipped',lease_token=NULL,lease_until=NULL,
                        last_error_code='user_immediate',updated_at=?
                        WHERE session_id=? AND status IN ('queued','running','retry_wait','submitting','submitted')""", (now, store.session_id))
    capture_closed = terminal and (task.get('capture_start_ms') is None or task.get('capture_end_ms') is not None
                                  or task.get('worker_status') in {'done','failed','stopped'})
    if capture_closed and (immediate or (not active and task.get('worker_status') in {'done','failed','stopped'})):
        state.update(phase='completed', completed_at=now, reason='user_immediate' if immediate else 'drained')
    if immediate and task.get('stop_audit'):
        task['stop_audit']['discarded_segments'] = sum(s.get('skip_code') == 'USER_DISCARD' for s in store._segments(conn))
    if task.get('media_frozen'):
        state.update(waiting_for_asr=False, waiting_for_frames=False)
    if task.get('finishing') != state or (immediate and task.get('stop_audit')):
        task['finishing'] = state
        store._set_task(conn, task)
    return state


def message(task, finish, pending=0):
    """User-facing live completion policy, shared by CLI status and stop."""
    if task.get('inspection_policy') in {'lite_live_realtime_v1','lite_live_realtime_v2'} or task.get('bounded_finishing'):
        return '已结束采集，正在完成当前检测并生成质检报告和内容复盘。'
    from runtime.live_backlog import enabled as catch_up, MEDIA_SECONDS, FINISH_SECONDS
    from runtime.full_live import enabled as full
    if catch_up(task):
        return f'直播优先检测最新内容，积压时会跳过旧音频。停止后媒体处理最多 {MEDIA_SECONDS} 秒，抽检结果最多 {FINISH_SECONDS} 秒封板；报告注明未检范围，随后生成复盘。'
    if task.get('inspection_policy')=='lite_sample_v1':
        return '采集结束后最多收尾 60 秒，随后交付已完成的抽检结果和未检范围。质检报告先交付，再基于有限窗口生成复盘；如原对话中断，请回原对话续办。'
    if finish.get('mode') == 'immediate' or finish.get('reason') == 'user_immediate':
        return '已停止剩余检测，正在基于已完成的结果生成质检报告和内容复盘。未检测的内容会在报告中明确标注，不纳入质检结论。'
    if not pending and task.get('worker_status') in {'done', 'failed', 'stopped'}:
        return '已采集内容的判定已结束，正在生成质检报告和内容复盘；如有证据不足，报告将注明具体范围。'
    from runtime.diagnostics import failure_label
    failure = failure_label(task)
    prefix = (failure if failure.startswith('本地存储异常') else
              '媒体处理失败，采集已停止' if task.get('worker_status') == 'failed' and task.get('capture_status') != 'failed' else
              '直播已结束' if task.get('capture_status') == 'ended' else
              '采集异常结束' if task.get('capture_status') == 'failed' else
              '已停止采集' if task.get('capture_status') == 'stopped' else '已收到结束请求，正在停止采集')
    return prefix + ('，正在补齐画面与语音证据' if finish.get('waiting_for_asr') or finish.get('waiting_for_frames') else '') + '，正在继续检测已采集的剩余内容。检测完成后，将生成质检报告和内容复盘。如需停止剩余检测，请在对话中说“立即停止”；报告将保留已完成的结果，并注明未检测范围。'


def closed(state, now=None):
    return bool(state) and (state['phase'] == 'completed' or state.get('mode') == 'immediate' or
        (state.get('deadline_at') is not None and (time.time() if now is None else now) >= state['deadline_at']))


def summary(state, segments):
    if not state:
        return {}
    skipped = [s for s in segments if s['review_status'] == 'skipped']
    reviewed = [s for s in segments if s['review_status'] == 'done']
    return {**state, 'remaining_seconds': max(0, math.ceil(state['deadline_at'] - time.time())) if state.get('deadline_at') is not None and state['phase'] != 'completed' else 0 if state['phase'] == 'completed' else None,
            'pending_segments': len(segments) - len(skipped) - len(reviewed),
            'skipped_segments': len(skipped), 'reviewed_segments': len(reviewed),
            'skipped_ms': __import__('runtime.store',fromlist=['interval_ms']).interval_ms(skipped),
            'reviewed_ms': __import__('runtime.store',fromlist=['interval_ms']).interval_ms(reviewed)}

def legacy_enabled(task):
    return task.get('kind', 'live') == 'live' and task.get('delivery_mode', 'local_dashboard') == 'local_dashboard'

def legacy_advance(store, conn, now=None):
    now = time.time() if now is None else now
    task = store._task(conn)
    if not legacy_enabled(task):
        return {}
    state = task.get('finishing', {})
    if state.get('phase') == 'completed':
        return state
    terminal = task.get('capture_status') in TERMINAL
    if not state and not (task.get('stop_requested') or task.get('live_ended_at') or terminal):
        return {}
    segments = store._segments(conn)
    if not state:
        # Historical completed reports remain untouched.
        if terminal and task.get('worker_status') in {'done', 'failed'} and all(s['review_status'] == 'done' for s in segments):
            return {}
        started = now
        for value in (task.get('stop_requested_at'), task.get('live_ended_at'), task.get('finished_at')):
            if value:
                try:
                    started = min(started, float(value) if isinstance(value, (float, int)) else datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp())
                except (ValueError, TypeError):
                    pass
        state = {'phase': 'draining', 'started_at': started, 'deadline_at': started + 30}
    # ASR failover may need the existing bounded model download plus queued
    # inference. Give it a fixed budget, never a sliding heartbeat deadline.
    if task.get('asr_policy')=='local_first' and task.get('asr_backend')=='local':
        from runtime.media import asr_needs_processing
        from runtime.model_preparation import MAX_SECONDS
        from runtime.mediakit import config
        pending_asr = any(s.get('asr_status') in {'pending','running','fallback_pending'}
                          or asr_needs_processing(s) for s in segments)
        pending_frames = any(s.get('frame_status') not in {'success','failed'} for s in segments)
        pending = pending_asr or pending_frames
        active = task.get('worker_status') not in {'failed','stopped','done','setup_pending'}
        if pending and active and 'asr_deadline_at' not in state:
            remote_budget = max(0, float(config(task, 'asr_timeout_seconds', 600))) + 60
            # Include one final capture segment that may still be registering.
            durations = [(s['end_ms']-s['start_ms'])/1000 for s in segments] + [180]
            from runtime.frame_router import CLOUD_SECONDS
            interval = max(1, float(config(task,'frame_interval_seconds',20)))
            budget = MAX_SECONDS + sum(remote_budget + 2 * (duration + 160)
                + 3 * (CLOUD_SECONDS + 90 + 60 * max(1,math.ceil(duration/interval))) for duration in durations)
            state = {**state, 'asr_deadline_at': now + budget}
        waiting = pending and active and now < state.get('asr_deadline_at', 0)
        if waiting:
            state = {**state, 'waiting_for_asr': pending_asr, 'waiting_for_frames': pending_frames,
                     'deadline_at': state['asr_deadline_at']}
        elif state.get('waiting_for_asr') or state.get('waiting_for_frames'):
            state = {**state, 'waiting_for_asr': False, 'waiting_for_frames': False, 'deadline_at': now + 30}
    expired = now >= state['deadline_at']
    if expired:
        for segment in segments:
            if segment['review_status'] in {'done', 'skipped'}:
                continue
            segment.update(review_status='skipped', skip_reason=REASON)
            conn.execute('UPDATE segments SET data=? WHERE id=?', (json.dumps(segment, ensure_ascii=False), segment['id']))
        conn.execute("""UPDATE media_jobs SET status='skipped',lease_token=NULL,lease_until=NULL,
                        last_error_code='finish_deadline',updated_at=?
                        WHERE session_id=? AND status IN ('queued','running','retry_wait','submitting','submitted')""", (now, store.session_id))
    settled = all(s['review_status'] in {'done', 'skipped'} for s in segments)
    capture_closed = terminal and (task.get('capture_start_ms') is None or task.get('capture_end_ms') is not None or task.get('worker_status') in {'done','failed','stopped'})
    if capture_closed and (expired or (settled and task.get('worker_status') in {'done', 'failed'})):
        state = {**state, 'phase': 'completed', 'completed_at': now,
                 'reason': 'deadline' if expired else 'drained'}
    if task.get('finishing') != state:
        task['finishing'] = state
        store._set_task(conn, task)
    return state
