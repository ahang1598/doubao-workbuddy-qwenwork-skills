"""Versioned Lite inspection windows. Raw media rows never carry sampling decisions."""
import json
import math
import time
from runtime.store import Store, ASR_DONE, FRAME_DONE, encode, interval_ms, uncovered_ranges

POLICY = 'lite_sample_v1'
PARAMETERS = {'period_ms': 60000, 'window_ms': 20000, 'max_frames': 2,
              'pending_seconds': 120, 'review_seconds': 120, 'finish_seconds': 60,
              'video_max_windows': 10}
REASONS = {'backlog_skipped': '积压跳过', 'review_timeout': '判定超时',
           'finish_timeout': '收尾超时', 'insufficient_evidence': '证据不足'}


def enabled(task):
    return task.get('inspection_policy') == POLICY


def video_windows(duration):
    if type(duration) is not int or duration <= 0:
        raise ValueError('video duration must be positive milliseconds')
    count = min(10, math.ceil(duration / 60000))
    result = []
    for i in range(count):
        a, b = i * duration // count, (i + 1) * duration // count
        length = min(20000, b - a)
        start = a + (b - a - length) // 2
        result.append((start, start + length))
    return result


def windows(conn, session):
    return [json.loads(r[0]) for r in conn.execute(
        'SELECT data FROM inspection_windows WHERE session_id=? ORDER BY idx', (session,))]


def save(conn, session, row):
    conn.execute('INSERT INTO inspection_windows(session_id,idx,data) VALUES(?,?,?) '
                 'ON CONFLICT(session_id,idx) DO UPDATE SET data=excluded.data '
                 'WHERE inspection_windows.data<>excluded.data',
                 (session, row['index'], encode(row)))


def skip(row, reason, now):
    row.update(review_status='skipped', window_status=reason, skip_code=reason,
               skip_reason=REASONS[reason], sealed_at=now)


