# 业务流程详述

## 业务目标

输入一张商品主图或商品 URL，**先确认目标平台与站点**，按用户提供的平台找竞品，**按平台分组输出**选品数据表——每个平台只显示它能抓到的列。支持 5 个平台。

- **Amazon**：原生以图搜图。
- **Walmart / TikTok / eBay / Ozon**：无图搜，先 AI 识图提取特征 + 搜索词，再按关键词搜索；Ozon 须俄语词。

## 输入参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| imageUrl | string | 二选一 | 公开商品图片 URL |
| productUrl | string | 二选一 | 商品页 URL；Step 0 识别来源平台站点并取其主图 |
| platform | string | 条件必填 | 目标平台（单选）；未提供时 Step 0 询问 |
| site | string | 条件必填 | 该平台站点（单选）；未提供时 Step 0 询问 |
| top_n | integer | 否 | 返回条数，默认 10 |
| refineWithSorftime | boolean | 否 | 仅 Amazon 销量精修，默认 false |

## 步骤拆解

### Step 0：确认平台 + 站点（前置，按输入类型分两条路径）
- **平台与站点均为单选。**
- **站点规则**：单站点平台（Walmart=us、Ozon=ru）自动采用并告知用户；多站点平台（Amazon 8 站 / TikTok 15 区 / eBay 16 站）**必须让用户从列表选一个，不得默认**。
- **情形 A 给图片**：问目标平台（Amazon/Walmart/TikTok/eBay/Ozon，单选）→ 按站点规则确认站点。
- **情形 B 给商品 URL**：先识别链接的来源平台站点（amazon.com→Amazon/us、walmart.com→Walmart/us、ozon.ru→Ozon/ru、ebay.de→eBay/de…）→ **即使已识别出平台站点，也必须回显给用户并取得明确"是/否"确认，不得自动跳过直接搜索**："是否以此平台站点为目标"：是→用该站点并取该商品主图作 imageUrl；否→问目标平台与站点（单选）。
- 追问统一走 `linkfox-form-protocol`；沉默/"都行"不算确认。
- 产出：confirmed `platform` + `site`（+ 情形 B 解析出的 imageUrl）→ Step 2 路由。

### Step 1：识图提取特征与搜索词
- 工具：`linkfox-multimodal-recognize-image`。
- requirement 输出 JSON：`category` / `features` / `search_query`(英) / `search_query_ru`(俄)。
- 产出：search_query → Walmart/TikTok/eBay；search_query_ru → Ozon；product_description → 报告参考行。

### Step 2：按平台搜索（每平台只取可抓字段）
| 平台 | 工具 | 关键入参 | 直出字段 |
|------|------|---------|---------|
| Amazon | `linkfox-amazon-search-by-image` | imageUrl, amazonDomain, aggregateByKeepaData=true | salesRank/monthlySalesUnits/monthlySalesRevenue/fulfillment/categoryTree/weight/dimension |
| Walmart | `linkfox-walmart-search` | keyword=search_query, sort=best_seller | usItemId/title/price/image/shipping |
| TikTok | `linkfox-fastmoss-product-search` | keyword=search_query, region, orderField=total_units_sold | price/totalSaleCnt/totalSaleGmvAmt/categoryName |
| eBay | `linkfox-ebay-search` | keyword=search_query, ebayDomain | price/salesQuantity/shipping/sellerName |
| Ozon | `linkfox-mpstats-ozon-product-search` | keyword=search_query_ru | productId/title/brand/image（仅身份） |

### Step 3：补全选品数据
| 平台 | 工具 | 入参 | 补全字段 |
|------|------|------|---------|
| Walmart | `linkfox-wallysmarter-product-detail` | productId(整数), 逐条 | salesEstimate/revenue/departmentName/fulfillmentType |
| Ozon | `linkfox-mpstats-ozon-product-detail` | productIds(批量≤100) | price/monthlySalesUnits/monthlySalesRevenue/rating/nicheName |
| Amazon(可选) | `linkfox-sorftime-product-detail`(+step_3_5_junglescout) | asin≤10/批 | 精修销量/BSR |

### Step 4：按平台自适应列 + 每平台 Top N → 交付
- 脚本：`scripts/step_4_merge_rank.py`。
- 每平台只保留其列（见 SKILL.md 列表），各自按销量降序取 Top N，汇成一个 `skill-output` envelope（带 `platformColumns`）。
- 销售额优先接口直出，缺失按 价格×销量。

## 报告诉求
按平台分组的竞品表 + 参考商品 + 数据来源 + 局限性。样式交 `linkfox-report-generator`。

## 无效输入与异常（详见 SKILL.md「Bad Cases」）
- 无图无链接、无效图片、无效/不支持平台的链接、不支持平台、站点不匹配、识图失败、搜索为空 → 一律用 `linkfox-form-protocol` 提示用户给正确输入，不静默失败、不编造数据。

## 已知局限
- 图搜仅 Amazon；其余靠关键词召回。
- BSR/重量/尺寸仅 Amazon；配送无 TikTok/Ozon；eBay 无品类/销售额（已售代销量）。
- Ozon 须俄语词 + 两步；销量口径跨平台不一致（见 SKILL.md）。
