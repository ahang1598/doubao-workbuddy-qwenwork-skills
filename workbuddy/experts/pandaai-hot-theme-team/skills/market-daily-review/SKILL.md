---
name: market-daily-review
description: "Generate A-share end-of-day market review reports with Pandadata data, covering trade-date checks, index performance and valuation, market breadth, limit-up/down sentiment, industries/concepts, 龙虎榜, block trades, margin financing, northbound holdings, risk notes, and optional scheduled after-close automation. Use when the user asks for 今日复盘, 收盘总结, 每日市场报告, A股复盘, 龙虎榜复盘, 北向资金动向, or to set up an automated daily market review."
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
    "placeholder": "补充复盘口径或特别要求（可选）",
    "required": false
  },
  "fields": [
    {
      "key": "date",
      "label": "复盘日期",
      "type": "date",
      "help": "留空时使用最近已完成的 A 股交易日"
    },
    {
      "key": "focus",
      "label": "重点关注",
      "type": "text",
      "placeholder": "例如：北向持仓、半导体板块、龙虎榜"
    }
  ],
  "prompt_template": "{{#task}}任务与材料：\n{{task}}\n\n{{/task}}{{#attachments}}用户上传的材料（已放入工作区）：\n{{attachments}}\n\n{{/attachments}}执行 A 股收盘复盘。{{#date}}以 {{date}} 为目标日期。{{/date}}未指定日期时以最近已完成的 A 股交易日为目标日期。{{#focus}}重点关注 {{focus}}。{{/focus}}先核验交易日，再覆盖指数表现与估值、市场宽度、涨跌停情绪、行业与概念、龙虎榜、大宗交易、两融、北向持仓和风险提示，逐项标注数据接口与日期并说明滞后或缺失数据，输出中文报告。"
}
```

# Market Daily Review

Use this skill to generate factual A-share after-close review reports. Prefer Pandadata as the data source, keep every statistic traceable to an interface and data date, and never invent missing figures.

## Workflow

1. Determine the target date. If the user does not provide one, use the latest completed A-share trading day. Check `get_last_trade_date` and `get_trade_cal`; if the target date is closed, return a short "今日休市" note instead of a full report.
2. Load `pandadata` before making real API calls. Use its method index or search script to confirm parameters and fields; do not guess Pandadata signatures.
3. Collect data in this order:
   - Trading calendar and stock universe: `get_last_trade_date`, `get_trade_cal`, `get_trade_list`.
   - Index performance and valuation: `get_index_daily`, `get_index_indicator`.
   - Market breadth and sentiment: `get_stock_daily` or `get_stock_rt_daily`, plus `get_stock_status_change`.
   - Hot sectors and concepts: `get_industry_constituents`, `get_concept_list`, `get_concept_constituents`.
   - Funds and notable trades: `get_lhb_list`, `get_lhb_detail`, `get_block_trade`, `get_margin`, `get_hsgt_hold`.
4. Compute breadth and ranking metrics from raw rows: rising/falling counts, limit-up/limit-down counts, turnover leaders, industry/concept leaders, 龙虎榜 top net buy/sell names, block-trade discount/premium distribution, margin balance change, and northbound holding changes.
5. Generate Markdown using `references/report-template.md`. Save the report to `reports/daily/YYYYMMDD.md` unless the user gives another path.
6. Run `scripts/validate_report.py <report-path>` after writing the report. Fix missing sections, missing source notes, or missing data-date labels before presenting the result.

## Pandadata Reference

Read `references/pandadata-map.md` when planning calls, selecting fields, or deciding how to degrade if a data interface is unavailable. The map is a routing aid only; the exact call contract must still come from `pandadata`.

## Report Rules

- Write in Chinese unless the user requests another language.
- Use absolute dates such as `2026-06-11`; avoid ambiguous "today" in the final report body.
- Mark T+1 datasets clearly. Margin financing, northbound holdings, and some exchange disclosures may lag the market date.
- State the limit-up/limit-down counting rules, including whether ST stocks and one-price boards are included.
- Keep the report factual: summarize structure, flows, and anomalies; do not give tomorrow's trading instructions or personalized investment advice.
- When a data call fails, keep the report useful by generating available sections and adding a concise missing-data note under "数据说明".

## Automation

When the user asks for an automated daily review, create an after-close task for trading days only, preferably after `18:30 Asia/Shanghai` so delayed datasets have time to settle. Make the task idempotent: if `reports/daily/YYYYMMDD.md` already exists, regenerate and overwrite it.
