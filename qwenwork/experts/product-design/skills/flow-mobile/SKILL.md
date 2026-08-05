---
name: mobile页面设计
name_en: "flow-mobile"
argument-hint: "输入要做的移动端流程，如：抖音视频拍摄到发布的完整路径"
description: >
  触发（正向）：用户要设计移动端（H5 / React Native App）的多屏 flow、信息架构、TabBar 导航骨架、权限引导流程、移动端购物/支付流程、移动播放器/Paywall、行程规划、健康追踪、AI 助手、社交动态/DM，或任何移动端多屏交互设计。关键词：移动端、H5、App、React Native、TabBar、Flow、多屏、IA、App 架构、手机、iPhone、Android、跨平台。

  审查模式（Review Mode）触发词：检查交互、审查、review、帮我看看、哪里不对、优化 UI、链路不顺。

  排除（反向）：Web/浏览器桌面产品（用 /Web页面设计）、iOS 原生 SwiftUI（用 ios-spark-flow）、单页面移动端组件（用 ui-design-brain）、仅需配色/字体（用 theme-factory）。

description_en: >
  Mobile multi-screen flow and page design (H5 / React Native App). Triggers when designing mobile
  flows, information architecture, TabBar navigation skeletons, permission prompts, mobile
  shopping/payment flows, mobile players/Paywalls, itinerary planning, health tracking, AI
  assistants, social feeds/DMs, or any mobile multi-screen interaction design.

  Keywords: mobile, H5, App, React Native, TabBar, Flow, multi-screen, IA, App architecture,
  iPhone, Android, cross-platform.

  Also triggers in review mode: check interactions, review, help me find issues, UI issues,
  optimize UI, flow feels broken.

  Excludes: web/desktop products (use /flow-web), native iOS SwiftUI, single mobile
  screen components, color/typography only.

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
  writes: flow-mobile
  schema:
    skill: string
    generated_at: string
    project_name: string
    project_type: string
    scenario: string
    tech_stack: string
    flows:
      - name: string
        screens: array<string>
        components_used: array<string>
        components_missing: array<string>
    output_files: array<string>
---

# mobile页面设计

> 你是移动端多屏 Flow 设计专家。本 skill 通过 4 个步骤，从场景识别到多屏代码输出，生成符合行业认知的完整移动端用户 flow 原型。支持两条技术路径：**H5（Ant Design Mobile）** 和 **React Native（Expo + NativeWind + Gluestack UI v2）**。

**重要**：必须按 Step 0 → 1 → 2 → 3 → Q_tech → 4 的顺序执行，**每步之间等待用户确认**，不可跳步合并。

---

## Chain Context

### 上游读取（Step 0 执行，先于 Step 1）

按以下顺序尝试读取上下文：

1. 扫描会话中的 `<!-- spark-context:brief -->` / `<!-- spark-context:sitemap -->` / `<!-- spark-context:stories -->` marker
2. 读取项目目录 `spark-output/context/brief.json` / `sitemap.json` / `stories.json`
3. 都没有则跳过，按无上下文流程执行（进入 Step 1）

可复用字段映射（找到 brief 时）：

- `brief.project_type` / `project_subtype` → 直接进入 Step 2 的场景识别（跳过 Step 1.1 关键词扫描）
- `brief.business_goal` / `user` → 用作 Step 3 IA 骨架设计依据
- `brief.strategy_dimensions` → 影响交互模式与 TabBar 架构
- `brief.constraints` / `out_of_scope` → 限定生成范围

读到上下文后告知用户："检测到 Brief 上下文（项目：[project_name]，类型：[project_type]/[project_subtype]），已沿用以上字段。如需修改请说明，否则我将直接进入 Step 2 场景确认。"

**注意**：Review Mode 触发词优先于 Chain Context 检测——若用户输入含审查关键词，依然先进入 Step 1.0 Review Mode。

### 下游输出（Step 4 完成时执行）

完成所有 flow 生成后，**同时**做两件事：

按 [chain-protocol.md](../../chain-protocol.md) §2.1 v1.1 智能适配规则：

**Step 1 — 写盘到 `spark-output/context/flow-mobile.json`**（必做，主持久化通道；目录不存在先创建）。写入完整 JSON（schema 见本 SKILL.md frontmatter `chain.schema` 字段）。

