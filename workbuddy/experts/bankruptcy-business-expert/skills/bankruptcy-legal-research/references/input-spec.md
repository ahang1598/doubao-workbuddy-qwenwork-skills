# 破产法律研究 — 输入规格

## 必填参数

| 参数 | 类型 | 说明 |
|------|------|------|
| research_question | string | 法律研究问题或争议焦点描述 |
| case_facts | object | 已确认案件事实：key_facts(关键事实列表)/acceptance_date(受理日期)/procedure_type(程序类型) |

## 可选参数

| 参数 | 类型 | 说明 |
|------|------|------|
| research_depth | string | 研究深度："statutes"(法规)/"statutes_interpretations"(法规+司法解释)/"full"(法规+司法解释+类案)，默认"statutes_interpretations" |
| specific_provisions | string[] | 需重点分析的特定法条（如"第31条""第40条"） |
| supporting_skill | string | 请求支撑的技能名称（如"bankruptcy-claim-review"），用于定向输出 |
