---
name: Word文档处理
name_en: word-document-processing
version: 1.0.1
description: "Word文档创建、编辑和分析，支持修订跟踪、批注、格式保留。内置律师规范Pandoc模板（宋体+首行缩进）+Lua过滤器，Markdown一键转DOCX。适用于创建正式文档、合同修订、内容提取等任务。"
category: general
changelog: "1.0.1: 回传批注功能修复（补齐scripts/templates/5个批注基础设施模板、修复document.py add_comment段落锚点缺陷）；1.0.0: 初始版本"
---

# DOCX 文档创建、编辑与分析

## 概述

用户可能要求你创建、编辑或分析 .docx 文件的内容。.docx 文件本质上是一个包含 XML 文件和其他资源的 ZIP 压缩包，你可以读取或编辑其中的内容。

本技能提供 **2 级技术栈**：标准流程（md2docx.py：pandoc + doc_styler）用于创建文档和内容提取，复杂流程（python-docx + OOXML）用于编辑已有文档、修订跟踪和批注。

## 输出规范

样式细节（字体/字号/配色/表格/行距/页脚）由 `doc_styler.py` 自动处理，以下仅列出 agent 在编写 Markdown 内容时需遵守的规则。

### 通用

- 正式法律交付物必须包含 AI 辅助、仅供参考、不构成正式法律意见或等价免责声明
- 合同修订版和带批注修订版正文不插入免责声明块，保持合同外观
- 禁止"保证胜诉""绝无风险""完全合规""一定合法"等绝对化法律结论
- 风险、状态、优先级不得只靠颜色表达，必须同时有文字标签
- 依据标签限定为：`[已核]` `[待核]` `[用规]` `[事实]` `[推定]` `[用户提供]` `[公开来源]`；不得临时自创或混用
- 文件名不得含 emoji；下载件采用可识别的主题和日期命名

### word-report

- 全文不得含 emoji

### word-revision

- 全文不得含 emoji
- 修订必须使用 OOXML `<w:ins>` `<w:del>` `<w:delText>` 标记，不得用"修改前/修改后"等内联文字或颜色/删除线冒充修订
- 保留原合同纸张、页边距和主体样式，不套报告品牌色

### machine-template

- 产品上传模板、法院表单不得改变字段、列序、必填标记、隐藏元数据、校验规则或官方版式
- 必须提供模板一致性或回转测试，并在发布前通过

## 技术栈分级

| 级别 | 技术 | 适用场景 | 成本 |
|------|------|----------|------|
| **标准** | pandoc + 模板 + Lua 过滤器 + doc_styler | 创建正式文档（Markdown → DOCX）、内容提取（DOCX → Markdown） | `md2docx.py` 一行命令 |
| **复杂** | Document 库 (python-docx) + OOXML | 编辑现有文档、修订跟踪、批注、DOM 级操作 | 需写 Python 脚本 |

**升级原则**：创建文档统一走标准流程（`md2docx.py`）。编辑已有文档、修订跟踪、批注、解包分析升级到 python-docx + OOXML。

## 工作流决策树

### 判断任务类型

```
用户需求
├─ 读取/分析文档内容
│   ├─ 只需文本 → read 工具直接读取
│   ├─ 需保留修订/格式 → 标准: pandoc 转 Markdown
│   └─ 需批注/结构/嵌入媒体 → 复杂: 解包 + 原始 XML 访问
│
├─ 创建新文档
│   └─ Markdown + pandoc + 模板 + doc_styler（统一标准流程，见下方"创建 Word 文档"）
│
├─ 编辑现有文档
│   ├─ .doc 文件 → 先转 .docx（见"格式转换"章节），再按下方选择
│   │
│   ├─ 自己的文档 + 简单修改（替换文本/填充占位符） → 复杂: Document 库
│   ├─ 自己的文档 + 结构性修改（增删节/改样式/操作表格） → 复杂: Document 库
│   │
│   └─ 他人的文档（需修订标记）
│       ├─ 法律/学术/商业/政府文档 → 复杂: Redlining 工作流（必须）
│       └─ 普通文档 → 复杂: Redlining 工作流（推荐）
```

## 读取和分析内容

### 从 .docx 文件提取文本（pandoc）

