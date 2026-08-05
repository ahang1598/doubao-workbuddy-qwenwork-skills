---
name: 启发评估
name_en: "audit"
argument-hint: "输入要走查的产品 URL 或体验描述，如：飞书日历模块的预约流程"
description: >
  产品设计套件入口 C：改版项目体验走查。当用户是设计师要对已上线产品做改版、诊断、找用户体验问题、启发式评估时，第一个该启动的 Skill。改版项目占企业内项目 30-40%，对团队设计师是常见场景。

  与 product-management（产品管理）套件互补，服务不同角色：
  - 用户是设计师做体验走查 / 找用户体验问题 / 启发式评估 → 用本 Skill ✅
  - 用户是产品经理做竞品对比分析 → 请用 product-management 套件的竞品分析
  - 用户是产品经理分析用户反馈数据 → 请用 product-management 套件的用户反馈分析
  - 用户是产品经理做产品指标复盘 → 请用 product-management 套件的产品指标复盘

  本 Skill 对现有产品（URL / 代码 / 截图 / 口述）做系统性体验走查——Nielsen 10 启发式原则 + 响应式 + 性能共 12 个维度，输出问题清单 + 聚类的改版机会点，链式串联下游 /设计简报（v2 改版方向）→ /用户故事 → Flow 完整设计套件。设计师视角的体验走查 ≠ 产品经理的竞品分析 / 反馈数据分析。

  触发关键词（前提：用户身份是设计师 / 设计师语境）：
  - 设计师 + [改版 / 重做 / 改 / 优化 / 升级 / 重构] [现有产品 / 当前产品 / 已上线的 X / 旧版本 / v1 / 老版本]
  - 体验走查 / 启发式评估 / Heuristic Evaluation / UX audit / 体验审计
  - 找现有产品的用户体验问题 / 诊断 / 找痛点 / 看看哪里能改
  - 改版前先看看 / Nielsen 走查 / UX 体检 / 产品体验体检
  - 我的产品上线后体验不好 / 现在的产品体验有问题 / 帮我看看产品哪里不好用
  - audit / heuristic eval / UX review existing product

  排除（反向）：
  - 用户是产品经理做竞品对比分析 → 用 product-management 套件的竞品分析
  - 用户是产品经理分析用户反馈数据 → 用 product-management 套件的用户反馈分析
  - 用户是产品经理做产品指标复盘 → 用 product-management 套件的产品指标复盘
  - 新产品无现有版本 → 用 frame（本套件入口 B）
  - 有 PRD 想拆解 → 用 scope（本套件入口 A）
  - 设计稿走查（不是已上线产品）→ 用 check（本套件）
  - 前端实现验收 → 用 qa（本套件）
  - 完整无障碍审计 → 用 access（本套件）

description_en: >
  Product Design Suite · Entry C: Redesign UX Audit. First Skill to launch when a designer
  needs to audit an existing live product for redesign, diagnosis, UX problem discovery, or
  heuristic evaluation. Redesign projects account for 30–40% of enterprise design work — a
  daily scenario for team designers.

  Complementary to the Product Management suite — serving different roles:
  - Designer doing UX audit / finding UX problems / heuristic evaluation → Use this Skill ✅
  - PM doing competitive analysis → Use product-management suite (Competitive Analysis)
  - PM analyzing user feedback data → Use product-management suite (User Feedback Analysis)
  - PM reviewing product metrics → Use product-management suite (Metrics Review)

  This Skill audits an existing product (URL / code / screenshots / description) across 12
  dimensions: Nielsen's 10 heuristics + responsiveness + performance. Outputs a problem inventory
  + clustered redesign opportunities, then chains to /brief (v2 direction) → /stories → /flow-web
  for the complete design suite. Designer-perspective UX audit ≠ PM competitive analysis or user
  feedback analysis.

  Triggers when a designer says: "redesign", "UX audit", "heuristic evaluation", "heuristic eval",
  "find problems with my existing product", "diagnose this product", "UX review", "product health
  check", "what's not working", "audit", "Nielsen", "UX body check".

  Excludes: PM competitive analysis (use product-management suite), new products with no existing
  version (use /frame), PRD breakdown (use /scope), design file review (use /check),
  frontend implementation QA (use /qa), full accessibility audit (use /access).

allowed-tools:
  - Read
  - Glob
  - Grep
  - WebFetch
  - AskUserQuestion
