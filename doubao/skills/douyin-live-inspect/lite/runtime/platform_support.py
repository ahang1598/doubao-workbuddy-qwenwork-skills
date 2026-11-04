"""Small OS boundary shared by media workers, downloads and credential storage."""
# 核心实现模块：负责本模块声明的检测、状态处理或交付边界；敏感输入和原始响应不进入日志。
import contextlib
import ntpath
import os
from pathlib import Path
import signal
import stat
import subprocess
import sys
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


class PrivateDirectoryError(PermissionError):
    def __init__(self, reason, error_detail=None):
        self.reason = reason
        self.error_detail = error_detail
        super().__init__(reason)


# SID objects select the IdentityReference overload (a SID string selects NTAccount).
# Construct and verify the complete DACL before writing anything to disk.
WINDOWS_PRIVATE_ACL = r"""
$ErrorActionPreference='Stop'
try {
  $p=$env:INSPECT_PRIVATE_PATH
  $user=[System.Security.Principal.WindowsIdentity]::GetCurrent().User
  $system=New-Object System.Security.Principal.SecurityIdentifier('S-1-5-18')
  function ValidAcl($acl) {
    $rules=@($acl.GetAccessRules($true,$true,[System.Security.Principal.SecurityIdentifier]))
    if (!$acl.AreAccessRulesProtected -or $rules.Count -ne 2) { return $false }
    foreach ($sid in @($user,$system)) {
      $found=@($rules | Where-Object { $_.IdentityReference.Value -eq $sid.Value -and $_.AccessControlType -eq 'Allow' -and $_.FileSystemRights -eq 'FullControl' -and $_.InheritanceFlags -eq 'ContainerInherit,ObjectInherit' -and $_.PropagationFlags -eq 'None' })
      if ($found.Count -ne 1) { return $false }
    }
    return $true
  }
  $dir=New-Object System.IO.DirectoryInfo($p)
  [Console]::Error.WriteLine('ACL_READ')
  $acl=$dir.GetAccessControl([System.Security.AccessControl.AccessControlSections]::Access)
  if (!(ValidAcl $acl)) {
    $acl=New-Object System.Security.AccessControl.DirectorySecurity
    $acl.SetAccessRuleProtection($true,$false)
    foreach ($sid in @($user,$system)) {
      $rule=New-Object System.Security.AccessControl.FileSystemAccessRule($sid,'FullControl','ContainerInherit,ObjectInherit','None','Allow')
      $acl.AddAccessRule($rule)
    }
    if (!(ValidAcl $acl)) { throw 'invalid DACL' }
    [Console]::Error.WriteLine('ACL_APPLY')
    $dir.SetAccessControl($acl)
  }
  [Console]::Error.WriteLine('ACL_VERIFY')
  if (!(ValidAcl ($dir.GetAccessControl([System.Security.AccessControl.AccessControlSections]::Access)))) { throw 'verification failed' }
  [Console]::Write('ACL_VERIFIED')
} catch {
  # PowerShell 会包装 .NET 异常；沿内部异常识别拒绝访问，仅输出固定标记，避免泄露路径和 SID。
  $errorObject=$_.Exception
  while ($null -ne $errorObject) {
    # -2147024891 是有符号 HRESULT 0x80070005（E_ACCESSDENIED）。
    if ($errorObject -is [System.UnauthorizedAccessException] -or $errorObject.HResult -eq -2147024891) {
      [Console]::Error.WriteLine('ACL_ACCESS_DENIED')
      break
    }
    $errorObject=$errorObject.InnerException
  }
  exit 1
}
"""


def windows_powershell():
    # 宿主可能裁剪 PATH；从系统目录定位，不搜索当前目录中的同名程序。
    root = os.environ.get('SystemRoot') or os.environ.get('windir')
    # 旧版 Python 将单反斜杠根路径也视为绝对路径；仍需盘符/UNC 根，避免依赖当前盘。
    if not root or not ntpath.isabs(root) or not ntpath.splitdrive(root)[0]:
        # 环境变量缺失或不是绝对路径时询问 Windows，避免假定系统安装在 C 盘。
        import ctypes
        from ctypes import wintypes
        get_directory = ctypes.WinDLL('kernel32', use_last_error=True).GetWindowsDirectoryW
        get_directory.argtypes = [wintypes.LPWSTR, wintypes.UINT]
        get_directory.restype = wintypes.UINT
        # 缓冲区按宽字符计数；返回长度达到容量时不能使用被截断的系统目录。
        buffer = ctypes.create_unicode_buffer(32768)
        length = get_directory(buffer, len(buffer))
        if not length:raise ctypes.WinError(ctypes.get_last_error())
        if length >= len(buffer):raise OSError('Windows directory exceeds buffer')
        root = buffer.value
    # 32 位进程使用 Sysnative 绕过 WOW64 重定向；其他进程使用 System32。
    directory = 'Sysnative' if sys.maxsize <= 2**32 and os.environ.get('PROCESSOR_ARCHITEW6432') else 'System32'
    # v1.0 是 Windows PowerShell 沿用的目录名，5.1 也在此处，不代表运行版本。
    executable = ntpath.join(root, directory, 'WindowsPowerShell', 'v1.0', 'powershell.exe')
    # 保留 stat 的缺失/拒绝访问异常，供调用方分类；候选路径不是文件时也不能回退 PATH。
    if not stat.S_ISREG(os.stat(executable).st_mode):raise FileNotFoundError('Windows PowerShell missing')
    return executable


