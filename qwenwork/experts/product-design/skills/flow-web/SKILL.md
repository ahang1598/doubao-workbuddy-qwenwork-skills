---
name: Web页面设计
name_en: "flow-web"
argument-hint: "输入要做的 Web 流程，如：用户从首页搜索商品到完成下单"
description: >
  触发（正向）——设计模式：用户要设计 Web 端多屏 flow、产品信息架构、用户流程，或以下任一场景：
  SaaS 管理后台（权限管理、成员管理、工作区、角色配置、Admin）、
  AI 产品（AI 对话、写作助手、Copilot、大模型、AI 工具）、
  营销官网（Landing Page、注册转化、免费试用、访客漏斗、onboarding）、
  数据分析（数据看板、BI、报表、仪表盘、图表钻取、维度筛选）、
  电商（购物车、结账流程、商品详情、下单、加购、订单追踪）、
  开发者工具（API Key、SDK、Playground、CLI、集成配置、Webhook）、
  内部运营（审批流、工单、报销、请假、差旅、内部流程、OA）、
  金融科技（转账、汇款、账户余额、交易记录、支付、对账、KYC）、
  社区社交（Feed、帖子、评论、点赞、私信、关注、社区广场）、
  医疗健康（预约就诊、健康档案、问诊、复诊、医患沟通）、
  教育科技（课程学习、测验、证书、练习、XP、学习路径）、
  娱乐流媒体（视频播放、音乐、Playlist、订阅、内容推荐）、
  设计工具（画布、设计稿、模板、导出、协作、版本管理）、
  房产平台（房源列表、地图看房、预约看房、楼盘详情）、
  招聘平台（职位列表、投递简历、申请状态追踪、JD 页面）、
  生产力 / 协作工具（轻量笔记、周报、团队复盘、async 协作、知识库、Notion/Coda 类轻量文档）。
  关键词：flow、多屏、IA、信息架构、屏幕流程、用户流程、注册流、管理后台、结账流程、看板、onboarding、复盘、周报、笔记。

  触发（正向）——审查模式：用户要对现有 Web UI 做质量审查、问题诊断或优化建议。
  关键词：检查交互、交互流程、用户链路、审查、review、帮我看看哪里不对、链路是否通畅、不够好看、优化 UX、UI 问题、UI 质量。

  排除（反向）：iOS/移动端设计（用 ios-spark-flow）、单页面组件（用 ui-design-brain）、视觉样式主题（用 theme-factory）、仅需单屏原型（用 interface-design）、静态海报/图片（用 canvas-design）。

description_en: >
  Web multi-screen flow and page design. Triggers when designing web product flows, information
  architecture, or user flows — covering all major web product categories: SaaS dashboards
  (permissions, team management, workspace, admin), AI products (chat UI, writing assistant,
  copilot, LLM tools), marketing sites (landing pages, registration funnels, onboarding),
  data analytics (dashboards, BI, reports, charts, drill-downs), e-commerce (cart, checkout,
  product detail, order tracking), developer tools (API key, SDK, playground, webhooks,
  integrations), internal operations (approval flows, tickets, expense, leave, OA), fintech
  (transfers, accounts, transactions, payments, KYC), community/social (feed, posts, comments,
  DMs, follows), healthcare (appointments, health records, consultations), edtech (courses,
  quizzes, certificates, learning paths), entertainment/streaming (video, music, playlists,
  subscriptions), design tools (canvas, templates, collaboration, versioning), real estate,
  recruiting, and productivity/collaboration tools (notes, weekly reports, async collaboration,
  knowledge bases).

  Also triggers in review mode for existing web UI quality review, UX issue diagnosis, or
  optimization suggestions. Keywords: flow, multi-screen, IA, user flow, registration flow,
  admin dashboard, checkout, onboarding, notes, knowledge base.

  Excludes: iOS/mobile design (use /flow-mobile), single-page components, visual style/theme,
  single-screen prototype, static posters/images.

allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
  - AskUserQuestion
chain:
  protocol_version: "1.0"
  reads: [brief, sitemap, stories, board]
  writes: flow-web
  schema:
    skill: string
    generated_at: string
    project_name: string
    project_type: string
    scenario: string
    component_library: string
    flows:
      - name: string
        screens: array<string>
        components_used: array<string>
        components_missing: array<string>
    output_files: array<string>
---

# WEB流程

> 你是 Web 多屏 Flow 设计专家。本 skill 通过 4 个步骤，从场景识别到多屏代码输出，生成符合行业认知的完整用户 flow 原型。组件库在 Step 3 确认后由用户选择，支持 shadcn/ui、Spark Design、Ant Design 三条路径。

---

**重要**：必须按 Step 0 → 1 → 2 → 3 → Q_tech → 4 的顺序执行，**每步之间等待用户确认**，不可跳步合并。

---

## Chain Context

### 上游读取（Step 0 执行，先于 Step 1）

按以下顺序尝试读取上下文：

1. 扫描会话中的 `<!-- spark-context:brief -->` / `<!-- spark-context:sitemap -->` / `<!-- spark-context:stories -->` marker
2. 读取项目目录 `spark-output/context/brief.json` / `sitemap.json` / `stories.json`
3. **向上查找**：若当前目录无 `spark-output/context/`，依次检查 `../` 和 `../../` 下的 `spark-output/context/`（覆盖 Phase A 创建新项目目录后 context 不在当前目录的场景）
4. 读取 `spark-output/context/_session-state.json`（Compaction 恢复通道）——若存在，从中获取 `workspace_path` 定位上游 context 目录，再按渠道 2 重试
5. 都没有则跳过，按无上下文流程执行（进入 Step 1）

可复用字段映射（找到 brief 时）：

- `brief.project_type` / `project_subtype` → 直接进入 Step 2 的场景识别（跳过 Step 1.1 的关键词扫描）
- `brief.business_goal` / `user` → 用作 Step 3 IA 设计的依据
- `brief.strategy_dimensions` → 影响 Step 4 组件选型与交互细节
- `brief.constraints` / `out_of_scope` → 限定生成范围
- `brief.style` → 视觉风格输入

读到上下文后告知用户："检测到 Brief 上下文（项目：[project_name]，类型：[project_type]/[project_subtype]），已沿用以上字段，跳过 Step 1.1 关键词扫描。如需修改请说明，否则我将直接进入 Step 2 场景确认。"

### 下游输出（Step 4 完成时执行）

按 [chain-protocol.md](../../chain-protocol.md) §2.1 v1.1 智能适配规则：

**Step 1 — 写盘到 `spark-output/context/flow-web.json`**（必做，主持久化通道；目录不存在先创建）。写入完整 JSON（schema 见本 SKILL.md frontmatter `chain.schema` 字段）。

**Step 2 — chat 输出紧凑 marker**（必做，⛔ **不要在 chat 内重复输出 Step 1 的完整 JSON**）：

```
<!-- spark-context:flow-web ref="spark-output/context/flow-web.json" -->
Flow Web 已保存：project=[project_name]，scenario=[scenario]，组件库=[component_library]，[N] 个 flows / [M] 个 .tsx 文件输出
<!-- /spark-context:flow-web -->
```

**降级 fallback**：若 Step 1 写盘失败（chat-only 平台），输出完整 JSON marker（无 ref 属性，marker 之间放裸 JSON）作为唯一持久化通道。

**Step 3 — 写入 session state（必做，Compaction 恢复通道）**：

每次写盘 `flow-web.json` 时，同步写入 `spark-output/context/_session-state.json`：

```json
{
  "current_skill": "flow-web",
  "workspace_path": "<当前 pwd 的绝对路径>",
  "original_workspace_path": "<Step 0 读取上游 context 时的原始目录（Phase A 创建新目录前的 pwd）>",
  "completed_skills": ["brief", "sitemap", "stories", "flow-web"],
  "current_phase": "Phase B / Phase C / 完成",
  "updated_at": "<ISO8601>"
}
```

> **作用**：Conversation Compaction 后会话 marker（渠道 1）被清除，AI 通过读取此文件恢复执行进度与 context 路径，避免"找不到 context"的死循环。该文件每次有 Skill 完成时由该 Skill 的下游输出步骤更新（追加 `completed_skills`、刷新 `current_skill` 和 `current_phase`）。

下游可消费 Skill：Check（走查时读取已生成 flow 列表）/ QA（验收时对照） / Edge（异常态补全）/ Pitch（汇报材料引用） / PRD（设计资产路径引用）。

### 字段流向下游