def tick(store, conn, now=None):
    now = time.time() if now is None else now
    task = store._task(conn)
    state = task.get('finishing', {})
    if state.get('phase') == 'completed':
        return state
    conn.execute('CREATE TABLE IF NOT EXISTS inspection_windows '
                 '(session_id TEXT,idx INTEGER,data TEXT NOT NULL,PRIMARY KEY(session_id,idx))')
    raw = Store._segments(store, conn)
    rows = windows(conn, store.session_id)
    by_index = {r['index']: r for r in rows}
    terminal = task.get('capture_status') in {'ended', 'stopped', 'failed'} or task.get('stop_requested') or task.get('live_ended_at')
    if terminal and not state:
        from datetime import datetime
        started=now
        for value in (task.get('stop_requested_at'),task.get('live_ended_at')):
            if value:
                try:started=min(started,float(value) if isinstance(value,(int,float)) else datetime.fromisoformat(value.replace('Z','+00:00')).timestamp())
                except (TypeError,ValueError):pass
        state = {'phase': 'draining', 'started_at': started, 'deadline_at': started + 60, 'mode': 'sample'}
        # Freeze the last candidate identity. Late ASR may enrich it, never add work.
        task['sampling_stop_ms'] = max([r['end_ms'] for r in raw] +
            [task.get('capture_active_span', {}).get('end_ms', 0),task.get('capture_observed_ms',0)])
    from runtime import live_backlog
    if live_backlog.enabled(task):task['live_backlog_policy']='latest_v1'
    if state and live_backlog.enabled(task):
        state['deadline_at'] = min(state['deadline_at'], state['started_at']+live_backlog.FINISH_SECONDS)
        state['media_deadline_at'] = min(state.get('media_deadline_at', float('inf')),
                                        state['started_at']+live_backlog.MEDIA_SECONDS, state['deadline_at'])
    live_backlog.expire(store, conn, task, raw, state, now)
    media_expired = bool(state.get('media_deadline_at') is not None and now >= state['media_deadline_at'])
    evidence_end=max([r['end_ms'] for r in raw]+[0])
    media_end = max(evidence_end,task.get('capture_observed_ms',0),task.get('capture_active_span',{}).get('end_ms',0))
    if media_end and 'sampling_origin_ms' not in task:
        task['sampling_origin_ms'] = min([r['start_ms'] for r in raw]+[task.get('capture_active_span',{}).get('start_ms',media_end)])
    origin = task.get('sampling_origin_ms', 0)
    if terminal:
        media_end = min(media_end, task.get('sampling_stop_ms', media_end))
    if task.get('kind') == 'video':
        plan = video_windows(task['source_duration_ms'])
    else:
        plan = [(a, a + 20000) for a in range(origin, media_end, 60000)]
    task['sampling_observed_ms']=media_end
    for index, (a, b) in enumerate(plan):
        sources = [s for s in raw if s['start_ms'] < b and s['end_ms'] > a]
        if not sources and task.get('kind')=='video' and task.get('sampling_preparing_index')!=index:
            continue
        row = by_index.get(index)
        if row is None:
            row = {'id': 1000000000 + index, 'window_id': f'window-{index:06d}', 'index': index,
                   'start_ms': a, 'end_ms': b, 'created_at': now, 'review_status': 'pending',
                   'window_status': 'preparing', 'evidence_revision': 1, 'policy_version': POLICY,
                   'media_file': sources[0]['media_file'] if sources else 'media', 'audio_file': None,
                   'asr_task_id': None, 'frames': [], 'subtitles': []}
            by_index[index] = row
        if row.get('frame_preparation')=='running' and row.get('frame_lease_token'):
            if now>=row.get('frame_lease_until',0):row['frame_preparation']='remote_pending'
        elif row.get('frame_preparation')=='running' and now-row.get('frame_started_at',now)>=25:
            row['frame_preparation']='failed'
        if row['review_status'] in {'done', 'skipped'} or row.get('review_started_at') is not None:
            continue  # Claimed evidence and sealed outcomes are immutable.
        if terminal and media_end < b:
            row['end_ms'] = max(a + 1, media_end)
        subtitles = list({u['id']: u for s in sources for u in s.get('subtitles', [])
                          if u['start_ms'] < row['end_ms'] and u['end_ms'] > a}.values())
        if media_expired and row.get('frame_preparation') != 'success':
            row['frame_preparation'] = 'failed'
        images_enabled=task.get('image_inspection',True)
        if not images_enabled:row['frame_preparation']='disabled'
        frames=row.get('prepared_frames',[]) if images_enabled else []
        chosen = []
        for fraction in (.25, .75):
            candidates = [f for f in frames if f not in chosen]
            if candidates:
                chosen.append(min(candidates, key=lambda f: abs(f['time_ms'] - (a + (row['end_ms']-a)*fraction))))
        if row['subtitles'] != subtitles or row['frames'] != chosen:
            row['evidence_revision'] += 1
        sealed = media_expired or evidence_end >= b or (terminal and task.get('worker_status') in {'done','failed','stopped'}) or index in task.get('sampling_prepared_indices',[])
        ready = sealed and (bool(sources) or media_expired) and all(s['asr_status'] in ASR_DONE and s['frame_status'] in FRAME_DONE for s in sources)
        missing=uncovered_ranges([row],sources)
        if media_expired:
            missing=[{**g,'reason':live_backlog.FINISH} for g in missing]
        row['window_sealed']=sealed
        row.update(subtitles=subtitles, frames=chosen, source_segment_ids=[s['id'] for s in sources],
                   asr_status=('failed' if missing or any(s['asr_status'] not in {'success','no_audio'} or s.get('speech_gaps') for s in sources) else 'success' if subtitles else 'no_audio' if all(s['asr_status']=='no_audio' for s in sources) else 'success') if ready else 'pending',
                   speech_gaps=missing+[{'start_ms':max(a,s['start_ms']),'end_ms':min(row['end_ms'],s['end_ms'])} for s in sources if s['asr_status'] not in {'success','no_audio'}]+[{**g,'start_ms':max(a,g['start_ms']),'end_ms':min(row['end_ms'],g['end_ms'])} for s in sources for g in s.get('speech_gaps',[]) if g['start_ms']<row['end_ms'] and g['end_ms']>a],
                   frame_status='disabled' if not images_enabled and ready else ('success' if row.get('frame_preparation')=='success' and len(chosen)==2 else 'failed') if ready and row.get('frame_preparation') in {'success','failed'} else 'pending',
                   window_status='ready' if ready else 'preparing')
        if ready and row.get('frame_preparation') in {'success','failed'} and not subtitles and not chosen and row['asr_status'] != 'no_audio':
            skip(row, 'insufficient_evidence', now)
    rows = sorted(by_index.values(), key=lambda r: r['index'])
    for row in rows:
        if row['review_status'] != 'pending':
            continue
        started = row.get('review_started_at')
        if state and now >= state['deadline_at']:
            skip(row, 'finish_timeout', now)
        elif started is not None and now - started >= 120:
            skip(row, 'review_timeout', now)
        elif started is None and now - row['created_at'] >= 120:
            skip(row, 'backlog_skipped', now)
    pending = [r for r in rows if r['review_status']=='pending' and r.get('review_started_at') is None]
    if task.get('kind') != 'video':
        for row in pending[:-1]:
            skip(row, 'backlog_skipped', now)
    for row in rows:
        save(conn, store.session_id, row)
    if state and (now >= state['deadline_at'] or
                  (task.get('worker_status') in {'done','failed','stopped'} and all(r['review_status'] in {'done','skipped'} for r in rows))):
        state.update(phase='completed', completed_at=now, reason='deadline' if now>=state['deadline_at'] else 'drained')
    if state:
        task['finishing'] = state
    if task != store._task(conn):
        store._set_task(conn, task)
    return state


