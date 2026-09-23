#!/usr/bin/env bash
# speech_metrics.sh — measure what actually matters about a TTS take, so a
# narration line can be gated WITHOUT guessing from the file length.
#
# A TTS file's duration lies: providers pad the head/tail with silence, so a
# 10.1s file can hold 9.2s of speech (and vice versa). Downstream assemblers
# centre the SPEECH inside its window, so the speech length — not the file
# length — is the number to check.
#
# Prints one line of KEY=VALUE pairs (and JSON with --json):
#   duration      file length (s)
#   speech_start  where speech begins (leading silence trimmed)
#   speech_end    where speech ends (trailing silence trimmed)
#   speech        speech_end - speech_start  <-- gate on this
#   pauses        number of internal silences >= --pause (default 0.8s)
#   longest_pause longest internal silence (s)
#
# With --text or --words it also reports the DELIVERY RATE, which is how you catch a
# take that fits the window only because the voice raced through it:
#   words         spoken words counted in the line
#   wps           words / speech seconds
#   rate          ok | RUSHED (wps > --max-wps, default 2.9) | SLOW (wps < 2.1)
# RE-SET 2026-08-04 for the elevenlabs engine, which reads far slower than seed_audio did:
# ten takes measured 2.37 2.38 2.41 2.43 2.48 2.50 2.56 2.65 and, on an overlong 28-word
# line, 2.40 2.65 — so the natural band is roughly 2.4-2.6 and the old 3.8 ceiling could
# never fire at all. 2.9 sits clear of the natural pace and still catches a crammed read.
# History: the default was 3.2 until 2026-08-01 and 3.8 until today, both calibrated on
# seed_audio, whose six delivered takes measured 3.22 3.24 3.26 3.34 3.37 3.47 wps.
# If the engine is switched back, the thresholds move back with it — they are a property
# of the engine, not of the writing.
# A RUSHED take is a REWRITE (fewer words), never something to ship: it fits the
# clock and still sounds like an auctioneer.
#
# Usage:
#   scripts/speech_metrics.sh voice01.wav [--text "the line"] [--words N]
#                             [--max-wps 3.2] [--pause 0.8] [--noise -45] [--json]
#
# Requires: ffmpeg, ffprobe, awk.
set -euo pipefail

FILE=""; PAUSE="0.8"; NOISE="-45"; JSON=0; TEXT=""; WORDS=""; MAXWPS="2.9"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --pause) PAUSE="$2"; shift 2 ;;
    --noise) NOISE="$2"; shift 2 ;;
    --text)  TEXT="$2"; shift 2 ;;
    --words) WORDS="$2"; shift 2 ;;
    --max-wps) MAXWPS="$2"; shift 2 ;;
    --json)  JSON=1; shift ;;
    -h|--help) grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) FILE="$1"; shift ;;
  esac
done
[[ -n "$FILE" && -f "$FILE" ]] || { echo "ERROR: pass an audio file" >&2; exit 1; }
for b in ffmpeg ffprobe awk; do command -v "$b" >/dev/null 2>&1 || { echo "ERROR: '$b' not found" >&2; exit 1; }; done

DUR="$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$FILE")"
EVENTS="$(ffmpeg -i "$FILE" -af "silencedetect=noise=${NOISE}dB:d=0.25" -f null - 2>&1 \
          | grep -Eo 'silence_(start|end): *-?[0-9.]+' || true)"

# Speech bounds: ignore a leading silence that starts at ~0, and close the tail
# silence that EOF left open.
read -r SS SE <<< "$(awk -v A="$DUR" '
  /silence_start/ { s=$NF+0; if(first==""){first=s}; last=s; open=1; next }
  /silence_end/   { e=$NF+0; if(first!="" && first<0.1 && ssdone==""){ss=e; ssdone=1};
                    e_last=e; s_before=last; open=0 }
  END {
    if (open==1)                       se=last;
    else if (e_last>0 && A-e_last<0.2) se=s_before;
    else                               se=A;
    printf "%.3f %.3f", ss+0, se+0 }' <<< "$EVENTS")"
[[ -z "${SS:-}" ]] && SS=0; [[ -z "${SE:-}" || "$SE" == "0.000" ]] && SE="$DUR"
SPEECH="$(awk -v a="$SS" -v b="$SE" 'BEGIN{d=b-a; if(d<0)d=0; printf "%.3f", d}')"
# Degenerate detection (all-silence or no events) -> fall back to the whole file.
awk -v s="$SPEECH" 'BEGIN{exit (s<0.3)?0:1}' && { SS=0; SE="$DUR"; SPEECH="$DUR"; }

