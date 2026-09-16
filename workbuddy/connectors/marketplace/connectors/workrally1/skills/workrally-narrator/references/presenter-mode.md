# On-screen narrator — video + photo in, narrated video out

Use this mode only when the request supplies an existing video and asks to place the
person from a photo on-screen as its narrator. The photo must depict the user or another
consenting non-public person. This is a video workflow: never substitute audio-only Mode
A, a static image overlay, or a hand-written chroma-key command.

Read `../../../references/workrally-mcp-mapping.md` first — tool names, model lookup,
resolution enums and the `sandbox_exec` → local shell rule all live there.

## Locked contract

- Preserve the base video's picture and cover its full duration by default.
- One 10-second generation = one presenter line. Use `ceil(base_duration / 10)` blocks;
  fewer blocks require an explicit test-range request. When the final base window is shorter
  than 10 seconds, generate and trim the normal 10-second talking clip to the measured
  final-window duration before compositing it.
- Supplied script text is authored text. Split it only at sentence boundaries and keep every
  word in order. Budget roughly 3.1–3.5 words per second for latin scripts and roughly
  4.5–5.5 characters per second for Chinese: 31–35 words (or 45–55 characters) for each full
  block and proportionally fewer for a partial final window. If its length cannot fit that
  grid, report both counts and ask whether the base duration or covered range should change.
- Without supplied text, transcribe the base video in the LOCAL shell with `faster_whisper`.
  WorkRally has no video-analysis tool, so scene structure is not available: if
  `faster_whisper` is missing, ask the user for the script text instead of guessing.
- Lock one narrator identity for Mode A via `canvas_audio_model_list` fields. Mode B
  talking clips do **not** use a library voice: native clip audio decides the timbre.
  Never call `voice_list`.
- **There is no `voice_change` equivalent in WorkRally.** The talking clip's voice is
  whatever the video model's native audio produced. See "Voice on the talking clip" below.

## Voice on the talking clip

Higgsfield generated a silent-timbre talking clip and then swapped the timbre with
`voice_change`, which preserved clip timing. WorkRally has no such tool, so:

1. Choose a video model whose `canvas_video_provider_config` entry reports
   `support_audio: true` and leave `enable_sound` at its default (`true`). The clip then
   carries native speech, and the model — not a TTS voice picker — decides the timbre.
2. Verify each clip: it must contain an audio stream, run the full block duration, and
   speak the block line. `ffprobe` the stream and listen/inspect before accepting.
3. If native audio is unavailable, mute, or says the wrong words, **stop and say so**.
   Do not fabricate a replacement. The honest degradations, in order of preference:
   - deliver the base video plus a separate narration track built with Mode A
     (`canvas_generate_audio` `mode:"audio"`), and let the user decide about compositing;
   - deliver the base video untouched and report that on-screen presenter mode needs a
     video model with working native speech in this environment.
   Never composite a silent presenter and call it narrated.

Native lipsync and native audio quality are **not yet verified** on WorkRally (see the
"已知缺口" table in the mapping doc). Treat every presenter run as needing a human look at
the result before delivery.

## Pipeline

1. **Resolve inputs.** For a local video or photo, call `upload_file` on each to get a CDN
   URL, then `asset_create` when the file must land in the media library. Keep the URLs.
   When the request supplies only an asset id with no URL, ask for the URL or the file
   again — WorkRally has no media-listing tool to look one up, and guessing from recency is
   forbidden. Probe the video duration in the local shell (`ffprobe`). Survey its audio: a
   mono mix means original speech and music cannot be separated safely, so disclose that
   the original audio will be dropped.
