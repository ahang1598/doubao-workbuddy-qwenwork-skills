# Style Spec And Routing

Read this before generating or consuming `style_spec.json`, classifying roles, applying text rules, installing role styles, or cleaning direct formatting.

## Intermediate Style Spec

The role style spec is the mandatory bridge between template extraction and target formatting. It must be generated from the template only, then consumed by the target stage. Target styles, target style names, and target direct formatting must never influence what a role should look like.

All source formats must enter this same bridge. Do not maintain separate target-formatting routes for native `.docx`, legacy `.doc`, PDF, images, or website rules after evidence extraction. Convert every usable source into a role-based `style_spec.json`, then classify the target into `role_map.json`, then apply the spec. The only difference between source formats is evidence priority and confidence.

When `references/template-distill-render-qa.md` is used, `template_evidence.json` or `qa_report.json` may support `style_spec.json` only on the template side. Target-before QA can warn about direct-format cleanup needs and object-preservation risks, but it must not define the desired role style. The target file answers "where is each role"; the template evidence answers "how each role should look."

Source-aware priority is locked:

- Native `.docx`/`.dotx`: `user_rules > template_text_rules > representative_template_direct_format > template_style_xml > property-level granular fallback only for explicit prose text rules with missing/default core properties`. Do not inject whole-role bundled fallback into clean native DOCX styles because missing properties can be intentional Word inheritance. Instruction-heavy native DOCX templates are different: if text says `摘要：楷体小5号` or `文章正文是5号宋体` but the paragraph/style exposes no real line spacing, indentation, or paragraph spacing, preserve the explicit font/字号 and fill only the missing paragraph properties from granular fallback.
- All non-DOCX sources, including legacy `.doc`/`.dot`, PDF, screenshot/image/OCR, website, and externally supplied visual rules: `user_rules > extracted_text_rules > source_column_detection_for_fallback_variant > bundled_OOXML_fallback > legacy_dictionary_fallback`. For website links, the source-column step is allowed only when website/user text explicitly says single-column or double-column manuscript layout; otherwise choose single-column fallback and record `website_unspecified_columns_default_single`.

Priority wording is important: "non-DOCX source is lower confidence" means the carrier lacks reliable Word XML style parts. It does not mean extracted text rules are weaker than fallback. Explicit text rules must lock the exact property channels they mention, and fallback may only fill unstated or unsafe-default channels. Re-apply explicit user/text rules after fallback merge.

Rules JSON explicit fields do not need `source` or `confidence` to be honored. A role rule containing deterministic formatting keys such as `size`, `font_size`, `fonts`, `font`, `spacing`, `line_spacing`, `indent`, `paragraph.indentation`, `align`, `bold`, `italic`, `color`, `tabs`, or `numbering` is an explicit text/user rule by structure and must survive non-DOCX sanitization. Drop only fields marked as visual/geometry inference, such as `source=visual_role_alignment`, `pdf_visual`, `visual_supplement`, or similar visual-only evidence.

Rules JSON must be normalized before any visual sanitization, text-rule merge, fallback merge, or style installation. Accept both the flat schema and OOXML-summary schema:

```json
{
  "roles": {
    "body": {
      "size": "24",
      "spacing": {"line": "480", "lineRule": "auto"}
    }
  }
}
```

```json
{
  "body": {
    "summary": {
      "pPr": {"spacing": {"line": "480"}},
      "rPr": {"sz": {"val": "24"}}
    }
  }
}
```

The second form must normalize to `body.size="24"` and `body.spacing={"line":"480","lineRule":"auto"}`. `summary.pPr.ind`, `summary.pPr.jc`, `summary.rPr.rFonts`, root-level `pPr/rPr`, and `paragraph.pPr` are also valid sources for the same flat fields. Record accepted summary paths in `rules_schema_diagnostics.normalized_fields`. Invalid role names or role rules with no recognized deterministic fields must generate schema warnings; do not silently run fallback as if the user rule succeeded.

Spacing normalization is mandatory, not cosmetic. WordprocessingML `w:spacing/@w:line` is not a free-form decimal field. Convert semantic line-spacing rules before writing XML: `1.5`/`1.5x`/`一倍半` -> `360` with `lineRule="auto"`, `double-spaced`/`double line spacing` -> `480`, `single-spaced`/`single line` -> `240`, and exact point spacing -> points*20 with `lineRule="exact"`. This applies to flat rules, OOXML-summary rules, extracted website/PDF text, legacy DOC text, `style_spec.json`, role `style_xml`, `pPr_xml`, `Normal`, `docDefaults`, and any final direct paragraph spacing. If a reused spec already contains `w:line="1.5"`, repair it before repack and record the repair in QA.

Website author guidelines are not native Word templates. Pages such as Nature formatting guides often state submission rules such as `Contributions should be double-spaced and written in English`, organization order, title length, reference limits, and figure/table placement, but not full Word style XML. Treat these as high-priority extracted text rules for the properties they state; map manuscript-wide rules to content roles such as abstract/summary, body, reference items, captions, and display equations. Missing typography, paragraph spacing, table XML, equation tabs, and page setup still come from the selected standard fallback. Do not infer Nature/Science production PDF layout or double columns from the website brand when the manuscript guide does not explicitly require it.

When the source is non-DOCX or a blank carrier DOCX used only because the formatter requires a package, the carrier template must be treated as unformatted. Start generated role styles from a clean style shell and write only properties from explicit text/user rules plus granular fallback. Do not inherit blank-template, converted DOC/DOT, PDF, website, OCR, or Word built-in Heading/Reference colors, underlines, borders, small caps, theme colors, stale sizes, single line spacing `w:line="240"`, style links, support files, headers/footers, or page XML. Visual/geometry evidence may only provide reliable `fallback_columns`, except website links where visual/brand/page-layout evidence must not provide double-column fallback without explicit website/user text.

