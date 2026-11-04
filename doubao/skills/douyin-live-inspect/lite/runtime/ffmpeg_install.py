"""Install FFmpeg with resumable downloads and bounded stalls and local work."""
# 核心实现模块：负责本模块声明的检测、状态处理或交付边界；敏感输入和原始响应不进入日志。
import json
import http.client
import os
import socket
import ssl
import urllib.error
import urllib.request
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import threading
import uuid
import time

from runtime.platform_support import process_options, kill_tree

POLL_SECONDS = 1
MAX_ATTEMPTS = 3
IDLE_TIMEOUT = 30
WORK_TIMEOUT = 90  # Non-download work only.
LEGACY_URL = "https://www.gyan.dev/ffmpeg/builds/packages/ffmpeg-8.1.2-essentials_build.zip"
CDN_URL = "https://lf6-cdn-tos.douyinstatic.com/obj/livesaas/inspect-lite/ffmpeg/ffmpeg-8.1.2-essentials_build.zip"
GITHUB_URL = "https://github.com/GyanD/codexffmpeg/releases/download/8.1.2/ffmpeg-8.1.2-essentials_build.zip"
PINNED_SHA = "db580001caa24ac104c8cb856cd113a87b0a443f7bdf47d8c12b1d740584a2ec"


def _attempt(key, spec, number, progress):
    from runtime import artifacts
    from runtime.model_preparation import environment
    attempt = '.prepare-ffmpeg-' + uuid.uuid4().hex + '-'
    child = subprocess.Popen([sys.executable, '-m', 'runtime.ffmpeg_install'],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        env=environment(), **process_options())
    handlers={}
    state = {'prepare_stage': 'permissions', 'bytes_received': 0, 'prepare_attempts': number}
    changed = time.monotonic()
    state_lock = threading.Lock()
    notices = []
    pipe = child.stderr
    child.stderr = None  # communicate owns stdout; the reader owns progress stderr.
    def read_progress():
        nonlocal changed
        try:
            while True:
                line = pipe.readline(16385)
                if not line: break
                if len(line) > 16384: break
                value = json.loads(line)
                with state_lock:
                    if value.get('prepare_stage') != state.get('prepare_stage') or value.get('bytes_received', 0) > state.get('bytes_received', 0):
                        changed = time.monotonic()
                    if value.get('prepare_stage') != state.get('prepare_stage'): notices.append(dict(value))
                    state.update(value)
        except (OSError, ValueError, TypeError): pass
        finally: pipe.close()
    reader = threading.Thread(target=read_progress, daemon=True)
    reader.start()
    try:
        if threading.current_thread() is threading.main_thread():
            def interrupted(signum, frame):raise SystemExit(128+signum)
            for name in ('SIGTERM','SIGBREAK'):
                sig=getattr(signal,name,None)
                if sig is not None:
                    handlers[sig]=signal.signal(sig,interrupted)
        data = json.dumps({'key':key,'spec':spec,'prefix':attempt,'attempt':number}).encode()
        previous = None
        last_notice = 0
        while True:
            try:
                raw, _ = child.communicate(data, timeout=POLL_SECONDS)
                break
            except subprocess.TimeoutExpired:
                data = None
                now = time.monotonic()
                with state_lock:
                    detail, idle = dict(state), now-changed
                    pending=list(notices);notices.clear()
                for notice in pending:
                    notify(progress,notice);previous=notice.get('prepare_stage');last_notice=now
                stage = detail['prepare_stage']
                if stage != previous or now-last_notice >= 15:
                    notify(progress, detail); previous=stage; last_notice=now
                # Child enforces the cumulative work budget. Parent also catches
                # a dead coordinator, without imposing a total download deadline.
                if idle > (IDLE_TIMEOUT+5 if stage in {'download','lock','permissions'} else WORK_TIMEOUT+5):
                    from runtime.bridge import record_preparation
                    record_preparation(detail)
                    raise
        reader.join(1)
        for notice in notices:notify(progress,notice)
        if child.returncode or len(raw)>16384:raise artifacts.PreparationError('FFMPEG_PREPARATION_FAILED','ffmpeg',True)
        result=json.loads(raw)
        from runtime.bridge import record_preparation
        record_preparation(result.get('diagnostic', {}))
        if result.get('acl_reason'):
            from runtime.bridge import record_runtime_issue
            record_runtime_issue('windows_acl',result['acl_reason'])
        if 'error' in result:
            failure=artifacts.PreparationError(result['error']['code'],result['error']['stage'],result['error']['retryable'])
            failure.http_status=result['error'].get('http_status')
            failure.network_failure_kind=result['error'].get('network_failure_kind')
            failure.diagnostic=result.get('diagnostic',{})
            raise failure
        return Path(result['root']), result['source'], result
    except BaseException as error:
        try:kill_tree(child)
        except (OSError, subprocess.SubprocessError, KeyboardInterrupt, SystemExit):
            try:child.kill()
            except (OSError, KeyboardInterrupt, SystemExit):pass
        try:child.communicate(timeout=3)
        except (OSError, subprocess.SubprocessError, KeyboardInterrupt, SystemExit):
            try:
                child.kill()
                child.wait(timeout=1)
            except (OSError, subprocess.SubprocessError, KeyboardInterrupt, SystemExit):pass
        if child.poll() is None:
            raise artifacts.PreparationError('FFMPEG_PREPARATION_FAILED','ffmpeg',False) from None
        if isinstance(error, subprocess.TimeoutExpired):
            failure=artifacts.PreparationError('FFMPEG_PREPARATION_STALLED',state['prepare_stage'],True)
            failure.diagnostic=dict(state)
            if state['prepare_stage']=='download':
                failure.network_failure_kind='timeout'
                failure.diagnostic['network_failure_kind']='timeout'
            raise failure from None
        raise
    finally:
        for sig,handler in handlers.items():signal.signal(sig,handler)
        # Never delete staging while a child whose exit is unconfirmed may write it.
        exited = child.poll() is not None
        # Only this invocation's staging directories; never touch published caches.
        def cleanup():
            try:
                parent=artifacts.destination('ffmpeg',key,spec).parent
                for directory in parent.glob(attempt+'*'):
                    if directory.is_dir() and not directory.is_symlink():shutil.rmtree(directory,ignore_errors=True)
            except (OSError, ValueError, KeyError, TypeError):pass
        # Antivirus/blocked filesystem cleanup must not extend the install deadline.
        if exited:
            cleaner=threading.Thread(target=cleanup,daemon=True)
            cleaner.start();cleaner.join(.1)


