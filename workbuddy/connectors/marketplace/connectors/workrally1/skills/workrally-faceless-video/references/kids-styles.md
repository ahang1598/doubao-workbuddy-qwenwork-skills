# kids-styles.md — the Kids channel: baked-in styles + interplay rules

The Kids channel type runs on ITS OWN baked-in style set (below) — offer THESE
in the style question, not the generic paths. Each style ships a pinned
FORMULA (§0 form — paste byte-identical everywhere) and 2–4 CANONICAL
reference images (URLs below). **Phase 1 for Kids:** import every listed URL
as `input_images` URLs (see the WorkRally note below; local files go through
`upload_file` first), then make ONE style-key call on `canvas_generate_image`
together with the style's
FORMULA and the §1 style-sample template (user's aspect) → the completed
task_id is the USER'S OWN unique style key, look-locked to the canon. The refs
are STYLE DONORS ONLY — never used as frames, never shown as the result, and
their SUBJECTS are never copied (take the render style, not the characters).
If the URLs are missing/unreachable, fall back to generating the key from the
FORMULA alone (log which path was taken).

## Canonical ref URLs (style donors)

> **WorkRally:** these URLs are on a CDN that is NOT in WorkRally's `input_images`
> allowlist. `curl` each one to a local file, `upload_file` it, and use the returned
> WorkRally URL. If a download fails, the pinned FORMULA alone is still a valid anchor —
> say the style is formula-only for this run. There is no `media_id` to resolve.

**1. Studio 3D (recommended default):**
- https://static.higgsfield.ai/faceless/studio_3d_1.jpeg
- https://static.higgsfield.ai/faceless/studio_3d_2.jpeg

**2. Pastel Flat 2D:**
- https://static.higgsfield.ai/faceless/flat-2d-1.jpeg
- https://static.higgsfield.ai/faceless/flat-2d-2.jpeg
- https://static.higgsfield.ai/faceless/flat-2d-3.jpeg

**3. Colorful 3D:**
- https://static.higgsfield.ai/faceless/colorful_3d_1.jpeg
- https://static.higgsfield.ai/faceless/colorful_3d_2.jpeg

**4. Hand-drawn Ink:**
- https://static.higgsfield.ai/faceless/hand-drawn-1.jpeg
- https://static.higgsfield.ai/faceless/hand-drawn-2.jpeg
- https://static.higgsfield.ai/faceless/hand-drawn-3.jpeg
- https://static.higgsfield.ai/faceless/hand-drawn-4.jpeg

**5. Poster Vector:**
- https://static.higgsfield.ai/faceless/flat-2d-4.jpeg
- https://static.higgsfield.ai/faceless/flat-2d-5.jpeg
- https://static.higgsfield.ai/faceless/flat-2d-6.jpeg

Style question for Kids: chips 1–4 in this order (Studio 3D first, marked
recommended) + "More styles" → Poster Vector and the preset widget (Fluffy Toy
lives there). Hands-off default = Studio 3D.

## 1. Studio 3D (recommended default)

> Studio 3D preschool style — chunky rounded cartoon 3D characters with a soft
> glossy toy finish, big adorable googly cartoon eyes and tiny friendly smiles,
> smooth matte-and-glossy plastic-clay surfaces with no sharp edges, clear
> readable silhouettes, bright saturated candy colors (red, yellow, blue,
> orange, green), gentle soft studio lighting with soft rounded shadows, pure
> clean seamless white background with generous negative space, playful
> preschool CGI look — non-photorealistic, no live-action, no on-screen text.

{MOTION}: dimensional — `springy bouncy friendly motion (hops, wobbles,
blinks), smooth gentle camera moves`; DROP `3D render` from NEGATIVE.
PALETTE LOCK: `bright candy palette of the reference images on a pure seamless
white background — no new colors, no gradients in the backdrop`.

## 2. Pastel Flat 2D

> flat 2D vector cartoon in a soft pastel preschool style: soft pink, baby
> blue, mint green, sandy yellow and lavender palette, colored outlines one
> shade darker than each fill (never black), large round circle eyes with
> white sclera, large black pupils and small white glints, simplified rounded
> shapes with organic curves, cell shading with distinct flat shadow shapes,
> friendly warm expressions, clean uncluttered backgrounds with a soft gentle
> gradient, no sharp angles, no textures.

{MOTION}: flat — `simple limited animation on twos, soft bouncy easing`; KEEP
`3D render` in NEGATIVE.
PALETTE LOCK: `pastel palette of the reference images (pink / baby blue /
mint / sandy yellow / lavender) — no new colors, outlines darker-shade never black`.

## 3. Colorful 3D

> colorful stylized 3D cartoon: deliberately rounded chunky character
> proportions with oversized sparkling expressive eyes, wide warm smiles and
> clear readable silhouettes, glossy toy-like clean surfaces, soft
> near-shadowless studio lighting, cartoonish high-gloss CGI never photoreal,
> ULTRA-VIVID high-saturation candy palette turned up bold and punchy (cherry
> red, sky blue, sunny yellow, lime green, orange at full intensity — never
> muted, never pastel), cozy storybook environments with rounded friendly
> shapes under a bright blue sky with fluffy clouds, safe friendly upbeat
> mood with adventure but no real danger, lively springy comedic motion
> accents (sweat drops, surprise marks, whoosh effects).

The cast, its size and any team roles come from the SCRIPT, not the style —
this look works with one hero, two friends or a crowd equally well.

{MOTION}: dimensional — `lively springy motion with comedic accents, dynamic
but gentle camera (push-ins, orbits, crane pull-backs)`; DROP `3D render`.
PALETTE LOCK: `vivid high-saturation candy primaries of the reference images,
turned up bold — no muted or pastel drift, no new colors; if the script has
recurring heroes, each keeps one consistent signature color`.
Note: this style pairs well with a light instrumental bed — but the skill's
music policy is unchanged (bed only if the user provides/asks).

## 4. Hand-drawn Ink

> hand-drawn thin-line ink illustration, uniform thin slightly wobbly black
> ink outlines on a PURE WHITE background, objects and figures left uncolored,
> simple rounded figures with dot eyes, tiny line mouths and hugely expressive
> eyebrows, soft flat light-grey shadow shapes under objects and figures with
> soft edges and no hatching, flat 2D, no gradients, no texture, STRICTLY
> NEUTRAL BLACK-AND-WHITE greyscale — no color cast, no bluish or cool tint,
> no colors beyond pure white, neutral grey and black, deadpan understated
> humor, clean disciplined linework, never photorealistic.

{MOTION}: flat — `simple limited animation on twos`; KEEP `3D render`.
PALETTE LOCK: `pure white / neutral grey / black ONLY — any color is a defect`.

## 5. Poster Vector

> flat 2D vector cartoon in a cheerful minimal poster look — bold rounded
> geometric shapes with no outlines, solid flat color fills, NO gradients, NO
> texture, friendly blob characters with tiny curved-line closed eyes or dot
> eyes and small simple smile mouths, one subtle flat darker-tone offset
> shadow per shape, vivid saturated palette of sunny yellow, tangerine orange,
> cobalt blue, bubblegum pink, grass green, deep navy plus black and white
> accents, single plain flat solid-color background, a white sparkle diamond
> as the signature accent.

{MOTION}: flat — `snappy poster-style motion, shapes popping with slight
overshoot`; KEEP `3D render`.
PALETTE LOCK: `the poster palette of the reference images, one flat backdrop
color per scene — no gradients, no new colors`.

---

## The Kids EXPLAINER skeleton — THE QUESTION COMES FIRST

Almost every Kids topic is "what is X", "how does X work" or "why does X". A Kids
video that opens on atmosphere reads as random to a child. The skeleton is fixed:

- **Block 1 = the question out loud, then the answer in the same breath.** Name the
  thing in the FIRST sentence, phrased the way a child would ask it, and answer it in
  plain words. No windup, no "today we are going to learn about", no scene-setting
  before the answer lands.
- **Block 2 = ONE concrete example the child can see.** Not "cells are everywhere"
  but "this leaf is packed with millions of them, stacked like bricks" — a single
  named thing doing the thing.
- **Middle blocks = one new idea each, in the order a child actually asks:** what is
  it → where is it → what does it do → what happens without it. Never two ideas in
  one block.
- **Last block = the WOW then the CALLBACK.** One surprising quantity, said in words,
  then a closing line that answers the opening question again in four or five words.
- **THE TEST, run it before SCRIPT LOCK:** read ONLY the first sentence of every
  block, in order. If those sentences alone do not answer the opening question, the
  script is random and gets rewritten — not patched with livelier wording.

## Kids plain language — the sentence a six-year-old repeats back

Density is not the same thing as difficulty: a Kids line can be full and still be easy.

- **One idea per sentence, and at most two sentences per block.** A second clause
  hanging off a comma is a second idea — split it or drop it.
- **Everyday words only.** Say what a thing DOES before what it is CALLED, and only
  name it once. Abstract nouns get replaced by something visible.
- **Compare to what a child already holds:** a grain of rice, a football pitch, a
  school bus, a bathtub, a heartbeat. Never to a micron, percentage, or scientific scale.
- **Small counts, said in words.** No decimals, ranges, or dates.
- **No stacked adjectives, no similes inside similes**, and no sentence that needs
  the previous sentence to make sense.
- **Read it out loud as a test:** if you run out of breath, or would not say it to a
  six-year-old at a kitchen table, rewrite it. A slightly shorter line that lands
  beats a full line that does not.

## Pictures must TELL the story, not decorate the narration

Every block shows a CHANGE, never a tableau:

- **One visible action per block, with a before and an after** — the lid comes off,
  the seed cracks, the water climbs the stem, the balloon leaves the hand. The 4-cut
  pattern stages that one action; it does not show four angles of a standing pose.
- **The through-line prop is physically present AND physically different by the end**
  — it moves, opens, fills, multiplies, or changes colour.
- **Forbidden:** a character standing and gesturing at an unchanged scene,
  atmosphere beats with nothing happening, and the same staging twice in one video.
- **The verb test:** if a block's shot text can be written without a verb, it is
  decoration — rewrite it with something happening.

## Narrator-only is the DEFAULT Kids video

Talking characters and the sung song are OPT-IN sub-modes. They are not a fix for a
weak script. Make the plain narrated Kids explainer strong first: lock the skeleton
and picture-storytelling, then use dialogue or a song only when the user asked.

---

## The Kids interplay (narrator ↔ character ↔ viewer) — MANDATORY

This is what makes Kids content Kids content: the narrator TALKS to the
characters and the viewer, and the video VISIBLY ANSWERS.

- **Characters react to the narrator on screen.** When the VO greets or asks
  ("Say hi to Masha!"), that block's SHOT beat stages the reaction: the
  character turns to camera and WAVES, nods, gasps, claps, points, presses a
  finger to lips. Write the reaction INTO the shot text, timed to the line's
  beat. Mouths never move with speech — reactions are gesture and face only
  (rule 7's no-lip-sync stands; reacting ≠ talking).
- **Direct address, both ways.** The narrator names characters and talks to
  them ("Look how brave Masha is!") AND to the viewer ("Can YOU spot the red
  balloon?"). Characters look INTO the camera on viewer-addressed beats —
  breaking the fourth wall is the genre, not a bug.
- **Call-and-response across block boundaries.** Put the question at the END
  of a block's line ("...can you count the apples?"); the block boundary IS
  the answer beat, and the NEXT block opens with the payoff ("That's right —
  three!"). Never leave a long pause INSIDE a line for the answer (the ≥0.8s
  internal-pause rule still applies — boundaries are free pauses).
- **Rich narration, always moving:** catchphrases, sound-words spoken by the
  narrator ("whoosh!", "ding!"), micro-celebrations ("hooray!") — packed into
  17–21-word flowing lines; warmth = word choice, never pauses.

## Kids shot dynamics — the 4-cut block

Kids blocks are MORE dynamic than the house default of FIVE cuts: use **FOUR hard cuts**
per 10s block, pattern `WIDE establishing → CU on the character (reaction
beat) → ECU on the detail/object → MEDIUM (resolution)`:

```
SHOT 1 — 0.0s to 2.5s — WIDE: {scene establishing beat}.
HARD CUT.
SHOT 2 — 2.5s to 5.0s — CLOSE-UP on {character}: {reaction to the narrator}.
HARD CUT.
SHOT 3 — 5.0s to 7.5s — EXTREME CLOSE-UP on {detail/prop}: {the thing itself}.
HARD CUT.
SHOT 4 — 7.5s to 10.0s — MEDIUM: {resolution / celebration beat}.
```

Vary the pattern's order between blocks (never twice the same sequence);
everything else from prompts.md §3 applies (staggered entrances, one camera
behavior per shot, settle at the end, impact beat, SFX 1:1). If a 4-cut block
fails twice on generation, drop THAT block to 3 cuts — never the whole video.

## Kids audio

Clips carry PLAYFUL diegetic SFX (the assembler keeps them under the voice):
sparkle dings, boings, pops, giggling bells, whooshes on hops — 2–4 cues tied
to motions + a soft ambient bed. The AUDIO line names them per cue, still "no
voice, no narration, no music".

## Kids music bed — DEFAULT ON (style-inherent: it travels with the Kids look)

A Kids video ships WITH a wordless background music bed by default — and so
does ANY channel running in a Kids-catalog style (cross-channel rule: the bed
is the Kids styles' style-inherent law; a history run in Colorful 3D gets a
bed too, with the MOOD matched to the CHANNEL's tone — playful-light, not
babyish). GENERATED per run to fit the topic. Source priority:

1. a file the user supplied (always wins);
2. GENERATE the bed before the AUDIO review with `canvas_generate_audio`
   `mode:"music"` (no voice id), model from `canvas_audio_model_list`,
   **`duration` = the VIDEO's exact total length in
   seconds** (block flow: N×10; picture story: the sum of the takes +
   breaths, rounded up) — one continuous track, NO looping needed.
   **The per-request duration ceiling is whatever the chosen model reports — read it from
   the model list, do not assume the original provider's 600s.**
   Runs longer than that ceiling: split into parts at or below it with the SAME prompt and
   losslessly join them into ONE bed file (`ffmpeg -f concat -c copy` on the
   parts — legal INPUT PREP; the mix itself still happens only inside the
   assembler). Prompt = the topic's mood translated into tempo, instruments
   and feel — **instrumental, no lyrics, no vocals, ≤2 sentences (1 is
   best)**: calm/cozy topics → soft lo-fi or warm marimba + airy pads, light
   mid-tempo; adventure/action → brighter bouncy small-combo groove. Lean on
   acoustic / jazz / lo-fi / small-combo genres — they pass moderation
   reliably; AVOID big orchestral scores and EDM/bass-drop wording (known
   content-filter trips). Poll to `state:4`, download, pass to the
   assembler as `--music <file>` (the assembler's loop is only a safety net
   for a short bed);
3. generation failed/unavailable → assemble WITHOUT a bed and say so in one
   line.

Level: the default bed passes **`--music-vol 0.05`** — tested down from 0.10
and 0.07, where the bed still fought the narration. On top of the level, the
assembler now DUCKS the bed under speech (sidechain compression keyed by the
voice: the music dips hard while a line plays and breathes back up in the
gaps) — the voice must dominate effortlessly; clamp ≤0.20 still holds. Never
block delivery on music, and never synthesize music with the speech model —
`canvas_generate_audio` `mode:"audio"` speaks, `mode:"music"` plays.

## Kids voice pace — hotter delivery, shorter density

Kids lines use **17–21 words per 10s block**
voice, but run faster and more excited; {DELIVERY} carries an EXCITED
cue — name the emotion outright (e.g. `warm thrilled storyteller, quick
bouncy pace, bright smiling timbre, bursting with delight`); generous
performed brackets ([giggles], [gasp], [mock surprise], [laughs]) are
welcome, budgeted ~1s each, and emotion words live IN the lines too ("wow!",
"amazing!", "here comes the best part!"). Warmth and playfulness live in word
choice and ENERGY — never in pauses (the ≥0.8s internal-pause rule still
applies) and never in clipped baby-sentences.
