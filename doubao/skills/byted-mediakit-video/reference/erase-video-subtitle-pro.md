# 精细化字幕擦除

## 能力用途

用于字幕擦除（精细化版），对视频字幕进行高质量无痕擦除，并最大程度还原视频画面。

## 参数填写规则

- 可选参数仅在用户明确指定，或可从用户意图准确确定时填写；不得伪造。不能准确确定时省略，确为正确完成任务所必需时先向用户澄清。
- `client_token` 按下方异步幂等工作流生成或复用；其他文档派生的 Cloud 公共请求字段只在用户明确提供时传递，不得由 Agent 生成、推断或补写。

## 语义效果选项

### `mode` 可选效果

| 语义名称 | 参数值        | 说明                                    |
| ---- | ---------- | ------------------------------------- |
| 字幕模式 | `Subtitle` | 擦除 OCR 检测为字幕的文本；默认仅处理画面下半部分。          |
| 文本模式 | `Text`     | 擦除 OCR 检测为字幕及人名、地名等其他类型文本，不包含牌匾等场景文字。 |

### `model_version` 可选效果

| 语义名称 | 参数值  | 说明                                        |
| ---- | ---- | ----------------------------------------- |
| V5   | `v5` | 优化 AIGC 视频擦除后的闪烁、带阴影字幕的擦除效果和误擦问题，并提升处理速度。 |

### `output_encode_mode` 可选效果

| 语义名称 | 参数值       | 说明                       |
| ---- | --------- | ------------------------ |
| 大小优先 | `Size`    | 在保证一定画质的前提下，使输出码率接近源文件。  |
| 画质优先 | `Quality` | 采用较高码率编码，画质更好，但文件体积可能更大。 |

## Cloud

### 命令与生命周期

- 命令：`mediakit-cli video erase-video-subtitle-pro`
- 生命周期：异步
- 返回方式：返回 `task_id`，再查询终态结果。

### 使用指南

- 对象或对象数组参数（`--erase-ratio-location`、`--subtitle-filter`、`--time-segment-filter`）需传合法 JSON 字符串；字段名与层级必须与上表“枚举/范围/结构”及子字段说明一致。不要用逗号分隔或裸文本。
- POSIX / bash：用单引号整体包裹，例如 `--erase-ratio-location '[{...}]'`。
- Windows PowerShell：按共享入口 [JSON 参数传参](../../byted-mediakit-shared/SKILL.md) 把 JSON flag 放在 `--%` 之后，内部双引号写成 `\"`，例如 `--% --erase-ratio-location "[{\"top_left_x\":0,\"top_left_y\":0,\"bottom_right_x\":1,\"bottom_right_y\":0.2}]"`。Windows 内联 JSON 禁止单引号 JSON 和 `$json` 变量；`@文件`、stdin `-`、`file://` 写法按共享入口 [JSON 参数传参](../../byted-mediakit-shared/SKILL.md) 执行。

#### 先识别字幕位置，再精细化擦除

处理字幕擦除请求时，应先向用户确认是否发起 [`video-ocr`](video-ocr.md) 的 `Detailed` 模式任务，以定位字幕的时间和位置并降低误擦台标、水印、标题等其他画面文字的风险。仅在用户明确确认后才能调用 `video-ocr`；用户已明确要求先进行 OCR 定位时视为已确认，用户明确要求直接擦除或拒绝该定位流程时跳过。`video-ocr` 单文件视频时长不得超过 10 分钟；超出该限制时应告知用户无法对整段视频使用此定位流程，不得发起整段 `video-ocr` 任务。

OCR 定位和精细化擦除是两个独立的异步任务。正常首次执行该工作流时不主动生成 `client_token`。只有用户明确要求结果重试、重新跑或重新发起某个阶段时，才为需要重新提交的阶段生成新的 token；若用户要求重新发起整个字幕擦除流程，则分别生成新的 `ocr_client_token` 和 `erase_client_token`，两个 token 不得相同。提交发生网络超时或响应丢失时，复用当前阶段原请求已有的 token；原请求未传则继续不传。不得把 OCR 阶段的 token 复用于擦除阶段。

