# 上下游技能依赖

## 互补技能

| 技能 | 关系 | 说明 |
|------|------|------|
| 06-投资协议审查（investment-agreement-review） | 互补 | 本技能设计条款→06审查条款合规性 |

## 上游技能

| 技能 | 依赖程度 | 说明 |
|------|----------|------|
| 01-起草和审查投资意向书（draft-and-review-investment-intent） | 推荐 | TS条款→正式协议条款设计 |

## 下游技能

| 技能 | 依赖程度 | 说明 |
|------|----------|------|
| 06-投资协议审查（investment-agreement-review） | 必需 | 设计后→审查 |
| cap-market-adversarial-clause-analysis | 推荐 | 设计后→陷阱识别（对抗性审查） |
| cap-market-founder-liability-review | 推荐 | 设计的回购/赔偿/担保条款→创始人个人责任归集量化 |
| cap-market-cap-table-verify | 推荐 | 设计的清算优先权/反稀释/对赌条款→量化模拟 |
| cap-market-multi-round-consistency | 推荐 | 多轮设计→跨轮一致性比对（尤其R21 MFN回溯） |

## 对比技能

| 技能 | 区分点 |
|------|--------|
| 06-投资协议审查 | 从零设计 vs 已有条款审查 |
| cap-market-adversarial-clause-analysis | 条款生成 vs 陷阱识别（设计出的条款往往即对抗性审查对象） |

## 双向联动说明

- **→ adversarial（对抗识别）**：本技能生成的条款（如参与权无上限、完全棘轮、MFN无例外）往往是 adversarial T1-T12 的对抗性风险来源；设计后建议由其做对抗性专项审查。
- **→ founder-liability（责任归集）**：R3回购/R16赔偿/R18锁定/R21相关条款会转化为创始人个人责任，设计后由其归集量化总敞口。
- **→ cap-table-verify（量化模拟）**：R1清算/R2反稀释/R3对赌等经济条款的量化影响由其完整模拟。
- **→ multi-round（跨轮一致）**：多轮设计尤其须检查 R21 MFN 的回溯适用，由 multi-round 做一致性比对。

## 弱引用声明

本技能为独立设计工具，不强制依赖上游技能输出。与其他资本市场技能的关系为推荐协作而非硬依赖。