# Internal pauses strictly INSIDE the speech.
read -r PN PMAX <<< "$(awk -v lo="$SS" -v hi="$SE" -v thr="$PAUSE" '
  /silence_start/ { s=$NF+0; open=1; next }
  /silence_end/   { e=$NF+0; if(open==1 && s>lo+0.1 && e<hi-0.1 && e-s>=thr){n++; if(e-s>mx)mx=e-s}; open=0 }
  END{ printf "%d %.2f", n+0, mx+0 }' <<< "$EVENTS")"

# Delivery rate — only when the caller told us how many words were spoken. Bracketed
# stage directions ([scoffs]) are performed, not read, so they do not count as words.
#
# WorkRally port: Chinese has no word separators, so `tr -cs [:alnum:]` collapses a whole
# line to nothing and the rate gate silently stops working. Count CJK ideographs
# individually and switch the thresholds to characters/second, because Mandarin TTS reads
# ~4.0-4.6 chars/s where English reads ~2.4 words/s. The CJK band is DERIVED from the
# speech window, not measured on the provider — re-measure once real takes exist.
CJK=0
if [[ -n "$TEXT" ]] && command -v python3 >/dev/null 2>&1; then
  CJK="$(printf '%s' "$TEXT" | python3 -c '
import re, sys
text = sys.stdin.read()
cjk = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
letters = [c for c in text if c.isalpha()]
print(1 if letters and sum(1 for c in letters if cjk.match(c)) * 2 >= len(letters) else 0)
' 2>/dev/null || echo 0)"
fi
if [[ -z "$WORDS" && -n "$TEXT" ]]; then
  if [[ "$CJK" == "1" ]]; then
    WORDS="$(printf '%s' "$TEXT" | python3 -c '
import re, sys
text = re.sub(r"\[[^][]*\]|\([^()]*\)", "", sys.stdin.read())
cjk = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
units = 0
for token in re.findall(r"[^\W_]+", text, re.UNICODE):
    units += len(token) if cjk.search(token) else 1
print(units)
')"
  else
    WORDS="$(printf '%s' "$TEXT" | sed -e 's/\[[^][]*\]//g' -e 's/([^()]*)//g' \
              | tr -cs "[:alnum:]'-" ' ' | awk '{print NF}')"
  fi
fi
# The caller may still override --max-wps; only the untouched default moves for CJK.
SLOWWPS="2.1"
if [[ "$CJK" == "1" && "$MAXWPS" == "2.9" ]]; then MAXWPS="5.5"; SLOWWPS="3.4"; fi
RATE=""; WPS=""
if [[ -n "$WORDS" ]]; then
  read -r WPS RATE <<< "$(awk -v w="$WORDS" -v s="$SPEECH" -v mx="$MAXWPS" -v lo="$SLOWWPS" 'BEGIN{
    if (s<=0) { print "0.00 unknown"; exit }
    r=w/s; printf "%.2f %s", r, (r>mx ? "RUSHED" : (r<lo ? "SLOW" : "ok")) }')"
fi

if [[ "$JSON" == "1" ]]; then
  printf '{"file":"%s","duration":%.3f,"speech_start":%.3f,"speech_end":%.3f,"speech":%.3f,"pauses":%d,"longest_pause":%.2f' \
    "$(basename "$FILE")" "$DUR" "$SS" "$SE" "$SPEECH" "${PN:-0}" "${PMAX:-0}"
  [[ -n "$WORDS" ]] && printf ',"words":%d,"wps":%s,"rate":"%s"' "$WORDS" "$WPS" "$RATE"
  printf '}\n'
else
  printf 'duration=%.3f speech_start=%.3f speech_end=%.3f speech=%.3f pauses=%d longest_pause=%.2f' \
    "$DUR" "$SS" "$SE" "$SPEECH" "${PN:-0}" "${PMAX:-0}"
  [[ -n "$WORDS" ]] && printf ' words=%d wps=%s rate=%s' "$WORDS" "$WPS" "$RATE"
  printf '\n'
fi
if [[ "$RATE" == "RUSHED" ]]; then
  echo "WARN: ${WPS} words/sec is auctioneer pace — REWRITE the line shorter (target <= ${MAXWPS}) and regenerate. Do NOT ship it and do NOT slow the audio down." >&2
fi
