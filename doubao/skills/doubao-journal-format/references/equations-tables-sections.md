# Equations Tables And Sections

Read this before applying equation tab-stop layout, table body formatting, section/page setup, headers/footers, or mixed-column layout repair.

## Equation Layout

Formula paragraphs and equation numbers are often positioned by paragraph tab stops (`w:pPr/w:tabs`) and inline tab runs (`w:tab`), not only by paragraph style.

Mandatory equation-layout behavior:

- Scan template paragraphs containing OMML (`m:oMath` or `m:oMathPara`), including OMML nested inside runs.
- Treat display formulas/equations as an independent `equation` role. Template paragraphs using `DisplayFormula`, `Equation`, or `Formula` styles, MathType/OLE formula paragraphs, numbered graphic-equation paragraphs, and formula-only/numbered formula paragraphs must not be mapped as generic `body`.
- Also detect equation-like object paragraphs in the target, including MathType/OLE embedded objects (`w:object`, `OLEObject`, `objectEmbed`, VML `imagedata` with equation/MathType ProgID) and numbered graphic-equation paragraphs. These are not OMML, but they can still receive paragraph tab-stop layout.
- Detect whether the paragraph has an equation number such as `(1)`, `（1）`, or `(2.3)`.
- Extract paragraph tab-stop definitions: each `w:tab` alignment (`left`, `center`, `right`, etc.) and position (`w:pos`).
- Extract inline tab structure: number of tabs before the formula, tabs between equation and number (`tabs_between_equation_and_number`), and tabs after the number.
- Store this as `equation_layout_map.json` internally.
- After direct-format cleanup, apply the extracted `w:tabs` and required `w:tab` runs to target equation paragraphs, including compatible MathType/OLE object paragraphs.
- Tab-run synchronization is exact, not append-only. If the template says `tabs_before_equation=0`, remove extra pure tab runs immediately before the formula. If the template says `tabs_between_equation_and_number=1`, reduce or add pure tab runs between formula and number until the count is exactly one.
- For MathType/OLE formulas, inspect both paragraph-child pure tab runs and `w:tab` children inside the same `w:r` as the object. Some target files store `TAB + OLE object + TAB + number` as separate runs, while others store tabs inside the object run. Both forms must be normalized.
- Do not treat generated role style IDs such as `14equation`, `DisplayFormula`, or other style names as formula object anchors. Equation anchors must come from OMML, OLE/object/embed/control, equation-like drawing/pict evidence, or explicitly equation-like object attributes, not from `w:pStyle`/`w:rStyle` values.
- Ignore non-layout markers such as `w:lastRenderedPageBreak` when deciding whether a run is a pure tab run; a run containing only `w:tab` plus render markers is still removable tab layout.
- If the template only provides an unnumbered centered formula sample with no `w:tabs`, treat this as valid evidence for formula role/alignment but not for numbered-equation tabs. For target numbered display equations, use the computed fallback below rather than preserving stale target tabs.
- Computed fallback for numbered display equations is mandatory when the template has no numbered-equation tab evidence: compute the active text width from the final target section containing that equation (`pgSz.w - pgMar.left - pgMar.right - pgMar.gutter`, adjusted per column when `w:cols` has multiple columns), set paragraph tabs to a center tab at half of that active width and a right tab at the full active width, remove old target equation tabs, then set exactly one `w:tab` before the formula and exactly one `w:tab` between the formula and the equation number.
- The fallback has Chinese and English single-column/multi-column variants, but all variants use the same geometry rule: single-column equations use the section text width; double-column equations use the computed column width, not the full page/body width. This prevents equations and equation numbers from crossing the column boundary when a single-column manuscript is converted to a two-column template.
- The fallback must be computed per equation paragraph or per active section, not once from the document's final section. Mixed-layout documents can contain single-column front matter, two-column body sections, and later full-width sections; each equation must receive tab stops appropriate to its own section.
- Computed fallback must place the equation number at the right edge of the body text area, not at the physical page edge. Page margins and columns must be respected.
- Apply equation tab layout only to display-equation paragraphs. OLE/MathType objects embedded inside normal prose are inline formulas and must stay as `body`; do not remove their surrounding text or tabs as if the whole paragraph were a display formula.
- If the template equation paragraph has no paragraph-level `w:tabs`, but its style/alignment centers the formula, remove stale target paragraph-level `w:tabs` from equation paragraphs instead of preserving incompatible tab stops.
- Do not modify OMML formula XML, MathType/OLE object XML, field codes, images, or the equation number text itself. Only change paragraph properties and tab run separators.
- After equation layout and after any final direct-format cleanup, protect display and inline equation/object paragraphs from exact fixed line-height clipping. If an OMML, MathType/OLE, drawing, or pict paragraph inherits `w:lineRule="exact"` from body/equation styles or direct `pPr`, override only that paragraph to `w:lineRule="auto"` before repack. This is a visual preservation guard, separate from equation tab layout, and must not rewrite formula/OLE payloads.
- If a target formula has no equation number, apply only the unnumbered formula layout when available; do not invent equation numbers.
- If the template has no equation tab-stop evidence, preserve target equation layout and mention in the final note that formula alignment/equation-number position needs visual confirmation.
- Report counts by equation kind, such as `omml`, `ole_object`, and `numbered_graphic_equation`, in the internal format report.

