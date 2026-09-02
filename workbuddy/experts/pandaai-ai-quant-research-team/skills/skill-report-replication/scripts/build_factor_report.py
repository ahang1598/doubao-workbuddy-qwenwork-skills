#!/usr/bin/env python
"""Build a standalone factor validation HTML report from a JSON summary.

The generated report follows references/output_contract.md and the section
keywords checked by scripts/quality_gate_check.py.
"""

from __future__ import annotations

import argparse
import base64
import html
import json
from pathlib import Path
from typing import Any


REQUIRED_CHARTS = [
    ("03_factor_validation/charts/01_ie_distribution.png", "Factor Distribution", "data/ie_factor_matrix.csv"),
    ("03_factor_validation/charts/02_ic_series.png", "IC Time Series", "data/ic_series.csv"),
    ("03_factor_validation/charts/03_is_oos_ic_comparison.png", "IS vs OOS IC Comparison", "data/ic_series.csv"),
    (
        "03_factor_validation/charts/04_cumulative_nav_equal_weight.png",
        "Equal-Weight Validation NAV",
        "data/portfolio_returns_ew_full.csv",
    ),
    (
        "03_factor_validation/charts/05_cumulative_nav_strategy_direction.png",
        "Strategy-Direction Validation NAV",
        "data/portfolio_returns_dir_full.csv",
    ),
    ("03_factor_validation/charts/06_drawdown.png", "Drawdown", "data/portfolio_returns_dir_full.csv"),
]

CHART_EXPLANATIONS = {
    "01_ie_distribution.png": (
        "Shows the latest cross-sectional factor values by instrument.",
        "Read higher/lower bars as stronger/weaker exposure to the replicated factor. Large cross-sectional separation is needed for useful sorting.",
    ),
    "02_ic_series.png": (
        "Shows IC and Rank IC through time.",
        "Read values away from zero as stronger predictive direction. The OOS region matters more than the in-sample region.",
    ),
    "03_is_oos_ic_comparison.png": (
        "Compares average IC / Rank IC in-sample and out-of-sample.",
        "If OOS weakens, flips sign, or collapses toward zero, the factor conclusion should be downgraded.",
    ),
    "04_cumulative_nav_equal_weight.png": (
        "Shows theoretical equal-weight long-short factor-validation NAV.",
        "This is a close/close validation curve, not an actual BACKTEST account equity curve.",
    ),
    "05_cumulative_nav_strategy_direction.png": (
        "Shows strategy-direction or BACKTEST actual/equal-lot NAV.",
        "Explain whether it comes from signal-log close/close validation or from BACKTEST report equity, and why it differs from the equal-weight curve.",
    ),
    "06_drawdown.png": (
        "Shows drawdown derived from NAV.",
        "Drawdown equals NAV / rolling max(NAV) - 1. It is a risk chart, not a duplicated NAV curve.",
    ),
    "07_walkforward.png": (
        "Shows performance by walk-forward window.",
        "Large window-to-window differences indicate regime dependence or weak robustness.",
    ),
    "08_cost_sensitivity.png": (
        "Shows how annualized return changes as rebalance cost assumptions increase.",
        "A fast decline means the strategy is sensitive to execution costs.",
    ),
}


def esc(value: Any) -> str:
    return html.escape("" if value is None else str(value))


def fmt_metric(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.4f}"
    return esc(value)


def table_from_dict(data: dict[str, Any]) -> str:
    if not data:
        return "<p class=\"muted\">未提供或未执行。</p>"
    rows = [f"<tr><th>{esc(key)}</th><td>{fmt_metric(value)}</td></tr>" for key, value in data.items()]
    return "<table><tbody>" + "\n".join(rows) + "</tbody></table>"


