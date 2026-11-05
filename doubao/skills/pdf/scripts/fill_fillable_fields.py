"""Fill canonical AcroForm values with pypdf.

PyMuPDF remains the primary library elsewhere in this skill; this script keeps
pypdf for appearance-sensitive AcroForm updates.
"""

import argparse
import json

from pypdf import PdfReader, PdfWriter


def fill_pdf_fields(input_pdf_path: str, fields_json_path: str, output_pdf_path: str):
    with open(fields_json_path, encoding="utf-8") as f:
        fields = json.load(f)
    fields_by_page = {}
    for field in fields:
        if "value" in field:
            field_id = field["field_id"]
            page = field["page"]
            if page not in fields_by_page:
                fields_by_page[page] = {}
            fields_by_page[page][field_id] = field["value"]

    reader = PdfReader(input_pdf_path)

    writer = PdfWriter(clone_from=reader)
    for page, field_values in fields_by_page.items():
        writer.update_page_form_field_values(writer.pages[page - 1], field_values, auto_regenerate=False)

    writer.set_need_appearances_writer(True)

    with open(output_pdf_path, "wb") as f:
        writer.write(f)


def monkeypatch_pypdf_method():
    from pypdf.generic import DictionaryObject
    from pypdf.constants import FieldDictionaryAttributes

    original_get_inherited = DictionaryObject.get_inherited

    def patched_get_inherited(self, key: str, default=None):
        result = original_get_inherited(self, key, default)
        if key == FieldDictionaryAttributes.Opt:
            if isinstance(result, list) and all(isinstance(v, list) and len(v) == 2 for v in result):
                result = [r[0] for r in result]
        return result

    DictionaryObject.get_inherited = patched_get_inherited


def main():
    """Parse arguments and fill canonical AcroForm fields."""
    parser = argparse.ArgumentParser(
        description="Fill canonical AcroForm fields from a JSON value file."
    )
    parser.add_argument("input_pdf", help="Path to the input PDF")
    parser.add_argument("fields_json", help="Path to the field-values JSON file")
    parser.add_argument("output_pdf", help="Path for the filled output PDF")
    args = parser.parse_args()

    monkeypatch_pypdf_method()
    fill_pdf_fields(args.input_pdf, args.fields_json, args.output_pdf)


if __name__ == "__main__":
    main()
