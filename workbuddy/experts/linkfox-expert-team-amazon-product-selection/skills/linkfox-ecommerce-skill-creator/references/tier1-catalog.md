# Tier 1 Catalog - 按能力分组（主表）

> meta-skill 在"新建模式"下的**分类导航表**。共 67 个 Tier 1 skill。
> 数据来源：`../../linkfoxagent-v2/`（团队内部 SOT，按目录扫描每个 SKILL.md frontmatter 提炼）。
> 本表是 v2 的二次摘要 / 导航缓存，不是能力发现 SOT。创建 workflow 时先用 `scripts/list_v2_skills.py` 扫实时 v2 全集，再用本表按能力定位，并以实时目录和对应 `SKILL.md` frontmatter 为准。
> 完整数据源分组见 `tier1-by-vendor.md`。常见业务链路见 `tier1-recipes.yaml`。
>
> 字段说明：`skill name (slug) | 平台/站点 | 一句业务用途`

---

## 1. 商品详情（4）

| Slug | 平台/站点 | 用途 |
|---|---|---|
| linkfox-amazon-product-detail | Amazon 多站 | 前端模拟抓详情：标题/主图/附图/五点/A+/规格/相关品/作者评论；最多 40 ASIN 批量；按 ASIN 计费且单价较高 |
| linkfox-sorftime-amazon-product-detail | Amazon 14 站 | Sorftime ASIN 详情含日/月销量与销售额（自 2021 年起）+ 多级 BSR 历史 + FBA 费/佣金/预估毛利率；单次最多 10 ASIN |
| linkfox-keepa-product-request | Amazon (Keepa) | Keepa 按 ASIN 批量取结构化字段：标题/价格/材质/重量/上架时间/子体月销/近 12 月每月月销；单次最多 100 ASIN |
| linkfox-wallysmarter-product-detail | Walmart | 按 ItemId 查商品详情、价格历史、销量历史趋势；返回非结构化数据 |

## 2. 商品搜索 / 前端排名（5）

| Slug | 平台/站点 | 用途 |
|---|---|---|
| linkfox-amazon-search | Amazon | 模拟真实用户前台搜索，含广告/推荐位；支持邮编/类目节点/排序/页码/设备/语言 |
| linkfox-amazon-search-by-image | Amazon 8 站 | 以图搜图找视觉相似 ASIN；按邮编/国家/价格/评分/评论数排序 |
| linkfox-walmart-search | Walmart | 关键词/类目/价格区间/商店 ID/NextDay 配送/排序/facet |
| linkfox-ebay-search | eBay 多站 | 关键词/类目/价格/格式（拍卖/一口价/最佳出价）/条件/位置/排序 |
| linkfox-tsearch-search | 通用网页 | Google / Reddit / 社区 / 公众号 / 站外帖子；返回非结构化内容直接进总结 |

## 3. 结构化选品 / 多维筛选（7）

| Slug | 平台/站点 | 用途 |
|---|---|---|
| linkfox-keepa-product-search | Amazon (Keepa) | 高级筛：类目/价/月销/关键词正反向/BSR/评论/评分/包装/重量/配送/上架/危险品/变体/历史排名 |
| linkfox-sellersprite-product-search | Amazon | 卖家精灵 40+ 维：毛利率/卖家数/FBA 运费/上架时间/Listing 质量分/Choice/Best Seller/New Release/品牌包含或排除 |
| linkfox-sorftime-amazon-product-query | Amazon 14 站 | Sorftime 6 种模式：ASIN 找同类 / NodeId / 品牌 / 卖家名 / 卖家 ID / ABA 关键词；含 FBA 毛利 |
| linkfox-fastmoss-product-search | TikTok | FastMoss 关键词 + 类目 + 店铺类型 + 本土仓 + 销量/GMV/佣金率/达人数 多维筛 |
| linkfox-echotik-list-product | TikTok 16 区 | EchoTik 关键词 + 中文分类 + 销量/GMV/带货视频/达人/播放/评分/佣金 Min-Max |
| linkfox-youying-shopee-get-product-infos | Shopee 11 站 | 友鹰 Shopee：类目/价/评分/Favorite/销售额/件数/Sku 数/店铺/官方店/优选/本土跨境/发货地 |
| linkfox-dld-product-search | 1688 | 店雷达 1688 关键词搜货源；7/30 天周期；批发价/代发价/销量/起购量/卖家类型；**关键词必须中文** |

