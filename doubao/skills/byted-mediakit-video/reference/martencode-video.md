# 极智超清

## 能力用途

极智超清在转码时智能分析视频的场景、动作、内容和纹理，选择最优编码参数，以相对较低码率输出主观画质更优的视频，降低带宽成本并改善用户视觉体验。

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

- 命令：`mediakit-cli video martencode-video`
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
mediakit-cli video martencode-video \
  --video-url <video_url> \
  --container-format <container_format> \
  --video '<video_json>'
```

仅使用用户真实输入替换占位符；可选 flag 遵守参数填写规则，不得编造 URL、文件、枚举或业务参数。

### 参数

| 参数路径 | CLI flag | 类型 | 必填 | 默认值 | 枚举/范围/结构 | 说明 |
| --- | --- | --- | --- | --- | --- | --- |
| `audio` | `--audio` | object | 否 | - | - | 音频转码参数配置可省略；未传 audio 时，音频使用默认参数转码：编码格式为 aac，其余参数跟随源文件。 |
| `audio.bitrate_kbps` | - | integer | 是 | 128（Schema 默认；仍需显式提供） | 最小值: 10；最大值: 500 | 音频码率，单位 Kbps，支持 10 至 500，默认 128；未设置时输出音频码率与原始音频一致。 |
| `audio.bitrate_mode` | - | string | 是 | "cbr"（Schema 默认；仍需显式提供） | 枚举: ["cbr","cae"] | 音频码率控制模式，支持 cbr、cae，默认 cbr。cbr 仅在 video.codec=h264 时支持，会尝试使音频流每一秒保持在 audio.bitrate_kbps 设定码率，适合对带宽稳定性要求高的流式传输场景；cae 仅在 audio.codec=aac 时支持，会根据音频复杂度动态调整瞬时码率，并确保整个文件平均码率接近 audio.bitrate_kbps 目标值。 |
| `audio.channels` | - | integer | 否 | 2 | 枚举: [1,2] | 声道数可省略，支持 1、2，默认 2；1 表示单声道，2 表示双声道。 |
| `audio.codec` | - | string | 是 | "aac"（Schema 默认；仍需显式提供） | 枚举: ["aac"] | 音频编码格式，支持 aac，默认 aac。 |
| `audio.sample_rate` | - | integer | 是 | 44100（Schema 默认；仍需显式提供） | 枚举: [8000,11025,12000,16000,22050,24000,32000,44100,48000,64000,88200,96000] | 音频采样率，单位 Hz，支持 8000、11025、12000、16000、22050、24000、32000、44100、48000、64000、88200、96000，默认 44100。 |
| `audio.volume_integrated_loudness` | - | number | 否 | -12 | 最小值: -70；最大值: -5 | 音频整体感知音量，单位 LUFS，可省略，支持 -70 至 -5，默认 -12。 |
| `audio.volume_loudness_range` | - | number | 否 | 7 | 最小值: 1；最大值: 20 | 响度范围用于调节最响亮和最安静部分差异，单位 LU，可省略，支持 1 至 20，默认 7；在 audio.volume_method=2Pass 时生效。 |
| `audio.volume_method` | - | string | 否 | - | 枚举: ["2Pass"] | 音量均衡算法可省略；未设置时不处理音量。2Pass 启用两阶段响度分析与处理，且三个响度参数生效。 |
| `audio.volume_true_peak` | - | number | 否 | 0 | 最小值: -9；最大值: 0 | 音频最高上限用于防止削波失真，单位 dBTP，可省略，支持 -9 至 0，默认 0。 |
| `client_token` | `--client-token` | string | 否 | - | - | 用户请求凭证，用于幂等控制；大小写敏感，长度不超过 64 个 ASCII 可打印字符。 用于控制异步任务幂等；同步任务不支持幂等校验。异步任务首次提交时默认不传，服务端仍会对相同核心参数执行 24 小时默认幂等。用户明确指定 token 时原样使用。因网络超时、响应丢失等原因重试同一次提交时，原请求有 token 则复用原值，原请求未传则继续不传。任务已有结果后，用户要求“结果不对，重试”“重新跑一次”或“重新发起任务”时，必须生成并传递新的 token，避免返回原任务。新对话中用户要求“重新发起任务”时，若当前上下文具备完整任务参数，直接生成新 token 并提交；若参数不足，先向用户澄清，补齐后再使用新 token 发起，不得直接省略 token。新任务后续发生提交重试时复用该新 token。已有 task_id 且任务尚未完成时，只查询原任务，不得重新提交。CLI runtime 不判断用户意图，也不自动生成 token。 |
| `container_format` | `--container-format` | string | 是 | "MP4"（Schema 默认；仍需显式提供） | 枚举: ["MP4","FLV","MPEGTS"] | 输出视频的封装格式，支持 MP4、FLV、MPEGTS，默认 MP4。 |
| `metadata_add_tags` | `--metadata-add-tags` | array<object> | 否 | - | - | 可省略，为输出视频新增由 key 和 value 组成的元信息标签；新增标签与保留标签同名时覆盖源文件值；对 MPEGTS 封装格式无效。 |
| `metadata_add_tags[].key` | - | string | 否 | - | - | 标签键。 |
| `metadata_add_tags[].value` | - | string | 否 | - | - | 标签值。 |
| `metadata_keep_tags` | `--metadata-keep-tags` | array<string> | 否 | - | - | 可省略，指定从源视频保留的元信息标签键列表；默认转码会丢弃大部分元信息，例如标题和艺术家；对 MPEGTS 封装格式无效。 |
| `video` | `--video` | object | 是 | - | - | 视频转码参数配置。 |
| `video.bitrate_crf` | - | number | 否 | 25 | 最小值: 0；最大值: 51 | 码率 CRF 参数可省略，仅在 video.bitrate_mode=crf 时生效，是 crf 模式主要质量控制器；支持 0 至 51，默认 25；数值越小，画质越高且文件体积越大，0 表示无损。 |
| `video.bitrate_kbps` | - | integer | 是 | 2000（Schema 默认；仍需显式提供） | 最小值: 10；最大值: 50000 | 视频码率目标值，单位 Kbps，支持 10 至 50000，默认 2000；abr 模式下是平均码率目标，cbr 模式下是恒定码率目标，crf 模式下是最大码率限制。 |
| `video.bitrate_mode` | - | string | 是 | "crf"（Schema 默认；仍需显式提供） | 枚举: ["crf","abr","cbr"] | 码率控制模式，支持 crf、abr、cbr，默认 crf。crf 模式尽量保持整体视觉质量在 video.bitrate_crf 设定水平，同时确保瞬时码率不超过 video.bitrate_kbps，推荐大多数场景使用；abr 模式使输出整体平均码率接近 video.bitrate_kbps，适用于需要把文件大小控制在特定范围的场景；cbr 模式尝试让视频流每一秒保持在 video.bitrate_kbps 设定码率，画质随复杂度波动而码率稳定，适用于对网络传输稳定性要求极高的流媒体场景。 |
| `video.codec` | - | string | 是 | "h264"（Schema 默认；仍需显式提供） | 枚举: ["h264","h265"] | 视频编码格式，支持 h264、h265，默认 h264。 |
| `video.fps` | - | integer | 否 | - | 最小值: 1；最大值: 240 | 目标帧率可省略，支持 1 至 240；未设置时输出完全遵循原视频帧率。设置后会激活 video.fps_mode；vfr 下表示最大帧率，cfr 下表示恒定帧率。 |
| `video.fps_mode` | - | string | 否 | "vfr" | 枚举: ["vfr","cfr"] | 帧率模式可省略，支持 vfr、cfr，默认 vfr。仅在设置 video.fps 后生效；未提供 video.fps 时遵循源帧率并忽略 video.fps_mode。vfr 模式把 video.fps 作为最高帧率，源帧率较低时保留，较高时降低到设定值，避免不必要的帧率过度提升；cfr 模式把 video.fps 作为强制输出帧率，无论源帧率如何都转换为该恒定帧率。 |
| `video.is_hdr_to_sdr` | - | boolean | 否 | true | - | 可省略，控制是否将 HDR 视频转换为 SDR，默认 true；false 时保留 HDR。 |
| `video.scale_height` | - | integer | 否 | - | 最小值: 0；最大值: 4320 | 目标高度，单位 px，可省略，支持 0 至 4320；仅在 video.scale_type=2 时生效，只传宽或高之一时，另一边按比例缩放。 |
| `video.scale_long` | - | integer | 否 | - | 最小值: 0；最大值: 4320 | 目标长边，单位 px，可省略，支持 0 至 4320；仅在 video.scale_type=1 时生效，只传短边或长边之一时，另一边按比例缩放。 |
| `video.scale_mode` | - | integer | 否 | 0 | 枚举: [0,1,2] | 伸缩模式可省略，支持 0、1、2，默认 0，仅在 video.scale_type 为 1 或 2 时生效。0 不上采：源片比目标大时缩小，比目标小时保持原尺寸；1 拉伸上采，强制拉伸到目标宽高，可能导致画面变形；2 补黑边上采，等比缩放到目标框内，不足部分用黑边填充。 |
| `video.scale_short` | - | integer | 否 | - | 最小值: 0；最大值: 4320 | 目标短边，单位 px，可省略，支持 0 至 4320；仅在 video.scale_type=1 时生效，只传短边或长边之一时，另一边按比例缩放。 |
| `video.scale_type` | - | integer | 否 | 0 | 枚举: [0,1,2] | 伸缩限制可省略，支持 0、1、2，默认 0。0 为跟随片源模式，不进行任何缩放，支持最高 8K 分辨率，video.scale_mode、video.scale_width、video.scale_height、video.scale_short、video.scale_long 均无效；1 为长短边限制模式，激活 video.scale_short 和 video.scale_long，可设置长边或短边，另一边按原比例缩放，支持最高 4K 分辨率；2 为宽高限制模式，激活 video.scale_width 和 video.scale_height，可设置宽度或高度，另一边按原比例缩放，支持最高 4K 分辨率。 |
| `video.scale_width` | - | integer | 否 | - | 最小值: 0；最大值: 4320 | 目标宽度，单位 px，可省略，支持 0 至 4320；仅在 video.scale_type=2 时生效，只传宽或高之一时，另一边按比例缩放。 |
| `video_url` | `--video-url` | string | 是 | - | - | 待转码视频的 URL，支持本地文件路径和公网 HTTP/HTTPS URL 两种输入协议；支持 mp4、mov、mkv、flv、ts、avi、wmv 等主流视频格式。 |

### 返回结果

| 字段路径 | 类型 | 必含 | 模式 | 说明 |
| --- | --- | --- | --- | --- |
| `request_id` | string | 否 | Cloud | 请求标识；仅在后端返回时出现。 |
| `task_id` | string | 是 | Cloud | 异步任务的唯一标识，用于查询任务状态并获取最终结果。 |
| `task_type` | string | 否 | Cloud | 任务类型；仅在后端实际返回非空值时出现。 |
| `duration` | number | 否 | Cloud 终态 | 视频时长，单位秒。 |
| `resolution` | string | 否 | Cloud 终态 | 转码后视频分辨率，支持 240p、360p、480p、540p、720p、1080p、2k、4k。 |
| `video_codec` | string | 否 | Cloud 终态 | 视频编码格式，例如 h264 或 h265。 |
| `video_url` | string | 否 | Cloud 终态 | 输出视频地址。返回有效期 24 小时的 HTTPS 临时下载链接，需要及时下载保存。 |

Cloud 调用成功后读取 `task_id`，再查询终态结果：

```bash
mediakit-cli shared query-task --task-id <task_id> --poll-complete
```

### 机器合同

以下命令只读取本模式的实时 help/schema，不发起业务调用：

```bash
mediakit-cli video martencode-video --help
mediakit-cli video martencode-video --schema
```
