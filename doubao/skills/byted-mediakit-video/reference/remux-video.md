# 视频转封装

## 能力用途

视频转封装用于调整视频容器格式，仅修改容器格式，不会重新编解码音视频码流，适用于点播分发适配、流媒体切片打包与多端兼容等场景。

## 参数填写规则

- 可选参数仅在用户明确指定，或可从用户意图准确确定时填写；不得伪造。不能准确确定时省略，确为正确完成任务所必需时先向用户澄清。
## Cloud

### 命令与生命周期

- 命令：`mediakit-cli video remux-video`
- 生命周期：异步
- 返回方式：返回 `task_id`，再查询终态结果。

### 使用指南

- 数组参数（`--metadata-keep-tags`）传多个值时用逗号分隔并整体加引号，例如 `--metadata-keep-tags "url1,url2"`。
- 单个值中的文件名或 URL 不能包含逗号（`,`），否则会被 CLI 当成多个元素拆开。遇到这种情况时，先向用户澄清，请其提供不含逗号的文件名或对应 URL 后再调用。
- 对象或对象数组参数（`--metadata-add-tags`）需传合法 JSON 字符串；字段名与层级必须与上表“枚举/范围/结构”及子字段说明一致。不要用逗号分隔或裸文本。
- POSIX / bash：用单引号整体包裹，例如 `--metadata-add-tags '[{...}]'`。
- Windows PowerShell：按共享入口 [JSON 参数传参](../../byted-mediakit-shared/SKILL.md) 把 JSON flag 放在 `--%` 之后，内部双引号写成 `\"`，例如 `--% --metadata-add-tags "[{\"key\":\"value\"}]"`。Windows 内联 JSON 禁止单引号 JSON 和 `$json` 变量；`@文件`、stdin `-`、`file://` 写法按共享入口 [JSON 参数传参](../../byted-mediakit-shared/SKILL.md) 执行。

### 调用示例

```bash
mediakit-cli video remux-video \
  --video-url <video_url> \
  --container-format <container_format>
```

仅使用用户真实输入替换占位符；可选 flag 遵守参数填写规则，不得编造 URL、文件、枚举或业务参数。

### 参数

| 参数路径 | CLI flag | 类型 | 必填 | 默认值 | 枚举/范围/结构 | 说明 |
| --- | --- | --- | --- | --- | --- | --- |
| `client_token` | `--client-token` | string | 否 | - | - | 用户请求凭证，用于幂等控制；大小写敏感，长度不超过 64 个 ASCII 可打印字符。 用于控制异步任务幂等；同步任务不支持幂等校验。异步任务首次提交时默认不传，服务端仍会对相同核心参数执行 24 小时默认幂等。用户明确指定 token 时原样使用。因网络超时、响应丢失等原因重试同一次提交时，原请求有 token 则复用原值，原请求未传则继续不传。任务已有结果后，用户要求“结果不对，重试”“重新跑一次”或“重新发起任务”时，必须生成并传递新的 token，避免返回原任务。新对话中用户要求“重新发起任务”时，若当前上下文具备完整任务参数，直接生成新 token 并提交；若参数不足，先向用户澄清，补齐后再使用新 token 发起，不得直接省略 token。新任务后续发生提交重试时复用该新 token。已有 task_id 且任务尚未完成时，只查询原任务，不得重新提交。CLI runtime 不判断用户意图，也不自动生成 token。 |
| `container_format` | `--container-format` | string | 是 | "MP4"（Schema 默认；仍需显式提供） | 枚举: ["MP4","FLV","MPEGTS"] | 目标封装格式，支持 MP4、FLV、MPEGTS，默认值为 MP4。 |
| `metadata_add_tags` | `--metadata-add-tags` | array<object> | 否 | - | - | 可选填写需要为输出视频新增的元信息标签列表，每个标签由 key 和 value 组成；对 MPEGTS 封装格式无效；新增标签与被保留标签同名时，会覆盖源文件的值。 |
| `metadata_add_tags[].key` | - | string | 否 | - | - | 标签键；每个标签由 key 和 value 组成。 |
| `metadata_add_tags[].value` | - | string | 否 | - | - | 标签值；每个标签由 key 和 value 组成。 |
| `metadata_keep_tags` | `--metadata-keep-tags` | array<string> | 否 | - | - | 可选填写需要从源视频保留的元信息标签列表，用于指定需要保留的标签键（Key）；默认情况下转码过程会丢弃大部分元信息（如标题、艺术家等）；对 MPEGTS 封装格式无效。 |
| `video_url` | `--video-url` | string | 是 | - | - | 待处理视频的 URL，支持本地文件路径和公网 HTTP/HTTPS URL 两种输入协议。 |

### 返回结果

| 字段路径 | 类型 | 必含 | 模式 | 说明 |
| --- | --- | --- | --- | --- |
| `request_id` | string | 否 | Cloud | 请求标识；仅在后端返回时出现。 |
| `task_id` | string | 是 | Cloud | 异步任务的唯一标识，用于查询任务状态并获取最终结果。 |
| `task_type` | string | 否 | Cloud | 任务类型；仅在后端实际返回非空值时出现。 |
| `duration` | number | 否 | Cloud 终态 | 视频时长，单位为秒。 |
| `video_url` | string | 否 | Cloud 终态 | 输出视频地址。返回 HTTPS 临时下载链接，有效期为 24 小时； |

Cloud 调用成功后读取 `task_id`，再查询终态结果：

```bash
mediakit-cli shared query-task --task-id <task_id> --poll-complete
```

### 机器合同

以下命令只读取本模式的实时 help/schema，不发起业务调用：

```bash
mediakit-cli video remux-video --help
mediakit-cli video remux-video --schema
```
