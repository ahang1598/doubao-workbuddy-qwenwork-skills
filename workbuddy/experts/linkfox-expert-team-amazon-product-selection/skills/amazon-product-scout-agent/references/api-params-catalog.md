# 卖家精灵选产品 API 参数目录

本文件列出 `linkfox-sellersprite-product-search` 的全部参数，供 `product_scout_agent.py` 的 `--suggest` 命令和 CLAUDE.md 参考。

## 搜索与关键词

| 参数 | 类型 | 说明 | CLI 参数 |
|------|------|------|---------|
| keyword | string | 搜索关键词 | `--keyword` |
| matchType | int | 1=词组匹配, 2=模糊匹配, 3=精准匹配 | - |
| excludeKeywords | string | 排除关键词 | - |
| marketplace | string | 站点: US/UK/DE/FR/JP/CA/IT/ES/MX/IN | `--marketplace` |
| nodeLabel | string | 类目名称 | - |
| nodeIdPath | string | 类目节点ID | - |
| filterSubNode | bool | 是否筛选子类目 | - |

## 价格与利润

| 参数 | 类型 | 说明 | CLI 参数 |
|------|------|------|---------|
| minPrice | number | 最低价格 | `--min-price` |
| maxPrice | number | 最高价格 | `--max-price` |
| minProfit | number | 最小毛利率%(1-100) | - |
| maxProfit | number | 最大毛利率%(1-100) | - |
| minRevenue | number | 最低月销售额 | - |
| maxRevenue | number | 最高月销售额 | - |
| minFba | number | 最低FBA运费 | - |
| maxFba | number | 最高FBA运费 | - |

## 销量与排名

| 参数 | 类型 | 说明 | CLI 参数 |
|------|------|------|---------|
| minUnits | int | 最低月销量 | `--min-units` |
| maxUnits | int | 最高月销量 | `--max-units` |
| minAmzUnit | int | 最低子体30日销量(仅nearly) | - |
| maxAmzUnit | int | 最高子体30日销量(仅nearly) | - |
| minUnitsGrowthRate | number | 月销量最低增长率% | `--min-units-growth-rate` |
| maxUnitsGrowthRate | number | 月销量最高增长率% | - |
| minBsr | int | 大类BSR最低排名 | `--min-bsr` |
| maxBsr | int | 大类BSR最高排名 | `--max-bsr` |
| minBsrGrowthRate | number | BSR最低增长率% | `--min-bsr-growth-rate` |
| maxBsrGrowthRate | number | BSR最高增长率% | `--max-bsr-growth-rate` |
| minBsrGrowthCount | int | BSR最低增长数 | - |
| maxBsrGrowthCount | int | BSR最高增长数 | - |
| minSubNodeBsrRank | int | 子类BSR最低排名(需filterSubNode) | - |
| maxSubNodeBsrRank | int | 子类BSR最高排名(需filterSubNode) | - |

## 评分与评论

| 参数 | 类型 | 说明 | CLI 参数 |
|------|------|------|---------|
| minRating | number | 最低评分(0-5) | `--min-rating` |
| maxRating | number | 最高评分(0-5) | `--max-rating` |
| minRatings | int | 最低评分数(0-10000) | `--min-ratings` |
| maxRatings | int | 最高评分数(0-10000) | `--max-ratings` |
| minRatingsGrowthCount | int | 最低月新增评分数 | - |
| maxRatingsGrowthCount | int | 最高月新增评分数 | - |
| minListingQualityScore | number | 最低Listing质量分 | - |
| maxListingQualityScore | number | 最高Listing质量分 | - |

## 商品属性

| 参数 | 类型 | 说明 | CLI 参数 |
|------|------|------|---------|
| minVariations | int | 最低变体数 | - |
| maxVariations | int | 最高变体数 | `--max-variations` |
| minWeights | number | 最小重量 | `--min-weight` |
| maxWeights | number | 最大重量 | `--max-weight` |
| weightUnit | string | 重量单位: g/kg/oz/lb | `--weight-unit` |
| dimensionType | string | 包装尺寸类型(站点特定) | - |
| minSellers | int | 最小卖家数 | `--min-sellers` |
| maxSellers | int | 最大卖家数 | `--max-sellers` |

## 徽章与配送

| 参数 | 类型 | 说明 | CLI 参数 |
|------|------|------|---------|
| badgeBestSeller | string | Best Seller: Y/N/空 | `--badge-best-seller` |
| badgeAmazonsChoice | string | Amazon's Choice: Y/N/空 | `--badge-amazons-choice` |
| badgeNewRelease | string | New Release: Y/N/空 | `--badge-new-release` |
| fulfillment | string | 配送: AMZ/FBA/FBM(逗号分隔) | `--fulfillment` |
| showVariation | string | 显示变体: Y/N | - |

## 卖家与品牌

| 参数 | 类型 | 说明 | CLI 参数 |
|------|------|------|---------|
| sellerNation | string | 卖家国籍: CN/HK/US等 | `--seller-nation` |
| includeSellers | string | 包含卖家 | - |
| excludeSellers | string | 排除卖家 | - |
| includeBrands | string | 包含品牌 | - |
| excludeBrands | string | 排除品牌 | - |

## 上架与分页

| 参数 | 类型 | 说明 | CLI 参数 |
|------|------|------|---------|
| hideUnlistedProduct | bool | 隐藏下架商品(默认true) | - |
| listedWithinLastMonths | int | 上架月数: 1/3/6/12/24 | `--listed-within-months` |
| page | int | 页码(从1开始) | - |
| size | int | 每页条数(10-100) | - |

## 排序字段（16种）

| 字段 | 说明 |
|------|------|
| total_units | 月销量 |
| total_amount | 月销售额 |
| bsr_rank | BSR排名 |
| price | 价格 |
| rating | 评分值 |
| reviews | 评分数 |
| profit | 毛利率 |
| reviews_rate | 留评率 |
| available_date | 上架时间 |
| questions | 问答数 |
| total_units_growth | 销量增长率 |
| total_amount_growth | 销售额增长率 |
| reviews_increasement | 新增评论数 |
| bsr_rank_cv | BSR波动系数 |
| bsr_rank_cr | BSR变化率 |
| amz_unit | 子体销量 |

排序方向: `desc` = `"true"` 降序, `"false"` 升序

## 数据快照

| 参数 | 类型 | 说明 |
|------|------|------|
| dataSnapshotMonth | string | `nearly`(近30天实时) 或 `yyyyMM`(历史月快照) |

## 站点包装尺寸类型

### US (美国)
SS=小号标准, LS=大号标准, SO=小号大件, MO=中号大件, LO=大号大件, LB=大号大件LB, SP=特殊大件, O=其他

### UK/DE/FR/IT/ES (欧洲)
SL=小号信封, NL=标准信封, LL=大号信封, ELL=超大号信封, SM=小包裹, SD=标准包裹, SB=小号大件, NB=标准大件, LB=大号大件, SPO=特殊大件, O=其他

### JP (日本)
SM=小号, ST=标准, OV=大件, SS=超大尺寸, O=其他

### CA (加拿大)
EN=信封装, ST=标准, SO=小号大件, MO=中号大件, LO=大号大件, SP=特殊大件, O=其他

### MX/IN (墨西哥/印度)
同 US 标准

## 站点货币

| 站点 | 货币 | 符号 |
|------|------|------|
| US | USD | $ |
| UK | GBP | £ |
| DE/FR/IT/ES | EUR | € |
| JP | JPY | ¥ |
| CA | CAD | C$ |
| MX | MXN | MX$ |
| IN | INR | ₹ |