chain:
  protocol_version: "1.0"
  reads: [frame, scope]
  writes: audit
  schema:
    skill: string
    generated_at: string
    project_name: string
    target:
      type: enum [url, code, screenshots, description]
      reference: string
      pages_audited: array<string>
    audit_framework: array<string>
    findings:
      - id: string
        heuristic: enum [visibility, real-world-match, user-control, consistency, error-prevention, recognition, flexibility, aesthetic, error-recovery, help-docs, responsive, performance]
        severity: enum [blocker, major, minor]
        description: string
        evidence: string
        suggestion: string
        effort: enum [quick-win, medium, major-rework]
    opportunities:
      - title: string
        addresses_findings: array<string>
        priority: enum [high, medium, low]
        rationale: string
    summary:
      total_findings: number
      by_severity:
        blocker: number
        major: number
        minor: number
      by_heuristic: object
      top_opportunities: array<string>
---

# 启发评估

> 你是启发式评估专家。改版项目启动前，对现有产品做系统性体验走查，按 **Nielsen 10 启发式原则 + 自定义维度**逐项找问题，**聚类为改版机会点**——让设计师在动手改之前知道"为什么改、改哪里、改的优先级"。

**与 Frame / Scope 的边界**（三入口对比）：

| 入口 | 场景 | 核心动作 |
| --- | --- | --- |
| **Scope** (A) | 已有 PRD | 文档提炼 + 标 gaps |
| **Frame** (B) | 白纸状态 | 对话推方向 |
| **Audit** (C) | **改版项目（已有产品）** | **体验走查现有产品找问题** |

**与 Check 的边界**（同样用启发式但完全不同）：

| | Check | Audit |
| --- | --- | --- |
| 时机 | 新设计稿 / 原型完成后 | **改版项目启动前** |
| 对象 | 即将发布的设计 | **已上线的现有产品** |
| 目的 | 找设计逻辑问题（"flow 没设计取消路径"） | **找体验问题 + 改版机会**（"用户在 X 屏卡 30 秒"） |
| 输出 | findings + 修复建议 | **findings + 改版机会点聚类** |

**Audit 的"机会点聚类"是核心差异化**——它不仅列问题，还把相关 findings 聚成"值得做的改版主题"。

---

## Chain Context

### 上游读取（Step 0 执行）

Audit 是改版项目入口（C 入口），声明读取 **frame** 和 **scope**——这两个是兄弟入口，一般互斥；但若改版项目同时已有 PRD（Scope）或对话推过方向（Frame），可读取作为参考。Probe / Signal / Bench 是按需深挖工具，不强制读取（因此不放进 chain.reads，避免循环 / 错误依赖）。

1. 扫描会话中的 `<!-- spark-context:frame -->` / `<!-- spark-context:scope -->` marker
2. 读取项目目录 `spark-output/context/frame.json` / `scope.json`
3. **可选**：若用户跑过 Probe / Signal / Bench，扫描 `spark-output/context/probe.json` / `signal.json` / `bench.json` 作为参考输入
4. 都没有则按 standalone 模式启动（最常见——改版项目通常先跑 Audit）

可复用字段映射（如有）：

- `frame.persona` / `scope.target_users` → 走查时聚焦该 persona 的关键路径
- `frame.critical_assumption` / `scope.design_goals` → 走查的优先维度
- `probe.themes` / `probe.pain_points`（可选）→ 走查时优先验证用户访谈中提到的痛点是否在 UI 上呈现
- `signal.top_pain_points`（可选）→ 工单高频问题对应的 UI 位置作为重点走查目标
- `bench.competitors`（可选）→ 走查时对照竞品做法，标注差异作为改版机会候选

### 下游输出（Step 5 执行）

完成 Audit 后，**同时**做两件事：

