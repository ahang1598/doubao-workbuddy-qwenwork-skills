# Data Source Rules

Use real, traceable data for factor validation and BACKTEST execution. Pandadata is the default production market-data source for price, volume, and daily bar data.

## Default Pandadata Source

Use WorkBuddy `call_pandadata` before factor validation or BACKTEST when the report requires daily market data:

```bash
python WorkBuddy call_pandadata \
  --asset-type stock \
  --symbols 000001.SZ 600000.SH \
  --start-date 20250101 \
  --end-date 20250131 \
  --output /home/coder/project/replication/report-replication/{report_id}/03_factor_validation/data_cache/pandadata_market_data.csv \
  --project-dir /home/coder/project/replication/report-replication/{report_id}
```

Supported `--asset-type` values:

| Asset type | Pandadata method |
| --- | --- |
| `stock` | `get_stock_daily` |
| `index` | `get_index_daily` |
| `future` | `get_future_daily` |
| `hk` | `get_hk_daily` |
| `us` | `get_us_daily` |

The downloader writes a normalized CSV or Parquet with at least `date`, `symbol`, and `close`, plus a sidecar metadata JSON. Use this cache as the market-data input for `scripts/local_backtest.py`.

Credentials must be provided through `WorkBuddy-managed authentication`, `WorkBuddy-managed authentication`, `WorkBuddy-managed authentication`, or `WorkBuddy-managed authentication`. Do not copy credential values into project artifacts.

## Required Provenance

Record the following in `manifest.json` and the HTML reports:

- Data provider or file source.
- Pandadata SDK method, local cache path, metadata path, URL, database path, or BACKTEST config source.
- Symbols/universe.
- Sample period.
- Frequency.
- Adjustment rules.
- Data availability timestamp or publish-time assumption when relevant.
- Missing-value handling.
- Whether credential values were excluded from persisted artifacts.

If a non-Pandadata source is used, record the concrete reason Pandadata could not supply the required dataset.

## Prohibited Data

Do not use synthetic, mock, or randomly generated market data to prove factor effectiveness.

A fixed-seed random factor is allowed only as a negative-control baseline on the same real return data used by the target factor.

## Insufficient Data

If data cannot support the report's factor test:

- Keep the required report section.
- State the concrete blocker in Chinese.
- Mark the conclusion as `inconclusive`.
- Create or update `failure_report.md` if the project cannot proceed.
