---
name: intro-drafter
description: Drafts Introduction prose via a six-paragraph flow: background, limitations, problem and goal, challenges, solution overview, contributions. Use when asked to write or draft an Intro. Outputs prose.
---

# 引言起草器（Introduction Drafter）

## 与上级 paper-write 的协调

本 sub-skill 在 `paper-write/SKILL.md` 的 S0-S5 流程中被调用。写作时必须同时遵守上级定义的以下规则：

- **Provenance thinking**：写每段正文之前，先在内部想清楚每个事实性声明的来源（用户输入 / scholar_search 结果 / L0 常识）。没有来源的主张不写入正文。交付的正文中不包含任何方括号占位标签。
- **证据层级 L0-L4**：L0（领域常识，不含具体数字/人名/量化比较）可写背景铺垫；L1（全文）可写任何声明；L2（摘要）只写方向概述；L3（元数据）只写 "X et al. addressed Y"；L4（模型记忆）什么都不写。
- **Red Flags**：如果你想写一个你"记得"但无法追溯到用户输入或 scholar_search 的事实，停下来。用 scholar_search 验证——验证失败则改写或删除该声明。
- **不编造用户未提供的任何具体细节**：包括但不限于应用场景和使用领域、技术机制和物理原理、规模和数量描述、以及程序/实现细节（量表题目数、软件版本、实验参数等）。用户没给的细节直接省略。

## 概述

引言是整篇论文的压缩版本。在一页半到两页的篇幅里，它必须交代清楚：研究对象是什么、
这个问题为什么重要、已有工作为何不足、本文贡献了什么，以及这些贡献如何对应到正文
的各个章节。审稿人往往读完引言就决定要不要继续读下去，因此引言的逻辑主线必须无懈可击。

这个 skill 是一个 **正文生成器（prose generator）**，不是大纲生成器。它接收一小组输入
（研究领域、已有局限、核心思路、关键挑战、方案概览，以及可选的引用文献），输出
**真正成段的六段式引言正文**。六段式流程图只在内部用作思考脚手架，绝不出现在输出里。

输出的正文必须读起来像一位真正的研究者亲手写的引言：段落流畅、没有行内标签、没有
"Paragraph 1: Background" 这类 markdown 小标题、没有严重度表格、没有一致性检查报告。
就只是引言本身。

## 何时使用这个 skill

- 用户要求"写引言""起草 Intro""把这个想法写成引言段落"或"把这份粗略的计划整理成一篇
  正式的引言"。
- 用户已经有了一段左右的研究想法，想要的是打磨好的成段文字，而不是大纲。
- 用户给出了 Goal / Key Idea，但还没动笔写引言。
- 用户贴了参考文献，要求你把它们编织进引言里。

## 何时不要使用这个 skill

- 论文是 benchmark 类论文。请改用 `benchmark-paper-template`（独立 plugin），它的流程图
  不一样。
- 用户想起草 Methods / Results / Discussion / Abstract。请改用同级 skill
  `section-drafter/SKILL.md`。
- 用户已经有了引言正文，只想做润色。请把他们转给 `paper-polish`（同级 skill）。
- 用户想评估这篇引言是否达到了可投稿的水准。请把他们转给 `doubao-academic-evaluator`。

## 前置判断：这篇论文是 STEM 还是非 STEM？

本 skill 的六段模型（背景→局限→目标→挑战→方案→贡献）是为 STEM/技术类论文设计的。如果用户的研究属于非 STEM 范式（人文、社科、经济学、法学等），**不要用本 skill 的六段模型**——回到上级 `paper-write/SKILL.md` 的 CER 框架（Claim-Evidence-Reasoning-Role），按该学科的惯例直接为每段搭 CER 骨架后写正文。具体的学科惯例差异（结构、语气、证据类型）使用你自己的学科知识，但所有事实性声明仍必须遵守上级定义的 L0-L4 证据层级和 provenance thinking（写前想清来源、无来源不写）纪律。

判断依据是研究方法：有实验/基准/模型/算法 → 走下面的六段流程；其他范式 → 回上级 CER 框架。

如果是 STEM，继续走下面的核心流程。

## 核心流程（STEM/技术类论文）

