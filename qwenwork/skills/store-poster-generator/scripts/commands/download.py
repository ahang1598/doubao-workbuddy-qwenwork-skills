"""
download 命令

下载文件到 workspace 目录中。

用法：
    python cli.py download <url>
    python cli.py download <url> --dest subdir/filename.txt
    python cli.py download <url> --extract
"""

import sys
from pathlib import Path

from commands.skill_context import get_skill_context
from utils.download_utils import download_file, download_and_extract

DISABLED = True

def _get_output_dir() -> Path:
    """从 skill_context 获取下载文件的目标目录。"""
    context = get_skill_context()
    output_dir = context.get("output_dir")

    print(f"output_dir: {output_dir}")
    if not output_dir:
        print("❌ 无法确定下载目标目录：PWD 和 AGENT_WORK_ROOT 均未设置", file=sys.stderr)
        sys.exit(1)
    return Path(output_dir)


def _filename_from_url(url: str) -> str:
    """从 URL 中提取文件名，去除查询参数。"""
    path_part = url.split("?")[0].split("#")[0]
    name = path_part.rstrip("/").rsplit("/", 1)[-1]
    return name or "downloaded_file"


def register(subparsers) -> None:
    """Register the download subcommand."""
    parser = subparsers.add_parser(
        "download",
        help="下载文件到 workspace 目录",
    )
    parser.add_argument("url", help="要下载的文件 URL")
    parser.add_argument(
        "--dest",
        default=None,
        help="保存路径（相对于 workspace 目录），不指定则自动从 URL 推断文件名",
    )
    parser.add_argument(
        "--extract",
        action="store_true",
        default=False,
        help="下载后自动解压（支持 .zip / .tar.gz / .tgz）",
    )
    parser.set_defaults(handler=run)


def run(args) -> None:
    """Execute the download command."""
    workspace_dir = _get_output_dir()

    if args.extract:
        dest_dir = workspace_dir / args.dest if args.dest else workspace_dir
        dest_dir.mkdir(parents=True, exist_ok=True)

        print(f"📥 下载并解压到: {dest_dir}")
        print(f"   URL: {args.url}")
        try:
            download_and_extract(args.url, dest_dir)
            print(f"✅ 下载并解压完成: {dest_dir}")
        except Exception as error:
            print(f"❌ 下载或解压失败: {error}", file=sys.stderr)
            sys.exit(1)
    else:
        filename = args.dest or _filename_from_url(args.url)
        dest_path = workspace_dir / filename
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        print(f"📥 下载文件到: {dest_path}")
        print(f"   URL: {args.url}")
        try:
            download_file(args.url, str(dest_path))
            print(f"✅ 下载完成: {dest_path}")
        except Exception as error:
            print(f"❌ 下载失败: {error}", file=sys.stderr)
            sys.exit(1)
