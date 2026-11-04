"""Python 侧的有界 Node 方法通道与命令元数据出口，兼容旧 runtime.telemetry* 调用。
管理进程通信、普通/诊断队列和收尾等待，转交发送请求，不在桥接层重新推导任务结果。
"""
import atexit
from contextlib import contextmanager
import io
import json
import os
from pathlib import Path
import queue
import re
import shutil
import signal
import stat
import subprocess
import sys
import threading
import uuid
from types import SimpleNamespace
import sqlite3
from runtime.context import persistent, dimensions, safe_dimensions, DIAGNOSTIC_ENUMS, ENUMS, ERRORS, ERROR_DETAILS

ROOT = Path(__file__).resolve().parents[2] / 'lite'
CHILD_MARKER = 'BYTEDLIVE_LITE_TELEMETRY_CHILD'
_CONTEXT = 'BYTEDLIVE_LITE_TELEMETRY_IDENTITY'
_KEYS = json.loads((ROOT.parent / 'telemetry/telemetry-events.json').read_text(encoding='utf-8'))
TASK, FUNNEL, ASR, STOP = (SimpleNamespace(**_KEYS[k]) for k in ('task','funnel','asr','stop'))
COMMANDS = frozenset(_KEYS['lite'].values())
BRIDGE_COMMANDS = COMMANDS | {'doctor','status','resume','refresh-credentials','asr-reconcile','review-next','review-state','rules-load','review-submit','prepare-runtime','start-video','batch-create','batch-next','batch-status','batch-stop','recap-input','recap-submit','report-delivery-ack','delivery-ack','result-page','scene-confirm','review-defer','snapshot'}
_METADATA = {}
_CHANNEL_FD = None
_MAX_BYTES = 4 * 1024 * 1024


def enabled():
    return os.environ.get('BYTEDLIVE_TELEMETRY_DISABLED','').strip().lower() not in ('1','true') and _CONTEXT in os.environ


@contextmanager
def task_scope(task):
    """独立后台或快速写入进程沿用已跟踪任务身份，不创建命令或历史任务事件。"""
    if os.environ.get('BYTEDLIVE_TELEMETRY_DISABLED','').strip().lower() in ('1','true'):
        yield
        return
    previous = os.environ.get(_CONTEXT)
    record = task.get('_telemetry')
    if record:
        os.environ[_CONTEXT] = json.dumps(record.get('owner') or {})
    try:
        yield
    finally:
        if os.environ.get(_CONTEXT) != previous:
            try:drain()
            except Exception:pass
        if previous is None:os.environ.pop(_CONTEXT, None)
        else:os.environ[_CONTEXT] = previous


def capability():
    if os.environ.get('BYTEDLIVE_TELEMETRY_DISABLED','').strip().lower() in ('1','true'):
        return {'status':'disabled'}, None
    node = shutil.which('node')
    if not node:return {'status':'missing_node'}, None
    try:
        probe = subprocess.run([node,'--version'],capture_output=True,text=True,timeout=1)
        match = re.fullmatch(r'v(\d+)\.\d+\.\d+\s*',probe.stdout)
        if probe.returncode or not match or int(match[1]) < 20:return {'status':'unsupported_node'}, None
    except (OSError,ValueError,subprocess.SubprocessError):return {'status':'unavailable'}, None
    if not (ROOT.parent/'telemetry/bridge.mjs').is_file() or not (ROOT.parent/'telemetry/vendor/tooling-telemetry.cjs').is_file():
        return {'status':'unavailable'}, None
    return {'status':'available'}, node


def prepare_identity_directory(directory):
    from runtime.platform_support import private_directory
    private_directory(directory)


