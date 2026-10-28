---
name: media-read
description: Extract objective text and detail from images, audio, and video. Use for OCR, transcription, summaries, charts, screenshots, receipts, scanned documents, recordings, and clips.
---

# Media Read

Use the `qwenwork_media_read` MCP tool. Do not read credential files or token environment variables, and do not call a model endpoint directly.

## Workflow

1. Put related files in one `files` array, up to 20 items.
2. For local media, use absolute paths inside the current workspace or the current conversation's managed `uploads` directory when an uploaded image path is supplied. HTTPS image and video URLs are accepted; remote audio must first be saved into the workspace.
3. Write a specific `prompt` that names every field or output shape required. For example, request labeled invoice fields rather than a generic description.
4. Use the returned `text` as objective extraction. Keep any `reasoning` separate from the answer.

This lightweight desktop integration sends original media without image resizing or Sharp/Pillow preprocessing. If a large or dense image loses detail, crop or resize a copy with an available document/media tool and call `qwenwork_media_read` again.

Use direct visual inspection instead when the task requires subjective design judgment rather than extraction.
