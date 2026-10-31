# 原生 HTML 报告数据结构

正式报告先整理事实与筛选结果，再写一个 UTF-8 `report.json`。`scripts/render_structured_report.py` 从该 JSON 输出原生 HTML；仅在用户明确要求时额外导出 Markdown。HTML 不经过 Markdown 转换。

## 顶层字段

| 字段 | 内容 |
|---|---|
| `schema_version` | 新报告固定为 `2`，启用板块、小节和重点公司的结构检查；旧数据未填写时按旧版兼容 |
| `title` | 报告标题，页面只显示一次 H1 |
| `subtitle` | 一句话说明研究问题和结论边界 |
| `as_of` | 数据截止时点及口径 |
| `scope` | 市场或股票池范围 |
| `summary` | 可选的结论卡片数组，每项包含 `label`、`value`、`detail` |
| `conclusion` | 必填的核心判断；位于摘要卡片之后、正文章节之前，说明入选与排除判断及关键依据，不重复卡片数字。按不同判断自然分段，在字符串中用空行分隔段落 |
| `sections` | 正文大板块数组，每项包含 `title`、必填的 `conclusion`、可选 `intro`、`blocks`；页面自动给大板块编号 |
| `sources` | 来源索引数组，每项包含唯一正整数 `id`、`title`，可加 `kind`、`date`、`usage`、`url` |

正文引用使用 `[1]`、`[2]`，HTML 会将其连接到来源索引。URL 仅在 `sources` 中填写。固定风险提示由渲染器追加，无需在 `sections` 重写。

## 正文排版层级

正文叙述区只用三级字号：大板块标题及编号 22px、小节标题 18px、结论/导语/解释/普通段落/列表 16px。结论可以加粗，但不另设字号；同一叙述区的文字统一使用正文深色，不用颜色区分标题、结论和导语。长分析只写在正文，不放进 `heading.text`。图表、指标卡、候选卡及其内部文字保留各自组件样式，不受这条正文规则约束。

## 内容组件

`blocks` 按阅读顺序组合以下类型：

- `paragraph`：`text`。一个判断或事实用一个段落。
- `heading`：`text`、`conclusion`。`text` 只写短标题（建议 4–18 个汉字），例如“筛选范围”“景气驱动”；渲染器在每个大板块内自动加“1）”“2）”等序号。标题后直接显示 `conclusion`，随后才是 `paragraph`、`metrics`、`list` 或图表。不要把整段分析、纳入与排除清单、数据缺口清单写成标题。超过 40 字的标题会由渲染器降为正文，以免出现整页大号粗体。
- `list`：`items`，可设 `ordered:true`。
- `metrics`：`items:[{"label":"...","value":"...","detail":"..."}]`。适合关键财务和筛选指标。`value` 尽量只放一个短数字及单位，指标名称放 `label`，对比和解释放 `detail`；不要把“内销+16.3%/出口+30.4%”之类的完整句子做成大号数值。
- `flow`：`title`、`steps`、可选 `note`。每个步骤有 `title`、`detail`、可选非负整数 `count` 和 `count_unit`。这是筛选规则流程卡片，不能写字符画。
- `table`：`columns`、`rows`，可选 `caption`、`note`。每行单元格数必须与表头相同。
- `chart`：`spec` 使用 `references/visualization-rules.md` 中的 `title`、`source`、`x`、`series` 图表结构，直接生成内联 SVG。
- `cards`：`items`。每项有 `title`、作为该卡片结论的 `summary`，可选 `subtitle`、`stats`，用于候选股或分组条目。
- `company`：`title`、一句 `thesis`、非空 `stats:[{"label":"...","value":"..."}]`，以及五部分 `parts`。五部分的键固定为 `role`、`earnings`、`valuation`、`peers`、`risk`；每部分都写 `conclusion` 和 `text`，先判断再给证据及解释。页面把二者连成同一段：小标题一层，结论与正文一层，避免再单独堆一层结论。研究内容仍须覆盖 `templates/key-company-card.md` 的必要维度。旧版 `analysis`、`points` 数据可渲染，新报告使用 `parts`。
- `timeline`：`items`，每项有 `date`、`title`、`detail`。
- `callout`：`title`、`text`、可选 `tone:"risk"`。

筛选流程中的 `count` 只放实际运行筛选所得的整数数量。若只有推测范围，写在 `detail` 中并标明“估计”，同时在 `note` 说明不是逐股扫描结果；不得用图形面积暗示精确漏斗人数。候选股及行情数据仍需保留可复核表格，卡片只是阅读入口。

