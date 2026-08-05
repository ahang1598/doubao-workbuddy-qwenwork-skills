# Scenario: 教育科技 / EdTech

## Identity

**Platform**: Web
**Definition**: 提供在线课程学习、互动练习与技能认证的教育平台，面向学生（B2C）和机构管理员（B2B），核心价值在于将学习进度可视化并通过游戏化机制维持长期参与。
**Canonical Examples**: Brilliant（交互课程）、Teachable（课程发布+证书管理）、Preply（语言测验+辅导）
**Not this scenario if**: 仅为企业内训工具（→ internal-ops）；以视频库为核心无互动练习（→ entertainment）；以招聘/技能评测为主而非学习过程（→ HR SaaS）

---

## User Profile

| 维度 | 内容 |
|---|---|
| 主要角色 | 学生（Learner）/ 课程管理员（Admin / Course Creator） |
| 核心目标 | 学生：按路径完成课时、积累技能、获取证书；管理员：监控学生进度、颁发/撤销证书、管理注册 |
| 心智模型 | 学生参照「游戏通关」（节点解锁、XP 奖励）；管理员参照「学籍管理系统」（学生档案 + CRUD 操作） |
| 使用频率 | 学生：高频日常（每日练习/课时）；管理员：偶尔使用（审核、颁证、运营活动） |
| 决策模式 | 学生：任务驱动（今天完成哪节课）；管理员：数据参考（查看进度后操作） |

---

## IA Template

**导航模式**: 双栏布局 — 左侧固定课程树/侧边栏（学生端）或管理侧边栏（管理端）+ 右侧主内容区；课时内切换为顶部进度条 + 全屏沉浸模式
**页面层级**: Dashboard → Course Map → Lesson Exercise → Feedback → Completion Summary（学生端）；Student Profile → Enrollment Table → Certificate Modal（管理端）
**权限角色**: 2 种：Learner（仅读取自己的进度和内容）/ Admin（读写所有学生档案、证书、注册数据）
**数据密度**: 中（学生端：卡片+节点地图；管理端：表格+气泡状态）
**主要容器模式**: 学生端：全页面沉浸（课时内）+ 覆盖层（答题反馈）；管理端：Dialog（证书颁发）+ Dropdown（Actions 菜单）

### 导航骨架图（ASCII）

```
学生端
──────────────────────────────────────────────
Home / Dashboard
  └─ My Courses（课程卡列表）
       └─ Course Map（节点路径图）
            └─ Lesson Exercise（沉浸全屏）
                 ├─ Inline Feedback（覆盖层）
                 └─ Lesson Complete（完成汇总屏）
  └─ Tests & Quizzes
       └─ Quiz Instructions Modal → Quiz Question（循环）→ Results

管理端
──────────────────────────────────────────────
Admin Dashboard
  └─ Students（学生列表）
       └─ Student Profile
            ├─ Enrollments Tab（课程注册表格）
            │    └─ Actions Menu → Issue Certificate Modal → Toast Confirm
            └─ Certificates Tab（已颁证书表格 + Revoke）
```

---

#### 图 2：关键状态对比图（Key State Variations）

```
左：Course Map 有进度（部分节点已完成）         右：新学生空状态（未选课程，引导探索）

┌────────────────────────────────────┐  ┌────────────────────────────────────┐
│ My Courses  [Python Fundamentals]  │  │ My Courses                         │
├────────────────────────────────────┤  ├────────────────────────────────────┤
│        ◉ Intro to Python           │  │                                    │
│        ✓ Variables & Types         │  │                                    │
│        ✓ Control Flow              │  │         📚                         │
│        ● Functions  ← 当前         │  │   You haven't enrolled in any      │
│        ○ Classes    ← 解锁待做     │  │   courses yet.                     │
│        🔒 Modules   ← 锁定         │  │                                    │
│        🔒 Advanced  ← 锁定         │  │   [Explore Courses]                │
│                                    │  │                                    │
│   Progress: 2/7 完成  28%          │  │                                    │
└────────────────────────────────────┘  └────────────────────────────────────┘
```

---

#### 图 3：覆层层级图（Overlay Hierarchy）

