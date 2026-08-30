"""小红书笔记内容提取器。

支持两种输入方式：
1. feed_id + xsec_token（需要浏览器）：通过 CDP 获取笔记正文和图片列表
2. image_urls（无需浏览器）：直接批量下载图片到本地

图片下载特性：
- SHA256 缓存去重，避免重复下载
- 支持 jpg/png/webp/gif 等常见格式
- 自动推断文件扩展名
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

from .path_guard import safe_output_dir

logger = logging.getLogger(__name__)

_DEFAULT_OUTPUT_DIR = Path.home() / ".content-breakdown" / "output" / "xhs"

_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}

_DOWNLOAD_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.xiaohongshu.com/",
}


# ──────────────────────────────── 公共接口 ────────────────────────────────

def download_images(
    image_urls: list[str],
    output_dir: str | None = None,
    prefix: str = "",
) -> dict[str, Any]:
    """批量下载图片到本地（无需浏览器）。

    Args:
        image_urls: 图片 URL 列表。
        output_dir: 保存目录（默认 ~/.content-breakdown/output/xhs/images）。
        prefix: 文件名前缀（如 feed_id）。

    Returns:
        {
            "success": bool,
            "downloaded": list[str],   # 成功下载的本地路径列表
            "failed": list[str],       # 下载失败的 URL 列表
            "total": int,
            "error": str | None,
        }
    """
    save_dir = safe_output_dir(output_dir) if output_dir else _DEFAULT_OUTPUT_DIR / "images"
    save_dir.mkdir(parents=True, exist_ok=True)

    downloaded: list[str] = []
    failed: list[str] = []

    session = requests.Session()
    session.headers.update(_DOWNLOAD_HEADERS)

    for image_url in image_urls:
        try:
            local_path = _download_single_image(session, image_url, save_dir, prefix)
            downloaded.append(local_path)
            logger.info("下载成功: %s -> %s", image_url[:60], local_path)
        except Exception as download_error:
            failed.append(image_url)
            logger.warning("下载失败 %s: %s", image_url[:60], download_error)

    return {
        "success": len(downloaded) > 0,
        "downloaded": downloaded,
        "failed": failed,
        "total": len(image_urls),
        "error": None if downloaded else "所有图片下载失败",
    }



def extract_from_metadata(
    metadata: dict[str, Any],
    output_dir: str | None = None,
    download_images_flag: bool = True,
    extract_keyframes: bool = False,
) -> dict[str, Any]:
    """从 Agent 通过 browser_use 获取的元数据提取笔记内容。

    Agent 通过 browser_use 打开小红书页面后，从 window.__INITIAL_STATE__ 获取到：
    - feed_id, title, content, note_type, image_urls, video_url, 互动数据, comments

    本函数根据这些数据：
    - 图文笔记：下载图片到本地
    - 视频笔记：下载视频 → 提取音频 → ASR 转录

    Args:
        metadata: Agent 传入的元数据字典，包含：
            - feed_id (str): 笔记 ID
            - title (str): 笔记标题
            - content (str): 正文内容
            - note_type (str): "normal"（图文）或 "video"（视频）
            - image_urls (list[str]): 图片 URL 列表（图文笔记）
            - video_url (str): 视频直链（视频笔记）
            - like_count (int): 点赞数
            - collect_count (int): 收藏数
            - comment_count (int): 评论数
            - comments (list[dict]): 评论列表
        output_dir: 输出目录。
        download_images_flag: 是否下载图片到本地。
        extract_keyframes: 是否提取关键帧截图。

    Returns:
        dict with success, feed_id, title, content, image_urls, image_files, etc.
    """
    out_dir = safe_output_dir(output_dir) if output_dir else _DEFAULT_OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    feed_id = metadata.get("feed_id", "unknown")
    title = metadata.get("title", "")
    content = metadata.get("content", "")
    note_type = metadata.get("note_type", "normal")
    image_urls = metadata.get("image_urls", [])
    video_url = metadata.get("video_url")
    comments = metadata.get("comments", [])

    result: dict[str, Any] = {
        "success": True,
        "feed_id": feed_id,
        "title": title,
        "content": content,
        "content_file": None,
        "note_type": note_type,
        "image_urls": image_urls,
        "image_files": [],
        "video_url": video_url,
        "transcript_text": "",
        "transcript_file": None,
        "like_count": metadata.get("like_count", 0),
        "collect_count": metadata.get("collect_count", 0),
        "comment_count": metadata.get("comment_count", 0),
        "comments": comments,
        "keyframes": None,
        "error": None,
    }

    # 保存正文
    if content:
        content_file = out_dir / f"{feed_id}_content.txt"
        full_text = f"# {title}\n\n{content}" if title else content
        content_file.write_text(full_text, encoding="utf-8")
        result["content_file"] = str(content_file)

    # 视频笔记：下载视频 → 提取音频 → ASR 转录
    if note_type == "video" and video_url:
        logger.info("检测到视频笔记，开始 ASR 转录...")
        transcript_text, transcript_file, asr_segments, keyframes = _transcribe_xhs_video(
            video_url=video_url,
            feed_id=feed_id,
            output_dir=out_dir,
            extract_keyframes=extract_keyframes,
        )
        result["transcript_text"] = transcript_text
        result["transcript_file"] = transcript_file
        if keyframes:
            result["keyframes"] = keyframes
        if transcript_text:
            logger.info("视频转录成功，字数: %d", len(transcript_text))
        else:
            logger.warning("视频转录失败或无内容")

    # 图文笔记：下载图片
    elif download_images_flag and image_urls:
        images_dir = out_dir / f"{feed_id}_images"
        download_result = download_images(image_urls, str(images_dir), prefix=feed_id)
        result["image_files"] = download_result["downloaded"]
        logger.info(
            "图片下载完成: %d/%d 张",
            len(download_result["downloaded"]),
            len(image_urls),
        )

    return result


def extract_image_texts_from_dir(
    image_dir: str,
    output_dir: str | None = None,
) -> dict[str, Any]:
    """对本地图片目录执行 OCR 识别文字。

    Args:
        image_dir: 已下载图片的目录路径。
        output_dir: 输出目录（保存合并文本）。

    Returns:
        {
            "success": bool,
            "image_texts": list[dict],  # [{"index": 0, "text": "...", "file": "..."}]
            "combined_text": str,
            "error": str | None,
        }
    """
    import os

    image_path = Path(image_dir)
    if not image_path.exists() or not image_path.is_dir():
        return {
            "success": False,
            "image_texts": [],
            "combined_text": "",
            "error": f"图片目录不存在: {image_dir}",
        }

    out_dir = safe_output_dir(output_dir) if output_dir else image_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    # 找到目录中的图片文件
    image_extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
    image_files = sorted([
        f for f in image_path.iterdir()
        if f.suffix.lower() in image_extensions
    ])

    if not image_files:
        return {
            "success": False,
            "image_texts": [],
            "combined_text": "",
            "error": f"目录中未找到图片文件: {image_dir}",
        }

    logger.info("对 %d 张图片执行 OCR: %s", len(image_files), image_dir)

    image_texts: list[dict] = []
    for index, img_file in enumerate(image_files):
        ocr_text = _ocr_with_vision(str(img_file))
        image_texts.append({
            "index": index,
            "text": ocr_text,
            "file": str(img_file),
            "error": None if ocr_text else "无文字内容",
        })
        if ocr_text:
            logger.info("图片 %d OCR 完成: %d 字", index + 1, len(ocr_text))

    combined_text = "\n\n---\n\n".join(
        f"[图片 {item['index'] + 1}]\n{item['text']}"
        for item in image_texts
        if item.get("text")
    )

    # 保存合并文本
    if combined_text:
        feed_id = image_path.name.replace("_images", "")
        combined_file = out_dir / f"{feed_id}_image_texts.txt"
        combined_file.write_text(combined_text, encoding="utf-8")
        logger.info("OCR 结果已保存: %s", combined_file)

    return {
        "success": len(image_texts) > 0,
        "image_texts": image_texts,
        "combined_text": combined_text,
        "error": None,
    }

# ──────────────────────────────── 内部实现 ────────────────────────────────

def _transcribe_xhs_video(
    video_url: str,
    feed_id: str,
    output_dir: Path,
    extract_keyframes: bool = False,
) -> tuple[str, str | None, list, list]:
    """下载小红书视频并做 ASR 转录，返回 (转录文本, 转录文件路径, asr_segments, keyframes)。

    复用 bcut_asr 的能力：
    1. 下载视频到临时文件
    2. 提取音频（WAV 16kHz 单声道）
    3. 必剪云端 ASR 转录
    4. 保存转录文本
    5. 可选：提取关键帧截图（在视频清理前执行）

    Args:
        video_url: 视频直链 URL。
        feed_id: 笔记 ID，用于文件命名。
        output_dir: 输出目录。
        extract_keyframes: 是否提取关键帧截图（仅用户明确要求时传 True）。

    Returns:
        (转录文本, 转录文件路径, asr_segments, keyframes)，失败时返回 ("", None, [], [])。
    """
    import ssl
    import urllib.request
    import tempfile

    from .bcut_asr import extract_audio_with_ffmpeg, transcribe_with_bcut

    # 下载视频到临时文件
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    video_path = output_dir / f"{feed_id}_video_temp.mp4"
    try:
        req = urllib.request.Request(video_url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Referer": "https://www.xiaohongshu.com/",
        })
        with urllib.request.urlopen(req, timeout=60, context=ssl_context) as resp:
            video_path.write_bytes(resp.read())
        file_size_mb = video_path.stat().st_size / 1024 / 1024
        logger.info("视频下载成功: %s (%.1fMB)", video_path.name, file_size_mb)
    except Exception as download_error:
        logger.warning("视频下载失败: %s", download_error)
        return "", None, [], []

    # 提取音频
    audio_path = str(output_dir / f"{feed_id}_audio_temp.wav")
    audio_ok = extract_audio_with_ffmpeg(str(video_path), audio_path)
    if not audio_ok:
        logger.warning("音频提取失败")
        video_path.unlink(missing_ok=True)
        return "", None, [], []

    # extract_audio_with_ffmpeg 可能输出 .mp3 或 .aac 而非 .wav，找到实际的音频文件
    if not Path(audio_path).exists():
        for alt_ext in [".mp3", ".aac"]:
            alt_path = str(output_dir / f"{feed_id}_audio_temp{alt_ext}")
            if Path(alt_path).exists() and Path(alt_path).stat().st_size > 0:
                logger.info("使用替代音频文件: %s", alt_path)
                audio_path = alt_path
                break

    # 必剪云端 ASR 转录（transcribe_with_bcut 返回 dict）
    try:
        asr_result = transcribe_with_bcut(audio_path, output_dir=str(output_dir))
        transcript_text = asr_result.get("text", "") if asr_result.get("success") else ""
        transcript_output_file = asr_result.get("output_file")
        asr_segments = asr_result.get("segments", []) if asr_result.get("success") else []
        if transcript_text:
            logger.info("转录完成，字数: %d", len(transcript_text))

            # 关键帧提取（可选，仅用户明确要求时执行，在视频清理前）
            keyframes: list = []
            if extract_keyframes and asr_segments:
                logger.info("开始提取关键帧...")
                from .keyframe_extractor import extract_keyframes_from_timestamps
                keyframes = extract_keyframes_from_timestamps(
                    video_path=str(video_path),
                    segments=asr_segments,
                    output_dir=str(output_dir),
                    video_stem=feed_id,
                )
                successful_frames = sum(1 for frame in keyframes if frame.get("screenshot"))
                logger.info("关键帧提取完成：%d 帧", successful_frames)

            return transcript_text, transcript_output_file, asr_segments, keyframes
        else:
            logger.warning("必剪 ASR 转录无内容: %s", asr_result.get("error", ""))
    except Exception as asr_error:
        logger.warning("必剪 ASR 转录失败: %s", asr_error)
    finally:
        # 清理临时文件
        video_path.unlink(missing_ok=True)
        Path(audio_path).unlink(missing_ok=True)

    return "", None, [], []


def _download_single_image(
    session: requests.Session,
    image_url: str,
    save_dir: Path,
    prefix: str,
) -> str:
    """下载单张图片，返回本地路径（SHA256 缓存去重）。"""
    url_hash = hashlib.sha256(image_url.encode()).hexdigest()[:16]
    ext = _detect_image_extension(image_url)
    filename_prefix = f"{prefix}_" if prefix else ""
    filename = f"{filename_prefix}img_{url_hash}_{int(time.time())}{ext}"
    filepath = save_dir / filename

    # 检查是否已有同 hash 的文件
    existing = _find_cached_file(save_dir, url_hash)
    if existing:
        logger.debug("使用缓存图片: %s", existing)
        return existing

    resp = session.get(image_url, timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(f"下载失败 (status={resp.status_code}): {image_url}")

    filepath.write_bytes(resp.content)
    return str(filepath)

def _detect_image_extension(url: str) -> str:
    """从 URL 推断图片扩展名。"""
    parsed = urlparse(url)
    path = parsed.path.lower()
    for ext in _IMAGE_EXTENSIONS:
        if path.endswith(ext):
            return ext
    return ".jpg"


def _find_cached_file(save_dir: Path, url_hash: str) -> str | None:
    """查找已有同 hash 的缓存文件。"""
    prefix = f"img_{url_hash}_"
    for filename in os.listdir(save_dir):
        if filename.startswith(prefix) or f"_{url_hash}_" in filename:
            return str(save_dir / filename)
    return None




def _parse_comments(comments_raw: dict) -> list[dict]:
    """解析评论数据。"""
    if not isinstance(comments_raw, dict):
        return []
    comment_list = comments_raw.get("comments", [])
    if not isinstance(comment_list, list):
        return []
    result = []
    for comment in comment_list:
        if not isinstance(comment, dict):
            continue
        result.append({
            "id": comment.get("id", ""),
            "content": comment.get("content", ""),
            "user": comment.get("userInfo", {}).get("nickname", ""),
            "like_count": comment.get("likeCount", 0),
        })
    return result


def _parse_count(count_text: str) -> int:
    """解析数量文本（如 '1.2w' -> 12000）。"""
    if not count_text:
        return 0
    try:
        count_text = str(count_text).strip()
        if "w" in count_text.lower() or "万" in count_text:
            import re
            num_part = re.sub(r"[^\d.]", "", count_text)
            return int(float(num_part) * 10000) if num_part else 0
        import re
        num_part = re.sub(r"[^\d]", "", count_text)
        return int(num_part) if num_part else 0
    except (ValueError, TypeError):
        return 0


# ──────────────────────────────── Markdown 报告 ────────────────────────────────

def _save_as_markdown(
    filepath: Path,
    feed_id: str,
    title: str,
    content: str,
    image_texts: list[dict],
    like_count: int,
    collect_count: int,
    comment_count: int,
) -> None:
    """将笔记正文、图片 OCR 文字和内容分析保存为 Markdown 文件。

    Markdown 结构：
    - 标题
    - 互动数据（点赞/收藏/评论）
    - 笔记正文
    - 图片内容（OCR，每张图片一个小节）
    - 内容分析（主题、关键信息点、内容结构）

    Args:
        filepath: 保存路径（.md 文件）。
        feed_id: 笔记 ID。
        title: 笔记标题。
        content: 笔记正文。
        image_texts: 图片 OCR 结果列表。
        like_count: 点赞数。
        collect_count: 收藏数。
        comment_count: 评论数。
    """
    lines: list[str] = []

    # ── 标题 ──
    display_title = title if title else f"小红书笔记 {feed_id}"
    lines.append(f"# {display_title}")
    lines.append("")

    # ── 互动数据 ──
    lines.append(f"> ❤️ 点赞 {like_count}　⭐ 收藏 {collect_count}　💬 评论 {comment_count}")
    lines.append("")

    # ── 笔记正文 ──
    if content:
        lines.append("## 笔记正文")
        lines.append("")
        lines.append(content)
        lines.append("")

    # ── 图片内容（OCR）──
    valid_image_texts = [item for item in image_texts if item.get("text")]
    if valid_image_texts:
        lines.append("## 图片内容（OCR 识别）")
        lines.append("")
        for item in valid_image_texts:
            image_number = item["index"] + 1
            lines.append(f"### 图片 {image_number}")
            lines.append("")
            lines.append(item["text"])
            lines.append("")

    # ── 内容分析 ──
    lines.append("## 内容分析")
    lines.append("")

    all_text = content + "\n" + "\n".join(
        item["text"] for item in image_texts if item.get("text")
    )
    analysis = _analyze_content(title, all_text, image_count=len(image_texts))

    lines.append(f"**核心主题**：{analysis['theme']}")
    lines.append("")

    if analysis["key_points"]:
        lines.append("**关键信息点**：")
        for point in analysis["key_points"]:
            lines.append(f"- {point}")
        lines.append("")

    lines.append(f"**内容结构**：{analysis['structure']}")
    lines.append("")

    if analysis["content_type"]:
        lines.append(f"**内容类型**：{analysis['content_type']}")
        lines.append("")

    filepath.write_text("\n".join(lines), encoding="utf-8")


def _analyze_content(title: str, full_text: str, image_count: int) -> dict[str, Any]:
    """基于正文和图片 OCR 文字做轻量级内容分析（纯文本，不调用 LLM）。

    分析维度：
    - 核心主题：从标题和高频词推断
    - 关键信息点：提取数字、列表项、重要句子
    - 内容结构：判断是否有分点/分段/图文结合
    - 内容类型：攻略/测评/分享/教程等

    Args:
        title: 笔记标题。
        full_text: 正文 + 图片 OCR 合并文本。
        image_count: 图片数量。

    Returns:
        {
            "theme": str,
            "key_points": list[str],
            "structure": str,
            "content_type": str,
        }
    """
    import re

    # ── 核心主题 ──
    theme = title.strip() if title else "未知主题"
    # 去掉 emoji 和话题标签，保留核心词
    theme_clean = re.sub(r"[#＃@][\w\u4e00-\u9fff]+", "", theme)
    theme_clean = re.sub(r"[\U00010000-\U0010ffff]", "", theme_clean).strip()
    if theme_clean:
        theme = theme_clean

    # ── 关键信息点：提取数字相关句子 + 列表项 ──
    key_points: list[str] = []
    seen_points: set[str] = set()

    # 提取含数字的短句（价格、数量、时间等关键信息）
    number_sentences = re.findall(
        r"[^。！？\n]{5,40}(?:\d+(?:\.\d+)?(?:元|円|块|万|亿|%|折|天|月|年|次|张|个|款|版)[^。！？\n]{0,20})",
        full_text,
    )
    for sentence in number_sentences[:5]:
        sentence = sentence.strip()
        if sentence and sentence not in seen_points:
            key_points.append(sentence)
            seen_points.add(sentence)

    # 提取列表项（以数字序号、emoji 序号、✅❌⭐等开头的行）
    list_items = re.findall(
        r"^[\s]*(?:[①②③④⑤⑥⑦⑧⑨⑩1-9][️⃣]?[、.．]?|[✅❌⭐💡📌🔑])\s*(.{5,50})",
        full_text,
        re.MULTILINE,
    )
    for item in list_items[:5]:
        item = item.strip()
        if item and item not in seen_points:
            key_points.append(item)
            seen_points.add(item)

    # 如果没提取到，取正文前两句话
    if not key_points and full_text:
        first_sentences = re.split(r"[。！？\n]", full_text.strip())
        for sentence in first_sentences[:2]:
            sentence = sentence.strip()
            if len(sentence) > 10:
                key_points.append(sentence)

    # ── 内容结构 ──
    has_numbered_list = bool(re.search(r"[①②③④⑤1-9][️⃣]?[、.．]", full_text))
    has_sections = full_text.count("\n") > 5
    has_images = image_count > 0

    structure_parts: list[str] = []
    if has_numbered_list:
        structure_parts.append("分点列举")
    if has_sections:
        structure_parts.append("多段落")
    if has_images:
        structure_parts.append(f"图文结合（{image_count} 张图）")
    structure = " + ".join(structure_parts) if structure_parts else "纯文字"

    # ── 内容类型 ──
    content_type = _infer_content_type(title, full_text)

    return {
        "theme": theme,
        "key_points": key_points[:6],
        "structure": structure,
        "content_type": content_type,
    }


def _infer_content_type(title: str, full_text: str) -> str:
    """根据标题和正文关键词推断内容类型。"""
    combined = (title + full_text).lower()

    type_keywords: list[tuple[str, list[str]]] = [
        ("攻略/指南", ["攻略", "指南", "教程", "怎么", "如何", "步骤", "方法", "技巧", "秘诀"]),
        ("测评/对比", ["测评", "对比", "评测", "推荐", "种草", "避坑", "踩雷", "好用", "不好用"]),
        ("经验分享", ["分享", "经验", "心得", "感受", "体验", "亲测", "实测", "真实"]),
        ("好物推荐", ["好物", "推荐", "必买", "必入", "值得买", "好用", "神器", "宝藏"]),
        ("旅行游记", ["旅行", "旅游", "游记", "打卡", "景点", "酒店", "民宿", "出行"]),
        ("美食探店", ["美食", "探店", "好吃", "餐厅", "饭店", "菜", "吃", "味道"]),
        ("穿搭时尚", ["穿搭", "ootd", "搭配", "衣服", "时尚", "风格", "单品"]),
    ]

    for content_type, keywords in type_keywords:
        if any(keyword in combined for keyword in keywords):
            return content_type

    return "生活记录"


# ──────────────────────────────── 图片 OCR ────────────────────────────────

# 小红书笔记图片的候选 CSS 选择器（按优先级排列）
_XHS_IMAGE_SELECTORS = [
    ".swiper-slide img",
    ".note-slider img",
    ".carousel img",
    ".image-container img",
    "section.note-detail img",
    ".media-container img",
]




# ──────────────────────────────── 图片 OCR ────────────────────────────────

def _ocr_with_vision(image_path: str) -> str:
    """对图片进行 OCR 文字识别（跨平台）。

    降级策略（按优先级）：
    1. rapidocr-onnxruntime：纯 Python，Windows/macOS/Linux 全支持，中文识别效果好
    2. macOS Vision（PyObjC）：macOS 专属，系统级 OCR，无需额外安装
    3. pytesseract：跨平台通用备选，需安装 Tesseract 引擎
    4. macOS Vision（swift 命令行）：macOS 专属兜底，系统自带 swift

    Args:
        image_path: 本地图片文件路径（PNG/JPG）。

    Returns:
        识别出的文字字符串，识别失败时返回空字符串。
    """
    # 优先：跨平台 rapidocr
    try:
        return _ocr_via_rapidocr(image_path)
    except ImportError:
        logger.debug("rapidocr 未安装，尝试 macOS Vision OCR")
    except Exception as rapidocr_error:
        logger.warning("rapidocr OCR 失败: %s，尝试 macOS Vision", rapidocr_error)

    # 降级：macOS Vision（PyObjC）
    try:
        return _ocr_via_pyobjc(image_path)
    except ImportError:
        logger.debug("PyObjC 未安装，尝试 pytesseract")
    except Exception as pyobjc_error:
        logger.warning("PyObjC OCR 失败: %s，尝试 pytesseract", pyobjc_error)

    # 降级：pytesseract（跨平台通用，Windows/macOS/Linux）
    try:
        return _ocr_via_tesseract(image_path)
    except ImportError:
        logger.debug("pytesseract 未安装，尝试 swift 命令行 OCR")
    except Exception as tesseract_error:
        logger.warning("pytesseract OCR 失败: %s，尝试 swift 命令行", tesseract_error)

    # 最终兜底：macOS Vision（swift 命令行）
    try:
        return _ocr_via_swift(image_path)
    except Exception as swift_error:
        logger.warning("所有 OCR 方案均失败: %s", swift_error)
        return ""


def _ocr_via_rapidocr(image_path: str) -> str:
    """通过 rapidocr-onnxruntime 进行 OCR（跨平台，Windows/macOS/Linux 均支持）。

    安装：pip install rapidocr-onnxruntime

    中文识别基于 PaddleOCR 模型，准确率高，无需 GPU。
    """
    from rapidocr_onnxruntime import RapidOCR

    engine = RapidOCR()
    ocr_result, _ = engine(image_path)
    if not ocr_result:
        return ""
    # ocr_result 格式：[[坐标, 文字, 置信度], ...]
    return "\n".join(item[1] for item in ocr_result if item and len(item) >= 2)


def _ocr_via_pyobjc(image_path: str) -> str:
    """通过 PyObjC 调用 macOS Vision 框架进行 OCR（macOS 专属）。

    安装：pip install pyobjc-framework-Vision pyobjc-framework-Quartz
    """
    import subprocess
    import sys

    # 用子进程隔离 ObjC 运行时，避免主进程污染
    ocr_script = f"""
