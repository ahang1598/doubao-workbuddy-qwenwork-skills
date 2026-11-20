# 2023 年以来用 self-instruct 造数据训练小模型并做 benchmark 的论文：三条改造路线与一个反证

## 一、核心结论

**总体判断**：你问的是"2023 年以来，有没有一类论文用 self-instruct 生成指令数据、训练小模型、并在 benchmark 上评测"。答案是有的，但**严格照搬原版 Self-Instruct 流水线（175 个手写种子任务自举、再用同一族大模型训练）并且只训小模型的工作几乎没有**：2023 年之后真正跑通"自生成数据 → 小模型 → benchmark"这一闭环的工作，几乎都改动了自举链条上的某一环。下面按被改动的环节分成三条主路线（数据规模与多样性、指令生成器、种子来源），再补一条关于数据配比与规模边界的限定证据，以及一条正在出现的反证。

1. **原版 Self-Instruct 直接搬到 10B–40B 模型上会失效，这是后续所有改造的起点。** 原范式由 Wang et al.（2023a）提出，用 175 个手写种子任务让模型自举指令，并在 175B 模型上验证有效；Lee et al.（2023）把这套流程搬到 10B–40B 的宽松许可模型上时发现效果明显下降，必须简化 in-context 模板、并对多个模型的输出做集成，才能把数据质量拉回来。这条反证解释了为什么 2023 年之后的小模型论文大多不再"原样复现"。

2. **路线一（规模与多样性）用"量"换"质"，是目前唯一在 1B 以下规模上给出完整 benchmark 证据的路线。** Wu et al.（2024）构造 2.58M 条指令（既有指令 + 新生成指令），用 gpt-3.5-turbo 生成回答，微调 0.5B–1.5B 的 encoder-decoder 与 decoder-only 两组模型，在 15 个 NLP benchmark 的自动指标上加人工评估，结论是小得多的模型可以与强基线相当。

3. **路线二（改指令生成器）是 7B/13B 上最主流、硬指标最可查的一路。** Evol-Instruct 通过深度与广度进化把简单指令改写成复杂指令，LLaMA-7B/13B 与 Code Llama-7B/13B 分别在 AlpacaEval、GSM8K 以及 HumanEval、MBPP 上超过对应基座（Xu et al.，2024；Luo et al.，2024）；Ada-Instruct 进一步指出连 GPT-4o 都产不出足够长的复杂指令，改用 10 条样本微调出的生成器之后，13B 模型在 HumanEval、MBPP、GSM8K、MATH 上均优于用 Self-Instruct 数据训练的同规模模型（Cui & Wang，2024）。

4. **路线三（换种子来源）把"人写的种子任务"换成真实语料或模型自身分布，绕开了种子瓶颈。** OSS-Instruct 从真实开源代码片段反推指令，Code Llama-7B 级模型在 HumanEval+ 与 MBPP 上超过同等规模的代码指令模型（Wei 等，2024）；Magpie 更进一步，完全不给种子，直接让对齐好的模型自己采样指令，8B 级模型在 AlpacaEval 2、Arena-Hard 等对齐评测上达到可与更强模型相比的水平（Xu 等，2025）。

5. **这些数字之间不能直接横比，因为评测口径已经分裂成两套。** 代码与数学路线用 pass@1 硬指标（HumanEval、MBPP、GSM8K、MATH），通用对话路线用 LLM judge（AlpacaEval 2、Arena-Hard）；Wang et al.（2023b）在统一管线里用 12 个 benchmark 横评 7B/13B 模型，发现没有任何单一指令数据源能在所有评测上最优，数据配比与模型规模比单点方法更能决定上限。

6. **反证已经出现：纯 LLM 合成指令不是充分条件。** Ma et al.（2025）把人类撰写的指令与开源模型的生成响应配对，得到的数据集稳定优于现有纯合成数据集，并在日语上复现了同一结论，提示"人类指令信号"仍是被低估的变量。

## 二、研究范围与方法

