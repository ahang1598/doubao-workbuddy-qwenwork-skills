# 数据字段汇总

## Step 1（linkfox-multimodal-recognize-image）
| 字段 | 说明 |
|------|------|
| category | 品类 |
| features | 特征列表 |
| search_query | 2–5 词英文搜索短语（Walmart/TikTok/eBay 用） |
| search_query_ru | 俄语搜索短语（Ozon 用） |

> 返回在 `text`/`stdout` 字段里含 JSON 代码块，需解析提取。

## Step 2 各平台直出字段

**Amazon**（`amazon-search-by-image`，aggregateByKeepaData=true）：asin / title / brand / price / currency / imageUrl / `salesRank`(BSR) / `monthlySalesUnits`(销量) / `monthlySalesRevenue`(销售额) / `fulfillment`(配送) / `categoryTree`(品类) / `weight`(重量,克) / `dimension`(尺寸,毫米)。

**Walmart**（`walmart-search`）：usItemId / title / price / currency / imageUrl / twoDayShipping·freeShipping·freeShippingWithWalmartPlus(配送)。

**TikTok**（`fastmoss-product-search`）：productId / title / price / currency / imageUrl / region(站点) / `totalSaleCnt`(销量) / `totalSaleGmvAmt`(销售额=GMV) / categoryName(品类)。

**eBay**（`ebay-search`）：productId / title / price / currency / imageUrl / `salesQuantity`(已售数量) / shipping(配送) / sellerName(卖家)。

**Ozon**（`mpstats-ozon-product-search`）：productId(SKU) / title / brand / imageUrl（**仅身份，无业务指标**）。

## Step 3 补全字段

**Walmart**（`wallysmarter-product-detail`，按 productId 整数）：`salesEstimate`(销量) / `revenue`(销售额) / `departmentName`(品类) / `fulfillmentType`(WFS|MARKETPLACE)。

**Ozon**（`mpstats-ozon-product-detail`，按 productIds 批量）：`price` / `monthlySalesUnits`(销量) / `monthlySalesRevenue`(销售额) / `rating`(评分) / `nicheName`(品类,取叶子) / currency。

**Amazon 可选**（`sorftime-product-detail` + step_3_5_junglescout）：精修销量 / BSR。

## Step 4 各平台输出列（自适应，单一真相源见脚本 `PLATFORM_COLUMNS`）

| 平台 | imageUrl | title | site | id | price | category | bsr | unitsSold | revenue | fulfillment | weight | dimensions | rating | seller | soldQuantity |
|------|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| Amazon | ✅ | ✅ | ✅ | asin | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | | | |
| Walmart | ✅ | ✅ | ✅ | itemId | ✅ | ✅ | | ✅ | ✅ | ✅ | | | | | |
| TikTok | ✅ | ✅ | ✅ | itemId | ✅ | ✅ | | ✅ | ✅(GMV) | | | | | | |
| eBay | ✅ | ✅ | ✅ | itemId | ✅ | | | | | ✅ | | | | ✅ | ✅ |
| Ozon | ✅ | ✅ | | itemId(SKU) | ✅ | ✅ | | ✅ | ✅ | | | | ✅ | | |

> 空白 = 该平台接口不提供该列，输出中**不写该字段**（非 N/A）。字段映射与 envelope 见 `references/output-schema.md`。
