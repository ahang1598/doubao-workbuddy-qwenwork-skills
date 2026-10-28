# 视频元信息获取

## 能力用途

探测输入的视频 URL，输出标准化的媒资元信息。

## 参数填写规则

- 可选参数仅在用户明确指定，或可从用户意图准确确定时填写；不得伪造。不能准确确定时省略，确为正确完成任务所必需时先向用户澄清。
## Cloud

### 命令与生命周期

- 命令：`mediakit-cli video probe-video-metadata`
- 生命周期：异步
- 返回方式：返回 `task_id`，再查询终态结果。

### 参数

| 参数路径 | CLI flag | 类型 | 必填 | 默认值 | 枚举/范围/结构 | 说明 |
| --- | --- | --- | --- | --- | --- | --- |
| `video_url` | `--video-url` | string | 是 | - | - | 待探测的视频 URL。支持 mp4、flv、ts、avi、mov、wmv、mkv 等主流视频格式。支持本地文件路径和公网 HTTP/HTTPS URL 两种输入协议。 |

| `client_token` | `--client-token` | string | 否 | - | - | 用户请求凭证，用于幂等控制；大小写敏感，长度不超过 64 个 ASCII 可打印字符。 用于控制异步任务幂等；同步任务不支持幂等校验。异步任务首次提交时默认不传，服务端仍会对相同核心参数执行 24 小时默认幂等。用户明确指定 token 时原样使用。因网络超时、响应丢失等原因重试同一次提交时，原请求有 token 则复用原值，原请求未传则继续不传。任务已有结果后，用户要求“结果不对，重试”“重新跑一次”或“重新发起任务”时，必须生成并传递新的 token，避免返回原任务。新对话中用户要求“重新发起任务”时，若当前上下文具备完整任务参数，直接生成新 token 并提交；若参数不足，先向用户澄清，补齐后再使用新 token 发起，不得直接省略 token。新任务后续发生提交重试时复用该新 token。已有 task_id 且任务尚未完成时，只查询原任务，不得重新提交。CLI runtime 不判断用户意图，也不自动生成 token。 |
### 调用示例

```bash
mediakit-cli video probe-video-metadata \
  --video-url <video_url>
```

仅使用用户真实输入替换占位符；可选 flag 遵守参数填写规则，不得编造 URL、文件、枚举或业务参数。

### 返回结果

| 字段路径 | 类型 | 必含 | 模式 | 说明 |
| --- | --- | --- | --- | --- |
| `request_id` | string | 否 | Cloud | 请求标识；仅在后端返回时出现。 |
| `task_id` | string | 是 | Cloud | 异步任务的唯一标识，用于查询任务状态并获取最终结果。 |
| `task_type` | string | 否 | Cloud | 任务类型；仅在后端实际返回非空值时出现。 |
| `audio_stream_meta` | object / null | 是 | Cloud 终态 | 主音频流元信息。视频不含音频流时返回 null。 |
| `audio_stream_meta.bitrate` | number / null | 否 | Cloud 终态 | 音频流码率，单位为 bps。 |
| `audio_stream_meta.channels` | number / null | 否 | Cloud 终态 | 音频声道数。 |
| `audio_stream_meta.codec` | string / null | 否 | Cloud 终态 | 音频编码格式，例如 aac。 |
| `audio_stream_meta.duration` | number / null | 否 | Cloud 终态 | 音频流时长，单位为秒。 |
| `audio_stream_meta.sample_rate` | number / null | 否 | Cloud 终态 | 音频采样率，单位为 Hz。 |
| `format_meta` | object / null | 是 | Cloud 终态 | 容器层元信息，包含封装格式、码率、时长、大小等。 |
| `format_meta.bitrate` | number / null | 否 | Cloud 终态 | 容器码率，单位为 bps。 |
| `format_meta.container` | string / null | 否 | Cloud 终态 | 容器格式（封装格式），例如 MP4。 |
| `format_meta.duration` | number / null | 否 | Cloud 终态 | 容器声明的时长，单位为秒。 |
| `format_meta.md5` | string / null | 否 | Cloud 终态 | 文件 MD5 值（如可获取）。 |
| `format_meta.size` | number / null | 否 | Cloud 终态 | 文件大小，单位为 byte。 |
| `video_stream_meta` | object / null | 是 | Cloud 终态 | 主视频流元信息。视频不含视频流时返回 null。 |
| `video_stream_meta.bitrate` | number / null | 否 | Cloud 终态 | 视频流码率，单位为 bps。 |
| `video_stream_meta.codec` | string / null | 否 | Cloud 终态 | 视频编码格式，例如 h264。 |
| `video_stream_meta.duration` | number / null | 否 | Cloud 终态 | 视频流原始时长，单位为秒。 |
| `video_stream_meta.dynamic_range` | string / null | 否 | Cloud 终态 | 动态范围，可为 HDR 或 SDR。 |
| `video_stream_meta.fps` | number / null | 否 | Cloud 终态 | 视频帧率，单位为 fps。 |
| `video_stream_meta.height` | number / null | 否 | Cloud 终态 | 视频流显示高度，单位为像素（px）。 |
| `video_stream_meta.width` | number / null | 否 | Cloud 终态 | 视频流显示宽度，单位为像素（px）。 |

Cloud 调用成功后读取 `task_id`，再查询终态结果：

```bash
mediakit-cli shared query-task --task-id <task_id> --poll-complete
```

### 机器合同

以下命令只读取本模式的实时 help/schema，不发起业务调用：

```bash
mediakit-cli video probe-video-metadata --help
mediakit-cli video probe-video-metadata --schema
```
