#!/usr/bin/env python3
"""Verify that every text run in a generated DOCX has an East Asian font."""
from __future__ import annotations

import sys
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W_NS}


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: font_check.py <contract.docx>")
    path = Path(sys.argv[1])
    with ZipFile(path) as archive:
        document = ET.fromstring(archive.read("word/document.xml"))
        names = archive.namelist()
    missing = 0
    for run in document.findall(".//w:r", NS):
        text = "".join(node.text or "" for node in run.findall(".//w:t", NS)).strip()
        if not text:
            continue
        fonts = run.find("w:rPr/w:rFonts", NS)
        east_asia = fonts.get(f"{{{W_NS}}}eastAsia") if fonts is not None else None
        if east_asia not in {"宋体", "黑体"}:
            missing += 1
    if missing or any("comments" in name for name in names):
        print("FONT CHECK FAILED")
        if missing:
            print(f"- {missing} 个文字 run 未指定东亚字体")
        if any("comments" in name for name in names):
            print("- 文档包含批注部件")
        raise SystemExit(1)
    print("Font check passed.")


if __name__ == "__main__":
    main()
