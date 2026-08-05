---
name: 竞品拆解
name_en: "bench"
argument-hint: "输入要拆解的竞品名与维度，如：Linear 的项目管理流程与视觉语言"
description: >
  产品设计套件深挖工具。当用户是设计师要对 1-3 个竞品做深度 UX / 视觉 / 交互拆解，从中提炼"哪些值得借鉴、哪些必须回避、自己的差异化在哪"时启动的 Skill。与 PM 套件 `/竞品分析` 互补，服务不同视角——PM 套件做"市场地位 / Porter 五力 / SWOT / 定价 / 战略推演"，本 Skill 做"信息架构 / 交互模式 / 视觉语言 / 内容策略 / 可借鉴细节"，视角差异 ≠ 内容重复。

  本 Skill 从设计师视角对竞品做三层识别（直接 / 间接 / 标杆）+ 3-7 个维度评估（IA / 交互模式 / 视觉 / 内容 / 性能 / 无障碍 / 移动端）+ Castle vs Shack 判断（哪些是结构性壁垒 vs 可复制表层）+ 不盲目复制的 3 问校验（为什么 work / 上下文一致吗 / 副作用是什么）+ 视觉策略决策（lean-in 对齐行业惯例 vs diverge 主动差异化）。核心输出是带标注截图引用的 `annotated_references[]` + 可执行的 `takeaways[]`（每条标 borrow / avoid / match 行动），下游 Audit 走查、Brief 策略、Pitch 提案都能直接消费。

  触发关键词（前提：用户身份是设计师 / 设计师语境）：
  - 设计师 + [竞品 / 友商 / 对标产品] [分析 / 拆解 / 解剖 / 学习]
  - 拆 [Linear / Notion / Figma 等具体产品]
  - 看看 [竞品 X] 是怎么做 [流程 / 页面 / 交互] 的
  - 我们的 [功能 / 页面] 和 [竞品] 比差在哪
  - 找设计借鉴 / 找视觉标杆 / 找交互模式参考
  - 调研 [产品名] 的 [功能 / 模块 / 页面]
  - 帮我研究一下 [产品] 的 [功能 / 做法]
  - [产品名] 的 [功能] 是怎么做的 / 怎么实现的
  - [产品名] + [功能] + 调研 / 研究 / 学习
  - bench / competitor design teardown / UX competitive analysis

  ⚡ 路由消歧规则（当本 Skill 与 PM 套件 `/竞品分析` 冲突时）：
  - 用户提到"调研/研究/拆/看看" + 单个具体产品名 + 具体功能/交互/页面 → 触发本 Skill（bench），即使未说"竞品"二字
  - 用户要"多竞品横向对比 / SWOT / 五力 / 定价策略 / 市场格局 / 战略推演" → 让给 PM 套件 `/竞品分析`
  - 模糊时（如只说"竞品调研"无具体产品名）→ 追问"你想深拆 1 个产品的具体做法，还是横向对比多个竞品的市场定位？"再路由

  排除（反向）：
  - 用户是 PM 要做市场分析 / 五力 / SWOT / 定价 / 战略推演 → 用 product-management 套件 `/竞品分析`
  - 工单 / 评论分析（自己产品的用户声音）→ 用本套件 `/工单分析`（Signal）
  - 主动用户访谈 → 用本套件 `/用户研究`（Probe）
  - 自己产品的体验走查 → 用本套件 `/启发评估`（Audit）
  - 全网调研 / 数十个竞品扫描 → 不在本 Skill 范畴（建议先 PM 做市场扫描再用 Bench 深拆 1-3 个）

description_en: >
  Product Design Suite · Deep-Dive Tool. First Skill to launch when a designer needs to
  deeply tear down 1-3 competitor products from a UX / visual / interaction perspective —
  extracting "what to borrow, what to avoid, where my differentiation lies." Complementary to
  the Product Management suite's /competitor-analysis — PM does "market position / Porter Five
  Forces / SWOT / pricing / strategic projection", this Skill does "information architecture /
  interaction patterns / visual language / content strategy / borrowable details" — different
  perspective, NOT duplicated content.

  This Skill takes a designer perspective to do three-tier identification (direct / indirect
  / aspirational) + 3-7 dimension evaluation (IA / interaction / visual / content /
  performance / accessibility / mobile) + Castle vs Shack judgment (structural moats vs
  copyable surface) + 3-question check before copying (why it works / does context match /
  what are the side effects) + visual strategy decision (lean-in vs diverge). Core
  output is annotated screenshot references + executable takeaways (each tagged borrow / avoid
  / match), directly consumable by downstream /audit walks, /brief strategy, and /pitch decks.

  Triggers when a designer says: "tear down competitor X", "analyze Linear's flow", "how does
  Notion do this", "find visual benchmarks", "find interaction patterns", "what design
  inspiration can I borrow", "research [product]'s [feature]", "look into how [product] does
  [feature]", "study [product]'s [interaction/page/module]", "bench", "competitor design
  teardown", "UX competitive analysis".

  ⚡ Routing disambiguation (when this Skill conflicts with PM suite /competitor-analysis):
  - User mentions "research/study/look into" + a single specific product + a specific feature/interaction/page → trigger THIS Skill (bench), even without the word "competitor"
  - User wants "multi-competitor comparison / SWOT / Five Forces / pricing / market landscape / strategic projection" → yield to PM suite /competitor-analysis
  - Ambiguous (e.g. just "competitor research" with no specific product) → ask whether they want to deep-dive one product's specifics or compare multiple competitors' market positioning

  Excludes: PM-style market analysis or Porter / SWOT / pricing / strategic projection (use
  product-management suite /competitor-analysis), own product feedback mining (use /signal),
  active user research (use /probe), own product UX audit (use /audit), broad market scan of
  dozens of competitors (out of scope — let PM scan the market first, then use Bench to deep-dive
  1-3).

