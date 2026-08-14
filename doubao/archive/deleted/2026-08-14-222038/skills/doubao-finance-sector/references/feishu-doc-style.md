## 飞书文档版报告规范（板块热度分析）

## 输出目标

生成适合通过 `lark-doc` skill 写入飞书文档的结构化报告。报告内容、章节顺序、数据引用和合规口径与对话版分析及第二阶段中间产物保持一致；当前首选中间产物为 `doc.md`，`payload.json` 仅保留为 legacy fallback。

本规范的视觉目标参考摩根士丹利行研/业绩快报类 Word 报告：白底、深黑正文、橙色强调、细规则线分区、紧凑但可读的表格、较高信息密度。Claude financial-services 的 equity research 工作流将最终报告定位为 DOCX，并强调 institutional standards、可点击引用、专业表格和高密度报告；本 skill 采用其"机构报告意识"，但执行层面只使用 `lark-doc` 明确支持的属性。

`lark-doc` 可设置标题、段落、列表、表格、引用块、分割线、超链接、`span` 文字色/背景色、`callout`、表格列宽和单元格背景色；在多数环境下不能稳定设置字体、字号、行高、段间距、页边距、纸张大小、页眉页脚或自定义 hex 色。因此本版本只使用飞书稳定支持的原生元素，并把无法直接设置的细节转换为标题层级和结构规则：

- 文档标题：`<title align="left">`。
- 标题层级：`<h1>`、`<h3>`。
- 普通段落：`<p>`。
- 编号列表：`<ol>`、`<li>`。
- 表格：`<table>`、`<colgroup>`、`<col>`、`<thead>`、`<tbody>`、`<tr>`、`<th>`、`<td>`。
- 引用和提示：`<blockquote>`、`<callout>`。
- 分割线：`<hr/>`。
- 加粗、链接和行内颜色：`<b>`、`<a>`、`<span text-color>`、`<span background-color>`。
- 来源编号，如 `[1]`、`[2]`。

禁止：

