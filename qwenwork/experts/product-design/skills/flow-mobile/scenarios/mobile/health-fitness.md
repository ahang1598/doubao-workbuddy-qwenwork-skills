# Scenario: Mobile Health & Fitness（健康与运动追踪 App）

> **研究来源**：基于对 GO Club、Miles、The Outsiders、Gentler Streak、GrowPal、Strava、komoot 等 7 个真实 iOS 产品 flow 和页面的横向分析抽象，不代表任何单一产品的具体实现。

---

## Identity

**Platform**: Mobile (H5 / React Native)
**Definition**: 以运动追踪和健康数据可视化为核心的移动端消费者应用，用户通过健康平台 API 读写步数/心率/运动数据，记录运动会话，查看健康进度，完成个性化目标。

**Canonical Examples**: Apple Fitness+、Strava、Gentler Streak

**Not this scenario if**:
- 以营养/饮食记录为主（如 MyFitnessPal，属于 Health & Wellness 中的 Nutrition 子集）
- 以医疗诊断/病历管理为主（改用 web/healthcare）
- 以团队/教练管理为主（B2B 运动管理平台，属于 web/saas-management 变体）
- 主要在 Web 端使用（改用 web/data-analytics 或 web/healthcare）

---

## User Profile

| 维度 | 内容 |
|---|---|
| **主要角色** | Active User（主动锻炼者）/ Casual Tracker（日常步数/睡眠追踪者）/ Health Optimizer（关注 VO2 Max / HRV 等指标者）|
| **核心目标** | 完成今日运动目标 / 记录一次锻炼 / 查看近期健康趋势 |
| **心智模型** | 熟悉健康追踪生态，期待「闭环可视化」（完成 Ring → 得到反馈）；不想输入太多手动数据（偏好自动追踪）|
| **使用频率** | 高频（每天打开 1-3 次）：早晨查看今日目标 / 运动中 / 运动后复盘 |
| **决策模式** | 目标驱动：「我今天走了多少步」「这周热量消耗怎样」，而非探索发现型 |
| **容错期望** | 运动记录误操作可编辑，但删除健康数据需警告（影响第三方 App）；权限可随时在系统设置更改 |

---

## IA Template

**导航模式**: Tab Bar（底部 Tab Bar，3-5 项，各产品差异较大）

典型结构：
```
Tab 1: 今日 / Today    — 今日目标进度 + 快速操作（开始运动）
Tab 2: 历史 / Activity — 运动记录列表 + 周/月统计
Tab 3: 进度 / Progress — 长期趋势图表 + 指标卡片
Tab 4: 发现 / Explore  — 计划/训练库（部分产品有）
Tab 5: 我的 / Profile  — 目标设置 + 健康平台集成 + 账户
```

**页面层级**: 3 级
```
L1: Tab 根页（Today / Activity / Progress）
L2: 详情页（单次运动详情 / 指标详情页）
L3: 操作面板（添加运动 Bottom Sheet / 日期选择器）
```

**权限流结构**（健康类 App 权限较复杂）:
```
健康数据（核心权限，分类授权）:
  → 自定义说明页 → 系统健康权限授权（iOS: HealthKit 分类授权；Android: Health Connect）
  → 类别: 步数 / 运动能量 / 心率 / 睡眠 / 运动记录...

Notifications:
  → 说明页（「每日目标提醒」「运动完成通知」）→ 系统通知权限弹窗

Location（运动 GPS 追踪）:
  → 说明页（「记录跑步路线」）→ 浏览器 Geolocation API / Expo Location（whenInUse）
  → always（后台 GPS）需二次申请（系统限制）

Motion & Fitness（步数计步器）:
  → 系统弹窗（首次读取计步器时自动触发）
```

**数据密度**: 中（Dashboard 以卡片 + 进度可视化为主，细节页以图表为主）
- 核心视图：环形进度（`Progress` 圆形 / `Gauge`）+ 折线图/柱状图（图表库）+ Cards
- 辅助视图：`List`（运动历史记录）
- 不使用：多列 Table（Web BI 工具专属）

