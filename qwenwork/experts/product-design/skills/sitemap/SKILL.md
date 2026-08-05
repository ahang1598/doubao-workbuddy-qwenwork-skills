---
name: 站点地图
name_en: "sitemap"
argument-hint: "输入产品的主要功能，如：注册登录、商品浏览、下单支付、订单管理"
description: >
  站点地图（IA 骨架）。基于 /设计简报（业务目标 / 用户）+ /用户故事（功能拆解 + 设计触点）输出可被 Flow Web/Mobile 直接消费的站点结构——主导航 + 页面层级 + 路由命名 + 关键 flow 概览。设计师不必从零拉树状图，AI 从上游字段直接生成 IA 骨架，再让设计师调整。

  触发关键词：站点地图、sitemap、信息架构、IA、页面结构、路由设计、导航结构、有哪些页面、页面层级、Flow 之前的 IA 骨架。

  排除（反向）：单屏内的交互流程（用 /Web页面设计 / flow-mobile）、视觉风格（用 board）、用户旅程（用 /用户旅程）、原型详细稿（直接用 flow-web/mobile）。

description_en: >
  Information Architecture skeleton (Sitemap). Based on Brief (business goals / users) + Stories
  (feature breakdown + design touchpoints), generates a site structure directly consumable by Flow
  Web/Mobile — main navigation, page hierarchy, route naming, and key flow overview. AI derives the
  IA from upstream context so designers skip starting from a blank canvas.

  Triggers when a designer says: "sitemap", "information architecture", "IA", "page structure",
  "route design", "navigation structure", "what pages do we need", "page hierarchy",
  "IA skeleton before Flow", "站点地图".

  Excludes: intra-screen interaction flows (use /flow-web or /flow-mobile), visual style
  (use board), user journey map (use /journey), detailed prototype (go directly to
  /flow-web or /flow-mobile).

allowed-tools:
  - Read
  - Write
  - Glob
  - Grep
  - AskUserQuestion
chain:
  protocol_version: "1.0"
  reads: [brief, frame, scope, stories]
  writes: sitemap
  schema:
    skill: string
    generated_at: string
    project_name: string
    platform: enum [web, mobile, multi]
    primary_navigation:
      - id: string
        label: string
        route: string
        icon_hint: string
        children: array<NavItem>
    pages:
      - id: string
        route: string
        label: string
        purpose: string
        parent: string
        access: enum [public, authenticated, role-restricted]
        related_features: array<string>
        related_stories: array<string>
    key_flows:
      - name: string
        page_sequence: array<string>
    metadata:
      depth_max: number
      page_count: number
      platform_notes: string
---

# 站点地图

> 你是信息架构（IA）专家。基于 Brief 的业务目标 / 用户和 Stories 的功能拆解，生成可被 Flow Web/Mobile **直接消费**的站点结构——主导航、页面层级、路由命名、关键 flow 概览。

**与 Flow Web/Mobile 的边界**：
- **Sitemap** 关注**站点结构层**——页面有哪些、怎么组织、怎么命名路由（楼层平面图）
- **Flow Web/Mobile** 关注**页面内 + 多屏交互层**——每页的设计、组件、跳转细节（房间装修详图）

举例（产品复盘工具 DesignRetro）：
- Sitemap：主导航 `[Home, Board, Settings]`；Home 路由 `/new`，包含 4 屏序列 `[Welcome → ThreeQuestions → Preview → Done]`
- Flow Web：每屏的实际字段、组件类型、loading 态、跳转动画

**链式价值**：Sitemap 是 Flow Web/Mobile 的关键中间件——它们的 `chain.reads` 已声明读取 sitemap，但此前 Sitemap 不存在导致链路断口。补上后，Flow 不再需要从 brief 直接推 IA，而是基于已对齐的页面结构展开多屏设计，**质量与一致性显著上升**。

---

## Chain Context

### 上游读取（Step 0 执行）

按以下顺序尝试读取上下文：

1. 扫描会话中的 `<!-- spark-context:brief -->` / `<!-- spark-context:stories -->` / `<!-- spark-context:frame -->` / `<!-- spark-context:scope -->` marker
2. 读取项目目录 `spark-output/context/brief.json` / `stories.json` / `frame.json` / `scope.json`
3. 都没有则进入 Step 1 询问基本信息（用户描述 + 主要功能）

可复用字段映射：

