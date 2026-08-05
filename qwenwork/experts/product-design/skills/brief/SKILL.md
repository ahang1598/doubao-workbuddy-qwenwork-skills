---
name: 设计简报
name_en: "brief"
argument-hint: "输入项目背景与目标用户，如：为内容创作者做一个 AI 灵感板工具"
description: >
  设计简报（Design Brief）。生成一页纸 HTML 文档，在设计开始前对齐业务目标、用户需求、设计策略、设计标准与边界约束。是链式上下文的核心锚点节点——所有下游 Skill（/用户故事 /站点地图 /用户旅程 /Web页面设计 /mobile页面设计 /设计走查 /写PRD 等）都从 Brief 读取项目背景，避免重复填写。HTML 可一键导出 PNG 分享给 UX/PM/工程/业务方。

  触发关键词：写设计简报、设计简报、design brief、brief、一页纸、启动设计项目、启动设计前对齐方向、设计前对齐、设计目标对齐、设计方向对齐、对齐 UX/PM/工程、给设计 kickoff、设计 brief 模板、一页纸 brief、design brief HTML、设计起点文档、为设计画方向地图。

  排除（反向）：方向尚未明确时先做方向探索（用 /问题框定 探索新方向，或用 /读需求 拆解已有 PRD，或用 /启发评估 诊断改版项目）；细化为可执行场景（用 /用户故事）；画用户体验旅程（用 /用户旅程）；产出工程交付文档（用 /写PRD）；做向上汇报材料（用 /设计提案）。
description_en: >
  Generates a one-page Design Brief (HTML) that aligns business goals, user needs, design strategy,
  design standards, and boundary constraints before design execution begins. The chain anchor node —
  all downstream skills read from Brief context. Triggers when a designer says: "write a design
  brief", "start a design project", "align on design direction", "one-pager", "design brief",
  "brief", or uses /brief. Excludes: direction exploration before brief exists (use /frame or
  /scope), user story breakdown (use /stories), engineering PRD (use /prd).

chain:
  protocol_version: "1.0"
  reads: [frame, scope, audit]
  writes: brief
  schema:
    skill: string
    generated_at: string
    project_name: string
    project_type: string
    project_subtype: string
    business_context: string
    business_goal: array<string>
    user: array<string>
    strategy_dimensions:
      - dimension: string
        thesis: string
        tactics: array<string>
        rationale: string
    design_criteria:
      quantitative: array<string>
      qualitative: array<string>
    constraints: array<string>
    out_of_scope: array<string>
    style: string
    ratio: string
    scale: string
---

# 设计简报

Design Brief Skill — 在设计启动前，用一页可导出的 HTML 文档完成目标、用户、策略、标准、约束的一次性对齐。

## 能力矩阵

本 Skill 的三种运行模式，可单独运行也可叠加。最常见路径：链式模式（从 Frame / Scope / Audit 来）。

| 模式 | 触发条件 | 产出特征 |
| --- | --- | --- |
| 🟢 **独立模式** | 无前序上下文，直接调用 | 引导式追问 7 字段 → 完整 HTML |
| 🔵 **链式模式** | 检测到 `spark-output/context/frame|scope|audit|journey|hmw.json` | 跳过已预填字段 → 完整 HTML |
| 🟣 **增强模式** | 项目同目录有 SparkDesign 组件库标识（未来） | HTML 内策略维度引用真实组件名 |

> Brief 的产出形态在三种模式下完全一致（双通道：`spark-output/context/brief.json` + 完整 HTML），区别只在"提问多少 / 字段从哪里来"。

## 输入要求

| 输入项 | 必填？ | 来源优先级 | 缺失时行为 |
| --- | --- | --- | --- |
| `project_name` | ✅ | 链式 frame / scope > 用户输入 | Phase 3 追问 |
| `project_type` + `project_subtype` | ✅ | 用户输入（Phase 1 六大类选择） | 进入 Phase 1 引导 |
| `business_context` | ✅ | 链式 frame.persona.situation / scope.background > 用户输入 | Phase 3 追问 |
| `business_goal` | ✅ | 链式 frame.business_angle / scope.business_goal > 用户输入 | Phase 3 追问 |
| `user` | ✅ | 链式 frame.persona / scope.target_users > 用户输入 | Phase 3 追问 |
| `strategy_dimensions` | ✅ | Phase 4 勾选 + Phase 4.5 AI 草拟 + Phase 4.6 追问被否决项 | 按项目类型默认勾选 3 项 |
| `design_criteria` | ✅ | 用户输入（Phase 3 追问） | Phase 3 追问 |
| `constraints` | ⭕ | 链式 scope.constraints > 用户输入 | 标注"未提供"，不阻断 |
| `out_of_scope` | ⭕ | 用户输入 | 标注"未提供"，不阻断 |
| `style` / `ratio` / `scale` | ⭕ | 按项目类型自动匹配（Phase 6.3） | 取默认值（chalk / 16-9 / md） |

**信息完整度判断**：必填项任一缺失 → 进入 Phase 3 引导追问；仅可选项缺失 → 直接生成 HTML 并在卡片内标注"待补充"。

## Chain Context

### 上游读取（Phase 0.5 执行）

**Step 1 · 扫描上下文来源**（按顺序，找到任一即读取）：

- [ ] 会话内 marker：`<!-- spark-context:frame -->` / `scope` / `audit` / `journey` / `hmw`
- [ ] 项目文件：`spark-output/context/frame.json` / `scope.json` / `audit.json` / `journey.json` / `hmw.json`
- [ ] 都没有 → 跳过 Phase 0.5，按无上下文流程执行

**Step 2 · 字段映射 checklist**（找到上下文时，按下表逐项映射并预填 Brief 字段）：

#### 来自 frame（最常见，无 PRD 场景）

| Brief 字段 | ← Frame 字段 | 处理方式 |
| --- | --- | --- |
| `project_name` | `frame.project_name` | 直接沿用 |
| `business_context` | `frame.persona.situation` | 部分填入（再让用户补"为什么现在做"等业务背景） |
| `business_goal`（候选） | `frame.business_angle.strategic_intent`（growth/retention/defensive） | 转为业务目标候选项让用户确认 |
| `user`（4 条以内） | `frame.persona.description` + `frame.persona.goal` | 合成 4 条短描述（每条 ≤ 25 字） |
| `strategy_dimensions`（候选维度） | `frame.opportunities`（每条机会点） | 转为 Phase 4 维度勾选的候选项 |
| `strategy_dimensions[*].thesis`（方向锚点） | `frame.lean_direction.one_liner` | 作为策略思路的方向锚点 |
| **假设标记**（Phase 5 草图预览显式标出） | `frame.critical_assumption` | 在 Brief 末尾用 ⚠️ 显式标记 |
| `constraints`（候选） | `frame.competitive_landscape` 中竞品已踩的坑 | 转为本设计的约束候选 |

#### 来自 scope（有 PRD 场景）

| Brief 字段 | ← Scope 字段 | 处理方式 |
| --- | --- | --- |
| `project_name` | `scope.project_name` | 直接沿用 |
| `business_context` | `scope.background` | 直接沿用 |
| `business_goal` | `scope.business_goal` | 直接沿用 |
| `constraints` | `scope.constraints` + `scope.gaps` | scope 标的 gaps 作为待补充的约束 |
| `user`（候选） | `scope.target_users` | 转为 user 候选项让用户精简到 4 条以内 |

#### 来自 audit（改版场景）

| Brief 字段 | ← Audit 字段 | 处理方式 |
| --- | --- | --- |
| `strategy_dimensions`（候选） | `audit.opportunities`（改版机会点聚类） | 转为本次改版的策略候选维度 |
| `constraints`（候选） | `audit.findings`（blocker / major 项） | 转为"v2 必须改"约束 |
| **假设标记** | `audit.findings` 中 severity=high 的项 | 显式标记为"v2 必须验证修复" |

#### 来自 journey / hmw（增量来源）

- `journey.stages[*].opportunities` → 补充 `strategy_dimensions` 候选
- `journey.key_moments[type=dropout-risk]` → 加入 `business_goal` 强化（"降低 X stage 流失"）
- `hmw.cards` → 作为 `strategy_dimensions[].tactics` 的灵感源（不直接转，作为讨论起点）

