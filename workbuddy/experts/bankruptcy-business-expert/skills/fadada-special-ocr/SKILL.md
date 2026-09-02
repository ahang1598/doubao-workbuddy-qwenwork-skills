---
name: 法大大专用OCR
name_en: fadada-special-ocr
description: 调用平台内部 OCR API 识别扫描版 PDF、图片、拍照件和截图，并对超过10MB的单文件使用包内固定脚本按页拆分后顺序识别。触发：图像型材料或普通PDF提取返回 empty/partial。不触发：已有稳定文本层的PDF、代码或Markdown。
---
# 扫描 PDF / 图片材料 OCR 识别

## 核心约束（必须最先阅读）

**⛔ 以下约束强制执行，严禁绕过 ⛔**


- **唯一允许的 OCR 方式**：调用内部 OCR API（见第3节）
- **文件过大（单文件超过10MB）**：必须由 `ocr_to_markdown.py` 自动调用包内 `scripts/split_ocr_input.py`；PDF 按原页序转为单页图片，单张大图在保持整页的前提下确定性压缩，再逐页调用 OCR API 并按页序组装。禁止运行时另写拆分代码或临时修改脚本。
- **严禁直接用视觉能力读取图片**：不要自行 view/read 扫描图像内容
- **严禁提供替代方案**：API 失败时，不要说"我可以试着帮你读一下"
- **API 失败时**：直接向用户展示错误信息并停止，不做任何兜底尝试
- **必须保留页序和页边界**：不得打乱、合并、截断页面内容
- **必须告知 Markdown 输出位置**：无论后续是否继续做问答、摘要、分析或生成，最终对用户的可见回复里都必须显式说明已生成 Markdown 文件，并给出 `output_file` 的绝对路径或链接
- **文件名时间戳必须真实**：`output_file` 中的 `{YYMMDD}_{HHMMSS}` 必须取 Markdown 实际写入时的当前本地时间，禁止使用示例值、占位值、估算值或“随便取一个时间”
- **默认使用高层脚本**：标准入口必须是 `ocr_to_markdown.py`；`parse_contract_file.py` 仅用于底层接口调试或查看 OCR 原始响应，不作为正常交付路径

**失败处理：**

- 如果 OCR API 不可用，明确报告依赖缺失并停止。
- 如果 OCR 输出为空或严重不完整，明确指出失败页码。
- 如果只有部分页面可读，返回部分结果，并显式给出提示。

## 1. 判断是否该启用本 skill

### 从 pdf skill 自动转入（最高优先级）

当运行 `extract_text.py` 后，JSON 输出中出现以下任一情况，需要切换本 skill：

| 触发条件 | 说明 |
|----------|------|
| `"next_action": "fadada-scanned-ocr"` | pdf skill 明确指示转 OCR |
| `"status": "empty"` | 所有页均无可读内容 |
| `"status": "partial"` | 部分页空白或内容质量不可用 |

无论单个还是多个文件需要 OCR，都**逐个调用脚本**，每次只传一个文件，拿到结果后再处理下一个：

```bash
python scripts/ocr_to_markdown.py <文件A>
# 读取并处理结果后再执行下一个
python scripts/ocr_to_markdown.py <文件B>
```

不要让代理自行拼接文件名、时间戳或 Markdown 正文——这些全由脚本负责生成。

### 其他触发场景

在以下场景中也使用本 skill：

- PDF 页面本质上是图片、扫描图或截图，需从图片中提取文字。
- 用户提供的是独立图片文件、扫描件图片、拍照件、截图等，需从图像中提取文字。
- PDF 是混合型文档：部分页面有可选中文本，部分页面是图片。
- 从指向扫描/图片型 PDF 或图片文件的 URL 或本地文件中提取文字。

出现以下情况时，不要使用本 skill：

- PDF 已经有稳定文本层，普通 PDF 读取 skill 可以可靠读取（即 `status: "success"`）。
- 代码文件或 Markdown 文档。
- 不涉及图像转文本的任务。

判断提取策略：

- 如果文档是混合型 PDF，整份文档统一走 OCR，不按页分流，确保处理一致性。


## 2. 执行前准备

确认以下输入信息：

