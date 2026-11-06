---
name: xiaoyi-pdf-win
post_process: aigc-marker-win
description: >
  PDF 综合处理技能，处理文档生成、编辑、安全与解析。
  适用情形：
  1. 创建与排版：从零生成报告、提案、简历等 PDF，或对现有文档重新排版美化；
  2. 表单与水印：自动填写 PDF 表单字段，或添加文字/图片水印（如打水印、标机密）；
  3. 页面管理：合并多个 PDF，或拆分、提取指定页码；
  4. 安全控制：为 PDF 添加密码（加密）或移除密码（解密）；
  5. 内容提取：从 PDF 中提取纯文本或导出表格数据。
  只要用户诉求涉及生成、排版、美化、转换、拼接、拆分 PDF，或处理水印、表单、密码，必须触发本技能。
metadata:
  version: "1.2"
  category: document-generation
---

# xiaoyi-pdf

Four tasks. One skill.

## Output convention

- Run commands from the current task workspace; never `cd` into the Skill directory.
- Refer to scripts with the absolute Skill path and pass an absolute workspace path to every `--out`/`--outdir` option.
- Final output names must be specific to the task. Never reuse a generic `output.pdf` from another task.
- Keep temporary render files in the scripts' system-temp directories. Put only final PDF/TXT/XLSX/CSV artifacts in the task workspace.
- After validation and AIGC marking, call `send_file_to_user(abs_file_path_list=["<absolute output path>"])`. Do not merely print a local path.

## ⚠️ CREATE job isolation (mandatory)

Each CREATE request must own one UUID job. Different chats—and multiple PDF
requests in the same chat—must never share `content.json` or infer a "latest"
job.

1. Initialize a job before writing content:

   ```bash
   bash "{baseDir}/scripts/make.sh" init
   ```

   Save the returned `PDF_JOB_ID` in the agent conversation context. The
   returned `PDF_CONTENT_PATH` is inside
   `%TEMP%/xiaoyi_pdf/<PDF_JOB_ID>/content.json`.

2. Every later `exec` must restore that exact job explicitly:

   ```bash
   eval "$(bash "{baseDir}/scripts/make.sh" session --session-id "<PDF_JOB_ID>")"
   ```

   Never use a global/current/latest job, and never assume exported variables
   survive across `exec` calls.

3. Write generated blocks to the restored absolute `PDF_CONTENT_PATH`. Do not
   write `$PWD/content.json` for CREATE work.

4. Build by ID; do not also pass `--content`:

   ```bash
   bash "{baseDir}/scripts/make.sh" run \
     --session-id "<PDF_JOB_ID>" \
     --title "Q3 Strategy Review" --type proposal \
     --out "$PWD/q3-strategy-review.pdf"
   ```

`run` snapshots the job content into a new private render directory before it
starts. Final merge uses an exclusive output lock and atomic replacement, so a
second job targeting the same PDF fails clearly instead of overwriting it.

REFORMAT parses its source inside one isolated invocation and does not need a
CREATE job ID. Other routes take explicit input/output paths and must still use
task-specific absolute output names.

## Read `design/design.md` before any CREATE or REFORMAT work.

---

## Route table

| User intent                                    | Route              | Scripts used                                                                           |
| ---------------------------------------------- | ------------------ | -------------------------------------------------------------------------------------- |
| Generate a new PDF from scratch                | **CREATE**         | `palette.py` → `cover.py` → `render_cover.py` → `render_body.py` → `merge.py`          |
| Fill / complete form fields in an existing PDF | **FILL**           | `fill_inspect.py` → `fill_write.py`                                                    |
| Reformat / re-style an existing document       | **REFORMAT**       | `reformat_parse.py` → then full CREATE pipeline                                        |
| Add watermark to an existing PDF               | **WATERMARK**      | `watermark_cli.py` → `watermark_text.py` / `watermark_image.py` / `watermark_merge.py` |
| Merge multiple PDFs                            | **MERGE**          | `make.sh merge`                                                                        |
| Split PDF into pages / ranges                  | **SPLIT**          | `make.sh split`                                                                        |
| Encrypt PDF with password                      | **ENCRYPT**        | `make.sh encrypt`                                                                      |
| Decrypt PDF with password                      | **DECRYPT**        | `make.sh decrypt`                                                                      |
| Extract text to .txt                           | **EXTRACT-TEXT**   | `make.sh extract-text`                                                                 |
| Extract tables to Excel/CSV                    | **EXTRACT-TABLES** | `make.sh extract-tables`                                                               |

