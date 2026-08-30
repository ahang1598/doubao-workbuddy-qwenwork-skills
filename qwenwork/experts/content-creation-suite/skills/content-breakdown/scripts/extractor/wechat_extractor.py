"""微信公众号图文提取器。

支持从公众号文章链接（mp.weixin.qq.com/s/xxxxx）提取：
- 文章标题、正文文本
- 文章内嵌图片（直接下载原图）
- 图片 OCR 文字识别
- 生成 Markdown 分析报告

无需登录，无需浏览器，直接 HTTP 请求页面 HTML 解析。
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
import time
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import requests

from .path_guard import safe_output_dir

logger = logging.getLogger(__name__)

_DEFAULT_OUTPUT_DIR = Path.home() / ".content-breakdown" / "output" / "wechat"

_REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://mp.weixin.qq.com/",
}

_IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp")


def extract_article(
    article_url: str,
    output_dir: str | None = None,
    download_images: bool = True,
    ocr_images: bool = True,
) -> dict[str, Any]:
    """从微信公众号文章链接提取内容（无需登录，无需浏览器）。

    Args:
        article_url: 公众号文章链接（mp.weixin.qq.com/s/xxxxx）。
        output_dir: 输出目录（默认 ~/.content-breakdown/output/wechat）。
        download_images: 是否下载文章图片（默认 True）。
        ocr_images: 是否对图片做 OCR 文字识别（默认 True）。

    Returns:
        {
            "success": bool,
            "article_id": str,
            "title": str,
            "author": str,
            "account_name": str,
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
        "account_name": "",
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
    try:
        session = requests.Session()
        session.headers.update(_REQUEST_HEADERS)
        resp = session.get(article_url, timeout=30)
        if resp.status_code != 200:
            result["error"] = f"请求失败 (status={resp.status_code}): {article_url}"
            return result
        html = resp.text
    except Exception as request_error:
        result["error"] = f"网络请求失败: {request_error}"
        return result

    # 解析文章内容
    try:
        article_data = _parse_article_html(html, article_url)
    except Exception as parse_error:
        result["error"] = f"HTML 解析失败: {parse_error}"
        return result

    result["title"] = article_data.get("title", "")
    result["author"] = article_data.get("author", "")
    result["account_name"] = article_data.get("account_name", "")
    result["publish_time"] = article_data.get("publish_time", "")
    result["content"] = article_data.get("content", "")
    result["image_urls"] = article_data.get("image_urls", [])
    result["success"] = True

    logger.info(
        "文章解析成功: title=%s, 图片=%d 张, 正文=%d 字",
        result["title"][:30],
        len(result["image_urls"]),
        len(result["content"]),
    )

    # 保存正文
    if result["content"]:
        content_file = out_dir / f"{article_id}_content.txt"
        header = f"# {result['title']}\n\n" if result["title"] else ""
        meta = ""
        if result["account_name"]:
            meta += f"**公众号**：{result['account_name']}\n"
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
    if ocr_images and result["image_files"]:
        logger.info("开始图片 OCR 识别...")
        image_texts = _ocr_image_files(result["image_files"])
        result["image_texts"] = image_texts
        total_chars = sum(len(item.get("text", "")) for item in image_texts)
        logger.info("OCR 完成: %d 张图片，共 %d 字", len(image_texts), total_chars)

    # 生成 Markdown 报告
    report_file = _save_as_markdown(
        article_id=article_id,
        title=result["title"],
        account_name=result["account_name"],
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
    """解析公众号文章 HTML，提取标题、正文、图片 URL 等。

    优先使用 BeautifulSoup，降级使用正则表达式。
    """
    try:
        from bs4 import BeautifulSoup
        return _parse_with_beautifulsoup(html, article_url)
    except ImportError:
        logger.info("BeautifulSoup 未安装，使用正则表达式解析")
        return _parse_with_regex(html, article_url)


def _parse_with_beautifulsoup(html: str, article_url: str) -> dict[str, Any]:
    """使用 BeautifulSoup 解析文章 HTML。"""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")

    # 标题
    title = ""
    title_tag = soup.find("h1", {"id": "activity-name"}) or soup.find("h1", class_="rich_media_title")
    if title_tag:
        title = title_tag.get_text(strip=True)
    if not title:
        og_title = soup.find("meta", property="og:title")
        if og_title:
            title = og_title.get("content", "")

    # 公众号名称
    account_name = ""
    account_tag = soup.find("strong", class_="profile_nickname") or soup.find(id="js_name")
    if account_tag:
        account_name = account_tag.get_text(strip=True)

    # 作者
    author = ""
    author_tag = soup.find("span", id="js_author_name") or soup.find("em", id="js_author_name")
    if author_tag:
        author = author_tag.get_text(strip=True)

    # 发布时间
    publish_time = ""
    time_tag = soup.find("em", id="publish_time") or soup.find(id="publish_time")
    if time_tag:
        publish_time = time_tag.get_text(strip=True)
    if not publish_time:
        # 从 JS 变量里提取
        time_match = re.search(r'var\s+ct\s*=\s*"(\d+)"', html)
        if time_match:
            import datetime
            ts = int(time_match.group(1))
            publish_time = datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")

    # 正文内容（#js_content）
    content = ""
    image_urls: list[str] = []
    content_div = soup.find("div", id="js_content")
    if content_div:
        # 提取图片 URL（data-src 优先，src 降级）
        for img in content_div.find_all("img"):
            img_url = img.get("data-src") or img.get("src") or ""
            if img_url and img_url.startswith("http") and "mmbiz" in img_url:
                image_urls.append(img_url)

        # 提取纯文本（保留段落结构）
        paragraphs = []
        for element in content_div.find_all(["p", "section", "h1", "h2", "h3", "h4"]):
            text = element.get_text(strip=True)
            if text:
                paragraphs.append(text)
        content = "\n\n".join(paragraphs)

        # 去重图片 URL
        seen: set[str] = set()
        unique_image_urls = []
        for url in image_urls:
            # 去掉 URL 参数后比较（同一张图可能有不同参数）
            base_url = url.split("?")[0]
            if base_url not in seen:
                seen.add(base_url)
                unique_image_urls.append(url)
        image_urls = unique_image_urls

    return {
        "title": title,
        "author": author,
        "account_name": account_name,
        "publish_time": publish_time,
        "content": content,
        "image_urls": image_urls,
    }


def _parse_with_regex(html: str, article_url: str) -> dict[str, Any]:
    """使用正则表达式解析文章 HTML（BeautifulSoup 不可用时的降级方案）。"""
    # 标题
    title = ""
    title_match = re.search(r'id="activity-name"[^>]*>(.*?)</h1>', html, re.DOTALL)
    if title_match:
        title = re.sub(r"<[^>]+>", "", title_match.group(1)).strip()
    if not title:
        og_match = re.search(r'property="og:title"\s+content="([^"]+)"', html)
        if og_match:
            title = og_match.group(1)

    # 公众号名称
    account_name = ""
    account_match = re.search(r'id="js_name"[^>]*>(.*?)</strong>', html, re.DOTALL)
    if account_match:
        account_name = re.sub(r"<[^>]+>", "", account_match.group(1)).strip()

    # 发布时间
    publish_time = ""
    time_match = re.search(r'var\s+ct\s*=\s*"(\d+)"', html)
    if time_match:
        import datetime
        ts = int(time_match.group(1))
        publish_time = datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")

    # 正文（提取 js_content 区域的文本）
    content = ""
    content_match = re.search(
        r'id="js_content"[^>]*>(.*?)</div>\s*</div>\s*<div[^>]*id="js_tags"',
        html,
        re.DOTALL,
    )
    if content_match:
        raw_content = content_match.group(1)
        # 去掉所有 HTML 标签
        text = re.sub(r"<[^>]+>", "\n", raw_content)
        # 清理多余空白
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        content = "\n\n".join(lines)

    # 图片 URL（data-src）
    image_urls = re.findall(r'data-src="(https://mmbiz[^"]+)"', html)
    # 去重
    seen: set[str] = set()
    unique_image_urls = []
    for url in image_urls:
        base_url = url.split("?")[0]
        if base_url not in seen:
            seen.add(base_url)
            unique_image_urls.append(url)

    return {
        "title": title,
        "author": "",
        "account_name": account_name,
        "publish_time": publish_time,
        "content": content,
        "image_urls": unique_image_urls,
    }


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

            # 缓存命中
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
    # 微信图片 URL 通常没有扩展名，默认 jpg
    return ".jpg"


# ──────────────────────────────── 图片 OCR ────────────────────────────────

def _ensure_rapidocr() -> None:
    """确保 rapidocr-onnxruntime 已安装，未安装时自动 pip 安装。"""
    try:
        import rapidocr_onnxruntime  # noqa: F401
    except ImportError:
        logger.info("rapidocr-onnxruntime 未安装，正在自动安装...")
        import subprocess
        import sys
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "rapidocr-onnxruntime", "-q"],
                check=True,
                timeout=180,
            )
            logger.info("rapidocr-onnxruntime 安装成功")
        except Exception as install_error:
            logger.warning("rapidocr-onnxruntime 自动安装失败: %s", install_error)


