# 输入规格

## 输入参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| task_type | enum | 是 | `confirm_holder` / `assess_proxy` / `design_nomination` |
| company_info | object | 条件必填 | 标的公司基本信息（名称/注册地/股权结构/公司类型） |
| holder_evidence | text | 条件必填 | 持股证据描述（`confirm_holder`时必填） |
| proxy_agreement | text | 条件必填 | 代持协议文本或内容描述（`assess_proxy`时必填） |
| nominee_info | object | 条件必填 | 名义股东信息（姓名/身份/职业） |
| actual_investor_info | object | 否 | 实际出资人信息 |
| industry_type | text | 否 | 标的公司所属行业（影响代持效力判断） |
| other_shareholders_consent | text | 否 | 其他股东是否知晓/同意代持的描述 |
| funding_evidence | text | 否 | 出资凭证/银行流水/资金用途附言 |

## 输入模式

### Mode A: 确认股东资格（confirm_holder）

用户提供持股证据，技能执行三层递进验证。

最少输入：`task_type=confirm_holder` + `company_info` + `holder_evidence`

### Mode B: 代持风险分析（assess_proxy）

用户提供代持协议，技能执行效力三层判断+内外风险敞口评估。

最少输入：`task_type=assess_proxy` + `proxy_agreement` + `nominee_info`

### Mode C: 显名路径设计（design_nomination）

用户提供代持关系描述，技能设计显名方案。

最少输入：`task_type=design_nomination` + `company_info` + `actual_investor_info`

## 追问策略

- 追问≤1次：信息不足时一次性列全部缺口
- 仅在以下情况追问：无任务表达 / 缺关键事实 / 产物互斥
