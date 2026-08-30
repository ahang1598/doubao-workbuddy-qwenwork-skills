---
name_en: "cn-family-legal-consultation"
name: "婚姻家事法律咨询与综合分析"
displayName: "婚姻家事法律咨询与综合分析"
description: "整合事实、证据、现行法和类案，形成咨询摘要、律师分析、方案比较及可追溯起草指令。"
description_en: "Integrate facts, evidence, current law, and relevant cases into client advice, lawyer analysis, option comparison, and traceable drafting instructions."
argument-hint: "请提出婚姻家事问题，并提供已知事实、所在地、时间节点和已有材料。"
argument-hint-en: "Provide the family-law question, known facts, location, timeline, and available materials."
user-invocable: true
---

# 婚姻家事法律咨询与综合分析

读 [统一作业标准](../../references/operating-standard.md)、[法律权威核验](../../references/authority-baseline.md) 和 [结构化底稿](../../references/data-contracts.md)。信息不足时先调用 `cn-family-matter-intake`；正式法律依据由 `cn-family-statute-research` 核验，确需裁判样本时调用 `cn-family-case-research`。

## 统一问题树

1. 咨询问题、法律关系、主体资格和法域。
2. `verified_fact / party_statement / inference / disputed_fact / unknown` 分层。
3. 分析基准日、办理地和关键时间节点。
4. 每个争点对应：事实、证据、法律、正反观点、结论、置信度和验证动作。
5. 权属确定度、执行难度、第三人影响、登记要求、税费和时间风险。
6. 存在真实替代路径时形成最多三种方案，比较利益、风险、执行成本、前提和失败后果；已有明确答案时不机械凑 A/B/C。
7. 证据建议及必须升级给律师、税务师、评估师、心理/医疗或其他专业人员的事项。
8. `drafting_instruction`：可写事实、仅可写为当事人陈述的事项、禁止写入项、条件条款、留空项、履行动作和人工判断点。

## 三种视图

- 当事人摘要：问题、简明结论、主要依据、风险、选项和下一步。
- 律师备忘录：完整问题树、事实证据映射、法源、正反分析、风险矩阵、研究缺口和置信度。
- 起草指令包：经批准事实、条款目标、选择的条款变体、禁止写入项、条件和履行动作。

根据用户身份和目标输出最轻量的必要视图，不默认堆叠三份长文。用户只问一个明确问题时直接回答该问题，不先强制调用访谈或类案检索；已知信息不得重复询问。

## 禁止事项

不得保证协议必然有效或法院必然采纳；不得引用未经当前任务核验的具体法条、案号或地方口径；不得把对方陈述写成已查明事实；证据冲突未关闭时不得输出无条件起草结论；对登记、过户、税费、贷款变更和第三人效力必须使用条件化表述。
