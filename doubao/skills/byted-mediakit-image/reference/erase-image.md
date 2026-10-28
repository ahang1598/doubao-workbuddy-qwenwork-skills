# 图像擦除修复

## 能力用途

可按不同场景控制自动检测并擦除图片中的文字或常见图标，擦除后的区域通过智能填充技术进行修复，修复后的区域与背景自然融合。

## 参数填写规则

- 提交一张图片（支持本地文件路径和公网 HTTP/HTTPS URL 两种输入协议`），可选择标准版擦除修复；标准版支持自动检测、bbox、遮罩和文字擦除。 可选参数仅在用户明确指定，或可从用户意图准确确定时填写；不得伪造。不能准确确定时省略，确为正确完成任务所必需时先向用户澄清。

- 用户未点名格式时省略 output_format/format；用源容器或扩展名去填属于编造。用户点名了文档中的格式时即使等于默认值也要显式传递。调用成功或已被拦截后，不得再用编造的格式重试同一工具。
## 语义效果选项

### `standard_scene` 可选效果

| 语义名称 | 参数值 | 说明 |
| --- | --- | --- |
| 全屏图标擦除 | `full_screen_icon_erase` | 擦除全屏图标。 |
| 全屏文字擦除 | `full_screen_text_erase` | 擦除全屏文字；可指定要擦除的文字，不指定时擦除所有文字内容。 |
| 指定区域擦除 | `selected_area_erase` | 擦除矩形框或遮罩图指定区域的并集。 |

## Cloud

### 命令与生命周期

- 命令：`mediakit-cli image erase-image`
- 生命周期：同步
- 返回方式：直接返回 Cloud 业务结果。

### 使用指南

- 对象或对象数组参数（`--selected-area`）需传合法 JSON 字符串；字段名与层级必须与下方参数表一致。不要用逗号分隔或裸文本。
- POSIX / bash：用单引号整体包裹，例如 `--selected-area '{"top_left_x":0,...}'`。
- Windows PowerShell：按共享入口的 JSON 参数传参规则将该 flag 放在 `--%` 后；Windows 内联 JSON 不要传单引号 JSON 或 `$json` 变量；`@文件`、stdin `-`、`file://` 写法按共享入口执行。

### 参数

| 参数路径 | CLI flag | 类型 | 必填 | 默认值 | 枚举/范围/结构 | 说明 |
| --- | --- | --- | --- | --- | --- | --- |
| `image_url` | `--image-url` | string | 是 | - | - | 待处理图像的 URL；图像来源支持本地文件路径和公网 HTTP/HTTPS URL 两种输入协议；输入图像分辨率不得小于 10x10 像素，且不得超过 2560x1440 像素，顺序为宽x高；单张输入图片大小不得超过 10 MB；输入图片仅支持 .png、.jpg、.jpeg、.webp、.tiff、.bmp和.heic 格式。 |
| `output_format` | `--output-format` | string | 否 | "webp" | 枚举: ["png","jpeg","webp"] | 输出图片的格式，支持 webp、png 和 jpeg；默认 webp。 |
| `standard_erase_text` | `--standard-erase-text` | string | 否 | - | - | standard_erase_text 指定需要擦除的文字内容；仅当 standard_scene 为 full_screen_text_erase 时生效；不提供 standard_erase_text 时会擦除识别到的所有文字。 |
| `standard_scene` | `--standard-scene` | string | 否 | "full_screen_text_erase" | 枚举: ["full_screen_text_erase","full_screen_icon_erase","selected_area_erase"] | 标准版擦除场景，仅当 tool_version 为 standard 时生效。默认值为 full_screen_text_erase。full_screen_text_erase：全屏文字擦除。可通过 standard_erase_text 字段指定要擦除的文字，不指定则默认擦除所有文字内容。full_screen_icon_erase：全屏图标擦除。selected_area_erase：指定区域擦除。使用此场景时，您必须至少提供 selected_area（矩形坐标）或 mask_url（遮罩图）中的一个参数来定义擦除范围。如果同时提供了这两个参数，系统将擦除它们所定义区域的并集。 |
| `tool_version` | `--tool-version` | string | 否 | "standard" | 枚举: ["standard"] | 图像擦除修复选用的模型版本；当前仅支持 standard（标准版）；standard 标准版适用于简单、明确的擦除任务。 |

