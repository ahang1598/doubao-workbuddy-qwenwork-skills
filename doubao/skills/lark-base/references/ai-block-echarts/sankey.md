# 桑基图：sankey

## 公开子类型

`chart_type` 为 `sankey`。两种 subtype 均至少 2 个维度、1 个度量，维度无上限。

| sub_chart_type | 形态 | series[].orient |
|---|---|---|
| sankey | 水平流向 | horizontal |
| sankeyVertical | 垂直流向 | vertical |

仅开放上表两项，总能力清单保持 46 项。多级流向通过有序 `dimensions` 表达，如“渠道 → 地区 → 品类”；不要编造 subtype。

## 数据角色

角色由 `dimensions/measures` 顺序推导：全部维度依次组成流向路径，各相邻层形成一段连线，`measures[0]` 为沿路径的流量。两维输入保持边表兼容：`dimensions[0]` 为源节点，`dimensions[1]` 为目标节点。

多层路径只增加有序维度，下例是 `ai_config.data_sources` 的唯一元素（不是 spec）：

```json
{
  "base_token": "<BASE_TOKEN>",
  "table_name": "订单流向",
  "dimensions": [{"field": "渠道"}, {"field": "地区"}, {"field": "品类"}],
  "measures": [{"field": "金额", "aggregation": "sum"}]
}
```

## ECharts 样式 option

以下仅为 `ai_config.spec`：

```json
{
  "tooltip": {"trigger": "item"},
  "series": [{
    "type": "sankey",
    "nodeAlign": "justify",
    "nodeWidth": 20,
    "nodeGap": 8,
    "label": {"show": true, "fontSize": 12},
    "lineStyle": {"opacity": 0.4, "curveness": 0.5}
  }]
}
```

方向由 `sub_chart_type` 决定（`sankey` 水平、`sankeyVertical` 垂直），创建时不要在 spec 中写与 subtype 相反的 `orient`。编辑时直接 patch `series[0].orient`（`horizontal`/`vertical`）即可，服务端会切换为对应 subtype；也可以直接切换 `sub_chart_type`。常用配置包括 `nodeAlign/nodeWidth/nodeGap`、`label.show/fontSize/color`、`lineStyle.opacity/curveness/color`。局部样式用 spec patch，不重新提交节点和边。
