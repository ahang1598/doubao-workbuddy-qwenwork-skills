---
name: Word文档处理
name_en: word-document-processing
description: "Word文档创建、编辑和分析，支持修订跟踪、批注、格式保留。内置律师规范Pandoc模板（宋体+首行缩进）+Lua过滤器，Markdown一键转DOCX。适用于创建正式文档、合同修订、内容提取等任务。"
category: general
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

| 级别　　 | 技术　　　　　　　　　　　　　　　　　　| 适用场景　　　　　　　　　　　　　　　　　　　　　　　　　　 | 成本　　　　　　　　　|
| ----------| -----------------------------------------| --------------------------------------------------------------| -----------------------|
| **标准** | pandoc + 模板 + Lua 过滤器 + doc_styler | 创建正式文档（Markdown → DOCX）、内容提取（DOCX → Markdown） | `md2docx.py` 一行命令 |
| **复杂** | Document 库 (python-docx) + OOXML　　　 | 编辑现有文档、修订跟踪、批注、DOM 级操作　　　　　　　　　　 | 需写 Python 脚本　　　|

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

> 以下命令需在 skill 根目录（含 `ooxml/` 子目录的目录）下执行，不是 `scripts/` 子目录。

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

> **工作目录约定**：本技能所有命令的相对路径都以 **skill 根目录**为基准（即 `SKILL.md` 所在目录），不是 `scripts/` 子目录。执行命令前请 `cd` 到 skill 根目录，例如 `cd "C:/Users/<用户名>/AppData/Roaming/RicheeAI/SKILLs/custom/Word文档处理"`。

### 一行命令（md2docx.py）

```bash
python scripts/md2docx.py input.md -o output.docx
```

`md2docx.py` 自动完成 pandoc 转换 + doc_styler 样式化 + 自检。常用参数：

| 参数　　　　　　　　　　　　　　| 说明　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　　|
| ---------------------------------| -------------------------------------------------------------------|
| `-o output.docx`　　　　　　　　| 输出路径（默认同名 .docx）　　　　　　　　　　　　　　　　　　　　|
| `--profile word-report`　　　　 | 样式 profile（默认），可选 `word-revision` / `none`（跳过样式化） |
| `--doc-name "报告标题"`　　　　 | 页脚文档名称（仅 `name-page` / `name-page-of-total` 页脚格式需要） |
| `--footer-format page-of-total` | 页脚格式（见下表，默认 `page-of-total`）　　　　　　　　　　　　　|

##### 页脚格式

| 值 | 效果 | 示例 |
|----|------|------|
| `page-only` | 仅页码 | `3` |
| `name-page` | 文档名 + 页码 | `审查意见书  \|  3` |
| `page-of-total` | 页码 / 总页数（默认） | `3 / 12` |
| `name-page-of-total` | 文档名 + 页码 / 总页数 | `审查意见书  \|  3 / 12` |
| `none` | 无页脚 | — |

### 样式规范

`md2docx.py` 自动应用律师文书规范：宋体（含西文/CJK/复杂脚本统一）+ 1.5 倍行距 + 首行缩进 2 字符、标题统一黑色加粗、表头黑色加粗 + 细灰边框 + 动态列宽分配、AI 免责声明、页码页脚。返回空列表 = 自检通过。

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
- **表格（必须用 HTML `<table>` 语法，见下方"HTML 合并单元格表格"）**
- 链接
- 引用块 `>`
- 图片（内嵌本地文件 `![](./image.png)`，pandoc 支持 PNG/JPEG/SVG）
- 其他 HTML 片段（精确图片尺寸 `<img width="300">`、自定义样式 `<div style="...">`）仅在 Markdown 不支持时使用

**正式文档 Markdown 正文不得使用 emoji**。用 `[已核验]`、`[注意]`、`[高]`、`[中]`、`[低]` 等文字标签替代 ✅ ⚠️ 🔴 🟡 🟢，在生成 md 阶段即控制好。

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

#### 填空项与下划线

法律文档常含填空项（甲方名称、签署日期、签章位置、合同金额等），需保留下划线格式。Pandoc 原生支持 `<u>` 标签生成 Word 下划线，样式处理不会覆盖。

##### 语法

