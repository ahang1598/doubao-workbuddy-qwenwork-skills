---
name: section-drafter
description: Drafts prose for any non-Introduction section (Abstract, Related Work, Methods, Results, Discussion, Conclusion). Uses a thinking-template and self-consistency checks. Outputs flowing prose.
---

# 章节撰写器（Section Drafter）

## 与上级 paper-write 的协调

本 sub-skill 在 `paper-write/SKILL.md` 的 S0-S5 流程中被调用。写作时必须同时遵守上级定义的以下规则：

- **Provenance thinking**：写每段正文之前，先在内部想清楚每个事实性声明的来源（用户输入 / scholar_search 结果 / L0 常识）。没有来源的主张不写入正文。交付的正文中不包含任何方括号占位标签。
- **证据层级 L0-L4**：L0（领域常识，不含具体数字/人名/量化比较）可写背景铺垫；L1（全文）可写任何声明；L2（摘要）只写方向概述；L3（元数据）只写 "X et al. addressed Y"；L4（模型记忆）什么都不写。
- **Red Flags**：如果你想写一个你"记得"但无法追溯到用户输入或 scholar_search 的事实，停下来。用 scholar_search 验证——验证失败则改写或删除该声明。
- **不编造用户未提供的任何具体细节**：包括但不限于应用场景和使用领域、技术机制和物理原理、规模和数量描述、以及程序/实现细节（量表题目数、软件版本、实验参数、beam size、bins 数量、采样策略等）。用户没给的细节直接省略。

## 总览

在为任何章节落笔之前，你脑子里必须先有一副完整的论文逻辑骨架：研究背景、前人工作
的具体局限、核心思路或研究目标、阻碍朴素方案成立的技术挑战、逐一应对这些挑战的方
法模块，以及论文最终要主张的贡献。没有这副骨架就写 Methods，会写成平铺直叙的清单；
没有它写 Discussion，会写成空泛的猜测；没有它写 Abstract，会写成千篇一律的概述。

本 skill 通过一套标准化的思考模板在内部搭起这副骨架，对整条逻辑链跑四项自洽性检
查，然后撰写**用户实际要求的那个章节**的正文。输出的是正文，不是填好的模板，也不
是自洽性检查报告。

如果用户要的是 Introduction，请改用同级 skill `intro-drafter/SKILL.md`，它有一套
专为引言设计的六段式框架。

## 何时使用本 skill

- 用户要求撰写任意非引言章节的正文：
  - "写一下 Methods 章节"
  - "为这个想法起草一段 Discussion"
  - "帮我写 Abstract"
  - "把这些放进 Results 章节"
  - "起草 Related Work"
  - "写 Conclusion"
- 用户正在构思某个章节该包含什么内容，想要成段的文字，而不只是要点列表。
- 用户已有实验结果，想把它们写成文字。
- 用户已有某章节的部分草稿，需要补完。

## 何时不要使用本 skill

- 用户要的是 **Introduction**。请用同级的 `intro-drafter/SKILL.md`。
- 用户已有成稿正文，想做语言润色。请用上一级的 `paper-polish` skill。
- 这是一篇 benchmark 论文。在落笔前的规划阶段，请用 `benchmark-paper-template`
  （独立插件）。
- 用户想评估某章节是否达到投稿标准。请引导他们去 `doubao-academic-evaluator`。

## 核心流程

整个流程是**内部思考**在前、**正文输出**在后。思考模板与自洽性检查都在静默中完
成；输出里只出现用户要求的那个章节的正文。

### 第 1 步：确认用户想要哪个章节

常见情形，以及对应要套用的 section-specific guidance 小节（见下文）：

- Abstract
- Related Work
- Methods（或 Methodology）
- Results
- Discussion
- Conclusion 或 Future Work

如果用户已明确点名某个章节，就用它。如果没有，从输入里推断：实验结果指向 Results；
机理解释指向 Discussion；要一段高层概述则指向 Abstract。

如果实在判断不出来，问一个简短的问题然后停下。

### 第 2 步：论文类型定位（内部）

参见 `references/paper-types.md`，区分 Technique、New Problem/Setting 与 Cross-domain
三类。

论文类型决定了每个章节的权重分配。Technique 类论文的 Methods 是主角；New Problem
类论文的 Methods 更简洁，但其 Discussion 中"为何这个新设定重要"才是承重墙。

如果用户的输入描述的其实是一篇 benchmark 论文，请停下并转至
`benchmark-paper-template`（独立插件）完成规划，再回到这里做章节撰写。

### 第 3 步：填写思考模板（内部）

参见 `references/thinking-template.md`，了解每一格的内容契约与常见失败模式。

用用户给你的材料，在脑中静默地把这六格填上。用户没有给出的格子，保守地推断，或留作
一个问题，待写完正文后再标出。

