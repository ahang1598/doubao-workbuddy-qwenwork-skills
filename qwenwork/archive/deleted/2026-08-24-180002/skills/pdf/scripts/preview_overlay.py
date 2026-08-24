"""CLI: draw label/entry bounding boxes on a rendered page image.

Entry boxes are outlined in red and label boxes in blue so placement can be
sanity-checked visually against a rasterized page.

Usage: python preview_overlay.py [page number] [fields.json] [input image] [output image]
"""

import json
import sys

from PIL import Image, ImageDraw

_ENTRY_COLOR = "red"
_LABEL_COLOR = "blue"
_STROKE = 2


def draw_overlay(page_number, fields_json_path, input_path, output_path):
    with open(fields_json_path) as handle:
        document = json.load(handle)

    image = Image.open(input_path)
    canvas = ImageDraw.Draw(image)

    drawn = 0
    for field in document["form_fields"]:
        if field["page_number"] != page_number:
            continue
        canvas.rectangle(field["entry_bounding_box"], outline=_ENTRY_COLOR, width=_STROKE)
        canvas.rectangle(field["label_bounding_box"], outline=_LABEL_COLOR, width=_STROKE)
        drawn += 2

    image.save(output_path)
    print(f"Created validation image at {output_path} with {drawn} bounding boxes")


def main(argv):
    if len(argv) != 5:
        print(
            "Usage: preview_overlay.py [page number] [fields.json file] "
            "[input image path] [output image path]"
        )
        sys.exit(1)
    draw_overlay(int(argv[1]), argv[2], argv[3], argv[4])


if __name__ == "__main__":
    main(sys.argv)
