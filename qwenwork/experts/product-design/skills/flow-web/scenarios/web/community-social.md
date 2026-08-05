# Scenario: 社区 / 社交 Community & Social

## Identity
**Platform**: Web
**Definition**: 面向消费者或社群用户的内容发布、互动、私信全链路产品——核心价值在于将"发现内容→表达互动→建立连接"的参与飞轮最大化。
**Canonical Examples**: Threads（轻量文字社区）；Instagram Web（多媒体社区）；X/Twitter（实时话题讨论）；LinkedIn（职业社交社区）
**Not this scenario if**:
- 主要任务是卖家/团队协作管理内容（→ 用 SaaS 管理后台场景）
- 纯内容消费/订阅无互动功能（→ 用营销网站或娱乐流媒体场景）
- B2B 知识库或文档中心（→ 用开发者工具或内部运营场景）

---

## User Profile

| 维度 | 内容 |
|---|---|
| 主要角色 | 社区成员（Content Creator / Lurker / Active Participant）|
| 核心目标 | 发现感兴趣的内容、表达自我、与他人建立连接 |
| 心智模型 | 消费级社交 App，期望"像 Instagram 一样流畅"；对内容可见性和隐私有控制诉求 |
| 使用频率 | 高频日常（每日多次查看 feed）；内容创作为低频到中频 |
| 决策模式 | 探索发现（算法驱动）+ 关系驱动（关注者内容）双模式混合 |

---

## IA Template

**导航模式**: Left Sidebar（固定左侧，含 Logo + 图标导航 + 发帖 CTA），三栏布局（左导航 + 中间 Feed + 右侧推荐/信息栏）
> 理由：社交平台 feed 内容需要最大宽度展示；Left Sidebar 是 Web 社交端全行业共识（X、Instagram、Threads、LinkedIn 均如此）；右侧推荐栏提供算法引导的关系增长入口，不占 Feed 主干。

**页面层级**: Feed（Home）→ Profile → Post Detail → DM Inbox → DM Chat（双栏）→ Settings
> For You / Following 双 Tab 切换 Feed 算法视角，不是页面级跳转

**权限角色**: 已登录用户（完整功能）；未登录访客（只读，强制引导注册）；账号类型（Public / Private 影响关注审批流）

**数据密度**: 中（Feed 卡片为主，单列，无限滚动）+ 局部低（DM 对话气泡）+ 局部高（Profile 网格 / 推荐 Sidebar）
> Feed 卡片包含头像、用户名、时间戳、内容、互动操作栏；比电商商品卡简单，比 BI Dashboard 稀疏

**主要容器模式**:
- Composer Modal / Bottom Sheet（发帖叠加在 Feed 上，不跳转新页）：内容创作入口
- Post Detail Modal / 新页（点击展开帖子）：评论展示与回复
- DM 双栏布局（左侧会话列表 + 右侧消息区）：私信
- Per-message Context Menu（hover/long-press 触发）：消息操作
- Filter Sheet / Privacy Settings Page：账号管控

### 导航骨架图（ASCII）

