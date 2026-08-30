"""抖音视频内容提取器。

支持三种输入方式：
1. play_url（视频直链）：直接下载视频 → 提取音频 → ASR 转录
2. video_file（本地视频文件）：提取音频 → ASR 转录
3. video_id（需要浏览器）：通过 CDP 获取视频信息和字幕

字幕提取策略（自动降级）：
  策略 0：API 字幕（subtitle_infos，来自 aweme 接口拦截）
  策略 1：必剪云端 ASR（B站免费，中文优化，视频 ≤ 60s）
  策略 2：Whisper 本地转录（视频 ≤ 16s，需安装 openai-whisper）
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
import tempfile
import urllib.request
from pathlib import Path
from typing import Any

from .bcut_asr import extract_audio_with_ffmpeg, transcribe_with_bcut
from .path_guard import safe_output_dir

logger = logging.getLogger(__name__)

_DEFAULT_OUTPUT_DIR = Path.home() / ".content-breakdown" / "output" / "douyin"

_REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.douyin.com/",
}

# ──────────────────────────────── 公共接口 ────────────────────────────────

def extract_from_audio_url(
    audio_url: str,
    output_dir: str | None = None,
) -> dict[str, Any]:
    """从音频轨直链提取转录文本（DASH 分离场景，无需下载视频）。

    抖音使用 DASH 音视频分离技术，视频和音频可能是独立的 URL。
    当 Performance API 返回的是纯视频轨（media-video-avc1）时，
    需要获取独立的音频轨 URL（media-audio-und-mp4a）直接下载音频进行 ASR。

    优势：跳过视频下载（50-100MB）和 ffmpeg 音频提取步骤，
    直接下载音频文件（5-15MB），速度更快。

    Args:
        audio_url: 音频轨直链（通常包含 media-audio-und-mp4a）。
        output_dir: 输出目录。

    Returns:
        同 extract_from_play_url 的返回格式。
    """
    import ssl

    out_dir = safe_output_dir(output_dir) if output_dir else _DEFAULT_OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    result: dict[str, Any] = {
        "success": False,
        "subtitle_text": "",
        "transcript_text": "",
        "subtitle_file": None,
        "transcript_file": None,
        "method": None,
        "keyframes": None,
        "error": None,
    }

    # 下载音频文件
    audio_path = out_dir / "audio_temp.m4a"
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    try:
        req = urllib.request.Request(audio_url, headers=_REQUEST_HEADERS)
        with urllib.request.urlopen(req, timeout=60, context=ssl_context) as resp:
            audio_path.write_bytes(resp.read())
        if audio_path.exists() and audio_path.stat().st_size > 0:
            file_size_mb = audio_path.stat().st_size / 1024 / 1024
            logger.info("音频下载成功: %s (%.1fMB)", audio_path.name, file_size_mb)
        else:
            result["error"] = "音频下载失败，文件为空"
            return result
    except Exception as download_error:
        result["error"] = f"音频下载失败: {download_error}"
        logger.warning("音频下载失败: %s", download_error)
        return result

    # 必剪 ASR 支持 m4a 格式，直接转录
    logger.info("尝试必剪云端 ASR 转录（音频轨直传）...")
    bcut_result = transcribe_with_bcut(str(audio_path), str(out_dir))
    if bcut_result["success"]:
        result["success"] = True
        result["subtitle_text"] = bcut_result["text"]
        result["subtitle_file"] = bcut_result["output_file"]
        result["method"] = "bcut_asr"
        result["segments"] = bcut_result.get("segments", [])
        logger.info("必剪 ASR 转录成功（音频轨直传）")
    else:
        result["error"] = f"必剪 ASR 失败: {bcut_result['error']}"
        logger.warning("必剪 ASR 失败: %s", bcut_result["error"])

    # 清理临时音频文件
    audio_path.unlink(missing_ok=True)

    return result

def extract_from_metadata(
    metadata: dict[str, Any],
    output_dir: str | None = None,
    whisper_model: str = "medium",
    skip_transcript: bool = False,
    extract_keyframes: bool = False,
) -> dict[str, Any]:
    """从 Agent 通过 browser_use 获取的元数据提取内容。

    metadata 中可包含：
      - play_url: 视频直链（必须）
      - title: 视频标题（可选）
      - subtitle_infos: 字幕信息列表（可选，有则优先使用 API 字幕）

    Args:
        metadata: 由 Agent 通过 browser_use 获取的元数据字典。
        output_dir: 输出目录。
        whisper_model: Whisper 模型名称。
        skip_transcript: 是否跳过转录。
        extract_keyframes: 是否提取关键帧截图。

    Returns:
        同 extract_from_play_url 的返回格式。
    """
    # 如果有 API 字幕信息，优先使用
    subtitle_infos = metadata.get("subtitle_infos")
    if subtitle_infos:
        result = extract_from_subtitle_infos(
            subtitle_infos=subtitle_infos,
            video_id=metadata.get("video_id", "unknown"),
            output_dir=output_dir,
        )
        if result.get("success") and result.get("subtitle_text"):
            if metadata.get("title"):
                result["title"] = metadata["title"]
            return result

    # 无字幕或字幕提取失败，走视频下载 + ASR 流程
    play_url = metadata.get("play_url")
    if not play_url:
        return {
            "success": False,
            "subtitle_text": "",
            "transcript_text": "",
            "subtitle_file": None,
            "transcript_file": None,
            "method": None,
            "error": "metadata 中缺少 play_url 字段，无法下载视频",
        }

    result = extract_from_play_url(
        play_url=play_url,
        output_dir=output_dir,
        whisper_model=whisper_model,
        skip_transcript=skip_transcript,
        extract_keyframes=extract_keyframes,
        title=metadata.get("title", ""),
    )

    if metadata.get("title"):
        result["title"] = metadata["title"]

    return result



def extract_from_play_url(
    play_url: str,
    output_dir: str | None = None,
    whisper_model: str = "medium",
    skip_transcript: bool = False,
    extract_keyframes: bool = False,
    title: str = "",
) -> dict[str, Any]:
    """从视频直链提取字幕和转录文本（无需浏览器）。

    Args:
        play_url: 抖音视频直链（play_url）。
        output_dir: 输出目录。
        whisper_model: Whisper 模型名称（medium 推荐，base 中文效果差）。
        skip_transcript: 是否跳过转录，只提取字幕。
        extract_keyframes: 是否提取关键帧截图。
        title: 视频标题（传入后作为 Whisper initial_prompt 提升转录质量）。

    Returns:
        同 extract_from_metadata 的返回格式。
    """
    out_dir = safe_output_dir(output_dir) if output_dir else _DEFAULT_OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    result: dict[str, Any] = {
        "success": False,
        "subtitle_text": "",
        "transcript_text": "",
        "subtitle_file": None,
        "transcript_file": None,
        "method": None,
        "error": None,
    }

    # 下载视频到临时目录
    video_path = _download_video(play_url, out_dir)
    if not video_path:
        result["error"] = "视频下载失败，请检查 play_url 是否有效"
        return result

    return _extract_from_video_file(
        video_path=str(video_path),
        output_dir=str(out_dir),
        whisper_model=whisper_model,
        skip_transcript=skip_transcript,
        cleanup_video=True,
        extract_keyframes=extract_keyframes,
        title=title,
    )


def extract_from_video_file(
    video_file: str,
    output_dir: str | None = None,
    whisper_model: str = "medium",
    skip_transcript: bool = False,
    extract_keyframes: bool = False,
    title: str = "",
) -> dict[str, Any]:
    """从本地视频文件提取字幕和转录文本（无需浏览器）。

    Args:
        video_file: 本地视频文件路径。
        output_dir: 输出目录（默认使用视频所在目录）。
        whisper_model: Whisper 模型名称（medium 推荐，base 中文效果差）。
        skip_transcript: 是否跳过转录，只提取字幕。
        extract_keyframes: 是否提取关键帧截图（仅用户明确要求时传 True）。
        title: 视频标题（传入后作为 Whisper initial_prompt 提升转录质量）。

    Returns:
        同 extract_from_play_url。
    """
    video_path = Path(video_file)
    if not video_path.exists():
        return {
            "success": False,
            "subtitle_text": "",
            "transcript_text": "",
            "subtitle_file": None,
            "transcript_file": None,
            "method": None,
            "error": f"视频文件不存在: {video_file}",
        }

    out_dir = safe_output_dir(output_dir) if output_dir else video_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    return _extract_from_video_file(
        video_path=str(video_path),
        output_dir=str(out_dir),
        whisper_model=whisper_model,
        skip_transcript=skip_transcript,
        cleanup_video=False,
        extract_keyframes=extract_keyframes,
        title=title,
    )


def extract_from_subtitle_infos(
    subtitle_infos: list[dict],
    video_id: str,
    output_dir: str | None = None,
) -> dict[str, Any]:
    """从 API 字幕信息直接提取字幕文本（最快，无需下载视频）。

    适用于已通过抖音 aweme API 获取到 subtitle_infos 的场景。

    Args:
        subtitle_infos: 来自 aweme API 的字幕信息列表。
        video_id: 视频 ID（用于命名输出文件）。
        output_dir: 输出目录。

    Returns:
        同 extract_from_play_url。
    """
    out_dir = safe_output_dir(output_dir) if output_dir else _DEFAULT_OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    result: dict[str, Any] = {
        "success": False,
        "subtitle_text": "",
        "transcript_text": "",
        "subtitle_file": None,
        "transcript_file": None,
        "method": "api_subtitle",
        "error": None,
    }

    texts = _download_and_parse_subtitle_infos(subtitle_infos)
    if not texts:
        result["error"] = "API 字幕为空或下载失败"
        return result

    combined_text = "\n".join(texts)
    subtitle_file = out_dir / f"{video_id}_subtitle.txt"
    subtitle_file.write_text(combined_text, encoding="utf-8")

    result["success"] = True
    result["subtitle_text"] = combined_text
    result["subtitle_file"] = str(subtitle_file)
    logger.info("API 字幕提取成功，字数: %d", len(combined_text))
    return result


# ──────────────────────────────── 内部实现 ────────────────────────────────

def _extract_from_video_file(
    video_path: str,
    output_dir: str,
    whisper_model: str,
    skip_transcript: bool,
    cleanup_video: bool,
    extract_keyframes: bool = False,
    title: str = "",
) -> dict[str, Any]:
    """从视频文件提取字幕和转录（内部实现）。"""
    result: dict[str, Any] = {
        "success": False,
        "subtitle_text": "",
        "transcript_text": "",
        "subtitle_file": None,
        "transcript_file": None,
        "method": None,
        "keyframes": None,
        "error": None,
    }

    out_dir = safe_output_dir(output_dir)
    video_path_obj = Path(video_path)
    stem = video_path_obj.stem

    # 提取音频
    audio_path = out_dir / f"{stem}_audio.wav"
    logger.info("提取音频: %s", video_path)
    if not extract_audio_with_ffmpeg(video_path, str(audio_path)):
        result["error"] = "音频提取失败，请确认已安装 ffmpeg 或 imageio-ffmpeg"
        return result

    # extract_audio_with_ffmpeg 可能输出 .mp3 或 .aac 而非 .wav，找到实际的音频文件
    if not audio_path.exists():
        for alt_ext in [".mp3", ".aac"]:
            alt_path = out_dir / f"{stem}_audio{alt_ext}"
            if alt_path.exists() and alt_path.stat().st_size > 0:
                logger.info("使用替代音频文件: %s", alt_path)
                audio_path = alt_path
                break
        else:
            result["error"] = "音频提取后未找到输出文件"
            return result

    # 策略 1：必剪云端 ASR（返回带时间戳的分段数据）
    logger.info("尝试必剪云端 ASR 转录...")
    bcut_result = transcribe_with_bcut(str(audio_path), output_dir)
    if bcut_result["success"]:
        result["success"] = True
        result["subtitle_text"] = bcut_result["text"]
        result["subtitle_file"] = bcut_result["output_file"]
        result["method"] = "bcut_asr"
        result["segments"] = bcut_result.get("segments", [])
        logger.info("必剪 ASR 转录成功")
    else:
        logger.warning("必剪 ASR 失败: %s，尝试 Whisper 兜底", bcut_result["error"])

        # 策略 2：Whisper 本地转录（兜底）
        if not skip_transcript:
            whisper_result = _transcribe_with_whisper(
                str(audio_path), output_dir, whisper_model, title=title
            )
            if whisper_result["success"]:
                result["success"] = True
                result["transcript_text"] = whisper_result["text"]
                result["transcript_file"] = whisper_result["output_file"]
                result["method"] = f"whisper_{whisper_model}"
            else:
                result["error"] = f"必剪 ASR: {bcut_result['error']}；Whisper: {whisper_result['error']}"

    # 关键帧提取（可选，仅用户明确要求时执行）
    if extract_keyframes and result["success"] and video_path_obj.exists():
        asr_segments = result.get("segments", [])
        if asr_segments:
            logger.info("开始提取关键帧...")
            from .keyframe_extractor import extract_keyframes_from_timestamps
            keyframes = extract_keyframes_from_timestamps(
                video_path=str(video_path_obj),
                segments=asr_segments,
                output_dir=str(video_path_obj.parent),
                video_stem=video_path_obj.stem.replace("_video_temp", ""),
            )
            result["keyframes"] = keyframes
            successful_frames = sum(1 for frame in keyframes if frame.get("screenshot"))
            logger.info("关键帧提取完成：%d 帧", successful_frames)

    return result


def _download_video(play_url: str, output_dir: Path) -> Path | None:
    """从视频直链下载视频文件。"""
    import ssl

    video_path = output_dir / "video_temp.mp4"
    # 跳过 SSL 证书验证（抖音 CDN 可能使用自签名证书）
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    try:
        req = urllib.request.Request(play_url, headers=_REQUEST_HEADERS)
        with urllib.request.urlopen(req, timeout=60, context=ssl_context) as resp:
            video_path.write_bytes(resp.read())
        if video_path.exists() and video_path.stat().st_size > 0:
            logger.info("视频下载成功: %s (%.1fMB)", video_path.name, video_path.stat().st_size / 1024 / 1024)
            return video_path
    except Exception as download_error:
        logger.warning("视频下载失败: %s", download_error)
    return None


def _transcribe_with_whisper(
    audio_path: str,
    output_dir: str,
    model_name: str = "medium",
    title: str = "",
) -> dict[str, Any]:
    """使用 OpenAI Whisper 进行本地语音转录。

    Args:
        audio_path: 音频文件路径。
        output_dir: 输出目录。
        model_name: Whisper 模型名称（推荐 medium，base 中文效果差）。
        title: 视频标题，作为 initial_prompt 提升转录准确度。
    """
    result: dict[str, Any] = {
        "success": False,
        "text": "",
        "output_file": None,
        "error": None,
    }

    try:
        import whisper
    except ImportError:
        result["error"] = "未安装 openai-whisper，请运行: pip install openai-whisper"
        return result

    try:
        logger.info("使用 Whisper (%s) 转录: %s", model_name, audio_path)
        model = whisper.load_model(model_name)
        audio_data = whisper.load_audio(audio_path)

        # 构建 initial_prompt：将视频标题作为上下文，提升专有名词识别率
        transcribe_kwargs = {"language": "zh", "verbose": False}
        if title:
            context_prompt = f"以下是抖音视频的口播内容，视频标题为：{title}"
            transcribe_kwargs["initial_prompt"] = context_prompt
            logger.info("使用 initial_prompt: %s", context_prompt[:60])

        whisper_result = model.transcribe(audio_data, **transcribe_kwargs)

        transcript_text = whisper_result.get("text", "").strip()
        if not transcript_text:
            result["error"] = "转录结果为空（可能无语音或仅 BGM）"
            return result

        result["success"] = True
        result["text"] = transcript_text

        out_path = safe_output_dir(output_dir) / f"{Path(audio_path).stem}_whisper.txt"
        out_path.write_text(transcript_text, encoding="utf-8")
        result["output_file"] = str(out_path)
        logger.info("Whisper 转录完成，字数: %d", len(transcript_text))

    except Exception as whisper_error:
        result["error"] = f"Whisper 转录失败: {whisper_error}"
        logger.warning("Whisper 转录失败: %s", whisper_error)

    return result


def _download_and_parse_subtitle_infos(subtitle_infos: list[dict]) -> list[str]:
    """下载并解析 subtitle_infos 中的字幕内容（SRT/VTT 格式）。"""
    all_texts: list[str] = []

    for sub_info in subtitle_infos:
        if not isinstance(sub_info, dict):
            continue

        sub_url = sub_info.get("url", "")
        sub_format = sub_info.get("format", "srt")

        if not sub_url:
            url_list = sub_info.get("url_list", [])
            if url_list and isinstance(url_list, list):
                sub_url = url_list[0]

        if not sub_url:
            continue

        try:
            req = urllib.request.Request(sub_url, headers=_REQUEST_HEADERS)
            with urllib.request.urlopen(req, timeout=15) as response:
                sub_content = response.read().decode("utf-8", errors="ignore")
                text = _parse_vtt(sub_content) if sub_format == "vtt" else _parse_srt(sub_content)
                if text.strip():
                    all_texts.append(text)
        except Exception as download_error:
            logger.debug("字幕下载失败: %s", download_error)

    return all_texts


def _parse_srt(srt_content: str) -> str:
    """解析 SRT 格式字幕为纯文本。"""
    seen: set[str] = set()
    lines: list[str] = []
    cleaned = re.sub(r"^\d+\s*$", "", srt_content, flags=re.MULTILINE)
    cleaned = re.sub(r"\d{2}:\d{2}:\d{2},\d{3}\s*-->\s*\d{2}:\d{2}:\d{2},\d{3}.*\n", "\n", cleaned)
    cleaned = re.sub(r"<[^>]+>", "", cleaned)
    for line in cleaned.split("\n"):
        line = line.strip()
        if line and line not in seen:
            seen.add(line)
            lines.append(line)
    return "\n".join(lines)


def _parse_vtt(vtt_content: str) -> str:
    """解析 VTT 格式字幕为纯文本。"""
    seen: set[str] = set()
    lines: list[str] = []
    cleaned = re.sub(r"WEBVTT.*?\n\n", "", vtt_content, flags=re.DOTALL)
    cleaned = re.sub(r"\d{2}:\d{2}:\d{2}\.\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}\.\d{3}.*\n", "\n", cleaned)
    cleaned = re.sub(r"<[^>]+>", "", cleaned)
    for line in cleaned.split("\n"):
        line = line.strip()
        if not line or line.isdigit():
            continue
        if line not in seen:
            seen.add(line)
            lines.append(line)
    return "\n".join(lines)
