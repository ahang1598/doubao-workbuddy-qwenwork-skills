#!/usr/bin/env python3
"""浏览器 CDP 连通性测试脚本：有头模式"""

import subprocess
import tempfile
import time

from services.browser.cdp_client import CdpBrowser


def _find_chrome() -> str:
    """查找系统 Chrome 可执行路径。"""
    import os
    import platform
    import shutil

    system = platform.system()

    if system == "Darwin":
        mac_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        if os.path.exists(mac_path):
            return mac_path

    if system == "Linux":
        for name in ("google-chrome-stable", "google-chrome", "chromium-browser", "chromium"):
            path = shutil.which(name)
            if path:
                return path

    raise FileNotFoundError("未找到系统 Chrome，请手动指定路径")


def test_browser_connectivity():
    print("🚀 启动浏览器 CDP 连通性测试...")

    chrome_path = _find_chrome()
    print(f"🔍 找到 Chrome: {chrome_path}")

    user_data_dir = tempfile.mkdtemp(prefix="chrome_cdp_test_")
    port = 9333

    chrome_process = subprocess.Popen(
        [
            chrome_path,
            f"--remote-debugging-port={port}",
            f"--user-data-dir={user_data_dir}",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-extensions",
            "about:blank",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        import json
        import urllib.request

        # 等待 CDP 就绪
        ws_endpoint = None
        for _ in range(30):
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=2) as resp:
                    data = json.loads(resp.read().decode())
                    ws_endpoint = data.get("webSocketDebuggerUrl")
                    if ws_endpoint:
                        break
            except Exception:
                pass
            time.sleep(0.3)

        if not ws_endpoint:
            raise RuntimeError("CDP 端口未就绪")

        browser = CdpBrowser(ws_endpoint)
        print(f"✅ 浏览器连接成功 (version: {browser.version})")

        page = browser.new_page()
        print("✅ 新页面创建成功")

        page.goto("https://www.baidu.com", timeout=15000)
        title = page.title()
        print(f"✅ 页面加载成功, title: {title}")

        page.wait_for_timeout(2000)

        page.screenshot(path="/tmp/cdp_test.png")
        print("✅ 截图保存至 /tmp/cdp_test.png")

        page.close()
        browser.close()
        print("✅ 浏览器连接已关闭")

    finally:
        chrome_process.terminate()
        chrome_process.wait(timeout=5)

    print("\n🎉 浏览器 CDP 连通性测试全部通过！")


if __name__ == "__main__":
    test_browser_connectivity()