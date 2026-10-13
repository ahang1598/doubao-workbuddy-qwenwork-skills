"""Isolated Python inference process. No audio upload or host credential access."""
import json
import math
import os
from pathlib import Path
import queue
import re
import shutil
import sys
import subprocess
import threading
import time
import uuid

WORKER = Path(__file__).with_name('asr_worker.py')
BUNDLED_RUNTIME = Path(__file__).resolve().parents[1] / 'resources' / 'local-asr'

def resolve_runtime_root(explicit=None):
    return str(Path(explicit or os.environ.get('LOCAL_ASR_RUNTIME_ROOT') or BUNDLED_RUNTIME).expanduser().resolve())


RETRYABLE = {'ASR_PROCESS_EXITED', 'ASR_INITIALIZE_TIMEOUT', 'ASR_STOP_TIMEOUT'}


class ASRError(RuntimeError):
    def __init__(self, code):
        self.code = code if re.fullmatch(r'ASR_[A-Z_]+', str(code)) else 'ASR_PROTOCOL_ERROR'
        super().__init__(self.code)


class LocalASR:
    def __init__(self, store=None, *, command=None):
        self.store, self.process, self.reader = store, None, None
        self.command = command or [sys.executable, str(WORKER)]
        self.responses = queue.Queue(maxsize=2)
        self.closed = threading.Event()
        self.close_lock = threading.Lock()

    def spawn(self):
        env = {k: v for k, v in os.environ.items() if k in {'PATH', 'TMPDIR', 'TEMP', 'TMP', 'LANG', 'LC_ALL', 'SYSTEMROOT', 'SystemRoot', 'WINDIR', 'HOME', 'USERPROFILE'}}
        from runtime.platform_support import media_popen
        self.process = media_popen(self.command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=subprocess.DEVNULL, env=env, start_new_session=os.name != 'nt' and not os.environ.get('INSPECT_PREPARATION_CHILD'))
        def read():
            try:
                while not self.closed.is_set():
                    line = self.process.stdout.readline(2 * 1024 * 1024 + 1)
                    if not line or len(line) > 2 * 1024 * 1024: break
                    self.responses.put_nowait(json.loads(line))
            except (OSError, ValueError, queue.Full):
                pass
            finally:
                try: self.responses.put_nowait(None)
                except queue.Full: pass
        self.reader = threading.Thread(target=read, daemon=True)
        self.reader.start()

    def request(self, command, *, timeout=30, cancel=None, **fields):
        if self.process is None: self.spawn()
        rid = uuid.uuid4().hex
        try:
            self.process.stdin.write((json.dumps({'id': rid, 'command': command, **fields}) + '\n').encode())
            self.process.stdin.flush()
        except (BrokenPipeError, OSError):
            raise ASRError('ASR_PROCESS_EXITED') from None
        deadline = time.monotonic() + timeout
        if self.store is not None:
            from runtime.live_backlog import remaining
            deadline = min(deadline, time.monotonic()+remaining(self.store.task(),timeout))
        while time.monotonic() < deadline:
            if cancel is not None and cancel.is_set(): raise ASRError('ASR_CANCELLED')
            try: response = self.responses.get(timeout=min(.2, max(.001, deadline-time.monotonic())))
            except queue.Empty: continue
            if response is None: raise ASRError('ASR_PROCESS_EXITED')
            if not isinstance(response, dict) or response.get('id') != rid: raise ASRError('ASR_PROTOCOL_ERROR')
            if response.get('ok') is not True: raise ASRError((response.get('error') or {}).get('code'))
            if not isinstance(response.get('value'), dict): raise ASRError('ASR_PROTOCOL_ERROR')
            return response['value']
        raise ASRError('ASR_STOP_TIMEOUT' if command == 'transcribe' else 'ASR_INITIALIZE_TIMEOUT')

    def initialize(self, cancel=None, timeout=60):
        task = self.store.task()
        fallback = task.get('asr_primary_backend') == 'mediakit' and task.get('asr_fallback_runtime')
        metadata = self.request('initialize', runtime_root=task['asr_fallback_runtime_root'] if fallback else task['asr_runtime_root'],
                                task_root=str(self.store.root), cancel=cancel, timeout=timeout)
        # Frozen resource identity prevents an unnoticed model change during resume.
        frozen = fallback or task.get('asr_runtime') or {}
        if metadata != frozen:
            self.close()
            raise ASRError('ASR_RUNTIME_INCOMPATIBLE')

    def close(self):
        with self.close_lock:
            self.closed.set()
            p = self.process
            if not p: return
            try:
                p.stdin.close()  # EOF disposes the idle model process.
                from runtime.live_backlog import remaining
                p.wait(timeout=max(.001,remaining(self.store.task(),4)) if self.store else 4)
            except (OSError, subprocess.TimeoutExpired):
                try: p.kill()
                except ProcessLookupError: pass
                p.wait()
            if self.reader: self.reader.join(timeout=1)
            p.stdout.close()
            self.process = None