- `flow-web.flows[]` → **Edge** 的状态矩阵覆盖范围；**Check** 的走查目标；**QA** 的还原度核对范围；**Access** 的 WCAG 审计页面清单
- `flow-web.flows[].screens[].file_path` → **Check / QA / Access** 的逐文件走查锚点；**PRD** 的设计资产路径引用
- `flow-web.component_library` → **QA** 的"组件命名是否一致"核查；**Check** 的组件规范一致性走查；**Pitch** 的"我们押了什么组件库"决策素材
- `flow-web.scenario` → **Pitch** 的"为谁设计"输入；**PRD** 的 Solution & Feature Scope 锚点
- `flow-web.tech_stack` → **PRD** 的工程交付段；**QA** 的代码层走查；**Metric** 的埋点缺口分析基础

---

---

## 独立能力（无需连接器）

本 Skill 在完全离线、无任何连接器的场景下即可完整交付，所有方法论与输出形态不依赖外部系统：

- **IA + 导航 + 内容层级 + SparkDesign 组件规格**：四件套完整方法论
- **链式上下文双通道**：写入 `spark-output/context/flow-web.json` + 会话内 marker block，下游 Check / Edge / Chart / PRD / QA 可直接读取
- **多屏 Flow 代码生成**：基于 SparkDesign 组件库本地生成完整 React 代码（含 boilerplate）
- **白屏排查清单**：用户端 troubleshooting 全本地化文档
- **最小可运行项目模板**：boilerplate 内置，无需外部脚手架

> 红线：缺连接器时 **绝不 abort**，所有引导与输出路径必须照常完成。

## 增强能力（连接器加持）

接入以下连接器后，可减少手动粘贴、提高对齐效率。所有连接器均为可选，未装时按"降级路径"列的方式回落。

| 连接器 | 阶段 | 增强能力 | 降级路径 |
| --- | --- | --- | --- |
| **Figma** | Step 1 INTAKE / Step 3 ARCHITECT | 读取现有 Figma 页面 frame 作为视觉对照与 IA 输入，避免重复设计；ARCHITECT 阶段可对照 Figma 校验组件覆盖率 | 未装时让用户粘贴 Figma 链接或描述现有页面结构 |
| **GitHub** | Step 4 GENERATE 之后 | 生成的 SparkDesign 代码直接开 PR 到目标仓库，附 Skill 元数据 commit message 便于 review | 未装时输出代码到本地 `spark-output/flow-web/` 目录，用户手动 commit |

**接入触发**：用户首次调用 `/Web页面设计` 时，Skill 主动检测已认证的连接器并显示「已检测到：XXX，将自动启用增强模式」提示，用户可在该次会话中选择关闭。

**字段流向变化**：

- 启用 **Figma** → `chain.schema` 新增可选字段 `figma_refs: array<{flow_name, frame_url}>`
- 启用 **GitHub** → `chain.schema` 新增可选字段 `pr_url: string` + `commit_sha: string`，下游 Check / QA 可对照 PR diff 走查

> 所有新增字段都是 **可选**，未启用连接器时字段缺省，下游 Skill 必须能容忍缺省。

---

## Step 1: INTAKE — 意图识别 + 信息补全

> **规则**：先分析触发语，再按需提问。触发语已回答的维度，禁止重复问。

### 1.1 关键词识别（先分析，不提问）

读取用户的触发语，对照以下速查表提取：产品类型 / 用户角色 / Flow 动词。

| 场景 | 识别关键词 |
|---|---|
| UI 审查 | 检查、审查、review、帮我看看、哪里不对、不够好看、优化 UI、UI 问题 |
| SaaS Management | 管理后台、权限、成员、工作区、配置、Admin、角色 |
| AI Product | AI 对话、写作助手、AI 工具、Copilot、大模型 |
| Marketing Site | Landing Page、注册转化、访客、官网、免费试用 |
| Data Analytics | 数据看板、BI、图表、维度、报表、仪表盘、钻取 |
| E-commerce | 电商、购物车、结账、商品、下单、加购 |
| Developer Tools | API Key、SDK、开发者、Playground、CLI、集成 |
| Internal Ops | 审批、工单、报销、请假、差旅、内部流程 |
| Fintech | 转账、汇款、交易记录、账户余额、支付、对账 |
| Community & Social | 社区、帖子、Feed、评论、点赞、私信、关注 |
| Healthcare | 预约就诊、健康档案、医患、问诊、复诊 |
| EdTech | 课程、学习、测验、证书、练习、XP |
| Entertainment | 视频、音乐、播放、订阅、Playlist、流媒体 |
| Design Tools | 画布、设计稿、模板、导出、协作、版本 |
| Real Estate | 房源、地图看房、预约看房、中介、楼盘 |
| Job Platform | 职位、投递简历、申请状态、招聘、JD |
| Productivity Tool | 周报、复盘、retrospective、笔记、知识库、async 协作、团队空间、Notion-like、轻量文档 |

### 1.2 置信度路径（根据识别结果选一条）

**路径 A — 高置信（触发语明确匹配 1 个场景）**

直接用 `AskUserQuestion` 做场景确认（1 问）：

```json
{
  "questions": [{
    "question": "我识别到你的场景是「[场景名]」（[一句话描述]），是这样吗？",
    "header": "场景确认",
    "options": [
      { "label": "✅ 是的，继续", "description": "进入场景文件读取和 Flow 选择" },
      { "label": "❌ 不对，我来描述一下", "description": "重新输入产品描述" }
    ]
  }]
}
```

用户确认后 → 跳过 Q2，直接进入 Step 2。

---

**路径 B — 中置信（触发语匹配 2-3 个候选场景）**

用 `AskUserQuestion` 展示候选场景（1 问）：

```json
{
  "questions": [{
    "question": "你的场景更接近哪个？",
    "header": "场景选择",
    "options": [
      { "label": "[候选场景 A]", "description": "[一句话区分点]" },
      { "label": "[候选场景 B]", "description": "[一句话区分点]" },
      { "label": "[候选场景 C（如有）]", "description": "[一句话区分点]" }
    ]
  }]
}
```

用户选择后 → 跳过 Q2，直接进入 Step 2。

---

**路径 C — 低置信（触发语模糊，无法推断场景）**

用 `AskUserQuestion` 展示 4 大类（1 问）：

```json
{
  "questions": [{
    "question": "用一句话描述产品是什么、面向谁？",
    "header": "Product",
    "options": [
      { "label": "🏢 B2B 后台类", "description": "SaaS 管理后台 / 内部运营 / 数据分析 / 开发者工具" },
      { "label": "🛍️ 消费者产品", "description": "电商 / 娱乐流媒体 / 社区社交 / 教育科技" },
      { "label": "💼 垂直行业", "description": "金融科技 / 医疗健康 / 房产 / 招聘" },
      { "label": "🤖 其他", "description": "AI 产品 / 营销网站 / Landing Page" }
    ]
  }]
}
```

用户选完大类后 → **必须继续问 Q2**（大类不足以确定用户角色）。

### 1.3 Q2 — 用户角色（仅路径 C 触发）

```json
{
  "questions": [{
    "question": "核心用户角色是哪类？",
    "header": "User Role",
    "options": [
      { "label": "Admin / Operator", "description": "已登录管理者，有配置权限" },
      { "label": "End User", "description": "已登录终端用户，使用产品核心功能" },
      { "label": "Visitor / Prospect", "description": "未登录访客，处于注册/转化漏斗中" }
    ]
  }]
}
```

收到 Q2 回答后，进入 Step 2。

### 1.4 Review Mode 触发路径

**识别关键词**：检查、审查、review、帮我看看、哪里不对、不够好看、优化 UI、UI 问题

识别后**跳过 Step 2/3/4**，直接进入独立 Review Mode 执行路径：

```
Review Mode：
→ 用 AskUserQuestion 请用户提供需审查的代码或描述当前页面功能
→ 读取 references/ui-review.md
→ 按 P1 → P2 → P3 顺序扫描
→ 输出完整问题清单 + 对应 TECH_STACK 的修复代码片段（不只是文字描述）
```

**Review Mode 输出格式**：

```
## UI 审查报告

### P1 违反项（必须修复）
- [P1-X] [问题描述]
  修复：[对应 TECH_STACK 的代码片段]

### P2 违反项（建议修复）
- [P2-X] [问题描述]
  修复：[className 或结构]

### P3 建议清单
- [ ] [P3-X] ⬜ 未满足 / ✅ 已满足
```

---

## Step 2: CLASSIFY — 场景识别与文件映射

> 基于 Step 1 的回答，识别最匹配的 scenario，明确告知用户后读取对应文件。

### 决策矩阵

