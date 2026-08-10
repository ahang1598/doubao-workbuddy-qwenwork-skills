#!/usr/bin/env python3
"""Run a transparent reverse DCF with bisection and sensitivity grids."""

import copy
import argparse
import json
import math
import sys
from pathlib import Path



def emit(message):
    sys.stderr.write("%s\n" % message)


def finite(name, value):
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s 必须为有限数" % name)
    return number


def validate_params(params):
    required = [
        "base_revenue", "years", "growth_rate", "margin_start", "target_margin",
        "tax_rate", "sales_to_capital", "wacc", "terminal_growth", "terminal_roic",
    ]
    for field in required:
        if field not in params:
            raise ValueError("params.%s 缺失" % field)
    if finite("base_revenue", params["base_revenue"]) <= 0:
        raise ValueError("base_revenue 必须为正")
    years = int(params["years"])
    if years < 1 or years > 30:
        raise ValueError("years 必须在 1–30")
    if finite("sales_to_capital", params["sales_to_capital"]) <= 0:
        raise ValueError("sales_to_capital 必须为正")
    wacc = finite("wacc", params["wacc"])
    terminal_growth = finite("terminal_growth", params["terminal_growth"])
    terminal_roic = finite("terminal_roic", params["terminal_roic"])
    if not 0 < wacc < 1:
        raise ValueError("wacc 必须在 (0,1) 内")
    if terminal_growth <= -1:
        raise ValueError("terminal_growth 必须大于 -1")
    if wacc <= terminal_growth:
        raise ValueError("wacc 必须大于 terminal_growth")
    if terminal_roic <= terminal_growth:
        raise ValueError("terminal_roic 必须大于 terminal_growth")
    if not 0 <= finite("tax_rate", params["tax_rate"]) < 1:
        raise ValueError("tax_rate 必须在 [0,1)")
    if finite("growth_rate", params["growth_rate"]) <= -1:
        raise ValueError("growth_rate 必须大于 -1")


def value_model(params):
    validate_params(params)
    base_revenue = finite("base_revenue", params["base_revenue"])
    years = int(params["years"])
    growth = finite("growth_rate", params["growth_rate"])
    margin_start = finite("margin_start", params["margin_start"])
    margin_target = finite("target_margin", params["target_margin"])
    tax_rate = finite("tax_rate", params["tax_rate"])
    sales_to_capital = finite("sales_to_capital", params["sales_to_capital"])
    wacc = finite("wacc", params["wacc"])
    terminal_growth = finite("terminal_growth", params["terminal_growth"])
    terminal_roic = finite("terminal_roic", params["terminal_roic"])

    rows = []
    revenue = base_revenue
    pv_explicit = 0.0
    for year in range(1, years + 1):
        previous = revenue
        revenue = previous * (1.0 + growth)
        margin = margin_start + (margin_target - margin_start) * year / years
        ebit = revenue * margin
        nopat = ebit * (1.0 - tax_rate)
        reinvestment = (revenue - previous) / sales_to_capital
        fcff = nopat - reinvestment
        discount_factor = (1.0 + wacc) ** year
        pv_fcff = fcff / discount_factor
        pv_explicit += pv_fcff
        rows.append({
            "year": year,
            "revenue": revenue,
            "operating_margin": margin,
            "nopat": nopat,
            "reinvestment": reinvestment,
            "fcff": fcff,
            "pv_fcff": pv_fcff,
        })

    next_revenue = revenue * (1.0 + terminal_growth)
    next_nopat = next_revenue * margin_target * (1.0 - tax_rate)
    terminal_reinvestment = next_nopat * terminal_growth / terminal_roic
    terminal_fcff = next_nopat - terminal_reinvestment
    terminal_value = terminal_fcff / (wacc - terminal_growth)
    pv_terminal = terminal_value / ((1.0 + wacc) ** years)
    enterprise_value = pv_explicit + pv_terminal
    return {
        "enterprise_value": enterprise_value,
        "pv_explicit": pv_explicit,
        "pv_terminal": pv_terminal,
        "terminal_value_share": pv_terminal / enterprise_value if enterprise_value else None,
        "terminal_fcff": terminal_fcff,
        "years": rows,
    }