- 不输出 `<!DOCTYPE html>`、`<style>`、`<script>`、HTML class、CSS style、inline style。
- 不输出 CSS、外部字体、图片、SVG、图表库、K 线图、价格轴、网页卡片；允许使用飞书原生 `<column-group>` 做文档内分栏。
- 不依赖红绿颜色表达涨跌；必须在文字中写清"上涨/下跌"方向。
- 不使用营销式标题、长横线分割、复杂嵌套列表。
- 不输出 Markdown 语法（`**`、`#`、`- `、`` ` ``、`>` 等），所有内容必须为 lark-doc XML 标签。

## lark-doc 可执行样式基准

用户确认生成飞书文档后，必须调用 `lark-doc` 写入飞书文档。不要把完整报告正文直接丢在对话框里，除非 `lark-doc` 不可用且用户明确同意先看草稿。

### 写入方式

飞书文档版必须先组装为一段完整的 lark-doc XML 内容，再通过 `lark-doc` 写入：

- 新建文档或用户明确允许重写目标文档时，优先使用全文写入/覆盖类操作，把完整 XML 作为 `content` 传入。
- 已有文档如含评论、图片、附件或用户手工编辑内容，使用覆盖写入前必须确认；否则先读取文档结构，再使用块级替换/追加方式更新。
- 写入内容必须是 lark-doc XML 片段，不包 `<!DOCTYPE html>`、`<html>`、`<head>`、`<body>`，不带 CSS、style、script 或 class。
- 动态文本写入 XML 前必须转义：`&` -> `&amp;`，`<` -> `&lt;`，`>` -> `&gt;`，普通换行 -> `<br/>`。
- 行内样式嵌套顺序必须遵守：`<a>` -> `<b>` -> `<em>` -> `<del>` -> `<u>` -> `<code>` -> `<span>` -> 文本。

默认传输策略：

1. 用户没有给目标文档：询问是否新建飞书文档，并在新文档中写入完整 XML。
2. 用户给了目标文档且明确说"覆盖/重写"：使用完整 XML 覆盖写入。
3. 用户给了目标文档但没有说可覆盖：先读取文档，确认后再覆盖；若用户只要追加，则追加到文末。

### 可设置与不可设置

- 可以设置：标题层级、段落/列表、对齐、引用块、分割线、callout 背景/边框/文字色、表格列宽、单元格背景色、超链接、行内文字颜色和背景色。
- 不能稳定设置：字体、字号、行高、字间距、段间距、页边距、纸张大小、页眉页脚、表格边框粗细；自定义 hex 色仅在目标 `lark-doc` 环境明确支持时使用。
- 橙色强调是本模板的固定视觉目标。飞书文档优先使用命名色 `text-color="orange"` 与 `border-color="orange"`；自定义 HEX 色不作为默认要求。
- 主标题、章节标题、二级小标题和关键数字统一使用橙色强调；不要改成蓝色目标色。
- 命名色 fallback 只能使用 `red`、`orange`、`yellow`、`green`、`blue`、`purple`、`gray`、`white` 及 `light-*`、`medium-*` 系列中的可用色。
- 投行报告风格在飞书中的近似实现：主标题、章节标题和关键数字用 `text-color="orange"`；避免大面积浅橙底；辅助信息和表格底色用 `gray` / `light-gray`，用 `<hr/>` 做章节区隔，用紧凑表格和列宽控制信息密度。

### 标题与分区

一级章节必须用 `hr + h1` 形成投行报告式分区：

```xml
<hr/>
<h1 align="left"><span text-color="orange">综合热度仪表盘</span></h1>
```

要求：

- 每个一级章节前使用一个 `<hr/>`，不得连续使用多个分割线。
- 一级章节使用 `<h1 align="left"><span text-color="orange">...</span></h1>`。
- 二级小标题使用 `<h3 align="left"><span text-color="orange">...</span></h3>`，不得使用 `<h2>`。
- 字号视觉目标固定为：报告标题约 18 pt；一级章节约 14 pt；二级小标题约 12 pt；正文约 10.5 pt。飞书无法直接设字号时，用 `title / h1 / h3 / p` 的层级逼近该比例。
- 普通段落使用 `<p align="left">`；每段 80-160 个汉字，避免导出 PDF 后形成大块文字墙。
- 重点词可用 `<b>`，不要整段加粗。
- 编号列表使用 `<ol>`，每个 `<li>` 必须写 `seq="auto"`，保证飞书自动编号稳定。

### 表格样式

所有表格采用 `lark-doc` 可落地的"投行模型表"近似样式：

- 使用 `<colgroup>` 明确列宽，避免 PDF 导出后错列或宽表撑开。
- 表头 `<th background-color="light-gray">`，表头文字用 `<p align="center"><b><span text-color="orange">...</span></b></p>`；所有表头必须居中。不要使用浅橙表头，以免整体显得偏轻。
- 第一列行标签使用 `<td background-color="light-gray" vertical-align="middle">`，所有表格文字统一居中。
- 所有表格正文统一使用 `<p align="center">...</p>` 居中。
- 所有单元格统一使用 `vertical-align="middle"` + `<p align="center">...</p>`。
- 数字列所在单元格内容尽量短，并在文本中保留正负号、单位和来源编号。
- 价格、比例、金额等数值数据单元格统一使用 `<p align="center"><b>...</b></p>` 加粗；纯文本解释列不加粗。
- 表格不超过 6 列；超过 6 列时拆表或改为纵向指标表。
- 不使用 `rowspan` 和 `colspan` 做复杂表头，除非用户明确要求；日报模板保持单层表头，减少飞书导出 PDF 错位。

## 触发规则

默认仍先输出对话版完整分析。只有用户明确表示"生成飞书文档 / 生成飞书文档版 / 做成飞书文档 / 继续生成"时，才进入飞书文档生成流程。

如果 `doc.md` 尚未生成，先按 SKILL.md 飞书文档流程生成并校验 `doc.md`，再进入飞书文档生成。仅当新链路失败时，才回退到 legacy payload 路径。

## 文档结构

飞书文档版必须按以下固定顺序写入 `lark-doc` 内容。所有文本内容以第一阶段对话正文为唯一母版，原句搬运，不做压缩、改写或同义替换。10 股行情、近7日复算、四组分组数据来自 `doc.md`（由 facts 直接生成并完成水合）；legacy payload 仅用于回退。

```
<title>板块热度分析 · {sector}</title>
<p>元数据行</p>
<callout>合规提示</callout>

<hr/><h1>综合热度仪表盘</h1>
... 文字仪表盘 + headline + summary + 4 核心指标 callout 高亮块 + 10股列表 ...

<hr/><h1>双轨热度 · 信息 vs 行情</h1>
... 双轨总括 pill + 双轨热度表格 + 判断 ...

<hr/><h1>📌 直接回答</h1>
... callout 三行结论 ...

<hr/><h1>① 现在有多热</h1>
... 本段结论 + 四维度高亮块 ...

