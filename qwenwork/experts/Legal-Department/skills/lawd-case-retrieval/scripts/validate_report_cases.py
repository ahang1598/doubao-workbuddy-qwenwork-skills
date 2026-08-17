#!/usr/bin/env python3
"""Validate canonical JSON input for a legal case retrieval report."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any


PLACEHOLDER_PATTERNS = (
    re.compile(r"\{\{.*?\}\}"),
    re.compile(r"\[(?:待补充|请填写|填写|律师|律所|案件名称)\]"),
    re.compile(r"\b(?:TODO|TBD)\b", re.IGNORECASE),
)


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"输入文件不存在：{path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON 无法解析：第 {exc.lineno} 行第 {exc.colno} 列：{exc.msg}") from exc
    if not isinstance(data, dict):
        raise ValueError("JSON 顶层必须是对象")
    return data


def parse_date(value: Any, field: str, errors: list[str]) -> date | None:
    if value in (None, ""):
        return None
    if not isinstance(value, str):
        errors.append(f"{field} 必须是日期字符串")
        return None
    normalized = value.strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y年%m月%d日"):
        try:
            return datetime.strptime(normalized, fmt).date()
        except ValueError:
            pass
    errors.append(f"{field} 日期无法解析：{value}")
    return None


def walk_strings(value: Any, path: str = "$"):
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, dict):
        for key, child in value.items():
            yield from walk_strings(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from walk_strings(child, f"{path}[{index}]")


def contains_placeholder(text: str) -> bool:
    return any(pattern.search(text) for pattern in PLACEHOLDER_PATTERNS)


def case_identity(case: dict[str, Any]) -> tuple[str, str] | None:
    for field in ("case_id", "case_no", "raw_record_locator"):
        value = str(case.get(field) or "").strip()
        if value:
            return field, value
    return None


def require_type(data: dict[str, Any], key: str, expected: type, errors: list[str]) -> Any:
    value = data.get(key)
    if not isinstance(value, expected):
        errors.append(f"{key} 必须是 {expected.__name__}")
        return expected()
    return value


def validate(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if data.get("schema_version") != "1.0":
        errors.append("schema_version 必须为 1.0")

    require_type(data, "report", dict, errors)
    require_type(data, "retrieval_targets", list, errors)
    require_type(data, "conclusions", list, errors)
    constraints = require_type(data, "explicit_constraints", dict, errors)
    cases = require_type(data, "cases", list, errors)

    if not cases:
        errors.append("cases 至少需要一个案例")

    for key in ("regions", "court_levels", "other"):
        if key in constraints and not isinstance(constraints[key], list):
            errors.append(f"explicit_constraints.{key} 必须是数组")

    date_from = parse_date(constraints.get("date_from"), "explicit_constraints.date_from", errors)
    date_to = parse_date(constraints.get("date_to"), "explicit_constraints.date_to", errors)
    if date_from and date_to and date_from > date_to:
        errors.append("明确时间约束的起始日期晚于结束日期")

    max_cases = constraints.get("max_cases")
    if max_cases not in (None, ""):
        if isinstance(max_cases, bool) or not isinstance(max_cases, int) or max_cases < 1:
            errors.append("explicit_constraints.max_cases 必须是正整数")
        elif len(cases) > max_cases:
            errors.append(f"案例数量 {len(cases)} 超过用户明确上限 {max_cases}")

    regions = [str(item).strip() for item in constraints.get("regions", []) if str(item).strip()]
    court_levels = [str(item).strip() for item in constraints.get("court_levels", []) if str(item).strip()]
    seen_identities: set[tuple[str, str]] = set()
    seen_case_nos: set[str] = set()

    for index, case in enumerate(cases, start=1):
        label = f"cases[{index - 1}]"
        if not isinstance(case, dict):
            errors.append(f"{label} 必须是对象")
            continue

        title = str(case.get("title") or "").strip()
        case_no = str(case.get("case_no") or "").strip()
        court = str(case.get("court") or "").strip()

        identity = case_identity(case)
        if identity is None:
            errors.append(
                f"{label} 缺少案例身份字段：case_id、case_no、raw_record_locator 至少一个非空"
            )
        elif identity in seen_identities:
            errors.append(f"{label} 案例身份键重复：{identity[0]}={identity[1]}")
        else:
            seen_identities.add(identity)

        if not title:
            errors.append(f"{label}.title 不能为空")
        if case_no:
            if case_no in seen_case_nos:
                errors.append(f"{label}.case_no 重复：{case_no}")
            seen_case_nos.add(case_no)

        judges = case.get("judges", [])
        legal_basis = case.get("legal_basis", [])
        if judges is not None and not isinstance(judges, list):
            errors.append(f"{label}.judges 必须是数组")
        if legal_basis is not None and not isinstance(legal_basis, list):
            errors.append(f"{label}.legal_basis 必须是数组")

        decision_date = parse_date(case.get("decision_date"), f"{label}.decision_date", errors)
        if date_from or date_to:
            if decision_date is None:
                errors.append(f"{label} 无法用现有裁判日期验证用户明确时间约束")
            else:
                if date_from and decision_date < date_from:
                    errors.append(f"{label} 裁判日期早于用户明确起始日期")
                if date_to and decision_date > date_to:
                    errors.append(f"{label} 裁判日期晚于用户明确截止日期")

        if regions:
            if not court:
                errors.append(f"{label} 无法院全称，无法验证用户明确地域约束")
            elif not any(region in court for region in regions):
                errors.append(f"{label} 法院不符合用户明确地域约束：{court}")

        if court_levels:
            if not court:
                errors.append(f"{label} 无法院全称，无法验证用户明确法院层级约束")
            elif not any(level in court for level in court_levels):
                errors.append(f"{label} 法院不符合用户明确法院层级约束：{court}")

    for path, text in walk_strings(data):
        if contains_placeholder(text):
            errors.append(f"{path} 含模板占位符")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="校验类案检索报告结构化 JSON")
    parser.add_argument("input_json", type=Path)
    args = parser.parse_args()

    try:
        data = load_json(args.input_json)
    except ValueError as exc:
        print(f"校验失败：{exc}", file=sys.stderr)
        return 1

    errors = validate(data)
    if errors:
        print(f"校验失败，共 {len(errors)} 项：", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"校验通过：{len(data['cases'])} 个案例；仅核验 JSON 中明确声明的约束。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
