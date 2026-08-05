# Scenario: Mobile Productivity / Task Manager（移动端任务管理）

> **研究来源**：基于对 Structured、Joi、OKURI、(Not Boring) Habits、Checker、Haptic、Exoplan 等真实 iOS 产品 flow 和页面的横向分析抽象，不代表任何单一产品的具体实现。

---

## Identity

**Platform**: Mobile (H5 / React Native)
**Definition**: 以任务创建与追踪为核心的移动端生产力 App，用户可以快速捕捉任务、按日/周维度规划时间、配置重复习惯，并通过日视图时间轴管理每天的工作计划。

**Canonical Examples**: Todoist、Things 3、TickTick、Structured、(Not Boring) Habits

**Not this scenario if**:
- 产品是团队协作项目管理工具（Jira/Linear/Trello 风格，以看板/Sprint 为核心）
- 产品是日历工具（Google Calendar/Apple Calendar，以事件/邀请为核心而非任务）
- 产品是笔记工具（Notion/Obsidian，以文档结构为核心）
- 产品是企业工单系统

---

## User Profile

| 维度 | 内容 |
|---|---|
| **主要角色** | 个人效率用户（每日计划者）/ 习惯养成用户（打卡追踪者）|
| **核心目标** | 不遗漏任何待办事项 / 把任务分配到合适的时间 / 建立可重复的日常习惯 |
| **心智模型** | 纸质 To-Do 列表的数字化升级：快速写下 → 分配时间 → 划掉已完成 |
| **使用频率** | 高频（每天早晨规划 + 全天查看完成状态）；每次使用 2-10 分钟 |
| **决策模式** | 计划驱动型：主动建立清单并按优先级执行，而非被通知被动触发 |
| **容错期望** | 中：任务误删须有确认弹窗；已完成任务可撤销（Undo Complete）；无需草稿保存（任务很短） |

---

## IA Template

**导航模式**: Bottom Tab Bar（4-5 个 Tab）

```
Tab 1: 今日 / Today   — 日视图（时间轴 + 当日任务列表）
Tab 2: 收件箱 / Inbox — 未分配日期的任务收集
Tab 3: 日历 / Calendar — 周/月日历视图
Tab 4: 习惯 / Habits  — 习惯追踪 Grid/List
Tab 5: 设置 / Settings — 账户 + 主题 + 通知
```

**选择建议**: 纯任务 App → Today + Inbox + Calendar 三 Tab；兼有习惯追踪 → 增加 Habits Tab；轻量版 → Today Tab 单屏（类 OKURI 风格）

**页面层级**: 2-3 级
```
L1: 日视图 / Inbox（Tab 主屏）
L2: 任务详情（Task Detail，全屏推入或大 Sheet）
L3: 子任务编辑 / 重复配置子选择器（叠加 Sheet 或 Popover）
```

**权限流结构**:
```
Notifications（任务提醒）:
  → 创建第一个提醒（Alert）时触发系统通知权限弹窗
  → 或 Onboarding 完成后单独询问

Calendar Access（导入日历事件）:
  → 首次进入日历视图时请求，说明页描述「同步现有日历事件」

Location（位置提醒，可选）:
  → 部分高级 App 支持「到达某地点时提醒」，首次配置时请求
```

**数据密度**: 低-中
- 日视图：时间轴（竖向，每小时格）+ 任务卡片（横贯时间槽）
- Inbox：简洁列表（圆形 Checkbox + 任务标题 + 颜色标签 + 时长估计）
- 习惯追踪：Grid 或 List，每条习惯含图标 + 进度（Streak / 热力图）

**主要容器模式**:
| 场景 | 容器 |
|---|---|
| 快速添加任务 | Bottom Sheet（半屏，键盘即弹）|
| 完整任务配置（重复/提醒/子任务）| Bottom Sheet（大，或全屏 Push）|
| 重复频率子选择 | Popover 或叠加半屏 Sheet |
| 任务操作菜单（完成/删除/编辑）| Bottom Sheet（Action Sheet 样式，4选项）|
| 删除任务确认 | Dialog |
| 习惯创建 | 全屏逐步引导（Stepper 式全屏页）|
| 完成习惯 | 原地 Checkbox 交互（无 Modal）|

