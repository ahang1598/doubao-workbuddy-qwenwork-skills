# Kling MCP 模型参数快照

本快照来自官方 Kling MCP `who_am_i`，`mcpVersion=1.3.1`，核验日期为 2026-08-31。账号等级、区域或服务版本变化时，模型、默认值和允许值都可能变化；每次提交前必须重新调用 `who_am_i`，实时结果优先于本文件。

## 封闭参数规则

- 先确定工具和规范 `model`，再把该模型当次 `arguments[]` 与 `inputs[]` 分别建立为两个白名单。未出现在白名单中的名称一律不得传递。
- `model` 没有可省略的通用默认值，必须传所选工具实时清单中的规范模型名；别名只用于理解用户表达。
- 参数有 `default` 时，用户明确要求或专业 Skill 已从用途可靠推导出合法值则采用该值，否则传实时默认值；不得让默认值覆盖已确定的画幅、单/多镜头或音频意图。任何取值都只能采用该参数当次 `allowedValues` / `allowed_values` 中的精确字符串。
- 必填参数没有默认值时必须补齐；可选参数没有默认值时，只有用户意图确实需要且能得到合法值时才传。不要用空字符串、`null`、空数组或猜测值占位。
- `arguments[].value` 全部使用字符串，包括数字、布尔值和 JSON 数组。每个参数名最多出现一次。
- 模型没有 inputs 时省略顶层 `inputs`；有 inputs 时只传模型声明的名称，满足全部必填项，并使用实时工具 schema 声明的 `inputType`。
- 切换工具或模型后废弃已构造的 `arguments` 和 `inputs`，从新模型的白名单重新构造。

## 分辨率矩阵

`—` 表示该模型在该工具下没有分辨率参数，必须省略。图像只使用 `img_resolution`，视频与动作控制只使用 `resolution`；当前快照没有通用 `quality`、`size`、`width`、`height` 或 `fps` 参数。

| 工具 | 模型 | 参数名 | 默认值 | 允许值 |
| --- | --- | --- | --- | --- |
| `text_to_image` | `kling-image-v3_0_omni` | `img_resolution` | `4k` | `1k`、`2k`、`4k` |
| `text_to_image` | `kling-image-o1` | `img_resolution` | `2k` | `1k`、`2k` |
| `text_to_image` | `kling-image-v3_0` | `img_resolution` | `2k` | `1k`、`2k` |
| `text_to_image` | `kling-image-v2_1` | `img_resolution` | `2k` | `1k`、`2k` |
| `image_to_image` | `kling-image-v3_0_omni` | `img_resolution` | `4k` | `1k`、`2k`、`4k` |
| `image_to_image` | `kling-image-o1` | `img_resolution` | `2k` | `1k`、`2k` |
| `image_to_image` | `kling-image-v3_0` | `img_resolution` | `1k` | `1k`、`2k` |
| `image_to_image` | `kling-image-v2_1` | — | — | — |
| `text_to_video` | `kling-video-v2_5` | `resolution` | `1080p` | `720p`、`1080p` |
| `text_to_video` | `kling-video-o1` | `resolution` | `1080p` | `720p`、`1080p` |
| `text_to_video` | `kling-video-v3_0_omni` | `resolution` | `4k` | `720p`、`1080p`、`4k` |
| `text_to_video` | `kling-video-v3_0` | `resolution` | `4k` | `720p`、`1080p`、`4k` |
| `text_to_video` | `kling-video-v3_0_turbo` | `resolution` | `1080p` | `720p`、`1080p` |
| `image_to_video` | `kling-video-v3_0_omni` | `resolution` | `4k` | `720p`、`1080p`、`4k` |
| `image_to_video` | `kling-video-v3_0` | `resolution` | `4k` | `720p`、`1080p`、`4k` |
| `image_to_video` | `kling-video-v3_0_turbo` | `resolution` | `1080p` | `720p`、`1080p` |
| `motion_control` | `kling-video-v2_6` | `resolution` | `720p` | `720p`、`1080p` |
| `motion_control` | `kling-video-v3_0` | `resolution` | `720p` | `720p`、`1080p` |

## 完整 input 名称索引

- 多图参考：`image_1` 至 `image_10`，但具体上限以所选模型为准。
- 首尾帧：`first_image`、`tail_image`。
- 2.1 参考角色：`subject_image_0`、`subject_image_1`、`subject_image_2`、`subject_image_3`、`scene_image`、`style_image`。
- 动作控制：`image`、`video`。

