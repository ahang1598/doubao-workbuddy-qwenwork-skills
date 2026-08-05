# Scenario: SaaS Management（SaaS 管理后台）

> **研究来源**：基于对 Stripe、Fingerprint、Kit、Homerun、ManyChat、Figma、Cohere、Resend、Airtable 等 9 个真实产品 flow 的横向分析抽象，不代表任何单一产品的具体实现。

---

## Identity

**Platform**: Web
**Definition**: B2B web application where authenticated operators (admins, managers) manage users, permissions, resources, and account settings for an organization or workspace.

**Canonical Examples**: Stripe Dashboard、Linear、Vercel、Resend、Airtable Workspace

**Not this scenario if**: 产品面向终端消费者（改用 web/ecommerce 或 ios/consumer-social）；产品以数据可视化为主（改用 web/data-analytics）；产品是移动端原生 App（改用对应 iOS scenario）。

---

## User Profile

| 维度 | 内容 |
|---|---|
| **主要角色** | Admin（最高权限）/ Manager（资源管理）/ Member（受限操作） |
| **核心目标** | 高效完成运营任务：管理用户、配置资源、查看数据 |
| **心智模型** | 熟悉企业软件（如 Google Workspace、Notion），期待侧边栏导航、表格列表、设置页 |
| **使用频率** | 高频日常使用，任务驱动，目标明确 |
| **决策模式** | 任务驱动型：清楚要做什么，期望路径最短、反馈即时 |
| **容错期望** | 低容错：操作不可逆时必须有确认步骤（删除、权限变更） |

---

## IA Template

**导航模式**: Sidebar（左侧固定导航）
- 一级：产品核心功能区（Dashboard、数据、资源列表）
- 二级：Settings 作为独立区域，通过 sidebar 底部或 avatar 下拉访问
- 移动端：Sidebar 折叠为顶部 Hamburger 或底部 Tab Bar

**页面层级**: 3 级
```
L1: Dashboard / 主功能区（Overview）
L2: 资源列表页（List）→ 资源详情页（Detail）
L3: 编辑表单（Edit）或 Settings 子页
```

**权限角色结构**:
```
Admin     → 全部操作（含邀请成员、删除账户、修改计划）
Manager   → 管理资源，不能修改账户级设置
Member    → 查看+特定操作，不能管理其他成员
（高复杂产品可有 Viewer、Custom 角色）
```

**数据密度**: 高
- 核心视图：Table（多列，含状态 Badge、行操作 DropdownMenu）
- 辅助视图：Card（统计数据 / KPI，仅在 Dashboard 使用）
- 不使用：无限滚动列表（用分页 Table 代替）

**主要容器模式**:
| 场景 | 容器 |
|---|---|
| 简单创建/编辑（≤5字段） | Dialog（弹窗） |
| 复杂创建/编辑（>5字段，多分组） | Sheet（右侧抽屉）或全页面 Form |
| 不可逆操作确认（删除、撤销邀请） | AlertDialog |
| 详情查看 | 新页面（Detail Page）或 Sheet |
| 多步骤配置（订阅、引导） | 全屏多步 Modal Wizard |

**导航骨架图（ASCII）**:
```
┌──────────────────────────────────────────────────────┐
│  Logo    [Search / Cmd+K]              [Avatar ▾]    │
├────────┬─────────────────────────────────────────────┤
│        │  PageHeader: Title         [Primary Action] │
│ Nav    ├─────────────────────────────────────────────┤
│        │  Toolbar: [Search____] [Filter ▾] [Export]  │
│ ─────  ├─────────────────────────────────────────────┤
│ Item 1 │                                             │
│ Item 2 │  Table / Main Content                       │
│ Item 3 │                                             │
│        │  ─────────────────────────────────────────  │
│ ─────  │  □ Row 1   Badge   Role   Date   [···]     │
│ Settings│  □ Row 2   Badge   Role   Date   [···]     │
│        │  □ Row 3   Badge   Role   Date   [···]     │
│ [Help] ├─────────────────────────────────────────────┤
│ [User] │  Pagination: ← 1 2 3 → | 20/page ▾         │
└────────┴─────────────────────────────────────────────┘
```

