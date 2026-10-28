# 画质增强

## 能力用途

用于视频画质增强。利用 AI 算法对输入视频进行分析，并智能执行包括但不限于视频去噪、色彩增强、清晰度提升、瑕疵修复和超分辨率的一系列优化操作。提供 standard 和 professional 两种版本：standard 兼顾处理速度与视频画质，内置高频使用的 10 余种增强算法，适用于视频分发场景的画质增强；professional 提供极致画质增强，内置 30 余种深度 AI 增强算法，适用于影视级视频制作。不同版本会影响增强算法的强度、适用场景与计费。

## 参数填写规则

- 可选参数仅在用户明确指定，或可从用户意图准确确定时填写；不得伪造。不能准确确定时省略，确为正确完成任务所必需时先向用户澄清。
## 语义效果选项

### `enhance_style` 可选效果

| 语义名称 | 参数值 | 说明 |
| --- | --- | --- |
| 自然 | `natural` | 降低画质增强强度，锐化痕迹更少，画面观感更自然。 |
| 高清 | `hd` | 增强强度适中，画面锐利清晰。 |

### `scene` 可选效果

| 语义名称 | 参数值 | 说明 |
| --- | --- | --- |
| AIGC 场景 | `aigc` | 对大模型生成的低分辨率视频进行超分处理，并对生成视频的细节进行重绘。 |
| UGC 短视频场景 | `ugc` | 修复短视频多次压缩和传输造成的模糊、块效应与色带失真。 |
| 短剧场景 | `short_series` | 对剧中人像进行增强和细节强化。 |
| 老片修复场景 | `old_film` | 修复老旧影片瑕疵，包括时域去噪、划痕去除、消除闪烁和修正色偏。 |
| 通用模板 | `common` | 通用画质增强模板。 |

### `tool_version` 可选效果

| 语义名称 | 参数值 | 说明 |
| --- | --- | --- |
| 专业版 | `professional` | 提供更强的画质增强并投入更多算力资源。 |
| 标准版 | `standard` | 兼顾处理速度与视频画质，内置高频使用的增强算法。 |

## Cloud

### 命令与生命周期

- 命令：`mediakit-cli video enhance-video`
- 生命周期：异步
- 返回方式：返回 `task_id`，再查询终态结果。

### 参数

| 参数路径 | CLI flag | 类型 | 必填 | 默认值 | 枚举/范围/结构 | 说明 |
| --- | --- | --- | --- | --- | --- | --- |
| `bit_depth` | `--bit-depth` | integer | 否 | 8 | 枚举: [8,10,12,16] | 目标色深（也称为位深），仅专业版（tool_version 为 professional）支持。取值如下：8：（默认值）8 bit 位深，每个颜色通道有 2⁸（即 256）个亮度等级。支持 h264、h265 编码。10：10 bit 位深，每个颜色通道有 2¹⁰（即 1024）个亮度等级。支持 h265、prores 编码。12：12 bit 位深，每个颜色通道有 2¹²（即 4096）个亮度等级。支持 h265 编码。16：16 bit 位深，每个颜色通道有 2¹⁶（即 65536）个亮度等级。支持 ffv1、exr 编码。注意：请确保输入视频时长不超过 40 秒。此档位下，码率由系统自动决定，bitrate、bitrate_level 参数均不生效。16 bit 色深任务为单任务串行处理，即只能单一任务处理完成后，再开始新任务处理，因此处理时间可能较长。 |
| `bitrate_level` | `--bitrate-level` | string | 否 | "medium" | 枚举: ["low","medium","high"] | 用于控制输出视频的平均码率，会影响视频的视觉质量和最终的文件体积。可选 low、medium、high；其中 high 表示高码率，medium 表示中码率，推荐使用，low 表示低码率；默认 medium。 |
| `client_token` | `--client-token` | string | 否 | - | - | 用户请求凭证，用于幂等控制；大小写敏感，长度不超过 64 个 ASCII 可打印字符。 用于控制异步任务幂等；同步任务不支持幂等校验。异步任务首次提交时默认不传，服务端仍会对相同核心参数执行 24 小时默认幂等。用户明确指定 token 时原样使用。因网络超时、响应丢失等原因重试同一次提交时，原请求有 token 则复用原值，原请求未传则继续不传。任务已有结果后，用户要求“结果不对，重试”“重新跑一次”或“重新发起任务”时，必须生成并传递新的 token，避免返回原任务。新对话中用户要求“重新发起任务”时，若当前上下文具备完整任务参数，直接生成新 token 并提交；若参数不足，先向用户澄清，补齐后再使用新 token 发起，不得直接省略 token。新任务后续发生提交重试时复用该新 token。已有 task_id 且任务尚未完成时，只查询原任务，不得重新提交。CLI runtime 不判断用户意图，也不自动生成 token。 |
| `fps` | `--fps` | number | 否 | - | 最小值: 15；最大值: 120 | 目标帧率，单位为 fps，取值范围为 15 到 120。若未指定 fps，输出视频将保持与原始片源一致的帧率。建议 fps 不超过原片的 4 倍。 |
| `resolution` | `--resolution` | string | 否 | - | 枚举: ["240p","360p","480p","540p","720p","1080p","2k","4k","6k","8k"] | 目标分辨率档位。您可以使用此参数将视频超分到指定规格。支持：240p；360p；480p；540p；720p；1080p；2k；4k；6k；8k 注意：此参数与 resolution_limit 互斥，不可同时配置。 |
| `resolution_limit` | `--resolution-limit` | integer | 否 | - | 最小值: 128；最大值: 4320 | 目标分辨率的短边像素限制，取值范围为 128 到 4320。系统将根据 resolution_limit 在保持原视频宽高比的前提下等比缩放到该限制值。resolution_limit 与 resolution 不可同时配置。 |
| `scene` | `--scene` | string | 否 | "common" | 枚举: ["common","ugc","short_series","aigc","old_film"] | 用于选择一个针对特定业务场景的预设画质增强模板。scene 仅在 tool_version 为 standard 时生效，可选 common、ugc、short_series、aigc、old_film，默认 common。其中 common 表示通用模板，ugc 表示 UGC 短视频场景，short_series 表示短剧场景，aigc 表示 AIGC 内容场景，old_film 表示老片修复场景。 |
| `tool_version` | `--tool-version` | string | 否 | "standard" | 枚举: ["standard","professional"] | 影响增强算法的强度、适用场景与计费。可选 standard 和 professional，默认 standard。其中 standard 表示标准版，兼顾处理速度与视频画质，内置高频使用的 10 余种增强算法，覆盖主流播放平台画质要求，适用于视频分发场景的画质增强；professional 表示专业版，提供极致画质增强，保障镜头级画质效果，内置 30 余种深度 AI 增强算法，适用于影视级视频制作。 |
| `video_url` | `--video-url` | string | 是 | - | - | 待增强的视频 URL，支持本地文件路径和公网 HTTP/HTTPS URL 两种输入协议。支持 mp4、flv、ts、avi、mov、wmv、mkv 等主流视频格式。建议单个输入文件大小不超过 10 GB。输入视频分辨率最高支持 2K，长边范围为 360 到 2560，短边范围为 360 到 1440。 |

