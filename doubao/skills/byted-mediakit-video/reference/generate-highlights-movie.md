# 高光智剪-影视拆条

## 能力用途

支持面向电影、电视剧等长视频内容，按剧情故事线识别高光并拆分成多段指定时长的高光片段，用于影视合集分发的短视频素材；算法会识别并去除景色铺垫、缓慢运镜、片头片尾曲等低密度信息；每段拆条带有高光前置开场与结尾钩子设计。

## 参数填写规则

- 可选参数仅在用户明确指定，或可从用户意图准确确定时填写；不得伪造。不能准确确定时省略，确为正确完成任务所必需时先向用户澄清。
## Cloud

### 命令与生命周期

- 命令：`mediakit-cli video generate-highlights-movie`
- 生命周期：异步
- 返回方式：返回 `task_id`，再查询终态结果。

### 使用指南


- `{}` 和 `[{}]` 仅展示 JSON 容器形状。命令模板中的 `<参数名_json>` 必须替换为符合参数表、已补齐必填字段的合法 JSON；不得直接提交空容器或占位符。
- 布尔参数（`--enable-generate-video`）只能写成 `--enable-generate-video=true` 或 `--enable-generate-video=false`，也可用裸 `--enable-generate-video`（等价 true）；禁止空格传值 `--enable-generate-video true`，否则该值会被当作位置参数。
- 布尔参数取默认值时直接省略，不要显式重复默认值。
- 对象或对象数组参数（`--highlight-cuts-param`、`--opening-hook-param`）需传合法 JSON 字符串；字段名与层级必须与上表“枚举/范围/结构”及子字段说明一致。不要用逗号分隔或裸文本。
- POSIX / bash：用单引号整体包裹，例如 `--highlight-cuts-param '{}'`。
- Windows PowerShell：按共享入口 [JSON 参数传参](../../byted-mediakit-shared/SKILL.md) 把 JSON flag 放在 `--%` 之后，内部双引号写成 `\"`，例如 `--% --highlight-cuts-param "{}"`。Windows 内联 JSON 禁止单引号 JSON 和 `$json` 变量；`@文件`、stdin `-`、`file://` 写法按共享入口 [JSON 参数传参](../../byted-mediakit-shared/SKILL.md) 执行。

### 调用示例

```bash
mediakit-cli video generate-highlights-movie \
  --video-url <video_url>
```

仅使用用户真实输入替换占位符；可选 flag 遵守参数填写规则，不得编造 URL、文件、枚举或业务参数。

### 参数

| 参数路径 | CLI flag | 类型 | 必填 | 默认值 | 枚举/范围/结构 | 说明 |
| --- | --- | --- | --- | --- | --- | --- |
| `client_token` | `--client-token` | string | 否 | - | - | 用户请求凭证，用于幂等控制；大小写敏感，长度不超过 64 个 ASCII 可打印字符。 用于控制异步任务幂等；同步任务不支持幂等校验。异步任务首次提交时默认不传，服务端仍会对相同核心参数执行 24 小时默认幂等。用户明确指定 token 时原样使用。因网络超时、响应丢失等原因重试同一次提交时，原请求有 token 则复用原值，原请求未传则继续不传。任务已有结果后，用户要求“结果不对，重试”“重新跑一次”或“重新发起任务”时，必须生成并传递新的 token，避免返回原任务。新对话中用户要求“重新发起任务”时，若当前上下文具备完整任务参数，直接生成新 token 并提交；若参数不足，先向用户澄清，补齐后再使用新 token 发起，不得直接省略 token。新任务后续发生提交重试时复用该新 token。已有 task_id 且任务尚未完成时，只查询原任务，不得重新提交。CLI runtime 不判断用户意图，也不自动生成 token。 |
| `enable_generate_video` | `--enable-generate-video` | boolean | 否 | true | - | enable_generate_video 默认值为 true；为 true 时生成拆条视频文件，并在结果中返回 video_urls；为 false 时仅输出时间戳、评分、标题等片段元信息，不生成视频文件，可用于自定义二次剪辑。 |
| `highlight_cuts_param` | `--highlight-cuts-param` | object | 否 | - | - | highlight_cuts_param 控制每段拆条的目标时长范围以及是否返回详细片段时间线信息；留空时默认生成 90\-180 秒的拆条片段。 |
| `highlight_cuts_param.enable_detailed_info` | - | boolean | 否 | false | - | enable_detailed_info 默认值为 false；控制是否在 clips 中输出每段拆条的片段类型、评分及原始视频和拆条视频中的起止时间等详细信息。 |
| `highlight_cuts_param.max_duration` | - | number | 否 | 180 | 最小值: 1；最大值: 600 | max_duration 表示单个拆条片段的最大时长，单位为秒；默认值为 180 秒；范围为 1 到 600；建议不超过 180 秒（3 分钟）以贴合短视频平台分发节奏。 |
| `highlight_cuts_param.min_duration` | - | number | 否 | 90 | 最小值: 1；最大值: 600 | min_duration 表示单个拆条片段的最短时长，单位为秒；默认值为 90 秒；范围为 1 到 600。 |
| `opening_hook_param` | `--opening-hook-param` | object | 否 | - | - | opening_hook_param 控制是否在每个拆条片段开头拼接最精彩的钩子片段；留空时默认添加 5\-15 秒的高光前置。 |
| `opening_hook_param.is_enabled` | - | boolean | 否 | true | - | is_enabled 默认值为 true；为 true 时系统自动提取最精彩片段置于拆条视频开头；为 false 时按原始剧情顺序输出拆条视频。 |
| `opening_hook_param.max_duration` | - | number | 否 | 15 | 最小值: 0；最大值: 60 | opening_hook_param.max_duration 默认值为 15 秒，范围为 0 到 60。 |
| `opening_hook_param.min_clip_duration` | - | number | 否 | 5 | 最小值: 0；最大值: 60 | min_clip_duration 是构成高光前置的单个片段最短时长，用于避免碎片过多造成频闪；默认值为 5；范围为 0 到 60。 |
| `opening_hook_param.min_duration` | - | number | 否 | 5 | 最小值: 0；最大值: 60 | opening_hook_param.min_duration 默认值为 5 秒，范围为 0 到 60。 |
| `opening_hook_param.min_score` | - | number | 否 | 4 | 最小值: 0；最大值: 5 | min_score 是筛选高光前置片段的最低评分，数值越高表示筛选标准越严格；默认值为 4；范围为 0 到 5。 |
| `video_url` | `--video-url` | string | 是 | - | - | video_url 是待处理的影视视频源 URL；支持本地文件路径和公网 HTTP/HTTPS URL 两种输入协议；支持 mp4、flv、ts、avi、mov、wmv、mkv 等主流视频格式；单次任务仅支持单个视频文件；输入视频最高支持 1080p 分辨率，时长不得超过 180 分钟，必须同时包含视频流和音频流；输入更适合电影，也适用于电视剧等长视频内容，不建议用于纯综艺、纪录片、广告或纯 BGM 视频；建议音频轨道包含清晰可识别的中文对话文本，以帮助算法准确理解剧情逻辑。 |

