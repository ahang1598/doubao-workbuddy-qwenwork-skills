"""Local failure metadata only: never serialize exception text, SQL or locals."""
from pathlib import Path
import json
import os
import time
import sqlite3
import sys
import errno
import re


def capture_process_details(stderr, exit_code):
    """Keep fixed failure categories, never FFmpeg text, URLs, paths or headers."""
    text = stderr[-16384:].lower()
    status = re.search(rb'\b(?:http error|server returned) ([45][0-9]{2})\b', text)
    result = {'category':'http_error' if status else 'process_exit', 'exit_code':exit_code}
    if status:
        result['http_status'] = int(status[1])
        return result
    for pattern, category in (
            (b'unknown encoder', 'encoder_unavailable'),
            (b'permission denied', 'permission_denied'),
            (b'certificate verify failed', 'tls_error'),
            (b'connection timed out', 'network_timeout'),
            (b'connection refused', 'connection_error'),
            (b'connection reset', 'connection_error'),
            (b'failed to resolve hostname', 'connection_error'),
            (b'invalid data found when processing input', 'invalid_media'),
            (b'matches no streams', 'stream_missing'),
            (b'does not contain any stream', 'stream_missing')):
        if pattern in text:
            result['category'] = category
            break
    return result


def is_memory_error(error):
    # Python 3.10 does not export SQLITE_NOMEM; SQLite's primary code is stable.
    return (isinstance(error, MemoryError) or
            isinstance(error, OSError) and error.errno == errno.ENOMEM or
            isinstance(error, sqlite3.Error) and getattr(error, 'sqlite_errorcode', 0) & 255 == getattr(sqlite3, 'SQLITE_NOMEM', 7))


def failure_details(error):
    result = {'category': type(error).__name__, 'frames': []}
    from runtime.http_fetch import safe_failure
    source = safe_failure(getattr(error, 'source_failure', None))
    if source:result['source_failure'] = source
    for key in ('errno', 'winerror'):
        value = getattr(error, key, None)
        if type(value) is int and abs(value) <= 2**53 - 1:
            result[key] = value
    if is_memory_error(error):
        result['code'] = 'OUT_OF_MEMORY'
    if isinstance(error, sqlite3.Error):
        code = getattr(error, 'sqlite_errorcode', None)
        name = getattr(error, 'sqlite_errorname', None)
        if type(code) is int:
            result['sqlite_errorcode'] = code
        if isinstance(name, str) and name.startswith('SQLITE_') and name.isidentifier():
            result['sqlite_errorname'] = name
    runtime = Path(__file__).resolve().parent
    tb = error.__traceback__
    while tb is not None:
        code = tb.tb_frame.f_code
        path = Path(code.co_filename).resolve()
        if path.parent == runtime:
            result['frames'].append({'file': path.name, 'function': code.co_name, 'line': tb.tb_lineno})
        tb = tb.tb_next
    result['frames'] = result['frames'][-8:]
    from runtime.video import VideoError
    if isinstance(error, VideoError):
        result.update(error.diagnostic)
    return result


def log_failure(error, *, stage, attempt=1):
    """Best-effort local diagnostics independent of the failing database."""
    try:
        event = {'event':'runtime_failure', 'time':time.time(), 'pid':os.getpid(),
                 'component':'lite_runtime', 'stage':stage, 'attempt':attempt,
                 'sqlite_version':sqlite3.sqlite_version, 'diagnostic':failure_details(error)}
        from runtime import review_execution
        current = review_execution._current
        if current:
            event.update({key:current[1][key] for key in ('request_id','context_id') if current[1].get(key)})
            # Persist bounded metadata before the supervisor discards untrusted stderr.
            events = [*current[1].get('diagnostics', []), event][-16:]
            review_execution.phase('runtime_failure', diagnostics=events)
        print(json.dumps(event), file=sys.stderr, flush=True)
    except Exception:
        pass  # A broken stderr must never replace the original failure.


def cleanup_actions(actions, primary=None):
    """Attempt every cleanup and return the first failure without masking it."""
    for stage, action in actions:
        try:
            action()
        except BaseException as error:
            log_failure(error, stage=stage)
            if primary is None:
                primary = error
    return primary


