# Scenario: Mobile Messaging（移动端私信/群聊）

> **研究来源**：基于对 XChat、Instagram DM、Daze、Abode、Substack、BeReal、Gizmo、Sora 等真实 iOS 产品 flow 和页面的横向分析抽象，不代表任何单一产品的具体实现。

---

## Identity

**Platform**: Mobile (H5 / React Native)
**Definition**: 以私信与群聊为核心交互方式的移动端消息 App，用户可以与个人联系人或群组进行多媒体实时通信，支持文字、图片、语音消息，以及 emoji 反应等社交互动。

**Canonical Examples**: WhatsApp、Telegram、Signal、iMessage

**Not this scenario if**:
- 产品是公开 Feed + 评论模式的社交媒体（改用 mobile/consumer-social）
- 产品是 AI 助手对话（改用 mobile/ai-assistant）
- 产品是企业内部沟通工具（Slack/Teams 风格，以频道为主）
- 主要在 Web 端使用，移动端为辅

---

## User Profile

| 维度 | 内容 |
|---|---|
| **主要角色** | 私聊用户（1:1 实时对话）/ 群聊用户（家庭群/朋友群/兴趣群）|
| **核心目标** | 快速发出消息并确认对方收到 / 在群组中保持联络感 |
| **心智模型** | 类 SMS/iMessage 体验：会话列表 → 点击进入 → 发消息，消息是时间线结构而非 Feed |
| **使用频率** | 极高频（多次/天）；每次使用时间短（1-5 分钟），随时随地碎片化 |
| **决策模式** | 即时反应型：消息通知驱动打开 App，无固定浏览习惯 |
| **容错期望** | 低容错：消息发送状态必须明确（发送中/已送达/已读），误删对话需 Dialog 确认 |

---

## IA Template

**导航模式**: Bottom Tab Bar（私信类 App 主流模式）

```
Tab 1: 聊天 / Chats   — 会话列表（核心视图）
Tab 2: 通话 / Calls   — 语音/视频通话记录
Tab 3: 联系人 / Contacts — 联系人列表
Tab 4: 设置 / Settings  — 账户、通知、隐私设置
```

**选择建议**: 纯私信/群聊 App → Tab Bar 4-5 Tab；嵌入在社交 App 内的 DM → 作为主 App 的一个 Tab 存在（如 Instagram DM）

**页面层级**: 2-3 级
```
L1: 聊天列表（Chat List）
L2: 会话线程（Conversation Thread）
L3: 群组详情（Group Info）/ 联系人详情（Contact Info）/ 媒体查看（Media Viewer）
```

**权限流结构**:
```
Microphone（语音消息）:
  → 首次点击麦克风 → 系统麦克风权限弹窗（无需说明页，语音消息场景目的显而易见）

Camera / Photos（图片/视频附件）:
  → 首次点击附件 → 系统 Photos 权限弹窗

Notifications（消息通知）:
  → Onboarding 完成后询问（非强制，但对消息 App 是核心功能）

Contacts（联系人同步）:
  → 首次进入"联系人"或"新建会话"时请求
```

**数据密度**: 低-中
- 聊天列表：每行 = 头像 + 名称 + 最新消息预览 + 时间 + 未读角标
- 会话线程：气泡列表（文字/图片/语音/表情），自动滚到最新
- 特殊元素：语音消息波形图、emoji 反应 badge、「已读」状态文字

**主要容器模式**:
| 场景 | 容器 |
|---|---|
| 新建会话（联系人选择）| Full-screen Modal（Stack Push）|
| 群组详情 / 成员管理 | Stack Push 页面 |
| 媒体附件预览（图片/视频）| Full-screen Modal（黑色背景）|
| Emoji 反应 picker | Bottom Sheet（Medium 高度）|
| 删除/退出对话确认 | Dialog |
| 附件来源选择（图片/拍照）| Action Sheet |
| 静音时长选择 | Action Sheet / Bottom Sheet |

