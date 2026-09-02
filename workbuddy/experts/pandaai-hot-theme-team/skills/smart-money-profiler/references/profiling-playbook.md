# Smart Money Profiling Playbook

Read this playbook when building or revising a smart-money profile. It is a compact operating guide, not a replacement for the exact Pandadata API documentation. Always confirm method signatures and fields with the `pandadata` skill before calling.

This skill is **descriptive behavior tracking**. It does not build backtestable factors (→ `skill-a1-lhb-tracking`), does not grade crowding/over-heating risk (→ `agent-crowding-risk-monitor`), and does not produce a single-day market snapshot (→ `market-daily-review`). Keep within: actor identity + cross-period behavior + multi-source consensus/divergence.

## Default Scope

- Subject: one A-share stock (`XXXXXX.SH` / `XXXXXX.SZ`) **or** one capital actor (a 营业部/席位 name such as `机构专用`, `深股通专用`, or a labeled 游资 seat).
- 龙虎榜 lookback: latest ~6–12 months of 上榜 episodes unless the user narrows it.
- Northbound window: latest ~3–6 months of `get_hsgt_hold` history for streak detection; extend on request.
- Win-rate validation windows: 上榜后 5 / 10 / 20 个交易日 (counted in trading days via `get_trade_cal` / `get_prev_trade_date`).
- Output: Markdown profile report; persistent archive at `profiles/seats.json`.

## Pillar 1 — Seat Identity & Profiling

### Data path

1. `get_lhb_list` — find 上榜 episodes (`symbol`, `date`, `type`, `reason`, `amount`) for the stock/date range. Use it to enumerate which days a name appeared.
2. `get_lhb_detail` — per episode, pull seats with `side` (`buy`/`sell`/`cum`), `rank`, `agency`, `b_value`, `s_value`, `reason`. This is the source of seat identity and direction.
3. `get_stock_daily` — pull post-episode prices for win-rate / holding-period validation.
4. `get_stock_industry` / `get_stock_detail` / `get_concept_constituents` — attribute the stock to industry/concept to build the seat's 偏好板块.

### Seat label dictionary (editable, rule-matched — NOT official)

Labels are derived by matching the `agency` text. State explicitly in every report: **席位标签来自规则匹配，不等于官方认定**. When no rule matches confidently, use `未分类`.

| Label | Match rule (on `agency` text) | Notes |
|---|---|---|
| `机构专用席位` | `agency` 等于或包含 `机构专用` | 公募/保险/私募等机构通道的汇总席位；不指向具体机构。 |
| `陆股通/外资通道` | 包含 `深股通专用` 或 `沪股通专用` | 北向资金的龙虎榜通道；与 `get_hsgt_hold` 口径不同，需分开标注。 |
| `知名游资营业部` | `agency` 命中可维护的游资营业部别名字典（见下） | 字典是人工维护的"江湖标签"，属推断，不等于实际操盘人。 |
| `量化/程序化席位` | 命中量化席位字典，或行为特征（高频上榜、买卖快进快出、分散标的）符合 | 行为特征仅作辅助，必须标注为"推断"。 |
| `普通营业部` | 是营业部名称但未命中游资/量化字典 | 默认归类。 |
| `未分类` | 无法匹配或信息不足 | 不要硬猜。 |

Maintainable alias dictionary (extend over time; seed entries are examples — verify before asserting a 江湖名号):

```text
# 游资营业部别名字典（示例，需人工维护；标签=推断，非官方）
known_hot_money:
  - match_contains: "宁波"          # 例：宁波系，仅作分组标签
    tag: "游资-宁波系(推断)"
  - match_contains: "拉萨"          # 例：常见量化/北向相关通道聚集地
    tag: "席位-拉萨通道(推断)"
  - match_contains: "上海超级"      # 占位示例
    tag: "游资(推断)"
# 量化/程序化席位字典（示例）
known_quant_seats:
  - match_contains: "深股通专用"    # 通道，非量化，仅示意规则形态
    tag: "陆股通/外资通道"
```

The dictionary is the maintainable part of identity classification. Treat every non-trivial 游资/量化 tag as inference and append `(推断)`.

