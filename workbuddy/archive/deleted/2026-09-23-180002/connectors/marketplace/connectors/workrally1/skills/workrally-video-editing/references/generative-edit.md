# Generative edit — the three `canvas_generate_video` edit modes

WorkRally exposes exactly three edit-oriented driver modes. Everything else on
`canvas_generate_video` (`Text`, `FirstLastFrame`, `SubjectToVideo`) creates new
footage and is out of scope for this skill.

All three consume an **asset_id**, never a URL and never a local path. Upload first
(`upload_file` → `asset_create`), probe second (`scripts/probe_video.sh`), submit third.

## Model discovery (mandatory, every session)

Call `canvas_video_provider_config` before the first submission. It returns provider
groups; pick the one that matches your mode:

| mode | provider group | notes |
|---|---|---|
| `VideoEdit` | `video_edit_providers` | capability 6 |
| `SmartEdit` | `smart_edit_providers` | capability 16 |
| `ExtendVideo` | `subject_to_video_providers` | reuses the reference-to-video capability |

Use the `provider` field as `model`. Never guess an ID — the available set differs
per environment (dev / staging / prod) and an unknown provider is rejected outright.

Per-provider fields that gate what you can submit:

| field | meaning |
|---|---|
| `duration_options` | allowed `duration` values in seconds |
| `resolution_options` | allowed `resolution` enums, each `{value, label}` |
| `max_video_count` / `max_image_count` / `max_audio_count` | reference asset caps |
| `max_video_duration` | longest source the model accepts |
| `extend_duration_range` / `extend_video_max_duration` | **ExtendVideo only**; empty means this provider cannot extend |
| `support_audio` | model can emit a native audio track |
| `support_erase_subtitles` | `enable_erase_subtitles` is accepted |

If no provider in the required group comes back, the capability is unavailable in
this environment. Say so and stop — do not fall back to a different mode and
pretend it is the same thing.

## Resolution enum (video ≠ image)

`1`=480P `2`=540P `3`=720P `4`=1080P `5`=1440P `6`=2160P.
Must come from that provider's `resolution_options[].value`. Omit it and the backend
picks the model's first available tier.

`VideoEdit` ignores `resolution` entirely — do not send it.

## Aspect ratio

WorkRally accepts `21:9` `16:9` `4:3` `2:1` `1:1` `1:2` `3:4` `9:16`.
There is no `4:5`, `2:3`, `3:2`, `3:1` or `4:1`. Map Instagram vertical to `3:4`,
Pinterest to `3:4`, horizontal editorial to `4:3`, ultrawide banners to `21:9`,
then crop locally with ffmpeg if the platform needs an exact native size — and tell
the user you cropped.

`SmartEdit` derives geometry from `source_video` and submits `ratio: "adaptive"`;
an `aspect_ratio` argument does not override the source there.

---

## Mode 1 — `VideoEdit` (prompt-driven repaint)

Rewrites the picture of an existing clip according to a prompt. Broad, whole-frame
changes: style, weather, time of day, wardrobe, set dressing.

```jsonc
canvas_generate_video({
  mode: "VideoEdit",
  prompt: "<中文编辑指令，必填>",
  model: "<video_edit_providers[].provider>",
  origin_video: "<源视频 asset_id>",
  count: 1,
  task_name: "<素材名_编辑意图>"
})
```

- `origin_video` is a bare **asset_id string**, not an object.
- `prompt` is **required**. An empty prompt is rejected.
- Do not send `resolution`.

**Prompt shape.** State the change, then state what must not change. Models drift
on everything you leave unspoken.

```
把画面改成黄昏时分的暖调侧逆光，天空转为橙紫渐变，地面出现长投影。
人物的身份、五官、发型、服装款式与镜头运动完全保持不变，构图与画面时长不变。
```

Keep one change axis per submission. "改成黄昏 + 换成冬装 + 加下雪" in one prompt
reliably produces a mess; run them as separate passes and chain the outputs.

## Mode 2 — `SmartEdit` (targeted object / person replacement)

Aligns with the Web「梦宝智能编辑」. Swaps a specific subject inside the frame while
holding the rest of the shot.

```jsonc
canvas_generate_video({
  mode: "SmartEdit",
  prompt: "<中文替换指令；可为空>",
  model: "<smart_edit_providers[].provider>",
  source_video: {
    asset_id: "<源视频 asset_id>",
    width: 1920,        // 必填，> 0
    height: 1080,       // 必填，> 0
    duration: 12480     // 必填，> 0，单位【毫秒】
  },
  reference_assets: [
    { type: "image", url: "<替换目标的参考图URL>" }
  ],
  count: 1,
  task_name: "<素材名_替换目标>"
})
```