**导航骨架图（ASCII，会话线程）**:
```
┌────────────────────────────────────┐
│  Status Bar                         │
├────────────────────────────────────┤
│ ←返回  [头像] 名称 / 群组名  [···] │  ← Navigation Bar
├────────────────────────────────────┤
│                                    │
│  ──── 今天 ────                    │  ← Section Header（日期分隔）
│                                    │
│  对方消息（左对齐，灰色气泡）       │
│    [🌊] 0:12  ▶                   │  ← 语音消息气泡
│                                    │
│            我的消息（右对齐）       │
│            ← 你好！                │
│              已读 ✓✓              │  ← 消息状态
│                                    │
│  对方消息 +  👍 1                  │  ← emoji 反应 badge
│                                    │
├────────────────────────────────────┤
│ [📎] [      消息...       ] [🎤]  │  ← Composer（常驻底部）
└────────────────────────────────────┘
```

---

## 该场景独有的 IA/UX 决策

1. **Composer 必须是单一恒定底部栏，通过图标切换模式而非多个 CTA** — 私信 Composer 不同于 AI 助手（只需文字输入），需要承载文字、图片附件、语音录制三种输入模式。正确做法是：单一输入框 + 右侧/左侧固定图标（📎 附件、🎤 语音），点击不同图标在同一 Composer 区域切换输入模式，而非弹出额外 Panel 或跳转新页面——Instagram（flow 2875）和 Daze（flow 9126）均采用此架构，保持 Composer 视觉重心稳定。

2. **语音消息必须有完整的五状态生命周期，不能直接发送** — 语音消息从录制到送达共 5 个明确状态：① 麦克风权限 → ② 录制中（波形 + 计时器 + 取消/停止）→ ③ 预览（播放/取消/发送三按钮）→ ④ 发送中（气泡内 spinner）→ ⑤ 已送达（波形气泡 + 时长）。跳过「预览」步骤直接发送会导致用户无法确认录音内容是否清晰，增加误发风险；Daze（flow 9126，9 屏）是完整实现的标准参照。

3. **emoji 反应必须双层视觉反馈：持久内联 badge + 瞬态动画确认** — 用户点击 emoji 反应后，需要两种并行反馈：① 持久状态——气泡旁显示小 emoji badge（含计数「👍 1」），在会话中永久可见；② 瞬态动画——emoji 放大弹出后消失，给操作即时感知。只有内联 badge 而无动画，用户会怀疑操作是否成功；只有动画而无持久 badge，会话刷新后状态消失——XChat（flow 11654）同时实现了两层反馈，是行业标准模式。

4. **消息请求必须与普通会话物理隔离，不能合并在聊天列表** — 陌生人发来的消息请求如果直接出现在聊天列表，会破坏「已知联系人」的安全感预期，特别是在 E2E 加密场景下。正确做法：聊天列表顶部有独立的「Message Requests」入口（显示待处理数量 badge）；点击进入请求列表，每个请求显示受保护预览（有限消息预览）+ Accept / Delete 二选一底部栏；接受后会话升级为正式线程，并显示端到端加密状态提示——XChat（flow 11664）是标准实现。

5. **聊天列表的长按 Contextual Menu 和左滑 Action 必须分工明确，不能重叠** — 左滑提供高频、快捷的两个操作（静音 Mute + 删除 Delete），不超过两项，防止误触；长按显示完整 Contextual Menu（Mark Unread / Mute / Pin / Rename / Delete / Archive），涵盖所有管理动作。两者不应完全重叠（都做相同的事）也不应分工不清（用户不知道哪个操作在哪里）——Substack（flow 4494）+ XChat（flow 11674）均验证了这套左滑/长按分工模式。

---

## Canonical Flows

> 以下 flow 基于 9 个真实产品样本横向分析抽象。括号内标注「行业共识」表示 3 个以上产品采用相同模式。

---

### Flow 1: 开始新会话（Start New Conversation）

**在此场景的特殊性**: 私信 App 新建会话的入口与 IM 工具（Slack/Teams）有根本差异——私信 App 以「联系人」为单位而非「频道」，新建会话必须先选人再建线程（而非进入公开频道）。群聊需要给群命名，这是首次使用者最常忽略的步骤。多选联系人时用 chip 展示已选状态是行业共识（XChat flow 11665 + Gizmo flow 10031 均如此），让用户清楚自己选了哪些人。

**行业共识**：XChat（flow 11665）、Instagram（flow 2873）、BeReal（flow 4938）、Gizmo（flow 10031）均采用「聊天列表右上角 Compose 图标 → 联系人选择页（支持搜索 + Recents）→ 多选后 chips 展示 → 确认建线程」的完整流程。

