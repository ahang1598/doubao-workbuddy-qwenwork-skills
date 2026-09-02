# Output Contract

Use this contract for every report replication project.

## Directory

```text
/home/coder/project/replication/report-replication/{report_id}/
  01_translation/full_translation.md
  02_factor_reproduction/ai_summary_and_factor_formula.md
  02_factor_reproduction/reference_implementation.py
  03_factor_validation/factor_validation_report.html
  03_factor_validation/data/
  03_factor_validation/data/ie_factor_matrix.csv
  03_factor_validation/data/direction_matrix_from_strategy.csv
  03_factor_validation/data/portfolio_returns_ew_full.csv
  03_factor_validation/data/portfolio_returns_ew_is.csv
  03_factor_validation/data/portfolio_returns_ew_oos.csv
  03_factor_validation/data/portfolio_returns_dir_full.csv
  03_factor_validation/data/portfolio_returns_dir_is.csv
  03_factor_validation/data/portfolio_returns_dir_oos.csv
  03_factor_validation/data/ic_series.csv
  03_factor_validation/data/factor_diagnostics.csv
  03_factor_validation/data/coverage_by_date.csv
  03_factor_validation/data/missing_by_asset.csv
  03_factor_validation/data/quantile_returns.csv
  03_factor_validation/data/rolling_metrics.csv
  03_factor_validation/data/yearly_performance.csv
  03_factor_validation/data/turnover_series.csv
  03_factor_validation/data/benchmark_comparison.csv
  03_factor_validation/data/backtest_alignment_audit.csv
  03_factor_validation/charts/
  03_factor_validation/charts/01_ie_distribution.png
  03_factor_validation/charts/02_ic_series.png
  03_factor_validation/charts/03_is_oos_ic_comparison.png
  03_factor_validation/charts/04_cumulative_nav_equal_weight.png
  03_factor_validation/charts/05_cumulative_nav_strategy_direction.png
  03_factor_validation/charts/06_drawdown.png
  03_factor_validation/charts/07_ic_distribution.png
  03_factor_validation/charts/08_rolling_ic.png
  03_factor_validation/charts/09_quantile_nav.png
  03_factor_validation/charts/10_quantile_return_bar.png
  03_factor_validation/charts/11_yearly_return_heatmap.png
  03_factor_validation/charts/12_turnover_series.png
  03_factor_validation/charts/13_data_coverage_heatmap.png
  03_factor_validation/charts/14_missing_value_heatmap.png
  03_factor_validation/charts/15_benchmark_nav_comparison.png
  03_factor_validation/charts/16_backtest_alignment_nav.png
  03_factor_validation/charts/17_parameter_stability_heatmap.png
  03_factor_validation/charts/18_cost_sensitivity.png
  03_factor_validation/charts/19_walkforward.png
  03_factor_validation/data_cache/
  03_factor_validation/data_cache/pandadata_market_data.csv
  03_factor_validation/data_cache/pandadata_market_data.csv.metadata.json
  04_backtest_strategy/strategy.py
  04_backtest_strategy/config.json
  04_backtest_strategy/backtest_report.html
  04_backtest_strategy/backtest_report_raw.html (optional raw BACKTEST engine report)
  04_backtest_strategy/backtest_logs/signal_log.jsonl
  04_backtest_strategy/backtest_logs/equity_curve.csv
  04_backtest_strategy/backtest_logs/performance_metrics.csv
  04_backtest_strategy/backtest_logs/trades.csv
  04_backtest_strategy/backtest_logs/position_return_detail.csv
  06_delivery/final_delivery_summary.md
  failure_report.md
  manifest.json
```

## Language Requirements

- User-facing deliverables must be Chinese-readable: translation, AI summary, factor validation HTML, BACKTEST explanation HTML, final delivery summary, and generated strategy docstrings/comments.
- English is allowed only for formulas, code/API names, metric abbreviations, original titles, proper names, CSV column names, and ticker symbols.
- If BACKTEST or another tool emits English/garbled HTML, preserve it as `backtest_report_raw.html` and create `backtest_report.html` as a Chinese reader-facing explanation page that links to the raw artifact.
- Beginner-facing explanations must be written for smart non-quant readers. Avoid rigid template prose, unexplained jargon, marketing claims, and exaggerated certainty.

## Chart Image Text Requirements

