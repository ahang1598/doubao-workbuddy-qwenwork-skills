---
name: smart-money-profiler
description: "Identify and profile the capital actors behind A-share trading from Pandadata interfaces, then track how they behave across time. Builds 龙虎榜 seat identity profiles (机构专用席位、知名游资营业部、量化席位、外资/陆股通通道), northbound cross-period behavior (加仓/减仓 streaks, 板块轮动, 集中度), and multi-source capital consensus vs divergence (北向 × 机构席位 × 融资盘 × 大宗买方). Use when the user asks for 聪明钱、资金主体画像、龙虎榜席位身份、游资追踪、机构席位胜率、北向跨期行为、资金合力分歧、谁在买卖, or a smart-money actor profile and cross-period behavior report. This skill is descriptive behavior tracking, not factor backtesting, not crowding-risk alerting, and not a single-day market snapshot."
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


```json qsh-form
{
  "version": 1,
  "task": {
    "placeholder": "请给出股票代码或资金主体名称（二选一）",
    "required": true
  },
  "fields": [
    {
      "key": "symbol",
      "label": "股票代码",
      "type": "text",
      "placeholder": "例如：600519.SH；按资金主体研究时可留空"
    },
    {
      "key": "actor",
      "label": "资金主体",
      "type": "text",
      "placeholder": "例如：机构专用、深股通专用或某营业部；按股票研究时可留空"
    },
    {
      "key": "mode",
      "label": "画像范围",
      "type": "select",
      "default": "full",
      "options": [
        { "value": "full", "label": "完整三支柱画像" },
        { "value": "seat", "label": "席位身份与画像" },
        { "value": "northbound", "label": "北向跨期行为" },
        { "value": "consensus", "label": "多源资金合力/分歧" }
      ]
    },
    {
      "key": "horizon",
      "label": "事后验证窗口",
      "type": "select",
      "default": "5,10,20",
      "options": [
        { "value": "5,10,20", "label": "5/10/20个交易日" },
        { "value": "5", "label": "5个交易日" },
        { "value": "10", "label": "10个交易日" },
        { "value": "20", "label": "20个交易日" }
      ]
    }
  ],
  "prompt_template": "{{#task}}任务与材料：\n{{task}}\n\n{{/task}}{{#attachments}}用户上传的材料（已放入工作区）：\n{{attachments}}\n\n{{/attachments}}对{{#symbol}}股票 {{symbol}}{{/symbol}}{{#actor}}资金主体 {{actor}}{{/actor}}开展 {{mode}} 画像，识别龙虎榜席位规则标签、北向跨期加减仓及北向/机构席位/融资盘/大宗买方的合力或分歧，并按 {{horizon}} 交易日窗口陈述事后表现；所有结论标明 Pandadata 方法、数据窗口与缺失状态，席位身份注明规则匹配而非官方认定，不输出因子、拥挤评级、单日大盘复盘或买卖指令，输出中文报告。"
}
```

# Smart Money Profiler

Use this skill to answer two questions the rest of the ecosystem does not: **谁在买卖（资金主体身份识别）**, and **他们一贯怎么做（跨期行为画像）**. It turns scattered 龙虎榜 seats, northbound holdings, margin balances, and block trades into named capital actors with persistent profiles and time-series behavior — every claim traced to a Pandadata method and data period.

This is **descriptive behavior tracking**, not prediction. Seat identity labels come from rule matching, not official designation. After-the-fact win-rate validation always states its window. The skill never emits buy/sell instructions.

## What this skill is NOT (anti-collision boundary)

Read this first. Three sibling skills cover adjacent ground; this skill must not duplicate them.

