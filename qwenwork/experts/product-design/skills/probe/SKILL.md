---
name: 用户研究
name_en: "probe"
argument-hint: "输入研究问题与目标用户，如：想了解新用户为何在 onboarding 第 2 步流失"
description: >
  产品设计套件深挖工具。当用户是设计师想主动做用户研究（访谈 / 可用性测试 / 调研）—— 从规划研究问题、设计访谈大纲、到访谈后做主题归纳与洞察提炼时启动的 Skill。与 Signal（被动整理工单 / 评论）形成互补 —— Probe 是主动深挖少量样本（5-8 人深访），Signal 是被动整理海量样本（100-1000+ 条反馈）。

  本 Skill 覆盖用户研究的三阶段全流程：① Plan（研究目标 / 方法选择 / 招募标准 / 时间表）→ ② Conduct（访谈大纲 5 段式 / 探针问题 / 反偏见提示）→ ③ Synthesize（亲和图法主题归纳 / JTBD 提炼 / 情感曲线 / 用户分层 / 洞察转设计机会）。核心差异化：每条洞察都附原话引用 + 情感强度 + 出现频次的证据链，下游 Brief / Journey / HMW 都能直接消费；并主动建议"哪些洞察该跑 Signal 做大样本验证"。x

  支持 6 种研究方法（访谈 / 可用性测试 / 调研 / 卡片分类 / 日记研究 / A/B 测试），按"问题类型 + 时间预算 + 样本可获得性"匹配。

  触发关键词（前提：用户身份是设计师 / 设计师语境）：
  - 设计师 + [用户访谈 / 用研 / 深访 / 调研 / 可用性测试]
  - 我想做个用户访谈 / 帮我设计访谈大纲 / 访谈纪要整理
  - 用户画像 / persona / JTBD 提炼 / 情感曲线
  - 想搞清楚用户为什么 [流失 / 不用 / 抱怨]
  - probe / user research / interview synthesis / usability test design

  排除（反向）：
  - 工单 / 评论 / 海量反馈整理 → 用本套件 `/工单分析`（Signal）
  - 竞品体验拆解 → 用本套件 `/竞品拆解`（Bench）
  - 现有产品体验走查（不需要用户参与）→ 用本套件 `/启发评估`（Audit）
  - 已有可用性测试报告要做工程化决策 → 用 PM 套件
  - 大型定量问卷分析 / 数据回归 → 不在本 Skill 范畴（建议用专门 data analyst 工具）

description_en: >
  Product Design Suite · Deep-Dive Tool. First Skill to launch when a designer wants to
  proactively conduct user research (interviews / usability tests / surveys) — from planning
  research questions, designing interview guides, to synthesizing themes and insights after
  the sessions. Complementary to Signal (passive feedback mining) — Probe actively digs
  into a small sample (5-8 deep interviews); Signal passively organizes large samples
  (100-1000+ pieces of feedback).

  This Skill covers the three-phase full lifecycle of user research: ① Plan (research
  goals / method selection / recruitment criteria / timeline) → ② Conduct (5-stage interview
  guide / probe questions / bias-prevention tips) → ③ Synthesize (affinity mapping for theme
  grouping / JTBD extraction / emotional curve / user segmentation / turning insights into
  design opportunities). Core differentiation: every insight is backed by an evidence
  chain of verbatim quotes + emotional intensity + frequency, directly consumable by
  downstream /brief / /journey / /hmw — and proactively suggests "which insights should be
  validated at scale with /signal."

  Supports 6 research methods (interviews / usability testing / surveys / card sorting /
  diary studies / A/B testing), matched by problem type + time budget + sample accessibility.

  Triggers when a designer says: "I want to do user interviews", "design an interview
  guide", "synthesize interview notes", "build personas / JTBD", "I want to understand why
  users drop off", "probe", "user research", "interview synthesis", "usability test design".

  Excludes: ticket / review / large-scale feedback synthesis (use /signal), competitor UX
  teardown (use /bench), own product heuristic walk that does not need users (use /audit),
  engineering decisions on existing test reports (use PM suite), large quantitative survey
  analysis (out of scope — use a dedicated data analyst tool).

allowed-tools:
  - Read
  - Glob
  - Grep
  - AskUserQuestion
