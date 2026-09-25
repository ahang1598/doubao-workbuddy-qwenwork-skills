# Existing-PDF Editing Tool List

Read this file when the user wants to change content in an existing PDF while
preserving its pages and layout. This is a menu of editing tools, not one
mandatory workflow. Select only the operations needed for the request.

Use PyMuPDF by default, keep the source file unchanged, save to a separate
output path, and render every changed page for visual verification.

## Text Editing

| Task | PyMuPDF Tool | Notes |
|------|----------------|-------|
| Add short text at a point | `page.insert_text()` | Suitable for simple one-line additions |
| Add text inside a rectangle | `page.insert_textbox()` | Check its return value; a negative value means the text did not fit |
| Add styled or multilingual text | `page.insert_htmlbox()` | Supports HTML/CSS, complex scripts, custom fonts, and bounded downscaling |
| Replace existing searchable text | `page.add_redact_annot()` + `page.apply_redactions()` followed by an insertion method | Use only for the target regions; preserve unrelated graphics and images |
| Remove text without replacement | `page.add_redact_annot()` + `page.apply_redactions()` | Confirm whether the redaction fill should be transparent or match the background |
| Locate text and coordinates | `page.search_for()` or `page.get_text("dict", sort=True)` | Prefer span, line, or paragraph rectangles over blind global replacement |

### Add Text

```python
rect = pymupdf.Rect(72, 100, 300, 140)
remaining_height = page.insert_textbox(
    rect,
    "Additional text",
    fontname="helv",
    fontsize=11,
    color=(0, 0, 0),
    align=pymupdf.TEXT_ALIGN_LEFT,
    overlay=True,
)
if remaining_height < 0:
    raise ValueError("Text does not fit in the target rectangle")
```

For translated, multilingual, or variably sized text, prefer
`page.insert_htmlbox()`. Supply a known font through a PyMuPDF `Archive` and
CSS `@font-face` when glyph coverage matters. Do not assume an embedded subset
font contains the replacement characters.

### Replace or Remove Searchable Text

This pattern applies only when the requested edit actually replaces or removes
existing text. Add all redactions for a page before applying them.

```python
rect = pymupdf.Rect(72, 100, 300, 140)
page.add_redact_annot(rect, fill=False, cross_out=False)
page.apply_redactions(
    images=pymupdf.PDF_REDACT_IMAGE_NONE,
    graphics=pymupdf.PDF_REDACT_LINE_ART_NONE,
    text=pymupdf.PDF_REDACT_TEXT_REMOVE,
)

spare_height, scale = page.insert_htmlbox(
    rect,
    "Replacement text",
    css="* { font-family: sans-serif; font-size: 11pt; }",
    scale_low=0.75,
    overlay=True,
)
if spare_height < 0:
    raise ValueError("Replacement text does not fit")
```

Do not silently save clipped or missing replacement text. For text translation,
expand into confirmed whitespace, reduce font size within a legible limit, or
reflow only the affected region before considering document reconstruction.

## Image and Page-Content Editing

| Task | PyMuPDF Tool | Notes |
|------|----------------|-------|
| Add an image | `page.insert_image()` | Use `overlay=True` to place it above existing content |
| Replace an embedded image | `page.replace_image()` | Replacing an xref can affect every placement of that image in the document |
| Remove an embedded image | `page.delete_image()` | Check all pages that reuse the same image xref |
| Place another PDF page as content | `page.show_pdf_page()` | Useful for watermarks, templates, and vector-preserving overlays |
| Draw lines, shapes, or filled areas | `page.draw_line()`, `page.draw_rect()`, or `page.new_shape()` | Commit a `Shape` after composing multiple drawing operations |

```python
image_rect = pymupdf.Rect(72, 120, 272, 320)
page.insert_image(
    image_rect,
    filename="replacement.png",
    keep_proportion=True,
    overlay=True,
)
```

For page-level operations such as merge, split, rotate, crop, watermarks,
metadata, or encryption, follow the relevant guidance in [SKILL.md](SKILL.md).

## Annotation Editing

| Task | PyMuPDF Tool |
|------|----------------|
| Highlight text | `page.add_highlight_annot()` |
| Add a sticky-note comment | `page.add_text_annot()` |
| Add a visible free-text annotation | `page.add_freetext_annot()` |
| Add underline, strikeout, or squiggly markup | `page.add_underline_annot()`, `page.add_strikeout_annot()`, `page.add_squiggly_annot()` |
| Add ink or shapes | `page.add_ink_annot()`, `page.add_rect_annot()`, `page.add_circle_annot()` |
| Remove an annotation | `page.delete_annot()` |

```python
for rect in page.search_for("review this"):
    annotation = page.add_highlight_annot(rect)
    annotation.set_info(content="Needs review")
    annotation.update()
```

Annotations are not the same as permanent page content. If the result must be
non-editable or must print identically in every viewer, verify whether the task
requires annotation flattening or direct page-content insertion.

## Link Editing

| Task | PyMuPDF Tool |
|------|----------------|
| Inspect links | `page.get_links()` |
| Add a link | `page.insert_link()` |
| Change a link | `page.update_link()` |
| Remove a link | `page.delete_link()` |

```python
page.insert_link({
    "kind": pymupdf.LINK_URI,
    "from": pymupdf.Rect(72, 100, 220, 120),
    "uri": "https://example.com",
})
```

## Forms

Interactive form fields use a separate tool path. Follow [forms.md](forms.md)
for AcroForm inspection and filling. Do not replace form-field values with page
annotations unless the PDF is confirmed to be non-fillable or the user requests
a flattened visual result.

## Scanned or Outlined Content

Searchable-text tools cannot directly edit letters that are image pixels or
vector outlines.

- For scanned pages, use image-aware redaction or edit the raster region, then
  insert replacement content and inspect the reconstructed background.
- For outlined text, use visual coordinates and targeted drawing/redaction only
  when the surrounding graphics can be preserved.
- If localized editing cannot meet the requested quality, explain the limitation
  before rebuilding the affected page or document.

Read [SKILL.md](SKILL.md) for scanned-PDF rendering guidance.

## Save and Verify

```python
document.save("edited.pdf", garbage=4, deflate=True)
```

Before reporting completion, confirm that:

- the source file was not overwritten;
- page count, page dimensions, and non-target content remain as expected;
- inserted text and images are complete, legible, and correctly positioned;
- no target content remains visible when removal was requested;
- changed pages pass rendered visual inspection.

Use the ReportLab guidance in [SKILL.md](SKILL.md) only when the user requests a
new PDF or when direct editing cannot satisfy the requested layout. Use [reference.md](reference.md)
for advanced extraction, repair, JavaScript libraries, and troubleshooting.
