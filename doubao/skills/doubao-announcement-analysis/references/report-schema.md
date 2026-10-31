# 结构化报告 report.json

report.json 是完整报告的唯一内容源。先完成 facts.json，再写 report.json；不创建完整 Markdown 源稿。正式 HTML 与对话摘要都由 finalize_report.py 从同一份 report.json 生成。

## 顶层字段

| 字段 | 要求 |
|---|---|
| mode | single（单条深度解读）或 batch（批量监控） |
| title | 中文报告标题 |
| summary | 2–5 条给对话框和 HTML 首页使用的重要结论；每条重要结论必须有 fact_ids |
| sections | 完整正文，按阅读顺序排列 |

单条深度解读必须有以下 section.key，各节必须有内容：

| key | 内容 |
|---|---|
| announcement | 公告基本信息与客观内容 |
| key_facts | 关键数字、条款与口径 |
| importance | 重要性及判断依据 |
| history | 历史同类公告对比，必须含 table |
| linked_signals | 关联公告、资讯、研报、互动回复与疑点 |
| price_reaction | 股价阶段表现检查；status 为 normal 或 abnormal，abnormal 时必须有带事件的价格图 |
| perspectives | 基本面、管理层、反方和风险点 |
| watchlist | 后续关注与验证条件 |

批量监控必须有 coverage、announcements、highlights、gaps 四个 section.key。批量模式仍须保留来源与风险提示；正文无需强行扩展成单条深度解读。

perspectives 章节至少有三个 block，分别设置 angle 为 fundamentals、management、counter_case。模板将它们排成“基本面与估值影响”“管理层与大股东视角”“反方与风险点”三个小节。没有证据支持某一角度时，应明确写出缺口，不臆造解释。

## 段落、表格与引用

每个 section 对象包含 key、title、blocks。block.type 可取 paragraph、callout、list、table、chart。

- paragraph / callout：text 和 fact_ids。
- list：items 数组，每项有 text 和 fact_ids。
- table：headers 文字数组、rows 二维数组；非数字标签可直接写文字，关键数字必须写成 {"text":"212.46亿元","fact_ids":["profit_q3"]} 形式。可加 caption 说明口径。
- 所有 fact_ids 都必须指向 facts.json 中的 claims[].claim_id。关键数字及重要判断应有事实绑定。不要在正文手写 [1]、脚注编号或内部占位符。
- 同一来源名称与 URL 在 HTML 中自动合并为一个引用编号；文末来源清单由模板生成。

对话摘要只使用 summary 数组，不从 HTML 全文截取，不把完整报告粘贴到对话框。

## 图表

chart block 必填 title、chart_type、unit、caption、market、x_labels、series。chart_type 为 line 或 bar；同一张图只能有一个单位，混合单位须拆图。x_labels 为 3–12 项，series 为 1–4 条。每个数据点有 value 和 fact_ids；至少一条所引事实必须在 facts.json 中写有完全匹配的数值 value 与单位 unit。价格图可另加 events，每个事件写 x_index（对应 x_labels 的零起始位置）、date（必须等于 x_labels[x_index]）、phase（发生/披露/可交易）、label、market、fact_ids。

跨市场图表需写 market_note；事件所属市场与曲线市场不同还需写 cross_market_note。phase 明确区分事件发生、公告披露与可交易时间；盘后披露可在 label 中进一步写明。HTML 模板用这些数据直接绘制响应式 SVG，不接受预制大 PNG 作为数值图表。

~~~json
{
  "type": "chart",
  "title": "报告前后股价与事件",
  "chart_type": "line",
  "unit": "元",
  "caption": "来源：交易所历史行情；收盘价口径",
  "market": "A股",
  "x_labels": ["2026-10-20", "2026-10-21", "2026-10-22"],
  "series": [
    {
      "name": "收盘价",
      "values": [
        {"value": 100, "fact_ids": ["price_1020"]},
        {"value": 92, "fact_ids": ["price_1021"]},
        {"value": 94, "fact_ids": ["price_1022"]}
      ]
    }
  ],
  "events": [
    {
      "x_index": 1,
      "date": "2026-10-21",
      "phase": "发生",
      "label": "公司实施回购",
      "market": "A股",
      "fact_ids": ["buyback_1021"]
    }
  ]
}
~~~

示意数值仅用于说明字段，不能用于真实报告。

## 最小结构示意

~~~json
{
  "mode": "single",
  "title": "示例公司季度公告解读",
  "summary": [
    {"text": "2026年第三季度收入增长，但利润承压。", "fact_ids": ["revenue_q3", "profit_q3"]},
    {"text": "后续关注毛利率与现金流变化。", "fact_ids": ["margin_q3", "cashflow_q3"]}
  ],
  "sections": [
    {
      "key": "announcement",
      "title": "公告基本信息",
      "blocks": [
        {"type": "paragraph", "text": "公司于2026年10月20日披露三季报。", "fact_ids": ["report_date"]}
      ]
    },
    {
      "key": "history",
      "title": "历史对比",
      "blocks": [
        {
          "type": "table",
          "headers": ["报告期", "收入"],
          "rows": [
            ["2026Q2", {"text": "100亿元", "fact_ids": ["revenue_q2"]}],
            ["2026Q3", {"text": "120亿元", "fact_ids": ["revenue_q3"]}]
          ],
          "caption": "来源：公司定期报告；单位：亿元"
        }
      ]
    },
    {
      "key": "price_reaction",
      "title": "股价阶段表现",
      "status": "normal",
      "blocks": [
        {"type": "paragraph", "text": "公告前后股价未见明显异动。", "fact_ids": ["price_reaction"]}
      ]
    }
  ]
}
~~~

上例只展示字段写法，不是完整单条报告；正式报告必须覆盖全部必需章节。标题、表格、图表、图注与免责声明都在 HTML 中排版，不需要模型手写 HTML。

## 门禁

finalize_report.py 依次检查事实表结构、必需章节、事实绑定、数据图点值与 fact.value/unit 一致性、市场和事件时间口径、原有的语气/无名锚/评级/预期锚/内部术语规则。错误会阻断 HTML 与摘要生成；警告须人工复核。固定免责声明由模板写入 HTML，避免遗漏或自行改写。
