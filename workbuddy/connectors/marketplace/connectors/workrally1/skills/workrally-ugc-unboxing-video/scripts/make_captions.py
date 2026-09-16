#!/usr/bin/env python3
"""
make_captions.py — TikTok/抖音-safe .ass subtitles for UGC clips + ffmpeg burn command.

Default: plain captions — each phrase simply appears on its timestamp. Big, bold,
white with black outline, locked inside the vertical-video safe zones. Animations
and fonts are OPT-IN flags.

Usage:
    python3 make_captions.py segments.json                          -> plain captions
    python3 make_captions.py segments.json --anim pop               -> entrance animation
    python3 make_captions.py segments.json --font "PingFang SC"     -> font override
    python3 make_captions.py segments.json --size 100               -> bigger text (auto-fit still applies)
    python3 make_captions.py segments.json --no-caps                -> keep original casing

Animations (--anim): none (default) | fade | pop | bounce | slide-up | slide-down |
                     zoom-out | flip | blur-in | shake | stretch

Fonts: the font name is resolved by fontconfig at burn time, so it must be INSTALLED
locally. The default is "PingFang SC" (preinstalled on macOS, covers both Chinese and
latin); "Noto Sans SC" (`brew install --cask font-noto-sans-sc`) is the portable
alternative. A font without CJK glyphs burns Chinese text as empty boxes, so --font
is only worth overriding for a latin-only script.

Input JSON:
{
  "video": "clip.mp4",
  "style": {                            // optional overrides (same keys as flags)
    "font": "PingFang SC",
    "size": 88,                         // px at 1080x1920; auto-shrinks if a line is too wide
    "fill": "&H00FFFFFF",               // ASS BGR: white
    "outline_color": "&H00000000",      // black
    "outline": 5,
    "margin_v": 620,                    // px from bottom; clamped to >=320 (safe zone)
    "caps": true,                       // upper-cases latin text; a no-op for Chinese
    "anim": "none"
  },
  "segments": [
    {"start": 0.0, "end": 1.5, "text": "这个我用了三个月"},
    {"start": 1.9, "end": 4.6, "text": "本来没打算发出来"}
  ]
}

Safe zones baked in (1080x1920): bottom >=320px kept clear (platform UI + caption bar),
side margins 80px, top 10% never reached. Max 2 lines; the longest line auto-shrinks the
font so text NEVER crosses the side margins. Line length is measured in DISPLAY WIDTH,
so a CJK glyph counts as two latin columns.
"""

import json, argparse, os, pathlib, re, subprocess, sys

PLAY_W, PLAY_H = 1080, 1920
MARGIN_X = 80                 # side margins, px
MIN_MARGIN_V = 320            # hard floor: bottom ~17% stays clear (platform UI)
GLYPH_K = 0.58                # avg latin glyph width in em
WRAP_WIDTH = 16               # display width above which a caption breaks into two lines

CJK = "\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff"
WIDE = CJK + "\u3000-\u303f\uff00-\uff60"   # + CJK punctuation and fullwidth forms
_CJK_RE = re.compile(f"[{CJK}]")
_WIDE_RE = re.compile(f"[{WIDE}]")
# libass 按“字族名”走 fontconfig 解析。macOS 上 PingFang SC 位于 SIP 保护的
# PrivateFrameworks 下，fontconfig 索引不到它——fc-match 会返回 Verdana 之类完全无关的
# 字体，中文于是被静默烧成方框，而 ffmpeg 退出码仍是 0。所以候选字族必须回读校验。
CJK_FONT_CANDIDATES = [
    "Noto Sans CJK SC", "Noto Sans SC", "Source Han Sans SC",
    "PingFang SC", "Hiragino Sans GB", "STHeiti",
    "Microsoft YaHei", "WenQuanYi Zen Hei",
]