class NodeChannel:
    def __init__(self):
        self.lock = threading.Lock()
        self.child = None
        self.pid = os.getpid()

    def close(self,force=False):
        child, self.child = self.child, None
        if child is None:return
        if force:
            try:child.kill()
            except OSError:pass
        try:
            child.stdin.close()
            child.wait(timeout=3.5)
        except (OSError,ValueError,subprocess.SubprocessError):
            try:child.kill(); child.wait(timeout=.2)
            except (OSError,subprocess.SubprocessError):pass
        for stream in (child.stdin,child.stdout):
            try:stream.close()
            except (OSError,ValueError):pass

    def start(self):
        node = os.environ.get('BYTEDLIVE_LITE_TELEMETRY_NODE')
        if not node:_, node = capability()
        if not node:raise RuntimeError('Telemetry runtime unavailable')
        from runtime.credentials import background_env
        self.child = subprocess.Popen([node,str(ROOT.parent/'telemetry/bridge.mjs'),'--python'],
            stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,env=background_env(),bufsize=0)

    def call(self,method,facts,context):
        if self.pid != os.getpid():
            # A fork never reuses its parent's pipes or mutex.
            self.pid=os.getpid();self.child=None;self.lock=threading.Lock()
        encoded=(json.dumps({'method':method,'facts':facts,'context':context},ensure_ascii=False,allow_nan=False)+'\n').encode()
        if len(encoded)>_MAX_BYTES:return None
        with self.lock:
            try:
                if self.child is None or self.child.poll() is not None:self.close();self.start()
                child=self.child
                written=queue.Queue(maxsize=1)
                responses=queue.Queue(maxsize=1)
                notify=method=='send' and not facts.get('wait')
                # 每次交换只用一个工作线程；同一锁内写入并读取，保留写/读各自的时限。
                def exchange():
                    try:
                        remaining=memoryview(encoded)
                        while remaining:
                            count=child.stdin.write(remaining)
                            if not count:raise OSError('Channel closed')
                            remaining=remaining[count:]
                        written.put_nowait(True)
                        if notify:return
                        reader=io.BufferedReader(child.stdout)
                        try:
                            line=reader.readline(_MAX_BYTES + 1)
                            responses.put_nowait(line if line and len(line)<=_MAX_BYTES else None)
                        finally:reader.detach()
                    except (OSError,ValueError):
                        try:written.put_nowait(False)
                        except queue.Full:pass
                        try:responses.put_nowait(None)
                        except queue.Full:pass
                threading.Thread(target=exchange,daemon=True).start()
                if not written.get(timeout=2):raise OSError('Channel closed')
                if notify:return True
                line=responses.get(timeout=4)
                if line is None:raise OSError('Channel closed')
                response=json.loads(line)
                if response.get('error'):return None
                return response.get('value')
            except (OSError,ValueError,RuntimeError,queue.Empty,subprocess.SubprocessError):
                self.close(force=True)
                return None


_rpc_channel = NodeChannel()
atexit.register(_rpc_channel.close)


def request(method, facts=None):
    if os.environ.get('BYTEDLIVE_TELEMETRY_DISABLED','').strip().lower() in ('1','true'):return None
    if not enabled() and method != 'report_runtime_failure':return None
    try:
        from runtime.artifacts import cache_root
        context={'cacheRoot':str(cache_root()),'python':sys.executable}
        return _rpc_channel.call(method,facts or {},context)
    except Exception:return None


def wait_windows(command):
    try:child=subprocess.Popen(command,creationflags=getattr(subprocess,'CREATE_NEW_PROCESS_GROUP',0x200))
    except OSError:return None
    try:return child.wait()
    except KeyboardInterrupt:
        try:child.send_signal(signal.CTRL_BREAK_EVENT);child.wait()
        except (KeyboardInterrupt,OSError):
            try:child.kill();child.wait()
            except OSError:pass
        return 130
    except OSError:return 1


def enter_bridge():
    if os.environ.pop(CHILD_MARKER,None)=='1':return
    args=sys.argv[1:]
    if not args or args[0] not in BRIDGE_COMMANDS or '--help' in args or '-h' in args:return
    _,node=capability()
    if not node:return
    command=[node,str(ROOT.parent/'telemetry/bridge.mjs'),sys.executable,str(ROOT/'scripts/live_inspect.py'),*args]
    if os.name=='nt':
        code=wait_windows(command)
        if code is not None:raise SystemExit(code)
        return
    try:os.execv(node,command)
    except OSError:pass


def open_channel():
    global _CHANNEL_FD
    marker=os.environ.pop('INSPECT_TELEMETRY_FD',None)
    if marker!='3' or os.environ.get(CHILD_MARKER)!='1':return
    fd=3
    try:
        os.set_inheritable(fd,False)
        if os.environ.get('BYTEDLIVE_TELEMETRY_DISABLED','').strip().lower() in ('1','true'):
            os.close(fd);return
        if os.name=='nt':
            import ctypes
            from ctypes import wintypes
            import msvcrt
            kernel=ctypes.WinDLL('kernel32',use_last_error=True)
            kernel.GetFileType.argtypes=[wintypes.HANDLE];kernel.GetFileType.restype=wintypes.DWORD
            kernel.SetNamedPipeHandleState.argtypes=[wintypes.HANDLE,ctypes.POINTER(wintypes.DWORD),ctypes.c_void_p,ctypes.c_void_p]
            kernel.SetNamedPipeHandleState.restype=wintypes.BOOL
            handle=msvcrt.get_osfhandle(fd);mode=wintypes.DWORD(1)
            if kernel.GetFileType(handle)!=3 or not kernel.SetNamedPipeHandleState(handle,ctypes.byref(mode),None,None):raise OSError('Pipe unavailable')
            msvcrt.setmode(fd,os.O_BINARY)
        else:
            mode=os.fstat(fd).st_mode
            if not (stat.S_ISFIFO(mode) or stat.S_ISSOCK(mode)):raise OSError('Pipe required')
            os.set_blocking(fd,False)
        _CHANNEL_FD=fd
        request('outbox_start')
    except Exception:
        try:os.close(fd)
        except OSError:pass


