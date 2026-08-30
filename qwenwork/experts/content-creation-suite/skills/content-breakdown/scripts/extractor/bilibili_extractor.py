"""B 站视频内容提取器。

支持从 B 站视频链接（bilibili.com/video/BVxxx）提取：
- 视频基本信息（标题、UP 主、播放量、点赞、投币等）
- 字幕文本（AI 字幕 / UP 主上传字幕，需要已登录的 Chrome + Cookie）
- 语音转录（无字幕或 --no-cookie 模式时，下载最低画质视频 → 提取音频 → 必剪云端 ASR）

两种运行模式：
- Cookie 模式：通过 browser_use 获取登录 Cookie，尝试获取 AI 字幕，无字幕时降级 ASR
- --no-cookie 模式：跳过字幕 API，直接通过公开 API 下载视频（360P）→ ASR 转录
"""

from __future__ import annotations

import logging
import re
import time
from pathlib import Path
from typing import Any

import requests

from .path_guard import safe_output_dir

logger = logging.getLogger(__name__)

_DEFAULT_OUTPUT_DIR = Path.home() / ".content-breakdown" / "output" / "bilibili"

_REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.bilibili.com/",
}

# B 站视频画质：16=360P（最低，只需音频时用）
_VIDEO_QUALITY_LOW = 16


