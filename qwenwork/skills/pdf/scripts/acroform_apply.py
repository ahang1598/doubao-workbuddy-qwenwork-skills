"""CLI: write values into a PDF's native (fillable) form fields.

Reads a ``field_values.json`` list where each entry carries a ``field_id``,
its ``page`` and the ``value`` to set, validates every entry against the
document's actual widgets, then writes a filled copy.

Usage: python acroform_apply.py <input pdf> <field_values.json> <output pdf>
"""

import json
import sys

from pypdf import PdfReader, PdfWriter

from acroform_model import enumerate_widgets


def _load_requested_values(values_path: str):
    """Return (raw entries, {page: {field_id: value}}) for the request file."""
    with open(values_path) as handle:
        entries = json.load(handle)

    per_page = {}
    for entry in entries:
        if "value" not in entry:
            continue
        per_page.setdefault(entry["page"], {})[entry["field_id"]] = entry["value"]
    return entries, per_page


def _value_rejection(widget, value):
    """Return an error string if ``value`` is illegal for ``widget``, else None."""
    kind = widget["type"]
    name = widget["field_id"]

    if kind == "checkbox":
        checked = widget["checked_value"]
        unchecked = widget["unchecked_value"]
        if value not in (checked, unchecked):
            return (
                f'ERROR: Invalid value "{value}" for checkbox field "{name}". '
                f'The checked value is "{checked}" and the unchecked value is '
                f'"{unchecked}"'
            )
    elif kind == "radio_group":
        allowed = [opt["value"] for opt in widget["radio_options"]]
        if value not in allowed:
            return (
                f'ERROR: Invalid value "{value}" for radio group field "{name}". '
                f"Valid values are: {allowed}"
            )
    elif kind == "choice":
        allowed = [opt["value"] for opt in widget["choice_options"]]
        if value not in allowed:
            return (
                f'ERROR: Invalid value "{value}" for choice field "{name}". '
                f"Valid values are: {allowed}"
            )
    return None


def _audit_request(entries, widgets_by_id) -> bool:
    """Print any problems with the requested entries; return True on failure."""
    failed = False
    for entry in entries:
        widget = widgets_by_id.get(entry["field_id"])
        if not widget:
            failed = True
            print(f"ERROR: `{entry['field_id']}` is not a valid field ID")
            continue
        if entry["page"] != widget["page"]:
            failed = True
            print(
                f"ERROR: Incorrect page number for `{entry['field_id']}` "
                f"(got {entry['page']}, expected {widget['page']})"
            )
            continue
        if "value" in entry:
            problem = _value_rejection(widget, entry["value"])
            if problem:
                print(problem)
                failed = True
    return failed


def apply_form_values(input_pdf: str, values_path: str, output_pdf: str) -> None:
    entries, per_page = _load_requested_values(values_path)

    reader = PdfReader(input_pdf)
    widgets_by_id = {w["field_id"]: w for w in enumerate_widgets(reader)}

    if _audit_request(entries, widgets_by_id):
        sys.exit(1)

    writer = PdfWriter(clone_from=reader)
    for page, values in per_page.items():
        writer.update_page_form_field_values(
            writer.pages[page - 1], values, auto_regenerate=False
        )
    writer.set_need_appearances_writer(True)

    with open(output_pdf, "wb") as handle:
        writer.write(handle)


def _install_choice_option_shim():
    """Normalize export/import (/Opt) pairs so choice values compare cleanly."""
    from pypdf.generic import DictionaryObject
    from pypdf.constants import FieldDictionaryAttributes

    inherited = DictionaryObject.get_inherited

    def shimmed(self, key, default=None):
        result = inherited(self, key, default)
        if key == FieldDictionaryAttributes.Opt:
            if isinstance(result, list) and all(
                isinstance(v, list) and len(v) == 2 for v in result
            ):
                result = [pair[0] for pair in result]
        return result

    DictionaryObject.get_inherited = shimmed


def main(argv):
    if len(argv) != 4:
        print("Usage: acroform_apply.py [input pdf] [field_values.json] [output pdf]")
        sys.exit(1)
    _install_choice_option_shim()
    apply_form_values(argv[1], argv[2], argv[3])


if __name__ == "__main__":
    main(sys.argv)