<hr/><h1>② 为什么涨 / 跌</h1>
... 本段结论 + 催化时间线条目 ...

<hr/><h1>③ 谁在动、谁没动</h1>
... 本段结论 + 10股行情表格 + 四组行为分类 ...

<hr/><h1>④ 接下来盯什么</h1>
... 本段结论 + 盯盘信号列表 ...

<hr/><h1>⑤ 风险提示</h1>
... 本段结论 + 编号风险列表 ...

<hr/><h1>⑥ 信息来源</h1>
... 编号来源列表 ...

<hr/><h1>免责声明</h1>
... 三段灰色免责声明 ...
```

## 顶部版式

文档标题固定为旧版风格：

```xml
<title>{sector}板块热度分析：{headline}</title>
```

标题下方用一行灰色元信息承接市场、目标概念板块和完整数据时点：

```xml
<p align="left"><span text-color="gray">市场：{market} | 目标概念板块：{index_caliber} | 数据时点：{timestamp}</span></p>
```

字段来自 `doc.md` 的 `sector` / `headline` / `market` / `index_caliber` / `timestamp`；标题中需要带上核心结论句。

元信息下方固定放置合规提示 callout：

```xml
<callout emoji="⚠️" background-color="light-yellow" border-color="yellow">
<p>本文仅用于信息参考与研究辅助，不构成任何投资建议。股市有风险，请结合自身风险承受能力决策。</p>
</callout>
```

要求：

- 顶部不用大段免责声明，避免首屏松散。
- 元信息一行优先；过长时拆成两行 `<p>`，不要放进表格。
- 顶部 `callout` 只用于合规提示，不堆积观点；采用旧版固定样式 `⚠️ + light-yellow/yellow`。

## 综合热度仪表盘

对应 `doc.md` 字段：`composite_score`、`gauge_pill`、`headline`、`summary`、`key_chips`、`selected_stocks`。

### 文字仪表盘

综合热度分数采用旧版简洁表达，不输出刻度行：

```xml
<hr/>
<h1 align="left"><span text-color="orange">综合热度仪表盘</span></h1>
<p align="left"><b>综合热度：{score}/5（{gauge_pill}）</b></p>
```

- `gauge_pill` 为 `doc.md` 中的简短定性标签，使用括号包裹，整体与分数放在同一加粗行内。

### headline 与 summary

```xml
<p align="left"><b>{headline}</b></p>
<p align="left"><b>{summary}</b></p>
```

- `headline` 为开篇核心结论的标题句，加粗展示。
- `summary` 为 headline 下方的摘要段落，加粗展示。

### 4 核心指标高亮块

将 4 个核心指标展示为两栏布局——页面分栏为 2 列，每列纵向放置 2 个高亮块（callout），共 4 个高亮块。不使用表格，使用 `grid`：

```xml
<grid>
<column width-ratio="0.5">
<callout emoji="📊" background-color="light-gray" border-color="gray">
<p><span text-color="gray">{label_0}</span></p>
<p><b>{value_0}{unit_0}</b></p>
</callout>
<callout emoji="📊" background-color="light-gray" border-color="gray">
<p><span text-color="gray">{label_2}</span></p>
<p><b>{value_2}{unit_2}</b></p>
</callout>
</column>
<column width-ratio="0.5">
<callout emoji="📊" background-color="light-gray" border-color="gray">
<p><span text-color="gray">{label_1}</span></p>
<p><b>{value_1}{unit_1}</b></p>
</callout>
<callout emoji="📊" background-color="light-gray" border-color="gray">
<p><span text-color="gray">{label_3}</span></p>
<p><b>{value_3}{unit_3}</b></p>
</callout>
</column>
</grid>
```

要求：

- `key_chips` 必须恰好 4 个，缺一则报错不生成。
- 两栏布局：左栏={label_0, label_2}，右栏={label_1, label_3}。
- 每个高亮块内：标签在上（灰色小字），数值在下（黑色加粗大字），左对齐。
- 涨跌幅类 chip（`color` 字段为 `"up"` 或 `"down"`）在数值前写"上涨"或"下跌"，例如 `<b>上涨 +2.35%</b>` 或 `<b>下跌 -1.20%</b>`。不依赖颜色表达方向。
- 数值和单位写在同一 `<b>` 标签内，不加空格分隔（如 `<b>85亿</b>`）。
- 不使用 `<table>` 标签；两列容器固定使用 `<grid>` 与 `<column width-ratio="0.5">`。

### 10 只代表股列表

```xml
<p align="left"><span text-color="gray">本次选取的 10 只代表股：{股票1}、{股票2}、...、{股票10}</span></p>
```

- 股票名来自 `doc.md` 的 `selected_stocks` 数组。
- 灰色小字，放在核心指标高亮块下方。

## 双轨热度 · 信息 vs 行情

对应 `doc.md` 字段：`info_score`、`market_score`、`divergence`。

### 双轨总括 pill

根据信息轨与行情轨的高低组合，输出总括判断：

```xml
<hr/>
<h1 align="left"><span text-color="orange">双轨热度 · 信息 vs 行情</span></h1>
<p align="left"><b>双轨偏热</b>：信息与行情共振，市场关注度高且资金参与积极</p>
```

四种情况对应的总括文本：

| 条件 | 标签 | 说明 |
|------|------|------|
| info ≥ 3 且 market ≥ 3 | 双轨偏热 | 信息与行情共振，市场关注度高且资金参与积极 |
| info ≥ 3 且 market < 3 | 信息领先 | 政策/消息面热度领先于价格表现，预期走在行情前面 |
| info < 3 且 market ≥ 3 | 行情领先 | 价格/成交热度领先于信息面，可能存在纯资金驱动 |
| info < 3 且 market < 3 | 双轨偏冷 | 信息面与行情面均低迷，板块处于低关注状态 |

### 双轨热度表格

```xml
<table>
<colgroup><col width="100"/><col width="80"/><col width="220"/><col width="400"/></colgroup>
<thead><tr>
<th background-color="light-gray"><p align="center"><b><span text-color="orange">轨道</span></b></p></th>
<th background-color="light-gray"><p align="center"><b><span text-color="orange">分数</span></b></p></th>
<th background-color="light-gray"><p align="center"><b><span text-color="orange">热度</span></b></p></th>
<th background-color="light-gray"><p align="center"><b><span text-color="orange">意味着</span></b></p></th>
</tr></thead>
<tbody>
<tr>
<td background-color="light-gray" vertical-align="middle"><p align="center">信息轨</p></td>
<td vertical-align="middle"><p align="center"><b>{info_score}/5</b></p></td>
<td vertical-align="middle"><p align="center">{进度条文字}</p></td>
<td vertical-align="middle"><p align="center">消息 / 催化 / 公开讨论的密度与强度</p></td>
</tr>
<tr>
<td background-color="light-gray" vertical-align="middle"><p align="center">行情轨</p></td>
<td vertical-align="middle"><p align="center"><b>{market_score}/5</b></p></td>
<td vertical-align="middle"><p align="center">{进度条文字}</p></td>
<td vertical-align="middle"><p align="center">价格 / 成交 / 代表股 / 估值的强度</p></td>
</tr>
</tbody>
</table>
```

- 第一列（轨道名）灰底居中。
- 热度列由 10 个可见方块组成：若干彩色方块（填充）+ 若干极浅灰方块（未填充），总数必须固定为 10。每个分数点对应 2 个方块（10 方块 / 5 分 = 2 方块/分）。
  - 信息轨：蓝色填充（`<span text-color="blue">█</span>`）+ 极浅灰占位（`<span text-color="light-gray">█</span>`）
  - 行情轨：红色填充（`<span text-color="red">█</span>`）+ 极浅灰占位（`<span text-color="light-gray">█</span>`）
  - 信息轨示例（4/5 = 8 蓝色 + 2 极浅灰）：`<span text-color="blue">████████</span><span text-color="light-gray">██</span>`
  - 行情轨示例（3/5 = 6 红色 + 4 极浅灰）：`<span text-color="red">██████</span><span text-color="light-gray">████</span>`
  - 禁止用空格、透明字符或省略未填充部分来占位；不满 5 分的部分必须用极浅灰方块补齐。
- 列宽固定为 `100 / 80 / 220 / 400`。

### 判断

```xml
<p align="left"><b>判断：</b>{divergence.verdict}</p>
<p align="left">{divergence.meaning}</p>
```

- `verdict` 加粗标签后接正文。
- `meaning` 为普通段落，详细解读双轨背离或共振的含义。

## 📌 直接回答

对应 `doc.md` 字段：`answer.restate`、`answer.conclusion`、`answer.next`。

使用 callout 包裹三行结论，形成视觉区隔：

```xml
<hr/>
<h1 align="left"><span text-color="orange">📌 直接回答</span></h1>
<callout emoji="💡" background-color="light-gray" border-color="orange" text-color="gray">
<p><b>问题：</b>{answer.restate}</p>
<p><b>结论：</b>{answer.conclusion}</p>
<p><b>下一步：</b>{answer.next}</p>
</callout>
```

- emoji 固定用 `💡`。
- 三行分别以粗体标签开头，正文紧随其后。

## ① 现在有多热

对应 `doc.md` 字段：`section_summaries.heat`、`dimensions`。

### 本段结论

```xml
<hr/>
<h1 align="left"><span text-color="orange">① 现在有多热</span></h1>
<p align="left"><b>本段结论：</b>{section_summaries.heat}</p>
```

### 四维度高亮块

将 4 个维度展示为上下两组独立两栏分栏：第一组分栏横向放置第 1、2 个高亮块，第二组分栏横向放置第 3、4 个高亮块，共 4 个高亮块。不使用表格，使用 `grid`：

```xml
<grid>
<column width-ratio="0.5">
<callout emoji="🔴" background-color="light-gray" border-color="gray">
<p><b>{name_1}  ·  {state_1}</b></p>
<p><b>关键数据：</b>{value_1}</p>
<p>{read_1}</p>
</callout>
</column>
<column width-ratio="0.5">
<callout emoji="🔴" background-color="light-gray" border-color="gray">
<p><b>{name_2}  ·  {state_2}</b></p>
<p><b>关键数据：</b>{value_2}</p>
<p>{read_2}</p>
</callout>
</column>
</grid>
<grid>
<column width-ratio="0.5">
<callout emoji="🔴" background-color="light-gray" border-color="gray">
<p><b>{name_3}  ·  {state_3}</b></p>
<p><b>关键数据：</b>{value_3}</p>
<p>{read_3}</p>
</callout>
</column>
<column width-ratio="0.5">
<callout emoji="🔴" background-color="light-gray" border-color="gray">
<p><b>{name_4}  ·  {state_4}</b></p>
<p><b>关键数据：</b>{value_4}</p>
<p>{read_4}</p>
</callout>
</column>
</grid>
```

要求：

- `dimensions` 必须恰好 4 个，每个含 `name`、`state`、`value`、`read` 四个字段。
- 四维度固定为：价格涨跌、成交量能、代表股表现、估值位置。
- 两组分栏布局：第一组={name_1, name_2}，第二组={name_3, name_4}；同一组内两个高亮块横向排列，顶部对齐，字段结构保持一致，解释文字尽量控制为相近长度以利于底部齐平。
- 每个高亮块内：第一行为维度名（加粗）+ 状态，第二行为关键数据，第三行为解读。
- 状态值直接写中文（"确认""弱确认""背离"），不依赖 emoji。
- 不使用 `<table>` 标签；两列容器固定使用 `<grid>` 与 `<column width-ratio="0.5">`。

## ② 为什么涨 / 跌

对应 `doc.md` 字段：`section_summaries.catalysts`、`catalysts`。

### 本段结论

```xml
<hr/>
<h1 align="left"><span text-color="orange">② 为什么涨 / 跌</span></h1>
<p align="left"><b>本段结论：</b>{section_summaries.catalysts}</p>
```

### 催化时间线条目

`catalysts` 精选 3-5 条，最多 6 条，按日期倒序排列。每条使用以下固定结构：

```xml
<h3 align="left"><span text-color="orange">{tone_label} · {date} · {category}</span></h3>
<p align="left"><b>{title}</b></p>
<p align="left"><span text-color="gray">信息来源：{source_name}</span></p>
<p align="left">{fact}</p>
<blockquote>
<p><b>为什么重要：</b>{why}</p>
<p><b>后续验证：</b>{verify}</p>
</blockquote>
```

要求：

- `tone_label` 直接写"利好""利空"或"中性"，不依赖 emoji 颜色。
- `date` 为日期文本（如"6月23日"）。
- `category` 为催化类别短标签。
- 如有外部原文链接（`url` 字段非空），在标题后追加 `<a href="{url}">查看原文 ↗</a>`。
- 每条催化之间空一行分隔。
- 每条的 `fact`、`why`、`verify` 字段均来自第一阶段正文原句搬运。
- `why` 和 `verify` 放在 `<blockquote>` 中形成视觉缩进。

## ③ 谁在动、谁没动

对应 `doc.md` 字段：`section_summaries.divergence`、`stocks`、`divergence_groups`。

### 本段结论

```xml
<hr/>
<h1 align="left"><span text-color="orange">③ 谁在动、谁没动</span></h1>
<p align="left"><b>本段结论：</b>{section_summaries.divergence}</p>
```

### 10 只代表股行情表格

固定 6 列表格，按当日涨跌幅降序排列：

```xml
<h3 align="left"><span text-color="orange">10 只代表股行情</span></h3>
<table>
<colgroup><col width="120"/><col width="100"/><col width="130"/><col width="130"/><col width="150"/><col width="170"/></colgroup>
<thead><tr>
<th background-color="light-gray"><p align="center"><b><span text-color="orange">股票</span></b></p></th>
<th background-color="light-gray"><p align="center"><b><span text-color="orange">角色</span></b></p></th>
<th background-color="light-gray"><p align="center"><b><span text-color="orange">当日涨跌</span></b></p></th>
<th background-color="light-gray"><p align="center"><b><span text-color="orange">当日成交(亿)</span></b></p></th>
<th background-color="light-gray"><p align="center"><b><span text-color="orange">近7日涨跌</span></b></p></th>
<th background-color="light-gray"><p align="center"><b><span text-color="orange">近7日均成交(亿)</span></b></p></th>
</tr></thead>
<tbody>
<tr>
<td background-color="light-gray" vertical-align="middle"><p align="center">{name}</p></td>
<td vertical-align="middle"><p align="center">{role}</p></td>
<td vertical-align="middle"><p align="center"><b><span text-color="red">上涨 +X.XX%</span></b></p></td>
<td vertical-align="middle"><p align="center"><b>{turnover}</b></p></td>
<td vertical-align="middle"><p align="center"><b><span text-color="green">下跌 -X.XX%</span></b></p></td>
<td vertical-align="middle"><p align="center"><b>{turnover_7d}</b></p></td>
</tr>
<!-- 共 10 行，按当日涨跌幅降序 -->
</tbody>
</table>
```

要求：

- `stocks` 必须恰好 10 只，按 `change`（当日涨跌幅）降序排列。
- 涨跌幅必须写清方向："上涨 +X.XX%"或"下跌 -X.XX%"，零值写"0.00%"。上涨用红色（`<span text-color="red">`），下跌用绿色（`<span text-color="green">`），零值不着色。
- 股票名（第一列）灰底居中。
- 数值列（当日涨跌、当日成交、近7日涨跌、近7日均成交）加粗居中。
- 成交额保留两位小数。
- 列宽固定为 `120 / 100 / 130 / 130 / 150 / 170`。

### 四组行为分类

`divergence_groups` 四组顺序固定，使用上下两组独立两栏分栏：第一组分栏横向放置放量上攻组、缩量上行组，第二组分栏横向放置缩量回调组、放量杀跌组，共 4 个高亮块。不使用表格，使用 `grid`：

```xml
<h3 align="left"><span text-color="orange">四组行为分类</span></h3>

