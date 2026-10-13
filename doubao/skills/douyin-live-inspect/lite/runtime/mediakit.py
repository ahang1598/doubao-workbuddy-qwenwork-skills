# Adapted from skills_live_inspect_lite/runtime/mediakit.py; content-only migration.
"""mediakit-cli-doubao 0.2.1 adapter. No credentials or CLI stderr in logs.

The host build is cloud-only and rejects --cloud; call domain commands directly.
Do not substitute the public CLI, which uses a different authentication contract.
"""
import json
from concurrent.futures import ThreadPoolExecutor
import math
import os
import re
from pathlib import Path
import shutil
import subprocess
import time

from .credentials import ENV_KEYS, environment, refresh, version as credential_version

DIAGNOSTIC_CATEGORIES = frozenset({
    'upload_address_failed', 'authentication_rejected', 'missing_task_id',
    'rate_limited', 'request_timeout', 'network_error', 'service_unavailable',
    'cli_failed', 'cli_unavailable', 'invalid_response', 'credentials_unavailable',
})


class CommandFailure(RuntimeError):
    def __init__(self, exit_code, output='', *, category=None, not_submitted=False):
        # Only fixed categories leave the adapter; never persist raw CLI output.
        text = output.lower()
        status = re.search(r'(?:http(?:/\d(?:\.\d)?)?\s+|["\']?(?:status_code|statuscode|status code)["\']?\s*[:=]\s*)([45]\d\d)\b', text)
        http_status = int(status.group(1)) if status else None
        if category is not None:
            pass
        elif http_status in (401, 403) or any(value in text for value in ('token expired', 'invalid token', 'token has expired', 'unauthorized', 'invalidparameter.invalidapikey')):
            category = 'authentication_rejected'
        elif '申请上传地址响应缺少 result' in text:
            category = 'upload_address_failed'
        elif 'task_id' in text and any(value in text for value in ('缺少', 'missing')):
            category = 'missing_task_id'
        elif http_status in (401, 403):
            category = 'authentication_rejected'
        elif http_status == 429 or any(value in text for value in ('too many requests', 'rate limit', '限流')):
            category = 'rate_limited'
        elif any(value in text for value in ('etimedout', 'timed out', 'timeout', '超时')):
            category = 'request_timeout'
        elif any(value in text for value in ('econnreset', 'econnrefused', 'enotfound', 'eai_again', 'network unreachable', 'connection reset')):
            category = 'network_error'
        elif http_status is not None and http_status >= 500:
            category = 'service_unavailable'
        else:
            category = 'cli_failed'
        self.diagnostic = {'category': category, 'exit_code': exit_code}
        # Upload-address acquisition precedes media upload and task creation. A
        # missing result is therefore replay-safe; genuinely ambiguous submit
        # failures remain fenced as submission_unknown.
        if not_submitted or category == 'upload_address_failed':
            self.diagnostic['submission_state'] = 'not_submitted'
        if http_status is not None:
            self.diagnostic['http_status'] = http_status
        super().__init__(f'mediakit command failed (exit {exit_code}; {category})')


def sync_credentials(store):
    """Called by a fresh host shell, never by the long-lived supervisor."""
    result = refresh(store.workspace_root)
    if not result['updated']:
        return {**result, 'requeued_segments': 0, 'asr_health': asr_health(store.segments(), store.task())}
    recovered = recover_credentials(store)
    # Preflight credential failures may precede any task-level block. An explicit
    # host refresh can requeue these too; they never invoked the submit command.
    with store.connection(True) as conn:
        for segment in store._segments(conn):
            if unsubmitted_auth_failure(segment):
                if store._update_segment(conn, segment['id'], asr_status='pending', asr_diagnostic=None):
                    recovered.append(segment['id'])
    return {**result, 'requeued_segments': len(recovered), 'asr_health': asr_health(store.segments(), store.task())}


def credentials_env(store):
    return environment(store.workspace_root)