### 参数关系

- `highlight_cuts_param` 在 enable_generate_video=False 时必填。

### 返回结果

| 字段路径 | 类型 | 必含 | 模式 | 说明 |
| --- | --- | --- | --- | --- |
| `request_id` | string | 否 | Cloud | 请求标识；仅在后端返回时出现。 |
| `task_id` | string | 是 | Cloud | 异步任务的唯一标识，用于查询任务状态并获取最终结果。 |
| `task_type` | string | 否 | Cloud | 任务类型；仅在后端实际返回非空值时出现。 |
| `input_duration` | number | 否 | Cloud 终态 | input_duration 是输入视频总时长，单位为秒。 |
| `result_cuts_info` | array<object> | 否 | Cloud 终态 | result_cuts_info 的条目顺序与 video_urls 一致。 |
| `result_cuts_info[].clips` | array<object> | 否 | Cloud 终态 | clips 仅在 highlight_cuts_param.enable_detailed_info 为 true 时返回。 |
| `result_cuts_info[].clips[].cut_end_time` | number / null | 否 | Cloud 终态 | cut_end_time 是片段在最终拆条视频中的结束时间点，单位为秒。 |
| `result_cuts_info[].clips[].cut_start_time` | number / null | 否 | Cloud 终态 | cut_start_time 是片段在最终拆条视频中的起始时间点，单位为秒。 |
| `result_cuts_info[].clips[].score` | number / null | 否 | Cloud 终态 | score 是片段高光评分，范围为 [1, 5]。 |
| `result_cuts_info[].clips[].source_end_time` | number / null | 否 | Cloud 终态 | source_end_time 是片段在原始视频中的结束时间点，单位为秒。 |
| `result_cuts_info[].clips[].source_start_time` | number / null | 否 | Cloud 终态 | source_start_time 是片段在原始视频中的起始时间点，单位为秒。 |
| `result_cuts_info[].clips[].type` | string | 否 | Cloud 终态 | type 表示片段类型：OpeningHook（高光前置）或 HighlightClip（高光主体）。 |
| `result_cuts_info[].duration` | number / null | 否 | Cloud 终态 | duration 是拆条视频实际时长，单位为秒。 |
| `result_cuts_info[].size` | integer / string / null | 否 | Cloud 终态 | size 是拆条视频文件大小，单位为字节。 |
| `result_cuts_info[].title` | string | 否 | Cloud 终态 | title 是算法基于剧情自动生成的片段标题或内容简述。 |
| `result_cuts_info[].video_url` | string | 否 | Cloud 终态 | video_url 是该拆条片段对应的视频地址；未生成视频时 video_url 为空字符串；video_url 的有效期为 24 小时，需及时保存。 |
| `video_urls` | array<string> | 否 | Cloud 终态 | enable_generate_video 为 false 或算法未成功生成视频时，video_urls 为空。 返回有效期为 24 小时的 HTTPS 临时下载链接； |

Cloud 调用成功后读取 `task_id`，再查询终态结果：

```bash
mediakit-cli shared query-task --task-id <task_id> --poll-complete
```

### 机器合同

以下命令只读取本模式的实时 help/schema，不发起业务调用：

```bash
mediakit-cli video generate-highlights-movie --help
mediakit-cli video generate-highlights-movie --schema
```
