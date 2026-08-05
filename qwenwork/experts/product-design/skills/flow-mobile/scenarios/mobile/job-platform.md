# Scenario: Mobile Job Platform（求职平台）

> **研究来源**：基于对 LinkedIn iOS、Indeed 等真实产品的横向分析抽象，不代表任何单一产品的具体实现。

---

## Identity

**Platform**: Mobile (H5 / React Native)
**Definition**: Consumer-facing Mobile App for job seekers to search, filter, and apply for positions, featuring a job search experience, quick apply flows, and application status tracking.

**Canonical Examples**: LinkedIn（专业人脉 + 移动端求职）、Indeed（海量职位搜索）、Glassdoor（职位 + 公司评价）

**Not this scenario if**: 产品是企业 HR 管理后台；产品是自由职业接单平台（改用 mobile/marketplace）；产品是内部员工管理（改用 web/internal-ops）。

---

## User Profile

| 维度 | 内容 |
|---|---|
| **主要角色** | Job Seeker（求职者，主要用户）；Recruiter / Employer（次要角色，通常有独立后台）|
| **核心目标** | 找到匹配职位 → 了解岗位详情 → 快速投递 → 追踪申请状态 |
| **心智模型** | 熟悉 LinkedIn 模式：搜索 + 筛选 + 职位卡片；对「投了多少岗位、是否被查看」有追踪需求 |
| **使用频率** | 阶段性高频（求职期每天使用）；会话 15~30 分钟 |
| **决策模式** | 比较驱动型：对比多岗位 → 收藏感兴趣 → 精选投递；非即时决策 |
| **容错期望** | 中：投递须有明确确认反馈；长申请表单需要草稿保存 |

---

## IA Template

**导航模式**: Bottom Tab Bar 5 Tab（Home / My Network / Post / Notifications / Jobs）或简化版（Search / Jobs / Alerts / Profile）

- **Jobs Tab（核心）**：搜索框 + 筛选条件 + 职位卡片列表 + My Jobs 追踪
- **Job Detail**：页面导航 push，全屏展示职位详情（职责 / 要求 / 公司简介），底部固定 Apply CTA
- **Apply Flow**：Easy Apply ≤ 3 步（Bottom Sheet Large，保留职位背景可见）；Full Application 独立页面
- **My Jobs Tab**：申请状态追踪（Saved / Applied / Viewed / Interview / Offer/Rejected）

**页面层级**: 3 级
```
L1: Jobs Home（搜索 + 职位列表）
L2: Job Detail（职位详情页）
L3: Easy Apply Sheet / Full Application Form + My Jobs Dashboard
```

**权限角色结构**:
```
Guest（未登录）   → 可浏览职位，无法申请或收藏（触发登录 Modal）
Registered User → 完整申请 + 收藏 + 追踪状态 + 上传简历
Premium / Pro   → 直接消息招聘方 + 谁看了我 + 额外简历曝光（订阅付费）
```

**数据密度**: 中
- 职位列表：紧凑型卡片（公司 Logo + 职位名 + 公司名 + 地点 + 薪资 + 时间 + 申请人数）
- 职位详情：段落式（职责 / 要求 / 福利 / 公司简介），关键指标首屏可见
- 筛选：Bottom Sheet（Job Type / Location / Date Posted / Experience Level）

**主要容器模式**:
| 场景 | 容器 |
|---|---|
| Easy Apply 表单（≤ 3 步）| Bottom Sheet（Large，保留职位背景） |
| Full Application（长表单）| 独立全屏页面 |
| 高级筛选 | Bottom Sheet（Medium / Large）|
| 收藏职位 | Toast 确认（无 Modal，操作即时）|
| 登录/注册（申请时触发）| Bottom Sheet 或 Full-screen Modal（保留当前职位上下文）|
| Premium Paywall | Bottom Sheet（应用内订阅购买）|

