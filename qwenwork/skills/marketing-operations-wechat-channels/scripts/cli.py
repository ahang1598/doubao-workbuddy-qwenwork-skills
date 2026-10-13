# -*- coding: utf-8 -*-
"""微信视频号自动化 CLI 入口。"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime

logger = logging.getLogger(__name__)


def _output(data: dict, exit_code: int = 0) -> None:
    """输出 JSON 结果并退出。"""
    print(json.dumps(data, ensure_ascii=False, indent=2))
    if exit_code != 0:
        sys.exit(exit_code)


def _get_browser(args: argparse.Namespace):
    """获取 Browser 实例。"""
    from wc.cdp import Browser

    browser = Browser(host=args.host, port=args.port)
    browser.connect()
    return browser


def _get_page(args: argparse.Namespace):
    """获取或创建 Page 实例。"""
    browser = _get_browser(args)
    page = browser.get_existing_page()
    if not page:
        page = browser.new_page("about:blank")
    return browser, page


# ========== 认证命令 ==========


def cmd_check_login(args: argparse.Namespace) -> None:
    """检查登录状态。"""
    from wc.login import check_login_status

    browser, page = _get_page(args)
    try:
        logged_in = check_login_status(page)
        if logged_in:
            _output({"logged_in": True, "message": "已登录"})
        else:
            _output({"logged_in": False, "message": "未登录，请扫码登录"}, exit_code=1)
    finally:
        browser.close()


def cmd_login(args: argparse.Namespace) -> None:
    """获取登录二维码。"""
    from wc.login import fetch_qrcode, save_qrcode_to_file

    browser, page = _get_page(args)
    try:
        src, already_logged_in = fetch_qrcode(page)
        if already_logged_in:
            _output({"logged_in": True, "message": "已登录，无需重复登录"})
            return

        result: dict = {"logged_in": False, "qrcode_src": src}

        # 尝试保存为文件
        try:
            filepath = save_qrcode_to_file(src)
            result["qrcode_file"] = filepath
            result["message"] = f"请使用微信扫描二维码登录。二维码已保存到: {filepath}"
        except ValueError:
            result["message"] = "请在浏览器中扫描二维码登录"

        result["next_step"] = "扫码完成后执行 check-scan-status"
        _output(result)
    finally:
        # 不关闭 browser，保持页面状态等待扫码
        pass


def cmd_check_scan_status(args: argparse.Namespace) -> None:
    """检查扫码后的页面状态。"""
    from wc.login import check_scan_status

    browser, page = _get_page(args)
    try:
        result = check_scan_status(page)
        if result.get("logged_in"):
            _output(result)
        elif result.get("waiting_scan"):
            _output(result, exit_code=1)
        else:
            _output(result)
    finally:
        browser.close()


def cmd_delete_cookies(args: argparse.Namespace) -> None:
    """删除 cookies。"""
    from wc.cookies import delete_cookies, get_cookies_file_path

    path = get_cookies_file_path(args.account)
    delete_cookies(path)
    _output({"success": True, "message": "Cookies 已删除"})


def cmd_close_browser(args: argparse.Namespace) -> None:
    """关闭浏览器 tab。"""
    try:
        browser, page = _get_page(args)
        browser.close_page(page)
        browser.close()
        _output({"success": True, "message": "浏览器 tab 已关闭"})
    except Exception as e:
        _output({"success": False, "error": str(e)}, exit_code=2)


# ========== 发布命令 ==========


def cmd_publish_video(args: argparse.Namespace) -> None:
    """发布视频（一步完成）。"""
    from wc.login import check_login_status
    from wc.publish_video import publish_video_content
    from wc.types import PublishVideoContent

    browser, page = _get_page(args)
    try:
        # 检查登录
        if not check_login_status(page):
            _output({"success": False, "error": "未登录"}, exit_code=1)
            return

        # 解析参数
        publish_date = None
        if args.schedule:
            publish_date = datetime.strptime(args.schedule, "%Y-%m-%d %H:%M")

        content = PublishVideoContent(
            title=_read_file_content(args.title_file),
            video_path=args.video,
            tags=args.tags or [],
            publish_date=publish_date,
            category=args.category,
            is_original=args.original,
            is_draft=args.draft,
        )

        publish_video_content(page, content)

        status = "草稿" if content.is_draft else "已发布"
        _output({
            "success": True,
            "title": content.title,
            "video": content.video_path,
            "status": status,
        })
    finally:
        browser.close()


def cmd_fill_publish_video(args: argparse.Namespace) -> None:
    """填写视频发布表单（不发布）。"""
    from wc.login import check_login_status
    from wc.publish_video import fill_publish_video_form
    from wc.types import PublishVideoContent

    browser, page = _get_page(args)
    try:
        if not check_login_status(page):
            _output({"success": False, "error": "未登录"}, exit_code=1)
            return

        publish_date = None
        if args.schedule:
            publish_date = datetime.strptime(args.schedule, "%Y-%m-%d %H:%M")

        content = PublishVideoContent(
            title=_read_file_content(args.title_file),
            video_path=args.video,
            tags=args.tags or [],
            publish_date=publish_date,
            category=args.category,
            is_original=args.original,
            is_draft=False,
        )

        fill_publish_video_form(page, content)

        _output({
            "success": True,
            "title": content.title,
            "video": content.video_path,
            "status": "表单已填写，等待确认发布",
            "next_step": "确认内容无误后执行 click-publish 或 save-draft",
        })
    finally:
        # 不关闭 browser，保持页面状态
        pass


def cmd_click_publish(args: argparse.Namespace) -> None:
    """点击发布按钮。"""
    from wc.publish_video import click_publish_button

    browser, page = _get_page(args)
    try:
        click_publish_button(page)
        _output({"success": True, "message": "视频已发布"})
    finally:
        browser.close()


def cmd_save_draft(args: argparse.Namespace) -> None:
    """保存为草稿。"""
    from wc.publish_video import click_save_draft

    browser, page = _get_page(args)
    try:
        click_save_draft(page)
        _output({"success": True, "message": "已保存为草稿"})
    finally:
        browser.close()


# ========== 图文发布命令 ==========

def cmd_publish_image(args: argparse.Namespace) -> None:
    """发布图文（一步完成）。"""
    from wc.login import check_login_status
    from wc.publish_image import publish_image_content
    from wc.types import PublishImageContent

    browser, page = _get_page(args)
    try:
        if not check_login_status(page):
            _output({"success": False, "error": "未登录"}, exit_code=1)
            return

        publish_date = None
        if args.schedule:
            publish_date = datetime.strptime(args.schedule, "%Y-%m-%d %H:%M")

        content = PublishImageContent(
            title=_read_file_content(args.title_file) if args.title_file else "",
            description=_read_file_content(args.desc_file) if args.desc_file else "",
            image_paths=args.images,
            tags=args.tags or [],
            publish_date=publish_date,
            is_draft=args.draft,
        )

        publish_image_content(page, content)

        status = "草稿" if content.is_draft else "已发布"
        _output({
            "success": True,
            "title": content.title,
            "images": content.image_paths,
            "image_count": len(content.image_paths),
            "status": status,
        })
    finally:
        browser.close()

def cmd_fill_publish_image(args: argparse.Namespace) -> None:
    """填写图文发布表单（不发布）。"""
    from wc.login import check_login_status
    from wc.publish_image import fill_publish_image_form
    from wc.types import PublishImageContent

    browser, page = _get_page(args)
    try:
        if not check_login_status(page):
            _output({"success": False, "error": "未登录"}, exit_code=1)
            return

        publish_date = None
        if args.schedule:
            publish_date = datetime.strptime(args.schedule, "%Y-%m-%d %H:%M")

        content = PublishImageContent(
            title=_read_file_content(args.title_file) if args.title_file else "",
            description=_read_file_content(args.desc_file) if args.desc_file else "",
            image_paths=args.images,
            tags=args.tags or [],
            publish_date=publish_date,
            is_draft=False,
        )

        fill_publish_image_form(page, content)

        _output({
            "success": True,
            "title": content.title,
            "images": content.image_paths,
            "image_count": len(content.image_paths),
            "status": "表单已填写，等待确认发布",
            "next_step": "确认内容无误后执行 click-publish 或 save-draft",
        })
    finally:
        # 不关闭 browser，保持页面状态
        pass

# ========== 工具函数 ==========


def _read_file_content(filepath: str) -> str:
    """读取文件内容。"""
    with open(filepath, encoding="utf-8") as f:
        return f.read().strip()


# ========== 参数解析 ==========


def build_parser() -> argparse.ArgumentParser:
    """构建 CLI 参数解析器。"""
    parser = argparse.ArgumentParser(
        prog="wc-cli",
        description="微信视频号自动化 CLI",
    )

    # 全局选项
    parser.add_argument(
        "--host", default="127.0.0.1", help="Chrome 调试主机 (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--port", type=int, default=9222, help="Chrome 调试端口 (default: 9222)"
    )
    parser.add_argument("--account", default="", help="账号名称")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # check-login
    sub = subparsers.add_parser("check-login", help="检查登录状态")
    sub.set_defaults(func=cmd_check_login)

    # login
    sub = subparsers.add_parser(
        "login",
        help="获取登录二维码，输出后退出，用户扫码后执行 check-scan-status",
    )
    sub.set_defaults(func=cmd_login)

    # check-scan-status
    sub = subparsers.add_parser(
        "check-scan-status",
        help="检查扫码后的页面状态",
    )
    sub.set_defaults(func=cmd_check_scan_status)

    # delete-cookies
    sub = subparsers.add_parser("delete-cookies", help="删除 cookies")
    sub.set_defaults(func=cmd_delete_cookies)

    # close-browser
    sub = subparsers.add_parser("close-browser", help="关闭浏览器 tab")
    sub.set_defaults(func=cmd_close_browser)

    # publish-video（一步发布）
    sub = subparsers.add_parser("publish-video", help="发布视频（一步完成）")
    sub.add_argument("--title-file", required=True, help="标题文件路径")
    sub.add_argument("--video", required=True, help="视频文件路径")
    sub.add_argument("--tags", nargs="*", help="话题标签")
    sub.add_argument("--original", action="store_true", help="声明原创")
    sub.add_argument("--category", help="原创类型（如：生活、科技）")
    sub.add_argument("--schedule", help="定时发布（格式：YYYY-MM-DD HH:MM）")
    sub.add_argument("--draft", action="store_true", help="保存为草稿")
    sub.set_defaults(func=cmd_publish_video)

    # fill-publish-video（只填写表单，不发布）
    sub = subparsers.add_parser("fill-publish-video", help="填写视频表单（不发布）")
    sub.add_argument("--title-file", required=True, help="标题文件路径")
    sub.add_argument("--video", required=True, help="视频文件路径")
    sub.add_argument("--tags", nargs="*", help="话题标签")
    sub.add_argument("--original", action="store_true", help="声明原创")
    sub.add_argument("--category", help="原创类型")
    sub.add_argument("--schedule", help="定时发布（格式：YYYY-MM-DD HH:MM）")
    sub.set_defaults(func=cmd_fill_publish_video)

    # click-publish
    sub = subparsers.add_parser("click-publish", help="点击发布按钮")
    sub.set_defaults(func=cmd_click_publish)

    # save-draft
    sub = subparsers.add_parser("save-draft", help="保存为草稿")
    sub.set_defaults(func=cmd_save_draft)

    # publish-image（一步发布图文）
    sub = subparsers.add_parser("publish-image", help="发布图文（一步完成）")
    sub.add_argument("--title-file", help="标题文件路径（可选，22字符内）")
    sub.add_argument("--desc-file", help="描述文件路径（可选，1000字符内）")
    sub.add_argument("--images", nargs="+", required=True, help="图片文件路径（最多18张）")
    sub.add_argument("--tags", nargs="*", help="话题标签")
    sub.add_argument("--schedule", help="定时发布（格式：YYYY-MM-DD HH:MM）")
    sub.add_argument("--draft", action="store_true", help="保存为草稿")
    sub.set_defaults(func=cmd_publish_image)

    # fill-publish-image（只填写图文表单，不发布）
    sub = subparsers.add_parser("fill-publish-image", help="填写图文表单（不发布）")
    sub.add_argument("--title-file", help="标题文件路径（可选，22字符内）")
    sub.add_argument("--desc-file", help="描述文件路径（可选，1000字符内）")
    sub.add_argument("--images", nargs="+", required=True, help="图片文件路径（最多18张）")
    sub.add_argument("--tags", nargs="*", help="话题标签")
    sub.add_argument("--schedule", help="定时发布（格式：YYYY-MM-DD HH:MM）")
    sub.set_defaults(func=cmd_fill_publish_image)

    return parser


def main() -> None:
    """CLI 入口。"""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = build_parser()
    args = parser.parse_args()

    try:
        args.func(args)
    except Exception as e:
        logger.error("执行失败: %s", e, exc_info=True)
        _output({"success": False, "error": str(e)}, exit_code=2)


if __name__ == "__main__":
    main()
