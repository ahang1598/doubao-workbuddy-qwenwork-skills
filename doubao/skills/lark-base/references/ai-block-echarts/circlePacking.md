# 气泡图与嵌套圆图：circlePacking

## 公开子类型

`chart_type` 为 `circlePacking`；全部至少 1 个维度和 1 个度量，维度无上限。

| sub_chart_type | 形态 |
|---|---|
| circlePacking | 气泡图 |
| nestedCirclePacking | 基础嵌套圆图 |
| multiRootCirclePacking | 多根节点嵌套圆图 |

“气泡图”默认指 `circlePacking/circlePacking`，不是散点图。若用户说“散点气泡”或明确要求 x/y/size 三数值角色，先澄清是否需要坐标散点语义；不要误用层级打包替代。确认是散点需求后读取普通散点图契约，能力不满足时说明限制，不编造 AI scatter subtype。

## 数据角色

角色由 `dimensions/measures` 顺序推导：全部维度按顺序组成从父到子的层级路径，首个度量决定规模。

## ECharts 样式 option

当前 contract 用平台持有的 `custom` 系列承载气泡图，不存在公开的 `series.type:"circlePacking"`。平台负责布局和渲染函数，调用方仅描述样式。

以下为 `ai_config.spec`：

```json
{
  "tooltip": {"trigger": "item"},
  "series": [{
    "type": "custom",
    "label": {"show": true, "fontSize": 12},
    "itemStyle": {"opacity": 0.85, "borderColor": "#ffffff", "borderWidth": 1}
  }]
}
```

常用配置包括 `label.show/fontSize/color`、`itemStyle.color/opacity/borderColor/borderWidth` 与 `tooltip`。不承诺历史引擎私有布局参数可用。