def close_channel():
    global _CHANNEL_FD
    fd,_CHANNEL_FD=_CHANNEL_FD,None
    if fd is None:return
    try:
        if _METADATA.get('failure_component') and _METADATA.get('failure_reason'):
            _METADATA['diagnostic_event_id']=runtime_failure({**_METADATA,'recovery_outcome':_METADATA.get('recovery_outcome','failed')}, wait=True)
        payload=json.dumps(_METADATA,separators=(',',':'),ensure_ascii=True).encode('ascii')
        if len(payload)<=4096:os.write(fd,payload)
    except Exception:pass
    finally:
        try:os.close(fd)
        except OSError:pass


def record_preparation(detail):
    if os.environ.get('BYTEDLIVE_TELEMETRY_DISABLED','').lower() in ('1','true') or _CHANNEL_FD is None:return
    for key in ('prepare_stage','recovery_outcome','recovery_code','download_source','network_failure_kind'):
        if detail.get(key) in DIAGNOSTIC_ENUMS[key]:_METADATA[key]=detail[key]
    value=detail.get('http_status')
    if type(value) is int and 400<=value<=599:_METADATA['http_status']=value
    for key in ('bytes_received','bytes_total','prepare_attempts','recovery_elapsed_ms'):
        value=detail.get(key)
        if type(value) is int and 0<=value<=2**53-1:_METADATA[key]=value

def begin_command(command):
    """Only existing command events get diagnostics; disabled telemetry does no work."""
    _METADATA.clear()
    try:
        if (command not in {'start', 'stop', 'report', 'recap-report'} or
                os.environ.get('BYTEDLIVE_TELEMETRY_DISABLED', '').strip().lower() in ('1', 'true') or
                _CHANNEL_FD is None):
            return
        _METADATA.update(diagnostic_schema_version=1, python_version='.'.join(map(str, sys.version_info[:3])))
        if command == 'start':
            _METADATA.update(startup_stage='input_validation', startup_outcome='unknown')
    except Exception:
        pass

def startup_stage(stage, outcome=None):
    # Stages are memory-only; existing metadata boundaries perform the writes.
    try:
        if 'startup_stage' not in _METADATA:
            return
        if stage in DIAGNOSTIC_ENUMS['startup_stage']:
            _METADATA['startup_stage'] = stage
        if outcome in DIAGNOSTIC_ENUMS['startup_outcome']:
            _METADATA['startup_outcome'] = outcome
    except Exception:
        pass

def record_command_error(error):
    try:
        if not _METADATA.get('diagnostic_schema_version'):
            return
        from runtime.diagnostics import failure_details
        detail = failure_details(error)
        category = ('invalid_input' if isinstance(error, (ValueError, KeyError, TypeError)) else
                    'permission' if isinstance(error, PermissionError) else
                    'not_found' if isinstance(error, FileNotFoundError) else
                    'file_conflict' if isinstance(error, FileExistsError) else
                    'timeout' if isinstance(error, (TimeoutError, subprocess.TimeoutExpired)) else
                    'sqlite' if isinstance(error, sqlite3.Error) else
                    'import' if isinstance(error, ImportError) else
                    'io' if isinstance(error, OSError) else
                    'runtime' if isinstance(error, RuntimeError) else 'other')
        _METADATA.update(error_origin='business', error_category=category)
        for key in ('errno', 'winerror', 'sqlite_errorcode'):
            value = detail.get(key) if key == 'sqlite_errorcode' else getattr(error, key, None)
            if type(value) is int and abs(value) <= 2**53 - 1:
                _METADATA[key] = value
        if 'startup_stage' in _METADATA:
            _METADATA['startup_outcome'] = 'failed'
        publish_metadata()
    except Exception:
        pass

def publish_metadata(value=None, *, batch=False, error_code=None, error_detail=None):
    """Merge safe fields in memory; only close_channel writes the final snapshot."""
    if os.environ.get('BYTEDLIVE_TELEMETRY_DISABLED', '').strip().lower() in ('1', 'true'):
        return
    try:
        if _CHANNEL_FD is None:
            return
        if value is not None:
            incoming = dimensions(value, batch=batch)
            if _METADATA.get('workflow_kind') == 'video_batch':
                incoming['workflow_kind'] = 'video_batch'
            _METADATA.update(incoming)
        if error_code is not None and _METADATA.get('diagnostic_schema_version'):
            _METADATA['error_origin'] = 'business'
            if error_code == 'INVALID_INPUT':
                _METADATA.setdefault('error_category', 'invalid_input')
            if 'startup_stage' in _METADATA:
                _METADATA['startup_outcome'] = 'failed'
        if error_code is not None:
            _METADATA['error_code'] = error_code if error_code in ERRORS else 'OPERATION_FAILED'
        if error_detail in ERROR_DETAILS:
            _METADATA['error_detail'] = error_detail
    except Exception:
        pass

