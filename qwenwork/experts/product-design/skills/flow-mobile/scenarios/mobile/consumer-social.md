# Scenario: Mobile Consumer Social（消费者社交 App）

> **研究来源**：基于对 TikTok、Instagram、Threads、Airchat、Verse、Tilt、Savee 等 7 个真实 iOS 产品 flow 和页面的横向分析抽象，不代表任何单一产品的具体实现。

---

## Identity

**Platform**: Mobile (H5 / React Native)
**Definition**: 以内容创作和社交互动为核心的移动端消费者应用，用户通过 Feed 浏览内容、发布短视频/图片/文字、与他人通过 DM 或互动（点赞/评论/分享）建立关系。

**Canonical Examples**: TikTok、Instagram、Threads（Meta）

**Not this scenario if**:
- 以职业社交为主（LinkedIn 类，改用 web/community-social）
- 以音频/播客为主要内容形式（改用 entertainment 场景）
- 以即时通讯为核心功能（WhatsApp/Telegram，改用 Communication Tools 类产品）
- 主要在 Web 端使用（改用 web/community-social）

---

## User Profile

| 维度 | 内容 |
|---|---|
| **主要角色** | Creator（内容创作者）/ Viewer（浏览消费者）/ Connector（主动社交者）|
| **核心目标** | 发现感兴趣内容 / 发布自己的作品获得反馈 / 与朋友私聊或互动 |
| **心智模型** | 习惯手势导航（上划刷新、下划加载）和手机全屏沉浸式体验；期待即时反馈（点赞动画、评论计数即时更新）|
| **使用频率** | 极高频日常使用（多次/天），碎片化时间，注意力窗口短（3-15秒） |
| **决策模式** | 探索发现型：不带具体目标，刷到有趣内容就停留；创作时目标清晰（拍摄 → 发布） |
| **容错期望** | 发布前可随时取消 / 保存草稿；互动操作（点赞/取消赞）可反向；误删内容不可恢复（需 Dialog 确认） |

---

## IA Template

**导航模式**: Tab Bar（底部 Tab Bar，5 项）
```
Tab 1: 首页（Home）     — 推荐 Feed + 关注 Feed 切换
Tab 2: 搜索/发现       — 搜索框 + 热门内容瀑布流
Tab 3: 创作（+ 中心按钮）— 全屏 Camera Composer（Full-screen Modal）
Tab 4: 通知/消息       — 互动通知 + DM 入口
Tab 5: 我的（Profile） — 个人主页：头像/统计/内容网格
```

**页面层级**: 3 级
```
L1: Tab 根页（Feed / Discover / Notifications / Profile）
L2: 详情页（Post Detail / DM Thread / Other User Profile）
L3: 操作面板（Comments Sheet / Share Sheet / More Options）
```

**权限流结构**（移动端通用）:
```
Camera：首次点 Tab 3 → 自定义说明页（Pattern G）→ 浏览器权限 API / Expo Permissions 相机权限弹窗
Photos：首次选相册 → 浏览器权限 API / Expo Permissions 相册权限（限制/全部）
Notifications：完成首个关键操作（发帖/关注）后 → 浏览器权限 API / Expo Permissions 推送权限弹窗
Microphone：录视频时同步请求（Camera 授权时通常一并请求）
```

**数据密度**: 低（单列 Feed 全屏沉浸 / 三列网格缩略图）
- 核心视图：单列 Feed（视频/图片/文字 Card，懒加载）
- 辅助视图：3 列网格（Profile 内容网格）
- 不使用：Table 多列、Dense List（用户数据列表除外）

**主要容器模式**:
| 场景 | 容器 |
|---|---|
| 相机创作界面 | Full-screen Modal |
| 评论区 | Bottom Sheet（大尺寸） |
| 分享 / 保存到合集 | Bottom Sheet（中尺寸） |
| 发帖更多设置（隐私/标签） | Bottom Sheet（大尺寸） |
| 删除帖子确认 | Dialog |
| 举报内容多操作 | Action Sheet |
| 相册媒体选择 | 内联 Recents Grid |
| DM Thread | Stack Push |

