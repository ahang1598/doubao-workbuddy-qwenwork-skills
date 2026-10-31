# facts.json 规格

事实表为摘要、正文、表格、图表和后续关注清单中的关键数字与判断提供可追溯来源。它不是研究数据库，只登记最终报告实际引用的事实。完整内容另写在结构化 report.json 中。

## 基本结构

~~~json
{
  "meta": {
    "company": "示例公司",
    "code": "000001.SZ",
    "market": "A股",
    "announcement_type": "业绩披露类",
    "today": "2026-10-30",
    "announcement_date": "2026-10-20"
  },
  "claims": [
    {
      "claim_id": "revenue_q3",
      "text": "2026Q3营业收入为120亿元。",
      "value": 120,
      "unit": "亿元",
      "period": "2026Q3",
      "source": "公司2026年三季报",
      "url": "https://example.com/announcement",
      "usage_type": "hard_fact"
    }
  ]
}
~~~

## meta

company、market、today 必填；code、announcement_type、announcement_date 应按实际任务填写，不知道的不能编造。market 使用 A股、港股、美股。today 和 announcement_date 使用 YYYY-MM-DD；公告日期不能晚于分析日期。

## claims

每条 claim 只表达一个事实或判断。

| 字段 | 要求 |
|---|---|
| claim_id | 稳定短 ID，英文字母开头，只含英文字母、数字、下划线、点和连字符 |
| text | 一句完整文字，写清数字、期间、口径和限制条件 |
| source | 来源名称及日期 |
| url | 有公开链接时填写；没有时可以省略，不能编链接 |
| usage_type | 见下表 |
| period | 有具体期间时填写，供正文口径核查 |
| value / unit | 该 claim 用于图表数据点时必填，必须与 report.json 中对应点值和单位一致 |
| calculation | usage_type 为 author_calculation 时必填，写出算式 |

| usage_type | 适用来源与正文语气 |
|---|---|
| hard_fact | 公告、定期报告、交易所、官方数据库中的可核查数字；可写“披露”“显示” |
| company_statement | 公司互动平台表态；显名标注互动平台 |
| management_guidance | 管理层展望；写“管理层表示” |
| broker_estimate | 券商估算；写“据券商估算” |
| broker_forecast | 券商预测、一致预期；写“机构预计” |
| market_view | 媒体、市场讨论；显名归因，不能作硬事实 |
| author_calculation | 基于公开数据的计算；必须有 calculation |
| author_inference | 作者推断；保留“可能”“待验证”等限制语 |

禁止把券商估算、媒体观点、投资者评论或作者推断登记为 hard_fact。投资者评论只能帮助发现需要核查的问题，不能作为事实来源。

## 与 report.json 的绑定

report.json 的 summary、paragraph、callout、list item、table cell 和 chart point 通过 fact_ids 数组引用 claim_id。文字和数字必须先完整写给读者，再绑定事实；不使用旧版的行内 fact 标记，也不手写 [1] 之类的来源编号。

~~~json
{"type":"paragraph","text":"2026年第三季度营业收入为120亿元。","fact_ids":["revenue_q3"]}
~~~

图表点值须至少绑定一条 value 和 unit 完全匹配的 claim。若图表单位为“亿元”，事实表也写“亿元”；确需从其他单位换算，应另外登记 author_calculation 和算式。

## 校验边界

check_facts.py 检查 JSON 结构、meta、claim_id、source、usage_type、计算公式和明显的来源分级错误。完整报告门禁进一步检查未知 fact_ids、未绑定关键数字、图表点值与 claim.value/unit 不一致、期间和语气口径等。错误阻断 HTML 生成；警告仍需逐条复核。