**主要容器模式**:
| 场景 | 容器 |
|---|---|
| 添加手动运动记录 | Bottom Sheet（large）|
| 运动会话进行中 | Full-screen Modal（独立全屏界面）|
| 日期范围选择 | Bottom Sheet + 日历组件 |
| 权限说明 | 全屏静态页（onboarding 步骤内）|
| 删除运动记录确认 | Dialog（明确说明健康数据影响）|
| 指标详情 / 钻取 | Stack Push（新页面）|
| 计划选择 / 难度设置 | Action Sheet 或 Bottom Sheet |

**导航骨架图（ASCII）**:
```
┌────────────────────────────────────┐
│  Status Bar（时间 / 信号 / 电量）    │
├────────────────────────────────────┤
│  今日目标                    [编辑]  │  ← Tab 1: Today
│                                    │
│  ╔════════════════╗                │
│  ║  Activity Ring  ║  步数: 6,234   │
│  ║  (环形进度 ×3)  ║  热量: 342     │
│  ║                ║  运动: 28 min  │
│  ╚════════════════╝                │
│                                    │
│  [▶ 开始运动]（Primary Button）     │
│                                    │
│  近期活动                           │
│  ┌─ 今天 09:30 跑步 5.2km ─ 28min ─┐│
│  └─ 昨天 07:15 散步 3.8km ─ 42min ─┘│
│                                    │
├───┬────┬──────┬──────┬─────────────┤
│今日│活动 │ 进度  │ 发现 │  我的        │
└───┴────┴──────┴──────┴─────────────┘
```

---

## 该场景独有的 IA/UX 决策

1. **健康数据权限说明页（自定义说明）必须先于系统授权弹窗，且按数据类别分场景解释** — 系统健康授权表单一次展示 6-10 个数据类别开关（步数/心率/睡眠/运动能量…），用户不知道为什么需要如此多种数据，默认倾向关闭大多数。自定义说明页必须在触发系统弹窗前展示，按类别说明用途（「步数用于计算每日目标」「心率用于卡路里消耗精度」），让用户理解价值后再授权——这是健康类 App 区别于所有其他场景的「最高密度权限请求模式」，且每类权限的说明页必须独立（不可合并为一页笼统说明）。GO Club（flow 6349）/ Miles（flow 6704）均有此完整实现，是行业参照。

2. **Active Session 界面必须屏幕常亮 + 计时器 ≥60pt + 长按 2 秒停止，完全区别于普通内容页** — 运动会话进行中是移动端中唯一必须「屏幕常亮」的场景（RN：`expo-keep-awake`；H5：`navigator.wakeLock.request('screen')`）——用户跑步途中无法每 30 秒解锁一次手机查看配速。计时器字号必须 ≥60pt 等宽字体（户外强光下可读），「停止」按钮必须长按 2 秒防误触（运动中晃动极易误触单击按钮）——这些规则与普通内容页「正常字号 + 单击操作」完全相反，是运动 App 独有的 Full-time-critical UI 约定（Strava / komoot 均采用此规格）。

3. **删除健康数据必须在 Dialog 中明确警告跨系统影响** — 健康数据具有跨 App 影响性——删除某次运动记录会同步从健康平台（HealthKit / Health Connect）数据库删除，影响 Apple Watch 活动圈、第三方营养 App 的历史统计。Dialog 警告文字必须明确说明「此操作将同步从健康平台移除，不可撤销」，而非通用的「删除后无法恢复」——这是健康类 App 独有的数据完整性约定，普通列表删除无需关心跨系统影响，但健康数据删除的后果范围超出当前 App 边界。

