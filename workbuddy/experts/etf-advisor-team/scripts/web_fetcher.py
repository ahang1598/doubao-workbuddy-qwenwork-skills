#!/usr/bin/env python3
"""
web_fetcher.py — 通用网页抓取脚本（Playwright 无头浏览器）

功能：
  - 真实 Chromium 无头浏览器渲染（完整JS执行）
  - HTML → Markdown 高质量转换
  - Cloudflare 基础 JS Challenge 自动等待
  - 自定义 UA / Cookie / Header / Proxy
  - 内容提取（CSS选择器 / 正则 / 全文）
  - 截图调试
  - JSON / Markdown / 纯文本多格式输出
  - 自动重试与降级

依赖：
  pip install playwright beautifulsoup4 html2text
  playwright install chromium

用法：
  python web_fetcher.py --url "https://example.com"
  python web_fetcher.py --url "https://example.com" --selector "article" --output result.md
  python web_fetcher.py --url "https://example.com" --json --wait 5
  python web_fetcher.py --url "https://example.com" --screenshot shot.png
  python web_fetcher.py --url "https://example.com" --headers '{"Referer":"https://google.com"}'
"""

# --- UTF-8 bootstrap (auto-injected, idempotent) ---
import os as _bootstrap_os, sys as _bootstrap_sys
_bootstrap_dir = _bootstrap_os.path.dirname(_bootstrap_os.path.abspath(__file__))
if _bootstrap_dir not in _bootstrap_sys.path:
    _bootstrap_sys.path.insert(0, _bootstrap_dir)
try:
    from _utf8_bootstrap import enable_utf8_io as _bootstrap_enable
    _bootstrap_enable()
except Exception:
    pass
# --- end UTF-8 bootstrap ---


import argparse
import json
import os
import re
import sys
import time
import traceback
from typing import Optional
from urllib.parse import urlparse

# ---------------------------------------------------------------------------
# 依赖检测与友好提示
# ---------------------------------------------------------------------------
_MISSING = []
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PwTimeout
except ImportError:
    _MISSING.append("playwright")

try:
    from bs4 import BeautifulSoup, Tag
except ImportError:
    _MISSING.append("beautifulsoup4")

try:
    import html2text as _h2t
except ImportError:
    _MISSING.append("html2text")

if _MISSING:
    print(f"[web_fetcher] 缺少依赖: {', '.join(_MISSING)}", file=sys.stderr)
    print("请执行: pip install " + " ".join(_MISSING), file=sys.stderr)
    if "playwright" not in _MISSING:
        print("然后执行: playwright install chromium", file=sys.stderr)
    sys.exit(1)


# ═══════════════════════════════════════════════════════════════════════════
# 常量 & 配置
# ═══════════════════════════════════════════════════════════════════════════

# 默认 User-Agent（模拟最新版 Chrome，降低反爬触发概率）
DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

# 默认视口
DEFAULT_VIEWPORT = {"width": 1920, "height": 1080}

# 默认超时（毫秒）
DEFAULT_TIMEOUT = 30_000      # 页面导航超时（30s足够绝大多数页面）
DEFAULT_WAIT_AFTER = 1.5      # 页面加载后额外等待秒数（让JS/AJAX跑完）

# 重试配置
MAX_RETRIES = 2
RETRY_DELAY = 1.5  # 秒（首次失败后快速重试）

# Cloudflare 挑战页面关键词
CF_CHALLENGE_MARKERS = [
    "checking your browser",
    "just a moment",
    "please wait",
    "cf-browser-verification",
    "challenge-platform",
    "turnstile",
]

# 需要移除的干扰元素（CSS选择器）
NOISE_SELECTORS = [
    "script", "style", "noscript", "iframe",
    "nav", "footer", "header",
    ".sidebar", ".advertisement", ".ad-container", ".cookie-banner",
    "#cookie-consent", ".social-share", ".related-posts",
    "[role='complementary']", "[role='navigation']",
    ".nav-bar", ".footer", ".header",
]


# ═══════════════════════════════════════════════════════════════════════════
# HTML → Markdown 转换器
# ═══════════════════════════════════════════════════════════════════════════

