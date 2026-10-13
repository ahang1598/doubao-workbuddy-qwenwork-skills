"""Task-local stop intent, readable even while SQLite is unavailable."""
import json
import math
import os
import time
from pathlib import Path
from runtime.platform_support import nofollow_open, private_file


def read(root):
    try:
        with os.fdopen(nofollow_open(Path(root)/'stop-request.json', os.O_RDONLY)) as stream:
            if not private_file(os.fstat(stream.fileno())):return None
            value = json.load(stream)
        return value if type(value.get('requested_at')) in (int,float) and math.isfinite(value['requested_at']) and value.get('reason') in {'user_request','source_ended'} else None
    except (OSError, ValueError, TypeError, AttributeError):return None


def request(root, *, origin, reason, instruction):
    if origin not in {'agent','dashboard','runtime'} or reason not in {'user_request','source_ended'}:
        raise ValueError('explicit stop intent required')
    if origin == 'agent' and (not isinstance(instruction,str) or not instruction.strip()):
        raise ValueError('agent stop requires user instruction')
    root=Path(root).expanduser().resolve()
    if not (root/'inspection.db').is_file():raise ValueError('task does not exist')
    previous=read(root)
    if previous:return previous
    value={'requested_at':time.time(),'origin':origin,'reason':reason}
    try:
        fd=nofollow_open(root/'stop-request.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    except FileExistsError:
        return read(root)  # Another stop owns the first timestamp.
    with os.fdopen(fd,'w') as stream:
        json.dump(value,stream);stream.flush();os.fsync(stream.fileno())
    return value
