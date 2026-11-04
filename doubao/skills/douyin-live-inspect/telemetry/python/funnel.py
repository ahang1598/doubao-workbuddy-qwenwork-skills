"""复用业务报告状态、覆盖率和交付回执，生成 Lite 单任务及视频批次的漏斗事实。
保留有效质检、报告生成、实际交付和复盘的不同统计含义；发送时机由事务模块控制。
"""
import re
from urllib.parse import urlsplit
import uuid
from runtime.bridge import FUNNEL
from runtime.context import dimensions, ERRORS

def failed_source_page(task):
    """Keep the supplied page URL byte-for-byte, including room-identifying query."""
    if (task.get('kind') != 'live' or task.get('capture_status') != 'failed' or
            task.get('source_error_code') not in {'DOUYIN_FETCH_FAILED', 'DOUYIN_PAGE_UNAVAILABLE',
                                                'DOUYIN_FLV_UNAVAILABLE', 'DOUYIN_RESOLVER_UNAVAILABLE'}):
        return None
    source = task.get('source')
    if not isinstance(source, str):
        return None
    match = re.search(r'https://(?:live|www|v)\.douyin\.com/[^\s<>"，。]+', source)
    url = source if source.startswith(('https://', 'http://')) and not re.search(r'\s', source) else match[0] if match else source
    if re.search(r'[\s\x00-\x1f\x7f\\]', url):
        return None
    try:
        parsed = urlsplit(url)
        if (parsed.scheme not in {'http', 'https'} or parsed.hostname not in
                {'live.douyin.com', 'www.douyin.com', 'v.douyin.com'} or parsed.username or parsed.password or
                parsed.port not in (None, 443 if parsed.scheme == 'https' else 80) or
                re.search(r'\.(?:flv|m3u8|mp4|ts)$', parsed.path, re.I)):
            return None
    except ValueError:
        return None
    return url

def token(task, segments):
    from runtime.recap import evidence_input
    return evidence_input(task, segments)['evidence_version']

def video_fingerprint(store, task, segments, status=None):
    from runtime.static_delivery import FrozenStore
    from runtime.video_report import snapshot_key
    from runtime.ui import build_report
    # Use this transaction's data; opening another connection would see the old report.
    frozen = FrozenStore(store, snapshot=(task, segments,
        status if status is not None else store._status(task, segments)))
    return snapshot_key(frozen, build_report(frozen))

