---
name: profit-calculation-expert
description: 利润核算专家：输入任意数量 ASIN，自动拉取 Keepa 售价/费用 + 1688 采购成本 + 极目退货率/ACoS，用全损退货模型 + 类目 TACoS + 仓储费 + 入库配置费计算完整净利润，输出 HTML 报告。当用户说"算利润"、"利润核算"、"ASIN 利润测算"、"净利润计算"、"profit calculation"、"calculate profit for ASIN"、"check ASIN profitability"、"算算这个 ASIN 能赚多少"时触发。即使用户只说"帮我看看这几个 ASIN 利润怎么样"或"how much can I make on these ASINs"，也应触发本 skill。
---

## 适用场景

输入任意数量亚马逊 ASIN，自动完成"Keepa 拉数据 → 1688 找货源 → 极目查退货率/ACoS → 全成本净利润核算 → HTML 报告"全链路。

| 场景 | 说明 |
|------|------|
| 快速利润评估 | 给几个 ASIN，快速算出净利润和利润率 |
| 批量选品验证 | 上游工具产出候选 ASIN 列表，批量核算利润排序 |
| 成本敏感性分析 | 调整汇率/头程/仓储等参数，看利润变化 |

## 不适用

- 只想查单个 ASIN 详情（直接用 linkfox-keepa-product-request）
- 只想在 1688 找货源（直接用 linkfox-1688-search-by-image）
- 从品牌名出发发现新品并算利润（用 competitor-new-product-profit-analysis）
- 非 FBA 配送商品（成本模型基于 FBA 费率，FBM 商品请用其他工具）
- 无 Keepa 数据的新品 ASIN（S1b 需要历史价格曲线取正常售卖价，新品无历史数据则回退用当前 price）

## 输入参数

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| asins | string | 无（必填） | 逗号分隔的 ASIN 列表，不限数量 |
| domain | int | 1 | 亚马逊站点 ID（1=US, 2=UK, 3=DE, 5=JP...） |
| exchangeRate | float | 7.2 | CNY→USD 汇率 |
| fbaHeadCost | float | 3.0 | FBA 头程物流费（美元/件） |
| adTACoS | float | 10.0 | 回退广告 TACoS（S3 无数据时使用，%） |
| returnRate | float | 15.0 | 回退退货率（S3 无数据时使用，%） |
| disposalFee | float | 0.50 | 弃置费（美元/件） |
| storageRate | float | 0.87 | 月度仓储费率（美元/立方英尺，标准尺寸默认 0.87） |
| inboundPlacementFee | float | 0.40 | 入库配置费（美元/件，自动查表时此参数不生效） |
| nicheKeyword | string | 无 | 极目 niche 关键词，用于 S4 脚本精确匹配退货率/ACoS（可选，不传则按 category 匹配） |

## 已挂载能力约束

| skill | 用途 | 调用位置 | 状态 |
|-------|------|----------|------|
| linkfox-keepa-product-request | 批量获取 ASIN 售价/FBA费/佣金/尺寸 | S1a | 已挂载 |
| linkfox-keepa-product-series | 拉取 buyboxPrice 历史曲线，取正常售卖价 | S1b | 已挂载 |
| linkfox-1688-search-by-image | 1688 以图搜图（B2 路径） | S2b | 已挂载 |
| linkfox-jiimore-get-niche-info-by-keyword | 按关键词查极目 nicheId | S3 | 已挂载 |
| linkfox-aigc-textgen | AIGC 推导 1688 搜索词(S2a) + 多模态验证(S2c) + S3 兜底 | S2a/S2c/S3 | 已挂载 |
| linkfox-amazon-search | 拉关键词 Top 9 竞品图（精算模式） | S2a | 已挂载 |
| linkfox-dld-product-search | 1688 店雷达关键词搜索（B1 路径） | S2b | 已挂载 |
| linkfox-jiimore-get-niche-info | 查极目退货率/ACoS/sponsored% | S3 | 已挂载 |
| linkfox-sif-asin-summary | 查 ASIN 广告关键词数（零广告策略判断） | S4 | 已挂载 |
| linkfox-sif-asin-keywords | 查 ASIN Top 5 流量关键词（AIGC 验证卖点摘要） | S2c | 已挂载 |
| linkfox-report-generator | 生成 HTML 利润分析报告 | S5 | 已挂载 |

## 执行编排

- 第 1 层：S1 Keepa 批量拉取 — S1a 商品详情（每批最多 5 个 ASIN，自动分批，所有批次并行发起）+ S1b 历史时序（每个 ASIN 拉 buyboxPrice 曲线，与 S1a 并行）。
- 第 2 层（并行）：S2 1688 货源匹配（S2a AIGC 推导搜索词+价格区间 → S2b 两路并行采集 → S2c AIGC 多模态验证）+ S3 市场指标获取 — 两者输入都只依赖 S1，同一轮并行发起。
- 第 3 层：S4 净利润核算 — 依赖 S2 的 1688 成本、S3 的退货率/ACoS 和 S1 的 Keepa 数据。
- 第 3.5 层：S4.5 用户决策与重新核算 — 用户确认货源价格/头程后重跑 S4，长期固定参数写入专家级 `MEMORY.md`，下次 agent 自动读取。
- 第 4 层：S5 报告生成 — 依赖 S4（含用户确认值）的合并利润数据。

