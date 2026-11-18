"""Evidence-bound remediation projection; never reclassifies compliance or calls a model."""
import hashlib
import json
from pathlib import Path
from runtime.report_data import public_text, _decisions, _result, _rules

VERSION = 'lite_remediation_v1'
URGENT = {
    'dangerous_instruction': {'DY_BASE_001_P0', 'DY_BASE_003_P0'},
    'driving_substitution': {'AUTO_LOCAL_001'},
    'illegal_transaction': {'DY_BASE_001_P0', 'DY_ECOM_001_P1', 'FIN_CORE_003'},
}
FIELDS = {'object', 'issue', 'condition', 'reason', 'action'}


def enabled(task):
    return task.get('kind', 'live') == 'live' and task.get('remediation_version') == VERSION


def contract():
    return {'version': VERSION,
            'rules_file': str(Path(__file__).resolve().parents[1] / 'references' / 'remediation.md'),
            'instruction': '首次遇到此版本先读取 rules_file。每个命中 events[] 或复盘一般 problems[] 填写 remediation；合规复盘用 compliance_rule_id 引用已有命中。判定问题时一并填写条件与改法，不另做一轮评级；等级由程序即时计算。不得填写等级，缺证据按规则说明待核实。',
            'template': dict.fromkeys(sorted(FIELDS), '')}


def normalize(value, *, source, rule_id=None):
    """A bad optional annotation must not discard a valid primary judgment."""
    if value is None:
        return None
    if not isinstance(value, dict) or set(value) != FIELDS or any(
            not isinstance(v, str) or not v.strip() or len(v) > 2000 for v in value.values()):
        return {'status': 'invalid'}
    result = {k: public_text(v.strip()) for k, v in value.items()}
    condition = result['condition']
    allowed = {'standard', 'urgency_unknown', *URGENT} if source == 'compliance' else {'decision_or_operation', 'expression', 'uncertain'}
    if condition not in allowed or (condition in URGENT and rule_id not in URGENT[condition]):
        return {'status': 'invalid'}
    return result


