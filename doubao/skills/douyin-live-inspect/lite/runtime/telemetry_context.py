"""Safe task dimensions and invocation-private command metadata."""
import json
import os
import stat
import sys
import sqlite3
import subprocess
from runtime.task_context import ID

ENUMS = {
    'live_source_status': ['live', 'not_live', 'unknown'],
    'capture_status': ['pending', 'running', 'ended', 'stopped', 'failed'],
    'source_end_reason': ['offline', 'stream_retry_exhausted', 'source_resolution_failed', 'capture_failed', 'user_stop', 'duration_limit', 'unknown'],
    'source_error_code': ['none', 'STREAM_RETRY_EXHAUSTED', 'DOUYIN_FETCH_FAILED', 'DOUYIN_PAGE_UNAVAILABLE', 'DOUYIN_FLV_UNAVAILABLE', 'DOUYIN_RESOLVER_UNAVAILABLE', 'INVALID_INPUT'],
    'workflow_kind': ['live', 'video_single', 'video_batch', 'unknown'],
    'scenario_category': ['ecommerce', 'finance', 'automotive', 'other', 'unknown'],
    'delivery_mode': ['chat', 'local_dashboard', 'html_snapshot'],
    'asr_policy': ['remote_first', 'local_first', 'local_only'],
}
ERRORS = ['INVALID_INPUT', 'OUT_OF_MEMORY', 'OPERATION_FAILED', 'ABORTED', 'RUNTIME_UNAVAILABLE',
    'LOCAL_VIDEO_PATH_REQUIRED', 'VIDEO_SOURCE_UNAVAILABLE', 'VIDEO_SOURCE_CHANGED', 'VIDEO_INVALID',
    'SEGMENT_SKIPPED', 'ASR_EVIDENCE_MISSING', 'VIDEO_RECAP_NOT_SUPPORTED', 'RECAP_EVIDENCE_CHANGED',
    'RECAP_ALREADY_SAVED', 'EVIDENCE_CHANGED', 'FRAMES_NOT_REVIEWED', 'RULES_INCOMPLETE',
    'ALREADY_REVIEWED', 'EVIDENCE_NOT_READY', 'SCENE_REQUIRED']
ERROR_DETAILS = ['ARGUMENT_PARSE_ERROR', 'STOP_USER_INSTRUCTION_REQUIRED',
    'STOP_TASK_NOT_FOUND', 'STOP_CONFIRM_DISCARD_REQUIRED',
    'STOP_ORDINARY_REQUIRES_DRAIN', 'STOP_LIVE_TASK_REQUIRED', 'STOP_STATE_PENDING']
DIAGNOSTIC_ENUMS = {
    'startup_stage': ['input_validation', 'dependency_prepare', 'task_create', 'credential_prepare',
                      'dashboard_prepare', 'worker_launch', 'watcher_launch', 'completed', 'unknown'],
    'startup_outcome': ['setup_pending', 'started', 'failed', 'unknown'],
    'error_origin': ['business', 'process_launch', 'signal', 'wrapper_fallback'],
    'error_category': ['invalid_input', 'permission', 'not_found', 'file_conflict', 'io',
                       'sqlite', 'timeout', 'import', 'runtime', 'other'],
    'metadata_transport': ['pipe'],
    'metadata_init_status': ['ready', 'timeout', 'helper_failed', 'io_error'],
    'metadata_read_status': ['valid', 'empty', 'unavailable', 'invalid', 'io_error'],
    'child_signal': ['SIGINT', 'SIGTERM', 'SIGHUP', 'SIGBREAK', 'SIGKILL', 'SIGABRT', 'SIGSEGV'],
    'process_error_code': ['ENOENT', 'EACCES', 'EPERM', 'ENOEXEC', 'EINVAL', 'ENOMEM', 'EAGAIN', 'UNKNOWN'],
}

_METADATA = {}
_CHANNEL_FD = None


