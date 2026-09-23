# Intake and dispatch

This reference contains the complete Phase 0 contract. Resolve `FACELESS_SKILL_DIR`
before following any path below.

## Contents

- Interactive intake and its blocking question rounds
- Style, voice, duration, aspect, and subtitle locks
- Structured hands-off briefs

### Phase 0 — Intake, fixed semantic order

Resolve a structured product rendering alias before checking for missing intake:

- `animation_mode:"fully_animated"` locks the ordinary animated-block pipeline;
- `animation_mode:"scene_based"` locks Picture Story/stills mechanics.

Record the resolved mode and skip any conflicting inference or question. These
aliases are canonical whether they arrive from the user, a dispatcher, or an eval
harness; never default a supplied `scene_based` value back to Animated.

**INTERACTIVE INTAKE IS A BLOCKING PRECONDITION.** At the start of every run, classify
the request as either interactive or explicitly hands-off.
Imperatives such as “做一个”, “生成”, “来一条”, “make”, “create”, “produce”
do **not** mean hands-off. Lock every parameter explicitly supplied by the user and
collect every missing parameter through the question rounds below.

Before calling any media-generation, research, narration, assembly, or subtitle tool,
evaluate this exact condition:

```text
interactive && missing(type | style | topic | duration | aspect | subtitles | thumbnail |
Kids sound mode | voice | pasted-script title when absent)
```

If true, ask the next missing round and **immediately end the turn**. Do not continue
Phase 0, announce production, apply defaults, or enter Phase 1 in that turn. Resume only
after the user answered, then repeat the same check. The only tools allowed
while satisfying this precondition are reading `references/style-catalog.md` for the
style picker and `canvas_audio_model_list` for the voice picker (skip the latter on a
locked silent cut). Reaching any generation call with an
incomplete interactive intake is a workflow failure.

Collect only missing values in this order: (1) channel type, (2) style, (3) topic /
duration / aspect / subtitles / thumbnail, (4) pasted-script title when required,
(5) Kids sound mode when applicable, (6) voice.

**Question form.** Plain chat, in the user's language. At most three questions per turn,
each with two or three mutually exclusive options, the recommended one first, and always
room for a free answer. One short line of context before the questions, then stop — no
prose after them, no "anything else?". This plugin runs inside an IDE agent: there is
**no popup widget surface**, so do not emit GenUI payloads, do not call `ask_user_input`
or any other elicitation tool, and do not invent one. Restate already-locked parameters
as a **statement**, never as a confirmation question.

- **Ask ONLY for what's missing.** Parameters the user already stated in their message
  (duration, aspect, subtitles, thumbnail, style/preset name, topic, channel type) are LOCKED from
  the prompt: do NOT re-ask them and do NOT confirm them — restate the locked ones as a
  plain chat STATEMENT (no question mark, no "confirm or correct", no options) and ask
  only the gaps. A "here's what I gathered —
  all good?" round IS a re-ask and is forbidden. If a round has no missing parameter,
  SKIP that round entirely. Only a merely INFERRED value (e.g. type guessed from the
  topic) still gets confirmed — as a pre-selected option inside the relevant question,
  never as its own extra round.
