# Adapted from skills_live_inspect_lite/runtime/media_jobs.py; content-only migration.
"""Durable local media production. Queue ownership and evidence commit share SQLite."""
import json
import time
import uuid

SCHEMA = '''CREATE TABLE IF NOT EXISTS media_jobs(
 id INTEGER PRIMARY KEY,
 session_id TEXT NOT NULL,
 segment_id INTEGER NOT NULL,
 kind TEXT NOT NULL CHECK(kind IN ('frames','audio')),
 backend TEXT NOT NULL DEFAULT 'ffmpeg',
 status TEXT NOT NULL CHECK(status IN ('queued','running','retry_wait','succeeded','skipped','failed','submitting','submitted','submission_unknown')),
 remote_task_id TEXT,
 attempts INTEGER NOT NULL DEFAULT 0,
 next_run_at REAL NOT NULL DEFAULT 0,
 lease_token TEXT,
 lease_until REAL,
 result_json TEXT,
 last_error_code TEXT,
 created_at REAL NOT NULL,
 updated_at REAL NOT NULL,
 UNIQUE(session_id,segment_id,kind),
 FOREIGN KEY(session_id,segment_id) REFERENCES segments(session_id,id)
)'''
INDEX = 'CREATE INDEX IF NOT EXISTS media_jobs_due ON media_jobs(session_id,kind,status,next_run_at)'
TERMINAL = {'succeeded', 'skipped', 'failed', 'submission_unknown'}
STATES = ('queued', 'running', 'retry_wait', 'succeeded', 'skipped', 'failed',
          'submitting', 'submitted', 'submission_unknown')


def evidence_state(data, kind):
    if data.get('review_status') == 'skipped':return 'skipped'
    if kind == 'frames':
        return {'success': 'succeeded', 'failed': 'failed', 'disabled': 'succeeded'}.get(data.get('frame_status'), 'queued')
    if data.get('audio_file'):
        return 'succeeded'
    if data.get('asr_status') == 'no_audio':
        return 'skipped'
    if data.get('asr_status') in {'success', 'submitted', 'timed_out', 'submission_unknown'}:
        return 'skipped'  # Do not replay or overwrite existing ASR work.
    if data.get('asr_status') == 'failed':
        return 'failed'
    return 'queued'


def enqueue(conn, session_id, segment_id, data):
    now = time.time()
    for kind in (('audio',) if data.get('full_live') else ('frames','audio')):
        conn.execute('''INSERT OR IGNORE INTO media_jobs
            (session_id,segment_id,kind,status,created_at,updated_at) VALUES(?,?,?,?,?,?)''',
            (session_id, segment_id, kind, evidence_state(data, kind), now, now))


def initialize(store):
    """Additive upgrade/backfill, including legacy migrations that insert raw segments."""
    with store.connection(True) as conn:
        conn.execute(SCHEMA)
        conn.execute(INDEX)
        for row in conn.execute('''SELECT s.id,s.data FROM segments s WHERE s.session_id=?
                AND (SELECT count(*) FROM media_jobs j WHERE j.session_id=s.session_id
                     AND j.segment_id=s.id)<2''', (store.session_id,)).fetchall():
            enqueue(conn, store.session_id, row['id'], json.loads(row['data']))
        if conn.execute('PRAGMA user_version').fetchone()[0] < 4:
            conn.execute('PRAGMA user_version=4')


def reconcile(conn, session_id, segment_id, data):
    # Direct evidence imports/manual recovery may satisfy jobs before they are claimed.
    for kind in ('frames', 'audio'):
        state = evidence_state(data, kind)
        if state != 'queued':
            conn.execute('''UPDATE media_jobs SET status=?,updated_at=?
                WHERE session_id=? AND segment_id=? AND kind=? AND status='queued' ''',
                (state, time.time(), session_id, segment_id, kind))


