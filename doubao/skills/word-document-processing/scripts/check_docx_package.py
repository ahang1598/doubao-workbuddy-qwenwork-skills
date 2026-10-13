#!/usr/bin/env python3
import sys
import zipfile
from pathlib import Path

REQUIRED = ["[Content_Types].xml", "_rels/.rels", "word/document.xml"]


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: check_docx_package.py FILE.docx")
        return 2
    path = Path(sys.argv[1])
    if not path.exists():
        print(f"FAIL: missing file: {path}")
        return 1
    if path.suffix.lower() != ".docx":
        print(f"FAIL: not a .docx path: {path}")
        return 1
    if not zipfile.is_zipfile(path):
        print("FAIL: .docx is not a ZIP/OpenXML package")
        return 1
    with zipfile.ZipFile(path) as zf:
        names = set(zf.namelist())
        missing = [name for name in REQUIRED if name not in names]
        if missing:
            print("FAIL: missing required entries: " + ", ".join(missing))
            return 1
        document = zf.read("word/document.xml")
        if b"<w:body" not in document:
            print("FAIL: word/document.xml has no w:body")
            return 1
    print("PASS: valid DOCX package structure")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