**Step 2 — chat 输出紧凑 marker**（必做，⛔ **不要在 chat 内重复输出 Step 1 的完整 JSON**）：

```
<!-- spark-context:flow-mobile ref="spark-output/context/flow-mobile.json" -->
Flow Mobile 已保存：project=[project_name]，scenario=[scenario]，tech_stack=[H5/RN]，[N] 个 flows / [M] 个输出文件
<!-- /spark-context:flow-mobile -->
```

**降级 fallback**：若 Step 1 写盘失败（chat-only 平台），输出完整 JSON marker（无 ref 属性，marker 之间放裸 JSON）作为唯一持久化通道。

下游可消费 Skill：Check / QA / Pitch。

### 字段流向下游

- `flow-mobile.flows[]` → **Edge** 的状态矩阵覆盖范围；**Check** 的走查目标；**QA** 的还原度核对范围；**Access** 的 WCAG 审计页面清单
- `flow-mobile.flows[].screens[].file_path` → **Check / QA / Access** 的逐文件走查锚点；**PRD** 的设计资产路径引用
- `flow-mobile.tech_stack` → **PRD** 的工程交付段（H5 vs RN 决策）；**QA** 的代码层走查；**Metric** 的埋点缺口分析基础
- `flow-mobile.scenario` → **Pitch** 的"为谁设计"输入；**PRD** 的 Solution & Feature Scope 锚点

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

## 独立能力（无需连接器）

本 Skill 在完全离线、无任何连接器的场景下即可完整交付，所有方法论与输出形态不依赖外部系统：

- **IA + Mobile 端交互模式 + 组件映射**：完整方法论内置
- **链式上下文双通道**：写入 `spark-output/context/flow-mobile.json` + 会话内 marker block，下游 Check / Edge / Chart / PRD / QA 可直接读取
- **多屏 Flow 代码生成**：基于 SparkDesign Mobile 组件本地生成 React Native / 移动 Web 代码
- **Mobile Scenario 文件索引**：内置常见场景模板，无需外部资源

> 红线：缺连接器时 **绝不 abort**，所有引导与输出路径必须照常完成。

## 增强能力（连接器加持）

接入以下连接器后，可减少手动粘贴、提高对齐效率。所有连接器均为可选，未装时按"降级路径"列的方式回落。

| 连接器 | 阶段 | 增强能力 | 降级路径 |
| --- | --- | --- | --- |
| **Figma** | Step 1 INTAKE / Step 3 ARCHITECT | 读取现有 Figma Mobile frame 作为视觉对照与 IA 输入；ARCHITECT 阶段对照校验 Mobile 组件覆盖率 | 未装时让用户粘贴 Figma 链接或描述页面结构 |
| **GitHub** | Step 4 GENERATE 之后 | 生成的 SparkDesign Mobile 代码直接开 PR 到目标仓库 | 未装时输出代码到本地 `spark-output/flow-mobile/` 目录，用户手动 commit |

**接入触发**：用户首次调用 `/mobile页面设计` 时，Skill 主动检测已认证的连接器并显示「已检测到：XXX，将自动启用增强模式」提示，用户可在该次会话中选择关闭。

**字段流向变化**：

- 启用 **Figma** → `chain.schema` 新增可选字段 `figma_refs: array<{flow_name, frame_url}>`
- 启用 **GitHub** → `chain.schema` 新增可选字段 `pr_url: string` + `commit_sha: string`

> 所有新增字段都是 **可选**，未启用连接器时字段缺省，下游 Skill 必须能容忍缺省。

---

## Step 1: INTAKE — 意图识别 + 信息补全

### 1.0 Review Mode 前置检测（优先于其他分支）

读取触发语，若包含以下任意关键词：`检查交互` / `审查` / `review` / `帮我看看` / `哪里不对` / `优化 UI` / `链路不顺`

→ **立即跳过 Step 2–4，进入 Review Mode**：

用 `AskUserQuestion` 请用户提供审查目标：

```json
{
  "questions": [{
    "question": "请提供需要审查的代码文件路径，或描述当前页面的功能和遇到的问题。",
    "header": "审查目标",
    "options": [
      { "label": "粘贴 / 指定代码路径", "description": "我会读取并按 P1/P2/P3 逐项扫描" },
      { "label": "描述页面功能和问题", "description": "根据描述判断潜在的 UI 问题" }
    ]
  }]
}
```