import sys
try:
    import Quartz
    import Vision
    from Foundation import NSURL
except ImportError:
    print("IMPORT_ERROR", end="")
    sys.exit(0)

image_url = NSURL.fileURLWithPath_({repr(image_path)})
request = Vision.VNRecognizeTextRequest.alloc().init()
request.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
request.setUsesLanguageCorrection_(True)
request.setRecognitionLanguages_(["zh-Hans", "zh-Hant", "en-US"])

handler = Vision.VNImageRequestHandler.alloc().initWithURL_options_(image_url, None)
success = handler.performRequests_error_([request], None)

if not success[0]:
    sys.exit(0)

texts = []
for obs in request.results():
    candidate = obs.topCandidates_(1)
    if candidate and len(candidate) > 0:
        texts.append(str(candidate[0].string()))

print("\\n".join(texts), end="")
"""
    proc = subprocess.run(
        [sys.executable, "-c", ocr_script],
        capture_output=True,
        text=True,
        timeout=30,
    )
    output = proc.stdout.strip()
    if output == "IMPORT_ERROR":
        raise ImportError("PyObjC Vision 框架未安装")
    return output


def _ocr_via_swift(image_path: str) -> str:
    """通过 swift 命令行脚本调用 macOS Vision 框架进行 OCR（macOS 专属兜底）。

    无需额外安装，macOS 系统自带 swift。
    """
    import subprocess
    import tempfile

    swift_code = f"""
