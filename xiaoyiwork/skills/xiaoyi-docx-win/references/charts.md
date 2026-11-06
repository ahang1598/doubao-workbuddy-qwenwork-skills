# xiaoyi-docx 图表使用说明

`xiaoyi-docx` 支持通过 `matplotlib` 生成静态图表并嵌入 DOCX 文档。

## 通用参数说明

所有 `categories + series` 型图表共享以下参数：

| 参数 | 类型 | 说明 |
|------|------|------|
| `doc` | Document | python-docx 文档对象 |
| `categories` | list[str] | 分类标签，如 `["Q1", "Q2", "Q3"]` |
| `series` | list[dict] | 数据系列，如 `[{"name": "销售额", "values": [100, 200, 150]}]` |
| `title` | str | 图表标题 |
| `width` | Inches | 图片宽度，默认 `Inches(6)` |
| `height` | Inches | 图片高度，默认 `Inches(4.5)` |
| `colors` | list[tuple] | 自定义颜色，如 `[(255, 0, 0), (0, 128, 0)]` |
| `legend_pos` | str/None | 图例位置：`top`、`bottom`、`left`、`right`、`upper right`，`None` 为不显示。饼图/雷达图默认 `upper right`，其余默认 `right` |

## 导入方式

```python
from matplotlib_chart_utils import (
    add_column_chart,
    add_bar_chart,
    add_line_chart,
    add_pie_chart,
    add_area_chart,
    add_scatter_chart,
    add_radar_chart,
    add_histogram,
)
```

## 柱状图

```python
add_column_chart(
    doc,
    categories=["Q1", "Q2", "Q3"],
    series=[{"name": "销售额", "values": [100, 200, 150]}],
    title="季度销售额",
    colors=[(79, 129, 189)],
)
```

## 条形图

```python
add_bar_chart(
    doc,
    categories=["A", "B", "C"],
    series=[{"name": "销量", "values": [30, 50, 20]}],
    title="产品销量",
)
```

## 折线图

```python
add_line_chart(
    doc,
    categories=["1月", "2月", "3月"],
    series=[{"name": "访问量", "values": [120, 180, 150]}],
    title="月度访问量趋势",
)
```

## 饼图

```python
add_pie_chart(
    doc,
    categories=["A类", "B类", "C类"],
    series=[{"name": "占比", "values": [40, 35, 25]}],
    title="分类占比",
)
```

## 面积图

```python
add_area_chart(
    doc,
    categories=["Q1", "Q2", "Q3"],
    series=[{"name": "收入", "values": [50, 80, 65]}],
    title="季度收入",
)
```

## 散点图

```python
add_scatter_chart(
    doc,
    series=[
        {"name": "A组", "values": [(1, 3), (2, 5), (3, 2)]},
        {"name": "B组", "values": [(1, 4), (2, 2), (3, 6)]},
    ],
    title="散点分布",
)
```

## 雷达图

```python
add_radar_chart(
    doc,
    categories=["速度", "质量", "成本", "服务", "创新"],
    series=[{"name": "A产品", "values": [4, 5, 3, 4, 5]}],
    title="能力评估",
)
```

## 直方图

```python
add_histogram(
    doc,
    data=[1.2, 2.3, 1.8, 3.0, 2.5, 2.2, 3.1, 1.9],
    bins=4,
    title="数据分布",
    color=(79, 129, 189),
)
```
