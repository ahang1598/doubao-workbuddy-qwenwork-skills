---
name: linkfox-image-competitor-scout
description: 给定一张商品主图或一个商品 URL 链接，先确认一个目标平台与站点，再在该平台找竞品并输出选品数据表。给图片时先问目标平台与站点；给商品链接时先识别其平台站点并问用户是否以此为目标，否则再问目标平台与站点。Amazon 走以图搜图；Walmart/TikTok/eBay/Ozon 先用 AI 多模态识别商品内容与特征、提炼搜索词，再按关键词搜索同类品。适用场景：以图找竞品、按链接找竞品、多平台竞品对标、跨平台选品摸底、图片找货、以图搜货、视觉对标选品、竞品市场摸底。即使用户只说"帮我找这张图的竞品"、"这个链接在别的平台有没有同类"、"图片找货"，没有明说多平台或流程，只要意图是用图片或商品链接跨平台找竞品，也应触发本 skill。
metadata:
  version: v5
---

# 多平台竞品侦察（linkfox-image-competitor-scout）

输入**一张商品主图**或**一个商品 URL 链接**，**先确认一个目标平台与站点**，在该平台找视觉/同类竞品并输出选品数据表。

## 支持的平台与搜索方式


| 平台          | 搜索方式                  | 站点                      |
| ----------- | --------------------- | ----------------------- |
| **Amazon**  | 以图搜图                  | us/uk/de/fr/it/es/jp/in |
| **Walmart** | 识图→关键词搜索 + 详情补全       | us                      |
| **TikTok**  | 识图→关键词搜索              | 15 区域                   |
| **eBay**    | 识图→关键词搜索              | 16 站                    |
| **Ozon**    | 识图→**俄语**关键词搜索 + 详情补全 | ru                      |


**两种搜索路径（务必区分）**：

- **Amazon**：**直接调用以图搜图 skill**（`linkfox-amazon-search-by-image`），用图片找视觉相似的 ASIN，**无需关键词**。
- **Walmart / TikTok / eBay / Ozon**：这些平台**没有图搜能力**，因此先用**大模型识别图片的商品特征、提炼关键词**（`linkfox-multimodal-recognize-image`），**再用关键词在该平台搜索**同类商品（Ozon 用俄语关键词）。

## 适用场景


| 场景      | 说明                                                   |
| ------- | ---------------------------------------------------- |
| 多平台竞品对标 | 一张对标图，横扫 Amazon/Walmart/TikTok/eBay/Ozon 看同类竞品的价格、销量 |
| 视觉对标选品  | 选品前用参考图找各平台同类在售品，判断竞争程度与价格带                          |
| 图片找货    | 采购方给图，验证各平台是否有同款/同类在售及其销量                            |


## 不适用

- 只给关键词而非图片、且只查单平台（直接用对应平台的搜索 skill）。
- 历史价格/BSR 趋势曲线（用 `linkfox-keepa-product-series`）。
- 广告关键词反查（用 `linkfox-sif-asin-keywords`）。

---

## 输入参数


| 参数                 | 类型      | 默认    | 说明                                                                                                       |
| ------------------ | ------- | ----- | -------------------------------------------------------------------------------------------------------- |
| imageUrl           | string  | 二选一   | 商品主图公开 URL（JPG/PNG/WebP/GIF/BMP）。本地图先用 `linkfox-amazon-search-by-image/scripts/upload_image.py` 上传取 URL  |
| productUrl         | string  | 二选一   | 商品页 URL（如 amazon.com/walmart.com/ozon.ru 等的商品链接）。与 `imageUrl` 至少提供一个；给链接时由 Step 0 识别来源平台站点，再取其主图供后续识图/图搜 |
| platform           | string  | 运行时确认 | 目标平台（**单选**）：`amazon`/`walmart`/`tiktok`/`ebay`/`ozon`；**未提供时执行 Step 0 询问**                              |
| site               | string  | 运行时确认 | 该平台的站点（**单选**），如 amazon→`us`、ebay→`ebay.com`、tiktok→`US`、ozon→`ru`                                       |
| top_n              | integer | 10    | 返回条数                                                                                                     |
| refineWithSorftime | boolean | false | 仅 Amazon：用 `linkfox-sorftime-product-detail` 精修销量（默认用 Keepa 估算即可）                                        |


---

## 流水线步骤

### 步骤 0：确认平台与站点

先确认平台、再确认站点——决定该平台走"图搜"还是"识图+关键词搜"。**平台与站点均为单选。** 按用户提供的是图片还是商品链接走不同询问路径。

