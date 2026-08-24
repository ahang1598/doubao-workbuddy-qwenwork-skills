# Forms Guide

## Determining Form Type

Always run `inspect_form.py` before attempting to fill a PDF form.
The output tells you which filling strategy to use.

```bash
python scripts/inspect_form.py form.pdf --output fields.json
```

The `form_type` field in the output JSON is the key:

| `form_type` | Meaning | Filling strategy |
|---|---|---|
| `acroform` | Has standard fillable fields (AcroForm) | `fill_form.py` — set `fill_value` in fields array |
| `layout_based` | No fillable fields — plain document | `fill_form.py` — set `fill_value` in annotations array |

---

## AcroForm Filling

### Field types and how to fill them

**Text field:**
```json
{
  "name": "FullName",
  "type": "text",
  "fill_value": "Jane Smith"
}
```

**Checkbox:**
```json
{
  "name": "AgreeTerms",
  "type": "checkbox",
  "checked_value": "Yes",
  "unchecked_value": "Off",
  "fill_value": "true"
}
```
Set `fill_value` to any of: `"true"`, `"yes"`, `"1"`, `"on"` to check.
Any other value leaves the box unchecked.

**Choice (dropdown/listbox):**
```json
{
  "name": "Country",
  "type": "choice",
  "options": ["USA", "Canada", "UK"],
  "fill_value": "Canada"
}
```
`fill_value` must exactly match one of the options.

**Signature field:**
```json
{
  "name": "Signature",
  "type": "signature",
  "fill_value": ""
}
```
Signature fields cannot be filled programmatically in a legally valid way.
Leave `fill_value` empty and sign manually after generation.

---

## Layout-Based Filling

For non-fillable PDFs, `inspect_form.py` returns an `annotations` array
where each entry has a detected label and a suggested coordinate for the fill text.

### Editing the annotation JSON

```json
{
  "page": 1,
  "label": "Date of Birth:",
  "fill_x": 125.3,
  "fill_y": 210.5,
  "fill_value": "1990-06-15"
}
```

Set `fill_value` on the entries that correspond to fields you want to fill.
Leave `fill_value` as `""` to skip a field.

### Coordinate system

PDF files use **two different coordinate systems** depending on the tool:

| Tool | Origin | Y direction |
|---|---|---|
| PDF specification (pypdf) | Bottom-left corner | Upward |
| pdfplumber / inspect_form.py | Top-left corner | Downward |
| Image pixels (rendered PNG via pypdfium2) | Top-left corner | Downward |

`inspect_form.py` outputs pdfplumber coordinates (top-left origin).
`fill_form.py` converts them to PDF bottom-left origin automatically — you do not need to do this manually.

**Conversion formula** (if you ever need to do it yourself):
```
pdf_y = page_height_pt - pdfplumber_top
```

**Image ↔ PDF point conversion** (when working from a rendered PNG):
```
pdf_x = image_x * (pdf_width_pt  / image_width_px)
pdf_y = image_y * (pdf_height_pt / image_height_px)
```

Standard page sizes for reference:
- A4: 595 × 842 pt
- US Letter: 612 × 792 pt

### Verifying placement

Run `debug_annotations.py` before filling to visually confirm coordinates:

```bash
python scripts/debug_annotations.py form.pdf fields.json --output-dir debug/ --dpi 150
# Open debug/debug_page001.png — green = label zone, red = fill zone
```

If text is offset after filling, adjust `fill_x` / `fill_y` in the JSON and re-run debug until aligned, then fill.

### Font size

Default font size is 10pt. For smaller fields, use `--font-size 8`.
For larger/prominent fields, use `--font-size 12`.

---

## Overlay filling (`fill_form_overlay.py`) — flat & scanned PDFs

`fill_form.py` handles AcroForm widgets (the path above). When a PDF has
no widgets — flat-print intake forms, scanned originals, decorative PDFs
exported from Word — switch to the **overlay** path:

```
extract_form_structure.py  →  fields.json  →  check_bounding_boxes.py  →  fill_form_overlay.py
```

`fill_form_overlay.py` builds a reportlab text stamp per page and merges
it onto the original with `pypdf.PdfWriter.merge_page`. The stamp embeds
the glyph bytes via `_fonts.py`'s CJK-aware family, so Chinese / Japanese /
Korean text renders correctly across viewers — unlike `FreeText`
annotations, which depend on the viewer's font lookup.

### Decision tree

