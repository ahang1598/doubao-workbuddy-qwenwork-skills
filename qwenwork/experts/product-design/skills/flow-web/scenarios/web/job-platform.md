# Scenario: Job Platform（招聘平台）

> **研究来源**：基于对 LinkedIn Jobs、Indeed、Peerlist、Contra、Teamtailor（多家企业招聘站）等真实产品 flow 的横向分析抽象，不代表任何单一产品的具体实现。

---

## Identity

**Platform**: Web
**Definition**: Consumer-facing web platform for job seekers to search, filter, and apply for positions, with a job detail + application flow, and optionally an application status tracking dashboard.

**Canonical Examples**: LinkedIn Jobs（专业人脉+求职）、Indeed（海量职位搜索）、Glassdoor（职位+公司评价）、Peerlist（技术人才求职）、Contra（自由职业者接单）

**Not this scenario if**: 产品是公司内部 ATS（面试官/HR 管理端）（改用 web/saas-management）；产品是人力资源 SaaS（员工管理/绩效/薪酬）（改用 web/internal-ops）；产品是自由职业服务市场（以项目/技能为搜索对象而非职位）（改用 web/ecommerce 变体）；产品是移动端原生 App（改用 ios/job-platform）。

---

## User Profile

| 维度 | 内容 |
|---|---|
| **主要角色** | Job Seeker（求职者，主要用户）；Recruiter / Employer（发布职位方，通常在独立招聘后台操作）|
| **核心目标** | 找到匹配的职位 → 了解详情（职责/薪酬/公司） → 快速投递申请 → 跟踪申请状态 |
| **心智模型** | 熟悉 LinkedIn 模式：搜索框 + 左侧筛选 + 双栏（列表+详情）；对「投了多少岗位」有追踪需求 |
| **使用频率** | 阶段性高频（求职期每天使用，稳定期低频）；每次会话 30~60 分钟 |
| **决策模式** | 比较驱动型：浏览多个职位对比 → 收藏 → 精选几个投递；非即时决策 |
| **容错期望** | 中：长申请表单需要保存草稿；投递后需明确确认；申请状态需持续可追踪 |

---

## IA Template

**导航模式**: Top Nav（搜索栏 + Logo + 用户入口）+ 双栏布局（左侧职位列表 + 右侧职位详情）

- **Top Nav**：Logo + 搜索框（职位名称）+ 地点输入 + 搜索按钮 + 用户头像（已投递/收藏/账户）
- **左侧职位列表**（~40%）：带筛选 Filter Bar + 可滚动职位卡片列表 + 分页
- **右侧职位详情**（~60%）：Sticky Panel，点击左侧卡片刷新右侧内容（不跳转页面）
- **底部固定 Apply CTA**（详情面右侧）：随页面滚动保持在视口底部

**页面层级**: 3 级
```
L1: Job Search Results（双栏：左列表 + 右详情，Search = 入口）
L2: Job Detail（右侧面板详情展开，或独立详情页）
L3: Application Form（Modal 或独立表单页）+ Applied Dashboard（申请追踪）
```

注：求职平台的核心体验是「搜索→浏览→对比→申请」，与 SaaS 的任务执行模式不同，更接近 E-commerce 的探索购买路径，但没有购物车，投递即终态。

**权限角色结构**:
```
Visitor（未登录）  → 浏览职位列表 + 查看部分详情，无法申请或收藏
Registered User → 完整申请 + 收藏 + 查看申请状态 + 上传简历
Premium / Pro   → 简历高亮 + 直接联系招聘方 + 薪酬洞察（平台变体）
```

**数据密度**: 中
- 左侧列表：紧凑型卡片（职位名 + 公司 + 地点 + 薪资 + 发布时间 + 申请状态 Badge）
- 右侧详情：段落式（职责描述 + 要求 + 公司简介 + 福利），含关键指标摘要块
- Filter Bar：Chip 或 DropdownMenu 组合

