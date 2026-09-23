# Titles, lower thirds and overlays

Titles are ASS events on their own layer, or PNG overlays composited with ffmpeg.
There is no keyframe engine, no layer tree and no scripting API — everything here is
a declarative tag or an overlay filter. Complex motion graphics are out of scope;
say so rather than approximating badly.

## Primitive map

| Want | Mechanism |
|---|---|
| Fade in / out | ASS `\fad(in_ms, out_ms)` |
| Move across frame | ASS `\move(x1,y1,x2,y2,t1,t2)` |
| Scale / pop | ASS `\fscx` / `\fscy` inside `\t(t1,t2,...)` |
| Rotate | ASS `\frz` (also `\frx` / `\fry` for pseudo-3D) |
| Colour / opacity tween | ASS `\t(t1,t2,\1c&H...&)` / `\t(t1,t2,\alpha&H80&)` |
| Blur | ASS `\blur` (animatable via `\t`) |
| Wipe / reveal | ASS `\clip()` animated with `\t` |
| Outline draw-on | animate `\bord` from 0 upward |
| Per-character entrance | one `Dialogue` line per character with staggered starts |
| Static logo / badge | ffmpeg `overlay` filter with a PNG |
| Animated logo | pre-rendered transparent video, `overlay` with alpha |

`\t(t1,t2,tags)` times are **milliseconds relative to the line's own start**, not
timeline time. `\move` uses the same local clock.

## Lower third

```
[V4+ Styles]
Style: L3Name,PingFang SC,56,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,0,0,1,0,0,0,1
Style: L3Role,PingFang SC,36,&H00C8C8C8,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,1,0,0,0,1

[Events]
Dialogue: 1,0:00:02.00,0:00:07.00,L3Name,,0,0,0,,{\pos(120,900)\fad(300,300)\clip(120,860,120,960)\t(0,400,\clip(120,860,900,960))}张三
Dialogue: 1,0:00:02.15,0:00:07.00,L3Role,,0,0,0,,{\pos(120,960)\fad(300,300)\alpha&HFF&\t(150,500,\alpha&H00&)}产品负责人
```

The name wipes in from the left, the role fades in 150 ms behind it. Staggering the
two lines by 150–250 ms is what makes it read as designed rather than dumped on
screen.

Add a rule bar with an ASS drawing on a lower layer:

```
Dialogue: 0,0:00:02.00,0:00:07.00,L3Name,,0,0,0,,{\pos(120,1000)\p1\c&H32ACFF&\1a&H00&}m 0 0 l 400 0 l 400 6 l 0 6{\p0}
```

`\p1` enters drawing mode; coordinates are relative to `\pos`. `\p0` exits.

## Full-frame title card

```
Dialogue: 0,0:00:00.00,0:00:03.00,Body,,0,0,0,,{\an5\pos(540,960)\fs120\fad(400,400)\fscx90\fscy90\t(0,350,\fscx100\fscy100)}主标题\N{\fs52}副标题一行
```

`\an5` centres the anchor on `\pos`. Scaling from 90% to 100% over 350 ms reads as
confident; going past 100% and settling back reads as cheap.

For a card over black rather than over footage, generate the background instead of
overlaying:

```bash
ffmpeg -f lavfi -i color=c=black:s=1080x1920:d=3:r=30 \
  -f lavfi -i anullsrc=channel_layout=stereo:sample_rate=48000 \
  -vf "subtitles=title.ass" -c:v libx264 -crf 20 -pix_fmt yuv420p -c:a aac -shortest card.mp4
```

Then join it with [assembly.md](assembly.md).

## Per-character entrance

No token-motion API exists. Emit one event per character with staggered starts:

```
Dialogue: 0,0:00:01.00,0:00:04.00,Body,,0,0,0,,{\pos(400,960)\fad(150,0)}开
Dialogue: 0,0:00:01.06,0:00:04.00,Body,,0,0,0,,{\pos(470,960)\fad(150,0)}始
Dialogue: 0,0:00:01.12,0:00:04.00,Body,,0,0,0,,{\pos(540,960)\fad(150,0)}了
```

Each glyph needs an explicit `\pos`, so you must know the advance width. For CJK at
`\fs`=N the advance is N pixels per character, which makes this tractable; for Latin
text it is not, and you should use a whole-line `\fad` instead. 60–80 ms per
character is the readable range.

## PNG and logo overlays

```bash
# Static, top-right, 40px inset
ffmpeg -i in.mp4 -i logo.png \
  -filter_complex "[1:v]scale=160:-1[lg];[0:v][lg]overlay=W-w-40:40" \
  -c:a copy out.mp4

# Visible only between 2s and 8s, fading at both ends
ffmpeg -i in.mp4 -i logo.png \
  -filter_complex "[1:v]scale=160:-1,format=rgba,fade=t=in:st=0:d=0.4:alpha=1,fade=t=out:st=5.6:d=0.4:alpha=1[lg]; \
                   [0:v][lg]overlay=W-w-40:40:enable='between(t,2,8)'" \
  -c:a copy out.mp4

# Slide in from the right over 0.5s
ffmpeg -i in.mp4 -i logo.png \
  -filter_complex "[0:v][1:v]overlay=x='if(lt(t,0.5), W-(t/0.5)*(w+40), W-w-40)':y=40" \
  -c:a copy out.mp4
```

`format=rgba` before an alpha fade is required — without it the fade applies to
colour, not transparency. `enable='between(t,a,b)'` gates by **timeline** seconds.

## Layering order

ASS `Layer` is painted low to high. Keep a stable convention:

| Layer | Content |
|---|---|
| 0 | plates, rule bars, background shapes |
| 1 | titles, lower thirds |
| 2 | body captions |
| 3 | badges, callouts, watermarks |

Burn all text in **one** `subtitles` pass. Each additional burn is another full
re-encode and another generation of quality loss.

## What not to attempt

Springs, physics, morphing paths, shared counters, particle fields, 2.5D camera
moves and GLSL shaders have no equivalent here. When a request needs them, say
plainly that this toolchain does deterministic overlays and simple tweens only, and
offer the closest honest approximation — usually a fade, a wipe, or a cut.
