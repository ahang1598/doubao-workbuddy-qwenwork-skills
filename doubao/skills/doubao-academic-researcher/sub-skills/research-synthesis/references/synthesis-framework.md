# 综合框架

## 三步法详细流程

### 第一步：引文抽取

对每篇论文抽取 4 项信息：
- **核心发现**：一两句话
- **方法特征**：和其他论文的方法区别
- **适用条件**：什么条件下成立，已知局限
- **关系网**：支持/挑战/扩展了谁

不相关的论文整篇丢弃。

### 第二步：主题聚类

按**研究问题或方法流派**聚类。每个主题标记呈现方式：

- **paragraph**：多篇论文的细致综合，关系复杂时用散文
- **table**：3 篇以上可比工作的并排对比

**MECE taxonomy 设计规则**：
- 分类轴互斥且完备
- 空格 = gap = finding（"尚无工作将 X 应用于 Y"本身就是发现）
- 跨分类的论文单独讨论（它们挑战了分类轴本身）
- 如果某轴导致太多跨分类，换轴

### 第三步：逐节串行合成

每节输入 = 研究简报 + 该节分配的文献 + 已写好的前面几节。

串行保证连贯、避免重复、使过渡自然。

## 交叉对比写法

**反面**（逐篇罗列）：
> Smith et al. (2024) proposed method A for task X and achieved 85% accuracy. Lee et al. (2025) proposed method B for task X and achieved 87% accuracy.

**正面**（句内对比）：
> While Smith et al. [1] and Lee et al. [2] both target task X, they take fundamentally different approaches: Smith et al. leverage retrieval augmentation, achieving 85%, whereas Lee et al. rely on in-context learning, reaching 87% but at 3x the inference cost. Notably, Wang et al. [3] show that the retrieval-based strategy generalizes better to the related task Y, suggesting broader applicability despite the lower headline number.

**规则**：每个主题段落至少一个句子同时引用并对比 2+ 篇论文。

## 对比表设计

- 列 = 对比维度（方法特征、优势、局限、指标），不是论文属性
- 行 = 具体工作
- **caption 包含结论**（"Table 1: 基于检索的方法在召回率上领先，但推理延迟是端到端方法的 3-5 倍"）
- 缺失信息填"未报告"，不留空不编数字
- 去掉稀疏列（只有 1-2 篇报告的维度不适合做列）

## 矛盾呈现规则

A 说 X 有效、B 说 X 无效时：
1. 摆出双方发现（A 说什么、B 说什么）
2. 分析条件差异（数据集？指标？设置？样本量？）
3. 能判断 → 给倾向（"在 Z 条件下 B 更有说服力"）
4. 不能判断 → "目前证据不足以判断，需在 W 条件下验证"

**不要**：写"存在争议"然后跳过；平均掉矛盾；只引支持一方的文献。

## Related Work 思维骨架（每节必过）

写每个主题章节前，脑子里过一遍：

1. **claim**：这些工作放在一起告诉我们什么？
2. **正面证据**：哪几篇最直接支持？独立来源收敛？
3. **反面证据**：哪些工作矛盾或限定了 claim？
4. **条件差异**：正反分歧怎么解释？
5. **跨主题连接**：和其他主题什么关系？

骨架不打印，驱动散文。

**自检**：删掉引用后剩下的还是一篇有判断的分析 → 通过。只剩事实罗列 → 论证链没搭好。
