# Scenario: Mobile EdTech（教育科技）

> **研究来源**：基于对 Brilliant、Imprint、Duolingo、BoldVoice、Promova、Kann、Moonly 等 7 个真实 iOS 产品 flow 和页面的横向分析抽象，不代表任何单一产品的具体实现。

---

## Identity

**Platform**: Mobile (H5 / React Native)
**Definition**: 以课程学习和知识练习为核心的移动端教育应用，用户通过课程地图发现并完成课程单元，在内容阅读中完成内嵌测验获取 XP 奖励；应用以每日连击（Streak）和游戏化激励维持用户学习习惯，通过 Freemium 模式在 Paywall 处引导用户订阅付费计划。

**Canonical Examples**: Duolingo iOS（语言学习 + Streak）、Brilliant iOS（数学/科学交互式学习）、Imprint iOS（书摘 + 每日测验）、BoldVoice iOS（口音/语言 AI 练习）

**Not this scenario if**:
- 以视频课程为主（Udemy/Coursera 类，重在播放视频而非交互式内容，属于 web/edtech 或娱乐场景）
- 以企业培训为主（内部 LMS/合规培训，属于 web/internal-ops 变体）
- 以直播授课为主（在线家教/1:1 辅导，实时交互属于 Consumer Social 子场景）
- 以题库刷题为主（高考/考研刷题 App，属于专项 TestPrep 子场景）
- 主要在 Web 端使用（改用 web/edtech）

---

## User Profile

| 维度 | 内容 |
|---|---|
| **主要角色** | 自学者（碎片时间学新技能）/ 语言学习者（每日练习维持水平）/ 技能提升者（系统学习数学/科学/编程）|
| **核心目标** | 完成今日课程任务 / 维持连击不断签 / 通过测验检验理解 |
| **心智模型** | 期待「游戏感」（进度条、XP、徽章让学习有仪式感）；期待「短课时」（5-15 分钟可完成一个单元）；期待「即时反馈」（答对/答错立刻知道，不用等提交后全部批改）|
| **使用频率** | 高频（每天 1 次，通勤/睡前 10-20 分钟）：连击机制推动日常打卡 |
| **决策模式** | 任务驱动型：由「今日任务」或 Streak 提醒驱动打开 App，目的明确；偶尔探索新课程 |
| **容错期望** | 答错不扣命（部分 App 有「命」机制但通常可恢复）；连击中断有「修复」机会（Streak Freeze）；订阅前有免费内容体验 |

---

## IA Template

**导航模式**: Tab Bar（底部 Tab Bar，4-5 项）

Brilliant 模式（知识型课程）：
```
Tab 1: 首页 / Home    — Streak 进度卡片 + 今日课程节点
Tab 2: 课程 / Courses — 分类浏览 + 课程地图
Tab 3: 排行 / Leagues — 周排行榜（Leaderboard）
Tab 4: 设置 / Settings — 账户 + 订阅
```

Duolingo 模式（语言学习 + 游戏化）：
```
Tab 1: 学习 / Learn   — 课程地图（技能节点垂直滚动）
Tab 2: 练习 / Practice — 弱点复习
Tab 3: 排行 / Leaderboard — 联赛排名
Tab 4: 人物 / Profile — 徽章 + 统计
Tab 5: 更多 / More    — 设置 + 任务
```

BoldVoice 模式（AI 语言练习）：
```
Tab 1: 为你 / For You — 今日计划 + 推荐练习
Tab 2: 课程 / Course  — 课程列表 + 学习进度
Tab 3: AI 对话 / AI Chat — AI 口语练习（含红点角标）
Tab 4: 资源 / Resources — 额外学习材料
Tab 5: 我的 / Profile — 账户 + 订阅状态
```

**页面层级**: 3 级
```
L1: Tab 根页（Home / Courses / Practice）
L2: 课程详情（Course Map：技能节点地图）/ 课程类别（Category List）
L3: 课程单元阅读器（Lesson Reader，全屏沉浸）/ 每日测验 / Paywall
```