def _create_h2t_converter() -> _h2t.HTML2Text:
    """创建配置好的 html2text 转换器"""
    h = _h2t.HTML2Text()
    h.ignore_links = False
    h.ignore_images = False
    h.ignore_tables = False
    h.ignore_emphasis = False
    h.body_width = 0           # 不自动换行
    h.unicode_snob = True      # 使用Unicode字符
    h.skip_internal_links = True
    h.inline_links = True
    h.protect_links = False
    h.wrap_links = False
    h.single_line_break = False
    h.mark_code = True
    h.default_image_alt = ""
    return h


def html_to_markdown(html: str, base_url: str = "") -> str:
    """
    将 HTML 转换为干净的 Markdown。
    
    流程：
    1. BeautifulSoup 清理噪音元素
    2. html2text 转换为 Markdown
    3. 后处理：清理多余空行、修复格式
    """
    # --- Step 1: BeautifulSoup 清理 ---
    soup = BeautifulSoup(html, "html.parser")
    
    # 移除噪音元素
    for selector in NOISE_SELECTORS:
        for el in soup.select(selector):
            el.decompose()
    
    # 移除隐藏元素
    for el in soup.find_all(style=re.compile(r"display\s*:\s*none", re.I)):
        el.decompose()
    for el in soup.find_all(attrs={"hidden": True}):
        el.decompose()
    for el in soup.find_all(attrs={"aria-hidden": "true"}):
        # 保留图标等小元素，只移除大块内容
        if el.string and len(el.get_text(strip=True)) > 50:
            el.decompose()
    
    cleaned_html = str(soup)
    
    # --- Step 2: html2text 转换 ---
    converter = _create_h2t_converter()
    if base_url:
        converter.baseurl = base_url
    
    markdown = converter.handle(cleaned_html)
    
    # --- Step 3: 后处理 ---
    # 清理连续空行（最多保留2个）
    markdown = re.sub(r'\n{4,}', '\n\n\n', markdown)
    # 清理行首行尾空白
    lines = [line.rstrip() for line in markdown.split('\n')]
    markdown = '\n'.join(lines)
    # 清理首尾空白
    markdown = markdown.strip()
    
    return markdown


# ═══════════════════════════════════════════════════════════════════════════
# CSS 选择器提取
# ═══════════════════════════════════════════════════════════════════════════

def extract_by_selector(html: str, selector: str) -> str:
    """使用 CSS 选择器从 HTML 中提取内容"""
    soup = BeautifulSoup(html, "html.parser")
    elements = soup.select(selector)
    if not elements:
        return ""
    # 合并所有匹配元素
    parts = []
    for el in elements:
        parts.append(str(el))
    return "\n".join(parts)


# ═══════════════════════════════════════════════════════════════════════════
# 表格提取（增强）
# ═══════════════════════════════════════════════════════════════════════════

def extract_tables_as_markdown(html: str) -> str:
    """从 HTML 中提取所有表格并转换为 Markdown 表格"""
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all("table")
    if not tables:
        return ""
    
    result_parts = []
    for idx, table in enumerate(tables):
        rows = table.find_all("tr")
        if not rows:
            continue
        
        md_rows = []
        max_cols = 0
        for row in rows:
            cells = row.find_all(["th", "td"])
            cell_texts = [c.get_text(strip=True).replace("|", "\\|") for c in cells]
            max_cols = max(max_cols, len(cell_texts))
            md_rows.append(cell_texts)
        
        if not md_rows or max_cols == 0:
            continue
        
        # 对齐列数
        for r in md_rows:
            while len(r) < max_cols:
                r.append("")
        
        lines = []
        # 表头
        lines.append("| " + " | ".join(md_rows[0]) + " |")
        lines.append("| " + " | ".join(["---"] * max_cols) + " |")
        # 数据行
        for r in md_rows[1:]:
            lines.append("| " + " | ".join(r) + " |")
        
        if len(tables) > 1:
            result_parts.append(f"### 表格 {idx + 1}\n\n" + "\n".join(lines))
        else:
            result_parts.append("\n".join(lines))
    
    return "\n\n".join(result_parts)


