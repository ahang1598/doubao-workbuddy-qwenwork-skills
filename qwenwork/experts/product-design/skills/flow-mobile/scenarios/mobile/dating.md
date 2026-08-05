# Scenario: Mobile Dating App（移动端约会/交友）

> **研究来源**：基于对 Tinder iOS 产品 flow 和页面的横向分析抽象，不代表任何单一产品的具体实现。

---

## Identity

**Platform**: Mobile (H5 / React Native)
**Definition**: 以「滑卡发现 → 双向匹配 → 对话」为核心交互链路的移动端约会交友 App，用户通过全屏照片卡片做快速二元决策（Like / Dislike），双方互 Like 后解锁私信对话。

**Canonical Examples**: Tinder、Bumble、Hinge、Badoo

**Not this scenario if**:
- 产品是婚恋平台（以资料审核、红娘撮合为主，无滑卡交互）
- 产品是社交兴趣社区（以内容 Feed 为主，交友是副功能）
- 产品是私信 DM App（改用 mobile/messaging）
- 产品是线上交友直播（以直播互动为主）

---

## User Profile

| 维度 | 内容 |
|---|---|
| **主要角色** | 单身用户（寻找约会对象 / 寻找长期伴侣）|
| **核心目标** | 快速浏览潜在对象 → 与感兴趣的人匹配 → 建立真实连接（对话或见面）|
| **心智模型** | 数字化「相亲角」：照片是第一印象，快速筛选，靠 Prompts/Bio 了解性格 |
| **使用频率** | 中频（每天 1-2 次，每次 5-15 分钟）；碎片时间使用（通勤/睡前）|
| **决策模式** | 直觉驱动：0.5 秒看照片决定 Like/Dislike，成本极低 → 高频操作 |
| **容错期望** | 中：Rewind 可撤销上一次滑卡；配对后的消息不可撤回；封锁操作需二次确认 |

---

## IA Template

**导航模式**: Bottom Tab Bar（5 Tab）

```
Tab 1: 发现 / Discover  — 全屏滑卡（核心视图）
Tab 2: 喜欢 / Likes     — 收到的 Like 列表（付费可查看清晰头像）
Tab 3: 消息 / Messages  — Matches 头像行 + 对话列表
Tab 4: 探索 / Explore   — 分类兴趣组 / 关系意向筛选
Tab 5: 我的 / Profile   — 自己的资料 + 设置 + 订阅
```

**页面层级**: 2-3 级
```
L1: 发现（全屏滑卡）/ 消息列表 / Profile 主页
L2: 他人资料详情（Profile Detail）/ 单条对话（Conversation）/ 资料编辑（Profile Edit）
L3: 照片编辑 / Prompt 编辑 / 举报/封锁流程
```

**权限流结构**:
```
Location（发现附近用户，核心功能）:
  → Onboarding 时请求，先展示自定义说明页（「位置用于推荐附近的人，不会公开你的精确位置」）
  → 系统位置权限弹窗

Photos / Camera（上传个人照片）:
  → 首次进入照片上传环节时触发（Action Sheet 选相册 / 拍照两路径）

Notifications（配对通知 / 消息通知）:
  → Onboarding 完成后单独询问（非强制，但关键：用户不开通知会错过配对）
```

**数据密度**: 低（滑卡单屏一人，Photo 为主，文字为辅）
- 滑卡视图：全屏照片 + 底部信息叠层（Name / Age / Distance / Badges）
- 消息列表：Matches 横向头像行 + 对话列表（头像 + 名字 + 最新消息预览 + 时间）
- Profile 编辑：媒体 3x3 Grid + 文字 Sections（Bio / Prompts / 基本信息）

**主要容器模式**:
| 场景 | 容器 |
|---|---|
| 配对庆祝弹窗（Match!）| 全屏 Modal（动画覆盖层，强打断）|
| 安全提示 / 功能说明 | 半模态 Carousel（底部向上，可下滑关闭）|
| 举报 / 封锁操作 | Bottom Action Sheet → Dialog 确认 |
| Boost / Super Like 购买 | Bottom Sheet（付费 upsell，保留滑卡背景）|
| Prompt 编辑 | Full-screen Push 页 |
| 照片管理（3x3 Grid）| Inline 编辑（在 Profile 编辑页内）|
| 对话中 GIF / 音乐选择 | Bottom Sheet（Medium，内嵌搜索）|