**导航骨架图（ASCII，日视图 Today）**:
```
┌────────────────────────────────────┐
│  Status Bar                         │
├────────────────────────────────────┤
│  今日  周一，1月6日        [···]   │  ← NavigationBar
│  ┌─────────────────────────────┐   │
│  │ M  T  W  T [F] S  S        │   │  ← Week Strip（日期选择）
│  └─────────────────────────────┘   │
├────────────────────────────────────┤
│  08:00 │                           │
│  09:00 │ ████ 晨间例会    0:30     │  ← 任务卡片（彩色）
│  10:00 │                           │
│  11:00 │ ████ 撰写提案    1:00     │
│  12:00 │  ·  （当前时间线）         │
│  13:00 │                           │
│        │ + Add Task                │  ← 内联添加入口
│        ▼                           │
├────────────────────────────────────┤
│  Today  Inbox  Calendar  Habits  ⚙ │  ← Tab Bar
│              [+]                   │  ← FAB（全局快速添加）
└────────────────────────────────────┘
```

---

## 该场景独有的 IA/UX 决策

1. **快速添加任务必须是单步操作：FAB → 底部 Sheet → 输入标题 → 确认，不超过两个点击** — 任务管理 App 最高频的操作是「突然想到一件事，马上记下来」，用户处于碎片时间场景（会议间隙、通勤途中）。如果添加任务需要超过 2 步（如：点 + → 进入全屏页 → 填表单 → 返回），用户会选择「回头再加」而最终遗忘。正确做法：全局 FAB 点击后立即弹出底部 Sheet，键盘自动聚焦输入框，输入标题后点确认回显到列表——Joi（flow 4379）和 OKURI（flow 11865）均实现了这套「2 次点击完成创建」路径。

2. **日视图时间轴是任务管理的核心容器，不能用纯列表替代** — 纯列表（无时间维度）无法让用户感知「今天的时间还够不够」，是导致 overcommit（计划安排太多）的主要设计原因。竖向时间轴（每小时一格，任务卡片横跨时间槽）让用户看到任务密度和空余时间，支持长按拖拽重排——Structured（flow 3264）是移动端竖向时间轴的完整实现参考，包含冲突警告（overlapping 提示）和实时时间线（当前时间红线）。

3. **任务完成/删除操作必须用底部 Action Sheet 而非全屏页，保持当前视图不变** — 用户完成或删除任务时不应被迫离开日视图/Inbox——否则每次完成一条任务都需要导航返回，严重破坏「批量处理任务」的流畅感。正确做法：点击任务行弹出底部 Action Sheet（完成/删除/编辑/更多四选项），操作后 Sheet 收起，任务状态原地更新（划线/移入 Completed 分组）——Structured（flow 3296）是标准实现，完成后任务立即划线并移入 Inbox 底部 Completed 分组。

4. **重复任务配置必须在单一 Sheet 内完成，不能跳转多个子页** — 任务重复配置（频率 + 间隔 + 星期 + 提醒）是任务创建中最复杂的部分，但不应因此打断用户的创建流程。正确做法：在同一个 Task 创建 Sheet 内用分段控件（Segmented Control）选频率（Once/Daily/Weekly/Monthly），用 Chip 组件选星期，用 Stepper 调间隔，提醒用内联增删列表——Structured（flow 3276，6 屏）是在单一 Sheet 内完成全部配置的完整实现，无需跳转子页面。

5. **习惯打卡的交互必须强调「仪式感」，不能是普通 Checkbox** — 习惯追踪 App 的核心差异点在于：普通任务完成后「一次性消除」，而习惯需要「每天都来打卡」的持续激励。普通 Checkbox 没有任何仪式感，用户完成后不会有成就感。正确做法：习惯打卡用大圆形按钮（强调视觉重量）+ 按压交互（长按/按压触发，而非单点）+ 完成动画（粒子/颜色填充），加上底部日期条显示本周连续打卡记录（Streak）——(Not Boring) Habits（flow 5055）是高仪式感打卡交互的标准实现。

---

## Canonical Flows

> 以下 flow 基于 7 个真实产品样本横向分析抽象。括号内标注「行业共识」表示 3 个以上产品采用相同模式。

---

### Flow 1: 快速添加任务（Quick Task Capture）

