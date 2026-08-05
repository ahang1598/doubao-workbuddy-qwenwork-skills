# Scenario: Mobile Reading & Media（新闻阅读 / 杂志媒体）

> **研究来源**：基于对 Ground News（flow_id 7556、7558、7560、7562）、Apple News、Substack、The New Yorker、The New York Times 等真实产品 flow 的横向分析抽象，不代表任何单一产品的具体实现。

---

## Identity

**Platform**: Mobile (H5 / React Native)
**Definition**: Consumer-facing Mobile App for discovering, reading, and following news, magazine articles, or independent newsletters, featuring an article feed, reader mode, bookmark/save, and subscription/paywall management.

**Canonical Examples**: Apple News（系统级新闻聚合）、Ground News（偏见分析 + 新闻聚合）、Substack（独立作者订阅）、The New York Times、The New Yorker（杂志 App）

**Not this scenario if**: 产品是有声书/播客（改用 mobile/entertainment）；产品是社交内容发布平台（改用 mobile/consumer-social）；产品是图文电商（改用 mobile/marketplace）；产品是教育课程（改用 mobile/edtech）；产品是 Web 版内容管理（改用 web/xxx）。

---

## User Profile

| 维度 | 内容 |
|---|---|
| **主要角色** | News Reader / Subscriber（读者，主要用户）；Writer / Publisher（作者，发布端，通常在 Web 后台操作）|
| **核心目标** | 发现感兴趣的新闻/文章 → 完整阅读 → 收藏或分享 → 订阅喜欢的来源 |
| **心智模型** | 熟悉社交 Feed 模式（向下滚动浏览）+ 报纸版式（分类 Tab + 标题优先）；对「订阅」有明确的价值认知 |
| **使用频率** | 高频（每天多次，早晨 + 碎片时间）；每次会话 5~20 分钟 |
| **决策模式** | 浏览驱动型：快速扫标题 → 感兴趣点进 → 深度阅读 → 收藏 |
| **容错期望** | 低：阅读被打断 = 严重体验损害；离线阅读/缓存是加分项 |

---

## IA Template

**导航模式**: Bottom Tab Bar 4-5 Tab（Today / News / Following / Saved / Profile 或 Home / Discover / Alerts / Profile）

- **Today / Home Tab**：个性化推荐 Feed（头条 Carousel + 主题文章卡片列表）
- **News / Discover Tab**：话题分类浏览（横向 Category Tabs + 分类文章列表）
- **Following Tab**：关注的来源/作者最新内容（订阅流）
- **Saved / Bookmarks**：已收藏文章列表（离线可读）
- **Profile / Account**：订阅管理 + 阅读偏好 + 通知设置

**页面层级**: 3 级
```
L1: News Feed（今日推荐 / 分类浏览 / 关注订阅）
L2: Article Reader（全屏文章阅读器，Reader Mode）
L3: Share Sheet / Save Confirmation / Display Settings Sheet / Paywall Modal
```

注：与 consumer-social 不同，Reading App 的 L2 Article Reader 是核心工作区，全屏沉浸，隐藏 Tab Bar。

**权限角色结构**:
```
Guest（未登录）    → 浏览 Feed + 阅读免费文章，无法收藏（提示注册）
Registered User  → 完整收藏 + 自定义 Feed + 关注来源
Subscriber / Pro → 解锁付费文章 + 离线下载 + 跨设备同步（应用内订阅）
```

**数据密度**: 中
- Feed 列表：中密度卡片（标题 + 来源 + 时间 + 缩略图，无摘要；或大图 + 简短摘要）
- Article Reader：低密度（只显示文章内容，所有 UI Chrome 收起）
- 分类浏览：紧凑型（仅标题行 + 来源 + 时间，右侧小缩略图）

**主要容器模式**:
| 场景 | 容器 |
|---|---|
| 文章阅读 | 页面导航 push（Reader Mode，Tab Bar 隐藏）|
| 阅读字体/尺寸设置 | Bottom Sheet（Medium，不离开文章）|
| 保存/书签确认 | Toast（乐观更新，无 Modal）|
| 分享文章 | 系统分享面板（Share Sheet）|
| Feed 个性化（分类选择）| Bottom Sheet（Large）或全屏 Modal |
| 付费解锁文章（Paywall）| Bottom Sheet（含应用内订阅购买）|
| 举报/屏蔽内容 | Action Sheet（底部操作菜单，不全屏）|

