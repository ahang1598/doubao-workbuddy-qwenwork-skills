"""Finite, resource-only preparation jobs shared by new tasks and explicit setup.

A detached supervisor bounds the child's lifetime. Only the child publishes caches;
media workers merely observe its state and never own or stop its process tree.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
import time
import uuid

from runtime import artifacts
from runtime.platform_support import file_lock, private_directory, process_options, kill_tree

MAX_SECONDS = 2400
ACTIVE = {'queued', 'preparing'}


def job_root(job_id):
    if not re.fullmatch('[a-f0-9]{64}', job_id): raise ValueError('invalid preparation id')
    return artifacts.cache_root() / '.preparation' / job_id


def write(path, value):
    temp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    with open(temp, 'x', encoding='utf-8') as out:
        os.chmod(temp, 0o600)
        json.dump(value, out)
    os.replace(temp, path)


def identity(task):
    # Python executable participates: a cache prepared by another interpreter may
    # be reusable, but its dependency check does not certify this interpreter.
    spec = artifacts.validate_spec(task.get('artifact_specs', {}).get('asr'))
    value = [artifacts.platform_key(), spec['version'], spec['sha256'], sys.executable]
    return hashlib.sha256(json.dumps(value).encode()).hexdigest()


def status(job_id):
    try:
        state = json.loads((job_root(job_id) / 'state.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {'id': job_id, 'status': 'failed', 'code': 'MODEL_PREPARATION_MISSING', 'retryable': True}
    if state['status'] in ACTIVE and time.time() - state.get('heartbeat', 0) > 30:
        return {**state, 'status': 'failed', 'code': 'MODEL_PREPARATION_INTERRUPTED', 'retryable': True}
    return state


def environment():
    # Whitelist instead of forwarding host tokens, cookies, proxy credentials or
    # task inputs. Model endpoints are unsigned HTTPS URLs in the pinned spec.
    names = ('PATH', 'HOME', 'USERPROFILE', 'LOCALAPPDATA', 'XDG_CACHE_HOME', 'SYSTEMROOT',
             'WINDIR', 'TEMP', 'TMP', 'TMPDIR', 'LANG', 'LC_ALL', 'SSL_CERT_FILE', 'SSL_CERT_DIR')
    env = {k: os.environ[k] for k in names if k in os.environ}
    env['INSPECT_MODEL_CACHE_DIR'] = str(artifacts.cache_root())
    env['PYTHONPATH'] = str(Path(__file__).resolve().parents[1])
    return env


_launch_lock = threading.Lock()

def ensure(task):
    """确保任务所需资源已准备完成，状态写入可恢复文件而不是依赖当前进程内存。"""
    # Also serialize threads: OS file locks alone are not a portable thread mutex.
    with _launch_lock:
        return _ensure(task)

def _ensure(task):
    job_id = identity(task)
    private_directory(artifacts.cache_root())
    root = private_directory(job_root(job_id))
    with file_lock(root / 'launch.lock'):
        current = status(job_id)
        if current['status'] in ACTIVE: return current
        # An OS lock closes the stale heartbeat/relaunch race. A live old child
        # can never overwrite a replacement job or download alongside it.
        try:
            with file_lock(root / 'run.lock', timeout=0):
                request = {'artifact_specs': {'asr': task['artifact_specs']['asr']}}
                write(root / 'request.json', request)
                generation=uuid.uuid4().hex
                current = {'generation':generation,'id': job_id, 'status': 'queued', 'stage': 'queued',
                           'heartbeat': time.time(), 'started_at': time.time(), 'code': None}
                write(root / 'state.json', current)
                subprocess.Popen([sys.executable, '-m', 'runtime.model_preparation', 'supervise', job_id, generation],
                                 env=environment(), stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL, **process_options())
        except TimeoutError:
            return {**current, 'status': 'preparing'}
        except OSError:
            current.update(status='failed', code='MODEL_PREPARATION_START_FAILED', retryable=True)
            write(root / 'state.json', current)
        return current


def execute(job_id, generation):
    root = job_root(job_id)
    with file_lock(root / 'run.lock'):
        task = json.loads((root / 'request.json').read_text(encoding='utf-8'))
        state = status(job_id)
        if state.get('generation')!=generation: return
        state.update(status='preparing', stage='initializing')
        mutex = threading.Lock()
        done = threading.Event()
        def progress(**fields):
            with mutex:
                state.update(fields, heartbeat=time.time())
                write(root / 'state.json', state)
        def heartbeat():
            while not done.wait(2): progress()
        pulse = threading.Thread(target=heartbeat, daemon=True)
        progress()
        pulse.start()
        try:
            result = artifacts.prepare(task=task, install=True, model_only=True, progress=progress)
            done.set(); pulse.join()
            issue = (result.get('issues') or [{}])[0]
            progress(status='ready' if result['ready'] else 'failed', stage='ready' if result['ready'] else issue.get('stage'),
                     code=issue.get('code'), retryable=issue.get('retryable', False))
        except Exception:
            done.set(); pulse.join()
            progress(status='failed', code='MODEL_PREPARATION_FAILED', retryable=True)


def supervise(job_id, generation):
    child = subprocess.Popen([sys.executable, '-m', 'runtime.model_preparation', 'execute', job_id, generation],
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             env={**os.environ,'INSPECT_PREPARATION_CHILD':'1'}, **process_options())
    try:
        child.wait(timeout=MAX_SECONDS)
    except subprocess.TimeoutExpired:
        kill_tree(child); child.wait()
    with file_lock(job_root(job_id) / 'launch.lock'):
        current = status(job_id)
        if current.get('generation')==generation and (current['status'] in ACTIVE or current.get('code') == 'MODEL_PREPARATION_INTERRUPTED'):
            current.update(status='failed', code='MODEL_PREPARATION_INTERRUPTED', retryable=True)
            write(job_root(job_id) / 'state.json', current)


def wait(job_id, cancel=None):
    while True:
        state = status(job_id)
        if state['status'] not in ACTIVE: return state
        if cancel is not None and cancel(): return {**state, 'status': 'cancelled'}
        time.sleep(.25)


def inspect(task=None):
    """只读检查本地模型和工具能力，返回可解释的准备状态。"""
    check = artifacts.prepare(task=task, install=False)
    check['model_preparation'] = {'status': 'ready' if check['ready'] else 'missing'}
    try:
        job_id = identity(check)
        if (job_root(job_id) / 'state.json').is_file():
            check['model_preparation'] = status(job_id)
            if check['ready']: check['model_preparation']['status'] = 'ready'
            elif check['model_preparation']['status']=='ready': check['model_preparation']['status']='missing'
    except (ValueError, artifacts.PreparationError): pass
    return check


def start_check(task=None, *, defer_model=False):
    """Prepare shared binaries only; a cold model never blocks the caller."""
    common = artifacts.prepare(task=task, common_only=True)
    if not common['ready']: return common
    if defer_model:
        return {**common,'ready':False,'waiting':True,'model_preparation':{'status':'pending'}}
    frozen = {**(task or {}), 'artifact_specs': common['artifact_specs'], 'runtime_binaries': common['binaries']}
    check = artifacts.prepare(task=frozen, install=False)
    if check['ready']: return check
    # Only a recoverable missing/invalid managed cache can start a download.
    issue = (check.get('issues') or [{}])[0]
    if issue.get('code') != 'ARTIFACT_CACHE_MISSING': return check
    try: state = ensure(frozen)
    except (OSError, ValueError, artifacts.PreparationError):
        check['issues']=[{'code':'MODEL_PREPARATION_START_FAILED','stage':'prepare','retryable':True}]
        return check
    if state['status']=='failed':
        check['issues']=[{'code':state.get('code'),'stage':state.get('stage','prepare'),'retryable':state.get('retryable',False)}]
    check['model_preparation'] = state
    check['waiting'] = state['status'] in ACTIVE or state['status'] == 'ready'
    return check


def prepare_runtime():
    check = start_check()
    if check.get('waiting'):
        state = wait(check['model_preparation']['id'])
        check = artifacts.prepare(task={'artifact_specs': check['artifact_specs'],
                                        'runtime_binaries': check['binaries']}, install=False)
        check['model_preparation'] = state
    return check


def before_capture(store, cancel):
    """采集前执行有界准备，避免把模型下载或环境缺失拖进采集阶段。"""
    task = store.task()
    if not task.get('model_waiting'): return True
    store.update_task(worker_status='preparing', capture_status='pending')
    def stopped():
        store.update_task(worker_heartbeat=time.time())
        return cancel.is_set() or store.should_stop()
    state = wait(task['model_preparation_id'], stopped)
    if state['status'] == 'cancelled' or stopped():
        store.update_task(worker_status='done', capture_status='stopped')
        return False
    if state['status'] == 'ready':
        check = artifacts.prepare(task=store.task(), install=False)
        if check['ready']:
            store.bind_prepared_model(check)
            return True
        state = {'code': (check.get('issues') or [{'code': 'MODEL_PREPARATION_FAILED'}])[0]['code']}
    store.update_task(worker_status='setup_pending', setup_error=state.get('code'), capture_status='pending')
    return False


def record_backup(store, check, *, observed=None):
    """Persist detached preparation outcomes even after cloud startup returns."""
    from runtime.context import DIAGNOSTIC_ENUMS
    state = 'ready' if check.get('ready') else 'preparing' if check.get('waiting') else 'unavailable'
    code = (check.get('issues') or [{}])[0].get('code') if state == 'unavailable' else None
    with store.connection(True) as conn:
        task = store._task(conn)
        if task.get('asr_policy') != 'remote_first':return
        # Cache polling must not overwrite a newer preparation result.
        if observed is not None and state != 'ready' and any(task.get(k) != observed.get(k) for k in
                ('local_backup_status','local_setup_error','model_preparation_id')):return
        if task.get('asr_fallback_runtime') or (task.get('local_backup_status') == 'ready' and state != 'ready'):return
        if state == 'unavailable':code = code or task.get('local_setup_error') or 'ASR_RUNTIME_UNAVAILABLE'
        # 准备失败只保留合同错误码，避免旧任务或异常文本进入状态与遥测。
        if code is not None and (not isinstance(code,str) or code not in DIAGNOSTIC_ENUMS['recovery_code']):code = 'ASR_RUNTIME_UNAVAILABLE'
        changed = (task.get('local_backup_status'), task.get('local_setup_error')) != (state, code)
        task.update(local_backup_status=state, local_setup_error=code)
        job_id = check.get('model_preparation', {}).get('id')
        if not changed and (not job_id or task.get('model_preparation_id') == job_id):return
        if job_id:task['model_preparation_id'] = job_id
        store._set_task(conn, task)
    if changed and state == 'unavailable':
        try:
            from runtime.bridge import runtime_failure
            runtime_failure({'failure_component':'asr','failure_reason':'prepare_failed',
                             'recovery_outcome':'failed','recovery_code':code or 'ASR_RUNTIME_UNAVAILABLE'}, task)
        except Exception:pass


def select_backend(store, cancel, *, budget=15, total_budget=90):
    """在固定预算内选择本地优先或云端回退，并持久化最终后端决策。"""
    """Select once before capture; only missing-model download waits use budget.

    The detached resource job owns retries. Download completion ends the wait
    deadline before extraction/smoke checks and the task's 60s initialization.
    """
    import queue
    from runtime.asr_router import cloud_available
    from runtime.local_asr import LocalASR
    task=store.task()
    if task.get('asr_startup',{}).get('status')=='selected':
        return True,None
    overall_deadline=time.monotonic()+total_budget
    deadline=None; wall_deadline=None; download_complete=False
    results=queue.Queue()
    abandoned=threading.Event()
    def probe(kind,fn):
        try:value=fn()
        except Exception:value={'ready':False,'issues':[{'code':'MODEL_PREPARATION_FAILED'}]}
        if abandoned.is_set():return
        if kind=='local' and task.get('asr_policy')=='remote_first':
            try:record_backup(store,value)
            except Exception:value={'ready':False,'issues':[{'code':'MODEL_PREPARATION_FAILED'}]}
        results.put((kind,value))
    def start_probe():
        if task.get('asr_policy')=='remote_first':record_backup(store,{'waiting':True})
        threading.Thread(target=probe,args=('local',lambda:start_check(task)),daemon=True).start()
    start_probe()
    cloud={'ready':False}
    cloud_done=task.get('asr_policy') not in {'remote_first','local_first'}
    if not cloud_done:
        threading.Thread(target=probe,args=('cloud',lambda:cloud_available(store,probe_timeout=5)),daemon=True).start()
    check=None; job_id=None; checking=True
    initializing=False; init_cancel=threading.Event(); pending_bridge=None
    phase=None
    def report_failure(code):
        # Reporting is optional, including import/queue failures after startup failed.
        try:
            from runtime.bridge import runtime_failure
            safe_code=code  # Node validates the optional diagnostic boundary.
            runtime_failure({'failure_component':'asr','failure_reason':'prepare_timeout' if code=='ASR_STARTUP_TIMEOUT' else 'prepare_failed',
                'recovery_outcome':'failed','recovery_code':safe_code,
                'recovery_elapsed_ms':max(0,round((time.monotonic()-overall_deadline+total_budget)*1000))},store.task())
        except Exception:pass
    def preparing(stage):
        nonlocal phase
        if phase==stage:return
        phase=stage
        messages={'checking':'正在检查本地模型',
                  'downloading':'本地模型缺失，最多等待下载15秒',
                  'verifying':'模型下载已完成，正在校验和准备本地模型',
                  'initializing':'正在初始化本地模型'}
        store.update_task(worker_status='preparing',asr_startup={
            'status':'preparing','stage':stage,'message':messages[stage],
            'deadline_at':wall_deadline if stage=='downloading' else None,
            'cache_hit':None if check is None else bool(check.get('ready') and not job_id)})
    preparing('checking')
    if task.get('asr_policy')=='remote_first':
        store.update_task(asr_startup={'status':'preparing','stage':'cloud','message':'正在检查远端处理能力'})
    def choose(backend,reason,bridge=None):
        with store.connection(True) as conn:
            current=store._task(conn)
            if current.get('stop_requested'):
                init_cancel.set()
                if bridge:threading.Thread(target=bridge.close,daemon=True).start()
                current.update(worker_status='done',capture_status='stopped')
                store._set_task(conn,current)
                return False,None
            current.update(asr_primary_backend=backend,asr_selection_reason=reason,model_waiting=False,
                worker_status='pending',asr_startup={'status':'selected','stage':'selected','deadline_at':None,
                'cache_hit':bool(check and not job_id and check.get('ready')),'backend':backend,'reason':reason})
            if job_id:current['model_preparation_id']=job_id
            if backend=='mediakit':
                current['asr_runtime']=None
                if task.get('asr_policy')!='remote_first':current['local_setup_error']=((check or {}).get('issues') or [{}])[0].get('code')
            store._set_task(conn,current)
        return True,bridge
    while not cancel.is_set() and not store.should_stop():
        if time.monotonic()>=overall_deadline:
            abandoned.set()
            init_cancel.set()
            if pending_bridge:threading.Thread(target=pending_bridge.close,daemon=True).start()
            store.update_task(worker_status='setup_pending',setup_error='ASR_STARTUP_TIMEOUT',
                asr_startup={'status':'failed','stage':phase or 'checking','code':'ASR_STARTUP_TIMEOUT'})
            report_failure('ASR_STARTUP_TIMEOUT')
            return False,None
        try:
            kind,value=results.get(timeout=.1)
            if kind=='cloud':cloud=value;cloud_done=True
            elif kind=='initialized':
                initializing=False
                if value.get('ready'):
                    return choose('local','model_ready',pending_bridge)
                if pending_bridge:
                    threading.Thread(target=pending_bridge.close,daemon=True).start()
                    pending_bridge=None
                check={**check,'ready':False,'waiting':False,'issues':[{'code':value.get('code','ASR_INITIALIZE_FAILED')}]}
            else:
                check=value;checking=False
                job_id=check.get('model_preparation',{}).get('id') or job_id
                if job_id:
                    with store.connection(True) as conn:
                        current=store._task(conn);current['model_preparation_id']=job_id;store._set_task(conn,current)
                if check.get('waiting') and deadline is None:
                    deadline=time.monotonic()+budget
                    wall_deadline=time.time()+budget
                    preparing('downloading')
        except queue.Empty:pass
        if task.get('asr_policy')=='remote_first':
            if cloud.get('ready'):
                return choose('mediakit','preferred_cloud')
            if not cloud_done:continue
        # Observe completion before testing the deadline, so delayed polling does
        # not turn an on-time download into a cloud fallback.
        if job_id and check and check.get('waiting'):
            state=status(job_id)
            completed=state.get('download_completed_monotonic')
            if completed is not None:
                download_complete=completed<=deadline or (cloud_done and not cloud.get('ready'))
            elif state['status']=='ready':
                # Compatibility with preparation jobs started by an older worker.
                download_complete=time.monotonic()<=deadline or (cloud_done and not cloud.get('ready'))
            if download_complete:preparing('verifying')
            if state['status']=='failed':
                check={**check,'waiting':False,'issues':[{'code':state.get('code')}]}
            elif state['status']=='ready' and download_complete and not checking:
                checking=True;start_probe()
        expired=deadline is not None and not download_complete and time.monotonic()>=deadline
        failed=bool(check and not check.get('ready') and not check.get('waiting'))
        if cloud.get('ready') and (expired or failed):
            return choose('mediakit','model_unavailable_cloud' if failed else 'model_wait_timeout_cloud')
        if failed and cloud_done:
            code=(check.get('issues') or [{}])[0].get('code') or 'ASR_RUNTIME_UNAVAILABLE'
            abandoned.set()
            store.update_task(worker_status='setup_pending',setup_error=code,
                             asr_startup={'status':'failed','stage':phase or 'checking','code':code})
            report_failure(code)
            return False,None
        if check and check.get('ready') and not initializing:
            store.bind_prepared_model(check)
            pending_bridge=LocalASR(store);initializing=True
            preparing('initializing')
            def initialize(bridge=pending_bridge):
                try:
                    bridge.initialize(init_cancel,timeout=60)
                    results.put(('initialized',{'ready':True}))
                except Exception as error:
                    results.put(('initialized',{'ready':False,'code':getattr(error,'code','ASR_INITIALIZE_FAILED')}))
                finally:
                    if init_cancel.is_set():bridge.close()
            threading.Thread(target=initialize,daemon=True).start()
        store.update_task(worker_heartbeat=time.time())
    abandoned.set();init_cancel.set()
    if pending_bridge:threading.Thread(target=pending_bridge.close,daemon=True).start()
    store.update_task(worker_status='done',capture_status='stopped')
    return False,None


if __name__ == '__main__':
    {'supervise': supervise, 'execute': execute}[sys.argv[1]](sys.argv[2], sys.argv[3])
