"""Task-local SQLite contract, adapted from skills_live_inspect_lite/runtime/store.py.

Retains durable evidence, evidence revisions, without shared
room-wide queues. Audience and comments are task-local supplements; semantic decisions are supplied by Agent.
"""
# Store 是 Lite 的持久化边界：任务、片段、复核批次和交付状态都必须先落库再对外报告。
from __future__ import annotations
import contextlib
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import time
import uuid
from datetime import datetime, timezone
from runtime.rules import SCENARIOS, task_scenarios

SCENE_WINDOW_MS = 30 * 1000

def _is_transient_read_error(error):
    return (isinstance(error, sqlite3.OperationalError)
            and getattr(error, 'sqlite_errorcode', None) == 522)


ASR_DONE = {'success', 'failed', 'timed_out', 'submission_unknown', 'no_audio'}
FRAME_DONE = {'success', 'failed', 'not_required', 'not_scheduled', 'unavailable', 'disabled'}
DECISIONS = {'hit', 'no_hit', 'not_applicable', 'insufficient'}


def check_event_gate(rule, event, evidence):
    gate = rule.get('evidence_gate', 'direct')
    refs = event['evidence_ids']
    counterparts = event.get('counterpart_evidence_ids', [])
    if gate == 'claim_specific':
        basis = event.get('claim_basis')
        quote = event.get('claim_quote')
        def normalize(text):
            return re.sub(r'[\s，。；、：！？“”「」,;:!?]+', '', str(text or ''))
        def quoted(text, ids):
            # ASR can span consecutive subtitle IDs. Image text comes from the viewed-frame description.
            speech = ''.join(evidence[r].get('text','') for r in ids if evidence[r]['kind']=='asr')
            return bool(normalize(text)) and (normalize(text) in normalize(speech) or
                    any(evidence[r]['kind']=='image' for r in ids) and normalize(text) in normalize(event.get('description')))
        if basis not in ('direct','contradiction') or not isinstance(quote,str) or not quoted(quote, refs):
            raise ValueError('absolute claim basis required')
        if basis == 'contradiction':
            if not counterparts or set(counterparts).intersection(refs):
                raise ValueError('counterpart evidence required')
            other = event.get('counterpart_quote')
            if not isinstance(other,str) or not quoted(other,counterparts):
                raise ValueError('counterpart quote required')
        gate = 'counterpart' if basis=='contradiction' else 'direct'
    if gate=='counterpart':
        if not counterparts or set(counterparts).intersection(refs):
            raise ValueError('counterpart evidence required')
    elif counterparts:
        raise ValueError('counterpart evidence not allowed')


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def encode(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(',', ':'))


def safe_message(value, limit=600):
    text = re.sub(r'https?://\S+', '[来源地址]', str(value))
    for key in ('DOUBAO_OFFICE_USER_ACCESS_TOKEN', 'DOUBAO_OFFICE_CLI_TOKEN'):
        if os.environ.get(key): text = text.replace(os.environ[key], '[凭据]')
    return text[:limit]


def skill_version():
    try:
        text=(Path(__file__).resolve().parents[2]/'SKILL.md').read_text(encoding='utf-8')
        match=re.search(r'^\s*version:\s*["\']?([^"\'\s]+)',text,re.M)
        return match.group(1) if match else None
    except OSError:
        return None


def initialize_decision_traces(c):
    c.execute('CREATE TABLE IF NOT EXISTS decision_traces '
              '(id TEXT PRIMARY KEY,session_id TEXT NOT NULL,segment_id INTEGER NOT NULL,created_at TEXT NOT NULL,data TEXT NOT NULL)')


def save_decision_trace(c, store, segment, digest, task, rules, evidence, decisions, payload):
    initialize_decision_traces(c)
    audit=[{'rule_id':d['rule_id'],'status':d['status'],
            'evidence_gate':rules[d['rule_id']].get('evidence_gate','direct'),
            'event_count':len(d['events']),
            'evidence_ids':[ref for e in d['events'] for ref in e['evidence_ids']],
            'counterpart_evidence_ids':[ref for e in d['events'] for ref in e['counterpart_evidence_ids']]}
           for d in decisions]
    context_id=payload.get('_source_context') or payload.get('context_id')
    context=None
    if context_id:
        row=c.execute('SELECT data FROM review_contexts WHERE id=? AND session_id=?',(context_id,store.session_id)).fetchone()
        context=json.loads(row[0]) if row else None
    submitted=payload.get('_audit_submission',payload)
    submitted={key:copy.deepcopy(value) for key,value in submitted.items()
               if key in {'task_id','context_id','host_task_id','segment_id','evidence_revision','summary','images_viewed','content_route','sales_observation','clarification_observations','clarification_checks','qa_observations','qa_checks','rules','reviewed'}}
    trace={
        'schema':'review_decision_trace/v2','trace_id':digest,'recorded_at':now_iso(),
        'task_id':store.task_id,'session_id':store.session_id,'segment_id':segment['id'],
        'skill_version':skill_version(),
        'evidence_revision':segment.get('evidence_revision'),'review_protocol':task.get('review_protocol'),
        'rules_version':task['rules_snapshot'].get('version'),'context_id':context_id,
        # These three blocks are the reproducible input/output boundary.
        'frozen_rules':copy.deepcopy(list(rules.values())),
        'frozen_policies':copy.deepcopy(task['rules_snapshot'].get('policies',{})),
        'review_contract':copy.deepcopy((context or {}).get('audit_contract')),
        'evidence':{'subtitles':[copy.deepcopy(item) for item in segment.get('subtitles',[])],
                    'frames':[{key:value for key,value in frame.items() if key != 'path'} for frame in segment.get('frames',[])],
                    'asr_status':segment.get('asr_status'),'frame_status':segment.get('frame_status'),
                    **({'viewer_context':copy.deepcopy(segment['viewer_context'])} if 'viewer_context' in segment else {})},
        'submitted_decision':submitted,'normalized_decisions':copy.deepcopy(decisions),
        **({'clarification_context':copy.deepcopy(payload.get('_clarification_context', [])),
            'normalized_clarification_observations':copy.deepcopy(payload['_normalized_clarifications'])} if '_normalized_clarifications' in payload else {}),
        **({'normalized_clarification_checks':copy.deepcopy(payload['_normalized_clarification_checks'])} if '_normalized_clarification_checks' in payload else {}),
        **({'sales_base':copy.deepcopy(payload.get('_sales_base')),
            'sales_products':copy.deepcopy(payload.get('_sales_products', [])),
            'normalized_sales_observation':copy.deepcopy(payload['_normalized_sales'])} if '_normalized_sales' in payload else {}),
        **({'qa_context':copy.deepcopy(payload.get('_qa_context', [])), 'normalized_qa_observations':copy.deepcopy(payload['_normalized_qa'])} if '_normalized_qa' in payload else {}),
        **({'normalized_qa_checks':copy.deepcopy(payload['_normalized_qa_checks'])} if '_normalized_qa_checks' in payload else {}),
        'validation':{'status':'accepted','evidence_gate_checks':audit},
    }
    if '_normalized_qa' in payload and str(segment['id']) not in (context or {}).get('supplements', {}):
        from runtime.interactions import review_diagnostic
        trace['qa_review'] = review_diagnostic(payload.get('_qa_context', []), segment,
            payload['_normalized_qa'], payload.get('_normalized_qa_checks', []),
            (context or {}).get('qa_focus', {}).get(str(segment['id']), []), version=(context or {}).get('qa_focus_version',1))
    c.execute('INSERT OR IGNORE INTO decision_traces VALUES(?,?,?,?,?)',
              (digest,store.session_id,segment['id'],trace['recorded_at'],encode(trace)))
    for decision in decisions:
        rule = rules[decision['rule_id']]
        if (decision['status'] != 'hit' or rule.get('kind') == 'visual_router'
                or not rule.get('count_as_risk', True)):
            continue
        events = decision['events']
        facts = {'task_id':store.task_id, 'segment_id':segment['id'], 'rule_id':decision['rule_id'],
                 'start_ms':min(e['start_ms'] for e in events), 'event_count':len(events)}
        # Each segment belongs to one task. A supplemental review may retain the same hit.
        c.execute("""CREATE UNIQUE INDEX IF NOT EXISTS first_risk_hit ON operation_logs
                     (segment_id,json_extract(message,'$.rule_id')) WHERE kind='risk.hit'""")
        saved = c.execute("INSERT OR IGNORE INTO operation_logs(created_at,kind,message,segment_id) VALUES(?,?,?,?)",
                          (trace['recorded_at'],'risk.hit',encode({**facts,'trace_id':digest}),segment['id']))
        if saved.rowcount and c.telemetry is not None:
            from runtime.rules import RULE_DEFINITIONS
            builtin = rule.get('origin') != 'custom' and any(
                row[0] == facts['rule_id'] for group in RULE_DEFINITIONS.values() for row in group)
            c.telemetry.risk_hits.append({**facts,'rule_id':facts['rule_id'] if builtin else 'custom'})
    if trace.get('qa_review', {}).get('questions'):
        questions = trace['qa_review']['questions']
        counts = {name:sum(q['outcome'] == name for q in questions)
                  for name in ('answered','reply_detected','question_extracted','candidate_unanswered','no_candidate','not_checked')}
        c.execute('INSERT INTO operation_logs(created_at,kind,message,segment_id) VALUES(?,?,?,?)',
                  (trace['recorded_at'],'qa_review',encode({'trace_id':digest,
                   'matcher':trace['qa_review']['matcher'], 'question_count':len(questions),
                   'provided_count':sum(q['provided_to_model'] for q in questions), 'outcomes':counts}),segment['id']))
    c.execute('INSERT INTO operation_logs(created_at,kind,message,segment_id) VALUES(?,?,?,?)',
              (now_iso(),'review_decision_trace',safe_message(encode({
                  'trace_id':digest,'rules_version':task['rules_snapshot'].get('version'),'decisions':audit})),segment['id']))