```
┌──────────────────────────────────────────────────────────────────────────┐
│  [Logo]  My Courses  Tests  Progress  Profile                 [Avatar ▾]  │ ← TopBar（z-100）
├───────────────┬──────────────────────────────────────────────────────────┤
│  Sidebar      │  ▓▓▓▓▓▓░░░░░░░░░░░░░  Progress 28%  Lesson 3 / 7       │ ← 课时内进度条（z-100）
│               ├──────────────────────────────────────────────────────────┤
│  Course Map   │  【课时题目区（全屏，Lesson Exercise 沉浸模式）】         │
│  My Progress  │                                                          │
│  Tests        │  What is the output of print(2 + 3)?                    │
│  Profile      │                                                          │
│               │  ○  4     ○  5     ○  6     ○  Error                    │
│               │                      [Check（选择后激活）]               │
│               │                                                          │
│               │  ┌──────────────────────────────────────────────────┐   │
│               │  │  Inline Feedback Overlay（底部覆盖层）z-index:200 │   │
│               │  │  ✓ Correct!  +10 XP          [Continue →]        │   │
│               │  │  或 ✗ Incorrect  [Try Again]  [See Answer]        │   │
│               │  └──────────────────────────────────────────────────┘   │
│               │    ▲ 触发: 点击 Check 提交答案                            │
│               │                                                          │
│               │  ┌──────────────────────────────────────────────────┐   │
│               │  │  Quiz Instructions Modal（中）z-index: 300        │   │
│               │  │  1. Read each question carefully                  │   │
│               │  │  2. Select your answer                            │   │
│               │  │  3. You have 1 attempt per question               │   │
│               │  │  [Continue]                          [× Close]    │   │
│               │  └──────────────────────────────────────────────────┘   │
│               │    ▲ 触发: 进入 Quiz 前的说明弹窗                         │
│               │                                                          │
│               │  ┌──────────────────────────────────────────────────┐   │
│               │  │  Issue Certificate Modal（Admin，中）z-index: 300 │   │
│               │  │  Certificate template: [Select template ▾]       │   │
│               │  │  [Cancel]                    [Issue（primary）]   │   │
│               │  └──────────────────────────────────────────────────┘   │
│               │    ▲ 触发: Admin → Student Profile → Actions → Issue    │
└───────────────┴──────────────────────────────────────────────────────────┘
  ┌───────────────────────────────────────────────────────┐
  │  ✓ Certificate issued to Alex Wang   [×]              │  ← Toast（底部，z-500）
  └───────────────────────────────────────────────────────┘

触发关系说明:
- Inline Feedback Overlay（底部）: 提交答案后即时出现，z-200，覆盖题目底部，正确/错误分支不同
- Quiz Instructions Modal（中）: 进入测验前强制显示，z-300，用户确认后才开始计时
- Issue Certificate Modal（Admin，中）: Admin 端 Actions → Issue Certificate 触发，z-300，选模板后才激活按钮
- Toast（底）: 颁发成功等轻量反馈，z-500，3-5 秒消失
```

---

## 该场景独有的 IA/UX 决策

1. **进度分层表达（全局 vs 单次）** — edtech 必须同时维护两个维度：课程级进度（课程地图节点完成率）和单课级进度（课时内顶部进度条）。通用 SaaS 只需任务状态，而 edtech 需要让用户感知「我在这门课里完成了多少」与「我在这节课里走到哪了」两个层次，否则学习动力会断裂。

2. **答题反馈必须包含解释路径，而非仅告知对错** — Brilliant、Imprint、Preply 的测验均在错误反馈后提供「Why? / Explanation / See answer」入口。通用表单提交只需成功/失败；edtech 的错误是学习机会，系统必须将「错误 → 解释 → 继续」设计为三步流程而非两步，否则会直接削弱学习效果。

3. **证书双轨制：自动触发 vs 管理员手动颁发** — 必须同时支持：课程完成自动发放（面向学生）和管理员从学生 Profile 主动颁发（面向运营/合规场景）。证书有法律/就业价值，必须支持手动覆盖和 Revoke（撤销）能力，这决定了证书管理需要独立于课程完成逻辑的 IA 分支。

4. **Empty State 承担激励钩子角色** — edtech 的 empty state 不仅说明「暂无内容」，还直接嵌入创建/启动引导（CTA 按钮 + 激励文案）。这与通用 SaaS 的占位提示有本质区别——empty state 是课程激活的最后一道漏斗环节。

5. **课程地图作为独立 IA 层而非导航菜单** — 课程地图是可浏览、有视觉节奏的路径图（节点 + 连线 + 锁定态），而非普通列表。「还有多少路要走」变成可感知的空间概念，用视觉化手段维持长期留存动力——通用产品用进度百分比即可，edtech 需要地图。

---

## Canonical Flows

> 以下 flow 基于对真实产品的横向分析抽象而来，代表该场景的高频用户任务。