# ═══════════════════════════════════════════════════════════════════════════
# Cloudflare 检测与等待
# ═══════════════════════════════════════════════════════════════════════════

def _is_cf_challenge(page_content: str, page_title: str) -> bool:
    """检测页面是否为 Cloudflare 挑战页"""
    text_lower = (page_content + " " + page_title).lower()
    return any(marker in text_lower for marker in CF_CHALLENGE_MARKERS)


def _wait_for_cf_challenge(page, max_wait: int = 15) -> bool:
    """
    等待 Cloudflare JS Challenge 自动完成。
    返回 True 如果挑战被通过，False 如果超时。
    """
    start = time.time()
    while time.time() - start < max_wait:
        try:
            content = page.content()
            title = page.title()
            if not _is_cf_challenge(content, title):
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


# ═══════════════════════════════════════════════════════════════════════════
# 核心：页面抓取
# ═══════════════════════════════════════════════════════════════════════════

class FetchResult:
    """抓取结果封装"""
    def __init__(self):
        self.url: str = ""
        self.final_url: str = ""
        self.title: str = ""
        self.status_code: int = 0
        self.html: str = ""
        self.markdown: str = ""
        self.tables_markdown: str = ""
        self.extracted: str = ""      # CSS选择器提取结果
        self.screenshot_path: str = ""
        self.success: bool = False
        self.error: str = ""
        self.elapsed: float = 0.0
        self.cf_challenged: bool = False
        self.redirect_chain: list = []
    
    def to_dict(self) -> dict:
        d = {
            "success": self.success,
            "url": self.url,
            "final_url": self.final_url,
            "title": self.title,
            "status_code": self.status_code,
            "elapsed_seconds": round(self.elapsed, 2),
        }
        if self.error:
            d["error"] = self.error
        if self.cf_challenged:
            d["cloudflare_challenged"] = True
        if self.redirect_chain:
            d["redirect_chain"] = self.redirect_chain
        if self.markdown:
            d["content_markdown"] = self.markdown
        if self.tables_markdown:
            d["tables_markdown"] = self.tables_markdown
        if self.extracted:
            d["extracted"] = self.extracted
        if self.screenshot_path:
            d["screenshot"] = self.screenshot_path
        return d


