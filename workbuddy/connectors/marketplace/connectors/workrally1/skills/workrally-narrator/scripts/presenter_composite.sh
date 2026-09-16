#!/usr/bin/env bash
# presenter_composite.sh — Phase P (presenter mode) per-block composite.
#
# Takes one explainer BLOCK clip and the presenter's voice-changed green-screen
# TALK clip, chroma-keys the person out (the key color is MEASURED from the talk
# clip's own corner — every model renders a different green shade), and
# composites them:
#
#   cutout    — person cut out flush in the bottom-right corner (facecam style)
#   badge     — Loom-style circle on a flat paper-tone disc, bottom-right w/ margin
#   fullframe — person keyed at block height, centered, flush bottom (on-camera
#               "cameo" look — the block scene stays visible around the person;
#               used by cameo mode on HOOK/TURN/CLOSER blocks)
#
# KEYING (two paths, auto-selected from the measured background):
#   - chromakey (YUV) ONLY for a truly broadcast-clean green: SAT>=60 AND R<30.
#     Olive/natural greens (e.g. RGB 59,129,69 — SAT hits 60 with R 59) have
#     near-neutral U/V: chromakey wipes or ghosts the person there.
#   - otherwise a NORMALIZED-CHROMATICITY key: wall = g/(r+g+b) > 0.42 AND
#     g>r+10 AND g>b+10. Luma-invariant, so gradient/vignetted walls key fully,
#     while green SPILL on the person (not green-DOMINANT) stays opaque.
#     Chain: geq mask -> dilation (1px fringe shave) -> gblur 1.2 -> negate ->
#     alphamerge -> despill.
#   - AUTO-FALLBACK: if the chromakey path keys the WALL fine (bg alpha < 16)
#     but eats the PERSON (face/torso < 245 — green spill on dark/reflective
#     clothing; measured on a real jacket: face 189, torso 20), the composite
#     retries with the chromaticity key before failing. The chromaticity path
#     accepts a slightly higher bg residue (< 40) — invisible once composited
#     over a scene. Person opacity (>245) is the HARD gate on both paths.
#
# QC SIDECAR: on success writes <out>.mp4.qc.json (route, alpha metrics, PASS)
# next to the output. Every presenter block must have one; a missing sidecar means
# the composite was hand-rolled and must not be delivered.
#
# Also extracts the block's narration audio from the talk clip, loudness-
# normalized to -16 LUFS (so the assembler's music level lands like a Phase-5
# take), FULL clip length (no trimming) so the assembler's fixed window never
# re-centers it and lipsync survives. Written next to the output as
# <out>_voice.wav — pass "<out>.mp4 <out>_voice.wav" to assemble_blocks.sh.
#
# Usage:
#   scripts/presenter_composite.sh BLOCK.mp4 TALK.mp4 OUT.mp4 \
#       [--style cutout|badge|fullframe]  # default cutout
#       [--pos br|bl|tr|tl]         # corner (default br). cutout: br|bl ONLY —
#                                   #   its torso is cut at the frame edge, so a
#                                   #   top corner would leave the body floating
#       [--key auto|0xRRGGBB]       # default auto (measured from TALK corner)
#       [--cut-h-frac F]            # cutout height as fraction of block height (default 0.64)
#       [--cut-w-frac F]            # center-crop width kept from talk frame (default 0.72)
#       [--badge-frac F]            # badge size as fraction of block height (default 0.355)
#       [--badge-crop-y PX]         # face vertical offset inside the disc crop (default 40;
#                                   #   a tighter head-and-shoulders framing wants ~130)
#       [--margin-frac F]           # override: uniform badge margin as fraction of height.
#                                   #   Default AUTO platform-safe margins by base aspect:
#                                   #   landscape 16:9 -> 5% W sides, 7% H top/bottom (title-safe);
#                                   #   portrait 9:16 (IG Reels/Stories spec, 1080x1920 basis) ->
#                                   #   top 250px (13.1% H), bottom 320px (16.7% H), sides 120px
#                                   #   (11.2% W); bottom corners' RIGHT margin widens to 21.8% W
#                                   #   (engagement rail covers the right edge of the bottom 40% H).
#       [--disc-color 0xRRGGBB]     # badge disc fill (default 0xE8DFD0)
#
# Requires: ffmpeg, ffprobe, od, awk, python3 (+PIL, numpy) for matte QC
set -euo pipefail

