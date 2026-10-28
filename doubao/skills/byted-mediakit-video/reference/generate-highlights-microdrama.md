# 高光智剪-短剧

## 能力用途

可用于短剧高光智剪，基于输入剧集的角色和剧情故事线理解提取高光片段，并按时长、产出个数、顺剪或跳剪等要求生成高光混剪、单集预告等视频。

## 参数填写规则

- 可选参数仅在用户明确指定，或可从用户意图准确确定时填写；不得伪造。不能准确确定时省略，确为正确完成任务所必需时先向用户澄清。
## 语义效果选项

### `edit_param.mode` 可选效果

| 语义名称 | 参数值 | 说明 |
| --- | --- | --- |
| 基础剪辑 | `BasicEdit` | 不添加额外视觉元素。 |
| 模板剪辑 | `TemplateEdit` | 使用指定的短剧三要素视觉模板。 |

## Cloud

### 命令与生命周期

- 命令：`mediakit-cli video generate-highlights-microdrama`
- 生命周期：异步
- 返回方式：返回 `task_id`，再查询终态结果。

### 使用指南


- `{}` 和 `[{}]` 仅展示 JSON 容器形状。命令模板中的 `<参数名_json>` 必须替换为符合参数表、已补齐必填字段的合法 JSON；不得直接提交空容器或占位符。
- 布尔参数（`--enable-generate-video`、`--enable-return-poster`、`--enable-segment-tag`）只能写成 `--enable-generate-video=true` 或 `--enable-generate-video=false`，也可用裸 `--enable-generate-video`（等价 true）；禁止空格传值 `--enable-generate-video true`，否则该值会被当作位置参数。
- 布尔参数取默认值时直接省略，不要显式重复默认值。
- 数组参数（`--video-urls`）传多个值时用逗号分隔并整体加引号，例如 `--video-urls "url1,url2"`。
- 单个值中的文件名或 URL 不能包含逗号（`,`），否则会被 CLI 当成多个元素拆开。遇到这种情况时，先向用户澄清，请其提供不含逗号的文件名或对应 URL 后再调用。
- 对象或对象数组参数（`--edit-param`、`--highlight-cuts-param`、`--opening-hook-param`）需传合法 JSON 字符串；字段名与层级必须与上表“枚举/范围/结构”及子字段说明一致。不要用逗号分隔或裸文本。
- POSIX / bash：用单引号整体包裹，例如 `--edit-param '{}'`。
- Windows PowerShell：按共享入口 [JSON 参数传参](../../byted-mediakit-shared/SKILL.md) 把 JSON flag 放在 `--%` 之后，内部双引号写成 `\"`，例如 `--% --edit-param "{}"`。Windows 内联 JSON 禁止单引号 JSON 和 `$json` 变量；`@文件`、stdin `-`、`file://` 写法按共享入口 [JSON 参数传参](../../byted-mediakit-shared/SKILL.md) 执行。

### 调用示例

```bash
mediakit-cli video generate-highlights-microdrama \
  --video-urls "url1,url2"
```

仅使用用户真实输入替换占位符；可选 flag 遵守参数填写规则，不得编造 URL、文件、枚举或业务参数。

### 参数

