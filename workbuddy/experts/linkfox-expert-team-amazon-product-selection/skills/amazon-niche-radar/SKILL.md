---
name: amazon-niche-radar
description: 蓝海扫描专家 — 亚马逊品类市场洞察全流程：输入任意品类关键词或 ASIN，经关键词验证、细分市场发现、7 源并行采集（极目/卖家精灵/前台搜索/ABA/Google Trends/社媒验证/商业洞察）、派生计算与 Top ASIN 深度拆解（Keepa + SIF），输出按数据源分节的多维度 HTML 报告。当用户说"这个产品能不能做"、"这个赛道值得进吗"、"这个品类还能做吗"、"值不值得做这个品类"、"这个 ASIN 所在的市场怎么样"、"这个关键词值得做吗"、"这个词的市场大不大"、"这个搜索词背后的市场怎么样"、"这个词竞争激烈吗"、"帮我做个市场调研"、"分析一下这个品类"、"这个品类市场怎么样"、"赛道分析"、"市场分析报告"、"扫一下这个品类"、"复查一下这个品类"、"这个品类最近变化大吗"、"竞品格局有什么变化"、"category market analysis"、"is this niche worth entering"、"should I enter this category" 时触发。即使用户只说"这个品类竞争大不大"或"这个赛道准入门槛高不高"，没有明说报告或 SOP，也应触发本 skill。
---

## 适用场景

输入一个品类关键词，自动完成关键词验证、类目定位、多源数据采集与多维度分析，输出一份按数据源分节的综合市场洞察 HTML 报告。

| 场景 | 说明 |
|------|------|
| 判断一个产品所在的赛道值不值得进入 | 卖家已有目标产品或 ASIN，需全面评估其所在品类的市场容量、竞争格局、新品友好度、利润空间，决定是否入场 |
| 判断一个关键词市场值不值得进入 | 卖家发现某个搜索词/品类词，需验证该关键词背后的真实市场大小、垄断程度和准入门槛 |
| 竞品格局定期复查 | 已涉足品类的卖家定期复查竞争态势变化（建议搭配定时任务周期执行） |

## 不适用

- 只查单个 ASIN 的详情或销量 → 直接用 `linkfox-keepa-product-request` 或 `linkfox-amazon-product-detail`
- 只查关键词搜索量 → 直接用 `linkfox-aba-intelligent-query`
- 一次性快速问答（"这个品类大概多大"）→ 直接用极目或卖家精灵单次查询回答
- 批量多品类同时分析 → 本 skill 每次只处理一个品类关键词，执行时间长（10-15 分钟）、内容多。如果用户输入多个关键词或多个 ASIN，建议分批次做定时任务查询（使用 `linkfox-task-scheduler`），不要在单次会话中串行跑多个品类

## 输入参数

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| keyword | string | 必填 | 用户输入的品类入口词，如 "pet water fountain"、"yoga mat" |
| country | string | US | 站点代码，目前支持 US |
| report_lang | string | zh | 报告主体语言（zh / en） |

## 已挂载能力约束

| skill | 用途 | 调用位置 | 状态 |
|-------|------|----------|------|
| linkfox-amazon-search | 前台搜索获取商品列表（S1 搜索 3 页 + 降级路径 bestseller 翻页） | S1, S3.2-Fallback | 已挂载 |
| linkfox-sif-asin-keywords | ASIN 流量关键词反查，筛选精准词 | S1 | 已挂载 |
| linkfox-jiimore-get-niche-info-by-keyword | 细分市场洞察（垄断/新品/竞争/趋势） | S2, S3 | 已挂载 |
| linkfox-amazon-category-lookup | 类目节点查询，获取 nodeIdPath | S2 | 已挂载 |
| linkfox-sellersprite-market-statistics | 类目市场统计看板（头部/新品/竞争指标） | S3 | 已挂载 |
| linkfox-aba-intelligent-query | ABA 搜索词趋势与 Top ASIN 点击转化 | S3 | 已挂载 |
| linkfox-google-trend-get-trend-by-keys | Google Trends 关键词 5 年热度趋势 | S3 | 已挂载 |
| linkfox-tsearch-search | 社媒趋势验证（Reddit/TikTok 网络搜索） | S3 | 已挂载 |
| linkfox-amazon-opportunity-report-by-keyword | 亚马逊商业洞察报告（六维分析） | S3 | 已挂载 |
| linkfox-keepa-product-series | Keepa 历史时序数据（价格/BSR/评论/销量） | S6 | 已挂载 |
| linkfox-keepa-product-request | Keepa 商品详情（售价/FBA费/佣金/包装尺寸/类目路径） | S2-A（S6.4-A 缓存复用） | 已挂载 |
| linkfox-sif-asin-summary | SIF ASIN 流量来源构成与曝光分布 | S6 | 已挂载 |
| linkfox-1688-search-by-image | 1688 以图搜图找同款货源 | S6.4-B | 已挂载 |
| linkfox-dld-product-search | 1688 店雷达关键词搜索（工厂货源筛选） | S6.4-B | 已挂载 |
| linkfox-aigc-textgen | AIGC 多模态分析（B1 入参推导 + 货源验证） | S6.4-B | 已挂载 |
| linkfox-report-generator | HTML 报告生成 | S5 | 已挂载 |

