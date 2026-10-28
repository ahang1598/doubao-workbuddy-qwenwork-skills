#!/usr/bin/env python3
"""Write a completed MediaKit ASR result for the recording converter.

Read the JSON returned by MediaKit's task query from stdin. The expected task
ID must be the one returned when submitting this recording's WAV.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any


def _milliseconds(value: Any) -> int:
    if isinstance(value, bool):
        raise ValueError("ASR timestamp must be a number of seconds")
    try:
        seconds = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("ASR timestamp must be a number of seconds") from exc
    if not seconds.is_finite():
        raise ValueError("ASR timestamp must be finite")
    return int((seconds * 1000).to_integral_value(rounding=ROUND_HALF_UP))


def convert_result(result: dict[str, Any], *, expected_task_id: str) -> list[dict[str, Any]]:
    """Convert MediaKit CLI's completed, flattened subtitle result to JSONL rows."""
    if not isinstance(result, dict) or result.get("status") != "completed":
        raise ValueError("MediaKit ASR task is not completed")
    if not expected_task_id or result.get("task_id") != expected_task_id:
        raise ValueError("MediaKit ASR task_id does not match this recording")
    if result.get("success") is False or result.get("task_type", "asr-subtitles") != "asr-subtitles":
        raise ValueError("MediaKit result is not a successful ASR task")
    subtitles = result.get("subtitles")
    if not isinstance(subtitles, list):
        raise ValueError("MediaKit result has no subtitles array")

    rows = []
    for index, subtitle in enumerate(subtitles):
        if not isinstance(subtitle, dict):
            raise ValueError(f"invalid subtitle #{index}")
        try:
            start = _milliseconds(subtitle["start_time"])
            end = _milliseconds(subtitle["end_time"])
            text = subtitle["subtitle_text"]
        except KeyError as exc:
            raise ValueError(f"subtitle #{index} is missing {exc.args[0]}") from exc
        if not isinstance(text, str) or not text.strip() or start < 0 or end < start:
            raise ValueError(f"invalid subtitle #{index}")
        rows.append({"t_ms": start, "t_end_ms": end, "text": text.strip()})
    rows.sort(key=lambda row: (row["t_ms"], row["t_end_ms"]))
    return rows


def write_asr(session_dir: Path, rows: list[dict[str, Any]]) -> Path | None:
    """Publish only a complete JSONL file under the actual .cuasession directory."""
    session_dir = Path(session_dir)
    if session_dir.suffix != ".cuasession" or not session_dir.is_dir() or session_dir.is_symlink():
        raise ValueError("session_dir must be an existing .cuasession directory")
    audio_dir = session_dir / "audio"
    if audio_dir.is_symlink():
        raise ValueError("audio directory must not be a symlink")
    target = audio_dir / "asr.jsonl"
    if not rows:
        if target.exists() or target.is_symlink():
            raise FileExistsError("an ASR file already exists for an empty result")
        return None

    audio_dir.mkdir(exist_ok=True)
    data = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)
    if target.exists() or target.is_symlink():
        if target.is_file() and not target.is_symlink() and target.read_text(encoding="utf-8") == data:
            return target
        raise FileExistsError("a different ASR file already exists for this recording")

    handle, temporary = tempfile.mkstemp(prefix=".asr-", suffix=".tmp", dir=audio_dir)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, target)
    finally:
        os.unlink(temporary)
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session-dir", required=True, type=Path)
    parser.add_argument("--task-id", required=True)
    args = parser.parse_args()
    try:
        result = json.load(sys.stdin)
        rows = convert_result(result, expected_task_id=args.task_id)
        output = write_asr(args.session_dir, rows)
    except (ValueError, OSError) as exc:
        print(f"ASR handoff failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"asrPath": str(output) if output else None, "segments": len(rows)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