| 信息项   | 说明 |
| -------- | ---- |
| 文件来源 | 本地路径或 URL；输入材料可以是 PDF 或图片文件（具体格式以实际接口支持为准） |
| 用户意图 | 见下表，结合用户实际需求判断 |

用户意图分类与 OCR 后衔接方向：

| 意图类型 | 典型表述 | OCR 后衔接方向 |
| -------- | -------- | -------------- |
| 展示全文 | "把这份文件内容给我看看" | 先生成 Markdown 文件，正文使用 `full_text_formatted`（场景 A） |
| 基于文件问答 | "根据这个文件回答我的问题"、"帮我解读一下这份合同" | 先生成 Markdown 文件，再将 `full_text_cleaned` 传入智能体问答流程（场景 C） |
| 摘要 / 字段抽取 | "帮我提取关键信息"、"总结一下" | 先生成 Markdown 文件，再将 `full_text_cleaned` 传入下游摘要或抽取 skill（场景 B） |
| 整合生成新文档 | "结合这份文件和……写一份……" | 先生成 Markdown 文件，再由生成类 skill 汇总 `full_text_cleaned` 内容，经 docx skill 输出 |

补充约定：

- 单张图片、单页扫描件、单个截图等非 PDF 输入，统一按**单页材料**处理，输出中页码固定为第 1 页。

## 3. 调用 OCR API

### 服务端文件解析接口

**接口地址**：`POST /claw/contractFile/parseFile`

| 环境 | 域名 |
|------|------|
| 开发环境（NODE_ENV=development） | https://dev-claw.richee.cn |
| 生产环境 | https://claw.richee.cn |

**认证**：使用 `richee-token` Header，Token 由 RicheeAI 平台自动注入（`RICHEEAI_TOKEN` 环境变量）。

**执行脚本**：

```bash
# 标准入口：OCR + 清洗 + 排版 + 写 Markdown
python scripts/ocr_to_markdown.py <文件路径>

# 标准入口：同时写出 .ocr.json sidecar，便于下游复用 full_text_cleaned / full_text_formatted
python scripts/ocr_to_markdown.py --write-sidecar <文件路径>

# 低层调试：仅调用 OCR API，不写 Markdown
python scripts/parse_contract_file.py <文件路径>
```

`ocr_to_markdown.py` 会在调用 API 前检查单文件大小。超过 10MB 时只走包内固定拆分入口；拆分失败返回具体 `BLOCKED_INPUT` 原因，不上传超限原文件，也不改用模型视觉能力。

**⚠️ 多文件时必须逐个调用，禁止一次性传入多个文件**

脚本内部对多个文件是顺序串行处理，每个文件单独调用一次 API。一次性传入多个文件会导致：
- 所有文件的等待时间累加，容易整体超时
- 任意一个文件失败会使顶层 `success` 变为 `false`，导致 agent 误判全部失败

正确做法：对每个文件单独执行一次脚本，每次拿到结果后再处理下一个：

```bash
# ✅ 正确：逐个调用
python scripts/ocr_to_markdown.py <文件1>
# 读取结果后再执行下一个
python scripts/ocr_to_markdown.py <文件2>

# ❌ 错误：一次性传多个
python scripts/ocr_to_markdown.py <文件1> <文件2> ...
```

标准路径下，必须以 `ocr_to_markdown.py` 的 stdout JSON 为准读取 `output_file`、`generated_at` 等字段，
不得由代理自行推断文件名、时间戳或输出路径。

**⚠️ 脚本执行后必须校验结果，禁止假定成功**

脚本在所有文件均成功时以 exit code 0 退出，任意文件失败则以 exit code 1 退出。**exit code 是第一道判断**，但仅凭 exit code 0 不足以确认内容有效，还必须读取 stdout JSON 逐项核验：

```
执行脚本
  → exit code 1 → 直接向用户报告失败，读取 stdout JSON 获取具体错误信息
  → exit code 0 → 继续读取 stdout JSON
      → 检查 results[0].success 是否为 true
      → 检查 results[0].global_warnings 是否包含"识别结果为空"
      → 检查 results[0].cleaned_chars 是否 > 0
      → 以上任一不通过 → 向用户明确报告失败，不得输出成功提示
```

