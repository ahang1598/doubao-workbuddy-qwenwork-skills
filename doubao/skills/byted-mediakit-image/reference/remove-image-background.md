# 图像背景移除

## 能力用途

自动识别并保留通用物体、人像或商品主体，移除背景后生成背景透明的图片，用于图像背景移除（抠图）；PNG、WebP 可输出透明背景，JPEG 的透明区域会填充为黑色。人像和商品场景还可生成主体描边或裁去多余透明区域。

## 参数填写规则

- 提交一张图片（支持本地文件路径和公网 HTTP/HTTPS URL 两种输入协议），并指定背景移除场景；human 适用于真人人像主体抠图，product 适用于商品主体抠图，general 适用于不确定主体分类或动漫/二次元、商标/Logo、非纯色背景通用物品等场景，也可在 human/product 效果不佳时改用。human/product 支持描边和透明背景裁剪。可选参数仅在用户明确指定，或可从用户意图准确确定时填写；不得伪造。不能准确确定时省略，确为正确完成任务所必需时先向用户澄清。

- 用户未点名格式时省略 output_format/format；用源容器或扩展名去填属于编造。用户点名了文档中的格式时即使等于默认值也要显式传递。调用成功或已被拦截后，不得再用编造的格式重试同一工具。

## 语义效果选项

### `scene` 可选效果

| 语义名称 | 参数值 | 说明 |
| --- | --- | --- |
| 人像抠图 | `human` | 抠出图像中的人像主体。 |
| 商品抠图 | `product` | 抠出图像中的商品主体。 |
| 通用场景 | `general` | 抠出图像主体但不限定主体分类。 |

## Cloud

### 命令与生命周期

- 命令：`mediakit-cli image remove-image-background`
- 生命周期：同步
- 返回方式：直接返回 Cloud 业务结果。

### 使用指南

- 布尔参数（`--need-contour`、`--need-crop-background`）只能写成 `--need-contour=true` 或 `--need-contour=false`，也可用裸 `--need-contour`（等价 true）；禁止空格传值 `--need-contour true`，否则该值会被当作位置参数。
- 布尔参数取默认值时直接省略，不要显式重复默认值。

### 调用示例

```bash
mediakit-cli image remove-image-background \
  --image-url <image_url> \
  --scene <scene>
```

仅使用用户真实输入替换占位符；可选 flag 遵守参数填写规则，不得编造 URL、文件、枚举或业务参数。

### 参数

| 参数路径               | CLI flag                 | 类型    | 必填 | 默认值    | 枚举/范围/结构                      | 说明                                                                                                                                                                                                                                            |
| ---------------------- | ------------------------ | ------- | ---- | --------- | ----------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `contour_color`        | `--contour-color`        | string  | 否   | "#FFFFFF" | 格式: "^#[0-9a-fA-F]{6}$"           | 主体描边颜色，使用十六进制 RGB，默认 #FFFFFF；仅当 need_contour 为 true 且 scene 为 human 或 product 时生效。                                                                                                                                   |
| `contour_size`         | `--contour-size`         | integer | 否   | 10        | 最小值: 1；最大值: 100              | 主体描边宽度，单位 px，范围 1 至 100，默认 10；仅当 need_contour 为 true 且 scene 为 human 或 product 时生效。                                                                                                                                  |
| `image_url` | `--image-url` | string | 是 | - | - | 待处理的图像 URL，支持本地文件路径和公网 HTTP/HTTPS URL 两种输入协议；仅支持 .png、.jpg、.jpeg、.webp、.tiff、.bmp和.heic 格式；单张图片不得超过 10 MB，图像输入分辨率的长边不得超过 7680 px、短边不得超过 4320 px。 |
| `need_contour`         | `--need-contour`         | boolean | 否   | false     | -                                   | 是否为主体生成描边，默认 false；仅在 scene 为 human 或 product 时生效，在 general 场景下会被忽略。                                                                                                                                              |
| `need_crop_background` | `--need-crop-background` | boolean | 否   | false     | -                                   | 是否将输出图片的透明背景裁剪到刚好包裹住主体，默认 false；仅在 scene 为 human 或 product 时生效，在 general 场景下会被忽略。                                                                                                                    |
| `output_format`        | `--output-format`        | string  | 否   | "png"     | 枚举: ["png","jpeg","webp"]         | 输出图片格式可用 png、jpeg、webp，默认 png；png 支持透明背景，webp 支持透明背景，jpeg 不支持透明背景，jpeg 的透明区域将填充为黑色。                                                                                                             |
| `scene`                | `--scene`                | string  | 是   | -         | 枚举: ["general","human","product"] | 背景移除场景可用 general、human、product；general 为通用场景，适用于期望抠出图像主体但不确定该主体所属分类的场景；human 为人像抠图场景，适用于仅需抠出图像中的人像主体的场景；product 为商品抠图场景，适用于仅需抠出图像中的商品主体的场景。    |

### 返回结果

| 字段路径       | 类型    | 必含 | 模式  | 说明                                       |
| -------------- | ------- | ---- | ----- | ------------------------------------------ |
| `image_format` | string  | 否   | Cloud | 生成图像的格式。                           |
| `image_height` | integer | 否   | Cloud | 生成图像的高度，单位 px。                  |
| `image_size`   | integer | 否   | Cloud | 生成图像的大小，单位为字节。               |
| `image_url`    | string  | 否   | Cloud | 背景移除后的图片下载 URL，有效期 24 小时。 |
| `image_width`  | integer | 否   | Cloud | 生成图像的宽度，单位 px。                  |

| `usage` | object | 否 | Cloud | 可选顶层返回字段。仅对已开放该字段的账号，在 Cloud 同步调用成功，或 query_task 查询到 completed 终态，且服务实际产生并返回正向计费用量时透传；其他状态、异步提交及 Local 调用不返回。 |
| `usage.normalized_usage` | number | 是 | Cloud | 归一化后的计费用量。由服务端按 BillingCount / 固定单位换算值 × list_price 计算，结果保留 6 位小数；客户端只校验并原样透传，不计算、推断或补齐。 |

### 机器合同

以下命令只读取本模式的实时 help/schema，不发起业务调用：

```bash
mediakit-cli image remove-image-background --help
mediakit-cli image remove-image-background --schema
```
