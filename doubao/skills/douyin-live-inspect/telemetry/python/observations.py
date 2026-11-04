"""根据直播任务事实生成停止来源、阻塞恢复观察，维护对应观察标记。
观察与任务结果分别判断，不把停止请求或环境观察直接计为任务完成。
"""
import uuid
import re
from datetime import datetime, timezone
from runtime.context import DIAGNOSTIC_ENUMS, ENUMS, STOP_ENUMS, STOP_OPTIONAL_ENUMS
from runtime.bridge import STOP

COMMAND = STOP.OBSERVED

def safe(value):
    if not isinstance(value, dict):return None
    if not isinstance(value.get('task_id'), str) or not re.fullmatch('[0-9a-f]{32}', value['task_id'], re.I):return None
    if type(value.get('run_index')) is not int or not 1 <= value['run_index'] <= 2**53-1:return None
    if type(value.get('stop_revision')) is not int or not 1 <= value['stop_revision'] <= 2**53-1:return None
    if any(value.get(k) not in allowed for k, allowed in STOP_ENUMS.items()):return None
    try:
        event_id=uuid.UUID(value['diagnostic_event_id'])
        if event_id.version not in range(1,6) or str(event_id)!=value['diagnostic_event_id'].lower():return None
        if not isinstance(value['observed_at'], str) or len(value['observed_at']) > 64:return None
        if not re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?(?:Z|[+-]\d\d:\d\d)', value['observed_at']):return None
        at = datetime.fromisoformat(value['observed_at'].replace('Z', '+00:00'))
        if at.tzinfo is None:return None
    except (KeyError, ValueError, TypeError, AttributeError):return None
    extra = {k:value[k] for k in (*STOP_ENUMS, 'task_id', 'run_index', 'stop_revision', 'diagnostic_event_id', 'observed_at')}
    for k, allowed in STOP_OPTIONAL_ENUMS.items():
        if value.get(k) in allowed:extra[k] = value[k]
    for k in ('blocking_reason', 'failure_component', 'failure_reason'):
        if value.get(k) in DIAGNOSTIC_ENUMS[k]:extra[k] = value[k]
    for k in ('capture_status', 'source_end_reason', 'source_error_code'):
        if value.get(k) in ENUMS[k]:extra[k] = value[k]
    return {'command':COMMAND, 'extra':extra}

def observations(task, signal=None):
    """An Agent's nonempty instruction is a claim, never authenticated user intent."""
    result = {}
    audit = task.get('stop_audit') or {}
    base = {k:task[k] for k in ('capture_status', 'source_end_reason', 'source_error_code') if k in task}
    immediate = audit.get('mode') == 'immediate'
    # freeze_on_end may write a cleanup signal after an initial immediate stop.
    # That later runtime signal is not an earlier ordinary stop request.
    if immediate and signal and signal.get('origin') == 'runtime' and signal.get('reason') == 'source_ended':
        try:
            at = datetime.fromisoformat(audit['at'].replace('Z', '+00:00'))
            if at.tzinfo is not None and at.timestamp() <= signal['requested_at']:signal = None
        except (KeyError, ValueError, TypeError):pass
    if task.get('stop_requested') or signal or task.get('capture_status') == 'stopped':
        # The durable signal owns the first request; a later immediate audit is
        # a separate operation and must never rewrite that request's provenance.
        intent = signal or audit
        reason = task.get('stop_reason') or intent.get('reason', 'unknown')
        first_audit = {} if signal and immediate else audit
        result['stop'] = request_observation(task, intent, first_audit, reason, base)
        result['stop']['stop_mode'] = 'drain' if signal else audit.get('mode', 'unknown')
        if signal and immediate:
            result['immediate'] = request_observation(task, audit, audit, audit.get('reason'), base)
            result['immediate']['stop_mode'] = 'immediate'
    # Keep blockers in a separate observation: a user stop and an error can coexist.
    for key, detail in [('progress', task.get('_progress_diagnostic')), ('report', task.get('_report_diagnostic')),
                        ('drain', (task.get('finishing') or {}).get('diagnostic'))]:
        if not isinstance(detail, dict) or detail.get('recovery_outcome') == 'success':continue
        why = detail.get('blocking_reason')
        if why not in DIAGNOSTIC_ENUMS['blocking_reason'] or why in {'none','user_discard'}:continue
        result[key] = {**base, 'stop_source':'error_blocked', 'stop_origin':'runtime', 'stop_reason':'unknown',
            'stop_evidence':'runtime_state', 'stop_state':'blocked',
            **{k:detail[k] for k in ('blocking_reason','failure_component','failure_reason') if k in detail}}
    if task.get('capture_status') == 'failed' or task.get('worker_status') == 'failed':
        result['failure'] = {**base, 'stop_source':'error_blocked', 'stop_origin':'runtime',
            'stop_reason':'unknown', 'stop_evidence':'runtime_state', 'stop_state':'blocked'}
    return result