**⚠️ 结果字段位置（重要）**

每次调用只传一个文件，脚本 stdout 结构为：

```json
{
  "success": true,
  "total": 1,
  "results": [
    { "success": true, "input_file": "...", "output_file": "...", "generated_at": "...", "global_warnings": [], ... }
  ]
}
```

- **`output_file`、`generated_at`、`global_warnings` 等字段在 `results[0]` 内，顶层不存在这些字段**
- `results[0].success == false` 时，读取 `results[0].error` 向用户报告，不得假装成功

**错误处理规则**：

| 错误类型 | 处理方式 |
|----------|----------|
| Token 未注入 | 脚本退出，提示"未找到认证 Token" |
| 文件不存在 | 返回 `{"success": false, "error": "文件不存在: ..."}` |
| HTTP 错误 | 返回 `{"success": false, "error": "HTTP 错误 {code}: ..."}` |
| 网络请求失败 | 返回 `{"success": false, "error": "请求失败: ..."}` |
| JSON 解析错误 | 返回 `{"success": false, "error": "响应 JSON 解析错误: ..."}` |

**任何错误情况下，均不得自行调用模型视觉能力尝试识别。**


## 4. 解析 OCR 返回结果

### 接口返回格式

```json
{
  "code": "000000",
  "message": "操作成功！",
  "success": true,
  "data": [
    {
      "fileName": "合同.pdf",
      "content": "解析后的文本内容..."
    }
  ],
  "callSuccess": true
}
```

### 结果处理

API 返回的 `content` 是整份文档的识别文本，**不含分页结构**，直接作为 `full_text_raw` 使用。
在标准路径下，后续清洗、排版、命名、写盘由 `ocr_to_markdown.py` 确定性完成：

| API 字段 | 处理结果 |
|----------|----------|
| `data[].fileName` | → `source_file` |
| `data[].content` | → `full_text_raw`（原样保留）→ 清洗 → `full_text_cleaned` → Markdown 排版 → `full_text_formatted` |
| 脚本写盘时刻 | → `generated_at` |
| 脚本文件写入结果 | → `output_file` |

成功判断：外层 `success == true` 且 `code == "000000"`。

## 5. 清洗与输出

### 5.1 清洗规则

清洗只做**最小干预**，绝不修改实质内容：

| 允许清洗 | 禁止修改 |
|----------|----------|
| 多余空行、行末空格 | 姓名、案号 |
| 明显的换行粘连（段落拼接） | 日期、金额 |
| 页眉页脚重复行（如"第X页 共X页"） | 法条引用、判决结果 |

对以下内容**必须标记为不确定**，不得猜测补全：

- 印章文字
- 手写内容、签名
- 模糊、污损、遮挡区域
- 旋转或歪斜严重的页面

标记格式：`【识别不确定：印章/手写/模糊/遮挡】`

### 5.2 Markdown 排版规则

`full_text_formatted` 基于 `full_text_cleaned` 生成，仅用于 Markdown 文件正文展示。
排版必须满足以下原则：**通用、保守、基于模式匹配，不做内容判断**。

| 规则 | 识别条件 | 处理方式 |
|----------|----------|----------|
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

### 5.3 根据用户意图输出

**A. 展示全文 / 生成可下载文档**（两者统一走此路径）

生成 Markdown 文件并向用户提供链接。文件名格式：

```
{原文件名去扩展名}_{YYMMDD}_{HHMMSS}.md
```

例：`合同扫描件_260409_181225.md`。
其中 `{YYMMDD}_{HHMMSS}` 必须取 Markdown 文件实际生成完成时刻，不能复用示例时间，也不能口头说明“随便取个时间”。

文件内容结构：

```markdown
# {原文件名去扩展名}

- **来源文件**：{fileName}
- **识别时间**：{YYYY-MM-DD HH:MM:SS}

---

{full_text_formatted}

---

## 识别警告
（仅 global_warnings 非空时追加此节）
- {warning 1}
- {warning 2}
```

生成后向用户回复：以脚本返回的 `output_file` 为准提供文件链接 + 如有警告则简要说明识别质量问题。

**B. 后续摘要 / 字段抽取**