def table_from_rows(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "<p class=\"muted\">未提供或未执行。</p>"
    columns = list(rows[0].keys())
    header = "".join(f"<th>{esc(col)}</th>" for col in columns)
    body = []
    for row in rows:
        body.append("<tr>" + "".join(f"<td>{fmt_metric(row.get(col))}</td>" for col in columns) + "</tr>")
    return f"<table><thead><tr>{header}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def section_table_or_note(value: Any, empty_note: str = "未提供或未执行。") -> str:
    if isinstance(value, dict) and value:
        return table_from_dict(value)
    if isinstance(value, list) and value:
        if all(isinstance(item, dict) for item in value):
            return table_from_rows(value)
        return "<ul>" + "".join(f"<li>{esc(item)}</li>" for item in value) + "</ul>"
    if isinstance(value, str) and value.strip():
        return f"<p>{esc(value)}</p>"
    return f"<p class=\"muted\">{esc(empty_note)}</p>"


def resolve_chart_path(base_dir: Path, raw_path: str) -> Path:
    raw = Path(raw_path)
    if raw.is_absolute():
        return raw
    for root in [base_dir, *base_dir.parents]:
        candidate = root / raw
        if candidate.exists():
            return candidate
    return base_dir / raw


def image_tag(path: Path, title: str, source: str) -> str:
    explanation = CHART_EXPLANATIONS.get(path.name, ("Chart explanation missing.", "Add a current-result takeaway before delivery."))
    note = (
        f"<div class=\"chart-note\"><b>How to read:</b> {esc(explanation[0])}"
        f"<br><b>Current takeaway:</b> {esc(explanation[1])}"
        f"<br><b>Data source:</b> {esc(source)}</div>"
    )
    if not path.exists():
        return (
            f"<figure class=\"missing\"><p>图表未生成或数据不足，未执行: {esc(path.name)}</p>"
            f"<figcaption>{esc(title)} | 数据来源: {esc(source)}</figcaption>{note}</figure>"
        )
    mime = "image/png"
    if path.suffix.lower() in {".jpg", ".jpeg"}:
        mime = "image/jpeg"
    elif path.suffix.lower() == ".webp":
        mime = "image/webp"
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return (
        f"<figure><img src=\"data:{mime};base64,{data}\" alt=\"{esc(title)}\">"
        f"<figcaption>{esc(title)} | 数据来源: {esc(source)}</figcaption>{note}</figure>"
    )


def metric_guide() -> str:
    rows = [
        ("IE", "Idiosyncratic asymmetry factor; the replicated signal used for sorting assets."),
        ("IC", "Correlation between factor values and next-period returns."),
        ("Rank IC", "Correlation between factor ranks and next-period return ranks."),
        ("ICIR", "Mean IC divided by IC volatility; a stability measure."),
        ("Positive IC Ratio", "Share of periods where IC is above zero; interpret according to the expected factor direction."),
        ("Annual Return", "Period returns converted to an annualized rate."),
        ("Annual Volatility", "Annualized standard deviation of returns."),
        ("Sharpe", "Annual return divided by annual volatility."),
        ("Calmar", "Annual return divided by absolute maximum drawdown."),
        ("Max DD", "Worst peak-to-trough NAV decline."),
        ("Win Rate", "Share of periods with positive returns."),
        ("NAV", "Cumulative net asset value, usually starting at 1."),
        ("IS / OOS", "In-sample and out-of-sample periods; OOS evidence carries more weight."),
    ]
    body = "".join(f"<tr><th>{esc(k)}</th><td>{esc(v)}</td></tr>" for k, v in rows)
    return f"<table><tbody>{body}</tbody></table>"


def rag_scorecard(summary: dict[str, Any]) -> str:
    rows = summary.get("rag_scorecard") or summary.get("scorecard") or []
    if not rows:
        rows = [
            {"item": "QUALITY_GATE_BLOCKER", "status": "red", "metric": "scorecard_missing", "evidence": "No objective RAG scorecard was provided in the input summary.", "impact": "Final delivery must compute scorecard rows from validation metrics."},
        ]
    body = []
    for row in rows:
        status = str(row.get("status", "yellow")).lower()
        body.append(
            f"<tr><td>{esc(row.get('item'))}</td><td><span class=\"chip {esc(status)}\">{esc(status)}</span></td>"
            f"<td>{esc(row.get('metric'))}</td><td>{esc(row.get('evidence'))}</td><td>{esc(row.get('impact'))}</td></tr>"
        )
    return "<table><tr><th>Check</th><th>RAG</th><th>Metric</th><th>Evidence</th><th>Conclusion impact</th></tr>" + "".join(body) + "</table>"


def benchmark_comparison(summary: dict[str, Any]) -> str:
    rows = summary.get("benchmark_comparison") or summary.get("benchmarks") or []
    if not rows:
        rows = [
            {"benchmark": "QUALITY_GATE_BLOCKER", "note": "benchmark_comparison_missing: compute reverse_factor, random_factor_fixed_seed, equal_weight_buy_hold, and zero_return_always_flat from real traceable data."},
        ]
    if all(isinstance(row, dict) for row in rows):
        return table_from_rows(rows)
    return "<ul>" + "".join(f"<li>{esc(row)}</li>" for row in rows) + "</ul>"


def backtest_alignment_audit(summary: dict[str, Any]) -> str:
    rows = summary.get("backtest_alignment_audit") or summary.get("alignment_audit") or []
    if not rows:
        rows = [
            {"dimension": "QUALITY_GATE_BLOCKER", "factor_validation": "alignment_audit_missing", "backtest_actual": "Compare source, date range, frequency, execution assumptions, final NAV, max drawdown, and divergence explanation before delivery."},
        ]
    return table_from_rows(rows)


def collect_charts(summary: dict[str, Any], base_dir: Path) -> dict[str, str]:
    charts: dict[str, str] = {}
    for raw in summary.get("charts", []):
        if isinstance(raw, dict):
            path = str(raw.get("path", ""))
            title = str(raw.get("title", Path(path).stem))
        else:
            path = str(raw)
            title = Path(path).stem
        if path:
            charts[path] = title

    for path, title, _source in REQUIRED_CHARTS:
        charts.setdefault(path, title)
    return charts


def build_chart_gallery(summary: dict[str, Any], base_dir: Path) -> str:
    custom_sources = summary.get("chart_sources", {})
    parts = []
    for path, title in collect_charts(summary, base_dir).items():
        source = custom_sources.get(path)
        if not source:
            source = next((src for req_path, _title, src in REQUIRED_CHARTS if req_path == path), path)
        parts.append(image_tag(resolve_chart_path(base_dir, path), title, source))
    return "\n".join(parts)


def build_html(summary: dict[str, Any], base_dir: Path) -> str:
    title = summary.get("title", "因子验证报告")
    factor_name = summary.get("factor_name", "待复现因子")
    conclusion = summary.get("conclusion", "inconclusive")

    diagnostics = summary.get("diagnostics", {})
    distribution = summary.get("distribution", summary.get("factor_distribution", {}))
    ic_metrics = summary.get("ic_metrics", summary.get("metrics", {}))
    equal_weight = summary.get("equal_weight_portfolio", summary.get("quantile_returns", {}))
    strategy_direction = summary.get("strategy_direction_portfolio", {})
    walk_forward = summary.get("walk_forward", summary.get("walkforward", {}))
    cost_sensitivity = summary.get("cost_sensitivity", {})
    audit = summary.get("audit", {})
    yearly = summary.get("yearly_performance", [])
    notes = summary.get("notes", "未执行项、数据不足项或无法判断项必须在此说明。")

    chart_gallery = build_chart_gallery(summary, base_dir)

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(title)}</title>
  <style>
    body {{ font-family: Arial, "Microsoft YaHei", sans-serif; margin: 0; color: #172026; background: #f6f7f9; }}
    main {{ max-width: 1120px; margin: 0 auto; padding: 32px 20px 56px; }}
    h1 {{ font-size: 30px; margin: 0 0 8px; }}
    h2 {{ margin-top: 0; border-bottom: 1px solid #d8dde3; padding-bottom: 8px; }}
    section {{ background: #fff; border: 1px solid #d8dde3; border-radius: 8px; padding: 20px; margin-top: 18px; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
    th, td {{ border: 1px solid #d8dde3; padding: 8px 10px; text-align: left; vertical-align: top; }}
    th {{ background: #eef2f5; }}
    img {{ max-width: 100%; height: auto; display: block; margin: 10px auto; }}
    figcaption {{ color: #5a6672; font-size: 13px; text-align: center; }}
    .badge {{ display: inline-block; background: #0f766e; color: #fff; padding: 4px 10px; border-radius: 999px; font-size: 13px; }}
    .chip {{ display: inline-block; border-radius: 999px; padding: 2px 8px; color: #fff; font-weight: 700; }}
    .green {{ background: #16a34a; }}
    .yellow {{ background: #ca8a04; }}
    .red {{ background: #dc2626; }}
    .muted {{ color: #6b7280; }}
    .missing {{ background: #fff4e5; padding: 10px; border-left: 4px solid #d97706; }}
    .read {{ background: #f8fafc; border-left: 4px solid #64748b; padding: 12px; margin-top: 10px; }}
    .chart-note {{ background: #fff7ed; border-left: 4px solid #f97316; padding: 10px 12px; margin-top: 8px; font-size: 14px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 12px; }}
  </style>
</head>
<body>
<main>
  <h1>{esc(title)}</h1>
  <p><span class="badge">Factor Validation | 结论: {esc(conclusion)}</span></p>
  <p>因子名称: {esc(factor_name)}</p>

  <section>
    <h2>阅读指南 / How To Read This Report</h2>
    <div class="read">先看结论，再沿着证据链检查：因子定义是否清楚 -> 是否通过未来函数/偷价审计 -> IC 和 Rank IC 是否支持方向 -> 分层组合是否赚钱 -> OOS 是否保持 -> BACKTEST 实际回测是否能承接理论结果。</div>
    {metric_guide()}
  </section>

  <section>
    <h2>红黄绿判定与结论打分卡 / RAG Scorecard</h2>
    <p>颜色必须来自客观指标或显式规则，不得由模型主观拍脑袋决定。</p>
    {rag_scorecard(summary)}
  </section>

  <section>
    <h2>基准对照 / Benchmark Comparison</h2>
    <p>至少比较反向因子、固定随机种子随机因子、等权买入持有、零收益/永远空仓基准。</p>
    {benchmark_comparison(summary)}
  </section>

  <section>
    <h2>BACKTEST 差异审计 / BACKTEST Alignment Audit</h2>
    <p>解释理论因子验证曲线与 BACKTEST 实际权益曲线在数据源、频率、执行、权重、成本和资金口径上的差异。</p>
    {backtest_alignment_audit(summary)}
  </section>

  <section>
    <h2>报告头 / 因子验证报告</h2>
    <p>{esc(summary.get("methodology", "本报告用于复现研报因子、验证预测能力，并对齐 BACKTEST 策略回测信号。"))}</p>
  </section>

  <section>
    <h2>因子审计 / Bias Check</h2>
    {section_table_or_note(audit, "未提供因子审计结果。必须披露 look-ahead、price leakage/偷价、信号滞后和执行价。")}
  </section>

  <section>
    <h2>数据诊断 / Data Diagnostics</h2>
    {table_from_dict(diagnostics)}
  </section>

  <section>
    <h2>因子横截面分布 / Factor Distribution</h2>
    {section_table_or_note(distribution, "未提供因子横截面分布统计。")}
  </section>

  <section>
    <h2>IC 分析 / Rank IC / ICIR</h2>
    {table_from_dict(ic_metrics)}
  </section>

  <section>
    <h2>等权重组合回测 / Equal Weight Quantile Portfolio</h2>
    {section_table_or_note(equal_weight, "未执行等权重组合回测。")}
  </section>

  <section>
    <h2>策略等手数组合 / Equal Lot Strategy Direction</h2>
    {section_table_or_note(strategy_direction, "未执行策略方向或等手数组合回测。")}
  </section>

  <section>
    <h2>Walk-forward 滚动窗口验证</h2>
    {section_table_or_note(walk_forward, "数据不足或未执行 Walk-forward。")}
  </section>

  <section>
    <h2>成本敏感性 / Cost Sensitivity</h2>
    {section_table_or_note(cost_sensitivity, "未计算成本敏感性。")}
  </section>

  <section>
    <h2>验证结论 / Conclusion</h2>
    <p>{esc(conclusion)}</p>
    <p>{esc(notes)}</p>
  </section>

  <section>
    <h2>年度表现 / Yearly Performance</h2>
    {table_from_rows(yearly)}
  </section>

  <section>
    <h2>图表与数据来源 / Charts</h2>
    <div class="grid">{chart_gallery}</div>
  </section>
</main>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="JSON summary path.")
    parser.add_argument("--output", required=True, help="HTML output path.")
    args = parser.parse_args()

    input_path = Path(args.input).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()
    summary = json.loads(input_path.read_text(encoding="utf-8-sig"))
    html_text = build_html(summary, input_path.parent)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_text, encoding="utf-8")
    print(json.dumps({"output": str(output_path)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
