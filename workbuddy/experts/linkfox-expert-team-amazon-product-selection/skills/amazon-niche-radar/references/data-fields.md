# 数据字段汇总

## S1 输出

| 字段 | 来源 | 说明 |
|------|------|------|
| Top ASIN | amazon-search products（sponsored=false，按 monthlySalesUnits 降序取第一） | 销量最高非广告商品，同时用于 SIF 反查和 S6 深度拆解 |
| 精准关键词集合 | sif-asin-keywords (isMainKw/isAccurateKw=true) | 按搜索量降序 |
| 种子词 | 精准关键词集合[0] | 搜索量最大的精准词 |

## S2 输出

| 字段 | 来源 | 说明 |
|------|------|------|
| nodeIdPath | amazon-category-lookup | 类目节点路径 |
| 已验证 niche 列表 | jiimore data[] × SIF isMainKw/isAccurateKw 交叉匹配 | 与 SIF 标签词匹配上的 niche，每个含完整指标 |
| 全部 nicheTitle 列表 | jiimore data[].nicheTitle + translationZh | 展示给用户的全部细分市场选项 |

## S3 输出 — 极目 (jiimore)

| 字段 | 说明 |
|------|------|
| searchVolumeWeekly | 周搜索量 |
| searchVolumeQuarterly | 季度搜索量 |
| searchVolumeGrowthWeekly | 周搜索量增长率 |
| searchVolumeGrowthQuarterly | 季度搜索量增长率 |
| unitsSoldWeekly | 周销量 |
| unitsSoldQuarterly | 季度销量 |
| top5BrandsClickShare | Top5 品牌点击份额 |
| top5ProductsClickShare | Top5 商品点击份额 |
| brandCount | 品牌数 |
| avgBrandAgeNow | 平均品牌年龄 |
| newProductsLaunchedSemiannual | 半年新品上架数 |
| successfulLaunchedSemiannual | 半年新品成功数 |
| launchRateSemiannual | 新品成功率 |
| cpc{low/medium/high} | CPC 三档 |
| acos | ACoS |
| breakEvenRatio | 盈亏平衡比 |
| profitMarginGt50PctSkuRatio | 毛利率>50%的SKU占比 |
| returnRateAnnual | 年退货率 |
| avgPrice / minimumPrice / maximumPrice | 均价/最低价/最高价 |

## S3 输出 — 卖家精灵 (sellersprite-market-statistics)

| 字段 | 说明 | 报告章节 |
|------|------|---------|
| avgRevenue | 月均销售额（每商品） | 4.1 市场规模 |
| avgUnits | 月均销量（每商品） | 4.1 市场规模 |
| products | 样品商品数 | 4.1 市场规模 |
| brands | 品牌数 | 4.1 市场规模 |
| sellers | 卖家数 | 4.1 市场规模 |
| avgSellers | 平均每商品卖家数（竞争密度） | 4.1 市场规模 |
| firstShelfDate | 首次上架日期 | 4.1 市场规模 |
| lastShelfDate | 最近上架日期 | 4.1 市场规模 |
| avgWeight / baseAvgWeight | 平均重量（磅/克） | 4.1 市场规模 |
| avgVolume / baseAvgVolume | 平均体积（in³/cm³） | 4.1 市场规模 |
| hlProducts | 头部样本数（=10） | 4.2 头部集中度 |
| hlAvgUnits | 头部月均销量 | 4.2 头部集中度 |
| hlAvgRevenue | 头部月均销售额 | 4.2 头部集中度 |
| hlAvgPrice | 头部平均价格 | 4.2 头部集中度 |
| hlAvgRating | 头部平均评分 | 4.2 头部集中度 |
| hlAvgRatings | 头部平均评论数 | 4.2 头部集中度 |
| hlAvgRatingsCv | 头部月评论增长 | 4.2 头部集中度 |
| hlAvgBsr | 头部平均 BSR | 4.2 头部集中度 |
| newProducts / newProductProportion | 新品数/新品占比 | 4.3 新品表现 |
| newAvgUnits | 新品月均销量 | 4.3 新品表现 |
| newAvgRevenue | 新品月均销售额 | 4.3 新品表现 |
| newAvgPrice | 新品平均价格 | 4.3 新品表现 |
| newAvgRating | 新品平均评分 | 4.3 新品表现 |
| newAvgRatings | 新品平均评论数 | 4.3 新品表现 |
| maxNewRatings | 新品最大评论数 | 4.3 新品表现 |
| minNewRatings | 新品最小评论数 | 4.3 新品表现 |
| avgPrice | 类目平均价格 | 4.4 竞争门槛 |
| avgRating | 类目平均评分 | 4.4 竞争门槛 |
| avgRatings | 类目平均评论数 | 4.4 竞争门槛 |
| avgRatingsCv | 月评论增长（评论追赶难度） | 4.4 竞争门槛 |
| avgBsr | 类目平均 BSR | 4.4 竞争门槛 |
| avgProfit | 平均毛利率 | 4.4 竞争门槛 |
| avgSellers | 平均每商品卖家数 | 4.4 竞争门槛 |
| avgWeight / avgVolume | 平均重量/体积 | 4.4 竞争门槛 |

