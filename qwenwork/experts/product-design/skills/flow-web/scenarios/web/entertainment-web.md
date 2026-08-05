# Scenario: Entertainment Web（视频/娱乐平台）

> **研究来源**：基于对 Prime Video、YouTube、Tidal、Deezer、Twitch 等 5 个真实产品 flow 的横向分析抽象，不代表任何单一产品的具体实现。

---

## Identity

**Platform**: Web
**Definition**: Consumer-facing web platform for discovering, streaming, and organizing video or audio content, with subscription or freemium monetization models.

**Canonical Examples**: YouTube（视频平台）、Netflix / Prime Video（订阅流媒体）、Spotify / Tidal Web（音乐流媒体）

**Not this scenario if**: 产品是内容创作工具（改用 web/design-tools）；产品是直播电商或带货平台（改用 web/ecommerce）；产品是播客/新闻内容聚合阅读器而非主动播放型（改用 community-social variant）；产品是移动端原生 App（改用 ios/entertainment）。

---

## User Profile

| 维度 | 内容 |
|---|---|
| **主要角色** | Consumer（已登录或未登录访客，核心行为是消费内容）|
| **核心目标** | 发现感兴趣的内容 → 播放 → 保存/收藏；或升级付费解锁更多内容 |
| **心智模型** | 熟悉 YouTube/Netflix 模式：首页 Feed + 搜索 + 内容详情 + 持续播放 |
| **使用频率** | 高频娱乐型，会话较长（30分钟~数小时），目标模糊（消遣发现）|
| **决策模式** | 探索发现型：浏览 → 被内容吸引 → 决定播放；非任务驱动 |
| **容错期望** | 中：误操作可以后退，但播放中断/进度丢失会引发明显不满 |

---

## IA Template

**导航模式**: Left Sidebar（主分类导航）+ Top Nav（搜索、用户头像）+ Bottom Persistent Player（音乐流媒体必须）

- Left Sidebar：主分类（Home、Explore/Browse、Library/My Collection、Live）
- Top Nav：搜索框 + 通知 + 用户头像（下拉账户菜单）
- Bottom Player：音乐流媒体场景中跨页面持久存在，不随导航跳转消失

**页面层级**: 4 级
```
L1: Home / Browse（内容发现首页，横向 Carousel 行）
L2: Category / Genre 页 或 Search Results（内容列表，Grid / Feed）
L3: Content Detail（内容详情：视频播放页 / 专辑详情 / 剧集列表）
L4: Active Playback（全屏或嵌入式播放器，含 Up Next / Related）
```

**权限角色结构**:
```
Visitor（未登录）  → 浏览内容，不可播放付费内容，无收藏
Free User（已登录）→ 播放免费内容，有收藏，受广告限制
Premium（订阅用户）→ 全量内容 + 无广告 + 离线下载（如有）
```

**数据密度**: 低~中
- 主视图：Card（图片主导，标题+元数据辅助，卡片间距宽松）
- 不使用：表格、高密度信息列表

**主要容器模式**:
| 场景 | 容器 |
|---|---|
| 播放内容 | 全页或嵌入式 Video Player（宽屏 16:9）|
| 选择 Playlist / Watchlist | Sheet（右侧抽屉）或小型 Popover |
| 订阅升级 / Paywall | 全屏多步 Modal Wizard（3-4 步）|
| 视频/音乐的 Context Menu | DropdownMenu（卡片三点菜单）|
| 语言/字幕设置 | Popover（播放器内悬浮，不全页跳转）|

**导航骨架图（ASCII）**:
```
┌─────────────────────────────────────────────────────────┐
│  Logo    [Search__________________]      [🔔] [Avatar▾] │
├──────────┬──────────────────────────────────────────────┤
│          │  [Hero Banner / Featured Content]             │
│  Home    │  ─────────────────────────────────────────── │
│  Browse  │  Trending This Week          [See all →]      │
│  Library │  [Card][Card][Card][Card][Card] ──→            │
│  Live    │  ─────────────────────────────────────────── │
│          │  Continue Watching           [See all →]      │
│          │  [Card▶ 43%][Card▶ 12%][Card▶ 78%] ──→        │
│          │  ─────────────────────────────────────────── │
│          │  Recommended for You                          │
│          │  [Card][Card][Card][Card][Card] ──→            │
├──────────┴──────────────────────────────────────────────┤
│  ▶ Now Playing: Song Name — Artist   ──●──  🔀 ⏮ ⏸ ⏭  │  ← Bottom Player（音乐场景）
└─────────────────────────────────────────────────────────┘
```

