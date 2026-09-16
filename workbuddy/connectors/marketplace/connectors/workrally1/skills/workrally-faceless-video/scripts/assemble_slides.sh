#!/usr/bin/env bash
# assemble_slides.sh — the PICTURE STORY assembler: still images + per-beat
# voice takes -> ONE narrated video. THE SLIDE LASTS AS LONG AS ITS LINE:
# each image holds for exactly its take's duration (+ a small breath),
# minimum slide length enforced. Guarantees:
#   * pair count assert (--blocks N, mandatory for long runs) — a partial
#     video is impossible
#   * every slide's segment carries narration (asserted on the joined track,
#     BEFORE any music bed could mask a hole)
#   * LEVEL LAW — voice 1.0; optional music bed 0.10 (clamped <=0.20); no
#     clip SFX exists in this flow
#   * two-pass LINEAR loudnorm to -16 LUFS (ratios preserved)
#   * full decode validation of the final (audio present, spans video,
#     zero-error decode)
#   * one file out; hand-rolled ffmpeg remains forbidden by the skill
#
# Usage:
#   FRAME-BY-FRAME (picture-flow default):
#     scripts/assemble_slides.sh --out final.mp4 --audio narration.wav
#       --blocks N --timeline script_manifest.json --frames-dir work/frames
#       [--requested-seconds S]
#       [--max-hold 1.5] [--music bed.mp3]
#       [--music-vol 0.10]
#     frames.txt: one "image <seconds>" per line (durations from the Whisper
#     timeline). ONE continuous narration is laid over the whole cut; the
#     per-frame durations must sum to the narration length (-0.2s/+0.6s: the last
#     frame gets a ~0.3s tail hold so -shortest cannot clip the final word). N = the
#     frame count. The timeline is mechanically capped at 1.5s per frame.
#
#   LEGACY per-beat pairs (debugging only):
#     scripts/assemble_slides.sh --out final.mp4 --blocks N [--manifest pairs.txt]
#       [--breath 0.2] [--min-slide 1.0] [--max-hold 2.5] [--music bed.mp3]
#       [--music-vol 0.10] [--allow-mismatch]
#       [image001.png voice001.wav image002.png voice002.wav ...]
#
# MAX-HOLD: frame-by-frame timeline mode hard-caps every frame at 1.5s. The
# legacy per-beat mode uses --max-hold (2.5s by default). A longer hold is a
# hard ERROR: split it upstream.
#
# Manifest: one "image voice" pair per line, # comments allowed.
# --blocks N is REQUIRED on every run (pair count asserted before any work).
# EVERY slide image must be in the video's aspect (same ratio as slide 1,
# ±2%) — asset sheets (3:4 characters, 1:1 props) are refs, NEVER slides;
# a wrong-aspect image is a hard ERROR. Output is capped at 1080p-class
# (long side ≤1920). Subtitles are finish_video.sh --subs's job, not this script's;
# unavailable captioning = deliver unsubbed + warn. In this port the caption burn lives
# in finish_video.sh --subs, using scripts/subtitles/.
# Requires: ffmpeg, ffprobe, awk.
set -euo pipefail

OUT="final.mp4"; BREATH="0.2"; MINSLIDE="1.0"; MAXHOLD="2.5"; MUSIC=""; MVOL="0.10"; BLOCKS=""; REQUESTED_SECONDS=""; BILLING_BLOCKS=""; MANIFEST=""; TIMELINE=""; FRAMES_DIR=""; ALLOWMM=0; AUDIO=""; ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --out) OUT="$2"; shift 2 ;;
    --breath) BREATH="$2"; shift 2 ;;
    --min-slide) MINSLIDE="$2"; shift 2 ;;
    --max-hold) MAXHOLD="$2"; shift 2 ;;
    --audio) AUDIO="$2"; shift 2 ;;
    --music) MUSIC="$2"; shift 2 ;;
    --music-vol) MVOL="$2"; shift 2 ;;
    --blocks) BLOCKS="$2"; shift 2 ;;
    --requested-seconds) REQUESTED_SECONDS="$2"; shift 2 ;;
    --manifest) MANIFEST="$2"; shift 2 ;;
    --timeline) TIMELINE="$2"; shift 2 ;;
    --frames-dir) FRAMES_DIR="$2"; shift 2 ;;
    --subs) echo "ERROR: --subs was removed. Captions are burned by finish_video.sh --subs, which assembles first and then burns from the clean master." >&2; exit 2 ;;
    --allow-mismatch) ALLOWMM=1; shift ;;
    -h|--help) grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) ARGS+=("$1"); shift ;;
  esac
done
if [[ -n "$REQUESTED_SECONDS" ]]; then
  [[ "$REQUESTED_SECONDS" =~ ^[0-9]+$ ]] && (( REQUESTED_SECONDS > 0 )) || {
    echo "ERROR: --requested-seconds must be a positive integer" >&2
    exit 2
  }
  BILLING_BLOCKS=$(( (REQUESTED_SECONDS + 9) / 10 ))
