#!/usr/bin/env python3
"""Measure every per-block narration take against its exact manifest line.

The agent used to hand-build one ``speech_metrics.sh`` command per take. That made the
retry set depend on prose interpretation and, in one failed run, measured the final
takes with ``--text 'final take'`` instead of the words actually sent to TTS. This
wrapper owns the manifest-to-file mapping and returns one machine-readable retry set.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

TARGET_MIN = 7.8
HARD_MIN = 7.2
HARD_MAX = 9.5
ADAPTIVE_WORD_MIN = 17
DEFAULT_WORD_MAX = 23
# WorkRally port: Chinese lines are measured in characters, so the retry floor/ceiling
# has to match validate_motion_script.py's CJK budget instead of the word band.
CJK_PATTERN = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\U00020000-\U0002ffff]")
CJK_ADAPTIVE_WORD_MIN = 30
CJK_DEFAULT_WORD_MAX = 42


def _is_cjk(text: str) -> bool:
    letters = [character for character in text if character.isalpha()]
    if not letters:
        return False
    return sum(1 for c in letters if CJK_PATTERN.match(c)) * 2 >= len(letters)


def _parse_blocks(value: str) -> set[int]:
    if not value.strip():
        return set()
    try:
        blocks = {int(item.strip()) for item in value.split(",") if item.strip()}
    except ValueError as error:
        raise argparse.ArgumentTypeError("block lists contain integers only") from error
    if any(block < 1 for block in blocks):
        raise argparse.ArgumentTypeError("block numbers start at 1")
    return blocks


def _default_metrics_script() -> Path:
    here = Path(__file__).resolve()
    # WorkRally port: this skill ships speech_metrics.sh next to it, so look there
    # first. The sibling-narrator-bundle layout stays as a fallback.
    candidates = (
        here.parent / "speech_metrics.sh",
        here.parents[2] / "narrator" / "scripts" / "speech_metrics.sh",
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(
        "could not locate speech_metrics.sh next to this script; restore the skill's "
        "scripts/ directory or pass --metrics-script"
    )


def _recommended_words(
    words: int, speech: float, window: float = 10.0, *, cjk: bool = False
) -> int:
    scale = window / 10.0
    word_min = CJK_ADAPTIVE_WORD_MIN if cjk else ADAPTIVE_WORD_MIN
    word_max = CJK_DEFAULT_WORD_MAX if cjk else DEFAULT_WORD_MAX
    if speech <= 0:
        return words
    if speech > HARD_MAX * scale:
        target = round(words * 9.0 * scale / speech)
        return max(max(1, math.floor(word_min * scale)), min(words - 1, target))
    if speech < HARD_MIN * scale:
        target = math.ceil(words * 8.5 * scale / speech)
        return min(math.ceil(word_max * scale), max(words + 1, target))
    return words


def _classify(
    metric: dict[str, Any], *, accept_soft: bool, window: float = 10.0
) -> tuple[str, bool]:
    speech = float(metric["speech"])
    pauses = int(metric.get("pauses", 0))
    rate = metric.get("rate")
    scale = window / 10.0
    if not math.isfinite(speech) or speech < 0 or pauses < 0:
        raise ValueError("speech metrics must be finite and non-negative")
    if pauses:
        return "pausey", False
    if speech > HARD_MAX * scale:
        return "too_long", False
    if speech < HARD_MIN * scale:
        return "too_short", False
    if rate == "RUSHED":
        return "rushed", False
    if rate == "SLOW":
        return "slow", False
    if rate != "ok":
        raise ValueError("speech metrics must include a known delivery rate")
    if speech < TARGET_MIN * scale:
        return ("soft_pass" if accept_soft else "soft_retry"), accept_soft
    return "pass", True


def measure(
    script: dict[str, Any],
    voice_dir: Path,
    metrics_script: Path,
    *,
    accept_soft_blocks: set[int] | None = None,
    duration_seconds: float | None = None,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, Any]:
    accept_soft_blocks = accept_soft_blocks or set()
    blocks = script.get("blocks")
    if not isinstance(blocks, list) or not blocks:
        raise ValueError("script must contain a non-empty blocks array")
    if duration_seconds is None:
        duration_seconds = len(blocks) * 10.0
    if (
        not math.isfinite(duration_seconds)
        or duration_seconds <= 0
        or math.ceil(duration_seconds / 10) != len(blocks)
    ):
        raise ValueError("duration must be positive and match the manifest block count")
    if any(block < 1 or block > len(blocks) for block in accept_soft_blocks):
        raise ValueError("accepted soft blocks must exist in the manifest")

    takes: list[dict[str, Any]] = []
    retry_blocks: list[int] = []
    overlong_blocks: list[int] = []
    for index, block in enumerate(blocks, start=1):
        if not isinstance(block, dict) or not isinstance(block.get("vo_line"), str):
            raise ValueError(f"block {index} has no vo_line")
        if block.get("n", index) != index:
            raise ValueError(f"block {index} has an incorrect n")
        # Dialogue uses the clip's full-length native audio, never a TTS window.
        if script.get("talking_characters") and block.get("block_kind") == "dialogue":
            takes.append({"block": index, "state": "native_dialogue"})
            continue
        window = min(10.0, duration_seconds - (index - 1) * 10)
        voice = voice_dir / f"voice{index:02d}.wav"
        if not voice.is_file():
            takes.append({"block": index, "state": "missing", "file": str(voice)})
            retry_blocks.append(index)
            continue

        completed = runner(
            [
                "bash",
                str(metrics_script),
                str(voice),
                "--text",
                block["vo_line"],
                "--json",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout).strip()[:500]
            raise RuntimeError(f"speech metrics failed for block {index}: {detail}")
        metric = json.loads(completed.stdout)
        state, accepted = _classify(
            metric, accept_soft=index in accept_soft_blocks, window=window
        )
        take = {"block": index, "state": state, **metric}
        if state in {"too_long", "too_short"}:
            take["recommended_words"] = _recommended_words(
                int(metric["words"]),
                float(metric["speech"]),
                window,
                cjk=_is_cjk(block["vo_line"]),
            )
        takes.append(take)
        if not accepted:
            retry_blocks.append(index)
        if state == "too_long":
            overlong_blocks.append(index)

    result: dict[str, Any] = {
        "valid": not retry_blocks,
        "retry_blocks": retry_blocks,
        "overlong_blocks": overlong_blocks,
        "takes": takes,
    }
    if overlong_blocks:
        joined = ",".join(str(block) for block in overlong_blocks)
        result["revalidate_with"] = f"--duration-retry-blocks {joined}"
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--script", required=True, type=Path)
    parser.add_argument("--voice-dir", required=True, type=Path)
    parser.add_argument("--metrics-script", type=Path, default=None)
    parser.add_argument(
        "--duration-seconds", type=float, default=None,
        help="Requested motion duration; scales the window for a short final block",
    )
    parser.add_argument(
        "--accept-soft-blocks",
        type=_parse_blocks,
        default=set(),
        help="Comma-separated blocks already retried once in the 7.2-7.8s soft band",
    )
    arguments = parser.parse_args()
    try:
        script = json.loads(arguments.script.read_text(encoding="utf-8"))
        result = measure(
            script,
            arguments.voice_dir,
            arguments.metrics_script or _default_metrics_script(),
            accept_soft_blocks=arguments.accept_soft_blocks,
            duration_seconds=arguments.duration_seconds,
        )
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as error:
        print(json.dumps({"valid": False, "errors": [str(error)]}))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    sys.exit(main())