**Step 3 · 告知用户沿用情况**（必做）：

读到上下文后必须明确告诉用户：

> "已读到 [N 个] 上游 Skill 上下文：[列出 frame/scope/audit/...]。已自动预填以下字段，跳过对应提问：
> - project_name = [...]
> - business_context = [...]
> - user = [...]
> ...
> 接下来从 [第一个未自动预填的字段，按 Phase 3 依赖顺序] 开始问你。"

**Phase 3 提问顺序原则**：跳过已被上游字段预填的字段，从下一个未填字段按 Phase 3 定义的依赖顺序开始问（完整依赖顺序 + 字数约束见下方 Phase 3 章节，不在此重复以避免漂移）。

### 下游输出（Phase 7 执行）

完成 Brief 内容后，**同时**做两件事：

1. **会话内输出**：

   ```
   <!-- spark-context:brief -->
   { ...JSON（schema 见 frontmatter）... }
   <!-- /spark-context:brief -->
   ```

2. **写入项目文件**：`spark-output/context/brief.json`（目录不存在时先创建）

下游可消费 Skill：Stories / Sitemap / **Journey** / Flow Web / Flow Mobile / Landing / Campaign / Chart / Edge / Motion / Check / Access / Metric / QA / PRD / Pitch / Retro。

### 字段流向下游

Brief 是链路锚点，下游消费量最大（13 个 Skill）。字段映射：

- `brief.project_name` → 全部 13 下游 Skill 的项目识别字段
- `brief.user` → **Stories / Journey** 的 persona 输入；**PRD** 的 Personas 段
- `brief.business_goal` → **Pitch** 的 The Bet / Why Now；**PRD** 的 Goals & Success Metrics；**Metric** 的 NSM 推导锚点
- `brief.strategy_dimensions[]` → **Stories** 的 acceptance_criteria 候选；**Flow Web/Mobile** 的 IA 决策依据；**Check** 的"策略一致性"走查项；**PRD** 的 Solution & Feature Scope 输入
- `brief.design_criteria.quantitative` → **Metric** 的 Driver / Counter Metrics 候选；**QA** 的还原度容差基线
- `brief.design_criteria.qualitative` → **Check** 的走查标准；**Access** 的合规目标基线
- `brief.constraints` → **Sitemap / Flow Web/Mobile / Edge** 的设计边界；**PRD** 的 Constraints & Risks
- `brief.project_type` / `brief.project_subtype` → **Flow Web/Mobile** 的 scenario 选型路由

## ⛔ 核心原则（全局硬约束，违反即判定任务失败）

1. **本 Skill 的视觉产物唯一来源是 `prototype/brief.html`。** 它不是"参考"，而是**必须被完整克隆并在其上做字段替换**的源文件。
2. **禁止自写 HTML 结构、CSS 样式、JS 逻辑。** 包括但不限于：自定义配色 / 字体 / 圆角 / 阴影 / 间距、引入 Tailwind / Bootstrap / 任何 UI 框架、"简化版"或"更干净的版本"。
3. **禁止凭记忆重建模板。** 每次执行 Phase 6 都必须**实际读取**本 Skill 目录下的 `prototype/brief.html`（结构）+ `prototype/brief-themes.css`（样式），以这两个文件的当前实际内容为唯一基线。
4. **路径解析优先级**（依次尝试，找到即用，不要凭印象编造路径）：
   1. 相对本 SKILL.md 的相对路径 `prototype/brief.html`
   2. 用文件搜索工具（glob / find / grep_search / list_dir 等任一可用工具）按文件名 `brief.html` 在 skill 安装目录下定位——常见位置含 `~/.qoderwork/skills/brief/prototype/brief.html`、`.claude/skills/brief/prototype/brief.html`、`<repo>/2-Define/Brief/prototype/brief.html`、`<plugin-pack>/skills/brief/prototype/brief.html` 等，但**不要硬编码**——按文件名搜索更可靠
   3. 让用户提供绝对路径
5. **三次定位都失败才停止。** 单次 read_file 失败不算"无法读取"——必须先尝试搜索；连续三次定位失败才告知用户"模板缺失"，不得降级、不得即兴生成替代 HTML。

## 触发条件

以下任意一种情况触发本 Skill：

- 用户说"帮我写设计简报 / Design Brief / 项目对齐文档"
- 用户说"启动一个设计项目"、"开始设计前先对齐方向"
- 用户使用 `/设计简报` 指令
- 前序 Skill（Scope、Journey、HMW）完成后，用户希望沉淀为一页文档

---

## 独立能力（无需连接器）

本 Skill 在完全离线、无任何连接器的场景下即可完整交付，所有方法论与输出形态不依赖外部系统：

- **一页纸 HTML 完整生成**：目标 / 用户 / 策略 / 标准 / 约束七字段引导式追问 → Phase 4/4.5/4.6 策略维度勾选与 AI 草拟 → 完整 HTML 输出
- **链式上下文双通道**：写入 `spark-output/context/brief.json` + 会话内 marker block，下游 14 个 Skill 可直接读取（无需连接器）
- **HTML 一键导出 PNG**：本地浏览器即可完成，无需云服务
- **三种运行模式自适应**：独立模式（无前序）/ 链式模式（读本地 spark-output）/ 增强模式（识别 SparkDesign 组件标识）全部本地化运行
- **六大项目类型差异化模板**：B2C / B2B / Tool / Content / 营销活动 / 平台型差异化策略库内置在 Skill 内

> 红线：缺连接器时 **绝不 abort**，所有引导式追问与 HTML 生成路径必须照常完成。

## 增强能力（连接器加持）

接入以下连接器后，可减少手动粘贴、提高对齐效率。所有连接器均为可选，未装时按"降级路径"列的方式回落。

| 连接器 | 阶段 | 增强能力 | 降级路径 |
| --- | --- | --- | --- |
| **Figma** | Phase 0.5 上游读取 | 直接抓取项目相关 frame / moodboard / 早期 sketch 作为 `business_context` 与策略维度的视觉佐证；HTML 内"参考视觉"区块嵌入 frame 缩略图 + 深链 | 未装时让用户手动粘贴 Figma 链接或截图描述，HTML 内退化为纯文字引用 |
| **Notion / 飞书文档** | Phase 7 输出后 | Brief HTML 一键写入团队 wiki 指定空间，自动生成项目锚点页（下游 Skill 通过 wiki 链接反查 Brief）；并搜索 wiki 历史 Brief 作为同类项目参考 | 未装时输出本地 `spark-output/brief/{project}.html`，提示用户手动上传至团队 wiki |
| **Linear / Jira** | Phase 0.5 上游读取 | 若 `business_context` 与某个 Epic / Project 绑定，可拉取 Epic 描述 / 关联 issue 数量 / 当前 sprint 作为业务背景的补充事实 | 未装时让用户在 Phase 3 追问中手动描述"业务背景与现状"，不影响 Brief 主体 |
| **GitHub** | Phase 4.5 策略维度 AI 草拟 | 检测项目代码仓库的 package.json / 技术栈，让策略维度的"技术约束"与"组件复用策略"更贴合实际工程现状 | 未装时按用户描述的技术栈生成通用策略，准确度略降但不阻断 |

**接入触发**：用户首次调用 `/设计简报` 时，Skill 主动检测已认证的连接器并显示「已检测到：Figma / Notion，将自动启用增强模式」提示，用户可在该次会话中选择关闭。

**字段流向变化**：

- 启用 **Figma** → `chain.schema` 新增可选字段 `reference_visuals: array<{frame_url, thumbnail, description}>`，下游 Flow Web/Mobile / Pitch 可直接复用
- 启用 **Notion / 飞书** → `chain.schema` 新增可选字段 `wiki_page_url: string`，下游 Skill 在生成自己的文档时可在底部引用 Brief wiki 链接
- 启用 **Linear / Jira** → `chain.schema` 新增可选字段 `source_epic: {id, url, title}`，PRD / Stories 下游读取后可自动关联同一 Epic

> 所有新增字段都是 **可选**，未启用连接器时字段缺省，下游 Skill 必须能容忍缺省。

