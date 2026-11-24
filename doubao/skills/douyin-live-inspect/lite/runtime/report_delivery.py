"""保证 Agent 续办信息可读，同时不丢弃完整质检证据。"""
import os
import datetime
import sys
import tempfile
from pathlib import Path
from runtime.store import encode

RECAP_REMINDER = '如长时间未收到复盘报告，请回到原对话发送“生成复盘报告”。'


def attach_report_delivery(data, command):
    """选择当前报告作为宿主交付物，不能用实时工作台替代报告。"""
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
            delivery.update(url=data.get('report_url'), message=f'请交付本次{name} HTML。')
        else:
            delivery['message'] = (f'请通过宿主附件能力交付本次{name}的 HTML。'
                '在对话展示实际返回的预览或下载入口，不能只发云电脑路径或 file URI，不能用 monitor 工作台代替报告。'
                '仅宿主附件能力不可用或交付失败时改为完整 Chat 报告，并说明报告页未交付、以 channel=chat 确认。')
        delivery['message'] += ('最终总结中的报告链接也必须使用本次真实地址；不得把“已交付”、状态文字或相对文件名填作链接目标。'
            '已展示文件卡片时可直接写“见下方文件卡片”，无真实地址不另造 Markdown 链接。')
        if 'media' in artifacts and artifacts['media']['path'].endswith('.mp4'):
            if mode == 'local_dashboard':
                delivery['message'] += '回放视频为独立 MP4；随 HTML 交付 media 附件并保留相对目录，下载后在本地打开。'
            else:
                delivery['message'] += '宿主单独预览 HTML 时无法读取相邻 MP4。如需在报告中回放，沿原目录用 --single-file 导出并交付，打开附件点风险时间验证播放；超出宿主附件限制时随报告交付独立 MP4 并说明限制。'
        channel = 'file'
    else:
        delivery.update(type='chat_report', message=((f'请交付{name}无法生成的实际原因，不编造报告。' if failed else f'请在当前对话交付完整{name}正文。') +
            ('报告页未交付，请说明实际导出或附件不可用原因。' if mode != 'chat' else '')))
        channel = 'chat'
    delivery['message'] += ('结论仅限已检测内容；说明已检测与舍弃数量、范围及原因，不把未检测当无风险；实际交付后才确认对应回执。'
        '质检报告先交付，再按后续动作完成复盘；不得在仅交付质检报告时结束执行；两份结果均实际交付前不得宣称完成。')
    if kind == 'review' and data.get('status') == 'ready' and data.get('available'):
        delivery['message'] += ('复盘成功交付并完成原流程确认后，仅在最终聊天回复结尾邀请用户“继续聊聊”：'
            '结合经营数据分析、挑选高光剪辑、优化下一场直播脚本；结合本场发现简短推荐，等待用户选择后再执行。'
            '引导不写入报告正文、HTML 或 summary.md。执行细节见 ../references/doubao-delivery.md 的“复盘后继续聊聊”。')
    media = artifacts.get('media', {})
    if media.get('path', '').endswith('.zip'):
        delivery['message'] += '完整 MP4 合成失败。请通过 present_files 或宿主附件工具随报告单独交付 media 中的 FLV 切片 ZIP，展示实际下载入口；附件交付失败时如实说明。'
    data['delivery'] = delivery
    if command == 'report' and not failed and data.get('recap', {}).get('status') == 'failed' and not data['recap'].get('terminal_failure'):
        delivery['message'] += '\n\n请在质检报告或附件后的对话正文展示以下提示（仍须立即继续生成复盘，不等待用户催促）：' + RECAP_REMINDER
    if data.get('delivery_ack_contract'):
        data['delivery_ack_contract']['template']['channel'] = channel


