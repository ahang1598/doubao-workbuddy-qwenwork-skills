---
name: report-replication
description: "Reproduce quantitative research reports and papers end to end: full Chinese translation, AI summary, factor formula reconstruction, factor effectiveness validation, standalone beginner-readable HTML factor report, BACKTEST strategy generation and local backtest execution, Chinese backtest explanation report, and final delivery summary. Use when the user provides a quant report/PDF/link/text and asks for report replication, factor replication, factor validation, BACKTEST strategy code, or a beginner-readable research replication package."
license: GPL-3.0-only
metadata:
  organization: QuantSkills
  organization_url: https://github.com/quantskills
  repository: skill-report-replication
  repository_url: https://github.com/quantskills/skill-report-replication
  project_type: skill
  collection: report-replication
  creator: abgyjaguo
  maintainer: abgyjaguo
quantSkills:
  project_type: skill
  category: replication
  tags:
  - report-replication
  - factor-research
  - backtest
  - pandadata
  - html-report
  - chinese
  platforms:
  - claude-code
  - codex
  - hermes
  - openclaw
  - cursor
  status: stable
  validation_level: runnable
  maintainer_type: official
  summary_zh: "把一篇量化研报、论文、PDF、网页或文本材料，转化为 Pandadata 真实数据驱动的研究复现交付包：全文翻译 → 因子公式复现 → 有效性验证 → 策略代码 → 真实本地回测 → 交付摘要。"
  summary_en: "Quant report replication skill that turns papers or reports into Chinese translations, factor formulas, Pandadata-backed validation reports, and strategy assets."
  license: GPL-3.0
---

## WorkBuddy PandaData MCP 强制覆盖

本节优先于本 Skill 后续所有数据源、依赖安装和命令示例。WorkBuddy 版只允许使用已连接的
`pandadata` Connector：先调用 `auth_status`，再按共享 Runtime Skill 中的已登记路由调用
`call_pandadata`。本地 PandaData SDK、直接 HTTP、凭证文件和历史下载脚本在此版本中均
已禁用。必须执行空数据复查并在最终答案附完整调用回执；未打开 `DATA_GATE` 不得分析。

## WorkBuddy PandaData MCP 强制覆盖

本节优先于本 Skill 后续所有数据源、依赖安装和命令示例。WorkBuddy 版只允许使用已连接的
`pandadata` Connector：先调用 `auth_status`，再按共享 Runtime Skill 中的已登记路由调用
`call_pandadata`。本地 PandaData SDK、直接 HTTP、凭证文件和历史下载脚本在此版本中均
已禁用。必须执行空数据复查并在最终答案附完整调用回执；未打开 `DATA_GATE` 不得分析。

## WorkBuddy PandaData MCP 强制覆盖

本节优先于本 Skill 后续所有数据源、依赖安装和命令示例。WorkBuddy 版只允许使用已连接的
`pandadata` Connector：先调用 `auth_status`，再按共享 Runtime Skill 中的已登记路由调用
`call_pandadata`。本地 PandaData SDK、直接 HTTP、凭证文件和历史下载脚本在此版本中均
已禁用。必须执行空数据复查并在最终答案附完整调用回执；未打开 `DATA_GATE` 不得分析。

```json qsh-form
{
  "version": 1,
  "task": {
    "placeholder": "请提供量化研报、论文、PDF、网页或文本，并说明期望复现范围",
    "required": true
  },
  "fields": [
    {
      "key": "focus",
      "label": "复现重点",
      "type": "text",
      "placeholder": "如：全文翻译、某个因子、有效性验证或回测策略"
    }
  ],
  "prompt_template": "{{#task}}任务与材料：\n{{task}}\n\n{{/task}}{{#attachments}}用户上传的材料（已放入工作区）：\n{{attachments}}\n\n{{/attachments}}请端到端复现所给量化报告或论文{{#focus}}，重点关注 {{focus}}{{/focus}}：完成中文全文翻译、研究摘要与因子公式重构、真实可溯源数据验证、无前视偏差的 BACKTEST 策略及本地回测、中文可读报告和最终交付摘要；无法执行的环节须如实记录，输出中文报告。"
}
```

# Report Replication BACKTEST

## Purpose

Turn a quant report, paper, PDF, webpage, or text source into a complete research delivery package under `/home/coder/project/replication/report-replication`:

1. Full Chinese translation of the original report or paper.
2. Chinese AI summary plus factor formula reconstruction in Markdown.
3. Chinese factor validation report as standalone HTML, with charts, metrics, audit notes, and plain-language explanations for users who do not know quantitative jargon.
4. BACKTEST strategy code plus a Chinese backtest explanation HTML. Preserve raw BACKTEST engine output separately when needed.
5. Chinese final delivery summary.

This skill is self-contained for translation, factor reconstruction, factor validation, bundled local BACKTEST execution, optional external BACKTEST execution, and final delivery. Do not call any legacy framework-specific skills, scripts, data layers, examples, or assumptions.

Pandadata is the default production market-data source. Use WorkBuddy `call_pandadata` to download daily stock, index, futures, Hong Kong, or US market data into `03_factor_validation/data_cache/` before factor validation or BACKTEST. User-provided or report-supplied files may be used only when Pandadata does not cover the required dataset, and the fallback must be documented in `manifest.json`, the validation report, and the final summary.

Credentials must come from `WorkBuddy-managed authentication`, `WorkBuddy-managed authentication`, `WorkBuddy-managed authentication`, or `WorkBuddy-managed authentication`. Never write usernames, passwords, tokens, or raw credential files into generated artifacts, logs, commits, or reports. Record only that credential values were not persisted.

## Language And Readability Rules

- All user-facing deliverables must use Chinese as the primary language: `full_translation.md`, `ai_summary_and_factor_formula.md`, `factor_validation_report.html`, `backtest_report.html`, `final_delivery_summary.md`, and explanatory comments/docstrings in generated strategy code.
- English may appear only when unavoidable: original paper titles, proper names, formulas, code identifiers, CSV column names, API names, ticker/symbol names, metric abbreviations, and short parenthetical glossary labels such as `IC` or `Sharpe`.
- Do not deliver English narrative sections, English-only reports, or mojibake/garbled Chinese. If a tool generates English or garbled HTML, wrap or rewrite it into a Chinese reader-facing artifact and preserve the raw file separately for audit.
- Before final delivery, spot-check the main readable files for Chinese readability rather than relying only on automated quality gates.
- Explain quant concepts as if the reader is smart but new to quant research. Prefer restrained science writing: concise, concrete, and evidence-led.

## Chart Image Text Rules

- Text rendered inside generated chart image files must be English ASCII only. This includes PNG/SVG titles, subtitles, axis labels, legends, colorbar labels, annotation text, heatmap labels, in-image table headers, and watermarks.
- Keep Chinese explanations outside the image in the HTML/Markdown captions and chart explanation blocks. The report can remain Chinese-readable while the chart pixels stay font-compatible.
- When using Matplotlib, Seaborn, Plotly static export, or another image renderer, use broadly available Latin fonts such as `DejaVu Sans` or `Arial`. Do not set CJK chart fonts such as `SimHei`, `SimSun`, `Microsoft YaHei`, `Noto Sans CJK`, or `Source Han Sans`.
- Prefer English chart labels from `references/factor_validation_checklist.md`, for example `Benchmark NAV Comparison`, not Chinese translations. If the original factor/report name is Chinese, draw an ASCII-safe display label in the chart and keep the original Chinese name in the surrounding report text.

## Required Output Contract

Create one project directory per report:

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

Read `references/output_contract.md` before writing final artifacts.

## Honesty Rules

- Say exactly what was done. If a step was not run, state that it was not run.
- Do not fabricate walk-forward results, cost-sensitivity results, IC series, charts, backtest reports, or BACKTEST logs.
- If BACKTEST cannot run, or if data is unavailable or insufficient, document the blocker and mark the conclusion as inconclusive.
- Every chart, table, and metric in the HTML report must be traceable to a file under `03_factor_validation/data/`, a chart under `03_factor_validation/charts/`, or a BACKTEST artifact.
- Every chart and key metric in the HTML report must also be explained in plain language: what it means, how to read it, what the current result implies, and which data/artifact it came from.

## Subagent Governance

This skill does not require subagents. Default to a single main-agent workflow unless the current task is too large and a subagent would materially reduce risk or time.

If a subagent/background agent is used:

- The main agent remains fully responsible for correctness and final delivery.
- Subagent outputs are drafts only. They must never be copied into final artifacts without main-agent review.
- Subagents must write only under `/home/coder/project/replication/report-replication/{report_id}/.agent_work/` or another explicitly isolated scratch directory.
- Subagents must not overwrite final artifacts such as `factor_validation_report.html`, `strategy.py`, `signal_log.jsonl`, `manifest.json`, or delivery summaries.
- The main agent must independently verify formulas, data provenance, leakage checks, generated CSVs, charts, BACKTEST reports, and conclusions before promotion into final artifacts.
- The main agent must rerun the relevant step checks and final `quality_gate_check.py` after integrating any subagent work.
- If any required stage fails, create `failure_report.md` with the failed command, error, partial artifacts, likely cause, and next repair step.

## Workflow

### 1. Initialize

Before creating or running the project, verify the local runtime dependencies:

```bash
python scripts/check_dependencies.py --install
```

Use Python 3.10 or newer for Pandadata. The default WorkBuddy `pandadata` Connector runtime reads local credentials from the current environment or `WorkBuddy-managed authentication`; it also requires `requests` at runtime.

Use `scripts/create_project.py` to create the output structure and `manifest.json`. The default root is `/home/coder/project/replication/report-replication`.

Download real Pandadata market data before validation and BACKTEST:

```bash
python WorkBuddy call_pandadata \
  --asset-type stock \
  --symbols 000001.SZ 600000.SH \
  --start-date 20250101 \
  --end-date 20250131 \
  --output /home/coder/project/replication/report-replication/{report_id}/03_factor_validation/data_cache/pandadata_market_data.csv \
  --project-dir /home/coder/project/replication/report-replication/{report_id}
```

Then use the bundled local BACKTEST engine by default:

```bash
python scripts/local_backtest.py /home/coder/project/replication/report-replication/{report_id} --market-data /home/coder/project/replication/report-replication/{report_id}/03_factor_validation/data_cache/pandadata_market_data.csv
```

The bundled engine reads real market data plus `04_backtest_strategy/backtest_logs/signal_log.jsonl`, applies a configurable execution lag, estimates fees/slippage, and writes equity, trade, metric, alignment, raw, and Chinese HTML report artifacts. If the user explicitly supplies an external BACKTEST runner, use it only after documenting the entrypoint, command, config, and output mapping in `manifest.json`.

Record:

- Original input path or URL.
- Report title if known.
- Run date.
- Python executable and dependency report.
- BACKTEST engine entrypoint, version if known, command, config, and output files. For the bundled engine, record `scripts/local_backtest.py`.
- Pandadata method, symbols/universe, sample period, frequency, adjustment rule, local cache path, metadata path, missing-value handling, assumptions, parameters, code hashes, and run history.

### 2. Extract And Translate

Deliver `01_translation/full_translation.md`.

Requirements:

- It must be a full Chinese translation, not only English extraction.
- Preserve the original structure, page markers, section markers, table notes, chart captions, and formula explanations when extractable.
- Mark uncertain OCR/PDF extraction regions as `pending verification` / `待核验`.
- Do not invent missing formulas, table values, or chart notes.

After Step 2, run:

```bash
python scripts/check_step2_translation.py /home/coder/project/replication/report-replication/{report_id}
```

Do not move to Step 3 until the gate passes or the blocker is documented.

### 3. Reconstruct Factors

Deliver:

- `02_factor_reproduction/ai_summary_and_factor_formula.md`
- `02_factor_reproduction/reference_implementation.py`

The Markdown file must include the research question, conclusion, asset universe, sample period, rebalance frequency, data source, benchmark, factor formula, variable definitions, portfolio construction rules, assumptions, and bias checks.

The reference implementation must include factor calculation functions precise enough to audit the formula, including missing-value rules, standardization, ranking or grouping, regression model details when relevant, and rebalance timing.

After Step 3, run:

```bash
python scripts/check_step3_factor_reconstruction.py /home/coder/project/replication/report-replication/{report_id}
```

Do not move to factor validation until the gate passes or the blocker is documented.

### 4. Validate Factor Effectiveness

Use real, traceable market or research data. Default to Pandadata daily data downloaded with WorkBuddy `call_pandadata` when validating market-price factors or running BACKTEST. Prefer the Pandadata dataset that matches the report universe and BACKTEST configuration. Do not use synthetic, mock, or randomly generated market data to prove effectiveness. A fixed-seed random factor may only be used as a negative-control baseline on the same real return data as the target factor.

Validation is two-phase:

```text
Step 3: factor reconstruction
  -> Phase A: independent theoretical factor validation
Step 5: BACKTEST strategy and backtest
  -> Phase B: alignment validation that consumes backtest_logs/signal_log.jsonl
```

