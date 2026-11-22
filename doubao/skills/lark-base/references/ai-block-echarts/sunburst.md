# 旭日图：sunburst

`chart_type` / `sub_chart_type` 均为 `sunburst`。

## 数据角色与数量

至少 2 个维度、1 个度量，维度无上限。角色由 `dimensions/measures` 顺序推导：全部维度依次组成从父到子的层级路径，内圈为父层，外圈为子层；首个度量为规模。平台由平表聚合结果构建层级，不手写节点或 children。

## ECharts 样式 option

以下仅为 `ai_config.spec`。

```json
{
  "tooltip": {"trigger": "item"},
  "series": [{
    "type": "sunburst",
    "radius": ["15%", "90%"],
    "center": ["50%", "50%"],
    "label": {"show": true, "rotate": "radial", "fontSize": 12},
    "itemStyle": {"borderColor": "#ffffff", "borderWidth": 1},
    "emphasis": {"focus": "ancestor"}
  }]
}
```

常用配置包括 `radius/center/startAngle`、`label.show/rotate/fontSize/color`、`itemStyle.borderColor/borderWidth`、`levels` 的样式与 `emphasis`。保持真实层级顺序，不能通过 option 偷换父子字段。
