#!/usr/bin/env bash
# Burn an ASS or SRT subtitle file into a video, resolving a CJK-capable font first.
#
# WorkRally has no subtitle-burn tool — only subtitle erase. This is the burn path.
# Always burn LAST: a generative edit pass repaints the frame and destroys baked text.
#
# Font note: on macOS, "PingFang SC" resolves to a SIP-protected path that libass
# cannot open, and Chinese text silently renders as tofu boxes. This script probes
# for a font that actually resolves and overrides the subtitle file when needed.
#
# Usage:
#   burn_captions.sh -i in.mp4 -s captions.ass -o out.mp4
#   burn_captions.sh -i in.mp4 -s captions.srt -o out.mp4 --font "Hiragino Sans GB" --size 64

set -euo pipefail

IN=""; SUB=""; OUT=""; FONT=""; SIZE=""; CRF="20"

usage() {
  cat >&2 <<'EOF'
usage: burn_captions.sh -i <in.mp4> -s <captions.ass|srt> -o <out.mp4>
                        [--font <family>] [--size <px>] [--crf <n>]

  --font   Force a font family. Default: auto-detect a CJK-capable one.
  --size   Base font size. SRT only; ASS carries its own [V4+ Styles].
  --crf    x264 quality, lower is better. Default 20.

Burning re-encodes the video; audio is stream-copied.
EOF
}

while [ $# -gt 0 ]; do
  case "$1" in
    -i|--input) IN="${2:-}"; shift 2 ;;
    -s|--subs)  SUB="${2:-}"; shift 2 ;;
    -o|--out)   OUT="${2:-}"; shift 2 ;;
    --font)     FONT="${2:-}"; shift 2 ;;
    --size)     SIZE="${2:-}"; shift 2 ;;
    --crf)      CRF="${2:-}"; shift 2 ;;
    -h|--help)  usage; exit 0 ;;
    *)          echo "未知参数: $1" >&2; usage; exit 1 ;;
  esac
done

[ -n "$IN" ] && [ -n "$SUB" ] && [ -n "$OUT" ] || { usage; exit 1; }

command -v ffmpeg >/dev/null 2>&1 || {
  echo "ffmpeg 未安装。macOS 执行 brew install ffmpeg" >&2; exit 127; }

[ -f "$IN" ]  || { echo "输入视频不存在: $IN" >&2; exit 1; }
[ -f "$SUB" ] || { echo "字幕文件不存在: $SUB" >&2; exit 1; }

case "$(printf '%s' "$SUB" | tr '[:upper:]' '[:lower:]')" in
  *.ass|*.ssa) KIND="ass" ;;
  *.srt)       KIND="srt" ;;
  *) echo "不支持的字幕格式（需要 .ass / .ssa / .srt）: $SUB" >&2; exit 1 ;;
esac

# --- font resolution -------------------------------------------------------
# fc-match always returns *something*; a silent fallback to a Latin-only face is
# how tofu happens. Treat a match as real only when the requested family appears
# in the returned family list and the file is readable.
font_resolves() {
  local want="$1" out family file
  command -v fc-match >/dev/null 2>&1 || return 2
  out=$(fc-match --format='%{family}|%{file}' "$want" 2>/dev/null) || return 1
  family="${out%%|*}"; file="${out#*|}"
  [ -r "$file" ] || return 1
  printf '%s' ",$family," | grep -qiF ",$want," || return 1
  return 0
}

# Verified on macOS; the Linux/Windows entries are the usual CJK families.
CANDIDATES="Hiragino Sans GB
Noto Sans CJK SC
Source Han Sans SC
Source Han Sans CN
Songti SC
WenQuanYi Zen Hei
Microsoft YaHei
SimHei
Arial Unicode MS
PingFang SC"

pick_font() {
  local c
  while IFS= read -r c; do
    [ -n "$c" ] || continue
    if font_resolves "$c"; then printf '%s' "$c"; return 0; fi
  done <<EOF
$CANDIDATES
EOF
  return 1
}

FC_AVAILABLE=1
command -v fc-match >/dev/null 2>&1 || FC_AVAILABLE=0

OVERRIDE_FONT=""

if [ -n "$FONT" ]; then
  if [ "$FC_AVAILABLE" = "1" ] && ! font_resolves "$FONT"; then
    echo "警告: 字体 '$FONT' 在本机无法解析，中文可能渲染成方框" >&2
  fi
  OVERRIDE_FONT="$FONT"
elif [ "$FC_AVAILABLE" = "0" ]; then
  echo "提示: 未安装 fontconfig（fc-match），跳过字体自检。烧完请抽帧确认字形" >&2
elif [ "$KIND" = "ass" ]; then
  # Only override when a family the ASS actually declares fails to resolve.
  BAD=""
  while IFS= read -r fam; do
    [ -n "$fam" ] || continue
    font_resolves "$fam" || BAD="$fam"
  done <<EOF