**导航骨架图（ASCII）**:
```
┌────────────────────────────────────┐
│  Status Bar（时间 / 信号 / 电量）     │
├────────────────────────────────────┤
│  [Following] [For You ▼]           │  ← Tab 1 Feed 顶部 Segmented
│                                    │
│  ┌──────────────────────────────┐  │
│  │     全屏内容（视频/图片/文字） │  │
│  │                              │  │
│  │    [Avatar]  用户名  关注     │  ← 右侧操作列
│  │    [♥]  计数                 │
│  │    [💬] 计数                 │
│  │    [➦]  分享                 │
│  │    [⋯]  更多                 │  │
│  │  ──── 文字描述/hashtags ──── │  │
│  └──────────────────────────────┘  │
│                                    │
├───┬────┬──────┬──────┬─────────────┤
│ 🏠 │ 🔍 │  ➕  │  🔔  │  👤          │  ← TabBar
└───┴────┴──────┴──────┴─────────────┘
```

---

## 该场景独有的 IA/UX 决策

1. **相机创作界面必须用 Full-screen Modal，Tab Bar 中央 `+` 按钮不可触发 Bottom Sheet** — Bottom Sheet 容器会在相机预览四周留边距和圆角，背景透明可见效果会让相机预览与底层 Feed 内容产生穿透干扰，严重破坏创作沉浸感。Full-screen Modal 才能提供真正的全屏黑色沉浸式相机体验（TikTok / Instagram 行业共识）。这是移动端消费者社交与 Web 端「弹窗表单」最根本的 UI 架构差异——Web 端的「发帖 Modal」在移动端必须升格为全屏覆盖，否则创作体验割裂，用户创作欲望受阻。

2. **Feed 互动操作（点赞/评论）必须在 Feed 内完成，评论区用大尺寸 Bottom Sheet 叠加而非跳转** — 移动端消费者社交的留存核心是「不打断浏览连续性」——点击评论按钮弹出大尺寸 Bottom Sheet 叠在 Feed 之上，关闭 Sheet 后 Feed 完全还原（无需「后退」）。Web 端通常跳转独立评论页，用户需「后退」才能继续浏览，这在移动端会造成明显的滚动位置丢失。双击点赞（double-tap on content，触发 ❤️ 放大动画 + 触觉反馈）是移动端特有手势，Web 端无对应——Instagram flow_id 2836（点赞+保存，2屏不离 Feed）是此模式的行业标准实现。

3. **DM 媒体发送必须用内联 Recents Grid，不可跳转系统相册** — DM 图片发送有两种架构：① 跳转系统相册选择后返回（用户离开 Thread，关闭相册需重新定位对话，上下文割裂）；② 内联 Recents Grid（点击相册图标在 Composer 下方就地展开 3 列缩略图网格，不跳出当前页面）。Instagram flow_id 2879 完整记录了内联选择器模式，是所有移动端社交 DM 的行业共识——跳转系统相册的摩擦成本极高，且丢失「我正在和谁聊、聊了什么」的对话背景，严重影响媒体发送意愿。

4. **创作中断时必须提供「保存草稿 / 丢弃」Dialog，不可静默关闭丢弃内容** — 用户在内容编辑阶段（已录制视频 + 添加滤镜 + 输入描述文字）点击 X 关闭时，必须弹出 Dialog 提供明确选项：「保存草稿」/ 「丢弃」，草稿保存至 Profile Drafts 区。TikTok 24 屏创作流程（flow_id 2794）是标准实现。与工具类 App 的「自动草稿」不同，社交内容创作（视频剪辑 + 贴纸 + 音乐 = 多媒体组合状态）的误删代价极高（重新拍摄录制），必须由用户主动选择是否保留，而非默默丢弃。

