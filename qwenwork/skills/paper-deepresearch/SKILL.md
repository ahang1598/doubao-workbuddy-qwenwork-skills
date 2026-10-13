---
name: paper-deepresearch
description: 面向学术论文的**原文级调研（Deep Research）**能力模块。适用于：用户指定某篇论文要求"读透 + 追踪背景 + 扩展最新相关工作"，或用户给出某个学术 topic 要求系统性深度调研与写作综述。
install_source: official
install_method: download
skill_id: official_KDwpsYfJ
enabled_at: 1791893761439
version: 1.0.0
name_zh: 学术论文深度研究
---
# SKILL: paper-deepresearch

面向学术论文的**原文级调研（Deep Research）**能力模块。适用于：用户指定某篇论文要求"读透 + 追踪背景 + 扩展最新相关工作"，或用户给出某个学术 topic 要求系统性深度调研与写作综述。

---

## 1) Overview

### ⚠️ 输出形式（强制）
- **本 skill 被触发即代表用户期望生成钉钉在线文档**，主 Agent 无需询问用户是否需要写成文档，也不得以对话文本替代文档作为最终交付物。
- 数据收集完成后，必须通过 `task`（subagent_type: writer）委托 Writer Agent 创建钉钉在线文档。

### 钉钉工具优先（必须遵守）
- 所有钉钉相关信息获取与写作，先参考 `dws` 并按其指引调用对应技能
- 需要访问钉钉文档/群消息/会议/任务时，直接通过 `dws` 对应子命令调用

### 工具/Skill 明确清单（直接使用 dws 命令）

必须先参考 `dws` 并调用对应技能。

| 工具 | 用途 | 适用场景 |
|------|------|---------|
| `WebSearch` | 广泛检索公开学术信息 | 论文定位、arXiv/出版社搜索、会议论文检索、引用链追踪 |
| `fetch` | 获取特定网页/文档全文 | 论文原文 PDF 下载、作者主页、出版社页面、Semantic Scholar |
| `pdf-parser` | 解析 PDF 文档 | 论文 PDF 全文解析、公式/图表/定理提取 |
| `knowledge` | 检索内部知识库 | 内部已有的论文分析、技术调研、相关项目资料 |
| `file` | 写入素材文件（append 模式） | 将调研素材、结构化笔记写入 draft.md |
| `task` | 分发子任务给 Writer Agent | 完成素材收集后调用，生成钉钉在线文档 |
| `file_read` | 读取文件内容 | Writer Agent 读取 draft.md（Writer Agent 使用） |
| `outline_generator` | 生成结构化大纲 | Writer Agent 生成报告大纲（Writer Agent 使用） |
| `dws doc create` | 生成钉钉在线文档 | Writer Agent 最终输出（Writer Agent 使用） |
| `end` | 结束任务 | Writer Agent 完成后返回文档链接 |
| `dws todo` | 创建后续研究待办任务 | 报告生成后（可选） |
| `dws ding` | 通知相关人员 | 报告生成后（可选） |

### 草稿文件路径规范（动态化，避免并发冲突）
- 草稿文件路径格式：`/home/workspace/draft_{任务标识}_{YYYYMMDD_HHMMSS}.md`
- 例如：`/home/workspace/draft_年度报告_20260415_161500.md`
- 任务开始时确定路径，全程使用同一路径，任务结束后可选择清理

### 证据与时间约束（与主/写作agent一致）
- 任何数据/结论必须来自可追溯来源；不确定则明确标注"需补充资料"。
- 若用户指定时间范围，必须严格筛选在时间窗内的资料，过期内容不得使用。
- 不可编造事实、链接或来源；引用必须有明确出处。
- 学术论文引用必须包含：作者、标题、会议/期刊、年份、DOI/arXiv ID。

### 可读性规则（强制）
- 并列项>=3：优先使用无序/有序列表或表格
- 单段>150字必须拆分（列表/小节/Callout）
- 连续两段无列表且信息密度高：插入列表或 Callout
- 公式必须使用 LaTeX 格式，行内公式用 `\(...\)`，独立公式用 `\[...\]`

