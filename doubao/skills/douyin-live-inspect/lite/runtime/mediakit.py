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
import uuid

from .credentials import ENV_KEYS, BACKGROUND_SECRET_KEYS, environment, refresh, version as credential_version
from runtime.credential_worker import eligible as credential_worker_eligible

DIAGNOSTIC_CATEGORIES = frozenset({
    'upload_address_failed', 'authentication_rejected', 'missing_task_id',
    'rate_limited', 'request_timeout', 'network_error', 'service_unavailable',
    'cli_failed', 'cli_unavailable', 'invalid_response', 'credentials_unavailable',
})
HOST_REFRESH_CATEGORIES = frozenset({'authentication_rejected', 'credentials_unavailable', 'upload_address_failed'})
HOST_REFRESH_WAIT_SECONDS = 30


def format_unsupported(value, depth=0):
    """Only explicit structured decoder codes warrant changing the media input."""
    if depth>=4 or not isinstance(value,dict):return False
    codes={'unsupported_container','unsupported_codec','unsupported_format','decode_error','decode_failed'}
    for key in ('code','error_code'):
        code=value.get(key)
        if isinstance(code,str) and code.lower() in codes:return True
    return any(format_unsupported(value.get(key),depth+1) for key in ('error','result','data'))


def failure_metadata(output):
    """Extract bounded diagnostic scalars, never messages, URLs or credentials."""
    detail = {}
    def visit(value, depth=0, error=False):
        if depth > 4 or not isinstance(value, dict):return
        for key, item in value.items():
            name = key.lower().replace('_', '').replace('-', '')
            if name in {'httpstatus', 'statuscode'} and not isinstance(item, bool):
                if re.fullmatch(r'[1-5]\d\d', str(item)):
                    detail.setdefault('http_status', int(item))
            elif name in {'code', 'errorcode', 'requestid', 'xrequestid', 'logid', 'xttlogid'}:
                field = ('error_code' if name in {'code', 'errorcode'} else
                         'log_id' if name in {'logid', 'xttlogid'} else 'request_id')
                pattern = r'(?:[A-Za-z][A-Za-z0-9_.-]{0,63}|\d{1,12})' if field == 'error_code' else r'[A-Za-z0-9][A-Za-z0-9_-]{7,127}'
                if isinstance(item, (str, int)) and not isinstance(item, bool) and re.fullmatch(pattern, str(item)):
                    # JWTs and common credential prefixes are never diagnostic IDs.
                    if not str(item).lower().startswith(('eyj', 'bearer', 'sk-', 'sk_')):
                        if field == 'error_code' and error:detail[field] = str(item)
                        else:detail.setdefault(field, str(item))
            elif name in {'error', 'response', 'responsemetadata', 'result', 'data', 'body', 'headers'}:
                visit(item, depth + 1, error or name == 'error')
    decoder = json.JSONDecoder()
    try:
        visit(json.loads(output))
    except (ValueError, TypeError):
        # CLI stderr can prefix a JSON error with a log label or mix JSON lines.
        for match in re.finditer(r'(?m)^[^\n{]*\{', output):
            try:visit(decoder.raw_decode(output[match.end()-1:])[0])
            except ValueError:pass
    for key, value in re.findall(r'(?im)^\s*(request[_-]?id|log[_-]?id|x-request-id|x-tt-logid|error[_-]?code|http[_-]?status|status[_-]?code)\s*[:=]\s*([^\s]+)[ \t]*$', output):
        visit({key:value})
    return detail