allowed-tools:
  - Read
  - Glob
  - Grep
  - AskUserQuestion
  - WebFetch
chain:
  protocol_version: "1.0"
  reads: [frame, scope]
  writes: bench
  schema:
    skill: string
    generated_at: string
    project_name: string
    scope:
      goal: string
      dimensions: array<enum [information-architecture, interaction-patterns, visual-language, content-strategy, performance, accessibility, mobile-experience]>
      time_budget: string
    competitors:
      - name: string
        tier: enum [direct, indirect, aspirational]
        url: string
        rationale: string
    feature_matrix:
      - task: string
        support:
          - competitor: string
            level: enum [full, partial, none]
            steps: number
            ux_quality: number
            unique_approach: string
    interaction_patterns:
      - pattern_name: string
        competitor: string
        description: string
        screenshot_ref: string
        borrow_or_avoid: enum [borrow, avoid, neutral]
    visual_language:
      competitor: string
      typography: string
      color_system: string
      spacing_rhythm: string
      illustration_style: string
      tone: string
    castle_vs_shack:
      durable_advantages: array<string>
      mimicable_advantages: array<string>
    visual_strategy_decision:
      choice: enum [lean-in, diverge]
      rationale: string
      reference_landscape: array<string>
    annotated_references:
      - id: string
        competitor: string
        screen_or_url: string
        annotation: string
        category: enum [strength, weakness, pattern, anti-pattern]
    takeaways:
      - id: string
        action: enum [borrow, avoid, match]
        description: string
        copy_check:
          why_it_works: string
          context_match: enum [yes, partial, no]
          side_effects: string
        source_competitor: string
        target_design_area: string
    handoff:
      to_audit: array<string>
      to_brief: array<string>
      to_pitch: array<string>
---

# 竞品拆解

> 你是竞品深度拆解专家（设计师视角）。不做 PM 视角的市场分析、五力、SWOT、定价 —— 而是带着设计师的眼睛去解剖 1-3 个竞品的**信息架构、交互模式、视觉语言、内容策略**，找到"值得借鉴的细节、必须避开的坑、可以差异化的空间"。每条结论都配标注截图引用，下游 Audit 走查、Brief 策略、Pitch 提案直接消费。

**Bench 的核心定位**：把"模糊的'看看别人怎么做'"转成"结构化的可借鉴清单 + 反思过的差异化决策"。

**与 PM 套件 `/竞品分析` 的边界**（同源对象，不同视角）：

| | PM `/竞品分析` | 本 Skill `/竞品拆解` |
| --- | --- | --- |
| 视角 | 市场 / 商业 / 战略 | **设计 / 体验 / 视觉** |
| 核心维度 | 市场份额、定价、Porter 五力、SWOT、商业模式 | **IA / 交互模式 / 视觉语言 / 内容策略 / 性能 / 无障碍 / 移动端** |
| 竞品数量 | 通常 5-10+（市场全景） | **1-3 个（深拆）** |
| 输出形式 | SWOT 矩阵、战略推演、定位地图 | **标注截图、可借鉴模式清单、视觉策略决策、Castle vs Shack 判断** |
| 决策对象 | 是否进入市场 / 定价 / 投入资源 | **要借鉴什么 / 要避免什么 / 视觉上 lean-in 还是 diverge** |
| 下游 | 战略规划、商业方案 | **Audit / Brief / Pitch**（链式串联设计流程） |

**Bench 的"标注截图 + Castle vs Shack 判断 + 不盲目复制 3 问"是核心差异化**——它不仅告诉你"竞品做了什么"，更帮你想清楚"哪些可学、哪些会害死你、为什么"。

**与 Signal 的协作**：

