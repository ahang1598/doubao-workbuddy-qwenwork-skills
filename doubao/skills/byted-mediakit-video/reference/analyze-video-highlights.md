# 高光片段提取

## 能力用途

支持短剧 Miniseries 和小游戏 Game 两种分析模型，用于高光片段提取，并输出精准时间戳、高光打分、OCR 文本和画面描述，供二次开发或内容分析。

## 参数填写规则

- 可选参数仅在用户明确指定，或可从用户意图准确确定时填写；不得伪造。不能准确确定时省略，确为正确完成任务所必需时先向用户澄清。
## Cloud

### 命令与生命周期

- 命令：`mediakit-cli video analyze-video-highlights`
- 生命周期：异步
- 返回方式：返回 `task_id`，再查询终态结果。

### 使用指南


- `{}` 和 `[{}]` 仅展示 JSON 容器形状。命令模板中的 `<参数名_json>` 必须替换为符合参数表、已补齐必填字段的合法 JSON；不得直接提交空容器或占位符。
- 数组参数（`--video-urls`）传多个值时用逗号分隔并整体加引号，例如 `--video-urls "url1,url2"`。
- 单个值中的文件名或 URL 不能包含逗号（`,`），否则会被 CLI 当成多个元素拆开。遇到这种情况时，先向用户澄清，请其提供不含逗号的文件名或对应 URL 后再调用。
- 对象或对象数组参数（`--minigame-info`）需传合法 JSON 字符串；字段名与层级必须与上表“枚举/范围/结构”及子字段说明一致。不要用逗号分隔或裸文本。
- POSIX / bash：用单引号整体包裹，例如 `--minigame-info '{}'`。
- Windows PowerShell：按共享入口 [JSON 参数传参](../../byted-mediakit-shared/SKILL.md) 把 JSON flag 放在 `--%` 之后，内部双引号写成 `\"`，例如 `--% --minigame-info "{}"`。Windows 内联 JSON 禁止单引号 JSON 和 `$json` 变量；`@文件`、stdin `-`、`file://` 写法按共享入口 [JSON 参数传参](../../byted-mediakit-shared/SKILL.md) 执行。

### 调用示例

```bash
mediakit-cli video analyze-video-highlights \
  --video-urls "url1,url2" \
  --model <model> \
  --mode <mode>
```

仅使用用户真实输入替换占位符；可选 flag 遵守参数填写规则，不得编造 URL、文件、枚举或业务参数。

### 参数