将模板中的研究要求合并成读者易扫读的章节，不要逐条复制模板标题。页面先显示横向目录，再显示 `summary` 卡片和 `conclusion` 总判断，然后进入正文。正文大板块编号由渲染器生成，小标题在各大板块内从“1）”顺序编号；`report.json` 的标题文字不手写序号。每个大板块的 `conclusion` 紧跟大标题；有小标题时，每个 `heading.conclusion` 紧跟小标题，所属指标卡、图表和正文都放在结论之后。若大板块有 `intro` 且第一个 block 是小标题，渲染器会把 `intro` 放在第一个小节结论之后。图表不能单独承担结论。数据来源和固定免责声明列在文末，目录和标题的编号接续正文。同一筛选流程只展示一次；用 `flow` 解释筛选逻辑，用 `cards` 指引候选分组，用 `table` 保留完整核验数据。

重点公司五部分固定显示为“业务角色与主线相关性”“业绩情况”“估值与交易状态”“同行对比”“风险”，但每部分的文字应围绕该公司的具体证据与判断，不把研究字段逐条列成表单。示意结构：

```json
{"type":"company","title":"示例公司","thesis":"一句话概括定位、核心价值和主要风险。","stats":[{"label":"营收增速","value":"示例：12%"}],"parts":{"role":{"conclusion":"相关业务有直接证据。","text":"说明业务角色、收入关联及后续发展。"},"earnings":{"conclusion":"业绩受该业务拉动，但现金流仍需核验。","text":"说明营收、利润、毛利率和牵引程度。"},"valuation":{"conclusion":"当前估值需要结合阶段走势判断。","text":"说明估值、股价、成交和资金。"},"peers":{"conclusion":"与同环节公司相比有明确优势和劣势。","text":"给出可比数据和差异原因。"},"risk":{"conclusion":"核心不确定性是订单兑现。","text":"列出反向证据和验证指标。"}}}
```

## 最小示例

以下数值仅演示组件结构，不代表真实市场数据。

```json
{
  "schema_version": 2,
  "title": "低 PB 与资金流入筛选示例",
  "subtitle": "先说明条件，再展示候选与证据缺口",
  "as_of": "示例数据",
  "scope": "A 股",
  "summary": [
    {"label": "必要条件", "value": "PB ≤ 1.0", "detail": "仅作演示"},
    {"label": "资金确认", "value": "近 10 日多次流入", "detail": "以同一数据源核验"}
  ],
  "conclusion": "示例仅说明筛选方法：低 PB 不能单独构成入选理由，还需核验盈利质量和资金信号。\n\n数据未核实前不对候选作确定判断。",
  "sections": [
    {
      "title": "筛选逻辑",
      "conclusion": "低 PB 必须同时通过盈利质量与资金信号核验，否则只进入观察名单。",
      "intro": "低估值需要与盈利质量和资金信号一起判断。",
      "blocks": [
        {"type": "flow", "title": "筛选规则流程", "steps": [
          {"title": "界定股票池", "detail": "确定市场和交易状态"},
          {"title": "低 PB 条件", "detail": "在可比行业内检查 PB"},
          {"title": "资金信号确认", "detail": "核验多个交易日的资金数据"},
          {"title": "质量与风险过滤", "detail": "检查盈利、流动性和风险标记"}
        ], "note": "未执行逐股扫描时，不展示通过数量。"},
        {"type": "chart", "spec": {"title": "候选 PB 对比", "source": "示例数据", "x": ["公司 A", "公司 B"], "left_unit": "PB：倍", "series": [{"name": "PB", "type": "bar", "values": [0.6, 0.8]}]}},
        {"type": "table", "caption": "候选核验表", "columns": ["股票", "PB", "资金信号", "风险"], "rows": [["公司 A", "0.6", "待核验", "示例"]]}
      ]
    }
  ],
  "sources": [{"id": 1, "title": "示例数据", "kind": "演示", "date": "示例", "usage": "仅验证页面组件"}]
}
```

运行：

```bash
python3 scripts/render_structured_report.py report.json --output report.html
```

HTML 需要在浏览器中检查桌面与手机宽度。若出现 `<pre><code>` 字符画、重复 H1、未生成的图表说明或未绑定来源的关键数字，先修报告数据或组件，再交付。
同时检查标题是否只有短语、正文是否保持稳定字号、指标卡的数值是否简短，以及标签和注释在手机宽度下是否仍可阅读。