**权限流结构**（EdTech App 权限集中）:
```
Notifications（连击提醒 / 每日练习时间到 / 订阅到期）:
  → 首次完成第一节课后 → 说明页（「连击不断签，每日提醒」）
  → 系统 Notifications 权限弹窗
  → 时机：用户刚完成课程，正在感受学习成就感时请求

Microphone（AI 口语练习 / 发音识别 - BoldVoice / Duolingo 等）:
  → 首次进入口语练习 → 自定义说明页（「麦克风用于评估你的发音」）
  → 系统麦克风权限弹窗

Speech Recognition（语音转文字答题 - 部分 App）:
  → 说明页 → 系统 Speech 权限弹窗（随 Microphone 一起请求）

Camera（扫描教材 / AR 功能 - 部分 App）:
  → 系统 Camera 权限弹窗（单独在使用时请求）
```

**数据密度**: 低（课程阅读器全屏单页内容，答题卡片居中排列，进度用颜色/图标表示而非数字表格）
- 核心视图：全屏内容页（Swiper / ScrollView）+ 课程地图（纵向 List）
- 辅助视图：Grid（课程分类 / 徽章展示）
- 游戏化元素：线性进度条（顶部）+ 自定义 XP 动画
- 不使用：多列 Table、复杂 Form

**主要容器模式**:
| 场景 | 容器 |
|---|---|
| 课程单元阅读器 | Full-screen Modal 或 Stack Push（全屏沉浸，无 Tab Bar）|
| 答题即时反馈 | 全屏叠层（Overlay：绿色/红色背景 + 正确答案说明）|
| 课程单元完成庆祝 | Bottom Sheet（large）或内嵌全页（XP 总结 + 徽章）|
| Paywall | Bottom Sheet（large）或 Full-screen Modal（同 Entertainment 场景）|
| 连击中断警告 | Dialog 或 Bottom Sheet（medium）（「今日连击将在 X 小时后中断」）|
| 每日测验 | Stack Push（独立页面）或 Bottom Sheet（large）（从 Home 触发）|
| 排行榜 | Stack Push（独立 Tab 根页）|
| 删除学习记录确认 | Dialog |

**导航骨架图（ASCII，Brilliant 模式）**:
```
┌────────────────────────────────────┐
│  Status Bar（时间 / 信号 / 电量）    │
├────────────────────────────────────┤
│  ⚡ 1  [T][W][Th][F][S]  ↗         │  ← Streak Card（连击天数 + 周点阵）
│  1 Max streak · 5 Lessons complete │
├────────────────────────────────────┤
│                                    │
│  ╔══════════════════════════════╗  │
│  ║  [3D 等轴测课程地图插图]      ║  │
│  ║                              ║  │  ← 课程地图（当前进度节点）
│  ║  ▶ Analyzing Bar Charts      ║  │
│  ╚══════════════════════════════╝  │
│                                    │
│  [继续课程]  主色 Button           │  ← 今日 CTA
│                                    │
├───┬──────┬──────┬─────────────────┤
│ 🏠 │ 📚  │  🏆  │  ⚙️              │  ← TabBar
└───┴──────┴──────┴─────────────────┘
```

---

## 该场景独有的 IA/UX 决策

1. **Paywall 必须在用户完成第一节免费课后触发，不可在 Onboarding 末尾前置** — 移动端 EdTech 的转化逻辑是「先体验学习风格，再判断是否值得付费」。Brilliant（flow 4316，48屏）的 Onboarding 让用户先完成一节真实课程内容，感受交互式学习体验后才弹出订阅页——而非在问卷结束后立即呈现 Paywall（此时用户尚未理解产品价值，付费意愿极低）。移动端 EdTech 与 SaaS 的根本区别在于：SaaS 用户在注册前已了解功能，EdTech 用户必须「先上手才能感知价值」，因此免费首课是 Paywall 的必要前置，不是可选的宽松策略。

2. **课程进度条必须在每道练习题层级显示（而非仅课程层级），让用户感知时间成本** — 移动端 EdTech 的核心焦虑是「这节课还要多久」。Brilliant（flow 4333 / 4326 / 4335）/ Imprint（flow 5644）均在 Lesson 界面顶部展示分段式进度条（每格对应一道练习题，当前题高亮），而非简单的「第 3 课 / 共 12 课」文字——分段进度条让用户在任意时刻都知道「还剩几步」，可以决定「现在能不能完成」，是防止中途放弃的关键机制。

