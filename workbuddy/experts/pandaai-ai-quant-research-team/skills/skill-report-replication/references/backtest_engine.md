# BACKTEST Engine Rules

Use the bundled local BACKTEST engine as the default strategy execution and backtest engine for Step 5.

## Entry Point

Default entrypoint:

```bash
python scripts/local_backtest.py /home/coder/project/replication/report-replication/{report_id} --market-data /home/coder/project/replication/report-replication/{report_id}/03_factor_validation/data_cache/pandadata_market_data.csv
```

Download the default market-data file from Pandadata first:

```bash
python WorkBuddy call_pandadata \
  --asset-type stock \
  --symbols 000001.SZ 600000.SH \
  --start-date 20250101 \
  --end-date 20250131 \
  --output /home/coder/project/replication/report-replication/{report_id}/03_factor_validation/data_cache/pandadata_market_data.csv \
  --project-dir /home/coder/project/replication/report-replication/{report_id}
```

Market data supports CSV or Parquet. The Pandadata downloader normalizes the required columns:

- `date`
- `symbol`
- `close`

Use `--date-col`, `--symbol-col`, and `--price-col` when the input uses different names.

If an external or user-provided market-data file replaces Pandadata, document why Pandadata was insufficient and record the source in `manifest.json`.

The engine reads signals from:

```text
04_backtest_strategy/backtest_logs/signal_log.jsonl
```

Each line must be:

```json
{"date": "YYYY-MM-DD", "signals": {"SYM": {"factor": 1.23, "direction": 1}}}
```

If the user explicitly supplies an external BACKTEST runner, document its module/CLI/executable, version or commit, config format, expected output files, and data source. Do not substitute another framework silently.

## Strategy Code

Generated strategy code must live at:

```text
04_backtest_strategy/strategy.py
```

Requirements:

- Keep all editable parameters in one visible section.
- Implement the reconstructed factor exactly enough for audit.
- Record factor value and direction for every evaluated date/symbol.
- Make execution assumptions explicit: rebalance timing, order timing, slippage, fees, margin, contract multiplier, capital allocation, and risk controls.
- Write a signal log to `04_backtest_strategy/backtest_logs/signal_log.jsonl`.
- The bundled engine applies configurable execution lag, fees, slippage, initial cash, annualization, and max per-symbol weight.

## Backtest Report

The user-facing report must live at:

```text
04_backtest_strategy/backtest_report.html
```

If BACKTEST emits a raw HTML/CSV/JSON report, preserve it as:

```text
04_backtest_strategy/backtest_report_raw.html
```

or another clearly named file under `04_backtest_strategy/backtest_logs/`, then reference it in the Chinese report.

The bundled engine writes:

```text
04_backtest_strategy/backtest_logs/equity_curve.csv
04_backtest_strategy/backtest_logs/performance_metrics.csv
04_backtest_strategy/backtest_logs/trades.csv
04_backtest_strategy/backtest_logs/position_return_detail.csv
03_factor_validation/data/direction_matrix_from_strategy.csv
03_factor_validation/data/portfolio_returns_dir_full.csv
03_factor_validation/data/backtest_alignment_audit.csv
```

## Alignment

After the BACKTEST run, update the factor validation report with Phase B alignment:

- Compare theoretical validation NAV with BACKTEST actual equity/NAV.
- Explain differences in data source, frequency, execution timing, position sizing, fees, slippage, and capital/margin rules.
- Save the audit table to `03_factor_validation/data/backtest_alignment_audit.csv`.
- Save the alignment chart to `03_factor_validation/charts/16_backtest_alignment_nav.png` when BACKTEST equity is available.