def open_channel():
    """Claim only the bridge-owned pipe; never open a path or standard stream."""
    global _CHANNEL_FD
    marker = os.environ.pop('INSPECT_TELEMETRY_FD', None)
    if marker != '3' or os.environ.get('BYTEDLIVE_LITE_TELEMETRY_CHILD') != '1':
        return
    fd = 3
    try:
        # Close inheritance before any business code can launch worker/watcher processes.
        os.set_inheritable(fd, False)
        if os.environ.get('BYTEDLIVE_TELEMETRY_DISABLED', '').strip().lower() in ('1', 'true'):
            os.close(fd)
            return
        if os.name == 'nt':
            import ctypes
            from ctypes import wintypes
            import msvcrt
            kernel = ctypes.WinDLL('kernel32', use_last_error=True)
            kernel.GetFileType.argtypes = [wintypes.HANDLE]
            kernel.GetFileType.restype = wintypes.DWORD
            kernel.SetNamedPipeHandleState.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p, ctypes.c_void_p]
            kernel.SetNamedPipeHandleState.restype = wintypes.BOOL
            handle = msvcrt.get_osfhandle(fd)
            mode = wintypes.DWORD(1)  # PIPE_NOWAIT also supports Python 3.10/3.11.
            if kernel.GetFileType(handle) != 3 or not kernel.SetNamedPipeHandleState(handle, ctypes.byref(mode), None, None):
                raise OSError('diagnostic pipe unavailable')
            msvcrt.setmode(fd, os.O_BINARY)
        else:
            mode = os.fstat(fd).st_mode
            if not (stat.S_ISFIFO(mode) or stat.S_ISSOCK(mode)):
                raise OSError('diagnostic pipe required')
            os.set_blocking(fd, False)
        _CHANNEL_FD = fd
    except Exception:
        try:
            os.close(fd)
        except OSError:
            pass


def close_channel():
    """One bounded nonblocking snapshot; a full/broken pipe never delays business."""
    global _CHANNEL_FD
    fd, _CHANNEL_FD = _CHANNEL_FD, None
    if fd is None:
        return
    try:
        payload = json.dumps(_METADATA, separators=(',', ':'), ensure_ascii=True).encode('ascii')
        if len(payload) <= 4096:
            os.write(fd, payload)
    except Exception:
        pass
    finally:
        try:
            os.close(fd)
        except OSError:
            pass



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


def safe_dimensions(value):
    result = {key: value[key] for key, allowed in ENUMS.items() if value.get(key) in allowed}
    for key in ('task_id','child_task_id'):
        if isinstance(value.get(key),str) and ID.fullmatch(value[key]): result[key]=value[key]
    return result


def dimensions(task, *, batch=False):
    result = safe_dimensions(task)
    local_id=task.get('task_id') or task.get('id')
    if isinstance(local_id,str) and ID.fullmatch(local_id): result['task_id']=local_id
    record=task.get('_telemetry') or {}
    batch_id=(task.get('notice_batch') or {}).get('id')
    if not batch_id and record.get('batch_directory'): batch_id=record.get('task_id')
    if isinstance(batch_id,str) and ID.fullmatch(batch_id):
        result.update(task_id=batch_id,child_task_id=local_id)
    if task.get("kind", "live") != "live" or "live_source_status" not in task:
        for key in ("live_source_status", "capture_status", "source_end_reason", "source_error_code"):
            result.pop(key, None)
    scenario = task.get('scenario')
    if task.get('scenario_selection') == 'pending' or not scenario:
        category = 'unknown'
    else:
        category = {'电商': 'ecommerce', '金融': 'finance', '汽车': 'automotive',
                    'ecommerce': 'ecommerce', 'finance': 'finance', 'automotive': 'automotive'}.get(scenario, 'other')
    result['scenario_category'] = category
    result['workflow_kind'] = ('video_batch' if batch or task.get('notice_batch') else
                               'video_single' if task.get('kind') == 'video' else
                               'live' if task.get('kind') == 'live' else result.get('workflow_kind', 'unknown'))
    return result


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
