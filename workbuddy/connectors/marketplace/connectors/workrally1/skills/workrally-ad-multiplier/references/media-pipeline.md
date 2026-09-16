# Source probe and finalization

Read this reference in Stage 2 for source normalization and in Stage 7 for final
delivery. Run every command in the **local shell** — there is no remote sandbox and no
presigned upload slot in this port. Keep one working directory for the whole run; the
finals are local files, and they only enter the WorkRally media library when the user
asks (or when a later WorkRally call needs an `asset_id`).

## Source probe normalization

Download only the trusted hosted source URL, following HTTPS redirects only and
limiting it to 500 MiB. Probe with:

```bash
curl --fail --location --proto '=https' --proto-redir '=https' --retry 2 --max-filesize 524288000 --output source.mp4 "$SOURCE_URL"
ffprobe -v error -show_streams -show_format -of json -- source.mp4
```

Normalize the JSON deterministically:

1. Select the primary non-cover-art video stream: prefer
   `disposition.default=1`, otherwise the first video stream whose
   `disposition.attached_pic` is not `1`.
2. Parse finite positive duration from `format.duration`, falling back to the
   primary video stream's duration. Reject missing/non-finite duration and any
   result outside 4.0-30.0 seconds.
3. Require positive coded width/height. Parse positive sample-aspect ratio,
   default `1:1`. Display aspect is `(coded_width * SAR) / coded_height`; invert
   it after normalized 90° or 270° rotation from side data or `tags.rotate`.
4. Parse positive `avg_frame_rate`, then `r_frame_rate`, falling back to 24 fps
   only for duration tolerance.
5. Select the audio stream marked `disposition.default=1`, otherwise the first
   audio stream. Retain its absolute ffprobe stream index. A missing audio stream
   means the source is silent.
6. Parse finite primary-video and selected-audio `start_time`. Set
   `AUDIO_OFFSET = audio_start_time - video_start_time` only when both are
   finite; otherwise use `0.0`.

Retain exact `SOURCE_DURATION`, `ceil(SOURCE_DURATION)`, display aspect, fps,
rotation-aware display geometry, audio stream index, and audio offset.

## Finalization

Process at most four completed outputs per shell command so a failure isolates cleanly.

In each command:

1. Download the immutable source once with the HTTPS-only command above.
2. Extract its selected default audio once. First try stream copy to MKA; if it
   fails, decode once to PCM WAV. Use the absolute stream index, `-nostdin`, and
   safely quoted paths:

   ```bash
   ffmpeg -nostdin -y -i source.mp4 -map "0:$AUDIO_STREAM_INDEX" -vn -c:a copy source-audio.mka
   # fallback only after copy failure
   ffmpeg -nostdin -y -i source.mp4 -map "0:$AUDIO_STREAM_INDEX" -vn -c:a pcm_s24le source-audio.wav
   ```

   If an audible source fails both commands, fail the group; never deliver a
   silent substitute. Skip extraction for a silent source.
3. Download each trusted completed generation HTTPS result URL with the same
   protocol and size restrictions. Reject an unplayable or video-less raw result.
4. Build `AUDIO_FILTER` from the measured offset:

   - positive: `adelay=<offset_ms>:all=1,asetpts=PTS-STARTPTS,apad=whole_dur=<duration>,atrim=duration=<duration>`;
   - negative: `atrim=start=<absolute_offset>,asetpts=PTS-STARTPTS,apad=whole_dur=<duration>,atrim=duration=<duration>`;
   - zero: `asetpts=PTS-STARTPTS,apad=whole_dur=<duration>,atrim=duration=<duration>`.

5. Discard accidental generated audio, retain only the generated video stream,
   trim to exact source duration, and restore only extracted source audio:

   ```bash
   # Audible source
   ffmpeg -nostdin -y -i raw.mp4 -i "$AUDIO_ABS" \
     -filter_complex "[1:a:0]$AUDIO_FILTER[source_audio]" \
     -map 0:v:0 -map '[source_audio]' -t "$SOURCE_DURATION" \
     -c:v copy -c:a aac -b:a 192k -movflags +faststart final.mp4

   # Silent source
   ffmpeg -nostdin -y -i raw.mp4 -map 0:v:0 -t "$SOURCE_DURATION" \
     -c:v copy -an -movflags +faststart final.mp4
   ```

   Do not use `-itsoffset`, `-shortest`, or `-avoid_negative_ts make_zero`:
   those may shift or truncate the inherited video timeline. If the generated
   video is too short, fail it rather than looping or freezing frames.
6. Probe each final and require all gates:

   - playable and contains a video stream;
   - duration within `max(1/fps, 0.10)` seconds of exact source duration;
   - rotation/SAR-aware display aspect within 1.5% relative error of source;
   - displayed short edge within 8 pixels of the selected 720 (`resolution: 3`) or
     1080 (`resolution: 4`);
   - audible source → AAC audio exists; silent source → no audio stream.

7. Name each passing final deterministically by its output index, e.g.
   `work/output/output01.mp4`, so the delivery order cannot drift.

Emit one concise receipt per output containing only its workflow index, QC
measurements and failure reason. Put a final in the media library only on request:

```
upload_file(file_path="<abs path>/work/output/output01.mp4")   → CDN url
asset_create(asset_url=<url>, project_id=<短番项目ID>)          → asset_id
```

A provider download failure may retry once; never submit a second edit job for a
download, remux or QC failure.