def extract_video(
    bvid: str,
    output_dir: str | None = None,
    cookie: str = "",
    skip_transcript: bool = False,
    extract_keyframes: bool = False,
    no_cookie: bool = False,
) -> dict[str, Any]:
    """从 B 站视频 BV 号提取内容（字幕或语音转录）。

    Args:
        bvid: B 站视频 BV 号（如 BV1GJ411x7h7）。
        output_dir: 输出目录（默认 ~/.content-breakdown/output/bilibili）。
        cookie: B 站登录 Cookie 字符串（由 Agent 通过 browser_use 获取）。
        skip_transcript: 跳过 ASR 转录（无字幕时不下载视频）。

    Returns:
        {
            "success": bool,
            "bvid": str,
            "title": str,
            "author": str,
            "duration": int,
            "view_count": int,
            "like_count": int,
            "coin_count": int,
            "method": str,          # "api_subtitle" | "bcut_asr"
            "subtitle_text": str,
            "subtitle_file": str | None,
            "transcript_text": str,
            "transcript_file": str | None,
            "report_file": str | None,
            "error": str | None,
        }
    """
    out_dir = safe_output_dir(output_dir) if output_dir else _DEFAULT_OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    result: dict[str, Any] = {
        "success": False,
        "bvid": bvid,
        "title": "",
        "author": "",
        "duration": 0,
        "view_count": 0,
        "like_count": 0,
        "coin_count": 0,
        "method": "",
        "subtitle_text": "",
        "subtitle_file": None,
        "transcript_text": "",
        "transcript_file": None,
        "report_file": None,
        "error": None,
    }

    # ── Step 1：获取视频基本信息（无需登录）──
    video_info = _fetch_video_info(bvid)
    if not video_info:
        result["error"] = f"获取视频信息失败，请检查 BV 号是否正确: {bvid}"
        return result

    cid = video_info["cid"]
    result["title"] = video_info["title"]
    result["author"] = video_info["author"]
    result["duration"] = video_info["duration"]
    result["view_count"] = video_info["view_count"]
    result["like_count"] = video_info["like_count"]
    result["coin_count"] = video_info["coin_count"]

    logger.info(
        "视频信息获取成功: title=%s, cid=%s, duration=%ds",
        result["title"], cid, result["duration"],
    )

    # ── Step 2：验证 Cookie ──
    cookie_str = cookie.strip() if cookie else ""
    if not cookie_str and not no_cookie:
        logger.warning("未提供 B 站 Cookie")
        result["error"] = (
            "未提供 B 站 Cookie，请通过 browser_use 获取 B 站登录 Cookie 后传入 --cookie 参数，"
            "或使用 --no-cookie 模式直接下载视频走 ASR"
        )
        return result

    if no_cookie:
        logger.info("无 Cookie 模式：跳过字幕 API，直接下载视频走 ASR")

    # ── Step 3：尝试获取字幕（需要 Cookie）──
    subtitle_text = ""
    if cookie_str and not no_cookie:
        subtitle_text = _fetch_subtitle(bvid=bvid, cid=cid, cookie=cookie_str)
    if subtitle_text:
        logger.info("字幕获取成功: %d 字", len(subtitle_text))
        subtitle_file = out_dir / f"{bvid}_subtitle.txt"
        subtitle_file.write_text(subtitle_text, encoding="utf-8")
        result["method"] = "api_subtitle"
        result["subtitle_text"] = subtitle_text
        result["subtitle_file"] = str(subtitle_file)
        result["success"] = True
        result["report_file"] = _save_as_markdown(
            bvid=bvid,
            video_info=video_info,
            text=subtitle_text,
            method="字幕",
            output_dir=out_dir,
        )

        # 关键帧提取（可选，仅用户明确要求时执行）
        # API 字幕路径：需要下载视频才能截帧
        if extract_keyframes:
            play_url = _fetch_play_url(bvid=bvid, cid=cid, cookie=cookie_str)
            if play_url:
                kf_video_path = out_dir / f"{bvid}_video_temp_kf.mp4"
                logger.info("关键帧提取：下载视频...")
                if _download_video(play_url=play_url, output_path=str(kf_video_path)):
                    subtitle_segments = _parse_subtitle_to_segments(subtitle_text, duration_seconds=result["duration"])
                    if subtitle_segments:
                        logger.info("开始提取关键帧...")
                        from extractor.keyframe_extractor import extract_keyframes_from_timestamps
                        keyframes = extract_keyframes_from_timestamps(
                            video_path=str(kf_video_path),
                            segments=subtitle_segments,
                            output_dir=str(out_dir),
                            video_stem=bvid,
                        )
                        result["keyframes"] = keyframes
                        successful_frames = sum(1 for frame in keyframes if frame.get("screenshot"))
                        logger.info("关键帧提取完成：%d 帧", successful_frames)
                    kf_video_path.unlink(missing_ok=True)
                else:
                    logger.warning("关键帧提取：视频下载失败")
            else:
                logger.warning("关键帧提取：获取视频直链失败")

        return result

    logger.info("视频无字幕，尝试下载视频进行 ASR 转录")

    if skip_transcript:
        result["error"] = "视频无字幕，且已跳过 ASR 转录（--skip-transcript）"
        return result

    # ── Step 4：无字幕 → 下载视频 → ASR 转录 ──
    play_url = _fetch_play_url(bvid=bvid, cid=cid, cookie=cookie_str)
    if not play_url:
        result["error"] = "获取视频直链失败，请检查视频是否可正常访问" if no_cookie else "获取视频直链失败，请确认已登录 B 站"
        return result

    video_path = out_dir / f"{bvid}_video_temp.mp4"
    logger.info("开始下载视频（最低画质）: %s", play_url[:80])
    if not _download_video(play_url=play_url, output_path=str(video_path)):
        result["error"] = "视频下载失败"
        return result

    logger.info("视频下载完成，开始 ASR 转录")
    transcript_result = _transcribe_video(
        video_path=str(video_path),
        output_dir=str(out_dir),
    )

    if not transcript_result.get("success"):
        # 清理临时视频文件
        if video_path.exists():
            video_path.unlink()
        result["error"] = transcript_result.get("error", "ASR 转录失败")
        return result

    transcript_text = transcript_result.get("text", "")
    transcript_file = transcript_result.get("output_file")
    asr_segments = transcript_result.get("segments", [])

    # 关键帧提取（可选，仅用户明确要求时执行，在视频清理前）
    if extract_keyframes and asr_segments and video_path.exists():
        logger.info("开始提取关键帧...")
        from extractor.keyframe_extractor import extract_keyframes_from_timestamps
        keyframes = extract_keyframes_from_timestamps(
            video_path=str(video_path),
            segments=asr_segments,
            output_dir=str(out_dir),
            video_stem=bvid,
        )
        result["keyframes"] = keyframes
        successful_frames = sum(1 for frame in keyframes if frame.get("screenshot"))
        logger.info("关键帧提取完成：%d 帧", successful_frames)

    # 清理临时视频文件
    if video_path.exists():
        video_path.unlink()

    result["method"] = "bcut_asr"
    result["transcript_text"] = transcript_text
    result["transcript_file"] = transcript_file
    result["success"] = True
    result["report_file"] = _save_as_markdown(
        bvid=bvid,
        video_info=video_info,
        text=transcript_text,
        method="语音转录（必剪 ASR）",
        output_dir=out_dir,
    )
    return result


