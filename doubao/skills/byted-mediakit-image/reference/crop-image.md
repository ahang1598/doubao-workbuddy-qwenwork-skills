# 图像裁剪

## 能力用途

对输入图像进行多模式裁剪，可执行方向裁剪、定向裁剪、自定义裁剪或内切圆裁剪，适用于多端尺寸适配、主体保留和指定区域截取。

## 参数填写规则

- 输入图片并指定裁剪模式。支持本地文件路径和公网 HTTP/HTTPS URL 两种输入协议。未传 crop_mode 时默认 directional，且方向裁剪默认位置为 center。 可选参数仅在用户明确指定，或可从用户意图准确确定时填写；不得伪造。不能准确确定时省略，确为正确完成任务所必需时先向用户澄清。

- 用户未点名格式时省略 output_format/format；用源容器或扩展名去填属于编造。用户点名了文档中的格式时即使等于默认值也要显式传递。调用成功或已被拦截后，不得再用编造的格式重试同一工具。
## 语义效果选项

### `crop_mode` 可选效果

| 语义名称 | 参数值 | 说明 |
| --- | --- | --- |
| 圆形裁剪 | `circle` | 执行最大内切圆裁剪。 |
| 定向裁剪 | `origin` | 根据指定宽高、偏移量和锚点进行定向裁剪。 |
| 方向裁剪 | `directional` | 根据指定宽度、高度和位置进行方向裁剪。 |
| 自定义裁剪 | `custom` | 根据左上角和右下角坐标进行自定义裁剪。 |

### `crop_position` 可选效果

| 语义名称 | 参数值 | 说明 |
| --- | --- | --- |
| 右侧 | `right` | 裁剪区域位于右侧。 |
| 居中 | `center` | 裁剪区域居中。 |
| 左侧 | `left` | 裁剪区域位于左侧。 |
| 底部 | `down` | 裁剪区域位于底部。 |
| 顶部 | `up` | 裁剪区域位于顶部。 |

### `origin_gravity` 可选效果

| 语义名称 | 参数值 | 说明 |
| --- | --- | --- |
| 上中 | `north` | 以上中为锚点。 |
| 下中 | `south` | 以下中为锚点。 |
| 中心 | `center` | 以中心为锚点。 |
| 右上 | `northeast` | 以右上为锚点。 |
| 右下 | `southeast` | 以右下为锚点。 |
| 右中 | `east` | 以右中为锚点。 |
| 左上 | `northwest` | 以左上为锚点。 |
| 左下 | `southwest` | 以左下为锚点。 |
| 左中 | `west` | 以左中为锚点。 |

## Cloud

### 命令与生命周期

- 命令：`mediakit-cli image crop-image`
- 生命周期：同步
- 返回方式：直接返回 Cloud 业务结果。

### 参数