### 目标
- **原文驱动**：必须定位到论文**原文 PDF**（arXiv/出版社/作者主页等）并通读，基于原文进行理解、复述、推导与批判性分析。
- **topic 拉通**：从 topic 的问题定义与主流范式切入，连接到用户指定论文（primary paper），再扩展到**近期相关论文（recent related works）**，形成"背景 → 主文献 → 近作 → 关系论证 → 结论与空白"的闭环。
- **技术深度**：写作中要善于使用公式、符号、命题/定理结构，而不是浅层"摘要式总结"。

### 触发方式（Triggers）
当用户出现以下意图时触发本 skill：
- "帮我调研/精读这篇论文：<标题/DOI/arXiv/链接>"
- "给我对 <topic> 做 deep research / 系统性调研 / 最新进展梳理"
- "把这篇论文放到该领域脉络里，找最近相关论文并对比"
- "我需要推导/理解论文里的公式、定理、对偶、复杂度、实验设计"

### 输入（Inputs）
- **必选其一**：`paper_identifier`（标题/DOI/arXivID/URL/PDF）或 `topic`（关键词 + 子方向约束）
- **可选**：
  - 时间窗口（例如近 2 年/3 年）
  - 目标会议/期刊
  - 方法偏好（理论/实验/应用）
  - 关注点（例如"对偶推导""泛化界""算法复杂度""实现细节"）

### 输出（Outputs）
- **钉钉在线文档论文深度解读报告**，包含：
  - Topic 背景与问题定义（含统一符号与公式）
  - Primary paper 深度解构（模型/定理/算法/实验）
  - Recent papers（原文级阅读后的归类、对比与关系论证）
  - 关键公式与推导路线（必要时给出 proof sketch）
  - 局限性、开放问题、可复现建议、下一步研究线索
- 可选附录：`BibTeX` 条目集合、对比表、术语表、符号表

---

## 2) 论文检索与证据构建（主 Agent 执行）

> 核心原则：**只要是"调研论文"，就必须拿到原文并阅读**；只要是"找相关论文"，就必须对每篇候选至少拿到原文并做结构化阅读记录。

### 2.1 Primary paper：定位原文 + 版本确认

1. **定位权威原文来源（按优先级）**
   - arXiv（preprint PDF）
   - 出版社页面（最终版本 / camera-ready）
   - 作者主页 / institutional repository
   - 语义学术索引（如 Semantic Scholar）用于交叉验证元数据与引用链

**WebSearch 查询示例**：
```
- "{论文标题} arxiv PDF"
- "{论文标题} {作者} {年份} conference"
- "DOI:{DOI编号}"
- "{arXivID} paper"
```

**fetch 获取原文**：
```
fetch(
  url: "https://arxiv.org/abs/XXXX.XXXXX",
  prompt: "获取该论文的完整元数据：标题、作者、摘要、版本号、提交日期、DOI"
)
```

2. **版本一致性检查**
   - 核对：标题、作者、年份、会议/期刊、版本号（arXiv v1/v2...）、DOI
   - 若存在多个版本：明确"以哪一版为主"，并记录差异（新增定理/实验/修订假设）

3. **原文获取失败的降级策略**
   - 若出版社付费墙：尝试 arXiv / 作者公开稿 / accepted version
   - 仍不可得：请求用户上传 PDF（此时停止"深度推导"，改做"可得信息范围内"的有限分析）

**写入 draft.md**（使用 `file(path: "/home/workspace/draft_{任务标识}_{YYYYMMDD_HHMMSS}.md", mode: "append")`）：
```markdown
## Primary Paper 元数据

- **标题**：...
- **作者**：...
- **会议/期刊**：...（年份）
- **arXiv ID**：...（版本 vX）
- **DOI**：...
- **原文来源**：arXiv / 出版社 / 作者主页
- **版本说明**：以 vX 为主，与 camera-ready 差异为...
```

### 2.2 Primary paper：通读与结构化笔记（必须）

对整篇原文做**结构化拆解**，每一项都要能回指到章节/公式编号（证据化）：

