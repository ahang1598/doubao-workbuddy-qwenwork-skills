"""在 Lite 业务事务内登记基线、读取必要快照，准备事件并保存可选遥测状态。
提交并关闭连接后才发送，回滚丢弃事件；子任务释放锁后再汇总父批次，不在业务锁内等待网络。
"""
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
import copy
import json
import os
from pathlib import Path
import sqlite3
import time
from runtime import bridge, lifecycle, funnel, observations
from runtime.context import dimensions
from runtime.lifecycle import inspection_result
from runtime.funnel import state, payload, token, video_fingerprint, failed_source_page

_PARENT=ContextVar('telemetry_batch',default=None)
_BATCH_OPERATION=ContextVar('telemetry_batch_operation',default=None)
enabled=bridge.enabled
send=bridge.send
new_record=bridge.new_record
record_event=bridge.record_event
owner=bridge.owner
TASK=bridge.TASK

def now():return datetime.now(timezone.utc).isoformat()


def save_optional(store,connection,task):
    # 调用方持有当前事务快照，只在其中更新遥测字段，无需再次读取。
    connection.execute('UPDATE live_sessions SET data=? WHERE id=?',(json.dumps(task,ensure_ascii=False),store.session_id))


class Connection(sqlite3.Connection):
    telemetry=None


class PendingEvents:
    def __init__(self,store,connection):
        self.store=store;self.connection=connection;self.actions=set();self.baselines={}

    def register(self,kind,before=None,after=None):
        if not enabled():return
        task=before if kind == 'task' and before is not None else self.store._task(self.connection)
        if task.get('kind')=='video':
            from runtime.sampling import report_store
            self.store=report_store(self.store,task=task)
        b,a=before or {},after or {}
        changed={key for key in b.keys() | a.keys() if b.get(key)!=a.get(key)}
        record=task.get('_telemetry',{})
        completion=False
        def funnel_changed():
            if record.get('funnel_schema_version')==1:self.actions.add('funnel')
        if kind=='completion':completion=True
        elif kind=='funnel':funnel_changed()
        elif kind=='segment':
            self.actions.add('dimensions')
            if task.get('_funnel_video_receipt') and changed-{'claim_token','lease_until'}:funnel_changed()
            if before is None or changed & {'review_status','asr_status','frame_status','review_result','skip_code','subtitles','evidence_revision'}:
                funnel_changed();completion=True
        else:
            if b.get('_telemetry'):self.actions.add('dimensions')
            if (changed & (TASK_STATE | {'media_frozen','report_deliveries','recap','live_source_status','source_end_reason','source_error_code','capture_diagnostic'})
                    or (b.get('_funnel_video_receipt') and changed-{'server_pid','server_port','worker_pid','capture_pid'})):
                funnel_changed()
            completion=bool(changed & TASK_STATE)
            if 'worker_status' in changed:
                self.baselines.setdefault('worker_status',b.get('worker_status'));self.actions.add('resume')
            if changed & {'recap','report_deliveries'}:
                self.baselines.setdefault('recap',{k:v for k,v in (b.get('recap') or {}).items() if k in ('status','evidence_version','attempts','failure_code')});self.actions.add('recap')
            if changed & {'stop_requested','stop_audit','stop_reason','capture_status','worker_status','source_end_reason','source_error_code','_progress_diagnostic','_report_diagnostic','finishing'}:
                self.actions.add('stop_observation')
            for key in ('_progress_diagnostic','_report_diagnostic'):
                if a.get(key) and key in changed and key not in self.actions:
                    self.actions.add(key);self.baselines[key]=copy.deepcopy(a[key])
            if (b.get('finishing',{}).get('phase')!='completed' and a.get('finishing',{}).get('phase')=='completed'
                    and a['finishing'].get('diagnostic')):self.actions.add('stop-drain')
        if completion and record and 'completion' not in self.baselines:
            self.baselines['completion']=inspection_result(task,self.store._segments(self.connection))
            self.actions.add('completion')

    def prepare(self):
        if not self.actions or not enabled():return []
        c=self.connection;c.execute('SAVEPOINT optional_telemetry')
        try:
            task=self.store._task(c);r=task.get('_telemetry');b=self.baselines;a=self.actions
            emitted=[]
            if 'dimensions' in a:
                if r:r['dimensions']=dimensions(task,batch=bool(r.get('batch_directory')))
                if task.get('_recap_telemetry'):task['_recap_telemetry']['dimensions']=dimensions(task)
            if ('resume' in a and r and r.get('task_finished_at') and b.get('worker_status') in {'done','failed','stopped'}
                    and task.get('worker_status') in {'preparing','pending','running'}):
                r['dimensions']=dimensions(task,batch=bool(r.get('batch_directory')))
                emitted.append(record_event(TASK.RESUMED,r))
            if 'recap' in a:lifecycle.recap_transition(task,b.get('recap',{}),emitted)
            if 'stop_observation' in a:
                try:
                    from runtime.stop_signal import read
                    observed={**task,'_telemetry':dict(r or {})}
                    pending=observations.observe(observed,read(self.store.root)) or []
                    if observed.get('_telemetry',{}).get('stop_observation'):
                        r['stop_observation']=observed['_telemetry']['stop_observation']
                    emitted.extend(pending)
                except Exception:pass
            for key in ('_progress_diagnostic','_report_diagnostic','stop-drain'):
                if key in a:
                    detail=task.get('finishing',{}).get('diagnostic',{}) if key=='stop-drain' else b[key]
                    emitted.append({'command':'runtime.failure','extra':{**detail,'task_id':task.get('task_id')}})
            segments=self.store._segments(c) if a & {'completion','funnel'} else []
            reviewed=sum(s.get('review_status')=='done' and bool(s.get('review_result')) for s in segments)
            status=None
            if 'funnel' in a:
                try:status=self.store._status(task,segments)
                except Exception:pass
            if 'completion' in a and r and not r.get('task_finished_at'):
                result=inspection_result(task,segments,status['coverage'] if status else None,reviewed=reviewed)
                if result and not b.get('completion'):
                    r['dimensions']=dimensions(task,batch=bool(r.get('batch_directory')))
                    event=record_event(TASK.FINISHED,r,result)
                    skipped=[s for s in segments if s.get('skip_code')=='ASR_RETRY_EXHAUSTED' and s.get('review_status')=='skipped']
                    event['extra'].update(asr_skipped_segments=len(skipped),asr_skipped_ms=sum(s['end_ms']-s['start_ms'] for s in skipped))
                    emitted.append(event)
            if 'funnel' in a and r and r.get('funnel_schema_version')==1 and status:
                try:emitted.append(payload(r,state(self.store,task,segments,c,status,reviewed=reviewed),funnel.source_dimensions(task)))
                except Exception:pass
            save_optional(self.store,c,task)
            emitted=[event for event in emitted if event]
            return emitted
        except Exception:
            c.execute('ROLLBACK TO optional_telemetry')
            return []
        finally:c.execute('RELEASE optional_telemetry')