def recover_credentials(store):
    """A new host credential allows another attempt only before task creation."""
    if not submissions_paused(store):
        return []
    try:
        version = credential_version(credentials_env(store))
    except (OSError, ValueError):
        return []
    recovered = []
    with store.connection(True) as conn:
        row = conn.execute('SELECT data FROM live_sessions WHERE id=?', (store.session_id,)).fetchone()
        data = json.loads(row[0])
        blocked = data.get('asr_credential_block')
        legacy_upload_block = blocked and blocked.get('category') == 'upload_address_failed'
        if not blocked or (blocked['version'] == version and not legacy_upload_block):
            return recovered
        for row in conn.execute('SELECT id,data FROM segments WHERE session_id=?', (store.session_id,)).fetchall():
            segment = json.loads(row['data'])
            if unsubmitted_auth_failure(segment):
                if store._update_segment(conn, row['id'], asr_status='pending', asr_diagnostic=None):
                    recovered.append(row['id'])
            if (segment.get('asr_task_id') and segment.get('asr_status') == 'timed_out'
                    and (segment.get('asr_diagnostic') or {}).get('category') in {'authentication_rejected', 'credentials_unavailable'}):
                store._update_segment(conn, row['id'], asr_status='pending', asr_diagnostic=None)
                recovered.append(row['id'])
        # _update_segment can update session revision; preserve those changes.
        data = json.loads(conn.execute('SELECT data FROM live_sessions WHERE id=?', (store.session_id,)).fetchone()[0])
        if legacy_upload_block:
            data['asr_cloud_failure'] = 'upload_address_failed'
        data.pop('asr_credential_block', None)
        conn.execute('UPDATE live_sessions SET data=? WHERE id=?', (json.dumps(data), store.session_id))
    return recovered


def unsubmitted_auth_failure(segment):
    # This fixed router error is emitted only before invoking the submit command.
    return (segment.get('asr_selection_reason') != 'cloud_unavailable_local'
            and segment.get('asr_status') == 'failed' and not segment.get('asr_task_id')
            and (segment.get('asr_diagnostic') or {}).get('category') == 'CLOUD_ASR_AUTH_UNAVAILABLE')


def submissions_paused(store):
    return bool(store.task().get('asr_credential_block'))


def request_credentials(store, segment, *, defer_failure=False):
    try:
        return credentials_env(store)
    except (OSError, ValueError):
        store.update_task(asr_credential_block={'version': 'unavailable', 'category': 'credentials_unavailable'})
        if segment.get('asr_task_id'):
            store.update_segment(segment['id'], _remote_asr=True, _defer_asr_failure=defer_failure,
                                 asr_status='timed_out', asr_diagnostic={'category': 'credentials_unavailable'})
        return None


def asr_health(segments, task=None):
    blocked = [s for s in segments if s.get('asr_status') == 'submission_unknown']
    # Old task databases may contain arbitrary diagnostics; never echo them.
    categories = sorted({category if isinstance(category, str) and category in DIAGNOSTIC_CATEGORIES else 'unknown_submission'
                         for s in blocked for category in [(s.get('asr_diagnostic') or {}).get('category')]})
    pause = (task or {}).get('asr_credential_block')
    return {'submissions_paused': bool(pause),
            'message': ({'upload_address_failed': '上传地址响应异常；恢复调度并核实未知提交，不能据此认定凭证失效',
                         'credentials_unavailable': '工作目录凭证缺失或不可读，请执行 refresh-credentials'}.get(
                             pause['category'], '鉴权失败，请更新登录凭证')) if pause else
                        '提交结果未知；resume 或刷新凭证不会重放。先核实远端任务，无法核实时保留语音证据缺口。' if blocked else None,
            'status': 'needs_attention' if blocked or pause else 'ok', 'blocked_segments': len(blocked),
            'categories': categories, 'automatic_replay_safe': False,
            'next_action': 'sync_host_credentials_and_reconcile_submissions' if pause and blocked else
                           'refresh-credentials' if pause else 'reconcile_submissions' if blocked else None}


def config(task, key, default):
    return task.get('runtime_binaries', {}).get(key, task.get('config', {}).get(key, task.get(key, default)))