**Tab Bar 骨架图（ASCII）**:
```
┌─────────────────────────────────────────┐
│   Ground News          [🔔] [👤]        │  ← Navigation Bar
│  ─────────────────────────────────────  │
│  [Top International ●] [For You] [Blind]│  ← Category Tabs
├─────────────────────────────────────────┤
│  ┌──────────────────────────────────┐   │
│  │  [HEADLINE CAROUSEL]             │   │
│  │  Gaza Ceasefire Talks Resume...  │   │
│  │  ● ○ ○ ○ ○                       │   │
│  └──────────────────────────────────┘   │
│                                         │
│  ┌──────────────────────────────────┐   │
│  │  [Thumbnail]  AI Regulation...   │   │
│  │             ■ 24 sources · 3h ago│   │
│  └──────────────────────────────────┘   │
│  ┌──────────────────────────────────┐   │
│  │  [Thumbnail]  Markets Drop...    │   │
│  │             ■ 18 sources · 5h ago│   │
│  └──────────────────────────────────┘   │
├─────────────────────────────────────────┤
│  Home(●)  Discover  Alerts  Profile     │  ← TabBar
└─────────────────────────────────────────┘
```

---

## 该场景独有的 IA/UX 决策

1. **Article Reader 必须全屏沉浸，Tab Bar 强制隐藏** — 新闻阅读的核心体验是持续专注阅读，Tab Bar 在阅读中的持续存在是视觉干扰而非工具。进入 Article Reader 时必须隐藏底部 Tab Bar，退出阅读后自动恢复。与 consumer-social 的内容详情（评论/互动是核心目的）不同，Reading App 所有 UI Chrome 都应服务于「阅读继续」而非「离开当前内容」。高质量实现还会在用户点击内容区域后自动收起 NavigationBar（仅保留返回按钮），进入「完全沉浸模式」。

2. **「减少/移除」内容偏好操作必须有即时 Restore 出口，不能静默消失** — Ground News flow_id 7566（Remove source）和 flow_id 7558（Show less like this）都展示了同一模式：移除来源 / 关闭话题后，成功反馈（Toast 或 Banner）中必须含「Restore in Settings」或「Undo」链接。新闻 Feed 的内容权重是用户长期个性化的结果——破坏性修改无法通过「删除然后重新设置」简单恢复，必须在操作完成的当下提供轻量撤回路径。否则用户因为一次误操作而永久失去某个新闻来源，往往根本不知道去哪里找回。

3. **本地新闻 Location 权限必须走 Pattern G：先 App 内说明页，再触发系统弹窗** — Ground News flow_id 7571 展示了标准实现：Local News Hero Screen（说明价值 + 两个选项「Use Device Location / Skip」）→ 用户主动点击 → 然后才触发系统权限弹窗。跳过 App 内说明直接弹系统权限会导致用户在不理解上下文时拒绝，后续无法再次请求（移动端系统只给一次自动弹窗机会），彻底损失地理化内容能力。Pattern G 说明页必须清楚回答「为什么需要？」和「允许能带来什么好处？」这两个问题，才能显著提升用户授权率。

4. **Feed 话题排序必须用 long-press + drag handle 拖拽模式** — Ground News flow_id 7573 的 11 步话题管理流展示了最优实现：进入「Edit Navigation」专屏 → 每行话题右侧显示 drag handle（三横线）→ long-press + 拖动重排，被拖动行视觉浮起（elevated shadow）+ 其他行动态填充占位。这优于「编辑模式 + 上下箭头按钮」，因为拖拽给用户直接的空间操控感，且 long-press 触发与移动端系统列表排序（如音乐播放列表、任务顺序）完全一致，用户无需学习新交互。

