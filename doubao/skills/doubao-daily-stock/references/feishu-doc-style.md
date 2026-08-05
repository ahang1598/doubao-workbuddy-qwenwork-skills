## 飞书文档版报告规范

## 第二轮必读执行摘要

本文件是用户确认生成飞书文档版后的强制格式门禁。进入飞书文档编辑流程后，必须先从本文件开头读到结尾，再组装 `lark-doc` XML；不得只搜索关键词、只读取局部片段、只依赖 `SKILL.md` 或 `core-workflow.md` 摘要生成飞书文档。

飞书文档版只做结构化和样式调优，事实、观点、章节顺序、表格字段、来源编号和免责声明必须与完整 Markdown 内容底稿对齐，不得在第二轮重新生成或改写内容判断。

飞书写入硬规则：

- 必须通过 `lark-doc` 写入飞书文档；除非 `lark-doc` 不可用且用户明确同意，才可输出标签版草稿。
- 写入内容必须是 `lark-doc` 支持的静态 XML 标签和文本，主要使用 `title/h1/h3/p/ol/table/callout/hr/span/a`。
- 首屏顺序固定为：文档标题 -> 灰色元信息 -> 浅灰底合规提示 callout -> 公司一句话简介 -> 核心结论 -> 摘要指标表 -> 第一部分正文。
- 强调色目标固定为 `#005689`；若当前 `lark-doc` 只支持命名色，标题和关键数字使用 `text-color="orange"` 作为 fallback。
- 表格表头使用 `background-color="light-gray"`，表头文字使用 `text-color="orange"`、加粗、居中。
- 表格第一列行标签使用 `background-color="light-gray"`；所有表格文字统一用 `<p align="center">...</p>` 居中。
- 所有表格必须使用 `<colgroup>` 固定列宽；不得临时省略 `<colgroup>`、改列名、改列数或生成超过 5 列的宽表。
- 固定列宽：摘要指标表 `170 / 230 / 170 / 230`；A 股资金流表 `190 / 200 / 410`；港股资金流表 `200 / 200 / 400`；美股资金流表 `160 / 200 / 440`；技术指标表 `110 / 150 / 390 / 150`；关键价格区间表 `150 / 210 / 440`；A 股完整盈利预测表 `130 / 190 / 190 / 145 / 145`；港股/美股评级目标价表 `240 / 200 / 190 / 170`。
- 摘要指标、资金流、技术指标、关键价格区间、投行一致预期必须使用本文“固定表格模板”的结构；缺失字段统一写 `暂无`。
- 不依赖红绿颜色表达涨跌，必须在文字中写清“上涨/下跌”“净流入/净流出”。
- 文末必须依次输出“信息来源”和“免责声明”；每个关键数据或事实必须能回链到来源编号。

## 输出目标

生成适合通过 `lark-doc` skill 写入飞书文档的结构化报告。报告内容、章节顺序、数据引用和合规口径与对话版日报保持一致，但最终交付必须进入飞书文档，而不是只在对话框重新输出完整报告。

本规范的视觉目标是白底、深黑正文、强调色标题、细规则线分区、紧凑但可读的表格和较高信息密度。执行层面只使用 `lark-doc` 明确支持的属性。

`lark-doc` 可设置标题、段落、列表、表格、引用块、分割线、超链接、`span` 文字色/背景色、`callout`、表格列宽和单元格背景色；在多数环境下不能稳定设置字体、字号、行高、段间距、页边距、纸张大小、页眉页脚或自定义 hex 色。因此本版本只使用飞书稳定支持的原生元素，并把无法直接设置的细节转换为标题层级和结构规则：

- 文档标题：`<title align="left">`。
- 标题层级：`<h1>`、`<h2>`、`<h3>`。
- 普通段落：`<p>`。
- 编号列表：`<ol>`、`<li>`。
- 表格：`<table>`、`<colgroup>`、`<col>`、`<thead>`、`<tbody>`、`<tr>`、`<th>`、`<td>`。
- 引用和提示：`<blockquote>`、`<callout>`。
- 分割线：`<hr/>`。
- 加粗、链接和行内颜色：`<b>`、`<a>`、`<span text-color>`、`<span background-color>`。
- 来源编号，如 `[1]`、`[2]`。

要求：

- 只使用 `lark-doc` 支持的静态标签和文本。
- 不依赖红绿颜色表达涨跌；必须在文字中写清“上涨/下跌”“净流入/净流出”。
- 不使用营销式标题、长横线分割、复杂嵌套列表。

## lark-doc 可执行样式基准