| 判断条件 | 匹配 Scenario | 读取文件 |
|---|---|---|
| Web + 已登录 + B2B + Admin/Operator + 管理用户/资源/权限/设置 | **SaaS Management** | `scenarios/web/saas-management.md` |
| Web + AI 对话是产品核心界面 + 任意用户角色 | **AI Product** | `scenarios/web/ai-product.md` |
| Web + 未登录访客 + 注册 / 免费试用 / 付费升级 / onboarding | **Marketing Site** | `scenarios/web/marketing-site.md` |
| Web + 已登录 + 数据分析师/业务管理者 + Dashboard/维度钻取/图表/报表导出 | **Data Analytics / BI** | `scenarios/web/data-analytics.md` |
| Web + 消费者 + 商品浏览/加购/购物车/电商结账 | **E-commerce** | `scenarios/web/ecommerce.md` |
| Web + 开发者/工程师 + API Key/SDK/CLI/代码集成/Playground | **Developer Tools** | `scenarios/web/developer-tools.md` |
| Web + 企业内部员工 + 审批流/工单/状态机/请假/报销/差旅管理 | **Internal Ops** | `scenarios/web/internal-ops.md` |
| Web + 已登录 + 转账/汇款/账户余额/交易记录/金融支付 | **Fintech** | `scenarios/web/fintech.md` |
| Web + 消费者 + 社交 Feed/发帖/评论/点赞/DM/关注互动 | **Community & Social** | `scenarios/web/community-social.md` |
| Web + 患者/医疗用户 + 预约就诊/健康档案/医患消息 | **Healthcare** | `scenarios/web/healthcare.md` |
| Web + 学生/学习者 + 课程/练习/测验/XP/证书 | **EdTech** | `scenarios/web/edtech.md` |
| Web + 消费者 + 视频/音乐内容消费/播放/订阅升级/Playlist | **Entertainment Web** | `scenarios/web/entertainment-web.md` |
| Web + 用户 + 画布编辑/设计创作/模板/导出/分享协作 | **Design Tools** | `scenarios/web/design-tools.md` |
| Web + 消费者 + 房源搜索/地图看房/预约看房/联系中介 | **Real Estate** | `scenarios/web/real-estate.md` |
| Web + 求职者 + 职位搜索/投递简历/申请状态追踪 | **Job Platform** | `scenarios/web/job-platform.md` |
| Web + 个人 / 5-20 人小团队 + 轻量内容创作 / async 协作 / 团队周报 / 知识沉淀 | **Productivity Tool** | `scenarios/web/productivity-tool.md` |

### 匹配逻辑

1. **明确匹配** → 直接告知匹配结果，读取文件
2. **部分匹配** → 列出候选，说明差异，让用户选择
3. **无匹配** → 告知当前覆盖的 16 类场景，推荐最接近的场景

### 读取文件

```
读取 scenarios/web/[matched-scenario].md
提取：IA Template / Canonical Flows / Spark Component Kit

读取 references/spark-token-config.md
提取：token 规范 + 禁止行为清单
```

### Q3 — Target Flow（多选，场景确认后动态生成）

> ⚠️ **强制要求**：调用 `AskUserQuestion` 时 `multiSelect` 字段必须设为 `true`，不得省略或设为 `false`。

基于 scenario 文件的 Canonical Flows 生成选项：

```json
{
  "questions": [{
    "question": "这次要设计哪些 flow？可多选。",
    "header": "Target Flow",
    "multiSelect": true,
    "options": [
      { "label": "[Flow 1 名称]", "description": "[Flow 1 一句话描述]" },
      { "label": "[Flow 2 名称]", "description": "[Flow 2 一句话描述]" },
      { "label": "[Flow 3 名称]", "description": "[Flow 3 一句话描述]" }
    ]
  }]
}
```

**多 Flow 执行规则**：一次性输出所有选中 flow 的 Step 3 IA 骨架，用户统一确认后进入 Q_tech，不逐 flow 打断。

**自定义 Flow（用户通过「Other」输入时）**：**必须**列出参照的具体 Canonical Flow 名称和与之的差异点（例：「参照 [注册 Flow]，差异：去掉邮箱验证步骤，增加手机号绑定」），以最近的 Canonical Flow 为骨架基础继续执行。Phase B 的 UI 元素映射声明表中再校验一次该差异点的实现方式。

---

## Step 3: ARCHITECT — IA 骨架设计

> 基于 Q3 选择的 flow，**一次性输出全部 IA 骨架**，然后统一等待用户确认。**输出后必须停下来等用户确认，不可直接跳到 Q_tech。**

### Sitemap 边界声明

- **已跑 Sitemap Skill**：检查工作目录是否存在 `sitemap.md`，若存在则读取页面层级与导航结构，Step 3 直接基于该产物输出骨架，**不重新提问**页面层级与导航模式。
- **未跑 Sitemap Skill**：Step 3 退化执行，自行推导页面层级与导航模式。

### 输出格式

为每个选中的 Flow 输出以下骨架（连续输出，不中断）：

```
## [Flow 名称] — IA 骨架

**场景参照**：[Scenario 名称]
**导航模式**：[Sidebar / Top Nav / Minimal，说明选择理由]
**页面层级**：[L1] → [L2] → [L3（如有）]
**数据密度**：[高 / 中 / 低]

**Flow：[Flow 名称]**
**屏幕数**：[N] 屏（[理由]）
**入口**：[什么操作触发这个 flow]

| 屏幕 | 名称 | 主操作 | 关键组件 | 跳转 |
|---|---|---|---|---|
| Screen 1 | [名称] | [核心 CTA] | [top 3 组件] | → Screen 2 |
| Screen N | [Exit Screen] | [确认/完成] | [组件] | → 退出 flow |

**三种终态**：
- ✅ Success：[用户看到什么，发生了什么]
- ❌ Error：[最常见错误场景及处理方式]
- ↩ Abandon：[用户中途退出时的策略]

**组件预告**：[top 5 组件及用途]
```

全部 flow 骨架输出完毕后，用 `AskUserQuestion` 统一确认：

```json
{
  "questions": [{
    "question": "以上 [N] 个 Flow 的 IA 骨架是否符合预期？",
    "header": "Confirm",
    "options": [
      { "label": "全部确认，进入组件库选择", "description": "所有骨架均符合预期，进入 Q_tech" },
      { "label": "需要调整某个 Flow", "description": "说明哪个 Flow 需要调整什么" },
      { "label": "需要调整屏幕数", "description": "增加或减少某个 flow 中的屏幕数量" },
      { "label": "需要调整 flow 边界", "description": "修改起点、终点或分支逻辑" }
    ]
  }]
}
```

- 全部确认 → 进入 **Q_tech**
- 需要调整 → 修改对应骨架后重新统一输出并请求确认

**架构决策**：从 scenario 文件的 `IA Template` 和 `Canonical Flows` 中提取规则，不得使用 scenario 文件中未记录的规则。

---

## Q_tech: 组件库选择

> **时机**：所有 flow 的 IA 骨架均已确认后，Step 4 开始之前。只问一次。

```json
{
  "questions": [{
    "question": "IA 骨架已全部确认。选择构建应用的组件库：",
    "header": "组件库",
    "options": [
      {
        "label": "Spark Design（Spark 团队推荐）",
        "description": "Spark Design — 设计系统原生组件，视觉语言统一，链式上下文深度集成。适合使用 SparkDesign 系统的团队设计师。"
      },
      {
        "label": "shadcn/ui（AI 原生 / 独立设计师）",
        "description": "shadcn/ui — 安装零风险，AI 完全熟悉，社区文档丰富，Tailwind CSS 3。适合独立设计师或无内部组件库时的兜底选择。"
      },
      {
        "label": "Ant Design（数据后台密集型）",
        "description": "Ant Design — 企业级组件库，Table / Form 功能强大，适合数据密集型后台场景。"
      }
    ]
  }]
}
```

用户选择后 → 记录为 `TECH_STACK`，进入 Step 4。后续所有代码均基于此选择，**中途不再切换**。

---

## Step 4: GENERATE — 完整应用生成

> 用户确认 Q_tech 后，分 4 个 Phase 生成完整可运行应用。

### 技术约束（根据 TECH_STACK 适用对应规则）

**shadcn/ui 路径**：
- ✅ 颜色使用 shadcn 语义类：`bg-background`、`text-foreground`、`bg-muted`、`bg-primary`、`text-primary-foreground`、`border-border`
- ✅ 组件 import 来自 `@/components/ui/[component]`
- ✅ 暗色模式：`document.documentElement.classList.toggle('dark', isDark)`
- ✅ Tooltip 必须有 `TooltipProvider` 包裹
- ❌ 禁止混用 Spark token 类（`bg-bg-base`、`text-text` 等）

**Spark Design 路径**：
- ✅ 颜色全部来自 Spark token：`bg-bg-base`、`text-text`、`bg-primary` 等
- ✅ 组件 import 来自 `sparkdesign` 包：`import { Button, Tag } from 'sparkdesign'`
- ✅ App Shell 必须用 `<ThemeStyleProvider>` 包裹，`theme="mint"`
- ✅ 间距使用 Tailwind scale，圆角用语义类
- ❌ 禁止：`bg-white`、`text-gray-500`、硬编码颜色值
- ❌ 禁止：shadcn 语义类（`bg-background`、`text-foreground` 等）

