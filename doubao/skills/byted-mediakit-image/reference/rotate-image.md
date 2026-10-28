# 图像旋转

## 能力用途

通过设置旋转角度和旋转背景样式对图片进行旋转处理，适用于图片方向校正、创意编辑和批量图像处理。

## 参数填写规则

- 输入图片并指定旋转角度、旋转背景样式和输出格式。支持本地文件路径和公网 HTTP/HTTPS URL 两种输入协议。 可选参数仅在用户明确指定，或可从用户意图准确确定时填写；不得伪造。不能准确确定时省略，确为正确完成任务所必需时先向用户澄清。

- 用户未点名格式时省略 output_format/format；用源容器或扩展名去填属于编造。用户点名了文档中的格式时即使等于默认值也要显式传递。调用成功或已被拦截后，不得再用编造的格式重试同一工具。
## 语义效果选项

### `fill_color` 可选效果

| 语义名称 | 参数值 | 说明 |
| --- | --- | --- |
| 白色填充 | `White` | 以白色填充旋转后产生的空白区域。 |
| 透明填充 | `Transparent` | 以透明色填充旋转后产生的空白区域。 |
| 黑色填充 | `Black` | 以黑色填充旋转后产生的空白区域。 |

## Cloud

### 命令与生命周期

- 命令：`mediakit-cli image rotate-image`
- 生命周期：同步
- 返回方式：直接返回 Cloud 业务结果。

### 参数

| 参数路径 | CLI flag | 类型 | 必填 | 默认值 | 枚举/范围/结构 | 说明 |
| --- | --- | --- | --- | --- | --- | --- |
| `fill_color` | `--fill-color` | string | 否 | "Black" | 枚举: ["Black","White","Transparent"] | fill_color 用于填充旋转后因非正交角度产生的空白区域，支持 Black、White、Transparent。Black 表示黑色填充，White 表示白色填充，Transparent 表示透明填充，建议配合 png 格式输出，fill_color 默认为 Black。 |
| `image_url` | `--image-url` | string | 是 | - | - | 待处理图片的 URL。支持本地文件路径和公网 HTTP/HTTPS URL 两种输入协议，仅支持 .png、.jpg、.jpeg、.webp 格式，仅支持处理静图。输入图片宽度和高度均不得超过 10000 像素，建议单张图片不超过 35 MB。 |
| `output_format` | `--output-format` | string | 否 | "webp" | 枚举: ["original","png","jpeg","webp"] | output_format 用于指定输出图片格式，支持 original、png、jpeg、webp。original 表示保持与原图一致的格式，output_format 默认为 webp。 |
| `rotate_angle` | `--rotate-angle` | integer | 是 | - | 最小值: 1；最大值: 359 | rotate_angle 表示图像逆时针旋转的角度，必须大于 0 且必须小于 360。 |

### 调用示例

```bash
mediakit-cli image rotate-image \
  --image-url <image_url> \
  --rotate-angle <rotate_angle>
```

仅使用用户真实输入替换占位符；可选 flag 遵守参数填写规则，不得编造 URL、文件、枚举或业务参数。

### 返回结果

| 字段路径 | 类型 | 必含 | 模式 | 说明 |
| --- | --- | --- | --- | --- |
| `image_format` | string | 否 | Cloud | image_format 表示生成图像的格式。 |
| `image_height` | integer | 否 | Cloud | image_height 表示生成图像的高度，单位为 px。 |
| `image_size` | integer | 否 | Cloud | image_size 表示生成图像的大小，单位为字节。 |
| `image_url` | string | 否 | Cloud | image_url 是处理后图片文件的下载地址，有效期为 24 小时，请务必及时保存该地址指向的产物。 |
| `image_width` | integer | 否 | Cloud | image_width 表示生成图像的宽度，单位为 px。 |

| `usage` | object | 否 | Cloud | 可选顶层返回字段。仅对已开放该字段的账号，在 Cloud 同步调用成功，或 query_task 查询到 completed 终态，且服务实际产生并返回正向计费用量时透传；其他状态、异步提交及 Local 调用不返回。 |
| `usage.normalized_usage` | number | 是 | Cloud | 归一化后的计费用量。由服务端按 BillingCount / 固定单位换算值 × list_price 计算，结果保留 6 位小数；客户端只校验并原样透传，不计算、推断或补齐。 |
### 机器合同

以下命令只读取本模式的实时 help/schema，不发起业务调用：

```bash
mediakit-cli image rotate-image --help
mediakit-cli image rotate-image --schema
```