```
┌─────────────────────────────────────────────────────────────────────┐
│  ┌──────────────┐  ┌─────────────────────────────┐  ┌───────────┐  │
│  │ ● Brand Logo │  │  [For You] | [Following]     │  │ 搜索/发现 │  │
│  │──────────────│  │─────────────────────────────│  │───────────│  │
│  │ 🏠 Home      │  │  ┌──────────────────────┐    │  │ Suggested │  │
│  │ 🔍 Search    │  │  │ [头像] 用户名 · 时间  │    │  │ Users (3) │  │
│  │ 🔔 Notif (3) │  │  │ 帖子内容文字/图片    │    │  │ [Follow]  │  │
│  │ ✉️  Messages  │  │  │ [♡ 12] [💬 4] [↗] [⊡]│    │  │           │  │
│  │ 👤 Profile   │  │  └──────────────────────┘    │  │ Trending  │  │
│  │              │  │  ┌──────────────────────┐    │  │ #Topic 1  │  │
│  │  [+ Post]    │  │  │ [头像] 用户名 · 时间  │    │  │ #Topic 2  │  │
│  │  ← 固定大 CTA│  │  │ 帖子内容文字/图片    │    │  │ #Topic 3  │  │
│  └──────────────┘  │  │ [♡ 8] [💬 1] [↗] [⊡] │    │  │           │  │
│                    │  └──────────────────────┘    │  │ Footer    │  │
│                    │  ↕ 无限滚动                   │  └───────────┘  │
│                    └─────────────────────────────┘                  │
├─────────────────────────────────────────────────────────────────────┤
│  Composer Modal（叠加在 Feed 上方）                                   │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ [× 关闭]                                        [发布 →]    │    │
│  │ [头像] What's on your mind?                                  │    │
│  │ ─────────────────────────────────────────────────────────   │    │
│  │ [📷] [GIF] [📍] [😊]        [隐私: 所有人 ▾] [发布按钮]     │    │
│  └─────────────────────────────────────────────────────────────┘    │
├─────────────────────────────────────────────────────────────────────┤
│  DM（双栏）                                                           │
│  ┌────────────────┐  ┌───────────────────────────────────────────┐  │
│  │ [🔍 搜索会话]  │  │ 用户名 · 在线                              │  │
│  │ ────────────── │  │ ─────────────────────────────────────────  │  │
│  │ [头像] Alex    │  │    [气泡] 对方消息 10:23 AM               │  │
│  │ 上次消息预览   │  │         [气泡] 我的回复 10:24 AM          │  │
│  │ ────────────── │  │    [气泡] 对方消息 10:25 AM               │  │
│  │ [头像] Jamie   │  │ ─────────────────────────────────────────  │  │
│  │ 上次消息预览   │  │ [😊] [📷] [输入框 Write a message...] [➤] │  │
│  └────────────────┘  └───────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

#### 图 2：关键状态对比图（Key State Variations）

```
左：Home Feed 正常态（有内容，For You 激活）    右：Following Tab 空状态（新账号，无关注）

┌────────────────────────────────────┐  ┌────────────────────────────────────┐
│ [For You] | [Following]            │  │ [For You] | [Following]  ←激活     │
├────────────────────────────────────┤  ├────────────────────────────────────┤
│ ┌──────────────────────────────┐   │  │                                    │
│ │ [头像] Alex · 2h             │   │  │                                    │
│ │ 今天遇到了一件有趣的事...    │   │  │         👥                         │
│ │ [♡ 12] [💬 4] [↗] [⊡]      │   │  │   You're not following anyone yet. │
│ └──────────────────────────────┘   │  │   Follow people to see their       │
│ ┌──────────────────────────────┐   │  │   posts here.                      │
│ │ [头像] Jamie · 45m           │   │  │                                    │
│ │ 附一张今日通勤照片 🚆        │   │  │   [Find people to follow]          │
│ │ [图片]                       │   │  │                                    │
│ │ [♡ 8] [💬 1] [↗] [⊡]       │   │  │                                    │
│ └──────────────────────────────┘   │  │                                    │
│ ↕ 无限滚动                         │  │                                    │
└────────────────────────────────────┘  └────────────────────────────────────┘
```

---

#### 图 3：覆层层级图（Overlay Hierarchy）

```
┌──────────────────────────────────────────────────────────────────────────┐
│  ● Brand  🏠 🔍 🔔(3) ✉️ 👤   [+ Post]                                  │ ← Left Sidebar（z-100）
├────────┬──────────────────────────────────────────────┬──────────────────┤
│        │  [For You] | [Following]                     │  Suggested (3)   │
│ Sidebar│  ─────────────────────────────────────────── │  [Follow]        │
│        │  ┌──────────────────────────────────────┐   │  ────────────    │
│        │  │ [头像] Alex · 2h                      │   │  Trending        │
│        │  │ 今天遇到了一件有趣的事...              │   │  #Topic 1        │
│        │  │ [♡ 12][💬 4][↗][⊡] [···]            │   └──────────────────┤
│        │  └──────────────────────────────────────┘                      │
│        │                                                                 │
│        │  ┌──────────────────────────────────────────────────────────┐  │
│        │  │  Composer Modal（中）z-index: 300                         │  │
│        │  │  [× 关闭]                              [Post →]           │  │
│        │  │  [头像] What's on your mind?                              │  │
│        │  │  ─────────────────────────────────────────────────       │  │
│        │  │  [📷] [GIF] [📍] [😊]   [所有人 ▾]  [隐私配置]          │  │
│        │  └──────────────────────────────────────────────────────────┘  │
│        │    ▲ 触发: 点击 [+ Post] 或 Feed 顶部占位框                    │
│        │                                                                 │
│        │  ┌──────────────────────────────────────────────────────────┐  │
│        │  │  Share Sheet（中/底）z-index: 250                        │  │
│        │  │  Share post via…                                         │  │
│        │  │  [Repost] [Send via DM] [Copy link] [Share to…]         │  │
│        │  └──────────────────────────────────────────────────────────┘  │
│        │    ▲ 触发: 帖子卡片 [↗] 按钮                                   │
│        │                                                                 │
│        │  ┌──────────────────────────────────────────────────────────┐  │
│        │  │  Delete AlertDialog（中）z-index: 400                    │  │
│        │  │  Delete message?                                         │  │
│        │  │  ● Delete for you    ○ Delete for everyone               │  │
│        │  │  [Cancel]            [Delete]                            │  │
│        │  └──────────────────────────────────────────────────────────┘  │
│        │    ▲ 触发: DM 消息「…」→ Delete                               │
└────────┴─────────────────────────────────────────────────────────────────┘
  ┌──────────────────────────────────────────────┐
  │  ✓ Posted · View   [×]                        │  ← Toast（底部，z-500）
  └──────────────────────────────────────────────┘