1. 取得上述确认后，按当前产品的 Cloud 调用要求准备运行环境，对同一个输入视频执行 `mediakit-cli video video-ocr --video-url <video_url> --mode Detailed`，读取返回的 `task_id`，并通过 `mediakit-cli shared query-task --task-id <task_id> --poll-complete` 获取终态结果。仅当用户明确要求重新执行 OCR 阶段时，在重新提交命令中增加 `--client-token <new_ocr_client_token>`。OCR 提交发生网络超时或响应丢失时，原请求已带 token 则复用原值，原请求未传则继续不传。
2. 在 `subtitles` 中筛选 `text_label` 为 `Subtitle` 的条目。使用其 `start_time`、`end_time` 确定需要擦除的时间段，使用 `text_location` 的 `top_left_x`、`top_left_y`、`bottom_right_x`、`bottom_right_y` 确定字幕框。`Detailed` 模式返回的位置单位为像素。
3. 将像素坐标转换为本工具要求的归一化比例。设视频画面宽度为 `W`、高度为 `H`，则 `top_left_x / W`、`bottom_right_x / W` 分别作为横坐标比例，`top_left_y / H`、`bottom_right_y / H` 分别作为纵坐标比例；转换结果须保持在 `[0,1]` 范围内。视频宽高和帧率可从源视频信息或 [`probe-video-metadata`](probe-video-metadata.md) 的探测结果中取得，其中帧率读取 `video_stream_meta.fps`。为覆盖文字描边或阴影，可在不超出画面的前提下按实际画面向字幕框外侧留出适当边距。
4. 不要直接使用 OCR 返回的原始时间边界，也不要固定只扩两帧。设有效视频帧率为 `F`，扩边帧数固定为 `K = 6`，扩边时长为 `Δ = K / F` 秒。完成第 5 步的时间窗合并后，对每个合并后的擦除时间窗将起始时间调整为 `max(0, start_time - Δ)`，将结束时间调整为 `min(D, end_time + Δ)`，其中 `D` 为视频总时长。无法取得有效帧率时，应先从源视频信息或 [`probe-video-metadata`](probe-video-metadata.md) 的探测结果中获取；仍无法取得时不得执行依赖帧扩边的精细擦除流程，并应向用户说明。
5. 对字幕条目按起始时间升序处理。相邻条目均为 `Subtitle`、两个归一化矩形相交或接触，且时间间隔不超过 `4 / F` 秒时，应将其合并为连续擦除时间窗；即使 `subtitle_text` 不同，也不应在字幕切换处重置擦除区域。合并后的起止时间分别取最小值和最大值，矩形取各框的最小左上角与最大右下角形成的外接矩形；重复处理直到没有可继续合并的条目。空间位置明显变化或时间间隔超过 `4 / F` 秒的字幕框不得合并。完成合并后，按第 4 步统一扩边。
6. 若同一位置贯穿整段视频，可将转换后的矩形传给顶层 `--erase-ratio-location`。若字幕位置随时间变化，使用 `--time-segment-filter`，设置 `mode` 为 `selected`，并将合并、扩边后的起止时间及对应归一化矩形分别写入各 `segments[].erase_ratio_location`。`selected` 只控制字幕擦除的生效时间范围，不会裁剪、截取或删除视频片段，也不会改变输出视频时长。
7. 使用分段擦除框时，不要同时传顶层 `--erase-ratio-location`。执行前应核对所有时间段均满足 `end_time > start_time`，每个矩形满足右下角坐标分别大于左上角坐标，并确认所选区域没有覆盖需要保留的台标、水印、标题或其他画面文字。
8. 正常首次提交 `erase-video-subtitle-pro` 时不主动生成 `client_token`。擦除任务已有结果后，只有用户明确要求结果重跑或重新发起时，才生成新的 `erase_client_token` 并在重新提交命令中增加 `--client-token <new_erase_client_token>`，避免在 24 小时内返回原任务。提交发生网络超时或响应丢失时，原请求已带 token 则复用原值，原请求未传则继续不传。

`video-ocr` 只提供定位依据，不会自动触发字幕擦除。应先检查 OCR 终态结果，再根据确认后的字幕类别、合并并扩边后的时间和位置构造本工具参数。

### 调用示例

```bash
mediakit-cli video erase-video-subtitle-pro \
  --video-url <video_url>
```

仅使用用户真实输入替换占位符；可选 flag 遵守参数填写规则，不得编造 URL、文件、枚举或业务参数。

