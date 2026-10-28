# 解说视频生成

## 能力用途

基于已完成的剧本还原任务，可使用自定义解说词或由 AI 自动生成解说词，生成带 AI 配音与解说字幕的营销或解说视频；可配置音色、字幕样式与原文字幕擦除。


## 参数填写规则

- 可选参数仅在用户明确指定，或可从用户意图准确确定时填写；不得伪造。不能准确确定时省略，确为正确完成任务所必需时先向用户澄清。
## 语义效果选项

### `erase_mode` 可选效果

| 语义名称 | 参数值 | 说明 |
| --- | --- | --- |
| 标准擦除 | `standard` | 平衡擦除效果和处理效率，可能残留轻微涂抹痕迹。 |

### `subtitle_config.font_type` 可选效果

| 语义名称 | 参数值 | 说明 |
| --- | --- | --- |
| 庞门正道标题体 | `pm_zhengdao` | 字幕字体：庞门正道标题体。 |
| 思源黑体 | `sy_black` | 字幕字体：思源黑体。 |

### `subtitle_config.typesetting` 可选效果

| 语义名称 | 参数值 | 说明 |
| --- | --- | --- |
| 横排 | `0` | 文字横向排列。 |
| 竖排 | `1` | 文字竖向排列。 |

## Cloud

### 命令与生命周期

- 命令：`mediakit-cli video drama-recap`
- 生命周期：异步
- 返回方式：返回 `task_id`，再查询终态结果。

### 使用指南


- `{}` 和 `[{}]` 仅展示 JSON 容器形状。命令模板中的 `<参数名_json>` 必须替换为符合参数表、已补齐必填字段的合法 JSON；不得直接提交空容器或占位符。
- `--drama-script-task-id` 必须来自已完成的剧本还原终态结果。若用户未提供：先调用 [drama-script.md](drama-script.md)，轮询至终态后读取 `drama_script_task_id`，再调用本工具；禁止猜测或伪造。
- 布尔参数（`--erase-subtitle`）只能写成 `--erase-subtitle=true` 或 `--erase-subtitle=false`，也可用裸 `--erase-subtitle`（等价 true）；禁止空格传值 `--erase-subtitle true`，否则该值会被当作位置参数。
- 布尔参数取默认值时直接省略，不要显式重复默认值。
- 对象或对象数组参数（`--drama-recap-config`、`--miniseries-edit`、`--speaker-config`、`--subtitle-config`）需传合法 JSON 字符串；字段名与层级必须与上表“枚举/范围/结构”及子字段说明一致。不要用逗号分隔或裸文本。
- POSIX / bash：用单引号整体包裹，例如 `--drama-recap-config '{}'`。
- Windows PowerShell：按共享入口 [JSON 参数传参](../../byted-mediakit-shared/SKILL.md) 把 JSON flag 放在 `--%` 之后，内部双引号写成 `\"`，例如 `--% --drama-recap-config "{}"`。Windows 内联 JSON 禁止单引号 JSON 和 `$json` 变量；`@文件`、stdin `-`、`file://` 写法按共享入口 [JSON 参数传参](../../byted-mediakit-shared/SKILL.md) 执行。

### 调用示例

```bash
mediakit-cli video drama-recap \
 --drama-script-task-id <drama_script_task_id>
```

仅使用用户真实输入替换占位符；可选 flag 遵守参数填写规则，不得编造 URL、文件、枚举或业务参数。

### 参数

