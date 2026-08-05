# facts.json 规格

`facts.json` 的职责只有一个：给正文里的关键数字和关键判断提供可追溯来源。它不是研究数据库，也不是必须完整复刻三张财务报表。

默认使用轻量结构；只有在写完整季度报告、需要复算同比/环比/预期偏离时，才补充完整报告块。

---

## 默认结构

```json
{
  "meta": {
    "company": "示例公司",
    "code": "000000.SH",
    "quarter": "2026Q1",
    "today": "2026-06-21",
    "release_date": "2026-04-25"
  },
  "claims": [
    {
      "claim_id": "revenue_q1",
      "text": "公司2026Q1营业收入为28.4亿元，同比增长6.0%。",
      "source": "公司2026年一季度报告(2026-04-25)",
      "url": "https://example.com/report.pdf",
      "usage_type": "hard_fact"
    },
    {
      "claim_id": "market_share_estimate",
      "text": "有券商估算公司在该细分市场份额约40%-45%，公司未披露该口径。",
      "source": "XX证券研报(2026-04-28)",
      "url": "https://example.com/research",
      "usage_type": "broker_estimate"
    }
  ]
}
```

---

## 必填字段

### `meta`

`meta` 只记录任务边界：

| 字段 | 含义 |
|---|---|
| `company` | 公司名 |
| `code` | 股票代码；未知可留空，但不要编 |
| `quarter` | 报告期，如 `2026Q1`、`2025年` |
| `today` | 当前分析日期，格式 `YYYY-MM-DD` |
| `release_date` | 财报/公告发布日期，格式 `YYYY-MM-DD` |

`release_date` 早于 `today` 很久只会提示复核，不阻断。分析历史报告时不要为了过门禁改日期。

### `claims`

每条 claim 只表达一个正文会引用的事实或判断。

| 字段 | 含义 |
|---|---|
| `claim_id` | 正文 `{fact:claim_id}` 使用的稳定短 id；必须以英文字母开头，只能包含字母、数字、`_`、`.`、`-` |
| `text` | 事实内容，用一句完整中文写清楚数字、期间、口径和限制条件 |
| `source` | 来源名称和日期，如 `公司一季报(2026-04-25)` |
| `url` | 来源链接；确实没有公开链接时可省略 |
| `usage_type` | 正文使用方式，决定语气边界 |

如果是作者自行计算的数字，额外写 `calculation`：

```json
{
  "claim_id": "revenue_qoq_calc",
  "text": "按公司披露数据计算，2026Q1收入环比下降1.1%。",
  "source": "公司2026年一季度报告(2026-04-25)",
  "url": "https://example.com/report.pdf",
  "usage_type": "author_calculation",
  "calculation": "(176.17 / 178.13 - 1) * 100 = -1.1%"
}
```

---

## usage_type

`usage_type` 是 claims 里最重要的字段之一。它告诉正文应该用多强的语气。

| usage_type | 适用来源 | 正文写法 |
|---|---|---|
| `hard_fact` | 公司公告、定期报告、交易所披露、官方数据库 | 可写「公司披露」「为」「显示」 |
| `company_statement` | 公司新闻稿、管理层表述、说明会纪要 | 写「公司称」「管理层表示」 |
| `management_guidance` | 公司指引、管理层展望 | 写「公司预计」「管理层指引」 |
| `broker_estimate` | 券商估算、券商转引的行业测算 | 写「券商估算」「研报测算」「外部估算」 |
| `broker_forecast` | 券商预测、一致预期 | 写「机构预计」「一致预期」 |
| `market_view` | 媒体、市场讨论、社交平台线索 | 写「媒体报道」「市场讨论」，不能作为硬事实 |
| `author_calculation` | 基于公开数据的计算 | 写「按公开数据计算」；必须提供 `calculation` |
| `author_inference` | 由数据推出的解释性判断 | 写「可能指向」「更像是」，并给后续验证方式 |

禁止把 `broker_estimate`、`market_view`、`author_inference` 写成公司已经披露的确定事实。

---

## 正文绑定

正文、表格和后续关注项中的关键事实，在完整数字或判断后绑定 `{fact:claim_id}`：

```markdown
公司2026Q1营业收入为28.4亿元，同比增长6.0%。{fact:revenue_q1}
```

不要把 `{fact:...}` 当数值占位符：

```markdown
错误：营业收入为 {fact:revenue_q1}
正确：营业收入为28.4亿元。{fact:revenue_q1}
```

同一句话用多个事实支撑时：

```markdown
收入环比基本持平，但毛利率环比改善。{fact:revenue_qoq,gross_margin_qoq}
```

---

## 完整报告块

只有写完整季度点评、需要自动复算或需要判断「超/低于预期」时，才补充这些块：

| 块 | 何时填写 |
|---|---|
| `actual` | 需要复算本期收入、利润、毛利率、现金流等核心财务指标时 |
| `history` | 正文要写同比/环比，且希望脚本复算时 |
| `consensus` | 正文要写「超预期」「低于预期」时 |
| `guidance` | 正文要对比公司指引时 |
| `forecast` | 正文要转引具名机构预测时 |
| `shares` | 正文要复算 EPS 或市值相关指标时 |
| `price` | 正文需要引用行情事实时；本技能不做估值 |

这些块用于复算和交叉检查，不替代 `claims`。只要正文引用了关键数字或关键判断，就仍应有对应 claim。

---

## 校验边界

`check_facts.py` 只应阻断这些问题：

1. JSON 无法解析。
2. `claims` 不是数组。
3. `claim_id` 缺失、重复或格式错误。
4. claim 缺少 `source` 或 `usage_type`。
5. `hard_fact` 明显来自券商、媒体或市场讨论。
6. `author_calculation` 缺少 `calculation`。

其他问题只提示复核，不应阻断写作。
