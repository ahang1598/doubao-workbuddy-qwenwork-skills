# Composite — screenshot insets over the live creator (ffmpeg only, no generation)

The creator is on camera the whole video (the clips are the base picture and the continuous voice).
Each useful screenshot shows as a **large inset laid OVER the face** for ~1.2–1.5s, then clears — the
viewer sees a clean face between insets. The inset **floats over the live video**: no blurred
background, no blurred copy, no solid backing. **No generation here** — every screen pixel is a real
capture and ffmpeg only composites.

Steps A–D run in the **local shell** — there is no cloud sandbox and no `sandbox_exec` tool.
`curl -sL` the clips and card stills down from their result URLs first, run the ffmpeg chain, then
`upload_file` `output/final.mp4` (or `final_captioned.mp4` when the captions step follows) and
`asset_create` it if it needs to land in the media library. Requires local `ffmpeg` / `ffprobe`;
say so and stop if they are missing. Do not call `video_concat`.

Target 1080×1920 (9:16), clip fps (ffprobe), yuv420p, **audio copied, video encoded exactly once**
(this overlay pass). Geometry is in FRACTIONS of the frame — recompute px for other sizes.
Inputs: `output/clip_<K>.mp4`, `output/section_<label>.png`, the ordered `{section_label, words}` plan
plus the hook and closer word counts.

**Degrade case:** no usable cards (capture failed and no user screenshots) → skip B–D entirely, concat
the clips into `output/final.mp4` and go to the captions step. Talking-head-only is the accepted
fallback; never invent a UI to fill the gap.

## A — base spine

```bash
: > output/clips.txt; for K in $(seq 1 N); do echo "file 'clip_${K}.mp4'" >> output/clips.txt; done
ffmpeg -f concat -safe 0 -i output/clips.txt -c copy output/creator_full.mp4
T=$(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 output/creator_full.mp4)
FPS=$(ffprobe -v error -select_streams v:0 -show_entries stream=r_frame_rate -of default=nw=1:nk=1 output/clip_1.mp4)
```

N never matters downstream — all window math runs over the absolute timeline `T`.

## B — card images (no pad, no backing — they float over the live creator)

Every card must carry a **site marker** (logo / navbar / price+CTA / a reviews UI block). If a crop
loses the marker, **widen the band — never centre-crop it away**.

1. **Never use ImageMagick on the full-page capture.** A mobile full-page shot of a modern landing is
   routinely 20-25k px tall, and ImageMagick's default resource limits reject it — `identify` and
   `convert` then exit non-zero, sometimes with empty stdout and stderr, so the step fails silently.
   `ffmpeg` and Pillow read the same file fine; use them. With Pillow set
   `Image.MAX_IMAGE_PIXELS = None`.
2. **Never crop a band by y-FRACTION.** Repeat captures of one URL vary in height by up to ~14% —
   hundreds of px of drift, enough to slice a heading in half. Crop by the **absolute rect** the
   capture script reports for that section (`rect.top * rect.dpr`), never by a fraction of the page
   height.

**There is also no image-analysis tool here, so do not plan on measuring bands by eye.** Prefer
captures over crops:

- **Other cards (reviews / specs / pricing / feature screens / product views)** — use each
  `output/section_<label>.png` **directly** as the card content. The capture script centres each
  section in the viewport, so site chrome is already in frame. This is the primary path and needs no
  geometry at all.
- **Hero card (the first card — must read as the site)** — capture it as its own section still by
  passing the site's brand / H1 wording to `--sections`; that viewport shot lands near the top of the
  page and already contains logo + navbar. Only if no such still exists, crop from `site_full.png`
  with ffmpeg — by the reported rect when the script gave you one, otherwise the top band:
  ```bash
  # element-anchored (preferred): TOP = rect.top * rect.dpr, H = band height in device px
  ffmpeg -i output/site_full.png -vf "crop=iw:${H}:0:${TOP}" output/card_hero.png
  # last resort, no rect available:
  ffmpeg -i output/site_full.png -vf "crop=iw:ih*0.35:0:0" output/card_hero.png
  ```
  If a stitched or tall card makes text unreadable after the step-D box-fit, drop the lowest-value part
  and rebuild — never crop the frame tighter.