1. Research background. Scenario, importance, motivation.
2. Limitations 1 through 3 of prior work.
3. Key Idea (Technique) or Our Goal (New Problem).
4. Challenges 1 through 3.
5. Methodology modules. One module per challenge.
6. Contributions (3 or 4).

### 第 4 步：跑四项自洽性检查（内部）

参见 `references/consistency-checks.md`，了解检查步骤与逻辑链断裂的示例。

1. **Limitations to Key Idea**: does the Key Idea address the Limitations?
2. **Key Idea to Challenges**: do the Challenges arise from implementing
   the Key Idea?
3. **Challenges to Methodology**: does each module address a specific
   challenge?
4. **Methodology to Contributions**: do contributions cover modules and
   results?

如果某项检查没通过，先在你的方案里修好底层的不一致，再动笔。不要围绕一条断裂的逻辑
链硬写正文——在审稿人眼里那会读起来像东拼西凑。

### 第 5 步：套用章节专属写作指引

参照下文的 section-specific 笔记，确定每个章节该包含什么、该怎么写。第 3 步的思考模
板各格给你的是内容；这些笔记给你的是形式。

### 第 6 步：撰写正文

把用户要的章节写成流畅的正文。纪律如下：

- **No labels in the output**. No "Methods", "Discussion" markdown header
  unless the user explicitly asked for the section header. Just prose, in
  paragraphs.
- **No internal scaffolding in the output**. The thinking template, the
  consistency checks, the paper-type decision are all silent. The user does
  not see them.
