# 组件库扩展

本文件是 `linkfox-report-generator` 的 `references/analysis-layouts.md` 的扩展，定义本 skill 专用的自定义组件。S5 报告生成时，除读取系统级 analysis-layouts.md 外，同时 Read 本文件获取扩展组件。

---

## 18. Three-Column Stats Panel（三列数据总览看板）

适用于"全部 / 头部 / 新品"三组同构指标并列展示的场景（如卖家精灵市场统计看板还原）。用 `comparison-grid cols-3` + 每列内嵌 `data-table` 实现，纯 API 直取值，无派生计算，无图表。

### 布局结构

- 三列并排，每列一个 `comparison-card`，卡片标题为分组名
- 每列内嵌 `data-table`，左列字段名、右列数值（`.num` 右对齐）
- 数值格式：金额加 `$` 前缀 + 千分位；百分比保留 1 位小数；关键指标用 `<strong>` 加粗
- 重量/体积等双单位字段用 ` / ` 分隔（如 `0.31 lbs / 140 g`）

### 三列分组规则

| 列 | 标题 | 数据来源 | 字段数 |
|----|------|---------|--------|
| 左列 | 全部样本 | API 顶层字段 | 13 |
| 中列 | 头部商品（前 10） | API `hl*` 前缀字段 | 8 |
| 右列 | 新品（6个月内上架）+ 市场时间 | API `new*` 前缀字段 + `firstShelfDate`/`lastShelfDate` | 11 |

### 字段映射

**左列：全部样本**

| 显示名 | API 字段 | 格式 |
|--------|---------|------|
| 样本商品数 | products | 整数 |
| 样本品牌数 / 卖家数 | brands / sellers | `43 / 48` |
| 平均 BSR | avgBsr | 千分位 |
| 近30天均销量 | avgUnits | 整数 |
| 近30天均销售额 | avgRevenue | `$` + 千分位 |
| 平均价格 | avgPrice | `$` + 两位小数 |
| 近30天评分平均增长数 | avgRatingsCv | 整数 |
| 平均评分数 | avgRatings | 千分位 |
| 平均星级 | avgRating | 一位小数 |
| 平均卖家数 | avgSellers | 一位小数 |
| 平均重量 | avgWeight / baseAvgWeight | `X lbs / Y g` |
| 平均体积 | avgVolume / baseAvgVolume | `X in³ / Y cm³` |
| 平均毛利率 | avgProfit | 百分比加粗 |

**中列：头部商品（前 10）**

| 显示名 | API 字段 | 格式 |
|--------|---------|------|
| 前10商品样本总数 | hlProducts | 整数 |
| 前10商品 BSR 均值 | hlAvgBsr | 千分位 |
| 前10商品近30天均销量 | hlAvgUnits | 整数加粗 |
| 前10商品近30天均销售额 | hlAvgRevenue | `$` + 千分位加粗 |
| 前10商品平均价格 | hlAvgPrice | `$` + 两位小数 |
| 前10商品近30天评分增长 | hlAvgRatingsCv | 整数 |
| 前10商品平均评分数 | hlAvgRatings | 千分位 |
| 前10商品平均星级 | hlAvgRating | 一位小数 |

**右列：新品 + 市场时间**

| 显示名 | API 字段 | 格式 |
|--------|---------|------|
| 新品数量 | newProducts | 整数 |
| 新品占比 | newProductProportion | 百分比加粗 |
| 新品评分数（最高） | maxNewRatings | 千分位 |
| 新品评分数（平均） | newAvgRatings | 整数 |
| 新品评分数（最低） | minNewRatings | 整数 |
| 新品平均价格 | newAvgPrice | `$` + 两位小数 |
| 新品平均星级 | newAvgRating | 一位小数 |
| 新品近30天均销量 | newAvgUnits | 整数 |
| 新品近30天均销售额 | newAvgRevenue | `$` + 千分位 |
| 商品首次上架时间 | firstShelfDate | YYYY-MM-DD |
| 商品最新上架时间 | lastShelfDate | YYYY-MM-DD |

### HTML 结构示例

```html
<div class="comparison-grid cols-3">
  <div class="comparison-card">
    <div class="card-title">全部样本</div>
    <div class="data-table-wrapper">
      <table class="data-table">
        <thead><tr><th>指标</th><th class="num">全部样本 (100)</th></tr></thead>
        <tbody>
          <tr><td>样本商品数</td><td class="num">100</td></tr>
          <tr><td>样本品牌数 / 卖家数</td><td class="num">43 / 48</td></tr>
          <!-- ... 其余字段 ... -->
          <tr><td>平均毛利率</td><td class="num"><strong>81.91%</strong></td></tr>
        </tbody>
      </table>
    </div>
  </div>
  <!-- 中列：头部商品、右列：新品+时间，结构相同 -->
</div>
```