Few-shot:

| Template evidence | Target equation paragraph | Expected behavior |
|---|---|---|
| Formula + one tab + `(1)`, with center/right tab stops | Formula + `(2)` without tab | Add the template tab stops and insert one tab between formula and `(2)`. |
| Template has unnumbered formula centered by a tab stop | Target unnumbered formula | Apply the unnumbered formula tab-stop layout; do not add a number. |
| Template OMML equation has center/right tab stops | Target MathType OLE equation with `(3)` in the same paragraph | Apply the template paragraph tabs and insert the required separator tabs around the OLE object; do not edit the OLE payload. |
| Template `DisplayFormula` style is centered and has no `w:tabs`; target is `TAB + OLE formula + TAB + (1)` | Map the paragraph as `equation`, apply centered equation style, remove the formula-before tab, and keep only the required tab between formula and number if the template profile requires one. |
| Template has an unnumbered centered OLE/OMML formula and no numbered formula example | Target is `TAB + OLE formula + TAB + (1)` | Compute fallback tabs from the equation's active section/column width, set center/right tab stops, normalize to exactly one tab before formula and one tab before number. |
| Template has no usable formula tab evidence, target has numbered display equations in a two-column body | Target is `OLE formula + (1)` or stale `TAB + OLE + TAB + (1)` | Compute center/right tabs from the column width, not the full body/page width, and normalize the runs to `TAB + formula + TAB + number`. |
| Template has no usable formula tab evidence, target has numbered equations in both single-column and double-column sections | Same document has equations in different sections | Use different computed fallback widths per section: single-column equations use section text width; double-column equations use column width. |
| Target paragraph has an image plus equation number `(4)` and no prose caption words | Treat as a numbered graphic equation candidate and apply paragraph tab layout; do not treat ordinary figures/captions as equations. |
| Target body paragraph contains `text + OLE inline formula + text` | Keep it as `body`; do not apply display-equation tab cleanup. |
| Template has no formula tab evidence | Target formulas exist | Preserve target formula layout and warn the user to check formulas. |

## Table Body Formatting

`table_caption` only formats the text above or below a table. It does not format the table body. Table body formatting must have its own bridge file, `table_format_map.json`.

For Chinese fallback with bilingual front matter and no stronger template evidence, figure/table captions should be bilingual: Chinese caption first, English translation in the immediately following caption paragraph. Do not put the English translation in the same paragraph via a soft line break or raw newline; separate paragraphs make spacing and role mapping auditable.

Mandatory table behavior:

- Scan every template `<w:tbl>` and extract table body XML features, not only nearby captions.
- Score every template table for formatting strength before applying it to targets. Border evidence, cell border evidence, table styles, shading, margins, header-row evidence, and internal paragraph/run formatting make a table stronger. Text volume alone must not make a table representative.
- Treat tables with little or no border/style evidence as weak or possible placeholder/occupancy tables.
- Extract table-level properties from `w:tblPr`, including `w:tblStyle`, `w:jc`, `w:tblInd`, `w:tblCellSpacing`, `w:tblLook`, `w:tblCellMar`, `w:shd`, and especially `w:tblBorders`.
- Treat table width (`w:tblW`) and layout (`w:tblLayout`) as protected layout-size properties, not ordinary formatting children. Do not include them in broad `tblPr` overwrite.
- Extract every table-border side separately: `top`, `bottom`, `left`, `right`, `insideH`, and `insideV`, including `val`, `sz`, `space`, `color`, `themeColor`, and related attributes.
- Extract row-level properties from `w:trPr`, including header-row repeat `w:tblHeader`, row height, `cantSplit`, row alignment, and row cell spacing.
- Extract representative row profiles for header row, body rows, and footer/last row. Three-line tables usually encode top line on the table/header, header bottom line on the first row's cells, and bottom line on the last row or table border.
- Extract cell-level formatting properties from `w:tcPr`, including `w:tcW`, `w:tcBorders`, `w:shd`, `w:tcMar`, `w:textDirection`, and vertical alignment. Recognize merge/topology properties such as `gridSpan`, `hMerge`, and `vMerge` for audit, but do not force template merge topology onto target tables.
- Extract each cell-border side separately: `top`, `bottom`, `left`, `right`, `insideH`, `insideV`, `tl2br`, and `tr2bl` when present.
- Extract representative table-internal paragraph/run formatting from non-empty cells so table text font, size, bold, alignment, spacing, and vertical alignment do not remain from the target.
- Apply the extracted table profile to target tables after direct-format cleanup. Replace only formatting containers; never rewrite cell text, formulas, drawings, media, field codes, or relationship parts.
- Preserve target table width by default when the template table width is `auto`, missing, or `w:w="0"`. Many templates use `w:tblW w:type="auto" w:w="0"` only to let the sample table fit its content; copying it can shrink target tables from full page width to content width.
- Override target table width only when the template provides explicit width evidence such as `w:type="pct"` with nonzero `w:w` or `w:type="dxa"` with nonzero `w:w`, or when the run uses `--allow-table-width-override`.
- If target width is preserved because template width is auto/unspecified, record this in `format_report` as `table_width_preserved`.
- Preserve table topology: do not change row count, column count, `gridSpan`, `vMerge`, `hMerge`, or nested tables during automatic formatting.
- If template and target table counts differ, do not hard-match by index. Use the strongest representative template table profile for target tables by default, so a weak second template table cannot remove borders from target table 2.
- If template and target table counts match, index matching is allowed only when the matched template table has enough formatting evidence. If the matched template table is weak and the representative template table is much stronger, bypass the weak profile and use the representative profile.
- Record representative-table reuse and weak-profile bypasses in `format_report`, including template table index, target table index, and reason.
- If no template table exists, or the only template tables are weak/placeholder tables without usable border/style evidence, apply the table fallback for both Chinese and English templates from `assets/fallback_ooxml_spec.json`: a conservative academic three-line table with top rule, header bottom rule, bottom rule, and no vertical/internal grid lines. Apply only border/cell-formatting XML from the selected language/column variant; preserve target table width, row/column count, merge topology, cell text, formulas, drawings, and media. Report `table_three_line_fallback` so the user confirms table borders visually.
- Three-line fallback must not rely on table-level `tblBorders` alone. Use the bundled sample `tblPr_xml` as a coarse backup and also write bundled or computed cell-level borders: first row every cell gets top thick rule, inferred final header row every cell gets bottom thin rule, final row every cell gets bottom thick rule, and left/right/inside borders use `none` rather than `nil`. This is required because Word may hide table-level top/bottom when cell borders override or conflict with them.
- For composite/multi-row headers, infer the last header row conservatively from merge topology, effective column spans, spanning group cells, short label/subheader rows, and the first data-like row with multiple numeric/percentage/checkmark cells. Put the header-bottom rule below the final header row, not always below row 1. When the inferred header has more than one row, add a thin horizontal separator between header levels so grouped headers such as `准确度` over `Top1/Top5` remain visually separated. If the template provides explicit multi-row header borders, template XML wins over fallback inference.