def install(request, emit=None):
    """Track actual progress, not heartbeats; a stalled installer never owns UI time.

    Runs only in the disposable child. Its daemon cannot survive coordinator exit.
    The parent reaps the whole process group before cleaning staging directories.
    """
    from runtime import artifacts
    spec=request['spec']
    started=time.monotonic();changed=started
    previous_tick=started; work_elapsed=0
    state={'prepare_stage':'permissions','bytes_received':0,'prepare_attempts':request.get('attempt',1)}
    resumed=False
    lock=threading.Lock();done=threading.Event();worker_result={}
    def progress(**fields):
        nonlocal changed,resumed
        update={}
        if 'stage' in fields:update['prepare_stage']=fields['stage']
        for source,target in [('bytes_received','bytes_received'),('bytes_total','bytes_total'),('attempt','prepare_attempts')]:
            if source in fields:update[target]=fields[source]
        with lock:
            if 'resumed_bytes' in fields:resumed=fields['resumed_bytes']>0
            if update.get('prepare_stage',state['prepare_stage'])!=state['prepare_stage'] or update.get('bytes_received',0)>state['bytes_received']:changed=time.monotonic()
            state.update(update)
            if emit:emit(dict(state))
    def smoke(root, spec):
        if not all(artifacts.binary_ok(root/spec['entrypoints'][name],name) for name in ('ffmpeg','ffprobe')):
            raise artifacts.PreparationError('ARTIFACT_SMOKE_FAILED','ffmpeg')
    def work():
        try:
            root,source=artifacts.ensure_artifact('ffmpeg',request['key'],spec,smoke,progress=progress,prefix=request['prefix'],downloader=download)
            worker_result.update(root=str(root),source=source)
        except artifacts.PreparationError as error:worker_result['error']=error.public()
        except PermissionError as error:
            worker_result.update(error={'code':'ARTIFACT_PERMISSION_DENIED','stage':'permissions','retryable':False},
                          acl_reason=getattr(error,'reason',None))
        except Exception:worker_result['error']={'code':'FFMPEG_PREPARATION_FAILED','stage':'ffmpeg','retryable':False}
        finally:done.set()
    threading.Thread(target=work,daemon=True).start()
    while not done.wait(.01):
        now=time.monotonic()
        with lock:idle=now-changed;stage=state['prepare_stage']
        if stage not in {'download','lock'}:work_elapsed+=now-previous_tick
        previous_tick=now
        stalled=stage in {'permissions','lock','download'} and idle>=IDLE_TIMEOUT
        if stalled or work_elapsed>=WORK_TIMEOUT:
            # Use a separate dict: a late installer completion cannot mutate the failure.
            result={'error':{'code':'FFMPEG_PREPARATION_STALLED' if stalled else 'FFMPEG_PREPARATION_TIMEOUT',
                             'stage':'ffmpeg','retryable':True}}
            if stalled and stage=='download':result['error']['network_failure_kind']='timeout'
            break
    else:
        result=dict(worker_result)
    with lock:diagnostic=dict(state)
    if 'error' in result:
        stage=result['error'].get('stage')
        if stage=='ffmpeg':result['error']['stage']=diagnostic['prepare_stage']
        elif stage:diagnostic['prepare_stage']={'verify':'verify_extract','extract':'verify_extract','manifest':'cache'}.get(stage,stage)
    diagnostic.update(recovery_outcome='failed' if 'error' in result else 'success',
                      recovery_code=result.get('error',{}).get('code','none'),
                      recovery_elapsed_ms=round((time.monotonic()-started)*1000))
    if 'http_status' in result.get('error',{}):diagnostic['http_status']=result['error']['http_status']
    if 'network_failure_kind' in result.get('error',{}):diagnostic['network_failure_kind']=result['error']['network_failure_kind']
    return {**result,'diagnostic':diagnostic,'recovered':resumed or diagnostic['prepare_attempts']>1}