### 参数

| 参数路径                                                                   | CLI flag                 | 类型            | 必填 | 默认值        | 枚举/范围/结构                 | 说明                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| ---------------------------------------------------------------------- | ------------------------ | ------------- | -- | ---------- | ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `client_token`                                                         | `--client-token`         | string        | 否  | -          | -                        | 用户请求凭证，用于幂等控制；大小写敏感，长度不超过 64 个 ASCII 可打印字符。 用于控制异步任务幂等；同步任务不支持幂等校验。异步任务首次提交时默认不传，服务端仍会对相同核心参数执行 24 小时默认幂等。用户明确指定 token 时原样使用。因网络超时、响应丢失等原因重试同一次提交时，原请求有 token 则复用原值，原请求未传则继续不传。任务已有结果后，用户要求“结果不对，重试”“重新跑一次”或“重新发起任务”时，必须生成并传递新的 token，避免返回原任务。新对话中用户要求“重新发起任务”时，若当前上下文具备完整任务参数，直接生成新 token 并提交；若参数不足，先向用户澄清，补齐后再使用新 token 发起，不得直接省略 token。新任务后续发生提交重试时复用该新 token。已有 task\_id 且任务尚未完成时，只查询原任务，不得重新提交。CLI runtime 不判断用户意图，也不自动生成 token。 |
| `erase_ratio_location`                                                 | `--erase-ratio-location` | array<object> | 否  | -          | 最少项数: 0；最多项数: 20         | 配置擦除框位置数组后，系统仅在指定矩形框选区域内执行文本擦除。每个 location 由左上角与右下角两个顶点确定矩形擦除区域，坐标以画面左上角 (0, 0) 为原点、右下角为 (1, 1)，X 轴向右、Y 轴向下，使用相对画面宽高的归一化比例 \[0,1]。最多支持 20 个擦除框。 location 对象用于定义一个矩形擦除框，使用归一化的坐标系，以视频画面左上角为原点 (0, 0)、右下角为 (1, 1)，通过指定左上和右下两个顶点的坐标来确定擦除区域。                                                                                                                                                                                              |
| `erase_ratio_location[].bottom_right_x`                                | -                        | number        | 是  | -          | 最小值: 0；最大值: 1            | bottom\_right\_x 是框选区域右下角相对于视频左上角在 X 轴上的偏移比例，范围 \[0,1]；0 与左边缘对齐，1 与右边缘对齐。该值应大于 top\_left\_x。                                                                                                                                                                                                                                                                                                                                          |
| `erase_ratio_location[].bottom_right_y`                                | -                        | number        | 是  | -          | 最小值: 0；最大值: 1            | bottom\_right\_y 是框选区域右下角相对于视频左上角在 Y 轴上的偏移比例，范围 \[0,1]；0 与上边缘对齐，1 与下边缘对齐。该值应大于 top\_left\_y。                                                                                                                                                                                                                                                                                                                                          |
| `erase_ratio_location[].top_left_x`                                    | -                        | number        | 是  | -          | 最小值: 0；最大值: 1            | top\_left\_x 是框选区域左上角相对于视频左上角在 X 轴上的偏移比例，范围 \[0,1]；0 与左边缘对齐，1 与右边缘对齐。                                                                                                                                                                                                                                                                                                                                                                 |
| `erase_ratio_location[].top_left_y`                                    | -                        | number        | 是  | -          | 最小值: 0；最大值: 1            | top\_left\_y 是框选区域左上角相对于视频左上角在 Y 轴上的偏移比例，范围 \[0,1]；0 与上边缘对齐，1 与下边缘对齐。                                                                                                                                                                                                                                                                                                                                                                 |
| `mode`                                                                 | `--mode`                 | string        | 否  | "Subtitle" | 枚举: \["Subtitle","Text"] | 字幕擦除模式，默认 Subtitle，支持 Subtitle 和 Text。Subtitle 模式擦除 OCR 检测为字幕的文本，默认仅处理视频画面下半部分（下方 50%）区域；配置 erase\_ratio\_location 时，只处理自定义擦除框与画面下半部分的交集。Text 模式擦除 OCR 检测为字幕及人名、地名等其他类型文本，不包含牌匾等场景文字；默认检测整个视频画面，配置 erase\_ratio\_location 时仅在指定擦除框内执行。                                                                                                                                                                                                |
| `model_version`                                                        | `--model-version`        | string        | 否  | "v5"       | 枚举: \["v5"]              | 擦除算法版本，豆包版仅支持 v5，默认 v5。V5 优化 AIGC 生成视频擦除字幕后的闪烁问题、带阴影字幕的擦除效果和误擦问题，并提升处理速度。                                                                                                                                                                                                                                                                                                                                                             |
| `output_encode_mode`                                                   | `--output-encode-mode`   | string        | 否  | "Quality"  | 枚举: \["Quality","Size"]  | 输出视频编码模式，默认 Quality。Quality 采用较高码率编码，画质更好，但文件体积可能更大；Size 在保证一定画质的前提下使输出码率接近源文件。                                                                                                                                                                                                                                                                                                                                                       |
| `subtitle_filter`                                                      | `--subtitle-filter`      | object        | 否  | -          | -                        | subtitle\_filter 通过文字高度和水平居中程度帮助系统更准确地判断哪些文本属于字幕，避免误擦大标题、台标、水印等非字幕文本。仅当文本高度不低于下限、不高于上限且水平方向足够居中时，文本才会被判定为字幕并擦除，大标题、台标、水印等文本会被排除。仅在 mode 为 Subtitle 时生效，不传时使用系统默认值。                                                                                                                                                                                                                                                                    |
| `subtitle_filter.center_offset_ratio`                                  | -                        | number        | 否  | -          | 最小值: 0；最大值: 1            | center\_offset\_ratio 是文字区域中心相对视频宽度中心的最大偏离比例，范围 \[0,1]，默认 0.08；超过该比例的文本不会被判定为字幕。                                                                                                                                                                                                                                                                                                                                                      |
| `subtitle_filter.max_text_height_ratio`                                | -                        | number        | 否  | -          | 最小值: 0；最大值: 1            | max\_text\_height\_ratio 是相对视频高度的文字高度最大比例，范围 \[0,1]；高于该高度的文本不会被判定为字幕；不传时默认 0.1（10%）。                                                                                                                                                                                                                                                                                                                                                  |
| `subtitle_filter.min_text_height_ratio`                                | -                        | number        | 否  | -          | 最小值: 0；最大值: 1            | min\_text\_height\_ratio 是相对视频高度的文字高度最小比例，范围 \[0,1]，默认 0.01（1%）；低于该高度的文本不会被判定为字幕。                                                                                                                                                                                                                                                                                                                                                     |
| `time_segment_filter`                                                  | `--time-segment-filter`  | object        | 否  | -          | -                        | 按时间段控制字幕擦除范围；不配置时处理整段视频。mode 为 selected 时仅处理 segments 列出的时间段，mode 为 skip 时跳过这些时间段并处理其余部分。                                                                                                                                                                                                                                                                                                                                             |
| `time_segment_filter.mode`                                             | -                        | string        | 是  | -          | 枚举: \["skip","selected"] | skip 跳过 segments 中列出的时间段并擦除其余部分；selected 仅擦除 segments 中列出的时间段。selected 只控制字幕擦除的生效时间范围，不会裁剪、截取或删除视频片段，也不会改变输出视频时长。                                                                                                                                                                                                                                                                                                                     |
| `time_segment_filter.segments`                                         | -                        | array<object> | 是  | -          | 最少项数: 1                  | 需要执行或跳过字幕擦除的时间段列表，至少包含 1 个时间段。 一个字幕擦除时间段，由起始时间、结束时间和可选的分段擦除框组成。                                                                                                                                                                                                                                                                                                                                                                       |
| `time_segment_filter.segments[].end_time`                              | -                        | number        | 是  | -          | 最小值: 0                   | end\_time 是以秒为单位的片段结束时间，需大于 start\_time。                                                                                                                                                                                                                                                                                                                                                                                              |
| `time_segment_filter.segments[].erase_ratio_location`                  | -                        | array<object> | 否  | -          | 最少项数: 0；最多项数: 20         | 当前时间段专属的擦除框列表，每个时间段最多支持 20 个擦除框；仅在 time\_segment\_filter.mode 为 selected 时支持，且不能与顶层 erase\_ratio\_location 同时配置。不传或传空数组时，该时间段使用默认擦除行为。 当前时间段内的一个矩形擦除框；坐标以画面左上角 (0,0) 为原点、右下角 (1,1)，均使用相对画面宽高的归一化比例。                                                                                                                                                                                                                                   |
| `time_segment_filter.segments[].erase_ratio_location[].bottom_right_x` | -                        | number        | 是  | -          | 最小值: 0；最大值: 1            | 擦除框右下角相对于视频画面左边缘的水平偏移比例，范围为 \[0,1]，并且应大于 top\_left\_x。                                                                                                                                                                                                                                                                                                                                                                                |
| `time_segment_filter.segments[].erase_ratio_location[].bottom_right_y` | -                        | number        | 是  | -          | 最小值: 0；最大值: 1            | 擦除框右下角相对于视频画面顶边的垂直偏移比例，范围为 \[0,1]，并且应大于 top\_left\_y。                                                                                                                                                                                                                                                                                                                                                                                 |
| `time_segment_filter.segments[].erase_ratio_location[].top_left_x`     | -                        | number        | 是  | -          | 最小值: 0；最大值: 1            | 擦除框左上角相对于视频画面左边缘的水平偏移比例，范围为 \[0,1]。                                                                                                                                                                                                                                                                                                                                                                                                   |
| `time_segment_filter.segments[].erase_ratio_location[].top_left_y`     | -                        | number        | 是  | -          | 最小值: 0；最大值: 1            | 擦除框左上角相对于视频画面顶边的垂直偏移比例，范围为 \[0,1]。                                                                                                                                                                                                                                                                                                                                                                                                    |
| `time_segment_filter.segments[].start_time`                            | -                        | number        | 是  | -          | 最小值: 0                   | start\_time 是以秒为单位的片段起始时间，取值大于等于 0。                                                                                                                                                                                                                                                                                                                                                                                                   |
| `video_url`                                                            | `--video-url`            | string        | 是  | -          | -                        | 支持本地文件路径和公网 HTTP/HTTPS URL 两种输入协议，支持 mp4、flv、ts、avi、mov、wmv、mkv 等主流视频格式，输入分辨率最高支持 2K，输出分辨率最高支持 1080P。                                                                                                                                                                                                                                                                                                                                 |

