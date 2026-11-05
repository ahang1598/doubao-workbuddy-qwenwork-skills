#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT
"""Decode chart-list thumbnail JSON into image files.

Pipe the JSON output of ``+chart-list --only-thumbnail`` to stdin. The script
never prints base64 data; it emits a compact manifest containing only statuses,
chart IDs, image metadata, paths, and error LogIDs.
"""

from __future__ import annotations

import argparse
import base64
import re
import binascii
import json
import sys
from pathlib import Path
from typing import Any

from lark_sheet_read_cli import LarkCliError, run_sheets


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def image_format(raw: bytes) -> str:
    """Identify the filename suffix without inspecting rendered content."""
    if raw.startswith(PNG_SIGNATURE):
        return "png"
    if raw.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if raw.startswith(b"RIFF") and raw[8:12] == b"WEBP":
        return "webp"
    return "unknown"


def safe_thumbnail_name(value: Any) -> str:
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", str(value)).strip("._")
    return name or "chart"


def thumbnail_file_suffix(inspection: dict[str, Any]) -> str:
    return {"png": ".png", "jpeg": ".jpg", "webp": ".webp"}.get(
        str(inspection.get("format") or ""), ".bin"
    )


def decode_thumbnail_base64(encoded: str) -> bytes:
    value = encoded.strip()
    if value.startswith("data:"):
        _, separator, value = value.partition(",")
        if not separator:
            raise ValueError("invalid data URI")
    return base64.b64decode("".join(value.split()), validate=True)


def error_log_ids(value: Any) -> list[str]:
    found: set[str] = set()

    def visit(item: Any, key: str = "") -> None:
        if key == "base64":
            return
        if isinstance(item, dict):
            for child_key, child in item.items():
                visit(child, str(child_key))
        elif isinstance(item, (list, tuple)):
            for child in item:
                visit(child)
        else:
            found.update(re.findall(r"20\d{12}[A-Fa-f0-9]{12,40}", str(item)))

    visit(value)
    return sorted(found)

ACTION = "chart_thumbnail_decode"


def _log_ids(value: Any) -> list[str]:
    return error_log_ids(value)


