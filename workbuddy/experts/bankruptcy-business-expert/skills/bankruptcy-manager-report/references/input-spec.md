# 管理人报告编制 — 输入规格

## 必填参数

| 参数 | 类型 | 说明 |
|------|------|------|
| report_type | string | 报告类型："takeover"/"asset_status"/"distribution_plan"/"duty" |
| case_info | object | 案件信息：debtor_name/case_number/court_name/procedure_type/acceptance_date |
| data_sources | object | 数据来源路径：claim_review_summary/asset_tracing_summary/distribution_calc_data/legal_research_summary |

## 可选参数

| 参数 | 类型 | 说明 |
|------|------|------|
| report_style | string | 报告样式："standard"/"detailed"/"brief"，默认"standard" |
| court_requirements | string | 受理法院特殊格式要求描述 |
| report_period | object | 报告期间：start_date/end_date（履职报告适用） |