- **Problem Setup & Notation**
  - 随机变量/数据分布/样本：\(\xi \sim \mathbb{P}\)，\(\{\xi_i\}_{i=1}^n\)
  - 决策变量：\(x \in \mathcal{X}\)
  - 目标与风险/约束：\(\min_{x \in \mathcal{X}} \mathbb{E}_{\mathbb{P}}[\ell(x;\xi)]\)，或 \(\min f(x)\ \text{s.t.}\ g(x)\le 0\)
- **核心方法/算法**
  - 写出关键优化形式（primal/dual/regularized）
  - 给出算法迭代（如 SGD/PDHG/ADMM/镜像下降）的一般式
- **理论结果**
  - 定理/命题：条件（assumptions）→ 结论（rates/bounds/consistency）
  - 必须明确：依赖常数、光滑性/Lipschitz、强凸性、维度依赖、样本量依赖
- **实验与评估**
  - 数据集、指标、baselines、消融、统计显著性、复杂度与 wall-clock
- **局限性与讨论**
  - 论文自述限制 + 你识别到的隐含限制（假设过强、不可扩展、证据不足等）

> 输出一个"Primary paper evidence table"：Claim → Location（Section/Equation/Theorem）→ Notes（你对其含义/边界的解释）。

**使用 `pdf-parser` 解析论文 PDF**，提取公式、定理、实验表格等关键内容。

**写入 draft.md**（使用 `file(path: "/home/workspace/draft_{任务标识}_{YYYYMMDD_HHMMSS}.md", mode: "append")`）：
```markdown
## Primary Paper 结构化笔记

### Problem Setup & Notation
- 问题设定：...（Section X）
- 核心符号：...
- 目标函数：\(\min_{x \in \mathcal{X}} \mathbb{E}_{\mathbb{P}}[\ell(x;\xi)]\)（Eq. X）

### 核心方法/算法
- 关键优化形式：...（Section X）
- 算法迭代式：...（Algorithm X）

### 理论结果
- Theorem X：在假设 A1-A3 下，...（Section X）
- 收敛率：...
- 依赖条件：...

### 实验与评估
- 数据集：...
- 指标：...
- 主要结果：...（Table X / Figure X）

### 局限性与讨论
- 论文自述：...
- 识别到的隐含限制：...

### Evidence Table
| Claim | Location | Notes |
|-------|----------|-------|
| ... | Section X, Eq. Y | ... |
| ... | Theorem Z | ... |
```

### 2.3 Topic background：从"定义 → 范式 → 经典工作"建立脉络

当用户调研的是"论文"也要做 topic 背景（因为需要解释它解决的是什么问题）：

1. 统一定义：写出该 topic 的标准数学表述（至少 1--2 个 canonical forms）
2. 识别主流范式：优化/统计/学习/因果/控制等
3. 定位 3--8 篇奠基/综述/教材级引用，作为"背景锚点"
4. 提取该领域的常见难点与评价标准（例如：泛化、稳健性、可扩展性、可解释性、可复现性）

**WebSearch 查询示例**：
```
- "{topic} survey review tutorial"
- "{topic} canonical formulation mathematical framework"
- "{topic} seminal paper foundational work"
- "{topic} benchmark evaluation metrics"
```

**写入 draft.md**（使用 `file(path: "/home/workspace/draft_{任务标识}_{YYYYMMDD_HHMMSS}.md", mode: "append")`）：
```markdown
## Topic Background

### 问题定义
- Canonical form 1：...
- Canonical form 2：...

### 主流范式
- ...

### 奠基工作（背景锚点）
| 论文 | 年份 | 核心贡献 | 与 primary paper 关系 |
|------|------|---------|---------------------|
| ... | ... | ... | ... |

### 领域难点与评价标准
- 泛化：...
- 稳健性：...
- 可扩展性：...
```

### 2.4 Recent related works：搜索"同 topic 最新论文"并原文阅读（必须）

> 用户要求：对**原文同个 topic 最近的相关论文**进行搜索原文并阅读整篇原文。

1. **检索范围建议**
   - 默认：近 24--36 个月（可按用户指定）
   - 目标：5--15 篇"强相关 + 有代表性"论文（宁缺毋滥）

2. **检索策略（组合拳）**
   - 关键词扩展：同义词、缩写、核心术语 + 方法名
   - 会议/期刊定向：该领域顶会顶刊（按 topic 确定）
   - 引用追踪：
     - backward：primary paper 引用的关键前置工作
     - forward：引用 primary paper 的近期论文（尤其最新）
   - 相关性判别：是否共享同一核心建模对象/理论命题/实验设置

