#!/usr/bin/env python3
"""Gate a Kids SONG MODE prompt before it is submitted.

The song model only holds a beat when the prompt carries the meter machinery from
``references/kids-song.md`` verbatim and carries NOTHING that invites a tempo change.
Every "the rhythm is awful" report from dev testing (2026-07-25 v2, 2026-07-29 U25) came
from a prompt that had drifted off that skeleton — a bridge, a groove word, or lines whose
syllable counts wandered.

So the prompt is checked mechanically, the same way a script is:

    python3 scripts/validate_song_prompt.py --prompt song_prompt.txt [--json]

Exit 0 = submit it. Exit 1 = fix the reported items first; do not "try it and see".
Checks:
  * length <= 2048 characters (the model's hard prompt limit)
  * one CONSTANT bpm stated, and it is 100 (gentle) or 112 (dance-along)
  * the steady-beat clauses are present (steady/constant beat, 4/4, no tempo changes)
  * banned tempo words absent: bridge, slow down, speed up, ritardando, accelerando,
    tempo change, key change, breakdown, drop, half-time, double-time
  * banned groove jargon absent: four-on-the-floor, syncopation, swung, shuffle groove
  * the syllable machinery is stated (8 syllables, one syllable per beat, beat one,
    4-bar phrases)
  * a chorus exists and is marked as repeating verbatim
  * quoted lyric lines hold the 8-syllable meter (the counter is an estimate, so a line
    may be off by one; more than a quarter of the lines off by two or more fails)
"""

from __future__ import annotations

import argparse
import json
import re
import sys

MAX_PROMPT_CHARS = 2048
ALLOWED_BPM = {100, 112}
TARGET_SYLLABLES = 8

REQUIRED_CLAUSES: tuple[tuple[str, str], ...] = (
    (r"steady|constant", "state that the beat is STEADY AND CONSTANT from first second to last"),
    (r"\b4/4\b", "state the simple 4/4 metre"),
    (r"no\s+tempo\s+changes?", 'state "NO tempo changes"'),
    (r"8\s+syllables|eight\s+syllables", "state the 8-syllable line law"),
    (r"one\s+syllable\s+per\s+beat", 'state "one syllable per beat"'),
    (r"beat\s+one", "state that every line starts on beat one of its bar"),
    (r"4-?bar|four-?bar", "state the 4-bar phrase law"),
    (r"chorus", "name the chorus sections"),
    (r"verbatim|repeat", "state that the chorus repeats verbatim"),
)

BANNED_TEMPO = (
    "bridge",
    "slow down",
    "slowdown",
    "speed up",
    "speedup",
    "ritardando",
    "accelerando",
    "tempo change",
    "key change",
    "breakdown",
    "half-time",
    "double-time",
    "drop",
)
BANNED_GROOVE = (
    "four-on-the-floor",
    "four on the floor",
    "syncopation",
    "syncopated",
    "swung",
    "shuffle groove",
)

VOWEL_GROUPS = re.compile(r"[aeiouy]+", re.IGNORECASE)
WORD = re.compile(r"[A-Za-z']+")


def _syllables(word: str) -> int:
    """Cheap English syllable estimate — good enough to catch a wandering line."""
    word = word.lower().strip("'")
    if not word:
        return 0
    groups = VOWEL_GROUPS.findall(word)
    count = len(groups)
    if word.endswith("e") and count > 1 and not word.endswith(("le", "ee", "ye")):
        count -= 1
    return max(1, count)


def _line_syllables(line: str) -> int:
    return sum(_syllables(word) for word in WORD.findall(line))


def _lyric_lines(prompt: str) -> list[str]:
    lines: list[str] = []
    for quoted in re.findall(r'"([^"]{10,})"', prompt):
        for part in re.split(r"\s*(?:/|\||\n)\s*", quoted):
            part = part.strip(" ,.;:!?-")
            if len(WORD.findall(part)) >= 3:
                lines.append(part)
    return lines


