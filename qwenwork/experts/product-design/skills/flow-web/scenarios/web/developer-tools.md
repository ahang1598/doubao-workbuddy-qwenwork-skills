# Scenario: 开发者工具 / Developer Tools

## Identity
**Platform**: Web
**Definition**: 面向技术用户（开发者）的 SaaS 产品，核心价值通过 API、SDK 或 CLI 交付；产品需要将"账号创建"与"首次 API 调用成功"之间的摩擦降到最低。
**Canonical Examples**: OpenAI Platform、Resend、Anthropic Console、Cohere、Gladia、Factory AI
**Not this scenario if**:
- 不提供 API Key 或 SDK（→ SaaS 管理后台）
- 主要受众是业务人员或运营，不写代码（→ 内部运营工具）
- 是面向消费者的 AI 产品（→ AI 产品场景）

---

## User Profile

| 维度 | 内容 |
|---|---|
| 主要角色 | 独立开发者 / 工程师 / DevRel / 技术评估者 |
| 核心目标 | 完成 API 集成——从注册到收到第一次真实 API 响应 |
| 心智模型 | "开源文档 + npm install"——期望自助完成，不需要销售介入 |
| 使用频率 | 初次 onboarding 一次性；进入生产后高频使用 Dashboard + Docs |
| 决策模式 | 任务驱动（完成集成任务）+ 文档参考（反复查阅 API Ref） |

---

## IA Template

**导航模式**: TopBar（品牌 + 主导航）+ 左侧 Sidebar（功能树 / 文档树）  
选择理由：开发者工具同时提供"产品控制台（Dashboard/API Keys）"和"文档（Docs/Playground）"两套内容，顶导负责切换，左侧 sidebar 负责分类导航。

**页面层级**: 3-4 级  
`Dashboard（首页）→ 功能列表（API Keys / Projects）→ 详情 / 创建向导 → Playground`

**权限角色**: 2-3 个  
- Owner：全部权限，含 Billing、Key 管理、团队邀请  
- Member / Developer：创建 Key、调用 API，不可修改账单  
- 只读 / Viewer（可选）：只能查看用量和文档

**数据密度**: 中  
API Key 列表、用量统计（表格/图表）；Playground 为全屏编辑器模式；文档页为文章+代码块混排。

**主要容器模式**: Dialog（创建 Key、确认删除）+ 全页面（Playground 三栏、文档）+ Quickstart 步进向导

### 导航骨架图（ASCII）

```
┌──────── TopBar ─────────────────────────────────────────────┐
│  Logo │ Dashboard  Docs  Playground  API Keys │ Avatar Menu │
└─────────────────────────────────────────────────────────────┘
│  Left Sidebar         │  Main Content Area                  │
│  ┌──────────────┐     │  ┌────────────────────────────────┐ │
│  │ Overview     │     │  │  Dashboard / List / Editor     │ │
│  │ Projects     │     │  │                                │ │
│  │   ├ API Keys │     │  │  [Quickstart steps]            │ │
│  │   └ Usage    │     │  │  [API Key table]               │ │
│  │ Playground   │     │  │  [Three-column Playground]     │ │
│  │ Docs         │     │  │                                │ │
│  │   ├ Guides   │     │  └────────────────────────────────┘ │
│  │   └ API Ref  │     │                                     │
│  └──────────────┘     │                                     │
└───────────────────────┴─────────────────────────────────────┘
```

---

#### 图 2：关键状态对比图（Key State Variations）

```
左：API Keys 列表有效态（多个 Key，含状态）    右：API Keys 空状态（新账号，无 Key）

┌────────────────────────────────────┐  ┌────────────────────────────────────┐
│ API Keys               [+ Create]  │  │ API Keys               [+ Create]  │
├────────────────────────────────────┤  ├────────────────────────────────────┤
│ Name        Secret    Last used    │  │                                    │
│ ─────────────────────────────────  │  │                                    │
│ prod-key-1  sk-****  2h ago [···]  │  │         🔑                         │
│ staging     sk-****  3d ago [···]  │  │   No API keys yet.                 │
│ test-key    sk-****  Never  [···]  │  │   Create an API key to start       │
│              Revoke / Delete       │  │   integrating with our API.        │
│                                    │  │                                    │
│                                    │  │   [Create API key]                 │
└────────────────────────────────────┘  └────────────────────────────────────┘
```