触发关系说明:
- Composer Modal（中）: 点击 [+ Post] 触发，叠加在 Feed 上方，z-300，背景 Feed 叠暗
- Share Sheet（中）: 帖子卡片 [↗] 触发，z-250，列出转发/DM/复制链接等操作
- Delete AlertDialog（中）: DM「…」→ Delete 触发，z-400，强制选择删除范围后确认
- Toast（底）: 发布成功、Bookmark 成功等轻量反馈，z-500，3-5 秒自动消失
```

---

## 该场景独有的 IA/UX 决策

> 以下 5 条记录社区/社交场景与其他 Web 场景（SaaS、AI 产品、营销网站、电商）的本质 IA/UX 差异。

1. **内容类型决定 Composer 深度（Content-Type-Gated Composer Depth）**：纯文字帖（Threads）= 轻量 Modal，2步即完成；媒体帖（Instagram carousel）= 深度多步流（选图→逐张编辑→滤镜→元数据→隐私配置→发布），最多可达 41 屏。设计时必须按内容类型分叉 Composer 深度，而非用一套通用 composer 处理所有类型——SaaS 创建表单复杂度固定，电商结账步骤可预测，唯有社交场景的 Composer 深度随内容类型剧烈变化。

2. **发布前隐私配置层（Pre-Publish Privacy Control Layer）**：Metadata 配置屏固定包含「隐藏赞数」「关闭评论」「允许 Remix」「可见范围」四类开关，是社交场景特有的"发布前审核层"。普通内容创作工具（AI 写作、BI 报告）没有此层，SaaS 创建表单不涉及内容分发权限——这层 IA 决策在社交场景是必须而非可选。

3. **Feed 算法入口可见化（Visible Algorithm Entry Points）**：Feed 顶部 For You / Following 双 Tab 是显式的算法控制入口，给用户对内容分发路径的主动选择权；Right Sidebar 的 Trending Topics 是内容发现的辅助引擎。这是社交场景特有的"算法可感知"IA 层——其他场景（SaaS Dashboard、电商 PLP）的内容排序对用户不透明或不重要。

4. **消息删除的作用域决策（Scoped Deletion）**：DM 删除分「仅对我」vs「对双方」，是社交/隐私场景特有的破坏性操作分层（X、Telegram 均有明确的二选一 Modal）；评论删除则同步清除所有子回复（LinkedIn 有明确 Warning）。这种"删除影响范围的显式选择"在电商、SaaS 场景中不存在——删除订单或用户通常只有一种后果。

5. **iOS-to-Web 功能降级声明（Native Feature Overflow Handling）**：TikTok Web 端对部分消息类型（语音消息、高级 AR 效果）主动展示"此功能仅支持 App"提示，而非静默降级或隐藏入口。这是社交场景独有的"跨端能力溢出"IA 问题——Web 版功能集是移动端的子集，需为不支持的 native feature 预设 fallback 提示占位，而不是假装功能不存在。

---

## Canonical Flows

> 以下 flow 基于对真实产品的横向分析抽象而来，代表该场景的高频用户任务。

### Flow 1: Create and Publish Post

**在此场景的特殊性**: Composer 始终叠加在 Feed 上方（不跳新页），保留用户的浏览上下文；发布完成后以 Transient Toast 而非页面跳转确认，维持 Feed 连续性。媒体帖增加选图→编辑→元数据三个步骤，文字帖只需两步（写→发）。隐私配置是社交场景特有的发布前必经层。

**前置条件**: 用户已登录（访客无法发帖）；账号未被暂停或限制发布内容
**若前置条件不满足**: 未登录用户点击「+ Post」→ 触发注册/登录引导 Modal；账号受限 → 发布按钮 disabled + inline 提示原因

**Entry**: 点击 Left Sidebar 固定大 CTA「+ Post / New Thread」按钮，或点击 Feed 顶部 Composer 占位文本框

**Screens**:

```
Screen 1: Composer Modal（轻量文字帖，叠加在 Feed 上）
  主操作: 写入文字内容 → 发布
  关键组件:
    - Modal Header: × 关闭 + 「Post / Publish」主 CTA（内容为空时禁用）
    - 用户头像 + 占位文案"What's on your mind?"
    - 富文本输入区（支持 @ 提及 / # 话题 / URL 自动转换）
    - @ 触发: 浮动用户搜索补全列表
    - 底部 Toolbar: 📷 添加图片 / GIF / 📍 地点 / 😊 Emoji Picker
    - 隐私下拉:「所有人 ▾」/「仅好友」/「仅自己」（默认值由账号设置决定）
    - 字符计数（接近上限时变红，如 Twitter 的 280 字）
    - 背景 Feed 叠暗（Overlay Dim），不离开 Feed 上下文
  → 纯文字 + 点击「Post」: 发布请求 → Toast「Posted ✓ View」（Screen 1 关闭，Feed 刷新置顶新帖）
  → 点击 📷 添加媒体: 展开 Screen 2（媒体帖扩展流）
  → 点击 ×: 关闭 Modal，返回 Feed；若已输入内容触发「Discard post?」二次确认 Modal