- Chart image files under `03_factor_validation/charts/` must render English ASCII text only. This includes image titles, subtitles, axis labels, legends, colorbar labels, annotations, heatmap labels, in-image table headers, and watermark text.
- Chinese chart explanations belong in the surrounding HTML/Markdown text, not inside the image pixels.
- For Matplotlib/Seaborn/Plotly static images, use broadly available Latin fonts such as `DejaVu Sans` or `Arial`; do not configure CJK chart fonts such as `SimHei`, `SimSun`, `Microsoft YaHei`, `Noto Sans CJK`, or `Source Han Sans`.
- If a source factor name or report label is Chinese, draw an ASCII-safe display label in the chart and preserve the original Chinese name in the HTML caption or explanation.

## `manifest.json`

Include:

- `report_id`
- `title`
- `source`
- `created_at`
- `python`
- `backtest_engine`
- `backtest_entrypoint`
- `backtest_command`
- `data_sources`
- `assumptions`
- `parameters`
- `code_hashes`
- `run_history`
- `artifacts`
- `status`
- `subagent_usage` if any subagent/background agent was used. Record scope, scratch path, promoted artifacts, rejected artifacts, and main-agent verification steps.

## Subagent / Background Agent Policy

Subagents are optional and not part of the required workflow. If used, they must be treated as untrusted assistants:

- They may only write to isolated scratch paths such as `/home/coder/project/replication/report-replication/{report_id}/.agent_work/`.
- They may not directly edit or overwrite final artifacts.
- Their outputs must be reviewed and promoted manually by the main agent.
- The main agent must rerun all relevant validation scripts and `quality_gate_check.py` after promotion.
- The final report and delivery summary must not rely on subagent claims unless the main agent reproduced or verified the evidence.

## 1. Full Translation

File: `01_translation/full_translation.md`

Acceptance criteria:

- Preserve the original section order.
- Translate all body text, table notes, chart captions, footnotes, and formula explanations where extractable.
- Keep page or section anchors when possible.
- Mark low-confidence OCR/PDF extraction areas as `待核验`.
- Do not invent missing table values or formula terms.

## 2. AI Summary And Factor Formula

File: `02_factor_reproduction/ai_summary_and_factor_formula.md`

Acceptance criteria:

- State the research question in plain Chinese.
- Summarize the core finding and investment intuition.
- Identify asset universe, sample period, rebalance frequency, benchmark, and data source.
- Reconstruct each factor with formula, variables, calculation order, and implementation assumptions.
- Show pseudocode or concise implementation notes.
- Record bias and risk checks.

## 3. Factor Validation Report

File: `03_factor_validation/factor_validation_report.html`

Acceptance criteria:

- Standalone HTML that opens without a server.
- Include written methodology, charts, tables, and final conclusion.
- The report body must be Chinese. Metric abbreviations and short English labels are allowed only as glossary aids.
- All text inside embedded chart images must be English ASCII only; Chinese explanations must appear below or near the chart in HTML.
- Include a reader-facing `How To Read This Report` / `阅读指南` section near the top. It must explain the evidence chain in plain language: factor definition -> bias audit -> IC / Rank IC -> portfolio test -> OOS result -> BACKTEST result alignment.
- Include a metric dictionary / glossary that explains, at minimum: IE, IC, Rank IC, ICIR, Positive IC Ratio, Annual Return, Annual Volatility, Sharpe, Calmar, Max DD, Win Rate, NAV, IS, and OOS.
- State the data source path/mode used for validation.
- State the Pandadata method and cache file used for validation, or explain why a non-Pandadata source was required.
- Data must be real and traceable. Synthetic, mock, or randomly generated market data is strictly prohibited for factor validation. If data is insufficient, state this explicitly and label the conclusion as `inconclusive`.
- A fixed-seed random-factor baseline is allowed only as a negative-control signal on the same real return data used by the factor. It must never replace real market data.
- Include data diagnostics, IC tests, Rank IC tests, IC distribution, rolling IC, quantile returns, quantile monotonicity, long-short performance, drawdown, yearly/monthly performance, turnover, benchmark comparison, and BACKTEST alignment when data allows.
- Include a factor audit section: data availability, signal lag, label construction, execution price, look-ahead checks, price leakage checks, sample split, and cost assumptions.
- Include in-sample, out-of-sample, and walk-forward results.
- Include parameter stability, transaction-cost sensitivity, reverse-factor baseline, random-factor baseline, leave-one-asset-out or leave-one-sector-out robustness, and benchmark comparison when data allows.
- Under every chart, include a beginner-facing chart explanation block with five chart-specific parts: `这张图回答什么问题`, `怎么看`, `我们看到了什么`, `这意味着什么`, and `数据来源`.
- For drawdown charts, explicitly state that drawdown is derived from NAV and is not a duplicate NAV curve.
- For BACKTEST-vs-factor-validation curves, explicitly state whether the curve is theoretical close/close factor validation or actual BACKTEST equity. If actual BACKTEST equity is used, say which report series or artifact was used.
- Explicitly state that `04_cumulative_nav_equal_weight.png` and `05_cumulative_nav_strategy_direction.png` are factor-validation curves, not BACKTEST actual equity curves, unless the report has actually extracted and embedded BACKTEST actual equity.
- Include a red/yellow/green judgement table and conclusion scorecard. It must be computed from objective metrics and must cover formula confidence, data coverage, leakage audit, IC direction, OOS result, portfolio risk/return, cost robustness, and BACKTEST actual result alignment.
- Include a benchmark comparison section against at least reverse factor, fixed-seed random factor, equal-weight buy-and-hold, and zero-return / always-flat baseline. Save the benchmark data or metrics in `03_factor_validation/data/`.
- Include a BACKTEST alignment audit section comparing factor-validation curves with BACKTEST actual equity: source artifact, date range, frequency, weighting/execution assumptions, final NAV, max drawdown, and explanation of divergence.
- Include the expanded chart pack when data allows: IC distribution, rolling IC, quantile NAV, quantile return monotonicity, yearly/monthly performance heatmap, turnover series, data coverage heatmap, missing-value heatmap, benchmark NAV comparison, BACKTEST alignment NAV comparison, parameter stability heatmap, cost sensitivity chart, and walk-forward chart.
- The HTML must be understandable to users who are not quant researchers.
- For futures strategies, report both theoretical equal-weight and actual strategy weighting such as equal-lot performance when data allows, and explain the difference.
- Explain missing metrics if some cannot be calculated.

