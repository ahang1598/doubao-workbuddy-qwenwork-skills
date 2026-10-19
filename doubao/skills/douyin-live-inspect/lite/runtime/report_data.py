"""Shared read-only report aggregation and safe prose for quality and recap."""
import re

def public_text(value):
    """Report prose is text, never raw transport diagnostics or source addresses."""
    # Do not truncate saved judgment reasons; redact URLs/credential assignments only.
    text = re.sub(r'https?://\S+', '[来源地址]', str(value))
    text = re.sub(r'(?i)(bearer\s+)[\w.\-]+', r'\1[凭据]', text)
    # Quoted JSON/header values must be removed as a whole, including spaces.
    text = re.sub(
        r"(?i)((?:[\"']?)(?:[\w-]*token|secret|authorization|cookie|api[_-]?key)[\"']?\s*[:=]\s*)"
        r"(?:\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'|[^\s,;}]+)",
        r'\1[凭据]', text)
    import os
    for key in ('DOUBAO_OFFICE_USER_ACCESS_TOKEN', 'DOUBAO_OFFICE_CLI_TOKEN'):
        if os.environ.get(key): text = text.replace(os.environ[key], '[凭据]')
    return text


DECISION_RESULTS = ('hit', 'no_hit', 'not_applicable', 'insufficient', 'pending', 'skipped')
ASR_SUCCESS = {'done', 'ready', 'completed', 'success'}


def _decisions(segment):
    review = segment.get('review_result') or {}
    return review.get('decisions', review.get('rules', [])) or []


def _result(decision):
    return decision.get('result', decision.get('status'))


def _rule_summary(rule, segments):
    counts = dict.fromkeys(DECISION_RESULTS, 0)
    groups = {}
    for segment in segments:
        decisions = [d for d in _decisions(segment) if str(d.get('rule_id')) == rule['id']]
        retained_hit=segment.get('full_live') and any(_result(d)=='hit' for d in decisions)
        if retained_hit:
            decisions=[d for d in decisions if _result(d)=='hit']
        elif segment.get('review_status') == 'skipped':
            decisions = [{'result': 'skipped' if segment.get('skip_code')=='ASR_RETRY_EXHAUSTED' else 'insufficient',
                          'reason': skip_reason(segment)}]
        elif segment.get('review_status') != 'done':
            decisions = [{'result': 'pending', 'reason': '该片段尚未完成判定'}]
        elif not decisions:
            decisions = [{'result': 'insufficient', 'reason': '该片段缺少规则判断结果'}]
        results = [_result(d) for d in decisions]
        # Duplicate/unknown historical decisions cannot silently clear a segment.
        result = ('hit' if 'hit' in results else
                  results[0] if len(decisions) == 1 and results[0] in DECISION_RESULTS else 'insufficient')
        counts[result] += 1
        for decision in decisions:
            status = _result(decision)
            status = status if status in DECISION_RESULTS else 'insufficient'
            reason = public_text(decision.get('reason') or '').strip() or '未保存判断依据，无法展示具体原因'
            key = (status, reason)
            groups.setdefault(key, {'result': status, 'reason': reason, 'segments': []})
            span = {'segment_id': segment['id'], 'start': segment.get('start_ms', 0) / 1000,
                    'end': segment.get('end_ms', 0) / 1000}
            if span not in groups[key]['segments']:
                groups[key]['segments'].append(span)
    result = ('hit' if counts['hit'] else 'pending' if counts['pending'] else
              'insufficient' if counts['insufficient'] or counts['skipped'] or not segments else
              'not_applicable' if counts['not_applicable'] == len(segments) else 'clear')
    return {'result': result, 'counts': counts, 'judgments': list(groups.values()),
            'assessment': assessment(counts), 'coverage_summary': rule_coverage(rule, segments)}


def assessment(counts):
    """A scoped conclusion never claims that unchecked content is clear."""
    return ('hit' if counts.get('hit') else 'no_hit_in_checked_scope' if counts.get('no_hit') else
            'not_applicable' if counts.get('not_applicable') else 'undetermined')