## S3 输出 — 前台搜索 (amazon-search × 3 页)

| 字段 | 说明 |
|------|------|
| asin | 商品 ASIN |
| brand | 品牌 |
| title | 标题 |
| extractedPrice | 解析价格 |
| rating / ratings | 评分/评论数 |
| monthlySalesUnits / monthlySalesRevenue | 月销量/月销售额 |
| fulfillment | 配送方式 (FBA/AMZ/FBM) |
| sellerNation | 卖家国别 |
| availableDate | 上架日期 |
| options | 变体选项 |
| sponsored | 是否广告 |
| position | 搜索位置 |

## S3 输出 — ABA Part A (aba-intelligent-query，种子词深度查询)

| 字段 | 说明 | 报告章节 |
|------|------|---------|
| reportstartdate | 报告周日期 | 5.2 Part B |
| searchfrequencyrank | 搜索频率排名 | 5.2 Part B |
| clickedasin | 点击 ASIN | 5.2 Part B |
| clickeditemname | 点击商品名称 | 5.2 Part B |
| clicksharerank | 点击排名（1=第一） | 5.2 Part B |
| clickShare | 点击份额（0~1） | 5.2 Part B |
| conversionShare | 转化份额（0~1） | 5.2 Part B |

## S3 输出 — ABA Part B (aba-intelligent-query，5 关键词排名对比)

| 字段 | 说明 | 报告章节 |
|------|------|---------|
| searchterm | 搜索词 | 5.1 Part A |
| reportstartdate | 报告周日期 | 5.1 Part A |
| searchFrequencyRank | 搜索频率排名 | 5.1 Part A |

## S4 派生指标 — ABA Part A (5 关键词)

| 指标 | 计算方式 |
|------|---------|
| 排名趋势序列 | 每个关键词 26 周的 searchFrequencyRank 数组 |
| 排名波动率 CV | std(ranks) / mean(ranks) × 100 |
| 趋势方向 | (后13周均值 - 前13周均值) / 前13周均值 × 100 |
| 周环比改善/恶化次数 | 逐周比较变化方向统计 |
| 最佳/最差排名 | min(ranks) / max(ranks) |
| 热度梯队 | 按最新排名分梯队 |

## S3 输出 — Google Trends (google-trend-get-trend-by-keys，5 词 × 5 年)

| 字段 | 说明 | 报告章节 |
|------|------|---------|
| keyword | 查询关键词 | 6. Google Trends |
| timeRange | 周日期 | 6. Google Trends |
| value | 搜索热度值（0-100 归一化） | 6. Google Trends |

## S4 派生指标 — Google Trends

| 指标 | 计算方式 |
|------|---------|
| 5 年周维度趋势序列 | 每个关键词 262 周的 value 数组 |
| 年度均值 | 按年分组求 value 平均 |
| 5 年趋势方向 | (末年均值 - 首年均值) / 首年均值 × 100 |
| Google Trends vs ABA 交叉验证 | 对比 GT 趋势方向与 ABA 趋势方向，判定一致/分歧/无法对比 |

## S3 输出 — 社媒验证 (tsearch-search，条件触发)

| 字段 | 说明 | 报告章节 |
|------|------|---------|
| title | 搜索结果标题 | 6. Google Trends（社媒验证子节） |
| url | 来源 URL | 6. Google Trends（社媒验证子节） |
| content | 页面内容摘要 | 6. Google Trends（社媒验证子节） |
| score | 相关性评分 | 6. Google Trends（社媒验证子节） |

## S3 输出 — 商业洞察报告 (amazon-opportunity-report-by-keyword)

| 字段 | 说明 | 报告章节 |
|------|------|---------|
| stdout | Markdown 格式的六维分析报告全文 | 8. 商业洞察报告 |
| errcode | 200=已形成细分赛道，其他=未形成 | 8. 商业洞察报告 |
| costTime | 查询耗时 | — |
| costToken | 消耗 token | — |

### 商业洞察报告六维内容

