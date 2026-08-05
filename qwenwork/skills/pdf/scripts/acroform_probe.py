"""CLI: report whether a PDF exposes interactive (fillable) form fields.

Usage: python acroform_probe.py <file.pdf>
"""

import sys

from pypdf import PdfReader


def has_interactive_form(pdf_path: str) -> bool:
    """Return True when the document carries an AcroForm field dictionary."""
    return bool(PdfReader(pdf_path).get_fields())


def main(argv):
    if len(argv) != 2:
        print("Usage: acroform_probe.py <file.pdf>")
        sys.exit(1)

    if has_interactive_form(argv[1]):
        print("This PDF has fillable form fields")
    else:
        print(
            "This PDF does not have fillable form fields; you will need to "
            "visually determine where to enter data"
        )


if __name__ == "__main__":
    main(sys.argv)
