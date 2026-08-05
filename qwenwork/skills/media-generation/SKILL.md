---
name: media-generation
version: 1.1.2
description: Generate videos or music as asynchronous media artifacts. Use this skill when the user asks for text-to-video, image-to-video, first-and-last-frame video, multi-reference-image video, music, a song, a soundtrack, or background music. This skill creates video/music files; it is not for text-to-speech.
description_zh: 生成异步视频或音乐产物。当用户要求文生视频、单图生视频、首尾帧生视频、多参考图生视频、音乐、歌曲、配乐或背景音乐时使用此技能。本技能生成视频或音乐文件，不用于文字转语音。
license: Proprietary
---

# Media Generation

Use QwenWork built-in media tools. Do not invoke a media provider directly and do not use text-to-speech for music requests.

## Required workflow

1. Choose exactly one submit tool:
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
- Prefer names such as `QwenWork-品牌宣传片-15s` or `生日祝福-欢快流行歌曲`.
- Do not use generic names such as `generated-video`, `generated-music`, `output`, or `result`.

## Model selection

Omit `model` by default. QwenWork selects a compatible logical model alias.

Only pass `model` when the user explicitly requests a supported model:

- Seedance 2.0: `seedance-2.0`
- Happy Horse 1.0: `happy-horse-1.0`
- MiniMax Music 2.5: `minimax-music-2.5`

Do not expose provider endpoint paths or internal model IDs.

## Video capability mapping

Select the mode from the user's inputs:

- Prompt only: `text_to_video`
- One source or first-frame image: `image_to_video`, with `image`
- First and last frame images: `first_last_frame_to_video`, with `first_frame_image` and `last_frame_image`
- Multiple reference images: `reference_images_to_video`, with `reference_images`

Supported scope:

- Seedance 2.0: all four modes.
- Happy Horse 1.0: `text_to_video` and `image_to_video`; only 720p/1080p, without `aspect_ratio` or `generate_audio`.
- Reference videos, reference audio, and video editing are outside the initial scope.

For local images, use absolute paths. The files must be inside the current workspace or an additional directory granted to the conversation. For multi-reference video, pass 1–9 images.

## Video submission examples

All examples intentionally omit `model`. Let QwenWork select a compatible model unless the user explicitly names one.

### Text to video

Call `qwenwork_video_generate` with:

```json
{
  "mode": "text_to_video",
  "prompt": "A matte-black wireless earbud rotates slowly in a clean studio, with soft rim lighting and a smooth camera push-in.",
  "duration_seconds": 10,
  "resolution": "1080p",
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
- If the result says `resumable: true`, retain the `task_id`.
- Do not resume automatically after a restart or conversation switch.
- Resume only when the user asks to continue, by calling `qwenwork_media_task` again with the same `task_id`.

If `wait` times out with `timed_out: true`, tell the user that the upstream task is still processing and can be resumed later. Do not submit a duplicate task unless the user asks to regenerate.

The current qwenwork-router contract has no active cancellation API. Do not claim that an upstream media task has been cancelled.

## Delivery

`qwenwork_media_task action=wait` downloads completed artifacts into the current conversation output directory:

- Video: `.mp4`
- Music: `.mp3`

Always call `qwenwork_file_present_files` after a successful wait. This is what creates the clickable Feed artifact card and lets the user preview or play the file using their existing artifact-preview preference.

After the artifact card is presented, finish with a concise delivery summary:

- Write the entire delivery summary in the user's conversation language, including every heading, field label, sentence, and follow-up suggestion. Unless the user explicitly requests another language, use the dominant natural language of the user's latest request; do not infer the language from model names, parameter names, filenames, or other technical tokens.
- For Chinese conversations, use headings such as `## 成片信息` and `## 创意方案总结`.
- Never use the English headings in a non-English conversation.
- For video, include the localized equivalent of a finished-video section with the known duration, resolution, aspect ratio, and audio setting. Omit values that were not requested or confirmed.
- Add a localized creative-plan section covering the content positioning, visual style, key shots or narrative structure, and audio direction when relevant.
- For music, summarize the known style, mood, tempo, instruments, vocal choice, and structure.
- Do not invent generated-media properties that were not present in the user request or tool inputs.
