# Deterministic edits — local ffmpeg recipes

Everything here runs in the **local shell**. There is no `sandbox_exec`.
Check the toolchain once per session:

```bash
command -v ffmpeg ffprobe
```

Missing on macOS → `brew install ffmpeg`. If it cannot be installed, degrade honestly:
say the deterministic step was skipped. Never describe an unrun command as done.

## Stream copy first

`-c copy` remuxes without re-encoding: instant, lossless, no generation loss.
Re-encode only when the operation actually changes pixels (scale, crop, speed,
filters, burn-in) or when concatenating mismatched sources.

Always tell the user when a step re-encoded.

## Trim

Cut a range. `-ss` before `-i` seeks fast; with `-c copy` it snaps to the nearest
keyframe, so the cut can land up to a GOP early.

```bash
# Fast, lossless, keyframe-aligned
ffmpeg -ss 00:00:03 -to 00:00:11 -i in.mp4 -c copy out.mp4

# Frame-accurate, re-encodes
ffmpeg -ss 00:00:03 -to 00:00:11 -i in.mp4 \
  -c:v libx264 -crf 18 -preset medium -c:a aac out.mp4
```

Ask for frame accuracy only when the user cares about an exact beat; otherwise the
copy path is better.

Drop the head or tail:

```bash
ffmpeg -ss 00:00:02 -i in.mp4 -c copy out.mp4          # drop first 2s
ffmpeg -i in.mp4 -t 00:00:30 -c copy out.mp4           # keep first 30s
```

## Speed

Video and audio need separate filters. `atempo` is valid in 0.5–2.0; chain it for
larger factors.

```bash
# 2x faster
ffmpeg -i in.mp4 -filter_complex "[0:v]setpts=0.5*PTS[v];[0:a]atempo=2.0[a]" \
  -map "[v]" -map "[a]" out.mp4

# 0.5x slower
ffmpeg -i in.mp4 -filter_complex "[0:v]setpts=2.0*PTS[v];[0:a]atempo=0.5[a]" \
  -map "[v]" -map "[a]" out.mp4

# 4x — chain atempo
ffmpeg -i in.mp4 -filter_complex "[0:v]setpts=0.25*PTS[v];[0:a]atempo=2.0,atempo=2.0[a]" \
  -map "[v]" -map "[a]" out.mp4
```

`setpts` multiplier is the **inverse** of the speed factor. Silent source: drop the
audio branch and add `-an`.

Reverse (loads the whole clip into memory — short clips only):

```bash
ffmpeg -i in.mp4 -vf reverse -af areverse out.mp4
```

## Frame rate

```bash
ffmpeg -i in.mp4 -r 30 -c:v libx264 -crf 18 -c:a copy out.mp4          # resample
ffmpeg -i in.mp4 -vf "minterpolate=fps=60" -c:a copy out.mp4           # interpolate, slow
```

Prefer plain `-r` resampling. `minterpolate` is expensive and introduces artifacts on
fast motion; only reach for it when the user explicitly asks for smoothing.

## Audio

```bash
# Strip audio
ffmpeg -i in.mp4 -an -c:v copy out.mp4

# Replace the track entirely (cut to the shorter of the two)
ffmpeg -i in.mp4 -i music.m4a -map 0:v -map 1:a -c:v copy -c:a aac -shortest out.mp4

# Mix a bed under the original at 25%
ffmpeg -i in.mp4 -i music.m4a \
  -filter_complex "[1:a]volume=0.25[bed];[0:a][bed]amix=inputs=2:duration=first[a]" \
  -map 0:v -map "[a]" -c:v copy -c:a aac out.mp4

# Duck the bed under dialogue
ffmpeg -i in.mp4 -i music.m4a \
  -filter_complex "[1:a][0:a]sidechaincompress=threshold=0.05:ratio=8[bed];[0:a][bed]amix=inputs=2[a]" \
  -map 0:v -map "[a]" -c:v copy -c:a aac out.mp4

# Fade in / out
ffmpeg -i in.mp4 -af "afade=t=in:d=1,afade=t=out:st=28:d=2" -c:v copy out.mp4
```

`-shortest` is what stops a long music bed from padding the video. Check
`has_audio` from `scripts/probe_video.sh` before mapping `0:a` — mapping a
nonexistent stream fails the whole command.

## Fades and simple transitions

```bash
# Fade from/to black (st = start second)
ffmpeg -i in.mp4 -vf "fade=t=in:st=0:d=0.5,fade=t=out:st=9.5:d=0.5" -c:a copy out.mp4

# Crossfade two clips over 1s (re-encodes; offset = first clip length - duration)
ffmpeg -i a.mp4 -i b.mp4 \
  -filter_complex "[0:v][1:v]xfade=transition=fade:duration=1:offset=4[v];[0:a][1:a]acrossfade=d=1[a]" \
  -map "[v]" -map "[a]" out.mp4
```

`xfade` `offset` is measured from the start of the **first** input. Get it wrong and
the transition lands off-screen. Other useful presets: `wipeleft`, `slideup`,
`circleopen`, `dissolve`.

## Stills and contact sheets

```bash
ffmpeg -ss 00:00:04 -i in.mp4 -frames:v 1 -q:v 2 frame.jpg      # single frame
ffmpeg -i in.mp4 -vf "fps=1/5,scale=320:-1,tile=4x3" sheet.jpg  # contact sheet
```

Use a contact sheet to look at a clip before deciding on an edit — cheaper and more
informative than describing the video blind.

## Loop and hold

```bash
ffmpeg -stream_loop 3 -i in.mp4 -c copy out.mp4                        # 4 plays total
ffmpeg -i in.mp4 -vf "tpad=stop_mode=clone:stop_duration=2" -c:a copy out.mp4  # freeze last frame 2s
```

## Verify before delivering

```bash
ffprobe -v error -show_entries format=duration,size \
  -show_entries stream=codec_type,codec_name,width,height,r_frame_rate \
  -of default=noprint_wrappers=1 out.mp4
```

A command that exited 0 is not proof of a correct edit. Confirm duration, both
stream types, and dimensions changed the way you intended. For anything visual,
pull a frame and look at it if the host can see images.

## Delivery encode

When a final re-encode is needed, these settings are a safe default:

```bash
ffmpeg -i in.mp4 -c:v libx264 -crf 20 -preset medium -pix_fmt yuv420p \
  -movflags +faststart -c:a aac -b:a 192k out.mp4
```

`-pix_fmt yuv420p` is what makes the file play in browsers and social apps;
`+faststart` moves the index to the front for web streaming. Both matter and both
are easy to forget.

Handing the result back to a generative edit pass or to the media library requires
`upload_file` + `asset_create` — local paths are never accepted by MCP tools.
