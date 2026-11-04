"""Drain saved live evidence with progress-based waits and one fenced review retry."""
import hashlib
import json
import math
import uuid

IDLE_SECONDS = 120
MAX_SECONDS = 900


def fingerprint(segments, batches):
    # Process heartbeats and repeated polls are not evidence of useful progress.
    value = [[s['id'], s['asr_status'], bool(s.get('asr_task_id')), s['frame_status'],
              s.get('evidence_revision'), s['review_status'], bool(s.get('review_result'))] for s in segments]
    value += [[b['id'], b['generation'], b['status'], b.get('review_progress_at')] for b in batches]
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def reason(segment, batches):
    from runtime.store import ASR_DONE, FRAME_DONE
    if segment['asr_status'] not in ASR_DONE:return 'asr_result_timeout'
    if segment.get('drain_media_failure'):return segment['drain_media_failure']
    if not segment.get('frames') and not any(str(u.get('text', '')).strip() for u in segment.get('subtitles', [])):
        return 'asr_failed' if segment['asr_status'] not in {'success', 'no_audio'} else 'no_transcript'
    if segment['frame_status'] not in FRAME_DONE:return 'frames_timeout'
    if any(str(segment['id']) in b['targets'] for b in batches):return 'review_timeout'
    return 'review_not_dispatched'


def retire(store, conn, batch, now):
    from runtime import live_review
    running = batch.get('executor') == 'child' and batch['status'] in {'dispatching', 'running', 'cancelling'}
    batch.update(status='cancelling' if running else 'retry', generation=batch['generation']+1,
                 expired_reason='LIVE_BATCH_REVIEW_TIMEOUT', review_progress_at=now)
    # A running/unknown child keeps its occupancy until cancellation is acknowledged.
    live_review.save(conn, store.session_id, batch)