def extract_from_url(
    video_url: str,
    output_dir: str | None = None,
    cookie: str = "",
    skip_transcript: bool = False,
    extract_keyframes: bool = False,
    no_cookie: bool = False,
) -> dict[str, Any]:
    """从 B 站视频页面链接提取内容（自动解析 BV 号）。

    Args:
        video_url: B 站视频链接（如 https://www.bilibili.com/video/BV1GJ411x7h7）。
        output_dir: 输出目录。
        cookie: B 站登录 Cookie 字符串（由 Agent 通过 browser_use 获取）。
        skip_transcript: 跳过 ASR 转录。
        extract_keyframes: 是否提取关键帧截图（仅用户明确要求时传 True）。
        no_cookie: 无 Cookie 模式，跳过字幕 API，直接下载视频走 ASR。
    """
    bvid = _extract_bvid(video_url)
    if not bvid:
        return {
            "success": False,
            "error": f"无法从链接中解析 BV 号: {video_url}",
            "bvid": "",
        }
    logger.info("解析 BV 号: %s → %s", video_url, bvid)
    return extract_video(
        bvid=bvid,
        output_dir=output_dir,
        cookie=cookie,
        skip_transcript=skip_transcript,
        extract_keyframes=extract_keyframes,
        no_cookie=no_cookie,
    )


# ──────────────────────────────── 视频信息 ────────────────────────────────

def _extract_bvid(url: str) -> str | None:
    """从 B 站链接中提取 BV 号。"""
    match = re.search(r"BV[a-zA-Z0-9]+", url)
    return match.group(0) if match else None


def _fetch_video_info(bvid: str) -> dict[str, Any] | None:
    """获取 B 站视频基本信息（无需登录）。"""
    api_url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
    try:
        response = requests.get(api_url, headers=_REQUEST_HEADERS, timeout=10)
        data = response.json()
        if data.get("code") != 0:
            logger.warning("视频信息 API 返回错误: code=%s, msg=%s", data.get("code"), data.get("message"))
            return None
        video_data = data["data"]
        stat = video_data.get("stat", {})
        return {
            "cid": video_data["cid"],
            "title": video_data.get("title", ""),
            "author": video_data.get("owner", {}).get("name", ""),
            "duration": video_data.get("duration", 0),
            "view_count": stat.get("view", 0),
            "like_count": stat.get("like", 0),
            "coin_count": stat.get("coin", 0),
            "favorite_count": stat.get("favorite", 0),
            "share_count": stat.get("share", 0),
            "desc": video_data.get("desc", ""),
        }
    except Exception as fetch_error:
        logger.warning("获取视频信息失败: %s", fetch_error)
        return None


# ──────────────────────────────── 字幕获取 ────────────────────────────────

