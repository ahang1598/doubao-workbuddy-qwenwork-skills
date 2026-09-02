---
name: linkfox-amazon-search-competition
description: 亚马逊前台搜索首页或前3页自然结果市场格局分析。双数据源：用 linkfox-amazon-search 拉默认排序结果去广告重算 organic_rank，再用 linkfox-keepa-product-request 批量补充品牌/卖家/BSR/利润/上架时间/12月销量趋势等深度字段；固定输出：38维格局（竞争格局15维 + 进入门槛13维 + 趋势生命周期10维）+ 新品清单 + 类目上下文画像 + 每条ASIN的title/image结构化增强 + JSON与动态对比表三交付。触发：前台搜索市场格局分析、首页商品分析、前3页分析、搜索结果竞争格局、38维市场分析、品牌集中度、品牌垄断系数、BSR趋势、利润率分布、上架时间分布、新品起量速度、生命周期阶段、市场成熟度、竞品对比表、标题同质化、主图形态、偏题ASIN、SERP competitive landscape。工具依赖：linkfox-amazon-search（45积分）+ linkfox-keepa-product-request（~540积分），总计~585积分。
---

# 亚马逊前台搜索市场格局分析

输入一个关键词，用 `linkfox-amazon-search` 搜默认相关性排序的 **首页或前 3 页**，去广告并重算自然位后，再用 `linkfox-keepa-product-request`（history=1）批量补充深度字段，**固定跑完整链路**：

1. **38 维市场格局** + **升级版新品清单**
2. **类目上下文画像**（买家看标题 vs 主图各关心什么）
3. **每条 ASIN 增强**（title / imageUrl 结构化 + 对比维取值 + Keepa 字段）
4. **三交付**：HTML 报告 + 增强 JSON / 动态对比表

> **双数据源**：SERP 提供搜索位次与基础字段；Keepa 补充品牌/卖家/BSR/利润/上架时间/12月销量趋势。

## 核心特点

- **双数据源**：`linkfox-amazon-search`（SERP）+ `linkfox-keepa-product-request`（深度字段）
- **38 维分析**：竞争格局 15 维 + 进入门槛 13 维 + 趋势与生命周期 10 维
- **Keepa 降级**：Keepa 不可用时自动降级为纯 SERP 6 段分析
- **自然位重算**：`position` 为页内相对名次；按 page 顺序去广告后连续编号 `organic_rank`
- **月销缺失规则**：`monthlySalesUnits` 缺失记为 50；revenue 缺失用 `50 × extractedPrice` 估算
- **广告过滤**：分析基于自然结果，不含 `sponsored: true`
- **标题/主图必做**：按类目生成 context_profile，增强每个 ASIN，输出代码 + 表格

## 参数概览

| 参数 | 类型 | 必填 | 说明 | 默认值 |
|------|------|------|------|--------|
| keyword | string | 是 | 搜索关键词（需翻译为目标站点语言） | - |
| amazonDomain | string | 是 | 亚马逊站点域名（如 amazon.com） | - |
| language | string | 否 | 语言代码 | 按 amazonDomain 推断 |
| keepaDomain | string | 否 | Keepa 站点 ID | 按 amazonDomain 映射 |

**站点映射**：amazon.com→en_US（keepa 1），amazon.co.uk→en_GB（keepa 2），amazon.de→de_DE（keepa 3），amazon.fr→fr_FR（keepa 4），amazon.co.jp→ja_JP（keepa 5），amazon.ca→en_CA（keepa 6），amazon.it→it_IT（keepa 8），amazon.es→es_ES（keepa 9）。

用户未指定站点时，用 `AskUserQuestion` 询问。

## 工作流程（固定全流程，不拆路由）

### Step 1 — 拉前台搜索
`sort: "relevanceblender"`。前 3 页并行（各 15 积分，共 45 积分）。

### Step 2 — 合并、去广告、重算 organic_rank
按 page 顺序、页内 position 升序、跳过 sponsored、连续编号、ASIN 去重。

