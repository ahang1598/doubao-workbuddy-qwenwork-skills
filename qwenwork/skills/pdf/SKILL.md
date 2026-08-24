---
name: pdf
version: 1.0.4
description: >
  Operates on PDF files: inspect/fill forms, merge/split, watermark, encrypt/decrypt, strip metadata, extract tables or images, compress, validate, render pages to images (so the agent can read scanned PDFs with vision); render an existing .md/.html/.tex source file to PDF; or create new branded PDFs from MDX (reports, briefings, whitepapers). Do not use for: reading/summarizing/analyzing PDF content (use parse_file); PDF → Word (use pdf-convert-to-word); editing Word/PPT/spreadsheets; unauthorized files.
description_zh: >
  对 PDF 文件本身执行结构化操作：检查/填写表单、合并/拆分、加水印、加密/解密、清除元数据、提取表格或图片、压缩、校验、把页面渲染为图片（便于以视觉方式阅读扫描版 PDF）；把已有的 .md/.html/.tex 源文件渲染为 PDF；或基于 MDX 生成带品牌样式的新 PDF（报告、简报、白皮书）。优先使用适配的 QwenWork 云端能力；云端不适配或异常时，保留可信本地路径以完成任务。不适用于：阅读/总结/分析 PDF 内容（改用 parse_file）、PDF 转 Word（改用 pdf-convert-to-word）、编辑 Word/PPT/表格内容、未授权文件。
license: Proprietary. LICENSE has complete terms.
---

# PDF — Professional PDF Processing

## What this skill is for

This skill operates on **PDF files themselves** — structural processing, not content authoring.

Use it when the user wants to:
- merge, split, rotate, reorder, watermark, or crop PDF pages
- encrypt, decrypt, strip metadata from, or redact a PDF
- optimize, compress, or validate a PDF
- remove or manipulate pages, images, or sections within a PDF
- extract tables from a PDF to Excel (preserving table structure)
- extract images from a PDF
- render PDF pages to images so the agent can read scanned pages with vision
- inspect or fill a PDF form (AcroForm or flat/scanned via overlay)
- convert an existing Office document (DOCX/PPTX/XLSX and legacy variants) to PDF
- generate a PDF from an **existing** `.md` / `.html` / `.tex` source file in the workspace

## Do not trigger this skill for

Do **not** use this skill when:
- the user only wants to **read, summarize, analyze, or ask questions** about PDF content — no PDF structural operation is needed
- the user wants to **write/generate content** (report, article, meeting minutes, analysis) and output as PDF — the core task is content authoring, not PDF manipulation
- the user says "export to PDF / output PDF / make this a PDF" but has **no existing `.md`/`.html`/`.tex` source file** — that is content creation
- the user wants **PDF → Word/docx** conversion (handled by `pdf-convert-to-word`)
- the user’s real task is to edit **Word / slides / spreadsheet** content
- the task is mainly **image editing, restoration, or stylization**
- the user asks for **legal-grade permanent redaction guarantees** beyond what this toolchain verifies
- the user refers to files that are **not provided, not accessible, or not authorized**

**Key principle**: if the user’s core need is “create/write content” and PDF is just the output format, do NOT trigger this skill. Only trigger when the PDF file itself (or a structured source file like `.md`) is the direct subject of work.

---

## Creating a new PDF — route selection

| Route | When |
|-------|------|
| **[mdx2pdf.md](mdx2pdf.md) — DEFAULT semantic entry** | Invoke `scripts/generate_mdx_pdf.py` for Markdown/MDX. It prefers the typed cloud capability when that backend supports the requested source and features, and otherwise preserves the local `md2pdf` / ReportLab paths needed to finish the task. |
| `markdown_to_pdf.py` (below) | The local ReportLab implementation for ordinary Markdown. Use it directly when the user requests raw layout controls or when a plain local render is the best fit. |

All other PDF work — reading, extracting, merging, splitting, OCR, forms, watermarking, encryption — uses the scripts below; mdx2pdf is creation-only.

---

## Routing rules (non-creation operations)

### Route map