| 场景　　　　 | 写法　　　　　　　　　　　　　　　　　　　　　 | 说明　　　　　　　　　　　　　　|
| --------------| ------------------------------------------------| ---------------------------------|
| 已填写内容　 | `<u>北京某某科技有限公司</u>`　　　　　　　　　| 内容保留下划线　　　　　　　　　|
| 空白填空线　 | `<u>　　　</u>`　　　　　　　　　　　　　　　　| 全角空格 + 下划线，视觉为空白线 |
| 全角下划线　 | `＿＿＿＿`　　　　　　　　　　　　　　　　　　 | 直接用全角下划线字符　　　　　　|
| 红色空缺标识 | `<u><span style="color:red">待填写</span></u>` | 未填写项标红提醒　　　　　　　　|

##### 示例

```markdown
**甲方**：<u>北京某某科技有限公司</u>
**乙方**：<u><span style="color:red">待填写</span></u>

签署日期：2026 年<u>　　</u>月<u>　　</u>日
签署地点：<u>　　　　　　　　</u>

法定代表人：＿＿＿＿＿＿　联系电话：＿＿＿＿＿＿
```

##### 适用场景

- 合同主体信息（甲方/乙方名称、地址、法定代表人）
- 签署信息（日期、地点、签章位置）
- 金额、期限等可变条款

> **注意**：`<u>` 标签与全角下划线 `＿` 可混用，但同一文档内建议统一风格。红色空缺标识仅用于未填写项，填写后应移除红色样式。
>
> **表格填空例外**：表格单元格内的填空项**不需要下划线**。表格本身有边框线，下划线会造成视觉冗余。直接写内容或留空即可：`<td>待填写</td>` 或 `<td></td>`。

#### 表格

**文档中所有表格统一使用 HTML `<table>` 语法**，不使用标准 Markdown 表格（`|...|...|` 语法）。HTML 表格是 Markdown 表格的超集，支持合并单元格、列宽控制、单元格对齐等所有场景。

##### 基本语法与合并单元格

用 `colspan` 跨列合并（`rowspan` 跨行支持有限，建议改用重复文本或调整结构）：

```markdown
<table>
<tr>
  <th>条款编号</th>
  <th>原条文内容</th>
  <th>修改后内容</th>
  <th>修改说明</th>
</tr>
<tr>
  <td>第12条</td>
  <td>合同期限为一年</td>
  <td>合同期限为三年</td>
  <td>延长合作周期</td>
</tr>
<tr>
  <td colspan="4"><strong>备注：</strong>以上修改自2026年1月1日起生效。</td>
</tr>
</table>
```

##### 属性支持

| 属性                        | 支持 | 说明                                                                 |
| --------------------------- | :--: | -------------------------------------------------------------------- |
| `colspan`（跨列）           | 完全 | 正确生成 `w:gridSpan`                                                |
| `rowspan`（跨行）           | 部分 | 用空单元格替代 `w:vMerge`，视觉近似但非真正跨行合并                  |
| `style="width:N%"`（列宽） | 完全 | 第一行所有 `<th>`/`<td>` 都指定百分比时，跳过 `doc_styler` 动态计算  |
| `align`（对齐）             | 完全 | 见下方"单元格对齐"                                                   |

##### 列宽指定

默认 `doc_styler.py` 根据内容长度动态计算列宽。如需精确控制，在**第一行**所有 `<th>`/`<td>` 上用 `style="width:NN%"` 指定百分比：

```markdown
<table>
<tr>
  <th style="width:30%">项目</th>
  <th style="width:35%">招标人</th>
  <th style="width:35%">招标代理机构</th>
</tr>
<tr>
  <td>1</td>
  <td>甲方</td>
  <td>代理</td>
</tr>
</table>
```

**规则**：
- 必须覆盖第一行**所有列位**（缺一不可，否则回退动态计算）
- 只支持百分比（`width:30%`），不支持 `px`/`em`
- 比例总和接近 100%（容差 ±5%）
- 含 `colspan` 的表头：`width` 按 `colspan` 平均分配（如 `colspan="2" style="width:40%"` 等价每列 20%）
- 适用：招标书/合同附件等有标准列宽要求的表格，或需避免窄列被挤压的场景

##### 单元格对齐

在 `<td>` / `<th>` 上使用 HTML `align` 属性：

```html
<td align="center">内容</td>
<td align="left">内容</td>
<td align="right">内容</td>
```

支持值：`center`、`left`、`right`。未指定时默认左对齐。

