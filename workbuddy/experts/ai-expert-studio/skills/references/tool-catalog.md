# AI-HIVE Connector 工具契约

适用契约：`@infimind-next/ai-hive-mcp` 0.2.5；Connector 必须在运行时实际暴露对应工具字段。

这是两个专家包唯一的工具字段来源。模型、价格、参数枚举与路由可用性始终以运行时 `list_models` 返回为准。

## 通用调用顺序

1. 需要执行时调用 `get_user_info` 检查账户和余额。
2. 调用 `list_models` 获取实时模型目录。
3. 选择 `publicModelId` 和该模型实际返回的 `routingMode`。
4. 从同一模型的 `pricingSnapshot` 数组中选出同一路由记录，原样传回。
5. 有本地素材时先调用 `upload_media_from_path`，按媒体类型保存返回的 `mediaId` 和 `mediaType`。
6. 展示模型、路由、批量、主要参数和价格摘要；调用 `chat_text`、`generate_image` 或 `generate_video` 前取得用户确认。
7. 调用对应付费工具。异步生成只用返回的真实 `taskId` 查询状态。

## 工具输入

### `get_user_info`

不接收参数，返回账户和余额摘要。

### `list_models`

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `modelType` | `TEXT \| IMAGE \| VIDEO` | 否 | 按资源类型过滤。 |

返回的每个模型包含 `publicModelId`、`routingModes`、`pricingSnapshot`，以及相应的 `textConfig`、`imageConfig` 或 `videoConfig`。不得推荐返回结果中不存在的模型、路由或参数枚举。

### `upload_media_from_path`

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `path` | string | 是 | 用户明确授权的本地绝对路径。 |
| `filename` | string | 否 | 需要覆盖上传文件名时使用。 |
| `contentType` | string | 否 | 需要明确 MIME 类型时使用。 |

文件类型由文件名和 MIME 类型识别；显式 MIME 会先去除首尾空白并转为小写。音频只接受 MP3 或 WAV，支持 `audio/mpeg`、`audio/mp3`、`audio/wav`、`audio/x-wav`，客户端单文件上传上限为 15 MiB。

上传成功后保存真实 `mediaId`；音频返回必须确认 `mediaType=AUDIO`，然后才可把该 ID 放入视频调用的 `audioMediaIds`。音频不得用于 `chat_text`、聊天音频、语音转写、TTS 或音频生成。

### `chat_text`

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `publicModelId` | string | 是 | 来自实时模型目录。 |
| `routingMode` | string | 是 | 必须是该模型实际返回的路由。 |
| `messages` | array | 是 | 至少包含一条用户消息；消息含 `role`、`content`、`mediaIds`。 |
| `thinkingEnabled` | boolean | 否 | 仅在模型能力支持且用户需要时启用。 |
| `pricingSnapshot` | object | 是 | 同模型、同路由的价格快照，原样传回。 |

### `generate_image`

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `publicModelId` | string | 是 | 来自实时图片模型目录。 |
| `routingMode` | string | 是 | 该模型实际支持的路由。 |
| `prompt` | string | 是 | 图片提示词。 |
| `batchSize` | integer | 是 | 1–10；增加数量会增加费用。 |
| `imageMediaIds` | string[] | 是 | 无参考图时传空数组。 |
| `params` | object | 是 | 只放 `imageConfig` 支持的分辨率、比例、质量、格式等参数。 |
| `pricingSnapshot` | object | 是 | 同模型、同路由的价格快照。 |

### `generate_video`

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `publicModelId` | string | 是 | 来自实时视频模型目录。 |
| `routingMode` | string | 是 | 该模型实际支持的路由。 |
| `prompt` | string | 是 | 视频提示词，不混入接口字段说明。 |
| `imageMediaIds` | string[] | 是 | 图片、主体、场景、关键帧参考；不用时传空数组。 |
| `videoMediaIds` | string[] | 是 | 动作参考、编辑母版或延长源；不用时传空数组。 |
| `audioMediaIds` | string[] | 是 | 音色、旁白、音乐或音效参考；不用时传空数组。 |
| `firstFrameMediaId` | string | 否 | 首帧图片。 |
| `lastFrameMediaId` | string | 否 | 尾帧图片。 |
| `params` | object | 是 | 只放 `videoConfig` 支持的时长、比例、分辨率、音频、格式等参数。 |
| `pricingSnapshot` | object | 是 | 同模型、同路由的价格快照。 |

同一个媒体 ID 只放入与其真实类型一致的字段。首尾帧场景使用独立字段，其他图片仍可放入 `imageMediaIds`。

计划使用音频时，先确认运行时 `generate_video` schema 包含 `audioMediaIds`；字段缺失时停止音频执行，并提示用户升级或更新 Connector。不得把音频 ID 塞入图片、视频或聊天媒体字段绕过门禁。

### `get_generation_task`

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `taskId` | string | 是 | 来自图片或视频创建调用的真实返回值。 |

## 任务状态与失败结构

- `PENDING`、`SUBMITTED`、`PROCESSING`：继续查询原 `taskId`，不得创建替代任务。
- `COMPLETED`：检查结果 URL、数量和工具返回的元数据后交付。
- `FAILED`：展示 `failure.code`、`failure.summary`、`failure.suggestion`。

超出观察窗口时只报告仍在处理并保留 `taskId`。调整 Prompt、参数、模型或路由后再次调用属于新付费任务，必须重新取得用户确认。

## 禁止事项

- 不自行构造模型 ID、价格快照、参数枚举或路由。
- 不把接口参数混进 Prompt。
- 不在未得到用户授权时读取或上传本地文件。
- 不在失败、超时或结果未确认时自动创建新的付费任务。
