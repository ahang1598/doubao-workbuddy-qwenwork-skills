# 视频转码

## 能力用途

视频转码将视频码流转换为另一视频码流，可涉及编码格式、分辨率、码率、I 帧间隔和封装格式转换，用于适应不同业务场景、播放终端和网络环境。

## 参数填写规则

- 可选参数仅在用户明确指定，或可从用户意图准确确定时填写；不得伪造。不能准确确定时省略，确为正确完成任务所必需时先向用户澄清。
## 语义效果选项

### `video.scale_mode` 可选效果

| 语义名称 | 参数值 | 说明 |
| --- | --- | --- |
| 不上采 | `0` | 源片大于目标时缩小，小于目标时保持原尺寸。 |
| 拉伸上采 | `1` | 强制拉伸到目标宽高，可能导致画面变形。 |
| 补黑边上采 | `2` | 等比缩放到目标框内，并用黑边填充不足部分。 |

## Cloud

### 命令与生命周期

- 命令：`mediakit-cli video transcode-video`
- 生命周期：异步
- 返回方式：返回 `task_id`，再查询终态结果。

### 使用指南


- `{}` 和 `[{}]` 仅展示 JSON 容器形状。命令模板中的 `<参数名_json>` 必须替换为符合参数表、已补齐必填字段的合法 JSON；不得直接提交空容器或占位符。
- 数组参数（`--metadata-keep-tags`）传多个值时用逗号分隔并整体加引号，例如 `--metadata-keep-tags "url1,url2"`。
- 单个值中的文件名或 URL 不能包含逗号（`,`），否则会被 CLI 当成多个元素拆开。遇到这种情况时，先向用户澄清，请其提供不含逗号的文件名或对应 URL 后再调用。
- 对象或对象数组参数（`--audio`、`--metadata-add-tags`、`--video`）需传合法 JSON 字符串；字段名与层级必须与上表“枚举/范围/结构”及子字段说明一致。不要用逗号分隔或裸文本。
- POSIX / bash：用单引号整体包裹，例如 `--audio '{}'`。
- Windows PowerShell：按共享入口 [JSON 参数传参](../../byted-mediakit-shared/SKILL.md) 把 JSON flag 放在 `--%` 之后，内部双引号写成 `\"`，例如 `--% --audio "{}"`。Windows 内联 JSON 禁止单引号 JSON 和 `$json` 变量；`@文件`、stdin `-`、`file://` 写法按共享入口 [JSON 参数传参](../../byted-mediakit-shared/SKILL.md) 执行。

### 调用示例

```bash
mediakit-cli video transcode-video \
  --video-url <video_url> \
  --container-format <container_format> \
  --video '<video_json>'
```

仅使用用户真实输入替换占位符；可选 flag 遵守参数填写规则，不得编造 URL、文件、枚举或业务参数。

### 参数

