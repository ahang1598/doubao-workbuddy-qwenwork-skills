# OCR 输出格式约定

本文件定义法大大专用OCR skill 的标准输出结构，供解析、展示、摘要/抽取、文档生成各环节使用。

> **数据来源说明**：内部 OCR API（`/claw/contractFile/parseFile`）每个文件只返回两个字段：
> `fileName`（文件名）和 `content`（全量识别文本，一个字符串，不含分页结构）。
> 本文件定义的结构应由高层脚本 `scripts/ocr_to_markdown.py` 在 API 返回基础上**确定性生成**，非 API 直接输出，也不应由代理临时口头拼接。

---

## 推荐入口脚本

正常交付路径应直接调用高层脚本：

```bash
python scripts/ocr_to_markdown.py <文件路径>
python scripts/ocr_to_markdown.py --write-sidecar <文件路径>
```

其中：

- `ocr_to_markdown.py` 负责生成 `full_text_cleaned`、`full_text_formatted`、`generated_at`、`output_file`
- `--write-sidecar` 会额外写出 `.ocr.json` 文件，便于下游 skill 读取结构化结果
- `parse_contract_file.py` 仅用于底层接口调试，不作为正常交付路径

标准路径下，用户看到的文件名、时间戳、路径必须直接取自 `ocr_to_markdown.py` 的 stdout JSON。

---

## 主输出：Markdown 文件（最高优先级）

OCR 完成后，**首要动作是生成 Markdown 文件**，而不是在对话中打印全文。
Markdown 文件正文应使用 `full_text_formatted`，而不是直接输出 `full_text_cleaned`。

### 文件名格式

```
{原文件名去扩展名}_{YYMMDD}_{HHMMSS}.md
```

| 部分 | 说明 | 示例 |
|------|------|------|
| `{原文件名去扩展名}` | API 返回的 `fileName`，去掉 `.pdf`/`.png` 等后缀 | `合同扫描件` |
| `{YYMMDD}` | 输出完成当天日期，2位年+月+日 | `260409` |
| `{HHMMSS}` | 输出完成时的时分秒 | `181225` |

完整示例：`合同扫描件_260409_181225.md`

强约束：

- `{YYMMDD}_{HHMMSS}` 必须取 Markdown 实际写入完成时的当前本地时间
- 不得使用示例值、占位值、估算值或任意编造的时间
- 用户可见回复里只能展示真实生成后的文件名，不能写“随便取个时间”之类的说明

### Markdown 文件内容模板

```markdown
# {原文件名去扩展名}

- **来源文件**：{fileName}
- **识别时间**：{YYYY-MM-DD HH:MM:SS}
- **材料类型**：{pdf | image}

---

{full_text_formatted}

---

{如果 global_warnings 非空，追加以下内容：}

## 识别警告

{每条 warning 独占一行，格式为 "- {warning}"}
```

### 生成后的操作

1. 将 Markdown 文件写入工作空间（用户当前工作目录）
2. 向用户提供 `output_file` 的绝对路径或文件链接
3. 如有 `global_warnings`，在回复中简要提示识别质量问题
4. 如果后续还继续做摘要、问答、法律分析或生成，最终合并后的用户回复里仍必须保留第 2 步，不能省略
5. 用户可见回复中展示的文件名必须与实际已写入文件完全一致
6. `output_file` 和 `generated_at` 必须以 `ocr_to_markdown.py` 的 stdout JSON 为准，不得由代理自行拟造

---

## 内部数据结构

Markdown 文件生成过程中使用的中间数据结构，供后续 skill（问答、抽取、摘要）复用。

```json
{
  "doc_type": "scanned_ocr",
  "source_kind": "pdf",
  "source_file": "判决书.pdf",
  "generated_at": "2026-04-09T18:12:25+08:00",
  "full_text_raw": "API 返回的 content 原文，完整保留，不做任何修改",
  "full_text_cleaned": "清洗后的文本，只修正空行和换行粘连",
  "full_text_formatted": "基于 full_text_cleaned 按 Markdown 排版规则生成的展示文本",
  "global_warnings": ["接口未返回页码信息，全文作单页处理"],
  "output_file": "/abs/path/判决书_260409_181225.md",
  "sidecar_file": "/abs/path/判决书_260409_181225.ocr.json"
}
```

### 字段说明

| 字段 | 类型 | 来源 | 说明 |
|------|------|------|------|
| `doc_type` | string | `ocr_to_markdown.py` | 固定值 `"scanned_ocr"` |
| `source_kind` | string | `ocr_to_markdown.py` | `"pdf"` 或 `"image"` |
| `source_file` | string | API `fileName` | 原始文件名 |
| `generated_at` | string | `ocr_to_markdown.py` | Markdown 实际写入时刻的 ISO 8601 时间 |
| `full_text_raw` | string | API `content` | API 原始返回文本，完整保留，不做任何修改 |
| `full_text_cleaned` | string | `ocr_to_markdown.py` | 对 `full_text_raw` 最小清洗后的文本 |
| `full_text_formatted` | string | `ocr_to_markdown.py` | 基于 `full_text_cleaned` 按排版规则生成的 Markdown 正文展示版本 |
| `global_warnings` | array[string] | `ocr_to_markdown.py` | 全局警告列表，无则为 `[]` |
| `output_file` | string | `ocr_to_markdown.py` | 已写入的 Markdown 文件绝对路径 |
| `sidecar_file` | string | `ocr_to_markdown.py` 可选生成 | `.ocr.json` sidecar 文件绝对路径；仅在 `--write-sidecar` 时存在 |