def notify(callback, detail):
    if callback:
        try: callback(dict(detail))
        except Exception: pass


def console_progress(detail):
    stage = detail.get('prepare_stage')
    limit = detail.get('attempt_limit',MAX_ATTEMPTS)
    source = {'cdn':'国内 CDN','gyan':'Gyan 原站','github':'GitHub 官方镜像','custom':'配置的下载源'}.get(detail.get('download_source'),'下载源')
    if detail.get('retry'):
        message = f"下载暂时受阻，{'正在切换到' if detail.get('source_changed') else '正在重试'}{source}，第 {detail['prepare_attempts']}/{limit} 次尝试，已下载部分将继续复用。"
    elif stage == 'download':
        message = '正在安装相关依赖，可能会花费一点时间，请耐心等待。安装完成前尚未开始质检。'
        message += f" 已下载 {detail.get('bytes_received',0)}/{detail.get('bytes_total',0)} 字节，第 {detail.get('prepare_attempts',1)}/{limit} 次尝试（{source}）。"
    else:
        message = '正在准备质检依赖：' + {'lock':'等待安装锁','cache':'检查缓存','verify_extract':'校验并解压','smoke':'检查可执行程序','publish':'完成安装','permissions':'检查目录','cleanup':'清理临时文件'}.get(stage,'准备中')
    print(message, file=sys.stderr, flush=True)


def migrated_spec(spec):
    if spec.get('url') == LEGACY_URL and spec.get('version') == '8.1.2' and spec.get('sha256') == PINNED_SHA:
        return {**spec, 'url': CDN_URL}
    return spec