5. **Paywall 弹出时文章首段必须保留在背景可见（带渐变截断），不能直接覆盖** — 新闻 Paywall 的转化机制是「内容钩子」：用户必须先被文章吸引，才愿意为「读完它」付费。Paywall Bottom Sheet 从底部弹起时，背景的文章内容（带向下渐变模糊截断效果）必须依然可见——这一设计让用户感知到「内容就在眼前，只差一步」的心理张力。与 edtech 的 Paywall（Onboarding 漏斗之后，用户已建立学习意愿）不同，新闻 Paywall 是用户在随机浏览中突然遭遇的决策时刻，文章预览是唯一的价值说明媒介。

---

## Canonical Flows

### Flow 1: 浏览 Feed + 阅读文章（Browse Feed & Read Article）

**在此场景的特殊性**: 与 consumer-social 不同，Reading App 的核心体验是「沉浸式阅读」而非互动；文章打开后 Tab Bar 必须隐藏，营造全屏阅读环境；文章操作（收藏/分享/设置）通过顶部工具栏图标完成，不破坏阅读沉浸感；收藏操作必须乐观更新（即时 filled icon，不等接口返回）

**Entry**: 用户打开 App 进入今日推荐 Feed，或切换 Category Tab 到感兴趣的话题

**Screens**:
```
Screen 1: News Feed（Home Tab）
  主操作: 浏览文章卡片，发现感兴趣的内容
  关键组件:
    - NavigationBar: App 名称 + 通知 Bell 图标 + 头像
    - Category Tabs（横向 ScrollView：Breaking / Technology / Science / Business / Sports）
    - Headline Carousel（横向轮播，顶部大卡片，最新要闻，分页点）
    - 虚拟化列表 ArticleCard: 缩略图 + 标题 + 来源名 + 时间 + 来源数量/偏见条
    - Per-card Bookmark Icon（右上角，tap 即时 filled 乐观更新）
    - Per-card 「···」溢出菜单（→ Save / Share / See less like this / Report）
  → 点击文章卡片: 页面导航 push → Screen 2（Article Reader）
  → 点击 Bookmark: 即时状态切换（filled），Toast「Saved · View」
  → 点击「···」: Action Sheet → 各操作

Screen 2: Article Reader
  主操作: 阅读完整文章
  布局: 全屏页面，Tab Bar 隐藏
  关键组件:
    - NavigationBar: 返回箭头（「← 话题名」）+ Bookmark + Share + 「···」
    - 文章头部: 来源 Logo + 来源名 + 发布时间 + 分享数
    - 大图（全宽 Hero）
    - 文章内容: 滚动区域（serif 字体 + 舒适行距）
    - Reader Mode 说明覆层（首次使用，2步）: 「You're in reader mode」+ dismiss
    - Bottom Toolbar（悬停可见，阅读中收起）: 进度指示 + 字体设置 Aa + 分享 + 收藏
  → 点击「Aa」字体设置: Bottom Sheet（Medium）→ Screen 2a（Display Settings）
  → 点击收藏: Bookmark icon 即时 filled，Toast「Saved」
  → 点击分享: 系统分享面板

Screen 2a: Display Settings Sheet
  主操作: 调整阅读排版
  关键组件:
    - Sheet Header: 「Display Settings」+ Button「✕」
    - Article Font 选择（横向滚动 Button Row：New York / Georgia / System / Mono，选中有蓝色边框）
    - Text Size 选择（横向 Button Row：S / Default / L / XL，选中高亮）
  → 改变设置: 后台 Article Reader 即时更新（Sheet 保持打开）
  → 关闭 Sheet: 返回 Article Reader，设置保留
```

**Exit State**: 文章阅读完毕，用户点 Back 返回 Feed；收藏的文章出现在 Saved Tab
**Empty State**: Feed 无内容时：空状态插图「No stories yet」+ Button「Explore Topics」

---

### Flow 2: 个性化 Feed 设置（Customize News Feed）

**在此场景的特殊性**: 新闻 App 的 Feed 个性化是高价值功能（直接影响日活留存）；类目选择用视觉化 Chip 网格（不是 List），已选状态需明显高亮；「For You」Feed 首次加载前必须至少选择 1 个类目；保存设置后 Feed 动效切换到个性化结果（不是静态跳转）

**Entry**: 用户在 Profile 设置中点击「Personalize Feed」，或 Feed 个性化引导 Banner

