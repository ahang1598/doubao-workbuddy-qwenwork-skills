#!/usr/bin/env bash
# assemble_final.sh — ONE command that turns block clips + per-block voice lines into
# ONE finished video. Deterministic, weak-agent-proof: the agent calls this once and
# never hand-rolls ffmpeg. Guarantees:
#   * fixed length  = N × clip-seconds (default 10) — video is NEVER shortened to audio
#     (asserted on the output; the script FAILS if the final duration is off by > 1s)
#   * one file out   (never part1/part2)
#   * NO time-stretch (no atempo / no speed change) — a voice line whose SPEECH is
#     longer than the window is a HARD ERROR (rewrite + regenerate upstream)
#   * a clip shorter than the window by > 0.5s is a HARD ERROR (regenerate the block)
#   * each block's voice is centered by its SPEECH, not by file length: leading and
#     trailing silence in the TTS file is measured (silencedetect) and ignored, so a
#     padded take can't shift the words off their scene
#   * pair sanity: if the numbers in a clip filename and its voice filename disagree
#     (block03 + voice05), you get a WARNING — the #1 cause of "audio on the wrong block"
#   * NO leading freeze (first ~1.5s checked with freezedetect) and no long frozen
#     TAIL (last ~2s checked) — a WARNING means regenerate that block
#   * LEVEL LAW — voice 1.0 always; the clips' own diegetic SFX are KEPT under
#     the voice at 0.12 (--sfx-vol, clamped <=0.20); the optional music bed sits
#     at 0.10 (--music-vol, clamped <=0.20); final loudnorm -16 LUFS
#   * --sfx-vol 0 excludes clip audio entirely (voice/song is kept)
#
# Usage:
#   scripts/assemble_final.sh --out final.mp4 --blocks N [--clip-seconds 10]
#       [--music bed.mp3] [--music-vol 0.10] [--sfx-vol 0.12] [--manifest pairs.txt]
#       [--allow-mismatch]
#       [block01.mp4 voice01.wav block02.mp4 voice02.wav ...]
#
# Pass clip/voice PAIRS in block order — positionally, or (preferred, always in
# production) via --manifest: one "clip voice" pair per line, # comments allowed.
# --blocks N is REQUIRED on every run: the pair count is asserted BEFORE any
# work, so a dropped pair fails instead of shipping a hole. Pair-number
# mismatches (block03 + voice05) are an ERROR (--allow-mismatch to override
# for truly unnumbered files).
# Subtitles are NOT burned here — finish_video.sh --subs does that AFTER assembly
# on the clean voice takes + this script's sidecar. Captions are NEVER
# hand-timed by an agent.
# --song song.wav = SONG MODE (kids music video): args/manifest lines are
# CLIPS ONLY (one per block, no voice files); the one continuous sung track
# is laid over the whole cut at 1.0, clip SFX drop to 0.06 (unless --sfx-vol
# given); the song length must equal N x clip-seconds within +/-3s (hard
# assert — regenerate the song, never trim). Mutually exclusive with --music.
# Requires: ffmpeg, ffprobe, awk.
set -euo pipefail

OUT="final.mp4"; CLIP=10; MUSIC=""; MVOL="0.10"; SFXVOL="0.12"; SFXSET=0; BLOCKS=""; MANIFEST=""; ALLOWMM=0; SONG=""; CLIPONLY=0; STEPPED=""; SCRIPT=""; ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --out) OUT="$2"; shift 2 ;;
    --clip-seconds) CLIP="$2"; shift 2 ;;
    --stepped) STEPPED="$2"; shift 2 ;;
    --song) SONG="$2"; shift 2 ;;
    --clips-only) CLIPONLY=1; shift ;;
    --music) MUSIC="$2"; shift 2 ;;
    --music-vol) MVOL="$2"; shift 2 ;;
    --sfx-vol) SFXVOL="$2"; SFXSET=1; shift 2 ;;
    --blocks) BLOCKS="$2"; shift 2 ;;
    --manifest) MANIFEST="$2"; shift 2 ;;
    --script) SCRIPT="$2"; shift 2 ;;
    --subs) echo "ERROR: --subs was removed. Captions are burned by finish_video.sh --subs, which assembles first and then burns from the clean master." >&2; exit 2 ;;
    --allow-mismatch) ALLOWMM=1; shift ;;
    -h|--help) grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) ARGS+=("$1"); shift ;;
  esac