def observation(reason, detail):
    from runtime.bridge import record_preparation, record_runtime_issue
    from runtime.bridge import runtime_failure
    from runtime.transaction import enabled
    if not enabled(): return
    value = {**detail, 'failure_component':'ffmpeg', 'failure_reason':reason}
    try:
        from runtime.task_context import read
        from runtime.bridge import _METADATA, safe_dimensions
        # Match the command bridge's confirmed identity (batch ID for batch commands).
        task = safe_dimensions(_METADATA)
        if not task.get('task_id'):
            directory = os.environ.get('INSPECT_USAGE_CONTEXT_DIR')
            task = read(directory) if directory else None
        event_id = runtime_failure(value, task)
        for field in ('http_status','network_failure_kind','bytes_received','bytes_total'):
            _METADATA.pop(field,None)
        record_preparation(value)
        record_runtime_issue('ffmpeg', reason)
        # ACL has its own event; otherwise bridge and outbox share this observation.
        if _METADATA.get('failure_component') == 'windows_acl':
            _METADATA.pop('diagnostic_event_id',None)
        else:
            _METADATA['diagnostic_event_id'] = event_id
    except Exception: pass


def pinned_package(spec):
    return spec.get('version')=='8.1.2' and spec.get('sha256')==PINNED_SHA and spec.get('bytes')==109728040


def ensure(key, spec, progress=None):
    from runtime import artifacts
    # Custom manifests keep their original source and retry policy.
    mirrors = pinned_package(spec) and spec.get('url')==CDN_URL
    attempts = [('cdn',CDN_URL),('cdn',CDN_URL),('gyan',LEGACY_URL),('github',GITHUB_URL)] if mirrors else [('custom',spec.get('url'))]*MAX_ATTEMPTS
    started = time.monotonic()
    observation('prepare_started', {'prepare_stage':'permissions','recovery_outcome':'pending','prepare_attempts':1,'download_source':attempts[0][0]})
    for number,(label,url) in enumerate(attempts,1):
        def forward(detail):
            notify(progress,{**detail,'attempt_limit':len(attempts),'download_source':label})
        try:
            root, source, result = _attempt(key, {**spec,'url':url}, number, forward)
            observation('prepare_recovered' if result.get('recovered') or number>1 else 'prepare_completed',
                        {**result.get('diagnostic',{}),'recovery_outcome':'success','recovery_code':'none',
                         'download_source':label,'prepare_attempts':number,'recovery_elapsed_ms':round((time.monotonic()-started)*1000)})
            return root, source
        except artifacts.PreparationError as error:
            detail = {**getattr(error,'diagnostic',{}), 'prepare_attempts':number,'download_source':label,
                      'recovery_code':error.code,'recovery_outcome':'failed',
                      'recovery_elapsed_ms':round((time.monotonic()-started)*1000)}
            retry = error.stage == 'download' and ((error.retryable and error.code in {
                'ARTIFACT_NETWORK_ERROR','ARTIFACT_HTTP_ERROR','FFMPEG_PREPARATION_STALLED'}) or
                (mirrors and error.code=='ARTIFACT_HTTP_ERROR'))
            if not retry or number == len(attempts):
                observation('prepare_timeout' if error.code.startswith('FFMPEG_PREPARATION_') and error.code != 'FFMPEG_PREPARATION_FAILED' else 'prepare_failed',detail)
                raise
            observation('prepare_retry', {**detail,'recovery_outcome':'pending'})
            next_label=attempts[number][0]
            notify(progress,{**detail,'prepare_stage':'download','prepare_attempts':number+1,'retry':True,
                'attempt_limit':len(attempts),'download_source':next_label,'source_changed':next_label!=label})
            time.sleep(1 if mirrors else 2**(number-1))


class GithubReleaseRedirect(urllib.request.HTTPRedirectHandler):
    """Allow only the pinned release's HTTPS asset handoff, including its signed query."""
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        from runtime import artifacts
        target=urllib.parse.urlsplit(newurl)
        if (req.full_url != GITHUB_URL or target.scheme!='https' or
            target.hostname!='release-assets.githubusercontent.com' or target.port not in (None,443) or
            target.username or target.password or target.fragment):
            raise artifacts.PreparationError('ARTIFACT_REDIRECT_REJECTED','download')
        return super().redirect_request(req,fp,code,msg,headers,newurl)