**Screens**:
```
Screen 1: Feed Personalization（类目选择）
  主操作: 选择感兴趣的新闻类目
  容器: Bottom Sheet（Large）或全屏页面
  关键组件:
    - 标题「Personalize your feed」
    - 说明文字（「Choose topics you care about」）
    - 网格类目 Chips（2~3 列，每个 Chip：图标 + 类目名，选中有填充色 + 对勾）
    - 类目覆盖: World / Politics / Business / Technology / Science / Sports / Arts / Health / Lifestyle 等
    - Button「Done」（主 CTA，选择 ≥1 个后激活）+ 「Skip」（ghost，跳过个性化）
    - 已选数量提示（「3 topics selected」）
  → 点击 Chip: 即时切换选中/未选中状态（乐观更新）
  → 点击「Done」: Sheet dismiss，Feed 刷新为个性化内容
  → 点击「Skip」: 使用默认推荐 Feed
  → 点击「Reorder Topics」或进入 Edit News 专屏: → Screen 1a（话题排序）

Screen 1a: Edit News / Reorder Topics（话题拖拽重排）
  主操作: 拖拽重新排列话题在 Top Bar 的顺序
  关键组件:
    - NavigationBar: 「← Personalize」+ 标题「Edit Navigation」
    - 可排序列表: 每行（话题图标 + 话题名 + 右侧 drag handle ⋮⋮）
    - 拖拽交互: long-press 触发行浮起（elevated shadow）+ 其他行动态收缩占位
    - Toggle 区块（Feed 开关，分组）:
        - Blindspot（显示你不常看的观点）Toggle
        - For You（算法推荐）Toggle
        - Local News Toggle（开启触发地理位置 Pattern G 权限请求）
        - Compact Cards（紧凑卡片模式）Toggle
        - Hide Paywalls（屏蔽付费来源内容）Toggle
  → 拖拽完成: 行自动定位，不需要额外「Save」（实时保存）
  → 点击 Back: 返回 Screen 1，Top Bar 话题顺序已更新

Screen 2: Personalized Feed（个性化结果）
  主操作: 查看个性化后的 Feed 内容
  关键组件:
    - 「For You」Tab 高亮（导航状态切换）
    - ArticleCard 列表（基于选择的类目过滤推荐）
    - Active Filters 显示（如有 Topic Chip 在 Feed 顶部）
    - 恢复 Banner（若刚执行了「Remove source / Show less」操作：「[来源] removed · Restore in Settings」，3秒自动消失）
  Exit: 用户继续正常浏览 Feed
```

**Exit State**: Feed 内容已个性化，Category Tabs 中「For You」Tab 置为默认选中
**Empty State**: 如选择的类目暂无内容：「No stories for this topic yet · Try another topic」

---

### Flow 3: 订阅付费解锁（Subscribe to Unlock Premium）

**在此场景的特殊性**: 移动端新闻 App 的 Paywall 触发时机是「用户点击付费文章后」（不在浏览阶段拦截）；必须有清晰的价值主张（预览文章的一部分 + 订阅福利列表）；Annual Plan 默认选中（与 Entertainment 场景一致）；必须提供「恢复购买」按钮（平台合规）；购买通过平台原生支付完成

**Entry**: 用户点击 Feed 中带锁图标的付费文章，或 Profile → Subscription → Upgrade