5. **For You Feed 必须允许游客浏览，登录门槛只设在「操作」时** — 消费者社交的激活逻辑是「先让用户看到内容价值，再激励注册」。TikTok 游客模式允许未登录用户浏览 For You Feed，直到用户尝试点赞/评论/关注时才触发登录 Bottom Sheet（保留当前内容上下文，登录完成后自动继续操作）。强制先注册再看内容会在「用户最脆弱的好奇阶段」制造最大摩擦，导致激活率大幅下降——这是消费者社交与 SaaS（必须登录才能使用）最根本的架构差异，也是移动端消费者社交 App 与 Web 社区平台（通常有更低的匿名浏览门槛）需要对齐的关键决策。

---

## Canonical Flows

> 以下 flow 基于 7 个真实产品样本横向分析抽象。括号内标注「行业共识」表示 3 个以上产品采用相同模式。

---

### Flow 1: Create & Publish Post（创建并发布内容）

**在此场景的特殊性**: 消费者社交 App 的内容创作入口是独立的相机页面（Full-screen Modal），而非 Web 端的表单弹窗。「内容类型」通过相机界面内的 Segmented Mode 选择（TikTok: 10m/60s/15s/Photo/Text），而非先选类型再进入不同页面。**效果/滤镜选择**是移动端特有功能，在相机预览状态下实时预览，Web 端无对应。发帖前的「More Options」页面集中处理隐私设置（谁可以看 / 评论 / 下载），是 B2C 社交产品保护用户的核心设计，B2B 工具类产品无此模式。TikTok 24 屏的完整创作流程是当前行业最复杂的移动创作体验。

**行业共识**：全部研究样本均将「创建内容」放在 Tab Bar 中央（`+` 按钮）；TikTok、Instagram 均先请求 Camera 权限说明页，再进入相机界面。

**Entry**: 点击 Tab Bar 中央 `+` 按钮 → Full-screen Modal 弹出相机页面

```
Screen 1: 权限说明页（首次进入）
  触发条件: Camera 权限未授权时插入此页
  主操作: 点击「允许访问相机」→ 触发浏览器权限 API / Expo Permissions 相机权限弹窗
  关键组件: 相机图标（大图标）, Text（说明文字）,
            Button("允许访问相机"，主要按钮样式),
            Button("稍后再说"，次要按钮样式)
  → 授权成功: 进入 Screen 2（Camera Composer）
  → 拒绝权限: Toast 提示 + 导引去系统设置开启
  → 已授权: 直接进入 Screen 2（跳过此页）

Screen 2: Camera Composer（相机创作界面）
  主操作: 选择模式 → 录制/拍摄
  关键组件:
    - 顶部: 关闭按钮（X）/ 翻转摄像头 / 闪光灯 / 定时器
    - 中央: 相机预览（全屏）
    - 底部 Segmented Mode: [10min] [60s] [15s] [Photo] [Text]
    - 录制按钮: 大圆形快门（长按录制 / 单击拍照）
    - 录制进度: 圆形进度环（red）环绕快门按钮
    - 右侧: Effects 按钮（打开效果抽屉）
  → 点击 Effects: Bottom Sheet 弹出效果列表（搜索 + 分类网格 + 实时预览）
  → 录制完成 / 拍照: 进入 Screen 3

Screen 3: 内容编辑器（录制后）
  主操作: 添加 Sticker / 文字 / 选择封面 → 点击「下一步」
  关键组件:
    - 预览视频/图片（全屏）
    - 工具栏（右侧竖排）: 文字/贴纸/滤镜/封面/剪辑
    - Button("下一步"，主要按钮样式)（右上角或底部固定）
    - Button("重新录制"，次要按钮样式)（左上角）
  → 点击「下一步」: 进入 Screen 4

Screen 4: 发帖 Metadata Composer
  主操作: 填写描述 + 设置发布选项 → 点击「发布」
  关键组件:
    - 内容预览缩略图（左上角小图）
    - TextArea（描述文字，支持 @提及 / #话题 / 表情）
    - 设置列表（右箭头）:
        "位置"（浏览器 Geolocation / Expo Location 选择）
        "谁可以看"（默认「所有人」→ 点击进子页选择）
        "更多选项"（评论权限/下载/合拍等 Toggle 面板）
    - Button("发布"，主要按钮样式)（底部全宽）
    - Button("保存草稿"，次要按钮样式)（次要）
  → 点击「发布」: 上传进度显示（Screen 5）
  → 点击「保存草稿」: 保存后返回 Feed，Toast 确认

Screen 5: 发布确认（上传中 → 成功）
  主操作: 等待上传完成
  关键组件:
    - ProgressIndicator（circular）（上传中）
    - 上传成功: 自动关闭 Full-screen Modal，返回 Feed
    - Toast「内容已发布」
  Exit: 返回 Home Feed，新帖出现在个人主页
```