3. **课程完成模态必须是全屏庆祝 UI（含 XP / 连击更新 + Haptic），不可用普通 Toast** — EdTech 的留存核心是「完成感」——每完成一课，用户必须收到明确的正向强化。行业共识（Duolingo 绿色猫头鹰 + XP 徽章 / Imprint 奖励卡片 / Brilliant 积分弹窗）均使用全屏或半屏 Modal（Bottom Sheet large 或 Full-screen Modal）展示 XP 获得数、连击天数更新、新解锁徽章，配合触觉反馈（RN：`expo-haptics` success；H5：`navigator.vibrate`）——Toast 3 秒消失的短暂反馈无法给予「真正完成了某件事」的仪式感，直接影响次日留存意愿。

4. **连击（Streak）必须在 Home 首屏以日历点阵显示，连击断掉时提供「修复」而非批评** — 移动端 EdTech 的首屏必须让用户第一眼看到自己的连击状态（Brilliant Home：周点阵 + 连击天数大字 + 今日节点高亮）——连击不在首屏等于不存在，失去最强留存锚点。更重要的是：连击中断时不应显示「你打破了连击！」的负面提示，而应提供「连击修复（Streak Repair）」机制（消耗道具或完成补课任务），转化中断危机为参与机会——Duolingo 的 Streak Freeze 道具和连击修复流程是行业验证的留存设计，EdTech 产品不处理中断场景等于放弃了连击断后最脆弱的流失节点。

5. **交互式练习（拖拽/点击选项/填空）必须用原生手势实现，不可用 WebView 内嵌** — Brilliant 的核心竞争力是移动端原生交互练习（拖拽图表元素 / 点击选项即时高亮反馈 / 填写公式），而非 PDF 教材或嵌入式 Web 内容——原生实现（RN `PanResponder` / `Gesture Handler`；H5 Pointer Events + CSS 动画）才能提供即时的视觉反馈（选中动画 + 正误颜色变化 + 触觉反馈），WebView 内嵌的交互延迟和滚动行为异常会严重破坏「流状态」（Flow State）。移动端 EdTech 与 Web EdTech 在技术层的根本差异是：Web 可以用 HTML Canvas / React 构建通用练习组件，移动端需要原生手势 API，开发成本更高但交互体验完全不同。

---

## Canonical Flows

> 以下 flow 基于 7 个真实产品样本横向分析抽象。括号内标注「行业共识」表示 3 个以上产品采用相同模式。

---

### Flow 1: Personalized Onboarding & Learning Path Setup（个性化 Onboarding + 学习路径）

**在此场景的特殊性**: 移动端 EdTech App 的 Onboarding 与其他场景最大的区别是**学习目标问卷（Goal Questionnaire）驱动个性化推荐**——这不是普通的用户偏好设置，而是一个引导用户思考自身学习目标的「教育性」问卷，Brilliant（flow 4316）展示了经典的三问结构：主目标（What's your top goal?）→ 子目标细化 → 学科偏好，每步选择后 App 给出「有共鸣」的反馈（「好选择！80% 的学习者有相同目标」），增加仪式感。**学习路径推荐加载屏**（Loading: 「Finding your perfect learning path...」）是 EdTech 特有的「计算感」UX，刻意放慢加载速度让用户感受个性化价值。**Paywall 在 Onboarding 末尾插入**（不是在用户触发付费内容时才弹出），这与娱乐 App Paywall 时机不同——EdTech 趁用户学习动机最高时呈现付费价值（Brilliant / BoldVoice / Promova 均如此）。Paywall 展示「学习路径将帮助你...」而非通用功能列表，把订阅价值与刚设定的目标直接挂钩。

**行业共识**：Brilliant（flow 4316）/ BoldVoice / Promova 均在 Onboarding 末尾触发 Paywall；三问学习目标问卷结构在多个教育 App 中验证；平台内购或支付处理是移动端强制要求（同 Entertainment 场景）。

**Entry**: 首次安装 → App 启动 → Onboarding 引导