---

## 执行流程（Route B）

按以下 8 个阶段顺序执行。每个阶段完成后再进入下一阶段，不得跳跃。

### Phase 0 — 触发识别

确认触发来源（自然语言 / 指令）。无需向用户确认，直接进入 Phase 0.5。

### Phase 0.5 — 上下文检查

检查当前会话是否已有前序 Skill 输出的项目上下文（Scope 输出、PRD 摘要、Journey 结论等）。

- **有上下文**：提取可复用字段（项目名称、项目类型、业务目标、用户），预填入对应模块，告知用户："我从上下文中提取了以下信息，可以直接沿用或修改。" 然后进入 Phase 1。
- **无上下文**：直接进入 Phase 1。

### Phase 1 — 项目类型选择

向用户提问，确认项目所属大类与子类型。若用户描述已足够清晰，可直接判断，无需再问。

**六大类及子类型：**

| 大类       | 子类型                                      |
| ---------- | ------------------------------------------- |
| 产品设计   | 全新产品 / 产品迭代 / 产品改版              |
| 营销与传播 | 营销设计 / 会议与活动 / 线下物料 / 视频设计 |
| 品牌设计   | 全新品牌 / 品牌升级                         |
| 研究与评估 | 用户研究 / 设计走查 / 设计咨询              |
| 系统与资产 | 设计系统与规范                              |
| 特殊介质   | 硬件设计 / 互动设计                         |
| 管理类     | 设计项目管理 / 组织管理                     |

用户不确定时，AI 根据描述直接判断并告知选择理由，用户确认后继续。

### Phase 2 — 文档判断

询问用户是否有已有文档（PRD、需求文档、Research 报告等）：

- **路径 A（有文档）**：读取文档，提炼关键信息填入各模块，告知"以下字段信息不足，需要补充：[缺失列表]"，逐一追问缺失项。
- **路径 B（无文档）**：展示空白模板结构，进入逐字段追问模式。

### Phase 3 — 内容填写

按**依赖优先顺序**逐字段追问，不得按字段编号顺序（背景决定目标，目标决定用户，用户决定策略）：

```
业务背景 → 业务目标 → 用户 → 设计策略 → 设计标准 → 边界约束 → 不做什么
```

**追问规则：**

- 每次只问一个字段。
- 每个问题附带 AI 推荐答案，格式：`> 推荐：[AI 建议内容]`，用户可直接采纳、修改或否定。
- 若用户已在上文提及相关信息，不重复追问，直接沿用并告知。

**各字段字数上限（HTML 卡片容量约束，生成时严格遵守）：**

| 字段     | 格式                  | 上限                                                                                               |
| -------- | --------------------- | -------------------------------------------------------------------------------------------------- |
| 业务背景 | 连续段落              | ≤ 100 字                                                                                          |
| 业务目标 | 列表                  | ≤ 4 条，每条 ≤ 22 字                                                                             |
| 用户     | 列表                  | ≤ 4 条，每条 ≤ 25 字                                                                             |
| 设计策略 | 2–3 列维度（三段式） | 每列：标题 ≤ 10 字 + 主张 ≤ 22 字 + 手法 2–3 条（每条 ≤ 16 字）+ 依据（可选）≤ 25 字          |
| 设计标准 | 带标签列表            | ≤ 4 条，每条 ≤ 22 字（行首带 `定量` / `定性` pill，对应 `data-kind="quant"` / `"qual"`） |
| 边界约束 | 列表                  | ≤ 5 条，每条 ≤ 22 字                                                                             |
| 不做什么 | 列表                  | ≤ 5 条，每条 ≤ 22 字                                                                             |

超出上限时，AI 应主动精简，优先删去冗余修饰词，保留关键数字与动词。

**专属字段追问**（Phase 1 确定类型后激活，在标准字段完成后追问）：

见下方「字段结构」章节中各类型的专属必填字段。

### Phase 4 — 设计策略维度选择

根据项目类型，展示过滤后的设计策略维度供用户勾选。

**管理类例外**：不展示策略维度，改为填写"执行路径"（本周期的核心行动路线）。

**过滤规则：**

| 维度        | 产品设计 | 营销与传播 | 品牌设计 | 研究与评估 | 系统与资产 | 特殊介质 |
| ----------- | :------: | :--------: | :------: | :--------: | :--------: | :------: |
| 信息架构 IA |    ✓    |     —     |    —    |     —     |     ✓     |    ✓    |
| 交互设计    |    ✓    |     —     |    —    |     —     |     ✓     |    ✓    |
| 视觉设计    |    ✓    |     ✓     |    ✓    |     —     |     ✓     |    ✓    |
| 内容设计    |    ✓    |     ✓     |    ✓    |     ✓     |     —     |    —    |
| 情感化设计  |    ✓    |     ✓     |    ✓    |     —     |     —     |    ✓    |
| 用户引导    |    ✓    |     —     |    —    |     ✓     |     ✓     |    ✓    |
| 多端适配    |    ✓    |     ✓     |    —    |     ✓     |     ✓     |    —    |
| 数据可视化  |    ✓    |     —     |    —    |     ✓     |     —     |    —    |
| 动效设计    |    ✓    |     ✓     |    ✓    |     —     |     —     |    ✓    |
| 无障碍设计  |    ✓    |     —     |    —    |     ✓     |     ✓     |    ✓    |

用户勾选维度后，**进入 Phase 4.5（AI 先写策略草稿）**，而非立即走追问。

### Phase 4.5 — 设计策略草稿（AI 先行）

在走结构化追问前，AI 先基于 **业务背景 / 业务目标 / 用户** 三项输入，为每个勾选的维度自动生成一份 **三段式草稿**，交给设计师批改而非从零写起。

**草稿结构（每个维度一份）：**

```
[维度名]
  主张  ·  [一句判断，≤ 22 字]
  手法  ·  [动作 1，≤ 16 字]
         ·  [动作 2，≤ 16 字]
         ·  [动作 3，≤ 16 字]（可缺省）
  依据  ·  [对应业务目标 / 用户痛点，≤ 25 字]
```

**输出样例（以"交互设计"为例，假设业务目标含"跳出率↓20%"）：**

```
交互设计
  主张  ·  结算压缩到 3 步，错误校验前置
  手法  ·  地址 / 支付合并一屏
         ·  字段实时校验
         ·  进度条常驻顶部
  依据  ·  对应 B2（跳出率↓20%）；用户低容忍繁琐
```

**处理规则：**

- 每个维度以卡片形式并排展示，设计师逐条处理。
- 每份草稿提供三种操作：`✓ 采纳` / `✎ 改写` / `✗ 否决后进入手写追问`。
- 全部确认后，进入 Phase 5；仅被 `✗ 否决` 的维度才走 Phase 4.6 的追问式填写。

### Phase 4.6 — 三段式结构化追问（仅处理 Phase 4.5 被否决的维度）

对被否决的维度，改问结构化三连问（不再使用开放式的"你打算从哪个角度切入"）：

```
Q1 · 主张｜[维度名] 上你打算用什么方式推动目标？（≤ 22 字）
    > 推荐：[AI 建议]
    > 可选角度（选 1–2 或自提）：[子问题池抽取 2–3 条]

Q2 · 手法｜具体落到 2–3 个可执行动作是什么？（每条 ≤ 16 字）
    > 推荐：① [建议 1]  ② [建议 2]  ③ [建议 3]

Q3 · 依据｜这条策略对应哪个业务目标或用户痛点？（≤ 25 字，可跳过）
    > 推荐：对应 [业务目标编号]；源自用户 [痛点关键词]
```

**子问题池（AI 追问时从对应维度抽取 2–3 条作为启发，按"切面"分组）：**

