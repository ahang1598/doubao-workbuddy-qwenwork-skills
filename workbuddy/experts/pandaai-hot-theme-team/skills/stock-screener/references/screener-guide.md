# Stock Screener Guide

Use this reference when a stock screen has more than one condition, requires point-in-time handling, or mixes financial, market, shareholder, and event data.

## Normalized Filter Schema

Represent each user condition as an object with these fields before execution:

| Field | Meaning |
|---|---|
| `id` | Stable short name, such as `cash_dividend_3y` |
| `source_text` | Original user phrase |
| `universe_effect` | Whether it narrows the starting universe before data fetch |
| `metric` | Business metric being tested |
| `operator` | `=`, `!=`, `>`, `>=`, `<`, `<=`, `between`, `in`, `not_in`, `rank_top_n`, or `rank_percentile` |
| `threshold` | Numeric, categorical, date, or list threshold |
| `window` | Lookback period and frequency, such as `3 fiscal years`, `60 trading days`, or `latest report` |
| `date_basis` | Trading date, report period, announcement date, or disclosure date |
| `methods` | Pandadata method names to verify through `pandadata` |
| `pass_rule` | Plain-language pass/fail rule |
| `missing_policy` | Exclude, keep with warning, or ask user |

Ask a clarification when any required field changes the meaning materially. Otherwise choose the conservative interpretation and state it.

## Condition Map

| User intent | Interpretation guidance | Candidate methods |
|---|---|---|
| 当前可交易A股, 剔除停牌, 剔除ST | Start from a date-specific tradable pool and remove special-treatment or non-trading names. | `get_trade_list`, `get_stock_status_change`, `get_stock_detail` |
| 上市满N年/天 | Compare listing date or first available trading date to the screening date. | `get_stock_detail`, `get_stock_daily` |
| 行业/概念/指数成分 | Use constituent methods before heavier per-stock calls. Confirm industry taxonomy with the user if multiple taxonomies exist. | `get_industry_constituents`, `get_concept_constituents`, `get_index_weights` |
| 市值, 成交额, 涨跌幅, 均线, 新高新低 | Use daily data on the screening date or an explicit trading window. Prefer adjusted data for moving averages when the user asks about price trends. | `get_stock_daily`, `get_stock_daily_pre` |
| PE/PB/ROE/负债率/利润增速 | Confirm fields in financial or market data docs. Use latest disclosed report period not later than the screen date. | `get_fina_reports`, `get_fina_performance`, `get_fina_forecast`, `get_stock_daily` |
| 连续分红, 股息率 | Define whether the window is fiscal years or calendar years. Dividend yield usually needs dividend amount divided by screen-date price; label it as calculated. | `get_stock_cash_dividend`, `get_stock_dividend_amount`, `get_stock_daily` |
| 北向持股/加仓 | Compare holdings across two dates in the requested window. If the user says `加仓`, define absolute shares, market value, or holding ratio. | `get_hsgt_hold` |
| 两融余额/变化 | Compare margin financing or securities lending values across the requested dates. | `get_margin` |
| 股东户数减少/集中度提升 | Compare holder counts between report dates. Require a minimum time gap if the user does not specify one. | `get_holder_count`, `get_top_holders` |
| 质押率低于N% | Use pledge statistics, prefer latest disclosure not later than the screen date. Exclude missing data unless the user allows unknowns. | `get_stock_pledge_stat` |
| 股东增减持 | Separate announced plans from completed changes. State whether the filter uses plan size, completion status, or announcement recency. | `get_stock_shareholder_change` |
| 解禁风险 | Define look-ahead horizon, such as next 30/90/180 days, then compare unlock shares or market value to float shares or market cap when possible. | `get_restricted_list`, `get_stock_daily`, `get_stock_detail` |
| 龙虎榜活跃 | Treat as event evidence, not a quality score. Use explicit windows and count/frequency rules. | `get_lhb_list` |

## Execution Order

1. Establish `screen_date`, trading calendar, and initial universe.
2. Apply cheap universe filters: exchange, board, industry, concept, index membership, ST, listing age, and explicit exclusions.
3. Apply bulk market filters: market cap, turnover, liquidity, price change, and trend windows.
4. Apply bulk or period financial filters: latest disclosed report, financial growth, leverage, profitability, and forecast events.
5. Apply corporate action filters: dividends, unlocks, pledge, shareholder count, top holders, and shareholder changes.
6. Apply capital-flow filters: northbound holdings, margin data, and abnormal trading.
7. Apply ranking, tie-breakers, and final formatting.

Prefer the filter with the highest expected elimination rate when two filters have similar API cost. For per-symbol calls, operate only on the surviving universe.

## Output Contract

Return Markdown with these sections unless the user requests another format:

1. `筛选口径`: normalized criteria, screen date, universe, and unresolved assumptions.
2. `筛选漏斗`: one row per layer with input count, output count, eliminated count, method, parameters, and data date.
3. `结果清单`: final stocks with code, name, all condition values, report periods or data dates, and notes.
4. `缺失与剔除`: missing data, failed API calls, skipped rows, and whether they were excluded.
5. `复跑信息`: saved JSON path when created, plus method/parameter summary.
6. `声明`: fixed non-investment-advice disclaimer.

When saving JSON, use this shape:

```json
{
  "screen_date": "YYYY-MM-DD",
  "universe": "description",
  "criteria": [],
  "funnel": [],
  "results": [],
  "missing_data": [],
  "api_calls": [],
  "disclaimer": "本筛选结果基于公开数据与规则化条件生成，仅供研究参考，不构成任何投资建议。"
}
```

## QA Checklist

- Confirm every method and parameter against the `pandadata` skill before calling it.
- Confirm every date used for a financial or event row is not later than `screen_date`.
- Confirm all final rows have evidence values for every strict filter.
- Confirm rankings are applied after hard filters and are labeled separately.
- Confirm empty API results are reported as evidence, not silently ignored.
- Confirm the final report includes data cutoff dates and the fixed disclaimer.