```
Screen 1: 欢迎页（Brand Intro）
  主操作: 了解 App → 点击「开始」
  关键组件:
    - 全屏品牌画面（Lottie 动画或 Image，品牌吉祥物/插图）
    - Text("学习，让人进步"，largeTitle，粗体）
    - Text(一句话价值主张，body，灰色）
    - Button("开始", 主色，全宽)

Screen 2: 目标问卷（Goal Questionnaire，多步）
  主操作: 选择学习目标 → 推进问卷
  关键组件:
    - Stack Navigation（顶部进度条线性进度）
    - Step 1: Text("你的主要学习目标是？", title，粗体)
        选项卡片列表（每个选项: 图标 + 目标名称 + 描述）
        选中态: 品牌色边框 + 浅色填充
    - Step 2: Text("具体想提升哪方面？") + 子目标选项列表
    - Step 3: Text("你想学的科目是？") + 学科 Grid（3列，图标 + 名称）
    - Button("继续", 主色，全宽，disabled 未选时)
    - [选择后] Text("好选择！X% 的学习者有同样目标"，小字，品牌色，动画淡入）

Screen 3: 学习路径计算加载（Loading Personalization）
  主操作: 等待系统生成路径（有意延迟，增加个性化感知）
  关键组件:
    - 圆形 Loading 或线性进度条（带百分比）
    - Text("正在为你寻找最适合的学习路径...", 动画文字逐步出现）
    - [可选] 3条简短统计数字依次淡入:
        Text("已有 X 万名学习者完成此路径")
        Text("平均每天只需 15 分钟")
    - 约 2-3 秒后自动进入 Screen 4

Screen 4: 学习路径推荐（Learning Path Recommendation）
  主操作: 查看推荐路径 → 了解内容 → 进入 Paywall
  关键组件:
    - Text("你的专属学习路径已准备好！", 粗体大字）
    - 推荐路径卡片 List（1-3条，大圆角卡）:
        每张 PathCard:
          封面图（路径封面）
          路径名（粗体）
          「X 个课程 · 预计 X 周」（小字灰色）
          线性进度条（「0% 完成」，灰色 = 未开始）
    - [部分 App] 免费预览提示（Text("前 3 节可免费体验"，小字)）
    - Button("解锁完整路径", 主色，全宽）→ Screen 5 Paywall

Screen 5: Paywall（学习目标版）
  主操作: 选择订阅计划 → 订阅
  关键组件（与 Entertainment 场景相同的订阅结构，但内容差异化）:
    - 功能展示:
        功能点列表（「✓ 完整课程库 XX+ 门」「✓ 每日 AI 反馈」「✓ 无广告学习」）
        或 Carousel Feature Card（每页一个具体功能）
    - 「与你的目标匹配」文案（呼应问卷中选择的目标，如「帮你实现：提升数学能力」）
    - 计划选择（Annual 默认选中 + 「节省 X%」Badge / Monthly 备选）
    - 试用说明（「7 天免费试用，随时取消」，小字）
    - Button("开始免费体验", 主色，全宽）
    - Button("恢复购买", 文字按钮)（合规要求）
    - Button("跳过，先免费体验", 文字按钮)（选填，允许用户用免费内容体验）
  → 点击「开始免费体验」: 平台支付流程 → 成功返回首页
```

**Exit State**:
- ✅ 订阅成功：进入首页，学习路径解锁，Paywall 关闭
- ↩ 点击「跳过」：进入首页，仅可访问免费内容，付费内容显示锁定状态
- ✅ 完成 Onboarding（无订阅）：首页显示推荐课程，付费课程节点显示 🔒

---

### Flow 2: Lesson Completion（课程单元阅读 + 答题 + 完成）

**在此场景的特殊性**: 移动端 EdTech 课程单元与 Web 端在线课程最大的区别是**全屏沉浸式「课程阅读器」（Lesson Reader）**——进入课程后，Tab Bar 消失，整个屏幕变为单页内容展示，顶部只有进度条（线性进度）和关闭按钮，让学习者专注内容，不受导航干扰（Brilliant / Imprint / Moonly 均如此）。**内嵌式多选题（Inline MCQ）**是与 Web 端最大的 UX 差异——移动端答题卡片直接出现在内容流中，用户点选后出现即时反馈全屏叠层（绿色=正确/红色=错误，带短暂触觉反馈），而非把所有题目集中到末尾测试（Brilliant flow 4333 / flow 4326 详细记录了 29 屏交互流程）。**答错后的「Why?」解释展开**直接在题目下方展示——用户答错时看到正确答案 + 原因，学习效果优于纯粹显示「错误」。**课程完成动画**是高密度的情绪满足时刻，XP 数字飞出动画配合触觉反馈，是移动端独有的沉浸式奖励体验。

