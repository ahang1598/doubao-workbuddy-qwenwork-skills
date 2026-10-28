---
name: media-generation-ecommerce
version: 1.8.0
description: Generate or edit ecommerce images, generate videos from text, a first frame, first and last frames, or reference images, and create music as asynchronous media artifacts. Use for product images, scene and selling-point images, image editing and variations, masked edits, text-to-video, animating an image, first-and-last-frame video, reference-image video, songs, soundtracks, and model selection for supported media, and whenever another ecommerce skill hands over image, video, or music task sheets. Multi-output work such as image sets, detail pages, platform asset packages, or multi-SKU sets is planned by the calling ecommerce skill; this skill executes each media task. Not for text-to-speech or editing an existing video while preserving its frames or audio.
description_zh: 生成或编辑商品主图、场景图、卖点图和其他图片；根据文字、首帧、首尾帧或参考图生成新视频；生成歌曲或配乐；执行其他电商技能交来的图片、视频、音乐任务单。套图、详情页、平台素材包、多 SKU 等成套任务由对应的电商业务技能先出计划，再由本技能逐项执行。不用于文字转语音，也不用于要求保留原片画面和音轨的视频剪辑。
license: Proprietary
---

# Media Generation

Use the built-in media tools below. Do not invoke a media provider directly and do not use text-to-speech for music requests. Do not invoke native `ImageGen`/`image_gen` or `WebSearch`/`web_search`/`websearch` tools; use the canonical tools below. The `web_search` parameter in a media tool is a grounding option, not a tool name.

## References

Read the matching reference files in full before the first submission they apply to. Paths are relative to this skill's directory.

| Read | When |
| --- | --- |
| `references/model-routing.md` | Before choosing a model for any image or video task, unless the model is already locked by the user or a task sheet (still check its hard constraints there). |
| `references/image-rules.md` | Any image task: visible-text rendering and language, text overlay on a base image, prompt hand-off, parameter inheritance, sample-to-batch work, failures. |
| `references/mask-edit.md` | Any user selection or mask, or a request to change only a located region. |
| `references/video-rules.md` | Any video task: plan-or-generate, defaults, guardrails A–D for references, input preprocessing, locked plans, high-risk requests, failures. |
| `references/video-prompts.md` | Writing or restructuring a video prompt, audio or on-screen text, or naming several reference images. |
| `references/video-constraints.md` | Checking a video duration, resolution, ratio, seed, or reference-image limit. |

## Before submitting

- If the user asks only for a plan, script, model recommendation, or capability explanation, answer that request without submitting a media task. A later request to generate from an agreed plan authorizes submission.
- Keep the user's latest approved content, asset roles, output count, visible text, format, aspect ratio, resolution, duration, and audio requirements. Do not quietly replace an unsupported requirement with a different specification. Treat the capability tables in this skill as the packaged reference; check the currently visible tools and their schemas before submitting, and explain a material limitation when it prevents the requested result. If a submit tool is unavailable, explain that this session cannot perform that media task.
- The video path documented here uses reference images. If the current tool schema also exposes reference video or audio, check its semantics and limits before using it; otherwise use the media-understanding and keyframe path in `references/video-rules.md`. Treat changes or continuation as generation of a new clip. Do not promise preservation of source frames or audio, seamless extension, exact spoken words, lip sync, or subtitle timing from a single generation call.

## Required workflow

1. Choose exactly one submit tool:
   - Image generation or editing: `qwenwork_image_generate`
   - Video: `qwenwork_video_generate`
   - Music: `qwenwork_music_generate`
2. Keep the returned `task_id`.
3. Classify the generated files before waiting:
   - Use `artifact_purpose: "deliverable"` when the files directly satisfy the user's request.
   - Use `artifact_purpose: "intermediate"` when the files are inputs to a later conversion, composition, edit, or other transformation. For example, an MP4 generated only to create a requested GIF is intermediate; an MP4 explicitly requested by the user is a deliverable.
4. Call `qwenwork_media_task` with `action: "wait"`, that `task_id`, the chosen `artifact_purpose`, and a friendly semantic `output_name`.
5. When `wait` returns `success: true`, follow `should_present`:
   - If `should_present: true`, call `qwenwork_file_present_files` with every path in `files`.
   - If `should_present: false`, use the files only as working inputs and continue producing the requested final artifacts.
6. Only after the final deliverable files are presented successfully, tell the user the requested media artifacts are ready.

The submit tools are asynchronous. Never describe a submitted task as a completed artifact.

## Requests from other skills

Ecommerce workflow skills, including user-installed ones, may hand their media work to this skill. They describe the work with task sheets and capability names instead of tool names. Handle them as follows:

- A task sheet (图片任务单, 视频任务单, or 音乐任务单) is a JSON object that uses the field names of the matching submit tool: `qwenwork_image_generate` for `mode: "generate"` or `"edit"`, `qwenwork_video_generate` for the four video modes, and `qwenwork_music_generate` for music. Preserve its `mode`, specification fields, and prompt. Treat an explicit `model` as a confirmed requirement: pass it when the current schema and tool guidance permit that choice and accept the value. If a Profile locks the model and hides `model`, submit only when that lock is confirmed to satisfy the task sheet; otherwise explain the mismatch or uncertainty and follow the calling skill's fallback rule. Do not silently drop another unsupported field or value (for example `quality`, `reference_videos`, or `reference_audios`).
- Each task sheet comes with 用途 and 产物名. Pass 产物名 as `output_name`. Map 用途“交付” to `artifact_purpose: "deliverable"` and 用途“中间” to `artifact_purpose: "intermediate"`.
- For Open Image 2 task sheets, the quality rule below takes precedence over preserving the supplied `quality`: default to `medium` when exposed, and use `medium` even if the task sheet itself recommends `high`. Use `high` only when the task sheet conveys the user's explicit request for that tier or equivalent highest-quality intent. Preserve an explicitly specified `low`, `medium`, or `auto` tier from the user or task sheet.
- A calling skill may mark a result “中间” because it must first pass that skill's own check, or must be shown together with other results. When the calling skill then asks to show such a file, or a final file it produced locally, call `qwenwork_file_present_files` with the absolute paths in the requested order. Do not show results that the calling skill rejected or replaced.
- Capability names used by calling skills map to these tools:
  - 媒体理解 (媒体理解请求): `qwenwork_media_read`, with fields `files`, `prompt`, and optional `max_tokens`.
  - 联网搜索 (联网搜索请求): `qwenwork_web_search`, with fields `query`, `time_range`, and `max_results`.
  - 文件展示, or “按执行层的展示方式展示”: `qwenwork_file_present_files`, with `files: [{"file_path": "<absolute path>"}]` in display order.
- The calling skill's batch order, self-checks, regeneration limits, and local post-processing take precedence over the defaults here. The waiting, resume, and failure rules in this skill still apply.

## Output naming

Always pass `output_name` when waiting for a completed artifact:

- Derive it from the user's subject or purpose, artifact type, and a useful known spec such as duration.
- Use the user's language and keep it concise. Do not include a directory or file extension.
- Prefer names such as `产品主视觉`, `品牌宣传片-15s`, or `生日祝福-欢快流行歌曲`.
- Do not use generic names such as `generated-image`, `generated-video`, `generated-music`, `output`, or `result`.

## Model selection

Choose the model with `references/model-routing.md`: a model named by the user or written in a task sheet is locked; otherwise filter by hard constraints and use the scenario order as the initial preference. Pass `model` only when the current schema and tool guidance permit explicit choice and accept the value. A Profile-locked tool may hide `model`; do not claim that the skill can override the lock. If a locked requirement cannot be confirmed against the visible tool or Profile, explain the limitation instead of silently replacing the model. Tell the user the public model name before submitting only when the actual model can be confirmed. List other available models and their differences when the user asks.

For the models listed below, use these canonical aliases when the current schema accepts them:

- GPT Image 2, `gpt-image-2`, `gpt-image2`, or Open Image 2: `open-image-2`
- Banana Image 2, `nano-banana-2`, or Gemini 3.1 Flash Image: `banana-image-2`
- Seedance 2.0, SeeDance 2.0, or `sd2.0`: `seedance-2.0`
- Happy Horse 1.0: `happy-horse-1.0`
- MiniMax Music 2.5: `minimax-music-2.5`

Do not pass a provider name or old internal codename as `model`, expose provider endpoint paths or internal model IDs, invoke any native `ImageGen`/`image_gen` tool, or direct the user to a provider API for a supported request. If the user requests a model outside this list, first check the current tool schema; if it is unavailable in this session, explain that limitation and offer an exposed option rather than silently replacing it.

The JSON examples below illustrate a schema that exposes `model`. When the current Profile hides that field, omit it from the call and verify that the Profile-locked model satisfies any user or task-sheet model requirement before submitting.

## Shared prompt and reference rules

