# 风险规则框架

## RC-01: 未解析直接审查

| 属性 | 值 |
|------|-----|
| rule_id | RC-01 |
| trigger_condition | 未先解析协议直接审查 |
| severity | 阻断 |
| effect_on_output | 须先解析协议→结构化JSON |

## RC-02: 规则组遗漏

| 属性 | 值 |
|------|-----|
| rule_id | RC-02 |
| trigger_condition | 仅使用部分规则组（遗漏VA/GOV/EX/FP/IR/MR中任一） |
| severity | 阻断 |
| effect_on_output | 须确保六组规则集全部审查 |

## RC-03: 检索模糊回复

| 属性 | 值 |
|------|-----|
| rule_id | RC-03 |
| trigger_condition | 检索结果为模糊回复（非三态） |
| severity | 阻断 |
| effect_on_output | 须明确有/明确无/需人工确认 |

## RC-04: 改写未标人审

| 属性 | 值 |
|------|-----|
| rule_id | RC-04 |
| trigger_condition | 改写输出未标注人审关卡 |
| severity | 阻断 |
| effect_on_output | 须补充"须经持证律师审核后方可使用" |

## RC-05: 处置方案不足

| 属性 | 值 |
|------|-----|
| rule_id | RC-05 |
| trigger_condition | 处置方案仅1套路径 |
| severity | 阻断 |
| effect_on_output | 须补充至≥2套路径 |

## RC-06: 规则未覆盖未标注

| 属性 | 值 |
|------|-----|
| rule_id | RC-06 |
| trigger_condition | 规则未覆盖的条款未标注"建议人工审查" |
| severity | 警告 |
| effect_on_output | 须标注"建议人工审查" |

## RC-07: 核心条款缺市场基准

| 属性 | 值 |
|------|-----|
| rule_id | RC-07 |
| trigger_condition | 核心级条款（对赌/回购/清算优先/反稀释/一票否决）审查结论未附市场常见区间 |
| severity | 警告 |
| effect_on_output | 补充2026年市场基准+时效性标注，使客户判断偏离度 |

## RC-08: 未做重要性分级

| 属性 | 值 |
|------|-----|
| rule_id | RC-08 |
| trigger_condition | 审查结果未按核心/重要/一般标注交易重要性 |
| severity | 警告 |
| effect_on_output | 须按交易重要性分级并排序呈现 |

## RC-09: 核心经济条款未提示量化

| 属性 | 值 |
|------|-----|
| rule_id | RC-09 |
| trigger_condition | 核心级"不符"涉及对赌金额/清算倍数/反稀释/回购利率等经济条款，未提示可量化经济影响 |
| severity | 警告 |
| effect_on_output | 须提示该条款的经济敞口可经 cap-table-verify（股权/稀释模拟）或 founder-liability（创始人责任敞口）量化 |