4. **Progress 页以「周」为最小时间粒度，配合 ← 上周/下周 → DateRange Navigator** — 运动健康数据的最有意义周期是「一周」——单日数据波动大，看不出趋势；月视图粒度太粗，失去单次运动细节。周视图核心结构是三层：顶部 7 个迷你环形进度（每天一个，完成率用颜色深浅表示）+ 折线图（本周每日变化）+ DateRange Navigator（← 上周 | 本周 | 下周 →，支持翻查历史）。The Outsiders / GrowPal / Gentler Streak 均采用此周视图结构——月视图仅适合「年度总结」类场景，日常查看首选周视图，这是健康 App 区别于 Web BI Dashboard 的时间粒度选择共识。

5. **Onboarding 必须「个性化问卷先于权限请求」，用目标建立连接再解释为何需要数据** — 健康 App 有两种 Onboarding 顺序：先权限 vs 先问卷。行业研究（GO Club flow 6349 / Miles flow 6704）一致验证：先用 2-3 步个性化问卷（目标类型/当前体能水平/期望提醒方式）建立「产品了解用户的感知」后，用户对健康数据授权的理解和意愿显著更高——问卷答案提供了「为什么需要这些数据」的具体语境（「根据你的步行目标，我们需要读取你的步数」），而直接弹出系统权限表单会让用户感觉「还不了解产品就被索取权限」，拒绝率明显上升。

---

## Canonical Flows

> 以下 flow 基于 7 个真实产品样本横向分析抽象。括号内标注「行业共识」表示 3 个以上产品采用相同模式。

---

### Flow 1: Onboarding with Permission Setup（新用户引导 + 权限授权）

**在此场景的特殊性**: 健康 & 运动 App 的 onboarding 是移动端生态中**权限请求密度最高**的场景——通常需要依次请求健康数据（含多个数据类别）/ 通知 / 位置 / 运动数据 4 类权限，每类都需先展示自定义说明页再触发系统弹窗。GO Club 的 24 屏 onboarding（flow_id 6349）是行业最完整的范例：先个性化问卷（3 步），再权限序列，再计划生成 loading 页，最终落地 Dashboard。关键设计决策是**问卷先于权限**——用户先理解产品价值，再理解为什么需要这些权限，显著提升授权率。「继续」按钮在未选中选项时保持 disabled 是强制完成的行业共识。

**行业共识**：GO Club（flow 6349）和 Miles（flow 6704）均在健康数据请求前展示「连接 Apple Health 好处」说明页；两者均用生物识别完成登录。

**Entry**: 首次启动 App

```
Screen 1: Welcome / Sign-In
  主操作: 选择登录方式
  关键组件:
    - 品牌插图 / 价值主张 Image
    - Text（App 名称 + 1句 tagline）
    - Button("使用 Apple 登录 / Google 登录", 主色)
    - Button("使用邮箱注册", 次要)
    - Button("已有账号？登录", 文字按钮)
  → 点击社交登录: 触发系统 OAuth 授权
  → 验证成功: 进入 Screen 2

Screen 2-4: 个性化问卷（3 步，每步一个问题）
  主操作: 选择答案 → 点击「继续」
  关键组件（每步）:
    - 顶部线性进度条（step X of 3）
    - Text（问题：如「你的主要健康目标是？」）
    - 选项卡片列表（每项: 图标 + 标题 + 描述，单选）
    - Button("继续", 主色，.disabled 未选时)
  → 选中选项后「继续」激活
  → 每步完成推进下一题

Screen 5: 健康数据权限说明页
  主操作: 点击「连接健康平台」→ 触发系统健康权限授权
  关键组件:
    - 大图标（心形 / 健康图标）
    - Text（标题：「连接健康数据」）
    - Text（说明：「我们会读取 步数 / 运动 / 心率 数据来生成你的个性化计划，仅在 App 使用期间访问」）
    - 数据类别清单（步数 ✓ / 运动时长 ✓ / 心率 ✓）
    - Button("连接健康平台", 主色)
    - Button("稍后跳过", 文字按钮)
  → 点击「连接」: 触发系统健康权限授权（用户可按类别开关）
  → 授权完成（全部 / 部分）: 进入 Screen 6

Screen 6: 计划生成（Loading）
  主操作: 等待个性化计划生成完成
  关键组件:
    - 圆形 Loading 动画（居中）或自定义动画
    - Text（「正在为你生成专属计划...」）
    - 渐进式 Text（「分析目标 ✓」「计算步数目标 ✓」「生成周计划 ✓」）
  → 完成后自动跳转 Screen 7

Screen 7: Dashboard（初始状态）
  主操作: 查看今日目标 / 开始使用
  关键组件:
    - 环形进度（×3 Activity Rings 风格：运动 / 步数 / 热量，初始值均为 0%）
    - Cards（今日目标: 步数目标 XXXX 步 / 热量目标 XXX 千卡）
    - Button("开始第一次运动", 主色)（CTA）
    - Toast（「计划已就绪！」）
  Exit: 用户开始使用 App
```

