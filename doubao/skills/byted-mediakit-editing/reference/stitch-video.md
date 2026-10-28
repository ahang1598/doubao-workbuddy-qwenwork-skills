# 视频画面拼接

## 能力用途

将 2 至 3 个视频在同一画布中按左右或上下方向进行空间拼接，适用于多视角对比和画面组合；输出时长以最长输入为准，较短视频结束后以黑屏补齐，并混合所有选择保留的音轨。
## 参数填写规则

- 可选参数仅在用户明确指定，或可从用户意图准确确定时填写；不得伪造。不能准确确定时省略，确为正确完成任务所必需时先向用户澄清。
## 语义效果选项

### `stitch_direction` 可选效果

| 语义名称 | 参数值 | 说明 |
| --- | --- | --- |
| 上下拼接 | `vertical` | 上下拼接。 |
| 左右拼接 | `horizontal` | 左右拼接。 |

## Cloud

### 命令与生命周期

- 命令：`mediakit-cli editing stitch-video`
- 生命周期：异步
- 返回方式：返回 `task_id`，再查询终态结果。

### 使用指南


- `{}` 和 `[{}]` 仅展示 JSON 容器形状。命令模板中的 `<参数名_json>` 必须替换为符合参数表、已补齐必填字段的合法 JSON；不得直接提交空容器或占位符。
- 对象或对象数组参数（`--videos`）需传合法 JSON 字符串；字段名与层级必须与上表“枚举/范围/结构”及子字段说明一致。不要用逗号分隔或裸文本。
- POSIX / bash：用单引号整体包裹，例如 `--videos '[{...}]'`。
- Windows PowerShell：按共享入口 [JSON 参数传参](../../byted-mediakit-shared/SKILL.md) 把 JSON flag 放在 `--%` 之后，内部双引号写成 `\"`，例如 `--% --videos "[{\"video_url\":\"<url>\"}]"`。Windows 内联 JSON 禁止单引号 JSON 和 `$json` 变量；`@文件`、stdin `-`、`file://` 写法按共享入口 [JSON 参数传参](../../byted-mediakit-shared/SKILL.md) 执行。

### 调用示例

```bash
mediakit-cli editing stitch-video \
  --videos '<videos_json>' \
  --stitch-direction <stitch_direction>
```

仅使用用户真实输入替换占位符；可选 flag 遵守参数填写规则，不得编造 URL、文件、枚举或业务参数。

### 参数

| 参数路径 | CLI flag | 类型 | 必填 | 默认值 | 枚举/范围/结构 | 说明 |
| --- | --- | --- | --- | --- | --- | --- |
| `client_token` | `--client-token` | string | 否 | - | - | 用户请求凭证，用于幂等控制；大小写敏感，长度不超过 64 个 ASCII 可打印字符。 用于控制异步任务幂等；同步任务不支持幂等校验。异步任务首次提交时默认不传，服务端仍会对相同核心参数执行 24 小时默认幂等。用户明确指定 token 时原样使用。因网络超时、响应丢失等原因重试同一次提交时，原请求有 token 则复用原值，原请求未传则继续不传。任务已有结果后，用户要求“结果不对，重试”“重新跑一次”或“重新发起任务”时，必须生成并传递新的 token，避免返回原任务。新对话中用户要求“重新发起任务”时，若当前上下文具备完整任务参数，直接生成新 token 并提交；若参数不足，先向用户澄清，补齐后再使用新 token 发起，不得直接省略 token。新任务后续发生提交重试时复用该新 token。已有 task_id 且任务尚未完成时，只查询原任务，不得重新提交。CLI runtime 不判断用户意图，也不自动生成 token。 |
| `stitch_direction` | `--stitch-direction` | string | 是 | - | 枚举: ["horizontal","vertical"] | 拼接方式：horizontal 表示左右拼接，vertical 表示上下拼接。 |
| `videos` | `--videos` | array<object> | 是 | - | 最少项数: 2；最多项数: 3 | 待拼接的视频对象列表，最少传入 2 个，最多传入 3 个；拼接画面的顺序与列表顺序一致。 |
| `videos[].keep_audio` | - | boolean | 否 | true | - | 是否保留该视频的音频。默认值 true；为 false 时，该视频的音轨不会被合入最终产物。 |
| `videos[].video_url` | - | string | 是 | - | - | 待拼接的输入视频地址。支持本地文件路径和公网 HTTP/HTTPS URL 两种输入协议；支持 mp4、flv、ts、avi、mov、wmv、mkv 等主流视频格式。输入视频最高支持 4K (3840×2160) 分辨率。建议输入文件大小不超过 10 GB。建议输入视频的宽高比为 16:9、9:16、1:1、4:3、3:4 等常见规格，以获得更好的拼接效果。 |

### 返回结果

| 字段路径 | 类型 | 必含 | 模式 | 说明 |
| --- | --- | --- | --- | --- |
| `request_id` | string | 否 | Cloud | 请求标识；仅在后端返回时出现。 |
| `task_id` | string | 是 | Cloud | 异步任务的唯一标识，用于查询任务状态并获取最终结果。 |
| `task_type` | string | 否 | Cloud | 任务类型；仅在后端实际返回非空值时出现。 |
| `duration` | number | 否 | Cloud 终态 | 输出视频的总时长，单位为秒。 |
| `resolution` | string | 否 | Cloud 终态 | 输出视频分辨率可能为 240p、360p、480p、540p、720p、1080p、2k 或 4k。 |
| `video_url` | string | 否 | Cloud 终态 | 生成的拼接后视频文件地址，文件格式为 MP4。未设置输出存储位置时，返回 HTTPS 临时下载链接，有效期为 24 小时；设置输出存储位置后，返回存储地址，格式为 vod://<空间名>/<媒资ID> 或 tos://<桶名>/<对象Key>。 |

Cloud 调用成功后读取 `task_id`，再查询终态结果：

```bash
mediakit-cli shared query-task --task-id <task_id> --poll-complete
```

### 机器合同

以下命令只读取本模式的实时 help/schema，不发起业务调用：

```bash
mediakit-cli editing stitch-video --help
mediakit-cli editing stitch-video --schema
```