> **注意**：表格对齐用 `align` 属性，**不要**用标准 Markdown 表格语法（`| :---: |`）——本技能所有表格统一用 HTML `<table>`。

#### 段落对齐

段落对齐与表格对齐独立，通过 **Fenced Div + class** 控制段落左/中/右/两端对齐：

```markdown
::: {.text-center}
居中的标题或正文
:::

::: {.text-right}
右对齐的署名或日期
:::
```

| Class           | 对齐方式   | 典型场景                       |
| --------------- | ---------- | ------------------------------ |
| `.text-center`  | 居中       | 标题、副标题、署名区           |
| `.text-right`   | 右对齐     | 日期、签名、页码               |
| `.text-left`    | 左对齐     | 正文（默认，一般无需显式使用） |
| `.text-justify` | 两端对齐   | 法律文书正文、长段落（标准格式）|

**规则**：
- **`:::` 标记必须独占一行，且与前面的块之间留空行**。两种常见错误写法都会失效：① 写在段落文字中间；② 紧跟在段落文字行之后（无空行）——这两种情况下 pandoc 都会把 `:::` 吞进前一个段落当普通文本，对齐不生效（仅标题等块级元素之后可紧跟无空行）
- 每个 Fenced Div 可包含多个段落，所有段落统一应用该对齐
- 支持嵌套：外层 Div 的对齐会透传到内层无对齐属性的 Div
- 与 `.no-indent` / `.indent` 等缩进 class 可共存于同一 Div
- 与其他 class 共存时，仅提取对齐相关 class，其余保留
- 不可与表格对齐混用（表格用 `align` 属性）

#### 首行缩进控制

模板默认正文段落首行缩进 2 字符。署名区、日期、引用块等场景需取消缩进时，通过 **Fenced Div + class** 控制：

```markdown
:::: {.no-indent}
甲方：北京某某科技有限公司
签署日期：2026 年 8 月 13 日
::::
```

| Class        | 效果             | 典型场景               |
| ------------ | ---------------- | ---------------------- |
| `.no-indent` | 取消首行缩进     | 署名、日期、引用块     |
| `.indent`    | 强制首行缩进 2 字 | 覆盖 `no-indent` 嵌套 |

**规则**：
- **`:::` 标记必须独占一行，且与前面的块之间留空行**。两种常见错误写法都会失效：① 写在段落文字中间；② 紧跟在段落文字行之后（无空行）——这两种情况下 pandoc 都会把 `:::` 吞进前一个段落当普通文本，缩进不生效（仅标题等块级元素之后可紧跟无空行）
- 与 `.text-center` / `.text-right` 等对齐 class 可共存于同一 Div
- 支持嵌套：外层 `.no-indent` 透传到内层无缩进属性的 Div
- 仅作用于段落（`Para`/`Plain`），表格/列表/标题不受影响

#### 分页符

法律文档常需在附件、签署栏、附录、独立说明页等位置强制分页（**模板的 Heading 样式未配置自动分页**，章节标题不会自动新起一页）。下列任一写法（**独立成行，前后必须空行**）会被自动识别并转换为 Word 分页符：

##### 写法

| 写法　　　　　　　 | 示例　　　　　　　　　　　　　　　　　　　　　　| 适用场景　　　　　　　|
| --------------------| -------------------------------------------------| -----------------------|
| 反斜杠命令　　　　 | `\newpage`　　　　　　　　　　　　　　　　　　　| 简洁，推荐 agent 生成 |
| raw HTML（after）　| `<div style="page-break-after: always"></div>`　| 兼容 HTML 约定　　　　|
| raw HTML（before） | `<div style="page-break-before: always"></div>` | 等价变体　　　　　　　|

##### 示例

```markdown
# 合同正文

（正文内容）

\newpage

# 附件一：标的物清单

（附件内容）

<div style="page-break-after: always"></div>

# 签署栏

甲方：________________
```

##### 注意

- **前后必须空行**，否则 pandoc 会将 `\newpage` 当作行内文本，将 `<div>` 当作行内 HTML 处理
- 三种写法等价，同一文档内建议统一风格
- **不要把 `---` 当作分页符**——`---` 是水平线（见下方"水平线"章节），不会分页；强制分页请用上述三种写法
- 模板未给 Heading 1 配置 `pageBreakBefore`，章节标题不会自动分页——**如需"每个章节独立成页"，必须在每个章节标题前显式加分页符**；如希望所有 H1 自动分页，可在 `scripts/templates/template.docx` 的 Heading 1 样式里加 `<w:pageBreakBefore/>`

