"""微博图文提取器。

支持从微博链接提取：
- 微博正文文本（含长文展开）
- 微博配图（直接下载原图）
- 图片 OCR 文字识别
- 生成 Markdown 分析报告

使用移动端 API（m.weibo.cn/detail/{mid}）获取 JSON 数据，无需登录，无需浏览器。
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

_DEFAULT_OUTPUT_DIR = Path.home() / ".content-breakdown" / "output" / "weibo"

_REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) "
        "Version/16.0 Mobile/15E148 Safari/604.1"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://m.weibo.cn/",
}

_IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp")


def extract_weibo(
    weibo_url: str,
    output_dir: str | None = None,
    download_images: bool = True,
    ocr_images: bool = True,
) -> dict[str, Any]:
    """从微博链接提取内容（无需登录，无需浏览器）。

    Args:
        weibo_url: 微博链接，支持多种格式：
            - https://m.weibo.cn/detail/{mid}
            - https://weibo.com/{uid}/{mid}
            - https://weibo.com/detail/{mid}
        output_dir: 输出目录（默认 ~/.content-breakdown/output/weibo）。
        download_images: 是否下载微博配图（默认 True）。
        ocr_images: 是否对图片做 OCR 文字识别（默认 True）。

    Returns:
        {
            "success": bool,
            "weibo_id": str,
            "title": str,
            "author": str,
            "publish_time": str,
            "content": str,
            "content_file": str | None,
            "image_urls": list[str],
            "image_files": list[str],
            "image_texts": list[dict],
            "reposts_count": int,
            "comments_count": int,
            "likes_count": int,
            "report_file": str | None,
            "error": str | None,
        }
    """
    out_dir = safe_output_dir(output_dir) if output_dir else _DEFAULT_OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    weibo_id = _extract_weibo_id(weibo_url)
    if not weibo_id:
        return {
            "success": False,
            "weibo_id": "",
            "error": f"无法从链接中解析微博 ID: {weibo_url}",
            "title": "", "author": "", "publish_time": "", "content": "",
            "content_file": None, "image_urls": [], "image_files": [],
            "image_texts": [], "reposts_count": 0, "comments_count": 0,
            "likes_count": 0, "report_file": None,
        }

    result: dict[str, Any] = {
        "success": False,
        "weibo_id": weibo_id,
        "title": "",
        "author": "",
        "publish_time": "",
        "content": "",
        "content_file": None,
        "image_urls": [],
        "image_files": [],
        "image_texts": [],
        "reposts_count": 0,
        "comments_count": 0,
        "likes_count": 0,
        "report_file": None,
        "error": None,
    }

    session = requests.Session()
    session.headers.update(_REQUEST_HEADERS)
    weibo_data = None

    # 头条文章走专用解析路径
    if _is_ttarticle_url(weibo_url):
        logger.info("检测到微博头条文章链接，使用 autocli read 获取内容")
        html = _fetch_with_autocli(weibo_url)
        if html:
            weibo_data = _parse_ttarticle_html(html)
        if not weibo_data:
            # 降级：直接请求原 URL
            try:
                pc_headers = {**_REQUEST_HEADERS, "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )}
                resp = session.get(weibo_url, headers=pc_headers, timeout=30)
                if resp.status_code == 200:
                    weibo_data = _parse_ttarticle_html(resp.text)
            except Exception as request_error:
                logger.warning("头条文章 HTTP 请求失败: %s", request_error)
    else:
        # 普通微博：通过移动端 API 获取详情
        api_url = f"https://m.weibo.cn/detail/{weibo_id}"
        try:
            resp = session.get(api_url, timeout=30)
            if resp.status_code != 200:
                result["error"] = f"API 请求失败 (status={resp.status_code}): {api_url}"
                return result
        except Exception as request_error:
            result["error"] = f"网络请求失败: {request_error}"
            return result

        # 解析响应
        try:
            weibo_data = _parse_detail_response(resp.text)
        except Exception as parse_error:
            result["error"] = f"数据解析失败: {parse_error}"
            return result

        # 移动端 API 失败时降级到 autocli read
        if not weibo_data:
            logger.info("移动端 API 解析失败，尝试 autocli read 降级")
            html = _fetch_via_cdp(f"https://m.weibo.cn/detail/{weibo_id}")
            if html:
                weibo_data = _parse_detail_response(html)

    if not weibo_data:
        result["error"] = "未能提取微博数据（页面可能需要登录或被反爬拦截）"
        return result

    # 提取字段
    result["author"] = weibo_data.get("author", "")
    result["publish_time"] = weibo_data.get("publish_time", "")
    result["content"] = weibo_data.get("content", "")
    result["title"] = weibo_data.get("title", "")
    result["image_urls"] = weibo_data.get("image_urls", [])
    result["reposts_count"] = weibo_data.get("reposts_count", 0)
    result["comments_count"] = weibo_data.get("comments_count", 0)
    result["likes_count"] = weibo_data.get("likes_count", 0)
    result["success"] = True

    logger.info(
        "微博解析成功: author=%s, 图片=%d 张, 正文=%d 字",
        result["author"],
        len(result["image_urls"]),
        len(result["content"]),
    )

    # 保存正文
    if result["content"]:
        content_file = out_dir / f"{weibo_id}_content.txt"
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
        images_dir = out_dir / f"{weibo_id}_images"
        images_dir.mkdir(parents=True, exist_ok=True)
        downloaded, failed = _download_weibo_images(
            session=session,
            image_urls=result["image_urls"],
            save_dir=images_dir,
            weibo_id=weibo_id,
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
        weibo_id=weibo_id,
        title=result["title"],
        author=result["author"],
        publish_time=result["publish_time"],
        content=result["content"],
        image_texts=result["image_texts"],
        reposts_count=result["reposts_count"],
        comments_count=result["comments_count"],
        likes_count=result["likes_count"],
        output_dir=out_dir,
    )
    result["report_file"] = report_file

    return result


# ──────────────────────────────── 数据解析 ────────────────────────────────


def _parse_detail_response(html: str) -> dict[str, Any] | None:
    """从移动端 detail 页面响应中提取微博数据。

    m.weibo.cn/detail/{mid} 返回 HTML，其中包含
    var $render_data = [{...}] 形式的 JSON 数据。
    """
    # 提取 $render_data
    render_match = re.search(
        r'var\s+\$render_data\s*=\s*\[(.*?)\]\s*\[0\]',
        html,
        re.DOTALL,
    )
    if not render_match:
        # 备选：有些版本是直接赋值对象
        render_match = re.search(
            r'var\s+\$render_data\s*=\s*(\{.*?\})\s*;',
            html,
            re.DOTALL,
        )
    if not render_match:
        logger.warning("未找到 $render_data，尝试从页面 HTML 解析")
        return _parse_html_fallback(html)

    try:
        raw_json = render_match.group(1)
        data = json.loads(raw_json)
    except json.JSONDecodeError:
        logger.warning("$render_data JSON 解析失败，尝试 HTML 降级")
        return _parse_html_fallback(html)

    # 从 render_data 中提取 status 对象
    status = data.get("status", {})
    if not status:
        return _parse_html_fallback(html)

    return _extract_from_status(status)


def _extract_from_status(status: dict) -> dict[str, Any]:
    """从微博 status 对象中提取关键字段。"""
    # 正文（HTML 格式，需清理）
    raw_text = status.get("text", "")
    content = _clean_html_text(raw_text)

    # 长文展开
    long_text = status.get("longText", {})
    if isinstance(long_text, dict) and long_text.get("longTextContent"):
        content = _clean_html_text(long_text["longTextContent"])

    # 作者
    user = status.get("user", {})
    author = user.get("screen_name", "") if user else ""

    # 发布时间
    publish_time = status.get("created_at", "")

    # 标题（微博头条文章有 page_info.title）
    title = ""
    page_info = status.get("page_info", {})
    if page_info and isinstance(page_info, dict):
        title = page_info.get("title", "") or page_info.get("content1", "")

    # 图片 URL（取大图）
    image_urls: list[str] = []
    pics = status.get("pics", [])
    if pics:
        for pic in pics:
            large = pic.get("large", {})
            img_url = large.get("url", "") if large else pic.get("url", "")
            if img_url:
                image_urls.append(img_url)

    # 互动数据
    reposts_count = status.get("reposts_count", 0)
    comments_count = status.get("comments_count", 0)
    likes_count = status.get("attitudes_count", 0)

    return {
        "title": title,
        "author": author,
        "publish_time": publish_time,
        "content": content,
        "image_urls": image_urls,
        "reposts_count": reposts_count,
        "comments_count": comments_count,
        "likes_count": likes_count,
    }


def _parse_html_fallback(html: str) -> dict[str, Any] | None:
    """HTML 降级解析（当 JSON 提取失败时）。"""
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
    except ImportError:
        return None

    content = ""
    title = ""

    # 尝试从 meta 标签提取
    og_title = soup.find("meta", property="og:title")
    if og_title:
        title = og_title.get("content", "")

    og_desc = soup.find("meta", property="og:description")
    if og_desc:
        content = og_desc.get("content", "")

    if not content:
        # 尝试从页面中提取文本内容
        content_div = soup.find("div", class_="weibo-text") or soup.find("div", class_="card-text")
        if content_div:
            content = content_div.get_text(strip=True)

    if content:
        return {
            "title": title,
            "author": "",
            "publish_time": "",
            "content": content,
            "image_urls": [],
            "reposts_count": 0,
            "comments_count": 0,
            "likes_count": 0,
        }
    return None


def _clean_html_text(html_text: str) -> str:
    """清理微博 HTML 文本，保留纯文本。"""
    if not html_text:
        return ""
    # 将 <br> 和 <br/> 替换为换行
    text = re.sub(r"<br\s*/?>", "\n", html_text)
    # 提取 @用户名 和 #话题#
    text = re.sub(r'<a[^>]*>(@[^<]+)</a>', r'\1', text)
    text = re.sub(r'<a[^>]*>(#[^<]+#)</a>', r'\1', text)
    # 处理表情文字（<span class="url-icon">...</span> 后的 alt 文本）
    text = re.sub(r'<span class="url-icon">.*?</span><span>([^<]*)</span>', r'\1', text)
    # 去掉剩余的 HTML 标签
    text = re.sub(r"<[^>]+>", "", text)
    # 清理多余空白
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)


# ──────────────────────────────── 图片下载 ────────────────────────────────


def _download_weibo_images(
    session: requests.Session,
    image_urls: list[str],
    save_dir: Path,
    weibo_id: str,
) -> tuple[list[str], list[str]]:
    """批量下载微博配图，返回 (成功路径列表, 失败 URL 列表)。"""
    downloaded: list[str] = []
    failed: list[str] = []

    # 微博图片需要带 Referer
    download_headers = {
        "Referer": "https://m.weibo.cn/",
        "User-Agent": _REQUEST_HEADERS["User-Agent"],
    }

    for index, image_url in enumerate(image_urls):
        try:
            url_hash = hashlib.sha256(image_url.encode()).hexdigest()[:12]
            ext = _detect_image_extension(image_url)
            filename = f"{weibo_id}_img_{index + 1:02d}_{url_hash}{ext}"
            filepath = save_dir / filename

            if filepath.exists() and filepath.stat().st_size > 0:
                downloaded.append(str(filepath))
                continue

            resp = session.get(image_url, headers=download_headers, timeout=30)
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
    weibo_id: str,
    title: str,
    author: str,
    publish_time: str,
    content: str,
    image_texts: list[dict],
    reposts_count: int,
    comments_count: int,
    likes_count: int,
    output_dir: Path,
) -> str | None:
    """生成 Markdown 分析报告。"""
    lines: list[str] = []

    display_title = title if title else f"微博 {weibo_id}"
    if author:
        display_title = f"@{author}: {display_title}" if title else f"@{author} 的微博"
    lines.append(f"# {display_title}")
    lines.append("")

    if author or publish_time:
        if author:
            lines.append(f"**作者**：@{author}")
        if publish_time:
            lines.append(f"**发布时间**：{publish_time}")
        lines.append(f"**转发** {reposts_count} | **评论** {comments_count} | **点赞** {likes_count}")
        lines.append("")
        lines.append("---")
        lines.append("")

    if content:
        lines.append("## 微博正文")
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
        analysis = _analyze_content(title or "", full_text.strip())
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
    report_file = output_dir / f"{weibo_id}_report.md"
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
        ("日常生活", ["今天", "打卡", "日常", "记录", "心情", "晚安", "早安"]),
    ]
    for content_type, keywords in type_keywords:
        if any(kw in combined for kw in keywords):
            return content_type
    return "综合内容"


# ──────────────────────────────── 工具函数 ────────────────────────────────


def _extract_weibo_id(weibo_url: str) -> str:
    """从微博链接中提取微博 ID（mid）。

    支持格式：
    - https://m.weibo.cn/detail/5129390123456789
    - https://m.weibo.cn/status/5129390123456789
    - https://weibo.com/1234567890/PxxxxYyyy
    - https://weibo.com/detail/5129390123456789
    - https://weibo.cn/detail/5129390123456789
    - https://weibo.com/ttarticle/p/show?id=2309405307592401617076
    """
    parsed = urlparse(weibo_url)
    path = parsed.path.rstrip("/")

    # /detail/{mid} 或 /status/{mid}
    detail_match = re.search(r"/(?:detail|status)/([A-Za-z0-9]+)", path)
    if detail_match:
        return detail_match.group(1)

    # weibo.com/{uid}/{mid} 格式
    user_post_match = re.search(r"/(\d+)/([A-Za-z0-9]+)$", path)
    if user_post_match:
        return user_post_match.group(2)

    # ttarticle/p/show?id=xxx 格式（微博头条文章）
    if "ttarticle" in path:
        import urllib.parse as urlparse_mod
        params = urlparse_mod.parse_qs(parsed.query)
        article_id = params.get("id", [None])[0]
        if article_id:
            return article_id

    return ""


def _is_ttarticle_url(weibo_url: str) -> bool:
    """判断是否为微博头条文章链接。"""
    return "ttarticle" in weibo_url


def _parse_ttarticle_html(html: str) -> dict[str, Any] | None:
    """解析微博头条文章 HTML，提取正文内容。"""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        logger.warning("BeautifulSoup 未安装，无法解析头条文章")
        return None

    soup = BeautifulSoup(html, "html.parser")

    title = ""
    title_tag = soup.find("div", class_="title") or soup.find("h1")
    if title_tag:
        title = title_tag.get_text(strip=True)
    if not title:
        og_title = soup.find("meta", property="og:title")
        if og_title:
            title = og_title.get("content", "")

    author = ""
    author_tag = soup.find("div", class_="name") or soup.find("a", class_="name")
    if author_tag:
        author = author_tag.get_text(strip=True)

    content = ""
    image_urls: list[str] = []
    content_div = (
        soup.find("div", class_="WB_editor_iframe_new")
        or soup.find("div", id="article_content")
        or soup.find("article")
        or soup.find("div", class_="article-content")
    )
    if content_div:
        for img in content_div.find_all("img"):
            img_url = img.get("data-src") or img.get("src") or ""
            if img_url and img_url.startswith("http"):
                image_urls.append(img_url)

        paragraphs = []
        for element in content_div.find_all(["p", "section", "h1", "h2", "h3"]):
            text = element.get_text(strip=True)
            if text and len(text) > 1:
                paragraphs.append(text)
        content = "\n\n".join(paragraphs)

    if not content:
        # 降级：从 meta description 提取
        og_desc = soup.find("meta", property="og:description")
        if og_desc:
            content = og_desc.get("content", "")

    if content:
        return {
            "title": title,
            "author": author,
            "publish_time": "",
            "content": content,
            "image_urls": image_urls,
            "reposts_count": 0,
            "comments_count": 0,
            "likes_count": 0,
        }
    return None


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

    微博移动端页面偶尔会反爬，需真实浏览器降级。
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