检索使用学术检索工具在 ACL Anthology、arXiv 以及 ICLR / NeurIPS / ICML 论文集中执行，并对关键条目回读论文页摘要核对。主要关键词组为：self-instruct、synthetic instruction data、Evol-Instruct、OSS-Instruct、Magpie、instruction tuning small language model、benchmark；中文侧补检"自生成指令 / 指令微调 / 小模型 / 评测"。时间范围 2023 年 1 月至 2026 年 11 月。

纳入标准四条，缺一不可：① 2023 年后正式发表或公开预印本；② 训练数据由模型自生成（Self-Instruct 原范式或其直接变体，如进化指令、代码反推指令、无种子自采样）；③ 训练与评测主体不超过 13B（个别工作含 15B 对照，单独注明）；④ 有 benchmark 数值评测，而不是只做人工或 GPT-4 偏好打分。

排除：只做数据选择或配比而不生成的；只做 RLHF/DPO 对齐的；纯知识蒸馏（教师回答本身不构成指令自举）的；只有主观评测的。最终纳入 10 篇核心文献，另有 6 篇条件不完全满足的边界工作单列在第七节，以便看清"什么不算"。

## 三、文献多维地图

| 主题 | 支持文献数 | 代表文献 | 争议 / 反对 | 研究空白 / 后续价值 |
|---|---:|---|---|---|
| A. 规模与多样性 | 3 篇 | Wang et al.（2023a）；Wu et al.（2024）；Lee et al.（2023） | 放大数据在 0.5B–1.5B 有效，在 10B–40B 反而失效，条件差异未解释清楚 | 0.5B 以下没有任何系统对照，是最低算力场景的明显缺口 |
| B. 指令生成器改造 | 3 篇 | Xu et al.（2024）；Luo et al.（2024）；Cui and Wang（2024） | 进化轮次、生成器自身规模的最优配置没有统一结论 | 生成器要不要微调、能微调到多小，仍是空白 |
| C. 种子源替换 | 2 篇 | Wei et al.（2024）；Xu et al.（2025） | 都依赖强对齐模型或高质量语料，弱模型能否自采样未验证 | 弱对齐与领域模型上的可迁移性值得做 |
| D. 配比与规模边界 | 2 篇 | Wang et al.（2023b）；Lee et al.（2023） | 配比结论随模型族与评测集变化，难以外推 | 缺"同一 base、同一 benchmark、只变生成策略"的受控实验 |
| E. 人类指令必要性 | 1 篇 | Ma et al.（2025） | 只证明效果更优，没有成本侧对照 | 人机混合的最优比例与成本曲线是空白 |

证据主要集中在 7B/13B 的生成器改造以及代码、数学的硬指标评测上；1B 以下的规模轴与通用对话评测明显稀疏，这两处正是最容易做出增量的位置。

## 四、研究视角与本文结构

现有工作可以按"自举链条上被改造的哪一环"分成五类：**数据规模与多样性**（把自举结果放大到百万级并铺开主题）、**指令生成器**（改"谁来生成、怎么进化"）、**种子来源**（改"从哪里起步"）、**数据配比与规模边界**（改"怎么混、在多大模型上还有效"）、**人类指令的必要性**（质疑"纯合成够不够"）。这一分类轴互斥——每类只动链条上的一个环节；同时基本完备——2023 年后这类论文的改动都落在其中一处。第五类不是另一条并行路线，而是对前四类的反向检验，因此放在最后作为反证。下文依此展开。

## 五、核心逻辑图