- Treat the user's current request and any approved plan as the source of truth. Retain the confirmed subject, changes, preservation requirements, shot order, spoken lines, on-screen copy, and prohibited elements. A follow-up such as "按上面的方案生成" calls for the latest approved version, not a new concept.
- For an edit based on an existing layout, change only the elements the user requested; keep all other visible content intact unless the user authorizes a change.
- Assign each supplied image a purpose before submitting it: base image or first frame, subject or product identity, clothing or packaging, pose, scene, composition, logo, or style. Refer to the corresponding image number and purpose in the prompt when several images are used; number them by their order in the submitted array. For video, favor useful identity references even when their pose differs from the requested shot, and screen optional references by shot intent. Respect the user's latest include or exclude instructions and current input limits; explain any tradeoff before omitting a requested image. If the role of an essential image is ambiguous, ask for the missing role.
- Write descriptive prompts in the user's language. For Chinese requests, keep the description in Chinese; preserve exact English brand names, model numbers, or requested English copy.
- When a source image anchors a real product, clothing item, package, or logo, state which visible properties must remain unchanged. Use only details the user supplied or that are reliably visible; do not invent its color, material, structure, printed text, or claims. When details are uncertain, ask the model to preserve the source image's actual visible details instead of guessing them in words.
- If a fine visual detail is critical, inspect its source region at a readable scale before describing it. If it remains unclear, refer to the source image instead of guessing.
- For on-image text, copy user-provided wording exactly and keep the requested language. In a Chinese ecommerce request, use Simplified Chinese for new visible copy unless the user specifies another language; keep brand names and model numbers as given. Do not invent prices, product specifications, or marketing claims. If the user asks to remove text or leave the image text-free, do not add a heading or placeholder copy. The packaged image routes can attempt on-image text; Open Image 2 is an initial preference, and the actual result must be checked. Put the text in the prompt so it is rendered in the same generation, and do not add text to a generated image locally unless the user requests that workflow.

## Image capability mapping

Use `qwenwork_image_generate` for every image request. Do not call native `ImageGen` or `image_gen` tools.

- New image from a prompt: `mode: "generate"`; omit `images` and `mask_image`.
- Edit, restyle, vary, or combine existing images: `mode: "edit"`, with `images` containing 1–14 inputs.
- Masked editing: `mode: "edit"`, with `images` and `mask_image`.

For edits, put the image to change first in `images`; use later images only for their stated reference roles. To add text to an existing image, follow `references/image-rules.md` section 2. For any user selection or mask, follow `references/mask-edit.md` before submitting. The documented Open Image 2 route needs an RGBA PNG mask matching `images[0]` in size and polarity described there; if another model exposes masking, check its current format and polarity. Verify alignment and never drop the user's selection.

For local images, use absolute paths. The files must be inside the current workspace or an additional directory granted to the conversation. HTTPS URLs and image data URLs are also accepted.

Pass the chosen model only when the current schema and tool guidance allow it; otherwise follow the Profile lock rule in "Model selection". Use only controls exposed for the actual model. The following mapping describes this packaged tool and should be checked against the current schema:

- `size`, `output_count`, `output_format`, and `mask_image` belong to Open Image 2. Generation and editing accept `size: "auto"` or a valid custom `WIDTHxHEIGHT`; see `references/model-routing.md` for the limits.
- `quality` accepts `low`, `medium`, `high`, or `auto` for Open Image 2 generation and editing when the current Schema and Profile expose it. For both modes, explicitly pass `quality: "medium"` by default; do not omit the field. Use `quality: "high"` only when the user requests that tier by name or clearly expresses equivalent intent, such as "highest quality", "maximum image quality", "use the best quality tier", "最高质量", "最高画质", or "画质拉满". Interpret the user's meaning in context, not by exact keyword matching; these examples are not exhaustive. A task sheet may carry the same user intent. Open-ended creativity, general requests such as "high-quality", "HD", or "more polished", or a task sheet's own preference are insufficient; use `medium` in those cases. Preserve an explicitly specified `low`, `medium`, or `auto` tier from the user or task sheet. Explain a requested tier that the actual model does not support instead of silently dropping it.
- `aspect_ratio`, `resolution`, and `web_search` belong to Banana Image 2.

### Text to image

Call `qwenwork_image_generate` with:

```json
{
  "mode": "generate",
  "model": "banana-image-2",
  "prompt": "黑色无线耳机置于深色磨砂展台，柔和轮廓光，真实商品摄影，画面中不出现文字。",
  "aspect_ratio": "1:1",
  "resolution": "2K"
}
```

### Image editing with a requested model, size, and quality

Call `qwenwork_image_generate` with:

```json
{
  "mode": "edit",
  "model": "open-image-2",
  "prompt": "保留原图商品的形状和 Logo，只把背景改成暖色极简摄影棚，并增加柔和的自然投影。",
  "images": ["/absolute/path/product.png"],
  "size": "1280x1024",
  "quality": "medium",
  "output_format": "png"
}
```