## 4. 关键词反查 / 流量分析（6）

| Slug | 平台/站点 | 用途 |
|---|---|---|
| linkfox-aba-intelligent-query | Amazon 15 站 | ABA 搜索词周数据 SQL 智能查询，近 3 年；搜索词 / 排名 / 点击 ASIN / 点击占比 / 转化占比 |
| linkfox-sellersprite-traffic-keyword | Amazon | 按 ASIN 反查竞品流量词：自然/SP/AC/ER/HR/品牌/视频；月搜索量/购买量/购买率/PPC/Top3 点转化；单次 1 个 ASIN |
| linkfox-sif-asin-keywords | Amazon | SIF 按 ASIN 反查流量关键词，含自然+SP 排名、周搜索量、本地化译文；单次 1 个 ASIN |
| linkfox-sif-asin-summary | Amazon | SIF 按 ASIN 看整体流量结构（自然/SP/SB/SBV/AC/TR/ER 占比 + 周期对比 + 关键词新进/退出）；最多 10 ASIN |
| linkfox-sif-keyword-overview | Amazon | SIF 关键词供需比 / 搜索热度 / 市场机会的市场概览（不含 ASIN 明细）|
| linkfox-sif-keyword-summary | Amazon | SIF 关键词为锚的逐 ASIN 流量结构明细：广告占比 / search share / 关键词级曝光 |

## 5. 评论 / 客户反馈（3）

| Slug | 平台/站点 | 用途 |
|---|---|---|
| linkfox-amazon-reviews-list | Amazon | 单 ASIN 评论；按星级 / 关键词 / 时间或有用性 / 媒体类型 / 格式 / 评论者类型筛；每星级最多 100 条 |
| linkfox-jiimore-get-niche-review-from-keyword | Amazon US/JP/DE | 极目按关键词做细分市场舆情和评论分析，洞察消费者真实需求与痛点 |

## 6. 类目调研 / 细分市场 / 选品发现（8）

| Slug | 平台/站点 | 用途 |
|---|---|---|
| linkfox-amazon-opportunity-report-by-keyword | Amazon **US only** | 按关键词查 6 大维度（市场潜力/产品特征/评论/客户画像/搜索趋势/定价）+ AI 多维交叉商业洞察报告 |
| linkfox-sellersprite-market-research | Amazon | 卖家精灵选市场：50+ 维（FBA 占比/退货率/卖家数/品牌集中度/月销售额增长/BSR 增长）找蓝海类目 |
| linkfox-sellersprite-market-statistics | Amazon | 卖家精灵按 NodeId 路径 + 时间范围统计市场指标；头部 Listing 平均销量/销售额/BSR/星级 + 新品月均；单次 1 个节点 |
| linkfox-sellersprite-competitor-lookup | Amazon 12 站 | 按 ASIN/卖家名/品牌/类目精准命中竞品；销量趋势 + 流量来源 + 价格 + 评分 + 历史月份快照对比 |
| linkfox-jiimore-product-discovery | Amazon US/JP/DE | 极目按关键词挖潜力爆品（高转化 / 点击增长 / 毛利率 / 年销 / FBA 费 / 评分 / 评论 / 上架时间） |
| linkfox-jiimore-page-asins-by-asin | Amazon US/JP/DE | 极目按种子 ASIN 挖同类潜力品（维度同 product-discovery，仅种子换成 ASIN） |
| linkfox-jiimore-get-niche-info-by-keyword | Amazon US/JP/DE | 极目按关键词查细分市场垄断度 / 品牌集中度 / 前 5 商品/品牌点击份额 / CPC / 退货率 / 新品率 / 广告占比 |
| linkfox-jiimore-get-niche-info | Amazon US/JP/DE | 极目按 nicheId 查细分市场详细信息、买家评价、市场洞察；通常与 niche-info-by-keyword 串联 |