### 使用要点

1. 数据全部直接取自 API 返回值，`data-source` 的 `.ds-computed` 写"无派生计算"
2. `totalProducts`（商品总数）不在 market-statistics 返回中，从 `amazon-category-lookup` 或 `sellersprite-market-research` 获取，写入 report-meta
3. 如需追加派生对比指标，用虚线分隔行区分原始值和派生值：
   `<tr><td colspan="2" style="text-align:center;color:#999;font-size:12px;padding:6px;border-top:2px dashed #ddd;">以下为派生对比指标</td></tr>`

---

## 19. Amazon-Search Charts Panel（前台搜索数据图表看板）

基于 `linkfox-amazon-search` 前三页（默认相关性排序）返回的商品数据，生成 9 个分布与集中度图表。全部字段来自 API 返回值，仅需 Python 分桶统计后用 ECharts 渲染。

### 图表清单与字段映射

| 图表 | 类型 | X 轴 | Y 轴（左） | Y 轴（右） | API 字段 | 分桶规则 |
|------|------|------|-----------|-----------|---------|---------|
| 商品集中度 | 帕累托图（柱+线） | position（1~N） | monthlySalesUnits | 累计销量占比% | position, monthlySalesUnits | 按 position 排序，逐条累加 |
| 品牌集中度 | 柱+线 | brand（按销量降序取 Top 15） | monthlySalesUnits | 累计销量占比% | brand, monthlySalesUnits | 按 brand 聚合求和 |
| 卖家类型分布 | 饼图 | — | — | — | fulfillment | FBA / AMZ / 其他 |
| 卖家所属地分布 | 柱+线 | sellerNation | 商品数 | 销量占比% | sellerNation, monthlySalesUnits | 按 sellerNation 聚合 |
| 上架时间分布 | 柱+线 | 上架时长区间 | 商品数 | 销量占比% | availableDate | 1月/3月/半年/1年/2年/3年/3年+ |
| 上架趋势分布 | 柱+线 | 上架年份 | 商品数 | 销量占比% | availableDate | 按年提取 |
| 评分数分布 | 柱+线 | 评论数区间 | 商品数 | 销量占比% | ratings | 无/1-50/50-100/100-200/200-500/500+ |
| 评分值分布 | 柱+线 | 星级区间 | 商品数 | 销量占比% | rating | <3.0/3.0-3.5/3.5-4.0/4.0-4.2/4.2-4.5/4.5+ |
| 价格分布 | 柱+线 | 价格区间 | 商品数 | 销量占比% | extractedPrice | <$15/$15-30/$30-60/$60-100/$100-200/$200+ |

### 不支持还原的图表（缺字段）

| 卖家精灵图表 | 缺失原因 | 替代数据源 |
|------------|---------|-----------|
| 卖家集中度 | amazon-search 无卖家名称字段，只有 sellerNation | sellersprite-market-statistics（间接） |
| A+视频分布 | amazon-search 无 A+/视频状态字段 | 需 amazon-product-detail 逐 ASIN 查询 |
| 商品需求趋势 | amazon-search 无搜索量时间序列 | aba-intelligent-query 或 jiimore |

### ECharts 配色规则

- 柱状图（商品数）：`#4f46e5`（靛蓝）
- 柱状图（销量）：`#f59e0b`（橙黄）
- 折线图（占比%）：`#10b981`（绿色）
- 饼图色板：`['#4f46e5','#06b6d4','#8b5cf6','#f59e0b','#10b981','#ef4444']`

### 通用图表配置模板（帕累托图 — 商品集中度/品牌集中度）

```javascript
// chart_product_concentration
var chart = echarts.init(document.getElementById('chart_id'));
chart.setOption({
  title: { text: '商品集中度', left: 'center', textStyle: { fontSize: 14 } },
  tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
  legend: { data: ['销量', '累计占比'], top: 30 },
  xAxis: { type: 'category', data: /* position 或 brand 数组 */, axisLabel: { rotate: 45, fontSize: 10 } },
  yAxis: [
    { type: 'value', name: '销量' },
    { type: 'value', name: '累计占比', position: 'right', axisLabel: { formatter: '{value}%' }, max: 100 }
  ],
  series: [
    { name: '销量', type: 'bar', data: /* monthlySalesUnits 数组 */, itemStyle: { color: '#f59e0b' } },
    { name: '累计占比', type: 'line', yAxisIndex: 1, data: /* 累计百分比数组 */, itemStyle: { color: '#10b981' }, lineStyle: { width: 2 } }
  ],
  grid: { left: '10%', right: '8%', top: 60, bottom: 60, containLabel: true }
});
```