**主要容器模式**:
| 场景 | 容器 |
|---|---|
| 职位申请表单（≤5字段，Quick Apply）| Dialog（全屏或中等 Modal）|
| 职位申请表单（>5字段，Full Application）| 独立页面（不覆盖详情）|
| 收藏/保存职位 | Toast 确认（无 Modal，操作即时）|
| 申请状态追踪 | 独立 Dashboard 页（Applied 列表）|
| 高级筛选 | Popover 或 Filter Sidebar 展开（不全页 Modal）|
| 登录/注册（申请时触发）| Modal（保留当前职位上下文）|

**导航骨架图（ASCII）**:
```
┌──────────────────────────────────────────────────────────────────┐
│  Logo  [🔍 Job title, keyword___] [📍 Location___]  [Search]  [☰]│
├───────────────────────┬──────────────────────────────────────────┤
│  Sort: Relevance ▾    │                                          │
│  Filter: [Remote ×] [Full-time ×] [More ▾]   1,247 jobs         │
├───────────────────────┤  Senior Product Designer                 │
│  ●  Senior Product    │  Figma · San Francisco, CA · Remote OK   │
│     Designer          │  $140K – $180K · Posted 2d ago           │
│     Figma · Remote    │  ──────────────────────────────────────  │
│     $140K–180K  2d ago│  About the Role                          │
│ ─────────────────── │  We're looking for a Senior Product...    │
│  ○  Lead UX Researcher│                                          │
│     Stripe · NYC      │  Requirements                            │
│     $130K–160K  1d ago│  · 5+ years product design experience    │
│ ─────────────────── │  · Proficient in Figma                    │
│  ○  Product Designer  │  · Experience with design systems        │
│     Notion · Remote   │                                          │
│     $120K–150K  3d ago│  ──────────────────────────────────────  │
│                       │  [ ♡ Save ]   [ Apply Now →  ]          │
│  [Load more]          │  (Sticky at bottom of right panel)       │
└───────────────────────┴──────────────────────────────────────────┘
```

---


### 图 2：关键状态对比图（Key State Variations）

```
左：Job Search Results 正常态（双栏视图，已选中职位，筛选条件激活）      右：My Applications 空状态（尚无任何申请记录）

┌────────────────────────────────────┐  ┌────────────────────────────────────┐
│ [Remote ×][Full-time ×][More ▾]    │  │  [全部] [Active] [Archived]        │
│ 1,247 jobs found   Sort: Relev ▾   │  ├────────────────────────────────────┤
├──────────────────────────────────  │  │                                    │
│ ● Senior Product Designer          │  │                                    │
│   Figma · Remote · $140K–180K 2d   │  │           📋                       │
│─────────────────────────────────   │  │                                    │
│ ○ Lead UX Researcher               │  │   You haven't applied to           │
│   Stripe · NYC · $130K–160K 1d     │  │   any jobs yet                     │
│─────────────────────────────────   │  │                                    │
│ ○ Product Designer                 │  │   [ Start Searching ]              │
│   Notion · Remote · $120K–150K 3d  │  │                                    │
│                          [Load more]│  │                                    │
│ ──── Detail Panel ──────────────── │  │                                    │
│ Senior Product Designer            │  │                                    │
│ Figma · SF, CA · Remote · $140–180K│  │                                    │
│    [ ♡ Save ]    [ Apply Now → ]   │  │                                    │
└────────────────────────────────────┘  └────────────────────────────────────┘
```

---