### Flow 1: 完成交互课时并领取奖励

**在此场景的特殊性**: 奖励不是功能解锁（通用 SaaS），而是学习动机维持工具——XP + 连击是游戏化层叠的核心；错误反馈必须携带解释路径，不能只告知对错；Check 按钮在选择前条件禁用，强制先选后提交

**前置条件**: 用户已登录且已注册目标课程；当前课时节点已解锁（前置课时已完成）
**若前置条件不满足**: 节点未解锁 → 点击节点显示锁定提示「Complete [前置课时名] first to unlock」；未注册课程 → 重定向至课程购买/注册页

**Entry**: 用户在课程地图点击未完成的课时节点

**Screens**:

```
Screen 1: 课程地图（Course Map）
  主操作: 点击目标课时节点
  关键组件: 节点路径图（已完成/锁定/当前态）、课程总览卡（总课时数、进度）
  → 选择课时: Screen 2
  → 返回首页: 退出

Screen 2: 课时交互区（Lesson Exercise）
  主操作: 操作交互控件 → 点击 Check
  关键组件: 顶部线性进度条、题目提示文本、交互控件、条件禁用的 Check 按钮、关闭按钮
  → 未选择时: Check 保持禁用
  → 提交答案: Screen 3（反馈）
  → 关闭: 返回 Screen 1（进度不保存）

Screen 3: 答题反馈（Inline Feedback — 覆盖层）
  主操作: 选择「继续」（正确）或「重试 / 查看解答」（错误）
  关键组件: 正确=绿色覆盖层 + XP 即时显示；错误=黄色提示 + Try Again + See Answer；可展开解释面板
  → 正确: Screen 4
  → 错误后重试: Screen 2
  → 错误后查看答案: 展示正确答案 → Screen 4

Screen 4: 课时完成汇总（Lesson Complete）
  主操作: 点击「Continue」
  关键组件: 完成插图、Lesson complete 标题、TOTAL XP 数字、连击奖励（如有）、Continue 按钮
  → 成功: Screen 1（节点更新为已完成态）
```

**Exit State**: 返回课程地图，当前节点打勾/高亮，下一节点解锁，XP 计入账户
**Empty State**: 若课时未解锁（前置课时未完成），节点显示灰色锁定态，点击提示「完成前一课时后解锁」

---

### Flow 2: 进行词汇自测并管理生词

**在此场景的特殊性**: 这不是打分测验，是「自我声明式」二元认知评估（Yes/No），结果直接驱动内容个性化（加入生词表）；结果屏是行动转化点而非终点，必须有明确的后续 CTA

**前置条件**: 用户已登录；已注册该语言课程；「Tests & Quizzes」功能对当前课程可用
**若前置条件不满足**: 未注册课程 → 测验卡显示「Enroll to take quizzes」+ 注册 CTA；测验功能被管理员禁用 → 测验卡置灰 + Tooltip 说明

**Entry**: 用户在「Tests & Quizzes」区域点击「Vocab Quiz」卡片

**Screens**:

```
Screen 1: 测验入口总览（Tests & Quizzes Overview）
  主操作: 点击「Vocab Quiz」卡
  关键组件: 测验卡列表（Progress Test / Vocab Quiz）、历史结果卡（含进度条）、左侧学习模块侧边栏
  → 点击测验卡: Screen 2
  → 浏览历史: 停留

Screen 2: 测验规则说明弹窗（Instructions Modal）
  主操作: 点击「Continue」
  关键组件: 居中模态框、编号步骤说明（1-2-3）、Continue 主按钮、关闭 X
  → Continue: Screen 3
  → 关闭: 返回 Screen 1

Screen 3: 题目问答（Quiz Question — 循环）
  主操作: 点击「Yes」或「No」回答单词认知
  关键组件: 顶部线性进度条、大字体单词显示、问题文本、Yes/No 二元按钮、关闭 X
  → 回答后自动加载下一题（进度条推进）
  → 全部完成: Screen 4
  → 关闭: 中断退出

Screen 4: 测验结果与后续行动（Results & Follow-up CTA）
  主操作: 点击「Add words」或「Skip」
  关键组件: 强调色背景、个性化标题、得分百分比 + 进度条、词汇量估算、未知词示例列表、Add words（主）/ Skip（次）双按钮
  → Add words: 进入生词本管理
  → Skip: 返回 Screen 1
```

**Exit State**: 选 Add words 后未知词批量加入 Vocab List，返回总览并更新「已测验」状态；选 Skip 直接回总览
**Empty State**: 若用户全部回答「Yes」（无生词），结果屏显示积极反馈，隐藏「Add words」，仅显示 Done