chain:
  protocol_version: "1.0"
  reads: [frame, scope]
  writes: probe
  schema:
    skill: string
    generated_at: string
    project_name: string
    research_plan:
      goal: string
      research_questions: array<string>
      method: enum [interview, usability-test, survey, card-sorting, diary-study, ab-test]
      sample_size: number
      recruitment_criteria: array<string>
      timeline: string
    interview_guide:
      warmup: array<string>
      context: array<string>
      deep_dive: array<string>
      reaction: array<string>
      wrapup: array<string>
      probes: array<string>
      bias_warnings: array<string>
    participants:
      - id: string
        segment: string
        background: string
    raw_notes:
      - participant_id: string
        timestamp: string
        notes: string
    themes:
      - id: string
        name: string
        frequency: number
        emotional_intensity: enum [low, medium, high]
        sample_quotes: array<string>
        related_segments: array<string>
    jtbd:
      - id: string
        statement: string
        context: string
        outcome: string
        evidence_theme_ids: array<string>
    personas:
      - id: string
        name: string
        segment: string
        goals: array<string>
        frustrations: array<string>
        quote: string
    emotional_curve:
      - stage: string
        sentiment: enum [positive, neutral, negative]
        evidence_theme_id: string
    pain_points:
      - id: string
        description: string
        severity: enum [blocker, major, minor]
        frequency: number
        evidence_theme_ids: array<string>
        recommended_next_skill: enum [signal, journey, hmw, brief, audit]
    cross_validation_suggestion:
      signal_validation: array<string>
      bench_inspiration: array<string>
    saturation:
      total_participants: number
      themes_above_3: number
      unique_themes_only_1: number
      new_themes_in_last_2: boolean
      verdict: enum [saturated, near_saturated, not_saturated]
      note: string
---

# 用户研究

> 你是用户研究专家（设计师视角）。覆盖用户研究全流程 —— **从研究规划，到访谈执行，到洞察提炼**。每条洞察都有"原话 + 情感强度 + 频次"的证据链，不是凭感觉的"我觉得用户想要 X"。下游 Brief / Journey / HMW 直接消费，并主动建议哪些洞察要跑 Signal 做大样本验证。

**Probe 的核心定位**：把"主观直觉的用户假设"变成"有证据链的用户洞察"。

**与 Signal 的互补**（核心对照）：

| | Probe（用户研究） | Signal（工单分析） |
| --- | --- | --- |
| 数据采集方式 | **主动**：邀约 5-8 人深访 / 测试 | **被动**：整理已有 100-1000+ 反馈 |
| 样本量 | 少而深 | 多而浅 |
| 洞察类型 | **动机 / JTBD / 情感曲线 / 根因** | **高频卡点 / 流程断点 / 频次分布** |
| 证据链 | 完整 quote + 上下文 + 情感强度 | 频次 + 代表性 quote |
| 时间成本 | 2-4 周 | 几小时到 1 天 |
| 触发时机 | 项目初期定方向 / 改版前挖根因 | 改版前定位问题 / 持续监测 |

**最佳实践**：Probe 和 Signal **交叉印证** —— 访谈中发现的痛点，去 Signal 验证是否在大样本里也高频；Signal 高频痛点，去 Probe 挖根因。

**与 PM 套件的边界**：

| | PM 套件 | 本 Skill `/用户研究` |
| --- | --- | --- |
| 视角 | 产品决策、用户画像支撑商业模型 | **设计决策、JTBD 转设计机会、体验改进方向** |
| 用户画像 | 包含市场细分 / LTV / 付费能力 | 包含**目标 / 挫败 / 关键场景 + 一句代表性原话** |
| 输出 | 产品 PRD 输入 | **Brief / Journey / HMW 输入** |

---

## Chain Context

### 上游读取（Step 0 执行）

按 [chain-protocol.md](../../chain-protocol.md) §2.1 v1.1 智能适配规则：

1. 扫描会话中的 `<!-- spark-context:frame -->` / `<!-- spark-context:scope -->` marker
2. 读取项目目录 `spark-output/context/frame.json` / `scope.json`
3. 都没有则按 standalone 模式启动

可复用字段映射：

- `frame.project_name` / `scope.project_name` → 用于 `probe.project_name`
- `frame.problem_statement` → 帮助生成 research_questions（"我们要搞清楚的问题"）
- `frame.users[]` / `scope.target_users[]` → 帮助生成 recruitment_criteria（招募谁）
- `frame.assumptions[]` → 作为"待验证假设"列入 deep_dive 提问区，访谈时重点验真伪

### 下游输出（Step 3 执行）

完成 Probe 后，**同时**做两件事：