### Open Image 2 generation with visible text and requested size and quality

```json
{
  "mode": "generate",
  "model": "open-image-2",
  "prompt": "一只银色保温杯置于浅灰背景，正面商品摄影，边缘清晰；画面上方居中写标题「12 小时长效保温」。新增的说明性文字使用简体中文；品牌名、型号及用户指定文案保持原样，避免英文模板词、乱码和不可读字符。",
  "size": "1280x1024",
  "quality": "medium"
}
```

## Video capability mapping

Select the mode from the user's intent, not just the number of images:

- Prompt only: `text_to_video`
- Animate an existing image as the first frame while preserving its composition: `image_to_video`, with `image`
- First and last frame images: `first_last_frame_to_video`, with `first_frame_image` and `last_frame_image`
- Create a new shot using reference images for subject, product, clothing, action, scene, or style: `reference_images_to_video`, with 1–9 `reference_images`. A single reference image does not by itself make the task `image_to_video`.

Scope documented for this package:

- Seedance 2.0: all four modes, including lowercase `resolution: "4k"` on the standard model. See `references/video-constraints.md` for output encoding.
- Happy Horse 1.0: `text_to_video` and `image_to_video`; only 720p/1080p, without `aspect_ratio` or `generate_audio`.
- The documented schema has no reference video, reference audio, in-place edit, or extension mode. If the current schema still lacks them, understand an existing video with `qwenwork_media_read` and extract keyframes locally as reference images. Treat the result as a new clip and verify any requested resemblance or continuity.

Use only duration values and controls exposed by the current schema. In the documented version:

- Both listed models accept a fixed `duration_seconds` from 4 to 15, without automatic duration. If the current lower bound remains 4 seconds, explain a shorter request's limitation and offer 4 seconds instead of silently changing it. For more than the current upper bound, follow the 特殊需求 table in `references/model-routing.md`.
- The documented defaults are 5 seconds when `duration_seconds` is omitted; check the actual result if the current tool applies a different default.
- When the user gives no duration, resolution, or aspect ratio, start with the defaults in `references/video-rules.md` section 2 (5 seconds, 720p, ratio inferred from the scenario). Apply and describe only controls the chosen model actually exposes; do not promise an inferred ratio for a model without aspect-ratio control.
- There is no reliable fixed-camera control. A stationary-camera instruction in the prompt can guide the shot, but do not promise a fixed camera when that is an exact requirement.

For local images, use absolute paths. The files must be inside the current workspace or an additional directory granted to the conversation. The packaged `reference_images_to_video` limit is 1–9 `reference_images`; check the current tool before submitting.

Build the video prompt around the subject, its continuous action, scene and lighting, camera movement, pacing, any requested sound or visible text, and preservation requirements. For a short product clip, prefer a coherent motion over many scene changes. If the user wants only a subtle live-photo effect, keep the original image as the visual anchor and request small natural motion rather than a new setting or plot. For first-and-last-frame video, preserve the supplied frame order and describe the transition between them. For reference images, name each submitted image by its order in the array and say whether it guides identity, product, clothing, action, scene, or style. In the documented Seedance schema, set `generate_audio: true` for an audio track unless the user asks for silence, then set `false`; check the current schema before passing the field. The documented Happy Horse tool has no audio control. A generated audio track does not establish that exact narration or synchronized subtitles were produced.

## Video submission examples

These examples show Seedance 2.0 with an audio track and user-confirmed specifications. Apply the current schema and Profile model rule above before using them.

### Text to video

Call `qwenwork_video_generate` with:

```json
{
  "mode": "text_to_video",
  "model": "seedance-2.0",
  "prompt": "黑色无线耳机在干净的摄影棚中缓慢旋转，柔和轮廓光，镜头平稳推近，配轻柔环境音，不要旁白。",
  "duration_seconds": 10,
  "resolution": "4k",
  "aspect_ratio": "16:9",
  "generate_audio": true
}
```

### Single image to video

Call `qwenwork_video_generate` with:

```json
{
  "mode": "image_to_video",
  "model": "seedance-2.0",
  "prompt": "保持原图商品设计、文字和背景不变，只增加轻微转台旋转与反光变化，镜头平稳推近。",
  "image": "/absolute/path/product.png",
  "duration_seconds": 8,
  "resolution": "1080p",
  "generate_audio": true
}
```

### First and last frames to video

Call `qwenwork_video_generate` with:

```json
{
  "mode": "first_last_frame_to_video",
  "model": "seedance-2.0",
  "prompt": "从给定首帧平滑过渡到给定尾帧，保持主体外观一致，镜头运动自然连贯。",
  "first_frame_image": "/absolute/path/opening-frame.png",
  "last_frame_image": "/absolute/path/closing-frame.png",
  "duration_seconds": 6,
  "resolution": "1080p",
  "generate_audio": true
}
```

### Multiple reference images to video

Call `qwenwork_video_generate` with:

```json
{
  "mode": "reference_images_to_video",
  "model": "seedance-2.0",
  "prompt": "图 1 和图 2 用于保持人物身份与服装一致，图 3 只参考视觉风格；生成一段连贯的行走镜头。",
  "reference_images": [
    "/absolute/path/character-front.png",
    "/absolute/path/character-side.png",
    "/absolute/path/style-reference.png"
  ],
  "duration_seconds": 10,
  "resolution": "1080p",
  "aspect_ratio": "16:9",
  "generate_audio": true
}
```

## Music behavior

`qwenwork_music_generate` creates music or songs, not spoken narration.

- Put genre, mood, tempo, instruments, vocal style, and structure in `prompt`.
- Put supplied lyrics in `lyrics`.
- If the user wants a song with vocals but did not provide lyrics, omit `lyrics` and enable `auto_lyrics`. For instrumental music or an explicit no-lyrics request, omit `lyrics`, set `auto_lyrics: false`, and state the instrumental intent in `prompt`.
- The documented music tool delivers MP3; verify the returned file's actual format before presentation.

## Waiting, interruption, and resume

Waiting is local:

- Switching conversations, stopping the Agent, or closing the app may interrupt `qwenwork_media_task action=wait`.
- Interruption does not cancel the upstream task.
- If the result says `resumable: true`, retain both the `task_id` and its `artifact_purpose`.
- Do not resume automatically after a restart or conversation switch.
- Resume only when the user asks to continue, by calling `qwenwork_media_task` again with the same `task_id` and the same `artifact_purpose`.

If `wait` times out with `timed_out: true`, tell the user that completion has not yet been confirmed and the task can be resumed later. Do not submit a duplicate task unless the user asks to regenerate.

For a failed task with `retryable: false`, do not submit another media task in the same turn. For other failures, inspect the reported cause and the chosen mode, input count, model capability, and values before retrying. Do not silently switch a model the user explicitly chose or use an empty artifact as a successful result.

The documented media tools have no cancellation action. Do not claim that an upstream task was cancelled unless a current tool confirms it.

## Delivery

`qwenwork_media_task action=wait` returns local paths for completed artifacts. The documented common formats are:

- Image: `.png`, `.jpg`, or `.webp`, according to the generated artifact
- Video: `.mp4`
- Music: `.mp3`

Use the returned paths and verify the actual file types; do not derive a format claim solely from this list.

Call `qwenwork_file_present_files` after a successful wait only when the result says `should_present: true`. This creates the clickable Feed artifact card and lets the user preview or play the final file using their existing artifact-preview preference. Do not present intermediate files; consume them as working inputs and present only the derived final deliverables. The only exception is an intermediate result that a calling skill asks to show after its own check, as described in "Requests from other skills".

For image edits with critical fine details, compare the relevant source and result regions at a readable scale before claiming a match. Treat conflicting media descriptions as inconclusive; if visual inspection remains inconclusive, state the uncertainty. Do not claim pixel-level identity from a generative result.

After the artifact card is presented, finish with a concise delivery summary:

- Write the entire delivery summary in the user's conversation language, including every heading, field label, sentence, and follow-up suggestion. Unless the user explicitly requests another language, use the dominant natural language of the user's latest request; do not infer the language from model names, parameter names, filenames, or other technical tokens.
- For Chinese conversations, use headings such as `## 成片信息` and `## 创意方案总结`.
- Never use the English headings in a non-English conversation.
- For image generation or editing, summarize the known size, aspect ratio, resolution or quality tier, output format, and edit intent. Omit values that were not requested or confirmed.
- For video, include the localized equivalent of a finished-video section with the known duration, resolution, aspect ratio, and audio setting. Omit values that were not requested or confirmed.
- Add a localized creative-plan section covering the content positioning, visual style, key shots or narrative structure, and audio direction when relevant.
- For music, summarize the known style, mood, tempo, instruments, vocal choice, and structure.
- Do not invent generated-media properties that were not present in the user request or tool inputs.
- If the available result or preview shows that a required product detail, exact visible text, frame relationship, or media specification was missed, say what missed the requirement. Do not describe an unverified result as having exact copy, audio, or timing.