---

#### 图 3：覆层层级图（Overlay Hierarchy）

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Logo │ Dashboard  Docs  Playground  API Keys │           [Avatar ▾]      │ ← TopBar（z-100）
├─────────────────────┬────────────────────────────────────────────────────┤
│  Left Sidebar       │  API Keys                          [+ Create key]  │
│                     │  ─────────────────────────────────────────────────  │
│  Overview           │  Name        Secret    Last used   Status          │
│  Projects           │  prod-key-1  sk-****   2h ago      Active  [···]  │
│  ├ API Keys ←       │  staging     sk-****   3d ago      Active  [···]  │
│  └ Usage            │                                                     │
│  Playground         │  ┌──────────────────────────────────────────────┐  │
│  Docs               │  │  Create API Key Dialog（中）z-index: 300      │  │
│                     │  │  Key name (optional)                         │  │
│                     │  │  [production-key___________________]         │  │
│                     │  │  [Cancel]              [Create secret key]   │  │
│                     │  └──────────────────────────────────────────────┘  │
│                     │    ▲ 触发: 点击 [+ Create key]                      │
│                     │                                                     │
│                     │  ┌──────────────────────────────────────────────┐  │
│                     │  │  New Key Banner（z-300，替换 Dialog）          │  │
│                     │  │  Save your key — it won't be shown again.    │  │
│                     │  │  sk-**********************  [Show] [Copy]    │  │
│                     │  │  [I've copied this key — Continue]           │  │
│                     │  └──────────────────────────────────────────────┘  │
│                     │    ▲ 触发: Create 成功后立即展示（替换 Dialog）      │
│                     │                                                     │
│                     │  ┌──────────────────────────────────────────────┐  │
│                     │  │  Revoke Key AlertDialog（中）z-index: 400    │  │
│                     │  │  Revoke "staging"?                           │  │
│                     │  │  Any app using this key loses access now.    │  │
│                     │  │  This cannot be undone.                      │  │
│                     │  │  [Cancel]              [Revoke key]          │  │
│                     │  └──────────────────────────────────────────────┘  │
│                     │    ▲ 触发: Key 行 [···] → Revoke                   │
└─────────────────────┴────────────────────────────────────────────────────┘
  ┌──────────────────────────────────────────┐
  │  ✓ API key revoked successfully   [×]    │  ← Toast（底部，z-500）
  └──────────────────────────────────────────┘

触发关系说明:
- Create Dialog（中）: 点击 [+ Create key] 触发，z-300，输入名称后生成
- New Key Banner（中）: Create 成功后替换 Dialog，z-300，强制用户确认已复制后关闭
- Revoke AlertDialog（中）: Key 行 [···] → Revoke 触发，z-400，不可撤销操作强制确认
- Toast（底）: Revoke 成功轻量反馈，z-500，3-5 秒消失
```

---

## 该场景独有的 IA/UX 决策

1. **API Key 的「一次性可见」仪式感设计**  
   Key 生成是高权限操作，产品刻意通过「显示一次，请立即复制」警示文案 + 不可再次查看的设计传递安全语义。UI 层用遮罩显示 + copy 按钮组合，而非普通 input field。删除和重新生成是唯一的 recovery path。

2. **Quickstart 作为 Activation 核心，而非可选引导**  
   无论产品复杂度如何（3 屏到 26 屏），所有产品都把「生成第一个 key + 跑第一段代码」作为 activation moment。成功标志不是「账号创建完成」，而是「收到第一次真实 API 响应」。

3. **代码示例内联预填 Key，消除集成摩擦**  
   用户生成 key 后，页面上的代码 snippet 自动将 key 内联填入（`Authorization: Bearer sk-xxx`），无需手动替换 placeholder。Tab 切换语言时 key 保持内联，直到用户离开页面。

4. **三栏 Playground = 开发者核心循环工作台**  
   Schema/Docs（左，探索）+ Query/Prompt editor（中，编写）+ Response panel（右，验证）对应 Learn → Write → Test 思维循环。Apollo、Anthropic Workbench、Cohere 独立收敛到此布局，是行业最强 IA 共识，不应被简化。

5. **新一代 AI Agent 开发者工具新增「Session 创建」前置流程**  
   Factory AI 揭示的新范式：选择 AI agent 角色 → 配对本地/远程 workspace → 系统自动 repo 扫描并生成 Todo List。传统 API 工具无此步骤，AI 原生开发者工具需要独立设计此 IA 层。

---

## Canonical Flows

> 以下 flow 基于对真实产品的横向分析抽象而来，代表该场景的高频用户任务。

### Flow 1: 注册并生成首个 API Key

**在此场景的特殊性**: Key 生成页面是一次性可见的安全仪式，不是普通的表单提交成功页面；代码示例需要在 key 生成后实时内联注入。

**前置条件**: 邮箱地址有效且可接收验证邮件；用户未持有现有账号（否则跳转登录）
**若前置条件不满足**: 邮箱已注册 → inline 提示「Account already exists」+ 登录链接；邮箱验证超时 → Resend 链接重新发送

**Entry**: 未登录用户访问开发者主页或 Pricing 页，点击「Sign up / Get started free」

**Screens**:

```
Screen 1: 账号创建入口
  主操作: 输入邮箱 + 密码，或选择 SSO（GitHub / Google）
  关键组件: Email input（with inline validation）, Password input, SSO provider buttons, CTA「Continue」
  → 成功: Screen 2
  → 已有账号: Login 页面

Screen 2: 邮箱验证等待
  主操作: 等待验证邮件，点击邮件链接确认
  关键组件: 状态提示卡（「Check your inbox for yiting@…」）, Resend email 文字链, 进度状态 badge
  → 成功: Screen 3（自动跳转）

Screen 3: 基本信息补充（轻量）
  主操作: 填写姓名、选择使用场景
  关键组件: Name field, Use-case chips（Personal / Team / Enterprise）, Skip 链接
  → 成功: Screen 4
  → Skip: Screen 4

Screen 4: 创建 Project + 命名 API Key
  主操作: 输入 project 名和 key 名称，点击「Generate API Key」
  关键组件: Project name input, Key name input（optional description）, Primary CTA「Generate API Key」
  → 成功: Screen 5

Screen 5: API Key 一次性展示（核心屏幕）
  主操作: 复制 key，切换语言 Tab 查看集成代码
  关键组件:
    - 警告 Banner（「This key will only be shown once. Copy it now.」）
    - Key display field（遮罩 + 「Show / Copy」按钮）
    - 代码示例区（Tab: curl / Python / Node / TypeScript）
    - 代码内联预填 key（Bearer sk-xxx）
    - CTA「Continue to Dashboard」
  → 成功: Screen 6
  → 未复制离开: 确认 Dialog（「Did you copy your API key?」）

Screen 6: 下一步引导卡片
  主操作: 选择下一步：查看文档 / 添加信用卡 / 邀请团队成员
  关键组件: Next steps card list（图标 + 标题 + 描述 + CTA），「Go to Dashboard」主按钮
  → 成功: Dashboard（exit state）
```

**Exit State**: 开发者进入 Dashboard，Sidebar 显示已创建的 project，key 状态为 Active，Usage = 0/限额  
**Empty State**: 首次创建前 API Keys 列表为空，显示 empty state + 「Create your first API key」CTA

---

### Flow 2: Quickstart — 发起首次 API 调用

**在此场景的特殊性**: Quickstart 是 activation gate，Step 2（执行请求）被 key 的存在与否硬性 gate 住；成功的判定标准是真实的 API 响应，不是表单提交。

**前置条件**: 已登录；账号下有至少一个 Active API Key；未超过当前套餐的免费调用配额
**若前置条件不满足**: 无 API Key → Step 1 未完成，Quickstart 引导创建 Key；配额耗尽 → Step 2 执行请求返回 429 错误 + Upgrade 提示

**Entry**: 已登录新用户首次进入系统自动跳转，或从左侧 sidebar「Quickstart」入口进入

**Screens**:

```
Screen 1: Quickstart 概览页
  主操作: 查看任务步进列表，识别当前阻塞步骤
  关键组件:
    - 步进卡片列表（Step 1: Create API Key ✅ / Step 2: Send first request ⬜）
    - 每个步骤的状态 badge（Completed / Pending / Locked）
    - 左侧 sidebar「Quickstart」高亮当前位置
  → 成功: Screen 2（点击 Step 2）
  → Step 1 未完成: Step 1 卡片展开，引导创建 key

Screen 2: API Key 创建 + 代码注入
  主操作: 点击「Add API Key」→ key 生成后自动内联到代码 snippet
  关键组件:
    - 「Add API Key」CTA（gate 住 Step 2 的执行按钮）
    - Key 显示区（mask + copy）
    - 多语言代码 Tab（实时 key 内联更新）
    - Step 2 执行 CTA（灰色 → 蓝色，key 创建后激活）
  → 成功: Screen 3

Screen 3: 执行测试请求 + 成功确认
  主操作: 点击「Send / Run」触发真实 API 请求
  关键组件:
    - Primary CTA「Send email / Run API call」（激活状态）
    - 成功 Toast / Success Banner（「🎉 Request successful! Status: 200」）
    - 响应 JSON 预览区（折叠展示）
    - Next Steps 卡片（Add domain / Invite team / View API reference）
  → 成功: exit state
  → API 错误: 错误码 + 错误说明 inline（「Error 401: Invalid API key」），附修复提示
```

**Exit State**: Quickstart 全部步骤标记为 completed，引导进入下一配置（域名、Webhook、生产环境 key）  
**Empty State**: N/A（Quickstart 为线性向导，无空状态）

---

### Flow 3: 使用 Playground 探索 API 并调试请求

**在此场景的特殊性**: Playground 是三栏布局的全屏工作台，不可简化为单页面表单；左侧 schema explorer 是必要组件，承担文档与调试的桥接。

**前置条件**: 已登录；具有 Owner 或 Developer 角色（Viewer 无 Playground 执行权限）；账号下有可用 API Key
**若前置条件不满足**: 无 API Key → Playground 执行按钮 disabled + 提示「Create an API key first」；Viewer 角色 → Playground 只读模式（可查看但不可执行）

**Entry**: 已登录开发者点击 TopBar「Playground」或从 API Ref 文档页点击「Try it」按钮

**Screens**:

```
Screen 1: 文档首页（左侧 Sidebar 树形导航）
  主操作: 展开文档树，找到目标 endpoint 或 guide
  关键组件:
    - 左侧 Tree sidebar（折叠分组：Getting Started / Authentication / Endpoints / Models / Changelog）
    - 顶部全文搜索 input（Command+K 触发）
    - 主内容区：文章正文 + 内联代码块 + Copy 按钮
    - 右侧 TOC（页内锚点，浮动）
  → 成功: Screen 2（点击具体 endpoint）

Screen 2: Endpoint 文档页（两栏布局）
  主操作: 阅读参数说明，查看 Request/Response 结构，点击「Try it in Playground」
  关键组件:
    - 左栏：Parameter 表格（name / type / required / description）, HTTP method badge（GET/POST/PUT）
    - 右栏：代码 Tab（curl / Python / Node）+ Copy 按钮，Response Schema 示例（JSON 高亮）
    - CTA「Try it in Playground」（→ Screen 3）
  → 成功: Screen 3
  → 继续浏览: Screen 1（sidebar 导航）

Screen 3: API Playground（三栏工作台）
  主操作: 构造请求参数，点击「Run / Execute」，验证响应是否符合预期
  关键组件:
    - 左栏 Schema Explorer：checkbox 选择 fields，搜索 type，折叠分组
    - 中央 Query/Prompt Editor：语法高亮，行号，自动补全，Endpoint selector（下拉），Variables Tab / Headers Tab
    - 右栏 Response Panel：JSON 高亮显示，HTTP 状态码 badge（200 / 400 / 500），响应时间，Copy response 按钮
    - 顶部：Endpoint URL bar + 「Run / Execute」CTA（Primary）+ 保存 snippet 链接
  → 成功: exit state
  → API 错误: 右栏显示错误 JSON + 状态码 badge（红色），不中断编辑状态
```

**Exit State**: 开发者验证了接口行为，可点击「Copy code」将调试完成的代码片段带入自己的项目  
**Empty State**: Playground 初始状态：中央 editor 显示示例 query/prompt 占位内容，右栏显示「Run a request to see the response」

---

---

### Flow 4: API Key 轮换与撤销

**在此场景的特殊性**: API Key 的安全生命周期管理是开发者工具场景特有的高频运维任务——Key 泄露、权限变更、定期轮换都会触发此 flow。与普通 SaaS 设置修改不同，Key 撤销是立即生效的不可逆操作（所有使用该 Key 的集成即刻断连），因此必须有 AlertDialog 强制确认并说明后果。轮换流程通常是「先创建新 Key → 更新集成配置 → 再撤销旧 Key」的三步式，而非直接替换（Linear flow_id 6692 / OpenAI flow_id 4226 / Factory AI flow_id 7761 均验证了此模式）。

**行业共识**: 出现在 Linear（flow_id 6692）、OpenAI（flow_id 4226）、Factory AI（flow_id 7761）等多个开发者工具样本中。

**前置条件**: 当前用户为 Owner 角色（Member/Developer 可创建 Key 但通常无法撤销他人 Key）；当前账号下有至少一个 Active API Key
**若前置条件不满足**: Member 角色 → [Revoke] 按钮不显示或 disabled + Tooltip「需要 Owner 权限」；无 Active Key → 列表空状态，仅显示 [+ Create key]

**Entry**: Settings → API Keys（或 Sidebar → Projects → API Keys）

```text
Screen 1: API Keys 列表
  主操作: 查看现有 Key 列表，决定新建或撤销
  关键组件:
    - 列表表格（列：Name / Secret（遮罩）/ Created / Last used / Permissions / [···]）
    - 每行行操作「[···]」菜单: Edit name / Revoke
    - 右上角「+ Create key」主 CTA
    - Key 状态（Active 绿色 Badge；过期/已撤销则不在列表或显示 Revoked 灰色）
  → 点击「+ Create key」: Screen 2（创建新 Key）
  → 点击行「[···]」→「Revoke」: Screen 4（撤销确认）

Screen 2: 创建 API Key Dialog
  主操作: 命名新 Key（可选），点击「Create secret key」
  关键组件:
    - Dialog 标题:「Create new secret key」
    - Name input（可选，不填则自动命名「Secret key [N]」）
    - Permissions 选择（如有：All / Read only / Custom）
    - [Cancel]（ghost）/ [Create secret key]（primary）
  → 点击「Create secret key」: Screen 3（Key 一次性展示）
  → 点击 Cancel: 关闭 Dialog，回到 Screen 1

Screen 3: API Key 一次性展示
  主操作: 复制新 Key，确认已保存
  关键组件:
    - 警告 Banner（红色或橙色）:「Save your secret key now — it won't be shown again」
    - Key 展示区: 遮罩显示 + [Show]（揭示完整值）+ [Copy]（复制 + Toast「Copied!」）
    - 主 CTA:「Done / I've copied my key」（确认后关闭，回到 Screen 1）
    - 点击「Done」前若未点击 Copy → 确认 Dialog「Did you copy your API key? This is your only chance.」
  → 点击「Done（已复制）」: 关闭，Screen 1 列表追加新 Key 行（Active，Last used: Never）
  → 离开页面前未确认: 浏览器 beforeunload 提示「Changes you made may not be saved」

Screen 4: Revoke Key 确认 AlertDialog
  主操作: 确认撤销旧 Key
  关键组件:
    - AlertDialog 标题:「Revoke "[Key Name]"?」
    - 警告文案:「Any application using this key will lose access immediately. This action cannot be undone.」
    - [Cancel]（返回 Screen 1，Key 保留）/ [Revoke key]（危险色，红色或 destructive）
  → 点击「Revoke key」: Key 从列表移除 → Toast「API key revoked successfully」→ 回到 Screen 1
  → 点击 Cancel: 关闭 AlertDialog，Key 保留，回到 Screen 1
```

**Exit State**:

- ✅ 新 Key 创建：Key 出现在列表，Last used「Never」，Secret 永久遮罩
- ✅ 旧 Key 撤销：列表移除该行（或变为 Revoked 灰色态），Toast 确认，使用该 Key 的集成立即失效
- ↩ 操作取消：任意步骤 Cancel 回到 API Keys 列表，无变更

---

## Component Kit

按使用频率排序，标注用途：

| 功能概念 | 具体用途 |
|---|---|
| 标签页切换 | Playground 语言切换（curl/Python/Node）、文档子导航 |
| 模态对话框 + 危险操作确认 | API Key 生成确认、删除 Key 二次确认、邀请团队弹窗 |
| 单行文本输入 | 注册表单、Key 命名、搜索框 |
| 操作按钮 | 主 CTA（Generate Key、Run、Send）、次 CTA（Skip、Resend）|
| 状态标签 | Key 状态（Active/Revoked）、HTTP 方法（GET/POST）、状态码 |
| 内容卡片 | Quickstart 步进卡片、Next Steps 引导卡片、用量统计卡 |
| 操作通知（Toast）| API 调用成功/失败确认、Key 复制成功反馈 |
| 页面级警告横幅 | API Key 一次性可见警告 Banner、Key 将过期提醒 |
| 进度条 | Quickstart 完成进度（步骤数/总步骤数）|
| 基础数据表格 | API Keys 列表（Name / Created / Last used / Status）、Usage 明细 |
| 选择下拉 | Playground endpoint 选择器、模型选择器、区域选择 |
| 分隔线 | Sidebar 分组分割线、Docs 页面 section 分隔 |
| 多行文本输入 | Playground 中央 Query/Prompt 编辑器基础结构 |
| 可滚动区域 | Playground 左侧 Schema Explorer、长文档页面 |
| 气泡提示 | Key 遮罩时的 hover 提示（「Click to reveal」）、参数说明 |

---

## Anti-Patterns

> 该场景中真实存在的常见设计错误，基于研究观察。

- **把 API Key 做成普通表单成功页面**：显示为普通的 input field 并允许随时查看，丢失安全语义 → 应使用遮罩 + 警告 Banner + 一次性可见的仪式感设计，强制用户意识到 key 的权限重量

- **Quickstart 做成可选的 tooltip 引导**：用气泡引导覆盖在 Dashboard 上，用户可随时关闭，无法传达 activation 的紧迫性 → 应作为独立页面，用步进卡片 gate 住流程，直到首次 API 调用成功

- **代码示例不内联 key，只写 YOUR_API_KEY 占位符**：用户需要额外复制粘贴才能运行 snippet，引入不必要的摩擦 → Key 生成后应自动内联填入所有代码示例，降低 time-to-first-success

- **Playground 简化为单列表单**：把参数做成一个竖向表单，去掉 response 面板 → 开发者无法同时看到请求构造和响应结果，破坏 Learn → Write → Test 核心循环，应坚持三栏布局

- **文档和 Playground 分属两个独立产品**：文档是静态网站，Playground 是另一个域名，之间没有「Try it」跳转 → 两者应深度集成，文档中的每个 endpoint 应有直接进入 Playground 的入口