import Vision
import Foundation

let imageURL = URL(fileURLWithPath: "{image_path}")
guard let cgImage = NSImage(contentsOf: imageURL)?.cgImage(forProposedRect: nil, context: nil, hints: nil) else {{
    exit(0)
}}

let request = VNRecognizeTextRequest {{ request, error in
    guard let observations = request.results as? [VNRecognizedTextObservation] else {{ return }}
    for obs in observations {{
        if let top = obs.topCandidates(1).first {{
            print(top.string)
        }}
    }}
}}
request.recognitionLevel = .accurate
request.usesLanguageCorrection = true
request.recognitionLanguages = ["zh-Hans", "zh-Hant", "en-US"]

let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])
try? handler.perform([request])
"""
    with tempfile.NamedTemporaryFile(suffix=".swift", mode="w", delete=False) as swift_file:
        swift_file.write(swift_code)
        swift_file_path = swift_file.name

    try:
        proc = subprocess.run(
            ["swift", swift_file_path],
            capture_output=True,
            text=True,
            timeout=60,
        )
        return proc.stdout.strip()
    finally:
        import os as _os
        _os.unlink(swift_file_path)

def _ocr_via_tesseract(image_path: str) -> str:
    """通过 pytesseract 进行 OCR（跨平台通用备选）。

    安装：
      pip install pytesseract Pillow
      系统需安装 Tesseract 引擎：
        - macOS: brew install tesseract tesseract-lang
        - Windows: https://github.com/UB-Mannheim/tesseract/wiki 下载安装
        - Linux: apt install tesseract-ocr tesseract-ocr-chi-sim
    """
    import pytesseract
    from PIL import Image

    image = Image.open(image_path)
    text = pytesseract.image_to_string(image, lang="chi_sim+eng")
    return text.strip()