用户确认生成飞书文档后，必须调用 `lark-doc` 写入飞书文档。不要把完整报告正文直接丢在对话框里，除非 `lark-doc` 不可用且用户明确同意先看草稿。

### 写入方式

飞书文档版必须先组装为一段完整的 lark-doc XML 内容，再通过 `lark-doc` 写入：

- 新建文档或用户明确允许重写目标文档时，优先使用全文写入/覆盖类操作，把完整 XML 作为 `content` 传入。
- 已有文档如含评论、图片、附件或用户手工编辑内容，使用覆盖写入前必须确认；否则先读取文档结构，再使用块级替换/追加方式更新。
- 写入内容必须是 lark-doc XML 片段。
- 动态文本写入 XML 前必须转义：`&` -> `&amp;`，`<` -> `&lt;`，`>` -> `&gt;`，普通换行 -> `<br/>`。
- 行内样式嵌套顺序必须遵守：`<a>` -> `<b>` -> `<em>` -> `<del>` -> `<u>` -> `<code>` -> `<span>` -> 文本。

默认传输策略：

1. 用户没有给目标文档：询问是否新建飞书文档，并在新文档中写入完整 XML。
2. 用户给了目标文档且明确说“覆盖/重写”：使用完整 XML 覆盖写入。
3. 用户给了目标文档但没有说可覆盖：先读取文档，确认后再覆盖；若用户只要追加，则追加到文末。

### 可设置与不可设置

- 可以设置：标题层级、段落/列表、对齐、引用块、分割线、callout 背景/边框/文字色、表格列宽、单元格背景色、超链接、行内文字颜色和背景色。
- 不能稳定设置：字体、字号、行高、字间距、段间距、页边距、纸张大小、页眉页脚、表格边框粗细；自定义 hex 色仅在目标 `lark-doc` 环境明确支持时使用。
- 强调色目标固定为 `#005689`，等价 RGB 为 `rgb(0, 86, 137)`，HSL 为 `hsl(202, 100%, 27%)`。飞书文档/屏幕端优先用 HEX 表述；RGB/HSL 只作为等价说明，CMYK `100, 37, 0, 46` 仅作为打印参考，不作为飞书写入参数。
- 如果 `lark-doc` 支持自定义文字色，主标题、章节标题、二级小标题和关键数字使用 `#005689`。如果当前 `lark-doc` 只支持命名色，则使用 `text-color="orange"` 作为近似 fallback，避免误用浅橙或高饱和亮橙。
- 命名色 fallback 只能使用 `red`、`orange`、`yellow`、`green`、`blue`、`purple`、`gray` 及 `light-*`、`medium-*` 系列中的可用色。
- 飞书中的近似实现：主标题、章节标题和关键数字按 `#005689` 目标色处理，命名色 fallback 用 `text-color="orange"`；避免大面积浅橙底；辅助信息和表格底色用 `gray` / `light-gray`，用 `<hr/>` 做章节区隔，用紧凑表格和列宽控制信息密度。

### 顶部版式

避免长标题在 PDF 导出时折行过重。文档标题只放公司名，股票代码和日期放在下一行元信息里：

```xml
<title align="left">个股日报：股票简称</title>
<p align="left"><span text-color="gray">证券代码：601899.SH / 02899.HK｜生成日期：YYYY-MM-DD｜数据截至：YYYY-MM-DD 收盘｜报告口径：研究讨论，不构成投资建议</span></p>
<callout emoji="📌" background-color="light-gray" border-color="orange" text-color="gray">
<p>以下内容仅为行情与逻辑分析，不构成任何投资买卖建议，务必结合自身风险承受能力决策。</p>
</callout>
<p align="left"><b>公司一句话简介：</b>...</p>
<hr/>
```

要求：

- 顶部不用大段免责声明，避免首屏松散。
- 元信息一行优先；过长时拆成两行 `<p>`，不要放进 4 列表格。
- 公司一句话简介控制在 28-60 个中文字符。
- 顶部 `callout` 只用于合规提示，不堆积观点；emoji 固定用 `📌`，不得临时换成营销感图标。

### 标题与分区

一级章节必须用 `hr + h1` 形成报告式分区：

```xml
<hr/>
<h1 align="left"><span text-color="orange">一、今日行情、量能与资金流向</span></h1>
<h3 align="left"><span text-color="orange">价格与量能</span></h3>
```

要求：