### Seat profile metrics (derive and label each)

- 上榜频次 (`appearance_count`): number of distinct (`symbol`,`date`) episodes the seat appears in, split by `side`.
- 累计净买卖 (`cum_net_value`): `sum(b_value) − sum(s_value)` over the window. Exclude `side == "cum"` rows.
- 上榜后 N 日胜率 (`win_rate_Nd`): share of buy episodes where `get_stock_daily` close at +N trading days exceeds the 上榜当日 close. Define N = 5/10/20. State the price basis (后复权 via `get_stock_daily` adjusted fields if used) and that it is descriptive of past episodes.
  - `次日(或N日)收益 = 收盘价[T+N] / 收盘价[T] − 1`, where `T` = 上榜日, counted in trading days.
- 平均持有/退出周期 (`avg_hold_days`): for seats that both buy then later sell the same name, average trading days between the buy episode and the next sell episode of that name. Mark as approximate when 买卖配对不完整.
- 偏好板块/风格 (`fav_sectors`): distribution of episodes' industry/concept (via `get_stock_industry` / `get_concept_constituents`) and typical `reason` text (涨幅偏离/换手/连板 等).

### Outputs

- A **seat profile card** for one actor: identity label (+ 规则匹配/推断 tag), 上榜频次, 累计净买卖, 5/10/20 日胜率 (with sample sizes), 平均持有/退出周期, 偏好板块, recent episodes table.
- A **"近期活跃知名资金主体"榜**: rank recently-active labeled seats by appearance/净买卖 over the window. This is an activity roster, not a buy list.

## Pillar 2 — Northbound Cross-Period Behavior

### Data path

- `get_hsgt_hold` — time series of `date`, `shares_num`, `holding_ratio`, `adjusted_holding_ratio`. Sort by `date` ascending before any streak logic. (Note: this is the holding-disclosure series; it can lag the trade date — say so.)
- `get_index_daily` / `get_stock_daily` — align with index/stock price to detect divergence.

### Metrics

- 加仓/减仓 streak: longest run of consecutive same-sign change in `holding_ratio` (or `shares_num`). Report `streak_direction`, `streak_len` (disclosure points), and cumulative Δ over the streak.
- 集中度/持股比例变化: change in `holding_ratio` over the window; flag sustained climbs vs choppy moves.
- 板块轮动迁移 (optional, multi-stock): compare northbound direction across a board's constituents (`get_concept_constituents` / `get_stock_industry`) to see where北向 is rotating toward/away.
- 与指数背离: northbound 加仓 while the stock/index falls (or vice versa) over the same window → label `与价格背离，需要关注`.
- 持续性建仓 vs 短期博弈: a long one-directional streak with rising holding_ratio reads as `持续性建仓(描述)`; brief reversing moves read as `短期博弈(描述)`. Both are descriptions, not forecasts.

## Pillar 3 — Capital Consensus vs Divergence

Overlay four capital routes on the **same symbol and window**, derive each route's net direction, then classify.

| Route | Method | Net-direction rule |
|---|---|---|
| 北向 | `get_hsgt_hold` | Δ`holding_ratio` (or `shares_num`) over window > 0 → 买入方向；< 0 → 卖出方向。 |
| 机构席位 | `get_lhb_detail` | sum over `agency == 机构专用` rows of (`b_value` − `s_value`) > 0 → 买入方向。 |
| 融资盘 | `get_margin` | Δ`margin_balance` over window > 0 (净融资买入) → 买入方向；用 `buy_on_margin_value` 辅助。 |
| 大宗买方 | `get_block_trade` | net `amount` where a notable `buyer` (e.g. `机构专用`) dominates vs `seller` → 买入方向；折溢价看 `price` 对当日收盘。 |

Classification rules (state every route, including `无数据`):

- `资金合力(同向买入)`: ≥3 of the 4 routes net-buy in the same window, none strongly opposing. List on the **资金合力榜**.
- `资金分歧(对打)`: at least one route net-buys while another net-sells with comparable magnitude. List on the **资金分歧榜**, naming which route buys and which sells (e.g. `北向加仓 vs 机构席位净卖出`).
- `证据不足`: 2 or more routes have no data, or magnitudes are negligible → say so, do not force a verdict.

