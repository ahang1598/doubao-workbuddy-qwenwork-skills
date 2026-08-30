"""视频关键帧提取器。

基于 ASR 转录时间戳，在对应时间点截取视频帧，生成图文对照的关键帧报告。

工作流程：
1. 接收 ASR 转录结果（含每句话的 start_time 毫秒时间戳）
2. 用 ffmpeg 在对应时间点截取视频帧（PNG 格式）
3. 返回 [时间戳 + 文案 + 截图路径] 的对照列表

依赖：imageio-ffmpeg（已内置，无需额外安装）
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Any

from .path_guard import safe_output_dir

logger = logging.getLogger(__name__)


def _get_ffmpeg_path() -> str:
    """获取 ffmpeg 可执行文件路径（优先使用 imageio-ffmpeg 内置版本）。"""
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        pass

    # fallback: 检查系统 PATH 中的 ffmpeg
    try:
        proc = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if proc.returncode == 0:
            return "ffmpeg"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    raise RuntimeError(
        "未找到 ffmpeg。请安装：pip install imageio-ffmpeg 或 brew install ffmpeg"
    )


def extract_keyframes_from_timestamps(
    video_path: str,
    segments: list[dict[str, Any]],
    output_dir: str,
    video_stem: str = "video",
    max_frames: int = 20,
) -> list[dict[str, Any]]:
    """根据 ASR 时间戳列表截取视频关键帧。

    Args:
        video_path: 本地视频文件路径。
        segments: ASR 分段列表，每项包含 start_time（毫秒）和 transcript（文案）。
        output_dir: 截图保存目录。
        video_stem: 视频文件名前缀，用于截图命名。
        max_frames: 最多截取帧数（避免过多截图，默认 20）。

    Returns:
        关键帧列表，每项格式：
        {
            "index": int,           # 序号（从 1 开始）
            "timestamp_ms": int,    # 时间戳（毫秒）
            "timestamp_str": str,   # 时间戳字符串（如 "00:03"）
            "transcript": str,      # 对应文案
            "screenshot": str,      # 截图本地路径
            "error": str | None,    # 截图失败时的错误信息
        }
    """
    if not segments:
        logger.warning("ASR 分段列表为空，无法提取关键帧")
        return []

    frames_dir = safe_output_dir(output_dir) / f"{video_stem}_keyframes"
    frames_dir.mkdir(parents=True, exist_ok=True)

    try:
        ffmpeg_path = _get_ffmpeg_path()
    except RuntimeError as error:
        logger.error("ffmpeg 不可用: %s", error)
        return []

    # 限制最大帧数，均匀采样
    selected_segments = _sample_segments(segments, max_frames)

    keyframes: list[dict[str, Any]] = []
    for frame_index, segment in enumerate(selected_segments, start=1):
        timestamp_ms = segment.get("start_time", 0)
        transcript = (segment.get("transcript") or segment.get("text") or "").strip()
        timestamp_str = _format_timestamp(timestamp_ms)

        screenshot_path = frames_dir / f"frame_{frame_index:03d}_{timestamp_str.replace(':', '')}.png"

        success, error_message = _capture_frame_at_timestamp(
            ffmpeg_path=ffmpeg_path,
            video_path=video_path,
            timestamp_ms=timestamp_ms,
            output_path=str(screenshot_path),
        )

        keyframes.append({
            "index": frame_index,
            "timestamp_ms": timestamp_ms,
            "timestamp_str": timestamp_str,
            "transcript": transcript,
            "screenshot": str(screenshot_path) if success else None,
            "error": error_message,
        })

        if success:
            logger.info("关键帧 %d/%d 截取成功: %s [%s]", frame_index, len(selected_segments), timestamp_str, transcript[:20])
        else:
            logger.warning("关键帧 %d/%d 截取失败: %s", frame_index, len(selected_segments), error_message)

    successful_count = sum(1 for frame in keyframes if frame["screenshot"])
    logger.info("关键帧提取完成：%d/%d 帧成功，保存至 %s", successful_count, len(keyframes), frames_dir)

    return keyframes


def _capture_frame_at_timestamp(
    ffmpeg_path: str,
    video_path: str,
    timestamp_ms: int,
    output_path: str,
) -> tuple[bool, str | None]:
    """用 ffmpeg 在指定时间点截取单帧图片。

    Args:
        ffmpeg_path: ffmpeg 可执行文件路径。
        video_path: 视频文件路径。
        timestamp_ms: 截帧时间点（毫秒）。
        output_path: 截图保存路径（PNG）。

    Returns:
        (成功标志, 错误信息)
    """
    # 将毫秒转换为 HH:MM:SS.mmm 格式（ffmpeg -ss 参数格式）
    total_seconds = timestamp_ms / 1000.0
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = total_seconds % 60
    timestamp_ffmpeg = f"{hours:02d}:{minutes:02d}:{seconds:06.3f}"

    command = [
        ffmpeg_path,
        "-ss", timestamp_ffmpeg,   # 精确跳转到时间点（放在 -i 前面，速度更快）
        "-i", video_path,
        "-vframes", "1",           # 只截取 1 帧
        "-q:v", "2",               # 图片质量（1-31，越小越好）
        "-y",                      # 覆盖已有文件
        output_path,
    ]

    try:
        proc = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if proc.returncode == 0 and Path(output_path).exists():
            return True, None
        else:
            error_detail = proc.stderr.strip().split("\n")[-1] if proc.stderr else "未知错误"
            return False, f"ffmpeg 截帧失败: {error_detail}"
    except subprocess.TimeoutExpired:
        return False, "ffmpeg 截帧超时（30s）"
    except Exception as capture_error:
        return False, f"截帧异常: {capture_error}"


def _sample_segments(
    segments: list[dict[str, Any]],
    max_frames: int,
) -> list[dict[str, Any]]:
    """从 ASR 分段中均匀采样，限制最大帧数。

    当分段数量超过 max_frames 时，均匀间隔采样；否则全部保留。
    始终保留第一帧和最后一帧。
    """
    if len(segments) <= max_frames:
        return segments

    # 均匀采样：始终包含首尾
    step = (len(segments) - 1) / (max_frames - 1)
    sampled_indices = {round(i * step) for i in range(max_frames)}
    sampled_indices.add(0)
    sampled_indices.add(len(segments) - 1)

    return [segments[index] for index in sorted(sampled_indices)]


def _format_timestamp(timestamp_ms: int) -> str:
    """将毫秒时间戳格式化为 MM:SS 字符串（如 "03:45"）。"""
    total_seconds = timestamp_ms // 1000
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f"{minutes:02d}:{seconds:02d}"


def format_keyframes_report(keyframes: list[dict[str, Any]]) -> str:
    """将关键帧列表格式化为可读的文本报告。

    Args:
        keyframes: extract_keyframes_from_timestamps 返回的关键帧列表。

    Returns:
        格式化的文本报告字符串。
    """
    if not keyframes:
        return "（无关键帧数据）"

    lines: list[str] = []
    for frame in keyframes:
        timestamp = frame.get("timestamp_str", "??:??")
        transcript = frame.get("transcript", "（无文案）")
        screenshot = frame.get("screenshot")
        error = frame.get("error")

        lines.append(f"[{timestamp}] {transcript}")
        if screenshot:
            lines.append(f"  截图：{screenshot}")
        elif error:
            lines.append(f"  截图失败：{error}")
        lines.append("")

    return "\n".join(lines).strip()
