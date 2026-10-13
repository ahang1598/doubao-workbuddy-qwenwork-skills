#!/usr/bin/env python3
"""Validate a student profile used by college-growth-roadmap-cn."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, TextIO

from privacy_utils import sanitize


VALID_STAGES = {"大一", "大二", "大三", "大四", "大五", "研一", "研二", "研三", "博士", "其他"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="检查学生画像 JSON 是否足以生成从当前学期到毕业的路线图。"
    )
    parser.add_argument(
        "input",
        nargs="?",
        default="-",
        help="画像 JSON 路径；默认 '-'，表示从标准输入读取。",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--strict",
        dest="strict",
        action="store_true",
        help="存在缺失字段或警告时退出 1。",
    )
    mode.add_argument(
        "--allow-partial",
        dest="strict",
        action="store_false",
        help="允许信息不全的探索版画像通过（默认）。",
    )
    parser.set_defaults(strict=False)
    parser.add_argument("--compact", action="store_true", help="输出单行 JSON；默认缩进两格。")
    return parser


def load_json(input_name: str, stdin: TextIO) -> Any:
    if input_name == "-":
        return json.load(stdin)
    with Path(input_name).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def nonempty_strings(
    value: Any, field: str, errors: list[str], *, allow_empty: bool = False
) -> list[str]:
    if value == [] and allow_empty:
        return []
    if isinstance(value, str):
        values = [value]
    elif isinstance(value, list) and all(isinstance(item, str) for item in value):
        values = value
    else:
        errors.append(f"{field} must be a string or a list of strings")
        return []
    if any(not item.strip() for item in values):
        errors.append(f"{field} must not contain empty strings")
    return [item.strip() for item in values if item.strip()]


def validate(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        return {"status": "invalid", "errors": ["root must be an object"], "missing": [], "warnings": []}

    errors: list[str] = []
    missing: list[str] = []
    warnings: list[str] = []

    for field in ("school", "major", "education_level"):
        value = data.get(field)
        if not isinstance(value, str) or not value.strip():
            missing.append(field)

    if not (data.get("current_stage") or data.get("graduation_year")):
        missing.append("current_stage_or_graduation_year")

    stage = data.get("current_stage")
    if stage is not None and not isinstance(stage, str):
        errors.append("current_stage must be a string")
    elif stage and stage not in VALID_STAGES:
        warnings.append("current_stage 非标准值，请人工确认")

    graduation_year = data.get("graduation_year")
    if graduation_year is not None and not isinstance(graduation_year, (int, str)):
        errors.append("graduation_year must be an integer or string")
    elif isinstance(graduation_year, bool):
        errors.append("graduation_year must not be a boolean")
    elif isinstance(graduation_year, int) and not 2000 <= graduation_year <= 2200:
        errors.append("graduation_year integer must be between 2000 and 2200")
    elif isinstance(graduation_year, str) and not re.fullmatch(r"\d{4}", graduation_year.strip()):
        errors.append("graduation_year string must be a four-digit year")
    elif isinstance(graduation_year, str) and not 2000 <= int(graduation_year) <= 2200:
        errors.append("graduation_year string must be between 2000 and 2200")

    goals = data.get("target_paths", [])
    goals = nonempty_strings(goals, "target_paths", errors, allow_empty=True)
    if not goals:
        warnings.append("target_paths 未提供：只能生成探索版路线图")

    cities = data.get("target_cities", [])
    cities = nonempty_strings(cities, "target_cities", errors, allow_empty=True)

    wants_city_policy = any(
        keyword in goal for goal in goals for keyword in ("落户", "人才引进", "城市")
    )
    if wants_city_policy and not cities:
        missing.append("target_cities")

    status = "invalid" if errors else ("partial" if missing or warnings else "ready")
    return {"status": status, "errors": errors, "missing": missing, "warnings": warnings}


def emit(payload: dict[str, Any], compact: bool) -> None:
    print(json.dumps(sanitize(payload), ensure_ascii=False, indent=None if compact else 2))


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        data = load_json(args.input, sys.stdin)
    except (OSError, json.JSONDecodeError) as exc:
        emit({"status": "invalid", "errors": [str(exc)], "missing": [], "warnings": []}, args.compact)
        return 2

    result = validate(data)
    emit(result, args.compact)
    if result["status"] == "invalid":
        return 2
    if args.strict and result["status"] != "ready":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
