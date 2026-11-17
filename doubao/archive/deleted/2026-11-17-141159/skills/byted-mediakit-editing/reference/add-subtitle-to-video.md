# 视频加字幕

## 能力用途

将字幕文件或文本内容按自定义样式压制到视频画面中，生成带内嵌字幕的新视频。

## 能力边界

- 本工具只添加字幕，不能擦除字幕或水印，不能添加水印。
- 字幕位置只能从 `subtitle_pos_preset` 支持的固定预设中选择，不支持任意 X/Y 坐标；不得把字幕文本当作可自由定位的文字水印层。
- 水印需求必须改用当前产品明确公开的水印或画面叠加工具；没有匹配能力时应说明不支持，不能用本工具代替。

## 参数填写规则

- Cloud: subtitle_url参数与subtitles参数两者必须指定一个，且subtitle_url 优先级更高 可选参数仅在用户明确指定，或可从用户意图准确确定时填写；不得伪造。不能准确确定时省略，确为正确完成任务所必需时先向用户澄清。
- 设置 subtitle_pos_preset 或 subtitle_font_size 前，若没有视频宽高，先探测视频元信息。用户未指定位置时：横屏使用 bottom_center，竖屏使用 lower_third。
- 字号不得超过当前位置预设的最大渲染高度（视频原始高度 × height%）；单行字数 × 字号不得超过当前位置预设宽度（视频原始宽度 × width%）。
- 若成片用于短视频或漫剧平台，设置位置前向用户确认，并避开平台操作栏、进度条和互动控件。
## 语义效果选项

### `subtitle_font_type` 可选效果

| 语义名称 | 参数值 | 说明 |
| --- | --- | --- |
| 庞门正道标题体 | `pm_zhengdao` | 粗壮有力，硬汉气场，大标题/封面神器。 |
| 思源黑体 | `sy_black` | 经典无衬线黑体，端正百搭，正文首选。 |
| 站酷快乐体 | `zhanku_kuaile` | 圆润活泼，带手写感，适合轻松搞笑的 Vlog 氛围。 |

### `subtitle_pos_preset` 可选效果

| 语义名称 | 参数值 | 说明 |
| --- | --- | --- |
| 偏下三分之一 | `lower_third` | 字幕位于画面偏下三分之一处。 |
| 底部居中 | `bottom_center` | 字幕位于画面底部居中。 |
| 画面正中央 | `center` | 字幕位于画面正中央。 |
| 顶部居中 | `top_center` | 字幕位于画面顶部居中。 |

### `subtitle_text_effect` 可选效果

| 语义名称 | 参数值 | 说明 |
| --- | --- | --- |
| 渐变花字 | `vcr://fl10000386` | 字面呈黄、绿、蓝、粉的横向多色渐变。 |
| 牛仔蓝描边 | `vcr://fl10000395` | 浅蓝字面，外缘为较深蓝色描边。 |
| 白玫描边 | `vcr://fl10000396` | 白色字面，外缘为玫红色描边。 |
| 白粉描边 | `vcr://fl10000390` | 白色字面，外缘为粉色描边。 |
| 白黑描边 | `vcr://fl10000398` | 白色字面，外缘为黑色描边。 |
| 立体阴影 | `vcr://fl10000387` | 橙黄色字面带向右下方偏移的深红色阴影。 |
| 粉白描边 | `vcr://fl10000391` | 粉色字面，外缘为白色描边。 |
| 纹理花字 | `vcr://fl10000383` | 橙黄色字面叠有红色块状纹理。 |
| 绿色描边 | `vcr://fl10000394` | 黄绿色字面，外缘为深绿色描边。 |
| 蓝色描边 | `vcr://fl10000393` | 浅蓝字面，外缘为亮蓝色描边。 |
| 蓝黑描边 | `vcr://fl10000392` | 浅蓝字面，外缘依次可见黑色和蓝色描边。 |
| 铁锈红白色描边 | `vcr://fl10000397` | 铁锈红字面，外缘为白色描边。 |
| 黄白描边 | `vcr://fl10000381` | 浅黄色字面，外缘依次可见白色和黄色描边。 |
| 黄黑描边 | `vcr://fl10000389` | 黄色字面，外缘为黑色描边。 |
| 黑白描边 | `vcr://fl10000388` | 黑色字面，外缘为白色描边。 |
| 黑色描边 | `vcr://fl10000385` | 白色字面，外缘为黑色描边。 |