**行业共识**：Brilliant（4333/4326）/ Imprint（5643/5644）/ Kann（9160）均使用「内嵌 MCQ + 即时反馈」结构；课程完成 XP 总结 Modal 是所有研究样本的共识（Duolingo / Imprint / Brilliant 均有）；课程完成后返回课程地图并即时更新节点状态是行业标准。

**Entry**: 课程地图点击当前可用课程节点 → 进入课程阅读器

```
Screen 1: 课程地图（Course Map）
  主操作: 查看课程进度 / 选择下一课程
  关键组件:
    - Stack Navigation（页面标题为课程名称）
    - ScrollView（纵向，课程节点列表）:
        每个 LessonNode（圆形图标或方形卡片）:
          已完成（绿色 checkmark + 标题）
          当前（品牌色 highlight + Button "开始/继续"）
          未解锁（灰色 lock 图标 + 标题）
          未订阅解锁（🔒 图标，点击 → Paywall）
    - Section Header（「Unit X: 单元名称」）
    - 顶部进度卡: Text("X% 完成") + 线性进度条
  → 点击当前节点: Full-screen Modal → Screen 2 课程阅读器

Screen 2: 课程阅读器（Lesson Reader，全屏沉浸）
  主操作: 阅读内容 → 答题 → 完成课程
  关键组件（Tab Bar 隐藏，全屏沉浸）:
    - 顶部:
        Button(✕ 关闭)（左上角，→ Dialog 确认放弃）
        线性进度条（中部横向，标识当前课程进度）
        当前步数/总步数（右侧，小字，可选）
    - 内容区域（根据内容类型切换）:
        [文本内容页] ScrollView / 全页 VStack:
          内容标题（粗体大字）
          内容段落（正文字号，行间距 8）
          Image / 插图（可选）
        [图表/交互内容页] 自定义交互组件（Slider / 选择器等）
        [嵌入视频] 视频播放器（定高，不全屏，inline 播放）
    - 底部导航（固定在视口底部）:
        Button("继续", 主色，全宽)（阅读页）
        或 [MCQ 答题态]:
          选项卡片列表（每个 MCQ 选项）:
            Button(选项文字，次要，选中态: 品牌色填充)
          Button("检查答案", 主色，全宽，disabled 未选时)

Screen 2-A: 答题即时反馈（Answer Feedback Overlay）
  触发条件: 点击「检查答案」后
  主操作: 查看答题结果 → 继续
  关键组件（全屏叠加 Overlay，覆盖课程内容底部约 30%）:
    - [答对] 绿色底色背景（圆角顶部）:
        Text("✓ 正确！", 白色粗体）
        Text("+ X XP", 白色小字，XP 计数动画）
    - [答错] 红色底色背景:
        Text("✗ 正确答案是 [答案文字]", 白色粗体）
        可展开「为什么？」区域:
            Text(解释文字，白色）
    - Button("继续", 白色按钮，主色文字，全宽）
    - 触觉反馈（答对 success / 答错 error vibration）
  → 点击「继续」: 叠层关闭 → 下一内容页 / 若为最后一页 → Screen 3

Screen 3: 课程完成庆祝（Lesson Completion）
  主操作: 看到完成结果 → 返回课程地图
  关键组件:
    - Full-screen Modal 或内嵌全页
    - 庆祝动画（Lottie 动画 or 星形图标，品牌色）
    - Text("课程完成！", largeTitle，粗体）
    - XP 总结区（3 项成绩横向排列）:
        总 XP（闪电图标 + 数字）
        用时（秒表图标 + 时间）
        正确率（checkmark 图标 + 百分比）
    - [徽章获得] 徽章插图 + Text("解锁了新徽章！")
    - Button("继续", 主色，全宽）
  → 点击「继续」: 关闭 Modal → Screen 1 课程地图（节点状态即时更新）
```

