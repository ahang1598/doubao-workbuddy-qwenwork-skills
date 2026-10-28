# 圆角矩形

## 能力用途

为图片四角快速添加正圆或椭圆圆角，适用于头像、卡片等常见视觉编辑场景。

## 参数填写规则

- 提交待处理图片，并按圆角类型配置半径参数。corner_type=circle 时必须传 radius；corner_type=ellipse 时必须同时传 radius_x 和 radius_y。 可选参数仅在用户明确指定，或可从用户意图准确确定时填写；不得伪造。不能准确确定时省略，确为正确完成任务所必需时先向用户澄清。

- 用户未点名格式时省略 output_format/format；用源容器或扩展名去填属于编造。用户点名了文档中的格式时即使等于默认值也要显式传递。调用成功或已被拦截后，不得再用编造的格式重试同一工具。
## 语义效果选项

### `corner_type` 可选效果

| 语义名称 | 参数值 | 说明 |
| --- | --- | --- |
| 椭圆圆角 | `ellipse` | 使用椭圆圆角。 |
| 正圆圆角 | `circle` | 使用正圆圆角。 |

## Cloud

### 命令与生命周期

- 命令：`mediakit-cli image round-corner-image`
- 生命周期：同步
- 返回方式：直接返回 Cloud 业务结果。

### 参数

| 参数路径 | CLI flag | 类型 | 必填 | 默认值 | 枚举/范围/结构 | 说明 |
| --- | --- | --- | --- | --- | --- | --- |
| `circle_radius` | `--circle-radius` | integer | 否 | 50 | 最小值: 0 | 正圆圆角半径，单位为 px，取值范围为 [0, 原图最小边/2]；超过该范围时按最大内切圆半径处理。 |
| `corner_type` | `--corner-type` | string | 否 | "circle" | 枚举: ["circle","ellipse"] | 圆角类型支持 circle 和 ellipse。circle 表示正圆圆角，半径通过 circle_radius 配置；ellipse 表示椭圆圆角，X 轴和 Y 轴半径分别通过 ellipse_radius_x 和 ellipse_radius_y 配置。默认 circle。 |
| `ellipse_radius_x` | `--ellipse-radius-x` | integer | 否 | 40 | 最小值: 0 | 椭圆圆角 X 轴（水平）半径，单位为 px，取值大于等于 0。 |
| `ellipse_radius_y` | `--ellipse-radius-y` | integer | 否 | 60 | 最小值: 0 | 椭圆圆角 Y 轴（垂直）半径，单位为 px，取值大于等于 0。 |
| `image_url` | `--image-url` | string | 是 | - | - | 待处理图片的 URL，支持本地文件路径和公网 HTTP/HTTPS URL 两种输入协议；仅支持 .png、.jpg、.jpeg、.webp 格式，仅支持处理静图。建议单张图片不超过 35 MB，输入图片的宽和高均不得超过 10000 像素。 |
| `output_format` | `--output-format` | string | 否 | "webp" | 枚举: ["original","png","jpeg","webp"] | 输出图片格式支持 original、png、webp 和 jpeg，默认 webp。original 保持原图格式；png 和 webp 会对圆角外区域进行透明填充，jpeg 会对圆角外区域进行白色填充。 |

### 调用示例

```bash
mediakit-cli image round-corner-image \
  --image-url <image_url>
```

仅使用用户真实输入替换占位符；可选 flag 遵守参数填写规则，不得编造 URL、文件、枚举或业务参数。

### 返回结果

| 字段路径 | 类型 | 必含 | 模式 | 说明 |
| --- | --- | --- | --- | --- |
| `image_format` | string | 否 | Cloud | 生成图像的格式 |
| `image_height` | integer | 否 | Cloud | 生成图像的高度，单位为 px |
| `image_size` | integer | 否 | Cloud | 生成图像的大小，单位为字节 |
| `image_url` | string | 否 | Cloud | 处理后的图片文件下载地址，有效期为 24 小时，必须及时保存指向的产物。 |
| `image_width` | integer | 否 | Cloud | 生成图像的宽度，单位为 px |

| `usage` | object | 否 | Cloud | 可选顶层返回字段。仅对已开放该字段的账号，在 Cloud 同步调用成功，或 query_task 查询到 completed 终态，且服务实际产生并返回正向计费用量时透传；其他状态、异步提交及 Local 调用不返回。 |
| `usage.normalized_usage` | number | 是 | Cloud | 归一化后的计费用量。由服务端按 BillingCount / 固定单位换算值 × list_price 计算，结果保留 6 位小数；客户端只校验并原样透传，不计算、推断或补齐。 |
### 机器合同

以下命令只读取本模式的实时 help/schema，不发起业务调用：

```bash
mediakit-cli image round-corner-image --help
mediakit-cli image round-corner-image --schema
```