- 每个一级章节前使用一个 `<hr/>`，不得连续使用多个分割线。
- 一级章节使用 `<h1 align="left"><span text-color="orange">...</span></h1>`。
- 二级小标题使用 `<h3 align="left"><span text-color="orange">...</span></h3>`，不得使用 `<h2>`，避免“价格与量能”“关键价格区间”等副标题视觉上接近一级章节。
- 字号视觉目标固定为：报告标题约 18 pt；一级章节约 14 pt；二级小标题约 12 pt；正文约 10.5 pt。飞书无法直接设字号时，用 `title / h1 / h3 / p` 的层级逼近该比例。
- 普通段落使用 `<p align="left">`；每段 80-160 个汉字，避免导出 PDF 后形成大块文字墙。
- 重点词可用 `<b>`，不要整段加粗。
- 编号列表使用 `<ol>`，每个 `<li>` 必须写 `seq="auto"`，保证飞书自动编号稳定。

### 表格样式

所有表格采用 `lark-doc` 可落地的“结构化模型表”近似样式：

- 使用 `<colgroup>` 明确列宽，避免 PDF 导出后错列或宽表撑开。
- 表头 `<th background-color="light-gray">`，表头文字用 `<p align="center"><b><span text-color="orange">...</span></b></p>`；所有表头必须居中。不要使用浅橙表头，以免整体显得偏轻。
- 第一列行标签使用 `<td background-color="light-gray" vertical-align="middle">`，所有表格文字统一居中。
- 所有表格正文统一使用 `<p align="center">...</p>` 居中。
- 所有单元格统一使用 `vertical-align="middle"` + `<p align="center">...</p>`。
- 数字列所在单元格内容尽量短，并在文本中保留正负号、单位和来源编号。
- 价格、比例、金额等数值数据单元格统一使用 `<p align="center"><b>...</b></p>` 加粗；纯文本解释列（如复盘含义、分析、观察含义）不加粗。
- 关键汇总行可使用 `background-color="light-gray"`，不要大面积使用 `light-orange` 或 `medium-orange`，因为飞书不能保证白字表头，也会降低整体可读性。
- 表格不超过 5 列；超过 5 列时拆表或改为纵向指标表。
- 不使用 `rowspan` 和 `colspan` 做复杂表头，除非用户明确要求；日报模板保持单层表头，减少飞书导出 PDF 错位。

表格适配规则：

- 摘要指标表固定 4 列，列宽固定为 `170 / 230 / 170 / 230`。
- A 股资金流表固定 3 列，列宽固定为 `190 / 200 / 410`。
- 港股资金流表固定 3 列，列宽固定为 `200 / 200 / 400`。
- 美股资金流表固定 3 列，列宽固定为 `160 / 200 / 440`。
- 技术指标表固定 4 列，列宽固定为 `110 / 150 / 390 / 150`。
- 关键价格区间表固定 3 列，列宽固定为 `150 / 210 / 440`。
- A 股完整盈利预测表固定 5 列，列宽固定为 `130 / 190 / 190 / 145 / 145`。
- 港股/美股评级目标价表固定 4 列，列宽固定为 `240 / 200 / 190 / 170`。
- 信息来源不使用表格，使用普通编号行，避免链接把表格撑宽。

### 固定表格模板

生成飞书文档版时，以下表格的结构和列宽必须固定，不得临时改列名、改列数或省略 `<colgroup>`。

摘要指标表：

```xml
<table>
<colgroup><col width="170"/><col width="230"/><col width="170"/><col width="230"/></colgroup>
<thead><tr>
<th background-color="light-gray"><p align="center"><b><span text-color="orange">指标</span></b></p></th>
<th background-color="light-gray"><p align="center"><b><span text-color="orange">数值</span></b></p></th>
<th background-color="light-gray"><p align="center"><b><span text-color="orange">指标</span></b></p></th>
<th background-color="light-gray"><p align="center"><b><span text-color="orange">数值</span></b></p></th>
</tr></thead>
<tbody>
<tr><td background-color="light-gray" vertical-align="middle"><p align="center">当前价格</p></td><td vertical-align="middle"><p align="center"><b>...</b></p></td><td background-color="light-gray" vertical-align="middle"><p align="center">涨跌幅</p></td><td vertical-align="middle"><p align="center"><b>...</b></p></td></tr>
<tr><td background-color="light-gray" vertical-align="middle"><p align="center">日内区间</p></td><td vertical-align="middle"><p align="center"><b>...</b></p></td><td background-color="light-gray" vertical-align="middle"><p align="center">总市值</p></td><td vertical-align="middle"><p align="center"><b>...</b></p></td></tr>
<tr><td background-color="light-gray" vertical-align="middle"><p align="center">市盈率 TTM</p></td><td vertical-align="middle"><p align="center"><b>...</b></p></td><td background-color="light-gray" vertical-align="middle"><p align="center">成交额</p></td><td vertical-align="middle"><p align="center"><b>...</b></p></td></tr>
<tr><td background-color="light-gray" vertical-align="middle"><p align="center">换手率</p></td><td vertical-align="middle"><p align="center"><b>...</b></p></td><td background-color="light-gray" vertical-align="middle"><p align="center">量比</p></td><td vertical-align="middle"><p align="center"><b>...</b></p></td></tr>
</tbody>
</table>
```

