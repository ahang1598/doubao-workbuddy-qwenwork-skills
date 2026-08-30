"""百家号图文提取器。

支持从百家号文章链接（baijiahao.baidu.com/s?id=xxxxx）提取：
- 文章标题、作者、发布时间、正文文本
- 文章内嵌图片（直接下载原图）
- 图片 OCR 文字识别
- 生成 Markdown 分析报告

无需登录，无需浏览器，直接 HTTP 请求页面 HTML 解析。
"""

from __future__ import annotations

import hashlib
import logging
import re
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

from .path_guard import safe_output_dir

logger = logging.getLogger(__name__)

_DEFAULT_OUTPUT_DIR = Path.home() / ".content-breakdown" / "output" / "baijiahao"

_REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://baijiahao.baidu.com/",
}

_IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp")


def extract_article(
    article_url: str,
    output_dir: str | None = None,
    download_images: bool = True,
    ocr_images: bool = True,
    page_html: str | None = None,
) -> dict[str, Any]:
    """从百家号文章链接提取内容。

    优先使用 Agent 通过 browser_use 获取的页面 HTML（page_html 参数），
    如果未提供则尝试 HTTP 直接请求（可能被百度安全验证拦截），
    HTTP 失败时自动降级到 CDP 浏览器。

    Args:
        article_url: 百家号文章链接（baijiahao.baidu.com/s?id=xxxxx）。
        output_dir: 输出目录（默认 ~/.content-breakdown/output/baijiahao）。
        download_images: 是否下载文章图片（默认 True）。
        ocr_images: 是否对图片做 OCR 文字识别（默认 True）。
        page_html: Agent 通过 browser_use 获取的页面 HTML（优先使用）。

    Returns:
        {
            "success": bool,
            "article_id": str,
            "title": str,
            "author": str,
            "publish_time": str,
            "content": str,
            "content_file": str | None,
            "image_urls": list[str],
            "image_files": list[str],
            "image_texts": list[dict],
            "report_file": str | None,
            "error": str | None,
        }
    """
    out_dir = safe_output_dir(output_dir) if output_dir else _DEFAULT_OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    article_id = _extract_article_id(article_url)

    result: dict[str, Any] = {
        "success": False,
        "article_id": article_id,
        "title": "",
        "author": "",
        "publish_time": "",
        "content": "",
        "content_file": None,
        "image_urls": [],
        "image_files": [],
        "image_texts": [],
        "report_file": None,
        "error": None,
    }

    # 获取文章 HTML
    # 优先级：page_html 参数（browser_use）> HTTP 直接请求 > CDP 浏览器降级
    html = ""
    session = requests.Session()
    session.headers.update(_REQUEST_HEADERS)

    if page_html:
        logger.info("使用 browser_use 提供的页面 HTML（%d 字符）", len(page_html))
        html = page_html
    else:
        # 尝试 HTTP 直接请求（百家号大概率被安全验证拦截）
        try:
            resp = session.get(article_url, timeout=30)
            if resp.status_code == 200:
                resp.encoding = resp.apparent_encoding or "utf-8"
                html = resp.text
        except Exception as request_error:
            logger.warning("HTTP 请求失败: %s", request_error)

        # 检测反爬拦截（百度安全验证）
        if not html or "百度安全验证" in html or "网络不给力" in html:
            logger.info("检测到百度安全验证拦截，尝试 CDP 浏览器降级")
            cdp_html = _fetch_via_cdp(article_url)
            if cdp_html:
                html = cdp_html
            else:
                result["error"] = "百度安全验证拦截，CDP 浏览器降级也失败。请通过 browser_use 获取页面 HTML 后传入 --page-html-file 参数"
                return result

    # 解析文章内容
    try:
        article_data = _parse_article_html(html, article_url)
    except Exception as parse_error:
        result["error"] = f"HTML 解析失败: {parse_error}"
        return result

    result["title"] = article_data.get("title", "")
    result["author"] = article_data.get("author", "")
    result["publish_time"] = article_data.get("publish_time", "")
    result["content"] = article_data.get("content", "")
    result["image_urls"] = article_data.get("image_urls", [])
    result["success"] = True

    logger.info(
        "文章解析成功: title=%s, 图片=%d 张, 正文=%d 字",
        result["title"][:30] if result["title"] else "(无标题)",
        len(result["image_urls"]),
        len(result["content"]),
    )

    # 保存正文
    if result["content"]:
        content_file = out_dir / f"{article_id}_content.txt"
        header = f"# {result['title']}\n\n" if result["title"] else ""
        meta = ""
        if result["author"]:
            meta += f"**作者**：{result['author']}\n"
        if result["publish_time"]:
            meta += f"**发布时间**：{result['publish_time']}\n"
        if meta:
            meta += "\n---\n\n"
        content_file.write_text(header + meta + result["content"], encoding="utf-8")
        result["content_file"] = str(content_file)

    # 下载图片
    if download_images and result["image_urls"]:
        images_dir = out_dir / f"{article_id}_images"
        images_dir.mkdir(parents=True, exist_ok=True)
        downloaded, failed = _download_article_images(
            session=session,
            image_urls=result["image_urls"],
            save_dir=images_dir,
            article_id=article_id,
        )
        result["image_files"] = downloaded
        if failed:
            logger.warning("有 %d 张图片下载失败", len(failed))
        logger.info("图片下载完成: %d/%d 张", len(downloaded), len(result["image_urls"]))

    # 图片 OCR
    if ocr_images and result.get("image_files"):
        logger.info("开始图片 OCR 识别...")
        from extractor.wechat_extractor import _ocr_image_files
        image_texts = _ocr_image_files(result["image_files"])
        result["image_texts"] = image_texts
        total_chars = sum(len(item.get("text", "")) for item in image_texts)
        logger.info("OCR 完成: %d 张图片，共 %d 字", len(image_texts), total_chars)

    # 生成 Markdown 报告
    report_file = _save_as_markdown(
        article_id=article_id,
        title=result["title"],
        author=result["author"],
        publish_time=result["publish_time"],
        content=result["content"],
        image_texts=result["image_texts"],
        output_dir=out_dir,
    )
    result["report_file"] = report_file

    return result