def _fetch_subtitle(bvid: str, cid: int, cookie: str) -> str:
    """获取 B 站视频字幕文本（需要 Cookie）。"""
    api_url = f"https://api.bilibili.com/x/player/v2?bvid={bvid}&cid={cid}"
    headers = {**_REQUEST_HEADERS, "Cookie": cookie}
    try:
        response = requests.get(api_url, headers=headers, timeout=10)
        data = response.json()
        if data.get("code") != 0:
            logger.debug("字幕 API 返回错误: code=%s", data.get("code"))
            return ""

        subtitles = data.get("data", {}).get("subtitle", {}).get("subtitles", [])
        if not subtitles:
            logger.info("视频无字幕")
            return ""

        # 优先选中文字幕，其次选第一个
        subtitle_url = None
        for sub in subtitles:
            lan = sub.get("lan", "")
            if lan.startswith("zh") or lan == "ai-zh":
                subtitle_url = sub.get("subtitle_url", "")
                break
        if not subtitle_url:
            subtitle_url = subtitles[0].get("subtitle_url", "")

        if not subtitle_url:
            return ""

        # 字幕 URL 可能以 // 开头，补全 https:
        if subtitle_url.startswith("//"):
            subtitle_url = "https:" + subtitle_url

        logger.info("下载字幕: %s", subtitle_url[:80])
        sub_response = requests.get(subtitle_url, headers=_REQUEST_HEADERS, timeout=10)
        sub_data = sub_response.json()

        # 解析字幕 JSON，提取 content 字段
        body = sub_data.get("body", [])
        lines = [item.get("content", "") for item in body if item.get("content")]
        return "\n".join(lines)

    except Exception as subtitle_error:
        logger.warning("获取字幕失败: %s", subtitle_error)
        return ""


# ──────────────────────────────── 视频下载 ────────────────────────────────

def _fetch_play_url(bvid: str, cid: int, cookie: str) -> str:
    """获取 B 站视频直链（无 Cookie 时返回 360P，有 Cookie 可更高）。"""
    api_url = (
        f"https://api.bilibili.com/x/player/playurl"
        f"?bvid={bvid}&cid={cid}&qn={_VIDEO_QUALITY_LOW}&fnval=0&fnver=0&fourk=0"
    )
    headers = {**_REQUEST_HEADERS, "Cookie": cookie} if cookie else _REQUEST_HEADERS
    try:
        response = requests.get(api_url, headers=headers, timeout=10)
        data = response.json()
        if data.get("code") != 0:
            logger.warning("视频直链 API 返回错误: code=%s, msg=%s", data.get("code"), data.get("message"))
            return ""

        durl = data.get("data", {}).get("durl", [])
        if not durl:
            logger.warning("视频直链列表为空")
            return ""

        play_url = durl[0].get("url", "")
        logger.info("视频直链获取成功: %s...", play_url[:80])
        return play_url

    except Exception as play_error:
        logger.warning("获取视频直链失败: %s", play_error)
        return ""


def _download_video(play_url: str, output_path: str) -> bool:
    """下载 B 站视频到本地。"""
    headers = {
        **_REQUEST_HEADERS,
        "Range": "bytes=0-",
    }
    try:
        response = requests.get(play_url, headers=headers, stream=True, timeout=60)
        response.raise_for_status()
        total_size = int(response.headers.get("content-length", 0))
        downloaded = 0
        with open(output_path, "wb") as video_file:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    video_file.write(chunk)
                    downloaded += len(chunk)
        logger.info(
            "视频下载完成: %.1f MB → %s",
            downloaded / 1024 / 1024,
            output_path,
        )
        return True
    except Exception as download_error:
        logger.warning("视频下载失败: %s", download_error)
        return False


# ──────────────────────────────── ASR 转录 ────────────────────────────────

