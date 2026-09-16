# Limits and diagnostics

## Symptom → contract

| Symptom / refusal | Contract |
|---|---|
| `SmartEdit模式的 source_video 必须包含有效 width/height/duration` | All three required, all > 0, and `duration` is **milliseconds**. Use `probe_video.sh`'s `duration_ms`. |
| `SmartEdit模式需要 source_video.asset_id` | An asset_id, not a URL and not a local path. `upload_file` → `asset_create` first. |
| `VideoEdit模式需要提供 origin_video` | `origin_video` is a bare asset_id **string**, not an object like `source_video`. |
| `ExtendVideo模式需要 duration` | `duration` is the number of seconds **to add**, required and > 0. |
| `ExtendVideo 的 reference_assets 仅支持图片` | The source belongs in `source_video`; only images may go in `reference_assets`. |
| `prompt（提示词）不能为空` | Required for `VideoEdit`. Optional only for `SmartEdit` and `ExtendVideo`. |
| Unknown or rejected model | Provider IDs are environment-specific. Re-read `canvas_video_provider_config`; never hardcode or guess. |
| Provider cannot extend | Its `extend_duration_range` is empty. Filter for a provider that has one. |
| `enable_erase_subtitles` rejected | Only providers with `support_erase_subtitles: true` accept it. |
| Media short-link expired | WorkRally short links live 5 hours. Re-resolve and resubmit. |
| Aspect ratio rejected | Only `21:9 16:9 4:3 2:1 1:1 1:2 3:4 9:16` exist. See [clip-geometry.md](clip-geometry.md). |
| Wrong output resolution | Video enums differ from image enums; value must be in that provider's `resolution_options`. `VideoEdit` ignores `resolution` entirely. |
| Concat plays only the first clip | Demuxer concat requires identical codec, geometry, frame rate and audio layout. Normalise first. |
| Concat audio drifts | Mismatched sample rates, or a silent input with no audio stream. Give every input a track. |
| `concat` filter refuses the graph | Missing `setsar=1` after scaling, or unequal stream counts across inputs. |
| Filter output has odd dimensions | H.264 + `yuv420p` needs even width and height. Use `scale=-2:H`, never `-1`. |
| Video will not play in a browser | Missing `-pix_fmt yuv420p`, or missing `-movflags +faststart`. |
| Subtitles render as tofu boxes | Usually `PingFang SC` on macOS — fontconfig resolves it to a SIP-protected path libass cannot open, then silently falls back to a Latin face. Use `Hiragino Sans GB`. See [caption-systems.md](caption-systems.md). |
| Burned SRT text is enormous | libass renders SRT against a 384×288 canvas, scaling `Fontsize` by `height/288`. Convert to ASS and fix `PlayRes` first. |
| Subtitle positions all wrong | `PlayResX` / `PlayResY` do not match the video's pixel dimensions. |
| Subtitle colours inverted | ASS colours are `&HAABBGGRR` — BGR order, and alpha `00` is opaque. |
| Burned text vanished after an edit | Captions were burned before a generative pass. Burn last, always. |
| Trim landed early | `-ss` with `-c copy` snaps to a keyframe. Re-encode for frame accuracy. |
| Music padded the video | Missing `-shortest`. |
| Mapping `0:a` failed | The input has no audio stream. Check `has_audio` before mapping. |

## What each command actually proves

- `probe_video.sh` / `ffprobe` — real stream properties. A file extension proves
  nothing about codec, depth or dimensions.
- `ffmpeg` exit 0 — the command ran. It does **not** prove the edit is correct.
  Re-probe the output and compare against intent.
- `canvas_get_task` `state=4` — the task succeeded and `output_assets` is populated.
  It does not mean the result matches the request.
- A single extracted frame — proves what that frame looks like, nothing about the
  rest of the clip or about audio.
- A contact sheet — cheap coverage across the timeline; the best available proxy for
  actually watching the video.

## Polling discipline

Poll each task_id every 3 seconds. States: `1` queued, `2` running, `3` paused,
`4` succeeded, `5` failed, `6` cancelled.

- A polling timeout is **not** a failure. Keep the task_id and report it as still
  running.
- Stop after 12 rounds for a given deliverable. Continue in the next turn.
- Completed tasks are frozen — never resubmit one.
- Retry a technical failure at most once per task. Stop immediately on safety,
  permission or quota errors and explain; do not retry those.
- Failed submissions and revisions both count against a budget of three submissions
  per deliverable. Rewriting the prompt does not reset it.

## Honest reporting

- If `ffmpeg` is not installed, say the deterministic step was skipped. Do not
  describe an unrun command as executed.
- If the host cannot see pixels, say the result was not visually verified. Do not
  claim quality passed, and do not spend generations on speculative fixes.
- If one segment of a multi-part deliverable failed, report exactly which. Do not
  claim the whole thing is done.
- If a capability does not exist (timeline engine, transcription, editable project
  export, cost estimation), say so plainly. Do not substitute something else and
  present it as equivalent.
