#!/usr/bin/env bash
# burn_caps_clean.sh — burn CLEAN CAPS subtitles onto a finished video from an .srt,
# using ffmpeg + libass. Explainer-style but PLATELESS: bold WHITE text, black
# OUTLINE + soft drop shadow, bottom-centre. No paper, NO background box.
# Text is forced to UPPERCASE (Unicode-aware: works for Cyrillic etc. via python3).
# Exact timing (from a Whisper-built srt), zero jitter.
#
# Sizing: ffmpeg converts SRT with a 384x288 subtitle grid (PlayResY=288), so values
# are fractions of 288: fontsize 13 ≈ 4.5% of frame height (small), marginv 34 ≈
# bottom 12%. Do NOT pass marginv ≥ 90 — that parks captions mid-frame.
#
# Usage:
#   scripts/burn_caps_clean.sh --in video.mp4 --srt caps.srt --out final_subbed.mp4
#     [--font "TikTok Sans"] [--fontsdir DIR] [--fontsize 13] [--marginv 34]
#     [--outline 2] [--shadow 1]
#
# Font: put a bold face at scripts/fonts/ — default family "TikTok Sans"
# (TikTokSans-Bold.ttf, SIL OFL, Latin+Cyrillic+Greek; see fonts/README.md for the
# curl one-liner). Binaries are not committed; without a .ttf libass falls back to a
# system font (the script warns — the look will differ).
#
# CJK: TikTok Sans has NO Chinese glyphs. When the .srt contains CJK and --font was
# not pinned, the family is switched to a system CJK face (PingFang SC on macOS, the
# first :lang=zh family fontconfig reports elsewhere) and a warning is printed.
# libass resolves families through fontconfig, which does not always see a system
# .ttc — ALWAYS extract a frame and confirm the Chinese caption actually rendered.
# For Chinese, subtitle_paper_burn.py is the safer burner: it loads the font file by
# absolute path instead of asking fontconfig for a family name.
# Requires: ffmpeg (with libass); python3 recommended for non-ASCII uppercasing.
set -euo pipefail

IN=""; SRT=""; OUT="final_subbed.mp4"; FONT="TikTok Sans"; FONT_SET=0; FONTSDIR=""; FSIZE=13; MV=34; OUTLINE=2; SHADOW=1; NOCAPS=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --in) IN="$2"; shift 2 ;;
    --srt) SRT="$2"; shift 2 ;;
    --out) OUT="$2"; shift 2 ;;
    --font) FONT="$2"; FONT_SET=1; shift 2 ;;
    --fontsdir) FONTSDIR="$2"; shift 2 ;;
    --fontsize) FSIZE="$2"; shift 2 ;;
    --marginv) MV="$2"; shift 2 ;;
    --outline) OUTLINE="$2"; shift 2 ;;
    --shadow) SHADOW="$2"; shift 2 ;;
    --no-caps) NOCAPS=1; shift ;;
    -h|--help) grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 1 ;;
  esac