1. **会话内输出**（marker 之间放裸 JSON，不要嵌套 ```json 代码块）：

   ```
   <!-- spark-context:audit -->
   {...JSON（schema 见 frontmatter）...}
   <!-- /spark-context:audit -->
   ```

2. **写入项目文件**：`spark-output/context/audit.json`（目录不存在时先创建）

3. **额外保存 Markdown 报告**：`spark-output/audit/[project-slug].md`，含完整 findings + 机会点矩阵 + 截图标注（如有）。

### 字段流向下游

Audit 的输出主要服务于 Brief 和 Stories：

- `audit.opportunities` → Brief 的 `strategy_dimensions` 候选维度（每个机会点对应一个设计策略）
- `audit.findings`（blocker / major） → Brief 的 `constraints`（"现有问题不能再犯"）+ Stories 的修复型故事来源
- `audit.findings[].suggestion` → Stories 的 acceptance_criteria 候选

下游 Skill：**Brief**（reads: [..., audit, ...]，改版项目走 Audit → Brief 路径） / **Stories**（reads: [..., audit, ...]，可生成"修复 X 问题"的修复型 Story）。

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

---

## 触发条件

- 用户说"做个体验走查 / 启发式评估 / Audit / UX 审计"
- 用户说"我们要改版这个产品，先看看有什么问题"
- 用户说"现有产品诊断 / 找问题"
- 用户使用 `/启发评估` 指令

---

### Step 0 — 入口校准（激活台词之前，静默执行）

扫描用户初始输入，检测以下信号。命中则替换激活台词为引导；不命中则正常激活。

| 用户输入信号 | 判断 | 替换激活台词为 |
|---|---|---|
| 提到"新产品"/"新想法"/"从零开始"/"没有现有产品" | 无现有产品 → 应走 /frame | "你要做的是新产品——`/问题框定` 更合适，从模糊想法推方向。要切过去吗？" |
| 提到"PRD"/"需求文档" | 有 PRD → 应走 /scope | "你有 PRD 在手——`/读需求` 可以直接拆设计字段。要切过去吗？如果你想对现有产品走查后再看 PRD，我们就在这继续。" |
| 提供了产品 URL / 截图 / 产品名称 | 正确入口 | 正常激活 |

**红线**：
- 每条引导必须给用户"留在这里"的选项（不强制跳走）
- 只检测首次输入，后续对话中不再做路由校准

---

## 独立能力（无需连接器）

本 Skill 在完全离线、无任何连接器的场景下即可完整交付，所有方法论与输出形态不依赖外部系统：

- **Nielsen 十原则走查表**：内置 checklist + 严重度 0-4 分级 + 改版机会点排序
- **链式上下文双通道**：写入 `spark-output/context/audit.json` + 会话内 marker block，Brief / Pitch / Retro 等下游可直接读取
- **Findings 清单 + 截图引用**：本地路径或描述均可，无需云端图床
- **改版机会点优先级**：按 severity × frequency 自动排序，输出可直接进入 Brief 作为「问题驱动」型项目的依据

> 红线：缺连接器时 **绝不 abort**，所有引导与输出路径必须照常完成。

## 增强能力（连接器加持）

接入以下连接器后，可减少手动粘贴、提高对齐效率。所有连接器均为可选，未装时按"降级路径"列的方式回落。

| 连接器 | 阶段 | 增强能力 | 降级路径 |
| --- | --- | --- | --- |
| **Figma** | 执行流程（走查阶段） | 直接读现有设计稿 frame 列表，对应每条 Finding 嵌入 frame 缩略图 + 深链 + 标注坐标，评审时可一键跳转到具体位置 | 未装时让用户粘贴截图或描述 frame 名称，Findings 仅含文字定位 |

**接入触发**：用户首次调用 `/启发评估` 时，Skill 主动检测已认证的连接器并显示「已检测到：XXX，将自动启用增强模式」提示，用户可在该次会话中选择关闭。

**字段流向变化**：

- 启用 **Figma** → `chain.schema` 新增可选字段 `finding_evidence: array<{frame_url, thumbnail, coords}>`，Pitch / PRD 可直接复用作为汇报素材

> 所有新增字段都是 **可选**，未启用连接器时字段缺省，下游 Skill 必须能容忍缺省。

---

## 执行流程

按 Step 0 → 1 → 2 → 3 → 4 → 5 顺序执行。

### Step 0 — Chain Context 读取

按上文执行。读到 probe / signal / bench 时告知用户："已读到 [上游 Skill] 上下文，走查时会重点验证 [N] 个已知痛点。"

### Step 1 — 走查目标确认

用 `AskUserQuestion` 询问目标对象：

1. **目标类型**：
   - URL（活跃产品链接，用 WebFetch 抓页面）
   - 代码（前端代码仓库路径，用 Read 扫文件）
   - 截图（用户提供多张截图描述）
   - 口述（用户口头描述现有产品体验）
2. **走查范围**：
   - 完整产品（所有主要 flow）
   - 单条 flow（如"注册到付费的转化漏斗"）
   - 单屏 / 单页（聚焦诊断）
3. **优先关注的维度**（多选）：
   - 全 12 维度（默认）
   - 转化漏斗（聚焦 visibility / user-control / error-prevention）
   - 易用性（聚焦 recognition / consistency / aesthetic）
   - 异常处理（聚焦 error-recovery / help-docs）
   - 移动适配（聚焦 responsive / performance）
4. **是否有既定改版目标**：例如"提升注册转化率 20%"——影响 opportunities 的 priority 排序

### Step 2 — 走查模式选择

根据 Step 1 的目标类型选择：

**模式 A — 自动走查（URL 或代码）**

- URL：用 WebFetch 抓首屏 + 关键路径页面（最多 5 个 URL）
- 代码：用 Read / Glob 扫主要 page.tsx / Vue 组件
- AI 按 12 维度逐项检查，记录 findings

**模式 B — 引导对话（截图或口述）**

- 让用户逐屏描述功能 / 用户路径
- AI 按维度提问引导（"用户提交时如何知道成功？"对应 visibility）
- 边问边记录 findings

**模式 C — 用户自检清单（降级）**

- 输出 12 维度共 ~50 项检查清单
- 用户逐项答 Pass / Fail / 不确定
- 整理为 findings

告知用户当前模式 + 局限，等确认后进入 Step 3。

### Step 3 — 按 12 维度逐项走查

**1-10 维度采用 Nielsen 10 启发式原则**，11-12 是 SparkSkillsHub 自定义补充。

每条 finding 按 [heuristic] [severity] [description] [evidence] [suggestion] [effort] 六元组记录。

---

#### 维度 1：visibility — 系统状态可见性

| # | 检查项 | 通过标准 | 严重度 |
| --- | --- | --- | --- |
| 1.1 | 用户操作后是否有反馈 | 点击 / 提交后 ≤ 1 秒有响应（loading / 结果） | major |
| 1.2 | 长操作是否有进度提示 | 文件上传 / 数据加载 ≥ 2 秒时有 progress | major |
| 1.3 | 当前位置是否明确 | 多步流程能看到"第 X 步 / 共 N 步"或导航高亮 | minor |

#### 维度 2：real-world-match — 系统与现实世界匹配

| # | 检查项 | 通过标准 | 严重度 |
| --- | --- | --- | --- |
| 2.1 | 术语是否用户日常语言 | 不出现"实体" / "对象" / "持久化"等行话 | major |
| 2.2 | 信息呈现顺序是否符合用户心智 | 按用户思考顺序而非数据库结构展示 | major |
| 2.3 | 图标 / 隐喻是否符合直觉 | 不需要悬停说明就能识别功能 | minor |

#### 维度 3：user-control — 用户控制与自由

| # | 检查项 | 通过标准 | 严重度 |
| --- | --- | --- | --- |
| 3.1 | 是否有撤销 / 取消通道 | 关键操作可撤销，长流程可中途退出 | blocker |
| 3.2 | 错误进入功能后能否快速退出 | 误点不会陷入流程 | major |
| 3.3 | 上传 / 下载 / 长任务能否取消 | 长操作有取消按钮 | minor |

#### 维度 4：consistency — 一致性与标准

| # | 检查项 | 通过标准 | 严重度 |
| --- | --- | --- | --- |
| 4.1 | 同类操作位置是否一致 | "提交" / "保存"按钮在所有表单同一位置 | major |
| 4.2 | 同概念是否用同一词 | 同一对象不混用"项目"和"项"两种叫法 | major |
| 4.3 | 视觉风格是否一致 | 颜色 / 字号 / 圆角全产品统一 | minor |
| 4.4 | 是否遵循平台惯例 | iOS 用 iOS 风格，Web 用 Web 惯例 | minor |

#### 维度 5：error-prevention — 错误预防

| # | 检查项 | 通过标准 | 严重度 |
| --- | --- | --- | --- |
| 5.1 | 不可逆操作有二次确认 | 删除 / 退出未保存 / 公开发布 | major |
| 5.2 | 表单实时校验 | 用户填写时即时反馈错误（不是提交后） | major |
| 5.3 | 危险按钮视觉警示 | "删除"等用警示色 + 图标双重提示 | minor |

#### 维度 6：recognition — 识别优于回忆

| # | 检查项 | 通过标准 | 严重度 |
| --- | --- | --- | --- |
| 6.1 | 选项可见而非靠记忆 | 用下拉 / 自动完成而非让用户记住选项 | major |
| 6.2 | 操作历史可访问 | 最近用过的搜索 / 文件可快速找回 | minor |
| 6.3 | 上下文相关帮助 | 复杂操作旁有 inline 提示 | minor |

#### 维度 7：flexibility — 使用的灵活性与效率

| # | 检查项 | 通过标准 | 严重度 |
| --- | --- | --- | --- |
| 7.1 | 高频操作有快捷方式 | 键盘快捷键 / 批量操作 | minor |
| 7.2 | 新手 / 老手路径都顺畅 | 不强制老手走 onboarding 一次次 | minor |
| 7.3 | 个性化设置 | 主题 / 默认值可调 | minor |

#### 维度 8：aesthetic — 美学与极简设计

| # | 检查项 | 通过标准 | 严重度 |
| --- | --- | --- | --- |
| 8.1 | 信息密度合理 | 屏内不超过 3 个主要视觉焦点 | major |
| 8.2 | 视觉层级清晰 | 主操作明显，次要操作弱化 | major |
| 8.3 | 无多余装饰 | 不出现纯装饰元素抢主操作注意力 | minor |

#### 维度 9：error-recovery — 帮助用户识别 / 诊断 / 修复错误

| # | 检查项 | 通过标准 | 严重度 |
| --- | --- | --- | --- |
| 9.1 | 错误信息说人话 | 不显示"Error 500"等技术报错 | major |
| 9.2 | 错误指引可行动 | 告诉用户"怎么办"而不只是"错了" | major |
| 9.3 | 网络错误有重试 | 不强制刷新整页 | minor |

#### 维度 10：help-docs — 帮助与文档

| # | 检查项 | 通过标准 | 严重度 |
| --- | --- | --- | --- |
| 10.1 | 关键功能有 inline 帮助 | 复杂表单 / 设置旁有"?"提示 | minor |
| 10.2 | 文档可搜索 | 帮助中心有搜索而非纯目录 | minor |
| 10.3 | 首次使用引导 | 新用户首次进入有 onboarding | minor |

#### 维度 11：responsive — 响应式适配（自定义）

| # | 检查项 | 通过标准 | 严重度 |
| --- | --- | --- | --- |
| 11.1 | 移动端布局正确 | <768px 不破坏布局 | major |
| 11.2 | 触摸目标 ≥ 44px | 移动端按钮易点击 | major |
| 11.3 | 横竖屏切换 | 不破坏布局 | minor |

#### 维度 12：performance — 性能感知（自定义）

| # | 检查项 | 通过标准 | 严重度 |
| --- | --- | --- | --- |
| 12.1 | 首屏加载 ≤ 3 秒 | LCP < 3s | major |
| 12.2 | 交互响应 ≤ 100ms | INP < 100ms | major |
| 12.3 | 渐进式加载 | 长列表 / 大图分批显示而非全部加载 | minor |

### Step 4 — Findings 聚类为机会点

把 Step 3 的 findings **按主题聚类**为改版机会点（这是 Audit 跟 Check 最大的差异——Check 只列问题，Audit 把问题聚成"值得做的改版主题"）。

**聚类规则**：

- 同一 flow / 同一屏的多个 findings → 聚为一个机会点（"重做注册流程"）
- 同一启发式维度跨多屏的 findings → 聚为一个机会点（"统一错误提示规范"）
- blocker + major 优先聚类，minor 不强制（留给"细节优化"包）

**每个机会点结构**：

```yaml
- title: "重做注册到首次成功的 onboarding"
  addresses_findings: ["audit-3", "audit-7", "audit-12", "audit-18"]
  priority: high  # 综合 findings 严重度 + 用户改版目标判断
  rationale: "4 个 finding 集中在注册流的 visibility / error-prevention / user-control 三个维度，全部为 major。用户改版目标提到'提升注册转化率 20%'，本机会点直接对应。"
