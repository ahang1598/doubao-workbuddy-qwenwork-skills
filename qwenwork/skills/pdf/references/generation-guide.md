# Generation Guide

## HTML → PDF (html_to_pdf.py)

### Page size and margin guidelines

| Use case | Recommended settings |
|---|---|
| Standard report | `--page-size a4 --margin 20mm` |
| Presentation / slide | `--page-size a4 --margin 10mm` |
| US Letter document | `--page-size letter --margin 1in` |
| Dense data table | `--page-size a3 --margin 15mm` |

### Rendering backend

`html_to_pdf.py` uses **ReportLab** directly — no headless browser. CSS rules in the source HTML are mostly ignored; the script parses block structure (headings, lists, tables, blockquote, pre, img) with BeautifulSoup and emits ReportLab flowables. Zero system dependencies.

### Headers, footers, CSS flags

`--header`, `--footer`, and `--css` are accepted for backward
compatibility but are **no-ops** in the reportlab backend. If you need
repeating headers/footers, use `reportlab.platypus.PageTemplate`
directly in a custom script, or post-process with `pypdf`.

### Fonts and CJK

ReportLab ships with a small set of built-in Type 1 fonts
(Helvetica / Times / Courier) that do **not** cover CJK. For Chinese
output, register a TTF at the top of the script, for example:

```python
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
pdfmetrics.registerFont(TTFont("PingFang", "/System/Library/Fonts/PingFang.ttc"))
# Then set fontName="PingFang" in the ParagraphStyle definitions.
```

On macOS, PingFang SC / STSong are available by default.

---

## LaTeX → PDF (latex_to_pdf.py)

### Tectonic vs. pdflatex

Tectonic is recommended because it:
1. Auto-downloads missing CTAN packages (no `tlmgr install` needed)
2. Handles multi-pass compilation automatically
3. Is faster than full TeX Live

### Common LaTeX issues

**Chinese/CJK text:** Use the `ctex` package:
```latex
\documentclass[UTF8]{ctexart}
\begin{document}
你好，世界
\end{document}
```

**Missing packages:** Tectonic fetches from CTAN automatically if internet
is available. Offline: pre-populate the Tectonic cache with `tectonic --only-cached`.

**Complex figures (TikZ, PGFPlots):** These compile correctly with Tectonic.
Ensure `--keep-logs` for debugging if rendering fails.

### Error diagnosis table

| Error message | Cause | Fix |
|---|---|---|
| `! Undefined control sequence` | Typo or missing `\usepackage` | Check command spelling |
| `! Missing $ inserted` | Math outside math mode | Wrap in `$...$` |
| `No pages of output` | `\begin{document}` missing or fatal error | Check structure |
| `Runaway argument` | Unclosed `{` or `[` | Balance braces |
| Font shape unavailable | Missing font | Add `\usepackage[T1]{fontenc}` |

---

## Markdown → PDF (markdown_to_pdf.py)

### Theme selection

| Theme | Best for |
|---|---|
| `default` | General documents, notes |
| `professional` | Business reports, proposals |
| `minimal` | Technical docs, code-heavy content |

### Table of contents (`--toc`)

The `--toc` flag is accepted for backward compatibility but is a **no-op**
in the reportlab backend. If you need a TOC, emit one as regular Markdown
at the top of the source file.

### Supported Markdown features

The script uses **markdown-it-py** in CommonMark mode, with the
`table` and `strikethrough` plugins enabled. Supported:

- headings (h1–h6), paragraphs, emphasis/strong, inline code
- fenced code blocks with Pygments syntax highlighting
- ordered / unordered / nested lists
- blockquotes
- GFM tables
- horizontal rules
- hyperlinks

### Embedding images

Use standard Markdown image syntax with **local** paths:

```markdown
![Figure 1](./charts/revenue.png)
```

Remote images (http/https) are **not** fetched — the reportlab backend
never makes network calls. Pre-download the image locally first.