At minimum evaluate:

- Data coverage, missingness, outliers, and factor distribution.
- IC, Rank IC, ICIR, IC t-statistic, positive IC ratio, IC distribution, yearly/quarterly IC, cumulative IC, and rolling IC.
- Quantile/group monotonicity, equal-weight portfolio returns, long-short returns, long-only/short-only legs when applicable, and strategy-direction portfolio returns.
- Full sample, in-sample, out-of-sample, and walk-forward when data allows.
- Drawdown, annual return, volatility, downside volatility, Sharpe, Sortino, Calmar, max drawdown, max drawdown duration, win rate, profit/loss ratio, skewness, kurtosis, VaR/CVaR, turnover, capacity/liquidity proxy when data allows, and yearly/monthly performance.
- Look-ahead, price leakage, data availability time, signal lag, execution price, cost assumptions, sample split, and overfitting controls.
- Parameter stability, cost sensitivity, reverse-factor baseline, fixed-seed random-factor baseline, equal-weight buy-and-hold baseline, zero-return/always-flat baseline, leave-one-asset-out or leave-one-sector-out robustness when data allows, and BACKTEST alignment.

Report readability requirements:

- Write the report in Chinese. English terms may appear only as short labels, metric abbreviations, formulas, or artifact names.
- Render every chart image with English ASCII text only; keep Chinese reader-facing explanations in the HTML below each image.
- Add a `How To Read This Report` / `阅读指南` section near the top that explains the evidence chain from factor definition, bias audit, IC, portfolio test, OOS result, and BACKTEST result.
- Add a metric dictionary explaining at least IE, IC, Rank IC, ICIR, Positive IC Ratio, Annual Return, Annual Volatility, Sharpe, Calmar, Max DD, Win Rate, NAV, IS, and OOS.
- Under every chart, include a Chinese beginner-facing explanation block. It must be specific to that chart and contain:
  - `这张图回答什么问题`
  - `怎么看`
  - `我们看到了什么`
  - `这意味着什么`
  - `数据来源`
- Explain clearly that factor-validation NAV curves are not automatically BACKTEST actual account/equity curves:
  - `04_cumulative_nav_equal_weight.png` is a theoretical equal-weight factor-validation curve.
  - `05_cumulative_nav_strategy_direction.png` is a strategy-direction validation curve reconstructed from directions and return data.
  - BACKTEST actual account/equity curves come from BACKTEST artifacts such as `04_backtest_strategy/backtest_report_raw.html`, exported equity files, or log files.
  - For futures, explain equal-weight vs equal-lot, contract multipliers, next-bar execution, fees, slippage, margin/capital allocation, and daily mark-to-market.
- Add a red/yellow/green (RAG) judgement table and conclusion scorecard. It must use objective metrics, not model opinion. At minimum score formula confidence, data coverage, leakage audit, IC direction, OOS portfolio result, full-sample portfolio risk/return, cost robustness, and BACKTEST actual result alignment.
- Add benchmark comparison against at least: reverse factor, fixed-seed random factor, equal-weight buy-and-hold, and zero-return / always-flat baseline. Save the benchmark returns or metrics under `03_factor_validation/data/`.
- Add a BACKTEST alignment audit table comparing factor-validation curves with BACKTEST actual equity curves: data source, time range, frequency, weighting/execution assumptions, final NAV, max drawdown, and whether divergence is expected/explained.
- Produce the expanded factor-validation visual pack when data allows: IC distribution, rolling IC, quantile NAV, quantile return monotonicity bar chart, yearly/monthly performance heatmap, turnover series, data coverage heatmap, missing-value heatmap, benchmark NAV comparison, BACKTEST alignment NAV comparison, parameter stability heatmap, cost sensitivity chart, and walk-forward chart.
- If an expanded chart or metric cannot be produced, keep the section and state the exact blocker in Chinese.
- The report must be useful to a non-quant user without requiring them to inspect CSV files or BACKTEST internals.

Final conclusion must be one of: effective, weakly effective, ineffective, regime-dependent, or inconclusive.

Read `references/factor_validation_checklist.md` and `references/factor_audit_and_robustness.md` before judging effectiveness.

Use `scripts/build_factor_report.py` when a deterministic HTML scaffold is useful. The generated HTML must still satisfy `references/output_contract.md` and `scripts/quality_gate_check.py`.