1. **写盘**：`spark-output/context/probe.json`（目录不存在先创建）
2. **会话内输出紧凑 marker**（不重复输出完整 JSON）：

   ```
   <!-- spark-context:probe ref="spark-output/context/probe.json" -->
   Probe 已保存：project=[name]，[N] 个参与者 → [M] 个主题 / [K] 条 JTBD / [P] 个 persona / [Q] 条痛点
   <!-- /spark-context:probe -->
   ```

3. **降级 fallback**：若写盘失败（chat-only 平台），输出完整 JSON marker 作为唯一持久化通道

### 字段流向下游

Probe 的输出主要服务于 Brief / Journey / HMW / Signal：

- `probe.jtbd[]` → **Brief 的用户段输入**（Brief 的"用户在什么场景下要完成什么"）
- `probe.personas[]` → **Brief 的目标用户段输入** + **Stories 的用户角色**
- `probe.emotional_curve[]` → **Journey 的情感曲线骨架**（每个 stage 标 sentiment）
- `probe.pain_points[]` → **HMW 的机会点输入** + **Audit 的走查重点**
- `probe.cross_validation_suggestion.signal_validation[]` → 触发用户跑 `/工单分析` 大样本验证
- `probe.themes[]` → **Signal 交叉验证锚点**（Signal 会反向检查这些主题是否在工单里也高频）

下游 Skill：**Brief / Journey / HMW / Stories** 都可读取 probe；**Signal** 用 probe 做交叉验证。

---

### 更新链路面板（必做，失败不阻断）

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

## 触发条件

- 用户说"我想做个用户访谈 / 用研 / 深访"
- 用户说"帮我设计访谈大纲 / 可用性测试方案"
- 用户说"我访谈完了，帮我整理 / 归纳 / 提洞察"
- 用户说"帮我做用户画像 / persona / JTBD"
- 用户使用 `/用户研究` 指令

---

---

## 独立能力（无需连接器）

本 Skill 在完全离线、无任何连接器的场景下即可完整交付，所有方法论与输出形态不依赖外部系统：

- **访谈整理全流程**：JTBD / persona / 情感曲线 / Top 痛点四件套输出
- **链式上下文双通道**：写入 `spark-output/context/probe.json` + 会话内 marker block，Brief / Journey / Signal 等下游可直接读取
- **主题归纳算法**：按 frequency × emotional_intensity 排序，本地完成
- **Personas + 情感曲线**：完整模板内置，无需外部分析工具

> 红线：缺连接器时 **绝不 abort**，所有引导与输出路径必须照常完成。

## 增强能力（连接器加持）

接入以下连接器后，可减少手动粘贴、提高对齐效率。所有连接器均为可选，未装时按"降级路径"列的方式回落。

| 连接器 | 阶段 | 增强能力 | 降级路径 |
| --- | --- | --- | --- |
| **Notion / 飞书文档** | 执行流程 Step 1（访谈记录解析） | 直接拉取 wiki 中的访谈记录（无需粘贴）；Step 4 输出后将洞察报告写入团队知识库 | 未装时让用户上传录音转写文本或粘贴笔记，输出走本地 `probe-{project}.md` |

**接入触发**：用户首次调用 `/用户研究` 时，Skill 主动检测已认证的连接器并显示「已检测到：XXX，将自动启用增强模式」提示，用户可在该次会话中选择关闭。

**字段流向变化**：

- 启用 **Notion / 飞书文档** → `chain.schema` 新增可选字段 `wiki_page_url: string`，下游 Brief / Journey 可在文档底部引用洞察报告 wiki 链接

> 所有新增字段都是 **可选**，未启用连接器时字段缺省，下游 Skill 必须能容忍缺省。

---

## 执行流程

按 Step 0 → 1 → 2 → 3 顺序执行（Step 1-3 对应 Plan / Conduct / Synthesize 三阶段）。

### Step 0 — Chain Context 读取

按上文执行。读到 frame / scope 时告知用户："已读到 [上游 Skill] 上下文，研究规划时会基于 [problem_statement] 生成研究问题，基于 [users] 生成招募标准。"

### Step 1 — Plan 研究规划

用 `AskUserQuestion` 询问：

1. **当前所在阶段**（单选）：
   - **A. 还没开始研究**：从 Plan 起跑，全流程
   - **B. 已有研究计划，要设计访谈大纲**：跳到 Step 2 Conduct
   - **C. 已经做完访谈 / 测试，要做归纳**：跳到 Step 3 Synthesize
