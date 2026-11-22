# 矩形树图：treemap

## 公开子类型

`chart_type` 为 `treemap`。两项都至少 2 个维度、1 个度量，维度无上限；基础树图也不能只给一个维度。

| sub_chart_type | 形态 |
|---|---|
| treemap | 基础矩形树图 |
| nestedTreemap | 显示父级标签的嵌套矩形树图 |

用户要求嵌套展示或可见父级标签时选择 `nestedTreemap`；否则选 `treemap`。

## 数据角色

角色由 `dimensions/measures` 顺序推导：全部维度按顺序形成从父到子的层级路径，首个度量决定矩形面积。平台从平表聚合数据构建层级，不手写树结构。

## ECharts 样式 option

以下为嵌套矩形树图的 `ai_config.spec`；基础树图可以省略 `upperLabel`。

```json
{
  "tooltip": {"trigger": "item"},
  "series": [{
    "type": "treemap",
    "roam": false,
    "leafDepth": 2,
    "upperLabel": {"show": true, "fontSize": 12},
    "label": {"show": true},
    "itemStyle": {"borderColor": "#ffffff", "borderWidth": 1, "gapWidth": 2},
    "breadcrumb": {"show": true}
  }]
}
```

常用配置包括 `roam/leafDepth`、`upperLabel.show`、`label.show/fontSize/color`、`itemStyle.borderColor/borderWidth/gapWidth`、`breadcrumb.show`。`series[].type` 固定为 `treemap`，不能填 `nestedTreemap`。
