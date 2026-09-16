# Generation and delivery

This reference contains the complete Phase 4–8b contract. Resolve
`FACELESS_SKILL_DIR` (the directory holding the skill's `SKILL.md`) before following any
path below.

## Contents

- Block video generation and review
- Narration through `canvas_generate_audio` `mode:"audio"` (core MCP)
- Local ffmpeg assembly and QC
- Subtitles through local ffmpeg burn (narrated runs only)
- Intake-selected cover through `workrally-thumbnail`
- Delivery

### Hands-off concurrency after SCRIPT LOCK

In explicit auto/headless mode, Phase 4 clips and Phase 5 narration are independent once
the script and assets are locked. Submit both complete waves before polling either, then
poll the two ledgers independently. Never run two attempts for the same index at once.

This does not apply to interactive runs: VIDEO and AUDIO review questions are spending
gates, so an interactive run completes and approves Phase 4 before submitting Phase 5.

### Phase 4 — Generate blocks (one call per block)
Before the first block, call `canvas_video_provider_config` once and pick the model from
what it returns. Require 10-second generation, the chosen 16:9/9:16 ratio, and image
references (`can_upload_image` / `max_image_count`). Read `resolution_options` and take
the highest offered up to `4` (1080P); do not send an enum the model did not declare and
do not silently lower it either — say which档 you got. Never hardcode a model id.

Native audio matters: `support_audio: true` means the clip carries its own diegetic
soundtrack, which is what the AUDIO prompt line asks for. `enable_sound` defaults to
true; pass `false` only to force a silent block. Check the audio that came back, not the
presence of a request flag. Missing audio, or generated speech/music in a narration
block, is a named QC failure: retry that block once, then stop if it remains unusable.
Song mode keeps its own sound rules.

For each block 1..N, one `canvas_generate_video` call:
`model:"<id from canvas_video_provider_config>"`, `mode:"SubjectToVideo"` (the asset
sheets are the reference subjects), `duration:10`, `resolution: 4`,
`aspect_ratio`: chosen aspect, `reference_assets` = location →
characters → props, in that order. **HARD LIMIT: at most 7 image
references per call**, and never more than the model's `max_image_count`. Send
ONLY the assets that appear in THIS block; if a block still exceeds 7, trim in reverse
priority (extra props first, then the spare coverage view) — NEVER drop the block's
location or an on-screen character. The prompt contains the
FIVE timed hard-cut shots (`SHOT 1 0.0–2.0s … HARD CUT … SHOT 2 2.0–4.0s … HARD CUT
… SHOT 5 8.0–10.0s`; Kids: the 4-cut pattern) plus "characters only emote, do NOT talk"
and the diegetic-audio-only line. Full template →
`${FACELESS_SKILL_DIR}/references/prompts.md §3`. Submit the blocks, keep a
`block number → task_id → last state` ledger, and poll each `task_id` with
`canvas_get_task` every 3 seconds. Apply the RETRY
LADDER on a rejected or `state:5` block, resubmitting only the failed block numbers.
**A `state:4` block is FINAL.** Never pause the run to "re-taste" a finished block:
regenerate ONLY on a moderation or generation failure (RETRY LADDER) or on a NAMED gate/QC violation (style
drift vs the assets, static head/tail WARN from the assembler, wrong aspect) — and only
AFTER the whole batch is collected. Do not stop mid-batch to redo a block on preference;
do not resubmit blocks the checklist has no complaint about.
After all N blocks are complete, interactive mode posts the exact final `{index, task_id, result url}` block ledger
in chat, renders the VIDEO review question, and ends the turn; enter the route's
next stage only after `Continue`. Auto/headless mode proceeds immediately
without the list.
**GATE 4 (completeness):** all N blocks are `state:4` and downloaded (`block01..N.mp4`),
one per script block, no gaps. Never proceed with a missing block.

### Phase 5 — Voiceover — `canvas_generate_audio` `mode:"audio"`

Executed inline. **Never** call `voice_list` / `tts_create` / `workrally-narrator`.
A silent cut locked at GATE 0 skips this phase: go to assembly with
`finish_video.sh --no-voice` (clips-only). Subtitles stay off.

Before the first take, read `voice.lock` (`model_id` + `voice_id`) written at GATE 0.
If the file is missing, call `canvas_audio_model_list` again and lock a MiniMax/TTS
model + voice, or fall to silent cut — do not invent ids.

Send every ordinary or `block_kind:"narration"` line with one
`canvas_generate_audio` call (`count: 1`):

- `mode:"audio"`
- `model`: locked `model_id` from `voice.lock`
- `prompt`: the authored `vo_line` **only** (no timecodes, no `[scoffs]` stage directions)
- `audio_field_values: { voice: "<locked voice_id>" }` on MiniMax models; omit `ref_audios`
- `short_series_project_id` when the run already has a 短番 project
- the N block lines, numbered, in order;
- the timing target: **7.8–9.5s of measured speech for every full 10s block**;
- the density target — **characters for Chinese narration** (see
  `vo_and_captions.md §Length`), or 20–23 words for a Latin-script language; Kids use
  the shorter band;
- for a SHORT final block (non-multiple-of-10 duration): that block's own window.

Delivery direction lives in the written line, not in a separate `emotion_prompt`
(this tool has none). One locked voice everywhere. Poll `canvas_get_task` to a
terminal state. Guarantees: MP3 tail-click removal before WAV measurement, speech-length
and `rate=ok` gates, rewriting a line denser/shorter when it misses (NEVER `atempo`),
no internal pause ≥0.8s, RETRY SET LAW, per-line attempt budget. Keep result URLs in
numeric block order and wording synchronized with `script_manifest.json`.

After every narration wave, materialize and measure all final takes in **one local shell
command**. The measurement helper needs ffmpeg, not Whisper; run it even on the declared
missing-Whisper route. Replace the base64 placeholder with the compact current manifest
encoded as base64, list every final completed result URL in numeric block order, and
replace the language placeholder with the run's locked `NARRATION_LANGUAGE` (`zh` for
Chinese narration). The command writes the manifest, downloads and converts every final
result into deterministic `voice01.wav … voiceNN.wav` slots, then verifies them:

```bash
set -e
mkdir -p work/voices
printf '%s' '<script-manifest-base64>' | base64 -d > script_manifest.json
printf '%s\n' '<voice01-result-url>' '<voice02-result-url>' > voice_urls.txt
i=0
while IFS= read -r url; do
  i=$((i+1)); idx=$(printf '%02d' "$i")
  curl -fL --retry 3 --retry-all-errors "$url" -o "work/voices/take$idx.mp3"
  ffmpeg -hide_banner -loglevel error -i "work/voices/take$idx.mp3" -ac 1 -ar 24000 \
    -af 'areverse,atrim=start=0.030,asetpts=N/SR/TB,afade=t=in:st=0:d=0.060,areverse' \
    -y "work/voices/voice$idx.wav"
done < voice_urls.txt
python3 ${FACELESS_SKILL_DIR}/scripts/measure_narration_takes.py \
  --script script_manifest.json --voice-dir work/voices --duration-seconds {requested_seconds}
python3 ${FACELESS_SKILL_DIR}/scripts/verify_takes.py \
  --script script_manifest.json --voice-dir work/voices --language '<narration-language-code>'
```

If Phase 0 selected the missing-Whisper degraded route, do not run this intermediate
`verify_takes.py` command and do not claim that the audio-content gate passed. Still
run `measure_narration_takes.py` in the materialization call: missing Whisper never
waives duration/rate checks. Keep the ordered completed URLs and current manifest for
the final self-contained finisher with `--allow-unverified-audio` and its degraded receipt.