fi
MVOL="$(awk -v v="$MVOL" 'BEGIN{v=v+0; if(v<0)v=0; if(v>0.2){print "WARN: --music-vol clamped to 0.20 (voice stays 1.0)" > "/dev/stderr"; v=0.2} printf "%.3f", v}')"
# bed_gain_db <voice_track> <bed_file> <mvol>
# The bed must sit ~14 dB under the SPEECH, whatever level the bed file happens to
# arrive at. A fixed multiplier cannot promise that: a hot generated bed at -8 dB mean
# times 0.10 still buries a -31 dB narration (dev 2026-07-29 — "music very loud, the
# voice is barely there"). So measure both and compute the gain; --music-vol stays the
# knob, read as a trim around its 0.10 default (0.05 = -6 dB, 0.20 = +6 dB).
bed_gain_db() {
  local vmean bmean trim
  vmean="$(ffmpeg -hide_banner -i "$1" -af volumedetect -f null - 2>&1 | grep -Eo 'mean_volume: *-?[0-9.]+' | grep -Eo '\-?[0-9.]+' | head -1)"
  bmean="$(ffmpeg -hide_banner -i "$2" -af volumedetect -f null - 2>&1 | grep -Eo 'mean_volume: *-?[0-9.]+' | grep -Eo '\-?[0-9.]+' | head -1)"
  awk -v v="${vmean:--20}" -v b="${bmean:--20}" -v mv="$3" 'BEGIN{
    trim = 20*log(mv/0.10)/log(10);
    g = (v - 14) - b + trim;
    if (g > 0) g = 0; if (g < -40) g = -40;
    printf "%.2f", g }'
}

for b in ffmpeg ffprobe awk python3; do command -v "$b" >/dev/null 2>&1 || { echo "ERROR: '$b' not found" >&2; exit 1; }; done

# ============================================================================
# FRAME-BY-FRAME MODE (--audio): ONE continuous narration track + a manifest of
# FRAMES with per-frame durations (from the Whisper timeline). Each frame holds
# for its duration; the narration is laid over the whole cut. This is the
# picture-flow default — the old per-beat pairs path stays below for debugging.
# Manifest / positional args: "image <seconds>" per frame.
# ============================================================================
if [[ -n "$AUDIO" ]]; then
  [[ -f "$AUDIO" ]] || { echo "ERROR: --audio not found: $AUDIO" >&2; exit 1; }
  [[ -n "$MUSIC" && ! -f "$MUSIC" ]] && { echo "ERROR: --music file not found: $MUSIC" >&2; exit 1; }
  ASSEMBLY_ATTEMPT=1
  TMP="$(mktemp -d)"
  trap 'rm -rf "$TMP"' EXIT
  FR_IMG=(); FR_DUR=(); FR_BEAT=(); FR_START=(); FR_END=()
  if [[ -n "$TIMELINE" ]]; then
    [[ -z "$MANIFEST" ]] || { echo "ERROR: pass --timeline or --manifest, not both" >&2; exit 1; }
    [[ -f "$TIMELINE" ]] || { echo "ERROR: --timeline not found: $TIMELINE" >&2; exit 1; }
    [[ -d "$FRAMES_DIR" ]] || { echo "ERROR: --frames-dir is required with --timeline" >&2; exit 1; }
    python3 - "$TIMELINE" > "$TMP/timeline.tsv" <<'PY'
import json
import sys

payload = json.load(open(sys.argv[1], encoding="utf-8"))
if payload.get("manifest_version") != 2:
    raise SystemExit("ERROR: scene timeline must use manifest_version 2")
frames = payload.get("frames")
if not isinstance(frames, list) or not frames:
    raise SystemExit("ERROR: scene timeline must contain frames")
previous_end = 0.0
previous_frame_job_id = None
previous_frame_url = None
previous_output_slot = None
for expected, frame in enumerate(frames, start=1):
    if not isinstance(frame, dict) or frame.get("n") != expected:
        raise SystemExit(f"ERROR: timeline frame {expected} is invalid")
    start = float(frame.get("start", -1))
    end = float(frame.get("end", -1))
    duration = float(frame.get("duration", -1))
    if abs(start - previous_end) > 0.01:
        raise SystemExit(f"ERROR: timeline gap/overlap before frame {expected}")
    if duration <= 0 or duration > 1.5 or abs((end - start) - duration) > 0.01:
        raise SystemExit(f"ERROR: timeline frame {expected} duration is invalid")
    if frame.get("output_slot") != f"frame-{expected:03d}":
        raise SystemExit(f"ERROR: timeline frame {expected} output_slot is invalid")
    frame_job_id = frame.get("frame_job_id")
    frame_url = frame.get("frame_url")
    if not isinstance(frame_job_id, str) or not frame_job_id.strip():
        raise SystemExit(f"ERROR: timeline frame {expected} frame_job_id is missing")
    if not isinstance(frame_url, str) or not frame_url.startswith(("http://", "https://")):
        raise SystemExit(f"ERROR: timeline frame {expected} frame_url is missing")
    if frame.get("image_mode") == "variation" and (
        frame.get("reference_output_slot") != previous_output_slot
        or frame.get("reference_frame_job_id") != previous_frame_job_id
        or frame.get("reference_frame_url") != previous_frame_url
    ):
        raise SystemExit(f"ERROR: timeline frame {expected} variation lineage is invalid")
    print(expected, int(frame["beat_n"]), f"{start:.3f}", f"{end:.3f}", f"{duration:.3f}", sep="\t")
    previous_end = end
    previous_frame_job_id = frame_job_id
    previous_frame_url = frame_url
    previous_output_slot = frame["output_slot"]
