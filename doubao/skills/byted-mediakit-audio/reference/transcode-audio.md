# 音频转码

## 能力用途

将音频转换为另一种封装与编码配置，并可调整采样率、码率、声道和响度，以及保留、新增或覆盖元信息，用于适配播放终端、网络传输和媒资库响度标准化。
## 参数填写规则

- 可选参数仅在用户明确指定，或可从用户意图准确确定时填写；不得伪造。不能准确确定时省略，确为正确完成任务所必需时先向用户澄清。
## Cloud

### 命令与生命周期

- 命令：`mediakit-cli audio transcode-audio`
- 生命周期：异步
- 返回方式：返回 `task_id`，再查询终态结果。

### 使用指南


- `{}` 和 `[{}]` 仅展示 JSON 容器形状。命令模板中的 `<参数名_json>` 必须替换为符合参数表、已补齐必填字段的合法 JSON；不得直接提交空容器或占位符。
- 数组参数（`--metadata-keep-tags`）传多个值时用逗号分隔并整体加引号，例如 `--metadata-keep-tags "url1,url2"`。
- 单个值中的文件名或 URL 不能包含逗号（`,`），否则会被 CLI 当成多个元素拆开。遇到这种情况时，先向用户澄清，请其提供不含逗号的文件名或对应 URL 后再调用。
- 对象或对象数组参数（`--audio`、`--metadata-add-tags`）需传合法 JSON 字符串；字段名与层级必须与上表“枚举/范围/结构”及子字段说明一致。不要用逗号分隔或裸文本。
- POSIX / bash：用单引号整体包裹，例如 `--audio '{}'`。
- Windows PowerShell：按共享入口 [JSON 参数传参](../../byted-mediakit-shared/SKILL.md) 把 JSON flag 放在 `--%` 之后，内部双引号写成 `\"`，例如 `--% --audio "{}"`。Windows 内联 JSON 禁止单引号 JSON 和 `$json` 变量；`@文件`、stdin `-`、`file://` 写法按共享入口 [JSON 参数传参](../../byted-mediakit-shared/SKILL.md) 执行。

### 调用示例

```bash
mediakit-cli audio transcode-audio \
  --container-format <container_format> \
  --audio '<audio_json>'
```

仅使用用户真实输入替换占位符；可选 flag 遵守参数填写规则，不得编造 URL、文件、枚举或业务参数。

### 参数

