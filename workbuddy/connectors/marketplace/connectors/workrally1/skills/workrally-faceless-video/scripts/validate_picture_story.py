#!/usr/bin/env python3
"""Validate deterministic scene-based script gates before TTS spend."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any


WORD_PATTERN = re.compile(r"[^\W_]+(?:[-'’][^\W_]+)*", re.UNICODE)
MINIMUM_BEATS_PER_MINUTE = 25
MAXIMUM_BEATS_PER_MINUTE = 35
MINIMUM_WORDS_PER_BEAT = 4
MAXIMUM_WORDS_PER_BEAT = 8
MAXIMUM_NARRATION_WORDS_PER_SECOND = 2.5

# WorkRally port: Chinese narration has no spaces, so count each CJK ideograph as one
# unit and scale the per-beat / per-second budgets from words to characters at the
# measured Mandarin read rate (~4.3 chars/s vs ~2.4 words/s).
CJK_PATTERN = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\U00020000-\U0002ffff]")
CJK_MINIMUM_WORDS_PER_BEAT = 6
CJK_MAXIMUM_WORDS_PER_BEAT = 14
CJK_MAXIMUM_NARRATION_WORDS_PER_SECOND = 4.6


def _units(text: str) -> list[str]:
    units: list[str] = []
    for token in WORD_PATTERN.findall(text):
        if CJK_PATTERN.search(token):
            units.extend(token)
        else:
            units.append(token)
    return units


def _word_count(text: str) -> int:
    return len(_units(text))


def _is_cjk(text: str) -> bool:
    letters = [character for character in text if character.isalpha()]
    if not letters:
        return False
    return sum(1 for c in letters if CJK_PATTERN.match(c)) * 2 >= len(letters)


def _phrase_from(beat: dict[str, Any]) -> tuple[str, str]:
    for field in ("phrase", "vo_line"):
        value = beat.get(field)
        if isinstance(value, str) and value.strip():
            return field, value.strip()
    return "phrase", ""


def _validate(script: Any, duration_seconds: float) -> dict[str, Any]:
    errors: list[str] = []
    invalid_beats: list[dict[str, Any]] = []
    beats = script.get("beats") if isinstance(script, dict) else None
    if isinstance(script, dict):
        genre = script.get("genre")
        if genre not in {"education", "history", "kids", "storytelling"}:
            errors.append(
                "genre must be education, history, kids, or storytelling"
            )
        if script.get("animation_mode") != "scene_based":
            errors.append("animation_mode must be scene_based")
    if not isinstance(beats, list) or not beats:
        return {
            "valid": False,
            "errors": ["script must contain a non-empty beats array"],
            "invalid_beats": [],
        }

    minimum_beats = max(
        1,
        math.ceil(duration_seconds * MINIMUM_BEATS_PER_MINUTE / 60),
    )
    maximum_beats = max(
        minimum_beats,
        math.floor(duration_seconds * MAXIMUM_BEATS_PER_MINUTE / 60),
    )
    if not minimum_beats <= len(beats) <= maximum_beats:
        errors.append(
            f"beat count {len(beats)} is outside {minimum_beats}-{maximum_beats} "
            f"for {duration_seconds:g}s "
            f"({MINIMUM_BEATS_PER_MINUTE}-{MAXIMUM_BEATS_PER_MINUTE} beats/minute)"
        )

    total_word_count = 0
    cjk_beats = 0
    for index, raw_beat in enumerate(beats, start=1):
        if not isinstance(raw_beat, dict):
            invalid_beats.append(
                {
                    "n": index,
                    "error": "beat must be an object",
                    "word_count": 0,
                }
            )
            continue
        phrase_field, phrase = _phrase_from(raw_beat)
        word_count = _word_count(phrase)
        total_word_count += word_count
        cjk_phrase = _is_cjk(phrase)
        if cjk_phrase:
            cjk_beats += 1
        beat_minimum = CJK_MINIMUM_WORDS_PER_BEAT if cjk_phrase else MINIMUM_WORDS_PER_BEAT
        beat_maximum = CJK_MAXIMUM_WORDS_PER_BEAT if cjk_phrase else MAXIMUM_WORDS_PER_BEAT
        unit_label = "characters" if cjk_phrase else "words"
        declared_number = raw_beat.get("n")
        beat_number = declared_number if isinstance(declared_number, int) else index
        beat_errors: list[str] = []
        if declared_number != index:
            beat_errors.append(f"n must be {index}")
        if not phrase:
            beat_errors.append("phrase is required")
        elif not beat_minimum <= word_count <= beat_maximum:
            beat_errors.append(
                f"phrase must contain {beat_minimum}-{beat_maximum} {unit_label}"
            )
        image_mode = raw_beat.get("image_mode")
        if image_mode not in {"new", "variation"}:
            beat_errors.append("image_mode must be new or variation")
        elif image_mode == "variation":
            if index == 1:
                beat_errors.append("the first beat cannot be a variation")
            if raw_beat.get("variation_of") != index - 1:
                beat_errors.append(
                    f"variation_of must be the immediately previous beat ({index - 1})"
                )
            change_only = raw_beat.get("change_only")
            if not isinstance(change_only, str) or not change_only.strip():
                beat_errors.append("variation requires a non-empty change_only")
        if beat_errors:
            invalid_beats.append(
                {
                    "n": beat_number,
                    "field": phrase_field,
                    "phrase": phrase,
                    "word_count": word_count,
                    "errors": beat_errors,
                }
            )

    cjk_script = beats and cjk_beats * 2 >= len(beats)
    rate = (
        CJK_MAXIMUM_NARRATION_WORDS_PER_SECOND
        if cjk_script
        else MAXIMUM_NARRATION_WORDS_PER_SECOND
    )
    maximum_word_count = max(1, math.floor(duration_seconds * rate))
    if total_word_count > maximum_word_count:
        unit_label = "character" if cjk_script else "word"
        errors.append(
            f"total {unit_label} count {total_word_count} exceeds the "
            f"{maximum_word_count}-{unit_label} pre-TTS budget for {duration_seconds:g}s"
        )

    return {
        "valid": not errors and not invalid_beats,
        "beat_count": len(beats),
        "total_word_count": total_word_count,
        "maximum_word_count": maximum_word_count,
        "expected_beat_count": {
            "minimum": minimum_beats,
            "maximum": maximum_beats,
        },
        "errors": errors,
        "invalid_beats": invalid_beats,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--script", required=True, type=Path)
    parser.add_argument("--duration-seconds", required=True, type=float)
    arguments = parser.parse_args()
    if arguments.duration_seconds <= 0:
        parser.error("--duration-seconds must be positive")

    try:
        script = json.loads(arguments.script.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(
            json.dumps(
                {"valid": False, "errors": [str(error)], "invalid_beats": []},
                ensure_ascii=False,
            )
        )
        return 1

    result = _validate(script, arguments.duration_seconds)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    sys.exit(main())
