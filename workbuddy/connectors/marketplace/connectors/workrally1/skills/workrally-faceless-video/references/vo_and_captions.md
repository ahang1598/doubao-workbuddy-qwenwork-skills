# vo_and_captions.md — fixed-window canvas TTS + local caption burn

## Voiceover — `canvas_generate_audio` `mode:"audio"` · ONE LINE PER BLOCK
- **One narrator voice for the whole video — call `canvas_audio_model_list` at intake.**
  Pick a text-to-speech `audio_models[]` entry (prefer `is_minimax: true`). Offer that
  model's `fields` voice-option labels in one question (no generated audition samples),
  with a one-line channel recommendation described by TIMBRE, never by a voice name this
  skill has not seen in the current fields: **History → deep, measured storyteller · Kids →
  warm bright host · Explainer → lively conversational · Fairy Tale & Myth → deep hushed
  storyteller · Picture Story → match the tone.** The same rule drives the auto-pick for
  hands-off runs. Record `model_id` + `voice_id` in `voice.lock` and use them on EVERY
  line — never let lines come out in different voices; a take that comes back in a
  different timbre is a failure → regenerate with the locked pair.
  No TTS model → silent cut (see intake). Never call `voice_list` / `tts_create`.
- Each line is one `canvas_generate_audio` call: `mode:"audio"`, locked `model`,
  `prompt` = authored words only, MiniMax `audio_field_values.voice` = locked id,
  no `ref_audios`. Poll `canvas_get_task`. Optionally pass `short_series_project_id`.
- **Intonation & mood live in the SCRIPT, not in the voice:** fit delivery to the channel
  type + topic (sombre topic → measured wording, fewer gags; playful → lighter lines).
  The voice never changes mid-video. This tool has no `emotion_prompt` — do not paste
  stage directions into `prompt`.
- **Kids call-and-response:** the narrator addresses characters and the viewer by name
  ("Say hi to Masha!", "Can YOU count the apples?") and the video stages the visible
  reaction (see kids-styles.md). Questions go at the END of a line — the block boundary
  IS the answer beat, and the next line opens with the payoff ("That's right — three!").
  Never leave a ≥0.8s pause inside a line for the answer. Narrator-spoken sound-words
  ("whoosh!", "ding!") and catchphrases count as words in the Kids 17–21 budget.
- **One spoken line per block** (block N → `voiceNN.wav`). No timecodes, no big continuous
  chunk, no `adelay` juggling. One line = one 10s scene → perfect sync by construction.
- **Line prompt format — spoken words only:** `canvas_generate_audio` has no bracket
  syntax and no timecode window. `prompt` carries the authored words **only**. Never paste a
  `[00:00-00:09]` bracket or `[scoffs]`-style stage direction into `prompt`: the original
  provider read those as performance cues; this tool reads them as words to speak.
- **Measured retries:** the initial budget is not an unbreakable retry floor.
  After converted WAVs exist, run `${FACELESS_SKILL_DIR}/scripts/measure_narration_takes.py`
  with `--script script_manifest.json --voice-dir work/voices --duration-seconds {requested_seconds}`
  in that same call. For measured overlong slots only, follow `recommended_words`
  and revalidate with the cumulative `--duration-retry-blocks` set (Chinese 30-character /
  Latin 17-word floor per full block). Passing takes are immutable. Soft 7.2–7.8s is
  accepted only after one retry; a hard miss after three attempts is a failure, not a
  deliverable.
