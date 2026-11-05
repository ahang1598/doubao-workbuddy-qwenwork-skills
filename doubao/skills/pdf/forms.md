**CRITICAL: You MUST complete these steps in order. Do not skip ahead to writing code.**

The bundled rendering, structure-extraction, and annotation scripts use PyMuPDF. The fillable-field extraction and update scripts intentionally retain pypdf because they inspect the canonical AcroForm field tree, parent/kid relationships, export states, and appearance behavior.

If you need to fill out a PDF form, run
`python scripts/extract_form_field_info.py <input.pdf> <field_info.json>`.
Use the "Fillable fields" path when the output contains fields; otherwise use
the "Non-fillable fields" path.

# Fillable fields
If the PDF has fillable form fields:
- Use the generated `field_info.json`, whose fields follow this conceptual schema:
```text
[
  {
    "field_id": (unique ID for the field),
    "page": (page number, 1-based),
    "rect": ([left, bottom, right, top] bounding box in raw PDF/AcroForm coordinates returned by pypdf; the origin is at the bottom-left and y increases upward),
    "type": ("text", "checkbox", "radio_group", or "choice"),
  },
  // Checkboxes have "checked_value" and "unchecked_value" properties:
  {
    "field_id": (unique ID for the field),
    "page": (page number, 1-based),
    "type": "checkbox",
    "checked_value": (Set the field to this value to check the checkbox),
    "unchecked_value": (Set the field to this value to uncheck the checkbox),
  },
  // Radio groups have a "radio_options" list with the possible choices.
  {
    "field_id": (unique ID for the field),
    "page": (page number, 1-based),
    "type": "radio_group",
    "radio_options": [
      {
        "value": (set the field to this value to select this radio option),
        "rect": (bounding box for the radio button for this option)
      },
      // Other radio options
    ]
  },
  // Multiple choice fields have a "choice_options" list with the possible choices:
  {
    "field_id": (unique ID for the field),
    "page": (page number, 1-based),
    "type": "choice",
    "choice_options": [
      {
        "value": (set the field to this value to select this option),
        "text": (display text of the option)
      },
      // Other choice options
    ],
  }
]
```
- Convert the PDF to PNGs (one image for each page) with this script (run from this file's directory):
`python scripts/convert_pdf_to_images.py <file.pdf> <output_directory>`
Then analyze the images to determine the purpose of each form field (make sure to convert the raw PDF/AcroForm bounding-box coordinates to image coordinates).
- Create a `field_values.json` file in this format with the values to be entered for each field:
```json
[
  {
    "field_id": "last_name",
    "description": "The user's last name",
    "page": 1,
    "value": "Simpson"
  },
  {
    "field_id": "Checkbox12",
    "description": "Checkbox to be checked if the user is 18 or over",
    "page": 1,
    "value": "/On"
  }
]
```
Each `field_id` and `page` must match `field_info.json`. For checkboxes, use the extracted `checked_value` or `unchecked_value`; for radio groups, use one of the extracted `radio_options[].value` values.
- Run the `fill_fillable_fields.py` script from this file's directory to create a filled-in PDF:
`python scripts/fill_fillable_fields.py <input pdf> <field_values.json> <output pdf>`
The script writes the supplied field values directly.

# Non-fillable fields
If the PDF doesn't have fillable form fields, you'll add text annotations. First try to extract coordinates from the PDF structure (more accurate), then fall back to visual estimation if needed.

## Step 1: Try Structure Extraction First

Run this script to extract text labels, lines, and checkboxes with their exact PyMuPDF page coordinates:
`python scripts/extract_form_structure.py <input.pdf> form_structure.json`

This creates a JSON file containing:
- **labels**: Every text element with exact coordinates (x0, top, x1, bottom in PDF points)
- **lines**: Horizontal lines that define row boundaries
- **checkboxes**: Small square rectangles that are checkboxes (with center coordinates)
- **row_boundaries**: Row top/bottom positions calculated from horizontal lines

If `form_structure.json` has meaningful labels that correspond to form fields,
use **Approach A: Structure-Based Coordinates**. If the PDF is scanned or
image-based and has few or no labels, use **Approach B: Visual Estimation**.

---

## Approach A: Structure-Based Coordinates (Preferred)

Use this when `extract_form_structure.py` found text labels in the PDF.

### A.1: Analyze the Structure

Read form_structure.json and identify:

1. **Label groups**: Adjacent text elements that form a single label (e.g., "Last" + "Name")
2. **Row structure**: Labels with similar `top` values are in the same row
3. **Field columns**: Entry areas start after label ends (x0 = label.x1 + gap)
4. **Checkboxes**: Use the checkbox coordinates directly from the structure

**Coordinate system**: PyMuPDF (MuPDF) page coordinates, where the origin is at the top-left and y increases downward. In the JSON, `top` stores `y0` (the upper edge) and `bottom` stores `y1` (the lower edge), so `top < bottom` for a valid box.

### A.2: Create fields.json with PyMuPDF Page Coordinates

For each field, calculate entry coordinates from the extracted structure:

**Text fields:**
- entry x0 = label x1 + 5 (small gap after label)
- entry x1 = next label's x0, or row boundary
- entry top = same as label top
- entry bottom = row boundary line below, or label bottom + row_height

**Checkboxes:**
- Use the checkbox rectangle coordinates directly from form_structure.json
- entry_bounding_box = [checkbox.x0, checkbox.top, checkbox.x1, checkbox.bottom]

Create fields.json using `pdf_width` and `pdf_height` (these keys signal PyMuPDF page coordinates to the bundled fill script):
```json
{
  "pages": [
    {"page_number": 1, "pdf_width": 612, "pdf_height": 792}
  ],
  "form_fields": [
    {
      "page_number": 1,
      "description": "Last name entry field",
      "field_label": "Last Name",
      "label_bounding_box": [43, 63, 87, 73],
      "entry_bounding_box": [92, 63, 260, 79],
      "entry_text": {"text": "Smith", "font_size": 10}
    },
    {
      "page_number": 1,
      "description": "US Citizen Yes checkbox",
      "field_label": "Yes",
      "label_bounding_box": [260, 200, 280, 210],
      "entry_bounding_box": [285, 197, 292, 205],
      "entry_text": {"text": "X"}
    }
  ]
}
```

**Important**: Use `pdf_width`/`pdf_height` and the PyMuPDF coordinates directly from form_structure.json. Despite the key names, these are not raw bottom-left-origin PDF coordinates.

---

## Approach B: Visual Estimation (Fallback)

Use this when the PDF is scanned/image-based and structure extraction found no usable text labels (e.g., all text shows as "(cid:X)" patterns).

### B.1: Convert PDF to Images

`python scripts/convert_pdf_to_images.py <input.pdf> <images_dir/>`

### B.2: Initial Field Identification

Examine each page image to identify form sections and get **rough estimates** of field locations:
- Form field labels and their approximate positions
- Entry areas (lines, boxes, or blank spaces for text input)
- Checkboxes and their approximate locations

For each field, note approximate pixel coordinates (they don't need to be precise yet).

### B.3: Zoom Refinement (CRITICAL for accuracy)

For each field, crop a region around the estimated position to refine coordinates precisely.

**Create a zoomed crop using the bundled Pillow script:**
```bash
python scripts/crop_image.py <page_image> <crop_output.png> <left> <top> <right> <bottom>
```

Where:
- `<left>, <top>` = top-left corner of the crop region
- `<right>, <bottom>` = bottom-right corner of the crop region
- Add about 50 pixels of padding around the estimated field when possible

**Example:** To refine a "Name" field estimated around (100, 150):
```bash
python scripts/crop_image.py images_dir/page_1.png crops/name_field.png 50 120 350 200
```

**Examine the cropped image** to determine precise coordinates:
1. Identify the exact pixel where the entry area begins (after the label)
2. Identify where the entry area ends (before next field or edge)
3. Identify the top and bottom of the entry line/box

**Convert crop coordinates back to full image coordinates:**
- full_x = crop_x + crop_offset_x
- full_y = crop_y + crop_offset_y

Example: If the crop started at (50, 120) and the entry box starts at (52, 18) within the crop:
- entry_x0 = 52 + 50 = 102
- entry_top = 18 + 120 = 138

**Repeat for each field**, grouping nearby fields into single crops when possible.

### B.4: Create fields.json with Refined Coordinates

Create fields.json using `image_width` and `image_height` (signals image coordinates):
```json
{
  "pages": [
    {"page_number": 1, "image_width": 1700, "image_height": 2200}
  ],
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

**Important**: Use `image_width`/`image_height` and the refined pixel coordinates from the zoom analysis.

---

## Step 2: Fill the Form

The fill script auto-detects the coordinate system and handles conversion:
`python scripts/fill_pdf_form_with_annotations.py <input.pdf> fields.json <output.pdf>`
