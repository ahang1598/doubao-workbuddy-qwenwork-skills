# 音频调速

## 能力用途

用于音频调速，可调整音频播放倍速，实现快放或慢放效果。

## 参数填写规则

- 可选参数仅在用户明确指定，或可从用户意图准确确定时填写；不得伪造。不能准确确定时省略，确为正确完成任务所必需时先向用户澄清。

- 用户未点名格式时省略 output_format/format；用源容器或扩展名去填属于编造。用户点名了文档中的格式时即使等于默认值也要显式传递。调用成功或已被拦截后，不得再用编造的格式重试同一工具。
## Cloud

### 命令与生命周期

- 命令：`mediakit-cli editing adjust-audio-speed`
- 生命周期：异步
- 返回方式：返回 `task_id`，再查询终态结果。

### 参数

| 参数路径 | CLI flag | 类型 | 必填 | 默认值 | 枚举/范围/结构 | 说明 |
| --- | --- | --- | --- | --- | --- | --- |
| `audio_url` | `--audio-url` | string | 是 | - | - | 待调速的音频 URL。支持本地文件路径和公网 HTTP/HTTPS URL 两种输入协议；支持 mp3、m4a、wav 等主流音频格式；建议单个输入文件大小不超过 10 GB。 |
| `client_token` | `--client-token` | string | 否 | - | - | 用户请求凭证，用于幂等控制；大小写敏感，长度不超过 64 个 ASCII 可打印字符。 用于控制异步任务幂等；同步任务不支持幂等校验。异步任务首次提交时默认不传，服务端仍会对相同核心参数执行 24 小时默认幂等。用户明确指定 token 时原样使用。因网络超时、响应丢失等原因重试同一次提交时，原请求有 token 则复用原值，原请求未传则继续不传。任务已有结果后，用户要求“结果不对，重试”“重新跑一次”或“重新发起任务”时，必须生成并传递新的 token，避免返回原任务。新对话中用户要求“重新发起任务”时，若当前上下文具备完整任务参数，直接生成新 token 并提交；若参数不足，先向用户澄清，补齐后再使用新 token 发起，不得直接省略 token。新任务后续发生提交重试时复用该新 token。已有 task_id 且任务尚未完成时，只查询原任务，不得重新提交。CLI runtime 不判断用户意图，也不自动生成 token。 |
| `format` | `--format` | string | 否 | "m4a" | 枚举: ["mp3","m4a","ogg","flac","wav"] | 输出音频格式。支持 mp3、m4a、ogg、flac、wav；默认值为 m4a。 |
| `speed` | `--speed` | number | 否 | 1 | 最小值: 0.1；最大值: 4 | 音频播放倍速为 0.1 至最高 4.0；1.0 表示原速，小于 1.0 表示慢放，大于 1.0 表示快放。 |

### 调用示例

```bash
mediakit-cli editing adjust-audio-speed \
  --audio-url <audio_url>
```

仅使用用户真实输入替换占位符；可选 flag 遵守参数填写规则，不得编造 URL、文件、枚举或业务参数。

### 返回结果

| 字段路径 | 类型 | 必含 | 模式 | 说明 |
| --- | --- | --- | --- | --- |
| `request_id` | string | 否 | Cloud | 请求标识；仅在后端返回时出现。 |
| `task_id` | string | 是 | Cloud | 异步任务的唯一标识，用于查询任务状态并获取最终结果。 |
| `task_type` | string | 否 | Cloud | 任务类型；仅在后端实际返回非空值时出现。 |
| `audio_url` | string | 否 | Cloud 终态 | 调速后生成的音频文件下载地址。返回 HTTPS 临时下载链接，有效期为 24 小时，请及时下载保存； |
| `duration` | number | 否 | Cloud 终态 | 输出音频的时长，单位为秒。 |

Cloud 调用成功后读取 `task_id`，再查询终态结果：

```bash
mediakit-cli shared query-task --task-id <task_id> --poll-complete
```

### 机器合同

以下命令只读取本模式的实时 help/schema，不发起业务调用：

```bash
mediakit-cli editing adjust-audio-speed --help
mediakit-cli editing adjust-audio-speed --schema
```
