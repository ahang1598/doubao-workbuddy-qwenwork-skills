"""Keep Agent continuation readable without discarding report evidence."""
import os
import tempfile
from runtime.store import encode, upgrade_guidance

RECAP_REMINDER = '如长时间未收到复盘报告，请回到原对话发送“生成复盘报告”。'


def attach_report_delivery(data, command):
    """Select the current report, never the workbench, for actual host delivery."""
    if not data.get('delivery_required') or not (data.get('status') in {'ready','failed','blocked'} or data.get('available')):
        return
    kind = 'quality' if command == 'report' else 'review'
    name = '质检报告' if kind == 'quality' else '内容复盘报告'
    mode = data.get('delivery_mode', 'chat')
    artifacts = {a['type']:a for a in data.get('artifacts', []) if a.get('status') == 'ready'}
    item = artifacts.get(kind) if data.get('artifact_status') == 'ready' else None
    delivery = {**data.get('delivery', {}), 'required':True, 'report_kind':'quality' if kind == 'quality' else 'recap'}
    failed = data.get('status') in {'failed','blocked'}
    if mode != 'chat' and item and not failed:
        delivery.update(type='report_url' if mode == 'local_dashboard' else 'html_snapshot',
                        path=item['path'], artifact_type=item['type'], version=item['version'])
        if mode == 'local_dashboard':
            delivery.update(url=data.get('report_url'), message=f'请打开并交付本次{name} 独立 HTML 链接，已保存的视频内嵌。')
        else:
            delivery['message'] = (f'请通过宿主附件能力交付本次{name}的单文件 HTML。'
                '在对话展示实际返回的预览或下载入口，不能只发云电脑路径或 file URI，不能用 monitor 工作台代替报告。'
                '仅宿主附件能力不可用或交付失败时改为完整 Chat 报告，并说明报告页未交付、以 channel=chat 确认。')
        channel = 'file'
    else:
        delivery.update(type='chat_report', message=((f'请交付{name}无法生成的实际原因，不编造报告。' if failed else f'请在当前对话交付完整{name}正文。') +
            ('报告页未交付，请说明实际导出或附件不可用原因。' if mode != 'chat' else '')))
        channel = 'chat'
    delivery['message'] += ('结论仅限已检测内容；说明已检测与舍弃数量、范围及原因，不把未检测当无风险；实际交付后才确认对应回执。'
        '质检报告先交付，再按后续动作完成复盘；不得在仅交付质检报告时结束执行；两份结果均实际交付前不得宣称完成。')
    if not failed:
        upgrade = data.get('upgrade') or upgrade_guidance()
        data['upgrade'] = upgrade
        delivery['message'] += ('\n\n按交付规则适用开通引导时，在同次对话完整展示以下内容，不得仅摘取链接；'
            '分为“方式一：飞书群沟通（更高效）”和“方式二：提交工单”两个独立段落；填写项用列表且仅归属方式二，能力介绍单独置于最后。工单填写步骤支持小字则用小字，否则用普通文字。已确认开通或属于登录、网络、配置故障时改给对应恢复说明。\n\n'
            + upgrade['markdown'])
    data['delivery'] = delivery
    if command == 'report' and not failed and data.get('recap', {}).get('status') == 'failed' and not data['recap'].get('terminal_failure'):
        delivery['message'] += '\n\n请在质检报告或附件后的对话正文展示以下提示（仍须立即继续生成复盘，不等待用户催促）：' + RECAP_REMINDER
    if data.get('delivery_ack_contract'):
        data['delivery_ack_contract']['template']['channel'] = channel


def public_live_report(report):
    """Keep coverage limitations alongside user-facing live reports."""
    import copy
    result=copy.deepcopy(report)
    result['display_scope']='checked_content'
    for key in ('asr_sources','sampling'):
        result.pop(key,None)
    conclusion=result.get('conclusion')
    if isinstance(conclusion,dict):
        assessment=conclusion.get('assessment','undetermined')
        result['conclusion']={**conclusion,'assessment':assessment,'summary':{
            'hit':'已检测内容中发现规则命中。',
            'no_hit_in_checked_scope':'已检测内容中未发现规则命中。',
            'not_applicable':'已检测内容中未发现适用规则命中。'
        }.get(assessment,'检测未完成，无法给出质检结论。') + (' 存在未检测内容，详见覆盖范围与缺口。' if result.get('skipped_segment_count') else '')}
    for rule in result.get('rules',[]):
        rule['display_scope']='checked_content'
        for key in ('coverage_summary','counts','judgments'):rule.pop(key,None)
    if isinstance(result.get('asr'),dict):
        result['asr']={k:v for k,v in result['asr'].items() if k=='utterances'}
    return result


def compact_coverage(summary):
    return {**{k:v for k,v in summary.items() if k not in ('segments', 'issues')},
            'issue_reasons': sorted({i['reason'] for i in summary.get('issues', []) if i.get('reason')})}