---

### 图 2：关键状态对比图（Key State Variations）

```
左：Content Detail 正常态（Premium 可播放）      右：订阅到期态（Play 被 Paywall 拦截）

┌────────────────────────────────────┐  ┌────────────────────────────────────┐
│  [Player Area - 16:9 Thumbnail]    │  │  [Player Area - 16:9 Thumbnail]    │
│          ▶ (Play Circle)           │  │     🔒 Your subscription expired   │
├────────────────────────────────────┤  ├────────────────────────────────────┤
│ Breaking Bad  S1  2008  TV-MA  62m │  │ Breaking Bad  S1  2008  TV-MA  62m │
│                                    │  │                                    │
│ [▶ Play]  [+ Watchlist]  [...]    │  │ [🔒 Renew to Watch]  [+ Watchlist] │
│                                    │  │                                    │
│ Drama · Thriller · 5 Seasons       │  │ Drama · Thriller · 5 Seasons       │
│ A chemistry teacher...             │  │ A chemistry teacher...             │
│                                    │  │  ⚠ Your plan expired on Apr 20.    │
│ [Episodes] [Related] [Details]     │  │    Renew now to keep watching.     │
└────────────────────────────────────┘  └────────────────────────────────────┘
```

---

### 图 3：覆层层级图（Overlay Hierarchy）

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Logo    [Search___________________________]          [🔔] [Avatar ▾]    │ ← Top Nav（z-100）
├──────────┬───────────────────────────────────────────────────────────────┤
│          │  [Video Player — 全屏宽度]                                     │
│  Home    │  ┌──── Controls Bar（鼠标移入显示）───────────────────────┐   │
│  Browse  │  │  ▶ ⏭ 🔊────●─────── 01:23 / 45:00  CC  1080p  [⛶]  │   │
│  Library │  └───────────────────────────────────────────────────────┘   │
│  Live    │                                                               │
│          │  ┌──── Autoplay Countdown Widget（右下角浮出）─────────┐      │
│          │  │  Next: Episode 2 — "Cat's in the Bag"              │      │
│          │  │  Auto-playing in  12  seconds                      │      │
│          │  │  [Skip] [Cancel]                                   │      │ ← z-150（内嵌 Player）
│          │  └────────────────────────────────────────────────────┘      │
│          │    ▲ 触发: 剧集剩余 15 秒自动浮出                              │
│          │                                                               │
│          │  ┌──────────────────────────────────────────────────────┐    │
│          │  │  Playlist Picker Sheet（右侧）z-index: 200            │    │
│          │  │  Add to playlist                                     │    │
│          │  │  ○ Watch Later                                       │    │
│          │  │  ○ My Favorites                                      │    │
│          │  │  + Create new playlist                               │    │
│          │  │  [Done]                                              │    │
│          │  └──────────────────────────────────────────────────────┘    │
│          │    ▲ 触发: 内容详情页 [+ Watchlist] 或卡片三点菜单             │
│          │                                                               │
│          │  ┌──────────────────────────────────────────────────────┐    │
│          │  │  Renewal Modal（中）全屏 Wizard  z-index: 300          │    │
│          │  │  Your subscription expired.                          │    │
│          │  │  ┌────────────┐ ┌────────────┐                      │    │
│          │  │  │ Monthly    │ │ Annual     │                      │    │
│          │  │  │ $9.99/mo   │ │ $79.99/yr  │                      │    │
│          │  │  └────────────┘ └────────────┘                      │    │
│          │  │  [Renew with Visa ...1234] [Change payment method]   │    │
│          │  └──────────────────────────────────────────────────────┘    │
│          │    ▲ 触发: 点击 [▶ Play] 订阅已到期内容时                    │
└──────────┴───────────────────────────────────────────────────────────────┘
  ┌───────────────────────────────────────────────────────┐
  │  ▶ Now Playing: Song Name — Artist  ──●──  🔀 ⏮ ⏸ ⏭  │  ← Bottom Player（z-50，音乐场景持久）
  └───────────────────────────────────────────────────────┘
  ┌──────────────────────────────────────────────────────┐
  │  ✓ Added to Watch Later   [View]  [×]                │  ← Toast（z-500）
  └──────────────────────────────────────────────────────┘