def doctor(runtime_root=None, *, require_single_pass=False, binaries=None, model_only=False):
    binaries = binaries or {}
    checks, issues = {}, []
    for name, command in ([] if model_only else [('ffmpeg', [binaries.get('ffmpeg_bin') or shutil.which('ffmpeg') or 'ffmpeg', '-version']),
                          ('ffprobe', [binaries.get('ffprobe_bin') or shutil.which('ffprobe') or 'ffprobe', '-version'])]):
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=10)
            valid = result.returncode == 0
        except (OSError, ValueError, subprocess.SubprocessError): valid = False
        checks[name] = {'compatible': valid}
        if not valid: issues.append({'code': 'LOCAL_DEPENDENCY_UNAVAILABLE', 'dependency': name})
    metadata = None
    root = resolve_runtime_root(runtime_root)
    if sys.version_info >= (3, 10):
        bridge = LocalASR()
        try: metadata = bridge.request('check', runtime_root=root, timeout=60)
        except (ASRError, OSError) as error:
            issues.append({'code': getattr(error, 'code', 'ASR_PROCESS_EXITED'), 'dependency': 'local-asr'})
        finally: bridge.close()
    else:
        issues.append({'code': 'LOCAL_DEPENDENCY_UNAVAILABLE', 'dependency': 'python>=3.10'})
    if require_single_pass and metadata and metadata.get('asr_mode') != 'single_pass':
        issues.append({'code': 'ASR_SINGLE_PASS_REQUIRED', 'dependency': 'local-asr',
                       'message': '新任务需要单遍离线 Runtime；旧双遍任务需使用旧版 Skill 续办。'})
    return {'ok': not issues, 'ready': not issues, 'backend': 'local', 'binaries': checks, 'warnings': [],
            'runtime': metadata, 'issues': issues}


def normalize_subtitles(result, segment):
    if result.get('dropped_audio_ms') != 0 or not isinstance(result.get('subtitles'), list):
        raise ASRError('ASR_AUDIO_DROPPED' if result.get('dropped_audio_ms') else 'ASR_PROTOCOL_ERROR')
    output = []
    for item in result['subtitles']:
        if not isinstance(item, dict) or not isinstance(item.get('text'), str): raise ASRError('ASR_PROTOCOL_ERROR')
        a, b = item.get('start_ms'), item.get('end_ms')
        if any(type(v) not in (int, float) or not math.isfinite(v) for v in (a, b)):
            raise ASRError('ASR_PROTOCOL_ERROR')
        start, end = segment['start_ms'] + round(a), min(segment['end_ms'], segment['start_ms'] + round(b))
        if a < 0 or b < a or start > end: raise ASRError('ASR_PROTOCOL_ERROR')
        if item['text'].strip():
            output.append({'id': f"asr-{segment['id']}-{len(output)}", 'text': item['text'], 'start_ms': start, 'end_ms': end})
            if isinstance(item.get('asr_quality'), dict):
                output[-1]['asr_quality'] = item['asr_quality']
    return output


