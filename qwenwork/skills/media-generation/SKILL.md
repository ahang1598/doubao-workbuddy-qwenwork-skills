---
name: media-generation
version: 1.4.0
description: Generate or edit images with automatic model selection or a supported model explicitly requested by the user, generate videos, or create music as asynchronous media artifacts. Use this skill when the user asks for text-to-image, image editing, image variations, choosing a supported model for image generation or editing, text-to-video, image-to-video, first-and-last-frame video, multi-reference-image video, music, a song, a soundtrack, or background music. This skill creates image/video/music files; it is not for text-to-speech.
description_zh: 支持自动选模，也支持按用户明确指定的已支持模型生成或编辑图片，以及生成异步视频或音乐产物。当用户要求文生图、编辑图片、图片变体、为生图或编辑图选择已支持模型、文生视频、单图生视频、首尾帧生视频、多参考图生视频、音乐、歌曲、配乐或背景音乐时使用此技能。本技能生成图片、视频或音乐文件，不用于文字转语音。
license: Proprietary
---

# Media Generation

Use QwenWork built-in media tools. Do not invoke a media provider directly and do not use text-to-speech for music requests. Do not invoke native `ImageGen`/`image_gen` or `WebSearch`/`web_search`/`websearch` tools; use the canonical QwenWork tools below. The `web_search` image-generation parameter is a grounding option, not a tool name.

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

## Output naming

Always pass `output_name` when waiting for a completed artifact:

- Derive it from the user's subject or purpose, artifact type, and a useful known spec such as duration.
- Use the user's language and keep it concise. Do not include a directory or file extension.
- Prefer names such as `产品主视觉`, `QwenWork-品牌宣传片-15s`, or `生日祝福-欢快流行歌曲`.
- Do not use generic names such as `generated-image`, `generated-video`, `generated-music`, `output`, or `result`.

## Model selection

Omit `model` by default. QwenWork selects a compatible logical model alias when the user does not name a supported model.

When the user explicitly requests a supported model, you must pass its canonical public alias instead of refusing the request or claiming that the image tool only supports a default model:

- GPT Image 2, `gpt-image-2`, `gpt-image2`, or Open Image 2: `open-image-2`
- Banana Image 2: `banana-image-2`
- Seedance 2.0: `seedance-2.0`
- Happy Horse 1.0: `happy-horse-1.0`
- MiniMax Music 2.5: `minimax-music-2.5`

Pass only the canonical aliases shown above. Do not pass `gpt-image-2` or `gpt-image2` to the tool, expose provider endpoint paths or internal model IDs, invoke any native `ImageGen`/`image_gen` tool, or direct the user to a provider API for a supported request.

## Image capability mapping

Use `qwenwork_image_generate` for every image request. Do not call native `ImageGen` or `image_gen` tools.

- New image from a prompt: `mode: "generate"`; omit `images` and `mask_image`.
- Edit, restyle, vary, or combine existing images: `mode: "edit"`, with `images` containing 1–14 inputs.
- Masked editing: `mode: "edit"`, with `images` and `mask_image`.
- Explicit model selection works for both `generate` and `edit`. If the user names a supported model, include its canonical alias in `model`.

For local images, use absolute paths. The files must be inside the current workspace or an additional directory granted to the conversation. HTTPS URLs and image data URLs are also accepted.

Omit `model` by default. QwenWork selects a compatible image model from the requested controls. Do not combine model-specific controls unless the selected model supports them:

- `size`, `output_count`, `output_format`, and `mask_image` select Open Image 2 compatibility.
- `quality` selects Open Image 2 compatibility for both `mode: "generate"` and `mode: "edit"`. Allowed values are `low`, `medium`, `high`, and `auto`; do not send it with Banana Image 2. If the user does not request a quality tier, omit it and leave the default to the upstream provider.
- `aspect_ratio`, `resolution`, and `web_search` select Banana Image 2 compatibility.

For Open Image 2 generation and editing, `size` accepts `auto` or `WIDTHxHEIGHT` with a lowercase `x`. Width and height must each be positive integers divisible by 16 and no greater than 3840; width divided by height must be between 1/3 and 3, inclusive, and width multiplied by height must be between 655360 and 8294400 pixels, inclusive. Sizes such as `1280x1024`, `3840x2160`, and `2160x3840` are valid examples, not an exhaustive list. Preserve a requested valid size; if the size is invalid, explain the constraint before choosing a different size. If the user does not request a size, omit it and leave the default to the upstream provider.

### Text to image

Call `qwenwork_image_generate` with:

```json
{
  "mode": "generate",
  "prompt": "A premium wireless earbud on a matte-black pedestal, soft rim lighting, editorial product photography, no text.",
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
  "prompt": "Keep the product shape and logo unchanged. Replace the background with a warm minimalist studio and add a soft natural shadow.",
  "images": ["/absolute/path/product.png"],
  "size": "1280x1024",
  "quality": "medium",
  "output_format": "png"
}
```

### Open Image 2 generation with a requested custom size and quality

Call `qwenwork_image_generate` with:

```json
{
  "mode": "generate",
  "model": "open-image-2",
  "prompt": "A silver travel mug on a plain white background, front-facing product photography, crisp edges, no text.",
  "size": "1280x1024",
  "quality": "high"
}
```

## Video capability mapping

Select the mode from the user's inputs:

- Prompt only: `text_to_video`
- One source or first-frame image: `image_to_video`, with `image`
- First and last frame images: `first_last_frame_to_video`, with `first_frame_image` and `last_frame_image`
- Multiple reference images: `reference_images_to_video`, with `reference_images`

Supported scope:

- Standard Seedance 2.0: all four modes, with `resolution` values `480p`, `720p`, `1080p`, and lowercase `4k`. A requested `4k` selects Seedance compatibility; do not silently reduce it to `1080p`. If the user does not request a resolution, omit it and leave the default to the upstream provider.
- Happy Horse 1.0: `text_to_video` and `image_to_video`; only 720p/1080p, without `aspect_ratio` or `generate_audio`.
- Reference videos, reference audio, and video editing are outside the initial scope.

For local images, use absolute paths. The files must be inside the current workspace or an additional directory granted to the conversation. For multi-reference video, pass 1–9 images.

Seedance 2.0's `4k` output uses 10-bit H.265 in an MP4 container. Present the original generated file without silently transcoding or reducing its resolution. If the preview cannot play it, keep the original downloadable artifact and explain that playback requires a player with 10-bit H.265 support. Do not promise a fixed width and height solely from the `4k` setting.

## Video submission examples

All examples intentionally omit `model`. Let QwenWork select a compatible model unless the user explicitly names one.

### Text to video

Call `qwenwork_video_generate` with:

```json
{
  "mode": "text_to_video",
  "prompt": "A matte-black wireless earbud rotates slowly in a clean studio, with soft rim lighting and a smooth camera push-in.",
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
  "prompt": "Keep the product design unchanged. Add a slow turntable rotation, subtle reflections, and a steady camera push-in.",
  "image": "/absolute/path/product.png",
  "duration_seconds": 8,
  "resolution": "1080p"
}
```

### First and last frames to video

Call `qwenwork_video_generate` with:

```json
{
  "mode": "first_last_frame_to_video",
  "prompt": "Create a smooth cinematic transition from the opening frame to the closing frame while preserving the subject.",
  "first_frame_image": "/absolute/path/opening-frame.png",
  "last_frame_image": "/absolute/path/closing-frame.png",
  "duration_seconds": 6,
  "resolution": "1080p"
}
```

### Multiple reference images to video

Call `qwenwork_video_generate` with:

```json
{
  "mode": "reference_images_to_video",
  "prompt": "Use the references to preserve the character, clothing, and visual style across a continuous walking shot.",
  "reference_images": [
    "/absolute/path/character-front.png",
    "/absolute/path/character-side.png",
    "/absolute/path/style-reference.png"
  ],
  "duration_seconds": 10,
  "resolution": "1080p",
  "aspect_ratio": "16:9"
}
```

## Music behavior

`qwenwork_music_generate` creates music or songs, not spoken narration.

- Put genre, mood, tempo, instruments, vocal style, and structure in `prompt`.
- Put supplied lyrics in `lyrics`.
- If the user did not provide lyrics, omit `lyrics` and leave `auto_lyrics` enabled.
- The delivered format is MP3.

## Waiting, interruption, and resume

Waiting is local:

- Switching conversations, stopping the Agent, or closing QwenWork may interrupt `qwenwork_media_task action=wait`.
- Interruption does not cancel the upstream task.
- If the result says `resumable: true`, retain both the `task_id` and its `artifact_purpose`.
- Do not resume automatically after a restart or conversation switch.
- Resume only when the user asks to continue, by calling `qwenwork_media_task` again with the same `task_id` and the same `artifact_purpose`.

If `wait` times out with `timed_out: true`, tell the user that the upstream task is still processing and can be resumed later. Do not submit a duplicate task unless the user asks to regenerate.

The current qwenwork-router contract has no active cancellation API. Do not claim that an upstream media task has been cancelled.

## Delivery

`qwenwork_media_task action=wait` downloads completed artifacts into the current conversation output directory:

- Image: `.png`, `.jpg`, or `.webp`, according to the generated artifact
- Video: `.mp4`
- Music: `.mp3`

Call `qwenwork_file_present_files` after a successful wait only when the result says `should_present: true`. This creates the clickable Feed artifact card and lets the user preview or play the final file using their existing artifact-preview preference. Do not present intermediate files; consume them as working inputs and present only the derived final deliverables.

After the artifact card is presented, finish with a concise delivery summary:

- Write the entire delivery summary in the user's conversation language, including every heading, field label, sentence, and follow-up suggestion. Unless the user explicitly requests another language, use the dominant natural language of the user's latest request; do not infer the language from model names, parameter names, filenames, or other technical tokens.
- For Chinese conversations, use headings such as `## 成片信息` and `## 创意方案总结`.
- Never use the English headings in a non-English conversation.
- For image generation or editing, summarize the known size, aspect ratio, resolution or quality tier, output format, and edit intent. Omit values that were not requested or confirmed.
- For video, include the localized equivalent of a finished-video section with the known duration, resolution, aspect ratio, and audio setting. Omit values that were not requested or confirmed.
- Add a localized creative-plan section covering the content positioning, visual style, key shots or narrative structure, and audio direction when relevant.
- For music, summarize the known style, mood, tempo, instruments, vocal choice, and structure.
- Do not invent generated-media properties that were not present in the user request or tool inputs.