<whiteboard type="mermaid">
%%{init: {'theme': 'base', 'themeVariables': {
  'fontFamily': 'Inter, Arial, Microsoft YaHei, sans-serif',
  'background': '#FAF9F6',
  'primaryColor': '#E8EEF6',
  'primaryTextColor': '#1F2933',
  'primaryBorderColor': '#2F5D8C',
  'lineColor': '#627D98',
  'secondaryColor': '#E6F0EA',
  'tertiaryColor': '#F4EFE6'
}}}%%
flowchart TD
    Title["self-instruct 系数据训练小模型：三条改造路线与一条反证"]
    Core["2023 年以来，自生成指令数据要怎样改造才能在 1B–13B 小模型上真正换来 benchmark 提升？"]
    Title --> Core
    classDef title fill:#F4EFE6,stroke:#9A7B4F,color:#1F2933,stroke-width:1px
    classDef core fill:#E8EEF6,stroke:#2F5D8C,color:#102A43,stroke-width:1.5px
    classDef theme fill:#E6F0EA,stroke:#3B7C6E,color:#1F2933,stroke-width:1px
    class Title title
    class Core core
    N1[["规模与多样性优先（LaMini-LM） (R1 R2)"]]
    class N1 theme
    N2[["改指令生成器（Evol-Instruct / Ada-Instruct） (R3 R4 R7)"]]
    class N2 theme
    N3[["换种子来源（OSS-Instruct / Magpie） (R5 R6)"]]
    class N3 theme
    N4[["配比与规模边界（Tülu / Ensemble-Instruct） (R8 R9)"]]
    class N4 theme
    N5[["人类指令不可替代（反证） (R10)"]]
    class N5 theme
    Core -->|引出| N1
    Core -->|引出| N2
    Core -->|引出| N3
    Core -->|引出| N4
    Core -->|引出| N5
    N4 -->|限定| N1
    N4 -->|限定| N2
    N1 -->|扩展| N3
    N2 -->|分化| N3
    N3 -->|补充| N2
    N5 -->|反驳| N1
    N5 -->|限定| N3
</whiteboard>

## 六、主题章节

### （一）规模与多样性：把自举数据放大到百万级

*本节文献：Wang et al.（2023a）；Wu et al.（2024）；Lee et al.（2023）*

这一类的共同主张是：小模型缺的不是"更聪明的提示"，而是"足够多、足够杂"的指令。Wang et al.（2023a）建立的原始流水线给出了这个方向的基本形状——175 个手写种子任务，模型自己扩写出新任务、再用模型生成答案，然后过滤掉重复和过短的样本；但它的验证场景是 175B 的同族模型，自举数据的作用被写成"对齐大模型"，而不是"把小模型抬起来"。

真正把这条路线推到小模型上的是 Wu et al.（2024）。他们把数据规模做到 2.58M 条，同时刻意铺开主题覆盖，用 gpt-3.5-turbo 统一生成回答，然后微调 0.5B–1.5B 的 encoder-decoder（T5 系）与 decoder-only 两组模型。与前面那篇的关键差别不只是"数据更多"，而是**把"学生模型规模"当作自变量**：同一批指令喂给不同大小的学生，看能力落在哪。他们的结论是小得多的模型可与强基线相当，且额外做了幻觉与毒性评估——这一点比多数同类工作更完整。

但这条路线有一个被自己暴露出来的边界。Lee et al.（2023）在 10B–40B 的宽松许可模型上复用同一套 175 个种子任务时，发现 Self-Instruct 的表现明显不如在大模型上，原因是大模型才具备足够的 in-context 学习能力去稳定地"照着种子写新任务"；他们的补救办法是简化模板、按"有输入/无输入"拆成两条流水线、并对多个模型的输出做集成筛选。这与 Wu et al.（2024）的"量大管饱"形成有意思的对照：**同样是加数据，一个靠规模与多样性，一个靠把生成环节拆细**，两者对"质量从哪来"的假设并不相同。

| 工作 | 数据规模 | 学生模型规模 | 生成模型 | 评测方式 | 关键结论 |
|---|---|---|---|---|---|
| Wang et al.（2023a） | 52k 自举指令（175 种子） | 175B（同族大模型） | 自身 | Super-NaturalInstructions 等任务集 | 自举数据可对齐大模型，非小模型场景 |
| Wu et al.（2024） | 2.58M（既有 + 新生成） | 0.5B–1.5B | gpt-3.5-turbo | 15 个 NLP benchmark 自动指标 + 人工 | 小模型可与强基线相当 |
| Lee et al.（2023） | 175 种子重写 + 集成筛选 | 10B–40B | 多个开源 LM 集成 | 任务级性能对比 | 原样 Self-Instruct 在此规模失效，需改模板与集成 |