| `bitrate` | `--bitrate` | integer | 否 | - | 最小值: 10；最大值: 150000 | 目标平均码率，单位为 kbps，取值范围 [10, 150000]。不填时按 bitrate_level 结合分辨率与帧率自动换算。当同时指定 bitrate 与 bitrate_level 时，仅 bitrate 生效。 |
| `codec` | `--codec` | string | 否 | - | 枚举: ["h264","h265","prores","ffv1","exr"] | 视频编码格式，仅专业版（tool_version 为 professional）支持。指定 codec 时必须同时指定 bit_depth，且两者需为合法组合，若未指定 codec，系统将按 bit_depth 自动选择相应编码：8 的默认编码为 h264；10 和 12 的默认编码为 h265；16 的默认编码为 ffv1。支持的编码格式如下：h264；h265；prores；ffv1；exr 注意：prores、ffv1、exr 编码不支持指定码率，此时 bitrate、bitrate_level 参数均不生效。 |
| `enhance_style` | `--enhance-style` | string | 否 | "hd" | 枚举: ["hd","natural"] | 画质增强风格。标准版（tool_version 为 standard）与专业版（tool_version 为 professional）均支持。可选值：hd：（默认）高清。增强强度适中，画面锐利清晰。natural：自然。降低画质增强强度，锐化痕迹更少，画面观感更自然。 |
### 调用示例

```bash
mediakit-cli video enhance-video \
  --video-url <video_url>
```

仅使用用户真实输入替换占位符；可选 flag 遵守参数填写规则，不得编造 URL、文件、枚举或业务参数。

### 返回结果

| 字段路径 | 类型 | 必含 | 模式 | 说明 |
| --- | --- | --- | --- | --- |
| `request_id` | string | 否 | Cloud | 请求标识；仅在后端返回时出现。 |
| `task_id` | string | 是 | Cloud | 异步任务的唯一标识，用于查询任务状态并获取最终结果。 |
| `task_type` | string | 否 | Cloud | 任务类型；仅在后端实际返回非空值时出现。 |
| `duration` | number | 否 | Cloud 终态 | 输出视频的总时长，单位为秒。 |
| `fps` | number | 否 | Cloud 终态 | 输出视频的帧率。 |
| `resolution` | string | 否 | Cloud 终态 | 输出视频的分辨率。 |
| `tool_version` | string | 否 | Cloud 终态 | 任务实际使用的工具版本。 |
| `video_url` | string | 否 | Cloud 终态 | 增强后的视频文件下载地址。返回一个 HTTPS 临时下载链接，有效期为 24 小时； |

Cloud 调用成功后读取 `task_id`，再查询终态结果：

```bash
mediakit-cli shared query-task --task-id <task_id> --poll-complete
```

### 机器合同

以下命令只读取本模式的实时 help/schema，不发起业务调用：

```bash
mediakit-cli video enhance-video --help
mediakit-cli video enhance-video --schema
```