## 执行编排

- **第 1 层（串行）**：S1 关键词验证 —— 必须先完成，产出精准关键词和 Top ASIN（销量最高非广告 ASIN）
- **第 2 层（并行）**：S2-A 类目节点查询 + S2-B 细分市场发现 —— 两者都依赖 S1 但互不依赖，同一轮并行发起
- **第 3 层（并行 + 条件串行）**：S3 数据采集 —— S3.3 复用 S1.1 的 3 页数据不重复搜索；S3.1 极目（复用 S2-B 缓存）/ S3.2 卖家精灵 / S3.3 前台搜索（复用 S1.1）/ S3.4 ABA(2次) / S3.5 Google Trends(5次) / S3.7 商业洞察报告 **六路同时发起，互不依赖**；**S3.6 社媒验证为条件触发步骤**，须等 S3.4 + S3.5 均返回后判断触发条件（Google Trends 年度均值增长 ≥50% 或 ABA 排名 26 周内变化 ≥30%），满足则执行三次 tsearch 网络搜索，不满足则跳过。S4 须等 S3.6 完成或确认跳过后才进入
- **第 4 层（串行）**：S4 派生计算 —— 依赖 S3 全部返回
- **第 5 层（串行）**：S5 报告生成 —— 依赖 S4
- **第 6 层（并行+串行）**：S6 Top ASIN 深度拆解 + 利润核算 —— 复用 S1 的 Top ASIN + 3 页搜索数据 + S2-A 的 Keepa 缓存（S6.4-A 不需实际调用）。S6.1 Keepa历史 + S6.2 SIF概览 + S6.3 SIF关键词 三路并行；同时 AIGC 入参推导（读 S2-A 缓存 + S1.1 的 3 页数据 Top 9 商品图）；然后 B1 店雷达 + B2 以图搜图 两路并行；再串行 AIGC 验证（标题预筛选 + 多模态对比）；最后 S6.4-C 净利润核算串行（复用 S2-A Keepa 数据 + S6.4-B 货源数据，含零广告策略判断）

## 流水线

| 步骤 | 做什么（一句话） | 依赖 | 用途 | 详情 |
|------|----------------|------|------|------|
| S1 关键词验证 | 前台搜索 3 页一次搜完 → 取销量最高非广告 ASIN（+ S3.3 数据复用）→ SIF 反查筛 isMainKw/isAccurateKw → 得精准词 | 无 | 为 S2/S3/S6 提供精准关键词、Top ASIN 和前台搜索 3 页数据 | `references/steps/S1.md` |
| S2 类目与细分市场发现 | 并行：S2-A 用 Top ASIN 调 Keepa 获取 categoryTreeId + 商品详情（S6.4-A 缓存复用）+ S2-B jiimore 查 niche 列表并与 SIF 标签词交叉验证 | S1 | 为 S3 提供 nodeIdPath，为 S6.4-A 预取 Keepa 数据 | `references/steps/S2.md` |
| S3 六源并行采集 | S3.3 复用 S1.1 数据不重复搜索；并行调用极目/卖家精灵统计/ABA(2次)/Google Trends(5次)/社媒验证(条件触发)/商业洞察报告 | S1, S2 | 为 S4 提供全量原始数据 | `references/steps/S3.md` |
| S4 派生计算 | Python 脚本对四源数据做 CR3/CR5、价格分布、评分分布、产品形态分类等派生统计 | S3 | 为 S5 报告提供所有派生指标 | `references/steps/S4.md` |
| S5 报告生成 | 按 linkfox-report-generator 规范写 HTML 片段 → 注入模板 → 输出最终报告 | S4 | 交付最终 HTML 报告 | `references/steps/S5.md` |
| S6 Top ASIN 深度拆解+利润核算 | 复用 S1 的 Top ASIN + 3 页搜索数据 + S2-A 的 Keepa 缓存，三路并行跑 Keepa历史 + SIF概览 + SIF关键词 → AIGC 入参推导 → B1 店雷达 + B2 以图搜图 两路并行 → AIGC 验证 → 串行算净利润（含零广告策略判断） | S1, S2-A, S2-B | 为报告追加头部竞品深度拆解+利润核算章节 | `references/steps/S6.md` |

