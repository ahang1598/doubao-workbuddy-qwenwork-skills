#!/usr/bin/env python3
"""
make_captions.py — 给 UGC 竖版口播生成抖音 / 小红书安全区内的 .ass 字幕，并打印 ffmpeg 烧字命令。

默认：朴素字幕 —— 每个短语在自己的时间点出现。大字、粗体、白字黑描边，锁在竖版安全区里。
动画与字体都是**可选**开关。

用法：
    python3 make_captions.py segments.json                          -> 朴素字幕
    python3 make_captions.py segments.json --anim pop               -> 入场动画
    python3 make_captions.py segments.json --font "Noto Sans SC"    -> 换字体
    python3 make_captions.py segments.json --size 100               -> 更大字号（仍会自动收缩以适配）

动画（--anim）: none（默认）| fade | pop | bounce | slide-up | slide-down |
                zoom-out | flip | blur-in | shake | stretch

字体：默认 `PingFang SC`（macOS 自带，**有完整中文字形**）。中文字幕必须用带中文字形的字体，
否则 libass 渲染出方框或直接丢字。macOS 备选 `Hiragino Sans GB`、`Heiti SC`；
Linux 装 `Noto Sans SC`（`fonts-noto-cjk`）后用 `--font "Noto Sans SC"`。
纯英文口播可以传 `--font "Montserrat"` 之类。用 `fc-list :lang=zh` / `fc-list | grep -i pingfang`
确认本机确实装了该字体，ffmpeg 的 ass filter 通过 fontconfig 解析字体名。

输入 JSON：
{
  "video": "clip.mp4",
  "style": {                            // 可选覆盖（键名与命令行开关一致）
    "font": "PingFang SC",
    "size": 88,                         // 1080x1920 下的 px；某行过宽会自动缩小
    "fill": "&H00FFFFFF",               // ASS BGR：白
    "outline_color": "&H00000000",      // 黑
    "outline": 5,
    "margin_v": 620,                    // 距底部 px；下限钳到 >=320（安全区）
    "caps": true,                       // 仅对西文有意义，中文无影响
    "anim": "none"
  },
  "segments": [
    {"start": 0.0, "end": 1.5, "text": "这个我用了两周"},
    {"start": 1.9, "end": 4.6, "text": "本来没打算发"}
  ]
}

内建安全区（1080x1920）：底部 >=320px 留空（平台 UI + 字幕条），左右各 80px，顶部 10% 不触及。
最多 2 行；最长那行会自动缩小字号，保证文字**绝不**越过左右边距（CJK 字形按 1.0 em 计宽，
西文按 0.58 em）。
"""

import json, argparse, os, pathlib, re, subprocess, sys

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

PLAY_W, PLAY_H = 1080, 1920
MARGIN_X = 80                 # 左右边距，px
MIN_MARGIN_V = 320            # 硬下限：底部约 17% 留空（平台 UI）
GLYPH_K = 0.58                # 西文平均字形宽度（em）
CJK_K = 1.0                   # CJK 字形是全宽

CJK = r"\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\u3040-\u30ff\uac00-\ud7af\u3000-\u303f\uff00-\uffef"
_CJK_RE = re.compile(f"[{CJK}]")
# 换行切分单元：汉字逐字、拉丁词整块
_UNIT_RE = re.compile(f"[{CJK}]|[^\\s{CJK}]+")

DEF_STYLE = {
    "font": CJK_FONT, "size": 88,
    "fill": "&H00FFFFFF", "outline_color": "&H00000000", "outline": 6,
    "margin_v": 620, "caps": True, "anim": "none",
}

# ASS 入场标签
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

def em_width(text: str) -> float:
    """一行文字的估算宽度（单位 em）：CJK 字形 1.0，西文 0.58。"""
    return sum(CJK_K if _CJK_RE.match(ch) else GLYPH_K for ch in text)

def _units(text: str):
    """可换行的最小单元：汉字逐字，拉丁词整块。中文没有空格，按空格切会得到一整行。"""
    return _UNIT_RE.findall(text)

def _join(units):
    out = ""
    for u in units:
        if not out:
            out = u
            continue
        if _CJK_RE.match(out[-1]) or _CJK_RE.match(u[0]):
            out += u
        else:
            out += " " + u
    return out

def wrap(text: str, max_em: float = 9.5):
    """最多两行的均衡换行。max_em 是单行的目标 em 宽度。"""
    units = _units(text)
    if len(units) <= 1 or em_width(text) <= max_em:
        return [_join(units)] if units else [text]
    best, best_w = None, 10**9
    for i in range(1, len(units)):
        l1, l2 = _join(units[:i]), _join(units[i:])
        w = max(em_width(l1), em_width(l2))
        if w < best_w:
            best, best_w = [l1, l2], w
    return best

def fit_size(desired: int, lines) -> int:
    """缩小字号使最长行落在左右边距内。"""
    max_w = PLAY_W - 2 * MARGIN_X
    longest = max((em_width(l) for l in lines), default=1.0) or 1.0
    fitted = min(desired, int(max_w / longest))
    return max(36, fitted)

def build_ass(data: dict, cli_style: dict) -> str:
    st = {**DEF_STYLE, **data.get("style", {}), **{k: v for k, v in cli_style.items() if v is not None}}
    margin_v = max(MIN_MARGIN_V, int(st["margin_v"]))
    anim = st["anim"] if st["anim"] in ANIM_TAGS or str(st["anim"]).startswith("slide") else "none"

    # 先给所有段落换行，再算全局统一字号，让每条字幕大小一致
    seg_lines = []
    for seg in data["segments"]:
        raw = seg["text"].strip()
        if st["caps"]: raw = raw.upper()   # CJK 无影响
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
    ap.add_argument("-o", "--out")
    a = ap.parse_args()
    src = pathlib.Path(a.json_path)
    data = json.loads(src.read_text(encoding="utf-8"))
    out = pathlib.Path(a.out) if a.out else src.with_suffix(".ass")
    out.write_text(build_ass(data, {"anim": a.anim, "font": a.font, "size": a.size}), encoding="utf-8")
    video = data.get("video", "clip.mp4")
    stem = pathlib.Path(video).stem
    print(f"wrote {out}")
    print(f'burn: ffmpeg -y -i "{video}" -vf "ass={out}" -c:a copy "{stem}_captioned.mp4"')
    if CJK_FONT_OK:
        print(f'note: 字体={CJK_FONT}（已通过 fc-match 回读校验）。libass 按字族名解析，')
        print('      烧完请抽一帧确认中文不是方框。')
    else:
        print('WARN: fontconfig 找不到可解析的中文字族，中文会烧成方框。', file=sys.stderr)
        print('      装一个：brew install --cask font-noto-sans-sc', file=sys.stderr)

if __name__ == "__main__":
    main()
