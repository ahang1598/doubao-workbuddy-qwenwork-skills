"""
taobao-login 命令（CLI 入口）

启动淘宝登录验证：通过 CDP 打开淘宝登录页，等待用户完成登录。
主进程启动后直接退出，登录验证在独立子进程中运行。
"""

from utils.envs import IS_IN_DWS
from services.taobaoworkflows.taobao_login import start_taobao_login

DISABLED = IS_IN_DWS


def register(subparsers) -> None:
    """Register the taobao-login subcommand."""
    parser = subparsers.add_parser(
        "taobao-login",
        help="启动淘宝登录验证（非无头模式）",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="登录超时秒数（默认 30s）",
    )
    parser.set_defaults(handler=run)


def run(args) -> None:
    """Execute the taobao-login command."""
    start_taobao_login(timeout=args.timeout)
