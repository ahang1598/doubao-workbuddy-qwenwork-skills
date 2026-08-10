# facts.json 规格

`facts.json` 的职责只有一个：给正文里的关键数字和关键判断提供可追溯来源。它不是研究数据库，不需要穷举公告里的每一个数字，只登记正文/表格/后续关注清单里**实际引用**的那些。

---

## 结构

```json
{
  "meta": {
    "company": "恒尚节能",
    "code": "603137.SH",
    "market": "A股",
    "announcement_type": "监管问询类",
    "today": "2026-07-22",
    "announcement_date": "2026-07-13"
  },
  "claims": [
    {
      "claim_id": "np_2025",
      "text": "标的公司金胜电子2025年净利润4187万元，同比增长189.5%。",
      "source": "恒尚节能关于上海证券交易所问询函的回复公告（2026-07-13）",
      "url": "http://paper.cnstock.com/html/2026-07/14/content_2243747.htm",
      "usage_type": "hard_fact"
    },
    {
      "claim_id": "media_view_bubble",
      "text": "有市场评论认为本次问询函回复戳破了标的公司的半导体概念炒作泡沫。",
      "source": "财经媒体报道（2026-07-16）",
      "url": "https://example.com/media-report",
      "usage_type": "market_view"
    }
  ]
}
```

---

## 必填字段

### `meta`

只记录任务边界，不需要填满整套研究档案：

| 字段 | 含义 |
|---|---|
| `company` | 公司名 |
| `code` | 股票代码；未知可留空，但不要编 |
| `market` | 固定取值之一：`A股` / `港股` / `美股` |
| `announcement_type` | 对应 `references/markets-taxonomy.md` 或命中 playbook 的分类名，如"监管问询类""股权激励类" |
| `today` | 当前分析日期，格式 `YYYY-MM-DD` |
| `announcement_date` | 本次分析的公告发布/回复日期，格式 `YYYY-MM-DD` |

`announcement_date` 早于 `today` 很久只会提示复核，不阻断——分析历史公告时不要为了过门禁改日期。

### `claims`

每条 claim 只表达一个正文会引用的事实或判断。

| 字段 | 含义 |
|---|---|
| `claim_id` | 正文 `{fact:claim_id}` 使用的稳定短 id；必须以英文字母开头，只能包含字母、数字、`_`、`.`、`-` |
| `text` | 事实内容，用一句完整中文写清楚数字、期间、口径和限制条件 |
| `source` | 来源名称和日期，如「公司关于问询函的回复公告（2026-07-13）」 |
| `url` | 来源链接；确实没有公开链接时可省略 |
| `usage_type` | 正文使用方式，决定语气边界（见下表） |

如果是作者自行计算的数字，额外写 `calculation`：

```json
{
  "claim_id": "np_qoq_calc",
  "text": "按公司披露数据计算，标的公司净利润同比增长189.5%。",
  "source": "恒尚节能关于问询函的回复公告（2026-07-13）",
  "usage_type": "author_calculation",
  "calculation": "(4187 / 1446 - 1) * 100 = 189.5%"
}
```

---

## usage_type

`usage_type` 是 claims 里最重要的字段。它告诉正文应该用多强的语气，也是 `scripts/lint_report.py` 做语气核查的依据。

| usage_type | 适用来源 | 正文写法 |
|---|---|---|
| `hard_fact` | 公司公告、定期报告、交易所披露、官方数据库、互动平台回复中可核查的具体数字 | 可写「公司披露」「为」「显示」 |
| `company_statement` | 公司互动平台回复中的表述性内容（非硬数字） | 写「公司在互动平台回复称」 |
| `management_guidance` | 管理层展望、说明会表述 | 写「管理层表示」 |
| `broker_estimate` | 券商估算、券商转引的测算 | 写「券商估算」「研报测算」「外部估算」 |
| `broker_forecast` | 券商预测、一致预期 | 写「机构预计」「一致预期」 |
| `market_view` | 媒体、投资者评论区（同花顺/东方财富/雪球等）线索 | 写「媒体报道」「投资者评论区讨论」，不能作为硬事实 |
| `author_calculation` | 基于公开数据的计算 | 写「按公开数据计算」；必须提供 `calculation` |
| `author_inference` | 由数据推出的解释性判断 | 写「可能指向」「更像是」，并给后续验证方式 |

禁止把 `broker_estimate`、`market_view`、`author_inference` 写成公司已经披露的确定事实；`check_facts.py` 会阻断把 `hard_fact` 明显标给 broker/media/market 来源的情况。

---

## 正文绑定

正文、表格和后续关注项中的关键事实，在完整数字或判断后绑定 `{fact:claim_id}`：

```markdown
标的公司2025年净利润4187万元，同比增长189.5%。{fact:np_2025}
```

不要把 `{fact:...}` 当数值占位符：

```markdown
错误：净利润为 {fact:np_2025}
正确：净利润为4187万元。{fact:np_2025}
```

同一句话用多个事实支撑时：

```markdown
标的公司业绩增长但估值短期抬升，两点叠加放大市场对交易合理性的质疑。{fact:np_2025,valuation_gap}
```

---

## 校验边界

`check_facts.py` 只阻断这些问题：

1. JSON 无法解析。
2. `claims` 不是数组。
3. `claim_id` 缺失、重复或格式错误。
4. claim 缺少 `source` 或 `usage_type`。
5. `hard_fact` 明显来自 broker/media/market 来源。
6. `author_calculation` 缺少 `calculation`。
7. `meta` 缺少必填字段，或日期格式/先后关系有明显问题。

其他问题（url 缺失、期间口径提示等）只提示复核，不阻断写作。