def span_ms(rows):
    spans = []
    for row in sorted(rows, key=lambda r: r['start']):
        start, end = row['start'], row['end']
        if end <= start:
            continue
        if spans and start <= spans[-1][1]:
            spans[-1][1] = max(end, spans[-1][1])
        else:
            spans.append([start, end])
    return round(sum(end - start for start, end in spans) * 1000)


def summarize_coverage(rows, issues):
    categories = ('checked', 'evidence_insufficient', 'pending', 'unchecked')
    counts = {key: sum(row['category'] == key for row in rows) for key in categories}
    durations = {key: span_ms([r for r in rows if r['category'] == key]) for key in categories}
    # Recorded time without a segment still belongs to the inspection scope.
    total_ms = span_ms(rows + [i for i in issues if i['kind'] == 'judgment'])
    # A confirmed event is useful, but does not certify a source gap as reviewed time.
    checked = [r for r in rows if r['category'] == 'checked']
    # Deduplicate issues shared by several rules; reasons stay available per rule.
    unique = {}
    for issue in issues:
        key = (issue.get('segment_id'), issue['kind'], issue['start'], issue['end'], issue['reason'])
        unique[key] = issue
    issues = list(unique.values())
    blocking = [i for i in issues if i['kind'] != 'pending']
    # |checked minus blocking| = |checked union blocking| - |blocking|.
    # Interval unions avoid a checked-segment × issue cross product.
    durations['checked'] = span_ms(checked + blocking) - span_ms(blocking)
    issue_counts = {kind:len({i['segment_id'] for i in issues
                             if i['kind'] == kind and i.get('segment_id') is not None})
                    for kind in ('speech','image','judgment_missing','judgment_insufficient','unchecked','pending')}
    insufficient_ids = {r['segment_id'] for r in rows if r['category'] == 'evidence_insufficient'}
    speech_insufficient = len({i['segment_id'] for i in issues if i['kind'] == 'speech'
                               and i.get('segment_id') in insufficient_ids})
    return {'segment_count': len(rows), 'counts': counts, 'duration_ms': durations,
            'total_ms': total_ms, 'checked_segment_ratio': counts['checked'] / len(rows) if rows else None,
            'checked_time_ratio': durations['checked'] / total_ms if total_ms else None,
            'has_gaps': any(i['kind'] != 'pending' for i in issues), 'has_pending': bool(counts['pending']),
            'gap_ms': span_ms(issues), 'issue_segment_counts':issue_counts,
            'speech_insufficient_segments':speech_insufficient, 'segments': rows, 'issues': issues}


def rule_coverage(rule, segments):
    rows, issues = [], []
    for segment in segments:
        decisions = [d for d in _decisions(segment) if str(d.get('rule_id')) == rule['id']]
        results = [_result(d) for d in decisions]
        retained_hit = segment.get('full_live') and 'hit' in results
        span = {'segment_id': segment['id'], 'start': segment.get('start_ms', 0) / 1000,
                'end': segment.get('end_ms', 0) / 1000}
        skipped = segment.get('review_status') == 'skipped'
        if retained_hit or (segment.get('review_status') == 'done' and
                            ('hit' in results or (len(results) == 1 and results[0] in {'no_hit', 'not_applicable'}))):
            category = 'checked'
        elif skipped and segment.get('skip_code') != 'ASR_RETRY_EXHAUSTED':
            category = 'unchecked'
        elif not skipped and results == ['pending']:
            category = 'pending'
        elif skipped or segment.get('review_status') == 'done':
            category = 'evidence_insufficient'
        else:
            category = 'pending'
        rows.append({**span, 'category': category})
        if category == 'checked':
            if 'speech' in rule.get('modalities', ['speech']):
                gaps = segment.get('speech_gaps', [])
                if gaps or segment.get('asr_status') in {'failed','timed_out','submission_unknown'}:
                    ranges = [{'start':max(span['start'], g['start_ms']/1000),
                               'end':min(span['end'], g['end_ms']/1000)} for g in gaps]
                    for missing in ranges or [span]:
                        if missing['end'] > missing['start']:
                            issues.append({**span, **missing, 'kind':'speech', 'reason':'部分语音证据缺失，已确认的判断仍保留'})
            if 'image' in rule.get('modalities', []) and segment.get('frame_status') in {'failed','unavailable'}:
                issues.append({**span, 'kind':'image', 'reason':'画面证据缺失，已确认的判断仍保留'})
            continue
        decision_reason = '；'.join(dict.fromkeys(public_text(d.get('reason') or '').strip()
                                                   for d in decisions)).strip('；')
        if category == 'unchecked':
            kind, reason = 'unchecked', skip_reason(segment)
        elif category == 'pending':
            kind, reason = 'pending', '该片段尚未完成判定'
        elif skipped and segment.get('skip_code') == 'ASR_RETRY_EXHAUSTED':
            kind, reason = 'speech', skip_reason(segment)
        elif not decisions:
            kind, reason = 'judgment_missing', '该片段缺少规则判断结果'
        elif 'speech' in rule.get('modalities', ['speech']) and (
                segment.get('asr_status') not in ASR_SUCCESS | {'no_audio'} or segment.get('speech_gaps')
                or (not segment.get('subtitles') and segment.get('asr_status') != 'no_audio')):
            kind, reason = 'speech', decision_reason or '语音证据不足（原因未记录）'
        else:
            modalities = rule.get('modalities', [])
            image_missing = 'image' in modalities and segment.get('frame_status') in {'failed', 'unavailable'}
            kind = 'image' if image_missing else 'judgment_insufficient'
            reason = decision_reason or '原因未记录'
        issues.append({**span, 'kind': kind, 'reason': reason})
    return summarize_coverage(rows, issues)


