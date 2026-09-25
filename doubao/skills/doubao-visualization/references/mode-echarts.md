# ECharts 精确数据图表

本文件是常规 ECharts 任务的完整运行契约。读完即可生成大多数折线、柱状、饼图、散点、雷达、热力、箱线、树、桑基、漏斗和 K 线 option。

## 何时追加专项文件

- 复杂 callback、自由布局、特殊数据格式，或移动端存在多行 legend、visualMap、dataZoom、密集标签时，再读 `echarts-option-spec.md`。
- system prompt 的 `Device platform` 明确为“电脑端”或“网页端”时，读 `echarts-web-pc-spec.md`；移动端或未声明平台时不读取。
- Web/PC 分支已选择 `sunburst` 或 `gauge` 时，再分别读取 `echarts-web-pc-sunburst-reference.md` 或 `echarts-web-pc-gauge-reference.md`。
- 来源追溯或规则审计时读 `echarts-source.md`；正常生成不读取。

## 适用范围

用于准确表达趋势、分类对比、排行、占比、相关性、分布、层级、流向、漏斗、进度和金融 K 线。用户明确要求 ECharts、option、`echarts` 代码块或图表配置时直接使用。

不用于地图、通用网页、原图标注、几何证明、复杂动画或知识结构示意；后者使用 HTML/SVG。

## 输出契约

只输出完整 option 对象：

````text
<一句话说明数据来源、口径或示例属性>

```echarts
{
  title: { text: '标题' },
  tooltip: { trigger: 'axis', triggerOn: 'click', renderMode: 'richText', confine: true },
  xAxis: { type: 'category', data: ['A', 'B', 'C'] },
  yAxis: { type: 'value' },
  series: [{ type: 'line', data: [1, 2, 3] }]
}
```

<必要的关键结论>
````

- 代码块语言必须是小写 `echarts`。
- 不输出 `const option =`、`echarts.init`、`setOption`、HTML、CSS、CDN、DOM 或 renderer 包裹。
- option 自包含、无注释、无外部变量。
- 不显式指定颜色（含纯色和渐变）；这一限制只针对颜色属性，字号、字重、线宽、透明度、间距和位置等非颜色配置仍按原规范设置。
- 普通数据图不得同时再输出 HTML 版 ECharts。

## 数据与图形选择

- 时间趋势、多系列变化 → `line`。
- 分类对比、排行、长类目 → `bar`，长类目优先横向柱。
- 少量分类占比 → `pie`；分类多时改用 `bar`。
- 双指标关系、聚类 → `scatter`。
- 多维能力 → `radar`。
- 二维矩阵 → `heatmap`，但禁止地图热力。
- 分布与离群值 → `boxplot`。
- 层级 → `tree` / `treemap` / `sunburst`。
- 流向 → `sankey`；阶段转化 → `funnel`。
- 金融开高低收 → `candlestick`，数据顺序固定为 `[open, close, lowest, highest]`。

## 稳定性

- 图表与正文从同一份已核对的数据生成；标题、series、轴、tooltip和label的指标、单位、对象与期间须对应实际字段，不能把一个指标的值标成另一个指标。
- 一维类目序列按 `axis.data[i]` 对应 `series.data[i]`，缺值用 `null` 占位，不删项造成错位；显式坐标、时间点或 `encode` 数据按维度映射检查，不强求点数等长。仅为减少刻度文字时不裁剪轴数据；真正筛选或聚合时同步处理轴和各序列。
- 日期事件和区间数据须按对应系列与维度表达；普通 `bar` 的 `[开始,结束]` 不会自动成为区间条。核对类别及起止值映射，有执行条件时确认核心图形实际画出，而非只剩坐标和图例。
- tooltip 必须包含 `triggerOn:'click'`、`renderMode:'richText'`、`confine:true`；richText返回纯文本，不含HTML标签，换行使用 `String.fromCharCode(10)`。
- 默认 tooltip 足够时不写 formatter。必要 callback 直接写ES5函数并在访问参数前判空，不能把函数源码加引号当字符串；ECharts占位模板如 `formatter:'{b}: {d}%'` 仍允许。
- 禁止箭头函数、`let`、`const`、ES6反引号模板字符串、可选链、解构和依赖 DOM 的 callback。
- 直角坐标图配置 `grid` 和 `containLabel:true`。
- 多系列配置 legend；系列多时使用滚动图例或拆图。
- 核心图形和关键标签应完整可辨；其余条目可通过明确的点击、缩放或关联列表完整查看。不能用隐藏、裁切或不可读小字掩盖缺陷，也不要求首帧全部标名。
- 单位在轴、tooltip、label 和正文中保持一致；控制小数位和大数单位。
- 真实数据必须说明来源、口径或时间范围；无法核验时只输出明确标注的示例或模板。
- 禁止 `geo`、`map`、`registerMap`、行政区划、经纬度轨迹和地图热力。

## 移动端

当 system、用户或目标容器任一明确为手机/移动端时：

- 按约 351×351dp 卡片规划，而不是整机屏幕。
- 根据 title、subtext、legend、轴名实际高度计算 grid，不照抄固定 top。
- 标题 14-16px，legend/axisLabel 10-12px。
- pie、radar、gauge 等中心图根据表头后剩余空间设置中心和半径。
- visualMap、dataZoom、xAxis label 和单位必须分区，不得重叠。
- 类目密集时可缩写、旋转、抽稀刻度或拆图；关键标识保持可辨，其余条目完整可查，不能因隐藏标签破坏对应关系。