| 参数路径 | CLI flag | 类型 | 必填 | 默认值 | 枚举/范围/结构 | 说明 |
| --- | --- | --- | --- | --- | --- | --- |
| `client_token` | `--client-token` | string | 否 | - | - | 用户请求凭证，用于幂等控制；大小写敏感，长度不超过 64 个 ASCII 可打印字符。 用于控制异步任务幂等；同步任务不支持幂等校验。异步任务首次提交时默认不传，服务端仍会对相同核心参数执行 24 小时默认幂等。用户明确指定 token 时原样使用。因网络超时、响应丢失等原因重试同一次提交时，原请求有 token 则复用原值，原请求未传则继续不传。任务已有结果后，用户要求“结果不对，重试”“重新跑一次”或“重新发起任务”时，必须生成并传递新的 token，避免返回原任务。新对话中用户要求“重新发起任务”时，若当前上下文具备完整任务参数，直接生成新 token 并提交；若参数不足，先向用户澄清，补齐后再使用新 token 发起，不得直接省略 token。新任务后续发生提交重试时复用该新 token。已有 task_id 且任务尚未完成时，只查询原任务，不得重新提交。CLI runtime 不判断用户意图，也不自动生成 token。 |
| `edit_param` | `--edit-param` | object | 否 | - | - | 高光视频剪辑配置用于控制最终输出视频的视觉风格；留空时默认使用基础剪辑模式。enable_generate_video 为 false 时，该配置将被忽略。 |
| `edit_param.mode` | - | string | 是 | "BasicEdit"（Schema 默认；仍需显式提供） | 枚举: ["BasicEdit","TemplateEdit"] | 成片剪辑模式决定是否使用视觉模板，默认为 BasicEdit；支持 BasicEdit 和 TemplateEdit。BasicEdit 表示基础剪辑，不添加额外视觉元素；TemplateEdit 表示模板剪辑，使用指定的短剧三要素视觉模板。 |
| `edit_param.template_edit` | - | object | 否 | - | - | 短剧模板剪辑参数不是无条件必选；当 mode 为 TemplateEdit 时必须填写。 |
| `edit_param.template_edit.hint` | - | string | 否 | - | 最长长度: 20 | 短剧提示语将显示在画面左侧或右侧，长度不得超过 20 个字符。 |
| `edit_param.template_edit.template` | - | string | 否 | "热门短剧1" | 枚举: ["热门短剧1","热门短剧2","热门短剧3","热门短剧4","热门短剧5"] | 短剧三要素视觉模板名称决定剧名、角标、提示语的样式和位置，默认为热门短剧1；支持 热门短剧1、热门短剧2、热门短剧3、热门短剧4、热门短剧5。 |
| `edit_param.template_edit.title` | - | string | 否 | - | 最长长度: 22 | 短剧名称将显示在视频画面中，长度不得超过 22 个字符。 |
| `enable_generate_video` | `--enable-generate-video` | boolean | 否 | true | - | 是否生成高光混剪视频，默认为 true。true 时生成并输出高光混剪视频；false 时不生成高光混剪视频，传入的 edit_param 将被忽略。 |
| `enable_return_poster` | `--enable-return-poster` | boolean | 否 | false | - | 是否在任务结果中返回混剪视频的封面图 URL，默认为 false。true 时返回混剪视频的封面图 URL；false 时不返回封面图。 |
| `enable_segment_tag` | `--enable-segment-tag` | boolean | 否 | - | - | 是否返回高光片段和分镜标签，默认为 false。true 时在 mixvideo_info.clips 与 storyboard_info 中额外返回 tags 字段；false 时不返回 tags 字段。 |
| `highlight_cuts_param` | `--highlight-cuts-param` | object | 否 | - | - | 高光智剪参数配置用于控制最终输出视频的时长与个数；留空时默认使用热门短剧1模板。 |
| `highlight_cuts_param.cut_mode` | - | string | 否 | "Mixed" | 枚举: ["Mixed","Sequential"] | 剪辑模式默认为 Mixed；支持 Mixed 和 Sequential。Mixed 表示混剪，打乱高光片段的原始顺序；Sequential 表示顺剪，保持高光片段的原始时间顺序。 |
| `highlight_cuts_param.enable_storyboard` | - | boolean | 否 | false | - | 控制是否在任务结果中输出详细的分镜信息 storyboard_info，默认为 false。 |
| `highlight_cuts_param.highlight_ending_prompt` | - | string | 否 | - | - | 高光混剪结尾钩子选取偏好，仅在 cut_mode 为 Mixed 的混剪模式下生效。 |
| `highlight_cuts_param.highlight_segment_prompt` | - | string | 否 | - | - | 高光片段选取偏好，仅在 cut_mode 为 Mixed 的混剪模式下生效。 |
| `highlight_cuts_param.highlight_start_prompt` | - | string | 否 | - | - | 高光混剪开头起播点选取偏好，仅在 cut_mode 为 Mixed 的混剪模式下生效。 |
| `highlight_cuts_param.max_duration` | - | number | 否 | 180 | - | 期望输出高光视频的最大时长，默认为 180。 |
| `highlight_cuts_param.max_number` | - | integer | 否 | 6 | - | 最多输出的高光视频数量，默认为 6。 |
| `highlight_cuts_param.min_duration` | - | number | 否 | 30 | - | 期望输出高光视频的最小时长，默认为 30。 |
| `highlight_cuts_param.user_preferred_segments` | - | array<object> | 否 | - | - | 用户期望优先选用的原片内容或片段，支持填写多个，仅在 cut_mode 为 Mixed 的混剪模式下生效。 优先片段：仅含 episode 表示整集优先；含 start_time/end_time 表示该集指定时间区间优先 |
| `highlight_cuts_param.user_preferred_segments[].end_time` | - | number | 否 | - | - | 优先片段在该输入视频中的结束时间，单位为秒。 |
| `highlight_cuts_param.user_preferred_segments[].episode` | - | integer | 是 | - | 最小值: 0 | 优先选用的输入视频序号，从 0 开始计数；仅含该序号表示整集优先。 |
| `highlight_cuts_param.user_preferred_segments[].start_time` | - | number | 否 | - | - | 优先片段在该输入视频中的起始时间，单位为秒；与 end_time 一并提供时，表示该集指定时间区间优先。 |
| `mode` | `--mode` | string | 否 | "StorylineCuts" | 枚举: ["StorylineCuts"] | 当前版本固定为 StorylineCuts。 |
| `opening_hook_param` | `--opening-hook-param` | object | 否 | - | - | 精彩前置参数用于控制是否在视频开头添加一个极具吸引力的钩子片段来留住观众；留空时默认在视频开头添加精彩前置片段。 |
| `opening_hook_param.enable_opening_hook` | - | boolean | 否 | true | - | 是否启用精彩前置开场钩子，默认为 true。 |
| `opening_hook_param.max_duration` | - | number | 否 | 15 | - | 开场钩子片段的最大时长，默认为 15。 |
| `opening_hook_param.min_clip_duration` | - | number | 否 | 5 | - | 构成开场钩子的单个高光片段的最小持续时长，默认为 5。 |
| `opening_hook_param.min_duration` | - | number | 否 | 5 | - | 开场钩子片段的最小时长，默认为 5。 |
| `opening_hook_param.min_score` | - | number | 否 | 3 | - | 构成开场钩子的单个高光片段所需达到的最低高光分，范围为 [1, 5]，默认为 3。 |
| `opening_hook_param.opening_hook_prompt` | - | string | 否 | - | - | 精彩前置片段选取标准，用自然语言描述开头钩子的筛选偏好。 |
| `video_ending_mode` | `--video-ending-mode` | string | 否 | - | 枚举: ["ReuseMainEnding","SmartSelect"] | 视频结尾选取模式默认为 ReuseMainEnding；支持 ReuseMainEnding 和 SmartSelect。ReuseMainEnding 时优先复用正片剧集结尾；SmartSelect 时使用智能选取模式。 |
| `video_urls` | `--video-urls` | array<string> | 是 | - | 最少项数: 1；最多项数: 100 | 待处理的短剧原片视频 URL 列表。支持本地文件路径和公网 HTTP/HTTPS URL 两种输入协议；支持 mp4、flv、ts、avi、mov、wmv、mkv 等主流视频格式；输入分辨率最高支持 1080p。所有输入文件的累计总时长不得超过 45 分钟。输入素材必须同时包含视频流和音频流，视频画面下半部分必须包含清晰居中的中文字幕，音频轨道中必须包含清晰可识别的中文对话文本。 |