---

### 图 2：关键状态对比图（Key State Variations）

```
左：Table 有数据行（正常态）                右：资源列表为空（空状态 + 创建引导）

┌────────────────────────────────────┐  ┌────────────────────────────────────┐
│ Members                [+ Invite]  │  │ Members                [+ Invite]  │
├────────────────────────────────────┤  ├────────────────────────────────────┤
│ [Search...]  [Role ▾]  [Status ▾] │  │ [Search...]  [Role ▾]  [Status ▾] │
├──────────────────────────────────  │  ├──────────────────────────────────  │
│ □  Alice Wu   Admin   ● Active ···│  │                                    │
│ □  Bob Lee    Member  ● Active ···│  │                                    │
│ □  Carol X    Member  ○ Pending ··│  │         👥                         │
│ □  Dan Park   Manager ● Active ···│  │   No team members yet.             │
│ □  Eve Chen   Member  ● Active ···│  │   Invite your first team member    │
│                                    │  │   to get started.                  │
│ ← 1 2 3 →    20/page ▾     5 of 24│  │                                    │
│                                    │  │   [+ Invite Team Member]           │
└────────────────────────────────────┘  └────────────────────────────────────┘
```

---

### 图 3：覆层层级图（Overlay Hierarchy）

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Logo  [Search / Cmd+K]                                  [Avatar ▾]      │ ← Top Bar（z-100）
├────────┬─────────────────────────────────────────────────────────────────┤
│        │  Members                                   [+ Invite]           │
│ Nav    ├─────────────────────────────────────────────────────────────────┤
│        │  ┌──────────────────────────┐              ┌───────────────────┐ │
│ Item 1 │  │  Invite Modal（中）      │              │  Detail Sheet（右）│ │
│ Item 2 │  │  z-index: 300           │              │  z-index: 200      │ │
│ Item 3 │  │                         │              │                    │ │
│        │  │  Email:                 │              │  Member: Alice Wu  │ │
│ ─────  │  │  [user@example.com    ] │              │  Role: Admin       │ │
│Settings│  │                         │              │  Status: ● Active  │ │
│        │  │  Role:                  │              │  Last login: Apr 26│ │
│ [Help] │  │  ● Admin (全部权限)     │              │                    │ │
│ [User] │  │  ○ Manager (资源管理)   │              │  [Edit Role]       │ │
│        │  │  ○ Member (只读+操作)  │              │  [Remove Member]   │ │
│        │  │                         │              └───────────────────┘ │
│        │  │  [Cancel] [Send Invite] │    ▲ 触发: 行操作 ··· → View      │
│        │  └──────────────────────────┘                                   │
│        │    ▲ 触发: 点击 [+ Invite]                                      │
│        │                                                                  │
│        │  ┌────────────────────────────────────┐                         │
│        │  │  Delete AlertDialog（中）z-index:400│                         │
│        │  │  Remove Carol X from workspace?    │                         │
│        │  │  They will lose all access.        │                         │
│        │  │  [Cancel]   [Remove Member]        │                         │
│        │  └────────────────────────────────────┘                         │
│        │    ▲ 触发: ··· → Remove member（不可逆操作强制确认）             │
└────────┴─────────────────────────────────────────────────────────────────┘
  ┌──────────────────────────────────────────┐
  │  ✓ Invite sent to user@example.com  [×]  │  ← Toast（底部，z-500）
  └──────────────────────────────────────────┘