### 参数关系

- `$.erase_ratio_location[].bottom_right_x` 必须大于 `$.erase_ratio_location[].top_left_x`。
- `$.erase_ratio_location[].bottom_right_y` 必须大于 `$.erase_ratio_location[].top_left_y`。
- `$.time_segment_filter.segments[].end_time` 必须大于 `$.time_segment_filter.segments[].start_time`。
- `$.time_segment_filter.segments[].erase_ratio_location[].bottom_right_x` 必须大于 `$.time_segment_filter.segments[].erase_ratio_location[].top_left_x`。
- `$.time_segment_filter.segments[].erase_ratio_location[].bottom_right_y` 必须大于 `$.time_segment_filter.segments[].erase_ratio_location[].top_left_y`。

### 返回结果

| 字段路径               | 类型     | 必含 | 模式       | 说明                                                               |
| ------------------ | ------ | -- | -------- | ---------------------------------------------------------------- |
| `request_id`       | string | 否  | Cloud    | 请求标识；仅在后端返回时出现。                                                  |
| `task_id`          | string | 是  | Cloud    | 异步任务的唯一标识，用于查询任务状态并获取最终结果。                                       |
| `task_type`        | string | 否  | Cloud    | 任务类型；仅在后端实际返回非空值时出现。                                             |
| `duration`  | number | 否  | Cloud 终态 | duration 表示输出视频总时长，单位为秒。                                  |
| `video_url` | string | 否  | Cloud 终态 | video\_url 是擦除字幕后的视频地址；返回有效期 24 小时的 HTTPS 临时下载链接，请及时下载保存； |

Cloud 调用成功后读取 `task_id`，再查询终态结果：

```bash
mediakit-cli shared query-task --task-id <task_id> --poll-complete
```

### 机器合同

以下命令只读取本模式的实时 help/schema，不发起业务调用：

```bash
mediakit-cli video erase-video-subtitle-pro --help
mediakit-cli video erase-video-subtitle-pro --schema
```
