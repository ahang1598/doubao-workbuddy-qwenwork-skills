#!/usr/bin/env python3
"""Validate, merge, deduplicate, limit, and trim case-search results returned by case-retrieval connectors."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "case-retrieval-handoff/v1"
HEAVY_FIELDS = {
    "courtFindOut",
    "courtThink",
    "sourceContent",
    "trialProcess",
    "preTrialProcess",
}


class ValidationError(ValueError):
    """Raised when a search response cannot be safely processed."""


def load_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValidationError(f"无法读取有效 JSON：{path}：{exc}") from exc

    if not isinstance(payload, dict):
        raise ValidationError(f"顶层 JSON 必须是对象：{path}")
    return payload


def validate_page(payload: dict[str, Any], label: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    body = payload.get("Body")
    if not isinstance(body, dict):
        raise ValidationError(f"{label} 缺少对象字段 Body")
    if body.get("success") is False:
        message = body.get("message") or "检索响应 success=false"
        raise ValidationError(f"{label} 响应失败：{message}")

    data = body.get("data")
    if not isinstance(data, dict):
        raise ValidationError(f"{label} 缺少对象字段 Body.data")
    cases = data.get("caseResult")
    if not isinstance(cases, list):
        raise ValidationError(f"{label} 的 Body.data.caseResult 必须是数组")

    validated: list[dict[str, Any]] = []
    for index, case in enumerate(cases):
        if not isinstance(case, dict):
            raise ValidationError(f"{label} 的第 {index + 1} 个案例必须是对象")
        domain = case.get("caseDomain")
        if not isinstance(domain, dict):
            raise ValidationError(f"{label} 的第 {index + 1} 个案例缺少对象字段 caseDomain")
        case_no = domain.get("caseNo")
        if case_no is not None and not isinstance(case_no, str):
            raise ValidationError(f"{label} 的第 {index + 1} 个案例 caseNo 必须是字符串或 null")
        validated.append(case)
    return data, validated


def nonblank(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def court_name(domain: dict[str, Any]) -> str:
    court = domain.get("trialCourt")
    if isinstance(court, dict):
        return nonblank(court.get("name")) or ""
    return ""


def case_identity(case: dict[str, Any]) -> str:
    domain = case["caseDomain"]
    case_id = nonblank(domain.get("caseId"))
    if case_id:
        return f"id:{case_id}"

    case_no = nonblank(domain.get("caseNo"))
    if case_no:
        return f"no:{case_no}"

    title = nonblank(domain.get("caseTitle")) or ""
    trial_date = nonblank(domain.get("trialDate")) or ""
    court = court_name(domain)
    if title and trial_date and court:
        raw = json.dumps([title, court, trial_date], ensure_ascii=False, separators=(",", ":"))
        return "meta:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()

    raw = json.dumps(domain, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "json:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def deduplicate(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for case in cases:
        identity = case_identity(case)
        if identity in seen:
            continue
        seen.add(identity)
        unique.append(case)
    return unique


def trim_case(case: dict[str, Any], include_court_think: bool) -> dict[str, Any]:
    trimmed = copy.deepcopy(case)
    domain = trimmed["caseDomain"]
    fields_to_remove = HEAVY_FIELDS - ({"courtThink"} if include_court_think else set())
    for field in fields_to_remove:
        domain.pop(field, None)
    return trimmed


def extract_query(data_pages: list[dict[str, Any]], override: str | None) -> str | None:
    if override is not None:
        return override
    for data in data_pages:
        query = nonblank(data.get("query"))
        if query:
            return query
    return None


def service_total(data_pages: list[dict[str, Any]]) -> int | None:
    totals = [value for data in data_pages if isinstance((value := data.get("totalCount")), int)]
    return max(totals) if totals else None


def build_outputs(
    pages: list[dict[str, Any]],
    requested_count: int | None,
    include_court_think: bool,
    query_override: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    data_pages: list[dict[str, Any]] = []
    raw_cases: list[dict[str, Any]] = []
    for index, page in enumerate(pages):
        data, cases = validate_page(page, f"第 {index + 1} 页")
        data_pages.append(data)
        raw_cases.extend(cases)

    unique_cases = deduplicate(raw_cases)
    delivery_cases = unique_cases[:requested_count] if requested_count is not None else unique_cases
    missing_case_no_count = sum(
        1 for case in delivery_cases if nonblank(case["caseDomain"].get("caseNo")) is None
    )
    shortfall = max(requested_count - len(delivery_cases), 0) if requested_count is not None else 0
    stats: dict[str, Any] = {
        "pageCount": len(pages),
        "rawCaseCount": len(raw_cases),
        "uniqueCaseCount": len(unique_cases),
        "deliveryCount": len(delivery_cases),
        "duplicateCount": len(raw_cases) - len(unique_cases),
        "requestedCount": requested_count,
        "shortfall": shortfall,
        "missingCaseNoCount": missing_case_no_count,
    }

    common = {
        "schemaVersion": SCHEMA_VERSION,
        "query": extract_query(data_pages, query_override),
        "source": {
            "provider": "case-retrieval-connector",
            "pageCount": len(pages),
            "serviceTotalCount": service_total(data_pages),
        },
    }
    full = {
        **common,
        "setType": "full",
        "processing": {
            **stats,
            "heavyFieldsTrimmed": False,
            "courtThinkIncluded": True,
        },
        "cases": copy.deepcopy(unique_cases),
    }
    delivery = {
        **common,
        "setType": "delivery",
        "processing": {
            **stats,
            "heavyFieldsTrimmed": True,
            "courtThinkIncluded": include_court_think,
        },
        "cases": [trim_case(case, include_court_think) for case in delivery_cases],
    }
    return full, delivery, stats


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def positive_integer(value: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("必须是正整数") from exc
    if number <= 0:
        raise argparse.ArgumentTypeError("必须是正整数")
    return number


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", action="append", required=True, type=Path, help="分页检索结果 JSON，可重复")
    parser.add_argument("--full-output", required=True, type=Path, help="完整去重结果 JSON")
    parser.add_argument("--trimmed-output", required=True, type=Path, help="裁剪后的交付集 JSON")
    parser.add_argument("--stats-output", required=True, type=Path, help="处理统计 JSON")
    parser.add_argument("--requested-count", type=positive_integer, help="用户明确要求的案例数量")
    parser.add_argument("--include-court-think", action="store_true", help="交付集保留 courtThink")
    parser.add_argument("--query", help="覆盖原始响应中的 Query，仅用于记录")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        pages = [load_json(path) for path in args.input]
        full, delivery, stats = build_outputs(
            pages,
            requested_count=args.requested_count,
            include_court_think=args.include_court_think,
            query_override=args.query,
        )
        write_json(args.full_output, full)
        write_json(args.trimmed_output, delivery)
        write_json(args.stats_output, stats)
    except ValidationError as exc:
        print(f"数据校验失败：{exc}", file=sys.stderr)
        return 2

    print(json.dumps(stats, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
