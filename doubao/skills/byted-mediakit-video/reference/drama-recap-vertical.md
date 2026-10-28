# 解说视频生成（短剧行业模型）

## 能力用途

基于输入短剧剧集的角色与剧情故事线理解，自动提取高光片段并生成全新解说视频；支持文字解说（原片高光混剪 + 屏幕文字）与旁白解说（原片高光混剪 + AI 语音 + BGM），并可套用短剧三要素视觉模板。


## 参数填写规则

- 可选参数仅在用户明确指定，或可从用户意图准确确定时填写；不得伪造。不能准确确定时省略，确为正确完成任务所必需时先向用户澄清。
## 语义效果选项

### `edit_param.mode` 可选效果

| 语义名称 | 参数值 | 说明 |
| --- | --- | --- |
| 基础剪辑 | `BasicEdit` | 仅拼接高光片段。 |
| 模板剪辑 | `TemplateEdit` | 在基础剪辑上套用短剧三要素视觉模板。 |

### `narrate_options.erase_subtitle_mode` 可选效果

| 语义名称 | 参数值 | 说明 |
| --- | --- | --- |
| 标准擦除 | `standard` | 平衡擦除效果与效率；复杂纹理或剧烈运动背景可能残留轻微涂抹痕迹。 |
| 马赛克遮挡 | `mosaic` | 以高斯模糊直接遮盖字幕区域，处理效率最高。 |

### `text_options.align_type` 可选效果

| 语义名称 | 参数值 | 说明 |
| --- | --- | --- |
| 右对齐 | `right` | 文字右对齐。 |
| 居中对齐 | `middle` | 文字居中对齐。 |
| 左对齐 | `left` | 文字左对齐。 |

### `text_options.font_type` 可选效果

| 语义名称 | 参数值 | 说明 |
| --- | --- | --- |
| 思源粗体 | `SY_Bold` | 思源粗体。 |
| 思源黑体 | `SY_Black` | 思源黑体。 |

## Cloud

### 命令与生命周期

- 命令：`mediakit-cli video drama-recap-vertical`
- 生命周期：异步
- 返回方式：返回 `task_id`，再查询终态结果。

### 使用指南


- `{}` 和 `[{}]` 仅展示 JSON 容器形状。命令模板中的 `<参数名_json>` 必须替换为符合参数表、已补齐必填字段的合法 JSON；不得直接提交空容器或占位符。
- 布尔参数（`--enable-return-poster`）只能写成 `--enable-return-poster=true` 或 `--enable-return-poster=false`，也可用裸 `--enable-return-poster`（等价 true）；禁止空格传值 `--enable-return-poster true`，否则该值会被当作位置参数。
- 布尔参数取默认值时直接省略，不要显式重复默认值。
- 数组参数（`--video-urls`）传多个值时用逗号分隔并整体加引号，例如 `--video-urls "url1,url2"`。
- 单个值中的文件名或 URL 不能包含逗号（`,`），否则会被 CLI 当成多个元素拆开。遇到这种情况时，先向用户澄清，请其提供不含逗号的文件名或对应 URL 后再调用。
- 对象或对象数组参数（`--edit-param`、`--narrate-options`、`--text-options`）需传合法 JSON 字符串；字段名与层级必须与上表“枚举/范围/结构”及子字段说明一致。不要用逗号分隔或裸文本。
- POSIX / bash：用单引号整体包裹，例如 `--edit-param '{}'`。
- Windows PowerShell：按共享入口 [JSON 参数传参](../../byted-mediakit-shared/SKILL.md) 把 JSON flag 放在 `--%` 之后，内部双引号写成 `\"`，例如 `--% --edit-param "{}"`。Windows 内联 JSON 禁止单引号 JSON 和 `$json` 变量；`@文件`、stdin `-`、`file://` 写法按共享入口 [JSON 参数传参](../../byted-mediakit-shared/SKILL.md) 执行。

### 调用示例

```bash
mediakit-cli video drama-recap-vertical \
  --video-urls "url1,url2"
```

仅使用用户真实输入替换占位符；可选 flag 遵守参数填写规则，不得编造 URL、文件、枚举或业务参数。

### 参数