# The required clauses NEGATE the banned words ("NO tempo changes"), so the negated forms
# are removed before the banned-word scan.
NEGATED = re.compile(
    r"\bno\s+(?:tempo\s+changes?|key\s+changes?|slow\s?downs?|speed\s?ups?|breakdowns?|drops?|bridges?)",
    re.IGNORECASE,
)
SYLLABLE_TOLERANCE = 1
MAX_OFF_METER_SHARE = 0.25
# A line this far off is not an estimator miss, it is a line that cannot be sung on the
# beat — one of them is enough to break the groove, so it fails on its own.
GROSS_SYLLABLE_MISS = 4


def validate(prompt: str, *, target_syllables: int = TARGET_SYLLABLES) -> dict:
    errors: list[str] = []
    lowered = prompt.casefold()
    scannable = NEGATED.sub(" ", lowered)

    if len(prompt) > MAX_PROMPT_CHARS:
        errors.append(
            f"prompt is {len(prompt)} characters, over the {MAX_PROMPT_CHARS} limit — "
            "trim instrument adjectives first, never the meter laws or the lyrics"
        )

    bpm_values = {int(value) for value in re.findall(r"(\d{2,3})\s*bpm", lowered)}
    if not bpm_values:
        errors.append("no BPM stated — name one constant tempo (100 gentle / 112 dance-along)")
    elif len(bpm_values) > 1:
        errors.append(
            "more than one BPM in the prompt ("
            + ", ".join(str(value) for value in sorted(bpm_values))
            + ") — one constant tempo only"
        )
    elif not bpm_values <= ALLOWED_BPM:
        errors.append(
            f"BPM {bpm_values.pop()} is untested — use 100 (gentle) or 112 (dance-along)"
        )

    for pattern, message in REQUIRED_CLAUSES:
        if not re.search(pattern, lowered):
            errors.append(f"missing clause: {message}")

    for phrase in BANNED_TEMPO:
        if phrase in scannable:
            errors.append(
                f'banned tempo word "{phrase}" — dynamics come from orchestration '
                "(fuller final chorus, extra claps), never from tempo"
            )
    for phrase in BANNED_GROOVE:
        if phrase in scannable:
            errors.append(
                f'banned groove jargon "{phrase}" — describe claps and instruments plainly'
            )

    lyrics = _lyric_lines(prompt)
    if not lyrics:
        errors.append("no quoted lyric lines found — the verses and chorus go in the prompt")
    else:
        off = [
            f'"{line}" ({_line_syllables(line)})'
            for line in lyrics
            if abs(_line_syllables(line) - target_syllables) > SYLLABLE_TOLERANCE
        ]
        gross = [
            f'"{line}" ({_line_syllables(line)})'
            for line in lyrics
            if abs(_line_syllables(line) - target_syllables) >= GROSS_SYLLABLE_MISS
        ]
        if gross:
            errors.append(
                f"lyric line(s) nowhere near the {target_syllables}-syllable meter — they "
                "cannot land one syllable per beat: "
                + "; ".join(gross[:6])
                + (" …" if len(gross) > 6 else "")
            )
        elif len(off) > max(1, int(len(lyrics) * MAX_OFF_METER_SHARE)):
            errors.append(
                f"{len(off)} of {len(lyrics)} lyric lines miss the {target_syllables}-syllable "
                "meter by two or more — the wandering meter is what makes the beat sound "
                "broken; rewrite them: "
                + "; ".join(off[:6])
                + (" …" if len(off) > 6 else "")
            )

    return {
        "valid": not errors,
        "characters": len(prompt),
        "bpm": sorted(bpm_values),
        "lyric_lines": len(lyrics),
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prompt", required=True, help="file holding the song prompt")
    parser.add_argument("--syllables", type=int, default=TARGET_SYLLABLES)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    with open(args.prompt, encoding="utf-8") as handle:
        prompt = handle.read()

    result = validate(prompt, target_syllables=args.syllables)
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"valid: {result['valid']}  chars: {result['characters']}  "
              f"bpm: {result['bpm']}  lyric lines: {result['lyric_lines']}")
        for error in result["errors"]:
            print(f"  - {error}")
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    sys.exit(main())
