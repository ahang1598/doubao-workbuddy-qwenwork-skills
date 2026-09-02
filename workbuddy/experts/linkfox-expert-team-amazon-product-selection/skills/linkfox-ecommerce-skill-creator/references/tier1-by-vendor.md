# Tier 1 Catalog - 按数据源/厂商索引

> SOT：`linkfoxagent-v2/` 实时目录（每个真实 skill 的 `SKILL.md` frontmatter）。
> 本文件按数据源分组，便于"我已经知道用哪家"的反向查找。
> 主表（按能力）见 `tier1-catalog.md`；按平台见 `tier1-by-platform.md`。

---

## 亚马逊前端 / ABA 官方（6）

| Slug | 用途 |
|---|---|
| linkfox-amazon-product-detail | 前端模拟拉详情，22 站，按 ASIN 计费（单价高） |
| linkfox-amazon-search | 前端关键词搜索（含广告位） |
| linkfox-amazon-search-by-image | 以图搜图，8 站 |
| linkfox-amazon-reviews-list | 评论抓取，支持星级、关键词、排序和媒体类型过滤 |
| linkfox-amazon-opportunity-report-by-keyword | 6 维 AI 选品报告，**当前仅美国站** |

| Slug | 用途 |
|---|---|
| linkfox-aba-intelligent-query | ABA Search Terms Report 周维度（15 站，近 3 年），SQL 风格自然语言查询 |

## Keepa（3）

> Amazon 详情 + 价格/BSR 历史 + 高级筛选。

| Slug | 用途 |
|---|---|
| linkfox-keepa-product-request | 按 ASIN 批量结构化字段（含近 12 月月销量），单次最多 100 |
| linkfox-keepa-product-search | 高级商品搜索（多维度结构化筛选） |
| linkfox-keepa-product-series | 单 ASIN 历史曲线（价格/BSR/卖家数/划线价/闪促） |

## SellerSprite 卖家精灵（5）

> Amazon 选品/竞品/市场/流量词反查。

| Slug | 用途 |
|---|---|
| linkfox-sellersprite-product-search | 40+ 维度选品（毛利率 / Badge / 历史月份快照） |
| linkfox-sellersprite-market-research | 50+ 维度筛蓝海类目 + 头部 10 商品图 |
| linkfox-sellersprite-market-statistics | 单类目节点市场指标（头部 listing 平均销量等） |
| linkfox-sellersprite-competitor-lookup | 按 ASIN/卖家/品牌/类目精准查竞品（含历史快照） |
| linkfox-sellersprite-traffic-keyword | 单 ASIN 反查全部流量词（自然 + SP + AC + 品牌 + 视频） |

## SIF 搜索情报（4）

> 按 ASIN/关键词分析 Amazon 流量结构。

| Slug | 用途 |
|---|---|
| linkfox-sif-asin-keywords | 单 ASIN 流量词明细 + 自然/SP 排名 + 周搜索量 |
| linkfox-sif-asin-summary | 单/批量（≤10）ASIN 流量结构概要 + 周期对比 |
| linkfox-sif-keyword-overview | 关键词竞争度/供需比/市场概览 |
| linkfox-sif-keyword-summary | 关键词流量结构 + 主要竞品 ASIN 明细 |

## Sorftime（2）

> 14 站 Amazon 详情 + 销量/销额/BSR 趋势 + FBA 费 + 毛利率。

| Slug | 用途 |
|---|---|
| linkfox-sorftime-amazon-product-detail | 单/批量（≤10）ASIN 详情 + 时序 |
| linkfox-sorftime-amazon-product-query | 六种查询模式（ASIN 同类 / 类目 / 品牌 / 卖家 / ABA 词） |

## 极目 Jiimore（5，**仅 US/JP/DE**）

| Slug | 用途 |
|---|---|
| linkfox-jiimore-get-niche-info-by-keyword | 关键词 → 细分市场指标（垄断/集中度/前 5 品牌等） |
| linkfox-jiimore-get-niche-info | nicheId → 细分市场详情/买家反馈/洞察 |
| linkfox-jiimore-get-niche-review-from-keyword | 关键词 → 细分市场舆情/痛点 |
| linkfox-jiimore-page-asins-by-asin | 种子 ASIN → 同类潜力品 |
| linkfox-jiimore-product-discovery | 关键词 → 潜力爆品挖掘 |

## FastMoss TikTok（2）

| Slug | 用途 |
|---|---|
| linkfox-fastmoss-product-search | 关键词搜索（销量/GMV/佣金/达人数） |
| linkfox-fastmoss-product-rank-top-selling | 日/周/月榜，**不支持关键词检索** |

## EchoTik TikTok（2）

| Slug | 用途 |
|---|---|
| linkfox-echotik-list-product | 关键词 + 16 国/区域 + 中文类目 + 达人带货数据 |
| linkfox-echotik-list-new-product-rank | 16 区域新品榜 |

## Google Trends（2）

| Slug | 用途 |
|---|---|
| linkfox-google-trend-get-trend-by-keys | 指定关键词在 XX 国家的热度趋势 |
| linkfox-google-trend-get-trend-by-time | 指定国家最近时段的热门话题 |

## 1688 / 店雷达 DLD（2）

