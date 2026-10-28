# 图像压缩

## 能力用途

支持一站式图像体积优化，覆盖压缩质量、文件体积上限、输出格式转换和 PNG 瘦身；适用于用户上传图片前的体积治理；适用于网站与 App 的图片分发加载优化；适用于 AIGC 与多模态模型的媒体预处理。用户明确给出 quality、max_size 或 output_format，要求格式转换，或明确接受 PNG 有损压缩时选择本工具；压缩率提高可能增加画质损失。

## 相近能力选择

缩小图片文件体积时，先读取 [图片体积治理选择指南](families/image-size-reduction.md)，再决定使用 slim-image 或 compress-image。

## 参数填写规则

- 提交一张图片并指定压缩质量、输出体积上限、PNG 瘦身与输出格式。支持本地文件路径和公网 HTTP/HTTPS URL 两种输入协议。未传 output_format 时默认 webp。 可选参数仅在用户明确指定，或可从用户意图准确确定时填写；不得伪造。不能准确确定时省略，确为正确完成任务所必需时先向用户澄清。
- 与 `slim-image` 的边界：用户强调尽量不掉画质、质量优先或高质量缩小体积，且未要求精确体积上限、质量值或格式转换时，应优先使用 `slim-image`；若只说压缩或变小且无法判断目标，先澄清。

- 用户未点名格式时省略 output_format/format；用源容器或扩展名去填属于编造。用户点名了文档中的格式时即使等于默认值也要显式传递。调用成功或已被拦截后，不得再用编造的格式重试同一工具。
## Cloud

### 命令与生命周期

- 命令：`mediakit-cli image compress-image`
- 生命周期：同步
- 返回方式：直接返回 Cloud 业务结果。

### 使用指南

- 布尔参数（`--png-lossy`）只能写成 `--png-lossy=true` 或 `--png-lossy=false`，也可用裸 `--png-lossy`（等价 true）；禁止空格传值 `--png-lossy true`，否则该值会被当作位置参数。
- 布尔参数取默认值时直接省略，不要显式重复默认值。

### 调用示例

```bash
mediakit-cli image compress-image \
  --image-url <image_url>
```

仅使用用户真实输入替换占位符；可选 flag 遵守参数填写规则，不得编造 URL、文件、枚举或业务参数。

### 参数

| 参数路径 | CLI flag | 类型 | 必填 | 默认值 | 枚举/范围/结构 | 说明 |
| --- | --- | --- | --- | --- | --- | --- |
| `image_url` | `--image-url` | string | 是 | - | - | 待处理图片的 URL。仅支持静图；支持本地文件路径和公网 HTTP/HTTPS URL 两种输入协议；支持 .png、.jpg、.jpeg、.webp 格式。建议单张输入图片不超过 35 MB。输入图像的宽和高分别都不得超过 10000 像素。输出为 avif 时，建议输入图像的宽×高不超过 100,000 像素，否则任务可能失败。输出为 heic 时，建议输入图像分辨率不超过 4K（约4096×4096 像素），否则任务可能失败。 |
| `max_size` | `--max-size` | integer | 否 | - | 最小值: 1 | 输出图像的文件体积上限，单位为字节（Byte）。推荐设为 10,485,760 字节（10 MiB）。仅在 output_format 为 jpeg 或 webp 时生效；设置后，系统自动调整压缩参数以尽可能满足体积限制，手动设置的 quality 会被忽略。 |
| `output_format` | `--output-format` | string | 否 | "webp" | 枚举: ["png","jpeg","webp","avif","heic"] | 输出图片格式。支持 png、jpeg、webp、avif、heic；未提供 output_format 时默认使用 webp。若希望保持原图格式，需要显式传入原格式。 |
| `png_lossy` | `--png-lossy` | boolean | 否 | false | - | 可选开启 PNG 图片有损压缩，以获得更高压缩率；仅在 output_format 为 png 时生效；默认为 false。 |
| `quality` | `--quality` | integer | 否 | 75 | 最小值: 1；最大值: 100 | 压缩质量最小值为 1，最大值为 100，默认为 75。quality 越小，压缩率越高且图像质量损失越大。设置 max_size 时，quality 会被忽略。 |

### 返回结果

| 字段路径 | 类型 | 必含 | 模式 | 说明 |
| --- | --- | --- | --- | --- |
| `image_format` | string | 否 | Cloud | 生成图像的格式。 |
| `image_height` | integer | 否 | Cloud | 生成图像的高度，单位为 px。 |
| `image_size` | integer | 否 | Cloud | 生成图像的大小，单位为字节。 |
| `image_url` | string | 否 | Cloud | 处理后图片文件的下载地址，有效期为 24 小时，用户必须及时保存产物。 |
| `image_width` | integer | 否 | Cloud | 生成图像的宽度，单位为 px。 |

| `usage` | object | 否 | Cloud | 可选顶层返回字段。仅对已开放该字段的账号，在 Cloud 同步调用成功，或 query_task 查询到 completed 终态，且服务实际产生并返回正向计费用量时透传；其他状态、异步提交及 Local 调用不返回。 |
| `usage.normalized_usage` | number | 是 | Cloud | 归一化后的计费用量。由服务端按 BillingCount / 固定单位换算值 × list_price 计算，结果保留 6 位小数；客户端只校验并原样透传，不计算、推断或补齐。 |
### 机器合同

以下命令只读取本模式的实时 help/schema，不发起业务调用：

```bash
mediakit-cli image compress-image --help
mediakit-cli image compress-image --schema
```