After-the-fact confirmation: pull `get_stock_daily` for the window after the consensus/divergence was observed and describe whether price followed the majority direction. This is descriptive event review, **not** an IC/factor evaluation.

## Profile Archive Schema — `profiles/seats.json`

Persistent, append/update ledger. Suggested shape:

```json
{
  "schema_version": "1.0",
  "generated_by": "smart-money-profiler",
  "last_updated": "YYYYMMDD",
  "seats": [
    {
      "agency": "机构专用",
      "label": "机构专用席位",
      "label_basis": "规则匹配",
      "appearance_count": {"buy": 0, "sell": 0},
      "cum_net_value": 0.0,
      "win_rate": {"d5": null, "d10": null, "d20": null, "samples": 0},
      "avg_hold_days": null,
      "fav_sectors": [],
      "recent_episodes": [
        {"symbol": "000001.SZ", "date": "YYYYMMDD", "side": "buy",
         "b_value": 0.0, "s_value": 0.0, "rank": 1, "reason": "", "source": "get_lhb_detail"}
      ],
      "data_window": {"start": "YYYYMMDD", "end": "YYYYMMDD"}
    }
  ]
}
```

Update rules:
- Key seats by exact `agency` string. Merge new episodes into `recent_episodes`, de-duplicating on (`symbol`,`date`,`side`,`rank`).
- Re-derive `appearance_count`, `cum_net_value`, `win_rate`, `avg_hold_days` from the accumulated `recent_episodes` after merge.
- Idempotent per date: re-running the same date must not double-count episodes.
- Never write a derived metric without also writing its `samples`/`data_window` so freshness is auditable.

## Report Skeleton

Use this order unless the user requests a custom layout.

1. `画像摘要`: 3–6 bullets — who the subject is (stock or actor), the dominant capital behavior observed, key consensus/divergence finding, and data freshness.
2. `席位身份与画像`: seat identity table (label + 规则匹配/推断 tag), profile card(s), recent episodes, 上榜后 5/10/20 日胜率 with sample sizes.
3. `北向跨期行为`: holding_ratio time series summary, streak(s), 集中度变化, 与指数背离 note.
4. `资金合力 / 分歧`: four-route direction table, 合力/分歧 verdict with every route listed, 事后走势 description.
5. `中长期印证`(optional): `get_top_holders` / `get_holder_count` quarterly institutional in/out to corroborate the short-term picture.
6. `数据附录`: method-by-method source table — `数据模块 | 来源接口 | 查询窗口 | 返回行数 | 最新日期/数据期 | side/方向 | 备注`.

## Empty-Data Handling

- If `get_lhb_detail` returns no rows for the window: keep the 席位 section, write `无龙虎榜明细数据（get_lhb_detail，窗口 YYYYMMDD–YYYYMMDD）`, and proceed with northbound only.
- If `get_hsgt_hold` returns no rows (e.g. non-连通标的): write `无北向持股数据`, skip streak logic, do not estimate.
- If a consensus route has no data: mark that route `无数据` in the four-route table and downgrade the verdict toward `证据不足` rather than inferring direction.
- Never fill a missing denominator (e.g. float for 集中度) with an assumption; degrade to a qualitative note.

## QA Checklist

- Subject (stock or seat) is normalized and shown consistently.
- Every seat label carries `规则匹配` or `推断` and the disclaimer that labels are not official.
- `side == "cum"` rows are excluded from net buy/sell math.
- Win-rate and holding-period figures show their trading-day window, price basis, and sample size.
- Northbound streaks report direction, length, magnitude, and the divergence note separately.
- Consensus/divergence verdict lists all four routes including `无数据` ones.
- `profiles/seats.json` updates are idempotent and de-duplicated; derived metrics carry `samples`/`data_window`.
- Empty data is disclosed with method + window, not hidden.
- No factor/backtest metrics (IC/RankIC/分组回测), no crowding-risk grade, no single-day全市场 snapshot.
- Final disclaimer present exactly: `本报告基于公开数据与规则化分析生成，仅供研究参考，不构成任何投资建议。`