**在此场景的特殊性**: 「快速捕捉」是任务管理 App 最高频的单次操作，设计目标是让用户从「想到一件事」到「任务已记录」之间的摩擦趋近于零。关键差异：只要求输入标题，其他属性均为可选且可在事后编辑；底部 Sheet 而非全屏页（保留当前视图上下文）；键盘自动聚焦；添加后无跳转，任务立即出现在当前列表——OKURI 和 Joi 均体现了「2 次点击完成」的极简路径。

**行业共识**：Joi（flow 4379）、OKURI（flow 11865/11866）、Structured（flow 3296）均采用「FAB → 底部 Sheet（键盘弹出）→ 输入标题 → 确认」的最短添加路径。

**Entry**: 任意 Tab → 右下角 FAB（+）或页面内联「+ Add Task」行

```
Screen 1: 日视图 / Inbox（当前视图）
  主操作: 点击 FAB 发起快速添加
  关键组件:
    - FAB（右下角，圆形 +，主色，z-index 浮于 Tab Bar 上方）
    - 内联入口（列表最末行）: 「+ 添加任务」（灰色文字 + + 图标）
    - 当日任务列表 / Inbox 列表（当前状态）
  → 点击 FAB 或内联入口: Bottom Sheet 弹出 → Screen 2

Screen 2: 快速添加 Sheet
  主操作: 输入任务标题并确认
  容器: Bottom Sheet（半屏，随键盘上移）
  关键组件:
    - TextInput（单行，「任务名称...」placeholder，autofocus，键盘立即弹出）
    - 快捷属性栏（TextInput 下方，单行图标组）:
        Button（📅 日期，点击 → DatePicker Popover）
        Button（⏰ 提醒，点击 → 时间选择 Popover）
        Button（🔄 重复，点击 → 频率选择 Popover）
        Button（🎨 颜色，点击 → 颜色选择器）
        Button（📋 列表/项目，点击 → 项目选择 Sheet）
    - Button（「完成」/ 「✓」，右上角或键盘工具栏右侧）
    - [可选] Button（「添加更多选项」，文字链接，点击 → Screen 3 全屏配置）
  → 输入标题 + 点击「完成」: Sheet 收起，任务立即追加到列表顶部或对应日期，无跳转
  → 点击「添加更多选项」: Sheet 升级为全屏 Task Detail（Screen 3）
  → 点击 Sheet 外区域 / 向下拖拽: Sheet 收起，任务不保存

Screen 3: 全屏任务详情（可选，从「添加更多选项」进入）
  主操作: 配置任务完整属性
  容器: 全屏 Push 页或大 Bottom Sheet（Large）
  关键组件:
    - NavigationBar: Button「取消」（左）+ 标题「新任务」+ Button「保存」（右，disabled 直到标题非空）
    - TextField（任务标题，必填，大号字体）
    - TextArea（备注/描述，可选，多行）
    - Section「时间」: 日期选择器（Inline DatePicker 或点击后 Wheel Picker）+ 时长估计（Stepper）
    - Section「重复」: → 打开重复配置子 Sheet（见 Flow 2 Screen 2a）
    - Section「提醒」: Alert 列表（内联增删）
    - Section「颜色」: 色块横排，点击选中（圆形选中态）
    - Section「子任务」: 子任务列表（内联 + 添加行）
  → 点击「保存」: 任务保存，返回上一屏，任务出现在列表
```

**Exit State**:
- ✅ 快速添加：Sheet 收起，任务顶部插入列表（或分配到选定日期），无提示
- ✅ 详细配置：保存后返回日视图，任务卡片出现在对应时间槽
- ↩ 取消：Sheet 收起，无任何变化

---

### Flow 2: 任务属性配置（Task Creation with Properties）

**在此场景的特殊性**: 任务的「重复频率」和「提醒」配置是任务管理 App 与简单 To-Do 列表的核心差异——正确的重复任务设计能让用户从「每次手动添加」解放出来。关键设计挑战：重复配置有多个维度（频率 × 间隔 × 星期几），必须在单一 Sheet 内完成而不打断创建流程。Structured（flow 3276）是最完整的参考：Segmented Control 选频率 → Chip 选星期 → Stepper 调间隔 → 内联 Alert 列表，全部在同一 Sheet 内完成。

**行业共识**：Structured（flow 3276/3279/3281）均在 Task 创建 Sheet 内配置重复/提醒，无需跳转独立子页面。

**Entry**: Flow 1 Screen 3（全屏任务详情）→ 点击「重复」Section