**Screens**:
```
Screen 1: Article Paywall（文章内 Paywall）
  主操作: 了解订阅价值，决定是否订阅
  容器: Bottom Sheet（从文章底部弹出，文章首段依然可见在背景；向下渐变模糊截断效果增强「内容就在眼前」的心理张力）
  关键组件:
    - Sheet Header: App Logo + 标题「Think freely.」（或品牌 Paywall 语）+ Button「✕」（必须存在，平台合规要求）
    - 文章预览摘要（已读部分，向下渐变遮罩截断，清晰传达「还有更多内容」）
    - 福利列表（CheckList 风格，对勾图标）:
      - ✓ Unlimited access to all stories
      - ✓ Bias coverage analysis
      - ✓ Offline reading
      - ✓ Ad-free experience
    - 订阅选项（RadioGroup，两个选项卡片）:
      - Annual（高亮边框 + Badge「Most Popular」）: $XX.99/year = $X.99/month（换算强调性价比）
      - Monthly: $X.99/month（次选项，字体小一级）
    - Button「Start Free Trial」或「Subscribe」（主 CTA，品牌色，全宽）
    - Link「Restore Purchase」（灰色小字，平台合规，必须存在）
    - Legal 小字（「X-day free trial, then $XX/year. Cancel anytime.」）
  → 点击「Subscribe / Start Free Trial」: → Screen 2（平台支付流程）
  → 点击「✕」: Sheet dismiss，回到免费 Feed

Screen 2: 平台支付流程（系统原生）
  主操作: 通过平台原生支付完成购买
  关键组件（系统原生，App 不可定制）:
    - 应用图标 + 订阅名称 + 来源
    - 订阅详情卡片（价格 + 计划 + 免费试用说明）
    - 生物识别确认（Face ID / Touch ID / 指纹）
  → 确认成功: → Screen 3（成功状态）
  → 用户取消: 回到 Screen 1 Paywall

Screen 3: Subscription Success
  主操作: 确认订阅成功，进入内容
  关键组件:
    - 庆祝动效（confetti 或 checkmark 动画）
    - 标题「Welcome to [App Name]+!」
    - 解锁确认（「You now have access to all premium content.」）
    - Button「Start Reading」（主 CTA，进入 Premium Feed）
  Exit: 用户返回 Feed，之前被锁的文章现在可以完整阅读
```

**Exit State**: 订阅状态持久，Profile → Subscription 显示订阅详情（续费日期 + 取消入口）；Feed 中锁图标消失
**Empty State**: 不适用

---

---

### Flow 4: Bookmark & Audio Mode（书签稍后读 + 听文章 TTS）

**在此场景的特殊性**: 新闻阅读的「稍后读」和「朗读模式」是两个深度互补的功能——通勤中无法看屏幕的用户需要「把文章读出来」，而书签列表正是「待听队列」的天然容器。ElevenReader（flow_id 8968，5 屏）记录了 TTS 朗读的完整技术闭环：文字输入 → 转换处理 → Reader + 当前句子蓝色高亮同步播放（text synchronized highlighting），是移动端 TTS 的行业实现标准。flow_id 8971（5 屏，URL → 提取文章 → 朗读）和 flow_id 8949（4 屏，语速控制 Bottom Sheet：0.5x-4x，选中后即时应用）补充了「链接导入」和「语速调节」两个关键子流程。**与 entertainment 场景 Podcast 播放器的最大区别**：TTS 文章朗读必须在播放界面内展示原文文字并同步高亮当前段落（用户可随时对照阅读），而 Podcast 只显示封面/波形；同时「朗读中途切换到 Feed 浏览」时必须有持久 Mini Player（悬停在 Tab Bar 上方），维持「听+看其他内容」的并行体验。

**行业共识**：ElevenReader（flow_id 8949）的语速控制 Bottom Sheet 是标准实现（不用 inline slider）：0.5x / 0.75x / 1x / 1.25x / 1.5x / 2x 离散速度选项，选中后关闭 Sheet 即时生效。Brink（flow_id 10924）和 Ground News（flow_id 7560）均确认了 Bookmark 乐观更新（单击 icon 即时 filled，无 Modal 确认）。

**Entry**: Tab Bar → 点击「Saved / 收藏」Tab

