# 面积图：area

## 公开子类型

`chart_type` 为 `area`。全部至少 1 个度量；除 `verticalArea` 恰好 1 个分类维度外，维度无上限。

| sub_chart_type | 最少维度 | 形态 | Dashboard 已覆盖 |
|---|---:|---|---|
| area | 1 | 基础面积 | 是 |
| smoothArea | 1 | 平滑面积 | 是 |
| stepArea | 1 | 阶梯面积 | 是 |
| verticalArea | 1 | 转置坐标轴 | 否 |
| multiSeriesArea | 2 | 多系列面积 | 是 |
| percentArea | 2 | 百分比堆叠 | 是 |
| stackedArea | 2 | 堆叠面积 | 是 |

## 数据角色

角色由 `dimensions/measures` 顺序推导：首个维度为分类，多维系列型的末位维度为系列；度量提供数值。不允许用多度量规避最少维度要求。

## ECharts 样式 option

ECharts 面积图使用 `series[].type:"line"` 与 `areaStyle`，不能把 `area` 作为 series 类型。以下仅为 `ai_config.spec`。

```json
{
  "tooltip": {"trigger": "axis"},
  "legend": {"show": true},
  "xAxis": {"type": "category"},
  "yAxis": {"type": "value"},
  "series": [{
    "type": "line",
    "showSymbol": false,
    "lineStyle": {"width": 2},
    "areaStyle": {"opacity": 0.24},
    "label": {"show": false}
  }]
}
```

- 示例隐藏了数据点和数据标签：原话要求“数据点显示”时写 `showSymbol:true`，要求显示标签或标签位置时写 `label.show:true` 和 `label.position`，不能沿用示例里的 `false`。
- 平滑使用 `smooth:true`；阶梯使用 `step:"end"`。平滑堆叠、平滑百分比堆叠用 `stackedArea`/`percentArea` 加 `smooth:true`。
- 是否堆叠由 subtype 决定：`multiSeriesArea` 与 `stackedArea` 之间可通过 patch `series[].stack` 切换；单系列面积图堆叠没有视觉差异。从 `area`/`smoothArea`/`stepArea` 改成堆叠或百分比堆叠时，只 patch `stack` 不生效：同时提交 `chart_type`、`sub_chart_type`（`stackedArea` 或 `percentArea`）和末位加入系列维度的完整 `data_sources`。百分比轴格式 `"{value}%"` 只是显示格式。
- `verticalArea`（垂直面积图）只画一个系列：只放 1 个分类维度和度量，不自行追加分组维度；需要按组多系列时说明限制，由用户选择。
- `area` 与 `verticalArea` 之间交换 `xAxis.type`/`yAxis.type` 时，服务端会切换 subtype；其他面积 subtype 没有垂直形态，改方向会返回错误。
- 常用配置包括 `areaStyle.color/opacity`、`lineStyle.color/width`、`label.show/position/fontSize/color`、`legend.show`。
- 数据标签默认不显示；“标签放底部”写 `series[].label:{"show":true,"position":"bottom"}`，不是 `legend.bottom`。单位写进组件名称或 `yAxis.axisLabel.formatter`，有图例时不写 `yAxis.name`（会与顶部图例重叠）。
