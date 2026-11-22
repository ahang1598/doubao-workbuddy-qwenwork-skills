# 瀑布图：waterfall

## 公开子类型

`chart_type` 为 `waterfall`；全部至少 1 个度量，维度无上限。

| sub_chart_type | 最少维度 | 形态 |
|---|---:|---|
| waterfall | 1 | 基础瀑布 |
| waterfallHorizontal | 1 | 水平瀑布 |
| stackedWaterfall | 2 | 堆叠瀑布 |

仅开放上表三项，不按前端或历史文档扩展 subtype。

## 数据角色

角色由 `dimensions/measures` 顺序推导：首个维度为分类；堆叠型末位维度为系列；首个度量为增减量。最低度量数是 1，不要求旧协议中的总计标记、总计值等额外字段。不在 spec 写字段绑定或总计数据。

## ECharts 样式 option

瀑布结构由平台依据 subtype 和结果构造。样式 option 使用 `bar` 系列，不存在 ECharts `waterfall` 系列类型。以下为 `ai_config.spec`。

```json
{
  "tooltip": {"trigger": "axis"},
  "xAxis": {"type": "category"},
  "yAxis": {"type": "value"},
  "series": [{
    "type": "bar",
    "stack": "waterfall",
    "itemStyle": {"opacity": 0.9},
    "label": {"show": true, "position": "top"}
  }]
}
```

`waterfall` 与 `waterfallHorizontal` 之间交换 `xAxis.type`/`yAxis.type` 时，服务端会切换 subtype；`stackedWaterfall` 没有横向形态，改方向会返回错误。常用配置包括 `series[].label.show/fontSize/color`、`itemStyle.color/opacity`、轴标签及 `tooltip`。不沿用旧引擎的标签显示规则。
