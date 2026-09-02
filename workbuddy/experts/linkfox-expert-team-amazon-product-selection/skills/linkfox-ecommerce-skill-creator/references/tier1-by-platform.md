# Tier 1 Catalog - 按平台索引

> SOT：`linkfoxagent-v2/` 实时目录（每个真实 skill 的 `SKILL.md` frontmatter）。
> 本表是基于某个时间点 v2 内容整理出的平台导航缓存，可能滞后；用户已指明目标平台时可用它收窄，但最终候选必须回到实时 v2 全集确认。
> 跨平台 / 平台无关 skill 在末尾「跨平台 / 平台无关」段。

---

## Amazon（最丰富，44 skill）

> Amazon 是 Tier 1 覆盖最厚的平台。注意 ① 多站 vs 单站差异（评论、Opportunity、Jiimore）；② vendor 之间能力多有重叠，按"想看的字段"挑。

### 商品详情
- `linkfox-amazon-product-detail`：前端模拟，22 站，含五点/A+/规格/附图/bought together，按 ASIN 计费，单价较高。
- `linkfox-keepa-product-request`：结构化字段 + 近 12 个月月销量，单次最多 100 ASIN。
- `linkfox-sorftime-amazon-product-detail`：含销量/销额历史 + 多级 BSR + FBA 费 + 毛利率，14 站，单次最多 10 ASIN。

### 搜索 / 列表
- `linkfox-amazon-search`：模拟前台搜索，含广告/推荐位（前端真实页面）。
- `linkfox-amazon-search-by-image`：以图搜图，8 站。
- `linkfox-keepa-product-search`：结构化筛选（类目/价/销/BSR/评论/重量/上架时间）。
- `linkfox-sellersprite-product-search`：40+ 维度筛 + 历史月份快照 + Badge 标识 + 毛利率。
- `linkfox-sorftime-amazon-product-query`：六种查询模式（ASIN 同类 / 类目 / 品牌 / 卖家 / ABA 词），14 站。

### 评论
- `linkfox-amazon-reviews-list`：单 ASIN，每星级最多 100，支持星级、关键词、排序和媒体类型过滤。

### 关键词反查 / 流量结构
- `linkfox-aba-intelligent-query`：ABA Search Terms Report 周数据（15 站，近 3 年），SQL 风格自然语言查询。
- `linkfox-sellersprite-traffic-keyword`：单 ASIN 反查全部流量词（自然 + SP + AC/ER/HR + 品牌 + 视频）。
- `linkfox-sif-asin-keywords`：单 ASIN 流量词明细 + 自然/SP 排名 + 周搜索量。
- `linkfox-sif-asin-summary`：单 / 批量（≤10）ASIN 流量结构概要 + 周期对比。
- `linkfox-sif-keyword-overview`：关键词级竞争度/供需比/市场概览。
- `linkfox-sif-keyword-summary`：关键词级流量结构 + 主要竞品 ASIN 明细。

### 选品 / 类目市场
- `linkfox-amazon-opportunity-report-by-keyword`：6 大维度 AI 综合洞察报告，**当前仅美国站**。
- `linkfox-sellersprite-market-research`：50+ 维度筛蓝海类目 + 头部 10 商品图。
- `linkfox-sellersprite-market-statistics`：单类目节点的市场指标统计。
- `linkfox-jiimore-get-niche-info-by-keyword`：关键词 → 细分市场指标（**仅 US/JP/DE**）。
- `linkfox-jiimore-get-niche-info`：按 nicheId 深挖细分市场（**仅 US/JP/DE**）。
- `linkfox-jiimore-get-niche-review-from-keyword`：关键词 → 细分市场舆情/痛点（**仅 US/JP/DE**）。
- `linkfox-jiimore-page-asins-by-asin`：种子 ASIN → 同类潜力品（**仅 US/JP/DE**）。
- `linkfox-jiimore-product-discovery`：关键词 → 潜力爆品（**仅 US/JP/DE**）。

### 价格 / BSR / 销量历史
- `linkfox-keepa-product-series`：单 ASIN 历史曲线（价格 / BSR / 卖家数 / 划线价 / 闪促）。
- `linkfox-sorftime-amazon-product-detail`：含销量/销额/BSR 时序（与详情合并）。
- `linkfox-keepa-product-request`：结构化字段中含近 12 月月销量。

### 竞品精准命中
- `linkfox-sellersprite-competitor-lookup`：按 ASIN/卖家/品牌/类目精准查竞品，含历史月份快照。

> 注：店铺授权（SP-API）/ 广告 / ERP 等"店内数据"类 skill 当前不在 67-skill 名单中；如需要请走团队后续上新。

---

## TikTok Shop（4 skill）

