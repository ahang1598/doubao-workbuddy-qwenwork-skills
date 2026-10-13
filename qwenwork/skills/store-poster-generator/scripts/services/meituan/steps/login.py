"""
美团登录步骤。

打开美团登录页面，轮询等待用户完成登录操作。
主进程启动后立即打断 pipeline，由 agent 在用户登录后重新调用 check_login 确认。

- run()          — 业务逻辑函数，在 detached worker 中执行
- create_step()  — 工厂函数，返回配置好的 BrowserStep 实例
"""

from services.browser.cdp_client import CdpBrowser, CdpPage

from services.browser_pipeline import BrowserStep
from services.browser_pipeline.browser_step import WorkerResult

MEITUAN_ACCOUNT_URL = "https://i.meituan.com/mttouch/page/account"

_LOGGED_IN_INDICATORS = ["我的", "账户", "余额", "订单", "收藏"]

_DEFAULT_TIMEOUT = 120


def _is_logged_in(current_url: str, page_text: str) -> bool:
    """检测是否已登录美团。"""
    if "mttouch/page/account" not in current_url:
        return False
    text_lower = page_text.lower()
    return any(indicator in text_lower for indicator in _LOGGED_IN_INDICATORS)


def run(browser: CdpBrowser, page: CdpPage, params: dict) -> WorkerResult:
    """在子进程中打开登录页面并等待用户完成登录。

    打开美团账户页面，轮询检测用户是否完成登录，超时后自动退出。
    """
    timeout_seconds = params.get("timeout", _DEFAULT_TIMEOUT)

    print(f"🌐 打开美团登录页面: {MEITUAN_ACCOUNT_URL}", flush=True)
    page.goto(MEITUAN_ACCOUNT_URL, timeout=15000, wait_until="domcontentloaded")
    # page.wait_for_timeout(2000)

    current_url = page.url
    print(f"📍 当前 URL: {current_url}", flush=True)
    print("⏳ 等待用户完成登录...", flush=True)

    timeout_ms = timeout_seconds * 1000
    poll_interval_ms = 3000
    elapsed_ms = 0

    while elapsed_ms < timeout_ms:
        page.wait_for_timeout(poll_interval_ms)
        elapsed_ms += poll_interval_ms

        try:
            current_url = page.url
            page_text = page.inner_text("body")

            if _is_logged_in(current_url, page_text):
                print(f"✅ 登录成功！当前 URL: {current_url}", flush=True)
                return WorkerResult(
                    status="success",
                    message="美团登录成功",
                    data={"final_url": current_url},
                )
        except Exception as error:
            print(f"⚠️  检测登录状态时出错: {error}", flush=True)

        remaining_seconds = (timeout_ms - elapsed_ms) // 1000
        print(f"   ⏳ 等待中... (剩余 {remaining_seconds}s)", flush=True)

    print(f"⏰ 登录超时 ({timeout_seconds}s)", flush=True)
    return WorkerResult(
        status="timeout",
        message=f"登录超时 ({timeout_seconds}s)，未检测到登录成功",
    )


def create_step(*, timeout: int = 120) -> BrowserStep:
    """构建登录步骤（detached，打断 pipeline 等待用户操作）。"""
    return BrowserStep(
        name="login",
        run_fn=run,
        device_name="iphone14",
        detached=True,
        timeout=timeout,
        abort_after_launch=True,
        abort_message="登录页面已打开 (PID={pid})，请在浏览器中完成登录后再继续",
        extra_params={"timeout": timeout},
    )
