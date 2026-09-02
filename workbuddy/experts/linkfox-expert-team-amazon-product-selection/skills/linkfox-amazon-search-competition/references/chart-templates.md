# ECharts 图表配置模板（38 段 + 新品清单）

聚合脚本 `scripts/aggregate_competition.py` 输出的 JSON 填入下列模板。

## 目录

1. [页流量占比（段1）](#段1-页流量占比)
2. [自然位集中度帕累托（段2）](#段2-自然位集中度)
3. [分布图（段3/4/5/12/13/22/23/27）](#段345-分布图)
4. [变体覆盖 KPI（段6）](#段6-变体覆盖)
5. [品牌集中度/销量份额（段7/8）](#段78-品牌集中度)
6. [头部品牌垄断系数（段9）](#段9-头部品牌垄断系数)
7. [卖家集中度（段10）](#段10-卖家集中度)
8. [配送方式占比饼图（段11）](#段11-配送方式占比)
9. [多卖家竞争占比（段14）](#段14-多卖家竞争占比)
10. [类目分布（段15）](#段15-类目分布)
11. [门槛 KPI（段16-21/25-28/35/37/38）](#门槛-kpi)
12. [新品评论增长散点（段18）](#段18-新品评论增长散点)
13. [佣金率分布（段24）](#段24-佣金率分布)
14. [月销量趋势折线（段29/30）](#段2930-月销量趋势)
15. [BSR趋势折线（段31）](#段31-bsr趋势)
16. [新品起量速度散点（段33）](#段33-新品起量速度)
17. [生命周期阶段表（段34）](#段34-生命周期阶段)
18. [头部vs新品对比柱（段36）](#段36-头部-vs-新品)
19. [新品清单附录](#附录-新品清单)
20. [完整聚合 JSON 结构](#完整聚合-json-结构)

## 配色

| 用途 | 色值 |
|------|------|
| 柱（商品数） | `#4f46e5` |
| 柱（销量） | `#f59e0b` |
| 折线（占比%） | `#10b981` |
| 折线（趋势） | `#06b6d4` |
| 饼/其它 | `['#4f46e5','#06b6d4','#8b5cf6','#f59e0b','#10b981','#ef4444']` |

---

## 段1 页流量占比

`type: "table"`。可用表格或柱状图。

数据：`dimensions[0].data.pages[]` → `page`, `productCount`, `units`, `unitsShare`, `revenue`, `revenueShare`。

---

## 段2 自然位集中度

`type: "pareto"`。

```javascript
var d = dim.data;
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
  ]
});
```

---

## 段3/4/5 分布图

统一：柱 = 商品数，线 = 销量占比%。

```javascript
var d = dim.data;
chart.setOption({
  title: { text: dim.name, left: 'center', textStyle: { fontSize: 14 } },
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
  ]
});
```

段3 额外 KPI：`salesWeightedAvgPrice`、`simpleAvgPrice`。

分布图同样适用于：段12（变体复杂度）、段13（卖家数量）、段22（利润率）、段23（FBA费用）、段27（上架时间）。

---

## 段6 变体覆盖

`type: "data"` 纯 KPI：`hasVariantCount` / `hasVariantRatio` / `hasVariantUnitsShare`。

---

## 段7/8 品牌集中度

`type: "table"`。数据：`data.brands[]` → `brand`, `asinCount`, `asinShare`（段7）或 `units`, `unitsShare`（段8）。可用饼图或表格渲染。

---

## 段9 头部品牌垄断系数

`type: "data"`。展示 CR3/CR5：`data.cr3`, `data.cr5`, `data.label`。

---

## 段10 卖家集中度

`type: "table"`。数据：`data.sellers[]` → `sellerId`, `asinCount`, `asinShare`。

---

## 段11 配送方式占比

`type: "pie"`。数据：`data.fulfillments[]` → `type`, `count`, `share`, `unitsShare`。

```javascript
var d = dim.data;
chart.setOption({
  title: { text: '配送方式占比', left: 'center', textStyle: { fontSize: 14 } },
  tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
  series: [{
    type: 'pie', radius: ['40%', '70%'],
    data: d.fulfillments.map(f => ({ name: f.type, value: f.count }))
  }]
});
```

---

## 段14 多卖家竞争占比

`type: "data"`。`multiSellerCount` / `multiSellerRatio` / `multiSellerUnitsShare`。

---

## 段15 类目分布

`type: "table"`。数据：`data.categories[]` → `category`, `asinCount`, `asinShare`, `units`, `unitsShare`。

---

## 门槛 KPI

适用于段16-21、25-28、35、37、38，`type: "data"`。用 KPI 卡片或表格展示。

| 维度 | 关键字段 |
|------|----------|
| 16 评论门槛 | top10Avg, top10Median |
| 17 评论中位数 | median, p25, p75 |
| 19 价格门槛 | p25, p50, p75 |
| 20 BSR门槛 | top10Avg, top10Median, keepaCoverage |
| 21 BSR中位数 | median, p25, p75, keepaCoverage |
| 25 危险品占比 | hazmatCount, hazmatRatio |
| 26 成人产品占比 | adultCount, adultRatio |
| 28 新品占比 | newCount, newRatio |
| 35 市场成熟度 | avgAgeMonths, avgRatings, stage |
| 37 价格离散度 | cv, mean, stdev, label |
| 38 销量离散度 | cv, mean, stdev, label |

---

## 段18 新品评论增长散点

`type: "scatter"`。数据：`data.scatterData[]` → `ageMonths`(X), `monthlyGrowthRate`(Y)。

---

## 段24 佣金率分布

`type: "distribution"`。数据：`data.fees[]` → `fee`, `count`, `share`。

---

## 段29/30 月销量趋势

`type: "trend"`。折线图。

```javascript
var d = dim.data;
var months = d.monthlyTotals || [];
chart.setOption({
  title: { text: '市场总销量趋势', left: 'center', textStyle: { fontSize: 14 } },
  tooltip: { trigger: 'axis' },
  xAxis: { type: 'category', data: months.map(m => m.month) },
  yAxis: { type: 'value', name: '总销量' },
  series: [{ type: 'line', data: months.map(m => m.totalUnits), itemStyle: { color: '#06b6d4' }, areaStyle: {} }]
});
```

---

## 段31 BSR趋势

`type: "trend"`。数据：`data.perAsin[]` → `current`, `d30`, `d90`, `d180`。

---

## 段33 新品起量速度

`type: "scatter"`。数据：`data.newProducts[]` → `currentUnits`(X), `growthRate`(Y)。

---

## 段34 生命周期阶段

`type: "table"`。数据：`data.stages[]` → `stage`, `count`, `share`。

| 阶段 | 颜色 |
|------|------|
| 导入期 | `#10b981` |
| 成长期 | `#06b6d4` |
| 成熟期 | `#4f46e5` |
| 衰退期 | `#ef4444` |

---

## 段36 头部 vs 新品

`type: "comparison"`。柱状对比图：`top10AvgUnits` vs `newAvgUnits`。

---

## 附录 新品清单

`appendix.data`：`rule` / `note` / `count` / `items[]`。

`items[]` 字段：organic_rank, asin, brand, title, price, rating, ratings, units, availableDate, units_imputed, has_variant, keepa_available。

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
    "aggregatedAt": "2026-08-03 12:00:00",
    "dimensions": 38,
    "keepaAvailable": true,
    "keepaCoverage": 93.5,
    "keepaSuccessCount": 43,
    "bucketMode": "smart",
    "disclaimer": "..."
  },
  "bucketDefs": { "price": [], "ratingCount": [], "ratingValue": [], "variationNum": [], "sellerNum": [], "profit": [], "fbaFees": [], "availableMonths": [] },
  "dimensions": [
    {"dimension": 1, "name": "页流量占比", "type": "table", "data": {}},
    {"dimension": 2, "name": "自然位集中度", "type": "pareto", "data": {}},
    {"dimension": 3, "name": "价格分布", "type": "distribution", "data": {}},
    {"dimension": 4, "name": "评分数分布", "type": "distribution", "data": {}},
    {"dimension": 5, "name": "评分分布", "type": "distribution", "data": {}},
    {"dimension": 6, "name": "变体覆盖", "type": "data", "data": {}},
    {"dimension": 7, "name": "品牌集中度", "type": "table", "data": {}},
    {"dimension": 8, "name": "品牌销量份额", "type": "table", "data": {}},
    {"dimension": 9, "name": "头部品牌垄断系数", "type": "data", "data": {}},
    {"dimension": 10, "name": "卖家集中度", "type": "table", "data": {}},
    {"dimension": 11, "name": "配送方式占比", "type": "pie", "data": {}},
    {"dimension": 12, "name": "变体复杂度分布", "type": "distribution", "data": {}},
    {"dimension": 13, "name": "卖家数量分布", "type": "distribution", "data": {}},
    {"dimension": 14, "name": "多卖家竞争占比", "type": "data", "data": {}},
    {"dimension": 15, "name": "类目分布", "type": "table", "data": {}},
    {"dimension": 16, "name": "评论门槛(Top10)", "type": "data", "data": {}},
    {"dimension": 17, "name": "评论中位数", "type": "data", "data": {}},
    {"dimension": 18, "name": "新品评论增长速度", "type": "scatter", "data": {}},
    {"dimension": 19, "name": "价格门槛", "type": "data", "data": {}},
    {"dimension": 20, "name": "BSR门槛(Top10)", "type": "data", "data": {}},
    {"dimension": 21, "name": "BSR中位数", "type": "data", "data": {}},
    {"dimension": 22, "name": "利润率分布", "type": "distribution", "data": {}},
    {"dimension": 23, "name": "FBA费用分布", "type": "distribution", "data": {}},
    {"dimension": 24, "name": "佣金率分布", "type": "distribution", "data": {}},
    {"dimension": 25, "name": "危险品占比", "type": "data", "data": {}},
    {"dimension": 26, "name": "成人产品占比", "type": "data", "data": {}},
    {"dimension": 27, "name": "上架时间分布", "type": "distribution", "data": {}},
    {"dimension": 28, "name": "新品占比", "type": "data", "data": {}},
    {"dimension": 29, "name": "月销量趋势", "type": "trend", "data": {}},
    {"dimension": 30, "name": "市场总销量趋势", "type": "trend", "data": {}},
    {"dimension": 31, "name": "BSR趋势", "type": "trend", "data": {}},
    {"dimension": 32, "name": "BSR波动度", "type": "data", "data": {}},
    {"dimension": 33, "name": "新品起量速度", "type": "scatter", "data": {}},
    {"dimension": 34, "name": "产品生命周期阶段", "type": "table", "data": {}},
    {"dimension": 35, "name": "市场成熟度", "type": "data", "data": {}},
    {"dimension": 36, "name": "头部vs新品销量对比", "type": "comparison", "data": {}},
    {"dimension": 37, "name": "价格离散度", "type": "data", "data": {}},
    {"dimension": 38, "name": "销量离散度", "type": "data", "data": {}}
  ],
  "appendix": {
    "name": "新品清单",
    "type": "table",
    "data": { "rule": "...", "note": "...", "count": 0, "items": [] }
  }
}
```

## 报告边界文案（必须出现）

样本 = 默认排序前 3 页自然结果（已去广告）。自然位次为按页序去广告后连续编号，非官方 rank/BSR。月销缺失按 50 件计。新品清单有 Keepa 数据时以 availableDate&lt;6 月为主口径，无 Keepa 数据时以 ratings&lt;100 为代理。Keepa 数据覆盖率 = 成功 ASIN 数 / 总 ASIN 数。BSR/利润/FBA费用/品牌/卖家等维度仅在 Keepa 数据可用时呈现。