| 参数路径 | CLI flag | 类型 | 必填 | 默认值 | 枚举/范围/结构 | 说明 |
| --- | --- | --- | --- | --- | --- | --- |
| `client_token` | `--client-token` | string | 否 | - | - | 用户请求凭证，用于幂等控制；大小写敏感，长度不超过 64 个 ASCII 可打印字符。 用于控制异步任务幂等；同步任务不支持幂等校验。异步任务首次提交时默认不传，服务端仍会对相同核心参数执行 24 小时默认幂等。用户明确指定 token 时原样使用。因网络超时、响应丢失等原因重试同一次提交时，原请求有 token 则复用原值，原请求未传则继续不传。任务已有结果后，用户要求“结果不对，重试”“重新跑一次”或“重新发起任务”时，必须生成并传递新的 token，避免返回原任务。新对话中用户要求“重新发起任务”时，若当前上下文具备完整任务参数，直接生成新 token 并提交；若参数不足，先向用户澄清，补齐后再使用新 token 发起，不得直接省略 token。新任务后续发生提交重试时复用该新 token。已有 task_id 且任务尚未完成时，只查询原任务，不得重新提交。CLI runtime 不判断用户意图，也不自动生成 token。 |
| `minigame_info` | `--minigame-info` | object | 否 | - | - | 仅当 model 为 Game 时可选填，用于提供小游戏描述信息以辅助模型更精准地识别高光内容。 |
| `minigame_info.highlight_definition` | - | string | 否 | - | 最长长度: 5000 | 描述游戏中的高光时刻或精彩瞬间的定义。 |
| `minigame_info.name` | - | string | 否 | - | 最长长度: 5000 | 用于标识游戏内容的游戏名称。 |
| `minigame_info.play_definition` | - | string | 否 | - | 最长长度: 5000 | 描述游戏的玩法规则或核心特点。 |
| `mode` | `--mode` | string | 是 | - | 枚举: ["StorylineCuts","HighlightExtract"] | 当 model 为 Miniseries 时，mode 必须为 StorylineCuts；当 model 为 Game 时，mode 必须为 HighlightExtract。 |
| `model` | `--model` | string | 是 | - | 枚举: ["Miniseries","Game"] | Miniseries 是短剧模型，结合故事线理解，智能识别钩子点、反转、亲密、冲突等高光片段；Game 是小游戏模型，精准识别玩法操作片段和击杀、连胜、满血反杀等高光瞬间。 |
| `video_urls` | `--video-urls` | array<string> | 是 | - | 最少项数: 1；最多项数: 100 | 待分析的视频 URL 列表，不同模型对输入视频的数量、时长和内容有不同要求。支持本地文件路径和公网 HTTP/HTTPS URL 两种输入协议；支持 mp4、flv、ts、avi、mov、wmv、mkv 等主流视频格式；输入分辨率最高支持 1080p。用于短剧高光片段提取时，单次任务最多支持输入 30 个视频文件，累计总时长建议不超过 45 分钟，输入素材必须同时包含视频流和音频流，视频画面下半部分垂直位置 0.5-1.0 范围内必须包含清晰居中的中文字幕，音频轨道必须包含清晰可识别的中文对话文本；仅含 BGM（含歌词）、纯音乐、语气词或无有效语义的声音将无法准确识别剧情逻辑。用于小游戏高光片段提取时，当前单次任务仅支持输入单个视频文件；输入多个视频时默认选择第一个文件分析，输入文件时长不得超过 10 分钟。 |

### 参数关系

- `mode` 在 model=Miniseries 时必填。
- `mode` 在 model=Game 时必填。

### 返回结果

| 字段路径 | 类型 | 必含 | 模式 | 说明 |
| --- | --- | --- | --- | --- |
| `request_id` | string | 否 | Cloud | 请求标识；仅在后端返回时出现。 |
| `task_id` | string | 是 | Cloud | 异步任务的唯一标识，用于查询任务状态并获取最终结果。 |
| `task_type` | string | 否 | Cloud | 任务类型；仅在后端实际返回非空值时出现。 |
| `duration` | number | 否 | Cloud 终态 | 输入视频的总时长，单位为秒。 |
| `highlight_info` | array<object> | 否 | Cloud 终态 | 高光片段元数据列表。 |
| `highlight_info[].description` | string | 否 | Cloud 终态 | 算法生成的该片段画面描述信息。 |
| `highlight_info[].end_time` | number | 否 | Cloud 终态 | 片段在原始视频中的结束时间，单位为秒。 |
| `highlight_info[].ocr` | string | 否 | Cloud 终态 | 识别出的画面中的字幕或文字内容。 |
| `highlight_info[].score` | number | 否 | Cloud 终态 | 高光分数范围为 1 到 5，分数越高代表片段越精彩。 |
| `highlight_info[].source_video_index` | integer | 否 | Cloud 终态 | 该片段在输入视频列表中的来源索引位置，从 0 开始。 |
| `highlight_info[].start_time` | number | 否 | Cloud 终态 | 片段在原始视频中的起始时间，单位为秒。 |

Cloud 调用成功后读取 `task_id`，再查询终态结果：

```bash
mediakit-cli shared query-task --task-id <task_id> --poll-complete
```

### 机器合同

以下命令只读取本模式的实时 help/schema，不发起业务调用：

```bash
mediakit-cli video analyze-video-highlights --help
mediakit-cli video analyze-video-highlights --schema
```