Screen 2: 媒体选择 & 编辑（仅媒体帖）
  主操作: 从相册选图/录制 → 编辑调整
  关键组件:
    - 相册 Grid（多选模式，选中图片显示编号徽章 ①②③）
    - 拍摄按钮（直接开启摄像头）
    - 多选后可拖拽排序缩略图列表
    - 逐张编辑区: 裁剪 / 滤镜选择 / 调节亮度对比度
    - 媒体数量上限提示（如"最多 10 张"）
  → 确认选图 + 点击「Next」: Screen 3

Screen 3: Metadata & 隐私配置（媒体帖 + 复杂文字帖）
  主操作: 填写说明文字、配置隐私与互动开关
  关键组件:
    - 媒体缩略图预览（可点击返回编辑）
    - Caption 输入框（支持 @ / # / URL，字数计数）
    - 高级配置区（Toggle Group）:
        ○ 隐藏赞数（Hide Like Count）
        ○ 关闭评论（Turn Off Comments）
        ○ 允许 Remix / 合拍
    - 可见范围再次确认（下拉）
    - 添加地点（可选，输入后显示地点 Chip）
    - 右侧或底部持久预览（帖子最终样式）
    - 主 CTA:「Share / Post」按钮（媒体上传期间显示进度条，按钮置灰）
  → 点击「Share」: 上传 + 发布 → Toast「Posted · View」/ 跳至新帖详情页
  → 点击「Back」: 返回 Screen 2 重新编辑媒体