**Exit State**:
- ✅ 健康数据全授权：Dashboard 显示今日实时步数数据
- ⚠️ 部分授权：Dashboard 可用，数据类型受限，顶部 Banner 提示「部分数据不可用」
- ↩ 跳过：Dashboard 可用，步数等自动数据显示「--」，手动记录功能仍可用

---

### Flow 2: Start & Complete Workout Session（开始 + 完成运动会话）

**在此场景的特殊性**: 运动会话的 UI 有三种截然不同的状态，需分别设计——**开始前**（选择运动类型、目标距离/时间）/ **进行中**（大字计时、实时数据、停止控制）/ **结束后**（会话总结 + 分享）。「进行中」屏幕是健康类 App 独有的 full-time-critical UI，必须**屏幕常亮 + 单手操作优化 + 大字**，与普通内容展示页完全不同。The Outsiders 的 Add Workout 底部表单用了感知强度滑块（彩虹渐变），比简单的 1-10 数字输入更直观。GPS 权限在首次运动 GPS 记录时触发。

**行业共识**：活跃会话屏幕使用大号计时器（≥60pt）+ 暗色全屏背景（减少视觉干扰，户外强光下对比度高）；暂停/结束控制器用底部大按钮（Strava、The Outsiders、komoot 均如此）。

**Entry**: Today Tab → 点击「▶ 开始运动」按钮

```
Screen 1: 选择运动类型
  主操作: 选择运动类型 → 点击「开始」
  关键组件:
    - Bottom Sheet 或 Full-screen Modal 进入创建界面
    - Grid（2列）或 List（运动类型: 跑步/步行/骑行/力量/瑜伽...）
    - 每项: 图标 + 类型名 + 最近记录
    - 自定义目标（可选）: 目标距离输入 + 预计时长选择
    - Button("开始", 主色)
  → 点击「开始」: 进入 Screen 2（Active Session）

Screen 2: 运动进行中（Active Session）
  主操作: 查看实时数据 / 暂停 / 停止
  关键组件（全屏深色界面）:
    - 主计时器（HH:MM:SS，超大字号 ≥60pt，等宽字体）
    - Metrics Cards（2-3 个主要指标，大字体: 距离 / 配速 / 心率）
    - Map（地图组件，实时 GPS 轨迹，若有 Location 权限）
    - 底部控制区（固定在视口底部）:
        Button（暂停/继续，圆形大按钮）
        Button（停止，圆形大红按钮，需长按 2 秒防误触）
    - 屏幕常亮: `expo-keep-awake` keepAwakeAsync / `navigator.wakeLock`
  → 点击「暂停」: 计时暂停，按钮变「继续」+ 「提前结束」
  → 长按「停止」（2 秒）: 进入 Screen 3

Screen 3: 运动总结（Session Summary）
  主操作: 查看数据 / 分享 / 保存
  关键组件:
    - 运动类型标题 + 时间戳（「今天 09:30 · 跑步」）
    - Stats Grid（2×3 或 3×2）：总距离 / 总时长 / 平均配速 / 热量 / 步数 / 最高心率
    - Map（完整 GPS 轨迹，静态截图效果）
    - 进度条（目标完成率：已跑 5.2km / 目标 5km ✓）
    - 操作区：
        Button("分享", 次要)（系统分享面板 / `navigator.share`）
        Button("保存", 次要)
    - Toast / Banner（「运动已自动保存到健康平台」）
  → 点击「保存」: 写入健康平台，返回 Today Dashboard
  → 点击「分享」: 系统分享面板
  Exit: Today Dashboard，环形进度更新
```

