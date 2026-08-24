#!/usr/bin/env python3
"""
secure_pdf.py — PDF Security Operations

Handles encryption, decryption, redaction, and permission management.

Usage:
    # Encrypt with user and owner passwords
    python scripts/secure_pdf.py --action encrypt \
        --input doc.pdf --output secured.pdf \
        --user-password "read123" --owner-password "admin456"

    # Decrypt (provide owner password)
    python scripts/secure_pdf.py --action decrypt \
        --input secured.pdf --output plain.pdf \
        --password "admin456"

    # Redact text patterns (replaces matched text areas with black boxes)
    python scripts/secure_pdf.py --action redact \
        --input contract.pdf --output redacted.pdf \
        --patterns "SSN" "email" --custom-pattern "\\d{3}-\\d{2}-\\d{4}"

    # Remove all metadata
    python scripts/secure_pdf.py --action strip-metadata \
        --input doc.pdf --output clean.pdf
"""

import argparse
import re
import sys
from pathlib import Path


def action_encrypt(input_path: Path, output_path: Path,
                   user_pw: str, owner_pw: str) -> None:
    try:
        import pypdf
    except ImportError:
        print("Error: pypdf required. Run: pip install pypdf", file=sys.stderr)
        sys.exit(1)

    reader = pypdf.PdfReader(str(input_path))
    writer = pypdf.PdfWriter()
    writer.append(reader)
    writer.encrypt(user_password=user_pw, owner_password=owner_pw)
    with open(output_path, "wb") as fh:
        writer.write(fh)
    print(f"Encrypted → {output_path}")
    print(f"  User password:  {user_pw}")
    print(f"  Owner password: {owner_pw}")


def action_decrypt(input_path: Path, output_path: Path, password: str) -> None:
    try:
        import pypdf
    except ImportError:
        print("Error: pypdf required. Run: pip install pypdf", file=sys.stderr)
        sys.exit(1)

    reader = pypdf.PdfReader(str(input_path))
    if reader.is_encrypted:
        result = reader.decrypt(password)
        if result == pypdf.PasswordType.NOT_DECRYPTED:
            print("Error: wrong password", file=sys.stderr)
            sys.exit(1)

    writer = pypdf.PdfWriter()
    writer.append(reader)
    with open(output_path, "wb") as fh:
        writer.write(fh)
    print(f"Decrypted → {output_path}")


BUILTIN_PATTERNS = {
    "SSN": r"\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b",
    "email": r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b",
    "phone": r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
    "credit_card": r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
    "ip_address": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
}


def action_redact(input_path: Path, output_path: Path,
                  pattern_names: list[str], custom_patterns: list[str]) -> None:
    """
    Redact text matching given patterns by drawing black rectangles over them.
    Uses pdfplumber to locate text, pypdf to write black annotation boxes.
    """
    try:
        import pdfplumber
        import pypdf
        import pypdf.generic as generic
    except ImportError:
        print("Error: pypdf and pdfplumber required.", file=sys.stderr)
        sys.exit(1)

    # Build combined regex
    patterns: list[str] = []
    for name in pattern_names:
        if name in BUILTIN_PATTERNS:
            patterns.append(BUILTIN_PATTERNS[name])
        else:
            print(f"Warning: unknown pattern name '{name}', skipping", file=sys.stderr)
    patterns.extend(custom_patterns)

    if not patterns:
        print("Error: no valid patterns specified", file=sys.stderr)
        sys.exit(1)

    combined_re = re.compile("|".join(patterns), re.IGNORECASE)

    reader = pypdf.PdfReader(str(input_path))
    writer = pypdf.PdfWriter()
    writer.append(reader)

    redaction_count = 0

    with pdfplumber.open(str(input_path)) as plumber_doc:
        for page_idx, plumber_page in enumerate(plumber_doc.pages):
            if page_idx >= len(writer.pages):
                break
            writer_page = writer.pages[page_idx]
            page_height = float(plumber_page.height)

            words = plumber_page.extract_words(x_tolerance=3, y_tolerance=3) or []
            for word in words:
                if not combined_re.search(word["text"]):
                    continue

                # Convert pdfplumber coords (top-origin) to PDF (bottom-origin)
                x0 = float(word["x0"]) - 1
                x1 = float(word["x1"]) + 1
                y0 = page_height - float(word["bottom"]) - 1
                y1 = page_height - float(word["top"]) + 1

                black_box = generic.DictionaryObject({
                    generic.NameObject("/Type"): generic.NameObject("/Annot"),
                    generic.NameObject("/Subtype"): generic.NameObject("/Square"),
                    generic.NameObject("/Rect"): generic.ArrayObject([
                        generic.FloatObject(x0), generic.FloatObject(y0),
                        generic.FloatObject(x1), generic.FloatObject(y1),
                    ]),
                    generic.NameObject("/IC"): generic.ArrayObject([
                        generic.FloatObject(0), generic.FloatObject(0), generic.FloatObject(0)
                    ]),
                    generic.NameObject("/C"): generic.ArrayObject([
                        generic.FloatObject(0), generic.FloatObject(0), generic.FloatObject(0)
                    ]),
                    generic.NameObject("/F"): generic.NumberObject(4),
                })

                if "/Annots" not in writer_page:
                    writer_page[generic.NameObject("/Annots")] = generic.ArrayObject()
                writer_page["/Annots"].append(writer._add_object(black_box))
                redaction_count += 1

    with open(output_path, "wb") as fh:
        writer.write(fh)
    print(f"Redacted {redaction_count} occurrence(s) → {output_path}")
    if redaction_count == 0:
        print("No matches found for specified patterns.")


def action_strip_metadata(input_path: Path, output_path: Path) -> None:
    try:
        import pypdf
    except ImportError:
        print("Error: pypdf required. Run: pip install pypdf", file=sys.stderr)
        sys.exit(1)

    reader = pypdf.PdfReader(str(input_path))
    writer = pypdf.PdfWriter()
    writer.append(reader)
    writer.add_metadata({})
    with open(output_path, "wb") as fh:
        writer.write(fh)
    print(f"Metadata stripped → {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="PDF security operations.")
    parser.add_argument("--action", required=True,
                        choices=["encrypt", "decrypt", "redact", "strip-metadata"])
    parser.add_argument("--input", required=True, help="Input PDF path")
    parser.add_argument("--output", required=True, help="Output PDF path")

    # Encrypt
    parser.add_argument("--user-password", default="", help="User (read) password")
    parser.add_argument("--owner-password", default="", help="Owner (admin) password")

    # Decrypt
    parser.add_argument("--password", help="Password for decryption")

    # Redact
    parser.add_argument("--patterns", nargs="+",
                        choices=list(BUILTIN_PATTERNS.keys()),
                        help="Built-in pattern names to redact")
    parser.add_argument("--custom-pattern", nargs="+", dest="custom_patterns", default=[],
                        help="Custom regex patterns to redact")

    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    if not input_path.exists():
        print(f"Error: file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    if args.action == "encrypt":
        action_encrypt(input_path, output_path, args.user_password, args.owner_password)
    elif args.action == "decrypt":
        if not args.password:
            parser.error("--password required for decrypt")
        action_decrypt(input_path, output_path, args.password)
    elif args.action == "redact":
        action_redact(input_path, output_path,
                      args.patterns or [], args.custom_patterns)
    elif args.action == "strip-metadata":
        action_strip_metadata(input_path, output_path)


if __name__ == "__main__":
    main()