如果只需读取 .docx 文档的文本内容，应使用 pandoc 将文档转换为 Markdown。Pandoc 能很好地保留文档结构，并可显示修订跟踪：

```bash
# 将文档转换为 Markdown，保留修订跟踪
pandoc --track-changes=all path-to-file.docx -o output.md
# 选项：--track-changes=accept/reject/all
```

### 原始 XML 访问

以下情况需要原始 XML 访问：批注、复杂格式、文档结构、嵌入媒体和元数据。要使用这些功能，需要解包文档并读取其原始 XML 内容。

#### 解包文件

`python ooxml/scripts/unpack.py <office_file> <output_directory>`

#### 关键文件结构

- `word/document.xml` - 主文档内容
- `word/comments.xml` - document.xml 中引用的批注
- `word/media/` - 嵌入的图片和媒体文件
- 修订跟踪使用 `<w:ins>`（插入）和 `<w:del>`（删除）标签

## 格式转换：将 .doc 转换为 .docx

处理旧版 `.doc` 文件时，直接用 `read` 工具读取内容即可。如需保留原始格式编辑，请用户先将其转换为 `.docx`：

1. **在 Microsoft Word 中打开 `.doc` 文件**
2. **另存为** → 选择 `.docx` 格式
3. **上传转换后的文件** 以进行后续处理

**注意**：转换后，使用"编辑现有 Word 文档"工作流来修改生成的 `.docx` 文件。

## 创建 Word 文档（标准流程）

所有 Markdown → DOCX 创建统一走两步标准流程：**pandoc 转换（律师规范模板 + Lua 过滤器）→ doc_styler.py 样式规范化 + 交付前自检**。禁止 pandoc 裸输出直接交付。

### 一行命令（md2docx.py）

```bash
python scripts/md2docx.py input.md -o output.docx
```

`md2docx.py` 自动完成 pandoc 转换 + doc_styler 样式化 + 自检。常用参数：

| 参数 | 说明 |
|------|------|
| `-o output.docx` | 输出路径（默认同名 .docx） |
| `--profile word-report` | 样式 profile（默认），可选 `word-revision` / `none`（跳过样式化） |
| `--doc-name "报告标题"` | 页脚文档名称（默认取输入文件名） |

### doc_styler 自动覆盖项

`doc_styler.py` 的 `apply_doc_style()` 一次性完成：页面 A4/页边距、字体声明（全文宋体，含西文/CJK/复杂脚本）、字号阶梯、1.5 倍行距、标题统一黑色加粗、黑底白字表头+细灰边框+斑马纹+动态列宽分配（语义+内容分析，固定布局）、AI 免责声明、页码页脚（清除模板残留后重建）。返回空列表 = 自检通过。

### Lua 过滤器

预置过滤器在 `scripts/lua/` 下，通过 `scripts/markdown-to-docx.lua` 一键加载（md2docx.py 默认启用）：

| 过滤器 | 功能 |
|--------|------|
| `disable-ordered-list-numbering.lua` | 禁用 Pandoc 有序列表自动编号，保留 Markdown 原文序号文字 |
| `add-inline-code.lua` | 将行内代码样式独立，背景色与文字色分离 |
| `image-title-to-caption.lua` | 自动将图片 alt 标题转为 Word 图片题注 |
| `preserve_font_color.lua` | 保留 Markdown 中的字体颜色 |

> 模板采用**律师文书规范**：宋体 + 1.5 倍行距 + 首行缩进 2 字符，全文统一宋体（含西文）。doc_styler 在此基线上覆盖为最终交付样式。

### 手动分步（需要自定义时）

如需自定义模板或过滤器，手动分步执行：

```bash
# 1. pandoc 转换
pandoc input.md \
  --reference-doc=scripts/templates/template.docx \
  --lua-filter=scripts/markdown-to-docx.lua \
  -o draft.docx

# 2. doc_styler 样式化
python -c "
from docx import Document
from doc_styler import apply_doc_style
doc = Document('draft.docx')
violations = apply_doc_style(doc, 'word-report', '文档名称')
if violations:
    print('校验失败:', violations)
    exit(1)
doc.save('final.docx')
"
```

### Markdown 编写指南

对于内容优先的文档，使用语义化 Markdown：

- 标题 `#` ~ `######`
- 段落
- 无序列表和有序列表
- 基础表格
- 链接
- 引用块 `>`
- 图片（内嵌本地文件 `![](./image.png)`，pandoc 支持 PNG/JPEG/SVG）