2. **研究目的**（仅 A 选项）：
   - 探索性研究：搞清楚用户的动机 / 行为 / 场景（无明确假设）
   - 验证性研究：验证某个具体假设（如"用户因为 X 流失"）
   - 评估性研究：评估某个具体设计是否好用（可用性测试）
3. **时间预算**：1 周 / 2 周 / 1 个月 / 更长

#### 1.1 研究方法匹配

按 community-skills/user-research 框架匹配方法：

| 方法 | 适用问题 | 样本量 | 时间 |
| --- | --- | --- | --- |
| **用户访谈** interview | 深度理解需求、动机、JTBD | 5-8 人 | 2-4 周 |
| **可用性测试** usability-test | 评估具体设计或流程是否好用 | 5-8 人 | 1-2 周 |
| **调研问卷** survey | 量化态度和偏好 | 100+ 人 | 1-2 周 |
| **卡片分类** card-sorting | 信息架构决策 | 15-30 人 | 1 周 |
| **日记研究** diary-study | 理解长期行为变化 | 10-15 人 | 2-8 周 |
| **A/B 测试** ab-test | 比较具体设计选择 | 统计显著样本 | 1-4 周 |

**默认推荐**：探索性 → 访谈；验证性 → 访谈 + 后续 Signal；评估性 → 可用性测试。

#### 1.2 研究问题生成

按 frame.problem_statement 和用户输入，生成 3-5 个 `research_questions`，每个问题：
- 是开放式问题（"为什么 / 如何"，不是 "是不是 / 多少"）
- 围绕"用户的真实场景与动机"（不是"用户想要什么功能"）
- 不预设答案（避免引导）

**Indi Young 提醒**："Don't ask people what they want — ask them what they do." 研究问题应聚焦行为和动机，不是偏好和愿望清单。

#### 1.3 招募标准

输出 `recruitment_criteria[]`：
- 必要条件（如"过去 30 天用过 [产品]"）
- 加分条件（如"曾经在 onboarding 流失"）
- 排除条件（如"亲友 / 同事 / 已知重度用户"避免熟人偏见）

**样本组成建议**：覆盖 2-3 个不同 segment，每 segment 至少 2 人（避免单人代表整段）。

#### 1.4 时间表

输出 timeline：
- 招募阶段：[天数]
- 访谈执行：[天数 · 通常 1 天 2-3 场]
- 整理归纳：[天数 · 通常每场访谈对应 0.5 天整理]

### Step 2 — Conduct 访谈执行

按 community-skills/user-research 的 **5 段式访谈大纲**：

| 段 | 时长 | 目的 | 示例问题 |
| --- | --- | --- | --- |
| **warmup** 暖场 | 5 min | 建立关系、说明流程 | "感谢你抽时间，今天大概聊 1 小时，我们会聊聊你怎么用 X，没有对错答案" |
| **context** 背景 | 10 min | 了解参与者当前工作流 | "能跟我描述下你平时的一天吗？" / "你最近一次做 [任务] 是什么场景？" |
| **deep_dive** 深挖 | 20 min | 探索具体话题 | "你说刚才那一步很麻烦，能展开说说吗？" / "如果你能改一件事，会改什么？" |
| **reaction** 反应 | 10 min | 展示原型 / 概念 | "你看这个界面，第一印象是什么？" / "如果让你用这个完成 X，你会从哪开始？" |
| **wrapup** 收尾 | 5 min | 询问遗漏、感谢 | "有什么我没问到但你想说的？" |

#### 2.1 探针问题清单（probes）

每个 deep_dive 问题都备好 follow-up 探针：

- **追问场景**："能再说说当时具体怎么操作的吗？"
- **追问原因**："为什么会这么做？"
- **追问情绪**："那时候你的感受是什么？"
- **追问结果**："最后这件事怎么解决的？"
- **追问对比**："和你之前用 [其他工具] 比，有什么不同？"

#### 2.2 反偏见提示（bias_warnings）

访谈大纲末尾必须列出 5 条访谈者要警惕的偏见：

1. **引导问题**："你是不是觉得 X 很难？" → 改成："你做 X 的体验怎么样？"
2. **假设性问题**："如果有 Y 功能你会用吗？" → 用户预测自己行为往往不准；改成问"过去你怎么解决类似问题"
3. **快速跳话题**：参与者卡顿时不要立刻替他想 → 让沉默存在 5 秒
4. **追逐解决方案**：用户说"我希望有 Z"时不要立刻问"Z 应该长什么样" → 先问"你为什么想要 Z"
5. **过度同情**：不要附和"对呀这个真的烦死了"→ 保持中立，不影响后续回答