The helper maps each exact `vo_line` to `voiceNN.wav`, skips declared Kids dialogue
and scales the speech window for a short final block. Read its JSON `retry_blocks`,
`overlong_blocks` and `recommended_words`; never hand-build a `speech_metrics.sh --text`
loop. A measured overlong block may use the 17-word retry floor: rewrite that line,
then rerun `validate_motion_script.py --script script_manifest.json --duration-seconds {requested_seconds}`
with `--duration-retry-blocks N,...`. Retain the union of measured overlong block
numbers across retries; all other blocks keep their initial word floor.
Pass `--accept-soft-blocks N,...` to measurement only for 7.2–7.8s takes already
retried once. Re-measure every wave, regenerate only the returned retry indices,
and never change successful takes.

All N files are mandatory even when local measurement was unavailable during
generation. On the normal route, after any line is regenerated, replace only that
index's URL and rerun this whole materialize-and-verify command; never run
`verify_takes.py` in a later call that assumes the downloaded files survived.

The command uses tiny local transcription to catch a provider returning another job's
audio or a take that predates a line rewrite. On non-zero exit, regenerate only the
named mismatching narration indices from the current manifest with the locked voice
pair, then rerun the verifier. A passing take stays immutable. A content mismatch is
never accepted as the "closest" take and never reaches assembly; stop after the bounded
per-line attempt budget instead of shipping the wrong words.

Kids Talking Characters is **NOT PORTED** — WorkRally's native clip audio and on-screen
lip-sync are unverified (mapping doc §9), so there is no route that can put cast dialogue
in a generated block. Every Kids run here is narrator-only.

If this run requires a music bed, generate
it now with `canvas_generate_audio` in `mode:"music"` (before review), not during
assembly. After every take and due bed passes its bounded checks, interactive
mode posts the exact final audio ledger in chat (give a due bed its own unique
stage index), renders the AUDIO review question, and ends the turn; enter assembly only after `Continue`.
Auto/headless mode proceeds immediately without the list.

**GATE 5:** silent cut → no voice files, skip measurement; proceed to `--no-voice` assembly.
Otherwise exactly N numbered voice files, `measure_narration_takes.py` exits zero,
and, whenever `faster_whisper` is
available, `verify_takes.py` exits clean. Every narration block uses the one locked
voice and passes the 7.8–9.5s target (soft 7.2–7.8s only after one retry; hard reject
outside 7.2–9.5s, scaled for a short final block), `rate=ok`, and no
internal pause ≥0.8s. The only degraded exception is the Phase-0 missing-Whisper route: the
single finisher call must include `--allow-unverified-audio`, its
`AUDIO_CONTENT_UNVERIFIED=faster_whisper` receipt is mandatory, and delivery must state
that take content could not be transcribed for verification.
After at most three attempts per line (changed text before a third attempt), stop
with the exact failing slot and metrics if the hard window or delivery gate still
fails. Never ship the closest failed take.

**Picture Story voice = ONE continuous narration, then Whisper (NOT per-beat takes).**
Send the whole narration through `canvas_generate_audio` `mode:"audio"` with the locked
model + voice, chunking it yourself if the text is too long and joining the chunks
losslessly with ffmpeg `concat` (no re-encode, no crossfade) into one `narration.wav`,
then the frame timeline comes from Whisper word timestamps per
`${FACELESS_SKILL_DIR}/references/picture-flow.md` Phase 5 / 5b: segments every
~0.7–1.2s, and at each framing change; no frame
segment >1.5s). Those Whisper timings set every frame's duration in Phase 6.
No TTS model → Picture Story cannot run; say so and offer a motion channel instead.
NOTE (feedback to backend): `validate_picture_story_audio.py` is the OLD per-beat audio
gate (rejects takes >3.0s, expects one take per beat) — it does NOT apply to a single
continuous narration and is NOT run in this model. It needs a rewrite to validate the
frame timeline (sum of frame durations ≈ narration length, max-hold ≤1.5s) — the
assembler's `--audio` mode already asserts exactly that, so the check is covered until
the validator is updated.

