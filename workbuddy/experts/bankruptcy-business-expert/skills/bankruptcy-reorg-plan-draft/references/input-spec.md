# 重整计划草案编制 — 输入规格

## 必填参数

| 参数 | 类型 | 说明 |
|------|------|------|
| debtor_info | object | 债务人信息：name/industry/main_business/total_assets/total_liabilities |
| claim_summary | object | 债权审查结论摘要：by_priority{employee/social_tax/secured/ordinary}各含total和count |
| available_resources | object | 可供偿债资源：asset_valuation/investor_commitment/operating_revenue_forecast |
| business_plan_direction | string | 经营方案方向描述（如"引入战略投资人续建在售楼盘"） |

## 可选参数

| 参数 | 类型 | 说明 |
|------|------|------|
| investor_info | object | 战略投资人：name/commitment_amount/investment_terms |
| procedure_type | string | "reorganization"(重整)/"settlement"(和解)，默认"reorganization" |
| shareholder_equity | object | 出资人权益现状：shareholders[]{name/percentage} |
| employee_reset_plan | string | 职工安置方案描述（如有） |
