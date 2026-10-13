"""
通用下载 & 解压工具

提供带进度输出的文件下载、压缩包解压等通用能力，供各模块复用。
"""

import os
import sys
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path


def get_archive_suffix(url: str) -> str:
    """根据 URL 推断压缩包后缀名。"""
    lower_url = url.lower()
    if lower_url.endswith(".tar.gz") or lower_url.endswith(".tgz"):
        return ".tar.gz"
    if lower_url.endswith(".zip"):
        return ".zip"
    return ".zip"


def extract_archive(archive_path: str, dest_dir: Path) -> None:
    """解压压缩包到目标目录，支持 .zip 和 .tar.gz/.tgz。"""
    if archive_path.endswith(".tar.gz") or archive_path.endswith(".tgz"):
        with tarfile.open(archive_path, "r:gz") as tar:
            tar.extractall(path=str(dest_dir))
    elif archive_path.endswith(".zip"):
        with zipfile.ZipFile(archive_path, "r") as zf:
            zf.extractall(path=str(dest_dir))
    else:
        with zipfile.ZipFile(archive_path, "r") as zf:
            zf.extractall(path=str(dest_dir))


def _format_size(num_bytes: int) -> str:
    """将字节数格式化为人类可读的大小字符串。"""
    for unit in ("B", "KB", "MB", "GB"):
        if abs(num_bytes) < 1024:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024
    return f"{num_bytes:.1f} TB"


def _make_progress_hook(total_size: int | None):
    """创建 urlretrieve 的进度回调函数。"""
    downloaded = 0

    def hook(block_count: int, block_size: int, _total_size: int):
        nonlocal downloaded
        downloaded = block_count * block_size
        actual_total = total_size or _total_size

        if actual_total and actual_total > 0:
            percent = min(downloaded / actual_total * 100, 100)
            bar_length = 30
            filled = int(bar_length * percent / 100)
            bar = "█" * filled + "░" * (bar_length - filled)
            sys.stdout.write(
                f"\r   ⏳ [{bar}] {percent:5.1f}%  "
                f"{_format_size(downloaded)} / {_format_size(actual_total)}"
            )
        else:
            sys.stdout.write(f"\r   ⏳ 已下载 {_format_size(downloaded)}")

        sys.stdout.flush()

    return hook


def download_file(url: str, dest_path: str) -> None:
    """下载文件到指定路径，输出下载进度。

    Args:
        url: 下载地址
        dest_path: 保存到的本地文件路径

    Raises:
        Exception: 下载失败时抛出异常
    """
    # 先尝试 HEAD 请求获取文件大小
    total_size = None
    try:
        request = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(request, timeout=10) as response:
            content_length = response.headers.get("Content-Length")
            if content_length:
                total_size = int(content_length)
    except Exception:
        pass

    hook = _make_progress_hook(total_size)
    urllib.request.urlretrieve(url, dest_path, reporthook=hook)
    # 换行，结束进度条
    print()


def download_and_extract(url: str, dest_dir: Path) -> None:
    """下载压缩包并解压到目标目录（带进度输出）。

    下载完成后自动清理临时文件。

    Args:
        url: 压缩包下载地址
        dest_dir: 解压目标目录

    Raises:
        Exception: 下载或解压失败时抛出异常
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    suffix = get_archive_suffix(url)

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
            tmp_path = tmp_file.name

        download_file(url, tmp_path)
        extract_archive(tmp_path, dest_dir)
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
