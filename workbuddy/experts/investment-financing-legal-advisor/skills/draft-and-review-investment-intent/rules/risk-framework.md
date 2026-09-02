# 风险规则框架

## RC-01: 负面清单版本过期

| 属性 | 值 |
|------|-----|
| rule_id | RC-01 |
| trigger_condition | 引用外商投资负面清单时未标注版本 |
| severity | 阻断 |
| effect_on_output | 须更新为现行有效版本+标注生效日期后方可输出准入结论 |

## RC-02: VIE合法性绝对化

| 属性 | 值 |
|------|-----|
| rule_id | RC-02 |
| trigger_condition | 断言"VIE合法"或"VIE违法" |
| severity | 阻断 |
| effect_on_output | 须改为概率判断+风险等级+司法判例支撑 |

## RC-03: 回购义务人单一化

| 属性 | 值 |
|------|-----|
| rule_id | RC-03 |
| trigger_condition | 名股实债结构中仅设目标公司为回购义务人 |
| severity | 阻断 |
| effect_on_output | 须建议创始股东回购+目标公司连带担保；标注新公司法第224条第3款定向减资须经全体股东另有约定或章程另有规定，默认须等比减资 |

## RC-04: 跨境手续遗漏

| 属性 | 值 |
|------|-----|
| rule_id | RC-04 |
| trigger_condition | 跨境外汇手续遗漏商务/发改/外汇任一环节 |
| severity | 阻断 |
| effect_on_output | 须补充完整路径图（三部门各管一段，不可互为前提） |

## RC-05: 股债定性单一维度

| 属性 | 值 |
|------|-----|
| rule_id | RC-05 |
| trigger_condition | 股债定性仅依赖单一维度判断 |
| severity | 阻断 |
| effect_on_output | 须执行完整四维分析（缔约过程/转让价格/收益安排/担保机制）+标注每个维度权重 |

## RC-06: 外观主义未区分内外

| 属性 | 值 |
|------|-----|
| rule_id | RC-06 |
| trigger_condition | 股债定性未区分内部关系与外部关系 |
| severity | 警告 |
| effect_on_output | 须补充：内部实质重于形式，外部外观主义优先 |
