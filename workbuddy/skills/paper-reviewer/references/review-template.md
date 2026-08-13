# Review Template — OpenReview 标准输出模板

供 paper-reviewer skill 在 Step 5 加载使用。输出语言跟随论文语言：英文论文用英文模板，中文论文用中文模板。section 结构两者完全一致。

---

## 模板结构（中英对照）

```markdown
# Paper Review: <论文标题>

## Summary / 论文总结
<3-5 句话，用自己的话复述：论文解决什么问题、提出什么方法、得到什么结果。
向作者和 AC 证明审稿人读懂了论文。不复述摘要原文，不评价，只陈述。>

## Strengths / 优点
<按重要性排序，每条：先给结论句，再给论文证据（章节/页码/图表/数字），
最后说明该优点为什么对领域有价值。通常 3-5 条。>

1. **<结论句>**. <证据与阐述，如 "In Section 3.2, the proposed ... ; Table 2 shows ... on X benchmark, which outperforms the strongest baseline by Y%. This is valuable because ...">
2. ...

## Weaknesses / 缺点
<按严重性排序，major 在前。每条：问题是什么 → 论文中的具体位置/证据 →
为什么这是问题 → （尽量）可操作的修复建议或验证实验建议。
只写有证据支撑的问题，不写"我感觉"。>

1. **<问题概述>**. <详细阐述。例如 "The central claim of X% improvement (Abstract, L12) is only supported by a single dataset (Table 2), and the strongest baseline [ref] was run without hyperparameter tuning (Section 4.1). To substantiate the claim, the authors should ...">
2. ...

### Minor Comments / 次要问题
<笔误、排版、图表可读性、缺非关键引用等，逐条列出页码/位置。不影响分数。>

## Questions to Authors / 向作者提问
<列出需要作者澄清或补充的问题。好问题的标准：答案会实质改变评审判断。
可为 rebuttal 阶段的关键。>

1. <问题 1，注明相关章节>
2. ...

## Limitations / 局限性确认
<作者是否如实讨论了工作的局限？审稿人发现的局限是否已被作者承认？
一两段即可。>

## Overall Assessment / 总体评价与打分理由
<一段话：综合 strengths 与 weaknesses 的分量，解释为什么给这个分数。
必须与下面的分数自洽。>

- **Score / 评分**: <1-10>
- **Confidence / 置信度**: <1-5，附一句说明为何是该置信度>
```

---

## 各 Section 写作要求与示例

### Summary

- 用审稿人自己的理解重写，不抄摘要；控制在 150 词以内。
- 包含三要素：问题、方法核心 idea、主要结果/结论。
- 英文示例开头：`This paper addresses the problem of X. The authors propose Y, which ... The main finding is Z, demonstrated on benchmarks A and B.`

### Strengths

- 每条 = 结论句（加粗）+ 证据 + 价值说明。避免空洞赞美（"well-written" 只能算 minor strength，除非写作确实出色）。
- 好的示例：`**The theoretical analysis is rigorous and complete.** All proofs are self-contained in Appendix A, and Theorem 3.1 explicitly states its assumptions, which are verified empirically in Section 5.2. This level of rigor is rare in this subfield and makes the results trustworthy.`
- 差的示例（禁止）：`The paper is interesting and well organized.`（无证据、无信息量）

### Weaknesses

- 每条 = 问题 + 证据位置 + 影响 + 修复建议。
- 批评对事不对人；用 "the paper claims ... but the experiments show ..."，不用 "the authors failed to ..."（指人）这类表述。
- 区分事实与推测：推测性担忧必须标注，如 `I suspect ... , but I could not verify this from the text.`
- 数量上：major weaknesses 通常 2-4 条；堆 10 条琐碎问题冒充严格是低质量审稿。

### Questions to Authors

- 只问"答案会改变判断"的问题，如：`Could you clarify whether the test set of Benchmark B was used during model selection (Section 4.2)? If so, the main comparison may be compromised.`
- 不问可以直接从文中查证的事（说明没读仔细）。

### Score 与理由

- 分数定义见 review-criteria.md 的锚点表。理由段必须引用前面列出的具体 strengths/weaknesses 编号，形成闭环。
- 示例：`Given the solid empirical results (S1, S2) but the limited baseline fairness (W1) and missing significance testing (W2), I rate this paper 6: marginally above the acceptance threshold, provided the authors address W1 in revision.`

### Confidence

- 如实降档。示例：`Confidence: 3 — I am familiar with the general area but have not verified the proofs in Appendix A line by line.`

---

## 语气规范

1. 专业、直接、建设性；不讽刺、不居高临下、不奉承。
2. 每条批评给作者留出可执行的出路（补实验、加基线、澄清写法、公开代码）。
3. 遇到疑似学术诚信问题（抄袭、一稿多投、数据造假迹象），只陈述可观察的事实证据，不下道德定论，并建议由 AC/程序委员会处理。
4. 若用户是论文作者本人（自查场景），可在 review 末尾追加一节 `Actionable Revision Checklist / 修改清单`，把 weaknesses 按优先级转成 to-do list。