A 股资金流表：

```xml
<table>
<colgroup><col width="190"/><col width="200"/><col width="410"/></colgroup>
<thead><tr>
<th background-color="light-gray"><p align="center"><b><span text-color="orange">资金类别</span></b></p></th>
<th background-color="light-gray"><p align="center"><b><span text-color="orange">流入/流出情况</span></b></p></th>
<th background-color="light-gray"><p align="center"><b><span text-color="orange">复盘含义</span></b></p></th>
</tr></thead>
<tbody>
<tr><td background-color="light-gray" vertical-align="middle"><p align="center">主力资金</p></td><td vertical-align="middle"><p align="center"><b>...</b></p></td><td vertical-align="middle"><p align="center">...</p></td></tr>
<tr><td background-color="light-gray" vertical-align="middle"><p align="center">超大单资金</p></td><td vertical-align="middle"><p align="center"><b>...</b></p></td><td vertical-align="middle"><p align="center">...</p></td></tr>
<tr><td background-color="light-gray" vertical-align="middle"><p align="center">大单资金</p></td><td vertical-align="middle"><p align="center"><b>...</b></p></td><td vertical-align="middle"><p align="center">...</p></td></tr>
<tr><td background-color="light-gray" vertical-align="middle"><p align="center">北向资金</p></td><td vertical-align="middle"><p align="center"><b>...</b></p></td><td vertical-align="middle"><p align="center">...</p></td></tr>
</tbody>
</table>
```

北向资金行仅在陆港通标的中出现，非陆港通股票必须删除该行。第一列只写短标签 `北向资金`，不要把“仅陆港通”等适用条件写进第一列；该短标签必须用 `<p align="center">北向资金</p>` 居中。

港股资金流表：

```xml
<table>
<colgroup><col width="200"/><col width="200"/><col width="400"/></colgroup>
<thead><tr>
<th background-color="light-gray"><p align="center"><b><span text-color="orange">资金指标</span></b></p></th>
<th background-color="light-gray"><p align="center"><b><span text-color="orange">流入/流出情况</span></b></p></th>
<th background-color="light-gray"><p align="center"><b><span text-color="orange">复盘含义</span></b></p></th>
</tr></thead>
<tbody>
<tr><td background-color="light-gray" vertical-align="middle"><p align="center">资金净流入/流出</p></td><td vertical-align="middle"><p align="center"><b>...</b></p></td><td vertical-align="middle"><p align="center">...</p></td></tr>
<tr><td background-color="light-gray" vertical-align="middle"><p align="center">南向资金</p></td><td vertical-align="middle"><p align="center"><b>...</b></p></td><td vertical-align="middle"><p align="center">...</p></td></tr>
</tbody>
</table>
```

南向资金行仅在港股通标的且取得权威数据时出现，非港股通股票或未取得权威数据时必须删除该行。第一列只写短标签 `南向资金`，不要把“仅港股通”等适用条件写进第一列；该短标签必须用 `<p align="center">南向资金</p>` 居中。

美股资金流表：

```xml
<table>
<colgroup><col width="160"/><col width="200"/><col width="440"/></colgroup>
<thead><tr>
<th background-color="light-gray"><p align="center"><b><span text-color="orange">资金类别</span></b></p></th>
<th background-color="light-gray"><p align="center"><b><span text-color="orange">流入/流出情况</span></b></p></th>
<th background-color="light-gray"><p align="center"><b><span text-color="orange">复盘含义</span></b></p></th>
</tr></thead>
<tbody>
<tr><td background-color="light-gray" vertical-align="middle"><p align="center">资金净流入/流出</p></td><td vertical-align="middle"><p align="center"><b>...</b></p></td><td vertical-align="middle"><p align="center">...</p></td></tr>
</tbody>
</table>
```

技术指标表：