- **不产出可回测因子。** 不计算 IC / RankIC / ICIR、不做未来函数检查、不生成生产因子文件、不跑分组回测。若用户想把某个行为信号（如"高胜率席位买入"）做成可回测 Alpha 因子，移交 `skill-a1-lhb-tracking`。
- **不做过热/拥挤风险评级。** 不输出抱团、过热、踩踏、去杠杆风险等级，不做风险预警评分卡。若用户问"这笔交易是不是太拥挤了/要不要降风险"，移交 `agent-crowding-risk-monitor`。
- **不做单日全市场复盘。** 不产出"今日收盘快照"（指数涨跌、市场宽度、涨跌停家数、当日龙虎榜榜单复盘）。若用户要"今日复盘/收盘总结"，移交 `market-daily-review`。

**本 skill 的独有价值 = 资金主体身份识别（Seat Identity）+ 跨期行为画像（Cross-Period Profiling）+ 多源资金合力/分歧（Consensus vs Divergence）。** 关键词区分：本 skill 关心"是谁、一贯怎么做、几路资金是否同向"；不关心"做成因子、是否过热、今天大盘怎么样"。

## Core Workflow

1. Determine the subject and mode. The subject is either **a stock** (`XXXXXX.SH` / `XXXXXX.SZ`) or **a capital actor** (a seat/营业部 name, "机构专用", "深股通专用", or a known 游资 label). Normalize six-digit codes: `SH` for `600/601/603/605/688/689`, `SZ` for `000/001/002/003/300/301`; ask only when ambiguous.
2. Pick the pillar(s) the request needs: (1) Seat Identity & Profiling, (2) Northbound Cross-Period Behavior, (3) Capital Consensus vs Divergence. A full actor/stock profile uses all three; a focused question may use one.
3. Read `references/profiling-playbook.md` before the first profile in a session. It holds the seat-label dictionary and classification rules, profile schema, win-rate / holding-period formulas, consensus/divergence判定规则, report skeleton, empty-data handling, and the QA checklist.
4. Use `references/pandadata-interface-contracts.md` for registered methods and execute them directly through `call_pandadata`. Use `search_methods` only when no registered method covers the task, and use `get_method_doc` only after an explicit contract error; do not invent methods, parameters, fields, symbols, or credentials.
5. Resolve trading dates with `get_last_trade_date`, `get_trade_cal`, and `get_prev_trade_date` so windows (上榜后 5/10/20 个交易日) are counted in trading days, not calendar days.
6. Collect evidence first, then analyze. Keep raw returned rows or row counts long enough to cite source method, data date / window, and missing-data status. Sort multi-period tables by their date field (`date`, `end_date`) before windowing.
7. Maintain the persistent seat profile archive at `profiles/seats.json` (schema in the playbook). On each run, update or append seat records; treat it as an accumulating ledger, not a one-shot output.
8. Produce a Markdown profile report by default. If the user wants Word/PDF/HTML, generate the analytical content here first, then hand off to the relevant document skill.

## Three Pillars × Interface Map

Before any call, confirm exact parameters and fields via `pandadata`.

| Pillar | Primary methods | What it answers |
|---|---|---|
| 1️⃣ **席位身份与画像** | `get_lhb_list`, `get_lhb_detail`, `get_stock_daily` | 上榜买卖席位是谁？归为哪类主体（机构/游资/量化/外资通道）？该席位上榜频次、累计净买卖、上榜后 N 日胜率、平均持有/退出周期、偏好板块？ |
| 2️⃣ **北向跨期行为** | `get_hsgt_hold`, `get_index_daily`, `get_stock_daily` | 北向在该标的上是持续加仓还是减仓（streak）？持股比例/集中度怎么变？与指数走势是否背离？是持续性建仓还是短期博弈？ |
| 3️⃣ **资金合力 / 分歧** | `get_hsgt_hold`, `get_lhb_detail`, `get_margin`, `get_block_trade`, `get_stock_daily` | 同一标的上北向、机构席位、融资盘、大宗买方四路资金方向是否一致？是"合力同向"还是"互相对打分歧"？事后走势如何印证？ |