Blank/carrier templates must materialize fallback instead of preserving Word defaults:

- If the source package has no meaningful format text/sample content but external rules exist, route it as `blank_carrier_template`.
- Generate `docDefaults` and `Normal` from the body fallback baseline, not from the blank Word package.
- Generate every role style from explicit text/user rules plus granular fallback. A blank carrier's existing `Normal`, `Heading1`, `Heading2`, and `Bibliography` styles are containers only.
- Validate at least `title`, `heading1`, `body`, and `equation` role styles after spec creation. For Chinese fallback, `title` and `heading1` must have explicit `w:spacing w:before="240" w:after="120" w:line="360" w:lineRule="auto"` where defined by fallback, `body` must have `w:line="360"`, and `Normal/docDefaults` must not remain at blank-template `w:line="240"` when the fallback language is Chinese.
- If user rules explicitly set body spacing, such as `line="480"`, materialize that same locked spacing into weak-source `docDefaults` and `Normal` after fallback merge. Do not leave `Normal` at `w:line="240"` while `9body` has `w:line="480"`, because unbound/body-like paragraphs can display with Normal spacing.
- When reusing an old `style_spec.json` created from a blank carrier, repair it before installation by rebuilding low-confidence role styles from the current fallback. Do not let stale `style_xml` carry the old carrier's 240-line spacing back into QA repair.

When the format source began as legacy `.doc` or `.dot` and was converted to temporary `.docx`, the converted package is only a text-extraction carrier. Do not use converted `styles.xml`, `Normal`, `Heading`, bibliography styles, representative paragraph/run direct formatting, rendered visual crosscheck, settings/fontTable/theme, headers/footers, or page XML as style authority. If converted text rules such as `正文五号宋体` are found, they lock only the stated properties; missing properties come from fallback. If the converted/rendered source reliably exposes single-column or double-column layout, record only `fallback_columns` for variant selection and final risk notes.

Legacy `.doc`/`.dot`, PDF, screenshot/image/OCR, website, and plain text rules must use the same bridge. Extract text rules and optional column-count metadata only; after that, the target formatting stage is still role-map plus style-spec application. Do not let a converted `Normal`, `Heading`, bibliography style, blank carrier, website display stylesheet, or PDF/OCR visual sample define blue headings, red underlined references, exact colors, exact fonts, underlines, local emphasis, role alignment, spacing, indentation, tabs, or other default shell formatting.

For converted `.doc`/`.dot`, do not hardcode `fallback_columns=1`. Although converted OpenXML is not style authority, the converted `sectPr/w:cols` count is allowed low-confidence structural evidence for choosing `zh_single`, `zh_double`, `en_single`, or `en_double`. If the converted package has any section with `w:cols/@w:num >= 2`, choose double-column fallback unless explicit user/rules metadata says otherwise. If `sectPr` detection fails, use source filename keywords such as `双栏`, `单栏`, `two-column`, or `single-column` as lower-priority hints, then default to single-column with a warning.

For non-DOCX sources, never replace an entire role with fallback just because one property is missing. Merge at property level. A rule like `正文宋体五号` locks body font and size; missing line spacing must come from fallback, not coarse visual evidence or converted-DOC direct formatting. A short rule paragraph can provide font/size wording but must not donate its paragraph spacing, indentation, tabs, color, or border.

If a website guideline says `正文 12 pt Times New Roman` and says nothing about spacing, body font/size must be `12 pt Times New Roman`; spacing may come from fallback. Do not report this as the text rule being weaker than fallback.

Apply the same property-level merge to native DOCX instruction templates. A native `.docx` is not automatically a high-quality style authority when it is mostly explanatory prose or sample instructions. If role text rules are explicit but the matched paragraph is a format hint, a label plus writing instructions, or has default/placeholder paragraph XML such as `w:spacing w:line="0"`, treat its paragraph properties as missing and complete them from granular fallback. Do not use this as permission to overwrite a clean native DOCX style that has trustworthy paragraph XML.

For paired abstract/keyword rules, allow font and字号 to propagate between the pair when one side gives the explicit format and the other side is only a keyword-count/example sentence. For example, `摘要：楷体小5号` plus `关键词：3-8个关键词...` means both abstract and keywords use 楷体小五 unless a stronger rule says otherwise; paragraph spacing/indent still comes from explicit evidence or fallback at property level.

Low-confidence visual evidence is column-count only. For PDF, converted DOC/DOT preview, OCR/image visual hints, screenshots, and blank carriers, do not emit or trust visual role, alignment, `size`, `bold`, `indent`, `spacing`, tabs, colors, underlines, or run-level properties. For website links, do not infer column count from visual hints, publisher brands, production article pages, or common journal practice; use explicit website/user text or default to single-column. Explicit prose/user text rules still win; everything else must come from fallback.

If visual/geometry screening can reliably determine single-column or double-column layout, write only `_meta.fallback_columns`/`source_column_detection`. Long front-matter lines are often misread as justified, so non-DOCX visual-only alignment must be dropped rather than normalized into `center`.

For weak-source fallback, abstract and keyword content should default to five-point size (`w:sz=21`). The labels `摘要`, `关键词`, `Abstract`, and `Key words`/`Keywords` are run-level bold markers only; the following abstract/keyword content must remain non-bold. Recognize label variants including `[Abstract]`, `【Abstract】`, `ABSTRACT`, `[摘要]`, `[Keywords]`, and `KEY WORDS` with or without a colon. Do not encode whole-style bold on `abstract`, `keywords`, `english_abstract`, or `english_keywords` just to bold the label.