名称相似不代表可以互换。只在目标模型当次 inputs 白名单声明相应名称时传入。

## `text_to_image`

所有模型 inputs 均为空，提交时省略 `inputs`。

- `kling-image-v3_0_omni`
  - 参数：`prompt` 必填；`img_resolution=4k`（`1k/2k/4k`）；`aspect_ratio=3:4`（`auto/9:16/2:3/3:4/1:1/4:3/3:2/16:9/21:9`）；`imageCount=1`（`1/2/3/4/5/6/7/8/9`）。
- `kling-image-o1`
  - 参数：`prompt` 必填；`img_resolution=2k`（`1k/2k`）；`aspect_ratio=3:4`（`9:16/2:3/3:4/1:1/4:3/3:2/16:9/21:9`）；`imageCount=1`（`1/2/3/4/5/6/7/8/9`）。
- `kling-image-v3_0`
  - 参数：`prompt` 必填；`img_resolution=2k`（`1k/2k`）；`aspect_ratio=3:4`（`9:16/2:3/3:4/1:1/4:3/3:2/16:9/21:9`）；`imageCount=1`（`1/2/3/4/5/6/7/8/9`）。
- `kling-image-v2_1`
  - 参数：`prompt` 必填；`img_resolution=2k`（`1k/2k`）；`aspect_ratio=3:4`（`9:16/2:3/3:4/1:1/4:3/3:2/16:9/21:9`）；`imageCount=1`（`1/2/3/4/5/6/7/8/9`）。

`who_am_i` 在部分图像模型中列出 `elements`，但当前工具级说明明确禁止 `text_to_image` 使用 Element；采用更严格的交集，不传 `elements`，也不在提示词中使用 `<<<id>>>`。

## `image_to_image`

- `kling-image-v3_0_omni`
  - 参数：`prompt` 必填；`img_resolution=4k`（`1k/2k/4k`）；`aspect_ratio=3:4`（`auto/9:16/2:3/3:4/1:1/4:3/3:2/16:9/21:9`）；`imageCount=1`（`-1/1/2/3/4/5/6/7/8/9`）；`story_mode=false`（`true/false`）；`elements` 选填，最多 10。
  - inputs：`image_1` 必填；`image_2` 至 `image_10` 选填。
- `kling-image-o1`
  - 参数：`prompt` 必填；`img_resolution=2k`（`1k/2k`）；`aspect_ratio=3:4`（`auto/9:16/2:3/3:4/1:1/4:3/3:2/16:9/21:9`）；`imageCount=1`（`1/2/3/4/5/6/7/8/9`）；`elements` 选填，最多 10。
  - inputs：`image_1` 必填；`image_2` 至 `image_10` 选填。
- `kling-image-v3_0`
  - 参数：`prompt` 必填；`img_resolution=1k`（`1k/2k`）；`aspect_ratio=3:4`（`auto/9:16/2:3/3:4/1:1/4:3/3:2/16:9/21:9`）；`imageCount=1`（`1/2/3/4/5/6/7/8/9`）；`elements` 选填，最多 10。
  - inputs：`image_1` 必填；`image_2` 至 `image_10` 选填。
- `kling-image-v2_1`
  - 参数：`prompt` 选填且无默认值；`aspect_ratio=1:1`（`9:16/2:3/3:4/1:1/4:3/3:2/16:9/21:9`）；`imageCount=1`（`1/2/3/4/5/6/7/8/9`）。没有 `img_resolution`，不得传分辨率参数。
  - inputs：`subject_image_0`、`subject_image_1`、`subject_image_2`、`subject_image_3`、`scene_image`、`style_image` 均选填。
  - 模型说明要求每个 `subject_image_N` 同时提供同 URL 的 `raw_subject_image_N`，且 subject、scene、style 合计至少两张图片；当前 inputs 白名单没有 raw 字段。冲突未修复前停止，不得猜测字段名提交。

## `text_to_video`

所有模型 inputs 均为空，提交时省略 `inputs`。

- `kling-video-v2_5`
  - 参数：`prompt` 必填；`duration=5`（`5/10`）；`aspect_ratio=16:9`（`16:9/9:16/1:1`）；`imageCount=1`（`1/2/3/4`）；`resolution=1080p`（`720p/1080p`）；`enable_audio=true`（`true/false`）；`enable_asmr=false`（`true/false`）；`audio_prompt`、`music_prompt` 选填且无默认值。