STYLE="cutout"; POS="br"; KEY="auto"; CUT_H_FRAC="0.64"; CUT_W_FRAC="0.72"
BADGE_FRAC="0.355"; BADGE_CROP_Y="40"; MARGIN_FRAC=""; DISC="0xE8DFD0"
ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --style) STYLE="$2"; shift 2 ;;
    --pos) POS="$2"; shift 2 ;;
    --key) KEY="$2"; shift 2 ;;
    --cut-h-frac) CUT_H_FRAC="$2"; shift 2 ;;
    --cut-w-frac) CUT_W_FRAC="$2"; shift 2 ;;
    --badge-frac) BADGE_FRAC="$2"; shift 2 ;;
    --badge-crop-y) BADGE_CROP_Y="$2"; shift 2 ;;
    --margin-frac) MARGIN_FRAC="$2"; shift 2 ;;
    --disc-color) DISC="$2"; shift 2 ;;
    -h|--help) grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) ARGS+=("$1"); shift ;;
  esac
done
[[ ${#ARGS[@]} -eq 3 ]] || { echo "usage: presenter_composite.sh BLOCK TALK OUT [--style cutout|badge] (see --help)" >&2; exit 2; }
BLOCK="${ARGS[0]}"; TALK="${ARGS[1]}"; OUT="${ARGS[2]}"
[[ "$STYLE" == "cutout" || "$STYLE" == "badge" || "$STYLE" == "fullframe" ]] || { echo "bad --style '$STYLE'" >&2; exit 2; }
[[ "$POS" == "br" || "$POS" == "bl" || "$POS" == "tr" || "$POS" == "tl" ]] || { echo "bad --pos '$POS' (br|bl|tr|tl)" >&2; exit 2; }
if [[ "$STYLE" == "cutout" && ( "$POS" == "tr" || "$POS" == "tl" ) ]]; then
  echo "cutout is bottom-only (torso is cut at the frame edge) — use --pos br|bl or --style badge" >&2; exit 2
fi
for f in "$BLOCK" "$TALK"; do [[ -f "$f" ]] || { echo "missing input: $f" >&2; exit 2; }; done

# Dependency preflight (local IDE machine, not a preinstalled sandbox image).
for b in ffmpeg ffprobe python3 od awk; do
  command -v "$b" >/dev/null 2>&1 || { echo "ERROR: '$b' not found — install it before compositing" >&2; exit 1; }
done
python3 -c "import PIL, numpy" >/dev/null 2>&1 || {
  echo "ERROR: the matte QC needs Pillow + numpy. Install them (python3 -m pip install pillow numpy) and rerun." >&2
  echo "       Do NOT hand-roll a chroma key and do NOT skip the QC: without it a half-transparent presenter ships silently." >&2
  exit 1
}

probe() { ffprobe -v error -select_streams v:0 -show_entries stream="$2" -of csv=p=0 "$1"; }
BW=$(probe "$BLOCK" width); BH=$(probe "$BLOCK" height)
TW=$(probe "$TALK" width);  TH=$(probe "$TALK" height)

# --- key color: average 5 background points (corners + top-center, 40x40 each at 1s).
# CORE = filter chain that turns the raw talk stream into keyed+despilled RGBA.
# It is embedded as "[1:v]${CORE},crop=..." in the composite and as
# "[0:v]${CORE}" in the QC probe.
# normalized-chromaticity chain (defined once — the auto route below and the
# chromakey->chromaticity QC fallback both use it)
CHROMA_CORE="format=gbrp,split[ks][km];[km]geq=r='255*gt(g(X,Y)*100,42*(r(X,Y)+g(X,Y)+b(X,Y)))*gt(g(X,Y),r(X,Y)+10)*gt(g(X,Y),b(X,Y)+10)':g='0':b='0',extractplanes=r,dilation,gblur=sigma=1.2,lutyuv=y=negval[ka];[ks][ka]alphamerge,despill=type=green"
CORE=""; ROUTE=""
if [[ "$KEY" == "auto" ]]; then
  # background points: top corners, top-center, and the two sides at 1/4 height —
  # above the shoulder line of a waist-up presenter (mid-height side points land
  # ON the person's arms and contaminate both the key mean and the QC)
  SAMPLES=$(for XY in "8:8" "iw-48:8" "8:ih/4" "iw-48:ih/4" "iw/2-20:8"; do
    X="${XY%%:*}"; Y="${XY##*:}"
    ffmpeg -v error -ss 1 -i "$TALK" -vf "crop=40:40:${X}:${Y},scale=1:1" -frames:v 1 -f rawvideo -pix_fmt rgb24 - 2>/dev/null | od -An -tu1 | awk '{print $1, $2, $3; exit}'
  done)
  # mean key + ADAPTIVE similarity: the measured spread of the background points
  # around the mean (normalized RGB distance) + margin — never a guessed constant
  read -r MR MG MB SIM <<<"$(echo "$SAMPLES" | awk '
    {r[NR]=$1;g[NR]=$2;b[NR]=$3;sr+=$1;sg+=$2;sb+=$3;n++}
    END{mr=sr/n;mg=sg/n;mb=sb/n;mx=0;
        for(i=1;i<=n;i++){d=sqrt((r[i]-mr)^2+(g[i]-mg)^2+(b[i]-mb)^2)/441.67; if(d>mx)mx=d}
        s=mx+0.04; if(s<0.08)s=0.08; if(s>0.15)s=0.15;
        printf "%d %d %d %.3f", mr, mg, mb, s}')"
  KEY=$(printf "0x%02X%02X%02X" "$MR" "$MG" "$MB")
  # sanity: green must dominate, or the measured points weren't background
  if [[ "$MG" -lt 80 || "$MG" -le "$MR" || "$MG" -le "$MB" ]]; then
    echo "presenter_composite: background ($MR,$MG,$MB) is not green — is the talk clip on a green screen?" >&2; exit 1
  fi
  SAT=$(( MG - (MR > MB ? MR : MB) ))
  # chromakey ONLY for broadcast-clean green (vivid AND near-zero red).
  # Olive/natural-wall greens (R>=30) ghost or wipe the person under chromakey
  # even when SAT crosses 60 (measured: SAT 60, R 59 -> person alpha 11/255),
  # and plain RGB colorkey eats green SPILL on clothing (torso alpha 161/255).
  # Those go to the chromaticity key instead.
  if [[ "$SAT" -ge 60 && "$MR" -lt 30 ]]; then
    SIM=$(awk -v s="$SIM" 'BEGIN{print (s<0.11)?"0.110":s}')  # chromakey needs a bit more reach on soft hair edges
    CORE="chromakey=${KEY}:${SIM}:0.05,despill=type=green"; ROUTE="chromakey"
    echo "KEY: $KEY -> chromakey=${KEY}:${SIM}:0.05"
  else
    # normalized-chromaticity key: wall = green-dominant in g/(r+g+b) space.
    # Luma-invariant -> survives gradient/vignetted walls; green SPILL on the
    # person (gray hoodie etc.) is not green-DOMINANT, so the person stays opaque.
    CORE="$CHROMA_CORE"; ROUTE="chromaticity"
    echo "KEY: $KEY (SAT=$SAT R=$MR) -> chromaticity key (g_norm>0.42)"
  fi
else
  CORE="chromakey=${KEY}:0.13:0.06,despill=type=green"; ROUTE="chromakey-manual"
  echo "KEY: $KEY -> $CORE"
fi

# --- matte QC: background must key to ~0 alpha; the person's FACE and TORSO
# must both stay opaque (>245). A face-only patch missed half-transparent
# torsos (green spill on clothing). If the CHROMAKEY path keys the wall (bg
# clean) but eats the person, retry once with the chromaticity key (relaxed
# bg < 40 — invisible over a scene; person gate unchanged). A FAIL after that
# means the generated green is too dirty for a clean key — regenerate the
# talking clip; do NOT hand-tune thresholds.
run_qc() { # $1 = CORE filter chain, $2 = bg alpha max -> prints metrics; rc 0/1
  # `mktemp --suffix` is GNU-only; BSD/macOS needs the XXXXXX template form.
  local png rc tmpd; tmpd=$(mktemp -d "${TMPDIR:-/tmp}/presenter_qc.XXXXXX"); png="$tmpd/matte.png"
  ffmpeg -y -v error -ss 2 -i "$TALK" -filter_complex "[0:v]$1" -frames:v 1 "$png"
  QC=$(python3 - "$png" "$2" <<'PY'
import sys
from PIL import Image
import numpy as np
im = np.array(Image.open(sys.argv[1]).convert("RGBA"))
bgmax = float(sys.argv[2])
h, w = im.shape[:2]
a = im[:, :, 3].astype(int)
pts = [(8, 8), (w - 48, 8), (8, h // 4), (w - 48, h // 4), (w // 2 - 20, 8)]
bg = float(np.mean([a[y:y + 40, x:x + 40].mean() for (x, y) in pts]))
face = float(a[int(h * 0.30):int(h * 0.55), int(w * 0.40):int(w * 0.60)].mean())
torso = float(a[int(h * 0.60):int(h * 0.85), int(w * 0.35):int(w * 0.65)].mean())
ok = bg < bgmax and face > 245 and torso > 245
print(f"{'PASS' if ok else 'FAIL'} bg_alpha={bg:.0f} face_alpha={face:.0f} torso_alpha={torso:.0f}")
sys.exit(0 if ok else 1)
PY
); rc=$?
  rm -rf "$tmpd"; echo "$QC"; return $rc
}
FALLBACK=0
if QCRES=$(run_qc "$CORE" 16); then
  echo "QC: $QCRES"
else
  echo "QC: $QCRES"
  BGV=$(sed -E 's/.*bg_alpha=([0-9]+).*/\1/' <<<"$QCRES")
  if [[ "$ROUTE" == chromakey* && "$BGV" -lt 16 ]]; then
    echo "QC: person alpha failed on chromakey with a clean bg -> auto-fallback to chromaticity key" >&2
    CORE="$CHROMA_CORE"; ROUTE="chromaticity-fallback"; FALLBACK=1
    if QCRES=$(run_qc "$CORE" 40); then
      echo "QC(fallback): $QCRES"
    else
      echo "QC(fallback): $QCRES"
      echo "presenter_composite: matte QC FAILED on both keys — regenerate this talking clip (bad green), do not tune thresholds" >&2; exit 3
    fi
  else
    echo "presenter_composite: matte QC FAILED — regenerate this talking clip (bad green), do not tune thresholds" >&2; exit 3
  fi
fi

even() { awk -v x="$1" 'BEGIN{ v=int(x+0.5); if (v%2) v=v+1; print v }'; }

# --- shared audio chain: full-length, loudnorm to -16 LUFS ---
VOICE="${OUT%.mp4}_voice.wav"
ACHAIN="loudnorm=I=-16:TP=-1.5:LRA=11,aformat=sample_rates=44100:channel_layouts=stereo"

if [[ "$STYLE" == "fullframe" ]]; then
  # cameo on-camera look: keyed person at BLOCK height, centered, flush bottom.
  FH=$(even "$BH")
  FILTER="[1:v]${CORE},scale=-2:${FH}[p];[0:v][p]overlay=(W-w)/2:H-h:shortest=1[v];[1:a]${ACHAIN}[a]"
elif [[ "$STYLE" == "cutout" ]]; then
  CH=$(even "$(awk -v h="$BH" -v f="$CUT_H_FRAC" 'BEGIN{print h*f}')")
  CW_KEEP="$CUT_W_FRAC"
  CW_OFF=$(awk -v f="$CUT_W_FRAC" 'BEGIN{printf "%.4f", (1-f)/2}')
  case "$POS" in
    br) OXY="x=W-w+6:y=H-h+2" ;;
    bl) OXY="x=-6:y=H-h+2" ;;
  esac
  FILTER="[1:v]${CORE},crop=iw*${CW_KEEP}:ih:iw*${CW_OFF}:0,scale=-2:${CH}[p];[0:v][p]overlay=${OXY}:shortest=1[v];[1:a]${ACHAIN}[a]"
else
  S=$(( TW < TH ? TW : TH ))
  MAXY=$(( TH - S )); CY=$(( BADGE_CROP_Y > MAXY ? MAXY : BADGE_CROP_Y ))
  CX=$(( (TW - S) / 2 ))
  C=$(( S / 2 )); R=$(awk -v s="$S" 'BEGIN{print int(s*0.4375)}'); R2=$(( R * R ))
  BMIN=$(( BW < BH ? BW : BH ))
  BS=$(even "$(awk -v h="$BMIN" -v f="$BADGE_FRAC" 'BEGIN{print h*f}')")
  # margins: explicit --margin-frac (uniform) or AUTO platform-safe by aspect
  px() { awk -v d="$1" -v f="$2" 'BEGIN{print int(d*f+0.5)}'; }
  if [[ -n "$MARGIN_FRAC" ]]; then
    MXL=$(px "$BH" "$MARGIN_FRAC"); MXR=$MXL; MYT=$MXL; MYB=$MXL
  elif (( BW >= BH )); then   # landscape: broadcast title-safe
    MXL=$(px "$BW" 0.05); MXR=$MXL; MYT=$(px "$BH" 0.07); MYB=$MYT
  else
    # portrait: Instagram Reels/Stories spec on a 1080x1920 canvas —
    # top 250px (13%), bottom 320px (16.7%), sides 120px (11.1%); the
    # engagement rail eats the RIGHT edge down the bottom 768px (40% H) to
    # ~235px (21.8% W), so bottom-right needs the wide right margin while
    # top corners keep the plain 120px one.
    MXL=$(px "$BW" 0.112); MYT=$(px "$BH" 0.131); MYB=$(px "$BH" 0.167)
    if [[ "$POS" == "br" || "$POS" == "bl" ]]; then
      MXR=$(px "$BW" 0.218)   # clear of the bottom-right button rail
    else
      MXR=$(px "$BW" 0.112)
    fi
  fi
  case "$POS" in
    br) OXY="x=W-w-${MXR}:y=H-h-${MYB}" ;;
    bl) OXY="x=${MXL}:y=H-h-${MYB}" ;;
    tr) OXY="x=W-w-${MXR}:y=${MYT}" ;;
    tl) OXY="x=${MXL}:y=${MYT}" ;;
  esac
  FILTER="color=c=white:s=${S}x${S},format=gray,geq=lum='if(lte((X-${C})*(X-${C})+(Y-${C})*(Y-${C}),${R2}),255,0)',split[circ][circ2];[1:v]${CORE},crop=${S}:${S}:${CX}:${CY},format=rgba,split[pkA][pkB];[pkA]alphaextract[pa];[pa][circ]blend=all_mode=multiply[clipmask];[pkB][clipmask]alphamerge[personclip];color=c=${DISC}:s=${S}x${S}[bg];[bg][circ2]alphamerge[disc];[disc][personclip]overlay,scale=${BS}:${BS}[badge];[0:v][badge]overlay=${OXY}:shortest=1[v];[1:a]${ACHAIN}[a]"