Few-shot:

| Template evidence | Expected behavior |
|---|---|
| Three-line table: table `top/bottom`, header row/cell `bottom`, no inside vertical lines | Target table receives cell-level top line on first row, header-bottom line under the final header row, bottom line on the final row, and no vertical/internal grid lines. |
| Template table has full grid with `insideH/insideV` and cell `tcBorders` | Target table receives matching horizontal and vertical grid lines. |
| Template has a styled `List Table 6 Colorful` table style plus explicit cell borders | Copy/apply the table style reference and explicit `tblBorders/tcBorders`; do not stop at paragraph roles. |
| Template has table 1 as a three-line table and table 2 as a borderless placeholder; target has 9 tables | Use table 1 as the representative format for target tables. Do not map target table 2 to the borderless template table 2. |
| Template/target both have 2 tables, but template table 2 has no border/style evidence while table 1 has strong borders | Bypass template table 2 and use the representative strong table for target table 2; report `table_weak_template_profile_bypassed`. |
| Template table has `w:tblW w:w="0" w:type="auto"` and target table has `w:tblW w:w="5000" w:type="pct"` | Preserve target `pct=5000`; apply borders/fonts/alignment but do not shrink the table. |
| Template table has explicit `w:tblW w:w="5000" w:type="pct"` | The explicit width may override target width unless the user has locked a reviewed table map. |
| Template has only a table caption and no actual table | Apply the conservative three-line table fallback to target tables and warn that table borders/body layout need confirmation. |
| English template has no usable table XML or only a weak placeholder table | Apply the same three-line table fallback; do not preserve target full-grid/vertical lines merely because the template is English. |
| Fallback three-line table renders without a visible top line in Word | Repair by writing first-row cell `tcBorders/top` explicitly; table-level `tblBorders/top` alone is not enough. |
| Header row 1 has a merged group cell such as `准确度` spanning two columns, row 2 has `Top1` and `Top5`, and row 3 starts data such as `87.60`/`97.55` | Treat rows 1-2 as the table header and place the header-bottom rule below row 2. |
| A fallback table has two header rows but only row 1 received the header bottom line | Repair by writing cell-level bottom borders to every cell in the final inferred header row and a thinner separator between header rows. |
| Row 1 is short labels and row 2 already contains multiple numeric data cells | Treat only row 1 as the header; do not swallow row 2 as a subheader just because it is short. |

Fallback table XML source:

- Select `zh_single`, `zh_double`, `en_single`, or `en_double` from `assets/fallback_ooxml_spec.json`.
- Use `tables.three_line.tblPr_xml`, `header_tcPr_xml`, `body_tcPr_xml`, and `footer_tcPr_xml` as the primary fallback.
- Do not copy `tblW type="auto" w="0"` from the sample over target table width. Preserve target width unless the source template has explicit nonzero `pct/dxa` width or the user passes `--allow-table-width-override`.
- Keep the final cell-border enforcement pass even when the bundled XML is applied; it protects Word rendering of the top/header/bottom rules across target tables with inherited cell borders.
- Record `three_line_header_inference` and `three_line_multi_header_separator_enforced` in the internal table stats so multi-row header decisions can be audited when the rendered table still looks off.

## Section Routing

Word documents may contain multiple sections. Section properties can live in the final `body/sectPr` or inside paragraph properties as `pPr/sectPr`. Treat every `sectPr` as active page setup.

Mandatory behavior:

