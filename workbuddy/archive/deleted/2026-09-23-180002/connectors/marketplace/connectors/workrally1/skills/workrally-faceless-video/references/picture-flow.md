# picture-flow.md — the PICTURE STORY direction (narrated stills)

The fourth channel direction, PEER to Explainer / History / Kids: the video is
built from STILL IMAGES, not motion clips. One continuous narration is generated
first; Whisper word timestamps then define a dense sequence of ~0.7–1.2s
microframes, with a new frame at every framing change. The assembler holds each
frame for its timeline segment; there are no fixed 10s windows. Tone is free: a
Picture Story can be a kids bedtime tale, a history vignette, a deadpan
slice-of-life — the direction is the MECHANIC, not the audience.

Models stay locked: images from `canvas_image_model_list`, voice from
`canvas_generate_audio` `mode:"audio"` (core MCP). NO
`canvas_generate_video` in this direction — nothing is animated. No TTS model → this
direction cannot run; offer a motion channel.

**The "Frame by frame" preset card — or ANY explicit stills/picture preset ask —
LOCKS this direction, even when the channel/brief says History or Kids.** The
channel keeps its TONE (kids-warm, history-witty); the mechanics are this
file's. Never "correct" the pick back to a motion flow.

## Styles (offer these three chips; descriptions VERBATIM)

1. **Flat 2D Papercraft (recommended)** — "Layered cut-paper collage — flat
   colored paper shapes with crisp cut edges, subtle drop shadows between
   layers, textured construction paper." (Preset card: **"Frame by frame"** in the
   "Faceless channel presets" catalog — picking that card means this direction + this
   look.)

   FORMULA (§0 form, byte-identical everywhere):

   > flat 2D papercraft collage: characters and scenery cut from colored
   > construction paper with crisp scissor-cut edges, layered flat shapes
   > with subtle soft drop shadows between paper layers, visible paper grain
   > and fiber texture, slightly imperfect hand-cut silhouettes, matte
   > saturated paper palette, simple readable compositions on a plain paper
   > backdrop, handcrafted collage feel, non-photorealistic, no gradients
   > outside paper shadows, no outlines — shapes are defined by paper edges.

   PALETTE LOCK: `matte construction-paper palette of the reference images —
no neon, no gradients, colors read as physical paper`.

2. **Stickman Cartoon** — the generic webcomic formula from
   `${FACELESS_SKILL_DIR}/references/prompts.md §0` (crude paint-program webcomic), verbatim.

3. **Hand-drawn Ink** — the formula from `${FACELESS_SKILL_DIR}/references/kids-styles.md §4`
   (thin-line ink on pure white, greyscale), verbatim.

Something adjacent the user asks for ("crayon", "flat vector") → map to the
closest of the three and confirm in one line; uploads work as style donors as
usual.

## FRAME-BY-FRAME, not a slideshow (this direction's core)

The audio is ONE continuous narration of the whole story (Phase 5) — NEVER
2–3s per-beat snippets. Whisper then gives word timestamps, and FRAMES are
laid onto that timeline (Phase 5b/4/6). The point is animation-by-stills: a
single moment gets a SMALL BURST of near-identical frames that each change ONE
detail, so it reads as movement — not one static picture held while the
narrator talks.

**The mental model — a moment = a burst of edited frames of the SAME shot:**

> "woke up, on his back" → F1 WIDE: John flat on his back, eyes closed.
> (same shot) → F2: eyes OPEN. (same shot) → F3: head turned, squinting.
> "his face — a scowl" → F4 CLOSE-UP: John's face neutral.
> (same shot) → F5: brows knit, scowl lands.
> "he sat up on the bed" → F6 MEDIUM: sitting up, mid-rise.
> "shuffled down the hall" → F7: walking the hallway.
> (same shot) → F8: still walking, scratching his head.
> "brushing his teeth" → F9 INTERIOR: brush AT his mouth.
> (same shot) → F10: hand DOWN, done, foam on lip.

