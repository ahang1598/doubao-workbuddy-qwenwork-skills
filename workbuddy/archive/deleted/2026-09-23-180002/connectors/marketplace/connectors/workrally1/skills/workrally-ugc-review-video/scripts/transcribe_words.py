#!/usr/bin/env python3
"""
transcribe_words.py — 用 faster-whisper 产出词级时间轴。
从视频里抽单声道音频，写出 words.json = [[start,end,"word"],...]。

词级时间戳（word_timestamps=True）是这套字幕样式的硬要求 —— 短语级时间会在停顿处漂移。
永远转写**成片**（合轨后的最终视频），不要用脚本计划：视频模型有自己的语速。

依赖（本机，非沙箱）：
    python3 -m pip install faster-whisper
    ffmpeg 在 PATH 上
第一次运行会下载模型到 ~/.cache/huggingface，需要网络；离线环境用 --model-dir 指定已下载的目录。

用法：
    python3 transcribe_words.py final.mp4 -o words.json [--model small] [--lang zh]

中文口播用 --lang zh（默认）；英文口播传 --lang en。
"""
import json, argparse, subprocess, tempfile, os, shutil, sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("-o", "--out", default="words.json")
    ap.add_argument("--model", default="small")      # tiny/base/small/medium
    ap.add_argument("--lang", default="zh")
    ap.add_argument("--model-dir", default=None,
                    help="已下载模型的本地目录（离线环境用），对应 faster-whisper 的 download_root")
    a = ap.parse_args()

    if not shutil.which("ffmpeg"):
        sys.exit("缺少 ffmpeg：先装 ffmpeg（macOS: brew install ffmpeg），或跳过烧字幕交付无字幕成片")

    try:
        from faster_whisper import WhisperModel
    except ImportError:
        sys.exit("缺少 faster-whisper：python3 -m pip install faster-whisper。"
                 "装不上就如实告知用户本次不烧字幕，不要编造时间轴")

    wav = tempfile.mktemp(suffix=".wav")
    subprocess.run(["ffmpeg", "-y", "-i", a.video, "-vn", "-ac", "1",
                    "-ar", "16000", wav, "-loglevel", "error"], check=True)

    root = a.model_dir if a.model_dir and os.path.isdir(a.model_dir) else None
    if root:
        os.environ.setdefault("HF_HUB_OFFLINE", "1")  # 本地缓存只读，跳过 HF 版本校验
    model = WhisperModel(a.model, device="cpu", compute_type="int8", download_root=root)
    segs, _ = model.transcribe(wav, word_timestamps=True, language=a.lang)

    words = [[round(w.start, 2), round(w.end, 2), w.word.strip()]
             for s in segs for w in s.words]
    json.dump(words, open(a.out, "w"), ensure_ascii=False)
    os.remove(wav)
    print(f"wrote {a.out} — {len(words)} words")


if __name__ == "__main__":
    main()
