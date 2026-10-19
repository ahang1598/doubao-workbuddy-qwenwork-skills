"""Local failure metadata only: never serialize exception text, SQL or locals."""
from pathlib import Path
import json
import os
import time
import sqlite3
import sys
import errno


def is_memory_error(error):
    # Python 3.10 does not export SQLITE_NOMEM; SQLite's primary code is stable.
    return (isinstance(error, MemoryError) or
            isinstance(error, OSError) and error.errno == errno.ENOMEM or
            isinstance(error, sqlite3.Error) and getattr(error, 'sqlite_errorcode', 0) & 255 == getattr(sqlite3, 'SQLITE_NOMEM', 7))


def failure_details(error):
    result = {'category': type(error).__name__, 'frames': []}
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
    if capture_failed and (task.get('capture_error') in {
            'DOUYIN_PAGE_UNAVAILABLE', 'DOUYIN_FLV_UNAVAILABLE', 'DOUYIN_FETCH_FAILED'} or
            (not task.get('capture_error') and
             (task.get('capture_diagnostic') or {}).get('category') == 'DouyinResolveError')):
        return '直播流不可用，可能已结束'
    return '采集失败' if capture_failed else '媒体处理失败'


def capture_status_text(task):
    status = task.get('capture_status', 'pending')
    if status == 'failed':
        return failure_label(task)
    if status == 'ended' and task.get('kind', 'live') == 'live':
        return '直播已结束'
    return {'pending':'待开始', 'running':'进行中', 'stopped':'已停止', 'ended':'已结束'}.get(status, '状态未知')
