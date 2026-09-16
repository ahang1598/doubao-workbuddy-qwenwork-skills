# Motion language

Vocabulary for the `prompt` field of a generative edit. WorkRally's video models are
Chinese-first, so write these terms in Chinese — translating them to English costs
fidelity.

This is prompt craft, not an API. Nothing here is a preset name; combine terms.

## Two axes, kept separate

Confusing camera movement with subject movement is the most common reason an edit
comes back wrong. Name them separately in the prompt.

**Camera（镜头运动）**

| Term | Meaning |
|---|---|
| `固定镜头` | locked off, no camera movement |
| `缓慢推近` / `快速推近` | dolly / push in |
| `拉远` | pull back |
| `左摇` / `右摇` | pan |
| `上摇` / `下摇` | tilt |
| `跟随` | tracking with the subject |
| `环绕` | orbit around the subject |
| `手持轻微晃动` | handheld micro-shake |
| `升格` | slow motion (over-cranked) |
| `甩镜` | whip pan |

**Subject（主体运动）**

| Term | Meaning |
|---|---|
| `走向镜头` / `走出画面` | approach / exit frame |
| `转身` / `回头` | turn / glance back |
| `抬手` `低头` `坐下` | discrete gestures |
| `头发被风吹动` | ambient secondary motion |
| `衣物自然摆动` | cloth motion |

## Preserving motion during an edit

For `VideoEdit` and `SmartEdit`, what you *don't* want changed matters as much as
what you do. The models will happily re-choreograph a shot you only asked to recolour.

Lock the motion explicitly:

```
镜头运动、机位、构图与画面时长完全保持不变。
人物的动作节奏与走位不变。
```

Include this in almost every `VideoEdit` prompt. Omitting it is why edits come back
with a different camera move.

## Intensity

Models over-read intensity adjectives. A modifier alone shifts the result more than
expected.

| Level | Phrasing |
|---|---|
| Barely there | `极其轻微的`、`几乎察觉不到的` |
| Subtle (default) | `缓慢的`、`轻微的`、`自然的` |
| Noticeable | `明显的`、`稳定匀速的` |
| Strong | `快速的`、`剧烈的`、`猛然` |

Start subtle. Escalating on a second pass is cheap; walking back an over-driven
result usually is not.

## Timing words

Duration lives in the `duration` parameter, not the prompt. But *phrasing* within the
clip does belong in the prompt:

- `全程匀速` — constant throughout
- `先静止片刻，再缓慢推近` — hold, then move
- `动作在中段完成，结尾回到静止` — settle before the end

The last one matters for `ExtendVideo`: a tail that ends in motion is hard to cut
away from.

## Lighting and atmosphere

| Axis | Terms |
|---|---|
| Direction | `正面光` `侧光` `侧逆光` `逆光` `顶光` |
| Quality | `柔光` `硬光` `漫射` `点状光源` |
| Colour temp | `暖调` `冷调` `中性` `橙青对比` |
| Time | `清晨` `正午` `黄昏` `蓝调时刻` `夜晚` |
| Atmosphere | `薄雾` `雨天` `逆光尘埃` `霓虹反射` |

Change one axis per pass. `改成黄昏` and `改成逆光` are both defensible; asking for
both plus a wardrobe swap in one prompt is not.

## Continuity for `ExtendVideo`

The extension must feel like the same take. Carry these forward explicitly:

```
延续前一段的镜头运动方向与速度，保持相同的光线、色调与景深，
人物服装、发型与所处环境完全一致。
```

Then describe only what is new. Describing the whole scene again invites the model to
reinterpret it.

## What not to write

- **No shot-count or edit language.** `切三个镜头`, `快切蒙太奇` — the model
  generates one continuous shot. Multiple shots means multiple generations plus a
  local concat.
- **No timecodes.** `在第 3 秒时` is not honoured. Split the clip and edit the
  segment instead.
- **No director, cinematographer, studio or franchise names.** Translate the intended
  look into concrete light, palette, lens and texture terms. These names must not
  appear in prompts, progress messages, error text or delivery notes.
- **No negative-prompt field.** `canvas_generate_video` has no separate negative
  parameter. Express exclusions as positive constraints
  (`背景保持干净，没有额外人物` rather than a negative list).