| 维度        | 子问题池（按切面分组）                                                                                                                                                                                                                     |
| ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 信息架构 IA | **结构**：层级深度？分类心智？核心任务是否前置？<br>**导航**：导航模型（全局 / 侧栏 / 抽屉）？跨层级路径？<br>**组织**：内容聚类依据？搜索 vs 浏览？标签 / 筛选策略？                                                    |
| 交互设计    | **路径**：核心任务闭环？步骤数压缩？分支收敛？<br>**反馈**：进度感知？成功 / 失败态？关键节点反馈形式？<br>**异常**：错误前置校验？恢复路径？空 / 加载 / 离线态？<br>**输入**：表单策略？手势 / 快捷？键盘可达性？ |
| 视觉设计    | **调性**：关键词 3–5 个？品牌延展度？<br>**层级**：对比度策略？字阶？色彩优先级？<br>**媒介**：图像 vs 插画？图标语言？留白哲学？                                                                                       |
| 内容设计    | **语气**：人格画像？称呼策略？长短文平衡？<br>**结构**：标题 / 正文 / 微文案句式？信息密度？<br>**本地化**：多语言？文化敏感度？合规话术？                                                                               |
| 情感化设计  | **高峰**：成就节点？惊喜时刻？仪式感设计？<br>**低谷**：失败 / 错误 / 空态的安抚？<br>**人格**：品牌口吻？角色化？声音 / 音效？                                                                                          |
| 用户引导    | **首程**：Onboarding 节奏？价值前置？跳过策略？<br>**关键节点**：功能点引？Coachmark？渐进披露？<br>**空状态**：无数据 / 无权限 / 新用户？引导 CTA？                                                                     |
| 多端适配    | **主端判定**：主端？次端？响应式 vs 分平台？<br>**断点**：断点策略？栅格？容器查询？<br>**差异**：可触达性差异？手势差异？输入方式差异？<br>**一致性**：跨端资产复用？交互隐喻对齐？                               |
| 数据可视化  | **主看板**：3 个主指标？时间粒度？对比维度？<br>**钻取**：下钻路径？筛选联动？上下文保留？<br>**可读**：图表类型选型？色彩编码？异常告警？<br>**可操作**：导出？订阅？分享？标注？                                 |
| 动效设计    | **进出**：页面 / 组件进出节奏？层级叙事？<br>**状态**：切换 / 加载 / 反馈动效？时长与缓动？<br>**品牌**：动效人格？signature 动作？<br>**克制**：动效可关？性能预算？晕动症兼容？                                  |
| 无障碍设计  | **对比**：文本 / 图标对比度？色盲模拟？<br>**操作**：键盘全流程？焦点顺序？Tab trap？<br>**辅助**：读屏语义？alt / aria？实时区？<br>**动效**：prefers-reduced-motion？可关闭？                                    |

### Phase 5 — 完整性校验 + 草图预览

所有字段填写完成后：

1. 检查 7 个通用模块是否均有实质内容（非空、非"待定"）。
2. 以提示卡片列出缺陷：`⚠ [字段名]：内容过于模糊，建议补充 [具体建议]`
3. 输出带视觉结构的文字草图预览（用 Markdown 表格或代码块模拟 Bento 布局），让用户确认信息密度与结构。
4. 用户可对话修改任意字段后再生成 HTML。

**草图预览示例（横版默认布局，用代码块 ASCII 模拟 Bento 网格）：**

```
┌──────────────────────────────────┬────────────────┬────────────────┐
│ 业务背景  Business Context        │ 业务目标 Goal  │ 用户 User      │
│ 平台成熟期，GMV 增速趋缓，购物车  │ · 购物车转化   │ · 25–40 女性   │
│ 放弃率高于行业 12pp，Q2 增长专项  │   45%→58%      │ · 移动端为主   │
│ 聚焦购物车到支付转化路径。        │ · 跳出率↓20%  │ · 月购 3 次+   │
│                                  │ · 支付率↑8%   │ · 低容忍繁琐   │
├──────────────────────────────────┴────────────────┼────────────────┤
│ 设计策略  Design Strategy                          │ 设计标准       │
│ ┌─ IA ─────────┬─ 交互 ─────────┬─ 情感化 ────────┐│ Design Criteria│
│ │ 主张：核心操 │ 主张：结算压  │ 主张：支付动效 ││ · 步骤≤3 [定量]│
│ │ 作提至首屏   │ 缩到 3 步     │ + 加购确认     ││ · 完成率>88%   │
│ │ 手法：       │ 手法：        │ 手法：         ││ · 感知清晰[定性]│
│ │ · 精简层级   │ · 合并结算屏  │ · 支付成功动效 ││                │
│ │ · 去冗余跳转 │ · 实时校验    │ · 加购即时反馈 ││                │
│ │ 依据：B2     │ · 进度常驻    │ 依据：B4 客诉↓ ││                │
│ └──────────────┴───────────────┴────────────────┘│                │
├──────────────────────────────────┬────────────────┴────────────────┤
│ 边界约束  Constraints             │ 不做什么  Out of Scope           │
│ · 8 周内上线                      │ · 商品详情页不改                │
│ · 支付模块不可改动                │ · 会员积分不重设                │
│ · 遵守 DS v2.3                    │ · PC 端不覆盖                   │
│ · 2 名设计师                      │ · 推荐算法不调                  │
└──────────────────────────────────┴────────────────────────────────┘
```

或 **Markdown 表格版**（信息密度更高、便于对话中快速修订）：

| 模块     | 内容摘要                                                                                                                                                                                                                    |
| -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 业务背景 | 平台成熟期，GMV 增速趋缓；购物车放弃率高于行业 12pp，Q2 增长专项。                                                                                                                                                          |
| 业务目标 | 购物车转化 45%→58%；跳出率↓20%；支付率↑8%；流程客诉↓30%。                                                                                                                                                               |
| 用户     | 25–40 岁城市女性；移动端为主；月购 3 次+；对繁琐流程低容忍。                                                                                                                                                               |
| 设计策略 | IA｜主张：核心操作提至首屏 · 手法：精简层级 / 去冗余跳转 · 依据：B2<br>交互｜主张：结算压缩 3 步 · 手法：合并结算屏 / 实时校验 / 进度常驻 <br>情感化｜主张：支付动效 + 加购确认 · 手法：成功动效 / 即时反馈 · 依据：B4 |
| 设计标准 | 步骤≤3（定量）；完成率>88%（定量）；流程感知清晰（定性）；无卡点（定性）                                                                                                                                                   |
| 边界约束 | 8 周上线；支付模块不可改；遵守 DS v2.3；2 名设计师。                                                                                                                                                                        |
| 不做什么 | 商品详情页不改；会员积分不重设；PC 端不覆盖；推荐算法不调。                                                                                                                                                                 |

两种格式任选其一输出，推荐 ASCII 版（更接近最终视觉）。

### Phase 6 — 视觉输出

生成完整 HTML 文件（基于 `prototype/brief.html` 模板）。

#### 6.0 ⛔ 绝对禁止（任一违反即视为生成失败，必须重做）

- ❌ 从零编写任何 `<style>` 内容或新增内联 `style="..."`
- ❌ 引入 Tailwind、Bootstrap、DaisyUI、shadcn、任何 CDN 样式表或 UI 框架
- ❌ 自行定义颜色、字体、圆角、阴影、间距、栅格等视觉 token
- ❌ 删除、替换、"简化"工具栏、主题切换器、字号控件、导出按钮
- ❌ 修改 `<style>` 内任何 CSS 变量、`data-theme` 规则、`.brief-canvas` grid 布局
- ❌ 修改 `<script>` 内任何 JS（主题切换 / 布局切换 / 字号缩放 / `fitCards` / topbar 可编辑 `bindEditable` / `modern-screenshot` 导出）
- ❌ 以"更现代"、"更简洁"、"移动端优化"为由重写模板
- ❌ 生成一个只有 100–300 行的"轻量版" HTML（合并后的完整文件约 1500 行——结构 ~500 行 + 样式 ~1040 行，成品行数不得低于原型 95%）
- ❌ 删除或改写 `.topbar-title-wrap` / `.topbar-meta-wrap` 容器、`.topbar-title-edit` / `.topbar-meta-edit` 铅笔按钮、`body.is-exporting` 相关规则（这是 topbar 文案可编辑功能的必需 DOM / CSS）
- ❌ 删除或修改 `modern-screenshot` 脚本引用（当前用 jsDelivr CDN，保证导出 PNG 可用；不得改成不可达的本地路径、不得删除此行）

#### 6.1 ✅ 生成步骤（必须严格按序执行）

