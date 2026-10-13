"""
美团登录检测步骤。

连接浏览器打开账户页面检测登录状态，
主进程同步执行（detached=False），返回 logged_in=True/False。

- run()          — 业务逻辑函数，签名与 login/search 一致
- create_step()  — 工厂函数，返回配置好的 BrowserStep 实例
"""

from services.browser.cdp_client import CdpBrowser, CdpPage

from services.browser_pipeline import BrowserStep
from services.browser_pipeline.browser_step import WorkerResult

MEITUAN_ACCOUNT_URL = "https://i.meituan.com/mttouch/page/account"

_LOGGED_IN_INDICATORS = ["我的", "账户", "余额", "订单", "收藏"]


def _is_logged_in(current_url: str, page_text: str) -> bool:
    """检测是否已登录美团。"""
    if "mttouch/page/account" not in current_url:
        return False
    text_lower = page_text.lower()
    return any(indicator in text_lower for indicator in _LOGGED_IN_INDICATORS)


def run(browser: CdpBrowser, page: CdpPage, params: dict) -> WorkerResult:
    """检测美团登录状态。

    打开账户页面，检测页面内容判断是否已登录，立即返回结果。
    """
    print(f"🔍 打开美团账户页面: {MEITUAN_ACCOUNT_URL}", flush=True)
    page.goto(MEITUAN_ACCOUNT_URL, timeout=15000, wait_until="domcontentloaded")
    page.wait_for_timeout(2000)

    current_url = page.url
    page_text = page.inner_text("body")
    logged_in = _is_logged_in(current_url, page_text)

    if logged_in:
        print(f"✅ 已登录美团 (URL: {current_url})", flush=True)
        return WorkerResult(
            status="success",
            message="已登录美团",
            data={"logged_in": True, "url": current_url},
        )

    print(f"⚠️  未登录美团 (URL: {current_url})", flush=True)
    return WorkerResult(
        status="success",
        message="未登录美团",
        data={"logged_in": False, "url": current_url},
    )


def create_step() -> BrowserStep:
    """构建登录检测步骤（主进程同步执行，不打断）。"""
    return BrowserStep(
        name="check_login",
        run_fn=run,
        detached=False,
        device_name="iphone14",
        timeout=30,
    )