- **Length: each line should naturally fill most of its block** (the assembler CENTRES
  detected speech inside the block, ignoring the file's edge silences). Write
  **34–42 characters of Chinese** (Kids 28–36), or 20–23 words for a Latin-script
  language (Kids 17–21), comma-light, at most TWO sentences. Enforce
  **7.8–9.5s detected speech**, `rate=ok` and **no internal pause ≥0.8s** —
  the assembler flags pausey takes (WARN with the pause
  length); rewrite flowing and regenerate, don't ship stalls. Warmth for Kids = word
  choice, not pauses (`${FACELESS_SKILL_DIR}/references/kids-styles.md §Kids voice pace`).
  The Chinese band and the `rate` thresholds behind it are **derived from the speech
  window at ~4.0–4.6 characters/second, not measured on WorkRally's TTS** — recalibrate
  from `measure_narration_takes.py` output once real takes exist, and do not present the
  derived numbers as measured ones.
  Convert each returned MP3 with the reverse-trim/fade recipe in
  `generation-and-delivery.md` Phase 5 before measurement. **If detected speech exceeds
  its block or `rate=RUSHED` → rewrite it shorter and regenerate. NEVER `atempo` /
  speed-up / slow-down / pitch-shift** to fit. Do NOT touch `speed` unless asked.
  A clearly sparse first take should be rewritten denser; after the bounded retry
  budget, fail any take that still misses the hard window or delivery gates. Prefer one
  flowing clause over clipped sentences and keep punctuation sparse: TTS pauses at every
  full stop and comma, so fewer of them both shortens the take and removes the pausey feel.
- Open with a hook question when asked. Numbers spelled out as words, never digits.
  Characters never lip-sync (external narrator).

## Assemble
In ordinary motion-video runs, download completed block and narration results
as ordered `blockNN.mp4` / `voiceNN.wav` pairs inside the local shell, write
`pairs.txt`, and run
`${FACELESS_SKILL_DIR}/scripts/finish_video.sh` with ordered
clip/voice URL files. Its motion path calls
`${FACELESS_SKILL_DIR}/scripts/assemble_final.sh --out work/output/final.mp4 --blocks N --manifest pairs.txt
[--music bed.mp3] [--stepped 12]`. This local FFmpeg script is the canonical path,
not a fallback.
`--blocks N` is REQUIRED and the manifest is written for EVERY run (mispaired or
missing lines are hard fails). Captions are NOT part of assembly — `finish_video.sh --subs`
burns them from the clean master afterwards. The assembler centers each narration line in
its fixed block,
concatenates to **N×10s** (never shortened), and enforces the LEVEL LAW: voice 1.0
always, the clips' diegetic SFX kept under it at ~0.12, optional music bed at ~0.10
generic / **0.05 for the kids-look default bed**, DUCKED under speech by a
sidechain keyed on the voice (both hard-clamped ≤0.20) + `loudnorm -16 LUFS`;
outputs ONE file with no leading freeze. Diegetic SFX already live in the clips (whooshes, sparkles for Kids). Music
bed when the user supplied a file or explicitly asked — PLUS the Kids channel, where
a wordless bed is ON BY DEFAULT. A due bed needs no file: it is GENERATED before
the AUDIO review with
`canvas_generate_audio` in `mode:"music"` at the VIDEO's exact duration (the per-request
duration ceiling is whatever the chosen model reports — read it, do not assume;
longer = join parts; `${FACELESS_SKILL_DIR}/references/kids-styles.md §Kids music bed`); otherwise run
without `--music` —
voices + the clips' diegetic SFX are the mix. Never block delivery on a bed, never
substitute the speech model for music (`canvas_generate_audio` `mode:"audio"` speaks;
`mode:"music"` plays the bed).

## Subtitles — LOCAL ffmpeg burn (there is no WorkRally caption tool)

WorkRally only *erases* subtitles (`canvas_generate_video`'s `enable_erase_subtitles`).
Burning is entirely local, and the burners ship inside this skill at
`${FACELESS_SKILL_DIR}/scripts/subtitles/`. `finish_video.sh --subs <look>` chains the
whole thing in one call: assemble the clean master → Whisper-time the per-block voice takes
(or the continuous `narration.wav`) against `script_manifest.json` → write `final.srt` →
burn → probe.

- the look: `clean` (default) · `paper` (torn cream label, handwritten — storybook
  tones) · `bold` (ALL-CAPS with platform safe zones);
- `script_manifest.json` is the AUTHORED WORDING (Whisper stays the clock — every
  displayed word comes from the exact `vo_line` / `phrase`);
- sizing: Chinese ≤14 characters per caption, Latin ≤5 words / ≤32 characters;
- Chinese never gets uppercased — `--language zh` implies `--no-caps`.

Two things stay non-negotiable no matter who asks: **timings come from Whisper only**
(never from the script, never estimated) and **captions stay small, single-line and out of
the way**.

**The CJK glyph trap.** None of the fetched faces covers Chinese, so libass falls back to a
system font. On a machine with no CJK font the labels burn as tofu boxes and nothing errors
out. Look at one burned frame before delivering; if the glyphs are missing, pass
`--sub-font "PingFang SC"` (or another local CJK face) or deliver the clean cut and say
captions could not be rendered.

If Whisper is unavailable, `audio_to_captions.py` exits 2 and `finish_video.sh` delivers the
cut unsubbed with a WARN in its receipts — relay that to the user rather than guessing
timings.