触发关系说明:
- Invite Modal（中）: 点击 [+ Invite] 触发，居中弹出，z-300；字段 ≤5 个用 Dialog
- Detail Sheet（右）: 行操作 ··· → View Details 触发，右侧滑入，z-200，主列表仍可见
- Delete AlertDialog（中）: 行操作 ··· → Remove 触发，z-400 阻断（高于 Sheet），强制确认
- Toast（底）: 邀请发送成功、权限变更等轻量反馈，z-500，3-5 秒自动消失
```

---

## 该场景独有的 IA/UX 决策

1. **字段数量决定容器选型：≤5 字段用 Dialog，>5 字段用 Sheet** — B2B SaaS 的「创建/编辑」操作有严格的容器选型规则：字段 ≤5 个用 Dialog（不离开列表上下文，快速完成）；字段 >5 个或有多分区用 Sheet（右侧抽屉，可承载更多内容）；复杂多步骤配置（订阅升级、初始引导）用全屏 Modal Wizard。这与消费者产品（不论字段多少一律全页表单）有本质差异——B2B 用户在工作流中频繁创建资源，减少页面跳转是核心效率诉求。研究样本中 Stripe（简单邀请用 Dialog）与 Fingerprint（含高级权限用 Sheet 可折叠扩展）分别是两端的参考实现。

2. **邀请产生 Pending 三态，不是即时加入** — B2B SaaS 的成员邀请不同于消费者产品的「关注」——被邀请者必须接受邮件邀请才能加入，产生「Pending」中间状态。成员列表必须通过状态 Badge 区分三态：Active（正常成员）/ Pending（邀请已发出、未接受）/ Suspended（已暂停）。Pending 行须提供「Resend invite」和「Revoke」两个行操作（而非仅「Remove」）。忽略三态只用 Active/Inactive 二态，会导致 Admin 无法管理「僵尸邀请」——发出去但长期未被接受的邀请没有任何管理入口，Shuttle（flow_id 6369）和 Fingerprint（flow_id 11173）均验证了此模式。

3. **角色选择必须内嵌权限描述，不能只显示角色名** — B2B SaaS 的角色（Admin / Manager / Member 等）对于新操作者不直观——大多数人无法直觉判断「Manager 和 Member 的区别是什么」。角色 RadioGroup 或 Select 中每个选项必须附带 1–2 行权限描述（如「Can invite members and manage all resources」vs「Can view and edit assigned resources only」）。Fingerprint（flow_id 11173）的「Advanced permissions」Collapsible 是复杂权限场景的正确解法：先提供简洁的预设角色，再允许高级用户展开细粒度权限控制，不强迫所有用户面对权限矩阵。

4. **Settings 是独立管理空间，不是主导航一级项目** — B2B SaaS 的 Settings（包含团队管理、账单、API Key、Webhook、通知等）入口在 Sidebar 底部或 Avatar 下拉菜单，不与「Dashboard / List / Reports」平级。这体现「工作频率分层」原则：用户每天使用 Dashboard 和资源列表，但每周或每月才需要进入 Settings。把 Settings 放在主导航会造成层级混乱（设置操作与日常操作混在一起），降低核心功能的可发现性。Settings 内部则用子页面 Tabs（Team / Billing / API / Notifications）组织，不用嵌套 Sidebar。

5. **Upgrade CTA 在产品内多点触发，价格随席位动态计算** — B2B SaaS 的订阅升级不依赖用户主动访问定价页，而在产品内自然触发：① Sidebar 底部的升级 Badge；② 功能受限时的 inline 提示（「This feature requires Pro · Upgrade」）；③ Settings → Billing 当前计划展示旁边。升级 Modal 必须包含席位数量选择（价格随席位动态计算：N seats × $X/seat = $Y/month）和年付/月付切换（年付通常有折扣 Badge 如「Save 20%」）——这是与消费者订阅（固定价格选计划）的关键差异。右侧实时 Summary 面板（Grammarly、Stellate、Rox 均有）是席位计价场景的必要组件。

---

## Canonical Flows

> 以下 flow 基于 13 个真实产品样本的横向分析抽象。括号内标注「行业共识」表示 3 个以上产品采用相同模式。

---

### Flow 1: Invite Team Member（邀请成员）

**在此场景的特殊性**: B2B SaaS 的邀请模式区别于消费者产品——被邀请者不会立即加入，而是产生「Pending」状态等待对方接受（Stripe、Fingerprint、Kit、Homerun 均如此）。角色选择是关键决策节点，必须附带权限描述文字辅助判断（纯角色名不够）。Fingerprint 的「Advanced permissions」Collapsible 展开是复杂权限场景的行业解法。入口在 Settings → Team，不是主导航直达，符合 B2B 后台「设置区管理成员」的心智模型。

**行业共识**：出现在全部 13 个样本产品中，是 SaaS 后台最高频的用户管理任务。

**前置条件**: 当前用户为 Admin 角色（Manager 和 Member 无权邀请成员）；未超过套餐席位上限
**若前置条件不满足**: 非 Admin 用户看不到「+ Invite」按钮；席位已满 → 触发升级提示（Flow 3 路径）

**Entry**: Settings → Team → 点击「+ Invite / New Member」按钮

```
Screen 1: Team Members List
  主操作: 点击「+ Invite」CTA（右上角，primary button）
  关键组件: Table（成员列表：姓名/邮箱、角色 Badge、状态 Badge、最后登录）
            Input（搜索过滤）, DropdownMenu（行操作：改权限 / 移除）
  → 点击「+ Invite」: 打开 Dialog（Screen 2）
  → Empty State: Card 居中，「还没有成员，邀请第一个」+ Invite CTA

