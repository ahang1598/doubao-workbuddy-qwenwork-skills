# 高光智剪-小游戏

## 能力用途

支持识别小游戏录屏视频中的核心玩法与高光事件，例如连击、通关、极限操作，并快速生成用于买量推广的视频素材。可选提供游戏名称、玩法描述和高光定义，辅助更精准地识别精彩内容。

## 参数填写规则

- 可选参数仅在用户明确指定，或可从用户意图准确确定时填写；不得伪造。不能准确确定时省略，确为正确完成任务所必需时先向用户澄清。
## Cloud

### 命令与生命周期

- 命令：`mediakit-cli video generate-highlights-minigame`
- 生命周期：异步
- 返回方式：返回 `task_id`，再查询终态结果。

### 使用指南


- `{}` 和 `[{}]` 仅展示 JSON 容器形状。命令模板中的 `<参数名_json>` 必须替换为符合参数表、已补齐必填字段的合法 JSON；不得直接提交空容器或占位符。
- 布尔参数（`--enable-generate-video`）只能写成 `--enable-generate-video=true` 或 `--enable-generate-video=false`，也可用裸 `--enable-generate-video`（等价 true）；禁止空格传值 `--enable-generate-video true`，否则该值会被当作位置参数。
- 布尔参数取默认值时直接省略，不要显式重复默认值。
- 数组参数（`--video-urls`）传多个值时用逗号分隔并整体加引号，例如 `--video-urls "url1,url2"`。
- 单个值中的文件名或 URL 不能包含逗号（`,`），否则会被 CLI 当成多个元素拆开。遇到这种情况时，先向用户澄清，请其提供不含逗号的文件名或对应 URL 后再调用。
- 对象或对象数组参数（`--minigame-info`）需传合法 JSON 字符串；字段名与层级必须与上表“枚举/范围/结构”及子字段说明一致。不要用逗号分隔或裸文本。
- POSIX / bash：用单引号整体包裹，例如 `--minigame-info '{}'`。
- Windows PowerShell：按共享入口 [JSON 参数传参](../../byted-mediakit-shared/SKILL.md) 把 JSON flag 放在 `--%` 之后，内部双引号写成 `\"`，例如 `--% --minigame-info "{}"`。Windows 内联 JSON 禁止单引号 JSON 和 `$json` 变量；`@文件`、stdin `-`、`file://` 写法按共享入口 [JSON 参数传参](../../byted-mediakit-shared/SKILL.md) 执行。

### 调用示例

```bash
mediakit-cli video generate-highlights-minigame \
  --video-urls "url1,url2"
```

仅使用用户真实输入替换占位符；可选 flag 遵守参数填写规则，不得编造 URL、文件、枚举或业务参数。

### 参数

| 参数路径 | CLI flag | 类型 | 必填 | 默认值 | 枚举/范围/结构 | 说明 |
| --- | --- | --- | --- | --- | --- | --- |
| `client_token` | `--client-token` | string | 否 | - | - | 用户请求凭证，用于幂等控制；大小写敏感，长度不超过 64 个 ASCII 可打印字符。 用于控制异步任务幂等；同步任务不支持幂等校验。异步任务首次提交时默认不传，服务端仍会对相同核心参数执行 24 小时默认幂等。用户明确指定 token 时原样使用。因网络超时、响应丢失等原因重试同一次提交时，原请求有 token 则复用原值，原请求未传则继续不传。任务已有结果后，用户要求“结果不对，重试”“重新跑一次”或“重新发起任务”时，必须生成并传递新的 token，避免返回原任务。新对话中用户要求“重新发起任务”时，若当前上下文具备完整任务参数，直接生成新 token 并提交；若参数不足，先向用户澄清，补齐后再使用新 token 发起，不得直接省略 token。新任务后续发生提交重试时复用该新 token。已有 task_id 且任务尚未完成时，只查询原任务，不得重新提交。CLI runtime 不判断用户意图，也不自动生成 token。 |
| `enable_generate_video` | `--enable-generate-video` | boolean | 否 | true | - | 控制是否生成高光混剪视频，默认 true。true 时生成并输出高光混剪视频；false 时不生成高光混剪视频。 |
| `minigame_info` | `--minigame-info` | object | 否 | - | - | 可选的小游戏描述信息，建议填写以辅助模型更精准地识别高光内容。 |
| `minigame_info.highlight_definition` | - | string | 否 | - | 最长长度: 5000 | 游戏高光时刻或精彩瞬间定义，例如一次消除多个方块或躲避所有障碍物通关。 |
| `minigame_info.name` | - | string | 否 | - | 最长长度: 5000 | 游戏名称，用于标识游戏内容。 |
| `minigame_info.play_definition` | - | string | 否 | - | 最长长度: 5000 | 游戏玩法规则或核心特点描述。 |
| `mode` | `--mode` | string | 否 | "HighlightExtract" | 枚举: ["HighlightExtract"] | 高光提取模式，当前版本固定为 HighlightExtract。 |
| `video_urls` | `--video-urls` | array<string> | 是 | - | 最少项数: 1；最多项数: 1 | 待处理小游戏视频 URL 列表。单次任务仅支持输入 1 个视频文件；支持本地文件路径和公网 HTTP/HTTPS URL 两种输入协议；支持 mp4、flv、ts、avi、mov、wmv、mkv 等主流视频格式；输入文件时长不得超过 10 分钟；输入分辨率最高支持 1080p。 支持、公网 HTTP/HTTPS URL 输入协议；支持 mp4、flv、ts、avi、mov、wmv、mkv 等主流视频格式；输入文件的时长不得超过 10 分钟；输入分辨率最高支持 1080p。 |