收到后：读取 `references/mobile-ui-review.md`，按 P1 → P2 → P3 顺序扫描，输出审查报告。

---

### 1.1 关键词识别（未触发 Review Mode 时执行）

读取用户触发语，对照以下速查表提取：产品类型 / 用户角色 / Flow 动词。

| 场景 | 识别关键词 |
|---|---|
| Consumer Social | 社交、发帖、动态、DM、私信、关注、点赞、评论、TikTok 类、Instagram 类 |
| Health & Fitness | 健康、运动、锻炼、卡路里、步数、睡眠、心率、训练计划 |
| AI Assistant | AI 对话、聊天机器人、语音输入、AI 助手、ChatGPT 类 |
| Consumer Finance | 转账、汇款、账户余额、交易记录、支付、数字钱包 |
| Marketplace | 电商、购物车、结账、商品、下单 |
| Food Delivery | 外卖、餐厅、菜单、配送、点餐、本地生活、Uber Eats 类、美团类 |
| Entertainment | 视频、音乐、播客、内容消费、播放、订阅、Paywall |
| Travel | 航班、酒店、行程、预订、登机、旅游 |
| EdTech | 课程、学习、测验、证书、练习、打卡、连击 |
| Job Platform | 职位、投递简历、申请状态、招聘 |
| Reading & Media | 新闻、文章阅读、订阅解锁、Feed 个性化 |
| Design & Media Editing | 图片编辑、模板、滤镜、AI 生成图像、设计创作 |
| Messaging | 私信、群聊、聊天、消息、IM、WhatsApp 类、Telegram 类 |
| Productivity | 任务管理、To-Do、待办、习惯打卡、日视图、时间规划、Todoist 类 |
| Dating | 约会、交友、滑卡、配对、Tinder 类、Bumble 类 |
| Camera & Photo | 相机、拍照、修图、滤镜调色、照片编辑、VSCO 类、Lightroom 类 |

### 1.2 置信度路径

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

用户确认后 → 直接进入 Step 2。

**路径 B — 中置信（触发语匹配 2–3 个候选场景）**

```json
{
  "questions": [{
    "question": "你的场景更接近哪个？",
    "header": "场景选择",
    "options": [
      { "label": "[候选场景 A]", "description": "[一句话区分点]" },
      { "label": "[候选场景 B]", "description": "[一句话区分点]" }
    ]
  }]
}
```

**路径 C — 低置信（触发语模糊）**

```json
{
  "questions": [{
    "question": "用一句话描述这个移动端产品是什么、面向谁？",
    "header": "Product",
    "options": [
      { "label": "🛍️ 消费者产品", "description": "电商 / 娱乐流媒体 / 社区社交 / 教育科技" },
      { "label": "💰 金融 & 生活服务", "description": "数字钱包 / 出行旅游 / 健康运动 / 本地外卖" },
      { "label": "🤖 AI & 内容工具", "description": "AI 助手 / 新闻阅读 / 设计编辑工具" },
      { "label": "💼 求职 & 其他", "description": "招聘平台 / 其他移动端场景" }
    ]
  }]
}
```

路径 C 选完大类后 → 必须继续问 Q2。

### 1.3 Q2 — 目标 Flow 类型（仅路径 C 触发）

```json
{
  "questions": [{
    "question": "这次要设计哪个具体 flow？",
    "header": "目标 Flow",
    "options": [
      { "label": "核心功能 flow", "description": "产品的主要用户任务（发帖/下单/转账/学习）" },
      { "label": "Onboarding flow", "description": "新用户注册 / 引导 / 权限请求" },
      { "label": "支付 / 订阅 flow", "description": "购买 / 升级 / Paywall" },
      { "label": "个人资料 / 设置 flow", "description": "资料编辑 / 账户设置" }
    ]
  }]
}
```

收到 Q2 回答后，进入 Step 2。

---

## Step 2: CLASSIFY — 场景识别与文件映射

### 决策矩阵