```
Screen 1: 任务详情（背景层，保持可见）
  关键组件（已在 Flow 1 Screen 3 描述）:
    - Section「重复」行: 当前值显示（「从不」/ 「每天」/ 「每周一、三」）
    - 点击整行: 打开 Screen 2a（重复配置 Sheet）

Screen 2a: 重复配置（Recurrence Sheet）
  主操作: 配置重复频率、间隔、适用星期
  容器: Bottom Sheet（Large）叠加在任务详情上方
  关键组件:
    - Sheet Header: 标题「重复」+ Button「完成」（右，保存并收起）
    - Segmented Control（频率类型，单选，4 个选项）:
        Once（一次性）/ Daily（每天）/ Weekly（每周）/ Monthly（每月）
    - [条件显示，Weekly 时出现] 星期选择（Chip 组，7 个）:
        Chip（S / M / T / W / T / F / S，可多选）
        已选状态: 主色填充背景
    - [条件显示，非 Once 时出现] 间隔 Stepper:
        Label「每 X 天 / 周 / 月重复」
        Stepper（- 和 + 按钮，中间显示当前数值，最小值 1）
    - [可选] 结束日期:
        RadioGroup（「永不结束」/ 「结束于...」/ 「重复 N 次」）
        DatePicker（条件显示，选「结束于...」时）
  → 点击「完成」: Sheet 收起，任务详情页「重复」行更新为配置摘要文字（如「每周一、三」）

Screen 2b: 提醒配置（Alert Section，内联交互）
  主操作: 添加、修改、删除任务提醒
  容器: 内联于任务详情 Sheet，不需要额外 Sheet
  关键组件（Alert Section）:
    - Alert 列表（每行）:
        时间文字（如「任务开始前 15 分钟」/ 「09:00」）
        右侧「×」删除按钮
    - Button「+ 添加提醒」（列表末行，蓝色文字）→ 点击 → Popover 或 Sheet:
        预设快捷选项: 「准时」/ 「提前 5 分钟」/ 「提前 15 分钟」/ 「提前 1 小时」/ 「自定义时间」
        自定义: Wheel Time Picker（小时 + 分钟滚动选择器）
    - 最多 3 个提醒（超出时「+ 添加提醒」禁用并显示「最多 3 个提醒」提示）
  → 点击预设快捷选项 / 选择自定义时间 + 确认: Alert 添加到列表，Popover 收起
  → 首次添加提醒时：触发系统通知权限弹窗（如未授权）
```

**Exit State**:
- ✅ 重复配置：任务详情「重复」行显示摘要；任务保存后按频率自动生成
- ✅ 提醒配置：提醒时间出现在 Alert 列表；授权通知权限后生效
- ↩ 取消：Sheet 收起，重复/提醒配置不保存

---

### Flow 3: 日视图任务管理（Daily Timeline Task Management）

**在此场景的特殊性**: 日视图时间轴是任务管理 App 区别于普通 To-Do 的核心 UX——竖向时间轴（每小时格）让用户直观看到任务密度和剩余空间，避免 overcommit。长按拖拽重排任务是移动端特有的高效操作（鼠标悬停在移动端不存在，长按是确认"我要移动这个"的标准手势）。Structured（flow 3264）展示了完整的「点击查看 → 长按拖拽 → 冲突警告 → 拖到垃圾桶删除」闭环，以及 FAB 和内联「+ Add Task」双入口共存的标准布局。

**行业共识**：Structured（flow 3264/3283）确认：Week Strip 横向日期导航固定顶部；竖向时间轴时间戳左对齐；任务完成后划线+颜色变灰；FAB 持续可见于时间轴右下角。

**Entry**: Today Tab → 日视图时间轴