**Exit State**:
- ✅ 课程完成：课程地图节点变为绿色 checkmark，下一节点解锁；首页 Streak 计数更新
- ↩ 中途关闭（点 ✕）：Dialog「放弃本次学习？当前进度不会保存」→ 确认后关闭，回到课程地图
- ⚠️ 课程被锁定（免费用户访问付费节点）：Empty + 锁图标 + Button("解锁", → Paywall)

---

### Flow 3: Daily Practice & Streak Maintenance（每日练习 + 连击维持）

**在此场景的特殊性**: 移动端 EdTech 的每日练习环节与课程学习有本质区别——课程学习是**线性进度型**（有明确起止节点，完成后 checkmark），每日练习是**周期循环型**（每天刷新，完成后得 Streak，明天重置），这对应了 Duolingo 和 Brilliant 的核心留存机制。**Streak（连击）组件**是移动端 EdTech 独有的高优先级常驻元素——它出现在首页 Streak Card（周点阵 + 火焰图标 + 天数）、Tab Bar Badge（昨天忘记练习时角标提醒）、结课庆祝页（Streak +1 动画）。**每日测验（Daily Quiz）** 是 Imprint 的独特模式：独立于课程路径，每天推送一套基于昨日阅读内容的 5-10 道随机题，Bottom Sheet（large）从首页触发，形成「阅读 → 次日测验」的记忆强化循环。**连击中断保护**（Streak Freeze）：部分 App 允许购买「冻结」让断签不扣连击，此功能通常在 Streak 中断 Dialog 时推销。

**行业共识**：Brilliant / Duolingo 均将 Streak 放在首页最显眼位置（周点阵 + 天数）；每日练习完成后 Streak +1 动画是多产品共识；Push Notifications 练习提醒（「别忘了今天的学习」）是所有研究样本均有的功能。

**Entry**: 首页 Home Tab → Streak 状态展示 / 点击「今日任务」CTA

```
Screen 1: 首页（Today's Dashboard）
  主操作: 查看连击状态 / 进入今日练习
  关键组件:
    - Stack Navigation 或直接 ScrollView（根据 App 风格）
    - Streak 进度卡（显著位置）:
        火焰图标 + 连击天数（粗体大字）
        分享 Button（可选）
        周点阵（7个圆形，当日高亮，已完成日填满，今日可完成日 outlined）
        小字说明（「1 最长连击 · X 课程已完成」）
    - 今日任务区（课程节点预览，等轴测图 or 普通卡片）:
        Text("今日练习", 粗体）
        PathNodeCard（课程当前节点 + 描述 + 「继续」Button）
    - [每日测验类 App] Button("开始今日测验 🎯", 次要）（→ Screen 2 测验 Sheet）
    - Empty（今日任务已完成：「连击保持！明天见 👋」+ 下次任务预告）

Screen 2: 每日测验 / 练习（Daily Practice Session）
  触发条件: 点击「今日任务」或直接从通知跳转
  主操作: 完成一组知识检验题 → 得到 XP + Streak
  关键组件:
    - Stack Push 或 Bottom Sheet（large）（根据 App）
    - 顶部: 分段进度条（完成一题一段变色）
           + 心形图标 × N（「命」数，部分 App 有此机制）
    - 题目区（全屏或大卡片）:
        题目文字（title3，居中或左对齐）
        [MCQ] 选项卡片列表:
            Button(选项文字，次要，选中: 深色填充 + 动画)
        [True/False] 两个大 Button（「✓ 正确」/ 「✗ 错误」，半屏宽）
        [填空/输入] TextInput + 键盘
        Button("检查", 主色，disabled 未选时)
    - 即时反馈（同 Flow 2 Screen 2-A：绿色/红色底部叠层 + 解释文字）
    - [题目全部完成] → Screen 3

Screen 3: 每日练习完成（Session Complete + Streak Update）
  主操作: 查看成绩 → 更新连击
  关键组件:
    - Full-screen Modal 或独立页
    - Streak 更新动画（火焰图标放大 + 天数 +1 动画，品牌色光晕）:
        Text("🔥 X 天连击！", largeTitle，粗体）
        Text("今日任务完成", 灰色）
    - XP 总结（今日获得 XP + 总计 XP，线性进度条经验值条）
    - [徽章完成] Badge 卡片（如「连击 7 天」徽章解锁）
    - Button("完成", 主色，全宽，返回首页）
    - [首次请求通知] Banner（「开启每日提醒，不断签」→ 系统通知权限弹窗）

Screen 3-A: 连击中断处理（Streak Broken Dialog）
  触发条件: 昨日未完成练习，今日打开 App
  主操作: 接受中断 / 购买 Streak Freeze 恢复
  关键组件:
    - Dialog 或 Bottom Sheet（medium）:
        熄灭火焰图标
        Text("连击中断了 😢", 粗体）
        Text("你已经连续学习 X 天，昨日错过了练习。")
    - [有 Streak Freeze 库存] Button("使用连击保护（剩余 X 次）", 主色)
    - [购买 Streak Freeze] Button("购买连击保护 ¥X", 次要)（平台内购）
    - Button("没关系，重新开始", 文字按钮)（接受中断，连击归零）
```

