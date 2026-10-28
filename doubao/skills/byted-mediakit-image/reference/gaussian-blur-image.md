# 图像高斯模糊

## 能力用途

用于图像高斯模糊；通过设定模糊强度快速对图片进行模糊处理，适用于隐私信息弱化、背景氛围化、生成预览图及封面背景等场景。

## 参数填写规则

- 输入一张图片并指定高斯模糊强度。blur_strength 范围为 1~100，数值越大越模糊，默认 10；推荐值为 10（轻度）、30（中度）、100（重度）。output_format 默认 original 表示保持原图格式。 可选参数仅在用户明确指定，或可从用户意图准确确定时填写；不得伪造。不能准确确定时省略，确为正确完成任务所必需时先向用户澄清。

- 用户未点名格式时省略 output_format/format；用源容器或扩展名去填属于编造。用户点名了文档中的格式时即使等于默认值也要显式传递。调用成功或已被拦截后，不得再用编造的格式重试同一工具。
## Cloud

### 命令与生命周期

- 命令：`mediakit-cli image gaussian-blur-image`
- 生命周期：同步
- 返回方式：直接返回 Cloud 业务结果。

### 参数

| 参数路径 | CLI flag | 类型 | 必填 | 默认值 | 枚举/范围/结构 | 说明 |
| --- | --- | --- | --- | --- | --- | --- |
| `blur_strength` | `--blur-strength` | integer | 否 | 10 | 最小值: 1；最大值: 100 | 高斯模糊强度，数值越大越模糊，范围 1 到 100，默认 10。推荐 10 为轻度模糊，推荐 30 为中度模糊，推荐 100 为重度模糊。 |
| `image_url` | `--image-url` | string | 是 | - | - | 待处理图片 URL，支持本地文件路径和公网 HTTP/HTTPS URL 两种输入协议；仅支持处理静图；支持 .png、.jpg、.jpeg、.webp 格式。输入图像的宽和高均不得超过 10000 像素，建议单张图片不超过 35 MB。 |
| `output_format` | `--output-format` | string | 否 | "original" | 枚举: ["original","png","jpeg","webp"] | 输出图片格式，original 表示保持与原图一致的格式；支持 original、png、jpeg、webp，默认 original。 |

### 调用示例

```bash
mediakit-cli image gaussian-blur-image \
  --image-url <image_url>
```

仅使用用户真实输入替换占位符；可选 flag 遵守参数填写规则，不得编造 URL、文件、枚举或业务参数。

### 返回结果

| 字段路径 | 类型 | 必含 | 模式 | 说明 |
| --- | --- | --- | --- | --- |
| `image_format` | string | 否 | Cloud | 生成图像的格式，例如 jpeg。 |
| `image_height` | integer | 否 | Cloud | 生成图像的高度，单位为 px。 |
| `image_size` | integer | 否 | Cloud | 生成图像的大小，单位为字节。 |
| `image_url` | string | 否 | Cloud | 处理后的图片文件下载地址，有效期为 24 小时，请务必及时保存产物。 |
| `image_width` | integer | 否 | Cloud | 生成图像的宽度，单位为 px。 |

| `usage` | object | 否 | Cloud | 可选顶层返回字段。仅对已开放该字段的账号，在 Cloud 同步调用成功，或 query_task 查询到 completed 终态，且服务实际产生并返回正向计费用量时透传；其他状态、异步提交及 Local 调用不返回。 |
| `usage.normalized_usage` | number | 是 | Cloud | 归一化后的计费用量。由服务端按 BillingCount / 固定单位换算值 × list_price 计算，结果保留 6 位小数；客户端只校验并原样透传，不计算、推断或补齐。 |
### 机器合同

以下命令只读取本模式的实时 help/schema，不发起业务调用：

```bash
mediakit-cli image gaussian-blur-image --help
mediakit-cli image gaussian-blur-image --schema
```
