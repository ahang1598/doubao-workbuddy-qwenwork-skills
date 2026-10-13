"""Lossy catch-up policy for live v2 sampling; durable gaps fence retries."""
import time

MAX_BACKLOG_MS = 30000
KEEP_MS = 10000
MEDIA_SECONDS = 10
FINISH_SECONDS = 30
BACKLOG = 'ASR_BACKLOG_SKIPPED'
FINISH = 'ASR_FINISH_TIMEOUT'


def enabled(task):
    return (task.get('kind') == 'live' and task.get('pipeline_version') == 2
            and task.get('inspection_policy') == 'lite_sample_v1'
            and (task.get('finishing', {}).get('phase') != 'completed'
                 or task.get('live_backlog_policy') == 'latest_v1'))


def captured_end(task):
    return max(task.get('capture_observed_ms', 0),
               task.get('capture_active_span', {}).get('end_ms', 0))


def remaining(task, maximum):
    if not enabled(task):return maximum
    deadline = task.get('finishing', {}).get('media_deadline_at')
    return maximum if deadline is None else max(0, min(maximum, deadline-time.time()))


def gap_fields(start, end, code):
    return dict(asr_status='failed', asr_final=True, subtitles=[],
                asr_diagnostic={'category':code}, asr_gap_code=code,
                speech_gaps=[{'start_ms':start, 'end_ms':end, 'reason':code}])


def expire(store, conn, task, raw, state, now):
    """Run inside the same transaction as evidence updates, never recursively."""
    if not enabled(task):return
    deadline = state.get('media_deadline_at')
    timed_out = deadline is not None and now >= deadline
    for row in raw:
        changed = False
        if (not row.get('asr_final') and row['asr_status'] not in {'success','no_audio'}
                and row.get('review_status') not in {'done','skipped'}):
            code = FINISH if timed_out else BACKLOG if captured_end(task)-row['end_ms'] > MAX_BACKLOG_MS else None
            if code:
                row.update(gap_fields(row['start_ms'], row['end_ms'], code))
                changed = True
                conn.execute("UPDATE media_jobs SET status='skipped',lease_token=NULL,lease_until=NULL,last_error_code=?,updated_at=? "
                    "WHERE session_id=? AND segment_id=? AND kind='audio' AND status NOT IN ('succeeded','failed','skipped')",
                    (code, now, store.session_id, row['id']))
        if timed_out and row['frame_status'] not in {'success','failed'}:
            row['frame_status'] = 'failed'; changed = True
        if changed:store._write_segment(conn, row['id'], row)
    if timed_out:
        conn.execute("UPDATE media_jobs SET status='skipped',lease_token=NULL,lease_until=NULL,last_error_code=?,updated_at=? "
            "WHERE session_id=? AND status NOT IN ('succeeded','failed','skipped','submission_unknown')",
            (FINISH, now, store.session_id))


class Cancellation:
    """Cancel media at its deadline and obsolete ASR while allowing review to drain."""
    def __init__(self, store, parent=None, segment_id=None):
        self.store, self.parent, self.segment_id = store, parent, segment_id

    def is_set(self):
        if self.parent is not None and self.parent.is_set():return True
        state = self.store.finish_tick()
        task = self.store.task()
        from runtime.realtime_policy import enabled as fast_live
        if not enabled(task) and not fast_live(task):return False
        if state.get('phase') == 'completed' or remaining(task, 1) <= 0:return True
        if self.segment_id is not None:
            return any(s['id']==self.segment_id and (s.get('asr_gap_code') or s['review_status']=='skipped') for s in self.store.segments())
        return False

    def wait(self, seconds):
        deadline = time.monotonic()+seconds
        while not self.is_set():
            left = deadline-time.monotonic()
            if left <= 0:return False
            time.sleep(min(.1,left))
        return True