```
Screen 1: 日视图（Daily Timeline）
  主操作: 浏览当日任务，完成/管理任务
  关键组件:
    - NavigationBar: 「今日」日期文字 + 右侧 ··· 操作菜单（「复制今天的任务到明天」等）
    - Week Strip（顶部横向，固定）:
        7 个日期 Chip（日 月 日期数字），当天高亮（主色圆圈）
        横向滑动可切换到其他周
    - 实时时间线（红色横线 + 当前时间文字，随时间滚动）
    - 竖向时间轴（ScrollView，每小时一格）:
        时间戳（左侧，灰色小字，如「09:00」）
        任务卡片（时间戳右侧，横跨对应时长的高度）:
          左侧彩色 accent bar（任务颜色）
          任务标题 + 时长文字（如「1:00」）
          右侧圆形 Checkbox（点击即完成）
        空时间槽: 「+ Add Task」内联文字（灰色，点击触发快速添加 Sheet）
    - 冲突警告标签（红色 「overlapping」pill，任务卡片右上角，有时间重叠时显示）
    - FAB（右下角 +，浮于时间轴上方）
  → 点击任务卡片（非 Checkbox 区域）: Bottom Sheet 弹出（Screen 2）
  → 点击圆形 Checkbox: 任务立即标记为完成（划线 + 卡片变灰 + 轻微动效）
  → 长按任务卡片: 进入拖拽模式（Screen 3）
  → 点击 FAB / 内联「+ Add Task」: 快速添加 Sheet（同 Flow 1 Screen 2）

Screen 2: 任务操作 Action Sheet
  主操作: 对选中任务执行操作
  容器: Bottom Sheet（Action Sheet 样式，半屏）
  关键组件:
    - Sheet Header: 任务名称（单行，只读，灰色小字）
    - Button「✓ 标记完成」（或「↩ 撤销完成」，已完成时）
    - Button「✏ 编辑任务」→ 进入全屏 Task Detail（Flow 2）
    - Button「📋 复制任务」→ 弹出目标日期选择 Popover
    - Button「🗑 删除任务」→ Dialog 确认（Screen 2a）
    - Button「取消」（Sheet 底部独立区）
  → 点击「标记完成」: 任务划线变灰，Sheet 收起
  → 点击「删除任务」: Screen 2a（确认 Dialog）

Screen 2a: 删除确认 Dialog
  关键组件:
    - Dialog 标题:「删除任务？」
    - 说明: 「删除后无法恢复」（普通任务）或「删除「[任务名]」，仅删除本次 / 删除所有重复」（重复任务二选一）
    - Button「删除」（danger 红色）
    - Button「取消」（取消样式）
  → 点击「删除」: 任务从时间轴移除，Toast「任务已删除 · 撤销」
  → 点击「取消」: 返回 Action Sheet

Screen 3: 拖拽重排（Drag & Drop）
  主操作: 长按任务拖拽到新时间槽
  触发: 在任务卡片上长按 0.5s
  关键组件（拖拽状态）:
    - 被拖拽的任务卡片（放大 1.05x + 轻微投影，跟随手指移动）
    - 时间轴背景（其他任务半透明）
    - 目标位置预占位（蓝色虚线矩形，显示任务将落在哪个时间槽）
    - 删除目标区（时间轴底部或角落，红色垃圾桶图标，拖到此处删除任务）
    - 实时更新的时间文字（跟随手指显示当前目标时间，如「11:30」）
  → 松手到新时间槽: 任务落到新位置，时间更新，冲突警告实时检测
  → 拖到删除目标区: 任务删除（有确认弹窗或直接删除+Toast「已删除 · 撤销」）
  → 拖到屏幕外: 取消拖拽，任务回到原位
```

**Exit State**:
- ✅ 完成任务：任务划线+灰色，Checkbox 填充，不离开时间轴视图
- ✅ 拖拽重排：任务出现在新时间槽，时间戳更新，如有冲突显示 overlapping 警告
- ✅ 删除：Toast「已删除 · 撤销」（可 Undo），任务从时间轴消失

---

### Flow 4: 习惯创建与每日打卡（Habit Creation & Daily Check-off）

**在此场景的特殊性**: 习惯追踪是任务管理 App 的重要差异化功能——普通任务完成后消失，习惯则需要「每天都回来」，因此设计核心是强化「Streak 连续感」和「打卡仪式感」。(Not Boring) Habits（flow 5055）是最有辨识度的实现：全屏黑底大字输入（去表单感）→ 圆形星期 Toggle → Wheel 时间选择器 → 进入追踪主屏，大圆形按压交互（非单点 Checkbox）。Checker（flow 6958）展示了量化习惯追踪（数值 Board），每次打卡可记录数量而非仅布尔值，适合「每天跑 X 公里」类场景。

**行业共识**：(Not Boring) Habits（flow 5055）、Haptic（flow 2101）确认：习惯命名屏用全屏/大号文字输入减少「填表单」感；圆形 Toggle 选星期（7个圆形可点击）；打卡交互强调仪式感（大圆按压/长按）；底部水平日期条显示本周打卡记录。