def retain_local_reports(store, data):
    """Keep final delivery files outside temporary tasks; never move the live monitor."""
    delivery = data.get('delivery', {})
    if (data.get('delivery_mode') != 'local_dashboard' or data.get('artifact_status') != 'ready'
            or delivery.get('type') != 'report_url'):
        return
    import hashlib
    import shutil
    from runtime.platform_support import private_directory, file_lock
    from runtime.static_delivery import media_file, atomic
    from runtime.live_room import web_rid
    message = ('豆包优先通过 present_files 将 delivery.path 交付为文件卡片，使用宿主实际返回的入口；'
        '已展示卡片时总结引用卡片，不额外贴 file://。其他宿主仅在确认支持本地文件链接时使用 delivery.url。'
        '附件不可用或打开失败时说明报告页尚不可访问，复用原报告补交或交付完整 Chat 正文；不重新采集。'
        'workflow_complete 仅表示交付回执齐全，不证明宿主打开、刷新或回放成功。')
    delivery['message'] = message + delivery.get('message', '')
    selected = [a for a in data.get('artifacts', [])
                if a.get('status') == 'ready' and a.get('type') in {'quality', 'review', 'media', 'summary'}]
    try:
        # The original path separates legacy tasks even when they lack a business ID.
        identity = hashlib.sha256(str(store.root.resolve()).encode()).hexdigest()[:24]
        base = private_directory(Path.home() / 'DouyinLiveInspect')
        task = store.task()
        room = web_rid(task)
        if room:
            try:
                started = datetime.datetime.fromisoformat(task['created_at'].replace('Z', '+00:00'))
                if started.tzinfo is None:
                    raise ValueError('task start timezone missing')
                stamp = started.astimezone(datetime.timezone(datetime.timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S')
                if sys.platform == 'win32':
                    stamp = stamp.replace(':', '：')
            except (KeyError, ValueError, TypeError, AttributeError):
                room = None  # Legacy tasks without a start time retain their task identity.
        root = private_directory(private_directory(base / 'Reports') / (room or identity))
        replacements = {}
        with file_lock(root / '.delivery.lock', timeout=2):
            if room:
                folder = root / stamp
                owner = folder / '.task'
                if folder.exists() and (not owner.is_file() or owner.read_text() != identity):
                    folder = root / (stamp + ' (' + identity + ')')
                root = private_directory(folder)
                owner = root / '.task'
                if owner.exists() and owner.read_text() != identity:
                    raise ValueError('report directory belongs to another task')
                atomic(owner, identity)
            # Publish media first so a newly opened report never references an unfinished copy.
            for item in sorted(selected, key=lambda a: a['type'] != 'media'):
                source = media_file(store, item['path'])
                if source is None:
                    raise ValueError('report artifact unavailable')
                target = (private_directory(root / 'media') if item['type'] == 'media' else root) / source.name
                fd, temporary = tempfile.mkstemp(prefix='.delivery-', dir=target.parent)
                try:
                    with os.fdopen(fd, 'wb') as output, source.open('rb') as stream:
                        shutil.copyfileobj(stream, output)
                    os.replace(temporary, target)
                finally:
                    if os.path.exists(temporary): os.unlink(temporary)
                replacements[item['path']] = str(target)
        # Only advertise retained files after every required copy succeeded.
        for item in selected:
            item['path'] = replacements[item['path']]
        delivery['path'] = replacements[delivery['path']]
        delivery['url'] = data['report_url'] = Path(delivery['path']).as_uri()
        if data.get('review_report_url'):
            review = next((a for a in selected if a['type'] == 'review'), None)
            if review: data['review_report_url'] = Path(review['path']).as_uri()
        delivery['message'] += '报告产物已保存到独立持久目录；如有 media，移动或下载时保留相对目录。'
    except (OSError, ValueError, TimeoutError):
        delivery['message'] += '持久副本保存失败，当前路径仍为原任务产物；请用原文件卡片补交并说明留存限制，不宣称已稳定保存。'


def public_live_report(report):
    """向用户展示直播报告时保留覆盖范围限制，避免把未检测内容包装成无风险。"""
    import copy
    result=copy.deepcopy(report)
    result['display_scope']='checked_content'
    for key in ('asr_sources','sampling'):
        result.pop(key,None)
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
    if 'scoring_context' in source:
        context = source['scoring_context']
        quality['scoring_context'] = {**context,
            'evidence': [e for e in context['evidence'] if e.get('segment_id') in ids],
            'issues': [i for i in context['issues'] if i.get('segment_id') in ids]}
    return {**source, **quality, 'segments': segments,
            'evidence': [e for e in source['evidence'] if e['segment_id'] in ids],
            'offset': offset, 'total_segments': len(source['segments']), 'next_offset': next_offset,
            'next_page_argv': ['recap-input', '--task-dir', str(task_dir), '--offset', str(next_offset)]
                             if next_offset is not None else None}


def recap_brief(store, source):
    """Shorten model input only; validation and saved evidence stay complete."""
    if not source['segments'] or any(not isinstance(s.get('summary'), str) or not s['summary'].strip()
                                     for s in source['segments']):
        return source
    context = source['scoring_context']
    risk_segments = {e['segment_id'] for e in context['evidence']
                     if e['kind'] == 'quality' and e.get('result') == 'hit'}
    # Scoring retains content evidence, including segments with no risk hits.
    result = {**source,
        'evidence_file': bounded_output(store, 'recap-input', source, force=True)['data']['result_file'],
        'segments': [{k:v for k,v in s.items() if k not in ('evidence_ids', 'decisions')} for s in source['segments']],
        'evidence': [e for e in source['evidence'] if e['segment_id'] in risk_segments]}
    if 'quality_conclusion' in source:
        result['quality_conclusion'] = {**source['quality_conclusion'],
            'coverage_summary': compact_coverage(source['quality_conclusion']['coverage_summary'])}
        result['rule_assessments'] = [{**r, 'coverage_summary': compact_coverage(r['coverage_summary'])}
                                      for r in source.get('rule_assessments', [])]
    return result


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
    if full.get('remediation'):
        remediation = full['remediation']
        summary['remediation'] = {k: remediation[k] for k in ('status', 'version', 'message') if k in remediation}
        summary['remediation'].update(details_file=str(path),
            item_count=len(remediation.get('items', [])), pending_count=len(remediation.get('pending', [])))
    if 'coverage_complete' in full['conclusion']:summary['coverage_complete'] = full['conclusion']['coverage_complete']
    if 'evidence_gaps' in full:summary['evidence_gaps'] = full['evidence_gaps']
    result = {**data, 'report': summary, 'report_details_file': str(path)}
    # Coverage timelines are in the full report; avoid duplicating them in stdout.
    result.pop('coverage', None)
    source = result.get('recap_input')
    if source:
        source = recap_brief(store, source)
        result['recap_input'] = {k: source[k] for k in ('identity', 'duration_ms', 'evidence_version', 'recap')}
        result['recap_input']['total_segments'] = len(source['segments'])
        result['recap_input']['result_file'] = bounded_output(store, 'recap-input', source, force=True)['data']['result_file']
        result['recap_input']['read_argv'] = ['recap-input', '--task-dir', str(store.root), '--offset', '0']
        result['next_action'] = result['after_delivery_next_action'] = 'read-recap-evidence-pages'
        result['submission_contract'] = {**result['submission_contract'], 'instruction':
            '先交付质检报告，再完整读取 recap_input.result_file；无法读文件才按 read_argv 分页。'
            + result['submission_contract']['instruction']}
    if len(encode(result).encode()) > 22000 and result.get('submission_contract',{}).get('analysis_rules'):
        # Keep the complete policy available without exceeding the command reply budget.
        result['submission_contract'] = {**result['submission_contract'],
            'analysis_rules':'分析前读取 analysis_rules_file 的完整规则；不能以本回执摘要代替规则。',
            'analysis_rules_file':str(Path(__file__).resolve().parents[1]/'assets/rules/recap-rules.md')}
    return result


MAX_OUTPUT_BYTES = 24 * 1024


def bounded_output(store, command, data, *, force=False, read_only=False):
    """超出输出上限时按内容哈希落盘，绝不截断证据或提交契约。"""
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
        folder.mkdir(mode=0o777 if os.name == 'nt' else 0o700,exist_ok=True)
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
        summary['submission_contract'] = {k:contract[k] for k in ('protocol','input_path','draft_state','submit_command_argv','submit_argv','verify_argv','state_argv','inspection_scope') if k in contract}
        # Keep the standalone argv; its suffix is the same command in the current Lite runtime.
        if contract.get('submit_command_argv') and contract.get('submit_argv', [])[2:] == contract['submit_command_argv']:
            del summary['submission_contract']['submit_command_argv']
        if contract.get('verify_argv', [])[:1] == ['recap-report']:
            summary['submission_contract']['instruction'] = contract['instruction']
        summary['context_id'] = contract.get('template', {}).get('context_id')
    # Host delivery must remain actionable even when evidence moves to a file.
    summary.update({k:data[k] for k in ('delivery_mode','delivery','artifact_status','artifacts',
        'source_end_reason','live_source_status','capture_status_text','source_refresh',
        'capture_failure','diagnostic_delivery','snapshot_check','snapshot_events','snapshot_delivery','after_delivery_next_action','credential_worker_action','qa_worker_action',
        'poll_after_seconds','wait_command_argv','continuation_path','continuation_instruction') if k in data})
    if 'continuation_instruction' in summary:
        # The immediate action is pagination; the saved result retains its own
        # continuation. Do not tell the Agent to submit before reading evidence.
        summary['continuation_instruction'] = '先读完整结果，再续办。'
        if data.get('workflow_complete') is False:
            summary['continuation_instruction'] += ' 按完整结果的 next_action 继续，不以最终回复结束本轮。'
    if data.get('delivery_required') and 'delivery_ack_contract' in data:
        summary['delivery_ack_contract'] = data['delivery_ack_contract']
    delivery_instruction = ('先按 Lite 入口执行 snapshot_check 的 status 检查并处理附件，再回到本响应。' if data.get('snapshot_check') else '')
    if data.get('source_refresh'):delivery_instruction='先按 source_refresh 从当前直播页补源并交回原任务，随后读本批完整结果。'+delivery_instruction
    if data.get('snapshot_delivery'):delivery_instruction += '先交付 snapshot_delivery 工作台附件。'
    if data.get('diagnostic_delivery'):delivery_instruction += '按 diagnostic_delivery 交付采集失败诊断；这不是有效报告。'
    if data.get('delivery'):delivery_instruction += '报告按 delivery 交付；Chat 降级须完整读取正文。'
    if data.get('credential_worker_action'):delivery_instruction += '先处理 credential_worker_action，再继续原动作；不等待刷新完成。'
    if data.get('qa_worker_action'):delivery_instruction += '继续风险判定前先处理 qa_worker_action：补齐子任务或记录具体失败，未到重试时间则继续原流程。'
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
