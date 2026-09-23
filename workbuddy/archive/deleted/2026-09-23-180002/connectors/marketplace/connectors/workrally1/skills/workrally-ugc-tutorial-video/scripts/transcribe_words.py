#!/usr/bin/env python3
"""
transcribe_words.py — word-level timestamps via faster-whisper.
Extracts mono audio from a video and writes words.json = [[start,end,"word"],...].

Word-level (word_timestamps=True) is MANDATORY for the caption style — phrase-level
timings drift through pauses. Always transcribe the FINISHED (composited) video, not
the script plan: the video model speaks at its own pace.

Runs on the LOCAL machine (no cloud sandbox). Requires:
    ffmpeg on PATH
    python3 -m pip install faster-whisper

Model weights download to ~/.cache/huggingface on first run. Point
WHISPER_MODEL_DIR at a local cache directory to run fully offline.

Usage:
    python3 transcribe_words.py final.mp4 -o words.json [--model small] [--lang zh]
"""
import json, argparse, subprocess, tempfile, os, shutil, sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("-o", "--out", default="words.json")
    ap.add_argument("--model", default="small")      # tiny/base/small/medium
    ap.add_argument("--lang", default="zh", help="zh for Chinese speech, en for English")
    a = ap.parse_args()

    if shutil.which("ffmpeg") is None:
        sys.exit("ffmpeg not found on PATH — install it (macOS: brew install ffmpeg) and retry")
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        sys.exit("faster-whisper not installed — run: python3 -m pip install faster-whisper")

    wav = tempfile.mktemp(suffix=".wav")
    subprocess.run(["ffmpeg", "-y", "-i", a.video, "-vn", "-ac", "1",
                    "-ar", "16000", wav, "-loglevel", "error"], check=True)

    # An offline cache is opt-in; without it faster-whisper downloads to ~/.cache.
    root = os.environ.get("WHISPER_MODEL_DIR") or None
    if root and os.path.isdir(root):
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
    else:
        root = None
    model = WhisperModel(a.model, device="cpu", compute_type="int8", download_root=root)
    segs, _ = model.transcribe(wav, word_timestamps=True, language=a.lang)

    words = [[round(w.start, 2), round(w.end, 2), w.word.strip()]
             for s in segs for w in s.words]
    json.dump(words, open(a.out, "w"), ensure_ascii=False)
    os.remove(wav)
    print(f"wrote {a.out} — {len(words)} words")


if __name__ == "__main__":
    main()
