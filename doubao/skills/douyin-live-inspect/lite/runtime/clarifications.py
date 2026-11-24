"""Evidence-linked on-air corrections, independent of compliance verdicts."""
import copy
import hashlib
import json

REFERENCE = 'https://www.samr.gov.cn/zw/zfxxgk/fdzdgknr/fgs/art/2026/art_ce66ea61fcec4583b5dbd677f470088b.html'
RETENTION = '纠错记录应自直播结束之日起保存不少于三年；本报告仅保存已采集证据，运营者须另行确保长期归档、备份与可检索性，临时任务目录不构成三年留存保障。'
INSTRUCTION = (
    '同时检查口误、关键条件遗漏、表述不当及需要澄清的说法，填写 clarification_observations，无发现填空数组。'
    '这不是新增违规规则，不为凑数量列正常表达；仅 ASR 可疑或缺可靠依据时用 uncertain，不能认定主播说错。'
    '新项填写 kind(slip/incomplete/inappropriate/uncertain)、object(商品及套餐条件)、issue、quote、evidence_ids、action(现场需澄清的具体内容，不编造正确价格或权益)。'
    '后续纠正填写 clarification_id、status(partial/corrected/dismissed)、quote、evidence_ids、reason；ID 从 clarification_context 复制，同段新项 ID 为 segment_id:c数组序号(从1开始)。'
    '同批前段新项可按同一方式引用。必须是同一对象和条件、发生在原话之后的明确口播；泛泛道歉、改口但未补齐条件用 partial；明确纠正或补齐全部问题才用 corrected。'
    'dismissed 仅用于后续证据明确排除原疑点，不能用来掩盖已发生的问题；不因后续纠正自动撤销已有风险。'
    '无后续证据保留原状态；未采集到纠正不等于运营者没有纠错机制。仅检查本次提供的待澄清项，不反复带入已纠正项。'
)
CHECK_INSTRUCTION = (
    'clarification_observations 和 clarification_checks 必填；前者空数组明确表示本段无新增疑点或纠正。'
    '逐项核对本段 clarification_checklist，在 clarification_checks 写 {id,status,reason}，每项恰好一次。'
    'status 为 not_observed(本段未观察到纠正)、insufficient(证据不足)、partial、corrected 或 dismissed。'
    '后三者必须同时在 clarification_observations 提交该目标的对应原文证据；不能用空数组跳过历史清单。'
    'reason 说明具体已查范围和判断依据；无可用字幕时只能 insufficient。仅强制完成检查，不要求发现问题或纠正。'
)