def request_observation(task, intent, audit, reason, base):
    if reason not in STOP_ENUMS['stop_reason']:reason = 'unknown'
    origin = intent.get('origin', 'unknown')
    if origin not in STOP_ENUMS['stop_origin']:origin = 'unknown'
    source, evidence = 'unknown', 'unknown'
    limit = {}
    if reason == 'execution_limit':
        from runtime.realtime_policy import cloud_limited, CLOUD_COMMAND_LIMIT
        count = task.get('cloud_live_command_count')
        confirmed = cloud_limited(task) and type(count) is int and count >= CLOUD_COMMAND_LIMIT
        source = 'execution_limit'
        evidence = 'runtime_state' if confirmed else 'agent_claim' if origin == 'agent' else 'unknown'
        limit['limit_source'] = 'skill_command_budget' if confirmed else 'agent_reported' if origin == 'agent' else 'unknown'
    elif reason in {'duration_limit', 'source_ended'}:source, evidence = 'system', 'runtime_state'
    elif origin == 'dashboard' and reason == 'user_request':source, evidence = 'user', 'dashboard_request'
    elif origin == 'agent':
        source = 'agent'
        evidence = 'agent_claim' if audit.get('user_instruction') and audit.get('reason') == 'user_request' else 'agent_action'
    if not audit and reason == 'user_request':evidence = 'signal_only'
    return {**base, **limit, 'stop_source':source, 'stop_origin':origin, 'stop_reason':reason,
        'stop_evidence':evidence, 'stop_state':'stopped' if task.get('capture_status') in {'stopped','ended','failed'} else 'requested'}

def observe(task, signal):
    from runtime.transaction import now
    record = task.get('_telemetry')
    if not record or task.get('kind') != 'live':return
    current = observations(task, signal)
    run = record['run_index']
    previous = record.get('stop_observation', {})
    old = previous.get('states', {}) if previous.get('run') == run else {}
    if 'immediate' in current and 'stop' in old:
        for key in ('stop_source', 'stop_origin', 'stop_reason', 'stop_evidence', 'limit_source'):
            if key in old['stop']:current['stop'][key] = old['stop'][key]
    # Missing diagnostics are not proof of recovery. Preserve the last known
    # blocker until an explicit success or a running process state supersedes it.
    details = {'progress':task.get('_progress_diagnostic'), 'report':task.get('_report_diagnostic'),
               'drain':(task.get('finishing') or {}).get('diagnostic')}
    for key in old.keys() - current.keys():
        if key in {'stop', 'immediate'}:continue
        recovered = ((details.get(key) or {}).get('recovery_outcome') == 'success' if key != 'failure' else
                     'running' in (task.get('capture_status'), task.get('worker_status')) and
                     'failed' not in (task.get('capture_status'), task.get('worker_status')))
        if not recovered:current[key] = old[key]
    revision = previous.get('revision', 0)
    emitted = []
    for key in sorted(current.keys() | old.keys()):
        state = current.get(key)
        if state == old.get(key):continue
        if state is None:
            if key in {'stop', 'immediate'}:continue
            state = {**old[key], 'stop_state':'recovered'}
        revision += 1
        event = safe({**state, 'stop_scope':'request' if key == 'stop' else key,
            'task_id':task['task_id'], 'run_index':run, 'stop_revision':revision,
            'diagnostic_event_id':str(uuid.uuid5(uuid.UUID(record['telemetry_task_id']), f'stop:{run}:{revision}')),
            'observed_at':now()})
        if event:emitted.append(event)
    if current == old:return
    record['stop_observation'] = {'run':run, 'revision':revision, 'states':current}
    return emitted