<grid>
<column width-ratio="0.5">
<callout emoji="🟢" background-color="light-gray" border-color="gray">
<p><b>放量上攻组</b> — 量价齐升 · 参与充分</p>
<p><code>股票1</code> <code>股票2</code> <code>股票3</code></p>
<p>{feature_1}</p>
</callout>
</column>
<column width-ratio="0.5">
<callout emoji="🟢" background-color="light-gray" border-color="gray">
<p><b>缩量上行组</b> — 量能不足 · 持续性存疑</p>
<p>（无）</p>
<p>{feature_2}</p>
</callout>
</column>
</grid>
<grid>
<column width-ratio="0.5">
<callout emoji="🟢" background-color="light-gray" border-color="gray">
<p><b>缩量回调组</b> — 抛压衰竭 · 多近企稳</p>
<p><code>股票1</code> <code>股票2</code></p>
<p>{feature_3}</p>
</callout>
</column>
<column width-ratio="0.5">
<callout emoji="🟢" background-color="light-gray" border-color="gray">
<p><b>放量杀跌组</b> — 抛压沉重 · 资金出逃</p>
<p><code>股票1</code></p>
<p>{feature_4}</p>
</callout>
</column>
</grid>
```

要求：

- 四组顺序固定，不可调换。两组分栏布局：第一组=放量上攻、缩量上行；第二组=缩量回调、放量杀跌；同一组内两个高亮块横向排列，顶部对齐，字段结构保持一致，解释文字尽量控制为相近长度以利于底部齐平。
- 每个高亮块内：第一行为组名（加粗）+ 副标题，第二行为股票列表，第三行为 feature 解释文字。
- 每只股票使用 `<code>` 标签包裹，同一组内多个 `<code>` 之间用空格分隔。
- 空组股票行写"（无）"，不写空字符串。
- 每组的 `feature` 文本来自第一阶段正文原句搬运。
- 不使用 `<table>` 标签；两列容器固定使用 `<grid>` 与 `<column width-ratio="0.5">`。

## ④ 接下来盯什么

对应 `doc.md` 字段：`section_summaries.watch`、`watch_signals`。

### 本段结论与信号列表

```xml
<hr/>
<h1 align="left"><span text-color="orange">④ 接下来盯什么</span></h1>
<p align="left"><b>本段结论：</b>{section_summaries.watch}</p>

