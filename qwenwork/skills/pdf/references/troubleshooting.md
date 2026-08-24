# Troubleshooting

## Installation Issues

### pypdf import error
```
ModuleNotFoundError: No module named 'pypdf'
```
**Fix:** `pip install pypdf`

Note: the older package is `PyPDF2` — do NOT use it; use `pypdf` (lowercase).

### pdfplumber import error
```
ModuleNotFoundError: No module named 'pdfplumber'
```
**Fix:** `pip install pdfplumber`

### Markdown/HTML → PDF backend

The default `markdown_to_pdf.py` and `html_to_pdf.py` backends are **pure
Python** (markdown-it-py / beautifulsoup4 + ReportLab). They do **not**
launch a headless browser and do **not** require `playwright` or
`chromium`. If you see an old traceback mentioning
`playwright._impl._errors.Error: Executable doesn't exist at ...`, you are
running an outdated copy of these scripts — re-sync this skill.

Cloud failures use stable routing codes:

- `CLOUD_AUTH_REJECTED` — HTTP 401/403; do not retry the same cloud call, but
  normal `auto` tasks may continue through a compatible local route.
- `CLOUD_TOOL_NOT_FOUND` — HTTP 404 during capability discovery; do not repeat
  discovery, but normal `auto` tasks may continue through a compatible local
  route.
- `CLOUD_TRANSIENT_FAILURE` — timeout, HTTP 429, or HTTP 5xx; retryable by the
  bounded semantic router only.

For ordinary `.md`, `generate_mdx_pdf.py` prefers a compatible cloud render and
may use the packaged ReportLab backend locally when its dependencies are ready,
so an unavailable cloud backend must not block a normal Markdown conversion.
Use `--render-profile plain` to request ReportLab explicitly and `branded` to
avoid silently degrading to it. `.mdx` is never sent to ReportLab because doing
so would render MDX components as plain text.

### Tectonic not found
```
Error: 'tectonic' not found on PATH
```
**Fix:**
- macOS: `brew install tectonic`
- Any: `cargo install tectonic` (requires Rust)

### pypdfium2 rendering error
```
ModuleNotFoundError: No module named 'pypdfium2'
```
**Fix:** `pip install pypdfium2`

---

## Extraction Issues

### Empty or garbled text extraction
**Symptoms:** `extract_content.py` returns empty or nonsense text.

**Diagnosis:**
```bash
python scripts/analyze_pdf.py document.pdf
```
- If `pdf_type: scanned` → switch to RENDER route.
- If `pdf_type: text` but garbled → text may be encoded with a custom font
  mapping. Try `pdftotext -layout` as a fallback.

### Tables not detected
**Symptom:** `extract_tables.py` reports "No tables found"

**Causes and fixes:**
1. Table has no visible borders → use `vertical_strategy: text` (see extraction-guide.md)
2. Table is actually an image → render that page with
   `convert_pdf_to_images.py` and read it with vision.
3. Single-column text mistaken for table → this is correct behavior; no tables exist

---

## Form Filling Issues

### `update_page_form_field_values` has no effect
**Cause:** pypdf requires that the page writer object is the same as the
writer that owns the page. `fill_form.py` uses `writer.append(reader)` which
ensures this. If you see this, ensure you're using the latest pypdf version:
```bash
pip install --upgrade pypdf
```

### Annotation text appears outside the field area
**Cause:** Coordinate mismatch between pdfplumber (top-origin) and PDF (bottom-origin).

`fill_form.py` converts automatically, but if results are wrong, manually
adjust `fill_y` in the JSON. Increase the value to move text up, decrease to move down.

### Checkbox stays unchecked
**Cause:** The `checked_value` for this PDF is not `"Yes"` — it may be `"On"` or a custom value.

**Fix:** Run `inspect_form.py` and check the `checked_value` field in the output.
Use that exact value in `fill_value`.

---

## Generation Issues

### PDF output is blank or has rendering artifacts
**Cause (HTML route):** CSS `display: none` on body, or JS errors preventing content rendering.

**Fix:** Add `wait_until="networkidle"` (already default). Check that the HTML
is valid. Test in a browser first.

### LaTeX compilation loop / timeout
**Cause:** Tectonic normally auto-handles multi-pass. If it loops, there may be
a circular dependency in `\ref` or `\cite` commands.

**Fix:** Ensure your `.bib` file is referenced correctly. Run with `--keep-logs`
and inspect the log for "rerun" messages.

### Markdown images not appearing
**Cause:** Relative image paths require the markdown file and images to be in the same directory.

**Fix:** Ensure images are in the same directory as the `.md` file, or use absolute paths.

---

## Performance Issues

### OCR is very slow
- Lower `--dpi` to 200 for faster (but lower quality) OCR
- OCR is CPU-bound; for large batches, consider processing in parallel

### PDF merge of many files is slow
- pypdf loads all pages into memory; for 100+ files, process in batches of 20
- Use `qpdf` CLI for bulk merges: `qpdf --empty --pages *.pdf -- merged.pdf`

### optimize_pdf.py shows 0% or minimal size reduction

**"0 re-encoded" — images not recognized:**
Images stored with FlateDecode (raw pixels + zlib) rather than DCTDecode (JPEG)
were previously invisible to the compressor. The current version handles
FlateDecode images via raw-byte reconstruction. If you still see 0, the images
may use JBIG2 or another rare codec — use `--rasterize-fallback` as a last
resort (warn the user about quality loss first).

**Images re-encoded but reduction is small:**
The original images are already heavily compressed JPEGs with little room for
further savings. Try a lower `--image-quality` (50–60), accepting visible
quality loss, or use `--target-size <KB>` to let the script search
automatically.

**PDF is mostly vector graphics / text:**
Vector content (text, paths, charts) cannot be reduced by image compression.
Try `qpdf --compress-streams=y --recompress-flate` for stream-level
compression, or use `--rasterize-fallback` to convert pages to images (text
becomes non-searchable).

---

## Windows Path Handling

On Windows, **never use `copy`, `xcopy`, or `robocopy` with double-quoted paths that end in `\`** — the shell interprets `\"` as an escaped quote, causing "unclosed quote" errors.

Use Python for all file copy/move operations instead:

```python
import shutil, pathlib
shutil.copy2(r"C:\Users\...\file.pdf", r"C:\dest\file.pdf")
# or for directories:
shutil.copytree(src, dst)
```

When passing Windows paths to shell commands, always use **forward slashes** or ensure no trailing backslash inside quotes:
- ✓ `python scripts/analyze_pdf.py "C:/Users/foo/bar.pdf"`
- ✓ `python scripts/analyze_pdf.py C:\Users\foo\bar.pdf`  (no quotes needed if no spaces)
- ✗ `copy "C:\source\" "C:\dest\"`  (trailing `\"` breaks quoting)