def paged_conclusion(conclusion, ids, include_unassigned=False):
    coverage = conclusion['coverage_summary']
    return {**conclusion, 'coverage_summary': {**coverage, 'range_scope':'page',
            'segments':[s for s in coverage['segments'] if s['segment_id'] in ids],
            'issues':[i for i in coverage['issues'] if i.get('segment_id') in ids or (include_unassigned and i.get('segment_id') is None)]}}

def evidence_page(source, task_dir, offset=0):
    coverage_rows = source.get('quality_conclusion', {}).get('coverage_summary', {}).get('segments', [])
    total = max(len(source['segments']), len(coverage_rows))
    if offset < 0 or offset > total:
        raise ValueError('invalid recap offset')
    segments = source['segments'][offset:offset + 5]
    ids = {s['id'] for s in segments}
    end = min(offset + 5, total)
    next_offset = end if end < total else None
    # Evidence can exclude discarded/unreviewed segments. Page coverage separately
    # with the same cursor so their reasons survive, without duplicating ranges.
    quality = {}
    if 'quality_conclusion' in source:
        coverage_ids = {s['segment_id'] for s in coverage_rows[offset:offset + 5]}
        quality['quality_conclusion'] = paged_conclusion(source['quality_conclusion'], coverage_ids, offset == 0)
        quality['rule_assessments'] = [paged_conclusion(r, coverage_ids, offset == 0) for r in source.get('rule_assessments', [])]
        quality['total_coverage_segments'] = len(coverage_rows)
    return {**source, **quality, 'segments': segments,
            'evidence': [e for e in source['evidence'] if e['segment_id'] in ids],
            'offset': offset, 'total_segments': len(source['segments']), 'next_offset': next_offset,
            'next_page_argv': ['recap-input', '--task-dir', str(task_dir), '--offset', str(next_offset)]
                             if next_offset is not None else None}


def compact_report(store, data):
    if len(encode(data).encode()) <= 24000:
        return data
    # Full quality details remain private and are not fetched from worker logs.
    full = data['report']
    path = store.root / 'quality-report-details.json'
    fd, temporary = tempfile.mkstemp(prefix='.quality-report-', dir=store.root)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            stream.write(encode(full))
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary): os.unlink(temporary)
    summary = {k: full[k] for k in ('duration_seconds', 'segment_count',
               'reviewed_segment_count', 'skipped_segment_count', 'hit_rule_count', 'conclusion','display_scope') if k in full}
    if 'coverage_summary' in full['conclusion']:
        summary['conclusion'] = {**full['conclusion'], 'coverage_summary': compact_coverage(full['conclusion']['coverage_summary'])}
    summary['rules'] = [{**{k:v for k,v in r.items() if k not in ('judgments','coverage_summary')},
                         **({'coverage_summary':compact_coverage(r['coverage_summary'])} if 'coverage_summary' in r else {})} for r in full['rules']]
    summary['hit_rules'] = [{**r, 'events': r['events'][:2], 'total_events': len(r['events'])}
                            for r in full['hit_rules']]
    summary['details_file'] = str(path)
    if 'coverage_complete' in full['conclusion']:summary['coverage_complete'] = full['conclusion']['coverage_complete']
    if 'evidence_gaps' in full:summary['evidence_gaps'] = full['evidence_gaps']
    result = {**data, 'report': summary, 'report_details_file': str(path)}
    # Coverage timelines are in the full report; avoid duplicating them in stdout.
    result.pop('coverage', None)
    source = result.get('recap_input')
    if source:
        result['recap_input'] = {k: source[k] for k in ('identity', 'duration_ms', 'evidence_version', 'recap')}
        result['recap_input']['total_segments'] = len(source['segments'])
        result['recap_input']['result_file'] = bounded_output(store, 'recap-input', source, force=True)['data']['result_file']
        result['recap_input']['read_argv'] = ['recap-input', '--task-dir', str(store.root), '--offset', '0']
        result['next_action'] = result['after_delivery_next_action'] = 'read-recap-evidence-pages'
        result['submission_contract']['instruction'] = (
            '先交付 report 中的质检摘要和报告链接，优先完整读取 recap_input.result_file 中全部证据；无法读文件才执行 recap_input.read_argv 分页。'
            '使用完整证据分析并按本合同提交；采用分页时沿 next_page_argv 读取直到 next_offset=null，再合并。'
            '证据版本须始终一致，变化时从第一页重新读取。不要读取 worker.log，不要等待后台模型。'
            '质检完整细节仅在 report_details_file；不能将质检摘要当作完整复盘证据。')
    return result


MAX_OUTPUT_BYTES = 24 * 1024


