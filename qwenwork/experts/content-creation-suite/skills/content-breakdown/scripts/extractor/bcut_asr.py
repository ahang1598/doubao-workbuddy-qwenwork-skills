"""必剪云端语音识别（B站免费 ASR 服务）。

提供免费的中文语音识别能力，无需本地 GPU。
支持 aac/mp3/wav/flac/m4a 格式音频文件。
"""

from __future__ import annotations

import json
import logging
import subprocess
import time
from enum import Enum
from pathlib import Path
from typing import Any

import requests

from .path_guard import safe_output_dir

logger = logging.getLogger(__name__)

_API_REQ_UPLOAD = "https://member.bilibili.com/x/bcut/rubick-interface/resource/create"
_API_COMMIT_UPLOAD = "https://member.bilibili.com/x/bcut/rubick-interface/resource/create/complete"
_API_CREATE_TASK = "https://member.bilibili.com/x/bcut/rubick-interface/task"
_API_QUERY_RESULT = "https://member.bilibili.com/x/bcut/rubick-interface/task/result"

_SUPPORTED_FORMATS = {"flac", "aac", "m4a", "mp3", "wav"}


class _ResultState(Enum):
    STOP = 0
    RUNNING = 1
    ERROR = 3
    COMPLETE = 4


class ASRSegment:
    """单条语音识别断句。"""

    def __init__(self, data: dict[str, Any]) -> None:
        self.start_time: int = data.get("start_time", 0)
        self.end_time: int = data.get("end_time", 0)
        self.transcript: str = data.get("transcript", "")
        self.confidence: float = data.get("confidence", 0.0)

    def to_srt_timestamp(self) -> str:
        def _fmt(ms: int) -> str:
            hours = ms // 3_600_000
            minutes = (ms // 60_000) % 60
            seconds = (ms // 1_000) % 60
            millis = ms % 1_000
            return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"

        return f"{_fmt(self.start_time)} --> {_fmt(self.end_time)}"


class ASRResult:
    """语音识别完整结果。"""

    def __init__(self, data: dict[str, Any]) -> None:
        self.utterances = [ASRSegment(u) for u in data.get("utterances", [])]
        self.version: str = data.get("version", "")

    @property
    def has_data(self) -> bool:
        return len(self.utterances) > 0

    def to_text(self) -> str:
        return "\n".join(seg.transcript for seg in self.utterances)

    def to_srt(self) -> str:
        return "\n".join(
            f"{idx}\n{seg.to_srt_timestamp()}\n{seg.transcript}\n"
            for idx, seg in enumerate(self.utterances, 1)
        )


class BcutAPIError(Exception):
    def __init__(self, code: int, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"BcutAPI [{code}]: {message}")


class BcutASR:
    """必剪语音识别接口。"""

    def __init__(self, file_path: str | Path | None = None) -> None:
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            ),
        })
        self._task_id: str | None = None
        self._etags: list[str] = []
        self._sound_bin: bytes | None = None
        self._sound_fmt: str | None = None
        self._sound_name: str | None = None
        self._in_boss_key: str = ""
        self._resource_id: str = ""
        self._upload_id: str = ""
        self._upload_urls: list[str] = []
        self._per_size: int = 0
        self._download_url: str = ""

        if file_path:
            self.set_data(file_path)

    def set_data(self, file_path: str | Path) -> None:
        file_path = Path(file_path)
        self._sound_bin = file_path.read_bytes()
        self._sound_fmt = file_path.suffix.lstrip(".").lower()
        self._sound_name = file_path.name
        logger.info("加载音频: %s (%dKB)", self._sound_name, len(self._sound_bin) // 1024)

    def upload(self) -> None:
        if not self._sound_bin or not self._sound_fmt:
            raise ValueError("未设置音频数据，请先调用 set_data()")

        resp = self._session.post(_API_REQ_UPLOAD, data={
            "type": 2,
            "name": self._sound_name,
            "size": len(self._sound_bin),
            "resource_file_type": self._sound_fmt,
            "model_id": 7,
        })
        resp.raise_for_status()
        resp_json = resp.json()
        if resp_json.get("code"):
            raise BcutAPIError(resp_json["code"], resp_json.get("message", "未知错误"))

        data = resp_json["data"]
        self._in_boss_key = data["in_boss_key"]
        self._resource_id = data["resource_id"]
        self._upload_id = data["upload_id"]
        self._upload_urls = data["upload_urls"]
        self._per_size = data["per_size"]

        self._etags = []
        for clip_index, upload_url in enumerate(self._upload_urls):
            start = clip_index * self._per_size
            end = (clip_index + 1) * self._per_size
            resp = self._session.put(upload_url, data=self._sound_bin[start:end])
            resp.raise_for_status()
            self._etags.append(resp.headers.get("Etag", ""))

        resp = self._session.post(_API_COMMIT_UPLOAD, data={
            "in_boss_key": self._in_boss_key,
            "resource_id": self._resource_id,
            "etags": ",".join(self._etags),
            "upload_id": self._upload_id,
            "model_id": 7,
        })
        resp.raise_for_status()
        resp_json = resp.json()
        if resp_json.get("code"):
            raise BcutAPIError(resp_json["code"], resp_json.get("message", "未知错误"))

        self._download_url = resp_json["data"]["download_url"]
        logger.info("音频上传完成")

    def create_task(self, max_retries: int = 3) -> str:
        for attempt in range(1, max_retries + 1):
            resp = self._session.post(_API_CREATE_TASK, json={
                "resource": self._download_url,
                "model_id": "7",
            })
            resp.raise_for_status()
            resp_json = resp.json()

            if resp_json.get("code") == 0:
                self._task_id = resp_json["data"]["task_id"]
                logger.info("语音识别任务已创建: %s", self._task_id[:8])
                return self._task_id

            if resp_json.get("code") == -504 and attempt < max_retries:
                logger.warning("创建任务超时，第 %d/%d 次重试...", attempt, max_retries)
                time.sleep(2 * attempt)
                continue

            raise BcutAPIError(resp_json["code"], resp_json.get("message", "未知错误"))

        raise BcutAPIError(-1, "创建任务失败，已达最大重试次数")

    def wait_for_result(self, timeout: int = 300) -> ASRResult:
        if not self._task_id:
            raise ValueError("未创建任务，请先调用 create_task()")

        logger.info("等待语音识别完成...")
        start_time = time.time()

        while time.time() - start_time < timeout:
            resp = self._session.get(_API_QUERY_RESULT, params={
                "model_id": 7,
                "task_id": self._task_id,
            })
            resp.raise_for_status()
            resp_json = resp.json()

            if resp_json.get("code"):
                raise BcutAPIError(resp_json["code"], resp_json.get("message", "未知错误"))

            result_data = resp_json["data"]
            state = result_data.get("state")

            if state == _ResultState.COMPLETE.value:
                logger.info("语音识别完成")
                return ASRResult(json.loads(result_data.get("result", "{}")))

            if state == _ResultState.ERROR.value:
                raise BcutAPIError(-1, f"识别失败: {result_data.get('remark', '未知错误')}")

            time.sleep(1)

        raise BcutAPIError(-1, f"识别超时（{timeout}秒）")


def extract_audio_with_ffmpeg(video_path: str, output_audio_path: str) -> bool:
    """使用 ffmpeg 从视频提取音频（WAV 16kHz 单声道）。

    优先使用系统 PATH 中的 ffmpeg（版本通常更新，兼容性更好）。
    如果系统未安装 ffmpeg，使用 imageio-ffmpeg 内置的 ffmpeg 二进制（跨平台）。
    如果 imageio-ffmpeg 也未安装，自动通过 pip 安装后重试。
    """
    import shutil

    ffmpeg_exe = shutil.which("ffmpeg")
    if ffmpeg_exe:
        logger.info("使用系统 ffmpeg: %s", ffmpeg_exe)
    else:
        logger.info("系统未安装 ffmpeg，尝试使用 imageio-ffmpeg")
        try:
            import imageio_ffmpeg
            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
            logger.info("使用 imageio-ffmpeg: %s", ffmpeg_exe)
        except ImportError:
            logger.info("imageio-ffmpeg 未安装，正在自动安装...")
            try:
                import subprocess as _sp
                import sys as _sys
                _sp.run(
                    [_sys.executable, "-m", "pip", "install", "imageio-ffmpeg", "-q"],
                    check=True,
                    timeout=120,
                )
                import imageio_ffmpeg
                ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
                logger.info("imageio-ffmpeg 安装成功，ffmpeg 路径: %s", ffmpeg_exe)
            except Exception as install_error:
                logger.warning("imageio-ffmpeg 自动安装失败: %s", install_error)
                ffmpeg_exe = "ffmpeg"

    # 先检查视频文件是否有效
    video_file = Path(video_path)
    if not video_file.exists():
        logger.error("视频文件不存在: %s", video_path)
        return False
    video_size = video_file.stat().st_size
    if video_size < 1024:
        logger.error("视频文件过小 (%d bytes)，可能下载不完整或链接已过期: %s", video_size, video_path)
        return False
    logger.info("视频文件大小: %.1f MB", video_size / 1024 / 1024)

    # 先用 ffprobe 检查视频是否包含音频流
    has_audio_stream = True  # 默认假定有音频流（ffprobe 不可用时不阻断）
    try:
        ffprobe_exe = ffmpeg_exe.replace("ffmpeg", "ffprobe") if "ffmpeg" in ffmpeg_exe else "ffprobe"
        probe_result = subprocess.run(
            [ffprobe_exe, "-v", "error", "-select_streams", "a", "-show_entries", "stream=codec_name,sample_rate,channels", "-of", "json", video_path],
            capture_output=True, text=True, timeout=30,
        )
        if probe_result.returncode == 0:
            import json as _json
            try:
                probe_data = _json.loads(probe_result.stdout)
                audio_streams = probe_data.get("streams", [])
                if not audio_streams:
                    has_audio_stream = False
                    logger.error(
                        "⚠️ 视频文件不包含音频流（纯视频轨）: %s\n"
                        "这通常是因为抖音使用 DASH 音视频分离技术，下载到的是纯视频轨（media-video-avc1）。\n"
                        "解决方案：需要获取独立的音频轨 URL（包含 media-audio-und-mp4a 的 URL）并使用 --audio-url 参数。",
                        video_path,
                    )
                    return False
                logger.info("ffprobe 音频流信息: %s", probe_result.stdout.strip()[:300])
            except (ValueError, KeyError):
                logger.info("ffprobe 输出: %s", probe_result.stdout.strip()[:300])
        else:
            logger.warning("ffprobe 检查失败 (returncode=%d): %s", probe_result.returncode, probe_result.stderr[:200])
    except Exception as probe_error:
        logger.debug("ffprobe 不可用，跳过检查: %s", probe_error)

    # 尝试多种编码参数，提高兼容性
    mp3_output = output_audio_path.replace(".wav", ".mp3") if output_audio_path.endswith(".wav") else output_audio_path
    cmd_variants = [
        # 方案 1：标准 PCM WAV
        ("PCM WAV", [ffmpeg_exe, "-i", video_path, "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", "-y", output_audio_path]),
        # 方案 2：直接转 WAV（不指定编码器，让 ffmpeg 自动选择）
        ("auto WAV", [ffmpeg_exe, "-i", video_path, "-vn", "-f", "wav", "-ar", "16000", "-ac", "1", "-y", output_audio_path]),
        # 方案 3：使用 MP3 格式（兼容性最强）
        ("MP3", [ffmpeg_exe, "-i", video_path, "-vn", "-acodec", "libmp3lame", "-ar", "16000", "-ac", "1", "-y", mp3_output]),
        # 方案 4：copy 音频流再转码（某些封装格式直接转码会出错）
        ("copy+re-encode", [ffmpeg_exe, "-i", video_path, "-vn", "-acodec", "aac", "-ar", "16000", "-ac", "1", "-y", output_audio_path.replace(".wav", ".aac") if output_audio_path.endswith(".wav") else output_audio_path]),
    ]
    for label, cmd in cmd_variants:
        try:
            logger.info("尝试音频提取方案 [%s]: %s", label, " ".join(cmd[-5:]))
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            actual_output = cmd[-1]
            if result.returncode == 0 and Path(actual_output).exists() and Path(actual_output).stat().st_size > 0:
                file_size = Path(actual_output).stat().st_size
                logger.info("✅ 音频提取成功 [%s]: %s (%.1f KB)", label, actual_output, file_size / 1024)
                return True
            # 提取失败时打印完整的 stderr 用于排查
            stderr_text = result.stderr.strip() if result.stderr else "(无 stderr)"
            logger.warning("❌ 方案 [%s] 失败 (returncode=%d): %s", label, result.returncode, stderr_text[:500])
        except FileNotFoundError:
            logger.error("ffmpeg 可执行文件未找到: %s", ffmpeg_exe)
            break
        except subprocess.TimeoutExpired:
            logger.warning("❌ 方案 [%s] 超时 (120s)", label)
        except Exception as error:
            logger.warning("❌ 方案 [%s] 异常: %s", label, error)
    return False


def transcribe_with_bcut(
    audio_path: str,
    output_dir: str | None = None,
    output_format: str = "txt",
) -> dict[str, Any]:
    """使用必剪云端 ASR 转录音频文件。

    Returns:
        {"success": bool, "text": str, "srt": str, "output_file": str|None, "error": str|None}
    """
    result: dict[str, Any] = {
        "success": False,
        "text": "",
        "srt": "",
        "output_file": None,
        "error": None,
    }

    audio_path_obj = Path(audio_path)
    if not audio_path_obj.exists():
        result["error"] = f"音频文件不存在: {audio_path}"
        return result

    out_dir = safe_output_dir(output_dir) if output_dir else audio_path_obj.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        asr = BcutASR(str(audio_path_obj))
        asr.upload()
        asr.create_task()
        asr_data = asr.wait_for_result()

        if not asr_data.has_data:
            result["error"] = "未识别到语音内容"
            return result

        result["text"] = asr_data.to_text()
        result["srt"] = asr_data.to_srt()
        result["segments"] = [
            {
                "start_time": seg.start_time,
                "end_time": seg.end_time,
                "text": seg.transcript,
            }
            for seg in asr_data.utterances
        ]
        result["success"] = True

        stem = audio_path_obj.stem
        if output_format == "srt":
            output_file = out_dir / f"{stem}_bcut.srt"
            output_file.write_text(result["srt"], encoding="utf-8")
        else:
            output_file = out_dir / f"{stem}_bcut.txt"
            output_file.write_text(result["text"], encoding="utf-8")

        result["output_file"] = str(output_file)
        logger.info("必剪 ASR 转录完成，字数: %d", len(result["text"]))

    except BcutAPIError as api_error:
        result["error"] = f"必剪 ASR 错误: {api_error}"
        logger.warning("必剪 ASR 错误: %s", api_error)
    except Exception as unexpected_error:
        result["error"] = f"转录异常: {unexpected_error}"
        logger.warning("必剪 ASR 异常: %s", unexpected_error)

    return result
