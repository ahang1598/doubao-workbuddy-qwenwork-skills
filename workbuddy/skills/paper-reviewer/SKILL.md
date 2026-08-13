---
name: paper-reviewer
description: 专业学术论文审稿 skill。以领域专家视角对学术论文（本地 PDF、arXiv ID/URL、粘贴文本）进行系统评审，自动识别论文学科与贡献类型并切换对应领域专家标准，输出顶会 OpenReview 风格（NeurIPS/ICLR/ICML）的标准 review 意见：Summary、Strengths、Weaknesses、Questions to Authors、Overall Score (1-10)、Confidence。输出语言跟随论文语言。触发场景包括：审论文、审稿、论文评审、review this paper、peer review、写评审意见、帮我看看这篇论文能不能中、rebuttal 前自查等。
agent_created: true
---

# Paper Reviewer

## Overview

以真实顶会审稿人的标准与严谨度评审学术论文：通读全文 → 识别领域 → 切换专家视角 → 逐维度证据化分析 → 输出标准 OpenReview 格式 review。核心原则是**每一条论断都必须锚定论文中的具体证据**（章节、页码、公式、图表、实验数字），杜绝泛泛而谈和臆造内容。

## 审稿工作流

### Step 1: 获取并通读论文

根据输入形式选择获取方式：

- **本地 PDF 路径** → 用 Read 工具直接读取（支持 PDF 分页读取）。
- **arXiv ID 或 URL** → 下载 PDF 到本地后用 Read 读取；若网络受限，抓取 arXiv HTML 版本（`https://arxiv.org/abs/<id>`）。
- **粘贴的全文/片段** → 直接分析，但若内容明显不完整（缺实验、缺结论），在 review 中注明评审基于不完整稿件。

**必须通读全文后才能动笔**，包括方法、实验、附录（若有）。只读摘要和引言就出评审意见是审稿大忌，禁止这样做。

### Step 2: 识别领域与论文类型

通读后先判断（写入内部分析，不必输出）：

1. **学科与子领域**：如机器学习、NLP、CV、系统/网络、软件工程、理论计算机、HCI、生物信息、医学、社会科学、自然科学实验等。
2. **贡献类型**：新算法/方法、理论分析、实证研究、Benchmark/数据集、系统构建、综述、应用案例。贡献类型决定评价权重的分配。

打开 `references/review-criteria.md`，加载其中的「五维度评审细则」与该学科对应的「分学科检查清单」，作为本稿的评审标尺。

### Step 3: 建立专家视角

以该领域**资深审稿人**（相当于顶会 AC/Senior Reviewer 水平）的视角评审，要求：

- 熟悉该领域主流方法、经典基线与近期进展，能判断 claim 的创新性是相对什么基线而言的。
- 能识别实验设计中的常见漏洞（数据泄漏、基线不公平、指标选择偏差、统计显著性缺失等）。
- 若论文超出自身可靠判断范围（如高度专业的数学证明、湿实验细节），在 Confidence 上如实降档，并在 review 中声明不确定之处，**不装懂、不臆断**。

### Step 4: 逐维度深度分析

按 `references/review-criteria.md` 的五个维度逐一分析：Novelty（新颖性）、Soundness（技术严谨性）、Clarity（表达清晰度）、Significance（影响力）、Reproducibility（可复现性）。

分析纪律：

- **证据锚定**：每个 strength/weakness 必须引用论文具体位置，如 "Section 3.2 的式 (5)"、"Table 2 中 X 数据集上的结果"、"第 4 页第 2 段"。
- **区分 major / minor**：致命缺陷（实验无法支撑结论、证明有错误、创新性表述失实）与次要问题（排版、笔误、图表可读性）分开陈述。
- **先理解作者的 claim，再评估证据是否支撑 claim**——不要用"我认为应该做什么"代替"论文声称了什么、证明了什么"。

### Step 5: 按标准模板输出 review

打开 `references/review-template.md`，严格按其中的 OpenReview 模板输出，包含：Summary、Strengths、Weaknesses、Questions to Authors、Limitations 确认、Overall Score (1-10) 及理由、Confidence (1-5)。

输出语言规则：

- **英文论文 → 英文 review**；中文论文 → 中文 review。
- 用户显式指定语言时，以用户要求为准。
- 无论哪种语言，Weaknesses 和 Questions 保持专业、具体、建设性——指出问题的同时尽量给出可操作的修改方向。

补充交付（用户要求时才做）：

- **Rebuttal 预判**：列出作者最可能的反驳点及回应建议。
- **修改清单**：把 weaknesses 转成按优先级排序的 to-do list，供作者投稿前自查。
- **审稿人对比**：模拟 2-3 位不同倾向审稿人（严格派/宽容派/应用派）给出多份 review。

## 硬性规则

1. **不臆造**：论文中不存在的内容（数字、实验、引用）绝不写进 review；不确定的地方明确说 "I could not verify..."。
2. **评分诚实**：分数必须反映真实判断，不为讨好用户而抬分；评分理由要与 strengths/weaknesses 的分量一致。
3. **建设性**：批评对事不对人，每个 major weakness 尽量附带改进建议或验证实验建议。
4. **时效意识**：判断相关工作新颖性时，如不确定最新进展，用 WebSearch 快速核查该方向近期工作，避免以过时认知误判创新性（在 review 中注明核查范围）。
5. **拒绝代写造假**：本 skill 用于真实评审与自查，不用于伪造同行评审意见欺骗期刊/会议。

## Resources

### references/

- `review-criteria.md` — 评分锚点（1-10 分与 Confidence 1-5 的定义）、五维度评审细则、分学科检查清单（ML/NLP/CV/系统/理论/HCI/生物医学/社科/自然科学）、常见致命缺陷清单、major vs minor 区分标准。**Step 2 和 Step 4 必读**。
- `review-template.md` — OpenReview 标准输出模板（中英双语结构）、各 section 写作要求与示例片段、语气规范。**Step 5 必读**。