def report_store(store):
    if not isinstance(store,Store) or isinstance(store, WindowStore) or not enabled(store.task()):
        return store
    result = object.__new__(WindowStore)
    result.__dict__.update(store.__dict__)
    return result


class WindowStore(Store):
    """Reuse task/rule/evidence validation with a separate transactional row adapter."""
    def _segments(self, conn):
        return windows(conn, self.session_id)

    def _segment(self, conn, sid):
        return next((row for row in self._segments(conn) if row['id']==sid), None)

    def _segments_by_ids(self, conn, ids):
        wanted=set(ids)
        return [row for row in self._segments(conn) if row['id'] in wanted]

    def _write_segment(self, conn, sid, data):
        save(conn, self.session_id, data)

    def _update_segment(self, conn, sid, **fields):
        tick(self, conn)
        row = next((r for r in self._segments(conn) if r['id']==sid), None)
        if not row or row['review_status'] in {'done','skipped'}:
            return False
        row.update(fields)
        row['window_status'] = 'done' if row['review_status']=='done' else 'reviewing'
        self._write_segment(conn, sid, row)
        return True

    def claim(self, *, known_rules_version=None, limit=1):
        # Repeated reads return the same active window; never lease a second one.
        result=super().claim(known_rules_version=known_rules_version, limit=1)
        rules=result.get('rules')
        if rules and not rules.get('cached'):
            result['rules']={**rules,'rules':[{k:v for k,v in r.items() if k not in {'source_section','source_sha256'} } for r in rules['rules']]}
        return result

    def submit(self, payload):
        if not isinstance(payload, dict) or payload.get('task_id') != self.task_id:
            raise ValueError('task binding mismatch')
        if 'segments' in payload:
            raise ValueError('sample policy accepts one window per submission')
        summary = payload.get('summary')
        if not isinstance(summary, str) or not summary.strip() or len(summary)>200:
            raise ValueError('window summary requires 1..200 characters')
        self.finish_tick()
        row = next((r for r in self.segments() if r['id']==payload.get('segment_id')), None)
        if row and row['review_status']=='skipped':
            return {'status':'window_expired','window_id':row['window_id'], 'reason':row['skip_reason'],
                    'retryable':False,'next_action':'report' if self.task().get('finishing',{}).get('phase')=='completed' else 'review-next'}
        if row and row.get('review_started_at') is None:
            raise ValueError('claim window before submission')
        return super().submit(payload)

    def _status(self, task, segments):
        result = super()._status(task, segments)
        done = [s for s in segments if s['review_status']=='done']
        result['task']['inspection_policy'] = POLICY
        result['task']['image_inspection'] = task.get('image_inspection',True)
        result['task']['inspection_scope'] = '字幕和画面' if task.get('image_inspection',True) else '仅ASR字幕，未检测画面'
        from runtime import live_backlog
        parameters = dict(task.get('sampling_parameters',PARAMETERS))
        if live_backlog.enabled(task):parameters.update(finish_seconds=live_backlog.FINISH_SECONDS, media_seconds=live_backlog.MEDIA_SECONDS)
        result['sampling'] = {'policy': POLICY, 'parameters': parameters,
            'image_inspection':task.get('image_inspection',True),
            'sampled_ms': interval_ms(done), 'completed_windows':len(done), 'window_count':len(segments),
            'active_windows':sum(s['review_status']=='pending' and s.get('review_started_at') is not None for s in segments),
            'pending_windows':sum(s['review_status']=='pending' and s.get('review_started_at') is None for s in segments),
            'planned_unchecked_ranges':planned_gaps(task,segments),
            'skipped_ranges':[{k:s[k] for k in ('window_id','start_ms','end_ms','window_status','skip_reason')}
                              for s in segments if s['review_status']=='skipped']}
        if live_backlog.enabled(task):
            raw = self._read_with_retry(lambda conn:Store._segments(self, conn))
            skipped = [r for r in raw if r.get('asr_gap_code') == live_backlog.BACKLOG]
            pending = [r['start_ms'] for r in raw if not r.get('asr_final') and r['asr_status'] not in {'success','no_audio'}]
            consumed = min(pending+[task.get('asr_consumed_ms',live_backlog.captured_end(task))])
            result['sampling']['asr_backlog'] = {
                'backlog_ms':max(0, live_backlog.captured_end(task)-consumed),
                'skipped_ms':interval_ms(skipped), 'skip_count':len(skipped)}
        return result