| 维度 | 关键内容 | 交叉验证对象 |
|------|---------|-------------|
| 市场潜力 | 年搜索量、YoY 增长率、近90日趋势、销售额、均价、缺货率 | Google Trends 年度均值变化 |
| 竞争结构 | 在售产品数、品牌数(YoY变化)、Top5 Click Share、新品上线数 | sellersprite 品牌/卖家数、极目新品成功率 |
| 产品特征 | 决胜属性(标配)+溢价属性(差异化) | 前台搜索产品形态分类 |
| 评价质量 | 平均评分、差评痛点分布(设备失效/电池/说明书等) | 前台搜索评分值分布、低分高销量竞品 |
| 客户画像 | 买家年龄段、收入区间、使用场景 | 前台搜索产品形态分类、极目 niche categorieList |
| 定价分析 | 价格带分布、甜蜜区、空白价格段 | 前台搜索价格分布分桶 |

## S6 输出 — Keepa 历史时序 (keepa-product-series)

| 字段 | 说明 | 报告章节 |
|------|------|---------|
| buyboxPrice | Buy Box 价格历史 [{time, value}] | 9.1 Keepa 解读 |
| bsrSub | 子类目 BSR 历史 [{categoryName, points}] | 9.1 Keepa 解读 |
| rating | 星级评分历史 [{time, value}] | 9.1 Keepa 解读 |
| ratingCount | 评论数历史 [{time, value}] | 9.1 Keepa 解读 |
| monthlySold | 月销量历史 [{time, value}] | 9.1 Keepa 解读 |

解读规范见 `references/keepa-interpretation.md`（8 维度）。

## S6 输出 — SIF 流量概览 (sif-asin-summary)

| 字段 | 说明 | 报告章节 |
|------|------|---------|
| totalExposureScore / Prev | 总曝光得分（及上期） | 9.2 SIF 流量解读 |
| naturalSearchExposureScore / Ratio / Prev | 自然搜索曝光（得分/占比/上期） | 9.2 SIF 流量解读 |
| sponsoredProductsExposureScore / Ratio / Prev | SP 广告曝光 | 9.2 SIF 流量解读 |
| amazonsChoiceExposureScore / KeywordCount / In / Out | AC 标签曝光 | 9.2 SIF 流量解读 |
| editorialRecommendationsExposureScore / Ratio | 编辑推荐曝光 | 9.2 SIF 流量解读 |
| topRatedExposureScore / Ratio | Top Rated 曝光 | 9.2 SIF 流量解读 |
| totalTrafficKeywordCount / Prev / In / Out | 总流量词数 | 9.2 SIF 流量解读 |
| naturalSearchKeywordCount / In / Out | 自然搜索词数 | 9.2 SIF 流量解读 |
| sponsoredProductsKeywordCount | SP 广告词数 | 9.2 SIF 流量解读 |
| isVariantProduct | 是否变体 | 9.2 SIF 流量解读 |

解读规范见 `references/sif-asin-interpretation.md`（8 维度）。

## S6 输出 — SIF 关键词反查 (sif-asin-keywords)

| 字段 | 说明 | 报告章节 |
|------|------|---------|
| keyword | 流量关键词 | 9.3 关键词反查 |
| weeklySearchVolume | 周搜索量 | 9.3 关键词反查 |
| trafficShare | 流量份额 | 9.3 关键词反查 |
| naturalTrafficShare | 自然流量份额 | 9.3 关键词反查 |
| productNaturalRank | 自然排名 | 9.3 关键词反查 |
| trafficCharacteristicMarkers | 流量标签 (isMainKw/isAccurateKw) | 9.3 关键词反查 |
| clickToPurchaseConversionRate | 点击转化率 | 9.3 关键词反查 |
| displayPositionTypes | 展示位置类型 | 9.3 关键词反查 |
| naturalRankDisplay | 自然排名展示 | 9.3 关键词反查 |

## S4 派生指标 — ABA Part B (种子词 Top ASIN)

| 指标 | 计算方式 |
|------|---------|
| Top3 点击集中度 | 每周 clicksharerank=1/2/3 的 clickShare 之和 |
| Top3 转化集中度 | 每周 clicksharerank=1/2/3 的 conversionShare 之和 |
| 点击-转化效率比 | conversionShare / clickShare × 100% |
| 头部 ASIN 更替频率 | 26 周内 clicksharerank=1 的不同 ASIN 数量 |

## S4 派生指标

| 指标 | 计算方式 |
|------|---------|
| 年化销售额 | avgRevenue × products × 12 |
| 年化销量 | avgUnits × products × 12 |
| 头部集中倍数 | hlAvgUnits ÷ avgUnits |
| CR3/CR5 | Top 3/5 品牌月销量 ÷ 总月销量 |
| 价格分布分桶 | 按 extractedPrice 分 6 桶 |
| 评分分布分桶 | 按 rating 分 4 桶 |
| 新品占比 | 半年内上架商品数 ÷ 总商品数 |
| 配送/卖家国别占比 | 逐商品统计 |
| 产品形态分类 | 按标题关键词判定 |
