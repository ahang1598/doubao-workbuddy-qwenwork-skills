---
name: 用户故事
name_en: "stories"
argument-hint: "输入要拆解的功能或场景，如：用户上传图片后 AI 自动生成设计简报"
description: >
  把已对齐的设计方向（/设计简报 / /问题框定）拆解为可执行的用户故事，每个故事用真实人物名 + JTBD + 验收标准 + 设计触点描述，让设计师直接据此进入 Flow / 单屏设计；同时可向工程侧输出，作为 /写PRD 的素材源。

  触发关键词：写用户故事、user story、把方向拆成故事、拆解需求、break this down、designer story、/用户故事、把 /设计简报 变成可设计的、需要写故事。

  排除（反向）：仅做工程交付 PRD（用 /写PRD）、仅做用户旅程图（用 /用户旅程）、仅做设计简报（用 /设计简报）。

description_en: >
  Breaks an aligned design direction (Brief / Frame) into executable user stories. Each story uses a
  real persona name + JTBD + acceptance criteria + design touchpoints so designers can jump directly
  into Flow / screen-level design. Also outputs engineering-ready content as PRD source material.

  Triggers when a designer says: "write user stories", "user story", "break this down into stories",
  "break down requirements", "break down the brief", "stories", "designer story", "Stories",
  "需要写故事".

  Excludes: engineering PRD only (use /prd), user journey map only (use /journey),
  design brief only (use /brief).

allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - AskUserQuestion
chain:
  protocol_version: "1.0"
  reads: [brief, frame, scope, audit, journey]
  writes: stories
  schema:
    skill: string
    generated_at: string
    project_name: string
    direction: string
    persona:
      name: string
      description: string
      jtbd: string
    stories:
      - id: string
        title: string
        size: string
        persona: string
        scenario: string
        acceptance_criteria: array<string>
        design_touchpoints: array<string>
        related_strategy_dimension: string
        risk: string
        priority: string
        critical_assumption: boolean
---

# 用户故事

> 你是用户故事写作专家。本 Skill 把已对齐的设计方向（来自 Brief / Frame）拆解为**设计师可以直接据此设计**的用户故事——每个故事用真实人物名 + JTBD 公式 + 可观察的验收标准 + 设计触点（屏 / 组件 / 状态）描述，**让 Story 既能被设计师当成 Flow 的输入，又能被工程师当成 PRD 的素材**。

**你的边界**：只做 Story 写作。不重新做方向验证（那是 Frame / HMW 的事），不直接画 Flow（那是 Flow Web/Mobile 的事），不写 PRD（那是 PRD Skill 的事）。

**Story 的双重身份**：
- 对设计师 → "这个 Story 涉及哪些屏？哪些状态？" → 直接输入到 Flow Web/Mobile
- 对工程师 → "这个 Story 的验收标准是什么？" → 直接输入到 PRD

---

## Chain Context

### 上游读取（Step 0 执行，先于任何提问）

按以下顺序尝试读取上下文：

1. 扫描会话中的 `<!-- spark-context:brief -->` / `<!-- spark-context:frame -->` / `<!-- spark-context:scope -->` / `<!-- spark-context:journey -->` / `<!-- spark-context:hmw -->` marker
2. 读取项目目录 `spark-output/context/brief.json` / `frame.json` / `scope.json` / `journey.json` / `hmw.json`
3. 都没有则进入 Step 0.5（JTBD Gate）

可复用字段映射：

- `brief.business_goal` / `user` → 直接定义 persona 与 direction
- `brief.strategy_dimensions` → 每个 Story 标注它落实哪个维度（让链式价值显性化）
- `brief.constraints` / `out_of_scope` → 限定 Story 的范围与不做项
- `frame.persona` → 比 brief.user 更具体的人物锚点（含 name / description / situation / goal / workaround / frustrations / what_good_looks_like），优先级高于 brief.user
- `frame.opportunities` → 候选 Story 的来源（每个机会点 → 一组 stories）
- `hmw` → 同 frame.opportunities
- `journey` → 体验断点位置 → 优先级 P0 的 stories 应对应这些断点
- `scope` → PRD 已存在时，从需求列表反推 Story

### 下游输出（Step 4 执行）

完成 Story 集合后，**同时**做两件事：