def state(store, task, segments, connection, status=None, *, reviewed=None):
    if status is None:status = store._status(task, segments)
    if reviewed is None:reviewed = sum(s.get('review_status') == 'done' and bool(s.get('review_result')) for s in segments)
    effective = bool(reviewed)
    ready = bool(effective and status['report_ready'])
    quality = recap = 'none'
    recap_status = {'status':'not_required'}
    outcome, failure_stage, failure_reason = 'unknown', 'none', 'none'
    delivery_error = 'none'
    if task.get('kind') == 'video':
        ready = False  # Generation requires a matching persisted report, not just ready inputs.
        receipt = task.get('_funnel_video_receipt', {})
        # Both resume and same-run report changes invalidate a previous delivery.
        if (receipt and receipt.get('report_run') == task.get('video_report_run', 1)
                and receipt.get('run_index') == (task.get('_telemetry') or {}).get('run_index', 1)
                and receipt.get('token') == token(task, segments)
                and receipt.get('fingerprint') == video_fingerprint(store, task, segments, status)):
            # A generated report can truthfully describe zero completed judgments.
            ready = bool(receipt.get('ready'))
            quality = 'ready' if ready and receipt.get('status') == 'delivered' else 'none'
            delivery_error = 'host' if receipt.get('status') == 'failed' else 'none'
        complete = quality == 'ready'
    else:
        from runtime.recap import evidence_input, state as recap_state
        source = evidence_input(task, segments)
        recap_status = recap_state(task, source)
        from runtime.report_completion import outcome_available
        # 复用回执确认的业务规则；质检统计额外要求有真实保存的判定。
        delivery_status = {**status, 'report_ready': ready}
        def delivery(kind):
            receipt = task.get('report_deliveries', {}).get(kind, {})
            outcome = receipt.get('outcome', 'ready')
            if (receipt.get('evidence_version') == source['evidence_version']
                    and outcome in {'ready', 'failed'}
                    and outcome_available(task, kind, outcome, delivery_status, recap_status)):
                return outcome
            return 'none'
        quality, recap = delivery('quality'), delivery('recap')
        complete = quality == 'ready' and recap == 'ready' and recap_status.get('status') == 'ready'
        if complete and task.get('review_dispatch_version') == 2 and not task.get('media_frozen'):
            from runtime.report_completion import has_active_review_child
            complete = not has_active_review_child(connection, store.session_id)
    terminal = task.get('worker_status') in {'done','failed','stopped'} and task.get('capture_status') in {'ended','failed','stopped'}
    if complete:
        outcome = 'success'
    elif delivery_error == 'host':
        outcome, failure_stage, failure_reason = 'failed', 'delivery', 'HOST_DELIVERY_FAILED'
    elif terminal and not ready and (task.get('capture_status') == 'failed' or task.get('worker_status') == 'failed') and any(
            (task.get(key) or {}).get('code') == 'OUT_OF_MEMORY' or (task.get(key) or {}).get('category') == 'MemoryError'
            for key in ('capture_diagnostic', 'failure_diagnostic', 'stream_diagnostic')):
        outcome, failure_stage, failure_reason = 'failed', 'inspection', 'OUT_OF_MEMORY'
    elif recap_status.get('status') == 'insufficient':
        outcome, failure_stage, failure_reason = 'insufficient', 'recap', 'CONTENT_INSUFFICIENT'
    elif recap_status.get('terminal_failure'):
        outcome, failure_stage, failure_reason = 'failed', 'recap', 'RECAP_FAILED'
    elif terminal and not ready and task.get('capture_status') == 'failed':
        code = task.get('source_error_code')
        # Only explicit transport evidence refines a generic resolver failure.
        detail = (task.get('capture_diagnostic') or {}).get('source_failure') or {}
        if (code in {'XHS_FETCH_FAILED','XHS_PAGE_UNAVAILABLE','XHS_AUTH_REQUIRED','XHS_STREAM_UNAVAILABLE','XHS_LIVE_STATE_UNKNOWN','INVALID_BROWSER_SOURCE','DOUYIN_FETCH_FAILED', 'DOUYIN_PAGE_UNAVAILABLE', 'DOUYIN_FLV_UNAVAILABLE', 'DOUYIN_RESOLVER_UNAVAILABLE'}
                and detail.get('kind') in {'dns_error', 'tls_error', 'network_timeout', 'connection_error'}):
            code = 'NETWORK_ERROR'
        outcome, failure_stage, failure_reason = 'failed', 'inspection', code if code and code != 'none' else 'TASK_FAILED'
    elif terminal and not ready and task.get('worker_status') == 'failed':
        exhausted = any(s.get('skip_code') == 'ASR_RETRY_EXHAUSTED' for s in segments)
        outcome, failure_stage, failure_reason = 'failed', 'inspection', 'ASR_RETRY_EXHAUSTED' if exhausted else 'TASK_FAILED'
    elif recap_status.get('status') == 'blocked':
        outcome, failure_stage, failure_reason = 'insufficient', 'recap', recap_status.get('code', 'CONTENT_INSUFFICIENT')
    elif terminal and not ready and (status.get('report_blocked_reason') or
            (not status['review_pending'] and not status['media_pending'] and not effective)):
        outcome, failure_stage, failure_reason = 'insufficient', 'quality', (
            status.get('report_blocked_reason') or ('NO_REVIEWED_CONTENT' if segments else 'NO_CAPTURED_CONTENT'))
    elif quality == 'failed' or recap == 'failed':
        outcome, failure_stage, failure_reason = 'failed', 'quality' if quality == 'failed' else 'recap', 'TASK_FAILED'
    # Retryable attempt failures remain in-progress online; local attempt events explain them.
    if recap_status.get('status') == 'failed' and not recap_status.get('terminal_failure') and recap != 'failed':
        recap_status = {**recap_status, 'status': 'generating'}
    # Source attribution is business state: a later confirmation must advance the snapshot.
    source = {k: v for k, v in dimensions(task).items() if k in
              {'live_source_status', 'capture_status', 'source_end_reason', 'source_error_code'}}
    diagnostic = {}
    if task.get('kind') == 'video':
        diagnostic = {
            'asr_pending_segments': status['pipeline']['asr']['pending_segments'],
            'media_pending_segments': status['media_pending'],
            'review_pending_segments': status['review_pending'],
            'review_ready_segments': status['review_ready_pending'],
            'reviewed_segments': reviewed,
            'skipped_segments': sum(s.get('review_status') == 'skipped' for s in segments),
            'report_status': 'ready' if ready else 'blocked' if status.get('report_blocked_reason') or (outcome == 'insufficient' and failure_stage == 'quality') else
                             'pending_media' if status['media_pending'] else 'pending_review' if status['review_pending'] else 'unknown',
        }
    return {**source, **diagnostic, 'flow_result':outcome, 'failure_stage':failure_stage, 'failure_reason':failure_reason,
            'recap_status':recap_status.get('status','missing'), 'effective_result': int(effective), 'quality_ready': int(ready),
            'quality_delivery': quality, 'recap_delivery': recap,
            'workflow_success': int(complete), 'delivery_error': delivery_error,
            'quality_blocked': int(not ready and bool(status.get('report_blocked_reason'))),
            'funnel_run': (task.get('_telemetry') or {}).get('run_index', 1)}