def _charts(payload: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    rows: list[tuple[str, dict[str, Any]]] = []
    sheets = data.get("sheets") if isinstance(data, dict) else None
    if isinstance(sheets, list):
        for sheet in sheets:
            if not isinstance(sheet, dict):
                continue
            sheet_id = str(sheet.get("sheet_id") or sheet.get("id") or "sheet")
            for chart in sheet.get("charts", []):
                if isinstance(chart, dict):
                    rows.append((sheet_id, chart))
    elif isinstance(data, dict):
        for chart in data.get("charts", []):
            if isinstance(chart, dict):
                rows.append(("sheet", chart))
    return rows


def decode_payload(
    payload: dict[str, Any],
    *,
    output_dir: Path,
    expected_chart_ids: list[str] | None = None,
) -> dict[str, Any]:
    if payload.get("ok") is False:
        return {
            "ok": False,
            "engine": "lark",
            "action": ACTION,
            "result_type": "execution_error",
            "next_action": "retry_or_report",
            "error": payload.get("error") or "chart-list returned ok=false",
            "data": {"error_log_ids": _log_ids(payload)},
        }

    output_dir.mkdir(parents=True, exist_ok=True)
    expected = list(dict.fromkeys(str(value) for value in (expected_chart_ids or []) if value))
    received: list[str] = []
    valid: list[str] = []
    files: list[dict[str, Any]] = []
    for sheet_id, chart in _charts(payload):
        chart_id = str(chart.get("chart_id") or chart.get("id") or "")
        if not chart_id:
            continue
        received.append(chart_id)
        details = chart.get("details") if isinstance(chart.get("details"), dict) else chart
        thumbnail = details.get("thumbnail") if isinstance(details.get("thumbnail"), dict) else {}
        mime_type = str(thumbnail.get("mime_type") or thumbnail.get("mime") or "")
        encoded = thumbnail.get("base64")
        item: dict[str, Any] = {
            "chart_id": chart_id,
            "mime_type": mime_type,
            "version": str(thumbnail.get("version") or ""),
            "reported_width": thumbnail.get("width"),
            "reported_height": thumbnail.get("height"),
        }
        if not isinstance(encoded, str) or not encoded.strip():
            item.update({"status": "empty", "reason": "thumbnail.base64 is empty"})
            files.append(item)
            continue
        try:
            raw = decode_thumbnail_base64(encoded)
            inspection = {"format": image_format(raw)}
        except (binascii.Error, ValueError) as exc:
            item.update({"status": "invalid", "reason": str(exc)})
            files.append(item)
            continue
        suffix = thumbnail_file_suffix(inspection)
        path = output_dir / (
            f"{safe_thumbnail_name(sheet_id)}_{safe_thumbnail_name(chart_id)}{suffix}"
        )
        path.write_bytes(raw)
        status = "decoded"
        item.update({"status": status, "path": str(path.resolve()), "bytes": len(raw), **inspection})
        files.append(item)
        if status == "decoded":
            valid.append(chart_id)

    received = list(dict.fromkeys(received))
    valid = list(dict.fromkeys(valid))
    if not expected:
        expected = received.copy()
    missing = [chart_id for chart_id in expected if chart_id not in received]
    unavailable = [chart_id for chart_id in expected if chart_id not in valid]
    valid_expected = [chart_id for chart_id in expected if chart_id in valid]
    coverage = {
        "valid": len(valid_expected),
        "expected": len(expected),
        "rate": len(valid_expected) / len(expected) if expected else None,
    }
    images = [
        {"chart_id": str(item["chart_id"]), "path": str(item["path"])}
        for item in files
        if item.get("status") == "decoded" and item.get("chart_id") in expected
    ]
    assets_ready = not unavailable and bool(expected)
    result_type = "decoded" if assets_ready else "thumbnail_unavailable"
    result = {
        "ok": True,
        "engine": "lark",
        "action": ACTION,
        "result_type": result_type,
        "next_action": "use_images" if assets_ready else "retry_thumbnail_or_report",
        "data": {
            "expected_chart_ids": expected,
            "received_chart_ids": received,
            "valid_chart_ids": valid_expected,
            "missing_chart_ids": missing,
            "unavailable_chart_ids": unavailable,
            "coverage": coverage,
            "files": files,
            "images": images,
            "error_log_ids": _log_ids(payload),
        },
    }
    manifest_path = output_dir / "thumbnail_manifest.json"
    result["data"]["manifest_path"] = str(manifest_path.resolve())
    manifest_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Decode chart-list thumbnail JSON without printing base64 data."
    )
    parser.add_argument("--input", help="JSON file; defaults to stdin")
    parser.add_argument("--output-dir", required=True, help="Directory for decoded images and manifest")
    target = parser.add_mutually_exclusive_group()
    target.add_argument("--url", help="Fetch directly from this spreadsheet URL")
    target.add_argument("--spreadsheet-token", help="Fetch directly from this spreadsheet token")
    sheet = parser.add_mutually_exclusive_group()
    sheet.add_argument("--sheet-id", help="Worksheet reference_id for direct fetch")
    sheet.add_argument("--sheet-name", help="Worksheet name for direct fetch")
    parser.add_argument("--chart-id", help="Single chart_id for direct fetch")
    parser.add_argument(
        "--expected-chart-id",
        action="append",
        default=[],
        help="Expected chart_id; repeat for multiple charts",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        direct_fetch = bool(args.url or args.spreadsheet_token)
        if direct_fetch:
            if args.input:
                raise ValueError("--input cannot be combined with direct-fetch flags")
            if not (args.sheet_id or args.sheet_name) or not args.chart_id:
                raise ValueError("direct fetch requires a worksheet locator and --chart-id")
            payload = run_sheets(
                "+chart-list",
                url=args.url,
                spreadsheet_token=args.spreadsheet_token,
                sheet_id=args.sheet_id,
                sheet_name=args.sheet_name,
                flags={"chart_id": args.chart_id, "only_thumbnail": True},
            )
        else:
            source = Path(args.input).read_text(encoding="utf-8") if args.input else sys.stdin.read()
            payload = json.loads(source)
            if not isinstance(payload, dict):
                raise ValueError("input JSON must be an object")
        expected = list(args.expected_chart_id)
        if args.chart_id and args.chart_id not in expected:
            expected.append(args.chart_id)
        result = decode_payload(
            payload,
            output_dir=Path(args.output_dir).expanduser().resolve(),
            expected_chart_ids=expected,
        )
    except (LarkCliError, OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        result = {
            "ok": False,
            "engine": "lark",
            "action": ACTION,
            "result_type": "execution_error",
            "next_action": "retry_or_report",
            "error": str(exc),
            "data": {"error_log_ids": _log_ids(str(exc))},
        }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result.get("result_type") != "decoded":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
