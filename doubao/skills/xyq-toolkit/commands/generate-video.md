# generate-video：生视频

适用于文生视频、参考图/视频/音频生成、视频编辑、视频延长、首尾帧生成，以及 Draft 样片和转成片。仅处理已有视频的清晰度或字幕时，分别使用 [超分](video-super-resolution.md)、[擦字幕](erase-video-subtitle.md)。

## 输入与参数

| 参数 | 必填 | 规则 |
| --- | --- | --- |
| `--prompt` | 按阶段 | 用户原始描述，不能全为空白；传入非空 `--draft-task-id` 转成片时可省略 |
| `--model` | 是 | 用户指定的准确模型枚举；未明确模型时先确认，不猜测 |
| `--image` | 否 | 本地图片路径，重复参数 |
| `--video` | 按模式 | 本地视频路径，重复参数；视频编辑、视频延长需提供原视频 |
| `--audio` | 否 | 本地 `.mp3/.wav` 音频路径，重复参数 |
| `--duration` | 按模式、阶段 | 整数秒；Seedance 2.5 / Draft 编辑模式不传或传 `-1`，其他三种模式为 `4–30` 秒；Draft 转成片不传。其他模式按模型配置：MiniMax、Wan、HappyHorse 可省略，其他模型需明确提供；用户只给时长范围时先确认具体秒数 |
| `--ratio` | 按模式、阶段 | 比例字符串，不转换为生图枚举；Seedance 2.5 编辑、延长、首尾帧模式不传或传 `adaptive`；Draft 转成片不传。其他模式按模型配置：MiniMax、Wan、HappyHorse 可省略，其他模型需明确提供 |
| `--resolution` | 按模型 | Draft 两阶段不传，服务端固定样片 480p、成片 1080p；`Seedance_2.0_mini`、`Seedance_2.0_mini_lite` 可省略，服务端默认 `720p`；MiniMax、Wan、HappyHorse 可省略；其他模型需明确提供 |
| `--generate-type` | 否 | 首尾帧任务传 `1`；其他显式值交服务端处理 |
| `--task-type` | 否 | 生成模式：`auto/reference/edit/extend`，未传时保持缺省 |
| `--seed` | 否 | 自定义 seed，显式 `0/-1` 保留，未传时保持缺省 |
| `--draft` | 否 | 生成样片；显式 `--draft=false` 保留 false，未传时省略字段 |
| `--draft-task-id` | 否 | 生成成片时提供查询结果中的原始样片任务 ID |

当前支持的模型以 `pippit-tool-cli model list` 为准，完整参数配置用 `pippit-tool-cli model describe MODEL_KEY` 查询；缓存有效期为 5 分钟，需要最新结果时加 `--refresh`。详情见 [模型发现](model.md)。CLI 不自行维护模型白名单或分辨率组合校验。

本地图片支持 `.jpg/.jpeg/.png/.gif/.bmp/.webp/.svg`；视频支持 `.mp4/.avi/.mov/.wmv/.flv/.webm/.mkv/.m4v`；音频支持 `.mp3/.wav`。CLI 内部上传参考素材，保留文件后缀校验和 prompt 非空校验，仅传入非空 `--draft-task-id` 时允许省略 prompt。不新增生成参数范围或组合校验，不补可选参数默认值。

## Seedance 2.5 四种模式

先确认当前模型配置已开放对应模式，再按下表组装输入。Draft 样片在服务端开放后沿用这组模式输入；转成片只需模型和 `draft_task_id`，见下节。

| 模式 | `creation_modes.key` | CLI 参数与输入 | 时长、比例 |
| --- | --- | --- | --- |
| 参考生成 | `reference_generation` | `--task-type reference`、prompt，按需提供图片/视频/音频 | duration 为 `4–30` 秒；ratio 按用户要求和模型配置提供 |
| 视频编辑 | `video_edit` | `--task-type edit`、prompt、`--video` 原视频 | duration 不传或 `-1`；ratio 不传或 `adaptive` |
| 视频延长 | `video_extend` | `--task-type extend`、prompt、`--video` 原视频 | duration 为 `4–30` 秒；ratio 不传或 `adaptive` |
| 首尾帧 | `first_last_frame` | `--generate-type 1`、prompt，按首帧、尾帧顺序传图片（支持仅首帧，最多两张），不传 task-type，不传视频/音频 | duration 为 `4–30` 秒；ratio 不传或 `adaptive` |