### HTML Report Standard Structure

`factor_validation_report.html` must contain these sections:

0. **阅读指南 / How To Read This Report**: evidence chain and metric dictionary.
0.1 **红黄绿判定与结论打分卡 / RAG Scorecard**: objective scorecard.
0.2 **基准对照 / Benchmark Comparison**: reverse factor, fixed-seed random factor, equal-weight buy-and-hold, zero-return baseline.
0.3 **BACKTEST 差异审计 / BACKTEST Alignment Audit**: theoretical factor validation vs BACKTEST actual equity.
1. **报告头**: report title, source, validation date, data source, symbols, sample period.
2. **因子审计（Bias Check）**.
3. **数据诊断**.
4. **IE 因子横截面分布图**.
5. **IC 分析**.
6. **IC 稳定性与显著性**.
7. **分层组合回测**.
8. **策略方向组合回测**.
9. **年度/月度表现与换手**.
10. **稳健性验证**.
11. **基准和 BACKTEST 对齐**.
12. **验证结论**.

If a section cannot be generated because of insufficient data, keep the section title and write a concrete Chinese blocker.

### Required Data Files

`03_factor_validation/data/` must include:

| File | Content | Required |
| --- | --- | --- |
| `ie_factor_matrix.csv` | factor value by date and asset | yes |
| `direction_matrix_from_strategy.csv` | trading direction by date and asset from strategy signal log | yes |
| `portfolio_returns_ew_full.csv` | equal-weight full-sample returns | yes |
| `portfolio_returns_ew_is.csv` | equal-weight IS returns | yes |
| `portfolio_returns_ew_oos.csv` | equal-weight OOS returns | yes |
| `portfolio_returns_dir_full.csv` | strategy-direction full-sample returns | yes |
| `portfolio_returns_dir_is.csv` | strategy-direction IS returns | yes |
| `portfolio_returns_dir_oos.csv` | strategy-direction OOS returns | yes |
| `walkforward_results.csv` | walk-forward window results | if executed |
| `ic_series.csv` | IC and Rank IC series | yes |
| `factor_diagnostics.csv` | factor distribution diagnostics | yes |
| `coverage_by_date.csv` | coverage and valid signal counts | yes |
| `missing_by_asset.csv` | missingness by asset | yes |
| `quantile_returns.csv` | quantile portfolio returns and NAV | yes |
| `rolling_metrics.csv` | rolling returns, volatility, Sharpe, drawdown, IC | if data allows |
| `yearly_performance.csv` | yearly/monthly performance | if data allows |
| `turnover_series.csv` | turnover and position changes | if data allows |
| `parameter_stability.csv` | parameter stability grid | if executed |
| `cost_sensitivity.csv` | transaction cost sensitivity | if executed |
| `benchmark_comparison.csv` | factor and baseline returns or metrics | yes |
| `backtest_alignment_audit.csv` | factor-validation vs BACKTEST actual equity audit | yes |

