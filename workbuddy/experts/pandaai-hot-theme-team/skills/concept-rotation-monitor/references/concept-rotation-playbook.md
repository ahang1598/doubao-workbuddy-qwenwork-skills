# Concept Rotation Monitor Playbook

Routing, the bottom-up aggregation formulas, weighting/breadth definitions, the membership-snapshot rule, report skeleton, empty-data handling, and QA for `concept-rotation-monitor`. Read this before the first run in a session. The exact call contract for the three interfaces still comes from the `pandadata` skill.

## 1. Routing table

| Need | Method | Key params |
|---|---|---|
| Concept universe / new concepts | `get_concept_list` | `concept` (optional), `start_date`, `end_date` |
| Constituents (as-of a date) | `get_concept_constituents` | `concept`, `concept_stock` (optional), `date`, `fields` |
| Constituent daily returns | `get_stock_daily` | `symbol`, `start_date`, `end_date` |
| Window bounds / trading days | `get_last_trade_date`, `get_trade_cal` | per `pandadata` |

## 2. Field models

**`get_concept_list`** — `name` (概念名称), `date` (概念纳入/成立日期). A recent `date` = newly-formed concept.

**`get_concept_constituents`** — `concept` (概念名称), `concept_stock` (成分股代码), `date` (股票纳入该概念日期). Pass `date=` to get membership **as of** that day; membership is time-varying.

**`get_stock_daily`** — per constituent OHLCV; use the close series to compute window returns.

There is **no concept-level price field** anywhere — the concept signal is always computed bottom-up.

## 3. Bottom-up aggregation formulas

For a concept `C` with constituents `{s_i}` (as of the snapshot date) and window `W` trading days:

- **Constituent return** `r_i(W) = close_i(t) / close_i(t−W) − 1`. Drop `s_i` if either close is missing (suspension/new listing); record the drop count.
- **Concept momentum**:
  - Default **equal-weight median**: `mom_median(C,W) = median_i r_i(W)` (robust to a few runners).
  - Optionally **equal-weight mean**: `mom_mean(C,W) = mean_i r_i(W)` (state that extremes can dominate).
  - State which you used. There is **no market-cap concept index**; equal-weight is the default because concepts have no natural weighting.
- **Breadth**: `breadth(C,W) = share of i with r_i(W) > 0` (or share above own 20D MA). High momentum + low breadth = a narrow move led by a few names.
- **Short vs long spread**: `accel(C) = mom(C, W_short) − mom(C, W_long)` (e.g. 5D − 20D). Positive = 升温/轮入; negative = 降温/轮出.

## 4. Membership-snapshot & overlap rules

- **Snapshot the membership.** Always pass an explicit `date` to `get_concept_constituents` matching the end of the return window (or the analysis date). Computing a past window return on **today's** membership is lookahead/survivorship — do not do it. Label the snapshot date in the report.
- **Overlap / non-additivity.** A single stock is in many concepts; concept momenta are correlated and **not additive**. Never sum concept returns or present concept leaders as independent exposures — a hot leader inflates every concept it belongs to. When a cluster of top concepts shares the same driver names, say so.
- **Constituent-count context.** Report each concept's constituent count. A 3-name concept's "momentum" is noisy; require a minimum count (e.g. ≥5, state it) for the main leaderboard and list tiny concepts separately.

## 5. New-concept handling

- A concept whose `get_concept_list` `date` is within the lookback (e.g. last 30 trading days) is **newly formed** — flag it. It has little price history; its window momentum may be undefined or unstable. List new concepts in their own section, not ranked against seasoned ones.

## 6. Report skeleton (8 sections)

```
# A股概念题材热度轮动 · <范围> · <窗口/快照日>
## 1. 摘要              （范围、动量窗口、成分快照日、口径(等权中位/均值)、3–5 条要点）
## 2. 概念全景          （概念数、成分数分布、新成立概念数）
## 3. 动量排名          （按短窗口动量排名，标注等权口径与窗口、成分数门槛）
## 4. 广度对照          （动量旁列广度%，区分普涨 vs 少数拉动）
## 5. 轮动信号          （短−长动量差：升温/轮入 vs 降温/轮出）
## 6. 新概念雷达        （近端成立的概念，单列，历史短不可比）
## 7. 风险提示          （概念重叠不可加、措辞克制、非投资建议）
## 8. 数据说明          （表格见下）
```

数据说明表：`数据模块 | 来源接口 | 查询窗口 | 成分快照日 | 动量口径/窗口 | 覆盖概念/成分数 | 剔除数 | 备注`。

## 7. Empty-data / failure handling

- If `get_concept_list` or `get_concept_constituents` returns empty for the window, keep the heading and write `无数据（<method>，<window>）`.
- If a whole-market pull over every concept is heavy, restrict to the most-populated or user-named concepts and note the restriction under 数据说明.
- If constituents' daily data is partly missing, drop those names from the concept aggregate and state the drop count; if too few remain (< the min count), mark the concept 样本不足 rather than reporting an unstable number.
- If membership at the snapshot date is unavailable, state it and fall back to the nearest available snapshot with the date noted — never silently use today's membership for a past window.

## 8. QA checklist

- [ ] Concept momentum computed bottom-up; weighting (等权 median/mean) and window named.
- [ ] Constituent membership snapshot-dated via explicit `date`; no lookahead on today's membership.
- [ ] Breadth reported beside momentum; narrow moves flagged.
- [ ] Short−long spread used for the rotation read (升温/降温).
- [ ] Concept overlap / non-additivity stated; leaders not treated as independent exposures.
- [ ] Constituent counts shown; tiny concepts held to a min-count or listed separately.
- [ ] Newly-formed concepts flagged and not ranked against seasoned ones.
- [ ] Dropped-constituent counts stated; empty sections say `无数据` with method + window.
- [ ] Window / snapshot date labeled throughout.
- [ ] Wording factual; no directional calls; ends with the standard disclaimer.