done
if [[ -n "$MANIFEST" ]]; then
  [[ -f "$MANIFEST" ]] || { echo "ERROR: --manifest not found: $MANIFEST" >&2; exit 1; }
  while read -r mc mv _extra; do
    [[ -z "$mc" || "$mc" == \#* ]] && continue
    if [[ -n "$SONG" || "$CLIPONLY" == "1" ]]; then
      # SONG / silent: manifest lines are CLIPS ONLY (one per line).
      [[ -n "$mv" ]] && { echo "ERROR: --song/--clips-only manifest lines carry ONE clip each (no voice files): '$mc $mv'" >&2; exit 1; }
      ARGS+=("$mc")
    else
      [[ -n "$mv" ]] || { echo "ERROR: manifest line has no voice file: '$mc'" >&2; exit 1; }
      ARGS+=("$mc" "$mv")
    fi
  done < "$MANIFEST"
fi
# SCRIPT LOCK: validate_motion_script.py writes script.lock next to the manifest it
# approved, holding a digest of the narration WORDS (formatting is free). A run that
# edits a line after the lock cannot reach the assembler any more. On 2026-07-31 a
# ten-minute run appended one identical filler sentence to 36 of its 60 lines to stretch
# them, pushed those takes past the speech ceiling and shipped nothing after 120 jobs.
SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCK=""
if [[ -n "$SCRIPT" ]]; then
  LOCK="$(dirname "$SCRIPT")/script.lock"
elif [[ -f script.lock ]]; then
  LOCK="script.lock"
fi
if [[ -n "$LOCK" && -f "$LOCK" ]]; then
  [[ -n "$SCRIPT" ]] || { echo "ERROR: $LOCK exists but --script was not passed. The assembler checks the narration against the locked script — pass --script <script_manifest.json>." >&2; exit 1; }
  [[ -f "$SCRIPT" ]] || { echo "ERROR: --script not found: $SCRIPT" >&2; exit 1; }
  python3 "$SELF_DIR/validate_motion_script.py" --script "$SCRIPT" \
    --duration-seconds "$(awk -v b="${BLOCKS:-1}" -v c="$CLIP" 'BEGIN{print (b*c>0? b*c : 10)}')" \
    --lock "$LOCK" --verify-lock >&2 || {
      echo "ERROR: the narration no longer matches $LOCK — a line changed after SCRIPT LOCK. A line changes ONLY by rewriting it and re-running validate_motion_script.py; appending or reusing text to reach a length is never allowed. Re-validate, regenerate the takes for the changed blocks, then assemble." >&2; exit 1; }
fi
# SONG MODE (kids music video): one continuous sung track over the whole cut.
# Clip SFX drop to 0.06 by default (barely-there under the song).
if [[ -n "$SONG" ]]; then
  [[ -f "$SONG" ]] || { echo "ERROR: --song file not found: $SONG" >&2; exit 1; }
  [[ -n "$MUSIC" ]] && { echo "ERROR: --song and --music are mutually exclusive (the song IS the music)." >&2; exit 1; }
  [[ "$CLIPONLY" == "1" ]] && { echo "ERROR: --song and --clips-only are mutually exclusive." >&2; exit 1; }
  [[ "$SFXSET" == "0" ]] && SFXVOL="0.06"
fi
# Silent / diegetic-only cut: no voice files. Clip audio IS the soundtrack.
if [[ "$CLIPONLY" == "1" && "$SFXSET" == "0" ]]; then
  SFXVOL="1"
fi
# LEVEL LAW: voice is ALWAYS 1.0; music defaults to 0.10 and SFX to 0.12, both
# hard-clamped at 0.20 so no caller can bury the narration in mush.
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
# The clip's own audio needs the SAME treatment and did not have it: --sfx-vol was a
# fixed multiplier of a level nobody measured, so how loud the SFX ended up depended on
# what the video model happened to render. A quiet clip vanished at 0.12 and a clip that
# came back with its own music or stray speech still competed with the narration.
# Measured the same way, the clip audio sits a fixed distance UNDER the voice and
# --sfx-vol becomes a trim around its default (0.06 = -6 dB, 0.24 = +6 dB).
# The gain goes both ways. A clip that arrives below the target must be lifted rather
# than disappearing from the mix; cap the lift at +10 dB so an empty noise floor is not
# raised into audibility.
# Called only for positive volumes; zero uses the voice-only path, not a dB floor.
sfx_gain_db() { # $1 = normalised voice file, $2 = clip, $3 = --sfx-vol
  local vmean cmean
  vmean="$(ffmpeg -hide_banner -i "$1" -af volumedetect -f null - 2>&1 | grep -Eo 'mean_volume: *-?[0-9.]+' | grep -Eo '\-?[0-9.]+' | head -1)"
  cmean="$(ffmpeg -hide_banner -i "$2" -af volumedetect -f null - 2>&1 | grep -Eo 'mean_volume: *-?[0-9.]+' | grep -Eo '\-?[0-9.]+' | head -1)"
  awk -v v="${vmean:--20}" -v c="${cmean:--60}" -v sv="$3" 'BEGIN{
    trim = 20*log(sv/0.12)/log(10);
    g = (v - 18) - c + trim;
    if (g > 10) g = 10; if (g < -40) g = -40;
    printf "%.2f", g }'
}

if [[ "$CLIPONLY" == "1" && "$SFXSET" == "0" ]]; then
  SFXVOL="1.000"
else
  SFXVOL="$(awk -v v="$SFXVOL" 'BEGIN{v=v+0; if(v<0)v=0; if(v>0.2){print "WARN: --sfx-vol clamped to 0.20 (voice stays 1.0)" > "/dev/stderr"; v=0.2} printf "%.3f", v}')"
fi
for b in ffmpeg ffprobe awk; do command -v "$b" >/dev/null 2>&1 || { echo "ERROR: '$b' not found" >&2; exit 1; }; done
# --stepped N: ANIMATE ON TWOS — re-time each block so the image updates only
# N times/sec (stepped, hand-drawn cartoon look; masks AI over-smoothness).
# Container fps and audio are untouched. Default off; Fairy Tale/Myth uses 12.
STEPPRE=""
if [[ -n "$STEPPED" ]]; then
  awk -v s="$STEPPED" 'BEGIN{exit (s+0>=2 && s+0<=30)?0:1}' || { echo "ERROR: --stepped must be an fps between 2 and 30 (e.g. 12 for on-twos)." >&2; exit 1; }
  STEPPRE="fps=${STEPPED},"
  echo "  --stepped ${STEPPED}: on-twos cadence (image updates ${STEPPED}x/sec)" >&2
fi
n=${#ARGS[@]}
if [[ -n "$SONG" || "$CLIPONLY" == "1" ]]; then
  (( n >= 1 )) || { echo "ERROR: pass CLIPS (one per block) or --manifest in --song/--clips-only mode" >&2; exit 1; }
  pairs=$n
else
  (( n >= 2 && n % 2 == 0 )) || { echo "ERROR: pass clip/voice PAIRS: clip1 voice1 clip2 voice2 ..." >&2; exit 1; }
  pairs=$(( n / 2 ))
fi
if [[ -n "$BLOCKS" ]] && (( pairs != BLOCKS )); then
  echo "ERROR: --blocks $BLOCKS declared but $pairs pairs supplied — a missing/extra block. Fix the manifest; do NOT assemble a partial video." >&2; exit 1
fi
[[ -z "$BLOCKS" ]] && { echo "ERROR: --blocks N is REQUIRED — pass the expected pair count (a dropped pair must FAIL, not ship; this is not optional on short runs either)." >&2; exit 1; }
[[ -n "$MUSIC" && ! -f "$MUSIC" ]] && { echo "ERROR: --music file not found: $MUSIC" >&2; exit 1; }
# SONG MODE: the song must fit the video (N x CLIP) within +/-3s — otherwise the
# song was generated at the wrong length: regenerate the SONG (never trim video).
if [[ -n "$SONG" ]]; then
  SDUR="$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$SONG")"
  awk -v s="$SDUR" -v e="$(( pairs * CLIP ))" 'BEGIN{x=s-e; if(x<0)x=-x; exit (x<=3)?0:1}' || {
    echo "ERROR: --song is ${SDUR}s but the video is $(( pairs * CLIP ))s (N x ${CLIP}) — regenerate the song at the target length (or fix N); do NOT trim either side." >&2; exit 1; }
fi

FINAL_OUT="$OUT"
ASSEMBLY_ATTEMPT=1
TMP="$(mktemp -d)"
cleanup() {
  rm -rf "$TMP"
}
trap cleanup EXIT
OUT="$TMP/final-candidate.mp4"
PBJSON=()   # per-block sidecar entries (machine-readable assembly manifest)
c0="${ARGS[0]}"
DIMS="$(ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=p=0 "$c0")"
W="${DIMS%%,*}"; H="${DIMS##*,}"
FPS_RAW="$(ffprobe -v error -select_streams v:0 -show_entries stream=r_frame_rate -of csv=p=0 "$c0")"
FPS="$(awk -F/ '{ if(NF==2 && $2>0) printf "%.4f",$1/$2; else print $1 }' <<< "$FPS_RAW")"; [ -z "$FPS" ] && FPS=30
echo "[1/3] ${pairs} blocks -> ${W}x${H} @ ${FPS}fps, fixed ${CLIP}s each; speech-centered, no atempo" >&2

LIST="$TMP/list.txt"; : > "$LIST"
# Voice-only twin of every block. Narration presence is asserted on this track, not on
# the finished mix where SFX transients can hide a missing voice.
VOLIST="$TMP/volist.txt"; : > "$VOLIST"
for ((i=0;i<pairs;i++)); do
  if [[ -n "$SONG" || "$CLIPONLY" == "1" ]]; then
    clip="${ARGS[i]}"; voice=""
  else
    clip="${ARGS[i*2]}"; voice="${ARGS[i*2+1]}"
  fi
  [[ -f "$clip"  ]] || { echo "ERROR: clip not found: $clip" >&2; exit 1; }
  [[ -z "$SONG" && "$CLIPONLY" != "1" && ! -f "$voice" ]] && { echo "ERROR: voice not found: $voice" >&2; exit 1; }
  if [[ -n "$SONG" || "$CLIPONLY" == "1" ]]; then
    # SONG MODE per-block: video checks only (duration + freeze probes); the
    # audio is the one continuous song, laid over the cut after concat.
    D="$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$clip")"
    awk -v d="$D" -v c="$CLIP" 'BEGIN{exit (d < c-0.5) ? 0 : 1}' && {
      echo "ERROR: clip $((i+1)) ($clip) is only ${D}s (<${CLIP}s) — REGENERATE the block." >&2; exit 1; }
    FRZH="$(ffmpeg -v info -t 1.5 -i "$clip" -vf "freezedetect=n=-60dB:d=1.0" -an -f null - 2>&1 | grep -c freeze_start || true)"
    [[ "$FRZH" != "0" ]] && echo "WARN: clip $((i+1)) ($clip) opens on ~static frames — regenerate this block (rule 21)." >&2
    FRZT="$(ffmpeg -v info -sseof -2 -i "$clip" -vf "freezedetect=n=-60dB:d=1.2" -an -f null - 2>&1 | grep -c freeze_start || true)"
    [[ "$FRZT" != "0" ]] && echo "WARN: clip $((i+1)) ($clip) ends on ~static frames (frozen tail) — consider regenerating." >&2
    out="$TMP/b_$(printf '%03d' "$i").mp4"
    HASAUD="$(ffprobe -v error -select_streams a:0 -show_entries stream=codec_type -of csv=p=0 "$clip" | head -1)"
    if [[ "$HASAUD" == "audio" && "$SFXVOL" != "0.000" ]]; then
      FC="[0:v]scale=${W}:${H}:force_original_aspect_ratio=decrease,pad=${W}:${H}:(ow-iw)/2:(oh-ih)/2:black,${STEPPRE}fps=${FPS},format=yuv420p,setsar=1,tpad=stop_mode=clone:stop_duration=${CLIP}[v];[0:a]volume=${SFXVOL},apad[a]"
      ffmpeg -y -loglevel error -i "$clip" -filter_complex "$FC" \
        -map "[v]" -map "[a]" -t "$CLIP" -c:v libx264 -preset veryfast -crf 20 -c:a aac -b:a 192k "$out"
    else
      FC="[0:v]scale=${W}:${H}:force_original_aspect_ratio=decrease,pad=${W}:${H}:(ow-iw)/2:(oh-ih)/2:black,${STEPPRE}fps=${FPS},format=yuv420p,setsar=1,tpad=stop_mode=clone:stop_duration=${CLIP}[v]"
      ffmpeg -y -loglevel error -i "$clip" -f lavfi -t "$CLIP" -i "anullsrc=r=44100:cl=stereo" -filter_complex "$FC" \
        -map "[v]" -map 1:a -t "$CLIP" -c:v libx264 -preset veryfast -crf 20 -c:a aac -b:a 192k "$out"
    fi
    echo "file '$out'" >> "$LIST"
    printf '  block %02d: clip %.2fs (%s, sfx %.2f)\n' "$((i+1))" "$D" "$([[ -n "$SONG" ]] && echo song || echo clips-only)" "$SFXVOL" >&2
    PBJSON[i]="$(printf '{"n":%d,"clip":"%s","voice":"","clip_s":%.2f,"speech_s":0,"speech_abs_s":0,"lead_silence_s":0,"internal_pauses":0,"freeze_head":%s,"freeze_tail":%s}' \
      "$((i+1))" "$(basename "$clip")" "$D" \
      "$([[ "${FRZH:-0}" != "0" ]] && echo true || echo false)" "$([[ "${FRZT:-0}" != "0" ]] && echo true || echo false)")"
    continue
  fi
  # Pair sanity: numbers in the two filenames should match (block03 <-> voice03).
  # The extension is stripped FIRST — otherwise ".mp4" reads as number 4.
  cn="$(basename "$clip"  | sed 's/\.[^.]*$//' | grep -Eo '[0-9]+' | tail -1 || true)"
  vn="$(basename "$voice" | sed 's/\.[^.]*$//' | grep -Eo '[0-9]+' | tail -1 || true)"
  if [[ -n "$cn" && -n "$vn" ]] && (( 10#$cn != 10#$vn )); then
    if [[ "$ALLOWMM" == "1" ]]; then
      echo "WARN: pair $((i+1)) mixes numbers: $(basename "$clip") + $(basename "$voice") (--allow-mismatch)." >&2
    else
      echo "ERROR: pair $((i+1)) mixes numbers: $(basename "$clip") + $(basename "$voice") — the audio would land on the WRONG block. Fix the manifest order (or pass --allow-mismatch only if the files are truly unnumbered)." >&2
      exit 1
    fi
  fi
  A="$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$voice")"
  D="$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$clip")"
  # SPEECH bounds: ignore leading/trailing silence of the TTS file when centering.
  EVENTS="$(ffmpeg -i "$voice" -af silencedetect=noise=-45dB:d=0.25 -f null - 2>&1 | grep -Eo 'silence_(start|end): *-?[0-9.]+' || true)"
  read -r SS SE <<< "$(awk -v A="$A" '
    /silence_start/ { s=$NF+0; if(first==""){first=s}; last=s; open=1; next }
    /silence_end/   { e=$NF+0; if(first!="" && first<0.1 && ssdone==""){ss=e; ssdone=1};
                      e_last=e; s_before=last; open=0 }
    END {
      if (open==1)                      se=last;        # file ended inside silence
      else if (e_last>0 && A-e_last<0.2) se=s_before;   # EOF auto-closed the tail silence
      else                               se=A;          # speech runs to the end
      printf "%.3f %.3f", ss+0, se+0 }' <<< "$EVENTS")"
  [[ -z "${SS:-}" ]] && SS=0; [[ -z "${SE:-}" ]] && SE="$A"
  SPEECH="$(awk -v a="$SS" -v b="$SE" 'BEGIN{d=b-a; if(d<=0)d=0; printf "%.3f", d}')"
  # A degenerate detect (all-silence or no events) falls back to the full file.
  awk -v s="$SPEECH" 'BEGIN{exit (s<0.3)?0:1}' && { SS=0; SE="$A"; SPEECH="$A"; }
  # Pausey-take probe: internal silences >=0.8s INSIDE the speech (a flowing line has
  # none; every full stop the TTS honours costs ~0.7s of dead air on screen).
  read -r IPN IPMAX <<< "$(awk -v lo="$SS" -v hi="$SE" '
    /silence_start/ { s=$NF+0; open=1; next }
    /silence_end/   { e=$NF+0; if(open==1 && s>lo+0.1 && e<hi-0.1 && e-s>=0.8){n++; if(e-s>mx)mx=e-s}; open=0 }
    END{ printf "%d %.2f", n+0, mx+0 }' <<< "$EVENTS")"
  [[ "${IPN:-0}" != "0" ]] && echo "WARN: voice $((i+1)) ($voice) has ${IPN} internal pause(s) >=0.8s (longest ${IPMAX}s) — pausey take: rewrite the line as ONE flowing clause (fewer full stops) and regenerate." >&2
  # HARD checks — narration must fill a 10s block without clipping. Expressed
  # relative to CLIP so the script's --clip-seconds option keeps the same margins.
  # WINDOW: floor CLIP-2.2, ceiling CLIP-0.5 (7.8–9.5s for the production 10s block).
  # seed_audio lengths are BIMODAL — the same line returns near 9.0s or near 10.4s, and the
  # pace wanders 1.9-3.4 words/sec between generations. The old 9.4-9.8 band sat in the dead
  # zone BETWEEN the modes, so even a good 9.0s take was rejected: two dev runs on 2026-07-29
  # spent ~150 generations on 18 lines and then started cutting silence inside the takes to
  # pass, which is audible. The band below still brackets the low mode.
  # The ceiling is below CLIP, never CLIP: a take whose speech is as long as the block has zero
  # margin, so the closing consonant lands on the -t CLIP cut and the word is chopped
  # (reproduced 2026-07-31: speech 0.50..10.20 in a 10s block passed the gate and shipped
  # clipped).
  # MOVED 2026-08-01, and the placement is the point. The band used to be CLIP-1.4..CLIP-0.4
  # (8.6-9.6) and it sat in the wrong PLACE: six consecutive takes at the [00:00-00:09] bracket
  # measured 8.58 8.61 8.65 8.69 8.94 8.98, so the old floor ran through the middle of the
  # provider's own distribution and rejected good takes by tens of milliseconds — one run died
  # on 8.580 against 8.600 — while the old ceiling left the closing word 0.05s from the cut on
  # the rare take that reached it. CLIP-0.5 leaves 0.25s of tail after plain centring, which is the deliberate trade:
  # a take between 9.2 and 9.5 is ACCEPTED rather than re-rolled, because a regeneration costs
  # far more than the quarter second it borrows.
  # 2026-08-03: the ceiling now has slack it never uses. The word band came down to 20-23 and
  # the TTS bracket stayed at [00:00-00:09], which lands takes at 8.5-8.9 — measured 8.68 and
  # 8.48 on the pair that fixed the clipping. Length alone should no longer reject anything;
  # if it starts to, the bracket has been widened somewhere and the two must move together.
  # CLIP-2.0 is a floor against
  # a FAILED take, not a pacing rule: 1.5s without narration in a 10s hard-cut block is ordinary
  # editing, and the rate gate — not the length — is what catches a rushed read.
  # 2026-08-04: floor moved from CLIP-2.0 to CLIP-2.2 with the engine swap to elevenlabs,
  # which has no rate control and ignores the timecode bracket. Must stay equal to
  # SPEECH_WINDOW in validate_motion_script.py.
  SPEECH_MIN="$(awk -v c="$CLIP" 'BEGIN{printf "%.3f", c-2.2}')"
  SPEECH_MAX="$(awk -v c="$CLIP" 'BEGIN{printf "%.3f", c-0.5}')"
  awk -v s="$SPEECH" -v lo="$SPEECH_MIN" -v hi="$SPEECH_MAX" 'BEGIN{exit (s < lo || s > hi) ? 0 : 1}' && {
    echo "ERROR: voice $((i+1)) ($voice) carries ${SPEECH}s of speech; required ${SPEECH_MIN}–${SPEECH_MAX}s. Fix it by CHANGING THE WORDS OF THAT ONE LINE and regenerating that take: too long — cut modifiers, keep the facts; too short — add one more FACT. Forbidden: appending a sentence or clause to the line, reusing a sentence from another block, atempo, trimming speech, or touching any other block. Then re-run validate_motion_script.py (it rewrites script.lock) before assembling again." >&2; exit 1; }
  awk -v d="$D" -v c="$CLIP" 'BEGIN{exit (d < c-0.5) ? 0 : 1}' && {
    echo "ERROR: clip $((i+1)) ($clip) is only ${D}s (<${CLIP}s) — REGENERATE the block; a held still frame is not a scene." >&2; exit 1; }
  # Freeze probes: head (first ~1.5s) and tail (last ~2s). Warnings — regenerate per rule 21.
  FRZH="$(ffmpeg -v info -t 1.5 -i "$clip" -vf "freezedetect=n=-60dB:d=1.0" -an -f null - 2>&1 | grep -c freeze_start || true)"
  [[ "$FRZH" != "0" ]] && echo "WARN: clip $((i+1)) ($clip) opens on ~static frames — regenerate this block (rule 21)." >&2
  FRZT="$(ffmpeg -v info -sseof -2 -i "$clip" -vf "freezedetect=n=-60dB:d=1.2" -an -f null - 2>&1 | grep -c freeze_start || true)"
  [[ "$FRZT" != "0" ]] && echo "WARN: clip $((i+1)) ($clip) ends on ~static frames (frozen tail) — consider regenerating." >&2
  # LEVEL-MATCH THE VOICE INPUT before it enters the mix. A fresh TTS take lands near
  # -31 dB mean while dialogue audio lifted out of a generated clip lands near -21 dB;
  # mixing both at 1.0 gives the dev 2026-07-29 complaint "narrator blocks are quiet,
  # character blocks are loud". One single-pass loudnorm per voice input removes the
  # spread mechanically, before any bed or SFX is placed under it.
  VN="$TMP/v_$(printf '%03d' "$i").wav"
  PREMEAN="$(ffmpeg -hide_banner -i "$voice" -af volumedetect -f null - 2>&1 | grep -Eo 'mean_volume: *-?[0-9.]+' | grep -Eo '\-?[0-9.]+' | head -1 || true)"
  if ffmpeg -y -loglevel error -i "$voice" -af "loudnorm=I=-19:TP=-1.5:LRA=11" -ar 48000 -ac 2 "$VN" 2>/dev/null; then
    POSTMEAN="$(ffmpeg -hide_banner -i "$VN" -af volumedetect -f null - 2>&1 | grep -Eo 'mean_volume: *-?[0-9.]+' | grep -Eo '\-?[0-9.]+' | head -1 || true)"
    printf '  block %02d: voice level %s dB -> %s dB (matched)\n' "$((i+1))" "${PREMEAN:-?}" "${POSTMEAN:-?}" >&2
    voice="$VN"
  else
    echo "WARN: could not level-match $voice — mixing it as-is; block loudness may differ from its neighbours." >&2
  fi
  # Center the SPEECH in the fixed window: put speech start at (CLIP - speech)/2,
  # compensating for the file's own leading silence. NO atempo.
  # SIMPLIFIED 2026-08-01, together with the window move. The protected-region trick
  # (centre [SS, SE+0.30] instead of [SS,SE]) existed only because the ceiling of CLIP-0.4
  # left the tail 0.2s from the cut, and real audio runs up to ~0.25s past SE because
  # silencedetect needs 0.25s before it calls anything silence. With the ceiling at CLIP-0.8
  # plain centring already leaves 0.4s of tail, so the guard bought nothing and only made the
  # arithmetic harder to reason about. When the take's own leading silence exceeds the offset
  # we still TRIM that much file-edge silence rather than clamping the delay to zero and
  # letting the speech run past the -t CLIP cut. Silence only, never speech, never tempo.
  # HEAD_GUARD — this is the one that actually ate words, and it ate them at the FRONT.
  # silencedetect declares speech only once the level is clearly up, so its speech start
  # lands LATE: measured 2026-08-01 on a real take, the detector said 1.538s while the
  # first word began at 1.120s — 418ms of the word sat inside what we called silence.
  # The trim can never exceed the detected start, but that is not enough, because the
  # detected start is already inside the word. Never cut closer than this to it.
  HEAD_GUARD=0.5
  read -r PAD_MS TRIM_S <<< "$(awk -v ss="$SS" -v sp="$SPEECH" -v c="$CLIP" -v hg="$HEAD_GUARD" 'BEGIN{
    t0=(c-sp)/2; if(t0<0)t0=0;          # centre the speech
    pad=t0-ss; if(pad<0)pad=0;
    trim=ss-t0; if(trim<0)trim=0;
    lim=ss-hg; if(lim<0)lim=0;          # keep hg seconds of real audio ahead of the cut
    if(trim>lim)trim=lim;
    printf "%d %.3f", pad*1000, trim }')"
  awk -v d="$TRIM_S" 'BEGIN{exit (d>0.001)?0:1}' && \
    echo "  block $((i+1)): trimming ${TRIM_S}s of the take's own leading silence so the speech fits the window" >&2
  out="$TMP/b_$(printf '%03d' "$i").mp4"
  # Keep the clip's own diegetic SFX under the voice (whooshes, sparkles, paper).
  # The gain is MEASURED against this block's own voice, not taken as a fixed fraction
  # of a level nobody looked at — see sfx_gain_db. Clips without an audio stream or
  # with --sfx-vol 0 use voice-only. Never substitute the default gain for mute.
  HASAUD="$(ffprobe -v error -select_streams a:0 -show_entries stream=codec_type -of csv=p=0 "$clip" | head -1)"
  if [[ "$HASAUD" == "audio" && "$SFXVOL" != "0.000" ]]; then
    SFXG="$(sfx_gain_db "$voice" "$clip" "$SFXVOL")"
    printf '  block %02d: clip SFX %s dB under the mix\n' "$((i+1))" "$SFXG" >&2
    FC="[0:v]scale=${W}:${H}:force_original_aspect_ratio=decrease,pad=${W}:${H}:(ow-iw)/2:(oh-ih)/2:black,${STEPPRE}fps=${FPS},format=yuv420p,setsar=1,tpad=stop_mode=clone:stop_duration=${CLIP}[v];[1:a]atrim=start=${TRIM_S},asetpts=PTS-STARTPTS,adelay=${PAD_MS}:all=1,apad[vo];[0:a]volume=${SFXG}dB,apad[sfx];[sfx][vo]amix=inputs=2:duration=first:normalize=0[a]"
  else
    if [[ "$HASAUD" == "audio" ]]; then
      printf '  block %02d: clip SFX muted (excluded from mix)\n' "$((i+1))" >&2
    else
      echo "WARN: clip $((i+1)) ($clip) has NO audio stream — block goes in voice-only, its background sound is lost. Re-download or regenerate the block." >&2
    fi
    FC="[0:v]scale=${W}:${H}:force_original_aspect_ratio=decrease,pad=${W}:${H}:(ow-iw)/2:(oh-ih)/2:black,${STEPPRE}fps=${FPS},format=yuv420p,setsar=1,tpad=stop_mode=clone:stop_duration=${CLIP}[v];[1:a]atrim=start=${TRIM_S},asetpts=PTS-STARTPTS,adelay=${PAD_MS}:all=1,apad[a]"
  fi
  ffmpeg -y -loglevel error -i "$clip" -i "$voice" \
    -filter_complex "$FC" \
    -map "[v]" -map "[a]" -t "$CLIP" -c:v libx264 -preset veryfast -crf 20 -c:a aac -b:a 192k "$out"
  echo "file '$out'" >> "$LIST"
  vout="$TMP/vo_$(printf '%03d' "$i").wav"
  ffmpeg -y -loglevel error -i "$voice" \
    -af "atrim=start=${TRIM_S},asetpts=PTS-STARTPTS,adelay=${PAD_MS}:all=1,apad" \
    -t "$CLIP" -ar 48000 -ac 2 "$vout"
  echo "file '$vout'" >> "$VOLIST"
  # Verify that the narration actually reached the mixed block. SFX 18 dB below the
  # voice changes the mean only slightly; a mix more than 3 dB below the voice-only twin
  # indicates broken wiring and must not be delivered.
  MIXMEAN="$(ffmpeg -hide_banner -i "$out" -vn -af volumedetect -f null - 2>&1 | grep -Eo 'mean_volume: *-?[0-9.]+' | grep -Eo '\-?[0-9.]+' | head -1 || true)"
  VOMEAN="$(ffmpeg -hide_banner -i "$vout" -af volumedetect -f null - 2>&1 | grep -Eo 'mean_volume: *-?[0-9.]+' | grep -Eo '\-?[0-9.]+' | head -1 || true)"
  if [[ -n "$MIXMEAN" && -n "$VOMEAN" ]] && awk -v m="$MIXMEAN" -v v="$VOMEAN" 'BEGIN{exit (m < v-3) ? 0 : 1}'; then
    echo "ERROR: block $((i+1)) mixes to ${MIXMEAN} dB but its voice alone is ${VOMEAN} dB — the narration did not reach the mix. Do NOT deliver." >&2
    exit 1
  fi
  # Where the speech actually lands inside the block: padded forward, or reached by
  # trimming file-edge silence. Both branches put it at t0 = (CLIP - speech)/2.
  BLOCK_START="$(awk -v p="$PAD_MS" -v ss="$SS" -v tr="$TRIM_S" 'BEGIN{printf "%.3f", p/1000 + ss - tr}')"
  printf '  block %02d: clip %.2fs, file %.2fs, speech %.2fs (%.2f..%.2f) -> speech starts at %.2fs\n' \
    "$((i+1))" "$D" "$A" "$SPEECH" "$SS" "$SE" "$BLOCK_START" >&2
  # Absolute position of this block's SPEECH in the finished file, plus the
  # take's own leading silence. Captions are timed from the CLEAN voice files
  # (no music/SFX to confuse the STT) and shifted by these two numbers:
  #   t_final = speech_abs_s + (t_word_in_voice_file - lead_silence_s)
  # NOTE: word timestamps come from the UNTRIMMED clean take, so lead_silence_s stays the
  # take's own ss and speech_abs_s must be the POST-trim position — otherwise every caption
  # in a trimmed block drifts late by exactly TRIM_S.
  SPEECH_ABS="$(awk -v i="$i" -v c="$CLIP" -v b="$BLOCK_START" 'BEGIN{printf "%.3f", i*c + b}')"
  PBJSON[i]="$(printf '{"n":%d,"clip":"%s","voice":"%s","clip_s":%.2f,"speech_s":%.2f,"speech_abs_s":%.3f,"lead_silence_s":%.3f,"internal_pauses":%d,"freeze_head":%s,"freeze_tail":%s}' \
    "$((i+1))" "$(basename "$clip")" "$(basename "$voice")" "$D" "$SPEECH" "$SPEECH_ABS" "$SS" "${IPN:-0}" \
    "$([[ "${FRZH:-0}" != "0" ]] && echo true || echo false)" "$([[ "${FRZT:-0}" != "0" ]] && echo true || echo false)")"
