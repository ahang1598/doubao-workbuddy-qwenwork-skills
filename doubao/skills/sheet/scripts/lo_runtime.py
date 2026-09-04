"""
Helper for running LibreOffice (soffice) in environments where AF_UNIX
sockets may be blocked (e.g., sandboxed VMs).  Detects the restriction
at runtime and applies an LD_PRELOAD shim if needed.
"""

import os
import socket
import subprocess
from pathlib import Path
from typing import List


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
