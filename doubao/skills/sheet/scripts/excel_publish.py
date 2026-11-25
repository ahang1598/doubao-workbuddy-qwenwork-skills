#!/usr/bin/env python3
"""Read requested calculated values and import the original workbook once."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

from _lo_reuse import output_file, publish_output
from excel_recalculate import recalculate


def _digest(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def _save(path, result):
    with output_file(path, mode=0o600) as (stream, directory):
        stream.write(json.dumps(result, ensure_ascii=False).encode('utf-8'))
        publish_output(stream, directory, path, overwrite=True)


def _lock_identity(path, descriptor):
    current, held = path.lstat(), os.fstat(descriptor)
    if (current.st_dev, current.st_ino) != (held.st_dev, held.st_ino):
        raise OSError('publish lock path was replaced; preserve the existing state')


def _acquire_lock(path):
    if sys.platform == 'win32':
        import msvcrt
    else:
        import fcntl
    created = False
    flags = os.O_RDWR | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_BINARY', 0)
    if path.is_symlink():
        raise OSError('publish lock must not be a symbolic link')
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | flags, 0o600)
        created = True
    except FileExistsError:
        descriptor = os.open(path, flags)
    try:
        if sys.platform == 'win32':
            msvcrt.locking(descriptor, msvcrt.LK_NBLCK, 1)
        else:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        marker = b'sheet-publish-lock-v1\n'
        if created:
            os.write(descriptor, marker)
            os.fsync(descriptor)
        elif os.read(descriptor, len(marker) + 1) != marker:
            raise OSError('legacy or unknown publish lock; recover the existing import first')
        _lock_identity(path, descriptor)
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def publish(file, state, *, name=None, folder_token=None, read_ranges=None, timeout=180):
    source = Path(file).resolve()
    receipt = Path(state).absolute()
    if receipt.is_symlink() or receipt.resolve() == source:
        return dict(status='invalid_input', error='state must be a separate non-symlink file')
    if not source.is_file() or timeout <= 0 or source.suffix.lower() not in ('.xlsx', '.xls', '.csv'):
        return dict(status='invalid_input', error='input must be an existing workbook and timeout must be positive')
    if read_ranges and source.suffix.lower() != '.xlsx':
        return dict(status='invalid_input', error='calculated range reading requires .xlsx')
    lock = receipt.with_name(receipt.name + '.lock')
    try:
        descriptor = _acquire_lock(lock)
    except (OSError, ImportError) as exc:
        return dict(status='state_unavailable', error=str(exc), state=str(receipt),
                    action='保留现有回执；若上次进程中断，先恢复其输出和导入任务，不另建状态文件重导。')
    result = dict(state=str(receipt))
    try:
        request = dict(source=str(source), sha256=_digest(source), name=name,
                       folder_token=folder_token, read_ranges=read_ranges)
        if receipt.exists():
            previous = json.loads(receipt.read_text(encoding='utf-8'))
            if not isinstance(previous, dict):
                raise ValueError('state must contain a JSON object')
            if previous.get('request') != request:
                return dict(status='request_changed', previous=previous, state=str(receipt),
                            action='已有导入回执对应其他输入；保留在线修改，在原在线对象上继续，不自动重导。')
            return dict(previous, reused=True)
        result = dict(status='preparing', request=request, source=str(source), state=str(receipt))
        if read_ranges:
            calculated = recalculate(str(source), read_ranges=read_ranges)
            result['calculation'] = calculated
            if calculated.get('status') != 'recalculated' or calculated.get('read_status') != 'read':
                return dict(result, status='values_unavailable',
                            action='尚未导入；按 calculation 处理取值失败，源文件仍可按原交付契约导入。')
            if any(selection.get('error_cells') for selection in calculated.get('ranges', [])):
                return dict(result, status='calculation_errors',
                            action='所需范围含公式错误，尚未导入；处理 calculation 中已报告的错误。')
        if _digest(source) != request['sha256']:
            return dict(result, status='source_changed', action='取值期间源文件变化，尚未导入；使用完成写入的源文件。')
        command = ['lark-cli', 'sheets', '+workbook-import', '--file', './' + source.name]
        if name is not None:
            command.extend(['--name', name])
        if folder_token is not None:
            command.extend(['--folder-token', folder_token])
        result.update(status='import_unknown',
                      action='不重导；从本次回执、宿主输出恢复 ticket/next_command 或查找本次产物。')
        _lock_identity(lock, descriptor)
        _save(receipt, result)
        try:
            _lock_identity(lock, descriptor)
            completed = subprocess.run(command, cwd=source.parent, capture_output=True, text=True,
                                       timeout=timeout, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            result['error'] = str(exc)
            for key in ('stdout', 'stderr'):
                output = getattr(exc, key, None)
                if output:
                    result[key] = output.decode('utf-8', errors='replace') if isinstance(output, bytes) else output
            _lock_identity(lock, descriptor)
            _save(receipt, result)
            return result
        result.update(returncode=completed.returncode, stdout=completed.stdout, stderr=completed.stderr)
        try:
            envelope = json.loads(completed.stdout)
        except ValueError:
            envelope = None
        result['import'] = envelope
        if isinstance(envelope, dict):
            result.pop('stdout')
        data = envelope.get('data') if isinstance(envelope, dict) else None
        if isinstance(data, dict) and envelope.get('ok') is True and completed.returncode == 0:
            if data.get('ready') is True and type(data.get('job_status')) is int and data['job_status'] == 0 and data.get('url'):
                result.update(status='imported', url=data['url'],
                              action='使用原始 import 回执处理 data.extra；后续操作在该在线对象完成，再按交付契约交付。')
            else:
                result['status'] = 'import_pending'
        _lock_identity(lock, descriptor)
        _save(receipt, result)
        return result
    except (OSError, ValueError, TypeError) as exc:
        return dict(result, status='state_error', error=str(exc),
                    action='保留回执和本次宿主输出；不能据此认定未导入，不另建状态文件重导。')
    finally:
        os.close(descriptor)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('file')
    parser.add_argument('--state', required=True, help='Persistent JSON receipt for this import; repeat it to recover without reimporting')
    parser.add_argument('--name')
    parser.add_argument('--folder-token')
    parser.add_argument('--read-range', action='append', dest='read_ranges')
    parser.add_argument('--timeout', type=int, default=180)
    args = parser.parse_args()
    result = publish(args.file, args.state, name=args.name, folder_token=args.folder_token,
                     read_ranges=args.read_ranges, timeout=args.timeout)
    print(json.dumps(result, ensure_ascii=False))
    if result['status'] != 'imported':
        print(result.get('action') or result.get('error') or result['status'], file=sys.stderr)
        return 3
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