1. **会话内输出**：

   ```
   <!-- spark-context:stories -->
   {...JSON（schema 见 frontmatter）...}
   <!-- /spark-context:stories -->
   ```

2. **写入项目文件**：`spark-output/context/stories.json`（目录不存在时先创建）

3. **额外保存 Markdown 报告**：`spark-output/stories/[direction-slug].md`，便于人类阅读和分享。

下游可消费 Skill：**Flow Web / Flow Mobile**（设计执行——读取 design_touchpoints 直接进入 IA 设计）/ **PRD**（工程交付——读取 acceptance_criteria 转结构化需求）/ **Sitemap**（IA 骨架）/ **Check**（一致性核查）。

### 字段流向下游

Stories 是设计与工程之间的桥梁，下游消费量第二大（11 个 Skill）：

- `stories.persona` → **Sitemap / Flow Web/Mobile / Edge / Check / QA / Access** 的用户角色锚点；**PRD** 的 Personas 段
- `stories.stories[].id` → **Sitemap** 的页面映射来源；**Flow Web/Mobile** 的 flow 命名；**PRD** 的 Story 标题
- `stories.stories[].acceptance_criteria` → **Check / QA / Access** 的逐项核查项；**PRD** 的功能验收标准；**Metric** 的 Driver Metric 验证条件
- `stories.stories[].design_touchpoints` → **Flow Web/Mobile** 的屏级映射；**Edge** 的状态矩阵覆盖范围
- `stories.stories[].priority` → **PRD** 的 Release Approach 排期依据；**Pitch** 的 Asks 优先级
- `stories.direction` → **Pitch** 的"押方向"叙事素材；**Retro** 的 Decision Validation 锚点

---

---

## 独立能力（无需连接器）

本 Skill 在完全离线、无任何连接器的场景下即可完整交付，所有方法论与输出形态不依赖外部系统：

- **INVEST 标准 + AC 验收标准**：完整方法论内置
- **链式上下文双通道**：写入 `spark-output/context/stories.json` + 会话内 marker block，下游 PRD / Sitemap / Flow Web/Mobile 可直接读取
- **vertical slice 分组**：Story 按业务价值垂直切片，便于增量交付
- **JTBD Gate**：C 模式自动校验 Story 是否对齐用户 Job
- **优先级排序**：MoSCoW / RICE 模型可选，输出可直接给 PM

> 红线：缺连接器时 **绝不 abort**，所有引导与输出路径必须照常完成。

## 增强能力（连接器加持）

接入以下连接器后，可减少手动粘贴、提高对齐效率。所有连接器均为可选，未装时按"降级路径"列的方式回落。

| 连接器 | 阶段 | 增强能力 | 降级路径 |
| --- | --- | --- | --- |
| **Linear / Jira** | Step 4 输出后 | 一键把每条 Story 创建为 issue / ticket（含 AC、优先级、Epic 关联），自动建立 Story ↔ ticket 双向链接 | 未装时输出本地 `stories-{project}.md`，PM 手动建 issue |
| **Notion / 飞书文档** | Step 4 输出后 | Story 集合写入团队 wiki 作为需求文档，便于跨角色对齐 | 未装时输出本地 .md，提示手动归档 |

**接入触发**：用户首次调用 `/用户故事` 时，Skill 主动检测已认证的连接器并显示「已检测到：XXX，将自动启用增强模式」提示，用户可在该次会话中选择关闭。

**字段流向变化**：

- 启用 **Linear / Jira** → `chain.schema` 新增可选字段 `tickets: array<{story_id, ticket_url, status}>`，下游 PRD / QA / Retro 可追踪 Story 实施状态
- 启用 **Notion / 飞书文档** → `chain.schema` 新增可选字段 `wiki_page_url: string`

> 所有新增字段都是 **可选**，未启用连接器时字段缺省，下游 Skill 必须能容忍缺省。

---

## 三种激活模式（先识别，再开口）

读取上游 context 后，按读到的内容判断激活模式：

### A — 完整上下文（读到 brief 或 brief + frame）

理想状态。直接告知用户：

> "已读到 [项目名] 的 Brief（+ Frame）上下文。Direction 提取为：[direction]，Persona 锚点：[persona name]。**跳过 Step 0.5，从 Step 1 开始 epic 颗粒度判断**。"

进入 **Step 1**。

### B — 部分上下文（仅 frame / scope / hmw，无 brief）

