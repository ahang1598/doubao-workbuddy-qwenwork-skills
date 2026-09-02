---
name: PDF文档处理
name_en: pdf-generation-editing-tool
version: 1.0.0
description: "PDF文档生成、美化与处理。支持从零创建精美PDF报告与表单、将Markdown/文本转换为PDF、以及PDF合并拆分、添加水印/页码、加密解密等操作。注意：纯文本提取请使用系统内置读取工具。"
category: general
---
# PDF文档处理

## Read `design/design.md` before any CREATE or REFORMAT work.

---

## Route table

| User intent                                                          | Route        | Entry point                |
| ----------------------------------------------------------------------| --------------| ----------------------------|
| Generate a new PDF from scratch (visual quality matters)             | **CREATE**   | `scripts/make.sh run`      |
| Reformat / re-style an existing document into a polished PDF         | **REFORMAT** | `scripts/make.sh reformat` |
| Operate on existing PDFs (tables/merge/split/watermark/form/encrypt) | **PROCESS**  | `scripts/processing/*.py`  |

**Rule:** when in doubt between CREATE and REFORMAT, ask whether the user has an existing document to start from. If yes → REFORMAT. If no → CREATE.
**Rule:** if the user wants to *operate on* an existing PDF (not make it beautiful), use PROCESS.
**Rule:** for plain text extraction / reading PDF content, use the system's built-in read tool (natively supports PDF + OCR) — do NOT use this skill.

---

## Route A: CREATE

Full pipeline — content → design tokens → cover → body → merged PDF.

```bash
bash scripts/make.sh run \
  --title "Q3 Strategy Review" --type proposal \
  --author "Strategy Team" --date "October 2025" \
  --accent "#2D5F8A" \
  --content content.json --out report.pdf
```

**Doc types:** `report` · `proposal` · `resume` · `portfolio` · `academic` · `general` · `minimal` · `stripe` · `diagonal` · `frame` · `editorial` · `magazine` · `darkroom` · `terminal` · `poster` · `richee`

| Type        | Cover pattern | Visual identity　　　　　　　　　　　　　　　　　　　　　　　　　|
| -------------| ---------------| ------------------------------------------------------------------|
| `report`    | `fullbleed`   | Dark bg, dot grid, Playfair Display　　　　　　　　　　　　　　　|
| `proposal`  | `split`       | Left panel + right geometric, Syne　　　　　　　　　　　　　　　 |
| `resume`    | `typographic` | Oversized first-word, DM Serif Display　　　　　　　　　　　　　 |
| `portfolio` | `atmospheric` | Near-black, radial glow, Fraunces　　　　　　　　　　　　　　　　|
| `academic`  | `typographic` | Light bg, classical serif, EB Garamond　　　　　　　　　　　　　 |
| `general`   | `fullbleed`   | Dark slate, Outfit　　　　　　　　　　　　　　　　　　　　　　　 |
| `minimal`   | `minimal`     | White + single 8px accent bar, Cormorant Garamond　　　　　　　　|
| `stripe`    | `stripe`      | 3 bold horizontal color bands, Barlow Condensed　　　　　　　　　|
| `diagonal`  | `diagonal`    | SVG angled cut, dark/light halves, Montserrat　　　　　　　　　　|
| `frame`     | `frame`       | Inset border, corner ornaments, Cormorant　　　　　　　　　　　　|
| `editorial` | `editorial`   | Ghost letter, all-caps title, Bebas Neue　　　　　　　　　　　　 |
| `magazine`  | `magazine`    | Warm cream bg, centered stack, hero image, Playfair Display　　　|
| `darkroom`  | `darkroom`    | Navy bg, centered stack, grayscale image, Playfair Display　　　 |
| `terminal`  | `terminal`    | Near-black, grid lines, monospace, neon green　　　　　　　　　　|
| `poster`    | `poster`      | White bg, thick sidebar, oversized title, Barlow Condensed　　　 |
| `richee`    | `grid`        | Richee 品牌风格——浅灰底色 + 绿色强调，遵循 course-guideline 规范 |

### 自定义封面布局（AI-Driven Layout）

你可以通过 `--pattern` 选择预设模板，或通过 `--layout-params` 生成布局 JSON 文件，由 AI 完全自主描述封面布局。渲染引擎将依次渲染 JSON 中的每个元素。

**优先原则**：`--layout-params` > `--pattern` > 类型默认 cover_pattern。

```bash
# 方式 1：显式选择预设模板
python scripts/palette.py --title "..." --type report --pattern diagonal --out tokens.json

# 方式 2：AI 生成自定义布局（核心流程）
# Step 1: AI 生成 layout.json
# Step 2:
python scripts/palette.py --title "..." --type report \
  --layout-params layout.json --accent "#C4964A" --out tokens.json
python scripts/cover.py --tokens tokens.json --out cover.pdf
```

