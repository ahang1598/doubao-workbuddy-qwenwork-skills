#!/usr/bin/env python3
"""Extract paragraphs and tables from a clean (accepted-revisions) DOCX and
produce a bilingual.json ready for ``build_bilingual_review.py``."""

from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path

from lxml import etree
from skill_paths import generated_path

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W_NS}
W = f"{{{W_NS}}}"


def visible_text(paragraph) -> str:
    values = paragraph.xpath(
        ".//w:t/text() | .//w:tab | .//w:br",
        namespaces=NS,
    )
    parts: list[str] = []
    for value in values:
        if isinstance(value, str):
            parts.append(value)
        elif value.tag == W + "tab":
            parts.append("\t")
        elif value.tag == W + "br":
            parts.append("\n")
    return "".join(parts)


def cell_text(cell) -> str:
    """Visible text of a table cell (all paragraphs concatenated)."""
    paras = cell.xpath("./w:p", namespaces=NS)
    return "\n".join(visible_text(p) for p in paras).strip()


def extract_from_docx(path: Path) -> list[dict]:
    """Walk the document body and yield paragraph / table items."""
    with zipfile.ZipFile(path) as archive:
        root = etree.fromstring(archive.read("word/document.xml"))
    body = root.find(f".//{{{W_NS}}}body")
    if body is None:
        raise ValueError("no w:body found")

    items: list[dict] = []
    clause_num = 0

    for child in body:
        tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag

        if tag == "p":
            text = visible_text(child).strip()
            if text:
                clause_num += 1
                items.append({
                    "number": str(clause_num),
                    "en": text,
                    "zh": "",
                    "kind": "clause",
                })

        elif tag == "tbl":
            rows = child.xpath("./w:tr", namespaces=NS)
            if not rows:
                continue
            # First row = header
            hdr_cells = rows[0].xpath("./w:tc", namespaces=NS)
            headers = [cell_text(c) for c in hdr_cells]

            data_rows: list[dict] = []
            for tr in rows[1:]:
                cells = tr.xpath("./w:tc", namespaces=NS)
                data_rows.append({
                    "cells": [{"en": cell_text(c), "zh": ""} for c in cells]
                })

            items.append({
                "kind": "table",
                "headers": headers,
                "rows": data_rows,
            })

    return items


def apply_translations(items: list[dict], translations: dict) -> None:
    """Fill zh fields from translation data.  Leaves ``【待确认：中文文本】``
    for unmatched text."""
    clause_map = translations.get("clauses", {})
    table_data = translations.get("tables", {})

    for item in items:
        if item.get("kind") == "table":
            # Match table by headers (first table → _table_0, etc.)
            tid = f"_table_{sum(1 for i in items if i.get('kind') == 'table' and i is not item)}"
            tinfo = table_data.get(tid, {})
            hdr_trans = tinfo.get("headers")
            cell_trans = tinfo.get("cells", {})
            if hdr_trans:
                item["headers"] = hdr_trans
            for row in item.get("rows", []):
                for c in row.get("cells", []):
                    c["zh"] = cell_trans.get(c["en"], "【待确认：中文文本】")
        else:
            en = item.get("en", "")
            item["zh"] = clause_map.get(en, "【待确认：中文文本】")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract paragraphs and tables from a clean DOCX → bilingual.json"
    )
    parser.add_argument("input", type=Path, help="Clean (accepted) DOCX")
    parser.add_argument("--translations", type=Path, help="JSON translation map")
    parser.add_argument("--title-en", default="Reviewed Agreement")
    parser.add_argument("--title-zh", default="经审查的协议")
    parser.add_argument("--language-mode", choices=("en_zh", "zh_en"), required=True)
    parser.add_argument("--language-priority-en", required=True)
    parser.add_argument("--language-priority-zh", required=True)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    items = extract_from_docx(args.input)

    translations: dict = {}
    if args.translations and args.translations.exists():
        translations = json.loads(args.translations.read_text(encoding="utf-8"))

    apply_translations(items, translations)

    # Use translation-provided titles if available
    title_en = translations.get("title_en", args.title_en)
    title_zh = translations.get("title_zh", args.title_zh)

    output = {
        "title_en": title_en,
        "title_zh": title_zh,
        "language_mode": args.language_mode,
        "language_priority_en": args.language_priority_en,
        "language_priority_zh": args.language_priority_zh,
        "paragraphs": items,
    }

    output_path = generated_path(args.out, "bilingual JSON")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"created {output_path} ({len(items)} items)")


if __name__ == "__main__":
    main()
