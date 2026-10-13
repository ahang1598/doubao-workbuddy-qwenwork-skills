"""Adapt local content-only inspection data to the existing Inspect UI.

Read-only projections shared by static HTML and Chat delivery.
"""
from __future__ import annotations

import datetime as dt
import json
import math
from pathlib import Path
from runtime.recap import recap_report
from runtime.report_data import public_text, _rules, _rule_summary, _report_gaps, _decisions, _result, ASR_SUCCESS, DECISION_RESULTS, report_coverage, report_conclusion

ASSETS = Path(__file__).resolve().parents[1] / 'assets' / 'ui'

def _seconds(value):
    if isinstance(value, (int, float)):
        return value / 1000 if value > 1e12 else value
    if isinstance(value, str):
        try:
            return dt.datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp()
        except ValueError:
            pass
    return 0


def _time(ms):
    seconds = max(0, int(ms or 0) // 1000)
    return f'{seconds // 3600:02d}:{seconds // 60 % 60:02d}:{seconds % 60:02d}'



def _evidence(store):
    from runtime.sampling import report_store
    store=report_store(store)
    """Only expose explicitly indexed artifacts, never arbitrary filesystem paths."""
    items = {}
    for segment in store.segments():
        for frame in segment.get('frames', []):
            items[f"{segment['id']}:{frame['id']}"] = frame.get('path', '')
    playback = store.task().get('playback_file')
    if playback:
        items['playback'] = playback
    return items


def coverage(store):
    status = store.status()
    from runtime.full_live import speech_only_scope
    speech_only=speech_only_scope(store.task())
    segments = store.segments()
    skipped = sum(s.get('review_status') == 'skipped' for s in segments)
    total = len(segments)
    reviewed = sum(s.get('review_status') == 'done' for s in segments)
    asr_terminal = {'done', 'ready', 'completed', 'success', 'no_audio', 'failed', 'timed_out', 'submission_unknown'}
    frame_terminal = {'done', 'ready', 'completed', 'success', 'failed','not_required','not_scheduled','unavailable','disabled'}
    media_pending = sum(s.get('review_status') != 'skipped' and (s.get('asr_status') not in asr_terminal or s.get('frame_status') not in frame_terminal)
                        for s in segments)
    speech_gap_segments = [s for s in segments if s.get('asr_status') in {'failed', 'timed_out', 'submission_unknown'}]
    image_gap_segments = [] if speech_only else [s for s in segments if s.get('frame_status') in {'failed', 'unavailable'}]
    evidence_gap_ids = {s['id'] for s in speech_gap_segments + image_gap_segments}
    evidence_gaps = len(evidence_gap_ids)
    from runtime.store import interval_ms
    speech_ranges = []
    for segment in speech_gap_segments:
        ranges = [{'start_ms': max(segment.get('start_ms', 0), gap.get('start_ms', 0)),
                   'end_ms': min(segment.get('end_ms', 0), gap.get('end_ms', 0))}
                  for gap in segment.get('speech_gaps', [])]
        ranges = [r for r in ranges if r['end_ms'] > r['start_ms']]
        speech_ranges.extend(ranges or [segment])
    speech_gap_ms = interval_ms(speech_ranges)
    # Pending media cannot dilute the gap ratio. This controls presentation
    # only: evidence gaps and insufficient decisions remain in the report.
    speech_processed_ms = interval_ms([s for s in segments if s.get('asr_status') in asr_terminal])
    speech_gap_ratio = speech_gap_ms / speech_processed_ms if speech_processed_ms else None
    minor_speech_gap = (0 < speech_gap_ms <= 1000 or
                        speech_gap_ratio is not None and 0 < speech_gap_ratio <= 0.01)
    speech_gap_warning = bool(speech_gap_segments) and not minor_speech_gap
    visible_gap_ids = {s['id'] for s in image_gap_segments + (speech_gap_segments if speech_gap_warning else [])}
    evidence_gap_warning = bool(visible_gap_ids)
    image_disabled = sum(s.get('frame_status') == 'disabled' for s in segments)
    source_gaps = sum(s.get('asr_status') not in {'done', 'ready', 'completed', 'success', 'no_audio'}
                      or s.get('frame_status') not in {'done', 'ready', 'completed', 'success'}
                      for s in segments)
    pending_media = sum(s.get('review_status') not in {'done','skipped'}
                        and (s.get('asr_status') not in asr_terminal or s.get('frame_status') not in frame_terminal)
                        for s in segments)
    reviewed_ms=interval_ms([s for s in segments if s.get('review_status')=='done'])
    skipped_ms=interval_ms([s for s in segments if s.get('review_status')=='skipped'])
    asr_skips=[s for s in segments if s.get('review_status')=='skipped' and s.get('skip_code')=='ASR_RETRY_EXHAUSTED']
    asr_skipped=len(asr_skips)
    asr_skipped_ms=sum(s['end_ms']-s['start_ms'] for s in asr_skips)
    if status.get('full_live'):
        media_pending=status['media_pending'];pending_media=media_pending
        source_gaps=status['evidence_gaps']
    pending = total - reviewed - skipped
    ready_pending = max(0, pending - pending_media)
    message = f'内容片段 {total} 个：已判定 {reviewed} 个；待判定 {pending} 个'
    if skipped:
        message += f"；已检测 {reviewed_ms/1000:g} 秒"
        if asr_skipped:message += f"；ASR 失败跳过 {asr_skipped} 个，共 {asr_skipped_ms/1000:g} 秒"
        if skipped>asr_skipped:
            label='结束后未完成检测' if status.get('finishing',{}).get('phase')=='completed' else '未检测（积压或超时，详见明细）'
            message += f"；{label} {skipped-asr_skipped} 个，共 {(skipped_ms-asr_skipped_ms)/1000:g} 秒"
    if pending:
        ready_label = ('可进入判定（含已终结缺口）' if evidence_gap_warning else
                       '可进入判定' if evidence_gaps else '证据完整、可进入判定')
        message += f'（媒体处理中 {pending_media} 个，{ready_label} {ready_pending} 个）'
    open_ms = status.get('task', {}).get('open_segment_ms', 0)
    if open_ms:
        message += f'；采集中、等待切片闭合 {open_ms/1000:g} 秒'
    if evidence_gap_warning:
        if speech_only:
            message += f'；{len(visible_gap_ids)} 个片段存在语音识别缺口（实际缺失约 {speech_gap_ms/1000:g} 秒；画面关闭不计入缺口）'
        else:
            message += f'；{len(visible_gap_ids)} 个片段存在语音或画面证据缺口'
    if speech_only:
        message += '；检测范围：仅字幕，画面未检测'
    elif image_disabled:
        message += f'；画面检测已关闭，{image_disabled} 个片段不检查画面'
    message += '。'
    return {'segments': total, 'reviewed': reviewed, 'pending': pending, 'skipped':skipped,
            'finishing':status.get('finishing',{}),
            'asr_skipped':asr_skipped,'asr_skipped_ms':asr_skipped_ms,'reviewed_ms':reviewed_ms,
            'finish_skipped':skipped-asr_skipped,'skipped_ms':skipped_ms,
            'media_pending': media_pending, 'pending_media': pending_media,
            'ready_pending': ready_pending, 'evidence_gaps': evidence_gaps,
            'speech_gap_segments':len(speech_gap_segments),'speech_gap_ms':speech_gap_ms,
            'speech_processed_ms':speech_processed_ms,'speech_gap_ratio':speech_gap_ratio,
            'speech_gap_warning':speech_gap_warning,'evidence_gap_warning':evidence_gap_warning,
            'image_gap_segments':len(image_gap_segments),
            'evidence_pending': status.get('evidence_pending'),
            'image_disabled': image_disabled,
            'inspection_scope': 'speech_only' if speech_only else None,
            # Missing/failed source channels are never represented as clean evidence.
            'source_gaps': source_gaps,
            'message': message,
            'capture': store.status().get('coverage', {})}


def build_report(store, token=''):
    from runtime.sampling import report_store
    store=report_store(store)
    inspection_status = store.status()
    task, segments = store.task(), store.segments()
    from runtime.full_live import speech_only_scope
    speech_only=speech_only_scope(task)
    rules = _rules(task)
    evidence, utterances = [], []
    rule_conclusions = {}
    available = _evidence(store)
    for segment in segments:
        subtitles = segment.get('subtitles', [])
        utterances.extend({'start': u.get('start_ms', 0) / 1000,
                           'end': u.get('end_ms', u.get('start_ms', 0)) / 1000,
                           'text': u.get('text', '')} for u in subtitles)
        if segment.get('review_status') != 'done' and not (segment.get('full_live') and segment.get('speech_reviewed')):
            continue
        for index, decision in enumerate(_decisions(segment)):
            rule_id = str(decision.get('rule_id', ''))
            if _result(decision) != 'hit':
                continue
            if rule_id not in {r['id'] for r in rules}:
                continue
            events = decision.get('events') or []
            positioned_events = 0
            for event_index, event in enumerate(events):
                start, end = event.get('start_ms'), event.get('end_ms')
                if not all(type(t) in (int, float) and math.isfinite(t) and t >= 0 for t in (start, end)) or end < start:
                    continue
                positioned_events += 1
                references = set(map(str, event.get('evidence_ids', [])))
                frame_ids = [f"{segment['id']}:{f['id']}" for f in segment.get('frames', [])
                             if str(f['id']) in references]
                text = event.get('text') or '\n'.join(u.get('text', '') for u in subtitles if str(u.get('id')) in references)
                evidence.append({'id': f"s{segment['id']}-d{index}-e{event_index}", 'rule_id': rule_id,
                                 'rule_name': next((r['name'] for r in rules if r['id'] == rule_id), '质检规则'),
                                 'start': start / 1000,
                                 'end': end / 1000,
                                 'kind': 'image' if frame_ids else 'text', 'text': text,
                                 'reason': public_text(decision.get('reason', '')),
                                 'images': [f'evidence:{fid}'
                                            for fid in frame_ids if fid in available],
                                 'frame_ids': frame_ids})
            if not positioned_events or positioned_events < len(events):
                reasons = rule_conclusions.setdefault(rule_id, [])
                reason = public_text(decision.get('reason') or '').strip() or '规则已命中，具体判断依据未保存'
                if reason not in reasons:
                    reasons.append(reason)
    cov = coverage(store)
    captured_content_reviewed = bool(segments) and not cov['pending'] and not cov['skipped'] and not cov['capture'].get('analysis_gaps')
    for rule in rules:
        rule.update(_rule_summary(rule, segments))
        rule['status'] = 2 if rule['result'] == 'hit' else 1 if rule['result'] in ('clear', 'not_applicable') else None
    cov['gaps'] = _report_gaps(segments, cov['capture'], rules, speech_only)
    cov['speech_gaps'] = sum(g['kind'] == 'speech' for g in cov['gaps'])
    cov['image_gaps'] = sum(g['kind'] == 'image' for g in cov['gaps'])
    rule_counts = {result: sum(r['result'] == result for r in rules)
                   for result in ('hit', 'clear', 'pending', 'insufficient', 'not_applicable')}
    asr_summary = {backend: dict.fromkeys(('success', 'failed', 'pending', 'no_audio', 'skipped'), 0)
                   for backend in ('local', 'cloud', 'unknown')}
    for segment in segments:
        backend = segment.get('asr_backend') or task.get('asr_backend', 'mediakit')
        backend = 'cloud' if backend == 'mediakit' else 'local' if backend == 'local' else 'unknown'
        status = segment.get('asr_status')
        state = ('success' if status in ASR_SUCCESS else 'no_audio' if status == 'no_audio' else
                 'failed' if status in ('failed', 'timed_out', 'submission_unknown') else 'skipped' if segment.get('review_status')=='skipped' else 'pending')
        asr_summary[backend][state] += 1
    terminal = task.get('capture_status') in ('stopped', 'ended', 'failed') and task.get('worker_status') in ('done', 'failed')
    coverage_complete = (captured_content_reviewed and not cov['source_gaps']
                         and not cov['capture'].get('missing_ms')
                         and cov['capture'].get('complete', True))
    if 'sampling' in inspection_status:
        sample=inspection_status['sampling']
        coverage_complete=coverage_complete and not sample['planned_unchecked_ranges'] and not sample['skipped_ranges']
        planned=sample['planned_unchecked_ranges']
        cov['gaps']=_report_gaps(segments,cov['capture'],rules,speech_only,planned)
    duration = max([s.get('end_ms', 0) for s in segments] + [task.get('capture_observed_ms', 0) or 0, task.get('capture_end_ms', 0) or 0]) / 1000
    video_state = {}
    if task.get('kind') == 'video':
        from runtime.report_data import video_coverage
        video_state = video_coverage(task, segments, rules, cov, inspection_status)
        duration = cov['total_ms'] / 1000
    scoped_conclusion = report_conclusion(rules, report_coverage(rules, cov['gaps']), speech_only)
    rule_gaps=[{'bundle':b,'message':name+'专项追加未完成；该专项不在本次结论范围内。'}
               for b,name in (('finance','金融'),('ecommerce','电商')) if b in task.get('rule_load_gaps',{})]
    if rule_gaps:
        coverage_complete=False
        scoped_conclusion['rule_load_gaps']=rule_gaps
        scoped_conclusion['summary']=scoped_conclusion.get('summary','')+' '+' '.join(g['message'] for g in rule_gaps)
    return {**video_state, 'report_kind': task.get('kind', 'live'),
            'inspection_scope': 'speech_only' if speech_only else None,
            'task': {'id': task.get('id'), 'name': task.get('name', '直播内容质检'),
            'scenario_name': '' if task.get('rules_mode')=='dynamic' else task.get('scenario', ''), 'created_time': _seconds(task.get('created_at')),
            'machine_start_time': task.get('capture_epoch', 0),
            'machine_end_time': (task.get('capture_epoch', 0) + task['capture_end_ms'] / 1000) if task.get('capture_epoch') and task.get('capture_end_ms') is not None else 0},
            'duration_seconds': duration, 'monitored_duration_ms':task.get('monitored_duration_ms'), 'rules': rules,
            'hit_rule_count': sum(r['status'] == 2 for r in rules), 'evidence': evidence,
            'hit_event_count':len(evidence), 'hit_count_basis':'按规则与证据事件计数，同一时间可命中多条规则',
            'rule_conclusions': [{'rule_id': r['id'], 'rule_name': r['name'], 'reasons': rule_conclusions[r['id']]}
                                 for r in rules if r['id'] in rule_conclusions],
            'conclusion': {**scoped_conclusion, **({'scope':'本次没有完成抽检，无法给出质检结论' if not inspection_status['sampling']['completed_windows'] else '本次抽检范围内未发现规则命中' if not any(r['status']==2 for r in rules) else '本次结论仅适用于已完成的抽检范围'} if 'sampling' in inspection_status else
                              {'scope':'仅字幕检测；画面未检测，画面风险不在结论范围内'} if speech_only else {}), 'captured_content_reviewed': captured_content_reviewed,
                           'progress': 'completed' if inspection_status['report_ready'] or (terminal and captured_content_reviewed) else 'running',
                           'rule_counts': rule_counts,
                           'has_incomplete_results': bool(rule_gaps) or bool(cov['capture'].get('analysis_gaps')) or not rules or any(r['counts']['pending'] or r['counts']['insufficient'] or r['counts']['skipped']
                                                                     or r['result'] == 'insufficient' for r in rules),
                           'coverage_complete': coverage_complete, **video_state},
            'asr': {'utterances': sorted(utterances, key=lambda u: u['start']),
                    'summary': asr_summary,
                    'sources': [{'segment_id':s['id'],'backend':s.get('asr_backend') or task.get('asr_backend','mediakit'),
                                 'local_failure':s.get('local_failure'), 'status': s.get('asr_status')} for s in segments]},
            'video': {'url': 'media/playback.mp4' if 'playback' in available else '',
                      'duration_seconds': duration, 'timeline': task.get('playback_map', [])}, 'coverage': cov,
            **({'sampling':inspection_status['sampling']} if 'sampling' in inspection_status else {})}


class _SnapshotView:
    """One immutable input set for every projection in a dashboard response."""
    def __init__(self, store):
        self.root=store.root
        if hasattr(store,'read_snapshot'):
            self._task_data,self._segments_data,self._status_data=store.read_snapshot()
        else:
            self._status_data=store.status()
            self._task_data,self._segments_data=store.task(),store.segments()
    def task(self):return self._task_data
    def segments(self):return self._segments_data
    def status(self):return self._status_data


def _pipeline_issues(task, segments):
    """Describe evidence and current work without inventing incident history."""
    from runtime.diagnostics import failure_label
    issues = []
    if task.get('capture_status') == 'failed':
        issues.append({'stage':'capture', 'state':'failed', 'message':failure_label(task),
                       'action':'已采集内容仍然保留。', 'segments':[]})
    if (task.get('worker_status') in {'failed','setup_pending'} and
            not task.get('processing_completed_at') and task.get('failure_stage') != 'capture'):
        issues.append({'stage':'processing', 'state':'failed',
                       'message':'媒体处理失败' if task.get('worker_status') == 'failed' else '媒体处理依赖未就绪',
                       'action':'请回到原对话排查并恢复原任务。', 'segments':[]})
    success = {'done','ready','completed','success'}
    for segment in segments:
        if segment.get('review_status') == 'skipped':continue
        for stage, field in (('asr','asr_status'), ('frames','frame_status')):
            value = segment.get(field)
            is_asr = stage == 'asr'
            diagnostic = segment.get('asr_diagnostic' if is_asr else 'frame_diagnostic') or {}
            code = diagnostic.get('category') or (segment.get('local_failure') if is_asr else None)
            final = segment.get('review_status') == 'done' or (is_asr and segment.get('asr_final'))
            recovering = is_asr and not final and (value == 'fallback_pending' or
                segment.get('asr_recovery_status') in {'preparing','running'})
            if value in success or (is_asr and value == 'no_audio'):
                if not (is_asr and segment.get('local_failure')):continue
                state = 'resolved'
            elif value in {'failed','timed_out','submission_unknown'}:
                state = 'evidence_gap' if final else 'recovering' if recovering else 'waiting'
            elif recovering:
                state = 'recovering'
            else:
                continue
            # Only allowlisted copy is public; raw diagnostic text may contain credentials.
            message = ({'ASR_EMPTY_SPEECH':'检测到语音活动，但未识别出文字',
                        'upload_address_failed':'云端获取上传地址失败，提交状态未确认',
                        'CLOUD_ASR_AUTH_UNAVAILABLE':'云端语音识别认证不可用'}.get(code)
                       if is_asr else None)
            message = message or ({'timed_out':'语音识别超时',
                                  'submission_unknown':'云端提交状态未确认，不可自动重复提交'}.get(value,
                                  '语音识别异常') if is_asr else '画面提取失败')
            action = {'resolved':'证据已补齐。', 'evidence_gap':'该证据缺口已保留，不代表检测通过。',
                      'recovering':'正在尝试恢复证据。', 'waiting':'请在原对话核对并继续处理。'}[state]
            span = {k:segment.get(k,0) for k in ('id','start_ms','end_ms')}
            existing = next((i for i in issues if (i['stage'],i['state'],i['message']) == (stage,state,message)), None)
            if existing:
                existing['segments'].append(span)
            else:
                issues.append({'stage':stage,'state':state,'message':message,'action':action,'segments':[span]})
    return issues


def _processing_progress(task, cov, status, issues):
    pending, media = cov['pending'], cov['pending_media']
    worker = task.get('worker_status','pending')
    finished_media = bool(task.get('processing_completed_at'))
    review = status.get('full_live') or {}
    dispatcher = review.get('dispatcher_status')
    in_flight = (dispatcher in {'active', 'stalled'} and review.get('inflight_batches', 0) > 0
                 and review.get('oldest_inflight_seconds', 0) < 180)
    waiting = any(i['stage'] in {'asr','frames'} and i['state']=='waiting' for i in issues)
    recovering = any(i['stage'] in {'asr','frames'} and i['state']=='recovering' for i in issues)
    if (status.get('full_live') or {}).get('cancelling_batches'):
        state, title, message = 'review_reconciling', '判定 Worker 退出待确认', '报告仅包含已保存结果；仍需确认在途 Worker 已退出，不能结束调度。'
    elif status.get('report_ready'):
        state, title, message = 'ready', '质检报告已生成', '质检报告已生成，可直接查看。'
    elif task.get('capture_status') == 'failed' and not cov['segments']:
        state, title, message = 'no_media', '未采集到内容，无法生成报告', '本次采集失败，未采集到可检测内容。'
    elif (status.get('finishing') or {}).get('phase') == 'completed':
        state, title, message = 'ended', '检测已结束', '未完成或缺失的内容不代表已检测通过。'
    elif (status.get('finishing') or {}).get('mode') == 'immediate':
        state, title, message = 'stopping', '正在停止剩余检测', '正在准备质检报告和复盘报告。'
    elif waiting or worker == 'setup_pending' or ((media or recovering) and (worker != 'running' or finished_media)):
        state, title, message = 'blocked', '媒体处理待恢复', '媒体处理未完成，等待在原对话排查并恢复原任务。'
    elif recovering:
        state, title, message = 'processing', '正在恢复媒体证据', '媒体处理正在尝试恢复，完成后继续判定。'
    elif media:
        state, title, message = 'processing', '正在处理已采集内容', f'还有 {media} 个片段需要完成媒体处理。'
    elif pending and dispatcher in {'launch_unknown', 'reconciling'}:
        state, title, message = 'review_reconciling', 'Worker 启动状态待确认', '在途任务尚需核对；不得重复派发，未占用证据可继续串行判定。'
    elif pending and dispatcher == 'interrupted':
        state, title = 'review_paused', '判定长时间无进展'
        message = '采集和语音识别仍可继续，但长时间未收到判定活动；需在原对话核对命令执行与已保存结果，不能据此认定会话已退出。'
    elif pending and in_flight:
        state, title, message = 'review_inflight', '判定批次处理中', '当前批次已领取，尚未提交判定结果；请等待本批次完成。'
    elif pending and dispatcher == 'stalled':
        state, title = 'review_stalled', '判定进度停滞'
        message = '采集和语音识别仍可继续，但 AI 判定已超过 60 秒没有提交结果；请在原对话检查在途批次。'
    elif pending:
        state, title, message = 'waiting_review', '等待剩余内容判定', '媒体证据处理已结束，等待当前对话继续判定；若对话已中断，请回到原对话继续。'
    else:
        state, title, message = 'waiting', '等待报告就绪', '请以实际报告就绪状态为准。'
    if pending and task.get('capture_status') in {'ended', 'stopped', 'failed'}:
        from runtime.diagnostics import capture_status_text
        message = message.replace('采集和语音识别仍可继续，但', '')
        message = capture_status_text(task) + '，采集已停止，已采集内容仍保留。' + message
    review_metrics = status.get('full_live') or {}
    review_error = review_metrics.get('last_review_error')
    if pending and review_error:
        code = review_error.get('code')
        if code in {'REVIEW_INVALID_JSON','REVIEW_JSON_INVALID'}:
            message += ' 判定提交的 JSON 格式错误，请在原对话修复后重交。'
        else:
            message += ' 判定提交校验失败，请在原对话修复失败项。'
        message += f" 提交校验失败 {review_metrics.get('review_validation_failures',0)} 次。"
        attempt = review_metrics.get('seconds_since_review_attempt')
        success = review_metrics.get('seconds_since_review_success')
        if isinstance(attempt,(int,float)):
            message += f' 最近提交尝试：{int(attempt)} 秒前。'
        message += f' 最近成功提交：{int(success)} 秒前。' if isinstance(success,(int,float)) else ' 尚无成功提交。'
    return {'state':state,'title':title,'message':f"已判定 {cov['reviewed']} 个片段，剩余 {pending} 个。{message}"}


def build_snapshot(store, token=''):
    store=_SnapshotView(store)
    status_data = store.status()
    finish = status_data.get('finishing', {})
    task, segments, report = store.task(), store.segments(), build_report(store, token)
    recap = recap_report(store, token)
    capture = task.get('capture_status', 'pending')
    worker = task.get('worker_status', 'pending')
    stopping = bool(task.get('stop_requested')) and capture not in ('stopped', 'ended', 'failed')
    terminal = capture in ('stopped', 'ended', 'failed')
    cov = report['coverage']
    issues = _pipeline_issues(task, segments)
    for issue in issues:
        issue['show_warning'] = not (issue['stage'] == 'asr' and issue['state'] == 'evidence_gap'
                                    and not cov['speech_gap_warning'])
    progress = _processing_progress(task, cov, status_data, issues)
    if 'sampling' in status_data:
        sampled=status_data['sampling']
        progress['message']=f"已完成 {sampled['completed_windows']} 个抽检窗口，抽检 {sampled['sampled_ms']/1000:g} 秒；正在判定 {sampled['active_windows']} 个，待判 {sampled['pending_windows']} 个。其余范围及跳过原因见报告。"
        if finish.get('phase')=='draining':progress['message']+=' 收尾总预算 60 秒，到期交付已完成结果。'
        if finish.get('phase')=='completed':progress['message']+=' 本次抽检已结束。'
    status = 5 if capture == 'failed' or worker == 'failed' else 4 if terminal else 2 if capture == 'running' else 1
    from runtime.diagnostics import failure_label, capture_status_text
    failure = failure_label(task)
    capture_text = capture_status_text(task)
    closed_text = capture_text if capture == 'ended' and task.get('kind', 'live') == 'live' else '采集已结束'
    dispatcher_status = (status_data.get('full_live') or {}).get('dispatcher_status')
    dispatcher_paused = dispatcher_status == 'interrupted' and cov['pending']
    dispatcher_inflight = progress['state'] == 'review_inflight'
    dispatcher_stalled = dispatcher_status == 'stalled' and cov['pending'] and not dispatcher_inflight
    name = (failure if failure
            else 'Worker 启动状态待确认' if dispatcher_status in {'launch_unknown','reconciling'}
            else '判定长时间无进展' if dispatcher_paused
            else '判定批次处理中' if dispatcher_inflight
            else '判定进度停滞' if dispatcher_stalled
            else closed_text + '，待完成判定' if terminal and cov['pending']
            else '已结束' if terminal else '质检中' if status == 2 else '等待采集')
    if stopping and not failure:
        name='已收到结束请求，正在停止采集'
    if finish.get('phase') == 'draining' and task.get('kind') == 'video':
        name = ('采集已结束，正在补齐画面与语音证据' if finish.get('waiting_for_frames') else
                '采集已结束，正在补齐语音识别' if finish.get('waiting_for_asr') else
                '采集已结束，正在收尾，最多等待 30 秒' if terminal else '正在停止采集并收尾，最多等待 30 秒')
    elif finish.get('phase') == 'draining':
        name = ('正在停止剩余检测' if finish.get('mode') == 'immediate' else
                '采集已结束，剩余内容检测中' if terminal else '正在停止采集，随后检测剩余内容')
    elif finish.get('skipped_segments'):
        name = '质检已结束，部分内容未完成检测'
    if terminal or finish.get('phase') == 'draining':
        suffix = {'review_reconciling':'Worker 启动状态待确认','review_paused':'判定长时间无进展','review_inflight':'判定批次处理中','review_stalled':'判定进度停滞','waiting_review':'待完成判定','blocked':'媒体处理待恢复',
                  'processing':'正在处理已采集内容' if failure else '剩余内容检测中',
                  'stopping':'正在停止剩余检测'}.get(progress['state'])
        if suffix:name = (failure or (closed_text if terminal else '正在停止采集')) + '，' + suffix
    if task.get('recovery_state') == 'worker_unresponsive':
        name='媒体 worker 无响应，正在等待独占锁释放'
    elif task.get('recovery_state') == 'blocked':
        name='媒体处理恢复受阻，请在原任务续办'
    # The badge describes inspection progress. Historical capture failures stay
    # in pipeline/issues and must not override a settled report or review queue.
    if (terminal or finish.get('phase') == 'completed') and cov['segments'] and progress['state'] in {'ready', 'ended'}:
        status = 4
        name = ('质检已结束，部分内容未完成检测' if cov['skipped'] else
                '质检已结束，存在证据缺口' if cov['evidence_gap_warning'] else '质检已结束')
    elif (terminal and cov['segments'] and progress['state'] in {'waiting_review', 'processing', 'stopping'}
          and failure in {'', '采集失败'}
          and not any(i['stage'] == 'processing' and i['state'] == 'failed' for i in issues)):
        status = 4
        name = closed_text + '，' + suffix
    elif failure and not name.startswith(failure):
        name = failure
    records = [{'id': index + 1, 'rule_id': e['rule_id'], 'rule_name': e['rule_name'],
                'machine_result': 'hit', 'samples': [{'text': e['text'], 'reason': e['reason'],
                'time': _time(e['start'] * 1000), 'evidence_id': next(iter(e['frame_ids']), None)}]}
               for index, e in enumerate(report['evidence'])]
    if task.get('media_frozen'):
        blocked=status_data.get('report_blocked_reason')
        reviewing=finish.get('phase')=='draining' and bool(status_data.get('review_pending'))
        message=('未检测到语音' if blocked=='NO_SPEECH' else '未获得可用语音文字，无法生成报告') if blocked else ('报告已生成' if status_data['report_ready'] and recap['available'] else '正在生成报告')
        if blocked:message='本次未能完成检测'
        elif reviewing:message='正在完成当前检测'
        elif recap['status']=='failed':message='质检报告可查看，复盘生成失败'
        status=5 if blocked or recap['status']=='failed' else 4
        name=message
        issues=[]
        progress={'state':'failed' if blocked or recap['status']=='failed' else 'processing' if reviewing else 'ready' if recap['available'] else 'generating','title':message,
                  'message':message if blocked or reviewing else '基于已检测内容生成质检报告和复盘。'}
    return {'ok': True, 'report_blocked_reason':status_data.get('report_blocked_reason'), 'finishing': finish, 'issues': issues, 'sampling': status_data.get('sampling'), 'full_live':status_data.get('full_live'), 'processing_progress': progress,
            'task': {'id': task.get('id'), 'name': task.get('name', '直播内容质检'),
            'inspection_policy':task.get('inspection_policy'),'kind': task.get('kind','live'), 'source_duration_ms': task.get('source_duration_ms'),
            'processed_ms': task.get('capture_observed_ms',0),
            'status': status, 'status_text': name, 'scenario_name': '' if task.get('rules_mode')=='dynamic' else task.get('scenario', ''),
            'media_frozen':bool(task.get('media_frozen')),
            'monitor_ended_at':task.get('monitor_ended_at'),
            'monitored_duration_ms':task.get('monitored_duration_ms'),
            'stop_requested': bool(task.get('stop_requested')),
            'stop_requested_at': _seconds(task.get('stop_requested_at')),
            'capture_status': capture,
            'capture_status_text': capture_text,
            'worker_status': worker,
            'recovery_state': task.get('recovery_state'),
            'created_at': task.get('capture_epoch') or _seconds(task.get('created_at')),
            'updated_at': (task.get('capture_epoch', 0) + task['capture_end_ms'] / 1000) if task.get('capture_epoch') and task.get('capture_end_ms') is not None else _seconds(task.get('updated_at'))},
            'records': records, 'refreshed_at': dt.datetime.now(dt.timezone.utc).isoformat(),
            'quality_report_url': 'quality.html' if store.status()['report_ready'] else '',
            'review_report_supported': task.get('kind') != 'video', 'recap': {k: v for k, v in recap.items() if k != 'document' and k not in ('evidence', 'references', 'video', 'coverage')},
            'review_report_url': 'review.html' if recap['available'] else '',
            'pipeline': store.status().get('pipeline', {}), 'coverage': cov}
