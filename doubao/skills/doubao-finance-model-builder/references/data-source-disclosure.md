# 数据来源披露与假设证据链

## 适用范围

三表、DCF、LBO和可比公司正式任务在标准化输入、预测和估值前，建立`data-source-ledger.json`和`assumption-evidence-matrix.json`。来源列表非空、报告末尾集中列链接或笼统写“年报/数据库”均不能替代逐字段披露。

本规范用于统一披露，不新增评分器，也不改变`references/model-and-artifact-controls.md`定义的阻断条件。

## 数据来源台账

`data-source-ledger.json`至少包含`meta`、`sources`和`field_mappings`。

每个`sources`记录至少包含：

`source_id | source_type | title | publisher | url | local_evidence_path | publication_date | reporting_period | accessed_at`

每个关键`field_mappings`记录至少包含：

`field_id | field_name | adopted_value | source_ids | report_period | source_locator | unit | currency | statistical_basis | value_type | adjustment | conflict_resolution`

- `url`指向原始文件、公告页面或可复核数据库页面，不以搜索结果摘要代替。
- `local_evidence_path`使用任务目录内相对路径，便于交付后复核。
- `source_locator`写明页码、表名、附注号、行项目或数据库字段。
- `value_type`使用`reported`、`external_estimate`、`analyst_adjustment`、`assumption`或`derived`。
- 调整值同时保留原始值、调整方法和理由；冲突数据保留候选值和最终选择理由。
- 股本、价格、汇率、现金、债务、租赁和少数股东权益分别记录基准日期；日期不一致时披露桥接方法。

## 假设证据矩阵

每个重大假设至少包含：

`assumption_id | assumption_type | model_field | scenario | forecast_period | adopted_value | unit | currency | historical_values | historical_periods | historical_source_ids | historical_trend | business_driver | forecast_logic | external_evidence_ids | forecast_vs_history_explanation | invalidation_conditions`

收入增长、销量、价格、产品结构、利润率、税率、资本开支、折旧摊销、营运资本、LBO经营改善与退出、可比公司调整和溢折价按实际任务覆盖。

DCF分别记录`risk_free_rate`、`beta`、`equity_risk_premium`、`cost_of_debt`、`tax_rate`、`capital_structure`和`terminal_growth`。不得用一条“WACC假设”代替组成项依据。

预测值偏离历史区间、管理层指引或行业趋势时，在`forecast_vs_history_explanation`中解释变化来自周期、产能、价格、产品组合、效率、会计口径或其他可观察驱动。

## Excel披露

正式工作簿包含“数据来源”“历史数据与口径”“假设依据”和“模型检查”。关键输入单元格关联`source_id`或`assumption_id`。

“数据来源”展示来源编号、标题、发布机构、报告期、公开日、链接、本地证据和使用字段；“历史数据与口径”展示原始值、调整值、单位、币种、统计口径和调整说明；“假设依据”至少展示模型输入、历史区间、历史趋势、预测值、业务逻辑、来源编号和失效条件。

<!-- END OF FILE: data-source-disclosure.md -->