# ──────────────────────────────── HTML 解析 ────────────────────────────────


def _parse_article_html(html: str, article_url: str) -> dict[str, Any]:
    """解析百家号文章 HTML，提取标题、正文、图片 URL 等。

    优先使用 BeautifulSoup，降级使用正则表达式。
    """
    try:
        from bs4 import BeautifulSoup
        return _parse_with_beautifulsoup(html, article_url)
    except ImportError:
        logger.info("BeautifulSoup 未安装，使用正则表达式解析")
        return _parse_with_regex(html, article_url)


def _parse_with_beautifulsoup(html: str, article_url: str) -> dict[str, Any]:
    """使用 BeautifulSoup 解析百家号文章 HTML。"""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")

    # 标题：多种选择器降级
    title = ""
    title_tag = (
        soup.find("div", class_="article-title")
        or soup.find("h2", class_="article-title")
        or soup.find("div", class_="article-title-text")
    )
    if title_tag:
        title = title_tag.get_text(strip=True)
    if not title:
        og_title = soup.find("meta", property="og:title")
        if og_title:
            title = og_title.get("content", "")
    if not title:
        title_el = soup.find("title")
        if title_el:
            raw_title = title_el.get_text(strip=True)
            title = re.sub(r"[_\-]\s*百家号.*$", "", raw_title).strip()

    # 作者
    author = ""
    author_tag = (
        soup.find("div", class_="author-name")
        or soup.find("span", class_="author-name")
        or soup.find("p", class_="author-name")
    )
    if author_tag:
        author = author_tag.get_text(strip=True)
    if not author:
        author_meta = soup.find("meta", {"name": "author"})
        if author_meta:
            author = author_meta.get("content", "")

    # 发布时间
    publish_time = ""
    time_tag = (
        soup.find("span", class_="publish-time")
        or soup.find("span", class_="date")
        or soup.find("div", class_="article-source")
    )
    if time_tag:
        time_text = time_tag.get_text(strip=True)
        date_match = re.search(r"\d{4}[-/]\d{2}[-/]\d{2}[\s\d:]*", time_text)
        if date_match:
            publish_time = date_match.group().strip()
        else:
            publish_time = time_text

    # 正文内容
    content = ""
    image_urls: list[str] = []

    # 选择器优先级：固定 class 名 → 语义标签
    content_div = (
        soup.find("div", class_="article-content")
        or soup.find("div", id="article")
        or soup.find("div", class_="index-module_articleWrap")
        or soup.find("article")
    )

    # 百家号新版使用混淆 class 名，固定选择器失效时用启发式方法
    if not content_div:
        candidate_divs = []
        sidebar_keywords = ["换一换", "相关推荐", "作者最新文章", "百度首页"]
        for div in soup.find_all("div"):
            text = div.get_text(strip=True)
            if len(text) > 80 and not any(kw in text for kw in sidebar_keywords):
                child_divs = div.find_all("div", recursive=False)
                if child_divs:
                    child_classes = [" ".join(c.get("class", [])) for c in child_divs if c.get("class")]
                    unique_classes = set(child_classes)
                    has_paragraph_pattern = (
                        len(child_divs) >= 3
                        and len(unique_classes) <= 3
                        and any(child_classes.count(cls) >= 3 for cls in unique_classes)
                    )
                    if has_paragraph_pattern:
                        candidate_divs.append((len(text), div))

        candidate_divs.sort(key=lambda x: x[0], reverse=True)
        for _, div in candidate_divs:
            div_text = div.get_text(strip=True)
            if "百度首页" not in div_text and "登录" not in div_text:
                content_div = div
                logger.info("使用智能检测定位正文容器（class=%s, %d chars）",
                           " ".join(div.get("class", [])), len(div_text))
                break

    if content_div:
        # 提取图片 URL
        for img in content_div.find_all("img"):
            img_url = img.get("data-src") or img.get("src") or ""
            if img_url and img_url.startswith("http"):
                if _is_content_image(img_url):
                    image_urls.append(img_url)

        # 提取纯文本：优先取直接子 div 文本（百家号新版每段一个 div）
        noise_texts = {"举报/反馈", "举报", "反馈", "分享", "收藏", "关注", ""}
        paragraphs = []
        direct_children = content_div.find_all("div", recursive=False)
        if direct_children:
            for child in direct_children:
                text = child.get_text(strip=True)
                if text and text not in noise_texts:
                    paragraphs.append(text)

        # 降级：传统 <p>/<section> 标签
        if not paragraphs:
            for element in content_div.find_all(["p", "section", "h1", "h2", "h3", "h4"]):
                text = element.get_text(strip=True)
                if text and len(text) > 1 and text not in noise_texts:
                    paragraphs.append(text)

        # 最终降级：直接 get_text
        if not paragraphs:
            raw_text = content_div.get_text("\n", strip=True)
            paragraphs = [line for line in raw_text.splitlines()
                         if line.strip() and line.strip() not in noise_texts]

        content = "\n\n".join(paragraphs)
        image_urls = _deduplicate_urls(image_urls)

    # SSR JSON 数据降级
    if not content:
        ssr_data = _extract_ssr_data(html)
        if ssr_data:
            content = ssr_data.get("content", content)
            title = ssr_data.get("title", title) or title
            author = ssr_data.get("author", author) or author

    return {
        "title": title,
        "author": author,
        "publish_time": publish_time,
        "content": content,
        "image_urls": image_urls,
    }