- `brief.project_name` → `project_name`
- `brief.business_goal` → 决定主导航的优先级（KPI 相关功能上一级导航）
- `brief.user` / `frame.persona` → 决定首页 / 落地页的内容定位
- `brief.constraints` → 影响平台选择（如 "Web 优先" → platform: web）
- `brief.out_of_scope` → 排除某些 page 候选
- `stories.stories[*].design_touchpoints` → **核心**：每个 Story 的"涉及屏"直接转为 page 候选
- `stories.stories[*].design_touchpoints[].screen` → page id 与 label 的来源
- `scope.features` → 不基于 stories 时（用户跳过 Stories）的备用 page 候选
- `scope.target_users` → access 字段的依据（是否需要登录）

读到上下文后告知用户："读到 [项目名] 的 [Brief / Stories / ...] 上下文。本次将基于 [N] 个 Stories 的 design_touchpoints 与 [M] 条业务目标推导 IA 骨架。"

### 下游输出（Step 5 执行）

完成 Sitemap 后，**同时**做两件事：

1. **会话内输出**（marker 之间放裸 JSON，不要嵌套 ```json 代码块）：

   ```
   <!-- spark-context:sitemap -->
   {...JSON（schema 见 frontmatter）...}
   <!-- /spark-context:sitemap -->
   ```

2. **写入项目文件**：`spark-output/context/sitemap.json`（目录不存在时先创建）

3. **额外保存 Markdown 报告**：`spark-output/sitemap/[project-slug].md`，含树状图 + 路由表 + 关键 flow 序列。

下游可消费 Skill：**Flow Web / Flow Mobile**（Step 0 优先读 Sitemap，已有 sitemap 时跳过 IA 骨架重新设计） / **Check**（IA 一致性核对依据） / **PRD**（路由清单作为工程输入）。

### 字段流向下游

- `sitemap.platform` → **Flow Web** vs **Flow Mobile** 的路由判定（platform=web → 走 flow-web；mobile → flow-mobile）
- `sitemap.primary_navigation` → **Flow Web/Mobile** 的全局导航骨架；**Check** 的"信息架构"走查项；**Access** 的导航无障碍审计基础
- `sitemap.pages[]` → **Flow Web/Mobile** 的屏清单；**Edge** 的状态矩阵生成范围；**QA** 的页面级走查范围；**PRD** 的功能模块清单
- `sitemap.flows[]` → **Flow Web/Mobile** 的 flow 边界；**Edge** 的 flow 内部状态枚举依据；**Check** 的关键路径核查
- `sitemap.routing_table` → **PRD** 的工程交付段（路由配置）；**QA** 的 URL 命中率核查

---

## 触发条件

- 用户说"画个站点地图 / sitemap / IA 结构 / 页面结构"
- 用户说"在 Flow 之前先把 IA 定下来"
- 用户使用 `/站点地图` 指令
- Stories 完成后，用户希望先做 IA 骨架再进 Flow（推荐路径）

---

---

## 独立能力（无需连接器）

本 Skill 在完全离线、无任何连接器的场景下即可完整交付，所有方法论与输出形态不依赖外部系统：

- **IA 层级生成**：主导航 / 站点树 / 页面清单 / 关键 Flow 四段式输出
- **链式上下文双通道**：写入 `spark-output/context/sitemap.json` + 会话内 marker block，下游 Flow Web / Flow Mobile / PRD 可直接读取
- **导航结构对齐**：基于 Stories / Brief 自动推导，本地完成
- **关键 Flow 标注**：高频路径单独抽出，便于设计执行聚焦

> 红线：缺连接器时 **绝不 abort**，所有引导与输出路径必须照常完成。

## 增强能力（连接器加持）

接入以下连接器后，可减少手动粘贴、提高对齐效率。所有连接器均为可选，未装时按"降级路径"列的方式回落。

| 连接器 | 阶段 | 增强能力 | 降级路径 |
| --- | --- | --- | --- |
| **Figma** | 执行流程输出后 | 将 Sitemap 反向同步为 FigJam / Figma 页面结构（每个节点对应一个 Frame 占位），设计师可直接在 Figma 内继续细化 | 未装时输出本地 `sitemap-{project}.md` + Mermaid 树图，设计师手动建 Figma 页面 |

**接入触发**：用户首次调用 `/站点地图` 时，Skill 主动检测已认证的连接器并显示「已检测到：XXX，将自动启用增强模式」提示，用户可在该次会话中选择关闭。

**字段流向变化**：

- 启用 **Figma** → `chain.schema` 新增可选字段 `figma_page_map: array<{node_id, frame_url}>`，下游 Flow Web / Mobile 在 Step 2 文件映射时可直接复用

> 所有新增字段都是 **可选**，未启用连接器时字段缺省，下游 Skill 必须能容忍缺省。

---

## 执行流程

按 Step 0 → 1 → 2 → 3 → 4 → 5 顺序执行。

### Step 0 — Chain Context 读取

按上文执行。读到完整上下文（brief + stories）直接进入 Step 1 简化版。

### Step 1 — 平台与范围确认

用 `AskUserQuestion` 确认：

1. **平台**：
   - Web（桌面浏览器）
   - Mobile（H5 / App）
   - Multi（多端，需要考虑响应式 + 端差异）
2. **MVP 范围**（如果 stories.stories 数量 > 6）：
   - All（所有 stories 对应的页都纳入 sitemap）
   - P0 only（仅 priority=p0 的 stories 纳入）
   - 自定义（用户指定包含哪些）

读到 `brief.constraints` 中含"Web 优先"等明确指示时，平台默认匹配，仅做最终确认（不让用户重选）。

### Step 2 — 主导航生成

基于 `stories.design_touchpoints` 的 `screen` 字段聚类 + `brief.business_goal` 优先级，推导主导航。

**主导航数量约束**：
- Web：3-7 项主导航（超过 7 项需用户确认或合并）
- Mobile：3-5 项 TabBar（超过 5 项必须收敛）

**生成规则**：

1. **聚类**：把 stories 中所有 `design_touchpoints.screen` 按语义聚类（Welcome / 创建流程 → 同一类；Board / 看板 → 同一类）
2. **命名**：每个聚类提炼一个**1-2 字短动词或名词**作为导航 label（"创建"、"看板"、"设置"）
3. **排序**：按 business_goal 优先级降序——直接服务核心 KPI 的导航靠前
4. **图标提示**（icon_hint）：给设计师一个图标候选（lucide-react / ant-icons 名称），不是必填

**导航类型决策**：

| 平台 | 主导航形式 |
| --- | --- |
| Web | 顶部导航栏 / 侧边栏（按内容密度选择）  |
| Mobile | TabBar（底部 3-5 项）+ 二级菜单收纳其余 |
| Multi | 同时声明 web + mobile 两套，列在 metadata.platform_notes |

输出主导航草稿后让用户确认或调整。

### Step 3 — 页面层级展开

对每个主导航项，展开其下页面层级：

**深度约束**：
- 总深度 ≤ 3 层（首页 → 二级 → 三级）
- 超过 3 层意味 IA 设计有问题，需要扁平化

**每个 page 字段**：

```yaml
- id: page-create-new                # kebab-case，全局唯一
  route: "/new"                       # URL 路径
  label: "新建周回顾"                  # 中文（按用户语言）
  purpose: "用户从这里启动一次周回顾创建"  # 一句话描述这页存在的目的
  parent: "create"                    # 父级 nav id，顶层为空
  access: "authenticated"             # public | authenticated | role-restricted
  related_features:                   # 关联到 brief / scope 的功能 / strategy_dimensions
    - "用户引导"
  related_stories:                    # 关联到 stories[*].id
    - "story-1"
    - "story-2"
