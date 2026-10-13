"""单实例锁，防止多个进程同时操作浏览器。"""

from __future__ import annotations

import contextlib
import logging
import os
import time

import psutil

logger = logging.getLogger(__name__)

_DEFAULT_LOCK_FILE = os.path.join(
    os.path.expanduser("~"), ".dingclaw", "wechat-channels", "run.lock"
)


class RunLock:
    """文件锁，确保同一时间只有一个进程在操作。"""

    def __init__(self, lock_file: str = _DEFAULT_LOCK_FILE) -> None:
        self.lock_file = lock_file
        self._fd: int | None = None

    def acquire(self, timeout: float = 30.0) -> bool:
        """获取锁。"""
        os.makedirs(os.path.dirname(self.lock_file), exist_ok=True)
        deadline = time.monotonic() + timeout

        while time.monotonic() < deadline:
            try:
                self._fd = os.open(
                    self.lock_file,
                    os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                )
                os.write(self._fd, str(os.getpid()).encode())
                logger.debug("获取锁成功: %s", self.lock_file)
                return True
            except FileExistsError:
                if self._is_stale():
                    self._force_release()
                    continue
                time.sleep(1)

        logger.warning("获取锁超时: %s", self.lock_file)
        return False

    def release(self) -> None:
        """释放锁。"""
        if self._fd is not None:
            with contextlib.suppress(OSError):
                os.close(self._fd)
            self._fd = None

        with contextlib.suppress(FileNotFoundError):
            os.remove(self.lock_file)

        logger.debug("释放锁: %s", self.lock_file)

    def _is_stale(self) -> bool:
        """检查锁文件是否已过时。"""
        try:
            with open(self.lock_file) as f:
                pid = int(f.read().strip())
            return not psutil.pid_exists(pid)
        except (ValueError, OSError):
            return True

    def _force_release(self) -> None:
        """强制释放过时的锁。"""
        with contextlib.suppress(FileNotFoundError):
            os.remove(self.lock_file)
        logger.info("强制释放过时锁: %s", self.lock_file)

    def __enter__(self) -> RunLock:
        if not self.acquire():
            raise TimeoutError(f"无法获取锁: {self.lock_file}")
        return self

    def __exit__(self, *args: object) -> None:
        self.release()