| 参数路径 | CLI flag | 类型 | 必填 | 默认值 | 枚举/范围/结构 | 说明 |
| --- | --- | --- | --- | --- | --- | --- |
| `audio` | `--audio` | object | 否 | - | - | 不传 audio 时，音频使用 aac 编码，其他参数跟随源文件。 |
| `audio.bitrate_kbps` | - | integer | 是 | 128（Schema 默认；仍需显式提供） | 最小值: 10；最大值: 500 | 音频码率单位 Kbps，范围 [10, 500]，默认 128；不设置时跟随原始音频码率。 |
| `audio.bitrate_mode` | - | string | 是 | "cbr"（Schema 默认；仍需显式提供） | 枚举: ["cbr","cae"] | cae 仅在 audio.codec=aac 时支持，按内容复杂度调整瞬时码率并使平均码率接近 bitrate_kbps。cbr 是默认恒定码率模式，仅在 video.codec=h264 时支持，用于带宽稳定性要求高的流式传输。 |
| `audio.channels` | - | integer | 否 | 2 | 枚举: [1,2] | 音频声道数支持 1（单声道）和 2（双声道），默认是 2。 |
| `audio.codec` | - | string | 是 | "aac"（Schema 默认；仍需显式提供） | 枚举: ["aac"] | 音频编码当前仅支持 aac，默认也是 aac。 |
| `audio.sample_rate` | - | integer | 是 | 44100（Schema 默认；仍需显式提供） | 枚举: [8000,11025,12000,16000,22050,24000,32000,44100,48000,64000,88200,96000] | aac 支持采样率 8000、11025、12000、16000、22050、24000、32000、44100、48000、64000、88200、96000 Hz，默认 44100 Hz。 |
| `audio.volume_integrated_loudness` | - | number | 否 | -12 | 最小值: -70；最大值: -5 | 响度值设置，用于在音量均衡模式下调整音频的整体响度水平。范围为 [-70, -5]，默认值为 -12。当 volume_method 为 2Pass 时，该参数必填。 |
| `audio.volume_loudness_range` | - | number | 否 | 7 | 最小值: 1；最大值: 20 | 响度范围单位 LU，范围 [1, 20]，默认 7；volume_method=2Pass 时生效。 |
| `audio.volume_method` | - | string | 否 | - | 枚举: ["2Pass"] | volume_method=2Pass 可启用两阶段响度分析与处理，使三个响度参数生效；不设置时不处理音量。 |
| `audio.volume_true_peak` | - | number | 否 | 0 | 最小值: -9；最大值: 0 | 音量峰值，用于在音量均衡模式下设置音频的最大峰值。范围为 [-9, 0]，默认值为 0。当 volume_method 为 2Pass 时，该参数必填。 |
| `client_token` | `--client-token` | string | 否 | - | - | 用户请求凭证，用于幂等控制；大小写敏感，长度不超过 64 个 ASCII 可打印字符。 用于控制异步任务幂等；同步任务不支持幂等校验。异步任务首次提交时默认不传，服务端仍会对相同核心参数执行 24 小时默认幂等。用户明确指定 token 时原样使用。因网络超时、响应丢失等原因重试同一次提交时，原请求有 token 则复用原值，原请求未传则继续不传。任务已有结果后，用户要求“结果不对，重试”“重新跑一次”或“重新发起任务”时，必须生成并传递新的 token，避免返回原任务。新对话中用户要求“重新发起任务”时，若当前上下文具备完整任务参数，直接生成新 token 并提交；若参数不足，先向用户澄清，补齐后再使用新 token 发起，不得直接省略 token。新任务后续发生提交重试时复用该新 token。已有 task_id 且任务尚未完成时，只查询原任务，不得重新提交。CLI runtime 不判断用户意图，也不自动生成 token。 |
| `container_format` | `--container-format` | string | 是 | "MP4"（Schema 默认；仍需显式提供） | 枚举: ["MP4","FLV","MPEGTS"] | 输出封装格式支持 MP4、FLV、MPEGTS，默认是 MP4。 |
| `metadata_add_tags` | `--metadata-add-tags` | array<object> | 否 | - | - | 新增元信息标签与保留标签同名时，新设置覆盖源文件值。metadata_add_tags 对 MPEGTS 封装格式无效。 |
| `metadata_add_tags[].key` | - | string | 否 | - | - | 标签键。 |
| `metadata_add_tags[].value` | - | string | 否 | - | - | 标签值。 |
| `metadata_keep_tags` | `--metadata-keep-tags` | array<string> | 否 | - | - | 可指定从源视频保留的元信息标签键；默认转码会丢弃大部分元信息。metadata_keep_tags 对 MPEGTS 封装格式无效。 |
| `video` | `--video` | object | 是 | - | - | 视频参数，必填 |
| `video.bitrate_crf` | - | number | 否 | 25 | 最小值: 0；最大值: 51 | bitrate_crf 仅在 bitrate_mode=crf 时生效；值越小画质越高、体积越大，0 表示无损。bitrate_crf 范围 [0, 51]。 |
| `video.bitrate_kbps` | - | integer | 是 | 2000（Schema 默认；仍需显式提供） | 最小值: 10；最大值: 50000 | video.bitrate_kbps 在 crf、abr、cbr 模式下分别表示最大码率限制、平均码率目标、恒定码率目标。 |
| `video.bitrate_mode` | - | string | 是 | "crf"（Schema 默认；仍需显式提供） | 枚举: ["crf","abr","cbr"] | crf 推荐用于大多数场景，尽量保持 bitrate_crf 指定的视觉质量，并以 bitrate_kbps 限制瞬时码率。abr 调整码率使整体平均码率接近 bitrate_kbps，适合将文件大小控制在特定范围。cbr 尝试让视频流每秒严格保持 bitrate_kbps 设定码率，适合要求网络传输稳定的流媒体场景。 |
| `video.codec` | - | string | 是 | "h264"（Schema 默认；仍需显式提供） | 枚举: ["h264","h265"] | 视频编码格式支持 h264 和 h265，默认是 h264。 |
| `video.fps` | - | integer | 否 | - | 最小值: 1；最大值: 240 | fps 范围 [1, 240]；vfr 下是最大帧率，cfr 下是恒定帧率。 |
| `video.fps_mode` | - | string | 否 | "vfr" | 枚举: ["vfr","cfr"] | 只有设置 fps 后 fps_mode 才生效；未提供 fps 时遵循原视频帧率并忽略 fps_mode。cfr 将 fps 作为强制恒定输出帧率。vfr 将 fps 作为最高帧率；源帧率较低时保留，较高时降低到 fps。 |
| `video.is_hdr_to_sdr` | - | boolean | 否 | true | - | true 将 HDR 转换为 SDR；false 保留 HDR。 |
| `video.scale_height` | - | integer | 否 | - | 最小值: 0；最大值: 4320 | scale_height 单位为 px，范围 [0, 4320]，仅在 scale_type=2 时生效；只传宽或高之一时另一边按比例缩放。 |
| `video.scale_long` | - | integer | 否 | - | 最小值: 0；最大值: 4320 | scale_long 单位为 px，范围 [0, 4320]，仅在 scale_type=1 时生效；只传短边或长边之一时另一边按比例缩放。 |
| `video.scale_mode` | - | integer | 否 | 0 | 枚举: [0,1,2] | scale_mode 仅在 scale_type 为 1 或 2 时生效。0 不上采：源片大于目标时缩小，小于目标时保持原尺寸。1 强制拉伸到目标宽高，可能导致画面变形。2 等比缩放到目标框内并用黑边填充不足部分。 |
| `video.scale_short` | - | integer | 否 | - | 最小值: 0；最大值: 4320 | scale_short 单位为 px，范围 [0, 4320]，仅在 scale_type=1 时生效；只传短边或长边之一时另一边按比例缩放。 |
| `video.scale_type` | - | integer | 否 | 0 | 枚举: [0,1,2] | scale_type=0 跟随片源且不缩放，相关尺寸参数无效，最高支持 8K。scale_type=1 激活 scale_short 和 scale_long，另一边按原比例缩放，最高支持 4K。scale_type=2 激活 scale_width 和 scale_height，另一边按原比例缩放，最高支持 4K。视频缩放模式默认是 0。 |
| `video.scale_width` | - | integer | 否 | - | 最小值: 0；最大值: 4320 | scale_width 单位为 px，范围 [0, 4320]，仅在 scale_type=2 时生效；只传宽或高之一时另一边按比例缩放。 |
| `video_url` | `--video-url` | string | 是 | - | - | 待转码视频支持 mp4、mov、mkv、flv、ts、avi、wmv 等主流视频格式；支持本地文件路径和公网 HTTP/HTTPS URL 两种来源协议。 |