def planned_gaps(task, rows):
    end=task.get('source_duration_ms') or max([r['end_ms'] for r in rows]+[task.get('capture_end_ms') or 0,task.get('capture_observed_ms',0),task.get('sampling_observed_ms',0)])
    cursor=task.get('sampling_origin_ms',0) if task.get('kind')!='video' else 0
    result=[]
    for row in sorted(rows,key=lambda r:r['start_ms']):
        if row['start_ms']>cursor:
            result.append({'start_ms':cursor,'end_ms':row['start_ms'],'window_status':'planned_unchecked','reason':'计划未抽检'})
        cursor=max(cursor,row['end_ms'])
    if cursor<end:result.append({'start_ms':cursor,'end_ms':end,'window_status':'planned_unchecked','reason':'计划未抽检'})
    return result


def recap_windows(task, rows):
    done=sorted((s for s in rows if s['review_status']=='done'),key=lambda s:s['start_ms'])
    levels={str(r['id']):str(r.get('priority',r.get('risk_level',r.get('severity','')))).lower() for r in task['rules_snapshot']['rules']}
    risk_ids={str(r['id']) for r in task['rules_snapshot']['rules'] if r.get('count_as_risk',True)}
    ranks={'p0':4,'p1':3,'p2':2,'p3':1,'high':3,'高':3,'medium':2,'中':2,'low':1,'低':1}
    def risk(row):
        hits=[d for d in row.get('review_result',{}).get('rules',[]) if d['status']=='hit' and str(d['rule_id']) in risk_ids]
        return max([ranks.get(levels.get(str(d['rule_id'])),1) for d in hits]+[0])
    risky=sorted((s for s in done if risk(s)),key=lambda s:(-risk(s),s['start_ms']))[:3]
    return sorted({s['id']:s for s in done[:1]+risky+done[-8:]}.values(),key=lambda s:s['start_ms'])


