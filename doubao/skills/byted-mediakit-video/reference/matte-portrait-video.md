# 视频人像抠图

## 能力用途

自动识别视频中的人物主体，移除原始背景，并生成背景透明或纯色背景的视频文件，适用于背景替换等后期处理场景。

## 参数填写规则

- 可选参数仅在用户明确指定，或可从用户意图准确确定时填写；不得伪造。不能准确确定时省略，确为正确完成任务所必需时先向用户澄清。

- 用户未点名格式时省略 output_format/format；用源容器或扩展名去填属于编造。用户点名了文档中的格式时即使等于默认值也要显式传递。调用成功或已被拦截后，不得再用编造的格式重试同一工具。
## 语义效果选项

### `background_color` 可选效果

| 语义名称 | 参数值 | 说明 |
| --- | --- | --- |
| 白色 | `white` | MP4 输出使用白色背景。 |
| 绿色 | `green` | MP4 输出使用绿色背景。 |
| 黑色 | `black` | MP4 输出使用黑色背景。 |

## Cloud

### 命令与生命周期

- 命令：`mediakit-cli video matte-portrait-video`
- 生命周期：异步
- 返回方式：返回 `task_id`，再查询终态结果。

### 参数

| 参数路径 | CLI flag | 类型 | 必填 | 默认值 | 枚举/范围/结构 | 说明 |
| --- | --- | --- | --- | --- | --- | --- |
| `background_color` | `--background-color` | string | 否 | - | 枚举: ["black","white","green"] | 输出视频的背景颜色；black 表示黑色，white 表示白色，green 表示绿色，默认为绿色；仅当 format 为 MP4 时生效。 |
| `client_token` | `--client-token` | string | 否 | - | - | 用户请求凭证，用于幂等控制；大小写敏感，长度不超过 64 个 ASCII 可打印字符。 用于控制异步任务幂等；同步任务不支持幂等校验。异步任务首次提交时默认不传，服务端仍会对相同核心参数执行 24 小时默认幂等。用户明确指定 token 时原样使用。因网络超时、响应丢失等原因重试同一次提交时，原请求有 token 则复用原值，原请求未传则继续不传。任务已有结果后，用户要求“结果不对，重试”“重新跑一次”或“重新发起任务”时，必须生成并传递新的 token，避免返回原任务。新对话中用户要求“重新发起任务”时，若当前上下文具备完整任务参数，直接生成新 token 并提交；若参数不足，先向用户澄清，补齐后再使用新 token 发起，不得直接省略 token。新任务后续发生提交重试时复用该新 token。已有 task_id 且任务尚未完成时，只查询原任务，不得重新提交。CLI runtime 不判断用户意图，也不自动生成 token。 |
| `format` | `--format` | string | 否 | "WEBM" | 枚举: ["MOV","WEBM","MP4"] | 输出视频的格式，默认为 WEBM。MP4 输出 MP4 格式和纯色背景，并可选用 background_color 指定背景颜色。MOV 输出 QuickTime Movie 格式和透明背景，支持 Alpha 透明通道。WEBM 输出 WebM 格式和透明背景，支持 Alpha 透明通道。 |
| `video_url` | `--video-url` | string | 是 | - | - | 指定待抠图的视频 URL，支持 mp4、flv、ts、avi、mov、mkv、wmv 等主流视频格式；支持本地文件路径和公网 HTTP/HTTPS URL 两种输入协议。 |

### 调用示例

```bash
mediakit-cli video matte-portrait-video \
  --video-url <video_url>
```

仅使用用户真实输入替换占位符；可选 flag 遵守参数填写规则，不得编造 URL、文件、枚举或业务参数。

### 返回结果

| 字段路径 | 类型 | 必含 | 模式 | 说明 |
| --- | --- | --- | --- | --- |
| `request_id` | string | 否 | Cloud | 请求标识；仅在后端返回时出现。 |
| `task_id` | string | 是 | Cloud | 异步任务的唯一标识，用于查询任务状态并获取最终结果。 |
| `task_type` | string | 否 | Cloud | 任务类型；仅在后端实际返回非空值时出现。 |
| `duration` | number | 否 | Cloud 终态 | 输出视频的时长，单位为秒。 |
| `resolution` | string | 否 | Cloud 终态 | 输出视频的分辨率，与原片对齐。 |
| `video_url` | string | 否 | Cloud 终态 | 生成的抠像后视频文件地址；返回有效期为 24 小时的 HTTPS 临时下载链接； |

Cloud 调用成功后读取 `task_id`，再查询终态结果：

```bash
mediakit-cli shared query-task --task-id <task_id> --poll-complete
```

### 机器合同

以下命令只读取本模式的实时 help/schema，不发起业务调用：

```bash
mediakit-cli video matte-portrait-video --help
mediakit-cli video matte-portrait-video --schema
```