| 判断条件 | 匹配 Scenario | 读取文件 |
|---|---|---|
| 社交动态/发帖/评论/DM/互关 | Consumer Social | `scenarios/mobile/consumer-social.md` |
| 健康/运动/锻炼/卡路里/步数 | Health & Fitness | `scenarios/mobile/health-fitness.md` |
| AI 对话是核心界面（语音/文字） | AI Assistant | `scenarios/mobile/ai-assistant.md` |
| 账户余额/转账/汇款/支付/交易记录 | Consumer Finance | `scenarios/mobile/consumer-finance.md` |
| 商品浏览/购物车/结账（非外卖） | Marketplace | `scenarios/mobile/marketplace.md` |
| 餐厅/菜单/外卖配送/点餐 | Food Delivery | `scenarios/mobile/food-delivery.md` |
| 视频/音乐/播客/内容消费 + Paywall | Entertainment | `scenarios/mobile/entertainment.md` |
| 航班/火车/酒店/行程规划 | Travel | `scenarios/mobile/travel.md` |
| 课程/测验/XP/连击/订阅学习计划 | EdTech | `scenarios/mobile/edtech.md` |
| 职位搜索/投递简历/申请状态追踪 | Job Platform | `scenarios/mobile/job-platform.md` |
| 新闻/杂志/文章阅读/订阅解锁 | Reading & Media | `scenarios/mobile/reading-media.md` |
| 矢量模板设计/AI 生成图像/多媒体编辑 | Design & Media Editing | `scenarios/mobile/design-tools.md` |
| 1:1 私信/群聊/IM 消息是核心功能 | Messaging | `scenarios/mobile/messaging.md` |
| 任务管理/To-Do/习惯打卡/时间规划 | Productivity | `scenarios/mobile/productivity.md` |
| 滑卡发现/匹配/约会交友 | Dating | `scenarios/mobile/dating.md` |
| 拍照相机/照片滤镜调色/修图导出 | Camera & Photo | `scenarios/mobile/camera-photo.md` |

常见歧义：AI 语言练习 → AI Assistant vs EdTech；外卖 → Food Delivery vs Marketplace；IM 消息 → Messaging vs Consumer Social（DM 是其中一 Tab）

无匹配时 → 告知 16 类覆盖，推荐最接近场景。

### Q3 — 多选 Flow 选择

读取 scenario 文件后，从 Canonical Flows 动态生成选项：

```json
{
  "questions": [{
    "question": "这次要设计哪些 flow？（可多选，将按选择顺序依次生成）",
    "header": "Flow 选择",
    "multiSelect": true,
    "options": [
      { "label": "[Flow 1 名称]", "description": "[一句话描述该 flow 的主要用户任务]" },
      { "label": "[Flow 2 名称]", "description": "[一句话描述该 flow 的主要用户任务]" }
    ]
  }]
}
```

**Q3 "Other" fallback 强化规则**：用户选择"Other"或自定义 flow 时，必须在下一条消息中明确声明：
1. 最相似的 Canonical Flow 名称（必须是 scenario 文件中存在的 flow）
2. 与该 Canonical Flow 的关键差异点（至少 2 条）

Phase B 的组件映射声明表中须同步注明此 flow 的参照来源与差异点，不得遗漏。

---

## Step 3: ARCHITECT — 移动端 IA 骨架设计（批量模式）

> 一次性生成所有选中 flow 的 IA 骨架，再统一确认。

**输出所有 flow 的 IA 骨架**（按 Q3 选择顺序），每个 flow 格式如下：

```
## [Flow 名称] — 移动端 IA 骨架

**场景参照**：[Scenario 名称]，基于 [N] 个真实移动产品横向研究
**导航模式**：TabBar（[N] Tab）/ Stack，说明选择理由
**页面层级**：[L1 Tab 根页] → [L2 列表/详情] → [L3 操作面板 / 全屏]
**数据密度**：[高 / 中 / 低]

**Flow：[Flow 名称]**
**屏幕数**：[N] 屏（[理由]）
**入口**：[什么操作触发这个 flow]

| 屏幕 | 名称 | 主操作 | 关键组件 | 跳转方式 |
|---|---|---|---|---|
| Screen 1 | [名称] | [核心 CTA] | [top 3 组件] | Stack push → Screen 2 |
| Screen N | [Exit Screen] | [确认/完成] | [组件] | 返回根页 |

**三种终态**：
- ✅ Success：[描述]
- ❌ Error：[描述]
- ↩ Abandon：[描述]
```

所有 flow 骨架输出完毕后，发起**单次统一确认**：

```json
{
  "questions": [{
    "question": "以上 [N] 个 flow 的移动端 IA 骨架是否符合预期？",
    "header": "批量确认",
    "options": [
      { "label": "全部确认，进入技术路径选择", "description": "所有骨架符合预期" },
      { "label": "需要调整（请在 Other 中说明是哪个 flow 及问题）", "description": "描述需要修改的 flow 名称 + 具体调整点" }
    ]
  }]
}
```