**Exit State**:
- ✅ Success：Full-screen Modal 关闭，Toast「已发布」，Profile 网格出现新帖
- ❌ 上传失败：内联错误 + Button("重试") + 本地保存草稿
- ↩ Abandon：任意步骤可点 X 关闭，弹 Dialog 确认是否「保存草稿」或「丢弃」

---

### Flow 2: Feed Interaction（互动：点赞、评论、分享）

**在此场景的特殊性**: 移动端消费者社交的互动操作绑定在 Feed 内容的右侧操作列（竖排图标）上，Web 端通常是横排 toolbar。**双击点赞**（double-tap on content）是行业共识（TikTok、Instagram 均如此），触发 ❤️ 动画 + 触觉反馈，是移动端特有的手势交互。评论区通过大尺寸 Bottom Sheet 从底部弹出（不离开 Feed 页面），Web 端通常是独立评论页面。Instagram feed_id 2836 记录了「点赞 + 保存」二步操作（2屏），印证了不离开 Feed 的设计共识。

**行业共识**：所有研究样本中，Feed 互动操作均不触发页面跳转；评论区用大尺寸 Bottom Sheet 呈现（TikTok、Instagram、Verse 均如此）。

**Entry**: 在 Home Feed 中浏览内容

```
Screen 1: Home Feed（浏览状态）
  主操作: 浏览、滑动切换内容
  关键组件:
    - FlatList / VirtualList（Feed 容器，支持下拉刷新）
    - 媒体内容（Image / Video Player）
    - 右侧操作列（绝对定位覆盖在内容上）:
        [Avatar + 关注按钮]（主要按钮样式）
        [♥ 点赞] + 计数 Text
        [💬 评论] + 计数 Text
        [➦ 分享] + 计数 Text
        [⋯ 更多] 
    - 底部: 作者信息 + 文字描述 + Hashtag + 音乐条
  → 双击内容区域: ❤️ 动画（放大缩小）+ 触觉反馈 + 点赞 Toggle
  → 点击 [♥]: 点赞 Toggle + 计数 +1/-1（即时）
  → 点击 [💬]: 弹出评论 Bottom Sheet（Screen 2）
  → 点击 [➦]: 弹出分享 Bottom Sheet（Screen 3）
  → 长按内容: Context Menu 弹出（不感兴趣 / 举报 / 保存）

Screen 2: 评论 Bottom Sheet
  主操作: 浏览评论 / 发表评论
  关键组件:
    - Bottom Sheet（大尺寸）+ 可见拖拽指示条
    - 评论列表头（「评论 X 条」+ 关闭按钮）
    - List（评论列表，每行：Avatar + 用户名 + 评论文字 + 时间 + ♥ 微点赞）
    - 滑动操作（长按评论: 回复/举报/删除）
    - 底部固定 Composer:
        TextInput（"添加评论..."，多行）+ 发送 Button
        emoji 快捷栏（常用 Emoji 横排滚动）
  → 输入文字 + 点击发送: 评论即时插入列表顶部，计数更新
  → 点击他人评论「回复」: TextInput 自动填入 @用户名

Screen 3: 分享 Bottom Sheet
  主操作: 选择分享方式
  关键组件:
    - Bottom Sheet（中尺寸）
    - 内容预览（Card：缩略图 + 标题）
    - 快捷分享（头像列表: 最近联系人 DM 快捷发送）
    - List（分享到 DM / 复制链接 / 保存到本地 / 发现更多...）
    - 系统分享面板（打开其他 App）
  → 点击某联系人: 直接发送到 DM，Toast「已发送至 XX」，Sheet 关闭
  → 点击「复制链接」: Toast「链接已复制」，Sheet 关闭
```