**Entry**: 聊天列表 → 右上角 ✏️ Compose 图标

```
Screen 1: 聊天列表（Chat List）
  主操作: 浏览所有会话 / 发起新会话
  关键组件:
    - NavigationBar: 标题「消息」+ 右上角 Button（✏️ Compose）
    - SearchBar（搜索联系人名称或消息内容，置顶）
    - [可选] Pinned 会话分组（📌 头部，最多 3-5 条）:
        Section Header「置顶」
        Row: 头像 + 名称 + 最新消息预览 + 时间 + 未读 Badge
    - 普通会话列表（FlatList，按时间降序）:
        Row: 头像（圆形，60pt）+ 名称（加粗，有未读时）+ 最新消息预览（灰色单行截断）+ 时间戳
        Unread Badge（红色小圆角矩形，右侧）
        在线状态绿点（头像右下角，如平台支持）
    - [可选] Message Requests 入口（聊天列表顶部独立 Banner 行）:
        Text「1 条消息请求」+ 右箭头
  → 点击 ✏️: 跳转 → Screen 2（联系人选择）
  → 点击某条会话: Push → Screen 3（会话线程）
  → 点击「Message Requests」: Push → 消息请求列表

Screen 2: 新建会话（New Conversation）
  主操作: 选择联系人，创建 1:1 或群聊
  关键组件:
    - NavigationBar: Button「取消」（左）+ 标题「新消息」+ Button「创建群组」（右，文字按钮）
    - SearchBar（「搜索联系人」，自动获得焦点）
    - 已选联系人区（chips，输入框上方，初始隐藏）:
        Chip（头像缩略图 + 名称 + × 删除）
        横向 ScrollView，超出后可左右滑动
    - 联系人列表（Recents / All Contacts 分组）:
        Section Header「最近联系」
        Row: 头像 + 名称 + handle（@xxx）+ 右侧复选框
        Section Header「所有联系人」（按字母排序）
    - 右上角「下一步」Button（disabled 直到选中至少 1 人）
  → 选中 1 人: 直接进入 Screen 3（1:1 会话线程，无需确认步骤）
  → 选中 2+ 人: 右上角「下一步」激活 → Screen 2a（群组命名）

Screen 2a: 群组命名（Group Name）
  触发条件: 选中 2 名以上联系人
  关键组件:
    - NavigationBar: Button「返回」（左）+ 标题「新建群组」+ Button「创建」（右，disabled 直到有群名）
    - 头像组（选中成员头像横排）
    - TextField（「群组名称」，必填，autofocus）
    - 已选成员预览（小头像 + 名称 chips，只读）
  → 输入群名 + 点击「创建」: 创建群聊 → 进入 Screen 3（空群聊线程）

Screen 3: 会话线程（空状态，首次）
  主操作: 发出第一条消息
  关键组件:
    - NavigationBar: 返回箭头 + 头像（圆形）+ 名称/群名 + ··· 详情
    - Empty 区域:
        头像（大，80pt）+ 名称
        Text「这是你与 [名称] 的私信」或「欢迎来到群组！」
        [可选] 快速分享联系方式按钮
    - Composer（底部常驻）: 📎 + 输入框 + 🎤
  → 发出第一条消息: 消息气泡出现，会话线程进入 Screen 3a
  → 发送后: 聊天列表自动刷新，该会话置顶显示最新消息
```

**Exit State**:
- ✅ 1:1 会话：直接进入线程，Composer 激活可发消息
- ✅ 群聊：创建后进入空群聊，欢迎文字提示「[用户名] 创建了群组」
- ↩ 取消：返回聊天列表，无新会话创建

---

### Flow 2: 会话线程核心交互（文字 + 语音 + 图片）

**在此场景的特殊性**: 私信 App 的会话线程与 AI 助手最大的差异是**多媒体对等双向性**——双方均可发文字/图片/语音，且语音消息是移动端独有的高频交互（不同于 Web）。语音消息必须有完整的录制 → 预览 → 发送五状态生命周期（Daze flow 9126 是最完整实现）；图片附件通过系统 Photo Picker 选择，多张图在消息气泡中以网格布局展示；Swipe-to-reply 是引用回复的标准手势（Instagram flow 2876 确认）。