### 返回结果

| 字段路径 | 类型 | 必含 | 模式 | 说明 |
| --- | --- | --- | --- | --- |
| `request_id` | string | 否 | Cloud | 请求标识；仅在后端返回时出现。 |
| `task_id` | string | 是 | Cloud | 异步任务的唯一标识，用于查询任务状态并获取最终结果。 |
| `task_type` | string | 否 | Cloud | 任务类型；仅在后端实际返回非空值时出现。 |
| `duration` | number | 否 | Cloud 终态 | 转码后视频时长，单位为秒。 |
| `resolution` | string | 否 | Cloud 终态 | 转码后视频分辨率规格，可能包括 240p、360p、480p、540p、720p、1080p、2k、4k 等。 |
| `video_codec` | string | 否 | Cloud 终态 | 转码后视频的编码格式。 |
| `video_url` | string | 否 | Cloud 终态 | 返回有效期 24 小时的 HTTPS 临时下载链接； |

Cloud 调用成功后读取 `task_id`，再查询终态结果：

```bash
mediakit-cli shared query-task --task-id <task_id> --poll-complete
```

### 机器合同

以下命令只读取本模式的实时 help/schema，不发起业务调用：

```bash
mediakit-cli video transcode-video --help
mediakit-cli video transcode-video --schema
```
