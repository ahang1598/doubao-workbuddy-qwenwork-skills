"""
chrome 命令（CLI 入口）

Chrome/Chromium 管理：查找、检查、下载。
核心逻辑位于 chromium/ 包中。

当环境变量 DWS 有值时，本命令自动禁用。
"""

import sys

from utils.envs import IS_IN_DWS
from services.browser.finder import check_chrome, download_chrome, ensure_chrome

DISABLED = IS_IN_DWS

# ---------------------------------------------------------------------------
# CLI 注册
# ---------------------------------------------------------------------------

_ACTION_HANDLERS = {
    "ensure": ensure_chrome,
    "check": check_chrome,
    "download": download_chrome,
}


def register(subparsers) -> None:
    """Register the chrome subcommand."""
    parser = subparsers.add_parser(
        "chrome",
        help="Chrome/Chromium 管理：查找、检查、下载",
    )
    parser.add_argument(
        "action",
        choices=list(_ACTION_HANDLERS.keys()),
        help="操作类型：ensure（查找+自动下载）、check（仅查找）、download（强制下载）",
    )
    parser.set_defaults(handler=run)


def run(args) -> None:
    """Execute the chrome command."""
    handler = _ACTION_HANDLERS[args.action]
    chrome_path = handler()
    if chrome_path:
        print(f"\n🎯 Chrome 可执行文件路径: {chrome_path}")
        sys.exit(0)
    else:
        print("\n❌ 操作失败", file=sys.stderr)
        sys.exit(1)
