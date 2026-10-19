"""Business task identity reserved before acquisition; independent of telemetry."""
import json
import os
from pathlib import Path
import re
import stat
import uuid

FILE = '.task-context.json'
ID = re.compile(r'[0-9a-f]{32}', re.I)


def read(directory):
    from runtime.platform_support import nofollow_open
    filename = Path(directory) / FILE
    try:
        if not stat.S_ISREG(filename.lstat().st_mode):
            raise ValueError('invalid task context')
        fd = nofollow_open(filename, os.O_RDONLY | getattr(os, 'O_NONBLOCK', 0))
    except FileNotFoundError:
        return None
    with os.fdopen(fd, 'r', encoding='utf-8') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > 1024:
            raise ValueError('invalid task context')
        value = json.load(stream)
    if not isinstance(value, dict) or not isinstance(value.get('task_id'), str) or not ID.fullmatch(value['task_id']):
        raise ValueError('invalid task context')
    return value


def reserve(directory):
    from runtime.platform_support import private_directory
    root = Path(directory).expanduser()
    if root.is_symlink():
        raise ValueError('invalid task directory')
    root = root.resolve()
    skill = Path(__file__).resolve().parents[2]
    if root == skill or skill in root.parents:
        raise ValueError('task directory must be outside Skill')
    private_directory(root)
    value = read(root)
    if value:
        return value['task_id']
    if (root / 'inspection.db').exists() or (root / 'batch.json').exists():
        return None
    temporary = root / (FILE + '.' + uuid.uuid4().hex)
    try:
        with os.fdopen(os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w', encoding='utf-8') as stream:
            json.dump({'task_id': uuid.uuid4().hex, 'funnel_schema_version': 1}, stream)
        try:
            os.link(temporary, root / FILE)
        except FileExistsError:
            pass
    finally:
        temporary.unlink(missing_ok=True)
    return read(root)['task_id']
