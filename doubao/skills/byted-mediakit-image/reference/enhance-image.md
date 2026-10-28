# 图像画质增强

## 能力用途

基于图像内容理解进行智能决策，提升图片的分辨率、清晰度与色彩表现。

## 参数填写规则

- 必须至少传入 multiple 或 target_width / target_height，指定倍率或宽高。如果同时传入 multiple 和 target_width / target_height，则 multiple 生效。若不设置则默认倍率为2 可选参数仅在用户明确指定，或可从用户意图准确确定时填写；不得伪造。不能准确确定时省略，确为正确完成任务所必需时先向用户澄清。
## 语义效果选项

### `generative_enhance_mode` 可选效果

| 语义名称 | 参数值 | 说明 |
| --- | --- | --- |
| 保真度优先 | `fidelity_first` | 更侧重保留和增强图像既有细节，尽可能减少对原始内容的改动。 |
| 生成度优先 | `generative_first` | 在保留原图结构的基础上生成更丰富的纹理细节。 |

### `tool_version` 可选效果

| 语义名称 | 参数值 | 说明 |
| --- | --- | --- |
| 专业版 | `professional` | 在平衡保真度的前提下补充自然纹理细节，提升低质图像的清晰度与色彩表现。 |
| 标准版 | `standard` | 平衡处理速度、码率增长与画质效果。 |

## Cloud

### 命令与生命周期

- 命令：`mediakit-cli image enhance-image`
- 生命周期：同步
- 返回方式：直接返回 Cloud 业务结果。

### 参数

| 参数路径 | CLI flag | 类型 | 必填 | 默认值 | 枚举/范围/结构 | 说明 |
| --- | --- | --- | --- | --- | --- | --- |
| `image_url` | `--image-url` | string | 是 | - | - | image_url 是待增强图像的 URL，支持本地文件路径和公网 HTTP/HTTPS URL 两种输入协议；单张输入图片不得超过 10 MB；输入和输出尺寸范围随 tool_version 而不同：standard 输入短边 16–1440 px、长边 16–2160 px，输出两边均不超过 6144 px；professional 输入短边至少 256 px、长边不超过 2048 px，输出长边不超过 10240 px；仅支持 .png、.jpg、.jpeg、.webp 格式。 |
| `multiple` | `--multiple` | number | 否 | - | 最小值: 1；最大值: 30 | multiple 为非必选参数，表示图像处理后相对原图的放大倍数，支持 2 位小数；tool_version 为 standard 时，multiple 的范围是 [1, 8]；tool_version 为 professional 时，multiple 的范围是 [1, 30]；最终生成图像的宽度和高度不能超过所选模型版本支持的最大分辨率。 如果同时设置 multiple、target_width 和 target_height，优先使用 multiple；如果三者均未设置，默认按 2 倍放大。 |
| `target_height` | `--target-height` | integer | 否 | - | 最小值: 64；最大值: 10240 | target_height 为非必选参数，表示处理后的目标高度，单位为 px；可选，通常与 target_width 配合使用，也可单独设置以保持原图宽高比；tool_version 为 standard 时，target_height 的范围是 [原图高度, 6144]，且最终放大倍数不能超过 8 倍；tool_version 为 professional 时，target_height 的范围是 [64, 10240]；只指定宽或高时，另一边按原图宽高比等比缩放；同时指定宽和高且比例不一致时，按完整容纳于目标尺寸框内的最大尺寸保持原图宽高比。 |
| `target_width` | `--target-width` | integer | 否 | - | 最小值: 64；最大值: 10240 | target_width 为非必选参数，表示处理后的目标宽度，单位为 px；target_height 与 target_width 可选搭配使用，也可单独设置以保持原图宽高比；tool_version 为 standard 时，target_width 的范围是 [原图宽度, 6144]，且最终放大倍数不能超过 8 倍；tool_version 为 professional 时，target_width 的范围是 [64, 10240]；只指定宽或高时，另一边按原图宽高比等比缩放；同时指定宽和高且比例不一致时，按完整容纳于目标尺寸框内的最大尺寸保持原图宽高比； |
| `tool_version` | `--tool-version` | string | 否 | "standard" | 枚举: ["standard","professional"] | tool_version 为非必选参数，用于选择画质增强模型版本，不同版本在效果、处理范围和价格上有所差异；默认是 standard；standard 是标准版，平衡处理速度与画质效果；professional 是专业版，提供发丝级画质增强，效果更佳； |

| `generative_enhance_mode` | `--generative-enhance-mode` | string | 否 | "generative_first" | 枚举: ["generative_first","fidelity_first"] | 生成式增强策略，用于控制模型在“忠于原图”和“创造性修复”之间的平衡点。此参数仅在 tool_version 为 professional 时生效。支持取值如下：fidelity_first：保真度优先。此模式下，模型会更侧重于保留和增强图像的既有细节（如人物特征、原始纹理），尽可能减少对原始内容的改动。适用场景：当您需要高度还原细节时，如处理人像、产品图、文字截图等。generative_first：（默认）生成度优先。此模式下，模型会在保留原图结构的基础上智能生成更丰富、更自然的纹理细节，以达到最佳的主观视觉效果。适用场景：修复严重压缩或模糊的低质量图像，或当您希望获得最大程度的清晰度和细节感，并可以接受一定程度的细节再创作时。 |
### 参数关系

- `$.multiple` 在 tool_version=standard 时必须满足：最大值: 8。
- `$.target_height` 在 tool_version=standard 时必须满足：最大值: 6144。
- `$.target_width` 在 tool_version=standard 时必须满足：最大值: 6144。
- `$.multiple` 在 tool_version=professional 时必须满足：最大值: 30。
- `$.target_height` 在 tool_version=professional 时必须满足：最大值: 10240。
- `$.target_width` 在 tool_version=professional 时必须满足：最大值: 10240。

### 调用示例

```bash
mediakit-cli image enhance-image \
  --image-url <image_url>
```

仅使用用户真实输入替换占位符；可选 flag 遵守参数填写规则，不得编造 URL、文件、枚举或业务参数。

### 返回结果

| 字段路径 | 类型 | 必含 | 模式 | 说明 |
| --- | --- | --- | --- | --- |
| `image_format` | string | 否 | Cloud | tool_version 为 standard 时，输出图像格式固定为 png；tool_version 为 professional 时，输出图像格式与输入图像格式保持一致。 |
| `image_height` | integer | 否 | Cloud | 生成图像的高度，单位为 px。 |
| `image_size` | integer | 否 | Cloud | 生成图像的大小，单位为字节。 |
| `image_url` | string | 否 | Cloud | image_url 是增强后图片文件的下载地址，有效期为 24 小时，必须及时保存产物。 |
| `image_width` | integer | 否 | Cloud | 生成图像的宽度，单位为 px。 |

| `usage` | object | 否 | Cloud | 可选顶层返回字段。仅对已开放该字段的账号，在 Cloud 同步调用成功，或 query_task 查询到 completed 终态，且服务实际产生并返回正向计费用量时透传；其他状态、异步提交及 Local 调用不返回。 |
| `usage.normalized_usage` | number | 是 | Cloud | 归一化后的计费用量。由服务端按 BillingCount / 固定单位换算值 × list_price 计算，结果保留 6 位小数；客户端只校验并原样透传，不计算、推断或补齐。 |
### 机器合同

以下命令只读取本模式的实时 help/schema，不发起业务调用：

```bash
mediakit-cli image enhance-image --help
mediakit-cli image enhance-image --schema
```
