# 上下游技能依赖

## 上游技能

| 技能 | 依赖程度 | 说明 |
|------|----------|------|
| 07-公司股权尽职调查 | 推荐 | 工商登记数据+历轮融资历史可复用 |
| 02-股东确权与代持纠纷处理 | 可选 | 代持关系识别可参考其代持验证方法论 |

## 下游技能

| 技能 | 依赖程度 | 说明 |
|------|----------|------|
| cap-market-multi-round-consistency | 推荐 | Cap Table→多轮条款一致性比对 |
| 05-投融资退出方案与争议解决 | 推荐 | 股权结构→退出路径选择+清算瀑布分析 |
| cap-market-special-rights-design | 可选 | Cap Table→特殊权利条款设计（如反稀释/优先清算） |

## 对比技能

| 技能 | 区分点 |
|------|--------|
| cap-market-multi-round-consistency | 股权计算 vs 条款一致性 |
| cap-market-founder-liability-review | 股权结构核验 vs 创始人个人责任评估 |
| cap-market-adversarial-clause-analysis | 股权计算 vs 条款对抗性分析 |

## 双向联动说明

- **→ adversarial（对抗性审查）**：本技能在输出清算瀑布/反稀释调整/对赌减资测算时，若条款本身存在对抗性风险（如 participating 无上限、完全棘轮、对赌触发），应提示用户"如需条款对抗性风险审查→ `cap-market-adversarial-clause-analysis`"。
- **← adversarial（量化前置）**：`cap-market-adversarial-clause-analysis` 识别 T8-T12 经济条款后，建议调用本技能做完整量化模拟。分工为：对抗性识别（adversarial）→ 量化建模（本技能）。
- **→ founder-liability（对赌责任）**：对赌(VAM)触发减资/回购的 Cap Table 量化由本技能完成，但回购义务主体（创始人个人责任）与减资程序合规由 `cap-market-founder-liability-review` 与律师判断。

## 弱引用声明

本技能为独立计算工具，不强制依赖上游技能输出。用户可直接提供历轮SPA+工商登记信息。与其他资本市场技能的关系为推荐协作而非硬依赖。