仍先生成 Markdown 文件（同场景 A），再将 `full_text_cleaned` 传入下游摘要或抽取 skill。
如有 `sidecar_file`，优先让下游读取 sidecar 中的结构化字段，避免在对话上下文中重复塞入大段全文。
不要在本 skill 内做字段抽取或摘要，保持职责分离。
最终对用户的回复中，仍必须保留 Markdown 文件路径或链接，不能只输出摘要/抽取结果。

**C. 基于文件问答**

仍先生成 Markdown 文件（同场景 A），再将 `full_text_cleaned` 作为上下文传入问答流程。
如有 `sidecar_file`，优先从 sidecar 读取 `full_text_cleaned`，不要让代理重新拼接完整正文。
如 `global_warnings` 非空，在传递上下文时附带警告说明，提示问答结果可能受识别质量影响。
最终对用户的回复中，仍必须保留 Markdown 文件路径或链接，不能只输出问答或分析结果。

### 5.4 用户可见回复要求

无论最终停在 OCR 阶段，还是继续进入摘要、问答、诉讼策略分析、证据清单整理等下游流程，**对用户的最终可见回复都必须包含以下信息**：

1. 已生成 Markdown 文件这一事实
2. `output_file` 的绝对路径或可点击链接
3. 如有 `global_warnings`，用一句话提示识别质量问题

不得出现以下情况：

- 内部已经生成了 Markdown 文件，但最终回复完全不提
- 只把 `output_file` 传给下游 skill，不在用户回复中展示
- 最终回复只包含分析、摘要、问答结论，看不出 OCR 结果已落盘
- 在用户可见回复里展示示例文件名、占位时间戳，或附带”随便取个时间””这里先写一个时间”等说明
- **多文件时只展示第一个文件的结果，其余文件的 `output_file` 被遗漏**（必须逐条列出所有 `results[i].output_file`）

推荐写法：

```markdown
已生成 OCR 转写 Markdown：[{文件名}]({output_file})
```

如后续还有分析内容，应先给出上面的文件信息，再继续输出正文分析。

## 6. 输出格式约定

最终输出结构（供后续 skill 复用），详见 `references/output-contract.md`：

脚本 stdout 始终为以下顶层结构（单文件时 `results` 也是数组，长度为 1）：

```json
{
  "success": true,
  "total": N,
  "results": [ <每个文件一个对象，字段见下表> ]
}
```

每个 `results[i]` 对象包含：

| `results[i]` 字段 | 来源 | 说明 |
|-------------------|------|------|
| `input_file` | 脚本推断 | 输入文件绝对路径 |
| `source_file` | `data[].fileName` | API 返回的文件名 |
| `source_kind` | 脚本推断 | `"pdf"` 或 `"image"` |
| `generated_at` | 脚本写盘时刻 | ISO 8601 时间戳 |
| `output_file` | 脚本写入 .md 后推断 | Markdown 文件绝对路径 |
| `global_warnings` | 脚本检测 | 识别质量警告列表 |
| `sidecar_file` | 可选，`--write-sidecar` 时存在 | sidecar JSON 绝对路径 |
| `raw_chars` / `cleaned_chars` / `formatted_chars` | 脚本统计 | 字符数统计，供质量判断 |

`full_text_*` 字段**默认不在 stdout 中**，需传 `--include-texts` 才会出现。下游 skill 优先读 sidecar 获取全文，避免撑大上下文。

读取规则：
- **必须遍历 `results[]`，不得只读 `results[0]`**
- `output_file` 和 `generated_at` 只存在于 `results[i]` 内，顶层无此字段
- 失败的条目：`results[i].success == false`，读 `results[i].error` 并单独报告

## 7. 参考文件

- `references/ocr-api-integration.md` — 接口地址、鉴权方式、请求/响应格式、限制说明
- `references/output-contract.md` — 完整输出字段约定与 Markdown 文件模板
- `scripts/split_ocr_input.py` — 超过 10MB 的 PDF/图片固定拆分与压缩入口

## 法院文书与证据材料注意事项

- 法院判决书和证据材料经常包含印章、边注、截图、歪斜扫描页。
- 优先保证完整性，不要做过度清洗。
- 不做任何法律判断，仅做文字提取和忠实呈现。