**Rule:** when in doubt between CREATE and REFORMAT, ask whether the user has an existing document to start from. If yes → REFORMAT. If no → CREATE.

---

## ⚠️ 重要注意事项

### AIGC 标识（必须）

**所有生成的 PDF 文档必须添加 AIGC 标识。** 在文档生成/编辑完成并校验通过后，**立即调用预装的 `aigc-marker-win` skill**：

```
使用 aigc-marker-win 为 output.pdf 添加 AIGC 标识
```

**规则：**

- 这是合规要求，**不可跳过**
- `aigc-marker-win` 是独立预装 Skill；本 Skill 不复制、不安装它。如果运行环境不可用，必须明确提示缺少依赖，不能将未标识的 PDF 作为最终文件交付
- 在 PDF 生成并通过检查后调用 `aigc-marker-win`，看到 `AIGC_MARKER_OK` 后再调用 `send_file_to_user(abs_file_path_list=["<absolute output path>"])`
- 支持批量：可为整个目录的 PDF 添加标识

## Route A: CREATE

Full pipeline — content → design tokens → cover → body → merged PDF.

```bash
bash "{baseDir}/scripts/make.sh" run \
  --session-id "<PDF_JOB_ID>" \
  --title "Q3 Strategy Review" --type proposal \
  --author "Strategy Team" --date "October 2025" \
  --accent "#2D5F8A" \
  --out "$PWD/q3-strategy-review.pdf"
```

**Doc types:** `report` · `proposal` · `resume` · `portfolio` · `academic` · `general` · `minimal` · `stripe` · `diagonal` · `frame` · `editorial` · `magazine` · `darkroom` · `terminal` · `poster`

| Type        | Cover pattern | Visual identity                                             |
| ----------- | ------------- | ----------------------------------------------------------- |
| `report`    | `fullbleed`   | Dark bg, dot grid, Playfair Display                         |
| `proposal`  | `split`       | Left panel + right geometric, Syne                          |
| `resume`    | `typographic` | Oversized first-word, DM Serif Display                      |
| `portfolio` | `atmospheric` | Near-black, radial glow, Fraunces                           |
| `academic`  | `typographic` | Light bg, classical serif, EB Garamond                      |
| `general`   | `fullbleed`   | Dark slate, Outfit                                          |
| `minimal`   | `minimal`     | White + single 8px accent bar, Cormorant Garamond           |
| `stripe`    | `stripe`      | 3 bold horizontal color bands, Barlow Condensed             |
| `diagonal`  | `diagonal`    | SVG angled cut, dark/light halves, Montserrat               |
| `frame`     | `frame`       | Inset border, corner ornaments, Cormorant                   |
| `editorial` | `editorial`   | Ghost letter, all-caps title, Bebas Neue                    |
| `magazine`  | `magazine`    | Warm cream bg, centered stack, hero image, Playfair Display |
| `darkroom`  | `darkroom`    | Navy bg, centered stack, grayscale image, Playfair Display  |
| `terminal`  | `terminal`    | Near-black, grid lines, monospace, neon green               |
| `poster`    | `poster`      | White bg, thick sidebar, oversized title, Barlow Condensed  |
| `chinese`   | `minimal`     | Clean white cover, HarmonyOS Sans SC font (app-installed)   |

Cover extras (inject into tokens via `--abstract`, `--cover-image`):