> **小结**：这条路线证明了"小模型 + 大规模自举数据"可行，但可行区间由生成模型的质量决定；把同一套流程平移到中等规模模型，收益会反向。

### （二）改指令生成器：从"多生成"到"生成得更复杂"

*本节文献：Xu et al.（2024）；Luo et al.（2024）；Cui and Wang（2024）*

第二条路线认为瓶颈不在数量，而在**指令的复杂度分布**：种子任务本身是简单的，自举出来的东西也简单，小模型因此学不到多步推理。Evol-Instruct 的做法是不换种子、换"改写规则"——对已有指令做加深（加入约束、增加推理步数、提升复杂度）和拓宽（生成新领域、新形式），把一条简单指令"进化"成难指令，再让模型为难题生成答案。Xu et al.（2024）在 LLaMA-7B/13B 上验证这条路径：模型在 AlpacaEval 这类对抗性偏好评测上明显超过未进化的版本，在 GSM8K 等有标准答案的任务上也有提升，说明"更难"确实转化成了"更会做题"。

Luo et al.（2024）把这套逻辑搬到代码上，用 Code Llama-7B/13B 与 StarCoder-15B 作学生，在 HumanEval、HumanEval+、MBPP、DS-1000 上评测。代码任务的好处是判分客观（跑单元测试），因此这条子路线的证据强度明显高于通用对话：Evol-Instruct 带来的提升可以被 pass@1 直接量出来，而不是靠 judge 打分。

Cui and Wang（2024）则把矛头指向生成器本身。他们发现即便用 GPT-4o，在明确要求下也产不出长度 ≥100 token 的复杂指令，分布上就与真实任务对不上；于是改为**用 10 条样本微调一个开源模型当生成器**，让它学到目标任务的指令长度分布，再用这个生成器去批量造数据。13B 学生在 HumanEval、MBPP、GSM8K、MATH 上的 pass@1/准确率均高于用 Self-Instruct 数据训练的同规模模型，并且在跨任务设置（用 MBPP 指令训练、在 HumanEval 上评测）中同样领先——这一点比单一任务上的提升更能说明"指令分布对齐"是有效机制，而不是过拟合到某个测试集。

| 方法 | 生成器改造方式 | 学生模型 | 硬指标 benchmark | 相对基线 |
|---|---|---|---|---|
| Xu et al.（2024） | 深度/广度进化已有指令 | LLaMA-7B/13B | AlpacaEval、GSM8K 等 | 优于未进化版本与同规模基线 |
| Luo et al.（2024） | 把进化规则迁到代码指令 | Code Llama-7B/13B、StarCoder-15B | HumanEval、HumanEval+、MBPP、DS-1000 | 优于对应基座 |
| Cui and Wang（2024） | 用 10 条样本微调生成器，对齐目标长度分布 | 13B | HumanEval、MBPP、GSM8K、MATH、CommonsenseQA | 优于 Self-Instruct 数据，含跨任务设置 |

> **小结**：改生成器比加数据更省，但代价是必须知道"目标任务的指令长什么样"——这条路线本质上是把领域先验注入生成环节。

### （三）换种子来源：从手写种子到真实语料与模型自身

*本节文献：Wei et al.（2024）；Xu et al.（2025）*

第三条路线换的不是生成规则，而是**起点**。手写 175 个种子任务是一个很弱的前提：它把领域覆盖锁死在作者的个人想象里，也让"自举"从一开始就带着分布偏移。Wei et al.（2024）的做法是从真实开源代码里切出片段，让模型围绕这段代码反推"什么样的需求会写出这段代码"，从而得到一条指令。这样做的好处有两层：指令天然带有真实代码的复杂度与上下文，而且答案可以用执行结果验证，数据质量不依赖生成模型的自我判断。