class CommandFailure(RuntimeError):
    def __init__(self, exit_code, output='', *, category=None, not_submitted=False, env=None):
        # Remove known host credentials before extracting any diagnostic fields.
        for key, value in {**os.environ, **(env or {})}.items():
            if value and (key in BACKGROUND_SECRET_KEYS or key.startswith('BYTECLOUD_CLI_API_JWT_TOKEN')):
                output = output.replace(value, '[REDACTED]')
        metadata = failure_metadata(output)
        text = output.lower()
        status = re.search(r'(?:http(?:/\d(?:\.\d)?)?\s+|["\']?(?:http_status|status_code|statuscode|status code)["\']?\s*[:=]\s*)([45]\d\d)\b', text)
        http_status = metadata.get('http_status', int(status.group(1)) if status else None)
        code = metadata.get('error_code', '').lower()
        upload_address=('申请上传地址响应缺少 result' in text or category=='upload_address_failed'
                        or bool(re.search(r'"(?:stage|phase)"\s*:\s*"upload_address"',text)))
        expired=any(v in text for v in ('token expired','token has expired','tokenexpired','expiredtoken','凭证已过期'))
        if category is not None:
            category=category if category in DIAGNOSTIC_CATEGORIES else 'cli_failed'
        elif expired or http_status in (401,403) or code in {'authenticationerror', 'authenticationfailed', 'accessdenied'} or any(v in text for v in ('invalid token','unauthorized','invalidparameter.invalidapikey')):
            category='authentication_rejected'
        elif http_status==429 or code=='requestlimitexceeded' or any(v in text for v in ('too many requests','too_many_requests','toomanyrequests','rate limit','限流')):
            category='rate_limited'
        elif (http_status is not None and http_status>=500) or code in {'internalserviceerror', 'serviceinitializingerror'} or any(v in text for v in ('service_unavailable','serviceunavailable')):
            category='service_unavailable'
        elif any(v in text for v in ('etimedout','timed out','timeout','超时')):
            category='request_timeout'
        elif any(v in text for v in ('econnreset','econnrefused','enotfound','eai_again','network unreachable','connection reset')):
            category='network_error'
        elif upload_address:
            category='upload_address_failed'
        elif 'task_id' in text and any(v in text for v in ('缺少','missing')):
            category='missing_task_id'
        else:
            category='cli_failed'
        reason=('credential_expired' if category=='authentication_rejected' and expired else
                category if category in {'authentication_rejected','rate_limited','service_unavailable','request_timeout','network_error'} else
                'upload_response_missing' if upload_address else 'unknown')
        self.diagnostic={**metadata,'category':category,'reason':reason,'exit_code':exit_code,
                         'failure_stage':'upload_address' if upload_address else 'submit'}
        try:
            if format_unsupported(json.loads(output)):self.diagnostic['format_unsupported']=True
        except (ValueError,TypeError):pass
        # Phase and cause are independent: a 401/429/5xx at address acquisition
        # is still known not to have created a remote recognition task.
        if not_submitted or upload_address:self.diagnostic['submission_state']='not_submitted'
        if http_status is not None:self.diagnostic['http_status']=http_status
        super().__init__(f'mediakit command failed (exit {exit_code}; {category})')


def sync_credentials(store, *, refresh_id=None, refresh_cycle=None):
    """Called by a fresh host shell, never by the long-lived supervisor."""
    from runtime.credentials import status, read
    with store.connection(True) as conn:
        task = store._task(conn)
        request = task.get('asr_host_refresh') or {}
        if refresh_id and (request.get('request_id') != refresh_id or request.get('status') != 'pending'
                           or not credential_worker_eligible(task)
                           or (request.get('resident') and (refresh_cycle != request.get('cycle')
                               or request.get('worker_status') in {'unavailable','stopped'}))):
            return {'updated':False,'reason':'refresh_request_inactive','credential_changed':False}
        previous = status(store.workspace_root).get('version')
        try:previous_token=read(store.workspace_root)[ENV_KEYS[0]]
        except (OSError,ValueError):previous_token=None
        result = refresh(store.workspace_root)
        result['credential_changed'] = bool(result['updated'] and result.get('version') != previous)
        result['token_changed'] = bool(result['updated'] and os.environ.get(ENV_KEYS[0]) != previous_token)
        active = request.get('status') == 'pending' and credential_worker_eligible(task)
        if active:
            state = 'refreshed' if result['updated'] else 'missing'
            for segment in store._segments(conn):
                waiting = segment.get('asr_host_refresh') or {}
                if waiting.get('requested_at') == request['requested_at'] and waiting.get('status') == 'pending':
                    store._update_segment(conn, segment['id'], asr_host_refresh={**waiting,'status':state})
            task = store._task(conn)
            request={**request,'status':state}
            if request.get('resident'):
                from runtime.credential_worker import REFRESH_SECONDS, RECHECK_SECONDS
                request['next_refresh_at']=time.time()+(REFRESH_SECONDS if result['token_changed'] else RECHECK_SECONDS)
                if result['token_changed']:request['last_rotated_at']=time.time()
            task['asr_host_refresh'] = request
        task['asr_host_refresh_at'] = time.time()
        store._set_task(conn, task)
    recovered = recover_credentials(store, allow_same=active) if result['updated'] else []
    try:
        store.log('mediakit_credential_refresh', json.dumps({'phase':'imported' if result['updated'] else 'missing',
            'credential_changed':result['credential_changed'], 'token_changed':result['token_changed'], 'active_request':active, 'refresh_id':request.get('request_id'), 'cycle':request.get('cycle'),
            'trigger':request.get('trigger'), 'next_refresh_at':request.get('next_refresh_at')}))
    except Exception:pass
    if not result['updated']:
        return {**result, 'requeued_segments': 0, 'asr_health': asr_health(store.segments(), store.task())}
    # Preflight credential failures may precede any task-level block. An explicit
    # host refresh can requeue these too; they never invoked the submit command.
    with store.connection(True) as conn:
        for segment in store._segments(conn):
            if unsubmitted_auth_failure(segment):
                if store._update_segment(conn, segment['id'], asr_status='pending', asr_diagnostic=None):
                    recovered.append(segment['id'])
    return {**result, 'requeued_segments': len(recovered), 'asr_health': asr_health(store.segments(), store.task())}