**Exit State**:
- ✅ 正常完成：数据写入健康平台，Dashboard 环形进度动态更新（动画效果）
- ❌ 无 GPS 信号：距离/地图显示「--」，其他数据正常记录
- ↩ 中途放弃（会话 < 1 分钟）：弹 Dialog「时间不足 1 分钟，是否放弃此次记录？」→「放弃」/「继续」

---

### Flow 3: Review Weekly Progress（查看周进度与历史趋势）

**在此场景的特殊性**: 移动端健康类 App 的进度页通常以**周为单位**展示趋势（而非月/年），可通过日历行左右滑动切换周，每天有一个状态圆点（活跃/休息/未追踪）。The Outsiders（Progress Tab）展示了三层深度：周概览折线图 → 日选择器 → 单日指标卡片（Average / Max / Min），这是该场景的行业模板。图表使用图表库（RN: `react-native-gifted-charts` / `victory-native`；H5: `echarts` / `recharts`），不需要自行实现。**环形进度**用于单个指标的仪表盘风格展示（如 VO2 Max、HRV），线性进度条用于目标完成度（如「6 km / 10 km 今日步数目标」）。

**行业共识**：The Outsiders / GrowPal / Gentler Streak 均使用周视图 + 日历行 + 折线图；Stack Push 进入单次运动详情是移动端通用模式。

**Entry**: Tab Bar → 点击「进度」Tab

```
Screen 1: 进度概览（Progress Dashboard）
  主操作: 查看本周趋势 / 切换时间范围
  关键组件:
    - 标题「进度」/ 「Progress」+ 本周日期范围如「2026/4/7 – 4/13」
    - DateRange Navigator（← 上周 | 本周日期 | 下周 →，左右箭头）
    - 周环形总结: 7个迷你环形进度（每天一个，颜色深浅表示完成率）
    - 折线图 / 柱状图（显示本周每日步数或距离变化）
    - Metrics Overview Section（3 张卡片: 本周总步数 / 总运动时长 / 平均每日步数）
    - 「OVERVIEW」Section Title + Cards（Average / Max / Min）
  → 点击单日圆点: 高亮该日，图表显示该日数据点（Screen 2）
  → 点击「← 上周」: 周视图切换动画（300ms ease-out）

Screen 2: 单日活动详情（Day Detail）
  主操作: 查看该日所有运动记录
  关键组件:
    - Stack Push（页面标题显示日期）
    - 环形进度（当日 Ring 进度: 运动 / 步数 / 热量，带百分比数字）
    - List（当日运动记录列表）:
        每行: 运动类型图标 + 运动名称 + 时长 + 距离 + 时间戳
        左滑: 删除（附 Dialog 二次确认）
    - Empty 空状态（当日无记录: 「休息日 🛌」+ 「记录一次运动」CTA）
  → 点击某运动记录: Stack Push → Screen 3

Screen 3: 单次运动详情（Workout Detail）
  主操作: 查看完整运动数据
  关键组件:
    - 运动类型 + 日期（页面标题）
    - Map（GPS 轨迹，静态）
    - Stats Grid（距离/时长/配速/热量/步频/心率区间）
    - 折线图（心率随时间变化，含心率区间色带）
    - Button("分享", 次要)（分享该次运动）
    - Button("删除", danger 样式，底部，触发 Dialog 警告）
  Exit: 点击返回 → 回到 Day Detail 或 Progress 概览
```

**Exit State**:
- ✅ 正常浏览：历史数据展示，图表平滑切换
- 空状态（新用户无数据）：Progress Dashboard 展示 「记录你的第一次运动」引导 CTA
- ↩ 删除记录后：List 即时移除该行，健康平台数据同步删除，Toast「已从健康平台删除」

---