def _ocr_single_image(image_path: str) -> str:
    """对单张图片做 OCR，返回识别文字（跨平台，多方案降级）。

    降级策略：
    1. rapidocr-onnxruntime（Win/Mac/Linux 全平台）
    2. macOS Vision PyObjC（仅 macOS）
    3. pytesseract（Win/Mac/Linux，需安装 Tesseract 引擎）
    """
    # 方案 1：rapidocr（跨平台首选）
    _ensure_rapidocr()
    try:
        from rapidocr_onnxruntime import RapidOCR
        ocr = RapidOCR()
        result, _ = ocr(image_path)
        if result:
            return "\n".join([line[1] for line in result if line[1]])
        return ""
    except ImportError:
        logger.debug("rapidocr-onnxruntime 不可用，尝试 macOS Vision")
    except Exception as rapid_error:
        logger.warning("rapidocr OCR 识别失败: %s，尝试 macOS Vision", rapid_error)

    # 方案 2：macOS Vision（仅 macOS）
    try:
        text = _ocr_with_macos_vision(image_path)
        if text:
            return text
    except Exception as vision_error:
        logger.debug("macOS Vision OCR 失败: %s，尝试 pytesseract", vision_error)

    # 方案 3：pytesseract（跨平台通用备选）
    try:
        import pytesseract
        from PIL import Image
        image = Image.open(image_path)
        text = pytesseract.image_to_string(image, lang="chi_sim+eng")
        return text.strip()
    except ImportError:
        logger.warning("pytesseract 未安装，所有 OCR 方案均不可用")
    except Exception as tess_error:
        logger.warning("pytesseract OCR 失败: %s", tess_error)

    return ""