#### 设计空间坐标系统

所有坐标基于 **794×1123** 设计空间（自动缩放到 A4）：
- 标准边距：80
- 可用内容宽度：634
- 标题区域通常位于 y ≈ 24%~42%（270~472）
- 页脚区域通常位于 y ≈ 94%~97%（1056~1087）

#### 布局元素类型（layout_params.elements）

每个元素按数组顺序从前到后渲染。

| type | 说明 | 必填字段 |
|---|---|---|
| `rect` | 填充矩形 | `x, y, w, h, color, opacity?` |
| `line` | 直线 | `x1, y1, x2, y2, color, width?, opacity?` |
| `text` | 单行文本 | `x, y, text, font, size, color, align?, opacity?` |
| `text_block` | 多行自动换行文本块（CJK 逐字/拉丁逐词） | `x, y, text, font, size, color, max_w, line_h?, opacity?` |
| `dot_grid` | 装饰性圆点网格 | `x, y, cols, rows, gap, r, color, opacity?` |
| `polygon` | 填充多边形 | `points: [[x,y],...], color, opacity?` |
| `bracket` | 角括号（左上+右上+左下） | `x, y, w, h, color, width?` |

- `font`: `"display"` 或 `"body"`
- `align`（text/text_block）: `"start"` / `"middle"` / `"end"`
- `line_h`: 行高（pt），默认 `size * 1.4`
- opacity: 0.0~1.0

#### 模板变量

元素中的字符串值使用 `{变量名}` 语法，执行时会被替换为 tokens 中对应值：

| 变量　　　　　 | 含义　　　　　　　　　　　　| 示例值　　　　 |
| ----------------| -----------------------------| ----------------|
| `{title}`　　　| 标题文本　　　　　　　　　　| "Q3 战略回顾"　|
| `{subtitle}`　 | 副标题　　　　　　　　　　　| "市场分析报告" |
| `{author}`　　 | 作者　　　　　　　　　　　　| "战略团队"　　 |
| `{date}`　　　 | 日期　　　　　　　　　　　　| "2026年7月"　　|
| `{doc_type}`　 | 文档类型　　　　　　　　　　| "报告"　　　　 |
| `{accent}`　　 | 强调色（Richee 品牌绿）　　 | "#029856"　　　|
| `{accent_lt}`　| 强调色浅色变体　　　　　　　| "#12B76A"　　　|
| `{cover_bg}`　 | 封面背景色（Richee 浅色底） | "#F6F7F9"　　　|
| `{text_light}` | 封面主文字色（纯黑） | "#000000"　　　　|
| `{page_bg}`　　| 正文背景色　　　　　　　　　| "#FAFAF8"　　　|
| `{dark}`　　　 | 深色　　　　　　　　　　　　| "#0A0C14"　　　|
| `{muted}`　　　| 弱化文本色　　　　　　　　　| "#888888"　　　|
| `{body_text}`　| 正文字色　　　　　　　　　　| "#2A2A2A"　　　|

#### 布局示例（fullbleed 风格）

参见 `design/samples/` 目录下的 `fullbleed.json`。

Cover extras (inject into tokens via `--abstract`, `--cover-image`):
- `--abstract "text"` — abstract text block on the cover (magazine/darkroom)
- `--cover-image "url"` — hero image URL/path (magazine, darkroom, poster)

**Color overrides — always choose these based on document content:**
- `--accent "#HEX"` — override the accent color; `accent_lt` is auto-derived by lightening toward white
- `--cover-bg "#HEX"` — override the cover background color

**Accent color selection guidance:**

Richee 品牌要求绿色系为唯一彩色强调色，禁止引入蓝色、紫色、橙色等其他彩色系。accent 色必须从以下绿色色板中选择：

| 层级 | HEX | 使用场景 |
|------|-----|---------|
| 深绿（主强调） | `#029856` | 默认 accent，用于 section rules、callout bars、table headers |
| 中绿 | `#039855` | 次级强调元素 |
| 标准绿 | `#12B76A` | 默认 accent\_lt（浅色变体）、图标、步骤数字 |
| 亮绿 | `#6EE7A8` | 背景装饰、渐变端色 |
| 极浅绿（背景） | `#F0FFF4` | 卡片绿色背景 |

**Rule:** 绿色是 Richee 唯一的彩色强调色。封面与正文必须使用同一套配色方案，由 `palette.py` 统一产出 `tokens.json` 定义。

**content.json block types:**