| `mask_url` | `--mask-url` | string | 否 | - | - | 遮罩图片 URL。通过上传一张黑白遮罩图，可以指定需要擦除的任意形状区域。仅当 standard_scene 为 selected_area_erase 时生效。遮罩图要求如下：图像来源：支持本地文件路径和公网 HTTP/HTTPS URL 两种输入协议。分辨率要求：必须与输入图像 image_url 的分辨率一致。如果同时传入 selected_area，则擦除两个参数指定区域的并集。 |
| `selected_area` | `--selected-area` | object | 否 | - | - | 指定擦除区域（矩形框）。仅当 standard_scene 为 selected_area_erase 时生效。坐标系以输入图像的左上角为原点，宽度和高度均归一化为 [0,1]。例如，(0.5, 0.5) 代表图像中心点。如果同时传入 mask_url，则擦除两个参数指定区域的并集。 |
| `selected_area.bottom_right_x` | - | number | 是 | - | 最小值: 0；最大值: 1 | 矩形框右下角的 X 坐标（横向位置）。该值必须大于 top_left_x。 |
| `selected_area.bottom_right_y` | - | number | 是 | - | 最小值: 0；最大值: 1 | 矩形框右下角的 Y 坐标（纵向位置）。该值必须大于 top_left_y，取值范围 [0, 1]。 |
| `selected_area.top_left_x` | - | number | 是 | - | 最小值: 0；最大值: 1 | 矩形框左上角的 X 坐标（横向位置）。该值为相对于图片总宽度的比例。 |
| `selected_area.top_left_y` | - | number | 是 | - | 最小值: 0；最大值: 1 | 矩形框左上角的 Y 坐标（纵向位置）。该值为相对于图片总高度的比例。 |
### 参数关系

- standard_scene=selected_area_erase 且 tool_version=standard 时，参数必须满足：条件必填（selected_area 或 mask_url）。
- `$.selected_area.bottom_right_x` 必须大于 `$.selected_area.top_left_x`。
- `$.selected_area.bottom_right_y` 必须大于 `$.selected_area.top_left_y`。

### 调用示例

```bash
mediakit-cli image erase-image \
  --image-url <image_url>
```

仅使用用户真实输入替换占位符；可选 flag 遵守参数填写规则，不得编造 URL、文件、枚举或业务参数。

### 返回结果

| 字段路径 | 类型 | 必含 | 模式 | 说明 |
| --- | --- | --- | --- | --- |
| `image_format` | string | 否 | Cloud | 生成图像的格式。 |
| `image_height` | integer | 否 | Cloud | 生成图像的高度，单位为像素（px）。 |
| `image_size` | integer | 否 | Cloud | 生成图像的大小，单位为字节。 |
| `image_url` | string | 否 | Cloud | 擦除修复后的图片下载 URL，有效期为 24 小时，必须及时保存对应的产物。 |
| `image_width` | integer | 否 | Cloud | 生成图像的宽度，单位为像素（px）。 |

| `usage` | object | 否 | Cloud | 可选顶层返回字段。仅对已开放该字段的账号，在 Cloud 同步调用成功，或 query_task 查询到 completed 终态，且服务实际产生并返回正向计费用量时透传；其他状态、异步提交及 Local 调用不返回。 |
| `usage.normalized_usage` | number | 是 | Cloud | 归一化后的计费用量。由服务端按 BillingCount / 固定单位换算值 × list_price 计算，结果保留 6 位小数；客户端只校验并原样透传，不计算、推断或补齐。 |
### 机器合同

以下命令只读取本模式的实时 help/schema，不发起业务调用：

```bash
mediakit-cli image erase-image --help
mediakit-cli image erase-image --schema
```