| 参数路径 | CLI flag | 类型 | 必填 | 默认值 | 枚举/范围/结构 | 说明 |
| --- | --- | --- | --- | --- | --- | --- |
| `batch_count` | `--batch-count` | integer | 否 | 1 | 最小值: 1；最大值: 100 | 批量生成的解说视频数量，最大为 100，默认为 1，允许基于同一份输入一次性生成多个版本的解说视频。 |
| `client_token` | `--client-token` | string | 否 | - | - | 用户请求凭证，用于幂等控制；大小写敏感，长度不超过 64 个 ASCII 可打印字符。 用于控制异步任务幂等；同步任务不支持幂等校验。异步任务首次提交时默认不传，服务端仍会对相同核心参数执行 24 小时默认幂等。用户明确指定 token 时原样使用。因网络超时、响应丢失等原因重试同一次提交时，原请求有 token 则复用原值，原请求未传则继续不传。任务已有结果后，用户要求“结果不对，重试”“重新跑一次”或“重新发起任务”时，必须生成并传递新的 token，避免返回原任务。新对话中用户要求“重新发起任务”时，若当前上下文具备完整任务参数，直接生成新 token 并提交；若参数不足，先向用户澄清，补齐后再使用新 token 发起，不得直接省略 token。新任务后续发生提交重试时复用该新 token。已有 task_id 且任务尚未完成时，只查询原任务，不得重新提交。CLI runtime 不判断用户意图，也不自动生成 token。 |
| `drama_recap_config` | `--drama-recap-config` | object | 否 | - | - | 解说词配置，用于控制解说词的生成方式、风格、语速等核心创作参数。 |
| `drama_recap_config.auto_generate_recap` | - | boolean | 否 | false | - | 是否由 AI 自动生成解说词；true 时根据视频内容自动创作解说文案，false 时使用用户提供的文案，默认 false。 |
| `drama_recap_config.enable_repeat_match` | - | boolean | 否 | false | - | 是否允许解说词匹配重复的视频画面；true 为宽松匹配模式，允许视频片段被重复使用，可提升生成速度和成功率，但可能导致成片出现少量重复画面；false 为严格匹配模式，确保每个视频片段只被使用一次，成片重复度更低但耗时可能更长；默认 false。 |
| `drama_recap_config.pause_time` | - | integer | 否 | 120 | 最小值: 1；最大值: 1000 | AI 配音的句间停顿时长，单位为毫秒，范围为 [1, 1000]，默认 120；可以控制解说配音的节奏感，数值较大时停顿更明显、节奏更舒缓，数值较小时节奏更紧凑。 |
| `drama_recap_config.prefer_speed` | - | boolean | 否 | false | - | 是否优先保障生成速度；true 时使用更少的模型尝试次数，生成耗时更短；false 时生成结果整体更稳定，耗时较长；默认 false。 |
| `drama_recap_config.style` | - | string | 否 | - | 最长长度: 500 | AI 生成解说词的风格指令，仅在 auto_generate_recap 为 true 时生效。 |
| `drama_recap_config.text_length` | - | integer | 否 | - | 最小值: 1；最大值: 5000 | AI 生成解说词的期望长度（UTF-8 字符数），最大 5000；仅在 auto_generate_recap 为 true 时生效；为保证解说内容自然流畅，最终输出的文本长度可能不会严格等于期望长度，但会尽量趋近。 |
| `drama_recap_config.text_speed` | - | number | 否 | 1 | 最小值: 0.5；最大值: 2 | 期望的解说词语速，范围为 [0.5, 2.0]，默认 1.0（标准语速）；数值越大语速越快，推荐 1.2 或 1.3 以获得更好的听感。 |
| `drama_script_task_id` | `--drama-script-task-id` | string | 是 | - | 最短长度: 1 | 已成功完成的剧本还原任务的 task_id，取自剧本还原任务终态结果中的 drama_script_task_id；传入后系统参考该任务的剧本还原结果生成解说视频。用户未提供时不得编造，须先完成剧本还原再填入。 |
| `erase_mode` | `--erase-mode` | string | 否 | "standard" | 枚举: ["standard"] | 字幕擦除模式；仅当 erase_subtitle 为 true 时生效。默认 standard；standard 表示标准版字幕擦除，平衡擦除效果和处理效率，会残留轻微的涂抹痕迹。 |
| `erase_subtitle` | `--erase-subtitle` | boolean | 否 | false | - | 是否擦除原视频中的字幕；true 时移除原有字幕，false 时保留原有字幕，默认 false。 |
| `miniseries_edit` | `--miniseries-edit` | object | 否 | - | - | 仅竖屏的短剧三要素配置，使用预设视觉模板，为解说视频一键添加“短剧三要素”（剧名、角标、提示语）。 |
| `miniseries_edit.hint` | - | string | 否 | - | 最长长度: 20 | 短剧提示语，是画面左右两侧的一行文字；可以是概括视频核心冲突或亮点的引导性文字，也可以是“影视效果 请勿模仿 无不良价值观引导”的免责声明；不得超过 20 个字。 |
| `miniseries_edit.template` | - | string | 否 | - | 枚举: ["热门短剧1","热门短剧2","热门短剧3","热门短剧4","热门短剧5"] | “短剧三要素”视觉模板名称，不同模板决定剧名、角标、提示语的位置和样式；支持 热门短剧1、热门短剧2、热门短剧3、热门短剧4、热门短剧5。 |
| `miniseries_edit.title` | - | string | 否 | - | 最长长度: 15 | 短剧名称，会在解说视频画面上展示剧名，用于品牌识别和引导用户搜索；不得超过 15 个字。 |
| `recap_text` | `--recap-text` | string | 否 | - | 最长长度: 5000 | 用户自定义的解说词文本，最多 5000 字符；drama_recap_config.auto_generate_recap 为 true 时，不得传入 recap_text。 |
| `speaker_config` | `--speaker-config` | object | 否 | - | - | AI 配音配置。 |
| `speaker_config.voice_type` | - | string | 否 | "Yunxi" | 枚举: ["Yunxi","Yunjian","Yunfeng","Yunyi","Yunjie","Yunze","Yunye","Xiaoxiao","Xiaochen","Xiaohan","Xiaomo"] | 配音的音色名称，默认 Yunxi；支持预置音色 Yunxi、Yunjian、Yunfeng、Yunyi、Yunjie、Yunze、Yunye、Xiaoxiao、Xiaochen、Xiaohan、Xiaomo。 |
| `subtitle_config` | `--subtitle-config` | object | 否 | - | - | 解说字幕配置，用于自定义新生成的解说字幕的字体、位置、颜色等。 |
| `subtitle_config.align_type` | - | integer | 否 | 1 | - | 文本对齐方式，默认 1（居中）；横排时 0 表示左对齐、1 表示居中、2 表示右对齐；竖排时 1 表示居中、3 表示上对齐、4 表示下对齐。 |
| `subtitle_config.alpha` | - | number | 否 | 1 | 最小值: 0；最大值: 1 | 字幕字体透明度，范围为 [0, 1]，默认 1。 |
| `subtitle_config.background_border_size` | - | number | 否 | 0 | 最小值: 0 | 字幕背景边框大小，默认 0。 |
| `subtitle_config.background_color` | - | string | 否 | "#00000000" | - | 字幕背景颜色，RGBA 格式，默认 "#00000000"（透明）。 |
| `subtitle_config.border_color` | - | string | 否 | "#00000000" | - | 字幕描边颜色，RGBA 格式，默认 "#00000000"（透明）。 |
| `subtitle_config.border_width` | - | integer | 否 | - | 最小值: 1 | 字幕描边宽度，单位为 px。 |
| `subtitle_config.bottom_right_x` | - | integer | 否 | - | 最小值: 1 | 字幕矩形区域右下角的 X 坐标，单位为像素（px），需大于 top_left_x。 |
| `subtitle_config.bottom_right_y` | - | integer | 否 | - | 最小值: 1 | 字幕矩形区域右下角的 Y 坐标，单位为像素（px），需大于 top_left_y。 |
| `subtitle_config.disable_subtitle` | - | boolean | 否 | false | - | 是否不在生成的解说视频中添加新的解说字幕；false 时添加新的解说字幕，默认 false。 |
| `subtitle_config.font_color` | - | string | 否 | "#FFFFFFFF" | - | 字幕字体颜色，RGBA 格式，默认 "#FFFFFFFF"（白色）。 |
| `subtitle_config.font_size` | - | integer | 否 | - | 最小值: 1 | 字幕字体大小，单位为 px。 |
| `subtitle_config.font_type` | - | string | 否 | "sy_black" | 枚举: ["sy_black","pm_zhengdao"] | 字幕字体，默认 sy_black；支持 sy_black、pm_zhengdao。 |
| `subtitle_config.line_max_width` | - | number | 否 | 1 | 最小值: 0；最大值: 1 | 自动换行宽度占字幕区域的比例，范围为 [0, 1]，默认 1。 |
| `subtitle_config.top_left_x` | - | integer | 否 | - | 最小值: 0 | 字幕矩形区域左上角的 X 坐标，单位为像素（px）。 |
| `subtitle_config.top_left_y` | - | integer | 否 | - | 最小值: 0 | 字幕矩形区域左上角的 Y 坐标，单位为像素（px）。 |
| `subtitle_config.typesetting` | - | integer | 否 | 0 | 枚举: [0,1] | 文字排列方向，默认 0；0 表示横排，1 表示竖排。 |