- **输入**：`imageUrl`（图片）或 `productUrl`（商品链接），及用户透露的平台线索
- **操作**：
  - **情形 A — 提供的是图片**：询问目标平台（单选）→ 再确认该平台的站点（单选）。
  - **情形 B — 提供的是商品 URL 链接**：先从链接识别来源平台与站点（如 `amazon.com`→Amazon/us、`amazon.co.jp`→Amazon/jp、`walmart.com`→Walmart/us、`ozon.ru`→Ozon/ru、`ebay.de`→eBay/de）。**即使已能从链接明确识别出平台与站点，也必须把识别结果回显给用户、取得明确确认后才继续，不得自动跳过直接搜索。** 询问「检测到该链接为 [平台 / 站点]，是否以此为目标？」
    - **是** → 用该平台站点；并取该商品主图作为后续识图/图搜的 `imageUrl`。
    - **否** → 询问目标平台（单选）→ 再确认站点（单选）。
  - 平台单选、站点拍板、是/否确认等所有追问统一走 `linkfox-form-protocol` 产出表单，不自由文本散问；**沉默 / "你看着办" / "都行" 不算确认，必须拿到用户明确的"是/否"**。
- **输出**：确认后的 `platform` 与 `site`；（情形 B）解析出的 `imageUrl`
- **用途**：作为步骤 2 的平台路由与站点参数；情形 B 解析出的主图供步骤 1/2 使用

### 步骤 1：大模型识别图片商品特征 → 关键词

**仅非 Amazon 平台必需**（Walmart/TikTok/eBay/Ozon 靠关键词搜索）；Amazon 走图搜不需要关键词，此步对 Amazon 可选（仅为报告提供"参考商品"描述）。

- **输入**：`imageUrl`
- **操作**：调用 `linkfox-multimodal-recognize-image`，requirement 要求输出 JSON：`category`、`features`、`search_query`（2–5 词英文）、`search_query_ru`（俄语翻译，供 Ozon）
- **输出**：`product_description`、`search_query`、`search_query_ru`
- **用途**：`search_query` 进 Walmart/TikTok/eBay 搜索；`search_query_ru` 进 Ozon 搜索；`product_description` 写报告"参考商品"行（含 Amazon）

### 步骤 2：按平台找竞品

对选定平台执行其对应分支（下表按平台列出搜索方式），结果经 `response_io.py` 落盘。**只取该平台能抓到的字段**（见步骤 4 列表）。

- **Amazon**：`linkfox-amazon-search-by-image`，传 `imageUrl`、`amazonDomain`、`aggregateByKeepaData=true`。**Keepa 聚合直出** `salesRank`(BSR)/`monthlySalesUnits`(销量)/`monthlySalesRevenue`(销售额)/`fulfillment`(配送)/`categoryTree`(品类)/`weight`(重量)/`dimension`(尺寸)。
- **Walmart**：`linkfox-walmart-search`，传 `keyword=search_query`、`sort="best_seller"` → 基础 + ItemId。
- **TikTok**：`linkfox-fastmoss-product-search`，传 `keyword=search_query`、`region`、`orderField="total_units_sold"`、`pageSize=top_n` → 直出 价格/销量/GMV/品类。
- **eBay**：`linkfox-ebay-search`，传 `keyword=search_query`、`ebayDomain` → 直出 价格/已售数量/配送/卖家。
- **Ozon**：`linkfox-mpstats-ozon-product-search`，传 `keyword=search_query_ru` → 仅身份字段（SKU/标题/品牌/图）。
- **输出**：各平台落盘文件
- **用途**：Amazon/TikTok/eBay 字段已够；Walmart/Ozon 的 ID 进步骤 3 补全

### 步骤 3：补全选品数据

- **Walmart**：`linkfox-wallysmarter-product-detail`（按 ItemId 整数，逐条）→ `salesEstimate`(销量)/`revenue`(销售额)/`departmentName`(品类)/`fulfillmentType`(配送)。
- **Ozon**：`linkfox-mpstats-ozon-product-detail`（按 SKU 批量 ≤100）→ `price`/`monthlySalesUnits`(销量)/`monthlySalesRevenue`(销售额)/`rating`(评分)/`nicheName`(品类)。
- **Amazon（可选）**：`refineWithSorftime=true` 时用 `linkfox-sorftime-product-detail` 精修销量；仍缺可用 `scripts/step_3_5_junglescout.py` 兜底。
- **输出**：Walmart/Ozon 的销量/销售额/品类等
- **用途**：进步骤 4 合并

### 步骤 4：按平台自适应列 + Top N → 最终交付

- **输入**：步骤 2/3 该平台落盘文件
- **操作**：运行 `scripts/step_4_merge_rank.py`。**只保留所选平台可抓列**、按销量降序取 Top `top_n`，汇成一个 `skill-output` envelope（`subject=product_list`，每条带 `platform`，并附 `platformColumns`）。销售额优先接口直出，缺失按 `价格×销量` 估算。
- **输出**：该平台 Top N 条；列见下表
- **用途**：最终交付 / 移交报告

**各平台对应输出列**（按所选平台取对应一行）：


| 平台      | 输出列                                     |
| ------- | --------------------------------------- |
| Amazon  | 主图·标题·站点·ASIN·价格·品类·BSR·销量·销售额·配送·重量·尺寸 |
| Walmart | 主图·标题·站点·ItemId·价格·品类·销量·销售额·配送         |
| TikTok  | 主图·标题·区域·productId·价格·品类·销量·销售额(GMV)    |
| eBay    | 主图·标题·站点·productId·价格·已售数量·配送·卖家        |
| Ozon    | 主图·标题·SKU·价格·品类·销量·销售额·评分               |