```
Screen 1: Saved Articles List（书签列表）
  主操作: 浏览已收藏文章，选择一篇开始阅读或收听
  关键组件:
    - NavigationBar: 标题「Saved」+ 右上角 Button「Edit」（进入批量删除模式）
    - 过滤 Tab（横向，可选）: Tab("All") / Tab("Unread") / Tab("Read")
    - List（已收藏文章，按保存时间倒序排列）:
        每行: 缩略图（左侧正方形）+ VStack（标题 + 来源名 + 预计阅读时长「3 min read」+ 保存时间）
        右侧图标区: Bookmark（filled 状态，点击取消收藏）+ 「···」
        未读标识: 标题左侧蓝色圆点（已读后消失）
        左滑操作: Button("Delete" danger 色) + Button("Mark as Read" 灰色)
    - Empty State（无收藏）: 插图「Nothing saved yet」+ Text「Tap the bookmark icon on any article」
  → 点击文章行: 进入 Article Reader（Screen 2，Audio Mode 关闭的默认阅读状态）
  → 点击文章行右侧「🎧 Listen」图标（可选 shortcut）: 直接进入 Screen 2 并自动启动 Audio Mode

Screen 2: Article Reader + Audio Mode 入口
  主操作: 阅读文章 / 点击「Listen」启动朗读
  布局: 全屏，Tab Bar 隐藏
  关键组件（Audio Mode 关闭时）:
    - NavigationBar: 「← 返回」+ 标题「Saved」+ Bookmark（filled）+ Share + 「···」
    - 文章内容区（正常阅读模式）
    - Bottom Toolbar（Sticky，随内容滚动保持底部固定）:
        Button("🎧 Listen"，主色，带文字): 启动 TTS 朗读
        Button("Aa" 字体)
        Button("Share")
  → 点击「🎧 Listen」: TTS 初始化（短暂 Loading 指示），进入 Audio Mode（Screen 2-A）

Screen 2-A: Article Reader（Audio Mode 启动中 → 播放中）
  主操作: 跟随朗读 / 控制播放
  关键组件（Audio Mode 激活时）:
    - 文章内容区（正常显示，当前播放句子高亮：蓝色背景覆盖 + 滚动视口自动跟随当前句）
    - Audio Player Bar（底部 Sticky，替代 Bottom Toolbar）:
        [≪ 后退 30s] [⏸ 暂停 / ▶ 播放] [≫ 前进 30s]（三个圆形大按钮）
        播放进度条（线性，可拖拽跳转）
        Button("1.0x"，当前语速，点击弹出 Screen 3 语速 Sheet）
        Button("✕" 关闭，关闭 Audio Mode，回到普通阅读模式）
    - 屏幕常亮（`expo-keep-awake` / `navigator.wakeLock`，朗读期间防息屏）
  → 点击「1.0x」速度按钮: Bottom Sheet → Screen 3
  → 点击「≪ 后退 30s」: 音频和高亮回退 30 秒
  → 点击「✕ 关闭」Audio Mode: 停止 TTS，恢复普通阅读状态，Toolbar 切回「🎧 Listen」
  → 点击 Back（返回书签列表）: Audio Mode 持续播放，Mini Player 出现在 Tab Bar 上方（Screen 4）

Screen 3: 语速控制（Playback Speed Sheet）
  主操作: 选择朗读速度
  容器: Bottom Sheet（Medium）
  关键组件:
    - Sheet Header: 「播放速度」+ Button「✕」
    - 速度选项（垂直 List，每行文字按钮）:
        「0.5×」/ 「0.75×」/ 「1×（正常）」/ 「1.25×」/ 「1.5×」/ 「2×」
        当前选中项: 蓝色文字 + 右侧对勾 ✓
    - 注意: 无独立「保存」按钮——点击选项即时应用并关闭 Sheet（ElevenReader flow_id 8949 模式）
  → 点击任意速度: Sheet 关闭，播放速度即时切换，Audio Player Bar 速度显示更新（如「1.5×」）

Screen 4: Mini Player（切换 Tab 后持续播放）
  主操作: 在浏览其他内容时保持对朗读的控制
  位置: 固定悬浮在 Tab Bar 上方（Safe Area 之上，Tab Bar 之上）
  关键组件（一行固定高度，约 64pt）:
    - 文章缩略图（32pt 正方形，左侧）
    - 文章标题（单行截断，字号 14pt）
    - 播放进度条（线性，细，文章下方）
    - [⏸ 暂停 / ▶ 播放]（圆形按钮，40pt）
    - [✕ 关闭]（关闭 Mini Player + 停止朗读）
    - 点击 Mini Player（非按钮区域）: 跳转回 Article Reader Audio Mode（Screen 2-A）
  Exit: 
    - 朗读完毕（文章末尾）: Mini Player 显示「播放完毕」+ Toast「Saved as Read」，3 秒后 Mini Player 消失
    - 点击 Mini Player [✕]: 停止朗读，Mini Player 消失，文章标记为已读
```

