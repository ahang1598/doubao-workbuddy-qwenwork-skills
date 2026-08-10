# 直接个股筛选

## 适用场景

用户要求根据明确条件、市场、指数、股票池，或净资产收益率（ROE）、市盈率（PE）、股息率、成长、流动性、订单证据等条件筛选股票。

直接筛选仍需要解释筛选条件与股票结论的关系。不能只输出命中列表；必须说明股票池来源、过滤条件、风险处理、数据缺口和候选分组。

## 必读资源

- `references/delivery-workflow.md`
- `references/formal-report-execution-contract.md`
- `references/report-quality-gate.md`
- `references/scope-context-rules.md`
- `references/research-depth-rules.md`
- `references/company-analysis-dimensions.md`
- `references/strategy-factor-library.md`
- `references/metric-definitions.md`
- `references/screening-and-ranking-rules.md`
- `references/risk-handling.md`
- `references/data-freshness-and-conflicts.md`
- `references/broker-research-usage.md`
- `references/evidence-sources.md`
- `references/visualization-rules.md`
- `templates/stock-screening-report.md`
- `templates/direct-stock-screening.md`
- `templates/market-valuation-table.md`

## 输入识别

提取市场、证券类型、股票池、指数/板块、指标、阈值、策略风格、排序字段、排除条件、风险偏好、时间窗口和输出形式。若用户给定固定股票池，不主动扩展，除非用户明确要求。

区分必要条件、辅助确认和表达约束。用户明确给出的硬条件应优先执行；用户未指定的财务、估值、交易、资金和风险维度作为基础体检。

## 股票池构建

- 全市场或指数股票池：使用金融结构化数据检索，当前工具为 `seed_finance_search`。
- 用户指定列表：只使用用户指定标的。
- 行业或主题限定股票池：先进入对应执行手册，再执行条件过滤。
- 策略风格筛选：读取 `references/strategy-factor-library.md`，把必要条件和辅助确认拆开。

## 检索计划

最新价、最近交易日涨跌幅、5 日涨跌幅、20 日涨跌幅、年初至今涨跌幅、市值、估值、财务、分红、流动性、资金、风险标记、成分股和机构预测优先使用 `seed_finance_search`；订单、客户、业务进展、公告原文、公司 IR、政策和非结构化证据使用 `general_search`。

正式筛选中，只要涉及候选质量、未来业绩、行业/主题/产业链/策略背景或重点候选展开，默认按 `references/formal-report-execution-contract.md` 和 `references/broker-research-usage.md` 尝试检索券商研报。只有用户明确要求极简名单、不要研报，或检索工具不可用时，才可不展开研报；此时必须说明研报缺口，不能把未检索写成无影响。

## 分析步骤

1. **执行正式报告合同。** 若不是极简任务，先按 `references/formal-report-execution-contract.md` 准备范围背景包、股票池和证据包、财务/估值/交易/资金体检包、券商研报和权威观点包。
2. **转写透明规则。** 将自然语言条件转成市场、股票池、必要条件、辅助确认、排序/分组依据和风险处理方式。
3. **补充范围背景。** 若股票池来自行业、主题、指数、市场或指标条件，按 `references/scope-context-rules.md` 先说明当前状态和指标分布，并用背景表、筛选漏斗或指标分布图支撑。
4. **确认指标适用性。** 负 PE、亏损公司、金融地产、强周期、高成长、港美股等不能机械套用同一指标。
5. **构建股票池。** 记录来源、快照日期、指数/行业/概念/用户指定列表。
6. **执行强制排除。** 用户明确排除、无法交易、非目标证券类型、关键数据不可用等。
7. **执行必要条件过滤。** 对 PE、PB、ROE、股息率、成长、资金、流动性、订单等条件逐项过滤。
8. **基础体检和风险标记。** 对候选补充财务质量、估值位置、最新价、日涨跌、5 日涨跌、20 日涨跌、年初至今、交易状态、资金状态、风险事件和数据缺口。
9. **业务和研报验证。** 按 `references/company-analysis-dimensions.md` 对重点候选解释主营业务、行业位置、相关业务发展、业绩牵引、基本面、估值交易、资金/股价表现、同行对比、公告和研报增量；业务证据不足时降低结论强度。
10. **分组而非黑盒排序。** 按核心候选、稳健候选、弹性候选、观察名单、排除或风险标记分组。
11. **处理缺失数据。** 按 `references/data-freshness-and-conflicts.md` 回填；仍缺失时说明原因，不用裸 `--` 支撑强结论。
12. **选择可视化。** 根据数据完整性使用筛选漏斗、候选全景表、估值/成长/股息/5 日/20 日/年初至今涨跌幅/成交额/财务质量对比。

## 筛选和排序方法

不得把无关指标合成隐藏评分。多维度同时重要时，使用多列展示、条件命中矩阵或分组。用户未指定策略时，辅助体检不能变成新的硬筛选条件。

## 证据要求

候选表应包含数据日期或报告期。非标准字段应标注来源。预测、研报观点和模型推断必须与公司事实分开。

## 输出模块

按需使用直接筛选模板、候选事实表、证据表、重点公司卡片和可视化规则。正式报告输出前必须按 `references/report-quality-gate.md` 自检；缺少重点公司深度、交易/资金状态、券商观点、有效来源或可视化时，只在 `references/retrieval-budget-and-stop-rules.md` 的预算内补足；达到预算后降级说明并交付。默认至少包含：

- 筛选条件和适用边界；
- 范围背景、指标分布或股票池当前状态；
- 股票池来源和过滤过程；
- 候选全景表；
- 行情与估值对比表，使用 `templates/market-valuation-table.md`，保留收盘价/最新价、总市值、PE、日涨跌、5 日、20 日、年初至今、成交额和换手率列；
- 分组结论；
- 重点候选解析，使用 `templates/key-company-card.md` 的多维结构；
- 交易状态和资金/机构关注字段；行情窗口优先集中展示在行情与估值对比表中；
- 券商研报、权威媒体或明确的研报覆盖不足说明；
- 可视化或准可视化：筛选漏斗/条件矩阵 + 候选全景表 + 至少一个指标对比组件；
- 风险和信息缺口；
- 数据来源，写明来源名称、类型、日期/报告期和用途；
- 风险提示与免责声明。

用户有明确篇幅或形式约束时按约束调整。

## 应省略内容

除非影响筛选条件，否则不添加行业发现或主题研究。

## 常见错误

- 把负 PE 当成低估值。
- 用分析师覆盖数量代表公司质量。
- 在策略允许风险标的时仍然自动排除。
- 条件筛选只给股票列表，不解释过滤过程和数据缺口。
- 用户给定固定股票池时擅自扩展候选。
- 把辅助体检维度变成未声明的硬筛选条件。

## 降级策略

`seed_finance_search` 不可用时，说明金融结构化检索工具未返回完整结果；可用 `general_search` 检索财报、公告和权威金融网站，但不得猜测缺失的行情、估值或财务指标。

若 `general_search` 或研报检索不足，业务进展、订单、未来业绩和催化剂判断应降低强度。若关键指标缺失导致无法执行必要条件，应输出受限候选或可复现筛选计划。
