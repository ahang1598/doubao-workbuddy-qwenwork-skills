# 破产资产调查与追收 — 输入规格

## 必填参数

| 参数 | 类型 | 说明 |
|------|------|------|
| takeover_materials | string[] | 接管材料路径（账册/流水/合同/权属证明/报表） |
| acceptance_date | string(ISO 8601) | 破产申请受理日期，用于确定撤销权时间窗口 |
| debtor_info | object | 债务人信息：name(全称)/industry(行业)/registered_capital(注册资本)/legal_representative(法定代表人) |

## 可选参数

| 参数 | 类型 | 说明 |
|------|------|------|
| known_clues | string[] | 已知财产线索描述 |
| related_parties | object[] | 已知关联方：name/relationship_type(股权控制/亲属/任职)/details |
| sensitive_period_1y | boolean | 是否重点审查受理前1年内交易（第31条），默认true |
| sensitive_period_6m | boolean | 是否重点审查受理前6个月内交易（第32条），默认true |
