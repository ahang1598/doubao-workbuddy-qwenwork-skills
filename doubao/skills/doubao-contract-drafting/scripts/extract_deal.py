#!/usr/bin/env python3
"""Extract paragraphs and tables from DOCX, Markdown, text, or JSON inputs."""
from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def docx_blocks(path: Path) -> list[dict]:
    with zipfile.ZipFile(path) as archive:
        root = ET.fromstring(archive.read("word/document.xml"))
    body = root.find(f"{W}body")
    blocks: list[dict] = []
    for child in ([] if body is None else list(body)):
        if child.tag == f"{W}p":
            text = "".join(node.text or "" for node in child.iter(f"{W}t")).strip()
            if text:
                blocks.append({"type": "paragraph", "text": text})
        elif child.tag == f"{W}tbl":
            rows = []
            for tr in child.findall(f"{W}tr"):
                rows.append(["".join(node.text or "" for node in tc.iter(f"{W}t")).strip() for tc in tr.findall(f"{W}tc")])
            blocks.append({"type": "table", "rows": rows})
    return blocks


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("Usage: extract_deal.py <input...>")
    output = []
    for name in sys.argv[1:]:
        path = Path(name)
        if path.suffix.lower() == ".docx":
            blocks = docx_blocks(path)
        elif path.suffix.lower() in {".md", ".txt"}:
            blocks = [{"type": "paragraph", "text": line} for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        else:
            blocks = [{"type": "raw", "text": path.read_text(encoding="utf-8")}]
        output.append({"source": path.name, "blocks": blocks})
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
