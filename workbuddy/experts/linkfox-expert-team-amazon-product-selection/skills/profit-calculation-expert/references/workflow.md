# 业务流程详述

## 业务目标

输入任意数量 ASIN，自动拉取三大数据源（Keepa + 1688 + 极目），用全量成本模型计算净利润，输出 HTML 报告。

## 输入参数

| 参数 | 类型 | 默认 | 必填 | 说明 |
|------|------|------|------|------|
| asins | string | — | 是 | 逗号分隔的 ASIN 列表 |
| domain | int | 1 | 否 | 亚马逊站点 ID |
| exchangeRate | float | 7.2 | 否 | CNY→USD 汇率 |
| fbaHeadCost | float | 3.0 | 否 | FBA 头程（美元/件） |
| adTACoS | float | 10.0 | 否 | 回退 TACoS（%） |
| returnRate | float | 15.0 | 否 | 回退退货率（%） |
| disposalFee | float | 0.50 | 否 | 弃置费（美元/件） |
| storageRate | float | 0.87 | 否 | 仓储费率（美元/cu.ft） |
| inboundPlacementFee | float | 0.40 | 否 | 入库配置费（美元/件） |

## 步骤拆解

| # | 动作 | 上游 | 下游 | 所需字段 |
|---|------|------|------|----------|
| S1 | Keepa 批量拉取 | 输入参数 | S2(imageUrl), S3(categoryTree), S4(费用) | price, fbaFees, referralFeePercentage, imageUrl, categoryTree, packageDimensions |
| S2 | 1688 以图搜图 | S1(imageUrl) | S4(1688成本) | offerId, title, price(¥), salesQuantity |
| S3 | 极目市场指标 | S1(categoryTree) | S4(退货率+TACoS) | returnRateAnnual, acos, sponsoredProductsPercentageNow |
| S4 | 净利润核算 | S1+S2+S3 | S5(利润数据) | 11项成本 + 净利润 + 净利润率 |
| S5 | HTML 报告 | S4 | 用户交付 | 全部字段 |

## 成本项清单（11项）

1. 1688 采购成本(USD) = 1688价格(¥) / 汇率
2. FBA 配送费 = fbaFees (Keepa)
3. 亚马逊佣金 = 售价 × referralFeePercentage / 100
4. 广告费 = 售价 × nicheTACoS (S3无数据时回退adTACoS)
5. COGS = 1688成本 + FBA头程
6. 退款管理费 = 佣金 × 20%
7. 弃置费 = $0.50
8. 单笔退货亏损 = FBA费 + 退款管理费 + COGS + 弃置费
9. 每件预期退货损失 = 退货率 × 单笔退货亏损
10. 月度仓储费 = (L×W×H mm³ / 28316846.6) × storageRate
11. 入库配置费 = $0.40

净利润 = 售价 - (1+2+3+4+9+10+11+头程)