**WebSearch 查询示例**：
```
- "{topic} {关键方法} 2024 2025 paper"
- "{primary paper 标题} cited by recent"
- "{topic} {顶会名} 2024 2025"
- "{核心术语} {同义词} new approach"
```

3. **对每篇 recent paper 的"最小原文阅读"标准**
   - 必须下载 PDF 并读：Abstract + Intro + Method + Main Theorem/Key Lemma + Experiments + Limitations/Discussion
   - 输出结构化卡片：
     - Problem / Method / Key result（公式级）/ Empirical setup / Relation to primary paper（替代、改进、互补、否定）

**写入 draft.md**（使用 `file(path: "/home/workspace/draft_{任务标识}_{YYYYMMDD_HHMMSS}.md", mode: "append")`）：
```markdown
## Recent Related Works

### 检索策略与范围
- 时间窗口：近 XX 个月
- 检索渠道：arXiv, {顶会}, Semantic Scholar, Google Scholar
- 候选论文数：XX 篇，筛选后：XX 篇

### 结构化卡片

#### Paper R1：{标题}（{作者}, {年份}）
- **Problem**：...
- **Method**：...
- **Key result**：...（公式级）
- **Empirical setup**：...
- **Relation to primary paper**：替代/改进/互补/否定 — 具体说明...

#### Paper R2：{标题}（{作者}, {年份}）
- ...
```

### 2.5 质量控制（Search QA）

- 不允许只读二手解读（博客/短评）就下结论
- 对关键结论必须双重核对：原文公式/定理 + 实验设置
- 若出现矛盾（不同论文结论冲突）：记录冲突点（假设不同？数据不同？指标不同？实现差异？）

---

## 3) 写作规范与论证要求

> 写作总路线（用户要求）：**从 topic 入手 → 介绍 primary paper → 引到 recent papers → 论证关系**。

### 3.1 推荐报告结构（强制层次）

#### 0. TL;DR（不超过 10 行）
- 1--2 句 topic 定义 + 1 句 primary paper 的核心贡献 + 1--3 句近期进展与差异 + 1 句开放问题

#### 1. Topic：问题定义与统一符号（公式优先）
- 给出 canonical objective（示例）：
  \[
  \min_{x\in\mathcal X}\ \mathbb{E}_{\mathbb P}\big[\ell(x;\xi)\big]
  \quad\text{或}\quad
  \min_{x\in\mathcal X}\ f(x)\ \text{s.t.}\ g(x)\le 0
  \]
- 若为稳健/分布鲁棒/正则等主题，写出标准形式（示例）：
  \[
  \min_{x\in\mathcal X}\ \sup_{\mathbb Q\in\mathcal U}\ \mathbb E_{\mathbb Q}[\ell(x;\xi)]
  \]
- 明确：
  - \(\xi\) 的含义、样本如何来、\(\mathcal X\) 的结构
  - 常用假设（Lipschitz/convex/smooth/bounded support...）与其作用

#### 2. Primary paper 深度解构（以"模型--方法--定理--算法--实验"组织）
- **2.1 模型与关键构件**：把论文最核心的 1--3 个公式抄成统一符号体系，并解释每一项的作用
- **2.2 方法与推导主线**：给出从原问题到可解形式的"推导路线图"
  - 例如：primal → dual → regularization → tractable reformulation
- **2.3 理论结果（定理化呈现）**
  - 用"Assumption → Theorem → Interpretation"写法
  - 给出 proof sketch（只抓关键不等式/关键技巧），必要时写：
    \[
    \text{(key inequality)}\quad A \le B + C
    \]
- **2.4 算法细节**
  - 写出迭代更新式与复杂度（示例）：
    \[
    x^{t+1} = \Pi_{\mathcal X}\Big(x^t - \eta_t \nabla \hat f(x^t)\Big)
    \]
- **2.5 实验与结论可信度**
  - baseline 是否合理？指标是否匹配主张？是否有消融与统计检验？

