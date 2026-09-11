# ECharts Web/PC 内联适配规则

## 读取门与适用范围

本文件只在 system prompt 的 `Device platform` 明确为“电脑端”或“网页端”时读取。

它只规范原生 `echarts` option 在 Web 内联预览中的布局与可读性；不改变输出协议，不用于手机端、移动端或未提供平台的请求。移动端默认遵循 `mode-echarts.md`，只有命中复杂特征时才追加 `echarts-option-spec.md`。

先读取 `mode-echarts.md`，再读取本文件。只有同时命中复杂 callback、自由布局或特殊数据格式时才追加 `echarts-option-spec.md`；`shared-quality.md` 仅用于高风险审计，不是本分支默认依赖。除本文件明确覆盖的画布、字号、间距、图例和 tooltip 规则外，主模式中的安全、数据、图形选择与地图禁用规则仍然有效。

## Web 内联运行环境

- 图表直接在宽度随消息容器变化、高度固定 `420px` 的 iframe 内运行；当前典型内联尺寸约为 `986 × 420`，属于宽屏矮画布。
- ECharts 读取 iframe 的真实宽高并在容器变化时执行 `chart.resize()`。所有百分比 center、radius、grid 和组件位置都按真实的约 986×420 容器重新计算；必须以最终 Web 内联预览为验收基线。
- 宿主负责 HTML 包装、ECharts 初始化、`ResizeObserver`、`chart.resize()` 和 `chart.dispose()`。option 中不得输出 DOM、初始化代码或监听器。
- 图表内容应尽量使用 iframe 的可用区域；标题、图例、grid、dataZoom、visualMap 与 tooltip 只预留必要空间，不得为了“安全区域”额外缩小绘图区，也不得依赖滚动才能完整查看。
- `option.media` 不得用于判断手机/桌面设备；如确有多个 Web 宽度边界，可用于同一 Web/PC 分支内部的宽度适配，但默认优先生成单一、稳定的扁平画布布局。

## 输出契约与安全

- 代码块语言必须为小写 `echarts`，option 必须直接以 `{` 开始。
- 只输出自包含的完整 option；不得输出 `const option =`、`echarts.init`、`setOption`、HTML、CSS、CDN、DOM 或 renderer 包裹。
- 不得访问 `window`、`document`、`fetch`、`XMLHttpRequest`、`WebSocket`、`eval`、`Function`、动态 import 或 IIFE。
- 保留 `mode-echarts.md` 的 ES5 callback、事实核验、数据来源和地图禁用要求；只有已经按条件加载 `echarts-option-spec.md` 时，才叠加其中的专项细则。

## Web 设计 token

Web/PC 分支直接按真实 iframe CSS 像素设置文字、线宽和图例图标，不做缩放补偿。下列值只覆盖电脑端/网页端，不得套用到移动端。

| 元素 | Web/PC 设计值 |
| --- | ---: |
| 主标题 | 14–16px |
| 副标题 | 10–11px |
| 图例与坐标轴标签 | 10–12px |
| 坐标轴名称 | 10–12px |
| Tooltip 文字 | 10–11px |
| 普通数据标签 | 10–12px |
| 折线宽度 | 2px |
| 数据点大小 | 6–8px |
| 图例图标宽度 | 12–16px |

不得为了信息密度继续降低该基线字号；空间不足时改用缩写、采样、滚动图例、dataZoom、拆图或更合适的图形。

## 布局规则

### 直角坐标图

沿用既有 ECharts 的自适应 `grid` 规则；不引入 Web/PC 专属的大数值 `left`、`right`、`top`、`bottom` 基线。

