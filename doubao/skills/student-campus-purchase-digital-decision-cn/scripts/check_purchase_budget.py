#!/usr/bin/env python3
"""Validate a purchase plan and calculate only evidence-backed budget totals."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any


TIERS = ("buy_now", "after_arrival", "optional", "do_not_buy")
MAX_ITEMS = 200
MAX_AMOUNT = 1_000_000_000
MAX_QUANTITY = 1_000


def reject_constant(value: str) -> None:
    raise ValueError(f"不允许非有限数值: {value}")


def error(message: str) -> int:
    print(json.dumps({"ok": False, "error": message}, ensure_ascii=False), file=sys.stderr)
    return 2


def number(
    value: Any,
    field: str,
    *,
    allow_null: bool = False,
    integer: bool = False,
    minimum: float = 0,
    maximum: float = MAX_AMOUNT,
) -> float | int | None:
    if value is None and allow_null:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} 必须是数值")
    if not math.isfinite(value):
        raise ValueError(f"{field} 必须是有限数值")
    if integer and not isinstance(value, int):
        raise ValueError(f"{field} 必须是整数")
    if not minimum <= value <= maximum:
        raise ValueError(f"{field} 必须在 {minimum} 到 {maximum} 之间")
    return value


def nonempty_string(value: Any, field: str, maximum: int = 100) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} 必须是非空字符串")
    result = value.strip()
    if len(result) > maximum:
        raise ValueError(f"{field} 过长")
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="检查开学采购预算")
    parser.add_argument("--input", required=True, type=Path, help="采购计划 JSON 文件")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        with args.input.open("r", encoding="utf-8") as handle:
            data = json.load(handle, parse_constant=reject_constant)
        if not isinstance(data, dict):
            raise ValueError("JSON 根节点必须是对象")

        budget = number(data.get("total_budget"), "total_budget")
        currency = data.get("currency", "CNY")
        if not isinstance(currency, str) or not 3 <= len(currency.strip()) <= 8:
            raise ValueError("currency 必须是 3–8 个字符")
        currency = currency.strip().upper()

        items = data.get("items")
        if not isinstance(items, list) or not 1 <= len(items) <= MAX_ITEMS:
            raise ValueError(f"items 必须是 1–{MAX_ITEMS} 项的数组")

        totals = {tier: 0.0 for tier in TIERS}
        missing_by_tier = {tier: [] for tier in TIERS}
        normalized_items = []
        seen_names: set[str] = set()

        for index, item in enumerate(items):
            if not isinstance(item, dict):
                raise ValueError(f"items[{index}] 必须是对象")
            name = nonempty_string(item.get("name"), f"items[{index}].name")
            if name in seen_names:
                raise ValueError(f"项目名称重复: {name}")
            seen_names.add(name)

            tier = item.get("tier")
            if tier not in TIERS:
                raise ValueError(f"items[{index}].tier 非法")
            quantity = number(
                item.get("quantity", 1),
                f"items[{index}].quantity",
                integer=True,
                minimum=1,
                maximum=MAX_QUANTITY,
            )
            unit_price = number(
                item.get("price_estimate"),
                f"items[{index}].price_estimate",
                allow_null=True,
            )
            line_total = None if unit_price is None else float(unit_price * quantity)
            if line_total is None:
                missing_by_tier[tier].append(name)
            else:
                totals[tier] += line_total
            normalized_items.append(
                {
                    "name": name,
                    "tier": tier,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "known_line_total": line_total,
                }
            )

        committed_missing = missing_by_tier["buy_now"] + missing_by_tier["after_arrival"]
        optional_missing = committed_missing + missing_by_tier["optional"]
        known_committed = totals["buy_now"] + totals["after_arrival"]
        known_with_optional = known_committed + totals["optional"]
        committed_total = None if committed_missing else round(known_committed, 2)
        with_optional_total = None if optional_missing else round(known_with_optional, 2)

        output = {
            "ok": True,
            "currency": currency,
            "budget": budget,
            "items": normalized_items,
            "known_totals_by_tier": {key: round(value, 2) for key, value in totals.items()},
            "known_committed_subtotal": round(known_committed, 2),
            "committed_total": committed_total,
            "committed_over_budget": None if committed_total is None else committed_total > budget,
            "known_with_optional_subtotal": round(known_with_optional, 2),
            "with_optional_total": with_optional_total,
            "with_optional_over_budget": (
                None if with_optional_total is None else with_optional_total > budget
            ),
            "remaining_after_committed": (
                None if committed_total is None else round(budget - committed_total, 2)
            ),
            "missing_price_items_by_tier": missing_by_tier,
            "complete": not any(missing_by_tier.values()),
            "warning": (
                None
                if not any(missing_by_tier.values())
                else "未知价格未按 0 处理；known_* 仅是已知小计。"
            ),
        }
        print(json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False))
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        return error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