**Ant Design 路径**：
- ✅ 组件 import 来自 `antd`：`import { Button, Table, Form } from 'antd'`
- ✅ 主题通过 `ConfigProvider` 管理，暗色用 `theme.darkAlgorithm`
- ✅ 布局使用 `Layout`、`Sider`、`Content` 等 antd 布局组件
- ✅ 表单使用 antd `Form` + `Form.Item` 模式
- ❌ 禁止混用 shadcn 或 Spark 的 token 类

详细规范分别见：
- `references/shadcn-setup.md`
- `references/spark-token-config.md`
- `references/antd-setup.md`

### Phase 总览

```
Phase A（一次 response）：脚手架初始化 + 共享基础文件
         ↓ 用户发送「继续」
Phase B（每个 flow 一次 response）：逐个生成 flow 文件
         ↓ 每个 flow 后用户发送「继续」
Phase C（一次 response）：App Shell 集成 + 启动验证
         ↓ 自动继续
Phase D（一次 response）：DS Coverage Notes + Anti-Pattern 检查
```

**核心原则：Flow 文件必须先于 App Shell 生成。** App Shell 需要 import 所有 flow，必须在全部 flow 文件生成完毕（Phase B 结束）后才能生成（Phase C）。

---

### Phase A：项目基础（一次 response）

#### A.1 确认项目信息

**项目名**：用 `AskUserQuestion` 提供 2 个 option（工具自动附加 Other = 共 3 个选项）：

```json
{
  "questions": [
    {
      "question": "项目文件夹名称是什么？",
      "header": "项目名",
      "options": [
        { "label": "[根据场景推断的推荐名，如 sports-ticket-hub]", "description": "使用推荐名称" },
        { "label": "继续推荐更多名称", "description": "AI 再推荐 2 个备选" }
      ]
    }
  ]
}
```

- 用户选推荐名 → 直接使用，进入下一步
- 用户选「继续推荐更多名称」→ 再次调用 `AskUserQuestion`，提供 2 个新备选名 + 自动 Other
- 用户选 Other → 输入框，直接输入自定义名称

**项目状态**：用 `AskUserQuestion` 询问：

```json
{
  "questions": [
    {
      "question": "是否已有 Vite + React 项目？",
      "header": "项目状态",
      "options": [
        { "label": "全新项目", "description": "从零开始创建" },
        { "label": "已有项目", "description": "跳过创建，直接安装依赖" }
      ]
    }
  ]
}
```

#### A.2 用 `Bash` 执行安装（Claude 执行，用户无需操作）

根据 A.1 回答和 `TECH_STACK`，执行对应安装命令：

**shadcn/ui 路径**：
```bash
npm create vite@latest [project-name] -- --template react-ts
cd [project-name] && npm install
npx shadcn@latest init
npx shadcn@latest add button input form dialog sheet card table tabs badge select textarea checkbox switch avatar progress skeleton dropdown-menu alert-dialog popover tooltip toast separator scroll-area breadcrumb
npm install react-router-dom lucide-react
```

**Spark Design 路径**：
```bash
# 第一次 Bash 调用
npm create vite@latest [project-name] -- --template react

# 第二次 Bash 调用（全部链式，不得拆分，cd 之后所有命令必须在同一次调用中执行）
cd [project-name] && npm install && npm install sparkdesign && npm install tslib && npm install -D tailwindcss @tailwindcss/vite && npm install react-router-dom lucide-react

# 第三次 Bash 调用（验证 tslib 是否提升到顶层；npm v11+ deduplication 可能不提升 peer deps）
ls [project-name]/node_modules/tslib || (cd [project-name] && npm pack tslib && npm install ./tslib-*.tgz && rm -rf node_modules/.vite && echo "⚠️ tslib 未提升，已强制安装到顶层并清除 Vite 缓存")
```

**Ant Design 路径**：
```bash
npm create vite@latest [project-name] -- --template react-ts
cd [project-name]
npm install antd react-router-dom lucide-react
```

执行规则：每条命令等待完毕再执行下一条；若报错立即停止并告知用户，不继续后续步骤。

#### A.3 写入配置文件（用 `Write` 工具直接写入）

> ⚠️ **工具约束**：项目初始化后已存在的文件（如 `vite.config.js`）必须先用 `Read` 工具读取，再用 `Edit` 或 `Write` 写入，否则工具报错。

按 `TECH_STACK` 写入对应配置：

**shadcn/ui**：参考 `references/shadcn-setup.md` 第三节（vite.config.ts + @ alias）

**Spark Design**：参考 `references/spark-token-config.md` 第八节：
- `vite.config.js`：添加 `@tailwindcss/vite` 插件
- `src/index.css`：`@import "tailwindcss"` + `@import 'sparkdesign/theme.css'` + `@import 'sparkdesign/scale.css'` + `body { margin:0; }` — **禁止添加任何 `@theme` 块，否则循环引用导致颜色全部归零**
- `src/main.jsx`：**第一行**必须是 `import 'sparkdesign/style'`

**Ant Design**：无需特殊配置，antd v5 开箱即用。

#### A.4 读取参考文件

```
读取 references/flow-structure.md
提取：屏幕注释头格式、跳转注释格式、状态变体规则、DS Coverage Notes 格式

读取 references/component-concept-map.md
提取：当前 TECH_STACK 对应列的组件名（Phase B 代码生成时的组件映射依据）
```

#### A.5 生成共享文件

在 `src/flows/shared/` 下生成：
- **`types.ts`**：所有 flow 共用的数据类型、枚举、接口
- **`mock-data.ts`**：模拟数据，让 flow 在无后端时可交互

**项目目录结构**：

```
src/
├── App.tsx
└── flows/
    ├── shared/
    │   ├── types.ts          # Phase A 生成
    │   └── mock-data.ts      # Phase A 生成
    ├── flow-1/               # Phase B 生成
    │   └── flow1-[name].tsx
    ├── flow-2/               # Phase B 生成
    │   └── flow2-[name].tsx
    └── [feature-name]/       # Phase C 生成（App Shell）
        └── [feature-name].tsx
```

#### A.5.1 继承上游上下文（必做）

> **解决的问题**：Phase A 创建新项目目录并 `cd` 进去后，上游 `spark-output/context/*.json` 不在当前目录，导致下游 Skill（Check / QA / Retro）读不到 brief 等上下文，链路断裂。

**执行逻辑**：

1. 检查 Step 0 是否读取到了上游 context（brief / sitemap / stories 至少一个）
2. 若读取到，且当前已 `cd` 到新项目目录（即 `pwd` ≠ Step 0 读取 context 时的目录）：
   ```bash
   mkdir -p spark-output/context
   cp ../spark-output/context/*.json spark-output/context/ 2>/dev/null || true
   ```
3. 验证复制结果：`ls spark-output/context/` 确认文件已到位
4. 若 Step 0 未读取到任何 context，跳过本步

**红线**：
- ❌ 不要在复制后修改 JSON 内容——原样保留上游输出
- ❌ 不要只复制 `brief.json`——全量复制 `*.json`，确保下游任何 Skill 都能读到完整链路

#### A.6 环境验证（仅「全新项目」触发）

> **触发条件**：A.1 用户选择「全新项目」时执行；选择「已有项目」时跳过，直接输出 Phase A 结束语。

**Spark Design 路径**：用 `Write` 工具生成 `src/SetupCheck.tsx`（内容见 `references/spark-token-config.md` 第八节），然后临时修改 `src/App.tsx` 只渲染 `<SetupCheck />`，执行 `npm run dev`。

**shadcn / Ant Design 路径**：无需 SetupCheck，跳过本步骤。

**Phase A 结束语（全新项目 · Spark 路径）**：

```
✅ Phase A 完成：依赖已安装，配置文件已写入。
技术栈：Spark Design

⚠️ 环境验证：请在浏览器打开 http://localhost:5173，确认以下三项均正常：
  1. 页面背景为浅色（bg-bg-base token 正常）
  2. 按钮显示品牌色（Spark 组件样式正常）
  3. Tag 显示绿/红/橙色（颜色 token 正常）

全部正常后发送「继续」，开始生成第一个 flow 文件。
如有异常请截图或描述问题，先修复环境再继续。

⚠️ 注意：若中途退出，请手动删除 src/SetupCheck.tsx，并将 src/App.tsx 恢复为标准入口，避免残留文件影响后续生成。
```

**Phase A 结束语（全新项目 · 非 Spark 路径，或已有项目）**：

```
✅ Phase A 完成：依赖已安装，配置文件已写入。
技术栈：[TECH_STACK]
共 [N] 个 flow 待生成：[Flow 1]、[Flow 2]...

发送「继续」开始生成第一个 flow 文件。
```

