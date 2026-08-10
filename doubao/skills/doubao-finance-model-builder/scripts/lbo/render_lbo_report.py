#!/usr/bin/env python3
"""Optionally render a supplemental Chinese LBO report from engine output.

The default user-facing deliverable is the audited Excel workbook. Run this
renderer only when the user explicitly requests a separate document.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def num(value: Any, decimals: int = 1) -> str:
    return "NA" if value is None else f"{float(value):,.{decimals}f}"


def pct(value: Any) -> str:
    return "NA" if value is None else f"{float(value):.1%}"


def warning_zh(value: str) -> str:
    raw = value.removeprefix("[INCOMPLETE] ")
    translations = {
        "At least one exit multiple exceeds the entry multiple; do not use it as Base without evidence.": "至少一个退出倍数高于进入倍数；没有证据时不得作为基准情景。",
        "No management_case supplied; add an operating improvement comparison when Base returns are impaired or near the equity cliff.": "未提供经营改善情景；当基准回报受损或接近股权归零临界点时必须补充。",
        "provenance must be an object": "来源台账必须为对象。",
        "provenance.sources must be a non-empty array": "来源台账必须包含至少一条来源。",
        "provenance.field_sources.entry must reference real source IDs": "进入估值字段必须映射到真实来源ID。",
        "provenance.field_sources.operating_case must reference real source IDs": "经营情景字段必须映射到真实来源ID。",
        "provenance.field_sources.debt_terms must reference real source IDs": "债务条款字段必须映射到真实来源ID。",
        "provenance.field_sources.exit must reference real source IDs": "退出假设字段必须映射到真实来源ID。",
        "基准回报受损或接近股权归零，但未提供经营改善量化情景": "基准回报受损或接近股权归零，但未提供经营改善量化情景。",
    }
    if raw.startswith("duplicate provenance source_id:"):
        return "来源ID重复：" + raw.split(":", 1)[1].strip()
    if raw.startswith("provenance.sources[") and raw.endswith(".source_id is required"):
        return "来源台账存在缺失的来源ID。"
    return translations.get(raw, raw)


def select_exit(result: dict[str, Any], exit_year: int | None, exit_multiple: float | None) -> dict[str, Any]:
    rows = result.get("exit_results", [])
    if not rows:
        raise ValueError("result has no exit_results")
    years = sorted({int(row["exit_year"]) for row in rows})
    multiples = sorted({float(row["exit_multiple"]) for row in rows})
    chosen_year = exit_year if exit_year is not None else (5 if 5 in years else years[len(years) // 2])
    chosen_multiple = exit_multiple if exit_multiple is not None else multiples[len(multiples) // 2]
    match = next(
        (
            row for row in rows
            if int(row["exit_year"]) == chosen_year
            and abs(float(row["exit_multiple"]) - chosen_multiple) <= 1e-9
        ),
        None,
    )
    if match is None:
        raise ValueError("requested exit year/multiple is not in result grid")
    return match


def render(result: dict[str, Any], exit_year: int | None = None, exit_multiple: float | None = None) -> str:
    selected = select_exit(result, exit_year, exit_multiple)
    bridge = next(
        item for item in result.get("return_bridge", [])
        if item["exit_year"] == selected["exit_year"]
        and abs(item["exit_multiple"] - selected["exit_multiple"]) <= 1e-9
    )
    company = result.get("company", {})
    currency = company.get("currency", "")
    status_code = result.get("model_status_code", "INCOMPLETE")
    status_zh = result.get("model_status", "未完成")
    lines = [
        f"# {company.get('name', company.get('ticker', '目标公司'))} LBO回报分析",
        "",
        f"> 模型状态：{status_zh}（{status_code}）",
        "",
        "## 结论摘要",
        "",
        *( [
            f"- 退出年份：第{selected['exit_year']}年；退出倍数：{num(selected['exit_multiple'], 2)}x。",
            f"- 退出企业价值：{num(selected['enterprise_value'])}；退出股权价值：{num(selected['equity_value'])} {currency}。",
            f"- 财务投资人利润：{num(selected['profit'])}；投资回报倍数（MOIC）：{num(selected['moic'], 2)}x；内部收益率（XIRR）：{pct(selected['xirr'])}。",
        ] if status_code == "PASS" else ["- 质量门未通过，不输出财务投资人利润、MOIC或XIRR结论；以下仅保留假设和债务底稿。"] ),
        "",
        "## 关键假设清单",
        "",
        "| 假设 | 数值或处理 |",
        "|---|---|",
    ]
    if status_code != "PASS":
        lines.extend(["## 阻断事项", ""])
        lines.extend(f"- {warning_zh(item)}" for item in result.get("blocking_issues", []))
        lines.append("")
    assumption_labels = {
        "ebitda_growth": "EBITDA增长",
        "depreciation_amortization": "折旧摊销",
        "depreciation_tax_shield": "折旧税盾",
        "capex": "资本开支",
        "working_capital": "营运资本",
        "cash_taxes": "现金税",
        "refinancing": "再融资",
    }
    for key, value in result.get("assumption_ledger", {}).items():
        lines.append(f"| {assumption_labels.get(key, key)} | {value} |")

    su = result.get("sources_and_uses", {})
    lines.extend([
        "",
        "## 交易资金来源与用途",
        "",
        f"- 总用途：{num(su.get('total_uses'))}；总来源：{num(su.get('total_sources'))}；差额：{num(su.get('balance_check'), 4)}。",
        f"- 财务投资人初始股权投入：{num(su.get('sponsor_equity'))}。",
        "",
        "## 债务偿还与流动性",
        "",
        "| 年份 | EBITDA | 现金利息 | 期末债务 | 期末现金 | 期末净债务 | 流动性缺口 |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ])
    for row in result.get("annual_debt_schedule", []):
        lines.append(
            f"| {row['year']} | {num(row['ebitda'])} | {num(row['cash_interest'])} | "
            f"{num(row['ending_debt'])} | {num(row['ending_cash'])} | {num(row['ending_net_debt'])} | {num(row['liquidity_shortfall'])} |"
        )

    lines.extend([
        "",
        "## 回报来源量化",
        "",
        "| 回报来源 | 对股权价值变化贡献 | 占股权价值变化比例 |",
        "|---|---:|---:|",
    ])
    labels = {
        "ebitda_growth": "EBITDA增长",
        "multiple_change": "退出倍数变化",
        "net_debt_paydown": "净债务偿还",
        "debt_like_change": "少数股东及其他类债务变化",
        "exit_fee": "退出费用",
    }
    amounts = {
        "ebitda_growth": bridge.get("ebitda_growth_contribution"),
        "multiple_change": bridge.get("multiple_change_contribution"),
        "net_debt_paydown": bridge.get("net_debt_paydown_contribution"),
        "debt_like_change": bridge.get("debt_like_change_contribution"),
        "exit_fee": bridge.get("exit_fee_contribution"),
    }
    percentages = bridge.get("contribution_pct_of_equity_change", {})
    for key in labels:
        lines.append(f"| {labels[key]} | {num(amounts[key])} | {pct(percentages.get(key))} |")
    lines.extend([
        f"| 合计股权价值变化 | {num(bridge.get('equity_value_change'))} | 100.0% |",
        "",
    ])

    comparison = result.get("management_case_comparison")
    if comparison and status_code == "PASS":
        lines.extend([
            "## 经营改善量化对比",
            "",
            f"对比情景：{comparison.get('name')}；在相同第{comparison['exit_year']}年和{num(comparison['exit_multiple'], 2)}x退出倍数下完整重跑债务计划。",
            "",
            "| 指标 | 基准情景 | 经营改善情景 | 改善幅度 |",
            "|---|---:|---:|---:|",
            f"| 退出EBITDA | {num(comparison['base']['exit_ebitda'])} | {num(comparison['management']['exit_ebitda'])} | {num(comparison['management']['exit_ebitda'] - comparison['base']['exit_ebitda'])} |",
            f"| 退出企业价值 | {num(comparison['base']['enterprise_value'])} | {num(comparison['management']['enterprise_value'])} | {num(comparison['delta']['enterprise_value'])} |",
            f"| 退出股权价值 | {num(comparison['base']['equity_value'])} | {num(comparison['management']['equity_value'])} | {num(comparison['delta']['equity_value'])} |",
            f"| MOIC | {num(comparison['base']['moic'], 2)}x | {num(comparison['management']['moic'], 2)}x | {num(comparison['delta']['moic'], 2)}x |",
            f"| XIRR | {pct(comparison['base']['xirr'])} | {pct(comparison['management']['xirr'])} | {pct(comparison['delta']['xirr'])} |",
            "",
        ])

    lines.extend(["## 模型警告", ""])
    warnings = result.get("warnings", [])
    lines.extend(f"- {warning_zh(item)}" for item in warnings) if warnings else lines.append("- 无计算层警告。")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="将LBO引擎结果渲染为中文报告")
    parser.add_argument("result", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--exit-year", type=int)
    parser.add_argument("--exit-multiple", type=float)
    args = parser.parse_args()
    result = json.loads(args.result.read_text(encoding="utf-8"))
    result_hash = hashlib.sha256(args.result.read_bytes()).hexdigest()
    rendered = render(result, args.exit_year, args.exit_multiple).rstrip() + f"\n\n<!-- CALCULATED_SHA256:{result_hash} -->\n"
    args.output.write_text(rendered, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
