#!/usr/bin/env python3
"""Profile a DWS AI-table JSON snapshot without third-party dependencies."""

from __future__ import annotations

import argparse
import json
import math
import re
import statistics
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


def load_json(path: str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def find_list(payload: Any, preferred: tuple[str, ...]) -> list:
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []
    for key in preferred:
        value = payload.get(key)
        if isinstance(value, list):
            return value
    data = payload.get("data")
    if isinstance(data, dict):
        return find_list(data, preferred)
    return []


def normalize_fields(payload: Any) -> list[dict]:
    rows = find_list(payload, ("fields", "items"))
    result = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        field_id = row.get("fieldId") or row.get("id") or row.get("field_id")
        name = row.get("fieldName") or row.get("name") or field_id
        result.append(
            {
                "field_id": field_id,
                "name": name,
                "type": row.get("type") or row.get("fieldType"),
                "config": row.get("config") or {},
            }
        )
    return result


def normalize_records(payload: Any) -> list[dict]:
    rows = find_list(payload, ("records", "items", "rows"))
    result = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        cells = row.get("cells") if isinstance(row.get("cells"), dict) else row
        result.append(
            {
                "record_id": row.get("recordId") or row.get("id") or row.get("rowId"),
                "cells": cells,
            }
        )
    return result


def empty(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {}


def scalar(value: Any) -> Any:
    if isinstance(value, dict):
        for key in ("text", "name", "value", "displayValue"):
            if key in value and not isinstance(value[key], (dict, list)):
                return value[key]
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    if isinstance(value, list):
        return " | ".join(str(scalar(item)) for item in value)
    return value


def parse_number(value: Any) -> float | None:
    value = scalar(value)
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        return float(value)
    if isinstance(value, str):
        text = value.strip().replace(",", "").rstrip("%")
        try:
            number = float(text)
            return number if math.isfinite(number) else None
        except ValueError:
            return None
    return None


def parse_date(value: Any) -> datetime | None:
    value = scalar(value)
    if not isinstance(value, str):
        return None
    text = value.strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y-%m", "%Y/%m"):
            try:
                return datetime.strptime(text, fmt)
            except ValueError:
                pass
    return None


def infer_type(values: list[Any], declared: Any) -> str:
    if declared:
        return str(declared)
    sample = [value for value in values if not empty(value)][:100]
    if not sample:
        return "empty"
    numeric = sum(parse_number(value) is not None for value in sample)
    dated = sum(parse_date(value) is not None for value in sample)
    if numeric / len(sample) >= 0.9:
        return "number"
    if dated / len(sample) >= 0.9:
        return "date"
    if any(isinstance(value, list) for value in sample):
        return "list"
    if any(isinstance(value, dict) for value in sample):
        return "object"
    return "text"


def profile_field(field: dict, values: list[Any], total: int) -> dict:
    present = [value for value in values if not empty(value)]
    normalized = [str(scalar(value)) for value in present]
    counts = Counter(normalized)
    numbers = [number for value in present if (number := parse_number(value)) is not None]
    dates = [date for value in present if (date := parse_date(value)) is not None]
    result = {
        "field_id": field["field_id"],
        "name": field["name"],
        "declared_type": field["type"],
        "inferred_type": infer_type(present, field["type"]),
        "non_null_count": len(present),
        "missing_count": total - len(present),
        "missing_rate": round((total - len(present)) / total, 6) if total else 0,
        "unique_count": len(counts),
        "duplicate_value_count": sum(count - 1 for count in counts.values() if count > 1),
        "is_unique_non_null": bool(present) and len(counts) == len(present),
        "top_values": [{"value": value, "count": count} for value, count in counts.most_common(10)],
        "sample_values": list(dict.fromkeys(normalized))[:5],
    }
    if numbers and len(numbers) / max(1, len(present)) >= 0.8:
        result["numeric"] = {
            "min": min(numbers),
            "max": max(numbers),
            "mean": round(statistics.fmean(numbers), 6),
            "median": statistics.median(numbers),
        }
    if dates and len(dates) / max(1, len(present)) >= 0.8:
        result["date"] = {
            "min": min(dates).isoformat(),
            "max": max(dates).isoformat(),
        }
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--records", required=True)
    parser.add_argument("--fields")
    parser.add_argument("--output")
    args = parser.parse_args()

    records = normalize_records(load_json(args.records))
    fields = normalize_fields(load_json(args.fields)) if args.fields else []
    field_map = {field["field_id"]: field for field in fields if field["field_id"]}
    all_keys = sorted({key for record in records for key in record["cells"].keys()})
    for key in all_keys:
        field_map.setdefault(key, {"field_id": key, "name": key, "type": None, "config": {}})

    profiles = [
        profile_field(field_map[key], [record["cells"].get(key) for record in records], len(records))
        for key in all_keys
    ]
    semantic_key = re.compile(r"(^id$|_id$|编号|编码|工号|单号|主键|唯一标识|唯一ID|key$)", re.I)
    profile = {
        "generated_at": datetime.now().astimezone().isoformat(),
        "record_count": len(records),
        "records_with_id": sum(bool(record["record_id"]) for record in records),
        "field_count": len(field_map),
        "fields": profiles,
        "unique_fields": [field["name"] for field in profiles if field["is_unique_non_null"]],
        "candidate_keys": [
            field["name"]
            for field in profiles
            if field["is_unique_non_null"] and semantic_key.search(field["name"])
        ],
    }
    text = json.dumps(profile, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)


if __name__ == "__main__":
    main()
