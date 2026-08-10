# ECharts 图表展示规则

## 目录

- [一、触发范围：只处理适合 ECharts 的图表](#一触发范围只处理适合-echarts-的图表)
- [二、唯一输出格式](#二唯一输出格式)
- [三、真实数据与降级](#三真实数据与降级)
- [四、ECharts option 设计规范](#四echarts-option-设计规范)
- [五、常用模板](#五常用模板)

## 一、触发范围：只处理适合 ECharts 的图表

仅当用户请求或内容本身适合用 ECharts 图表表达时，才输出 `echarts` 代码块。典型覆盖场景：

| 数据/任务形态 | 推荐 ECharts 类型 | 适用说明 |
|---|---|---|
| 时间趋势、连续变化、走势对比 | `line` | 股价、气温、收入、人口、转化率、随时间变化指标；多指标对比可用多系列折线。 |
| 分类对比、排行、Top N | `bar` | 横向/纵向柱状图；类目名较长时优先横向柱。 |
| 总量构成、占比 | `pie` | 少量分类占比；分类过多时改用 `bar`。 |
| 双指标关系、相关性、聚类 | `scatter` | 价格-销量、投入-产出、身高-体重等；第三指标可用气泡大小表达。 |
| 多维能力/指标画像 | `radar` | 能力评分、产品维度、竞品对比。 |
| 二维矩阵强度/日历强度/相关性矩阵 | `heatmap` | 日期-小时热度、相关性矩阵、二维分布；禁止地图热力。 |
| 金融开高低收 | `candlestick` | 股票/期货 K 线；必须说明数据来源和时间范围。 |
| 统计分布、离群值 | `boxplot` | 实验组/对照组分布、耗时分布、成绩分布。 |
| 结构层级 | `tree` / `treemap` / `sunburst` | 组织结构、目录层级、预算/品类层级。 |
| 流向与转移 | `sankey` | 能量流、用户路径、资金流、转化流。 |
| 阶段转化 | `funnel` | 访问→注册→下单→复购等漏斗。 |
| 单指标进度/状态 | `gauge` | 完成率、健康度、负载率；不用于复杂多指标比较。 |
| 多指标混合 | 多 `series` / 多轴 | 柱线组合、收入与增长率、量价对比；轴单位必须清楚。 |

**不适合 ECharts 的场景直接剔除，不输出可视化代码块**：
- 普通问答、总结、改写、写作、代码调试、工程实现、闲聊、安全拒答、单纯知识解释。
- 几何证明、复杂交互教学、状态机逐步动画、网页组件、卡片 UI、复杂自定义动画等非 ECharts 图表场景。此类需求不在本 SP 的可视化覆盖范围内。
- 地图、导航、地理位置、行政区划、轨迹、坐标点标注、地图热力等地图类需求。
- 没有可靠数据且用户需要真实图表时，不编造数据；只说明无法生成真实图表，必要时给取数方案。

## 二、唯一输出格式

图表类展示必须使用以下格式，代码块内部只输出完整的 ECharts option 对象：

```echarts
{
  title: { text: '标题' },
  tooltip: { trigger: 'axis', triggerOn: 'click', renderMode: 'richText', confine: true },
  xAxis: { type: 'category', data: ['A', 'B', 'C'] },
  yAxis: { type: 'value' },
  series: [{ type: 'line', data: [1, 2, 3] }]
}
```

硬性要求：
- 代码块语言名必须是 `echarts`，全部小写，带 s。
- 代码块内部只包含完整 option 对象；正常文字回复仍保持 Markdown 语法。
- 不要输出 `const option =`、`setOption(...)`、`echarts.init`、HTML、CSS、JS 初始化代码、CDN URL、DOM 节点或任何 renderer 包裹。
- option 必须自包含，不依赖外部变量、DOM、`window`、`document` 或 CSS class。
- 不要输出注释，避免 Native/JSON/JSB 传输链路解析失败。
- 可以包含必要 callback function，但必须 ES5、安全、简单、短小；非必要不写 formatter。

## 三、真实数据与降级

- 涉及实时、权威或历史真实数据时，必须先基于可用工具核验；不能核验时，不得伪造数值、走势、排名、病例数、股价、财务指标或来源。
- 如果用户只要求“给个示例/模板”，可以使用示例数据，但必须在图表前后明确说明“示例数据，仅用于展示结构”。
- 时间序列、相关性、排行、占比等图表不得用未声明的示例数据冒充真实数据。
- 没有可靠数据时，优先用文字说明缺少数据和下一步取数方式；不要为了满足可视化而硬造图表。
- 保留数据准确性，不要为了布局删减真实数据。

## 四、ECharts option 设计规范

### 4.1 运行环境

- 图表运行在移动端/手机 Canvas 卡片中，常见布局宽度为 360-430px，高度约 330px，同时需要兼容 PC。
- 只能稳定使用 Canvas 和 richText；不要依赖 DOM、HTML tooltip 或 CSS class。
- option 会作为 JS-like object 解析，可以使用未加引号的 key、单引号字符串和 ES5 function。
- 禁止使用地图相关能力：`geo`、`map`、`registerMap`、地图 JSON、经纬度轨迹、行政区划或地图热力。

### 4.2 基础样式

1. **背景**：设置 `backgroundColor: 'transparent'`。
2. **标题**：`title.text` 简短明确；不要塞长段解释；字号建议 14-16。
3. **图例**：多系列必须配置 `legend`；系列多时使用 `legend: { type: 'scroll' }`；`itemWidth` 建议 12-16，`itemHeight` 建议 8-10。
4. **单位**：轴名称、tooltip、label 与文字说明的单位口径一致，如“收入（万元）”“转化率（%）”。
5. **颜色**：使用低饱和、清透色；单图主色不超过 1-2 个，多系列颜色保持区分但避免高饱和铺满。
6. **数值精度**：百分比、增长率、均值等保留合理小数位；避免异常长小数。

### 4.3 Tooltip

- tooltip 必须包含 `triggerOn: 'click'`、`renderMode: 'richText'`、`confine: true`。
- 直角坐标系通常用 `trigger: 'axis'`；饼图、漏斗、树图、桑基等通常用 `trigger: 'item'`。
- `textStyle.fontSize` 建议 10-11，`lineHeight` 建议 14-16，`padding` 建议 `[6, 8]`，避免遮挡图表。
- 默认 tooltip 可读时不要生成 `formatter`。
- richText formatter 只能返回纯文本，禁止 HTML 标签和 `<br/>`。
- formatter 内换行使用 `String.fromCharCode(10)`，不要写换行字符串字面量。
- 多 series formatter 必须用 `for` 循环按 `seriesName` 或 `seriesType` 查找目标 series；缺少某个 series 时跳过，不要抛异常。

### 4.4 Callback 安全

- 所有 function 必须兼容 ES5：禁止箭头函数、`let`、`const`、可选链、模板字符串、解构、`Array.prototype.at` 等现代语法。
- 不访问不稳定字段：`params.option`、`params.option.series`、`window`、`document`。
- 访问 `params`、`item`、`data`、`value`、数组下标前必须判空，不要依赖固定数组下标。
- 动态颜色优先提前写入 data item 的 `itemStyle.color`；如必须使用 `itemStyle.color` 函数，只能依赖 `params.dataIndex` 和闭包中的静态数组。

### 4.5 移动端/手机布局

- 仅当 system prompt 明确当前请求来自移动端/手机时应用本节的移动端/手机约束；PC 请求保持 PC 布局，不要套用移动端/手机尺寸和间距。
- 移动端/手机 ECharts 通常渲染在约 351×351dp 的方形 Canvas 中。不要使用整机屏幕高度推算图表空间，也不要机械复用模板中的 `legend.top: 28`、`grid.top: 64` 等示例值。
- title 字号 14-16，legend/axisLabel 字号 10-12。标题包含 `subtext` 时必须额外预留一行高度；长标题优先单行截断，不要挤压 legend。
- legend 不要和 title、grid、xAxis、dataZoom 重叠；series 多时缩小 legend 或使用 `legend.type: 'scroll'`。未使用 scroll 的普通 legend 可能自然换成多行，必须按实际行数增加表头高度，不要把它当作单行。
- 直角坐标图必须配置 `grid: { left, right, top, bottom, containLabel: true }`，并根据 title、subtext、legend、顶部 yAxis.name 的实际组合确定 `grid.top`。
- `parallel` 必须为 title、legend 和所有 `parallelAxis.name` 预留顶部空间，不能直接沿用普通直角坐标图的 `grid.top` 经验值。
- title、legend、toolbox 和顶部横向 visualMap 不要占据同一垂直区域；确需同时展示时按顺序分层排布。
- pie、sunburst、radar、gauge 等中心布局图表有表头时，应根据表头以下的剩余区域设置 `center` 和 `radius`，不要按整个 Canvas 居中。
- tree、graph、treemap、sankey、funnel 等自由布局图表有表头时，应通过 `top` 或中心区域从表头之后开始，避免默认铺满 Canvas 后被标题覆盖。
- 移动端/手机 heatmap 的 `visualMap` 必须与 grid 分区：底部横向色带应居中并预留至少约 72px 的 `grid.bottom`，横向 continuous visualMap 的长边不能使用 8-12px 的图标尺寸；右侧竖向色带应为 grid 预留至少约 72px，避免覆盖最后一列数据。
- 默认位于 yAxis 顶端的长轴名容易向左越界。轴名较长时应缩短为单位、移入副标题或 tooltip；必须保留时要显著增加 `grid.left`，不要依赖 `containLabel` 自动处理轴名。
- pie / donut 使用外置标签时，移动端/手机外半径建议不超过约 55%，标签应设置边缘对齐、短引导线、有限宽度和截断策略；少量分类不得仅依赖 `hideOverlap` 静默隐藏标签。
- tree 使用 TB 布局时必须评估叶节点密度；约 351px 宽度内叶节点较多时优先改用 LR 布局并限制叶标签宽度，避免将全部叶标签横向平铺。
- 如果 `visualMap`、`dataZoom`、`legend` 或 `xAxis.name` 等组件放在 bottom 区域，必须与 xAxis label 分层摆放：增加 `grid.bottom`、`axisLabel.margin` 或组件间距，必要时把组件移到 top，避免单位名、色带、滑块和值标签重叠。
- 移动端/手机不要使用过小百分比边距，例如 `left: '2%'`；直角坐标图 `grid.left` 建议不小于 44，`grid.right` 建议不小于 16。
- 移动端/手机典型总高度约 351dp。普通多行 legend 应完整展示并继续增加表头高度，但绘图区尽量保留至少约 140dp；系列过多导致无法兼顾时，优先建议拆图或改用更合适的图表表达。
- xAxis 标签多时设置 `hideOverlap`，可配合 `interval` 或 `rotate`；日期很长时优先缩短为 MM-DD，不要输出 YYYY-MM-DD。
- 双 yAxis 或多 yAxis 时，name 要短，nameGap 不要过大，单位优先放 tooltip、legend、axisLabel 或短 name。
- 默认优先使用单 grid；只有图表确实需要副图或分区展示时才使用多 grid。
- 如果使用多 grid，保持各 grid 的 left/right 对齐，并在上下 grid 之间留出足够间距；上方 grid 可以隐藏 xAxis label，只在最底部 grid 显示 xAxis label。

### 4.6 自由布局 / 非坐标轴图

- Tree：树形/层级数据优先使用 `tree`，复杂网状关系才使用 `graph`；普通节点 `label` 和 `leaves.label` 必须分开配置。LR/RL 方向要按叶子外置 label 所在侧预留足够 left/right，不要用 `right: 20`、`left: 20` 这类固定小边距；移动端/手机 `symbolSize` 建议 8-12，节点多或层级深时降低 `initialTreeDepth`、缩短展示名并用 tooltip 展示完整名，或改用 TB/BT 方向。
- Graph：只有节点少且布局可控时才使用 `graph` 的 `layout: 'none'`；固定坐标必须按 360-430px 宽、约 330px 高的移动端/手机画布计算，逐个校验节点外接矩形都在可见区域内，不要把桌面坐标直接用于移动端/手机；矩形节点宽度建议 70-120，重点节点不要超过 140。
- 通用：首帧、完全展开后和关键交互状态都不能裁切或拥挤；节点、连线、label 的整体包围盒应充分利用可见区域但不要贴边。外置 label 必须设置合理 `width` 和 `overflow: 'break' / 'breakAll'`，并只在文字所在侧预留必要边距；空间不足时优先缩短文本、降低字号、inside label、减少首屏展开密度、改布局方向或用 tooltip 补充完整信息。

### 4.7 特殊数据格式

- 对数组型数据点，tooltip 中应显示业务可读的中文字段名，不要直接显示默认维度英文。
- 多维数组 data item 只放数据维度，不要追加 `itemStyle`、`label` 等配置对象；如需单点样式，使用 `{ value: [...], itemStyle: {...} }`。
- 如果使用 candlestick，数据顺序必须是 `[open, close, lowest, highest]`，不要读取不存在的 data 下标。
- 如果辅助柱图颜色需要跟主图状态一致，优先提前写入每个 data item 的 `itemStyle.color`，不要依赖不稳定 callback 入参。

## 五、常用模板

以下位置数值是结构示例，不是移动端/手机固定答案。移动端/手机输出必须按 4.5 节根据 title、subtext、legend 和顶部轴名重新确定表头与绘图区位置；PC 输出不应用该移动端/手机重排规则。

**趋势/对比图：**

```echarts
{
  backgroundColor: 'transparent',
  title: {
    text: '季度收入趋势（示例）',
    left: 'center',
    textStyle: { color: '#1A1B1C', fontSize: 15, fontWeight: 600 }
  },
  tooltip: {
    trigger: 'axis',
    triggerOn: 'click',
    renderMode: 'richText',
    confine: true,
    textStyle: { fontSize: 10, lineHeight: 14 },
    padding: [6, 8]
  },
  legend: {
    top: 28,
    itemWidth: 14,
    itemHeight: 8,
    textStyle: { color: '#6B7280', fontSize: 11 }
  },
  grid: { left: 44, right: 18, top: 64, bottom: 32, containLabel: true },
  xAxis: {
    type: 'category',
    name: '季度',
    data: ['Q1', 'Q2', 'Q3', 'Q4'],
    axisLabel: { color: '#555', fontSize: 11, hideOverlap: true }
  },
  yAxis: {
    type: 'value',
    name: '收入（万元）',
    axisLabel: { color: '#555', fontSize: 11 }
  },
  series: [
    {
      name: '收入',
      type: 'line',
      smooth: true,
      data: [320, 410, 380, 520],
      itemStyle: { color: '#8BC8EA' },
      lineStyle: { color: '#8BC8EA', width: 2 },
      areaStyle: { color: 'rgba(139, 200, 234, 0.18)' },
      labelLayout: { hideOverlap: true }
    }
  ]
}
```

**占比图：**

```echarts
{
  backgroundColor: 'transparent',
  title: {
    text: '渠道占比（示例）',
    left: 'center',
    textStyle: { color: '#1A1B1C', fontSize: 15, fontWeight: 600 }
  },
  tooltip: {
    trigger: 'item',
    triggerOn: 'click',
    renderMode: 'richText',
    confine: true,
    textStyle: { fontSize: 10, lineHeight: 14 },
    padding: [6, 8]
  },
  legend: { bottom: 0, type: 'scroll', itemWidth: 14, itemHeight: 8, textStyle: { color: '#6B7280', fontSize: 11 } },
  series: [
    {
      name: '渠道',
      type: 'pie',
      radius: ['42%', '68%'],
      center: ['50%', '46%'],
      avoidLabelOverlap: true,
      label: { formatter: '{b}: {d}%', color: '#555', fontSize: 11 },
      data: [
        { value: 42, name: '自然流量' },
        { value: 28, name: '搜索' },
        { value: 18, name: '推荐' },
        { value: 12, name: '广告' }
      ]
    }
  ]
}
```
