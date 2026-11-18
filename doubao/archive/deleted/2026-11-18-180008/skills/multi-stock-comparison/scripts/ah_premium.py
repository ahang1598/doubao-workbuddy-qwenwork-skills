#!/usr/bin/env python3
"""Calculate auditable A/H relative-value gaps without asserting arbitrage."""

import argparse
import json
import math
import sys
import tempfile
from datetime import date, datetime
from pathlib import Path


EXECUTION_CHECKS = (
    "fungibility_or_conversion_verified",
    "both_legs_tradeable",
    "short_leg_borrow_verified",
    "legal_route_verified",
    "settlement_and_fx_verified",
)


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


def nonempty_text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} 必须是非空字符串")
    return value.strip()


def clean_number(value):
    """Remove binary floating-point noise while preserving calculation precision."""
    return round(float(value), 12)


def iso_date(value, label):
    value = nonempty_text(value, label)
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{label} 必须是 YYYY-MM-DD") from exc
    return value


def timestamp(value, label):
    value = nonempty_text(value, label)
    candidate = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise ValueError(f"{label} 必须是 ISO 8601 日期或时间") from exc
    return value


def load_object(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("输入 JSON 顶层必须是对象")
    return data


def analyze_pair(raw, index):
    if not isinstance(raw, dict):
        raise ValueError(f"pairs[{index}] 必须是对象")
    prefix = f"pairs[{index}]"
    issuer = nonempty_text(raw.get("issuer"), f"{prefix}.issuer")

    a = raw.get("a")
    h = raw.get("h")
    fx = raw.get("fx")
    for name, block in (("a", a), ("h", h), ("fx", fx)):
        if not isinstance(block, dict):
            raise ValueError(f"{prefix}.{name} 必须是对象")

    a_code = nonempty_text(a.get("code"), f"{prefix}.a.code")
    h_code = nonempty_text(h.get("code"), f"{prefix}.h.code")
    a_price = finite_number(a.get("price_cny"), f"{prefix}.a.price_cny", positive=True)
    h_price = finite_number(h.get("price_hkd"), f"{prefix}.h.price_hkd", positive=True)
    a_time = timestamp(a.get("timestamp"), f"{prefix}.a.timestamp")
    h_time = timestamp(h.get("timestamp"), f"{prefix}.h.timestamp")
    fx_rate = finite_number(
        fx.get("cny_per_hkd"), f"{prefix}.fx.cny_per_hkd", positive=True
    )
    fx_time = timestamp(fx.get("timestamp"), f"{prefix}.fx.timestamp")
    ratio = finite_number(
        raw.get("a_units_per_h_share", 1.0),
        f"{prefix}.a_units_per_h_share",
        positive=True,
    )

    costs = raw.get("cost_rates", {})
    if not isinstance(costs, dict):
        raise ValueError(f"{prefix}.cost_rates 必须是对象")
    normalized_costs = {}
    for name, value in costs.items():
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"{prefix}.cost_rates 的键必须是非空字符串")
        normalized_costs[name] = finite_number(
            value, f"{prefix}.cost_rates.{name}", nonnegative=True
        )
    total_cost = sum(normalized_costs.values())
    if total_cost >= 1:
        raise ValueError(f"{prefix}.cost_rates 合计必须小于 1")

    checks = raw.get("execution_checks", {})
    if not isinstance(checks, dict):
        raise ValueError(f"{prefix}.execution_checks 必须是对象")
    normalized_checks = {name: checks.get(name) is True for name in EXECUTION_CHECKS}

    h_equivalent_cny = h_price * fx_rate / ratio
    raw_premium = a_price / h_equivalent_cny - 1
    direction = "long_h_short_a" if raw_premium > 0 else "long_a_short_h"
    if abs(raw_premium) < 1e-12:
        direction = "at_indicative_parity"
    declared_executable = all(normalized_checks.values())
    warnings = []
    if len({a_time, h_time, fx_time}) != 1:
        warnings.append("A/H/FX 时间戳不完全一致；价差含异步报价风险")
    if not normalized_checks["fungibility_or_conversion_verified"]:
        warnings.append("未验证股份可转换或可交割路径；不得称为无风险套利")
    if not declared_executable:
        warnings.append("至少一项执行条件未验证；仅可视为相对价值筛查")

    return {
        "issuer": issuer,
        "a_code": a_code,
        "h_code": h_code,
        "a_price_cny": clean_number(a_price),
        "h_price_hkd": clean_number(h_price),
        "fx_cny_per_hkd": clean_number(fx_rate),
        "a_units_per_h_share": clean_number(ratio),
        "h_equivalent_cny_per_a_unit": clean_number(h_equivalent_cny),
        "a_over_h_premium": clean_number(raw_premium),
        "gross_absolute_gap": clean_number(abs(raw_premium)),
        "assumed_total_cost_rate": clean_number(total_cost),
        "indicative_gap_after_assumed_costs": clean_number(
            max(abs(raw_premium) - total_cost, 0.0)
        ),
        "theoretical_direction": direction,
        "timestamps": {"a": a_time, "h": h_time, "fx": fx_time},
        "execution_checks": normalized_checks,
        "execution_screen": (
            "all_declared_checks_true_still_requires_live_verification"
            if declared_executable
            else "not_verified_as_executable"
        ),
        "cost_rates": normalized_costs,
        "warnings": warnings,
    }


