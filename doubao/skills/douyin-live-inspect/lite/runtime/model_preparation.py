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


def select_backend(store, cancel, *, budget=15):
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
    deadline=None; wall_deadline=None; download_complete=False
    results=queue.Queue()
    def probe(kind,fn):
        try:
            value=fn()
            if kind=='local' and task.get('asr_policy')=='remote_first':
                preparation=value.get('model_preparation',{})
                fields={'local_backup_status':'ready' if value.get('ready') else 'preparing' if value.get('waiting') else 'unavailable'}
                if preparation.get('id'):fields['model_preparation_id']=preparation['id']
                # Resource identity is frozen through the preparation owner,
                # including when cloud selection has already returned.
                with store.connection(True) as conn:
                    current=store._task(conn)
                    current.update(fields)
                    store._set_task(conn,current)
            results.put((kind,value))
        except Exception:results.put((kind,{'ready':False,'issues':[{'code':'MODEL_PREPARATION_FAILED'}]}))
    def start_probe():
        threading.Thread(target=probe,args=('local',lambda:start_check(task)),daemon=True).start()
    start_probe()
    cloud={'ready':False}
    cloud_done=task.get('asr_policy') not in {'remote_first','local_first'}
    if not cloud_done:
        threading.Thread(target=probe,args=('cloud',lambda:cloud_available(store,probe_timeout=5)),daemon=True).start()
    check=None; job_id=None; checking=True
    initializing=False; init_cancel=threading.Event(); pending_bridge=None
    phase=None
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
            if backend=='mediakit':current.update(asr_runtime=None,local_setup_error=((check or {}).get('issues') or [{}])[0].get('code'))
            store._set_task(conn,current)
        return True,bridge
    while not cancel.is_set() and not store.should_stop():
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
            store.update_task(worker_status='setup_pending',setup_error=(check.get('issues') or [{}])[0].get('code'))
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
    init_cancel.set()
    if pending_bridge:threading.Thread(target=pending_bridge.close,daemon=True).start()
    store.update_task(worker_status='done',capture_status='stopped')
    return False,None


if __name__ == '__main__':
    {'supervise': supervise, 'execute': execute}[sys.argv[1]](sys.argv[2], sys.argv[3])