> **关键词必须中文**。

| Slug | 用途 |
|---|---|
| linkfox-dld-product-search | 选品库关键词搜索（货源/工厂/一件代发） |
| linkfox-dld-product-billboard | 周/月榜单，发现批发爆款 |

## eBay（1）

| Slug | 用途 |
|---|---|
| linkfox-ebay-search | 前端商品列表搜索（拍卖/一口价/最佳出价） |

## Walmart / WallySmarter（2）

| Slug | 用途 |
|---|---|
| linkfox-walmart-search | 前端商品列表搜索 |
| linkfox-wallysmarter-product-detail | 按 ItemId 查详情 + 价格/销量历史 |

## 友鹰 Shopee（1）

| Slug | 用途 |
|---|---|
| linkfox-youying-shopee-get-product-infos | 11 站点选品（销量/评分/Favorite/官方店/本土跨境） |

## 通用网页 / TSearch（1）

| Slug | 用途 |
|---|---|
| linkfox-tsearch-search | 联网检索（Google/Reddit/微信公众号/社区/站外帖） |

## 睿观合规 / 商标 / 专利（6）

> 跨境合规，**法律敏感**：高相似度结果必须完整展示并附免责声明。

| Slug | 用途 |
|---|---|
| linkfox-ruiguan-text-trademark-detection | 文字商标（15 国） |
| linkfox-ruiguan-trademark-graphic-detection | 图形商标（含切图与雷达图） |
| linkfox-ruiguan-detection-patent-design | 外观专利（含 TRO 维权史） |
| linkfox-ruiguan-utility-patent-detection | 发明/实用新型，**当前仅美国站** |
| linkfox-ruiguan-copyright-detection | 版权检测 |
| linkfox-ruiguan-gun-parts-search | 政策合规（管制品/违禁品图像比对） |

## 智慧芽 PatSnap 专利（15）

> 著录 / 摘要 / 权利要求 / 说明书 / 引用 / 家族 / 法律状态 / PDF / 附图 / 翻译 / 以图搜专利。**多个 ID 用英文逗号分隔，上限 100 条**；`patentId` 优先于 `patentNumber`。

| Slug | 用途 |
|---|---|
| linkfox-zhihuiya-simple-bibliography | 简单著录（标题/申请号/公开号/申请日/公开日） |
| linkfox-zhihuiya-bibliography | 完整著录（含优先权/分类/申请人/发明人/引用） |
| linkfox-zhihuiya-abstract-data-translated | 摘要翻译（中/英/日） |
| linkfox-zhihuiya-abstract-image | 摘要附图（代表图） |
| linkfox-zhihuiya-claim-data | 权利要求原文 |
| linkfox-zhihuiya-claim-data-translated | 权利要求翻译 |
| linkfox-zhihuiya-description-data | 说明书原文 |
| linkfox-zhihuiya-description-data-translated | 说明书翻译 |
| linkfox-zhihuiya-fulltext-image | 全文附图（所有专利图） |
| linkfox-zhihuiya-pdf-data | PDF 全文下载链接 |
| linkfox-zhihuiya-legal-status | 法律状态（简单/法律/事件三层） |
| linkfox-zhihuiya-patent-cited | 专利被引用（向后引用） |
| linkfox-zhihuiya-patent-forward-citation | 专利引用（向前引用） |
| linkfox-zhihuiya-patent-family | 专利家族（同族/各国对应） |
| linkfox-zhihuiya-patent-image-search | 以图搜外观/实用新型专利（**法律敏感**） |

## 多模态 AI / AIGC（4）

| Slug | 用途 |
|---|---|
| linkfox-aigc-imagegen | AI 生图（BANANA / GPT_2_IMAGE / AIDRAW_EDIT / WAN2_7） |
| linkfox-aigc-imagegen-product | 商品图生成编排（白底图/场景图/特写图/卖点图/A+ 图） |
| linkfox-aigc-textgen | AI 生文（GEM_3_FLASH / GEM_3_1_PRO，支持图文理解） |
| linkfox-aigc-videogen | AI 生视频（KLING / V电影 / WAN万相 / SEED豆包 / HAILUO海螺） |

## 编排器 / 协议（3，**非数据源 skill**）

> 这三个 skill 不直接抓取数据；它们规范流程或编排其他 Tier 1。任何 Tier 2/3 都应优先调用本组而非自由实现。

| Slug | 用途 |
|---|---|
| linkfox-report-generator | 报告生成器（HTML 默认 + ECharts 骨架；Markdown 备选）；禁止在对话中拼接报告正文 |
| linkfox-task-scheduler | 定时任务 / 周期性任务调度 |
| linkfox-superagent-orchestration | 多阶段流程编排辅助 |

---

## 维护

- 上游 SOT：`linkfoxagent-v2/` 实时目录。
- 新增/重命名 skill 时优先保证实时目录正确；需要刷新本表时跑 `scripts/list_v2_skills.py --write-indexes <目录>` 生成索引视图后再替换。
- 总数核对：6 + 1 + 3 + 5 + 4 + 2 + 5 + 2 + 2 + 2 + 2 + 1 + 2 + 1 + 1 + 6 + 15 + 4 + 3 = **67**。