```

**Exit State**: Feed 刷新，新帖置顶（For You / Profile 均可见）；浮现 Transient Toast「Posted · View」（点击跳至帖子详情）
**Empty State**: Composer 内容为空时「Post」按钮禁用；媒体上传中途离开触发「You have unsaved changes」确认 Modal

---

### Flow 2: Browse Feed and Engage with Post

**在此场景的特殊性**: Feed 是核心产品面，互动操作（Like / Comment / Share / Bookmark）均在 Feed 卡片行内完成，无需跳转。评论展开为 Modal 或新页，评论区内支持 @ 提及、Emoji 反应、引用回复——这种"卡片内微操作 + 弹层深入"的双层结构是社交场景特有的，SaaS 列表行操作通常不需要情感化反馈。

**前置条件**: 用户已登录（未登录可只读 For You Feed，但无法 Like/Comment/Follow）；账号状态正常（未被暂停）
**若前置条件不满足**: 未登录用户点击 ♡/💬/Follow → 触发「Join to interact」登录引导 Modal，不阻断浏览；私密账号帖子对非关注者不可见，Profile Grid 显示锁定态

**Entry**: 点击底部或左侧「Home」导航，或启动应用默认进入 Feed

**Screens**:

```
Screen 1: Home Feed（算法 Feed 主界面）
  主操作: 浏览内容，决定是否互动
  关键组件:
    - 顶部 For You / Following 双 Tab（切换算法模式，无页面跳转）
    - Feed 卡片（单列，垂直堆叠）:
        头像 + 用户名 + 关系标签（Following / Suggested）+ 时间戳
        内容区（文字 / 图片 / 视频自动静音播放）
        互动操作栏: ♡ Like（含计数）/ 💬 Comment / ↗ Share / ⊡ Bookmark
        More（…）按钮: 举报 / 不感兴趣 / 关注
    - 右侧 Sidebar: Suggested Users（3条 + Follow 按钮）+ Trending Topics
    - 无限滚动（Intersection Observer），新内容批量追加
    - Feed 末尾空状态:「你已看完所有内容，刷新试试」+ Refresh CTA
    - 顶部未读内容提示 Badge（「↑ N new posts」，点击滚动至顶部）
  → 点击 ♡: Like 即时（乐观更新），图标变色，计数 +1
  → 点击 💬: Screen 2（评论区展开）
  → 点击 ↗: Share Sheet（转发到 Feed / 发 DM / 复制链接 / 分享至外部平台）
  → 点击 ⊡: Bookmark 成功 Toast「Saved」（留在 Feed）
  → 点击卡片非操作区 / 帖子文字: Screen 2（帖子详情 + 评论）
  → 点击头像 / 用户名: Screen 3（用户主页）
  → 点击 Follow（Sidebar）: 即时变「Following」（乐观更新）；私密账号变「Requested」

Screen 2: Post Detail & Comments（Modal 或新页）
  主操作: 查看评论、发表评论、表达 Emoji 反应
  关键组件:
    - 帖子完整内容（帖子卡片展开）
    - 互动操作栏（同 Feed，数据实时）
    - 评论区（线性列表，最新 / 热门 Tab 可切换）:
        评论行: 头像 + 用户名 + 评论内容 + 时间戳 + Emoji Reaction Strip
        二级回复折叠（「View N replies」展开）
        评论 hover/long-press: 上下文菜单（Like / Reply / Report / Delete（仅自己））
    - 评论删除（自己）: 「Delete comment?」确认 Modal，同步清除所有子回复（附 Warning 提示）
    - 底部固定评论输入框（Pinned Composer）:
        头像 + 输入框（支持 @ 提及 + Emoji）
        @ 触发浮动用户补全列表
        「Reply to [用户名]」引用条（点击 Reply 后出现，可取消）
        发送按钮（内容为空时禁用）
  → 点击「发送」: 评论追加到列表底部（乐观更新）+ Toast「Comment posted」
  → 点击 × / 返回: 关闭 Modal，回到 Feed