def failure_label(task):
    capture_failed = task.get('capture_status') == 'failed'
    worker_failed = task.get('worker_status') == 'failed'
    if not capture_failed and not worker_failed:
        return ''
    for key in ('capture_diagnostic', 'failure_diagnostic', 'stream_diagnostic'):
        diagnostic = task.get(key) or {}
        if diagnostic.get('code') == 'OUT_OF_MEMORY' or diagnostic.get('category') == 'MemoryError':
            return '内存不足，任务处理失败'
        if type(diagnostic.get('sqlite_errorcode')) is int:
            return '本地存储异常，采集已停止'
    if capture_failed and task.get('capture_error')=='BROWSER_SOURCE_TIMEOUT':
        return '浏览器补流等待超时，未取得可采集内容'
    if capture_failed and (task.get('capture_error') in {
            'XHS_FETCH_FAILED','XHS_PAGE_UNAVAILABLE','XHS_AUTH_REQUIRED','XHS_STREAM_UNAVAILABLE','XHS_LIVE_STATE_UNKNOWN','BROWSER_SOURCE_TIMEOUT','BROWSER_SOURCE_TASK_CLOSED','INVALID_BROWSER_SOURCE','DOUYIN_PAGE_UNAVAILABLE', 'DOUYIN_FLV_UNAVAILABLE', 'DOUYIN_FETCH_FAILED'} or
            (not task.get('capture_error') and
             (task.get('capture_diagnostic') or {}).get('category') == 'DouyinResolveError')):
        return '直播页面或流地址解析失败'
    return '采集失败' if capture_failed else '媒体处理失败'


def capture_status_text(task):
    status = task.get('capture_status', 'pending')
    if status == 'failed':
        return failure_label(task)
    if status == 'ended' and task.get('kind', 'live') == 'live':
        return ('直播已结束' if task.get('source_end_reason') == 'offline'
                and task.get('live_source_status') == 'not_live' else '采集已结束，未确认直播停播')
    return {'pending':'待开始', 'running':'进行中', 'stopped':'已停止', 'ended':'已结束'}.get(status, '状态未知')


# Business recovery categories are needed even when telemetry is disabled.
RECOVERY_CODES={'none','ASR_RUNTIME_UNAVAILABLE','ASR_BACKUP_TIMEOUT','ASR_RECOVERY_INTERRUPTED','ASR_RETRY_EXHAUSTED',
                'ASR_EMPTY_SPEECH','ASR_AUDIO_UNAVAILABLE','ASR_PROCESS_EXITED','ASR_INITIALIZE_FAILED',
                'ASR_INITIALIZE_TIMEOUT','ASR_STOP_TIMEOUT','ASR_RUNTIME_INCOMPATIBLE','ASR_PROTOCOL_ERROR','ASR_AUDIO_DROPPED','ASR_TIMEOUT','ASR_CANCELLED','ASR_RECOVERY_FAILED'}

BUSINESS_ERRORS = ['INVALID_INPUT', 'PERMISSION_DENIED', 'TASK_BINDING_MISMATCH', 'OUT_OF_MEMORY', 'OPERATION_FAILED', 'ABORTED', 'RUNTIME_UNAVAILABLE',
    'LOCAL_VIDEO_PATH_REQUIRED', 'VIDEO_SOURCE_UNAVAILABLE', 'VIDEO_SOURCE_CHANGED', 'VIDEO_INVALID', 'VIDEO_START_FAILED',
    'SEGMENT_SKIPPED', 'ASR_EVIDENCE_MISSING', 'VIDEO_RECAP_NOT_SUPPORTED', 'RECAP_EVIDENCE_CHANGED',
    'RECAP_ALREADY_SAVED', 'EVIDENCE_CHANGED', 'FRAMES_NOT_REVIEWED', 'RULES_INCOMPLETE',
    'ALREADY_REVIEWED', 'EVIDENCE_NOT_READY', 'SCENE_REQUIRED']