### Flow 4: Browse & Start a Training Plan（探索训练计划 + 问卷生成 + 开始计划）

**在此场景的特殊性**: 健康 App 的「发现训练计划」是区别于「记录单次运动」的独立用户旅程——用户不是自己录入数据，而是从 App 提供的计划库中选择一套结构化计划（如「12 周跑步入门」「肌肉增长中级计划」），通过**短问卷**（目标 / 体能水平 / 可训练天数）让 App 生成专属版本后保存至个人库。**Dropset（flow 6512，21 屏）**是该模式的最完整实现：问卷驱动（goal → motivation → height/weight → training days，7 步单问题页），滚轮 Picker 输入体重/身高，禁用状态 CTA（训练日至少选 1 天才激活），计划生成 Loading 后进入计划详情（总览 → 每日练习列表 → 单个动作详情）。**Train Fitness（flow 7168，3 屏）**展示了多 Tab 运动搜索：Exercises / Templates / Workouts / People，每 Tab 有 3 个过滤 Chip（肌肉群 / 器械 / 类型），搜索结果行带缩略图 + 肌肉群标签 + 右侧预览按钮。这两个模式可组合为「先浏览 → 选中模板 → 问卷个性化 → 生成计划」四步完整 flow。

**行业共识**：Dropset（flow 6512）和 Train Fitness（flow 7134）均使用「问卷先于计划生成」模式，CTA 在必填项未完成时为 disabled 状态；Train Fitness（flow 7168）、Strava 均将计划/模板与单次运动记录分开置于 Explore Tab，不与 Today Dashboard 混用。

**Entry**: Tab Bar → 点击「发现 / Explore」Tab

```
Screen 1: Explore 首页（计划浏览）
  主操作: 浏览推荐计划 / 搜索计划或动作
  关键组件:
    - SearchBar（顶部，placeholder「搜索计划、动作、模板」）
    - 内容 Tab 横排（水平可滑动）:
        Tab("动作", 选中) / Tab("模板") / Tab("我的计划") / Tab("发现人")
    - 过滤 Chip 行（3 个，横向排列）:
        Chip("肌肉群") / Chip("器械") / Chip("类型")（点击弹出 Bottom Sheet 选项）
    - List（搜索结果 / 浏览列表）:
        每行: 缩略图（运动姿势图）+ 动作/计划名称 + 主要肌肉群标签 + 右侧预览按钮（圆形波形图标）
    - 分组 Section Header（如「推荐计划」「热门模板」「本周新增」）
  → 点击 Tab("模板"): 切换为计划模板列表（带周数/天数/难度标签）
  → 点击计划卡片: Stack Push → Screen 2
  → 搜索输入: 实时过滤当前 Tab 的结果

Screen 2: 计划详情（Plan Detail）
  主操作: 查看计划概览 → 决定「生成我的版本」
  关键组件:
    - 顶部 Hero Image（计划封面 / 运动插图）
    - 计划标题（如「12 周力量入门计划」）
    - 标签行: Badge("12 周") / Badge("每周 4 天") / Badge("中级")
    - 文字描述（2-3 句，计划目标与适合人群）
    - 「本周训练预览」折叠区:
        - SectionList（按天分组）:
            每组 Header: 「周一 / 上身力量」
            每行: 动作缩略图 + 动作名 + 组数×次数（如「4 × 8」）
    - 底部固定操作区（Safe Area 内）:
        Button("生成我的计划", 主色)（全宽）
        Button("收藏", 次要)（与生成并排）
  → 点击「生成我的计划」: Full-screen Modal → Screen 3（问卷）

Screen 3-A: 目标选择（问卷 Step 1/4）
  主操作: 选择主要目标 → 点击「继续」
  关键组件:
    - 顶部线性进度条（step 1 of 4）
    - Text（问题：「你的主要训练目标是？」）
    - 选项卡片列表（大 Tap 目标，单选）:
        「增肌 / Muscle Gain」/ 「减脂 / Fat Loss」/ 「提升耐力 / Endurance」/ 「维持健康 / General Fitness」
        每项: 图标 + 标题 + 一句描述
    - Button("继续", 主色，未选时 .disabled)
  → 选中后「继续」激活，进入 Screen 3-B

Screen 3-B: 体能水平（问卷 Step 2/4）
  关键组件（同上结构）:
    - 选项: 「初学者（< 6 个月经验）」/ 「中级（6-24 个月）」/ 「高级（> 2 年）」

Screen 3-C: 身体数据（问卷 Step 3/4）
  主操作: 输入身高体重（滚轮 Picker）
  关键组件:
    - 身高 Picker（滚轮，cm，默认 170）
    - 体重 Picker（滚轮，kg，默认 65）
    - 单位切换（cm/in、kg/lb，右上角 Segmented）
    - Button("继续", 主色)

Screen 3-D: 训练天数（问卷 Step 4/4）
  主操作: 选择每周可训练天数 → 点击「生成计划」
  关键组件:
    - Text（「每周计划训练几天？」）
    - 天数 Chip Grid（1-7，横向排列，多选）
    - Button("生成计划", 主色，未选任何天时 .disabled)
  → 至少选 1 天后「生成计划」激活
  → 点击: Loading → Screen 4

Screen 4: 计划生成（Loading）
  主操作: 等待个性化计划生成
  关键组件:
    - 圆形 Loading 动画（居中，品牌色）
    - 渐进式 Text（「整合训练目标 ✓」「计算每周负荷 ✓」「生成专属计划...」）
  → 完成后自动跳转 Screen 5

Screen 5: 生成结果（My Plan）
  主操作: 查看生成的专属计划 → 保存 / 开始
  关键组件:
    - 计划标题 + 个性化摘要（「基于你的目标：增肌 · 中级 · 每周 4 天」）
    - SectionList（每周每日训练预览，按天分组）:
        每组: 「周一 · 上身推」
        每行: 动作名 + 组数×次数
    - Button("保存到我的计划", 主色)（全宽）
    - Button("预览全部动作", 次要)
  → 点击「保存」: 写入 Workouts 库，Toast「计划已保存」，返回 Explore Tab
  → 点击「预览全部动作」: Stack Push → 动作详情页（缩略图 + 肌肉图 + 说明）
```