**Entry**: Habits Tab → 右上角「+」或空状态 CTA 「创建第一个习惯」

```
Screen 1: 习惯主屏（Habits Dashboard）
  主操作: 查看所有习惯，完成当日打卡
  关键组件:
    - NavigationBar: 「习惯」标题 + 右上角 Button「+」新建
    - 今日日期横幅（「今天 · 周一 1月6日」）
    - 习惯列表（每条习惯）:
        习惯图标（emoji 或自定义图标）+ 习惯名称
        大圆形打卡按钮（右侧，未打卡: 空圆圈；已打卡: 主色填充 + ✓）
        底部 7 天日期条（每天一个小圆点，打卡日填充颜色，断开日为灰色）
        Streak 计数（如「🔥 7天连续」，底部小字）
    - 空状态（无习惯）:
        插图 + 「还没有习惯」+ Button「创建第一个习惯」
  → 点击大圆打卡按钮: 即时动画（填充颜色 + 缩放弹跳），Streak 计数更新（Screen 2）
  → 点击「+」: 新建习惯流程 → Screen 3

Screen 2: 打卡完成动效（瞬态状态）
  主操作: 视觉反馈确认打卡成功
  关键组件:
    - 大圆按钮: 颜色填充动画（从轮廓扩散到实心，约 0.4s）
    - [可选] 粒子/confetti 动画（首次打卡或完成每周目标时）
    - Streak 数字更新: 计数 +1 数字翻滚动画
    - 底部日期条: 今天的圆点填充
    - [可选] Toast（仅在完成「7天 Streak」里程碑时）: 「🔥 连续 7 天！保持住！」
  → 动效结束后（约 0.5s）: 回到 Screen 1 状态，打卡按钮保持已打卡样式

Screen 3: 习惯创建 — 命名（Step 1/3）
  主操作: 为新习惯起名
  容器: 全屏页面（逐步引导，不是 Sheet）
  关键组件:
    - 全屏大号 TextInput（居中，24-28pt 字体，autofocus，去掉边框和 label，只有 placeholder）
        Placeholder: 「习惯名称（如：每天冥想）」
    - 下方建议列表（灰色小字，纵向滚动）:
        「每天锻炼」/ 「喝 8 杯水」/ 「读书 30 分钟」/ 「冥想 10 分钟」（点击自动填入）
    - 底部 Button「继续」（主色，全宽，有输入才激活）
  → 点击「继续」: 进入 Screen 4

Screen 4: 习惯创建 — 频率（Step 2/3）
  主操作: 选择习惯的重复星期
  关键组件:
    - NavigationBar: 「← 返回」（左）+ 进度指示（2/3 步骤条）
    - 习惯名预览（大号，居中）
    - 星期选择（7 个圆形 Chip，水平排列）:
        S / M / T / W / T / F / S
        可多选，已选: 主色填充；未选: 灰色轮廓
        快捷行（Chip 下方）: 「每天」/ 「工作日」/ 「周末」
    - 底部 Button「继续」（激活条件: 至少选 1 天）
  → 点击「继续」: 进入 Screen 5

Screen 5: 习惯创建 — 提醒时间（Step 3/3）
  主操作: 设置每日提醒时间
  关键组件:
    - NavigationBar: 「← 返回」+ 进度指示（3/3 步骤条）
    - 习惯名预览（大号，居中）
    - Toggle「开启每日提醒」（默认开启）
    - Wheel 时间选择器（小时 + 分钟滚轮，原生 iOS 样式）
        [显示条件: Toggle 开启时]
    - Button「跳过」（文字链接，跳过提醒直接完成）
    - 底部 Button「完成」（主色，全宽）
  → 点击「完成」（有提醒时）: 触发系统通知权限弹窗（首次）→ 习惯保存 → 返回 Screen 1，新习惯出现在列表
  → 点击「完成」（无提醒时）: 习惯保存 → 返回 Screen 1
```

**Exit State**:
- ✅ 习惯创建：新习惯出现在 Habits 主屏，今日打卡按钮为空圆圈（未打卡状态）
- ✅ 打卡成功：大圆填充动画，Streak +1，底部日期条今天圆点填充
- ↩ 未完成全部步骤取消：返回 Habits 主屏，习惯不保存

---

## Mobile Component Kit

