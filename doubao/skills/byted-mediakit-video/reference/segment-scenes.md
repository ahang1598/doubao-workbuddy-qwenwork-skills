# 场景切分

## 能力用途

依据视频的转场和画面内容变化自动切分多个场景片段，输出每个场景片段的时间轴信息与对应的独立视频文件。

## 参数填写规则

- 可选参数仅在用户明确指定，或可从用户意图准确确定时填写；不得伪造。不能准确确定时省略，确为正确完成任务所必需时先向用户澄清。
## Cloud

### 命令与生命周期

- 命令：`mediakit-cli video segment-scenes`
- 生命周期：异步
- 返回方式：返回 `task_id`，再查询终态结果。

### 使用指南

- 布尔参数（`--enable-clip-fade`、`--return-segment-videos`）只能写成 `--enable-clip-fade=true` 或 `--enable-clip-fade=false`，也可用裸 `--enable-clip-fade`（等价 true）；禁止空格传值 `--enable-clip-fade true`，否则该值会被当作位置参数。
- 布尔参数取默认值时直接省略，不要显式重复默认值。

### 调用示例

```bash
mediakit-cli video segment-scenes \
  --video-url <video_url>
```

仅使用用户真实输入替换占位符；可选 flag 遵守参数填写规则，不得编造 URL、文件、枚举或业务参数。

### 参数

| 参数路径 | CLI flag | 类型 | 必填 | 默认值 | 枚举/范围/结构 | 说明 |
| --- | --- | --- | --- | --- | --- | --- |
| `client_token` | `--client-token` | string | 否 | - | - | 用户请求凭证，用于幂等控制；大小写敏感，长度不超过 64 个 ASCII 可打印字符。 用于控制异步任务幂等；同步任务不支持幂等校验。异步任务首次提交时默认不传，服务端仍会对相同核心参数执行 24 小时默认幂等。用户明确指定 token 时原样使用。因网络超时、响应丢失等原因重试同一次提交时，原请求有 token 则复用原值，原请求未传则继续不传。任务已有结果后，用户要求“结果不对，重试”“重新跑一次”或“重新发起任务”时，必须生成并传递新的 token，避免返回原任务。新对话中用户要求“重新发起任务”时，若当前上下文具备完整任务参数，直接生成新 token 并提交；若参数不足，先向用户澄清，补齐后再使用新 token 发起，不得直接省略 token。新任务后续发生提交重试时复用该新 token。已有 task_id 且任务尚未完成时，只查询原任务，不得重新提交。CLI runtime 不判断用户意图，也不自动生成 token。 |
| `enable_clip_fade` | `--enable-clip-fade` | boolean | 否 | false | - | enable_clip_fade 控制是否将检测到的淡入或淡出片段作为独立切片输出。enable_clip_fade 的默认值为 false。enable_clip_fade 为 true 且视频存在明显淡入或淡出过渡时，会将其分割为独立切片。enable_clip_fade 为 false 时不独立输出淡入或淡出片段，而将其视为前后场景的一部分并合并到相邻切片。 |
| `max_duration` | `--max-duration` | number | 否 | - | 最小值: 0 | max_duration 表示单个切片的最大时长，单位为秒。max_duration 的默认值为 30 秒。max_duration 必须大于或等于 min_duration。大于 max_duration 的片段将被强制切分。 |
| `min_duration` | `--min-duration` | number | 否 | - | 最小值: 0 | min_duration 表示单个切片的最小时长，单位为秒。min_duration 的默认值为 3 秒。小于 min_duration 的片段将被合并。min_duration 必须小于或等于 max_duration。 |
| `return_segment_videos` | `--return-segment-videos` | boolean | 否 | true | - | return_segment_videos 的默认值为 true。return_segment_videos 为 true 时生成切片文件，并在 segments[].segment_video_url 返回各切片下载链接。return_segment_videos 为 false 时不生成切片文件，仅返回 start_time 和 end_time 切片时间轴，不返回 segment_video_url。false 可用于只需获取场景时间码并由业务侧自行处理切片的场景，可降低任务耗时。 |
| `segment_threshold` | `--segment-threshold` | number | 否 | - | 最小值: 0；最大值: 100 | segment_threshold 是场景切分的敏感度阈值，最小值为 0，必须小于 100。取值越低，算法对场景变化越敏感，切分出的片段越多；取值越高，算法越倾向将微小变化视为同一场景，切分出的片段越少。同时设置 min_duration、max_duration 和 segment_threshold 时，系统采用两阶段逻辑以满足全部约束：第一阶段根据 segment_threshold 和 min_duration 进行切分；第一阶段后如有切片时长超过 max_duration，系统忽略 segment_threshold 再次切分，确保最终时长不超过 max_duration。 |
| `video_url` | `--video-url` | string | 是 | - | - | video_url 是待处理的视频 URL。视频来源支持本地文件路径和公网 HTTP/HTTPS URL 两种输入协议。支持 mp4、flv、ts、avi、mov、wmv、mkv 等主流视频格式。单个视频时长必须不超过 2 小时。 |

### 返回结果

| 字段路径 | 类型 | 必含 | 模式 | 说明 |
| --- | --- | --- | --- | --- |
| `request_id` | string | 否 | Cloud | 请求标识；仅在后端返回时出现。 |
| `task_id` | string | 是 | Cloud | 异步任务的唯一标识，用于查询任务状态并获取最终结果。 |
| `task_type` | string | 否 | Cloud | 任务类型；仅在后端实际返回非空值时出现。 |
| `duration` | number | 否 | Cloud 终态 | duration 是输入视频的总时长，单位为秒。 |
| `segments` | array<object> | 否 | Cloud 终态 | 切片信息列表。每个元素是一个包含切片起止时间等信息的对象。 |
| `segments[].end_time` | number | 否 | Cloud 终态 | segments[].end_time 是切片的结束时间，单位为秒。 |
| `segments[].segment_video_url` | string | 否 | Cloud 终态 | 切片视频文件的下载地址，有效期为 24 小时，输出视频为 MP4 格式。仅当请求参数 return_segment_videos 为 true（默认）时返回；当 return_segment_videos 为 false 时不生成切片文件，本字段不返回。 |
| `segments[].start_time` | number | 否 | Cloud 终态 | segments[].start_time 是切片的起始时间，单位为秒。 |

Cloud 调用成功后读取 `task_id`，再查询终态结果：

```bash
mediakit-cli shared query-task --task-id <task_id> --poll-complete
```

### 机器合同

以下命令只读取本模式的实时 help/schema，不发起业务调用：

```bash
mediakit-cli video segment-scenes --help
mediakit-cli video segment-scenes --schema
```