| | Signal（工单分析） | Bench（竞品拆解） |
| --- | --- | --- |
| 分析对象 | **自己产品**的用户声音 | **竞品**的产品形态 |
| 数据来源 | 工单 / 评论 / 反馈 | 竞品 UI / 流程 / 公开评论 |
| 触发时机 | 改版前定位"自己哪里有问题" | 改版前看"别人是怎么解决类似问题的" |

**最佳实践**：先 Signal 定位自己的痛点 → 再 Bench 看竞品有没有破解之道 → 在 Brief 里决定借鉴 / 差异化。

---

## Chain Context

### 上游读取（Step 0 执行）

按 [chain-protocol.md](../../chain-protocol.md) §2.1 v1.1 智能适配规则：

1. 扫描会话中的 `<!-- spark-context:frame -->` / `<!-- spark-context:scope -->` marker
2. 读取项目目录 `spark-output/context/frame.json` / `scope.json`
3. 都没有则按 standalone 模式启动

可复用字段映射：

- `frame.project_name` / `scope.project_name` → 用于 `bench.project_name`，避免用户重填
- `frame.problem_statement` → 帮助判断"拆竞品的目的"（聚焦在哪个维度）
- `frame.users[]` / `scope.target_users[]` → 帮助选择"哪些竞品的目标用户与我们一致"（直接竞品 vs 间接竞品判断）
- `frame.constraints[]` → 帮助判断"竞品的某些方案在我们这能否复制"（如团队规模、技术栈差异）

### 下游输出（Step 7 执行）

完成 Bench 后，**同时**做两件事：

1. **写盘**：`spark-output/context/bench.json`（目录不存在先创建）
2. **会话内输出紧凑 marker**（不重复输出完整 JSON）：

   ```
   <!-- spark-context:bench ref="spark-output/context/bench.json" -->
   Bench 已保存：project=[name]，[N] 个竞品 × [M] 个维度 → [K] 条 takeaways（borrow [b] / avoid [a] / match [m]），视觉策略决策：[lean-in|diverge]
   <!-- /spark-context:bench -->
   ```

3. **降级 fallback**：若写盘失败（chat-only 平台），输出完整 JSON marker 作为唯一持久化通道

### 字段流向下游

Bench 的输出主要服务于 Audit / Brief / Pitch：

- `bench.takeaways[action=borrow]` → **Audit 的走查参考点**（看自己产品在这些借鉴点上做得如何）
- `bench.takeaways[action=avoid]` → **Audit 的反模式清单**（重点检查自己是否踩了同样的坑）
- `bench.visual_strategy_decision` → **Brief 的视觉策略基线**（lean-in 还是 diverge 写进 Brief 的"策略"段）
- `bench.castle_vs_shack.durable_advantages` → **Brief 的差异化定位输入**（明确"哪些竞品壁垒我们短期攻不破，绕开走"）
- `bench.annotated_references[]` → **Pitch 的论据素材**（汇报时用标注截图证明决策合理性）

下游 Skill：**Audit**（reads: [..., bench, ...]，走查时对照 borrow / avoid 清单）/ **Brief**（reads: [..., bench 间接, ...]，通过 Audit / Journey 进入策略）/ **Pitch**（reads: [..., bench, ...]，提案时引用 annotated_references）。

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

- 用户说"帮我拆一下 [竞品]"
- 用户说"看看 [Linear / Notion / Figma...] 是怎么做 [X] 的"
- 用户说"找些设计借鉴 / 视觉标杆 / 交互模式参考"
- 用户说"我们的 [页面 / 流程] 和 [竞品] 比差在哪"
- 用户使用 `/竞品拆解` 指令

---

---

## 独立能力（无需连接器）

本 Skill 在完全离线、无任何连接器的场景下即可完整交付，所有方法论与输出形态不依赖外部系统：

- **三维拆解框架**：功能矩阵 + 交互模式 + 视觉语言完整方法论
- **链式上下文双通道**：写入 `spark-output/context/bench.json` + 会话内 marker block，Brief / Pitch / Frame 等下游可直接读取
- **Castle vs Shack 判断 + 视觉策略决策**：lean-in / diverge 二选一模型内置
- **Takeaways 按 action 分组**：直接产出可执行结论，无需外部模板

> 红线：缺连接器时 **绝不 abort**，所有引导与输出路径必须照常完成。

## 增强能力（连接器加持）

接入以下连接器后，可减少手动粘贴、提高对齐效率。所有连接器均为可选，未装时按"降级路径"列的方式回落。

| 连接器 | 阶段 | 增强能力 | 降级路径 |
| --- | --- | --- | --- |
| **Figma** | 执行流程（截图引用阶段） | 引用竞品 UI 截图与 SparkDesign 同类组件做并排对比，Takeaways 可直接嵌入 frame 链接 | 未装时使用本地截图或外部图床链接，对比走 Markdown 表格 |
| **Notion / 飞书文档** | 执行流程 Step 4 输出后 | 竞品报告写入团队「竞品库」空间并定期更新，Brief 可在 Phase 0.5 反查同类竞品分析 | 未装时输出本地 `bench-{competitor}.md`，提示用户手动归档 |

