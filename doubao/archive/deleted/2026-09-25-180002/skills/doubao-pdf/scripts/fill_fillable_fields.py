"""Fill canonical AcroForm values with pypdf.

PyMuPDF remains the primary library elsewhere in this skill; this script keeps
pypdf for field-tree validation and appearance-sensitive AcroForm updates.
"""

import argparse
import json
import sys

from pypdf import PdfReader, PdfWriter

from extract_form_field_info import get_field_info


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

    has_error = False
    field_info = get_field_info(reader)
    fields_by_ids = {f["field_id"]: f for f in field_info}
    for field in fields:
        existing_field = fields_by_ids.get(field["field_id"])
        if not existing_field:
            has_error = True
            print(f"ERROR: `{field['field_id']}` is not a valid field ID")
        elif field["page"] != existing_field["page"]:
            has_error = True
            print(f"ERROR: Incorrect page number for `{field['field_id']}` (got {field['page']}, expected {existing_field['page']})")
        else:
            if "value" in field:
                err = validation_error_for_field_value(existing_field, field["value"])
                if err:
                    print(err)
                    has_error = True
    if has_error:
        sys.exit(1)

    writer = PdfWriter(clone_from=reader)
    for page, field_values in fields_by_page.items():
        writer.update_page_form_field_values(writer.pages[page - 1], field_values, auto_regenerate=False)

    writer.set_need_appearances_writer(True)

    with open(output_pdf_path, "wb") as f:
        writer.write(f)


def validation_error_for_field_value(field_info, field_value):
    field_type = field_info["type"]
    field_id = field_info["field_id"]
    if field_type == "checkbox":
        valid_values = [
            value
            for value in (
                field_info.get("checked_value"),
                field_info.get("unchecked_value"),
            )
            if value is not None
        ]
        if not valid_values:
            return f'ERROR: No valid state values were found for checkbox field "{field_id}"'
        if field_value not in valid_values:
            return f'ERROR: Invalid value "{field_value}" for checkbox field "{field_id}". Valid values are: {valid_values}'
    elif field_type == "radio_group":
        option_values = [opt["value"] for opt in field_info["radio_options"]]
        if field_value not in option_values:
            return f'ERROR: Invalid value "{field_value}" for radio group field "{field_id}". Valid values are: {option_values}'
    elif field_type == "choice":
        choice_values = [opt["value"] for opt in field_info["choice_options"]]
        if field_value not in choice_values:
            return f'ERROR: Invalid value "{field_value}" for choice field "{field_id}". Valid values are: {choice_values}'
    return None


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