### Step 3 — Keepa 批量补充（~540 积分）
```bash
python scripts/batch_keepa_fetch.py <merged_products.json> --domain <keepa_domain_id> [--inline]
```
按 5 个一批调用 Keepa API（history=1），补充品牌/卖家/BSR/利润/上架时间/12月销量趋势等字段。24h 本地缓存。

**降级**：Keepa 不可用时跳过，后续使用纯 SERP 数据。

### Step 4 — 合并 SERP + Keepa
按 ASIN 合并，Keepa 字段平铺到产品对象。价格/月销优先用 SERP。

### Step 5 — 类目上下文画像 + ASIN 增强
生成 context_profile + enrichment（含 keepa_available 标记）。

### Step 6 — 运行 38 段聚合脚本
```bash
python scripts/aggregate_competition.py <merged_with_keepa.json> [--inline] [--fixed-buckets] [--buckets <file.json>]
```

### Step 7 — 交付（HTML + JSON + 对比表）
调用 `linkfox-report-generator` 生成 HTML，增强 JSON 和对比表落盘 data 目录。

## 38 段定义

### A. 竞争格局（15 维）

| # | 名称 | 图表 | 数据源 | 商业含义 |
|---|------|------|--------|----------|
| 1 | 页流量占比 | 表/柱 | SERP | 首页是否垄断流量 |
| 2 | 自然位集中度 | 帕累托 | SERP | 头部垄断还是长尾分散 |
| 3 | 价格分布 | 柱+线双Y | SERP+Keepa | 货与量是否同价带 |
| 4 | 评分数分布 | 柱+线双Y | SERP | 评论门槛 |
| 5 | 评分分布 | 柱+线双Y | SERP | 星级是否拉开差距 |
| 6 | 变体覆盖 | 纯KPI | SERP+Keepa | 多变体链接占比 |
| 7 | 品牌集中度 | 表/饼 | Keepa | 品牌 ASIN 数占比 |
| 8 | 品牌销量份额 | 表/饼 | Keepa | 品牌销量占比 |
| 9 | 头部品牌垄断系数 | 纯KPI | Keepa | CR3/CR5 |
| 10 | 卖家集中度 | 表/饼 | Keepa | 卖家 ASIN 数占比 |
| 11 | 配送方式占比 | 饼 | Keepa | FBA/FBM/AMZ 占比 |
| 12 | 变体复杂度分布 | 柱 | Keepa | 变体数量分桶 |
| 13 | 卖家数量分布 | 柱 | Keepa | 卖家数分桶 |
| 14 | 多卖家竞争占比 | 纯KPI | Keepa | sellerNum>1 占比 |
| 15 | 类目分布 | 表 | Keepa | 子类目聚合 |

### B. 进入门槛（13 维）

| # | 名称 | 图表 | 数据源 | 商业含义 |
|---|------|------|--------|----------|
| 16 | 评论门槛(Top10) | 纯KPI | ratings | Top10 平均评分数 |
| 17 | 评论中位数 | 纯KPI | ratings | 评分数中位数 |
| 18 | 新品评论增长速度 | 散点 | ratings/availableDate | 月均评论增长 |
| 19 | 价格门槛 | 纯KPI | extractedPrice | P25/P50/P75 |
| 20 | BSR门槛(Top10) | 纯KPI | Keepa salesRank | Top10 平均 BSR |
| 21 | BSR中位数 | 纯KPI | Keepa salesRank | BSR 中位数 |
| 22 | 利润率分布 | 柱 | Keepa profit | 利润率分桶 |
| 23 | FBA费用分布 | 柱 | Keepa fbaFees | FBA 费用分桶 |
| 24 | 佣金率分布 | 柱 | Keepa referralFeePercentage | 佣金率分布 |
| 25 | 危险品占比 | 纯KPI | Keepa isHazmat | 危险品占比 |
| 26 | 成人产品占比 | 纯KPI | Keepa isAdultProduct | 成人产品占比 |
| 27 | 上架时间分布 | 柱 | Keepa availableDate | 按上架月数分桶 |
| 28 | 新品占比 | 纯KPI | Keepa availableDate | 上架<6月占比 |