def payload(record, current, dims):
    if record.get('funnel_schema_version') != 1:
        return None
    previous = record.get('funnel_snapshot', {})
    if previous.get('state') == current:
        return None
    revision = previous.get('revision', 0) + 1
    record['funnel_snapshot'] = {'revision': revision, 'state': current}
    extra = {k: record[k] for k in ('telemetry_task_id','task_type','task_started_at','run_index') if k in record}
    # A bounded identity independent of event arrival time / command invocation.
    extra.update(dims)
    extra.update(record.get('owner') or {})
    extra.update(current)
    extra.update(funnel_schema_version=1, funnel_revision=revision,
                 lifecycle_event_id=str(uuid.uuid5(uuid.UUID(record['telemetry_task_id']), f'funnel:{revision}')))
    return {'command': FUNNEL.SNAPSHOT, 'extra': extra}

def source_dimensions(task):
    dims = dimensions(task)
    if (task.get('kind') == 'live' and task.get('capture_status') == 'failed'
            and task.get('source_error_code') in {'XHS_FETCH_FAILED','XHS_PAGE_UNAVAILABLE','XHS_AUTH_REQUIRED','XHS_STREAM_UNAVAILABLE','XHS_LIVE_STATE_UNKNOWN','BROWSER_SOURCE_TIMEOUT','BROWSER_SOURCE_TASK_CLOSED','INVALID_BROWSER_SOURCE','DOUYIN_FETCH_FAILED', 'DOUYIN_PAGE_UNAVAILABLE',
                'DOUYIN_FLV_UNAVAILABLE', 'DOUYIN_RESOLVER_UNAVAILABLE'}):
        from runtime.http_fetch import safe_failure
        diagnostic = task.get('capture_diagnostic')
        detail = safe_failure(diagnostic.get('source_failure') if isinstance(diagnostic, dict) else None)
        if detail:
            dims['source_failure_kind'] = detail['kind']
            if 'http_status' in detail:dims['source_http_status'] = detail['http_status']
    if (task.get('kind') == 'live' and task.get('capture_status') == 'failed'
            and task.get('source_error_code') == 'STREAM_RETRY_EXHAUSTED'):
        from runtime.capture_diagnostics import safe_process
        detail = safe_process(task.get('capture_process_diagnostic'))
        for source, target in [('category', 'capture_error_category'),
                               ('http_status', 'capture_http_status'), ('exit_code', 'capture_exit_code')]:
            if source in detail:
                dims[target] = detail[source]
    if (task.get('kind') == 'live' and task.get('capture_status') == 'failed'
            and task.get('source_end_reason') == 'capture_failed'):
        from runtime.capture_diagnostics import summarize, CATEGORIES
        assessment = (summarize(task) or {}).get('assessment')
        # A final exception can supersede an earlier pull failure. Do not attach
        # the earlier process's HTTP/exit codes to this different cause.
        if assessment in CATEGORIES:dims['capture_error_category'] = assessment
    page = failed_source_page(task)
    if page is not None:
        if len(page) <= 512:
            dims['source_page_url'] = page
        # Reuse acquisition's identity rules; do not guess room_id or conflicting IDs.
        from runtime.douyin_live import validate_douyin_live_url, DouyinLiveError
        try:
            reference = validate_douyin_live_url(page)
            if reference.startswith('https://live.douyin.com/'):
                reference = 'https://live.douyin.com/?live_web_rid=' + reference.rsplit('/', 1)[1]
            if len(reference) <= 160:
                dims['source_page_ref'] = reference
                dims.setdefault('source_page_url', reference)
        except DouyinLiveError:
            pass
    return dims