Apply this same restriction to all non-DOCX visual routes, not only PDF. If image/OCR/website/rendered-preview rules JSON contains role alignment, `size`, `fonts`, `bold`, `italic`, `color`, `underline`, `indent`, `spacing`, `tabs`, or similar visual-format fields, sanitize them before merging with template text rules. Only explicit user/prose rules may keep style fields.

For clean publisher templates with explicit Word styles, canonical `styleId` mapping is mandatory and overrides heuristic paragraph guessing:

| Role | Preferred template style IDs |
|---|---|
| `title` | `IOPTitle`, `Titledocument`, `TitleDocument`, `Title` |
| `author` | `Authors`, `Author` |
| `affiliation` | `Affiliation`, `AdressLines`, `AddressLines`, `Affiliations` |
| `abstract` | `Abstract` |
| `keywords` | `KeyWords`, `Keywords`, `Keyword`, `KeyWord` |
| `heading1` | `IOPH1`, then `Head1`, then `Heading1` |
| `heading2` | `IOPH2`, then `Head2`, then `Heading2` |
| `heading3` | `IOPH3`, then `Head3`, then `Heading3` |
| `body` | `Para`, then `BodyText` variants, then `Normal` |
| `figure_caption` | `FigureCaption`, `CaptionFigure`, then `Caption` |
| `table_caption` | `TableCaption`, `CaptionTable`, `TableTitle`, then `Caption` |
| `references_heading` | `ReferenceHead`, `ACMRefHead`, then `Heading1` |
| `reference_item` | `IOPRefs`, `Bibentry`, `BibEntry`, `References`, `Bibliography` |
| `equation` | `DisplayFormula`, `Equation`, `Formula` |
| `english_title` | `EnglishTitle`, `TitleEnglish` |
| `english_author` | `EnglishAuthors`, `AuthorsEnglish` |
| `english_affiliation` | `EnglishAffiliation`, `AffiliationEnglish` |
| `english_abstract` | `EnglishAbstract`, `AbstractEnglish` |
| `english_keywords` | `EnglishKeywords`, `KeywordsEnglish` |
| `metadata` | `Metadata` |
| `citation_format` | `CitationFormat` |

Heuristics may fill missing roles only after this canonical pass, but canonical styles must be usage-validated. A style that merely exists in `styles.xml` is only a candidate; it is authoritative only when real template paragraphs for that role actually use that `pStyle`, or when the role is a publisher-defined non-body role with no better paragraph evidence. ACM, IOP, and other publisher templates often keep visible body/head/reference formatting in custom style IDs such as `Para`, `Head1`, `IOPH1`, `FigureCaption`, `ReferenceHead`, `IOPRefs`, and `Bibentry`; these must beat generic Word defaults such as `Normal`, `Heading1`, and `Heading2`. If a normal body paragraph has no explicit `pStyle`, build the role from `docDefaults + Normal` plus that paragraph's direct `pPr/rPr`; never emit an empty body fallback.

For unknown journal templates, do not rely only on the fixed canonical table. Also inspect every template style's `styleId`, visible `w:name`, real paragraph usage, and expanded `basedOn` chain. Generic semantic style names such as `ArticleTitle`, `PaperTitle`, `ManuscriptTitle`, `HeadingLevel1`, `SectionHead2`, `FigCaption`, `TableCaption`, `BibliographyEntry`, `ReferenceItem`, or `Refs` may define the role even when the style ID is not in the known-publisher list. This semantic fallback must run before content-only paragraph guessing, but it must avoid collisions: `TableTitle/FigureTitle` are captions, `ReferenceHead` is the references heading, and `Subtitle/RunningTitle/ShortTitle` are not the main title.

Each role entry must include:

- role id and generated `style_id`, such as `title -> 1title`, `body -> 9body`;
- display name and style type;
- structured font summary: CJK/Latin/complex fonts, size, bold/italic, color, underline, emphasis mark, strike, superscript/subscript, hidden text, character spacing, position, scaling, kerning, shading, border, language;
- structured paragraph summary: alignment, outline level, text direction, indentation, first-line/hanging indent, spacing before/after, line spacing, grid flags, keep/page-break controls, widow control, tabs, numbering, borders, shading, frame, text alignment;
- locked text rule that overrode template XML, if any;
- source sample and source style id for audit;
- raw `pPr_xml`, `rPr_xml`, and full `style_xml`.

When a canonical `styleId` is selected, the audit sample/signature must come from a real template paragraph using that same `pStyle` whenever possible. Do not borrow samples from another detected paragraph of the same role, and do not use table style-inventory rows as role samples. Publisher-specific canonical IDs such as IOP `IOPTitle`, `IOPH1`, `IOPH2`, `IOPH3`, and `IOPRefs` must be treated as explicit role evidence before generic Word styles; record the selected `source_style_id` and its `basedOn` chain in `style_spec.json`.

Run-level direct formatting must be promoted to role styles only through representative coverage, never by the first formatted run:

