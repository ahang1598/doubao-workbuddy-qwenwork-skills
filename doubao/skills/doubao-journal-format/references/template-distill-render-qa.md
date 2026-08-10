# Template Evidence And Render QA

Read this when extracting a template into `style_spec.json`, writing audit artifacts, running visual QA, or diagnosing why the final Word display does not match the template.

## Evidence Contract

Before applying styles to the target, treat the template as an evidence source and distill it into an evidence contract. The contract can be written as `template_evidence.json` or folded into `style_spec.json` plus `qa_report.json`, but it must answer these questions:

- Template identity: absolute path, original extension, SHA-256 when practical, page count if rendered, section count, and whether the source was native `.docx` or converted from `.doc`/`.dot`.
- Page system: page size, orientation, margins, columns, gutter, header/footer distances, first/odd/even behavior, and every `sectPr` location.
- Role typography: title, author, affiliation, abstract, keywords, heading levels, body, captions, references, metadata, citation format, and equation roles with concrete font slots, size, bold/italic, color, underline, language, spacing, indents, tabs, borders, shading, keep/page-break controls, and raw `style_xml/pPr_xml/rPr_xml`.
- Direct-format evidence: representative paragraph/run properties only for native DOCX/DOTX templates. Converted legacy Word files are text-extraction carriers and must not donate direct formatting to role styles.
- Numbering evidence: style `numPr`, reference-list visible prefix pattern, automatic numbering definitions, abstractNum/num IDs, hanging indentation, and continuation-line behavior.
- Table evidence: `tblPr`, `tblGrid`, row properties, `tcPr`, top/header/bottom/inside/vertical border model, cell margins, table width, and representative table strength.
- Equation evidence: equation paragraph style, formula object kind, tabs before equation, tabs between equation and number, computed fallback tab stops, and whether tabs were template-derived or fallback-derived.
- Object preservation evidence: media, embeddings/OLE, charts, diagrams, headers, footers, comments, footnotes/endnotes, fields, hyperlinks, relationships, and custom XML part counts.

Unresolved values must be recorded as unresolved or filled only by granular fallback. Do not invent a style value merely because a paper template usually has it.

## Unified Evidence Fusion Route

Every usable format source must be normalized into the same role-based evidence contract before target formatting. The target-formatting stage consumes `style_spec.json` and `role_map.json`; it must not care whether the source began as `.docx`, `.dotx`, `.doc`, `.dot`, PDF, image, website, or text instructions.

Use this source-aware extraction route:

1. Identify the original source type and record it in `qa_report.format_source` and, when a style spec is written, `style_spec._meta`.
2. For native `.docx`/`.dotx`, extract OpenXML style, numbering, section, table, equation, header/footer, relationship, representative paragraph, and prose-rule evidence directly.
3. For legacy `.doc`/`.dot`, convert to temporary `.docx` with Microsoft Word when available or LibreOffice/`soffice` otherwise only so text and reliable column-count metadata can be extracted. Do not use converted OpenXML styles, converted direct formatting, support files, headers/footers, or page XML as formatting authority. Do inspect converted `sectPr/w:cols` only to choose fallback column count, and record the detection source. If converted `sectPr` detection fails, use source filename keywords such as `双栏`, `单栏`, `two-column`, or `single-column` as lower-priority fallback hints before defaulting to single-column.
4. For PDF/image/website sources, extract text rules before OCR/visual checks, then write rules JSON. Text-format guides define primary rules. Explicit source prose may also define supported content/structure operations through `postprocess_operations`, such as tables/figures after references, body citation marker conversion, reference-prefix conversion, or caption-prefix normalization. Visual/geometry evidence may select only the fallback variant column count (`fallback_columns=1` or `2`); it must not identify role alignment, style properties, or postprocess operations. Website links are the exception for column fallback: if website text/user rules do not explicitly state single-column or double-column manuscript layout, record single-column fallback instead of inferring from website visuals or publisher production examples.
5. Merge evidence at property level, not whole-role level. For example, if text says `正文五号宋体` but not line spacing, keep the text-rule font/size and fill line spacing from fallback; do not replace the entire body style with fallback and do not use non-DOCX visual/converted direct formatting.

