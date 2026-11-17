---
name: review-synthesis
display_name: "综述草稿与证据综合"
display_name_en: "Literature Review Synthesis"
description: "Draft thematic literature reviews with traceable claims, disagreements, methodological limitations, and scoped research gaps."
description_zh: "按主题综合文献，形成有论断出处、分歧解释、方法局限和明确范围的综述草稿。"
description_en: "Synthesize literature into thematic reviews with traceable claims, disagreements, limitations, and scoped gaps."
category: "research"
version: 1.0.0
author: "WorkBuddy Expert Publisher"
---

# 综述草稿与证据综合

## 触发与输入

需要形成主题综述、研究现状、争议与缺口或修订综述时使用。输入范围与筛选后的证据矩阵。仅有题录不写具体结果性综述，可输出结构与待提取问题。默认叙述性综述草稿，只有完成相应流程才使用更强的综述名称。

## 工作流程

1. 阅读 references/synthesis-guide.md，区分文献事实、综合判断与拟研究建议。按主题/机制/方法争议组织，不逐篇摘要堆砌。
2. 将主要论断编号C1等。经验论断关联纳入记录的P编号和具体位置，注明支持/反对/限定关系；背景提议也要标出属于研究者建议。
3. 对同一主题比较一致点、差异、研究条件和偏倚。保留阴性、不一致和不确定结果，不按显著性或论文数量投票。
4. 综述段落结构为主题句、具体证据、差异解释与局限、小结及下一步问题。措辞强度匹配访问层级和设计。只读摘要时直接声明不能复核完整方法。
5. 研究缺口表述为“在本次纳入材料及范围内尚未获得足够证据”，不能声称全领域无人研究，除非有足够检索依据。区分证据缺口和单篇局限，不自动把局限变为有价值课题。
6. 保留引用编号与完整可用题录，核对作者、年份和DOI。未核实题录明确标记；不添加看似可信的参考文献。

## 输出

综述草稿、论断证据清单、分歧与局限、研究缺口及参考文献。完整数据写claims[]及review_sections[]，每节有text和claim_ids。只提取摘要的局限要在正文可见，不能只写在附件末尾。

## 验收与边界

每个经验论断可追溯；没有来源的设想标为proposal。支持和反对证据不能合并成一致结论。相关与因果、未显著与无效果、未发现与不存在必须区分。要求编造参考文献或只保留支持结论的论文时，坚持真实证据，提供诚实改写。