### 图 3：覆层层级图（Overlay Hierarchy）

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Logo  [🔍 Job title, keyword___] [📍 Location___]  [Search]  [头像 ▾]  │ ← Top Nav（z-100）
├───────────────────────┬──────────────────────────────────────────────────┤
│ [Remote ×][Full-time ×][More ▾] [🔔 Save search]  1,247 jobs            │
│ ──────────────────────┤                                                  │
│ ● Senior Product      │  Senior Product Designer                         │
│   Designer            │  Figma · San Francisco, CA · Remote OK           │
│   Figma · Remote      │  $140K – $180K · Posted 2d ago                  │
│   $140K–180K          │  ──────────────────────────────────────          │
│ ─────────────────── │  About the Role                                  │
│ ○ Lead UX Researcher  │  We're looking for a Senior Product...           │
│   Stripe · NYC        │                                                  │
│ ─────────────────── │  ┌──────────────────────────────────────────────┐│
│ ○ Product Designer    │  │  Quick Apply Modal  z-index: 300             ││
│   Notion · Remote     │  │  Senior Product Designer — Figma             ││
│                       │  │  ● Use saved resume  resume_2024.pdf         ││
│ ┌────────────────────┐│  │  ○ Upload new resume                         ││
│ │ More Filters       ││  │  ──────────────────────────────────          ││
│ │ z-index: 200       ││  │  Phone: +1 (415) ___-____                   ││
│ │ ─────────────────  ││  │  Cover letter (optional)                    ││
│ │ ☐ Full-time        ││  │  [ Drop file here / Browse ]                ││
│ │ ☑ Part-time        ││  │  ☐ I consent to data processing             ││
│ │ ☐ Contract         ││  │  [Back]      [Submit Application]           ││
│ │ Salary: $60K–200K  ││  └──────────────────────────────────────────────┘│
│ │ [Reset] [Apply 247]││    ▲ 触发: 右侧 Panel [Apply Now] 按钮             │
│ └────────────────────┘│                                                  │
│  ▲ 触发: [More ▾] 按钮 │  ┌──────────────────────────────────────────────┐│
│                       │  │  Login Modal  z-index: 350                   ││
│                       │  │  Sign in to apply                            ││
│                       │  │  [Continue with Google]                      ││
│                       │  │  ──────── or ────────                        ││
│                       │  │  Email ___________  Password __________      ││
│                       │  │  [Sign In]   [Create account]               ││
│                       │  └──────────────────────────────────────────────┘│
│                       │    ▲ 触发: 未登录点击 [Apply Now] 或 [♡ Save]      │
│                       │                                                  │
│                       │  ┌──────────────────────────────────────────────┐│
│                       │  │  Withdraw AlertDialog  z-index: 400           ││
│                       │  │  Withdraw your application?                  ││
│                       │  │  This action cannot be undone.               ││
│                       │  │  [Cancel]   [Withdraw Application]（红色）    ││
│                       │  └──────────────────────────────────────────────┘│
│                       │    ▲ 触发: My Applications → 卡片菜单 → 撤回申请   │
└───────────────────────┴──────────────────────────────────────────────────┘
  ┌──────────────────────────────────────────────────────────────┐
  │  ✓ Job saved   [View Saved Jobs]   [Undo]   [×]              │  ← Toast（z-500）
  └──────────────────────────────────────────────────────────────┘