- `--abstract "text"` — abstract text block on the cover (magazine/darkroom)
- `--cover-image "url"` — hero image URL/path (magazine, darkroom, poster)

**Color overrides — always choose these based on document content:**

- `--accent "#HEX"` — override the accent color; `accent_lt` is auto-derived by lightening toward white
- `--cover-bg "#HEX"` — override the cover background color

**Accent color selection guidance:**

You have creative authority over the accent color. Pick it from the document's semantic context — title, industry, purpose, audience — not from generic "safe" choices. The accent appears on section rules, callout bars, table headers, and the cover: it carries the document's visual identity.

| Context                        | Suggested accent range                                   |
| ------------------------------ | -------------------------------------------------------- |
| Legal / compliance / finance   | Deep navy `#1C3A5E`, charcoal `#2E3440`, slate `#3D4C5E` |
| Healthcare / medical           | Teal-green `#2A6B5A`, cool green `#3A7D6A`               |
| Technology / engineering       | Steel blue `#2D5F8A`, indigo `#3D4F8A`                   |
| Environmental / sustainability | Forest `#2E5E3A`, olive `#4A5E2A`                        |
| Creative / arts / culture      | Burgundy `#6B2A35`, plum `#5A2A6B`, terracotta `#8A3A2A` |
| Academic / research            | Deep teal `#2A5A6B`, library blue `#2A4A6B`              |
| Corporate / neutral            | Slate `#3D4A5A`, graphite `#444C56`                      |
| Luxury / premium               | Warm black `#1A1208`, deep bronze `#4A3820`              |

**Rule:** choose a color that a thoughtful designer would select for this specific document — not the type's default. Muted, desaturated tones work best; avoid vivid primaries. When in doubt, go darker and more neutral.

**content.json format:**

- `content.json` 必须是**数组（列表）**格式：`[{"type": "h1", "text": "Title"}, ...]` ✓
- 不要使用 `{"blocks": [...]}` 或 `{"content": [...]}` 这种包装格式 ✗
- JSON 必须使用**英文双引号** `"`，不能用中文引号 `""`

**正确示例：**

```json
[
  {"type": "h1", "text": "第一章 绪论"},
  {"type": "body", "text": "随着信息技术的发展..."}
]
```

**Content 生成规范：**

为避免 JSON 语法错误（如双引号、反斜杠、换行符未转义），**禁止直接手写 JSON 字符串**。

**推荐方式**：使用 `scripts/content_builder.py` 生成内容：

```python
from scripts.content_builder import ContentBlock, save_content

blocks = [
    ContentBlock(type="h1", text="第一章 绪论"),
    ContentBlock(type="body", text='他说"你好"'),   # 无需手动转义引号
    ContentBlock(type="body", text="C:\\Users\\doc"), # 无需手动转义反斜杠
    ContentBlock(type="table",
        headers=["国家", "夺冠次数"],
        rows=[["巴西", "5"], ["德国", "4"]],
        caption="世界杯冠军统计"
    ),
]

save_content(blocks, r"<absolute PDF_CONTENT_PATH returned for this job>")
```

**规则：**

- 普通文本字段直接写 Python 字符串，不要为 JSON 再手动添加转义
- CREATE 必须写入当前 `PDF_JOB_ID` 对应的 `PDF_CONTENT_PATH`，禁止复用工作空间根目录的固定 `content.json`
- 公式字段必须使用 Python 原始字符串，例如 `ContentBlock(type="math", text=r"\frac{a}{b}")`，否则 `\f`、`\b`、`\t` 等可能被 Python 解释为控制字符
- `save_content()` 会自动处理特殊字符并输出合法的 JSON
- 仅在无法使用 Python 环境时，才允许手写 JSON（需自行保证语法正确）

**数学公式规则：**