| Block | Usage | Key fields |
|---|---|---|
| `h1` | Section heading + accent rule | `text` |
| `h2` | Subsection heading | `text` |
| `h3` | Sub-subsection (bold) | `text` |
| `body` | Justified paragraph; supports `<b>` `<i>` markup | `text` |
| `bullet` | Unordered list item (• prefix) | `text` |
| `numbered` | Ordered list item — counter auto-resets on non-numbered blocks | `text` |
| `callout` | Highlighted insight box with accent left bar | `text` |
| `table` | Data table — accent header, alternating row tints | `headers`, `rows`, `col_widths`?, `caption`? |
| `image` | Embedded image scaled to column width | `path`/`src`, `caption`? |
| `figure` | Image with auto-numbered "Figure N:" caption | `path`/`src`, `caption`? |
| `code` | Monospace code block with accent left border | `text`, `language`? |
| `math` | Display math — LaTeX syntax via matplotlib mathtext | `text`, `label`?, `caption`? |
| `chart` | Bar / line / pie chart rendered with matplotlib | `chart_type`, `labels`, `datasets`, `title`?, `x_label`?, `y_label`?, `caption`?, `figure`? |
| `flowchart` | Process diagram with nodes + edges via matplotlib | `nodes`, `edges`, `caption`?, `figure`? |
| `bibliography` | Numbered reference list with hanging indent | `items` [{id, text}], `title`? |
| `divider` | Accent-colored full-width rule | — |
| `caption` | Small muted label | `text` |
| `pagebreak` | Force a new page | — |
| `spacer` | Vertical whitespace | `pt` (default 12) |

**chart / flowchart schemas:**
```json
{"type":"chart","chart_type":"bar","labels":["Q1","Q2","Q3","Q4"],
 "datasets":[{"label":"Revenue","values":[120,145,132,178]}],"caption":"Q results"}

{"type":"flowchart",
 "nodes":[{"id":"s","label":"Start","shape":"oval"},
          {"id":"p","label":"Process","shape":"rect"},
          {"id":"d","label":"Valid?","shape":"diamond"},
          {"id":"e","label":"End","shape":"oval"}],
 "edges":[{"from":"s","to":"p"},{"from":"p","to":"d"},
          {"from":"d","to":"e","label":"Yes"},{"from":"d","to":"p","label":"No"}]}

{"type":"bibliography","items":[
  {"id":"1","text":"Author (Year). Title. Publisher."}]}
```

---

## Route B: REFORMAT

Parse an existing document → content.json → CREATE pipeline.

```bash
bash scripts/make.sh reformat \
  --input source.md --title "My Report" --type report --out output.pdf
```

**Supported input formats:** `.md` `.txt` `.pdf` `.json`

---

## Route C: PROCESS

Operate on existing PDFs — tables, merge, split, watermark, forms, encrypt, etc.
All scripts are in `scripts/processing/`.

> **Text extraction / reading PDF content:** use the system's built-in read tool (natively supports PDF + OCR). This skill does NOT handle plain text extraction.

### Table Extraction

Use pdfplumber directly (no dedicated script). See `reference.md` for examples.

```python
import pdfplumber
with pdfplumber.open("document.pdf") as pdf:
    for page in pdf.pages:
        tables = page.extract_tables()
        for table in tables:
            for row in table:
                print(row)
```

### Merge / Split / Rotate / Watermark / Encrypt

Use pypdf directly. See `reference.md` for full examples. Quick reference:

| Task | Library | Key API |
|---|---|---|
| Merge PDFs | pypdf | `PdfWriter().add_page(page)` |
| Split PDF | pypdf | One page per `PdfWriter` |
| Rotate pages | pypdf | `page.rotate(90)` |
| Add watermark | pypdf | `page.merge_page(watermark_page)` |
| Password protect | pypdf | `writer.encrypt("password")` |
| Extract metadata | pypdf | `reader.metadata` |

### Create Simple PDF (with Chinese text)

> ⛔ **创建含中文的 PDF 时，必须调用 `scripts/processing/create_pdf.py`，禁止自行用 reportlab 实现。**
> 脚本已内置中文字体嵌入（STSong-Light CID 字体），自行实现会导致中文乱码（黑色方块）。

```bash
# From text content
python scripts/processing/create_pdf.py output.pdf "长恨歌内容..." "长恨歌"

# From file
python scripts/processing/create_pdf.py output.pdf @content.txt "长恨歌"
```

### Form Filling

**If you need to fill out a PDF form, read `forms.md` and follow its instructions.**

The form filling workflow has two paths depending on whether the PDF has fillable form fields:

**Step 1 — Check if fillable:**
```bash
python scripts/processing/check_fillable_fields.py <input.pdf>
```

**Fillable fields path:**
1. `extract_form_field_info.py` → get field structure JSON
2. `convert_pdf_to_images.py` → render pages to PNG for visual analysis
3. Create `field_values.json` with values to enter
4. `fill_fillable_fields.py` → produce filled PDF