---

### Phase B：逐 Flow 生成（每个 flow 一次 response）

**Phase B 入口清理（仅全新项目 · Spark 路径执行）**：

收到用户「继续」后，在生成第一个 flow 文件之前，先执行两个清理动作：
1. 用 `Bash` 删除 `src/SetupCheck.tsx`
2. 用 `Edit` 将 `src/App.tsx` 从只渲染 `<SetupCheck />` 恢复为标准入口（包裹 `BrowserRouter`，import `[ProductName]App`）

清理完成后，**不得立即输出 flow 代码**，必须先完成以下核验步骤。

**Phase B 强制前置核验（Spark 路径）**：

> ⚠️ **"我能写" ≠ "应该自己写"**。遇到任何 `<table>`、`<select>`、`<input>` 等 HTML 原生元素，必须先核验 Spark 是否有封装，有则用组件，无则在 DS Coverage Notes 记录为 Missing。

1. 列出本次所有 flow 将用到的 UI 模式（table / dialog / select / tabs / form / card 等）
2. 对每类「基础 HTML 可手写」的元素，执行 grep 确认 Spark 是否有对应封装：

```bash
grep -i "Table\|DataTable\|Select\|Combobox\|DatePicker\|Slider\|Toggle\|ToggleGroup\|Tabs\|Tag" node_modules/sparkdesign/dist/src/components/index.d.ts
```

3. **有封装 → 必须使用 Spark 组件，禁止手写裸 HTML**；未确认存在前不得生成对应代码
4. **无封装 → 参照 `references/spark-token-config.md` 的 token 规范手写，并在 Phase D DS Coverage Notes 中记录为 Missing**
5. **输出「UI 元素→组件映射声明表」**（强制，不可跳过）：

```
| UI 元素          | 使用的 Spark 组件              | 依据                        |
|-----------------|-------------------------------|-----------------------------|
| 状态筛选切换      | Tabs + TabsList + TabsTrigger | component-concept-map 第一节 |
| 数据表格          | Table + TableHeader + TableRow | grep 确认存在               |
| 下拉选择          | Select + SelectContent         | grep 确认存在               |
| 只读状态展示      | Tag（color="slate/success/..."）| 无 onClick，纯展示           |
| ...              | ...                            | ...                         |
```

**Spark Design 高频映射规约（已固化最佳实践，AI 不要凭 shadcn 直觉写）**：

| 场景 | ✅ 正确用法 | ❌ 易踩坑写法 |
| --- | --- | --- |
| AI 聊天界面 | `ChatInput` + `Response` + `UserMessage` + `RelatedPrompts` 组合 | 手写 `<textarea>` + 裸 HTML message div |
| 状态标签（在线/离线 / 成功/失败） | `<Tag color="success">` | `<Badge>` — Spark 没有 Badge 组件 |
| 二态开关（on / off） | `<Toggle>` | `<Switch>` 或手写 checkbox |
| 多步骤指示器 | `<Progress />` + 步骤数字 | 手写步骤圆圈 |
| 信息提示 / 错误态 | `<Alert variant="warning">` + Try again CTA | 手写带边框 div |
| 折叠面板 / FAQ | `<Accordion>` | 手写 useState(open) + 条件渲染 |
| 副标题 / 提示文字 | `<TypographyMuted>` | `<p className="text-gray-500">` |

**判断原则**：UI 模式 Spark 有组件先用组件，没有再 token 手写。**Spark 命名跟 shadcn 不完全一致**（Tag vs Badge / Toggle vs Switch），写 import 前先 grep 确认。

声明表输出后直接进入代码生成，无需等用户确认。

**循环规则（强制）**：
- 每次 response 只输出当前 flow 文件（`flow[N]-[name].tsx`）
- 文件包含该 flow 的全部屏幕代码
- 不提前生成其他 flow 或 App Shell
- 每个 flow 生成后等待用户发送「继续」

**代码输出协议**：严格遵循 `references/flow-structure.md` 中定义的：
- 每屏注释头格式（FLOW / SCREEN N of M / ENTRY / EXIT / BRANCH）
- 屏幕间跳转注释格式（`{/* → User clicks "X" → SCREEN N+1 */}`）
- 状态变体声明（STATE: default / filled / submitting / error）

**组件名映射（必须执行）**：Scenario 文件的 Component Kit 使用抽象功能概念命名（如「状态标签」「可折叠列表」）。生成代码前，必须对照 `references/component-concept-map.md` 查找当前 `TECH_STACK` 对应列的具体组件名和子组件链，不得凭记忆猜测。

**Phase B 每个 flow 结束语（必须输出）**：

```
# 还有剩余 flow 时：
✅ Flow [X]/[N]「[Flow 名称]」已生成（[屏幕数] 屏）。
剩余待生成：[剩余 flow 名称列表]
发送「继续」生成下一个 flow。

# 这是最后一个 flow 时：
✅ Flow [N]/[N]「[Flow 名称]」已生成，所有 flow 文件完成。
发送「继续」生成 App Shell，完成集成并启动预览。
```

---

### Phase C：App Shell 集成与验证（一次 response）

#### C.1 生成 App Shell

在 `src/flows/[feature-name]/[feature-name].tsx` 生成主入口。

**App Shell 必须包含**：

| 职责 | 说明 |
|---|---|
| **主题包裹** | Spark 路径：`ThemeStyleProvider`；shadcn 路径：useEffect 切换 class；antd 路径：`ConfigProvider` |
| **全局布局** | 基于 Step 3 确定的导航模式（Sidebar / Top Nav / Minimal） |
| **Flow 集成** | import 并组装所有 flow 组件（Phase B 全部完成后） |
| **路由/切换逻辑** | 未认证走注册路由，已认证走主路由 |
| **共享状态** | 认证状态、当前活动页、appearance 切换 |

同时更新 `src/App.tsx` 包裹 BrowserRouter。

#### C.2 验证

```bash
npm run dev
```

若有 TypeScript 报错，在输出 App Shell 代码时一并修复。

**Phase C 结束语（必须输出）**：

```
✅ Phase C 完成：App Shell 已生成，所有 [N] 个 flow 已集成。
可在 http://localhost:5173 查看完整应用。
```

---

### Phase D：收尾文档（一次 response）

#### D.1 DS Coverage Notes

格式见 `references/flow-structure.md` 第七节，输出：
- Components Used（组件 / 用途 / import 来源）
- Patterns to Formalize（值得沉淀为规范的交互模式）
- Missing Components（当前组件库缺失、需手写的部分）

#### D.2 Anti-Pattern 检查

参照 Step 2 已读取的 scenario 文件中的 `Anti-Patterns` 节，逐条检查。如有违反，附加说明并修正。

#### D.3 UI 质量检查

读取 `references/ui-review.md`，按以下顺序逐条检查：

1. **P1（全部 6 条）**：有违反 → 直接输出对应 TECH_STACK 的修复代码片段，不只是文字提示
2. **P2（全部 8 条）**：有违反 → 输出修复 className 或结构调整
3. **P3（全部 4 条）**：以 `[ ]` 清单形式列出，标注当前生成物是否满足（✅ 已满足 / ⬜ 未满足），供用户自行决定是否修复

#### D.4 启动自检（必跑，违反任一即视为生成失败）⭐

> ⚠️ **这是防白屏的最后一道关。** 跳过这一步 = 把"代码跑不起来"的责任推给用户。前面所有 phase 做对了，这一步漏掉一项就前功尽弃。

**生成完所有文件后，逐项 self-check**（AI 必须主动 read 每个相关文件验证，不能 assume）：

##### 4.1 Import / Export 自洽性核查（高频白屏源）

- [ ] 用 grep 扫所有 `*.ts` / `*.tsx` 中的 `import { X, Y } from '...'` 语句
- [ ] 对每个被 import 的符号，**实际打开源文件验证 export 存在**（包括拼写、大小写、type vs value）
- [ ] 特别核查：`types.ts` 中**实际 export 的所有 type / interface / enum**，逐个跟 `mock-data.ts` 和 `*.tsx` 屏幕组件中的 import 对照
- [ ] 如发现 mock-data.ts 或屏幕组件 import 了 types.ts 没 export 的符号 → **必须在 types.ts 补 export，或在 import 处改名**
- [ ] 所有相对路径 `../../../` 超过 3 层 → 改用 `@/` alias

##### 4.1.a `import type` 强制规则（最高频白屏致死源 ⛔）

> **TypeScript 类型文件的 export 在 esbuild / Vite 编译后会被完全擦除**。普通 `import { X }` 在运行时 ESM 加载会找不到该 export，直接抛 `does not provide an export named 'X'` 整个模块解析失败 → 白屏。