def fetch_page(
    url: str,
    *,
    selector: Optional[str] = None,
    wait_seconds: float = DEFAULT_WAIT_AFTER,
    wait_for_selector: Optional[str] = None,
    timeout_ms: int = DEFAULT_TIMEOUT,
    user_agent: str = DEFAULT_UA,
    headers: Optional[dict] = None,
    cookies: Optional[list] = None,
    proxy: Optional[str] = None,
    viewport: Optional[dict] = None,
    screenshot_path: Optional[str] = None,
    extract_tables: bool = False,
    block_resources: Optional[list] = None,
    js_code: Optional[str] = None,
) -> FetchResult:
    """
    使用 Playwright 无头浏览器抓取页面。
    
    参数：
        url:               目标URL
        selector:          CSS选择器，只提取匹配的内容
        wait_seconds:      页面加载后额外等待秒数
        wait_for_selector: 等待指定CSS选择器出现后才认为加载完成
        timeout_ms:        页面导航超时（毫秒）
        user_agent:        自定义UA
        headers:           自定义HTTP头
        cookies:           自定义Cookie列表 [{"name":"x","value":"y","domain":"..."}]
        proxy:             代理地址 "http://host:port"
        viewport:          视口 {"width":1920,"height":1080}
        screenshot_path:   截图保存路径
        extract_tables:    是否额外提取表格为Markdown格式
        block_resources:   要阻止的资源类型 ["image","font","media"]
        js_code:           页面加载后执行的JS代码
    """
    result = FetchResult()
    result.url = url
    start_time = time.time()
    
    pw = None
    browser = None
    
    try:
        pw = sync_playwright().start()
        
        # 浏览器启动参数
        launch_args = {
            "headless": True,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-infobars",
                "--window-size=1920,1080",
                "--disable-extensions",
            ],
        }
        
        # 代理设置
        if proxy:
            launch_args["proxy"] = {"server": proxy}
        
        browser = pw.chromium.launch(**launch_args)
        
        # 上下文（context）设置
        ctx_args = {
            "user_agent": user_agent,
            "viewport": viewport or DEFAULT_VIEWPORT,
            "ignore_https_errors": True,         # 忽略SSL证书错误
            "locale": "zh-CN",
            "timezone_id": "Asia/Shanghai",
            "java_script_enabled": True,
        }
        
        # 额外 headers
        if headers:
            ctx_args["extra_http_headers"] = headers
        
        context = browser.new_context(**ctx_args)
        
        # 注入反检测脚本（在每个页面创建前执行）
        context.add_init_script("""
            // 隐藏 webdriver 标志
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            // 覆盖 chrome 属性
            window.chrome = { runtime: {} };
            // 覆盖 permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
            // 覆盖 plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
            // 覆盖 languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['zh-CN', 'zh', 'en-US', 'en'],
            });
        """)
        
        # 设置 cookies
        if cookies:
            context.add_cookies(cookies)
        
        page = context.new_page()
        page.set_default_timeout(timeout_ms)
        
        # 资源拦截（可加速加载、节省带宽）
        if block_resources:
            def route_handler(route):
                if route.request.resource_type in block_resources:
                    route.abort()
                else:
                    route.continue_()
            page.route("**/*", route_handler)
        
        # 追踪重定向
        redirects = []
        def on_response(response):
            if 300 <= response.status < 400:
                redirects.append({
                    "url": response.url,
                    "status": response.status,
                    "location": response.headers.get("location", ""),
                })
        page.on("response", on_response)
        
        # ---- 导航 ----
        response = page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        
        if response:
            result.status_code = response.status
        result.redirect_chain = redirects
        
        # 等待网络空闲（最多再等 wait_seconds 秒 + 5秒余量）
        try:
            page.wait_for_load_state("networkidle", timeout=int(wait_seconds * 1000 + 5000))
        except PwTimeout:
            pass  # 超时没关系，页面可能持续有请求
        
        # 额外等待（让延迟加载/AJAX完成）
        if wait_seconds > 0:
            page.wait_for_timeout(int(wait_seconds * 1000))
        
        # 等待特定选择器
        if wait_for_selector:
            try:
                page.wait_for_selector(wait_for_selector, timeout=10000)
            except PwTimeout:
                pass  # 选择器未出现，但继续处理
        
        # Cloudflare 检测
        page_content = page.content()
        page_title = page.title()
        if _is_cf_challenge(page_content, page_title):
            result.cf_challenged = True
            if _wait_for_cf_challenge(page, max_wait=20):
                # 挑战通过，重新获取内容
                page_content = page.content()
                page_title = page.title()
            else:
                result.error = "Cloudflare challenge not resolved within timeout"
        
        # 执行自定义 JS
        if js_code:
            try:
                page.evaluate(js_code)
                page.wait_for_timeout(1000)
                page_content = page.content()
            except Exception as e:
                result.error = f"JS execution error: {e}"
        
        # 记录最终URL和标题
        result.final_url = page.url
        result.title = page.title()
        result.html = page_content
        
        # ---- 内容提取 ----
        base_url = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
        
        if selector:
            # CSS选择器提取
            extracted_html = extract_by_selector(page_content, selector)
            if extracted_html:
                result.extracted = html_to_markdown(extracted_html, base_url)
                result.markdown = result.extracted
            else:
                result.error = f"选择器 '{selector}' 未匹配到任何元素，返回全文"
                result.markdown = html_to_markdown(page_content, base_url)
        else:
            result.markdown = html_to_markdown(page_content, base_url)
        
        # 表格提取
        if extract_tables:
            result.tables_markdown = extract_tables_as_markdown(page_content)
        
        # 截图
        if screenshot_path:
            page.screenshot(path=screenshot_path, full_page=True)
            result.screenshot_path = os.path.abspath(screenshot_path)
        
        result.success = True
        
    except PwTimeout as e:
        result.error = f"页面加载超时: {e}"
    except Exception as e:
        result.error = f"抓取失败: {type(e).__name__}: {e}"
        traceback.print_exc(file=sys.stderr)
    finally:
        try:
            if browser:
                browser.close()
            if pw:
                pw.stop()
        except Exception:
            pass
    
    result.elapsed = time.time() - start_time
    return result


