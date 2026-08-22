"""Report whether a PDF contains interactive fillable form fields."""

import argparse

import pymupdf


def check_fillable_fields(pdf_path):
    """Print the PDF form-field status and return whether fields exist."""
    with pymupdf.open(pdf_path) as document:
        if document.is_form_pdf:
            print("This PDF has fillable form fields")
            return True

        print(
            "WARNING: This PDF does not have fillable form fields; "
            "you will need to visually determine where to enter data"
        )
        return False


def main():
    """Parse arguments and inspect the requested PDF."""
    parser = argparse.ArgumentParser(
        description="Report whether a PDF contains interactive form fields."
    )
    parser.add_argument("input_pdf", help="Path to the input PDF")
    args = parser.parse_args()
    check_fillable_fields(args.input_pdf)


if __name__ == "__main__":
    main()
