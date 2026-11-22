# 水波图：liquid

`chart_type` / `sub_chart_type` 均为 `liquid`。

## 数据角色与数量

严格 0 个维度、至少 1 个度量。唯一数据源的 `dimensions` 为 `[]`。角色由 `dimensions/measures` 顺序推导，首个度量为指标值；先核对指标口径，不能把样式设置当作完成率计算。

## 目标值 `_targetValue`

水位和中心百分比 = 首个度量值 ÷ `_targetValue`，未写时目标为 1。`_targetValue` 写在 `ai_config.spec` 顶层，必须是非 0 的有限数字：

- 度量本身是 0~1 的比例（如百分比格式字段的平均值）：不写。
- 度量是 0~100 的进度或分值：写 `"_targetValue": 100`。
- 度量是计数、金额等绝对量：写用户给出的目标值；用户没给目标值时先澄清，不直接生成水波图。

无法确认度量单位时先澄清，不按数值大小猜测。

## ECharts 样式 option

当前 contract 使用平台持有的 `custom` 系列承载水波图，不开放旧引擎的 liquid 类型或额外插件入口；不提交自定义渲染函数。轮廓形状、外轮廓和指标层写在 `ai_config.spec` 顶层，不写进 `series`。

以下仅为 `ai_config.spec`（菱形轮廓、隐藏名称标题、保留中心数值）：

```json
{
  "maskShape": "diamond",
  "indicator": {"title": {"visible": false}},
  "tooltip": {"trigger": "item"},
  "series": [{
    "type": "custom",
    "label": {"fontSize": 24, "color": "#1f2329"},
    "itemStyle": {"color": "#3370eb", "opacity": 0.85}
  }]
}
```

| 原话 | 写入位置 |
|---|---|
| 轮廓形状（圆形、矩形、正方形、菱形、三角形、十字、星形） | 顶层 `maskShape`：`circle`（默认）、`rect`（铺满组件宽高）、`square`、`diamond`、`triangle`、`cross`、`star`；其它值会导致图表渲染失败 |
| 隐藏外轮廓线 | 顶层 `outline:{"visible":false}` |
| 外轮廓颜色 | `series[0].itemStyle.borderColor` |
| 外轮廓与水体间距、外边距 | 顶层 `outlinePadding`（非负数，默认 10）、`outlineMargin`（数字，或长度为 1、2、4 的数字数组） |
| 水体颜色、透明度 | `series[0].itemStyle.color`、`series[0].itemStyle.opacity` |
| 中心数值字号、颜色 | `series[0].label.fontSize`、`series[0].label.color` |
| 隐藏名称标题、保留中心数值 | 顶层 `indicator:{"title":{"visible":false}}` |
| 隐藏中心数值 | 顶层 `indicator:{"content":[{"visible":false}]}` |
| 名称标题和中心数值都隐藏 | 顶层 `indicator:{"visible":false}` |

- 中心数值显隐不读 `label.show`；顶层 `content`、`label.style.fontSize`、`indicatorSmartInvert:true` 会导致图表渲染失败，不要写。
- `series[].shape`、`series[].max/min`、`markLine` 对水波图不生效，`title.subtext` 只是文字：形状只认 `maskShape`，目标只认 `_targetValue`。
- 写入后回读 `spec`，核对 `_targetValue`、`maskShape`、`indicator` 已按原话保存。