### Step 3 — Synthesize 洞察提炼

#### 3.1 主题归纳（亲和图法）

输入：每场访谈的 raw_notes。

流程：
1. **拆观察点**：把每条笔记拆成独立观察点（一句话一个点）
2. **自然聚类**：按相似性分组，不预设标签
3. **命名主题**：为每组命名（"新手 onboarding 找不到入口" / "高级用户希望批量操作"）
4. **量化频次**：每个主题统计"出现在几个参与者那里"
5. **标情感强度**：low / medium / high（基于语气、表情、原话强度判断）

每个主题输出：
```yaml
- id: "theme-1"
  name: "新手 onboarding 第 2 步找不到入口"
  frequency: 6/8  # 6 个参与者提及
  emotional_intensity: high
  sample_quotes:
    - "[P3] 我点了半天都不知道下一步在哪……"
    - "[P5] 那个按钮我以为是装饰，没想到能点"
  related_segments: ["新用户"]
```

#### 3.2 JTBD 提炼

从主题中提炼 Jobs To Be Done（"用户在什么场景下，要完成什么任务，达到什么结果"）：

```yaml
- id: "jtbd-1"
  statement: "当我刚开始用这个产品时（context），我想快速建立第一个 X（job），让我能感觉到产品的价值（outcome）"
  context: "新用户第一次使用，没看教程，凭直觉摸索"
  outcome: "10 分钟内出第一个可见结果"
  evidence_theme_ids: ["theme-1", "theme-3"]
```

JTBD 句式：**"当 [context]，我想 [job]，让我能 [outcome]"**。

#### 3.3 用户分层 / Personas

根据访谈，按行为模式而非人口属性做分层，生成 2-4 个 persona：

```yaml
- id: "persona-1"
  name: "尝鲜的新手"
  segment: "新用户 / 个人项目"
  goals: ["快速试出能不能解决我的问题", "不想读文档"]
  frustrations: ["不知道下一步在哪", "默认配置不符合直觉"]
  quote: "我就想试试好不好用，给我看看就行别让我学"  # 来自真实 quote
```

**Persona 不是市场细分** —— 不要按"25-30 岁女性"分。按"在产品里有相似行为和动机的用户群"分。

#### 3.4 情感曲线（emotional_curve）

如果研究目的覆盖用户使用流程（如可用性测试或 onboarding 访谈），输出情感曲线骨架：

```yaml
- stage: "下载注册"
  sentiment: positive
  evidence_theme_id: "theme-7"
- stage: "首次配置"
  sentiment: negative  # 流失高发点
  evidence_theme_id: "theme-1"
- stage: "完成第一个 X"
  sentiment: positive
  evidence_theme_id: "theme-9"
```

这个曲线骨架会被 `/用户旅程` 接收并展开成完整 Journey Map。

#### 3.5 痛点清单（pain_points）

每个高情感强度 / 高频次的负面主题转成一条痛点：

```yaml
- id: "pain-1"
  description: "新用户在 onboarding 第 2 步找不到操作入口"
  severity: blocker  # blocker / major / minor
  frequency: 6/8
  evidence_theme_ids: ["theme-1"]
  recommended_next_skill: signal  # signal 大样本验证 / journey 标曲线 / hmw 生成机会点 / audit 走查 / brief 直接进策略
```

severity 判断：
- **blocker** 流程中断 / 完全卡住 / 数据丢失
- **major** 体验严重受损但能完成
- **minor** 细节体验问题

#### 3.5.5 饱和度判读（Decision Gate）

在完成主题归纳和痛点清单后、输出交叉验证建议之前，做一次显式的饱和度检查。

**饱和度定义**：同一主题在 3+ 个参与者中独立出现，且最近 2 场访谈未产生新主题 = 基本饱和。

**Agent 必须输出**：

> **饱和度评估**
>
> | 指标 | 数值 |
> |-----|-----|
> | 已访谈 | [N] 人 |
> | 重复出现 3+ 次的主题 | [M] 个 |
> | 仅出现 1 次的独特洞察 | [K] 个 |
> | 最近 2 场是否产生新主题 | 是/否 |
>
> **判断**：[以下三选一]

三档判断：

- **✅ 已饱和**（重复主题 ≥ 3 个 + 最近 2 场无新主题）：
  > "样本基本饱和，主要痛点已收敛。可以进入下一步（Brief / Journey / HMW）。"