def download(spec, path, progress=None):
    """One resumable attempt. ensure owns retries and reaps stalled writers first."""
    from runtime import artifacts
    if path.is_symlink(): raise artifacts.PreparationError('ARTIFACT_PATH_INVALID','download')
    try:
        offset = path.stat().st_size if path.exists() else 0
        if offset >= spec['bytes']:
            if progress:progress(stage='verify_extract')
            if offset == spec['bytes'] and artifacts.sha256(path) == spec['sha256']:
                if progress: progress(stage='download',bytes_received=offset,bytes_total=spec['bytes'],resumed_bytes=offset)
                return
            path.unlink(); offset=0
        if progress: progress(stage='download',bytes_received=offset,bytes_total=spec['bytes'],resumed_bytes=offset)
        headers={'Accept-Encoding':'identity'}
        if offset: headers['Range']=f'bytes={offset}-'
        request=urllib.request.Request(spec['url'],headers=headers)
        redirect=GithubReleaseRedirect() if pinned_package(spec) and spec['url']==GITHUB_URL else artifacts.SafeRedirect()
        with urllib.request.build_opener(redirect).open(request,timeout=15) as response:
            if response.status == 206 and offset:
                if response.headers.get('Content-Range') != f"bytes {offset}-{spec['bytes']-1}/{spec['bytes']}":
                    raise artifacts.PreparationError('ARTIFACT_RANGE_INVALID','download')
            elif response.status == 200:
                if offset and progress:
                    # Reset both coordinators' byte baseline; only new bytes refresh idle time.
                    progress(stage='download',bytes_received=0,bytes_total=spec['bytes'],resumed_bytes=0)
                offset=0
            else: raise artifacts.PreparationError('ARTIFACT_HTTP_ERROR','download')
            total=offset
            with path.open('ab' if offset else 'wb') as out:
                while True:
                    chunk=response.read1(64*1024)
                    if not chunk: break
                    total+=len(chunk)
                    if total>spec['bytes']: raise artifacts.PreparationError('ARTIFACT_SIZE_INVALID','download')
                    out.write(chunk);out.flush()
                    if progress: progress(stage='download',bytes_received=total,bytes_total=spec['bytes'])
        if total<spec['bytes']: raise ConnectionError()
        if progress: progress(stage='verify_extract')
        if artifacts.sha256(path)!=spec['sha256']: raise artifacts.PreparationError('ARTIFACT_HASH_INVALID','verify')
    except artifacts.PreparationError:
        path.unlink(missing_ok=True)
        raise
    except urllib.error.HTTPError as error:
        failure=artifacts.PreparationError('ARTIFACT_HTTP_ERROR','download',error.code in {408,429,500,502,503,504})
        failure.http_status=error.code
        raise failure from None
    except (urllib.error.URLError, TimeoutError, ConnectionError, socket.gaierror, ssl.SSLError, http.client.IncompleteRead) as error:
        cause=getattr(error,'reason',error)
        failure=artifacts.PreparationError('ARTIFACT_NETWORK_ERROR','download',True)
        failure.network_failure_kind=('dns' if isinstance(cause,socket.gaierror) else 'tls' if isinstance(cause,ssl.SSLError)
            else 'timeout' if isinstance(cause,TimeoutError) else 'connection' if isinstance(cause,(ConnectionError,http.client.IncompleteRead)) else 'unknown')
        raise failure from None
    except OSError:
        raise artifacts.PreparationError('ARTIFACT_DISK_ERROR','download') from None


def main():
    request=json.loads(sys.stdin.buffer.read(2*1024*1024+1))
    def emit(detail):
        print(json.dumps(detail),file=sys.stderr,flush=True)
    print(json.dumps(install(request, emit)),flush=True)


if __name__ == '__main__':main()