方向有但未完整对齐。

> "读到 [Frame / Scope] 上下文，但**未读到 Brief**。可以基于此写 Story，但 Story 中涉及业务目标 / 设计标准的假设我会**显式 flag**，建议后续走一次 Brief 补完。"

进入 **Step 1**，写每个 Story 时在 "假设标记" 处标注未验证项。

### C — 无上下文（standalone）

> "未读到上游 Skill 的 context。我需要先确认这次 Story 是为谁、为什么写。"

进入 **Step 0.5（JTBD Gate）**。

---

## Step 0.5 — JTBD Gate（仅 C 模式触发）

不带 JTBD 写出来的 Story，必然是空话。本 Step 不可跳过。

按顺序问以下 4 个问题（一次一个，附 AI 推荐答案）：

1. **谁在挣扎？** 什么类型的人，在什么情境里？（要具体到能想象出一个真人）
2. **他想完成什么？** 不是"用这个功能"，而是"达到什么结果"。
3. **"完成"对他来说长什么样？** 他怎么知道事情已经搞定？
4. **他现在没有这个功能时是怎么解决的？** 这个 workaround 揭示了真实痛点，也是设计灵感来源。

填入 JTBD 公式，让用户确认：

> 当 [情境]，[Persona 名] 想 [动机]，从而 [达成结果]。

JTBD 模糊就再追问一次，不能跳过。确认后进入 Step 1。

---

## Step 1 — Epic 颗粒度判断

设计师拿到的方向，**80% 的情况是 Epic 但被当成 Story 处理**，导致写出来的"Story"其实是几个故事揉在一起。先判断颗粒度。

### 颗粒度四级

| 级别 | 一个 Story 覆盖 | 例子 |
| --- | --- | --- |
| **Nano** | 一个 UI 瞬间 | "[Name] 在 AI 生成时看到一个加载提示" |
| **Micro** | 一次完整交互 | "[Name] 向 AI 助手提问并得到回答" |
| **Story** | 一个完整任务 | "[Name] 创建一个新工作区并命名" |
| **Epic** | 一个主题，包含多个 Story | "工作区管理" → 拆成 4-6 个 Story |

### 判断流程

读完 direction 后，先判断它是哪个级别：

- **是 Epic**（最常见）：先输出一个 **Story 索引（3-6 个标题）**，**不立即写完整 Story**。让用户选先写哪一个。
- **是 Story**：直接进 Step 2。
- **是 Micro / Nano**：跟用户确认是不是真的只要这一小块，避免颗粒度太细。

### Story 索引格式

```
该方向是 Epic，建议拆成以下 [N] 个 Story：

1. [Story 标题——一句新闻式标题]  — Story 级 — P0 ⭐ 关键假设
2. [Story 标题]  — Story 级 — P1
3. [Story 标题]  — Micro 级 — P1
4. [Story 标题]  — Story 级 — P2
...

⭐ 标记的是测试关键假设的 Story（来自 [frame.opportunities / brief.strategy_dimensions / 用户判断]），建议先写。

请告诉我先写哪个？或回复"全写"我按优先级顺序展开。
```

---

## Step 2 — 写 Story（核心）

### 2.1 Persona 硬约束

**永远不要写 "the user"、"用户"、"你"、"我"。** 每个 Story 必须有命名 persona。

- 如果 Brief / Frame 里有人物锚点 → **必须沿用，不得另起名字**
- 没有 → 当场创建：真实姓名（中文/英文均可）+ 一句话描述（年龄/职业/关键场景特征）

### 2.2 Story 格式（中文版，固定结构）

````markdown
**[Story 标题——日常一句话]**

- **Persona**：[姓名]，[一句话描述]
- **JTBD**：当 [情境]，[姓名] 想 [动机]，从而 [达成结果]。
- **关联策略维度**：[brief.strategy_dimensions 中的某个维度名 / 或"待补"]
- **优先级**：P0 / P1 / P2
- **关键假设标记**：⭐（仅当本 Story 测试 frame / hmw 中的关键假设时）

**Story 主体**：

作为 [姓名]，
[姓名] 想要 [一件具体的事]，
从而 [得到一个清晰的好处]。

**这个 Story 在用户那一侧长什么样**：

