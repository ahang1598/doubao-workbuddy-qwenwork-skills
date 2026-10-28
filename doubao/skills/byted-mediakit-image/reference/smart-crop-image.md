# 图像智能裁剪

## 能力用途

自动识别图像中的主体人脸区域，并适配指定尺寸进行裁剪；支持普通人脸和动漫人脸场景。未识别到人脸时，可按预设的降级策略输出结果。

## 参数填写规则

- 提交一张图片（支持本地文件路径和公网 HTTP/HTTPS URL 两种输入协议），并指定目标宽高、裁剪场景和未找到人脸时的降级裁剪策略。 可选参数仅在用户明确指定，或可从用户意图准确确定时填写；不得伪造。不能准确确定时省略，确为正确完成任务所必需时先向用户澄清。
## 语义效果选项

### `crop_strategy` 可选效果

| 语义名称 | 参数值 | 说明 |
| --- | --- | --- |
| 中心裁剪 | `center_crop` | 从图像正中心开始向四周裁剪。 |
| 毛玻璃填充 | `frosted_glass_fill` | 保持原图完整，并在两侧或上下添加毛玻璃背景达到目标尺寸。 |
| 顶部裁剪 | `top_crop` | 从图像顶部开始并水平居中裁剪。 |

### `scene` 可选效果

| 语义名称 | 参数值 | 说明 |
| --- | --- | --- |
| 动漫人脸裁剪 | `cartoon_face` | 使用动漫人脸裁剪场景模型。 |
| 普通人脸裁剪 | `person_face` | 使用普通人脸裁剪场景模型。 |

## Cloud

### 命令与生命周期

- 命令：`mediakit-cli image smart-crop-image`
- 生命周期：同步
- 返回方式：直接返回 Cloud 业务结果。

### 参数

| 参数路径 | CLI flag | 类型 | 必填 | 默认值 | 枚举/范围/结构 | 说明 |
| --- | --- | --- | --- | --- | --- | --- |
| `crop_strategy` | `--crop-strategy` | string | 否 | "top_crop" | 枚举: ["top_crop","center_crop","frosted_glass_fill"] | 可选。裁剪后图片与目标宽高比例不一致时，使用降级裁剪策略；支持三种策略：top_crop（从图像顶部开始并水平居中裁剪，默认）、center_crop（从图像正中心开始向四周裁剪）、frosted_glass_fill（保持原图完整，并在两侧或上下添加毛玻璃背景以达到目标尺寸）。 |
| `frosted_glass_strength` | `--frosted-glass-strength` | number | 否 | 100 | 最小值: 1 | 可选。毛玻璃填充的模糊强度，数值越大，模糊效果越强；仅在 crop_strategy 为 frosted_glass_fill 时生效。默认 100，推荐取值范围为 [10, 100]。 |
| `image_url` | `--image-url` | string | 是 | - | - | 待处理图片的 URL。支持本地文件路径和公网 HTTP/HTTPS URL 两种输入协议；仅支持 .png、.jpg、.jpeg、.webp、.tiff、.bmp、.heic 格式。图片宽和高均不得超过 6000 px，建议单张输入图片不超过 10 MB。 |
| `scene` | `--scene` | string | 否 | "person_face" | 枚举: ["person_face","cartoon_face"] | 可选。用于指定识别主体的裁剪场景模型；支持 person_face 和 cartoon_face 两种场景。person_face 表示普通人脸裁剪；cartoon_face 表示动漫人脸裁剪。默认 person_face。 |
| `target_height` | `--target-height` | integer | 否 | 100 | 最小值: 1 | 可选。裁剪后的目标高度，单位 px；默认 100。 |
| `target_width` | `--target-width` | integer | 否 | 100 | 最小值: 1 | 可选。裁剪后的目标宽度，单位 px；默认 100。 |

### 调用示例

```bash
mediakit-cli image smart-crop-image \
  --image-url <image_url>
```

仅使用用户真实输入替换占位符；可选 flag 遵守参数填写规则，不得编造 URL、文件、枚举或业务参数。

### 返回结果

| 字段路径 | 类型 | 必含 | 模式 | 说明 |
| --- | --- | --- | --- | --- |
| `image_format` | string | 否 | Cloud | 生成图像的格式。 |
| `image_height` | integer | 否 | Cloud | 生成图像的高度，单位 px。 |
| `image_size` | integer | 否 | Cloud | 生成图像的大小，单位字节。 |
| `image_url` | string | 否 | Cloud | 智能裁剪后图片文件的下载地址，有效期为 24 小时，务必及时保存指向的产物。 |
| `image_width` | integer | 否 | Cloud | 生成图像的宽度，单位 px。 |

| `usage` | object | 否 | Cloud | 可选顶层返回字段。仅对已开放该字段的账号，在 Cloud 同步调用成功，或 query_task 查询到 completed 终态，且服务实际产生并返回正向计费用量时透传；其他状态、异步提交及 Local 调用不返回。 |
| `usage.normalized_usage` | number | 是 | Cloud | 归一化后的计费用量。由服务端按 BillingCount / 固定单位换算值 × list_price 计算，结果保留 6 位小数；客户端只校验并原样透传，不计算、推断或补齐。 |
### 机器合同

以下命令只读取本模式的实时 help/schema，不发起业务调用：

```bash
mediakit-cli image smart-crop-image --help
mediakit-cli image smart-crop-image --schema
```
