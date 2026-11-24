"""Evidence-bound scoring; numeric policy is shared with the Node runtime."""
import json
import math
from pathlib import Path

RULES = json.loads((Path(__file__).resolve().parents[2] / 'references/review-scoring.json').read_text())


# Fixed diagnostics only: never return submitted values or raw exception text.
ERROR_HINTS = {
    'version': 'document.scoring.version 必须原样使用模板版本。',
    'evidence_version': 'document.scoring.evidence_version 必须原样使用本次模板的 evidence_version。',
    'dimensions': 'document.scoring.dimensions 必须保留模板的全部九个维度。',
    'risks': 'document.scoring.risks 必须逐项对应 scoring_context.issues。',
    'risk': 'scoring.risks 每项须为包含 issue_id、level、reason 的对象。',
    'issue_id': 'scoring.risks[].issue_id 须来自本次 issues，且不得重复。',
    'risk level/reason': 'scoring.risks[].level 仅允许 high/medium/low/unknown（不是 P0/P1/P2）；reason 必须非空且不超过 2000 字。',
    'risk evidence incomplete': '问题缺少逐条原话，level 须为 unknown，并说明缺少的证据。',
    'inconsistent repeated risk': '同一规则、同一原话的重复风险须使用一致 level。',
    'dimension': 'scoring.dimensions 每项须为模板中的维度对象。',
    'dimension id': 'scoring.dimensions[].id 须来自模板且不重复。',
    'status/reason': '维度 status 仅允许 scored/not_applicable/insufficient；reason 非空且不超过 2000 字。',
    'evidence_ids': '评分 evidence_ids 必须来自 scoring_context.evidence 且不重复。',
    'score': 'scored 须有 0–10 整数 score 和非空证据；其他状态 score 须为 null。',
    'evidence kind': '合规分引用 quality 证据，其他分项引用内容证据。',
    'compliance applicable': '合规分不能为 not_applicable。',
    'compliance incomplete': '质检未完成或有 unknown 风险时，合规分须为 insufficient，score 为 null。',
    'compliance score required': '质检完整且风险已明确分级时须填写合规分。',
    'compliance band': '合规分超出 scoring_rules 对应风险档位范围，请按该范围修正。',
    'content evidence unchecked': '本次评分有语音或画面证据，不能把摘要省略当作证据缺失。请核对 scoring_context 或 evidence_file 中的内容；可观察维度正常评分。若全部内容维度仍不可评，在相应 insufficient 项引用已核对的内容证据并说明具体缺口，不强行打分。',
}