Every arrow is ONE image. Notice most moments are 2–3 frames of the SAME
composition with one change (eyes, brow, hand position) — THAT is the
frame-by-frame feel. A brand-new framing happens when the ACTION or PLACE
changes (bed → face → hall → bathroom), not on every frame.

- **A new SHOT (new framing) whenever the line changes** action, place or
  subject; WITHIN a shot, 2–3 micro-variation frames carry the little
  movement (open eyes, turn head, raise hand).
- **SHOT MIX (the cut rhythm):** each frame names its SHOT — WIDE / MEDIUM /
  CLOSE-UP — mixed RANDOMLY with exactly one hard ban: **two CLOSE-UPs never
  run back to back.** Everything else may repeat (WIDE WIDE is legal, MEDIUM
  MEDIUM is legal): a healthy run reads like
  `W M W C W W M C W`. The CLOSE-UP → MEDIUM handoff is the money transition —
  show the emotion close, then play the resulting movement on the medium.
  (A micro-variation frame keeps its base's shot size — that's the one legal
  same-framing repeat, and it still counts as a CU for the no-two-CUs rule.)
- **Frame cadence — a frame every ~0.7–1.2s.** Once Whisper gives the
  timeline, slice it so NO frame holds longer than 1.5s (the assembler's hard
  cap). A phrase that spans 2s = 2 frames; 3s = 3 frames — usually the
  base plus its micro-variations. The picture changes about twice per spoken
  beat; a frame lingering while the narrator keeps talking is the slideshow we
  are killing.
- **THE MICRO-VARIATION FRAME (the whole trick) — it is an EDIT, not a
  re-render:** most frames ARE the previous frame with ONE detail changed.
  Generate it by passing the previous rendered frame's result URL as the **ONLY**
  reference — **do NOT attach the character sheet, location or props** (those
  make the model rebuild the scene, producing a different picture instead of an
  edit). Prompt: "Take the reference image and keep it EXACTLY — same
  composition, crop, camera, character, colors, background, style. Change ONLY:
  {one detail — eyebrows knit / eyes open / hand lowers / foam appears}. Do not
  redraw anything else." A run of 2–4 such edits chained on ONE shot IS the
  animation; a genuinely new framing (from assets) only when the action or
  place changes. See Phase 4 for the KIND-A/KIND-B split.
- **Frame count is a HARD FLOOR, not a suggestion: at least one frame every
  ~1.5s of narration, target one every ~1s.** A 1-minute story = **45–70
  FRAMES** (never fewer than ~40); 2 minutes = 90–140. Plan the count from the
  target duration BEFORE generating and show it at SCRIPT LOCK. **The assembler
  REJECTS a run with fewer than `ceil(narration_sec / 1.5)` frames** (a 60s
  story with 15 frames is a slideshow and hard-fails) — so generate the full
  dense set up front, don't discover the shortfall at assembly.
- **Why this is cheap: MOST frames are micro-variations** — the previous frame
  with ONE detail changed (one ref image + one `change_only` line). A single
  spoken moment ("he woke up") is not one frame, it is a BURST: on his back →
  eyes open → head turns → sits up. Budget ~2–3 frames per spoken beat; if a
  beat has only one frame, you are under-generating. Generate variations
  liberally — they are one `canvas_generate_image` call each and they ARE the animation.
- **SHOW WHAT THE LINE NAMES** (the variety law applies): the frame's nouns
  are IN the picture.
- Characters recur across frames (John in every frame) — identity comes from
  the asset roster refs + the previous-frame ref, same as the video flow.

## Pipeline deltas (vs the video flow)

Phases keep their numbers; what changes:

- **Phase 2 — assets (MANDATORY, FIRST — frames are composed FROM them):**
  characters (3:4) + key locations (chosen aspect) + props (1:1), style
  formula byte-identical, ≤7 refs per image call. Assets are REFERENCES
  ONLY — an asset sheet NEVER appears in the final as a slide (the assembler
  hard-fails on any wrong-aspect image). Locations are cheap here — a beat
  reuses its location REF with a different composition, never the same
  rendered frame. Submit independent assets through `canvas_generate_image` in
  sequential groups of at most six and wait each group with `canvas_get_task` polling.
