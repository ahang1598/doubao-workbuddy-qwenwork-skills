"""
浏览器连接封装。

通过 CDP 连接浏览器，支持单例复用。
纯标准库实现
"""

from contextlib import contextmanager

from services.browser.cdp_client import CdpBrowser, connect_over_cdp
from services.browser.cdp_launcher import launch_cdp_browser


def launch_browser(*, headless: bool = False) -> CdpBrowser:
    """通过 CDP 连接浏览器（单例模式，复用已有实例）。

    底层调用 launch_cdp_browser() 启动/复用独立的 Chrome 子进程，
    然后通过 CDP WebSocket 连接，主进程退出后 Chrome 仍然存活。

    Returns:
        CdpBrowser 实例
    """
    cdp_info = launch_cdp_browser(headless=headless)
    ws_endpoint = cdp_info["ws_endpoint"]

    print(f"🔗 通过 CDP 连接浏览器 (ws={ws_endpoint})...")
    browser = connect_over_cdp(ws_endpoint)
    print(f"✅ 浏览器连接成功 (version: {browser.version})")

    return browser


@contextmanager
def managed_browser(*, headless: bool = False):
    """上下文管理器：自动在退出时关闭浏览器连接。

    用法::

        with managed_browser() as browser:
            page = browser.new_page()
            ...
        # 退出 with 块时自动关闭连接
    """
    browser = launch_browser(headless=headless)
    try:
        yield browser
    finally:
        browser.close()
        print("🔒 managed_browser 退出，浏览器连接已关闭")