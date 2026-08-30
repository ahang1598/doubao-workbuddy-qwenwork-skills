"""今日头条图文提取器。

支持从今日头条文章链接提取：
- 文章标题、作者、发布时间、正文文本
- 文章内嵌图片（直接下载原图）
- 图片 OCR 文字识别
- 生成 Markdown 分析报告

使用 HTTP 请求页面 HTML，从 SSR 数据（articleInfo / INITIAL_PROPS）中提取内容。
无需登录，无需浏览器。
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

from .path_guard import safe_output_dir

logger = logging.getLogger(__name__)

_DEFAULT_OUTPUT_DIR = Path.home() / ".content-breakdown" / "output" / "toutiao"

_REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.toutiao.com/",
    "Cookie": "tt_webid=1",  # 基础 cookie 避免反爬
}

_MOBILE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) "
        "Version/16.0 Mobile/15E148 Safari/604.1"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Referer": "https://m.toutiao.com/",
}

_IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp")


def extract_article(
    article_url: str,
    output_dir: str | None = None,
    download_images: bool = True,
    ocr_images: bool = True,
    page_html: str | None = None,
) -> dict[str, Any]:
    """从今日头条文章链接提取内容（无需登录，无需浏览器）。

    Args:
        article_url: 头条文章链接，支持多种格式：
            - https://www.toutiao.com/article/{id}
            - https://www.toutiao.com/a{id}
            - https://m.toutiao.com/i{id}
        output_dir: 输出目录（默认 ~/.content-breakdown/output/toutiao）。
        download_images: 是否下载文章图片（默认 True）。
        ocr_images: 是否对图片做 OCR 文字识别（默认 True）。

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
            "read_count": int,
            "comment_count": int,
            "like_count": int,
            "report_file": str | None,
            "error": str | None,
        }
    """
    out_dir = safe_output_dir(output_dir) if output_dir else _DEFAULT_OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    article_id = _extract_article_id(article_url)
    if not article_id:
        return {
            "success": False,
            "article_id": "",
            "error": f"无法从链接中解析文章 ID: {article_url}",
            "title": "", "author": "", "publish_time": "", "content": "",
            "content_file": None, "image_urls": [], "image_files": [],
            "image_texts": [], "read_count": 0, "comment_count": 0,
            "like_count": 0, "report_file": None,
        }

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
        "read_count": 0,
        "comment_count": 0,
        "like_count": 0,
        "report_file": None,
        "error": None,
    }

    # 获取文章页面
    # 优先级：移动端 API > page_html 参数（browser_use）> Desktop HTTP > CDP 浏览器降级
    canonical_url = f"https://www.toutiao.com/article/{article_id}/"
    html = ""
    article_data = None
    session = requests.Session()
    session.headers.update(_REQUEST_HEADERS)

    # ── 方式零（推荐优先）：移动端 API 直接获取 JSON ──
    if not page_html:
        article_data = _fetch_mobile_api(article_id, session)
        if article_data and article_data.get("content"):
            logger.info("移动端 API 提取成功: title=%s, 正文=%d 字",
                        article_data.get("title", "")[:30], len(article_data.get("content", "")))

    # ── 降级：Desktop HTML + SSR 解析 ──
    if not article_data or not article_data.get("content"):
        if page_html:
            logger.info("使用 browser_use 提供的页面 HTML（%d 字符）", len(page_html))
            html = page_html
        else:
            # 尝试 HTTP 直接请求（桌面端大概率是 CSR 空壳）
            try:
                resp = session.get(canonical_url, timeout=30)
                if resp.status_code == 200:
                    resp.encoding = resp.apparent_encoding or "utf-8"
                    html = resp.text
            except Exception as request_error:
                logger.warning("HTTP 请求失败: %s", request_error)

        # 解析文章数据（优先从 SSR JSON 提取，降级 HTML 解析）
        if html:
            try:
                article_data = _parse_article_data(html, canonical_url)
            except Exception as parse_error:
                logger.warning("SSR 解析失败: %s", parse_error)

    # 反爬降级：CDP 浏览器
    if not article_data or not article_data.get("content"):
        logger.info("未获取到内容，尝试 CDP 浏览器降级")
        cdp_html = _fetch_via_cdp(canonical_url)
        if cdp_html:
            try:
                article_data = _parse_article_data(cdp_html, canonical_url)
            except Exception as parse_error:
                logger.warning("CDP 内容解析失败: %s", parse_error)

    if not article_data or not article_data.get("content"):
        result["error"] = "未能提取到文章内容。请通过 browser_use 获取页面 HTML 后传入 --page-html-file 参数，或安装 CDP 依赖: pip install chromedriver-autoinstaller selenium"
        return result

    result["title"] = article_data.get("title", "")
    result["author"] = article_data.get("author", "")
    result["publish_time"] = article_data.get("publish_time", "")
    result["content"] = article_data.get("content", "")
    result["image_urls"] = article_data.get("image_urls", [])
    result["read_count"] = article_data.get("read_count", 0)
    result["comment_count"] = article_data.get("comment_count", 0)
    result["like_count"] = article_data.get("like_count", 0)
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
        read_count=result["read_count"],
        comment_count=result["comment_count"],
        like_count=result["like_count"],
        output_dir=out_dir,
    )
    result["report_file"] = report_file

    return result


# ──────────────────────────────── 移动端 API ────────────────────────────────


def _fetch_mobile_api(article_id: str, session: requests.Session) -> dict[str, Any] | None:
    """通过头条移动端 API 直接获取文章 JSON 数据（无需浏览器，无需渲染）。

    API: GET https://m.toutiao.com/i{article_id}/info/
    返回完整 JSON 含 title, content, source, media_user, publish_time, 互动数据等。
    """
    api_url = f"https://m.toutiao.com/i{article_id}/info/"

    try:
        # 使用独立的 session 避免桌面端 headers 冲突
        mobile_session = requests.Session()
        mobile_session.headers.update(_MOBILE_HEADERS)
        resp = mobile_session.get(api_url, timeout=15)
        if resp.status_code != 200:
            logger.warning("移动端 API 返回 status=%d", resp.status_code)
            return None

        data = resp.json()
        article = data.get("data")
        if not article or not isinstance(article, dict):
            logger.warning("移动端 API 返回数据格式异常")
            return None

        # 提取正文（HTML 格式）
        raw_content = article.get("content", "")
        content = _clean_html_content(raw_content)

        # 从正文 HTML 中提取图片
        image_urls = _extract_images_from_content(raw_content)
        # 也从 image_list 或 poster_url 补充
        image_list = article.get("image_list", [])
        if image_list:
            for img_item in image_list:
                img_url = img_item.get("url") or img_item.get("origin_url", "")
                if img_url:
                    if img_url.startswith("//"):
                        img_url = "https:" + img_url
                    image_urls.append(img_url)
        poster_url = article.get("poster_url", "")
        if poster_url and poster_url.startswith("http"):
            image_urls.insert(0, poster_url)
        image_urls = _deduplicate_urls(image_urls)

        # 发布时间
        publish_time = article.get("publish_time", "")
        if isinstance(publish_time, (int, float)) and publish_time > 1000000000:
            import datetime
            publish_time = datetime.datetime.fromtimestamp(publish_time).strftime("%Y-%m-%d %H:%M")
        elif isinstance(publish_time, str) and publish_time.isdigit() and len(publish_time) >= 10:
            import datetime
            publish_time = datetime.datetime.fromtimestamp(int(publish_time)).strftime("%Y-%m-%d %H:%M")

        # 作者
        author = ""
        source = article.get("source", "") or article.get("detail_source", "")
        media_user = article.get("media_user", {})
        if media_user and isinstance(media_user, dict):
            author = media_user.get("screen_name", "") or media_user.get("name", "")
        if not author:
            author = source

        return {
            "title": article.get("title", ""),
            "author": author,
            "publish_time": str(publish_time),
            "content": content,
            "image_urls": image_urls,
            "read_count": article.get("impression_count", 0) or article.get("read_count", 0),
            "comment_count": article.get("comment_count", 0),
            "like_count": article.get("digg_count", 0) or article.get("like_count", 0),
        }

    except requests.exceptions.Timeout:
        logger.warning("移动端 API 超时")
    except requests.exceptions.RequestException as req_error:
        logger.warning("移动端 API 请求异常: %s", req_error)
    except json.JSONDecodeError:
        logger.warning("移动端 API 返回非 JSON 数据")
    except Exception as api_error:
        logger.warning("移动端 API 异常: %s", api_error)

    return None


# ──────────────────────────────── SSR 数据解析 ────────────────────────────────


def _parse_article_data(html: str, article_url: str) -> dict[str, Any] | None:
    """从头条文章页面提取数据。

    头条文章使用 SSR 渲染，核心数据通常在以下位置之一：
    1. window.__INITIAL_PROPS__ = {...}
    2. window._INIT_PROPS = {...}
    3. articleInfo = {...}
    4. 直接 HTML 解析（降级方案）
    """
    # 方案 1：从 SSR JSON 提取
    ssr_data = _extract_ssr_json(html)
    if ssr_data and ssr_data.get("content"):
        return ssr_data

    # 方案 2：HTML 解析降级
    return _parse_html_fallback(html, article_url)


def _extract_ssr_json(html: str) -> dict[str, Any] | None:
    """从页面 SSR JSON 中提取文章数据。"""
    # 尝试多种 SSR 数据格式
    patterns = [
        # __INITIAL_PROPS__（头条新版）
        r'window\.__INITIAL_PROPS__\s*=\s*(\{.*?\})\s*;?\s*</script>',
        # _INIT_PROPS（头条旧版）
        r'window\._INIT_PROPS\s*=\s*(\{.*?\})\s*;?\s*</script>',
        # articleInfo（部分文章页）
        r'articleInfo\s*:\s*(\{.*?\})\s*,?\s*(?:commentInfo|recommendInfo)',
        # INITIAL_STATE
        r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\})\s*;?\s*</script>',
    ]

    for pattern in patterns:
        match = re.search(pattern, html, re.DOTALL)
        if not match:
            continue
        try:
            data = json.loads(match.group(1))
            result = _extract_article_from_ssr(data)
            if result and result.get("content"):
                return result
        except json.JSONDecodeError:
            continue

    return None


def _extract_article_from_ssr(data: dict) -> dict[str, Any] | None:
    """从 SSR 数据对象中定位并提取文章信息。

    头条 SSR 数据结构可能的路径：
    - data.articleInfo / data.articleDetail
    - data.initialState.articleInfo
    - data 本身就是 articleInfo
    """
    # 尝试多个路径定位 articleInfo
    article_info = None
    candidate_paths = [
        lambda d: d.get("articleInfo"),
        lambda d: d.get("articleDetail"),
        lambda d: d.get("initialState", {}).get("articleInfo"),
        lambda d: d.get("data", {}).get("articleInfo"),
        lambda d: d if d.get("title") and (d.get("content") or d.get("article_content")) else None,
    ]

    for path_fn in candidate_paths:
        try:
            candidate = path_fn(data)
            if candidate and isinstance(candidate, dict):
                article_info = candidate
                break
        except (AttributeError, TypeError):
            continue

    if not article_info:
        return None

    # 提取正文（可能是 HTML 格式）
    raw_content = (
        article_info.get("content")
        or article_info.get("article_content")
        or article_info.get("detail_source", "")
    )
    content = _clean_html_content(raw_content)

    # 提取图片
    image_urls = _extract_images_from_content(raw_content)
    # 也从 image_list 字段提取
    image_list = article_info.get("image_list", [])
    if image_list:
        for img_item in image_list:
            img_url = img_item.get("url") or img_item.get("origin_url", "")
            if img_url:
                # 头条图片 URL 可能缺少协议
                if img_url.startswith("//"):
                    img_url = "https:" + img_url
                image_urls.append(img_url)
    image_urls = _deduplicate_urls(image_urls)

    # 发布时间
    publish_time = article_info.get("publish_time", "")
    if isinstance(publish_time, (int, float)) and publish_time > 1000000000:
        import datetime
        publish_time = datetime.datetime.fromtimestamp(publish_time).strftime("%Y-%m-%d %H:%M")

    # 作者
    author = ""
    source = article_info.get("source", "")
    media_user = article_info.get("media_user", {})
    if media_user and isinstance(media_user, dict):
        author = media_user.get("screen_name", "") or media_user.get("name", "")
    if not author:
        author = source

    return {
        "title": article_info.get("title", ""),
        "author": author,
        "publish_time": str(publish_time),
        "content": content,
        "image_urls": image_urls,
        "read_count": article_info.get("read_count", 0) or article_info.get("verify_count", 0),
        "comment_count": article_info.get("comment_count", 0),
        "like_count": article_info.get("digg_count", 0) or article_info.get("like_count", 0),
    }


def _parse_html_fallback(html: str, article_url: str) -> dict[str, Any] | None:
    """HTML 降级解析（当 SSR JSON 提取失败时）。"""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        logger.warning("BeautifulSoup 未安装，无法进行 HTML 降级解析")
        return None

    soup = BeautifulSoup(html, "html.parser")

    # 标题
    title = ""
    title_tag = soup.find("h1") or soup.find("title")
    if title_tag:
        title = title_tag.get_text(strip=True)
        # 去掉 " - 今日头条" 后缀
        title = re.sub(r"\s*[-_]\s*今日头条.*$", "", title).strip()

    # 正文
    content = ""
    image_urls: list[str] = []
    content_div = (
        soup.find("article")
        or soup.find("div", class_="article-content")
        or soup.find("div", id="article-content")
    )
    if content_div:
        for img in content_div.find_all("img"):
            img_url = img.get("data-src") or img.get("src") or ""
            if img_url and img_url.startswith("http") and _is_content_image(img_url):
                image_urls.append(img_url)

        paragraphs = []
        for element in content_div.find_all(["p", "h1", "h2", "h3", "h4"]):
            text = element.get_text(strip=True)
            if text and len(text) > 1:
                paragraphs.append(text)
        content = "\n\n".join(paragraphs)
        image_urls = _deduplicate_urls(image_urls)

    # 作者
    author = ""
    author_meta = soup.find("meta", {"name": "author"})
    if author_meta:
        author = author_meta.get("content", "")

    if content:
        return {
            "title": title,
            "author": author,
            "publish_time": "",
            "content": content,
            "image_urls": image_urls,
            "read_count": 0,
            "comment_count": 0,
            "like_count": 0,
        }
    return None


# ──────────────────────────────── 内容清理 ────────────────────────────────


def _clean_html_content(html_content: str) -> str:
    """清理头条文章 HTML 内容为纯文本。"""
    if not html_content:
        return ""
    # <br> 替换为换行
    text = re.sub(r"<br\s*/?>", "\n", html_content)
    # 去掉 <img> 标签（图片单独处理）
    text = re.sub(r"<img[^>]*>", "", text)
    # 保留段落结构
    text = re.sub(r"</p>\s*<p[^>]*>", "\n\n", text)
    text = re.sub(r"<p[^>]*>", "", text)
    text = re.sub(r"</p>", "\n", text)
    # 去掉剩余标签
    text = re.sub(r"<[^>]+>", "", text)
    # HTML 实体解码
    text = text.replace("&nbsp;", " ").replace("&amp;", "&")
    text = text.replace("&lt;", "<").replace("&gt;", ">")
    text = text.replace("&quot;", '"')
    # 清理多余空白
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n\n".join(lines)


def _extract_images_from_content(html_content: str) -> list[str]:
    """从 HTML 内容中提取图片 URL。"""
    if not html_content:
        return []
    image_urls: list[str] = []
    img_matches = re.findall(r'<img[^>]+src="([^"]+)"', html_content)
    for img_url in img_matches:
        if img_url.startswith("//"):
            img_url = "https:" + img_url
        if img_url.startswith("http") and _is_content_image(img_url):
            image_urls.append(img_url)
    return image_urls


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
    read_count: int,
    comment_count: int,
    like_count: int,
    output_dir: Path,
) -> str | None:
    """生成 Markdown 分析报告。"""
    lines: list[str] = []

    display_title = title if title else f"头条文章 {article_id}"
    lines.append(f"# {display_title}")
    lines.append("")

    if author or publish_time:
        if author:
            lines.append(f"**作者**：{author}")
        if publish_time:
            lines.append(f"**发布时间**：{publish_time}")
        stats_parts = []
        if read_count:
            stats_parts.append(f"**阅读** {read_count}")
        if comment_count:
            stats_parts.append(f"**评论** {comment_count}")
        if like_count:
            stats_parts.append(f"**点赞** {like_count}")
        if stats_parts:
            lines.append(" | ".join(stats_parts))
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
    """轻量级内容分析。"""
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
    """从头条文章 URL 提取文章 ID。

    支持格式：
    - https://www.toutiao.com/article/1234567890/
    - https://www.toutiao.com/a1234567890/
    - https://m.toutiao.com/i1234567890/
    - https://www.toutiao.com/i1234567890/
    """
    parsed = urlparse(article_url)
    path = parsed.path.rstrip("/")

    # /article/{id} 格式
    article_match = re.search(r"/article/(\d+)", path)
    if article_match:
        return article_match.group(1)

    # /a{id} 或 /i{id} 格式
    short_match = re.search(r"/[ai](\d+)", path)
    if short_match:
        return short_match.group(1)

    return ""


def _is_content_image(url: str) -> bool:
    """判断 URL 是否为正文图片（过滤小图标、logo、头像等）。"""
    skip_patterns = [
        "avatar", "icon", "logo", "emoji",
        "/user/", "/head/",
        "sf1-cdn-tos.toutiao",  # 头条静态资源
    ]
    url_lower = url.lower()
    return not any(pattern in url_lower for pattern in skip_patterns)


def _deduplicate_urls(urls: list[str]) -> list[str]:
    """去重 URL 列表。"""
    seen: set[str] = set()
    unique: list[str] = []
    for url in urls:
        base_url = url.split("?")[0]
        if base_url not in seen:
            seen.add(base_url)
            unique.append(url)
    return unique


def _fetch_with_autocli(url: str) -> str:
    """使用 autocli read 获取渲染后的页面 HTML（降级方案）。"""
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
        logger.warning("autocli read 失败: returncode=%d", result.returncode)
    except subprocess.TimeoutExpired:
        logger.warning("autocli read 超时")
    except Exception as autocli_error:
        logger.warning("autocli read 异常: %s", autocli_error)

    return ""


def _fetch_via_cdp(url: str) -> str:
    """通过 CDP（Selenium + debug Chrome）获取页面渲染后 HTML。

    头条文章为纯客户端渲染（CSR），需要真实浏览器执行 JS 后才能拿到正文。
    """
    import subprocess
    import shutil

    # 调用同目录下的 cdp_extract.py 脚本
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
