# 行业发现

## 适用场景

用户没有指定行业，希望先判断哪些行业或方向值得进一步筛选股票。

行业发现只用于找到下一步股票筛选入口，不能替代个股筛选结论。

## 必读资源

- `references/delivery-workflow.md`
- `references/formal-report-execution-contract.md`
- `references/report-quality-gate.md`
- `references/scope-context-rules.md`
- `references/industry-theme-taxonomy.md`
- `references/research-depth-rules.md`
- `references/broker-research-usage.md`
- `references/strategy-factor-library.md`
- `references/metric-definitions.md`
- `references/risk-handling.md`
- `references/data-freshness-and-conflicts.md`
- `references/visualization-rules.md`
- `templates/industry-discovery.md`

## 输入识别

提取市场、证券类型、风格、期限、风险偏好、政策/主题约束、行业排除条件和输出形式。

## 股票池构建

先构建候选行业或方向，再根据透明比较条件选择进入个股筛选的行业。行业分类、风格板块和概念方向应按 `references/industry-theme-taxonomy.md` 说明口径。

## 检索计划

行业表现、估值、盈利预期变化、流动性/资金流和风险优先使用金融结构化数据检索，当前工具为 `seed_finance_search`。政策催化、产业资料、行业空间和公开研究材料使用通用公开信息检索，当前工具为 `general_search`。

## 分析步骤

1. 若不是极简任务，先按 `references/formal-report-execution-contract.md` 中的范围背景、券商研报、可视化和来源要求准备行业发现材料；行业发现不直接替代个股筛选。
2. 确认用户未指定行业。
3. 按 `references/scope-context-rules.md` 分析市场或风格背景：市场表现、流动性、估值分布、资金偏好、政策/事件和风险。
4. 明确比较期限：短期交易、季度景气、中长期产业趋势或防御配置。
5. 根据用户目标选择透明行业比较指标，例如景气、盈利预期、估值位置、资金/交易状态、政策或产业催化、风险。
6. 按证据比较行业，而不是按叙事热度。
7. 使用券商行业研报和权威资料补充行业空间、景气周期和风险假设。
8. 输出候选行业或方向，并说明依据和适用期限。
9. 给出每个候选行业下一步应使用的个股筛选指标和需要核查的公司证据。

## 筛选和排序方法

不固定必须选出 1 到 3 个行业。不把近期资金流或涨幅直接等同于长期机会。

## 证据要求

说明行业分类、日期、来源和适用期限。

## 输出模块

按需使用行业发现模板、行业比较表、可视化规则和后续个股筛选入口。若用户要求继续筛股票，再切换到 `playbooks/industry-screening.md`。正式行业发现输出前必须按 `references/report-quality-gate.md` 中与范围背景、可视化、研报观点和来源追踪相关的要求自检。

默认至少包含：市场/风格背景、比较口径、行业比较表、估值/资金/5 日/20 日/年初至今表现等可比指标、券商行业观点或覆盖不足说明、可视化或准可视化、入选行业拆解、后续个股筛选入口、风险与信息缺口、可追溯数据来源、风险提示与免责声明。

## 应省略内容

用户已指定行业时，跳过全市场行业发现。

## 常见错误

- 未说明指标就给行业优先级；
- 把短期主题热度当成长期行业吸引力。

## 降级策略

行业数据不完整时，输出受限观察名单和需要补充验证的数据。