<callout emoji="🔵" background-color="light-gray" border-color="gray">
<p><b>信号 1 · {tag_1}：</b>{signal_1}</p>
<p><b>盯：</b>{watch_1}</p>
<p><b>改善：</b>{improve_1}</p>
<p><b>恶化：</b>{worsen_1}</p>
</callout>

<callout emoji="🔵" background-color="light-gray" border-color="gray">
<p><b>信号 2 · {tag_2}：</b>{signal_2}</p>
<p><b>盯：</b>{watch_2}</p>
<p><b>改善：</b>{improve_2}</p>
<p><b>恶化：</b>{worsen_2}</p>
</callout>

<!-- 共 N 条信号，至少 3 条，每条一个独立 callout -->
```

要求：

- `watch_signals` 至少 3 条，N 从 1 开始编号。
- 当 `tag` 为空时省略"· {tag}"部分。
- 每条信号使用一个独立 `<callout>`：第一行为信号描述（`signal`），后三行为盯/改善/恶化，保持 4 行结构。
- 信号之间自然分隔，无需额外空行。

## ⑤ 风险提示

对应 `doc.md` 字段：`section_summaries.risks`、`risks`。

### 本段结论与风险列表

```xml
<hr/>
<h1 align="left"><span text-color="orange">⑤ 风险提示</span></h1>
<p align="left"><b>本段结论：</b>{section_summaries.risks}</p>

