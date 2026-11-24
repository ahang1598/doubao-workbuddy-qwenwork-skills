#!/usr/bin/env python3
"""校验事实表的结构、日期和来源字段。"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

CLAIM_ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]*$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

BROKER_SOURCE_TYPES = {"broker_research", "broker_consensus", "sellside_research"}
MEDIA_SOURCE_TYPES = {"media", "news", "social", "forum", "xueqiu", "toutiao"}
CALC_SOURCE_TYPES = {"calculation", "author_calculation", "model_calculation"}


def load_json(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    stripped = text.strip()
    if stripped.startswith("{"):
        return json.loads(stripped)
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    if match:
        return json.loads(match.group(1))
    raise ValueError(f"{path} 不包含合法的 JSON 对象")


def parse_date(value: Any) -> date | None:
    if not isinstance(value, str) or not DATE_RE.match(value):
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def validate_meta(facts: dict[str, Any], errors: list[str]) -> None:
    meta = facts.get("meta")
    if not isinstance(meta, dict):
        errors.append("meta 缺失")
        return

    for field in ("company", "market", "today"):
        if not meta.get(field):
            errors.append(f"meta.{field} 缺失")

    today = parse_date(meta.get("today"))
    if meta.get("today") and today is None:
        errors.append("meta.today 格式错误，应为 YYYY-MM-DD")

    announcement_date = parse_date(meta.get("announcement_date"))
    if meta.get("announcement_date") and announcement_date is None:
        errors.append("meta.announcement_date 格式错误，应为 YYYY-MM-DD")

    if today and announcement_date and announcement_date > today:
        errors.append("meta.announcement_date 晚于 meta.today")


def validate_claims(facts: dict[str, Any], errors: list[str]) -> None:
    claims = facts.get("claims")
    if not isinstance(claims, list) or not claims:
        errors.append("claims 必须是非空数组")
        return

    seen: set[str] = set()
    for idx, claim in enumerate(claims):
        path = f"claims[{idx}]"
        if not isinstance(claim, dict):
            errors.append(f"{path} 必须是对象")
            continue

        claim_id = claim.get("claim_id")
        if not isinstance(claim_id, str) or not CLAIM_ID_RE.fullmatch(claim_id):
            errors.append(f"{path}.claim_id 缺失或格式错误（需以字母开头，只含字母/数字/._-）")
        elif claim_id in seen:
            errors.append(f"{path}.claim_id 重复：{claim_id}")
        else:
            seen.add(claim_id)

        if not claim.get("source"):
            errors.append(f"{path}.source 缺失")
        usage_type = claim.get("usage_type")
        if not usage_type:
            errors.append(f"{path}.usage_type 缺失")
        source_type = claim.get("source_type")
        tier = claim.get("tier")
        if usage_type == "hard_fact":
            is_secondary_tier = tier in ("broker", "media", "market")
            is_secondary_type = isinstance(source_type, str) and source_type in BROKER_SOURCE_TYPES | MEDIA_SOURCE_TYPES
            if is_secondary_tier or is_secondary_type:
                errors.append(
                    f"{path} 是 hard_fact，但来源指向 broker/media/market；"
                    "请改 usage_type（如 broker_estimate/market_view）或换成公司/交易所/官方数据库来源"
                )
        is_calculation_source = isinstance(source_type, str) and source_type in CALC_SOURCE_TYPES
        if (is_calculation_source or usage_type == "author_calculation") and not claim.get("calculation"):
            errors.append(f"{path} 是作者计算值（author_calculation）但缺少 calculation 字段，需写明算式")


def validate(facts: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    validate_meta(facts, errors)
    validate_claims(facts, errors)
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="校验 facts.json（门禁 1）")
    parser.add_argument("facts_json", help="facts.json 文件路径")
    args = parser.parse_args(argv)

    try:
        facts = load_json(Path(args.facts_json))
    except Exception as exc:  # noqa: BLE001
        print(f"[错误] 无法读取 JSON: {exc}", file=sys.stderr)
        return 1

    errors = validate(facts)
    for error in errors:
        print(f"[错误] {error}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