| User request | Route | Required entry step | Primary scripts |
|---|---|---|---|
| Extract text from PDF | EXTRACT | `analyze_pdf.py` | `extract_content.py` |
| Extract tables from PDF | EXTRACT | `analyze_pdf.py` | `extract_tables.py` |
| Extract images from PDF | EXTRACT | `analyze_pdf.py` | `extract_images.py` |
| Render PDF pages to images (for vision / scanned PDFs) | RENDER | input check | `convert_pdf_to_images.py` |
| Convert an existing Office document to PDF | CONVERT | input check | `office_to_pdf.py` |
| Merge / split / rotate / reorder / watermark / text-watermark PDF pages | EDIT | input + action check | `batch_ops.py` |
| Crop pages | CROP | input + action check | `crop_compose.py` (auto-detect content bbox, or manual `--crop`) |
| Compose / N-up (multiple pages → one page) | CROP | input + action check | `crop_compose.py` (`--layout vertical\|horizontal\|grid`) |
| Fill or inspect a PDF form | FORM | `inspect_form.py` | AcroForm → `fill_form.py` → optional `flatten_form.py` · flat/scan → `extract_form_structure.py` → `check_bounding_boxes.py` → `fill_form_overlay.py` |
| Encrypt / decrypt / redact / strip metadata | SECURITY | input + risk check | `secure_pdf.py` |
| Compress / optimize PDF | OPTIMIZE | input check | `optimize_pdf.py` |
| Validate PDF structure / PDF/A hints | VALIDATE | input check | `validate_pdf.py` |
| Create a branded PDF from Markdown/MDX | GENERATE | source type check | `generate_mdx_pdf.py` |
| Create PDF from HTML | GENERATE | source type check | `html_to_pdf.py` (thin shim → markdown_to_pdf) |
| Create PDF from LaTeX | GENERATE | source type check | `latex_to_pdf.py` |
| Create PDF processing report | REPORT | output inventory check | `create_report.py` |
| Batch process many PDFs | BATCH | enumerate inputs + per-file `analyze_pdf.py` | `batch_ops.py` + refs |

### Start here when the input is already a PDF

For routes whose input is already a PDF, run `analyze_pdf.py` to confirm `pdf_type`, `page_count`, and file size. The downstream text/render and form decisions key off this inspection. Do not run it for an Office input being converted to PDF or for an MD/MDX source being generated as a new PDF.

If `pdf_type = scanned` (or text comes back empty/garbled), default to the RENDER route: render the relevant pages with `convert_pdf_to_images.py` and read them with vision. Reach for `ocr_pipeline.py` only when the user explicitly asks for a searchable PDF or a plain-text OCR transcript.

---

## Working norms

A few non-obvious norms that this skill relies on:

**Choose the operation semantics first; prefer cloud when it fits, and preserve
task completion when it does not.** The agent decides pages, format, output
path, layout, quality, and other user-visible parameters, then starts with the
documented semantic script. In `auto` mode the script prefers a compatible typed
QwenWork capability and may switch once to a validated local implementation.
Do not preflight packages or install dependencies before this first invocation.

Cloud authentication/authorization failures, missing capability routes, source
limits, and unsupported feature combinations make that cloud path unsuitable;
they do not end a normal user task when a trusted local or workspace-provided
route can still complete it. Do not repeat a known-ineligible cloud call or loop
between engines. If the semantic entry genuinely cannot express the request,
use a compatible existing tool or a bounded local implementation, preserve the
requested output semantics, and validate the result. An explicit
`cloud_required` request remains terminal because it is an acceptance test of
that backend rather than a normal document task.

Backend policy is controlled uniformly by
`QWENWORK_DOCUMENT_EXECUTION_MODE=auto|local_required|cloud_required` (`auto`
is the default). `QWENWORK_DOCUMENT_RUNTIME_REQUIRED=true` remains a legacy
alias for `cloud_required`. Desktop and cloud sandboxes inject endpoint/token;
the Skill scripts never read or persist credentials.

**Write to a new output file by default.** Why: the original is the only fallback if a step goes wrong, and most users don't realize they're asking for an in-place edit. Overwrite only when the user explicitly says so.

**Don't claim the output is sanitized, redacted, or PDF/A-compliant beyond what the scripts actually verified.** Why: `secure_pdf.py --action redact` draws annotations over text — the underlying text stream is still there. `validate_pdf.py` checks structural integrity, not standards certification. Describe what was done, not what it sounds like.

**Stop on missing inputs, parse failures, or wrong-password encryption.** Don't paper over them. Why: silently skipping an unreadable page or fabricating an empty result wastes more user time than an early stop.

**Use the declared scripts before reaching for an alternative.** Why: every script in `scripts/` handles edge cases the obvious one-liner skips — CJK font registration, atomic writes, coordinate-system flips, FlateDecode image reconstruction. If a script lacks a required feature, choose a compatible existing tool or a bounded implementation and apply the same validation and non-destructive-write rules; do not stop merely because the preferred path is unavailable.