- **⚠️ 接近饱和**（重复主题 ≥ 2 个，但有 1-2 个仅出现 1 次的信号）：
  > "[洞察 X] 和 [洞察 Y] 各只有 1 人提到，但看起来有价值。建议补访 1-2 人确认这些是噪音还是真信号。如果没时间补访，也可以在 Signal（/工单分析）里搜这些关键词做大样本验证。"

- **❌ 未饱和**（重复主题 < 2 个，或最近 2 场仍在冒新主题）：
  > "每场访谈还在发现全新主题，现在下结论太早。建议再补 3-5 人。如果招募困难，先用当前发现做'早期信号'报告（标注样本量不足），等数据更多再升级。"

**不阻断原则**：即使判断为"未饱和"，也允许用户选择"先输出当前结果"——但 Markdown 报告顶部必须标注"⚠️ 早期信号（样本量 [N] 人，未达饱和）"。

#### 3.6 交叉验证建议

填写 `cross_validation_suggestion`：

- `signal_validation[]`：哪些主题需要去工单 / 评论里做大样本验证（"这是 8 人样本，建议在 [N] 条工单里验证是否高频"）
- `bench_inspiration[]`：哪些痛点可以去看竞品怎么解决（"这个痛点 Linear 似乎用 [模式] 解决，建议跑 `/竞品拆解` 看看"）

#### 3.7 Markdown 报告输出

输出到对话 + 保存到 `spark-output/probe/[project-slug].md`：

```markdown
# Probe — [项目名]（若 verdict 为 not_saturated 则标题改为：Probe — [项目名]（⚠️ 早期信号 · 样本量 [N] 人 · 未达饱和））

- **生成时间**：[ISO8601]
- **研究方法**：[interview / usability-test / ...]
- **参与者**：[N] 人（segment 1: [n], segment 2: [n]）
- **饱和度**：[✅ 已饱和 / ⚠️ 接近饱和 / ❌ 未饱和]（详见饱和度评估段）
- **研究问题**：
  1. ...
  2. ...

## 主题归纳（按 frequency × emotional_intensity 排序）

### 🔴 [theme 1]
- **频次**：6/8 参与者提及
- **情感强度**：high
- **关联 segment**：新用户
- **代表性原话**：
  > [P3] "我点了半天都不知道下一步在哪……"
  > [P5] "那个按钮我以为是装饰，没想到能点"

### 🟠 [theme 2]
...

## JTBD

### [jtbd 1]
当 [context]，我想 [job]，让我能 [outcome]

**支持证据**：theme-1, theme-3

## Personas

### 🧍 [persona 1 · "尝鲜的新手"]
- **Segment**：新用户 / 个人项目
- **Goals**：...
- **Frustrations**：...
- **Quote**："我就想试试好不好用..."

## 情感曲线（若适用）

| 阶段 | 情感 | 关键洞察 |
| --- | --- | --- |
| 下载注册 | 🟢 positive | ... |
| 首次配置 | 🔴 negative ← 流失高发 | ... |
| 完成第一个 X | 🟢 positive | ... |

## Top 痛点（按 severity × frequency 排序）

### 🥇 [pain 1]
- **描述**：...
- **严重度**：blocker
- **频次**：6/8
- **证据**：theme-1
- **推荐下一步**：`/工单分析` 大样本验证 / `/用户旅程` 标曲线 / `/HMW` 生成机会点

## 交叉验证建议

- **Signal 验证**：[主题 X] 建议在工单 / 评论里跑大样本验证
- **Bench 启发**：[痛点 Y] 建议参考 [竞品 Z] 是怎么解决的

## 下一步建议

- **Brief 接力**：把 JTBD 和 personas 写入 Brief 的"用户"段
- **Journey 接力**：用情感曲线骨架展开完整 Journey Map
- **HMW 接力**：每个 Top 痛点转化为 1-2 个 HMW 问题
- **Signal 验证**：8 人样本量有限，关键痛点建议跑大样本
```

#### 3.8 双通道 Context 输出

按 [chain-protocol.md](../../chain-protocol.md) §2.1 v1.1 智能适配规则：

**Step 1 — 写盘到 `spark-output/context/probe.json`**（必做）：

