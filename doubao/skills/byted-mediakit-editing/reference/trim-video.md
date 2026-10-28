# 视频裁剪

## 能力用途

用于视频裁剪，可按指定的开始和结束时间从输入视频截取片段。

## 参数填写规则

- 可选参数仅在用户明确指定，或可从用户意图准确确定时填写；不得伪造。不能准确确定时省略，确为正确完成任务所必需时先向用户澄清。
## Cloud

### 命令与生命周期

- 命令：`mediakit-cli editing trim-video`
- 生命周期：异步
- 返回方式：返回 `task_id`，再查询终态结果。

### 参数

| 参数路径 | CLI flag | 类型 | 必填 | 默认值 | 枚举/范围/结构 | 说明 |
| --- | --- | --- | --- | --- | --- | --- |
| `client_token` | `--client-token` | string | 否 | - | - | 用户请求凭证，用于幂等控制；大小写敏感，长度不超过 64 个 ASCII 可打印字符。 用于控制异步任务幂等；同步任务不支持幂等校验。异步任务首次提交时默认不传，服务端仍会对相同核心参数执行 24 小时默认幂等。用户明确指定 token 时原样使用。因网络超时、响应丢失等原因重试同一次提交时，原请求有 token 则复用原值，原请求未传则继续不传。任务已有结果后，用户要求“结果不对，重试”“重新跑一次”或“重新发起任务”时，必须生成并传递新的 token，避免返回原任务。新对话中用户要求“重新发起任务”时，若当前上下文具备完整任务参数，直接生成新 token 并提交；若参数不足，先向用户澄清，补齐后再使用新 token 发起，不得直接省略 token。新任务后续发生提交重试时复用该新 token。已有 task_id 且任务尚未完成时，只查询原任务，不得重新提交。CLI runtime 不判断用户意图，也不自动生成 token。 |
| `end_time` | `--end-time` | number | 否 | - | 最小值: 0 | 裁剪结束时间，单位为秒；支持最多两位小数；必须大于 start_time。未传时默认裁剪到输入视频末尾。 |
| `start_time` | `--start-time` | number | 否 | 0 | 最小值: 0 | 裁剪开始时间，单位为秒；支持最多两位小数；必须小于 end_time。默认为 0，表示从视频开头开始。 |
| `video_url` | `--video-url` | string | 是 | - | - | 待裁剪视频的 URL；支持本地文件路径和公网 HTTP/HTTPS URL 两种来源协议；支持 mp4、flv、ts、avi、mov、wmv、mkv 等主流视频格式；最高支持 4K（3840×2160）分辨率；建议单个输入文件不超过 10 GB。 |

### 参数关系

- `$.end_time` 必须大于 `$.start_time`。

### 调用示例

```bash
mediakit-cli editing trim-video \
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
| `resolution` | string | 否 | Cloud 终态 | 输出视频的分辨率。 |
| `video_url` | string | 否 | Cloud 终态 | 裁剪后视频文件地址，文件格式为 MP4。返回有效期 24 小时的 HTTPS 临时下载链接，需要及时下载保存； |

Cloud 调用成功后读取 `task_id`，再查询终态结果：

```bash
mediakit-cli shared query-task --task-id <task_id> --poll-complete
```

### 机器合同

以下命令只读取本模式的实时 help/schema，不发起业务调用：

```bash
mediakit-cli editing trim-video --help
mediakit-cli editing trim-video --schema
```
