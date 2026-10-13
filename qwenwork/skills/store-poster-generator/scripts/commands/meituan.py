"""
meituan 命令（CLI 入口）

美团工作流：支持 check-login（验证登录）和 search（执行搜索）两个子命令。
所有浏览器操作通过 detached worker 子进程执行，CLI 退出后浏览器窗口保持打开。

当环境变量 DWS 有值时，本命令自动禁用。
"""

import sys

from utils.envs import IS_IN_DWS
from services.meituan.workflow import run_check_login, run_login, run_search
from services.browser_pipeline import StepStatus

DISABLED = IS_IN_DWS


def register(subparsers) -> None:
    """Register the meituan subcommand."""
    parser = subparsers.add_parser(
        "meituan",
        help="美团工作流（模拟 iPhone 14）",
    )

    action_subparsers = parser.add_subparsers(
        dest="action",
        help="可用操作",
    )

    check_login_parser = action_subparsers.add_parser(
        "check-login",
        help="检测美团登录状态（同步返回 logged_in）",
    )
    check_login_parser.set_defaults(handler=_run_check_login)

    login_parser = action_subparsers.add_parser(
        "login",
        help="打开美团登录页面（detached，等待用户手动登录）",
    )
    login_parser.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="登录超时秒数（默认 120s）",
    )
    login_parser.set_defaults(handler=_run_login)

    search_parser = action_subparsers.add_parser(
        "search",
        help="执行美团关键词搜索（需先确认已登录）",
    )
    search_parser.add_argument(
        "keyword",
        help="搜索关键词（如：麦当劳）",
    )
    search_parser.add_argument(
        "--city",
        default="hangzhou",
        help="城市拼音（默认 hangzhou）",
    )
    search_parser.set_defaults(handler=_run_search)

    parser.set_defaults(handler=lambda args: parser.print_help())


def _run_check_login(args) -> None:
    """Execute the meituan check-login command."""
    context = run_check_login()
    logged_in = context.get("logged_in", False)
    print(f"\n{'✅ 已登录' if logged_in else '⚠️  未登录'}")
    _exit_with_context(context)

def _run_login(args) -> None:
    """Execute the meituan login command."""
    context = run_login(timeout=args.timeout)
    _exit_with_context(context)


def _run_search(args) -> None:
    """Execute the meituan search command."""
    context = run_search(keyword=args.keyword, city=args.city)
    _exit_with_context(context)


def _exit_with_context(context) -> None:
    """根据 Pipeline 执行结果决定退出码。"""
    has_failure = any(
        result.status == StepStatus.FAILED for result in context.results
    )
    if has_failure:
        sys.exit(1)
