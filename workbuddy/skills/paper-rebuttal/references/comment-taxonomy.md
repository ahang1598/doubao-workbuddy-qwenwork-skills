# 审稿意见分类体系与应对策略

用于阶段 1（拆解意见）和阶段 2（判定处置）。每条意见归入一个**意见类型**，并判定为 A/B/C/D 四种**处置类别**之一。

## 一、意见类型（意见在说什么）

| 类型 | 典型表述 | 常见处置 |
|------|----------|----------|
| 新颖性质疑 | "limited novelty", "incremental", "similar to [X]" | A 或 D：澄清与已有工作的差异，列对比表 |
| 方法质疑 | "why not use X", "the assumption is unrealistic", "complexity?" | A（解释设计动机）或 C（补充分析/实验） |
| 实验不足 | "missing baseline", "no ablation", "only one dataset", "statistical significance?" | C：补实验；无法补时给已有证据 + future work |
| 结果质疑 | "improvement is marginal", "numbers seem wrong", "cherry-picked" | A（解释评价协议）或 C（补充显著性检验/更多种子） |
| 理解与表述 | "unclear", "confusing notation", "how does Eq.(3) follow?" | B：改写、补定义、加示意 |
| 文献遗漏 | "missing related work [X]" | B：补充引用并讨论差异；若 [X] 不相关则 A/D |
| 写作与格式 | 错别字、图表可读性、结构问题 | B：直接修改 |
| 局限性/影响 | "limitations not discussed", "broader impact?" | B：补 Limitations 小节 |
| 超范围要求 | 要求做本质上另一篇论文的工作 | A/D：礼貌说明超出本文范围，承诺 future work |

## 二、处置类别判定（要不要改论文）

### A 类 — 可直接回答（不改论文）
判定条件（满足其一）：
- 论文中已有明确答案，审稿人未注意到 → 回复中引用精确位置（§章节 / Page / Line / Eq. / Table / Figure）。
- 审稿人误解了方法/设定 → 先感谢并承认表述可能不够醒目（可考虑顺手升级为 B 类微调表述），再给出解释。

禁忌：不得只说"请见论文第 X 节"而不给出实质解释。

### B 类 — 需小修改（改论文，不动核心内容）
判定条件：意见指出的问题通过增删几句话、补引用、改符号/图表说明即可解决，不改变方法、实验与结论。
执行：直接修改论文源文件，记入修改日志。

### C 类 — 需实质修改（补实验/补分析/补章节）
判定条件：审稿人指出的缺陷属实且影响结论可信度，如缺关键基线、缺消融、缺复杂度分析、结论超出证据范围。
执行顺序：
1. 评估工作量与截止时间，向用户确认是否能补做实验/分析；
2. 能完成的：补做 → 更新论文（正文 + 图表 + 结论措辞）→ 记入修改日志；
3. 无法完成的：回复中诚实说明原因（如计算资源/时间），提供已有证据部分回应，明确写入 future work；必要时同时弱化论文中过强的结论措辞（属于 B/C 混合修改）。

### D 类 — 意见不成立（礼貌反驳）
判定条件（必须同时满足）：
1. 意见基于事实性错误（如误读公式、混淆设定、引用了不相关的工作）；
2. 有论文原文或可引用的外部文献作为硬证据；
3. 反驳不会给人留下"防御性"印象——先找可认同的部分。

反驳框架（三段）：
1. 认同合理内核："We agree that ... is important / the reviewer raises a valid point about ..."；
2. 澄清事实："However, in our setting, ... (see §X, Eq.Y). Specifically, ..."；
3. 给出证据或行动："We have clarified this in the revision / The result in Table N shows ..."。

禁忌：禁止说审稿人"错了/没读懂"；禁止情绪化措辞；无硬证据时降级为 A 类解释或 B 类澄清性修改。

## 三、严重程度标注

- **Major**：直接影响接收决定（新颖性、方法正确性、关键实验缺失）→ 回复篇幅最长，优先处理。
- **Minor**：表述、引用、图表等 → 快速修改，回复简短。
- **Question**：单纯提问 → A 类直接回答。

严重程度由审稿人措辞（"major concern" / "minor" / "question"）和 meta-review 关注点共同决定。

## 四、整体关注点提取

除逐条意见外，单独记录：
- 各审稿人评分与置信度；
- meta-review / AC 总结的核心关切（若有，必须在 rebuttal 总述段首先回应）；
- 多个审稿人重复提到的问题（优先级最高，说明是论文真实弱点，几乎必然是 B/C 类）。