TASK_STATE={'capture_status','worker_status','stop_requested','finishing','capture_start_ms','capture_end_ms',
            'capture_spans','capture_active_span','capture_observed_ms'}


def _pending(connection):return connection.telemetry if enabled() else None

def task_changing(store,connection,before,after):
    try:
        tx=_pending(connection)
        if tx is not None:tx.register('task',before,after)
    except Exception:pass

def segment_changing(store,connection,sid,before,after):
    try:
        tx=_pending(connection)
        if tx is not None:tx.register('segment',before,after)
    except Exception:pass

def check_inspection_completion(store,connection):
    try:
        tx=_pending(connection)
        if tx is not None:tx.register('completion')
    except Exception:pass

def register(tx):
    if tx is not None:tx.register('funnel')

def start_store(store):
    if not enabled():return
    try:
        with store.connection(True) as c:
            task=store._task(c)
            if task.get('_telemetry'):return
            parent=_PARENT.get()
            r=task['_telemetry']=new_record('video_inspection' if task.get('kind')=='video' else 'live_inspection',task['created_at'],parent[1] if parent else None)
            r['task_id']=parent[2] if parent else task['task_id']
            if parent:r['batch_directory']=str(parent[0])
            r['dimensions']=dimensions(task,batch=bool(parent))
            event=record_event(TASK.STARTED,r)
            save_optional(store,c,task)
        send([event])
    except Exception:pass


def observe_video_delivery(store, receipt, frozen):
    """Called only after a validated report/receipt file commit, never by a query."""
    if not enabled():
        return
    try:
        from runtime.sampling import report_store
        store = report_store(store)
        with store.connection(True) as conn:
            task = store._task(conn)
            if task.get('_telemetry', {}).get('funnel_schema_version') != 1:
                return
            from runtime.video_report import receipt_matches_run
            if not receipt_matches_run(receipt, frozen):
                return
            frozen_task = frozen.task()
            if receipt['report_run'] != task.get('video_report_run', 1):
                return
            frozen_run = (frozen_task.get('_telemetry') or {}).get('run_index')
            if frozen_run != task['_telemetry']['run_index']:
                return  # A delayed observer must not replace this run's receipt.
            fingerprint = receipt.get('fingerprint')
            segments = store._segments(conn)
            evidence = token(frozen_task, frozen.segments())
            if (evidence != token(task, segments) or not fingerprint
                    or fingerprint != video_fingerprint(store, task, segments)):
                return  # Same-run delayed observations must not replace newer reports either.
            task['_funnel_video_receipt'] = {'fingerprint': fingerprint, 'token': evidence,
                'report_run': receipt['report_run'],
                # Use the report's frozen run, not a possibly resumed current task.
                'run_index': frozen_run,
                'ready': receipt['result'].get('status') == 'ready', 'status': receipt['delivery_status']}
            # Optional state only: no business revision or lifecycle side effects.
            conn.execute('UPDATE live_sessions SET data=? WHERE id=?', (json.dumps(task), store.session_id))
            register(conn.telemetry)
    except Exception:
        pass