- **User-provided screenshots** (fallback capture, usually DESKTOP) — use them **as is**: no stitch, no
  mobilising, no 3:4 crop, and **never a cover-crop**. The step-D contain-fit handles a wide desktop
  frame; it simply lands shorter in height.

**A missing section is not an error.** The capture script prints `error: "not reachable"` for a label it
could not open, and a lazy section can leave a `rect` of `null`. Skip that card, note it, and carry on
with the rest — never let one missing anchor throw. Once the set is built, apply the 3-card minimum: fewer
than 3 usable cards means the ask-the-user gate in `website-capture.md`, not a half-empty video.

**Card order:** hero (logo / navbar site marker) FIRST, anchored to the beat that names the site, then
details / product → reviews → price / warranty. Aim for ~6-10 cards and skip filler (nav strips,
footers, logo walls).

## C — timeline (variant B anchor, no ASR)

`t(cum) = T × cum_words / total_words` over the continuous voice. For a Chinese script count
**characters**, not space-separated words — the ratio is what matters, so the unit only has to be
consistent across the whole timeline.

- Hook → NO inset; `t_hook = min(2.0, t(hook_words))`. The hook lands on the open face.
- Body → every still is its own inset, anchored at its beat: `s_k = t(cum words before beat)`,
  `e_k = s_k + 1.4` (~1.2–1.5s), clamp `s_k ≥ t_hook`, and keep a **~0.3–0.5s clean-face gap** between
  insets (push a later anchor back if it would collide). Insets are interrupted, never a continuous
  strip. The first inset is ALWAYS the hero, at the site-naming beat.
- Closer → NO inset; `t_closer = t(total − closer_words)`; drop any window that would spill past it —
  the product action owns the closer.
- More insets come from **more captures + more narrated beats**, never from longer windows.

**Anchor drift.** `t(cum)` assumes even pacing from the authored words-per-section, but the render may
speak with pauses, so an inset can drift off the words it illustrates. If the drift is visibly off, run
one optional pass: transcribe `output/creator_full.mp4` word-level with `"$SKILL/scripts/transcribe_words.py"`
and recompute each `s_k` from the REAL word times, then re-composite. Use only when needed — it costs a
transcription.

## D — overlay (one encode)

```bash
WBOX=$((1080*78/100)); HBOX=$((1920*60/100)); UP=$((1920*4/100))
ffmpeg -i output/creator_full.mp4 -i output/card_hero.png -i output/card_reviews.png … \
  -filter_complex "\
    [1:v]scale=${WBOX}:${HBOX}:force_original_aspect_ratio=decrease[c1]; …\
    [0:v][c1]overlay=(W-w)/2:(H-h)/2-${UP}:enable='between(t,S1,E1)'[v1]; …" \
  -map "[vN]" -map 0:a -c:v libx264 -pix_fmt yuv420p -profile:v high -r "$FPS" -c:a copy output/final.mp4
```

One scaled input plus one time-gated `overlay` per card with the real `[s_k, e_k]`. The contain-fit box
(`0.78W × ≤0.60H`) does three things at once: width lands at ~0.78·W, the **hard height ceiling
0.60·H** is enforced (a tall card shrinks until it fits, so it never runs off-screen or into the
captions), and card sizes **normalise** so the inset does not jump between a tall hero and a short
warranty card. Centred horizontally and shifted up `0.04H`, the inset bottom lands ≈0.80H — clear of
the bottom ~15% caption band (raise or shrink further if a card ever reaches it).

No blur, no backing — the creator stays visible around the edges. **Audio is copied** (`-c:a copy`),
never re-encoded; the video is encoded exactly once, here. `output/final.mp4` is this step's
deliverable.