Screen 2: Invite Modal
  主操作: 填写邮箱 + 选择角色 → 点击「Send Invite」
  关键组件: Dialog, Input（邮箱）, RadioGroup 或 Select（角色选择）
            [可选] Collapsible「Advanced permissions」展开精细权限
            Button（Send Invite, primary）, Button（Cancel, ghost）
  → 角色说明: 角色旁边显示描述文字（引导用户选择）
  → 表单验证失败: 邮箱 Input 显示 inline 错误
  → 点击「Send Invite」成功: 关闭 Dialog，Toast 确认（Screen 3）

Screen 3: Updated Team List（成功状态）
  主操作: 确认邀请已发出（可选：Resend / Revoke）
  关键组件: Table（新增一行，Badge 显示「Pending」），Toast（「邀请已发送」）
  Exit: 用户停留在 Team List 页
```

**Exit State**:
- ✅ Success：Toast「邀请已发送至 xxx@email.com」+ 新成员出现在列表，状态为「Pending」
- ❌ Error：邮箱已存在时，Dialog 内显示 inline 错误「该用户已是成员」
- ↩ Abandon：关闭 Dialog，无任何改动，返回 Team List

---

### Flow 2: Manage Member Permissions（修改成员权限）

**在此场景的特殊性**: B2B SaaS 的权限变更影响他人访问范围，是高风险操作，需要比消费者产品「修改偏好」更强的确认机制。研究样本中出现两种入口模式：行内 Dropdown 直接切换角色（Ballpark、Hello Ivy——高效但无确认）vs. 行内菜单 → Dialog 选择（Kit——有缓冲，适合权限更复杂的产品）。角色数量 ≤ 4 时用 Dropdown 或 RadioGroup 均可；超过 4 个或有精细权限时必须用 Dialog + 角色描述。

**行业共识**：出现在 Ballpark、Kit、Hello Ivy 等 6 个样本中。

**前置条件**: 当前用户为 Admin；目标成员状态为 Active 或 Pending（Suspended 成员需先恢复再改权限）；不能修改自己的角色（防止唯一 Admin 自降权限导致锁定）
**若前置条件不满足**: 当前成员是唯一 Admin → 降权操作被 AlertDialog 阻止并说明限制

**Entry**: Team List → 某成员行的「···」DropdownMenu → 选择「Edit permissions / Change role」

```
Screen 1: Team Members List（当前状态）
  关键组件: Table, DropdownMenu（每行，包含：Edit permissions / Remove member）
  → 点击「Edit permissions」: 打开 Dialog（Screen 2）
  → 点击「Remove member」: 打开 AlertDialog 确认

Screen 2: Edit Permissions Modal
  主操作: 选择新角色 → 点击「Update」
  关键组件: Dialog, RadioGroup（角色选项 + 角色描述）
            Button（Update, primary）, Button（Cancel, ghost）
  → 选择角色时: 高亮当前选中角色，显示权限描述
  → 点击「Update」: 关闭 Dialog，列表即时刷新

Screen 3: Updated Team List（权限已变更）
  关键组件: Table（该成员的 Role Badge 已更新），Toast（「权限已更新」）
  Exit: 停留在 Team List