## 报告产物

报告按**数据源分节**，每个数据源独立做自己的多维度分析，末尾标注 data-source。综合研判章节跨源汇总。结构如下：

### 报告章节

1. **极目细分市场洞察**（数据源：jiimore-get-niche-info-by-keyword，多 niche 对比，S2-B 最早获取）
   - 搜索量与趋势：每个已验证 niche 的周/季度搜索量、增长率
   - 垄断程度：每个 niche 的 Top5 品牌点击份额、Top5 商品点击份额、品牌数、平均品牌年龄
   - 新品成功率：每个 niche 的上架数/成功数/成功率
   - 竞争指标：每个 niche 的 CPC 三档、ACoS、退货率、毛利率 >50% SKU 占比
   - 多 niche 对比表：已验证 niche 间的关键指标横向对比（搜索量、均价、垄断度、新品成功率）
2. **亚马逊前台搜索分析**（数据源：amazon-search × 3 页，默认相关性排序，S1.1 获取，S3.3 复用）
   - 流量聚集度：首页 vs 二页 vs 三页销售额对比，判断首页是否垄断
   - 商品集中度：按 position 排序的销量帕累托图 + 累计占比，找到销量剧减拐点
   - 品牌集中度：Top 15 品牌销量帕累托图 + 累计占比 + CR3/CR5，判断品牌垄断程度
   - 价格分布：按 $0-15/15-30/30-60/60-100/100-200/200+ 分桶，商品数 + 销量占比
   - 上架时间分布：按 1月/3月/半年/1年/2年/3年/3年+ 分桶，判断新品冲排名难度
   - 上架趋势分布：按上架年份分桶，判断市场迭代速度
   - 评分数分布：按 无/1-50/50-100/100-200/200-500/500+ 分桶，判断评论门槛
   - 评分值分布：按 <3.0/3.0-3.5/3.5-4.0/4.0-4.2/4.2-4.5/4.5+ 分桶，识别低分高销量竞品
   - 卖家类型分布：FBA / AMZ / 其他占比
   - 卖家所属地分布：各国商品数 + 销量占比，判断中国卖家竞争强度
   - 变体复杂度：有 options 字段的商品占比
3. **卖家精灵类目统计**（数据源：sellersprite-market-statistics，S3.2 获取）
   - 3.1 类目市场规模：总商品数、品牌数、卖家数、月均销量/销售额、年化估算、平均每商品卖家数（竞争密度）、市场上架时间跨度（firstShelfDate→lastShelfDate）、平均重量/体积（物流与仓储成本参考）
   - 3.2 头部集中度（对比柱状图：头部 Top10 vs 类目均值）：销量倍数、收入倍数、价格策略对比（头部均价 vs 类目均价）、评分优势对比、评论壁垒对比（头部评论数 + 月增长 vs 均值）、BSR 排名优势量化
   - 3.3 新品表现（对比柱状图：新品 vs 类目均值）：新品数量/占比（市场活力）、新品销量 vs 均值（新品是否能达到类目平均水位）、新品收入 vs 均值、新品定价策略（新品均价 vs 类目均价）、新品评分差距、新品评论门槛区间（minNewRatings→maxNewRatings，最低多少条评论能进榜）
4. **ABA 搜索词分析**（数据源：aba-intelligent-query，两次查询）
   - 4.1 Part A — 5 关键词搜索排名分析（SIF 标签词 Top 5 的 ABA 排名对比）
     - 排名趋势对比折线图（26 周，5 条线，Y 轴反向）
     - 排名波动率（变异系数 CV，判断热度稳定性）
     - 趋势方向（前半段 vs 后半段均值，改善/恶化百分比）
     - 周环比改善/恶化次数
     - 最佳/最差排名区间
     - 热度梯队分层表（按最新排名分梯队 + SIF 搜索量 + 趋势判断）
   - 4.2 Part B — 种子词 Top ASIN 点击转化分析
     - Top3 点击集中度 + 转化集中度周趋势（双折线图）
     - 最新一周 Top3 ASIN 点击 vs 转化对比柱状图
     - 点击-转化效率比（conversionShare ÷ clickShare，识别高转化潜力品）
     - 头部 ASIN 更替频率（26 周内 Top1 ASIN 变化次数）
