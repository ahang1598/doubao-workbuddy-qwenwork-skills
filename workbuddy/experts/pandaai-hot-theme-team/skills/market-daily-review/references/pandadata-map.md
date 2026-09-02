# Pandadata Map

Use this map to plan the daily review. Always confirm exact signatures and fields with the `pandadata` skill before calling any method.

## Core Date And Universe

| Need | Preferred method | Notes |
| --- | --- | --- |
| Latest trading day | `get_last_trade_date` | Use when the user says 今日复盘 or does not specify a date. |
| Trading calendar | `get_trade_cal` | Confirm whether the target date is open. |
| Tradable A-share universe | `get_trade_list` | Use as the stock list for breadth and batch行情 queries. |

## Market Sections

| Report section | Preferred methods | Derived metrics |
| --- | --- | --- |
| 指数概览与估值 | `get_index_daily`, `get_index_indicator` | Index return, turnover, PE/PB, valuation percentile. |
| 市场宽度与情绪 | `get_stock_daily` or `get_stock_rt_daily`, `get_stock_status_change` | Advancers/decliners, limit-up/down counts, turnover leaders, ST/status changes. |
| 行业与概念热点 | `get_industry_constituents`, `get_concept_list`, `get_concept_constituents` | Industry/concept returns by constituent aggregation, representative leading stocks. |
| 龙虎榜与大宗 | `get_lhb_list`, `get_lhb_detail`, `get_block_trade` | Listed reasons, seat buy/sell amounts, net buy/sell, block-trade premium/discount. |
| 两融与北向 | `get_margin`, `get_hsgt_hold` | Margin balance and change, northbound holding increase/decrease rankings. |

## Degradation

If a full-market or concept aggregation call is too slow or unavailable:

1. Keep trade-date, index, and valuation sections.
2. Keep 龙虎榜 and block-trade sections if available.
3. Replace market breadth with a clear unavailable note instead of estimating.
4. Add the skipped interface names and reason under `数据说明`.