`auto` 是下游自动判断模式的值，不对应上述四个页面选项。不要把 `video_edit`、`video_extend` 等配置 key 直接作为 `--task-type` 的值。

## Seedance 2.5 Draft 两阶段

两个阶段都使用准确枚举 `Seedance_2.5_draft`。这些参数需要服务端已支持 Draft 协议，并允许无 prompt 的二阶段请求；CLI 支持不等于目标环境已经开放。

第一阶段：提交样片并查询下载结果。

```bash
pippit-tool-cli generate-video \
  --model Seedance_2.5_draft --draft \
  --prompt "小猫钓鱼视频" --task-type reference \
  --ratio 16:9 --duration 10

pippit-tool-cli query-result \
  --thread-id DRAFT_THREAD_ID --run-id DRAFT_RUN_ID \
  --download-dir ./xyq_output/draft
```

向用户展示样片视频。保存查询结果中该视频的 `draft_task_id`，不要使用 `run_id`、视频资产 ID 或编辑器 `draft_key` 替代。用户尚未要求生成成片时，在预览阶段停止。

第二阶段：用户明确要求生成成片后，提交同一模型和样片 ID。

```bash
pippit-tool-cli generate-video \
  --model Seedance_2.5_draft \
  --draft-task-id DRAFT_TASK_ID

pippit-tool-cli query-result \
  --thread-id FINAL_THREAD_ID --run-id FINAL_RUN_ID \
  --download-dir ./xyq_output/final
```

成片继承样片的提示词、素材、时长、比例和 seed，无需重复提交，也不切换成 `Seedance_2.5`。样片与成片分别计费；下游固定样片 480p、成片 1080p，样片须在创建后 7 天内转成片。CLI 不推算过期时间、不自动进入下一阶段、不维护本地状态机。需要恢复样片 ID 时查询第一阶段的 thread/run，以实际返回的 `draft_task_id` 为准；缺失时按[样片结果说明](query-result.md#样片结果)处理。


## 模型与模式

先从模型列表取得准确 key，再查看配置中的分辨率、时长、比例和创作模式。配置会随服务端调整，本页示例不作为可用模型或参数范围清单。

MiniMax、Wan、HappyHorse 可省略分辨率、时长、比例，由服务端配置补默认值。MiniMax 的兼容输入 `720p` 会映射到 `768p`，Wan/HappyHorse 的 `720p` 保持不变。Max 首尾帧模式会按素材采用自适应比例。素材可用组合以当前配置和服务端校验为准，CLI 不限制素材数量。

```bash
pippit-tool-cli model list
pippit-tool-cli model describe MiniMax-H3
pippit-tool-cli generate-video --prompt "用户原始描述" --model MiniMax-H3 --ratio 16:9
```

模型查询失败时提示重试，不从本文示例推定模型仍然可用，不自行替换用户指定的模型。Wan 同样必须有提示词；文件和网页链接输入不在本命令范围内。

## 最小调用

`Seedance_2.0_mini` 和 `Seedance_2.0_mini_lite` 可以省略分辨率，CLI 不补值，交由服务端默认使用 `720p`：

```bash
pippit-tool-cli generate-video --prompt "用户原始描述" --model Seedance_2.0_mini --duration 5 --ratio 16:9
```

`seedance2.0_vision` 仍需指定分辨率：

```bash
pippit-tool-cli generate-video --prompt "用户原始描述" --model seedance2.0_vision --duration 5 --ratio 16:9 --resolution 720p
```

首尾帧场景：明确两张图片的角色，按首帧、尾帧顺序传两次 `--image`，固定传 `--generate-type 1`。MiniMax 只给首帧时也可传一张图片，仍需 `--generate-type 1`。缺少图片、角色不清或无法确定原始描述时先询问。完整示例见 [首尾帧生视频](../examples/first-last-frame.md)。

## 返回与处理

成功返回 `thread_id`、`run_id`、`web_thread_link`，继续 [异步结果与媒体交付](../workflows/async-delivery.md)。素材、权限或参数失败时说明原因，不自动降低用户指定的模型、分辨率或删减素材。无法确认提交是否成功时，不重复生成。

`--source` 是可选来源统计参数，由宿主 Agent 根据真实环境静默填写（如 `doubao_office`、`workbuddy`、`codex`）；来源不明时省略，不询问用户，不改变 prompt 或创作参数。详见 [宿主来源统计](../SKILL.md#宿主来源统计)。