补充约定：

- Markdown 文件正文使用 `full_text_formatted`
- 传给下游 skill 的正文使用 `full_text_cleaned`
- `full_text_formatted` 只做展示性排版，不承担内容纠错
- `output_file` 不只是内部字段；最终给用户的可见回复中必须显式展示
- `generated_at`、`output_file`、`sidecar_file` 由脚本真实写盘结果给出，不允许代理自行补写

## 用户可见回复约定

无论是否进入下游 skill，最终给用户的可见回复都必须明确说明 OCR Markdown 已生成，并展示 `output_file`。

最低要求：

1. 明确告知“已生成 OCR 转写 Markdown”
2. 给出 `output_file` 的绝对路径或可点击链接
3. 如有 `global_warnings`，补一句识别质量提示

禁止写法：

- 使用示例文件名冒充真实输出
- 在文件名后附带“随便取个时间”“这里先写一个时间”“时间无所谓”等说明

推荐写法：

```markdown
已生成 OCR 转写 Markdown：[{文件名}]({output_file})
```

如果后续还要继续输出分析、问答、摘要、诉讼策略、证据清单等内容，应先保留上面的文件信息，再继续正文。
如已生成 `sidecar_file`，下游 skill 应优先读取 sidecar，而不是把整段 OCR 正文重新塞回上下文。

## Markdown 排版规则

排版规则必须满足：**通用、保守、基于模式匹配，不做内容判断**。

| 规则 | 识别条件 | 处理方式 |
|------|----------|----------|
| 段落整理 | 连续多空行 | 保留一个空行 |
| 一级标题 | 独立成行的「第X章...」 | 转成 `## 第X章...` |
| 二级标题 | 独立成行的「第X节...」 | 转成 `### 第X节...` |
| 条款编号 | 段落首出现「第X条」 | 转成 `**第X条**`，其余内容保持内联 |
| 中文序号列表 | 以「一、」「二、」或「（一）」「（二）」开头的连续行 | 每行前加 `- `，行间不额外插入空行 |
| 数字序号列表 | 以「1.」「2.」或「①②」开头的连续行 | 保留原编号，确保每项独立成行 |
| 落款区 | 「甲方：」「乙方：」「签署日期：」等结尾定义行 | 将 key 加粗，例如 `**甲方**：...` |
| 其余 | 无法识别的内容 | 不改，原样保留 |

明确不做：

- 重建表格
- 猜测段落层级
- 补全缺失内容

---

## global_warnings 取值规范

> ⚠️ API 不提供置信度数据，置信度相关警告**不可使用**。

| 场景 | warning 写法 |
|------|-------------|
| 检测到印章文字区域 | `"识别不确定：印章"` |
| 检测到手写内容 | `"识别不确定：手写"` |
| 页面模糊/污损 | `"识别不确定：模糊"` |
| 内容被遮挡 | `"识别不确定：遮挡"` |
| 页面倾斜严重 | `"识别不确定：页面倾斜"` |
| 骑缝章（跨页） | `"识别不确定：骑缝章"` |
| 识别结果为空 | `"识别结果为空"` |

不确定内容在 `full_text_cleaned` 和 `full_text_formatted` 中的内联标记格式：
```
【识别不确定：印章】
```

---

## 各场景取用方式

**A. 展示全文 / 生成可下载文档**（两者合并，均走此路径）

首先生成 Markdown 文件（见上方主输出规范），然后向用户提供文件链接。
如有 `global_warnings`，在文件末尾附警告列表，并在回复中简要说明。

**B. 后续摘要 / 字段抽取**

将 `full_text_cleaned` 作为输入传入下游 skill，同时附带 `global_warnings`。
不要在本 skill 内做任何字段抽取或摘要；仍先输出 Markdown 文件，再交由下游处理。
如已生成 `sidecar_file`，优先从 sidecar 读取 `full_text_cleaned` 和其他结构化字段。
最终给用户的回复中，必须保留 Markdown 文件路径或链接，不能只展示摘要/抽取结果。

**C. 基于文件问答**

将 `full_text_cleaned` 作为上下文传入问答流程。
如有 `global_warnings`，附带说明识别质量可能影响问答结果。
仍先输出 Markdown 文件，保留可见的文字记录。
如已生成 `sidecar_file`，优先从 sidecar 读取 `full_text_cleaned`，避免重复拼接全文。
最终给用户的回复中，必须保留 Markdown 文件路径或链接，不能只展示问答或分析结果。

---

## 多文件输出约定

当输入为多个文件时，**每个文件独立生成一个 Markdown 文件**：

- 文件名各自按格式生成，时间戳取各自完成时间
- 不得将多个文件的文本合并到同一个文件
- 每个文件独立校验 success / 失败，失败的文件明确报错，不影响其他文件的处理
