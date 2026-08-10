# doubao-academic-researcher

对一个学术研究话题进行深度文献调研，产出**结构严谨、引用可靠**的专业综述。

## 定位

这是豆包学术技能三件套中的第三个：

```
doubao-academic-evaluator  ← 诊断侧（判断想法 / 审稿）
doubao-academic-polish     ← 产出侧（写论文 / 润色 / 理结构）
doubao-academic-researcher ← 研究侧（检索 → 综合 → evidence-first 的综述）
```

evaluator 和 polish 的工作前提是用户已经有想法或草稿。researcher 解决的是更上游的问题：**用户只有一个话题，需要先搞清楚这个方向的全貌、关键工作、争议和空白**。

## 核心设计理念

### 1. Evidence-First Survey（像真正的 survey paper）

综述的价值不在于罗列文献，而在于给出有判断力的结论。产出的报告是一篇真正的 survey paper：先在引言里定义 2-3 个研究问题（RQ），再用系统检索和分类框架一步步展开证据，最后在结论里逐条回答这些 RQ。

**结论是被证据"赚到"的，不是预告的。** 叙事节奏保持 evidence-first——引言提出问题，正文展开证据，结论回答问题，读者跟着一起推导，而不是先被告知答案再回头找支撑。这个设计防止 confirmation bias 把整条管线带偏。完整骨架见 `references/output-structure.md`。

### 2. 多视角检索（Multi-Perspective Search）

传统检索是"想关键词→搜→窄化"，同一个视角的渐进细化。我们的做法是：**先生成 3-5 个检索视角（主流方/批评方/相邻领域/方法论/政策），每个视角独立搜索，再跨视角合并。**

这保证了文献天然覆盖正反两面和多学科证据。在 5 轮 × 5 学科的测试中，多视角检索比单视角平均多找到 15-20% 的文献，并在跨视角合并时抓住了引用张冠李戴和数字错误。

检索的收敛不靠轮数，也不靠"覆盖够了"的感觉：合并、补盲区、纵深之后，以已入选文献为种子滚雪球（前置工作反查 + extension/critique 式后继检索），**一轮补搜零新增入选才算饱和**，方可收束进综合（见 literature-scout 第五步）。

灵感来自 STORM（Stanford OVAL）的 perspective-guided question asking。

### 3. 交叉对比，不逐篇罗列（Citation Interconnectedness）

学术综述和网页摘要的可量化区别：人写的综述 citation 互联密度 0.14，AI 直出只有 0.02（Shallow Synthesis, arXiv:2402.12255）。差距在于人会在同一句子里比较多篇论文，AI 倾向于逐篇孤立总结。

skill 的操作规则：**每个主题段落至少一个句子同时引用并对比 2+ 篇论文。**

### 4. 反朴素管线（Anti-Naive Pipeline）

朴素做法："读完论文→自由写→事后贴引用"。引用是装饰，和正文松耦合，极易张冠李戴。

正确做法："确定主题→把文献分配到主题→每个主题只从分配的文献里写→写完检查每条 claim 都有出处"。引用和正文是一体的。

灵感来自 DeepSurvey（arXiv:2605.29522）和 Ai2 Scholar QA（arXiv:2504.10861）。

### 5. 引用核验零容忍（Citation Verification）——两层核验

编造引用是整个 skill 的红线。核验分两层，相互独立：

- **条目级**（literature-scout）：每条引用用 `scholar_search` 反查真实性，判定为 5 级之一（VERIFIED / MINOR / MAJOR / UNVERIFIABLE / PAYWALL）。灰区 = 不使用。
- **字段级**（citation-guard）：`scholar_search` 的返回结构不含年份、卷、期、页码、DOI、期刊等级；这些题录字段一旦要被打印，必须经 citation-guard 从 Crossref API / 出版商官方页面解析获取，逐字段三态溯源（已核验 / 二手核验 / 未核验）。**题录字段只允许抄录，不允许生成**——"论文真实存在但 DOI/页码是编的"这类隐蔽失败由此根治。核验声明由台账生成，杜绝"声称全部核实、实际部分推断"的自相矛盾。

在 9 轮测试中，条目级核验拦截了多起引用编造（虚假 arXiv ID、张冠李戴的作者、编造的具体数字）；字段级核验（citation-guard）源于一次外部专家评测发现的题录字段偏差（正确论文 + 错误卷期页码/DOI），经白盒测试定位为"检索工具不返回题录字段 → 模型从记忆补全"的结构性缺口后新增。

灵感来自 ARS（academic-research-skills）的四索引 deterministic verification。

### 6. 7 维内部门禁（Internal Quality Gates）

综合过程中用 7 个维度做内部检查（不对外呈现）：

