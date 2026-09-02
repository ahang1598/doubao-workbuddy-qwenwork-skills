# 字段汇总表

## S1 Keepa 输出字段

| 字段 | 类型 | 来源 | 说明 |
|------|------|------|------|
| asin | string | keepa | ASIN |
| title | string | keepa | 标题 |
| brand | string | keepa | 品牌 |
| price | float | keepa | 售价($) |
| fbaFees | float | keepa | FBA配送费($) |
| referralFeePercentage | float | keepa | 佣金比例(%) |
| salesRank | int | keepa | BSR排名 |
| rating | float | keepa | 评分 |
| imageUrl | string | keepa | 主图URL |
| categoryTree | string | keepa | 类目树 |
| packageLength | int | keepa | 包装长(mm) |
| packageWidth | int | keepa | 包装宽(mm) |
| packageHeight | int | keepa | 包装高(mm) |
| packageWeight | int | keepa | 包装重量(g) |

## S2 1688 输出字段

| 字段 | 类型 | 来源 | 说明 |
|------|------|------|------|
| offerId | string | 1688 | 货号 |
| title | string | 1688 | 标题 |
| price | float | 1688 | 价格(¥) |
| salesQuantity | int | 1688 | 月销量 |
| repurchaseRate | string | 1688 | 复购率 |

## S3 极目输出字段

| 字段 | 类型 | 来源 | 说明 |
|------|------|------|------|
| returnRateAnnual | float | jiimore | 年退货率(0-1) |
| acos | float | jiimore | ACoS(数值) |
| sponsoredProductsPercentageNow | float | jiimore | 广告占比(0-1) |
| nicheTACoS | float | S3计算 | = acos/100 × sponsored% |

## S4 净利润输出字段

| 字段 | 类型 | 来源 | 说明 |
|------|------|------|------|
| cost_1688 | float | S4计算 | 1688成本(USD) |
| fba_fees | float | S1 | FBA配送费 |
| referral_fee | float | S4计算 | 佣金 = 售价×佣金率/100 |
| ad_cost | float | S4计算 | 广告费 = 售价×TACoS |
| cogs | float | S4计算 | COGS = 1688成本+头程 |
| refund_admin_fee | float | S4计算 | 退款管理费 = 佣金×20% |
| disposal_fee | float | 参数 | 弃置费 |
| single_return_loss | float | S4计算 | 单笔退货亏损 |
| expected_return_loss | float | S4计算 | 预期退货损失 = 退货率×单笔亏损 |
| storage_fee | float | S4计算 | 月度仓储费 |
| inbound_placement_fee | float | 参数 | 入库配置费 |
| total_cost | float | S4计算 | 总成本(11项之和) |
| net_profit | float | S4计算 | 净利润 = 售价-总成本 |
| net_margin | float | S4计算 | 净利润率 = 净利润/售价×100 |