def _parse_with_regex(html: str, article_url: str) -> dict[str, Any]:
    """使用正则表达式解析百家号文章 HTML（BeautifulSoup 不可用时的降级方案）。"""
    # 标题
    title = ""
    title_match = re.search(r'class="article-title"[^>]*>(.*?)</(?:div|h2)>', html, re.DOTALL)
    if title_match:
        title = re.sub(r"<[^>]+>", "", title_match.group(1)).strip()
    if not title:
        og_match = re.search(r'property="og:title"\s+content="([^"]+)"', html)
        if og_match:
            title = og_match.group(1)
    if not title:
        title_match = re.search(r"<title>(.*?)</title>", html, re.DOTALL)
        if title_match:
            title = re.sub(r"[_\-]\s*百家号.*$", "", title_match.group(1)).strip()

    # 作者
    author = ""
    author_match = re.search(r'class="author-name"[^>]*>(.*?)</(?:div|span|p)>', html, re.DOTALL)
    if author_match:
        author = re.sub(r"<[^>]+>", "", author_match.group(1)).strip()

    # 发布时间
    publish_time = ""
    time_match = re.search(r'class="publish-time"[^>]*>(.*?)</span>', html, re.DOTALL)
    if time_match:
        time_text = re.sub(r"<[^>]+>", "", time_match.group(1)).strip()
        date_match = re.search(r"\d{4}[-/]\d{2}[-/]\d{2}[\s\d:]*", time_text)
        if date_match:
            publish_time = date_match.group().strip()

    # 正文
    content = ""
    content_match = re.search(
        r'class="article-content"[^>]*>(.*?)</div>',
        html,
        re.DOTALL,
    )
    if content_match:
        raw_content = content_match.group(1)
        text = re.sub(r"<[^>]+>", "\n", raw_content)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        content = "\n\n".join(lines)

    # 图片 URL
    image_urls = []
    img_matches = re.findall(r'(?:data-src|src)="(https?://[^"]+(?:\.jpg|\.jpeg|\.png|\.webp)[^"]*)"', html)
    for img_url in img_matches:
        if _is_content_image(img_url):
            image_urls.append(img_url)
    image_urls = _deduplicate_urls(image_urls)

    return {
        "title": title,
        "author": author,
        "publish_time": publish_time,
        "content": content,
        "image_urls": image_urls,
    }