| 维度 | 检查什么 | 严重度 |
|---|---|---|
| **Angle** | 有判断角度还是只在罗列？ | CRITICAL |
| **Coverage** | 关键工作都覆盖了吗？ | MAJOR |
| **Citation** | 引用真实、引述准确？ | CRITICAL |
| **Taxonomy** | 按主题组织？MECE？ | MAJOR |
| **Calibration** | 判断强度 ≤ 证据强度？ | MAJOR |
| **Weaving** | 句内交叉对比？ | MAJOR |
| **Insight** | 结论达到裁决级？有读遍摘要也得不到的东西？ | MAJOR |

CRITICAL 维度不通过 → 停下修复。MAJOR 维度按性质路由：Coverage / Citation 回 literature-scout 补检索，其余（Taxonomy / Calibration / Weaving / Insight）在 research-synthesis 原地修复（详见 SKILL.md 的门禁路由表）。

### 7. 洞见协议（Insight Protocol）——综合环节的深度地板

覆盖式汇总不是综述。v5.0 起，综合环节受洞见协议约束：**结论阶梯 L0–L4** 给每条结论定楼层（复述/聚合不配进结论位，结论位每条 ≥ L2 裁决级，全文 ≥3 条机制解释、≥1 条可检验假设——规格化的证据缺口计入楼层）；写作前以怀疑者/方法论者/实践者三视角生成**深问题**作为讨论组织轴；硬矛盾必须走完**分歧裁决程序**（有条件立场 / 证据缺口 / 真实分歧，三选一，禁止"见仁见智"收尾）；成稿后做**洞见反思**——列出"读遍全部摘要也得不到的东西"，不足则重写。全部机制零检索成本，两种任务模式通用。

灵感来自 STORM 的视角化提问、OmniThink（EMNLP 2025，消融证明反思环节对新颖性贡献最大）与 DataSTORM 的论题发现—裁决—叙事链。

## 管线流程

整条管线由**同一个执行者按门禁结果驱动**——串行推进各阶段、在门禁不通过时回调对应阶段重做，使 scout→synthesis→检查→再 scout 的迭代得以持续进行，而非一次性线性走完。

```
用户提出研究话题
       ↓
Step 0: 意图澄清 → 冻结研究简报
       ↓
（执行者依次进入以下阶段，并按门禁结果回调迭代）
       ↓
┌─────────────────────────────────────┐
│  阶段一: literature-scout           │
│  生成 3-5 个检索视角                  │
│  → 每个视角独立搜索（宽→窄）          │
│  → 跨视角合并 + 补盲区               │
│  → 纵深 → 滚雪球至饱和（零新增收敛） │
│  → 引用核验（5 级判定）              │
│  → 产出: 经核验的文献清单             │
└─────────────────────────────────────┘
       ↓ （题录严格模式经此环节；综述模式直达阶段二——判据见 SKILL.md“任务模式分流”）
┌─────────────────────────────────────┐
│  题录核验: citation-guard            │
│  对最终入选文献逐篇解析题录            │
│  → Crossref API → 官方页面 → 未核验   │
│  → 字段级三态溯源 + 核验台账          │
│  → 核验声明由台账生成                 │
└─────────────────────────────────────┘
       ↓
┌─────────────────────────────────────┐
│  阶段二: research-synthesis          │
│  引文抽取 → 主题聚类（MECE）          │
│  → 逐节串行合成（Related Work 骨架）  │
│  → 交叉对比 + 矛盾呈现               │
│  → 自对抗审查（3 回溯问题）           │
│  → 7 维门禁检查                      │
│  → 产出: 结构化综合分析               │
└─────────────────────────────────────┘
       ↓
呈现阶段: evidence-first 叙事（引言提问 → 正文展开证据 → 结论回答 RQ）
       ↓
最终报告（survey paper 结构：摘要 + 引言/RQ + 研究方法 + 分类框架 + 各分支 + 综合讨论 + 开放问题 + 结论 + 参考文献）
```

## 输出报告结构

像一篇真正的 survey paper，主体章节连续编号，结论置末逐条回答引言的 RQ（完整骨架与写法纪律见 `references/output-structure.md`）：

```
# [研究话题]：[角度/核心判断]

## 摘要
[整篇综述的压缩版，给方向感，不剧透所有结论]

## 一、引言
[为什么需要这篇综述 + 研究问题（RQ）+ 本文组织方式]

## 二、研究方法
[检索策略 + 证据类型说明（非 CS 领域）]

## 三、分类框架
[MECE 分类]

## 四、[分支一]   ## 五、[分支二]   ## 六、[分支三]
[散文 + 对比表，表题含结论]

## 七、综合讨论
## 八、开放问题与未来方向
## 九、结论
[逐条回答引言里的 RQ——整篇综述的闭环]

## 参考文献
```

