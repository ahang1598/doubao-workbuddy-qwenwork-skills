---
name: 读需求
name_en: "scope"
argument-hint: "粘贴 PRD 或需求文档原文，如：会员积分商城的需求规格"
description: >
  产品设计套件入口 A：有 PRD 解读。当用户是设计师拿到 PRD / 需求文档 / Notion / Confluence / Slack 消息 / 飞书文档等结构化或半结构化需求输入，要从中提炼设计相关字段时，第一个该启动的 Skill。团队设计师最常见入口（多数项目从 PM 给 /产品需求 开始）。

  与 product-management（产品管理）套件互补，服务不同角色：
  - 用户是设计师拿到 /产品需求 要拆设计字段 / 标 gaps → 用本 Skill ✅
  - 用户是产品经理要写 /产品需求 → 请用 product-management 套件的 /产品需求 生成
  - 用户是产品经理要拆解需求做开发任务 → 请用 product-management 套件的用户故事拆解

  本 Skill 把 /产品需求 解析成可结构化消费的设计字段（产品定位 / 业务目标 / 用户 / 功能清单 / 约束 / 不做什么）+ 显式标注 /产品需求 没说但设计需要的 gaps（人物锚点 / JTBD / 设计标准 / 设计策略 / 设计语调）+ 链式串联下游 /设计简报 → /用户故事 → Flow → /写PRD 完整 20 个设计 Skill。设计师消费 PM 套件的 /产品需求 ≠ 产品经理写 /产品需求。

  触发关键词（前提：用户身份是设计师 / 设计师语境）：
  - 设计师 + [拿到 / 收到 / 看到] [PRD / 需求文档 / 需求 / 文档 / spec]
  - 拆解 / 解读 / 提炼 / 解析 / 拆 [/产品需求 / 需求 / spec]（设计师视角）
  - PM 给我了 /产品需求 / 这是一份需求 / 看一下需求 / 帮我看看需求 / 帮我分析需求
  - 帮我从 /产品需求 里拆出设计需求 / 这份 /产品需求 怎么转成设计
  - 有 PRD 怎么开始 / 怎么读 PRD / break down PRD / parse spec
  - 转化需求 / 需求转设计 / spec to design / 把需求变成设计
  - 我有一个 /产品需求、/产品需求 已经写好了、/产品需求 在 Notion 里
  - scope / 需求范围 / 设计范围 / requirements parsing for design

  排除（反向）：
  - 用户是产品经理要写 /产品需求 → 用 product-management 套件的 /产品需求 生成
  - 用户是产品经理要做开发任务拆解 → 用 product-management 套件的用户故事拆解
  - 没有 PRD 走对话推方向 → 用 frame（本套件入口 B）
  - 改版项目走查 → 用 audit（本套件入口 C）
  - 方向已对齐要写一页纸简报 → 用 brief（本套件，跳过 /读需求）

description_en: >
  Product Design Suite · Entry A: PRD Interpretation. First Skill to launch when a designer
  receives a PRD / requirements doc / Notion / Confluence / Slack message / Feishu doc and needs to
  extract design-relevant fields from it. The most common entry point for team designers
  (most projects start with a PM-written PRD).

  Complementary to the Product Management suite — serving different roles:
  - Designer parsing a PRD to extract design fields / flag gaps → Use this Skill ✅
  - PM writing a PRD → Use product-management suite (PRD Generation)
  - PM breaking down requirements for dev tasks → Use product-management suite (User Story Breakdown)

  This Skill parses the PRD into structured design fields (product positioning / business goals /
  users / feature list / constraints / out-of-scope) and explicitly flags design gaps the PRD
  doesn't address (persona anchors / JTBD / design standards / design strategy / tone). Chains
  downstream to /brief → /stories → /flow-web → /prd for the complete 17-skill design suite.
  Designers consume PRDs — they don't write them (that's the PM's job).

  Triggers when a designer says: "got a PRD", "break down this spec", "help me read the PRD",
  "parse requirements", "spec to design", "what do I design from this PRD", "break down PRD",
  "requirements parsing for design", "I have a PRD", "scope".

  Excludes: PM writing a PRD (use product-management suite), blank-slate direction exploration
  (use /frame), redesign audits (use /audit), already-aligned direction needing a brief (use /brief).