def solve_bisection(params, variable, target, low, high, tolerance=1e-7, max_iter=200):
    if variable not in {"growth_rate", "target_margin"}:
        raise ValueError("solve.variable 只允许 growth_rate 或 target_margin")
    target = finite("target_enterprise_value", target)
    if target <= 0:
        raise ValueError("target_enterprise_value 必须为正")
    low = finite("solve.low", low)
    high = finite("solve.high", high)
    if low >= high:
        raise ValueError("solve.low 必须小于 solve.high")

    def difference(value):
        trial = copy.deepcopy(params)
        trial[variable] = value
        return value_model(trial)["enterprise_value"] - target

    f_low = difference(low)
    f_high = difference(high)
    if f_low == 0:
        return low
    if f_high == 0:
        return high
    if f_low * f_high > 0:
        raise ValueError("求解区间没有包围目标价值；请调整 low/high")

    for _ in range(int(max_iter)):
        middle = (low + high) / 2.0
        f_mid = difference(middle)
        if abs(f_mid) <= tolerance * max(1.0, abs(target)) or abs(high - low) <= tolerance:
            return middle
        if f_low * f_mid <= 0:
            high = middle
            f_high = f_mid
        else:
            low = middle
            f_low = f_mid
    raise ValueError("bisection 未在 max_iter 内收敛")


def compute(data):
    params = copy.deepcopy(data.get("params") or {})
    base = value_model(params)
    result = {"base_case": base, "assumptions": params}

    target = data.get("target_enterprise_value")
    solve = data.get("solve")
    if target is not None and solve:
        solved = solve_bisection(
            params, str(solve["variable"]), target,
            solve["low"], solve["high"],
            solve.get("tolerance", 1e-7), solve.get("max_iter", 200),
        )
        solved_params = copy.deepcopy(params)
        solved_params[str(solve["variable"])] = solved
        result["reverse_solve"] = {
            "variable": solve["variable"],
            "solved_value": solved,
            "target_enterprise_value": float(target),
            "model_at_solution": value_model(solved_params),
        }

    sensitivity = {}
    for variable, values in (data.get("sensitivities") or {}).items():
        if variable not in {"wacc", "growth_rate", "target_margin", "terminal_growth"}:
            raise ValueError("不支持的 sensitivity 变量: %s" % variable)
        rows = []
        for value in values:
            trial = copy.deepcopy(params)
            trial[variable] = float(value)
            rows.append({
                variable: float(value),
                "enterprise_value": value_model(trial)["enterprise_value"],
            })
        sensitivity[variable] = rows
    if sensitivity:
        result["sensitivities"] = sensitivity

    grid = data.get("grid")
    if grid:
        rows = []
        for growth in grid.get("growth_rates", []):
            for margin in grid.get("target_margins", []):
                trial = copy.deepcopy(params)
                trial["growth_rate"] = float(growth)
                trial["target_margin"] = float(margin)
                value = value_model(trial)["enterprise_value"]
                row = {
                    "growth_rate": float(growth),
                    "target_margin": float(margin),
                    "enterprise_value": value,
                }
                if target is not None:
                    row["value_gap"] = value - float(target)
                rows.append(row)
        result["iso_value_grid"] = rows
    return result


def self_test():
    params = {
        "base_revenue": 1000, "years": 5, "growth_rate": 0.08,
        "margin_start": 0.12, "target_margin": 0.16, "tax_rate": 0.25,
        "sales_to_capital": 2.0, "wacc": 0.10,
        "terminal_growth": 0.03, "terminal_roic": 0.12,
    }
    target = value_model(params)["enterprise_value"]
    solved = solve_bisection(params, "growth_rate", target, 0.0, 0.20)
    if abs(solved - 0.08) > 1e-5:
        raise AssertionError((target, solved))
    higher_wacc = copy.deepcopy(params)
    higher_wacc["wacc"] = 0.11
    if value_model(higher_wacc)["enterprise_value"] >= target:
        raise AssertionError("higher WACC should reduce value")
    emit("SELF_TEST_PASS")


def main(argv=None):
    parser = argparse.ArgumentParser(description="运行反向 DCF、敏感性和二维等价值网格。")
    parser.add_argument("input_json", nargs="?")
    parser.add_argument("--output")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        self_test()
        return 0
    if not args.input_json or not args.output:
        parser.error("需要 input_json 和 --output，或使用 --self-test")
    try:
        data = json.loads(Path(args.input_json).read_text(encoding="utf-8"))
        result = compute(data)
    except Exception as exc:
        emit("[错误] %s" % exc)
        return 1
    payload = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
    Path(args.output).write_text(payload + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