```

**Exit State**:
- ✅ Success：角色 Badge 即时更新 + Toast 确认
- ❌ Error：无法降权（如唯一 Admin 不能降为 Member），AlertDialog 提示限制
- ↩ Abandon：Cancel 关闭 Dialog，权限未变

---

### Flow 3: Subscription Plan Upgrade（升级订阅计划）

**在此场景的特殊性**: B2B SaaS 的升级通常从产品内部触发（侧边栏底部升级 CTA / 功能限制处 / Settings → Billing），而非独立营销页。席位数量是关键变量，价格随席位动态计算（消费者产品通常是固定价格）。年付/月付 Toggle + 实时 Summary 面板是行业共识（Grammarly、Stellate、Rox 均有）。Rox 的「先加支付方式再升级」两步分离模式适用于无存储卡的新账户场景。

**行业共识**：出现在 Stellate、Grammarly、Rox 等样本中，适用于 SaaS 产品的计划升级场景。

**前置条件**: 当前用户为 Admin（只有 Admin 有权修改账单计划）；当前套餐为 Free 或低阶付费套餐
**若前置条件不满足**: 非 Admin 点击升级入口 → 提示「只有 Admin 可以修改订阅计划」；已是最高计划 → 无升级 CTA，显示当前计划详情

**Entry**: 产品内 Upgrade CTA（侧边栏底部 / 功能限制处 / Settings → Billing）

```
Screen 1: Plan Comparison
  主操作: 选择目标计划 → 点击「Continue」
  关键组件: Dialog（全屏 Modal Wizard），Card × 2（Free vs Pro 对比）
            Button（Continue, primary）, Link（Learn more）
  → 右侧面板: 实时更新 Summary（价格、席位数、到期日）

Screen 2: Choose Billing Cadence
  主操作: 选择月付 / 年付 → 点击「Continue」
  关键组件: Card × 2（Monthly / Annual，含「节省 X%」Badge）
            Summary 面板（实时更新：席位数 × 单价 = 小计）
            Button（Continue）, Button（Back, ghost）

Screen 3: Payment Method
  主操作: 填写支付信息 → 点击「Subscribe / Start Trial」
  关键组件: Tabs（Card / Bank），Form（卡号、有效期、CVV、国家）
            Summary 面板（最终金额确认），Link（订阅条款）
            Button（Subscribe, primary）, Button（Back, ghost）

Screen 4: Confirmation
  主操作: 确认升级成功 → 点击「Get Started」
  关键组件: Dialog（成功状态，可含 illustration 或 confetti），
            升级功能列表，Button（Get Started）
  Exit: 关闭 Modal，返回产品，新功能已解锁
```

**Exit State**:
- ✅ Success：确认页 + 新计划功能即时可用
- ❌ Error（支付失败）：Screen 3 显示 inline 错误，保留已填信息
- ↩ Abandon：任意步骤可「Back」或关闭 Modal，无扣费

---

### Flow 4: Create & Manage Resource（创建并管理业务资源）

**在此场景的特殊性**: 这是 SaaS 后台最通用的 CRUD pattern，适用于「项目 / API Key / Webhook / 集成 / 规则」等各类业务资源。「字段数量决定容器选型」是 B2B SaaS 独有的约定（≤5字段用 Dialog，>5字段用 Sheet 或全页 Form），消费者产品通常一律使用全页表单。不可逆删除必须用 AlertDialog 二次确认，在 B2B 环境中误删的业务代价远高于消费者场景，容错期望极低。

**说明**：通用 CRUD 模式，适用于「项目 / API Key / Webhook / 集成 / 规则」等各类业务资源。

**前置条件**: 当前用户有该资源类型的创建/编辑权限（通常为 Admin 或 Manager）
**若前置条件不满足**: Member 角色访问列表页时不显示「+ New」按钮，行操作 ··· 菜单仅显示「View」，无「Edit」/「Delete」

**Entry**: 资源列表页 → 点击「+ New [Resource]」

```
Screen 1: Resource List
  主操作: 点击「+ New」CTA
  关键组件: Table（资源列表），Input（搜索），Select（筛选状态）
            Button（+ New, primary），DropdownMenu（行操作）
  → Empty State: Card 居中 + Icon + 说明文字 + 「Create first [Resource]」CTA