done

VOTRACK="$TMP/joined.mp4"
echo "[2/3] concat -> single track" >&2
ffmpeg -y -loglevel error -f concat -safe 0 -i "$LIST" -c:v libx264 -preset veryfast -crf 20 -c:a aac -movflags +faststart "$VOTRACK"

# SONG MODE: lay the one continuous song (1.0) over the whole cut BEFORE the
# per-window audio assert — the assert then guarantees the song is audible in
# every window (and catches a silent/broken song file).
if [[ -n "$SONG" ]]; then
  SM="$TMP/songmix.mp4"
  ffmpeg -y -loglevel error -i "$VOTRACK" -i "$SONG" \
    -filter_complex "[1:a]aformat=sample_rates=44100:channel_layouts=stereo,apad[s];[0:a][s]amix=inputs=2:duration=first:normalize=0[a]" \
    -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 192k "$SM"
  VOTRACK="$SM"
  echo "  song laid over the cut at 1.0 (clip SFX ${SFXVOL})" >&2
fi

# NARRATION-PER-WINDOW assert: every 10s window must contain voice-level audio. A window
# whose center [+2..+8] is quiet for 6s straight has NO narration — the exact
# "silent second half" failure of hand-rolled assemblies. Checked BEFORE the
# music bed can mask it. Silent cuts skip this: diegetic SFX may legitimately pause.
if [[ "$CLIPONLY" == "1" ]]; then
  echo "  clips-only: skip narration-window assert" >&2