- Paragraph-level `pPr/rPr` is authoritative for paragraph mark character style. If it exists, use it before inspecting child runs.
- If paragraph-level `pPr/rPr` is absent, infer representative run formatting by text-length coverage across all meaningful text runs. Font, size, language, and character spacing may be promoted only when the same property covers a strong majority of the paragraph text.
- Local emphasis properties such as italic, bold, underline, color, highlight, shading, superscript/subscript, strike, emphasis marks, hidden text, caps, and character position need an even stronger near-whole-paragraph majority before promotion.
- A single formatted run, or the first formatted run, is not representative when surrounding text has no matching direct formatting. This prevents reference examples, captions, metadata, and body paragraphs from turning entirely italic/bold/colored because one journal name, volume number, marker, or hint phrase is formatted locally.
- Run-level superscript markers remain a separate marker pass. They must not become whole-paragraph `style/rPr` or nested `style/pPr/rPr`.

Few-shot:

| Template evidence | Expected behavior |
|---|---|
| Reference item text has normal authors/year, italic journal name, bold volume, then normal pages | `reference_item` keeps the paragraph/font/size evidence but does not write whole-style italic or bold. |
| Figure caption has only `Fig. 1` bold and the caption text normal | `figure_caption` does not become entirely bold. |
| A full title paragraph is entirely bold/italic in nearly every run | The emphasis may be promoted because it is representative whole-role formatting. |
| Author line has superscript affiliation numbers after names | Do not promote `vertAlign=superscript` to `author`; apply superscript only to detected marker runs later. |

Role-source content consistency is mandatory and must be generic, not a publisher-specific blacklist:

- A paragraph can define a core role style only when its text, position, and surrounding context are compatible with that role. Being early in the template, short, large, bold, or assigned a custom Word style is insufficient.
- Publisher metadata, date/DOI/copyright/received/revised/accepted notes, footnotes, correspondence notes, UI/operation instructions, and placeholder/rule prose must not become the source sample for `title`, `author`, `affiliation`, `abstract`, `keywords`, `body`, headings, captions, or references.
- Such paragraphs may map to `metadata` only when they are real front-matter metadata; footnotes and operation/help text should usually be skipped as style sources unless the target has an explicit matching role.
- If a style's first used paragraph is metadata/instruction text, do not infer the style's semantic role from position alone. Continue scanning for a content-consistent paragraph using the same role, or fall back through the source-aware priority chain.
- Do not fix this with hardcoded style-name blacklists. Use content features such as date/DOI/copyright/received/revised/accepted markers, footnote/correspondence language, UI operation words, formatting-rule wording, and role-zone context.

Few-shot:

| Template evidence | Expected behavior |
|---|---|
| Early paragraph says `Date of publication...` and uses a custom style | Treat as metadata/source-noise, not title/body, even if it is the first visible paragraph. |
| Early paragraph says `Digital Object Identifier...` or contains `doi:10...` | Do not use it as author/body/title style evidence; at most map as metadata. |
| A footnote/copyright/correspondence note appears before the real paper title | Skip it as a core role source; keep scanning for the real title/author/body samples. |
| A custom style's first used paragraph is a Word operation instruction such as Alt Text guidance | Do not use that paragraph's `pPr/rPr` as the body or caption style. |
| Real paper title appears after several publisher metadata rows | The real title paragraph, not the first visible short paragraph, supplies `title` evidence. |

Body source selection has an extra guardrail:

- Do not select `BodyText`, `BodyTextIndent`, `Para`, or any body canonical style just because it exists in `styles.xml`.
- First verify that actual body-like template paragraphs use that `pStyle`.
- If the template has many real body paragraphs with `pStyle=None`, use their `Normal/docDefaults + direct paragraph/run formatting` as the body style source even when an unused `BodyText` style exists.
- Record this as `source_route=detected_paragraph`, not `used_canonical_style_id`.
- This avoids Springer-style templates where headings/captions use named custom styles but real body text remains Normal, while an unused `BodyText` style in `styles.xml` has different font/size/spacing.
- When a real body paragraph has no explicit `pStyle`, materialize the template default paragraph style, usually `Normal`, together with `docDefaults` before applying the paragraph's direct formatting. Do not treat `pStyle=None` as `docDefaults` only; otherwise properties stored on `Normal`, such as `w:jc w:val="both"`, disappear.
- Do not use a hard minimum text length such as 80 characters to decide whether a body source is trustworthy. Short placeholder body samples such as `Enter text here.`, `Sample body text.`, or a short real paragraph may still carry the correct `Normal`/`BodyText` formatting.
- Keep the false-positive guard: short formatting hints and operation instructions are not body formatting samples. Text such as `正文宋体五号`, `文章正文是5号宋体`, `right-click ... Edit Alt Text`, `Use single tab stops...`, or other Word operation/help text must not contribute paragraph `jc`, `spacing`, `ind`, or tab settings to the body style.
- Before inheriting body paragraph spacing from a detected source paragraph, decide whether the source paragraph is a real body sample or only a format hint. A paragraph like `文章正文是5号宋体` can provide font/size text rules, but its paragraph spacing is not trustworthy.
- If a real body sample has explicit spacing such as `line="300" lineRule="auto"` or exact fixed spacing, preserve it. If the source has `line="0"` or no spacing, treat line spacing as unspecified and use the granular fallback.

Generated style IDs must use this readable sequence:

| Role | Generated style ID |
|---|---|
| `title` | `1title` |
| `author` | `2author` |
| `affiliation` | `3affiliation` |
| `abstract` | `4abstract` |
| `keywords` | `5keywords` |
| `heading1` | `6heading1` |
| `heading2` | `7heading2` |
| `heading3` | `8heading3` |
| `body` | `9body` |
| `figure_caption` | `10figurecaption` |
| `table_caption` | `11tablecaption` |
| `references_heading` | `12referencesheading` |
| `reference_item` | `13referenceitem` |
| `equation` | `14equation` |
| `english_title` | `15englishtitle` |
| `english_author` | `16englishauthor` |
| `english_affiliation` | `17englishaffiliation` |
| `english_abstract` | `18englishabstract` |
| `english_keywords` | `19englishkeywords` |
| `metadata` | `20metadata` |
| `citation_format` | `21citationformat` |

