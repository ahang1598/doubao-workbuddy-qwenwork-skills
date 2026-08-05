"""CLI: export the interactive form widgets of a PDF to JSON.

The emitted JSON is a flat list of widget descriptors (text inputs,
checkboxes, radio groups, choice lists) each carrying a stable ``field_id``,
its 1-based ``page`` and PDF-space ``rect``. The value writer consumes the
same ``field_id`` values.

Usage: python acroform_export.py <input.pdf> <output.json>
"""

import json
import sys

from pypdf import PdfReader

from acroform_model import enumerate_widgets


def export_widgets(pdf_path: str, json_path: str) -> None:
    widgets = enumerate_widgets(PdfReader(pdf_path))
    with open(json_path, "w") as handle:
        json.dump(widgets, handle, indent=2)
    print(f"Wrote {len(widgets)} fields to {json_path}")


def main(argv):
    if len(argv) != 3:
        print("Usage: acroform_export.py [input pdf] [output json]")
        sys.exit(1)
    export_widgets(argv[1], argv[2])


if __name__ == "__main__":
    main(sys.argv)