Screen 2: Create Form
  主操作: 填写字段 → 点击「Create」
  字段 ≤ 5 → 用 Dialog；字段 > 5 → 用 Sheet 或全页 Form
  关键组件: Input × N, Select × N, Textarea（描述）
            Button（Create, primary）, Button（Cancel, ghost）
  → 提交中: Button 变为 loading 状态，字段 disabled
  → 验证错误: 字段 inline 错误提示

Screen 3: Resource Detail（创建成功后跳转）
  主操作: 查看 / 编辑 / 删除
  关键组件: Breadcrumb, Badge（状态）, Button（Edit, secondary）
            Button（Delete, ghost destructive），Tabs（子内容分区）
  → 编辑: 原地 Edit 或跳转 Edit Form
  → 删除: AlertDialog 二次确认
```

**Exit State**:
- ✅ Success：跳转到新资源详情页，Toast「[Resource] 已创建」
- ❌ Error（名称重复）：Dialog/Sheet 内 inline 错误，不关闭
- ↩ Abandon：取消返回列表，无变更

---

## Component Kit

按使用频率排序（基于研究样本观察）：

| 优先级 | 功能概念 | 具体用途 |
|---|---|---|
| ★★★ | 高级数据表格 | 成员列表、资源列表（多列 + 状态标签 + 行操作） |
| ★★★ | 模态对话框 | 邀请表单、权限编辑（≤5字段） |
| ★★★ | 状态标签 | 状态（Active/Pending/Error）、角色标签 |
| ★★★ | 操作按钮 | 所有操作 CTA（含 loading 状态） |
| ★★★ | 表单容器（含校验）+ 单行文本输入 | 所有表单字段 |
| ★★ | 下拉操作菜单 | 表格行内「···」操作菜单 |
| ★★ | 危险操作确认 | 删除/撤销等不可逆操作的二次确认 |
| ★★ | 侧边面板/抽屉 | 复杂表单（>5字段）、详情侧边面板 |
| ★★ | 单选组 | 角色选择（互斥，≤6选项） |
| ★★ | 选择下拉 | 筛选、下拉选择（选项多于 6 个时） |
| ★★ | 操作通知（Toast） | 操作成功的非阻断确认（保存、邀请发送） |
| ★ | 标签页切换 | 详情页内容分区（Overview / Activity / Settings） |
| ★ | 加载骨架屏 | 列表和数据加载占位 |
| ★ | 面包屑导航 | 三级及以上页面的路径指示 |
| ★ | 单个可折叠区域 | 权限高级选项（Advanced permissions 展开） |
| ★ | 分页控件 | 成员列表 / 资源列表分页（数据 > 20 条） |

---

## Anti-Patterns

基于研究样本中观察到的设计错误：

- **22 屏向导创建单个资源**（ShareWillow 案例）：复杂配置应拆分为「快速创建 + 后续配置」两个流程，而非单次 22 步填写。超过 6 屏时必须拆分。

- **Toast 替代错误提示**：操作失败时只用 Toast 显示错误，3 秒后消失，用户不知道哪里出了问题。→ 正确做法：表单错误用 inline 提示（紧邻字段），Toast 只用于成功反馈。

- **角色选择不提供描述**：只展示角色名（Admin / Member）而不解释权限差异，导致邀请者随机选择。→ 正确做法：每个角色旁边显示 1-2 句描述，或在 Dialog 右侧放说明面板（Stripe 模式）。

- **删除操作无二次确认**：直接删除成员 / 资源，无 AlertDialog。→ 正确做法：不可逆操作必须用 AlertDialog，明确说明后果（「删除后无法恢复」）。

- **全页刷新代替局部更新**：邀请成员后整页刷新，用户失去操作上下文。→ 正确做法：操作成功后局部更新列表（新增行 / 状态变更），Toast 确认，不刷页。

- **Empty State 只显示「暂无数据」**：缺少引导 CTA，用户不知道下一步。→ 正确做法：Empty State 必须包含操作 CTA（如「邀请第一个成员」），解释为什么是空的。

- **设置页全部字段同时编辑 + 统一提交**：修改 3 处设置，点击一次「保存全部」，出错时用户不知道哪个失败。→ 正确做法：每个 Section 独立保存（按段落 Save），或分离关键设置到独立 Dialog。
