# 柱状图与条形图：bar

## 公开子类型

`chart_type` 为 `bar`；至少 1 个度量，维度无上限。多度量不能替代最少维度。

| sub_chart_type | 最少维度 | 形态 | Dashboard 已覆盖 |
|---|---:|---|---|
| column | 1 | 竖直柱 | 是 |
| bar | 1 | 水平条 | 是 |
| groupedColumn | 2 | 分组柱 | 是 |
| groupedBar | 2 | 分组条 | 是 |
| stackedColumn | 2 | 堆叠柱 | 是 |
| percentStackedColumn | 2 | 百分比堆叠柱 | 是 |
| percentBar | 2 | 百分比堆叠条 | 是 |
| groupedStackedColumn | 3 | 分组堆叠柱 | 否 |
| percentGroupedStackedColumn | 3 | 分组百分比堆叠柱 | 否 |

## 数据角色

角色由 `dimensions/measures` 顺序推导：首个维度为分类，多维系列型的末位维度为系列；首个度量为数值。三维 subtype 必须提供至少三个维度，不能采用“两维加多度量”的替代方案。无需 ID、alias 或手工字段绑定。

## ECharts 样式 option

以下是柱状图 `ai_config.spec`。

```json
{
  "tooltip": {"trigger": "axis"},
  "legend": {"show": true},
  "xAxis": {"type": "category"},
  "yAxis": {"type": "value", "splitLine": {"show": true}},
  "series": [{
    "type": "bar",
    "barMaxWidth": 52,
    "itemStyle": {"borderRadius": 4},
    "label": {"show": true, "position": "top"}
  }]
}
```

- 方向由 subtype 决定：竖向 `column`/`groupedColumn`/`percentStackedColumn` 分别对应横向 `bar`/`groupedBar`/`percentBar`。编辑时交换 `xAxis.type`/`yAxis.type`，服务端会切换到对应方向的 subtype；`stackedColumn`、`groupedStackedColumn`、`percentGroupedStackedColumn` 没有横向形态，改方向会返回错误。横向时标签位置可设 `right`。
- 是否堆叠由 subtype 决定，平台按 subtype 生成 `stack`。多系列 `groupedColumn` 与 `stackedColumn` 之间可通过 patch `series[].stack`（设值开启、`null` 关闭）切换；`column`/`bar` 只有一个系列，堆叠没有视觉差异。从 `column`/`bar` 改成“按 X 堆叠”或百分比堆叠时，只 patch `stack` 不生效：同时提交 `chart_type`、`sub_chart_type`（`stackedColumn`、`percentStackedColumn` 或横向 `percentBar`）和末位加入 X 作为系列维度的完整 `data_sources`。
- 百分比轴可用 `axisLabel.formatter:"{value}%"`；样式不替代数据归一化。
- 常用配置包括 `itemStyle.color/opacity/borderRadius`、`label.show/position/fontSize/color`、`barWidth/barMaxWidth`、`legend.show`；参考线等静态标注用 `series[].markLine`。
- 数据标签默认显示，位置用 `series[].label.position`（柱状 `top`/`inside`，条形 `right`/`inside`），不是 `legend`。单位写进组件名称或 `yAxis.axisLabel.formatter`，有图例时不写 `yAxis.name`（会与顶部图例重叠）。