2. **Make one green-screen identity reference.** Call `canvas_image_model_list`, pick a
   model whose `kontext_config.max_input_images >= 1`, and submit one
   `canvas_generate_image` with `count: 1`, `aspect_ratio: "9:16"`, `resolution: 4` (1K,
   or that model's nearest supported option), the photo URL in `input_images`, and
   `quality: "medium"` only when the model's `infer_quality_options` is non-empty. Poll
   `canvas_get_task` every 3 seconds. On two failures or a safety rejection, retry the same
   prompt on a different model from the same list — never on a hardcoded model id.

   Prompt (Chinese; WorkRally's main models are Chinese-language):

   ```text
   编辑第一张图片。人物必须完全保持原样——同一张脸、同样的发型、服装、肤色、姿势与取景，
   忠实复制，不要美化，不要换成相像的另一个人。只改一件事：把人物身后的背景整体替换为
   完全均匀的纯色绿幕（#00B140），布光均匀，没有渐变、阴影或暗角，铺满人物之外的全部区域。
   人物身上不要有绿色溢色；发丝边缘保持干净。
   ```

3. **Generate every talking block.** Read `canvas_video_provider_config`, pick a model with
   `support_audio: true` and a `max_video_duration` of at least 10 seconds. Submit one
   `canvas_generate_video` per block with `mode: "Text"`, `single_image_url` set to the
   completed green-screen image URL, `aspect_ratio: "9:16"`, `duration: 10`, and
   `resolution: 3` (720P, or that model's nearest option). Poll `canvas_get_task` every 3
   seconds. Keep completed blocks frozen and retry only failed ones, at most twice.

   Prompt template (Chinese):

   ```text
   身份参考（只用于外观，不是首帧）：忠实复制第一张图片里的人物与纯绿色背景。
   第一帧就已经在说话中，不要静止起手。人物看着正前方的镜头，用<语气>说<语言>：
   "<该块台词，逐字照抄，整块约 31–35 个英文词或 45–55 个汉字>"。
   每个字只说一遍，语速稳健偏快，说完保持平静专注的表情。最后一个不足 10 秒的窗口，
   台词按那个窗口的长度写，即使模型出的片子仍是 10 秒。镜头固定；只有自然的头部与
   肩部小幅动作。音频只有清晰的人声。背景保持均匀鲜亮的绿色。不要重复或即兴加词，
   不要字幕、不要水印、不要运镜、不要美颜、不要换背景、不要静止开场。
   ```

4. **Verify the audio on every completed clip** as described in "Voice on the talking clip".
   A block with no audio stream is a failed block, never a deliverable one.
5. **Composite and export in the LOCAL shell.** Do not look for `sandbox_exec`.
   - download the base video and every completed talking-clip URL;
   - cut the base into ordered windows of at most 10 seconds as `blkNN.mp4`; measure the last
     window exactly and, when it is partial, trim both audio and video of `talkNN.mp4` to that
     duration before compositing (do not pad, loop, or leave the generated 10-second tail);
   - run the bundled script once per block, never a custom key:
     ```bash
     bash <skill 目录>/scripts/presenter_composite.sh \
       blkNN.mp4 talkNN.mp4 outNN.mp4 --style cutout --pos br
     ```
   - require each `outNN.mp4.qc.json` to contain `result:"PASS"`; concatenate the ordered
     outputs, probe audio/video/duration, require the joined result to match the measured base
     duration within 0.1 seconds, and create one representative-frame contact sheet;
   - use `badge` instead of `cutout` when fine hair has a ragged/green edge or a close-up crop
     reads badly. Never tune chroma thresholds by hand.
   - the script needs `ffmpeg`, `ffprobe`, `python3` with Pillow + numpy. It refuses to run
     without them; install them or degrade honestly (see the SKILL's dependency section).
6. Inspect the contact sheet: the presenter is opaque, fully inside the frame, clean-edged,
   and never covers the important base-video content. A QC failure regenerates/recomposites
   only the affected block. The deliverable is the local MP4; put it in the media library
   with `upload_file` + `asset_create` only when the user wants it there.

## Delivery gate

Deliver the composited MP4 and report the block count, covered duration, presenter
position/style, whether original audio was dropped, and **which voice the video model
produced** (WorkRally cannot swap it afterwards). When supplied lines were used, verify
every sentence survived in order with nothing invented. Offer burned captions separately
via the `workrally-subtitles` skill; do not add them silently.