def batch_state(data, children):
    all_flag = lambda key: int(bool(children) and all(c.get(key) == 1 for c in children))
    delivered = bool(children) and all(c.get('quality_delivery') == 'ready' for c in children)
    failed = next((c for c in children if c.get('flow_result') == 'failed'), None)
    insufficient = next((c for c in children if c.get('flow_result') == 'insufficient'), None)
    cause = failed or insufficient or {}
    missing_failed = next((v for i,v in enumerate(data['videos'])
                           if v.get('status') == 'failed' and not children[i]), None)
    batch_reason = (missing_failed or {}).get('error')
    batch_reason = batch_reason if batch_reason in ERRORS and batch_reason != 'none' else 'TASK_FAILED'
    # Missing old-version counters remain unknown, never manufacture zeroes.
    counters = ('asr_pending_segments', 'media_pending_segments', 'review_pending_segments',
                'review_ready_segments', 'reviewed_segments', 'skipped_segments')
    diagnostic = {key: sum(c[key] for c in children if c) for key in counters
                  if any(children) and all(key in c for c in children if c)}
    pending_index = next((i + 1 for i,c in enumerate(children)
                          if c.get('report_status') in ('pending_media', 'pending_review')), None)
    if pending_index is not None: diagnostic['pending_child_index'] = pending_index
    cause_index = next((i + 1 for i,c in enumerate(children) if c and c is cause), None)
    if cause_index is not None: diagnostic['diagnostic_child_index'] = cause_index
    return {**diagnostic, 'flow_result':'success' if delivered else 'failed' if failed or missing_failed else 'insufficient' if insufficient else 'unknown',
            'failure_stage':cause.get('failure_stage','startup' if missing_failed else 'none'),
            'failure_reason':cause.get('failure_reason',batch_reason if missing_failed else 'none'),
            'recap_status':'not_required', 'effective_result': all_flag('effective_result'), 'quality_ready': all_flag('quality_ready'),
            'quality_delivery': 'ready' if delivered else 'none', 'recap_delivery': 'none',
            'workflow_success': int(delivered), 'delivery_error': 'host' if any(c.get('delivery_error') == 'host' for c in children) else 'none',
            'quality_blocked': int(any(c.get('quality_blocked') for c in children)),
            'funnel_run': data['_telemetry']['run_index'], 'expected_children': len(children),
            'observed_children': sum(bool(c) for c in children)}