## 文件结构

```
doubao-academic-researcher/
├── README.md                                          # 本文件
├── CHANGELOG.md                                       # 版本演化记录（失败驱动）
├── SKILL.md                                     # 主编排器
├── scripts/
│   └── check_report.py                                #   交付前 lint（黑名单/引用编号/声明清点，agent 模式安全网）
│
├── sub-skills/
│   ├── literature-scout/                        # 阶段一：检索 + 存在性核验
│   │   ├── SKILL.md                                   #   多视角检索 + 5 级核验
│   │   └── references/
│   │       ├── search-strategy.md                     #   关键词构造 + 学科调整
│   │       └── citation-protocol.md                   #   核验协议 + 灰区原则 + 字段级三态
│   │
│   ├── citation-guard/                          # 题录核验：字段级溯源
│   │   ├── SKILL.md                                   #   双红线 + 三通道瀑布 + 循环与闸门
│   │   ├── scripts/
│   │   │   └── verify_citations.py                    #   Crossref 通道的确定性脚本实现
│   │   └── references/
│   │       ├── crossref-playbook.md                   #   Crossref API 端点/字段映射/误匹配防御
│   │       └── ledger-and-statements.md               #   台账格式 + 分级声明模板
│   │
│   └── research-synthesis/                     # 阶段二：综合 + 审查
│       ├── SKILL.md                                   #   三步法 + Related Work 骨架
│       └── references/
│           ├── synthesis-framework.md                 #   交叉对比 + 对比表 + 矛盾呈现
│           ├── insight-protocol.md                    #   结论阶梯 L0–L4 + 深问题 + 分歧裁决 + 洞见反思
│           ├── quality-gates.md                       #   7 维门禁详细规则
│           └── self-adversarial.md                    #   3 回溯问题 + 视角检查
│
└── references/                                  # 共享
    ├── output-structure.md                            #   报告骨架 + 格式纪律
    └── hedge-calibration.md                           #   措辞阶梯（claim ≤ evidence）
```

## 跨学科证据标准

不同学科用不同的证据标准：

- **CS/AI**：基准测试、消融、可复现性
- **生物医学**：临床试验阶段、患者数、随访时长
- **社会科学**：区分相关与因果，标注效应量
- **经济学**：识别策略（IV/DID/RDD），区分统计显著与经济显著
- **跨学科**：区分模型预测、观测归因、田野实验

非 CS 领域的报告必须包含**证据类型说明表**，帮读者区分不同类型证据的可信度。

## 测试验证

v1–v5 全程失败驱动迭代（完整根因与修补记录见 `CHANGELOG.md`），累计 30+ 次独立测试与验收回放（CS/生物医学/社科/经济学/跨学科），验证了：

- 格式一致性（章节编号、小结、参考文献格式）
- 引用核验有效性（拦截编造引用、修正数字错误）
- 题录字段级核验（脚本化 Crossref 核验 + 台账 + 分级声明；v2–v4.5 经多轮验收回放打磨，含网络层故障的混合模式对策）
- 任务模式分流（严格模式的核验机器不污染普通综述任务，v4.2）
- 多视角检索价值（比单视角多 15-20% 文献覆盖）
- 跨学科适应性（不同学科自动切换证据标准）
- 交叉对比密度（每个主题段落有句内多引对比）
- 洞见协议（结论阶梯/深问题/分歧裁决，v5.0 新增；已跑一轮无回归信号，行为级验收进行中）

## 致谢

本技能的设计参考了以下开源项目和学术工作：

- [STORM](https://github.com/stanford-oval/storm)（Stanford OVAL）— 多视角检索、perspective-guided question asking
- [academic-research-skills](https://github.com/Imbad0202/academic-research-skills)（ARS）— 引用核验协议
- [Ai2 Scholar QA](https://arxiv.org/abs/2504.10861) — 证据综合三步法
- [Shallow Synthesis](https://arxiv.org/abs/2402.12255) — citation interconnectedness 指标
- OmniThink（EMNLP 2025）— 洞见反思机制（消融证明反思对新颖性贡献最大）
- Co-STORM / DataSTORM — 深问题与"论题发现 → 跨源验证 → 分析叙事"的组织轴
- [AutoSurvey](https://github.com/AutoSurveys/AutoSurvey) / [SurveyForge](https://github.com/InternScience/SurveyForge) — 综述生成架构
- [auto_research](https://victorchen96.github.io/auto_research/) — weakness routing 设计
- [HKUSTDial/Supervisor-Skills](https://github.com/HKUSTDial/Supervisor-Skills)— 姊妹技能来源