```

**路由命名规则**：

- kebab-case，全英文
- 资源型：`/items/[id]/edit`
- 操作型：`/new`、`/settings`
- 列表型：`/items`
- 详情型：`/items/[id]`
- 避免动词，优先用名词（`/board` 而非 `/view-board`）

**access 字段判断**：

- 落地页 / 营销页 / Auth 页 → public
- 用户内容 / 个人数据 → authenticated
- 团队管理 / 计费 / 高权限 → role-restricted

### Step 4 — 关键 flow 串联

不展开每屏细节（那是 Flow Web/Mobile 的事），但 Sitemap 应输出**关键 flow 经过哪些 page 的序列**，让 Flow Web/Mobile 直接消费。

每个 flow：

```yaml
- name: "Weekly Retro Creation"
  page_sequence:
    - "page-home"
    - "page-create-new"
    - "page-create-preview"
    - "page-create-done"
```

**flow 数量约束**：3-6 个关键 flow（不要全部 stories 都列，只列**对业务目标核心贡献**的）。

如果 stories 已包含详细的 design_touchpoints，sitemap 的 flow 是**对 stories 的简化串联**——把 `screen:` 字段提到的屏映射回 page id。

### Step 5 — 输出

#### 5.1 Markdown 报告（输出到对话 + 保存到 `spark-output/sitemap/[project-slug].md`）

```markdown
# Sitemap — [项目名]

- **生成时间**：[ISO8601]
- **平台**：Web / Mobile / Multi
- **数据源**：[Brief + Stories / ...]
- **页面总数**：N
- **最大深度**：M

