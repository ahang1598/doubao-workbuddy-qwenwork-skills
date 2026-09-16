# Captions — layer choice (`Both` default / `Subtitles` / `Hook`), burned in one pass

Captions are **ON by default**; only an explicit "no captions" brief skips the burn (then deliver
`output/final.mp4`). The `caption_mode` from step 1 picks the layers:

- **Both** (default) — top hook plate over the hook + bottom captions for the rest.
- **Subtitles** — bottom captions only.
- **Hook** — the top hook plate only.

Timing comes from a **word-level Whisper transcript of the FINAL audio**, so captions lip-sync to
playback and silence carries no caption — never planned-beat timings, never an even spread. If the
transcript finds no speech, burn NOTHING and deliver `output/final.mp4`.

Uses the bundle scripts `transcribe_words.py`, `group_captions.py`, `make_captions.py` from this
skill's `scripts/`. They run in the **local shell** — there is no cloud sandbox and no
`sandbox_exec` tool. `$SKILL` below is this skill's directory. Prefix with
`curl -sL -o output/final.mp4 '<结果URL>'` when the composite ran earlier, and finish with
`upload_file` + `asset_create` for `final_captioned.mp4`.

Local prerequisites: `ffmpeg`, `python3`, `python3 -m pip install faster-whisper`, and a font with
CJK glyphs (`PingFang SC` on macOS, or `Noto Sans SC`). Missing any of them means the burn cannot
run — tell the user and deliver the clean cut; never claim captions that were not burned.

## Bottom captions (`Subtitles` or `Both`)

Grouped from the word-level transcript, with the TEXT taken from the authored script — the same
path the sibling UGC flows use.

```bash
# 1. word-level timings from the FINISHED video (word timestamps are mandatory; phrase-level drifts)
#    --lang zh for Chinese speech (the default), --lang en for an English monologue
python3 "$SKILL/scripts/transcribe_words.py" output/final.mp4 -o output/words.json --lang zh

# 2. group + render, bottom safe-zone (~0.15·H), sentence case at size 50.
#    --script is REQUIRED: the caption TEXT comes from the authored monologue, whisper is
#    only the clock. Without it a mis-heard brand burns onto the video.
#    --font must name a locally installed family; Chinese needs CJK glyphs
python3 "$SKILL/scripts/group_captions.py" output/words.json -o output/segments.json \
  --video output/final.mp4 --script output/script.txt
python3 "$SKILL/scripts/make_captions.py" output/segments.json -o output/captions.ass --font "PingFang SC" --size 50 --no-caps
python3 - <<'PY'
H = 1920; MARGIN_V = round(0.15 * H)
p = "output/captions.ass"; out = []
for ln in open(p):
    ln = ln.rstrip("\n")
    if ln.startswith("Style: Cap,"):
        parts = ln.split(","); parts[-5] = "2"; parts[-2] = str(MARGIN_V); ln = ",".join(parts)  # bottom
    out.append(ln)
open(p, "w").write("\n".join(out) + "\n")
PY
```

**The QA gate is a hard stop.** `group_captions.py` exits `3` when a caption word is not in the
script, so a chained `&&` burn never ships mis-heard text. When it blocks: fix the script's display
forms (below) and re-run — `--allow-qa-misses` exists but is for the case where the flagged words are
genuinely correct.

**Display forms are the author's job.** The alignment repairs a mis-heard span only if the script says
what should appear on screen. Write every brand exactly as it is spelled and every number as digits.
A number written as a word, or a brand written the way it sounds, breaks the alignment and renders
wrong even when the alignment succeeds.

## Top hook plate (`Hook` or `Both`)

The plate carries the authored hook line from `output/hook.txt` (top ~0.10·H) and
holds over the hook only — it ends at the start of the first whole body word, never a pause guess and
never a fixed 2s.

```bash
python3 - <<'PY'
import json, re, difflib
norm = lambda t: re.sub(r"[^a-z0-9]", "", t.lower())
words = json.load(open("output/words.json"))                 # [[start,end,word],...]
hook  = open("output/hook.txt", encoding="utf-8").read().split()
a, b = [norm(w[2]) for w in words], [norm(t) for t in hook]
i_end = 0
for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes():
    if tag in ("equal", "replace"):
        i_end = max(i_end, i2)
first_body = i_end if 0 < i_end < len(words) else min(len(hook), len(words) - 1)
plate_end  = round(words[first_body][0], 2)
hook_start = round(words[0][0], 2)
json.dump({"video": "output/final.mp4",
           "segments": [{"start": hook_start, "end": plate_end,
                         "text": open("output/hook.txt").read().strip()}]},
          open("output/hook_seg.json", "w"))
json.dump([w for w in words if w[0] >= plate_end - 1e-6], open("output/body_words.json", "w"))
print(f"plate {hook_start}-{plate_end}s; body starts at {plate_end}s")
PY

python3 "$SKILL/scripts/make_captions.py" output/hook_seg.json -o output/hook.ass --font "PingFang SC" --no-caps
python3 - <<'PY'
H = 1920; TOP = round(0.10 * H)
p = "output/hook.ass"; out = []
for ln in open(p):
    ln = ln.rstrip("\n")
    if ln.startswith("Style: Cap,"):
        parts = ln.split(","); parts[-5] = "8"; parts[-2] = str(TOP); ln = ",".join(parts)  # top-center
    out.append(ln)
open(p, "w").write("\n".join(out) + "\n")
PY
```

With **Both**, group the BODY words (`output/body_words.json`) instead of `words.json` so no caption
sits under the plate. Plate text is words only — libass renders no colour emoji, so drop any emoji and
keep the words.

## Burn — one pass, audio copied

```bash
# Both
ffmpeg -y -i output/final.mp4 -vf "ass=output/captions.ass,ass=output/hook.ass" -c:a copy output/final_captioned.mp4
# Subtitles
ffmpeg -y -i output/final.mp4 -vf "ass=output/captions.ass" -c:a copy output/final_captioned.mp4
# Hook
ffmpeg -y -i output/final.mp4 -vf "ass=output/hook.ass" -c:a copy output/final_captioned.mp4
```

The Fontname is resolved by fontconfig at burn time, so it must be installed on this machine. Audio
is copied, never re-encoded. Grouping defaults live in `group_captions.py` (display width ≤11 — one
CJK glyph counts as two, join gap
<0.35s, 0.15s tail = pause-blanking, 0.20s min hold, de-overlap trim). The bottom ~15% band is the
caption safe-zone the composite keeps its insets out of. `output/final_captioned.mp4` is the
deliverable; keep `output/final.mp4` alongside.
