# 图像调整

## 能力用途

对输入图像的亮度、对比度和饱和度进行调整，支持调亮、调暗、增强对比度、减弱对比度、增强饱和度、减弱饱和度共 6 种快速调整效果。适用于素材基础优化、统一内容视觉风格、营造庄重、复古等特殊氛围等场景。

## 参数填写规则

- 提交一张图片并指定一种图像调整类型。支持本地文件路径和公网 HTTP/HTTPS URL 两种输入协议。adjust_type 为单选枚举，6 个值分别对应 6 个预置模板效果，未传 output_format 时默认保持原图格式。 可选参数仅在用户明确指定，或可从用户意图准确确定时填写；不得伪造。不能准确确定时省略，确为正确完成任务所必需时先向用户澄清。

- 用户未点名格式时省略 output_format/format；用源容器或扩展名去填属于编造。用户点名了文档中的格式时即使等于默认值也要显式传递。调用成功或已被拦截后，不得再用编造的格式重试同一工具。
## 语义效果选项

### `adjust_type` 可选效果

| 语义名称 | 参数值 | 说明 |
| --- | --- | --- |
| 减弱对比度 | `decrease_contrast` | 降低图像对比度。 |
| 减弱饱和度 | `decrease_saturation` | 降低图像饱和度。 |
| 增强对比度 | `increase_contrast` | 提高图像对比度。 |
| 增强饱和度 | `increase_saturation` | 提高图像饱和度。 |
| 调亮 | `increase_brightness` | 提高图像亮度。 |
| 调暗 | `decrease_brightness` | 降低图像亮度。 |

## Cloud

### 命令与生命周期

- 命令：`mediakit-cli image adjust-image-color`
- 生命周期：同步
- 返回方式：直接返回 Cloud 业务结果。

### 参数

| 参数路径 | CLI flag | 类型 | 必填 | 默认值 | 枚举/范围/结构 | 说明 |
| --- | --- | --- | --- | --- | --- | --- |
| `adjust_type` | `--adjust-type` | string | 是 | - | 枚举: ["increase_brightness","decrease_brightness","increase_contrast","decrease_contrast","increase_saturation","decrease_saturation"] | 必填的图像调整类型。支持 increase_brightness（调亮）、decrease_brightness（调暗）、increase_contrast（增强对比度）、decrease_contrast（减弱对比度）、increase_saturation（增强饱和度）、decrease_saturation（减弱饱和度）。一次仅支持选择一种效果。 |
| `image_url` | `--image-url` | string | 是 | - | - | 待处理图片，必填。支持本地文件路径和公网 HTTP/HTTPS URL 两种输入协议；仅支持 .png、.jpg、.jpeg、.webp 格式；仅支持处理静图。单张图片不得超过 35 MB，输入分辨率的宽和高均不得超过 10000 像素。 |
| `output_format` | `--output-format` | string | 否 | "original" | 枚举: ["original","png","jpeg","webp"] | 输出图片格式，可选。支持 original、png、jpeg、webp；original 表示保持与原图一致的格式，默认 original。 |

### 调用示例

```bash
mediakit-cli image adjust-image-color \
  --image-url <image_url> \
  --adjust-type <adjust_type>
```

仅使用用户真实输入替换占位符；可选 flag 遵守参数填写规则，不得编造 URL、文件、枚举或业务参数。

### 返回结果

| 字段路径 | 类型 | 必含 | 模式 | 说明 |
| --- | --- | --- | --- | --- |
| `image_format` | string | 否 | Cloud | 生成图像的格式。 |
| `image_height` | integer | 否 | Cloud | 生成图像的高度，单位为 px。 |
| `image_size` | integer | 否 | Cloud | 生成图像的大小，单位为字节。 |
| `image_url` | string | 否 | Cloud | 处理后的图片文件下载地址，有效期为 24 小时，请务必及时保存产物。 |
| `image_width` | integer | 否 | Cloud | 生成图像的宽度，单位为 px。 |

| `usage` | object | 否 | Cloud | 可选顶层返回字段。仅对已开放该字段的账号，在 Cloud 同步调用成功，或 query_task 查询到 completed 终态，且服务实际产生并返回正向计费用量时透传；其他状态、异步提交及 Local 调用不返回。 |
| `usage.normalized_usage` | number | 是 | Cloud | 归一化后的计费用量。由服务端按 BillingCount / 固定单位换算值 × list_price 计算，结果保留 6 位小数；客户端只校验并原样透传，不计算、推断或补齐。 |
### 机器合同

以下命令只读取本模式的实时 help/schema，不发起业务调用：

```bash
mediakit-cli image adjust-image-color --help
mediakit-cli image adjust-image-color --schema
```
