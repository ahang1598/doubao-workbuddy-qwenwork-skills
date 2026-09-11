# ECharts 精确数据图表

## 读取门

生成、修改或审核任何原生 ECharts option 前，**必须完整读取**：

1. `mode-echarts.md`
2. `echarts-option-spec.md`
3. `shared-quality.md`

该文件保留原 Skill 对移动端表头、自由布局、特殊数据格式、tooltip 和模板的完整细则。没有读完不得开始写 option。来源追溯见 `echarts-source.md`。

## 适用范围

用于准确表达趋势、分类对比、排行、占比、相关性、分布、层级、流向、漏斗、进度和金融 K 线。用户明确要求 ECharts、option、`echarts` 代码块或图表配置时直接使用。

不用于地图、通用网页、原图标注、几何证明、复杂动画或知识结构示意；后者使用 HTML/SVG。

## 输出契约

只输出完整 option 对象：

````text
<一句话说明数据来源、口径或示例属性>

```echarts
{
  backgroundColor: 'transparent',
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

- tooltip 必须包含 `triggerOn:'click'`、`renderMode:'richText'`、`confine:true`。
- 默认 tooltip 足够时不写 formatter。必要 callback 使用 ES5 function，访问参数前判空。
- 禁止箭头函数、`let`、`const`、模板字符串、可选链、解构和依赖 DOM 的 callback。
- 直角坐标图配置 `grid` 和 `containLabel:true`。
- 多系列配置 legend；系列多时使用滚动图例或拆图。
- 单位在轴、tooltip、label 和正文中保持一致；控制小数位和大数单位。
- 禁止 `geo`、`map`、`registerMap`、行政区划、经纬度轨迹和地图热力。

## 移动端

当 system、用户或目标容器任一明确为手机/移动端时：

- 按约 351×351dp 卡片规划，而不是整机屏幕。
- 根据 title、subtext、legend、轴名实际高度计算 grid，不照抄固定 top。
- 标题 14-16px，legend/axisLabel 10-12px。
- pie、radar、gauge 等中心图根据表头后剩余空间设置中心和半径。
- visualMap、dataZoom、xAxis label 和单位必须分区，不得重叠。
- 类目密集时缩短日期、旋转/隐藏重叠标签，或建议聚合、采样、拆图。