- [ ] **任何从 types.ts / *.types.ts / 纯类型文件 import interface / type / enum 的语句，必须用 `import type` 语法**：
  - ✅ 正确：`import type { Agent, Topic } from './types'`
  - ❌ 错误：`import { Agent, Topic } from './types'` ← 运行时白屏！
- [ ] 混合 import（同时有值和类型）拆成两行：
  ```typescript
  import type { Agent } from './types'    // 类型
  import { agentService } from './api'    // 值
  ```
- [ ] 或在单个 import 内用 `import { type X, valueY }` 内联 type 标记

**判断规则**：被 import 的符号在源文件是 `interface` / `type` / `enum` → 用 `import type`；是 `const` / `function` / `class` → 用普通 `import`。

##### 4.1.b 第三方库符号存在性核查（高频踩坑）

> AI 容易"凭命名习惯"写出不存在的 import——例如 `ClockOutlined` 听起来合理但 `@ant-design/icons` 实际只有 `ClockCircleOutlined`。

- [ ] **任何从第三方库（`antd` / `@ant-design/icons` / `react-router-dom` / `lucide-react` 等）import 的符号，必须实际存在于该库**
- [ ] 不确定时**先用 WebSearch 或读库文档核对**，再写 import；不要凭"听起来对"
- [ ] 高频易错 icon 名（来自 @ant-design/icons 真实命名）：
  - ✅ `ClockCircleOutlined`（不是 `ClockOutlined`）
  - ✅ `CheckCircleOutlined`（不是 `CheckOutlined` —— `CheckOutlined` 是另一个）
  - ✅ `LoadingOutlined`（不是 `LoaderOutlined`）
  - ✅ `MessageOutlined`（不是 `MsgOutlined`）
  - ✅ `EllipsisOutlined`（不是 `MoreOutlined` —— `MoreOutlined` 也存在但语义不同）
- [ ] **`lucide-react` 没有品牌 icon**（GitHub / Google / Twitter / Stripe 等）：
  - ❌ 错误：`import { GitHub, Google } from 'lucide-react'` —— lucide 是通用 UI icon 库，**不包含品牌 logo**
  - ✅ 处理：**用内联 SVG 替代**（从 simpleicons.org 拷贝 path，直接嵌进 JSX），或换用 `react-icons/si`（含品牌包）
  - 典型场景：OAuth 按钮（"Continue with GitHub"）—— 写一个 `<GitHubLogo />` 组件内联 SVG 即可
  - 校验方法：写品牌 icon 前先 grep `node_modules/lucide-react/dist/lucide-react.d.ts` 确认存在
- [ ] 高频易错 antd 组件 API：
  - **`Space` 的 props（antd v6 已改名）**：
    - ✅ 新 API：`<Space orientation="vertical" separator={<Divider />}>`
    - ❌ 旧 API（弃用 warning）：`<Space direction="vertical" split={<Divider />}>`
    - **2026 年起生成 antd 代码默认用新 API**，不要凭老知识写旧 prop
  - `Tag.CheckableTag` 而非 `CheckableTag`
  - **Typography 解构陷阱**（高频踩坑 ⚠️）：
    - 如果 JSX 里用 `<Text>`/`<Title>`/`<Paragraph>` 任意一个，**必须从 Typography 解构出全部用到的 sub-component**：
      ```typescript
      // ❌ 错误：只解构 Title 但 JSX 用了 Text → <Text> 被解析为全局 DOM Text，编译 error TS2786
      const { Title } = Typography
      return <><Title>X</Title><Text>Y</Text></>  // <Text> 报错！

      // ✅ 正确：用到几个解构几个
      const { Title, Text, Paragraph } = Typography
      ```
    - 或者用全限定名 `<Typography.Text>` 避免解构（推荐 mixed-use 时用）
  - **不要凭命名习惯 import antd 没有的 export**：
    - ❌ `import type { Notification } from 'antd/es'` — antd 没有此导出
    - 用 antd 内置类型前先核实存在；用第三方类型库（`@types/...`）或自定义

**典型白屏 case**：
- `mock-data.ts` 写 `import { Agent } from './types'`（types 里 Agent 是 interface） → 浏览器 `Uncaught SyntaxError: ... does not provide an export named 'Agent'`
- `screen.tsx` 写 `import { ClockOutlined } from '@ant-design/icons'` → 整个模块加载失败连锁阻断 App.tsx → 白屏

##### 4.2 项目基础设施完整性

- [ ] `package.json` 含必需依赖：`react` / `react-dom` / `react-router-dom`（如有路由）/ 选定组件库（`antd` / `@ant-design/icons` / 或 shadcn 相关）
- [ ] `vite.config.ts` 含 `resolve.alias: { '@': path.resolve(__dirname, './src') }`（如用 @ alias）
- [ ] `main.tsx` 含组件库样式 import：
  - Ant Design：`import 'antd/dist/reset.css'`
  - shadcn：`import './index.css'`（其中含 Tailwind 指令）
- [ ] `index.html` 含 `<div id="root">` mount 点
- [ ] `tsconfig.app.json` 含 `"paths": { "@/*": ["./src/*"] }` 配 alias

##### 4.3 App.tsx 路由与导航核查

- [ ] `App.tsx` 含 `BrowserRouter`（如多 flow 需路由切换）
- [ ] **必须含"屏幕选择器导航"**——让设计师能从首页点链接快速跳到每个 flow 的入口屏（不能只跑首页）
- [ ] 每个 flow 的入口屏在 `<Routes>` 中注册了 `<Route>`
- [ ] 路由 path 跟生成文件位置对应（如 `src/flows/flow1-create-space/screens/Welcome.tsx` 对应 path `/flow1`）

##### 4.4 mock-data 字段完整性

- [ ] `mock-data.ts` 中每个 mock 对象的字段，**完全匹配 types.ts 定义的类型**（不缺字段、不多字段）
- [ ] 如 types 定义 `interface Agent { id: string; name: string; status: 'online' | 'offline' }`，mock 不能只写 `{ name: 'X' }`（缺 id 和 status）
- [ ] enum / literal type 的值必须在允许范围（不能写 `status: 'busy'` 如果 type 只允许 'online' | 'offline'）

##### 4.5 屏幕组件首屏渲染核查

- [ ] 每个屏幕组件的 default export 是合法 React 组件
- [ ] 屏幕组件的 props（如有）有默认值或 mock 提供
- [ ] 没有 `useState(undefined)` 然后访问其 property（典型首屏 crash）

##### 4.5.a 脚手架残留清理（高频隐性 bug）

> Vite / CRA 等脚手架默认生成 `App.jsx` / `App.css` / `assets/` 等模板文件，**如果生成的项目用了 TypeScript（`App.tsx`）+ 自己的样式，残留的 `App.jsx` 会跟新的 `App.tsx` 产生模块解析冲突**——某些情况下 Vite 优先加载 `.jsx` 导致用户看到的不是你写的内容。

- [ ] **检查 `src/` 下是否有脚手架默认残留**：用 Bash 列 `src/` 目录，如有以下文件**必须删除**：
  - `src/App.jsx`（如果你写的是 `App.tsx`）
  - `src/App.css`（如果你不用，删了避免误引用）
  - `src/assets/react.svg`、`src/assets/vite.svg`（脚手架 logo，没用就删）
  - `src/index.css` 中的默认 CSS reset（如果你用了组件库自带 reset，删默认的避免冲突）
- [ ] **检查 `src/main.tsx` 是否还 import 了已删除的文件**：删完上面文件后必须更新 main.tsx 的 import
- [ ] **Phase A 已经验过一次 SetupCheck，Phase B 入口清理也已删 SetupCheck.tsx**——本步骤是兜底防 Vite 默认模板残留

**典型表现**：用户跑 `npm run dev` 看到的是 Vite 默认欢迎页（含 React + Vite logo），而不是你写的导航——多半是 App.jsx 残留导致。

##### 4.7 TypeScript strict 模式 hygiene（防 npm run build 失败）

> dev 模式（`npm run dev`）跑得起来不代表 `npm run build` 能过。strict 模式下未使用变量等都会变成 error，阻断 production build。**production-ready 交付前必须自检**。

- [ ] **未使用 import 全部删除**：grep 每个文件顶部 import，对照文件内实际使用，未引用的 import 一律删
- [ ] **未使用变量 / state / handler 全部删除**：用 `useState`、`const handler = ...` 等声明但从未读取的全删
- [ ] **故意未使用的 prop 加 `_` 前缀**：保留 prop 接口签名但当前组件不用 → 重命名为 `_propName`（TS 约定：下划线开头标记"故意未用"）
  ```typescript
  // ❌ 编译 error：'propName' is declared but never read
  function Component({ propName }: Props) { return <div /> }

  // ✅ 接受：下划线前缀告诉 TS / linter 这是故意的
  function Component({ propName: _propName }: Props) { return <div /> }
  ```
