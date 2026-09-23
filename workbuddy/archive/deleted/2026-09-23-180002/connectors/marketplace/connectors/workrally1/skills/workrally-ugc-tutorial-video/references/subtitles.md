# On-video text — optional hook plate (top) + word-by-word bottom captions

On-video text is **OFF by default** in this workflow: generation never bakes text, and anything
here is strictly a post-render burn the user opted into (`Subtitles` / `Hook` / `Both`). Two
layers, handed off at a **word boundary**: the hook line as a top plate for exactly the hook
segment, then short bottom captions (1-2 latin words, or ~5 Chinese glyphs) that blank out
in pauses. White/black outline, no animation, nothing duplicated. Deliverable:
`output/final_captioned.mp4`, with `output/final.mp4` kept alongside.

Uses three bundle scripts (`transcribe_words.py`, `group_captions.py`, `make_captions.py`) that
ship inside this skill's `scripts/`. They run in the **local shell** — there is no cloud sandbox
and no `sandbox_exec` tool. `$SKILL` below is this skill's directory; `output/` is a local working
folder. Prefix with `curl -sL -o output/final.mp4 '<结果URL>'` to pull a generated clip down, and
finish with `upload_file` + `asset_create` when the captioned cut has to land in the media library.

Local prerequisites: `ffmpeg`, `python3`, `python3 -m pip install faster-whisper`, and a font with
CJK glyphs for Chinese captions (`PingFang SC` on macOS, or `Noto Sans SC`). Missing any of them
means the burn cannot run — say so and deliver the clean cut instead of claiming captions shipped.

Caption TEXT comes from the authored monologue (`output/script.txt`), so brand names are always
spelled as authored — whisper is only the clock. The QA check is a HARD STOP: `group_captions.py`
exits `3` when a caption word is not in the script, so a chained burn never ships mis-heard text
(`--allow-qa-misses` overrides, for when the flagged words are genuinely correct).

Write every brand in the script exactly as it is spelled and every number as digits. A number
written as a word, or a brand written the way it sounds, breaks the alignment and renders wrong. If the transcript finds no speech, burn NOTHING and deliver
`output/final.mp4` — never guess timing, never even-spread.

Save before running: the full monologue verbatim to `output/script.txt`, and (only for the hook
layer) the chosen ≤6-word headline to `output/hook.txt`.

## Subtitles only (the common case)

```bash
# 1. word-level timings — from the FINISHED video (word_timestamps are mandatory; phrase-level drifts)
#    --lang zh for Chinese speech (the default), --lang en for an English monologue
python3 "$SKILL/scripts/transcribe_words.py" output/final.mp4 -o output/words.json --lang zh

# 2. script-aligned grouping, size 52; re-anchor to BOTTOM (~0.15·H)
#    --font must name a locally installed family; Chinese needs CJK glyphs
python3 "$SKILL/scripts/group_captions.py" output/words.json -o output/segments.json \
  --video output/final.mp4 --script output/script.txt      # exits 3 if a caption word is not in the script
python3 "$SKILL/scripts/make_captions.py" output/segments.json -o output/captions.ass --font "PingFang SC" --size 52 --no-caps
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

# 3. burn — the Fontname is resolved by fontconfig, so it must be installed on this machine
ffmpeg -y -i output/final.mp4 -vf "ass=output/captions.ass" -c:a copy output/final_captioned.mp4
```

## Adding the hook plate (`Hook` or `Both`)

Split the words at the hook/body boundary first, then build the plate as a second layer:

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
plate_end  = round(words[first_body][0], 2)                  # start of the first WHOLE body word
hook_start = round(words[0][0], 2)
json.dump({"video": "output/final.mp4",
           "segments": [{"start": hook_start, "end": plate_end,
                         "text": open("output/hook.txt").read().strip()}]},
          open("output/hook_seg.json", "w"))
json.dump([w for w in words if w[0] >= plate_end - 1e-6], open("output/body_words.json", "w"))
print(f"plate {hook_start}-{plate_end}s; body starts at {plate_end}s")
PY

# plate — no --anim; re-anchor to TOP (~0.10·H)
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

With the plate in play, group the BODY words (`output/body_words.json`) instead of `words.json`,
drop any caption group that falls under the plate, and burn both layers:
`-vf "ass=output/hook.ass,ass=output/captions.ass"`. The plate's end is the start of the first
whole body word — never a pause guess, never a fixed 2s.

Hook-plate text is words only — libass renders no color emoji, so drop any emoji and keep the
words. Grouping defaults live in `group_captions.py` (display width ≤11 — one CJK glyph counts as
two, join gap <0.35s, 0.15s tail = the pause-blanking, 0.20s min hold, de-overlap trim). Chinese
chunks from whisper are split per glyph before alignment so the authored text lands on real
timings. The bottom ~15% band is the caption safe-zone.
