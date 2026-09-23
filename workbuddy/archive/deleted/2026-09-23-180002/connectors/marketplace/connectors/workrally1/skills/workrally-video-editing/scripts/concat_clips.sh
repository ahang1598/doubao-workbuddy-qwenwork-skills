#!/usr/bin/env bash
# Join clips into one file, normalising geometry, frame rate and audio first.
#
# Demuxer concat (-c copy) needs every input to match exactly; generated clips
# almost never do. This probes the inputs, picks a target, normalises, then joins.
#
# Usage:
#   concat_clips.sh -o out.mp4 a.mp4 b.mp4 c.mp4
#   concat_clips.sh -o out.mp4 --size 1080x1920 --fps 30 a.mp4 b.mp4
#   concat_clips.sh -o out.mp4 --fit cover a.mp4 b.mp4

set -euo pipefail

OUT=""; SIZE=""; FPS=""; CRF="20"; FIT="contain"; INPUTS=()

usage() {
  cat >&2 <<'EOF'
usage: concat_clips.sh -o <out.mp4> [options] <clip1> <clip2> [...]

  --size WxH   Target geometry. Default: the first clip's dimensions.
  --fps N      Target frame rate. Default: the highest among the inputs.
  --fit MODE   contain (letterbox, default) | cover (crop to fill)
  --crf N      x264 quality, lower is better. Default 20.

Always re-encodes. Silent inputs get a bounded synthetic track so the audio
branch of concat lines up with the video branch.
EOF
}

while [ $# -gt 0 ]; do
  case "$1" in
    -o|--out)  OUT="${2:-}"; shift 2 ;;
    --size)    SIZE="${2:-}"; shift 2 ;;
    --fps)     FPS="${2:-}"; shift 2 ;;
    --fit)     FIT="${2:-}"; shift 2 ;;
    --crf)     CRF="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    -*)        echo "未知参数: $1" >&2; usage; exit 1 ;;
    *)         INPUTS+=("$1"); shift ;;
  esac
done

if [ -z "$OUT" ] || [ "${#INPUTS[@]}" -lt 2 ]; then
  usage; exit 1
fi

case "$FIT" in
  contain|cover) ;;
  *) echo "--fit 只支持 contain 或 cover" >&2; exit 1 ;;
esac

for bin in ffmpeg ffprobe; do
  command -v "$bin" >/dev/null 2>&1 || {
    echo "$bin 未安装。macOS 执行 brew install ffmpeg" >&2
    exit 127
  }
done

probe() {
  ffprobe -v error -select_streams "$1" -show_entries "stream=$2" \
    -of default=noprint_wrappers=1:nokey=1 "$3" 2>/dev/null | head -n1 || true
}

# Pass 1 — collect per-clip facts.
CLIP_AUDIO=(); CLIP_DUR=()
for f in "${INPUTS[@]}"; do
  [ -f "$f" ] || { echo "文件不存在: $f" >&2; exit 1; }
  [ -n "$(probe v:0 width "$f")" ] || { echo "未探测到视频流: $f" >&2; exit 1; }

  if [ -n "$(probe a:0 codec_name "$f")" ]; then
    CLIP_AUDIO+=("yes")
  else
    CLIP_AUDIO+=("no")
  fi

  d=$(ffprobe -v error -show_entries format=duration \
    -of default=noprint_wrappers=1:nokey=1 "$f" 2>/dev/null | head -n1 || true)
  [ -z "$d" ] || [ "$d" = "N/A" ] && d=$(probe v:0 duration "$f")
  [ -z "$d" ] || [ "$d" = "N/A" ] && d="0"
  CLIP_DUR+=("$d")
done

# Target geometry: explicit, else the first clip. H.264 + yuv420p needs even sides.
if [ -z "$SIZE" ]; then
  W=$(probe v:0 width  "${INPUTS[0]}")
  H=$(probe v:0 height "${INPUTS[0]}")
else
  W="${SIZE%x*}"; H="${SIZE#*x}"
  case "${W}${H}" in *[!0-9]*|"") echo "--size 格式应为 WxH，例如 1080x1920" >&2; exit 1 ;; esac
fi
W=$(( (W / 2) * 2 )); H=$(( (H / 2) * 2 ))

# Target fps: explicit, else the highest among the inputs.
if [ -z "$FPS" ]; then
  FPS=1
  for f in "${INPUTS[@]}"; do
    r=$(probe v:0 avg_frame_rate "$f")
    [ -z "$r" ] && continue
    [ "$r" = "0/0" ] && continue
    v=$(awk -v r="$r" 'BEGIN { split(r, p, "/"); if (p[2] != 0) printf "%.0f", p[1] / p[2]; else print 0 }')
    [ "${v:-0}" -gt "$FPS" ] 2>/dev/null && FPS="$v"
  done
fi

echo "目标: ${W}x${H} @ ${FPS}fps, fit=${FIT}, ${#INPUTS[@]} 段" >&2

if [ "$FIT" = "cover" ]; then
  VSCALE="scale=${W}:${H}:force_original_aspect_ratio=increase,crop=${W}:${H}"
else
  VSCALE="scale=${W}:${H}:force_original_aspect_ratio=decrease,pad=${W}:${H}:(ow-iw)/2:(oh-ih)/2:black"
fi

# Pass 2 — build the input list and the filter graph together, tracking indices.
ARGS=(); FILTER=""; LABELS=""; idx=0
for n in "${!INPUTS[@]}"; do
  f="${INPUTS[$n]}"
  ARGS+=(-i "$f")
  vsrc="${idx}:v"
  idx=$((idx + 1))

  if [ "${CLIP_AUDIO[$n]}" = "yes" ]; then
    asrc="$((idx - 1)):a"
  else
    # anullsrc is infinite; -t bounds it so concat can advance past this segment.
    ARGS+=(-f lavfi -t "${CLIP_DUR[$n]}" -i "anullsrc=channel_layout=stereo:sample_rate=48000")
    asrc="${idx}:a"
    idx=$((idx + 1))
    echo "  片段 $((n + 1)) 无音轨，已补 ${CLIP_DUR[$n]}s 静音: $f" >&2
  fi

  FILTER="${FILTER}[${vsrc}]${VSCALE},setsar=1,fps=${FPS},format=yuv420p[v${n}];"
  FILTER="${FILTER}[${asrc}]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo[a${n}];"
  LABELS="${LABELS}[v${n}][a${n}]"
done

FILTER="${FILTER}${LABELS}concat=n=${#INPUTS[@]}:v=1:a=1[vout][aout]"

ffmpeg -hide_banner -y "${ARGS[@]}" \
  -filter_complex "$FILTER" \
  -map "[vout]" -map "[aout]" \
  -c:v libx264 -crf "$CRF" -preset medium -pix_fmt yuv420p -movflags +faststart \
  -c:a aac -b:a 192k \
  "$OUT"

echo >&2
echo "完成。核对总时长是否等于各段之和：" >&2
echo "  ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1 '$OUT'" >&2