<callout emoji="⚠️" border-color="red">
<p><b>{风险标题_1}</b></p>
<p><b>触发：</b>{trigger_1}</p>
<p>{why_1}</p>
<p><b>证伪：</b>{invalidate_1}</p>
</callout>

<callout emoji="⚠️" border-color="red">
<p><b>{风险标题_2}</b></p>
<p><b>触发：</b>{trigger_2}</p>
<p>{why_2}</p>
<p><b>证伪：</b>{invalidate_2}</p>
</callout>

<!-- 共 N 条风险，至少 3 条，每条一个独立 callout -->
```

要求：

- `risks` 至少 3 条。
- 每条风险使用一个独立 `<callout>`：红框（`border-color="red"`）、无背景色（不设 `background-color`）。
- 每条包含 4 行：标题（`title`）、触发条件（`trigger`）、传导链解释（`why`）、证伪条件（`invalidate`）。
- 标题加粗，触发和证伪标签加粗。

## ⑥ 信息来源

对应 `doc.md` 字段：`sources`。

```xml
<hr/>
<h1 align="left"><span text-color="orange">⑥ 信息来源</span></h1>
<p align="left">[1] <a href="{url}">{name}</a> — {date} — {title}</p>
<p align="left">[2] <a href="{url}">{name}</a> — {date} — {title}</p>
<!-- ... -->
<p align="left">[N] 同花顺数据库 — 行情、成交、估值与10股近7个交易日数据</p>
```

要求：

- 每条来源一行 `<p>`，编号从 1 开始。
- 有 URL 的来源必须使用 `<a href="{url}">{name}</a>` 可点击链接。
- 无 URL 的来源用粗体名称，不加空链接。
- 最后一条固定为同花顺数据库（工具来源标识），说明覆盖的数据范围。
- 不使用表格堆放来源，避免链接撑宽。

## 免责声明

固定为以下三段灰色文字，紧跟"信息来源"之后：

```xml
<hr/>
<h1 align="left"><span text-color="orange">免责声明</span></h1>
<p align="left"><span text-color="gray">以上内容为AI自动生成或AI辅助生成，仅用于信息整理、投研辅助、教育交流或一般性分析参考，不构成对任何金融产品、交易策略或投资行为的推荐、邀约、承诺或保证，也不构成投资、法律、税务、会计等专业意见。</span></p>
<p align="left"><span text-color="gray">以上内容可能基于公开信息、历史数据或用户提供材料进行总结、归纳、推演与情景分析，但相关内容可能存在时效性不足、信息缺漏、事实误差、模型偏差或生成性错误，历史数据、历史业绩、回测结果及情景假设均不代表未来表现。</span></p>
<p align="left"><span text-color="gray">用户应基于自身风险承受能力、投资目标、财务状况及适用法律法规独立作出判断，必要时咨询持牌专业机构或顾问。任何因依赖以上内容而作出的决策及其后果，由用户自行承担。</span></p>
```

免责声明不可简写、不可合并、不可省略任一段。

## 固定表格列宽汇总

以下仅列出使用 `<table>` 的区块；四维度高亮块与四组分类高亮块使用 `<column-group>` + `<callout>` 分栏布局，不在此表。

| 表格 | 列数 | 列宽 (px) |
|------|------|-----------|
| 双轨热度表 | 4 | 100 / 80 / 220 / 400 |
| 10 股行情表 | 6 | 120 / 100 / 130 / 130 / 150 / 170 |

## 生成前校验

在构造 lark-doc XML 之前，必须先逐项验证 `doc.md` 字段完整性（若走 legacy 路径，则等价校验 payload）：

- [ ] `sector`、`market`、`index_caliber`、`timestamp`、`composite_score`、`gauge_pill`、`info_score`、`market_score` 存在且非空
- [ ] `headline`、`summary` 存在且非空
- [ ] `key_chips` 恰好 4 个，每个有 `label`、`value`（`unit` 可嵌入 value 或独立提供）
- [ ] `selected_stocks` 恰好 10 个股票名
- [ ] `divergence` 含 `verdict` 和 `meaning`
- [ ] `answer` 含 `restate`、`conclusion`、`next`
- [ ] `dimensions` 恰好 4 个，每个有 `name`、`state`、`value`、`read`
- [ ] `catalysts` 精选 3-5 条，最多 6 条，每条有 `date`、`title`、`tone`、`category`、`source_name`、`fact`、`why`、`verify`
- [ ] `stocks` 恰好 10 只，每只有 `name`、`role`、`change`、`turnover`、`change_7d`、`turnover_7d`
- [ ] `divergence_groups` 四组键完整（放量上攻、缩量上行、缩量回调、放量杀跌），每组含 `stocks` 和 `feature`
- [ ] `watch_signals` 至少 3 条
- [ ] `risks` 至少 3 条
- [ ] `sources` 至少 1 条
- [ ] `section_summaries` 含 `heat`、`catalysts`、`divergence`、`watch`、`risks`，每个值非空

任意一项不满足，必须先修复 `doc.md` 再生成。`doc.md` 修复需回到第一阶段修正 facts 或正文后重新生成，不得在 XML 中手工补数据；若走 legacy 路径，则按 payload 规则回退处理。

## lark-doc 写入复核

生成飞书文档版后，必须优先通过 `lark-doc` 写入飞书文档。写入后若具备 Chrome/飞书页面操作条件，应打开文档检查：

- 标题是否变成飞书标题样式。
- 元信息是否在标题下方保持紧凑。
- 合规提示是否显示为浅灰底、橙色边框的 callout。
- 每个一级章节前是否有单个分割线，章节标题是否有橙色强调。
- 4 核心指标展示为两栏分栏布局，每栏 2 个灰底 callout 高亮块，标签在上、数值在下。
- 双轨热度表正确展示，两条热度条均为 10 个可见方块，不满 5 分的部分用极浅灰方块补齐。
- 10 股行情表格 6 列对齐，涨跌幅写清"上涨/下跌"方向。
- 四组行为分类展示为上下两组独立两栏分栏，每组横向 2 个高亮块，每组含组名、股票代码块和解释文字，空组显示"（无）"。
- 催化时间线条目结构完整，`<blockquote>` 缩进正常。
- 盯盘信号每条为一个灰底 callout，风险提示每条为一个红框 callout。
- 信息来源链接可点击。
- 免责声明三段完整，灰色文字紧跟信息来源。
- 没有 Markdown 语法残留（`**`、`#`、`- `、`> ` 等未转换的标记）。
- 没有 CSS、图表残留、图片占位或网页组件文本。

如果不能调用 `lark-doc`，不得静默改为对话框长文输出；必须说明无法写入飞书文档的原因，并询问用户是否接受先输出 lark-doc 标签版草稿。