def digest(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def issue_key(issue):
    return digest({k:issue[k] for k in ('id','kind','object','issue','quote','evidence')})


def speech_key(segment):
    return digest({'id':segment['id'],'subtitles':segment.get('subtitles',[])})


def check_coverage(checks, observations, required, segment):
    from runtime.review_errors import ReviewValidationError
    def invalid(message):
        return ReviewValidationError(message,segment['id'],field='clarification_checks')
    known = {q['id']:q for q in required}
    if not isinstance(checks,list) or len(checks)!=len(known):
        raise invalid('clarification checks must cover every frozen item: '+','.join(known))
    updates = {q['clarification_id']:q['status'] for q in observations if 'clarification_id' in q}
    seen, result = set(), []
    for row in checks:
        if (not isinstance(row,dict) or set(row)!={'id','status','reason'} or not isinstance(row['id'],str)
                or row['id'] not in known or row['id'] in seen or not isinstance(row['status'],str)
                or row['status'] not in {'not_observed','insufficient','partial','corrected','dismissed'}
                or not isinstance(row['reason'],str) or not row['reason'].strip() or len(row['reason'])>2000):
            raise invalid('invalid clarification check; IDs must match the frozen checklist exactly')
        if (row['status'] in {'partial','corrected','dismissed'} or row['id'] in updates) and updates.get(row['id'])!=row['status']:
            raise invalid('clarification check status requires matching correction evidence: '+row['id'])
        if not segment.get('subtitles') and row['status']!='insufficient':
            raise invalid('missing speech requires insufficient clarification check')
        seen.add(row['id'])
        result.append({**row,'issue_key':issue_key(known[row['id']]),'speech_key':speech_key(segment)})
    return result


def follows(item, original):
    if item['start_ms'] >= original['end_ms']:return True
    if item['evidence'] != original['evidence']:return False
    text = ''.join(''.join(e['text'].split()) for e in item['evidence'])
    before, after = ''.join(original['quote'].split()), ''.join(item['quote'].split())
    return text.find(after, text.find(before)+len(before)) >= 0


def summarize(segments):
    issues = {}
    for segment in sorted(segments, key=lambda s: (s['start_ms'], s['id'])):
        reviewed = segment.get('review_status') == 'done' or segment.get('speech_reviewed')
        speech = {e['id']:{k:e[k] for k in ('id','start_ms','end_ms','text')} | {'segment_id':segment['id']}
                  for e in segment.get('subtitles',[])}
        originals = (segment.get('review_result') or {}).get('clarification_observations', []) if reviewed else []
        for row in sorted(originals + segment.get('clarification_supplements', []), key=lambda row:(row['start_ms'],'clarification_id' in row)):
            if any(e != speech.get(e['id']) for e in row['evidence']):continue
            if 'clarification_id' not in row:
                issues[row['id']] = {**copy.deepcopy(row), 'status':'uncertain' if row['kind']=='uncertain' else 'pending', 'corrections':[]}
            elif row['clarification_id'] in issues:
                issue = issues[row['clarification_id']]
                # Evidence changes invalidate links rather than silently changing their meaning.
                if row.get('original_evidence') != issue['evidence'] or not follows(row,issue):
                    continue
                issue['corrections'].append(copy.deepcopy(row))
                issue['status'] = row['status']
    return list(issues.values())


def remaining(segments):
    """Uncovered issue/ASR ranges; live checks and final receipts share the same keys."""
    items = [q for q in summarize(segments) if q['status'] not in {'corrected','dismissed'}]
    if not items:return []
    keys = {q['id']:issue_key(q) for q in items}
    result = []
    for segment in sorted(segments,key=lambda s:(s['start_ms'],s['id'])):
        checks = (segment.get('review_result') or {}).get('clarification_checks',[]) + segment.get('clarification_rechecks',[])
        checked = {(c['id'],c.get('issue_key'),c.get('speech_key')) for c in checks}
        subtitles = segment.get('subtitles',[])
        full_key = speech_key(segment)
        for start in range(0,len(subtitles),64):
            source = {k:segment[k] for k in ('id','start_ms','end_ms')}
            source['subtitles'] = copy.deepcopy(subtitles[start:start+64])
            key = speech_key(source)
            end = max(u['end_ms'] for u in source['subtitles'])
            pending = [q for q in items if q['start_ms']<end
                       and (q['id'],keys[q['id']],key) not in checked
                       and (q['id'],keys[q['id']],full_key) not in checked]
            if pending:result.append((source,pending))
    return result


def pending_page(segments):
    ranges = remaining(segments)
    if not ranges:return None
    items = ranges[0][1][:8]
    ids = {q['id'] for q in items}
    sources, seen, count = [], set(), 0
    for source, pending in ranges:
        required = [q['id'] for q in pending if q['id'] in ids]
        size = len(source['subtitles'])
        if not required or source['id'] in seen:continue
        if sources and count+size>64:break
        sources.append({**source,'clarification_checklist':required})
        seen.add(source['id']);count+=size
        if len(sources)==4:break
    return {'items':items,'segments':sources}


def context(segments, before_ms):
    rows = [q for q in summarize(s for s in segments if s['end_ms'] <= before_ms)
            if q['status'] not in {'corrected','dismissed'}]
    # Keep the raw source internally; the model sees only compact issue descriptions.
    return {'items':rows[-8:], 'omitted_count':max(0,len(rows)-8)}


def model_context(source):
    return {'items':[{k:q[k] for k in ('id','kind','object','issue','start_ms','status','action')}
                     for q in source['items']], 'omitted_count':source['omitted_count']}


def normalize(value, segment, previous):
    if not isinstance(value, list) or len(value)>20:
        raise ValueError('invalid clarification observations')
    speech = {u['id']:u for u in segment.get('subtitles',[])}
    known = {q['id']:q for q in previous}
    result = []
    for index, row in enumerate(value,1):
        if not isinstance(row,dict):raise ValueError('invalid clarification item')
        update = 'clarification_id' in row
        fields = {'clarification_id','status','quote','evidence_ids','reason'} if update else {'kind','object','issue','quote','evidence_ids','action'}
        if set(row)!=fields or any(not isinstance(row[k],str) or not row[k].strip() or len(row[k])>2000 for k in fields-{'evidence_ids'}):
            raise ValueError('invalid clarification fields')
        refs = row['evidence_ids']
        if not isinstance(refs,list) or not refs or any(not isinstance(ref,str) or ref not in speech for ref in refs) or len(set(refs))!=len(refs):
            raise ValueError('clarification requires current speech evidence')
        selected = sorted((speech[ref] for ref in refs),key=lambda e:e['start_ms'])
        if ''.join(row['quote'].split()) not in ''.join(''.join(e['text'].split()) for e in selected):
            raise ValueError('clarification quote must match speech')
        evidence = [{k:e[k] for k in ('id','start_ms','end_ms','text')} | {'segment_id':segment['id']} for e in selected]
        item = {**row, 'id':f"{segment['id']}:c{index}", 'segment_id':segment['id'],
                'start_ms':min(e.get('context_start_ms',e['start_ms']) for e in selected),
                'end_ms':max(e['end_ms'] for e in selected), 'evidence':evidence}
        if update:
            original = known.get(row['clarification_id'])
            if original is None:raise ValueError('unknown clarification target')
            if row['status'] not in {'partial','corrected','dismissed'}:raise ValueError('invalid clarification status')
            if not follows(item,original):raise ValueError('clarification correction precedes original statement')
            item['original_evidence'] = copy.deepcopy(original['evidence'])
        else:
            if row['kind'] not in {'slip','incomplete','inappropriate','uncertain'}:raise ValueError('invalid clarification kind')
            known[item['id']] = item
        result.append(item)
    return result


def recap_followup(data):
    """Describe outstanding items in the checked speech, separately from violations."""
    counts = data.get('counts', {})
    parts = []
    if counts.get('pending'):
        parts.append(f"{counts['pending']} 项仍待澄清")
    if counts.get('partial'):
        parts.append(f"{counts['partial']} 项已作部分说明，仍需补充")
    if counts.get('uncertain'):
        parts.append(f"{counts['uncertain']} 条表述待核实")
    if not parts:
        return ''
    text = '现场跟进：' + '，'.join(parts)
    if not data.get('recheck_complete'):
        return text + '，后续口播尚未核对完。'
    if not counts.get('partial'):
        return text + '，在已检查的口播中未看到针对这些事项的后续说明。'
    return text + '。'


def report(segments):
    rows = summarize(segments)
    gaps = remaining(segments)
    checked = sum(bool(s.get('subtitles')) and (s.get('review_status')=='done' or s.get('speech_reviewed',False))
                  and 'clarification_observations' in (s.get('review_result') or {}) for s in segments)
    return {'items':rows, 'counts':{status:sum(q['status']==status for q in rows)
                                  for status in ('pending','uncertain','partial','corrected','dismissed')},
            'checked_segments':checked, 'total_segments':len(segments),
            'recheck_complete':not gaps, 'unreviewed_pairs':sum(len(items) for _,items in gaps),
            'unreviewed_items':len({q['id'] for _,items in gaps for q in items}),
            'unavailable_segments':sum(not s.get('subtitles') for s in segments), 'retention_notice':RETENTION,
            'reference':REFERENCE, 'scope':'仅反映已采集并完成检查的口播；未观察到纠正不证明没有纠错机制，已纠正也不自动撤销原风险。'}