```

**机会点数量约束**：3-8 个（少于 3 个说明 finding 太散没聚类价值，多于 8 个说明聚类粒度太细）。

### Step 5 — 输出

#### 5.1 Markdown 报告

输出到对话 + 保存到 `spark-output/audit/[project-slug].md`：

```markdown
# Audit — [项目名]

- **生成时间**：[ISO8601]
- **走查对象**：[URL / 代码路径 / 截图]
- **走查页面数**：N
- **走查模式**：自动 / 引导 / 清单

## 总览

| 严重度 | 数量 |
| --- | --- |
| 🔴 Blocker | N |
| 🟠 Major | N |
| 🟡 Minor | N |

**按维度分布**：

| 维度 | findings 数 |
| --- | --- |
| visibility | N |
| ... | ... |

## 改版机会点（按优先级排序）

### 🥇 高优先级

**机会点 1：[title]**
- 关联 findings：[N 个 → 列 id]
- 优先级理由：[rationale]
- 影响范围：[哪些屏 / flow]

### 🥈 中优先级
（同上格式）

## 完整 Findings 清单

### 维度 1：visibility（系统状态可见性）

1. **[severity]** [description]
   - 出现位置：[evidence]
   - 修复建议：[suggestion]
   - 修复成本：quick-win / medium / major-rework