```xml
<table>
<colgroup><col width="110"/><col width="150"/><col width="390"/><col width="150"/></colgroup>
<thead><tr>
<th background-color="light-gray"><p align="center"><b><span text-color="orange">指标</span></b></p></th>
<th background-color="light-gray"><p align="center"><b><span text-color="orange">标签</span></b></p></th>
<th background-color="light-gray"><p align="center"><b><span text-color="orange">分析</span></b></p></th>
<th background-color="light-gray"><p align="center"><b><span text-color="orange">判断</span></b></p></th>
</tr></thead>
<tbody>
<tr><td background-color="light-gray" vertical-align="middle"><p align="center">MA</p></td><td vertical-align="middle"><p align="center"><b>...</b></p></td><td vertical-align="middle"><p align="center">...</p></td><td vertical-align="middle"><p align="center">...</p></td></tr>
<tr><td background-color="light-gray" vertical-align="middle"><p align="center">MACD</p></td><td vertical-align="middle"><p align="center"><b>...</b></p></td><td vertical-align="middle"><p align="center">...</p></td><td vertical-align="middle"><p align="center">...</p></td></tr>
<tr><td background-color="light-gray" vertical-align="middle"><p align="center">RSI</p></td><td vertical-align="middle"><p align="center"><b>...</b></p></td><td vertical-align="middle"><p align="center">...</p></td><td vertical-align="middle"><p align="center">...</p></td></tr>
</tbody>
</table>
```

关键价格区间表：

```xml
<table>
<colgroup><col width="150"/><col width="210"/><col width="440"/></colgroup>
<thead><tr>
<th background-color="light-gray"><p align="center"><b><span text-color="orange">项目</span></b></p></th>
<th background-color="light-gray"><p align="center"><b><span text-color="orange">数值</span></b></p></th>
<th background-color="light-gray"><p align="center"><b><span text-color="orange">观察含义</span></b></p></th>
</tr></thead>
<tbody>
<tr><td background-color="light-gray" vertical-align="middle"><p align="center">当前价</p></td><td vertical-align="middle"><p align="center"><b>...</b></p></td><td vertical-align="middle"><p align="center">...</p></td></tr>
<tr><td background-color="light-gray" vertical-align="middle"><p align="center">震荡区间</p></td><td vertical-align="middle"><p align="center"><b>...</b></p></td><td vertical-align="middle"><p align="center">...</p></td></tr>
<tr><td background-color="light-gray" vertical-align="middle"><p align="center">压力位</p></td><td vertical-align="middle"><p align="center"><b>...</b></p></td><td vertical-align="middle"><p align="center">...</p></td></tr>
<tr><td background-color="light-gray" vertical-align="middle"><p align="center">支撑位</p></td><td vertical-align="middle"><p align="center"><b>...</b></p></td><td vertical-align="middle"><p align="center">...</p></td></tr>
</tbody>
</table>
```

一致预期表：

- A 股盈利预测：列宽 `130 / 190 / 190 / 145 / 145`，表头固定为”年份 / 归母净利润 / 营业总收入 / 每股收益 / 市盈率”。
- 港股、美股评级目标价：列宽 `240 / 200 / 190 / 170`，表头固定为”机构名称 / 最新评级 / 目标价 / 日期”。
- 一致预期表同样遵守全局表格对齐规则：所有表头和正文统一居中。

## 触发规则

默认仍先输出对话版完整日报。只有用户明确表示“生成飞书文档版 / 做成飞书文档 / 继续生成 / 生成完整报告 / 做成文档”时，才调用 `lark-doc` 生成或编辑飞书文档版完整报告。

## 文档结构

飞书文档版必须按以下顺序写入 `lark-doc` 内容：

```xml
<title align="left">个股日报：股票简称</title>
<p align="left"><span text-color="gray">证券代码：...｜生成日期：YYYY-MM-DD｜数据截至：YYYY-MM-DD 收盘｜报告口径：研究讨论，不构成投资建议</span></p>
<callout emoji="📌" background-color="light-gray" border-color="orange" text-color="gray">
<p>以下内容仅为行情与逻辑分析，不构成任何投资买卖建议，务必结合自身风险承受能力决策。</p>
</callout>
<p align="left"><b>公司一句话简介：</b>...</p>
<hr/>

<h1 align="left"><span text-color="orange">核心结论</span></h1>
<ol>
<li seq="auto"><b>直接回答：</b>...</li>
<li seq="auto"><b>价格与量能：</b>...</li>
<li seq="auto"><b>板块位置：</b>...</li>
<li seq="auto"><b>技术区间：</b>...</li>
<li seq="auto"><b>消息与风险：</b>...</li>
</ol>

<h1 align="left"><span text-color="orange">摘要指标</span></h1>
<table>...</table>
<p align="left"><span text-color="gray">注：以上行情摘要截至 ...</span></p>

<hr/>
<h1 align="left"><span text-color="orange">一、今日行情、量能与资金流向</span></h1>
<h3 align="left"><span text-color="orange">价格与量能</span></h3>
<p align="left">...</p>
<h3 align="left"><span text-color="orange">资金流向</span></h3>
<table>...</table>

<hr/>
<h1 align="left"><span text-color="orange">二、板块联动与个股地位</span></h1>
...

<hr/>
<h1 align="left"><span text-color="orange">信息来源</span></h1>
<p align="left">[1] 来源名称｜日期｜标题｜<a href="https://...">https://...</a></p>

<hr/>
<h1 align="left"><span text-color="orange">免责声明</span></h1>
<p align="left"><span text-color="gray">...</span></p>
```

