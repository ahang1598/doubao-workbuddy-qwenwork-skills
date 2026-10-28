"""
Helper for running LibreOffice (soffice) in environments where AF_UNIX
sockets may be blocked (e.g., sandboxed VMs).  Detects the restriction
at runtime and applies an LD_PRELOAD shim if needed.
"""

import os
import signal
import shutil
import socket
import subprocess
import tempfile
import time
from pathlib import Path
from typing import List


# soffice 启动阶段的报错特征：命中即视为 profile / 启动失败，可换全新 profile 重试一次。
LO_START_FAILURE_MARKERS = (
    "User installation could not be completed",
    "The application cannot be started",
    "DeploymentException",
)


def profile_arg(profile_dir: Path) -> str:
    """LibreOffice 的 UserInstallation 只接受 file URL。"""
    return f"-env:UserInstallation={profile_dir.resolve().as_uri()}"


def soffice_detail(stderr: str, stdout: str = "") -> str:
    """合并 stderr 与 stdout 后去掉 Fontconfig 之类与失败无关的告警行，只留真正的报错。

    不能只取非空的那一路：stderr 常常只有 Fontconfig 告警，真实报错却在 stdout。
    """
    text = "\n".join(t for t in (stderr, stdout) if t)
    lines = [ln for ln in text.splitlines()
             if ln.strip() and not ln.startswith("Fontconfig warning")]
    return "\n".join(lines).strip()


def run_managed_process(cmd: List[str], timeout: float, env: dict) -> subprocess.CompletedProcess:
    """运行并回收整棵进程树，避免超时后残留 soffice.bin 继续写文件。"""
    popen_kwargs = {
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "text": True,
        "env": env,
    }
    if os.name == "posix":
        popen_kwargs["start_new_session"] = True
    elif os.name == "nt":
        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP

    process = subprocess.Popen(cmd, **popen_kwargs)
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        if os.name == "posix":
            # macOS 上组内进程退出后，再对该组发信号会报 PermissionError 而非
            # ProcessLookupError；两者都表示组已不存在，不能让清理阶段抛出。
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except (ProcessLookupError, PermissionError):
                pass
            deadline = time.monotonic() + 2
            while time.monotonic() < deadline:
                try:
                    os.killpg(process.pid, 0)
                except (ProcessLookupError, PermissionError):
                    break
                time.sleep(0.05)
            # 组长退出不代表 soffice.bin 已退出；对仍存在的整个组补发 SIGKILL。
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
        elif os.name == "nt":
            # terminate() 只杀 soffice.exe，taskkill /T 才能回收派生的 soffice.bin。
            try:
                subprocess.run(
                    ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=False,
                )
            except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
                process.kill()
        else:
            process.kill()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        raise
    return subprocess.CompletedProcess(cmd, process.returncode, stdout, stderr)


def sweep_stale_profiles(prefix: str, max_age_seconds: float = 3600) -> None:
    """清掉被强杀的进程遗留的临时 profile；只碰本用户、超过一小时的目录，失败不报。"""
    now = time.time()
    uid = os.getuid() if os.name == "posix" else None
    try:
        root = Path(tempfile.gettempdir())
        entries = list(root.glob(f"{prefix}*"))
    except OSError:
        return
    for path in entries:
        try:
            st = path.lstat()
            owned = uid is None or st.st_uid == uid
            if (path.is_dir() and not path.is_symlink() and owned
                    and now - st.st_mtime > max_age_seconds):
                shutil.rmtree(path, ignore_errors=True)
        except OSError:
            continue


def get_soffice_env() -> dict:
    env = os.environ.copy()
    env["SAL_USE_VCLPLUGIN"] = "svp"

    if _needs_shim():
        shim = _ensure_shim()
        env["LD_PRELOAD"] = str(shim)

    return env


def run_soffice(args: List[str], **kwargs) -> subprocess.CompletedProcess:
    env = get_soffice_env()
    return subprocess.run(["soffice"] + args, env=env, **kwargs)


_SHIM_DIR = Path.home() / ".cache" / "sheet-skill-spec" / "lo-shim"
_SHIM_SO = _SHIM_DIR / "lo_socket_shim.so"
_SHIM_SRC = _SHIM_DIR / "lo_socket_shim.c"


def _needs_shim() -> bool:
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.close()
        return False
    except OSError:
        return True


def _quiet_unlink(path: Path):
    """删除文件，不存在就算了。Python 3.7 的 unlink() 没有 missing_ok 形参。"""
    try:
        path.unlink()
    except OSError:
        pass


def _owned_private_file(path: Path) -> bool:
    try:
        stat = path.stat()
        return stat.st_uid == os.getuid() and (stat.st_mode & 0o077) == 0
    except OSError:
        return False