Xu et al.（2025）把这条路走到极端：干脆不给种子。他们发现对齐好的模型本身已经内化了"用户会怎么提问"的分布，只要喂给它对话模板的开头（chat template 前缀），模型就会自己续写出一条指令；对这些自采样指令做过滤后直接用于微调，8B 级模型在 AlpacaEval 2、Arena-Hard 这类偏好评测上就能达到与更强模型相比的水平。这实际上是对 Self-Instruct 的一次结构性简化：**种子、生成、筛选三步里，第一步被证明可以取消**。

代价也很清楚。OSS-Instruct 依赖一个足够大的真实语料池（代码场景恰好有），Magpie 依赖一个已经对齐好的教师模型；两者都把"小模型能否自举"变成了"小模型能否借到外部资源"。这与路线二形成互补关系：路线二把领域先验写进生成器，路线三把先验写进语料或教师模型。

| 方法 | 种子来源 | 学生模型 | benchmark | 关键结论 |
|---|---|---|---|---|
| Wei et al.（2024） | 真实开源代码片段反推指令 | Code Llama-7B 级 | HumanEval+、MBPP | 优于同等规模代码指令模型 |
| Xu et al.（2025） | 无种子，chat 模板前缀自采样 | 8B 级（Llama-3 系列） | AlpacaEval 2、Arena-Hard 等 | 去掉种子仍可对齐，但依赖强对齐教师 |

> **小结**：种子可以换、甚至可以取消，但"自举"的上限被外部资源锁住；这条路线在小模型上的真实约束是教师模型与语料的可得性，而不是算法。

### （四）配比与规模边界：self-instruct 不是万能数据

*本节文献：Wang et al.（2023b）；Lee et al.（2023）*

前面三条路线都在回答"怎么把自举数据做得更好"，这一条问的是"自举数据到底该占多少"。Wang et al.（2023b）用同一套训练与评测管线横评多种公开指令数据（其中包含 Self-Instruct 风格的合成数据）在 7B/13B/65B 模型上的表现，评测覆盖 12 个 benchmark。他们的核心发现不是"哪种数据最好"，而是**没有任何单一数据源能在所有评测上占优**：不同数据在 MMLU、GSM8K、BBH、代码与多语任务上各有短板，混合之后的整体表现才稳定。这个结论对"用一种自举数据打天下"的论文构成了直接限定。

Lee et al.（2023）从另一个角度给出同向证据：在 10B–40B 区间，原版 Self-Instruct 的数据质量下降并不是靠"再多生成一些"能补回来的，而是要靠模板简化与多模型集成。两条证据合起来说明，**自举数据的效果是条件性的**：它随生成模型能力、学生规模、以及与其他数据的配比而变化，脱离了这三者谈"self-instruct 有效/无效"都没有意义。

| 工作 | 模型规模 | 评测覆盖 | 关键发现 |
|---|---|---|---|
| Wang et al.（2023b） | 7B/13B/65B | 12 个 benchmark | 无单一数据源全能，配比与规模决定上限 |
| Lee et al.（2023） | 10B–40B | 任务级性能 | Self-Instruct 在此规模失效，需改模板 + 集成 |

> **小结**：自举数据是"配方里的一味"，不是配方本身；把它当成唯一数据源，是小模型复现失败最常见的来源。

### （五）反证：人类指令仍然不可替代

*本节文献：Ma et al.（2025）*

最后这一类不是新路线，而是对前四类的反向检验，因此只有一篇，但结论很硬。Ma et al.（2025）把问题问得很直接：只用模型合成的指令，够不够？他们的做法是保留**人类撰写的指令**、只把回答交给开源权重模型生成，用这套"人写指令 + 机写回答"的数据微调，结果稳定优于现有纯合成数据集，并在日语上复现同一结论。

这条证据之所以构成反证，是因为它拆开了通常被混在一起的两个变量：**指令来源**与**回答来源**。路线一与路线三的改进都集中在回答侧与规模侧（更多回答、更好的教师、更真实的语料），却默认指令本身可以从模型里长出来；Ma et al.（2025）说明，一旦把指令换回人类写，即便回答仍由模型生成，数据质量也会上一个台阶。需要说明的是，这一结论目前只在通用指令遵循场景下成立，且论文没有给出成本侧的定量对照，因此它更像"提醒"，还不足以判定合成指令在代码、数学这类有客观判据的任务上也失效。