def report_coverage(rules, source_gaps=()):
    """One task segment is counted once, using its least complete rule coverage."""
    priority = {'checked': 0, 'evidence_insufficient': 1, 'pending': 2, 'unchecked': 3}
    rows, issues = {}, []
    for rule in rules:
        summary = rule['coverage_summary']
        issues.extend(summary['issues'])
        for row in summary['segments']:
            saved = rows.get(row['segment_id'])
            if saved is None or priority[row['category']] > priority[saved['category']]:
                rows[row['segment_id']] = row
    # Source failures remain visible even when sufficient evidence supports a hit.
    by_segment_kind = {}
    for issue in issues:
        by_segment_kind.setdefault((issue.get('segment_id'), issue['kind']), []).append(issue)
    for gap in source_gaps:
        if gap['kind'] == 'image_unsampled':
            continue
        matching = by_segment_kind.setdefault((gap.get('segment_id'), gap['kind']), [])
        if any(i['start'] <= gap['start'] and i['end'] >= gap['end'] for i in matching):
            continue
        issue = {**gap, 'reason':public_text(gap.get('reason') or '原因未记录')}
        issues.append(issue)
        matching.append(issue)
    return summarize_coverage(list(rows.values()), issues)


def report_conclusion(rules, summary, speech_only=False):
    counts = {key: sum(r['counts'].get(key, 0) for r in rules) for key in DECISION_RESULTS}
    result = assessment(counts)
    scope = '已检测字幕' if speech_only else '已检测范围'
    text = ('已发现规则命中' if result == 'hit' else f'{scope}中未发现规则命中' if result == 'no_hit_in_checked_scope'
            else '已判定内容中的规则均不适用' if result == 'not_applicable' else '没有足够的有效判断，无法给出质检结论')
    if summary['has_gaps']:
        text += '，存在检测缺口'
    if summary['has_pending']:
        text += '，仍有待判定内容'
    return {'assessment': result, 'summary': text + '。', 'coverage_summary': summary}