触发关系说明:
- Bottom Player（底部）: 音乐场景专属，跨页面持久，z-50，播放状态不随路由变化
- Autoplay Countdown（播放器内浮出）: 剧集剩余 15 秒触发，z-150，Skip/Cancel 可中断
- Playlist Picker Sheet（右）: 内容 [+ Watchlist] 或三点菜单触发，z-200，背景内容可见
- Renewal Modal（中，全屏）: 点击 Play 订阅到期内容时触发，z-300，阻断播放直到续费完成
- Toast（底）: 添加收藏、操作确认轻量反馈，z-500，3-5 秒消失
```

---

## 该场景独有的 IA/UX 决策

1. **持久化底部播放器是音乐场景的 IA 核心约束** — Web 音乐流媒体（Spotify、YouTube Music、Tidal）必须维持一个跨页面持久的 Bottom Player，导航切换时播放器不销毁、播放状态不中断。这不是普通组件，而是整个应用的第四层 Layout 层（Header + Sidebar + 主内容区 + Bottom Player），所有页面的主内容区必须预留 Bottom Player 高度（约 72px）。通用 SaaS / EdTech 没有这个布局约束。

2. **Autoplay Countdown 是视频平台留存的主动机制** — Netflix / Prime Video 在剧集播放结束前 15–20 秒弹出下一集倒计时 Widget（「下一集 X 秒后自动播放 · Skip / Cancel」）。这与其他场景「操作完成后等待用户」的模式相反——平台主动延续用户的观看链条，减少会话中断。Skip 按钮必须在整个倒计时周期内可见，Cancel 延续至 Auto-play 触发前。

3. **内容卡片 Hover State 是 Web 端独有的决策层** — 桌面 Web 鼠标悬停时，卡片展开一层 Hover Panel（Netflix / YouTube 模式：卡片缩略图放大 + 叠加 Play 圆形按钮 + 浮出标题 / 年份 / 评级 / Save 操作图标），承担了移动端「点进详情页前」的预判功能。Web 版内容卡片必须设计 Default 和 Hover 两种状态；移动端 iOS/Android 无需处理此状态。

4. **Paywall 只在 Play 动作触发，Browse 与 Detail 全程开放** — 用户在 Home / Browse / Content Detail 页浏览时完全不受拦截；Paywall Modal 只在点击「Play」某付费保护内容时触发。与 SaaS（功能级门控）和 EdTech（课时节点锁定）不同——娱乐平台的内容可发现性优先于付费门控，用户必须先产生欲望才愿意订阅。Content Detail 页应完全展示标题、简介、演职员表，仅 Play 按钮触发 Paywall。

5. **「Continue Watching」是首屏的跨会话留存钩子** — 用户有观看历史后，Home 页「Continue Watching」Carousel 必须排在所有其他内容推荐区块之前（第一个内容 Section）；每张卡片底部附进度条（已观看比例）。这是流媒体留存的主要钩子——用户回来的动机通常是「继续上次未看完的内容」，而非重新发现新内容。无观看历史时此 Section 完全不显示（不展示空 Section）。

---

## Canonical Flows

### Flow 1: 内容发现 + 播放（Content Discovery & Playback）

**在此场景的特殊性**: 与 E-commerce 的商品浏览不同，娱乐内容详情页的主 CTA 是「播放」而非「加购」；内容详情无需跳转独立页面，视频流媒体直接在详情页内嵌播放（YouTube 模式）或打开 Player 页（Netflix 模式）；内容卡片必须显示「Continue Watching」进度（已观看比例）

**前置条件**: 用户已登录（未登录可浏览但无法收藏/收看付费内容）；用于播放的内容已上线（非下架状态）
**若前置条件不满足**: 未登录用户点击 Play 免费内容 → 弹出注册引导 Modal；付费内容点击 Play → 触发 Paywall（Flow 2）；内容在本地区不可用 → 内容详情显示「Not available in your region」

**Entry**: 用户在 Home / Browse 页浏览内容 Carousel，点击某个内容卡片

**Screens**:
```
Screen 1: Home / Browse
  主操作: 浏览内容 Carousel 行，发现并点击感兴趣的内容
  关键组件:
    - Hero Banner（全宽顶部，约 450px 高）:
        背景：自动播放 muted 预告片（视频平台）或高质量 Key Art（音乐平台）
        覆层文字: 内容标题（大字）+ 简介（1-2 行截断）+ 年份 / 评级 Badge
        CTA 双按钮: Button("▶ Play", .primary) + Button("ℹ More Info", .secondary)
    - Carousel 行组（LazyLoad，按优先级从上到下排列）:
        「Continue Watching」（仅有观看历史时，置首）— 每卡底部含进度条（已观看 %）
        「Trending Now」/ 「Recommended For You」/ 「New Releases」/ Genre 分类行
    - ContentCard（每行 Carousel 的基本单元）:
        16:9 缩略图（aspect-ratio: 16/9，object-fit: cover）
        Hover State（Desktop）: 卡片放大 scale-105 + 叠加 Play 圆形按钮 + 浮出标题 / 评级 / 操作图标
        Badge（右下角：时长 / LIVE 标签 / 4K / 进度百分比）
        Save 图标（hover 时显示，即时 optimistic toggle）
    - Category Filter Pills（可选）: 横向 Chip Row（All / Movies / Series / Genre）
  → 点击内容卡片: → Screen 2
  → 悬停卡片（Desktop hover）: 展开 Hover State，显示 Play + Save + 评级信息
  → 点击 Hero CTA「▶ Play」: 直接跳 Screen 3（跳过 Detail 页）
  → 点击搜索图标 / 搜索框: 展开搜索栏，进入 Search Results 页（独立 flow）