Screen 3: User Profile（查看他人主页）
  主操作: 了解用户，决定是否关注
  关键组件:
    - 头图 / 头像 / 用户名 / Bio / 网站链接
    - 统计栏: Posts N / Followers N / Following N（可点击查看列表）
    - Follow / Message 双按钮（已关注显示 Following + Message）
    - More（…）: 屏蔽 / 举报 / 限制
    - 内容 Grid / List 切换（帖子缩略图或完整帖列表）
    - 私密账号未关注态: Grid 区显示锁图标 + 「This account is private. Follow to see their posts.」
  → 点击「Follow」: 公开账号即时 Following；私密账号变「Requested」+ 提示 Modal
  → 点击「Message」: 打开 DM 会话（进入 Flow 3 Screen 1）
```

**Exit State**: 用户完成互动（Like / Comment / Follow）后留在 Feed 或 Post Detail，无强制页面跳转
**Empty State**: Following Tab 无内容（刚注册）显示「Follow people to see their posts here」+ Suggested Users 引导卡片

---

### Flow 3: Send and Manage Direct Messages

**在此场景的特殊性**: Web 端 DM 采用双栏布局（左侧会话列表 + 右侧消息区），而非 iOS 的全屏会话。消息操作（Reaction / Reply / Delete）通过 hover 触发的上下文菜单而非长按。删除分「仅对我」/「对所有人」两种范围，用户必须主动选择——这种"删除作用域的显式决策"是社交场景特有的 IA 问题。

**前置条件**: 用户已登录；目标用户未屏蔽当前账号（被屏蔽则无法发送 DM）；双方账号均处于正常状态
**若前置条件不满足**: 未登录 → 点击「Messages」触发登录引导；被对方屏蔽 → DM 入口不显示或发送静默失败；账号受限 → 「Your account is restricted from sending messages」提示

**Entry**: 点击 Left Sidebar「✉️ Messages」图标，或在用户主页点击「Message」按钮

**Screens**:

```
Screen 1: Messages Inbox（双栏入口）
  主操作: 找到目标会话或发起新对话
  关键组件:
    - 左栏（会话列表，固定宽度）:
        搜索框（实时过滤会话列表）
        「New Message（✏️）」按钮（触发用户搜索 Modal）
        会话行: 头像 + 用户名 + 最后消息预览（截断）+ 时间戳 + 未读角标（蓝色）
        右键 / hover 快捷操作: Delete conversation / Mark as read
    - 右栏（默认空态）:
        空态插图 + 「Select a conversation to start messaging」
        或「Your messages」大标题 + 「Send a new message」CTA
  → 点击会话行: 右栏切换至 Screen 2（会话内容）
  → 点击「New Message」: 用户搜索 Modal → 选择用户 → 右栏切换至新对话 Screen 2

Screen 2: DM Chat（右栏消息区）
  主操作: 撰写发送消息、对消息执行操作
  关键组件:
    - 顶部对话 Header: 头像 + 用户名 + 在线状态 + More（…）管理选项
    - 消息气泡区（线性时序，最新消息置底）:
        对方消息: 左侧气泡（浅背景）+ 时间戳
        我的消息: 右侧气泡（品牌色背景）+ 时间戳 + 已读回执（√√）
        消息 hover → 浮现操作条:「❤️」快速 Like + 「…」更多操作菜单
        Emoji Reaction 角标贴附气泡右下角（点击查看反应详情）
    - 媒体消息: 图片气泡（点击全屏预览）/ GIF 自动播放 / 音频（仅显示「Open in app」横幅）
    - 「Replying to [用户名]」引用条（点击 Reply 后锚定在输入框上方，可取消）
    - 底部输入区（固定）:
        😊 Emoji Picker / 📷 图片 / GIF 选择器
        输入框（Write a message...，自动扩展高度至上限后滚动）
        发送按钮（内容为空时禁用）
  → 点击「❤️」: 消息追加 Like 反应（乐观更新，角标计数 +1）
  → 点击「…」→ Reply: 引用条出现，发送后气泡显示引用内容
  → 点击「…」→ Delete: Screen 3（删除范围选择）
  → 输入 + 点击发送: 消息追加到对话底部（乐观更新），异步确认后显示√