### Phase 6 — Assemble in the local shell → ONE final video

**Canonical motion-video route:**

1. Keep every completed video and audio task's result URL in block order.
2. Run the wrapper once in the local shell. It writes ordered `clips.txt` and
   `voices.txt` URL lists plus `script_manifest.json`, revalidates the script, assembles,
   burns captions when asked, and verifies every output. Nothing is uploaded here:
   the deliverable is a local MP4.
   ```bash
   set -e
   printf '%s\n' '<clip01 url>' '<clip02 url>' > clips.txt
   printf '%s\n' '<voice01 url>' '<voice02 url>' > voices.txt
   printf '%s' '<script-manifest-base64>' | base64 -d > script_manifest.json
   python3 ${FACELESS_SKILL_DIR}/scripts/validate_motion_script.py \
     --script script_manifest.json --duration-seconds <requested-seconds>
   bash ${FACELESS_SKILL_DIR}/scripts/finish_video.sh \
     --blocks N --clips-file clips.txt --voices-file voices.txt \
     <optional --subs clean|paper|bold> <optional --allow-unverified-audio> \
     --script script_manifest.json --language '<narration-language-code>' \
     --out work/output/final.mp4
   test -s work/output/final.mp4
   ```
   `<script-manifest-base64>` is the compact current validated manifest encoded as
   base64. `--subs` makes the SAME call do Phase 7 (see below): it assembles the
   immutable `final_clean.mp4` master first, then burns captions from it into
   `final.mp4`. Without `--subs`, `--out work/output/final.mp4` is the clean master and
   is the deliverable. Add `--music URL|FILE` and `--stepped 12` only when applicable.
   `--allow-unverified-audio` is allowed only after the Phase-0 `faster_whisper` import
   retry failed; require the matching `AUDIO_CONTENT_UNVERIFIED=faster_whisper` receipt
   and disclose the degraded verification state with the deliverable. When the import
   succeeds, omit the flag and keep take verification fatal.
   The run can take minutes — start it in the background and poll its log; never launch
   a second assembly while the first is alive.
3. The wrapper downloads `block01.mp4 … blockNN.mp4` and
   `voice01.wav … voiceNN.wav`, writes `pairs.txt` in strict numeric order, runs
   the canonical assembler, and verifies every output. Read its `RECEIPTS` block:
   it names the MP4, the poster and the assembly sidecar, and flags a degraded
   audio check.
4. Put the finished file into the WorkRally media library only when the user asked for
   it (or a later WorkRally step needs an `asset_id`):
   ```
   upload_file(file_path="<abs path>/work/output/final.mp4")   → CDN url
   asset_create(asset_url=<url>, project_id=<短番项目ID>)        → asset_id
   ```
   Keep `final_clean_poster.jpg` and `final.mp4.assembly.json` as assembly receipts.
   If an upload fails, the local file is still the deliverable — say so, do not rerun
   assembly.

Local FFmpeg assembly is self-contained and does not need a remote generation record.
There is no core-MCP tool that stitches clips with centered narration; the assembler
is the only path that upholds the gates. **Do not call `video_concat`.** Missing ffmpeg
is a hard stop.

A silent cut uses the same wrapper without voice URLs:

```bash
bash ${FACELESS_SKILL_DIR}/scripts/finish_video.sh \
  --blocks N --clips-file clips.txt --no-voice \
  --out work/output/final.mp4
```

`--no-voice` is mutually exclusive with `--subs`. Optional `--music` still applies.

