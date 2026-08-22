"""Fill non-interactive PDF forms with positioned free-text annotations."""

import argparse
import json

import pymupdf


def transform_from_image_coords(bbox, image_width, image_height, pdf_width, pdf_height):
    x_scale = pdf_width / image_width
    y_scale = pdf_height / image_height

    left = bbox[0] * x_scale
    right = bbox[2] * x_scale

    top = bbox[1] * y_scale
    bottom = bbox[3] * y_scale

    return left, top, right, bottom


def transform_from_pdf_coords(bbox):
    return tuple(bbox)


def color_from_hex(value):
    value = value.lstrip("#")
    if len(value) != 6:
        raise ValueError(f"Expected a six-digit RGB color, got: {value!r}")
    return tuple(int(value[index:index + 2], 16) / 255 for index in (0, 2, 4))


def font_for_text(requested_font, text):
    if any("\u3400" <= char <= "\u9fff" for char in text):
        return "china-s"
    aliases = {
        "arial": "helv",
        "helvetica": "helv",
        "times": "tiro",
        "times new roman": "tiro",
        "courier": "cour",
    }
    return aliases.get(requested_font.lower(), requested_font)


def fill_pdf_form(input_pdf_path, fields_json_path, output_pdf_path):
    with open(fields_json_path, "r", encoding="utf-8") as f:
        fields_data = json.load(f)

    with pymupdf.open(input_pdf_path) as document:
        annotation_count = 0
        for field in fields_data["form_fields"]:
            page_num = field["page_number"]
            page = document[page_num - 1]
            page_info = next(
                item for item in fields_data["pages"]
                if item["page_number"] == page_num
            )

            if "pdf_width" in page_info:
                transformed_entry_box = transform_from_pdf_coords(
                    field["entry_bounding_box"]
                )
            else:
                transformed_entry_box = transform_from_image_coords(
                    field["entry_bounding_box"],
                    page_info["image_width"],
                    page_info["image_height"],
                    float(page.rect.width),
                    float(page.rect.height),
                )

            entry_text = field.get("entry_text", {})
            text = entry_text.get("text")
            if not text:
                continue

            requested_font = entry_text.get("font", "Arial")
            page.add_freetext_annot(
                pymupdf.Rect(transformed_entry_box),
                text,
                fontname=font_for_text(requested_font, text),
                fontsize=float(entry_text.get("font_size", 14)),
                text_color=color_from_hex(entry_text.get("font_color", "000000")),
                fill_color=None,
                border_color=None,
                border_width=0,
            )
            annotation_count += 1

        document.save(output_pdf_path, garbage=4, deflate=True)

    print(f"Successfully filled PDF form and saved to {output_pdf_path}")
    print(f"Added {annotation_count} text annotations")


def main():
    """Parse arguments and fill a non-interactive PDF form."""
    parser = argparse.ArgumentParser(
        description="Fill a non-interactive PDF form using positioned annotations."
    )
    parser.add_argument("input_pdf", help="Path to the input PDF")
    parser.add_argument("fields_json", help="Path to the fields JSON file")
    parser.add_argument("output_pdf", help="Path for the filled output PDF")
    args = parser.parse_args()

    fill_pdf_form(args.input_pdf, args.fields_json, args.output_pdf)


if __name__ == "__main__":
    main()