**Label OCR output as OCR-derived when it materially affects the answer.** Recognition errors happen; the user needs to know which numbers are scanned vs. native text.

---

## Large-file strategy

When `analyze_pdf.py` reports **page_count > 100** or file size > **10 MB**, work in chunks to avoid timeouts and context overflow.

### Chunk strategy by route

| Route | Approach |
|---|---|
| EXTRACT (text) | `extract_content.py --pages 1-50`, then `51-100`, etc. Merge afterward. |
| EXTRACT (tables) | `extract_tables.py --pages 1-30 --output tables_p1_30/`, then next range. For long reports, use the TOC / bookmarks from `analyze_pdf.py` to target only the pages with tables. |
| RENDER | Render only the pages the user asked about with `--pages <spec>`. |
| OCR | `ocr_pipeline.py` already streams page-by-page (O(1) memory). For files > 200 pages, always pass `--pages` to limit scope. |
| EDIT (split-by-chapter) | `batch_ops.py --action split-by-bookmarks` uses PDF bookmarks in a single pass. Manual chapter detection only if bookmarks are absent. |

### Chunk sizes

| pdf_type | Pages per chunk | Rationale |
|---|---|---|
| text | 50–100 | pdfplumber ~0.1 s/page |
| scanned | 20–30 | OCR at DPI 200 ~2–4 s/page |
| mixed | 30–50 | balance |

### Target-then-extract

For "find X in this long document": extract the TOC or first 5 pages first to locate the target pages, then extract only those. Almost always faster and more reliable than processing the whole file.

```bash
# Find the financial statements
python scripts/extract_content.py report.pdf --pages 1-5 --output toc.txt
# (toc says: 资产负债表 starts on page 120, 利润表 page 135 …)

# Extract only those pages
python scripts/extract_tables.py report.pdf --pages 118-145 --output financials/ --format xlsx
```

---

## Per-route notes

The route map says what script to call; these notes capture the non-obvious bits per route.

### EXTRACT
- Required: `analyze_pdf.py` first (even for images — `pdf_type` decides routing).
- Scripts: text → `extract_content.py` · tables → `extract_tables.py` · images → `extract_images.py`.

### RENDER
- Default DPI 150; bump to 200–250 only if text on the 150-DPI render is unreadable.
- Render only the pages the user asked about — never preemptively rasterize a whole long PDF.
- Prefer `convert_pdf_to_images.py`; it uses the typed `pdf.render_pages`
  capability when compatible and otherwise local PDFium. If neither route can
  satisfy an unusual rendering request, use another trusted renderer and keep
  the same page, quality, and output-validation requirements.
- The cloud renderer returns PNG. Explicit JPEG output remains local-only. In
  `cloud_required` mode, an unsupported format or remote failure is terminal.

### CONVERT
- Start with `python3 scripts/office_to_pdf.py input.docx output.pdf`.
- `office_to_pdf.py` uses local LibreOffice when ready and otherwise the typed
  `document.convert` capability. QwenWork validates/uploads the input and
  downloads the result atomically. In `cloud_required` mode a remote failure is
  terminal.

### FORM
- `inspect_form.py` reports `form_type`. Branch on it:
  - `acroform` → edit `fill_value` in fields.json → `fill_form.py`.
  - `layout_based` (flat / scanned) → `extract_form_structure.py` → compose `fields.json` (see `references/forms-guide.md` for schema; use `pdf_width`/`pdf_height` for structure path, `image_width`/`image_height` if you fell back to visual estimation) → `check_bounding_boxes.py` → `fill_form_overlay.py`.
- After filling, render the result with `convert_pdf_to_images.py` and eyeball it. CJK is auto-handled via `_fonts.py`; you don't need to register anything.
- When the user requests a non-editable result, run `flatten_form.py` after
  filling; do not replace this with an ad-hoc render/rebuild loop.
- Use `debug_annotations.py` only when coordinates feel uncertain.

### GENERATE
- For Markdown/MDX, follow [mdx2pdf.md](mdx2pdf.md) and start with
  `python3 scripts/generate_mdx_pdf.py SOURCE --output OUTPUT.pdf`. It uses an
  eligible typed cloud route first, then a compatible local `md2pdf` or
  ReportLab implementation. Version 0.4.7+ receives
  `--brand qwenwork-cn`; an older detected release receives `--no-header` so
  its legacy MuleRun mark cannot leak into the output. Local-only features such
  as `--base-dir`, `--components`, sources above the cloud upload limit, or an
  explicit plain ReportLab profile bypass the incompatible cloud route without
  reducing the requested result. It never installs Node, React, Playwright,
  Chromium, or md2pdf automatically.