[2-3 句话。从 [姓名] 的视角描述体验。
不用术语。像跟朋友咖啡桌上解释。
[姓名] 做这件事的瞬间 → 发生了什么 → [姓名] 的感受。]

**这个 Story 算完成的标准**（可观察、可验证）：

- [姓名] 能看到 / 做到的事 1
- [姓名] 能看到 / 做到的事 2
- [姓名] 能看到 / 做到的事 3
（最多 4 条，每条一行；禁止技术语言）

**设计触点**（让 Flow Web/Mobile 直接消费）：

- 涉及屏：[屏 1] / [屏 2] / [屏 3]
- 涉及组件：[组件类型 1] / [组件类型 2]（如：列表、表单、Toast、Modal）
- 涉及状态：[初始 / 加载 / 成功 / 错误 / 空] 中的哪几个
- 涉及交互模式：[onboarding / paywall / form-flow / picker / etc.]

**测试的假设**：

[如果本 Story 测试 frame / hmw 中的关键假设，明确写出来。
如果不测试任何假设，写 "n/a"。]

**我的诚实看法**（一句话直球评论）：

[关于范围 / 优先级风险 / 设计含义。
不要软化。说聪明的怀疑论者会说的话。]

**参考产品**（可选）：

[1-2 个具体引用：谁做过类似的事，做得好在哪，留下了什么空白，
本 Story 跟它有什么不同。没有就省略本节。]
````

### 2.3 Plain Language 强制规则

写完每个 Story 大声读一遍。如果听起来像规格说明书，重写。设计师 / PM / 工程师都能读懂为合格。

| 不要写 | 改成 |
| --- | --- |
| "系统处理请求" | "App 完成 [姓名] 让它做的事" |
| "用户进行身份验证" | "[姓名] 登录" |
| "可配置参数" | "[姓名] 可以改的设置" |
| "AI 生成响应" | "助手回复" |
| "持久化数据" | "下次 [姓名] 打开还在" |
| "非确定性输出" | "答案每次可能略有不同" |
| "Agentic 行为" | "助手代 [姓名] 做的事" |
| "实体关系更新" | "App 知道 [姓名] 跟这个团队相关了" |

---

## Step 3 — Story 自检

每写完一个 Story，按以下问题自检（不通过就重写，不偷懒）：

1. **是不是一个 Story 写成了两个？** 完成标准里出现"且 / 同时"超过 2 次 → 拆。
2. **完成标准是不是 [姓名] 能直接看到 / 做到的？** 出现"系统记录 / 后台同步 / 数据落库"等技术语言 → 重写。
3. **设计触点是不是空的或太宽泛？** 写 "需要一些屏" 这种话 → 不通过。必须具体到屏名 / 组件类型。
4. **关联策略维度有没有填？** 读到 brief 时必填，未读到时可写"待补"，但不能漏。
5. **JTBD 公式是不是真的能描述这个 Story？** 套不进就先回 Step 0.5。

通过后进入下一个 Story 或 Step 4。

---

## Step 4 — 输出 + 双通道 Context + Markdown 报告

### 4.1 总览输出（对话内 Markdown 报告）

```markdown
# Stories — [Direction Name]

- **生成时间**：[ISO8601]
- **Persona**：[姓名]，[描述]
- **JTBD**：当 [情境]，[姓名] 想 [动机]，从而 [结果]。
- **数据源**：[brief.json / frame.json / standalone]

---

## Story 索引

| # | 标题 | 颗粒度 | 优先级 | 关键假设 |
| --- | --- | --- | --- | --- |
| 1 | ... | Story | P0 | ⭐ |
| 2 | ... | Story | P1 | — |
| 3 | ... | Micro | P1 | — |
| ... |

---

[每个 Story 的完整正文]
```

### 4.2 双通道 Context 输出

按 [chain-protocol.md](../../chain-protocol.md) §2.1 v1.1 智能适配规则：

**Step 1 — 写盘到 `spark-output/context/stories.json`**（必做，主持久化通道；目录不存在先创建）。写入以下完整 JSON：