Screen 2: Content Detail
  主操作: 查看内容详情 → 点击播放 / 收藏
  关键组件（视频场景）:
    - 顶部嵌入式 Player 区（16:9，全宽）:
        默认态: 内容 Thumbnail + 居中 Play 圆形按钮
        可选: 自动播放 muted 预告片（20 秒后自动停止）
    - 内容信息区（Player 正下方）:
        标题（h1，大字）+ 年份 + 评级 Badge（TV-MA / PG-13）+ 时长 / 季集数
        动作行: Button("▶ Play", .primary) / Button("+ My List", toggle) / Like / Share / 「···」MoreMenu
    - Tabs（切换区域）:
        Episodes Tab: 季 Picker（Select 下拉）+ 集数列表（缩略图 + 集名 + 时长 + 简介 + Play 按钮）
        Related Tab: 相关内容 Grid（同类型推荐）
        Details Tab: 完整简介 + 演职员表 + 标签
  关键组件（音乐/专辑场景）:
    - Album Hero: 专辑封面（大图）+ 专辑名 + 艺术家名 + 年份 + 总时长
    - 动作行: Button("▶ Play All", .primary) / Button("🔀 Shuffle") / Button("+ My Library", toggle)
    - Track List: 每行（序号 + 歌名 + 艺术家 + 时长 + 「···」MenuTrigger）
        hover 时序号替换为 Play 图标（点击直接播放该曲）
  → 点击 Play（任意场景）: → Screen 3
  → 内容需订阅（点击 Play 后判断）: 弹出 Paywall Modal → Flow 2 Screen 1
  → 点击「+ My List / Library」: 即时 Toggle（optimistic）或 Playlist Picker → Flow 3