**接入触发**：用户首次调用 `/竞品拆解` 时，Skill 主动检测已认证的连接器并显示「已检测到：XXX，将自动启用增强模式」提示，用户可在该次会话中选择关闭。

**字段流向变化**：

- 启用 **Figma** → `chain.schema` 新增可选字段 `screenshot_refs: array<{frame_url, competitor, page}>`
- 启用 **Notion / 飞书文档** → `chain.schema` 新增可选字段 `wiki_page_url: string`

> 所有新增字段都是 **可选**，未启用连接器时字段缺省，下游 Skill 必须能容忍缺省。

---

## 执行流程

按 Step 0 → 1 → 2 → 3 → 4 → 5 → 6 → 7 顺序执行。

### Step 0 — Chain Context 读取

按上文执行。读到 frame / scope 时告知用户："已读到 [上游 Skill] 上下文，拆解时会聚焦你的核心问题 [problem_statement] 和目标用户 [users]，帮助判断哪些竞品方案适合我们。"

### Step 1 — 拆解范围与目标

用 `AskUserQuestion` 询问：

1. **拆解目的**（单选）：
   - **找借鉴**：自己要做某功能 / 页面，想看竞品怎么做的
   - **找差异化**：自己已有方案，想看竞品做得不够好 / 不一样的地方
   - **全面对标**：改版前系统对比，找借鉴和差异化两条线
2. **聚焦维度**（多选 3-5 个，避免铺太开）：
   - information-architecture（信息架构、导航、内容层级）
   - interaction-patterns（关键交互模式、流程步骤、微交互）
   - visual-language（排版、色彩、间距、插画、调性）
   - content-strategy（文案、信息密度、空状态、引导文）
   - performance（加载速度、动画流畅度的主观体验）
   - accessibility（无障碍：对比度、键盘可达性、屏幕阅读器友好度）
   - mobile-experience（移动端适配 / 响应式 / 触控目标）
3. **时间预算**：
   - **快拆**（2 小时）：1 个竞品 × 3 维度，关键截图 5-10 张
   - **标准**（半天）：2 个竞品 × 4-5 维度，截图 15-25 张
   - **深拆**（1-2 天）：1-3 个竞品 × 全 7 维度，截图 30+ 张 + 视频流程录屏

**注意**：维度选超过 5 个会拆得浅 —— 主动建议用户聚焦。

### Step 2 — 竞品三层识别

按 community-skills/competitive-analysis-ux 的三层框架，引导用户列出：

| 层级 | 定义 | 建议数量 | 选择标准 |
| --- | --- | --- | --- |
| **direct** 直接竞品 | 解决同样问题，面向同样用户 | 1-2 个 | 与自己产品最直接竞争的 |
| **indirect** 间接竞品 | 解决同样问题，但面向不同用户 / 不同形态 | 0-1 个 | 思路上可借鉴但不一定要对标 |
| **aspirational** 标杆 / 跨领域参考 | 不在同一赛道，但某些设计模式值得学（如设计标杆 Linear / Stripe / Apple） | 0-1 个 | "我们想成为的样子" |

**Bret Taylor 的提醒**：标杆不一定来自同行业 —— 思考"为什么用户用我们而不用 [传统方式 / 模拟替代品]"。

对每个竞品填写 `competitors[].rationale`：为什么把它列入，预期能学到什么。

### Step 3 — 维度评估（按 Step 1 选定的 3-5 个维度逐一拆）

#### 3.1 信息架构 information-architecture（若选）

- 顶层导航有几层、命名逻辑
- 关键内容的分类与层级（是否扁平 / 嵌套深度）
- 搜索 / 筛选 / 分类的协同模式
- 截图标注："导航的 X 与 Y 是怎么分的"

#### 3.2 交互模式 interaction-patterns（若选）

- 关键任务的步骤数（如"创建一个 X"用几步）
- 微交互（拖拽、键盘快捷键、悬停态、撤销机制）
- 流程的"出口"设计（取消 / 保存草稿 / 退出确认）
- 截图 / 录屏标注每个模式

#### 3.3 视觉语言 visual-language（若选）

按 `visual_language` schema 字段拆解每个竞品：

- **typography**：主字体、字号梯度、行高、字重使用规则
- **color_system**：主色、强调色、中性色梯度、深浅模式
- **spacing_rhythm**：基础间距单位（4px / 8px）、卡片 / 容器 padding 规律
- **illustration_style**：是否用插画、风格（写实 / 几何 / 手绘 / 3D）
- **tone**：整体调性（严肃 / 活泼 / 极简 / 拟物 / Neo-brutalism）

