"""Draw form-field label and entry boxes on a rendered page image."""

import argparse
import json

from PIL import Image, ImageDraw


def create_validation_image(page_number, fields_json_path, input_path, output_path):
    with open(fields_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    with Image.open(input_path) as img:
        draw = ImageDraw.Draw(img)
        num_boxes = 0

        for field in data["form_fields"]:
            if field["page_number"] == page_number:
                entry_box = field["entry_bounding_box"]
                label_box = field["label_bounding_box"]
                draw.rectangle(entry_box, outline="red", width=2)
                draw.rectangle(label_box, outline="blue", width=2)
                num_boxes += 2

        img.save(output_path)
        print(
            f"Created validation image at {output_path} "
            f"with {num_boxes} bounding boxes"
        )


def main():
    """Parse arguments and create a validation overlay image."""
    parser = argparse.ArgumentParser(
        description="Draw form-field label and entry boxes on a page image."
    )
    parser.add_argument("page_number", type=int, help="One-based PDF page number")
    parser.add_argument("fields_json", help="Path to the fields JSON file")
    parser.add_argument("input_image", help="Path to the rendered page image")
    parser.add_argument("output_image", help="Path for the validation image")
    args = parser.parse_args()
    create_validation_image(
        args.page_number,
        args.fields_json,
        args.input_image,
        args.output_image,
    )


if __name__ == "__main__":
    main()
