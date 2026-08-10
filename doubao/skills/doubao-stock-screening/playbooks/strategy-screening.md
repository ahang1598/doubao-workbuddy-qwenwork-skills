# 策略风格筛选

## 适用场景

用户要求按价值、成长、质量、高股息、质量成长、困境反转、动量、事件驱动或特殊情形进行筛选。

## 必读资源

- `references/delivery-workflow.md`
- `references/formal-report-execution-contract.md`
- `references/report-quality-gate.md`
- `references/scope-context-rules.md`
- `references/company-analysis-dimensions.md`
- `references/strategy-factor-library.md`
- `references/metric-definitions.md`
- `references/screening-and-ranking-rules.md`
- `references/risk-handling.md`
- `references/data-freshness-and-conflicts.md`
- `references/evidence-sources.md`
- `references/broker-research-usage.md`
- `references/visualization-rules.md`
- `templates/stock-screening-report.md`
- `templates/strategy-screening.md`
- `templates/market-valuation-table.md`

## 输入识别

提取策略、市场、股票池、行业/主题/产业链限定、必要期限、阈值、排序字段、风险约束和输出形式。

若用户使用口语化策略名称，先映射到 `references/strategy-factor-library.md` 中的策略类型。例如“便宜蓝筹”映射低估值/低估蓝筹，“红利防守”映射高股息/防御，“强势股”映射趋势/动量，“跌多了反弹”映射超跌反弹。

## 股票池构建

使用用户指定的市场或股票池。若用户未指定，选择适当的宽基市场、指数股票池或行业/主题股票池，并说明假设。股票池和标准金融指标优先使用金融结构化数据检索，当前工具为 `seed_finance_search`。

复合策略先收敛范围，再执行策略条件：

1. 市场/证券类型；
2. 行业、主题、产业链、指数或用户指定名单；
3. 必要策略条件；
4. 辅助确认指标；
5. 风险排除和降权。

## 检索计划

按策略检索指标：

- 成长：营收、利润、分部增长和现金质量；
- 价值：估值和盈利质量；
- 高股息：股息率、派息率、自由现金流和稳定性；
- 困境反转：亏损趋势、资产负债表、催化剂和风险标记；
- 动量：最近交易日涨幅、5 日涨幅、20 日涨幅、年初至今涨幅、换手率和相对强弱。

财务、估值、股息、行情、风险标记和交易活跃度优先使用 `seed_finance_search`。困境反转催化剂、事件驱动背景、公司公告解读和非结构化经营变化使用通用公开信息检索，当前工具为 `general_search`。

正式策略筛选中，默认按 `references/broker-research-usage.md` 尝试检索券商研报；用户要求“深度”“未来业绩”“板块轮动”“行业龙头”“策略报告”或策略依赖行业假设时必须展开。重点抽取行业景气、盈利预测、估值假设、催化剂和风险。只有用户明确要求极简名单、不要研报，或检索工具不可用时，才可降级并说明原因。

## 分析步骤

1. **执行正式报告合同。** 若不是极简任务，先按 `references/formal-report-execution-contract.md` 准备策略背景包、股票池和证据包、财务/估值/交易/资金体检包、券商研报和权威观点包。
2. 用透明规则定义策略，区分必要条件和辅助确认。
3. 按 `references/scope-context-rules.md` 分析策略或指标当前状态，例如市场/行业分位、指标分布、估值环境、资金和交易状态、策略失效条件，并用筛选漏斗、指标分布或条件命中矩阵展示。
4. 用户未给阈值时优先使用行业分位、市场分位或同组比较；必要时使用可解释的绝对阈值并说明。
5. 执行股票池限定、条件过滤和风险处理。
6. 对关键缺失字段按 `references/data-freshness-and-conflicts.md` 回填，不用裸 `--` 支撑强结论。
7. 只用策略相关指标排序或分组。
8. 多维度重要时输出条件命中矩阵，不合成综合分。
9. 按 `references/company-analysis-dimensions.md` 对核心候选补充业务介绍、策略指标可持续性、后续发展、业绩牵引、财务质量、估值位置、资金/最新价/日涨跌/5 日/20 日/年初至今股价表现、同行对比、策略催化和反向证据。

## 筛选和排序方法

不得用与策略无关的指标排名。不得把成长、价值、股息、资金和动量合成为隐藏总分。

推荐表达：

- 必要条件命中；
- 辅助确认较强；
- 策略逻辑成立但估值/风险需要观察；
- 仅部分命中；
- 风险标记或排除。

## 证据要求

说明报告期、数据日期和指标定义。预测指标必须标注预测来源。资金面、技术面和行情指标必须标注统计窗口。研报观点必须标注底层券商、报告日期和预测/假设性质。

## 输出模块

使用策略筛选模板、候选事实表和条件命中矩阵。需要时使用估值/成长散点图、股息率/现金流对比、5 日/20 日/年初至今涨跌幅/成交额/资金对比或板块轮动时间线。正式报告输出前必须按 `references/report-quality-gate.md` 自检；缺少策略背景、交易/资金状态、候选深度、来源追踪、研报观点或可视化时，只在 `references/retrieval-budget-and-stop-rules.md` 的预算内补足；达到预算后降级说明并交付。

默认至少包含：策略定义与适用边界、策略/指标当前状态和分布、股票池与过滤过程、候选全景、行情与估值对比表、分组结论、重点候选解析、资金/机构关注字段、券商研报或明确覆盖不足说明、可视化或准可视化、风险与信息缺口、可追溯数据来源、风险提示与免责声明。行情与估值对比表使用 `templates/market-valuation-table.md`，保留收盘价/最新价、总市值、PE、日涨跌、5 日、20 日、年初至今、成交额和换手率列。

## 应省略内容

策略本身不包含主题时，不添加主题分析。用户没有要求短线交易时，不默认加入技术指标和资金流。

## 常见错误

- 把负 PE 当作低估值；
- 困境反转策略中自动排除 ST；
- 用分析师覆盖数量代表质量。
- 用综合评分替代条件命中说明；
- 把单日资金流或短期涨幅写成基本面改善；
- 把券商预测写成确定性业绩。

## 降级策略

`seed_finance_search` 无结果时，不猜测财务、估值或行情指标；关键指标缺失时，将缺失字段单独列出，或提供可复现筛选计划。

`general_search` 或研报检索不足时，事件驱动、困境反转、板块轮动和未来业绩相关判断必须降低强度，并说明催化剂或盈利预测验证不足。