整个流程是 **内部思考** 在前，**正文输出** 在后。不要把中间的思考过程打印出来；只打印
最终的引言。

### 第 1 步：论文类型定位（内部）

参见：`references/paper-types.md`，里面有 Technique 与 New Problem/Setting 的区分、定位
标准，以及 Alpha-SQL、AFlow、LEAD 的范例。

判断这篇论文属于哪一类：

- **Technique Paper**: main contribution is a new method or mechanism solving
  an existing problem. Narrative axis is Key Idea / Mechanism. Goal gets one
  sentence in passing.
- **New Problem/Setting Paper**: main contribution is a new problem
  formulation. Narrative axis is Goal / Problem Formulation. Key Idea
  supports "why this definition is reasonable".

这个判断决定了你起草时第 3 段（Paragraph 3）要承载多大的分量。

### 第 2 步：规划六个段落（内部）

参见：`references/flowchart.md`，里面有每一段的标准目的、写作要点和常见失败。

对这六个段落中的每一个，在心里想清楚：

- 这一段的 **目的（Purpose）**。
- 从用户输入中提炼出的 **两到四个具体写作要点（writing points）**。
- **缺口（Gaps）**：用户的输入在哪些地方没能给到你所需的东西。这些你写完之后再向用户
  指出，而不是写之前。

六个段落：

1. Background and Motivation. Running example. Why the problem matters.
2. Limitations of existing work (at most three).
3. Problem essence and Our Goal. Hard constraints explicit.
4. Key challenges (at most three).
5. Solution overview. One module per challenge.
6. Contributions (three or four, each maps to a section).

### 第 3 步：设计或挑选 running example（内部）

参见：`references/running-example.md`，里面有设计原则和模式。

如果用户没有提供 running example：

不要编造具体的领域场景或失败案例（`references/running-example.md` 明确要求例子必须是 "Real. The example is drawn from real data or a real deployment, not fabricated."）。用用户给出的抽象问题描述写背景段。在第 6 步的可选说明中提醒用户："一个具体的 running example 能让第 1 段更有说服力——你能否提供一个来自你实验/部署中的真实场景？"

### 第 4 步：检查对齐（内部，动笔之前）

参见：`references/contribution-patterns.md`，里面有强模式与弱模式的对比。

在心里默默核对：

- Running-example loop: 第 1 段的例子在第 5 段或第 6 段重新出现。
- Limitations -> Challenges: 第 4 段的每一个 challenge 都对应解决第 2 段的某个
  limitation 或第 3 段的某个 hard constraint。
- Goal -> Contribution 1: 第 3 段的 Goal 与第 6 段的第一条 contribution 对齐。
- Challenges -> Modules: 一一对应，而不是多对多。
- Contributions: 三或四条，每条对应一个章节，不要出现 "extensive experiments" 这类
  含糊措辞。

如果某项核对没通过，**在动笔写正文之前** 先在你的规划里把它修好。不要围着一条断裂的
逻辑链去写正文。

### 第 5 步：写正文

现在起草六段流畅的正文。遵守以下纪律：

- **输出里不要出现段落标签**。读者看到的只应是流畅的正文，可带自然的过渡语
  （"Despite this progress, ...", "In this work, we ...", "We summarise our
  contributions as follows."）。
- **每一段是一个整块**，约 100-250 词，具体取决于这一段的角色和论文类型。Technique 与
  New Problem 的篇幅分配见 `references/paper-types.md`。
- **语言**。输出语言已由上级 skill `paper-write` 根据用户明确的要求决定。如果用户指向
  的是中文期刊，或说了"写中文版"/"用中文写"，就输出中文正文；否则输出英文。不要让你
  自己的输入语言（即用户消息的语言）触发中文输出——很多用户用中文描述想法，但论文是
  用英文投的。拿不准时，用英文。
