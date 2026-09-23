# On-video text — optional hook plate (top) + word-by-word bottom captions

On-video text is **OFF by default** in this workflow: generation never bakes text, and anything
here is strictly a post-render burn the user opted into (`Subtitles` / `Hook` / `Both`). Two
layers, handed off at a **word boundary**: the hook line as a top plate for exactly the hook
segment, then 1-2-word bottom captions that blank out in pauses. White fill / black outline, no
animation, nothing duplicated. Deliverable: `output/final_captioned.mp4`, with `output/final.mp4`
kept alongside.

WorkRally has **no subtitle-burn tool** — only subtitle *erasure* (`enable_erase_subtitles` on
`canvas_generate_video`). Burning happens on the **local shell** with `ffmpeg` plus the three
scripts shipped in this skill's `scripts/` directory (`transcribe_words.py`,
`group_captions.py`, `make_captions.py`). Run the commands below directly — there is no
`sandbox_exec`, no `$HF_WORKFLOWS`, and the working directory persists between calls, so no
single-call packing is needed. Prefix with `curl -sL -o output/final.mp4 <hosted url>` when the
final video only exists as a hosted URL; put `final_captioned.mp4` into the media library
afterwards with `upload_file` + `asset_create` only if the user asked for that.

`<skill>` below is this skill's install directory. Dependencies: `ffmpeg` on `PATH` and
`python3 -m pip install faster-whisper`. Either one missing → burn nothing, deliver the clean
master, and say so plainly.

**Chinese captions need a font with Chinese glyphs.** `make_captions.py` defaults to
`PingFang SC` (bundled with macOS); on Linux install `fonts-noto-cjk` and pass
`--font "Noto Sans SC"`. A Latin-only font (Montserrat / Metropolis) renders Chinese as
tofu boxes or drops it entirely. Verify with `fc-list :lang=zh` before burning.

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
python3 <skill>/scripts/transcribe_words.py output/final.mp4 -o output/words.json

# 2. script-aligned grouping (CJK-aware), 52px; re-anchor to BOTTOM (~0.15·H)
python3 <skill>/scripts/group_captions.py output/words.json -o output/segments.json \
  --video output/final.mp4 --script output/script.txt      # exits 3 if a caption word is not in the script
python3 <skill>/scripts/make_captions.py output/segments.json -o output/captions.ass --font "PingFang SC" --size 52
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

# 3. burn — local ffmpeg; the font name is resolved through fontconfig, so it must be installed
ffmpeg -y -i output/final.mp4 -vf "ass=output/captions.ass" -c:a copy output/final_captioned.mp4
```

## Adding the hook plate (`Hook` or `Both`)

Split the words at the hook/body boundary first, then build the plate as a second layer:

```bash
python3 - <<'PY'
import json, difflib, importlib.util
# reuse the shipped CJK-aware tokenizer so the split works for Chinese too
spec = importlib.util.spec_from_file_location("gc_mod", "<skill>/scripts/group_captions.py")
gc = importlib.util.module_from_spec(spec); spec.loader.exec_module(gc)
norm = gc._norm
words = json.load(open("output/words.json", encoding="utf-8"))   # [[start,end,word],...]
hook  = gc._tokenize(open("output/hook.txt", encoding="utf-8").read())
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
                         "text": open("output/hook.txt", encoding="utf-8").read().strip()}]},
          open("output/hook_seg.json", "w"), ensure_ascii=False)
json.dump([w for w in words if w[0] >= plate_end - 1e-6],
          open("output/body_words.json", "w"), ensure_ascii=False)
print(f"plate {hook_start}-{plate_end}s; body starts at {plate_end}s")
PY

# plate — no --anim; re-anchor to TOP (~0.10·H)
python3 <skill>/scripts/make_captions.py output/hook_seg.json -o output/hook.ass --font "PingFang SC"
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
words. Grouping defaults live in `group_captions.py` (pair ≤11 display columns with a CJK glyph
counted as 2, join gap <0.35s, 0.15s tail = the pause-blanking, 0.20s min hold, de-overlap trim).
The bottom ~15% band is the caption safe-zone. A Chinese hook plate stays ≤10 characters; the
≤6-word budget is the Latin equivalent.

If `faster-whisper` cannot be installed, or the transcript comes back empty, deliver
`output/final.mp4` untouched and tell the user captions were skipped and why. Never hand-write
timings, never even-spread, never describe an un-burned master as captioned.
