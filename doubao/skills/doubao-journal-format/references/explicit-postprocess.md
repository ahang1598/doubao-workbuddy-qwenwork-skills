# Explicit Postprocess

Read this only when the user or extracted source prose clearly asks for content or structure edits in addition to formatting, such as moving tables/figures after references, changing body citation markers, changing reference-list number style, or normalizing figure/table caption prefixes.

## Boundary

This module is an explicit-rule post-format layer. Do not enable it from template style evidence alone. Run it only when one of these is true:

- The user explicitly asks for a content/structure operation.
- The source formatting instructions explicitly require the operation as a manuscript rule, not merely as a visual style.
- The user provides a reviewed `postprocess_ops.json`.

If the instruction is ambiguous, ask before enabling. The default remains style formatting only.

When the operation comes from extracted PDF/website/DOC/OCR text rules, do not require the user to hand-author a second JSON. Write `postprocess_operations` or `_meta.postprocess_operations` into the same `rules.json`; `format_docx.py` will generate the temporary enabled ops JSON and run `scripts/explicit_postprocess.py` after the first valid repack. Manual `--explicit-postprocess-json` remains the reviewed override.

Do not use this layer to rewrite scientific content, reorder paragraphs broadly, edit formulas, edit image payloads, change table data, delete objects, or infer missing author/reference/caption text. Preserve relationships, media, fields, OMML, OLE, drawings, and section properties.

## Supported Operations

Use `scripts/explicit_postprocess.py` through `format_docx.py --explicit-postprocess-json postprocess_ops.json`. The JSON must include `enabled: true`.

Supported operation types:

- `move_tables_after_references`: move table blocks that occur before the reference heading to the end of the document after references. Include the nearby table caption only when it is clearly attached. Skip blocks that would move section properties.
- `move_figures_after_references`: move only standalone figure/image blocks that occur before the reference heading and have a clearly adjacent figure caption. Include the nearby figure caption only when it is clearly attached. Skip uncaptioned drawing/pict paragraphs, paragraphs containing OLE/MathType/OMML/formula objects, paragraphs mixed with normal body prose, and blocks that would move section properties. Never treat a MathType/OLE equation preview image as a figure.
- `normalize_body_citations`: change body citation markers such as `[1]` to `(1)`, apply italic/bold/superscript when explicitly requested, and skip the reference zone, captions, complex field paragraphs, drawings, formulas, and OLE.
- `normalize_reference_prefixes`: change reference-list item prefixes, such as `[1]` to `(1)`, `[1]` to `1`, or `[1]` to `1.`. This applies only inside the reference zone after `参考文献`/`References`. Use `renumber: true` only when the user explicitly asks for sequential renumbering. Use `add_missing: true` only when the user explicitly asks to add missing reference numbers.
- `normalize_figure_captions`: convert figure-caption prefixes such as `Figure 1`/`图1` to a requested prefix such as `Fig. 1:` and optionally bold the first sentence.
- `normalize_table_captions`: convert table-caption prefixes such as `Table 1`/`表1` to a requested prefix and optionally bold the first sentence.

## JSON Examples

```json
{
  "enabled": true,
  "operations": [
    {
      "type": "normalize_body_citations",
      "to": "parentheses",
      "italic": true
    },
    {
      "type": "normalize_reference_prefixes",
      "style": "round",
      "renumber": false,
      "add_missing": false
    },
    {
      "type": "normalize_figure_captions",
      "prefix": "Fig.",
      "separator": ":",
      "first_sentence_bold": true
    }
  ]
}
```

The same operations may be embedded in `rules.json`:

```json
{
  "_meta": {
    "source_type": "text_rules",
    "postprocess_operations": [
      {
        "type": "move_tables_after_references",
        "include_caption": true
      },
      {
        "type": "normalize_body_citations",
        "to": "parentheses",
        "italic": true
      }
    ]
  },
  "roles": {
    "body": {
      "fonts": {"ascii": "Times New Roman", "hAnsi": "Times New Roman"},
      "size": "24"
    }
  }
}
```

`postprocess_operations` should normally be an array of operation objects. A single operation object or a legacy shorthand object may be accepted for compatibility, but the formatter must emit a warning and normalize it internally:

```json
{
  "postprocess_operations": [
    {
      "type": "normalize_body_citations",
      "to": "parentheses",
      "italic": true
    },
    {
      "type": "normalize_reference_prefixes",
      "style": "plain_dot",
      "renumber": true
    }
  ]
}
```

Do not write ambiguous boolean keys such as `citation_markers_italic_parentheses` unless no better parser exists; if encountered, they must be translated to the explicit operation and reported as a normalized shorthand warning.

Few-shot text routing:

| Source prose | Expected route |
|---|---|
| `Tables and figures should be placed after the references.` | Emit `move_tables_after_references` and `move_figures_after_references`. |
| `Citation numbers should be placed within parentheses and italicized.` | Emit `normalize_body_citations` with `to=parentheses`, `italic=true`. |
| `References numbered sequentially.` | Emit `normalize_reference_prefixes` only for the reference list, with `renumber=true`; do not touch body citation markers. |
| `Figure legends begin with Fig. 1:` | Emit `normalize_figure_captions` with `prefix=Fig.`, `separator=:`. |
| `Figure legends: first sentence bold.` | Emit `normalize_figure_captions` with `first_sentence_bold=true`. |
| A PDF visually shows all tables at the end, but no text says this is required | Do not emit postprocess operations. |

Reference prefix styles:

| style | Output |
|---|---|
| `round` / `parentheses` | `(1)` |
| `square` / `brackets` | `[1]` |
| `plain` / `bare` | `1` |
| `plain_dot` / `dot` | `1.` |
| `plain_chinese_dot` | `1．` |
| `plain_parenthesis` | `1)` |

## Route

1. Complete the normal style/page/table/equation/reference formatting route first.
2. Repack a valid DOCX.
3. Run explicit postprocess only when manually supplied or auto-generated from explicit text-derived `postprocess_operations`.
4. During postprocess, run before/after preservation checks for paragraph count, table count, drawing/pict count, OLE/MathType/OMML count, and paragraph-text multiset for move-only operations. Any drop or text multiset change must be reported as a preservation issue and treated as a delivery risk.
5. Run structural QA, LibreOffice compatibility QA, and render QA after postprocess, not before.
6. Record the postprocess report in `qa_report.explicit_postprocess` and `format_report.risk_items`. The main formatter must print a concise `Postprocess results` summary with each operation's changed/moved/added/skipped counts and warnings.
7. In the final answer, mention only that content/structure postprocess was enabled and ask the user to confirm the affected items visually.

## Guardrails

- Never run postprocess based only on a template example looking a certain way.
- Never convert body citations when the template/user instruction only discusses reference-list prefixes.
- Never convert reference-list prefixes when the user only asks for body citation format.
- Never apply body citation conversion inside `参考文献`/`References`.
- Never add missing reference-list numbers unless explicitly requested.
- Never renumber existing reference-list entries unless explicitly requested.
- Never move figures/tables by guessing from captions alone when the object relationship is unclear.
- Never move a paragraph with OLE/MathType/OMML/object content as a figure, even if it contains `pict`/`shape` preview XML.
- Never move a paragraph that contains normal body prose plus a drawing/pict anchor as a figure block.
- Never move uncaptioned figure-like drawings unless a reviewed manual override explicitly disables the caption requirement.
- Never move paragraphs containing `sectPr`, fields, comments, footnotes, endnotes, bookmarks, OMML, OLE, MathType, or other formula/object payloads.
- Treat skipped complex paragraphs as warnings, not silent success.
