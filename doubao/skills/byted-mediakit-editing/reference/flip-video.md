# 视频画面翻转

## 能力用途

用于视频画面翻转，对指定视频进行上下或左右镜像翻转。

## 参数填写规则

- 可选参数仅在用户明确指定，或可从用户意图准确确定时填写；不得伪造。不能准确确定时省略，确为正确完成任务所必需时先向用户澄清。
## Cloud

### 命令与生命周期

- 命令：`mediakit-cli editing flip-video`
- 生命周期：异步
- 返回方式：返回 `task_id`，再查询终态结果。

### 使用指南

- 布尔参数（`--is-flip-horizontal`、`--is-flip-vertical`）只能写成 `--is-flip-horizontal=true` 或 `--is-flip-horizontal=false`，也可用裸 `--is-flip-horizontal`（等价 true）；禁止空格传值 `--is-flip-horizontal true`，否则该值会被当作位置参数。
- 布尔参数取默认值时直接省略，不要显式重复默认值。

### 调用示例

```bash
mediakit-cli editing flip-video \
  --video-url <video_url>
```

仅使用用户真实输入替换占位符；可选 flag 遵守参数填写规则，不得编造 URL、文件、枚举或业务参数。

### 参数

| 参数路径 | CLI flag | 类型 | 必填 | 默认值 | 枚举/范围/结构 | 说明 |
| --- | --- | --- | --- | --- | --- | --- |
| `client_token` | `--client-token` | string | 否 | - | - | 用户请求凭证，用于幂等控制；大小写敏感，长度不超过 64 个 ASCII 可打印字符。 用于控制异步任务幂等；同步任务不支持幂等校验。异步任务首次提交时默认不传，服务端仍会对相同核心参数执行 24 小时默认幂等。用户明确指定 token 时原样使用。因网络超时、响应丢失等原因重试同一次提交时，原请求有 token 则复用原值，原请求未传则继续不传。任务已有结果后，用户要求“结果不对，重试”“重新跑一次”或“重新发起任务”时，必须生成并传递新的 token，避免返回原任务。新对话中用户要求“重新发起任务”时，若当前上下文具备完整任务参数，直接生成新 token 并提交；若参数不足，先向用户澄清，补齐后再使用新 token 发起，不得直接省略 token。新任务后续发生提交重试时复用该新 token。已有 task_id 且任务尚未完成时，只查询原任务，不得重新提交。CLI runtime 不判断用户意图，也不自动生成 token。 |
| `is_flip_horizontal` | `--is-flip-horizontal` | boolean | 否 | false | - | 可省略，用于控制是否进行水平（左右）翻转，默认值为 false。 |
| `is_flip_vertical` | `--is-flip-vertical` | boolean | 否 | false | - | 可省略，用于控制是否进行垂直（上下）翻转，默认值为 false。is_flip_vertical 和 is_flip_horizontal 两个参数至少需要将其中一个设置为 true，否则处理后的视频与原视频没有区别；如果两个参数都设置为 true，效果等同于将画面旋转 180 度。 |
| `video_url` | `--video-url` | string | 是 | - | - | 待翻转的视频 URL，支持本地文件路径和公网 HTTP/HTTPS URL 两种输入协议；支持 mp4、flv、ts、avi、mov、wmv、mkv 等主流视频格式；最高支持 4K (3840×2160) 分辨率；建议输入文件大小不超过 10 GB。 |

### 参数关系

- 顶层参数必须至少满足一项：is_flip_vertical=True 或 is_flip_horizontal=True。

### 返回结果

| 字段路径 | 类型 | 必含 | 模式 | 说明 |
| --- | --- | --- | --- | --- |
| `request_id` | string | 否 | Cloud | 请求标识；仅在后端返回时出现。 |
| `task_id` | string | 是 | Cloud | 异步任务的唯一标识，用于查询任务状态并获取最终结果。 |
| `task_type` | string | 否 | Cloud | 任务类型；仅在后端实际返回非空值时出现。 |
| `duration` | number | 否 | Cloud 终态 | 输出视频的总时长，单位为秒。 |
| `resolution` | string | 否 | Cloud 终态 | 输出视频的分辨率，可能为 240p、360p、480p、540p、720p、1080p、2k 或 4k。 |
| `video_url` | string | 否 | Cloud 终态 | 生成的翻转后视频文件地址，文件格式为 MP4。返回一个 HTTPS 临时下载链接，有效期为 24 小时； |

Cloud 调用成功后读取 `task_id`，再查询终态结果：

```bash
mediakit-cli shared query-task --task-id <task_id> --poll-complete
```

### 机器合同

以下命令只读取本模式的实时 help/schema，不发起业务调用：

```bash
mediakit-cli editing flip-video --help
mediakit-cli editing flip-video --schema
```