### 返回结果

| 字段路径 | 类型 | 必含 | 模式 | 说明 |
| --- | --- | --- | --- | --- |
| `request_id` | string | 否 | Cloud | 请求标识；仅在后端返回时出现。 |
| `task_id` | string | 是 | Cloud | 异步任务的唯一标识，用于查询任务状态并获取最终结果。 |
| `task_type` | string | 否 | Cloud | 任务类型；仅在后端实际返回非空值时出现。 |
| `duration` | number / null | 否 | Cloud 终态 | 所有输出结束视频的总时长，单位为秒。 |
| `error` | object / null | 否 | Cloud 终态 | 任务失败时包含错误码和错误信息。 |
| `error.code` | string / null | 否 | Cloud 终态 | 失败时返回的错误码。 |
| `error.message` | string / null | 否 | Cloud 终态 | 失败时返回的错误信息。 |
| `failed_count` | integer / null | 否 | Cloud 终态 | 生成失败的视频数量。 |
| `success_count` | integer / null | 否 | Cloud 终态 | 成功生成的视频数量。 |
| `total_count` | integer / null | 否 | Cloud 终态 | 批量生成的总任务数。 |
| `video_url` | string / null | 否 | Cloud 终态 | 当 batch_count 为 1 时提供解说视频地址；返回 HTTPS 临时下载链接，有效期为 24 小时； |
| `video_urls` | array<string> | 否 | Cloud 终态 | 使用 batch_count 批量生成多个视频时，以数组形式提供所有视频的地址；返回 HTTPS 临时下载链接，有效期为 24 小时； |

Cloud 调用成功后读取 `task_id`，再查询终态结果：

```bash
mediakit-cli shared query-task --task-id <task_id> --poll-complete
```

### 机器合同

以下命令只读取本模式的实时 help/schema，不发起业务调用：

```bash
mediakit-cli video drama-recap --help
mediakit-cli video drama-recap --schema
```
