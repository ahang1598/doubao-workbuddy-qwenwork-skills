#!/usr/bin/env python3
"""Validate Picture Story voice takes before image generation and assembly."""

from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


SILENCE_DURATION_PATTERN = re.compile(r"silence_duration:\s*([0-9.]+)")


def _probe_duration(path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "csv=p=0",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return float(result.stdout.strip())


def _longest_silence(path: Path) -> float:
    result = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-i",
            str(path),
            "-af",
            "silencedetect=noise=-35dB:d=0.8",
            "-f",
            "null",
            "-",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    durations = [
        float(match)
        for match in SILENCE_DURATION_PATTERN.findall(result.stderr)
    ]
    return max(durations, default=0.0)


def _load_beats(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    beats = payload.get("beats") if isinstance(payload, dict) else None
    if not isinstance(beats, list) or not all(
        isinstance(beat, dict) for beat in beats
    ):
        raise ValueError("script must contain a beats array of objects")
    return beats


def _validate(
    *,
    beats: list[dict[str, Any]],
    voice_paths: list[Path],
    duration_seconds: float,
    breath_seconds: float,
    minimum_slide_seconds: float,
) -> dict[str, Any]:
    errors: list[str] = []
    invalid_beats: list[dict[str, Any]] = []
    if len(voice_paths) != len(beats):
        errors.append(
            f"voice count {len(voice_paths)} does not match beat count {len(beats)}"
        )

    per_beat: list[dict[str, Any]] = []
    for index, voice_path in enumerate(voice_paths, start=1):
        beat_errors: list[str] = []
        if not voice_path.is_file():
            invalid_beats.append(
                {
                    "n": index,
                    "voice": str(voice_path),
                    "errors": ["voice file is missing"],
                }
            )
            continue
        try:
            take_seconds = _probe_duration(voice_path)
            longest_silence_seconds = _longest_silence(voice_path)
        except (OSError, subprocess.CalledProcessError, ValueError) as error:
            invalid_beats.append(
                {
                    "n": index,
                    "voice": str(voice_path),
                    "errors": [f"cannot inspect voice: {error}"],
                }
            )
            continue

        slide_seconds = max(
            take_seconds + breath_seconds,
            minimum_slide_seconds,
        )
        if take_seconds > 3.0:
            beat_errors.append(
                f"take is {take_seconds:.3f}s; split/rewrite beats longer than 3.0s"
            )
        if longest_silence_seconds >= 0.8:
            beat_errors.append(
                "take contains "
                f"{longest_silence_seconds:.3f}s silence; maximum is below 0.8s"
            )

        entry = {
            "n": index,
            "voice": str(voice_path),
            "take_seconds": round(take_seconds, 3),
            "slide_seconds": round(slide_seconds, 3),
            "longest_silence_seconds": round(longest_silence_seconds, 3),
        }
        per_beat.append(entry)
        if beat_errors:
            invalid_beats.append({**entry, "errors": beat_errors})

    total_seconds = sum(item["slide_seconds"] for item in per_beat)
    tolerance_seconds = max(0.5, duration_seconds * 0.02)
    if len(per_beat) == len(beats) and not math.isclose(
        total_seconds,
        duration_seconds,
        abs_tol=tolerance_seconds,
    ):
        errors.append(
            f"assembled duration would be {total_seconds:.3f}s, outside "
            f"{duration_seconds - tolerance_seconds:.3f}-"
            f"{duration_seconds + tolerance_seconds:.3f}s target window"
        )

    return {
        "valid": not errors and not invalid_beats,
        "target_duration_seconds": duration_seconds,
        "tolerance_seconds": round(tolerance_seconds, 3),
        "estimated_assembled_duration_seconds": round(total_seconds, 3),
        "billing_block_count": math.ceil(duration_seconds / 10),
        "errors": errors,
        "invalid_beats": invalid_beats,
        "per_beat": per_beat,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--script", required=True, type=Path)
    parser.add_argument("--duration-seconds", required=True, type=float)
    parser.add_argument("--breath", default=0.2, type=float)
    parser.add_argument("--min-slide", default=1.0, type=float)
    parser.add_argument("voices", nargs="+", type=Path)
    arguments = parser.parse_args()
    if arguments.duration_seconds <= 0:
        parser.error("--duration-seconds must be positive")
    if arguments.breath < 0:
        parser.error("--breath must be non-negative")
    if arguments.min_slide <= 0:
        parser.error("--min-slide must be positive")
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        parser.error("ffmpeg and ffprobe are required")

    try:
        beats = _load_beats(arguments.script)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print(
            json.dumps(
                {"valid": False, "errors": [str(error)], "invalid_beats": []},
                ensure_ascii=False,
            )
        )
        return 1

    result = _validate(
        beats=beats,
        voice_paths=arguments.voices,
        duration_seconds=arguments.duration_seconds,
        breath_seconds=arguments.breath,
        minimum_slide_seconds=arguments.min_slide,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    sys.exit(main())