def atomic_json(path, value):
    path = Path(path)
    temp = path.with_name(path.name + '.' + secrets.token_hex(8) + '.tmp')
    try:
        with os.fdopen(os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w', encoding='utf-8') as f:
            f.write(encode(value)); f.flush(); os.fsync(f.fileno())
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def bounded_ms(value, name):
    if type(value) is not int or value < 0: raise ValueError(name + ' requires nonnegative integer')
    return value


def capture_coverage(task, segments):
    spans = []
    source=list(task.get('capture_spans',segments))
    if task.get('pipeline_version')==2 and task.get('capture_status')=='running' and task.get('capture_active_span'):
        source.append(task['capture_active_span'])
    for s in sorted(source, key=lambda s:s['start_ms']):
        if spans and s['start_ms'] <= spans[-1][1]: spans[-1][1] = max(spans[-1][1], s['end_ms'])
        else: spans.append([s['start_ms'],s['end_ms']])
    low = task.get('capture_start_ms') or 0
    high = task.get('capture_end_ms')
    known = high is not None and task.get('capture_start_ms') is not None
    high = max(low, high if high is not None else max([task.get('capture_observed_ms',0),*[b for a,b in spans]]))
    cursor, gaps, captured = low, [], 0
    for a,b in spans:
        a,b=max(a,low),min(b,high)
        if b<=a:continue
        if a-cursor>1000:gaps.append({'start_ms':cursor,'end_ms':a})
        cursor=max(cursor,b);captured+=b-a
    if high-cursor>1000:gaps.append({'start_ms':cursor,'end_ms':high})
    missing=sum(g['end_ms']-g['start_ms'] for g in gaps)
    initial_delay=(gaps[0]['end_ms']-gaps[0]['start_ms']
                   if gaps and spans and gaps[0]['start_ms']==low and gaps[0]['end_ms']<=spans[0][0] else 0)
    interrupted=max(0,missing-initial_delay)
    messages=[]
    if initial_delay:messages.append(f'启动连接等待 {max(1,(initial_delay+999)//1000)} 秒，该时段未采集或判定。')
    if interrupted:messages.append(f'录制中断缺失 {max(1,(interrupted+999)//1000)} 秒，缺失时段未作判定。')
    return {'start_ms':low,'end_ms':high,'gaps':gaps,'captured_ms':captured,
            'analysis_gaps':uncovered_ranges([{'start_ms':max(a,low),'end_ms':min(b,high)} for a,b in spans if min(b,high)>max(a,low)],segments),
            'missing_ms':missing,'initial_delay_ms':initial_delay,'interruption_missing_ms':interrupted,
            'message':' '.join(messages),'boundaries_known':known,
            'complete':known and not gaps,'ratio':captured/(high-low) if high>low else None}


def uncovered_ranges(spans, covered):
    """Interval difference; contextual captions do not add coverage."""
    result=[]
    for span in spans:
        cursor,end=span['start_ms'],span['end_ms']
        for item in sorted(covered,key=lambda s:s['start_ms']):
            a,b=item['start_ms'],item['end_ms']
            if b<=cursor or a>=end:continue
            if a>cursor:result.append({'start_ms':cursor,'end_ms':min(a,end)})
            cursor=max(cursor,min(b,end))
        if cursor<end:result.append({'start_ms':cursor,'end_ms':end})
    return result


def interval_ms(segments):
    spans=[]
    for s in sorted(segments,key=lambda s:s['start_ms']):
        if spans and s['start_ms']<=spans[-1][1]:spans[-1][1]=max(spans[-1][1],s['end_ms'])
        else:spans.append([s['start_ms'],s['end_ms']])
    return sum(b-a for a,b in spans)


class Store:
    def __init__(self, task_dir, **ignored):
        self.root = self.task_root = self.workspace_root = Path(task_dir).expanduser().resolve()
        self.path = self.root/'inspection.db'
        if not self.path.is_file(): raise ValueError('task does not exist')
        row=self._read_with_retry(lambda c:c.execute('SELECT id,data FROM live_sessions').fetchone())
        if not row:raise ValueError('task does not exist')
        self.session_id=row['id']; self.task_id=json.loads(row['data'])['id']

    @classmethod
    def create(cls, task_dir, *, name, scenario, source, rules, kind="live", **config):
        if kind not in {'live','video'}:raise ValueError('unsupported task kind')
        from runtime.sampling import POLICY, PARAMETERS, VIDEO_FULL_POLICY
        if config.get('inspection_policy') == POLICY:
            config['sampling_parameters']=dict(PARAMETERS)
            if kind == 'video':
                config['sampling_parameters'].update(pending_seconds=900, review_seconds=180, finish_seconds=900)
        if 'image_inspection' in config and type(config['image_inspection']) is not bool:raise ValueError('image_inspection must be boolean')
        if config.get('inspection_policy') == VIDEO_FULL_POLICY:
            config['sampling_parameters'] = {'period_ms': int(config.get('segment_seconds',30)*1000),
                'window_ms': int(config.get('segment_seconds',30)*1000), 'max_frames':2,
                'pending_seconds':PARAMETERS['pending_seconds'], 'review_seconds':PARAMETERS['review_seconds'], 'finish_seconds':None}
        if config.get('image_inspection') is False and 'sampling_parameters' in config:config['sampling_parameters']['max_frames']=0
        if kind == 'live':
            from runtime.remediation import VERSION
            config['remediation_version'] = VERSION
        duration=config.setdefault('max_duration_seconds',None)
        if duration is not None and (type(duration) is not int or duration <= 0):
            raise ValueError('duration must be a positive integer or null')
        delivery_mode=config.setdefault('delivery_mode','local_dashboard')
        if delivery_mode not in {'local_dashboard','html_snapshot','chat'}:raise ValueError('unsupported delivery mode')
        root=Path(task_dir).expanduser().resolve()
        skill=Path(__file__).resolve().parents[2]
        if root==skill or skill in root.parents:raise ValueError('task directory must be outside lite')
        if not isinstance(rules,dict) or not rules.get('rules'):raise ValueError('rules required')
        from runtime.platform_support import private_directory
        private_directory(root)
        path=root/'inspection.db'
        from runtime.task_context import reserve
        tid=reserve(root) or uuid.uuid4().hex
        try:
            fd=os.open(path,os.O_RDWR|os.O_CREAT|os.O_EXCL,0o600)
        except FileExistsError:
            from runtime.task_context import TaskAlreadyExists
            raise TaskAlreadyExists() from None
        os.close(fd)
        sid=uuid.uuid4().hex
        task=dict(config,id=tid,task_id=tid,session_id=sid,kind=kind,name=name,scenario=scenario,
                  source=source,rules_snapshot=rules,created_at=now_iso(),capture_status='pending',
                  worker_status='pending',stop_requested=False,revision=1)
        with contextlib.closing(sqlite3.connect(path)) as c:
            c.execute('PRAGMA journal_mode=WAL')
            c.executescript('''CREATE TABLE live_sessions(id TEXT PRIMARY KEY,data TEXT NOT NULL);
            CREATE TABLE segments(id INTEGER PRIMARY KEY,session_id TEXT NOT NULL,idx INTEGER NOT NULL,data TEXT NOT NULL,
              UNIQUE(session_id,idx),UNIQUE(session_id,id));
            CREATE TABLE submissions(id TEXT PRIMARY KEY,segment_id INTEGER NOT NULL,digest TEXT NOT NULL);
            CREATE TABLE operation_logs(id INTEGER PRIMARY KEY,created_at TEXT,kind TEXT,message TEXT,segment_id INTEGER);''')
            initialize_decision_traces(c)
            if task.get('inspection_policy') in {POLICY, VIDEO_FULL_POLICY}:
                c.execute('CREATE TABLE inspection_windows(session_id TEXT,idx INTEGER,data TEXT NOT NULL,PRIMARY KEY(session_id,idx))')
            c.execute('INSERT INTO live_sessions VALUES(?,?)',(sid,encode(task)))
            c.commit()
        obj=cls(root)
        for folder in ('media','frames','audio'): (root/folder).mkdir(mode=0o777 if os.name == 'nt' else 0o700)
        from runtime.media_jobs import initialize
        initialize(obj)
        from runtime.transaction import start_store
        start_store(obj)
        return obj

    @contextlib.contextmanager
    def connection(self,write=False,*,timeout=15):
        from runtime.review_execution import active, phase
        if active():
            timeout = min(timeout, .5)
            try: phase('database_write' if write else 'database_read')
            except OSError: pass
        from runtime.diagnostics import cleanup_actions, log_failure
        from runtime.transaction import Connection, PendingEvents
        events = []
        # Reconnect only before yielding. Never replay caller code or a commit.
        for attempt in range(1, 5):
            c = None
            stage = 'connection_open'
            try:
                c=sqlite3.connect(self.path,timeout=timeout,isolation_level=None,factory=Connection)
                c.row_factory=sqlite3.Row
                c.execute('PRAGMA foreign_keys=ON')
                if write:
                    stage = 'transaction_begin'
                    c.execute('BEGIN IMMEDIATE')
                break
            except BaseException as error:
                # Replaceable progress intentionally yields to an evidence writer.
                busy_progress = (write and timeout == 0 and stage == 'transaction_begin'
                    and isinstance(error, sqlite3.OperationalError)
                    and getattr(error, 'sqlite_errorcode', 0) & 255 in (5, 6))
                if not busy_progress:log_failure(error, stage=stage, attempt=attempt)
                if c is not None:
                    cleanup_actions([('cleanup_connection_close', c.close)], error)
                if stage == 'transaction_begin' and _is_transient_read_error(error) and attempt < 4:
                    time.sleep(.02 * (2 ** (attempt - 1)))
                    continue
                raise
        from runtime.transaction import enabled as telemetry_enabled
        pending = PendingEvents(self,c) if write and telemetry_enabled() else None
        c.telemetry = pending
        stage = 'transaction_body'
        primary = None
        try:
            yield c
            if write:
                stage = 'transaction_commit'
                events = pending.prepare() if pending is not None else []
                c.commit()
                if active():
                    try: phase('database_committed')
                    except OSError: pass  # A diagnostic write cannot undo a durable commit.
        except BaseException as error:
            primary = error
            log_failure(error, stage=stage, attempt=attempt)
        actions = [('cleanup_rollback', c.rollback)] if primary is not None and write else []
        primary = cleanup_actions(actions + [('cleanup_connection_close', c.close)], primary)
        if primary is not None:
            raise primary
        if events:
            from runtime.transaction import send, notify_parent
            try:
                send(events)
            except Exception:pass
            notify_parent(self,events)

    def for_session(self):return self
    def _read_with_retry(self, fn):
        """Bounded retries for short reads; other I/O errors propagate unchanged."""
        last = None
        for attempt in range(4):
            try:
                with self.connection() as c:
                    return fn(c)
            except sqlite3.OperationalError as error:
                last = error
                from runtime.diagnostics import log_failure
                log_failure(error, stage='snapshot_read', attempt=attempt + 1)
                if _is_transient_read_error(error) and attempt < 3:
                    time.sleep(0.02 * (2 ** attempt))
                    continue
                raise
        raise last
    def _task(self,c):return json.loads(c.execute('SELECT data FROM live_sessions WHERE id=?',(self.session_id,)).fetchone()[0])
    def _set_task(self,c,data):
        from runtime.transaction import task_changing
        before = self._task(c)
        if data == before: return
        # Delivery generations are business state, including when telemetry is off.
        if (data.get('kind') == 'video'
                and before.get('worker_status') in {'done', 'failed', 'stopped'}
                and data.get('worker_status') in {'preparing', 'pending', 'running'}):
            data['video_report_run'] = before.get('video_report_run', 1) + 1
        task_changing(self,c,before,data)
        data['revision']=data.get('revision',0)+1
        c.execute('UPDATE live_sessions SET data=? WHERE id=?',(encode(data),self.session_id))
    def task(self):
        return self._read_with_retry(self._task)
    def update_task(self,**fields):
        with self.connection(True) as c:
            task=self._task(c)
            for k in ('asr_fallback_runtime','asr_fallback_runtime_root'):
                if k in fields and fields[k]!=task.get(k):raise ValueError('immutable fallback model identity')
            if 'rule_routing_version' in fields and fields['rule_routing_version']!=task.get('rule_routing_version'):
                raise ValueError('immutable task identity')
            for k in ('id','task_id','session_id','remediation_version','kind','source','rules_snapshot','scenario','delivery_mode','asr_provider','asr_backend','asr_policy','frames_policy','asr_primary_backend','asr_selection_reason','model_preparation_id','artifact_specs','node_bin','ffmpeg_bin','ffprobe_bin','asr_runtime_root','asr_runtime','source_duration_ms','source_fingerprint','inspection_policy','review_protocol','segmentation','sampling_parameters','frame_required','frame_sampling_origin_ms','image_inspection'):
                if k in fields and fields[k]!=task.get(k):raise ValueError('immutable task identity')
            if task.get('media_frozen'):
                frozen = {'capture_start_ms','capture_end_ms','capture_observed_ms','capture_spans','capture_active_span',
                          'live_subtitle','monitor_ended_at','monitored_duration_ms','media_frozen','stop_requested'}
                fields = {k:v for k,v in fields.items() if k not in frozen}
                if fields.get('capture_status') in {'pending','running'}:fields.pop('capture_status')
                if fields.get('worker_status') in {'pending','running','setup_pending'}:fields.pop('worker_status')
                fields.pop('recovery_state',None)
            task.update(fields);self._set_task(c,task)
            from runtime.finishing import advance
            advance(self,c)
    def finish_tick(self):
        from runtime.finishing import advance
        task = self.task()
        from runtime.sampling import enabled, tick
        if enabled(task):
            with self.connection(True) as c:return tick(self,c)
        state = task.get('finishing', {})
        if state.get('phase') == 'completed':return state
        # Media heartbeats should not wait for a writer while no budget is due.
        from runtime.stop_signal import read as read_stop
        if not state and not (read_stop(self.root) or task.get('stop_requested') or task.get('live_ended_at') or
                              task.get('capture_status') in {'ended','stopped','failed'}):
            from runtime.realtime_policy import current, current_work
            if not current(task):return {}
            _, _, stalled, waiting = self._read_with_retry(lambda conn:current_work(self, conn, time.time()))
            from runtime.realtime_policy import no_speech_evidence
            if not stalled and not any(no_speech_evidence(task, s) for s in waiting):return {}
        # Re-read inside the write transaction; a concurrent stop must not be
        # overwritten by the read-only fast path's older task snapshot.
        with self.connection(True) as c:return advance(self,c)

    def update_progress(self, **fields):
        """Disposable live progress must not backpressure PCM or model decoding."""
        if not fields.keys() <= {'capture_reconnecting','capture_active_span','capture_observed_ms','capture_last_input_at',
                                'live_subtitle','worker_heartbeat','asr_consumed_ms'}:
            raise ValueError('only replaceable live progress may skip a busy write')
        try:
            with self.connection(True, timeout=0) as c:
                task=self._task(c)
                if task.get('media_frozen'):return False
                if task.get('capture_reconnecting') and fields.get('capture_reconnecting') is False:
                    task['live_source_status'] = 'live'
                task.update(fields)
                self._set_task(c,task)
            return True
        except sqlite3.OperationalError as error:
            code=getattr(error,'sqlite_errorcode',0)
            if (code & 255) in (5,6) or (not code and str(error) in ('database is locked','database table is locked')):
                return False  # Next progress tick replaces this sample; evidence is untouched.
            raise

    def bind_prepared_model(self,check):
        """One-time identity binding, before any media evidence can exist."""
        with self.connection(True) as c:
            task=self._task(c)
            if not task.get('model_waiting'):
                if task.get('asr_runtime')==check.get('runtime') and task.get('asr_runtime_root')==check.get('asr_runtime_root'):
                    return
                raise ValueError('model identity already bound')
            if self._segments(c): raise ValueError('model binding requires an empty waiting task')
            if not check['ready'] or check['artifact_specs']!=task['artifact_specs']:
                raise ValueError('prepared model identity changed')
            task.update(asr_runtime_root=check['asr_runtime_root'],asr_runtime=check['runtime'],
                        model_waiting=False,setup_error=None,worker_status='pending')
            self._set_task(c,task)

    def bind_fallback_model(self,check):
        """Freeze a verified local backup without changing the original ASR identity."""
        from runtime.finishing import advance, closed
        with self.connection(True) as c:
            if closed(advance(self,c)):return False
            task=self._task(c)
            if (task.get('asr_primary_backend')!='mediakit' or task.get('asr_policy') not in {'remote_first','local_first'}
                    or not check.get('ready') or not check.get('runtime') or not check.get('asr_runtime_root')
                    or check.get('artifact_specs')!=task.get('artifact_specs')):
                raise ValueError('invalid fallback model')
            if task.get('asr_fallback_runtime'):
                if (task['asr_fallback_runtime']!=check['runtime']
                        or task['asr_fallback_runtime_root']!=check['asr_runtime_root']):
                    raise ValueError('fallback model identity changed')
                return True
            task.update(asr_fallback_runtime=check['runtime'],asr_fallback_runtime_root=check['asr_runtime_root'])
            self._set_task(c,task)
            from runtime.mediakit import unsubmitted_auth_failure
            for segment in self._segments(c):
                if unsubmitted_auth_failure(segment):
                    self._update_segment(c,segment['id'],asr_status='pending',asr_diagnostic=None)
            return True

    def request_stop(self, *, immediate=False, origin=None, reason=None, user_instruction=None, confirm_discard=False):
        from runtime.finishing import advance
        execution_limit=reason=='execution_limit'
        if execution_limit:
            from runtime.realtime_policy import current
            if origin!='agent' or immediate or not current(self.task()):
                raise ValueError('execution limit requires current live drain')
        signal = None
        if not immediate and reason in {'user_request','execution_limit'}:
            from runtime.stop_signal import request
            signal=request(self.root,origin=origin,reason=reason,instruction=user_instruction)
        with self.connection(True) as c:
            task=self._task(c)
            from runtime.review_contract import enabled as protocol_v2
            if protocol_v2(task):
                if origin not in {'agent','dashboard'} or reason not in {'user_request','execution_limit'}:
                    raise ValueError('stop requires explicit user request')
                if origin=='agent' and not execution_limit and (not isinstance(user_instruction,str) or not user_instruction.strip()):
                    raise ValueError('agent stop requires user instruction')
                if immediate and not confirm_discard:
                    raise ValueError('immediate stop requires user confirmation to discard remaining content')
                if immediate and origin == 'agent':
                    import re
                    ordinary = re.sub(r'[\s。！!，,？?]', '', user_instruction)
                    if ordinary in {'结束质检', '停止质检', '停止监控', '结束监控', '结束检测', '停止检测'}:
                        raise ValueError('ordinary stop must drain; immediate stop requires explicit confirmation to discard remaining content')
                if not task.get('stop_requested') or (immediate and not task.get('stop_immediately')):
                    from runtime.report_data import public_text
                    task['stop_audit']={'origin':origin,'reason':reason,
                                        'user_instruction':public_text(user_instruction) if origin=='agent' and not execution_limit else None,
                                        'mode':'immediate' if immediate else 'drain',
                                        'discard_confirmed':bool(immediate and confirm_discard), 'discarded_segments':0, 'at':now_iso()}
            if immediate and task.get('kind','live')!='live':raise ValueError('immediate stop requires a live task')
            if task.get('finishing',{}).get('phase')=='completed':return
            if execution_limit and not task.get('stop_requested'):
                task['stop_reason']=signal['reason']
            task.update(stop_requested=True,stop_requested_at=task.get('stop_requested_at') or (signal['requested_at'] if signal else now_iso()))
            if immediate:task['stop_immediately']=True
            self._set_task(c,task)
            if task.get('kind', 'live') == 'live' and not immediate and (reason in {'user_request','execution_limit'} or task.get('freeze_on_end')):
                task['bounded_finishing']=True
                self._set_task(c,task)
            advance(self,c)
    def should_stop(self):
        from runtime.stop_signal import read
        if read(self.root):return True
        task=self.task()
        if task.get('stop_requested'):return True
        duration=task.get('max_duration_seconds')
        if task.get('kind')=='live' and duration is not None and task.get('capture_epoch') and time.time()-task['capture_epoch']>=duration:
            from runtime.stop_signal import request
            signal=request(self.root,origin='runtime',reason='source_ended',instruction=None)
            self.update_task(stop_requested=True,stop_requested_at=signal['requested_at'],stop_reason='duration_limit');return True
        return False
    def local_path(self,path):
        p=(self.root/str(path)).resolve()
        if p==self.root or self.root not in p.parents:raise ValueError('path outside task')
        return p
    def _segments(self,c):
        return [dict(json.loads(r['data']),id=r['id'],index=r['idx']) for r in c.execute('SELECT * FROM segments WHERE session_id=? ORDER BY idx',(self.session_id,))]
    def _segment(self,c,sid):
        if type(sid) is not int:return None
        row=c.execute('SELECT id,idx,data FROM segments WHERE session_id=? AND id=?',
                      (self.session_id,sid)).fetchone()
        return dict(json.loads(row['data']),id=row['id'],index=row['idx']) if row else None
    def _segments_by_ids(self,c,ids):
        ids=[sid for sid in ids if type(sid) is int]
        if not ids:return []
        placeholders=','.join('?' for _ in ids)
        query=f'SELECT id,idx,data FROM segments WHERE session_id=? AND id IN ({placeholders})'
        rows=c.execute(query,(self.session_id,*ids)).fetchall()
        return [dict(json.loads(row['data']),id=row['id'],index=row['idx']) for row in rows]
    def segments(self):
        return self._read_with_retry(self._segments)
    def add_segment(self,index,start_ms,end_ms,media_file, *, evidence=None):
        for val,key in ((index,'index'),(start_ms,'start'),(end_ms,'end')):bounded_ms(val,key)
        if end_ms<=start_ms:raise ValueError('empty segment')
        self.local_path(media_file)
        with self.connection(True) as c:
            if self._task(c).get('media_frozen'):raise ValueError('media evidence frozen')
            row=c.execute('SELECT id,data FROM segments WHERE session_id=? AND idx=?',(self.session_id,index)).fetchone()
            if row:
                old=json.loads(row['data'])
                if (old['start_ms'],old['end_ms'],old['media_file'])!=(start_ms,end_ms,str(media_file)):raise ValueError('conflicting segment')
                return row['id']
            from runtime.finishing import advance, closed, REASON
            finish=advance(self,c)
            if finish.get('phase')=='completed':raise ValueError('inspection finished')
            data=dict(start_ms=start_ms,end_ms=end_ms,media_file=str(media_file),frames=[],subtitles=[],
                      frame_status='pending',asr_status='pending',audio_file=None,asr_task_id=None,review_status='pending',evidence_revision=1)
            if evidence:
                if set(evidence) & {'id','index','start_ms','end_ms','media_file','review_status'}:raise ValueError('invalid initial evidence')
                for frame in evidence.get('frames',[]):self.local_path(frame['path'])
                if evidence.get('audio_file'):self.local_path(evidence['audio_file'])
                data.update(evidence)
            from runtime import full_live
            if full_live.enabled(self._task(c)):
                task=self._task(c)
                if not self._segments(c):
                    task['frame_sampling_origin_ms']=start_ms;self._set_task(c,task)
                full_live.initialize_segment(task,data)
            if self._task(c).get('image_inspection') is False:
                data.update(frames=[],frame_status='disabled')
            if closed(finish):
                from runtime.finishing import IMMEDIATE_REASON
                data.update(review_status='skipped',skip_reason=IMMEDIATE_REASON if finish.get('mode')=='immediate' else REASON,
                            skip_code='USER_DISCARD' if finish.get('mode')=='immediate' else 'FINISH_INCOMPLETE')
            from runtime.transaction import segment_changing
            segment_changing(self,c,None,None,data)
            sid=c.execute('INSERT INTO segments(session_id,idx,data) VALUES(?,?,?)',(self.session_id,index,encode(data))).lastrowid
            from runtime.media_jobs import enqueue
            enqueue(c,self.session_id,sid,data)
            from runtime.realtime_policy import enabled as fast_live
            if fast_live(self._task(c)):advance(self,c)
            task = self._task(c)
            if data.get('skip_code') == 'USER_DISCARD' and task.get('stop_audit'):
                task['stop_audit']['discarded_segments'] = sum(s.get('skip_code') == 'USER_DISCARD' for s in self._segments(c))
                self._set_task(c, task)
            return sid
    def _update_segment(self,c,sid,*,invalidate_review=False,_remote_asr=False,_defer_asr_failure=False,_asr_recovery=False,**fields):
        from runtime.finishing import advance, closed
        if closed(advance(self,c)):return False
        if self._task(c).get('media_frozen') and (invalidate_review or not fields.keys() <= {
                'review_status','review_result','review_started_at','reviewed_at','review_defer','review_attempts',
                'speech_reviewed','speech_review_completed_at','claim_token','lease_until','judgment_elapsed_ms'}):return False
        row=c.execute('SELECT data FROM segments WHERE session_id=? AND id=?',(self.session_id,sid)).fetchone()
        if not row:raise ValueError('unknown segment')
        data=json.loads(row[0])
        from runtime import live_backlog
        if live_backlog.remaining(self._task(c), 1) <= 0:return False
        from runtime.full_live import enabled as full
        task=self._task(c)
        if full(task) and time.time()>=task.get('finishing',{}).get('media_deadline_at',float('inf')) and any(k in fields for k in ('frames','subtitles','asr_status','frame_status')):return False
        if data.get('asr_final') and any(k in fields for k in ('asr_status','subtitles','asr_task_id')):return False
        if data.get('review_status')=='skipped' or (_asr_recovery and data.get('review_status')=='done'):return False
        if _remote_asr and data.get('asr_selection_reason')=='cloud_unavailable_local':return False
        if _remote_asr and 'asr_status' in fields:
            fields['asr_remote_status']=fields['asr_status']
        if _defer_asr_failure and fields.get('asr_status') in {'failed','timed_out','submission_unknown'}:
            fields['asr_remote_status']=fields['asr_status']
            fields['asr_status']='fallback_pending'
        for k in ('start_ms','end_ms','media_file','id','index'):
            if k in fields:raise ValueError('immutable segment identity')
        for item in fields.get('frames',[]):self.local_path(item['path'])
        if fields.get('audio_file'):self.local_path(fields['audio_file'])
        # Retrying missing speech invalidates the old judgment even if the
        # eventual successful result is silence (subtitles stay []). Do this
        # in the evidence transaction for every local/cloud recovery path.
        recovering_asr=(data.get('asr_status') in {'failed','timed_out','submission_unknown'}
                        and fields.get('asr_status') in {'pending','running','submitted','success','no_audio'})
        deferred_ready=data.get('review_status')=='deferred' and any(k in fields and fields[k]!=data.get(k) and fields[k] in usable for k,usable in (('asr_status',{'success','no_audio'}),('frame_status',{'success'})))
        changed=invalidate_review or recovering_asr or deferred_ready or any(k in fields and fields[k]!=data.get(k) for k in ('subtitles','frames'))
        from runtime import full_live
        if full_live.enabled(self._task(c)):
            if fields.get('asr_status') in ASR_DONE and data.get('asr_status') not in ASR_DONE:
                fields['asr_ready_at']=time.time()
            if changed and 'frames' in fields and 'subtitles' not in fields and data.get('review_result'):
                data['previous_review_result']=data['review_result']
        if changed and 'subtitles' in fields:
            data.pop('previous_review_result',None);data.pop('speech_reviewed',None);data.pop('speech_review_completed_at',None)
        data.update(fields)
        if changed:
            data.pop('review_attempts',None)
            data.pop('review_defer',None)
            data['evidence_revision']=data.get('evidence_revision',0)+1;data['review_status']='pending'
            for k in ('review_result','claim_token','lease_until'):
                if k=='review_result' and full_live.enabled(self._task(c)) and 'frames' in fields:continue
                data.pop(k,None)
            c.execute('DELETE FROM submissions WHERE segment_id=?',(sid,))
        self._write_segment(c,sid,data)
        from runtime.media_jobs import reconcile
        reconcile(c,self.session_id,sid,data)
        # Complete the drain in the final evidence transaction, not a later poll.
        if self._task(c).get("kind", "live") == "live":advance(self,c)
        return True
    def _write_segment(self,c,sid,data):
        from runtime.transaction import segment_changing
        row=c.execute('SELECT data FROM segments WHERE id=? AND session_id=?',(sid,self.session_id)).fetchone()
        segment_changing(self,c,sid,json.loads(row[0]) if row else None,data)
        c.execute('UPDATE segments SET data=? WHERE id=?',(encode(data),sid))

    def update_segment(self,sid,**fields):
        with self.connection(True) as c:return self._update_segment(c,sid,**fields)
    def log(self,kind,message,segment_id=None):
        limit = 8192 if kind == 'mediakit_cli_diagnostic' else 600
        with self.connection(True) as c:c.execute('INSERT INTO operation_logs(created_at,kind,message,segment_id) VALUES(?,?,?,?)',(now_iso(),kind,safe_message(message, limit),segment_id))

    def set_review_disposition(self, value):
        """Persist a reviewer downgrade without changing the original model decision."""
        required = {'task_id', 'segment_id', 'evidence_revision', 'rule_id', 'disposition', 'reason'}
        if not isinstance(value, dict) or set(value) != required:
            raise ValueError('review disposition requires task, segment, evidence, rule, disposition and reason')
        if value['task_id'] != self.task_id or type(value['segment_id']) is not int or type(value['evidence_revision']) is not int:
            raise ValueError('review disposition binding mismatch')
        if not isinstance(value['rule_id'], str) or not value['rule_id'] or value['disposition'] not in ('warning', 'insufficient'):
            raise ValueError('unsupported review disposition')
        if not isinstance(value['reason'], str) or not value['reason'].strip():
            raise ValueError('review disposition reason required')
        with self.connection(True) as c:
            task = self._task(c)
            row = c.execute('SELECT data FROM segments WHERE session_id=? AND id=?',
                            (self.session_id, value['segment_id'])).fetchone()
            if not row:
                raise ValueError('unknown segment')
            segment = json.loads(row[0])
            if segment.get('evidence_revision') != value['evidence_revision']:
                raise ValueError('evidence changed')
            decision = next((item for item in (segment.get('review_result') or {}).get('decisions',
                                                (segment.get('review_result') or {}).get('rules', []))
                             if item.get('rule_id') == value['rule_id'] and item.get('status', item.get('result')) == 'hit'), None)
            if decision is None:
                raise ValueError('review disposition requires a saved hit')
            key = ':'.join((str(value['segment_id']), str(value['evidence_revision']), value['rule_id']))
            disposition = {'disposition': value['disposition'], 'reason': value['reason'].strip(), 'reviewed_at': now_iso()}
            task.setdefault('review_dispositions', {})[key] = disposition
            self._set_task(c, task)
            c.execute('INSERT INTO operation_logs(created_at,kind,message,segment_id) VALUES(?,?,?,?)',
                      (now_iso(), 'review_disposition', safe_message(encode({
                          'rule_id': value['rule_id'], 'evidence_revision': value['evidence_revision'],
                          'disposition': value['disposition'], 'reason': disposition['reason']})), value['segment_id']))
        return {'status': 'saved', 'task_id': self.task_id, 'segment_id': value['segment_id'],
                'rule_id': value['rule_id'], 'disposition': value['disposition']}

    def decision_trace(self, *, segment_id=None, rule_id=None):
        """Return the persisted, evidence-grounded path for saved decisions.

        This is an audit projection, not a reconstruction of model reasoning.  It
        deliberately puts the submitted reason next to the exact evidence the
        runtime accepted, so an unsupported word in the reason is observable.
        """
        if segment_id is not None and type(segment_id) is not int:
            raise ValueError('segment_id requires integer')
        if rule_id is not None and (not isinstance(rule_id,str) or not rule_id):
            raise ValueError('rule_id requires nonempty string')
        def read(c):
            task=self._task(c)
            rules={r['id']:r for r in task['rules_snapshot']['rules']}
            entries=[]
            records=[]
            missing_records=0
            has_table=c.execute("SELECT 1 FROM sqlite_master WHERE name='decision_traces'").fetchone()
            if has_table:
                query='SELECT data FROM decision_traces WHERE session_id=?'
                params=[self.session_id]
                if segment_id is not None:
                    query+=' AND segment_id=?';params.append(segment_id)
                for row in c.execute(query,params):
                    record=json.loads(row[0])
                    if rule_id is not None:
                        record['normalized_decisions']=[decision for decision in record['normalized_decisions']
                                                        if decision.get('rule_id')==rule_id]
                        record['validation']['evidence_gate_checks']=[item for item in record['validation']['evidence_gate_checks']
                                                                       if item.get('rule_id')==rule_id]
                        if not record['normalized_decisions']:continue
                    records.append(record)
            for segment in self._segments(c):
                if segment_id is not None and segment['id'] != segment_id:continue
                result=segment.get('review_result') or {}
                evidence={x['id']:dict(x,kind='asr') for x in segment.get('subtitles',[])}
                evidence.update({x['id']:dict(x,kind='image') for x in segment.get('frames',[])})
                def project(ref):
                    item=evidence.get(ref)
                    if not item:return {'id':ref,'available':False}
                    value={'id':ref,'kind':item['kind'],'available':True}
                    for field in ('start_ms','end_ms','time_ms','text'):
                        if field in item:value[field]=item[field]
                    return value
                for decision in result.get('rules',[]):
                    current_rule_id=decision.get('rule_id')
                    if rule_id is not None and current_rule_id != rule_id:continue
                    rule=rules.get(current_rule_id,{})
                    events=[]
                    for event in decision.get('events',[]):
                        claim_refs=list(event.get('evidence_ids',[]))
                        counterpart_refs=list(event.get('counterpart_evidence_ids',[]))
                        events.append({
                            'evidence_ids':claim_refs,
                            'observed_evidence':[project(ref) for ref in claim_refs],
                            'counterpart_evidence_ids':counterpart_refs,
                            'observed_counterpart_evidence':[project(ref) for ref in counterpart_refs],
                            'event_text':event.get('text',''),
                            **{k:event[k] for k in ('claim_basis','claim_quote','comparison_scope','counterpart_quote') if k in event},
                            'start_ms':event.get('start_ms'),'end_ms':event.get('end_ms'),
                        })
                    gate=rule.get('evidence_gate')
                    recorded=next((record for record in reversed(records)
                                   if record.get('segment_id')==segment['id']
                                   and record.get('evidence_revision')==segment.get('evidence_revision')
                                   and any(d.get('rule_id')==current_rule_id and d==decision
                                           for d in record.get('normalized_decisions',[]))),None)
                    check=next((item for item in (recorded or {}).get('validation',{}).get('evidence_gate_checks',[])
                                if item.get('rule_id')==current_rule_id),None)
                    if recorded is None:missing_records+=1
                    entries.append({
                        'segment_id':segment['id'],'evidence_revision':segment.get('evidence_revision'),
                        'reviewed_at':segment.get('reviewed_at'),'rules_version':task['rules_snapshot'].get('version'),
                        'rule_id':current_rule_id,'rule_name':rule.get('name'),'status':decision.get('status'),
                        'reason':decision.get('reason',''),'channels':decision.get('channels',{}),
                        'evidence_gate':gate,
                        'gate_validation':{
                            'status':('passed' if decision.get('status')=='hit' else 'not_required') if check and gate else 'unknown',
                            'requires_counterpart':(any(e.get('claim_basis')=='contradiction' for e in events) if gate=='claim_specific' else gate=='counterpart') if gate else None,
                            'counterpart_evidence_present':any(event['counterpart_evidence_ids'] for event in events),
                        },
                        'events':events,
                    })
            return {'task_id':self.task_id,'rules_version':task['rules_snapshot'].get('version'),
                    'segment_id':segment_id,'rule_id':rule_id,'records':records,'entries':entries,
                    'review_dispositions':[{'segment_id':int(key.split(':',2)[0]), 'evidence_revision':int(key.split(':',2)[1]),
                                            'rule_id':key.split(':',2)[2], **value}
                                           for key,value in task.get('review_dispositions',{}).items()
                                           if len(key.split(':',2)) == 3
                                           and (segment_id is None or key.split(':',2)[0] == str(segment_id))
                                           and (rule_id is None or key.split(':',2)[2] == rule_id)],
                    'replayable':bool(entries) and missing_records==0,
                    'message':('records 保存了当时的规则、合同、全量本段证据、模型提交与校验结果，可用于复检与 Prompt/流程优化。'
                               if entries and missing_records==0 else
                               '审计记录不完整；部分 entries 仅由现存结果重建，不能保证完整复放。' if records else
                               '未找到新式审计记录；entries 仅由现存结果重建，不能保证完整复放。')}
        return self._read_with_retry(read)

    def load_rule_bundle(self,value):
        """Add evidence-backed industry rules without pausing ordinary review."""
        from runtime.sampling import report_store, enabled, WindowStore
        if not isinstance(self,WindowStore) and enabled(self.task()):
            return report_store(self).load_rule_bundle(value)
        from runtime.rules import load_rules, ALIASES
        if not isinstance(value,dict):raise ValueError('rule request must be an object')
        bundle=ALIASES.get(value.get('bundle'),value.get('bundle'))
        if bundle not in SCENARIOS:raise ValueError('unsupported rule bundle')
        with self.connection(True) as c:
            from runtime.finishing import advance, closed
            if closed(advance(self,c)):
                return {'status':'inspection_finished','next_action':'report'}
            task=self._task(c)
            if value.get('task_id')!=self.task_id:raise ValueError('task binding mismatch')
            if task.get('rules_mode')!='dynamic':raise ValueError('task uses a fixed rule snapshot')
            segment=self._segment(c,value.get('segment_id'))
            if not segment or segment['review_status'] in {'done','skipped'}:raise ValueError('no pending evidence')
            if value.get('evidence_revision')!=segment['evidence_revision']:raise ValueError('stale rule evidence')
            refs=value.get('evidence_ids');viewed=value.get('images_viewed',[])
            frames={f['id'] for f in segment.get('frames',[])}
            ids=frames|{u['id'] for u in segment.get('subtitles',[])}
            if (not isinstance(refs,list) or not refs or any(not isinstance(r,str) for r in refs)
                    or not isinstance(viewed,list) or any(not isinstance(r,str) for r in viewed)
                    or not set(refs)<=ids or not set(viewed)<=frames):raise ValueError('invalid rule evidence')
            if not (set(refs)&frames)<=set(viewed):raise ValueError('rule image evidence not viewed')
            if not isinstance(value.get('reason'),str) or not value['reason'].strip():raise ValueError('rule reason required')
            loaded=task.get('loaded_rule_bundles',[])
            if bundle not in loaded:
                snapshot=task['rules_snapshot']
                extra=load_rules(bundle)
                merged={r['id']:dict(r) for r in snapshot['rules']}
                for rule in extra['rules']:
                    if rule['id'] not in merged or rule.get('active_supplements'):
                        merged[rule['id']]=dict(rule)
                rules=list(merged.values())
                for i,rule in enumerate(rules,1):rule['order']=i
                policies={**snapshot.get('policies',{}),**extra.get('policies',{})}
                digest=hashlib.sha256(encode({'rules':rules,'policies':policies}).encode()).hexdigest()
                task['rules_snapshot']={**snapshot,'version':'dynamic-'+digest,'rules':rules,'policies':policies,
                    'source_sha256':hashlib.sha256((snapshot['source_sha256']+extra['source_sha256']).encode()).hexdigest()}
                task['loaded_rule_bundles']=[*loaded,bundle]
                task.setdefault('rule_load_evidence',[]).append({'bundle':bundle,'segment_id':segment['id'],
                    'evidence_ids':refs,'reason':value['reason']})
                self._set_task(c,task)
            return {'task_id':self.task_id,'status':'rules_loaded','loaded_rule_bundles':task['loaded_rule_bundles'],
                    'rules':task['rules_snapshot'],'next_action':'review-next'}

    def _ensure_rule_defaults(self,c):
        """Resume old unreviewed tasks without their retired selection gate."""
        task=self._task(c)
        if task.get('scenario_selection')!='pending':return
        from runtime.rules import load_rules
        if not any(s['review_status']=='done' for s in self._segments(c)):
            task.update(rules_snapshot=load_rules('common'),rules_mode='dynamic',
                        loaded_rule_bundles=[],scenario='通用')
        task['scenario_selection']='confirmed'
        task.pop('finance_rules_snapshot',None)
        self._set_task(c,task)

    def claim(self,*,known_rules_version=None,limit=1,include_deferred=False,dispatcher_id="main",source_context=None):
        if not self.task().get('inspection_policy') and self.task().get('pipeline_version') != 2 and limit==1:
            return self._legacy_claim(known_rules_version=known_rules_version,include_deferred=include_deferred)
        from runtime.full_live import enabled as full
        if full(self.task()):
            from runtime.live_review import claim
            return claim(self,known_rules_version,limit,dispatcher_id,source_context=source_context)
        from runtime.sampling import report_store, enabled, WindowStore
        if not isinstance(self,WindowStore) and enabled(self.task()):return report_store(self).claim(known_rules_version=known_rules_version,limit=limit)
        if type(limit) is not int or not 1<=limit<=5:raise ValueError('limit must be 1..5')
        with self.connection(True) as c:
            from runtime.finishing import advance, closed
            finish=advance(self,c)
            if closed(finish):
                return {'task_id':self.task_id,'segment':None,'finishing':finish,'next_action':'report' if finish['phase']=='completed' else 'status','inspection_finished':True}
            self._ensure_rule_defaults(c)
            all_segments=self._segments(c)
            selected=[]
            for s in all_segments:
                if s['review_status'] in {'done','skipped'}:continue
                from runtime.full_live import ready as evidence_ready
                if not evidence_ready(self._task(c),s):continue
                if not s.get('review_started_at'):
                    s['review_started_at']=time.time()
                    self._update_segment(c,s['id'],review_started_at=s['review_started_at'])
                # Legacy claimed rows are readable immediately; no ownership or expiry.
                s={k:v for k,v in s.items() if k not in ('claim_token','lease_until','review_attempts')}
                s['review_status']='pending'
                snapshot=self._task(c)['rules_snapshot']
                cached=bool(known_rules_version) and known_rules_version==snapshot.get('version')
                rules={'version':snapshot['version'],'cached':True,'rule_ids':[r['id'] for r in snapshot['rules']]} if cached else snapshot
                if self._task(c).get('pipeline_version')==2:
                    s['context_subtitles']=[u for previous in all_segments if previous['end_ms']<=s['start_ms'] and previous['end_ms']>s['start_ms']-30000 and previous['asr_status']=='success' for u in previous.get('subtitles',[])][-10:]
                s['image_inspection']=self._task(c).get('image_inspection',True)
                s['inspection_scope']='字幕和画面' if s['image_inspection'] else '仅ASR字幕，未检测画面'
                s['image_checklist']=[{k:f[k] for k in ('id','path','time_ms') if k in f} for f in s.get('frames',[])]
                from runtime.remediation import enabled as remediation_enabled, contract as remediation_contract
                if remediation_enabled(self._task(c)):
                    s['remediation_contract'] = remediation_contract()
                selected.append(s)
                if len(selected)>=limit:break
            if selected:
                return {'task_id':self.task_id,'session_id':self.session_id,
                        **({'segment':selected[0]} if limit==1 else {'segments':selected}), 'rules':rules,'finishing':finish}
        return {'task_id':self.task_id,'session_id':self.session_id,**({'segment':None} if limit==1 else {'segments':[]}), 'status':self.status()}
    def defer(self,payload):
        from runtime.sampling import report_store, WindowStore, VIDEO_FULL_POLICY
        if not isinstance(self,WindowStore) and self.task().get('inspection_policy')==VIDEO_FULL_POLICY:
            return report_store(self).defer(payload)
        from runtime.review_errors import ReviewError, review_error
        if self.task().get('kind')!='video':raise ReviewError('VIDEO_ONLY','command','此命令仅适用于视频。',retryable=False)
        if not isinstance(payload,dict) or payload.get('task_id')!=self.task_id:raise review_error('task binding mismatch')
        sid=payload.get('segment_id')
        reason=payload.get('reason_code')
        if not isinstance(reason,str) or reason not in {'INPUT_REPAIR_EXHAUSTED','EVIDENCE_UNAVAILABLE','REVIEW_BLOCKED'}:
            raise ReviewError('DEFER_REASON_INVALID','reason_code','请选择受控的待续办原因。',sid)
        with self.connection(True) as c:
            segment=self._segment(c,sid)
            if segment is None:raise review_error('unknown segment',sid)
            if type(payload.get('evidence_revision')) is not int or payload['evidence_revision']!=segment['evidence_revision']:
                raise review_error('evidence changed; read segment again',sid)
            if segment['review_status'] in {'done','skipped'}:raise review_error('segment already reviewed',sid)
            skipped=self._task(c).get('inspection_policy')==VIDEO_FULL_POLICY
            fields=({'review_status':'skipped','skip_code':reason,
                     'skip_reason':{'INPUT_REPAIR_EXHAUSTED':'判定输入修正次数耗尽','EVIDENCE_UNAVAILABLE':'判定证据不可用','REVIEW_BLOCKED':'判定受阻'}[reason],
                     'window_status':'skipped','sealed_at':time.time()} if skipped else
                    {'review_status':'deferred','review_defer':{'reason_code':reason,'evidence_revision':segment['evidence_revision']}})
            if skipped:
                segment.update(fields)
                self._write_segment(c,sid,segment)
            else:self._update_segment(c,sid,**fields)
        return {'status':'skipped' if skipped else 'deferred','segment_id':sid,'next_action':'review-next'}
    def submit(self,payload):
        if isinstance(payload,dict) and "segments" in payload:
            return self._submit(payload)
        if not self.task().get('inspection_policy') and self.task().get('pipeline_version') != 2:
            return self._legacy_submit(payload)
        from runtime.review_contract import enabled as protocol_v2, expand
        if protocol_v2(self.task()) and isinstance(payload,dict) and 'context_id' in payload and 'segments' not in payload:
            try:
                original=copy.deepcopy(payload)
                payload=expand(self,payload)
                payload['_audit_submission']=original
            except (ValueError,TypeError,KeyError) as error:
                from runtime.review_metrics import record_attempt
                from runtime.review_errors import review_error
                detail=review_error(error,fallback=True,protocol_v2=True)
                record_attempt(self,context_id=payload.get('context_id'),error={'code':detail['code']})
                raise
        observed=protocol_v2(self.task()) and isinstance(payload,dict) and 'segments' not in payload
        from runtime.review_metrics import record
        try:
            result=self._submit(payload)
        except (ValueError,TypeError,KeyError) as error:
            if observed:record(self,payload,error=error)
            raise
        if observed:record(self,payload,result=result)
        return result

    def _submit(self,payload):
        from runtime.sampling import report_store, enabled, WindowStore
        if not isinstance(self,WindowStore) and enabled(self.task()):return report_store(self).submit(payload)
        from runtime.review_errors import review_error
        if not isinstance(payload,dict) or payload.get('task_id')!=self.task_id:raise ValueError('task binding mismatch')
        if 'segments' in payload:
            items=payload['segments']
            maximum=20 if self.task().get('inspection_policy')=='lite_live_realtime_v2' else 5
            if not isinstance(items,list) or not 1<=len(items)<=maximum:raise ValueError(f'batch requires 1..{maximum} segments')
            results=[]
            for item in items:
                try:
                    if not isinstance(item,dict) or 'segments' in item or item.get('task_id',self.task_id)!=self.task_id:raise ValueError('invalid batch item')
                    results.append(self.submit({**{k:payload[k] for k in ('batch_id','generation','context_id','host_task_id') if k in payload},**item,'task_id':payload['task_id']}))
                except (ValueError,KeyError,TypeError) as error:
                    from runtime.review_contract import enabled as protocol_v2
                    detail=review_error(error, fallback=True, protocol_v2=protocol_v2(self.task()))
                    results.append({**detail,'status':'error','segment_id':item.get('segment_id') if isinstance(item,dict) else None})
            failures=[r for r in results if r['status']=='error']
            from runtime.review_contract import enabled as protocol_v2
            if failures and protocol_v2(self.task()):
                from runtime.review_metrics import record_attempt
                record_attempt(self,context_id=payload.get('context_id'),
                               error={k:failures[-1][k] for k in ('code','field') if k in failures[-1]},
                               count_error=False)
            retryable = [r for r in failures if r.get('code') not in {'LIVE_BATCH_REVIEW_TIMEOUT', 'ALREADY_REVIEWED'}]
            return {'status':'batch_saved','results':results,
                    'saved_count':sum(r['status'] in {'saved','already_saved'} for r in results),
                    'error_count':sum(r['status']=='error' for r in results),
                    'retry_segment_ids':[r['segment_id'] for r in retryable],
                    'repair_required':bool(retryable),
                    **({'next_action':'rules-load' if any(r.get('next_action')=='rules-load' for r in retryable)
                        else 'review-submit' if retryable else 'review-next'} if failures else {})}
        digest=hashlib.sha256(encode({k:v for k,v in payload.items() if k not in {'_source_context','_audit_submission','_sales_base','_sales_products','_normalized_sales','_clarification_context','_clarification_required','_normalized_clarifications','_normalized_clarification_checks','_qa_context','_qa_check_context','_normalized_qa','_normalized_qa_checks'}}).encode()).hexdigest()
        with self.connection(True) as c:
            from runtime.realtime_policy import current as realtime_current
            from runtime.finishing import advance, closed
            if realtime_current(self._task(c)) and closed(advance(self,c)):
                return {'status':'inspection_finished','retryable':False,'next_action':'report'}
            frozen = {}
            if payload.get('_source_context'):
                from runtime.live_review import check_context
                check_context(c, self, payload['_source_context'])
            old=c.execute('SELECT digest FROM submissions WHERE id=?',(digest,)).fetchone()
            if old:return {'status':'already_saved','segment_id':payload.get('segment_id')}
            from runtime.finishing import advance, closed
            finish=advance(self,c)
            s=self._segment(c,payload.get('segment_id'))
            if not s:raise ValueError('unknown segment')
            if s['review_status']=='skipped' and s.get('policy_version'):
                return {'status':'window_expired','retryable':False,'reason':s['skip_reason'],'next_action':'report' if finish.get('phase')=='completed' else 'review-next'}
            if s['review_status']=='skipped' and s.get('skip_code')=='ASR_RETRY_EXHAUSTED':raise ValueError('segment skipped')
            if closed(finish):return {'status':'inspection_finished','retryable':False,'next_action':'report'}
            revision=payload.get('evidence_revision')
            if type(revision) is not int or revision!=s.get('evidence_revision',1):raise ValueError('evidence changed; read segment again')
            if s['review_status']=='done':raise ValueError('segment already reviewed')
            from runtime.full_live import enabled as full
            if full(self._task(c)):
                from runtime.live_review import bind
                bind(c,self,payload,s)
            from runtime.full_live import ready as evidence_ready
            if not evidence_ready(self._task(c),s):raise ValueError('segment evidence not ready')
            rules={r['id']:r for r in self._task(c)['rules_snapshot']['rules']}
            rows=payload.get('rules')
            if not isinstance(rows,list) or len(rows)!=len(rules) or {r.get('rule_id') for r in rows if isinstance(r,dict)}!=set(rules):raise ValueError('each frozen rule requires one decision')
            evidence={x['id']:dict(x,kind='asr') for x in s.get('subtitles',[])}
            evidence.update({x['id']:dict(x,kind='image') for x in s.get('frames',[])})
            route=payload.get('content_route')
            task=self._task(c)
            routing_required=task.get('rules_mode')=='dynamic' and task.get('rule_routing_version')==1
            if routing_required or (task.get('inspection_policy') in {'lite_live_realtime_v1','lite_live_realtime_v2'} and route is not None):
                allowed_routes = task_scenarios(task) | {'general', 'undetermined'}
                if not isinstance(route,dict) or route.get('type') not in allowed_routes or not isinstance(route.get('reason'),str) or not route['reason'].strip():raise ValueError('content route required')
                refs=route.get('evidence_ids')
                needs_evidence=bool(evidence) if routing_required else bool(s.get('subtitles'))
                if (not isinstance(refs,list) or any(not isinstance(ref,str) or ref not in evidence for ref in refs)
                        or len(set(refs))!=len(refs) or (needs_evidence and not refs)
                        or (routing_required and not evidence and route['type']!='undetermined')):
                    raise ValueError('content route requires actual evidence')
                loaded=task.get('loaded_rule_bundles',[])
                if task.get('rules_mode') == 'dynamic' and route['type'] in SCENARIOS and route['type'] not in loaded and route['type'] not in task.get('rule_load_gaps',{}):
                    raise ValueError('specialist rules must be loaded before judgment')
            viewed=payload.get('images_viewed',[])
            if not isinstance(viewed,list) or any(i not in evidence or evidence[i]['kind']!='image' for i in viewed):raise ValueError('invalid viewed image IDs')
            if routing_required and any(evidence[ref]['kind']=='image' and ref not in viewed for ref in route['evidence_ids']):
                raise ValueError('image must be viewed before judgment')
            from runtime.full_live import speech_can_clear
            can_clear_speech = speech_can_clear(self._task(c), s)
            result=[]
            for rule_index,row in enumerate(rows):
                try:
                    status=row.get('status');rule=rules[row['rule_id']]
                    if status not in DECISIONS or not isinstance(row.get('reason'),str) or not row['reason'].strip():raise ValueError('invalid semantic decision')
                    if status=='no_hit':
                        if 'speech' in rule['modalities'] and not can_clear_speech:raise ValueError('missing ASR cannot clear speech rule')
                        if 'image' in rule['modalities'] and (self._task(c).get('image_inspection',True) or 'speech' not in rule['modalities']) and (s['frame_status']!='success' or not s['frames'] or not all(f['id'] in viewed for f in s['frames'])):raise ValueError('missing or unseen frames cannot clear image rule')
                    events=row.get('events',[])
                    if not isinstance(events,list) or (status=='hit' and not events) or (status!='hit' and events):raise ValueError('hits require evidence events only')
                    bound=[]
                    for event in events:
                        refs=event.get('evidence_ids')
                        if not isinstance(refs,list) or not refs or any(r not in evidence for r in refs):raise ValueError('foreign evidence')
                        items=[evidence[r] for r in refs]
                        if len(set(refs)) != len(refs):raise ValueError('duplicate evidence IDs')
                        counterpart_refs=event.get('counterpart_evidence_ids',[])
                        if not isinstance(counterpart_refs,list) or any(ref not in evidence for ref in counterpart_refs) or len(set(counterpart_refs)) != len(counterpart_refs):raise ValueError('invalid counterpart evidence')
                        check_event_gate(rule,event,evidence)
                        all_items=items+[evidence[ref] for ref in counterpart_refs]
                        if any(('speech' if e['kind']=='asr' else 'image') not in rule['modalities'] for e in all_items):raise ValueError('evidence channel not allowed by rule')
                        if any(e['kind']=='image' and e['id'] not in viewed for e in all_items):raise ValueError('image must be viewed before judgment')
                        speech=[e['text'] for e in items if e['kind']=='asr']
                        if any(e['kind']=='image' for e in all_items) and not str(event.get('description','')).strip():raise ValueError('image description required')
                        if any(min(s['end_ms'],e.get('end_ms',e.get('time_ms',0)+1000))<=max(s['start_ms'],e.get('start_ms',e.get('time_ms'))) for e in all_items):raise ValueError('evidence outside segment')
                        a=max(s['start_ms'],min(e.get('start_ms',e.get('time_ms')) for e in items))
                        b=min(s['end_ms'],max(e.get('end_ms',e.get('time_ms',0)+1000) for e in items))
                        if b<=a:raise ValueError('evidence outside segment')
                        bound.append({**({k:event[k] for k in ('claim_basis','claim_quote','comparison_scope','counterpart_quote') if k in event} if rule.get('evidence_gate')=='claim_specific' else {}),'evidence_ids':refs,'counterpart_evidence_ids':counterpart_refs,'start_ms':a,'end_ms':b,'text':event.get('description') or ''.join(speech)})
                        from runtime.remediation import enabled as remediation_enabled, normalize as normalize_remediation
                        if remediation_enabled(self._task(c)) and "remediation" in event:
                            bound[-1]['remediation'] = normalize_remediation(event['remediation'], source='compliance', rule_id=row['rule_id'])
                    decision={'rule_id':row['rule_id'],'status':status,'result':status,'reason':row['reason'],'events':bound}
                    if full(self._task(c)):
                        from runtime.full_live import speech_only_scope
                        speech_only=speech_only_scope(self._task(c))
                        channels=row.get('channels')
                        if not isinstance(channels,dict) or set(channels)!=set(rule['modalities']):raise ValueError('each rule channel requires a decision')
                        for channel,answer in channels.items():
                            allowed=DECISIONS | ({'not_checked'} if speech_only and channel=='image' else set())
                            if not isinstance(answer,dict) or answer.get('status') not in allowed or not str(answer.get('reason','')).strip():raise ValueError('invalid channel decision')
                            if speech_only and channel=='image' and answer['status']!='not_checked':raise ValueError('disabled image channel must be not_checked')
                            if answer['status']=='no_hit' and channel=='image' and (not s.get('frames') or not all(f['id'] in viewed for f in s['frames'])):raise ValueError('unseen image channel cannot be cleared')
                            if answer['status']=='no_hit' and channel=='speech' and not can_clear_speech:raise ValueError('missing speech channel cannot be cleared')
                            if answer['status']=='hit' and not any(any(evidence[i]['kind']==('asr' if channel=='speech' else 'image') for i in e['evidence_ids']) for e in bound):raise ValueError('channel hit requires matching evidence')
                        if status=='hit' and not any(v['status']=='hit' for v in channels.values()):raise ValueError('hit requires a hit channel')
                        if status=='no_hit' and any(v['status'] in {'hit','insufficient'} for v in channels.values()):raise ValueError('channel result contradicts conclusion')
                        if speech_only and 'speech' in channels:
                            if channels['speech']['status'] not in {'hit','no_hit','insufficient'}:
                                raise ValueError('speech-only conclusion must be a speech judgment')
                            if not can_clear_speech and status not in {'hit','insufficient'}:
                                raise ValueError('missing speech evidence requires insufficient')
                        if speech_only and (status!=channels['speech']['status'] if 'speech' in channels else status!='not_applicable'):
                            raise ValueError('speech-only conclusion must match speech channel')
                        decision['channels']=channels
                        previous=next((r for r in s.get('previous_review_result',{}).get('rules',[]) if r['rule_id']==row['rule_id'] and r['status']=='hit'),None)
                        if previous:
                            # Late visual supplementation cannot erase an already supported speech hit.
                            old_events=previous.get('events',[])
                            unique={tuple(e['evidence_ids']):e for e in old_events+bound}
                            decision.update(status='hit',result='hit',events=list(unique.values()),reason=previous['reason'] if status!='hit' else row['reason'])
                            decision['channels']={**channels,**{k:v for k,v in previous.get('channels',{}).items() if v['status']=='hit'}}
                    result.append(decision)
                except (ValueError,TypeError,KeyError) as error:
                    from runtime.review_contract import enabled as protocol_v2
                    if not protocol_v2(self._task(c)):raise
                    from runtime.review_errors import contextual
                    detail=contextual(error,s['id'],row.get('rule_id') if isinstance(row,dict) else None,rule_index)
                    if str(error) in {'foreign evidence','image must be viewed before judgment','channel hit requires matching evidence'}:
                        detail.allowed_evidence_ids=list(evidence)
                    raise detail from error
            sales = {}
            if 'clarification_observations' in payload:
                from runtime.clarifications import normalize as normalize_clarifications
                sales['clarification_observations'] = normalize_clarifications(payload['clarification_observations'], s, payload.get('_clarification_context', []))
                if '_clarification_required' in payload:
                    from runtime.clarifications import check_coverage
                    sales['clarification_checks'] = check_coverage(payload.get('clarification_checks'),sales['clarification_observations'],payload['_clarification_required'],s)
            elif 'clarification_observations' in s.get('previous_review_result', {}):
                sales['clarification_observations'] = s['previous_review_result']['clarification_observations']
                if 'clarification_checks' in s['previous_review_result']:
                    sales['clarification_checks'] = s['previous_review_result']['clarification_checks']
            if 'sales_observation' in payload:
                from runtime.sales_state import normalize
                sales['sales_observation'] = normalize(payload['sales_observation'], s, viewed, payload.get('_sales_base'), payload.get('_sales_products', []))
            elif s.get('previous_review_result', {}).get('sales_observation'):
                sales['sales_observation'] = s['previous_review_result']['sales_observation']
            if payload.get('_source_context'):
                frozen = json.loads(c.execute('SELECT data FROM review_contexts WHERE id=? AND session_id=?',
                                             (payload['_source_context'], self.session_id)).fetchone()[0])
                if 'viewer_contexts' in frozen:
                    s['viewer_context'] = frozen['viewer_contexts'].get(str(s['id']), {})
            if 'qa_observations' in payload:
                from runtime.interactions import normalize as normalize_qa
                sales['qa_observations'] = normalize_qa(payload['qa_observations'], s, viewed, payload.get('_qa_context', []), sales.get('sales_observation'))
                if frozen.get('qa_check_version') in {1,2} and str(s['id']) not in frozen.get('supplements', {}):
                    from runtime.interactions import check_coverage
                    sales['qa_checks'] = check_coverage(payload.get('qa_checks', []), sales['qa_observations'],
                                                       payload.get('_qa_context', []), s, version=frozen.get('qa_check_version',1),
                                                       required_previous=payload.get('_qa_check_context'))
            elif 'qa_observations' in s.get('previous_review_result', {}):
                sales['qa_observations'] = s['previous_review_result']['qa_observations']
                if 'qa_checks' in s['previous_review_result']:
                    sales['qa_checks'] = s['previous_review_result']['qa_checks']
            if not self._update_segment(c,s['id'],review_status='done',**({'speech_reviewed':True,'speech_review_completed_at':s.get('speech_review_completed_at',time.time())} if full(self._task(c)) else {}),review_result={**sales,**({'content_route':route} if route else {}),'rules':result,'decisions':result,'images_viewed':viewed,**({'summary':payload['summary']} if 'summary' in payload else {})},claim_token=None,lease_until=0,reviewed_at=now_iso(),judgment_elapsed_ms=max(0,round((time.time()-s['review_started_at'])*1000)) if s.get('review_started_at') else None):
                return {'status':'inspection_finished','retryable':False,'next_action':'report'}
            from runtime.realtime_policy import current as realtime_current
            if realtime_current(self._task(c)) and payload.get('batch_id'):
                from runtime.live_review import row, save
                batch = row(c, self.session_id, payload['batch_id'])
                batch['review_progress_at'] = time.time()
                save(c, self.session_id, batch)
            c.execute('INSERT INTO submissions VALUES(?,?,?)',(digest,s['id'],digest))
            if 'sales_observation' in sales:
                payload['_normalized_sales'] = sales['sales_observation']
            if 'clarification_observations' in sales:
                payload['_normalized_clarifications'] = sales['clarification_observations']
            if 'clarification_checks' in sales:
                payload['_normalized_clarification_checks'] = sales['clarification_checks']
            if 'qa_observations' in sales:
                payload['_normalized_qa'] = sales['qa_observations']
            if 'qa_checks' in sales:
                payload['_normalized_qa_checks'] = sales['qa_checks']
            save_decision_trace(c,self,s,digest,self._task(c),rules,evidence,result,payload)
        return {'status':'saved','segment_id':s['id']}

    def _scene_input(self,c):
        task=self._task(c)
        if task.get('scenario_selection')!='pending':return None
        # One closed fast-path segment is enough to choose the initial rule set. This
        # keeps the first decision near one minute while still using real evidence.
        all_segments=self._segments(c)
        segments=[s for s in all_segments if s['start_ms']<SCENE_WINDOW_MS]
        terminal=task.get('capture_status') in {'ended','stopped','failed'} and task.get('worker_status') in {'done','failed'}
        elapsed=max([s['end_ms'] for s in all_segments]+[0])>=SCENE_WINDOW_MS
        ready=bool(all_segments) and (elapsed or terminal) and all(s['frame_status'] in FRAME_DONE and s['asr_status'] in ASR_DONE for s in segments)
        # Expose only evidence inside the scene window, even for a segment crossing it.
        evidence=[{'id':s['id'],'evidence_revision':s.get('evidence_revision'),
                   'frames':[f for f in s['frames'] if f.get('time_ms',f.get('timestamp_ms',0))<SCENE_WINDOW_MS],
                   'subtitles':[u for u in s['subtitles'] if u.get('start_ms',0)<SCENE_WINDOW_MS],
                   'frame_status':s['frame_status'],'asr_status':s['asr_status']} for s in segments]
        token=hashlib.sha256(encode({'task_id':self.task_id,'segments':evidence}).encode()).hexdigest()
        return {'status':'scene_selection_required' if ready else 'scene_waiting',
                'default_scenario':'电商','window_end_ms':SCENE_WINDOW_MS,'selection_token':token if ready else None,
                'segments':evidence if ready else []}

    def confirm_scene(self,value):
        with self.connection(True) as c:
            from runtime.finishing import advance, closed
            if closed(advance(self,c)):
                return {'status':'inspection_finished','retryable':False,'next_action':'report'}
            task=self._task(c);preview=self._scene_input(c)
            if value.get('task_id')!=self.task_id:raise ValueError('task binding mismatch')
            if not preview or preview['status']!='scene_selection_required':raise ValueError('scene evidence not ready or already confirmed')
            if value.get('selection_token')!=preview['selection_token']:raise ValueError('stale scene evidence')
            scene=value.get('scenario')
            if scene not in ('电商','金融'):raise ValueError('scene must be ecommerce or finance')
            if not isinstance(value.get('reason'),str) or not value['reason'].strip():raise ValueError('scene reason required')
            refs=value.get('evidence_ids',[]);viewed=value.get('images_viewed',[])
            frames={f['id'] for s in preview['segments'] for f in s['frames']}
            ids=frames|{u['id'] for s in preview['segments'] for u in s['subtitles']}
            if not isinstance(refs,list) or not isinstance(viewed,list) or not set(refs)<=ids or not set(viewed)<=frames:raise ValueError('foreign scene evidence')
            if not (set(refs)&frames)<=set(viewed):raise ValueError('scene image evidence not viewed')
            if scene=='金融' and not refs:raise ValueError('finance requires observed evidence')
            if any(s.get('review_status')!='pending' for s in self._segments(c)):raise ValueError('cannot switch reviewed task')
            if scene=='金融':task['rules_snapshot']=task['finance_rules_snapshot']
            task.update(scenario=scene,scenario_selection='confirmed',scenario_reason=value['reason'],scenario_evidence_ids=refs)
            task.pop('finance_rules_snapshot',None)
            self._set_task(c,task)
            return {'task_id':self.task_id,'scenario':scene,'status':'scene_confirmed','next_action':'review-next'}

    def _legacy_claim(self,*,known_rules_version=None,include_deferred=False):
        with self.connection(True) as c:
            from runtime.finishing import advance, closed
            finish=advance(self,c)
            if closed(finish):
                return {'task_id':self.task_id,'segment':None,'finishing':finish,'next_action':'report' if finish['phase']=='completed' else 'status','inspection_finished':True}
            preview=self._scene_input(c)
            if preview is not None:
                return {'task_id':self.task_id,'session_id':self.session_id,'segment':None,**preview}
            for s in self._segments(c):
                if s['review_status'] in {'done','skipped'}:continue
                if s['review_status']=='deferred' and not include_deferred:continue
                if s['frame_status'] not in FRAME_DONE or s['asr_status'] not in ASR_DONE:continue
                if s['review_status']=='deferred' and include_deferred and not (s.get('review_defer') or {}).get('resuming'):
                    self._update_segment(c,s['id'],review_defer={**s['review_defer'],'resuming':True},review_attempts=None)
                # Legacy claimed rows are readable immediately; no ownership or expiry.
                s={k:v for k,v in s.items() if k not in ('claim_token','lease_until','review_attempts')}
                s['review_status']='pending'
                snapshot=self._task(c)['rules_snapshot']
                cached=bool(known_rules_version) and known_rules_version==snapshot.get('version')
                rules={'version':snapshot['version'],'cached':True,'rule_ids':[r['id'] for r in snapshot['rules']]} if cached else snapshot
                return {'task_id':self.task_id,'session_id':self.session_id,'segment':s,'rules':rules,'finishing':finish}
        return {'task_id':self.task_id,'session_id':self.session_id,'segment':None,'status':self.status()}

    def _legacy_submit(self,payload):
        from runtime.review_errors import ReviewError, review_error
        if not isinstance(payload,dict) or payload.get('task_id')!=self.task_id:raise review_error('task binding mismatch')
        try:digest=hashlib.sha256(encode(payload).encode()).hexdigest()
        except (ValueError,TypeError):raise ReviewError('REVIEW_JSON_INVALID','payload','提交内容必须是合法 JSON。') from None
        error=None
        with self.connection(True) as c:
            sid=payload.get('segment_id')
            segment=next((s for s in self._segments(c) if type(sid) is int and s['id']==sid),None)
            budgeted=(self._task(c).get('kind')=='video' and segment is not None
                      and type(payload.get('evidence_revision')) is int
                      and payload['evidence_revision']==segment.get('evidence_revision')
                      and segment['review_status'] not in {'done','skipped'})
            attempts=(segment.get('review_attempts') or []) if budgeted else []
            # Failed digests only: never persist raw input or judgment prose.
            if budgeted and digest in attempts:
                raise ReviewError('REVIEW_INPUT_REPEATED','payload','相同参数已失败，请按错误修正。',sid,
                                  retryable=False,next_action='review-defer' if len(attempts)>=3 else 'repair-review-input')
            if budgeted and len(attempts)>=3:
                raise ReviewError('REVIEW_RETRY_EXHAUSTED','payload','修正重试已达上限，请保留本段待续办。',sid,
                                  retryable=False,next_action='review-defer')
            try:result=self._legacy_submitOne(c,payload,digest)
            except ReviewError as caught:
                error=caught
                if budgeted and caught.detail['next_action']=='repair-review-input':
                    attempts=[*attempts,digest]
                    self._update_segment(c,sid,review_attempts=attempts)
                    error.detail['remaining_retries']=max(0,3-len(attempts))
                    if len(attempts)>=3:error.detail.update(retryable=False,next_action='review-defer')
        # Commit retry accounting before propagating a diagnostic.
        if error:raise error
        return result

    def _legacy_submitOne(self,c,payload,digest):
        from runtime.review_errors import review_error
        sid=payload.get('segment_id');rule_index=event_index=None
        old=c.execute('SELECT digest FROM submissions WHERE id=?',(digest,)).fetchone()
        if old:return {'status':'already_saved','segment_id':sid}
        from runtime.finishing import advance, closed
        if closed(advance(self,c)):
            return {'status':'inspection_finished','retryable':False,'next_action':'report'}
        s=next((s for s in self._segments(c) if type(sid) is int and s['id']==sid),None)
        if not s:raise review_error('unknown segment',sid,rule_index,event_index)
        if s['review_status']=='skipped':
            from runtime.review_errors import ReviewError
            raise ReviewError('SEGMENT_SKIPPED','segment_id','该片段已跳过，请继续其他片段。',sid,retryable=False,next_action='review-next')
        revision=payload.get('evidence_revision')
        if type(revision) is not int or revision!=s.get('evidence_revision',1):raise review_error('evidence changed; read segment again',sid,rule_index,event_index)
        if s['review_status']=='done':raise review_error('segment already reviewed',sid,rule_index,event_index)
        if self._task(c).get('scenario_selection')=='pending':raise review_error('confirm scene before review',sid,rule_index,event_index)
        if s['frame_status'] not in FRAME_DONE or s['asr_status'] not in ASR_DONE:raise review_error('segment evidence not ready',sid,rule_index,event_index)
        rules={r['id']:r for r in self._task(c)['rules_snapshot']['rules']}
        rows=payload.get('rules')
        if not isinstance(rows,list) or len(rows)!=len(rules) or {str(r.get('rule_id')) for r in rows if isinstance(r,dict)}!=set(rules):raise review_error('each frozen rule requires one decision',sid,rule_index,event_index)
        evidence={x['id']:dict(x,kind='asr') for x in s.get('subtitles',[])}
        evidence.update({x['id']:dict(x,kind='image') for x in s.get('frames',[])})
        viewed=payload.get('images_viewed',[])
        if not isinstance(viewed,list) or any(not isinstance(i,str) or i not in evidence or evidence[i]['kind']!='image' for i in viewed):raise review_error('invalid viewed image IDs',sid,rule_index,event_index)
        result=[]
        for rule_index,row in enumerate(rows):
            event_index=None
            status=row.get('status');rule=rules[row['rule_id']]
            if not isinstance(status,str) or status not in DECISIONS:raise review_error('invalid semantic decision',sid,rule_index,event_index)
            if not isinstance(row.get('reason'),str) or not row['reason'].strip():
                error=review_error('invalid semantic decision',sid,rule_index,event_index)
                error.detail['field']=f'rules[{rule_index}].reason'
                raise error
            if status=='no_hit':
                if 'speech' in rule['modalities'] and s['asr_status'] not in ('success','no_audio'):raise review_error('missing ASR cannot clear speech rule',sid,rule_index,event_index)
                if 'image' in rule['modalities'] and (s['frame_status']!='success' or not s['frames'] or not all(f['id'] in viewed for f in s['frames'])):raise review_error('missing or unseen frames cannot clear image rule',sid,rule_index,event_index)
            events=row.get('events',[])
            if not isinstance(events,list) or (status=='hit' and not events) or (status!='hit' and events):raise review_error('hits require evidence events only',sid,rule_index,event_index)
            bound=[]
            for event_index,event in enumerate(events):
                if not isinstance(event,dict):raise review_error('invalid evidence event',sid,rule_index,event_index)
                refs=event.get('evidence_ids')
                if not isinstance(refs,list) or not refs or any(not isinstance(r,str) or r not in evidence for r in refs):raise review_error('foreign evidence',sid,rule_index,event_index)
                items=[evidence[r] for r in refs]
                if len(set(refs)) != len(refs):raise review_error('duplicate evidence IDs',sid,rule_index,event_index)
                counterpart_refs=event.get('counterpart_evidence_ids',[])
                if not isinstance(counterpart_refs,list) or any(not isinstance(ref,str) or ref not in evidence for ref in counterpart_refs) or len(set(counterpart_refs)) != len(counterpart_refs):raise review_error('invalid counterpart evidence',sid,rule_index,event_index)
                try:
                    check_event_gate(rule,event,evidence)
                except ValueError as exc:
                    raise review_error(str(exc),sid,rule_index,event_index) from exc
                all_items=items+[evidence[ref] for ref in counterpart_refs]
                if any(('speech' if e['kind']=='asr' else 'image') not in rule['modalities'] for e in all_items):raise review_error('evidence channel not allowed by rule',sid,rule_index,event_index)
                if any(e['kind']=='image' and e['id'] not in viewed for e in all_items):raise review_error('image must be viewed before judgment',sid,rule_index,event_index)
                speech=[e['text'] for e in items if e['kind']=='asr']
                if any(e['kind']=='image' for e in all_items) and not str(event.get('description','')).strip():raise review_error('image description required',sid,rule_index,event_index)
                if any(min(s['end_ms'],e.get('end_ms',e.get('time_ms',0)+1000))<=max(s['start_ms'],e.get('start_ms',e.get('time_ms'))) for e in all_items):raise review_error('evidence outside segment',sid,rule_index,event_index)
                a=max(s['start_ms'],min(e.get('start_ms',e.get('time_ms')) for e in items))
                b=min(s['end_ms'],max(e.get('end_ms',e.get('time_ms',0)+1000) for e in items))
                if b<=a:raise review_error('evidence outside segment',sid,rule_index,event_index)
                bound.append({**({k:event[k] for k in ('claim_basis','claim_quote','comparison_scope','counterpart_quote') if k in event} if rule.get('evidence_gate')=='claim_specific' else {}),'evidence_ids':refs,'counterpart_evidence_ids':counterpart_refs,'start_ms':a,'end_ms':b,'text':event.get('description') or ''.join(speech)})
                from runtime.remediation import enabled as remediation_enabled, normalize as normalize_remediation
                if remediation_enabled(self._task(c)) and "remediation" in event:
                    bound[-1]['remediation'] = normalize_remediation(event['remediation'], source='compliance', rule_id=row['rule_id'])
            result.append({'rule_id':row['rule_id'],'status':status,'result':status,'reason':row['reason'],'events':bound})
        if not self._update_segment(c,s['id'],review_status='done',review_result={'rules':result,'decisions':result,'images_viewed':viewed},claim_token=None,lease_until=0,reviewed_at=now_iso(),review_defer=None,review_attempts=None):
            return {'status':'inspection_finished','retryable':False,'next_action':'report'}
        c.execute('INSERT INTO submissions VALUES(?,?,?)',(digest,s['id'],digest))
        save_decision_trace(c,self,s,digest,self._task(c),rules,evidence,result,payload)
        return {'status':'saved','segment_id':s['id']}

    def skip_asr(self,sid,code,**recovery):
        """Close one exhausted segment and fence all outstanding media leases atomically."""
        from runtime.finishing import advance, closed
        with self.connection(True) as c:
            if closed(advance(self,c)):return False
            segment=next((s for s in self._segments(c) if s['id']==sid),None)
            if not segment or segment['review_status'] in {'done','skipped'}:return False
            segment.update(recovery)
            segment.update(review_status='skipped',skip_code='ASR_RETRY_EXHAUSTED',
                           skip_reason='ASR 重试耗尽，已跳过该段判别',skipped_at=now_iso(),
                           asr_status='failed',asr_diagnostic={'category':code})
            for key in ('review_result','claim_token','lease_until'):segment.pop(key,None)
            self._write_segment(c,sid,segment)
            c.execute('DELETE FROM submissions WHERE segment_id=?',(sid,))
            c.execute("""UPDATE media_jobs SET status='skipped',lease_token=NULL,lease_until=NULL,
                last_error_code='ASR_RETRY_EXHAUSTED',updated_at=? WHERE session_id=? AND segment_id=?
                AND status NOT IN ('succeeded','skipped','failed','submission_unknown')""",(time.time(),self.session_id,sid))
            return True

    def read_snapshot(self):
        from runtime.sampling import capture_task, report_store, enabled, WindowStore
        if not isinstance(self,WindowStore) and enabled(self.task()):return report_store(self).read_snapshot()
        self.finish_tick()
        def read(c):
            c.execute('BEGIN')
            task,segments=self._task(c),self._segments(c)
            from runtime.review_contract import enabled as protocol_v2
            if protocol_v2(task) and c.execute("SELECT 1 FROM sqlite_master WHERE name='review_batches'").fetchone():
                from runtime.live_review import rows
                task['_review_batches']=rows(c,self.session_id)
            from runtime.live_room import report as room_report
            from runtime import qa_pipeline
            qa_data=({'qa':qa_pipeline.view(self,conn=c,segments=segments),
                      'qa_processing':qa_pipeline.progress(self,conn=c,task=task,segments=segments)}
                     if qa_pipeline.enabled(task) else {})
            if task.get('qa_pipeline') in ('comments_v1', 'split_v1'):
                qa_data['comment_summary'] = qa_pipeline.monitor_comment_summary(
                    c, self.session_id, purchases=task['qa_pipeline'] == 'comments_v1')
            return task,segments,room_report(self,c,task),qa_data,capture_task(self,c,task)
        task,segments,room,qa_data,coverage_task=self._read_with_retry(read)
        return task,segments,{**self._status(coverage_task,segments),'live_room':room,**qa_data}

    def status(self):
        return self.read_snapshot()[2]

    def _status(self,task,segments):
        finish=task.get('finishing',{})
        terminal=task['capture_status'] in {'ended','stopped','failed'} and task['worker_status'] in {'done','failed','stopped'}
        terminal=terminal or finish.get('phase')=='completed'
        unresolved=sum(s['review_status'] not in {'done','skipped'} for s in segments)
        from runtime import full_live
        media_pending=sum(s['review_status']!='skipped' and not full_live.ready(task,s) for s in segments)
        coverage=capture_coverage(task,segments)
        # May deliver a partial report, but never label failed/missing evidence as clean.
        has_text=any(str(u.get('text','')).strip() for s in segments for u in s.get('subtitles',[]))
        has_review=any(s['review_status']=='done' and s.get('review_result') for s in segments)
        no_review=bool(finish.get('mode')=='bounded' and terminal and not unresolved and not has_review)
        has_visual=full_live.enabled(task) and task.get('image_inspection') is True and any(
            s.get('review_status')=='done' and (s.get('review_result') or {}).get('rules') and any(
                f['id'] in s['review_result'].get('images_viewed',[]) for f in s.get('frames',[])) for s in segments)
        no_text=bool(task.get('media_frozen') and not has_text and not has_visual)
        ready=terminal and bool(segments) and not unresolved and not media_pending and not no_text and not no_review
        safe={k:task.get(k) for k in ('id','task_id','name','scenario','created_at','capture_status','worker_status','failure_stage','kind','source_duration_ms','asr_backend','stop_requested','stop_immediately','stop_reason','stop_audit','review_protocol','finished_at','recovery_state','recovery_attempts')}
        safe.update({k:task.get(k) for k in ('media_frozen','monitor_ended_at','monitored_duration_ms')})
        safe.update({k:task.get(k) for k in ('asr_policy','frames_policy','asr_primary_backend','asr_selection_reason','model_waiting','setup_error','local_backup_status')})
        safe.update({k:task[k] for k in ('failure_diagnostic','capture_diagnostic','stream_diagnostic') if task.get(k)})
        from runtime.context import DIAGNOSTIC_ENUMS
        code=task.get('local_setup_error')
        # 依赖检查可能早于准备任务创建；没有准备 ID 也要展示安全原因。
        safe['local_setup_error']=(code if isinstance(code,str) and code in DIAGNOSTIC_ENUMS['recovery_code'] else 'ASR_RUNTIME_UNAVAILABLE') if code else None
        preparation_id=task.get('asr_fallback_preparation_id') or task.get('model_preparation_id')
        if preparation_id:
            from runtime.model_preparation import status as preparation_status
            safe['model_preparation']=preparation_status(preparation_id)
        from runtime.adaptive_segments import enabled as adaptive
        if adaptive(task):
            captured_end = (task.get('capture_active_span') or {}).get('end_ms', 0)
            published_end = max((s['end_ms'] for s in segments), default=0)
            safe['segmentation'] = task['segmentation']
            safe['open_segment_ms'] = max(0, captured_end-published_end) if task.get('capture_status')=='running' else 0
        safe.update({k:task.get(k) for k in ('pipeline_version','asr_startup','asr_route','live_subtitle','inspection_policy','frame_required','image_inspection','review_scope_version')})
        if safe.get('asr_startup'):
            safe['asr_startup']={**safe['asr_startup'],'remaining_seconds':max(0,round(safe['asr_startup'].get('deadline_at',0)-time.time(),1)) if safe['asr_startup'].get('status')=='preparing' and safe['asr_startup'].get('deadline_at') is not None else None}
        safe['remote_routing']={kind:{k:v for k,v in task.get(kind+'_remote_route',{}).items() if k in {'state','retry_at'}} for kind in ('asr','frames')}
        safe['delivery_mode']=task.get('delivery_mode','local_dashboard')
        asr_attention=sum(s['review_status']!='skipped' and s['asr_status'] in {'failed','timed_out','submission_unknown'} for s in segments)
        asr_pending=sum(s['review_status']!='skipped' and s['asr_status'] not in ASR_DONE for s in segments)
        from runtime.mediakit import asr_health
        health=asr_health(segments,task)
        pipeline={
            'capture':{'status':task.get('capture_status','pending')},
            'processing':{'status':'done' if finish.get('phase')=='completed' else task.get('worker_status','pending'),'failure_stage':task.get('failure_stage')},
            'asr':{**health,'status':'stopped' if finish.get('phase')=='completed' and any(s['review_status']=='skipped' for s in segments) else 'needs_attention' if asr_attention or health['submissions_paused'] else 'pending' if asr_pending else 'ok',
                   'attention_segments':asr_attention,'pending_segments':asr_pending},
        }
        from runtime.finishing import summary
        progress={'captured_ms':coverage['captured_ms'],
                  'recognized_ms':interval_ms([s for s in segments if s['asr_status'] in {'success','no_audio'}]+[u for s in segments if s.get('speech_gaps') for u in s['subtitles']]),
                  'reviewed_ms':interval_ms([s for s in segments if s['review_status']=='done' or (full_live.enabled(task) and s.get('speech_reviewed'))]),
                  'judgment_backlog_ms':interval_ms([s for s in segments if s['review_status']=='pending' and full_live.ready(task,s)])}
        speech_only=full_live.speech_only_scope(task)
        evidence_pending=sum(s['asr_status'] not in ASR_DONE or (not speech_only and s['frame_status'] not in FRAME_DONE) for s in segments)
        evidence_failures=sum(s['asr_status'] in {'failed','timed_out','submission_unknown'} or
                              (not speech_only and s['frame_status'] in {'failed','unavailable'}) for s in segments)
        return {**({'full_live':full_live.progress(task,segments)} if full_live.enabled(task) else {}),'progress':progress,'finishing':summary(finish,segments),'task':safe,'segment_count':len(segments),'review_deferred':sum(s['review_status']=='deferred' for s in segments),
                'review_pending':unresolved,'media_pending':media_pending,
                'review_ready_pending':max(0,unresolved-media_pending),
                'report_ready':ready,'report_blocked_reason':'NO_CAPTURED_CONTENT' if not segments and (terminal or no_text) else ('NO_SPEECH' if segments and all(s.get('asr_status')=='no_audio' for s in segments) else 'NO_USABLE_TRANSCRIPT') if no_text else 'NO_REVIEWED_CONTENT' if no_review else 'NO_CAPTURED_CONTENT' if terminal and not segments else None,
                'coverage':coverage,'pipeline':pipeline,
                'evidence_pending':evidence_pending if task.get('review_scope_version')==1 else None,
                'image_disabled_segments':sum(s['frame_status']=='disabled' for s in segments),
                'evidence_gaps':evidence_failures if task.get('review_scope_version')==1 else
                    sum(s['asr_status'] not in ('success','no_audio') or s['frame_status'] not in ('success','not_required','not_scheduled') for s in segments)}
