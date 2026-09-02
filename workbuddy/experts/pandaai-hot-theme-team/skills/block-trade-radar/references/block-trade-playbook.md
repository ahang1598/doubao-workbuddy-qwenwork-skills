# Block Trade Radar Playbook

Routing, the discount/premium formula and edge cases, direction/wash-print rules, aggregation rules, report skeleton, empty-data handling, and QA for `block-trade-radar`. Read this before the first run in a session. The exact call contract for `get_block_trade` and `get_stock_daily` still comes from the `pandadata` skill.

## 1. Routing table

| Need | Method | Key params |
|---|---|---|
| Block-trade prints (market / name) | `get_block_trade` | `symbol` (empty = whole market), `start_date`, `end_date`, `fields` |
| Same-day close (for 折溢价率) | `get_stock_daily` | `symbol`, `start_date`, `end_date` |
| Identity | `get_stock_detail` | `symbol` |
| Industry rollup | `get_stock_industry` / `get_industry_constituents` | `symbol` |
| Window bounds | `get_last_trade_date`, `get_trade_cal` | per `pandadata` |

## 2. `get_block_trade` field model

| Field | Meaning | Use |
|---|---|---|
| `symbol` | 股票代码 | keying |
| `date` | 交易日期 | keying, join key to daily close, timeline |
| `sequence_id` | 序列号 | print-level key (multiple prints per name per day) |
| `price` | 成交价 | numerator of 折溢价率 |
| `volume` | 成交量 (股) | scale |
| `amount` | 成交额 (元) | **primary scale / ranking** |
| `buyer` | 买方营业部/席位 | direction (机构专用 = 接盘) |
| `seller` | 卖方营业部/席位 | direction (机构专用 = 出货) |

Note: **折溢价率 is not a field** — compute it (section 3). `buyer`/`seller` are free-text seat names; the only structured signal is the literal `机构专用` marker and the `buyer==seller` equality.

## 3. Discount / premium (折溢价率) — compute it

```
折溢价率 = 成交价(price) / 同日收盘价(close) - 1
```

- `close` = `get_stock_daily` close for the **same `symbol` and same `date`** as the print. Always pull daily over the block-trade window and join on (`symbol`,`date`).
- Sign convention: **负 = 折价** (price below market — common; buyer demands a discount); **正 = 溢价** (price above market — rarer). `≈0` = 平价.
- Buckets (state thresholds you use): 深折价 (≤ −5%), 折价 (−5%~−1%), 平价 (−1%~+1%), 溢价 (> +1%). These are conventions — label them; adjust if the user asks.
- **Edge cases**: if the same-day close is missing (suspended, new listing, data gap), mark 折溢价率 as `待补` for that print and exclude it from discount stats — never substitute the prior close silently. If the print `date` is not a trading day per the calendar, note it.

## 4. Direction & wash-print rules

- `机构专用` on **buyer** → institutional 接盘 (absorbing). On **seller** → institutional 出货 (distributing). Count net institutional flow as (机构买入额 − 机构卖出额) over the window; state it as a tendency, not identity.
- Seats are verbatim strings. Do **not** name a specific institution; `机构专用` is anonymous by design.
- **`buyer == seller` (same 营业部)** → likely 对倒 / 过券 (internal transfer). Flag separately and **exclude** from directional net and from discount-signal reads. It is a print, not a beneficial-ownership change.
- Foreign/中央结算/QFII-style seat strings: report verbatim; do not reclassify.

## 5. Aggregation rules

- A large trade is often split into many prints. **Aggregate per `symbol` per `date`**: 笔数, 总成交额, 总成交量, 成交额加权折溢价率 (Σ amount·折溢价 / Σ amount).
- For the market scan, roll up per name over the whole window: total amount, print count, mean/weighted discount, net institutional direction, and a repeat-discount flag (≥N discounted prints across ≥M days — state N, M).
- Rank tables: (a) largest by 总成交额; (b) deepest 加权折价; (c) notable 溢价; (d) repeat-discount names; (e) net institutional 净接盘 / 净出货.

## 6. Report skeleton (8 sections)

```
# A股大宗交易折溢价雷达 · <范围> · <窗口>
## 1. 摘要              （范围、窗口、快照日、去重后名称数/总成交额、3–5 条要点）
## 2. 大宗成交总览      （笔数、涉及名称、总成交额；折溢价基准=get_stock_daily 收盘）
## 3. 折溢价分布        （深折价/折价/平价/溢价 各多少，标注阈值口径与收盘基准）
## 4. 机构专用方向      （净接盘 vs 净出货；机构专用为匿名席位，不指名）
## 5. 成交额/折价榜      （成交额 Top、最深折价、显著溢价、重复折价名称）
## 6. 对倒式提示        （buyer==seller 的打款，单列并排除出方向净额）
## 7. 风险提示          （克制措辞，非投资建议）
## 8. 数据说明          （表格见下）
```

数据说明表：`数据模块 | 来源接口 | 查询窗口 | 返回笔数/名称数 | 快照日/交易日区间 | 折溢价基准 | 备注`。

## 7. Empty-data / failure handling

- If `get_block_trade` returns empty for the window, keep the headings and write `无数据（get_block_trade，<window>）`. No block trades is itself a finding.
- If a whole-market pull is heavy or times out, narrow the window and note it under 数据说明.
- If the same-day close is missing for a print, mark its 折溢价率 `待补` and exclude it from discount buckets; state how many prints were excluded.
- If a print's `date` falls on a non-trading day per `get_trade_cal`, note it rather than dropping silently.

## 8. QA checklist

- [ ] 折溢价率 computed as `price / 同日收盘价 − 1`, with the `get_stock_daily` close named as the basis.
- [ ] Missing-close prints marked `待补` and excluded from discount stats (count stated).
- [ ] Prints aggregated per `symbol`+`date` (and per name over window) before ranking.
- [ ] `机构专用` read as anonymous seat; no named institution invented.
- [ ] `buyer==seller` prints flagged and excluded from the directional net.
- [ ] Discount buckets/thresholds labeled as conventions.
- [ ] Window / snapshot date / trade-date range labeled.
- [ ] Source-note table present; empty sections say `无数据` with method + window.
- [ ] Wording factual; no directional calls or trading instructions.
- [ ] Ends with the standard disclaimer.