- **The INTAKE question set is CLOSED.** During intake, the ONLY things this skill may
  ask are type, style, topic, duration, aspect, subtitles, thumbnail yes/no, the Kids
  sound mode, the voice, and one choice among four titles only when a pasted
  script has no title of its own.
  The three post-generation review questions defined above are the only later
  exceptions. NEVER invent extra intake
  questions — no cover/thumbnail image, no video title outside that pasted-script case,
  no language (write narration in the user's language automatically), no
  character/mascot-design question, no "anything else?".
- **Round 1 — channel type (the niche), alone, first:** offer **Explainer
  (recommended)** first, then History, then Kids, then **Fairy Tale & Myth**
  (retellings of myths/fairy tales/legends — cinematic storybook look,
  `${FACELESS_SKILL_DIR}/references/style-cinematic-storybook.md`; also auto-locks when the user says
  "fairy tale / myth / legend / folklore / 神话 / 童话 / 传说", in any language). Picture
  Story is NOT an option here — it auto-locks when the user says "picture story / stills /
  slideshow story / storybook video / frame-by-frame / 图文 / 定格 / 逐帧" or picks
  "Frame by frame" in Round 2
  (narrated stills — `${FACELESS_SKILL_DIR}/references/picture-flow.md`). Ask this round as one
  question with exactly those four options, then end the turn.
- **Round 2 — style, IMMEDIATELY after the type:** read
  `${FACELESS_SKILL_DIR}/references/style-catalog.md` — the catalog is a LOCAL file, there
  is no server-side preset service on WorkRally. Offer the entries for the locked channel
  type by name, with each entry's one-liner verbatim from its style file. The
  picked entry is the LOCKED
  style for the run — lock it and move on (CROSS-CHANNEL STYLE RULE below; the
  "Frame by frame" entry locks Picture Story). Skip the question when the style is already
  decided: a style NAMED in the prompt resolves by name (below), uploaded
  style images (≤3) take the custom path, and a long-form-locked run offers its own
  LONG-FORM style set instead (below). HOW a style was picked never changes its
  mechanics: house styles generate the key from their pinned
  FORMULA (stickman uses the generic webcomic formula in `${FACELESS_SKILL_DIR}/references/prompts.md §0`);
  Kids styles pin 2–3 canonical ref images.
  **Canonical ref images need one extra hop on WorkRally:** the URLs pinned in the style
  files are on Higgsfield's CDN, which is NOT in WorkRally's `input_images` allowlist.
  `curl` each one to a local file, run `upload_file` on it, and use the returned WorkRally
  URL in `input_images`. If a canonical ref will not download, the pinned FORMULA alone is
  still a valid anchor — say that the style is formula-only for this run.
  Then make ONE style-key call on `canvas_generate_image` with the FORMULA. Refs are
  style donors only, never final frames.
  - **Per-type DEFAULTS + long-form:** when nothing is picked (hands-off, briefs):
    Explainer → **Editorial Motion Graphics** (Stickman Cartoon = the second house
    direction); History → **Editorial Motion Graphics** (named alternates **Paper
    Diorama**, **Mannequin** — `${FACELESS_SKILL_DIR}/references/style-mannequin.md`, clay-render
    reenactment figures); Kids → **Studio 3D** (then Pastel Flat 2D / Colorful 3D /
    Hand-drawn Ink / Poster Vector — `${FACELESS_SKILL_DIR}/references/kids-styles.md`);
    Picture Story → **Flat 2D Papercraft** (then
    Stickman / Hand-drawn Ink — one-liners verbatim from
    `${FACELESS_SKILL_DIR}/references/picture-flow.md`; adjacent asks map to the closest and confirm in one
    line); Fairy Tale & Myth → **Cinematic Storybook** (the only style;
    `${FACELESS_SKILL_DIR}/references/style-cinematic-storybook.md`, canon-refs → unique style key like
    the Kids flow). **LONG-FORM AUTO-LOCK: if the request already says ≥10 minutes and/or
    "documentary", the LONG-FORM direction is LOCKED from the prompt** — never
    offered as an option (offering what the user already chose is a re-ask). A locked
    long-form run: duration options become 10/15/20 min (+ Other) if not already
    stated; the style round offers the LONG-FORM set — **Watercolor Chronicle
    (recommended, first)** / Paper Diorama / Editorial Motion Graphics / Upload —
    with descriptions VERBATIM from the style files (`history-longform.md` carries
    Watercolor's one-liner); and the mandatory time warning + ERA-MAP flow from
    `${FACELESS_SKILL_DIR}/references/history-longform.md` apply.
  - **ONE catalog — `references/style-catalog.md`.** Every style that ships with this skill
    has a style file; that file's pinned FORMULA + canonical refs ARE the style. There is
    no `media_id` to resolve and no card art to derive a formula from.
    - **The styles, mapped to their files:** Editorial Motion Graphics · Stickman Cartoon
      (generic §0 formula) · Paper Diorama · Mannequin · Watercolor Chronicle · Studio 3D ·
      Pastel Flat 2D · Colorful 3D · Hand-drawn Ink · Poster Vector ·
      **Frame by frame** = the Picture Story direction · **Fairy Tale & Myth** =
      the Cinematic Storybook look (`${FACELESS_SKILL_DIR}/references/style-cinematic-storybook.md`).
    - **Two entries are DIRECTION entries, not just looks.** "Fairy Tale & Myth" locks
      channel type = Fairy Tale & Myth (on-twos `--stepped 12` + mysterious-calm bed).
      "Frame by frame" locks channel type = Picture Story with the Flat 2D Papercraft
      look (`${FACELESS_SKILL_DIR}/references/picture-flow.md` — formula unchanged).
    - **The legacy Higgsfield-only cards are GONE** (Fluffy Toy, 3D Papercraft, Mixed
      Media, Whiteboard Doodle, Pixel Art, Claymotion, Low Poly, Isometric Flat Vector,
      3D Mix, 2D Illustrator, Dynamic Motion Design, Vintage Documentary, Custom
      Template). They had no style file and existed only as server-hosted card art, which
      this plugin cannot resolve. If a user names one, say it is not available here, offer
      the closest shipped style, and write the formula from the user's own description —
      never pretend the original preset was applied.
  - **CROSS-CHANNEL STYLE RULE — any catalog style is valid on ANY channel type.**
    A style named on input (user message, brief `preset`, or a pick) is the
    LOCKED style for the run even when it is not among that channel's defaults —
    History in Colorful 3D, Kids in Editorial, Explainer in Watercolor Chronicle are
    all legal. Never re-ask, never "correct" the choice, never silently substitute the
    channel's default. **A style brings ONLY its look, never its home channel's
    mechanics:** the style file contributes the FORMULA, canonical refs / anchor
    mechanism (Kids styles keep their unique-key flow anywhere), palette lock,
    {MOTION} + negatives, and style-inherent laws (e.g. Mannequin's cast/identity
    rules). Everything narrative stays with the CHOSEN channel type: cut pattern
    (Kids' 4-cut belongs to the Kids CHANNEL — a History run in Studio 3D cuts the
    standard 5), narrator↔character interplay, beat grammar, documentary skeleton,
    script rules. **Kids-catalog styles carry ONE style-inherent extra: the default
    wordless music bed** (`${FACELESS_SKILL_DIR}/references/kids-styles.md §Kids music bed`) — a history or
    explainer run in a Kids look still gets the bed, with the MOOD matched to the
    channel's tone (playful-light for the look, not babyish). **"Fairy Tale & Myth"
    (Cinematic Storybook) carries TWO style-inherent extras anywhere it is used: the
    on-twos cadence (`--stepped 12`) and a mysterious-calm music bed**
    (`${FACELESS_SKILL_DIR}/references/style-cinematic-storybook.md`).
    The ONE exception is **"Frame by frame"** (or any explicit stills/picture
    style), which IS a direction entry: it locks Picture Story MECHANICS even when
    the channel/brief says history or kids — the channel keeps only its TONE.
    Watercolor Chronicle outside long-form is just the watercolor look — no
    long-form skeleton, no ERA MAP unless the run is long-form.
  - **A named style** → if the user has ALREADY NAMED one (in their message
    or by choosing a named option), resolve it BY NAME against the catalog: exact
    match, else FUZZY match (case/word-order/partial), then confirm in one line.
    If nothing plausibly matches, offer the 1–2 closest names in the SAME breath and only
    then fall back to the full list — never jump straight to the list over a typo (asking
    twice for the same choice is a bug).
  - **Upload ≤3 style images** → the user gives local paths or authorized URLs; local
    files go through `upload_file` first (style donors only).
- **Round 3 — compact intake for everything else (only the missing ones; skip when
  nothing is missing):** at most three questions per turn, then continue in the next
  compact round if necessary. Collect
  (a) topic — free text / channel-link /
  "randomizer"; (b) duration — 1 / 2 / 3 min (+ Other), **Fairy Tale & Myth offers
  2 / 3 min with 2 as the default** (a myth needs room to breathe); **on KIDS runs
  (Kids channel or a Kids-catalog style) the duration question ALSO offers "Music
  video — a sung song (1 or 2 min)"** — picking it locks SONG MODE (`${FACELESS_SKILL_DIR}/references/kids-song.md`:
  the song is generated FIRST, the blocks are staged to it; direct asks like "kids
  song / sing-along / music video / 儿歌 / 音乐视频" lock it from the prompt, and read that
  file's UNVERIFIED warning before promising anything); (c) frame aspect —
  **16:9 (default)** / 9:16, and only what the chosen model's `aspect_ratios` actually
  lists (never offer a ratio WorkRally does not have — there is no `4:5` and no `2:3`);
  (d) subtitles — yes / no (not offered in
  SONG MODE); (e) thumbnail — yes / no.
  When the topic input is a pasted script, first accept an existing `Title: …`, heading,
  or bare leading title line. If none exists, offer exactly four short titles derived only
  from that script: blunt claim, question, number, and surprise. A hands-off or unanswered
  round takes the first. Lock the title for Phase 8b; never compose a second thumbnail hook.
- **Round 4 — Kids sound mode, only for a Kids run:** skip when SONG MODE is already
  locked. The only Kids sound mode available here is **narrator only**. Talking
  characters (cast dialogue in the clip's own lip-synced audio) is **NOT PORTED** —
  WorkRally's native clip audio and lip-sync are unverified — so there is nothing to ask.
  If the user asks for talking characters, say plainly that it is unavailable on
  WorkRally today and offer narrator-only, then continue.
- **Round 5 — voice (the narrator), LAST — use the canvas audio model fields:**
  SKIP in SONG MODE and on a locked silent cut. Otherwise call
  `canvas_audio_model_list` once. Pick an `audio_models[]` entry that can do text-to-speech
  (prefer `is_minimax: true`; never hardcode a model id). Read that model's `fields` and
  find the field named `voice` (or whose label is 音色 / Voice). Offer those option
  **labels** as the voice picker; lock the option **value** as `voice_id` and the model's
  `model_id` as `audio_model_id`. Write both to `voice.lock` (two lines:
  `model_id=…` then `voice_id=…`). If a MiniMax model has empty `fields`, lock the model
  and generate with its default timbre — say that in one line, do not invent names.
  If `audio_models` has no text-to-speech model, **lock a silent cut** (clips keep their
  diegetic SFX; optional music bed still allowed; subtitles off) and skip this question.
  Never call `voice_list` / `tts_create`. Never ask the user to switch MCP profiles.
  Lead with a ONE-LINE RECOMMENDATION for the channel, described by TIMBRE
  because the available voices differ per environment — never name a voice this skill has
  not seen in the current `fields` response:
  **History → a deep, measured male storyteller; Kids → a warm bright host; Explainer →
  a lively conversational voice; Fairy Tale & Myth → a deep hushed storyteller, or a
  gentle warm one for softer tales; Picture Story → match the tone.** The user still picks
  freely. Do NOT generate voice audition samples, do NOT invent voice descriptions, and do
  NOT offer a voice that is not in the field options. **Record the picked pair — LOCKED for
  the whole video** (rule 15); never re-ask it later. **If the picked voice ERRORS on
  first use: do NOT re-open the question** — call `canvas_audio_model_list` again to recover
  the exact id and retry; re-ask the user ONLY if that voice truly no longer exists.
  Intonation and MOOD live in the script (`${FACELESS_SKILL_DIR}/references/vo_and_captions.md`);
  `canvas_generate_audio` has no `emotion_prompt` — keep `prompt` as the spoken words only.
- **Planning locks do not stop; media reviews do.** STYLE LOCK, SCRIPT LOCK, and
  long-form OUTLINE LOCK remain notification-only. ASSET LOCK is folded into the
  completed IMAGE review. In interactive mode the completed IMAGE, VIDEO, and AUDIO
  stages each show one ledger and stop on their review question.
  These are the only production approval stops. Named failures (retry ladder
  exhausted, assembly assert, BUDGET_CAP) also stop the run. A silent cut has no AUDIO
  review: after VIDEO, go to assembly.
- **AUTO / hands-off mode** (a platform flag, or the user says "no approvals /
  end-to-end / don't ask / 别问了 / 你定" / "pick the voice yourself" / "surprise me"): SKIP
  the intake rounds INCLUDING the voice question — missing parameters take the documented
  defaults: type Explainer, aspect 16:9, subtitles off, thumbnail yes, duration 1 min, and
  the type's default style (Kids → Studio 3D). **VOICE IS NOT ASKED in this mode. Call
  `canvas_audio_model_list`, auto-pick the first MiniMax (else first TTS) model and the
  first voice option whose label matches the channel's recommended timbre above, lock
  both, and name the picked voice in one line.** No TTS model → silent cut, one line.
  Asking in hands-off is a bug. **Stopping for a review
  approval in auto mode is a bug — auto mode exists precisely so the user gives no
  approvals; nothing in it waits.**
- **"Randomizer" topic path:** search the web for what is trending NOW (2–3 angles:
  "trending topics this week {month year}", "most searched questions this week", plus one
  vertical the user cares about if known). A good pick has a **why/how question** at its
  core, one **surprising number or reversal**, strong **visual potential**, broad appeal
  ("Why X is suddenly everywhere", "The real reason X costs so much"). Avoid breaking
  tragedies and active disasters, gossip with no data angle, anything unverifiable by two
  sources. Present the pick + one runner-up on the topic step; proceed with the pick
  unless the user swaps.

**GATE 0:** you have {type, aspect, subtitles y/n, thumbnail y/n,
**either a locked silent cut or `voice.lock` with `model_id` + `voice_id`**, topic, duration, style}. Compute **N = duration_seconds / 10,
rounded half-UP (45s → 5), minimum 3**. If a channel profile was saved earlier (memory /
project notes: style key + voice + type), reuse it and ask only the topic. Style option
descriptions come VERBATIM from the style files' intake one-liners — never improvised,
never naming third-party brands/studios, never promising on-screen text.


### Structured hands-off requests

When the request already supplies a structured brief, treat every supplied value as
locked and skip the matching question. Supported locks are `topic`, `duration_seconds`,
`aspect`, `channel_type`, `voice_id`, `preset`, up to three
`style_reference_urls`, `subtitles`, `thumbnail`, `title`, `music_url`, and
`channel_dna`. Resolve `animation_mode` before all of them. A supplied style reference
URL is authoritative look input; a simultaneous preset is lineage metadata only. A
`style_reference_url` outside WorkRally's `input_images` allowlist must be downloaded and
re-uploaded with `upload_file` first. `talking_characters` is **not supported** — ignore
it and say so once.

Use `N = ceil(duration_seconds / 10)` and keep `requested_duration_seconds` immutable for
assembly receipts. A hands-off request skips media review stops and delivers the
same final file as an interactive run.