**Exit State**:
- ✅ 点赞：即时 UI 更新（填充心形 + 计数）+ 触觉反馈
- ✅ 评论发送：新评论插入列表 + 计数更新
- ✅ 分享：Toast 确认，返回 Feed
- ↩ 关闭 Sheet：拖拽下滑或点 X，返回 Feed

---

### Flow 3: Direct Message with Media（DM 私信 + 媒体发送）

**在此场景的特殊性**: 移动端社交 App 的 DM 入口通常在 Notifications/Activity Tab（Tab 4）的右上角或单独的 DM Tab，而非 Web 端的顶部 Inbox icon。消费者社交 DM 的媒体发送通过**内联相册 Picker**（底部内嵌 Recents Grid）进行，而非先跳转到相册再返回——这是 Instagram、TikTok 等产品的共识（flow_id 2879 确认）。**消息气泡样式**高度可定制（Instagram flow_id 2881：Conversation Theme 8 屏），是区别于 Web 端的移动端特有功能。照片/视频支持全屏查看（tap → Full-screen Modal viewer + swipe-to-dismiss）。

**行业共识**：Instagram（flow 2879、2881）均确认了「内联 Recents Grid」+ 全屏查看的标准 DM 媒体流。

**Entry**: Tab 4 通知页 → 点击 DM 图标 / 某人发来的 DM 通知

```
Screen 1: DM 列表
  主操作: 选择一个对话
  关键组件:
    - NavigationBar（标题「消息」+ 右上角「新建」图标）
    - List（对话列表，支持搜索）:
        每行: Avatar（已读/未读圆点）+ 用户名 + 最近消息预览 + 时间
        未读角标计数
        左滑操作: 静音 / 删除
    - Empty State（空状态：「暂无对话，去发现新朋友」+ CTA）
  → 点击某对话: Stack Push → Screen 2

Screen 2: DM Thread（对话界面）
  主操作: 阅读消息 / 发送文字或媒体
  关键组件:
    - 自动滚到最新消息（消息数量变化时触发）
    - FlatList（消息气泡列表）:
        自己发送: 右侧蓝色气泡
        对方发送: 左侧灰色气泡 + Avatar
        时间戳: 居中显示（每隔若干条显示）
    - 顶部导航栏（对方 Avatar + 用户名 点击进主页；右：视频通话图标）
    - 底部 Composer（Safe Area 内）:
        Button（相机图标）/ Button（相册图标）/ Button（GIF）
        TextInput("消息..."，多行，最多 5 行)
        Button（发送箭头，输入为空时禁用）
    - 内联 Recents Grid（点击相册按钮展开）
  → 输入文字 + 点击发送: 气泡即时插入底部
  → 点击「相册图标」: Screen 3（内联媒体选择器展开）
  → 双击气泡: Emoji 快捷反应浮层（Like / Love / Haha 等）
  → 长按气泡: Context Menu（复制 / 回复 / 撤回 / 转发）

Screen 3: 内联媒体选择器（展开状态）
  主操作: 选择图片/视频 → 发送
  关键组件:
    - Recents Grid（3列，图片缩略图，懒加载）
    - 已选中: CheckMark 覆盖 + 蓝色边框
    - 选中后底部出现: Button("发送"，主要按钮样式)（激活）
    - Button（拍照/录像，实时相机缩略图）
  → 点击图片: 选中状态（CheckMark），Button("发送") 激活
  → 点击「发送」: 图片气泡插入 Thread，选择器收起

Screen 4: 全屏媒体查看器（点击图片气泡后）
  主操作: 查看 + 下滑关闭
  关键组件:
    - Full-screen Modal（黑色背景）
    - Image（原图，contain 模式）
    - 顶部: X 关闭 Button + 下载/转发按钮
    - 手势: swipe down → dismiss
  Exit: 下滑或点 X 返回 Thread
```

