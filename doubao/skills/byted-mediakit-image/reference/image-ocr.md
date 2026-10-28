# 图像文字识别OCR

## 能力用途

识别图片中的印刷体或手写体文字并返回文本块内容、位置坐标与置信度。标准版支持简体中文和英文印刷体通用识别；加强版支持印刷体、手写体及 100+ 语种，并支持通用识别与关键词匹配识别。
## 参数填写规则

- 提交一张包含通用印刷体文字的图片（支持本地文件路径和公网 HTTP/HTTPS URL 两种输入协议`），识别图片中的简体中文和英文文本。 可选参数仅在用户明确指定，或可从用户意图准确确定时填写；不得伪造。不能准确确定时省略，确为正确完成任务所必需时先向用户澄清。
## Cloud

### 命令与生命周期

- 命令：`mediakit-cli image image-ocr`
- 生命周期：同步
- 返回方式：直接返回 Cloud 业务结果。

### 使用指南

- `image_url` 有宽高与体积限制：长边不得超过 3840 px，短边不得超过 2160 px，单张文件大小不得超过 10 MB。为避免超限导致调用失败，提交 OCR 前可先用本域能力做前置探测与治理：
  1. 用 `probe-image-metadata`（默认 `info_type=metadata`）探测宽高与文件大小，判断是否可能超限；
  2. 若宽高超限，先用 `resize-image` 等比缩放到合规尺寸；详见 [resize-image.md](resize-image.md)；
  3. 若体积超限，先用 `compress-image` 压缩到 10 MB 以内；详见 [compress-image.md](compress-image.md)；
  4. 将预处理返回的 `image_url` 再作为本工具的 `--image-url` 输入。探测详见 [probe-image-metadata.md](probe-image-metadata.md)。

### 参数

| 参数路径 | CLI flag | 类型 | 必填 | 默认值 | 枚举/范围/结构 | 说明 |
| --- | --- | --- | --- | --- | --- | --- |
| `image_url` | `--image-url` | string | 是 | - | - | 待识别的图像 URL。图像来源支持本地文件路径和公网 HTTP/HTTPS URL 两种输入协议；图像长边不得超过 3840 px，短边不得超过 2160 px，单张图片文件大小不得超过 10 MB；仅支持 .png、.jpg、.jpeg、.webp、.tiff、.bmp和.heic 格式。 |

### 调用示例

```bash
mediakit-cli image image-ocr \
  --image-url <image_url>
```

仅使用用户真实输入替换占位符；可选 flag 遵守参数填写规则，不得编造 URL、文件、枚举或业务参数。

### 返回结果

| 字段路径 | 类型 | 必含 | 模式 | 说明 |
| --- | --- | --- | --- | --- |
| `ocr_result` | array<object> | 否 | Cloud | 通用印刷体文字识别结果列表，每个元素代表一个识别出的文本块。 |
| `ocr_result[].bottom_right_x` | number | 否 | Cloud | 文字框右下角的横坐标，单位为像素（px）。 |
| `ocr_result[].bottom_right_y` | number | 否 | Cloud | 文字框右下角的纵坐标，单位为像素（px）。 |
| `ocr_result[].confidence` | number | 否 | Cloud | 识别结果的置信度，范围为 [0, 1]，值越高表示结果越可信。 |
| `ocr_result[].content` | string | 否 | Cloud | 识别出的文字内容。 |
| `ocr_result[].top_left_x` | number | 否 | Cloud | 文字框左上角的横坐标，单位为像素（px）。 |
| `ocr_result[].top_left_y` | number | 否 | Cloud | 文字框左上角的纵坐标，单位为像素（px）。 |

| `keyword_result` | object | 否 | Cloud | 关键词匹配识别结果。仅加强版 task_type=keyword 时返回。对象的 key 为您传入的关键词，value 为识别到的匹配文本（String 类型）。 |
| `usage` | object | 否 | Cloud | 可选顶层返回字段。仅对已开放该字段的账号，在 Cloud 同步调用成功，或 query_task 查询到 completed 终态，且服务实际产生并返回正向计费用量时透传；其他状态、异步提交及 Local 调用不返回。 |
| `usage.normalized_usage` | number | 是 | Cloud | 归一化后的计费用量。由服务端按 BillingCount / 固定单位换算值 × list_price 计算，结果保留 6 位小数；客户端只校验并原样透传，不计算、推断或补齐。 |
### 机器合同

以下命令只读取本模式的实时 help/schema，不发起业务调用：

```bash
mediakit-cli image image-ocr --help
mediakit-cli image image-ocr --schema
```