def record_runtime_issue(component, reason):
    if os.environ.get('BYTEDLIVE_TELEMETRY_DISABLED', '').strip().lower() in ('1','true') or _CHANNEL_FD is None:return
    if _METADATA.get('failure_component') == 'windows_acl' and component == 'ffmpeg':return
    if component in DIAGNOSTIC_ENUMS['failure_component'] and reason in DIAGNOSTIC_ENUMS['failure_reason']:
        _METADATA.update(failure_component=component, failure_reason=reason)


class Channel:
    def __init__(self,limit=32):
        self.pending=queue.Queue(maxsize=limit);self.lock=threading.Lock();self.worker=None
    def submit(self,event):
        if not self.lock.acquire(blocking=False):return
        try:
            if self.worker is None or not self.worker.is_alive():
                self.worker=threading.Thread(target=self.run,daemon=True);self.worker.start()
            self.pending.put_nowait(event)
        except (queue.Full,RuntimeError):pass
        finally:self.lock.release()
    def run(self):
        while True:
            method,facts=self.pending.get()
            try:request(method,facts)
            except Exception:pass
            finally:self.pending.task_done()

_channel=Channel()
_diagnostics=Channel(128)

def send(events,*,wait=False):
    if not events or not enabled():return
    if wait:return request('send',{'events':events,'wait':True})
    try:
        ordinary=[]
        for event in events:
            if persistent(event):_diagnostics.submit(('submit',{'event':event}))
            else:ordinary.append(event)
        if ordinary:_channel.submit(('send',{'events':ordinary}))
    except Exception:pass
def submit(event):
    if not enabled():return
    try:_diagnostics.submit(('submit',{'event':event}))
    except Exception:pass
def drain(timeout=1):
    import time
    deadline=time.monotonic()+timeout
    for channel in (_diagnostics,_channel):
        with channel.pending.all_tasks_done:
            while channel.pending.unfinished_tasks:
                remaining=deadline-time.monotonic()
                if remaining<=0:return
                channel.pending.all_tasks_done.wait(remaining)

def safe_failure(value):
    from runtime.context import _CONTRACTS
    if not isinstance(value,dict):return {}
    enums=_CONTRACTS['ASR_ENUMS']
    result={k:value[k] for k in ('category','reason','failure_stage','submission_state') if value.get(k) in enums[k]}
    for k in ('exit_code','http_status'):
        v=value.get(k)
        if type(v) is int and (400<=v<=599 if k=='http_status' else abs(v)<=2**31):result[k]=v
    return result
def record(key, result, task=None):
    """业务只传事件 Key 和已有结果；公共归属与发送策略由遥测统一处理。"""
    if not enabled():return
    try:
        event={'command':key,'extra':result}
        if task is not None:
            event['task']={'task_id':task.get('task_id') or task.get('id'),
                           '_telemetry':{'owner':task.get('_telemetry',{}).get('owner',{})}}
        channel=_diagnostics if persistent(event, explicit=key==ASR.DIAGNOSTIC) else _channel
        channel.submit(('send',{'events':[event], **({'wait':True} if channel is _diagnostics else {})}))
    except Exception:pass

def emit(task,**fields):record(ASR.DIAGNOSTIC,fields,task)
emit_recovery=emit
def runtime_failure(detail,task=None,*,wait=False):
    if not enabled():return
    extra={**detail,'diagnostic_event_id':detail.get('diagnostic_event_id') or str(uuid.uuid4())}
    if extra.get('failure_component')=='asr' and extra.get('recovery_code') not in DIAGNOSTIC_ENUMS['recovery_code']:
        extra['recovery_code']='ASR_RUNTIME_UNAVAILABLE'
    if task:extra['task_id']=task.get('task_id') or task.get('id')
    event={'command':'runtime.failure','extra':extra}
    if wait:
        # 只有确认落盘后才把 ID 交给父进程，表示补报通道已接管；失败仍由父进程兜底。
        if request('submit',{'event':event}) is not True:return None
    else:submit(event)
    return extra['diagnostic_event_id']
def report_runtime_failure(detail):
    if _CHANNEL_FD is None:return request('report_runtime_failure',{'detail':detail})


atexit.register(drain)

# Legacy runtime.telemetry* imports forward to the one local rule implementation.
from runtime.lifecycle import owner, new_record, record_event
from runtime.observations import safe as stop_safe, observations as stop_observations