#### 3. Recent related works：归类--对比--关系论证（必须体现"最近"）
- **3.1 归类框架（先给 taxonomy）**
  - 例：A 类（理论强化）、B 类（算法加速/可扩展）、C 类（放松假设/更一般场景）、D 类（应用/系统化）
- **3.2 对比表（强制）**
  - 维度建议：目标/假设/关键公式或界/算法复杂度/实验设置/相对 primary paper 的关系
- **3.3 关系论证（不是罗列）**
  - 用明确语义连接：
    - "该工作在 primary 的 Assumption X 上做了放松..."
    - "该工作把 primary 的目标 \(\ell\) 替换为 \(\tilde \ell\)，得到更强/更弱的界..."
    - "该工作在同一 benchmark 上显示...，但其优势来自...（更强的模型容量/更大的算力预算/不同预处理）"

#### 4. 综合结论与开放问题（研究导向）
- 你认为"已解决/基本共识"的部分是什么？
- 哪些是"理论空白/实验不足/工程不可落地"的部分？
- 给出 3--6 条明确可执行的后续研究问题（尽量写成数学问题或可验证命题）

#### 5. 附录（可选但推荐）
- 符号表（Notation table）
- BibTeX 列表
- 复现清单（数据、代码、超参、随机种子、算力、环境）

### 3.2 公式化写作规范（必须遵守）
- 每次引入符号必须定义（第一次出现就定义）
- 每个"关键结论"尽量落到可检查的对象：公式编号/定理编号/实验表格
- 避免空泛形容词（"很有效""很先进"），改为可验证表述（"在设置 S 下，相比 baseline 提升 X%/界从 \(O(1/\sqrt n)\) 改为 \(O(1/n)\)"）

### 3.3 深度标准（反浅层检查）
若报告缺少以下任一项，则视为"浅层"，需要补齐：
- 至少 3 个关键公式（topic/primary/method 或 theorem）
- 至少 1 个推导路线（哪怕是 proof sketch）
- 至少 1 张系统对比表（primary vs recent）
- 至少 3 条"关系论证句"（说明为什么相关、改进在哪里、代价是什么）

---

## 4) 报告生成（Writer Agent）

### 任务分发

主 Agent 完成素材收集和分析后，调用 `task` 工具分发给 writer agent：

```json
{
  "description": "生成前沿论文解读钉钉在线文档",
  "prompt": "基于 /home/workspace/draft_{任务标识}_{YYYYMMDD_HHMMSS}.md 中的论文调研素材，生成一份结构完整的钉钉在线文档论文深度解读报告。\n\n要求：\n1. 严格按照报告结构：TL;DR → Topic 问题定义 → Primary paper 深度解构 → Recent works 归类对比 → 综合结论与开放问题\n2. 关键公式使用 LaTeX 格式，行内公式用 \\(...\\)，独立公式用 \\[...\\]\n3. 对比表必须包含，维度统一：目标/假设/关键公式或界/算法复杂度/实验设置/相对 primary paper 的关系\n4. 所有引用标注来源（作者, 标题, 会议/期刊, 年份）\n5. 定理化呈现理论结果：Assumption → Theorem → Interpretation\n6. 报告篇幅：标准版 15-30 页\n\n报告模板见下方。",
  "subagent_type": "writer"
}
```

### Writer Agent 执行流程

Writer Agent 收到任务后，按以下步骤执行：

1. **file_read**：读取 `/home/workspace/draft_{任务标识}_{YYYYMMDD_HHMMSS}.md`，获取主 Agent 整理的全部论文调研素材
   - 包括：Primary paper 结构化笔记、Topic background、Recent works 结构化卡片、Evidence table
2. **outline_generator**：基于素材和论文解读报告模板，生成结构化大纲
   - 大纲必须覆盖 3.1 中所有强制层次（TL;DR → Topic → Primary → Recent → Conclusion）
   - 每个章节标注预估字数
   - 确认公式数量、对比表数量、定理数量
3. **dws doc create**：根据大纲逐章生成钉钉在线文档内容
   - LaTeX 公式使用钉钉文档支持的公式格式
   - 对比表使用钉钉文档原生表格
   - 插入 Callout 突出核心定理与关键结论
   - 推导路线使用有序步骤呈现
