#!/usr/bin/env python3
# encoding: utf-8
"""
小红书Cookie获取脚本 - 基于Playwright自动化浏览器
功能：启动有头浏览器引导用户登录，通过 context.cookies() 获取包括 httpOnly 的完整Cookie
"""

import argparse
import json
import os
import sys
import time


def _check_login_state(page, context):
    """
    检查用户是否已登录小红书。
    采用双重检测策略，避免误判（未登录时 web_session 可能存在空值/占位值）：
    1. 页面DOM检测：通过 JS 检查页面中的用户信息（window.__INITIAL_STATE__ 等）
    2. Cookie有效性检测：web_session 值必须有实质内容（非空且长度≥10）
    """
    # 策略1：通过页面JS检测用户登录信息
    try:
        has_user = page.evaluate("""() => {
            // 方法a: 检查 __INITIAL_STATE__ 中的用户信息
            //        userInfo._value.redId 字段不存在表示游客（未登录），该字段存在表示已登录
            try {
                const state = window.__INITIAL_STATE__;
                if (state && state.user && state.user.userInfo && state.user.userInfo._value && state.user.userInfo._value.redId) {
                    return true;
                }
            } catch(e) {}
            return false;
        }""")
        if has_user:
            # 页面确认已登录，再验证Cookie有效性
            cookies = context.cookies()
            web_session = next(
                (c["value"] for c in cookies if c["name"] == "web_session"), "")
            if web_session and len(web_session) >= 10:
                return True
    except Exception:
        pass

    return False


def get_cookies_via_playwright(output_path=None, timeout=300):
    """
    启动Playwright有头浏览器，引导用户登录小红书，获取完整Cookie（包括httpOnly）
    :param output_path: Cookie文件输出路径，默认为 SKILL_DIR/cookies.json
    :param timeout: 登录等待超时时间（秒），默认300秒（5分钟）
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print(json.dumps({
            "success": False,
            "error": "playwright未安装，请运行: pip3 install playwright && playwright install chromium"
        }, ensure_ascii=False))
        sys.exit(1)

    # 默认输出到 SKILL_DIR/cookies.json
    if not output_path:
        skill_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), '..'))
        output_path = os.path.join(skill_dir, 'cookies.json')

    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("🔐 小红书Cookie获取工具 (Playwright)")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("即将打开浏览器，请在浏览器中完成小红书登录。")
    print("支持扫码登录、手机号登录、微信登录。")
    print(f"等待登录超时: {timeout}秒")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    with sync_playwright() as p:
        # 启动有头浏览器（用户可交互）
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/122.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        # 访问小红书首页
        page.goto("https://www.xiaohongshu.com", wait_until="domcontentloaded")

        # 等待用户登录：通过页面DOM和Cookie双重检测
        # 仅靠 web_session Cookie 存在不可靠——未登录时也可能有该Cookie（空值/占位值）
        # 必须通过页面用户信息确认真正登录成功
        print("\n⏳ 等待登录中... 请在浏览器中完成登录操作")
        start_time = time.time()
        logged_in = False

        while time.time() - start_time < timeout:
            logged_in = _check_login_state(page, context)
            if logged_in:
                break
            time.sleep(2)

        if not logged_in:
            # 最后一次尝试：导航到explore页触发Cookie和页面状态刷新
            print("⏳ 尝试导航到发现页触发登录态更新...")
            page.goto("https://www.xiaohongshu.com/explore",
                      wait_until="domcontentloaded")
            time.sleep(3)
            logged_in = _check_login_state(page, context)

        if not logged_in:
            browser.close()
            print(json.dumps({
                "success": False,
                "error": f"登录超时（{timeout}秒），未检测到 web_session Cookie"
            }, ensure_ascii=False))
            sys.exit(1)

        # 登录成功，提取Cookie
        all_cookies = context.cookies()

        # 过滤小红书相关域名，转换为 cookie 字符串
        xhs_domains = [".xiaohongshu.com", "xiaohongshu.com",
                       ".edith.xiaohongshu.com"]
        xhs_cookies = [
            c for c in all_cookies
            if any(c.get("domain", "").endswith(d) for d in xhs_domains)
        ]

        # 构建Cookie字符串
        cookie_str = "; ".join(
            f'{c["name"]}={c["value"]}' for c in xhs_cookies)

        # 检查关键字段：web_session 必须有实质内容
        cookie_dict = {c["name"]: c["value"] for c in xhs_cookies}
        missing = []
        web_session_value = cookie_dict.get("web_session", "")
        if not web_session_value or len(web_session_value) < 10:
            missing.append(f"web_session (值为空或过短: {len(web_session_value)}字符)")
        if "a1" not in cookie_dict:
            missing.append("a1")

        # 关闭浏览器
        browser.close()

        if missing:
            print(json.dumps({
                "success": False,
                "error": f"Cookie缺少关键字段: {', '.join(missing)}",
                "hint": "请确保已完全登录小红书后重试"
            }, ensure_ascii=False))
            sys.exit(1)

        # 保存Cookie
        cookie_data = {"cookies": cookie_str}
        os.makedirs(os.path.dirname(
            os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(cookie_data, f, ensure_ascii=False, indent=2)

        result = {
            "success": True,
            "cookie_file": os.path.abspath(output_path),
            "cookie_count": len(xhs_cookies),
            "web_session_len": len(web_session_value),
            "has_a1": "a1" in cookie_dict
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        print(f"\n✅ Cookie已保存至: {os.path.abspath(output_path)}")
        return result


def main():
    parser = argparse.ArgumentParser(description="小红书Cookie获取工具 (Playwright)")
    parser.add_argument("--output", "-o", default=None,
                        help="Cookie文件输出路径（默认 SKILL_DIR/cookies.json）")
    parser.add_argument("--timeout", "-t", type=int, default=300,
                        help="登录等待超时秒数（默认300）")
    args = parser.parse_args()
    get_cookies_via_playwright(output_path=args.output, timeout=args.timeout)


if __name__ == "__main__":
    main()