## 7. 价格 / BSR / 销量趋势（1）

| Slug | 平台/站点 | 用途 |
|---|---|---|
| linkfox-keepa-product-series | Amazon (Keepa) | 单 ASIN Keepa 历史曲线：新品/FBA/FBM/Prime/Coupon/划线价/闪促 + BSR(大类) + 卖家数；非结构化曲线 |

## 8. 热销榜 / 新品（3）

| Slug | 平台/站点 | 用途 |
|---|---|---|
| linkfox-fastmoss-product-rank-top-selling | TikTok | FastMoss 日/周/月 + 国家/类目交叉爆款榜；按销量/GMV/增长率排序；**不支持关键词检索** |
| linkfox-echotik-list-new-product-rank | TikTok 16 区 | EchoTik 按日期 + 区域取新品热销榜，把握短视频电商最新趋势 |
| linkfox-dld-product-billboard | 1688 | 店雷达 1688 周/月榜；多维筛（销量/销售额/批发价/代发/诚信通/起批量/卖家类型）；**关键词必须中文** |

## 9. 热点 / 趋势（2）

| Slug | 平台/站点 | 用途 |
|---|---|---|
| linkfox-google-trend-get-trend-by-keys | Google Trends | 关键词在指定国家地区和时间段（最早 2004）的搜索热度趋势 |
| linkfox-google-trend-get-trend-by-time | Google Trends | 指定区域近期实时热门话题和流行趋势；返回非结构化数据 |

## 10. 合规 / 商标 / 侵权（6）

| Slug | 平台/站点 | 用途 |
|---|---|---|
| linkfox-ruiguan-copyright-detection | 多国 | 睿观-版权侵权检测：按图片 URL 返回相似版权作品和风险提示；法律敏感，需免责声明 |
| linkfox-ruiguan-text-trademark-detection | 15 国 (AU/BX/CA/DE/EM/ES/FR/GB/IT/JP/MX/TR/US/WO/CN) | 睿观-文字商标比对：按产品标题 + 文本 + 国家返回近似商标 |
| linkfox-ruiguan-trademark-graphic-detection | 多国 | 睿观-图形商标（logo / 图标 / 视觉标识）相似度比对；支持切图 + 雷达图 |
| linkfox-ruiguan-detection-patent-design | 25+ 国 | 睿观-外观专利侵权：按标题 + 图片 + 国家返回相似度 + TRO 维权史 + LOC + 摘要 + 说明书；**相似度 ≥ 0.7 或有 TRO 必须完整展示** |
| linkfox-ruiguan-utility-patent-detection | Amazon **US only** | 睿观-发明专利检测：按标题 + 描述 + 国家搜寻相似的发明专利 |
| linkfox-ruiguan-gun-parts-search | 全球 | 睿观-政策合规纯图检测：按图片 URL 搜相似违规/管制品（枪支配件、违禁品） |

## 11. 专利数据查询（智慧芽 PatSnap，15）

| Slug | 用途 |
|---|---|
| linkfox-zhihuiya-bibliography | 完整著录项目（含优先权、分类、申请人、发明人、引用） |
| linkfox-zhihuiya-simple-bibliography | 简单著录（标题、申请号、公开号、申请日、公开日） |
| linkfox-zhihuiya-claim-data | 权利要求原文 |
| linkfox-zhihuiya-claim-data-translated | 权利要求翻译（中/英/日任一） |
| linkfox-zhihuiya-description-data | 说明书原文 / 实施例 |
| linkfox-zhihuiya-description-data-translated | 说明书翻译（中/英/日任一） |
| linkfox-zhihuiya-abstract-image | 摘要附图（首图 / 代表图） |
| linkfox-zhihuiya-abstract-data-translated | 标题 + 摘要翻译 |
| linkfox-zhihuiya-fulltext-image | 全文附图（所有图） |
| linkfox-zhihuiya-pdf-data | PDF 全文下载路径 |
| linkfox-zhihuiya-patent-family | 同族专利（各国对应） |
| linkfox-zhihuiya-patent-forward-citation | 向前引用：申请过程中引用的专利和文献 |
| linkfox-zhihuiya-patent-cited | 向后引用：该专利被其他专利引用 |
| linkfox-zhihuiya-legal-status | 简单法律状态 + 法律状态 + 法律事件 |
| linkfox-zhihuiya-patent-image-search | 按图片做外观/实用新型相似度检测；法律敏感，相似度高的必须完整展示 + 免责声明 |

