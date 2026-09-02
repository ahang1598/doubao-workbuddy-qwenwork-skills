# 风险规则框架

## RC-01: 责任条款遗漏

| 属性 | 值 |
|------|-----|
| rule_id | RC-01 |
| trigger_condition | 遗漏涉及个人责任的条款 |
| severity | 阻断 |
| effect_on_output | 须逐文件逐条款扫描，不可遗漏 |

## RC-02: 责任类型误分类

| 属性 | 值 |
|------|-----|
| rule_id | RC-02 |
| trigger_condition | 将个人责任误分类（如将公司义务误为个人） |
| severity | 阻断 |
| effect_on_output | 须按8类准确分类，区分个人义务与公司义务 |

## RC-03: 风险维度遗漏

| 属性 | 值 |
|------|-----|
| rule_id | RC-03 |
| trigger_condition | 五维评估中遗漏维度 |
| severity | 阻断 |
| effect_on_output | 须D1-D5全评估 |

## RC-04: 条款联动未分析

| 属性 | 值 |
|------|-----|
| rule_id | RC-04 |
| trigger_condition | 未分析条款间交叉引用和联动触发 |
| severity | 阻断 |
| effect_on_output | 须识别交叉引用并分析联动关系 |

## RC-05: 谈判建议不可操作

| 属性 | 值 |
|------|-----|
| rule_id | RC-05 |
| trigger_condition | 谈判建议过于笼统（如仅说"建议修改"） |
| severity | 警告 |
| effect_on_output | 须给出具体可操作建议（如"建议将回购上限设为投资额150%"） |

## RC-06: 总敞口未测算

| 属性 | 值 |
|------|-----|
| rule_id | RC-06 |
| trigger_condition | 仅列单条责任未汇总个人总敞口 |
| severity | 阻断 |
| effect_on_output | 须按 methodology §五 汇总最不利假设总敞口 + 资产覆盖比 |

## RC-07: 可保险性误判

| 属性 | 值 |
|------|-----|
| rule_id | RC-07 |
| trigger_condition | 将 D&O 险可覆盖的赔偿类责任误判为完全不可投保，或未区分可保/不可保核心敞口 |
| severity | 警告 |
| effect_on_output | 须区分 D&O 险可覆盖部分（陈述保证赔偿）与不可投保核心（现金回购/连带现金） |

## RC-08: 市场基准缺失

| 属性 | 值 |
|------|-----|
| rule_id | RC-08 |
| trigger_condition | 谈判建议未标注市场惯例基准（标准 vs 过度主张） |
| severity | 警告 |
| effect_on_output | 须标注市场标准与过度主张信号，供卖方律师制定谈判策略 |
