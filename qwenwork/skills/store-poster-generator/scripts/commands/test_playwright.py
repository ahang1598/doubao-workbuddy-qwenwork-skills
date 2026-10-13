"""
test-browser 命令（CLI 入口）

验证浏览器 CDP 连通性。
"""

from utils.envs import IS_IN_DWS
from services.browser.browser import launch_browser

DISABLED = IS_IN_DWS


def register(subparsers) -> None:
    """Register the test-playwright subcommand (保留命令名兼容)."""
    parser = subparsers.add_parser("test-playwright", help="验证浏览器 CDP 连通性")
    parser.set_defaults(handler=run)


def run(_args) -> None:
    """Execute the test-playwright command."""
    print("🚀 启动浏览器 CDP 连通性测试...")

    browser = launch_browser()

    page = browser.new_page()
    print("✅ 新页面创建成功")

    page.goto("https://www.baidu.com", timeout=15000)
    title = page.title()
    print(f"✅ 页面加载成功, title: {title}")

    page.wait_for_timeout(1000)
    page.close()
    browser.close()
    print("✅ 测试完成")