- 绘图区应尽量铺满 iframe 的可用区域；只为标题、图例、坐标轴标签和交互组件留出实际需要的空间。
- 不得因 Web/PC 分支额外增加外边距、卡片内边距或“安全区域”。
- 图例换行或使用 scroll 时，才相应增加 `grid.top`。
- dataZoom、visualMap、xAxis label 与单位名位于底部时，才增加 `grid.bottom` 并分层放置。
- 双 Y 轴或特别长的轴标签时，才增加必要左右边距；轴名过长时优先缩短或移入副标题/tooltip。
- 多 grid 仅在信息确有分区价值时使用；各 grid 左右边界对齐，避免缩小后难以分辨。
- 多 grid 时，仅最底部 grid 显示 xAxis label；上方 grid 隐藏 xAxis label，并在相邻 grid 之间保留足够间距。

### 标题、图例与信息密度

- 主标题优先单行且简短；来源或长说明放在图表外的 Markdown 正文。
- 在 420px 高度内先划分纵向区间：仅主标题时绘图区通常从约 `48px` 后开始；主标题 + subtext 时从约 `68px` 后开始；再有单行 legend / breadcrumb 时从约 `90px` 后开始。按实际行高调整，不照抄固定 top。
- title、subtext、legend、breadcrumb、toolbox 和顶部横向 visualMap 不得使用同一纵向区域；标题含 subtext 时必须预留完整副标题行，再按实际行数为其余表头组件逐层留位。
- `series.top`、`grid.top`、`radar.center` 或其他绘图区起点必须位于最下方表头组件之后；不得因图例、breadcrumb 或副标题存在而沿用无表头时的坐标。
- 当主标题、副标题与图形无法在 iframe 内同时完整容纳，或副标题会明显压缩绘图区时：保留简短主标题，移除图内 `subtext`，将完整说明、时间范围和数据来源写在 ECharts 代码块外的 Markdown。不得缩小关键文字、让标题换行挤压图形，或让图形覆盖表头。
- 多系列必须配置 legend；超过 4 个系列优先 `legend.type: 'scroll'`。
- 折线和柱状图默认不超过 4–6 个系列；超过 6 个时优先拆图或改用更合适的表达。
- X 轴标签超过约 12–16 个时使用采样、缩写或 dataZoom；长类目优先横向柱图。
- 横向排行默认展示 Top 10–15；双轴图最多两个 Y 轴。
- 饼图/环图默认不超过 6 个分类；更多分类改为横向柱图。
- 不同时堆叠多行标题、多行图例、双轴和底部 dataZoom。

### 强制防重叠与裁切

将移动端已有的“无重叠、无裁切”要求同样用于 Web/PC。输出前必须检查初始状态、展开/下钻状态和关键交互状态；文字之间、文字与图形、文字与组件之间均不得覆盖。

- 类目轴标签密集时使用 `axisLabel.hideOverlap: true`，并配合 `interval`、`rotate`、缩写、采样或 dataZoom；长日期优先缩短格式。不得让完整标签彼此压住。
- 数据标签、散点标签、关系图标签等密集文字在组件支持时使用 `labelLayout: { hideOverlap: true }` 或 `moveOverlap`；仍无足够空间时，隐藏次要标签并在 tooltip 中提供完整信息。
- 需要显示长文字时设置合理 `width`、`overflow: 'truncate'` 或 `'break'` 与 `lineHeight`；不得溢出画布、色块或节点背景。不能通过缩小到不可读来保留全部文字。
- `visualMap`、dataZoom、xAxis label、xAxis name、底部 legend 和数值标签必须分层摆放。组件确实位于底部时，增加必要的 `grid.bottom`、`axisLabel.margin` 或组件间距；必要时移至顶部。
- 直角坐标图使用 `containLabel: true`，但不得把它当作标题、轴名或多组件碰撞的唯一解决办法；长轴名应缩短、移入副标题或 tooltip。
- 对 treemap、tree、sankey、funnel、graph 等自由布局图，`series.top` 必须位于表头之后。节点/色块不足以容纳“名称 + 数值”两行时，优先仅保留一个关键字段或隐藏该标签，通过 tooltip、breadcrumb 或下钻呈现详情。
- 对 radar，图例必须与顶部 indicator 名称分层；依据表头后的区域重新计算 `center` 和 `radius`，并校验 indicator、数值标签和图例没有碰撞。

