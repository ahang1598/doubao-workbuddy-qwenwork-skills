# Linkfox 亚马逊选品专家团

WorkBuddy Team 型专家团包，包含 1 位主理人和 26 位亚马逊选品专家。

## 入口

- 主理人：linkfox-amazon-product-selection-team-lead
- 配置：.codebuddy-plugin/plugin.json
- 设置：settings.json

## 成员

- $(@{id=linkfox-expert-1688-sourcing-expert; name=1688找货源专家; desc=面向亚马逊卖家的 1688 找货源与利润分析，覆盖供应商匹配、以图验证、FBA 成本和净利润排序。; description=面向亚马逊卖家的 1688 找货源与利润分析专家。适用于用户提供 ASIN 后，需要匹配 1688 供应商、以图验证货源、核算 FBA 成本，或按预期净利润对货源排序的场景。; deps=System.Object[]}.id): 1688找货源专家 - 面向亚马逊卖家的 1688 找货源与利润分析，覆盖供应商匹配、以图验证、FBA 成本和净利润排序。
- $(@{id=linkfox-expert-aba-new-keyword-miner; name=ABA新词挖掘专家; desc=基于亚马逊 ABA 挖掘新词、趋势词、长尾词和类目机会词，并支持表格导出。; description=亚马逊 ABA 新词挖掘专家。适用于季节性爆发词、趋势词、排名跃升词、长尾联想词、Widget 类目卡关键词发现，以及 CSV/Excel 关键词导出的场景。; deps=System.Object[]}.id): ABA新词挖掘专家 - 基于亚马逊 ABA 挖掘新词、趋势词、长尾词和类目机会词，并支持表格导出。
- $(@{id=linkfox-expert-alexa-prompt-product-selection; name=Alexa 提示词选品专家; desc=用 Alexa 提示词和市场数据驱动亚马逊选品研究，支持自动执行与报告输出。; description=基于 Alexa 提示词的亚马逊选品研究专家。适用于需要结合市场数据生成 Alexa 购物提示词、COSMO 关系提示词、战略选品问题、自动化执行和提示词驱动选品报告的场景。; deps=System.Object[]}.id): Alexa 提示词选品专家 - 用 Alexa 提示词和市场数据驱动亚马逊选品研究，支持自动执行与报告输出。
- $(@{id=linkfox-expert-all-category-listing-scout; name=全品类铺货专家; desc=面向亚马逊全品类铺货，支持跨类目商品发现、批量筛选和 Listing 导向机会评估。; description=亚马逊全品类铺货与 Listing 选品专家。适用于跨类目铺货、批量发现商品机会、Listing 导向选品、全类目筛选和卖家精灵数据筛品的场景。; deps=System.Object[]}.id): 全品类铺货专家 - 面向亚马逊全品类铺货，支持跨类目商品发现、批量筛选和 Listing 导向机会评估。
- $(@{id=linkfox-expert-amazon-competitor-monitor; name=亚马逊竞品动态监控专家; desc=持续监控亚马逊竞品 ASIN 的价格、BSR、评论和 Listing 变化，并输出动态报告。; description=亚马逊竞品动态监控专家。适用于周期性跟踪竞品 ASIN、价格变化、BSR 波动、评论变化、Listing 改动、定时提醒和竞品动态报告的场景。; deps=System.Object[]}.id): 亚马逊竞品动态监控专家 - 持续监控亚马逊竞品 ASIN 的价格、BSR、评论和 Listing 变化，并输出动态报告。
- $(@{id=linkfox-expert-amazon-fba-inventory-planner; name=亚马逊FBA库存计划专家; desc=面向亚马逊 FBA 的库存规划与补货测算，覆盖销量速度、安全库存和风险检查。; description=亚马逊 FBA 库存计划与补货专家。适用于库存规划、销量速度估算、补货时间计算、安全库存设置、库存风险检查、FBA 补货测算和库存计划报告的场景。; deps=System.Object[]}.id): 亚马逊FBA库存计划专家 - 面向亚马逊 FBA 的库存规划与补货测算，覆盖销量速度、安全库存和风险检查。
- $(@{id=linkfox-expert-asin-keepa-curve-analyst; name=ASIN-Keepa曲线解读专家; desc=深度解读 ASIN Keepa 曲线和竞品生命周期，覆盖价格、BSR、销量、评论和流量结构。; description=ASIN Keepa 曲线与竞品生命周期分析专家。适用于深度诊断亚马逊 ASIN 的价格历史、BSR、销量趋势、评论增长、流量结构、生命周期阶段，并生成完整 HTML 竞品报告的场景。; deps=System.Object[]}.id): ASIN-Keepa曲线解读专家 - 深度解读 ASIN Keepa 曲线和竞品生命周期，覆盖价格、BSR、销量、评论和流量结构。
- $(@{id=linkfox-expert-beginner-sellersprite-scout; name=新手推荐选品专家-卖家精灵; desc=为亚马逊新手卖家提供保守、易操作的卖家精灵数据选品推荐。; description=面向新手卖家的卖家精灵选品推荐专家。适用于新手需要保守筛选条件、易操作细分市场、低门槛商品机会、选品指导和卖家精灵数据支撑筛品的场景。; deps=System.Object[]}.id): 新手推荐选品专家-卖家精灵 - 为亚马逊新手卖家提供保守、易操作的卖家精灵数据选品推荐。
- $(@{id=linkfox-expert-blue-ocean-market-scanner; name=蓝海扫描专家; desc=亚马逊蓝海品类市场扫描，覆盖多源洞察、竞争分析、Top ASIN 拆解与利润核算。; description=亚马逊蓝海品类市场扫描专家。适用于用户提供品类关键词或 ASIN 后，需要多源市场洞察、关键词验证、趋势分析、竞争格局扫描、Top ASIN 拆解、利润核算或 HTML 品类报告的场景。; deps=System.Object[]}.id): 蓝海扫描专家 - 亚马逊蓝海品类市场扫描，覆盖多源洞察、竞争分析、Top ASIN 拆解与利润核算。
- $(@{id=linkfox-expert-cross-cultural-product-scout; name=跨文化选品专家; desc=按目标国家或地区进行跨文化选品，结合本地生活方式、节日气候和多源数据验证。; description=跨文化电商选品专家。适用于用户提供目标国家或地区后，需要结合当地文化、生活方式、节日气候、1688 采购关键词、Alexa 提示词和多源验证来发现商品机会的场景。; deps=System.Object[]}.id): 跨文化选品专家 - 按目标国家或地区进行跨文化选品，结合本地生活方式、节日气候和多源数据验证。
- $(@{id=linkfox-expert-google-search-researcher; name=谷歌搜索专家; desc=用 Google AI Mode 做跨境电商网页研究，输出带引用的消费者、趋势和市场洞察。; description=面向跨境电商的 Google AI Mode 搜索研究专家。适用于需要带引用的最新 Google AI Overview 结果，用于海外消费者偏好、产品趋势、市场问题、技术趋势或连续追问式网页调研的场景。; deps=System.Object[]}.id): 谷歌搜索专家 - 用 Google AI Mode 做跨境电商网页研究，输出带引用的消费者、趋势和市场洞察。
- $(@{id=linkfox-expert-keyword-mining-expert; name=关键词挖掘专家; desc=挖掘和扩展亚马逊关键词，支持种子词、流量词、反查 ASIN 和搜索词筛选。; description=亚马逊关键词挖掘与扩展专家。适用于关键词发现、种子词扩展、流量词挖掘、反查 ASIN 关键词、搜索词筛选，以及为亚马逊选品研究生成关键词列表的场景。; deps=System.Object[]}.id): 关键词挖掘专家 - 挖掘和扩展亚马逊关键词，支持种子词、流量词、反查 ASIN 和搜索词筛选。
- $(@{id=linkfox-expert-low-inventory-product-selection; name=不压库存选品专家; desc=面向轻资产卖家的亚马逊不压库存选品，重点筛选 FBM、自发货和低库存风险机会。; description=面向轻资产卖家的亚马逊不压库存选品专家。适用于寻找 FBM、自发货、低库存压力机会，尤其是满足月销量、近期上架和库存风险约束的商品筛选场景。; deps=System.Object[]}.id): 不压库存选品专家 - 面向轻资产卖家的亚马逊不压库存选品，重点筛选 FBM、自发货和低库存风险机会。
- $(@{id=linkfox-expert-low-price-long-tail-selector; name=低价长尾选品专家; desc=面向亚马逊低价长尾市场，筛选低竞争关键词机会和低价商品想法。; description=亚马逊低价长尾选品专家。适用于寻找低价长尾商品、低价细分关键词机会、低竞争长尾产品想法，以及按长尾需求和价格筛选商品的场景。; deps=System.Object[]}.id): 低价长尾选品专家 - 面向亚马逊低价长尾市场，筛选低竞争关键词机会和低价商品想法。
- $(@{id=linkfox-expert-low-price-product-expert; name=低价商品专家; desc=面向亚马逊低价商品机会，支持价格带、平价细分市场和低客单商品筛选。; description=亚马逊低价商品选品专家。适用于寻找或评估低价商品、价格带机会、平价细分市场、小额客单商品，以及按低售价过滤商品的场景。; deps=System.Object[]}.id): 低价商品专家 - 面向亚马逊低价商品机会，支持价格带、平价细分市场和低客单商品筛选。
- $(@{id=linkfox-expert-new-release-product-scout; name=研发新品榜专家; desc=挖掘亚马逊新品榜机会，覆盖 New Release 商品、轻量卖家机会、FBA/FBM 和表格导出。; description=亚马逊新品榜选品专家。适用于挖掘 New Release 标识商品、销量适中的新品、轻量级中国卖家机会、FBA/FBM 商品、排序切换、定时选品和 Excel 导出的场景。; deps=System.Object[]}.id): 研发新品榜专家 - 挖掘亚马逊新品榜机会，覆盖 New Release 商品、轻量卖家机会、FBA/FBM 和表格导出。
- $(@{id=linkfox-expert-opportunistic-product-scout; name=投机选品专家; desc=面向亚马逊短窗口和趋势型机会，寻找高上行空间商品并提示风险。; description=亚马逊投机型选品专家。适用于寻找短窗口机会、趋势型商品、快速增长商品、高上行空间产品，并需要明确识别风险的选品场景。; deps=System.Object[]}.id): 投机选品专家 - 面向亚马逊短窗口和趋势型机会，寻找高上行空间商品并提示风险。
- $(@{id=linkfox-expert-potential-market-scout; name=潜力市场专家; desc=寻找亚马逊潜力市场和上升期商品，支持销量上限、近期上架、排序切换和表格导出。; description=亚马逊潜力市场选品专家。适用于寻找中等销量增长商品、新兴市场机会、月销量上限内的上升产品、近期上架筛选、排序切换、分页巡检、定时选品和 Excel 导出的场景。; deps=System.Object[]}.id): 潜力市场专家 - 寻找亚马逊潜力市场和上升期商品，支持销量上限、近期上架、排序切换和表格导出。
- $(@{id=linkfox-expert-profit-calculation-expert; name=利润核算专家; desc=核算亚马逊商品利润，覆盖 FBA 费用、到岸成本、佣金、广告、退货率、净利率和 ROI。; description=亚马逊商品利润核算专家。适用于核算 FBA 费用、头程到岸成本、佣金、仓储或弃置费用、广告假设、退货率影响、净利润、利润率、ROI 和商品盈利对比的场景。; deps=System.Object[]}.id): 利润核算专家 - 核算亚马逊商品利润，覆盖 FBA 费用、到岸成本、佣金、广告、退货率、净利率和 ROI。
- $(@{id=linkfox-expert-quality-listing-scout; name=精品铺货专家; desc=面向亚马逊精品铺货，筛选 BSR 上升、近期上架、评分达标的高质量 Listing 机会。; description=亚马逊精品铺货选品专家。适用于寻找 BSR 上升、近期上架、满足评分阈值的商品机会，进行精品 Listing 机会筛选、宽口径铺货筛选、排序切换或仅输出 Excel 的场景。; deps=System.Object[]}.id): 精品铺货专家 - 面向亚马逊精品铺货，筛选 BSR 上升、近期上架、评分达标的高质量 Listing 机会。
- $(@{id=linkfox-expert-sales-surge-product-scout; name=销量飙升榜专家; desc=挖掘亚马逊销量快速上升商品，支持月销量、环比增长、定时巡检和 Excel 输出。; description=亚马逊销量飙升榜选品专家。适用于寻找满足月销量和环比增长阈值的商品、快速上升机会、排序切换、重复巡检、定时任务和仅 Excel 交付的场景。; deps=System.Object[]}.id): 销量飙升榜专家 - 挖掘亚马逊销量快速上升商品，支持月销量、环比增长、定时巡检和 Excel 输出。
- $(@{id=linkfox-expert-serp-market-structure-analyst; name=前三页市场格局分析专家; desc=分析亚马逊前三页 SERP 市场结构，覆盖竞争、排名、价格、评论、品牌集中度和新品机会。; description=亚马逊前三页 SERP 市场格局分析专家。适用于分析页面级竞争、自然排名结构、价格分布、评论分布、品牌与卖家集中度、新品机会，并生成 SERP 市场报告的场景。; deps=System.Object[]}.id): 前三页市场格局分析专家 - 分析亚马逊前三页 SERP 市场结构，覆盖竞争、排名、价格、评论、品牌集中度和新品机会。
- $(@{id=linkfox-expert-single-variation-potential-scout; name=潜力单变体专家-卖家精灵; desc=基于卖家精灵筛选亚马逊潜力单变体商品，强调结构简单、增长信号和开发路径清晰。; description=基于卖家精灵的亚马逊潜力单变体选品专家。适用于寻找变体结构简单、变体复杂度低、具备销量或增长信号、开发路径更清晰的单变体商品机会。; deps=System.Object[]}.id): 潜力单变体专家-卖家精灵 - 基于卖家精灵筛选亚马逊潜力单变体商品，强调结构简单、增长信号和开发路径清晰。
- $(@{id=linkfox-expert-tro-risk-advisor; name=TRO风险提示专家; desc=对跨境电商 POD 商品图片或文本进行 TRO 与知识产权风险分级提示。; description=跨境电商 POD TRO 与知识产权风险提示专家。适用于用户提供商品图片或文本后，需要快速评估版权、商标、名人、品牌、体育、大学、宗教或平台侵权风险等级的场景。; deps=System.Object[]}.id): TRO风险提示专家 - 对跨境电商 POD 商品图片或文本进行 TRO 与知识产权风险分级提示。
- $(@{id=linkfox-expert-unmet-demand-miner; name=未满足需求挖掘专家; desc=从亚马逊评论和市场信号中挖掘客户痛点、未满足需求、产品缺口和改良机会。; description=亚马逊商品与细分市场未满足需求挖掘专家。适用于发现客户痛点、未满足需求、评论驱动的产品缺口、改良机会，以及从需求缺口生成产品概念的场景。; deps=System.Object[]}.id): 未满足需求挖掘专家 - 从亚马逊评论和市场信号中挖掘客户痛点、未满足需求、产品缺口和改良机会。
- $(@{id=linkfox-expert-voc-insight-analyst; name=VOC洞察专家; desc=结构化分析亚马逊评论 VOC，覆盖人群、场景、好评、差评、未满足需求和购买动机。; description=亚马逊评论 VOC 洞察分析专家。适用于用户提供 ASIN、标题、五点描述或评论数据后，需要结构化分析人群、使用场景、好评点、差评点、未满足需求和购买动机的场景。; deps=System.Object[]}.id): VOC洞察专家 - 结构化分析亚马逊评论 VOC，覆盖人群、场景、好评、差评、未满足需求和购买动机。

## 默认用法

用户可输入关键词、ASIN、类目、价格带、目标站点或选品目标，由主理人按任务复杂度调度对应专家协作，并输出选品结论、推荐等级和后续动作。