> **小结**：合成数据的天花板可能不在生成模型，而在"指令从哪来"；这为后续的人机混合研究留出了明确空间。

## 七、争议与开放问题

- **合成 vs 人类指令的真冲突**：Wu et al.（2024）与 Xu et al.（2025）都表明纯合成/自采样数据足以把小模型拉到可用水平，而 Ma et al.（2025）在同一类通用指令任务上得出人类指令更优。条件差异在于任务类型与判分方式：前者覆盖的 15 个 benchmark 与后者的对照实验都包含开放式生成，但 Ma et al.（2025）直接以"换掉指令来源"为干预，控制了回答模型，因此更接近因果比较。目前的倾向是：**在有客观判据的任务（代码、数学）上合成指令够用，在开放对话与文化知识上人类指令仍占优**——这是基于条件差异的推断，尚缺同一实验内的直接对照。

- **规模效应方向不一致**：Wu et al.（2024）在 0.5B–1.5B 上靠放大数据取得与强基线相当的结果，Lee et al.（2023）在 10B–40B 上却报告 Self-Instruct 失效。两者不构成真矛盾，而是分段现象——小模型"从无到有"受益于数据量，中等模型已具备一定的指令理解力，反而对数据质量更敏感；但转折点落在哪个规模区间，没有任何一篇给出定位。

- **开放问题一：0.5B 以下的规模轴是空白。** LaMini-LM 的下限是 0.5B，其余小模型工作基本集中在 7B/13B；0.1B–0.5B 区间既没有 self-instruct 数据的 scaling 证据，也没有与人类指令的对照。这是"最低算力部署"场景最现实的知识缺口。

- **开放问题二：缺受控对比。** 现有论文的 base model、数据量、回答生成模型、评测集各不相同，路线之间谁更优无法回答。至今没有一篇在同一 base、同一 benchmark 上只变"生成策略"的受控实验。

- **开放问题三：评价口径不可复现。** 通用对话路线依赖 AlpacaEval、Arena-Hard 这类 LLM judge，分数随 judge 模型与提示变化；代码/数学路线的 pass@1 稳定，但覆盖窄。两套口径混在同一个"self-instruct 有效"的结论里，是目前最容易被误读的地方。

- **条件不完全满足的边界工作**（列出以免混淆）：Wang et al.（2023a）训练的是 175B 模型，属奠基而非小模型证据；Peng et al.（2023）用 GPT-4 数据微调 LLaMA-7B，但评测以人工与 GPT-4 打分为主，没有标准 benchmark 矩阵；Orca 与 Orca 2（Mukherjee 等，2023；Mitra 等，2023）确实在 7B/13B 上做了 benchmark，但数据是解释轨迹蒸馏而非指令自举；Ivison et al.（2023）的 Tülu 2 加入 DPO 阶段，超出"纯 SFT + 自举数据"的范围；Köksal et al.（2024）的 LongForm 用逆向指令（文档→指令），不属于自举。

## 八、可研究的方向

1. **《0.1B–1B 规模上 self-instruct 数据的 scaling 曲线》**。缺口：LaMini-LM 最低只到 0.5B，且只报 15 个 benchmark 的汇总，0.5B 以下无证据（见第三节表 A 行）。方法思路：固定学生族（如 Qwen2.5-0.5B/1.5B、Pythia-410M/1B）与同一教师模型，只变数据量 1k / 10k / 100k，评 MMLU、IFEval、GSM8K 与 AlpacaEval；需对齐总 token 预算与训练步数，否则规模效应会被训练量混淆。难度：单卡或单机可做。

2. **《同一 base、同一 benchmark 下四种自举改造的受控对比》**。缺口：路线二、三各自有效，但 base 与评测不同，无法回答"改生成器 vs 换种子"谁更划算（见第七节开放问题二）。方法思路：固定 Llama-3-8B 与 Code Llama-7B，各取原版 Self-Instruct、Evol-Instruct、OSS-Instruct、Magpie 四种数据，统一 10k 条、统一回答生成模型与超参，评 HumanEval+、MBPP、GSM8K、IFEval、Arena-Hard；需控制去重率与指令长度分布，否则比较的其实是数据量而不是策略。