**行业共识**：Instagram（flow 2875/2876/2878）、Daze（flow 9126）、Abode（flow 4283）、UGLYCASH（flow 11211）均采用「底部常驻 Composer（文字 + 📎 + 🎤）+ 按图标切换输入模式」。

**Entry**: 聊天列表 → 点击任意会话行

```
Screen 1: 会话线程（Chat Thread）
  主操作: 查看消息历史 / 发送消息
  关键组件:
    - NavigationBar: 返回 + 头像（圆形，可点击查看详情）+ 名称 + ··· 操作菜单
    - 在线状态文字（「在线」/ 「最后上线 2 小时前」，NavigationBar 副标题）
    - 消息列表（FlatList，滚动到最新消息）:
        日期 Section Header（「今天」/ 「昨天」/ 「2024年1月5日」）
        文字气泡（左/右，圆角矩形）:
          Left: 灰色/白色气泡，头像（群聊时显示，1:1 时隐藏）
          Right: 品牌色气泡，右对齐
          底部状态文字（Right 气泡下方）: 「发送中...」→「已送达」→「✓✓ 已读」
        图片气泡（圆角，点击 → Full-screen Modal）
        语音消息气泡: 波形图 + 播放按钮 + 时长（如「0:24」）
        emoji 反应 badge（气泡角落，「👍 2」/ 「❤️」等）
    - 「正在输入...」指示器（对方输入时出现，三个跳动圆点）
    - Composer（固定底部，随键盘上移）:
        Button（📎 附件）
        TextInput（「消息...」，多行自动扩展）
        Button（🎤 语音，TextInput 为空时显示；有输入时切换为发送 ▲）
  → 点击 📎: Action Sheet（图库 / 拍照 / 文件）
  → 点击 🎤: 进入录音状态（Screen 2）
  → 长按任意消息: Context Menu（Screen 3 前置，内联弹出）
  → 右滑某条消息（Swipe-to-reply）: Composer 顶部出现引用预览条

Screen 2: 录音状态（Voice Message）
  主操作: 录制语音消息
  触发: 点击 Composer 右侧 🎤 按钮
  关键组件（录制中状态，覆盖 Composer 区域）:
    - 左侧: 录音波形动画（实时振幅）
    - 中间: 计时器（「0:05」，红点 + 数字）
    - Button（向左滑动取消，Label「< 取消」，灰色）
    - Button（⏹ 停止，右侧大圆形红色按钮）
    - [可选] 向上滑动锁定（持续录制而无需长按）
  → 点击停止 / 自然停止: 进入 Screen 2a（预览）
  → 向左滑取消: 取消录音，恢复 Composer 到初始状态

Screen 2a: 语音预览（Voice Preview）
  主操作: 确认后发送或取消
  关键组件（预览状态，仍在 Composer 区域）:
    - 波形图（静态，可点击播放确认内容）
    - 播放按钮（▶ 试听录音）
    - 计时器（总时长）
    - Button（🗑 删除，左侧，danger 色）
    - Button（发送 ▲，右侧，主色激活）
  → 点击「发送」: 语音消息发出，气泡出现在线程中，状态「发送中 → 已送达」

Screen 3: 图片附件发送
  主操作: 选择图片并发送
  触发: 点击 Composer 📎 → Action Sheet 选「图库」
  关键组件:
    - 系统 Photo Picker（iOS PHPicker，不可自定义）:
        支持多选（上限 5-10 张，可配置）
        右上角「选择 N 项」计数
        Button「添加」（选中后激活，右上角主色）
    - 返回 Composer 后（预览区）:
        图片缩略图横向 ScrollView，输入框上方
        每张图右上角「×」可移除
        TextInput 可同时输入说明文字
  → 点击「发送」: 图片气泡出现（单图 → 圆角大图；多图 → 2 列网格），进度指示 spinner 消失后显示完整图片
```

**Exit State**:
- ✅ 文字发送：气泡立即出现，底部状态「已送达」→ 对方读后「✓✓ 已读」
- ✅ 语音发送：波形气泡出现，对方可点击播放（播放后出现已听标记）
- ✅ 图片发送：缩略图气泡，点击全屏查看
- ❌ 网络异常：气泡旁显示「⚠️ 发送失败」+ 重试 Button

---

### Flow 3: Emoji 反应（Message Reaction）