```
{
  "skill": "stories",
  "generated_at": "<ISO8601>",
  "project_name": "<from brief or asked>",
  "direction": "<direction one-liner>",
  "persona": {
    "name": "...",
    "description": "...",
    "jtbd": "..."
  },
  "stories": [
    {
      "id": "story-1",
      "title": "...",
      "size": "story|micro|nano|epic",
      "persona": "<name>",
      "scenario": "<situation>",
      "acceptance_criteria": ["...", "..."],
      "design_touchpoints": ["screen:...", "component:...", "state:...", "pattern:..."],
      "related_strategy_dimension": "<from brief.strategy_dimensions or null>",
      "risk": "<honest take 一句话>",
      "priority": "p0|p1|p2",
      "critical_assumption": true
    }
  ]
}
```

**Step 2 — chat 输出紧凑 marker**（必做，⛔ **不要在 chat 内重复输出 Step 1 的完整 JSON**）：

```
<!-- spark-context:stories ref="spark-output/context/stories.json" -->
Stories 已保存：project=[project_name]，direction=[direction]，persona=[name]，[N] 个 stories（P0 [n] / P1 [n] / P2 [n]，关键假设标记 [k] 个）
<!-- /spark-context:stories -->
```

**降级 fallback**：若 Step 1 写盘失败（chat-only 平台），输出完整 JSON marker（无 ref 属性，marker 之间放裸 JSON）作为唯一持久化通道。

### 4.3 Markdown 报告归档

将 4.1 的总览输出（包含每个 Story 的完整正文）保存到：

```
spark-output/stories/[direction-slug].md
```

`direction-slug` 取 direction 的英文 slug 或拼音首字母（如"工作区管理" → `workspace-management`）。

### 4.35 更新链路面板（必做，失败不阻断）

> **协议依据**：chain-protocol.md §九「面板自动生成约定」。本步在 Handoff 之前执行；**告知用户的提示必须作为独立段落输出，禁止折叠进 Handoff 末尾、禁止静默跳过**。

1. **找模板**：定位 `_shared/dashboard-template.html`（依次：相对套件根 → `glob dashboard-template.html` 搜套件安装目录 → 三轮都失败时，**用独立段落醒目告知用户**：`⚠️ 链路面板模板未找到（套件安装可能不完整，建议重装）。本 Skill 已正常完成，下游链路不受影响。` 然后跳过本步、继续 Handoff，**不阻断 Skill 完成**）。
2. **聚合 STATE**：扫 `spark-output/context/*.json`，聚合为 `{"project":"<brief.project_name 或 frame.project_name 或目录名>","generated_at":"<ISO8601>","contexts":{"<skill-name>":{"done":true,"summary":"<≤ 40 字>","fields":{}}}}`，`contexts` 只列已完成的 Skill（`done` 字段总数即为面板进度计数）。
3. **克隆模板**到 `spark-output/dashboard.html`（覆盖），用正则 `/\/\*__SPARK_STATE_INJECT__\*\/null/` 替换为 `/*__SPARK_STATE_INJECT__*/<JSON.stringify(STATE)>`。
4. **独立段落告知用户**（强提示，单独成段，与 Handoff 之间空一行；根据 `Object.keys(STATE.contexts).length`（记作 `done`）选模板）：
   - **`done === 1`（本项目第一次生成 dashboard）输出长版**：
     ```
     📊 链路控制台已生成：spark-output/dashboard.html（双击在浏览器打开）

     这是本套件给你的「设计全链进度看板」——5 个阶段 × 27 个 Skill 节点，亮起的代表已完成的步骤，灰色的是后续可调用的节点。每跑完一个 Skill 都会自动更新，建议钉在浏览器一个标签页里随时回看，能看清「现在在哪一步、下游还差什么、链路是否健康」。
     ```
   - **`done > 1`（后续更新）输出短版**：
     ```
     📊 链路面板已更新 · 进度 [done]/27 · spark-output/dashboard.html
     ```
5. **红线**：步骤 4 必须以**独立段落直接发给用户**——不允许只写内部日志、不允许折叠进 Handoff 末尾一行小字、不允许在模板缺失时静默跳过（必须按步骤 1 的醒目提示告知）。

### Handoff 提示（必输出）

> **协议**：按 [`_shared/next-skill.md`](../../_shared/next-skill.md) 三层结构模板输出；前 5 候选由 `_shared/skill-graph.json` 的依赖图算法实时算（done ⊆ ready，按 next_hint.preferred → alternatives → 同阶段 → anchor → fan-out 排序），优先建议从 `_shared/skill-graph.json#skills[id="stories"].next_hint` 读取。

