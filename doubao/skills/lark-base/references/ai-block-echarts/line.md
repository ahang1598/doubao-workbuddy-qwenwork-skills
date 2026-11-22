# 折线图：line

## 公开子类型

`chart_type` 固定为 `line`。所有 subtype 至少 1 个度量；除 `verticalLine` 恰好 1 个分类维度外，维度不限制上限。

| sub_chart_type | 最少维度 | 形态 | Dashboard 已覆盖 |
|---|---:|---|---|
| line | 1 | 基础趋势 | 是 |
| smoothLine | 1 | 平滑曲线 | 是 |
| stepLine | 1 | 阶梯线 | 是 |
| verticalLine | 1 | 转置坐标轴 | 否 |
| multiSeriesLine | 2 | 多系列 | 是 |
| nonStackedLine | 2 | 非堆叠多系列 | 是 |
| percentLine | 2 | 百分比堆叠 | 否 |
| stackedLine | 2 | 堆叠 | 否 |

## 数据角色

角色由 `data_sources[0].dimensions/measures` 顺序推导：首个维度为分类，多维系列型的末位维度为系列；首个度量为数值。多度量不能替代 subtype 的最少维度要求。

## ECharts 样式 option

以下 JSON 仅为 `ai_config.spec`。`series[].type` 使用 `line`，不是 subtype 名称。

```json
{
  "tooltip": {"trigger": "axis"},
  "legend": {"show": true},
  "xAxis": {"type": "category", "axisLabel": {"rotate": 20}},
  "yAxis": {"type": "value", "splitLine": {"show": true}},
  "series": [{
    "type": "line",
    "smooth": true,
    "showSymbol": false,
    "lineStyle": {"width": 3},
    "label": {"show": false}
  }]
}
```

- `smoothLine` 使用 `smooth:true`；`stepLine` 使用 `step:"end"`，不同时启用平滑。
- `verticalLine`（垂直折线图）只画一条线：只放 1 个分类维度（如周次）和度量，多传维度会被拒绝。用户只说“垂直折线图看趋势”时不要自行追加分组维度去画多条线；用户明确要求按组多条线时，说明垂直形态只支持单线，由用户选择单线垂直或 `multiSeriesLine` 横向多线，不擅自换类型。
- `line` 与 `verticalLine` 之间交换 `xAxis.type`/`yAxis.type` 时，服务端会切换 subtype；其他折线 subtype 没有垂直形态，改方向会返回错误。
- 是否堆叠由 subtype 决定：`multiSeriesLine`/`nonStackedLine` 与 `stackedLine` 之间可通过 patch `series[].stack` 切换；单系列折线堆叠没有视觉差异。百分比轴可用 `axisLabel.formatter:"{value}%"`，但格式化不负责数值归一化。
- 常用配置包括 `lineStyle.color/width/type`、`label.show/position/fontSize/color`、`legend.show`。仅改样式时用 spec patch，不重写数据源。
- 数据标签默认不显示；“标签放底部”写 `series[].label:{"show":true,"position":"bottom"}`，不是 `legend.bottom`。单位写进组件名称或 `yAxis.axisLabel.formatter`，有图例时不写 `yAxis.name`（会与顶部图例重叠）。