**在此场景的特殊性**: Emoji 反应是私信 App 与 IM 工具最明显的差异之一——在不需要打断对话节奏的情况下对消息表达情感。触发方式是**长按消息**（与「选择文字/复制」等操作共享同一入口），因此快捷 emoji 行必须在 Context Menu 最顶部展示，而非嵌在操作列表中。XChat（flow 11654/11655）是双层视觉反馈（内联 badge + 瞬态动画）的最完整实现；BeReal（flow 4929）展示了深色主题下的快捷 emoji 设计；Sora（flow 7837）展示了完整 emoji picker 界面。

**行业共识**：XChat（flow 11654/11655）、Instagram（flow 2877）、BeReal（flow 4929）、Sora（flow 7837）均在长按后先展示快捷 emoji 行，再提供「完整 picker」入口。

**Entry**: 会话线程 → 长按任意消息气泡

```
Screen 1: 长按消息 → Context Menu + 快捷 emoji 行
  主操作: 选择 emoji 快速反应
  触发: 长按消息气泡 1 秒
  关键组件（内联弹出，覆盖在消息附近）:
    - 被长按的消息气泡（放大 1.05x 预览）
    - 快捷 emoji 行（气泡正上方，水平排列）:
        6-8 个高频 emoji（❤️ 👍 😂 😮 😢 🔥 👏 ···）
        最后一项「···」: 打开完整 picker
    - Context Menu 操作列表（emoji 行下方）:
        「回复」（Reply）
        「复制」（Copy）
        「收藏」（Bookmark，可选）
        「转发」（Forward）
        「删除」（Delete，danger 色，仅限自己的消息）
        「举报」（Report，仅限对方的消息）
    - 背景半透明暗色遮罩
  → 点击快捷 emoji: 反应立即添加，Context Menu 消失（进入 Screen 2）
  → 点击「···」: 打开完整 emoji picker（Screen 1a）
  → 点击背景遮罩 / 上滑: 关闭 Context Menu

Screen 1a: 完整 Emoji Picker（Bottom Sheet）
  主操作: 从全量 emoji 中选择反应
  容器: Bottom Sheet（Medium 高度，可拖拽展开）
  关键组件:
    - SearchBar（「搜索 emoji」，自动获得焦点）
    - Emoji 分类 Tab 横向（😀 🐣 🍕 ⚽ 🚗 💡 ❤️ 🔣）
    - Emoji 网格（6 列，FlatList / VirtualList，懒加载）
    - 最近使用区（「最近」，前 12 个）
  → 点击任意 emoji: 反应添加，Sheet 收起，进入 Screen 2

Screen 2: 反应已添加（Reaction Applied）
  主操作: 查看反应结果
  关键组件:
    - 消息气泡角落（右下角）: emoji badge（圆角小标签）+ 数量（如「👍 1」）
    - 瞬态动画: emoji 从气泡角落弹出放大 → 缩小至 badge（持续约 0.5s）
    - 已反应的 emoji badge 样式: 与未反应的 badge 有明显区分（边框高亮 / 背景加深）
  → 点击自己的反应 badge: 取消该反应
  → 点击他人的反应 badge: 查看「谁反应了」列表（Bottom Sheet，头像 + 名字）
  → 长按同一消息: 可切换反应（先取消原有，再选新 emoji）
```

**Exit State**:
- ✅ 反应成功：badge 持久显示在气泡角落；双层视觉反馈（瞬态动画 + 持久 badge）
- ↩ 取消反应：点击自己的 badge → badge 消失（如计数降为 0 则整个 badge 消失）

---

### Flow 4: 聊天列表管理（Conversation Management）

**在此场景的特殊性**: 聊天列表管理（置顶 / 静音 / 删除）是私信 App 区别于 IM 工具的高频操作——用户通常有 20-50 条会话，需要将重要联系人「置顶」，将噪音来源「静音」，以及对陌生人的「消息请求」进行 Accept/Reject 决策。左滑 Action 和长按 Context Menu 必须分工明确（左滑 = 快捷 2 项；长按 = 完整菜单）——Substack（flow 4494）+ XChat（flow 11674）展示了两者共存的标准实现。消息请求独立入口（flow 11664）是保护已建立联系人列表安全感的核心设计。