Do not phrase the evidence result as "website/PDF text rules are weak and fallback was used" when explicit text rules were extracted. Say instead that the source container was non-DOCX, explicit text rules were applied first, and fallback completed only missing properties.

Legacy `.doc`/`.dot` warning pattern: if conversion yields a `.docx`, do not conclude that converted styles or direct formatting are trustworthy. Use converted text rules first, optional column-count detection second, then granular fallback. The target-formatting stage must still consume only `style_spec.json` and `role_map.json`; it must not branch into a `.doc`-specific formatter. Converted shell styles are carriers, not authority.

## PDF Text Rules And Column Fallback

PDF sources are not Word templates. They do not expose reliable `styles.xml`, `numbering.xml`, section XML, paragraph style IDs, header/footer relationships, object anchors, or Word table/equation XML. Treat every PDF as text-rule evidence plus optional single/double-column fallback selection.

If the PDF text contains author instructions, submission guidelines, `投稿须知`, `来稿要求`, `作者指南`, `撰稿要求`, `格式要求`, `论文格式`, `参考文献格式`, or similar prose rules, treat the extracted text rules as the primary evidence. Do not infer the required manuscript style from the PDF guide page's own font/size/layout. A submission-guideline PDF may be typeset in a different style from the paper it describes.

Examples of text-guide rules that should win over visual inference:

| Extracted PDF text | Evidence to record |
|---|---|
| `表采用三线表的格式` | table border model is three-line; do not infer table borders from the instruction page itself. |
| `公式在文章中以阿拉伯数字连续编号，用（）括起置于公式右边` | equation numbering uses parenthesized Arabic numbers on the right; tab stops may still need fallback calculation. |
| `正文中引用参考文献时文献号须加[ ]用上标表示` | body reference citations should use bracketed superscript markers when applying a compatible superscript map/rule. |
| `参考文献格式 ... [期刊] 作者 年份 刊名 卷号 起始页码` | reference item pattern/order comes from the prose/example, not from the PDF paragraph's visual font. |

`scripts/extract_pdf_format.py` must write `pdf_rules.json` with `_meta.source_type="text_rules"`, `_meta.non_docx_standard_fallback=true`, optional `_meta.fallback_columns`/`source_column_detection`, and optional text-derived `postprocess_operations`. Use that file as `--rules-json` and pass `--format-source-type text_rules` or rely on the metadata. Text rules remain locked and have higher priority than fallback for stated properties; missing properties come from the selected fallback. Text-derived postprocess operations auto-run after the first valid repack. If no explicit PDF text rule is found, continue with the selected fallback and warn the user.

Non-DOCX visual whitelist:

- Allow: reliable single-column or double-column detection for fallback variant selection.
- Do not allow: paragraph role identity, role alignment,字号/point size, exact Chinese font, exact Latin font, bold/italic, color, underline, small caps, indentation, local italic/bold spans, exact line spacing, character spacing, exact tab stops, or run-level style details.
- Treat visual font size and coordinates only as internal extraction diagnostics; do not write them to `pdf_rules.json` or `style_spec.json`.

For PDF visual, PDF hybrid, image/OCR/website, text-rule, blank-template, and converted legacy Word sources, do not use an old Word "blank template" or converted shell style as formatting authority. Treat any blank/converted carrier document as a low-confidence container. Generated role styles must come from the evidence contract plus granular fallback, with no inherited Heading/Reference colors, paragraph borders, underlines, small caps, theme colors, or stale Word defaults unless the source/user/text rule explicitly requires them.

Blank/carrier template QA is mandatory when the format source is weak and the DOCX package is only a carrier:

- Select fallback language from explicit rules first, then from the target document text. Do not infer Chinese/English from an empty carrier package.
- Rebuild low-confidence `style_spec.json` role styles before installation if old `style_xml` contains carrier defaults.
- Write the selected body fallback baseline into target `docDefaults` and `Normal`.
- Audit role styles before delivery: Chinese blank-carrier fallback should show body `line="360"` and five-point size, title/heading fallback spacing such as `before="240" after="120" line="360"` where defined, and no remaining carrier `Normal` single spacing `line="240"` in the generated title/heading/body role styles.
- If any of these deterministic checks fail, repair and rerun the audit instead of sending the issue only as a user warning.