4. **end**：返回钉钉在线文档链接，任务结束

### 后续研究任务创建

报告生成后，主 Agent 根据"综合结论与开放问题"章节中的后续研究问题，询问用户是否创建钉钉待办任务。

**工具**：`dws todo`

**调用策略**：
1. 从报告中提取"后续研究问题"列表（3-6 条）
2. 将每条问题转化为可操作的待办任务
3. 询问用户确认任务列表后再创建

**调用示例**：
```
主 Agent 询问用户:
"报告中识别了以下后续研究方向，是否需要创建待办任务？
1. 调研开放问题1：{具体问题描述}
2. 复现 primary paper 实验
3. 精读 Paper R2 的方法细节"

用户确认后:
dws todo: 创建待办
- 任务1: "调研：{开放问题1}" — 截止: 2周后
- 任务2: "复现 primary paper 实验" — 截止: 1周后
- 任务3: "精读 Paper R2 方法细节" — 截止: 3天后
```

**注意**：
- 仅在报告包含明确的后续研究问题时创建
- 创建前必须询问用户确认任务列表
- 用户可调整任务内容、负责人和截止时间

### 文档通知（可选）

报告生成完成后，主 Agent 询问用户：

> "论文深度解读报告已生成，是否需要通过 DING 消息通知相关人员？"

**用户确认后执行**：
```
dws ding: 发送通知
- 接收人: {用户指定的接收人}
- 内容: "【论文解读】{论文标题/Topic} 深度解读报告已生成，请查阅：{文档链接}"
```

**注意**：
- 必须等待用户确认后才能发送，不可自动发送
- 接收人需用户指定
- 用户可修改接收人列表后再发送

---

## 5) 文档模板（Writer Agent 遵循）

```markdown
# {论文标题 / Topic} 深度解读报告

> 调研范围：{topic 关键词} | 时间窗口：近 {N} 个月
> Primary paper：{标题}（{作者}, {会议/期刊}, {年份}）
> 生成时间：YYYY-MM-DD

---

## TL;DR

{1–2 句 topic 定义}。{1 句 primary paper 的核心贡献}。{1–3 句近期进展与差异}。{1 句开放问题}。

---

## 1. Topic：问题定义与统一符号

### 1.1 问题定义
- Canonical objective：
  \[
  \min_{x\in\mathcal X}\ \mathbb{E}_{\mathbb P}\big[\ell(x;\xi)\big]
  \]
- 符号说明：\(\xi\) 表示...，\(\mathcal X\) 表示...，\(\ell\) 表示...

### 1.2 主流范式与假设
- 范式 A：...
- 范式 B：...
- 常用假设：Lipschitz / convex / smooth / bounded support...

### 1.3 奠基工作（背景锚点）

| 论文 | 年份 | 核心贡献 |
|------|------|---------|
| {经典工作1} | YYYY | ... |
| {经典工作2} | YYYY | ... |
| {经典工作3} | YYYY | ... |

---

## 2. Primary Paper 深度解构

### 2.1 模型与关键构件
- 核心公式 1：（Eq. X）
  \[
  ...
  \]
  解释：每一项的作用...

### 2.2 方法与推导主线
- 推导路线图：primal → dual → regularization → tractable reformulation
- 关键步骤说明：...

### 2.3 理论结果
> **Assumption A1**：...
> **Theorem 1**（{论文} Theorem X）：在 A1–A3 下，...
> **Interpretation**：该定理表明...

- Proof sketch：
  1. ...
  2. Key inequality：\(A \le B + C\)
  3. ...

### 2.4 算法细节
- 迭代更新式：
  \[
  x^{t+1} = \Pi_{\mathcal X}\Big(x^t - \eta_t \nabla \hat f(x^t)\Big)
  \]
- 复杂度：\(O(...)\)

### 2.5 实验与结论可信度

| 维度 | 评估 |
|------|------|
| Baseline 合理性 | ... |
| 指标匹配度 | ... |
| 消融实验 | 有/无 |
| 统计检验 | 有/无 |

- 主要实验结论：...

---

## 3. Recent Related Works

### 3.1 归类框架（Taxonomy）
- A 类（理论强化）：...
- B 类（算法加速/可扩展）：...
- C 类（放松假设/更一般场景）：...
- D 类（应用/系统化）：...

### 3.2 系统对比表

| 论文 | 类别 | 目标/假设 | 关键公式或界 | 算法复杂度 | 实验设置 | 相对 Primary 的关系 |
|------|------|---------|-------------|-----------|---------|-------------------|
| Paper R1 | A | ... | ... | ... | ... | 改进了假设 X |
| Paper R2 | B | ... | ... | ... | ... | 加速了算法至... |
| Paper R3 | C | ... | ... | ... | ... | 放松了条件... |
| ... | ... | ... | ... | ... | ... | ... |

### 3.3 关系论证
- Paper R1 vs Primary：...
- Paper R2 vs Primary：...
- Paper R3 vs Primary：...

---

## 4. 综合结论与开放问题

### 已解决/基本共识
- ...

### 理论空白/实验不足/工程不可落地
- ...

### 后续研究问题（3–6 条）
1. （数学问题/可验证命题）...
2. ...
3. ...

---

## 附录

### A. 符号表（Notation Table）

| 符号 | 含义 |
|------|------|
| \(\xi\) | ... |
| \(x\) | ... |
| \(\mathcal X\) | ... |

### B. BibTeX 列表
{BibTeX 条目}

### C. 复现清单
- 数据集：...
- 代码：...
- 超参数：...
- 随机种子：...
- 算力：...
- 环境：...
```