## Cloud

### 命令与生命周期

- 命令：`mediakit-cli editing add-subtitle-to-video`
- 生命周期：异步
- 返回方式：返回 `task_id`，再查询终态结果。

### 使用指南

- 对象或对象数组参数（`--subtitles`）需传合法 JSON 字符串；字段名与层级必须与上表“枚举/范围/结构”及子字段说明一致。不要用逗号分隔或裸文本。
- POSIX / bash：用单引号整体包裹，例如 `--subtitles '[{...}]'`。
- Windows PowerShell：按共享入口 [JSON 参数传参](../../byted-mediakit-shared/SKILL.md) 把 JSON flag 放在 `--%` 之后，内部双引号写成 `\"`，例如 `--% --subtitles "[{\"start_time\":0,\"end_time\":3,\"subtitle_text\":\"文本\"}]"`。Windows 内联 JSON 禁止单引号 JSON 和 `$json` 变量；`@文件`、stdin `-`、`file://` 写法按共享入口 [JSON 参数传参](../../byted-mediakit-shared/SKILL.md) 执行。

### 调用示例

```bash
mediakit-cli editing add-subtitle-to-video \
 --video-url <video_url>
```

仅使用用户真实输入替换占位符；可选 flag 遵守参数填写规则，不得编造 URL、文件、枚举或业务参数。

### 参数

| 参数路径 | CLI flag | 类型 | 必填 | 默认值 | 枚举/范围/结构 | 说明 |
| --- | --- | --- | --- | --- | --- | --- |
| `client_token` | `--client-token` | string | 否 | - | - | 用户请求凭证，用于幂等控制；大小写敏感，长度不超过 64 个 ASCII 可打印字符。 用于控制异步任务幂等；同步任务不支持幂等校验。异步任务首次提交时默认不传，服务端仍会对相同核心参数执行 24 小时默认幂等。用户明确指定 token 时原样使用。因网络超时、响应丢失等原因重试同一次提交时，原请求有 token 则复用原值，原请求未传则继续不传。任务已有结果后，用户要求“结果不对，重试”“重新跑一次”或“重新发起任务”时，必须生成并传递新的 token，避免返回原任务。新对话中用户要求“重新发起任务”时，若当前上下文具备完整任务参数，直接生成新 token 并提交；若参数不足，先向用户澄清，补齐后再使用新 token 发起，不得直接省略 token。新任务后续发生提交重试时复用该新 token。已有 task_id 且任务尚未完成时，只查询原任务，不得重新提交。CLI runtime 不判断用户意图，也不自动生成 token。 |
| `subtitle_font_color` | `--subtitle-font-color` | string | 否 | "#FFFFFFFF" | - | subtitle_font_color 非必填，字幕字体颜色采用 RGBA 格式，默认 #FFFFFFFF，表示不透明白色。 |
| `subtitle_font_size` | `--subtitle-font-size` | integer | 否 | 50 | 最小值: 1 | subtitle_font_size 非必填，字幕字体大小单位为 px，默认 50 px。字号不得超过所选位置预设的最大渲染高度，即视频原始高度 × height 百分比（例如 height 为 10% 时，最大字号为视频高度的 10%）；同时单行字数 × 字号不得超过所选位置预设的 width（视频原始宽度 × width 百分比，例如 80%）。 |
| `subtitle_font_type` | `--subtitle-font-type` | string | 否 | "sy_black" | 枚举: ["sy_black","pm_zhengdao","zhanku_kuaile"] | 字幕字体 ID。默认值为 sy_black (思源黑体)。 |
| `subtitle_pos_preset` | `--subtitle-pos-preset` | string | 否 | "bottom_center" | 枚举: ["bottom_center","top_center","center","lower_third"] | subtitle_pos_preset 非必填，通过预设值快速将字幕放到画面常用位置；支持 bottom_center（底部居中，默认，推荐横屏使用）、top_center（顶部居中）、center（画面正中央）、lower_third（偏下三分之一处，推荐竖屏使用）。用户未指定位置时：横屏使用 bottom_center，竖屏使用 lower_third。各预设对应的字幕渲染区域为：top_center 为 width 80%、height 10%、pos_x 10%、pos_y 5%；center 为 width 80%、height 15%、pos_x 10%、pos_y 42.5%；lower_third 为 width 80%、height 10%、pos_x 10%、pos_y 70%；bottom_center 为 width 80%、height 10%、pos_x 10%、pos_y 85%。其中 height 为相对视频原始高度的字体渲染最大高度，width 为相对视频原始宽度的字幕区域最大宽度。若当前没有视频宽高信息，可先探测视频元信息获取宽高后再选择位置与字号。若成片用于短视频或漫剧平台，设置位置前应向用户确认，并避开对应平台的操作栏、进度条和互动控件，避免字幕被遮挡。 |
| `subtitle_url` | `--subtitle-url` | string | 条件必填（subtitle_url 或 subtitles） | - | - | subtitle_url 非必填，用于提供字幕文件 URL，支持本地文件路径和公网 HTTP/HTTPS URL，支持 SRT、VTT、ASS 等常见字幕格式；subtitle_url 与 subtitles 同时存在时，优先使用 subtitle_url 的内容。 |
| `subtitles` | `--subtitles` | array<object> | 条件必填（subtitle_url 或 subtitles） | - | 最少项数: 1 | subtitles 非必填，是由多个字幕对象组成的字幕内容列表；每个对象包含字幕文本、开始时间和结束时间。 |
| `subtitles[].end_time` | - | number | 是 | - | 最小值: 0 | 该条字幕结束显示的时间，单位为秒。 |
| `subtitles[].start_time` | - | number | 是 | - | 最小值: 0 | 该条字幕开始显示的时间，单位为秒。 |
| `subtitles[].subtitle_text` | - | string | 是 | - | - | 单条字幕的文本内容。 |
| `video_url` | `--video-url` | string | 是 | - | - | video_url 是待添加字幕的视频 URL，支持本地文件路径和公网 HTTP/HTTPS URL 两种输入协议，支持 mp4、flv、ts、avi、mov、wmv、mkv 等主流视频格式；最高支持 4K（3840×2160）分辨率；建议输入视频文件大小不超过 10 GB。 |

