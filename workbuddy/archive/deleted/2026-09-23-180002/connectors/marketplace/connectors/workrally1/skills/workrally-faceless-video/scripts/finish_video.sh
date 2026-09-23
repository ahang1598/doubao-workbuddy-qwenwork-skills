#!/usr/bin/env bash
# ONE call for everything after the generations: download, assemble, caption, burn,
# verify, and print the receipts the gates read. Assembly always produces an
# immutable clean master. Captioning reads that master and writes the deliverable;
# it never burns into a file that may already contain captions.
#
# Why this exists: the sandbox is discarded seconds after a call returns, so the old
# shape — download, then assemble, then poll, then fonts, then captions, then burn,
# then check — lost its files three times in one dev run on 2026-07-29 and re-downloaded
# everything each time. Every step here is guarded and idempotent, so a recycled sandbox
# costs one re-run of THIS script and nothing else.
#
# Usage, motion blocks:
#   bash scripts/finish_video.sh --blocks 3 \
#        --clips-file clips.txt --voices-file voices.txt \
#        [--script script_manifest.json] [--subs clean|paper|bold] \
#        [--music URL|FILE] [--stepped 12] [--language en] [--out work/output/final.mp4]
#        [--sub-font "PingFang SC"] [--no-caps]
#
#   --language zh   implies --no-caps: uppercasing is meaningless for Chinese.
#   --sub-font      pin a caption face by family name. None of the fetched faces has
#                   CJK glyphs, so Chinese captions rely on a system CJK font — pin one
#                   here and inspect a burned frame before delivering.
#
# Usage, stills:
#   bash scripts/finish_video.sh --stills --timeline scene_manifest.json \
#        --frames-dir work/frames --narration URL --blocks N \
#        [--requested-seconds S] [--script script_manifest.json]
#   Legacy/debug: --stills --frames-file frames.txt --narration URL --blocks N
#
#   --allow-unverified-audio  continue only when faster_whisper is unavailable;
#                             the receipts mark the degraded content check
#   --no-verify-audio         legacy/debug: skip the take content check entirely
#   --no-voice                silent cut: clips only, no narration files; implies no --subs
#
#   clips.txt   one URL per line, in BLOCK order
#   voices.txt  one URL per line, same order (or one line for --stills narration)
#   frames.txt  one "URL seconds" pair per line, in timeline order
#
# Exit codes: 0 all gates green · 1 a gate failed (message on stderr, nothing shipped)
set -uo pipefail

OUT="work/output/final.mp4"
BLOCKS=""; CLIPS_FILE=""; VOICES_FILE=""; FRAMES_FILE=""; NARRATION=""
TIMELINE=""; FRAMES_DIR=""; REQUESTED_SECONDS=""
SCRIPT_MANIFEST=""; SUBS=""; MUSIC=""; STEPPED=""; LANG_OPT="en"; STILLS=0; VERIFY_AUDIO=1
ALLOW_UNVERIFIED_AUDIO=0; AUDIO_CONTENT_UNVERIFIED=""; SUB_FONT=""; NO_CAPS=0; NO_VOICE=0
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# WorkRally port: the caption helpers ship inside this skill, so there is no sandbox
# $HF_WORKFLOWS tree to look in.
SUBTITLE_SCRIPTS="$HERE/subtitles"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --blocks) BLOCKS="$2"; shift 2 ;;
    --clips-file) CLIPS_FILE="$2"; shift 2 ;;
    --voices-file) VOICES_FILE="$2"; shift 2 ;;
    --frames-file) FRAMES_FILE="$2"; shift 2 ;;
    --timeline) TIMELINE="$2"; shift 2 ;;
    --frames-dir) FRAMES_DIR="$2"; shift 2 ;;
    --requested-seconds) REQUESTED_SECONDS="$2"; shift 2 ;;
    --narration) NARRATION="$2"; shift 2 ;;
    --script) SCRIPT_MANIFEST="$2"; shift 2 ;;
    --subs) SUBS="$2"; shift 2 ;;
    --music) MUSIC="$2"; shift 2 ;;
    --stepped) STEPPED="$2"; shift 2 ;;
    --language) LANG_OPT="$2"; shift 2 ;;
    --sub-font) SUB_FONT="$2"; shift 2 ;;
    --no-caps) NO_CAPS=1; shift ;;
    --out) OUT="$2"; shift 2 ;;
    --stills) STILLS=1; shift ;;
    --allow-unverified-audio) ALLOW_UNVERIFIED_AUDIO=1; shift ;;
    --no-verify-audio) VERIFY_AUDIO=0; shift ;;
    --no-voice) NO_VOICE=1; shift ;;
    *) echo "ERROR: unknown argument $1" >&2; exit 1 ;;
  esac