### C. 趋势与生命周期（10 维）

| # | 名称 | 图表 | 数据源 | 商业含义 |
|---|------|------|--------|----------|
| 29 | 月销量趋势 | 折线 | Keepa history | 当前 vs 1/3/6/12月前 |
| 30 | 市场总销量趋势 | 折线 | Keepa history | 市场总量月度走势 |
| 31 | BSR趋势 | 折线 | Keepa salesRank | 当前 vs 30/90/180天 |
| 32 | BSR波动度 | 纯KPI | Keepa salesRank | CV |
| 33 | 新品起量速度 | 散点 | Keepa | 新品销量增长 |
| 34 | 产品生命周期阶段 | 表 | Keepa 综合 | 导入/成长/成熟/衰退 |
| 35 | 市场成熟度 | 纯KPI | Keepa 综合 | 平均上架月数+评论数 |
| 36 | 头部vs新品销量对比 | 柱 | SERP+Keepa | Top10 vs 新品 |
| 37 | 价格离散度 | 纯KPI | extractedPrice | CV |
| 38 | 销量离散度 | 纯KPI | units | CV |

### 附录：新品清单（升级）
- 有 Keepa：`availableDate` < 6 月
- 无 Keepa：`ratings < 100`（代理）
- 排序：`organic_rank` 升序

## Keepa 字段可用性

详见 [`references/keepa-fields.md`](keepa-fields.md)。

## 展示规则

- 所有位次分析使用 `organic_rank`，不用原始 `position` 跨页排序
- 帕累托累计占比单调递增，右 Y 轴最大 100%
- 分布图：柱=商品数，线=销量占比%
- 趋势图：折线，X 轴=时间（月/天），Y 轴=销量/BSR
- 散点图：X 轴=上架月数/时间，Y 轴=评论增长/销量增长
- 饼图：FBA/FBM/AMZ、品牌份额等占比
- 数字千分位，百分比 1 位小数
- 色板：`['#4f46e5','#06b6d4','#8b5cf6','#f59e0b','#10b981','#ef4444','#ec4899','#6366f1']`

## 报告必须披露的边界

- 样本 = 默认排序前 3 页自然结果（已去广告）
- 自然位次 = 按页序去广告后连续编号，**非**亚马逊官方 rank / BSR
- 月销缺失按 50 件计；销额缺失按 50×现价估算；注明原始销量覆盖率
- 是否含变体依据 SERP options + Keepa variationNum
- 新品清单：有 Keepa 数据时以 availableDate<6 月为主口径，无 Keepa 数据时以 ratings<100 为代理
- Keepa 数据覆盖率 = 成功 ASIN 数 / 总 ASIN 数
- BSR/利润/FBA费用/品牌/卖家等维度仅在 Keepa 数据可用时呈现

## 限制

- 每次 3 页 SERP：45 积分
- Keepa 批量：~48 ASINs / 5 = 10 批次，约 540 积分
- 总计约 585 积分
- Keepa 不可用时降级为纯 SERP 6 段分析（45 积分）
- 每页条数不固定，过滤广告后自然结果数量随词变化
- 实时前台快照 + Keepa 最近更新数据，非完全同步

## 适用与不适用

**适用**：关键词首页或前 3 页自然竞争结构；品牌份额与垄断系数；FBA/FBM 结构；卖家集中度；BSR 门槛与趋势；利润率与 FBA 费用分布；上架时间与新品分析；12 月销量趋势与生命周期阶段；定价带与销量是否错位；自然位集中度；标题/主图同质化与偏题形态；按类目对齐的 ASIN 对比表。

**不适用**：关键词级搜索量/趋势（用 ABA 工具）；广告/PPC 数据；评论内容分析；全类目份额（非前3页范围）；历史价格曲线（用 keepa-product-series）。