def invoke(binary, args, timeout=60, env=None, store=None):
    """One invocation only; a failed submission must never be replayed implicitly."""
    from runtime.media import media_command
    if not any(flag in args for flag in ('--schema','--help','--version')):
        env={**(os.environ if env is None else env),'MEDIAKIT_SURFACE':'skill',
             'MEDIAKIT_RUNTIME':(env or os.environ).get('MEDIAKIT_RUNTIME') or 'unknown'}
    try:
        result = media_command([binary, *args], capture_output=True, text=True, timeout=timeout, env=env, store=store)
    except subprocess.TimeoutExpired:
        raise CommandFailure(None, category='request_timeout') from None
    except (FileNotFoundError, PermissionError):
        raise CommandFailure(None, category='cli_unavailable',not_submitted=True) from None
    except OSError:
        raise CommandFailure(None, category='cli_unavailable') from None
    if result.returncode:
        raise CommandFailure(result.returncode, result.stdout + '\n' + result.stderr)
    try:
        value = json.loads(result.stdout)
    except (ValueError, TypeError):
        raise CommandFailure(result.returncode, category='invalid_response') from None
    if isinstance(value, dict) and (value.get('error') or value.get('success') is False):
        raise CommandFailure(result.returncode, result.stdout)
    if not isinstance(value, dict):
        raise CommandFailure(result.returncode, category='invalid_response')
    return value


def doctor(workspace_root=None):
    """Independent read-only probes share a 10s subprocess deadline, not 6 x 10s.

    Never return raw stdout/stderr or environment values in diagnostic failures.
    """
    commands = {'ffmpeg': ['-version'], 'ffprobe': ['-version'],
                'mediakit-cli': ['--version']}
    paths = {name: shutil.which(name) for name in commands}

    def version(name):
        entry = {'available': bool(paths[name]), 'version': None, 'compatible': False}
        if not paths[name]:
            return entry
        try:
            p = subprocess.run([paths[name], *commands[name]], capture_output=True, text=True, timeout=10)
            line = p.stdout.splitlines()[0] if p.stdout.strip() else ''
            import re
            match = re.search(r'\bv?(\d+\.\d+(?:\.\d+)?)\b', line)
            entry['version'] = match.group(1) if match else None
            entry['compatible'] = p.returncode == 0 and bool(match)
        except (OSError, subprocess.SubprocessError):
            pass
        return entry

    def schema(command, fields):
        if not paths['mediakit-cli']:
            return False
        try:
            value = invoke(paths['mediakit-cli'], [*command, '--schema'], timeout=10)
            return any(field in json.dumps(value).lower() for field in fields)
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError):
            return False

    with ThreadPoolExecutor(max_workers=6) as pool:
        version_jobs = {name: pool.submit(version, name) for name in commands}
        schema_jobs = {
            'asr': pool.submit(schema, ['video', 'asr-subtitles'], ('audio-url', 'audio_url')),
            'query': pool.submit(schema, ['shared', 'query-task'], ('task-id', 'task_id')),
        }
        checks = {name: job.result() for name, job in version_jobs.items()}
        schemas = {name: job.result() for name, job in schema_jobs.items()}
    credential_error = None
    try:
        values = environment(workspace_root) if workspace_root is not None else os.environ
    except (OSError, ValueError):
        values = {}
        credential_error = True
    env_present = {key: bool(values.get(key)) for key in ENV_KEYS}
    issues = []
    for name, check in checks.items():
        if not check['compatible']:
            issues.append({'code': 'BINARY_CHECK_FAILED' if check['available'] else 'MISSING_BINARY',
                           'dependency': name,
                           'message': '版本探测失败、超时或版本不兼容' if check['available'] else '当前执行环境的 PATH 中未找到依赖',
                           'action': '在豆包工作宿主中提供 mediakit-cli-doubao，并确认执行工具继承 PATH；不要安装同名 npm 包。'
                           if name == 'mediakit-cli' else '确认当前执行环境已安装 ' + name + ' 且 PATH 可见。'})
    if paths['mediakit-cli']:
        for name, passed in schemas.items():
            if not passed:
                issues.append({'code': 'SCHEMA_CHECK_FAILED', 'dependency': name,
                               'message': '接口 schema 探测失败、超时或缺少所需参数',
                               'action': '核对宿主 mediakit-cli-doubao 0.2.1 接口及命令错误；仅提供脱敏错误，不提供凭据。'})
    for name, present in env_present.items():
        if not present:
            issues.append({'code': 'WORKSPACE_CREDENTIALS_UNAVAILABLE' if credential_error else 'MISSING_HOST_ENV', 'dependency': name,
                           'message': '工作目录凭证缺失或不可读' if credential_error else '当前执行进程未继承该宿主环境变量',
                           'action': '在豆包工作中执行并继承宿主环境；已有任务可执行 refresh-credentials --task-dir <任务目录>。不要在对话中粘贴变量值。'})
    ready = not issues
    return {'ok': ready, 'ready': ready, 'binaries': checks, 'schemas': schemas,
            'environment': env_present, 'contract_version': '0.2.1', 'issues': issues}