def analyze(data):
    as_of = iso_date(data.get("as_of"), "as_of")
    pairs = data.get("pairs")
    if not isinstance(pairs, list) or not pairs:
        raise ValueError("pairs 必须是非空数组")
    if len(pairs) > 100:
        raise ValueError("pairs 最多 100 项")
    results = [analyze_pair(raw, index) for index, raw in enumerate(pairs)]
    return {
        "as_of": as_of,
        "pairs": results,
        "method_note": (
            "价差按同步价格、HKD/CNY 和股份经济单位计算；成本后价差仅为筛查，"
            "不证明股份可转换、借券可得或策略可执行。"
        ),
    }


def write_output(path, result):
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_self_test():
    sample = {
        "as_of": "2026-07-23",
        "pairs": [
            {
                "issuer": "示例公司",
                "a": {"code": "600000.SH", "price_cny": 12.0, "timestamp": "2026-07-23T08:00:00Z"},
                "h": {"code": "00000.HK", "price_hkd": 10.0, "timestamp": "2026-07-23T08:00:00Z"},
                "fx": {"cny_per_hkd": 0.92, "timestamp": "2026-07-23T08:00:00Z"},
                "a_units_per_h_share": 1,
                "cost_rates": {"fees": 0.004, "borrow": 0.02},
                "execution_checks": {name: False for name in EXECUTION_CHECKS},
            }
        ],
    }
    result = analyze(sample)
    pair = result["pairs"][0]
    assert abs(pair["h_equivalent_cny_per_a_unit"] - 9.2) < 1e-12
    assert pair["a_over_h_premium"] > 0
    assert pair["theoretical_direction"] == "long_h_short_a"
    assert pair["execution_screen"] == "not_verified_as_executable"
    assert pair["warnings"]

    executable = json.loads(json.dumps(sample))
    executable["pairs"][0]["execution_checks"] = {name: True for name in EXECUTION_CHECKS}
    assert analyze(executable)["pairs"][0]["execution_screen"].startswith("all_declared")

    invalid = json.loads(json.dumps(sample))
    invalid["pairs"][0]["a"]["price_cny"] = 0
    try:
        analyze(invalid)
    except ValueError:
        pass
    else:
        raise AssertionError("零价格应校验失败")

    with tempfile.TemporaryDirectory() as temp_dir:
        path = Path(temp_dir) / "result.json"
        write_output(path, result)
        assert json.loads(path.read_text(encoding="utf-8"))["pairs"]
    print("SELF_TEST_PASS")


def build_parser():
    parser = argparse.ArgumentParser(description="计算 A/H 折溢价与执行条件筛查")
    parser.add_argument("input", nargs="?", help="输入 JSON 路径")
    parser.add_argument("--output", help="输出 JSON 路径；缺省时写到 stdout")
    parser.add_argument("--self-test", action="store_true")
    return parser


def main():
    args = build_parser().parse_args()
    if args.self_test:
        run_self_test()
        return 0
    if not args.input:
        sys.stderr.write("错误: 必须提供输入 JSON 路径\n")
        return 2
    try:
        result = analyze(load_object(args.input))
        if args.output:
            write_output(args.output, result)
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        sys.stderr.write(f"错误: {exc}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