- **Phase 3 — script = ONE continuous narration + a shot outline.** Write the
  whole story as flowing narration (the text the singer/narrator will actually
  read end to end), PLUS a shot outline naming the framings in order
  (bed-wide → face-CU → hall-medium → bathroom) and, per framing, which
  micro-variation frames it will spawn (eyes open, brow knits, hand lowers).
  SCRIPT LOCK shows the narration + the outline + the estimated FRAME count.
- **Phase 5 — voice FIRST, ONE CONTINUOUS TRACK (not per-beat):** generate the
  ENTIRE narration as ONE `canvas_generate_audio` `mode:"audio"` take (the locked
  model + voice), read
  straight through — NEVER 2–3s snippets per phrase (that was the old bug).
  Long stories exceed the 2048-char prompt limit → split into a FEW LARGE
  chunks (whole paragraphs, ~1800 chars each, same voice pair + same
  {DELIVERY} verbatim) and losslessly join them into ONE `narration.wav`
  (`ffmpeg -f concat -c copy` — legal input prep). One flowing read, natural
  pacing; regenerate a chunk on wrong timbre or garbled reads. The narration phase
  skill submits chunks with `canvas_generate_audio` `mode:"audio"` and waits with `canvas_get_task` polling.
  After all chunks pass, interactive mode posts
  the exact final audio ledger, asks whether to continue to images, and ends the
  turn.
- **Phase 5b — Whisper the narration → the NUMBERED FRAME TIMELINE.** Run
  `${FACELESS_SKILL_DIR}/scripts/audio_to_captions.py narration.wav
  --json words.json`. The JSON contains canonical `words` plus display
  `captions`. Feed it directly to the deterministic builder:

  ```
  python3 ${FACELESS_SKILL_DIR}/scripts/build_scene_timeline.py \
    --script script_manifest.json --timestamps words.json \
    --audio-duration {MEASURED_AUDIO_SECONDS} \
    --requested-duration {REQUESTED_SECONDS} --out scene_manifest.json
  ```

  This is the only production frame-segment builder. It aligns authored beats to
  Whisper words, creates contiguous ~0.7–1.2s segments capped at 1.5s, numbers
  them in spoken order, and emits dependency `generation_waves`. Never hand-author
  a recovery timeline or spread timestamps evenly.
- **Phase 4 — images AFTER the timeline exists. TWO frame kinds, and MOST are
  EDITS (this is the whole point — read carefully):**

  **KIND A — NEW-FRAMING frame (`image_mode:"new"`):** a fresh `canvas_generate_image`
  render composed FROM the Phase-2 assets. `input_images` = the segment's location →
  character sheet(s) → props, in that order; prompt = the SHOT +
  scene in THIS EXACT style {FORMULA}. Use this ONLY when the ACTION or PLACE
  changes (bed → face → hallway → sink). These are the MINORITY — roughly one
  per real scene change.

  **KIND B — EDIT / micro-variation frame (`image_mode:"variation"`) — the
  MAJORITY (~2 of every 3 frames):** DO NOT re-render from assets. Take the
  PREVIOUS rendered frame's task_id and pass it as the **ONE and ONLY**
  reference on the call — **NO asset sheets, NO location, NO props** (adding
  them makes the model rebuild the scene from scratch — the exact bug that
  yields different pictures instead of an edit). Prompt VERBATIM shape:
  > "Take the reference image and keep it EXACTLY: same composition, same crop,
  > same camera, same character, same colors, same background, same style.
  > Change ONLY: {one small detail — eyes open / brows knit / hand lowers /
  > mouth opens / foam appears}. Do not redraw or re-stage anything else."
  The result is the previous frame with ONE thing moved — THAT is the
  animation. A burst on one shot = KIND A once, then 2–4 KIND-B edits CHAINED,
  each editing the frame before it (frame3 edits frame2 edits frame1). **If two
  consecutive frames look like different photos of the same moment, KIND B was
  done wrong — assets were sent and the scene got re-rendered instead of the
  previous frame edited.**

  Both kinds: `aspect_ratio` = the CHOSEN aspect (never square/3:4/1:1 — the
  assembler rejects wrong-aspect), 1080p-class not 2k/2.7k, no in-frame text.
  Submit frames by the manifest's `generation_waves`. Use each frame number as
  the submission wave `index`: wave 0 contains independent KIND-A frames, wave 1
  contains the first edit in each chain, and wave 2 the second. Process each wave
  in groups of at most six, then wait with `canvas_get_task` polling. A variation passes its
  predecessor's completed result URL as its only `input_images` entry. **Generate the
  FULL dense set to clear the
  assembler floor (`ceil(narration_sec/1.5)`, ~40 for a minute) AND make ~2/3
  of them KIND-B edits. Mostly-KIND-A is the "every frame is a different
  picture" bug — regenerate the in-between frames as edits of their
  predecessor, do not pad holds.**
  - **PROVENANCE — STRICT:** save every `canvas_generate_image` and `canvas_get_task` polling
    JSON result, then bind actual `{index,task_id,result_url}` records to the
    deterministic slots and atomically materialize the complete frame set:

    ```
    python3 ${FACELESS_SKILL_DIR}/scripts/bind_scene_frame_results.py \
      --manifest scene_manifest.json --results jobs-wave-0.json \
      --results jobs-wave-1.json --results jobs-wave-2.json \
      --out scene_manifest.bound.json
    python3 ${FACELESS_SKILL_DIR}/scripts/materialize_scene_frames.py \
      --manifest scene_manifest.bound.json --frames-dir work/frames
    ```

    The binder checks variation lineage; the materializer downloads through an
    isolated staging directory and atomically swaps the complete `frameNNN.png`
    set. Missing slots fail closed. Never copy a neighbouring frame into a gap or
    name frames by job completion order.
