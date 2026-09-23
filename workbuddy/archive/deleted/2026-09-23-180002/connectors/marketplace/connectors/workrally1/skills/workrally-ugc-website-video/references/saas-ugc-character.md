# SaaS UGC creator — input mapping + framing / self-film setting / spoken voice

The creator prompt itself is built from `references/ugc-character.md` (identity, beauty floor,
variety roll, wardrobe, modesty, safety, anti-slop). This file supplies the two SaaS-specific pieces
those rules do not decide:

1. **Input mapping (§0)** — how to settle the inputs `ugc-character.md` asks for, from a site brief.
2. **The clip carry (§1–§5)** — the framing, setting, accent, delivery and audio texture that a
   still cannot hold and that must be restated in the step-5 video prompt so the moving clip
   matches the seed. "Seedance" throughout this file means the provider picked from
   `canvas_video_provider_config` with `support_audio: true`.

## 0. Input mapping (site / store brief)

- **`category`** — map the site `type`: `saas` / `service` / `portfolio` / `content` → **`tech`**
  (the home-desk / living-room / studio-nook casting fits a site creator); `ecommerce` /
  `marketplace` → the **physical product's real category** (skincare, food, …) so the closer's
  product context matches.
- **`tier`** — from `audience`: default **`premium`** (b2b / prosumer founder); a mass-market store
  may use **`drugstore`**. Tier only calibrates wardrobe materials and room refinement.
- **`gender`** — the creator gender from the brief; lock it for the whole video.
- **`location` override** — the locked self-film scene from §2, so ONE setting holds every clip.
- **`user_request`** — the original brief verbatim (tone signals + backup parsing).
- **variety roll** — pick the eight numbers yourself as `ugc-character.md` describes; never reuse a
  previous run's set.

Voice, accent, delivery and audio (§3–§5) never go into the image prompt — the creator rules ban
voice from a still. They belong to the step-5 Seedance prompt only.

## 1. Framing — creator ~2/3 of frame, head CENTERED (no top headroom)

This is the **step-5 video target**, not something you compose in the seed: the creator seed is a
tight 3:4 head-and-shoulders selfie and that is fine — it carries identity only. Restate the framing
below in the clip prompt. The final video is vertical **9:16**:

- **Medium shot** — framed from roughly mid-torso up. The **creator fills about 2/3 of the frame**
  (large and dominant; not a distant full body, not an extreme close-up).
- **Head CENTERED in the frame — horizontally AND vertically.** The head sits in the middle; do
  **NOT** leave empty headroom above it and do **NOT** push the head high. Eyeline straight into the
  lens (phone-camera / selfie energy).
- **The screenshot inset floats over the upper face** — the composite places it centred, slightly up,
  over the live creator (visible around its edges). There is no reserved headroom band, and the inset
  is not for subtitles: captions run along the bottom.
- **Keep the creator clear of the bottom ~15% of the frame** — that is the caption safe-zone; face
  and hands sit above it.

## 2. Environment — the setting is part of the hook

The scene must read as an **authentic, self-filmed UGC moment**, not a studio:

- **Phone propped up in front of the creator** — selfie-style, on a little stand or leaned against
  something, the way real UGC is shot. Slight handheld imperfection is good, not a locked-off look.
- A **real lived-in home spot** — on a couch, on a bed with pillows, at a kitchen counter, at a desk.
  Cosy, personal, a bit of natural clutter — never an empty seamless backdrop.
- **Natural light** — soft window daylight or a warm lamp; the phone-camera look (mild lens softness,
  natural skin), not cinema lighting.
- Pick the spot from the site `type` / `audience`: a b2b/prosumer founder at a tidy desk; a
  consumer-app creator on a couch or bed. Lock ONE setting for the whole video — pass it as the
  location override AND restate it in every clip prompt.

## 3. Voice / accent — natural spoken Mandarin, no broadcast tone

- **自然口语普通话**, the way a real creator talks to a friend. Never a news-anchor / voiceover
  register. State it explicitly in the clip prompt (that is where the speech is generated) — e.g.
  「自然口语的普通话，像朋友聊天，不是播音腔、不是配音腔」. Switch languages or accents only when
  the user asked for one.
- One voice, one identity, the whole video.

## 4. Delivery — lively, varied rhythm, UGC energy

A **natural, lively conversational pace (~4.5–5.5 汉字/秒) — energetic in tone but never crammed or
rushed**, with the speed VARYING within the take (a touch quicker through connective lines, slower to
land a number / price / CTA). Bake it into the clip prompt: **「自然、有活力的口语表达，节奏和重音有
变化——像真人跟朋友聊天，不是旁白，不是配音；自然的手势」**. Allow **2–3 emphasis / non-verbal beats spread across the clip**
(a small laugh, an "honestly", a lean-in) — not just one at the top. The first line is the bold hook
from `saas-monologue.md`.

## 5. Audio texture — phone-mic realism + ambient that matches the picture

The video model generates the audio natively (`enable_sound`), so nudge its CHARACTER in the clip
prompt (best-effort, not a guarantee):

- **Sounds recorded on the phone in the scene** — iPhone front-camera mic: natural, slightly close
  and compressed. NOT studio-clean, NO background music.
- **Ambient = the natural sound of WHAT THE PICTURE SHOWS.** There is no default or preset: a living
  room → soft room tone; a kitchen → faint kitchen hum; a café → low café murmur; a desk/office →
  quiet office hum; outdoors → gentle outdoor air. Kept LOW, under the voice.
- **The spoken voice stays the clear, intelligible spine** — ambient never competes with it.
- Because the SETTING is locked for the whole video, describe the **same scene-appropriate ambient in
  every clip**; consistency comes from the scene being the same, not from a fixed preset.

Example (a living-room scene): *"audio recorded on an iPhone front camera — natural phone-mic tone
with faint living-room ambience matching the shot, no background music; voice clear and up-front."*
Swap the ambience for whatever the scene actually shows.

## Output of this step

`character_url` = `output_assets[0].url` from `canvas_generate_image` with the model picked from
`canvas_image_model_list` (`3:4`, `resolution: 5`), chained forward by URL — no download, no
re-upload — then de-slopped once per SKILL.md 步骤 3.5, and the de-slopped URL becomes the locked
identity. The framing, setting, accent, delivery and audio-texture notes are then **repeated in the
step-5 video prompt** so the moving clip matches the seed.