def _transcribe_video(video_path: str, output_dir: str) -> dict[str, Any]:
    """提取视频音频并用必剪云端 ASR 转录。"""
    from extractor.bcut_asr import extract_audio_with_ffmpeg, transcribe_with_bcut

    audio_path = str(Path(video_path).with_suffix(".wav"))
    try:
        if not extract_audio_with_ffmpeg(video_path, audio_path):
            return {"success": False, "error": "音频提取失败"}

        # extract_audio_with_ffmpeg 可能输出 .mp3 或 .aac 而非 .wav，找到实际的音频文件
        actual_audio = audio_path
        if not Path(audio_path).exists():
            video_stem = Path(video_path).stem
            video_dir = Path(video_path).parent
            for alt_ext in [".mp3", ".aac"]:
                alt_path = video_dir / f"{video_stem}{alt_ext}"
                if alt_path.exists() and alt_path.stat().st_size > 0:
                    actual_audio = str(alt_path)
                    break

        asr_result = transcribe_with_bcut(
            audio_path=actual_audio,
            output_dir=output_dir,
            output_format="txt",
        )
        return {
            "success": asr_result.get("success", False),
            "text": asr_result.get("text", ""),
            "segments": asr_result.get("segments", []),
            "output_file": asr_result.get("output_file"),
            "error": asr_result.get("error"),
        }
    finally:
        # 清理临时音频文件（包括可能的 .mp3/.aac 替代文件）
        for ext in [".wav", ".mp3", ".aac"]:
            cleanup_path = Path(video_path).with_suffix(ext)
            if cleanup_path.exists():
                cleanup_path.unlink(missing_ok=True)


# ──────────────────────────────── Markdown 报告 ────────────────────────────────

def _parse_subtitle_to_segments(subtitle_text: str, duration_seconds: int = 0) -> list[dict]:
    """将字幕文本按行解析为 segments 格式（用于关键帧提取）。

    由于 API 字幕只有文本，没有时间戳，这里按均匀分布估算时间戳。
    """
    lines = [line.strip() for line in subtitle_text.split("\n") if line.strip()]
    if not lines:
        return []
    # 按视频实际时长均匀分配时间戳；无时长信息时每行估算 3 秒
    total_ms = duration_seconds * 1000 if duration_seconds > 0 else len(lines) * 3000
    interval_ms = total_ms // len(lines)
    segments = []
    for index, line in enumerate(lines):
        start_time = index * interval_ms
        end_time = min((index + 1) * interval_ms, total_ms)
        segments.append({
            "start_time": start_time,
            "end_time": end_time,
            "text": line,
        })
    return segments


def _save_as_markdown(
    bvid: str,
    video_info: dict[str, Any],
    text: str,
    method: str,
    output_dir: Path,
) -> str | None:
    """生成 Markdown 分析报告。"""
    lines: list[str] = []

    title = video_info.get("title") or f"B 站视频 {bvid}"
    lines.append(f"# {title}")
    lines.append("")

    # 元信息
    lines.append(f"**UP 主**：{video_info.get('author', '')}")
    duration = video_info.get("duration", 0)
    minutes, seconds = divmod(duration, 60)
    lines.append(f"**时长**：{minutes}:{seconds:02d}")
    lines.append(f"**播放量**：{video_info.get('view_count', 0):,}")
    lines.append(f"**点赞**：{video_info.get('like_count', 0):,}  "
                 f"**投币**：{video_info.get('coin_count', 0):,}  "
                 f"**收藏**：{video_info.get('favorite_count', 0):,}")
    lines.append(f"**BV 号**：{bvid}")
    lines.append(f"**链接**：https://www.bilibili.com/video/{bvid}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # 视频简介
    desc = video_info.get("desc", "").strip()
    if desc and desc != "-":
        lines.append("## 视频简介")
        lines.append("")
        lines.append(desc)
        lines.append("")
        lines.append("---")
        lines.append("")

    # 字幕/转录文本
    if text:
        lines.append(f"## 视频内容（{method}）")
        lines.append("")
        lines.append(text)
        lines.append("")

    report_path = output_dir / f"{bvid}_report.md"
    try:
        report_path.write_text("\n".join(lines), encoding="utf-8")
        logger.info("Markdown 报告已生成: %s", report_path.name)
        return str(report_path)
    except Exception as save_error:
        logger.warning("保存报告失败: %s", save_error)
        return None