- **`width` / `height` / `duration` are all mandatory and must be positive.**
  `duration` is in **milliseconds** — `scripts/probe_video.sh` emits `duration_ms`
  for exactly this field. Passing seconds here is the single most common failure.
- `prompt` may be empty when the reference image alone is unambiguous.
- `reference_assets` accepts `image` / `video` / `audio`. Images may pass `url`;
  video and audio should pass `asset_id`. The source video is added automatically —
  do not list it again in `reference_assets`.
- Output duration follows the source (`duration` seconds = `round(duration_ms/1000)`).

**Prompt shape.** Name the thing being replaced by its on-screen position and
appearance, name what replaces it, then lock the rest.

```
把画面中桌上的那个白色马克杯替换成第一张图片里的保温杯，
保持它原有的位置、大小、透视与被手握持的关系不变。
其余画面、人物、光线、镜头运动完全不变。
```

Multiple reference images are addressed **positionally**: 「第一张图片」「第二张图片」
mapping to the `reference_assets` order. Do not use Higgsfield's
`IMAGE REFERENCES: image 1 = ...` list form.

## Mode 3 — `ExtendVideo` (continue past the end)

Generates new footage continuing from the end of the source.

```jsonc
canvas_generate_video({
  mode: "ExtendVideo",
  prompt: "<中文续接指令；可为空>",
  model: "<subject_to_video_providers[].provider，需 extend_duration_range 非空>",
  source_video: { asset_id: "<源视频 asset_id>" },
  duration: 5,          // 【延长的秒数】，必填且 > 0
  reference_assets: [{ type: "image", url: "<构图参考图URL>" }],
  count: 1,
  task_name: "<素材名_延长>"
})
```

- `duration` here is **how many seconds to add**, not the target total length.
  Required and must be > 0; keep it inside the provider's `extend_duration_range`.
- `source_video` only needs `asset_id`; width/height/duration are not required.
- `reference_assets` accepts **images only**. Passing a video or audio entry is
  rejected — the source belongs in `source_video`.
- Providers with an empty `extend_duration_range` cannot extend. Filter them out.

**Prompt shape.** Describe the continuation as motion, not as a new scene.

```
镜头继续向右平移，人物走出画面右侧，背景的街景自然延续，
光线、色调与镜头速度与前面保持一致。
```

An empty prompt lets the model infer the continuation — often the better choice for
a short 2–3 second tail.

---

## Native audio

Providers with `support_audio: true` emit a native soundtrack. `enable_sound`
defaults to `true` when omitted; pass `false` explicitly to keep the edit silent —
which is usually what you want when the source already has usable production audio
that you plan to remux with ffmpeg afterwards.

Do not run a separate TTS pass and re-mux when the model already carries native audio.

## Subtitle erase (not burn)

`enable_erase_subtitles: true` removes hard-burned subtitles already present in the
source. Only send it when the chosen provider reports `support_erase_subtitles: true`.

WorkRally has **no subtitle burn tool**. Adding captions is a local ffmpeg job — see
[caption-systems.md](caption-systems.md).

## Submit, poll, freeze

```
canvas_generate_video(...) → { task_ids: [...] }   // length ≈ count
canvas_get_task(task_id)   → state: 1排队 2运行 3暂停 4成功 5失败 6取消
```

Poll every 3 seconds, each task_id separately. On `state=4` read `output_assets`
(`asset_id` / `url` / dimensions). Keep a ledger of `intent → task_id → last state`.

Completed tasks are frozen — never resubmit them. A polling timeout is not a
generation failure. Stop after 12 rounds, keep the task_ids, and tell the user what
is still running.

Passing `project_id` (a **canvas ID** from `canvas_manage`, never a short-drama
project ID) makes the canvas show a live placeholder node. No extra
`canvas_manage(build_draft)` call is needed.

## Chaining edits

Each pass consumes the previous pass's output. The output is a **new asset** with its
own `asset_id` and possibly different dimensions and duration:

1. Read `output_assets[].asset_id` from the finished task.
2. Re-probe if the next step is `SmartEdit` or any ffmpeg geometry work —
   do not reuse the original source's width/height/duration.
3. Submit the next pass.

Budget three submissions per deliverable including retries. Rewriting the prompt does
not reset that budget.
