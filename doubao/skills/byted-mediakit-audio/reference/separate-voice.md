# 人声背景音分离

## 能力用途

从音频或视频中分离人声与其他声音：通用或音乐场景输出人声和背景音两轨，短剧或口播场景可进一步输出人声、音乐和音效三轨，便于剪辑、二次创作、人声优化、语音识别或声音复刻。
## 参数填写规则

- 可选参数仅在用户明确指定，或可从用户意图准确确定时填写；不得伪造。不能准确确定时省略，确为正确完成任务所必需时先向用户澄清。

- 用户未点名格式时省略 output_format/format；用源容器或扩展名去填属于编造。用户点名了文档中的格式时即使等于默认值也要显式传递。调用成功或已被拦截后，不得再用编造的格式重试同一工具。
## Cloud

#### 人声与背景音分离场景选择

`scene` 支持以下四种场景；未指定时默认使用 `Audio`。

| 场景 | 输出音轨 | 分离策略与适用内容 |
| --- | --- | --- |
| `Audio`（通用提取） | 人声、背景音，共 2 轨 | 提取音频中的全部人声，涵盖说话、唱歌等类型。先尽可能完整地分离人声，再通过相减计算背景音轨，是最常用的模式。用户只需去掉人声、保留背景音乐或全部背景声（包括原有音效）、不要求将音乐与音效拆开时使用此场景，读取 `background_audio_url`。若明确需要将音乐和音效分别处理，口播切换到 `Narrate`，短剧切换到 `Drama`；歌曲的人声与伴奏分离切换到 `Music`。 |
| `Narrate`（口播） | 人声、音乐、音效，共 3 轨 | 优先保证人声提取完整度，因此音乐轨和音效轨中可能轻微残留人声。适合清晰人声口播类内容，有单独分离音效轨道需求时适用。仅当用户明确需要将口播中的音乐与音效分别处理时使用此场景，分别读取 `music_audio_url` 与 `sfx_audio_url`。若只需去掉人声、保留 BGM 或全部背景声，不要求拆分音乐与音效，切换到 `Audio`；短剧内容切换到 `Drama`，歌曲切换到 `Music`。 |
| `Music`（音乐） | 唱歌人声、伴奏音，共 2 轨 | 两轨均衡提取，专为歌曲场景调优，仅适用于音乐类内容。用于歌曲的人声与伴奏分离，读取 `voice_audio_url` 与 `background_audio_url`。非音乐内容不要使用此场景；只需去掉人声并保留整体背景声时切换到 `Audio`；口播或短剧中明确需要将音乐和音效分别处理时，分别切换到 `Narrate` 或 `Drama`。 |
| `Drama`（剧集） | 人声、音乐、音效，共 3 轨 | 优先保证人声提取完整度，音乐轨和音效轨之间可能存在轻微交叉泄漏。适合短剧、剧集类视频场景。仅当短剧内容需要将人声、音乐和音效分别处理时使用此场景，分别读取 `voice_audio_url`、`music_audio_url` 与 `sfx_audio_url`。若只需去掉人声、保留 BGM 或全部背景声，不要求拆分音乐与音效，切换到 `Audio`；清晰口播且需要单独音效轨时切换到 `Narrate`；歌曲切换到 `Music`。 |

`Audio`、`Music` 的两轨对应 `voice_audio_url`、`background_audio_url`；`Drama`、`Narrate` 的三轨对应 `voice_audio_url`、`music_audio_url`、`sfx_audio_url`。`Music` 中的 `background_audio_url` 为伴奏音轨。

### 命令与生命周期

- 命令：`mediakit-cli audio separate-voice`
- 生命周期：异步
- 返回方式：返回 `task_id`，再查询终态结果。

### 参数