## 主导航

- 🏠 [label] — [route]（[icon_hint]）
- 📋 [label] — [route]（[icon_hint]）
- ⚙️ [label] — [route]（[icon_hint]）

## 站点树

```
/
├── /new (新建周回顾) [auth]
│   ├── /new/welcome
│   ├── /new/questions
│   ├── /new/preview
│   └── /new/done
├── /board (看板) [auth]
│   ├── /board (this week)
│   ├── /board/history
│   └── /board/[id] (detail)
├── /settings [auth]
│   └── /settings/team
└── /auth [public]
```

## 页面清单

| ID | Route | Label | Purpose | Access | 关联 Story |
| --- | --- | --- | --- | --- | --- |
| ... | ... | ... | ... | ... | ... |

## 关键 Flow

### Weekly Retro Creation
`/` → `/new/welcome` → `/new/questions` → `/new/preview` → `/new/done`

### Team Board Browse
`/` → `/board` → `/board/[id]`

### Account Setup
`/auth` → `/settings/team`
```

#### 5.2 双通道 Context 输出

按 [chain-protocol.md](../../chain-protocol.md) §2.1 v1.1 智能适配规则：

**Step 1 — 写盘到 `spark-output/context/sitemap.json`**（必做，主持久化通道；目录不存在先创建）。写入以下完整 JSON：

```
{
  "skill": "sitemap",
  "generated_at": "<ISO8601>",
  "project_name": "...",
  "platform": "web|mobile|multi",
  "primary_navigation": [
    {
      "id": "create",
      "label": "新建",
      "route": "/new",
      "icon_hint": "plus-circle",
      "children": []
    }
  ],
  "pages": [
    {
      "id": "page-home",
      "route": "/",
      "label": "首页",
      "purpose": "...",
      "parent": null,
      "access": "public|authenticated|role-restricted",
      "related_features": [],
      "related_stories": []
    }
  ],
  "key_flows": [
    {
      "name": "Weekly Retro Creation",
      "page_sequence": ["page-home", "page-create-new", "page-create-preview", "page-create-done"]
    }
  ],
  "metadata": {
    "depth_max": 3,
    "page_count": 0,
    "platform_notes": "Web 优先；Mobile 端通过响应式降级"
  }
}
```

**Step 2 — chat 输出紧凑 marker**（必做，⛔ **不要在 chat 内重复输出 Step 1 的完整 JSON**）：

```
<!-- spark-context:sitemap ref="spark-output/context/sitemap.json" -->
Sitemap 已保存：project=[project_name]，platform=[web/mobile/multi]，[N] 个主导航项，[M] 个页面（最大深度 [D] 层），[K] 个关键 flow
<!-- /spark-context:sitemap -->
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

> **协议**：按 [`_shared/next-skill.md`](../../_shared/next-skill.md) 三层结构模板输出；前 5 候选由 `_shared/skill-graph.json` 的依赖图算法实时算（done ⊆ ready，按 next_hint.preferred → alternatives → 同阶段 → anchor → fan-out 排序），优先建议从 `_shared/skill-graph.json#skills[id="sitemap"].next_hint` 读取。

**首行模板**：`✅ 站点地图 已完成（平台：{platform}），IA {N} 段 + 页面节点树 + Mermaid 已生成。`

**多端项目提醒（条件触发）**：

当满足以下任一条件时，在首行之后、第 2 行候选清单之前，插入提醒段：

- `sitemap.platform` 为 `multi`，但本次只输出了一端的 IA（如只画了 Web 后台）
- `brief.user` 存在多个角色且分属不同端（如"店主→Web 后台"+"顾客→H5"）
- `brief.constraints` 包含多端关键词（如"Web + H5"、"管理端 + 用户端"）

提醒模板：

```
⚠️ 本次 Sitemap 覆盖了 [{已完成端}] 端的 IA 骨架。检测到项目还有 [{未覆盖端}] 端，建议再跑一次 `/sitemap` 为该端生成独立站点地图——两端的主导航结构、页面深度、核心 Flow 通常有显著差异，合在一张图里会丢失端差异。
```

> 不触发时（单端项目或 multi 且两端都已输出）不显示此段。

**本 Skill 的 `next_hint`**（来自 skill-graph.json，**不可在此 SKILL.md 内硬编码覆盖**）：

- **preferred**：`/flow-web`
- **优先理由**：IA 骨架就绪，直接进 Web 端页面级 Flow 设计。
- **alternatives**：`/flow-mobile` (Mobile 优先项目) · `/edge` (想先盘点异常态覆盖度) · `/chart` (项目以数据展示为主可先做图表规格)
- **emoji**：🏗️

