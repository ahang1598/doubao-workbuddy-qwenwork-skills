#!/usr/bin/env python3
"""Validate and calculate IFRS/Non-IFRS or GAAP/Non-GAAP reconciliation bridges."""

import argparse
import json
import math
import sys
from pathlib import Path


BASIS_PAIRS = {
    "ifrs_non_ifrs": ("IFRS", "Non-IFRS"),
    "gaap_non_gaap": ("GAAP", "Non-GAAP"),
    "reported_adjusted": ("Reported", "Adjusted"),
}
RECURRENCE = {"one_off", "potentially_recurring", "recurring", "unknown"}
CASH_EFFECT = {"cash", "non_cash", "mixed", "unknown"}


def emit(message):
    sys.stderr.write(f"{message}\n")


def finite_number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} 必须是数值")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{label} 必须是有限数")
    return number


def nonempty_text(value, label, *, max_length=120):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} 必须是非空字符串")
    value = value.strip()
    if len(value) > max_length:
        raise ValueError(f"{label} 最长 {max_length} 个字符")
    return value


def optional_text(value, label, *, max_length=120):
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValueError(f"{label} 必须是字符串")
    value = value.strip()
    if len(value) > max_length:
        raise ValueError(f"{label} 最长 {max_length} 个字符")
    return value


def meaningful_ratio(numerator, denominator, *, sign_change=False):
    scale = max(abs(numerator), abs(denominator), 1.0)
    if sign_change or abs(denominator) <= scale * 1e-9:
        return None
    return numerator / abs(denominator)


def validate_and_calculate(data):
    if not isinstance(data, dict):
        raise ValueError("输入 JSON 顶层必须是对象")
    title = nonempty_text(data.get("title"), "title", max_length=100)
    metric = nonempty_text(data.get("metric"), "metric", max_length=60)
    unit = nonempty_text(data.get("unit"), "unit", max_length=30)
    pair_key = data.get("basis_pair", "ifrs_non_ifrs")
    if pair_key not in BASIS_PAIRS:
        raise ValueError(
            "basis_pair 必须是 ifrs_non_ifrs、gaap_non_gaap 或 reported_adjusted"
        )
    reported_label, adjusted_label = BASIS_PAIRS[pair_key]
    strict = data.get("strict_reconciliation", True)
    if not isinstance(strict, bool):
        raise ValueError("strict_reconciliation 必须是布尔值")
    tolerance = finite_number(data.get("tolerance", 1e-6), "tolerance")
    if tolerance < 0:
        raise ValueError("tolerance 不得小于 0")
    raw_periods = data.get("periods")
    if not isinstance(raw_periods, list) or not 1 <= len(raw_periods) <= 20:
        raise ValueError("periods 必须包含 1–20 项")

    results = []
    warnings = []
    seen_periods = set()
    for period_index, raw in enumerate(raw_periods):
        if not isinstance(raw, dict):
            raise ValueError(f"periods[{period_index}] 必须是对象")
        period = nonempty_text(
            raw.get("period"), f"periods[{period_index}].period", max_length=30
        )
        if period in seen_periods:
            raise ValueError(f"periods 存在重复期间: {period}")
        seen_periods.add(period)
        reported = finite_number(
            raw.get("reported", raw.get("ifrs")),
            f"periods[{period_index}].reported",
        )
        adjusted = finite_number(
            raw.get("adjusted", raw.get("non_ifrs")),
            f"periods[{period_index}].adjusted",
        )
        gap = adjusted - reported
        sign_change = reported * adjusted < 0

        raw_items = raw.get("adjustments", [])
        if not isinstance(raw_items, list) or len(raw_items) > 20:
            raise ValueError(
                f"periods[{period_index}].adjustments 必须是最多 20 项的数组"
            )
        adjustments = []
        for item_index, item in enumerate(raw_items):
            if not isinstance(item, dict):
                raise ValueError(
                    f"periods[{period_index}].adjustments[{item_index}] 必须是对象"
                )
            recurrence = item.get("recurrence", "unknown")
            cash_effect = item.get("cash_effect", "unknown")
            if recurrence not in RECURRENCE:
                raise ValueError(
                    f"periods[{period_index}].adjustments[{item_index}].recurrence "
                    f"必须是 {sorted(RECURRENCE)} 之一"
                )
            if cash_effect not in CASH_EFFECT:
                raise ValueError(
                    f"periods[{period_index}].adjustments[{item_index}].cash_effect "
                    f"必须是 {sorted(CASH_EFFECT)} 之一"
                )
            adjustments.append(
                {
                    "label": nonempty_text(
                        item.get("label"),
                        f"periods[{period_index}].adjustments[{item_index}].label",
                        max_length=60,
                    ),
                    "amount": finite_number(
                        item.get("amount"),
                        f"periods[{period_index}].adjustments[{item_index}].amount",
                    ),
                    "recurrence": recurrence,
                    "cash_effect": cash_effect,
                    "note": optional_text(
                        item.get("note"),
                        f"periods[{period_index}].adjustments[{item_index}].note",
                        max_length=160,
                    ),
                }
            )

        item_total = sum(item["amount"] for item in adjustments)
        residual = gap - item_total
        allowed_error = max(tolerance, abs(adjusted) * 1e-6, abs(reported) * 1e-6)
        balanced = abs(residual) <= allowed_error
        if adjustments and not balanced:
            message = (
                f"{period} 调节桥不平：{adjusted_label}-{reported_label}={gap:g}，"
                f"调节项合计={item_total:g}，残差={residual:g} {unit}"
            )
            if strict:
                raise ValueError(message)
            warnings.append(message)
        if not adjustments:
            warnings.append(f"{period} 未提供调节项，只能计算口径差额，不能解释差异来源")
        if sign_change:
            warnings.append(
                f"{period} 两种口径发生盈亏方向切换，不应使用百分比改善描述"
            )
        elif reported <= 0:
            warnings.append(
                f"{period} 法定/报告口径不为正，不应使用口径差额百分比描述改善"
            )

        absolute_total = sum(abs(item["amount"]) for item in adjustments)
        recurring_total = sum(
            abs(item["amount"])
            for item in adjustments
            if item["recurrence"] in {"recurring", "potentially_recurring"}
        )
        non_cash_total = sum(
            abs(item["amount"])
            for item in adjustments
            if item["cash_effect"] == "non_cash"
        )
        gap_ratio = meaningful_ratio(
            gap, reported, sign_change=sign_change or reported <= 0
        )
        dependency = meaningful_ratio(
            abs(gap), adjusted, sign_change=adjusted <= 0
        )
        results.append(
            {
                "period": period,
                "reported_label": reported_label,
                "adjusted_label": adjusted_label,
                "reported": reported,
                "adjusted": adjusted,
                "gap": gap,
                "gap_pct_of_reported": gap_ratio,
                "gap_pct_is_meaningful": gap_ratio is not None,
                "sign_change": sign_change,
                "adjustment_dependency": dependency,
                "reconciliation": {
                    "items_total": item_total,
                    "residual": residual,
                    "balanced": balanced if adjustments else None,
                },
                "adjustment_profile": {
                    "absolute_adjustments_total": absolute_total,
                    "recurring_or_potentially_recurring_share": (
                        recurring_total / absolute_total if absolute_total else None
                    ),
                    "identified_non_cash_share": (
                        non_cash_total / absolute_total if absolute_total else None
                    ),
                },
                "adjustments": adjustments,
                "waterfall_input": (
                    {
                        "title": f"{title}：{period} 口径调节桥",
                        "unit": unit,
                        "items": [
                            {"label": reported_label, "value": reported, "kind": "start"},
                            *[
                                {
                                    "label": item["label"],
                                    "value": item["amount"],
                                    "kind": "change",
                                }
                                for item in adjustments
                            ],
                            {"label": adjusted_label, "value": adjusted, "kind": "end"},
                        ],
                    }
                    if adjustments and balanced
                    else None
                ),
            }
        )

    valuation_basis = optional_text(
        data.get("valuation_basis"), "valuation_basis", max_length=80
    )
    if not valuation_basis:
        warnings.append(
            "未声明估值分母口径；使用 P/E、EPS 或盈利预测时必须说明采用哪一种口径"
        )
    return {
        "title": title,
        "metric": metric,
        "unit": unit,
        "basis_pair": pair_key,
        "basis_rule": f"{adjusted_label} = {reported_label} + 调节项",
        "valuation_basis": valuation_basis,
        "periods": results,
        "warnings": warnings,
    }