class MediaCancellation:
    """Keep recovery cancellable at the task's media deadline, not at 15 seconds."""
    def __init__(self, store, cancel, deadline=None):
        self.store, self.cancel, self.deadline = store, cancel, deadline

    def is_set(self):
        if self.deadline is not None and time.time() >= self.deadline:return True
        if self.cancel is not None and self.cancel.is_set(): return True
        if self.store.task().get('media_frozen'):return True
        finish = self.store.finish_tick()
        return bool(finish and (finish.get('phase') == 'completed' or finish.get('mode') == 'immediate' or
            time.time() >= finish.get('media_deadline_at', float('inf'))))

    def wait(self, seconds):
        deadline=time.monotonic()+seconds
        while not self.is_set():
            remaining=deadline-time.monotonic()
            if remaining<=0:return False
            if self.cancel is not None and hasattr(self.cancel,'wait'):
                self.cancel.wait(min(.1,remaining))
            else:time.sleep(min(.1,remaining))
        return True


class Processor:
    def __init__(self, store):
        self.store, self.bridge = store, None

    def close(self):
        if self.bridge: self.bridge.close()
        self.bridge = None

    def process(self, store, segment, *, cancel=None, defer_failure=False, recovery=False):
        # The OS worker lock owns this attempt. A new worker may rerun interrupted
        # pure local computation, but completed evidence is never recomputed.
        if segment.get('asr_status') in {'success', 'no_audio', 'failed'}: return
        if store.task().get('pipeline_version') == 2:
            cancel = MediaCancellation(store, cancel)
        started=time.monotonic()
        counter = 'asr_recovery_attempts' if recovery else 'asr_attempts'
        limit = 1 if recovery else 2
        attempts = int(segment.get(counter, 0))
        while attempts < limit:
            if cancel is not None and cancel.is_set(): return
            attempts += 1
            if not store.update_segment(segment['id'], asr_status='running', **{counter:attempts}):return
            try:
                if self.bridge is None:
                    self.bridge = LocalASR(store)
                    self.bridge.initialize(cancel)
                if recovery and (not segment.get('audio_file') or not store.local_path(segment['audio_file']).is_file()):
                    raise ASRError('ASR_AUDIO_UNAVAILABLE')
                budget=(segment['end_ms']-segment['start_ms'])/1000 + 90
                result = self.bridge.request('transcribe', audio_path=str(store.root / segment['audio_file']),
                    timeout=min(60, budget) if store.task().get('inspection_policy') == 'lite_live_realtime_v1' else budget, cancel=cancel)
                subtitles = normalize_subtitles(result, segment)
                metrics = {k: result.get(k) for k in ('duration_ms', 'processing_ms', 'dropped_audio_ms', 'asr_mode', 'asr_calls')}
                completion=({'asr_recovery_status':'success','asr_recovery_error':None,
                             'asr_recovery_elapsed_ms':round((time.monotonic()-started)*1000)} if recovery else {})
                gaps=result.get('speech_gaps',[])
                if gaps:
                    store.update_segment(segment['id'],asr_status='failed',subtitles=subtitles,asr_final=True,
                        speech_gaps=[{**g,'start_ms':g['start_ms']+segment['start_ms'],'end_ms':g['end_ms']+segment['start_ms']} for g in gaps],
                        asr_diagnostic={'category':'ASR_EMPTY_SPEECH'})
                    return
                store.update_segment(segment['id'], asr_status='success', subtitles=subtitles,
                                     asr_diagnostic=None, asr_metrics=metrics, **completion)
                return
            except (ASRError, OSError) as error:
                code = getattr(error, 'code', 'ASR_PROCESS_EXITED')
                if code == 'ASR_EMPTY_SPEECH':
                    store.update_segment(segment['id'],asr_status='failed',asr_final=True,
                                         asr_diagnostic={'category':code})
                    return
                self.close()
                if code == 'ASR_CANCELLED':
                    store.update_segment(segment['id'], asr_status='pending', **{counter:attempts if recovery else attempts-1})
                    return
                if code in RETRYABLE and attempts < limit: continue
                store.update_segment(segment['id'], asr_status='fallback_pending' if defer_failure else 'failed', asr_diagnostic={'category': code})
                return
        store.update_segment(segment['id'], asr_status='fallback_pending' if defer_failure else 'failed', asr_diagnostic={'category': 'ASR_RETRY_EXHAUSTED'})
