#!/usr/bin/env python3
"""Normalize PandaAI fields from XLSX, TXT/CSV, JSON, direct input, or defaults."""

from __future__ import annotations

import argparse
import csv
import json
import re
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET


DEFAULT_FIELDS = (
    {"name": "CLOSE", "type": "double", "description": "收盘价", "category": "market"},
    {"name": "OPEN", "type": "double", "description": "开盘价", "category": "market"},
    {"name": "HIGH", "type": "double", "description": "最高价", "category": "market"},
    {"name": "LOW", "type": "double", "description": "最低价", "category": "market"},
    {"name": "VOLUME", "type": "double", "description": "成交量", "category": "market"},
    {"name": "AMOUNT", "type": "double", "description": "成交额", "category": "market"},
    {"name": "TURNOVER", "type": "double", "description": "换手率", "category": "market"},
    {"name": "MARKET_CAP", "type": "double", "description": "总市值", "category": "market"},
)
NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
HEADER_NAMES = {"字段", "字段名", "field", "name", "code", "factor"}


def _col_index(ref: str) -> int:
    letters = "".join(ch for ch in ref if ch.isalpha()).upper()
    value = 0
    for ch in letters:
        value = value * 26 + ord(ch) - 64
    return value - 1


def read_xlsx(path: Path) -> list[dict[str, str]]:
    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
          "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
          "p": "http://schemas.openxmlformats.org/package/2006/relationships"}
    with zipfile.ZipFile(path) as archive:
        shared: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            for item in root.findall("m:si", ns):
                shared.append("".join(t.text or "" for t in item.iterfind(".//m:t", ns)))
        wb = ET.fromstring(archive.read("xl/workbook.xml"))
        rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        targets = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rels.findall("p:Relationship", ns)}
        output: list[dict[str, str]] = []
        for sheet in wb.findall("m:sheets/m:sheet", ns):
            category = sheet.attrib["name"]
            target = targets[sheet.attrib[f"{{{ns['r']}}}id"]].lstrip("/")
            xml_path = target if target.startswith("xl/") else f"xl/{target}"
            root = ET.fromstring(archive.read(xml_path))
            rows: list[list[str]] = []
            for row in root.findall(".//m:sheetData/m:row", ns):
                values: dict[int, str] = {}
                for cell in row.findall("m:c", ns):
                    ref, kind = cell.attrib.get("r", "A1"), cell.attrib.get("t")
                    value_node = cell.find("m:v", ns)
                    inline = cell.find("m:is/m:t", ns)
                    value = inline.text if inline is not None else (value_node.text if value_node is not None else "")
                    if kind == "s" and value:
                        value = shared[int(value)]
                    values[_col_index(ref)] = value or ""
                if values:
                    rows.append([values.get(i, "") for i in range(max(values) + 1)])
            if not rows:
                continue
            header = [str(x).strip().lower() for x in rows[0]]
            name_col = next((i for i, x in enumerate(header) if x in HEADER_NAMES), 0)
            type_col = next((i for i, x in enumerate(header) if x in {"类型", "type", "dtype"}), None)
            desc_col = next((i for i, x in enumerate(header) if x in {"描述", "说明", "description", "desc"}), None)
            for row in rows[1:]:
                name = row[name_col].strip() if name_col < len(row) else ""
                if not NAME_RE.fullmatch(name):
                    continue
                output.append({"name": name,
                               "type": row[type_col].strip() if type_col is not None and type_col < len(row) else "unknown",
                               "description": row[desc_col].strip() if desc_col is not None and desc_col < len(row) else "",
                               "category": category, "source": str(path)})
        return output


def read_text(path: Path) -> list[dict[str, str]]:
    text = path.read_text(encoding="utf-8-sig")
    delimiter = "\t" if "\t" in text.splitlines()[0] else ("," if "," in text.splitlines()[0] else None)
    if delimiter:
        rows = list(csv.reader(text.splitlines(), delimiter=delimiter))
        header = [x.strip().lower() for x in rows[0]]
        start = 1 if any(x in HEADER_NAMES for x in header) else 0
        name_col = next((i for i, x in enumerate(header) if x in HEADER_NAMES), 0)
        return [{"name": row[name_col].strip(), "type": row[1].strip() if len(row) > 1 else "unknown",
                 "description": row[2].strip() if len(row) > 2 else "", "category": path.stem,
                 "source": str(path)} for row in rows[start:] if len(row) > name_col and NAME_RE.fullmatch(row[name_col].strip())]
    return [{"name": line.strip(), "type": "unknown", "description": "", "category": path.stem,
             "source": str(path)} for line in text.splitlines() if NAME_RE.fullmatch(line.strip())]


def read_source(path: Path) -> list[dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix == ".xlsx":
        return read_xlsx(path)
    if suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        return data.get("fields", data) if isinstance(data, dict) else data
    if suffix in {".txt", ".csv", ".tsv"}:
        return read_text(path)
    raise ValueError(f"unsupported field source: {path}")


def normalize(fields: list[dict[str, Any]], expand_mrq: bool = False) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in fields:
        name = str(raw.get("name", "")).strip()
        if not NAME_RE.fullmatch(name) or name.lower() in {"symbol", "date"}:
            continue
        key = name.lower()
        if key not in seen:
            result.append({"name": name, "type": str(raw.get("type", "unknown")),
                           "description": str(raw.get("description", "")),
                           "category": str(raw.get("category", "uncategorized")),
                           "source": str(raw.get("source", "direct"))})
            seen.add(key)
        if expand_mrq and name.lower().startswith(("cfs_", "bs_", "is_")) and "_mrq_" not in key:
            for n in range(1, 13):
                derived = f"{name}_mrq_{n}"
                if derived.lower() not in seen:
                    result.append({"name": derived, "type": str(raw.get("type", "unknown")),
                                   "description": f"{raw.get('description', '')} 最近前第{n}期",
                                   "category": str(raw.get("category", "uncategorized")),
                                   "source": str(raw.get("source", "direct")), "derived": True})
                    seen.add(derived.lower())
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a normalized PandaAI field catalog")
    parser.add_argument("--input", type=Path, action="append", default=[])
    parser.add_argument("--fields", help="Comma-separated direct field names")
    parser.add_argument("--pure-blind", action="store_true", help="Use documented default market fields")
    parser.add_argument("--expand-mrq", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    raw: list[dict[str, Any]] = []
    for path in args.input:
        raw.extend(read_source(path))
    if args.fields:
        raw.extend({"name": name.strip(), "category": "direct", "source": "direct"}
                   for name in args.fields.split(","))
    if args.pure_blind or not raw:
        raw.extend(DEFAULT_FIELDS)
    fields = normalize(raw, args.expand_mrq)
    payload = {"schema_version": 1, "count": len(fields), "fields": fields}
    rendered = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