def _ensure_shim() -> Path:
    _SHIM_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(_SHIM_DIR, 0o700)
    if _SHIM_SO.exists():
        if not _owned_private_file(_SHIM_SO):
            raise RuntimeError(f"Refusing untrusted LibreOffice shim: {_SHIM_SO}")
        return _SHIM_SO

    # 源文件与临时 .so 都用 PID 唯一名：并发首次初始化时各进程独立编译，
    # finally 只清理自己的文件——共享固定名源文件会被先完成的进程删掉，
    # 让其它进程的 gcc 读不到源（12 并发实测 11 个 CalledProcessError）。
    # 最终 os.replace 原子发布，多进程各自编译同一份源，结果一致。
    tmp_src = _SHIM_DIR / f"lo_socket_shim.{os.getpid()}.tmp.c"
    tmp_src.write_text(_SHIM_SOURCE)
    os.chmod(tmp_src, 0o600)
    tmp_so = _SHIM_DIR / f"lo_socket_shim.{os.getpid()}.tmp.so"
    try:
        subprocess.run(
            ["gcc", "-shared", "-fPIC", "-o", str(tmp_so), str(tmp_src), "-ldl"],
            check=True,
            capture_output=True,
        )
        os.chmod(tmp_so, 0o700)
        os.replace(tmp_so, _SHIM_SO)
        if not _owned_private_file(_SHIM_SO):
            raise RuntimeError(f"LibreOffice shim permissions are unsafe: {_SHIM_SO}")
    finally:
        _quiet_unlink(tmp_src)
        _quiet_unlink(tmp_so)
    return _SHIM_SO


_SHIM_SOURCE = r"""
#define _GNU_SOURCE
#include <dlfcn.h>
#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/socket.h>
#include <unistd.h>

static int (*real_socket)(int, int, int);
static int (*real_socketpair)(int, int, int, int[2]);
static int (*real_listen)(int, int);
static int (*real_accept)(int, struct sockaddr *, socklen_t *);
static int (*real_close)(int);
static int (*real_read)(int, void *, size_t);

static int is_shimmed[1024];
static int peer_of[1024];
static int wake_r[1024];
static int wake_w[1024];
static int listener_fd = -1;

__attribute__((constructor))
static void init(void) {
    real_socket     = dlsym(RTLD_NEXT, "socket");
    real_socketpair = dlsym(RTLD_NEXT, "socketpair");
    real_listen     = dlsym(RTLD_NEXT, "listen");
    real_accept     = dlsym(RTLD_NEXT, "accept");
    real_close      = dlsym(RTLD_NEXT, "close");
    real_read       = dlsym(RTLD_NEXT, "read");
    for (int i = 0; i < 1024; i++) {
        peer_of[i] = -1;
        wake_r[i]  = -1;
        wake_w[i]  = -1;
    }
}

int socket(int domain, int type, int protocol) {
    if (domain == AF_UNIX) {
        int fd = real_socket(domain, type, protocol);
        if (fd >= 0) return fd;
        int sv[2];
        if (real_socketpair(domain, type, protocol, sv) == 0) {
            if (sv[0] >= 0 && sv[0] < 1024) {
                is_shimmed[sv[0]] = 1;
                peer_of[sv[0]]    = sv[1];
                int wp[2];
                if (pipe(wp) == 0) {
                    wake_r[sv[0]] = wp[0];
                    wake_w[sv[0]] = wp[1];
                }
            }
            return sv[0];
        }
        errno = EPERM;
        return -1;
    }
    return real_socket(domain, type, protocol);
}

int listen(int sockfd, int backlog) {
    if (sockfd >= 0 && sockfd < 1024 && is_shimmed[sockfd]) {
        listener_fd = sockfd;
        return 0;
    }
    return real_listen(sockfd, backlog);
}

int accept(int sockfd, struct sockaddr *addr, socklen_t *addrlen) {
    if (sockfd >= 0 && sockfd < 1024 && is_shimmed[sockfd]) {
        if (wake_r[sockfd] >= 0) {
            char buf;
            real_read(wake_r[sockfd], &buf, 1);
        }
        errno = ECONNABORTED;
        return -1;
    }
    return real_accept(sockfd, addr, addrlen);
}

int close(int fd) {
    if (fd >= 0 && fd < 1024 && is_shimmed[fd]) {
        int was_listener = (fd == listener_fd);
        is_shimmed[fd] = 0;

        if (wake_w[fd] >= 0) {
            char c = 0;
            write(wake_w[fd], &c, 1);
            real_close(wake_w[fd]);
            wake_w[fd] = -1;
        }
        if (wake_r[fd] >= 0) { real_close(wake_r[fd]); wake_r[fd]  = -1; }
        if (peer_of[fd] >= 0) { real_close(peer_of[fd]); peer_of[fd] = -1; }

        if (was_listener)
            _exit(0);
    }
    return real_close(fd);
}
"""


if __name__ == "__main__":
    import sys
    result = run_soffice(sys.argv[1:])
    sys.exit(result.returncode)
