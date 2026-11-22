# 玫瑰图：rose

## 公开子类型

`chart_type` 为 `rose`；全部至少 1 个度量，维度无上限。

| sub_chart_type | 最少维度 | 形态 |
|---|---:|---|
| rose | 1 | 基础极坐标柱 |
| groupedRose | 2 | 分组极坐标柱 |
| stackedRose | 2 | 堆叠极坐标柱 |
| groupedStackedRose | 3 | 分组堆叠极坐标柱 |

## 数据角色

角色由 `dimensions/measures` 顺序推导：首个维度为分类，多维系列型的末位维度为系列，首个度量为数值。三维 subtype 至少需要三个维度，不能用多度量替代。

| sub_chart_type | dimensions 顺序 |
|---|---|
| groupedRose | `[分组, 系列]`：扇区按首维分组，末维区分颜色 |
| stackedRose | `[分类, 堆叠层]` |
| groupedStackedRose | `[分组, 组内分类, 堆叠层]` |

例：“按缺陷类别看缺陷数 → 按缺陷状态分组 → 加一层是否影响放行，变成分组堆叠玫瑰图”的终态是一张 `groupedStackedRose`，`dimensions` 为 `[缺陷类别, 缺陷状态, 是否影响放行]`，不拆成两张图。

## ECharts 样式 option

本协议的玫瑰图是 `bar` + `coordinateSystem:"polar"`，不是 `series.type:"rose"`，也不是饼图 roseType 的替代入口。

以下为基础玫瑰图的 `ai_config.spec`：

```json
{
  "tooltip": {"trigger": "item"},
  "legend": {"show": true},
  "polar": {"radius": "70%"},
  "angleAxis": {"type": "category"},
  "radiusAxis": {"type": "value"},
  "series": [{
    "type": "bar",
    "coordinateSystem": "polar",
    "label": {"show": false},
    "itemStyle": {"opacity": 0.9}
  }]
}
```

堆叠型使用 `stack:"total"`，分组堆叠型使用 `stack:"group"`；保留平台的极坐标结构。常用配置包括 `polar.radius`、`legend.show`、`series[].label.show/fontSize/color`、`itemStyle.color/opacity`。