3. **《弱对齐模型能否自采样：Magpie 的下限测试》**。缺口：Magpie 的有效性依赖强对齐教师，弱模型与领域模型上的可行性未验证（见第三节表 C 行）。方法思路：取 base 模型、弱 SFT 模型与强对齐模型各一组，用同一 chat 模板前缀采样指令，比较指令多样性、可学习性与下游得分；需控制温度与去重阈值，并报告"采样成功率"这一被忽略的中间指标。

4. **《人机混合指令的最优比例与成本曲线》**。缺口：Ma et al.（2025）证明人类指令更优，但没有给出成本侧对照（见第三节表 E 行）。方法思路：在同一 7B/8B 学生上混合 0 / 10 / 30 / 50 / 100% 人类撰写指令，记录 API 调用成本与 benchmark 得分，画出成本-效果帕累托前沿；需区分"人写指令 + 机写回答"与"人写指令 + 人写回答"两种混合方式，否则成本口径不可比。

5. **《多语种小模型的自举数据可迁移性》**（可探索）。缺口：本次检索到的核心工作以英文为主，中文与日语仅有零散证据（Ma 等，2025 的日语部分）。方法思路：以中英平行指令为种子，比较"直译英文自举数据"与"母语重新自举"在中文 benchmark（C-Eval、CMMLU）上的差距；需控制语料规模与翻译质量，避免把翻译噪声当成方法差异。

## 九、局限性

本次以摘要层阅读为主，仅对 Ada-Instruct 做了部分全文核对，因此具体数字（如 pass@1 的精确值）一律停留在"论文报告"的层面，未做二次复算。核心文献 10 篇，边界工作 6 篇，覆盖的是 2023 年之后在 ACL Anthology、arXiv 与三大机器学习会议可检到的工作；2025 年下半年之后的预印本可能仍有遗漏。中文文献只做了关键词层面的补检，未系统检索知网/万方，因此"中文小模型自举数据"这一支可能被低估。此外，本次未对每篇的完整实验设置做逐项核对，"同一 benchmark 上的可比性"只在口径层面判断，未做数值对齐。

## 十、完整文献综述参考稿

<!-- REVIEW_DRAFT_PLACEHOLDER -->

## 十一、参考文献