```bash
python scripts/step_4_merge_rank.py \
  --amazon-search-files <2_amazon_*.json> \
  --walmart-search-files <2_walmart_*.json> --walmart-detail-files <3_walmart_*.json> \
  --tiktok-search-files <2_tiktok_*.json> \
  --ebay-search-files <2_ebay_*.json> \
  --ozon-detail-files <3_ozon_*.json> \
  --top-n 10
```

返回数据多（跨平台、含图片/长标题、被报告复用），通过 `response_io.py` 落盘后按需读取：

```bash
python scripts/response_io.py read <file> --fields "<paths>"
```

> 落盘走 `linkfox_paths.resolve_*_path`，默认写到 `<cwd>/linkfox/<YYYY-MM-DD>/<session>/reports/`。文件含价格等数据，勿提交。

---

## 报告产物

输出所选平台的竞品表（列见上表），并附：参考商品（步骤 1）、平台 + 站点、数据来源清单、局限性。

业务章节：

- 「竞品表」：来自步骤 4，所选平台的列，销量降序。
- 「跨平台对比」：可选；多次单平台运行后，挑各平台 TOP1 横向对比价格/销量。

> ⚠ 如果需要生成报告 / 精美报告，必须去阅读 SKILL `linkfox-report-generator`，根据它的规范来。本 skill 只准备业务数据；样式、排版、md/html 导出、元信息块统统由 `linkfox-report-generator` 负责。不要在此处复制报告样式或 html 模板。

最终交付 JSON 的 envelope 结构与组件契约见 `references/output-schema.md`。

---

## 无效输入与异常处理（Bad Cases）

任何一步发现输入无效或拿不到数据时，**不要静默失败、不要编造数据**——用 `linkfox-form-protocol` 向用户说明问题并索要正确输入。


| Bad Case    | 检测点                                | 给用户的提示                                                             |
| ----------- | ---------------------------------- | ------------------------------------------------------------------ |
| 既没给图片也没给链接  | 步骤 0：`imageUrl` 与 `productUrl` 都为空 | "请提供一张商品主图（公开 URL）或一个商品链接。"                                        |
| 无效图片        | 上传/识图/图搜返回错误：URL 打不开、404、非图片、格式不支持 | "这张图片无法访问或格式不支持，请提供有效的公开图片 URL（JPG/PNG/WebP/GIF/BMP）。"             |
| 无效商品链接      | 步骤 0 情形 B：域名不在支持平台内、非商品页、打不开、取不到主图 | "无法识别该链接，请提供 Amazon/Walmart/TikTok/eBay/Ozon 的有效商品链接，或改为直接上传商品主图。" |
| 选了不支持的平台    | 步骤 0：平台不在 5 个支持平台内                 | "该平台暂不支持。目前支持：Amazon、Walmart、TikTok、eBay、Ozon。"                    |
| 站点与平台不匹配    | 步骤 0：站点不在该平台支持范围                   | "该平台不支持此站点，请从以下站点选择：…（列出该平台站点）。"                                   |
| 识图失败/提不出关键词 | 步骤 1：返回非 200 或 `search_query` 为空   | "图片不够清晰或无法识别，请换一张更清晰的商品主图。"                                        |
| 搜索结果为空      | 步骤 2：该平台返回 0 条                     | "在该平台用此图/关键词未找到同类竞品，建议换更典型的主图，或换一个平台/站点再试。"                        |
| Ozon 关键词非俄语 | 步骤 2 Ozon：接口报错                     | 步骤 1 已自动翻译俄语；若仍失败，提示"Ozon 需俄语关键词，请确认商品可在俄区识别"。                     |


---

## 执行自检

- 步骤 0 已拿到用户明确确认的**单个**平台 + 站点；**情形 B 即使从链接已识别出平台站点，也已回显并取得用户明确"是/否"确认，未自动跳过**
- 步骤 1 拿到 `search_query`（非 Amazon 需要）与 `search_query_ru`（Ozon 需要）
- 步骤 2 选定平台有返回（失败则标注"暂无数据"）
- 步骤 3 Walmart 按 ItemId、Ozon 按 SKU 补全完成（若选这两个平台）
- 步骤 4 按该平台的列输出、Top N、销量降序；抓不到的列不出现
- 最终交付为 `skill-output` envelope（`subject=product_list`，`component=ProductListRenderer`，带 `platformColumns`）

---

## 已知局限

- **图搜仅 Amazon**：其余平台靠"识图→关键词"，召回受关键词质量影响。
- **Ozon**：须俄语关键词，步骤 1 自动翻译，搜索/详情两步；价格多为换算值。
- **eBay**：无品类/销售额，用"已售数量"代销量；部分多规格/拍卖商品价格为空。
- **TikTok**：无配送/BSR/重量/尺寸；销售额用 GMV。
- **BSR/重量/尺寸仅 Amazon**；**配送**无 TikTok/Ozon。
- **销量口径不一**：Amazon=Keepa 月销估算、Walmart/Ozon=统计期销量、TikTok=累计销量、eBay=历史已售；跨平台对比需注意口径差异。