**Exit State**:
- ✅ 发送成功：气泡即时显示 + Sent 状态（单勾→双勾→蓝色已读）
- ❌ 发送失败（无网络）：气泡显示感叹号 + 点击重试
- ↩ 关闭媒体选择器：收起，回到 Thread

---

### Flow 4: Explore & Discover Users（探索 Tab + 搜索用户 + 关注）

**在此场景的特殊性**: 消费者社交 App 的「探索/发现」Tab 是 Feed 之外留存用户的第二核心入口——区别于 Feed 的「被动接收算法推荐」，Explore Tab 是「主动搜索发现」，服务于用户想找到新关注对象、特定话题内容的意图。**Savee（flow 5273，3 屏）** 是最精简完整的社交 Discover 实现：Discover 落地页（Popular Users 头像卡横排 + Popular Images 瀑布流）→ 搜索激活（键盘弹出，底部内容上移）→ 搜索结果（Users Tab，每行头像 + 用户名 + Follow CTA）。**TikTok（flow 2761，3 屏）** 展示了用户主页内容排序（Latest/Popular）——进入他人 Profile 后内容网格可按偏好排序，是 Explore 路径中「找到用户 → 看内容 → 决定关注」决策链的关键中间步骤。**komoot（flow 8363，2 屏）** 是关注状态 Toggle 的最清晰示范：Follow 按钮点击后即时变为「Following ✓」+ Followers 计数 +1，无需跳转或加载。三者结合构成：Explore 落地 → 搜索 → 结果列表 → 进入 Profile → 关注 的完整 4 步发现链路。

**行业共识**：TikTok / Instagram / Savee 均将 Discover/Search 置于 Tab Bar 第 2 位（放大镜图标）；搜索激活时底部 Tab Bar 保持可见（不隐藏）；Follow 状态切换即时反映在按钮上（无中间 loading 状态），Followers 计数同步 +1/-1（komoot flow 8363 / Instagram 均如此）。

**Entry**: Tab Bar → 点击「搜索/发现」Tab（放大镜图标）