1. Wang, Y., Kordi, Y., Mishra, S., Liu, A., Smith, N. A., Khashabi, D., Hajishirzi, H. "SELF-INSTRUCT: Aligning Language Models with Self-Generated Instructions." ACL 2023. [https://aclanthology.org/2023.acl-long.754/](https://aclanthology.org/2023.acl-long.754/)
2. Wu, M., Waheed, A., Zhang, C., Abdul-Mageed, M., Aji, A. F. "LaMini-LM: A Diverse Herd of Distilled Models from Large-Scale Instructions." EACL 2024. [https://aclanthology.org/2024.eacl-long.57/](https://aclanthology.org/2024.eacl-long.57/)
3. Xu, C., Sun, Q., Zheng, K., Geng, X., Zhao, P., Feng, J., Tao, C., Lin, Q., Jiang, D. "WizardLM: Empowering Large Language Models to Follow Complex Instructions." ICLR 2024. [https://arxiv.org/abs/2304.12244](https://arxiv.org/abs/2304.12244)
4. Luo, Z., Xu, C., Zhao, P., Sun, Q., Geng, X., Hu, W., Tao, C., Ma, J., Lin, Q., Jiang, D. "WizardCoder: Empowering Code Large Language Models with Evol-Instruct." ICLR 2024. [https://arxiv.org/abs/2306.08568](https://arxiv.org/abs/2306.08568)
5. Wei, Y., Wang, Z., Liu, J., Ding, Y., Zhang, L. "Magicoder: Empowering Code Generation with OSS-Instruct." ICML 2024. [https://arxiv.org/abs/2312.02120](https://arxiv.org/abs/2312.02120)
6. Xu, Z., Jiang, F., Niu, L., Deng, Y., Poovendran, R., Choi, Y., Lin, B. Y. "Magpie: Alignment Data Synthesis from Scratch by Prompting Aligned LLMs with Nothing." ICLR 2025. [https://proceedings.iclr.cc/paper_files/paper/2025/file/be06e3802e9411381feece79b4d960c1-Paper-Conference.pdf](https://proceedings.iclr.cc/paper_files/paper/2025/file/be06e3802e9411381feece79b4d960c1-Paper-Conference.pdf)
7. Cui, W., Wang, Q. "Ada-Instruct: Adapting Instruction Generators for Complex Reasoning." Findings of EMNLP 2024. [https://aclanthology.org/2024.findings-emnlp.409/](https://aclanthology.org/2024.findings-emnlp.409/)
8. Wang, Y., Ivison, H., Dasigi, P., Hessel, J., Khot, T., Chandu, K. R., Wadden, D., MacMillan, K., Smith, N. A., Beltagy, I., Hajishirzi, H. "How Far Can Camels Go? Exploring the State of Instruction Tuning on Open Resources." NeurIPS 2023 Datasets and Benchmarks. [https://arxiv.org/abs/2306.04751](https://arxiv.org/abs/2306.04751)
9. Lee, Y.-S., Sultan, M. A., El-Kurdi, Y., Naseem, T., Munawar, A., Florian, R., Roukos, S., Astudillo, R. "Ensemble-Instruct: Instruction Tuning Data Generation with a Heterogeneous Mixture of LMs." Findings of EMNLP 2023. [https://aclanthology.org/2023.findings-emnlp.836/](https://aclanthology.org/2023.findings-emnlp.836/)
10. Ma, Y., Mizuki, S., Fujii, K., Nakamura, T., Ohi, M., Shimada, H., Shiotani, T., Saito, K., Maeda, K., Hattori, K., Okamoto, T., Ishida, S., Yokota, R., Takamura, H., Okazaki, N. "Building Instruction-Tuning Datasets from Human-Written Instructions with Open-Weight Large Language Models." COLM 2025. [https://arxiv.org/abs/2503.23714](https://arxiv.org/abs/2503.23714)
11. Mukherjee, S., Mitra, A., Jawahar, G., Agarwal, S., Palangi, H., Awadallah, A. "Orca: Progressive Learning from Complex Explanation Traces of GPT-4." arXiv 2023. [https://arxiv.org/abs/2306.02707](https://arxiv.org/abs/2306.02707)
12. Mitra, A., Del Corro, L., Mahajan, S., Codas, A., Simoes, C., Agarwal, S., Chen, X., Razdaibiedina, A., Jones, E., Aggarwal, K., Palangi, H., Zheng, G., Rosset, C., Khanpour, H., Awadallah, A. "Orca 2: Teaching Small Language Models How to Reason." arXiv 2023. [https://arxiv.org/abs/2311.11045](https://arxiv.org/abs/2311.11045)
13. Peng, B., Li, C., He, P., Galley, M., Gao, J. "Instruction Tuning with GPT-4." arXiv 2023. [https://arxiv.org/abs/2304.03277](https://arxiv.org/abs/2304.03277)
14. Ivison, H., Wang, Y., Pyatkin, V., Lambert, N., Peters, M., Dasigi, P., Jang, J., Wadden, D., Smith, N. A., Beltagy, I., Hajishirzi, H. "Camels in a Changing Climate: Enhancing LM Adaptation with Tülu 2." arXiv 2023. [https://arxiv.org/abs/2311.10702](https://arxiv.org/abs/2311.10702)
15. Köksal, A., Schick, T., Korhonen, A., Schütze, H. "LongForm: Effective Instruction Tuning with Reverse Instructions." Findings of EMNLP 2024. [https://aclanthology.org/2024.findings-emnlp.414/](https://aclanthology.org/2024.findings-emnlp.414/)