- `kling-video-o1`
  - 参数：`prompt` 必填；`duration=5`（`3/4/5/6/7/8/9/10`）；`aspect_ratio=16:9`（`16:9/9:16/1:1`）；`resolution=1080p`（`720p/1080p`）；`imageCount=1`（`1/2/3/4`）。
- `kling-video-v3_0_omni`
  - 参数：`prompt` 必填；`duration=5`（`3/4/5/6/7/8/9/10/11/12/13/14/15`）；`aspect_ratio=16:9`（`16:9/9:16/1:1`）；`resolution=4k`（`720p/1080p/4k`）；`imageCount=1`（`1/2/3/4`）；`prefer_multi_shots=false`（`true/false`）；`enable_audio=false`（`true/false`）。
- `kling-video-v3_0`
  - 参数：`prompt` 必填；`duration=5`（`3/4/5/6/7/8/9/10/11/12/13/14/15`）；`aspect_ratio=16:9`（`16:9/9:16/1:1`）；`resolution=4k`（`720p/1080p/4k`）；`imageCount=1`（`1/2/3/4`）；`prefer_multi_shots=false`（`true/false`）；`enable_audio=false`（`true/false`）。
- `kling-video-v3_0_turbo`
  - 参数：`prompt` 必填；`duration=5`（`3/4/5/6/7/8/9/10/11/12/13/14/15`）；`resolution=1080p`（`720p/1080p`）；`imageCount=1`（`1/2/3/4`）；`aspect_ratio=16:9`（`16:9/9:16/1:1`）。

`who_am_i` 在部分视频模型中列出 `elements`，但当前工具级说明明确禁止 `text_to_video` 使用 Element；采用更严格的交集，不传 `elements` 或 `<<<id>>>`。

## `image_to_video`

- `kling-video-v3_0_omni`
  - 参数：`prompt` 必填；`duration=5`（`3/4/5/6/7/8/9/10/11/12/13/14/15`）；`aspect_ratio=16:9`（`16:9/9:16/1:1`）；`resolution=4k`（`720p/1080p/4k`）；`imageCount=1`（`1/2/3/4`）；`prefer_multi_shots=false`（`true/false`）；`enable_audio=false`（`true/false`）；`elements` 选填，最多 7。
  - inputs：`image_1` 必填；`image_2` 至 `image_7` 选填。
- `kling-video-v3_0`
  - 参数：`prompt` 选填且无默认值；`duration=5`（`3/4/5/6/7/8/9/10/11/12/13/14/15`）；`resolution=4k`（`720p/1080p/4k`）；`imageCount=1`（`1/2/3/4`）；`prefer_multi_shots=true`（`true/false`）；`enable_audio=false`（`true/false`）；`elements` 选填，最多 3。没有 `aspect_ratio`，不得传画幅参数。
  - inputs：`first_image` 必填；`tail_image` 选填。
- `kling-video-v3_0_turbo`
  - 参数：`prompt` 选填且无默认值；`duration=5`（`3/4/5/6/7/8/9/10/11/12/13/14/15`）；`resolution=1080p`（`720p/1080p`）；`imageCount=1`（`1/2/3/4`）。没有 `aspect_ratio`、`prefer_multi_shots`、`enable_audio` 或 `elements`，均不得传递。
  - inputs：`first_image` 必填。

## `motion_control`

- `kling-video-v2_6`
  - 参数：`prompt` 选填且无默认值；`motionId` 选填且无默认值；`motionDirection` 必填（`image_direction/motion_direction`）；`resolution=720p`（`720p/1080p`）；`keepOriginalSound=true`（`true/false`）。
  - inputs：`image` 必填；`video` 选填。
- `kling-video-v3_0`
  - 参数：`prompt` 选填且无默认值；`motionId` 选填且无默认值；`motionDirection` 必填（`image_direction/motion_direction`）；`resolution=720p`（`720p/1080p`）；`keepOriginalSound=true`（`true/false`）；`elements` 选填，最多 1。
  - inputs：`image` 必填；`video` 选填。

`motionId` 与 `video` 必须二选一。`image_direction` 只支持 3–10 秒动作；`motion_direction` 跟随动作视频方向。不要把动作时长作为未声明的 `duration` 参数传入。
