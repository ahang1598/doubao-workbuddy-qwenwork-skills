# 风险规则框架

## RC-01: 陷阱遗漏
- severity: 阻断
- effect: 须逐条款扫描（双轴十二类），不可遗漏

## RC-02: 误分类
- severity: 阻断
- effect: 须按 T1-T12 准确分类

## RC-03: 修改建议不可操作
- severity: 警告
- effect: 须给出具体修改方案（含替代方案）

## RC-04: 严重度未评估/未调节
- severity: 阻断
- effect: 须评估高/中/低并结合交易情境调节

## RC-05: 经济条款未量化
- severity: 警告
- effect: T8-T12 须给出量化影响摘要或联动 `cap-market-cap-table-verify` 建议

## RC-06: 违约金基准误用
- severity: 阻断
- effect: 须以《民法典》第585条"超过实际损失30%"为酌减参考，不得误用4倍LPR作为合同违约金硬性上限

## RC-07: 修改建议无市场基准
- severity: 警告
- effect: 须先判市场标准 vs 投资人过度主张，定必争/可谈/接受优先级
