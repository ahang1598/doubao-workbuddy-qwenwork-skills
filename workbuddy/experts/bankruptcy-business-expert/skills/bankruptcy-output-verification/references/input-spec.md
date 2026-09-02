# 破产成果校验 — 输入规格

## 必填参数

| 参数 | 类型 | 说明 |
|------|------|------|
| deliverables | object[] | 待校验成果：path(路径)/role(角色)/format(格式) |
| user_query | string | 用户原始请求 |
| structured_summaries | object | 各阶段结构化摘要：claim_review/asset_tracing/distribution_calc/legal_research 路径 |
| role_stance | string | 角色立场："manager"/"creditor_agent"/"debtor_advisor" |

## 可选参数

| 参数 | 类型 | 说明 |
|------|------|------|
| report_type | string | 被校验产物类型（注意：本枚举与manager-report.report_type命名空间不同。本处distribution=分配方案/分配执行报告，manager-report用distribution_plan；本处claim_review/reorg_plan是对应技能的产物，非manager-report的report_type）。枚举值："takeover"/"asset_status"/"claim_review"/"distribution"/"duty"/"reorg_plan" |
| onboarding_profile | object | 入职偏好（输出风格/风险偏好），用于V4立场一致性校验 |