触发关系说明:
- More Filters Popover（左侧浮出）: Filter Bar [More ▾] 触发，z-200，背景列表仍可见，无遮罩层，允许同时看到结果数量变化
- Quick Apply Modal（中）: 右侧 Panel [Apply Now] 触发，z-300，全屏覆盖（含左侧列表），确保申请表单有充足填写空间
- Login Modal（中）: 未登录点击 [Apply Now] / [♡ Save] 触发，z-350，登录完成后自动继续原操作（不丢失职位上下文）
- Withdraw AlertDialog（中）: My Applications → 卡片操作菜单 → 撤回申请触发，z-400，不可逆操作强制二次确认
- Toast（底部左侧）: 收藏、归档申请、保存搜索等操作成功反馈，z-500，3-5 秒消失，含 Undo 操作
```

---

## 该场景独有的 IA/UX 决策

1. **双栏 Master-Detail 布局是 Web 求职平台的核心 IA 约束** — LinkedIn Jobs、Indeed、Netflix Jobs 均采用左侧职位列表（~40%）+ 右侧职位详情（~60%）同屏并存的布局，点击左侧卡片刷新右侧内容而不跳转页面。这让用户能在不丢失浏览上下文的情况下快速扫描、对比多个职位——这是求职场景的核心体验，与 E-commerce 的单列瀑布流完全不同。跳转到独立详情页意味着用户必须返回才能浏览下一个职位，打断「连续对比」的心流。

2. **Quick Apply vs Full Application 双路径必须在进入前明确区分** — 两者的用户承诺级别完全不同（1-3 步 vs 5-10 步），必须在 Apply CTA 区域就做出视觉区分（如双按钮：「Quick Apply」主 CTA + 「Full Application」次 CTA），而不是进入 Modal 后才发现是长表单。用户对「Quick Apply」的预期是≤3 分钟完成；若进了 Modal 才发现需要填写 8 个字段，产生的预期落差会直接导致表单放弃。

3. **简历上传必须支持拖放并保留已有档案** — Web 申请表单中「找到并上传简历」是首要摩擦点。Drag & Drop 区域让用户从桌面直接拖入，并排的 RadioGroup 选项（「Use saved resume」已有档案 / 「Upload new」上传新）避免每次重新上传。已有档案时默认选中「Use saved」，新用户看到空的 Drop Zone——这两种状态需要独立设计，不能用同一个 UI 处理。

4. **Sticky Apply CTA 是长职位描述中不可或缺的转化保障** — 职位描述通常 800-1500 字（职责 / 要求 / 公司简介 / 福利），用户需要读完才能决定申请。Apply CTA 必须 Sticky 固定在右侧 Panel 底部，在整个阅读过程中始终可见。与 E-commerce 的「加购」不同，求职「Apply」有唯一的高决策时刻（阅读完后），必须在那个时机触手可及。

5. **申请状态 Timeline 是平台留存的核心回访钩子** — 求职者投递后会高频回访查看状态（「有没有被看到？」「进面试了没？」），My Applications Dashboard 是这一行为的载体。Timeline（Applied → Viewed → Interview → Decision）配合时效提示（「No response in 14 days」）让用户理解当前阶段，避免「石沉大海」的体验——这直接影响用户是否愿意再次使用该平台投递。与 E-commerce 的「查看订单」（结果确定）不同，申请 Timeline 的每个节点都伴随着不确定性，设计必须传递「平台在帮你跟踪」的感知。

---

## Canonical Flows

### Flow 1: 搜索 + 过滤职位（Search & Filter Jobs）

**在此场景的特殊性**: 与 E-commerce 商品搜索不同，职位搜索的核心维度是「地点」+「工作类型（远程/现场）」+「薪资区间」+「发布时间」；筛选条件改变后列表即时刷新（无需「搜索」按钮），左侧列表和右侧详情同屏并存（点击卡片刷新右侧，不跳转）；空状态需给出明确的调整建议，不能只显示「No results」

**前置条件**: 无前置条件（匿名用户可访问职位搜索功能）；浏览器可正常加载搜索结果页
**若前置条件不满足**: 搜索词匹配零结果 → 空状态 + 建议调整筛选（「No jobs match your filters」+ 调整建议 CTA）；网络错误 → 搜索结果区显示错误提示 + 重试按钮；地理位置不可用 → 地点字段留空，筛选功能不受影响

**Entry**: 用户在 Top Nav 搜索框输入职位名称/关键词后回车，或从首页「Browse Jobs」进入

**Screens**:
```
Screen 1: Job Search Results（双栏视图）
  主操作: 浏览职位列表，调整筛选条件，点击职位查看详情
  关键组件:
    - Filter Chips（Active 状态显示已选筛选，点击 × 删除）: Remote, Full-time, $100K+, Engineering, etc.
    - Button「More Filters」（展开 Filter Popover）
    - Select「Sort by」（Relevance / Date Posted / Salary）
    - 结果数量（「1,247 jobs found」，筛选后实时更新）
    - 左侧职位卡片列表: JobCard（职位名 + 公司名 + 地点 + 薪资区间 + 发布时间 + [已申请] Badge）
    - 右侧详情 Panel: 初始状态显示首位职位详情，点击卡片切换（不跳转页面）
    - Button「Load More」（列表底部，追加加载下一页）
  → 改变筛选条件: 列表即时刷新，右侧详情重置为新列表的首位
  → 点击职位卡片: 右侧详情 Panel 切换为该职位（左侧卡片高亮）
  → 点击「More Filters」: 展开 Screen 1a（Filter Popover）

Screen 1a: More Filters Popover（浮层，不覆盖整页）
  主操作: 设置高级筛选条件
  关键组件:
    - CheckboxGroup（Job Type: Full-time / Part-time / Contract / Internship）
    - CheckboxGroup（Work Location: On-site / Hybrid / Remote）
    - Slider（Salary Range 双端）
    - Select（Experience Level: Entry / Mid / Senior / Director）
    - CheckboxGroup（Industry / Function）
    - Button「Apply Filters」（含命中数量）, Link「Reset」
  → 点击「Apply Filters」: Popover 关闭，职位列表刷新，Filter Chips 更新
