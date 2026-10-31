## HTML 报告版式规范

## 目录

- [输出目标](#输出目标)
- [首屏顺序硬规则](#首屏顺序硬规则)
- [视觉风格](#视觉风格)
- [版式防漂移硬规则](#版式防漂移硬规则)
  - [章节排版硬规则](#章节排版硬规则)
  - [边框白名单](#边框白名单)
- [页面结构](#页面结构)
  - [Header](#header)
  - [K线模块（当前版本已下线）](#k线模块当前版本已下线)
  - [摘要指标卡](#摘要指标卡)
  - [主体章节](#主体章节)
- [章节细则](#章节细则)
  - [一、今日行情、量能与资金流向](#一今日行情量能与资金流向)
  - [二、板块联动与个股地位](#二板块联动与个股地位)
  - [三、技术面分析](#三技术面分析)
  - [四、消息面与隔夜观察](#四消息面与隔夜观察)
  - [五、投行一致预期](#五投行一致预期)
  - [六、综合评级](#六综合评级)
  - [七、短期风险提示](#七短期风险提示)
  - [信息来源](#信息来源)
  - [免责声明](#免责声明)
- [分享版](#分享版)

## 输出目标

生成单文件 HTML，每次不同股票只替换数据和分析内容，视觉、结构、组件顺序保持一致。

必须：

- `<!DOCTYPE html>` 开头，`</html>` 结尾。
- 中文 `lang="zh-CN"`。
- CSS 内嵌。
- 当前版本不生成 K线模块，不内嵌 TradingView Lightweight Charts、KLineCharts、K线数据或图表初始化脚本。
- 无 `<script src=...>`、无外部 CSS、无外部图片、无外部字体。
- 可直接本地双击打开。

## 首屏顺序硬规则

首屏模块顺序必须固定，任何 agent 不得自行调整：

```html
<article class="report">
  <header class="report-header">...</header>
  <p class="lead">公司一句话简介/开篇判断...</p>
  <div class="metric-grid">...</div>
  <section class="section">一、今日行情、量能与资金流向...</section>
</article>
```

禁止：

- `.metric-grid` / 摘要指标卡必须直接跟在 `.lead` 后方。
- 不得插入 K线图、图表分隔线、空图容器或图表说明。
- 不得把 tabs 嵌入指标卡表格或做成表格 header。
- 不得生成 `今日 / 1个月 / 3个月` tabs。

## 视觉风格

延续投行/交易台快报风格：

- 背景：浅灰纸面 `#f5f4f1`。
- 主体纸张：`#fffdfa`。
- 文本：深黑 `#171717`。
- 规则线：低饱和灰棕 `#d9d3c8`。
- 主强调：深蓝 `#143d59`。
- 风险/压力强调：酒红 `#7a2f2f`。
- 字体：全页面统一使用同一套系统中文无衬线字体 `var(--sans)`；不得引入第二套等宽字体。数字对齐只能使用 `font-variant-numeric: tabular-nums`。
- 中文正文、标题、表格和标签统一使用中文标点：使用 `“”`、`（）`、`，`、`；`、`：`、`。`，不要在中文语句中使用英文直引号 `"..."`、英文括号 `(...)`、英文逗号或英文冒号。英文缩写、股票代码、百分号、时间和代码字段可保留必要英文字符。
- 不使用卡片堆叠、渐变、装饰图、营销页 hero。

## 版式防漂移硬规则

本报告采用单一最终版式系统。生成 HTML 时只能使用本文件规定的结构、class 和 CSS，不得把旧版本样式、临时补丁或其他 skill 的组件混入。

禁止：

- 不得出现历史覆盖块或改版标记，例如 `REDESIGN OVERRIDES`、`晨报 v2/v3/v4/v5/v7`、`override patch`、`dashboard_template`、`历史样式`、`改版补丁`。
- 不得生成或引用非本报告组件：`.hero`、`.news-card`、`.timeline`、`.hero-evidence`、`.summary-card`、`.dashboard-card`、`.memo-card` 等。
- 不得依赖图片改变布局；报告内不使用新闻图片、封面图或图片失败后的 DOM 改写。新闻和信息来源均为文本列表。
- 不得让模板猜页面结构。所有固定模块、表格、三项价格区间、三行指标状态和 3-5 条风险提示必须直接生成；表格和指标卡缺失数据统一写 `暂无`，或回到取数步骤，不得用其他字段 fallback 拼出不同版式，不得在单元格里写“暂未获取可信信息”这类长句。
- 不得用运行时 JS 生成报告正文、章节、表格、信息来源或免责声明；当前版本也不需要图表 JS。
- 不得新增 inline style。唯一例外是价格区间带内 `.zone-range`、`.zone-current`、`.zone-edge` 的 `left` / `width` 动态定位。
- `@media` 只能用于轻微移动端宽度适配、tab 换行和打印；不得在媒体查询中把 `.two-col`、`.technical-dashboard`、`.report-header` 改回左右分栏或改变模块顺序。

### 章节排版硬规则

以下排版系统必须全局复用，覆盖 7 个主体章节、“信息来源”和“免责声明”。不同 agent 不得自行放大标题、改变颜色、改段距或把标题做成卡片。

适用章节：

1. 一、今日行情、量能与资金流向
2. 二、板块联动与个股地位
3. 三、技术面分析
4. 四、消息面与隔夜观察
5. 五、投行一致预期
6. 六、综合评级
7. 七、短期风险提示
8. 信息来源
9. 免责声明

固定 CSS：

```css
.section {
  padding: 18px 0;
  border-top: 1px solid var(--rule);
}
.section h2 {
  margin: 0 0 12px;
  color: var(--ink);
  font-size: 18px;
  line-height: 1.35;
  font-weight: 700;
  letter-spacing: 0;
}
.section h3 {
  margin: 0 0 8px;
  color: var(--accent);
  font-size: 15px;
  line-height: 1.45;
  font-weight: 700;
  letter-spacing: 0;
}
.section p {
  margin: 0 0 10px;
  color: var(--ink);
  font-size: 14px;
  line-height: 1.72;
  letter-spacing: 0;
  word-spacing: 0;
  text-align: justify;
  text-align-last: left;
  text-justify: inter-character;
}
.section p:last-child { margin-bottom: 0; }
.section ul,
.section ol {
  margin: 0 0 10px;
  padding-left: 18px;
  color: var(--ink);
  font-size: 14px;
  line-height: 1.72;
}
.section li {
  margin: 5px 0;
  padding-left: 0;
}
.risk-list {
  display: grid;
  grid-template-columns: 1fr;
  gap: 0;
  margin: 0;
  padding: 0;
}
.risk-item {
  margin: 0 0 9px;
  color: var(--ink);
  font-size: 14px;
  line-height: 1.72;
  letter-spacing: 0;
  word-spacing: 0;
  text-align: justify;
  text-align-last: left;
  text-justify: inter-character;
}
.two-col {
  display: grid;
  grid-template-columns: 1fr;
  gap: 16px;
  align-items: start;
}
.two-col > div {
  min-width: 0;
}
.tag-row {
  margin: 0 0 10px;
}
.tag {
  display: inline-block;
  padding: 2px 7px;
  border: 1px solid var(--rule);
  background: #f7f4ee;
  color: var(--muted);
  font-size: 12px;
  line-height: 1.45;
  margin: 0 5px 6px 0;
}
.table-wrap {
  overflow-x: auto;
  border: 1px solid var(--rule);
  margin: 8px 0 12px;
}
table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
  font-size: 11px;
  line-height: 1.55;
}
th, td {
  padding: 8px 9px;
  border-bottom: 1px solid var(--rule);
  vertical-align: top;
}
th {
  background: #ece7dd;
  color: #2d2d2d;
  font-size: 11px;
  line-height: 1.45;
  font-weight: 700;
  letter-spacing: .04em;
  text-align: center;
}
td {
  color: var(--ink);
  font-size: 11px;
}
td:first-child {
  text-align: center;
}
td:not(:first-child) {
  text-align: left;
}
td.num {
  text-align: left;
  font-family: var(--sans);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
th.num {
  text-align: center;
  font-family: var(--sans);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
.fund-flow-table th {
  color: #2d2d2d;
  text-align: center;
}
.fund-flow-table .fund-col-category,
.fund-flow-table .fund-col-trend {
  width: 82px;
}
.fund-flow-table .fund-col-meaning {
  width: auto;
}
.fund-flow-table td:nth-child(1),
.fund-flow-table td:nth-child(2),
.fund-flow-table td.num {
  text-align: center;
  white-space: normal;
  word-break: keep-all;
  overflow-wrap: normal;
}
.fund-flow-table td:nth-child(3) {
  text-align: left;
  word-break: normal;
  overflow-wrap: anywhere;
}
.consensus-table th,
.consensus-table td,
.consensus-table td.num,
.consensus-table th.num {
  text-align: center;
}
tr:last-child td { border-bottom: 0; }
.source-note {
  color: var(--muted);
  font-size: 12px;
  line-height: 1.65;
}
.section.source-note h2 {
}
.risk-item:last-child { margin-bottom: 0; }
.section.source-note p {
  color: var(--muted);
  font-size: 12px;
  line-height: 1.65;
  margin-bottom: 8px;
}
.section.source-note p:last-child { margin-bottom: 0; }
.cite-ref {
  vertical-align: super;
  color: var(--accent-2);
  font-size: 10px;
  font-weight: 700;
  line-height: 0;
  text-decoration: none;
  margin-left: 2px;
}
.source-list {
  margin-top: 4px;
}
.source-row {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 18px;
  align-items: baseline;
  padding: 9px 0;
  border-bottom: 1px solid var(--rule);
  color: var(--ink);
  font-size: 12px;
  line-height: 1.65;
}
.source-row:last-child { border-bottom: 0; }
.source-main { min-width: 0; }
.source-index,
.source-name,
.source-title {
  color: var(--ink);
  font-weight: 700;
}
.source-date {
  margin: 0 8px;
  color: var(--muted);
  font-weight: 400;
}
.source-link {
  color: var(--ink);
  font-weight: 700;
  text-decoration: none;
  white-space: nowrap;
}
.source-link:hover { text-decoration: underline; }
```

章节结构与元素使用规则：

- 每个主体章节必须使用 `<section class="section">`，不得新增 `.card`、`.panel`、`.memo`、`.box` 外层。
- 主标题只用一个 `<h2>`，内容必须是完整编号标题，如 `一、今日行情、量能与资金流向`；不得拆成编号和标题两块。
- `<h2>` 下方到第一个正文块或 `.two-col` 的视觉间距由 `h2 margin-bottom: 12px` 控制，不得额外插入空白 div。
- 二级标题只用 `<h3>`，如 `价格与量能`、`资金流向`、`消息面复盘`、`隔夜潜在资讯`；不得使用 `<h2>` 或加粗段落替代。
- `<h3>` 到正文第一段或表格的间距固定为 8px；不得使用内联 style 改 margin。
- 正文段落统一使用 `<p>`，不得在普通正文里使用超大字号、弱灰正文或彩色正文。
- 正文段落必须使用中文报告式两端对齐：CSS 固定 `text-align: justify; text-align-last: left; text-justify: inter-character; letter-spacing: 0; word-spacing: 0;`。最后一行必须左对齐，避免句末被强行拉开。
- 禁止用全角/半角空格、`&nbsp;`、额外 `<br>` 或手动断句凑齐右边界；两端对齐只能由 CSS 完成。
- 两端对齐会让浏览器在行内轻微分配字间距，这是正常中文排版效果；不得额外设置 `letter-spacing` 或 `word-spacing` 放大这种间距。
- 表格只放在 `.table-wrap` 中；资金流向、投行一致预期使用同一套表格 CSS。第六部分不生成操作建议表格。
- 七个主体章节的普通正文必须统一使用 `.section p` 的 `14px / 1.72 / var(--ink)` 口径。第七部分“短期风险提示”不得使用 `<ol>`、`<ul>`、`<li>`、默认编号、小圆点、放大的列表字体或加粗列表标签；必须使用 `<div class="risk-list">` 包裹 3-5 个 `<p class="risk-item">...</p>`。
- `.risk-item` 的字号、行高、颜色、段距必须与第六部分普通正文 `<p>` 完全一致；风险项开头可以写 `资金流出风险：` 这类中文标签，但不得用 `<strong>`、`<b>` 或独立大号标题把标签加粗放大。
- 第二部分标签必须放在 `<p class="tag-row">...</p>` 或等效 `.tag-row` 容器中，标签后再接正文段落。
- “信息来源”使用 `<section class="section source-note" id="sources">`，字号比正文小一档。标题必须是 `信息来源`，不得使用旧标题 `数据与口径说明`。
- 正文中所有重要新闻、公告、产品、财务、研报/预测、产业事件、行业判断和展示数据都必须带上角标引用，格式为 `<a class="cite-ref" href="#source-1">[1]</a>`。不要只在文末泛泛列来源。
- 行情摘要、成交额、换手率、量比、PE TTM、资金流、板块行情、MA、MACD、RSI、压力位、支撑位和投行一致预期等结构化金融数据，只要写入正文、指标卡或表格，就必须有角标，并在“信息来源”列出可打开数据页或原始来源。
- “免责声明”必须紧跟在“信息来源”之后，使用 `<section class="section source-note disclaimer-note">`。标题 `免责声明` 单独一行，样式与“信息来源”的标题完全一致；下方三段 `<p>` 的字体、字号、颜色、行间距、段间距必须与“信息来源”说明段落完全一致。
- 不得使用旧结构 `<footer class="disclaimer">`，不得把“免责声明：”加粗塞进同一段开头，也不得重复生成两个免责声明模块。

禁止：

- 不得把章节主标题设为 28px、32px、40px 等 hero 级字号。
- 不得把二级标题设置为和主标题一样大。
- 不得让“价格与量能”等二级标题紧贴主标题；也不得用大段空白分隔。
- 不得在章节正文中使用内联 `style="font-size:..."`、`style="color:..."` 或随机 class 改变字号颜色。
- 不得让不同章节使用不同的标题字号、段落行距或表格 padding。

### 边框白名单

页面必须是“纸面报告 + 规则线”的投行快报质感，不得把普通正文段落随手做成卡片。

允许带外边框的组件仅限：

- 主报告纸张外框 `.page`。
- 顶部摘要指标矩阵 `.metric-grid` / `.metric`。
- 正式表格容器 `.table-wrap`，例如资金流向、投行一致预期。
- 技术面专用面板 `.tech-panel`、价格带/区间小格 `.level`、`.zone-note-item`。
- 免责声明或页脚的顶部规则线。

禁止带外边框的内容：

- 普通正文 section 不得有独立外框。
- `价格与量能`、`板块分析`、`消息面复盘`、`隔夜观察`、`风险提示`等纯文本块不得使用 card/panel/memo 样式。
- `.two-col` 只负责上下模块排列，不得添加 `border`、卡片背景或厚 padding 使其变成卡片组。
- 不要给“资金流向”整个模块加外框；只有里面的 `.table-wrap` 表格可以有边框。

## 页面结构

### Header

内容：

- eyebrow：`Daily Equity Recap / 每日复盘快报`
- H1：股票简称 + 股票代码。股票代码必须写在简称后面，使用小号弱化文本，与简称之间固定用 18px 左间距；字体仍使用 `var(--sans)`。
- subtitle：一句公司简介，必须包含核心产品/业务、行业地位或产业链位置；不要写成泛泛的赛道描述。
- meta：
  - 生成日期

Header 标题固定写法：

```html
<h1>中际旭创 <span class="stock-code">300308.SZ</span></h1>
<p class="subtitle">800G、1.6T 高速光模块龙头，全球市占率领先，绑定海外头部云厂商，是 AI 算力与光通信产业链核心标的。</p>
```

对应 CSS 必须包含：

```css
.stock-code {
  display: inline-block;
  margin-left: 18px;
  color: var(--faint);
  font-family: var(--sans);
  font-variant-numeric: tabular-nums;
  font-size: 42%;
  font-weight: 700;
  letter-spacing: 0;
  vertical-align: baseline;
}
.subtitle {
  margin: 8px 0 0;
  color: var(--muted);
  max-width: 760px;
}
```

subtitle 内容要求：

- 必须是一句话，控制在 28-60 个汉字左右。
- 必须至少包含两类信息：核心产品/业务、行业地位/市占率/产业链位置、核心客户/需求驱动。
- 不要出现“本文基于用户提供”“数据口径”等说明。

Header 中的 `meta-box` 必须固定放在公司业务/产品简介下方，严格只保留一行生成日期，不允许放到右侧自适应栏，也不允许做成表格或左右分栏键值对。`report-header` 不得使用左右分栏，固定写法：

```html
<div class="meta-box">
  <div><strong>生成日期</strong>：2026-06-11</div>
</div>
```

CSS 必须保证左对齐：

```css
.report-header {
  display: block;
  padding-bottom: 16px;
  border-bottom: 3px solid var(--ink);
}
.meta-box {
  margin-top: 10px;
  min-width: 0;
  color: var(--muted);
  font-size: 12px;
  text-align: left;
}
.meta-box div { margin-bottom: 4px; }
.meta-box strong { font-weight: 700; }
```

禁止：

- 不要写“数据口径：用户提供”。
- 不要加入“证券代码”这一行。
- 不要加入“报告类型”这一行。
- 不要加入“观点口径”这一行。
- 不要将 meta-box 渲染成 `<table>`。
- 不要使用两列 grid/flex 让 `meta-box` 跑到右侧，或让标签在左、数值在右。
- 不要把数值右对齐；生成日期必须左对齐。

### K线模块（当前版本已下线）

当前版本不生成 K线图。无论行情数据是否完整，HTML 中都不得出现 `Price Action / 价格走势`、`近期股价 K 线图`、`今日/1个月/3个月` tabs、`.market-chart-module`、`.chart-tabs`、`.tab-controls`、`.kline-panels`、`.chart-panel`、`window.RECAP_CHART_DATA`、`LightweightCharts`、`KLineCharts`、`CandlestickSeries`、`HistogramSeries` 或任何图表初始化脚本。

当前版本不拉取 30 个交易日日线。摘要指标卡必须直接位于 `.lead` 下方，中间不得插入图表分隔线或空图容器。

### 摘要指标卡

位置：公司一句话简介/开篇判断 `.lead` 下方。

当前版本没有 K线模块，摘要指标卡必须直接位于 `.lead` 下方；`.lead` 与 `.metric-grid` 中间不得插入 K线标题、tabs、图表容器、数据源说明、空白图表或额外分隔线。

8 个指标：

1. 当前价格
2. 涨跌幅
3. 日内区间
4. 总市值
5. 市盈率 TTM
6. 成交额
7. 换手率
8. 量比

每个指标只显示：

```html
<div class="metric">
  <div class="label">当前价格</div>
  <div class="value">1180.00元<a class="cite-ref" href="#source-1">[1]</a></div>
</div>
```

不要第三行 note。单位并入 value。

指标卡下方必须添加时间口径注释：

```html
<p class="metric-note">注：以上行情摘要截至 2026-06-12 13:30（交易日盘中）。</p>
```

固定 CSS：

```css
.metric-note {
  margin: 6px 0 0;
  color: var(--muted);
  font-size: 11px;
  line-height: 1.55;
}
```

要求：

- 注释只说明行情摘要的时间点或收盘口径；来源通过每个指标数值后的上角标进入“信息来源”。
- 对话框核心总结和 HTML 中的生成时间必须使用用户发起请求时间；行情摘要注释使用 `data_as_of`。

摘要指标卡颜色必须固定：

```css
.positive { color: #9b2424; }
.negative { color: #0f6b3f; }
.neutral { color: var(--accent); }
```

HTML class 使用规则：

```html
<!-- 涨跌幅为正 -->
<div class="value positive">+2.17%</div>

<!-- 涨跌幅为负 -->
<div class="value negative">-4.55%</div>

<!-- 日内区间固定深蓝 -->
<div class="value neutral">1126.90-1196.16元</div>

<!-- 其他指标不加颜色 class -->
<div class="value">约1.32万亿人民币</div>
```

资金流向表格同样使用 A 股红涨绿跌语义：

```html
<td class="num positive">+12.6亿元</td>
<td class="num negative">-3.4亿元</td>
```

### 主体章节

章节顺序固定：

1. 今日行情、量能与资金流向
2. 板块联动与个股地位
3. 技术面分析
4. 消息面与隔夜观察
5. 投行一致预期
6. 综合评级
7. 短期风险提示
8. 信息来源
9. 免责声明

## 章节细则

### 一、今日行情、量能与资金流向

使用上下排列，不使用左右两栏：

布局硬规则：

- 外层只使用普通 `<section class="section">`，section 本身只保留顶部细规则线，不得额外添加外边框。
- `.two-col` 只作为上下模块容器，CSS 固定为 `grid-template-columns: 1fr; gap: 16px;`；不得在宽屏时改成 `1fr 1fr`、`repeat(2, ...)` 或 `display: flex` 横排。
- `价格与量能` 必须排在上方，是纯文本块，不得使用 `.memo`、`.tech-panel`、`.level`、`.table-wrap` 或任何自定义 card/panel 类，不得有 `border: 1px solid ...` 外框。
- A 股股票：`资金流向` 必须排在下方，只有资金表格的 `.table-wrap` 可以有边框；不要给“资金流向”标题和整块内容再包一层外框。
- 非 A 股股票：不生成 `资金流向` 二级标题、不生成 `.fund-flow-table`，也不生成“主力资金 / 北向资金 / 大单资金”表格。相关交易线索应合并写入上方 `价格与量能` 文本。

上方模块 `价格与量能`：

- 第一段：价格、涨跌幅、日内区间、价格结构。
- 第二段：成交额、近 5 日均值对比、换手率、量比、缩量/放量判断、反弹或下跌质量。
- 第三段：原因解释。必须尝试说明造成今日价格和量能变化的基本面/行业/宏观/公告/海外映射/板块情绪原因。若有明确原因，写清“事实 -> 对盈利预期/估值/情绪/资金偏好的影响 -> 如何反映到今日价格量能”；若未见明确原因，写明“未见明确基本面催化，盘面更偏交易结构/板块情绪驱动”。

A 股下方模块 `资金流向`：

保留表格：

| 资金类别 | 流向趋势 | 复盘含义 |

HTML 必须写成 `<table class="fund-flow-table">`，用于锁定对齐规则：表头三列全部居中；正文第 1 列“资金类别”居中，第 2 列“流向趋势”居中，第 3 列“复盘含义”左对齐。

资金流向表格必须包含固定 `colgroup`，前两列等宽，第三列自适应：

```html
<table class="fund-flow-table">
  <colgroup>
    <col class="fund-col-category">
    <col class="fund-col-trend">
    <col class="fund-col-meaning">
  </colgroup>
  ...
</table>
```

列宽硬规则：

- 第 1 列 `资金类别` 和第 2 列 `流向趋势` 必须等宽，CSS 固定为 `82px`，刚好容纳四个中文字符和左右内边距。
- 第 3 列 `复盘含义` 使用剩余宽度并自动换行；不得给 `.fund-flow-table` 设置会触发横向拖动的固定 `min-width`。页面窄时优先让复盘含义列换行，而不是让整张表横向滚动。
- 不得使用 `width: auto`、百分比猜测或浏览器默认表格算法来决定前两列宽度。

非 A 股股票的第一部分结构：

```html
<section class="section">
  <h2>一、今日行情、量能与资金流向</h2>
  <div class="two-col">
    <div>
      <h3>价格与量能</h3>
      <p>...在同一段落内说明成交量、换手、相对均量、南向资金/期权/ETF 流向等可核验交易线索；若无可信资金线索，写“未见可核验的异常资金交易信号”。</p>
    </div>
  </div>
</section>
```

非 A 股禁止：

- 不得出现 `<h3>资金流向</h3>`。
- 不得出现 `<table class="fund-flow-table">`。
- 不得出现 `主力资金`、`北向资金`、`大单资金` 三行 A 股专用资金口径。

### 二、板块联动与个股地位

先放标签：

```html
<span class="tag">光模块 +1.23%</span>
<span class="tag">AI 算力 +0.87%</span>
<span class="tag">板块上涨 32 家</span>
<span class="tag">板块下跌 11 家</span>
```

再写一段分析，避免过长。

### 三、技术面分析

使用 `technical-dashboard`，固定上下排列：

- `.technical-dashboard` 必须固定为 `display: grid; grid-template-columns: 1fr; gap: 16px;`，不得在桌面端改成左右两栏。
- `指标状态` 必须在上方，`价格区间带` 必须在下方。

`指标状态` 三行：

- 只能有 MA、MACD、RSI 三行，顺序固定。
- 必须使用固定表格结构 `.tech-indicator-table`，不得使用自由排版。
- 表格固定四列：`指标`、`标签`、`分析`、`判断`。其中“标签、分析、判断”是每个指标块的三项内容。
- `指标` 列只能是 `MA`、`MACD`、`RSI`；`标签` 列写 2-6 个字的状态短语，例如 `跌破短均`、`绿柱收敛`、`中性偏弱`。
- `分析` 列写 1-2 句完整解释，必须面向不懂技术指标的读者说明含义，不能只罗列数字。
- `判断` 列写 2-6 个字的结论短语，例如 `趋势偏弱`、`动能修复`、`未超买`；判断必须留在同一行右侧，不得换到下一行或独立成段。
- `.tech-indicator-row` 必须是四列：`56px 88px minmax(0, 1fr) 76px`。

固定 HTML 模板：

```html
<div class="tech-panel">
  <h3>指标状态</h3>
  <div class="tech-indicator-table" aria-label="技术指标状态">
    <div class="tech-indicator-head">
      <div>指标</div>
      <div>标签</div>
      <div>分析</div>
      <div>判断</div>
    </div>
    <div class="tech-indicator-row">
      <div class="tech-name">MA</div>
      <div class="tech-tag">多头排列</div>
      <div class="tech-analysis">股价重新站上 MA10，且 MA5/MA10/MA20/MA60 仍保持向上排列，说明中期成本线没有被破坏，回调更像趋势内震荡。</div>
      <div class="tech-judge">趋势偏强</div>
    </div>
    <div class="tech-indicator-row">
      <div class="tech-name">MACD</div>
      <div class="tech-tag">绿柱收敛</div>
      <div class="tech-analysis">DIF 与 DEA 的差距缩小，绿柱较前一日缩短，表示短线调整动能边际减弱，但还没有完全转为重新上攻。</div>
      <div class="tech-judge">动能修复</div>
    </div>
    <div class="tech-indicator-row">
      <div class="tech-name">RSI</div>
      <div class="tech-tag">61.6</div>
      <div class="tech-analysis">RSI 回到偏强但未过热的区间，说明买盘恢复但尚未进入极端拥挤状态，短线仍需观察追高资金承接。</div>
      <div class="tech-judge">未超买</div>
    </div>
  </div>
</div>
```

固定 CSS：

```css
.technical-dashboard {
  display: grid;
  grid-template-columns: 1fr;
  gap: 16px;
  margin-bottom: 12px;
}
.tech-indicator-table {
  border: 1px solid var(--rule);
  background: var(--paper);
}
.tech-indicator-head,
.tech-indicator-row {
  display: grid;
  grid-template-columns: 56px 88px minmax(0, 1fr) 76px;
  align-items: center;
}
.tech-indicator-head {
  background: #ece7dd;
  color: #2d2d2d;
  font-size: 11px;
  line-height: 1.45;
  font-weight: 700;
  text-align: center;
}
.tech-indicator-head > div,
.tech-indicator-row > div {
  min-width: 0;
  padding: 8px 9px;
  border-left: 1px solid var(--rule);
  font-size: 11px;
}
.tech-indicator-head > div {
  text-align: center;
}
.tech-indicator-row > div {
  text-align: left;
}
.tech-indicator-head > div:first-child,
.tech-indicator-row > div:first-child {
  border-left: 0;
}
.tech-indicator-row {
  min-height: 58px;
  border-bottom: 1px solid var(--rule);
}
.tech-indicator-row:last-child { border-bottom: 0; }
.tech-indicator-row > div:nth-child(1),
.tech-indicator-row > div:nth-child(2),
.tech-indicator-row > div:nth-child(4) {
  text-align: center;
}
.tech-indicator-row > div:nth-child(3) { text-align: left; }
.tech-name {
  color: var(--accent);
  font-family: var(--sans);
  font-variant-numeric: tabular-nums;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
}
.tech-tag {
  color: var(--ink);
  font-size: 11px;
  font-weight: 700;
}
.tech-analysis {
  color: var(--muted);
  font-size: 11px;
  line-height: 1.65;
}
.tech-judge {
  justify-self: stretch;
  align-self: center;
  background: #f7f4ee;
  color: var(--accent);
  border-left: 1px solid var(--rule);
  font-size: 11px;
  font-weight: 700;
  text-align: center;
  white-space: nowrap;
}
```

禁止：

- 不得使用旧结构 `.tech-signal-grid`、`.tech-signal`、`.tech-copy`、`.tech-read`、`.tech-desc`、`.tech-badge`。
- 不得把判断写成 `<div class="tech-badge-row">趋势偏弱</div>` 或任何独立全宽横条。
- 不得省略 `.tech-indicator-head` 表头，避免列含义不清。
- 不得把三个指标做成普通 `<table>`；必须使用上述 `.tech-indicator-table` 结构。
- 不得只输出数字和一句“较前一日走弱/走强”，必须解释这对趋势和风险意味着什么。

下方模块 `价格区间带`：

- 固定使用单条横向价格轴，不得改成普通表格、饼图、柱状图、SVG 插画、多条分离进度条或自由画布。
- 横向柱体只允许一条 `.zone-track`，高度、颜色、边框固定；图上只绘制震荡区间和当前价，不绘制支撑位/压力位竖线。
- `scale_min` / `scale_max` 只用于计算映射范围，不得作为文字显示在图上。
- `scale_min` / `scale_max` 必须覆盖当前价、震荡区间、压力位、支撑位：先把当前价、震荡区间上下沿、压力位/压力区间上下沿、支撑位/支撑区间上下沿全部解析为数值集合；最小值作为左侧基准，最大值作为右侧基准，再额外留 5%-10% 边距。不得只用震荡区间或当前价决定横轴范围。
- 震荡区间用 `.zone-range.zone-oscillation` 横向色带表示，位置和宽度按区间起止价格计算。
- 震荡区间左边界下方必须显示区间低点，使用 `.zone-edge.zone-low`；右边界下方必须显示区间高点，使用 `.zone-edge.zone-high`。
- 压力位/支撑位不得在图上显示竖线、数字或标签，避免与当前价和震荡区间端点重叠；完整数值只放在下方 `.zone-note`。
- 当前价必须使用 `.zone-current` 红色垂直线标记，只有当前价允许在图上显示文字，文字为 `{价格} 当前价`，文字颜色与竖线同红色。
- 图上只能出现 3 个数据文字：当前价、震荡区间低点、震荡区间高点。不得显示 `scale_min`、`scale_max`、支撑位、压力位或其他数字。
- 震荡区间、压力位、支撑位的完整数值只能写在下方 `.zone-note` 三项中，不得同时写在图上。
- 轴下方三项必须固定从上到下纵向排列，顺序为：震荡区间、压力位、支撑位。不得做成三列横向卡片。
- 每个 `.zone-note-item` 是一行：左侧字段名，右侧数值。
- 所有价格位置必须按百分比计算，不得凭视觉手调。
- 颜色必须固定：`.zone-track` 底层横轴背景 `#ebe6dd`、边框 `#d9d3c8`；`.zone-range.zone-oscillation` 覆盖条背景 `#d1d3d1`、边框 `#9aa0a6`；`.zone-current` 当前价竖线与文字 `#9b2424`；`.zone-edge` 震荡区间两端数字 `#5e625f`。禁止任何 `linear-gradient`、`radial-gradient`、半透明彩色渐变、红绿压力/支撑色带或自定义配色。

数据契约：

```js
const priceZone = {
  scaleMin: 340,
  scaleMax: 530,
  current: { value: 412.30, label: '412.30 当前价' },
  oscillation: { low: 402, high: 446, label: '402-446元' },
  pressure: [{ value: 428, label: '425-430元' }],
  support: [{ value: 402, label: '402元' }, { value: 380, label: '380元' }]
};
```

百分比计算：

```js
function pct(price, scaleMin, scaleMax) {
  return Math.max(0, Math.min(100, (price - scaleMin) / (scaleMax - scaleMin) * 100));
}
```

要求：

- 震荡区间：`left = pct(low)`，`width = pct(high) - pct(low)`。
- 震荡区间低点标签：`left = pct(oscillation.low)`，文本为低点价格。
- 震荡区间高点标签：`left = pct(oscillation.high)`，文本为高点价格。
- 当前价：`left = pct(current.value)`。
- 压力位/支撑位：不得生成图上节点；只在 `.zone-note` 中展示文本。

固定 HTML 模板：

```html
<div class="tech-panel">
  <h3>关键价格区间</h3>
  <div class="price-zone" aria-label="关键价格区间示意">
    <div class="zone-axis">
      <div class="zone-track"></div>
      <div class="zone-range zone-oscillation" style="left: 32.6%; width: 23.2%;" aria-hidden="true"></div>
      <div class="zone-current" style="left: 38.1%;"><span>412.30 当前价</span></div>
      <div class="zone-edge zone-low" style="left: 32.6%;"><span>402</span></div>
      <div class="zone-edge zone-high" style="left: 55.8%;"><span>446</span></div>
    </div>
    <div class="zone-note">
      <div class="zone-note-item">
        <div class="k">震荡区间</div>
        <div class="v">402-446元</div>
      </div>
      <div class="zone-note-item">
        <div class="k">压力位</div>
        <div class="v">425-430元</div>
      </div>
      <div class="zone-note-item">
        <div class="k">支撑位</div>
        <div class="v">402 / 380 / 360元</div>
      </div>
    </div>
  </div>
</div>
```

固定 CSS：

```css
.zone-axis {
  position: relative;
  height: 118px;
  margin: 8px 2px 12px;
}
.zone-track,
.zone-range {
  position: absolute;
  top: 48px;
  height: 16px;
  box-sizing: border-box;
}
.zone-track {
  left: 0;
  right: 0;
  border: 1px solid #d9d3c8;
  background: #ebe6dd;
}
.zone-range {
  border: 1px solid #9aa0a6;
  background: #d1d3d1;
}
.zone-oscillation {
  background: #d1d3d1;
}
.zone-current {
  position: absolute;
  top: 30px;
  height: 52px;
  width: 3px;
  transform: translateX(-1.5px);
  background: #9b2424;
  z-index: 3;
}
.zone-current span {
  position: absolute;
  top: -20px;
  left: 6px;
  min-width: 64px;
  font-family: var(--sans);
  font-variant-numeric: tabular-nums;
  font-size: 12px;
  line-height: 1.2;
  font-weight: 700;
  white-space: nowrap;
  color: #9b2424;
}
.zone-edge {
  position: absolute;
  top: 74px;
  transform: translateX(-50%);
  color: #5e625f;
  font-family: var(--sans);
  font-variant-numeric: tabular-nums;
  font-size: 11px;
  line-height: 1.2;
  font-weight: 700;
}
.zone-edge span {
  white-space: nowrap;
}
.zone-note {
  display: grid;
  grid-template-columns: 1fr;
  gap: 6px;
}
.zone-note-item {
  display: grid;
  grid-template-columns: 96px 1fr;
  align-items: baseline;
  border: 1px solid var(--rule);
  background: var(--paper);
  padding: 8px 9px;
}
.zone-note-item .k {
  color: var(--faint);
  font-size: 11px;
}
.zone-note-item .v {
  font-family: var(--sans);
  font-variant-numeric: tabular-nums;
  font-weight: 700;
  text-align: right;
}
```

支撑/压力格式规则：

- 允许：`425-430元`。
- 允许：`444 / 430 / 425元`。
- 允许：`425元`。
- 禁止：`425-430 / 444-446元`。
- 禁止：`402-403 / 360元`。

价格区间带后必须有一段技术面总结。

### 四、消息面与隔夜观察

固定上下排列：

- 消息面复盘：最近 3 日内重要的基本面/产业面消息。必须来自权威财经媒体、产业媒体、公司公告/IR、交易所/监管披露，内容聚焦公司业务、订单、业绩、产品、客户、产能、行业趋势、政策监管、产业链景气。超过 3 日的旧新闻不得作为主体。
- 隔夜潜在资讯：当天剩余时间和未来几天可能影响业务/股价的事项，包括公司公告窗口、行业会议、客户/供应商财报与资本开支指引、产业链新闻、监管政策、分红/除权/解禁/股东大会等。
- 禁止把成交额超百亿、大宗交易、龙虎榜、主力资金、换手率、量比等纯交易异动重复写在第四部分；这些只能进入第一部分。
- 容器仍使用普通 `.two-col`，但必须上下排列：`消息面复盘` 在上方，`隔夜潜在资讯` 在下方；不得加外边框、卡片背景或额外 panel。二者都是纯文本块，不得使用 `.table-wrap`、`.tech-panel`、`.memo`、`.card`。

文末“信息来源”列出可核查出处。

### 五、投行一致预期

根据市场和可得数据选择一种展示方式，标题固定为 `五、投行一致预期`。

A 股或有完整盈利预测时，使用财务预测表：

| 年份 | 归母净利润 | 营业总收入 | 每股收益 | 市盈率 |

港股、美股或主要披露券商评级/目标价时，使用评级目标价表：

| 机构名称 | 最新评级 | 目标价 | 日期 |

有覆盖数据时，HTML 必须写成 `<table class="consensus-table">`，用于锁定对齐规则：表头和正文全部居中，包括所有 `.num` 数字列。

无可核验投行/券商覆盖时，不生成表格，改用：

```html
<div class="consensus-empty">
  <p>截至本报告生成时，暂未检索到可核验的投行/券商覆盖、评级或目标价记录。</p>
  <p>机会在于...</p>
  <p>风险在于...</p>
</div>
```

`.consensus-empty` 只是语义容器，不得添加边框、卡片背景、阴影或不同字号；其中 `p` 必须继承普通正文样式。

硬规则：

- 两种表格只能二选一，不得混用表头；无覆盖时不出表格。
- 财务预测表适用于 A 股或能取得未来 3 年净利润/收入/EPS/PE 的公司。
- 评级目标价表适用于港股、美股或只取得券商评级/目标价记录的公司，展示最近约 5 家机构。
- 评级目标价表的目标价必须带币种，日期统一写为 `YYYY-MM-DD`。
- 每行关键数据必须带来源角标。
- 禁止为了保留表格而输出全是 `暂无`、`未披露`、公司公告或 IR 的“机构覆盖”表。

### 六、综合评级

评级句：

`综合当日盘面、资金流向、技术形态与市场情绪，综合评级为<strong>...</strong>。`

评级句下方必须紧跟 2-3 段 `<p>` 作为评级说明，每段 60-120 字，解释评级原因。必须包含基本面或行业趋势判断，并结合估值、技术、资金、消息中的 2-3 项；不能只重复行情表现。

禁止生成操作建议表格。第六部分不得出现“空仓者”“持仓者”“短线参与者”“操作建议”“仓位 / 风控”“止损”“止盈”等交易指令型内容。

### 七、短期风险提示

使用无圆点、无序号的段落组，3-5 条，必须有针对性。固定结构如下，禁止使用浏览器默认 `<ul><li>` 小圆点或 `<ol><li>` 序号：

```html
<div class="risk-list">
  <p class="risk-item">资金流出风险：若主力资金继续净流出，短期反弹持续性会被削弱。</p>
  <p class="risk-item">估值风险：若业绩兑现慢于市场预期，高估值可能放大股价回撤。</p>
  <p class="risk-item">行业波动风险：若下游资本开支或行业景气度变化，订单和估值预期可能同步下修。</p>
</div>
```

硬规则：

- 不得使用 `<ol>`、`<ul>`、`<li>`，不得出现浏览器默认编号或小圆点。
- 不得把风险项标签写成 `<strong>资金流出风险：</strong>` 或大号加粗标题；风险项整体必须像普通正文段落一样阅读。
- `.risk-item` 必须继承第六部分正文的视觉口径：14px、line-height 1.72、`var(--ink)`、段间距 9px。
- 风险项可以用“风险名称：说明”的句式，但冒号前后仍是同一字号、同一字体、同一颜色和同一字重。

### 信息来源

文末标题固定为 `信息来源`。本节目的不是泛泛写“数据来自公开信息”，而是让读者能核查正文中的重要事实来源。

正文引用规则：

- 重要新闻、公告、产品、财务、研报/预测、产业事件、行业判断，以及当前价、涨跌幅、成交额、换手率、量比、资金流、板块行情、MA/MACD/RSI、PE TTM、支撑压力和投行一致预期等展示数据，都必须在对应句子、指标值或表格单元格中添加上角标。
- 上角标格式固定：`<a class="cite-ref" href="#source-1">[1]</a>`。
- 同一句如果来自多个来源，可连续写 `<a class="cite-ref" href="#source-1">[1]</a><a class="cite-ref" href="#source-2">[2]</a>`。
- 不要给纯分析判断硬塞来源；但分析判断依赖的事实必须标注来源。

来源列表结构固定：

```html
<section class="section source-note" id="sources">
  <h2>信息来源</h2>
  <div class="source-list">
    <div class="source-row" id="source-1">
      <div class="source-main">
        <span class="source-index">[1]</span>
        <span class="source-name">财联社</span>
        <span class="source-date">12月11日</span>
        <span class="source-title">美联储如期降息25个基点 预计2026年仅降息一次</span>
      </div>
      <a class="source-link" href="https://example.com/source" target="_blank" rel="noopener noreferrer">打开原文</a>
    </div>
  </div>
</section>
```

来源行样式：

- `[1]`、来源名称、标题、`打开原文`：黑色 `var(--ink)`、加粗。
- 日期：`var(--muted)`、正常字重。
- 每条来源一行，行间用 `border-bottom: 1px solid var(--rule)` 分隔；最后一条来源必须用 `.source-row:last-child { border-bottom: 0; }` 去掉底线，避免与下一节顶部规则线形成双线。`.source-list` 本身不加顶部 `border-top`，标题下方不要额外灰色横线。
- `打开原文` 是超链接，必须按截图风格放在每一行最右侧；不得省略，不得改成纯文本，不得放到标题后面。
- “信息来源”只展示引用文章/公告/数据页面/行情页/数据库页的列表，不在来源列表下方追加“说明：……”解释段落。

来源真实性硬规则：

- 不得编造媒体名、标题、日期、URL。
- 正式联网生成的报告必须按真实来源拆分编号：公告、新闻、产业媒体、研报/一致预期、公司/交易所/监管披露、行情页、数据库页等可打开外部来源分别单独成行；不得把多篇文章或多个来源合并成一个 `[1]`。只有在报告确实完全基于单一外部原文时，才允许只有一条来源。
- 当前价、成交额、换手率、量比、资金流、板块行情、技术指标、估值和一致预期等结构化数据必须作为来源行展示；来源行应尽量指向可打开的数据页、行情页、数据库页、公告页或研报页，不要使用无法核验的裸接口。
- 没有真实外部 URL 时，不得写假的“打开原文”链接；不得把内部核验记录、本地 txt、本地材料包或中间文件写成来源行。如确实未取得公开链接，则不要生成该来源行，也不要把该数据写入正文或表格。
- 新闻/公告/研报/公司披露能取得 URL 时，必须填写真实 URL。
- `href="#"`、`javascript:void(0)`、空链接、搜索结果页冒充原文链接均禁止。
- 消息面引用只使用权威财经媒体、产业媒体、公司公告/IR、交易所/监管披露；不得引用股吧、雪球小作文、贴吧等不可靠来源作为事实依据。

### 免责声明

必须紧跟“信息来源”之后单独成节，结构固定如下：

```html
<section class="section source-note disclaimer-note">
  <h2>免责声明</h2>
  <p>以上内容为AI自动生成或AI辅助生成，仅用于信息整理、投研辅助、教育交流或一般性分析参考，不构成对任何金融产品、交易策略或投资行为的推荐、邀约、承诺或保证，也不构成投资、法律、税务、会计等专业意见。</p>
  <p>以上内容可能基于公开信息、历史数据或用户提供材料进行总结、归纳、推演与情景分析，但相关内容可能存在时效性不足、信息缺漏、事实误差、模型偏差或生成性错误，历史数据、历史业绩、回测结果及情景假设均不代表未来表现。</p>
  <p>用户应基于自身风险承受能力、投资目标、财务状况及适用法律法规独立作出判断，必要时咨询持牌专业机构或顾问。任何因依赖以上内容而作出的决策及其后果，由用户自行承担。</p>
</section>
```

禁止使用旧的一段式 `<footer class="disclaimer">`。三段正文的 CSS 必须继承 `.section.source-note p`，即 `12px / 1.65 / var(--muted)`，段间距与“信息来源”一致。

## 分享版

如果用户要求对外分享，可额外生成 `share-report.html`：

- 顶部三句话摘要。
- 按钮 `打开完整报告`，链接到完整报告锚点。
- 下方嵌入同一完整报告。