### 返回结果

| 字段路径 | 类型 | 必含 | 模式 | 说明 |
| --- | --- | --- | --- | --- |
| `request_id` | string | 否 | Cloud | 请求标识；仅在后端返回时出现。 |
| `task_id` | string | 是 | Cloud | 异步任务的唯一标识，用于查询任务状态并获取最终结果。 |
| `task_type` | string | 否 | Cloud | 任务类型；仅在后端实际返回非空值时出现。 |
| `duration` | number | 否 | Cloud 终态 | 输入视频总时长，单位为秒。 |
| `mixvideo_info` | array<object> | 否 | Cloud 终态 | 高光混剪视频信息列表，每项包含构成该混剪的高光片段。 |
| `mixvideo_info[].clips` | array<object> | 否 | Cloud 终态 | 构成当前混剪视频的高光片段对象列表。 |
| `mixvideo_info[].clips[].clip_type` | string | 否 | Cloud 终态 | 片段类型，HighlightClip 代表普通高光片段。 |
| `mixvideo_info[].clips[].cut_end_time` | number | 否 | Cloud 终态 | 片段在最终混剪视频中的结束时间，单位为秒。 |
| `mixvideo_info[].clips[].cut_start_time` | number | 否 | Cloud 终态 | 片段在最终混剪视频中的起始时间，单位为秒。 |
| `mixvideo_info[].clips[].score` | number | 否 | Cloud 终态 | 分数越高表示片段越精彩。 |
| `mixvideo_info[].clips[].source_end_time` | number | 否 | Cloud 终态 | 片段在原始视频中的结束时间，单位为秒。 |
| `mixvideo_info[].clips[].source_start_time` | number | 否 | Cloud 终态 | 片段在原始视频中的起始时间，单位为秒。 |
| `mixvideo_info[].clips[].source_video_index` | integer | 否 | Cloud 终态 | 该片段在输入视频列表中的来源索引位置；小游戏高光智剪仅支持输入单个视频，来源索引固定为 0。 |
| `mixvideo_info[].mixvideo_index` | integer | 否 | Cloud 终态 | 混剪视频索引，与 video_urls 的位置一一对应，并从 0 开始。 |
| `mixvideo_info[].video_url` | string | 否 | Cloud 终态 | 当前混剪信息项对应的混剪视频地址。enable_generate_video 为 false 时不返回；返回有效期为 24 小时的 HTTPS 临时下载链接； |
| `video_urls` | array<string> | 否 | Cloud 终态 | 最终生成的高光混剪视频地址列表。enable_generate_video 为 false 时不返回；返回有效期为 24 小时的 HTTPS 临时下载链接； |

Cloud 调用成功后读取 `task_id`，再查询终态结果：

```bash
mediakit-cli shared query-task --task-id <task_id> --poll-complete
```

### 机器合同

以下命令只读取本模式的实时 help/schema，不发起业务调用：

```bash
mediakit-cli video generate-highlights-minigame --help
mediakit-cli video generate-highlights-minigame --schema
```