```
Screen 1: Explore 落地页（未搜索状态）
  主操作: 浏览推荐用户 / 热门内容 / 激活搜索
  关键组件:
    - SearchBar（顶部，placeholder「搜索用户、话题、内容」，点击激活 Screen 2）
    - Section「推荐用户」（横向可滑动）:
        头像卡 Carousel（每张: Avatar + 用户名 + 「关注」按钮，小尺寸）
    - Section「热门话题」（Chip 横排，可滑动）:
        Chip("#旅行" / "#美食" / "#健身"...)
    - 主内容区（瀑布流 / 网格）:
        按主题分组的内容卡片（图片/视频缩略图 + 作者小头像）
    - InfiniteScroll（下滑加载更多推荐）
  → 点击 SearchBar: 键盘弹起，进入 Screen 2（搜索激活状态）
  → 点击「关注」（推荐用户卡）: 即时状态切换（「关注」→「已关注 ✓」）
  → 点击内容缩略图: Stack Push → 帖子详情

Screen 2: 搜索激活（输入状态）
  主操作: 输入关键词
  关键组件:
    - SearchBar（激活，键盘弹出，右侧出现「取消」按钮）
    - 内容 Tab 横排（水平可滑动，切换搜索类型）:
        Tab("用户") / Tab("话题") / Tab("帖子") / Tab("音乐")
    - 热搜推荐区（SearchBar 为空时显示）:
        Section「热门搜索」:
            List（每行: 🔥 话题词 + 搜索量，点击自动填入）
        Section「最近搜索」:
            Chip 横排（最近搜索词 + × 删除按钮）
    - 实时联想结果（输入 ≥1 字时替换热搜区）:
        List（联想词 + 对应用户头像预览）
  → 输入关键词 + 提交（回车 / 点搜索）: 进入 Screen 3
  → 点击「取消」: 收起键盘，返回 Screen 1
  → 切换 Tab（如「话题」）: 搜索结果切换为话题列表

Screen 3: 搜索结果（用户列表）
  主操作: 浏览匹配用户 → 点击进入 Profile 或直接关注
  关键组件:
    - SearchBar（保留输入词 + 可修改）
    - 结果 Tab 横排（与 Screen 2 同步，当前选中「用户」）
    - List（搜索结果用户列表）:
        每行:
          Avatar（48pt，圆形）
          VStack:
            Text(用户名 @handle，body，粗体)
            Text(粉丝数 + 简介截断，caption，灰色)
          Button("关注", 主色，bordered，右侧)（已关注时显示「已关注」+ 灰色边框）
    - Empty State（无结果: 「没有找到"[关键词]"相关用户」+ 「查看热门用户」CTA）
  → 点击「关注」Button: 即时状态切换（主色填充 → 灰色「已关注」）+ Haptic 触觉反馈
  → 点击用户行（非按钮区域）: Stack Push → Screen 4

Screen 4: 用户主页（从搜索结果进入）
  主操作: 查看内容 → 决定关注 / 取关
  关键组件:
    - 顶部 Profile Header（固定，滑动内容区时保持在顶部）:
        Avatar（大，80pt）+ 用户名 + 简介
        Stat Row（帖子数 / 粉丝数 / 关注数，横排 3 列，可点击进入列表）
        Button("关注", 主色，全宽)（已关注: 「已关注」+ 「发消息」并排）
    - 内容排序 Dropdown（右上角，点击弹出选项）:
        「最新」/ 「最热门」（选中项有 ✓，切换后网格重新排序）
    - 内容网格（3 列，正方形缩略图，懒加载）:
        每格: 视频缩略图 + 播放量 Text（左下角覆盖）
    - 标签 Tab（可选）: Tab("帖子") / Tab("回复") / Tab("喜欢")
  → 点击「关注」: 即时状态切换 + Followers 计数 +1 + Haptic 触觉反馈
  → 再次点击（「已关注」→「取关」）: Action Sheet 弹出确认（「取消关注 @handle？」→「取消关注」danger / 「保留」）
  → 点击内容缩略图: Full-screen Modal 播放视频 / 查看图文帖子
  Exit: 点击返回 → 回到 Screen 3 搜索结果列表
```

**Exit State**:

- ✅ 关注成功：Button 即时变「已关注」+ Followers 计数 +1 + Haptic；Home Feed 开始出现该用户内容
- ↩ 取关：Action Sheet 确认 → 取关成功 Toast「已取消关注 @handle」+ Followers 计数 -1
- 空状态（搜索无结果）：Empty 组件 + 「探索热门用户」CTA 返回 Screen 1

---

## Mobile Component Kit

按使用频率排序（基于研究样本观察）：