The raw XML fields are authoritative. The structured fields are for audit, model routing, and sanity checks. If the structured parser misses a Word feature, the full `style_xml` must still carry it forward.

The target stage should:

1. Load the style spec.
2. Identify target paragraphs as title, abstract, keywords, body, heading levels, figure captions, table captions, references, display equations, etc.
3. Write `role_map.json` when requested.
4. Audit role-map warnings before style application. If a paragraph such as classification number, English title, affiliation, figure/table prose, or references is ambiguous, fix the role mapping rather than changing the style spec.
5. Audit style-spec warnings before installing styles. If body uses an unverified canonical route such as unused `BodyText`, regenerate or edit `style_spec.json`.
6. Re-run with `--role-map-in role_map.json` to lock the reviewed target role mapping.
7. Create/replace target role styles from `style_xml`.
8. Set each target paragraph `w:pStyle` to the role style. If the exact role style is unavailable, first use the cross-language equivalent role (`english_title -> title`, `english_author -> author`, `english_affiliation -> affiliation`, `english_abstract -> abstract`, `english_keywords -> keywords`, and the reverse pairs). Fall back to `body` only after exact and cross-language role styles are both unavailable, and report that as a visual-risk item.
9. Clean target direct formatting so it cannot override the spec.

`style_spec.json` and `role_map.json` are both reusable bridge files. `style_spec.json` answers "what should each role look like"; `role_map.json` answers "which target paragraph is which role." They may be emitted for audit, edited, and then supplied back with `--style-spec-in` and `--role-map-in` for deterministic reruns.

Locked bridge formatting means both inputs are supplied:

```bash
python3 scripts/format_docx.py \
  -t template.docx -i target.docx -o output.docx \
  --style-spec-in style_spec.json \
  --role-map-in role_map.json
```

In this mode, the script must not auto-classify missing paragraphs. Every non-empty target paragraph must appear in `role_map.json`, every role in `role_map.json` must exist in `style_spec.json`, and the corresponding `style_xml` from `style_spec.json` must be installed before paragraph binding. Missing indexes or unknown roles are fatal errors.

Even in locked bridge mode, run the style-spec preflight before installation. A reviewed `style_spec.json` is allowed to override heuristics, but it must not silently carry known-invalid body routes such as `source_route=unused_canonical_style_id` for `BodyText` when real body paragraphs use `pStyle=None`.

## Style Routing

Default route is spec-backed role binding:

1. The template is scanned for representative paragraphs: title, author, affiliation, abstract, keywords, headings, body, figure captions, table captions, references heading, and reference items.
2. The matching template style/signature is normalized into `style_spec.json` with stable generated style IDs such as `1title`, `6heading1`, and `9body`.
3. Target paragraphs are classified by content, then their `w:pStyle` is set to the generated role style.
4. The target's original `w:name` values are not trusted as the bridge.

When building role styles, first expand the template `basedOn` chain from base to leaf and materialize the effective `pPr/rPr`. Do not simply remove `basedOn` and keep only the leaf style, or the visible font/size/spacing may become much worse. Template paragraph direct formatting may be merged as a patch, but it must not replace the whole effective `pPr/rPr`.

After expanding inheritance, scrub role-incompatible inherited properties:

- Author and affiliation roles must not carry `vertAlign=superscript` at `style/rPr` or `style/pPr/rPr`; superscript belongs to marker runs only.
- Body, author, affiliation, abstract, keywords, metadata, citation, caption, and reference-item roles must not inherit title-only `outlineLvl`, `keepNext`, `keepLines`, or `pageBreakBefore`.
- `w:b w:val="0"` inherited into author/affiliation/body should be removed instead of allowed to mask real bold inherited from the intended source.
- Audit raw `style_xml`, not only structured summaries, because inherited pollution may be invisible in summarized fields.

Respect theme fonts. If a template style uses `asciiTheme`, `hAnsiTheme`, `eastAsiaTheme`, or `cstheme`, do not add the corresponding concrete `ascii`, `hAnsi`, `eastAsia`, or `cs` fallback font unless a higher-priority user/prose rule explicitly requires it. Concrete font attributes can override Calibri/Cambria theme schemes in Word.

For instruction-heavy templates, filter front-matter and rule text before choosing style sources. Do not use paragraphs like `WORD模板`, `文章编号`, `引用格式`, `中图分类号`, format explanation text, table cells, or figure/table instruction text as body/title/author style sources. Body source should come from real body-like paragraphs after the body rule is encountered; otherwise let the text rule/fallback define the body style.

For English publisher templates, do not map `Heading1` titled `Abstract` to the abstract body style. Abstract body should use a body/normal style unless the template provides a dedicated abstract-body style.

Chinese bilingual instruction templates need expanded front-matter roles:

- Use separate roles for Chinese and English front matter: `title`, `author`, `affiliation`, `abstract`, `keywords`, plus `english_title`, `english_author`, `english_affiliation`, `english_abstract`, and `english_keywords`.
- Treat `文章编号`, `中图分类号`, and `文献标志码` as `metadata`, even when they visually use the same font/size as body.
- Treat `引用格式` and its immediate English continuation line as `citation_format`.
- Explicit labels must outrank broad author/title/affiliation heuristics. Paragraphs beginning with `摘要`, `摘  要`, or `Abstract` must map to abstract roles before author/heading/title checks. Paragraphs beginning with `关键词`, `关键字`, `Key words`, or `Keywords` must map to keyword roles before author/heading/title checks.
- Detect the marker `英文题名、作者、单位、摘要、关键词参考下面模式` as a state transition, not as a role source. The following paragraphs should be classified in order as English title, English author, English affiliation, English abstract, and English keywords.
- Treat `WORD模板`, `姓全部大写，名首字母大写`, and similar explanation-only markers as non-role text; they should not be mapped to title/body or used as style sources.
- Do not collapse these roles into body just because they use body-like direct formatting. A role can use body-like formatting while still needing separate role identity for target mapping.

Single-language templates need cross-language role equivalents:

- If a pure English target maps its title to `english_title` but the template only defines `title` through `Titledocument`, use the `title` style as the equivalent source. Do not fall back to `body` or `Para`.
- If a pure Chinese target maps front matter to `title`, `author`, or `abstract` but the template only defines English-prefixed roles, use the corresponding English-prefixed style before body fallback.
- The equivalent pairs are `title <-> english_title`, `author <-> english_author`, `affiliation <-> english_affiliation`, `abstract <-> english_abstract`, and `keywords <-> english_keywords`.
- Treat an exact front-matter role source that uses body-like styles such as `Para`, `BodyText`, `BodyTextIndent`, or `Normal` as weak evidence. If the cross-language equivalent role has a stronger non-body style such as `Titledocument`, `Authors`, `Affiliation`, `Abstract`, or `KeyWords`, use the stronger equivalent role instead of the weak exact source.
- Record cross-language role usage in the internal format report. It is acceptable and safer than body fallback, but the final note should mention it when relevant.
- Treat direct body fallback for any title/author/affiliation/abstract/keywords role as a warning-level risk that needs visual confirmation.

Reference routing is stateful:

- `参考文献：`, `参考文献`, `References`, `REFERENCE`, and `REFERENCES` start the reference zone.
- Inside the reference zone, reference-item detection must run before title/heading detection. A paragraph such as `[1] 作者1．文章题名[J]...` is a reference item even though it contains `文章题名`.
- In Chinese instruction templates, skip reference-format explanation rows such as `期刊与书(论文集)著录格式为:`, `作者1`, `著者1`, `起始页-终止页`, and `不要缺少...` when selecting the `reference_item` style source. Prefer real examples after `例：`.
- Numberless continuation lines inside the reference zone, especially English continuation lines containing journal names, years, `[J]`, `[C]`, `[EB/OL]`, etc., should still map to `reference_item`.

Figure/table caption routing must be anchored:

- Match `图1 ...`, `Fig.1 ...`, `Figure 1 ...`, `表1 ...`, `Tab.1 ...`, and `Table 1 ...` as captions.
- Do not map prose such as `图7的混淆矩阵...`, `图2(b)所示...`, or `表1可以看出...` as captions.

Front-matter routing must not turn metadata into affiliation:

- `文章编号`, `中图分类号`, and `文献标志码` must map to `metadata`; `引用格式` must map to `citation_format`. They should never map to author/affiliation or generic body merely because their visual formatting resembles body text.
- `摘要` and `关键词` paragraphs must not map to author/affiliation/title merely because they are short, bold, centered, or contain punctuation/markers. If the preflight sees an explicit abstract/keyword/metadata label mapped to another role, warn before style injection.
- Email/contact-only lines in the front matter must map to affiliation/contact metadata, not title, author, or heading. A line such as `jizhang@tongji.edu.cn` is never an English title or author just because it is short and appears before the abstract.
- A short English paper title before `Abstract` should map to `title`, not affiliation, unless it contains organization words such as `University`, `Institute`, `College`, `School`, `Laboratory`, or `Department`.
- Author-line detection must run before plain English heading detection in the early front matter. A comma-separated English or pinyin name list such as `Zhang Ji, Bai Yakun, Liu Jiadong` maps to `author`, not `heading1`.
- After the initial role map is built, run a front-matter positional refinement pass before style application. In the short window after a title and before abstract/keywords/body, reclassify likely author lines and affiliation lines using both content and position.
- The refinement pass must treat comma-separated or Chinese-comma/顿号-separated names such as `Zhang Ji，Bai Yakun`, `Zhang Ji, Bai Yakun`, or `张三、李四` as `author` when they appear between title and affiliation/abstract, even when there are no superscript markers.
- If a line after the author line contains institution words such as `University`, `Institute`, `大学`, `学院`, `研究院`, `实验室`, or is immediately before an abstract marker, prefer `affiliation`.
- Do not classify numbered headings as authors. Strings such as `1 2D Human Pose Estimation` and `2 Methodology` remain `heading1` when they occur after front matter.

Heading routing must run before English title fallback after the first visible paragraph:

- `Introduction`, `Conclusion`, `Related Work`, `1 Introduction`, `1    Introduction`, and `1 2D Human Pose Estimation` are `heading1` when they occur after front matter.
- Numbered heading matching must tolerate multiple spaces between number and title.
- When a template heading role style such as ACM `Head1` has Word automatic numbering but a target heading already starts with a manual number, bind that paragraph to a no-number mirror of the same generated heading style. Keep automatic numbering for plain target headings without a manual prefix. This heading-specific conflict handling is separate from reference-list numbering repair.
- Plain English headings must be short and heading-like; long sentence text with verbs such as `allows`, `shows`, `uses`, `is`, or `which` must remain `body`.
- Do not let the broad early author/affiliation fallback classify ordinary body sentences. Author fallback needs name/marker features; affiliation fallback needs institution words.
- Do not let plain-heading title case logic capture comma-separated author lists. If a short line has multiple capitalized names separated by commas or Chinese commas and no institution words, prefer `author` in the front-matter zone.