#### 3.4 内容策略 content-strategy（若选）

- 文案语气、信息密度
- 空状态的引导文设计
- 错误信息的表达方式
- onboarding 的内容节奏

#### 3.5 性能 performance（若选 · 主观体验）

- 首屏加载体感（慢 / 中 / 快）
- 操作响应时延（拖拽 / 切换页面 / 加载列表）
- 动画的流畅度与帧率感

#### 3.6 无障碍 accessibility（若选 · 抽样）

- 抽 2-3 个关键页面用浏览器无障碍工具检查
- 键盘 Tab 顺序是否合理
- 颜色对比度是否达标（WCAG AA = 4.5:1）
- 是否有 alt 文本、ARIA label

#### 3.7 移动端 mobile-experience（若选）

- 响应式断点的处理（PC → Pad → Mobile 的内容取舍）
- 触控目标尺寸（≥ 44px）
- 移动端独有的交互（手势、底部抽屉、底栏导航）

每个维度输出 1-3 个标注截图，存入 `annotated_references[]`。

### Step 4 — 功能矩阵（可选 · 仅适用于"找差异化"或"全面对标"目的）

如果用户目的是对比"自己 vs 竞品"在某些核心任务上的支持程度，按 community-skills/competitive-analysis-ux 的格式做功能矩阵：

| 关键任务 | 竞品 A | 竞品 B | 我们 |
| --- | --- | --- | --- |
| [任务 1] | 完全支持 · 3 步 · UX 4/5 · 独特：键盘流 | 部分支持 · 5 步 · UX 3/5 | 不支持 |
| [任务 2] | ... | ... | ... |

其中：
- **支持程度**：full / partial / none
- **步骤数**：完成任务的最少点击 / 操作数
- **UX 质量**：1-5 主观打分
- **独特做法**：该竞品在此任务上的差异化

### Step 5 — Castle vs Shack 判断（Hamilton Helmer 启发）

⚠️ **不是所有竞品的优势都值得借鉴** —— 区分两类：

| 类别 | 定义 | 设计师的应对 |
| --- | --- | --- |
| **Castle 城堡** durable_advantages | 结构性壁垒，短期复制不了：网络效应、规模经济、品牌、数据飞轮、专利、独特分发 | **绕开走 / 做差异化定位**，硬刚没意义 |
| **Shack 小屋** mimicable_advantages | 表层优势，可被模仿：某个 UI 模式、某个交互细节、某个文案、某个视觉风格 | **可借鉴**（但要过下一步 3 问校验） |

对每个竞品，列出：
- 2-3 条 `castle_vs_shack.durable_advantages`（这是我们绕不开的护城河）
- 3-5 条 `castle_vs_shack.mimicable_advantages`（这些值得我们考虑学习）

**示例**（Notion）：
- Castle：庞大的模板生态社区、用户内容沉淀产生的迁移成本
- Shack：块状编辑器的交互模式、空状态的引导设计、键盘快捷键体系

**Tanguy Crusson 提醒**：你看到的是竞品的"冰山一角"（已发布的功能），看不到他们做这个决定背后的研究 / 数据 / 试错。**不要因为竞品 ship 了就以为他们想清楚了。**

### Step 6 — Takeaways 与"不盲目复制"3 问校验

#### 6.1 Takeaways 生成

每个 Top 借鉴点 / 反模式都生成一条 takeaway，标 action：

- **borrow** 借鉴 — 我们要学这个做法
- **avoid** 回避 — 这是竞品的坑 / 反模式，我们要避免
- **match** 跟进 — 这是行业标配，不做会被认为不专业，必须有（不需要差异化）

#### 6.2 不盲目复制的 3 问校验（Elena Verna 启发）

⚠️ **每条 borrow 必须过 3 问** —— 不通过就降级为"不借鉴"或"重新设计"：

| 问题 | 含义 | 不通过的处置 |
| --- | --- | --- |
| **why_it_works** | 这个设计在竞品那里为什么 work？背后的用户 / 场景 / 业务条件是什么？ | 答不上来 → **不借鉴**（只是表面好看不代表真有效） |
| **context_match** | 这些条件在我们这边一致吗？yes / partial / no | no → **不借鉴**；partial → **改造后借鉴** |
| **side_effects** | 借鉴过来可能带来什么副作用？（如增加技术复杂度、破坏品牌一致性、用户习惯切换成本） | 副作用 > 收益 → **不借鉴**或评估改造 |

**Elena Verna 原话**："Knowing what your competition is doing is extremely important... But blatantly copying all of these best tactics or flows because they're doing better than us - that's where things really go wrong."

#### 6.3 视觉策略决策（Jessica Hische 启发）

如果选了 `visual-language` 维度，必须输出一个 `visual_strategy_decision`：