def windows_acl_stage(output):
    if isinstance(output, bytes):output = output.decode('utf-8', errors='replace')
    # stderr 只取最后一个白名单阶段；没有标记表示进度未知，不推断系统根因。
    stages = [line.strip() for line in (output or '').splitlines()
              if line.strip() in {'ACL_READ', 'ACL_APPLY', 'ACL_VERIFY'}]
    return stages[-1] if stages else 'ACL_STARTUP'


def windows_private_directory(path):
    import tempfile
    reason = 'acl_apply_failed'
    detail = None
    # 用阶段变量隔离错误来源，共用一个捕获/上报出口；必须在对应操作前切换阶段。
    stage = 'ACL_STARTUP'
    try:
        result = subprocess.run([windows_powershell(),'-NoProfile','-NonInteractive','-Command',WINDOWS_PRIVATE_ACL],
            env={**os.environ,'INSPECT_PRIVATE_PATH':str(path)}, capture_output=True, timeout=15, shell=False)
        stage = windows_acl_stage(result.stderr)
        if result.returncode:
            # 非零退出可能发生于回读验证；不能全部当成 ACL 应用失败。
            reason = 'acl_verify_failed' if stage == 'ACL_VERIFY' else 'acl_apply_failed'
            suffix = '_ACCESS_DENIED' if b'ACL_ACCESS_DENIED' in result.stderr.splitlines() else '_FAILED'
            raise PrivateDirectoryError(reason, stage + suffix)
        stage = 'ACL_VERIFY'
        reason = 'acl_verify_failed'
        # 退出码为零仍须收到脚本完成回读的显式确认。
        if result.stdout.strip() != b'ACL_VERIFIED':raise PrivateDirectoryError(reason, stage + '_FAILED')
        # DACL 正确不代表实际可读写；先切到探测阶段，目录被删除也只能算验证失败。
        stage = 'ACL_PROBE'
        with tempfile.NamedTemporaryFile(dir=path, prefix='.acl-probe-', mode='w+b') as probe:
            probe.write(b'private');probe.flush();probe.seek(0)
            if probe.read() != b'private':raise PrivateDirectoryError(reason, stage + '_FAILED')
    except (OSError, subprocess.SubprocessError) as error:
        if isinstance(error, PrivateDirectoryError):
            # 此异常继承 PermissionError；优先保留已确定的分类，避免再次误判为拒绝访问。
            reason, detail = error.reason, error.error_detail
        elif isinstance(error, subprocess.TimeoutExpired):
            reason='acl_timeout'
            detail=windows_acl_stage(error.stderr)+'_TIMEOUT'
        else:
            # 只有启动阶段的文件缺失代表 PowerShell 不可用，不能覆盖探测阶段的 reason。
            if stage == 'ACL_STARTUP' and isinstance(error, FileNotFoundError):reason='acl_unavailable'
            suffix = '_NOT_FOUND' if isinstance(error, FileNotFoundError) else '_ACCESS_DENIED' if isinstance(error, PermissionError) else '_FAILED'
            detail = stage + suffix
        from runtime.bridge import publish_metadata, record_runtime_issue
        # 统一出口仅传固定详情与原有 reason，不上传原始系统错误，也不重复记录本次故障。
        publish_metadata(error_detail=detail)
        record_runtime_issue('windows_acl', reason)
        raise PrivateDirectoryError(reason,detail) from None


def private_directory(path):
    path = Path(path)
    if path.is_symlink() or (path.exists() and getattr(path.lstat(), 'st_file_attributes', 0) & 0x400):
        raise ValueError('private directory cannot be a link')
    try:path.mkdir(parents=True, exist_ok=True, mode=0o700)
    except OSError:
        if os.name == 'nt':
            from runtime.bridge import record_runtime_issue
            record_runtime_issue('windows_acl','acl_apply_failed')
            raise PrivateDirectoryError('acl_apply_failed') from None
        raise
    if os.name == 'nt':
        windows_private_directory(path)
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