**Step 1 · 读取模板结构（强制）**

读取本 Skill 目录下的 `prototype/brief.html`（**结构文件，约 500 行**），以其实际内容作为唯一基线。禁止凭记忆或凭 SKILL.md 里的片段推断模板结构。

> **v0.5.9 变更**：模板已拆分为结构（`brief.html` ~500 行）+ 样式（`brief-themes.css` ~1040 行，含 9 套主题 CSS 变量）。Step 1 只读结构文件，大幅降低 context 占用。

**路径解析协议**（依次尝试，**禁止凭印象编造路径**——尤其禁止编造仓库结构路径如 `3-Ideate/Brief/...`、`SparkSkillHub/2-Define/...` 等，AI 既不知道用户从哪安装、也不知道平台的实际安装目录）：

1. **首选**：用相对本 SKILL.md 的相对路径 `prototype/brief.html` 直接 `read_file`（多数 IDE / Agent 平台支持以 SKILL.md 同目录为基准）
2. **失败则搜索**：调用文件搜索工具按文件名 `brief.html` 定位，候选位置含但不限于：
   - `~/.qoderwork/skills/brief/prototype/brief.html`（QoderWork 安装目录）
   - `.claude/skills/brief/prototype/brief.html`（Claude Code 安装目录）
   - `<product-design-pack>/skills/brief/prototype/brief.html`（解压套件）
   - `<repo>/2-Define/Brief/prototype/brief.html`（开发仓库源码）
3. **再失败则问用户**："请告诉我你电脑上 `brief.html` 的绝对路径，或确认 Brief Skill 是否完整安装"
4. **三轮全失败才停止**——单轮失败不要立即停止，更不要"降级输出 markdown 版本"——只有定位真的不可能时才告知模板缺失

若读取失败 → 立即停止 → 告知用户"无法访问原型模板，本次不生成 HTML" → 不得即兴兜底。

**Step 1.5 · 读取样式文件（强制）**

读取与 `brief.html` 同目录下的 `prototype/brief-themes.css`（~1040 行，含 9 套主题的 CSS 变量 + 布局样式 + 打印媒体查询）。路径定位策略与 Step 1 一致（同目录下的 `brief-themes.css`）。

> **为什么单独读取**：CSS 文件内容是静态的，不需要做字段替换，在 context 窗口紧张时可以推迟到 Step 2 之前再读取，减少中间步骤的 context 占用。

**Step 2 · 全文克隆（合并结构 + 样式）**

将 `prototype/brief.html` 的结构 + `prototype/brief-themes.css` 的样式合并为一个**自包含的单 HTML 文件**，写入目标文件（默认路径 `spark-output/brief/[项目名].html`，目录不存在时先创建，由用户确认）。

**合并方法**：在输出 HTML 中，将 `<style></style>` 替换为 `<style>\n{brief-themes.css 全部内容}\n</style>`，并删除 `<link rel="stylesheet" href="brief-themes.css">` 行（输出文件必须自包含，不依赖外部 CSS 文件）。

合并后的新文件应与原型的视觉效果**完全等价**。

⛔ **克隆后编辑约束**：Write 工具写出的新文件，必须**先 Read 再 Edit**。不能直接对刚 Write / Bash cp 生成的文件执行 Edit——Edit 工具要求该文件在当前会话内曾被 Read 过。推荐流程：① 用 Write 一次性写出完整替换后的 HTML（最可靠）；② 或 Write 克隆 → Read 目标文件 → 逐字段 Edit 替换。**禁止跳过 Read 直接 Edit，否则会触发 "File has not been read yet" 错误。**

**Step 2.1 · 依赖说明（无需额外拷贝）**

HTML 里 `modern-screenshot` 通过 jsDelivr CDN 引用（`https://cdn.jsdelivr.net/npm/modern-screenshot@4/dist/index.js`），生成目标文件时**不需要**再同步拷贝任何 js 文件。只要用户打开 HTML 时能联网，"导出 PNG"即可工作。若用户需要离线使用，再另行下载 UMD 文件并将 `src` 改回相对路径。

**Step 3 · 仅替换以下字段**（表格列出的是唯一允许修改的位置，其余一行都不得改动）：

| 位置                                                                       | 原始内容（示例）                   | 替换为                                                                             |
| -------------------------------------------------------------------------- | ---------------------------------- | ---------------------------------------------------------------------------------- |
| `<title>`                                                                | `Design Brief — 购物车流程改版` | `Design Brief — [项目名称]`                                                     |
| `.topbar-title-wrap > .topbar-title` 文本节点                            | `购物车流程改版`                 | `[项目名称]`（仅替换文本，**保留外层 wrap + 铅笔按钮 DOM**）               |
| `.topbar-meta-wrap > .topbar-meta` 文本节点                              | `产品迭代 · 2026-04-29`         | `[子类型] · [YYYY-MM-DD]`（仅替换文本，**保留外层 wrap + 铅笔按钮 DOM**） |
| `<body data-theme="...">`                                                | `data-theme="chalk"`             | 按 6.3 默认风格规则替换                                                            |
| 7 张 `.card` 的 `.card-body` 内文本节点（`<ul><li>` 或段落 `<p>`） | 购物车案例文案                     | Phase 3 收集到的 7 个字段内容                                                      |

> **`.hint` 副标题不替换**：每张卡片第二行 `<p class="hint">...</p>` 是字段含义的固定释义（如「当前业务处于什么阶段，触发本次设计的原因」），必须保持与模板逐字一致。只替换 `.hint` **之后**的正文 `<p>` / `<ul class="list">` / `.s-grid` 内容。
> **设计标准 list 结构强约束**：每条必须是 `<li><span class="tag" data-kind="quant|qual">定量|定性</span><span class="text">...</span></li>`，tag 放**行首**（pill 胶囊形态），不是行尾纯文字。

**Step 4 · 严格保留清单（一行都不能改）**

- `<head>` 内全部 `<link>`（字体 preconnect + Google Fonts url）
- `<style>` 标签内全部 CSS（9 套主题变量 + 布局 + 字号体系 + 卡片样式 + topbar 可编辑态样式 + `body.is-exporting` 规则）
- `.toolbar-left` / `.toolbar-right` 的 HTML 结构与控件 id（`#themeSelect` / `#accentPicker` / 布局按钮组 / 字号按钮组 / 打印按钮 / `#exportBtn`）
- `.topbar-title-wrap` / `.topbar-meta-wrap` 容器 + 两个 `.topbar-*-edit` 铅笔按钮（含 SVG）
- `<script>` 标签内全部 JS（主题切换、`data-ratio` 切换、`data-scale` 切换、`fitCards`、`bindEditable` topbar 可编辑 IIFE、`modern-screenshot` 导出——必须使用 `domToBlob` + `URL.createObjectURL` + **`isInIframe()` 环境检测分流**（独立浏览器走 `directDownload`，iframe 预览态走 `showExportModal` 浮层，浮层内**必须用 `FileReader.readAsDataURL(blob)` 把预览图 `src` 切换成 base64 data URL**，并用 `<a class="export-preview-link" href="${dataUrl}" download>` 包裹 `<img>`——这是 sandbox iframe 下 Mac Option + 点击 / Windows 右键「图片另存为」能工作的唯一条件），**不得回退到 `domToPng` + data URL 的一次性下载**，**不得在浮层内添加下载按钮 / 复制到剪贴板 / 新窗口打开 等动作按钮（sandbox 已实测全部拦截，是无效噪音）**）
- `<script src="https://cdn.jsdelivr.net/npm/modern-screenshot@4/dist/index.js"></script>` 引用一行（**jsDelivr CDN，不得改成不可达的本地路径，不得删除此行**）
- `.brief-canvas` 内 7 张卡片的 DOM 顺序、class 名、每张卡片的 SVG line icon（`stroke-width="1.5"` / `stroke-linecap="round"` / `stroke-linejoin="round"` 全部保留）

**Step 5 · 交付前自检（每项必须勾上，未全部通过则回到 Step 1 重做）**