Supporting context (board attribution, mid/long-term institutional confirmation, date helpers):

| Use | Methods |
|---|---|
| 板块/行业/概念归属 | `get_stock_detail`, `get_stock_industry`, `get_concept_constituents` |
| 中长期机构股东印证 | `get_top_holders`, `get_holder_count` |
| 交易日历与窗口计数 | `get_trade_cal`, `get_last_trade_date`, `get_prev_trade_date` |

## Seat Identity Rules

- Seat identity labels are derived from **rule matching on the `agency` text returned by `get_lhb_detail`**, not from any official classification. Always state `标签来自规则匹配，不等于官方认定`.
- Standard buckets: `机构专用席位`、`陆股通/外资通道`（如"深股通专用""沪股通专用"）、`知名游资营业部`（依赖可维护的标签字典）、`量化/程序化席位`（依赖标签字典与行为特征，标注为推断）、`普通营业部/未分类`. The full rule set and editable dictionary live in `references/profiling-playbook.md`.
- When a seat cannot be confidently classified, label it `未分类` rather than forcing a guess. Do not present an inferred 游资/量化 label as established fact.
- `get_lhb_detail` `side` field: `buy` / `sell` / `cum`. The `cum` rows are severe-anomaly cumulative records unrelated to a specific direction — never net them against buy/sell.

## Analysis Rules

- Separate facts, derived metrics, and judgment. Label every derived quantity (净买卖额 = `b_value` − `s_value`, 上榜后 N 日收益, 胜率, 持有/退出周期, 集中度变化, streak 长度).
- After-the-fact win-rate validation must state the window in **trading days** (default 上榜后 5 / 10 / 20 个交易日) and the price basis from `get_stock_daily`. Win rate is descriptive of past episodes, never a forward signal.
- Northbound streaks are runs of consecutive same-direction change in `holding_ratio` / `shares_num`; report streak length, magnitude, and the divergence-with-index note separately.
- For consensus/divergence, align all four sources on the **same symbol and same window**, label each source's net direction, then classify per the playbook rules. State which sources had no data.
- Treat empty API results as evidence: write `无数据` with the method name and queried window instead of silently dropping a section.
- Use restrained wording — `可能提示`、`需要关注`、`与...同向/对打`. Never produce buy/sell calls or over-claim causality.
- End every report with: `本报告基于公开数据与规则化分析生成，仅供研究参考，不构成任何投资建议。`

## Persistent Archive & Automation

- The seat profile archive is `profiles/seats.json`. Each seat record accumulates 上榜频次, 累计净买卖, N-day 胜率样本, 平均持有/退出周期, 偏好板块/风格, plus `data_window` and `last_updated`. Schema and field definitions are in `references/profiling-playbook.md`.
- The archive is **append/update**, never overwrite-from-scratch: a new run merges fresh 龙虎榜 episodes into existing seat records and re-derives statistics from the accumulated sample.
- Support manual trigger ("给某席位/某股做资金主体画像") and scheduled refresh. For scheduled runs, prefer after-close on trading days (`get_trade_cal` to skip closures), and make the update idempotent for the same date so re-runs do not double-count episodes.

## Resource Guide

- `references/profiling-playbook.md`: seat-label dictionary & classification rules, profile-archive schema, win-rate / holding-period formulas, consensus-vs-divergence rules, report skeleton, empty-data handling, and QA checklist.
- `profiles/seats.json`: the persistent seat profile archive (created/updated at runtime).

## Quality Bar

- Every material claim traces to a Pandadata method, data date / window, and the `side`/direction it came from.
- Seat labels are tagged `规则匹配/推断`, not asserted as official fact.
- Win-rate and holding-period figures always carry their trading-day window and price basis.
- Consensus/divergence verdicts list every source and its direction, including `无数据` sources.
- No factor/backtest output, no crowding-risk grade, no single-day全市场 snapshot — those belong to the three sibling skills named above.
