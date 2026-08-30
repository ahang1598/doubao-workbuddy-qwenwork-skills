#  MCP 模型参数介绍

提交前仍须重新调用 `who_am_i`；如果模型、默认值、枚举、必填项或 inputs 已变化，使用实时值。顶层 `model` 必须使用目标工具实时清单中的规范模型名；所有 `arguments[].value` 都以字符串传递，包括布尔值和 JSON 数组。

## 完整 input 名称索引

- 多图参考：`image_1`、`image_2`、`image_3`、`image_4`、`image_5`、`image_6`、`image_7`、`image_8`、`image_9`、`image_10`。
- 首尾帧：`first_image`、`tail_image`。
- 2.1 参考角色：`subject_image_0`、`subject_image_1`、`subject_image_2`、`subject_image_3`、`scene_image`、`style_image`。
- 动作控制：`image`、`video`。

只在目标模型当次 inputs 数组声明相应名称时传入。

## `text_to_image`

- `kling-image-v3_0_omni`
  - 参数：`prompt` 必填；`img_resolution=4k`（`1k/2k/4k`）；`aspect_ratio=3:4`（`auto/9:16/2:3/3:4/1:1/4:3/3:2/16:9/21:9`）；`imageCount=1`（`1–9`）；`elements` 最多 10。
  - inputs：无。
- `kling-image-o1`
  - 参数：`prompt` 必填；`img_resolution=2k`（`1k/2k`）；`aspect_ratio=3:4`（`9:16/2:3/3:4/1:1/4:3/3:2/16:9/21:9`）；`imageCount=1`（`1–9`）；`elements` 最多 10。
  - inputs：无。
- `kling-image-v3_0`
  - 参数：`prompt` 必填；`img_resolution=2k`（`1k/2k`）；比例同 O1；`imageCount=1`（`1–9`）；`elements` 最多 10。
  - inputs：无。
- `kling-image-v2_1`
  - 参数：`prompt` 必填；`img_resolution=2k`（`1k/2k`）；`aspect_ratio=3:4`（`9:16/2:3/3:4/1:1/4:3/3:2/16:9/21:9`）；`imageCount=1`（`1–9`）。
  - inputs：无。

工具级说明明确禁止 `text_to_image` 使用 Element，因此即使 `who_am_i` 列出 `elements`，也不得传 `elements` 或在提示词中使用 `<<<id>>>`。

## `image_to_image`

- `kling-image-v3_0_omni`
  - 参数：`prompt` 必填；`img_resolution=4k`（`1k/2k/4k`）；`aspect_ratio=3:4`（含 `auto`）；`imageCount=1`（`-1` 或 `1–9`）；`story_mode=false`；`elements` 最多 10。
  - inputs：`image_1` 必填；`image_2` 至 `image_10` 选填。
- `kling-image-o1`
  - 参数：`prompt` 必填；`img_resolution=2k`（`1k/2k`）；比例含 `auto`；`imageCount=1`（`1–9`）；`elements` 最多 10。
  - inputs：`image_1` 必填；`image_2` 至 `image_10` 选填。
- `kling-image-v3_0`
  - 参数：`prompt` 必填；`img_resolution=1k`（`1k/2k`）；比例含 `auto`；`imageCount=1`（`1–9`）；`elements` 最多 10。
  - inputs：`image_1` 必填；`image_2` 至 `image_10` 选填。
- `kling-image-v2_1`
  - 参数：`prompt` 选填；`aspect_ratio=1:1`（`9:16/2:3/3:4/1:1/4:3/3:2/16:9/21:9`）；`imageCount=1`（`1–9`）。
  - inputs：`subject_image_0`、`subject_image_1`、`subject_image_2`、`subject_image_3`、`scene_image`、`style_image` 均选填。
  - 每个 `subject_image_N` 的模型说明要求同时提供同 URL 的 `raw_subject_image_N`，且 subject、scene、style 合计至少两张不同图片；当前 inputs 数组没有声明 raw 字段，这是服务端 schema 缺口，冲突未修复前不得猜测提交。

对 3.0 Omni、O1、3.0，当前前两个 inputs 说明要求 URL 来自 `file_upload`，不能直接使用本地路径或任意外链；对同一模型的其余图片输入采用相同的更严格限制。

## `text_to_video`

- `kling-video-v2_5`
  - 参数：`prompt` 必填；`duration=5`（`5/10`）；`aspect_ratio=16:9`（`16:9/9:16/1:1`）；`imageCount=1`（`1–4`）；`resolution=1080p`（`720p/1080p`）；`enable_audio=true`；`enable_asmr=false`；`audio_prompt`、`music_prompt` 选填。
  - inputs：无。
- `kling-video-o1`
  - 参数：`prompt` 必填；`duration=5`（`3–10`）；`aspect_ratio=16:9`；`resolution=1080p`；`imageCount=1`（`1–4`）；`elements` 最多 7。
  - inputs：无。
- `kling-video-v3_0_omni`
  - 参数：`prompt` 必填；`duration=5`（`3–15`）；`aspect_ratio=16:9`；`resolution=4k`（`720p/1080p/4k`）；`imageCount=1`（`1–4`）；`prefer_multi_shots=false`；`enable_audio=false`；`elements` 最多 7。
  - inputs：无。
- `kling-video-v3_0`
  - 参数同 3.0 Omni；`elements` 最多 3。
  - inputs：无。
- `kling-video-v3_0_turbo`
  - 参数：`prompt` 必填；`duration=5`（`3–15`）；`resolution=1080p`（`720p/1080p`）；`imageCount=1`（`1–4`）；`aspect_ratio=16:9`。
  - inputs：无。

工具级说明明确禁止 `text_to_video` 使用 Element；不得传 `elements` 或 `<<<id>>>`。

## `image_to_video`

- `kling-video-v3_0_omni`
  - 参数：`prompt` 必填；`duration=5`（`3–15`）；`aspect_ratio=16:9`；`resolution=4k`（`720p/1080p/4k`）；`imageCount=1`（`1–4`）；`prefer_multi_shots=false`；`enable_audio=false`；`elements` 最多 7。
  - inputs：`image_1` 必填；`image_2` 至 `image_7` 选填。
- `kling-video-v3_0`
  - 参数：`prompt` 选填；`duration=5`（`3–15`）；`resolution=4k`；`imageCount=1`（`1–4`）；`prefer_multi_shots=true`；`enable_audio=false`；`elements` 最多 3。
  - inputs：`first_image` 必填；`tail_image` 选填。
- `kling-video-v3_0_turbo`
  - 参数：`prompt` 选填；`duration=5`（`3–15`）；`resolution=1080p`（`720p/1080p`）；`imageCount=1`（`1–4`）。
  - inputs：`first_image` 必填。

3.0 与 Turbo 的 frame input 当前要求使用 `file_upload` 返回 URL。

## `motion_control`

- `kling-video-v2_6`
  - 参数：`prompt` 选填；`motionId` 选填；`motionDirection` 必填（`image_direction/motion_direction`）；`resolution=720p`（`720p/1080p`）；`keepOriginalSound=true`（`true/false`）。
  - inputs：`image` 必填；`video` 选填。
- `kling-video-v3_0`
  - 参数同 2.6，另有 `elements` 最多 1。
  - inputs：`image` 必填；`video` 选填。

`motionId` 与 `video` 必须二选一。`image_direction` 只支持 3–10 秒动作；`motion_direction` 跟随动作视频方向。
