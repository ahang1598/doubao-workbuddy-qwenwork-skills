"""Safe task dimensions and invocation-private command metadata."""
import json
import os
import stat

ENUMS = {
    'workflow_kind': ['live', 'video_single', 'video_batch', 'unknown'],
    'scenario_category': ['ecommerce', 'finance', 'automotive', 'other', 'unknown'],
    'delivery_mode': ['chat', 'local_dashboard', 'html_snapshot'],
    'asr_policy': ['remote_first', 'local_first', 'local_only'],
}
ERRORS = ['INVALID_INPUT', 'OPERATION_FAILED', 'ABORTED', 'RUNTIME_UNAVAILABLE',
    'LOCAL_VIDEO_PATH_REQUIRED', 'VIDEO_SOURCE_UNAVAILABLE', 'VIDEO_SOURCE_CHANGED', 'VIDEO_INVALID',
    'SEGMENT_SKIPPED', 'ASR_EVIDENCE_MISSING', 'VIDEO_RECAP_NOT_SUPPORTED', 'RECAP_EVIDENCE_CHANGED',
    'RECAP_ALREADY_SAVED', 'EVIDENCE_CHANGED', 'FRAMES_NOT_REVIEWED', 'RULES_INCOMPLETE',
    'ALREADY_REVIEWED', 'EVIDENCE_NOT_READY', 'SCENE_REQUIRED']
ERROR_DETAILS = ['ARGUMENT_PARSE_ERROR', 'STOP_USER_INSTRUCTION_REQUIRED',
    'STOP_TASK_NOT_FOUND', 'STOP_CONFIRM_DISCARD_REQUIRED',
    'STOP_ORDINARY_REQUIRES_DRAIN', 'STOP_LIVE_TASK_REQUIRED', 'STOP_STATE_PENDING']
_METADATA = {}


def safe_dimensions(value):
    return {key: value[key] for key, allowed in ENUMS.items() if value.get(key) in allowed}


def dimensions(task, *, batch=False):
    result = safe_dimensions(task)
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
    """Receives validated task state only; no stdout/stderr or stdin interception."""
    if os.environ.get('BYTEDLIVE_TELEMETRY_DISABLED', '').strip().lower() in ('1', 'true'):
        return
    try:
        target = os.environ.get('INSPECT_TELEMETRY_METADATA_FILE')
        if not target:
            return
        if value is not None:
            incoming = dimensions(value, batch=batch)
            if _METADATA.get('workflow_kind') == 'video_batch':
                incoming['workflow_kind'] = 'video_batch'
            _METADATA.update(incoming)
        if error_code is not None:
            _METADATA['error_code'] = error_code if error_code in ERRORS else 'OPERATION_FAILED'
        if error_detail in ERROR_DETAILS:
            _METADATA['error_detail'] = error_detail
        from runtime.platform_support import nofollow_open
        fd = nofollow_open(target, os.O_WRONLY | getattr(os, 'O_NONBLOCK', 0), 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                return
            stream.truncate(0)
            stream.write(json.dumps(_METADATA, separators=(',', ':')))
    except Exception:
        pass
