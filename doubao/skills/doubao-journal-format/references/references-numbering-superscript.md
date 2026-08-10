# References Numbering And Superscript

Read this before migrating numbering definitions, repairing bibliography numbering, or applying run-level superscript markers.

## Numbering Definitions

Paragraph styles may reference numbering through `w:pPr/w:numPr/w:numId`. These IDs are document-local and cannot be reused directly across DOCX packages.

Mandatory numbering behavior:

- Scan every generated non-reference role style for `numId` references before installing the styles.
- Load template `word/numbering.xml` and find each referenced `<w:num w:numId="...">`.
- Copy the referenced `<w:num>` and its linked `<w:abstractNum>` into the target `word/numbering.xml`.
- Allocate new target `abstractNumId` and `numId` values that do not conflict with the target document.
- Rewrite the generated role style `numId` values to the newly allocated target IDs before writing `styles.xml`.
- If the target package has no `word/numbering.xml`, create it and add the required relationship and `[Content_Types].xml` override.
- Report missing template `numId` definitions in the internal format report and warn the user that numbered styles need visual confirmation.

Never copy a template style containing `numId` without also copying and remapping its numbering definitions. Directly preserving template `numId=3` or `numId=14` in the target is invalid unless those IDs were explicitly created in the target numbering part.

This affects headings, custom numbered paragraph styles, and automatically numbered reference-list styles. Reference-list items are handled by the dedicated strategy below: visible-prefix templates use text repair, while Word-automatic templates keep/migrate `reference_item` `numPr`.

Heading numbering has an additional conflict mode. If the template heading style has `w:numPr` but the target heading text already contains a visible/manual number prefix, do not show both. The formatter should create a no-number mirror of the generated heading style and bind only those manually numbered heading paragraphs to the mirror. Plain headings without a manual prefix should keep the original automatic-numbering heading style.

## Reference List Numbering Repair

Reference-list numbering has two mutually exclusive modes, separate from body reference-citation superscripts:

1. `visible_text`: the template reference entries visibly contain prefixes such as `[1]`, `1.`, or `1)`. In this mode, repair visible target prefixes and remove conflicting Word automatic numbering from `reference_item`.
2. `word_auto`: the template reference entries get their numbers from a paragraph style such as ACM `Bibentry` with `w:numPr/w:numId`, and the paragraph text itself has no prefix. In this mode, preserve/migrate the style numbering and do not add visible prefixes.

Mandatory behavior:

- Extract explicit template reference-list numbering evidence from real `reference_item` examples, such as `[1]`, `［1］`, `1.`, `1．`, `1、`, or `1)`.
- Also inspect the selected template `reference_item` style source, especially `IOPRefs`, `Bibentry`, `BibEntry`, `References`, and `Bibliography`, for effective `w:pPr/w:numPr` after expanding the full `basedOn` chain. If the leaf style lacks `numPr` but an inherited parent style supplies it, classify the map as `word_auto`; do not misclassify it as unnumbered merely because the leaf style is sparse.
- Store this evidence in `reference_numbering_map.json` internally.
- Apply repair only after target paragraphs have already been mapped to roles.
- Only repair target paragraphs whose role is exactly `reference_item`.
- Do not mix Word automatic paragraph numbering with visible reference prefixes. In `visible_text` mode, before repair, remove paragraph-level `w:pPr/w:numPr` from every mapped `reference_item`; while installing role styles, remove `w:numPr` from the generated `reference_item` style.
- In `word_auto` mode, do the opposite: keep the generated `reference_item` style `w:numPr`, include its `numId` in numbering-definition migration, and do not prepend visible text numbers.
- Reference-list indentation is coupled to numbering mode. In `visible_text` mode or unnumbered reference styles, if `reference_item` has no explicit `w:ind` evidence, add a conservative default paired hanging indent `<w:ind w:left="420" w:hanging="420"/>` so the first line starts at the normal text boundary and wrapped lines align after the visible marker.
- This default hanging indent guard must run during style installation after `reference_numbering_map.json` is known, not only during early fallback construction. Native `.docx` templates can be high-confidence style sources and still omit `w:ind`; if the reference numbering mode is `visible_text` or non-automatic, create the missing `w:ind` instead of merely reporting `reference_item_missing_hanging_indent`.
- Never emit `w:hanging` alone for visible-text `reference_item`. In OOXML, first-line start equals `left - hanging`; if `left` is missing/zero and `hanging="420"`, the first line starts at `-420` twips and can protrude past the body left edge.
- In `word_auto` mode, do not add style-level fallback hanging indentation when the style has `w:numPr`; Word automatic numbering definitions usually carry their own `numbering.xml` level indentation.
- User rules and template prose rules outrank this fallback. Accept `indent`, `ind`, `indentation`, and `paragraph.indentation` forms for `reference_item`, including `hanging`, `hangingIndent`, `firstLine`, and `firstLineIndent`.
- If user rules or template prose provide only `hanging`/`hangingIndent` for visible-text `reference_item`, automatically set `left` to at least the same value. If both are present but `left < hanging`, raise `left` to `hanging`.
- Record in `format_report` when `reference_item` hanging indentation was filled by fallback, and warn when neither style indentation nor automatic numbering controls indentation.
- Normalize the whole mapped reference list in paragraph order, not only the missing paragraph. If an item already starts with a recognized number but it is no longer the expected sequence number or pattern, replace the visible prefix with the expected number.
- If a target reference item has no number and looks like the start of a bibliography entry, prepend the next sequential number using the template pattern, then continue numbering subsequent items from that inserted number.
- If a target reference item already starts with the expected recognized number and pattern, preserve it.
- Do not repair uncertain continuation lines, URLs, DOI-only lines, headings, captions, formulas, body citations, or any paragraph outside `reference_item`.
- If the template has no explicit reference-list numbering evidence, do not invent reference-list numbers. Report this in `format_report` and user-facing notes.
- Exception for weak/non-DOCX text-rule sources: because there is no reliable Word XML numbering evidence, use the standard visible-text fallback `[1]`, `[2]`, ... only for paragraphs already mapped as `reference_item`, unless explicit text rules specify another reference-prefix style or disable numbering. This fallback must still skip uncertain continuation lines, URLs, DOI-only lines, headings, captions, formulas, body citations, and every paragraph outside `reference_item`; report the fallback and ask the user to confirm bibliography order.
- If numbers were added or renumbered, report the count and tell the user to confirm bibliography order, because numbering is assigned by target reference-item order.

Few-shot:

| Template evidence | Target reference-zone paragraph | Expected behavior |
|---|---|---|
| Template examples start `[1]`, `[2]` | `Ren Guo-yin, LV Xiao-qi, LI Yu-hao. Real-time action recognition... [J]. ...` mapped as `reference_item` | Add `[n] ` before the paragraph using the next reference number. |
| Template examples start `[1]`; previous target item became `[11]` after a missing reference was repaired | Existing `[11] SHAN W...` mapped as the next `reference_item` | Replace the visible prefix with `[12]`; do not leave duplicate `[11]`. |
| Template examples start `[1]` | `[7] CHEN Y, ZHANG Z...` mapped as `reference_item` and expected sequence number is 7 | Preserve `[7]`; do not duplicate. |
| Target reference paragraph has Word `numPr` auto-numbering plus visible `[10]` | `[10] 任国印...` mapped as `reference_item` | Remove paragraph `numPr`; keep/normalize only the visible `[10]` prefix so Word does not display `[10] [10]`. |
| ACM template `Bibentry` has style `numPr`, and reference paragraph text starts directly with author/year | Target reference entries mapped as `reference_item` | Preserve/migrate `13referenceitem` style `numPr`; do not add `[1]` text and do not strip automatic numbering. |
| IOP template `IOPRefs` inherits `w:numPr` from a parent style | Target reference entries mapped as `reference_item` | Preserve/migrate inherited automatic numbering into `13referenceitem`; do not add visible `[1]` prefixes. |
| Chinese sample template has visible `[1]` examples but no `w:ind` on `reference_item` | Target reference entries wrap onto second lines | Add default `<w:ind w:left="420" w:hanging="420"/>` to `13referenceitem` unless user/template rules provide another safe indentation. |
| ACM/IEEE `Bibentry` has `w:numPr`, and `numbering.xml` level has hanging indentation | Target reference entries use Word automatic numbers | Keep numbering-level indentation; do not add a second style-level `w:hanging="420"`. |
| User `rules.json` contains `{"reference_item":{"paragraph":{"indentation":{"hanging":"360"}}}}` | Visible-text references | Write `<w:ind w:left="360" w:hanging="360"/>`; do not leave `hanging` without `left`. |
| Template/user rule says `悬挂缩进2字符` | Visible-text references | Write `<w:ind w:left="420" w:hanging="420"/>`, not only `w:hanging="420"`. |
| Template has no numbered reference examples | Numberless target references | Do not add numbers; warn that reference-list numbering was not repaired because template evidence was missing. |
| Non-DOCX source has no Word XML numbering evidence and no explicit contrary rule | Numberless target paragraph mapped as `reference_item` | Add standard `[n] ` visible prefix by reference-item order; warn user to confirm order. |
| Target paragraph is a URL continuation or DOI-only line | `https://...` mapped in the reference zone | Do not add a new number; treat as uncertain continuation. |
| Body text contains `[1]` citation | `method [1] shows...` | Do not treat it as reference-list numbering. Body citation superscript is handled only by `superscript_map.json`. |

## Run-Level Superscript

Superscript is not a paragraph style. Extract and apply it through a separate `superscript_map.json` bridge:

1. Scan template runs with `w:vertAlign w:val="superscript"`.
2. Classify superscript evidence by role before applying it. Author/affiliation markers and body reference-citation markers are separate categories.
3. Record author/affiliation markers only from author or affiliation roles, such as `1`, `2`, `*`, and `†`.
4. Record body reference-citation markers only from body text where the template explicitly uses citation-like markers such as `[1]`, `(1)`, or `^1`. Do not treat author/affiliation numbers `1`, `2`, `3` as evidence for body reference citation style.
5. Apply the map after role binding and direct-format cleanup, because cleanup removes run direct formatting.
6. Clear accidental whole-paragraph superscript only in author/affiliation roles, then split simple text runs and set `vertAlign=superscript` only on the matched marker text.
7. Skip complex runs containing drawings, fields, formulas, tabs, or multiple text nodes instead of rewriting them.
8. If the template has no author/affiliation superscript evidence, do not create author/affiliation superscripts.
9. If the template has no reference-citation superscript evidence, do not change target body reference citations at all. Preserve the original target citation formatting and mention this in the user-facing notes.
10. If the target author line has no marker text, do nothing. Never turn an entire author or affiliation line into superscript.

Few-shot:

| Template evidence | Target text | Expected behavior |
|---|---|---|
| Author has `Alice` + superscript `1` | `Alice1, Bob2` | Split text runs and superscript only `1` and `2` if markers are in the map. |
| Affiliation has superscript `1` | `University1` | Superscript only the trailing `1`; keep `University` normal. |
| Template has no superscript markers | `Alice1` | Leave target unchanged. |
| Body citation marker is superscript `[1]` | `method[1]` | Superscript only `[1]`; do not superscript every digit in body text. |
| Template only has author superscript `1`, `2`, `3` and no body citation superscript | `method[1] [2] [4]` | Leave all target body citations unchanged and warn the user that reference-citation superscript format was not extracted. |
