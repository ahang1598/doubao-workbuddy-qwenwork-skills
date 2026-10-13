"""
美团搜索步骤。

包含两部分：
- run()             — 业务逻辑函数，在 detached worker 中执行
- create_step()     — 工厂函数，返回配置好的 BrowserStep 实例
"""

from urllib.parse import quote

from services.browser.cdp_client import CdpBrowser, CdpPage

from services.browser_pipeline import (
    BrowserStep, PipelineContext, StepResult, StepStatus,
)
from services.browser_pipeline.browser_step import WorkerResult

DEFAULT_CITY = "hangzhou"

MEITUAN_SEARCH_URL_TEMPLATE = (
    "https://i.meituan.com/s/{city}-{keyword}"
    "?cevent=imt%2Fsearch%2Fhot%2F{keyword_encoded}"
)


def run(browser: CdpBrowser, page: CdpPage, params: dict) -> WorkerResult:
    """在子进程中执行的美团搜索逻辑。"""
    keyword = params.get("keyword")
    city = params.get("city", DEFAULT_CITY)

    if not keyword:
        return WorkerResult(status="failed", message="未提供搜索关键词 (keyword)")

    keyword_encoded = quote(keyword, safe="")
    search_url = MEITUAN_SEARCH_URL_TEMPLATE.format(
        city=city, keyword=keyword, keyword_encoded=keyword_encoded,
    )

    print(f"🔎 搜索关键词: {keyword}", flush=True)
    print(f"🏙️  城市: {city}", flush=True)
    print(f"🌐 跳转搜索页面: {search_url}", flush=True)

    page.goto(search_url, timeout=15000, wait_until="domcontentloaded")
    page.wait_for_timeout(3000)

    current_url = page.url
    page_title = page.title()

    print(f"📍 搜索结果页 URL: {current_url}", flush=True)
    print(f"📄 页面标题: {page_title}", flush=True)

    return WorkerResult(
        status="success",
        message=f"搜索完成: {keyword}",
        data={
            "keyword": keyword,
            "city": city,
            "search_url": current_url,
            "page_title": page_title,
        },
    )


def _validate_keyword(context: PipelineContext) -> StepResult | None:
    """搜索前校验：keyword 必须存在。"""
    if not context.get("keyword"):
        return StepResult(
            step_name="search",
            status=StepStatus.FAILED,
            message="未提供搜索关键词 (keyword)",
        )
    return None


def create_step() -> BrowserStep:
    """构建搜索步骤。"""
    return BrowserStep(
        name="search",
        run_fn=run,
        device_name="iphone14",
        timeout=30,
        params_builder=lambda ctx: {
            "keyword": ctx.get("keyword", ""),
            "city": ctx.get("city", DEFAULT_CITY),
        },
        validate=_validate_keyword,
    )