| 参数路径 | CLI flag | 类型 | 必填 | 默认值 | 枚举/范围/结构 | 说明 |
| --- | --- | --- | --- | --- | --- | --- |
| `client_token` | `--client-token` | string | 否 | - | - | 用户请求凭证，用于幂等控制；大小写敏感，长度不超过 64 个 ASCII 可打印字符。 用于控制异步任务幂等；同步任务不支持幂等校验。异步任务首次提交时默认不传，服务端仍会对相同核心参数执行 24 小时默认幂等。用户明确指定 token 时原样使用。因网络超时、响应丢失等原因重试同一次提交时，原请求有 token 则复用原值，原请求未传则继续不传。任务已有结果后，用户要求“结果不对，重试”“重新跑一次”或“重新发起任务”时，必须生成并传递新的 token，避免返回原任务。新对话中用户要求“重新发起任务”时，若当前上下文具备完整任务参数，直接生成新 token 并提交；若参数不足，先向用户澄清，补齐后再使用新 token 发起，不得直接省略 token。新任务后续发生提交重试时复用该新 token。已有 task_id 且任务尚未完成时，只查询原任务，不得重新提交。CLI runtime 不判断用户意图，也不自动生成 token。 |
| `edit_param` | `--edit-param` | object | 否 | - | - | 支持在 narrate 和 text 两种模式中使用；可选配置成片剪辑效果，包括套用包含剧名、角标和提示语的短剧三要素视觉模板。 |
| `edit_param.mode` | - | string | 是 | "BasicEdit"（Schema 默认；仍需显式提供） | 枚举: ["BasicEdit","TemplateEdit"] | 默认为 BasicEdit；支持 BasicEdit 和 TemplateEdit，BasicEdit 仅拼接高光片段，TemplateEdit 在基础剪辑上套用短剧三要素视觉模板。 |
| `edit_param.template_edit` | - | object | 否 | - | - | 仅当 edit_param.mode 为 TemplateEdit 时生效。 |
| `edit_param.template_edit.hint` | - | string | 否 | - | 最长长度: 20 | 画面左右两侧的一行短剧提示语，可选用于概括核心冲突或亮点，也可用作免责声明；不得超过 20 个字。 |
| `edit_param.template_edit.template` | - | string | 否 | "热门短剧1" | 枚举: ["热门短剧1","热门短剧2","热门短剧3","热门短剧4","热门短剧5"] | 默认为 热门短剧1；决定剧名、角标和提示语的位置及样式；支持 热门短剧1、热门短剧2、热门短剧3、热门短剧4、热门短剧5。 |
| `edit_param.template_edit.title` | - | string | 否 | - | 最长长度: 22 | 展示在解说视频画面上的短剧名称，用于品牌识别和引导用户搜索；不得超过 22 个字。 |
| `enable_return_poster` | `--enable-return-poster` | boolean | 否 | false | - | 默认为 false；true 会在任务结果中返回 poster_url，false 不返回封面图。 |
| `max_count` | `--max-count` | integer | 否 | 3 | 最小值: 1；最大值: 100 | 单次任务期望生成的解说视频数量上限，最小值为 1，不得超过 100，默认为 3。 |
| `max_duration` | `--max-duration` | number | 否 | 180 | 最小值: 1；最大值: 7200 | 每个解说视频的时长上限，单位为秒，最小值为 1，最大值为 7200，默认为 180 秒。 |
| `min_duration` | `--min-duration` | number | 否 | 30 | 最小值: 1；最大值: 7200 | 每个解说视频的时长下限，单位为秒，最小值为 1，最大值为 7200，默认为 30 秒。 |
| `mode` | `--mode` | string | 否 | "text" | 枚举: ["narrate","text"] | 默认为 text；支持 narrate 和 text 两种模式。narrate 生成原片高光混剪、AI 语音解说和 BGM；text 生成原片高光混剪与屏幕文字解说。 |
| `narrate_bgm_url` | `--narrate-bgm-url` | string | 否 | - | - | 指定旁白解说模式下使用的背景音乐音频 URL；支持本地文件路径和公网 HTTP/HTTPS URL；支持 mp3、m4a、wav 等主流音频格式；可选，不传时生成的解说视频不添加背景音乐。 |
| `narrate_options` | `--narrate-options` | object | 否 | - | - | 仅当 mode 为 narrate 时生效。 |
| `narrate_options.enable_narrate_bgm` | - | boolean | 否 | true | - | 默认为 true；true 启用 BGM 并使用 narrate_bgm_url 指定的音频，false 关闭背景音乐。 |
| `narrate_options.erase_subtitle_mode` | - | string | 否 | "mosaic" | 枚举: ["mosaic","standard"] | 默认为 mosaic；支持 mosaic 和 standard。mosaic 直接高斯模糊遮盖字幕区域，处理效率最高，适合快速遮挡且画面完整性要求不高的场景；standard 平衡擦除效果与效率，对纯色或简单背景效果良好，但复杂纹理或剧烈运动背景可能残留轻微涂抹痕迹。 |
| `narrate_options.narrate_ratio` | - | number | 否 | 0.3 | 最小值: 0；最大值: 1 | 控制旁白解说时长占生成视频时长的比例，最小值为 0，最大值为 1，默认为 0.3，建议不超过 0.5。 |
| `opening_hook` | `--opening-hook` | string | 否 | "auto" | 枚举: ["auto","force","disable"] | 精彩片段前置策略默认为 auto；支持 auto、force 和 disable。auto 会智能判断是否将最精彩片段前置到视频开头，force 强制开启精彩前置，disable 关闭精彩前置。 |
| `text_options` | `--text-options` | object | 否 | - | - | 仅当 mode 为 text 时生效。 |
| `text_options.align_type` | - | string | 否 | "left" | 枚举: ["left","middle","right"] | 默认为 left；支持 left、middle、right，分别表示左对齐、居中对齐和右对齐。 |
| `text_options.border_color` | - | string | 否 | "#00000080" | 格式: "^#[0-9A-Fa-f]{8}$" | 花字描边颜色必须使用 #RRGGBBAA 格式，默认为 #00000080。 |
| `text_options.border_width` | - | integer | 否 | 2 | 最小值: 1 | 花字描边宽度单位为 px，默认为 2，建议不超过字号的 0.1 倍。 |
| `text_options.font_color` | - | string | 否 | "#FFFFF290" | 格式: "^#[0-9A-Fa-f]{8}$" | 花字颜色必须使用 #RRGGBBAA 格式，默认为 #FFFFF290。 |
| `text_options.font_size` | - | integer | 否 | - | 最小值: 1 | 花字字号单位为 px；未传时按视频短边除以 24 自动计算，例如 720p 默认 30、1080p 默认 45；不得小于 1。 |
| `text_options.font_type` | - | string | 否 | "SY_Bold" | 枚举: ["SY_Bold","SY_Black"] | 默认为 SY_Bold；支持 SY_Bold 和 SY_Black，分别表示思源粗体和思源黑体。 |
| `text_options.inner_padding` | - | integer | 否 | 1 | 最小值: 0 | 花字内边距单位为 px，默认为 1。 |
| `text_options.is_bold` | - | boolean | 否 | false | - | 花字是否加粗，默认为 false。 |
| `text_options.is_italic` | - | boolean | 否 | true | - | 花字是否斜体，默认为 true。 |
| `text_options.is_underline` | - | boolean | 否 | false | - | 花字是否添加下划线，默认为 false。 |
| `text_options.shadow_color` | - | string | 否 | "#00000080" | 格式: "^#[0-9A-Fa-f]{8}$" | 花字阴影颜色必须使用 #RRGGBBAA 格式，默认为 #00000080。 |
| `video_urls` | `--video-urls` | array<string> | 是 | - | 最少项数: 1；最多项数: 30 | 待处理短剧原片的视频源 URL 列表；支持本地文件路径和公网 HTTP/HTTPS URL 两种输入协议；支持 mp4、flv、ts、avi、mov、wmv、mkv 等主流视频格式；单次任务支持传入 1 到 30 个视频文件；累计时长不得超过 120 分钟，即 2 小时；输入分辨率当前仅支持 1080p；输入素材需保持分辨率一致，否则会有兼容性问题；每个输入视频必须同时包含视频流和音频流；音频轨道必须包含清晰可识别的中文对话文本，仅含 BGM、纯音乐或语气词无法准确还原剧情；建议视频画面下半部分包含清晰居中的中文字幕，以提升文字解说定位和剧情理解准确度。 |