elif [[ -z "$SONG" ]]; then
  ASSERT_SRC="$TMP/voiceonly.wav"
  ffmpeg -y -loglevel error -f concat -safe 0 -i "$VOLIST" -ar 48000 -ac 2 "$ASSERT_SRC"
  VOD="$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$ASSERT_SRC")"
  awk -v d="${VOD:-0}" -v n="$pairs" -v c="$CLIP" 'BEGIN{exit (d > n*c-0.5) ? 1 : 0}' && {
    echo "ERROR: the voice-only track is ${VOD}s, not ${pairs}x${CLIP}s — the narration assert cannot be trusted. Do NOT deliver." >&2; exit 1; }
  QUIET="$(ffmpeg -i "$ASSERT_SRC" -af "silencedetect=noise=-18dB:d=6" -f null - 2>&1 | grep -Eo 'silence_(start|end): *[0-9.]+' || true)"
  EMPTY="$(awk -v C="$CLIP" -v P="$pairs" '
    /silence_start/ { s[++k]=$NF+0; next }
    /silence_end/   { e[k]=$NF+0 }
    END {
      for (i=0;i<P;i++) { ws=i*C+2; we=i*C+8;
        for (j=1;j<=k;j++) { ee=(e[j]>0)?e[j]:1e9;
          if (s[j]<=ws && ee>=we) { printf "%s%d", (out++?",":""), i+1; break } } } }' <<< "$QUIET")"
  if [[ -n "$EMPTY" ]]; then
    echo "ERROR: blocks [$EMPTY] have NO narration in their windows — the take itself is silent or was trimmed away. Fix the inputs and re-run; do NOT deliver." >&2
    exit 1
  fi
  echo "  narration present in all ${pairs} windows" >&2
