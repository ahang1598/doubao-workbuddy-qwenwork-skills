"""Local CLI boundary diagnostics; never capture media, auth or raw output."""
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess


PATCH_VERSION = 'cli-boundary-v2'


@lru_cache(maxsize=16)
def _identity(path, size, modified):
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    # Version discovery must not inherit host credentials or invoke a shell.
    env = {k: os.environ[k] for k in ('PATH', 'SystemRoot', 'WINDIR') if k in os.environ}
    version = None
    try:
        result = subprocess.run([path, '--version'], capture_output=True, text=True,
                                timeout=2, env=env)
        match = re.fullmatch(r'mediakit-cli(?: version)? (\d+\.\d+\.\d+(?:[-+][A-Za-z0-9.-]{1,48})?)\s*', result.stdout)
        if result.returncode == 0 and match:
            version = match[1]
    except (OSError, subprocess.TimeoutExpired, UnicodeError):
        pass
    return {'cli_sha256': digest.hexdigest(), 'cli_version': version}


def identity(binary):
    try:
        resolved = shutil.which(str(binary))
        if not resolved:
            return {'cli_identity_status': 'unavailable'}
        path = Path(resolved).resolve()
        stat = path.stat()
        return {**_identity(str(path), stat.st_size, stat.st_mtime_ns), 'cli_identity_status': 'available'}
    except OSError:
        return {'cli_identity_status': 'unavailable'}


def output_shape(output):
    """Describe the CLI envelope only, not the discarded upstream HTTP body."""
    if isinstance(output, bytes):
        output = output.decode('utf-8', errors='replace')
    output = output or ''
    shape = {'bytes': len(output.encode('utf-8'))}
    try:
        value = json.loads(output)
    except (ValueError, TypeError):
        return {**shape, 'json_type': 'invalid' if output.strip() else 'empty'}
    kind = ('object' if isinstance(value, dict) else 'array' if isinstance(value, list)
            else 'null' if value is None else 'scalar')
    shape['json_type'] = kind
    if isinstance(value, dict):
        shape['has_task_id'] = bool(value.get('task_id'))
        shape['has_error'] = bool(value.get('error'))
        shape['has_result'] = 'result' in value
    return shape


def upstream_events(output, env):
    """Accept only the opt-in upstream patch's fixed diagnostic schema."""
    from .mediakit import CommandFailure
    events = []
    for line in (output or '').splitlines():
        try:
            value = json.loads(line)
        except ValueError:
            continue
        if not isinstance(value, dict) or value.get('mediakit_diagnostic') != 'upload-v1':
            continue
        if value.get('stage') not in {'upload_address', 'upload_cache'}:
            continue
        event = {'stage': value['stage']}
        # Reuse credential redaction and scalar validation, including on success.
        detail = CommandFailure(0, line, env=env).diagnostic
        for key in ('http_status', 'error_code', 'request_id', 'log_id'):
            if key in detail:
                event[key] = detail[key]
        for key, allowed in {
            'result_kind': {'missing', 'null', 'object', 'wrong_type', 'empty_body', 'invalid_json'},
            'cache_status': {'hit', 'miss', 'read_error'},
            'cache_reason': {'absent', 'scope_changed', 'file_changed', 'missing_file_id', 'expired_or_invalid_expiry'},
        }.items():
            if isinstance(value.get(key), str) and value[key] in allowed:
                event[key] = value[key]
        events.append(event)
        if len(events) == 16:
            break
    return events


def record(store, *, cli, command, segment_id, elapsed_ms, trace, diagnostic=None):
    """Best effort: a logging failure must never turn a submit into a retry."""
    if store is None or command not in {'asr_submit', 'query_task'}:
        return
    if command == 'query_task' and diagnostic is None:
        return  # Successful polling remains in the existing task lifecycle logs.
    payload = {'patch_version': PATCH_VERSION, 'scope': 'cli_boundary',
               'command': command, 'elapsed_ms': elapsed_ms, **cli, **trace,
               'outcome': 'failed' if diagnostic is not None else 'returned'}
    if diagnostic is not None:
        payload['diagnostic'] = diagnostic
        payload['missing_upstream_fields'] = [k for k in ('http_status', 'error_code', 'request_id', 'log_id')
                                              if k not in diagnostic]
    try:
        store.log('mediakit_cli_diagnostic', json.dumps(payload, ensure_ascii=False), segment_id)
    except Exception:
        pass