5. **Google Trends 关键词热度分析**（数据源：google-trend-get-trend-by-keys，5 词 × 5 年）
   - 5 年周维度趋势对比折线图（支持 dataZoom 缩放）
   - 年度均值对比表（6 年 × 5 词）
   - 5 年趋势方向（首年均值 vs 末年均值）
   - Google Trends vs ABA 交叉验证表（趋势方向一致性 / 分歧 / 无法对比）
   - 社媒趋势验证（条件触发：仅当 Google Trends 出现显著趋势变化时）：搜索 Reddit/TikTok 真实讨论，验证趋势驱动因素（如 TikTok 复古风潮、数字排毒运动等），Quote Cards 展示关键帖子摘要
6. **亚马逊商业洞察报告**（数据源：amazon-opportunity-report-by-keyword，条件触发）
   - 市场潜力：年搜索量、YoY 增长率、近 90 日趋势、销售额、缺货率
   - 竞争结构：在售产品数、品牌数变化、Top5 品牌 Click Share、新品上线数
   - 产品特征：决胜属性（标配层）+ 溢价属性（差异化层）
   - 评价质量：平均评分、差评痛点分布
   - 客户画像：买家年龄段、收入区间、使用场景
   - 定价分析：价格带分布、甜蜜区、空白价格段
   - 跨源交叉验证：洞察报告的 YoY 增长 vs Google Trends 年度均值变化；差评痛点 vs 前台搜索低分高销量竞品；价格甜蜜区 vs 前台搜索价格分布；客户画像 vs 产品形态分类
7. **Top ASIN 深度拆解**（数据源：keepa-product-series + sif-asin-summary + sif-asin-keywords + keepa-product-request + 1688-search-by-image）
   - 7.1 Keepa 历史数据解读（Read `references/keepa-interpretation.md` 获取 8 维度解读规范）：价格波动分析、BSR 排名稳定性、Deal 依赖判断、评论增长趋势、评分波动、月销量趋势、价格-BSR 相关性、生命周期阶段
   - 7.2 SIF 流量结构解读（Read `references/sif-asin-interpretation.md` 获取 8 维度解读规范）：流量来源构成、曝光趋势、关键词覆盖广度、关键词流动性、AC 标签分析、推荐位曝光、变体流量分布、广告投放强度
   - 7.3 SIF 关键词反查：Top 10 流量词表（关键词/搜索量/流量份额/自然排名/标签），头部关键词流量集中度
   - 7.4 1688 货源匹配与净利润核算：B1 店雷达 + B2 以图搜图两路结果并列展示（不截断 Top N，展示全部通过 AIGC 验证的候选，含匹配/部分匹配标注 + 一句话理由），11 项全量成本拆解表（1688成本/FBA费/佣金/广告费/退货损失/仓储费/入库配置费/头程），净利润与净利润率，零广告策略或市场均值 ACoS 策略标注，成本拆解瀑布图，货源初步筛选提醒（待用户手工确认后重新核算）
8. **综合研判**（跨源汇总）
   - SWOT Grid
   - Insight List（行动建议）

### 报告规则

- 每个数据源章节只分析该数据源返回的字段，不混用其他数据源的数据做同一维度分析
- 每个含统计数字的章节末尾必须标注 data-source（skill 短名）
- 派生计算的章节在 data-source 中追加 .ds-computed 子块，列出指标名与计算方式
- 各数据源之间可能出现同一指标的不同口径值（如 "市场销量"），这属于多角度交叉验证，不是数据冲突
- **降级路径适配**：当 sellersprite-market-statistics 返回空数据时，第 3 节「卖家精灵类目统计」自动切换为降级看板（详见 S3.md S3.2-Fallback + S5.md 降级适配），输出三列看板 + 11 维度图表，data-source 标注 `amazon-search (bestseller fallback)`

### 报告完整性硬约束（违反即视为报告不合格）

1. **维度零遗漏**：上述每个章节中列出的**每一个分析维度**都必须在报告中出现，禁止以"数据不重要"或"篇幅有限"为由跳过任何维度。若某维度的数据源返回空/失败，必须在报告中保留该维度的标题并注明"数据未获取"（如 SIF 概览返回空时，8.2 的 8 个维度仍需逐一列出标题并标注"数据未获取"）