---

## 6) 执行流程

```
用户: "帮我精读这篇论文 / 对 <topic> 做 deep research"
          |
          v
+-------------------------------------------------------------+
|                    主 Agent 执行                              |
+-------------------------------------------------------------+
| 【2.1 定位原文】                                              |
| 1. WebSearch: 搜索论文标题/arXivID/DOI                       |
| 2. fetch: 获取 arXiv/出版社页面，确认版本                      |
| 3. pdf-parser: 解析论文 PDF 全文                                |
|                                                              |
| 【2.2 通读与结构化笔记】                                      |
| 4. 结构化拆解：Problem/Method/Theory/Experiment/Limitation    |
| 5. 生成 Evidence Table -> 写入 draft.md                       |
|                                                              |
| 【2.3 Topic Background】                                     |
| 6. WebSearch x N: topic 定义/范式/经典工作                     |
| 7. fetch: 获取综述/教材级引用 -> 写入 draft.md                 |
|                                                              |
| 【2.4 Recent Related Works】                                 |
| 8. WebSearch x N: 关键词扩展 + 会议定向 + 引用追踪             |
| 9. fetch + pdf-parser: 逐篇获取原文并结构化阅读                  |
| 10. 生成结构化卡片 -> 写入 draft.md                            |
|                                                              |
| 【2.5 质量控制】                                              |
| 11. 双重核对关键结论，记录矛盾点                               |
|                                                              |
| 【分发任务】                                                  |
| 12. task(writer): 携带模板分发写作任务                         |
+-------------------------------------------------------------+
          |
          v
+-------------------------------------------------------------+
|                   Writer Agent 执行                           |
+-------------------------------------------------------------+
| 1. file_read: 读取 /home/workspace/draft_{任务标识}_{YYYYMMDD_HHMMSS}.md                   |
|    - Primary paper 笔记 + Evidence Table                     |
|    - Topic Background                                        |
|    - Recent Works 结构化卡片                                  |
|                                                              |
| 2. outline_generator: 生成报告大纲                             |
|    - TL;DR → Topic → Primary → Recent → Conclusion           |
|    - 确认公式/对比表/定理数量                                  |
|                                                              |
| 3. dws doc create: 生成钉钉在线文档                           |
|    - LaTeX 公式 + 对比表 + 定理化呈现                          |
|    - Callout 突出核心结论                                     |
|                                                              |
| 4. end: 返回钉钉在线文档链接                                     |
+-------------------------------------------------------------+
          |
          v
     钉钉在线文档论文深度解读报告
          |
          v
     主 Agent: 创建后续研究待办? (dws todo)
          |
          v
     主 Agent: 是否 DING 通知? → 确认后发送
```

---

## 7) 质量检查清单