def _font_resolvable(family: str) -> bool:
    """fc-match 回读：族名对得上且文件可读，才算 libass 真的能用。"""
    try:
        r = subprocess.run(["fc-match", "-f", "%{family}|%{file}", family],
                           capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return False
    if r.returncode != 0 or "|" not in r.stdout:
        return False
    got, _, path = r.stdout.partition("|")
    return family.lower() in got.lower() and os.access(path.strip(), os.R_OK)

def resolve_cjk_font():
    for fam in CJK_FONT_CANDIDATES:
        if _font_resolvable(fam):
            return fam, True
    return "Noto Sans SC", False

CJK_FONT, CJK_FONT_OK = resolve_cjk_font()

DEF_STYLE = {
    "font": CJK_FONT, "size": 88,
    "fill": "&H00FFFFFF", "outline_color": "&H00000000", "outline": 6,
    "margin_v": 620, "caps": True, "anim": "none",
}

# ASS entrance tags
ANIM_TAGS = {
    "none": "",
    "fade": "{\\fad(220,0)}",
    "pop": "{\\fscx60\\fscy60\\t(0,160,\\fscx100\\fscy100)}",
    "bounce": "{\\fscx30\\fscy30\\t(0,200,\\fscx112\\fscy112)\\t(200,340,\\fscx100\\fscy100)}",
    "zoom-out": "{\\fscx140\\fscy140\\t(0,180,\\fscx100\\fscy100)\\fad(110,0)}",
    "flip": "{\\fscy10\\t(0,200,\\fscy100)\\fad(80,0)}",
    "blur-in": "{\\blur12\\t(0,220,\\blur0)\\fad(110,0)}",
    "shake": "{\\frz3\\t(0,70,\\frz-3)\\t(70,140,\\frz2)\\t(140,210,\\frz0)\\fad(70,0)}",
    "stretch": "{\\fscx170\\t(0,190,\\fscx100)\\fad(90,0)}",
}

def is_cjk(ch: str) -> bool:
    return bool(_CJK_RE.match(ch))

def is_wide(ch: str) -> bool:
    return bool(_WIDE_RE.match(ch))

def width(text: str) -> int:
    """Display width — a CJK glyph occupies two latin columns."""
    return sum(2 if is_wide(ch) else 1 for ch in text)

def units(text: str):
    """Wrappable units: each CJK glyph (plus trailing punctuation) on its own, each latin
    word whole. A line never breaks in the middle of a word or before CJK punctuation."""
    out, buf = [], ""
    for ch in text:
        if is_cjk(ch) or ch.isspace():
            if buf:
                out.append(buf); buf = ""
            if is_cjk(ch):
                out.append(ch)
        elif out and not buf and is_wide(ch) and is_cjk(out[-1][0]):
            out[-1] += ch          # keep 。！？ glued to the glyph it follows
        else:
            buf += ch
    if buf:
        out.append(buf)
    return out

def join(parts) -> str:
    """A space between two latin neighbours, nothing around a CJK glyph."""
    out = ""
    for p in parts:
        if not p:
            continue
        if out and not is_wide(out[-1]) and not is_wide(p[0]):
            out += " "
        out += p
    return out

def slide_tags(direction: str, margin_v: int, size: int) -> str:
    x = PLAY_W / 2
    y = PLAY_H - margin_v
    off = size * 0.6
    dx, dy = 0.0, 0.0
    if direction == "slide-up": dy = off
    elif direction == "slide-down": dy = -off
    return f"{{\\move({x + dx:.0f},{y + dy:.0f},{x:.0f},{y:.0f},0,200)\\fad(140,0)}}"

def ts(sec: float) -> str:
    h = int(sec // 3600); m = int(sec % 3600 // 60); s = sec % 60
    return f"{h}:{m:02d}:{s:05.2f}"

def wrap(text: str, max_width: int = WRAP_WIDTH):
    us = units(text)
    if width(text) <= max_width or len(us) == 1:
        return [join(us)]
    # balanced 2-line split: pick the break that minimizes the wider line
    best, best_w = None, 10**9
    for i in range(1, len(us)):
        l1, l2 = join(us[:i]), join(us[i:])
        m = max(width(l1), width(l2))
        if m < best_w:
            best, best_w = [l1, l2], m
    return best

def fit_size(desired: int, lines) -> int:
    """Shrink font so the longest line fits inside the side margins."""
    max_w = PLAY_W - 2 * MARGIN_X
    longest = max((width(l) for l in lines), default=1)
    fitted = min(desired, int(max_w / (longest * GLYPH_K)))
    return max(36, fitted)

def build_ass(data: dict, cli_style: dict) -> str:
    st = {**DEF_STYLE, **data.get("style", {}), **{k: v for k, v in cli_style.items() if v is not None}}
    margin_v = max(MIN_MARGIN_V, int(st["margin_v"]))
    anim = st["anim"] if st["anim"] in ANIM_TAGS or str(st["anim"]).startswith("slide") else "none"

    # Chinese needs a CJK font — swap the latin default rather than burning empty boxes.
    has_cjk = any(_CJK_RE.search(seg["text"]) for seg in data["segments"])
    if has_cjk and cli_style.get("font") is None and "font" not in data.get("style", {}):
        st["font"] = CJK_FONT
        if not CJK_FONT_OK:
            sys.stderr.write(
                "WARN: fontconfig 找不到可解析的中文字族，中文会烧成方框。"
                "装一个：brew install --cask font-noto-sans-sc\n")

    # Pre-wrap all segments, find the global fitted size so every caption matches
    seg_lines = []
    for seg in data["segments"]:
        raw = seg["text"].strip()
        if st["caps"]: raw = raw.upper()
        seg_lines.append((seg, wrap(raw)))
    size = min(fit_size(int(st["size"]), lines) for _, lines in seg_lines) if seg_lines else int(st["size"])

    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {PLAY_W}
PlayResY: {PLAY_H}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,{st['font']},{size},{st['fill']},{st['fill']},{st['outline_color']},&H96000000,-1,0,0,0,100,100,0,0,1,{st['outline']},0,2,{MARGIN_X},{MARGIN_X},{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ev = []
    for seg, lines in seg_lines:
        t0, t1 = float(seg["start"]), float(seg["end"])
        tags = slide_tags(anim, margin_v, size) if str(anim).startswith("slide") else ANIM_TAGS.get(anim, "")
        ev.append(f"Dialogue: 0,{ts(t0)},{ts(t1)},Cap,,0,0,0,,{tags}" + "\\N".join(lines))
    return head + "\n".join(ev) + "\n"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("json_path")
    ap.add_argument("--anim", choices=list(ANIM_TAGS) + ["slide-up", "slide-down"], default=None)
    ap.add_argument("--font", default=None)
    ap.add_argument("--size", type=int, default=None)
    ap.add_argument("--caps", dest="caps", action="store_true", default=None,
                    help="force upper case (latin only; a no-op for Chinese)")
    ap.add_argument("--no-caps", dest="caps", action="store_false",
                    help="keep the authored casing")
    ap.add_argument("-o", "--out")
    a = ap.parse_args()
    src = pathlib.Path(a.json_path)
    data = json.loads(src.read_text(encoding="utf-8"))
    out = pathlib.Path(a.out) if a.out else src.with_suffix(".ass")
    out.write_text(build_ass(data, {"anim": a.anim, "font": a.font, "size": a.size, "caps": a.caps}),
                   encoding="utf-8")
    video = data.get("video", "clip.mp4")
    stem = pathlib.Path(video).stem
    print(f"wrote {out}")
    print(f'burn:  ffmpeg -y -i "{video}" -vf "ass={out}" -c:a copy "{stem}_captioned.mp4"')
    print(f'note: Fontname={CJK_FONT if CJK_FONT_OK else "未解析到中文字族"} —— libass 按字族名走 fontconfig，烧完请抽一帧确认中文不是方框。')

if __name__ == "__main__":
    main()