$(awk -F',' '/^Style:/ { gsub(/^[ \t]+|[ \t]+$/, "", $2); print $2 }' "$SUB" | sort -u)
EOF
  if [ -n "$BAD" ]; then
    if OVERRIDE_FONT=$(pick_font); then
      echo "提示: ASS 声明的字体 '$BAD' 无法解析，已改用 '$OVERRIDE_FONT'" >&2
    else
      OVERRIDE_FONT=""
      echo "警告: 未找到可用的中文字体，中文可能渲染成方框" >&2
    fi
  fi
else
  if OVERRIDE_FONT=$(pick_font); then
    echo "提示: SRT 使用字体 '$OVERRIDE_FONT'" >&2
  else
    OVERRIDE_FONT=""
    echo "警告: 未找到可用的中文字体，中文可能渲染成方框" >&2
  fi
fi

# --- SRT normalisation -----------------------------------------------------
# libass renders SRT against a 384x288 canvas, so a Fontsize meant as video
# pixels comes out scaled by height/288 (3.75x at 1080p). Convert to ASS and
# rewrite PlayRes to the real frame size so force_style values are true pixels.
WORKSUB="$SUB"
TMPASS=""
cleanup() { [ -n "$TMPASS" ] && rm -f "$TMPASS"; }
trap cleanup EXIT

if [ "$KIND" = "srt" ]; then
  VW=$(ffprobe -v error -select_streams v:0 -show_entries stream=width \
    -of default=noprint_wrappers=1:nokey=1 "$IN" 2>/dev/null | head -n1)
  VH=$(ffprobe -v error -select_streams v:0 -show_entries stream=height \
    -of default=noprint_wrappers=1:nokey=1 "$IN" 2>/dev/null | head -n1)
  if [ -n "$VW" ] && [ -n "$VH" ]; then
    TMPASS="$(mktemp -t burncap).ass"
    ffmpeg -hide_banner -v error -y -i "$SUB" "$TMPASS"
    sed -i.bak -e "s/^PlayResX:.*/PlayResX: ${VW}/" -e "s/^PlayResY:.*/PlayResY: ${VH}/" "$TMPASS"
    rm -f "${TMPASS}.bak"
    WORKSUB="$TMPASS"
  else
    echo "警告: 未能读取视频尺寸，SRT 字号可能被放大" >&2
  fi
fi

# --- filter ----------------------------------------------------------------
# libavfilter parses the filter string, so ':' and '\' inside paths need escaping.
escape_path() {
  printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e 's/:/\\:/g' -e "s/'/\\\\'/g"
}

FILTER="subtitles='$(escape_path "$WORKSUB")'"

STYLE=""
if [ "$KIND" = "srt" ]; then
  # Now in real video pixels, scaled off frame height so 720p and 4K both read.
  BASE=$(awk -v h="${VH:-1080}" -v s="${SIZE:-0}" \
    'BEGIN { printf "%d", (s > 0 ? s : h * 0.052) }')
  MV=$(awk -v h="${VH:-1080}" 'BEGIN { printf "%d", h * 0.11 }')
  OL=$(awk -v b="$BASE" 'BEGIN { printf "%d", (b * 0.07 < 2 ? 2 : b * 0.07) }')
  STYLE="Fontsize=${BASE},PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000"
  STYLE="${STYLE},BorderStyle=1,Outline=${OL},Shadow=1,Alignment=2,MarginV=${MV}"
  [ -n "$OVERRIDE_FONT" ] && STYLE="Fontname=${OVERRIDE_FONT},${STYLE}"
else
  [ -n "$SIZE" ] && echo "提示: ASS 自带样式表，--size 已忽略；请改 [V4+ Styles]" >&2
  [ -n "$OVERRIDE_FONT" ] && STYLE="Fontname=${OVERRIDE_FONT}"
fi

[ -n "$STYLE" ] && FILTER="${FILTER}:force_style='${STYLE}'"

HAS_AUDIO=$(ffprobe -v error -select_streams a:0 -show_entries stream=codec_type \
  -of csv=p=0 "$IN" 2>/dev/null || true)

set -- ffmpeg -hide_banner -y -i "$IN" -vf "$FILTER" \
  -c:v libx264 -crf "$CRF" -preset medium -pix_fmt yuv420p -movflags +faststart
if [ -n "$HAS_AUDIO" ]; then set -- "$@" -c:a copy; else set -- "$@" -an; fi
set -- "$@" "$OUT"

echo "烧字幕（会重编码视频）: $SUB -> $OUT" >&2
"$@"

echo >&2
echo "完成。务必抽一帧核对字形没有变成方框、且文字在安全区内：" >&2
echo "  ffmpeg -ss 00:00:02 -i '$OUT' -frames:v 1 -q:v 2 check.jpg" >&2
