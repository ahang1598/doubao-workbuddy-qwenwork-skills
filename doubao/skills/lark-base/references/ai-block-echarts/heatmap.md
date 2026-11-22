# 热力图：heatmap

`chart_type` 和 `sub_chart_type` 均为 `heatmap`，不支持其它 subtype。

## 数据角色与数量

严格 2 个维度、至少 1 个度量。角色由 `dimensions/measures` 顺序推导：第一个维度为横轴分类，第二个维度为纵轴分类，第一个度量决定颜色强度。不能增加第三个维度，也不能用一个维度加多度量替代。

## ECharts 样式 option

以下仅为 `ai_config.spec`。颜色标尺用 `visualMap`，单元格样式写在热力系列的 `itemStyle`，不沿用旧引擎的 cell/axes 配置。

```json
{
  "tooltip": {"position": "top"},
  "xAxis": {"type": "category", "axisLabel": {"rotate": 20}},
  "yAxis": {"type": "category"},
  "visualMap": {
    "calculable": true,
    "orient": "horizontal",
    "inRange": {"color": ["#eef3ff", "#3370eb"]}
  },
  "series": [{
    "type": "heatmap",
    "label": {"show": true, "fontSize": 12},
    "itemStyle": {"borderColor": "#ffffff", "borderWidth": 1}
  }]
}
```

常用配置包括 `visualMap.show/inRange.color`、轴标签、`series[].label.show/fontSize/color`、`itemStyle.borderColor/borderWidth`。