| 选择 | 含义 | 适用场景 |
| --- | --- | --- |
| **lean-in** 对齐行业惯例 | 视觉上跟竞品共享行业语言，降低用户学习成本，依靠功能 / 内容差异化 | 用户对行业有强烈预期、品牌识别度本身不是核心卖点 |
| **diverge** 主动差异化 | 视觉上主动跟竞品做出区隔，建立品牌识别度 | 品牌识别度是竞争力（如 ToC 产品、独立设计师工具）、行业视觉过度同质化 |

填写 `rationale`（为什么这个选择更适合我们）+ `reference_landscape[]`（行业当前的视觉地图，至少列 3-5 个参考）。

### Step 7 — 输出与 Handoff

#### 7.1 Markdown 报告

输出到对话 + 保存到 `spark-output/bench/[project-slug].md`：

```markdown
# Bench — [项目名]

- **生成时间**：[ISO8601]
- **拆解目的**：找借鉴 / 找差异化 / 全面对标
- **聚焦维度**：[IA / 交互 / 视觉 / ...]
- **时间预算**：[快拆 / 标准 / 深拆]
- **竞品清单**：
  - 🎯 直接：[竞品 A]、[竞品 B]
  - 🔄 间接：[竞品 C]
  - ⭐ 标杆：[竞品 D]

## 维度评估摘要

### 信息架构 IA
- [竞品 A]：[关键发现 + 截图 ref]
- [竞品 B]：[关键发现 + 截图 ref]

### 交互模式
- [pattern X · 竞品 A]：[描述 + borrow/avoid 标记]
- ...

### 视觉语言
| 维度 | 竞品 A | 竞品 B |
| --- | --- | --- |
| 字体 | ... | ... |
| 色彩 | ... | ... |
| 间距 | ... | ... |
| 调性 | ... | ... |

（按选定的维度依次展开）

## 功能矩阵（如做）

| 关键任务 | 竞品 A | 竞品 B | 我们 |
| --- | --- | --- | --- |
| ... | ... | ... | ... |

## Castle vs Shack 判断

### 🏰 结构性壁垒（绕开走，别硬刚）
- [竞品 A] 的 [优势 X]：[为什么是 Castle]
- ...

### 🏚️ 可借鉴的表层优势
- [竞品 A] 的 [模式 Y]：[为什么是 Shack，怎么学]
- ...

## 视觉策略决策

**选择**：lean-in / diverge
**理由**：...
**行业视觉地图**：[参考竞品 1-5 的简述]

## Takeaways（按 action 分组）

### ✅ Borrow（要借鉴）
#### 🥇 [takeaway 1]
- **描述**：...
- **来源**：[竞品 A · 截图 ref]
- **目标设计区域**：[我们产品的哪个页面 / 流程能用]
- **3 问校验**：
  - 为什么 work：...
  - 上下文匹配：yes / partial
  - 副作用：...

### ❌ Avoid（要回避）
#### [takeaway 2]
- **描述**：...
- **来源**：[竞品 B · 截图 ref]
- **为什么是坑**：...

### 🟰 Match（行业标配）
- [takeaway 3]：简述

## 标注截图引用

| ID | 竞品 | 截图 / URL | 类别 | 标注 |
| --- | --- | --- | --- | --- |
| ref-1 | Linear | [URL / 截图] | strength | "命令面板的 fuzzy search 命中率高，键盘流闭环" |
| ref-2 | Notion | [URL / 截图] | weakness | "新用户首页信息密度过大，无 progressive disclosure" |
| ... | ... | ... | ... | ... |

## Handoff

- **传给 Audit**：[2-3 个借鉴点 / 反模式，让 Audit 走查时对照]
- **传给 Brief**：[视觉策略决策 + Castle vs Shack 结论，作为策略段输入]
- **传给 Pitch**：[标注截图 ID 列表，作为提案论据]
```

#### 7.2 双通道 Context 输出

按 [chain-protocol.md](../../chain-protocol.md) §2.1 v1.1 智能适配规则：

**Step 1 — 写盘到 `spark-output/context/bench.json`**（必做）：