```

**Exit State**: 筛选条件以 Active Filter Chip 形式持久显示，用户可逐个删除；右侧始终有一个职位详情可见（不为空）
**Empty State**: 筛选后无结果时：「No jobs match your filters」+ 建议操作按钮（「Try Remote」「Expand Salary Range」）+ 热门职位推荐 Carousel

---

### Flow 2: 查看职位详情 + 申请（Job Detail & Apply）

**在此场景的特殊性**: 职位详情页必须有 Sticky Apply CTA（随页面滚动固定在底部或右侧，随时可操作）；「Quick Apply」（已有档案时 ≤3步）和「Full Application」（长表单）是两个并行路径；申请表单用 Modal（不离开当前双栏视图）；文件上传（简历/Cover Letter）是 Drag & Drop，不跳转独立上传页；申请成功后职位卡片标注「Applied」Badge

**前置条件**: 用户已登录（未登录可查看职位详情，但申请和收藏操作需登录）；目标职位处于 Active 状态（未关闭/未截止）
**若前置条件不满足**: 未登录点击 Apply 或 Save → 触发登录/注册 Modal（保留当前职位上下文，登录后自动继续操作）；职位已关闭 → Apply CTA disabled + inline 提示「This position is no longer accepting applications」；档案简历未上传 → Quick Apply 内「Use saved resume」选项 disabled，需手动上传

**Entry**: 用户在搜索结果列表点击职位卡片，或右侧详情 Panel 点击「Apply Now」

**Screens**:
```
Screen 1: Job Detail Panel（搜索结果右侧 Panel 或独立详情页）
  主操作: 浏览职位详情，决定是否申请
  关键组件:
    - 职位标题（大字体）+ 公司名 + 地点 + 薪资区间 + 发布时间
    - 快捷标签 Badge Row（Remote / Full-time / Engineering / Senior）
    - 职位描述（About the Role / Responsibilities / Requirements / Nice to Have）
    - 公司简介 Block（公司规模 / 行业 / 成立年份 / 评分）
    - 福利待遇列表（Health / 401K / PTO / Remote OK）
    - Sticky Bottom CTA Bar: Button「Apply Now」（主，品牌色）+ Button「♡ Save」（次）
    - Link「Similar jobs」（同公司或同类职位横向卡片 Carousel）
  → 点击「Apply Now」: 打开 Screen 2（Application Modal）
  → 点击「Save / ♡」: Toast「Job saved」（未登录则触发登录 Modal）
  → 未登录点击 Apply: 触发登录/注册 Modal，完成后自动继续申请流程

Screen 2: Quick Apply Modal（已有档案的快速申请路径）
  主操作: 确认档案信息并提交申请
  关键组件:
    - Dialog（全屏 Modal，左侧职位摘要 + 右侧表单）
    - 简历选择: RadioGroup（「Use saved resume」已有 / 「Upload new」上传新）
    - Drag & Drop Upload Zone（PDF/DOC 文件拖放，含格式提示和大小限制）
    - Input（Contact Phone，如档案已有则预填）
    - Textarea「Cover letter（optional）」
    - CheckboxGroup「Screening Questions」（公司自定义问题，0-3个）
    - Checkbox「I consent to data processing」
    - Button「Submit Application」（主 CTA）, Button「Back」（ghost）
    → 提交中: Button loading 状态，表单 disabled
    → 提交成功: Screen 3

Screen 3: Application Submitted（Modal 内确认状态）
  主操作: 确认申请已发送，了解后续步骤
  关键组件:
    - Success Icon（勾）
    - 标题：「Application submitted!」
    - 摘要：职位名 + 公司名 + 提交时间
    - 「What's next」说明（「You'll hear back within [X] business days」或「Track your application in My Applications」）
    - Button「Track Application」（主 CTA，跳转至 Applied Dashboard）
    - Button「Continue Browsing」（ghost，关闭 Modal 回到搜索结果）
  Exit: Modal 关闭，左侧职位卡片出现「Applied」Badge
