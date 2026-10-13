"""
浏览器底层服务：提供 Chrome/Chromium 的查找、下载、CDP 启动/停止、浏览器连接。

纯标准库 CDP 实现

公开 API：
- check_chrome() / download_chrome() / ensure_chrome() — Chrome 查找与下载
- launch_cdp_browser() / stop_cdp_browser() — CDP 服务启动与停止
- launch_browser() — 通过 CDP 连接浏览器
- CdpBrowser / CdpPage / connect_over_cdp — CDP 客户端封装

Pipeline 和 DetachedWorker 相关能力已迁移至 services.browser_pipeline 包。
"""

from services.browser.finder import check_chrome, download_chrome, ensure_chrome
from services.browser.cdp_launcher import launch_cdp_browser, stop_cdp_browser
from services.browser.browser import launch_browser
from services.browser.cdp_client import CdpBrowser, CdpPage, connect_over_cdp

__all__ = [
    "check_chrome",
    "download_chrome",
    "ensure_chrome",
    "launch_cdp_browser",
    "stop_cdp_browser",
    "launch_browser",
    "CdpBrowser",
    "CdpPage",
    "connect_over_cdp",
]