**Tab Bar 骨架图（ASCII）**:
```
┌─────────────────────────────────────────┐
│  < Jobs             [My Jobs] [Settings] │  ← Navigation Bar
├─────────────────────────────────────────┤
│  [🔍 Job title, keywords_____________]  │  ← Search Bar
│  [📍 Location____] [Filters ▾]          │
│  ──────────────────────────────────────  │
│  Active Filters: [Remote ×] [Full-time ×]│
│  ──────────────────────────────────────  │
│  ┌──────────────────────────────────┐   │
│  │  [Amazon Logo]                    │   │
│  │  Store Manager, Amazon Fresh      │   │
│  │  Amazon · Seattle, WA · Hybrid    │   │
│  │  $85K–120K · 2d ago · 847 applied │   │
│  │  [♡ Save]              [Apply →] │   │
│  └──────────────────────────────────┘   │
│  ┌──────────────────────────────────┐   │
│  │  [Google Logo]                    │   │
│  │  Product Designer                 │   │
│  │  Google · Remote                  │   │
│  └──────────────────────────────────┘   │
├─────────────────────────────────────────┤
│  Home  Network  Post  Notif.  Jobs(●)   │  ← TabBar
└─────────────────────────────────────────┘
```

---

## 该场景独有的 IA/UX 决策

1. **职位详情必须完全公开可浏览，登录门槛只能设在「操作」时** — 移动端求职者在决定投递前需要完整评估岗位（职责 / 要求 / 薪资 / 公司文化），强制登录 gate 会在用户最脆弱的探索阶段造成摩擦，导致大量跳失。移动端的正确模式是：职位详情页全程无需登录，只有用户点击「Apply」或「Save」时才触发登录 Bottom Sheet（保留当前职位 Context，登录完成后自动继续操作）。与 edtech 的 Paywall 模式（先展示内容价值再付费）机制相同：用用户「已经感兴趣的内容」作为登录动机，而非强制先登录才能看到内容。

2. **「Easy Apply」与「Full Application」必须在职位卡片层就有明确区分，不能进入 Sheet 后才告知用户** — 求职者在浏览职位列表时就需要做「快速投递 vs 精心准备」的策略决定。职位卡片上必须用 Badge 明确标注（「Easy Apply」徽章 vs 无徽章），职位详情的底部 CTA 也须区分（「Easy Apply」→ Bottom Sheet Large 3 步以内 vs「Apply on Company Site」→ 外部浏览器跳转）。如果用户进入投递流程后才发现需要填写 12 个字段，等同于被欺骗，会极大损害信任感和下次再投的意愿。

3. **Easy Apply Sheet 必须在整个 Bottom Sheet Large 流程中保持职位摘要可见** — 用户在填写多步表单时，需要随时参照「自己在申请什么岗位」——特别是当 Step 2 有 Screening Questions 时（如「您是否有 AWS 认证？」），上下文职位信息直接影响用户如何回答。Sheet Header 下方需始终保留职位摘要行（公司 Logo + 职位名，只读压缩形式），而非仅在第 1 步展示后隐藏。与设计工具的 Canvas + Bottom Sheet 必须保持工作区可见的原理相同：上下文丢失 = 用户决策依据丢失。

4. **My Jobs Status Timeline 的时效提示是求职者最高焦虑来源，必须主动推送而非被动查看** — 移动端求职行为有强烈的「不确定焦虑」特征——用户每天多次打开 App 只为查看「简历有没有被查看」。正确做法是双路径推送：① Push Notification（「Your application for [职位名] was viewed by the recruiter」）+ ② My Jobs Dashboard 实时 Timeline 更新（时效标注「Viewed 2 days ago」/ 「No response in 14 days — consider following up」）。仅依赖用户主动打开 App 查看而无推送 = 用户焦虑无法被缓解，形成「死刷 App」的负体验；仅有推送而 Dashboard 无详细 Timeline = 用户无法看到申请的完整历程上下文。

5. **移动端求职的「保存职位」必须是 Optimistic Update + Undo Toast，不能弹确认 Modal** — 求职者在浏览职位列表时会高频使用「保存」功能（先存后判断），这是一个低成本、高频率、可逆的操作。JobCard 上的 Heart/Bookmark 按钮必须即时响应（filled 图标立即变化），同时底部显示 Toast「Job saved · Undo」——与 reading-media 的 Bookmark 模式完全一致。弹出 Modal 确认（「确定要保存此职位？」）会把低成本操作变成高摩擦操作，导致用户宁愿不保存；而缺少 Undo 则让用户对误操作没有安全感。

---

## Canonical Flows

### Flow 1: 搜索 + 筛选职位（Search & Filter Jobs）