def _report_gaps(segments, capture, rules, speech_only=False, planned=()):
    if planned:
        from runtime.store import uncovered_ranges
        capture = {**capture, **{key:uncovered_ranges(capture.get(key, []), planned)
                                for key in ('gaps', 'analysis_gaps')}}
    gaps = [{'start': g['start_ms'] / 1000, 'end': g['end_ms'] / 1000, 'kind': 'capture',
             'reason': '该时段未采集或判定，缺少录制内容', 'seekable': False}
            for g in capture.get('gaps', [])]
    gaps.extend({'start':g['start_ms']/1000,'end':g['end_ms']/1000,'kind':'judgment',
                 'reason':'已录制但未完成分析，语音和画面均未判定','seekable':True}
                for g in capture.get('analysis_gaps',[]))
    gaps.extend({'start':g['start_ms']/1000, 'end':g['end_ms']/1000, 'kind':'sampling',
                 'reason':g['reason'], 'seekable':False} for g in planned)
    insufficient_segments = {s['segment_id'] for rule in rules for group in rule['judgments']
                             if group['result'] == 'insufficient' for s in group['segments']}
    for segment in segments:
        span = {'segment_id': segment['id'], 'start': segment.get('start_ms', 0) / 1000,
                'end': segment.get('end_ms', 0) / 1000, 'seekable': True}
        if segment.get('review_status') == 'skipped':
            gaps.append({**span,'kind':'judgment','reason':'语音已判定，补充画面未完成判定' if segment.get('speech_reviewed') else skip_reason(segment),'duration_ms':segment['end_ms']-segment['start_ms']})
            continue
        source_gap = False
        for field, kind in (('asr_status', 'speech'), ('frame_status', 'image')):
            status = segment.get(field)
            if status in ASR_SUCCESS or (kind == 'speech' and status == 'no_audio'):
                continue
            if kind=='image' and speech_only and status=='disabled':
                continue
            if kind=='image' and segment.get('full_live') and status in {'not_required','not_scheduled'}:
                if status=='not_scheduled':gaps.append({**span,'kind':'image_unsampled','reason':'当前时段未计划采样画面'})
                continue
            source_gap = True
            if kind=='speech' and segment.get('speech_gaps'):
                gaps.extend({**span,'start':g['start_ms']/1000,'end':g['end_ms']/1000,
                             'kind':'speech','reason':'检测到语音但未识别出文本'} for g in segment['speech_gaps'])
                continue
            if kind == 'speech':
                # Diagnostics may contain credentials/URLs; expose only allowlisted messages.
                category = (segment.get('asr_diagnostic') or {}).get('category')
                reason = {'upload_address_failed': '云端获取上传地址失败，提交状态未确认',
                          'CLOUD_ASR_AUTH_UNAVAILABLE': '云端认证不可用',
                          'ASR_EMPTY_SPEECH': '本地识别为空'}.get(category)
                reason = reason or {'failed': '语音识别失败', 'timed_out': '语音识别超时',
                                    'submission_unknown': '云端提交状态未确认'}.get(status, '语音证据尚未就绪')
                if segment.get('local_failure') == 'ASR_EMPTY_SPEECH' and category != 'ASR_EMPTY_SPEECH':
                    reason = '本地识别为空；' + reason
            else:
                reason = '图片送检已关闭，未检测画面' if status == 'disabled' else '计划采样画面不可用，语音检测继续' if status == 'unavailable' else '画面提取失败' if status == 'failed' else '画面证据尚未就绪'
            gaps.append({**span, 'kind': kind, 'reason': reason})
        if not source_gap and segment['id'] in insufficient_segments:
            gaps.append({**span, 'kind': 'judgment', 'reason': '规则结果缺失或证据不足，具体原因见规则判断依据'})
    return sorted(gaps, key=lambda gap: gap['start'])


def _rules(task):
    rules = task.get('rules_snapshot', {}).get('rules', [])
    return [{**rule, 'id': str(rule.get('id', rule.get('rule_id', index))),
             'name': rule.get('name', rule.get('rule_name', '质检规则'))}
            for index, rule in enumerate(rules)
            if rule.get('kind') != 'visual_router' and rule.get('count_as_risk', True)]