### 图形专属空间规则

- `parallel` 必须单独为 title、legend 和全部 `parallelAxis.name` 预留表头空间；不得复用直角坐标图的 `grid.top` 经验值。
- heatmap 的 `visualMap` 必须与 grid 分区：底部横向色带、右侧竖向色带均不得覆盖最后一行或最后一列数据。按实际组件尺寸增加 `grid.bottom` 或 `grid.right`，不照抄移动端数值。
- pie / donut 使用外置标签时，使用边缘对齐、短引导线、有限 `width` 以及 `overflow: 'truncate'` 或 `'break'`；少量关键分类不能只依赖 `hideOverlap` 静默隐藏，空间不足时改为图例、tooltip 或拆图。
- Tree 必须分别配置普通节点 `label` 与叶节点 `leaves.label`。LR/RL 方向只在叶标签所在侧预留必要边距；节点过多或层级过深时降低 `initialTreeDepth`、缩短展示名，并用 tooltip 或点击展开显示详情。
- Web/PC Treemap 默认显式设置 `breadcrumb: { show: false }`，不得在图形下方生成路径按钮。作为完整总览展示时同时设置 `nodeClick: false`，避免隐藏返回路径后仍允许进入无法方便返回的子层级；仅当用户明确要求下钻导航时，才允许启用 breadcrumb 和相应点击行为。
- Graph 仅在节点少且布局可控时使用 `layout: 'none'`。固定坐标前必须逐个校验节点、label 和连线的整体包围盒；首帧、展开后和关键交互状态均不得裁切或拥挤。
- 所有自由布局图的外置标签必须设置 `width` 与 `overflow: 'break'` / `'breakAll'` 或 `'truncate'`；只在标签所在侧预留必要边距，禁止为未出现的标签扩大整张图的留白。

### 气泡散点图

- 用 `symbolSize` 映射第三指标时，气泡直径必须设置可辨识的最小值和不遮挡主要趋势的最大值；不能让极端值把其他气泡完全盖住。
- 气泡重叠时使用半透明填充与清晰描边；默认不在每个气泡上显示文字，使用 tooltip 呈现名称和三项数值。只有关键点、异常点或用户指定点才显示短 label，并用 `labelLayout` 避让。
- 当重叠仍无法区分时，优先按类别拆分、筛选 Top N、聚合或改用普通 scatter；不得靠继续缩小气泡或堆叠全量标签解决。

### 箱线图

- 箱线图必须在 tooltip 或正文明确统计口径：五数概括（最小值、Q1、中位数、Q3、最大值）及离群值是否显示、如何定义。
- 分组类目较长时优先横向箱线图；分组过多时只展示 Top N / 关键组、使用 dataZoom 或拆图，避免箱体和类目标签挤压。
- 离群点使用小尺寸、半透明样式；点密集时不为每个离群点写 label，完整数值交由 tooltip。不得让离群点遮住箱体、中位线或相邻组。

### 漏斗图

- 阶段标签优先显示在漏斗内部；内部空间不足时才使用外置标签，并设置有限宽度、截断或换行及短引导线。不得让两侧标签互相覆盖。
- 默认不超过 5–7 个阶段；更多阶段先合并相邻小阶段、拆为两张漏斗或改用阶段表/横向条形图。
- 转化率必须明确口径：相邻阶段转化率或相对首阶段转化率只能择一作为主展示，并在 tooltip 或副标题说明；不能把两种百分比混在同一 label 中。

### 柱线组合图