| `subtitle_text_effect` | `--subtitle-text-effect` | string | 否 | - | 最短长度: 1 | 花字效果的资源 ID。默认无花字效果。设置本参数后，subtitle_font_color 参数将不生效。 |
### 参数关系

- 顶层参数必须满足：条件必填（subtitle_url 或 subtitles）。
- `$.subtitles[].end_time` 必须大于 `$.subtitles[].start_time`。

### 返回结果

| 字段路径 | 类型 | 必含 | 模式 | 说明 |
| --- | --- | --- | --- | --- |
| `request_id` | string | 否 | Cloud | 请求标识；仅在后端返回时出现。 |
| `task_id` | string | 是 | Cloud | 异步任务的唯一标识，用于查询任务状态并获取最终结果。 |
| `task_type` | string | 否 | Cloud | 任务类型；仅在后端实际返回非空值时出现。 |
| `duration` | number | 否 | Cloud 终态 | 输出视频总时长，单位为秒。 |
| `resolution` | string | 否 | Cloud 终态 | 输出分辨率支持 240p、360p、480p、540p、720p、1080p、2k、4k。 |
| `video_url` | string | 否 | Cloud 终态 | 生成的带内嵌字幕视频地址，文件格式为 MP4。返回有效期 24 小时的 HTTPS 临时下载链接，需及时下载保存。 |

Cloud 调用成功后读取 `task_id`，再查询终态结果：

```bash
mediakit-cli shared query-task --task-id <task_id> --poll-complete
```

### 机器合同

以下命令只读取本模式的实时 help/schema，不发起业务调用：

```bash
mediakit-cli editing add-subtitle-to-video --help
mediakit-cli editing add-subtitle-to-video --schema
```
