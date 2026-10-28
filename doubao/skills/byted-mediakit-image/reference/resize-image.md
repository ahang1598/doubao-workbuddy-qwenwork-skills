# 图像缩放

## 能力用途

用于图像缩放，支持按指定宽高精确缩放，也可按长边、短边或等比模式缩放，适用于多端素材适配、封面与缩略图生成及批量图片预处理。

## 参数填写规则

- 输入一张图片并指定缩放策略。支持本地文件路径和公网 HTTP/HTTPS URL 两种输入协议`。未传 resize_mode 时默认 contain，未传 resize_adaptive 时默认同时启用 enlarge 与 shrink。 可选参数仅在用户明确指定，或可从用户意图准确确定时填写；不得伪造。不能准确确定时省略，确为正确完成任务所必需时先向用户澄清。

- 用户未点名格式时省略 output_format/format；用源容器或扩展名去填属于编造。用户点名了文档中的格式时即使等于默认值也要显式传递。调用成功或已被拦截后，不得再用编造的格式重试同一工具。
## 语义效果选项

### `resize_mode` 可选效果

| 语义名称 | 参数值 | 说明 |
| --- | --- | --- |
| 填满并裁剪 | `cover` | 保持宽高比填满目标框，并居中裁剪超出部分。 |
| 完整包含 | `contain` | 保持宽高比并完整包含在目标框内。 |
| 精确缩放 | `exact` | 强制缩放到指定宽高，可能造成拉伸或压缩变形。 |

## Cloud

### 命令与生命周期

- 命令：`mediakit-cli image resize-image`
- 生命周期：同步
- 返回方式：直接返回 Cloud 业务结果。

### 使用指南

- 数组参数（`--resize-adaptive`）传多个值时用逗号分隔并整体加引号，例如 `--resize-adaptive "url1,url2"`。
- 单个值中的文件名或 URL 不能包含逗号（`,`），否则会被 CLI 当成多个元素拆开。遇到这种情况时，先向用户澄清，请其提供不含逗号的文件名或对应 URL 后再调用。

### 调用示例

```bash
mediakit-cli image resize-image \
  --image-url <image_url> \
  --resize-long <resize_long>
```

仅使用用户真实输入替换占位符；可选 flag 遵守参数填写规则，不得编造 URL、文件、枚举或业务参数。

### 参数

| 参数路径 | CLI flag | 类型 | 必填 | 默认值 | 枚举/范围/结构 | 说明 |
| --- | --- | --- | --- | --- | --- | --- |
| `image_url` | `--image-url` | string | 是 | - | - | image_url 是待处理图片的 URL，图片来源支持本地文件路径和公网 HTTP/HTTPS URL 两种输入协议；输入支持 .png、.jpg、.jpeg、.webp 格式；输入仅支持静图；建议单张输入图片不超过 35 MB，输入图像的宽和高均不得超过 10000 像素。 |
| `output_format` | `--output-format` | string | 否 | "original" | 枚举: ["original","png","jpeg","webp"] | output_format 指定输出图片格式；支持 original、png、jpeg、webp，original 表示输出保持与原图一致的格式；默认 original。 |
| `resize_adaptive` | `--resize-adaptive` | array<string> | 否 | ["enlarge","shrink"] | 最少项数: 1；元素枚举: ["enlarge","shrink"] | resize_adaptive 控制仅在特定条件下执行缩放；支持 enlarge、shrink；enlarge 仅在原图尺寸小于目标尺寸时执行放大，shrink 仅在原图尺寸大于目标尺寸时执行缩小；默认 enlarge、shrink，即总是执行缩放。 |
| `resize_long` | `--resize-long` | integer | 条件必填（resize_long 或 resize_short） | 0 | 最小值: 0 | 目标图像的长边尺寸，单位为像素。等比缩放：仅设置此参数（或将 resize_short 设为 0），图像将按原始比例缩放，使长边匹配此值。组合使用：当与 resize_short 同时设置时，缩放行为由 resize_mode 参数决定。与 resize_short 必须至少提供一个大于 0 的值。 |
| `resize_mode` | `--resize-mode` | string | 否 | "contain" | 枚举: ["exact","contain","cover"] | resize_mode 定义同时指定 resize_long 和 resize_short 时的缩放行为；支持 exact、contain、cover；exact 强制将图像精确缩放到 resize_long x resize_short，可能导致拉伸或压缩变形；contain 保持原始宽高比，使图像完整包含在 resize_long x resize_short 矩形框内，最终宽高均不超过指定值；cover 保持原始宽高比，使图像完全填满 resize_long x resize_short 矩形框，并居中裁剪超出部分；默认 contain。 |
| `resize_short` | `--resize-short` | integer | 条件必填（resize_long 或 resize_short） | 0 | 最小值: 0 | 目标图像的短边尺寸，单位为像素。等比缩放：仅设置此参数（或将 resize_long 设为 0），图像将按原始比例缩放，使短边匹配此值。组合使用：当与 resize_long 同时设置时，缩放行为由 resize_mode 参数决定。与 resize_long 必须至少提供一个大于 0 的值。 |

### 参数关系

- 顶层参数必须满足：条件必填（resize_long 或 resize_short）。

### 返回结果

| 字段路径 | 类型 | 必含 | 模式 | 说明 |
| --- | --- | --- | --- | --- |
| `image_format` | string | 否 | Cloud | image_format 表示生成图像的格式。 |
| `image_height` | integer | 否 | Cloud | image_height 表示生成图像的高度，单位为 px。 |
| `image_size` | integer | 否 | Cloud | image_size 表示生成图像的大小，单位为字节。 |
| `image_url` | string | 否 | Cloud | image_url 是处理后图片文件的下载地址，有效期为 24 小时，请务必及时保存下载地址对应的产物。 |
| `image_width` | integer | 否 | Cloud | image_width 表示生成图像的宽度，单位为 px。 |

| `usage` | object | 否 | Cloud | 可选顶层返回字段。仅对已开放该字段的账号，在 Cloud 同步调用成功，或 query_task 查询到 completed 终态，且服务实际产生并返回正向计费用量时透传；其他状态、异步提交及 Local 调用不返回。 |
| `usage.normalized_usage` | number | 是 | Cloud | 归一化后的计费用量。由服务端按 BillingCount / 固定单位换算值 × list_price 计算，结果保留 6 位小数；客户端只校验并原样透传，不计算、推断或补齐。 |
### 机器合同

以下命令只读取本模式的实时 help/schema，不发起业务调用：

```bash
mediakit-cli image resize-image --help
mediakit-cli image resize-image --schema
```