- [ ] 文件行数 ≥ 原型行数的 95%（原型约 1555 行，成品 ≥ 1475 行）
- [ ] `<style>` 块完整保留，未被精简
- [ ] `#themeSelect`、`#accentPicker`、`#exportBtn` 三个核心控件 id 均存在
- [ ] `.topbar-title-edit`、`.topbar-meta-edit` 两个铅笔按钮存在且可聚焦
- [ ] 文件含 `<script src="https://cdn.jsdelivr.net/npm/modern-screenshot@4/dist/index.js"></script>` 的 **jsDelivr CDN** 引用
- [ ] 导出逻辑包含 `isInIframe()` / `directDownload()` / `showExportModal()` 三个函数，及 `.export-modal-*` / `.export-preview-link` 相关 CSS
- [ ] `showExportModal` 内使用 `FileReader.readAsDataURL(blob)` 把预览图 `src` 切换成 base64 data URL，并用 `<a class="export-preview-link" download>` 包裹 `<img>`（sandbox iframe 下 Mac Option + 点击 / Windows 右键另存的唯一条件）
- [ ] 浮层内**未**出现「下载到本地 / 复制到剪贴板 / 新窗口打开」等动作按钮（sandbox 已实测全拦，是无效噪音）；浮层文案含「强烈推荐系统浏览器打开」+ Mac / Windows 分平台操作说明
- [ ] `<body>` 属性齐备：`data-theme` / `data-ratio="16-9"`（横版默认）/ `data-scale="md"`（中号默认）三者均存在
- [ ] `<body data-theme="...">` 已按 6.3 规则设置为匹配项目类型的风格
- [ ] 7 张卡片的顺序、class、SVG icon 与原型一致
- [ ] 设计标准每个 `<li>` 均以 `<span class="tag" data-kind="quant|qual">` 开头（行首 pill）
- [ ] 未引入任何 Tailwind / Bootstrap / 外部 CSS 框架
- [ ] 未出现任何"自定义"颜色/字号/阴影/圆角（所有视觉 token 均来自原型 CSS 变量）
- [ ] **视觉验证**：如平台支持 `present_files` 或浏览器预览，展示 HTML 给用户确认（重点检查：策略维度卡片数量与网格匹配、文字未溢出）。不支持预览时提示用户手动在浏览器打开检查。

#### 6.2 生成时必须同步替换的字段

- HTML `<title>` 标签 → 替换为项目名称（例："Design Brief — [项目名称]"）
- `.topbar-title` 文本 → 替换为项目名称
- `.topbar-meta` 文本 → 替换为"[项目子类型] · [生成日期 YYYY-MM-DD]"（例：`产品迭代 · 2026-04-29`）
- 7 个 `.card` 内容 → 按 Phase 3 收集的字段填入
- `<body>` 的 `data-theme` → 设为本项目匹配的默认风格（见下方风格规则）

#### 6.3 默认风格规则（根据项目类型自动匹配）

| 项目类型                | 默认风格 | 备选推荐          |
| ----------------------- | -------- | ----------------- |
| 产品设计（迭代 / 改版） | Chalk    | Script、Slate     |
| 产品设计（全新产品）    | Script   | Chalk、Parchment  |
| 营销与传播              | Frame    | Noir、Onyx        |
| 品牌设计                | Noir     | Parchment、Script |
| 研究与评估              | Slate    | Parchment、Stone  |
| 系统与资产              | Stone    | Chalk、Slate      |
| 特殊介质                | Frame    | Noir、Terminal    |
| 管理类                  | Slate    | Chalk、Stone      |

生成后告知用户："已用 [风格名] 风格生成（完全基于 prototype/brief.html 模板克隆，仅替换文字字段），可在底部工具栏切换主题 / 自定义主题色 / 切换布局（横版 / 竖版 / 方版）/ 调整整体字号，满意后打印或导出 PNG。"

### Phase 7 — 保存项目上下文（双通道输出）

按 [chain-protocol.md](../../chain-protocol.md) 第 2.1 节的双通道规则同时输出：

按 [chain-protocol.md](../../chain-protocol.md) §2.1 v1.1 智能适配规则：

**Step 1 — 写盘到 `spark-output/context/brief.json`**（必做，主持久化通道；目录不存在先创建）。

⛔ **JSON 安全**（详见 chain-protocol.md §2.1.2）：写入前**必须检查所有字符串值中的引号字符**。用户原文中的中文弯引号 `""`（U+201C/U+201D）必须替换为 `「」`，否则会被存储为 ASCII `"` 破坏 JSON 结构，导致下游全链路（Dashboard 更新 + 下游 Skill 读取）解析失败。写盘后用 `python3 -c "import json; json.load(open('spark-output/context/brief.json'))"` 自检。

写入以下完整 JSON：

```
{
  "skill": "brief",
  "generated_at": "<ISO8601 当前时间>",
  "project_name": "",
  "project_type": "",
  "project_subtype": "",
  "business_context": "",
  "business_goal": [],
  "user": [],
  "strategy_dimensions": [
    {
      "dimension": "",
      "thesis": "",
      "tactics": [],
      "rationale": ""
    }
  ],
  "design_criteria": { "quantitative": [], "qualitative": [] },
  "constraints": [],
  "out_of_scope": [],
  "style": "",
  "ratio": "16-9",
  "scale": "md"
}
```

**Step 2 — chat 输出紧凑 marker**（必做，⛔ **不要在 chat 内重复输出 Step 1 的完整 JSON**）：

```
<!-- spark-context:brief ref="spark-output/context/brief.json" -->
Brief 已保存：project=[project_name]，project_type=[type/subtype]，persona=[user 第一条简述]，[N] 个 strategy_dimensions
<!-- /spark-context:brief -->
```

**降级 fallback**：若 Step 1 写盘失败（chat-only 平台），输出完整 JSON marker（无 ref 属性，marker 之间放裸 JSON）作为唯一持久化通道。

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

### Handoff 提示（必输出）

> **协议**：按 [`_shared/next-skill.md`](../../_shared/next-skill.md) 三层结构模板输出；前 5 候选由 `_shared/skill-graph.json` 的依赖图算法实时算（done ⊆ ready，按 next_hint.preferred → alternatives → 同阶段 → anchor → fan-out 排序），优先建议从 `_shared/skill-graph.json#skills[id="brief"].next_hint` 读取。

**首行模板**：`✅ 设计简报 已完成，business_goal + 5 维 strategy_dimensions + 9 项 design_criteria 已沉淀。`

**本 Skill 的 `next_hint`**（来自 skill-graph.json，**不可在此 SKILL.md 内硬编码覆盖**）：

- **preferred**：`/journey`
- **优先理由**：用户视角可视化（含情感曲线 + dropout-risk 标注）通常是 Brief 之后最有价值的一步——把抽象策略变成可视的体验断点。
- **alternatives**：`/stories` (想直接做工程拆解走结构化路径) · `/pitch` (需要先对齐决策者再执行) · `/sitemap` (已确定走 IA 优先路径)
- **emoji**：🎨

**红线**：
- ❌ 禁止在本段硬编码候选清单（如「进入 Stories / Journey / Sitemap」）——所有候选必须由算法实时生成
- ❌ 禁止按「文档类 / 视觉类 / 决策类」再分类候选（v0.5.5 起，分类已折叠进 next_hint.alternatives）
- ❌ 禁止与「更新链路面板」段合并——两段必须各自独立成段，中间空一行
- ❌ 禁止漏第 2 行候选清单——即使候选只有 1 个、或为空（终端节点）也要写出来

---

## 字段结构（Route A）

### 通用模块（7 个，所有类型必填）

| # | 模块     | 英文标题         | 说明                                                                                                                                  |
| - | -------- | ---------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| 1 | 业务背景 | Business Context | 当前业务处于什么阶段，触发本次设计的原因                                                                                              |
| 2 | 业务目标 | Business Goal    | 本次设计要推动哪些可量化的业务结果（KPI）                                                                                             |
| 3 | 用户     | User             | 主要受众是谁，核心使用场景是什么                                                                                                      |
| 4 | 设计策略 | Design Strategy  | 从哪些维度切入，用什么设计方法应对目标                                                                                                |
| 5 | 设计标准 | Design Criteria  | 体验层面的完成判断（单列列表，每条行首带 `定量` / `定性` pill 标签，`data-kind="quant"` 用 accent 染色，`"qual"` 用中性描边） |
| 6 | 边界约束 | Constraints      | 时间、技术、资源、规范等硬性限制                                                                                                      |
| 7 | 不做什么 | Out of Scope     | 本次明确排除的内容，防止范围蔓延                                                                                                      |