done
[[ -n "$IN"  && -f "$IN"  ]] || { echo "ERROR: --in video not found" >&2; exit 1; }
[[ -n "$SRT" && -f "$SRT" ]] || { echo "ERROR: --srt file not found" >&2; exit 1; }
command -v ffmpeg >/dev/null 2>&1 || { echo "ERROR: ffmpeg not found" >&2; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
[[ -z "$FONTSDIR" && -d "$SCRIPT_DIR/fonts" ]] && FONTSDIR="$SCRIPT_DIR/fonts"
if [[ -n "$FONTSDIR" ]] && ! ls "$FONTSDIR"/*.[to]tf >/dev/null 2>&1; then
  echo "WARN: no .ttf/.otf in $FONTSDIR — libass will fall back to a system font (look may differ). Drop TikTokSans-Bold.ttf there (fonts/README.md)." >&2
fi

# --- CJK: pick a face that actually has the glyphs -----------------------------
HAS_CJK=0
if command -v python3 >/dev/null 2>&1; then
  if python3 - "$SRT" <<'PY'
import re, sys
text = open(sys.argv[1], encoding="utf-8", errors="replace").read()
sys.exit(0 if re.search(r"[\u3400-\u4dbf\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]", text) else 1)
PY
  then HAS_CJK=1; fi
fi
if [[ "$HAS_CJK" == "1" ]]; then
  if [[ "$FONT_SET" == "0" ]]; then
    if [[ -n "$FONTSDIR" ]] && ls "$FONTSDIR"/NotoSansSC*.[to]tf >/dev/null 2>&1; then
      FONT="Noto Sans SC"
    else
      # Prefer a Simplified-Chinese family; fc-list's first :lang=zh hit is often a
      # Traditional face (Heiti TC), which renders 简体 text in the wrong glyph style.
      #
      # 仅仅出现在 fc-list 里是不够的：macOS 上 PingFang SC 落在 SIP 保护的
      # PrivateFrameworks 下，fontconfig 解析不到它（fc-match "PingFang SC" 会返回
      # Verdana 这类完全无关的字体），libass 于是把中文静默烧成方框，ffmpeg 不报错。
      # 所以每个候选都必须过 fc-match 回读校验：要回来的族名对得上、文件可读。
      font_usable() {
        local fam="$1" out got file
        command -v fc-match >/dev/null 2>&1 || return 1
        out="$(fc-match -f '%{family}|%{file}' "$fam" 2>/dev/null)" || return 1
        got="${out%%|*}"; file="${out#*|}"
        printf '%s' "$got" | grep -qiF "$fam" || return 1
        [[ -r "$file" ]] || return 1
      }
      PICK=""
      if command -v fc-list >/dev/null 2>&1; then
        FAMILIES="$(fc-list :lang=zh family 2>/dev/null || true)"
        for fam in "Noto Sans CJK SC" "Noto Sans SC" "Source Han Sans SC" "PingFang SC" \
                   "Microsoft YaHei" "Hiragino Sans GB" "WenQuanYi Zen Hei" "Heiti SC" "STHeiti"; do
          printf '%s' "$FAMILIES" | grep -qF "$fam" || continue
          font_usable "$fam" || { echo "WARN: 跳过 '${fam}'——fontconfig 解析不到可用字体文件" >&2; continue; }
          PICK="$fam"; break
        done
        if [[ -z "$PICK" ]]; then
          while IFS= read -r cand; do
            cand="${cand%%,*}"
            [[ -n "$cand" ]] || continue
            if font_usable "$cand"; then PICK="$cand"; break; fi
          done <<< "$FAMILIES"
        fi
      fi
      if [[ -n "$PICK" ]]; then
        FONT="$PICK"
      else
        echo "ERROR: the captions contain CJK but no Chinese-capable font was found. Install one (e.g. Noto Sans SC) or use subtitle_paper_burn.py, which loads a font file directly." >&2
        exit 1
      fi
    fi
    echo "WARN: CJK captions detected -> switching the family to '${FONT}'. libass resolves it through fontconfig; extract a frame and confirm the text rendered." >&2
  fi
  if [[ "$NOCAPS" == "0" ]]; then
    echo "NOTE: uppercasing does nothing to Chinese but shouts any embedded English — pass --no-caps for mixed CN/EN captions." >&2
  fi
fi

# Force UPPERCASE in the srt copy. python3 = Unicode-correct (Cyrillic etc.);
# awk toupper is ASCII-only on mawk/BSD awk, so it is only the last-resort fallback.
# --no-caps keeps the srt as authored (natural sentence case — the UGC-natural look).
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
if [[ "$NOCAPS" == "1" ]]; then
  cp "$SRT" "$TMP/caps_upper.srt"
elif command -v python3 >/dev/null 2>&1; then
  python3 -c 'import sys; sys.stdout.write(open(sys.argv[1], encoding="utf-8", errors="replace").read().upper())' "$SRT" > "$TMP/caps_upper.srt"
else
  echo "WARN: python3 not found — using awk toupper (ASCII-only: non-Latin text may stay lowercase)." >&2
  awk 'BEGIN{RS="";FS="\n"} {print toupper($0) "\n"}' "$SRT" > "$TMP/caps_upper.srt" 2>/dev/null || cp "$SRT" "$TMP/caps_upper.srt"
fi

# ASS colours are &HAABBGGRR. White fill, black outline, semi-soft shadow.
# BorderStyle=1 => outline+shadow (NO opaque box). No BackColour plate.
STYLE="FontName=${FONT},Fontsize=${FSIZE},PrimaryColour=&H00FFFFFF&,OutlineColour=&H00000000&,BorderStyle=1,Outline=${OUTLINE},Shadow=${SHADOW},Alignment=2,MarginV=${MV},Bold=1"

FONTS_ARG=""; [[ -n "$FONTSDIR" ]] && FONTS_ARG=":fontsdir=${FONTSDIR}"
ffmpeg -y -loglevel error -i "$IN" -vf "subtitles=${TMP}/caps_upper.srt${FONTS_ARG}:force_style='${STYLE}'" \
  -c:v libx264 -preset veryfast -crf 20 -c:a copy "$OUT"
CASE_LABEL="CAPS"
if [[ "$NOCAPS" == "1" ]]; then CASE_LABEL="natural case"; fi
echo "DONE -> $OUT  (clean ${CASE_LABEL}, no plate, small bottom captions)"