- When the command runs through Workspace Bash in the secure VM, set the Bash
  tool timeout to at least 900 seconds. The cloud operation itself is bounded
  to 10 minutes; the default 120-second VM shell timeout is too short.
- `generate_mdx_pdf_cloud.py` is retained only as an explicit forced-cloud
  adapter for acceptance tests; normal Skill workflows do not call it.
- For LaTeX invoke `latex_to_pdf.py`. It uses an existing local Tectonic or the
  typed `pdf.generate_latex` capability. Cloud generation accepts only a
  bounded self-contained `.tex` source (no `input`, `include`, external images,
  or bibliography files); do not install a TeX distribution in the client.
- Validate the output with `validate_pdf.py` for HTML / Markdown / LaTeX generation — these pipelines can produce broken PDFs in edge cases.

### SECURITY
- Before destructive actions (redact, decrypt, strip-metadata), summarize the scope (page range, pattern set) in your response so the user can spot a wrong target.
- `--action redact` draws annotations over text; the underlying stream is still there. Say so if the user implies they need court-grade redaction — point them at `qpdf --qdf` + manual stream editing, or Acrobat.

### OPTIMIZE
- `optimize_pdf.py` covers image re-encoding → adaptive quality search → controlled rasterization. Don't reinvent it.
- With `--target-size`, the script iterates to find the best quality that fits. If image compression alone can't hit the target, ask the user before passing `--rasterize-fallback` — it turns text into images and breaks search/select.

```bash
# Standard
python scripts/optimize_pdf.py input.pdf output.pdf --target-size 10240

# After user accepts quality loss
python scripts/optimize_pdf.py input.pdf output.pdf --target-size 10240 \
    --rasterize-fallback
```

### CROP
- `crop_compose.py` auto-detects content bbox via PyMuPDF. Pass `--crop x0,y0,x1,y1` to override, `--layout vertical|horizontal|grid` for composition, `--per-page N` for N-up.

### BATCH
- Enumerate inputs explicitly; drop missing / unauthorized files and list them in the final report.
- Run `analyze_pdf.py` per file, then dispatch each to its single-file route. Apply the Large-file strategy per file (not globally).
- Distinct output path per file. Aggregate into `{input, route, output, status, warnings}` rows.

### EDIT / VALIDATE / REPORT
- Single-script routes — `batch_ops.py` / `validate_pdf.py` / `create_report.py`. Pick action, give explicit output path, summarize the change.

---

## Stop conditions