**在此场景的特殊性**: 移动端求职搜索以关键词 + 地点双输入为核心；筛选通过 Bottom Sheet 完成（而非独立筛选页）；结果即时更新，不需要点击「Search」；职位卡片信息密度高（Logo + 职位 + 公司 + 地点 + 薪资 + 时间 + 申请人数）；已申请职位需在卡片显示「Applied」Badge

**Entry**: 用户点击底部 Tab Bar「Jobs」，或从首页 Job Suggestions 进入

**Screens**:
```
Screen 1: Jobs Home（搜索 + 列表）
  主操作: 输入关键词搜索，浏览职位列表
  关键组件:
    - SearchBar（职位名 / 关键词，支持快速清空）
    - TextField（地点）
    - Active Filter Chips（Remote / Full-time / Senior 等，点击 × 删除）
    - Button「Filters」（展开 Sheet 1a）
    - 结果数量 Label（「1,247 jobs found」）
    - 虚拟化列表 of JobCard:
        公司 Logo + 职位名 + 公司名 + 地点 + 薪资 + 时间 + 申请数
        Badge「Easy Apply」（有则显示）/ Badge「Applied」（已投递则覆盖）
        Button「Save」（Heart 图标，即时 Optimistic Update）
    - Sort Picker（Relevance / Date / Salary）
  → 输入关键词或地点: 结果即时刷新（debounced）
  → 点击职位卡片: 页面导航 push → Screen 2（Job Detail）
  → 点击「Filters」: Bottom Sheet → Screen 1a
  → 点击 Save: 即时 filled，Toast「Job saved · Undo」

Screen 1a: Filters Sheet（筛选 Bottom Sheet）
  主操作: 设置筛选条件
  关键组件:
    - Sheet Header: 「Filters」+ Button「Reset」
    - CheckboxGroup（Job Type: Full-time / Part-time / Contract）
    - CheckboxGroup（Work Location: On-site / Remote / Hybrid）
    - RadioGroup（Date Posted: Any / Past Week / Past Month）
    - RadioGroup（Experience Level: Internship / Entry / Mid / Senior）
    - Slider（Salary Range）
    - Button「Show [N] jobs」（主 CTA，含命中数量）
  → 点击「Show [N] jobs」: Sheet dismiss，列表刷新，Filter Chips 更新
  → 向下滑动: Sheet dismiss（不保存筛选）
```

**Exit State**: 筛选条件以 Chip 形式显示在搜索框下方，用户可逐个删除
**Empty State**: 「No jobs match your filters」+ 操作建议（「Try Remote」「Expand Salary Range」）+ 空状态插图与引导

---

### Flow 2: 查看职位详情 + Easy Apply（Job Detail & Easy Apply）

**在此场景的特殊性**: 移动端求职的核心体验是「Look → Apply in under 3 steps」；职位详情页底部必须有持久固定的 Apply CTA（安全区域吸底）；Easy Apply 通过 Bottom Sheet Large 呈现（不离开职位上下文）；Resume 选择是 RadioGroup（选已有 / 上传新）；申请成功后职位卡片添加「Applied」Badge 并提供「Continue Browsing」和「More Like This」

**Entry**: 用户在搜索结果列表点击职位卡片