| 参数路径 | CLI flag | 类型 | 必填 | 默认值 | 枚举/范围/结构 | 说明 |
| --- | --- | --- | --- | --- | --- | --- |
| `audio_url` | `--audio-url` | string | 条件必填（video_url 或 audio_url） | - | - | 音频地址，支持本地文件路径和公网 HTTP/HTTPS URL；支持 mp3、m4a、wav 等主流音频格式。 |
| `client_token` | `--client-token` | string | 否 | - | - | 用户请求凭证，用于幂等控制；大小写敏感，长度不超过 64 个 ASCII 可打印字符。 用于控制异步任务幂等；同步任务不支持幂等校验。异步任务首次提交时默认不传，服务端仍会对相同核心参数执行 24 小时默认幂等。用户明确指定 token 时原样使用。因网络超时、响应丢失等原因重试同一次提交时，原请求有 token 则复用原值，原请求未传则继续不传。任务已有结果后，用户要求“结果不对，重试”“重新跑一次”或“重新发起任务”时，必须生成并传递新的 token，避免返回原任务。新对话中用户要求“重新发起任务”时，若当前上下文具备完整任务参数，直接生成新 token 并提交；若参数不足，先向用户澄清，补齐后再使用新 token 发起，不得直接省略 token。新任务后续发生提交重试时复用该新 token。已有 task_id 且任务尚未完成时，只查询原任务，不得重新提交。CLI runtime 不判断用户意图，也不自动生成 token。 |
| `output_format` | `--output-format` | string | 否 | "mp3" | 枚举: ["aac","mp3","wav","m4a","flac"] | output_format 可选，用于指定分离后音频（包含 voice_audio_url 与 background_audio_url 文件）的输出格式；默认输出 MP3 格式，即 mp3；也可以指定为 aac、wav、m4a 或 flac。 |
| `video_url` | `--video-url` | string | 条件必填（video_url 或 audio_url） | - | - | 视频地址，支持本地文件路径和公网 HTTP/HTTPS URL 两种输入协议；支持 mp4、flv、ts、avi、mov、wmv、mkv 等主流视频格式；必须提供 video_url 或 audio_url 其中之一。 |
| `scene` | `--scene` | string | 否 | "Audio" | 枚举: ["Audio","Drama","Music","Narrate"] | 分离场景，用于针对不同内容类型选择更合适的分离策略。可选值：Audio：（默认）通用场景。输出人声/背景音 2 轨。Music：音乐场景。输出人声/背景音 2 轨。Drama：短剧场景。输出人声/音乐/音效 3 轨。Narrate：口播场景。输出人声/音乐/音效 3 轨。 |

### 参数关系

- 顶层参数必须满足：条件必填（video_url 或 audio_url）。

### 调用示例

```bash
mediakit-cli audio separate-voice
```

仅使用用户真实输入替换占位符；可选 flag 遵守参数填写规则，不得编造 URL、文件、枚举或业务参数。

### 返回结果

| 字段路径 | 类型 | 必含 | 模式 | 说明 |
| --- | --- | --- | --- | --- |
| `request_id` | string | 否 | Cloud | 请求标识；仅在后端返回时出现。 |
| `task_id` | string | 是 | Cloud | 异步任务的唯一标识，用于查询任务状态并获取最终结果。 |
| `task_type` | string | 否 | Cloud | 任务类型；仅在后端实际返回非空值时出现。 |
| `background_audio_url` | string | 否 | Cloud 终态 | 分离出的背景音音轨文件地址。 |
| `duration` | number | 否 | Cloud 终态 | 输入视频或音频总时长，单位为秒。 |
| `voice_audio_url` | string | 否 | Cloud 终态 | 分离出的人声音轨文件地址。 |
| `music_audio_url` | string | 否 | Cloud 终态 | 分离出的音乐音轨文件地址。 |
| `sfx_audio_url` | string | 否 | Cloud 终态 | 分离出的音效音轨文件地址。 |

Cloud 调用成功后读取 `task_id`，再查询终态结果：

```bash
mediakit-cli shared query-task --task-id <task_id> --poll-complete
```

### 机器合同

以下命令只读取本模式的实时 help/schema，不发起业务调用：

```bash
mediakit-cli audio separate-voice --help
mediakit-cli audio separate-voice --schema
```