> 多个专利查询接口的入参规则：`patentId` 与 `patentNumber` 至少传一个，都存在时优先 `patentId`；多 ID 用英文逗号分隔，单次上限 100 条。

## 12. 多模态 AI / 图像 / 文本 / 视频（4）

| Slug | 用途 |
|---|---|
| linkfox-aigc-imagegen | AI 文生图 / 图生图：BANANA / BANANA_2 / BANANA_PRO / GPT_2_IMAGE / AIDRAW_EDIT / WAN2_7；可控分辨率 + 宽高比 + 数量 |
| linkfox-aigc-imagegen-product | 商品图生成编排：白底图 / 场景图 / 特写图 / 卖点图 / A+ 图 |
| linkfox-aigc-textgen | AI 生文：GEM_3_FLASH（快速）+ GEM_3_1_PRO（高质量）；支持图文结合理解 + OCR + 看图说话 |
| linkfox-aigc-videogen | AI 生视频：KLING / V电影 / WAN万相 / SEED豆包 / HAILUO海螺 / HAPPY_HORSE；单图/多图模式，可控时长 / Pro / 声音 / 运镜 / 尾帧 |

## 13. 辅助 / 协议 / 编排（3）

| Slug | 用途 |
|---|---|
| linkfox-report-generator | **报告硬规则**：所有总结/分析/竞品/市场报告都必须经此 skill 调外部 LLM 生成，**禁止在对话中拼接报告正文**；HTML（默认）/ Markdown，跟随用户语言；ECharts 图表骨架内置 |
| linkfox-task-scheduler | 基础设施 skill：定时任务 / 周期性任务调度 |
| linkfox-superagent-orchestration | 基础设施 skill：多阶段流程编排辅助 |

---

## 用法（meta-skill 内部）

1. **新建模式入口**：作者讲业务需求 → 先扫 `linkfoxagent-v2/` 实时全集，再扫"配方表" `tier1-recipes.yaml` 找命中链路；命中链路的每个 slug 必须回到实时全集确认存在。
2. **不命中时**：在本表按能力桶（§1–§13）找候选 skill；本表只作导航，最终以实时 v2 和 SKILL.md frontmatter 为准。
3. **平台收窄**：候选 ≥ 2 个时，按用户指明的平台进 `tier1-by-platform.md` 收窄。
4. **同能力选型**：同桶多个候选时，依次比较：覆盖站点 → 数据维度（详情/历史/估算/趋势）→ 入参形态（关键词 vs ASIN vs ItemId）→ 计费量级。
5. **缺参 / 选项不明**：必须用运行环境支持的 AskUserQuestion 或等价表单能力一次性收敛，不允许自由文本散问。
6. **任何报告产物**：直接 handoff 给 `linkfox-report-generator`，本 skill 不写报告正文。

## 维护

- 上游 SOT：`../../linkfoxagent-v2/` （团队内部仓库），每个目录一个 SKILL.md。
- 上游有更新时，先以 `scripts/list_v2_skills.py` 的实时结果为准；需要刷新本表时跑 `scripts/list_v2_skills.py --write-indexes <目录>` 生成索引视图后再替换。
- 同步原则：**slug + 用途以 SKILL.md frontmatter 为准**；本目录不是 SOT，允许滞后但不得覆盖实时 v2 判断。
