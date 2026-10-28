# 视频人脸打码

## 能力用途

视频人脸打码可自动精准识别视频画面中的人脸区域，并对所有人脸进行模糊或马赛克处理，适用于需要保护人物五官隐私的场景。

## 参数填写规则

- 可选参数仅在用户明确指定，或可从用户意图准确确定时填写；不得伪造。不能准确确定时省略，确为正确完成任务所必需时先向用户澄清。
## 语义效果选项

### `mask_mode` 可选效果

| 语义名称 | 参数值 | 说明 |
| --- | --- | --- |
| 马赛克 | `mosaic` | 以马赛克遮挡人脸。 |
| 高斯模糊 | `blur` | 以高斯模糊遮挡人脸。 |

### `mask_strength` 可选效果

| 语义名称 | 参数值 | 说明 |
| --- | --- | --- |
| 中强度 | `medium` | 中强度人脸打码。 |
| 低强度 | `low` | 低强度人脸打码。 |
| 高强度 | `high` | 高强度人脸打码。 |

## Cloud

### 命令与生命周期

- 命令：`mediakit-cli video face-blur-video`
- 生命周期：异步
- 返回方式：返回 `task_id`，再查询终态结果。

### 使用指南

- 可选参数取默认值时直接省略，不要显式重复默认值。

### 调用示例

```bash
mediakit-cli video face-blur-video \
  --video-url <video_url>
```

仅使用用户真实输入替换占位符；可选 flag 遵守参数填写规则，不得编造 URL、文件、枚举或业务参数。

### 参数

| 参数路径 | CLI flag | 类型 | 必填 | 默认值 | 枚举/范围/结构 | 说明 |
| --- | --- | --- | --- | --- | --- | --- |
| `client_token` | `--client-token` | string | 否 | - | - | 用户请求凭证，用于幂等控制；大小写敏感，长度不超过 64 个 ASCII 可打印字符。 用于控制异步任务幂等；同步任务不支持幂等校验。异步任务首次提交时默认不传，服务端仍会对相同核心参数执行 24 小时默认幂等。用户明确指定 token 时原样使用。因网络超时、响应丢失等原因重试同一次提交时，原请求有 token 则复用原值，原请求未传则继续不传。任务已有结果后，用户要求“结果不对，重试”“重新跑一次”或“重新发起任务”时，必须生成并传递新的 token，避免返回原任务。新对话中用户要求“重新发起任务”时，若当前上下文具备完整任务参数，直接生成新 token 并提交；若参数不足，先向用户澄清，补齐后再使用新 token 发起，不得直接省略 token。新任务后续发生提交重试时复用该新 token。已有 task_id 且任务尚未完成时，只查询原任务，不得重新提交。CLI runtime 不判断用户意图，也不自动生成 token。 |
| `face_box_expand` | `--face-box-expand` | number | 否 | 0.2 | 最大值: 1；大于: 0 | 人脸边界框扩展比例，范围大于 0.0 且不超过 1.0，默认值为 0.2。系统将根据该比例在检测到的人脸区域基础上向外扩展打码范围。 |
| `face_confidence` | `--face-confidence` | number | 否 | 0.35 | 最小值: 0.1；最大值: 1 | 人脸检测置信度阈值，范围 0.1 至 1.0，默认值为 0.35。低于此阈值的检测结果将被丢弃。 |
| `mask_mode` | `--mask-mode` | string | 否 | "mosaic" | 枚举: ["mosaic","blur"] | 人脸打码方式：mosaic 表示马赛克，为默认值；blur 表示高斯模糊。 |
| `mask_strength` | `--mask-strength` | string | 否 | "medium" | 枚举: ["low","medium","high"] | 人脸打码强度：low 表示低强度；medium 表示中强度，为默认值；high 表示高强度。 |
| `video_url` | `--video-url` | string | 是 | - | - | 待打码的视频 URL，支持本地文件路径和公网 HTTP/HTTPS URL 两种输入协议；支持 mp4、flv、ts、avi、mov、wmv、mkv 等主流视频格式；分辨率最高支持 4K，推荐使用 1080P 以获得最佳处理效果；帧率需在 25~60 范围内；视频时长不得超过 10 分钟。 |

### 返回结果

| 字段路径 | 类型 | 必含 | 模式 | 说明 |
| --- | --- | --- | --- | --- |
| `request_id` | string | 否 | Cloud | 请求标识；仅在后端返回时出现。 |
| `task_id` | string | 是 | Cloud | 异步任务的唯一标识，用于查询任务状态并获取最终结果。 |
| `task_type` | string | 否 | Cloud | 任务类型；仅在后端实际返回非空值时出现。 |
| `duration` | number | 否 | Cloud 终态 | 输出视频总时长，单位为秒，可用于计量计费。 |
| `video_url` | string | 否 | Cloud 终态 | 已完成人脸打码的视频文件地址。返回 HTTPS 临时下载链接，有效期为 24 小时； |

Cloud 调用成功后读取 `task_id`，再查询终态结果：

```bash
mediakit-cli shared query-task --task-id <task_id> --poll-complete
```

### 机器合同

以下命令只读取本模式的实时 help/schema，不发起业务调用：

```bash
mediakit-cli video face-blur-video --help
mediakit-cli video face-blur-video --schema
```