**Exit State**:
- ✅ 保存成功：Toast「计划已保存到我的训练库」，Today Tab 出现「当前计划」卡片入口
- ↩ 中途关闭问卷：Dialog（「放弃问卷？你的答案将不被保存」→「放弃」/「继续」）
- 空状态（搜索无结果）：Empty 组件 + 「尝试其他关键词」+ 「浏览全部计划」CTA

---

## Mobile Component Kit

按使用频率排序（基于研究样本观察）：

| 优先级 | 组件（H5 antd-mobile）| 组件（RN Gluestack/RN）| 具体用途 |
|---|---|---|---|
| ★★★ | Tab Bar / `Tabs` | `react-navigation Bottom Tabs` | App 主导航（Today / Activity / Progress / Profile）|
| ★★★ | 圆形进度 / SVG 环形 | `react-native-circular-progress` | Activity Ring（运动 / 步数 / 热量进度环）|
| ★★★ | `echarts` / `recharts` | `victory-native` / `react-native-gifted-charts` | 周步数折线图、心率时序图、柱状统计 |
| ★★★ | 健康平台 API（H5 第三方）| `expo-health` / `react-native-health` | 步数/运动/心率等数据读写（iOS HealthKit / Android Health Connect）|
| ★★★ | Stack Navigation | `react-navigation Stack` | Progress → Day Detail → Workout Detail 三层钻取 |
| ★★ | `ProgressBar` 线性 | `ProgressBar` / 自定义 | 目标完成率（今日步数 / 周目标）|
| ★★ | `SpinLoading` / Loading | `ActivityIndicator` | 数据加载 / 计划生成等待状态 |
| ★★ | Bottom Sheet | `@gorhom/bottom-sheet` | 添加运动表单、日期选择、感知强度设置 |
| ★★ | 地图组件（Leaflet / Google Maps JS）| `react-native-maps` | GPS 跑步轨迹展示 |
| ★★ | 浏览器 Geolocation API | `expo-location` | 运动 GPS 追踪权限 + 位置数据 |
| ★★ | Push Notifications | `expo-notifications` / FCM | 每日目标提醒 / 运动完成通知权限 |
| ★★ | 滑动页（Swiper）/ TabView | `react-native-pager-view` | Onboarding 多步问卷横向滑动 |
| ★ | `List` | `FlatList` / `SectionList` | 历史运动记录、设置页健康类别 Toggle |
| ★ | `SwipeAction` | `Swipeable`（gesture-handler）| 历史记录列表左滑删除 |
| ★ | Empty 空状态 | 自定义 Empty | 无数据日的空状态（「休息日」）|
| ★ | `Slider` | `Slider`（@miblanchard）| 感知强度（Perceived Exertion）彩虹滑块 |
| ★ | 系统分享 / `navigator.share` | `react-native-share` | 运动总结分享到社交 |
| ★ | `Switch` / `Toggle` | `Switch` | 健康各数据类别授权开关（设置页）|