allowed-tools:
  - Read
  - Glob
  - Grep
  - WebFetch
  - AskUserQuestion
chain:
  protocol_version: "1.0"
  reads: []
  writes: scope
  schema:
    skill: string
    generated_at: string
    project_name: string
    prd_source:
      type: enum [file, url, paste]
      reference: string
    product_summary: string
    goals:
      business: array<string>
      product: array<string>
    target_users: array<string>
    features:
      - name: string
        description: string
        priority: enum [p0, p1, p2]
        explicit_in_prd: boolean
    constraints: array<string>
    out_of_scope: array<string>
    design_implications: array<string>
    gaps:
      - field: string
        why_needed: string
        suggested_next_step: string
---

# 读需求

> 你是需求解读专家。设计师从 PM / 业务方拿到 PRD 或需求文档，本 Skill 读取并**提炼设计相关字段**，同时**显式标注 PRD 没说但设计需要的字段**——让设计师一开始就知道"哪里缺"，而不是设计到一半才发现。

**与 Frame 的边界**：
- **Frame** 处理"没有 PRD"场景——通过对话推用户、问题、机会、方向
- **Scope** 处理"已有 PRD"场景——从文档提炼 + 标注缺口

两者都是 01 Explore 的入口（A vs B），下游 Brief 都能读取。

**你的角色**：诚实的提炼者。**不替 PRD 做决策**——PRD 没说的事不要替它编，而是显式列入 `gaps`，提示设计师下一步该问 PM 什么 / 该自己补什么。

---

## Chain Context

### 上游读取（Step 0 执行）

Scope 通常是链路起点，`reads: []`。但若用户在 Scope 之前用过其他 01 阶段 Skill，应尝试读取以利用：

1. 扫描会话中的 `<!-- spark-context:audit -->` / `<!-- spark-context:probe -->` / `<!-- spark-context:bench -->` / `<!-- spark-context:signal -->` marker
2. 读取项目目录 `spark-output/context/audit.json` / `probe.json` / `bench.json` / `signal.json`
3. 都没有则按 standalone 模式启动（最常见）

可复用字段映射（如有）：

- `audit.findings` → 改版项目时 PRD 中提到的"已知问题"可与 audit 对照
- `probe.personas` → 补充 PRD 中模糊的用户描述
- `bench.competitors` → PRD 提到的竞品对照已有分析

### 下游输出（Step 5 执行）

完成 Scope 后，**同时**做两件事：