This column-only visual rule is universal for non-DOCX visual sources. It applies to PDF, screenshots, images, OCR output, rendered DOC/DOT previews, and externally supplied visual rules JSON. Before `style_spec.json` is built, strip visual-only role/alignment/字号/font/bold/italic/color/underline/indentation/spacing/tabs/run-level fields. Retain only explicit prose/user text rules and optional fallback column metadata.

Website links have a stricter column rule than other visual sources. Do not use website captures, publisher article pages, journal brand reputation, Nature/Science-like production layouts, or visual website examples to infer double-column submission format. Only explicit website/user text such as `双栏`, `two-column`, `single-column`, or equivalent manuscript-layout wording may set `fallback_columns=2` or `fallback_columns=1`. If no such text is found, write `fallback_columns=1` and record `website_unspecified_columns_default_single`.

## PDF Geometry Evidence

Use PDF geometry evidence for sample articles, sample issues, publisher proofs, or PDFs that lack explicit text formatting instructions only to select single-column or double-column fallback. Recommend either a native `.docx` template/source-format file or explicit text formatting instructions in final notes.

Visual sample PDFs need role-source filtering before any rule is emitted:

- Ignore decorative or repeated watermark lines such as `样例`, `示例`, `样张`, `Sample`, `Draft`, and `Proof`, especially when they are huge, centered, or repeated across pages. They must never become `title`, `heading`, `body`, or caption style evidence.
- Do not let the largest font on the page define the title by itself. Use page position, text length, nearby title continuation lines, and front-matter state.
- Use a front-matter state machine on page 1: title may span multiple early large lines; the next short name-like line is `author`; institution/address lines are `affiliation`; communication author, funding, DOI, or dates are `metadata`; once abstract/keywords/body begins, later body lines must not be reclassified as author or affiliation merely because they contain institution words.
- Do not promote PDF visual bold/italic/color/font/size/alignment into role styles.
- For sample/proof PDFs, keep `source_type=text_rules` for `rules_json`; store visual diagnostics only in `pdf_evidence.json`.

When a PDF format source is present and no stronger `.docx`/explicit user rule covers the same properties, run:

```bash
python scripts/extract_pdf_format.py source.pdf \
  --out-json pdf_evidence.json \
  --rules-json pdf_rules.json
```

Use the common PDF toolchain in this order, combining all available evidence rather than relying on one parser:

1. **PyMuPDF / `fitz`**: primary source for selectable-text PDFs. Extract text for explicit prose rules and line coordinates for column detection only.
2. **`pdftotext -layout` and `pdftotext -bbox-layout`**: cross-check reading order, columns, line breaks, and selectable-text availability. Use layout text to catch extraction-order problems from PyMuPDF.
3. **`pdffonts`**: audit embedded/subset font inventory and font substitution risk. Treat subset names such as `ABCDEE+TimesNewRoman` as evidence for the normalized font family, not a literal Word font name.
4. **`pdfplumber`**: supplement text extraction, table/line diagnostics, and column detection when available.
5. **`mutool` / Poppler tools**: supplement PDF metadata, page/object structure, and extraction diagnostics when available.
6. **OCR / screenshot inspection**: last resort for scanned or image-only PDFs. OCR can recover text rules but cannot reliably recover exact fonts, sizes, paragraph styles, numbering definitions, or table XML. Mark these properties unresolved unless visually obvious.

`pdf_rules.json` should not use `_meta.source_type="pdf_visual_inference"` or `pdf_text_visual_hybrid` for this skill route. If an external tool emits those old source types, sanitize them to `text_rules`, keep explicit text rules only, and move column evidence into `_meta.fallback_columns`.

PDF geometry inference may reasonably infer:

- page/column geometry for fallback selection and layout QA only, not paragraph style typography.

PDF column detection must be conservative. Do not infer double-column layout from multiple left-edge clusters alone: single-column academic PDFs commonly contain first-line indents, hanging references, centered titles/captions/equations, and short formula/title rows that create extra x-coordinate clusters. A double-column vote needs all of these:

- balanced left and right body-like text bands, not just two left-edge clusters;
- a clear blank gutter between the median right edge of the left band and the median left edge of the right band;
- enough right-band body lines with meaningful text width;
- few body lines crossing the inferred column boundary;
- agreement across more than one page, or an explicit user/source instruction.

Sample-issue PDFs can have very few body-like lines per page because page 1 contains front matter and later pages contain formulas, tables, figures, captions, and short equation rows. Do not let page-vote majority alone force single-column in that case. If page-level votes are weak, run a cross-page aggregate geometry check:

- collect looser non-decorative text lines across inspected pages only for column-start evidence;
- require stable left and right x-start clusters that recur across multiple pages;
- require pages where both clusters appear, a real gutter between the left-column median right edge and right-column median start, and low full-width crossing-line ratio;
- record this as `aggregate_vote` in `source_column_detection`;
- use it only to choose `fallback_columns`, never to define fonts, sizes, alignment, spacing, indentation, colors, role styles, or content/structure postprocess operations.

If both page-level body-band evidence and cross-page aggregate evidence are weak, default `_meta.fallback_columns` to `1`, set low confidence, and tell the user that `--body-cols 2` or explicit text instructions can override the PDF guess when the intended layout is double-column.

PDF must not be treated as authoritative for:

- Word style IDs, based-on/next style relationships, `pPr/rPr` inheritance, `docDefaults`, numbering IDs, section breaks, header/footer rels, object anchors, OMML/OLE equation internals, field codes, or exact tab stops;
- exact table XML such as `tblGrid`, `gridSpan`, vertical merges, cell margins, and border conflict resolution;
- exact line spacing when text is scanned, subset fonts are missing, or extraction order is inconsistent;
- exact font family, color, underline, italic, small caps, character spacing, and run-level formatting unless stated in explicit text rules.
- visual字号/point size, visual bold/italic, visual alignment, visual indentation, and visual reference hanging indent.

If `extract_pdf_format.py` extracts zero text rules, do not stop by default. Use OCR when practical; otherwise apply the selected standard fallback and warn that the source was not DOCX and no explicit PDF text rules were found.

PDF conformance QA must compare the final installed role styles against explicit PDF text rules plus fallback variant expectations. Do not audit or repair final alignment/字号/bold/indentation/spacing against PDF visual evidence.

## QA Audit Route

Run structural QA before and after formatting whenever practical:

```bash
python scripts/qa_audit.py template.docx --out-json template_qa.json
python scripts/qa_audit.py target.docx --out-json target_before_qa.json
python scripts/qa_audit.py output.docx --out-json output_qa.json
```

The formatter can do this during a normal run:

```bash
python scripts/format_docx.py \
  -t template.docx -i target.docx -o output.docx \
  --qa-report-out qa_report.json
```

Use the QA report to compare:

- section count, page size, margins, and columns;
- direct run/paragraph formatting before and after cleanup;
- key parts such as `styles.xml`, `numbering.xml`, settings, font table, and theme;
- media, embeddings, charts, diagrams, headers, footers, rels, and customXml counts;
- remaining direct formatting examples that can still override role styles.
- table geometry: `tblW`, `tblInd`, `tblGrid`, row/cell `tcW`, explicit table/cell borders, header-row evidence, cell margins, and whether auto-width tables may render differently.
- image placement: `wp:inline` versus `wp:anchor`, drawing sizes, relationship targets, and missing image targets.
- high-inline-content line spacing: any paragraph containing `w:drawing`, `w:pict`, `w:object`/OLE/MathType, or OMML with effective `w:lineRule="exact"` is a high-risk clipping case. Final QA must flag it as `fixed_line_spacing_high_inline_content`; the formatter should repair it by applying a direct paragraph `w:spacing w:lineRule="auto"` before delivery, then rerun QA.
- header/footer watermark residue: `word/header*.xml` and `word/footer*.xml` containing `wp:anchor behindDoc="1"` or large anchored drawings can render as proof/sample watermarks. These should be removed when they are image-only background paragraphs, and flagged if still present after cleanup.
- Word fields: `PAGE`, `NUMPAGES`, `TOC`, `REF`, `PAGEREF`, `SEQ`, and other fields that may display stale values until Word updates fields.
- heading hierarchy: generated role heading styles, numbered heading-like paragraphs, level jumps, and numbered non-heading paragraphs that may break TOC behavior.