## 顶部信息

文档标题固定为：

`<title align="left">个股日报：股票简称</title>`

标题下方用一行或两行灰色元信息承接证券代码、生成日期、数据截至和报告口径：

`<p align="left"><span text-color="gray">证券代码：...｜生成日期：...｜数据截至：...｜报告口径：研究讨论，不构成投资建议</span></p>`

免责声明短提示固定放在浅灰底、橙色边框的 callout 中：

`<callout emoji="📌" background-color="light-gray" border-color="orange" text-color="gray"><p>以下内容仅为行情与逻辑分析，不构成任何投资买卖建议，务必结合自身风险承受能力决策。</p></callout>`

元信息不做表格，避免飞书导出 PDF 后首屏过宽：

- `生成日期：YYYY-MM-DD`
- `数据截至：YYYY-MM-DD HH:MM（交易日盘中）` 或 `数据截至：YYYY-MM-DD 收盘`
- `报告口径：研究讨论，不构成投资建议`
- `公司一句话简介：...`

公司一句话简介控制在 28-60 个中文字符，包含核心业务、行业地位或产业链位置。

## 核心结论

使用 3-5 条编号列表。第一条必须直接回答用户问题。核心结论虽然展示在开头，但必须在全部数据、资讯和分项分析完成后最后撰写。

每条必须写为 `<li seq="auto">`，开头使用 `<b>` 加粗主题词：

- `<li seq="auto"><b>直接回答：</b>...</li>`
- `<li seq="auto"><b>价格与量能：</b>...</li>`
- `<li seq="auto"><b>板块位置：</b>...</li>`
- `<li seq="auto"><b>技术区间：</b>...</li>`
- `<li seq="auto"><b>消息与风险：</b>...</li>`

不要使用卡片、彩色标签或小圆点堆叠。

## 摘要指标

摘要指标使用 4 行 4 列 `lark-doc` 表格，表头固定为“指标 / 数值 / 指标 / 数值”。写入时必须使用 `<table>`、`<colgroup>`、`<thead>`、`<tbody>`、`<th background-color="light-gray">` 和必要的 `<td background-color="light-gray">`。

摘要指标 8 项只能来自 `seed_finance_search（同花顺数据库）` 或基于其返回值自行计算：当前价格/收盘价、涨跌幅、日内区间、总市值、市盈率 TTM、成交额、换手率直接取自 `seed_finance_search（同花顺数据库）`；量比只在收盘口径下自行计算，公式为 `当日成交量 / 过去 5 个交易日平均成交量`，成交量输入必须来自 `seed_finance_search（同花顺数据库）`；盘中口径统一写 `暂无`，不得估算。不得使用 `general_search` 或其他来源补数。

字段顺序固定：

1. 当前价格 / 涨跌幅。
2. 日内区间 / 总市值。
3. 市盈率 TTM / 成交额。
4. 换手率 / 量比。

要求：

- 每个数值必须带来源编号。
- 单位直接写进数值。
- 缺失项写 `暂无`，不要写长句。
- 表格后必须写一行时间口径注释，并说明量比计算口径。收盘口径写：`注：以上行情摘要为 ... 收盘口径；量比为自行计算，公式为当日成交量 / 过去 5 个交易日平均成交量，成交量输入来自 seed_finance_search（同花顺数据库）。` 盘中口径写：`注：以上行情摘要截至 ...（交易日盘中）；量比因盘中缺少可比口径成交量，暂不计算。`
- 涨跌幅、净流入/净流出必须在正文解释中写清方向，不依赖颜色。

## 一、今日行情、量能与资金流向

### 价格与量能

写 2-3 段：