**行业共识**：XChat（flow 11674）、Substack（flow 4494）、Gizmo（flow 10035）均采用左滑快捷操作（Mute + Delete）+ 长按完整菜单（含 Pin / Mark Unread / Archive）；Google Gemini（flow 3223）确认长按 Pin 后聊天列表出现独立 Pinned 分组。

**Entry**: 聊天列表（Chat List）

```
Screen 1: 聊天列表（管理视角）
  主操作: 对会话进行 Pin / Mute / Delete 管理
  关键组件:
    - [已置顶] Pinned 会话分组（Section Header「置顶」+ 1-5 条会话）
    - 普通会话列表
    - 每行左滑: 快捷操作区（Screen 1a）
    - 每行长按: Context Menu（Screen 1b）
    - [右上角] Message Requests 入口（有待处理时显示，红色数字 badge）
  → 左滑某条会话: 显示快捷操作
  → 长按某条会话: 弹出 Context Menu

Screen 1a: 左滑快捷操作
  主操作: 快速静音或删除会话
  关键组件（会话行向左滑出，右侧露出操作按钮）:
    - Button「静音」（灰色，左侧）:
        点击 → Action Sheet 弹出（「静音 1 小时」/ 「静音 8 小时」/ 「永久静音」/ 「取消」）
        静音后: 会话行铃铛图标变为 🔕，不再显示消息通知
    - Button「删除」（红色，右侧）:
        点击 → Dialog（「删除会话？此操作无法撤销，且只对你生效。」→「删除」danger / 「取消」）
  → 向左滑动 → 点击「静音」: 选择时长 → 确认 → 会话行出现 🔕 图标
  → 向左滑动 → 点击「删除」: Dialog 确认 → 会话从列表消失，Toast「已删除会话」

Screen 1b: 长按 Context Menu
  主操作: 访问完整会话管理操作
  关键组件（内联弹出 Context Menu）:
    - 「标记为未读」（Mark as Unread）→ 会话行名称变粗体，未读 badge 出现
    - 「置顶对话」（Pin Chat）→ 会话移到 Pinned 分组（最多 5 个）
    - 「静音通知」（Mute Notifications）→ Action Sheet 选时长
    - 「归档」（Archive）→ 会话移入 Archive，从主列表消失，Toast「已归档 · 撤销」
    - 「删除对话」（Delete Chat）→ Dialog 确认
  → 选择「置顶对话」: 动画过渡，会话出现在 Pinned 分组顶部，Context Menu 收起

Screen 2: 消息请求（Message Requests）
  主操作: 审批来自陌生人的消息请求
  触发: 点击聊天列表顶部「N 条消息请求」入口
  关键组件:
    - NavigationBar: 返回 + 标题「消息请求」
    - 请求列表（每行）: 头像 + 名称 + handle + 消息预览（受限：仅显示首句）
    - [可选] Section Header「来自你可能认识的人」/ 「来自其他人」
  → 点击某条请求: Screen 2a（请求详情）

Screen 2a: 消息请求详情（Request Preview）
  主操作: Accept 或 Delete 消息请求
  关键组件:
    - 发送方信息（头像大图 + 名称 + handle + Mutual Contacts 信息）
    - 消息预览区（受保护，仅显示首条消息，后续消息模糊处理）
    - Text「接受后，[用户名] 可以看到你何时在线」（隐私提示）
    - 固定底部判定栏:
        Button「接受」（主色，全宽或左侧）
        Button「删除」（danger 色，次要样式）
  → 点击「接受」:
      会话升级为正式线程
      Toast 或内联提示「端到端加密已启用」（加密锁图标）
      跳转进入会话线程（Screen 3），Composer 激活
  → 点击「删除」: Dialog（「删除后，[名称] 不会收到通知。」→ 确认 / 取消）→ 请求移除
```

**Exit State**:
- ✅ 置顶成功：会话出现在 Pinned 分组，图钉 📌 图标标记
- ✅ 静音成功：🔕 图标显示在会话行，不再产生通知角标
- ✅ 接受消息请求：跳转到会话线程，显示加密提示，Composer 可用
- ✅ 删除会话：Toast「已删除」（无法撤销）
- ↩ 删除消息请求：发送方不收到通知，请求从列表消失

---

## Mobile Component Kit

按使用频率排序（基于研究样本观察）：