**导航骨架图（ASCII，发现/滑卡视图）**:
```
┌────────────────────────────────────┐
│  Status Bar                         │
├────────────────────────────────────┤
│  ● ○ ○   Tinder    [🔥]  [⚙]     │  ← 顶部导航（Tab Bar 在此页透明叠加）
├────────────────────────────────────┤
│                                    │
│  ┌──────────────────────────────┐  │
│  │  ● ● ○ ○ ○（照片进度点）    │  │  ← 多张照片导航
│  │                              │  │
│  │      [全屏照片]              │  │
│  │                              │  │
│  │  姓名 24  📍 3km away        │  │  ← 信息叠层（渐变遮罩）
│  │  ────────────────────       │  │
│  │  "热爱咖啡和周末远足"        │  │
│  └──────────────────────────────┘  │
│                                    │
│  ↩  ✕   ⭐   ❤   ⚡              │  ← 底部操作栏（5个按钮）
├────────────────────────────────────┤
│  🔥    ❤️    💬    🧭    👤       │  ← Tab Bar
└────────────────────────────────────┘
```

---

## 该场景独有的 IA/UX 决策

1. **发现/滑卡视图的 Tab Bar 必须透明叠加或隐藏，不能占用卡片空间** — 约会 App 的核心价值来自「照片」的视觉冲击力，全屏照片是第一印象载体。如果底部 Tab Bar 用实色背景占据屏幕底部 50pt，不仅遮挡关键的照片内容，也破坏了「你正在看一个真实的人」的沉浸感。正确做法：Tab Bar 在滑卡 Tab 上透明叠加（透明底色，图标白色），或将操作按钮区域与 Tab Bar 层叠在同一区域——Tinder（flow 3427）确认滑卡时底部操作栏和 Tab Bar 在同一屏共存，卡片照片延伸至底部安全区域。

2. **收到的 Like 列表必须对免费用户模糊处理，作为付费升级的最强转化入口** — 「有人喜欢你」是约会 App 用户最强烈的情感钩子，模糊头像（可以隐约看出有人，但看不清是谁）制造了「好奇 + 失落」的双重情绪，是将免费用户转化为付费用户的最高效 Freemium Gate。比起在空功能界面放付费 CTA，这种「剧透式遮罩」的转化率显著更高——Tinder Gold 的核心卖点之一就是「看谁喜欢了你」（See Who Likes You），直接对应 Likes Tab 的解锁。

3. **Profile 编辑必须有「Preview Tab」让用户从他人视角预览自己的卡片** — 用户在编辑自己的资料时，通常处于「主观视角」（「我填了什么」），很难预判别人滑到自己的卡片时看到的实际效果（照片顺序、Bio 截断、Prompt 组合）。如果缺少 Preview 功能，用户会在资料发布后才发现问题（如第一张照片不够吸引人），此时已错过了很多潜在配对。正确做法：Profile 编辑页顶部提供「Preview（预览）」Tab，切换后模拟滑卡视角全屏展示自己的卡片，可左右滑动查看所有照片——Tinder（flow 3440，54 屏）完整实现了 Edit / Preview 双 Tab 切换。

4. **配对弹窗（Match!）必须是全屏强打断，不能是 Toast 或小通知角标** — 「双向 Like」是约会 App 最重要的里程碑时刻，是整个产品给用户带来正向情绪峰值的核心节点。弱化这个时刻（Toast 提示）会让用户错失情绪高峰，失去「啊，匹配成功了！」的兴奋感——这种情绪峰值是用户持续使用 App 的关键动力。正确做法：Match 时全屏 Modal 覆盖（带双方头像爆炸出现的动画、五彩纸屑/光晕效果），提供「发消息」主 CTA 和「继续浏览」次要 CTA，强制让用户意识到「刚刚发生了一件大事」。

5. **举报/封锁必须是三步确认（Overflow → Action Sheet → Dialog），且不可逆操作须明确说明** — 封锁是约会 App 中少数具有强不可逆性的操作（封锁后对方永久消失，无法撤销），而举报涉及到对真实人的投诉，错误操作影响大。单步直接执行会造成误操作风险，特别是「Overflow 菜单中 Block 和 Share 相邻」的布局下误触概率高。正确做法：Overflow（···）→ Action Sheet（Share / Block / Report / Cancel）→ Dialog（「封锁 [名字]？此操作无法撤销，对方不会收到通知」→ 「封锁」danger / 「取消」），Dialog 说明封锁的具体影响——Tinder（flow 3424，5 屏）完整实现了此三步流程。