def host_refresh_due(task):
    """Keep host delegation pending independently of a segment's wait budget."""
    if not credential_worker_eligible(task):
        return False
    request = task.get('asr_host_refresh')
    if request:
        return request['status'] == 'pending' or (request['status'] == 'timed_out' and not request.get('request_id'))
    category = (task.get('asr_credential_block') or {}).get('category') or task.get('asr_cloud_failure')
    # Older tasks may have a failure but no per-segment handshake yet.
    return category in HOST_REFRESH_CATEGORIES and not task.get('asr_host_refresh_at')


def refresh_after_failure(store, segment, category, *, cancel=None, remaining=30, sleep=time.sleep):
    """One bounded host import per segment; concurrent failures share the request."""
    if category not in HOST_REFRESH_CATEGORIES or remaining <= 0 or (cancel is not None and cancel.is_set()):return False
    sid = segment['id']
    with store.connection(True) as conn:
        task = store._task(conn)
        current = next(s for s in store._segments(conn) if s['id'] == sid)
        if (not credential_worker_eligible(task)
                or current.get('asr_host_refresh') or current.get('asr_final')
                or current.get('review_status') in {'done','skipped'}):return False
        request = task.get('asr_host_refresh') or {}
        if request.get('resident') and request.get('status') != 'pending':
            from runtime.credential_worker import begin_cycle
            request=begin_cycle(request,trigger='failure',now=time.time())
            request['category']=category
        elif request.get('status') != 'pending':
            request = {'status':'pending', 'request_id':uuid.uuid4().hex, 'requested_at':time.time(),
                       'deadline_at':time.time()+min(HOST_REFRESH_WAIT_SECONDS,remaining), 'category':category}
        if not store._update_segment(conn, sid, asr_host_refresh={
                'requested_at':request['requested_at'], 'status':'pending'}):return False
        task = store._task(conn)
        task['asr_host_refresh'] = request
        store._set_task(conn, task)
    try:store.log('mediakit_credential_refresh', json.dumps({'phase':'requested', 'category':category, 'refresh_id':request['request_id'], 'cycle':request.get('cycle'), 'trigger':'failure'}), sid)
    except Exception:pass
    deadline = time.time()+min(HOST_REFRESH_WAIT_SECONDS, remaining)
    while time.time() < deadline:
        if cancel is not None and cancel.is_set():return False
        task = store.task()
        if not credential_worker_eligible(task):return False
        latest = next(s for s in store.segments() if s['id'] == sid).get('asr_host_refresh') or {}
        if latest.get('status') != 'pending':
            return latest.get('status') == 'refreshed'
        sleep(min(.2, max(0,deadline-time.time())))
    with store.connection(True) as conn:
        current = next(s for s in store._segments(conn) if s['id'] == sid)
        latest = current.get('asr_host_refresh') or {}
        if latest.get('status') != 'pending':return latest.get('status') == 'refreshed'
        store._update_segment(conn, sid, asr_host_refresh={**latest, 'status':'timed_out'})
    try:store.log('mediakit_credential_refresh', json.dumps({'phase':'timed_out', 'category':category, 'refresh_id':request['request_id'], 'cycle':request.get('cycle')}), sid)
    except Exception:pass
    return False


def credentials_env(store):
    return environment(store.workspace_root)


def recover_credentials(store, *, allow_same=False):
    """Recover safe submissions/known queries; a host handshake allows one same-token probe."""
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
        if not blocked or (blocked['version'] == version and not legacy_upload_block and not allow_same):
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