- 全部确认 → 进入 Q_tech
- 需要调整 → 修改对应 flow 骨架后重新发起统一确认

> 架构决策规则：从 scenario 文件的 `IA Template` 和 `Canonical Flows` 节提取，不得使用未在文件中记录的规则。

---

## Q_tech — 技术路径选择

> 所有 flow IA 骨架确认后，Step 4 开始前。只问一次。

```json
{
  "questions": [{
    "question": "这个 flow 准备运行在哪个平台？",
    "header": "技术路径",
    "options": [
      {
        "label": "H5 / 移动 Web",
        "description": "React + Ant Design Mobile（antd-mobile v5）。运行在手机浏览器或 WebView，无需安装，适合微信内嵌或移动官网。"
      },
      {
        "label": "React Native App",
        "description": "Expo + NativeWind v4 + Gluestack UI v2。真正的跨平台 App（iOS + Android），支持 Expo Go 扫码预览。"
      }
    ]
  }]
}
```

收到选择后，读取 `references/mobile-component-map.md`，提取对应路径的组件规范，进入 Step 4。

---

## Step 4: GENERATE — 多屏 Flow 代码生成

### Phase A — 项目初始化

→ **读取 `references/mobile-phase-a.md`** 执行完整项目初始化流程（A.1 询问项目名 → A.2 安装依赖 → A.3 共享文件 → A.4 RN 环境验证）。

### Phase B — 逐 flow 循环生成

按 Q3 选择顺序，每次 response 只生成当前 flow 文件（`flow[N]-[name].tsx`），生成后等待用户「继续」。

**B.1 强制读取**：
- `references/flow-structure.md` — 屏幕注释头格式、跳转注释格式、状态变体规则
- `references/component-concept-map.md` — 当前 Q_tech 路径对应的组件名和子组件链

**B.1.5 前置：UI 元素 → 组件映射声明表**

生成第一个 flow 前先输出所有 flow 将用到的组件映射声明表（无需等用户确认）。若有 Q3 "Other" flow，须在声明表中注明参照的 Canonical Flow 名称 + 差异点。

**B.2 路径分叉**：
- H5 路径 → **读取 `references/mobile-h5-constraints.md`**（B1 图标名、B2 Empty 约束、B3 未使用变量、D1 副作用 Hook、视觉质量规范）
- RN 路径 → **读取 `references/mobile-rn-constraints.md`**（技术约束、Gluestack v2 本地组件 import、视觉质量规范）

**B.4 DS Coverage Notes**（每个 flow 结束后必须输出）：

```markdown
## DS Coverage Notes

### [组件库] Components Used
| 组件 | 用途 | 备注 |
|---|---|---|

### Mobile-Specific Patterns Used
| Pattern | 说明 | 平台 |
|---|---|---|

### Components Missing from Component Library
- [ ] [组件名]：当前用 [替代方案]，建议封装（理由：[为什么需要]）
```

**B.5** 参照 scenario 文件 `Anti-Patterns` 节逐条检查，有违反则附说明并修正。

### Phase C — App Shell 生成

生成 `src/flows/[app-name]/[app-name].tsx`，整合所有 flow。

- H5：antd-mobile `TabBar` + react-router-dom 路由 + `SafeArea`
- RN：Expo Router `(tabs)` layout + 文件路由 + `SafeAreaView`
- App Shell 图标名必须引用 Phase B 已输出的映射声明表，不得重新猜测
- H5 TabBar 布局规则见 `references/mobile-h5-constraints.md`（flex 列，禁止 `position:fixed`）

Phase C 完成后执行验证（H5: `npm run dev` + `npx vite build`；RN: 清理 SetupCheck + `npx expo start`）——详见对应 references 文件的 C.2 节。

### Phase D — 质量审查

- **D.1** DS Coverage Notes 汇总（Phase B 已逐 flow 输出，此处确认完整性）
- **D.2** Anti-Pattern 检查（参照 scenario `Anti-Patterns` 节）
- **D.3** 读取 `references/mobile-ui-review.md`，按 P1 → P2 → P3 扫描所有代码，P1 违反项输出修复代码，P3 以 ✅/⬜ 列出