**字段区分说明：**

- 业务目标 = 业务 KPI（转化率、留存率等可量化结果）
- 设计标准 = 体验层面的判断依据（任务完成率、SUS 评分等），单列混合列表，每条用行首 pill 标注定量 / 定性

### 各类型专属字段

**产品设计 — 全新产品**

| 专属必填         | 专属可选           |
| ---------------- | ------------------ |
| 业务指标、技术栈 | 参考方向、排斥方向 |

**产品设计 — 产品迭代**

| 专属必填                                                                | 专属可选           |
| ----------------------------------------------------------------------- | ------------------ |
| 上下文输入（已有研究 / 历史版本结论）、受影响已有模块、业务指标、技术栈 | 参考方向、排斥方向 |

**产品设计 — 产品改版**

| 专属必填                                         | 专属可选           |
| ------------------------------------------------ | ------------------ |
| 上下文输入、改版范围、保留元素、业务指标、技术栈 | 参考方向、排斥方向 |

**营销与传播 — 营销设计**

| 专属必填                               | 专属可选           |
| -------------------------------------- | ------------------ |
| 投放平台、核心卖点、上线时间、传播目标 | 参考方向、排斥方向 |

**营销与传播 — 会议与活动**

| 专属必填                                | 专属可选           |
| --------------------------------------- | ------------------ |
| 活动时间地点、签到 / 互动形式、传播目标 | 参考方向、排斥方向 |

**营销与传播 — 线下物料**

| 专属必填                   | 专属可选           |
| -------------------------- | ------------------ |
| 物料尺寸规格、印刷工艺限制 | 参考方向、排斥方向 |

**营销与传播 — 视频设计**

| 专属必填                 | 专属可选           |
| ------------------------ | ------------------ |
| 时长、画幅比例、配乐方向 | 参考方向、排斥方向 |

**品牌设计 — 全新品牌**

| 专属必填                         | 专属可选           |
| -------------------------------- | ------------------ |
| 调性关键词（3–5个）、交付物范围 | 参考方向、排斥方向 |

**品牌设计 — 品牌升级**

| 专属必填                         | 专属可选           |
| -------------------------------- | ------------------ |
| 调性关键词、保留元素 vs 可变元素 | 参考方向、排斥方向 |

**研究与评估 — 用户研究**

| 专属必填                                 |
| ---------------------------------------- |
| 研究方法、样本量、研究问题、结论交付形式 |

**研究与评估 — 设计走查**

| 专属必填                         |
| -------------------------------- |
| 评估框架、走查范围、结论交付形式 |

**研究与评估 — 设计咨询**

| 专属必填                         |
| -------------------------------- |
| 咨询聚焦点、决策方、结论交付形式 |

**系统与资产 — 设计系统与规范**

| 专属必填                                         | 专属可选           |
| ------------------------------------------------ | ------------------ |
| 覆盖范围、与现有系统关系、首批组件优先级、使用者 | Token 层级设计需求 |

**特殊介质 — 硬件设计**

| 专属必填                            |
| ----------------------------------- |
| 硬件规格、使用环境、材料 / 工艺限制 |

**特殊介质 — 互动设计**

| 专属必填           |
| ------------------ |
| 交互模态、技术平台 |

**管理类**

| 专属必填                                           | 专属可选                   |
| -------------------------------------------------- | -------------------------- |
| 时间周期、关联 OKR、核心目标、优先级排期、成功标准 | 资源分配、主要 Stakeholder |
| 执行路径（替代"设计策略"）                         | —                         |

---

## 视觉输出规格（Route C）

### Bento 布局

> **关于"布局"而非"比例"：** 工具栏提供"横版 / 竖版 / 方版"三套布局模板（底层 `data-ratio` 仍为 `16-9 / 4-3 / 1-1`，仅切换 grid 排版）。画布宽度固定 1280px、**高度完全跟内容**，不再强制锁定画幅比例 —— 所见即所导。

**横版（默认，`data-ratio="16-9"`）** — 4 列 × 3 行，适合 Keynote / 幻灯片：

```
[业务背景 ×2列] [业务目标 ×1列] [用户 ×1列]
[设计策略 ×3列]               [设计标准 ×1列]
[边界约束 ×2列] [不做什么 ×2列]
```

**方版（`data-ratio="1-1"`）** — 3 列 × 4 行，顶部通栏 + 底部对半，适合社媒分享：

```
[业务背景 ×3列 顶部通栏]
[业务目标 ×1] [用户 ×1]       [设计标准 ×1]
[设计策略 ×3列]
[边界约束 ×1.5列] [不做什么 ×1.5列]
```

实现用 6 列子网格：业务背景 / 设计策略各 span 6，业务目标 / 用户 / 设计标准各 span 2，边界约束 / 不做什么各 span 3。

**竖版（`data-ratio="4-3"`）** — 3 列 × 4 行，底部对半，适合 A4 / 文档：

```
[业务背景 ×1.5列]              [业务目标 ×1.5列]
[用户 ×1]        [设计策略 ×2列 × 跨2行]
[设计标准 ×1]
[不做什么 ×1.5列]              [边界约束 ×1.5列]
```

实现用 6 列子网格：业务背景 / 业务目标 / 不做什么 / 边界约束各 span 3，用户 / 设计标准各 span 2，设计策略 span 4 列 × 2 行。

### 风格体系

HTML 内嵌所有风格的 CSS 变量，通过 `data-theme` 属性切换，无需重新加载。

**已实现的 9 个风格（工具栏下拉完整可用）：**

| 名称      | 原型参照   | 背景           | 字体                   | 调性             |
| --------- | ---------- | -------------- | ---------------------- | ---------------- |
| Chalk     | cursor     | 浅灰 #dcdcda   | Inter                  | 干净·开发·极简 |
| Parchment | claude     | 暖米 #d4cfc7   | Cormorant Garamond     | 温润·人文·AI   |
| Script    | elevenlabs | 暖白 #e2e2de   | EB Garamond            | 精致·编辑·衬线 |
| Noir      | bugatti    | 纯黑 #0a0a0a   | Cormorant Garamond     | 极奢·戏剧·衬线 |
| Frame     | runwayml   | 极深灰 #060606 | DM Sans + DM Mono      | 创意·暗调·AI   |
| Onyx      | shopify    | 纯黑 #000000   | Inter + JetBrains Mono | 干净·暗色·商业 |
| Stone     | neutral    | 浅灰 #dcdcdc   | DM Mono                | 中性·冷静·工程 |
| Slate     | stripe     | 冷白 #e8edf3   | Inter                  | 精准·企业·金融 |
| Terminal  | xai        | 深灰 #131518   | JetBrains Mono         | 终端·极客·低调 |

> 原规划中的 Paper（mintlify）、Pulse（verge）、Blueprint / Signal / Canvas / Void / Ink 均已从工具栏移除，不再作为默认或扩展风格。Paper / Pulse 待 CSS 补齐后再考虑加回。

### HTML 工具栏规格

工具栏位于 Brief Canvas 下方，左右两组：

```
[主题 ▾] [🎨 accent]  |  [布局 横版 | 竖版 | 方版]  |  [字号 小 | 中 | 大]    [打印 / PDF] [导出 PNG]
```

**左侧控件（`.toolbar-left`）：**

- **主题下拉**：`<select id="themeSelect">`，选中即时切换 `data-theme`，无动画延迟。
- **主题色自定义**：`<input type="color" id="accentPicker">` 圆形色板，实时覆盖 `--accent`；切换主题时自动回填该主题的默认 accent。
- **布局按钮组**：`横版 / 竖版 / 方版` 三按钮（底层仍切换 `data-ratio`），默认激活 **横版**。激活态反色（`background: var(--text); color: var(--brief-bg)`）。画布高度完全跟内容走，不再强制锁定比例 —— 所见即所导。
- **字号按钮组**：`小 / 中 / 大` 三按钮，切换 `data-scale`（对应 `--size-mult` = 1 / 1.2 / 1.45），所有字号 token 等比缩放，默认激活 **中**。