```

**Exit State**: 职位卡片显示「Applied」Badge；申请出现在 Applied Dashboard；用户回到双栏搜索视图继续浏览
**Empty State**: 不适用

---

### Flow 3: 申请状态追踪（Application Status Tracking）

**在此场景的特殊性**: 申请状态追踪是求职者的核心需求之一，直接影响平台留存（用户回来查看进度 = 高频回访场景）；状态流转是单向的（Applied → Viewed → Interview → Offer/Rejected）并非双向编辑；每条申请卡片需显示公司回应时间（「No response in 2 weeks」等时效提示）；允许求职者手动「Archive」已结束的申请（保持列表整洁）

**前置条件**: 用户已登录；账号中至少有 1 条已提交的申请记录（已通过 Flow 2 成功投递）
**若前置条件不满足**: 未登录访问 My Applications → 重定向至登录页，登录后自动进入 Dashboard；无申请记录 → Dashboard 显示空状态「You haven't applied to any jobs yet」+ Button「Start Searching」（不显示 Tabs 和状态筛选控件）

**Entry**: Top Nav「My Applications」入口，或申请确认页「Track Application」按钮

**Screens**:
```
Screen 1: Applied Jobs Dashboard
  主操作: 查看所有申请的状态
  关键组件:
    - Tabs（All / Active / Archived），默认 Active Tab（未结束的申请）
    - 状态筛选 ToggleGroup（All Status / Applied / Viewed / Interview / Offer / Rejected）
    - Application Card 列表:
      - 公司 Logo + 职位名 + 公司名 + 地点
      - 状态 Badge（Applied / Viewed / Interview Scheduled / Offer / Rejected）
      - 申请时间 + 最近更新时间
      - 时效提示（「Viewed 2 days ago」/ 「No response in 14 days」）
    - Card DropdownMenu（行操作：View Job / Archive / Withdraw Application）
    - Empty State（无申请时）: 「You haven't applied to any jobs yet」+ Button「Start Searching」
  → 点击 Application Card: 进入 Screen 2（申请详情）
  → 点击「Archive」: 卡片移入 Archived Tab，Toast 确认含「Undo」

Screen 2: Application Detail（右侧 Panel 或独立详情页）
  主操作: 查看该申请的完整时间线和当前状态
  关键组件:
    - 职位信息摘要（职位名 + 公司 + 申请时间）
    - Status Timeline（垂直步骤条）:
      - ✓ Applied（时间戳）
      - ✓ Viewed（「Recruiter viewed your profile」+时间戳，如有）
      - ○ Interview（「Pending」灰色，如有约面则显示时间 + 格式）
      - ○ Decision（Offer / Rejected，待定时为空）
    - 已提交材料摘要（简历文件名 + Cover Letter 摘要）
    - Button「Withdraw Application」（AlertDialog 确认）
    - Link「View Job Posting」（回到职位详情，确认岗位是否仍在招募）
