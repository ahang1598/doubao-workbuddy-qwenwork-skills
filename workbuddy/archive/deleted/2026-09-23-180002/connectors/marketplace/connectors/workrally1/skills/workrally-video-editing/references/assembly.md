# Assembly — joining clips and laying audio

**Local ffmpeg only.** Do not call `video_concat`. Missing ffmpeg is a hard stop.

## Local ffmpeg

### Same codec, same geometry → demuxer concat, lossless

```bash
cat > list.txt <<'EOF'
file '/abs/path/a.mp4'
file '/abs/path/b.mp4'
file '/abs/path/c.mp4'
EOF

ffmpeg -f concat -safe 0 -i list.txt -c copy out.mp4
```

Requires identical codec, resolution, frame rate, pixel format and audio layout.
Any mismatch produces a file that plays only the first clip, or drifts out of sync —
often with **no error**. Verify with `probe_video.sh` on each input first.

Paths in `list.txt` must be absolute, or relative to the list file's own directory.

### Mismatched sources → normalise, then concat

`scripts/concat_clips.sh` does this: probes every input, picks a target geometry and
frame rate, normalises each clip, then joins. Use it whenever the inputs did not all
come out of the same pipeline.

```bash
bash <skill 目录>/scripts/concat_clips.sh -o out.mp4 a.mp4 b.mp4 c.mp4
```

The one-liner equivalent, for reference:

```bash
ffmpeg -i a.mp4 -i b.mp4 -filter_complex \
  "[0:v]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30[v0]; \
   [1:v]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30[v1]; \
   [v0][0:a][v1][1:a]concat=n=2:v=1:a=1[v][a]" \
  -map "[v]" -map "[a]" -c:v libx264 -crf 20 -pix_fmt yuv420p -c:a aac out.mp4
```

`setsar=1` is not optional — mismatched sample aspect ratios make `concat` refuse
the graph. A silent clip breaks the audio branch; give it a synthetic track first:

```bash
ffmpeg -i silent.mp4 -f lavfi -i anullsrc=channel_layout=stereo:sample_rate=48000 \
  -map 0:v -map 1:a -c:v copy -c:a aac -shortest fixed.mp4
```

### Narration over a cut

Lay the voice track across the assembled cut, ducking any production audio:

```bash
ffmpeg -i cut.mp4 -i vo.wav \
  -filter_complex "[0:a]volume=0.2[bed];[bed][1:a]amix=inputs=2:duration=longest[a]" \
  -map 0:v -map "[a]" -c:v copy -c:a aac out.mp4
```

If the narration is longer than the picture, freeze the last frame to cover it
(`tpad`, see [ffmpeg-recipes.md](ffmpeg-recipes.md)) rather than letting the audio
get truncated.

## Voiceover

Writing and generating narration belongs to the `workrally-narrator` skill — hand
off rather than driving TTS from here. This skill's job is to take a
finished voice track and lay it against picture, as above.

Before commissioning narration at all, check whether the video model already carries
native audio (`support_audio: true`). If it does, `enable_sound` defaults to `true`
and the clip ships with its own soundtrack — a separate voice track would fight it.

## Ordering rules

These are the ones that actually bite:

1. **Normalise before joining.** Geometry and frame rate must agree at the join,
   not after it.
2. **Join before burning captions.** Timecodes are relative to the assembled
   timeline; burning per-clip then joining shifts every cue.
3. **Reformat aspect ratio last.** Do the creative work at source geometry, reshape
   once at delivery.
4. **Re-probe between stages.** Every generative pass can change dimensions and
   duration.

## Verify the assembly

```bash
ffprobe -v error -show_entries format=duration \
  -show_entries stream=codec_type,codec_name,width,height,r_frame_rate \
  -of default=noprint_wrappers=1 out.mp4
```

Total duration should equal the sum of the parts (minus any crossfade overlap).
A short result means the concat silently dropped a clip. Both a video and an audio
stream should be present if any input had sound.