- [ ] **handler signature 中未用的参数也加 `_` 前缀**：`onClick={(_id, _e) => doSomething()}`
- [ ] **运行 `npm run build` 验证**（如平台支持）：必须**干净通过**——只允许 chunk size 这类 warning，不允许任何 TypeScript error

**典型 production build 阻断**（你这次踩过的）：
- `'Avatar' is declared but never read` — 删
- `'selectedTopicId' is declared but never read` — 删 state
- `Property 'Text' does not exist on type 'JSX.IntrinsicElements'` — Typography 解构补 Text（见 4.1.b）

##### 4.6 自检报告（输出到对话）

跑完 4.1-4.5 + 4.7 后，向用户报告：

```
✅ 启动自检通过：[N 项核查全过]
   - import / export 自洽：扫描 [M] 个文件，[K] 个 import 全部找到对应 export
   - import type 规则：[N] 个类型 import 已用 import type 语法
   - 第三方库符号：[N] 个 antd / icon import 名称已核实存在
   - 基础设施：package.json / vite.config.ts / main.tsx 配置完整
   - App.tsx 导航：含 BrowserRouter + 屏幕选择器
   - mock-data 字段：完全匹配 types
   - 首屏可渲染：N 个屏幕组件检查通过
   - 脚手架残留清理：Vite 默认 App.jsx / 默认 assets 已删
   - TS strict 模式 hygiene：无未使用 import / 变量；npm run build 干净通过

下一步：cd 项目目录 && npm install && npm run dev
预期：浏览器自动打开 http://localhost:5173 或 5174，看到导航栏 + 可点进每个 flow 屏。
production 部署：npm run build → 应干净通过无 TS error。

如启动后白屏 / 报错，参见 SKILL.md 末尾"白屏排查清单"。
```

如有任何一项失败：

```
❌ 启动自检失败：[列具体哪一项 + 具体文件路径 + 具体错误]
正在修复中...
[修复后重新跑 4.1-4.5 直到通过]
```

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

---

### Handoff 提示（必输出）

> **协议**：按 [`_shared/next-skill.md`](../../_shared/next-skill.md) 三层结构模板输出；前 5 候选由 `_shared/skill-graph.json` 的依赖图算法实时算（done ⊆ ready，按 next_hint.preferred → alternatives → 同阶段 → anchor → fan-out 排序），优先建议从 `_shared/skill-graph.json#skills[id="flow-web"].next_hint` 读取。

**首行模板**：`✅ Web页面设计 已完成，Web 页面 Flow + 代码 + 启动自检已完成。`

**本 Skill 的 `next_hint`**（来自 skill-graph.json，**不可在此 SKILL.md 内硬编码覆盖**）：

- **preferred**：`/check`
- **优先理由**：页面级设计完成立刻自检（路由可达性 / 死代码 / token 消费 / Brief 一致性），防止下游 QA 翻车。
- **alternatives**：`/edge` (先补全异常态覆盖) · `/flow-mobile` (继续做 Mobile 端对应 Flow) · `/chart` (页面含数据展示需补图表规格)
- **emoji**：🔍

**红线**：
- ❌ 禁止在本段硬编码候选清单（如「进入 X / Y / Z」）——所有候选必须由算法实时生成
- ❌ 禁止按「文档类 / 视觉类 / 决策类」再分类候选（v0.5.5 起，分类已折叠进 next_hint.alternatives）
- ❌ 禁止与「更新链路面板」段合并——两段必须各自独立成段，中间空一行
- ❌ 禁止漏第 2 行候选清单——即使候选只有 1 个、或为空（终端节点）也要写出来

---

### 快速检查清单

```
应用完整性
- [ ] npm run dev 正常启动（Phase C 执行）
- [ ] 所有 flow 文件在 Phase B 逐个生成完毕
- [ ] App Shell 在 Phase C 生成，import 路径全部有效
- [ ] types.ts 和 mock-data.ts 已生成
- [ ] 全局布局符合 Step 3 的导航模式

Flow 结构
- [ ] 屏幕数在 2–6 范围内
- [ ] 每屏有标准注释头（FLOW / SCREEN N of M / ENTRY / EXIT）
- [ ] 屏幕间有跳转注释
- [ ] 有 Happy Path + 至少 1 个 Error Branch
- [ ] 定义了三种 Exit State（Success / Error / Abandon）

代码质量（根据 TECH_STACK 选对应项检查）
shadcn 路径：
- [ ] 颜色使用 shadcn 语义类，无硬编码值
- [ ] 组件 import 来自 @/components/ui/
- [ ] Tooltip 有 TooltipProvider 包裹
Spark 路径：
- [ ] Phase B 前已执行 UI 元素 grep 核验，所有 Spark 有封装的元素均已使用组件
- [ ] Phase B 前已输出「UI 元素→组件映射声明表」，每个 UI 元素都有对应组件名和依据
- [ ] 无裸 HTML `<table>`/`<thead>`/`<th>`/`<tr>`/`<td>`，全部使用 Spark Table/DataTable 组件
- [ ] 视图切换 / 状态筛选 Pill 已使用 Tabs，无 Tag 带 onClick
- [ ] Tag 仅用于只读状态展示（无 onClick），交互型切换一律用 Tabs / ToggleGroup / Toggle
- [ ] 异步按钮使用 `loading={isLoading}` prop，未用 `disabled` + 文字切换
- [ ] Tag `color` 只用 16 种有效值，未使用 `"default"`；中性标签用 `"slate"`
- [ ] Tag 无 `size` prop，需要更小字号用 `className="text-xs"` 替代
- [ ] 颜色使用 Spark token，无硬编码值
- [ ] 组件 import 来自 'sparkdesign' 包
- [ ] App Shell 使用 ThemeStyleProvider（theme="mint"）包裹
- [ ] 未使用不存在的组件：Form（用 Field 系列）、Accordion（用 Collapse 系列）、Badge（用 Tag）
- [ ] 未使用废弃名称：OtpInput（改 InputOTP）、Sidebar（改 SidebarMenu）
- [ ] Toast 使用 <Toaster /> + toast() 函数，未直接渲染 <Toast>
- [ ] 复合组件已写完整子组件链（Select/Tabs/Dialog/Breadcrumb 等）
- [ ] AI 场景已使用 ChatInput/Response/UserMessage 系列，未手写气泡 div
- [ ] **容器背景未使用 `bg-fill-*` 系列**：Sidebar 用 `bg-bg-layout`，Card/Panel 用 `bg-bg-container`，hover 用 `bg-bg-elevated`；`bg-fill-secondary` 仅限表单控件填充，不可用于容器（见 spark-token-config.md 4.1）
- [ ] **容器 border 按层级选 token**：Card/Panel 边框用 `border-border-secondary`，表格行分割用 `border-border-tertiary`，重要分割线才用 `border-border`
Ant Design 路径：
- [ ] 组件 import 来自 'antd'
- [ ] 主题通过 ConfigProvider 管理
- [ ] 表单使用 Form + Form.Item 模式

输出完整性
- [ ] DS Coverage Notes 已输出
- [ ] Anti-Pattern 检查已执行
- [ ] UI 质量检查（P1/P2）已执行，违反项已附修复代码
- [ ] P3 清单已输出（每条标注 ✅/⬜）
```

---

## 附录：Scenario 文件索引

| 场景 | 文件 | 覆盖 Flow 类型 |
|---|---|---|
| SaaS 管理后台 | `scenarios/web/saas-management.md` | 邀请成员、修改权限、订阅升级、创建/管理资源 |
| AI 产品 | `scenarios/web/ai-product.md` | 发送消息+回复、上传文件提问、管理对话历史 |
| 营销网站 | `scenarios/web/marketing-site.md` | 访客注册、产品内付费升级、企业级注册+工作区配置 |
| 数据分析 / BI | `scenarios/web/data-analytics.md` | 查看仪表盘+时间切换、维度钻取、自定义报表导出 |
| 电商 | `scenarios/web/ecommerce.md` | 商品浏览+加购、完整结账、过滤和筛选商品 |
| 开发者工具 | `scenarios/web/developer-tools.md` | 注册+生成 API Key、Quickstart、Playground 调试 |
| 内部运营工具 | `scenarios/web/internal-ops.md` | 提交+处理审批、配置审批规则、邀请成员+分配权限 |
| 金融科技 | `scenarios/web/fintech.md` | 发起转账、过滤交易记录、导出对账单 |
| 社区 / 社交 | `scenarios/web/community-social.md` | 创建+发布帖子、浏览 Feed+互动、发送和管理私信 |
| 医疗健康 | `scenarios/web/healthcare.md` | 预约时段、查看健康档案+医患消息、取消/改期 |
| 教育科技 | `scenarios/web/edtech.md` | 完成课时+领取奖励、词汇自测、管理员颁发证书 |
| 娱乐 / 流媒体 | `scenarios/web/entertainment-web.md` | 内容发现+播放、订阅升级/Paywall、Playlist 管理 |
| 设计工具 | `scenarios/web/design-tools.md` | 从模板创建、编辑+导出、分享+邀请协作 |
| 房产平台 | `scenarios/web/real-estate.md` | 搜索+过滤房源、查看房源详情、预约看房/联系中介 |
| 招聘平台 | `scenarios/web/job-platform.md` | 搜索+过滤职位、查看+申请职位、申请状态追踪 |