Screen 3: Active Playback（视频场景）
  主操作: 播放 / 暂停，拖拽进度，选择下一集
  关键组件:
    - Video Player（全屏或嵌入式 16:9，宽屏优先）
    - Controls Bar（鼠标移入显示，3 秒静止后淡出）:
        左: Play/Pause + 下一集跳过 + 音量 Slider + 当前时间 / 总时长
        中: Progress Slider（可拖拽，hover 显示缩略图预览）
        右: 字幕 CC + 画质 Select（Auto/1080p/720p）+ 全屏切换
    - Autoplay Countdown Widget（剧集结束前 15s 浮出，右下角）:
        「下一集：[剧集名]」+ 倒计时数字 + Button("Skip") + Button("Cancel")
    - Related Content Sidebar（宽屏可选，右侧 1/3 列）: 推荐内容卡片列表
  → 剧集播放结束: Countdown 归零自动播放下一集（已点 Cancel 则停止）
  → 用户导航离开: 进度自动保存；下次进 Home 首屏显示「Continue Watching」进度卡片
```

**Exit State**: 内容播放中；音乐场景中 Bottom Player 持久化，用户可继续浏览其他页面
**Empty State**: "Continue Watching" 区块无内容时不显示（不展示空状态 Section，等用户有观看记录再出现）

---

### Flow 2: 订阅升级 / Paywall（Subscription Upgrade）

**在此场景的特殊性**: Paywall 触发时机是 Play 动作（不在 Browse 页拦截）；Plan 比较必须在同一屏完成（Free vs Premium 功能对比表）；订阅完成后直接回到上一次触发 Paywall 的内容并自动播放（不跳转 Dashboard）

**前置条件**: 用户已登录；当前账号为 Free 用户或订阅已到期（Premium 用户不触发此 flow）；用户点击了付费保护内容的 Play 按钮
**若前置条件不满足**: Premium 用户 → 直接播放，不触发 Paywall；未登录用户 → 先触发注册引导，注册完成后再进入此 flow

**Entry**: 用户点击 Play 时发现内容需要订阅，弹出 Paywall Modal

**Screens**:
```
Screen 1: Paywall / Plan Comparison Modal（全屏 Modal Wizard）
  主操作: 选择订阅方案（Annual / Monthly）
  关键组件: Plan Comparison Card（功能对比，突出 Premium 优势）, Toggle（Annual / Monthly 切价）, CTA Button「Start Free Trial」/ 「Subscribe」
  → 选择方案并点击 CTA: Screen 2
  → 关闭 Modal: 返回内容详情页（内容可继续浏览但无法播放）

Screen 2: Payment Method
  主操作: 选择支付方式并填写信息
  关键组件:
    - Order Summary（右侧 Sticky Card 或底部汇总行）:
        选择的 Plan + 价格 + 免费试用说明（「After X-day trial: $XX/mo」）
        计费周期说明（「Billed annually / monthly. Cancel anytime.」）
    - RadioGroup（支付方式选择）:
        Credit / Debit Card（选中后展开字段区域）
        PayPal（选中后显示「Continue with PayPal」按钮，OAuth 窗口）
        Google Pay / Apple Pay（Web Payment Request API，选中后一键确认弹窗）
    - 信用卡表单（仅 Card 选中时展开，其余方式折叠隐藏）:
        Input（Card Number，PAN masking，16位自动格式化）
        Input Row: Expiry（MM/YY）+ CVV（3/4位，带 ? tooltip 说明位置）
        Input（Name on card）
    - Checkbox「保存支付方式以备下次使用」（已登录用户可见）
    - Button「Confirm & Subscribe」（主 CTA，全宽，loading 态显示 spinner + 表单 disabled）
    - 支付失败：Alert（inline 红色提示）+ Button「Try again」+ Button「Use another method」
  → 点击「Confirm & Subscribe」: 进入 loading 态 → Screen 3
  → 支付失败: 停留 Screen 2，inline 显示错误原因（卡号无效 / 余额不足）

Screen 3: Success / Confirmation
  主操作: 开始享受会员（CTA:「Start Watching」）
  关键组件: Success Icon, 会员权益摘要（3 条），「Start Watching」Button
  → 点击「Start Watching」: 跳回触发 Paywall 的内容详情页，自动播放
