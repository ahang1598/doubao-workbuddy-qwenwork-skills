# Shot blueprints

Capability mappings, not required templates. Read down the "need" column, then
route to the mechanism.

## Need → mechanism

| Need | Mechanism |
|---|---|
| Swap a product, prop or person in place | `SmartEdit` + reference image |
| Change season, weather, time of day | `VideoEdit`, one axis per pass |
| Restyle the whole look | `VideoEdit` with an explicit preservation clause |
| Add 2–3 seconds so a cut can breathe | `ExtendVideo`, empty or minimal prompt |
| Remove a passage | ffmpeg trim ×2 + concat |
| Tighten pacing | ffmpeg trim per segment, then concat |
| Speed ramp | ffmpeg `setpts` on split segments, then concat |
| Before / after comparison | two clips, `hstack` or `vstack` |
| Picture-in-picture | `overlay` with a scaled second input |
| Talking head + graphics | source on the spine, ASS overlays on top |
| Title card | generated colour source + ASS, joined as a clip |
| Lower third | ASS layer 1, see [title-animation.md](title-animation.md) |
| Captions | ASS layer 2, see [caption-systems.md](caption-systems.md) |
| Logo bug | ffmpeg `overlay` with a PNG |
| Reformat for another platform | ffmpeg scale + crop, see [clip-geometry.md](clip-geometry.md) |
| Music bed under dialogue | ffmpeg `amix` with `sidechaincompress` |
| Remove existing hard subtitles | `enable_erase_subtitles` on a supporting model |

## Side-by-side

```bash
# Horizontal, matched heights
ffmpeg -i a.mp4 -i b.mp4 -filter_complex \
  "[0:v]scale=-2:1080,setsar=1[l];[1:v]scale=-2:1080,setsar=1[r];[l][r]hstack=inputs=2[v]" \
  -map "[v]" -map 0:a -c:v libx264 -crf 20 -pix_fmt yuv420p out.mp4
```

`vstack` for vertical. Both inputs must match on the shared axis, hence the `scale`
and `setsar=1`. Output is twice as wide — reformat afterwards if the target is
`16:9`.

## Picture-in-picture

```bash
ffmpeg -i main.mp4 -i inset.mp4 -filter_complex \
  "[1:v]scale=480:-2[pip];[0:v][pip]overlay=W-w-40:H-h-40" \
  -map 0:a -c:v libx264 -crf 20 -pix_fmt yuv420p out.mp4
```

Gate it in time with `:enable='between(t,5,12)'`. Round the corners by pre-masking
the inset with an alpha PNG; there is no corner-radius parameter.

## Speed ramp

No ramping filter exists. Split, retime each part, rejoin:

```bash
ffmpeg -i in.mp4 -t 4 -c copy p1.mp4
ffmpeg -ss 4 -to 7 -i in.mp4 -c copy p2.mp4
ffmpeg -ss 7 -i in.mp4 -c copy p3.mp4
ffmpeg -i p2.mp4 -filter_complex "[0:v]setpts=0.25*PTS[v];[0:a]atempo=2.0,atempo=2.0[a]" \
  -map "[v]" -map "[a]" p2fast.mp4
bash <skill 目录>/scripts/concat_clips.sh -o out.mp4 p1.mp4 p2fast.mp4 p3.mp4
```

The transition between speeds is a hard cut, not a ramp. Say so — do not describe it
as a smooth ramp.

## Segment-then-edit

The default shape for any request touching part of a longer video. Editing the whole
timeline generatively is slow, expensive, and drifts everywhere you did not ask it to.

1. `probe_video.sh` the source.
2. ffmpeg trim the target segment (stream copy).
3. `upload_file` + `asset_create` the segment.
4. Generative edit that segment only.
5. Download the result, re-probe.
6. `concat_clips.sh` head + edited segment + tail.

Step 6 will need normalisation: the generated segment rarely matches the source's
codec, frame rate or dimensions.

## Multi-shot sequences

A generation produces **one continuous shot**. A three-shot sequence is three
generations plus a local concat. Never ask one prompt for multiple shots — see
[motion-language.md](motion-language.md).

Continuity across shots comes from carrying the same reference assets and repeating
the same wardrobe, lighting and palette clauses in each prompt, not from the model
remembering the previous generation.

## What has no mechanism

Layer trees, keyframe graphs, shared animated counters, path morphing, particle
systems, 2.5D camera rigs, GLSL shader effects and editable project files. When a
request needs one of these, say it is not supported and offer the nearest honest
approximation.
