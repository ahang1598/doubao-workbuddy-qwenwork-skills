#!/usr/bin/env bash
# Probe a video and emit the fields the WorkRally edit modes need, as one line of JSON.
#
# SmartEdit requires source_video.width / height / duration where duration is in
# MILLISECONDS. This script emits duration_ms for exactly that field.
#
# Usage:
#   probe_video.sh <file-or-url>

set -euo pipefail

usage() {
  echo "usage: probe_video.sh <file-or-url>" >&2
  echo '  emits: {"width","height","duration_ms","duration_s","fps","has_audio","v_codec","a_codec","aspect"}' >&2
}

if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
  usage
  exit 0
fi
if [ $# -ne 1 ]; then
  usage
  exit 1
fi

SRC="$1"

if ! command -v ffprobe >/dev/null 2>&1; then
  echo "ffprobe 未安装。macOS 执行 brew install ffmpeg" >&2
  exit 127
fi

case "$SRC" in
  http://*|https://*) ;;
  *)
    [ -f "$SRC" ] || { echo "文件不存在: $SRC" >&2; exit 1; }
    ;;
esac

# Query each field on its own so we never depend on ffprobe's field ordering.
probe() {
  ffprobe -v error -select_streams "$1" -show_entries "stream=$2" \
    -of default=noprint_wrappers=1:nokey=1 "$SRC" 2>/dev/null | head -n1 || true
}

W=$(probe v:0 width)
H=$(probe v:0 height)
VCODEC=$(probe v:0 codec_name)
RATE=$(probe v:0 avg_frame_rate)
ACODEC=$(probe a:0 codec_name)

DUR=$(ffprobe -v error -show_entries format=duration \
  -of default=noprint_wrappers=1:nokey=1 "$SRC" 2>/dev/null | head -n1 || true)

# Container duration can be missing (raw streams); fall back to the video stream's.
if [ -z "$DUR" ] || [ "$DUR" = "N/A" ]; then
  DUR=$(probe v:0 duration)
fi
[ -z "$DUR" ] || [ "$DUR" = "N/A" ] && DUR="0"

if [ -z "$W" ] || [ -z "$H" ] || [ "$W" = "N/A" ]; then
  echo "未探测到视频流: $SRC" >&2
  exit 1
fi

DUR_MS=$(awk -v d="$DUR" 'BEGIN { printf "%d", (d * 1000) + 0.5 }')

FPS=$(awk -v r="${RATE:-0/0}" 'BEGIN {
  split(r, p, "/")
  if (p[2] != 0 && p[2] != "") printf "%.3f", p[1] / p[2]; else printf "0.000"
}')

# Snap the real ratio to the nearest WorkRally-supported one.
ASPECT=$(awk -v w="$W" -v h="$H" '
  function abs(x) { return x < 0 ? -x : x }
  BEGIN {
    r = w / h
    n = split("21:9 16:9 4:3 2:1 1:1 1:2 3:4 9:16", cand, " ")
    best = ""; bestd = 1e9
    for (i = 1; i <= n; i++) {
      split(cand[i], p, ":")
      d = abs(r - (p[1] / p[2]))
      if (d < bestd) { bestd = d; best = cand[i] }
    }
    print best
  }')

HAS_AUDIO=false
[ -n "$ACODEC" ] && [ "$ACODEC" != "N/A" ] && HAS_AUDIO=true
[ "$HAS_AUDIO" = "false" ] && ACODEC=""

printf '{"width":%s,"height":%s,"duration_ms":%s,"duration_s":%s,"fps":%s,"has_audio":%s,"v_codec":"%s","a_codec":"%s","aspect":"%s"}\n' \
  "$W" "$H" "$DUR_MS" "$DUR" "$FPS" "$HAS_AUDIO" "${VCODEC:-}" "$ACODEC" "$ASPECT"
