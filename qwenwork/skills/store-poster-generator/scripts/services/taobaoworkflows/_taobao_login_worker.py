"""
淘宝登录验证独立子进程脚本。

由 taobao_login.py 服务通过 utils.process.launch_detached_script 启动。
通过 CDP 连接已有浏览器，打开淘宝登录页，
以非无头模式等待用户完成登录操作，超时后自动退出。

纯标准库 CDP 实现，无需 Playwright。

用法（由服务层自动调用，不需要手动执行）：
    python _taobao_login_worker.py --ws-endpoint ws://127.0.0.1:9222/devtools/browser/xxx
    python _taobao_login_worker.py --ws-endpoint ws://... --timeout 60
"""

import argparse
import sys

from services.browser.cdp_client import connect_over_cdp

_TAOBAO_LOGIN_URL = "https://login.taobao.com/havanaone/login/login.htm"

def main() -> None:
    parser = argparse.ArgumentParser(description="淘宝登录验证子进程")
    parser.add_argument("--ws-endpoint", required=True, help="CDP WebSocket endpoint")
    parser.add_argument("--timeout", type=int, default=30, help="登录超时秒数（默认 30s）")
    args = parser.parse_args()

    timeout_ms = args.timeout * 1000

    browser = connect_over_cdp(args.ws_endpoint)

    try:
        print(f"🔗 连接浏览器 (ws={args.ws_endpoint})...", flush=True)
        print(f"✅ 浏览器连接成功 (version: {browser.version})", flush=True)

        page = browser.new_page()
        print(f"🌐 打开淘宝登录页: {_TAOBAO_LOGIN_URL}", flush=True)
        page.goto(_TAOBAO_LOGIN_URL, timeout=15000)
        print("⏳ 等待登录完成...", flush=True)

        # 等待 URL 变化（登录成功后会跳转离开登录页）
        try:
            page.wait_for_url(
                lambda url: "login.taobao.com" not in url,
                timeout=timeout_ms,
            )
            final_url = page.url
            print(f"✅ 登录成功！跳转到: {final_url}", flush=True)
        except Exception:
            print(f"⏰ 登录超时（{args.timeout}s），未检测到登录成功", flush=True)

        page.close()
        print("✅ 页面已关闭", flush=True)

    except Exception as error:
        print(f"❌ 淘宝登录验证异常: {error}", file=sys.stderr, flush=True)
        sys.exit(1)
    finally:
        browser.close()

if __name__ == "__main__":
    main()