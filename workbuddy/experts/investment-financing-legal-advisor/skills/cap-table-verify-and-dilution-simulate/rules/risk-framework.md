# 风险规则框架

## RC-01: 历轮数据缺失

| 属性 | 值 |
|------|-----|
| rule_id | RC-01 |
| trigger_condition | 某轮或全部轮次协议未提供 |
| severity | 阻断 |
| effect_on_output | 须补充缺失轮次数据；缺失轮次后的Cap Table不输出 |

## RC-02: 计算错误

| 属性 | 值 |
|------|-----|
| rule_id | RC-02 |
| trigger_condition | 持股比例合计≠100%或股数不守恒 |
| severity | 阻断 |
| effect_on_output | 须重新计算至比例合计=100% |

## RC-03: 工商差异未分析

| 属性 | 值 |
|------|-----|
| rule_id | RC-03 |
| trigger_condition | 工商差异存在但未分析原因 |
| severity | 阻断 |
| effect_on_output | 须逐项标注差异原因（登记延迟/代持/期权池/口径不同/计算错误/未登记转让） |

## RC-04: 稀释计算错误

| 属性 | 值 |
|------|-----|
| rule_id | RC-04 |
| trigger_condition | 稀释后比例合计≠100%或Top-up处理顺序错误 |
| severity | 阻断 |
| effect_on_output | 须重新计算；含Top-up时先计算池扩大再计算新发稀释 |

## RC-05: 反稀释方式未标注

| 属性 | 值 |
|------|-----|
| rule_id | RC-05 |
| trigger_condition | 反稀释调整未标注方式或调整价 |
| severity | 警告 |
| effect_on_output | 须标注加权平均/完全棘轮及调整价 |

## RC-06: 期权池处理错误

| 属性 | 值 |
|------|-----|
| rule_id | RC-06 |
| trigger_condition | 期权池未单列或混入普通股计算 |
| severity | 阻断 |
| effect_on_output | 须拆分授予/未授予，单列期权池行 |

## RC-07: 穿透判断缺失

| 属性 | 值 |
|------|-----|
| rule_id | RC-07 |
| trigger_condition | 有限合伙持股平台未判断穿透或未标注理由 |
| severity | 阻断 |
| effect_on_output | 须判断是否穿透并标注理由（GP持股比例/份额分配表/平台类型） |

## RC-08: 代持无依据还原

| 属性 | 值 |
|------|-----|
| rule_id | RC-08 |
| trigger_condition | 无书面代持协议但擅自还原代持 |
| severity | 阻断 |
| effect_on_output | 须基于书面代持协议还原；无协议则标注"代持待核实" |

## RC-09: 反稀释总股数变化

| 属性 | 值 |
|------|-----|
| rule_id | RC-09 |
| trigger_condition | 反稀释调整后总股数变化（增发新股） |
| severity | 阻断 |
| effect_on_output | 反稀释仅调整持股分配，不增发新股，须修正计算 |

## RC-10: 清算优先权结构误分类

| 属性 | 值 |
|------|-----|
| rule_id | RC-10 |
| trigger_condition | 未区分 non-participating/participating/capped participating，或 non-participating 未取高 |
| severity | 阻断 |
| effect_on_output | 须按 SPA 标注结构；non-participating 实现 max(优先清算额, 普通股路径金额) |

## RC-11: 优先清算金额公式错误

| 属性 | 值 |
|------|-----|
| rule_id | RC-11 |
| trigger_condition | 优先清算金额写成"投资额 × (1 + 倍数)"（1× 被误算为 2×） |
| severity | 阻断 |
| effect_on_output | 修正为"优先清算金额 = 投资额 × 倍数"（1× 即等于投资额） |

## RC-12: 对赌减资未提示

| 属性 | 值 |
|------|-----|
| rule_id | RC-12 |
| trigger_condition | 含对赌(VAM)现金回购但未提示减资程序（新公司法第224/162条） |
| severity | 警告 |
| effect_on_output | 标注"须减资程序，由律师确认"，不替代该法律判断 |