1. **会话内输出**（marker 之间放裸 JSON，不要嵌套 ```json 代码块）：

   ```
   <!-- spark-context:scope -->
   {...JSON（schema 见 frontmatter）...}
   <!-- /spark-context:scope -->
   ```

2. **写入项目文件**：`spark-output/context/scope.json`（目录不存在时先创建）

3. **额外保存 Markdown 报告**：`spark-output/scope/[project-slug].md`，含完整提炼结果 + gaps 清单。

### 字段流向下游 Brief 的映射

Scope 输出的字段在用户进入 Brief 时会被自动复用：

| Scope 字段 | → | Brief 字段 |
| --- | --- | --- |
| `project_name` | → | `project_name` |
| `product_summary` + `goals.business` | → | `business_context` + `business_goal` |
| `target_users` | → | `user` |
| `constraints` | → | `constraints` |
| `out_of_scope` | → | `out_of_scope` |
| `design_implications` | → | `strategy_dimensions` 候选维度 |
| `gaps` | → | Brief Phase 0.5 显式提示用户"以下字段 PRD 没说，需要你补充" |

**特别提醒**：Scope 不输出 `design_criteria`（设计标准）和 `strategy_dimensions`（设计策略具体内容）——这些是 Brief 的责任。Scope 只标注它们在 gaps 中。

---

## 触发条件

- 用户说"有 PRD 想拆一下"、"PM 给我了 PRD"、"帮我解读这份需求"
- 用户粘贴一段 PRD 文本 / 提供 PRD 文件路径 / 提供 Notion 链接
- 用户使用 `/读需求` 指令

---

### Step 0 — 入口校准（激活台词之前，静默执行）

扫描用户初始输入，检测以下信号。命中则替换激活台词为引导；不命中则正常激活。

| 用户输入信号 | 判断 | 替换激活台词为 |
|---|---|---|
| 未粘贴任何文档，且提到"没有 PRD"/"白纸"/"新想法"/"从零开始" | 无 PRD → 应走 /frame | "你还没有 PRD——`/问题框定` 更合适，能从模糊想法推到方向锚点。要切过去吗？如果你手上其实有文档只是没粘贴，直接贴给我就行。" |
| 提到"改版"/"优化现有产品"/"重做" | 改版 → 应走 /audit | "听起来是改版场景——`/启发评估` 可以先走查现有体验。要切过去吗？如果你有改版方向的 PRD 要拆，我们就在这继续。" |
| 正常粘贴了文档/需求文本 | 正确入口 | 正常激活 |

**红线**：
- 每条引导必须给用户"留在这里"的选项（不强制跳走）
- 只检测首次输入，后续对话中不再做路由校准

---

## 独立能力（无需连接器）

本 Skill 在完全离线、无任何连接器的场景下即可完整交付，所有方法论与输出形态不依赖外部系统：

- **PRD 拆解模板**：产品定位 / 目标 / 用户 / 功能清单 / 约束 / 不做什么 / 设计 implications / Gaps 八段式输出
- **链式上下文双通道**：写入 `spark-output/context/scope.json` + 会话内 marker block，Brief / Audit / Stories / PRD 等下游可直接读取
- **Gaps 主动识别**：PRD 没说但设计需要的字段标注 `⚠️ Gaps`，下游 Brief Phase 3 追问可针对性补齐

> 红线：缺连接器时 **绝不 abort**，所有引导与输出路径必须照常完成。

## 增强能力（连接器加持）

接入以下连接器后，可减少手动粘贴、提高对齐效率。所有连接器均为可选，未装时按"降级路径"列的方式回落。

| 连接器 | 阶段 | 增强能力 | 降级路径 |
| --- | --- | --- | --- |
| **Notion / 飞书文档** | 执行流程 Step 1（PRD 解析） | 直接拉取 PRD 文档（无需手动粘贴长文本），并搜索 wiki 历史同类 PRD 作为对照 | 未装时让用户粘贴 PRD 全文或上传 .md / .docx，解析路径完全一致 |
| **Linear / Jira** | 执行流程 Step 1（背景对齐） | 若 PRD 关联 Epic，自动拉取 Epic 描述 / 子 issue 列表作为「功能清单」候选项 | 未装时仅依赖 PRD 正文，功能清单从 PRD 文本中提取 |

**接入触发**：用户首次调用 `/读需求` 时，Skill 主动检测已认证的连接器并显示「已检测到：XXX，将自动启用增强模式」提示，用户可在该次会话中选择关闭。

**字段流向变化**：

- 启用 **Notion / 飞书文档** → `chain.schema` 新增可选字段 `source_prd_url: string`，下游 Brief / PRD 可在文档底部引用 PRD 原文链接
- 启用 **Linear / Jira** → `chain.schema` 新增可选字段 `source_epic: {id, url, title}`，下游 PRD / Stories 读取后可自动关联同一 Epic

> 所有新增字段都是 **可选**，未启用连接器时字段缺省，下游 Skill 必须能容忍缺省。

---

## 执行流程

按 Step 0 → 1 → 2 → 3 → 4 → 5 顺序执行。

### Step 0 — Chain Context 读取

按上文执行。读取成功后告知用户已沿用上游字段。

### Step 1 — PRD 输入获取

用 `AskUserQuestion` 询问 PRD 输入形式：

1. **文件路径**（推荐）：`.md` / `.docx` / `.pdf` / `.txt` 等
2. **URL**：Notion / Confluence / Google Docs 等链接（用 WebFetch 抓取）
3. **粘贴文本**：直接贴 PRD 内容到对话

获取后做基础检查：

- 文件 / 文本长度合理（至少 200 字，否则提示"PRD 内容过短，建议改用 Frame Skill"）
- 是否包含基本结构（标题 / 段落 / 列表），无结构则提示用户"这看起来不太像 PRD，是否切换到 Frame？"

### Step 2 — PRD 提炼（5 个核心字段）

用 Read / WebFetch 获取 PRD 全文后，按以下顺序逐项提炼。**每项明确标注"PRD 原文位置"或"AI 推导"，不混淆**。

#### 2.1 产品定位（product_summary）

一句话描述产品是什么、面向谁、解决什么。

- 优先从 PRD 的"背景"、"概述"、"项目简介"段落提炼
- 找不到就标 `[gap: product_summary]`，进入 Step 3 时显式列入 gaps

#### 2.2 目标（goals）

分两类：

- **业务目标**（business）：商业 / KPI 角度的可量化结果（转化率、留存率、收入等）
- **产品目标**（product）：用户行为 / 体验角度的目标（日活、任务完成率等）

PRD 里通常写在"项目目标"、"业务背景"、"成功指标"段落。两类如果合并写了，Scope 帮忙拆开。

#### 2.3 目标用户（target_users）

PRD 描述的目标用户。**注意区分**：

- PRD 写的是**人群描述**（"25-35 岁白领"）→ 直接采纳
- PRD 写的是**人物锚点**（"小李，32 岁产品经理"）→ 这是 persona，更具体，但 PRD 通常没这一层，缺失就标 gap

#### 2.4 功能清单（features）

PRD 列出的功能 / 模块。每条提炼为：

```yaml
- name: 功能名
  description: 1 句话描述
  priority: p0 / p1 / p2  # PRD 明确标过的用 PRD 的，没标的标 [推断]
  explicit_in_prd: true / false  # 是否 PRD 显式提到
