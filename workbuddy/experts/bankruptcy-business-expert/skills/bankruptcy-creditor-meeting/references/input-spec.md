# 债权人会议支持 — 输入规格

## 必填参数

| 参数 | 类型 | 说明 |
|------|------|------|
| meeting_type | string | 会议类型："first"(第一次)/"interim"(临时)/"reorg_vote"(重整表决)/"settlement_vote"(和解表决) |
| case_info | object | 案件信息：debtor_name/case_number/court_name/procedure_type/acceptance_date |
| agenda_items | string[] | 议题清单 |
| claim_summary | object | 债权概况：total_creditors/total_amount/by_priority{}。数据来源：claim-review产出的claim_review_summary.json的summary.*和claims[] |

## 可选参数

| 参数 | 类型 | 说明 |
|------|------|------|
| voting_items | string[] | 需表决事项清单 |
| meeting_format | string | 会议形式："in_person"/"written"/"online"，默认"in_person" |
| meeting_date | string(ISO 8601) | 会议日期 |
| meeting_location | string | 会议地点 |
| need_committee | boolean | 是否需要设立债权人委员会，默认false |
| creditor_detail | object[] | 逐户债权人明细，用于表决可行性测算。每项含：name(名称)/amount(债权额)/claim_type(债权性质:secured/labor/tax/ordinary)/secured_amount(担保物覆盖额)/current_stance(当前倾向:support/oppose/abstain/unknown)/difficulty(争取难度:high/medium/low)。缺失时从claim_summary推导，但推导结果精度较低，建议提供 |
| voting_scenario | string | 表决场景："general"(一般事项)/"reorg"(重整计划)/"settlement"(和解协议)。决定门槛标准选择。默认"general" |