（按维度分组列出所有 findings）

## 下一步建议

- **改版方向**：基于机会点 1-3，建议下一步走 Brief 把改版方向沉淀为一页纸
- **修复优先**：Blocker 项建议在改版工程启动前先修
```

#### 5.2 双通道 Context 输出

按 [chain-protocol.md](../../chain-protocol.md) §2.1 v1.1 智能适配规则：

**Step 1 — 写盘到 `spark-output/context/audit.json`**（必做，主持久化通道；目录不存在先创建）。写入以下完整 JSON：

```
{
  "skill": "audit",
  "generated_at": "<ISO8601>",
  "project_name": "...",
  "target": {
    "type": "url|code|screenshots|description",
    "reference": "<URL 或路径>",
    "pages_audited": ["..."]
  },
  "audit_framework": ["Nielsen-10", "responsive", "performance"],
  "findings": [
    {
      "id": "audit-1",
      "heuristic": "visibility|real-world-match|user-control|consistency|error-prevention|recognition|flexibility|aesthetic|error-recovery|help-docs|responsive|performance",
      "severity": "blocker|major|minor",
      "description": "...",
      "evidence": "<具体位置或截图描述>",
      "suggestion": "...",
      "effort": "quick-win|medium|major-rework"
    }
  ],
  "opportunities": [
    {
      "title": "...",
      "addresses_findings": ["audit-1", "audit-3"],
      "priority": "high|medium|low",
      "rationale": "..."
    }
  ],
  "summary": {
    "total_findings": 0,
    "by_severity": { "blocker": 0, "major": 0, "minor": 0 },
    "by_heuristic": { "visibility": 0, "...": 0 },
    "top_opportunities": ["..."]
  }
}
```

> ⚠️ **summary 字段自动 derive 规则（强制）**：`total_findings` = `findings.length`；`by_severity.*` = 对 `findings` 按 `severity` 分组计数；`by_heuristic.*` = 对 `findings` 按 `heuristic` 分组计数。**禁止手写估算**——必须在生成 JSON 时从 findings 数组 programmatic 计算得出。若发现 summary 与 findings 不一致，以 findings 数组为准重新计算。

**Step 2 — chat 输出紧凑 marker**（必做，⛔ **不要在 chat 内重复输出 Step 1 的完整 JSON**）：

```
<!-- spark-context:audit ref="spark-output/context/audit.json" -->
Audit 已保存：project=[project_name]，[N] 个 findings（blocker [n] / major [n] / minor [n]），聚类为 [M] 个改版机会点
<!-- /spark-context:audit -->
```

**降级 fallback**：若 Step 1 写盘失败（chat-only 平台），输出完整 JSON marker（无 ref 属性，marker 之间放裸 JSON）作为唯一持久化通道。

### Handoff 提示（必输出）

> **协议**：按 [`_shared/next-skill.md`](../../_shared/next-skill.md) 三层结构模板输出；前 5 候选由 `_shared/skill-graph.json` 的依赖图算法实时算（done ⊆ ready，按 next_hint.preferred → alternatives → 同阶段 → anchor → fan-out 排序），优先建议从 `_shared/skill-graph.json#skills[id="audit"].next_hint` 读取。