Screen 3: 删除消息确认（Modal）
  主操作: 确认删除范围
  关键组件:
    - Modal 标题:「Delete message?」
    - 选项 Radio / 两个按钮:
        「Delete for you」— 仅从我的视角删除（对方仍可见）
        「Delete for everyone」— 双方均删除（有时间限制或权限要求）
    - 被删消息预览（简短截断，让用户确认是否是目标消息）
    - 取消按钮
  → 选择范围 + 确认: 气泡从对话中移除（「This message was deleted」占位文本或直接消失，取决于策略）
  → 点击取消: 关闭 Modal，消息保留
```

**Exit State**: 消息成功发送后留在当前对话；删除操作完成后气泡消失（或显示「已删除」占位）
**Empty State**: 全新账号 Inbox 空态：插图 + 「No messages yet」+ 「Send a message to someone you know」+ 用户搜索 CTA

---

---

### Flow 4: 账号隐私与通知设置

**在此场景的特殊性**: 社交产品的隐私设置与 SaaS 权限配置根本不同——它影响的是「他人能看到什么」而非「自己能操作什么」。私密账号切换是高风险变更（影响所有已发布内容的可见性），必须有确认 Modal。通知设置则是纯个人偏好，按类别分开（互动/关注/评论/推荐），可即时 Toggle 无需确认。Threads（flow_id 10673）的「Private profile → 确认 Modal → Toggle 更新」是行业共识参考；flow_id 10674 的「屏蔽列表 → 解除屏蔽 → AlertDialog → Toast → 空列表」补全了「管理他人访问权限」这条次要路径。

**行业共识**: 出现在 Threads（flow_id 10673、10674）、Instagram、X 等主流社交平台中。

**前置条件**: 用户已登录；访问自己的账号 Settings（无法修改他人隐私设置）
**若前置条件不满足**: 未登录 → 访问 Settings 跳转登录页

**Entry**: Avatar 下拉菜单 → Settings，或 Left Sidebar 底部「Settings」图标

```text
Screen 1: Settings 主页
  主操作: 选择隐私或通知子页
  关键组件:
    - Settings 左侧子页导航（Account / Privacy / Notifications / Security）
    - 当前选中项高亮，主内容区显示对应设置
  → 点击「Privacy」: Screen 2
  → 点击「Notifications」: Screen 3

Screen 2: Privacy 设置页
  主操作: 切换私密账号开关、管理屏蔽列表
  关键组件:
    - 「Private profile」Toggle（含说明文案：「Only approved followers can see your posts and interactions」）
    - 当前为 Public → 点击 Toggle: Screen 2a（确认 Modal）
    - 当前为 Private → 点击 Toggle: 直接切回 Public，无 Modal（降低隐私级别不需二次确认）
    - 「Blocked profiles」入口 → 打开 Screen 2b（屏蔽列表）
    - 「Restricted accounts」入口（可选）
    - 「Who can mention me」Select（Everyone / People you follow / No one）
    - 「Who can reply to my posts」Select（同上）

Screen 2a: 切换为私密账号确认 Modal
  主操作: 确认将账号设为私密
  关键组件:
    - Modal 标题:「Switch to private account?」
    - 说明文案:「Only people you approve will be able to see your posts. Your existing followers won't be affected.」
    - [Switch to private]（主按钮）/ [Cancel]（次要）
  → 点击「Switch to private」: Modal 关闭，Toggle 切换为 ON，说明文案更新
  → 点击「Cancel」: Modal 关闭，Toggle 保持 OFF

Screen 2b: 屏蔽列表 Modal
  主操作: 查看或解除屏蔽账号
  关键组件:
    - 屏蔽用户列表（头像 + 用户名 + 「Unblock」按钮）
    - 搜索栏（快速定位特定用户）
    - 空状态:「You haven't blocked anyone」
  → 点击「Unblock」: AlertDialog「Unblock @username? They'll be able to see your posts and send you messages again.」
    - [Unblock]（主按钮）→ Toast「@username unblocked」+ 该行从列表移除
    - [Cancel] → 关闭 AlertDialog，屏蔽保留

