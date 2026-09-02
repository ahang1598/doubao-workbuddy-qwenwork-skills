# Factor Validation Checklist

Use this checklist before judging whether a reconstructed factor is effective.

## Data

- Market data must be real and traceable.
- Record provider, file path or database path, symbols, frequency, sample period, adjustment rules, and missing-value handling.
- Synthetic, mock, or randomly generated market data is prohibited for proving factor effectiveness.
- A fixed-seed random factor is allowed only as a negative-control baseline on the same real returns.
- If data is insufficient, keep the required report sections and label the conclusion as `inconclusive`.

## Signal And Bias Audit

- Verify factor calculation order.
- Verify signal timestamp and data availability time.
- Apply at least one-period signal lag unless the report proves same-period execution is valid.
- Check look-ahead leakage, price leakage, survivorship bias, sample selection, and missing-value bias.
- Record execution price, rebalance timing, cost assumptions, and sample split.
- Strategy must output `backtest_logs/signal_log.jsonl`, recording factor value and trading direction by date/symbol.

## Metrics

At minimum compute or document blockers for:

- IC, Rank IC, ICIR, IC t-statistic, positive IC ratio.
- IC distribution, rolling IC, yearly or quarterly IC.
- Quantile/group returns, monotonicity, long-short returns, long-only/short-only legs when applicable.
- Full sample, IS, OOS, and walk-forward when data allows.
- Annual return, volatility, downside volatility, Sharpe, Sortino, Calmar, max drawdown, max drawdown duration, win rate, profit/loss ratio, skewness, kurtosis, VaR/CVaR, turnover.
- Parameter stability and transaction-cost sensitivity when data allows.

## Baselines

Benchmark against:

- Target factor.
- Reverse factor.
- Fixed-seed random factor.
- Equal-weight buy-and-hold.
- Zero-return / always-flat baseline.

Save benchmark returns or metrics to:

```text
03_factor_validation/data/benchmark_comparison.csv
```

## BACKTEST Alignment

After the BACKTEST run:

- Compare theoretical validation curves with BACKTEST actual equity/NAV.
- Explain data source, date range, frequency, weighting, execution, fees, slippage, margin/capital, final NAV, and max drawdown differences.
- Save audit data to `03_factor_validation/data/backtest_alignment_audit.csv`.
- Save the alignment chart to `03_factor_validation/charts/16_backtest_alignment_nav.png` when actual equity is available.

## Required Chart Pack

All text rendered inside chart image files must be English ASCII only. Use the `Content` labels below for chart titles, axis labels, legends, annotations, and colorbar labels where they fit. Keep Chinese reader explanations in the HTML/Markdown text around each chart, not inside the PNG/SVG pixels.

| # | File | Content | Required |
| --- | --- | --- | --- |
| 1 | `01_ie_distribution.png` | factor distribution | yes |
| 2 | `02_ic_series.png` | IC time series | yes |
| 3 | `03_is_oos_ic_comparison.png` | IS/OOS IC comparison | yes |
| 4 | `04_cumulative_nav_equal_weight.png` | equal-weight validation NAV | yes |
| 5 | `05_cumulative_nav_strategy_direction.png` | strategy-direction validation NAV | yes |
| 6 | `06_drawdown.png` | drawdown | yes |
| 7 | `07_ic_distribution.png` | IC distribution | yes |
| 8 | `08_rolling_ic.png` | rolling IC | if data allows |
| 9 | `09_quantile_nav.png` | quantile NAV | yes |
| 10 | `10_quantile_return_bar.png` | quantile return bar chart | yes |
| 11 | `11_yearly_return_heatmap.png` | yearly/monthly heatmap | if data allows |
| 12 | `12_turnover_series.png` | turnover | if data allows |
| 13 | `13_data_coverage_heatmap.png` | coverage heatmap | yes |
| 14 | `14_missing_value_heatmap.png` | missing-value heatmap | yes |
| 15 | `15_benchmark_nav_comparison.png` | benchmark comparison | yes |
| 16 | `16_backtest_alignment_nav.png` | validation vs BACKTEST actual equity | if available |
| 17 | `17_parameter_stability_heatmap.png` | parameter stability | if executed |
| 18 | `18_cost_sensitivity.png` | cost sensitivity | if executed |
| 19 | `19_walkforward.png` | walk-forward | if executed |