def invoke(binary, args, timeout=60, env=None, store=None, segment_id=None):
    from . import mediakit_diagnostics as diagnostics
    command = ('asr_submit' if args[:2] == ['video', 'asr-subtitles'] else
               'query_task' if args[:2] == ['shared', 'query-task'] else 'other')
    trace = {}
    started = time.monotonic()
    failure = None
    try:
        return _invoke(binary, args, timeout=timeout, env=env, store=store, trace=trace)
    except CommandFailure as error:
        failure = {**error.diagnostic, 'failure_stage': 'query'} if command == 'query_task' else error.diagnostic
        raise
    finally:
        if store is not None and (command == 'asr_submit' or command == 'query_task' and failure is not None):
            elapsed_ms = round((time.monotonic() - started) * 1000)
            try:
                diagnostics.record(store, cli=diagnostics.identity(binary), command=command,
                                   segment_id=segment_id, elapsed_ms=elapsed_ms,
                                   trace=trace, diagnostic=failure)
            except Exception:
                pass  # Diagnostics never change submission outcome or retry policy.


def _invoke(binary, args, timeout=60, env=None, store=None, trace=None):
    """One invocation only; a failed submission must never be replayed implicitly."""
    from runtime.media import media_command
    if not any(flag in args for flag in ('--schema','--help','--version')):
        env={**(os.environ if env is None else env),'MEDIAKIT_SURFACE':'skill',
             'MEDIAKIT_RUNTIME':(env or os.environ).get('MEDIAKIT_RUNTIME') or 'unknown',
             'MEDIAKIT_DIAGNOSTICS':'1'}
    try:
        result = media_command([binary, *args], capture_output=True, text=True, timeout=timeout, env=env, store=store)
    except subprocess.TimeoutExpired as error:
        if trace is not None:
            try:
                from .mediakit_diagnostics import output_shape
                trace.update(stdout=output_shape(error.stdout), stderr=output_shape(error.stderr), exit_code=None)
            except Exception:
                pass
        partial = [part.decode('utf-8', errors='replace') if isinstance(part, bytes) else part or ''
                   for part in (error.stdout, error.stderr)]
        raise CommandFailure(None, '\n'.join(partial), category='request_timeout', env=env) from None
    except (FileNotFoundError, PermissionError):
        raise CommandFailure(None, category='cli_unavailable',not_submitted=True) from None
    except OSError:
        raise CommandFailure(None, category='cli_unavailable') from None
    if trace is not None:
        try:
            from .mediakit_diagnostics import output_shape, upstream_events
            trace.update(stdout=output_shape(result.stdout), stderr=output_shape(result.stderr), exit_code=result.returncode)
            events = upstream_events(result.stderr, env)
            if events:
                trace['upstream_events'] = events
        except Exception:
            pass
    if result.returncode:
        raise CommandFailure(result.returncode, result.stdout + '\n' + result.stderr, env=env)
    try:
        value = json.loads(result.stdout)
    except (ValueError, TypeError):
        raise CommandFailure(result.returncode, result.stdout + '\n' + result.stderr, category='invalid_response', env=env) from None
    if isinstance(value,dict) and value.get('status')=='failed' and format_unsupported(value):return value
    if isinstance(value, dict) and (value.get('error') or value.get('success') is False):
        raise CommandFailure(result.returncode, result.stdout + '\n' + result.stderr, env=env)
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
                        ['shared', 'query-task', '--task-id', remote_id], env=env, store=store, segment_id=sid)
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
    env = {}
    def observe(phase,outcome,attempt,diagnostic=None):
        try:
            from runtime.bridge import emit,safe_failure
            selection=segment.get('remote_asr_selection') or {}
            change=selection.get('credential_change','unknown')
            if phase != 'query' and selection.get('credential_version') and credential_version(env)!=selection['credential_version']:
                change='rotated'
            emit(task,phase=phase,outcome=outcome,segment_id=segment['id'],attempt=attempt,
                 route_generation=selection.get('generation',0),backend='mediakit',
                 route_reason=selection.get('route_reason','unknown'),
                 credential_change=change,
                 **safe_failure(diagnostic or {}))
        except Exception:pass
    def update(**fields):
        return store.update_segment(segment['id'], _remote_asr=True,
                                    _defer_asr_failure=defer_failure, **fields)
    def refresh_env(category):
        if refresh_after_failure(store, segment, category, cancel=cancellation,
                                 remaining=deadline-clock(), sleep=sleep):
            return request_credentials(store, {**segment, 'asr_task_id':task_id}, defer_failure=defer_failure)
        return None
    if submissions_paused(store):
        if refresh_env((store.task().get('asr_credential_block') or {}).get('category')) is None:return
    if (task.get('asr_policy')=='remote_first' or current_live) and clock()>=deadline:
        if update(asr_status='timed_out') and task_id:
            observe('query','failed',0,{'query_status':'timed_out','failure_stage':'query'})
        return
    if not task_id:
        if not segment.get('audio_file'):
            return
        # Limit FLV uploads, not the potentially long remote recognition wait.
        slots = getattr(store, 'asr_upload_slots', None) if Path(segment['audio_file']).suffix.lower() == '.flv' else None
        if slots is not None:
            while not slots.acquire(timeout=.1):
                if cancellation.is_set():return
                if clock() >= deadline:
                    update(asr_status='timed_out')
                    return
        try:
            # Authentication may change while this upload waits for a slot.
            if cancellation.is_set() or submissions_paused(store):return
            media_path = store.local_path(segment['audio_file'])
            media_flag = '--audio-url'
            if media_path.suffix.lower() == '.flv':
                from runtime.flv import black_video
                try:
                    media_path = black_video(media_path, store.root / 'audio' / f"asr-{segment['id']}.flv")
                except (OSError, ValueError):
                    update(asr_status='failed', asr_diagnostic={'category':'ASR_RECOVERY_FAILED',
                        'stage':'prepare', 'submission_state':'not_submitted'})
                    store.log('asr_prepare_failed', 'ASR black video preparation failed before any cloud call', segment['id'])
                    return
                media_flag = '--video-url'
            if cancellation.is_set():return
            env = request_credentials(store, segment, defer_failure=defer_failure)
            if env is None:env = refresh_env('credentials_unavailable')
            if env is None or cancellation.is_set():return
            # Waiting for an upload slot must not look like an unknown submission.
            if clock() >= deadline:
                update(asr_status='timed_out')
                return
            if not update(asr_status='submission_unknown', asr_diagnostic=None,
                          asr_cloud_attempts=segment.get('asr_cloud_attempts',0)+1): return
            if cancellation.is_set():return
            attempts=segment.get('asr_submit_attempts',0)
            # Retry only failures proven to happen before remote task creation.
            # Live stays remote-first without risking duplicate submissions.
            limit=segment.get('flv_format_submit_limit',3)
            while True:
                if attempts>=limit:
                    raise CommandFailure(None,category='cli_unavailable',not_submitted=True)
                attempts+=1
                if not update(asr_submit_attempts=attempts,asr_status='submission_unknown',asr_diagnostic=None):return
                try:
                    observe('attempt','started',attempts)
                    result = invoke(binary, ['video', 'asr-subtitles', media_flag,
                                              str(media_path)], env=env, store=store, segment_id=segment['id'], timeout=max(.001,min(deadline-clock(),media_remaining(store.task(), 15 if v2 else 60))))
                    remote_id=result.get('task_id')
                    if isinstance(remote_id,bool) or not isinstance(remote_id,(str,int)) or not str(remote_id).strip():
                        raise CommandFailure(0,json.dumps(result),category='missing_task_id',env=env)
                    observe('result','success',attempts,{'submission_state':'submitted'})
                    break
                except CommandFailure as failure:
                    observe('result','failed',attempts,failure.diagnostic)
                    # Refresh even an ambiguous auth error, but never replay an unknown submission.
                    refreshed = refresh_env(failure.diagnostic.get('category'))
                    if (refreshed is not None and failure.diagnostic.get('submission_state')=='not_submitted'
                            and attempts<limit and clock()<deadline and not cancellation.is_set()):
                        env = refreshed
                        continue
                    if (failure.diagnostic.get('submission_state')!='not_submitted' or attempts>=limit
                            or failure.diagnostic.get('category') in HOST_REFRESH_CATEGORIES
                            or (task.get('kind','live')=='live' and (task.get('asr_policy')=='remote_first' or current_live)
                                and failure.diagnostic.get('failure_stage')=='upload_address')
                            ):
                        raise
                    # The failed call is known not to have created a remote
                    # task. Persist that fact before waiting or being stopped.
                    if not update(asr_status='pending',asr_remote_status='pending',asr_diagnostic={**failure.diagnostic,
                            'stage':'submit','credential_source':'workspace'}):return
                    delay=min((2,10)[min(attempts-1,1)],max(0,deadline-clock()))
                    # Small slices keep injected test clocks and real cancellation
                    # responsive without extending the original segment deadline.
                    while delay>0:
                        if cancellation.is_set():return
                        left=deadline-clock()
                        if left<=0:raise failure
                        step=min(.2,delay,left)
                        sleep(step)
                        delay-=step
                    if cancellation.is_set():return
                    if clock()>=deadline:raise failure
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
                store.log('asr_submit_failed', 'ASR submit failed before remote task creation: ' + json.dumps(diagnostic), segment['id'])
                return
            update(asr_diagnostic=diagnostic)
            store.log('asr_submission_unknown', 'Submission outcome unknown: ' + json.dumps(diagnostic) + '; automatic replay disabled', segment['id'])
            return
        finally:
            if slots is not None:slots.release()
    else:
        update(asr_status='submitted')
    if not v2:deadline = clock() + budget
    last_query_failure = {}
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
            if env is None:
                env = refresh_env('credentials_unavailable')
                if env is not None:update(asr_status='submitted')
            if env is None or cancellation.is_set():
                return
            result = invoke(binary, ['shared', 'query-task', '--task-id', task_id],
                            timeout=max(.001,media_remaining(store.task(), min(5 if v2 else 60, deadline-clock()))), env=env, store=store, segment_id=segment['id'])
            if cancellation.is_set():return
            state = str(result.get('status', '')).lower()
            if state == 'completed':
                subtitles = normalize_subtitles(result, segment)
                if update(asr_status='success', subtitles=subtitles, asr_diagnostic=None):
                    observe('query','success',0,{'query_status':'completed','subtitle_count':len(subtitles)})
                return
            if state in ('failed', 'canceled', 'cancelled'):
                diagnostic = {**CommandFailure(0,json.dumps(result),env=env).diagnostic,
                              'stage':'query','failure_stage':'query'}
                if update(asr_status='failed', asr_outcome=state,
                          asr_diagnostic=diagnostic,
                          asr_format_unsupported=state=='failed' and format_unsupported(result)):
                    observe('query','failed',0,{**diagnostic,'query_status':'failed' if state=='failed' else 'cancelled'})
                    store.log('asr_' + state, 'ASR task ' + state + ': ' + json.dumps(diagnostic), segment['id'])
                return
        except (OSError, ValueError, KeyError, TypeError, RuntimeError, subprocess.SubprocessError) as error:
            if cancellation.is_set():return
            diagnostic = {**getattr(error, 'diagnostic', {}), 'stage':'query', 'failure_stage':'query'}
            last_query_failure = diagnostic
            update(asr_diagnostic=diagnostic)
            if refresh_env(diagnostic.get('category')) is not None:
                update(asr_status='submitted')
                continue
            if diagnostic.get('category') in HOST_REFRESH_CATEGORIES:
                if diagnostic['category'] in {'authentication_rejected','credentials_unavailable'}:
                    store.update_task(asr_credential_block={'version': credential_version(env), 'category': diagnostic['category']})
                if update(asr_status='timed_out', asr_diagnostic=diagnostic):
                    observe('query','failed',0,{**last_query_failure,'query_status':
                        'authentication_rejected' if diagnostic['category']=='authentication_rejected' else 'failed'})
                    store.log('asr_query_failed', 'ASR query failed: ' + json.dumps(diagnostic), segment['id'])
                return
            # Queries are read-only and safe to retry against the same stored task ID.
            store.log('asr_query_retry', 'ASR query unavailable or malformed: ' + json.dumps(diagnostic), segment['id'])
        remaining = deadline - clock()
        if remaining > 0:
            if cancel is not None:
                cancel.wait(min(poll_seconds, remaining))
            else:
                sleep(min(poll_seconds, remaining))
    if cancellation.is_set():return
    if update(asr_status='timed_out', asr_diagnostic=last_query_failure or {'stage':'query','failure_stage':'query','category':'request_timeout'}):
        observe('query','failed',0,{**last_query_failure,'query_status':'timed_out','failure_stage':'query'})
    store.log('asr_timed_out', 'ASR wait expired; saved task ID can be resumed: ' + json.dumps(last_query_failure), segment['id'])