**Screens**:
```
Screen 1: Job Detail
  主操作: 浏览职位详情，决定是否申请
  布局: 全屏页面 + 底部安全区域固定 CTA Bar
  
  主要内容（滚动区域）:
    - 公司 Logo（大） + 职位名（大字体）+ 公司名 + 地点 + 薪资区间
    - Quick Stats 行：发布时间 / 申请人数 / 职位类型 Badge
    - 职位描述（About the Role / Responsibilities / Requirements）
    - 「Preferred Qualifications」折叠段落
    - 公司简介 Block（公司简介 + 规模 + 行业 + 成立年份 + 员工人数）
    - 福利待遇列表（Health / 401K / PTO / Remote）
    - Similar Jobs Carousel（底部）
  
  固定底部 CTA Bar（安全区域吸底）:
    - Button「Easy Apply」（主，品牌色填充）— 有 Easy Apply Badge 时
      或 Button「Apply on Company Site」（主）— 无 Easy Apply 时，点击跳外部浏览器
    - Button「Save」（Heart 图标，次要）
  
  关键组件:
    - Badge（「Actively recruiting」/ 「Easy Apply」/ 「Just posted」）
    - 展开/收起（「Read more」）
  → 点击「Easy Apply」: Bottom Sheet Large → Screen 2
  → 点击「Save」: 即时 Toast「Job saved · Undo」，Heart 图标变 filled
  → 未登录点击 Apply: Bottom Sheet → 登录/注册，完成后自动继续

Screen 2: Easy Apply Sheet（第 1 步 / 共 2-3 步）
  主操作: 确认简历并提交申请
  容器: Bottom Sheet Large，顶部职位摘要始终可见
  关键组件:
    - Sheet Header: 步骤指示（Step 1 of 2）+ Button「✕」关闭
    - 职位摘要（公司 Logo + 职位名 + 公司名，只读压缩行，常驻 Header 下方不消失）
    - Section「Resume」:
      - RadioGroup（「Use saved resume: [resume_name.pdf]」/ 「Upload new resume」）
      - 文件选择器（如选择 Upload new，支持 PDF/DOC）
    - Section「Contact Info」:
      - TextField（Phone Number，已有则预填）
      - TextField（Email，已有则预填）
    - Button「Next」（→ Screen 2b）
    - Button「Cancel」（ghost，关闭 Sheet）
  → 点击「Next」: Sheet 内页面切换 → Screen 2b

Screen 2b: Easy Apply Sheet（第 2 步：补充问题）
  主操作: 回答招聘方筛选问题，确认提交
  关键组件:
    - 步骤指示（Step 2 of 2）
    - Screening Questions（0-3 个，TextFields 或 RadioGroups）
    - TextArea「Cover letter (optional)」
    - Toggle「I consent to data processing」
    - Button「Submit Application」（主 CTA，disabled 直到必填项完成）
    - 提交中: Button loading 状态，表单 disabled
  → 点击「Submit Application」: Sheet 内切换 → Screen 3（确认）

Screen 3: Application Submitted（Sheet 内确认状态）
  主操作: 确认申请已发送
  关键组件:
    - Success Icon（绿色对勾图标）
    - 标题:「Application submitted!」
    - 摘要: 职位名 + 公司名 + 提交时间
    - 「What happens next」说明（「You'll hear back within X business days」）
    - Button「Track My Application」（主 CTA，跳转至 My Jobs）
    - Button「Continue Browsing」（ghost，关闭 Sheet 回到职位详情）
  Exit: Sheet 关闭，底部职位卡片出现「Applied」Badge
```

**Exit State**: 职位卡片标注「Applied」Badge；申请进入 My Jobs Dashboard；用户继续浏览
**Empty State**: 不适用

---

### Flow 3: 申请状态追踪（My Jobs & Application Status）

**在此场景的特殊性**: 移动端 My Jobs 是求职者的高频回访场景（平均每天多次查看状态）；状态更新必须双路径通知（Push Notification「Your application was viewed」+ My Jobs Dashboard Timeline 实时更新）；状态卡片需展示详细时效信息（「Viewed 2 days ago」/ 「No response in 14 days」）；支持滑动操作（左滑 Delete/Archive / 右滑查看职位）；空状态须引导回到 Job Search

**Entry**: Bottom Tab → My Jobs Tab（或从 Application 确认页「Track My Application」跳转）

**Screens**:
```
Screen 1: My Jobs Dashboard
  主操作: 查看所有申请和收藏的状态
  关键组件:
    - Tabs（Saved / Applied），默认 Applied Tab
    - 状态筛选 Tabs / SegmentedControl（All / Applied / Viewed / Interview / Decision）
    - ApplicationCard 列表（支持滑动操作）:
      - 公司 Logo + 职位名 + 公司名 + 地点
      - 状态 Badge（Applied / Viewed / Interview / Offer / Rejected）
      - 申请时间 + 最近更新
      - 时效提示（「Viewed 2 days ago」/ 「No response in 14 days」）
    - 左滑: Delete（警告色）/ Archive
    - 右滑: 快速 Message 或 View Job
    - 空状态（无申请）:
      title: 「No applications yet」
      description: 「Search and apply to jobs you're interested in」
      actions: Button「Search Jobs」
  → 点击 Application Card: 页面导航 push → Screen 2（申请详情）
  → 左滑 Delete: Dialog 确认（「Remove from My Jobs?」）

Screen 2: Application Detail
  主操作: 查看申请完整时间线和当前状态
  关键组件:
    - 职位摘要（Logo + 职位名 + 公司 + 申请时间）
    - Status Timeline（垂直步骤指示器）:
      - ✓ Applied（时间戳，绿色对勾）
      - ✓ Viewed（「Recruiter viewed your profile」+ 时间戳，绿色）
      - ○ Interview（Pending 灰色 / 有面试时显示: 日期 + 格式「Video / On-site」+ 加入日历 Button）
      - ○ Decision（Offer / Rejected，待定时为空圆圈）
    - 时效提示（Status 旁边）:「Viewed 2 days ago」/ 「No response in 14 days — consider following up」
    - 已提交材料摘要（简历文件名 + 上传时间）
    - Button「Withdraw Application」（destructive 红色文字按钮，Dialog 确认）
    - Link「View Job Posting」（返回职位详情，验证岗位是否仍在招募）
    - Banner（职位已关闭时）:「This job is no longer accepting applications」，黄色 Warning Banner
```

