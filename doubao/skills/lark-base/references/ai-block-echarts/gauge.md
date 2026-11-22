# 仪表图：gauge

`chart_type` / `sub_chart_type` 均为 `gauge`。

## 数据角色与数量

严格 0 个维度，至少 1 个度量。唯一数据源的 `dimensions` 必须为 `[]`，不能传分组字段。角色由 `dimensions/measures` 顺序推导，首个度量是指标数值。

## ECharts 样式 option

以下仅为 `ai_config.spec`：

```json
{
  "series": [{
    "type": "gauge",
    "min": 0,
    "max": 100,
    "startAngle": 225,
    "endAngle": -45,
    "progress": {"show": true},
    "pointer": {"show": true},
    "detail": {"show": true, "formatter": "{value}%", "fontSize": 24}
  }]
}
```

`min/max` 定义显示刻度范围，不会替代业务指标计算；若用户要求完成率，先确认源度量确实按该口径计算。常用配置包括 `progress.show`、`pointer.show`、`detail.show/fontSize/color/formatter`、`axisLabel` 与 `axisLine.lineStyle`。不沿用旧引擎的目标值或 indicator 字段。
