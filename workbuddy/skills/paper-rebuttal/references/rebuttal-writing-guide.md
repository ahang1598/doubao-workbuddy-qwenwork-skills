# Rebuttal 写作指南

## 一、写作原则

1. **感谢在前，实质在后**：开头感谢要简短（一句），重点放在实质回应，避免通篇客套。
2. **每条必答**：所有意见逐条回应；多条相似意见合并回复时，在每个提出者处都注明"见对 Rx.y 的回复"。
3. **先答后改**：每条回复先说结论/答案，再说修改。审稿人最先想看到的是"你接不接受我的观点"。
4. **证据导向**：任何声明都要落到具体位置（章节/页/行/公式/图表编号）或具体数据。
5. **不防御、不夸大**：承认真实弱点；承诺只写确定能兑现的（已完成的修改写过去时，未完成的写 future work）。
6. **区分时态**：已完成的修改用 "We have revised/added/updated..."；仅计划的不写进 Change made。

## 二、单条回复结构（三段式）

```
[Rx.y] <审稿人原话或精确概括（斜体或引用块）>

Response: <结论先行的回答。A 类给解释+原文引用；D 类给澄清+证据；B/C 类确认问题并简述方案。>

Change made: <仅 B/C 类需要。修改位置 + 内容摘要，与修改日志一致。>
```

篇幅分配：Major > Question > Minor。整体超字数时，压缩 A 类回复的解释部分，但不得删除任何条目。

## 三、语气红线

| 禁止 | 替换为 |
|------|--------|
| "The reviewer is wrong / misunderstood" | "We apologize for the ambiguity; we have clarified..." |
| "This is impossible / infeasible" | "This requires resources beyond the revision period; we have instead provided ... and will ... in future work" |
| "Obviously / Clearly" | 直接陈述事实 |
| 重复审稿人措辞中的负面词 | 中性概括："Regarding the concern on X..." |

## 四、常用句式库（英文）

**开头致谢**
- "We thank all reviewers for their constructive feedback. We have carefully revised the manuscript accordingly."
- "We are grateful for the recognition of [优点]. Below we address each concern in detail."

**A 类（解释）**
- "We thank the reviewer for the question. X is in fact addressed in §Y (Page Z, Lines A–B): ..."
- "We apologize for not making this sufficiently clear. The key distinction is that ..."

**B 类（小修改）**
- "We agree and have revised §X accordingly. The revised text now reads: '...'"
- "We have added citations to [X, Y] and discussed their differences in §Related Work."

**C 类（实质修改/补实验）**
- "Following the suggestion, we conducted a new experiment on [dataset/setting]. The results (Table N, Page P) show that ..., which supports our claim."
- "We have added an ablation study on X (§Y, Table Z). Removing X degrades performance by N%, confirming its contribution."
- 无法完成时："A full study on X requires [reason]. Within the revision period, we provide [已有证据] in §Y; a comprehensive study is planned as future work."

**D 类（礼貌反驳）**
- "We respectfully clarify that ... Specifically, Eq.(N) assumes ..., which holds in our setting because ..."
- "While [cited work] is related, it differs in [aspect]; our method targets ... We have added this discussion to §X to prevent confusion."

**收尾**
- "We hope the revisions address all concerns. We are happy to make further adjustments if needed."

## 五、中文场景

中文期刊/中文审稿意见时，回复用中文，结构与句式对应替换：
- "感谢审稿专家的宝贵意见。我们已逐条修改，具体回复如下。"
- "感谢您的指正。本文第 X 节已对此进行说明（第 X 页第 X 段）：……"
- "遵照建议，我们补充了 XX 实验，结果见修订稿表 N（第 X 页）。"
- "经仔细核对，此处可能存在误解：本文设定为……（见式 (N)），因此……。为避免歧义，我们已在修订稿第 X 节补充说明。"