| 优先级 | 组件（H5 antd-mobile）| 组件（RN Gluestack/RN）| 具体用途 |
|---|---|---|---|
| ★★★ | `TabBar` | `TabBar` / `BottomTabNavigator` | App 主导航结构（5 Tab） |
| ★★★ | `List` + `InfiniteScroll` | `FlatList` + `onEndReached` | Feed 内容流（懒加载，性能关键）|
| ★★★ | `Mask` / 全屏 Modal | `Modal`（全屏）| 相机创作界面、全屏媒体查看器 |
| ★★★ | `Image` + `lazyload` | `Image` + `FastImage` | Feed 内容缩略图、头像、媒体气泡 |
| ★★★ | `Popup` / `ActionSheet` | `BottomSheet`（large） | 评论区、分享面板、更多选项 |
| ★★★ | `TextArea` | `TextInput`（multiline） | 评论 Composer、DM 输入框、发帖描述 |
| ★★ | `PullToRefresh` | `RefreshControl` | Feed 下拉刷新 |
| ★★ | 自定义 ScrollView | `ScrollView` + `scrollToEnd` | DM Thread 自动滚动到最新消息 |
| ★★ | `NavBar` + Stack | `StackNavigator` | DM 列表 → Thread push 导航 |
| ★★ | `SwipeAction` | `Swipeable` | DM 列表（静音/删除）、评论行操作 |
| ★★ | `Popover` | `ContextMenu` | 长按帖子、长按气泡的上下文菜单 |
| ★★ | `ImagePicker` | `expo-image-picker` / `react-native-image-picker` | 媒体选择器（相册权限后调用）|
| ★ | `Badge` | `Badge` | Tab Bar 未读消息计数 |
| ★ | 浏览器 Notifications API | `expo-notifications` | Push 权限请求 |
| ★ | 浏览器 MediaDevices API | `expo-camera` | 相机录制界面 |
| ★ | `ShareSheet` / Web Share API | `react-native-share` | 系统分享面板 |
| ★ | `ErrorBlock` / Empty State | `EmptyState` 自定义 | DM 空状态、通知空状态 |
| ★ | `Grid`（3列） | `FlatList`（numColumns=3）| Profile 内容网格（3列缩略图）|

---

## Anti-Patterns

基于研究样本中观察到的设计错误：

- **强制登录后才显示任何内容（Gate All Content）**：用户进入 App 时立即跳转到注册页，不展示任何 Feed 内容。→ 正确做法：先展示 For You Feed（游客模式），互动操作（点赞/评论/发帖）时再触发登录引导（TikTok 模式），大幅提升激活率。

- **相机界面不经权限说明页直接调用系统弹窗**：用户看到系统弹窗时无上下文，拒绝率高。→ 正确做法：先展示 Pattern G 自定义说明页（「为什么需要相机权限」），用户理解后再触发系统弹窗，授权率显著提升。

- **Tab Bar 中央 `+` 按钮用 Bottom Sheet 而非 Full-screen Modal**：相机预览在 Sheet 中显示，被遮挡且不沉浸。→ 正确做法：创作界面必须用 Full-screen Modal，提供完整全屏相机体验（行业共识）。

- **评论区触发页面跳转（Stack Push Navigation）**：点击评论按钮跳转到独立评论页面，用户离开 Feed 上下文，返回后需重新定位。→ 正确做法：评论区用大尺寸 Bottom Sheet 从底部弹出，叠在 Feed 之上，关闭 Sheet 立即回到 Feed 原位置。

- **DM 媒体发送先跳转相册页再返回**：用户离开 DM Thread，跳到系统相册选完图再返回，体验割裂且背景上下文丢失。→ 正确做法：内联 Recents Grid 直接嵌在 DM Composer 下方展开（Instagram 模式，flow_id 2879），或用 ImagePicker 内联选择器，不跳出当前页面。

- **发帖没有「保存草稿」选项**：点击 X 关闭时立即丢弃所有已创作内容，用户无法中途保存。→ 正确做法：关闭创作界面时弹 Dialog（2 选项）：「保存草稿」/ 「丢弃」，草稿可在个人主页 Drafts 区找回（TikTok 模式）。

- **Feed 没有处理空状态**：新用户首次进入「关注」Feed 时显示空白，无 CTA 引导关注他人。→ 正确做法：Empty State 组件 + 明确 CTA（「去发现感兴趣的人」→ 跳转 Discover），搭配推荐关注列表（For You 逻辑）。

- **DM 列表不显示最后一条消息预览**：用户无法扫描哪个对话有新内容。→ 正确做法：每行显示「你: 最近消息截断...」（约 30 字）+ 时间戳，未读行用蓝色圆点标记 + 角标计数。