def _extract_ssr_data(html: str) -> dict[str, Any] | None:
    """尝试从页面 SSR JSON 数据中提取文章信息（百家号部分页面使用 SSR 渲染）。"""
    import json

    # 尝试匹配 window.__INITIAL_STATE__ 或类似的 SSR 数据
    patterns = [
        r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\})\s*;',
        r'window\.baijiahao\s*=\s*(\{.*?\})\s*;',
    ]
    for pattern in patterns:
        match = re.search(pattern, html, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1))
                article_info = data.get("articleDetail", {}).get("content", {})
                if not article_info:
                    article_info = data.get("article", {})
                if article_info:
                    # 正文可能是 HTML，需要清理
                    raw_content = article_info.get("content", "")
                    clean_content = re.sub(r"<[^>]+>", "\n", raw_content)
                    clean_lines = [line.strip() for line in clean_content.splitlines() if line.strip()]
                    return {
                        "title": article_info.get("title", ""),
                        "author": article_info.get("author", ""),
                        "content": "\n\n".join(clean_lines),
                    }
            except (json.JSONDecodeError, KeyError):
                continue
    return None


# ──────────────────────────────── 图片下载 ────────────────────────────────


def _download_article_images(
    session: requests.Session,
    image_urls: list[str],
    save_dir: Path,
    article_id: str,
) -> tuple[list[str], list[str]]:
    """批量下载文章图片，返回 (成功路径列表, 失败 URL 列表)。"""
    downloaded: list[str] = []
    failed: list[str] = []

    for index, image_url in enumerate(image_urls):
        try:
            url_hash = hashlib.sha256(image_url.encode()).hexdigest()[:12]
            ext = _detect_image_extension(image_url)
            filename = f"{article_id}_img_{index + 1:02d}_{url_hash}{ext}"
            filepath = save_dir / filename

            if filepath.exists() and filepath.stat().st_size > 0:
                downloaded.append(str(filepath))
                continue

            resp = session.get(image_url, timeout=30)
            if resp.status_code != 200:
                raise RuntimeError(f"下载失败 (status={resp.status_code})")

            filepath.write_bytes(resp.content)
            downloaded.append(str(filepath))
            logger.info("图片下载成功: %s", filename)

        except Exception as download_error:
            failed.append(image_url)
            logger.warning("图片下载失败 [%d]: %s", index + 1, download_error)

    return downloaded, failed