else
  ASSERT_SRC="$VOTRACK"
  QUIET="$(ffmpeg -i "$ASSERT_SRC" -af "silencedetect=noise=-18dB:d=6" -f null - 2>&1 | grep -Eo 'silence_(start|end): *[0-9.]+' || true)"
  EMPTY="$(awk -v C="$CLIP" -v P="$pairs" '
    /silence_start/ { s[++k]=$NF+0; next }
    /silence_end/   { e[k]=$NF+0 }
    END {
      for (i=0;i<P;i++) { ws=i*C+2; we=i*C+8;
        for (j=1;j<=k;j++) { ee=(e[j]>0)?e[j]:1e9;
          if (s[j]<=ws && ee>=we) { printf "%s%d", (out++?",":""), i+1; break } } } }' <<< "$QUIET")"
  if [[ -n "$EMPTY" ]]; then
    echo "ERROR: blocks [$EMPTY] have NO song in their windows — the take itself is silent or was trimmed away. Fix the inputs and re-run; do NOT deliver." >&2
    exit 1
  fi
  echo "  song present in all ${pairs} windows" >&2
fi

echo "[3/3] finalize -> $FINAL_OUT" >&2
# Two-pass LINEAR loudnorm: one constant gain for the whole file, so the
# voice/SFX/music ratios set above are PRESERVED (single-pass dynamic loudnorm
# pumps quiet SFX-only stretches up toward the voice = mush).
ln2_args() { # $1 = input file -> prints measured loudnorm args
  ffmpeg -hide_banner -i "$1" -af "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json" -f null - 2>&1 \
  | awk '/"input_i"/{i=$3}/"input_tp"/{t=$3}/"input_lra"/{l=$3}/"input_thresh"/{h=$3}/"target_offset"/{o=$3}
         {gsub(/[",]/,"",i);gsub(/[",]/,"",t);gsub(/[",]/,"",l);gsub(/[",]/,"",h);gsub(/[",]/,"",o)}
         END{printf "measured_I=%s:measured_TP=%s:measured_LRA=%s:measured_thresh=%s:offset=%s", i,t,l,h,o}'
}
if [[ -n "$MUSIC" ]]; then
  MIXED="$TMP/mixed.mp4"
  BEDG="$(bed_gain_db "$VOTRACK" "$MUSIC" "$MVOL")"
  if [[ "$CLIPONLY" == "1" ]]; then
    echo "  music bed: clips-only underlay ${BEDG} dB (no voice duck)" >&2
    ffmpeg -y -loglevel error -i "$VOTRACK" -stream_loop -1 -i "$MUSIC" \
      -filter_complex "[0:a]aformat=sample_rates=44100:channel_layouts=stereo[vo];[1:a]aformat=sample_rates=44100:channel_layouts=stereo,volume=${BEDG}dB[m];[vo][m]amix=inputs=2:duration=first:normalize=0[a]" \
      -map 0:v -map "[a]" -shortest -c:v copy -c:a aac -b:a 192k "$MIXED"
  else
    # DUCKING: the bed is sidechain-compressed by the VOICE — it dips hard while
    # narration plays and breathes back up in the gaps. The voice always wins.
    echo "  music bed: measured against the speech -> ${BEDG} dB (then ducked under the voice)" >&2
    ffmpeg -y -loglevel error -i "$VOTRACK" -stream_loop -1 -i "$MUSIC" \
      -filter_complex "[0:a]aformat=sample_rates=44100:channel_layouts=stereo,asplit=2[vo][key];[1:a]aformat=sample_rates=44100:channel_layouts=stereo,volume=${BEDG}dB[m];[m][key]sidechaincompress=threshold=0.02:ratio=8:attack=10:release=300[duck];[vo][duck]amix=inputs=2:duration=first:normalize=0[a]" \
      -map 0:v -map "[a]" -shortest -c:v copy -c:a aac -b:a 192k "$MIXED"
  fi
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

# Assert the fixed-length guarantee (GATE 6): |actual - N*CLIP| <= 1s.
TOT="$(awk -v n="$pairs" -v c="$CLIP" 'BEGIN{printf "%g", n*c}')"
FDUR="$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUT")"
awk -v d="$FDUR" -v e="$TOT" 'BEGIN{x=d-e; if(x<0)x=-x; exit (x<=1)?0:1}' || {
  echo "ERROR: final duration ${FDUR}s != expected ${TOT}s (±1s) — do NOT deliver; investigate the inputs." >&2; exit 1; }

# Integrity: the final must have an audio stream spanning the video, and must FULLY
# DECODE with zero errors (catches corrupted/truncated streams that stream-copy hides).
ADUR="$(ffprobe -v error -select_streams a:0 -show_entries stream=duration -of csv=p=0 "$OUT" | head -1)"
[[ -z "$ADUR" || "$ADUR" == "N/A" ]] && { echo "ERROR: final has no readable audio stream — do NOT deliver." >&2; exit 1; }
awk -v a="$ADUR" -v d="$FDUR" 'BEGIN{x=a-d; if(x<0)x=-x; exit (x<=1.5)?0:1}' || {
  echo "ERROR: audio stream ${ADUR}s vs video ${FDUR}s — mismatched/truncated audio; do NOT deliver." >&2; exit 1; }
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
POSTER="${FINAL_OUT%.mp4}_poster.jpg"
POSTER_CANDIDATE="$TMP/final-poster.jpg"
ffmpeg -y -loglevel error -ss 1 -i "$OUT" -frames:v 1 -q:v 2 "$POSTER_CANDIDATE" || true
if [[ ! -s "$POSTER_CANDIDATE" ]]; then
  ffmpeg -y -loglevel error -i "$OUT" -frames:v 1 -q:v 2 "$POSTER_CANDIDATE" || true
fi

# --- assembly sidecar: machine-readable proof the final went through this
# script, gates included. Optional delivery metadata reads block_count
# and per-block metrics from here; a final video without one was hand-assembled.
SIDE="${FINAL_OUT}.assembly.json"
SIDE_CANDIDATE="$TMP/assembly.json"
{
  printf '{"script":"assemble_final.sh","manifest_version":2,"assembly_attempts":%d,"out":"%s","blocks":%d,"clip_seconds":%s,"total_s":%s,"actual_s":%s,"width":%s,"height":%s,"fps":"%s","music":%s,"music_vol":%s,"sfx_vol":%s,"song":%s,"clips_only":%s,"gate":"speech in [window-0.6,window-0.2], clip>=window-0.5, speech-centered, narration/song in every window (silencedetect -18dB/6s; skipped on --clips-only), song length +/-3s of NxCLIP, no atempo, 2-pass linear loudnorm -16, duration +/-1s, full decode","per_block":[' \
    "$ASSEMBLY_ATTEMPT" "$(basename "$FINAL_OUT")" "$pairs" "$CLIP" "$TOT" "$FDUR" "$W" "$H" "$FPS" \
    "$([[ -n "$MUSIC" ]] && echo true || echo false)" "$MVOL" "$SFXVOL" \
    "$([[ -n "$SONG" ]] && echo true || echo false)" \
    "$([[ "$CLIPONLY" == "1" ]] && echo true || echo false)"
  for ((i=0;i<pairs;i++)); do printf '%s%s' "${PBJSON[i]}" "$([[ $i -lt $((pairs-1)) ]] && echo ,)"; done
  printf '],"ts":"%s"}\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
} > "$SIDE_CANDIDATE"
mv "$OUT" "$FINAL_OUT"
if [[ -s "$POSTER_CANDIDATE" ]]; then
  mv "$POSTER_CANDIDATE" "$POSTER"
  echo "POSTER: $POSTER" >&2
else
  echo "WARN: poster extraction failed (no $POSTER)" >&2
fi
mv "$SIDE_CANDIDATE" "$SIDE"
echo "ASSEMBLY-SIDECAR: $SIDE" >&2
echo "DONE: $FINAL_OUT  (ONE file, ${pairs} blocks x ${CLIP}s = ${TOT}s, actual ${FDUR}s; decode-validated)" >&2