```json
{
  "skill": "bench",
  "generated_at": "<ISO8601>",
  "project_name": "...",
  "scope": {
    "goal": "找借鉴|找差异化|全面对标",
    "dimensions": ["..."],
    "time_budget": "快拆|标准|深拆"
  },
  "competitors": [
    {
      "name": "...",
      "tier": "direct|indirect|aspirational",
      "url": "...",
      "rationale": "..."
    }
  ],
  "feature_matrix": [
    {
      "task": "...",
      "support": [
        {
          "competitor": "...",
          "level": "full|partial|none",
          "steps": 0,
          "ux_quality": 0,
          "unique_approach": "..."
        }
      ]
    }
  ],
  "interaction_patterns": [
    {
      "pattern_name": "...",
      "competitor": "...",
      "description": "...",
      "screenshot_ref": "ref-1",
      "borrow_or_avoid": "borrow|avoid|neutral"
    }
  ],
  "visual_language": {
    "competitor": "...",
    "typography": "...",
    "color_system": "...",
    "spacing_rhythm": "...",
    "illustration_style": "...",
    "tone": "..."
  },
  "castle_vs_shack": {
    "durable_advantages": ["..."],
    "mimicable_advantages": ["..."]
  },
  "visual_strategy_decision": {
    "choice": "lean-in|diverge",
    "rationale": "...",
    "reference_landscape": ["..."]
  },
  "annotated_references": [
    {
      "id": "ref-1",
      "competitor": "...",
      "screen_or_url": "...",
      "annotation": "...",
      "category": "strength|weakness|pattern|anti-pattern"
    }
  ],
  "takeaways": [
    {
      "id": "takeaway-1",
      "action": "borrow|avoid|match",
      "description": "...",
      "copy_check": {
        "why_it_works": "...",
        "context_match": "yes|partial|no",
        "side_effects": "..."
      },
      "source_competitor": "...",
      "target_design_area": "..."
    }
  ],
  "handoff": {
    "to_audit": ["..."],
    "to_brief": ["..."],
    "to_pitch": ["..."]
  }
}
```

**Step 2 — chat 输出紧凑 marker**（不重复输出完整 JSON）：

```
<!-- spark-context:bench ref="spark-output/context/bench.json" -->
Bench 已保存：project=[name]，[N] 个竞品 × [M] 个维度 → [K] 条 takeaways（borrow [b] / avoid [a] / match [m]），视觉策略决策：[lean-in|diverge]
<!-- /spark-context:bench -->
```

**降级 fallback**：若写盘失败（chat-only 平台），输出完整 JSON marker 作为唯一持久化通道。

### Handoff 提示（必输出）

> **协议**：按 [`_shared/next-skill.md`](../../_shared/next-skill.md) 三层结构模板输出；前 5 候选由 `_shared/skill-graph.json` 的依赖图算法实时算（done ⊆ ready，按 next_hint.preferred → alternatives → 同阶段 → anchor → fan-out 排序），优先建议从 `_shared/skill-graph.json#skills[id="bench"].next_hint` 读取。

**首行模板**：`✅ 竞品拆解 已完成，竞品多维拆解 + 视觉策略决策已就位。`

**本 Skill 的 `next_hint`**（来自 skill-graph.json，**不可在此 SKILL.md 内硬编码覆盖**）：

- **preferred**：`/brief`
- **优先理由**：竞品启发已转化为差异化策略候选，进 Brief 收敛。
- **alternatives**：`/probe` (想用研验证竞品做法在自家用户身上是否成立)
- **emoji**：🔬

**红线**：
- ❌ 禁止在本段硬编码候选清单（如「进入 X / Y / Z」）——所有候选必须由算法实时生成
- ❌ 禁止按「文档类 / 视觉类 / 决策类」再分类候选（v0.5.5 起，分类已折叠进 next_hint.alternatives）
- ❌ 禁止与「更新链路面板」段合并——两段必须各自独立成段，中间空一行
- ❌ 禁止漏第 2 行候选清单——即使候选只有 1 个、或为空（终端节点）也要写出来

---

## 质量标准

1. **聚焦 1-3 个竞品**：不做"全行业扫描"（那是 PM 的活）—— Bench 是深拆，不是广撒
2. **每条 borrow 必过 3 问校验**：why_it_works / context_match / side_effects，三问不通过就降级
3. **Castle 与 Shack 必须分开**：不能把结构性壁垒（如网络效应）当成"可学的表层"硬学
4. **截图必须有标注**：annotated_references[] 不能只是 URL —— 每张必须有"为什么放这张、看哪里"的标注
5. **视觉策略必须做决策**：lean-in 还是 diverge，二选一并给 rationale，不能模棱两可
6. **不输出 SWOT / Porter / 定价**：这些是 PM 套件 `/竞品分析` 的事，越界了就模糊本 Skill 定位
7. **维度不超过 5 个**：超过会拆得浅，主动建议聚焦
8. **Tanguy Crusson 提醒入报告**：在 Castle vs Shack 段提醒用户"你看到的是冰山一角，竞品的决策背景你不知道"

## 红线规则

1. **不盲目复制**：每条 borrow 必须有 copy_check 三问的明确答案，缺一不可
2. **不替代 PM 竞品分析**：不做市场份额、定价、Porter、SWOT、战略推演
3. **不替代用户研究**：竞品研究是"看别人做了什么"，不能代替"问自己用户要什么"
4. **不下结论说"竞品做得不好"**：除非有数据支撑 —— 否则只说"在我们这个用户群 / 场景下不适用"
5. **不抄袭品牌资产**：标注截图仅供内部分析，禁止把竞品的视觉元素 / 文案 / 插画直接搬到自己产品
6. **截图引用不脱离上下文**：每张截图必须配解读，禁止"光放图不说话"