def bounded_output(store, command, data, *, force=False, read_only=False):
    """Persist overflow by content hash; never truncate actual evidence or a contract."""
    import hashlib
    from runtime.store import atomic_json
    envelope={'ok':True,'command':command,'data':data}
    if not force and len(encode(envelope).encode('utf-8'))+1<=MAX_OUTPUT_BYTES:
        return envelope
    raw=encode(data)
    result_id=hashlib.sha256(raw.encode('utf-8')).hexdigest()
    folder=store.root/'.cli-results'
    path=folder/(result_id+'.json')
    if read_only:
        if not path.is_file(): raise ValueError('saved result unavailable')
    else:
        folder.mkdir(mode=0o700,exist_ok=True)
        if not path.exists():atomic_json(path,data)
    summary={k:v for k,v in data.items() if k in ('status','workflow_complete','workflow_outcome','terminal_failure','report_ready','delivery_required',
                                               'saved_count','error_count','duplicate_count')
             and isinstance(v,(bool,int,str)) and len(str(v))<=200}
    # Keep executable bindings visible while the complete evidence remains immutable.
    source = data.get('next') if isinstance(data.get('next'), dict) else data
    contract = source.get('submission_contract', {})
    summary.update({k:source[k] for k in ('task_id','batch_id','generation','executor','dispatch_contract','capability_check','rules_load_contract') if k in source})
    for name in ('capability_check', 'rules_load_contract'):
        if name in summary:
            # Detailed instructions stay in the full result; leave room for the
            # continuation that tells an idle Agent how to make progress.
            summary[name]={k:v for k,v in summary[name].items() if k!='instruction'}
    if contract:
        summary['submission_contract'] = {k:contract[k] for k in ('protocol','input_path','draft_state','submit_command_argv','submit_argv','state_argv','inspection_scope') if k in contract}
        summary['context_id'] = contract.get('template', {}).get('context_id')
    # Host delivery must remain actionable even when evidence moves to a file.
    summary.update({k:data[k] for k in ('delivery_mode','delivery','artifact_status','artifacts',
        'snapshot_check','snapshot_events','snapshot_delivery','after_delivery_next_action',
        'poll_after_seconds','continuation_path','continuation_instruction') if k in data})
    if 'continuation_instruction' in summary:
        # The immediate action is pagination; the saved result retains its own
        # continuation. Do not tell the Agent to submit before reading evidence.
        summary['continuation_instruction'] = '先读完整结果，再续办。'
    if data.get('delivery_required') and 'delivery_ack_contract' in data:
        summary['delivery_ack_contract'] = data['delivery_ack_contract']
    delivery_instruction = ('先按 Lite 入口执行 snapshot_check 的 status 检查并处理附件，再回到本响应。' if data.get('snapshot_check') else '')
    if data.get('snapshot_delivery'):delivery_instruction += '先交付 snapshot_delivery 工作台附件。'
    if data.get('delivery'):delivery_instruction += '报告按 delivery 交付；Chat 降级须完整读取正文。'
    return {'ok':True,'command':command,'data':{**summary,
        'next_action':'read-result-pages','result_id':result_id,'total_bytes':len(raw.encode('utf-8')),
        'total_chars':len(raw),'offset_unit':'unicode_code_points','result_file':str(path),
        'original_next_action':str(data.get('next_action',''))[:200],
        'read_argv':['result-page','--task-dir',str(store.root),'--result-id',result_id,'--offset','0'],
        'instruction':delivery_instruction+'Read result_file or follow read_argv/next_page_argv to next_offset=null; then follow its next_action.'}}


def result_page(store, result_id, offset):
    import hashlib
    import re
    if not isinstance(result_id,str) or not re.fullmatch('[0-9a-f]{64}',result_id):
        raise ValueError('invalid result ID')
    path=store.root/'.cli-results'/(result_id+'.json')
    # Keep pagination content-bound across refreshes/restarts/concurrent commands.
    raw=path.read_text(encoding='utf-8')
    if hashlib.sha256(raw.encode('utf-8')).hexdigest() != result_id:
        raise ValueError('saved result digest mismatch; reconcile the original request')
    if type(offset) is not int or not 0<=offset<=len(raw):
        from runtime.review_errors import ReviewError
        error=ReviewError('RESULT_OFFSET_INVALID','offset','偏移越界；完整读取 result_file，或从第一页沿 next_page_argv 恢复。',next_action='read-result-pages')
        error.detail.update(total_chars=len(raw),offset_unit='unicode_code_points',result_file=str(path),
            read_argv=['result-page','--task-dir',str(store.root),'--result-id',result_id,'--offset','0'])
        raise error
    end=min(len(raw),offset+4000)
    fragment=raw[offset:end]
    while len(encode(fragment).encode('utf-8'))>16000:
        end=offset+(end-offset)//2
        fragment=raw[offset:end]
    next_offset=end if end<len(raw) else None
    return {'result_id':result_id,'offset':offset,'total_chars':len(raw),'offset_unit':'unicode_code_points','json_fragment':fragment,'next_offset':next_offset,
        'next_page_argv':['result-page','--task-dir',str(store.root),'--result-id',result_id,'--offset',str(next_offset)] if next_offset is not None else None}