### Handoff 提示（必输出）

> **协议**：按 [`_shared/next-skill.md`](../../_shared/next-skill.md) 三层结构模板输出；前 5 候选由 `_shared/skill-graph.json` 的依赖图算法实时算（done ⊆ ready，按 next_hint.preferred → alternatives → 同阶段 → anchor → fan-out 排序），优先建议从 `_shared/skill-graph.json#skills[id="flow-mobile"].next_hint` 读取。

**首行模板**：`✅ mobile页面设计 已完成，Mobile 页面 Flow + 代码 + 启动自检已完成。`

**本 Skill 的 `next_hint`**（来自 skill-graph.json，**不可在此 SKILL.md 内硬编码覆盖**）：

- **preferred**：`/check`
- **优先理由**：Mobile 页面完成立刻自检，提前抓出适配 / 触达 / 状态覆盖问题。
- **alternatives**：`/edge` (补全异常态（Mobile 异常更多）) · `/flow-web` (继续做 Web 端对应 Flow)
- **emoji**：🔍

**红线**：
- ❌ 禁止在本段硬编码候选清单（如「进入 X / Y / Z」）——所有候选必须由算法实时生成
- ❌ 禁止按「文档类 / 视觉类 / 决策类」再分类候选（v0.5.5 起，分类已折叠进 next_hint.alternatives）
- ❌ 禁止与「更新链路面板」段合并——两段必须各自独立成段，中间空一行
- ❌ 禁止漏第 2 行候选清单——即使候选只有 1 个、或为空（终端节点）也要写出来

---

## 快速检查清单

```
Flow 结构
- [ ] 屏幕数 2–6 范围内
- [ ] 每屏有标准注释头（FLOW / SCREEN N of M / PLATFORM / ENTRY / EXIT）
- [ ] 屏幕间有跳转注释
- [ ] 有 Happy Path、至少 1 个 Error Branch
- [ ] 定义三种 Exit State（Success / Error / Abandon）

代码质量（H5）
- [ ] antd-mobile 组件，颜色用 CSS 变量，间距 4px 倍数
- [ ] NavBar + SafeArea 正确处理安全区
- [ ] Empty 组件 + 外层 div 并排 CTA，不得嵌套 children
- [ ] 图标名为 antd-mobile-icons 实际导出名（AppOutline 等）
- [ ] useState 只解构实际用到的值和 setter
- [ ] 副作用全在 useEffect 内，useState 无副作用
- [ ] TabBar 用 flex 列布局，禁止 position:fixed

代码质量（RN）
- [ ] Gluestack UI v2 本地组件（@/components/ui/[x]），NativeWind className
- [ ] SafeAreaView 包裹根视图，触摸目标 ≥ 44pt
- [ ] 长列表用 FlatList，空状态含 CTA

移动端合规
- [ ] 订阅/内购 flow 有「恢复购买」入口，Paywall 有关闭按钮
- [ ] 权限请求前有自定义说明页
- [ ] 涉及资金操作有二次确认

输出完整性
- [ ] DS Coverage Notes 已输出，缺失组件已标注
- [ ] Anti-Pattern 检查已执行
- [ ] UI 质量检查 P1/P2 已执行，违反项已附修复代码
- [ ] P3 清单已输出（每条标注 ✅/⬜）
```

---

## 附录：Mobile Scenario 文件索引