- Extract all template `sectPr` records, not only the final `body/sectPr`.
- If template and target section counts match, apply template section geometry by position.
- If the target has only one section but the template clearly has a mixed-column front/body structure, insert a continuous section break before target body text before applying page setup.
- Automatic section insertion is allowed only when all of these are true: the template has multiple section profiles, the chosen front/body sections have different column counts, the target currently has exactly one section, and the target body start can be located after abstract/keywords/front matter.
- Locate the target body start conservatively from role evidence: after title/author/affiliation/abstract/keywords/metadata, the first `heading1/heading2/heading3/body` paragraph can start the body section. If the body start is unclear, do not insert a section break; warn instead.
- Insert the break as paragraph-level `pPr/sectPr` on the paragraph immediately before body start, using the template front-matter section geometry. The final/body `sectPr` then receives the selected template body geometry.
- If counts differ and both have multiple sections, do content-aware section routing. Classify each template and target section as front matter, body, back matter/reference, or unknown from the text roles inside that section. Apply the template front-matter section to target front matter, the template body section to target body, and the template back/reference section to target back matter. Do not simply repeat the template final section.
- Treat `w:cols` as a key layout property, not just a passive child of `sectPr`.
- For mixed-column journal templates, do not choose the first multi-column body-like section blindly. Score all body-section candidates and choose the representative body section by column count, real body evidence, heading/abstract/keyword/reference evidence, section length, and penalties for front-matter/title/author/affiliation-heavy sections, tiny sections, and caption-only sections.
- By default, prefer a strong two-column body candidate over a three-column section when the three-column section is short or dominated by title/author/affiliation content. Three-column regions in templates are often author grids or special front-matter layouts, not the actual paper body.
- If the template has multiple body-like sections with different `w:cols`, print every candidate's section index, column count, character count, score, and the chosen section. Warn the user that body columns need visual confirmation.
- Provide a manual override such as `--body-cols 2` when the template's real body column count is known or the automatic score is ambiguous.
- For mixed-column journal templates, apply the chosen representative body section's `cols` to target body sections even when it is not the final template section.
- If the target has one section and the source is a native template without safe mixed-column evidence, use the template final/body section.
- If the source is weak/non-`.docx`/blank-carrier and the selected fallback is double-column, do not apply the body/double-column `cols` to the whole one-section target. Use the fallback front section for title/author/metadata/abstract/keywords, insert a continuous section break before the target body start, then apply the fallback body double-column section. If the body start is unclear, keep the one remaining section single-column and warn rather than making front matter double-column.
- Apply `pgSz`, `pgMar`, `cols`, and `docGrid` to every target `sectPr`, not only `body/sectPr`.
- Preserve section identity fields such as `type` and `titlePg`, but replace page geometry fields with template values.
- Remove old target `headerReference` and `footerReference` entries from every target `sectPr`.
- Insert template header/footer references into every target `sectPr`.
- Print and audit the number of sections processed. A multi-section target must report all sections, for example `Applied page setup to 6 section(s)` and `Applied headers/footers to 6 section(s)`.
- When section counts differ, print the template section profile sequence, target section profile sequence, and the chosen route, including each section's `cols` count. If no template body section with multi-column `cols` exists but the target has body sections, warn that body column layout needs visual confirmation.
- Record automatic mixed-column section insertion in `format_report` as `mixed_column_section_inserted`, including front/body column counts, target body-start child index, and chosen template body section index.

Failure mode to avoid: applying ACM page setup only to the final `body/sectPr` while earlier paragraph-level sections keep the target A4 page size, old margins, old columns, or stale footers. This makes the output visually unlike the template even when paragraph styles are correct.

Failure mode to avoid: in templates with `front single-column -> body double-column -> back single-column`, do not use the final single-column section as the fallback for every target body section. The body area must receive the body/double-column `w:cols` when the template provides one.

Failure mode to avoid: in templates with `single-column title -> three-column author grid -> two-column body -> full-width figure -> two-column references`, do not select the three-column author grid as the representative body section merely because it is the first multi-column section. The representative body section should be the longer two-column section with body/heading/abstract/keyword/reference evidence. The IJCA mixed single/double-column template is a canonical example.

Failure mode to avoid: when a target paper starts as a single-section manuscript and the template is `front single-column -> body double-column`, do not apply the body/double-column `cols` to the whole document. Insert a section break before the target body start so title, abstract, and keywords remain in the front-matter column layout while body text receives the body column layout.

Failure mode to avoid: when the format source is PDF/DOC/image/website/text rules and only selects the bundled double-column fallback, do not assume the fallback means all content is double-column. The fallback double-column variants are front-single/body-double for both Chinese and English. If no safe body-start split exists, single-column front layout is safer than double-column front matter.