Screen 3: Notifications 设置页
  主操作: 按类别开关通知
  关键组件:
    - 通知类别 Toggle 列表（按节分组）:
        互动通知: 「Likes」「Comments」「Reposts」「Mentions」
        关系通知: 「New followers」「Follow requests」
        推荐通知: 「Suggested posts」「Trending topics」
    - 每个 Toggle 即时生效（无需点击 Save），变更后无 Toast（静默保存）
    - 「Pause all notifications」总开关（置顶，关闭后所有 Toggle 变 disabled）
```

**Exit State**:

- ✅ 私密模式开启：Private profile Toggle 显示 ON，说明文案更新，新关注者需审批
- ✅ 解除屏蔽：Toast「@username unblocked」，屏蔽列表移除该行
- ✅ 通知偏好调整：各 Toggle 即时保存，无需额外确认

---

## Component Kit

按使用频率排序：

| 功能概念 | 具体用途 |
|---|---|
| 侧边面板/抽屉 + 模态对话框 | Composer Modal（发帖）/ 删除确认 Modal / 媒体全屏预览 |
| 用户头像 | Feed 卡片头像 / DM 气泡头像 / Profile 大头像 |
| 多行文本输入 | Composer 文字输入（自动扩展高度）/ DM 输入框 |
| 操作通知（Toast） | 发布成功确认 / Bookmark 确认 / Like 撤销 Undo |
| 标签页切换 | For You / Following Feed 切换 / 评论热门 & 最新切换 |
| 下拉操作菜单 | 帖子「…」更多操作 / 消息上下文菜单（hover 触发）|
| 锚定浮层 | Emoji 反应选择器（hover Emoji Strip）/ @ 用户补全列表 |
| 计数角标 | 导航未读数角标 / 消息未读蓝点 / 媒体多选编号 |
| 分隔线 | Feed 卡片分隔线 / DM 日期分组分隔 |
| 加载骨架屏 | Feed 卡片加载占位 / DM 会话列表骨架屏 |
| 开关 | 隐私配置开关（隐藏赞数 / 关闭评论 / 允许 Remix）|
| 选择下拉 | 帖子可见范围下拉 / 用户搜索（新建 DM）|
| 单选组 | 删除消息范围选择（仅我 / 所有人）|
| 可滚动区域 | DM 消息区域滚动容器（固定 viewport 内滚动）|
| 选择下拉（搜索模式） | @ 提及用户搜索 / 新建 DM 用户搜索 |

---

## Anti-Patterns

> 该场景中真实存在的常见设计错误，基于研究观察。

- **发帖后全页跳转（Full-page Redirect After Post）**: 发布成功后跳转至帖子详情页，打断 Feed 浏览连续性 → 正确做法：使用 Transient Toast「Posted · View」，Feed 原地刷新置顶新帖，用户可选择点击 View 跳至帖子，或留在 Feed 继续浏览。

- **统一 Composer 不区分内容类型（One-size Composer）**: 文字帖和多媒体帖使用同一个 Composer 深度，造成文字帖冗余步骤或媒体帖配置不足 → 正确做法：按内容类型分叉 Composer 深度，文字帖 2 步（写→发），媒体帖 4-5 步（选→编辑→配置→隐私→发布）。

- **删除消息无范围选择（Silent Delete）**: 删除 DM 消息时直接双端删除，未给用户选择「仅对我」的机会 → 正确做法：触发 Modal 让用户主动选择删除作用域，明确说明两种后果的差异。

- **关注私密账号后无状态反馈（Silent Requested State）**: 发送关注请求后按钮无变化，用户不清楚请求是否发出 → 正确做法：Follow 按钮即时变为「Requested」灰色态，并弹出提示「Follow request sent. They'll need to approve it.」

- **评论区无引用回复（Flat Comment Tree）**: 评论区所有回复平铺，用户无法快速判断回复对象 → 正确做法：支持 Reply 引用功能，回复气泡展示被引用消息片段；评论行 hover 时显示「Reply」快捷操作。

- **算法 Feed 无逃脱出口（Algorithm Lock-in）**: 只有 For You 单一 Feed，无 Following 或分类 Tab，用户无法控制内容来源 → 正确做法：提供 For You / Following 双 Tab，Right Sidebar 显示推荐理由（"Suggested for you"），给用户对算法的感知和部分控制权。