### 返回结果

| 字段路径 | 类型 | 必含 | 模式 | 说明 |
| --- | --- | --- | --- | --- |
| `request_id` | string | 否 | Cloud | 请求标识；仅在后端返回时出现。 |
| `task_id` | string | 是 | Cloud | 异步任务的唯一标识，用于查询任务状态并获取最终结果。 |
| `task_type` | string | 否 | Cloud | 任务类型；仅在后端实际返回非空值时出现。 |
| `input_duration` | number | 否 | Cloud 终态 | 输入视频总时长，单位为秒。 |
| `mode` | string | 否 | Cloud 终态 | 解说视频模式。 |
| `output_duration` | number / null | 否 | Cloud 终态 | 所有输出解说视频的总时长，单位为秒。 |
| `video_infos` | array<object> | 否 | Cloud 终态 | 每个解说视频的详细信息列表，并与 video_urls 顺序一致。 |
| `video_infos[].duration` | number / null | 否 | Cloud 终态 | 该条解说视频的时长，单位为秒。 |
| `video_infos[].poster_url` | string | 否 | Cloud 终态 | 未生成封面图或 enable_return_poster 为 false 时，poster_url 为空字符串。 |
| `video_infos[].size` | integer / string / null | 否 | Cloud 终态 | 该条解说视频的文件大小，单位为字节。 |
| `video_infos[].video_url` | string | 否 | Cloud 终态 | 返回有效期 24 小时的 HTTPS 临时下载链接。 |
| `video_urls` | array<string> | 否 | Cloud 终态 | video_urls 返回有效期 24 小时的 HTTPS 临时下载链接。 VOD 签名后的解说视频下载 URL。 |

Cloud 调用成功后读取 `task_id`，再查询终态结果：

```bash
mediakit-cli shared query-task --task-id <task_id> --poll-complete
```

### 机器合同

以下命令只读取本模式的实时 help/schema，不发起业务调用：

```bash
mediakit-cli video drama-recap-vertical --help
mediakit-cli video drama-recap-vertical --schema
```