#### 标题编号规范（律师文书）

模板的 Heading 样式已移除 `<w:numPr>`（禁止 Word 自动编号），标题序号需**在 Markdown 中手工编写**，按中国法律文书标准层级：

```
# 文档标题（不加序号）
## 一、一级标题            ← 中文数字 + 、
### （一）二级标题          ← 中文数字 + 括号
#### 1. 三级标题            ← 阿拉伯数字 + .
##### （1）四级标题          ← 阿拉伯数字 + 括号
```

> 序号由 Markdown 内容控制，不在模板里设自动编号，避免双份序号。

#### 其他补充

优先使用 Markdown 而非内嵌 HTML。仅在以下场景使用 HTML 片段：复杂表格（`colspan`/`rowspan`）、精确图片尺寸（`<img width="300">`）、自定义样式（`<div style="...">`）等 Markdown 不支持的格式。

**正式文档 Markdown 正文不得使用 emoji**。用 `[已核验]`、`[注意]`、`[高]`、`[中]`、`[低]` 等文字标签替代 ✅ ⚠️ 🔴 🟡 🟢，在生成 md 阶段即控制好。

#### 文档内锚点跳转

在标题上定义锚点 ID，正文中引用即可在 Word 中点击跳转（Ctrl+点击）：

```markdown
## 三、合同主体 {#contract-parties}

合同主体条款详见[合同主体部分](#contract-parties)，权利义务见[下文](#rights-obligations)。

### 3.1 权利义务 {#rights-obligations}
```

- 锚点 ID 必须为英文字母/数字/连字符（如 `clause-3`、`rights-obligations`），**不要用中文**
- 一个标题定义一个锚点，多处可引用同一锚点
- Pandoc 自动在目标标题处生成 Word 书签，链接处生成内部超链接

#### 脚注

使用 `[^id]` 语法插入脚注，适合标注法规依据、引用来源：

```markdown
违约金过分高于造成的损失[^1]。

[^1]: 《民法典》第585条第2款：约定的违约金过分高于造成的损失的，人民法院或者仲裁机构可以根据当事人的请求予以适当减少。
```

- 脚注自动编号，无需手动管理序号
- 脚注文本自动应用宋体 + 小字号样式
- 生成的 Word 中脚注引用为上标数字，点击可跳转到页脚脚注内容

## DOCX → Markdown 反向转换

将 `.docx` 转回 Markdown 以便编辑或归档：

```bash
# pandoc 直接转
pandoc input.docx -t markdown -o output.md

# 带修订跟踪
pandoc --track-changes=all input.docx -t markdown -o output.md
```

或使用封装脚本：

```bash
python scripts/docx2md.py input.docx output.md
```

## 复杂：编辑现有 Word 文档（Document 库）

编辑现有 Word 文档时，使用 **Document 库**（一个用于 OOXML 操作的 Python 库）。该库自动处理基础设施设置，并提供文档操作方法。对于复杂场景，可通过该库直接访问底层 DOM。

### 工作流

1. **必须 - 完整阅读文件**：从头到尾完整阅读 [`ooxml.md`](ooxml.md)（约600行）。**读取此文件时切勿设置任何范围限制。** 阅读完整内容以了解 Document 库 API 和直接编辑文档文件的 XML 模式。
2. 解包文档：`python ooxml/scripts/unpack.py <office_file> <output_directory>`
3. 使用 Document 库创建并运行 Python 脚本（参见 ooxml.md 中的"Document 库"部分）
4. 打包最终文档：`python ooxml/scripts/pack.py <input_directory> <office_file>`

Document 库既提供常用操作的高级方法，也支持通过直接 DOM 访问处理复杂场景。

## 复杂：Redlining 修订工作流（文档审阅）

此工作流允许你先用 Markdown 规划全面的修订跟踪，再在 OOXML 中实现。**关键**：要实现完整的修订跟踪，必须系统性地实现所有修改。

**批处理策略**：将相关修改分成 3-10 条一批。这使调试可控的同时保持效率。每批处理完后测试再进入下一批。

