---
name: concept-rotation-monitor
description: "Rank and track A-share concept/theme (概念题材) rotation with the Pandadata get_concept_list and get_concept_constituents interfaces, aggregating each concept's constituent daily returns from get_stock_daily into a concept-level momentum and breadth ranking, detecting newly-formed concepts, and reading short-vs-long-window momentum to see which themes are heating up or cooling down. Use when the user asks for 概念轮动, 题材轮动, 概念热度, 板块轮动, 概念动量排名, 题材涨幅榜, 新概念, 概念成分股, or an A-share concept-rotation monitor report."
---

## WorkBuddy PandaData 数据源覆盖

本技能在 WorkBuddy 专家包中运行时，所有实时和历史金融数据必须来自已连接的
`pandadata` Connector。若下文、参考资料或脚本提到 Python `panda_data` SDK、
AkShare、Tushare、网页抓取、直连 HTTP 或本地凭证，以本节为准：不得使用这些
方式获取正式数据。

1. 数据型任务必须先完成 `auth_status` 和至少一次真实的 `call_pandadata` 业务调用；在收到
   Connector 返回前，禁止输出分析、排名、数字结论或“无数据”。本 Skill 的流程不得绕过
   主 Agent 的最低接口调用清单。
2. 先按本 Skill 的 `references/pandadata-interface-contracts.md` 选择已登记方法和参数。只要任务能映射到已登记接口，
   就直接通过 `call_pandadata` 传入该业务方法和 `params`；常规调用前不得执行接口检索。
3. 仅当已登记方法被 Connector 明确报告为参数契约不兼容、字段契约变化或调用失败时，
   才对该方法调用一次 `get_method_doc`，修正参数后最多重试一次。
4. 仅当本地接口表没有匹配项，或 Connector 明确报告方法不存在/不受支持时，才调用
   `search_methods` 动态发现接口；不得靠猜测连续试用名称相近的 `get_*` 方法。
5. 只有 `call_pandadata` 实际返回 0 行时才允许写“无数据”。必须先完成一次复查调用：校验
   最新交易日与代码格式，放宽日期窗口，移除非必填过滤条件，或使用登记的备用参数；仍为
   0 行才可如实报告，并保留两次调用回执。0 行不得触发 `search_methods`。
6. 不向 `call_pandadata` 添加未登记参数或顶层行数限制；记录实际方法、参数、数据日期、
   频率、复权口径、行数、空值和错误状态。
7. 包内脚本只可处理 Connector 已返回的数据或执行纯本地计算与校验，不得自行联网取数。

最终答案必须包含“数据调用回执”表：接口、实际参数、状态、行数、数据日期范围和关键字段。
缺少回执表示任务未完成，必须继续调用工具而不是结束回答。

权限不足、配额限制、空结果、延迟发布和字段缺失都必须明确披露，不得切换到其他数据源
或用模型推断补数。


# Concept Rotation Monitor

Use this skill to **rank and track A-share concept/theme (概念题材) rotation**: aggregate each concept's **constituent daily returns** (from `get_stock_daily`) into a concept-level **momentum** and **breadth** ranking, detect **newly-formed concepts** (via inclusion dates), and compare **short-window vs long-window momentum** to see which themes are heating up or cooling down. Prefer Pandadata as the data source, keep every figure traceable to `get_concept_list` / `get_concept_constituents` / `get_stock_daily` and a date, and never invent concepts, constituents, returns, or rankings.

## Scope And Positioning (read first to avoid overlap)

This skill is the **concept/theme rotation** view. It is deliberately distinct from its siblings:

- Unlike `market-daily-review` (daily whole-market review that surfaces the *single day's* hot concepts as one section): this skill builds a **rotation time-series** — momentum over configurable windows, short-vs-long momentum spread, breadth, and new-concept detection across a lookback. If the user wants a one-day end-of-day review, hand off to `market-daily-review`.
- Unlike `stock-screener` (natural-language stock filter that may use concept membership as a *condition*): this skill ranks the **concepts themselves**, not stocks; the output is a theme leaderboard, not a stock shortlist. If the user wants stocks inside a theme filtered by fundamentals, hand off to `stock-screener`.
- Unlike `index-valuation-rotation` (industry/index **valuation** percentile and **industry** momentum): that works on标准行业 indices with valuation percentiles; this works on **market concepts/themes** (英伟达概念, etc.) built bottom-up from constituent returns, without valuation. Complementary lenses — industry vs theme.
- Unlike `portfolio-checkup` / `smart-money-profiler` (which use concept membership incidentally): the concept-rotation signal itself lives here.

## Concept Rotation Model (read before analysis)

There is **no concept price index field** — you build the concept signal **bottom-up** from constituent daily returns. Be explicit about every aggregation choice.

- **Concept universe (`get_concept_list`)** — returns `name` (概念名称) and `date` (概念纳入/成立日期). A recent `date` marks a **newly-formed concept** — flag these; a brand-new concept has little history and its "momentum" is not comparable to a seasoned one.
- **Constituents (`get_concept_constituents`)** — returns `concept`, `concept_stock` (成分股 code), and `date` (股票纳入该概念日期). **Constituent membership is time-varying** — pass a `date` to get the snapshot as of that day; do not use today's membership to compute last month's return (survivorship/lookahead). State the membership snapshot date.
- **Constituent returns (`get_stock_daily`)** — per constituent, compute the window return (e.g. 5D / 20D). Aggregate to the concept:
  - **Momentum** = the concept's aggregate constituent return over the window. Use **median** (robust) or **equal-weight mean**; state which. Equal-weight is the default (a concept has no natural cap weighting); note that a few extreme names can dominate a mean.
  - **Breadth** = share of constituents up over the window (e.g. % with positive return, or % above their own 20D MA). Momentum + breadth together separate a broad theme move from one or two runners.
- **Short vs long momentum** — compare a short window (e.g. 5D) to a long window (e.g. 20D/60D). Short ≫ long ⇒ **heating up / newly rotating in**; short ≪ long ⇒ **cooling / rotating out**. This spread is the rotation signal.
- **Concept overlap** — one stock belongs to many concepts; concept returns are **not independent**. Do not sum them or treat leaders as additive exposure; a hot stock lifts every concept it is in.

## Workflow

1. Resolve the target: a whole-market concept leaderboard, or a specific concept's constituents/timeline. Confirm the momentum windows (default 5D and 20D) and the lookback for new-concept detection.
2. Read `references/concept-rotation-playbook.md` before the first run in a session. Use it for the routing table, the bottom-up aggregation formulas, weighting/breadth definitions, the membership-snapshot rule, the report skeleton, empty-data handling, and the QA checklist.
3. Use the registered `get_concept_list`, `get_concept_constituents`, and `get_stock_daily` contracts in `references/pandadata-interface-contracts.md`, then call them directly through `call_pandadata`. Use `search_methods` only when no registered method covers the task, and use `get_method_doc` only after an explicit contract error; do not invent parameters, fields, symbols, or credentials.
4. Collect evidence:
   - Concept universe & new concepts: `get_concept_list` over the lookback.
   - Constituents as-of the snapshot date: `get_concept_constituents` with an explicit `date`.
   - Constituent daily returns: `get_stock_daily` over the momentum windows for the constituents.
   - Trading calendar: `get_last_trade_date` / `get_trade_cal` to bound windows and count trading days.
5. Compute per concept: window momentum (median / equal-weight mean, stated), breadth, short-vs-long spread, constituent count, and a new-concept flag. Rank concepts: strongest short-window momentum, biggest short−long acceleration (rotating in), biggest deceleration (rotating out), and highest breadth. Keep constituent counts and the membership snapshot date with every concept.
6. Generate the Markdown report following the skeleton in the playbook. Save to `reports/concept-rotation/<scope>-<date>.md` (e.g. `reports/concept-rotation/market-20260706.md`) unless the user gives another path.
7. Run `scripts/validate_report.py <report-path>` after writing. Fix missing sections, missing source notes, a missing weighting/aggregation caveat, a missing membership-snapshot/overlap caveat, missing window/date labels, or a missing disclaimer before presenting the result.

## Interface Map

Routing aid only; the exact call contract must still come from `pandadata`.

| Report section | Lead methods | What it answers |
|---|---|---|
| 概念全景 | `get_concept_list` | How many concepts; which are newly formed. |
| 动量排名 | `get_concept_constituents` + `get_stock_daily` | Which concepts lead by window momentum. |
| 广度对照 | `get_stock_daily` (per constituent) | Is the move broad (many up) or narrow (a few runners). |
| 轮动信号 | short vs long window momentum | Which themes are accelerating in / decelerating out. |
| 新概念雷达 | `get_concept_list` (`date`) | Recently formed concepts (little history — flag). |
| 概念成分 | `get_concept_constituents` | The constituent list behind a concept (snapshot-dated). |

## Analysis Modes

- **Whole-market leaderboard**: rank all (or the most-populated) concepts by short-window momentum, show breadth beside momentum, and highlight the short−long acceleration/deceleration to read rotation. State the membership snapshot date and weighting.
- **Single-concept drill**: one concept's constituents (as-of date), its momentum & breadth over windows, top contributing names, and whether it is newly formed.
- **Rotation read**: concepts with short ≫ long momentum are "轮入/升温"; short ≪ long are "轮出/降温". Present the spread; do not call tops/bottoms.
- **New-concept caution**: newly-formed concepts (recent `get_concept_list` date) have little history — report them separately and do not rank their momentum against seasoned concepts as if comparable.

## Report Rules

- Write in Chinese unless the user requests another language.
- **Always state the aggregation.** Concept momentum is bottom-up and depends on the weighting (等权 median vs mean) and window; name both. There is no official concept price index.
- **Always state the membership snapshot date.** Constituents change over time; computing a past return on today's membership is lookahead. Pass an explicit `date` to `get_concept_constituents` and label it.
- **Flag concept overlap.** A stock sits in many concepts, so concept returns are correlated and non-additive; a hot leader lifts every concept it is in. Do not present concept leaders as independent exposures.
- Separate facts (constituent returns, counts, inclusion dates), derived metrics (concept momentum, breadth, short−long spread, ranks), and judgment. Label all derived calculations.
- Treat empty API results as evidence. State "无数据" with the method name and queried window instead of silently omitting a section. If a constituent's daily data is missing, drop it from that concept's aggregate and state how many were dropped.
- Keep the tone factual and structural. Use "题材升温/降温", "广度偏窄由少数个股拉动", "轮入/轮出" rather than directional calls; never give trading instructions or personalized investment advice.

## Automation (optional scheduling)

When the user asks for an automated concept-rotation monitor, create a task that runs on trading days after market close (e.g. after `18:00 Asia/Shanghai`). Make it idempotent: if `reports/concept-rotation/<scope>-<date>.md` exists, regenerate and overwrite. Skip non-trading days.

## Resource Guide

- `references/concept-rotation-playbook.md`: routing table, bottom-up aggregation formulas, weighting/breadth definitions, membership-snapshot rule, report skeleton, empty-data handling, and the QA checklist.
- `scripts/validate_report.py`: checks the report for required sections, source notes, the aggregation/weighting caveat, the membership-snapshot/overlap caveat, window/date labels, and the disclaimer.

## Quality Bar

- Every material claim traces to `get_concept_list` / `get_concept_constituents` / `get_stock_daily`, a date, and the momentum window.
- Concept momentum always names its weighting (等权 median/mean) and window; there is no official concept index.
- Constituent membership is snapshot-dated (explicit `date`), avoiding lookahead.
- Concept overlap / non-additivity is stated; leaders are not presented as independent exposures.
- Newly-formed concepts are flagged and not ranked as comparable to seasoned ones.
- End every report with this disclaimer: `本报告基于公开数据与规则化分析生成，仅供研究参考，不构成任何投资建议。`