### 返回结果

| 字段路径 | 类型 | 必含 | 模式 | 说明 |
| --- | --- | --- | --- | --- |
| `request_id` | string | 否 | Cloud | 请求标识；仅在后端返回时出现。 |
| `task_id` | string | 是 | Cloud | 异步任务的唯一标识，用于查询任务状态并获取最终结果。 |
| `task_type` | string | 否 | Cloud | 任务类型；仅在后端实际返回非空值时出现。 |
| `duration` | number | 否 | Cloud 终态 | 输入视频的总时长，单位为秒。 |
| `mixvideo_info` | array<object> | 否 | Cloud 终态 | 高光片段的详细信息列表。 |
| `mixvideo_info[].clips` | array<object> | 否 | Cloud 终态 | 构成该混剪视频的高光片段列表。 |
| `mixvideo_info[].clips[].clip_type` | string | 否 | Cloud 终态 | 片段类型包括 HighlightClip 和 OpeningHook。HighlightClip 表示普通高光片段，OpeningHook 表示前置精彩片段。 |
| `mixvideo_info[].clips[].cut_end_time` | number | 否 | Cloud 终态 | 片段在最终混剪视频中的结束时间，单位为秒。 |
| `mixvideo_info[].clips[].cut_start_time` | number | 否 | Cloud 终态 | 片段在最终混剪视频中的起始时间，单位为秒。 |
| `mixvideo_info[].clips[].score` | number | 否 | Cloud 终态 | 高光分数，范围为 [1, 5]。 |
| `mixvideo_info[].clips[].source_end_time` | number | 否 | Cloud 终态 | 片段在原始视频中的结束时间，单位为秒。 |
| `mixvideo_info[].clips[].source_start_time` | number | 否 | Cloud 终态 | 片段在原始视频中的起始时间，单位为秒。 |
| `mixvideo_info[].clips[].source_video_index` | integer | 否 | Cloud 终态 | 片段来源于输入视频列表中的索引位置，从 0 开始。 |
| `mixvideo_info[].clips[].tags` | array<string> | 否 | Cloud 终态 | 高光片段的标签，仅当请求中 enable_segment_tag 为 true 时返回。 单个片段标签 |
| `mixvideo_info[].duration` | number | 否 | Cloud 终态 | 该混剪视频的时长，单位为秒。 |
| `mixvideo_info[].mixvideo_index` | integer | 否 | Cloud 终态 | 混剪视频的索引，与 video_urls 数组中的位置一一对应，从 0 开始。 |
| `mixvideo_info[].poster_url` | string | 否 | Cloud 终态 | 仅当请求中 enable_return_poster 为 true 且算法成功生成封面时返回。 |
| `mixvideo_info[].size` | integer | 否 | Cloud 终态 | 该混剪视频的文件大小，单位为字节。 |
| `mixvideo_info[].video_url` | string | 否 | Cloud 终态 | 返回一个 HTTPS 临时下载链接，有效期为 24 小时。如果 enable_generate_video 为 false 或底层未产生成片，则为空。 |
| `storyboard_info` | array<object> | 否 | Cloud 终态 | 仅当请求中 enable_storyboard 为 true 时返回。 |
| `storyboard_info[].description` | string | 否 | Cloud 终态 | 算法生成的画面描述信息。 |
| `storyboard_info[].end_time` | number | 否 | Cloud 终态 | 分镜在原始视频中的结束时间，单位为秒。 |
| `storyboard_info[].ocr` | string | 否 | Cloud 终态 | 识别出的画面字幕文本。 |
| `storyboard_info[].score` | number | 否 | Cloud 终态 | 分镜的高光分数，范围为 [1, 5]。 |
| `storyboard_info[].source_video_index` | integer | 否 | Cloud 终态 | 分镜来源于输入视频列表中的索引位置，从 0 开始。 |
| `storyboard_info[].start_time` | number | 否 | Cloud 终态 | 分镜在原始视频中的起始时间，单位为秒。 |
| `storyboard_info[].tags` | array<string> | 否 | Cloud 终态 | 分镜的标签，仅当请求中 enable_segment_tag 为 true 时返回。 单个分镜标签 |
| `video_urls` | array<string> | 否 | Cloud 终态 | 最终生成的混剪视频地址列表。返回 HTTPS 临时下载链接，有效期为 24 小时。 输出视频 URL |

Cloud 调用成功后读取 `task_id`，再查询终态结果：

```bash
mediakit-cli shared query-task --task-id <task_id> --poll-complete
```

### 机器合同

以下命令只读取本模式的实时 help/schema，不发起业务调用：

```bash
mediakit-cli video generate-highlights-microdrama --help
mediakit-cli video generate-highlights-microdrama --schema
```