def _detect_image_extension(url: str) -> str:
    """从 URL 推断图片扩展名。"""
    parsed = urlparse(url)
    path = parsed.path.lower()
    for ext in _IMAGE_EXTENSIONS:
        if path.endswith(ext):
            return ext
    return ".jpg"


# ──────────────────────────────── Markdown 报告 ────────────────────────────────


def _save_as_markdown(
    article_id: str,
    title: str,
    author: str,
    publish_time: str,
    content: str,
    image_texts: list[dict],
    output_dir: Path,
) -> str | None:
    """生成 Markdown 分析报告。"""
    lines: list[str] = []

    display_title = title if title else f"百家号文章 {article_id}"
    lines.append(f"# {display_title}")
    lines.append("")

    if author or publish_time:
        if author:
            lines.append(f"**作者**：{author}")
        if publish_time:
            lines.append(f"**发布时间**：{publish_time}")
        lines.append("")
        lines.append("---")
        lines.append("")

    if content:
        lines.append("## 文章正文")
        lines.append("")
        lines.append(content)
        lines.append("")

    ocr_texts = [item for item in image_texts if item.get("text")]
    if ocr_texts:
        lines.append("## 图片内容（OCR 识别）")
        lines.append("")
        for item in ocr_texts:
            lines.append(f"### 图片 {item['index']}")
            lines.append("")
            lines.append(item["text"])
            lines.append("")

    full_text = content + "\n" + "\n".join(item.get("text", "") for item in image_texts)
    if full_text.strip():
        analysis = _analyze_content(title, full_text.strip())
        lines.append("## 内容分析")
        lines.append("")
        if analysis.get("content_type"):
            lines.append(f"**内容类型**：{analysis['content_type']}")
        if analysis.get("key_points"):
            lines.append("")
            lines.append("**核心要点**：")
            for point in analysis["key_points"]:
                lines.append(f"- {point}")
        lines.append("")

    report_content = "\n".join(lines)
    report_file = output_dir / f"{article_id}_report.md"
    report_file.write_text(report_content, encoding="utf-8")
    logger.info("Markdown 报告已生成: %s", report_file.name)
    return str(report_file)


def _analyze_content(title: str, full_text: str) -> dict[str, Any]:
    """轻量级内容分析（纯文本，不调用 LLM）。"""
    sentences = [s.strip() for s in re.split(r"[。！？\n]", full_text) if len(s.strip()) > 10]
    key_points = sentences[:5]
    content_type = _infer_content_type(title, full_text)
    return {
        "content_type": content_type,
        "key_points": key_points,
    }


def _infer_content_type(title: str, full_text: str) -> str:
    """根据标题和正文推断内容类型。"""
    combined = (title + full_text).lower()
    type_keywords: list[tuple[str, list[str]]] = [
        ("教程/攻略", ["教程", "攻略", "步骤", "方法", "如何", "怎么", "指南", "手把手"]),
        ("产品评测", ["测评", "评测", "体验", "开箱", "推荐", "好用", "值得买"]),
        ("行业资讯", ["发布", "上线", "宣布", "官方", "最新", "消息", "动态"]),
        ("观点/分析", ["认为", "分析", "思考", "观点", "看法", "为什么", "原因"]),
        ("故事/案例", ["故事", "案例", "经历", "分享", "记录"]),
    ]
    for content_type, keywords in type_keywords:
        if any(kw in combined for kw in keywords):
            return content_type
    return "综合内容"


