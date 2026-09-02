# 破产分配计算 — 输入规格

## 必填参数

| 参数 | 类型 | 说明 |
|------|------|------|
| claim_review_summary | string(路径) | 债权审查结构化摘要JSON文件路径 |
| distributable_assets | object | 可供分配财产：total_amount(总额)/breakdown(明细列表：source/amount) |

## 可选参数

| 参数 | 类型 | 说明 |
|------|------|------|
| secured_claims_detail | object[] | 担保债权明细：claim_id/property_id/property_estimated_value/claim_amount |
| interim_distribution | object | 中间分配记录：date/amount/by_priority{} |
| distribution_mode | string | 分配方式："single"(一次)/"multiple"(多次)，默认"single" |
| rounding_rule | string | 尾差处理："last_item"(归入最后一笔)/"reserve"(归管理人指定账户)，默认"last_item" |
