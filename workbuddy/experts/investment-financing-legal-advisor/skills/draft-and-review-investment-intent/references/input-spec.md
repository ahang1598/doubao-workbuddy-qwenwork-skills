# 输入规格

## 输入参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| task_type | enum | 是 | `draft_ts` / `review_ts` / `compliance_check` / `risk_assessment` |
| ts_text | text | 条件必填 | 待审查的TS全文（`review_ts`时必填） |
| target_industry | text | 条件必填 | 目标行业描述（`compliance_check`时必填） |
| investor_type | enum | 否 | `domestic`（境内）/ `foreign`（境外）/ `cross_border`（跨境） |
| investment_structure | text | 条件必填 | 交易结构描述（`risk_assessment`时必填） |
| jurisdiction | text | 否 | 管辖地/仲裁地 |
| company_info | object | 否 | 目标公司基本信息（名称/注册地/注册资本/股权结构） |
| investor_info | object | 否 | 投资方基本信息 |
| existing_agreements | text | 否 | 已有协议文本（如NDA等） |

## 输入模式

### Mode A: 起草TS（draft_ts）

用户提供投资交易基本信息，技能生成TS草案。

最少输入：`task_type=draft_ts` + 投资金额 + 投前估值 + 股权比例

### Mode B: 审查TS（review_ts）

用户提供TS全文，技能审查约束力条款+风险点。

最少输入：`task_type=review_ts` + `ts_text`

### Mode C: 合规检查（compliance_check）

用户提供目标行业+投资方类型，技能评估行业准入+外汇合规。

最少输入：`task_type=compliance_check` + `target_industry` + `investor_type`

### Mode D: 风险评估（risk_assessment）

用户提供交易结构描述，技能执行股债定性+名股实债防范分析。

最少输入：`task_type=risk_assessment` + `investment_structure`

## 追问策略

- 追问≤1次：信息不足时一次性列全部缺口
- 仅在以下情况追问：无任务表达 / 缺关键事实 / 产物互斥
- 追问格式：列出缺口清单 + 每项说明为何需要 + 建议提供方式