def prepare_frames(store):
    """Extract exactly the sealed window's two positions, outside the DB transaction.

    Recording is continuous for live tasks. JPEG production waits for the window
    length, so a short final window can use its actual 25% and 75% positions.
    """
    if store.task().get('frames_policy')=='remote_first' and store.task().get('asr_policy')=='remote_first':
        from runtime.remote_frames import prepare_windows
        return prepare_windows(store)
    import subprocess
    from pathlib import Path
    from runtime.mediakit import config
    from runtime.realtime import recording_segments
    store.finish_tick()
    task=store.task()
    if task.get('image_inspection') is False:return
    from runtime import live_backlog
    if task.get('finishing',{}).get('phase')=='completed' or live_backlog.remaining(task,10)<=0:return
    with store.connection(True) as conn:
        candidates=[r for r in windows(conn,store.session_id) if r['review_status']=='pending'
                    and r.get('window_sealed') and not r.get('frame_preparation')]
        if not candidates:return
        row=candidates[0]
        row.update(frame_preparation='running',frame_started_at=time.time())
        save(conn,store.session_id,row)
    # A source file may still be open; fragmented MP4 permits bounded reads of
    # already written fragments. Never inspect unsampled images.
    recordings=recording_segments(store)
    frames=[]
    for n,fraction in enumerate((.25,.75)):
        budget=live_backlog.remaining(store.task(),10)
        if budget<=0:break
        at=row['start_ms']+round((row['end_ms']-row['start_ms'])*fraction)
        if task.get('kind')=='video':
            source=Path(task['source']);offset=at
        else:
            recording=next((s for s in recordings if s['start_ms']<=at<s['end_ms']),None)
            if recording:
                source=store.local_path(recording['media_file']);offset=at-recording['start_ms']
            else:
                journals=sorted((store.root/'media').glob('session-*.json'))
                eligible=[(p,json.loads(p.read_text())) for p in journals if json.loads(p.read_text())['base_ms']<=at]
                if not eligible:continue
                journal,session=eligible[-1]
                serial=int(journal.stem.split('-')[-1])
                previous=[s for s in recordings if s['start_ms']>=session['base_ms']]
                index=max([s['index'] for s in previous]+[serial-1])+1
                start=max([s['end_ms'] for s in previous]+[session['base_ms']])
                source=store.root/'media'/f'segment-{index:06d}.mp4';offset=at-start
                if offset<0 or not source.is_file():continue
        target=store.root/'frames'/f"sample-{row['index']:06d}-{n}.jpg"
        try:
            process=subprocess.run([config(task,'ffmpeg_bin','ffmpeg'),'-nostdin','-v','error','-y',
                '-ss',str(offset/1000),'-i',str(source),'-frames:v','1','-vf','scale=min(1280\\,iw):-2',
                '-q:v', '10', str(target)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=budget)
            if process.returncode==0 and target.is_file() and target.stat().st_size:
                target.chmod(0o600)
                frames.append({'id':f"sample-{row['index']}-{n}",'path':str(target.relative_to(store.root)),'time_ms':at})
        except (OSError,subprocess.TimeoutExpired):
            pass
    with store.connection(True) as conn:
        tick(store,conn)
        current=next((r for r in windows(conn,store.session_id) if r['id']==row['id']),None)
        if current and current['review_status']=='pending' and current.get('review_started_at') is None and current.get('frame_preparation')=='running':
            current.update(prepared_frames=frames,frame_preparation='success' if len(frames)==2 else 'failed')
            save(conn,store.session_id,current)
            tick(store,conn)