**Canonical motion / Picture Story scripts under the wrapper:** run
`bash ${FACELESS_SKILL_DIR}/scripts/assemble_final.sh` once
for motion blocks or
`bash ${FACELESS_SKILL_DIR}/scripts/assemble_slides.sh` once
for Picture Story. Every motion run
writes a MANIFEST first (one
`blockNN.mp4 voiceNN.wav` pair per line, in order) and passes the expected block
count — `--blocks N` is REQUIRED (the script refuses to start without it) and a
missing, extra, or number-mismatched pair is a hard fail:
```bash
bash ${FACELESS_SKILL_DIR}/scripts/assemble_final.sh --out work/output/final_clean.mp4 \
  --blocks N --manifest pairs.txt --script script_manifest.json
```
Add `--music bed.mp3` and `--stepped 12` only when applicable.
(**pass `--stepped 12` for Fairy Tale & Myth / any Cinematic Storybook run — the
on-twos cadence**; positional pairs remain for ad-hoc debugging only. Captions are not
burned by the assembler — `finish_video.sh --subs` does that from the clean master.)
**NO chunked assembly** — never split a long run into "chunks of 10" with your own
ffmpeg, never build the audio track separately, never re-mux by hand: one script call
does all N blocks, however many there are. **NO invented progress reports:** the only
legitimate assembly status is the script's own stderr (per-block lines + asserts) —
paste it; fabricating "chunk 6 assembling, ~7 minutes remaining" tables while nothing
runs is lying to the user and grounds for a failed run.
Run the assembler in the background and poll its log. If it is demonstrably alive, keep
polling that process; never launch a duplicate assembly.
The script does everything and guarantees the hard parts: fixed **N×10s** length, each
voice CENTERED in its 10s block, NO atempo, NO leading freeze, ONE output file, + optional
low music bed and `loudnorm -16 LUFS`. Diegetic SFX already live in the clips. Music bed
when the user supplied a file or explicitly asked — PLUS any KIDS-LOOK run (the Kids
channel, or ANY channel in a Kids-catalog style) AND every FAIRY TALE & MYTH /
Cinematic Storybook run, where a wordless bed is ON BY DEFAULT. No file needed: a due
bed was GENERATED before the AUDIO review with `canvas_generate_audio` in `mode:"music"` at the VIDEO's exact
duration (the per-request duration ceiling is whatever the chosen audio model reports —
read it, do not assume; longer runs join parts into one file — mechanism in
`${FACELESS_SKILL_DIR}/references/kids-styles.md §Kids music bed`). **Mood by channel: Kids = playful/bouncy;
Fairy Tale & Myth = MYSTERIOUS-CALM dark-enchanted ambient** (never bouncy —
`${FACELESS_SKILL_DIR}/references/style-cinematic-storybook.md §Music`). user file → generated bed →
generation failed = ship without + say so in one line. Pick the bed model from
`canvas_audio_model_list` and submit it as `canvas_generate_audio` `mode:"music"`; never
use the TTS path for music. **Default-bed level: `--music-vol
0.05` for Kids, `0.09` for Fairy Tale & Myth** (the narration must never fight the bed)
— and the assembler additionally DUCKS the bed under speech (sidechain keyed by the voice). Never block delivery on a bed, never
synthesize music with the speech model. Do NOT split into parts, do NOT re-encode by
hand, do NOT trim to the audio.
Besides the MP4 the script writes two platform artifacts next to it — keep both:
`final_clean_poster.jpg` (the result thumbnail) and `final_clean.mp4.assembly.json` (the machine-
readable ASSEMBLY SIDECAR: block count, per-block speech metrics, gates passed — the
proof the final went through the script; `assemble_slides.sh` writes the same pair).
**GATE 6:** exactly ONE `final_clean.mp4`, duration = N×10s (±1s, the script asserts this),
narration present in EVERY window (the script asserts this too — a "silent second half"
cannot pass), plays from frame 1 (no static head), one voice, SFX under the voice (music
only if provided), poster + assembly sidecar present next to the MP4.