def _ocr_image_files(image_files: list[str]) -> list[dict[str, Any]]:
    """对本地图片文件做 OCR 文字识别（使用 rapidocr-onnxruntime，跨平台）。"""
    results: list[dict[str, Any]] = []
    for index, image_file in enumerate(image_files):
        text = _ocr_single_image(image_file)
        results.append({
            "index": index + 1,
            "file": image_file,
            "text": text,
        })
        if text:
            logger.info("图片 %d OCR 完成: %d 字", index + 1, len(text))
    return results


def _ocr_with_macos_vision(image_path: str) -> str:
    """使用 macOS Vision 框架做 OCR（仅 macOS）。

    通过子进程隔离 ObjC 运行时，避免主进程污染。
    使用 sys.executable 而非硬编码 python3，确保 Windows 兼容。
    """
    import subprocess
    import sys

    script = f"""
import sys
try:
    import Vision, Quartz
    from Foundation import NSURL
except ImportError:
    print("IMPORT_ERROR", end="")
    sys.exit(0)

url = NSURL.fileURLWithPath_({repr(image_path)})
request = Vision.VNRecognizeTextRequest.alloc().init()
request.setRecognitionLanguages_(["zh-Hans", "zh-Hant", "en"])
request.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
request.setUsesLanguageCorrection_(True)
handler = Vision.VNImageRequestHandler.alloc().initWithURL_options_(url, {{}})
success = handler.performRequests_error_([request], None)
if not success[0]:
    sys.exit(0)
results = []
for obs in request.results():
    candidate = obs.topCandidates_(1)
    if candidate and len(candidate) > 0:
        results.append(str(candidate[0].string()))
print("\\n".join(results), end="")
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        timeout=30,
    )
    output = result.stdout.strip()
    if output == "IMPORT_ERROR":
        raise ImportError("PyObjC Vision 框架未安装（仅 macOS 可用）")
    return output


# ──────────────────────────────── Markdown 报告 ────────────────────────────────

def _save_as_markdown(
    article_id: str,
    title: str,
    account_name: str,
    author: str,
    publish_time: str,
    content: str,
    image_texts: list[dict],
    output_dir: Path,
) -> str | None:
    """生成 Markdown 分析报告。"""
    lines: list[str] = []

    # 标题
    display_title = title if title else f"微信公众号文章 {article_id}"
    lines.append(f"# {display_title}")
    lines.append("")

    # 元信息
    if account_name or author or publish_time:
        if account_name:
            lines.append(f"**公众号**：{account_name}")
        if author:
            lines.append(f"**作者**：{author}")
        if publish_time:
            lines.append(f"**发布时间**：{publish_time}")
        lines.append("")
        lines.append("---")
        lines.append("")

    # 正文
    if content:
        lines.append("## 文章正文")
        lines.append("")
        lines.append(content)
        lines.append("")

    # 图片 OCR
    ocr_texts = [item for item in image_texts if item.get("text")]
    if ocr_texts:
        lines.append("## 图片内容（OCR 识别）")
        lines.append("")
        for item in ocr_texts:
            lines.append(f"### 图片 {item['index']}")
            lines.append("")
            lines.append(item["text"])
            lines.append("")

    # 内容分析
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
    """从文章 URL 提取唯一标识符。"""
    # 优先取 URL path 里的 ID（/s/xxxxx 格式）
    path_match = re.search(r"/s/([A-Za-z0-9_-]+)", article_url)
    if path_match:
        return path_match.group(1)[:32]
    # 降级取 URL hash
    return hashlib.sha256(article_url.encode()).hexdigest()[:16]
