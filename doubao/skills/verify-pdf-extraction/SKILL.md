---
name: verify-pdf-extraction
description: Use when the agent needs to extract, verify, or complete information from a PDF, scanned PDF, local attachment, paper, report, ticket, drawing, protection-scope file, or PPT-export page, especially for OCR识别, 扫描件, 表格抽取, 图表数字化, 页码行号核验, 字段复核, 本地附件优先, 按PDF补缺, 不确定留空, 核对页码, 行政区县清单, 金额日期单位核验, or 图纸尺寸数量核验.
---

# Verify PDF Extraction

Use this skill when PDF content is the authority for extracting text, tables, chart values, page/line locations, legal citations, report fields, spreadsheet backfills, administrative-area lists, fine/ticket fields, drawings, or PDF-derived deliverables.

## 1. Confirm the authoritative PDF source

- If a local attachment path is provided, read the local PDF first; only use a link, webpage, or older context after local access fails.
- When the user says “按我给的PDF内容”, “见上传文件”, “目标文件所在目录有：普洱茶DB.pdf”, or asks about an uploaded paper, pause any answer based on historical context until the current file is opened.
- Concrete convention: for “普洱茶的保护范围不是全省，而是全省的75个区县”, the authority is the protection-scope PDF, not a province-wide assumption or a pre-existing target-file area list.
- Concrete convention: for batches like `江苏发展报告—2021.pdf` plus numbered spreadsheets such as `45_01-05-01_表 十大门类行业营业收入增速情况.xlsx`, use the PDF to fill or verify missing table rows before updating the spreadsheet.

## 2. Define fields and evidence before extracting

- List the target fields before parsing: text quote, page, line, table title, row/column headers, amount, date, unit, administrative-area name, drawing dimension, quantity, chart value, or source limitation.
- Concrete convention: for fine/ticket PDFs, extract and verify at least `金额`, `日期`, `单位`, and each target spreadsheet column against the original page; if any field is unclear, leave it blank with a note instead of inferring it.
- Concrete convention: for transaction-detail PDFs, treat each record boundary as a separate row and extract `时间`, `收支`, `金额`, and `对方` before filtering or sorting.
- Concrete convention: for legal citation checks asking “第几页第几行”, record `quoted_phrase`, `PDF页码`, `期刊页码`, `段落位置`, and `行号依据` separately; do not collapse printed page and PDF page into one value.

## 3. Classify page type and choose the extraction path

- Determine whether each relevant page is text PDF, scanned image, image table, vector drawing, chart page, continuation table, or mixed layout.
- Concrete convention: text extraction positions are not `第几行`; line numbers must be counted from a page screenshot, OCR result, or layout analysis of the rendered page.
- Concrete convention: for `9、附件9、成立环保组织机构文件.pdf` and `10、附件10、环境保护管理制度体系汇编.pdf`, if text extraction fails, render pages and OCR before drafting `环保组织机构`, `机构人员组成`, `职责分工`, `环境保护设施调试及日常运行维护制度`, `环境管理台账记录要求`, or `运行维护费用保障计划`.
- Concrete convention: for drawings or engineering PDFs, render or screenshot the page before reading `尺寸`, `数量`, `开向`, `部位编号`, names, or construction practices.

## 4. Extract tables, charts, and structured records without silent repair

- For table pages, preserve headers, merged-header meaning, row order, and continuation-table boundaries; do not silently normalize suspicious original text.
- Concrete convention: when the task is to find “哪里还有续表需要分开的”, inspect page titles and table carry-over markers, then report which tables continue across pages instead of merging them into one unmarked block.
- Concrete convention: when a protection-scope list includes town-level entries and the user says “乡镇级别的折到区县级就可以”, aggregate township entries to the district/county level, then count against the required 75 district/county records.
- Concrete convention: for chart-only values such as paper yield figures, do not write `NG` just because text/table extraction failed; first locate the chart page, crop it, OCR labels/axes, and digitize or estimate the plotted value. Mark it `估读` if digitized from an image, and only mark unreadable after that fails.

## 5. Verify every extracted item against the PDF

- Reopen the PDF page or rendered image for each critical field before delivery, especially amounts, dates, units, page numbers, line numbers, district/county names, chart estimates, dimensions, and quantities.
- Concrete convention: after extracting the Pu’er tea protection scope, the verified count must be 75 district/county-level records; if OCR produces 74, 76, duplicates, province-wide coverage, or city-only names, stop and report the mismatch.
- Concrete convention: for spreadsheet updates from reports, verify missing rows/columns, continuation-table splits, field formats, and record counts across all files when the batch is small; for larger batches, sample only after full structural checks pass.
- Concrete convention: when filling financial or audit-report fields, keep the original value and page number, then cross-check asset/liability/profit-table relationships and required unit conversion such as “万元保留两位”.

## 6. Handle uncertainty and deliver only verifiable claims

- Separate statuses in the output: `已核实`, `估读`, `未核实`, and `无法确认`.
- Concrete convention: do not change ambiguous source text, administrative-division names, amounts, dates, units, drawing dimensions, or legal quotations to what “looks right”; preserve the source form and add a limitation note.
- Concrete convention: if a quote is found in a cited paper but belongs to another author quoted in a footnote, state both the location and attribution boundary rather than saying it is simply the paper author’s own view.
- Concrete convention: if line count cannot be supported by rendered-page counting, give page and paragraph/section only, and explicitly mark line number as `无法确认`.
- Do not expose internal trial-and-error, chain-of-thought, or irrelevant tool details; provide the result, page/source basis, verification status, and limits.

## Example output pattern

For a scanned protection-scope PDF:

| item | value | PDF basis | status | note |
| --- | --- | --- | --- | --- |
| scope count | 75 district/county records | protection-scope PDF pages checked by OCR/rendered image | 已核实 | township entries folded to district/county level |
| unclear OCR name |  | page X crop | 无法确认 | leave blank until user supplies clearer scan |