fi

ffmpeg -y -v error -i "$BLOCK" -i "$TALK" -filter_complex "$FILTER" \
  -map "[v]" -map "[a]" -c:v libx264 -crf 18 -preset veryfast -pix_fmt yuv420p -c:a aac "$OUT"
ffmpeg -y -v error -i "$TALK" -vn -af "$ACHAIN" -c:a pcm_s16le "$VOICE"

# --- QC sidecar: machine-readable proof this composite went through the
# script's matte QC. qc_final.py requires one PASS sidecar per presenter
# block; hand-rolled composites have none and fail final QC.
BGA=$(sed -E 's/.*bg_alpha=([0-9]+).*/\1/' <<<"$QCRES")
FCA=$(sed -E 's/.*face_alpha=([0-9]+).*/\1/' <<<"$QCRES")
TSA=$(sed -E 's/.*torso_alpha=([0-9]+).*/\1/' <<<"$QCRES")
SIDECAR="${OUT}.qc.json"
printf '{"script":"presenter_composite.sh","result":"PASS","style":"%s","pos":"%s","key":"%s","route":"%s","fallback":%s,"bg_alpha":%s,"face_alpha":%s,"torso_alpha":%s,"block":"%s","talk":"%s","out":"%s","ts":"%s"}\n' \
  "$STYLE" "$POS" "$KEY" "$ROUTE" "$FALLBACK" "$BGA" "$FCA" "$TSA" \
  "$(basename "$BLOCK")" "$(basename "$TALK")" "$(basename "$OUT")" \
  "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$SIDECAR"

echo "OUT: $OUT"
echo "VOICE: $VOICE"
echo "QC-SIDECAR: $SIDECAR"