---

## Canonical Flows

> 以下 flow 基于 Tinder iOS 真实产品样本横向分析抽象。括号内标注「行业共识」表示多个产品采用相同模式。

---

### Flow 1: 滑卡发现（Swipe & Discovery）

**在此场景的特殊性**: 约会 App 的滑卡交互是移动端为数不多的「手势即决策」设计——右滑/点❤ = Like，左滑/点✕ = Dislike，整个判断在 0.5 秒内完成。这与其他 App「先浏览再决策」的模式根本不同。照片必须占满全屏（无边距），底部信息叠层（姓名/年龄/距离）用渐变遮罩保持可读性；操作按钮区域固定在底部，不可随内容滚动。「First Impression Message」（Tinder flow 3428）展示了一种进阶模式——在滑卡时就可以直接发消息给对方，减少「配对后不知道说什么」的沉默问题。

**行业共识**：Tinder（flow 3427/3428）确认：全屏卡片叠层（Swipe Deck）、底部5按钮操作栏（Rewind/Dislike/SuperLike/Like/Boost）、照片顶部进度点、左右滑动 + LIKE/NOPE overlay 文字。

**Entry**: 启动 App / 点击 Tab Bar 第一个 Tab（🔥 发现）

```
Screen 1: 发现（Swipe Deck）
  主操作: 浏览用户卡片，做 Like / Dislike 决策
  关键组件:
    - 全屏照片卡片（Swipe Deck，叠层）:
        当前卡片: 全屏照片（无边距，延伸至安全区域）
        下一张卡片: 微露出（右下角，约 4pt，暗示还有更多）
        照片顶部进度点（· · · ○ ○，指示多张照片数量）
        信息叠层（底部渐变遮罩）:
          姓名 + 年龄（大号，白色加粗）
          距离（📍 3km away）
          职业 / 学校（如有填写，次行）
          Verified Badge（蓝色认证图标，如已认证）
    - 手势交互:
        右滑: Like（卡片向右飞出 + 绿色「LIKE」overlay）
        左滑: Dislike（卡片向左飞出 + 红色「NOPE」overlay）
        上滑: Super Like（卡片向上飞出 + 蓝色「SUPER LIKE」overlay）
        下拉（或点击卡片）: 展开资料详情（Screen 1a）
    - 底部操作栏（5个按钮，圆形，固定在底部）:
        ↩ Rewind（灰色，撤销上一次操作，付费功能）
        ✕ Dislike（红色，大圆）
        ⭐ Super Like（蓝色，小圆，每天限额）
        ❤ Like（绿色，大圆）
        ⚡ Boost（紫色，提升曝光，付费功能）
    - [右上角] 过滤设置入口（⚙，年龄/距离偏好）
  → 右滑 / 点 ❤: 发出 Like，动画后显示下一张卡片；若对方也 Like → 触发 Screen 2（Match）
  → 左滑 / 点 ✕: Dislike，下一张卡片
  → 点击卡片主体区域（非操作栏）: Screen 1a（资料详情展开）
  → 点击 ⭐ Super Like: 用一次 Super Like 配额，对方看到时有特殊标记
  → 点击 ⚡ Boost: 付费 upsell Bottom Sheet（Screen 3，Flow 4）
  → 点击 ↩ Rewind（付费用户）: 撤销上一次 Dislike，恢复上一张卡片

Screen 1a: 资料详情展开（Profile Detail）
  主操作: 深入了解对方，做更充分的决策
  触发: 点击卡片主体区域 / 向上拖拽卡片 / 点击卡片底部 ▼ 展开箭头
  容器: 当前卡片向上展开（或 Push 新页面），底部操作栏不消失
  关键组件:
    - 照片横向 ScrollView（大图，指示点）
    - 基础信息: 姓名 / 年龄 / 距离 / 职业 / 学校
    - Bio Section（文字自我介绍，最多 500 字）
    - Prompts Section（2-3 个问答，如「My ideal weekend...」/ 「I'll know it's a match if...」）
    - 兴趣 Tags（Chips，横向流式布局，如「☕ 咖啡」「🎵 爵士乐」）
    - 基本信息行（身高 / 语言 / 关系意向 / 政治观）
    - Button「举报/封锁」（右上角 ···，或页面底部）
  → 向下拖拽 / 点击 ✕ 关闭: 收起详情，回到滑卡视图，卡片不变
  → 点击底部操作栏按钮（Like / Dislike）: 与 Screen 1 相同效果

Screen 2: 配对弹窗（Match!）
  触发: 双方互相 Like
  容器: 全屏 Modal（强打断，覆盖当前视图，需主动关闭）
  关键组件:
    - 全屏渐变背景（品牌色渐变，紫色/粉色）
    - 动画元素: 两人头像从两侧飞入相遇（弹跳动效）+ 五彩纸屑/光晕粒子动画
    - 标题文字「It's a Match!」（大号，白色，居中）
    - 副标题「你和 [名字] 互相喜欢对方」
    - Button「发消息」（主 CTA，白色按钮，进入对话界面）
    - Button「继续发现」（次要，白色文字链接，关闭 Modal 回到滑卡）
  → 点击「发消息」: Modal 关闭，进入对话页（Flow 3 Screen 2）
  → 点击「继续发现」/ 向下滑动: Modal 关闭，回到滑卡视图

Screen 3: First Impression Message（可选，滑卡前预发消息）
  触发: 点击卡片底部「发消息给 [名字]」入口（部分 Profile 有此功能）
  容器: Bottom Sheet（Medium）覆盖在卡片上方
  关键组件:
    - TextInput（「发一条消息...」，140字上限，右侧字数倒计）
    - Button「发送」（主色，右侧，有内容后激活）
    - Button「取消」（左侧，关闭 Sheet）
  → 点击「发送」: 消息发送（对方配对后可见），自动触发 Like，卡片飞出
  → 点击「取消」: Sheet 收起，回到卡片（未 Like）
```