### 通用图表配置模板（分布图 — 上架时间/评分数/评分值/价格/卖家所属地）

分布图统一为"柱状图（商品数）+ 折线图（销量占比%）"双 Y 轴结构：

```javascript
// chart_distribution
var chart = echarts.init(document.getElementById('chart_id'));
chart.setOption({
  title: { text: '价格分布', left: 'center', textStyle: { fontSize: 14 } },
  tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
  legend: { data: ['商品数量', '销量占比'], top: 30 },
  xAxis: { type: 'category', data: /* 区间标签数组 */ },
  yAxis: [
    { type: 'value', name: '商品数' },
    { type: 'value', name: '销量占比', position: 'right', axisLabel: { formatter: '{value}%' } }
  ],
  series: [
    { name: '商品数量', type: 'bar', data: /* 每桶商品数 */, itemStyle: { color: '#4f46e5' }, label: { show: true, position: 'top' } },
    { name: '销量占比', type: 'line', yAxisIndex: 1, data: /* 每桶销量占比% */, itemStyle: { color: '#10b981' }, label: { show: true, position: 'top', formatter: '{c}%' } }
  ],
  grid: { left: '10%', right: '8%', top: 60, bottom: 40, containLabel: true }
});
```

### 通用图表配置模板（饼图 — 卖家类型分布）

```javascript
// chart_fulfillment_pie
var chart = echarts.init(document.getElementById('chart_id'));
chart.setOption({
  title: { text: '卖家类型分布', left: 'center', textStyle: { fontSize: 14 } },
  tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
  series: [{
    type: 'pie', radius: ['40%', '70%'], center: ['50%', '55%'],
    data: [
      { name: 'FBA', value: /* FBA商品数 */, itemStyle: { color: '#4f46e5' } },
      { name: 'Amazon自营', value: /* AMZ商品数 */, itemStyle: { color: '#06b6d4' } },
      { name: '其他', value: /* 其他商品数 */, itemStyle: { color: '#f59e0b' } }
    ],
    label: { formatter: '{b}\n{c}个 ({d}%)' }
  }]
});
```

### Python 分桶统计提示词

生成报告前，先用 Python 对前三页合并数据做分桶统计，输出 JSON 后填入 ECharts data 数组。关键分桶逻辑：

```python
# 价格分布分桶
price_buckets = {"<$15": 0, "$15-30": 0, "$30-60": 0, "$60-100": 0, "$100-200": 0, ">$200": 0}
price_sales = {k: 0 for k in price_buckets}
for p in products:
    price = p.get("extractedPrice", 0) or 0
    units = p.get("monthlySalesUnits", 0) or 0
    if price < 15: k = "<$15"
    elif price < 30: k = "$15-30"
    elif price < 60: k = "$30-60"
    elif price < 100: k = "$60-100"
    elif price < 200: k = "$100-200"
    else: k = ">$200"
    price_buckets[k] += 1
    price_sales[k] += units

# 评分数分布分桶
rating_count_buckets = {"无": 0, "1-50": 0, "50-100": 0, "100-200": 0, "200-500": 0, "500+": 0}

# 评分值分布分桶
rating_val_buckets = {"<3.0": 0, "3.0-3.5": 0, "3.5-4.0": 0, "4.0-4.2": 0, "4.2-4.5": 0, "4.5+": 0}

# 上架时间分布（需要计算距今时长）
from datetime import datetime
now = datetime(2026, 7, 24)
age_buckets = {"1个月": 0, "3个月": 0, "半年": 0, "1年": 0, "2年": 0, "3年": 0, "3年+": 0}

# 品牌集中度（按销量降序）
brand_units = {}
for p in products:
    b = p.get("brand", "Unknown")
    brand_units[b] = brand_units.get(b, 0) + (p.get("monthlySalesUnits", 0) or 0)
sorted_brands = sorted(brand_units.items(), key=lambda x: -x[1])[:15]

# 商品集中度（按 position 排序）
positions = sorted(products, key=lambda x: x.get("position", 99))
```