PY
    while IFS=$'\t' read -r frame_number beat_number frame_start frame_end frame_duration; do
      FR_IMG+=("${FRAMES_DIR}/frame$(printf '%03d' "$frame_number").png")
      FR_DUR+=("$frame_duration")
      FR_BEAT+=("$beat_number")
      FR_START+=("$frame_start")
      FR_END+=("$frame_end")
    done < "$TMP/timeline.tsv"
  elif [[ -n "$MANIFEST" ]]; then
    [[ -f "$MANIFEST" ]] || { echo "ERROR: --manifest not found: $MANIFEST" >&2; exit 1; }
    while read -r im du _extra; do
      [[ -z "$im" || "$im" == \#* ]] && continue
      [[ -n "$du" ]] || { echo "ERROR: --audio manifest line needs 'image <seconds>': '$im'" >&2; exit 1; }
      FR_IMG+=("$im"); FR_DUR+=("$du"); FR_BEAT+=("0"); FR_START+=("0"); FR_END+=("0")
    done < "$MANIFEST"
  else
    (( ${#ARGS[@]} >= 2 && ${#ARGS[@]} % 2 == 0 )) || { echo "ERROR: pass image/duration pairs or --manifest in --audio mode" >&2; exit 1; }
    for ((k=0;k<${#ARGS[@]};k+=2)); do
      FR_IMG+=("${ARGS[k]}"); FR_DUR+=("${ARGS[k+1]}")
      FR_BEAT+=("0"); FR_START+=("0"); FR_END+=("0")
    done
  fi
  frames=${#FR_IMG[@]}
  [[ -z "$BLOCKS" ]] && { echo "ERROR: --blocks N is REQUIRED (the frame count)." >&2; exit 1; }
  (( frames == BLOCKS )) || { echo "ERROR: --blocks $BLOCKS but $frames frames supplied — fix the manifest; do NOT ship a partial video." >&2; exit 1; }
  for im in "${FR_IMG[@]}"; do
    [[ -s "$im" ]] || { echo "ERROR: frame image not found or empty: $im" >&2; exit 1; }
  done
  ADUR="$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$AUDIO")"
  # DENSITY FLOOR: frame-by-frame needs a frame at least every ~1.5s (target ~1s).
  # A slideshow (e.g. 15 frames for a 60s story) is rejected outright — split beats
  # into micro-variation bursts until the count clears. Override with --max-hold only
  # to LOWER it; the floor uses 1.5s regardless so density is mechanical, not advisory.
  MINFRAMES="$(awk -v a="$ADUR" 'BEGIN{ m=int(a/1.5); if(m<1)m=1; print m }')"
  (( frames < MINFRAMES )) && { echo "ERROR: only ${frames} frames for ${ADUR}s of narration — that is a slideshow. Frame-by-frame needs >= ${MINFRAMES} frames (one every ~1.5s); most are cheap micro-variation edits of the previous frame. Re-cut the timeline denser and regenerate the missing frames." >&2; exit 1; }
  # DISTINCT-PICTURE FLOOR. The count above is manifest ENTRIES, which a run can satisfy by
  # listing the SAME picture N times — measured 2026-07-31 (R7): one image copied across
  # every frame of a 65s story passed a 43-frame floor and shipped as a gallery, and the
  # retry shipped 25 pictures where 43 were required. Uniqueness is by CONTENT, not by
  # filename, because the duplicates arrive as frame001.png..frameNNN.png.
  UNIQ="$(printf '%s\n' "${FR_IMG[@]}" | while read -r f; do md5sum "$f" 2>/dev/null | cut -d' ' -f1; done | sort -u | wc -l)"
  (( UNIQ < MINFRAMES )) && { echo "ERROR: ${frames} frame entries but only ${UNIQ} DISTINCT pictures for ${ADUR}s of narration — repeating one image is a gallery, not frame-by-frame. Need >= ${MINFRAMES} distinct pictures; most are cheap micro-variation EDITS of the previous frame (one reference image + one changed detail), not full re-renders." >&2; exit 1; }
  echo "  density: ${frames} entries / ${UNIQ} distinct pictures / floor ${MINFRAMES}" >&2
  DIMS="$(ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=p=0 "${FR_IMG[0]}")"
  W="${DIMS%%,*}"; H="${DIMS##*,}"; W=$(( (W/2)*2 )); H=$(( (H/2)*2 )); AR_W="$W"; AR_H="$H"
  if (( W > 1920 || H > 1920 )); then
    read -r W H <<< "$(awk -v w="$W" -v h="$H" 'BEGIN{ m=(w>h)?w:h; s=1920/m; printf "%d %d", int(w*s/2)*2, int(h*s/2)*2 }')"
    echo "  output capped to ${W}x${H} (1080p-class)" >&2
  fi
  # TAIL HOLD: the last frame is stretched so the VISUAL track outlasts the narration by
  # ~0.3s. -shortest then ends the file on the audio, so the final word is never clipped
  # (dev 2026-07-29 F8: "the sound cuts off at the end" — the picture ran out first, and a
  # held last frame is invisible while a missing last word is not).
  TAILHOLD=0.3
  PRESUM="$(awk 'BEGIN{s=0} {s+=$1} END{printf "%.3f", s}' <<< "$(printf '%s\n' "${FR_DUR[@]}")")"
  LASTI=$((frames-1))
  NEED="$(awk -v a="$ADUR" -v s="$PRESUM" -v th="$TAILHOLD" -v last="${FR_DUR[$LASTI]}" 'BEGIN{
    d=(a+th)-s; cap=1.5-last;
    if(d<0)d=0; if(cap<0)cap=0; if(d>cap)d=cap;
    printf "%.3f", d
  }')"
  if awk -v n="$NEED" 'BEGIN{exit (n>0.01)?0:1}'; then
    FR_DUR[$LASTI]="$(awk -v d="${FR_DUR[$LASTI]}" -v n="$NEED" 'BEGIN{printf "%.3f", d+n}')"
    echo "  tail hold: last frame extended by ${NEED}s so the narration is never clipped" >&2
  fi
  FPS=30; LIST="$TMP/frames.ffconcat"; printf 'ffconcat version 1.0\n' > "$LIST"; SUM=0; PBJSON=(); PREVNUM=-1
  echo "[1/3] ${frames} frames -> ${W}x${H} @ ${FPS}fps; narration ${ADUR}s laid over the cut" >&2
  for ((i=0;i<frames;i++)); do
    im="${FR_IMG[i]}"; du="${FR_DUR[i]}"
    [[ "$im" != *"'"* && "$im" != *$'\n'* ]] || { echo "ERROR: frame image path contains an unsupported quote or newline: $im" >&2; exit 1; }
    # ffmpeg resolves concat-demuxer paths relative to this temporary ffconcat,
    # not relative to the caller's cwd. Canonicalize before writing the list so
    # `--frames-dir .` and relative manifest paths remain valid.
    im="$(realpath "$im")"
    FR_IMG[i]="$im"
    # ORDER GUARD: frames must be named frameNNN and appear in STRICTLY
    # ASCENDING timeline order — a jumble (or job-finish/ls order) here is the
    # "frames assembled out of sequence" bug. Numberless names skip the check
    # (--allow-mismatch), but production always uses frameNNN.
    fn="$(basename "$im" | sed 's/\.[^.]*$//' | grep -Eo '[0-9]+' | tail -1 || true)"
    if [[ -n "$fn" ]]; then
      if (( 10#$fn <= PREVNUM )) && [[ "$ALLOWMM" != "1" ]]; then
        echo "ERROR: frame order broken at manifest line $((i+1)): $(basename "$im") (number ${fn}) does not come after ${PREVNUM}. The manifest must list frameNNN in STRICT ascending timeline order — rebuild it by looping the numbered timeline 1..N, not by ls or job-finish order (--allow-mismatch to override for unnumbered files)." >&2
        exit 1
      fi
      PREVNUM=$(( 10#$fn ))
    fi
    awk -v d="$du" 'BEGIN{exit (d+0>0)?0:1}' || { echo "ERROR: frame $((i+1)) has a non-positive duration '$du'" >&2; exit 1; }
    awk -v d="$du" -v m="$MAXHOLD" 'BEGIN{exit (d+0>m+0)?0:1}' && { echo "ERROR: frame $((i+1)) ($im) holds ${du}s (max ${MAXHOLD}s) — slideshow feel; split it into micro-variation frames." >&2; exit 1; }
    ID="$(ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=p=0 "$im")"
    IW="${ID%%,*}"; IH="${ID##*,}"
    awk -v w="$IW" -v h="$IH" -v W="$AR_W" -v H="$AR_H" 'BEGIN{ a=w/h; A=W/H; d=a-A; if(d<0)d=-d; exit (d/A<=0.02)?0:1 }' || {
      echo "ERROR: frame $(basename "$im") is ${IW}x${IH} — not the video aspect (${AR_W}x${AR_H}). Asset sheets are refs, NEVER frames: regenerate in the chosen aspect_ratio." >&2; exit 1; }
    printf "file '%s'\nduration %s\n" "$im" "$du" >> "$LIST"
    SUM="$(awk -v s="$SUM" -v d="$du" 'BEGIN{printf "%.3f", s+d}')"
    PBJSON[i]="$(printf '{"n":%d,"beat_n":%s,"start":%s,"end":%s,"image":"%s","dur":%s}' "$((i+1))" "${FR_BEAT[i]}" "${FR_START[i]}" "${FR_END[i]}" "$(basename "$im")" "$du")"
  done
  # sum of frame durations must match the narration (±0.6s): a mismatch means
  # the Whisper timeline and the frame plan disagree — fix the manifest.
  # The visual track may be up to (TAILHOLD + 0.2)s LONGER than the narration — that is
  # the deliberate tail hold above. It may never be SHORTER by more than 0.2s, and it may
  # never overshoot by more: a bigger gap means the timeline was estimated, and the
  # pictures then drift ahead of the words.
  awk -v s="$SUM" -v a="$ADUR" -v th="$TAILHOLD" 'BEGIN{x=s-a; exit (x>=-0.2 && x<=th+0.2)?0:1}' || {
    echo "ERROR: frame durations sum to ${SUM}s against ${ADUR}s of narration — outside [-0.2s, +$(awk -v th="$TAILHOLD" 'BEGIN{printf "%.1f", th+0.2}')s]. The pictures would drift off the words. Re-cut the frame timeline from the Whisper segment starts: a frame's duration is next_segment_start - this_segment_start, never an estimate." >&2; exit 1; }
  printf "file '%s'\n" "${FR_IMG[$LASTI]}" >> "$LIST"
  VSILENT="$TMP/vid.mp4"
  echo "[2/3] encode ${frames} timed frames in one pass -> visual track" >&2
  ffmpeg -y -loglevel error -f concat -safe 0 -i "$LIST" \
    -vf "scale=${W}:${H}:force_original_aspect_ratio=decrease,pad=${W}:${H}:(ow-iw)/2:(oh-ih)/2:black,fps=${FPS},format=yuv420p,setsar=1" \
    -t "$SUM" -an -c:v libx264 -preset veryfast -crf 20 -movflags +faststart "$VSILENT"
  # narration presence: the audio must not be silent (a broken track).
  QUIET="$(ffmpeg -i "$AUDIO" -af "silencedetect=noise=-40dB:d=2" -f null - 2>&1 | grep -c 'silence_start: 0' || true)"
  ATOT="$(ffmpeg -i "$AUDIO" -af "volumedetect" -f null - 2>&1 | awk -F': ' '/mean_volume/{print $2+0}')"
  awk -v m="$ATOT" 'BEGIN{exit (m < -70)?0:1}' && { echo "ERROR: --audio is effectively silent (mean ${ATOT}dB) — bad narration track; do NOT deliver." >&2; exit 1; }
  echo "[3/3] lay narration + finalize -> $OUT" >&2
  ln2b() { ffmpeg -hide_banner -i "$1" -af "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json" -f null - 2>&1 \
    | awk '/"input_i"/{i=$3}/"input_tp"/{t=$3}/"input_lra"/{l=$3}/"input_thresh"/{h=$3}/"target_offset"/{o=$3}{gsub(/[",]/,"",i);gsub(/[",]/,"",t);gsub(/[",]/,"",l);gsub(/[",]/,"",h);gsub(/[",]/,"",o)}END{printf "measured_I=%s:measured_TP=%s:measured_LRA=%s:measured_thresh=%s:offset=%s", i,t,l,h,o}'; }
  # Level-match the narration before anything is placed under it (same law as the
  # block assembler): a raw TTS track can arrive 10 dB quieter than a generated bed.
  NARRN="$TMP/narr_matched.wav"
  if ffmpeg -y -loglevel error -i "$AUDIO" -af "loudnorm=I=-19:TP=-1.5:LRA=11" -ar 44100 -ac 2 "$NARRN" 2>/dev/null; then
    echo "  narration level-matched to -19 LUFS before the bed" >&2
    AUDIO="$NARRN"
  fi
  if [[ -n "$MUSIC" ]]; then
    BEDG="$(bed_gain_db "$AUDIO" "$MUSIC" "$MVOL")"
    echo "  music bed: measured against the speech -> ${BEDG} dB (then ducked under the voice)" >&2
    ffmpeg -y -loglevel error -i "$VSILENT" -i "$AUDIO" -stream_loop -1 -i "$MUSIC" \
      -filter_complex "[1:a]aformat=sample_rates=44100:channel_layouts=stereo,asplit=2[vo][key];[2:a]aformat=sample_rates=44100:channel_layouts=stereo,volume=${BEDG}dB[m];[m][key]sidechaincompress=threshold=0.02:ratio=8:attack=10:release=300[duck];[vo][duck]amix=inputs=2:duration=first:normalize=0[a]" \
      -map 0:v -map "[a]" -shortest -c:v copy -c:a aac -b:a 192k "$TMP/mix.mp4"
  else
    ffmpeg -y -loglevel error -i "$VSILENT" -i "$AUDIO" \
      -filter_complex "[1:a]aformat=sample_rates=44100:channel_layouts=stereo[a]" \
      -map 0:v -map "[a]" -shortest -c:v copy -c:a aac -b:a 192k "$TMP/mix.mp4"
  fi
  LN="$(ln2b "$TMP/mix.mp4")"
  OUT_CANDIDATE="$TMP/final_candidate.mp4"
  if [[ "$LN" == *measured_I=-* ]]; then
    ffmpeg -y -loglevel error -i "$TMP/mix.mp4" -af "loudnorm=I=-16:TP=-1.5:LRA=11:${LN}:linear=true" -c:v copy -c:a aac -b:a 192k "$OUT_CANDIDATE"
  else
    ffmpeg -y -loglevel error -i "$TMP/mix.mp4" -af "loudnorm=I=-16:TP=-1.5:LRA=11" -c:v copy -c:a aac -b:a 192k "$OUT_CANDIDATE"
  fi
  DERR="$( (ffmpeg -v error -xerror -i "$OUT_CANDIDATE" -f null - ) 2>&1 | head -3 || true)"
  [[ -n "$DERR" ]] && { echo "ERROR: final failed decode validation:" >&2; echo "$DERR" >&2; exit 1; }
  # optional subtitles (same policy as the pair path)
  POSTER="${OUT%.mp4}_poster.jpg"
  POSTER_CANDIDATE="$TMP/final_poster.jpg"
  ffmpeg -y -loglevel error -ss 1 -i "$OUT_CANDIDATE" -frames:v 1 -q:v 2 "$POSTER_CANDIDATE" || true
  [[ -s "$POSTER_CANDIDATE" ]] || ffmpeg -y -loglevel error -i "$OUT_CANDIDATE" -frames:v 1 -q:v 2 "$POSTER_CANDIDATE" || true
  FDUR="$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUT_CANDIDATE")"
  SIDE="${OUT}.assembly.json"
  SIDE_CANDIDATE="$TMP/final.assembly.json"
  { printf '{"manifest_version":2,"timeline_version":2,"assembly_attempts":%d,"script":"assemble_slides.sh","mode":"frame-by-frame","out":"%s","frames":%d,"narration_s":%s,"actual_s":%s' \
      "$ASSEMBLY_ATTEMPT" "$(basename "$OUT")" "$frames" "$ADUR" "$FDUR"
    if [[ -n "$REQUESTED_SECONDS" ]]; then
      printf ',"requested_s":%d,"blocks":%d' "$REQUESTED_SECONDS" "$BILLING_BLOCKS"
    fi
    printf ',"width":%s,"height":%s,"fps":"%s","music":%s,"music_vol":%s,"gate":"one continuous narration over the cut, per-frame durations sum to narration -0.2/+0.6s (deliberate tail hold on the last frame), max-hold %ss, all frames in aspect, 1080p cap, ducked bed, 2-pass linear loudnorm -16, full decode","per_frame":[' \
      "$W" "$H" "$FPS" "$([[ -n "$MUSIC" ]] && echo true || echo false)" "$MVOL" "$MAXHOLD"
    for ((i=0;i<frames;i++)); do printf '%s%s' "${PBJSON[i]}" "$([[ $i -lt $((frames-1)) ]] && echo ,)"; done
    printf '],"ts":"%s"}\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"; } > "$SIDE_CANDIDATE"
  mv "$OUT_CANDIDATE" "$OUT"
  [[ -s "$POSTER_CANDIDATE" ]] && mv "$POSTER_CANDIDATE" "$POSTER"
  mv "$SIDE_CANDIDATE" "$SIDE"
  echo "ASSEMBLY-SIDECAR: $SIDE" >&2
  [[ -s "$POSTER" ]] && echo "POSTER: $POSTER" >&2
  echo "DONE: $OUT  (ONE file, ${frames} frames, narration ${ADUR}s, actual ${FDUR}s; decode-validated)" >&2
  exit 0
fi

# --- legacy per-beat pairs path (image+voice per line) — debugging only ---
# Manifest lines: "image voice" (one frame per beat) or "imageA imageB voice"
# (X2 CUT RATE: two frames per beat — the frame switches mid-take while the
# audio runs uninterrupted). Encoded internally as imgA|imgB in one slot.
if [[ -n "$MANIFEST" ]]; then
  [[ -f "$MANIFEST" ]] || { echo "ERROR: --manifest not found: $MANIFEST" >&2; exit 1; }
  while read -r f1 f2 f3 _extra; do
    [[ -z "$f1" || "$f1" == \#* ]] && continue
    if [[ -n "$f3" ]]; then ARGS+=("$f1|$f2" "$f3")
    elif [[ -n "$f2" ]]; then ARGS+=("$f1" "$f2")
    else echo "ERROR: manifest line has no voice file: '$f1'" >&2; exit 1; fi
  done < "$MANIFEST"
fi
for b in ffmpeg ffprobe awk; do command -v "$b" >/dev/null 2>&1 || { echo "ERROR: '$b' not found" >&2; exit 1; }; done
n=${#ARGS[@]}
(( n >= 2 && n % 2 == 0 )) || { echo "ERROR: pass image/voice PAIRS (or --manifest)" >&2; exit 1; }
pairs=$(( n / 2 ))
if [[ -n "$BLOCKS" ]] && (( pairs != BLOCKS )); then
  echo "ERROR: --blocks $BLOCKS declared but $pairs pairs supplied — a missing/extra beat. Fix the manifest; do NOT assemble a partial video." >&2; exit 1
fi
[[ -z "$BLOCKS" ]] && { echo "ERROR: --blocks N is REQUIRED — pass the expected beat count (a dropped beat must FAIL, not ship; short runs included)." >&2; exit 1; }
[[ -n "$MUSIC" && ! -f "$MUSIC" ]] && { echo "ERROR: --music file not found: $MUSIC" >&2; exit 1; }

TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
PBJSON=()   # per-beat sidecar entries (machine-readable assembly manifest)
img0="${ARGS[0]%%|*}"   # first image (strip the X2 "|imgB" part if line 1 is a triple)
DIMS="$(ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=p=0 "$img0")"
W="${DIMS%%,*}"; H="${DIMS##*,}"
# Even dimensions for yuv420p.
W=$(( (W/2)*2 )); H=$(( (H/2)*2 ))
AR_W="$W"; AR_H="$H"   # the video's aspect — every slide image must match it
# 1080p-class cap: the long side never exceeds 1920. 25+ beats at 2.7K blow
# encode time and upload size for zero visible gain on a slideshow.
if (( W > 1920 || H > 1920 )); then
  read -r W H <<< "$(awk -v w="$W" -v h="$H" 'BEGIN{ m=(w>h)?w:h; s=1920/m; w2=int(w*s/2)*2; h2=int(h*s/2)*2; print w2, h2 }')"
  echo "  output capped to ${W}x${H} (1080p-class; long side <=1920)" >&2
fi
FPS=30
echo "[1/3] ${pairs} slides -> ${W}x${H} @ ${FPS}fps; slide = its take's length (+${BREATH}s breath, min ${MINSLIDE}s)" >&2

LIST="$TMP/list.txt"; : > "$LIST"
BOUNDS="$TMP/bounds.txt"; : > "$BOUNDS"
TCUM=0
for ((i=0;i<pairs;i++)); do
  imgspec="${ARGS[i*2]}"; voice="${ARGS[i*2+1]}"
  imgA="${imgspec%%|*}"; imgB=""
  [[ "$imgspec" == *"|"* ]] && imgB="${imgspec##*|}"
  [[ -f "$imgA" ]] || { echo "ERROR: image not found: $imgA" >&2; exit 1; }
  [[ -n "$imgB" && ! -f "$imgB" ]] && { echo "ERROR: image not found: $imgB" >&2; exit 1; }
  [[ -f "$voice" ]] || { echo "ERROR: voice not found: $voice" >&2; exit 1; }
  # Extension stripped FIRST — otherwise ".mp4" reads as number 4.
  cn="$(basename "$imgA"  | sed 's/\.[^.]*$//' | grep -Eo '[0-9]+' | tail -1 || true)"
  vn="$(basename "$voice" | sed 's/\.[^.]*$//' | grep -Eo '[0-9]+' | tail -1 || true)"
  if [[ -z "$imgB" && -n "$cn" && -n "$vn" ]] && (( 10#$cn != 10#$vn )); then
    if [[ "$ALLOWMM" == "1" ]]; then
      echo "WARN: beat $((i+1)) mixes numbers: $(basename "$imgA") + $(basename "$voice") (--allow-mismatch)." >&2
    else
      echo "ERROR: beat $((i+1)) mixes numbers: $(basename "$imgA") + $(basename "$voice") — the voice would land on the WRONG picture. Fix the manifest order (or pass --allow-mismatch only for truly unnumbered files)." >&2
      exit 1
    fi
  fi
  # ASPECT assert: every slide image must match the video's aspect (slide 1's
  # ratio, ±2%). Asset sheets (3:4 characters, 1:1 props) are REFERENCES for
  # generation — they must never appear in the final as slides.
  for im in "$imgA" ${imgB:+"$imgB"}; do
    ID="$(ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=p=0 "$im")"
    IW="${ID%%,*}"; IH="${ID##*,}"
    awk -v w="$IW" -v h="$IH" -v W="$AR_W" -v H="$AR_H" 'BEGIN{ a=w/h; A=W/H; d=a-A; if(d<0)d=-d; exit (d/A<=0.02)?0:1 }' || {
      echo "ERROR: slide image $(basename "$im") is ${IW}x${IH} — not the video aspect (${AR_W}x${AR_H} from slide 1). Asset sheets are refs, NEVER slides: regenerate this beat's FRAME in the chosen aspect_ratio." >&2
      exit 1; }
  done
  A="$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$voice")"
  DUR="$(awk -v a="$A" -v br="$BREATH" -v mn="$MINSLIDE" 'BEGIN{d=a+br; if(d<mn)d=mn; printf "%.3f", d}')"
  # MAX-HOLD assert: no single FRAME stays on screen longer than MAXHOLD (2.5s
  # default; the grammar targets <=2s) — a hanging frame reads as a slideshow.
  # X2 beats hold each frame for half the slide.
  HOLD="$DUR"; [[ -n "$imgB" ]] && HOLD="$(awk -v d="$DUR" 'BEGIN{printf "%.3f", d/2}')"
  awk -v h="$HOLD" -v m="$MAXHOLD" 'BEGIN{exit (h>m)?0:1}' && {
    echo "ERROR: beat $((i+1)) holds one frame ${HOLD}s (max ${MAXHOLD}s) — slideshow feel. Split the beat (X2 pair / micro-variation) or tighten the phrase; long holds do not ship." >&2
    exit 1; }
  seg="$TMP/s_$(printf '%03d' "$i").mp4"
  VFILT="scale=${W}:${H}:force_original_aspect_ratio=decrease,pad=${W}:${H}:(ow-iw)/2:(oh-ih)/2:black,fps=${FPS},format=yuv420p,setsar=1"
  if [[ -n "$imgB" ]]; then
    # X2 CUT RATE beat: frame A holds the first half, frame B the second half;
    # the take's audio runs uninterrupted across the cut.
    D1="$(awk -v d="$DUR" 'BEGIN{printf "%.3f", d/2}')"
    D2="$(awk -v d="$DUR" -v h="$D1" 'BEGIN{printf "%.3f", d-h}')"
    ffmpeg -y -loglevel error -loop 1 -t "$D1" -i "$imgA" -loop 1 -t "$D2" -i "$imgB" -i "$voice" \
      -filter_complex "[0:v]${VFILT}[va];[1:v]${VFILT}[vb];[va][vb]concat=n=2:v=1:a=0[v];[2:a]aformat=sample_rates=44100:channel_layouts=stereo,apad[a]" \
      -map "[v]" -map "[a]" -t "$DUR" -c:v libx264 -preset veryfast -crf 20 -c:a aac -b:a 192k "$seg"
    printf '  beat %03d: take %.2fs -> slide %ss (TWO frames, cut at %ss) (at %ss)\n' "$((i+1))" "$A" "$DUR" "$D1" "$TCUM" >&2
  else
    ffmpeg -y -loglevel error -loop 1 -i "$imgA" -i "$voice" \
      -filter_complex "[0:v]${VFILT}[v];[1:a]aformat=sample_rates=44100:channel_layouts=stereo,apad[a]" \
      -map "[v]" -map "[a]" -t "$DUR" -c:v libx264 -preset veryfast -crf 20 -c:a aac -b:a 192k "$seg"
    printf '  beat %03d: take %.2fs -> slide %ss (at %ss)\n' "$((i+1))" "$A" "$DUR" "$TCUM" >&2
  fi
  echo "file '$seg'" >> "$LIST"
  TEND="$(awk -v c="$TCUM" -v d="$DUR" 'BEGIN{printf "%.3f", c+d}')"
  printf '%s %s %s\n' "$((i+1))" "$TCUM" "$TEND" >> "$BOUNDS"
  PBJSON[i]="$(printf '{"n":%d,"images":"%s","voice":"%s","take_s":%.2f,"slide_s":%s,"start_s":%s,"x2":%s}' \
    "$((i+1))" "$(basename "$imgA")$([[ -n "$imgB" ]] && echo "+$(basename "$imgB")")" "$(basename "$voice")" \
    "$A" "$DUR" "$TCUM" "$([[ -n "$imgB" ]] && echo true || echo false)")"
  TCUM="$TEND"
done

VOTRACK="$TMP/joined.mp4"
echo "[2/3] concat ${pairs} slides -> single track" >&2
ffmpeg -y -loglevel error -f concat -safe 0 -i "$LIST" -c:v libx264 -preset veryfast -crf 20 -c:a aac -movflags +faststart "$VOTRACK"

# NARRATION-PER-SEGMENT assert (before any music): each beat's segment must
# contain voice-level audio (peaks > -18dB).
QUIET="$(ffmpeg -i "$VOTRACK" -af "silencedetect=noise=-18dB:d=0.9" -f null - 2>&1 | grep -Eo 'silence_(start|end): *[0-9.]+' || true)"
EMPTY="$(awk -v BF="$BOUNDS" '
  BEGIN { while ((getline line < BF) > 0) { split(line,b," "); idx[++nb]=b[1]; st[nb]=b[2]; en[nb]=b[3] } }
  /silence_start/ { s[++k]=$NF+0; next }
  /silence_end/   { e[k]=$NF+0 }
  END {
    for (i=1;i<=nb;i++) {
      ws=st[i]+0.15; we=en[i]-0.35; if (we<=ws) continue;
      for (j=1;j<=k;j++) { ee=(e[j]>0)?e[j]:1e9;
        if (s[j]<=ws && ee>=we) { printf "%s%s", (out++?",":""), idx[i]; break } } } }' <<< "$QUIET")"
if [[ -n "$EMPTY" ]]; then
  echo "ERROR: beats [$EMPTY] have NO narration in their segments — a voice file is silent/mispaired. Fix the inputs and re-run; do NOT deliver." >&2
  exit 1
fi
echo "  narration present in all ${pairs} segments" >&2

echo "[3/3] finalize -> $OUT" >&2
ln2_args() {
  ffmpeg -hide_banner -i "$1" -af "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json" -f null - 2>&1 \
  | awk '/"input_i"/{i=$3}/"input_tp"/{t=$3}/"input_lra"/{l=$3}/"input_thresh"/{h=$3}/"target_offset"/{o=$3}
         {gsub(/[",]/,"",i);gsub(/[",]/,"",t);gsub(/[",]/,"",l);gsub(/[",]/,"",h);gsub(/[",]/,"",o)}
         END{printf "measured_I=%s:measured_TP=%s:measured_LRA=%s:measured_thresh=%s:offset=%s", i,t,l,h,o}'
}
if [[ -n "$MUSIC" ]]; then
  # DUCKING: the bed is sidechain-compressed by the VOICE — it dips hard while
  # narration plays and breathes back up in the gaps. The voice always wins.
  MIXED="$TMP/mixed.mp4"
  ffmpeg -y -loglevel error -i "$VOTRACK" -stream_loop -1 -i "$MUSIC" \
    -filter_complex "[0:a]aformat=sample_rates=44100:channel_layouts=stereo,asplit=2[vo][key];[1:a]aformat=sample_rates=44100:channel_layouts=stereo,volume=${MVOL}[m];[m][key]sidechaincompress=threshold=0.02:ratio=8:attack=10:release=300[duck];[vo][duck]amix=inputs=2:duration=first:normalize=0[a]" \
    -map 0:v -map "[a]" -shortest -c:v copy -c:a aac -b:a 192k "$MIXED"
  SRC="$MIXED"
else
  SRC="$VOTRACK"
fi
LNARGS="$(ln2_args "$SRC")"
if [[ "$LNARGS" == *measured_I=-* ]]; then
  ffmpeg -y -loglevel error -i "$SRC" -af "loudnorm=I=-16:TP=-1.5:LRA=11:${LNARGS}:linear=true" -c:v copy -c:a aac -b:a 192k "$OUT"
else
  echo "WARN: loudness measurement failed — falling back to single-pass loudnorm." >&2
  ffmpeg -y -loglevel error -i "$SRC" -af "loudnorm=I=-16:TP=-1.5:LRA=11" -c:v copy -c:a aac -b:a 192k "$OUT"
fi

# Final integrity: expected duration (sum of slides), audio stream, full decode.
FDUR="$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUT")"
awk -v d="$FDUR" -v e="$TCUM" 'BEGIN{x=d-e; if(x<0)x=-x; exit (x<=1.5)?0:1}' || {
  echo "ERROR: final duration ${FDUR}s != expected ${TCUM}s — do NOT deliver; investigate the inputs." >&2; exit 1; }
ADUR="$(ffprobe -v error -select_streams a:0 -show_entries stream=duration -of csv=p=0 "$OUT" | head -1)"
[[ -z "$ADUR" || "$ADUR" == "N/A" ]] && { echo "ERROR: final has no readable audio stream — do NOT deliver." >&2; exit 1; }
DERR="$( (ffmpeg -v error -xerror -i "$OUT" -f null - ) 2>&1 | head -3 || true)"
[[ -n "$DERR" ]] && { echo "ERROR: final failed decode validation — corrupted stream; do NOT deliver:" >&2; echo "$DERR" >&2; exit 1; }

# --- subtitles: NOT this script's job. Captions live in finish_video.sh --subs and
# are burned AFTER assembly, on the clean voice takes + this sidecar. The old
# in-assembler Whisper path was removed 2026-07-29: it transcribed the MIXED final
# audio (music + SFX under the speech), which is exactly how words get swallowed
# and captions drift. A --subs flag now refuses loudly instead of silently doing
# the wrong thing.

# --- poster frame: platform result thumbnail (~1s in, falling back to frame 0).
# Best-effort: a missing poster never fails the assembly.
POSTER="${OUT%.mp4}_poster.jpg"
ffmpeg -y -loglevel error -ss 1 -i "$OUT" -frames:v 1 -q:v 2 "$POSTER" || true
if [[ ! -s "$POSTER" ]]; then
  ffmpeg -y -loglevel error -i "$OUT" -frames:v 1 -q:v 2 "$POSTER" || true
fi
[[ -s "$POSTER" ]] && echo "POSTER: $POSTER" >&2 || echo "WARN: poster extraction failed (no $POSTER)" >&2

# --- assembly sidecar: machine-readable proof the final went through this
# script, gates included. Optional delivery metadata reads beat count
# and per-beat metrics from here; a final video without one was hand-assembled.
SIDE="${OUT}.assembly.json"
{
  printf '{"script":"assemble_slides.sh","out":"%s","beats":%d,"total_s":%s,"actual_s":%s' \
    "$(basename "$OUT")" "$pairs" "$TCUM" "$FDUR"
  if [[ -n "$REQUESTED_SECONDS" ]]; then
    printf ',"requested_s":%d,"blocks":%d' "$REQUESTED_SECONDS" "$BILLING_BLOCKS"
  fi
  printf ',"width":%s,"height":%s,"fps":"%s","breath":%s,"min_slide":%s,"music":%s,"music_vol":%s,"gate":"slide = take duration + breath (min slide), all slides in the video aspect (asset sheets rejected), 1080p-class cap, narration in every segment (silencedetect -18dB), 2-pass linear loudnorm -16, duration match, full decode","per_beat":[' \
    "$W" "$H" "$FPS" "$BREATH" "$MINSLIDE" \
    "$([[ -n "$MUSIC" ]] && echo true || echo false)" "$MVOL"
  for ((i=0;i<pairs;i++)); do printf '%s%s' "${PBJSON[i]}" "$([[ $i -lt $((pairs-1)) ]] && echo ,)"; done
  printf '],"ts":"%s"}\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
} > "$SIDE"
echo "ASSEMBLY-SIDECAR: $SIDE" >&2
echo "DONE: $OUT  (ONE file, ${pairs} slides, ${TCUM}s total, actual ${FDUR}s; decode-validated)" >&2