**Exit State**:
- ✅ 互相 Like：Match 弹窗动画 → 主动发消息或继续浏览
- ✅ 单方 Like：卡片飞出，进入下一张（不提示，避免尴尬）
- ✅ Dislike：卡片飞出，进入下一张
- 📭 卡片已浏览完：显示「今日已浏览完所有附近用户」+ Boost upsell 或「明天再来」

---

### Flow 2: 个人资料设置（Profile Setup & Edit）

**在此场景的特殊性**: 约会 App 的资料完整度直接决定用户的曝光质量和配对率——没有头像的用户几乎不会被 Like，没有 Prompts 的用户显得「没个性」。因此 Profile 编辑页必须有**完成度进度条**（%）来持续激励用户填写，并明确标注每个字段的价值（「添加职业，让对方更了解你」）。Tinder（flow 3440，54 屏）是最完整的参考，实现了「Edit / Preview 双 Tab」，让用户随时切换到「他人视角」查看自己的卡片效果。照片管理 3x3 Grid 是约会 App 独有的核心 UI——照片顺序直接影响曝光效果。

**行业共识**：Tinder（flow 3440）确认：3x3 照片 Grid（拖拽排序）、Prompts 问答文字、Edit/Preview 双 Tab、完成度进度条、保存后 success toast。

**Entry**: Profile Tab（最右 Tab）→ 点击「编辑资料」/ 完成度进度条