**Exit State**: 申请状态实时显示；用户可随时 Archive 或 Withdraw；已结束申请自动建议移入 Archived
**Empty State**: My Jobs 为空时：「Start your job search」+ Button「Find Jobs」

---

---

### Flow 4: Resume Upload & Profile Setup（简历上传 + 求职档案完善）

**在此场景的特殊性**: 求职平台的「Profile / 求职档案」是 Easy Apply 的数据来源——完整的档案让 Easy Apply 的简历和联系方式字段自动预填，不完整的档案则需要用户在每次申请时手动输入相同信息。因此「Profile 完善」不是可选流程，而是影响整个申请体验效率的关键路径。Mozi（flow_id 4159，5 屏）是工作经历 Modal Sheet 的标准实现：Edit Profile 列表（每行 Row → 点击进入编辑）→ Modal Sheet（Job title + Company 两个 TextField）→「+ Add more」动态添加多条工作经历 → Save 按钮在必填项空时保持 disabled。**简历上传**必须走系统 Files Picker（不是自定义选择器）——用户的简历 PDF 通常在 Files/iCloud Drive/邮件附件中，系统 Files Picker 天然整合了 Recents / iCloud / 邮件等入口（Trip Way flow_id 8456 + ElevenReader flow_id 8969 均确认了这套标准 iOS 文件导入模式）。**Profile Completion Progress Bar** 是求职平台特有的进度激励机制——「65% complete」+ 具体提示（「Add education to improve match quality by 30%」）让用户理解每个字段对求职的实际价值，而非泛泛的「完善你的资料」。

**行业共识**：LinkedIn iOS 档案编辑使用「List of sections → 点击进入编辑 Sheet」模式；工作经历 Sheet 中的「Add more」允许多条目（Mozi flow_id 4159 确认）；简历上传后 Easy Apply 自动使用最新简历（用户无需每次重新上传）。

**Entry**: Profile Tab → 点击「Complete Profile」Banner 或右上角「Edit」按钮