---

## 附录：白屏排查清单（用户端 troubleshooting）

> Phase D.4 自检通过后仍可能因环境差异出现白屏。**生成完成后，把以下清单输出给用户作为兜底文档**。

### 排查步骤（按优先级）

#### 1. 打开浏览器 DevTools → Console 看红色 Error

最常见 4 种错误模式：

| 错误关键词 | 真实原因 | 修复 |
| --- | --- | --- |
| `does not provide an export named 'X'`（X 是 interface / type） | TS 类型在编译后被擦除，普通 import 找不到 | **改为 `import type { X } from '...'`**（Phase D.4.1.a） |
| `does not provide an export named 'X'`（X 是组件 / 函数 / 常量） | mock-data / 组件 import 了源文件没 export 的符号 | 让 AI 重跑 Phase D.4.1；或在源文件补 `export const X = ...` |
| `does not provide an export named 'XxxOutlined'`（icon） | 凭命名习惯写出不存在的 icon 名（如 `ClockOutlined`） | 查 @ant-design/icons 真实名（如 `ClockCircleOutlined`），Phase D.4.1.b |
| `Cannot find module '@/...'` | vite.config.ts 没配 alias | 在 vite.config.ts 加 `resolve.alias: { '@': path.resolve(__dirname, './src') }` |
| `Cannot read property 'X' of undefined` | mock-data 字段缺失 / 组件 props 没默认值 | 检查 mock-data.ts 是否完整匹配 types；给组件 props 加默认值 |
| `Unexpected token '<'` | Vite 没把 JSX 编译，main.tsx 用了 .ts 不是 .tsx | 重命名 main.ts → main.tsx，或 vite.config.ts 加 esbuild jsx 配置 |

#### 2. 看 Network 标签是否有 404

如有 .css / .js 加载失败：

- `antd/dist/reset.css` 404 → main.tsx 缺这一行 import，或 antd 没装（`npm install antd`）
- `/src/...` 404 → 文件路径拼错或文件没生成

#### 3. 页面有内容但样式乱

- Ant Design 路径：缺 `import 'antd/dist/reset.css'` 在 main.tsx
- shadcn 路径：缺 `import './index.css'` + Tailwind 没配
- Spark Design 路径：缺 token CSS import，参见 `references/spark-token-config.md`

#### 4. 页面完全空白且 Console 无错

- 检查 `index.html` 是否含 `<div id="root">`
- 检查 `main.tsx` 是否 `ReactDOM.createRoot(document.getElementById('root')!).render(<App />)`
- 检查 `App.tsx` 是否真的 return 了 JSX（不是 `return null` 或空 fragment）

#### 5. 终端启动有 warning 但不报错

- `port 5173 is in use, trying 5174 instead` → 正常，看新端口（如截图中的 5174）
- `[plugin:vite:react] Failed to load source map` → 不影响运行，忽略
- 一长串 TypeScript error → ts 类型问题，看具体哪个文件哪行

### 还是不行的 fallback 操作

直接发给 AI（QoderWork / Cursor）：

```
我的页面白屏。Console 报错：[贴 error 全文]
请按 SKILL.md Phase D.4 启动自检 6 项重新核查全部生成文件，
找出问题并修复。修复后告诉我哪些文件改了什么。
```

---

## 附录：最小可运行项目模板（boilerplate）

> Phase A 项目初始化时，**优先按以下模板生成基础设施**，避免缺关键配置。

### vite.config.ts（Ant Design / shadcn 通用）

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    open: true,
  },
})
```

### tsconfig.app.json 关键段

```json
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  }
}
```

### main.tsx（Ant Design 路径）

```typescript
import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import 'antd/dist/reset.css'
import App from './App'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>,
)
```

### App.tsx 模板（必须含屏幕选择器导航 + Routes）

```typescript
import { Routes, Route, Link } from 'react-router-dom'
import { Layout, Menu } from 'antd'
// import 每个 flow 的入口屏
import Flow1Entry from './flows/flow1-create-space/screens/Welcome'
import Flow2Entry from './flows/flow2-agent-discussion/screens/TopicList'
import Flow3Entry from './flows/flow3-control-decision/screens/Dashboard'

const { Header, Content } = Layout

export default function App() {
  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header>
        <Menu
          mode="horizontal"
          theme="dark"
          items={[
            { key: '1', label: <Link to="/flow1">创建空间</Link> },
            { key: '2', label: <Link to="/flow2">Agent 讨论</Link> },
            { key: '3', label: <Link to="/flow3">控制台</Link> },
          ]}
        />
      </Header>
      <Content style={{ padding: '24px' }}>
        <Routes>
          <Route path="/" element={<Flow1Entry />} />
          <Route path="/flow1" element={<Flow1Entry />} />
          <Route path="/flow2" element={<Flow2Entry />} />
          <Route path="/flow3" element={<Flow3Entry />} />
        </Routes>
      </Content>
    </Layout>
  )
}
```

### package.json 必需依赖（Ant Design 路径最小集）

```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.20.0",
    "antd": "^5.12.0",
    "@ant-design/icons": "^5.2.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "@vitejs/plugin-react": "^4.2.0",
    "typescript": "^5.3.0",
    "vite": "^5.0.0"
  }
}
```

shadcn / Spark Design 路径的 boilerplate 见 `references/shadcn-setup.md` / `references/spark-token-config.md`。

---

## 与兄弟 Skill 的边界（v0.4.0 补充）

| 场景 | 用谁 | 不用谁 |
| --- | --- | --- |
| Web 端（桌面 / 平板）多屏 Flow + SparkDesign 代码 | **Flow Web** | Flow Mobile（Mobile 端专属交互） |
| Mobile 端 Flow | Flow Mobile | Flow Web（手势 / 底部导航 / 软键盘不同） |
| 异常态专项穷举 | Edge | Flow Web（Flow 走主流程） |
| IA 结构 / 站点地图 | Sitemap | Flow Web（Flow Web 是 sitemap 下游具象化） |
| Landing 落地页 / Campaign 营销页 | Landing / Campaign（未来） | Flow Web（Flow 是产品页面 IA + 任务流） |
| 设计走查 / 验收 | Check / QA | Flow Web（Flow Web 是产出，不是 review） |

**Flow Web 不可替代性**：Web 端多屏 IA + SparkDesign 组件映射 + 实际 .tsx 代码生成，是「设计师在 IDE / Cursor / Vibe Coding 场景下直接产出可运行代码」的核心 AI 执行型 Skill——三件叠加在 product-design 内独此一份。

## 质量标准

1. **多屏完整**：单 Flow ≥ 3 屏，每屏含状态（默认 / 输入 / 空 / 错误 / 加载），关键屏交互注释完整
2. **SparkDesign 组件映射准确**：所有 UI 元素必须映射到 SparkDesign 真实组件（参考 Phase B 高频映射规约：Tag 不是 Badge / Toggle 不是 Switch / Chat 系列组合等）
3. **响应式断点显式**：≥ 3 个断点（mobile/tablet/desktop），每个断点的栅格 / 间距 / 组件密度变化必须标
4. **D.4 输出可运行 .tsx**：脚手架清理（无 App.jsx 残留）+ lucide-react 无品牌 icon 用内联 SVG fallback，代码必须直接 `npm run dev` 跑起来
5. **导航 IA 与 sitemap 对齐**：主导航 / 二级导航 / 面包屑必须与 sitemap.json 一致，不能 Flow 内自创导航结构
6. **键盘可达 + Focus 可见**：所有交互元素 tabindex 正确，focus 样式必须显式（不能依赖浏览器默认）

## 红线规则

1. **不照搬 Mobile 模式**：底部 tab / 拉刷 / 沉浸式头部不是 Web 模式——出现这些视为 Mobile 模式误用
2. **不用非 SparkDesign 组件**：项目内必须用 SparkDesign，引入第三方 UI 库（MUI / Antd / shadcn 直装）= 红线，破坏设计系统一致性
3. **不省略 Edge 异常态钩子**：每个数据屏必须留「空态 / 错误态 / 加载态」三个 slot，全部细节去 Edge 穷举但 slot 必须留