```
Screen 1: Profile 主页（Profile Overview）
  主操作: 查看当前资料完整度，进入编辑
  关键组件:
    - 顶部自己的卡片预览（缩略版，约 150pt 高度）
    - Profile Completion Card（醒目位置）:
        LinearProgressBar（如 65%）
        Text「你的资料 65% 完整」
        Text「添加一个 Prompt，让对方更了解你」（当前最影响完整度的字段提示）
    - Button「编辑资料」（主 CTA，进入 Screen 2）
    - 快速设置 Section（无需进入编辑页）:
        Discovery Settings（年龄范围 / 距离 / 关系意向 Slider）
        Notifications 开关（Match 通知 / 消息通知）
    - 订阅状态（Gold / Platinum Badge，或「升级到 Gold」入口）

Screen 2: 资料编辑器（Profile Editor）
  主操作: 编辑照片、Prompts、基本信息
  关键组件:
    - 顶部 Tab 切换（「编辑 Edit」/ 「预览 Preview」）
    - [Edit Tab 内容]:
      **照片管理区（3x3 Grid）**:
          - 已有照片格（展示照片缩略图，右上角「✏」编辑）
          - 空白格（「+」添加照片，点击 → Action Sheet: 「从相册选择」/ 「拍摄」）
          - 长按照片 → 拖拽排序（视觉拖拽反馈：被拖拽格放大 + 半透明）
          - Smart Photos 开关（AI 自动优化照片顺序，实验功能）
      **Bio Section**:
          - TextArea（「关于我...」，500 字上限 + 字数计数器）
          - Placeholder 示例文字（灰色，聚焦后消失）
      **Prompts Section**（2-3 个问答）:
          - 每个 Prompt 行: 题目（灰色小字）+ 回答（加粗）+ 右侧「✏ 编辑」
          - Button「+ 添加 Prompt」→ Screen 2a（选题目）
      **基本信息 Section**（水平 Chip 行）:
          - 职业 / 学校 / 身高 / 性别 / 关系意向 / 语言等
          - 每项点击 → 内联 Sheet 或全屏编辑
      - 底部 Button「保存」（主色，全宽）或顶部 NavigationBar Button「完成」
    - [Preview Tab 内容]:
      全屏卡片预览（完全模拟他人看到的滑卡视角）
      - 照片横向滑动（可查看所有照片）
      - 信息叠层（姓名 / 年龄 / 距离占位）
      - Bio + Prompts（滚动查看完整资料）
      - 底部「返回编辑」Button（次要）
  → 点击照片格「✏」: 操作 Sheet（「设为封面」/ 「删除」/ 「替换」）
  → 点击「+ 添加 Prompt」: Screen 2a
  → 点击「保存」/ 「完成」: 资料更新，Toast「资料已更新」，返回 Screen 1

Screen 2a: Prompt 选题目（Prompt Picker）
  主操作: 从题库中选择一个 Prompt 题目
  容器: Full-screen Push 页或 Bottom Sheet Large
  关键组件:
    - SearchBar（搜索题目关键词）
    - 分类 Section List（「关于我」/ 「我的生活」/ 「我的梦想」/ 「轻松问题」）
    - 每个题目行（点击选中）:
        题目文字（如「My love language is...」）
        [已选中] 右侧蓝色勾选图标
  → 选中题目: 跳转 Screen 2b（回答编辑）

Screen 2b: Prompt 回答编辑
  主操作: 为选中题目写回答
  关键组件:
    - 题目文字（只读，灰色，页面顶部）
    - TextArea（回答内容，140字上限 + 右下角字数倒计）
    - 示例回答（灰色 placeholder，「e.g. 一杯咖啡 + 一本书 + 一张窗边的桌子」）
    - Button「完成」（右上角，有内容后激活）
  → 点击「完成」: 回到 Screen 2 Profile 编辑器，Prompt 区更新
```

**Exit State**:
- ✅ 保存成功：Toast「资料已更新」；完成度进度条百分比上升
- ↩ 未保存退出（有改动时）: Dialog「放弃改动？」→「放弃」/ 「继续编辑」
- ❌ 照片不符合规范（无人脸/含违规内容）: 上传后图片区显示「照片审核中」状态，审核不通过后显示原因

---

### Flow 3: 配对后对话（Match → Message）

**在此场景的特殊性**: 约会 App 的对话与普通 IM 的最大差异是**破冰难度极高**——「配对了但不知道说什么」是用户最高频的痛点，产生了大量「沉默配对」（silent matches，配对后无人发消息）。正确的设计需要降低开口摩擦：系统提供 Ice Breaker Suggestions、对方填写的 Prompt 答案可以直接作为「评论此 Prompt」的起点、in-chat GIF/Sticker 选择器降低无话可说的尴尬。Tinder（flow 3469）展示了对话内嵌 Spotify 音乐分享——富媒体消息让对话不只是文字交换，音乐品味是天然的破冰话题。

**行业共识**：Tinder（flow 3469/3428）确认：对话列表顶部横向 Matches 头像行；对话内嵌 GIF/音乐选择器（Bottom Sheet）；配对前可发 First Impression Message。

**Entry**: Match 弹窗「发消息」CTA / 消息 Tab → 点击 Matches 头像 / 点击对话列表行

