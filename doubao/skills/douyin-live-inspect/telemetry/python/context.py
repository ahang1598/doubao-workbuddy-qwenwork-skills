"""读取两端共享的字段合同和补报策略，从任务中提取安全维度、归属关联及场景分类。
仅提供本地配置与事实处理，不启动子进程或执行网络发送。
"""
import json
from pathlib import Path
from runtime.task_context import ID

_CONTRACTS = json.loads((Path(__file__).resolve().parents[1] / 'config/contracts.json').read_text(encoding='utf-8'))
ENUMS = _CONTRACTS['ENUMS']
DIAGNOSTIC_ENUMS = _CONTRACTS['DIAGNOSTIC_ENUMS']
ERRORS = _CONTRACTS['ERRORS']
ERROR_DETAILS = _CONTRACTS['ERROR_DETAILS']
STOP_ENUMS = _CONTRACTS['STOP_ENUMS']
STOP_OPTIONAL_ENUMS = _CONTRACTS['STOP_OPTIONAL_ENUMS']

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

_DELIVERY = json.loads((Path(__file__).resolve().parents[1] / 'config/delivery.json').read_text(encoding='utf-8'))

def persistent(event, explicit=False):
    rule = _DELIVERY['explicit' if explicit else 'automatic'].get(event.get('command'))
    field = 'phase' if event.get('command') == 'asr.diagnostic' else 'failure_component'
    return rule is True or isinstance(rule, list) and event.get('extra', {}).get(field) in rule