2. **图表+文字双重输出**：每个有图表/表格的维度，**必须配一段文字解读**（至少 2 句话），说明数据含义和业务洞察。禁止只放图表/表格不写解读——图表展示"是什么"，文字解读"意味着什么"

3. **指标全量展示**：要求中列出的每个指标都必须展示。例如第1章要求"CPC 三档、ACoS、退货率、毛利率>50% SKU 占比"，则在 niche 对比表或独立表格中必须包含这 4 个指标列，不可只展示部分

4. **数据缺失的处理规范**：
   - 数据源返回空/失败时：保留章节标题 + 注明"数据未获取" + 说明原因（如"5个精准词全部返回4004"）
   - 降级路径下不可算的字段：标注"数据未提供"（如 sellers/avgSellers/avgProfit 等）
   - 条件触发步骤未触发时：注明触发条件及判断结果（如"Google Trends 年度增长 <50%，未触发社媒验证"）
   - **禁止静默跳过**：任何章节/维度缺失都必须在报告中有显式说明，不能直接消失

5. **章节编号对齐**：报告中的章节编号和标题必须与上述要求一一对应。例如要求中"2.6 销量天花板"，报告中必须用相同或包含"销量天花板"的标题，不可改用其他名称导致对应关系丢失

> **如果需要生成报告 / 精美报告，必须去阅读 SKILL `linkfox-report-generator`，根据它的规范来。**
> 本 skill 只负责把业务数据准备好；样式、排版、md/html 导出、元信息块统统由 `linkfox-report-generator` 负责。
> 不要在此处复制报告样式或 html 模板。

## 执行自检

每次跑完流程，agent 在收尾时确认：

- [ ] S1 成功获取精准关键词（isMainKw/isAccurateKw 标签验证通过）
- [ ] S2 成功获取 nodeIdPath 和 nicheTitle 列表
- [ ] S3 四个数据源全部返回非空数据（errcode=200）
- [ ] **S3.6 社媒验证已检查触发条件**：若 Google Trends 年度均值增长≥50%或ABA排名变化≥30%，确认已执行 tsearch 搜索（脚本路径 `linkfox-tsearch-search/scripts/tsearch_web_search.py`，参数仅 `keyword` 字段）
- [ ] **S3.7 商业洞察报告已尝试重试**：首个关键词返回 4004 时，依次尝试 SIF 精准词 Top 5（脚本调用须加 `--inline` 标志）
- [ ] S4 派生计算 JSON 包含报告所需全部指标
- [ ] S5 报告 HTML 成功落盘，路径已告知用户
- [ ] **Section 3（卖家精灵类目统计）使用了 `sellersprite-dashboard.md` 模板的三列看板布局**
- [ ] **S6.4 利润核算已完成**：S6.4-A Keepa详情获取了 fbaFees/referralFeePercentage/包装尺寸；S6.4-B 1688匹配到至少1个供应商；S6.4-C 11项成本全部计算并输出净利润
- [ ] **S6.4-B AIGC 入参推导已完成**：从 S1.1 的 3 页数据 Top 9 非广告商品 + 目标 ASIN 主图调用 AIGC，产出 keyWord + beginPrice/endPrice
- [ ] **S6.4-B AIGC 验证已完成**：B1+B2 结果经标题预筛选 + AIGC 多模态验证，保留匹配和部分匹配的候选
- [ ] **S6.4-C 零广告策略已判断**：S6.2 sponsoredProductsKeywordCount=0 时广告费=$0，否则用 nicheTACoS（回退 adTACoS）
- [ ] **S6.4-B 结果分别展示**：B1 和 B2 结果并列展示，不自动合并，由用户决策
- [ ] 报告每个章节都有 data-source 标注
- [ ] 如果某个数据源调用失败，在报告对应章节注明"数据未获取"

## 已知局限

- 目前仅支持美国站（US），其他站点需等待各 Tier 1 skill 扩展支持
- SIF 反查的 isMainKw/isAccurateKw 标签依赖于 SIF 数据更新周期，可能存在延迟
- jiimore 查询词如果过于长尾可能返回空结果，需要按搜索量降序依次重试
- amazon-category-lookup 的类目匹配基于名称模糊搜索，可能需要人工确认最匹配的节点
- ABA 数据为周维度，非日维度；排名越小热度越高
- 前台搜索 3 页约返回 150 个商品（默认相关性排序），不代表全量市场，仅反映该关键词下的竞争格局；降级路径下动态翻页直到 100 个非广告商品（bestseller 排序）
- 各数据源统计口径不同（如销量估算算法不同），同一指标可能出现不同数值，属正常交叉验证现象
