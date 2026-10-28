# 添加视频暗水印

## 能力用途

用于视频暗水印添加。在不影响视频画面视觉质量与完整性的前提下，将一串数字信息隐藏式地嵌入视频文件中。适用于视频版权保护、内容泄露溯源、文件真实性校验等场景。

## 参数填写规则

- 可选参数仅在用户明确指定，或可从用户意图准确确定时填写；不得伪造。不能准确确定时省略，确为正确完成任务所必需时先向用户澄清。
## 语义效果选项

### `watermark_level` 可选效果

| 语义名称 | 参数值 | 说明 |
| --- | --- | --- |
| 低强度 | `low` | 低强度暗水印。 |
| 标准强度 | `normal` | 在画质与抗攻击性之间取得平衡。 |
| 高强度 | `high` | 抗攻击性更强，对画面的潜在影响也更大。 |

## Cloud

### 命令与生命周期

- 命令：`mediakit-cli video add-video-invisible-watermark`
- 生命周期：异步
- 返回方式：返回 `task_id`，再查询终态结果。

### 参数

| 参数路径 | CLI flag | 类型 | 必填 | 默认值 | 枚举/范围/结构 | 说明 |
| --- | --- | --- | --- | --- | --- | --- |
| `client_token` | `--client-token` | string | 否 | - | - | 用户请求凭证，用于幂等控制；大小写敏感，长度不超过 64 个 ASCII 可打印字符。 用于控制异步任务幂等；同步任务不支持幂等校验。异步任务首次提交时默认不传，服务端仍会对相同核心参数执行 24 小时默认幂等。用户明确指定 token 时原样使用。因网络超时、响应丢失等原因重试同一次提交时，原请求有 token 则复用原值，原请求未传则继续不传。任务已有结果后，用户要求“结果不对，重试”“重新跑一次”或“重新发起任务”时，必须生成并传递新的 token，避免返回原任务。新对话中用户要求“重新发起任务”时，若当前上下文具备完整任务参数，直接生成新 token 并提交；若参数不足，先向用户澄清，补齐后再使用新 token 发起，不得直接省略 token。新任务后续发生提交重试时复用该新 token。已有 task_id 且任务尚未完成时，只查询原任务，不得重新提交。CLI runtime 不判断用户意图，也不自动生成 token。 |
| `video_url` | `--video-url` | string | 是 | - | - | 待添加暗水印的视频 URL。支持 mp4、mov、mkv、flv、ts、avi、wmv 等主流视频格式；支持本地文件路径和公网 HTTP/HTTPS URL 两种输入协议；分辨率最高支持 4K。 |
| `watermark_content` | `--watermark-content` | string | 是 | - | 格式: "^[1-9][0-9]{0,18}$" | 待嵌入视频的隐藏数字信息，用于版权追溯。需传入一个代表 64 位正整数的字符串，且必须为纯数字字符串；数字必须在 1 至 9223372036854775807 之间；不允许使用前导零或包含任何非数字字符。 |
| `watermark_level` | `--watermark-level` | string | 否 | "normal" | 枚举: ["low","normal","high"] | 可选的暗水印强度，用于决定抗攻击性与画面影响程度的平衡。normal 为标准强度，在画质与抗攻击性之间取得平衡，适用于大多数场景；high 为高强度，抗攻击性最强，能抵抗更强的视频处理，但对画面的潜在影响也相对更大；默认值为 normal 标准强度。 |

### 调用示例

```bash
mediakit-cli video add-video-invisible-watermark \
  --video-url <video_url> \
  --watermark-content <watermark_content>
```

仅使用用户真实输入替换占位符；可选 flag 遵守参数填写规则，不得编造 URL、文件、枚举或业务参数。

### 返回结果

| 字段路径 | 类型 | 必含 | 模式 | 说明 |
| --- | --- | --- | --- | --- |
| `request_id` | string | 否 | Cloud | 请求标识；仅在后端返回时出现。 |
| `task_id` | string | 是 | Cloud | 异步任务的唯一标识，用于查询任务状态并获取最终结果。 |
| `task_type` | string | 否 | Cloud | 任务类型；仅在后端实际返回非空值时出现。 |
| `duration` | number | 否 | Cloud 终态 | 输入视频的总时长，单位为秒，用于计量计费。 |
| `resolution` | string | 否 | Cloud 终态 | 输入视频的分辨率。 |
| `video_url` | string | 否 | Cloud 终态 | 已嵌入暗水印的视频文件地址。返回 HTTPS 临时下载链接，有效期为 24 小时。 |

Cloud 调用成功后读取 `task_id`，再查询终态结果：

```bash
mediakit-cli shared query-task --task-id <task_id> --poll-complete
```

### 机器合同

以下命令只读取本模式的实时 help/schema，不发起业务调用：

```bash
mediakit-cli video add-video-invisible-watermark --help
mediakit-cli video add-video-invisible-watermark --schema
```