def _hash(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def _occurrences(segment, refs, event=None):
    items = {u['id']: {'id': f"{segment['id']}:asr:{u['id']}", 'kind': 'speech',
                       'start_ms': u.get('start_ms', segment['start_ms']),
                       'end_ms': u.get('end_ms', segment['end_ms']), 'text': public_text(u.get('text', ''))}
             for u in segment.get('subtitles', [])}
    viewed = (segment.get('review_result') or {}).get('images_viewed', [])
    for frame in segment.get('frames', []):
        if frame['id'] in viewed:
            items[frame['id']] = {'id': f"{segment['id']}:frame:{frame['id']}", 'kind': 'image',
                'start_ms': frame['time_ms'], 'end_ms': min(segment['end_ms'], frame['time_ms'] + 1000),
                'text': public_text((event or {}).get('text', ''))}
    if not refs or any(ref not in items for ref in refs):
        return []
    selected = [items[ref] for ref in dict.fromkeys(refs)]
    return [{'start_ms': min(e['start_ms'] for e in selected), 'end_ms': max(e['end_ms'] for e in selected),
             'evidence_ids': [e['id'] for e in selected], 'evidence': selected}]


def _item(source, source_id, title, reason, metadata, occurrences, *, rule_id=None, insufficient=False):
    meta = normalize(metadata, source=source, rule_id=rule_id)
    level = 'ungraded'
    if insufficient:
        level = 'pending'
    elif meta and meta.get('status') != 'invalid':
        condition = meta['condition']
        if not occurrences or condition in {'urgency_unknown', 'uncertain'}:
            level = 'pending'
        elif source == 'compliance':
            level = 'P0' if condition in URGENT else 'P1'
        else:
            level = 'P1' if condition == 'decision_or_operation' else 'P2'
    valid = meta and meta.get('status') != 'invalid'
    return {'source': source, 'source_ids': [source_id], 'rule_id': rule_id,
            'confirmed': source == 'compliance' and not insufficient,
            'title': meta['issue'] if valid else public_text(title), 'level': level,
            'object': meta['object'] if valid else '', 'issue': meta['issue'] if valid else '',
            'condition': meta['condition'] if valid else '',
            'reason': meta['reason'] if valid else public_text(reason),
            'action': meta['action'] if valid else ('补齐判断依据后复核' if insufficient else '分级资料未完成，请结合原始判断人工复核'),
            'occurrences': occurrences, 'grading_status': 'ready' if valid else 'invalid' if meta else 'missing'}


def build(task, segments, *, include_content=False, source=None):
    if not enabled(task):
        return {'status': 'ungraded', 'message': '未分级：此任务未启用整改分级', 'items': [], 'pending': []}
    base = {'version': VERSION, 'evidence_version': _hash([
        task.get('rules_snapshot', {}).get('version'),
        [{k: s.get(k) for k in ('id', 'evidence_revision', 'review_status', 'subtitles', 'frames', 'review_result')} for s in segments]])}
    if task.get('capture_status') not in {'ended', 'stopped', 'failed'} or task.get('worker_status') not in {'done', 'stopped', 'failed'}:
        return {**base, 'status': 'waiting', 'message': '检测结束后生成整改清单', 'items': [], 'pending': []}
    items = []
    rules = {r['id']: r for r in _rules(task)}
    for segment in segments:
        if segment.get('review_status') != 'done' and not segment.get('speech_reviewed'):
            continue
        for di, decision in enumerate(_decisions(segment)):
            rid = str(decision.get('rule_id'))
            if rid not in rules or _result(decision) not in {'hit', 'insufficient'}:
                continue
            status = _result(decision)
            for ei, event in enumerate(decision.get('events') or [{}]):
                occurrences = _occurrences(segment, event.get('evidence_ids', []), event)
                items.append(_item('compliance', f"{segment['id']}:{di}:{ei}", rules[rid]['name'],
                    decision.get('reason', ''), event.get('remediation'), occurrences,
                    rule_id=rid, insufficient=status == 'insufficient'))
    content_status = None
    if include_content:
        from runtime.recap import evidence_input, _same_evidence
        source = source or evidence_input(task, segments)
        saved = task.get('recap') or {}
        base['recap_evidence_version'] = source['evidence_version']
        content_status = saved.get('status', 'missing')
        if not _same_evidence(saved.get('evidence_version'), source):
            content_status = 'stale' if saved else 'missing'
        if content_status == 'ready':
            evidence = {e['id']: e for e in source['evidence']}
            for index, problem in enumerate((saved.get('document') or {}).get('problems', [])):
                refs = problem.get('evidence_ids', [])
                linked = problem.get('compliance_rule_id')
                # An explicit, evidence-checked link references the existing compliance item.
                if linked and refs and set(refs) <= {ref for item in items if item['rule_id'] == linked
                        for o in item['occurrences'] for ref in o['evidence_ids']}:
                    continue
                occurrences = []
                if refs and all(ref in evidence for ref in refs):
                    selected = [evidence[ref] for ref in refs]
                    occurrences = [{'start_ms': min(e['start_ms'] for e in selected),
                        'end_ms': max(e['end_ms'] for e in selected), 'evidence_ids': refs, 'evidence': selected}]
                items.append(_item('content', f'problem:{index}', problem.get('title', ''), problem.get('reason', ''),
                                   problem.get('remediation'), occurrences))
    groups = {}
    for index, item in enumerate(items):
        # Missing object/issue annotations cannot safely merge different events of one rule.
        key = (item['source'], item['rule_id'], item['object'], item['issue'], item['action'], item['level'], item['condition']) if item['object'] and item['issue'] else ('unmerged', index)
        if key not in groups:
            groups[key] = item
        else:
            groups[key]['source_ids'].extend(item['source_ids'])
            groups[key]['occurrences'].extend(item['occurrences'])
    for item in groups.values():
        occurrences = {}
        for occurrence in item['occurrences']:
            key = (occurrence['start_ms'], occurrence['end_ms'], tuple((e['kind'], e['text']) for e in occurrence['evidence']))
            if key in occurrences:
                occurrences[key]['evidence_ids'] = list(dict.fromkeys(occurrences[key]['evidence_ids'] + occurrence['evidence_ids']))
            else:
                occurrences[key] = dict(occurrence)
        item['occurrences'] = sorted(occurrences.values(), key=lambda o: o['start_ms'])
        item['count'] = len(item['occurrences'])
    order = {'P0': 0, 'P1': 1, 'P2': 2, 'ungraded': 3, 'pending': 4}
    ordered = sorted(groups.values(), key=lambda i: (order[i['level']], min([o['start_ms'] for o in i['occurrences']] or [float('inf')])))
    incomplete = (not segments or any(s.get('review_status') != 'done' for s in segments)
                  or any(i['level'] == 'ungraded' for i in ordered))
    return {**base, 'status': 'partial' if incomplete else 'ready', 'content_status': content_status,
            'message': '部分内容未完成判定或问题未分级，原始判断仍保留' if incomplete else '仅针对本次已检测内容；整改等级不等于违法等级',
            'items': [i for i in ordered if i['level'] != 'pending'], 'pending': [i for i in ordered if i['level'] == 'pending']}