@contextmanager
def batch_context(root,data):
    record=data.get('_telemetry') if enabled() else None
    token=_PARENT.set((root,record['telemetry_task_id'],data['id']) if record else None)
    try:yield
    finally:_PARENT.reset(token)


@contextmanager
def batch_operation(directory):
    if not enabled():yield;return
    root=Path(directory).expanduser().resolve()
    state={'root':root,'changed':False,'children':{}};token=_BATCH_OPERATION.set(state)
    try:yield
    finally:
        _BATCH_OPERATION.reset(token)
        if state['changed'] or state['children']:observe_batch(root,changed=state['changed'],children=state['children'])


@contextmanager
def batch_changes(data):
    if not enabled():yield;return
    try:before=json.dumps(data,sort_keys=True)
    except Exception:yield;return
    try:yield
    finally:
        try:
            state=_BATCH_OPERATION.get()
            if state is not None and enabled() and before!=json.dumps(data,sort_keys=True):state['changed']=True
        except Exception:pass


def notify_parent(store,events):
    if not events or not enabled():return
    try:
        child=store.task().get('_telemetry',{})
        if child.get('batch_directory') and any(e.get('extra',{}).get('telemetry_task_id')==child.get('telemetry_task_id') for e in events):
            observe_batch(child['batch_directory'],children={child['telemetry_task_id']:child['run_index']})
    except Exception:pass


def observe_batch(directory,created=False,changed=False,children=None):
    if not enabled() or not(created or changed or children):return
    try:
        root=Path(directory).expanduser().resolve();state=_BATCH_OPERATION.get()
        if state is not None and state['root']==root:
            state['changed']|=changed;state['children'].update(children or {});return
        _observe_batch(root,created,children or {})
    except Exception:pass


def _observe_batch(root,created,children):
    from runtime.store import Store,atomic_json
    from runtime.platform_support import fcntl,nofollow_open
    fd=nofollow_open(root/'.batch.lock',os.O_CREAT|os.O_RDWR,0o600)
    with os.fdopen(fd,'w') as lock:
        deadline=time.monotonic()+1
        while True:
            try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);break
            except BlockingIOError:
                if time.monotonic()>=deadline:return
                time.sleep(.01)
        data=json.loads((root/'batch.json').read_text(encoding='utf-8'))
        records=[]
        for index,_ in enumerate(data['videos']):
            path=root/'tasks'/f'{index+1:04d}'
            records.append(Store(path).task().get('_telemetry',{}) if (path/'inspection.db').is_file() else None)
        value=prepare_batch(data,records,created,children)
        if value is None:return
        if value['write']:atomic_json(root/'batch.json',value['data'])
    send(value['events'])


def batch_state(root,data):
    from runtime.store import Store
    children=[]
    for index,_ in enumerate(data['videos']):
        path=Path(root)/'tasks'/f'{index+1:04d}'
        children.append(Store(path).task().get('_telemetry',{}).get('funnel_snapshot',{}).get('state',{}) if (path/'inspection.db').is_file() else {})
    return funnel.batch_state(data,children)


def prepare_batch(data,records,created,children):
    emitted=[];r=data.get('_telemetry')
    if not r:
        if not created:return
        r=data['_telemetry']=new_record('video_batch')
        emitted.append(record_event(TASK.STARTED,r))
    previous=r.get('dimensions');r['dimensions']=dimensions(data,batch=True)
    if emitted:emitted[0]['extra'].update(r['dimensions'])
    observed=r.setdefault('child_runs',{})
    resumed=any(run>observed.get(id,1) for id,run in children.items())
    for id,run in children.items():observed[id]=max(run,observed.get(id,0))
    if r.get('task_finished_at') and resumed:emitted.append(record_event(TASK.RESUMED,r))
    if not r.get('task_finished_at'):
        results=[c.get('task_result') if c is not None else ('failed' if data['videos'][i].get('status')=='failed' else None) for i,c in enumerate(records)]
        active=any(c is not None and not c.get('task_result') for c in records)
        result='completed' if data.get('stopped') and not active else None
        if not result and results and all(results):
            result='completed' if all(r=='completed' for r in results) else 'failed' if all(r=='failed' for r in results) else 'partial'
        if result:emitted.append(record_event(TASK.FINISHED,r,result))
    try:
        event=payload(r,funnel.batch_state(data,[(c or {}).get('funnel_snapshot',{}).get('state',{}) for c in records]),r['dimensions'])
        if event:emitted.append(event)
    except Exception:
        pass  # 漏斗投影失败不能丢弃已生成的批次生命周期事件及结束状态。
    return {'data':data,'events':[e for e in emitted if e],'write':bool(emitted or children or previous!=r['dimensions'])}