```

**Exit State**: 申请状态实时显示；用户可随时归档或撤回；已结束申请（Offer/Rejected）自动建议移入 Archived
**Empty State**: Dashboard 无申请时：「Start your job search」+ 搜索入口 CTA

---

### Flow 4: 保存搜索与职位推送设置（Save Search & Job Alerts）

**在此场景的特殊性**: 「保存搜索」不是独立入口，而是在搜索结果页上下文中触发——用户刚完成一次有效搜索，「这批结果不错，我想持续关注」是转化率最高的触发时机。与 E-commerce 的「加入心愿单」不同：这里保存的是动态查询而非静态商品，平台需持续匹配并推送新结果。Wittl（flow_id 5364）展示的 Job Listing 创建流程的招聘方视角印证了求职方的 Alert 配置需求——双方均需「职位类型+地点+频率」维度。Alert 频率选项（即时/每日/每周）直接影响用户的推送体验和取消订阅率：即时推送适合积极求职者，每周汇总适合被动浏览者。

**行业共识**: LinkedIn Jobs、Indeed、Peerlist 均在搜索结果页提供「Save search / 🔔 Alert」入口，Alert 配置不超过 3 个字段（关键词确认 + 频率 + 邮箱），不跳转独立页面。

**前置条件**: 用户已登录（未登录点击「Save search」触发登录/注册 Modal）；已执行至少一次关键词搜索（Filter 条件可选追加）
**若前置条件不满足**: 未登录 → 点击「🔔 Save search」触发 Login Modal，登录完成后自动打开 Alert Setup Modal；搜索词为空（仅地点无关键词）→ Alert Setup Modal 内显示 Warning「Add keywords to get more targeted alerts」（非阻断，可继续保存）；已存在完全相同的搜索 Alert → Modal 内 inline 提示「You already have an alert for this search」+ 链接「Manage existing alert」

**Entry**: 用户在 Job Search Results 页点击 Filter Bar 右侧「🔔 Save search」按钮

```text
Screen 1: Job Search Results（Alert 触发点）
  主操作: 点击「🔔 Save search」触发 Alert Setup Modal
  关键组件:
    - Filter Bar 最右端: Button「🔔 Save search」（次要按钮，有搜索结果时高亮可点击）
    - 已有该搜索的 Alert 时: 按钮变为「🔔 Saved」（Filled Bell 图标，点击可进入管理态）
    - Top Nav 中「My Alerts」入口（直接进入 Screen 4 管理页）
  → 点击「🔔 Save search」（未登录）: 触发 Login Modal → 登录后自动进入 Screen 2
  → 点击「🔔 Save search」（已登录）: 打开 Screen 2（Alert Setup Modal）
  → 点击「🔔 Saved」（已保存）: 打开 Screen 2（Alert 编辑态，标题改为「Edit job alert」）

Screen 2: Job Alert Setup Modal（居中弹出）
  主操作: 确认搜索条件 + 设置推送频率 + 创建 Alert
  关键组件:
    - Modal 标题:「Create job alert」
    - 搜索条件预览区（只读展示，可跳回编辑）:
        「Senior Product Designer in San Francisco, CA」
        Active Filter Chips（Remote / Full-time / $100K+）
        Link「Edit search criteria」（关闭 Modal，返回搜索页调整条件）
    - 「Alert frequency」频率选择:
        RadioGroup:
          ● As jobs are posted（新职位即时推送，推荐，适合积极求职者）
          ○ Daily digest（每天早 8 点汇总，减少打扰）
          ○ Weekly summary（每周一次，适合被动浏览者）
    - 「Send to」邮箱输入框（预填当前账号邮箱，可修改）
    - Toggle「Also notify in-app」（站内铃铛通知，默认开启）
    - 底部: Button「Cancel」（ghost）+ Button「Create alert」（主 CTA）
  → 点击「Create alert」: 提交 → Screen 3（Toast 反馈 + Modal 关闭）
  → 点击「Cancel」: 关闭 Modal，返回 Screen 1（Bell 按钮保持未激活状态）

Screen 3: Alert 创建成功（停留在 Screen 1 搜索结果页）
  主操作: 确认 Alert 已设置，继续浏览搜索结果
  关键组件:
    - Toast（左下角）:「🔔 Job alert created · [Manage alerts]」（3-5 秒自动消失）
    - Filter Bar「🔔 Save search」按钮状态更新为「🔔 Saved」（Filled Bell，已激活）
    - Toast 副链接「Manage alerts」→ 跳转 Screen 4
  → 用户继续浏览: 保持在搜索结果页，Bell 图标已更新为「Saved」状态，提示已保存

Screen 4: My Job Alerts 管理页（独立页面）
  主操作: 查看、暂停、删除已有 Alert；调整推送频率
  关键组件:
    - 页面标题「Job Alerts」+ 说明「We'll notify you when new jobs match your searches.」
    - Alert 卡片列表（每条已保存搜索一张卡片）:
        - 搜索标题（关键词 + 地点 + 主要筛选 Filter Chips）
        - 频率 Badge（Instant / Daily / Weekly）
        - 最近推送状态（「Last sent 2h ago · 12 new jobs」/ 「No new jobs since creation」）
        - Toggle 开关（暂停 / 恢复该 Alert，即时生效）
        - Card 操作: Button「Edit」（打开 Screen 2 编辑态）/ Button「Delete」（AlertDialog 确认）
    - Empty State（无 Alert 时）:「No job alerts yet」+ Button「Go to Job Search」
    - Button「+ Create new alert」（右上角，回到 Job Search 页触发新一轮保存流程）
  → 点击 Toggle 暂停: Toggle 变灰 + Toast「Alert paused · Undo」
  → 点击「Delete」: AlertDialog「Delete this alert?」[Cancel] + [Delete]（红色）
  → 删除成功: Toast「Alert deleted」，卡片从列表移除