def normalize_subtitles(result, segment):
    output = []
    items = result.get('subtitles')
    if not isinstance(items, list):
        raise ValueError('Completed ASR must include subtitles array')
    for i, item in enumerate(items):
        if not isinstance(item, dict) or not isinstance(item.get('subtitle_text'), str):
            raise ValueError('Invalid subtitle object')
        a, b = float(item['start_time']), float(item['end_time'])
        if not math.isfinite(a) or not math.isfinite(b) or a < 0 or b < a:
            raise ValueError('Invalid subtitle timing')
        start = segment['start_ms'] + round(a * 1000)
        end = min(segment['end_ms'], segment['start_ms'] + round(b * 1000))
        if start > end:
            raise ValueError('Subtitle outside segment')
        output.append({'id': f"asr-{segment['id']}-{i}", 'text': str(item['subtitle_text']),
                       'start_ms': start, 'end_ms': end})
    return output


def reconcile_submission(store, request):
    """Import a verified existing remote result; never create an ASR task.

    The caller must establish the ID/audio association outside this command:
    query-task does not provide an audio fingerprint to verify it automatically.
    """
    from runtime.finishing import closed
    task = store.task()
    sid, remote_id = request.get('segment_id'), request.get('remote_task_id')
    if (request.get('task_id') != store.task_id or request.get('confirmed_same_audio') is not True
            or type(sid) is not int or sid <= 0 or not isinstance(remote_id, str)
            or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,199}', remote_id)
            or task.get('asr_policy') == 'local_only'):
        raise ValueError('invalid ASR reconciliation')
    if closed(store.finish_tick()):
        return {'status': 'inspection_finished', 'next_action': 'report'}
    segments = store.segments()
    segment = next((s for s in segments if s['id'] == sid), None)
    if segment and segment.get('asr_selection_reason') == 'cloud_unavailable_local':
        return {'status': 'local_takeover', 'segment_id': sid}
    if segment and segment.get('asr_status') == 'success' and segment.get('asr_task_id') == remote_id:
        return {'status': 'already_reconciled', 'segment_id': sid}
    if (not segment or segment.get('asr_status') != 'submission_unknown' or segment.get('asr_task_id')
            or not segment.get('audio_file') or not segment.get('asr_diagnostic')
            or any(s['id'] != sid and s.get('asr_task_id') == remote_id for s in segments)):
        raise ValueError('invalid ASR reconciliation')
    try:
        env = credentials_env(store)
    except (OSError, ValueError):
        return {'status': 'credentials_unavailable', 'next_action': 'refresh-credentials'}
    try:
        result = invoke(config(task, 'mediakit_bin', 'mediakit-cli'),
                        ['shared', 'query-task', '--task-id', remote_id], env=env, store=store)
    except CommandFailure as error:
        return {'status': 'query_failed', 'diagnostic': {**error.diagnostic, 'stage': 'query',
                                                       'credential_source': 'workspace'}}
    state = str(result.get('status', '')).lower()
    if state not in ('completed', 'failed', 'canceled', 'cancelled', 'pending', 'queued', 'running', 'processing', 'submitted'):
        return {'status': 'query_failed', 'diagnostic': {'category': 'invalid_response', 'stage': 'query'}}
    if state != 'completed':
        return {'status': 'remote_failed' if state in ('failed', 'canceled', 'cancelled') else 'remote_pending',
                'segment_id': sid}
    subtitles = normalize_subtitles(result, segment)
    with store.connection(True) as conn:
        # The read-only query runs outside SQLite; reject concurrent evidence changes.
        current = store._segments(conn)
        if (next((s for s in current if s['id'] == sid), None) != segment
                or any(s['id'] != sid and s.get('asr_task_id') == remote_id for s in current)):
            raise ValueError('evidence changed; read segment again')
        # Confirmed results recover only missing intervals for the full live policy.
        fields={'asr_status':'success','asr_task_id':remote_id,'asr_backend':'mediakit','asr_diagnostic':None,'subtitles':subtitles}
        from runtime.full_live import enabled as full
        if full(task) and segment.get('speech_gaps'):
            from runtime.full_asr import merge
            fields['subtitles'],fields['speech_gaps']=merge(segment.get('subtitles',[]),subtitles,segment['speech_gaps'],segment)
            if fields['speech_gaps']:fields.update(asr_status='failed',asr_diagnostic={'category':'ASR_EMPTY_SPEECH'})
        elif full(task) and not subtitles and segment.get('subtitles'):
            fields['subtitles']=segment['subtitles']
        if not store._update_segment(conn, sid, invalidate_review=True, **fields):
            return {'status': 'inspection_finished', 'next_action': 'report'}
    store.log('asr_reconciled', 'Verified existing ASR result restored; no submission replayed', sid)
    return {'status': 'reconciled', 'segment_id': sid, 'next_action': 'review-next'}