def fetch_with_retry(retries: int = MAX_RETRIES, **kwargs) -> FetchResult:
    """带重试的抓取"""
    last_result = None
    for attempt in range(retries + 1):
        result = fetch_page(**kwargs)
        if result.success:
            return result
        last_result = result
        if attempt < retries:
            print(f"[web_fetcher] 第{attempt+1}次失败: {result.error}，{RETRY_DELAY}秒后重试...",
                  file=sys.stderr)
            time.sleep(RETRY_DELAY)
    return last_result


# ═══════════════════════════════════════════════════════════════════════════
# CLI 接口
# ═══════════════════════════════════════════════════════════════════════════

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="web_fetcher",
        description="通用网页抓取脚本（Playwright 无头浏览器）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  # 基本抓取 → 输出 Markdown 到终端
  python web_fetcher.py --url "https://reuters.com"

  # CSS 选择器提取
  python web_fetcher.py --url "https://news.com" --selector "article.main"

  # 保存为文件 + 截图
  python web_fetcher.py --url "https://example.com" --output result.md --screenshot page.png

  # JSON 格式输出（适合程序调用）
  python web_fetcher.py --url "https://api.example.com/page" --json

  # 自定义等待、Headers、代理
  python web_fetcher.py --url "https://slow-site.com" --wait 10 \\
      --headers '{"Referer":"https://google.com"}' \\
      --proxy "http://127.0.0.1:7890"

  # 阻止图片/字体加载（加速）
  python web_fetcher.py --url "https://heavy-site.com" --block-resources image,font

  # 提取表格
  python web_fetcher.py --url "https://data-site.com/table" --tables

  # 等待特定元素出现
  python web_fetcher.py --url "https://spa-app.com" --wait-for "#data-loaded"

  # 页面加载后执行JS（如点击"加载更多"）
  python web_fetcher.py --url "https://site.com" --js "document.querySelector('.load-more').click()"
        """,
    )
    
    # 必需参数
    p.add_argument("--url", required=True, help="目标 URL")
    
    # 内容提取
    p.add_argument("--selector", "-s", help="CSS 选择器，只提取匹配元素的内容")
    p.add_argument("--tables", action="store_true", help="额外提取所有表格为 Markdown 格式")
    
    # 等待控制
    p.add_argument("--wait", type=float, default=DEFAULT_WAIT_AFTER,
                   help=f"页面加载后额外等待秒数（默认 {DEFAULT_WAIT_AFTER}）")
    p.add_argument("--wait-for", dest="wait_for", help="等待指定 CSS 选择器出现")
    p.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT // 1000,
                   help=f"页面导航超时秒数（默认 {DEFAULT_TIMEOUT // 1000}）")
    
    # 输出控制
    p.add_argument("--output", "-o", help="输出文件路径（默认输出到终端）")
    p.add_argument("--json", action="store_true", dest="json_output",
                   help="JSON 格式输出")
    p.add_argument("--screenshot", help="截图保存路径 (.png)")
    p.add_argument("--html", action="store_true", help="额外输出原始 HTML")
    
    # 浏览器配置
    p.add_argument("--ua", default=DEFAULT_UA, help="自定义 User-Agent")
    p.add_argument("--headers", help='自定义 HTTP Headers（JSON格式）')
    p.add_argument("--cookies", help='自定义 Cookies（JSON数组格式）')
    p.add_argument("--proxy", help="代理地址，如 http://127.0.0.1:7890")
    p.add_argument("--viewport", help='视口大小（JSON），如 {"width":1280,"height":720}')
    
    # 性能优化
    p.add_argument("--block-resources", dest="block_resources",
                   help="阻止加载的资源类型（逗号分隔）：image,font,media,stylesheet")
    
    # JS 执行
    p.add_argument("--js", help="页面加载后执行的 JavaScript 代码")
    
    # 重试
    p.add_argument("--retries", type=int, default=MAX_RETRIES,
                   help=f"失败重试次数（默认 {MAX_RETRIES}）")
    
    # 调试
    p.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    
    return p


def main():
    parser = build_parser()
    args = parser.parse_args()
    
    # 解析 JSON 参数
    headers = None
    if args.headers:
        try:
            headers = json.loads(args.headers)
        except json.JSONDecodeError:
            print("[web_fetcher] --headers 参数不是有效的JSON", file=sys.stderr)
            sys.exit(1)
    
    cookies = None
    if args.cookies:
        try:
            cookies = json.loads(args.cookies)
        except json.JSONDecodeError:
            print("[web_fetcher] --cookies 参数不是有效的JSON", file=sys.stderr)
            sys.exit(1)
    
    viewport = None
    if args.viewport:
        try:
            viewport = json.loads(args.viewport)
        except json.JSONDecodeError:
            print("[web_fetcher] --viewport 参数不是有效的JSON", file=sys.stderr)
            sys.exit(1)
    
    block_resources = None
    if args.block_resources:
        block_resources = [r.strip() for r in args.block_resources.split(",")]
    
    if args.verbose:
        print(f"[web_fetcher] 抓取: {args.url}", file=sys.stderr)
        print(f"[web_fetcher] 等待: {args.wait}s | 超时: {args.timeout}s | 重试: {args.retries}",
              file=sys.stderr)
    
    # ---- 执行抓取 ----
    result = fetch_with_retry(
        retries=args.retries,
        url=args.url,
        selector=args.selector,
        wait_seconds=args.wait,
        wait_for_selector=args.wait_for,
        timeout_ms=args.timeout * 1000,
        user_agent=args.ua,
        headers=headers,
        cookies=cookies,
        proxy=args.proxy,
        viewport=viewport,
        screenshot_path=args.screenshot,
        extract_tables=args.tables,
        block_resources=block_resources,
        js_code=args.js,
    )
    
    if args.verbose:
        print(f"[web_fetcher] 耗时: {result.elapsed:.2f}s | 状态: {result.status_code} | "
              f"成功: {result.success}", file=sys.stderr)
        if result.cf_challenged:
            print("[web_fetcher] ⚠ 检测到 Cloudflare 挑战页", file=sys.stderr)
        if result.redirect_chain:
            print(f"[web_fetcher] 重定向链: {len(result.redirect_chain)} 次", file=sys.stderr)
        if result.error:
            print(f"[web_fetcher] 错误: {result.error}", file=sys.stderr)
    
    # ---- 输出 ----
    if args.json_output:
        output_data = result.to_dict()
        if args.html:
            output_data["html"] = result.html
        output_text = json.dumps(output_data, ensure_ascii=False, indent=2)
    else:
        parts = []
        if result.title:
            parts.append(f"# {result.title}\n")
        if result.final_url and result.final_url != result.url:
            parts.append(f"> 最终URL: {result.final_url}\n")
        if result.error and not result.success:
            parts.append(f"> ⚠ 错误: {result.error}\n")
        
        if result.markdown:
            parts.append(result.markdown)
        
        if args.tables and result.tables_markdown:
            parts.append("\n---\n## 表格数据\n\n" + result.tables_markdown)
        
        if args.html and result.html:
            parts.append("\n---\n## 原始 HTML\n\n```html\n" + result.html[:50000] + "\n```")
        
        output_text = "\n\n".join(parts)
    
    # 写入文件或输出到终端
    if args.output:
        output_dir = os.path.dirname(args.output)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output_text)
        print(f"[web_fetcher] ✅ 已保存到: {os.path.abspath(args.output)}", file=sys.stderr)
    else:
        print(output_text)
    
    # 退出码
    sys.exit(0 if result.success else 1)


# ═══════════════════════════════════════════════════════════════════════════
# 程序式调用接口（供其他脚本 import）
# ═══════════════════════════════════════════════════════════════════════════

def fetch(url: str, **kwargs) -> FetchResult:
    """
    程序式调用接口。
    
    用法：
        from web_fetcher import fetch
        result = fetch("https://example.com", selector="article", wait_seconds=3)
        print(result.markdown)
        print(result.success)
    """
    return fetch_with_retry(retries=kwargs.pop("retries", MAX_RETRIES), url=url, **kwargs)


if __name__ == "__main__":
    main()