- `linkfox-fastmoss-product-search`：关键词搜索，按销量/GMV/佣金/达人数筛。
- `linkfox-fastmoss-product-rank-top-selling`：日/周/月榜，**不支持关键词检索**。
- `linkfox-echotik-list-product`：关键词 + 16 国/区域 + 中文类目，含达人带货数据。
- `linkfox-echotik-list-new-product-rank`：16 区域新品榜。

---

## 1688（中国货源，2 skill）

- `linkfox-dld-product-search`：选品库关键词搜索（**关键词必须中文**）。
- `linkfox-dld-product-billboard`：周/月榜单，发现批发爆款（**关键词必须中文**）。

---

## eBay（1 skill）

- `linkfox-ebay-search`：前端商品列表搜索，支持邮编/类目/拍卖/一口价/最佳出价。

---

## Walmart（2 skill）

- `linkfox-walmart-search`：前端商品列表搜索（NextDay / facet / 拼写修正）。
- `linkfox-wallysmarter-product-detail`：按 ItemId 查详情 + 价格/销量历史。

---

## Shopee（1 skill，11 站）

- `linkfox-youying-shopee-get-product-infos`：友鹰 Shopee 选品（关键词 + 1-3 级类目 + 销量/评分/Favorite/Ratings/官方店/虾皮优选/本土跨境/发货地）。

---

## Google Trends（2 skill）

- `linkfox-google-trend-get-trend-by-keys`：指定关键词在 XX 国家的热度趋势（最早 2004）。
- `linkfox-google-trend-get-trend-by-time`：指定国家最近时段的热门话题。

---

## 跨平台 / 平台无关（14 skill）

### 通用网页搜索
- `linkfox-tsearch-search`：联网检索（Google/Reddit/微信公众号/社区/站外帖）。

### 全球合规 / 商标 / 专利侵权（睿观）（6）
- `linkfox-ruiguan-text-trademark-detection`：文字商标，15 国（AU/BX/CA/DE/EM/ES/FR/GB/IT/JP/MX/TR/US/WO/CN）。
- `linkfox-ruiguan-trademark-graphic-detection`：图形商标。
- `linkfox-ruiguan-detection-patent-design`：外观专利，**法律敏感**，相似度≥0.7 或有 TRO 维权史必须完整展示。
- `linkfox-ruiguan-utility-patent-detection`：发明/实用新型，**当前仅美国站**。
- `linkfox-ruiguan-copyright-detection`：版权检测。
- `linkfox-ruiguan-gun-parts-search`：政策合规（管制品/枪支配件/违禁品）。

### 专利数据库（智慧芽 PatSnap，15）
> 见 `tier1-by-vendor.md` § 智慧芽段。覆盖摘要/著录/权利要求/说明书/引用/家族/法律状态/PDF/附图/翻译/以图搜专利。**法律敏感**。

### 多模态 AI 内容（4）
- `linkfox-aigc-imagegen`：AI 生图（多模型 + 多分辨率/宽高比/数量）。
- `linkfox-aigc-imagegen-product`：商品图生成编排（白底图/场景图/特写图/卖点图/A+ 图）。
- `linkfox-aigc-textgen`：AI 生文，支持图文结合理解。
- `linkfox-aigc-videogen`：AI 生视频（多模型，单图/多图，控时长/Pro/声音/运镜/尾帧）。

### 编排器 / 协议（3，非数据源 skill）
- `linkfox-task-scheduler`：定时任务 / 周期性任务调度。
- `linkfox-superagent-orchestration`：多阶段流程编排辅助。
- `linkfox-report-generator`：报告生成器（HTML 默认，含 ECharts；Markdown 备选）。任何报告类产物必须经此 skill。

---

## 平台覆盖一览（速查）

| 能力 \ 平台 | Amazon | TikTok | 1688 | eBay | Walmart | Shopee | Google | 全球合规 |
|---|---|---|---|---|---|---|---|---|
| 商品详情 | ✓✓✓ | — | — | — | ✓ | — | — | — |
| 商品搜索 / 选品 | ✓✓✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | — |
| 评论 | ✓ | — | — | — | — | — | — | — |
| 关键词反查 / 流量结构 | ✓✓✓ | — | — | — | — | — | — | — |
| 类目 / 细分市场 | ✓✓✓ | — | — | — | — | — | — | — |
| 价格 / BSR 历史 | ✓✓ | — | — | — | ✓ | — | — | — |
| 榜单 | — | ✓✓ | ✓ | — | — | — | — | — |
| 趋势 / 热搜 | — | — | — | — | — | — | ✓✓ | — |
| 合规 / 商标 / 专利 | — | — | — | — | — | — | — | ✓✓✓ |

`✓✓✓` = 多家数据源；`✓✓` = 两家；`✓` = 至少一家；`—` = 暂无。

---

## 维护

- 上游 SOT：`linkfoxagent-v2/` 实时目录。
- 新增/重命名 skill 时优先保证实时目录正确；需要刷新本表时跑 `scripts/list_v2_skills.py --write-indexes <目录>` 生成索引视图后再替换。
