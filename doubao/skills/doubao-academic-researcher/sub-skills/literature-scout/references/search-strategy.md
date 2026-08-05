# 检索策略细则

## 关键词构造

关键词不是想到什么搜什么。按以下模式系统构造：

**模式 1：核心方法 × 应用领域**
- "retrieval augmented generation" + "question answering"
- "CRISPR base editing" + "clinical trial"

**模式 2：核心机制 × 目标任务**
- "chain of thought" + "scientific reasoning"
- "碱基编辑" + "遗传病治疗"

**模式 3：领域 + survey/benchmark/meta-analysis**
- "LLM agent survey 2024 2025"
- "social media adolescent mental health meta-analysis"

**模式 4：关键人名 × 方向**（当研究简报提到具体研究者时）
- "Haidt social media adolescent"
- "Orben screen time well-being"

**模式 5：已知论文的引用网络**
- 从已找到的核心论文的标题中提取关键术语，搜其被引/引用
- 系统化执行与收敛判据见 literature-scout SKILL.md「第五步：滚雪球至饱和」（向后反查前置、向前构造后继式检索、一轮零新增即饱和）

每个模式至少试一轮。在多视角检索中，每个视角用 1-2 种模式构造关键词，3-5 个视角 × 每视角 2 轮 = 若干轮 `scholar_search` 调用。具体次数不设上限，以覆盖充分为准。

## 盲区发现

第二轮检索后做一次盲区检查：

1. **覆盖检查**：研究简报的每个子方向是否有 ≥3 篇文献？
2. **流派检查**：有没有明显的方法流派完全缺席？
3. **引用链检查**：已找到的论文引用的高频工作是否在列表里？
4. **弃置检查**（STORM moderator trick）："搜到了但没打算用"的结果是否指向未覆盖的子方向？不要扔掉它们——它们是盲区的线索。
5. **时间检查**：近 1 年有没有重要工作？全是老论文说明可能漏了新进展。（收尾时另有硬性时效探针：宣布饱和前每视角一轮近 6-12 个月限定检索，见 literature-scout SKILL.md 第五步饱和判据。）

## 按学科调整检索

不同学科的文献分布不同：

- **CS/AI**：arXiv 预印本为主，更新极快，近 6 个月的工作可能关键。搜 arXiv 关键词。
- **生物医学**：NEJM/Lancet/Nature Medicine 的临床论文，搜 "clinical trial" + 疾病名。
- **社科**：AER/QJE（经济学）、Nature Human Behaviour（心理学），搜效应量和方法（RCT/DID/IV）。
- **跨学科**：分别搜每个相关学科，再合并。不要只搜一个学科的关键词。