```json
{
  "skill": "probe",
  "generated_at": "<ISO8601>",
  "project_name": "...",
  "research_plan": {
    "goal": "...",
    "research_questions": ["..."],
    "method": "interview|usability-test|survey|card-sorting|diary-study|ab-test",
    "sample_size": 0,
    "recruitment_criteria": ["..."],
    "timeline": "..."
  },
  "interview_guide": {
    "warmup": ["..."],
    "context": ["..."],
    "deep_dive": ["..."],
    "reaction": ["..."],
    "wrapup": ["..."],
    "probes": ["..."],
    "bias_warnings": ["..."]
  },
  "participants": [
    {"id": "P1", "segment": "...", "background": "..."}
  ],
  "raw_notes": [
    {"participant_id": "P1", "timestamp": "...", "notes": "..."}
  ],
  "themes": [
    {
      "id": "theme-1",
      "name": "...",
      "frequency": 0,
      "emotional_intensity": "low|medium|high",
      "sample_quotes": ["..."],
      "related_segments": ["..."]
    }
  ],
  "jtbd": [
    {
      "id": "jtbd-1",
      "statement": "...",
      "context": "...",
      "outcome": "...",
      "evidence_theme_ids": ["theme-1"]
    }
  ],
  "personas": [
    {
      "id": "persona-1",
      "name": "...",
      "segment": "...",
      "goals": ["..."],
      "frustrations": ["..."],
      "quote": "..."
    }
  ],
  "emotional_curve": [
    {"stage": "...", "sentiment": "positive|neutral|negative", "evidence_theme_id": "theme-1"}
  ],
  "pain_points": [
    {
      "id": "pain-1",
      "description": "...",
      "severity": "blocker|major|minor",
      "frequency": 0,
      "evidence_theme_ids": ["theme-1"],
      "recommended_next_skill": "signal|journey|hmw|brief|audit"
    }
  ],
  "cross_validation_suggestion": {
    "signal_validation": ["..."],
    "bench_inspiration": ["..."]
  },
  "saturation": {
    "total_participants": 0,
    "themes_above_3": 0,
    "unique_themes_only_1": 0,
    "new_themes_in_last_2": true,
    "verdict": "saturated|near_saturated|not_saturated",
    "note": "..."
  }
}
```

**Step 2 — chat 输出紧凑 marker**：

```
<!-- spark-context:probe ref="spark-output/context/probe.json" -->
Probe 已保存：project=[name]，[N] 个参与者 → [M] 个主题 / [K] 条 JTBD / [P] 个 persona / [Q] 条痛点
<!-- /spark-context:probe -->
```

**降级 fallback**：若写盘失败，输出完整 JSON marker 作为唯一持久化通道。

### Handoff 提示（必输出）

> **协议**：按 [`_shared/next-skill.md`](../../_shared/next-skill.md) 三层结构模板输出；前 5 候选由 `_shared/skill-graph.json` 的依赖图算法实时算（done ⊆ ready，按 next_hint.preferred → alternatives → 同阶段 → anchor → fan-out 排序），优先建议从 `_shared/skill-graph.json#skills[id="probe"].next_hint` 读取。

**首行模板**：`✅ 用户研究 已完成，访谈整理出 persona + JTBD + 情感曲线。`

**本 Skill 的 `next_hint`**（来自 skill-graph.json，**不可在此 SKILL.md 内硬编码覆盖**）：

- **preferred**：`/brief`
- **优先理由**：JTBD / persona / 情感曲线已沉淀，进 Brief 把洞察转策略最直接。
- **alternatives**：`/journey` (想直接画用户旅程把痛点可视化)
- **emoji**：👥

**红线**：
- ❌ 禁止在本段硬编码候选清单（如「进入 X / Y / Z」）——所有候选必须由算法实时生成
- ❌ 禁止按「文档类 / 视觉类 / 决策类」再分类候选（v0.5.5 起，分类已折叠进 next_hint.alternatives）
- ❌ 禁止与「更新链路面板」段合并——两段必须各自独立成段，中间空一行
- ❌ 禁止漏第 2 行候选清单——即使候选只有 1 个、或为空（终端节点）也要写出来

---

## 质量标准

1. **每条洞察都有证据链**：theme 必须有 quote + frequency + emotional_intensity，不能只是 AI 总结的话
2. **JTBD 用标准句式**：当 [context]，我想 [job]，让我能 [outcome] —— 不要写成"用户希望 X"
3. **Persona 按行为分**：不按人口属性（年龄 / 性别）分，按"产品里的行为和动机"分
4. **样本量 < 5 标"早期信号"**：5 人以下的访谈结果不能称为"洞察"，只能称为"早期信号 / 假设"
5. **反偏见提示必须出现在访谈大纲里**：bias_warnings 字段不能省略
6. **明确推荐下一步 Skill**：每条痛点都要标 recommended_next_skill，让用户知道接下来该做什么
7. **不替代量化研究**：8 人样本不能下"X% 的用户认为"这种量化结论 —— 只能说"8 人中有 6 人提到"
8. **饱和度判读必须出现**：Synthesize 阶段必须输出饱和度评估表 + 三档判断（saturated / near_saturated / not_saturated），不能跳过