---

## Anti-Patterns

基于研究样本中观察到的设计错误：

- **直接触发健康权限系统弹窗，不展示自定义说明页**：用户看到一个多类别授权表单（步数 / 心率 / 睡眠 / Active Energy...），不知道为什么需要这些权限，授权率极低。→ 正确做法：先展示自定义说明页，分场景解释每种数据的用途（「步数用于计算每日目标」「心率用于计算卡路里消耗」），再触发系统授权（GO Club / Miles 模式）。

- **Onboarding 跳过问卷直接展示 Dashboard**：用户没有设置个性化目标，Dashboard 显示通用默认值（如「步数目标：10000」），缺乏激励感。→ 正确做法：至少 2-3 步个性化问卷（目标类型 + 当前体能水平），在 Permission 流程前完成，最后生成专属计划（GO Club 24 屏 onboarding 验证了此模式对留存率的正向影响）。

- **运动进行中屏幕显示密集 UI（小字、多菜单）**：用户户外跑步或力量训练中无法精确点击小目标，或强光下看不清小字。→ 正确做法：Active Session 屏幕必须「大字优先」（计时器 ≥60pt 等宽字体）+ 全屏深色背景 + 底部大按钮（直径 ≥64pt）+ 屏幕常亮。

- **运动会话「停止」按钮单次点击即触发**：跑步中手机轻微晃动可能误触「停止」，导致数据丢失且无法恢复。→ 正确做法：「停止」按钮需长按 2 秒确认（长按手势），或先点击「暂停」再出现「结束」选项（两步停止）。

- **进度页只显示「本周」，无法查看历史周数据**：用户想对比「上周 vs 本周」时无法操作。→ 正确做法：周视图必须有 `← 上周 / 下周 →` 导航（DateRange Navigator），图表随之平滑切换（300ms 动画）。

- **空状态只显示数字「0」而非引导 CTA**：新用户进入 Progress Tab 看到全是 0 数据，不知道如何开始。→ 正确做法：Empty 组件展示插图 + 「记录你的第一次运动」CTA，或用「示例数据灰显」让用户理解功能后再引导开始。

- **删除运动记录不显示健康数据影响警告**：用户不知道删除会同步影响健康平台中的数据（可能影响其他 App 的统计）。→ 正确做法：Dialog 明确说明「删除后将同步从健康平台移除，此操作不可撤销」，两个操作选项：「删除」(danger 样式) / 「取消」。

- **Permission 序列在同一屏连续弹出多个系统弹窗**：用户连续看到健康数据 → 通知 → 位置 三个系统弹窗，感觉被「权限轰炸」，大量拒绝。→ 正确做法：每个权限请求之间穿插自定义说明页，解释用途后再触发系统弹窗；非核心权限（如通知）可延迟到用户完成第一次运动后再请求。
