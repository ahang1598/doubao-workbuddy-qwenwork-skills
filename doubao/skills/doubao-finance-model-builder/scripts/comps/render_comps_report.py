#!/usr/bin/env python3
"""Optionally render calculation JSON into a supplemental Markdown report.

The default user-facing deliverable is the audited Excel workbook. Run this
renderer only when the user explicitly requests a separate document.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any


MODES = {"decision-brief", "full-report", "audit-pack"}
METRIC_LABELS = {
    "ltm_ev_revenue": "最近十二个月企业价值/营业收入倍数（LTM EV/Revenue）",
    "ntm_ev_revenue": "未来十二个月企业价值/营业收入倍数（NTM EV/Revenue）",
    "ltm_ev_ebitda": "最近十二个月企业价值/息税折旧摊销前利润倍数（LTM EV/EBITDA）",
    "ntm_ev_ebitda": "未来十二个月企业价值/息税折旧摊销前利润倍数（NTM EV/EBITDA）",
    "ltm_pe": "最近十二个月市盈率（LTM P/E）",
    "ntm_pe": "未来十二个月市盈率（NTM P/E）",
    "ltm_ps": "最近十二个月市销率（LTM P/S）",
    "ntm_ps": "未来十二个月市销率（NTM P/S）",
    "ltm_fcf_yield": "最近十二个月自由现金流收益率（LTM FCF Yield）",
    "ntm_fcf_yield": "未来十二个月自由现金流收益率（NTM FCF Yield）",
    "price_to_book": "市净率（P/B）",
    "ltm_roe": "最近十二个月净资产收益率（LTM ROE）",
}
METRIC_GLOSSARY = {
    "ltm_ev_revenue": "企业价值除以最近十二个月营业收入，用于观察市场给予每单位历史收入的估值。",
    "ntm_ev_revenue": "企业价值除以估值基准日当时预测的未来十二个月营业收入。",
    "ltm_ev_ebitda": "企业价值除以最近十二个月息税折旧摊销前利润，企业价值与利润口径必须匹配。",
    "ntm_ev_ebitda": "企业价值除以估值基准日当时预测的未来十二个月息税折旧摊销前利润。",
    "ltm_pe": "完全稀释股权价值除以最近十二个月归属于普通股股东的净利润。",
    "ntm_pe": "完全稀释股权价值除以估值基准日当时预测的未来十二个月归属于普通股股东的净利润。",
    "ltm_ps": "完全稀释股权价值除以最近十二个月营业收入；资本结构差异显著时仅作辅助指标。",
    "ntm_ps": "完全稀释股权价值除以估值基准日当时预测的未来十二个月营业收入；资本结构差异显著时仅作辅助指标。",
    "ltm_fcf_yield": "最近十二个月自由现金流除以完全稀释股权价值；收益率越高通常对应估值越低。",
    "ntm_fcf_yield": "预测未来十二个月自由现金流除以完全稀释股权价值；收益率越高通常对应估值越低。",
    "price_to_book": "股价除以完成股息口径匹配后的每股净资产。",
    "ltm_roe": "最近十二个月归属于普通股股东的净利润除以期间平均普通股权益。",
}
CLASSIFICATION_LABELS = {
    "Target": "目标公司",
    "Core": "核心可比公司",
    "Secondary": "辅助可比公司",
    "Excluded": "排除公司",
}
ROLE_LABELS = {
    "Commercial Core": "商业核心",
    "Stage Core": "阶段核心",
    "Mature Boundary": "成熟边界",
    "Pipeline/Model Boundary": "管线/模式边界",
    "Global/Scale Boundary": "全球/规模边界",
    "Excluded": "排除",
}
QUALITY_LABELS = {"Pass": "通过", "Limited": "受限", "Fail": "不通过"}
MODE_LABELS = {
    "decision-brief": "决策摘要",
    "full-report": "完整报告",
    "audit-pack": "审计包",
}
CURRENCY_LABELS = {"CNY": "人民币", "HKD": "港元", "USD": "美元"}
UNIT_LABELS = {
    "millions": "百万元",
    "million": "百万元",
    "billions": "十亿元",
    "billion": "十亿元",
}
FUNDAMENTAL_LABELS = {
    "ltm_revenue": "最近十二个月营业收入",
    "ntm_revenue": "未来十二个月营业收入",
    "ltm_ebitda": "最近十二个月息税折旧摊销前利润（EBITDA）",
    "ntm_ebitda": "未来十二个月息税折旧摊销前利润（EBITDA）",
    "ltm_net_income": "最近十二个月归母净利润",
    "ntm_net_income": "未来十二个月归母净利润",
    "ltm_fcf": "最近十二个月自由现金流（FCF）",
    "ntm_fcf": "未来十二个月自由现金流（FCF）",
    "adjusted_bvps": "调整后每股净资产（BVPS）",
    "adjusted BVPS": "调整后每股净资产（BVPS）",
}


class RenderError(ValueError):
    pass


def finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def number(value: Any, decimals: int = 2) -> str:
    if not finite(value):
        return "NA"
    return f"{float(value):,.{decimals}f}"


def currency_label(value: Any) -> str:
    text = str(value or "").upper()
    return CURRENCY_LABELS.get(text, text)


def unit_label(value: Any) -> str:
    text = str(value or "")
    return UNIT_LABELS.get(text.lower(), text)


def classification_label(value: Any) -> str:
    return CLASSIFICATION_LABELS.get(str(value), str(value or "数据缺失（NA）"))


def company_classification_label(company: dict[str, Any]) -> str:
    value = company.get("classification")
    assessment = company.get("peer_assessment") or {}
    if value == "Core" and assessment.get("eligible_for_core_statistics") is not True:
        return "核心候选（未进入主统计）"
    return classification_label(value)


def role_label(value: Any) -> str:
    return ROLE_LABELS.get(str(value), str(value or "数据缺失（NA）"))


def quality_label(value: Any) -> str:
    return QUALITY_LABELS.get(str(value), str(value or "数据缺失（NA）"))


def metric_value(metric: str, value: Any) -> str:
    if not finite(value):
        return "NM"
    if metric.endswith("yield") or metric == "ltm_roe":
        return f"{float(value) * 100:.1f}%"
    return f"{float(value):.2f}×"


def select_primary_metric(payload: dict[str, Any], target: dict[str, Any]) -> str:
    profile = payload.get("meta", {}).get("valuation_profile")
    if isinstance(profile, dict):
        primary = profile.get("primary_metrics")
        if isinstance(primary, list):
            for metric in primary:
                if isinstance(metric, str) and target.get("metrics", {}).get(metric) is not None:
                    return metric
    for metric in (
        "ntm_ev_revenue",
        "ntm_ps",
        "ntm_ev_ebitda",
        "ntm_pe",
        "price_to_book",
        "ltm_ev_revenue",
        "ltm_ps",
        "ltm_ev_ebitda",
        "ltm_pe",
    ):
        if target.get("metrics", {}).get(metric) is not None:
            return metric
    raise RenderError("No valid primary valuation metric is available for the target")


def target_company(payload: dict[str, Any]) -> dict[str, Any]:
    ticker = payload.get("meta", {}).get("target_ticker")
    matches = [company for company in payload.get("companies", []) if company.get("ticker") == ticker]
    if len(matches) != 1:
        raise RenderError("target_ticker must match exactly one calculated company")
    return matches[0]


def score_text(company: dict[str, Any]) -> str:
    assessment = company.get("peer_assessment")
    if not isinstance(assessment, dict):
        return "NA"
    scores = assessment.get("scores", {})
    order = ("business_overlap", "business_model", "revenue_structure", "market_cap_band")
    if any(not finite(scores.get(field)) for field in order):
        return "NA"
    components = "/".join(f"{float(scores[field]):g}" for field in order)
    return f"{components} → {float(assessment.get('weighted_score', 0)):.1f}"


def core_observations(payload: dict[str, Any], metric: str) -> list[float]:
    return [
        float(company["metrics"][metric])
        for company in payload.get("companies", [])
        if company.get("classification") == "Core"
        and (company.get("peer_assessment") or {}).get("eligible_for_core_statistics") is True
        and finite(company.get("metrics", {}).get(metric))
    ]


def render_card(
    payload: dict[str, Any], target: dict[str, Any], metric: str, lines: list[str]
) -> None:
    meta = payload.get("meta", {})
    stats = payload.get("core_statistics", {}).get(metric, {})
    observations = core_observations(payload, metric)
    count = int(stats.get("count", 0) or 0)
    robust = bool(stats.get("robust", count >= 3))
    implied = payload.get("implied_share_values", {}).get(metric)

    model_pass = meta.get("model_status_code") == "PASS"
    if model_pass and robust and isinstance(implied, dict):
        fair_range = f"{number(implied.get('low'))}–{number(implied.get('high'))} {currency_label(meta.get('currency'))}/股"
    elif robust:
        fair_range = "未输出（分析质量门未通过）"
    else:
        fair_range = "数据缺失（NA；核心可比公司样本不足，不输出稳健区间）"
    if robust:
        peer_anchor = (
            f"中位数 {metric_value(metric, stats.get('median'))}；"
            f"第75百分位数 {metric_value(metric, stats.get('p75'))}"
        )
    elif observations:
        peer_anchor = (
            f"观察值 {metric_value(metric, min(observations))}–"
            f"{metric_value(metric, max(observations))}；非稳健"
        )
    else:
        peer_anchor = "数据缺失（NA）"

    lines.extend(
        [
            "## 投资判断卡",
            "",
            "| 判断项 | 数值或状态 |",
            "|---|---|",
            f"| 基准日价格 | {number(target.get('price'))} {currency_label(meta.get('currency'))}/股（{target.get('price_date', '数据缺失（NA）')}） |",
            f"| 主估值锚 | {METRIC_LABELS.get(metric, metric)} |",
            f"| 当前交易倍数 | {metric_value(metric, target.get('metrics', {}).get(metric))} |",
            f"| 核心可比公司基准 | {peer_anchor} |",
            f"| 核心可比公司隐含价值 | {fair_range} |",
            f"| 数据等级 | {meta.get('data_tier', 'D')} 级 |",
            f"| 核心可比公司有效样本 | {count}；{'稳健' if robust else '低稳健性'} |",
            "",
            "> 注：NA 表示数据缺失；NM 表示指标无经济意义。",
            "",
        ]
    )


def render_peers(payload: dict[str, Any], metric: str, lines: list[str]) -> None:
    lines.extend(
        [
            "## 同行定位",
            "",
            "四维分顺序：业务重叠/商业模式/收入结构/市值区间。",
            "",
            "| 公司 | 分类 | 角色 | 四维分 | 数据质量 | 主倍数 |",
            "|---|---|---|---:|---|---:|",
        ]
    )
    for company in payload.get("companies", []):
        if company.get("classification") == "Target":
            continue
        assessment = company.get("peer_assessment") or {}
        lines.append(
            "| {name} ({ticker}) | {classification} | {role} | {score} | {quality} | {multiple} |".format(
                name=company.get("name", company.get("ticker")),
                ticker=company.get("ticker", "NA"),
                classification=company_classification_label(company),
                role=role_label(company.get("peer_role")),
                score=score_text(company),
                quality=quality_label(assessment.get("data_quality")),
                multiple=metric_value(metric, company.get("metrics", {}).get(metric)),
            )
        )
    lines.append("")


def render_ev_bridge(target: dict[str, Any], currency: str, unit: str, lines: list[str]) -> None:
    ev = target.get("ev_bridge") or {}
    lines.extend(
        [
            "## 目标公司企业价值调节表",
            "",
            f"单位：{currency_label(currency)}{unit_label(unit)}",
            "",
            "| 项目 | 数值 |",
            "|---|---:|",
            f"| 完全稀释股权价值 | {number(target.get('market_cap'))} |",
            f"| 债务 | {number(ev.get('debt'))} |",
            f"| 优先股、少数股东及债务类调整 | {number(sum(float(ev.get(k, 0) or 0) for k in ('preferred_equity', 'noncontrolling_interest', 'debt_like_adjustments')))} |",
            f"| 可扣现金 | ({number(ev.get('cash'))}) |",
            f"| 可扣非经营投资 | ({number(ev.get('non_operating_investments'))}) |",
            f"| 企业价值 | **{number(target.get('enterprise_value'))}** |",
            "",
        ]
    )
    cash_bridge = target.get("cash_bridge")
    if isinstance(cash_bridge, dict):
        lines.extend(
            [
                "现金桥：",
                "",
                "| 现金项目 | 数值 |",
                "|---|---:|",
                f"| 现金及等价物 | {number(cash_bridge.get('cash_and_equivalents'))} |",
                f"| 定期存款 | {number(cash_bridge.get('term_deposits'))} |",
                f"| 短期投资 | {number(cash_bridge.get('short_term_investments'))} |",
                f"| 受限现金 | ({number(cash_bridge.get('restricted_cash'))}) |",
                f"| 经营现金准备 | ({number(cash_bridge.get('operating_cash_reserve'))}) |",
                f"| 可扣现金 | **{number(cash_bridge.get('deductible_cash'))}** |",
                "",
            ]
        )


def render_book_value_bridge(
    target: dict[str, Any], currency: str, unit: str, lines: list[str]
) -> None:
    book = target.get("book_value") or {}
    lines.extend(
        [
            "## 目标公司每股净资产与股息调节表",
            "",
            f"金额单位：{currency_label(currency)}{unit_label(unit)}；每股单位：{currency_label(currency)}/股",
            "",
            "| 项目 | 数值 |",
            "|---|---:|",
            f"| 报告普通股股东权益 | {number(book.get('common_equity'))} |",
            f"| 股息扣减 | ({number(book.get('dividend_deduction'))}) |",
            f"| 调整后普通股股东权益 | {number(book.get('adjusted_common_equity'))} |",
            f"| 每股净资产计算股本 | {number(book.get('book_value_shares'))} |",
            f"| 报告每股净资产（BVPS） | {number(book.get('reported_bvps'))} |",
            f"| 每股股息扣减 | ({number(book.get('dividend_deduction_per_share'))}) |",
            f"| 调整后每股净资产（BVPS） | **{number(book.get('adjusted_bvps'))}** |",
            "",
        ]
    )


def render_implied(payload: dict[str, Any], metric: str, lines: list[str]) -> None:
    rows = [
        row
        for row in payload.get("market_implied_fundamentals", [])
        if row.get("metric") == metric
    ]
    if not rows:
        return
    lines.extend(
        [
            "## 当前价格隐含预期",
            "",
            "| 基准 | 基准锚 | 反推指标 | 市场隐含值 | 当前值 | 差异 |",
            "|---|---:|---|---:|---:|---:|",
        ]
    )
    for row in rows:
        difference = row.get("implied_vs_current")
        difference_text = f"{float(difference) * 100:+.1f}%" if finite(difference) else "NA"
        lines.append(
            f"| {row.get('name', '基准')} | {metric_value(metric, row.get('benchmark'))} | "
            f"{FUNDAMENTAL_LABELS.get(str(row.get('implied_fundamental_field')), row.get('implied_fundamental_field', '财务指标'))} | "
            f"{number(row.get('implied_fundamental'))} | {number(row.get('current_fundamental'))} | {difference_text} |"
        )
    lines.append("")


def render_scenarios(payload: dict[str, Any], metric: str, lines: list[str]) -> None:
    scenarios = [row for row in payload.get("scenario_analysis", []) if row.get("metric") == metric]
    if not scenarios:
        return
    if metric == "price_to_book":
        lines.extend(
            [
                "## 情景",
                "",
                "| 情景 | 市净率 | 调整后每股净资产 | 隐含每股价值 |",
                "|---|---:|---:|---:|",
            ]
        )
        for row in scenarios:
            lines.append(
                f"| {row.get('name', '数据缺失（NA）')} | {metric_value(metric, row.get('anchor'))} | "
                f"{number(row.get('fundamental'))} | **{number(row.get('implied_share_value'))}** |"
            )
        lines.append("")
        return
    if metric in {"ltm_ps", "ntm_ps"}:
        revenue_label = "最近十二个月营业收入" if metric == "ltm_ps" else "未来十二个月营业收入"
        lines.extend(
            [
                "## 情景",
                "",
                f"| 情景 | 市销率 | {revenue_label} | 稀释股本 | 隐含每股价值 |",
                "|---|---:|---:|---:|---:|",
            ]
        )
        for row in scenarios:
            lines.append(
                f"| {row.get('name', '数据缺失（NA）')} | {metric_value(metric, row.get('anchor'))} | "
                f"{number(row.get('fundamental'))} | {number(row.get('diluted_shares'))} | "
                f"**{number(row.get('implied_share_value'))}** |"
            )
        lines.append("")
        return
    lines.extend(
        [
            "## 情景",
            "",
            "| 情景 | 倍数/收益率 | 财务指标 | 净债务调节值 | 稀释股本 | 隐含每股价值 |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for row in scenarios:
        lines.append(
            f"| {row.get('name', 'NA')} | {metric_value(metric, row.get('anchor'))} | "
            f"{number(row.get('fundamental'))} | {number(row.get('net_debt_bridge'))} | "
            f"{number(row.get('diluted_shares'))} | **{number(row.get('implied_share_value'))}** |"
        )
    lines.append("")


def render_sensitivity(payload: dict[str, Any], metric: str, lines: list[str]) -> None:
    spec = payload.get("sensitivity_analysis")
    if not isinstance(spec, dict) or spec.get("metric") != metric:
        return
    anchors = spec.get("anchors", [])
    rows = spec.get("rows", [])
    lines.extend(["## 二维敏感性", ""])
    raw_label = spec.get("fundamental_label") or "财务指标"
    axis_label = FUNDAMENTAL_LABELS.get(str(raw_label), str(raw_label))
    header = f"| {axis_label} | " + " | ".join(metric_value(metric, value) for value in anchors) + " |"
    divider = "|---:|" + "---:|" * len(anchors)
    lines.extend([header, divider])
    for row in rows:
        values = " | ".join(number(value) for value in row.get("share_values", []))
        lines.append(f"| {number(row.get('fundamental'))} | {values} |")
    lines.append("")
    if metric == "price_to_book":
        lines.extend(["列为市净率，行为调整后每股净资产。", ""])
    elif metric in {"ltm_ps", "ntm_ps"}:
        lines.extend(
            [
                f"列为市销率，行为营业收入；稀释股本：{number(spec.get('diluted_shares'))}。P/S 不使用净债务调节。",
                "",
            ]
        )
    else:
        lines.extend(
            [
                f"净债务调节值：{number(spec.get('net_debt_bridge'))}；稀释股本：{number(spec.get('diluted_shares'))}。",
                "",
            ]
        )


def render_full_metrics(payload: dict[str, Any], primary_metric: str, lines: list[str]) -> None:
    if primary_metric == "price_to_book":
        lines.extend(
            [
                "## 完整交易倍数",
                "",
                "| 公司 | 调整后每股净资产 | 市净率 | 最近十二个月市盈率 | 未来十二个月市盈率 | 最近十二个月净资产收益率 |",
                "|---|---:|---:|---:|---:|---:|",
            ]
        )
        for company in payload.get("companies", []):
            metrics = company.get("metrics", {})
            book = company.get("book_value", {})
            lines.append(
                f"| {company.get('name', company.get('ticker'))} | "
                f"{number(book.get('adjusted_bvps'))} | "
                f"{metric_value('price_to_book', metrics.get('price_to_book'))} | "
                f"{metric_value('ltm_pe', metrics.get('ltm_pe'))} | "
                f"{metric_value('ntm_pe', metrics.get('ntm_pe'))} | "
                f"{metric_value('ltm_roe', metrics.get('ltm_roe'))} |"
            )
        lines.append("")
        return
    lines.extend(
        [
            "## 完整交易倍数",
            "",
            "### 收入估值倍数",
            "",
            "| 公司 | 最近十二个月市销率 | 未来十二个月市销率 | 最近十二个月企业价值/营业收入 | 未来十二个月企业价值/营业收入 |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for company in payload.get("companies", []):
        metrics = company.get("metrics", {})
        lines.append(
            f"| {company.get('name', company.get('ticker'))} | "
            f"{metric_value('ltm_ps', metrics.get('ltm_ps'))} | "
            f"{metric_value('ntm_ps', metrics.get('ntm_ps'))} | "
            f"{metric_value('ltm_ev_revenue', metrics.get('ltm_ev_revenue'))} | "
            f"{metric_value('ntm_ev_revenue', metrics.get('ntm_ev_revenue'))} |"
        )
    lines.extend(
        [
            "",
            "### 盈利估值倍数",
            "",
            "| 公司 | 最近十二个月企业价值/息税折旧摊销前利润 | 未来十二个月企业价值/息税折旧摊销前利润 | 最近十二个月市盈率 | 未来十二个月市盈率 |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for company in payload.get("companies", []):
        metrics = company.get("metrics", {})
        lines.append(
            f"| {company.get('name', company.get('ticker'))} | "
            f"{metric_value('ltm_ev_ebitda', metrics.get('ltm_ev_ebitda'))} | "
            f"{metric_value('ntm_ev_ebitda', metrics.get('ntm_ev_ebitda'))} | "
            f"{metric_value('ltm_pe', metrics.get('ltm_pe'))} | "
            f"{metric_value('ntm_pe', metrics.get('ntm_pe'))} |"
        )
    lines.append("")


def render_glossary(metrics: list[str], lines: list[str]) -> None:
    unique_metrics: list[str] = []
    for metric in metrics:
        if metric in METRIC_GLOSSARY and metric not in unique_metrics:
            unique_metrics.append(metric)
    lines.extend(
        [
            "## 指标释义与口径",
            "",
            "- 最近十二个月（LTM）：截至估值基准日前最近已公开期间滚动计算的十二个月数据。",
            "- 未来十二个月（NTM）：使用估值基准日当时可得预测构造的未来十二个月数据。",
        ]
    )
    for metric in unique_metrics:
        lines.append(f"- {METRIC_LABELS[metric]}：{METRIC_GLOSSARY[metric]}")
    if any(metric in {"ltm_ps", "ntm_ps"} for metric in unique_metrics):
        lines.append(
            "- 市销率与企业价值/营业收入倍数的区别：市销率（P/S）使用完全稀释股权价值，企业价值/营业收入倍数（EV/Revenue）使用企业价值；资本结构差异明显时优先使用后者。"
        )
    lines.extend(
        [
            "- 核心可比公司：满足业务可比性、评分和数据质量门槛，并进入主统计的公司。",
            "- 数据缺失（NA）：相关数据无法可靠取得，不代表数值为零。",
            "- 指标无经济意义（NM）：分母为零、负值或该指标的经济含义失真。",
            "- 企业价值（EV）：一般行业中指完全稀释股权价值加净债务及其他优先索取权；保险市值/内含价值倍数中的 EV 指内含价值（Embedded Value），两者不得混用。",
            "",
        ]
    )


def render(payload: dict[str, Any], mode: str) -> str:
    if mode not in MODES:
        raise RenderError(f"Unsupported mode: {mode}")
    target = target_company(payload)
    metric = select_primary_metric(payload, target)
    meta = payload.get("meta", {})
    status_code = meta.get("model_status_code", "INCOMPLETE")
    analysis_summary = payload.get("analysis_summary", {})
    conclusion = analysis_summary.get("conclusion") if status_code == "PASS" else None
    lines = [
        f"# {target.get('name', target.get('ticker'))} 可比公司分析",
        "",
        f"> 模型状态：{meta.get('model_status', '未完成')}（{status_code}）；估值基准日：{meta.get('valuation_date', '数据缺失（NA）')}。",
        "",
        "## 一句话结论",
        "",
        f"> {conclusion if conclusion else '分析要件未通过质量门，不得输出推荐倍数或目标价；以下仅为计算底稿。'}",
        "",
    ]
    if status_code != "PASS":
        lines.extend(["## 阻断事项", ""])
        lines.extend(f"- {item}" for item in payload.get("blocking_issues", []))
        lines.append("")
    render_card(payload, target, metric, lines)
    render_peers(payload, metric, lines)
    if analysis_summary.get("peer_comparison"):
        lines.extend(["## 目标公司与核心同行比较", "", str(analysis_summary["peer_comparison"]), ""])
    if analysis_summary.get("premium_discount_rationale"):
        lines.extend(["## 溢折价判断", "", str(analysis_summary["premium_discount_rationale"]), ""])
    if metric == "price_to_book":
        render_book_value_bridge(
            target, str(meta.get("currency", "")), str(meta.get("unit", "")), lines
        )
    else:
        render_ev_bridge(
            target, str(meta.get("currency", "")), str(meta.get("unit", "")), lines
        )
    if status_code == "PASS":
        render_implied(payload, metric, lines)
        render_scenarios(payload, metric, lines)
        render_sensitivity(payload, metric, lines)
    else:
        lines.extend([
            "## 估值输出已阻断",
            "",
            "来源、同行分析或样本质量门未通过，因此不展示隐含每股价值、情景估值或敏感性结果。",
            "",
        ])
    if mode in {"full-report", "audit-pack"}:
        render_full_metrics(payload, metric, lines)
    if mode == "audit-pack":
        lines.extend(
            [
                "## 审计信息",
                "",
                f"- 数据等级：{meta.get('data_tier', 'D')} 级",
                f"- 来源台账记录数：{meta.get('source_count', 0)}",
                f"- 汇率记录数：{len(meta.get('fx_rates', []))}",
                f"- 输出模式：{MODE_LABELS.get(str(meta.get('output_mode', mode)), str(meta.get('output_mode', mode)))}",
                "",
            ]
        )
    warnings = payload.get("warnings", [])
    if warnings:
        lines.extend(["## 数据与计算警告", ""])
        lines.extend(f"- {warning}" for warning in warnings)
        lines.append("")
    glossary_metrics = [metric]
    if mode in {"full-report", "audit-pack"}:
        if metric == "price_to_book":
            glossary_metrics.extend(["ltm_pe", "ntm_pe", "ltm_roe"])
        else:
            glossary_metrics.extend(
                [
                    "ltm_ps",
                    "ntm_ps",
                    "ltm_ev_revenue",
                    "ntm_ev_revenue",
                    "ltm_ev_ebitda",
                    "ntm_ev_ebitda",
                    "ltm_pe",
                    "ntm_pe",
                ]
            )
    render_glossary(glossary_metrics, lines)
    return "\n".join(lines).rstrip() + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="将可比公司计算结果 JSON 渲染为中文 Markdown 报告")
    parser.add_argument("input", type=Path, help="可比公司计算结果 JSON")
    parser.add_argument("--output", type=Path, help="Markdown 报告输出路径")
    parser.add_argument("--mode", choices=sorted(MODES), help="覆盖输入文件中的输出模式")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        mode = args.mode or payload.get("meta", {}).get("output_mode", "decision-brief")
        rendered = render(payload, mode)
        calculated_hash = hashlib.sha256(args.input.read_bytes()).hexdigest()
        rendered = rendered.rstrip() + f"\n\n<!-- CALCULATED_SHA256:{calculated_hash} -->\n"
    except (OSError, json.JSONDecodeError, RenderError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 2
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