**原则：最小化精确编辑**
实现修订跟踪时，仅标记实际发生变化的文本。重复未变化的文本会使修订更难审查且显得不专业。将替换拆分为：[未变化文本] + [删除] + [插入] + [未变化文本]。对于未变化的文本，通过从原文中提取 `<w:r>` 元素并复用来保留原始 run 的 RSID。

示例 - 将句子中的 "30 days" 改为 "60 days"：

```python
# 错误 - 替换了整个句子
'<w:del><w:r><w:delText>The term is 30 days.</w:delText></w:r></w:del><w:ins><w:r><w:t>The term is 60 days.</w:t></w:r></w:ins>'

# 正确 - 仅标记变化的部分，为未变化文本保留原始 <w:r>
'<w:r w:rsidR="00AB12CD"><w:t>The term is </w:t></w:r><w:del><w:r><w:delText>30</w:delText></w:r></w:del><w:ins><w:r><w:t>60</w:t></w:r></w:ins><w:r w:rsidR="00AB12CD"><w:t> days.</w:t></w:r>'
```

### 修订跟踪工作流

1. **获取 Markdown 表示**：将文档转换为 Markdown，保留修订跟踪：

   ```bash
   pandoc --track-changes=all path-to-file.docx -o current.md
   ```

2. **识别并分组修改**：审查文档，识别所有需要修改的地方，将它们组织为逻辑批次：

   **定位方法**（用于在 XML 中查找修改位置）：
   - 章节/标题编号（如"第3.2节"、"第四条"）
   - 段落标识符（如有编号）
   - 用唯一上下文文本的 Grep 模式
   - 文档结构（如"第一段"、"签署栏"）
   - **不要使用 Markdown 行号** - 行号与 XML 结构不对应

   **批次组织**（每批 3-10 条相关修改）：
   - 按章节："批次1：第2节修订"、"批次2：第5节更新"
   - 按类型："批次1：日期修正"、"批次2：当事人名称变更"
   - 按复杂度：先处理简单文本替换，再处理复杂结构性修改
   - 按顺序："批次1：第1-3页"、"批次2：第4-6页"

3. **阅读文档并解包**：
   - **必须 - 完整阅读文件**：从头到尾完整阅读 [`ooxml.md`](ooxml.md)（约600行）。**读取此文件时切勿设置任何范围限制。** 特别关注"Document 库"和"修订跟踪模式"部分。
   - **解包文档**：`python ooxml/scripts/unpack.py <file.docx> <dir>`
   - **记录建议的 RSID**：解包脚本会建议一个用于修订跟踪的 RSID。复制此 RSID 供步骤 4b 使用。

4. **分批实现修改**：按步骤 2 的批次组织策略（按章节/类型/复杂度/顺序）在单个脚本中实现每组 3-10 条相关修改。此方法：
   - 使调试更容易（批次越小 = 越容易隔离错误）
   - 允许渐进式进展
   - 保持效率

   对于每批相关修改：

   **a. 将文本映射到 XML**：在 `word/document.xml` 中 grep 搜索文本，验证文本如何分布在 `<w:r>` 元素中。

   **b. 创建并运行脚本**：使用 `get_node` 查找节点，实现修改，然后 `doc.save()`。参见 ooxml.md 中的 **"Document 库"** 部分。

   **注意**：编写脚本前务必先 grep `word/document.xml` 获取当前行号并验证文本内容。每次脚本运行后行号会变化。

5. **打包文档**：所有批次完成后，将解包目录转换回 .docx：

   ```bash
   python ooxml/scripts/pack.py unpacked reviewed-document.docx
   ```

6. **最终验证**：确认所有修改已正确应用，无遗漏。

## 代码风格指南

**重要**：为 DOCX 操作生成代码时：

- 编写简洁代码，避免冗长的变量名和多余操作
- **Python 脚本**：避免不必要的 print 语句，用 `sys.exit(1)` 明确退出码

## 依赖

### 标准流程（md2docx.py）
- **pandoc**：`choco install pandoc`（Windows）或 `brew install pandoc`（macOS）或 `apt install pandoc`（Linux）
- **python-docx**：`pip install python-docx`（doc_styler.py / md2docx.py / docx2md.py 依赖）

### 复杂（Document 库 + OOXML 工具）
- **defusedxml**：`pip install defusedxml`（安全的 XML 解析）
- 使用前**必须**完整阅读 [`ooxml.md`](ooxml.md)