Legacy `--style-mode name` may still be used for very clean documents, but it is a known risk when the source document was written with arbitrary or localized style names.

## Text Rule Priority

Before any style is injected, scan template body text for visible formatting rules such as:

- `正文五号宋体`
- `摘要小五号宋体`
- `一级标题四号黑体居中`
- `英文 Times New Roman`

Priority is locked:

1. `user_rules`: explicit JSON passed with `--rules-json`.
2. `template_text_rules`: prose rules extracted from the template body.
3. `template_style_xml`: actual style XML copied from the template.
4. `bundled_OOXML_fallback`: fill missing or implicit-default properties from `assets/fallback_ooxml_spec.json`, selected by language and column count.
5. `legacy_dictionary_fallback`: emergency backup only for fields still absent after the OOXML fragment merge.

If prose rules conflict with `styles.xml`, prose rules win. If user JSON conflicts with both, user JSON wins.

The bundled fallback is not prose. It is a role-level OpenXML fragment library generated from four fallback sample DOCX files: Chinese single-column, Chinese double-column, English single-column, and English double-column. Every weak source, blank carrier, converted legacy source, PDF/text/OCR route, and missing-property fallback must use those `pPr_xml/rPr_xml` fragments first. Do not reconstruct fallback styles from narrative text when the JSON fragment exists. Native `.docx` templates are the exception: do not use bundled fallback to fill role-style font/size/spacing/alignment gaps in native template styles.

When a prose/user text rule explicitly sets a property, it must overwrite the same property group from template styles, representative direct formatting, and fallback. Do not merely append the new value while leaving stale same-channel attributes in place:

- If the rule sets `eastAsia`, remove `eastAsiaTheme` before writing `eastAsia`.
- If the rule sets `ascii`, remove `asciiTheme`; if it sets `hAnsi`, remove `hAnsiTheme`; if it sets `cs`, remove `cstheme`.
- If the rule sets size, remove existing `sz/szCs` and rewrite them.
- If the rule sets bold or color, remove existing same-group children before rewriting.
- This rule is property-channel specific. For weak sources such as PDF/text/OCR/blank carrier, `正文5号宋体` locks `eastAsia=宋体` and size, but may leave Latin/theme fonts, indentation, paragraph spacing, and line spacing to the selected bundled OOXML fallback unless the prose also specifies those properties. For native `.docx` templates, missing properties remain template inheritance rather than bundled fallback.
- Do not skip an entire XML child just because a text rule locks one attribute. If a rule locks `rFonts/@eastAsia`, the fallback may still fill `rFonts/@ascii` and `rFonts/@hAnsi`. If a rule locks `spacing/@line`, the fallback may still fill `spacing/@before` and `spacing/@after`, and vice versa.

Because `template_text_rules` outrank template XML, false positives are dangerous. Extract prose rules only from explicit formatting instructions, not from ordinary document instructions:

- Skip UI/help/instruction paragraphs such as image Alt Text instructions, `right-click`, `left-click`, `double-click`, `click on`, `Edit Alt Text`, `Title text box`, `Description text box`, and similar Word operation text.
- Do not classify a paragraph as the `title` role merely because it contains the English word `Title`; require a format-rule context such as font, size, style, alignment, or journal role wording.
- Do not infer alignment from bare direction words in English. `right` inside `right-click` is not right alignment, and `left` inside `left-click` is not left alignment.
- Accept English alignment only when it is explicit, such as `align right`, `right aligned`, `right alignment`, `right-align`, `align center`, `centered`, `justify`, or `left aligned`.
- If a suspected text rule contains no actual formatting property after parsing font/size/bold/alignment/spacing/indent, drop it rather than recording an empty or partial override.

Fallback must be granular, bilingual, and property-level:

- Detect template language as `zh` or `en`.
- Use the Chinese fallback for Chinese templates and the English fallback for English templates.
- Fill only missing properties. Never replace a whole role style with a fallback role style.
- Do not fill missing paragraph alignment (`w:jc`) through fallback. A missing `w:jc` has standard Word semantics: default left alignment. Preserve that implicit default unless a higher-priority user rule, template prose rule, template style, or real template paragraph explicitly sets alignment.
- Treat most explicit OOXML values as present even when they look falsy. Exception: `w:spacing w:line="0"` means no explicit line spacing was set, so treat the line-spacing semantic group as missing and fill both `line` and `lineRule` from fallback.
- If template prose says "正文宋体五号" but says nothing about line spacing, write body font/size from the prose rule, then inspect the actual body sample. Use the sample's line spacing only if it is trustworthy and explicit; otherwise fill missing body line spacing from the Chinese fallback.
- Chinese body fallback line spacing is 1.5 line spacing: `w:line="360" w:lineRule="auto"`.
- If template prose says "固定值 20 磅", write `w:spacing w:line="400" w:lineRule="exact"`.
- If template prose says "1.5 倍行距", write `w:spacing w:line="360" w:lineRule="auto"`.
- If template XML has `w:spacing w:line="0"` and no higher-priority text/user rule explicitly sets line spacing, replace that implicit default with the language fallback line-spacing pair, such as `w:line="240" w:lineRule="auto"` for explicit single line. Do not preserve stale `lineRule="atLeast"` or `lineRule="exact"` when `line="0"` triggered fallback; otherwise Word displays "at least 12 pt" instead of single spacing. Keep other zero values like `before="0"` and `after="0"` as real values.