- `math.text` 写 matplotlib mathtext 支持的 LaTeX 子集，不要包含 `align`、`cases`、`matrix` 等完整 LaTeX 环境
- 推荐使用 `\geq`、`\leq`、`\neq`；兼容输入 `\ge`、`\le`、`\ne` 会在渲染前自动规范化
- 中文可写在 `\text{}` 中；较长中文说明应放在 `caption` 或正文中
- 直接手写 JSON 时，LaTeX 反斜杠必须按 JSON 规则写成 `\\`；使用 `content_builder.py` 时不要手工做 JSON 转义
- 公式语法、字体或依赖错误会中止生成，修正后重试；不得把 LaTeX 源码当作公式降级交付

**content.json block types:**

| Block          | Usage                                                          | Key fields                                                                                  |
| -------------- | -------------------------------------------------------------- | ------------------------------------------------------------------------------------------- |
| `h1`           | Section heading + accent rule                                  | `text`                                                                                      |
| `h2`           | Subsection heading                                             | `text`                                                                                      |
| `h3`           | Sub-subsection (bold)                                          | `text`                                                                                      |
| `body`         | Justified paragraph; supports `<b>` `<i>` markup               | `text`                                                                                      |
| `bullet`       | Unordered list item (• prefix)                                 | `text`                                                                                      |
| `numbered`     | Ordered list item — counter auto-resets on non-numbered blocks | `text`                                                                                      |
| `callout`      | Highlighted insight box with accent left bar                   | `text`                                                                                      |
| `table`        | Data table — accent header, alternating row tints              | `headers`, `rows`, `col_widths`?, `caption`?                                                |
| `image`        | Embedded image scaled to column width                          | `path`/`src`, `caption`?                                                                    |
| `figure`       | Image with auto-numbered "Figure N:" caption                   | `path`/`src`, `caption`?                                                                    |
| `code`         | Monospace code block with accent left border                   | `text`, `language`?                                                                         |
| `math`         | Display math — LaTeX syntax via matplotlib mathtext            | `text`, `label`?, `caption`?                                                                |
| `chart`        | Bar / line / pie chart rendered with matplotlib                | `chart_type`, `labels`, `datasets`, `title`?, `x_label`?, `y_label`?, `caption`?, `figure`? |
| `flowchart`    | Process diagram with nodes + edges via matplotlib              | `nodes`, `edges`, `caption`?, `figure`?                                                     |
| `bibliography` | Numbered reference list with hanging indent                    | `items` [{id, text}], `title`?                                                              |
| `divider`      | Accent-colored full-width rule                                 | —                                                                                           |
| `caption`      | Small muted label                                              | `text`                                                                                      |
| `pagebreak`    | Force a new page                                               | —                                                                                           |
| `spacer`       | Vertical whitespace                                            | `pt` (default 12)                                                                           |

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

## Route B: FILL

Fill form fields in an existing PDF without altering layout or design.

```bash
# Step 1: inspect
bash "{baseDir}/scripts/make.sh" fill --input "$PWD/form.pdf" --inspect

# Step 2: fill
bash "{baseDir}/scripts/make.sh" fill --input "$PWD/form.pdf" --out "$PWD/filled.pdf" \
  --values '{"FirstName": "Jane", "Agree": "true", "Country": "US"}'
```

| Field type | Value format                                     |
| ---------- | ------------------------------------------------ |
| `text`     | Any string                                       |
| `checkbox` | `"true"` or `"false"`                            |
| `dropdown` | Must match a choice value from inspect output    |
| `radio`    | Must match a radio value (often starts with `/`) |

Always run `fill_inspect.py` first to get exact field names.

---

## Route C: REFORMAT

Parse an existing document → content.json → CREATE pipeline.

```bash
bash "{baseDir}/scripts/make.sh" reformat \
  --input "$PWD/source.md" --title "My Report" --type report --out "$PWD/output.pdf"
```

**Supported input formats:** `.md` `.txt` `.pdf` `.json`

---

## Route D: WATERMARK

Add text, image, or PDF watermarks to existing PDF pages.