```
Screen 1: Profile 主页（求职档案概览）
  主操作: 查看当前档案完整度，点击各 Section 进入编辑
  布局: 全屏页面，Tab Bar 保持可见
  关键组件:
    - Profile Header（顶部 Card）:
        Avatar（80pt 圆形，右上角「📷 编辑」icon）+ 姓名 + 当前职位（如「Product Designer · Seeking New Opportunities」）+ 地点
    - Profile Completion Card（橙色/品牌色警示）:
        LinearProgressBar（如 65%）
        Text（「Your profile is 65% complete」）
        Text（「Add education to improve match quality」）— 当前最影响完整度的字段提示
    - 各 Section List（每行右侧显示「›」或已有数据摘要）:
        Section「Resume / 简历」:
            已有: 文件名（「Resume_2024.pdf」）+ 上传时间 + 右侧「Replace」Button
            无简历: Button("Upload Resume ↑"，主色，虚线边框 Card)
        Section「Work Experience / 工作经历」:
            每条: 职位名 + 公司 + 时间段（单行摘要）+ 右侧「›」
            Button「+ Add Experience」（最后一行）
        Section「Education / 教育经历」:
            结构同 Work Experience
        Section「Skills / 技能」:
            Tag 云预览（前 5 个技能 Tag + 「+N more」标注）+ 右侧「›」
        Section「About / 个人总结」:
            摘要（前 100 字截断）+ 右侧「›」
  → 点击「Upload Resume」/ 「Replace」: → Screen 2（简历上传）
  → 点击「Work Experience」行 或「+ Add Experience」: → Screen 3（工作经历编辑 Sheet）
  → 点击「Skills」: → Screen 4（技能编辑）

Screen 2: 简历上传
  主操作: 选择并上传简历文件
  容器: 首次点击「Upload Resume」→ Action Sheet 弹出（选择来源）；已有简历点「Replace」→ 同样触发 Action Sheet
  关键组件（Action Sheet）:
    - 选项「Choose from Files」（系统 Files Picker，推荐）
    - 选项「Scan Document」（相机扫描，需 Camera 权限）
    - 选项「Cancel」
  → 点击「Choose from Files」: iOS 系统 Files Picker 弹出（Recents / iCloud Drive / Other locations）
  → 用户选择 PDF 文件（单选，仅 PDF / DOC / DOCX）: 文件名 + 预览 → 右上角「Open」确认

  上传中（系统 Files Picker 关闭后）:
    - 当前页面（Screen 1 背景）保持可见
    - 顶部 Banner（或 Toast）: 「Uploading resume... 上传中」+ ProgressIndicator（线性）
    - Resume Section 行更新为 Skeleton Loading 态
  上传成功:
    - Toast「Resume uploaded · View」（可点击预览 PDF）
    - Resume Section 行即时更新: 新文件名 + 「Just now」时间 + 「Replace」按钮激活

Screen 3: 工作经历编辑（Add / Edit Work Experience）
  主操作: 添加或修改工作经历条目
  容器: Modal Sheet（Large）覆盖在 Profile 页上方
  关键组件:
    - Sheet Header: Button「Cancel」（左）+ 标题「Work Experience」（中）+ Button「Save」（右，必填项为空时 .disabled）
    - 工作经历条目区（支持多条）:
        每条条目（卡片形式）:
          TextField(「Job Title *」，必填，placeholder「e.g. Product Designer」)
          TextField(「Company *」，必填，placeholder「e.g. Google」)
          DatePicker 行（两个月份选择器，左「Start Date」右「End Date」）
          Checkbox「I currently work here」（勾选后 End Date 变为「Present」并禁用）
          RadioGroup 或 Selector（Employment Type: Full-time / Part-time / Contract / Freelance）
          TextArea(「Description（Optional）」，placeholder「Key responsibilities and achievements...」，最多 500 字)
          Button「− Remove Entry」（danger 色文字，右对齐，当该条目是唯一一条时隐藏此按钮）
        分隔线
    - Button「+ Add Another Position」（品牌色文字 + 图标，最多支持 10 条）
    - 底部操作: Button「Save」（主色，全宽，disabled 状态直到每条必填项已填）
  → 点击「Save」（所有必填项完成）: Sheet dismiss，Profile 页 Work Experience Section 即时更新摘要
  → 点击「Cancel」（有改动时）: Dialog（「Discard changes? You'll lose unsaved edits.」→「Discard」danger / 「Keep Editing」）
  → 点击「Cancel」（无改动时）: Sheet 直接 dismiss

Screen 4: 技能编辑
  主操作: 添加或删除技能标签
  容器: 独立页面（Stack Push）或 Modal Sheet（Large）
  关键组件:
    - NavigationBar: 「← 返回」+ 标题「Skills」+ Button「Done」（右上角，保存当前状态）
    - 已有技能（Tag Cloud 区域）:
        Tag 流式布局（每个 Tag: 技能名 + 右侧「×」删除按钮）
        点击「×」: 即时移除该 Tag（乐观更新）
    - 搜索添加区:
        TextField(「Search or add skills...」，焦点时键盘弹出）
        实时联想下拉（输入 ≥ 1 字时显示，最多 5 条建议）:
            每行: 技能名（如「Figma」/ 「User Research」/ 「React Native」）
            点击建议行: 添加为 Tag，TextInput 清空，继续下一条
        若联想无匹配: 提示「Add "[输入词]" as custom skill」→ 点击添加自定义技能
    - 技能数量 Counter:「X / 50 skills」（LinkedIn 类平台上限 50 技能）
  → 点击「Done」: 返回 Screen 1，Skills Section 即时更新 Tag 云预览
```