done

die() { echo "ERROR: $*" >&2; exit 1; }
say() { echo "$*" >&2; }

command -v ffmpeg >/dev/null || die "ffmpeg is missing — run the Phase-0 preflight first"
command -v ffprobe >/dev/null || die "ffprobe is missing"
[[ -n "$SUBS" && "$SUBS" != "clean" && "$SUBS" != "paper" && "$SUBS" != "bold" ]] \
  && die "--subs takes clean, paper or bold (or omit it)"
if [[ $ALLOW_UNVERIFIED_AUDIO -eq 1 ]]; then
  [[ $VERIFY_AUDIO -eq 1 && $STILLS -eq 0 ]] \
    || die "--allow-unverified-audio is only valid for narrated motion verification"
  [[ -n "$SCRIPT_MANIFEST" && -s "$SCRIPT_MANIFEST" ]] \
    || die "--allow-unverified-audio requires a non-empty --script manifest"
  python3 -c "import faster_whisper" >/dev/null 2>&1 \
    && die "--allow-unverified-audio is forbidden when faster_whisper is available; run the mandatory content check"
fi

if [[ $NO_VOICE -eq 1 ]]; then
  [[ $STILLS -eq 0 ]] || die "--no-voice is not valid for --stills"
  [[ -z "$SUBS" ]] || die "--no-voice cannot burn captions (no narration to time)"
  VERIFY_AUDIO=0
fi