- **引用格式与密度**。采用 numeric citation-sequence 格式，按引用首次出现的顺序标注 `[1]`、`[2]`、...。
  **一篇完整的六段 Introduction 通常需要 15-25 条引用**——第 1 段（背景）3-5 条、第 2 段
  （已有工作局限）5-8 条、第 3-5 段各 2-4 条、第 6 段（贡献）0-2 条。引用稀疏的 Intro
  读起来像观点文章而非学术论文。动笔前先用 `scholar_search` 搜 3-5 轮不同关键词建立
  文献池，围绕搜到的真实文献组织论述。缺少来源时继续搜索而非回避引用；实在搜不到则
  改写为不需要引用的表述。不使用 `[citation needed]`。
  **正文之后必须输出 References 列表**，逐条列出所有引用文献，编号与正文 `[N]` 一一对应。
  用户指定 APA、Chicago 等其他 citation style 时从其要求。
- **数字与论断**。不要编造具体的百分比、加速比或 benchmark 数字。如果某条 contribution
  提到了具体增益，那必须是用户告诉过你的；否则就用 "improves over prior baselines"
  这类措辞，不附加任何标签。
- **时态（Voice）**。Past tense for prior work and what you observed; present or
  future tense for the paper's own claims that have not been validated yet
  ("this paper proposes", "we introduce", "we hypothesise that")。如果实验结果还没有
  报告给你，就不要写 "we achieved" 或 "we demonstrated"。
- **语气与措辞**。定稿前，对照上级层的几个 reference 文件扫一遍，检查语言质量：
  `../../../references/ai-tone-guardrails.md`（需要剔除的 AI 腔信号和夸大论断）、
  `../../../references/academic-phrasebank.md`（与证据强度匹配的 hedging 动词、gap 描述、
  过渡语）、`../../../references/section-conventions.md`（引言特有的惯例和常见陷阱）。
  这几个文件由所有 sub-skill 共享。

### 第 6 步：一句简短的后续说明（可选，最多三行）

在六段正文之后，你可以加上至多一小段自然语言的说明（不要表格、不要列表、不要严重度
标签），提醒用户注意：你打了占位的缺口、某段因为缺信息而写得比较试探性、或某个结构上
的隐忧。最多三行。如果你确实没有真正有用的话要补充，就整个略去。

## 输出长什么样

用户拿到的是：

- 六段引言正文，段与段之间用空行隔开，正文中用 `[1]`、`[2]`、... 标注引用。
- 正文之后紧跟 **References** 列表，逐条列出所有引用文献，编号与正文一一对应。
- 没有标题、没有标签、没有表格。
- 可选地，References 之后一段 1-3 行的纯文字说明。

就这些。别的都没有。

## 输出里绝对不能出现什么

这是本文件中最重要的一段。交给用户的输出绝对不能包含：

- 给段落命名的 markdown 标题（"## Paragraph 1: Background"）。
- 类型定位小节（"Type: Technique Paper"）。
- 流程图一致性表格（"Running-example loop: pass"）。
- 完整性闸门结果（"Gate 1-7: pass"）。
- 严重度汇总（"3 CRITICAL, 2 MAJOR"）。
- 任何对内部步骤名的引用（"Step 5 produced the following"）。
- 带标签的句子（"[user provided]"、"[model inference]"、"[citation needed]"、
  "[to be verified]"、"[to be specified by authors]"、"[to be confirmed]" 及其任何变体
  如 "[citation needed: specific gain]"）。如果缺少引用来源，用 scholar_search 搜索；
  搜不到则改写句子去掉引用需求，或在正文之后的可选说明中用自然语言提醒。

这些都是内部脚手架。它们是你的思考方式，不是用户该看到的东西。如果你发现自己正要写
其中任何一项，删掉它，接着写正文。

## 跨 skill 交接

- 如果引言已经起草好，而用户想要论文的其余部分，交接给同级 skill
  `section-drafter/SKILL.md`。
- 你产出的引言正文交回上级 `paper-write` 的 S5，由它统一回流 `paper-polish` 做语言收尾并交付——这是写作流程的固定一步，不是"读起来生硬才可选运行"的附加项。
- 如果你怀疑这个想法本身还不足以冲击顶会，不要在引言正文里说出来；在第 6 步那段可选的
  后续说明里提一下，并建议用户运行 `doubao-academic-evaluator`。

## 致谢

本 skill 及 `references/` 改编自 [HKUSTDial/Supervisor-Skills](https://github.com/HKUSTDial/Supervisor-Skills)。