#### 水平线（`---`）

Markdown 的 `---` 在标准语法中是水平线（horizontal rule），但 Pandoc 默认把它渲染为 VML `<v:rect o:hr="t"/>` 水平线对象，在 Word 中显示为可见横线，视觉突兀。

**处理策略**：`md2docx.py` 自动把 `---` 转为带上下间距的空段落（保留视觉分隔感，无可见横线）。

**使用建议**：

- 在 markdown 中可放心使用 `---` 作为章节间的视觉分隔，Word 输出为间距，不会出现横线
- 如果确实需要分页，**不要**用 `---`，应使用 `\newpage`（见上方"分页符"章节）
- 如果需要可见分隔线（如合同附件清单的视觉断点），用 `<u>　　　　　　　　</u>`（下划线空格）或表格整行单元格替代

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

将 `.docx` 转回 Markdown 以便编辑或归档。

### 一行命令（docx2md.py）

```bash
# cwd = skill 根目录
python scripts/docx2md.py input.docx -o output.md
```

**常用参数**：

| 参数 | 默认 | 说明 |
|------|------|------|
| `-o, --output` | `<input>.md` | 输出路径 |
| `--media-dir` | `./assets` | 提取的图片目录 |
| `--to` | `gfm` | pandoc 输出格式（`gfm` / `markdown` / `commonmark` 等） |
| `--wrap` | `none` | 换行模式（`none` / `auto` / `preserve`） |
| `--` 后参数 | — | 透传给 pandoc，例如 `--track-changes=all` |

### 修订跟踪处理

如果 docx 含修订跟踪（`<w:ins>` / `<w:del>`），需要通过 `--` 透传 pandoc 参数控制如何呈现：

```bash
# 接受所有修订后转换（默认行为，输出最终态）
python scripts/docx2md.py input.docx -o output.md

# 保留修订标记（含 ~~删除线~~ 和 [新增]{.ins} 等标记）
python scripts/docx2md.py input.docx -o output.md -- --track-changes=all

# 拒绝所有修订后转换（输出原始态）
python scripts/docx2md.py input.docx -o output.md -- --track-changes=reject
```

`--track-changes` 取值：`accept`（默认）/ `all` / `reject`。

### 直接用 pandoc（无封装）

如果不需要 docx2md.py 的封装（图片提取、参数透传），可直接调 pandoc：

```bash
pandoc input.docx -t markdown -o output.md
pandoc --track-changes=all input.docx -t markdown -o output.md
```

### 注意事项

- 标题中的 `<w:b/>` 属性会被 pandoc 解析为 `**...**` 加粗标记（模板 Heading 样式自带 bold），转换后可能看到 `# **标题**` 这种形式，可手动去掉 `**`
- `gfm` 格式比 pandoc 原生 `markdown` 更通用，但表格语法略不同；如需保留 pandoc 扩展语法用 `--to markdown`
- 图片会被提取到 `--media-dir` 指定目录，markdown 中以相对路径引用

## 高级编辑（按需阅读）

> 以下场景仅在**编辑现有 Word 文档**或执行 **Redlining 修订跟踪**时需要，新建文档无需参考。
> 详细工作流请查阅 [`advanced-editing.md`](advanced-editing.md)。

| 场景 | 说明 | 入口 |
|------|------|------|
| 编辑现有文档 | 使用 Document 库修改已有 .docx | [编辑现有 Word 文档](advanced-editing.md#复杂：编辑现有-word-文档document-库) |
| Redlining 修订 | 带修订跟踪的文档审阅工作流 | [Redlining 修订工作流](advanced-editing.md#复杂：redlining-修订工作流文档审阅) |

## 代码风格指南

**重要**：为 DOCX 操作生成代码时：

- 编写简洁代码，避免冗长的变量名和多余操作
- **Python 脚本**：避免不必要的 print 语句，用 `sys.exit(1)` 明确退出码

## 依赖

### 标准流程（md2docx.py）
- **python-docx**：`pip install python-docx`（doc_styler.py / md2docx.py / docx2md.py 依赖）

### 复杂（Document 库 + OOXML 工具）
- **defusedxml**：`pip install defusedxml`（安全的 XML 解析）
- 使用前**必须**完整阅读 [`ooxml.md`](ooxml.md)