Stop and surface the problem (don't paper over):

- Missing / inaccessible / corrupted input.
- Encrypted PDF without a working password.
- Required inspection step failed.
- Ambiguous target for a destructive write.
- The bounded dependency recovery below is ineligible, unavailable, or has
  failed after a backend error.
- No safe available route can preserve the requested semantics after bounded
  exploration and validation. Report the concrete missing capability and any
  usable partial result.

---

## Dependency policy

Do not pre-install packages speculatively. First invoke the documented semantic
script and let it use an already-ready local backend or the typed cloud route.

### One-time local dependency recovery

For a normal `auto` or `local_required` task, use this recovery only after the
semantic script reports `LOCAL_DEPENDENCY_MISSING`,
`NO_EXECUTION_BACKEND_AVAILABLE`, or a cloud infrastructure failure. Do not
recover from bad arguments, missing/corrupted/encrypted inputs, wrong passwords,
or `PDF_VALIDATION_FAILED`.

Install only the requested operation's declared packages at user scope, using
the same interpreter that launches the script. Use
`python -m pip install --user <packages>` (or the equivalent `python3` / `py -3`
command).

- Analysis/text/validation/form inspection: `pypdf pdfplumber`; tables to XLSX:
  `pdfplumber pandas openpyxl`; embedded images: `pypdf Pillow`; rendering:
  `pypdfium2 Pillow`.
- Form filling: `pypdf PyMuPDF`; flatten/crop/compose: `PyMuPDF`; edit/security:
  `pypdf`; text watermark/form overlay: `pypdf reportlab`; optimization:
  `pypdf Pillow` (raster fallback also needs `pypdfium2 reportlab`).
- Ordinary Markdown: `markdown-it-py reportlab pygments Pillow`; OCR:
  `numpy PyMuPDF rapidocr-onnxruntime reportlab Pillow`.

After installation, rerun the same semantic script and arguments under
`QWENWORK_DOCUMENT_EXECUTION_MODE=local_required` once before considering a
different trusted local route. On POSIX,
prefix that environment assignment to the command; in PowerShell, set
`$env:QWENWORK_DOCUMENT_EXECUTION_MODE = "local_required"` first. If Python,
`pip`, installation, or forced-local execution is unavailable, stop and report
the concrete error; never loop or retry the cloud route.

Do not turn this default recovery into a hard path restriction. When the
declared script cannot express the request, a compatible pre-existing tool may
still be used if its output is validated and the task does not enter a retry
loop.

Do not use this recovery path for a cloud_required acceptance test. That mode
must expose the cloud result without masking it with local execution.

Python package recovery does not authorize installing native programs such as
LibreOffice, Tectonic, qpdf, browser runtimes, or `md2pdf`. Ask the user before
installing a system-level dependency, and only when the requested operation has
no Python-only route. If Python or `pip` itself is absent, surface that boundary
instead of bootstrapping a runtime.

Some legacy, local-only scripts still print historical install hints. Treat
them as diagnostics and apply only the bounded policy above.

---

## Output contract

When you finish a run, return: route used · input file(s) · output file(s) · key settings that mattered · validation result (if applicable) · any warnings or uncertainty. Skip fields that don't apply — don't pad. A run is complete when the user has the artifact and the summary reflects any limitations honestly.

---

## Quick workflows

Common copy-paste starting points. For everything else, see the per-route notes above or run `python scripts/<script>.py --help`.

### Fill a PDF form

**AcroForm path:**
```bash
python scripts/inspect_form.py form.pdf --output fields.json --check-overlaps
# edit fields.json to set fill_value
python scripts/fill_form.py form.pdf fields.json filled.pdf
```

**Overlay path (flat / scanned):**
```bash
python scripts/inspect_form.py form.pdf --output detect.json    # confirm form_type
python scripts/extract_form_structure.py form.pdf structure.json
# agent composes fields.json from structure.json (schema in references/forms-guide.md)
python scripts/check_bounding_boxes.py fields.json
python scripts/fill_form_overlay.py form.pdf fields.json filled.pdf
python scripts/convert_pdf_to_images.py filled.pdf --output verify/ --dpi 150    # eyeball
```

### Render to images / extract / generate

```bash
# Render for vision reading
python scripts/convert_pdf_to_images.py scan.pdf --output images/ --pages 1-5 --dpi 150

# Extract tables to Excel
python scripts/extract_tables.py report.pdf --output tables/ --format xlsx

# Markdown/MDX → PDF (cloud when compatible, otherwise a validated local path)
python3 scripts/generate_mdx_pdf.py report.mdx --output result.pdf --page-size A4

# HTML → PDF
python scripts/html_to_pdf.py page.html --output result.pdf --page-size a4 --margin 20mm
```

> Do not write your own `markdown_to_pdf.py` / `html_to_pdf.py` / `create_*_pdf.py`. If the skill script errors out, re-read its `--help` — every CLI prints a usage example. Ad-hoc scripts miss CJK font registration, aspect-ratio handling, atomic writes, and splittable code blocks.

### Split / merge / watermark / crop

```bash
# Split specific pages (contiguous or not)
python scripts/batch_ops.py --action split --input book.pdf --pages 1,3,7-9 --output selected.pdf

# Split by bookmarks (one file per chapter)
python scripts/batch_ops.py --action split-by-bookmarks --input book.pdf --output-dir chapters/

# Merge
python scripts/batch_ops.py --action merge --inputs a.pdf b.pdf c.pdf --output merged.pdf

# Text watermark (CJK works)
python scripts/batch_ops.py --action text-watermark --input doc.pdf --text "机密" --output wm.pdf

# Crop / N-up compose — see python scripts/crop_compose.py --help
```

### Encrypt

```bash
python scripts/secure_pdf.py --action encrypt --input doc.pdf --output secured.pdf \
    --user-password "read123" --owner-password "admin456"
```

---

## References

Read when you need deeper context — not by default.

- `references/extraction-guide.md` — multi-column text, table edge cases
- `references/forms-guide.md` — AcroForm vs layout-based, coordinate systems, fields.json schema
- `references/generation-guide.md` — HTML / Markdown / LaTeX generation
- `references/security-guide.md` — encryption, redaction, metadata
- `references/advanced-libraries.md` — pypdfium2 / pdf-lib / qpdf recipes
- `references/troubleshooting.md` — common failure modes

---

## State handling

Stateless. Treat intermediate JSON / debug PNGs / OCR outputs as temporary unless the user asks to keep them. Re-run inspection for each new or materially changed file.