def advance(store, conn, task, state, batches, segments, stalled, now):
    from runtime import finishing, live_review
    from runtime.realtime_policy import skip
    from runtime.store import ASR_DONE, FRAME_DONE
    started = state['started_at']
    from runtime.realtime_policy import cloud_limited, CLOUD_DRAIN_SECONDS
    hard = started + (CLOUD_DRAIN_SECONDS if cloud_limited(task) else MAX_SECONDS)
    signature = fingerprint(segments, batches)
    if state.get('drain_version') != 1:
        state.update(drain_version=1, progress_signature=signature, last_progress_at=started,
                     deadline_at=min(hard, started+IDLE_SECONDS), recovery_attempts=0)
    elif signature != state.get('progress_signature'):
        state.update(progress_signature=signature, last_progress_at=now,
                     deadline_at=min(hard, now+IDLE_SECONDS))
    state['hard_deadline_at'] = hard
    task['finishing'] = state
    immediate = bool(task.get('stop_immediately'))
    expired = now >= hard
    pending = [s for s in segments if s['review_status'] not in {'done', 'skipped'}]
    blockers = state.setdefault('blocking_counts', {})

    def abandon(segment, why):
        blockers[why] = blockers.get(why, 0)+1
        segment['drain_blocking_reason'] = why
        skip(store, conn, segment, 'USER_DISCARD' if immediate else 'LIVE_FINISH_SKIPPED', now)

    if immediate or expired:
        why = 'user_discard' if immediate else 'drain_total_timeout'
        for segment in pending:abandon(segment, why)
        state['blocking_reason'] = why
    else:
        stalled_ids = {int(sid) for b in stalled for sid in b['targets']}
        idle = now >= state['deadline_at']
        retry_ids = set()
        for segment in pending:
            if not idle and segment['id'] not in stalled_ids:continue
            why = reason(segment, batches)
            has_text = any(str(u.get('text', '')).strip() for u in segment.get('subtitles', [])) or bool(segment.get('frames'))
            # A successful remote submit is not a recognition result. Honor the
            # already-frozen query budget, reserving a review window within the cap.
            remote_deadline = segment.get('asr_cloud_deadline_at')
            if (why == 'asr_result_timeout' and segment.get('asr_task_id')
                    and task.get('worker_status') not in {'done','failed','stopped'}
                    and type(remote_deadline) in (int,float) and math.isfinite(remote_deadline)
                    and now < min(remote_deadline, hard-IDLE_SECONDS)):
                state['deadline_at'] = max(state['deadline_at'], min(remote_deadline, hard-IDLE_SECONDS))
                continue
            # Partial saved speech can still be reviewed after media failure.
            if has_text and why in {'asr_result_timeout', 'frames_timeout'}:
                segment['drain_media_failure'] = why
                if segment['asr_status'] not in ASR_DONE:
                    segment.update(asr_status='timed_out', asr_final=True,
                                   asr_diagnostic={'category':'ASR_FINISH_TIMEOUT'})
                if segment['frame_status'] not in FRAME_DONE:segment['frame_status']='unavailable'
                conn.execute("UPDATE media_jobs SET status='skipped',lease_token=NULL,lease_until=NULL,last_error_code='drain_media_timeout',updated_at=? "
                             "WHERE session_id=? AND segment_id=? AND status NOT IN ('succeeded','failed','skipped')",
                             (now, store.session_id, segment['id']))
            if has_text and not segment.get('drain_review_retries'):
                segment.update(review_status='pending', drain_review_retries=1)
                segment.pop('review_defer', None)
                segment.pop('claim_token', None);segment.pop('lease_until', None)
                store._write_segment(conn, segment['id'], segment)
                retry_ids.add(segment['id'])
            else:
                abandon(segment, why)
        if retry_ids:
            for batch in batches:
                if retry_ids.intersection(map(int, batch['targets'])):retire(store, conn, batch, now)
            state['recovery_attempts'] += 1
            state.update(last_progress_at=now, deadline_at=min(hard, now+IDLE_SECONDS))
        # A stopped media worker cannot finish pending jobs. Preserve any partial
        # transcript for review instead of prematurely completing the whole task.
        if task.get('capture_status') in finishing.TERMINAL and task.get('worker_status') in {'done','failed','stopped'}:
            for segment in store._segments(conn):
                if segment['review_status'] in {'done','skipped'}:continue
                if segment['asr_status'] not in ASR_DONE:
                    segment.update(asr_status='failed', asr_final=True,
                                   asr_diagnostic={'category':'ASR_WORKER_STOPPED'})
                    segment['drain_media_failure'] = 'worker_stopped'
                if segment['frame_status'] not in FRAME_DONE:segment['frame_status']='unavailable'
                store._write_segment(conn, segment['id'], segment)

    segments = store._segments(conn)
    from runtime.realtime_policy import skip_empty
    skip_empty(store, conn, task, batches, segments, now)
    remaining = [s for s in segments if s['review_status'] not in {'done','skipped'}]
    terminal = task.get('capture_status') in finishing.TERMINAL
    settled = not remaining and terminal and task.get('worker_status') in {'done','failed','stopped'}
    exhausted = not remaining and bool(blockers)
    if immediate or expired or settled or exhausted:
        finishing.freeze_media(store, conn, task, now)
        for batch in live_review.rows(conn, store.session_id):
            if batch['status'] in live_review.ACTIVE:
                batch.update(status='cancelling' if batch.get('executor')=='child' and batch['status'] in {'dispatching','running','cancelling'} else 'expired',
                             generation=batch['generation']+1)
                live_review.save(conn, store.session_id, batch)
        state.update(phase='completed', completed_at=now, reason='USER_DISCARD' if immediate else 'drained' if settled and not blockers else 'LIVE_FINISH_SKIPPED')
        if immediate and task.get('stop_audit'):
            task['stop_audit']['discarded_segments'] = sum(s.get('skip_code')=='USER_DISCARD' for s in segments)
        reviewed = sum(s['review_status']=='done' and bool(s.get('review_result')) for s in segments)
        unresolved = sum(s['review_status']!='done' or bool(s.get('drain_media_failure')) for s in segments)
        why = state.get('blocking_reason') or next(iter(blockers), None)
        if not why:why = next((s.get('drain_media_failure') for s in segments if s.get('drain_media_failure')), None)
        why = why or ('no_captured_content' if not segments else 'none' if not unresolved else 'incomplete_evidence')
        state['blocking_reason'] = why
        success = why == 'none'
        state['diagnostic'] = dict(failure_component='finishing', failure_reason='drain_completed' if success else 'drain_blocked',
            blocking_reason=why, recovery_outcome='success' if success else 'failed',
            recovery_action='redispatch_review' if state['recovery_attempts'] else 'continue_processing',
            recovery_attempts=state['recovery_attempts'], recovery_elapsed_ms=max(0, round((now-started)*1000)),
            reviewed_segments=reviewed, unresolved_segments=unresolved,
            diagnostic_event_id=str(uuid.uuid5(uuid.UUID(hex=task.get('task_id') or task['id']), 'stop-drain:'+str(started))))
    else:
        state['waiting_for_asr'] = any(s['asr_status'] not in ASR_DONE for s in remaining)
        state['waiting_for_frames'] = any(s['frame_status'] not in FRAME_DONE for s in remaining)
    # Include our own mutations in the baseline so a retry alone does not grant
    # another window on the following poll. Heartbeats never renew this deadline.
    state['progress_signature'] = fingerprint(store._segments(conn), [b for b in live_review.rows(conn, store.session_id) if b['status'] in live_review.ACTIVE])
    task['finishing'] = state
    store._set_task(conn, task)
    return state
