# 马赛克图：mosaic

## 公开子类型

`chart_type` 为 `mosaic`；至少 1 个度量，维度无上限。

| sub_chart_type | 最少维度 | 形态 |
|---|---:|---|
| mosaic | 2 | 多维分类马赛克 |
| simpleMosaic | 1 | 简化马赛克 |

## 数据角色

角色由 `dimensions/measures` 顺序推导：首个维度为分类，多维系列型的末位维度为系列；首个度量为规模。

## ECharts 样式 option

当前 contract 使用平台持有的 `custom` 系列，不使用 `series.type:"mosaic"`，调用方不得提供自定义渲染函数。

以下仅为 `ai_config.spec`：

```json
{
  "tooltip": {"trigger": "item"},
  "series": [{
    "type": "custom",
    "label": {"show": true, "fontSize": 12},
    "itemStyle": {"borderColor": "#ffffff", "borderWidth": 1, "opacity": 0.9}
  }]
}
```

常用配置包括 `label.show/fontSize/color`、`itemStyle.color/opacity/borderColor/borderWidth` 和 `tooltip`；不提交旧引擎私有的 `percent`、`bar`、`legends` 配置。用户要求超出公开 subtype、单数据源或样式能力时先澄清或拒绝。