**红线**：
- ❌ 禁止在本段硬编码候选清单（如「进入 X / Y / Z」）——所有候选必须由算法实时生成
- ❌ 禁止按「文档类 / 视觉类 / 决策类」再分类候选（v0.5.5 起，分类已折叠进 next_hint.alternatives）
- ❌ 禁止与「更新链路面板」段合并——两段必须各自独立成段，中间空一行
- ❌ 禁止漏第 2 行候选清单——即使候选只有 1 个、或为空（终端节点）也要写出来

---

## 实操注意事项

### 主导航数量超限怎么办

- Web 超 7 项 → 把次要项收纳到下拉菜单（如"账户"、"帮助"）；或拆分为顶部 + 侧边双导航
- Mobile 超 5 项 → 必须把次要项移到"更多"页 / 二级菜单；不接受 6+ 个 TabBar

### 页面深度超 3 层怎么办

- 超过 3 层意味用户找不到东西。三种重构选择：
  - **横切**：把深层内容提到上一级，用 Tab 切换
  - **聚合**：合并兄弟页面（如 "团队设置 + 个人设置" 合并为 "设置"）
  - **快捷入口**：保持深度但在主导航 / 首页加快捷入口

### 没有 Stories 上下文时怎么办

降级方案：

- 优先读 `scope.features` 把每个 feature 转为 page 候选
- 没有 scope 时，用 `frame.directions[lean].user_value` 推导核心 page 集
- 都没有时，进入 Step 1 询问"你的产品有哪些核心功能（3-5 个）"

不建议在没有任何上下文时跑 Sitemap——结果质量不可控。

---

## 已知限制

- 不画详细的页面 mockup（那是 Flow Web/Mobile）
- 不做 SEO 路由优化（如 slug 设计）
- Mobile App 的页面间转场动画类型由 Flow Mobile 决定，不在 Sitemap 范围
- 多端项目时 web/mobile 的 IA 可能不完全对齐（合理的差异），Sitemap 在 platform: multi 时会输出两套主导航说明

---

## 与兄弟 Skill 的边界（v0.4.0 补充）

| | Sitemap（本 Skill） | Brief | Stories | Flow Web / Mobile |
| --- | --- | --- | --- | --- |
| 视角 | **页面层级 / IA 骨架** | 项目策略一页纸 | 用户故事颗粒 | 屏级页面设计 |
| 核心输出 | 主导航 + 页面树 + 关键 Flow 索引 | 目标 / 用户 / 策略 / 约束 | epic + story + 设计触点 | 多屏 IA + 组件清单 + .tsx |
| 颗粒度 | **页面 / 路由级**（粗） | 项目级（极粗） | 需求级（中） | 屏级（细） |
| 何时用 | Brief 后、Flow 前——画清楚"有哪些页面、怎么连" | 项目启动对齐方向 | 拆分需求为可执行单元 | 进入页面级设计 |

**典型衔接**：Brief（定方向）→ Stories（拆需求）→ **Sitemap（搭骨架）** → Flow Web/Mobile（画页面）。

不做：单屏视觉设计（用 Flow Web）、详细交互流程（用 Flow Web）、信息架构方法论本身的卡片分类研究（用 Probe）。

---

## 质量标准

1. **主导航 ≤ 7 项**：超过 7 项要主动建议合并或下沉，避免认知过载
2. **页面树最多 3 层**：超过 3 层提示用户考虑扁平化（业务场景必要除外）
3. **每个页面必须可追溯到 story / brief feature**：page → story_id / feature_id 映射不能断
4. **关键 Flow 必须列入索引**：top 3 高频任务的入口页 + 经过页 + 终点页要在 Sitemap 里能追到
5. **命名一致性**：同一概念在导航 / 页面树 / Flow 里命名必须统一（不能"我的订单"与"订单列表"混用）
6. **不替代 Flow Web/Mobile**：Sitemap 只画"页面之间的关系"，不画"页面内部的内容布局"

## 红线规则

1. **不凭空造页面**：每个页面必须能追溯到 story / brief feature 或用户明确指定
2. **不替代 IA 卡片分类研究**：如果用户不确定 IA 怎么分，建议跑 Probe 的 card-sorting 方法做用户参与的 IA 验证，不替用户拍脑袋
3. **不替代导航设计研究**：Sitemap 给的是逻辑结构，具体导航形态（顶部 / 侧栏 / 底栏）建议在 Flow Web/Mobile 阶段结合具体场景决策