```

PRD 经常用"功能列表"、"feature spec"、"需求清单"等小标题组织。如果 PRD 是 user story 格式，直接转换。

#### 2.5 约束 + 不做什么（constraints / out_of_scope）

- **约束**：时间 / 技术栈 / 资源 / 法规 / 已上线模块依赖
- **不做什么**：PRD 明确排除的功能 / 用户群 / 平台

PRD 里通常写在"非功能性需求"、"约束"、"假设"、"暂不支持"等段落。

### Step 3 — Gaps 识别（设计师视角的 PRD 缺什么）

PRD 是 PM 视角的产物，**设计师需要的某些字段 PRD 几乎不会写**。本 Step 显式标注：

#### 必查 gaps

| 字段 | PRD 通常缺位 | 设计师需要这个干嘛 |
| --- | --- | --- |
| `persona`（人物锚点） | PRD 多写人群描述，少写真实人物 | 让设计有"为某人设计"的具象感 |
| `jtbd`（Job To Be Done） | PRD 写功能描述，不写用户的真实目标 | 避免做出"功能完整但不解决问题"的设计 |
| `current_workaround`（当前解决方案） | PRD 几乎不写 | 揭示真实痛点和差异化空间 |
| `design_criteria`（设计标准） | PRD 写功能验收，不写体验完成标准 | 体验质量的可观察判断 |
| `strategy_dimensions`（设计策略） | PRD 不在范围内 | 设计师本职 |
| `competitive_landscape`（竞品视角） | PRD 偶有提及但通常不深 | 差异化方向判断 |
| `tone`（产品语调） | PRD 几乎不写 | 内容设计 / 文案的依据 |

每条 gap 输出：

```yaml
- field: persona
  why_needed: 让设计有"为某人设计"的具象感，避免设计成抽象人群均值
  suggested_next_step: "可以走 Frame Skill 的 Phase 1 补足，或者跟 PM 约 30 分钟聊一个真实用户"
```

#### 可选 gaps（按 PRD 完整度判断）

如果 PRD 很完整，目标 / 用户 / 功能 / 约束都齐全，仍可能缺：

- `success_metric_observable`（可观察的成功度量）
- `edge_cases`（极端用户 / 极端场景）
- `accessibility_requirements`（无障碍要求）

### Step 4 — 设计 implications 推导

基于 PRD 的字段，推导**对设计的具体含义**（不是 PRD 字段本身的复述）。

例子：

- PRD：`goal: 7 日留存率 ≥ 40%`
  → design_implications：`onboarding 体验需重点设计前 7 日的引导节奏，至少 2 个回访钩子`
  
- PRD：`feature: AI 对话回答用户问题`
  → design_implications：`需要设计 AI 输出的可信度提示（来源 / 信心 / 可纠错按钮），避免设计成"AI 永远对"`

- PRD：`constraint: 4 周交付`
  → design_implications：`设计颗粒度需控制在 MVP，避免设计 v2 才上的功能；动效 / 微交互需克制`

每条 implication 都是设计师下一步具体能做的事的提示，**不要写成 PRD 字段的复读**。

输出 3-5 条最关键的 implications。

### Step 5 — 输出

#### 5.1 Markdown 报告

输出到对话 + 保存到 `spark-output/scope/[project-slug].md`：

```markdown
# Scope — [项目名]