**Exit State**:

- ✅ 简历上传成功：Resume Section 显示新文件名 + 「Replace」，Profile Completion Progress 上升
- ✅ 工作经历保存：Work Section 显示摘要（「Product Designer at Google」）；Easy Apply Sheet 下次打开时简历字段自动预填新简历
- ✅ 技能保存：Skills Section Tag 云更新；Profile Completion 上升
- ❌ 上传失败（文件过大 / 格式不支持）：Toast「Upload failed · Supported formats: PDF, DOC, DOCX · Max 10MB」
- ↩ 放弃编辑（Sheet 内有改动点 Cancel）：Dialog 二次确认，防止误丢失

---

## Mobile Component Kit

按使用频率排序（基于研究样本观察）：

| 优先级 | 组件（H5 antd-mobile）| 组件（RN Gluestack/RN）| 具体用途 |
|---|---|---|---|
| ★★★ | `SwipeAction` + `List` | `SwipeableRow` + `FlatList` | 职位卡片列表（左滑 Delete/Archive，右滑快捷操作）|
| ★★★ | `Popup`（large）| `BottomSheet`（large）| Easy Apply 表单（Step 1-2-确认）；高级筛选 Filters |
| ★★★ | `Radio` + `RadioGroup` | `Radio` + `RadioGroup` | 简历选择（Use saved / Upload new）；Experience Level 筛选 |
| ★★★ | `Tabs` | `TabView` | My Jobs（Saved / Applied 切换）|
| ★★★ | `Toast` | `Toast` | 收藏成功（「Job saved · Undo」）；申请提交通知 |
| ★★ | `Badge` | `Badge` | 职位状态（Applied / New / Easy Apply）；申请状态（Viewed / Interview）|
| ★★ | `Dialog` | `AlertDialog` | 撤回申请确认 / 删除确认（不可逆操作）|
| ★★ | `Picker` / `Selector` | `Picker` | 导入文件（简历上传，PDF/DOC）|
| ★★ | `Steps` | `Stepper` | 申请时间线（Applied → Viewed → Interview → Decision）|
| ★ | `ErrorBlock` | `EmptyState` | 搜索无结果 / My Jobs 为空 Empty State |
| ★ | `Collapse` | `Accordion` | 职位描述「Read more」折叠展开 |

---

## Anti-Patterns

- **查看职位详情前强制登录（Login gate on job detail）**: 用户点击职位后被直接要求注册，无法先评估岗位是否合适 → 正确做法：职位详情完全公开可浏览，仅在「Apply」或「Save」时触发登录 Bottom Sheet（保留当前职位上下文，登录后自动继续）
- **申请表单无草稿保存（No draft save for long forms）**: Full Application 填到一半离开，重返时所有输入清空 → 正确做法：Full Application 自动保存草稿，My Jobs 列表显示「Continue application」状态卡片
- **无申请状态追踪（No application status tracking）**: 用户投递后完全无反馈，不知道是否被查看 → 正确做法：My Jobs Dashboard 展示完整 Status Timeline（Applied → Viewed → Interview → Decision），并标注时效提示
- **Easy Apply 超过 3 步（Easy Apply more than 3 steps）**: 「Easy Apply」名不副实，实际填写超过 3 屏内容 → 正确做法：Easy Apply 严格限制在 ≤3 步（Resume 选择 + 联系方式 + 可选 Screening Questions），超出字段必须显式标注「Full Application」而非 Easy Apply
- **职位卡片不区分 Easy Apply / Full Application（No badge distinction on card）**: 用户进入投递 Sheet 后才发现需要填写大量字段，感觉被误导 → 正确做法：职位卡片层必须通过「Easy Apply」Badge 明确区分两种投递路径；详情页底部 CTA 文案也须同步区分（「Easy Apply」vs「Apply on Company Site」），让用户在点击前就知道投递复杂度
- **申请状态变更无 Push Notification（No push notification for status updates）**: 用户只能主动打开 App 反复查看状态，形成「死刷」焦虑体验 → 正确做法：申请状态变更（Viewed / Interview 邀请 / Decision）必须同步发送 Push Notification，结合 My Jobs Dashboard 的实时 Timeline 形成「推送通知 + 主动查看」双路径，彻底消解求职者的不确定焦虑