Few-shot:

| Template evidence | Expected `style_spec.json` behavior |
|---|---|
| Text says `正文宋体五号`; style XML has `w:spacing w:line="0" w:lineRule="atLeast"` | Body keeps 宋体/五号 from text rule, treats the line-spacing group as missing, and writes zh body fallback `line="360" lineRule="auto"`. |
| Text says `文章正文是5号宋体`; source paragraph is only that hint and has single spacing | Body keeps 宋体/五号 from text rule, ignores the hint paragraph's spacing, and writes zh body fallback `line="360" lineRule="auto"`. |
| Real body sample has explicit `w:spacing w:line="300" w:lineRule="auto"` | Body preserves `line="300" lineRule="auto"` and does not overwrite it with fallback. |
| Springer-style `Normal` has `w:jc w:val="both"` and body sample text is short or `pStyle=None` | Body materializes `Normal + docDefaults + paragraph direct pPr`, preserving `jc="both"` instead of falling back to default left alignment. |
| Placeholder body text says `Enter text here.` in a body-like paragraph | Treat it as a valid body formatting sample if it has no explicit format-rule/operation-instruction wording. |
| Text says `正文宋体五号`; style XML has no `spacing` | Body keeps 宋体/五号, then fills only missing spacing from zh fallback. |
| Text says `文章正文是5号宋体`; demo body paragraph uses a different font/theme | Body writes `eastAsia=宋体`, removes `eastAsiaTheme`, writes `sz/szCs=21`, and does not let the demo paragraph's same-channel font/size override it. |
| Text says `body Times New Roman 12 pt`; style XML has no alignment | Body keeps Times New Roman/12 pt and preserves missing `w:jc` as Word default left alignment; fallback must not add alignment. |
| ACM `Titledocument`, `Authors`, or `Affiliation` style has no `w:jc` | Preserve missing `w:jc`; do not add `center` just because those roles often look centered in other templates. |
| Text says `正文固定值 20 磅` | Body writes fixed 20 pt line spacing regardless of fallback. |
| Text says `参考文献悬挂缩进2字符` | `reference_item` writes `w:left="420" w:hanging="420"` from the text rule. |
| Blank carrier DOCX has `Normal` single spacing `line="240"` and external Chinese rules are otherwise incomplete | Route as `blank_carrier_template`; body writes Chinese fallback `line="360"`, title/heading styles write their fallback paragraph spacing, and target `Normal/docDefaults` are rewritten to the body fallback baseline. |

Apply locked text rules to both `style/rPr` and nested `style/pPr/rPr`. Word may consult either location, so leaving old sizes or fonts in `pPr/rPr` can make the displayed result look like the old template/style even when `style/rPr` is correct.

Template hint colors must be normalized at the raw XML level:

- Instruction templates often use red, orange, or blue text for hints such as `点击在线查询分类号`, `分号`, `突出体现文章的新意`, or parenthetical reference-format labels.
- These colors are not necessarily journal-required formatting. Do not let them silently become official role styles for `metadata`, `abstract`, `keywords`, `citation_format`, `reference_item`, or `body`.
- Cleaning only structured fields such as `font.color` is insufficient. The authoritative `style_xml`, `pPr_xml`, and `rPr_xml` must also remove or normalize `<w:color>` nodes, otherwise Word will still display the inherited hint color.
- Treat common hint colors such as `FF0000`, `FF6600`, `0000FF`, `0070C0`, and `00B0F0` as suspicious in instruction-heavy templates. Remove them from generated role styles unless an explicit user rule or clear prose rule says the final submission style requires that color.
- Record removed hint colors in the internal format report so the final user note can call out metadata/abstract/keywords as visual-confirmation areas.

Example `rules.json`:

```json
{
  "roles": {
    "body": {
      "size": "21",
      "fonts": {
        "eastAsia": "宋体",
        "ascii": "Times New Roman",
        "hAnsi": "Times New Roman"
      },
      "align": "both"
    },
    "title": {
      "size": "32",
      "fonts": {
        "eastAsia": "黑体"
      },
      "bold": true,
      "align": "center"
    }
  }
}
```

`size` uses Word half-points, so 10.5 pt is `21`, 12 pt is `24`, and 16 pt is `32`.

## Direct Formatting Cleanup

After role binding, clean direct formatting that can override the assigned style:

- paragraph-level overrides: alignment, spacing, indentation, tabs, paragraph `rPr`, keep settings, outline level;
- run-level overrides: `rFonts`, `sz`, `szCs`, bold, italic, color, underline, highlight, shading, spacing, position, language.

This is required because Word display priority often lets run/paragraph direct formatting beat `styles.xml`. If this cleanup is skipped, fonts and sizes may still look like the original document even after styles were changed.

After cleanup, run format-conformance QA before reference numbering, table formatting, equation tabs, or superscript passes. It must compare `role_map.json` paragraph bindings against the actual target `w:pStyle`, and compare installed generated role styles against authoritative `style_spec.json` raw `pPr_xml`/`rPr_xml`. Deterministic mismatches are repair work, not final-note material: rebind wrong paragraphs, remove remaining direct overrides, and clear stale generated-style font/size/color/bold/italic/spacing/indent/alignment properties that are absent from the spec but could still override display. Only unresolved style IDs, ambiguous role mapping, or evidence-uncertain formatting should reach the user as visual-confirmation notes.

The cleanup only removes formatting properties from paragraph/run containers. It must not delete text nodes, drawings, OMML math, OLE objects, embedded media, tables, or relationship parts.