| 优先级 | 组件（H5 antd-mobile）| 组件（RN Gluestack/RN）| 具体用途 |
|---|---|---|---|
| ★★★ | `TextArea` + auto-resize | `TextInput` multiline + `onContentSizeChange` | Composer 消息输入框（多行自动扩展）|
| ★★★ | `List` / `VirtualList` | `FlatList` + `keyboardShouldPersistTaps` | 消息气泡列表（新消息自动 scrollToEnd）|
| ★★★ | `List` / `VirtualList` | `FlatList` + `SectionList` | 聊天列表（Pinned + 普通分组）|
| ★★★ | `SwipeAction` | `Swipeable`（react-native-gesture-handler）| 聊天列表左滑（Mute + Delete）|
| ★★ | 长按 `Popover` / `ActionSheet` | `ContextMenu` (RN) | 长按消息 Context Menu（反应 + 操作）|
| ★★ | `Popup` / `ActionSheet` | `BottomSheet` | Emoji 反应完整 picker / 静音时长选择 |
| ★★ | `Dialog` | `AlertDialog` | 删除对话 / 删除消息请求 二次确认 |
| ★★ | `Toast` | `Toast` | 归档/删除反馈（「已归档 · 撤销」）|
| ★★ | `ActionSheet` | `ActionSheet` | 附件来源选择（图库 / 拍照）/ 静音时长 |
| ★★ | 浏览器 MediaRecorder API | `expo-av` Audio.Recording | 语音消息录制 + 预览播放 |
| ★ | `ImageUploader` / `input[type=file]` | `expo-image-picker` PHPicker | 图片附件选择（多选）|
| ★ | `SearchBar` | `SearchBar` / `TextInput` | 联系人搜索 / 消息搜索 |
| ★ | `Badge` | `Badge` | 未读消息角标 / emoji 反应计数 |
| ★ | `Avatar` | `Avatar` | 联系人头像（圆形，60pt 列表 / 80pt 详情）|

---

## Anti-Patterns

- **录音后直接发送，没有预览步骤**：用户录完音立即发出，无法确认录音是否清晰或有误录内容，误发率高。→ 正确做法：录音结束后必须显示预览状态（波形 + 播放 + 时长），用户主动点击「发送」才发出，点击「删除」可以重录（Daze flow 9126 完整实现）。

- **emoji 反应只有动画，无持久 badge**：用户触发反应后看到动画，但刷新会话或重进后看不到任何反应状态。→ 正确做法：反应必须以持久 badge 形式常驻在消息气泡角落（「👍 1」），动画是即时确认，badge 是永久状态，两者缺一不可（XChat flow 11654）。

- **Compose 图标发起新会话时直接打开通讯录 App，跳出产品**：用户点击「新消息」被跳转到系统通讯录，丢失了产品内的联系人关系网络。→ 正确做法：新建会话必须在 App 内提供联系人选择页（含搜索 + Recents），不依赖系统通讯录跳转（XChat flow 11665）。

- **陌生人消息直接出现在主聊天列表**：破坏已建立联系人的安全感；用户不得不在常用联系人中辨认陌生请求，增加认知负担。→ 正确做法：陌生人消息进入独立「消息请求」列表，主聊天列表仅显示已接受联系人的会话（XChat flow 11664）。

- **左滑和长按提供相同操作，功能重叠**：用户在两个入口找同样的操作，导致认知混乱，且占用了宝贵的左滑 Action 位置。→ 正确做法：左滑仅限 2 个高频快捷操作（Mute + Delete），长按提供完整管理菜单（Pin / Archive / Mark Unread / Delete），两者分工明确（Substack flow 4494 + XChat flow 11674）。

- **聊天列表没有分组（Pinned / 普通）**：用户有 30+ 条会话时，最重要的联系人每次被新消息推到下方，需要滚动翻找。→ 正确做法：支持「置顶」功能，置顶会话在列表顶部独立分区（最多 3-5 条），长按 → Context Menu → 置顶即可完成操作（Google Gemini flow 3223 确认分组样式）。

- **语音消息气泡只有播放按钮，没有波形显示**：用户无法预判消息长短，对不熟悉发件人的消息不敢点播放（不知道会持续多久）。→ 正确做法：语音消息气泡必须包含波形图（时长可视化）+ 总时长数字，用户播放时波形从左到右填充进度（Daze flow 9126 + Abode flow 4283 均有此设计）。
