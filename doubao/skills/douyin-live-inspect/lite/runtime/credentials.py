# Adapted from skills_live_inspect_lite/runtime/credentials.py; content-only migration.
"""Workspace-scoped mediakit credentials; host environments are import-only."""
from runtime.platform_support import fcntl, nofollow_open, private_directory, private_file
import hashlib
import json
import os
from pathlib import Path
import stat

ENV_KEYS = ('DOUBAO_OFFICE_USER_ACCESS_TOKEN', 'DOUBAO_OFFICE_PLATFORM_APP_ID',
            'DOUBAO_OFFICE_AGENT_NAME')
BACKGROUND_SECRET_KEYS = frozenset((*ENV_KEYS, 'DOUBAO_OFFICE_BYTEDANCE_USER_ACCESS_TOKEN'))
FILENAME = '.mediakit-credentials.json'


def background_env():
    return {k: v for k, v in os.environ.items()
            if k not in {'INSPECT_TELEMETRY_METADATA_FILE', 'INSPECT_TELEMETRY_FD'} and k not in BACKGROUND_SECRET_KEYS and not k.startswith('BYTECLOUD_CLI_API_JWT_TOKEN')}


def read(workspace_root):
    path = Path(workspace_root) / FILENAME
    try:
        fd = nofollow_open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0))
    except FileNotFoundError:
        raise FileNotFoundError('Workspace credentials missing; run refresh-credentials --task-dir <directory>') from None
    with os.fdopen(fd) as handle:
        info = os.fstat(handle.fileno())
        if not private_file(info):
            raise ValueError('Unsafe credential file permissions')
        try:
            values = json.loads(handle.read(65536))
        except (ValueError, UnicodeError):
            raise ValueError('Invalid credential file') from None
    if not isinstance(values, dict) or not all(isinstance(values.get(k), str) and values[k] for k in ENV_KEYS):
        raise ValueError('Invalid credential file')
    return {k: values[k] for k in ENV_KEYS}


def environment(workspace_root):
    return {**background_env(), **read(workspace_root)}


def version(env):
    return hashlib.sha256(json.dumps([env.get(k, '') for k in ENV_KEYS]).encode()).hexdigest()


def status(workspace_root):
    path = Path(workspace_root) / FILENAME
    result = {'scope': 'workspace', 'path': str(path)}
    try:
        values = read(workspace_root)
        result.update(status='available', version=version(values), updated_at=path.stat().st_mtime)
    except FileNotFoundError:
        result['status'] = 'missing'
    except (OSError, ValueError):
        result['status'] = 'unavailable'
    return result


def refresh(workspace_root, *, initialize=False):
    """Serialize imports; initialization must never overwrite an existing file."""
    from .store import atomic_json
    root = Path(workspace_root)
    private_directory(root)
    fd = nofollow_open(root / '.mediakit-credentials.lock',
                 os.O_RDWR | os.O_CREAT | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0), 0o600)
    with os.fdopen(fd, 'r+') as lock:
        info = os.fstat(lock.fileno())
        if not private_file(info):
            raise ValueError('Unsafe credential lock permissions')
        fcntl.flock(lock, fcntl.LOCK_EX)
        if initialize:
            try:
                values = read(root)
            except FileNotFoundError:
                pass
            else:
                return {'updated': False, 'reason': 'already_initialized', 'version': version(values)}
        values = {key: os.environ.get(key, '') for key in ENV_KEYS}
        if not all(values.values()):
            return {'updated': False, 'reason': 'host_credentials_missing'}
        atomic_json(root / FILENAME, values)
        return {'updated': True, 'version': version(values), 'scope': 'workspace',
                'path': str(root / FILENAME)}
