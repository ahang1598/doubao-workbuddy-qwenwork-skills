# Frontmatter 规范

> Skill 的 frontmatter 是 agent 决定"要不要触发这个 skill"的唯一依据。写错就等于 skill 不存在。

---

## 允许的字段（只有这 6 个）

```yaml
---
name: <kebab-case>             # 必需。等于目录名
description: <见下>             # 必需。≤ 1024 字符，禁用 < >
license: <可选>                 # MIT、Apache-2.0 等
allowed-tools: <可选>           # 限制 skill 内能用的工具
metadata: <可选>                # author / version / homepage 等
compatibility: <可选>           # ≤ 500 字符。前置依赖、API key 要求等
---
```

其它字段（如 `tags`、`category`、`type`）会被 `quick_validate.py` 报错。

---

## name 规范

- kebab-case：`linkfox-amazon-product-detail`、`weekly-sourcing-workflow`。
- 必须等于 skill 目录名。
- Tier 1（单源 wrapper，由各 vendor 维护）推荐前缀：`linkfox-`（团队 LinkFox 数据源）或 vendor 前缀（`junglescout-`、`sif-`）。
- Tier 2 / Tier 3（本 skill 的产出范围）建议名字直接表达业务流程或终端能力：`weekly-sourcing-workflow`、`amazon-listing-replicator`。
- 不要用驼峰、下划线、大写。

---

## description 三件套

`description` 决定 agent 在用户说话时能否唤起 skill。三个要素必须齐全：

### 1. 第一句：核心场景的最自然表述

用用户最可能的口吻把"这个 skill 是干嘛的"说出来。

> 把电商业务流程沉淀成可复用 skill 的工作流。

不要写成简介式（"This skill provides..."），不要写成 ID 式（"workflow-skill-creator: a tool"）。

### 2. 5–10 个同义改写（双语）

把用户可能说的同一件事的不同表述全列出来，中英都要。同一段里。

> 当用户说"做一个选品流程的 skill"、"把每周竞品监控做成 skill"、"productize my Amazon SOP into a skill"、"build a weekly sourcing workflow skill"、"沉淀一条运营 SOP"、"create an ecommerce workflow skill"、"封装上新流程"...

写法要点：
- **短语为主，不要造长句**：每个改写一个语义，互相之间逗号或顿号分隔。
- **覆盖术语 + 口语 + 抽象意图**：术语（"SOP"、"workflow"）、口语（"沉淀"、"productize"）、抽象（"reusable"、"可复用"）三层都要有。
- **覆盖正向 + 同义换说**：不要只写一种说法的反复变体，要找真正不同的表述路径。

### 3. 反向补漏一句（对抗欠触发）

刻意"推一把"——agent 默认偏保守，宁肯不触发，所以要显式写出"边缘情况也要触发"。

> 即使用户只说"帮我把这个变成可复用的"或 "make this reusable" 也应触发。

或：

> 一次性分析、单点查询、纯解读不在本范围。

后者是反向限定（说什么不在范围），同样有助于消除模糊地带。

---

## description 正例

**Tier 2（跨源组合 / 流程编排）**：

> 周度选品流程 skill。串起 ABA 流量数据、Junglescout 关键词反查、SIF 价格段分析，输出本周候选 ASIN 池。当用户说"做一个每周选品流程"、"productize weekly sourcing"、"build a weekly sourcing workflow"、"把竞品扫描沉淀成流程"、"make this repeatable"、"沉淀一条选品 SOP"、"批量找候选 ASIN 的流程" 时触发。即使用户只说"我想每周做一次同样的事"或 "I want to do this every week"，也应触发。

**Tier 3（业务 SOP 复刻）**：

> Amazon Listing 复刻 skill：访谈用户原 listing 与目标站点 → 串 vendor skill 拉竞品/关键词/合规 → 输出翻译后的标题/五点/A+ 草稿与对照报告。当用户说"复刻这个 listing"、"replicate this listing for DE"、"把这个 listing 搬到日本站"、"重做一个一样的 listing"、"listing 跨站点复刻" 时触发。即使用户只说"按这个 ASIN 给我做一个新站的"，也应触发。

**Tier 1（单源 wrapper，由 vendor 维护，仅作风格参考）**：

> 查询 Amazon 商品详情：传入 ASIN 和站点，返回标题、价格、评分、评论数、品牌、规格等结构化字段。当用户说"查一下这个 ASIN"、"拉取商品详情"、"get amazon product info"、"product detail by ASIN"、"商品基础信息"、"listing 元数据" 时触发。即使用户只说"看看这个 B0XXX" 也应触发。

---

## description 反例

**反例 1**：写成 ID

```
description: linkfox-skill-creator: a tool for creating skills
```

问题：没有触发场景、没有同义改写、没有反向补漏。agent 几乎不会唤起。

**反例 2**：只写一种说法

```
description: 创建电商 skill 的工作流。当用户说"创建电商 skill"时触发。
```

问题：用户不会用 skill 自己的命名说话。"做一个 SOP"、"沉淀一个流程"、"productize this" 全部漏掉。

**反例 3**：单语

```
description: Workflow for creating reusable ecommerce skills. Triggers on phrases like "create a sourcing skill", "build a workflow skill"...
```

问题：团队中文为主，中文触发短语缺失。

**反例 4**：超长（超过 1024 字符）

把所有边缘场景、所有用户故事都塞进去——超过 1024 字符会被 validator 截断。聚焦"用户最可能说的 5–10 种说法 + 反向补漏一句"，其它放进 SKILL.md 主体的"适用与不适用"。

**反例 5**：含 `<` 或 `>`

```
description: Use when <user wants to create a skill>
```

问题：YAML 解析问题，validator 会报错。改成中文括号或去掉。

---

## compatibility 字段（Tier 1 wrapper 常用）

调用受限平台 API 的 skill，写明前置条件：

```yaml
compatibility: 需要 LinkFox API key，从 https://linkfox.io/api 获取后配置在 ~/.config/linkfox/key
```

或：

```yaml
compatibility: Requires Amazon SP-API credentials. Free tier: 100 requests/day. Rate limit: 5 req/sec.
```

约束：≤ 500 字符。