def write_json(path, payload, input_path=None):
    output = Path(path).resolve()
    if input_path is not None and output == Path(input_path).resolve():
        raise ValueError("输出路径不能覆盖输入文件")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return output


def self_test():
    valid = {
        "title": "示例公司净利润",
        "metric": "归母净利润",
        "unit": "百万元",
        "basis_pair": "ifrs_non_ifrs",
        "valuation_basis": "Non-IFRS diluted EPS",
        "periods": [
            {
                "period": "FY2025",
                "ifrs": 80,
                "non_ifrs": 120,
                "adjustments": [
                    {
                        "label": "股份支付",
                        "amount": 30,
                        "recurrence": "recurring",
                        "cash_effect": "non_cash",
                    },
                    {
                        "label": "并购摊销",
                        "amount": 10,
                        "recurrence": "potentially_recurring",
                        "cash_effect": "non_cash",
                    },
                ],
            }
        ],
    }
    result = validate_and_calculate(valid)
    period = result["periods"][0]
    assert period["gap"] == 40
    assert period["reconciliation"]["balanced"] is True
    assert period["adjustment_profile"]["recurring_or_potentially_recurring_share"] == 1
    invalid = json.loads(json.dumps(valid))
    invalid["periods"][0]["adjustments"][0]["amount"] = 20
    try:
        validate_and_calculate(invalid)
    except ValueError:
        pass
    else:
        raise AssertionError("不平衡的严格调节桥应被拒绝")
    emit("SELF_TEST_PASS")


def build_parser():
    parser = argparse.ArgumentParser(
        description="校验并计算 IFRS/Non-IFRS、GAAP/Non-GAAP 或 reported/adjusted 调节桥。"
    )
    parser.add_argument("input_json", nargs="?")
    parser.add_argument("--output")
    parser.add_argument("--self-test", action="store_true")
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.self_test:
        self_test()
        return 0
    if not args.input_json or not args.output:
        parser.error("正常运行必须提供 input_json 和 --output")
    try:
        data = json.loads(Path(args.input_json).read_text(encoding="utf-8"))
        result = validate_and_calculate(data)
        output = write_json(args.output, result, args.input_json)
    except Exception as exc:
        emit(f"[错误] {exc}")
        return 1
    emit(f"已生成: {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