**Non-fillable fields path:**
1. `convert_pdf_to_images.py` → render pages to PNG
2. Visually determine bounding boxes for each field
3. Create `fields.json` with bounding box data
4. `create_validation_image.py` → generate validation images for review
5. `check_bounding_boxes.py` → verify no overlaps
6. `fill_pdf_form_with_annotations.py` → produce filled PDF

> ⛔ **严禁自行编写 PDF 填充代码。必须调用脚本，脚本已内置中文字体嵌入。**

See `reference.md` for detailed examples of all libraries and tools.

---

## 输出规范

本技能遵循 **Richee 输出规范 1.2.0**，按严重程度分为三级：**GATE**（发布阻断，不满足则禁止发布）、**REQUIRED**（强制要求，验收失败但可修复）、**RECOMMENDED**（建议项，偏离需说明理由）。

### 全部 Profile 共同遵守（GATE）

正式 PDF 全文不得含 emoji；风险等级、状态、优先级等语义信息必须同时使用文字标签和颜色表达，禁止仅靠颜色区分。禁止出现保证胜诉、绝无风险、完全合规、一定合法等绝对化法律结论。依据标签必须由目标技能声明封闭集合，运行时不得自创或混用标签体系。

### 全部 Profile 共同遵守（REQUIRED）

输出文件名不含 emoji，采用可识别的"主题\_日期"格式，如 `Q3战略回顾_20260715.pdf`。

### pdf-report（CREATE / REFORMAT 精美报告 PDF）专属

**GATE：** PDF 默认 A4 页面（210mm × 297mm），正文页边距≥2cm，封面全幅无边距；导出后须检查封面和内容页完整性。PDF 含中文时必须使用 CJK 字体（STSong-Light CID 或等效 Unicode CID 字体），中文不得渲染为方块、乱码或空白——`render_body.py` 已内置 CJK 自动检测与字体切换，严禁绕过脚本自行实现。封面必须成功渲染且与正文合并，`merge.py` 会输出合并 QA 信息用于验证。

**REQUIRED：** 正文内容块（h1/h2/h3/body/table/chart/image 等）不得出现文本截断、跨页破坏或重叠；复杂页面（表格页、图表页、带大量内容的 h1 后正文页）应抽查确认无空白页、无截断。表格表头使用 accent 色底色 + 白字，数据行使用交替底色确保可读性，列宽按 `col_widths` 分配，禁止默认等宽。配色（accent / accent\_lt / cover\_bg）和字体（封面 Google Fonts + 正文 ReportLab 系统字体 / CJK 字体）必须由 `palette.py` 统一产出的 `tokens.json` 定义，封面与正文不得使用不同的配色方案。

**RECOMMENDED：** 若输出为法律/金融/合同类文档，建议在封面或正文首页包含"本文件由AI辅助生成，仅供参考"免责声明。

### pdf-form（表单填写）专属（GATE）

PDF 含中文时必须使用 STSong-Light CID 字体，`fill_fillable_fields.py` 和 `fill_pdf_form_with_annotations.py` 已内置 CJK 字体嵌入。表单填写后字段值不得超出边界框、不得覆盖已有文本、不得出现重叠，填写完成后必须通过 `scripts/processing/check_bounding_boxes.py` 验证。

### pdf-simple（create_pdf.py 简单 PDF）专属（GATE）

PDF 含中文时必须使用 `scripts/processing/create_pdf.py` 生成，不得自行用 reportlab 实现。脚本已内置 STSong-Light CID 字体嵌入，自行实现会导致中文乱码。

### pdf-merged（合并/拆分/水印等操作结果）专属（GATE）

仅继承通用 GATE 中"全文禁止 emoji"的要求。

---

## Environment

```bash
bash scripts/make.sh check   # verify all deps
bash scripts/make.sh fix     # auto-install missing deps
bash scripts/make.sh demo    # build a sample PDF
```

### CREATE / REFORMAT dependencies

| Tool | Used by | Install |
|---|---|---|
| Python 3.9+ | all `.py` scripts | system |
| `reportlab` | `render_body.py` | `pip install reportlab` |
| `pypdf` | merge, reformat | `pip install pypdf` |
| `matplotlib` | math/chart/flowchart blocks | `pip install matplotlib` |

### PROCESS dependencies

| Tool         | Used by                                              | Install                  |
| --------------| ------------------------------------------------------| --------------------------|
| `pdfplumber` | table extraction                                     | `pip install pdfplumber` |
| `pypdf`      | merge/split/rotate/watermark/encrypt/forms           | `pip install pypdf`      |
| `reportlab`  | `create_pdf.py`, `fill_pdf_form_with_annotations.py` | `pip install reportlab`  |
| `pymupdf`    | `convert_pdf_to_images.py`                           | `pip install pymupdf`    |
| `Pillow`     | `create_validation_image.py`                         | `pip install Pillow`     |