---

### Flow 3: 管理员颁发学生证书

**在此场景的特殊性**: 不同于自动化权益，这是管理员绕过自动判定主动执行的运营动作；操作路径嵌入在学生档案的 Enrollment 表格中（「以学生为中心」的 IA 组织逻辑）；必须有 Revoke 能力，因证书有外部法律效力；证书模板下拉在选择前禁用 Issue 按钮

**前置条件**: 当前用户为 Admin 角色；目标学生已注册该课程；该课程已配置至少一个证书模板（否则 Issue Certificate 置灰）
**若前置条件不满足**: 无证书模板 → 「Issue Certificate」置灰 + Tooltip「Create a certificate template for this course first」+ 跳转链接；学生未注册 → Actions 菜单不显示 Issue 选项

**Entry**: 管理员打开目标学生的 Profile 页面，切换到「Enrollments」Tab

**Screens**:

```
Screen 1: 学生 Enrollments 列表（Enrollment Table）
  主操作: 点击目标课程行的「Actions」按钮（三点菜单）
  关键组件: 左侧学生信息栏（头像、姓名）、Enrollment 表格（Course Name / Progress % / Actions）、进度气泡
  → 点击 Actions: Screen 2
  → 手动注册: 「Select course + Enroll」表单

Screen 2: 课程 Actions 菜单（Contextual Dropdown）
  主操作: 选择「Issue Certificate」
  关键组件: 上下文下拉菜单（Stats / Issue Certificate / Reset Progress / Unenroll-红色）
  → Issue Certificate: Screen 3
  → 其他选项: 对应分支

Screen 3: 颁发证书弹窗（Issue Certificate Modal）
  主操作: 从下拉选择证书模板 → 点击「Issue」
  关键组件: 居中模态框、证书模板下拉（选择前禁用 Issue）、Cancel（次）/ Issue（主，品牌强调色）
  → 未选择时: Issue 按钮禁用
  → 点击 Issue: Screen 4
  → 取消: 返回 Screen 1

Screen 4: 颁发确认（Toast + Updated Table）
  主操作: 查看确认结果
  关键组件: 页面底部 Toast 成功提示（短暂出现）、Certificates 区新增记录行（Course / Certificate Title / Date Issued / Revoke-红色）
  → Toast 消失: 停留在更新后的 Screen 1
  → 点击 Revoke: 触发撤销确认
```

**Exit State**: Certificates 表格出现新记录（含日期和 Revoke 选项），Toast 成功消息短暂显示后消失
**Empty State**: 若该课程无证书模板，「Issue Certificate」置灰，点击后提示「请先为该课程创建证书模板」并引导至证书创建流程

---

---

### Flow 4: 课程阶段测验与证书领取（学生端）

**在此场景的特殊性**: 这是学生端的「正式评估 → 证书」完整路径，与 Flow 2（词汇自测）的本质区别在于：有明确的通过分数线（Pass/Fail）、计分机制（百分比得分）、以及「通过后生成可下载证书」的闭环。通过后的证书领取是学习旅程的高价值节点，需要明确的成就感设计（庆祝屏 + 下载 CTA）。失败路径需区分「勉强未通过」和「明显不足」两种反馈强度，并提供复习建议。Preply（flow_id 9218）的题目循环 + 成功反馈 + 节点更新是核心结构参考。

**行业共识**: 有得分评估机制的 edtech 产品（Teachable、Brilliant、Preply）均采用此模式。

**前置条件**: 用户已登录；已注册对应课程；「Progress Test」功能对该课程已开启；学生完成度满足测验入场条件（部分产品要求完成一定比例课时后才可参加正式测验）
**若前置条件不满足**: 未满足入场条件 → 测验卡显示锁定态「Complete 80% of the course to unlock the test」+ 进度提示

**Entry**: Tests & Quizzes 页面 → 点击「Progress Test」卡片