**Exit State**:
- ✅ 今日练习完成：首页 Streak 天数 +1，周点阵当日圆点变为满色；连击卡显示「今日完成」
- 🔥 连击中断：App 打开时展示 Screen 3-A；Streak 天数归零（或使用 Freeze 保留）
- ⚠️ 命数耗尽（部分游戏化 App）：练习暂停 + 「明天再来」提示 + 可选付费刷新命数

---

## Mobile Component Kit

按使用频率排序（基于研究样本观察）：

| 优先级 | 组件（H5 antd-mobile）| 组件（RN Gluestack/RN）| 具体用途 |
|---|---|---|---|
| ★★★ | Tab Bar / `Tabs` | `react-navigation Bottom Tabs` | App 主导航（Home / Courses / Practice / Profile）|
| ★★★ | Stack Navigation | `react-navigation Stack` | 课程目录 → 课程详情 → 节点 Push 导航 |
| ★★★ | Full-screen Modal | `Modal` / `react-navigation Stack` | 课程阅读器（全屏沉浸）/ 完成庆祝 |
| ★★★ | `ProgressBar` 线性 | `ProgressBar` / 自定义分段 | 课程阅读器顶部进度条 / 经验值进度条 / 每日任务段指示 |
| ★★★ | 平台内购 / 自定义支付 | `react-native-iap` / Stripe SDK | Premium 订阅（同 Entertainment 场景）|
| ★★★ | Push Notifications | `expo-notifications` / FCM | 每日练习提醒 / 连击中断警告（核心留存机制）|
| ★★ | `<video>` inline | `react-native-video`（inline 模式）| 课程内嵌教学视频（非全屏）|
| ★★ | Bottom Sheet | `@gorhom/bottom-sheet` | 每日测验 Sheet / 课程完成奖励 / Paywall |
| ★★ | Grid / `WingBlank + Flex` | `FlatList`（numColumns=3）| 课程分类 Grid / 徽章成就展示 Grid |
| ★★ | `List` / `VirtualList` | `FlatList` / `SectionList` | 课程地图节点列表（课程路径纵向展示）|
| ★★ | Overlay / 绝对定位层 | `Modal` transparent / `ZStack` | 答题即时反馈叠层（绿色/红色底部区域）|
| ★★ | `expo-haptics` / `navigator.vibrate` | `expo-haptics` | 答对/答错触觉反馈 |
| ★ | 横向 ScrollView | `FlatList` horizontal | 课程分类横向 Carousel |
| ★ | Accordion / `Collapse` | `DisclosureGroup` / `Accordion` | 答错后「为什么？」解释展开 |
| ★ | Swiper / Carousel | `react-native-pager-view` | Paywall Feature Carousel / Onboarding 多步 |
| ★ | Empty 空状态 | 自定义 Empty | 今日已完成空状态 / 无课程内容 |
| ★ | Dialog / `Modal` | `AlertDialog` | 连击中断处理 / 放弃课程确认 |
| ★ | `expo-speech` / TTS | `expo-speech` | 例句/单词发音（语言学习 App）|
| ★ | 浏览器 Web Speech API | `@react-native-voice/voice` + Speech Recognition | 口语练习录音 + 语音识别评分 |