```

**Exit State**: 用户成为 Premium 订阅者，内容立即可播放，Paywall Modal 消失
**Empty State**: 不适用

---

### Flow 3: 添加到 Playlist / Watchlist

**在此场景的特殊性**: Playlist 操作不跳转独立的 Playlist 管理页面，而是在当前页面用 Sheet 或 DropdownMenu 完成；添加成功后用 Transient Toast 确认（「Added to [Playlist Name]」）

**前置条件**: 用户已登录；已注册（有账号），可以有或无 Library（Playlist 创建无前置条件）
**若前置条件不满足**: 未登录用户点击收藏/Watchlist → 注册引导 Modal

**Entry**: 用户在内容卡片三点菜单 或 内容详情页点击「Add to Playlist / Watchlist」

**Screens**:
```
Screen 1: Content Card / Content Detail（当前页面不变）
  主操作: 点击卡片 DropdownMenu 「Add to Playlist」或详情页「+ Add to Watchlist」
  关键组件: DropdownMenu（三点菜单）, Button（「+ Watchlist」图标按钮）
  → 点击操作: 打开 Screen 2（Sheet 或 Popover，不离开当前页）

Screen 2: Playlist Picker（Sheet 或 Popover）
  主操作: 选择已有 Playlist 或 创建新 Playlist
  关键组件: 已有 Playlist 列表（RadioGroup 或 CheckboxGroup）, 「+ Create New Playlist」入口
  → 选择已有 Playlist: 直接添加并 Toast 确认，Sheet 关闭
  → 点击「Create New Playlist」: Screen 3

Screen 3: Create Playlist（Sheet 内展开或新 Dialog，不跳页面）
  主操作: 输入 Playlist 名称并保存
  关键组件: Input（Playlist 名称）, Optional: 隐私设置 RadioGroup（Public / Private）, Save Button
  → 点击 Save: 创建并添加内容，Toast「Created and added to [Name]」, Sheet 关闭
  → 点击 Cancel: 返回 Screen 2（Playlist Picker）
```

**Exit State**: Toast「Added to [Playlist Name]」短暂出现后消失；内容详情页中「+ Watchlist」图标变为已选中状态（Filled Heart / Check）
**Empty State**: Library 中无 Playlist 时，Picker 只显示「+ Create New Playlist」入口（不显示空列表 Section）

---

---

### Flow 4: 订阅到期续费（Subscription Renewal After Expiry）

**在此场景的特殊性**: 续费与首次订阅（Flow 2）的关键区别在于——用户已经有付款记录，续费路径可以大幅缩短：使用已存支付方式「一键续费」是主路径，而非强制重新输入支付信息。平台还应在到期前后多点触发提醒（Banner、邮件、播放拦截），而非仅在用户想播放时才被动告知。SoundCloud（flow_id 6593）的「订阅概况 → 取消 → Reactivate 入口」展示了完整的订阅生命周期管理结构，其「Reactivate」流程是续费体验的参考原型。

**行业共识**: 主流流媒体平台（Netflix、Spotify、SoundCloud）均采用「已存支付方式一键续费 + Banner 提醒」模式。

**前置条件**: 用户已登录；账号曾持有有效订阅（有付款记录和已存支付方式）；当前订阅已到期（或在宽限期内）
**若前置条件不满足**: 从未订阅过（无付款记录）→ 走 Flow 2（完整首订流程）；订阅仍有效 → 无需 Renewal，直接播放；无有效支付方式 → 续费 Modal 内需填写新支付方式

**Entry**: 点击 Play 付费内容时被 Expired 拦截，或 Home 页顶部 Expired Banner CTA「Renew Now」

```text
Screen 1: 到期触发点（多入口）
  情况 A — Home 页顶部 Banner:
    - 黄色/橙色警告 Banner（全宽）:「Your subscription expired on Apr 20. Renew to keep watching.」
    - Banner CTA:「Renew Now」→ Screen 2
    - Banner 可关闭（[×]）
  情况 B — 播放付费内容时被拦截:
    - Content Detail 页 Play 按钮变为「🔒 Renew to Watch」
    - 点击后弹出 Renewal Modal → Screen 2