- 每个 series 必须显式绑定正确的 `yAxisIndex`；柱、线与左右轴的单位、格式、小数位和轴名必须一致可辨。不同量纲必须使用双轴，不得把不可直接比较的数值放同一轴。
- 双轴最多两个；轴范围不得为了制造趋势相似而任意截断或过度拉伸。若两个指标本质不同且易造成误读，优先拆图。
- 默认柱承担绝对量、线承担比率或趋势；line 的 label 只保留关键点或末点，避免与柱顶数值、legend 或另一条线重叠。

### 放不下时的降级策略

“所有文字都同时显示”不是强制目标；可读性优先。任何图表在约 986×420 的最终内联预览中仍无法让文字、扇区、节点或组件互不重叠时，必须按以下顺序降级，不得继续缩小字号或硬塞。

1. 缩短展示名、减少小数、使用缩写；完整文本放入 tooltip、legend、breadcrumb 或图表外 Markdown。
2. 隐藏次要数据标签，保留关键类别、Top N 或当前交互路径；使用 click / 下钻 / dataZoom 查看其余内容。
3. 聚合低值或相近类别为“其他”，并在 tooltip 或正文说明聚合口径。
4. 拆成多张图，或改用更适合逐项阅读的图形。

- Sunburst、treemap 等层级图不得在狭窄外圈或小色块中强行展示全量“名称 + 数值”。叶节点较多或名称较长时，扇区仅显示短名，完整说明、长别名和来源通过 tooltip、breadcrumb、下钻或点击展开查看。
- Sunburst 输出前必须计算数据的最大可见深度，并为每一个可见深度显式配置对应的 `levels[n].label`。存在显式数据根节点时，`levels[0]` 留给 ECharts 虚拟根，`levels[1]` 起依次对应数据根、一级节点直到最深叶节点；不得漏配最外层，使其回退到全局默认字号、旋转或描边。
- 每层 `label` 必须按该层环宽和扇区角度分别配置 `rotate`、`fontSize` 以及溢出策略。所有可见文字的完整包围盒必须位于自身扇区内；长名使用短展示名、有限 `width` 与 `overflow: 'truncate'`，小扇区结合 `label.minAngle` 和 `labelLayout.hideOverlap` 隐藏首屏标签，完整名称放入 tooltip / 下钻。不得让文字跨入相邻扇区或越出圆环边界。
- Sunburst 有 title 或 subtext 时，必须将表头与圆环彻底分区：title/subtext 只占顶部表头区；根据表头实际底边，将 `series.center[1]` 下移并调整 `radius`，使圆环外边界从表头之后开始。标题、副标题不得覆盖圆环、外圈标签或引导线。
- 对约 986×420 的 Web 内联画布，带标题和副标题的 Sunburst 优先使用像素纵向布局，例如 `title.top: 12`、`series.center: ['50%', 240]`、`radius: 155`，使圆环外边界约在 `85–90px` 之后、底边不超过约 `405px`。按实际表头和标签调整，但必须同时满足“表头不重叠”和“主体不过小”；不要用未经最终预览验证的大百分比 radius。
- Sunburst 叶名优先控制在 2–4 个汉字或一个简短词组。若短叶名仍会重叠，优先增加圆环可用区域、调整旋转方向或将完整文字交给 tooltip / 下钻；不得让标题与圆环重叠，也不得把长说明写入扇区。

### Tooltip 与图形细节

电脑端/网页端使用：

```js
tooltip: {
  trigger: 'axis',
  triggerOn: 'mousemove|click',
  renderMode: 'richText',
  confine: true
}
```

- 饼图、漏斗、树图和桑基图等非坐标轴图可使用 `trigger: 'item'`，但保留 `mousemove|click`、`richText` 与 `confine`。
- click 必须保留，核心结论不得只依赖 hover。
- tooltip 使用本文件 token；默认 tooltip 可读时不写 formatter。
- legend、轴标签、label、symbol 与连线均使用本文件 token；避免细线、小点和浅色小字。

### 自由布局图