class MediaJobs:
    def __init__(self, store):
        self.store = store

    def rows(self, conn=None):
        if conn is None:
            return self.store._read_with_retry(self.rows)
        return [dict(row) for row in conn.execute(
            'SELECT * FROM media_jobs WHERE session_id=? ORDER BY segment_id,id', (self.store.session_id,))]

    def summary(self, conn, segments):
        visible = {s['id'] for s in segments}
        jobs = [{k: v for k, v in row.items() if k not in {'lease_token', 'result_json'}}
                for row in self.rows(conn) if row['segment_id'] in visible]
        waiting = [j['created_at'] for j in jobs if j['status'] not in TERMINAL]
        return {'counts': {state: sum(j['status'] == state for j in jobs) for state in STATES},
                'oldest_wait_seconds': max(0, time.time()-min(waiting)) if waiting else 0,
                'jobs': jobs}

    def pending(self):
        return any(row['status'] not in TERMINAL for row in self.rows())

    def claim(self, kind, *, now=None, lease_seconds=30):
        if kind not in ('frames', 'audio'):
            raise ValueError('unknown media job kind')
        observed_at = time.time() if now is None else now
        # Most v2 evidence is already produced by the stream. Empty polls must
        # not acquire the single SQLite writer lock on every worker iteration.
        # Retry only the read-only probe; never replay a claim transaction.
        due = self.store._read_with_retry(lambda conn: conn.execute('''SELECT 1 FROM media_jobs WHERE session_id=? AND kind=?
                AND ((status IN ('queued','retry_wait') AND next_run_at<=?)
                     OR (status='running' AND lease_until<=?)) LIMIT 1''',
                (self.store.session_id, kind, observed_at, observed_at)).fetchone())
        if not due:return None
        with self.store.connection(True) as conn:
            now = time.time() if now is None else now
            from runtime.finishing import advance, closed
            if closed(advance(self.store, conn)) or self.store._task(conn).get('media_frozen'):return None
            # A crashed final attempt must terminate instead of retrying forever.
            for row in conn.execute('''SELECT * FROM media_jobs WHERE session_id=? AND kind=?
                    AND status='running' AND lease_until<=? AND attempts>=3''',
                    (self.store.session_id, kind, now)).fetchall():
                fields = {'frame_status': 'failed'} if kind == 'frames' else {'asr_status': 'failed'}
                self.store._update_segment(conn, row['segment_id'], **fields)
                conn.execute("UPDATE media_jobs SET status='failed',lease_token=NULL,lease_until=NULL,last_error_code='lease_expired',updated_at=? WHERE id=?", (now, row['id']))
            row = conn.execute('''SELECT * FROM media_jobs WHERE session_id=? AND kind=? AND backend IN ('ffmpeg','mediakit')
                AND ((status IN ('queued','retry_wait') AND next_run_at<=?)
                     OR (status='running' AND lease_until<=?))
                ORDER BY segment_id,id LIMIT 1''', (self.store.session_id, kind, now, now)).fetchone()
            if not row:
                return None
            token = uuid.uuid4().hex
            conn.execute("UPDATE media_jobs SET status='running',attempts=attempts+1,lease_token=?,lease_until=?,updated_at=? WHERE id=?",
                         (token, now+lease_seconds, now, row['id']))
            return dict(conn.execute('SELECT * FROM media_jobs WHERE id=?', (row['id'],)).fetchone())

    def renew(self, job, *, now=None, lease_seconds=30):
        with self.store.connection(True) as conn:
            now = time.time() if now is None else now
            return conn.execute('''UPDATE media_jobs SET lease_until=?,updated_at=? WHERE id=?
                AND session_id=? AND status='running' AND lease_token=? AND lease_until>?''',
                (now+lease_seconds, now, job['id'], self.store.session_id, job['lease_token'], now)).rowcount == 1

    def checkpoint(self, job, **fields):
        """Fence remote submission journals and per-segment backend choices too."""
        with self.store.connection(True) as conn:
            row = conn.execute("""SELECT 1 FROM media_jobs WHERE id=? AND session_id=?
                AND status='running' AND lease_token=? AND lease_until>?""",
                (job['id'], self.store.session_id, job['lease_token'], time.time())).fetchone()
            if not row or not self.store._update_segment(conn, job['segment_id'], **fields): return False
            if fields.get('frame_backend'):
                conn.execute('UPDATE media_jobs SET backend=? WHERE id=?', (fields['frame_backend'], job['id']))
            return True

    def complete(self, job, fields, *, error=None, now=None, publish=None):
        """Only the current lease may publish files, update evidence or schedule retry."""
        with self.store.connection(True) as conn:
            now = time.time() if now is None else now
            from runtime.finishing import advance, closed
            if closed(advance(self.store, conn)):return False
            current = conn.execute('''SELECT * FROM media_jobs WHERE id=? AND session_id=?
                AND status='running' AND lease_token=? AND lease_until>?''',
                (job['id'], self.store.session_id, job['lease_token'], now)).fetchone()
            if not current:
                return False
            fields = dict(fields)
            retry = bool(error) and current['attempts'] < 3
            state = 'retry_wait' if retry else 'failed' if error else 'skipped' if fields.get('asr_status') == 'no_audio' else 'succeeded'
            delay = (2, 10)[current['attempts']-1] if retry else 0
            if retry:
                if job['kind'] == 'frames': fields['frame_status'] = 'pending'
                else: fields.pop('asr_status', None)
            if not self.store._update_segment(conn, job['segment_id'], **fields):return False
            if publish:
                publish()
            conn.execute('''UPDATE media_jobs SET status=?,next_run_at=?,lease_token=NULL,lease_until=NULL,
                result_json=?,last_error_code=?,updated_at=? WHERE id=?''',
                (state, now+delay, json.dumps(fields, ensure_ascii=False), error, now, job['id']))
            return True


def run_job(store, job, *, cancel=None):
    """One bounded attempt, renewing the lease while either backend works."""
    import os
    from pathlib import Path
    import subprocess
    import tempfile
    import threading
    from runtime.media import extract_frames, extract_audio

    queue = MediaJobs(store)
    done = threading.Event()
    lost = threading.Event()
    def cancelled(): return lost.is_set() or (cancel is not None and cancel.is_set())

    def renew():
        while not done.wait(5):
            try:
                if not queue.renew(job):
                    lost.set()
                    return
            except Exception:
                # Losing the DB does not authorize a stale completion; complete fences it.
                lost.set()
                return

    pulse = threading.Thread(target=renew, daemon=True)
    pulse.start()
    try:
        segment = next(s for s in store.segments() if s['id'] == job['segment_id'])
        with tempfile.TemporaryDirectory(dir=store.root, prefix=f".media-job-{job['lease_token']}-") as temporary:
            try:
                if job['kind'] == 'frames':
                    from runtime.frame_router import extract, FrameJobCancelled
                    try:
                        fields, error, files = extract(store, segment, Path(temporary), job, cancelled=cancelled)
                    except FrameJobCancelled:
                        return
                else:
                    fields, error, files = extract_audio(store, segment, Path(temporary))
            except (OSError, ValueError, RuntimeError, EOFError, subprocess.SubprocessError):
                fields = {'frame_status': 'failed'} if job['kind'] == 'frames' else {'asr_status': 'failed'}
                error, files = job['kind'] + '_extraction_failed', []

            def publish():
                for source, target in files:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    os.replace(source, target)

            if queue.complete(job, fields, error=error, publish=publish) and error:
                store.log('media_job_retry_or_failed', error, job['segment_id'])
    finally:
        done.set()
        pulse.join(timeout=6)
