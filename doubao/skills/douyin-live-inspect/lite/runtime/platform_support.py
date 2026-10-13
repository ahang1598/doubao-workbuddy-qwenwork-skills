"""Small OS boundary shared by media workers, downloads and credential storage."""
import contextlib
import os
from pathlib import Path
import signal
import stat
import subprocess
import time
import threading

if os.name != 'nt':
    import fcntl
else:
    import msvcrt
    class _Locks:
        LOCK_EX, LOCK_NB, LOCK_UN = 1, 2, 4
        @staticmethod
        def flock(handle, mode):
            fd = handle if isinstance(handle, int) else handle.fileno()
            os.lseek(fd, 0, os.SEEK_SET)
            if mode & _Locks.LOCK_UN:
                msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
                return
            while True:
                try:
                    msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                    return
                except OSError:
                    if mode & _Locks.LOCK_NB: raise BlockingIOError('resource locked') from None
                    time.sleep(.1)
    fcntl = _Locks()


def nofollow_open(path, flags, mode=0o600):
    path = Path(path)
    if path.is_symlink() or (path.exists() and getattr(path.lstat(), 'st_file_attributes', 0) & 0x400):
        raise ValueError('link not allowed')
    return os.open(path, flags | getattr(os, 'O_NOFOLLOW', 0), mode)


def private_directory(path):
    path = Path(path)
    if path.is_symlink() or (path.exists() and getattr(path.lstat(), 'st_file_attributes', 0) & 0x400):
        raise ValueError('private directory cannot be a link')
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    if os.name == 'nt':
        # Restrict DACL to the current user and SYSTEM; never rely on POSIX mode bits on NTFS.
        script = "$p=$env:INSPECT_PRIVATE_PATH; $i=[System.Security.Principal.WindowsIdentity]::GetCurrent(); $a=New-Object System.Security.AccessControl.DirectorySecurity; $a.SetOwner($i.User); $a.SetAccessRuleProtection($true,$false); foreach($s in @($i.User.Value,'S-1-5-18')) {$r=New-Object System.Security.AccessControl.FileSystemAccessRule($s,'FullControl','ContainerInherit,ObjectInherit','None','Allow'); $a.AddAccessRule($r)}; Set-Acl -LiteralPath $p -AclObject $a -ErrorAction Stop"
        result = subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',script],
            env={**os.environ,'INSPECT_PRIVATE_PATH':str(path)}, capture_output=True, timeout=15)
        if result.returncode: raise ValueError('private directory ACL unavailable')
    elif path.stat().st_mode & 0o077:
        raise ValueError('directory must be private (0700)')
    return path


def private_file(info):
    return stat.S_ISREG(info.st_mode) and (os.name == 'nt' or
        (info.st_uid == os.getuid() and not info.st_mode & 0o077))


@contextlib.contextmanager
def file_lock(path, timeout=300):
    fd = nofollow_open(path, os.O_RDWR | os.O_CREAT)
    with os.fdopen(fd, 'r+b') as handle:
        deadline = time.monotonic() + timeout
        while True:
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline: raise TimeoutError('lock timeout') from None
                time.sleep(.1)
        try: yield
        finally: fcntl.flock(handle, fcntl.LOCK_UN)


def process_options():
    return {'creationflags': subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == 'nt' else {'start_new_session': True}


def kill_tree(process):
    if process.poll() is not None: return
    if os.name == 'nt':
        subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'], capture_output=True, timeout=15)
    else:
        try: os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError: pass


def stop_capture(process):
    # Closing the guardian pipe works on Windows as well as POSIX and survives worker death.
    if process.stdin and not process.stdin.closed: process.stdin.close()


# Python ASR regression tools use these names; share the existing OS boundary.
def open_lock(path):
    return nofollow_open(path, os.O_RDWR | os.O_CREAT)


def lock_file(handle, *, blocking=True):
    fcntl.flock(handle, fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB))


def unlock_file(handle):
    fcntl.flock(handle, fcntl.LOCK_UN)


# Actual child handles avoid signaling a reused PID or another inspection task.
_media_children = set()
_capture_children = set()
_media_children_lock = threading.Lock()
_media_children_closed = False

def media_popen(*args, **kwargs):
    capture = kwargs.pop('capture_child',False)
    with _media_children_lock:
        if _media_children_closed:raise RuntimeError('media processing stopped')
        child = subprocess.Popen(*args, **kwargs)
        _media_children.difference_update(p for p in list(_media_children) if p.poll() is not None)
        _media_children.add(child)
        if capture:_capture_children.add(child)
        return child

def stop_capture_children(force=False):
    with _media_children_lock:
        children=list(_capture_children)
    for child in children:
        if child.poll() is None:
            if force:kill_tree(child)
            else:stop_capture(child)

def stop_media_children():
    global _media_children_closed
    with _media_children_lock:
        _media_children_closed = True
        for child in list(_media_children):
            if child.poll() is None:
                # Preparation children may share their supervisor's process group.
                try:
                    if os.name != 'nt' and os.getpgid(child.pid) != child.pid:child.kill()
                    else:kill_tree(child)
                except ProcessLookupError:pass
        deadline = time.monotonic() + .5
        for child in list(_media_children):
            try:child.wait(timeout=max(0,deadline-time.monotonic()))
            except subprocess.TimeoutExpired:pass