### Required Data Cache Files

`03_factor_validation/data_cache/` should include the Pandadata cache used for validation and BACKTEST:

| File | Content | Required |
| --- | --- | --- |
| `pandadata_market_data.csv` | normalized Pandadata market data with `date`, `symbol`, and `close` | yes when market-price data is required |
| `pandadata_market_data.csv.metadata.json` | provider, SDK method, symbols, sample period, adjustment, output path, fetch timestamp, and missing-value handling | yes when Pandadata is used |

### Required Charts

`03_factor_validation/charts/` must include:

Image text rule: every chart title, axis label, legend, annotation, colorbar label, and in-chart table label must be English ASCII. Use the English content labels below directly when possible.

| File | Content | Required |
| --- | --- | --- |
| `01_ie_distribution.png` | factor distribution | yes |
| `02_ic_series.png` | IC time series | yes |
| `03_is_oos_ic_comparison.png` | IS vs OOS IC comparison | yes |
| `04_cumulative_nav_equal_weight.png` | equal-weight long-short NAV | yes |
| `05_cumulative_nav_strategy_direction.png` | strategy-direction long-short NAV | yes |
| `06_drawdown.png` | drawdown | yes |
| `07_ic_distribution.png` | IC / Rank IC distribution | yes |
| `08_rolling_ic.png` | rolling IC / Rank IC | if data allows |
| `09_quantile_nav.png` | quantile NAV | yes |
| `10_quantile_return_bar.png` | quantile average return bar chart | yes |
| `11_yearly_return_heatmap.png` | yearly/monthly return heatmap | if data allows |
| `12_turnover_series.png` | turnover series | if data allows |
| `13_data_coverage_heatmap.png` | data coverage heatmap | yes |
| `14_missing_value_heatmap.png` | missing value heatmap | yes |
| `15_benchmark_nav_comparison.png` | benchmark NAV comparison | yes |
| `16_backtest_alignment_nav.png` | factor validation vs BACKTEST actual equity | if BACKTEST equity is available |
| `17_parameter_stability_heatmap.png` | parameter stability | if executed |
| `18_cost_sensitivity.png` | cost sensitivity | if executed |
| `19_walkforward.png` | walk-forward results | if executed |

## 4. BACKTEST Strategy And Backtest

Files:

- `04_backtest_strategy/strategy.py`
- `04_backtest_strategy/config.json`
- `04_backtest_strategy/backtest_report.html`
- `04_backtest_strategy/backtest_report_raw.html` (optional raw engine report)
- `04_backtest_strategy/backtest_logs/`
- `04_backtest_strategy/backtest_logs/signal_log.jsonl`

Acceptance criteria:

- Strategy code writes the signal log consumed by the bundled local BACKTEST engine, or is compatible with a documented user-provided external BACKTEST entrypoint.
- Parameters are editable in one visible section.
- Strategy logic follows the reconstructed factor and validation results.
- BACKTEST is run locally with `scripts/local_backtest.py` by default.
- Default market data comes from `03_factor_validation/data_cache/pandadata_market_data.csv`, produced by WorkBuddy `call_pandadata`.
- `backtest_report.html` must be Chinese-readable; if the engine generated an English/garbled raw report, save it separately as `backtest_report_raw.html` and make `backtest_report.html` a Chinese explanation/wrapper with references to raw engine evidence.
- Strategy backtest must output `backtest_logs/signal_log.jsonl`, one JSON record per line: `{"date": "YYYY-MM-DD", "signals": {"SYM": {"factor": float, "direction": 1|-1|0}}}`.
- Bundled engine outputs must include `equity_curve.csv`, `performance_metrics.csv`, `trades.csv`, and `position_return_detail.csv`.
- Failure logs are saved when execution is blocked.
- The report explains how factor-validation logic maps into the BACKTEST strategy and where execution assumptions differ.

## 5. Final Delivery Summary

File: `06_delivery/final_delivery_summary.md`

Acceptance criteria:

- One concise decision-oriented summary.
- Includes report thesis, factor effectiveness conclusion, BACKTEST status, key metrics, artifact paths, assumptions, risks, and next steps.
- If a stage failed, links to `failure_report.md` and states what remains blocked.

## Failure Report

File: `failure_report.md`

Create this if any required stage cannot be completed.

Acceptance criteria:

- Failed stage.
- Exact command or action attempted.
- Error message or traceback.
- Partial artifacts already generated.
- Likely cause.
- Next repair step.