## 红线规则

1. **不编造 quote**：所有 sample_quotes 必须来自真实访谈纪要，禁止 AI 生成 / 改写
2. **不下"用户都 X"的结论**：8 人样本不能代表全体用户 —— 用"访谈样本中 N/M 人提到"的具体频次
3. **不替代专业用研团队**：复杂研究（如大规模定量、跨文化研究、敏感人群研究）建议找专业用研
4. **不让用户预测自己的行为**："你会用 X 功能吗"这种问题答案不可靠 —— 改问"过去你怎么解决类似问题"
5. **不忽略小样本的早期信号**：1-2 人提到的极端体验（如崩溃 / 数据丢失）也要记录，不能因为频次低就埋没
6. **不替代可用性测试的真实操作观察**：Probe 整理访谈记录，但不能替代亲眼观察用户的实际操作

---

## 输入不足处理

- **用户说"我想访谈但不知道问什么"**：从 frame / scope / 用户目的出发，先生成 5 个研究问题再展开大纲
- **用户没有 frame / scope**：先问 3 个最小问题（"想研究什么 / 用户是谁 / 想搞清楚什么"），再启动 Plan
- **用户已有访谈记录但没整理**：跳过 Plan / Conduct，直接进 Synthesize；要求用户提供原始记录（文本 / 转录 / 笔记）
- **样本量过少（< 3 人）**：明确告知"这是探索性信号，不是可靠洞察"，建议补访谈或转用 Signal
- **跨语言访谈**：分语言归纳主题，跨语言聚类时标"语言文化差异"

---

## 实操注意事项

### 与 Signal 的协作节奏

**理想流程**：先 Probe（5-8 人深挖根因）→ 再 Signal（验证根因是否在大样本里高频）→ 一致 → 高置信度洞察。

**反向也可**：先 Signal（大样本发现高频痛点）→ 再 Probe（5-8 人挖根因 / 场景）→ 互补完整画像。

### 与 Journey 的协作节奏

Probe 输出的 `emotional_curve` 是 Journey Map 的骨架 —— Journey 可以直接读取展开成完整旅程图，不需要重新做用户研究。

### 与 HMW 的协作节奏

Probe 的每个 pain_point 都能转 1-2 个 HMW 问题（"How might we 解决 [痛点描述]，让 [persona name] 能 [JTBD outcome]"）。

### 时间投入建议

| 研究类型 | 时间投入 |
| --- | --- |
| 仅做 Plan（设计研究方案） | 2-4 小时 |
| 仅做 Conduct（设计访谈大纲） | 1-2 小时 |
| 仅做 Synthesize（整理 5-8 人访谈） | 半天到 1 天 |
| 全流程（Plan + Conduct + Synthesize） | 2-4 周（含招募 + 执行 + 整理） |

### 样本量建议

| 研究目的 | 推荐样本 | 说明 |
| --- | --- | --- |
| 探索性深访 | 5-8 人 | Nielsen 经典结论：5 人能发现 ~85% 可用性问题 |
| 可用性测试 | 5-8 人 / 每 segment | 每个 segment 至少 5 人 |
| 调研问卷 | 100+ 人 | 需要统计显著性 |
| 卡片分类 | 15-30 人 | IA 决策 |

---

## 已知限制

- **AI 不能替你做访谈**：Probe 提供大纲 + 整理方法，访谈执行需要真人面对面
- **小样本结论有偏差**：5-8 人不代表全体用户，关键决策必须跑 Signal 大样本或定量调研验证
- **AI 整理依赖原始记录质量**：raw_notes 太简略时，主题归纳会粗糙；建议访谈时尽量记录原话
- **不替代真实可用性测试观察**：可用性测试的价值在"看用户实际操作"，纯文字记录会丢失行为信号
- **不替代专业用研团队**：跨文化研究 / 敏感人群（儿童 / 病患）/ 大规模定量需要专业资源
- **JTBD / persona 提炼带主观性**：AI 给的归纳仅供参考，关键洞察建议团队 review
