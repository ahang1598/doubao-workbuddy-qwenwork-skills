# 视频抽帧

## 能力用途

从视频中抽取截图，截图结果支持用于视频封面、预览图、雪碧图或其他视频理解任务的输入。

## 参数填写规则

- 可选参数仅在用户明确指定，或可从用户意图准确确定时填写；不得伪造。不能准确确定时省略，确为正确完成任务所必需时先向用户澄清。
## Cloud

### 命令与生命周期

- 命令：`mediakit-cli video extract-frames`
- 生命周期：异步
- 返回方式：返回 `task_id`，再查询终态结果。

### 使用指南

- 对象或对象数组参数（`--specified-frames`、`--specified-time`）需传合法 JSON 字符串并整体加单引号；字段名与层级必须与下方参数表及子字段说明一致。
- 不要用逗号分隔或裸文本传这些参数。
- 布尔参数（`--enable-sprite`）只能写成 `--enable-sprite=true` 或 `--enable-sprite=false`，也可用裸 `--enable-sprite`（等价 true）；禁止空格传值 `--enable-sprite true`，否则该值会被当作位置参数。
- 布尔参数取默认值时直接省略，不要显式重复默认值。

### 调用示例

```bash
mediakit-cli video extract-frames \
  --video-url <video_url>
```

仅使用用户真实输入替换占位符；可选 flag 遵守参数填写规则，不得编造 URL、文件、枚举或业务参数。

### 参数

