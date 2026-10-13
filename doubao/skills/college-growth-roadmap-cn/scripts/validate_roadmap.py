#!/usr/bin/env python3
"""Validate roadmap JSON produced by college-growth-roadmap-cn."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any, TextIO

from privacy_utils import sanitize


VALID_TYPES = {"HARD_GATE", "HIGH_VALUE", "OPTIONAL", "AVOID"}
VALID_STATUS = {"已核验", "历史参考", "待核验", "不适用"}
VALID_DEADLINE_TYPES = {"官方截止", "建议准备", "历史参考", "待核验"}
CORE_FIELDS = ("time", "node", "type", "why", "action", "verification_status")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="检查路线图 JSON 的节点、证据和时间字段。")
    parser.add_argument(
        "input",
        nargs="?",
        default="-",
        help="路线图 JSON 路径；默认 '-'，表示从标准输入读取。",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--strict",
        dest="strict",
        action="store_true",
        help="把草案警告视为未通过，用于交付前校验。",
    )
    mode.add_argument(
        "--allow-draft",
        dest="strict",
        action="store_false",
        help="允许带待核验项的结构化草案通过（默认）。",
    )
    parser.set_defaults(strict=False)
    parser.add_argument("--compact", action="store_true", help="输出单行 JSON；默认缩进两格。")
    return parser


def load_json(input_name: str, stdin: TextIO) -> Any:
    if input_name == "-":
        return json.load(stdin)
    with Path(input_name).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def is_iso_date(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        dt.date.fromisoformat(value)
    except ValueError:
        return False
    return True


def validate(data: Any, strict: bool) -> dict[str, Any]:
    if not isinstance(data, dict):
        return {"ok": False, "errors": ["root must be an object"], "warnings": []}

    nodes = data.get("nodes")
    if not isinstance(nodes, list):
        return {"ok": False, "errors": ["nodes must be a list"], "warnings": []}
    if not nodes:
        return {"ok": False, "errors": ["nodes must not be empty"], "warnings": []}

    errors: list[str] = []
    warnings: list[str] = []
    for index, item in enumerate(nodes):
        path = f"nodes[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{path}: must be an object")
            continue

        for field in CORE_FIELDS:
            if item.get(field) in (None, ""):
                errors.append(f"{path}.{field}: missing")
            elif field in {"time", "node", "why", "action"} and not isinstance(item[field], str):
                errors.append(f"{path}.{field}: expected string")

        node_type = item.get("type")
        if node_type not in VALID_TYPES:
            errors.append(f"{path}.type: invalid")

        status = item.get("verification_status")
        if status not in (None, "") and status not in VALID_STATUS:
            errors.append(f"{path}.verification_status: invalid")

        if node_type == "HARD_GATE":
            if not status:
                errors.append(f"{path}: HARD_GATE has no verification_status; use 待核验 when unknown")
            elif status in {"待核验", "历史参考"}:
                warnings.append(f"{path}: HARD_GATE is not currently verified")
            elif status == "已核验":
                for field in ("official_source", "applicable_cohort", "last_checked"):
                    if not isinstance(item.get(field), str) or not item[field].strip():
                        errors.append(f"{path}: verified HARD_GATE missing {field}")
                if item.get("last_checked") and not is_iso_date(item["last_checked"]):
                    errors.append(f"{path}.last_checked: expected YYYY-MM-DD")

        deadline = item.get("deadline")
        deadline_type = item.get("deadline_type")
        if deadline and not deadline_type:
            errors.append(f"{path}: deadline requires deadline_type")
        if deadline_type and deadline_type not in VALID_DEADLINE_TYPES:
            errors.append(f"{path}.deadline_type: invalid")
        if deadline and deadline_type in {"官方截止", "历史参考"} and not is_iso_date(deadline):
            errors.append(f"{path}.deadline: expected YYYY-MM-DD for {deadline_type}")

    ok = not errors and (not strict or not warnings)
    return {"ok": ok, "errors": errors, "warnings": warnings}


def emit(payload: dict[str, Any], compact: bool) -> None:
    print(json.dumps(sanitize(payload), ensure_ascii=False, indent=None if compact else 2))


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        data = load_json(args.input, sys.stdin)
    except (OSError, json.JSONDecodeError) as exc:
        emit({"ok": False, "errors": [str(exc)], "warnings": []}, args.compact)
        return 2

    result = validate(data, args.strict)
    emit(result, args.compact)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