```
Screen 1: 消息总览（Messages Overview）
  主操作: 查看新配对和进行中的对话
  关键组件:
    - 顶部横向 Matches 行（新配对头像，最多显示 5-7 个，右滑查看更多）:
        Section Header「新配对」
        头像（圆形，右下角「New」Badge 闪烁）+ 名字
        [空状态] 「继续滑卡发现更多人」提示
    - 对话列表（FlatList，按最近消息降序）:
        每行: 头像 + 名字 + 最新消息预览（或「发出第一条消息！」）+ 时间
        Unread Badge（小红点，右侧）
        [超过 24h 未回复] 「正在消失...」红色计时器（Bumble 模式，部分 App 有）
    - [搜索] 右上角搜索图标 → 搜索配对名字
  → 点击 Matches 头像（未对话）: 进入 Screen 2（空对话，含破冰提示）
  → 点击对话列表行（已对话）: 进入 Screen 2（历史对话）

Screen 2: 单条对话（Conversation）
  主操作: 与配对用户对话
  关键组件:
    - NavigationBar: 返回 + 对方头像（圆形，可点击查看资料）+ 名字 + ··· 操作菜单
    - 对话顶部（首次进入空对话时）:
        配对纪念头像组（双方头像并排 + 「你们是一对新 Match！」）
        Ice Breaker Suggestion Chips（「你喜欢 [对方 Prompt 中提到的内容] 吗？」）
        [对方的某个 Prompt 卡片] → 「评论此 Prompt」CTA（降低冷启动摩擦）
    - 消息列表（FlatList，自动滚到最新）:
        文字气泡（左/右，左侧灰色/右侧品牌色）
        GIF 卡片消息（带动图，点击暂停）
        Spotify 音乐卡片（封面 + 曲名 + 艺人 + 播放按钮）
        时间戳（每隔一定时间显示）
        已读状态（「已读」/ 「已送达」，右下角）
    - Composer（固定底部）:
        TextInput（「发消息...」，多行自动扩展）
        Button（😊 表情 / GIF 选择器图标）→ Bottom Sheet（Screen 2a）
        Button（♪ 音乐分享图标）→ Bottom Sheet（Screen 2b）
        Button（发送 ▲，有内容后激活）
  → 点击 Ice Breaker Chip: 自动填入 Composer
  → 点击「评论此 Prompt」: Composer 预填引用文字

Screen 2a: GIF 选择器（Bottom Sheet）
  主操作: 在对话中发送动图
  容器: Bottom Sheet（Medium，搜索框自动聚焦）
  关键组件:
    - SearchBar（「搜索 GIF...」，GIPHY / Tenor 接入）
    - GIF 网格（2列，懒加载）: 点击发送，Sheet 收起
    - 分类 Chips（「热门」/ 「爱心」/ 「笑话」）

Screen 2b: 音乐分享（Spotify Track，Bottom Sheet）
  主操作: 在对话中分享一首歌
  容器: Bottom Sheet（Medium）
  关键组件（Tinder flow 3469 实现）:
    - SearchBar（「搜索歌曲或艺人...」）
    - 热门推荐列表（封面 + 曲名 + 艺人，每行可点击播放预览片段）
    - 搜索结果列表（同样格式）
    - 点击曲目: Sheet 收起，消息流中插入音乐卡片（封面 + 曲名 + 艺人 + 播放按钮）
```

**Exit State**:
- ✅ 发送消息：气泡立即出现，状态「已送达」
- ✅ 发送 GIF / 音乐：富媒体卡片出现在消息流，对话活跃度提升
- ❌ 对方取消配对（Unmatch）: 对话从列表消失，用户无通知（静默移除）

---

### Flow 4: 高级功能与付费升级（Premium Upsell）

**在此场景的特殊性**: 约会 App 的付费转化策略与其他 App 根本不同——它不靠广告拦截或功能限制，而靠「情绪钩子」转化。最强的情绪钩子是「有人喜欢你但你看不到」（Likes Tab 模糊头像），第二强是「Super Like 用完了」（限额 + 明确提示用完），第三强是「想看看被 Skip 掉的那个人」（Rewind 按钮灰色 + 付费解锁）。Tinder 的 Gold / Platinum 订阅采用 Feature Gate 模式：在用户即将使用某功能的精确时刻触发 upsell，而非在 Onboarding 时强推付费页——Tinder（flow 3427）确认 Boost 按钮在操作栏常驻，用完后触发 upsell；（flow 3438）安全提示轮播完成后推付费。