**Picture Story assembly command** (frame-by-frame `--audio` mode; `--blocks` = the
FRAME count, not the billing count):
```
bash ${FACELESS_SKILL_DIR}/scripts/assemble_slides.sh \
  --out work/output/final_clean.mp4 --audio work/voices/narration.wav \
  --blocks {FRAME_COUNT} --timeline scene_manifest.bound.json --frames-dir work/frames \
  --requested-seconds {REQUESTED_SECONDS}
```
Prefer running this through `finish_video.sh --stills` so the same gates and receipts
apply. Before it, materialize the current base64-encoded script manifest and
rerun `validate_picture_story.py`, write the unbound `scene_manifest.json`, bind the
completed indexed results to `scene_manifest.bound.json`, materialize every frame from
that bound manifest's durable result URLs, and download the final continuous narration
URL. When subtitles are enabled, pass `--subs` to `finish_video.sh` so it transcribes
`work/voices/narration.wav` and burns from the clean master.
Add `--music bed.mp3` only when applicable.
`scene_manifest.json` is the unbound manifest v2 produced from Whisper words by
`build_scene_timeline.py`. `scene_manifest.bound.json` is the only assembly input: it is
bound to the actual indexed task results by `bind_scene_frame_results.py` and atomically
restored into `work/frames` by `materialize_scene_frames.py`. Never invent durations or
rename by completion order.
The one continuous narration is laid over the whole cut. The script asserts the
per-frame durations sum to the narration length (±1.5s), **frame numbers strictly
ascending with no gaps (a jumble hard-fails — the "assembled out of order" bug)**,
max-hold ≤1.5s/frame, **a DENSITY FLOOR
of `ceil(narration_sec/1.5)` frames (≈40 for a minute — a slideshow like 15 frames/min
hard-fails; generate the dense set in Phase 4, do not pad holds)**, aspect, 1080p cap,
narration present, full decode. Block accounting stays `ceil(requested_seconds/10)`
(NOT the frame count) — the sidecar records both `frames` and the billing blocks.
NOTE (feedback to backend): the old `--target-duration` per-beat total-duration gate is
replaced by the `--audio` sum-of-durations assert.

### Phase 7 — Subtitles — local ffmpeg burn (only if subtitles = yes)

**WorkRally has NO caption-burning tool.** `canvas_generate_video` only *erases*
subtitles (`enable_erase_subtitles`). Burning therefore happens entirely in the local
shell, with the scripts bundled under `${FACELESS_SKILL_DIR}/scripts/subtitles/`:

- `audio_to_captions.py` — Whisper word timestamps → `.srt`, with authored-wording
  substitution and the ≤5 words / ≤32 chars sizing;
- `burn_caps_clean.sh` — the `clean` / `bold` burner (libass, no plate);
- `subtitle_paper_burn.py` — the `paper` burner (torn cream label, handwritten);
- `fetch_fonts.sh` — idempotent, non-fatal per face.

Captions are never hand-timed. `finish_video.sh --subs <look>` chains all of it in one
call: it assembles the immutable `final_clean.mp4`, transcribes the per-block voice takes
(or the continuous `narration.wav` for Picture Story) against `script_manifest.json`,
writes `final.srt`, burns, and probes the result. Never pass `--subs` to either assembler
directly and never use a previously captioned video as burn input.

The LOOK: `clean` (default — slim white CAPS, tiny, bottom ~12%, no plate),
`paper` (torn cream label, handwritten — fits fairytale/storybook looks) or
`bold` (ALL-CAPS with platform safe zones). Channel default: Fairy Tale & Myth →
`paper`, everything else → `clean`, unless the user asked otherwise.

**Chinese captions:** pass `--no-caps` through to the burner — forcing uppercase is
meaningless for Chinese and `Bold=1` on a fallback face reads worse. None of the fetched
faces covers CJK, so libass falls back to a system CJK font; on a machine with no CJK
font installed the labels come out as boxes. Check one burned frame before delivering,
and if the glyphs are missing either point `--font` at a local CJK face
(`PingFang SC`, `Noto Sans SC`, `Source Han Sans`) or deliver the clean cut and say
captions could not be rendered. Never ship a video full of tofu boxes.