```bash
bash "{baseDir}/scripts/make.sh" watermark \
  --input doc.pdf \
  --type text \
  --text "机密文件" \
  --output doc_watermarked.pdf \
  --pages "1-3"
```

**Watermark types:**

- `text` — vector text watermark (rotation, opacity, font-size, color)
- `image` — PNG/JPEG/BMP/WebP scaled to fit page
- `pdf` — use another PDF page as the watermark layer

**Common options:**

- `--pages "1,3,5-10"` — apply only to specified pages
- `--font-size 48` — text size (default 48)
- `--rotate 45` — text rotation in degrees (default 45)
- `--opacity 0.3` — text opacity 0–1 (default 0.3)
- `--color "#888888"` — text color hex (default `#888888`)
- `--font /path/to/font.ttf` — explicit font file (useful for CJK text)

---

## Route E: MERGE

```bash
bash "{baseDir}/scripts/make.sh" merge --inputs "$PWD/a.pdf" "$PWD/b.pdf" --out "$PWD/merged.pdf"
```

## Route F: SPLIT

```bash
# Split into single pages
bash "{baseDir}/scripts/make.sh" split --input "$PWD/doc.pdf" --outdir "$PWD/pages"

# Split by ranges
bash "{baseDir}/scripts/make.sh" split --input "$PWD/doc.pdf" --outdir "$PWD/parts" --ranges "1-3,5"
```

## Route G: ENCRYPT / DECRYPT

```bash
bash "{baseDir}/scripts/make.sh" encrypt --input "$PWD/doc.pdf" --out "$PWD/protected.pdf" --password secret
bash "{baseDir}/scripts/make.sh" decrypt --input "$PWD/protected.pdf" --out "$PWD/unlocked.pdf" --password secret
```

## Route H: EXTRACT TEXT

```bash
bash "{baseDir}/scripts/make.sh" extract-text --input "$PWD/doc.pdf" --out "$PWD/text.txt"
```

## Route I: EXTRACT TABLES

```bash
bash "{baseDir}/scripts/make.sh" extract-tables --input "$PWD/doc.pdf" --out "$PWD/tables.xlsx"
bash "{baseDir}/scripts/make.sh" extract-tables --input "$PWD/doc.pdf" --out "$PWD/tables.csv" --format csv
```

Use `--format csv` to output CSV instead of the default Excel format.

---

## Environment

```bash
bash "{baseDir}/scripts/make.sh" check   # verify dependencies prepared by 小艺 Work
bash "{baseDir}/scripts/make.sh" demo    # build a sample PDF
```

| Tool          | Used by                 | Install                  |
| ------------- | ----------------------- | ------------------------ |
| Python 3.9+   | all `.py` scripts       | system                   |
| `reportlab`   | `render_body.py`        | 客户端后台安装               |
| `pypdf`       | fill, merge, reformat   | 客户端后台安装               |
| `playwright`  | `render_cover.py`       | 客户端后台安装               |
| `matplotlib`  | math, chart, flowchart | 客户端后台安装               |
| `Pillow`      | images, watermarks     | 客户端后台安装               |
| Chrome / Edge / Playwright Chromium | `render_cover.py` | system or Playwright installation |
| `pdfplumber`  | `pdf_extract_tables.py` | 客户端后台安装               |
| `pandas`      | `pdf_extract_tables.py` | 客户端后台安装               |
| `openpyxl`    | `pdf_extract_tables.py` | 客户端后台安装               |

Python 包统一声明在 Skill 根目录 `requirements.txt`，调用过程中禁止执行 `pip install`。

**Browser configuration and troubleshooting:**

- Override browser path with `CHROME_PATH=/path/to/chrome`.
- The renderer automatically checks system/user Chrome, then Microsoft Edge on Windows, then Playwright Chromium.
- If no browser is available, use the same Python shown by `make.sh check` to run `playwright install chromium`, or install Chrome/Edge.
- Python package permission errors can use `python -m pip install --user ...`; proxy/index timeouts require a reachable package index or offline wheels. Do not install packages during a Skill run.