**首行模板**：`✅ 启发评估 已完成，Nielsen 十原则走查 findings 已沉淀。`

**本 Skill 的 `next_hint`**（来自 skill-graph.json，**不可在此 SKILL.md 内硬编码覆盖**）：

- **preferred**：`/brief`
- **优先理由**：走查 findings 已就位，进 Brief 锚定本次改版的策略与边界。
- **alternatives**：`/stories` (想直接把 finding 转成修复型故事)
- **emoji**：🔍

**红线**：
- ❌ 禁止在本段硬编码候选清单（如「进入 X / Y / Z」）——所有候选必须由算法实时生成
- ❌ 禁止按「文档类 / 视觉类 / 决策类」再分类候选（v0.5.5 起，分类已折叠进 next_hint.alternatives）
- ❌ 禁止与「更新链路面板」段合并——两段必须各自独立成段，中间空一行
- ❌ 禁止漏第 2 行候选清单——即使候选只有 1 个、或为空（终端节点）也要写出来

---

## 实操注意事项

### 自动模式（URL）的局限

- WebFetch 取不到需登录页面
- 单页应用（SPA）的二级页面可能取不到
- 无法测试交互态（hover / focus / loading）
- 建议自动模式 + 用户补充截图混用

### 与 Bench 的关系

如果上游有 Bench 上下文（竞品深度拆解），Audit 走查时可主动对照："竞品 [X] 在这个场景用了 [Y] 模式，本产品当前是 [Z]，是否考虑迁移？"——把这种对照标为 `opportunity` 而非 `finding`。

