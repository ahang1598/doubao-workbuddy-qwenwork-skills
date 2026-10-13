#!/usr/bin/env python3
#
# FunASR Paraformer 语音转录
#
# 用法: python asr_funasr.py <音频文件> -o <输出JSON>
# 输出: 含句级 / 字级时间戳的 transcription.json
#

import argparse
import json
import logging
import os
import shutil
import sys
from pathlib import Path

import torch
from funasr import AutoModel

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

PUNC = set("。！？；，、,.!?;:：\"'“”‘’（）()[]【】 《》\t\n ")


def _maybe_exec_telemetry_runner() -> None:
    if os.environ.get("VIDEO_REDACTION_TELEMETRY_ACTIVE") == "1":
        return

    script_path = Path(__file__).resolve()
    script_dir = script_path.parent
    telemetry_runner = script_dir / "telemetry_runner.py"
    telemetry_module = script_dir / "telemetry.py"
    host_python = sys.executable or shutil.which("python3") or shutil.which("python")
    if not host_python or not telemetry_runner.exists() or not telemetry_module.exists():
        return

    env = os.environ.copy()
    env["VIDEO_REDACTION_TELEMETRY_ACTIVE"] = "1"
    os.execve(
        host_python,
        [
            host_python,
            str(telemetry_runner),
            "--entry-file",
            str(script_path),
            "--command",
            "asr-funasr",
            "--runtime",
            "python",
            "--",
            sys.executable,
            str(script_path),
            *sys.argv[1:],
        ],
        env,
    )


_maybe_exec_telemetry_runner()


def _ms_to_s(value) -> float:
    return round(float(value) / 1000.0, 3)


def _resolve_device(device: str) -> str:
    if device == "auto":
        return "cuda:0" if torch.cuda.is_available() else "cpu"
    return device


def _pick_model(language: str | None) -> str:
    if language and language.lower().startswith("en"):
        return "paraformer-en"
    return "paraformer-zh"


def _create_model(device: str, language: str | None) -> tuple[AutoModel, str]:
    device = _resolve_device(device)
    asr_model = _pick_model(language)
    logger.info("使用设备: %s", device)
    logger.info("加载 FunASR Paraformer: %s（ModelScope 已缓存则直接用）", asr_model)
    model = AutoModel(
        model=asr_model,
        vad_model="fsmn-vad",
        punc_model="ct-punc",
        vad_kwargs={"max_single_segment_time": 30000},
        device=device,
        disable_update=True,
        disable_pbar=True,
    )
    return model, asr_model


def _generate_with_fallback(model: AutoModel, audio_path: str):
    try:
        return model.generate(
            input=audio_path,
            batch_size_s=60,
            sentence_timestamp=True,
        )
    except TypeError:
        return model.generate(input=audio_path, batch_size_s=60)


def _words_from_timestamps(text: str, timestamps) -> list:
    chars = [c for c in text.replace(" ", "") if c not in PUNC]
    words = []
    if not timestamps:
        return words
    for ch, ts in zip(chars, timestamps):
        if not isinstance(ts, (list, tuple)) or len(ts) < 2:
            continue
        words.append({
            "word": ch,
            "start": _ms_to_s(ts[0]),
            "end": _ms_to_s(ts[1]),
            "probability": 1.0,
        })
    return words


def _segments_from_result(item: dict) -> list:
    segments = []
    sentence_info = item.get("sentence_info") or []
    if sentence_info:
        for i, sent in enumerate(sentence_info, 1):
            text = (sent.get("text") or sent.get("sentence") or "").strip()
            if not text:
                continue
            words = _words_from_timestamps(text, sent.get("timestamp") or [])
            start = _ms_to_s(sent["start"]) if sent.get("start") is not None else (
                words[0]["start"] if words else 0.0
            )
            end = _ms_to_s(sent["end"]) if sent.get("end") is not None else (
                words[-1]["end"] if words else start
            )
            segments.append({
                "id": i,
                "start": start,
                "end": end,
                "text": text.replace(" ", ""),
                "words": words,
            })
        return segments

    text = (item.get("text") or "").strip()
    if not text:
        return segments
    words = _words_from_timestamps(text, item.get("timestamp") or [])
    segments.append({
        "id": 1,
        "start": words[0]["start"] if words else 0.0,
        "end": words[-1]["end"] if words else 0.0,
        "text": text.replace(" ", ""),
        "words": words,
    })
    return segments


def transcribe_audio(audio_path: str, device: str = "auto", language: str = None) -> dict:
    model, asr_model = _create_model(device, language)
    results = _generate_with_fallback(model, audio_path)

    if not results:
        logger.error("转录结果为空")
        sys.exit(1)

    item = results[0]
    segments = _segments_from_result(item)
    duration = segments[-1]["end"] if segments else 0.0
    return {
        "language": "English" if asr_model.endswith("-en") else "Chinese",
        "language_probability": 1.0,
        "duration": duration,
        "segments": segments,
    }


def main():
    parser = argparse.ArgumentParser(description="使用 FunASR Paraformer 进行语音转录")
    parser.add_argument("audio_file", help="输入音频文件路径")
    parser.add_argument("-o", "--output", default="transcription.json", help="输出 JSON 文件路径")
    parser.add_argument("--device", default="auto", help="设备 (auto, cpu, cuda:0)")
    parser.add_argument("--language", default=None, help="语言 (Chinese, English)")
    args = parser.parse_args()

    audio_path = Path(args.audio_file).resolve()
    if not audio_path.exists():
        logger.error("音频文件未找到: %s", audio_path)
        sys.exit(1)

    try:
        data = transcribe_audio(str(audio_path), device=args.device, language=args.language)
        output_path = Path(args.output)
        if not output_path.is_absolute():
            output_path = Path.cwd() / output_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info("转录结果已保存到 %s", output_path)
    except Exception as e:
        logger.error("转录失败: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