### 流水线

| 步骤 | 做什么（一句话） | 依赖 | 用途 | 详情 |
|------|----------------|------|------|------|
| S1 Keepa批量拉取 | S1a 商品详情（售价/FBA费/佣金/尺寸/主图/类目）+ S1b 历史时序（buyboxPrice 曲线） | 无 | 为 S2 提供主图、为 S3 提供类目、为 S4 提供费用数据+正常售卖价 | `references/steps/S1.md` |
| S2 1688货源匹配 | S2a AIGC 推导搜索词+价格区间 + S2b 两路并行（B1 店雷达 + B2 以图搜图）+ S2c AIGC 多模态验证，取销量前 3 | S1 | 为 S4 提供 1688 采购成本 | `references/steps/S2.md` |
| S3 市场指标获取 | 按类目三阶段递进查极目退货率+ACoS+sponsored% | S1 | 为 S4 提供实际退货率和类目 TACoS | `references/steps/S3.md` |
| S4 净利润核算 | 全损退货模型+类目TACoS+仓储费+入库配置费，计算净利润 | S1, S2, S3 | 为 S5 报告提供利润排名数据 | `references/steps/S4.md` |
| S4.5 用户决策与重新核算 | 用户确认货源价格/头程后重跑 S4，长期固定参数写入 MEMORY.md | S4 | 用用户确认值替代初步筛选值，提升准确性 | `references/steps/S4.md` |
| S5 报告生成 | 按净利润降序生成 HTML 报告，含成本拆解/图表/洞察 | S4 | 交付最终产物给用户 | `references/steps/S5.md` |

## 报告产物

每次执行生成 HTML 利润分析报告，章节包括：

- **核心指标 KPI 卡片**：ASIN 总数、最高净利润率、平均净利润率、负利润 ASIN 数
- **净利润汇总表**：按净利润降序，含 ASIN/标题/类目/售价/1688成本/FBA费/佣金/广告费/退货损失/仓储费/入库配置费/头程/净利润/净利润率
- **成本拆解瀑布图**：ECharts 瀑布图展示从售价到净利润的成本逐项扣减
- **利润率对比柱状图**：颜色 绿>20% / 黄10-20% / 红<10% / 黑(亏损)
- **1688 货源匹配明细表**：每个 ASIN 3 个供应商对比（含 B1/B2 来源标注 + AIGC 验证结果）
- **货源初步筛选提醒**：醒目展示"利润核算基于初步筛选货源，用户确认货源后可重新核算"
- **关键洞察与建议**：按优先级标注

> ⚠ 如果需要生成报告 / 精美报告，必须去阅读 SKILL `linkfox-report-generator`，根据它的规范来。本 skill 只准备业务数据；样式、排版、md/html 导出、元信息块统统由 `linkfox-report-generator` 负责。不要在此处复制报告样式或 html 模板。

## 执行自检

- [ ] S1 所有 ASIN 都拿到了 price 和 fbaFees，缺失的标注
- [ ] S2 每个 ASIN 至少匹配到 1 个 1688 供应商，不足 3 个的标注
- [ ] S3 每个类目都获得了退货率数据（jiimore 或默认值）
- [ ] S4 仓储费计算使用了 Keepa 返回的包装尺寸（mm→立方英尺换算）
- [ ] S4 所有 11 项成本都已计入净利润
- [ ] 报告的每个章节都有数据来源，无来源章节标"暂无数据"
- [ ] 参数快照已写入报告头

## 已知局限

- Keepa 每次最多查 5 个 ASIN，大量 ASIN 需多批调用，积分消耗与 ASIN 数量成正比
- 1688 以图搜图依赖图片质量，缩略图可能影响匹配精度
- 极目退货率为类目级别，非单个 ASIN 的实际退货率
- 仓储费/弃置费/入库配置费按 FBA 费率表自动查表（根据 Keepa 包装尺寸区分标准/大件 + 旺季费率），费率表见 `references/fba-fee-table.md`
- 入库配置费为均值估算，实际取决于分仓策略（单点入仓$0/件，多点分仓$0.30-$0.40/件）
- 汇率为固定默认值，非实时
- 未包含：VAT 税、退货运费（买家退回运费）、礼品包装费等
- AIGC 入参推导的准确性依赖于亚马逊搜索结果中是否有视觉相似的商品
- 1688 搜索词的准确性依赖于 AIGC 对产品特征的理解，偶发翻译偏差