| 参数路径 | CLI flag | 类型 | 必填 | 默认值 | 枚举/范围/结构 | 说明 |
| --- | --- | --- | --- | --- | --- | --- |
| `audio` | `--audio` | object | 是 | - | - | audio 提供音频参数配置。 |
| `audio.bitrate_kbps` | - | integer | 是 | 128（Schema 默认；仍需显式提供） | 最小值: 10；最大值: 500 | bitrate_kbps 指定音频码率，单位为 Kbps，范围 10 至 500，默认值为 128。 |
| `audio.bitrate_mode` | - | string | 是 | "cbr"（Schema 默认；仍需显式提供） | 枚举: ["cbr","cae"] | bitrate_mode 指定音频码率控制模式，支持 cbr 和 cae，默认 cbr。cbr 是恒定码率模式，编码器会尝试让音频流每秒严格保持 bitrate_kbps 设定的码率，使文件大小可以被精确预测，适合带宽稳定性要求高的流式传输。cae 仅在 container_format 为 M4A 时支持，会根据音频内容复杂度动态调整瞬时码率，并确保整个文件平均码率接近 bitrate_kbps 目标值。 |
| `audio.channels` | - | integer | 否 | - | 枚举: [1,2] | channels 指定音频声道数，支持 1 和 2；1 表示单声道，2 表示双声道。不传时不在客户端补默认值，由后端按源音频与任务配置处理。 |
| `audio.sample_rate` | - | integer | 是 | 48000（Schema 默认；仍需显式提供） | 枚举: [8000,11025,12000,16000,22050,24000,32000,44100,48000,64000,88200,96000] | sample_rate 指定音频采样率，单位为 Hz，默认 48000。建议根据目标编码器填写：MP3 支持 8000、11025、12000、16000、22050、24000、32000、44100、48000；AAC 支持 8000、11025、12000、16000、22050、24000、32000、44100、48000、64000、88200、96000；Opus 支持 48000。 |
| `audio.volume_integrated_loudness` | - | number | 否 | -12 | 最小值: -70；最大值: -5 | volume_integrated_loudness 用于设定音频整体感知音量的目标综合响度，单位为 LUFS，范围 -70 至 -5，默认值为 -12。 |
| `audio.volume_loudness_range` | - | number | 否 | 7 | 最小值: 1；最大值: 20 | volume_loudness_range 调节音频最响亮和最安静部分之间的差异，单位为 LU，范围 1 至 20，默认值为 7；volume_method 为 2Pass 时生效。 |
| `audio.volume_method` | - | string | 否 | - | 枚举: ["2Pass"] | volume_method 是音量均衡算法开关；不设置时不处理音量。支持将 volume_method 设置为 2Pass 启用两阶段响度分析与处理，此时 volume_integrated_loudness、volume_true_peak 和 volume_loudness_range 生效。 |
| `audio.volume_true_peak` | - | number | 否 | 0 | 最小值: -9；最大值: 0 | volume_true_peak 设置音频信号的真实峰值最高上限，以防止削波失真，单位为 dBTP，范围 -9 至 0，默认值为 0。 |
| `audio_url` | `--audio-url` | string | 是 | - | - | audio_url 是待转码音频的 URL，支持本地文件路径和公网 HTTP/HTTPS URL 两种输入协议；输入支持 mp3、m4a、wav、wma、amr、aac、ogg、flac 等音频格式。 |
| `client_token` | `--client-token` | string | 否 | - | - | 用户请求凭证，用于幂等控制；大小写敏感，长度不超过 64 个 ASCII 可打印字符。 用于控制异步任务幂等；同步任务不支持幂等校验。异步任务首次提交时默认不传，服务端仍会对相同核心参数执行 24 小时默认幂等。用户明确指定 token 时原样使用。因网络超时、响应丢失等原因重试同一次提交时，原请求有 token 则复用原值，原请求未传则继续不传。任务已有结果后，用户要求“结果不对，重试”“重新跑一次”或“重新发起任务”时，必须生成并传递新的 token，避免返回原任务。新对话中用户要求“重新发起任务”时，若当前上下文具备完整任务参数，直接生成新 token 并提交；若参数不足，先向用户澄清，补齐后再使用新 token 发起，不得直接省略 token。新任务后续发生提交重试时复用该新 token。已有 task_id 且任务尚未完成时，只查询原任务，不得重新提交。CLI runtime 不判断用户意图，也不自动生成 token。 |
| `container_format` | `--container-format` | string | 是 | "MP3"（Schema 默认；仍需显式提供） | 枚举: ["MP3","M4A","OGG"] | container_format 指定目标封装格式，建议填写，默认 MP3；系统根据封装格式自动选择对应编码器：MP3 封装格式使用 MP3 编码器，M4A 封装格式使用 AAC 编码器，OGG 封装格式使用 Opus 编码器。 |
| `metadata_add_tags` | `--metadata-add-tags` | array<object> | 否 | - | - | metadata_add_tags 指定为输出音频新增的元信息标签；新增标签与保留标签同名时，新增标签设置覆盖源文件的值。 |
| `metadata_add_tags[].key` | - | string | 否 | - | - | metadata_add_tags 中每个标签由 key 组成。 |
| `metadata_add_tags[].value` | - | string | 否 | - | - | metadata_add_tags 中每个标签由 value 组成。 |
| `metadata_keep_tags` | `--metadata-keep-tags` | array<string> | 否 | - | - | metadata_keep_tags 指定从源音频保留的元信息标签键；默认情况下，转码会丢弃大部分元信息，例如标题和艺术家。 |

### 参数关系

- `$.container_format` 在 audio.bitrate_mode=cae 时必须满足：枚举: ["M4A"]。

### 返回结果

| 字段路径 | 类型 | 必含 | 模式 | 说明 |
| --- | --- | --- | --- | --- |
| `request_id` | string | 否 | Cloud | 请求标识；仅在后端返回时出现。 |
| `task_id` | string | 是 | Cloud | 异步任务的唯一标识，用于查询任务状态并获取最终结果。 |
| `task_type` | string | 否 | Cloud | 任务类型；仅在后端实际返回非空值时出现。 |
| `audio_url` | string | 否 | Cloud 终态 | audio_url 是输出音频的地址。返回 HTTPS 临时下载链接，有效期为 24 小时； |
| `duration` | number | 否 | Cloud 终态 | duration 表示音频时长，单位为秒。 |

Cloud 调用成功后读取 `task_id`，再查询终态结果：

```bash
mediakit-cli shared query-task --task-id <task_id> --poll-complete
```

### 机器合同

以下命令只读取本模式的实时 help/schema，不发起业务调用：

```bash
mediakit-cli audio transcode-audio --help
mediakit-cli audio transcode-audio --schema
```