- tree、treemap、sunburst、sankey、funnel 和 graph 必须从标题、图例之后开始布局。
- 外置 label 使用可读宽度和安全边距；空间不足时减少首屏密度、缩短文字或改布局方向，不缩小到不可读。
- pie、radar、gauge 等中心布局图根据表头后的剩余区域设置 `center` 与 `radius`，不要按整个 420px 高度机械居中。
- 没有外置标签、图例或辅助组件占位时，优先放大中心图主体，避免在四周留下大片无信息空白；不得沿用移动端的保守半径。
- gauge 默认以剩余区域的视觉高度为基准：将 `center` 下移到标题/副标题之后，并将 `radius` 调整到弧线接近左右可用边界；仅在刻度、外置数值或详情标签会碰撞时缩小。不得为未出现的内容预留空白。
- gauge 有 title 或 subtext 时，标题区必须与包含 `axisLabel` 的完整仪表盘外接区域分离；不能只避开圆弧，还要避开顶部刻度数字。对约 986×420 Web 内联画布，可从 `title.top: 12`、`series.center: ['50%', 255]`、`radius: 160` 开始，再按表头、起止角度和底部刻度范围调整；优先使用像素纵向位置，避免百分比 radius 在扁平画布中侵入标题区。
- gauge 必须把 `axisLabel` 纳入图形碰撞检查：任一刻度文字的完整包围盒不得与 `axisLine`、`progress`、`axisTick`、`splitLine`、`pointer`、`anchor` 或 `detail` 相交；尤其逐项检查顶部刻度、两端刻度以及 `0 / 50 / 100` 等关键文字。文字压在彩色进度弧、背景弧或刻度线上均视为不合格。
- gauge 不使用固定的 `axisLabel.distance` 基线。先确定 `radius`、`axisLine.lineStyle.width`、`axisTick.length` 和 `splitLine.length`，再调整 `axisLabel.distance`，使刻度文字整体落在圆弧内侧的空白区，或完整落在圆弧与刻度外侧，并与相邻图形保留清晰间隔。若空间不足，依次调整文字位置、减少 `splitNumber`、缩短 formatter、减小弧线宽度或调整 `center/radius`；不得通过把文字叠在弧带上或缩小到不可读来解决。
- 单指标完成率/进度型 gauge 默认使用进度弧和中央 `detail`，`pointer.show: false`；进度弧已能表达数值时，不要额外绘制会穿过文字的指针。
- 用户明确要求指针时，必须将 `detail`、单位和说明移出指针扫过的中心区域（例如下移至仪表盘下半部），并在初始值、最小值、最大值和常见中间值下检查指针不与任何文字重叠。无法同时保证时，保留指针并将数值移至图表下方，或改为无指针的进度环。

## 全屏边界

Web 内联与全屏可能使用不同的实际容器尺寸。第一阶段 option 以约 986×420 的 Web 内联预览可读为主；全屏只做回归验证，不在未核验实际画布尺寸前写死全屏专属 token 或使用 media 覆盖。

## 交付前检查

- 是否因 system prompt 为电脑端/网页端而读取了本文件？若不是，不得使用本文件规则。
- 在实际 Web 内联预览中，标题、图例、轴标签和 tooltip 是否仍可读？
- 标题、legend、grid、dataZoom、visualMap 是否有重叠或裁切？
- 是否逐项检查了 title/subtext/legend/breadcrumb/toolbox/visualMap、轴名/轴标签、数据标签与图形之间的重叠？密集文字是否已采用隐藏、截断、换行、采样或交互降级？
- Web/PC Treemap 是否默认关闭了底部 breadcrumb；若启用，是否确实来自用户明确要求的下钻导航？
- gauge 的顶部、两端和关键 `axisLabel` 是否完整避开进度弧、背景弧、刻度线、指针与中央 detail？
- 是否仍严格输出小写 `echarts` 的完整 option？
- 是否误改了移动端规则或将 Web token 用于移动端？