---

## 设计师视角 vs PM 视角的对照示例

同样是拆 Linear，两个套件输出完全不同的东西：

**PM 套件 `/竞品分析` 会输出**：
- Linear 的目标市场：3-200 人 SaaS 工程团队
- 定价模型：免费版 250 issue / 标准 8 美金 / 企业 14 美金
- Porter 五力：供应商议价力低、用户切换成本高（issue 数据迁移）
- SWOT：S = 极致体验 / W = 大型企业功能弱 / O = AI 集成 / T = Notion / Jira 反扑
- 战略建议：是否进入这个市场、如何定价、如何应对竞品

**本 Skill `/竞品拆解` 会输出**：
- IA：顶层只有 4 个一级导航（Inbox / My Issues / Active / All）—— borrow，比 Jira 的 8+ 一级菜单清爽
- 交互：CMD+K 命令面板是核心入口，键盘流闭环 —— borrow（context_match: yes，我们用户也是开发者）
- 视觉：极简 + 高对比 + 极致 spacing 节奏 —— 视觉决策 diverge（我们要做更友好的色彩）
- Castle：内置 GitHub / Slack 等深度集成的飞轮 —— 绕开走，我们短期做不到
- Shack：issue 三态 triage 流（Triage → Active → Done）—— borrow，3 问校验通过
- avoid：onboarding 没有引导只靠 Cheatsheet，新手会卡 —— 我们要做相反的渐进式引导

**两个输出加起来才是完整的"理解 Linear"——PM 看商业，Designer 看体验。**

---

## 输入不足处理

- **用户只说"帮我拆竞品"没说哪个**：主动问 1-3 个具体竞品名，给出"快拆 / 标准 / 深拆"选项
- **用户列了 5+ 个竞品**：提示"Bench 是深拆，建议聚焦 1-3 个；要扫多个用 PM 的 `/竞品分析`"
- **没法实际访问竞品 / 没有截图**：用 WebFetch 拉竞品官网 + 公开评论 / 文档作为替代分析对象，但标注"基于公开信息分析，未做交互级体验"
- **用户问"我们和竞品比哪个好"**：拒绝给"好 / 坏"的整体评价，只给"在 [维度] 上 [我们 / 竞品] 强 / 弱"的具体对比

---

## 实操注意事项

### 与 Signal 的协作节奏

**理想流程**：先 Signal（自己的用户在抱怨什么）→ 再 Bench（竞品是怎么解决类似问题的）→ 在 Brief 决定借鉴 / 差异化。

**反向也可**：先 Bench（看到行业某个新模式）→ 再 Signal（自己的用户是否也有这个需求）→ 验证后再做。

### 与 Audit 的协作节奏

Bench 的 `takeaways[borrow/avoid]` 是 Audit 走查的对照清单 —— 自己产品在借鉴点上做得如何、是否踩了竞品同样的坑。

### 与 Brief 的协作节奏

Bench 的 `visual_strategy_decision` 和 `castle_vs_shack.durable_advantages` 应该直接写入 Brief 的"策略"和"约束"段 —— 让 Brief 的决策有外部参照而不是凭空想。

### 与 Pitch 的协作节奏

Bench 的 `annotated_references[]` 是 Pitch 的论据库 —— 提案时引用"看，Linear 这样做（截图）我们也借鉴了这点"远比"我觉得应该这样"有说服力。

### 时间投入建议

| 拆解深度 | 时间投入 | 输出预期 |
| --- | --- | --- |
| 快拆 | 2 小时 | 1 个竞品 × 3 维度，5-10 张标注截图，3-5 条 takeaways |
| 标准 | 半天 | 2 个竞品 × 4-5 维度，15-25 张截图，8-12 条 takeaways |
| 深拆 | 1-2 天 | 1-3 个竞品 × 全 7 维度，30+ 张截图 + 录屏，15-25 条 takeaways + Castle vs Shack 完整判断 + 视觉策略决策 |

---

## 已知限制

- **截图采集需要人工**：Bench 不能替你截图 —— AI 看不到竞品 UI，需要用户提供截图或描述
- **WebFetch 抓取有限**：能拉网页 HTML / 文档，但拉不到 SaaS 登录后的真实产品体验
- **Castle 判断带主观性**：哪些算结构性壁垒、哪些算可学表层，需要业务理解，AI 给的判断仅供参考
- **不替代正式的可用性测试**：Bench 是"看别人怎么做"，不能验证"我们改了会更好"
- **不替代品牌策略**：lean-in / diverge 决策只在设计层面，深度品牌策略需要专门的 Brand Strategy 工作
- **3 问校验依赖诚实**：用户如果用"为了赶进度"覆盖 3 问的判断，Bench 拦不住，只能在红线提醒