# ──────────────────────────────── 工具函数 ────────────────────────────────


def _extract_article_id(article_url: str) -> str:
    """从百家号文章 URL 提取文章 ID。

    支持格式：
    - https://baijiahao.baidu.com/s?id=1234567890
    - https://mbd.baidu.com/newspage/data/landingsuper?id=xxx
    """
    import urllib.parse as urlparse_mod

    parsed = urlparse_mod.urlparse(article_url)
    params = urlparse_mod.parse_qs(parsed.query)
    article_id = params.get("id", [None])[0]
    if article_id:
        return article_id[:32]
    return hashlib.sha256(article_url.encode()).hexdigest()[:16]


def _is_content_image(url: str) -> bool:
    """判断 URL 是否为正文图片（过滤小图标、logo、头像等）。"""
    skip_patterns = [
        "avatar", "icon", "logo", "emoji", "gif",
        "pic.rmb.bdstatic.com/bjh/user",  # 百家号用户头像
        "himg.bdimg.com/sys",  # 百度系统图标
    ]
    url_lower = url.lower()
    return not any(pattern in url_lower for pattern in skip_patterns)


def _deduplicate_urls(urls: list[str]) -> list[str]:
    """去重 URL 列表（按去参数后的基础 URL 去重）。"""
    seen: set[str] = set()
    unique: list[str] = []
    for url in urls:
        base_url = url.split("?")[0]
        if base_url not in seen:
            seen.add(base_url)
            unique.append(url)
    return unique


def _fetch_with_autocli(url: str) -> str:
    """使用 autocli read 获取渲染后的页面 HTML（降级方案）。

    autocli read 通过用户 Chrome 浏览器扩展访问页面，可绕过反爬。
    """
    import subprocess
    import shutil

    autocli_path = shutil.which("autocli")
    if not autocli_path:
        logger.warning("autocli 未安装，无法降级")
        return ""

    try:
        result = subprocess.run(
            [autocli_path, "read", url, "-f", "html"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0 and result.stdout.strip():
            logger.info("autocli read 成功获取页面内容（%d 字符）", len(result.stdout))
            return result.stdout
        logger.warning("autocli read 失败: returncode=%d, stderr=%s", result.returncode, result.stderr[:200])
    except subprocess.TimeoutExpired:
        logger.warning("autocli read 超时")
    except Exception as autocli_error:
        logger.warning("autocli read 异常: %s", autocli_error)

    return ""


def _fetch_via_cdp(url: str) -> str:
    """通过 CDP（Selenium + debug Chrome）获取页面渲染后 HTML。

    百家号使用混淆 class 和动态加载，需真实浏览器执行 JS 后才能拿到完整正文。
    """
    import subprocess
    import shutil

    cdp_script = Path(__file__).parent.parent / "cdp_extract.py"
    if not cdp_script.exists():
        logger.warning("cdp_extract.py 不存在: %s", cdp_script)
        return ""

    python_path = shutil.which("python3") or shutil.which("python") or "python3"

    try:
        proc = subprocess.run(
            [python_path, str(cdp_script), "--url", url],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if proc.returncode != 0:
            logger.warning("CDP 脚本执行失败 (code=%d): %s", proc.returncode, proc.stderr[:200])
            return ""

        import json as _json
        data = _json.loads(proc.stdout)
        if data.get("success") and data.get("page_html"):
            html = data["page_html"]
            logger.info("CDP 获取页面成功（%d 字符）", len(html))
            return html
        logger.warning("CDP 返回但未获取到内容: %s", data.get("error", "unknown"))
    except subprocess.TimeoutExpired:
        logger.warning("CDP 超时（120s）")
    except Exception as cdp_error:
        logger.warning("CDP 异常: %s", cdp_error)

    return ""
