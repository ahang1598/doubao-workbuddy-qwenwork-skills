---
name: media-generation-premium
version: 1.1.1
description: Generate or edit images and generate videos or music for the enterprise premium media experience. Image, video, and music requests use official automatic model selection or organization-configured models exposed by the current tools. Use this skill for image generation or editing, text-to-video, image-to-video, first-and-last-frame video, multi-reference-image video, music, songs, soundtracks, or background music after the application activates the enterprise premium media experience. This skill creates image/video/music files; it is not for text-to-speech.
description_zh: 通过企业旗舰版媒体配置，为企业旗舰版媒体体验生成或编辑图片，并生成异步视频或音乐产物。图片、视频与音乐请求使用当前工具暴露的官方自动选模或组织配置模型。当应用已启用企业旗舰版媒体体验，且用户要求文生图、编辑图片、图片变体、文生视频、单图生视频、首尾帧生视频、多参考图生视频、音乐、歌曲、配乐或背景音乐时使用此技能。本技能生成图片、视频或音乐文件，不用于文字转语音。
license: Proprietary
---

# Enterprise Premium Media Generation

Use the built-in media tools only. Do not invoke a media provider directly, do not request or expose provider credentials or endpoints, and do not use text-to-speech for music requests.

The application activates this Skill for the enterprise premium media experience. The active image, video, or music path may use official automatic model selection or an organization-configured model. Treat each submit tool's current input schema and description as the source of truth for available modes, parameters, ranges, and model behavior:

- If the tool schema omits `model`, the application injects the configured model. Never add, infer, or override it.
- If the tool schema exposes `model` for an unbound media capability, omit it by default and only pass a value that the schema exposes when the user explicitly requests that model.
- Only send properties exposed by the current tool schema. A configured model can support a narrower set of modes, resolutions, durations, aspect ratios, or audio options than the baseline service.
- If the requested capability is absent from the current schema, explain that it is unavailable instead of guessing a provider-specific parameter.

## Required workflow

1. Choose exactly one submit tool:
   - Image generation or editing: `qwenwork_image_generate`
   - Video: `qwenwork_video_generate`
   - Music: `qwenwork_music_generate`
2. Keep the returned `task_id`.
3. Call `qwenwork_media_task` with `action: "wait"`, that `task_id`, and a friendly semantic `output_name`.
4. When `wait` returns `success: true`, call `qwenwork_file_present_files` with every path in `files`.
5. Only after `qwenwork_file_present_files` succeeds, tell the user the media artifact is ready.

The submit tools are asynchronous. Never describe a submitted task as a completed artifact.

## Output naming

Always pass `output_name` when waiting for a completed artifact:

- Derive it from the user's subject or purpose, artifact type, and a useful known spec such as duration.
- Use the user's language and keep it concise. Do not include a directory or file extension.
- Prefer names such as `产品主视觉`, `品牌宣传片-15s`, or `生日祝福-欢快流行歌曲`.
- Do not use generic names such as `generated-image`, `generated-video`, `generated-music`, `output`, or `result`.

## Image behavior

Use `qwenwork_image_generate` for every image request. Do not call the legacy `ImageGen` tool.

- New image from a prompt: `mode: "generate"`; omit `images` and `mask_image`.
- Edit, restyle, vary, or combine existing images: `mode: "edit"`, with `images` containing only the number of inputs allowed by the current tool schema.
- Masked editing: `mode: "edit"`, with `images` and `mask_image`, only when those fields are exposed by the current tool schema.
- Omit `model` by default. If the user explicitly names a supported image model, pass only the canonical alias specified by the current tool description and schema.
- Do not combine model-specific controls unless the current tool says they are compatible.

For local images, use absolute paths. The files must be inside the current workspace or an additional directory granted to the conversation. HTTPS URLs and image data URLs are also accepted when the current schema exposes them.

## Video behavior

Choose a video mode only from the current `qwenwork_video_generate` schema and provide its matching image fields:

- Prompt only: `text_to_video`
- One source or first-frame image: `image_to_video`, with `image`
- First and last frame images: `first_last_frame_to_video`, with `first_frame_image` and `last_frame_image`
- Multiple reference images: `reference_images_to_video`, with `reference_images`

Do not assume every configured model supports every listed mode. The current tool schema is authoritative.

For local images, use absolute paths. The files must be inside the current workspace or an additional directory granted to the conversation. For multi-reference video, pass only the number of images allowed by the current tool schema.

## Music behavior

`qwenwork_music_generate` creates music or songs, not spoken narration.

- Put genre, mood, tempo, instruments, vocal style, and structure in `prompt`.
- Put supplied lyrics in `lyrics`.
- If the user did not provide lyrics, omit `lyrics` and leave `auto_lyrics` enabled.
- The delivered format is MP3.

## Waiting, interruption, and resume

Waiting is local:

- Switching conversations, stopping the Agent, or closing the application may interrupt `qwenwork_media_task action=wait`.
- Interruption does not cancel the upstream task.
- If the result says `resumable: true`, retain the `task_id`.
- Do not resume automatically after a restart or conversation switch.
- Resume only when the user asks to continue, by calling `qwenwork_media_task` again with the same `task_id`.

If `wait` times out with `timed_out: true`, tell the user that the upstream task is still processing and can be resumed later. Do not submit a duplicate task unless the user asks to regenerate.

The current media-router contract has no active cancellation API. Do not claim that an upstream media task has been cancelled.

## Delivery

`qwenwork_media_task action=wait` downloads completed artifacts into the current conversation output directory:

- Image: `.png`, `.jpg`, or `.webp`, according to the generated artifact
- Video: `.mp4`
- Music: `.mp3`

Always call `qwenwork_file_present_files` after a successful wait. This creates the clickable artifact card and lets the user preview or play the file using their existing artifact-preview preference.

After the artifact card is presented, finish with a concise delivery summary:

- Write the entire delivery summary in the user's conversation language, including every heading, field label, sentence, and follow-up suggestion. Unless the user explicitly requests another language, use the dominant natural language of the user's latest request; do not infer the language from model names, parameter names, filenames, or other technical tokens.
- For Chinese conversations, use headings such as `## 成片信息` and `## 创意方案总结`.
- Never use the English headings in a non-English conversation.
- For image generation or editing, summarize the known size, aspect ratio, resolution tier, output format, and edit intent. Omit values that were not requested or confirmed.
- For video, include the localized equivalent of a finished-video section with the known duration, resolution, aspect ratio, and audio setting. Omit values that were not requested or confirmed.
- Add a localized creative-plan section covering the content positioning, visual style, key shots or narrative structure, and audio direction when relevant.
- For music, summarize the known style, mood, tempo, instruments, vocal choice, and structure.
- Do not invent generated-media properties that were not present in the user request or tool inputs.
