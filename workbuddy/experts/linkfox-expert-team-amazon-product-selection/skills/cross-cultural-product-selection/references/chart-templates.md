# ECharts 图表配置模板（6 段 + 新品清单）

聚合脚本 `scripts/aggregate_11d.py` 输出的 JSON 填入下列模板。

## 目录

1. [页流量占比（段1）](#段1-页流量占比)
2. [自然位集中度帕累托（段2）](#段2-自然位集中度)
3. [分布图（段3/4/5）](#段3-45-分布图)
4. [是否含变体 KPI（段6）](#段6-是否含变体)
5. [新品清单附录](#附录-新品清单)
6. [完整聚合 JSON 结构](#完整聚合-json-结构)

## 配色

| 用途 | 色值 |
|------|------|
| 柱（商品数） | `#4f46e5` |
| 柱（销量） | `#f59e0b` |
| 折线（占比%） | `#10b981` |
| 饼/其它 | `['#4f46e5','#06b6d4','#8b5cf6','#f59e0b','#10b981','#ef4444']` |

---

## 段1 页流量占比

`type: "table"`。可用表格或柱状图。

数据：`dimensions[0].data.pages[]` → `page`, `productCount`, `units`, `unitsShare`, `revenue`, `revenueShare`。

```javascript
// 可选柱状：各页销量占比
xAxis.data = pages.map(p => '第' + p.page + '页');
series[0].data = pages.map(p => p.unitsShare); // 或 units
```

---

## 段2 自然位集中度

`type: "pareto"`。

```javascript
var d = dim2.data;
chart.setOption({
  title: { text: '自然位销量集中度', left: 'center', textStyle: { fontSize: 14 } },
  tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
  legend: { data: ['销量', '累计占比'], top: 30 },
  xAxis: { type: 'category', data: d.labels },
  yAxis: [
    { type: 'value', name: '销量' },
    { type: 'value', name: '累计占比', position: 'right', max: 100, axisLabel: { formatter: '{value}%' } }
  ],
  series: [
    { name: '销量', type: 'bar', data: d.units, itemStyle: { color: '#f59e0b' } },
    { name: '累计占比', type: 'line', yAxisIndex: 1, data: d.cumulativeShare, itemStyle: { color: '#10b981' } }
  ],
  grid: { left: '10%', right: '8%', top: 60, bottom: 40, containLabel: true }
});
```

额外展示：`data.top10UnitsShare`（前10名销量占比）。

---

## 段3/4/5 分布图

统一：柱 = 商品数，线 = 销量占比%。

```javascript
var d = dim.data; // labels, productCounts, salesShares
chart.setOption({
  title: { text: '价格分布', left: 'center', textStyle: { fontSize: 14 } },
  tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
  legend: { data: ['商品数量', '销量占比'], top: 30 },
  xAxis: { type: 'category', data: d.labels },
  yAxis: [
    { type: 'value', name: '商品数' },
    { type: 'value', name: '销量占比', position: 'right', axisLabel: { formatter: '{value}%' } }
  ],
  series: [
    { name: '商品数量', type: 'bar', data: d.productCounts, itemStyle: { color: '#4f46e5' } },
    { name: '销量占比', type: 'line', yAxisIndex: 1, data: d.salesShares, itemStyle: { color: '#10b981' } }
  ],
  grid: { left: '10%', right: '8%', top: 60, bottom: 40, containLabel: true }
});
```

段3 额外 KPI：`salesWeightedAvgPrice`、`simpleAvgPrice`。

---

## 段6 是否含变体

`type: "data"` 纯 KPI：

- `hasVariantCount` / `hasVariantRatio`
- `hasVariantUnitsShare`
- `note`

不要解读为变体数量或复杂度。

---

## 附录 新品清单

`appendix.data`：

- `rule` / `note` / `count`
- `items[]`：organic_rank, asin, title, price, rating, ratings, units, units_imputed, has_variant

用表格渲染；`units_imputed=true` 时标注「估算」。

---

## 完整聚合 JSON 结构

```json
{
  "meta": {
    "totalProducts": 46,
    "rawUnitsCoverage": 70.0,
    "rawUnitsCount": 32,
    "imputedUnitsCount": 14,
    "missingUnitsDefault": 50,
    "rankMode": "recomputed",
    "aggregatedAt": "2026-07-31 19:00:00",
    "dimensions": 6,
    "bucketMode": "smart",
    "disclaimer": "..."
  },
  "bucketDefs": { "price": [], "ratingCount": [], "ratingValue": [] },
  "dimensions": [
    { "dimension": 1, "name": "页流量占比", "type": "table", "data": {} },
    { "dimension": 2, "name": "自然位集中度", "type": "pareto", "data": {} },
    { "dimension": 3, "name": "价格分布", "type": "distribution", "data": {} },
    { "dimension": 4, "name": "评分数分布", "type": "distribution", "data": {} },
    { "dimension": 5, "name": "评分分布", "type": "distribution", "data": {} },
    { "dimension": 6, "name": "是否含变体", "type": "data", "data": {} }
  ],
  "appendix": {
    "name": "新品清单（代理）",
    "type": "table",
    "data": { "rule": "...", "note": "...", "count": 0, "items": [] }
  }
}
```

## 报告边界文案（必须出现）

样本 = 默认排序前 3 页自然结果（已去广告）。自然位次为按页序去广告后连续编号，非官方 rank/BSR。月销缺失按 50 件计。新品清单以评分数 &lt; 100 为代理口径。