def process_asr(store, segment, *, poll_seconds=3, clock=None, sleep=time.sleep, cancel=None, defer_failure=False):
    """Persist unknown BEFORE submit, ID BEFORE query. Timeout IDs are resumable.

    The owner maintains worker heartbeat independently while this function waits.
    stop_requested intentionally does not cancel already acquired media.
    """
    from runtime.local_asr import MediaCancellation
    from runtime.live_backlog import Cancellation, enabled, remaining as media_remaining
    if enabled(store.task()):cancel=Cancellation(store,cancel,segment['id'])
    cancellation=MediaCancellation(store,cancel)
    if cancellation.is_set():return
    segment = next(s for s in store.segments() if s['id'] == segment['id'])
    if segment.get('review_status')=='skipped' or segment.get('asr_selection_reason') == 'cloud_unavailable_local': return
    status = segment.get('asr_status', 'pending')
    if status in ('success', 'failed', 'no_audio', 'submission_unknown'):
        return
    task = store.task()
    binary = config(task, 'mediakit_bin', 'mediakit-cli')
    v2=task.get('pipeline_version')==2
    current_live=task.get('inspection_policy')=='lite_live_realtime_v2'
    if clock is None:clock=time.time if task.get('asr_policy')=='remote_first' or current_live else time.monotonic
    budget = 600 if current_live else 60 if v2 else max(0, float(config(task, 'asr_timeout_seconds', 600)))
    deadline=clock()+budget
    if task.get('asr_policy')=='remote_first' or current_live:
        deadline=segment.get('asr_cloud_deadline_at',deadline)
        if 'asr_cloud_deadline_at' not in segment:
            if not store.update_segment(segment['id'],asr_cloud_deadline_at=deadline):return
        deadline=min(deadline,task.get('finishing',{}).get('media_deadline_at',float('inf')))
    task_id = segment.get('asr_task_id')
    def update(**fields):
        return store.update_segment(segment['id'], _remote_asr=True,
                                    _defer_asr_failure=defer_failure, **fields)
    if submissions_paused(store):
        return
    if (task.get('asr_policy')=='remote_first' or current_live) and clock()>=deadline:
        update(asr_status='timed_out')
        return
    if not task_id:
        if not segment.get('audio_file'):
            return
        env = request_credentials(store, segment, defer_failure=defer_failure)
        if env is None or cancellation.is_set():
            return
        # A marker without a diagnostic may still be in flight; reconciliation
        # requires a settled submission failure and must not race this invocation.
        if not update(asr_status='submission_unknown', asr_diagnostic=None,
                      asr_cloud_attempts=segment.get('asr_cloud_attempts',0)+1): return
        try:
            if cancellation.is_set():return
            attempts=segment.get('asr_submit_attempts',0)
            # Retry only failures proven to happen before remote task creation.
            # Live stays remote-first without risking duplicate submissions.
            limit=3
            while True:
                if attempts>=limit:
                    raise CommandFailure(None,category='cli_unavailable',not_submitted=True)
                attempts+=1
                if not update(asr_submit_attempts=attempts):return
                try:
                    result = invoke(binary, ['video', 'asr-subtitles', '--audio-url',
                                              str(store.root / segment['audio_file'])], env=env, store=store, timeout=max(.001,min(deadline-clock(),media_remaining(store.task(), 15 if v2 else 60))))
                    break
                except CommandFailure as failure:
                    if failure.diagnostic.get('submission_state')!='not_submitted' or attempts>=limit:
                        raise
                    if cancellation.is_set() or clock()>=deadline:return
                    sleep((2,10)[attempts-1])
                    if cancellation.is_set():return
            task_id = result.get('task_id')
            if isinstance(task_id, bool) or not isinstance(task_id, (str, int)) or not str(task_id).strip():
                raise CommandFailure(0, category='missing_task_id')
            task_id = str(task_id)
            if not update(asr_status='submitted', asr_task_id=task_id): return
            store.update_task(asr_cloud_failure=None)
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
            if cancellation.is_set():return
            # Error type is useful without recording subprocess arguments, URLs,
            # stderr or credentials. Unknown submissions must still not replay.
            diagnostic = {**getattr(error, 'diagnostic', {'category': type(error).__name__}),
                          'stage': 'submit', 'credential_source': 'workspace'}
            store.update_task(asr_cloud_failure=diagnostic['category'])
            if diagnostic.get('category') == 'authentication_rejected':
                store.update_task(asr_credential_block={'version': credential_version(env), 'category': diagnostic['category']})
            if diagnostic.get('submission_state')=='not_submitted':
                update(asr_status='failed',asr_diagnostic=diagnostic)
                store.log('asr_submit_failed', 'ASR submit failed before remote task creation; safe retries exhausted', segment['id'])
                return
            update(asr_diagnostic=diagnostic)
            store.log('asr_submission_unknown', 'Submission outcome unknown: ' + json.dumps(diagnostic) + '; automatic replay disabled', segment['id'])
            return
    else:
        update(asr_status='submitted')
    if not v2:deadline = clock() + budget
    while clock() < deadline:
        current=next(s for s in store.segments() if s['id']==segment['id'])
        if current.get('asr_selection_reason')=='cloud_unavailable_local': return
        if cancellation.is_set():return
        # Video user-stop retains its bounded local recovery policy.
        if v2 and task.get('kind','live')!='live' and store.should_stop():
            update(asr_status='timed_out')
            return
        try:
            env = request_credentials(store, {**segment, 'asr_task_id': task_id}, defer_failure=defer_failure)
            if env is None or cancellation.is_set():
                return
            result = invoke(binary, ['shared', 'query-task', '--task-id', task_id],
                            timeout=max(.001,media_remaining(store.task(), min(5 if v2 else 60, deadline-clock()))), env=env, store=store)
            if cancellation.is_set():return
            state = str(result.get('status', '')).lower()
            if state == 'completed':
                subtitles = normalize_subtitles(result, segment)
                update(asr_status='success', subtitles=subtitles, asr_diagnostic=None)
                return
            if state in ('failed', 'canceled', 'cancelled'):
                update(asr_status='failed', asr_outcome=state)
                store.log('asr_' + state, 'ASR task ' + state, segment['id'])
                return
        except (OSError, ValueError, KeyError, TypeError, RuntimeError, subprocess.SubprocessError) as error:
            if cancellation.is_set():return
            diagnostic = getattr(error, 'diagnostic', {})
            if diagnostic.get('category') == 'authentication_rejected':
                store.update_task(asr_credential_block={'version': credential_version(env), 'category': 'authentication_rejected'})
                update(asr_status='timed_out', asr_diagnostic=diagnostic)
                return
            # Queries are read-only and safe to retry against the same stored task ID.
            store.log('asr_query_retry', 'ASR query unavailable or malformed', segment['id'])
        remaining = deadline - clock()
        if remaining > 0:
            if cancel is not None:
                cancel.wait(min(poll_seconds, remaining))
            else:
                sleep(min(poll_seconds, remaining))
    if cancellation.is_set():return
    update(asr_status='timed_out')
    store.log('asr_timed_out', 'ASR wait expired; saved task ID can be resumed', segment['id'])