- **IMAGE REVIEW — after every frame is terminal:** interactive mode calls
  the exact final frame ledger in chat, split into
  consecutive display groups of at most 24 because dense Picture Stories
  normally exceed one widget, asks whether to assemble the final video, and
  ends the turn. There is no video generation or video review in Picture Story.
  Auto/headless runs continue directly to Phase 6 without the list.
- **Phase 6 — `${FACELESS_SKILL_DIR}/scripts/finish_video.sh
  --stills --timeline scene_manifest.bound.json --frames-dir work/frames
  --narration <narration-url> --blocks N --requested-seconds REQUESTED_SECONDS`
  in the local shell** (internally
  `${FACELESS_SKILL_DIR}/scripts/assemble_slides.sh`; NOT
  assemble_final.sh): the ONE continuous narration is laid over the whole cut;
  the bound manifest carries Whisper-derived durations plus immutable
  job provenance. `--blocks N` is the frame count (REQUIRED). The script
  asserts: manifest v2, count, contiguous timestamps, valid variation lineage,
  frame numbers strictly ascending with no gaps, per-frame
  ASPECT (a wrong-aspect image = an asset leaked into the frames = hard fail),
  **MAX HOLD — no frame on screen longer than 1.5s**, the sum of durations ≈
  narration length, distinct image-content floor, 1080p-class cap,
  the narration is present (not silent), full decode, and the LEVEL LAW (narration 1.0; optional music bed
  0.10 generic / 0.05 kids, DUCKED under the voice; NO clip SFX in this
  direction — a quiet bed is RECOMMENDED: kids-tone stories follow the Kids
  default-bed rule, others take a user file or explicit ask; never blocking).
- **Phase 7 — subtitles:** `finish_video.sh --subs` burns them locally from the clean master
  (pass `script_manifest.json` as the authored wording; look = `clean` by
  default, `paper` for storybook tones). Never hand-time or hand-burn captions;
  if the skill reports Whisper unavailable, deliver unsubbed and say so.
- The assembled cut is the final video deliverable. Export it through the normal
  confirmed-media delivery path.

## What does NOT apply here

10s windows, 3/4-cut templates, {MOTION} tokens, freeze/tail probes, the video model
retry specifics, impact beats. Everything else (golden rules on models,
voice lock, palette lock, no on-screen text, scripts-only assembly, no
invented progress) applies in full.
