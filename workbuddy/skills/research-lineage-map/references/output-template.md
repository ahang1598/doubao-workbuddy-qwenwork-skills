# 输出 Markdown 模板与填充示例

最终交付给用户的 `.md` 文件严格按以下结构组织。语言跟随用户语言（默认中文，专名保留英文原文）。

---

## 模板骨架

````markdown
# {主题}谱系演进图（{起始年}–{截止年}）

> 一句话概览：{主题}从{起点}到{现状}的演进主线是什么，核心矛盾如何从{早期难题}演变为{当今关注点}。

## 演进总图

```mermaid
{flowchart 主图：年代/范式 subgraph 泳道 + classDef 配色 + 问题→解决边标注}
```

## 关键节点明细

| 节点 | 年份 | 核心贡献 | 解决了什么问题 | 来源 |
|---|---|---|---|---|
| {工作名} | {年份} | {一句话贡献} | {它回应的前人难题} | {链接或"年份待考"} |

## 演进阶段叙事

### 第一阶段：{年代} · {阶段主题}
{2–4 句：本阶段谁提出了什么、遇到了什么瓶颈，为下一阶段埋下什么伏笔。}

### 第二阶段：{年代} · {阶段主题}
...

## 时间线速览（可选）

```mermaid
{timeline 简版}
```

## 参考资料

- [{来源标题}]({URL}) — {核实了什么：年份/血缘关系}
- ...
````

---

## 填充示例（主题：大语言模型 GPT 家族，节选）

````markdown
# GPT 家族谱系演进图（2017–2022）

> 一句话概览：GPT 系列沿"自回归预训练 + 规模化"主线演进，核心矛盾从"如何无监督预训练"演变为"如何对齐人类意图"。

## 演进总图

```mermaid
flowchart LR
  subgraph E1["2017 · 范式奠基"]
    Transformer["Transformer (2017)"]:::milestone
  end
  subgraph E2["2018–2019 · 路线确立"]
    direction TB
    GPT1["GPT (2018)"]:::pioneer
    GPT2["GPT-2 (2019)"]:::improve
  end
  subgraph E3["2020–2022 · 规模化与对齐"]
    direction TB
    GPT3["GPT-3 (2020)"]:::improve
    InstructGPT["InstructGPT (2022)"]:::improve
  end
  Transformer -->|"提供可并行训练的自注意力架构"| GPT1
  GPT1 -->|"容量与数据不足，零样本能力弱"| GPT2
  GPT2 -->|"规模仍不足以涌现通用能力"| GPT3
  GPT3 -->|"输出不听指令、与人类意图错位"| InstructGPT
  classDef pioneer fill:#dbeafe,stroke:#2563eb,stroke-width:2px,color:#1e3a8a
  classDef improve fill:#dcfce7,stroke:#16a34a,color:#14532d
  classDef branch fill:#ffedd5,stroke:#ea580c,color:#7c2d12
  classDef milestone fill:#fef9c3,stroke:#ca8a04,stroke-width:3px,color:#713f12
```

## 关键节点明细

| 节点 | 年份 | 核心贡献 | 解决了什么问题 | 来源 |
|---|---|---|---|---|
| Transformer | 2017 | 纯自注意力架构，可大规模并行训练 | RNN 串行计算慢、长程依赖弱 | [arXiv:1706.03762](https://arxiv.org/abs/1706.03762) |
| GPT | 2018 | 生成式预训练 + 任务微调范式 | NLP 依赖有监督标注数据 | [OpenAI 博客](https://openai.com/index/language-unsupervised/) |
| GPT-3 | 2020 | 175B 参数验证 in-context learning | 小模型零样本/少样本能力弱 | [arXiv:2005.14165](https://arxiv.org/abs/2005.14165) |
| InstructGPT | 2022 | RLHF 指令对齐 | 模型输出与人类意图错位 | [arXiv:2203.02155](https://arxiv.org/abs/2203.02155) |

## 演进阶段叙事

### 第一阶段：2017 · 架构奠基
Transformer 以自注意力取代循环结构，解决了并行训练与长程依赖两大瓶颈，为一切后续工作提供架构底座。

### 第二阶段：2018–2019 · 生成式预训练路线确立
GPT 证明"无监督预训练 + 微调"可行；GPT-2 沿规模化方向推进，但零样本能力仍弱，引出"规模是否即能力"之问。

### 第三阶段：2020–2022 · 规模化与对齐
GPT-3 以 175B 参数验证规模化路线，但暴露"不听指令"的对齐缺口；InstructGPT 用 RLHF 补上，主线矛盾从"能力"转向"意图对齐"。

## 参考资料

- [Attention Is All You Need](https://arxiv.org/abs/1706.03762) — 核实 Transformer 年份与动机
- [Improving Language Understanding by Generative Pre-Training](https://openai.com/index/language-unsupervised/) — 核实 GPT 发布年份
- [Language Models are Few-Shot Learners](https://arxiv.org/abs/2005.14165) — 核实 GPT-3 年份与参数量
- [Training language models to follow instructions with human feedback](https://arxiv.org/abs/2203.02155) — 核实 InstructGPT 年份与 RLHF 方法
````

---

## 写作要求

1. **明细表与图必须同源**：图中出现的每个节点都在表中有一行，反之亦然，不得图有表无。
2. **"解决了什么问题"列**禁止写"提升了性能"这类空话，必须指向具体难题（如"长程依赖丢失""RLHF 标注成本高"）。
3. **阶段叙事按"问题链"推进**：每段结尾落到本阶段遗留的瓶颈，自然引出下一阶段。
4. **联网核实失败的节点**：来源列写"年份待考"，并在交付时口头告知用户哪些节点未能核实。
5. 参考资料只列真正用于核实的来源，不堆砌。