If object counts drop unexpectedly, or if media/drawing/embedding/table/field counts shrink after formatting, stop and repair before delivery.

Run format-conformance QA immediately after role-style binding and direct-format cleanup, before bibliography numbering, table body formatting, equation tab layout, and superscript markers. This QA is a repair gate: verify generated role styles still match `style_spec.json`, verify every mapped target paragraph uses the expected role style, remove direct formatting that would override role font/size/spacing/indent/alignment, and re-audit. Record repair counts in `format_conformance_qa`; final notes should mention only unresolved or uncertainty-based failures, not deterministic repairs that succeeded.

For final user notes, convert QA findings into concise confirmation items only. Do not list successful formatting. Mention tables, images/floating anchors, high-inline-content spacing repairs or unresolved clipping risk, header/footer watermark cleanup or residue, fields/page numbers/TOC, heading hierarchy, object-count drops, and residual direct formatting only when the internal QA report actually flags them.

## LibreOffice Compatibility Gate

Run this gate after final DOCX repack and structural QA, before user delivery. This gate improves LibreOffice openability without weakening Word/OpenXML fidelity:

```bash
soffice --headless --invisible --norestore --convert-to pdf --outdir lo_compat final.docx
```

Rules:

- Use LibreOffice only to load the final DOCX and export a temporary PDF. This proves that LibreOffice can open the package well enough to render/export.
- Do not save, normalize, repair, or replace the final DOCX through LibreOffice. A LibreOffice-resaved DOCX may rewrite OMML formulas, MathType/OLE objects, floating anchors, fields, numbering, and Word-specific layout.
- Keep the original OpenXML-edited DOCX as the final deliverable when structural QA passes.
- Before this gate, inspect/rewrite package relationship parts so every `*.rels` serializes with the default package relationship namespace. If LibreOffice reports a source-load failure, inspect `word/_rels/document.xml.rels`, header/footer `.rels`, and copied part `.rels` first for `ns0:Relationships`/`ns0:Relationship`.
- Record the gate result as `libreoffice_compatibility_qa` in `qa_report.json`.
- If LibreOffice load/export fails, record `libreoffice_compatibility_failed` in `format_report.json` with the failure kind and stderr tail. Include a concise final user note that LibreOffice compatibility needs checking, but do not silently replace the file with a LibreOffice-normalized copy.
- If Microsoft Word render QA passes but LibreOffice compatibility fails, prefer Word fidelity and report the LibreOffice compatibility risk.

## Render Compare Gate

Rendering is an internal QA gate, not a user deliverable. After producing the final `.docx`, the formatter usually renders both the original target DOCX and the final DOCX to PNG pages and compares them before delivery. This gate is mandatory for native DOCX/DOTX visual templates; absence of `--render-qa-dir` is not permission to skip it for those sources.

Text-rule-source exception:

- If the desired format came primarily from text-only/OCR/non-DOCX-derived rules, skip target-before/final render comparison because the final layout is expected to differ greatly from the original target and visual diff becomes misleading.
- Text-rule sources include explicit plain-text formatting instructions, selectable-text PDF author/submission guidelines, legacy `.doc`/`.dot` converted text rules, OCR text extracted from screenshots/images, and website/image text instructions.
- Use `--format-source-type ocr_text_rules`, `--format-source-type text_rules`, `--format-source-type converted_docx_template`, or set `_meta.source_type` in `rules.json` to one of `text_rules`, `ocr_text_rules`, `image_text_rules`, `screenshot_text_rules`, or `website_text_rules`.
- Record `render_compare_qa` with `enabled=false`, `skipped=true`, `skip_reason=format_source_text_rules`, and record `render_compare_skipped_text_rules` in `format_report.json`.
- This exception skips only target-before/final visual comparison. Structural QA, package relationship checks, object-count audits, and LibreOffice load/export compatibility QA must still run.
- PDF/sample/article/proof sources use this exception in the current route because their visual evidence may select only fallback columns, not style properties. Still run structural QA, LibreOffice compatibility QA, and final local Word visual-confirmation notes.

Render-engine priority is locked:

1. Microsoft Word PDF export.
2. LibreOffice PDF export.
3. System preview/QuickLook when available.
4. Word GUI screenshot only as a last manual fallback.

For automated comparison, use the same engine for both the target-before DOCX and the final DOCX. Never compare `target-before` rendered by LibreOffice against `final` rendered by Word, or any other mixed-engine pair. If either side fails under one engine, abandon that engine and retry both files with the next engine. Record `engine`, `attempted_engines`, and any failure kinds in `render_compare_qa`.

```bash
python render_docx.py target.docx --output_dir render_qa/target_before --engine word
python render_docx.py output.docx --output_dir render_qa/final --engine word
```

The formatter can call the same gate:

```bash
python scripts/format_docx.py \
  -t template.docx -i target.docx -o output.docx \
  --format-report-out format_report.json \
  --qa-report-out qa_report.json
```

If `--render-qa-dir` is omitted, the formatter creates `<output-stem>_render_qa` for native visual sources. The report must include `render_compare_qa`, containing either the selected engine, attempted engines, target-before render status, final render status, page counts, page dimension changes, missing pages, and changed pages; or the explicit text-rule-source skip fields described above. Changed pages are expected after formatting; the purpose is to prove rendering happened and to surface page-count, page-size, or missing-page anomalies.

Inspect the rendered final pages at 100% zoom when possible. Check:

- font substitution or missing glyphs;
- title/author/affiliation/abstract/keywords hierarchy;
- body font, size, line spacing, and paragraph rhythm;
- table borders, cell padding, width, wrapping, and captions;
- equation centering and equation-number right alignment;
- images, floating objects, and captions;
- headers/footers, page numbers, margins, columns, and section breaks;
- reference-list numbering, hanging indentation, and citation superscripts;
- overlap, clipping, excessive blank gaps, and broken page/table breaks.

If rendering fails across all engines, do not claim visual QA passed. Treat it as a render-toolchain or document-compatibility blocker, record `mandatory_render_compare_failed` or `render_qa_failed` in `format_report.json`, keep the DOCX only if ZIP/package structural QA passes, and tell the user to open the file locally in Word for confirmation. If Word rendering fails but LibreOffice rendering succeeds for both files, report that the successful comparison used a lower-priority engine and ask the user to confirm in Word.

The expected execution environment is cloud-side and should already expose the render toolchain. Invoke the toolchain directly; failures are QA findings and must be recorded in the report.

## Visual Diff

For bug-fix regression checks, render two DOCX files and compare:

```bash
python scripts/render_and_diff.py before.docx after.docx --outdir diff_qa
```

Do not use visual diff as a strict pass/fail when the target content differs from the template. Use it to find unexplained changes: missing objects, changed page geometry, broken headers, unexpected pagination, or large layout movement outside the intended formatting scope.

## Legacy Word And Non-DOCX Sources

When a `.doc`/`.dot` source is detected, use a temporary-conversion route with Microsoft Word when available or LibreOffice/`soffice` otherwise only to extract text and optional column-count metadata. When a `.doc`/`.dot` source is converted to temporary `.docx`, or when a PDF/image/website is used as format evidence, mark the evidence source as lower confidence and standard-fallback-backed.

All non-DOCX sources share the same conservative route:

1. Use explicit user rules first.
2. Extract source text rules next, including PDF selectable text, OCR text, website text, converted DOC/DOT body instructions, and visible prose examples.
3. Use reliable visual/geometry evidence only to choose single-column or double-column fallback. For website links, skip this visual/geometry column inference unless the website/user text explicitly names the required column count; otherwise default to single-column.
4. Do not use converted style XML, converted direct formatting, visual role/alignment, headers/footers, support files, or page XML as formatting evidence.
5. Fill the remaining holes with granular fallback.
6. Run structural QA and LibreOffice load/export compatibility QA. Skip target-before/final render comparison as text-rule-source routing, and tell the user to visually confirm in Word.

Native DOCX template text rules and representative displayed/direct formatting remain valid only for native DOCX/DOTX templates. Non-DOCX text rules beat fallback only for explicitly stated properties; final notes must say the source was not DOCX, standard fallback was used for missing formatting, and better accuracy usually needs either a native `.docx` template/source-format file or explicit formatting rules provided directly as text instructions.