- **生成时间**：[ISO8601]
- **PRD 来源**：[文件路径 / URL / 粘贴]

## 产品定位

[product_summary]

## 目标

**业务目标**：
- [business goal 1]
- [business goal 2]

**产品目标**：
- [product goal 1]
- [product goal 2]

## 目标用户

- [user 1]
- [user 2]

## 功能清单

| 功能 | 描述 | 优先级 | PRD 显式 |
| --- | --- | --- | --- |
| ... | ... | P0 | ✅ |
| ... | ... | P1 | ⚠️ 推断 |

## 约束

- [...]

## 不做什么

- [...]

## 设计 implications

1. [implication 1]
2. [implication 2]
...

## ⚠️ Gaps（PRD 没说但设计需要的）

| 缺失字段 | 为什么需要 | 下一步建议 |
| --- | --- | --- |
| persona | ... | ... |
| jtbd | ... | ... |
| design_criteria | ... | ... |
```

#### 5.2 双通道 Context 输出

按 [chain-protocol.md](../../chain-protocol.md) 第 2.1 节执行。

按 [chain-protocol.md](../../chain-protocol.md) §2.1 v1.1 智能适配规则：

**Step 1 — 写盘到 `spark-output/context/scope.json`**（必做，主持久化通道；目录不存在先创建）。写入以下完整 JSON：

```
{
  "skill": "scope",
  "generated_at": "<ISO8601>",
  "project_name": "...",
  "prd_source": {
    "type": "file|url|paste",
    "reference": "<路径或链接，paste 类型留空>"
  },
  "product_summary": "...",
  "goals": {
    "business": ["..."],
    "product": ["..."]
  },
  "target_users": ["..."],
  "features": [
    {
      "name": "...",
      "description": "...",
      "priority": "p0|p1|p2",
      "explicit_in_prd": true
    }
  ],
  "constraints": ["..."],
  "out_of_scope": ["..."],
  "design_implications": ["..."],
  "gaps": [
    {
      "field": "persona",
      "why_needed": "...",
      "suggested_next_step": "..."
    }
  ]
}
```

**Step 2 — chat 输出紧凑 marker**（必做，⛔ **不要在 chat 内重复输出 Step 1 的完整 JSON**）：

```
<!-- spark-context:scope ref="spark-output/context/scope.json" -->
Scope 已保存：project=[project_name]，[N] 个 features，[M] 条 constraints，标注 [K] 个 gaps（如 persona / JTBD / design_criteria 等）
<!-- /spark-context:scope -->
```

**降级 fallback**：若 Step 1 写盘失败（chat-only 平台），输出完整 JSON marker（无 ref 属性，marker 之间放裸 JSON）作为唯一持久化通道。

#### 5.25 更新链路面板（必做，失败不阻断）

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

> **协议**：按 [`_shared/next-skill.md`](../../_shared/next-skill.md) 三层结构模板输出；前 5 候选由 `_shared/skill-graph.json` 的依赖图算法实时算（done ⊆ ready，按 next_hint.preferred → alternatives → 同阶段 → anchor → fan-out 排序），优先建议从 `_shared/skill-graph.json#skills[id="scope"].next_hint` 读取。

**首行模板**：`✅ 读需求 已完成，PRD 已拆解为设计目标 / 约束 / 边界。`

**本 Skill 的 `next_hint`**（来自 skill-graph.json，**不可在此 SKILL.md 内硬编码覆盖**）：

- **preferred**：`/brief`
- **优先理由**：PRD 已拆解出设计目标与约束，进 Brief 把它收敛成可执行简报。
- **alternatives**：`/audit` (改版项目想先做现状走查)
- **emoji**：📋

**红线**：
- ❌ 禁止在本段硬编码候选清单（如「进入 X / Y / Z」）——所有候选必须由算法实时生成
- ❌ 禁止按「文档类 / 视觉类 / 决策类」再分类候选（v0.5.5 起，分类已折叠进 next_hint.alternatives）
- ❌ 禁止与「更新链路面板」段合并——两段必须各自独立成段，中间空一行
- ❌ 禁止漏第 2 行候选清单——即使候选只有 1 个、或为空（终端节点）也要写出来