Screen 2: Renewal Modal（方案选择）
  主操作: 确认续费方案（以上次方案为默认）
  关键组件:
    - Modal 标题:「Renew your subscription」
    - Plan 选项（默认选中上次使用的方案）:
        ○ Monthly — $9.99/month
        ● Annual — $79.99/year（Save 33%，上次选择）Badge「Your previous plan」
    - 已存支付方式预览:「Renew with Visa ending in 1234」（主 CTA）
    - 次 CTA:「Use a different payment method」（展开 Screen 2a）
    - 账单说明:「You'll be charged $79.99 today. Cancel anytime.」
  → 点击「Renew with Visa...」: 直接提交 → Screen 3（跳过支付填写步骤）
  → 点击「Use a different payment method」: Screen 2a

Screen 2a: 更换支付方式（可选分支）
  主操作: 输入新支付方式信息
  关键组件: 标准支付表单（卡号/有效期/CVV）、PayPal/Google Pay 选项
  → 确认支付方式: 返回 Screen 2（已更新的支付预览）

Screen 3: 续费成功
  主操作: 确认续费完成，开始播放
  关键组件:
    - 成功状态图标 + 标题:「Welcome back!」
    - 订阅摘要:「Premium · Active until Apr 27, 2027」
    - 主 CTA:「Continue Watching」（恢复播放触发 Paywall 的那段内容）
    - 次 CTA:「Back to Home」
  → 点击「Continue Watching」: 关闭 Modal，自动播放被拦截的内容
  → Home 页 Expired Banner 消失，整体 UI 恢复 Premium 态
```

**Exit State**:

- ✅ 续费成功：订阅立即恢复，Home 页 Banner 消失，被拦截的内容自动开始播放
- ❌ 支付失败（卡无效/余额不足）：Screen 2 内 inline 错误提示 + 「Update payment method」入口
- ↩ 关闭 Modal：用户继续以免费态浏览，Banner 仍显示（下次进入付费内容仍会触发）

---

## Component Kit

按使用频率排序：

| 功能概念 | 具体用途 |
|---|---|
| 内容卡片 | 内容卡片（缩略图 + 标题 + 状态标签），Carousel Row 和 Grid 的基本单元 |
| 横向滚动内容行（手写）| 横向内容滚动行（Home 页 Trending / Recommended），支持 peek 显示下一张 |
| 范围滑块 | 播放进度条 + 音量控制，支持拖拽和键盘操作 |
| 标签页切换 | Content Detail 页标签（Episodes / Related / Details / About）|
| 下拉操作菜单 | 内容卡片三点菜单（Play next / Add to playlist / Share / Remove）|
| 侧边面板/抽屉 | Playlist Picker 右侧抽屉，保持背景内容可见 |
| 模态对话框 | Paywall Modal（Plan Comparison + Payment，3 步骤 Wizard）|
| 操作通知（Toast）| 收藏/添加 Playlist 成功确认（短暂，含 Undo 按钮）|
| 状态标签 | 内容类型标签（HD / 4K / LIVE / 评级），卡片右下角时长标签 |
| 进度条 | Continue Watching 进度条（卡片底部，显示已观看比例）|
| 用户头像 | 频道/创作者头像 |
| 单选组 | 订阅方案选择（Annual / Monthly），支付方式选择 |

---

## Anti-Patterns

- **播放时全页刷新（Playback triggers full page reload）**: 音乐流媒体中切换导航页面时 Bottom Player 消失 → 正确做法：Bottom Player 持久化，路由切换时保持播放状态，Player 不参与页面渲染
- **Browse 阶段弹出 Paywall（Paywall at browse, not at play）**: 用户还没决定是否要看某内容就被要求订阅 → 正确做法：只在用户点击 Play 时触发 Paywall，Browse 和内容详情页完全可访问
- **Playlist 操作跳转独立管理页面（Playlist opens a new page）**: 用户丢失当前浏览上下文 → 正确做法：Playlist Picker 用 Sheet 或 DropdownMenu，操作完成后原地 Toast 确认
- **无 Continue Watching 状态（No progress persistence）**: 用户中途退出后无法找到上次进度 → 正确做法：Home 页首屏显示「Continue Watching」Carousel，卡片底部显示播放进度条
