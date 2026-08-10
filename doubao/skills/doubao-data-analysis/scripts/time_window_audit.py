#!/usr/bin/env python3
"""Read source CSV/XLSX time columns and classify their interval semantics.

The audit is derived from source rows rather than a model-authored interval
list. Only the Python standard library is required.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import zipfile
from datetime import date, datetime, timedelta
from pathlib import Path
from xml.etree import ElementTree as ET


NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
REL_NS = {"r": "http://schemas.openxmlformats.org/package/2006/relationships"}
RID = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"


def _column_number(ref: str) -> int:
    letters = re.match(r"[A-Z]+", ref.upper())
    if not letters:
        raise ValueError(f"非法单元格引用: {ref}")
    value = 0
    for char in letters.group(0):
        value = value * 26 + ord(char) - 64
    return value


def _xlsx_rows(path: Path, sheet_name: str) -> list[dict[int, object]]:
    with zipfile.ZipFile(path) as archive:
        shared: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            for item in root.findall("m:si", NS):
                shared.append("".join(node.text or "" for node in item.findall(".//m:t", NS)))

        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        targets = {
            rel.attrib["Id"]: rel.attrib["Target"]
            for rel in rels.findall("r:Relationship", REL_NS)
        }
        sheet_path = ""
        for sheet in workbook.findall("m:sheets/m:sheet", NS):
            if sheet.attrib.get("name") == sheet_name:
                target = targets.get(sheet.attrib.get(RID, ""), "")
                sheet_path = target if target.startswith("xl/") else f"xl/{target.lstrip('/')}"
                break
        if not sheet_path:
            names = [s.attrib.get("name", "") for s in workbook.findall("m:sheets/m:sheet", NS)]
            raise ValueError(f"找不到 sheet={sheet_name!r}；可用 sheet: {names}")

        root = ET.fromstring(archive.read(sheet_path))
        rows: list[dict[int, object]] = []
        for row in root.findall(".//m:sheetData/m:row", NS):
            row_no = int(row.attrib.get("r") or len(rows) + 1)
            while len(rows) < row_no - 1:
                rows.append({})
            values: dict[int, object] = {}
            for cell in row.findall("m:c", NS):
                ref = cell.attrib.get("r", "")
                col = _column_number(ref)
                cell_type = cell.attrib.get("t", "")
                if cell_type == "inlineStr":
                    value: object = "".join(
                        node.text or "" for node in cell.findall(".//m:t", NS)
                    )
                else:
                    node = cell.find("m:v", NS)
                    raw = "" if node is None else node.text or ""
                    if cell_type == "s" and raw:
                        value = shared[int(raw)]
                    elif cell_type in {"str", "e"}:
                        value = raw
                    elif raw == "":
                        value = ""
                    else:
                        try:
                            value = float(raw)
                        except ValueError:
                            value = raw
                values[col] = value
            if len(rows) == row_no - 1:
                rows.append(values)
            else:
                rows[row_no - 1] = values
        return rows


def xlsx_sheet_names(path: Path) -> list[str]:
    with zipfile.ZipFile(path) as archive:
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        return [
            sheet.attrib.get("name", "")
            for sheet in workbook.findall("m:sheets/m:sheet", NS)
        ]


def _csv_rows(path: Path) -> list[dict[int, object]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [
            {idx + 1: value for idx, value in enumerate(row)}
            for row in csv.reader(handle)
        ]


def _as_date(value: object) -> date:
    if isinstance(value, (int, float)):
        return date(1899, 12, 30) + timedelta(days=int(value))
    text = str(value or "").strip()
    if not text:
        raise ValueError("日期为空")
    for candidate in (text, text[:10]):
        try:
            return date.fromisoformat(candidate)
        except ValueError:
            pass
    for pattern in ("%Y/%m/%d", "%Y年%m月%d日", "%m/%d/%Y"):
        try:
            return datetime.strptime(text, pattern).date()
        except ValueError:
            pass
    raise ValueError(f"无法解析日期: {text!r}")


def derive_type(intervals: list[tuple[date, date]]) -> str:
    unique = sorted(set(intervals))
    if not unique:
        return "unknown"
    if all(start == end for start, end in unique):
        return "point_events"
    overlaps = any(
        max(left[0], right[0]) <= min(left[1], right[1])
        for idx, left in enumerate(unique)
        for right in unique[idx + 1 :]
    )
    if not overlaps:
        return "non_overlapping_periods"
    starts = {start for start, _ in unique}
    nested = all(
        (left[0] <= right[0] and left[1] >= right[1])
        or (right[0] <= left[0] and right[1] >= left[1])
        for idx, left in enumerate(unique)
        for right in unique[idx + 1 :]
    )
    if len(starts) == 1 or nested:
        return "cumulative_snapshots"
    return "overlapping_periods"


def audit_source(
    source: Path,
    sheet: str,
    header_row: int,
    start_column: str,
    end_column: str,
) -> dict:
    suffix = source.suffix.lower()
    if suffix == ".xlsx":
        rows = _xlsx_rows(source, sheet)
    elif suffix == ".csv":
        rows = _csv_rows(source)
    else:
        raise ValueError("time_window_audit 仅直接支持 .xlsx/.csv；旧格式先无损转换")
    if header_row < 1 or header_row > len(rows):
        raise ValueError("header_row 超出有效范围")

    header = {
        str(value).strip(): col
        for col, value in rows[header_row - 1].items()
        if str(value).strip()
    }
    if start_column not in header or end_column not in header:
        raise ValueError(
            f"找不到时间列；start={start_column!r}, end={end_column!r}, "
            f"实际表头={sorted(header)}"
        )
    start_col, end_col = header[start_column], header[end_column]

    evidence: list[dict] = []
    intervals: list[tuple[date, date]] = []
    for row_no, row in enumerate(rows[header_row:], start=header_row + 1):
        raw_start, raw_end = row.get(start_col, ""), row.get(end_col, "")
        if str(raw_start).strip() == "" and str(raw_end).strip() == "":
            continue
        start, end = _as_date(raw_start), _as_date(raw_end)
        if start > end:
            raise ValueError(f"row {row_no}: start 晚于 end")
        intervals.append((start, end))
        evidence.append({"row": row_no, "start": start.isoformat(), "end": end.isoformat()})

    if not intervals:
        raise ValueError("指定时间列没有有效记录")
    return {
        "generated_by": "time_window_audit.py",
        "source_path": str(source.resolve()),
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "sheet": sheet,
        "header_row": header_row,
        "start_column": start_column,
        "end_column": end_column,
        "record_count": len(intervals),
        "derived_type": derive_type(intervals),
        "intervals": evidence,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("--sheet", default="Sheet1")
    parser.add_argument("--header-row", type=int, default=1)
    parser.add_argument("--start-column", required=True)
    parser.add_argument("--end-column", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()
    try:
        result = audit_source(
            Path(args.source),
            args.sheet,
            args.header_row,
            args.start_column,
            args.end_column,
        )
    except Exception as exc:
        print(f"FAIL\n- {exc}")
        return 1
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