| 参数路径 | CLI flag | 类型 | 必填 | 默认值 | 枚举/范围/结构 | 说明 |
| --- | --- | --- | --- | --- | --- | --- |
| `client_token` | `--client-token` | string | 否 | - | - | 用户请求凭证，用于幂等控制；大小写敏感，长度不超过 64 个 ASCII 可打印字符。 用于控制异步任务幂等；同步任务不支持幂等校验。异步任务首次提交时默认不传，服务端仍会对相同核心参数执行 24 小时默认幂等。用户明确指定 token 时原样使用。因网络超时、响应丢失等原因重试同一次提交时，原请求有 token 则复用原值，原请求未传则继续不传。任务已有结果后，用户要求“结果不对，重试”“重新跑一次”或“重新发起任务”时，必须生成并传递新的 token，避免返回原任务。新对话中用户要求“重新发起任务”时，若当前上下文具备完整任务参数，直接生成新 token 并提交；若参数不足，先向用户澄清，补齐后再使用新 token 发起，不得直接省略 token。新任务后续发生提交重试时复用该新 token。已有 task_id 且任务尚未完成时，只查询原任务，不得重新提交。CLI runtime 不判断用户意图，也不自动生成 token。 |
| `enable_sprite` | `--enable-sprite` | boolean | 否 | false | - | 默认 false。设为 true 时输出包含所有截图的雪碧图；设为 false 时输出多张独立截图。 |
| `scale_long` | `--scale-long` | integer | 否 | - | 最小值: 0；最大值: 4096 | scale_long 最小值为 0，最大值为 4096。输出图片长边不得超过原始视频长边。按长边缩放时，输出图片短边按原始比例自适应。enable_sprite 为 true 时，scale_long 定义单张小图的长边。同时设置 scale_long 和 scale_short 时保持原始宽高比，并分别约束长边和短边。 |
| `scale_short` | `--scale-short` | integer | 否 | - | 最小值: 0；最大值: 4096 | scale_short 最小值为 0，最大值为 4096。输出图片短边不得超过原始视频短边。按短边缩放时，输出图片长边按原始比例自适应。enable_sprite 为 true 时，scale_short 定义单张小图的短边。同时设置 scale_long 和 scale_short 时保持原始宽高比，并分别约束长边和短边。 |
| `scene_change_threshold` | `--scene-change-threshold` | number | 否 | 0.1 | 最小值: 0；最大值: 1 | scene_change_threshold 默认值为 0.1。scene_change_threshold 必须大于 0 且必须小于 1。scene_change_threshold 仅在 snapshot_type 为 SceneChange 时生效。scene_change_threshold 越小，场景变化检测越敏感，可能产生更多截图。 |
| `snapshot_limit` | `--snapshot-limit` | integer | 否 | - | 最小值: 1；最大值: 1000 | snapshot_limit 最小值为 1，最大值为 1000。实际输出的截图数可能小于 snapshot_limit。snapshot_limit 仅在 snapshot_type 为 TimeInterval 或 SceneChange 时生效。enable_sprite 为 true 时，snapshot_limit 表示雪碧图大图数量上限，小图数量上限为 snapshot_limit*sprite_rows*sprite_cols。 |
| `snapshot_type` | `--snapshot-type` | string | 否 | "TimeInterval" | 枚举: ["TimeInterval","SpecifiedTime","SpecifiedFrames","SceneChange"] | snapshot_type 决定抽帧的具体方式，默认为 TimeInterval，支持 TimeInterval、SpecifiedTime、SpecifiedFrames 和 SceneChange 四个字面值。TimeInterval 表示按时间间隔抽帧，并需配合 time_interval。SpecifiedTime 表示按指定时间点抽帧，并需配合 specified_time。SpecifiedFrames 表示按指定帧号抽帧，并需配合 specified_frames。SceneChange 表示按场景变化抽帧，并需配合 scene_change_threshold。 |
| `specified_frames` | `--specified-frames` | array<integer> | 否 | - | 最少项数: 1；最多项数: 2；元素枚举: [0,-1] | specified_frames 当前仅支持 0 表示视频首帧、-1 表示视频尾帧，最多支持 2 个值。 |
| `specified_time` | `--specified-time` | array<number> | 否 | - | 最少项数: 1；最多项数: 1000；元素最小值: 0 | specified_time 中时间点的单位为秒，支持最多 3 位小数，最多支持 1000 个时间点。 |
| `sprite_cols` | `--sprite-cols` | integer | 否 | 10 | 最小值: 1；最大值: 100 | sprite_cols 表示雪碧图在 X 轴水平方向的小图数量，默认值为 10，最小值为 1，最大值为 100。sprite_cols 仅在 enable_sprite 为 true 时生效。过大的雪碧图行列数可能导致任务失败，雪碧图建议单边不超过 16384 像素。 |
| `sprite_rows` | `--sprite-rows` | integer | 否 | 10 | 最小值: 1；最大值: 100 | sprite_rows 表示雪碧图在 Y 轴垂直方向的小图数量，默认值为 10，最小值为 1，最大值为 100。sprite_rows 仅在 enable_sprite 为 true 时生效。过大的雪碧图行列数可能导致任务失败，雪碧图建议单边不超过 16384 像素。 |
| `time_interval` | `--time-interval` | number | 否 | 1 | 最小值: 0.001 | time_interval 默认值为 1，单位为秒，支持最多 3 位小数，必须大于 0.001。time_interval 仅在 snapshot_type 为 TimeInterval 时生效。 |
| `video_url` | `--video-url` | string | 是 | - | - | video_url 是待处理的视频 URL，支持本地文件路径和公网 HTTP/HTTPS URL 两种输入协议。视频输入支持 mp4、mov、mkv、flv、ts、avi、wmv 等主流视频格式。 |

### 返回结果

| 字段路径 | 类型 | 必含 | 模式 | 说明 |
| --- | --- | --- | --- | --- |
| `request_id` | string | 否 | Cloud | 请求标识；仅在后端返回时出现。 |
| `task_id` | string | 是 | Cloud | 异步任务的唯一标识，用于查询任务状态并获取最终结果。 |
| `task_type` | string | 否 | Cloud | 任务类型；仅在后端实际返回非空值时出现。 |
| `snapshot_count` | integer | 否 | Cloud 终态 | snapshot_count 是成功生成的截图总数；雪碧图模式下，snapshot_count 表示雪碧图中的小图数量。 |
| `snapshots` | array<object> | 否 | Cloud 终态 | 截图结果列表。每个对象包含一张截图的信息。 |
| `snapshots[].image_url` | string | 否 | Cloud 终态 | 截图下载地址。该地址的有效期为 24 小时，请务必及时保存产物。 |

Cloud 调用成功后读取 `task_id`，再查询终态结果：

```bash
mediakit-cli shared query-task --task-id <task_id> --poll-complete
```

### 机器合同

以下命令只读取本模式的实时 help/schema，不发起业务调用：

```bash
mediakit-cli video extract-frames --help
mediakit-cli video extract-frames --schema
```
