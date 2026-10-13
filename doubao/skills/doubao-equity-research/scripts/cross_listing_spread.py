#!/usr/bin/env python3
"""Normalize cross-listing prices and measure an A/H-style relative-value spread."""

import argparse
import json
import math
import statistics
import sys
from datetime import date
from pathlib import Path


IMPLEMENTATION_CHECKS = (
    "fungible_or_convertible",
    "short_high_leg_available",
    "long_low_leg_accessible",
    "settlement_and_funding_aligned",
)


def emit(message):
    sys.stderr.write(f"{message}\n")


def finite_number(value, label, *, positive=False, nonnegative=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} 必须是数值")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{label} 必须是有限数")
    if positive and number <= 0:
        raise ValueError(f"{label} 必须大于 0")
    if nonnegative and number < 0:
        raise ValueError(f"{label} 不得小于 0")
    return number


def iso_date(value, label):
    if not isinstance(value, str):
        raise ValueError(f"{label} 必须是 YYYY-MM-DD")
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{label} 必须是 YYYY-MM-DD") from exc
    return value


def nonempty_text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} 必须是非空字符串")
    return value.strip()


def normalized_spread(row, prefix):
    a_price = finite_number(row.get("a_price_cny"), f"{prefix}.a_price_cny", positive=True)
    h_price = finite_number(row.get("h_price_hkd"), f"{prefix}.h_price_hkd", positive=True)
    fx = finite_number(row.get("cny_per_hkd"), f"{prefix}.cny_per_hkd", positive=True)
    a_claim = finite_number(
        row.get("a_claim_units_per_share", 1.0),
        f"{prefix}.a_claim_units_per_share",
        positive=True,
    )
    h_claim = finite_number(
        row.get("h_claim_units_per_share", 1.0),
        f"{prefix}.h_claim_units_per_share",
        positive=True,
    )
    a_cny_per_unit = a_price / a_claim
    h_cny_per_unit = h_price * fx / h_claim
    a_over_h_premium = a_cny_per_unit / h_cny_per_unit - 1.0
    h_discount_to_a = 1.0 - h_cny_per_unit / a_cny_per_unit
    return {
        "a_cny_per_economic_unit": a_cny_per_unit,
        "h_cny_per_economic_unit": h_cny_per_unit,
        "a_over_h_premium": a_over_h_premium,
        "h_discount_to_a": h_discount_to_a,
    }


def parse_implementation(value):
    if value is None:
        value = {}
    if not isinstance(value, dict):
        raise ValueError("implementation 必须是对象")
    checks = {name: value.get(name) is True for name in IMPLEMENTATION_CHECKS}
    missing = [name for name, passed in checks.items() if not passed]
    classification = (
        "mechanically_executable_candidate" if not missing else "relative_value_only"
    )
    return {
        "classification": classification,
        "checks": checks,
        "unmet_checks": missing,
    }