### 5. Generate And Run BACKTEST Strategy

Generate BACKTEST strategy code only after factor logic is reconstructed and Phase A validation has been attempted.

Required behavior:

- Read `references/backtest_engine.md` before writing or running Step 5.
- Convert the validated factor signal into executable strategy logic that writes `04_backtest_strategy/backtest_logs/signal_log.jsonl`.
- Keep parameters clear: symbols, frequency, factor window, rebalance frequency, entry/exit rules, risk controls, fees, slippage, margin, and capital constraints.
- Run the bundled local BACKTEST engine with `scripts/local_backtest.py` unless the user explicitly provides an external BACKTEST runner.
- Save or preserve BACKTEST's raw output as `04_backtest_strategy/backtest_report_raw.html`.
- Deliver `04_backtest_strategy/backtest_report.html` as a Chinese reader-facing backtest explanation report. It must summarize strategy logic, data, run artifacts, signal log, relationship to factor validation curves, known differences from theoretical validation, and link or point to the raw BACKTEST report if one exists.
- Save strategy logs under `04_backtest_strategy/backtest_logs/`.
- Output `04_backtest_strategy/backtest_logs/signal_log.jsonl` for Phase B alignment validation. Each line should be JSON: `{"date": "YYYY-MM-DD", "signals": {"SYM": {"factor": float, "direction": 1|-1|0}}}`.
- The bundled engine also writes `equity_curve.csv`, `performance_metrics.csv`, `trades.csv`, and `position_return_detail.csv`.

After Step 5, run:

```bash
python scripts/check_step5_strategy.py /home/coder/project/replication/report-replication/{report_id}
```

Then update `03_factor_validation/factor_validation_report.html` with Phase B alignment results.

### 6. Final Delivery Summary

Generate `06_delivery/final_delivery_summary.md` after all available artifacts are complete. Keep it concise and decision-oriented:

- What the report says.
- Whether the factor is effective.
- Whether BACKTEST ran successfully.
- Where the reports, strategy, logs, and validation artifacts are.
- Key assumptions, risks, blockers, and next steps.

If any required stage fails, also create `failure_report.md`.

### 7. Run Quality Gate

Before final delivery, run:

```bash
python scripts/quality_gate_check.py /home/coder/project/replication/report-replication/{report_id}
```

If the command reports errors, do not deliver as complete. Fix the errors and rerun, or provide `failure_report.md` and state that the project is blocked rather than complete.

## Quality Gates

Before final delivery, verify:

- All required artifact paths exist, or blockers are documented.
- The translation is complete enough to preserve the report structure.
- Every reconstructed formula has variables and assumptions.
- `02_factor_reproduction/reference_implementation.py` exists and contains function-level reference code.
- Data preparation records Pandadata provider/method, cache path, metadata path, symbols, period, adjustment type, frequency, missing-value handling, and data availability assumptions. If a non-Pandadata source is used, the report must explain why Pandadata was insufficient.
- No credential values are written into `manifest.json`, HTML/Markdown reports, logs, CSVs, or committed files.
- Factor validation uses real traceable data; no synthetic, mock, or random market data is used to prove effectiveness.
- If validation data is insufficient, the conclusion is inconclusive.
- Factor validation includes audit controls, IS/OOS or documented blocker, parameter stability, cost sensitivity or documented blocker, and baseline comparisons.
- The HTML report includes the required sections, charts, metrics, and traceable source captions.
- Chart explanation blocks are beginner-readable, chart-specific, non-mechanical, and include the five required parts.
- `04_backtest_strategy/backtest_report.html` is a Chinese reader-facing explanation when the BACKTEST engine output is not Chinese-readable; any raw engine HTML is preserved separately and referenced.
- BACKTEST was actually run through `scripts/local_backtest.py` or a documented external runner, or failure logs are saved.
- `06_delivery/final_delivery_summary.md` exists, or `failure_report.md` explains why completion was blocked.

## References

- `references/output_contract.md`: required files and acceptance criteria.
- `references/factor_validation_checklist.md`: factor validation metrics, charts, and conclusion standards.
- `references/factor_audit_and_robustness.md`: leakage, look-ahead, overfitting, sample split, and robustness rules.
- `references/backtest_engine.md`: BACKTEST strategy generation and execution rules.
- `references/data_sources.md`: data source and provenance rules.
- `references/replication_lessons_learned.md`: historical failure cases and guardrails.
