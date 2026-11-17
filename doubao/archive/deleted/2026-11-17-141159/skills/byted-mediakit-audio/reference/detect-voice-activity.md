# 语音端点识别

## 能力用途

识别音频或视频中的有效人声片段，定位每段人声的起止时间并返回时间戳列表，可用于为后续语音识别、分析、剪辑或训练筛选更干净的音频输入。
## 参数填写规则

- 可选参数仅在用户明确指定，或可从用户意图准确确定时填写；不得伪造。不能准确确定时省略，确为正确完成任务所必需时先向用户澄清。
## Cloud

### 命令与生命周期

- 命令：`mediakit-cli audio detect-voice-activity`
- 生命周期：异步
- 返回方式：返回 `task_id`，再查询终态结果。

### 参数

| 参数路径 | CLI flag | 类型 | 必填 | 默认值 | 枚举/范围/结构 | 说明 |
| --- | --- | --- | --- | --- | --- | --- |
| `audio_url` | `--audio-url` | string | 条件必填（video_url 或 audio_url） | - | - | audio_url 为待处理的音频 URL，是条件必填项；支持公网可访问的 http/https 直链或 mediakit/tos/vod 平台资源链接；audio_url 与 video_url 二选一，必须且只能提供其中一个。支持 mp3、m4a、wav、wma、amr、aac、ogg、flac 等主流音频格式。 |
| `client_token` | `--client-token` | string | 否 | - | - | 用户请求凭证，用于幂等控制；大小写敏感，长度不超过 64 个 ASCII 可打印字符。 用于控制异步任务幂等；同步任务不支持幂等校验。异步任务首次提交时默认不传，服务端仍会对相同核心参数执行 24 小时默认幂等。用户明确指定 token 时原样使用。因网络超时、响应丢失等原因重试同一次提交时，原请求有 token 则复用原值，原请求未传则继续不传。任务已有结果后，用户要求“结果不对，重试”“重新跑一次”或“重新发起任务”时，必须生成并传递新的 token，避免返回原任务。新对话中用户要求“重新发起任务”时，若当前上下文具备完整任务参数，直接生成新 token 并提交；若参数不足，先向用户澄清，补齐后再使用新 token 发起，不得直接省略 token。新任务后续发生提交重试时复用该新 token。已有 task_id 且任务尚未完成时，只查询原任务，不得重新提交。CLI runtime 不判断用户意图，也不自动生成 token。 |
| `video_url` | `--video-url` | string | 条件必填（video_url 或 audio_url） | - | - | video_url 为待处理的视频 URL，是条件必填项；支持公网可访问的 http/https 直链或 mediakit/tos/vod 平台资源链接；video_url 与 audio_url 二选一，必须且只能提供其中一个。支持 mp4、flv、ts、avi、mov、wmv、mkv 等主流视频格式。 |

### 参数关系

- 顶层参数必须满足：条件必填（video_url 或 audio_url）。

### 调用示例

```bash
mediakit-cli audio detect-voice-activity \
  --video-url <video_url>
```

仅使用用户真实输入替换占位符；可选 flag 遵守参数填写规则，不得编造 URL、文件、枚举或业务参数。

### 返回结果

| 字段路径 | 类型 | 必含 | 模式 | 说明 |
| --- | --- | --- | --- | --- |
| `request_id` | string | 否 | Cloud | 请求标识；仅在后端返回时出现。 |
| `task_id` | string | 是 | Cloud | 异步任务的唯一标识，用于查询任务状态并获取最终结果。 |
| `task_type` | string | 否 | Cloud | 任务类型；仅在后端实际返回非空值时出现。 |
| `duration` | number | 否 | Cloud 终态 | 输入媒体文件的总时长，单位为秒。 |
| `segment_count` | integer | 否 | Cloud 终态 | 检测到的人声片段数量；未检测到人声片段时为 0。 |
| `voice_segments` | array<object> | 否 | Cloud 终态 | 有效人声片段列表；未检测到有效人声时返回空数组。 |
| `voice_segments[].end_time` | number | 否 | Cloud 终态 | 片段结束时间，单位为秒，精确到小数点后两位。 |
| `voice_segments[].start_time` | number | 否 | Cloud 终态 | 片段开始时间，单位为秒，精确到小数点后两位。 |

Cloud 调用成功后读取 `task_id`，再查询终态结果：

```bash
mediakit-cli shared query-task --task-id <task_id> --poll-complete
```

### 机器合同

以下命令只读取本模式的实时 help/schema，不发起业务调用：

```bash
mediakit-cli audio detect-voice-activity --help
mediakit-cli audio detect-voice-activity --schema
```