def analyze(data):
    if not isinstance(data, dict):
        raise ValueError("输入 JSON 顶层必须是对象")
    as_of = iso_date(data.get("as_of"), "as_of")
    pair = data.get("pair")
    if not isinstance(pair, dict):
        raise ValueError("pair 必须是对象")
    a_symbol = nonempty_text(pair.get("a_symbol"), "pair.a_symbol")
    h_symbol = nonempty_text(pair.get("h_symbol"), "pair.h_symbol")
    spot = normalized_spread(pair, "pair")

    history = data.get("history", [])
    if not isinstance(history, list):
        raise ValueError("history 必须是数组")
    if len(history) > 5000:
        raise ValueError("history 最多 5000 条")
    seen_dates = set()
    history_rows = []
    for index, row in enumerate(history):
        if not isinstance(row, dict):
            raise ValueError(f"history[{index}] 必须是对象")
        day = iso_date(row.get("date"), f"history[{index}].date")
        if day in seen_dates:
            raise ValueError(f"history 存在重复日期: {day}")
        seen_dates.add(day)
        metrics = normalized_spread(row, f"history[{index}]")
        history_rows.append({"date": day, **metrics})
    if [row["date"] for row in history_rows] != sorted(row["date"] for row in history_rows):
        raise ValueError("history 必须按日期严格升序")

    costs = data.get("costs", {})
    if not isinstance(costs, dict):
        raise ValueError("costs 必须是对象")
    total_cost_bps = finite_number(
        costs.get("total_estimated_cost_bps", 0.0),
        "costs.total_estimated_cost_bps",
        nonnegative=True,
    )

    result = {
        "as_of": as_of,
        "pair": {"a_symbol": a_symbol, "h_symbol": h_symbol},
        "formula": (
            "A/H premium = (A price CNY / A claim units) / "
            "(H price HKD × CNY per HKD / H claim units) - 1"
        ),
        "spot": {
            **spot,
            "total_estimated_cost_bps": total_cost_bps,
            "premium_less_cost_buffer": spot["a_over_h_premium"]
            - total_cost_bps / 10000.0,
        },
        "implementation": parse_implementation(data.get("implementation")),
        "warnings": [
            "价差统计不证明均值回归或可执行套利。",
            "税费、股息、汇率、融券召回、停牌、节假日和结算错位需另行核验。",
        ],
    }

    if history_rows:
        premiums = [row["a_over_h_premium"] for row in history_rows]
        mean = statistics.fmean(premiums)
        stdev = statistics.pstdev(premiums) if len(premiums) >= 2 else 0.0
        percentile = sum(value <= spot["a_over_h_premium"] for value in premiums) / len(
            premiums
        )
        result["history"] = {
            "status": "available",
            "count": len(premiums),
            "start": history_rows[0]["date"],
            "end": history_rows[-1]["date"],
            "mean_premium": mean,
            "min_premium": min(premiums),
            "max_premium": max(premiums),
            "population_stdev": stdev,
            "spot_z_score": (
                (spot["a_over_h_premium"] - mean) / stdev if stdev > 0 else None
            ),
            "spot_percentile": percentile,
        }
        if len(premiums) < 20:
            result["warnings"].append(
                "历史样本少于 20 个观测值，分位与 z-score 仅作描述，不宜据此下交易结论。"
            )
    else:
        result["history"] = {
            "status": "unavailable",
            "reason": "未提供同口径历史序列，不能判断历史位置",
        }
    return result


def load_object(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_output(path, result, input_path):
    output = Path(path).resolve()
    if output == Path(input_path).resolve():
        raise ValueError("输出路径不能覆盖输入文件")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def run_self_test():
    data = {
        "as_of": "2026-07-23",
        "pair": {
            "a_symbol": "600000.SH",
            "h_symbol": "00000.HK",
            "a_price_cny": 10.0,
            "h_price_hkd": 8.0,
            "cny_per_hkd": 0.9,
        },
        "history": [
            {
                "date": "2026-07-21",
                "a_price_cny": 9.0,
                "h_price_hkd": 8.0,
                "cny_per_hkd": 0.9,
            },
            {
                "date": "2026-07-22",
                "a_price_cny": 9.5,
                "h_price_hkd": 8.0,
                "cny_per_hkd": 0.9,
            },
        ],
        "costs": {"total_estimated_cost_bps": 50},
        "implementation": {
            "fungible_or_convertible": False,
            "short_high_leg_available": True,
            "long_low_leg_accessible": True,
            "settlement_and_funding_aligned": True,
        },
    }
    result = analyze(data)
    expected = 10.0 / (8.0 * 0.9) - 1.0
    if abs(result["spot"]["a_over_h_premium"] - expected) > 1e-12:
        raise AssertionError("A/H 溢价计算错误")
    if result["implementation"]["classification"] != "relative_value_only":
        raise AssertionError("缺少可转换性时不得标记为可执行候选")
    if result["history"]["count"] != 2:
        raise AssertionError("历史统计错误")

    executable = dict(data)
    executable["implementation"] = {name: True for name in IMPLEMENTATION_CHECKS}
    if analyze(executable)["implementation"]["classification"] != (
        "mechanically_executable_candidate"
    ):
        raise AssertionError("全部执行条件为真时分类错误")

    malformed = dict(data)
    malformed["pair"] = dict(data["pair"])
    malformed["pair"]["cny_per_hkd"] = 0
    try:
        analyze(malformed)
    except ValueError:
        pass
    else:
        raise AssertionError("非正汇率应被拒绝")
    print("SELF_TEST_PASS")


def build_parser():
    parser = argparse.ArgumentParser(
        description="计算 A/H 或其他跨上市地证券的同币种折溢价与历史位置"
    )
    parser.add_argument("input", nargs="?", help="输入 JSON")
    parser.add_argument("--output", help="输出 JSON；省略时写到 stdout")
    parser.add_argument("--self-test", action="store_true")
    return parser


def main():
    args = build_parser().parse_args()
    if args.self_test:
        run_self_test()
        return 0
    if not args.input:
        emit("错误: 必须提供输入 JSON")
        return 2
    try:
        result = analyze(load_object(args.input))
        if args.output:
            write_output(args.output, result, args.input)
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        emit(f"错误: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