---

## Anti-Patterns

基于研究样本中观察到的设计错误：

- **答题集中在课程末尾测验（而非内嵌即时反馈）**：用户先阅读所有内容，到最后才做一套题，答错了也无法追溯到具体知识点，学习效果差，且大段内容后突然出题显得割裂。→ 正确做法：MCQ 问题内嵌在课程内容流中（读 2-3 页内容 → 1 题 → 即时反馈 → 继续读），答题成为「内容检验」而非「独立测试」，Brilliant flow 4333 完整展示了此结构（29 屏中 MCQ 与内容交替出现）。

- **答题反馈仅用 Toast，无解释**：答错后只弹出短暂 Toast「回答错误」就消失，用户不知道正确答案是什么，更不知道为什么答错，学习效果等于零。→ 正确做法：答题反馈必须展示（1）正确答案是哪个；（2）简短解释「为什么」（可折叠展开）；（3）视觉区分（绿色/红色覆盖底部区域，配合触觉反馈），Brilliant / Kann / Imprint 均如此。

- **课程阅读器保留底部 Tab Bar**：在阅读课程内容时 Tab Bar 始终可见，用户无意间点到其他 Tab 导致中途退出，同时 Tab Bar 占用宝贵的垂直空间压缩内容显示区。→ 正确做法：进入课程阅读器时使用 Full-screen Modal 或隐藏 Tab Bar 的 Stack Push，顶部只保留进度条和关闭按钮，沉浸式学习环境让注意力集中（Brilliant / Imprint 均如此）。

- **Streak 状态不在首页显示**：用户打开 App 不能立即看到自己的连击天数，只能在「我的」Tab 深层找到，失去了每日打开 App 的仪式感和动力。→ 正确做法：首页 Hero 区域必须显示 Streak 信息（火焰图标 + 天数 + 周点阵），让用户打开 App 第一眼就感受到「X 天连击，今天继续！」的激励（Brilliant Home 和 BoldVoice For You Tab 均将 Streak 置于最顶部可见区域）。

- **Paywall 在 Onboarding 问卷之前弹出**：用户还没设置学习目标、不知道 App 能帮自己做什么，就遇到订阅页，感觉像被收钱，信任感未建立，转化率极低。→ 正确做法：Paywall 应在 Onboarding 目标问卷完成后、学习路径展示后插入（「你的专属路径已准备好」→ Paywall），此时用户学习动机最高，Paywall 内容也能与刚设定的目标直接挂钩，提升付费意愿（Brilliant flow 4316 完整示范了此流程）。

- **课程地图只用普通 List 展示，无锁定/解锁视觉**：课程列表无法直观传递「学习路径」概念，用户看不出哪些节点已完成、哪些可以开始、哪些还未解锁，失去了游戏地图的进度感。→ 正确做法：课程地图用可滚动列表展示节点，每个节点有清晰的三态视觉（已完成: 绿色 checkmark / 当前: 高亮 Button / 锁定: 灰色锁图标），Brilliant 更使用等轴测 3D 插图配合节点提升视觉冲击力（视觉差异化可选，但三态状态是必须的）。

- **不提供「放弃确认」就直接退出课程**：用户在课程阅读器中误碰返回手势，直接退出，当前课程进度丢失，下次需要从头开始，体验差且浪费已花时间。→ 正确做法：课程阅读器顶部的 ✕ 关闭按钮点击时必须触发 Dialog「放弃学习？当前进度将不被保存」，给用户明确提示，防止误操作丢失进度（Brilliant / Imprint 均有此确认步骤）。

- **每日通知发送「你有新课程可学」而非「连击警告」**：通用提醒缺乏紧迫感，用户容易忽略；而「你的 X 天连击今晚 23:59 前中断」对连击意识强的用户有极强的行动驱动力。→ 正确做法：通知文案应个性化且带时间紧迫感（「🔥 你的 15 天连击今晚到期，10 分钟保住它！」），并选择用户历史上活跃的时间段发送（而非固定早上 9 点），Push Notifications 支持个性化内容和定时发送。
