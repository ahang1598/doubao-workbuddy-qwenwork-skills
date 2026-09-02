# 风险规则框架

## RC-01: 十部分遗漏

| 属性 | 值 |
|------|-----|
| rule_id | RC-01 |
| trigger_condition | 遗漏十部分中任一部分 |
| severity | 阻断 |
| effect_on_output | 须补充缺失部分（至少标注"待补充"） |

## RC-02: 法条未核实

| 属性 | 值 |
|------|-----|
| rule_id | RC-02 |
| trigger_condition | 法条引用未联网核实 |
| severity | 阻断 |
| effect_on_output | 须联网核实法条编号和内容 |

## RC-03: 单一数据源未标注

| 属性 | 值 |
|------|-----|
| rule_id | RC-03 |
| trigger_condition | 仅依赖单一数据源且未标注【待核实】 |
| severity | 阻断 |
| effect_on_output | 须补充【待核实】+信息来源+时间戳 |

## RC-04: 尽调结果未转化提示

| 属性 | 值 |
|------|-----|
| rule_id | RC-04 |
| trigger_condition | 未提示尽调结果须转化为合同附件 |
| severity | 阻断 |
| effect_on_output | 须补充"尽调结果须转化为投资协议附件"提示 |

## RC-05: 红旗未升级

| 属性 | 值 |
|------|-----|
| rule_id | RC-05 |
| trigger_condition | [红旗]发现未调用专项技能深度分析 |
| severity | 警告 |
| effect_on_output | 须调用对应专项技能做深度法律分析 |