If Whisper is unavailable, `audio_to_captions.py` exits 2 and `finish_video.sh` delivers
the cut **unsubbed** with a `WARN` in its receipts — relay that to the user. Do not guess
timings, and do not claim the clean copy contains captions.

**Non-negotiables that stay TRUE regardless of who asks:** timings come from
Whisper ONLY — even if the user says "time them from the script" (rule 8); captions
stay small and out of the way (rule 20).

Keep `final_clean_poster.jpg` extracted from the CLEAN video (Phase 6 does this before
captions) — a result card must never show a random subtitle fragment.

**GATE 7:** one `final.mp4` with Whisper-timed captions whose glyphs actually rendered,
or an explicit note that captions were unavailable.

> **Whisper normally serves both narrated-motion take verification (Gate 5) and
> subtitles (Phase 7).** A/V sync is by construction (one centered narration line per
> block — Phase 5/6). If Whisper remains unavailable after the one retry, the explicit
> `--allow-unverified-audio` route may deliver the clean cut without captions, but it must
> report and disclose that take content was not transcribed. Never ship guessed caption
> timings or claim the content gate passed.

### Phase 8 — Native resolution, no automatic upscale

Deliver the cut at the resolution the blocks were generated at (`resolution: 4` = 1080P
by default; higher only if the chosen model's `resolution_options` offer it). Never
downscale and never re-encode "for compatibility". **Do not call `toolbox_manage` or
offer a server-side upscale.** Picture Story keeps its 1080P stills output and never
touches the video model.

### Phase 8b — Generate the thumbnail only when the cover answer was yes

Run only when the locked intake answer is `thumbnail: yes`. Hands-off runs resolve an
unanswered thumbnail round to the documented `yes` default. A request for exactly one MP4
or one finished video constrains the video-file count only; it is not a thumbnail decline.
Only an explicit “no thumbnail” / “no cover” locks `thumbnail: no`. The cover is an
additional still-image deliverable; failure never blocks or delays the validated video.

Invoke the installed `workrally-thumbnail` skill with a complete locked handoff assembled
only from this run:

- **Reference image:** the Phase-1 style key and explicit `贴近这张参考` intent. That skill
  analyses a reference cover with its own eyes and never puts it in `input_images` — the
  style key is a look brief here, not a generation input.
- **Hook title:** for a pasted script, use the exact title locked at intake. For idea and
  research paths, derive one exact promise in the video's language and channel register
  from the current script manifest (2–14 characters for Chinese, 3–6 words for a
  Latin-script language). Let the thumbnail skill bake it with its local text-overlay
  script — that is its default and it is deterministic.
- **Scene:** one sentence carrying the episode hook and topic, not the full script.
- **Identity:** up to three recurring character images from the current asset roster. If there
  are none, lock a people-free concept. Never invent a photoreal person.
- **Aspect:** `16:9` even when the video is vertical.
- **Medium:** the exact locked illustrated medium, materials, and palette from this run.
- **Variant count:** one. Do not reopen match mode, character choice, text mode, or count.

The delivered cover must carry the exact hook. Validate it character-for-character.
Retry the handoff once when a required field was omitted or stale.

If cover generation still fails, use the poster frame the assembler already wrote:
`final_clean_poster.jpg` sits next to the MP4. If it is missing, extract a frame near one
second with ffmpeg and verify the JPEG. Record `thumbnail_source:"generated"` or
`thumbnail_source:"poster_frame"` and the local path (plus the CDN URL when the user asked
for it to be uploaded).

**GATE 8b:** when the locked cover answer was yes, one cover file exists and every value came
from this run's script manifest, style key, and asset roster rather than memory of another run.

The terminal deliverables are the final video from Phase 6 or 7 and, when selected, the
Phase-8b cover. Deliver both together, as local paths — plus CDN URLs when the user asked
for the media library. Keep the script, asset, assembly, subtitle, and thumbnail receipts
on disk for the rest of the session; they are diagnostic evidence, not a delivery API.