**Exit State**:

- ✅ 正常听完: 文章自动标记为已读（列表中蓝点消失），Toast「Marked as Read」
- ✅ 切换 Tab 继续播放: Mini Player 持续显示在 Tab Bar 上方，用户可继续浏览 Feed 的同时收听
- ❌ TTS 初始化失败（无网络）: Toast「无法加载朗读，请检查网络」，回到普通阅读模式
- ↩ 取消收藏：List 左滑 Delete 或点击 Bookmark → Action Sheet 确认「移除收藏？」→ 从 Saved 列表移除

---

## Mobile Component Kit

按使用频率排序（基于研究样本观察）：

| 优先级 | 组件（H5 antd-mobile）| 组件（RN Gluestack/RN）| 具体用途 |
|---|---|---|---|
| ★★★ | `InfiniteScroll` + `List` | `FlashList` / `FlatList` | 新闻 Feed 列表（文章卡片垂直滚动）|
| ★★★ | `Tabs` + `ScrollView`（横向）| `ScrollView` + `TouchableOpacity` | 分类 Tabs（Breaking / Technology / Sports 横向切换）|
| ★★★ | `Swiper` | `Carousel` / `PagerView` | Headline Carousel（头条轮播，顶部大卡片）|
| ★★★ | `Popup`（medium）| `BottomSheet`（medium）| Display Settings / Feed 个性化 / Paywall |
| ★★★ | `Toast` | `Toast` | 收藏确认（「Saved · View」）乐观更新反馈 |
| ★★ | `Grid` | `FlatList`（numColumns）| Feed 个性化类目 Chip 选择网格 |
| ★★ | `ActionSheet` | `ActionSheet` | 文章操作（Save / Share / Report / See less like this）|
| ★★ | `Switch` | `Switch` | Feed 设置开关（Local News / Compact Cards / Hide Paywalls）|
| ★★ | `DraggableFlatList`（第三方）| `DraggableFlatList` | 话题拖拽重排（long-press + drag handle）|
| ★ | `Radio` + `RadioGroup` | `Radio` + `RadioGroup` | 订阅计划选择（Annual / Monthly）|
| ★ | `Collapse` | `Accordion` | 文章「Read more」展开 / Subscription Details |

---

## Anti-Patterns

- **阅读中 Tab Bar 不隐藏（Tab Bar visible during article reading）**: 阅读器底部保留导航栏，破坏沉浸感，用户意外误触 → 正确做法：进入 Article Reader 时隐藏 Tab Bar，退出阅读自动恢复
- **Paywall 在浏览 Feed 时弹出（Paywall triggers on feed browse）**: 用户未打开任何文章就被要求订阅，严重影响探索体验 → 正确做法：Paywall 仅在用户点击「付费文章」后触发（在文章内），免费 Feed 浏览完全开放
- **收藏操作需要确认 Modal（Bookmark requires confirm Modal）**: 用户点收藏后弹 Alert 「Are you sure?」，打断阅读连续性 → 正确做法：Bookmark 乐观更新（即时 filled icon），Toast「Saved · Undo」提供撤销入口，无 Modal
- **无「恢复购买」入口（No restore purchase button）**: Paywall Sheet 中没有「Restore Purchase」按钮 → 违反平台审核规则，所有应用内购买界面必须包含 Restore Purchase 按钮
- **移除来源/话题后无 Restore 出口（Remove with no undo path）**: 用户「Remove source」或「Show less like this」后内容静默消失，没有任何撤回入口 → 正确做法：成功 Toast/Banner 中必须包含「Restore in Settings」或「Undo」链接（Ground News 模式），新闻偏好是长期积累的结果，误操作损失极难察觉和修复
- **本地新闻直接触发系统位置权限（Location permission without Pattern G）**: App 在没有任何说明的情况下直接弹出系统位置权限请求 → 系统只允许一次自动权限弹窗，用户在不理解原因时大概率拒绝，后续永远无法获得权限 → 正确做法：必须先显示 App 内说明页（Local News Hero：说明价值 + 「Use Device Location / Skip」），用户主动点击后再触发系统权限弹窗（Pattern G）