| 参数路径 | CLI flag | 类型 | 必填 | 默认值 | 枚举/范围/结构 | 说明 |
| --- | --- | --- | --- | --- | --- | --- |
| `crop_height` | `--crop-height` | integer | 条件必填（crop_mode=directional 或 crop_mode=origin） | - | 最小值: 0 | directional 模式下，crop_height 表示裁剪后图像的目标高度，单位为 px，且 crop_mode 为 directional 时必须提供 crop_height。crop_mode 为 origin 时，crop_height 表示目标高度，单位为 px。crop_height 为 0 时，高度根据 crop_width 按原图比例自适应。 |
| `crop_mode` | `--crop-mode` | string | 否 | "directional" | 枚举: ["directional","origin","custom","circle"] | 支持 directional、origin、custom、circle 四种模式。directional 根据指定宽度、高度和位置进行方向裁剪；origin 根据指定宽高、偏移量和锚点进行定向裁剪；custom 根据指定左上角和右下角坐标进行自定义裁剪；circle 执行最大内切圆裁剪，无需配置其他参数。裁剪模式决定裁剪行为及所需参数，默认 directional。 |
| `crop_position` | `--crop-position` | string | 否 | "center" | 枚举: ["center","up","down","left","right"] | 指定裁剪区域的位置。支持 center、up、down、left、right，分别表示居中、顶部、底部、左侧、右侧，默认 center。 |
| `crop_width` | `--crop-width` | integer | 条件必填（crop_mode=directional 或 crop_mode=origin） | - | 最小值: 0 | directional 模式下，crop_width 表示裁剪后图像的目标宽度，单位为 px，且 crop_mode 为 directional 时必须提供 crop_width。crop_mode 为 origin 时，crop_width 表示目标宽度，单位为 px。crop_width 为 0 时，宽度根据 crop_height 按原图比例自适应。directional 模式下，crop_width 与 crop_height 不得同时为 0。 |
| `custom_x1` | `--custom-x1` | integer | 条件必填（crop_mode=custom） | - | - | crop_mode 为 custom 时，custom_x1 表示裁剪区域左上角横坐标（X 轴），单位为 px。 |
| `custom_x2` | `--custom-x2` | integer | 条件必填（crop_mode=custom） | - | - | crop_mode 为 custom 时，custom_x2 表示裁剪区域右下角横坐标（X 轴），单位为 px。 |
| `custom_y1` | `--custom-y1` | integer | 条件必填（crop_mode=custom） | - | - | crop_mode 为 custom 时，custom_y1 表示裁剪区域左上角纵坐标（Y 轴），单位为 px。 |
| `custom_y2` | `--custom-y2` | integer | 条件必填（crop_mode=custom） | - | - | crop_mode 为 custom 时，custom_y2 表示裁剪区域右下角纵坐标（Y 轴），单位为 px。 |
| `image_url` | `--image-url` | string | 是 | - | - | 待处理图片的 URL，仅支持处理静图。支持本地文件路径和公网 HTTP/HTTPS URL 两种输入协议，支持 .png、.jpg、.jpeg、.webp 格式。建议单张图片不超过 35 MB。crop_mode 为 circle 时，原图最短边不得超过 2048 px。 |
| `origin_gravity` | `--origin-gravity` | string | 否 | "northwest" | 枚举: ["northwest","north","northeast","west","center","east","southwest","south","southeast"] | 指定定向裁剪的锚点（起始点）。支持 northwest、north、northeast、west、center、east、southwest、south、southeast，默认 northwest，表示左上角。 |
| `origin_x` | `--origin-x` | integer | 条件必填（crop_mode=origin） | - | - | crop_mode 为 origin 时，origin_x 表示相对锚点水平偏移量，单位为 px；正值向右，负值向左。 |
| `origin_y` | `--origin-y` | integer | 条件必填（crop_mode=origin） | - | - | crop_mode 为 origin 时，origin_y 表示相对锚点垂直偏移量，单位为 px；正值向下，负值向上。 |
| `output_format` | `--output-format` | string | 否 | "original" | 枚举: ["original","png","jpeg","webp"] | 指定输出图片格式，默认 original，表示保持原图格式。circle 模式下，为确保背景透明，建议输出为 png 或 webp；输出 jpeg 时，非圆形区域填充为白色。 |

### 参数关系

- `crop_width + crop_height` 在 crop_mode=directional 时必填。
- `crop_width + crop_height + origin_x + origin_y` 在 crop_mode=origin 时必填。
- `custom_x1 + custom_y1 + custom_x2 + custom_y2` 在 crop_mode=custom 时必填。
- `$.custom_x2` 必须大于 `$.custom_x1`。
- `$.custom_y2` 必须大于 `$.custom_y1`。

### 调用示例

```bash
mediakit-cli image crop-image \
  --image-url <image_url> \
  --crop-width <crop_width> \
  --crop-height <crop_height>
```

仅使用用户真实输入替换占位符；可选 flag 遵守参数填写规则，不得编造 URL、文件、枚举或业务参数。

### 返回结果

| 字段路径 | 类型 | 必含 | 模式 | 说明 |
| --- | --- | --- | --- | --- |
| `image_format` | string | 否 | Cloud | 生成图像的格式。 |
| `image_height` | integer | 否 | Cloud | 生成图像的高度，单位为 px。 |
| `image_size` | integer | 否 | Cloud | 生成图像的大小，单位为字节。 |
| `image_url` | string | 否 | Cloud | 处理后图片的下载地址，有效期为 24 小时，请及时保存产物。 |
| `image_width` | integer | 否 | Cloud | 生成图像的宽度，单位为 px。 |

| `usage` | object | 否 | Cloud | 可选顶层返回字段。仅对已开放该字段的账号，在 Cloud 同步调用成功，或 query_task 查询到 completed 终态，且服务实际产生并返回正向计费用量时透传；其他状态、异步提交及 Local 调用不返回。 |
| `usage.normalized_usage` | number | 是 | Cloud | 归一化后的计费用量。由服务端按 BillingCount / 固定单位换算值 × list_price 计算，结果保留 6 位小数；客户端只校验并原样透传，不计算、推断或补齐。 |
### 机器合同

以下命令只读取本模式的实时 help/schema，不发起业务调用：

```bash
mediakit-cli image crop-image --help
mediakit-cli image crop-image --schema
```