def video_coverage(task, segments, rules, coverage, status):
    """Time coverage is a union of intervals, not a count of segments."""
    duration = task.get('source_duration_ms') or max([s['end_ms'] for s in segments] + [0])
    def merged(rows):
        spans = []
        for s in sorted(rows,key=lambda s:s['start_ms']):
            a,b=max(0,s['start_ms']),min(duration,s['end_ms'])
            if b<=a:continue
            if spans and a<=spans[-1][1]:spans[-1][1]=max(b,spans[-1][1])
            else:spans.append([a,b])
        return spans
    reviewed = [s for s in segments if s.get('review_status')=='done']
    covered = merged(reviewed)
    reviewed_ms = sum(b-a for a,b in covered)
    deferred = [s for s in segments if s.get('review_status')=='deferred']
    coverage.update(deferred=len(deferred), reviewed_ms=reviewed_ms,
                    total_ms=duration, reviewed_ratio=reviewed_ms/duration if duration else 0)
    gaps = [g for g in coverage['gaps'] if g['kind']!='capture']
    cursor=0
    for a,b in merged(segments):
        if a>cursor:gaps.append({'start':cursor/1000,'end':a/1000,'kind':'capture','reason':'该时段未采集或判定','seekable':False})
        cursor=b
    if duration>cursor:gaps.append({'start':cursor/1000,'end':duration/1000,'kind':'capture','reason':'该时段未采集或判定','seekable':False})
    reasons={'INPUT_REPAIR_EXHAUSTED':'判定输入修正达到上限，待续办','EVIDENCE_UNAVAILABLE':'证据不可用，待续办','REVIEW_BLOCKED':'判定受阻，待续办'}
    for s in segments:
        if s.get('review_status') not in {'done','skipped'}:
            code=(s.get('review_defer') or {}).get('reason_code')
            gaps.append({'segment_id':s['id'],'start':s['start_ms']/1000,'end':s['end_ms']/1000,
                         'kind':'deferred' if s.get('review_status')=='deferred' else 'pending',
                         'reason':reasons.get(code,'该片段尚未完成判定'),'seekable':True})
    coverage['gaps']=sorted(gaps,key=lambda g:(g['start'],g['kind']))
    unresolved=any(s.get('review_status') not in {'done','skipped'} for s in segments)
    processing=(task.get('capture_status') in {'ended','stopped','failed'} and task.get('worker_status') in {'done','failed','stopped'}
                and not unresolved and not status['media_pending'])
    incomplete=any(r['counts']['insufficient'] or r['counts']['pending'] or r['result']=='insufficient' for r in rules)
    # Valid silence is evidence; failed or empty transcripts alone are not.
    effective=any(s.get('subtitles') or s.get('frames') or s.get('asr_status')=='no_audio' for s in reviewed)
    required={m for r in rules for m in r.get('modalities',[])}
    source_missing=any(('speech' in required and s.get('asr_status') not in ASR_SUCCESS|{'no_audio'})
                       or ('image' in required and (s.get('frame_status') not in ASR_SUCCESS or not s.get('frames'))) for s in segments)
    complete=bool(duration and rules and effective and reviewed_ms==duration and processing and not incomplete and not source_missing)
    label='未完成有效检测' if not effective else '完整检测结果' if complete else '部分检测结果'
    coverage['message'] += f' 已判定时间覆盖 {reviewed_ms/1000:g}/{duration/1000:g} 秒；待续办 {len(deferred)} 段。'
    return {'processing_complete':bool(processing),'coverage_complete':complete,'label':label,
            'effective_evidence':effective}


def skip_reason(segment):
    if segment.get('policy_version')=='lite_sample_v1':
        from runtime.sampling import REASONS
        return REASONS.get(segment.get('skip_code'),'证据不足')
    reasons = {'LIVE_BACKLOG_SKIPPED':'积压超过 3 分钟，保留最近 2 分钟',
               'LIVE_REVIEW_TIMEOUT':'批次 120 秒无提交进展，结束剩余检测',
               'LIVE_FINISH_SKIPPED':'收尾超过 120 秒，未完成检测',
               'USER_DISCARD':'用户明确舍弃剩余检测', 'NO_SPEECH_EVIDENCE':'结束时无可用语音文字'}
    if segment.get('skip_code') in reasons:return reasons[segment['skip_code']]
    if segment.get('skip_reason') == '用户主动停止，未完成检测':return segment['skip_reason']
    return 'ASR 重试耗尽，已跳过该段判别' if segment.get('skip_code')=='ASR_RETRY_EXHAUSTED' else '结束后未完成检测'