1. 价格、涨跌幅、日内区间和价格结构。
2. 成交额、近 5 日均值对比、换手率、量比（盘中为 `暂无`）、放量/缩量判断。
3. 今日走势原因：公司公告、业绩、订单、产品、客户、行业景气、政策、宏观、海外映射或板块情绪。没有明确原因时，必须写“未见明确基本面催化，盘面更偏交易结构/板块情绪驱动”。

### 资金流向

A 股使用 `lark-doc` 表格，表头固定为“资金类别 / 流入/流出情况 / 复盘含义”。行项目固定为主力资金、超大单资金、大单资金；若为陆港通标的，再追加北向资金行。非陆港通股票不得生成北向资金行。中单、小单暂不展示。第一列使用 `background-color="light-gray"`，表头用 `background-color="light-gray"`，表头文字用 `text-color="orange"`。第一列的 `主力资金`、`超大单资金`、`大单资金`、`北向资金` 都是 10 个字符以内短标签，必须全部居中。

港股使用 `lark-doc` 表格，表头固定为“资金指标 / 流入/流出情况 / 复盘含义”。行项目固定为资金净流入/流出；若为港股通标的且取得权威数据，再追加南向资金行。非港股通股票或无权威南向资金数据时不得生成南向资金行。港股不分大单小单，不得生成 A 股“主力资金 / 超大单 / 大单 / 北向资金”表格。

美股使用 `lark-doc` 表格，表头固定为“资金类别 / 流入/流出情况 / 复盘含义”，只保留一行“资金净流入/流出”。不得生成 A 股或港股专用资金行。

A 股资金流向指标只能来自 `seed_finance_search（同花顺数据库）`，不得使用 `general_search` 或其他来源补数。港股/美股资金净流入/净流出及港股通南向资金先查 seed；若 seed 未返回，可用 `general_search` 检索官方或权威机构来源，但数据日期必须是报告当日或最近一个有效交易日。若来源返回流入额和流出额，可写为 `净流入 +X（流入 X / 流出 X）[N]`；若只返回净额，则直接写 `净流入/净流出 X[N]`。

## 二、板块联动与个股地位

先写一行简洁标签，使用普通文本，不做彩色标签：

`板块标签：光模块 +1.23%[4]｜AI 算力 +0.87%[4]｜上涨 32 家 / 下跌 11 家[4]｜个股强于板块`

随后写 1-2 段分析：

- 个股涨跌幅相对板块/指数的强弱。
- 是领涨权重、跟随补涨、拖累板块，还是逆势表现。
- 用户问题涉及行业事件时，说明该事件是个股 alpha 还是板块 beta。

## 三、技术面分析

技术面分析使用两个 `lark-doc` 表格加一段总结。

### 指标状态

固定使用三行 `lark-doc` 表格，表头为“指标 / 标签 / 分析 / 判断”，三行顺序为 MA、MACD、RSI。“分析”列应设置为最宽列。

要求：

- 只保留 MA、MACD、RSI 三行，顺序固定。
- “分析”必须解释指标含义，不只堆数字。
- 指标读数必须带来源编号；缺失写 `暂无`。

### 关键价格区间

固定使用 `lark-doc` 表格。表头为“项目 / 数值 / 观察含义”，行顺序固定为当前价、震荡区间、压力位、支撑位。

表格后写一段技术面总结，按 `question_focus` 回答：

- `target_price`：上方第一压力区、乐观情景触发条件、失效条件。
- `short_trade`：短线波动环境和风险，不写入场、止损、止盈或仓位指令。
- `event_catalyst`：事件是否已经反映在突破、放量、跳空或高位震荡中。

## 四、消息面与隔夜观察

分两个小节：

### 消息面复盘

写最近 3 日内最重要的 3-5 条基本面/产业面消息。每条使用“日期 + 事实 + 影响判断”的短段落，不用表格堆标题。

### 隔夜潜在资讯

写未来几日可能影响公司业务、行业景气或估值的事项。不要写空泛的“关注资金流向”“关注是否继续放量”。

## 五、投行一致预期

根据市场和可得数据二选一：

A 股或完整盈利预测使用 `lark-doc` 表格，表头为“年份 / 归母净利润 / 营业总收入 / 每股收益 / 市盈率”。

港股、美股或评级目标价使用 `lark-doc` 表格，表头为“机构名称 / 最新评级 / 目标价 / 日期”。

无可核验覆盖时，不生成空表格，使用三段文字：

1. `截至本报告生成时，暂未检索到可核验的投行/券商覆盖、评级或目标价记录。`
2. 说明机会：关注度低、预期发现、估值重估。
3. 说明风险：外部验证不足、估值锚弱、信息透明度和流动性不确定。

