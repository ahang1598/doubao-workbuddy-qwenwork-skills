# Geometry, aspect ratio and resolution

Two separate geometry systems are in play and they do not share a vocabulary:
the **generation side** takes an enum plus a ratio string, the **local side** takes
pixels. Convert deliberately at the boundary.

## Supported aspect ratios

WorkRally accepts exactly these:

```
21:9  16:9  4:3  2:1  1:1  1:2  3:4  9:16
```

Anything else must be mapped, then optionally cropped locally:

| Requested | Use | Then |
|---|---|---|
| `4:5` (Instagram feed) | `3:4` | crop locally if the exact size matters |
| `2:3` (Pinterest) | `3:4` | crop locally |
| `3:2` (horizontal editorial) | `4:3` | crop locally |
| `3:1` / `4:1` (ultrawide banner) | `21:9` | crop locally |

Whenever you crop to reach a native platform size, **tell the user you cropped**.

`SmartEdit` inherits geometry from `source_video` and submits `ratio: "adaptive"`;
an aspect-ratio argument will not reshape it. Reshape after the edit, with ffmpeg.

## Resolution enums

Video and image use **different** enum tables. Mixing them is a silent quality bug.

| enum | video | image |
|---|---|---|
| 1 | 480P | — |
| 2 | 540P | — |
| 3 | 720P | — |
| 4 | 1080P | 1K |
| 5 | 1440P | 2K |
| 6 | 2160P | 4K |

Only send values present in that provider's `resolution_options[].value`.
Omitting `resolution` lets the backend pick the model's first available tier, which
is a reasonable default. `VideoEdit` ignores the field entirely.

## Common pixel sizes

| Ratio | 1080-class | 720-class |
|---|---|---|
| `16:9` | 1920×1080 | 1280×720 |
| `9:16` | 1080×1920 | 720×1280 |
| `1:1` | 1080×1080 | 720×720 |
| `4:3` | 1440×1080 | 960×720 |
| `3:4` | 1080×1440 | 720×960 |
| `21:9` | 2560×1080 | 1680×720 |
| `2:1` | 2160×1080 | 1440×720 |
| `1:2` | 1080×2160 | 720×1440 |

## Reshaping locally

Three strategies. Pick by what the user cares about losing.

**Cover / crop** — fills the frame, cuts the edges. Default for social reformats.

```bash
ffmpeg -i in.mp4 -vf "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920" \
  -c:a copy out.mp4
```

**Contain / letterbox** — keeps everything, adds bars. Use when nothing may be lost.

```bash
ffmpeg -i in.mp4 -vf "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black" \
  -c:a copy out.mp4
```

**Blurred backdrop** — fills the bars with a blurred copy. The usual choice for
turning landscape into vertical without dead black.

```bash
ffmpeg -i in.mp4 -filter_complex \
  "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=40:5[bg]; \
   [0:v]scale=1080:-2[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2" \
  -c:a copy out.mp4
```

Off-centre crop when the subject is not in the middle — `crop=w:h:x:y` with explicit
origin:

```bash
ffmpeg -i in.mp4 -vf "scale=-2:1920,crop=1080:1920:240:0" -c:a copy out.mp4
```

Look at a frame before choosing the crop origin. A centre crop that decapitates the
subject is the most common reformat failure.

## Encoder constraints

- Keep both dimensions **even**. H.264 with `yuv420p` requires it. `scale=-2:H`
  rounds to the nearest even number; `scale=-1:H` does not and will fail.
- Always finish with `-pix_fmt yuv420p` on delivery encodes, otherwise the file
  may not play in browsers or social apps.
- Scaling is a re-encode. Chain all geometry work into a single ffmpeg invocation
  rather than running several passes.

## Re-probe after every generative pass

Generated output does **not** reliably match the source's dimensions or duration.
Before any geometry work — and before a `SmartEdit` that consumes a previous
result — run:

```bash
bash <skill 目录>/scripts/probe_video.sh <file-or-url>
```

Use its `width` / `height` / `duration_ms` verbatim. Assuming the source geometry
carried through is the second most common failure in this skill, after passing
seconds where milliseconds were required.