**行业共识**：Tinder（flow 3427/3438/3437）均采用「Feature Gate 模式」——在用户试图使用付费功能的精确时刻（而非主动进入设置页）弹出 upsell Bottom Sheet，保留当前视图上下文。

**Entry**: 多个 Feature Gate 入口（见下方各 Screen）

```
Screen 1: Likes Tab（Freemium Gate — 最强转化入口）
  主操作: 查看谁喜欢了自己
  关键组件（免费用户视角）:
    - Tab 徽章（红色数字，如「7」，显示有 7 人喜欢了你）
    - 模糊头像网格（Grid，可见头像轮廓但无法辨认面孔，高斯模糊）
    - 锁定覆盖层文字:「7 人喜欢了你」（大号，白色）
    - 付费 CTA（底部固定）: Button「解锁，查看是谁」（主色，全宽）
    - 社会证明文字（锁定层内）: 「升级到 Gold，看清每一位喜欢你的人」
  → 点击「解锁，查看是谁」: Screen 3（订阅购买 Sheet）
  → [付费用户] 清晰头像网格，点击头像直接进入 Like + Match 流程

Screen 2: Boost upsell（滑卡中触发）
  触发: 点击操作栏 ⚡ Boost 按钮（或 Boost 配额用完时）
  容器: Bottom Sheet（Medium，滑卡视图在后方仍可见）
  关键组件:
    - 功能说明插图（箭头向上/曝光扩大动图）
    - 标题「Boost：30 分钟内让你的资料排名第一」
    - 社会证明（「Boost 用户的配对数量平均提升 10 倍」）
    - 价格选项（单次 / 套餐，RadioGroup 或 Selector）
    - Button「购买 Boost」（主色，全宽，显示选中价格）
    - Button「稍后」（文字链接，次要，关闭 Sheet）
  → 点击「购买 Boost」: 触发 Apple IAP → 支付成功 → 计时器倒计（30:00）出现在滑卡顶部
  → 点击「稍后」: Sheet 收起，回到滑卡视图

Screen 3: 订阅购买（Gold / Platinum Subscription Sheet）
  触发: 从 Likes Tab 「解锁」入口 / 从 Settings 「升级」入口
  容器: Bottom Sheet Large 或全屏 Modal
  关键组件:
    - 产品标题（「Tinder Gold」/ 「Tinder Platinum」）
    - 功能对比列表（✓ 无限 Likes / ✓ 查看谁喜欢你 / ✓ Passport / ✓ Boost 每月 1 次）
    - 订阅方案选择（RadioGroup + Selector，3个方案）:
        1 个月（¥198/月）
        6 个月（¥99/月，「最受欢迎」Badge）
        12 个月（¥75/月，「超值」Badge）
    - 实时价格摘要（选中方案后实时更新）
    - Button「开始免费试用 / 立即订阅」（主色，全宽，含选中价格）
    - 「订阅后可随时取消」文字（法律合规，灰色小字）
    - 「恢复购买」文字链接（已付费用户换设备时使用）
  → 点击「立即订阅」: 触发 Apple IAP → 订阅成功 → Sheet 关闭，功能即时解锁

Screen 4: Super Like 用完后 upsell（Super Like Refill）
  触发: 点击 ⭐ Super Like 按钮，但今日配额已用完（每天 1 次免费）
  容器: Bottom Sheet（Small，简洁）
  关键组件:
    - 文字「今日 Super Like 已用完」
    - 补充选项（套餐选择，2-3 个）: 「5 个 Super Likes ¥18」/ 「30 个 ¥88」
    - Button「购买」（主色）
    - Button「明天再来」（次要，文字链接，关闭 Sheet）
```

**Exit State**:
- ✅ 订阅成功：Likes Tab 解锁，模糊头像变清晰；顶部出现 Gold 徽章
- ✅ Boost 购买成功：滑卡顶部出现 30 分钟计时器，曝光提升
- ↩ 取消付费：Sheet 关闭，功能保持锁定状态，无任何惩罚性提示

---

## Mobile Component Kit

按使用频率排序（基于研究样本观察）：