```text
Screen 1: 测验入口（Tests & Quizzes Overview）
  主操作: 点击「Progress Test」卡片
  关键组件:
    - 测验卡（卡片含：题目数量、预计时长、通过分数线如「70%」、本人历史最高分）
    - 开始测验 CTA（「Start Test」）
    - 历史成绩迷你图（折线或进度条，过去3次尝试）
  → 点击测验卡 / Start Test: Screen 2（规则说明 Modal）

Screen 2: 测验规则说明 Modal
  主操作: 确认规则后开始
  关键组件:
    - Modal 标题:「Progress Test: [章节名]」
    - 说明列表: 题目数量、时间限制（如有）、通过分数线、每题尝试次数
    - [Start Test]（primary）/ [Cancel]（ghost）
  → 点击「Start Test」: Screen 3（开始题目循环）
  → 点击「Cancel」: 返回 Screen 1

Screen 3: 测验题目循环（Quiz Question Loop）
  主操作: 选择答案 → 提交 → 继续下一题
  关键组件:
    - 顶部进度条（当前题号 / 总题数，如「Q 3 / 10」）
    - 题目内容区（含题干 + 选项：单选/多选/填空）
    - [Check]（选择前 disabled，选后激活）
    - 答题反馈（inline，轻量版）: 正确 → 继续；错误 → 红色提示 + 正确答案高亮 + 继续
    - 与 Flow 1 的区别：正式测验的错误反馈不提供解释展开，仅显示正确答案（不干扰计分流程）
  → 最后一题提交后: Screen 4（结果页）

Screen 4: 测验结果页
  主操作: 查看得分，决定领取证书或复习重考
  关键组件（通过分支，得分 ≥ 通过线）:
    - 庆祝插图 + 标题「Congratulations! You passed.」
    - 得分显示（如「85 / 100」+ 百分比 + 「Passed」绿色 Badge）
    - 正确率明细（可折叠：各题对错情况）
    - 主 CTA:「Download Certificate」（生成 PDF + 弹出浏览器下载）
    - 次 CTA:「Back to Courses」
  关键组件（未通过分支，得分 < 通过线）:
    - 鼓励性标题「Almost there! Keep practicing.」（未大幅落后）
      或「Let's review the material first.」（明显不足，得分 < 50%）
    - 得分 + 「Not passed yet」橙色 Badge
    - 建议复习模块（「Review [Lesson X] to strengthen these topics」）
    - 主 CTA:「Retake Test」/ 次 CTA:「Review lessons」
```

**Exit State**:

- ✅ 通过：证书 PDF 下载到本地；Certificates 列表新增记录；课程地图 Tests 节点标为完成
- ❌ 未通过：显示复习建议；Tests 节点保持未完成；可再次触发测验（Retake）
- ↩ 退出中途：退出测验 → AlertDialog「Exit test? Your progress will not be saved.」

---

## Component Kit

按使用频率排序，标注用途：

| 功能概念 | 具体用途 |
|---|---|
| 进度条 | 课时内顶部进度条、测验题目进度、课程完成率气泡 |
| 内容卡片 | 课程卡、测验卡、学生 Profile 信息块 |
| 操作按钮 | Check（条件禁用）、Yes/No 二元按钮、Issue / Cancel / Revoke |
| 模态对话框 | 证书颁发弹窗、测验规则说明、操作确认 |
| 下拉操作菜单 | Actions 三点菜单（Issue / Reset / Unenroll）|
| 操作通知（Toast）| 颁发成功、操作完成的短暂通知 |
| 基础数据表格 | 学生 Enrollment 列表、证书记录列表 |
| 状态标签 | 进度状态气泡（已完成 / 进行中 / 未开始）、课时解锁态 |
| 选择下拉 | 证书模板下拉、课程注册选择 |
| 标签页切换 | Student Profile 内的 Enrollments / Certificates / Activity 切换 |
| 用户头像 | 学生头像（Profile 侧栏）|

---

## Anti-Patterns

> 该场景中真实存在的常见设计错误，基于研究观察。

- **单层进度表达**：只在课程列表显示总进度百分比，课时内没有当前题目的局部进度条 → 正确做法：全局进度条（课程地图节点）和局部进度条（课时内顶部）同时存在，各自管理不同层级的进度感

- **错误反馈仅告知对错**：答题错误后只显示红色提示和「重试」，不提供解释路径 → 正确做法：错误反馈必须携带「Why / Explanation / See answer」入口，将错误设计为学习机会

- **Check 按钮始终可点**：用户未选择答案即可提交，导致空提交或误操作 → 正确做法：Check 按钮在用户选择前保持 disabled 状态，选择后才激活

- **证书单一触发路径**：只有「课程完成率达 100%」时自动发放证书，无管理员手动操作入口 → 正确做法：同时支持自动触发（学生端）和管理员手动颁发（Admin 端），并提供 Revoke 能力

- **Empty State 仅占位**：空证书列表只显示「暂无证书」文字 → 正确做法：empty state 嵌入行动引导（「为该课程创建第一个证书模板」+ 主 CTA 按钮），承担激活漏斗功能