Do not let section routing affect role routing. Sections only control page geometry/header/footer. They must not reset paragraph role state, choose style sources, or make the model restart classification after each section. If adding multi-section support appears to make mapping worse, inspect `style_spec.json` and `role_map.json`: the likely fault is role source selection or classifier state, not the section XML update itself.

## Chinese Metadata Tab Layout

Whenever the target document explicitly contains Chinese classification metadata such as `中图分类号：TP311；TP391. 文献标志码：A`, format only that metadata pair as one paragraph with a right-aligned tab stop, not justified text and not repeated spaces. This is a deterministic target cleanup, not a weak-source-only fallback, because native DOCX templates can also contain manually spaced or untrustworthy metadata rows:

- Keep `中图分类号：...` at the left.
- Insert exactly one tab before `文献标志码：...`.
- Set the tab stop to `right` at the body text boundary computed from `pgSz.w - pgMar.left - pgMar.right - pgMar.gutter`.
- Set paragraph alignment to `left`; remove `both`/`distribute` justification and stale paragraph tabs.
- If the two fields are in adjacent paragraphs, merge only those two metadata paragraphs and move any paragraph-level `sectPr` from the removed paragraph to the kept paragraph so section routing is preserved.
- Run this after role-map-dependent passes such as reference numbering and superscript mapping, because merging paragraphs earlier can invalidate paragraph indexes.
- Apply it for native DOCX templates and weak/non-DOCX/blank-carrier sources alike unless the user explicitly disables it or gives a conflicting instruction.
- Do not infer this layout for unrelated metadata such as article number, received dates, funding, DOI, author affiliations, or citation-format lines.

Few-shot:

| Target metadata evidence | Expected behavior |
|---|---|
| One paragraph contains both `中图分类号` and `文献标志码`, separated by many spaces and justified | Replace the separator with a Word tab, add one right tab stop at the text boundary, and set `w:jc` to `left`. |
| `中图分类号：TP311` and the next paragraph is `文献标志码：A` | Merge into one metadata paragraph with one tab separator; do not merge unrelated metadata or body text. |
| Native DOCX route contains a `中图分类号` + `文献标志码` row with manual spaces, first-line indent, or justification | Still apply the one-line tab repair; this row is a known Chinese classification metadata layout, not generic metadata styling. |
| Native DOCX template explicitly gives a conflicting user/template instruction for this row | Follow the explicit instruction and report the conflict instead of applying the automatic tab repair. |

## Multi-Column Object Width Fitting

When section routing changes a body area from single-column to multi-column, wide objects from the original manuscript can remain at single-column/page width. This must be handled as a layout adaptation step after final section geometry exists:

- Compute the active text width for each section from `pgSz - left/right/gutter`, then compute the column width from `w:cols/@num` and `w:cols/@space`.
- In sections with more than one column, any inline or floating drawing whose `wp:extent/@cx` exceeds the active column width should be scaled down to fit the column while preserving aspect ratio. Update the matching drawing extents consistently.
- Skip small icons/logos and other tiny objects; do not enlarge objects.
- In multi-column sections, wide tables should be constrained to the active column width when their explicit `tblW`, `tblGrid`, or row cell widths exceed the column. Preserve row/column count, merge topology, text, formulas, drawings, and media.
- This fitting pass must run after page setup/section insertion and after table body formatting, because both can affect the final width context.
- Record scaled drawings/tables in the internal report and final risk notes. The user should visually confirm readability and placement.
- If the template intentionally uses full-width figures/tables through separate single-column sections, do not force those objects into a two-column section; section routing should keep/insert the full-width section first.

Few-shot:

| Situation | Expected behavior |
|---|---|
| Target manuscript is single-column, template body is two-column, a body image is 6.8 inches wide | Scale the image down to the computed column width and keep aspect ratio. |
| Target has a small icon under 0.5 inch in a two-column section | Leave it unchanged. |
| Target has a 100% page-width table in a two-column body section | Fit table width/grid/cell widths to the column while preserving content and merge topology. |
| Template has a full-width figure section between two-column body sections | Keep the figure in the full-width section when section evidence supports it; do not shrink solely because other sections are two-column. |
