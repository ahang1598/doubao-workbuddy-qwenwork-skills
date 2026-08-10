#!/usr/bin/env python3
"""将 DCF 计算结果渲染为中文 Markdown 报告。"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


SCENARIO_ZH = {"bear": "悲观", "base": "基准", "bull": "乐观"}
CURRENCY_ZH = {"CNY": "人民币", "HKD": "港元", "USD": "美元"}
UNITS_ZH = {"million": "百万元", "billion": "十亿元", "thousand": "千元", "unit": "元"}


def pct(value: float | None) -> str:
    return "缺失（NA）" if value is None else f"{value:.1%}"


def num(value: float | None, decimals: int = 1) -> str:
    return "缺失（NA）" if value is None else f"{value:,.{decimals}f}"


def scenario_zh(name: str) -> str:
    return SCENARIO_ZH.get(name.lower(), name)


def currency_units_zh(currency: Any, units: Any) -> str:
    currency_text = CURRENCY_ZH.get(str(currency).upper(), str(currency))
    units_text = UNITS_ZH.get(str(units).lower(), str(units))
    return f"{currency_text}（{currency}）/{units_text}"


def warning_zh(text: str) -> str:
    result = text
    for english, chinese in SCENARIO_ZH.items():
        if result.lower().startswith(f"{english}："):
            result = chinese + result[len(english):]
            break
        if result.lower().startswith(f"{english}:"):
            result = chinese + "：" + result[len(english) + 1:].lstrip()
            break
    return result


def render(payload: dict[str, Any], calculated: dict[str, Any], validation: dict[str, Any] | None = None) -> str:
    meta = calculated.get("meta", payload.get("meta", {}))
    base_name = calculated["base_scenario"]
    base = calculated["scenarios"][base_name]
    bridge = base["equity_bridge"]
    price = bridge.get("current_share_price_equivalent", bridge.get("current_share_price"))
    upside = base["per_share_value"] / price - 1.0 if price not in (None, 0) else None
    status_code = (validation or {}).get("model_status_code", "INCOMPLETE")
    status_zh = (validation or {}).get("model_status", "未完成")
    lines = [
        f"# {meta.get('company', '目标公司')}现金流折现（DCF）估值",
        "",
        "## 结论摘要",
        "",
        f"- 模型状态：**{status_zh}（{status_code}）**。",
        f"- 证券：{meta.get('ticker', '缺失（NA）')}；估值基准日：{meta.get('valuation_date', '缺失（NA）')}；币种/单位：{currency_units_zh(meta.get('currency', '缺失（NA）'), meta.get('units', ''))}。",
        f"- {'基准情景每股价值：**' + num(base['per_share_value'], 2) + '**；当前价格：' + num(price, 2) + '；隐含上涨/下跌空间：' + pct(upside) + '。' if status_code == 'PASS' else '质量门未通过，不输出目标价或上涨/下跌空间；下方数值仅为待修复计算底稿。'}",
        f"- 企业价值（EV）：{num(base['enterprise_value'])}；普通股权益价值：{num(base['equity_value'])}（仅在状态为PASS时构成估值结论）。",
        f"- 加权平均资本成本（WACC）：{pct(base['wacc'])}；永续增长率（g）：{pct(base['terminal_growth'])}；终值（TV）占企业价值：{pct(base['terminal_value_share_of_ev'])}。",
        f"- 数据等级：{meta.get('data_grade', '缺失（NA）')}。估值结果是条件化区间，不代表价格预测的确定性。",
        "",
        "## 术语与口径",
        "",
        "- 现金流折现（Discounted Cash Flow，DCF）：把未来现金流按资本成本折算为当前价值。",
        "- 企业自由现金流（Free Cash Flow to Firm，FCFF）：在向债权人和股东分配资金前，经营资产可提供给全部资本提供者的现金流。",
        "- 息税前利润（Earnings Before Interest and Taxes，EBIT）：扣除利息和所得税前的经营利润，用于隔离融资结构影响。",
        "- 税后经营利润（Net Operating Profit After Tax，NOPAT）：不考虑融资结构时，经营利润扣除经营相关税负后的利润。",
        "- 折旧与摊销（Depreciation and Amortization，D&A）：长期资产成本的会计分摊，通常作为非现金费用加回。",
        "- 资本性支出（Capital Expenditures，Capex）：取得或维护长期经营资产的现金投入。",
        "- 经营性净营运资本增加（Change in Net Working Capital，ΔNWC）：经营性净营运资本的增加额，增加通常占用现金。",
        "- 加权平均资本成本（Weighted Average Cost of Capital，WACC）：股权和债务资金要求回报率按目标资本结构加权后的折现率。",
        "- 企业价值（Enterprise Value，EV）：经营资产对债权人、股东等全部资本提供者的价值。",
        "- 终值（Terminal Value，TV）：显性预测期结束后全部后续现金流在预测期末的价值。",
        "- 永续增长率（Perpetual Growth Rate，g）：公司进入稳态后现金流长期持续增长的名义速率。",
        "- 年份后的E（Estimate，预测值）：表示该期间数据为模型预测而非已报告历史值。",
        "",
        "## 情景估值",
        "",
        "| 情景 | 加权平均资本成本（WACC） | 永续增长率（g） | 企业价值（EV） | 普通股权益价值 | 每股价值 | 终值占比 |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for name, result in calculated["scenarios"].items():
        lines.append(f"| {scenario_zh(name)} | {pct(result['wacc'])} | {pct(result['terminal_growth'])} | {num(result['enterprise_value'])} | {num(result['equity_value'])} | {num(result['per_share_value'], 2)} | {pct(result['terminal_value_share_of_ev'])} |")
    lines.extend([
        "",
        "## 基准情景现金流",
        "",
        "下表按上述口径，从税后经营利润加回折旧与摊销，再扣除资本性支出和经营性净营运资本增加，得到企业自由现金流。",
        "",
        "| 期间 | 收入 | 息税前利润率（EBIT利润率） | 税后经营利润（NOPAT） | 折旧与摊销（D&A） | 资本性支出（Capex） | 经营性净营运资本增加（ΔNWC） | 企业自由现金流（FCFF） | 折现后FCFF |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ])
    for row in base["forecast"]:
        lines.append(f"| {row['period']} | {num(row['revenue'])} | {pct(row['ebit_margin'])} | {num(row['nopat'])} | {num(row['da'])} | {num(row['capex'])} | {num(row['delta_nwc'])} | {num(row['fcff'])} | {num(row['pv_fcff'])} |")
    lines.extend([
        "",
        "## 企业价值到普通股权益价值桥接",
        "",
        f"企业价值（EV）为 {num(base['enterprise_value'])}，加可扣现金及非经营资产 {num(sum(bridge.get(k, 0) for k in ('cash','non_operating_investments','associates')))}，扣除债务及其他非普通股索取权 {num(sum(bridge.get(k, 0) for k in ('debt','lease_liabilities','unfunded_pension','preferred_stock','minority_interest','other_claims')))}，得到普通股权益价值 {num(base['equity_value'])}。完全稀释股份数为 {num(bridge['diluted_shares'])}。",
        "",
        "## 反向现金流折现",
        "",
        "反向现金流折现（Reverse DCF）从当前市值反推市场隐含的增长、利润率或现金流假设。",
        "",
    ])
    reverse = calculated.get("reverse_dcf")
    if reverse and reverse.get("implied_terminal_growth") is not None:
        lines.append(f"当前价格对应的隐含企业价值为 {num(reverse['target_enterprise_value'])}；在其他基准假设不变时，隐含永续增长率约为 {pct(reverse['implied_terminal_growth'])}。该结果用于检查市场预期，不是独立目标价。")
    else:
        reason = reverse.get("reason") if reverse else "未提供当前股价"
        lines.append(f"未形成有效的单变量反向现金流折现结果：{reason}。")
    lines.extend(["", "## 模型警告", ""])
    warnings = calculated.get("warnings", [])
    if warnings:
        lines.extend(f"- {warning_zh(warning)}" for warning in warnings)
    else:
        lines.append("- 未发现计算层面的高优先级警告；仍需结合来源台账和经营假设进行投资判断。")
    lines.extend([
        "",
        "## 失效条件",
        "",
        "正式报告必须补充至少三项可观察条件，分别覆盖收入或份额、利润率或现金转化、资本成本或终值，并写明阈值、时间点、来源与触发后的重估动作。",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="将DCF结果渲染为中文Markdown报告")
    parser.add_argument("input", type=Path)
    parser.add_argument("calculated", type=Path)
    parser.add_argument("--validation", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    calculated = json.loads(args.calculated.read_text(encoding="utf-8"))
    validation = json.loads(args.validation.read_text(encoding="utf-8")) if args.validation else None
    args.output.parent.mkdir(parents=True, exist_ok=True)
    calculated_hash = hashlib.sha256(args.calculated.read_bytes()).hexdigest()
    rendered = render(payload, calculated, validation).rstrip() + f"\n\n<!-- CALCULATED_SHA256:{calculated_hash} -->\n"
    args.output.write_text(rendered, encoding="utf-8")


if __name__ == "__main__":
    main()
