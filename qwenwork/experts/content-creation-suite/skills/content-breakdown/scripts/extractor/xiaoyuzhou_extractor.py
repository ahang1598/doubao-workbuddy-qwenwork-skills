"""小宇宙播客内容提取器。

无需登录，无需浏览器，直接 HTTP 请求解析 __NEXT_DATA__ 获取音频直链，
下载音频后使用必剪云端 ASR 进行转录，生成 Markdown 报告。
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any

import requests

from .path_guard import safe_output_dir

logger = logging.getLogger(__name__)

# 请求头，模拟正常浏览器访问
_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://www.xiaoyuzhoufm.com/",
}

# 音频下载请求头（需要 Referer 防盗链）
_AUDIO_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.xiaoyuzhoufm.com/",
}


def _parse_episode_id(url_or_id: str) -> str:
    """从 URL 或 episode ID 中提取 episode ID。

    支持格式：
    - https://www.xiaoyuzhoufm.com/episode/6761711b7d8426f692d99dfd
    - 6761711b7d8426f692d99dfd
    """
    url_or_id = url_or_id.strip()
    match = re.search(r"episode/([a-f0-9]{24})", url_or_id)
    if match:
        return match.group(1)
    # 直接是 24 位 hex ID
    if re.fullmatch(r"[a-f0-9]{24}", url_or_id):
        return url_or_id
    raise ValueError(f"无法解析小宇宙 episode ID，请提供完整链接或 24 位 ID: {url_or_id!r}")


def _fetch_episode_data(episode_id: str) -> dict[str, Any]:
    """请求小宇宙 episode 页面，解析 __NEXT_DATA__ 返回 episode 数据。"""
    url = f"https://www.xiaoyuzhoufm.com/episode/{episode_id}"
    logger.info("正在请求小宇宙页面: %s", url)

    response = requests.get(url, headers=_DEFAULT_HEADERS, timeout=30)
    response.raise_for_status()

    html = response.text
    match = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
        html,
        re.DOTALL,
    )
    if not match:
        raise RuntimeError("未在页面中找到 __NEXT_DATA__，页面结构可能已变更")

    next_data = json.loads(match.group(1))
    page_props = next_data.get("props", {}).get("pageProps", {})

    if not page_props or "episode" not in page_props:
        status_code = page_props.get("statusCode")
        if status_code == 404:
            raise ValueError(f"Episode 不存在（404）: {episode_id}")
        raise RuntimeError(f"pageProps 中未找到 episode 数据，statusCode={status_code}")

    return page_props["episode"]


def _format_duration(seconds: int) -> str:
    """将秒数格式化为 HH:MM:SS 或 MM:SS。"""
    if seconds <= 0:
        return "未知"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def _download_audio(audio_url: str, output_path: Path) -> None:
    """流式下载音频文件，显示进度。"""
    logger.info("正在下载音频: %s", audio_url)
    response = requests.get(audio_url, headers=_AUDIO_HEADERS, stream=True, timeout=60)
    response.raise_for_status()

    total_size = int(response.headers.get("content-length", 0))
    downloaded = 0
    chunk_size = 1024 * 1024  # 1MB

    with open(output_path, "wb") as audio_file:
        for chunk in response.iter_content(chunk_size=chunk_size):
            if chunk:
                audio_file.write(chunk)
                downloaded += len(chunk)
                if total_size > 0:
                    progress = downloaded / total_size * 100
                    logger.info("下载进度: %.1f%% (%d/%d MB)", progress, downloaded // 1024 // 1024, total_size // 1024 // 1024)

    logger.info("音频下载完成: %s (%.1f MB)", output_path.name, output_path.stat().st_size / 1024 / 1024)


def _transcribe_audio(audio_path: Path) -> str:
    """使用必剪云端 ASR 转录音频，返回转录文本。"""
    from extractor.bcut_asr import transcribe_with_bcut

    logger.info("正在使用必剪 ASR 转录音频（可能需要几分钟）...")
    asr_result = transcribe_with_bcut(str(audio_path))

    if not asr_result["success"]:
        error_msg = asr_result.get("error", "未知错误")
        raise RuntimeError(f"必剪 ASR 转录失败: {error_msg}")

    transcript = asr_result["text"]
    logger.info("转录完成，共 %d 字", len(transcript))
    return transcript


def _build_markdown_report(
    episode: dict[str, Any],
    transcript: str,
    audio_path: Path | None,
) -> str:
    """根据 episode 数据和转录文本生成 Markdown 报告。"""
    title = episode.get("title", "未知标题")
    description = episode.get("description", "").strip()
    shownotes = episode.get("shownotes", "").strip()
    duration_seconds = episode.get("duration", 0)
    pub_date = episode.get("pubDate", "")
    episode_id = episode.get("eid", "")

    podcast = episode.get("podcast", {}) or {}
    podcast_title = podcast.get("title", "未知播客")

    episode_url = f"https://www.xiaoyuzhoufm.com/episode/{episode_id}" if episode_id else ""

    lines = [
        f"# {title}",
        "",
        "## 基本信息",
        "",
        f"- **播客**: {podcast_title}",
        f"- **时长**: {_format_duration(duration_seconds)}",
    ]

    if pub_date:
        # 格式化发布时间（去掉毫秒和时区后缀）
        pub_date_clean = pub_date[:10] if len(pub_date) >= 10 else pub_date
        lines.append(f"- **发布时间**: {pub_date_clean}")

    if episode_url:
        lines.append(f"- **链接**: {episode_url}")

    if audio_path:
        lines.append(f"- **音频文件**: {audio_path.name}")

    if description:
        lines.extend([
            "",
            "## 节目简介",
            "",
            description,
        ])

    if shownotes and shownotes != description:
        lines.extend([
            "",
            "## 章节信息（Shownotes）",
            "",
            shownotes,
        ])

    if transcript:
        lines.extend([
            "",
            "## 内容转录",
            "",
            transcript,
        ])
    else:
        lines.extend([
            "",
            "## 内容转录",
            "",
            "（转录失败或已跳过）",
        ])

    return "\n".join(lines)


def extract_episode(
    url_or_id: str,
    output_dir: str = ".",
    skip_transcript: bool = False,
) -> dict[str, Any]:
    """提取小宇宙播客单集内容。

    Args:
        url_or_id: 小宇宙 episode 链接或 24 位 episode ID。
        output_dir: 输出目录，报告和音频文件保存在此。
        skip_transcript: 为 True 时跳过音频下载和转录，仅提取文字信息。

    Returns:
        包含提取结果的字典：
        {
            "success": bool,
            "title": str,
            "podcast_title": str,
            "description": str,
            "duration": int,          # 秒
            "audio_url": str,
            "transcript": str,        # 转录文本，skip_transcript=True 时为空
            "report_path": str,       # Markdown 报告路径
            "audio_path": str,        # 音频文件路径，skip_transcript=True 时为空
            "error": str,             # 仅在 success=False 时存在
        }
    """
    try:
        episode_id = _parse_episode_id(url_or_id)
    except ValueError as parse_error:
        return {"success": False, "error": str(parse_error)}

    output_path = safe_output_dir(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    try:
        episode = _fetch_episode_data(episode_id)
    except Exception as fetch_error:
        return {"success": False, "error": f"获取 episode 数据失败: {fetch_error}"}

    title = episode.get("title", "未知标题")
    description = episode.get("description", "").strip()
    duration_seconds = episode.get("duration", 0)
    podcast = episode.get("podcast", {}) or {}
    podcast_title = podcast.get("title", "未知播客")

    # 获取音频直链
    enclosure = episode.get("enclosure") or {}
    audio_url = enclosure.get("url", "")
    if not audio_url:
        # 兜底：尝试 media.source.url
        media = episode.get("media") or {}
        source = media.get("source") or {}
        audio_url = source.get("url", "")

    logger.info("标题: %s", title)
    logger.info("播客: %s", podcast_title)
    logger.info("时长: %s", _format_duration(duration_seconds))
    logger.info("音频链接: %s", audio_url)

    # 安全文件名（去掉特殊字符）
    safe_title = re.sub(r'[\\/:*?"<>|]', "_", title)[:60]
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    base_name = f"xiaoyuzhou_{safe_title}_{timestamp}"

    audio_path: Path | None = None
    transcript = ""

    if not skip_transcript:
        if not audio_url:
            logger.warning("未找到音频直链，跳过下载和转录")
        else:
            # 根据 URL 后缀确定扩展名
            audio_ext = Path(audio_url.split("?")[0]).suffix or ".m4a"
            audio_path = output_path / f"{base_name}{audio_ext}"

            try:
                _download_audio(audio_url, audio_path)
                transcript = _transcribe_audio(audio_path)
            except Exception as transcribe_error:
                logger.warning("音频转录失败: %s", transcribe_error)
                transcript = ""

    # 生成 Markdown 报告
    report_content = _build_markdown_report(episode, transcript, audio_path)
    report_path = output_path / f"{base_name}.md"
    report_path.write_text(report_content, encoding="utf-8")
    logger.info("报告已保存: %s", report_path)

    return {
        "success": True,
        "title": title,
        "podcast_title": podcast_title,
        "description": description,
        "duration": duration_seconds,
        "audio_url": audio_url,
        "transcript": transcript,
        "report_path": str(report_path),
        "audio_path": str(audio_path) if audio_path else "",
    }