```

**Exit State**:

- ✅ Alert 创建成功：Bell 按钮显示「🔔 Saved」激活态；平台按选定频率将匹配新职位推送至邮箱 + 站内通知
- ✅ Alert 管理：用户可在 My Alerts 页随时暂停（Toggle）、调整频率（Edit）、删除
- ⚠ 无匹配新职位：按设定周期检查但不发送空邮件，跳过该推送周期直到下次有新匹配

**Empty State**: My Job Alerts 页无 Alert 时显示「No job alerts yet」+ 「Go to Job Search」CTA；不显示 Alert 卡片区域

---

## Component Kit

按使用频率排序：

| 功能概念 | 具体用途 |
|---|---|
| 内容卡片 | 职位卡片（左侧列表的基本单元：职位名/公司/薪资/时间/状态标签）|
| 状态标签 | 职位状态（Applied / New / Remote）；筛选条件标签；申请状态（Applied/Interview/Offer/Rejected）|
| 模态对话框 | Quick Apply Modal（申请表单，含文件上传 + 问题 + 确认）；登录/注册 Modal |
| 多选框 | 申请表单筛选问题；数据同意 Checkbox；筛选条件 CheckboxGroup |
| 标签页切换 | Applied Dashboard 状态分类（All / Active / Archived）；职位详情内容分区 |
| 选择下拉 | 排序选择（Relevance / Date / Salary）；Experience Level 筛选 |
| 范围滑块 | 薪资区间双端筛选（More Filters Popover 内）|
| 下拉操作菜单 | 申请卡片行操作（View / Archive / Withdraw）；Filter 排序下拉 |
| 操作通知（Toast）| 收藏/保存成功（「Job saved」+ Undo）；申请归档确认 |
| 危险操作确认 | 撤回申请的二次确认（不可逆操作）|
| 分步向导步骤指示 | 申请状态 Timeline（垂直步进，Applied → Viewed → Interview → Decision）|
| 单行文本输入 | 搜索框（职位名 + 地点）；申请表单字段 |

---

## Anti-Patterns

- **查看职位详情前强制注册（Login gate on job detail view）**: 用户点击职位后立即被要求注册，无法先判断岗位是否感兴趣 → 正确做法：职位详情完全公开可浏览，仅在「申请」或「收藏」操作时触发登录/注册 Modal（保留当前职位上下文）
- **申请表单无草稿保存（No draft save for long application forms）**: 用户填到一半离开，再回来表单清空 → 正确做法：长表单（>5字段）自动保存草稿，申请入口显示「Continue application」状态
- **无申请状态追踪（No application status tracking）**: 用户投递后无任何反馈，不知道被查看还是被忽略 → 正确做法：My Applications Dashboard 展示完整状态 Timeline（Applied → Viewed → Interview → Decision），并标注时效提示
- **职位列表和详情是两个独立页面（List and detail as separate routes）**: 用户点击列表职位跳转到新页面，浏览上下文丢失（无法快速切换对比多个职位）→ 正确做法：双栏布局（左列表 + 右详情），点击卡片刷新右侧内容，不跳转页面
- **Quick Apply 实际超过 3 步（Quick Apply more than 3 steps）**: 标注「Quick Apply」的申请实际有 8-10 个表单字段，与「快速」承诺产生强烈落差，导致高放弃率 → 正确做法：Quick Apply 严格限制在 ≤3 步（简历选择 + 联系方式 + 可选 Screening Questions）；超出字段的路径必须明确标注「Full Application」，在 Apply CTA 阶段就做出区分
- **申请成功后无后续引导（No next step after submission）**: 提交后只显示「Success」确认，无后续 CTA，用户直接离开，平台错失建立回访习惯的时机 → 正确做法：申请成功状态必须包含两个出口：「Track My Application」（主 CTA，引导建立回访习惯）+ 「Browse Similar Jobs」（次 CTA，继续探索漏斗）