| 优先级 | 组件（H5 antd-mobile）| 组件（RN Gluestack/RN）| 具体用途 |
|---|---|---|---|
| ★★★ | 自定义卡片叠层（CSS 绝对定位）| `react-native-deck-swiper` / 自定义 PanResponder | Swipe Deck（全屏卡片叠层 + 手势）|
| ★★★ | `Popup`（full-screen）| Full-screen Modal（动画）| Match 庆祝弹窗（全屏打断）|
| ★★★ | `ActionSheet` | `ActionSheet` | 封锁/举报操作菜单 |
| ★★★ | `Dialog` | `AlertDialog` | 封锁二次确认（「此操作无法撤销」）|
| ★★★ | `Popup`（bottom）| `BottomSheet` | Boost/Super Like upsell / GIF 选择器 |
| ★★ | 3x3 `Grid` + 拖拽 | `DraggableFlatList` / 自定义 | 照片 Grid 管理（拖拽排序）|
| ★★ | `ProgressBar` | `ProgressBar` | Profile 完成度进度条 |
| ★★ | `TextArea` + 字数计数 | `TextInput` + 字数计数 | Bio 编辑（500 字）/ Prompt 回答（140 字）|
| ★★ | `SearchBar` | `SearchBar` | GIF / 音乐 / Prompt 题目搜索 |
| ★★ | `Tabs`（2 Tab）| `TabView` | Profile 编辑器「Edit / Preview」双 Tab |
| ★ | `Tag` / `Chip` | `Chip` | 兴趣 Tags（流式布局）/ Ice Breaker Chips |
| ★ | `Badge` | `Badge` | Matches 新配对角标 / Unread 消息角标 |
| ★ | `Toast` | `Toast` | 资料保存成功 / 操作完成反馈 |
| ★ | `Radio` + `Selector` | `RadioGroup` | 订阅方案选择（1/6/12 个月）|

---

## Anti-Patterns

- **滑卡视图的 Tab Bar 用实色背景占据底部空间**：照片被实色 Tab Bar 截断，全屏沉浸感破坏，用户注意力被导航元素分散。→ 正确做法：Tab Bar 在滑卡 Tab 上设为透明底色，操作按钮区域与 Tab Bar 层叠于同一位置，照片延伸到安全区域底部（Tinder flow 3427）。

- **Likes Tab 对免费用户直接隐藏（空状态或无此 Tab）**：错失了最高效的付费转化入口——「知道有人喜欢你但看不到谁」的好奇感是付费的最强动机。→ 正确做法：Likes Tab 对所有用户可见，但显示模糊头像 + 人数统计（「7 人喜欢了你」），用「剧透式遮罩」制造付费动机，而非完全隐藏功能。

- **Match 庆祝弹窗用 Toast 或系统通知而非全屏 Modal**：错过了约会 App 用户最重要的情绪峰值时刻，用户没有「配对成功」的仪式感，留存率显著下降。→ 正确做法：双向 Like 触发全屏 Modal（动画 + 粒子效果 + 双方头像），提供「发消息」主 CTA，强制让用户意识到这一里程碑时刻的重要性。

- **Profile 编辑没有「Preview」功能，用户不能从他人视角查看自己的卡片**：用户填写资料后无法预判卡片在滑卡视角下的实际效果，可能第一张照片不好但没意识到。→ 正确做法：Profile 编辑页提供 Edit/Preview 双 Tab，Preview 完全模拟滑卡视角全屏展示卡片（Tinder flow 3440）。

- **破冰（Ice Breaker）完全依赖用户自主发起，空对话只有输入框**：配对后空对话的压力极高，「沉默配对」（配对后从未对话）占全部配对的 50-70%。→ 正确做法：首次进入空对话时显示 Ice Breaker Suggestions（基于对方 Prompts 生成的话题 Chips），「评论此 Prompt」让用户有明确的对话切入点（Tinder flow 3428 / 3469 中均有此模式）。

- **封锁/举报只需一步操作（单次点击即执行）**：误操作率高，用户可能在滑卡时误触举报，造成不必要的账号问题。→ 正确做法：三步确认（Overflow ··· → Action Sheet → Dialog 确认，Dialog 说明「封锁后对方从所有位置消失且无法撤销」），Tinder（flow 3424）是标准实现。