每次任一切换后都会调用 `fitCards()` 重新检测卡片内容是否溢出。

**右侧控件（`.toolbar-right`）：**

- **打印 / PDF**：调用 `window.print()`，`@media print` 隐藏工具栏。
- **导出 PNG**：调用 `modern-screenshot`（jsDelivr CDN 加载）的 `domToBlob(#brief-canvas, { scale: 2, backgroundColor: 页面背景色, type: 'image/png' })` 生成 Blob。**根据运行环境自动分流**：
  - **独立浏览器（`window.top === window`）**：用 `URL.createObjectURL` + 临时挂 DOM 的 `<a>` 一键下载，按钮显示"已保存 ✓"。
  - **iframe 预览态（qoderwork 对话卡片、Notion embed 等，sandbox 同时拦截了 `<a>.click()` / `clipboard.write` / `window.open`，实测三条路径全无效）**：弹出 `.export-modal` 浮层，浮层内仅保留 `<a class="export-preview-link" href="<data-url>" download>` 包裹的预览图，不得添加任何动作按钮（都是无效噪音）。文案给用户两条路径：
    1. **强烈推荐：在系统浏览器（Chrome / Safari / Edge）中打开此 HTML** ——一键下载，无需额外操作，是最可靠路径；
    2. 若必须在预览态导出，在预览图上：**Mac 用 Option + 点击**触发下载弹窗；**Windows 用右键 → 图片另存为…**。
    
    **实现要点**：先用 `URL.createObjectURL(blob)` 兜底 `previewImg.src` 和 `.export-preview-link[href]`，再异步 `new FileReader().readAsDataURL(blob)`，`onload` 里把两者切换成 `data:image/png;base64,...`（blob URL 会被 sandbox 判为跨源导致右键菜单置灰 / Option 点击失效）。

  按钮保留 loading 态（"生成中…"）+ 成功反馈（"已保存 ✓" / "请在浮层点图保存 →"）+ 防抖。导出开始会给 `<body>` 加 `is-exporting` 类名，临时隐藏 topbar 铅笔按钮，避免 wrap 压缩导致文字折行。浮层关闭或 8 秒后 `revokeObjectURL` 释放。

### 字体加载

```html
<!-- Google Fonts 优先，系统字体回退；仅加载 9 套主题实际使用的字族 -->
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;500;600
  &family=DM+Mono:wght@300;400;500
  &family=DM+Sans:wght@300;400;500
  &family=EB+Garamond:wght@400;500
  &family=Inter:wght@300;400;500;600;700
  &family=JetBrains+Mono:wght@400;500
  &family=Noto+Sans+SC:wght@400;500;600
  &display=swap" rel="stylesheet">
```

离线时回退：`-apple-system, 'PingFang SC', sans-serif`（无衬线）/ `Georgia, serif`（衬线）。

---

## 输出物

本 Skill 产出一个完整可运行的 HTML 文件（`prototype/brief.html`），包含：

1. 顶部项目信息栏（项目名称、类型、日期 + 右侧 "DESIGN BRIEF" brand 标识），**标题与元信息支持 hover 铅笔按钮 → 点击即编辑**（刷新恢复 AI 默认值；导出 PNG 时自动隐藏铅笔防折行）
2. Bento 布局的 7 模块 Brief Canvas（每模块配 SVG line icon）
3. 底部工具栏（主题下拉 + 主题色自定义 + 布局切换 + 字号缩放 + 打印 / 导出）
4. 所有已实现风格的 CSS 变量（9 套，通过 `data-theme` 切换）
5. `modern-screenshot` 导出逻辑：`domToBlob` + `URL.createObjectURL` + iframe 检测分流（独立浏览器一键下载；iframe 预览态弹浮层提供「下载 / 剪贴板 / 新窗口 / 图片右键另存」四条兜底路径），含 loading 态 + 防抖 + 成功反馈 + `is-exporting` 防折行
6. 卡片内容自适应缩放（`fitCards`：溢出时逐级降低字号至 9px 下限）

HTML 中不依赖外部框架，仅依赖：

- Google Fonts（远程 CSS，需联网加载字体，不联网则自动回退到系统字体）
- `modern-screenshot` UMD（通过 jsDelivr CDN 加载，用于"导出 PNG"）

> 原方案曾用同目录 `./modern-screenshot.umd.js` 本地引用，但在 qoderwork 等工作流中生成 HTML 时不会自动同步拷贝二进制文件，导致"导出 PNG"报 `modernScreenshot is not defined`。现统一改为 CDN，生成后无需任何附加文件即可使用。

---

## 质量规范

> 本章节是 Skill 完成度的**高层判定标准**，与 Phase 6 内部的执行级约束互补。Phase 6 是"该怎么做"，本章节是"做对了没有"。

### 🚫 红线规则（违反即任务失败，无降级空间）

- **视觉产物必须基于 `prototype/brief.html` 克隆**——不得自写 HTML / CSS / JS，不得引入任何 UI 框架（详见 Phase 6.0）
- **必须输出双通道**：`spark-output/context/brief.json` 写盘 + chat 内紧凑 marker（含 `ref=` 属性）
- **必须按 chain-protocol §2.1 v1.1.1 执行顺序**：先写盘 → 自检行 → 渲染报告 → marker → handoff，不得颠倒
- **7 张卡片的 DOM 顺序、class 名、SVG line icon 必须与原型逐字一致**
- **设计标准每条必须以 `<span class="tag" data-kind="quant|qual">` 行首 pill 开头**，不得放行尾纯文字
- **三轮路径定位都失败才停止**——单次 read_file 失败必须先用文件搜索工具定位（详见 Phase 6 路径解析协议），不得凭印象编造仓库结构路径，也不得直接降级输出 markdown 版本

### ⚠️ 反模式（常见错误，需主动规避）

- ❌ 把"业务目标"和"设计标准"混为一谈——前者是业务 KPI（如"转化率提升 8%"），后者是体验判断依据（如"任务完成率 > 88%"）
- ❌ 按字段编号顺序追问（1→2→3...）——必须按依赖顺序：**业务背景 → 业务目标 → 用户 → 设计策略 → 设计标准 → 边界约束 → 不做什么**
- ❌ 在 Phase 4 跳过 Phase 4.5 直接走 4.6 追问——草稿在前（AI 先写），追问只处理被否决的维度
- ❌ 在 chat 内重复输出完整 JSON——应只输出紧凑 marker（≤ 80 字摘要），完整 JSON 写盘到文件
- ❌ 凭记忆重建 HTML 模板——必须每次 read_file 实际读取 `prototype/brief.html`
- ❌ 删除或"简化"工具栏控件、topbar 铅笔按钮、modern-screenshot 导出逻辑——它们是产物功能完整性的必需 DOM
- ❌ handoff 漏列下游 Skill 或按"推荐顺序"建议——应按"文档 / 视觉 / 决策"三类完整覆盖

### ✅ 质量标准（通过条件，全部满足才算交付）

**内容完整性**：
- 7 个通用模块全部有实质内容（非空、非"待定"、非"TBD"）
- 各字段字数符合 Phase 3 表格上限（HTML 卡片容量约束）
- 至少 2 个 `strategy_dimensions`，每个含 `dimension + thesis + tactics`（rationale 可空）
- 项目类型对应的专属字段已填（见「字段结构」章节）

**HTML 产物完整性**：
- 文件行数 ≥ 原型 95%（原型约 1555 行，成品 ≥ 1475 行）
- Phase 6.1 Step 5 自检清单全部勾选通过
- 浏览器打开后：主题切换 / 布局切换 / 字号缩放 / topbar 编辑 / 导出 PNG 五项功能均可用

**链路接入正确性**：
- `spark-output/context/brief.json` 文件已写入且 schema 符合 frontmatter 定义
- chat marker 含 `ref="spark-output/context/brief.json"` 属性
- 下游 Skill（Stories / Sitemap / Flow Web 等）调用时能正确读取本 Brief 上下文
- 已输出符合 Phase 7 Handoff 模板的下一步建议