按使用频率排序（基于研究样本观察）：

| 优先级 | 组件（H5 antd-mobile）| 组件（RN Gluestack/RN）| 具体用途 |
|---|---|---|---|
| ★★★ | `Popup`（half）| `BottomSheet`（half）| 快速添加任务 Sheet（键盘弹出）|
| ★★★ | `List` / `VirtualList` | `FlatList` | Inbox 任务列表（圆形 Checkbox + 标题）|
| ★★★ | `Popup`（action）| `ActionSheet` | 任务操作菜单（完成/删除/编辑/复制）|
| ★★★ | `Dialog` | `AlertDialog` | 删除任务确认（单次 / 全部重复）|
| ★★★ | `Checkbox` | `Checkbox` | 任务完成 Checkbox（圆形，大 44pt 触控区）|
| ★★ | `Segmented` | `SegmentedControl` | 重复频率选择（Once/Daily/Weekly/Monthly）|
| ★★ | `Selector` | `RadioGroup` / `Chip` | 星期选择（习惯频率 S/M/T/W/T/F/S Chip）|
| ★★ | `Stepper` | `Stepper` | 重复间隔调整（每 X 天/周）|
| ★★ | `Picker`（wheel）| `WheelPicker` / `DateTimePicker` | 提醒时间选择（Wheel 原生样式）|
| ★★ | `Toast` | `Toast` | 删除/操作完成反馈（含 Undo）|
| ★ | `Steps` | `ProgressBar` | 习惯创建步骤指示（Step 1/3）|
| ★ | `SearchBar` | `SearchBar` | 任务搜索（Inbox / 全局搜索）|
| ★ | `SwipeAction` | `Swipeable` | 任务列表左滑（删除/推迟）|
| ★ | `InfiniteScroll` / 自定义 | `FlatList` 自定义 | 竖向时间轴（每小时格，长按拖拽）|

---

## Anti-Patterns

- **添加任务需要超过 2 次点击才能开始输入**：用户在碎片时间（通勤/会议间）想快速记下任务，超过 2 步的创建路径会导致大量「回头再加」最终遗忘的任务。→ 正确做法：FAB → 底部 Sheet（键盘立即弹出）→ 输入标题 → 确认，整个流程 2 次点击（Joi flow 4379、OKURI flow 11865 均验证）。

- **任务操作（完成/删除）跳转到独立页面**：每次完成一条任务都需要进入详情页再返回，极大干扰批量处理任务的流畅感。→ 正确做法：点击任务行弹出底部 Action Sheet（完成/删除/编辑/复制），操作后 Sheet 收起，任务状态原地更新，不切换视图（Structured flow 3296）。

- **重复任务配置需要跳转多个子页面**：用户在配置「每周一三五提醒」时需要跳转 3 个不同页面，完成配置后不记得自己在哪里，严重影响创建流畅感。→ 正确做法：在单一 Task Sheet 内用 Segmented Control + Chip + Stepper 组合完成全部重复配置，不跳转子页（Structured flow 3276）。

- **日视图只显示任务列表，没有时间维度**：用户看不到任务在一天中的时间分布，无法感知是否 overcommit（计划了超过 8 小时的任务）。→ 正确做法：竖向时间轴（每小时一格），任务卡片高度对应时长，实时时间红线标注「现在」，让用户一眼看出剩余时间（Structured flow 3264）。

- **习惯打卡用普通小 Checkbox，无仪式感**：用户每天打卡后没有成就感，缺乏持续回来的动力，导致习惯追踪功能留存率极低。→ 正确做法：大圆形打卡按钮（44-60pt）+ 颜色填充动画 + Streak 计数 + 7天日期条，打卡变成每日「仪式」而非机械操作（(Not Boring) Habits flow 5055）。

- **删除重复任务只有「全部删除」一个选项**：用户可能只想删除「这周三那次」，而不是整个重复系列。→ 正确做法：删除重复任务的 Dialog 提供两个选项——「仅删除本次」和「删除所有重复」，让用户精确控制操作范围（Structured flow 3262）。

- **没有 Undo 机制**：用户误触「完成」或「删除」后没有任何恢复方式。→ 正确做法：完成任务支持「Undo Complete」（3秒内可撤销，时间轴右下角 Toast「已完成 · 撤销」）；删除任务同样提供 Undo Toast，3秒后永久删除。