def calculate(value, context):
    def require(ok, field):
        if not ok:
            raise ValueError('invalid scoring: ' + field)
    def text(v):
        return isinstance(v, str) and bool(v.strip()) and len(v) <= 2000
    require(isinstance(value, dict) and value.get('version') == RULES['version'], 'version')
    if context.get('evidence_version'):
        require(value.get('evidence_version') == context['evidence_version'], 'evidence_version')
    dimensions = value.get('dimensions')
    require(isinstance(dimensions, list) and len(dimensions) == 9, 'dimensions')
    evidence = {e['id']: e for e in context['evidence']}
    issues = {i['id']: i for i in context['issues']}
    grades = value.get('risks')
    require(isinstance(grades, list) and len(grades) == len(issues), 'risks')
    grouped, seen = {}, set()
    for row in grades:
        require(isinstance(row, dict), 'risk')
        rid = row.get('issue_id')
        require(isinstance(rid, str) and rid in issues and rid not in seen, 'issue_id')
        seen.add(rid)
        require(row.get('level') in ('high', 'medium', 'low', 'unknown') and text(row.get('reason')), 'risk level/reason')
        issue = issues[rid]
        require(bool(issue.get('quote')) or row['level'] == 'unknown', 'risk evidence incomplete')
        key = (str(issue['rule_id']), ''.join(issue.get('quote', '').split()) or rid)
        group = grouped.setdefault(key, {'level': row['level'], 'reason': row['reason'], 'rule_id': issue['rule_id'], 'occurrences': []})
        require(group['level'] == row['level'], 'inconsistent repeated risk')
        group['occurrences'].append(issue)
    risks = list(grouped.values())
    high = sum(r['level'] == 'high' for r in risks)
    provisional = not context['compliance_complete'] or any(r['level'] == 'unknown' for r in risks)
    result, seen = [], set()
    for row in dimensions:
        require(isinstance(row, dict), 'dimension')
        spec = next((d for d in RULES['dimensions'] if d['id'] == row.get('id')), None)
        require(spec is not None and spec['id'] not in seen, 'dimension id')
        seen.add(spec['id'])
        status, score, refs = row.get('status'), row.get('score'), row.get('evidence_ids')
        require(status in ('scored', 'not_applicable', 'insufficient') and text(row.get('reason')), 'status/reason')
        require(isinstance(refs, list) and all(isinstance(i, str) and i in evidence for i in refs) and len(set(refs)) == len(refs), 'evidence_ids')
        require((type(score) is int and 0 <= score <= 10 and bool(refs)) if status == 'scored' else score is None, 'score')
        if status == 'scored':
            require(any((evidence[i].get('kind') == 'quality') == (spec['id'] == 'compliance') for i in refs), 'evidence kind')
        if spec['id'] == 'compliance':
            require(status != 'not_applicable', 'compliance applicable')
            if provisional:
                require(status == 'insufficient', 'compliance incomplete')
            else:
                require(status == 'scored', 'compliance score required')
                lo, hi = (0, 2) if high >= 3 else (3, 4) if high else (5, 6) if any(r['level'] == 'medium' for r in risks) else (7, 8) if risks else (9, 10)
                require(lo <= score <= hi, 'compliance band')
        result.append({k: spec[k] for k in ('id', 'name', 'weight')} | {'status': status, 'score': score, 'reason': row['reason'].strip(), 'evidence_ids': refs,
            'evidence': [evidence[i] for i in refs]})
    result.sort(key=lambda r: next(i for i, d in enumerate(RULES['dimensions']) if d['id'] == r['id']))
    scored = [d for d in result if d['status'] == 'scored']
    if (not any(d['id'] != 'compliance' for d in scored)
            and any(d['id'] != 'compliance' and d['status'] == 'insufficient' for d in result)
            and any(e.get('kind') in ('speech', 'image') for e in evidence.values())):
        require(any(d['id'] != 'compliance' and d['status'] == 'insufficient'
                    and any(e.get('kind') in ('speech', 'image') for e in d['evidence'])
                    for d in result), 'content evidence unchecked')
    cap = next((limit for count, limit in RULES['caps'] if high >= count), None)
    total = None
    if any(d['id'] != 'compliance' for d in scored):
        total = sum(d['score'] * d['weight'] for d in scored) / sum(d['weight'] for d in scored)
        total = math.floor(min(total, cap if cap is not None else 10) * 10 + 0.5) / 10
    return {'version': RULES['version'], **({'evidence_version': context['evidence_version']} if context.get('evidence_version') else {}), 'dimensions': result, 'risks': risks, 'high_risk_count': high,
        'total': total, 'level': next((name for minimum, name in RULES['levels'] if total is not None and total >= minimum), ''),
        'status': 'unavailable' if total is None else 'provisional' if provisional else 'ready',
        'cap': cap, 'scope': '已检测内容评分',
        'message': '没有可评分的内容维度，无法评分' if total is None else '合规或风险分级不完整，暂定分；封顶尚不能完整判定' if provisional else '仅评价本次已检测内容，不代表全场或转化效果'}


def template(context):
    return {'version': RULES['version'], **({'evidence_version': context['evidence_version']} if context.get('evidence_version') else {}), 'dimensions': [
        {'id': d['id'], 'status': 'insufficient', 'score': None, 'reason': '', 'evidence_ids': []}
        for d in RULES['dimensions']], 'risks': [{'issue_id': i['id'], 'level': 'unknown', 'reason': ''} for i in context['issues']]}


def context_for(task, segments, evidence):
    from runtime.report_data import _decisions, _result, public_text
    items = list(evidence)
    issues = []
    complete = bool(segments and evidence)
    for s in segments:
        decisions = _decisions(s,task.get('review_dispositions'))
        complete = complete and s.get('review_status') == 'done' and bool(decisions)
        for di, d in enumerate(decisions):
            status = _result(d)
            complete = complete and status in ('hit', 'no_hit', 'not_applicable')
            rid = str(d.get('rule_id'))
            eid = f"quality:{s['id']}:{di}"
            items.append({'id': eid, 'segment_id': s['id'], 'kind': 'quality', 'start_ms': s['start_ms'], 'end_ms': s['end_ms'],
                          'text': public_text((d.get('review_disposition') or {}).get('reason') or d.get('reason', '')), 'rule_id': rid, 'result': status})
            if status != 'hit':
                continue
            events = d.get('events') or [{}]
            for ei, event in enumerate(events):
                refs = event.get('evidence_ids', [])
                quote = event.get('text') or event.get('description') or ' '.join(
                    u.get('text', '') for u in s.get('subtitles', []) if u['id'] in refs)
                if not quote:
                    complete = False
                issues.append({'id': f'{eid}:{ei}', 'segment_id': s['id'], 'rule_id': rid, 'quote': public_text(quote),
                    'evidence_ids': [eid], 'start_ms': event.get('start_ms', s['start_ms']),
                    'end_ms': event.get('end_ms', s['end_ms'])})
    return {'evidence': items, 'issues': issues, 'compliance_complete': bool(complete)}