| 场景 | 文件路径 | 覆盖 Flow 类型 |
|---|---|---|
| 消费者社交 | `scenarios/mobile/consumer-social.md` | 发帖 + 社交互动、相机拍摄发布、DM 私信 |
| 健康 & 运动 | `scenarios/mobile/health-fitness.md` | 开始锻炼 + 追踪、完成总结 + 历史记录、权限引导 |
| 移动端 AI 助手 | `scenarios/mobile/ai-assistant.md` | 发送消息 + 流式回复、语音输入转录、历史对话管理 |
| 消费者金融 | `scenarios/mobile/consumer-finance.md` | 账户总览 + 收款码、转账 + 生物识别确认、交易历史 |
| 电商 & 购物 | `scenarios/mobile/marketplace.md` | 商品浏览 + 详情、购物车 + 结账、搜索 + 筛选 |
| 外卖 & 本地餐饮 | `scenarios/mobile/food-delivery.md` | 发现附近店铺、商品定制 + 加购、快捷结账 + 订单追踪 |
| 娱乐 & 流媒体 | `scenarios/mobile/entertainment.md` | 内容浏览 + 详情、全屏视频 + Mini Player、Paywall 订阅 |
| 出行 & 旅游 | `scenarios/mobile/travel.md` | 搜索 + 预订交通、创建行程 + 事件管理、地图探索 |
| 教育科技 | `scenarios/mobile/edtech.md` | 个性化 Onboarding + Paywall、课程 + MCQ + 完成、每日练习 + Streak |
| 求职平台 | `scenarios/mobile/job-platform.md` | 搜索 + 筛选职位、查看详情 + Easy Apply、申请状态追踪 |
| 新闻阅读媒体 | `scenarios/mobile/reading-media.md` | 浏览 Feed + 阅读文章、个性化 Feed 设置、订阅付费解锁 |
| 设计媒体编辑 | `scenarios/mobile/design-tools.md` | 从模板创建并编辑、图像编辑 + 导出、AI 生成图像并插入 |
| 私信 & 群聊 | `scenarios/mobile/messaging.md` | 开始新会话、会话线程核心交互（文字/语音/图片）、聊天列表管理 |
| 任务 & 习惯管理 | `scenarios/mobile/productivity.md` | 快速添加任务、任务属性配置、日视图任务管理、习惯创建 + 每日打卡 |
| 约会 & 交友 | `scenarios/mobile/dating.md` | 滑卡发现、个人资料设置、配对后对话、高级功能付费升级 |
| 相机 & 照片编辑 | `scenarios/mobile/camera-photo.md` | 拍摄、照片滤镜 + 调整、导出 + 分享、图库整理 |

---

## 与兄弟 Skill 的边界（v0.4.0 补充）

| 场景 | 用谁 | 不用谁 |
| --- | --- | --- |
| Mobile 端（iOS / Android / RN / H5）多屏 Flow | **Flow Mobile** | Flow Web（Web 桌面 / 平板交互模式不同） |
| Web 端多屏 Flow | Flow Web | Flow Mobile（手势 / 底部导航 / 沉浸式头部不同） |
| 异常态专项穷举 | Edge | Flow Mobile（Flow 走 happy path） |
| IA 结构 / 站点地图 | Sitemap | Flow Mobile（Flow 是 sitemap 的下游具象化） |
| 单页响应式（Web → Mobile 自适应） | Flow Web 含响应式断点 | Flow Mobile（Flow Mobile 是原生 / H5 专属交互） |
| Landing 落地页 / Campaign 营销页 | Landing / Campaign（未来） | Flow Mobile（Flow 是产品页面 IA + 任务流） |

**Flow Mobile 不可替代性**：Mobile 端专属交互模式（手势 / 沉浸式导航 / 底部 tab / 拉刷 / 触底加载 / 安全区适配 / 软键盘策略）与 Web 端差异显著，单端 Skill 才能写到位。

## 质量标准

1. **多屏完整**：单 Flow ≥ 3 屏，每屏含状态（默认 / 输入 / 空 / 错误 / 加载），关键屏交互注释完整
2. **手势规约清晰**：tap / long-press / swipe / pinch / pull-to-refresh 必须显式标，不能默认「就这么用」
3. **导航模式选型**：底部 tab（≤ 5）/ 抽屉 / 顶部 tab / 嵌套 stack——必须选定一种主导航模式并说明原因
4. **安全区 + 软键盘适配**：iOS notch / Dynamic Island / Android 状态栏高度 / 软键盘弹出时表单避让——必须显式标
5. **触底加载 + 下拉刷新规约**：分页阈值 / 加载态 / 到底提示 / 空态——4 件套必须明确
6. **与 sitemap / stories 双向链**：每屏 page_id 与 sitemap 对应，每个交互对应 1 个 story 验收标准

## 红线规则

1. **不照搬 Web 模式**：Web 端的悬浮提示 tooltip / hover 状态 / 多栏布局在 Mobile 不成立——出现这些视为照搬未适配
2. **不省略空态 / 错误态**：Mobile 网络不稳定是常态，每个数据屏必须含「无网络 + 数据为空 + 加载失败」三态——缺一即不交付
3. **不替代 Edge 异常态穷举**：Flow Mobile 只画主流程 + 必要异常，全部异常态去 Edge 穷举——不要在 Flow 里塞所有 25 种 edge case
