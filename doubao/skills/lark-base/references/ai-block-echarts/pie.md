# 饼图与环形图：pie

## 公开子类型

`chart_type` 为 `pie`；两种 subtype 均至少 1 个维度、1 个度量，维度无上限。

| sub_chart_type | 形态 | ECharts radius |
|---|---|---|
| pie | 饼图 | 单一外半径 |
| donut | 环形图 | 内外半径数组 |

AI Block 的环形 subtype 是 `donut`，普通 Dashboard 的 block 类型则是 `ring`，两者不可混写。

## 数据角色

角色由 `dimensions/measures` 顺序推导：首个维度为分类，首个度量为扇区数值。

## ECharts 样式 option

以下为环形图 `ai_config.spec`。饼图将 radius 改为单值如 `"70%"`。

```json
{
  "tooltip": {"trigger": "item", "formatter": "{b}: {c} ({d}%)"},
  "legend": {"show": true},
  "series": [{
    "type": "pie",
    "radius": ["40%", "70%"],
    "center": ["50%", "54%"],
    "label": {"show": true, "formatter": "{b}: {d}%"},
    "labelLine": {"show": true},
    "itemStyle": {"borderColor": "#ffffff", "borderWidth": 1}
  }]
}
```

常用配置包括 `radius/center/startAngle`、`label.show/position/fontSize/color`、`labelLine.show/length`、`itemStyle.borderColor/borderWidth`。`series[].type` 固定为 `pie`，不能使用 `donut`。
