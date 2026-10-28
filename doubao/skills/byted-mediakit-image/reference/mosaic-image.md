# 图像打码

## 能力用途

支持对整张图像或指定矩形区域进行马赛克打码，可调整像素格形状与大小。支持用于遮挡人脸、证件信息、车牌、聊天记录等敏感内容。

## 参数填写规则

- 输入一张图片并配置打码方式。默认执行全图打码：mosaic_type=full-image、mosaic_step_x=12、mosaic_step_y=12、output_format=original。指定区域打码时设置 mosaic_type=specify-region，并传入 1-3 组 mosaic_regions 坐标。 可选参数仅在用户明确指定，或可从用户意图准确确定时填写；不得伪造。不能准确确定时省略，确为正确完成任务所必需时先向用户澄清。

- 用户未点名格式时省略 output_format/format；用源容器或扩展名去填属于编造。用户点名了文档中的格式时即使等于默认值也要显式传递。调用成功或已被拦截后，不得再用编造的格式重试同一工具。
## 语义效果选项

### `mosaic_shape` 可选效果

| 语义名称 | 参数值 | 说明 |
| --- | --- | --- |
| 圆形或椭圆像素格 | `circle` | 圆形或椭圆像素格。 |
| 矩形像素格 | `rectangle` | 矩形像素格。 |

### `mosaic_type` 可选效果

| 语义名称 | 参数值 | 说明 |
| --- | --- | --- |
| 指定区域打码 | `specify-region` | 仅对指定区域打码。 |
| 整图打码 | `full-image` | 对整张图片打码。 |

## Cloud

### 命令与生命周期

- 命令：`mediakit-cli image mosaic-image`
- 生命周期：同步
- 返回方式：直接返回 Cloud 业务结果。

### 使用指南

- 对象或对象数组参数（`--mosaic-regions`）需传合法 JSON 字符串；字段名与层级必须与上表“枚举/范围/结构”及子字段说明一致。不要用逗号分隔或裸文本。
- POSIX / bash：用单引号整体包裹，例如 `--mosaic-regions '[{...}]'`。
- Windows PowerShell：按共享入口 [JSON 参数传参](../../byted-mediakit-shared/SKILL.md) 把 JSON flag 放在 `--%` 之后，内部双引号写成 `\"`，例如 `--% --mosaic-regions "[{\"top_left_x\":0,\"top_left_y\":0,\"bottom_right_x\":100,\"bottom_right_y\":100}]"`。Windows 内联 JSON 禁止单引号 JSON 和 `$json` 变量；`@文件`、stdin `-`、`file://` 写法按共享入口 [JSON 参数传参](../../byted-mediakit-shared/SKILL.md) 执行。

### 调用示例

```bash
mediakit-cli image mosaic-image \
  --image-url <image_url>
```

仅使用用户真实输入替换占位符；可选 flag 遵守参数填写规则，不得编造 URL、文件、枚举或业务参数。

### 参数

| 参数路径 | CLI flag | 类型 | 必填 | 默认值 | 枚举/范围/结构 | 说明 |
| --- | --- | --- | --- | --- | --- | --- |
| `image_url` | `--image-url` | string | 是 | - | - | 仅支持处理静图；建议单张图片不超过 35 MB；输入图像的宽和高均不得超过 10000 像素。仅支持 .png、.jpg、.jpeg、.webp 格式。支持本地文件路径和公网 HTTP/HTTPS URL 两种输入协议。 |
| `mosaic_regions` | `--mosaic-regions` | array<object> | mosaic_type=specify-region 时是 | - | 最少项数: 1；最多项数: 3 | 最多支持 3 个矩形区域。 |
| `mosaic_regions[].bottom_right_x` | - | integer | 是 | - | 最小值: 0 | 框选区域右下角的 X 轴坐标，单位为 px，坐标原点为图像左上角，必须大于 top_left_x。 |
| `mosaic_regions[].bottom_right_y` | - | integer | 是 | - | 最小值: 0 | 框选区域右下角的 Y 轴坐标，单位为 px，坐标原点为图像左上角，必须大于 top_left_y。 |
| `mosaic_regions[].top_left_x` | - | integer | 是 | - | 最小值: 0 | 框选区域左上角的横 X 轴坐标，单位为 px，坐标原点为图像左上角。 |
| `mosaic_regions[].top_left_y` | - | integer | 是 | - | 最小值: 0 | 框选区域左上角的 Y 轴坐标，单位为 px，坐标原点为图像左上角。 |
| `mosaic_shape` | `--mosaic-shape` | string | 否 | "circle" | 枚举: ["circle","rectangle"] | 默认使用 circle。支持 circle 和 rectangle：circle 表示圆形/椭圆像素格，视觉更柔和；rectangle 表示矩形像素格，遮挡更规整。 |
| `mosaic_step_x` | `--mosaic-step-x` | integer | 否 | 12 | 最小值: 1 | 控制打码像素格的宽度，单位为 px；数值越大，马赛克颗粒感越强。默认值为 12。 |
| `mosaic_step_y` | `--mosaic-step-y` | integer | 否 | 12 | 最小值: 1 | 控制打码像素格的高度，单位为 px；数值越大，马赛克颗粒感越强。默认值为 12。 |
| `mosaic_type` | `--mosaic-type` | string | 否 | "full-image" | 枚举: ["full-image","specify-region"] | 默认使用 full-image，对整张图片打码。支持 full-image 和 specify-region：full-image 对整张图片打码；specify-region 仅对 mosaic_regions 指定的区域打码。 |
| `output_format` | `--output-format` | string | 否 | "original" | 枚举: ["original","png","jpeg","webp"] | 支持 png、jpeg、webp，也支持并默认使用 original，保持与原图一致的格式。 |

### 参数关系

- `$.mosaic_regions` 在 mosaic_type=specify-region 时必填。
- `$.mosaic_regions[].bottom_right_x` 必须大于 `$.mosaic_regions[].top_left_x`。
- `$.mosaic_regions[].bottom_right_y` 必须大于 `$.mosaic_regions[].top_left_y`。

### 返回结果

| 字段路径 | 类型 | 必含 | 模式 | 说明 |
| --- | --- | --- | --- | --- |
| `image_format` | string | 否 | Cloud | 返回生成图像的格式。 |
| `image_height` | integer | 否 | Cloud | 生成图像的高度，单位为 px。 |
| `image_size` | integer | 否 | Cloud | 生成图像的大小，单位为字节。 |
| `image_url` | string | 否 | Cloud | 处理后的图片文件下载地址有效期为 24 小时，必须及时保存产物。 |
| `image_width` | integer | 否 | Cloud | 生成图像的宽度，单位为 px。 |

| `usage` | object | 否 | Cloud | 可选顶层返回字段。仅对已开放该字段的账号，在 Cloud 同步调用成功，或 query_task 查询到 completed 终态，且服务实际产生并返回正向计费用量时透传；其他状态、异步提交及 Local 调用不返回。 |
| `usage.normalized_usage` | number | 是 | Cloud | 归一化后的计费用量。由服务端按 BillingCount / 固定单位换算值 × list_price 计算，结果保留 6 位小数；客户端只校验并原样透传，不计算、推断或补齐。 |
### 机器合同

以下命令只读取本模式的实时 help/schema，不发起业务调用：

```bash
mediakit-cli image mosaic-image --help
mediakit-cli image mosaic-image --schema
```