## 六、综合评估

先写研究判断句：

`综合当日盘面、资金净流向、技术形态、消息面和估值位置，研究判断为：中性偏强。`

研究判断句后写 2-3 段说明，每段 60-120 字，必须包含基本面或行业趋势判断，并结合估值、技术、资金、消息中的 2-3 项作为佐证。第六部分避免使用“评级”字眼。

禁止生成“操作建议”“空仓者”“持仓者”“短线参与者”“仓位 / 风控”“止损”“止盈”等具体交易建议表格或指令。

## 七、短期风险提示

使用 3-5 条 `<ol>` 编号列表，不使用小圆点。每条 1-2 句，每个 `<li>` 必须带 `seq="auto"`：

```xml
<ol>
<li seq="auto"><b>估值风险：</b>...</li>
<li seq="auto"><b>资金流反转风险：</b>...</li>
<li seq="auto"><b>行业波动风险：</b>...</li>
</ol>
```

至少一条风险必须直接对应 `question_focus`。

## 信息来源

使用普通段落，每条一行；来源编号保留在文本开头。外部来源链接写为 `<a href="...">...</a>`；`seed_finance_search（同花顺数据库）` 结构化数据可写工具来源标识、数据日期/时间和字段口径：

`<p align="left">[1] 来源名称｜YYYY-MM-DD｜标题｜<a href="https://...">https://...</a></p>`

`<p align="left">[2] seed_finance_search（同花顺数据库）｜YYYY-MM-DD HH:MM｜股票简称行情摘要及 A 股资金流字段｜工具返回字段：当前价格、涨跌幅、成交额、换手率、当日成交量、过去 5 个交易日成交量、A 股资金流；量比收盘后自行计算，盘中为暂无</p>`

要求：

- 正文、表格和结论中出现的每个关键数据或事实，都必须能对应到这里的来源编号。
- 外部链接必须是真实可打开的 URL、公告页面、媒体原文、公司/交易所/监管页面、产业/研报/预测原文或可打开数据页；摘要指标 8 项和 A 股资金流向指标必须标注 `seed_finance_search（同花顺数据库）` 工具来源标识，若工具返回可打开链接则同时附上链接；港股/美股资金数据若来自 `general_search`，必须列出官方或权威机构来源链接，且来源数据日期必须是报告当日或最近一个有效交易日。
- 不得使用 `#`、空链接、搜索结果页、本地材料包、内部核验记录或用户粘贴材料作为信息来源。
- 不得把多个不同事实都挂到同一个编号，除非确实来自同一篇原文或同一个数据页。

## 免责声明

固定为以下三段，紧跟“信息来源”之后：

```xml
<p align="left"><span text-color="gray">以上内容为AI自动生成或AI辅助生成，仅用于信息整理、投研辅助、教育交流或一般性分析参考，不构成对任何金融产品、交易策略或投资行为的推荐、邀约、承诺或保证，也不构成投资、法律、税务、会计等专业意见。</span></p>
<p align="left"><span text-color="gray">以上内容可能基于公开信息、历史数据或用户提供材料进行总结、归纳、推演与情景分析，但相关内容可能存在时效性不足、信息缺漏、事实误差、模型偏差或生成性错误，历史数据、历史业绩、回测结果及情景假设均不代表未来表现。</span></p>
<p align="left"><span text-color="gray">用户应基于自身风险承受能力、投资目标、财务状况及适用法律法规独立作出判断，必要时咨询持牌专业机构或顾问。任何因依赖以上内容而作出的决策及其后果，由用户自行承担。</span></p>
```

## lark-doc 写入复核

生成飞书文档版后，必须优先通过 `lark-doc` 写入飞书文档。写入后若具备 Chrome/飞书页面操作条件，应打开文档检查：

- 标题是否变成飞书标题样式。
- 元信息是否在标题下方保持紧凑，股票代码没有把标题挤成多行。
- 合规提示是否显示为浅灰底、橙色边框的 callout，而不是普通正文。
- 每个一级章节前是否有单个分割线，章节标题是否有橙色强调。
- 摘要指标表、资金流表、技术指标表、一致预期表是否没有过宽、错列或换行严重。
- 长段落是否过密；必要时拆成 80-160 字一段。
- 信息来源链接是否可点击。
- 免责声明是否紧跟信息来源。
- 没有非 `lark-doc` 标签或图片占位。

如果不能写入飞书文档，不得静默改为对话框长文输出；必须说明无法写入飞书文档的原因，并询问用户是否接受先输出标签版草稿。
