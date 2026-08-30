#!/usr/bin/env python3
"""xhs-content-reader CLI — 精简版，仅保留内容读取相关的 4 个命令。

子命令: check-login, search-feeds, get-feed-detail, close-browser
全局选项: --host, --port
输出: JSON（ensure_ascii=False）
退出码: 0=成功, 1=未登录, 2=错误
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone

# Windows 控制台默认编码（如 cp1252）不支持中文，强制 UTF-8
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("xhs-cli")
UTC = timezone.utc


def _output(data: dict, exit_code: int = 0) -> None:
    """输出 JSON 并退出。"""
    print(json.dumps(data, ensure_ascii=False, indent=2))
    sys.exit(exit_code)


def _connect(args: argparse.Namespace, reuse_page: bool = True):
    """连接到 Chrome 并返回 (browser, page)。"""
    from chrome_launcher import ensure_chrome, has_display
    from xhs.cdp import Browser

    if not ensure_chrome(port=args.port, headless=not has_display()):
        _output(
            {"success": False, "error": "无法启动 Chrome，请检查 Chrome 是否已安装"},
            exit_code=2,
        )

    browser = Browser(host=args.host, port=args.port)
    browser.connect()

    if reuse_page:
        page = browser.get_existing_page()
        if page:
            return browser, page

    page = browser.new_page()
    return browser, page


# ========== 子命令实现 ==========


def cmd_check_login(args: argparse.Namespace) -> None:
    """检查登录状态。"""
    from xhs.login import check_login_status

    browser, page = _connect(args)
    try:
        logged_in = check_login_status(page)
        if logged_in:
            _output({"logged_in": True}, exit_code=0)
        else:
            from chrome_launcher import has_display

            method = "qrcode" if has_display() else "phone"
            hint = (
                "请运行 login（二维码）完成登录"
                if method == "qrcode"
                else "请运行 send-code --phone <手机号>（手机验证码）完成登录"
            )
            _output(
                {"logged_in": False, "login_method": method, "hint": hint},
                exit_code=1,
            )
    finally:
        browser.close_page(page)
        browser.close()


def cmd_search_feeds(args: argparse.Namespace) -> None:
    """搜索 Feeds，支持筛选和时间过滤。"""
    from xhs.search import search_feeds_with_count
    from xhs.types import FilterOption

    time_start_sec: int | None = None
    time_end_sec: int | None = None
    need_time_filter = False

    if getattr(args, "time_start", None):
        try:
            time_start_sec = int(
                datetime.fromisoformat(args.time_start).replace(tzinfo=UTC).timestamp()
            )
            need_time_filter = True
        except ValueError:
            _output(
                {"success": False, "error": f"--time-start 格式无效: {args.time_start}"},
                exit_code=2,
            )
    if getattr(args, "time_end", None):
        try:
            time_end_sec = int(
                datetime.fromisoformat(args.time_end).replace(tzinfo=UTC).timestamp()
            ) + 86399
            need_time_filter = True
        except ValueError:
            _output(
                {"success": False, "error": f"--time-end 格式无效: {args.time_end}"},
                exit_code=2,
            )

    # 自动推断平台筛选器
    auto_publish_time = args.publish_time or ""
    if need_time_filter and not auto_publish_time:
        now_sec = int(datetime.now(tz=UTC).timestamp())
        earliest_sec = time_start_sec if time_start_sec is not None else time_end_sec
        if earliest_sec is not None:
            age_days = (now_sec - earliest_sec) / 86400
            if age_days <= 1:
                auto_publish_time = "一天内"
            elif age_days <= 7:
                auto_publish_time = "一周内"
            else:
                auto_publish_time = "半年内"

    auto_sort_by = args.sort_by or ""
    if need_time_filter and not auto_sort_by:
        auto_sort_by = "最新"

    filter_opt = FilterOption(
        sort_by=auto_sort_by,
        note_type=args.note_type or "",
        publish_time=auto_publish_time,
        search_scope=args.search_scope or "",
        location=args.location or "",
    )

    count: int = getattr(args, "count", 20) or 20
    if need_time_filter:
        search_count = min(count * 10, 200)
    else:
        search_count = min(int(count * 1.5) + 5, 60)

    browser, page = _connect(args)
    try:
        candidate_feeds = search_feeds_with_count(
            page, args.keyword, search_count, filter_opt
        )

        if need_time_filter:
            filtered_feeds = []
            for feed in candidate_feeds:
                if len(filtered_feeds) >= count:
                    break
                if not feed.id or feed.model_type == "rec_query":
                    continue
                publish_sec = feed.note_card.publish_time
                if publish_sec == 0:
                    continue
                in_range = True
                if time_start_sec is not None and publish_sec < time_start_sec:
                    in_range = False
                if time_end_sec is not None and publish_sec > time_end_sec:
                    in_range = False
                if in_range:
                    filtered_feeds.append(feed)
            feeds = filtered_feeds
        else:
            feeds = [
                f
                for f in candidate_feeds
                if f.id and f.model_type != "rec_query"
            ][:count]

        _output({"feeds": [f.to_dict() for f in feeds], "count": len(feeds)})
    finally:
        browser.close()


def cmd_get_feed_detail(args: argparse.Namespace) -> None:
    """获取 Feed 详情（正文 + 评论）。"""
    from xhs.feed_detail import get_feed_detail
    from xhs.types import CommentLoadConfig

    config = CommentLoadConfig(
        click_more_replies=args.click_more_replies,
        max_replies_threshold=args.max_replies_threshold,
        max_comment_items=args.max_comment_items,
        scroll_speed=args.scroll_speed,
    )

    browser, page = _connect(args)
    try:
        detail = get_feed_detail(
            page,
            args.feed_id,
            args.xsec_token,
            load_all_comments=args.load_all_comments,
            config=config,
        )
        _output(detail.to_dict())
    finally:
        browser.close()


def cmd_close_browser(args: argparse.Namespace) -> None:
    """关闭当前浏览器 tab 并断开 CDP 连接。"""
    from chrome_launcher import ensure_chrome, has_display
    from xhs.cdp import Browser

    if not ensure_chrome(port=args.port, headless=not has_display()):
        _output({"success": False, "error": "Chrome 未启动"}, exit_code=2)

    browser = Browser(host=args.host, port=args.port)
    browser.connect()
    page = browser.get_existing_page()
    if page:
        browser.close_page(page)
    browser.close()
    _output({"success": True, "message": "已关闭浏览器 tab"})


# ========== argparse 注册 ==========


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="xhs-content-reader",
        description="小红书内容读取 CLI（精简版）",
    )
    parser.add_argument(
        "--host", default="127.0.0.1", help="Chrome 调试主机 (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--port", type=int, default=9222, help="Chrome 调试端口 (default: 9222)"
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # check-login
    sub = subparsers.add_parser("check-login", help="检查登录状态")
    sub.set_defaults(func=cmd_check_login)

    # search-feeds
    sub = subparsers.add_parser("search-feeds", help="搜索 Feeds")
    sub.add_argument("--keyword", required=True, help="搜索关键词")
    sub.add_argument("--sort-by", help="排序: 综合|最新|最多点赞|最多评论|最多收藏")
    sub.add_argument("--note-type", help="类型: 不限|视频|图文")
    sub.add_argument("--publish-time", help="时间: 不限|一天内|一周内|半年内")
    sub.add_argument("--search-scope", help="范围: 不限|已看过|未看过|已关注")
    sub.add_argument("--location", help="位置: 不限|同城|附近")

    def _count_type(value: str) -> int:
        v = int(value)
        if v < 1 or v > 200:
            raise argparse.ArgumentTypeError(
                f"--count 必须在 1~200 之间，当前值: {v}"
            )
        return v

    sub.add_argument(
        "--count",
        type=_count_type,
        default=20,
        metavar="COUNT",
        help="返回帖子数量上限 (1~200, default: 20)",
    )
    sub.add_argument("--time-start", help="发布时间起点（ISO8601，如 2024-01-01）")
    sub.add_argument("--time-end", help="发布时间终点（ISO8601，如 2024-01-31）")
    sub.set_defaults(func=cmd_search_feeds)

    # get-feed-detail
    sub = subparsers.add_parser("get-feed-detail", help="获取 Feed 详情")
    sub.add_argument("--feed-id", required=True, help="Feed ID")
    sub.add_argument("--xsec-token", required=True, help="xsec_token")
    sub.add_argument(
        "--load-all-comments",
        action="store_true",
        help="加载全部评论（默认仅 top 30）",
    )
    sub.add_argument(
        "--click-more-replies", action="store_true", help="展开更多回复"
    )
    sub.add_argument(
        "--max-replies-threshold", type=int, default=10, help="展开回复数阈值"
    )
    sub.add_argument(
        "--max-comment-items",
        type=int,
        default=0,
        help="最大评论数上限（默认 30）",
    )
    sub.add_argument(
        "--scroll-speed", default="normal", help="滚动速度: slow|normal|fast"
    )
    sub.set_defaults(func=cmd_get_feed_detail)

    # close-browser
    sub = subparsers.add_parser("close-browser", help="关闭浏览器 tab")
    sub.set_defaults(func=cmd_close_browser)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