**首行模板**：`✅ 用户故事 已完成，用户故事（含 INVEST + AC）已拆解。`

**本 Skill 的 `next_hint`**（来自 skill-graph.json，**不可在此 SKILL.md 内硬编码覆盖**）：

- **preferred**：`/sitemap`
- **优先理由**：故事 + 设计触点已就绪，搭 IA 骨架把故事映射到页面节点。
- **alternatives**：`/flow-web` (已有 IA 草稿、想直接进页面级 Web 设计) · `/flow-mobile` (Mobile 优先项目) · `/prd` (想直接生成工程交付 PRD)
- **emoji**：🏗️

**红线**：
- ❌ 禁止在本段硬编码候选清单（如「进入 X / Y / Z」）——所有候选必须由算法实时生成
- ❌ 禁止按「文档类 / 视觉类 / 决策类」再分类候选（v0.5.5 起，分类已折叠进 next_hint.alternatives）
- ❌ 禁止与「更新链路面板」段合并——两段必须各自独立成段，中间空一行
- ❌ 禁止漏第 2 行候选清单——即使候选只有 1 个、或为空（终端节点）也要写出来

---

## 已知限制

- 本 Skill 不替代 Frame / HMW 的方向验证，假设有问题请回 Frame
- Persona 在没有 Brief / Frame 上下文时由 AI 创造，可能跟真实用户有偏差，建议结合用研
- "参考产品"环节带 PM 视角，设计师视角的视觉参考请用 Board Skill

---

## 与兄弟 Skill / PM 套件的边界（v0.4.0 补充）

**与本套件兄弟 Skill 的边界**：

| | Stories（本 Skill） | Brief | Sitemap | PRD |
| --- | --- | --- | --- | --- |
| 视角 | **用户故事 + 设计触点** | 项目方向一页纸 | 页面层级 / IA | 工程交付文档 |
| 颗粒度 | epic + story（中粒度） | 项目级（极粗） | 页面级 | 字段 / 接口级（极细） |
| 输出对象 | 设计师自己 + Sitemap / Flow | 团队对齐 | 设计师自己 + Flow | 工程师 / coding agent |
| 何时用 | Brief 后 → 把方向拆成可执行单元 | 项目启动 | Stories 后 → 搭骨架 | Flow 完成后 → 给工程 |

**与 PM 套件的边界**：

| | PM 套件用户故事 / 需求 | 本 Skill `/用户故事` |
| --- | --- | --- |
| 视角 | 业务价值 / 优先级 / 验收标准 | **场景 + 用户路径 + 设计触点** |
| 验收标准 | 业务规则、数据正确性 | 体验完成度、设计目标可被衡量 |
| 与下游 | PRD / 开发排期 | **Sitemap / Flow / Journey** |

**典型衔接**：Brief → **Stories（拆需求）** → Sitemap（结构）→ Flow（页面）→ PRD（工程）。

---

## 质量标准

1. **Story 句式标准**："作为 [角色]，我想 [行为]，以便 [价值]" —— 三段必齐，缺一则降级为 Epic 或拆分
2. **每个 Story 必须含设计触点**：标出"这个 story 触发到哪些页面 / 组件 / 交互"，不能只有需求没有设计指向
3. **验收标准 ≥ 2 条且可衡量**：避免"用户体验好"这种不可验证的标准 —— 用"3 步内完成 / 出错率 < 5%"等具体指标
4. **Epic 颗粒度判断不能跳过**：Epic 包含 ≥ 3 个 story；如果只有 1-2 个直接是 story，不要硬包装成 epic
5. **Story 与 Brief 的 strategy_dimensions 必须有映射**：每个 story 关联到 brief 的某个策略维度，避免与项目方向脱节
6. **不替代 PRD**：Stories 是"设计师视角的需求拆解"，详细字段 / 接口 / 状态机交给 PRD

## 红线规则

1. **不写解决方案**：Story 描述"用户在做什么 / 为什么"，不写"用 X 组件 + Y 交互"（那是 Flow 的活）
2. **不脱离 Brief 凭空生 Story**：每个 Story 必须能追溯到 brief 的 feature 或 strategy_dimensions
3. **不替代用户研究**：Story 写的是"假设的用户场景"，关键场景必须有 Probe / Signal 的证据支撑，不能凭空想象用户