mkdir -p work/blocks work/voices work/frames work/output
chmod +x "$HERE"/*.sh "$SUBTITLE_SCRIPTS"/*.sh 2>/dev/null || true

# Keep assembly and presentation outputs separate. Reusing an already-captioned
# $OUT as the next burn input produces stacked duplicate captions on retries.
# The clean master is therefore the authoritative assembly artifact whenever
# subtitles are requested; $OUT remains the one user-facing deliverable.
CLEAN_MASTER="${OUT%.mp4}_clean.mp4"
ASSEMBLY_OUT="$OUT"
[[ -n "$SUBS" ]] && ASSEMBLY_OUT="$CLEAN_MASTER"

# fetch URL -> path, skipping a file that is already there and non-empty
fetch() {
  local url="$1" dst="$2"
  if [[ -s "$dst" ]]; then return 0; fi
  case "$url" in
    /*|./*|../*) cp -f "$url" "$dst" && return 0 || return 1 ;;
  esac
  curl -fsSL --retry 3 --retry-all-errors --max-time 180 -o "$dst.part" "$url" || { rm -f "$dst.part"; return 1; }
  [[ -s "$dst.part" ]] || { rm -f "$dst.part"; return 1; }
  mv -f "$dst.part" "$dst"
}

# ---------------------------------------------------------------- inputs
if [[ $STILLS -eq 1 ]]; then
  [[ -n "$NARRATION" ]] || die "--stills needs --narration"
  if [[ -n "$TIMELINE" ]]; then
    [[ -f "$TIMELINE" ]] || die "--timeline not found: $TIMELINE"
    [[ -n "$FRAMES_DIR" && -d "$FRAMES_DIR" ]] || die "--timeline needs --frames-dir with the materialized frameNNN files"
    [[ -n "$BLOCKS" ]] || die "--timeline needs --blocks N equal to its frame count"
    n="$BLOCKS"
  else
    [[ -n "$FRAMES_FILE" && -f "$FRAMES_FILE" ]] || die "--stills needs --timeline/--frames-dir or legacy --frames-file"
    : > work/frames.txt
    n=0
    while read -r url secs _rest; do
      [[ -z "${url:-}" || "$url" == \#* ]] && continue
      [[ -n "${secs:-}" ]] || die "frames file line $((n+1)) has no duration: $url"
      n=$((n+1))
      dst="$(printf 'work/frames/frame%03d.png' "$n")"
      fetch "$url" "$dst" || die "frame $n did not download: $url"
      printf '%s %s\n' "$dst" "$secs" >> work/frames.txt
    done < "$FRAMES_FILE"
    [[ $n -gt 0 ]] || die "frames file produced no frames"
  fi
  fetch "$NARRATION" work/voices/narration.wav || die "narration did not download"
  say "[finish] $n frames + narration in place"
else
  [[ -n "$BLOCKS" ]] || die "--blocks N is required (the pair count is asserted before any work)"
  [[ -n "$CLIPS_FILE" && -f "$CLIPS_FILE" ]] || die "--clips-file is required"
  CLIP_URLS=()
  while IFS= read -r item; do
    [[ -z "$item" || "$item" == \#* ]] || CLIP_URLS+=("$item")
  done < "$CLIPS_FILE"
  [[ ${#CLIP_URLS[@]} -eq $BLOCKS ]] || die "${#CLIP_URLS[@]} clip URLs against --blocks $BLOCKS — fix the list, do not assemble a partial video"
  : > work/pairs.txt
  if [[ $NO_VOICE -eq 1 ]]; then
    for ((i=0; i<BLOCKS; i++)); do
      idx=$(printf '%02d' $((i+1)))
      fetch "${CLIP_URLS[i]}" "work/blocks/block$idx.mp4" || die "block $idx did not download"
      printf 'work/blocks/block%s.mp4\n' "$idx" >> work/pairs.txt
    done
    say "[finish] $BLOCKS clips (no-voice) in place"
  else
    [[ -n "$VOICES_FILE" && -f "$VOICES_FILE" ]] || die "--voices-file is required"
    VOICE_URLS=()
    while IFS= read -r item; do
      [[ -z "$item" || "$item" == \#* ]] || VOICE_URLS+=("$item")
    done < "$VOICES_FILE"
    [[ ${#VOICE_URLS[@]} -eq $BLOCKS ]] || die "${#VOICE_URLS[@]} voice URLs against --blocks $BLOCKS"
    for ((i=0; i<BLOCKS; i++)); do
      idx=$(printf '%02d' $((i+1)))
      fetch "${CLIP_URLS[i]}" "work/blocks/block$idx.mp4" || die "block $idx did not download"
      fetch "${VOICE_URLS[i]}" "work/voices/voice$idx.wav" || die "voice $idx did not download"
      printf 'work/blocks/block%s.mp4 work/voices/voice%s.wav\n' "$idx" "$idx" >> work/pairs.txt
    done
    say "[finish] $BLOCKS clip/voice pairs in place"
  fi
fi

MUSIC_ARG=()
if [[ -n "$MUSIC" ]]; then
  fetch "$MUSIC" work/bed.mp3 || die "music bed did not download"
  MUSIC_ARG=(--music work/bed.mp3)
fi

# ------------------------------------------------- content check (provider mix-up)
# A dev run on 2026-07-29 got takes for a DIFFERENT video back from the TTS under load:
# every length gate passed and the words were about onions in a video about pandas, caught
# only at the caption step. So before assembling, transcribe each take with the tiny model
# and compare it against the line it is supposed to say.
if [[ $VERIFY_AUDIO -eq 1 && $STILLS -eq 0 && -n "$SCRIPT_MANIFEST" && -s "$SCRIPT_MANIFEST" ]]; then
  if python3 -c "import faster_whisper" >/dev/null 2>&1; then
    python3 "$HERE/verify_takes.py" --script "$SCRIPT_MANIFEST" --voice-dir work/voices --language "$LANG_OPT" \
      || die "a take does not say its line — regenerate that line, never assemble it"
  elif [[ $ALLOW_UNVERIFIED_AUDIO -eq 1 ]]; then
    AUDIO_CONTENT_UNVERIFIED="faster_whisper"
    say "[finish] WARN: faster_whisper is unavailable — take content is UNVERIFIED; caller must disclose this degraded fallback"
  else
    die "faster_whisper is required to verify narrated motion takes; never assemble unverified audio"
  fi
fi

# ---------------------------------------------------------------- assemble
if [[ ! -s "$ASSEMBLY_OUT" || ! -s "$ASSEMBLY_OUT.assembly.json" ]]; then
  if [[ $STILLS -eq 1 ]]; then
    REQUESTED_ARG=(); [[ -n "$REQUESTED_SECONDS" ]] && REQUESTED_ARG=(--requested-seconds "$REQUESTED_SECONDS")
    if [[ -n "$TIMELINE" ]]; then
      bash "$HERE/assemble_slides.sh" --out "$ASSEMBLY_OUT" --audio work/voices/narration.wav \
        --blocks "$BLOCKS" --timeline "$TIMELINE" --frames-dir "$FRAMES_DIR" \
        ${REQUESTED_ARG[@]+"${REQUESTED_ARG[@]}"} ${MUSIC_ARG[@]+"${MUSIC_ARG[@]}"} \
        || die "assemble_slides.sh failed — fix the inputs it named, never route around it"
    else
      FRAME_COUNT="$(wc -l < work/frames.txt | tr -d ' ')"
      bash "$HERE/assemble_slides.sh" --out "$ASSEMBLY_OUT" --audio work/voices/narration.wav \
        --blocks "$FRAME_COUNT" --manifest work/frames.txt \
        ${REQUESTED_ARG[@]+"${REQUESTED_ARG[@]}"} ${MUSIC_ARG[@]+"${MUSIC_ARG[@]}"} \
        || die "assemble_slides.sh failed — fix the inputs it named, never route around it"
    fi
  else
    STEP_ARG=(); [[ -n "$STEPPED" ]] && STEP_ARG=(--stepped "$STEPPED")
    ASSEMBLER_SCRIPT_ARG=(); [[ -n "$SCRIPT_MANIFEST" ]] && ASSEMBLER_SCRIPT_ARG=(--script "$SCRIPT_MANIFEST")
    CLIPONLY_ARG=(); [[ $NO_VOICE -eq 1 ]] && CLIPONLY_ARG=(--clips-only)
    bash "$HERE/assemble_final.sh" --out "$ASSEMBLY_OUT" --blocks "$BLOCKS" --manifest work/pairs.txt \
      ${MUSIC_ARG[@]+"${MUSIC_ARG[@]}"} ${STEP_ARG[@]+"${STEP_ARG[@]}"} \
      ${ASSEMBLER_SCRIPT_ARG[@]+"${ASSEMBLER_SCRIPT_ARG[@]}"} \
      ${CLIPONLY_ARG[@]+"${CLIPONLY_ARG[@]}"} \
      || die "assemble_final.sh failed — fix the inputs it named, never route around it"
  fi
else
  say "[finish] $ASSEMBLY_OUT already assembled, keeping the clean master"
fi

SIDECAR="$ASSEMBLY_OUT.assembly.json"
POSTER="${ASSEMBLY_OUT%.mp4}_poster.jpg"
[[ -s "$SIDECAR" ]] || die "no assembly sidecar next to $OUT — the file did not come out of the assembler"
[[ -s "$POSTER" ]] || die "no poster next to $OUT"

# ---------------------------------------------------------------- captions
SRT="${OUT%.mp4}.srt"
if [[ -n "$SUBS" ]]; then
  if [[ ! -s "$SRT" ]]; then
    bash "$SUBTITLE_SCRIPTS/fetch_fonts.sh" || true
    SCRIPT_ARG=(); [[ -n "$SCRIPT_MANIFEST" && -s "$SCRIPT_MANIFEST" ]] && SCRIPT_ARG=(--script "$SCRIPT_MANIFEST")
    [[ ${#SCRIPT_ARG[@]} -eq 0 ]] && say "[finish] WARN: no --script manifest, captions are STT-only and may miss quiet words"
    VOICE_DIR=work/voices
    # Motion captions use the clean per-block voice takes and the assembler's
    # per-block offsets. Picture Story has one continuous narration and a
    # per-frame assembly sidecar, so it must use the narration itself; passing
    # per_frame as --per-block makes audio_to_captions reject the sidecar before
    # Whisper even runs.
    CAPTION_INPUT=("$ASSEMBLY_OUT")
    CAPTION_TIMING=(--per-block "$SIDECAR" --voice-dir "$VOICE_DIR")
    if [[ $STILLS -eq 1 ]]; then
      CAPTION_INPUT=(work/voices/narration.wav)
      CAPTION_TIMING=()
    fi
    CAPTION_STATUS=0
    if python3 "$SUBTITLE_SCRIPTS/audio_to_captions.py" "${CAPTION_INPUT[@]}" \
          --srt "$SRT" "${CAPTION_TIMING[@]}" \
          --language "$LANG_OPT" "${SCRIPT_ARG[@]}"; then
      :
    else
      CAPTION_STATUS=$?
    fi
    if [[ $CAPTION_STATUS -eq 2 ]]; then
      say "[finish] WARN: Whisper is unavailable — delivering UNSUBBED, say so to the user"
      rm -f "$SRT"
    elif [[ $CAPTION_STATUS -ne 0 ]]; then
      die "caption generation failed — fix the transcript, authored script, or assembly sidecar; refusing to deliver an unverified cut"
    fi
  else
    say "[finish] $SRT already there, keeping it"
  fi

  if [[ -s "$SRT" ]]; then
    SUBBED="${OUT%.mp4}_subbed.mp4"
    # WorkRally port: Chinese captions are never uppercased, and none of the fetched
    # faces carries CJK glyphs — libass falls back to a system font, so let the caller
    # pin one with --sub-font and check a burned frame before delivering.
    if [[ "$LANG_OPT" == zh* ]]; then NO_CAPS=1; fi
    if [[ "$SUBS" == "paper" ]]; then
      python3 "$SUBTITLE_SCRIPTS/subtitle_paper_burn.py" --in "$ASSEMBLY_OUT" --srt "$SRT" --out "$SUBBED" \
        || die "the paper burner failed"
    else
      FONT_ARG=()
      if [[ -n "$SUB_FONT" ]]; then FONT_ARG=(--font "$SUB_FONT")
      elif [[ "$SUBS" == "bold" ]]; then FONT_ARG=(--font "TikTok Sans"); fi
      CASE_ARG=(); [[ $NO_CAPS -eq 1 ]] && CASE_ARG=(--no-caps)
      bash "$SUBTITLE_SCRIPTS/burn_caps_clean.sh" --in "$ASSEMBLY_OUT" --srt "$SRT" --out "$SUBBED" \
        ${FONT_ARG[@]+"${FONT_ARG[@]}"} ${CASE_ARG[@]+"${CASE_ARG[@]}"} \
        || die "the caption burner failed"
    fi
    [[ -s "$SUBBED" ]] || die "the burner produced no file"
    mv -f "$SUBBED" "$OUT"
    say "[finish] captions burned ($SUBS) from the immutable clean master"
  else
    cp -f "$ASSEMBLY_OUT" "$OUT"
  fi
fi

# Preserve the historical receipt names expected by callers while keeping the
# clean master's own receipts intact for a safe retry or a different caption look.
if [[ "$ASSEMBLY_OUT" != "$OUT" ]]; then
  cp -f "$SIDECAR" "$OUT.assembly.json"
  cp -f "$POSTER" "${OUT%.mp4}_poster.jpg"
fi

# ---------------------------------------------------------------- gates
VDUR="$(ffprobe -v error -select_streams v:0 -show_entries stream=duration -of csv=p=0 "$OUT" | head -1)"
ADUR="$(ffprobe -v error -select_streams a:0 -show_entries stream=duration -of csv=p=0 "$OUT" | head -1)"
[[ -n "$VDUR" ]] || die "no video stream in $OUT"
[[ -n "$ADUR" ]] || die "no audio stream in $OUT"
TOL=0.25; [[ $STILLS -eq 1 ]] && TOL=0.75   # stills hold the last frame past the narration on purpose
awk -v v="$VDUR" -v a="$ADUR" -v t="$TOL" 'BEGIN{ d=v-a; if (d<0) d=-d; exit (d<=t)?0:1 }' \
  || die "audio $ADUR s against video $VDUR s — the burn truncated the voice track"

python3 - "$SIDECAR" "${BLOCKS:-0}" "$STILLS" "${REQUESTED_SECONDS:-}" <<'PY' || exit 1
import json, sys
side, want, stills, requested_raw = sys.argv[1], int(sys.argv[2] or 0), sys.argv[3] == "1", sys.argv[4]
d = json.load(open(side))
if stills:
    # assemble_slides.sh writes frames + per_frame[{n,image,dur}]
    frames, per = d.get("frames"), d.get("per_frame") or []
    if want and frames != want:
        print(f"ERROR: sidecar says frames={frames}, the run declared {want}", file=sys.stderr); sys.exit(1)
    if requested_raw and d.get("requested_s") != int(requested_raw):
        print(f"ERROR: sidecar says requested_s={d.get('requested_s')}, the run declared {requested_raw}", file=sys.stderr); sys.exit(1)
    if not per or len(per) != frames or any("dur" not in f for f in per):
        print("ERROR: stills sidecar has no per_frame durations — the file did not come out of the assembler", file=sys.stderr); sys.exit(1)
    print(f"  sidecar: frames={frames} per_frame={len(per)} narration={d.get('narration_s')}s")
else:
    blocks, per = d.get("blocks"), d.get("per_block") or []
    if want and blocks != want:
        print(f"ERROR: sidecar says blocks={blocks}, the run declared {want}", file=sys.stderr); sys.exit(1)
    if not per or any("speech_s" not in b for b in per):
        print("ERROR: sidecar has no per_block speech metrics — the file did not come out of the assembler", file=sys.stderr); sys.exit(1)
    print(f"  sidecar: blocks={blocks} per_block={len(per)}")
PY

say ""
say "RECEIPTS"
say "  file      $OUT  (video ${VDUR}s / audio ${ADUR}s)"
say "  poster    $POSTER"
say "  sidecar   $SIDECAR"
[[ -n "$AUDIO_CONTENT_UNVERIFIED" ]] \
  && say "  audio_check UNAVAILABLE — AUDIO_CONTENT_UNVERIFIED=$AUDIO_CONTENT_UNVERIFIED; disclose this degraded fallback"
[[ -n "$SUBS" ]] && { [[ -s "$SRT" ]] && say "  srt       $SRT ($SUBS)" || say "  srt       NONE — delivered unsubbed, tell the user"; }
say "  DONE — every gate green. The caller must chain the presigned PUT before this sandbox command exits."
exit 0