```
flat / scanned PDF
│
├─ Does extract_form_structure.py find usable labels?
│   ├─ YES → Approach A: structure-based coordinates (preferred)
│   ├─ PARTIAL → Approach C: hybrid (A for detected, B for missed)
│   └─ NO (cid:X garbage, image-only scans) → Approach B: visual estimation
│
└─ Always: check_bounding_boxes.py → fill_form_overlay.py → render the
    filled output with convert_pdf_to_images.py for an eyeball verification.
```

### Approach A — structure-based coordinates

Use when `extract_form_structure.py` found real text labels. Read the
JSON, group adjacent label words into logical labels, identify the row a
label sits in (similar `top`), and compute entry boxes from labels +
rows + checkboxes.

**Text fields:**
- `entry.x0 = label.x1 + 5` (small gap after label)
- `entry.x1 = next_label.x0` or row boundary on the right
- `entry.top = label.top`
- `entry.bottom = next row boundary` or `label.bottom + row_height`

**Checkboxes:** use the rectangle directly from `form_structure.json`.

Emit `fields.json` with `pdf_width`/`pdf_height` per page (this signals
PDF-point coordinates):

```json
{
  "pages": [{"page_number": 1, "pdf_width": 612, "pdf_height": 792}],
  "form_fields": [
    {
      "page_number": 1,
      "description": "Last name entry field",
      "field_label": "Last Name",
      "label_bounding_box": [43, 63, 87, 73],
      "entry_bounding_box": [92, 63, 260, 79],
      "entry_text": {"text": "陈炳材", "font_size": 10}
    },
    {
      "page_number": 1,
      "description": "US citizen — Yes",
      "field_label": "Yes",
      "label_bounding_box": [260, 200, 280, 210],
      "entry_bounding_box": [285, 197, 292, 205],
      "entry_text": {"text": "X"}
    }
  ]
}
```

### Approach B — visual estimation

Use only when structure extraction is empty / `(cid:X)` garbage.

1. Render the page: `python scripts/convert_pdf_to_images.py form.pdf --output pages/ --dpi 200`
2. Inspect each PNG, estimate each field's pixel bounding box.
3. For tighter coordinates, crop with Pillow rather than ImageMagick:
   ```python
   from PIL import Image
   Image.open("pages/page_001.png").crop((50, 200, 350, 280)).save("crop.png")
   ```
4. Emit `fields.json` with `image_width`/`image_height` per page (this
   signals pixel coordinates — `fill_form_overlay.py` scales them to
   PDF points internally):

```json
{
  "pages": [{"page_number": 1, "image_width": 1654, "image_height": 2339}],
  "form_fields": [
    {
      "page_number": 1,
      "description": "Last name entry field",
      "field_label": "Last Name",
      "label_bounding_box": [120, 175, 242, 198],
      "entry_bounding_box": [255, 175, 720, 218],
      "entry_text": {"text": "Smith", "font_size": 10}
    }
  ]
}
```

### Approach C — hybrid

Mix the two when structure catches most fields but misses some (circular
checkboxes, faded entries). Keep everything in **one** coordinate system
in the output JSON; if you used B for some fields, convert to PDF points
with `pdf_x = image_x * pdf_w / image_w`, `pdf_y = image_y * pdf_h / image_h`
and declare `pdf_width`/`pdf_height` for all pages.

### Coordinate convention

`fields.json` always uses **top-left** origin (y=0 at top, y grows down)
— the same convention `extract_form_structure.py` emits and pdfplumber
uses. `fill_form_overlay.py` flips Y once internally for PDF's
bottom-left origin. **Do not pre-flip Y yourself.**

### CJK text

`fill_form_overlay.py` registers a CJK font family on startup via
`_fonts.py`. If a `text` field contains CJK characters, it draws with
the registered family (e.g. `CJK` → PingFang/YaHei/Noto). Otherwise it
draws with Helvetica. No agent-side action required.

If `_fonts.py` cannot find any system CJK font, the script prints a
warning and Chinese text will render as boxes. Set the
`WUKONG_CJK_FONT` env var to an explicit TTF path to override.

### Validation before write

Always run `check_bounding_boxes.py fields.json` before
`fill_form_overlay.py`. It catches:
- Intersecting label/entry boxes (overlapping text)
- Entry box height < font size (text clips)

### Verify after write

```bash
python scripts/fill_form_overlay.py form.pdf fields.json filled.pdf
python scripts/convert_pdf_to_images.py filled.pdf --output verify/ --dpi 150
# Eyeball verify/page_*.png — text should sit cleanly within each entry box.
```

---

## Multi-Page Forms

`fill_form.py` handles multi-page forms:
- AcroForm: `update_page_form_field_values` is called on all pages.
- Annotation-based: the `page` field in each annotation entry routes the
  text to the correct page. Ensure page numbers in the JSON match the actual form.
