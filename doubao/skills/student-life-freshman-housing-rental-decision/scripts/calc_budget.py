#!/usr/bin/env python3
"""计算新生租房的持续成本、首次现金占用和有效月成本。"""

import argparse
import json
import math
import sys


MONTHLY_FIELDS = [
    "monthly_rent",
    "monthly_property",
    "monthly_utilities",
    "monthly_internet",
    "monthly_commute",
    "monthly_other",
]
NONREF_FIELDS = [
    "agency_fee",
    "moving_cost",
    "setup_cost",
    "other_one_time_nonrefundable",
]
CASH_FIELDS = ["deposit", "prepaid_rent", *NONREF_FIELDS]
MAX_MONEY = 100_000_000
MAX_MONTHS = 120


def reject_constant(value):
    raise ValueError(f"不允许非有限数值: {value}")


def parse_number(data, key, *, required=False, integer=False, maximum=MAX_MONEY):
    value = data.get(key)
    if value in (None, ""):
        if required:
            raise ValueError(f"缺少必填字段: {key}")
        return None
    if isinstance(value, bool):
        raise ValueError(f"{key} 必须是数字，不能是布尔值")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{key} 必须是数字") from exc
    if not math.isfinite(number):
        raise ValueError(f"{key} 必须是有限数字")
    if number < 0:
        raise ValueError(f"{key} 不能为负数")
    if number > maximum:
        raise ValueError(f"{key} 超出允许范围")
    if integer:
        if not number.is_integer():
            raise ValueError(f"{key} 必须是整数")
        return int(number)
    return number


def rounded(value):
    return None if value is None else round(value, 2)


def main():
    parser = argparse.ArgumentParser(description="计算新生租房预算")
    parser.add_argument("--input", required=True, help="JSON 输入文件")
    args = parser.parse_args()
    try:
        with open(args.input, "r", encoding="utf-8") as file:
            data = json.load(file, parse_constant=reject_constant)
        if not isinstance(data, dict):
            raise ValueError("JSON 根节点必须是对象")

        months = parse_number(
            data,
            "planned_months",
            required=True,
            integer=True,
            maximum=MAX_MONTHS,
        )
        if months <= 0:
            raise ValueError("planned_months 必须大于 0")
        parse_number(data, "monthly_rent", required=True)

        values = {key: parse_number(data, key) for key in set(MONTHLY_FIELDS + CASH_FIELDS)}
        monthly_missing = [key for key in MONTHLY_FIELDS if values[key] is None]
        cash_missing = [key for key in CASH_FIELDS if values[key] is None]
        nonref_missing = [key for key in NONREF_FIELDS if values[key] is None]

        known_monthly = sum(values[key] or 0 for key in MONTHLY_FIELDS)
        known_cash = sum(values[key] or 0 for key in CASH_FIELDS)
        known_nonref = sum(values[key] or 0 for key in NONREF_FIELDS)
        monthly_total = None if monthly_missing else known_monthly
        initial_cash = None if cash_missing else known_cash
        nonref = None if nonref_missing else known_nonref
        effective_monthly = (
            None
            if monthly_total is None or nonref is None
            else monthly_total + nonref / months
        )

        budget_limit = parse_number(data, "monthly_budget_limit")
        if budget_limit is None:
            over_budget = None
        elif monthly_total is not None:
            over_budget = monthly_total > budget_limit
        elif known_monthly > budget_limit:
            over_budget = True
        else:
            over_budget = None

        currency = str(data.get("currency") or "未指定").strip()
        if not currency or len(currency) > 16 or any(ch in currency for ch in "\r\n\t"):
            raise ValueError("currency 格式无效")

        missing_fields = [*monthly_missing, *cash_missing]
        output = {
            "currency": currency,
            "monthly_total": rounded(monthly_total),
            "known_monthly_subtotal": rounded(known_monthly),
            "initial_cash_required": rounded(initial_cash),
            "known_initial_cash_subtotal": rounded(known_cash),
            "nonrefundable_one_time": rounded(nonref),
            "known_nonrefundable_subtotal": rounded(known_nonref),
            "effective_monthly_cost": rounded(effective_monthly),
            "planned_months": months,
            "monthly_budget_limit": rounded(budget_limit),
            "over_monthly_budget": over_budget,
            "complete": not missing_fields,
            "missing_fields": missing_fields,
            "warning": (
                None
                if not missing_fields
                else "缺失字段按未知处理；known_* 仅是已知小计，不是总成本。"
            ),
        }
        print(json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False))
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