- **Language**. The output language was decided by the parent skill
  `paper-write` based on what the user explicitly asked for. If the user
  pointed to a Chinese journal or said "写中文版" / "用中文写", output
  Chinese prose. Otherwise output English. Do not let your own input
  language (the user's message) trigger Chinese output — many users
  describe ideas in Chinese but submit papers in English. When in doubt,
  English.
- **Citation style**. Use sequential numbering `[1]`, `[2]`, ... by order
  of first appearance in the text. If a reference is needed but unavailable,
  use `scholar_search` to find one. If search fails, rephrase the sentence
  so it no longer requires a citation, or omit the claim. Do not insert
  `[citation needed]`. If the user specifies a different citation style
  (APA 7th, Chicago Author-Date, etc.), follow their request.
- **Numbers**. Do not invent. If the user has not reported numbers, write
  qualitatively. Do not use `[to be specified by authors]`.
- **Voice**. Past tense for what was observed in this paper or prior work;
  present tense for principles and generalisations. Avoid "demonstrated"
  or "achieved" for results that have not been reported to you.
- **Tone and phrasing**. Before finalising, scan the prose against the
  parent-level reference files for language quality:
  `../../../references/ai-tone-guardrails.md` (AI-tone signals and inflated
  claims to remove), `../../../references/academic-phrasebank.md` (hedging
  verbs matched to evidence strength, gap descriptions, transitions), and
  `../../../references/section-conventions.md` (section-specific conventions
  and common pitfalls). These are shared across all sub-skills.

### 第 7 步：一句简短的后续提示（可选，至多三行）

正文之后，你可以附上至多三行纯文字，提醒用户该留意什么（一处占位的数字、一个暂定的
主张、一个结构上的隐忧）。不要表格，不要列表，不要标题。如果实在没有真正有用的东西
要说，就省略。

## Section-specific writing guidance

### Abstract

Aim for 200-250 words. Structure: one sentence stating the problem and its
importance; one sentence on the limitation of prior work; one sentence on
the key idea or contribution of the paper; two to three sentences on the
method at a high level; two sentences on the main results (qualitative if
no numbers given); one sentence on the significance or implications.

No citations in the abstract. No undefined acronyms. If a name is introduced
(framework, dataset, model), it must appear at least once more in the rest
of the paper. Avoid superlatives ("state-of-the-art", "revolutionary").

### Related Work

Structure as themes, not as a chronological list of papers. Two to four
themes is typical. For each theme: state the line of work, name two to four
representative works with brief description of their approach, end with a
sentence that names the specific limitation this paper addresses. The last
sentence of each theme links to a limitation in your Thinking Template.

Do not write "for a survey, see ...". Do not write "while many works have
explored ...". Each Related Work paragraph should leave the reader knowing
exactly where this paper sits in the landscape.

### Methods (Methodology)

Open with a one-paragraph overview that names the framework (one sentence),
states the overall pipeline (one to two sentences), and lists the modules
(one sentence per module). This overview paragraph mirrors the Solution
Overview paragraph from the Introduction.

For each module, write a subsection (one paragraph if the section is short,
two to three if the paper requires depth) that: states the module's purpose
(addresses Challenge N), describes the technical mechanism, optionally gives
a worked example using the paper's running example, and notes any practical
implementation considerations.

Equations: include only if the user gave them, or if a specific equation is
necessary for the mechanism. Do not invent equations. If a formal expression
is needed but the user has not given it, describe the relationship in prose
and ask the user for the equation after the draft — do not insert a bracketed
placeholder tag. Format: `$$...$$` for display equations, `$...$` inline.

### Results

Open with a brief paragraph naming the evaluation setup (datasets,
baselines, metrics) — only with the values the user has actually given.

For each result, follow the **describe-then-interpret** rule: first state
what was observed (the number, the comparison, the trend), then interpret
what it means (which challenge this resolves, what hypothesis this supports,
which baseline it dominates and why).

Do not invent specific numbers. If a result needs a percentage but the user
did not give it, use phrasing like "outperforms prior baselines by a
substantial margin (specific values reported in Table N)" with the actual
table number from the user's input or `[Table N]` placeholder.

Distinguish: what was observed vs what is inferred. Write "we observe X"
versus "this suggests Y". Never collapse the two.

### Discussion

The Discussion is where the paper earns its venue tier. Three layers:

1. **Mechanism layer**: explain why the results are what they are. Connect
   to the Key Idea from your thinking template. If the user gave you a
   mechanism hypothesis, develop it; if not, propose the most plausible
   mechanism consistent with the observed results and flag it as a working
   hypothesis.
2. **Connection to prior work**: relate the findings to the Limitations cell
   in your thinking template. State what prior work cannot explain and how
   this paper's findings provide a different account. Cite specifically if
   the user gave references; otherwise use `scholar_search` to find the
   reference, and if that fails, rephrase so the sentence no longer requires
   a citation. Do not insert `[citation needed]`.
3. **Limits and future work**: name two to three specific things this paper
   does not establish. Do not write a generic "limitations" paragraph. Be
   specific: "we have not validated X under condition Y" or "the proposed
   mechanism for Z requires further confirmation via experiment W".

Voice discipline for Discussion is critical. Use:

- "is consistent with" for what aligns with prior reports.
- "suggests that" for hypotheses the data supports.
- "we hypothesise that" for proposed mechanisms not yet directly tested.
- "would require further validation" for tentative claims.

Avoid "proves", "demonstrates conclusively", "establishes" unless the user
has explicitly told you the experiment provides such proof.

### Conclusion

One to two paragraphs. First paragraph: restate the problem and what the
paper contributed (one sentence each on Key Idea, methodology, main result).
Second paragraph: state two or three concrete next steps or open questions.

Do not summarise the whole paper section by section. Do not introduce new
material. Do not repeat the Abstract.

### Future Work (if separate from Conclusion)

Two to three numbered or paragraph items, each: states a specific gap this
paper does not close, why it matters, and a feasible next experiment or
extension. Do not list every possible extension; list the ones the paper's
findings most directly call for.

## 输出最终长什么样

用户会收到：

- 他们要的那个章节，写成流畅的正文，按段落组织（章节较长时再分小节），正文中用 `[1]`、`[2]`、... 标注引用。
- 正文之后紧跟 **References** 列表，逐条列出所有引用文献，编号与正文一一对应。
- 可选：References 之后至多三行纯文字的后续提示。

除此之外，别无他物。

## 输出里绝对不能出现什么

纪律与 `intro-drafter/SKILL.md` 一致。给用户的输出绝对不能包含：

- A filled-in thinking template ("| Stage | Content |").
- A consistency check report ("Check 1: pass").
- An integrity gate result.
- A severity summary.
- Section names as markdown headers unless the user explicitly asked for
  them (e.g., the user said "format with subsection headers").
- Tagged sentences ("[user provided]", "[model inference]", "[citation needed]",
  "[to be verified]", "[to be specified by authors]", "[to be confirmed]").
- A breakdown of what the model did internally ("Based on the thinking
  template I built, ...").
- Any meta-commentary about the model's own process, including: "Let me
  first analyze...", "Following the CER framework...", "Here I will
  structure...", "Based on the evidence collected in S1...", or Chinese
  equivalents like "首先让我分析一下..."、"根据 S2 的蓝图...". Start directly
  with the prose content, never with a description of your own workflow.

一旦发现自己正要写下上述任何一项，删掉它，回到正文。

## 跨 skill 交接

- 如果用户要的是 **Introduction**，那你就是错的 skill。交接给
  `intro-drafter/SKILL.md`。
- 你产出的章节正文交回上级 `paper-write` 的 S5，由它统一回流 `paper-polish` 做语言收尾并交付——这是写作流程的固定一步，不是"读起来生硬才可选运行"的附加项。
- 如果用户想把整篇论文都起草出来，一次只写一个章节。问清从哪个开始。
- 如果在撰写过程中你怀疑底层的想法太弱（Discussion 没有真正的机理、Methods 没有清
  晰的新意），不要把这层判断写进章节正文里；把它放在可选的后续提示里，并建议用户去
  `doubao-academic-evaluator`。

## 致谢

本 skill 及 `references/` 改编自 [HKUSTDial/Supervisor-Skills](https://github.com/HKUSTDial/Supervisor-Skills)。