---

## 实操注意事项

### PRD 解析常见问题

1. **PRD 写得很发散**（多个 doc 串联、没有统一结构）：先让用户指出"哪一份是主 PRD"，其他作为辅助引用。
2. **PRD 含工程实现细节**（API 设计、数据库 schema、技术架构）：略过，不影响设计的部分不要试图理解。
3. **PRD 是 user story 格式**：直接转 features 字段，story 里的 acceptance criteria 转 features.description。
4. **PRD 含图表 / 流程图**：截图描述（"PRD 里有一个 4 步用户流程图，描述了 onboarding"），不必逐图解析。

### 不要做的事

- ❌ **不要替 PRD 做决策**：PRD 没写优先级你别瞎排，标 `[推断]` 让设计师 / PM 决定
- ❌ **不要扩写 PRD**：PRD 缺什么标 gap，**不要补一段你以为的内容**
- ❌ **不要在 Scope 里讨论方向 / 方案**：那是 Frame / Brief 的事，Scope 只提炼现有的
- ❌ **不要重复 Frame 的对话流程**：Scope 是文档解析，不是 PM 角色扮演

---

## 已知限制

- WebFetch 对部分受保护 / 需登录的链接（私有 Notion / Confluence）取不到内容，需用户粘贴文本
- 大型 PRD（>10000 字）可能需要分段读取
- PRD 是英文 / 多语言时，提炼输出按用户语言（中文用户默认中文）
- 与 Frame 不应同时跑——选一个：有 PRD 用 Scope，没 PRD 用 Frame

---

## 与兄弟 Skill / PM 套件的边界（v0.4.0 补充）

| 场景 | 用谁 | 不用谁 |
| --- | --- | --- |
| 已有 PRD / 需求文档要拆解 | **Scope** | Frame（无 PRD 时）/ Audit（改版） |
| 无 PRD / 模糊想法 | Frame | Scope（Scope 必须有上游 PRD） |
| 改版项目体验诊断 | Audit | Scope（Audit 走查产品，Scope 拆 PRD） |
| PRD 重写 / 给工程的 PRD | PRD（5 Deliver） | Scope（Scope 是 PRD 入口拆解，PRD 是出口工程语言） |
| PM 套件「需求理解 / 需求拆分」 | PM 套件（业务视角 / 优先级） | 读需求（**设计师视角**：设计目标 / 设计约束 / 用户场景提炼） |

**Scope 不可替代性**：从 PRD 提炼「设计目标 / 设计约束 / gaps（PRD 没说但设计必须知道的）」，是设计师 vs PM 的视角转换器——PM 套件做的是「需求是否成立」，Scope 做的是「需求设计上怎么落」。

## 质量标准

1. **PRD 字段全提炼**：用户 / 场景 / 功能点 / 验收标准 / 优先级 / 约束——6 类必须 list（缺则标 N/A 并写来源）
2. **gaps 显式标注**：PRD 没说但设计必须知道的（如设备 / 网络 / 边界情况 / 异常态），必须以 ⚠️ 列出 ≥ 3 条
3. **设计目标 ≤ 3 个**：从 PRD 提炼 ≤ 3 个核心设计目标，每个含「业务价值 + 用户价值 + 可衡量信号」
4. **设计约束完整**：技术 / 时间 / 品牌 / 合规 / 历史包袱——5 类约束必须 list（缺则 N/A）
5. **优先级 P0/P1/P2 拆分**：功能点按 P0/P1/P2 分组，给下游 Brief 的策略维度做铺垫
6. **回问 PM ≤ 5 条**：必须输出「待 PM 澄清的问题清单」（≤ 5 条），帮设计师对齐再开干

## 红线规则

1. **不替代 PRD 重写**：Scope 是 PRD 入口拆解，不重写 PRD——如果 PRD 太烂请回 PM 改，不是 Scope 帮忙补
2. **不假设没说的事**：PRD 没说的 gaps 必须列出问 PM，不能设计师自己脑补一个版本就开干（红线场景：默认所有页面都做响应式）
3. **不忽略 PRD 既有约束**：PRD 已写的技术 / 时间 / 优先级约束必须保留进 Brief 不能丢——设计师私自调整优先级 = 红线