### 主 Agent — 检索质量检查
- [ ] Primary paper 原文 PDF 已获取并通读（含 method + main results + experiments）
- [ ] Primary paper 结构化卡片 + Evidence Table 已完成
- [ ] Topic 的 canonical form 与关键术语已统一
- [ ] 奠基/综述工作已定位（3--8 篇），背景脉络已建立
- [ ] 近 2--3 年 strong-related 论文已找到并逐篇原文阅读（至少核心章节）
- [ ] 每篇 recent paper 输出了结构化卡片（Problem/Method/Key result/Relation）
- [ ] 引用链（forward/backward）完成，矛盾点已记录
- [ ] 所有论文引用包含：作者、标题、会议/期刊、年份
- [ ] draft.md 内容完整，可直接交付 Writer Agent

### 主 Agent — 写作质量检查
- [ ] 结构符合：TL;DR → Topic → Primary → Recent → Relation → Conclusion
- [ ] 关键公式/定理/迭代式齐全且符号一致（至少 3 个关键公式）
- [ ] 至少 1 个推导路线（proof sketch）
- [ ] 对比表完成（至少 1 张，维度统一）
- [ ] 关系论证充分（至少 3 条，非罗列）
- [ ] 局限性与开放问题具体可执行（3--6 条后续研究问题）
- [ ] 避免空泛形容词，所有结论可验证

### Writer Agent — 报告生成检查
- [ ] TL;DR 完整且不超过 10 行
- [ ] 报告结构严格遵循文档模板
- [ ] LaTeX 公式格式正确，行内/独立公式区分清晰
- [ ] 对比表维度统一、横向可比
- [ ] 核心定理使用 Assumption → Theorem → Interpretation 格式
- [ ] 所有引用标注来源
- [ ] 已成功生成钉钉在线文档并返回链接
- [ ] 已询问用户是否创建后续研究待办任务（dws todo）
- [ ] 已询问用户是否通过 DING 通知，确认后已发送

---

## 8) 常见问题排查

| 失败模式 | 典型表现 | 根因分析 | 修复方法 |
|---------|---------|---------|---------|
| 只看摘要/博客 | 报告缺少公式和定理细节，结论空泛 | 未获取原文 PDF 或未通读 | 立即回到原文，补齐 method/assumption/theorem/experiment 的证据链；使用 `pdf-parser` 解析全文 |
| 相关工作堆砌 | 列出 10+ 篇论文但无分类、无对比、无关系论证 | 未做 taxonomy，直接罗列 | 必须先给 taxonomy，再用对比表与关系论证串起来；每篇必须说明与 primary paper 的关系 |
| 公式堆砌无解释 | 贴了大量公式但读者无法理解含义 | 缺少符号定义和直觉解释 | 每个公式都要解释"每一项是什么、为什么这样建、它带来什么性质"；首次引入符号必须定义 |
| 忽略假设边界 | 定理结论写了但未交代成立条件 | 跳过 assumptions 直接写结论 | 把所有定理的关键假设列出来，并讨论能否放松/代价是什么；使用 Assumption → Theorem → Interpretation 格式 |
| 符号不一致 | 不同章节用不同符号表示同一概念 | 未在开头建立统一符号体系 | Topic 章节必须建立统一符号表，后续所有章节严格遵循；附录提供 Notation Table |
| 深度不足 | 报告看起来像"摘要集合"，无推导、无 proof sketch | 未执行 3.3 深度标准检查 | 对照 3.3 四项标准逐一检查：公式>=3、推导路线>=1、对比表>=1、关系论证>=3 |
| 时间窗口失焦 | Recent works 包含 5 年前的论文，不够"recent" | 检索时未限定时间范围 | 严格执行 2.4 中的时间窗口（默认 24--36 个月），超出范围的论文仅在 Topic background 中引用 |
| 版本混淆 | 引用的定理/实验结果与原文不一致 | 引用了 arXiv 旧版本而非 camera-ready | 2.1 阶段必须核对版本一致性，明确以哪一版为主，记录版本差异 |
| 文档误发 | 未经用户确认就自动发送通知 | 流程中跳过了用户确认步骤 | 必须等待用户明确确认后才转发文档，不可自动触发 |
```