### 与 Check 的复用

Audit 的 12 维度有部分与 Check 的 10 类相似（visibility / error-prevention 等），但**判断对象不同**（已上线产品 vs 设计稿）。不要把 Check 的 finding 当 Audit 用，也不要反过来。

---

## 已知限制

- AI 走查带主观性，**建议关键发现配合 5-10 人真实用户测试验证**
- 自动模式只能扫静态层面，**无法测试用户实际行为路径**
- 不替代正式的可用性测试（用 Test Skill）
- 不替代完整无障碍审计（用 Access Skill）
- 与 Check 严格区分：设计稿走查请用 Check Skill

---

## 与兄弟 Skill / PM 套件的边界（v0.4.0 补充）

| 场景 | 用谁 | 不用谁 |
| --- | --- | --- |
| 改版项目：先诊断现有产品体验 | **Audit** | Frame（新项目无 PRD）/ Scope（拆 PRD） |
| 新产品方向探索 | Frame | Audit（Audit 必须有现成产品可走查） |
| 已有 PRD 要拆解 | Scope | Audit（Audit 不读 PRD 而是走查产品本身） |
| 完整 WCAG 合规审计 | Access | Audit（Audit 含可访问性一项，不替代完整 50+ 项 WCAG） |
| 主动用研找问题根因 | Probe | Audit（Audit 是专家走查 / 启发式，不做访谈） |
| 海量工单提炼高频痛点 | Signal | Audit（Audit 单人 / 小组走查，样本是产品本身不是工单） |

**Audit 不可替代性**：基于 Nielsen 10 + Krug + 自定义启发式，是「专家视角快速诊断现有体验」的最低成本工具——Probe（用研）/ Signal（工单）/ Bench（竞品）都需要外部数据，Audit 只需要现有产品本身。

## 质量标准

1. **Nielsen 10 原则全覆盖**：可见性 / 匹配现实 / 用户控制 / 一致性 / 防错 / 识别>回忆 / 灵活高效 / 美观简洁 / 错误恢复 / 帮助文档——10 项必须各 list 至少一次
2. **每个 finding 三件套**：问题描述 + 严重度（critical/major/minor/nit）+ 修复建议——缺一即不合格
3. **截图 / 定位明确**：每个 finding 必须可定位（页面路径 / 模块 / 截图 ref），不能只说「整体感觉不好」
4. **改版机会点反向输出**：findings 必须聚合为 ≥ 3 个改版方向，传递给下游 Brief
5. **可选读取 Probe/Signal/Bench**：如有这三个上游，必须显式引用其证据（不能只用专家直觉）
6. **优先级排序**：findings 按 severity × frequency 排序，前 10 条必须可落地为下次改版的待办

## 红线规则

1. **不替代用户测试**：Audit 是专家启发式，不是真实用户行为——重要决策必须配 Probe 或可用性测试（Test 未来）
2. **不替代完整 WCAG 审计**：Audit 含可访问性一项粗筛，完整 50+ 项合规请用 Access——法律合规场景不能只用 Audit
3. **不下整体评分**：不能给产品打「整体 7/10」这种总分——Audit 输出可执行 findings，不输出整体评级
