# Keepa 字段参考

`linkfox-keepa-product-request`（history=1）返回的字段列表、类型、可用率与用法。

## 字段映射

### 身份字段

| 字段 | 类型 | 可用率 | -1/0 处理 | 用途 |
|------|------|--------|-----------|------|
| asin | string | 100% | — | 主键 |
| parentAsin | string | ~70% | None | 变体归属 |
| brand | string | ~90% | None | 品牌集中度(维7-9) |
| manufacturer | string | ~80% | None | 展示 |
| model | string | ~60% | None | 展示 |
| color | string | ~60% | None | 展示 |
| material | string | ~60% | None | 展示 |

### 卖家字段

| 字段 | 类型 | 可用率 | -1/0 处理 | 用途 |
|------|------|--------|-----------|------|
| buyBoxSellerId | string | ~85% | None | 卖家集中度(维10) |
| sellerNum | integer | ~85% | None(-1/0) | 卖家数量分布(维13-14) |
| variationNum | integer | ~80% | None(-1/0) | 变体复杂度(维6,12) |
| fulfillment | string | ~85% | None | 配送方式(维11) |

### 上架字段

| 字段 | 类型 | 可用率 | -1/0 处理 | 用途 |
|------|------|--------|-----------|------|
| availableDate | string | ~85% | None | 上架时间/新品判定(维18,27,28) |
| lastUpdate | string | ~95% | None | 数据新鲜度 |
| isHazmat | boolean | ~95% | false | 危险品占比(维25) |
| isAdultProduct | boolean | ~95% | false | 成人产品占比(维26) |

### 排名字段

| 字段 | 类型 | 可用率 | -1/0 处理 | 用途 |
|------|------|--------|-----------|------|
| salesRank | integer | ~85% | None(-1/0) | BSR门槛/中位数(维20-21) |
| salesRank30 | integer | ~80% | None(-1/0) | BSR趋势(维31) |
| salesRank90 | integer | ~80% | None(-1/0) | BSR趋势(维31-32) |
| salesRank180 | integer | ~80% | None(-1/0) | BSR趋势/波动度(维31-32) |

### 价格费用字段

| 字段 | 类型 | 可用率 | -1/0 处理 | 用途 |
|------|------|--------|-----------|------|
| price | number | ~90% | None | 价格回退(SERP优先) |
| primePrice | number | ~70% | None | 展示 |
| currency | string | ~95% | "$" | 币种 |
| fbaFees | number | ~70% | None(-1/0) | FBA费用分布(维23) |
| profit | number | ~70% | None(-1/0) | 利润率分布(维22) |
| referralFeePercentage | number | ~70% | None(-1/0) | 佣金率分布(维24) |

### 历史销量字段（history=1 时返回）

| 字段 | 类型 | 可用率 | -1/0 处理 | 用途 |
|------|------|--------|-----------|------|
| monthlySalesUnits | integer | ~75% | None | 当前月销 |
| monthlySalesRevenue | number | ~70% | None | 当前月销额 |
| monthlySalesUnits1MonthAgo | integer | ~70% | None | 月销趋势(维29) |
| monthlySalesUnits2MonthsAgo | integer | ~70% | None | 市场趋势(维30) |
| monthlySalesUnits3MonthsAgo | integer | ~70% | None | 月销趋势(维29,33) |
| monthlySalesUnits4MonthsAgo | integer | ~65% | None | 市场趋势(维30) |
| monthlySalesUnits5MonthsAgo | integer | ~65% | None | 市场趋势(维30) |
| monthlySalesUnits6MonthsAgo | integer | ~65% | None | 月销趋势(维29) |
| monthlySalesUnits7MonthsAgo | integer | ~60% | None | 市场趋势(维30) |
| monthlySalesUnits8MonthsAgo | integer | ~60% | None | 市场趋势(维30) |
| monthlySalesUnits9MonthsAgo | integer | ~60% | None | 市场趋势(维30) |
| monthlySalesUnits10MonthsAgo | integer | ~55% | None | 市场趋势(维30) |
| monthlySalesUnits11MonthsAgo | integer | ~55% | None | 市场趋势(维30) |
| monthlySalesUnits12MonthsAgo | integer | ~50% | None | 月销趋势(维29) |

### 类目字段

| 字段 | 类型 | 可用率 | -1/0 处理 | 用途 |
|------|------|--------|-----------|------|
| rootCategory | integer | ~85% | None | 展示 |
| categoryTree | string | ~85% | None | 类目分布(维15) |
| categoryTreeId | string | ~85% | None | 展示 |
| subcategories | array | ~80% | None | 类目分布(维15) |

### 规格字段

| 字段 | 类型 | 可用率 | -1/0 处理 | 用途 |
|------|------|--------|-----------|------|
| packageHeight | integer | ~70% | None(-1/0) | 展示 |
| packageLength | integer | ~70% | None(-1/0) | 展示 |
| packageWidth | integer | ~70% | None(-1/0) | 展示 |
| packageDimensions | string | ~70% | None | 展示 |
| packageQuantity | integer | ~60% | None(-1/0) | 展示 |
| packageWeight | string | ~70% | None | 展示 |
| weight | string | ~60% | None | 展示 |
| itemHeight | integer | ~65% | None(-1/0) | 展示 |
| itemLength | integer | ~65% | None(-1/0) | 展示 |
| itemWidth | integer | ~65% | None(-1/0) | 展示 |
| dimensionsType | string | ~60% | None | 展示 |
| dimension | string | ~60% | None | 展示 |

### 图片字段

| 字段 | 类型 | 可用率 | -1/0 处理 | 用途 |
|------|------|--------|-----------|------|
| imageUrl | string | ~95% | None | 主图 |
| productImageUrls | array | ~80% | None | 图片列表 |
| asinUrl | string | ~95% | None | 详情页链接 |
| urlSlug | string | ~85% | None | URL slug |

## SERP vs Keepa 字段优先级

| 字段 | SERP | Keepa | 优先级 |
|------|------|-------|--------|
| price | extractedPrice | price | SERP > Keepa |
| monthlySalesUnits | monthlySalesUnits | monthlySalesUnits | SERP > Keepa |
| rating | rating | rating | SERP > Keepa |
| ratings | ratings | ratings | SERP > Keepa |
| title | title | title | SERP(完整) > Keepa |
| imageUrl | imageUrl | imageUrl | SERP > Keepa |
| brand | (空) | brand | Keepa only |
| fulfillment | (空) | fulfillment | Keepa only |
| availableDate | (空) | availableDate | Keepa only |
| salesRank | (无) | salesRank | Keepa only |
| profit | (无) | profit | Keepa only |
| fbaFees | (无) | fbaFees | Keepa only |

## 无效值处理规则

Keepa API 中 `-1` 和 `0` 通常表示数据不可用。`batch_keepa_fetch.py` 的 `_normalize_value()` 会将这些值转为 `None`。

| 原始值 | 转换后 | 说明 |
|--------|--------|------|
| -1 | None | 不可用 |
| 0 | None | 不可用（数值字段） |
| "-1" | None | 字符串型不可用 |
| "0" | None | 字符串型不可用 |
| "" | None | 空字符串 |
| null | None | 空值 |
