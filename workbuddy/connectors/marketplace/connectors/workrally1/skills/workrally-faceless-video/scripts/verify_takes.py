#!/usr/bin/env python3
"""Check that each narration take SAYS ITS LINE.

A dev run on 2026-07-29 received takes for a different video back from the TTS under
load: the lengths passed every gate and the words were about onions in a video about
pandas. Only the caption step noticed. Length gates cannot catch that; a cheap
transcription can.

Transcribes work/voices/voiceNN.wav with the tiny model and compares the words against
blocks[NN-1].vo_line from the script manifest. Exit 1 when any take is a mismatch, so
the finishing script refuses to assemble it.
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from pathlib import Path

WORD = re.compile(r"[^\W_]+", re.UNICODE)
MISMATCH_BELOW = 0.40   # below this the take is a different text entirely
THIN_BELOW = 0.55       # between the two: worth a warning, not a stop
# WorkRally port: Chinese has no word separators, so a whole line collapses into one
# token and SequenceMatcher scores every take 0.0 or 1.0. Compare character by
# character instead. Whisper also transcribes Mandarin in Simplified or Traditional
# depending on the segment, so the ratio runs lower than for English — the thresholds
# below are the same, which makes this gate a coarse "is this the right text at all"
# check rather than a wording check.
CJK = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\U00020000-\U0002ffff]")


def words(text: str | None) -> list[str]:
    units: list[str] = []
    for token in WORD.findall((text or "").casefold()):
        if CJK.search(token):
            units.extend(token)
        else:
            units.append(token)
    return units


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--script", required=True, type=Path)
    ap.add_argument("--voice-dir", required=True, type=Path)
    ap.add_argument("--language", default=None)
    ap.add_argument("--model", default="tiny", help="tiny is enough to spot a different text")
    args = ap.parse_args()

    payload = json.loads(args.script.read_text(encoding="utf-8"))
    blocks = payload.get("blocks") or payload.get("beats") or []
    if not blocks:
        print("verify_takes: manifest has no blocks, nothing to check", file=sys.stderr)
        return 0

    from faster_whisper import WhisperModel

    model = WhisperModel(args.model, device="cpu", compute_type="int8")
    mismatches: list[tuple[int, str, str]] = []

    for index, block in enumerate(blocks, start=1):
        wav = args.voice_dir / f"voice{index:02d}.wav"
        if not wav.is_file():
            continue
        said = words(block.get("vo_line") or block.get("phrase"))
        if not said:
            continue
        segments, _info = model.transcribe(
            str(wav), language=args.language or None, vad_filter=False
        )
        heard = words(" ".join(segment.text for segment in segments))
        ratio = difflib.SequenceMatcher(None, said, heard).ratio()
        state = "ok" if ratio >= THIN_BELOW else ("thin" if ratio >= MISMATCH_BELOW else "MISMATCH")
        print(f"  block {index:02d}: content={state} similarity={ratio:.2f}", file=sys.stderr)
        if state == "MISMATCH":
            mismatches.append((index, " ".join(said[:12]), " ".join(heard[:12])))

    for index, said, heard in mismatches:
        print(
            f"ERROR: block {index} should say '{said}…' but the take says '{heard}…'. "
            "Either the provider returned another video's audio, or this take predates an "
            "edit to that line. Both are fixed the same way: regenerate THIS take from the "
            "current manifest with the locked voice id, and leave every other take alone.",
            file=sys.stderr,
        )
    return 1 if mismatches else 0


if __name__ == "__main__":
    sys.exit(main())
