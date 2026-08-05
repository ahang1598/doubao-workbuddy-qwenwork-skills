# Scenario: Mobile Entertainment（娱乐 & 流媒体）

> **研究来源**：基于对 Luminary、Vinyls、UGLYCASH TV、DailyArt、Train Fitness、Breathwrk、Volv、Riverside、Sky Guide 等 9 个真实 iOS 产品 flow 和页面的横向分析抽象，不代表任何单一产品的具体实现。

---

## Identity

**Platform**: Mobile (H5 / React Native)
**Definition**: 以内容消费为核心的移动端娱乐应用，用户通过浏览/搜索发现视频、音乐、播客等内容，触发全屏或后台播放；应用通过 Freemium 模式运营，付费内容触发 Paywall，用户通过应用内订阅流程购买高级计划。

**Canonical Examples**: Netflix iOS、Spotify iOS、YouTube iOS、Luminary（播客）

**Not this scenario if**:
- 以直播互动为主（Twitch 类，重在弹幕/礼物互动，属于 Consumer Social 子集）
- 以短视频浏览为主（TikTok，属于 Consumer Social 场景）
- 以音频课程/播客学习为主（教育目的，改用 mobile/edtech）
- 主要在 Web 端使用（改用 web/ecommerce 或 web/community-social）
- 以游戏为主（属于 Gaming 子场景）

---

## User Profile

| 维度 | 内容 |
|---|---|
| **主要角色** | 休闲观看者（下班后追剧/看视频）/ 音乐听众（通勤/运动时背景音乐）/ 播客爱好者（碎片时间收听）|
| **核心目标** | 发现想看/听的内容 / 继续上次未看完的内容 / 以最少步骤进入播放状态 |
| **心智模型** | 期待「一键播放」（点击封面即开始播放，无需先进详情页）；期待从上次停止处继续（Resume）；期待后台不打断（锁屏后仍在播放）|
| **使用频率** | 高频（每天 1-3 次）：通勤 / 睡前 / 运动时 |
| **决策模式** | 混合型：有明确目标（「继续看第 3 集」）时直接操作；无目标时探索推荐 Feed |
| **容错期望** | 订阅前有免费试用（7 天）；误购可通过平台官方流程退款；收藏/观看列表随时可增删 |

---

## IA Template

**导航模式**: Tab Bar（底部 Tab Bar，4-5 项）

典型结构（Netflix / Spotify 模式）：
```
Tab 1: 首页 / Home    — 推荐内容 + 续播 + 分类横向 Carousel
Tab 2: 搜索 / Search  — 搜索框 + 分类 Grid（类型/主题）
Tab 3: 我的库 / Library — 已保存/收藏/下载内容
Tab 4: 我的 / Profile — 账户 + 订阅状态 + 设置
```

播客平台模式（Luminary）：
```
Tab 1: 发现 / Discover — 编辑推荐 + 分类 Feed
Tab 2: 搜索 / Search   — 播客/剧集搜索
Tab 3: 收件箱 / Inbox  — 新剧集未听通知列表
Tab 4: 我关注的 / Following — 已订阅播客
Tab 5: 我的 / Profile  — 账户 + Premium 状态
```

**页面层级**: 3 级
```
L1: Tab 根页（Home / Search / Library）
L2: 内容详情页（Show Detail / Album Detail / Podcast Detail）
L3: 播放器（全屏 Player）/ Paywall Modal（订阅页）
```

**权限流结构**（娱乐 App 权限较少）:
```
Notifications（新剧集提醒 / 下载完成）:
  → 说明页（「新剧集上线提醒，不错过你追的剧」）→ 系统通知权限弹窗
  → 触发时机: 首次完成内容收藏后

Background App Refresh（后台下载离线内容）:
  → 系统级，通常在 App 设置说明

Microphone（语音搜索，部分 App）:
  → 自定义说明页 → 系统麦克风权限弹窗
```

**数据密度**: 低（Cover 图主导，内容用「封面大图 + 标题」卡片展示）
- 核心视图：横向 ScrollView（Carousel 推荐）+ 纵向 List（列表）
- 辅助视图：Grid（2-3 列封面 Grid）
- 播放器：全屏视频播放器（H5 `<video>` 全屏 / RN `react-native-video`）
- 不使用：多列 Table、复杂 Form

**主要容器模式**:
| 场景 | 容器 |
|---|---|
| 视频播放器（全屏）| Full-screen Modal 或系统全屏视频组件 |
| Paywall（订阅触发）| Bottom Sheet（large）或 Full-screen Modal |
| 音频播放（Mini Player → 全屏）| 底部常驻 Mini Player + Full-screen Modal 展开 |
| 字幕/音频轨道选择 | Action Sheet 或 Bottom Sheet（medium）|
| 剧集列表（Season/Episode）| Stack Push 或 Bottom Sheet（large）|
| 删除下载/收藏确认 | Dialog |
| 分享内容 | 系统分享面板 / `navigator.share`（H5）|

**导航骨架图（ASCII，Netflix 模式）**:
```
┌────────────────────────────────────┐
│  Status Bar（时间 / 信号 / 电量）    │
├────────────────────────────────────┤
│  [Netflix Logo]         [搜索] [铃] │  ← 顶部 Logo + 操作图标
│                                    │
│  [全部] [电影] [剧集] [我的列表]    │  ← 分类 Chip 横向
│                                    │
│  ┌──────────────────────────────┐  │
│  │    Hero Banner（精选内容）    │  │  ← 大封面 Hero（全宽）
│  │  [▶ 播放]  [+ 我的列表]  [ℹ]  │  │  ← Hero 底部操作栏
│  └──────────────────────────────┘  │
│                                    │
│  继续收看                            │
│  [封面] [封面] [封面] [封面] →      │  ← 横向 Carousel
│                                    │
│  因为你看了...                       │
│  [封面] [封面] [封面] [封面] →      │  ← 推荐 Carousel
│                                    │
├───┬──────┬──────┬─────────────────┤
│ 🏠 │  🔍  │  下载 │  我的            │  ← TabBar
└───┴──────┴──────┴─────────────────┘
```

---

## 该场景独有的 IA/UX 决策

1. **移动端订阅支付须遵循平台规范，「恢复购买」是重要的合规与用户体验要求** — 移动端娱乐 App 的订阅在 iOS 上须通过 App Store（StoreKit），Android 须通过 Google Play Billing，H5 版本可使用自定义支付处理器（Stripe 等）。无论哪种路径，Paywall 界面都应包含「恢复购买」选项，为换机/重装用户找回历史订阅——所有 9 个研究样本均有此按钮，缺少会影响用户信任感，不是可选项。

2. **Paywall 必须先展示功能价值再展示价格，Annual 计划必须高亮为默认选中** — Paywall 转化逻辑是「先理解能得到什么，再判断价格是否值得」。功能 Carousel（Feature Card 横向滑动）或 Checkmark 功能 List 必须出现在价格选择之前或同屏顶部区域——只展示价格不展示价值会让用户无从判断。Annual 计划用高亮边框 + 「节省 X%」Badge + 默认选中表达推荐，Monthly 计划用轻描边作为备选（所有 9 个研究样本均采用此模式）——两者视觉平等展示会让用户陷入选择困难，显著降低年付转化率（Breathwrk / DailyArt / Train Fitness 均验证了此结构）。

3. **视频播放器控制 HUD 必须在播放状态下 3 秒无操作后自动淡出** — 全屏视频播放器的控制层（进度条/标题/字幕按钮）若始终显示，会永久遮挡视频字幕和人物脸部。必须实现：3 秒无交互后控制层淡出，点击屏幕任意处重新显示，暂停状态下保持可见。H5 `<video>` 需自定义控制栏并实现此逻辑；RN `react-native-video` 同样需要手动实现 HUD 的自动隐藏——这是移动端视频 App 的行业标准体验。

4. **音频 App 必须实现常驻底部 Mini Player，从任意 Tab 均可控制** — 移动端音频播放（播客/音乐）的核心 UX 约定是：一旦开始播放，底部出现 Mini Player（固定在 Tab Bar 上方），用户切换到任意 Tab 后 Mini Player 持续可见，可直接暂停/换下一首，无需返回播放页——「边听边浏览」是播客/音乐 App 的核心使用模式（Spotify iOS / Luminary 的行业标准）。没有 Mini Player 意味着用户每次切 Tab 后需重新找回播放页才能控制，「后台播放 + 便捷控制」的核心价值被完全破坏。

5. **移动端锁屏媒体控制和后台播放是音视频 App 的必要原生能力** — iOS 音频 App 须响应 `MPNowPlayingInfoCenter` + `MPRemoteCommandCenter`（锁屏控制中心和耳机线控控制播放）；Android 使用 MediaSession API；H5 使用 Media Session API（`navigator.mediaSession`）。用户「生活在 App 外」时（锁屏、切换其他 App）仍能无缝控制内容，是移动端娱乐 App 区别于纯 Web 版本的核心体验价值。

---

## Canonical Flows

> 以下 flow 基于 9 个真实产品样本横向分析抽象。括号内标注「行业共识」表示 3 个以上产品采用相同模式。

---

### Flow 1: Browse & Discover Content（内容浏览 + 内容详情）

**在此场景的特殊性**: 移动端娱乐 App 的内容首页与 Web 端最大的区别是**横向 Carousel 主导的垂直堆叠结构**——每个推荐类别占一行，横向可滚动，每个 Carousel 的封面卡片高于宽（3:4 或 2:3 比例），视觉冲击力强（Netflix/Spotify/Luminary 均如此）。**Hero Banner 全宽精选内容**（顶部约占 40vh，包含直接播放按钮）是流媒体的行业共识。**续播 Carousel**（「继续收看」或「为你推荐」）通常是首个 Carousel，每张卡片包含播放进度条，让用户一眼看出看到哪里——这是内容消费 App 与购物 App 内容列表最大的 UX 差异。内容详情页必须在顶部展示**大尺寸 Hero Image（或视频 Trailer）**，而非文字列表，才符合用户「看到想不想看」的感知模式。

**行业共识**：Netflix / Spotify / Luminary 均使用「Hero Banner + 横向 Carousel 列表」的首页结构；内容详情页顶部为 Hero + 播放 CTA（行业共识，见视频播放器研究）。

**Entry**: App 启动 → 首页 Home Tab（已登录状态）

```
Screen 1: 首页 / Home（内容 Feed）
  主操作: 浏览推荐内容 / 点击 Hero 播放 / 点击感兴趣内容
  关键组件:
    - ScrollView（纵向，下拉刷新）
    - 顶部: Logo + 分类过滤 Chips（横向滚动：「全部」「电影」「剧集」「我的列表」）
    - Hero Banner（全宽，约 56:32 比例，精选内容大图）:
        背景图 + 渐变遮罩 + 底部操作栏
        操作栏: Button("▶ 播放", 主色) + Button("+ 我的列表", 次要) + Button("ℹ 详情", 文字)
    - Carousel 1（「继续收看」）: 横向 ScrollView + 卡片列表:
        每张卡片: 封面图（16:9）+ 进度条（底部叠加）
    - Carousel 2-N（推荐分类）: 横向 ScrollView + 卡片列表:
        每张卡片: 封面图（2:3，标准竖向封面）+ 可选标题
    - [可选] Featured Row（精选 2-3 个 Large 卡片）
  → 点击 Hero「播放」: Full-screen Modal → Flow 2 播放器
  → 点击某封面卡片: Stack Push → Screen 2 内容详情
  → 点击「+ 我的列表」: 立即收藏，图标切换，Toast「已加入我的列表」

Screen 2: 内容详情（Show / Album / Podcast Detail）
  主操作: 了解内容 → 播放 / 收藏 / 收听
  关键组件:
    - Stack Push（透明导航栏叠于 Hero 图上）
    - 顶部 Hero Image / Trailer（全宽，16:9 或竖向封面）
      [可选] 自动播放 Trailer（静音，3 秒后开始）
    - 标题区:
        内容名（粗体大字）
        年份 / 评级 / 时长 / 类型标签（小字灰色）
    - 操作按钮区:
        Button("▶ 播放", 主色，全宽或大宽按钮)
        Button("⬇️ 下载", 次要，可选，需订阅)
        Button("+ 我的列表 / ♥ 收藏", 次要)
    - 内容简介（限制 3 行，「展开」→ 展开全文）
    - [视频/剧集] Section「剧集」: 季/集 Picker + 剧集 List（每行: 缩略图 + 集数 + 时长 + 简介）
    - [播客] Section「剧集」: 剧集 List（每行: 标题 + 时长 + 日期 + 播放按钮）
    - Related Content Carousel（「相似内容」）
  → 点击「播放」: Full-screen Modal → Flow 2 播放器（全屏）
  → 点击剧集行「播放」: 直接从该集开始播放
  → 点击「+ 我的列表」(付费内容，未订阅): Bottom Sheet → Flow 3 Paywall
```

**Exit State**:
- ✅ 成功加载：首页 Carousel 显示完整，推荐内容个性化
- ⚠️ 网络断开：只显示已缓存/下载内容，Banner「无网络，显示离线内容」
- 空状态（新用户 Library 为空）：Empty 组件「还没有收藏，快去发现吧」+ 「去发现」CTA

---

### Flow 2: Content Playback（全屏视频 / 音频播放）

**在此场景的特殊性**: 移动端的全屏视频播放器与 Web 端差异极大——Web 端播放器嵌在页面中，移动端通常是 **Full-screen Modal 全屏黑背景**（Netflix/YouTube 模式）。控制栏**自动隐藏**（点击屏幕显示，3 秒无操作后淡出），避免遮挡内容。**续播（Resume）** 机制：返回首页后同一内容的进度条准确更新，重新打开时弹出「继续播放」vs「从头开始」的选择（Action Sheet 或 Dialog）。音频播放（播客/音乐）通常使用常驻底部 **Mini Player**，点击展开为全屏播放器。

**行业共识**：所有研究样本的视频全屏播放器均使用黑色背景 + 自动隐藏控制栏 + 手势（左右滑动快进退）；音频 Mini Player 底部常驻是 Spotify / Luminary 的行业标准。

**Entry**: 内容详情页 → 点击「▶ 播放」→ Full-screen Modal 触发

```
Screen 1: 视频播放器（全屏）
  主操作: 观看视频 / 控制播放进度
  关键组件（黑色全屏背景）:
    - 视频渲染视图（H5 `<video>` / RN `react-native-video`）
    - 控制 HUD（点击屏幕显示，3 秒无操作淡出）:
        顶部: X 关闭 Button（左）/ 内容标题（中）/ 投屏 Button + 字幕 Button（右）
        中央: Button(⏮ 后退15s) + Button(⏸/▶ 播放/暂停, 大尺寸 ≥48pt) + Button(⏭ 前进15s)
        底部: Slider（播放进度，当前时间 / 总时长）
        底部右: Button(字幕/音频) + Button(剧集)
    - [手势] 左右滑动（快退/快进）
    - [手势] 双击左侧（后退 10s）/ 双击右侧（前进 10s）
  → 点击字幕/音频: Action Sheet（字幕语言列表 / 音频轨道选择）
  → 点击剧集: Bottom Sheet（large）弹出剧集列表 → 点击切换集数
  → 点击 X / 下滑手势: 关闭全屏 → 返回内容详情页

Screen 2: 音频 Mini Player（常驻底部，音乐/播客）
  触发条件: 开始播放音频内容
  主操作: 查看当前播放 / 暂停 / 跳转全屏
  关键组件（固定在 Tab Bar 上方，毛玻璃/半透明背景）:
    - 高度约 64pt
    - 横向排列:
        封面图（40×40pt，圆角）
        内容标题（单行截断）+ 来源名（小字）
        Spacer
        Button(⏸/▶ 暂停/播放，图标 ≥24pt)
        Button(⏭ 下一首)
    - 顶部: 薄进度条（1-2pt 高度，品牌色）
  → 点击 Mini Player 任意区域（非按钮）: Bottom Sheet（large）或 Full-screen Modal 展开全屏播放器
  → 点击⏭: 跳到下一集/下一首，Mini Player 内容更新

Screen 3: 全屏音频播放器（Mini Player 展开后）
  主操作: 控制播放 / 查看歌词/章节 / 分享
  关键组件:
    - Bottom Sheet（large）或 Full-screen Modal
    - 大封面图（居中，约 280×280pt，圆角，轻微阴影）
    - 内容标题（粗体大字）
    - 艺术家/播客名（灰色次要字）
    - 心形收藏 Button + 分享 Button
    - Slider（播放进度 + 当前时间 / 总时长）
    - 控制按钮行:
        Button(⏮) + Button(⏸/▶, 大按钮 ≥56pt) + Button(⏭)
    - Button(🔀 随机) + Button(🔁 循环)（音乐场景）
    - [播客] Button(⏩ 前进30s) + 播放速度 Button("1×")（→ Action Sheet 选速度）
```

**Exit State**:
- ✅ 播放中：进度条持续更新，Mini Player 常驻，Home 界面封面进度条同步
- ⏸ 切换 App：系统媒体通知显示播放控制（音频）
- 💾 已下载内容：离线可播放，无网络 Banner 不显示

---

### Flow 3: Paywall & Subscription Purchase（Paywall + 订阅购买）

**在此场景的特殊性**: 移动端 App 内订阅购买须遵循平台规范（iOS: App Store StoreKit；Android: Google Play Billing），触发**平台级购买确认弹窗**（开发者无法完全自定义此界面）；H5 版本可使用自定义支付处理器（Stripe/支付宝等），拥有更大的界面自定义空间。**Paywall 进入方式**通常是 Bottom Sheet（large）或 Full-screen Modal，确保用户可以随时关闭放弃。**「恢复购买」选项**是移动端合规要求，必须出现在 Paywall 界面。**Annual vs Monthly 双计划**是行业共识：所有研究样本（8/9）均默认选中 Annual（高亮显示「最受欢迎」badge），Annual 节省百分比（「省 37%」）以醒目文字展示。

**行业共识**：Breathwrk（flow 7743）/ Luminary（flow 4696）/ Vinyls（flow 8916）/ Train Fitness（flow 7156）均使用「功能列表 → 计划选择 → 购买确认 → 成功确认」4 步标准 Paywall 结构；Annual 计划默认高亮是所有样本共识。

**Entry**: 点击付费内容 / 在设置页点击「升级 Premium」/ Onboarding 结束时插入

```
Screen 1: Paywall 功能展示页
  触发条件: 用户访问付费内容，或主动点击「解锁高级功能」
  主操作: 了解高级功能 → 进入计划选择
  关键组件:
    - Bottom Sheet（large）或 Full-screen Modal（可关闭）
    - X 关闭 Button（右上角，让用户可以随时关闭）
    - Hero 区域（选择一种）:
        Option A - 功能 Carousel（Swiper/Carousel，每页一个 Feature Card）:
            大图标 + 功能标题 + 描述（2-3 行）
        Option B - 功能 List（每行 checkmark + 功能描述）
    - [可选] 社会证明（评分区：⭐⭐⭐⭐⭐ + 评价数量 + 引用短评）
    - Button("继续", 主色，全宽，→ Screen 2）

Screen 2: 订阅计划选择（Plan Selection）
  主操作: 选择 Annual 或 Monthly 计划 → 订阅
  关键组件:
    - 计划卡片（2 个，单选 RadioGroup 风格）:
        Annual 卡片（默认选中，高亮边框 + 品牌色）:
            「年付」+ 「¥X/年，折合 ¥X/月」
            Badge("节省 XX%"，绿色填充)
            Badge("7 天免费试用"，可选)
        Monthly 卡片:
            「月付」+ 「¥X/月」
    - 试用说明（小字灰色）:
        「免费试用 7 天，到期自动转为年付 ¥X/年，随时可取消」
    - Button("开始免费试用", 主色，全宽，显示当前选中计划)
    - Button("恢复购买", 文字按钮)（合规要求，必须出现）
    - Text("服务条款 · 隐私政策", 小字，链接样式）（合规要求）
  → 点击「开始免费试用」: 触发平台购买流程 → Screen 3

Screen 3: 购买确认（平台级或自定义）
  主操作: 确认购买
  关键组件（视平台不同）:
    - [iOS/Android 原生] 平台级购买确认弹窗（开发者无法自定义）:
        订阅详情（App 名称 + 计划名称 + 价格 + 计费周期说明）
        试用期说明 + 生物识别 / 密码确认
    - [H5] 自定义支付界面:
        信用卡 / 支付宝 / 微信支付等输入表单
        订单摘要 + 确认支付按钮
    - 支付处理 Loading
  → 购买成功: 进入 Screen 4
  → 购买取消/失败: 返回 Screen 2（Plan Selection），显示错误 Toast

Screen 4: 购买成功确认（Post-Purchase）
  主操作: 确认订阅成功 → 回到内容
  关键组件:
    - 大图标（成功 checkmark，绿色，≥60pt）或动画
    - Text("订阅成功！", 粗体大字)
    - Text("7 天免费试用已开始", 灰色)
    - Button("开始探索", 主色，全宽，关闭 Paywall，解锁内容)
    - Toast（若返回原页：「Premium 已解锁」，3 秒消失）
```

**Exit State**:
- ✅ 订阅成功：Paywall 关闭，原先锁定的内容立即可用，Profile Tab 显示「Premium 会员」
- ↩ 取消购买（平台弹窗取消）：返回 Plan Selection，无任何扣费
- ↩ 关闭 Paywall（点击 X）：返回触发 Paywall 的页面，付费内容仍显示锁状态
- ✅ 恢复购买成功：Toast「已恢复您的订阅」，内容解锁

---

---

### Flow 4: Offline Download Management（离线下载管理）

**在此场景的特殊性**: 移动端娱乐 App 的「离线下载」与 Web 端下载有根本差异——Web 端下载是文件系统操作（保存到用户自选路径），移动端下载是 **App 内托管缓存**（文件存在 App 沙箱内，只能在 App 内播放，不暴露文件路径给用户）。Netflix（flow_id 10578，7 屏）展示了下载入口的标准位置：剧集列表中每集右侧的圆形下载图标（空心圆 → 圆形进度环填充 → 实心对勾），无需离开内容详情页即可发起多集下载。HBO Max（flow_id 10289，4 屏）是下载管理页的标准实现：系列为单位分组 + 每集单独显示文件大小 + 编辑模式（勾选 → 批量删除）+ 顶部存储空间指示器（已用 / 总可用）。YouTube Music（flow_id 11367，5 屏）的 Downloaded 筛选 Chip 是「在 Library 中快速定位离线内容」的最简实现——不需要独立 Downloads Tab，Library 横向 Category Chips 中加一个「Downloaded」Pill 即可切换。**Wi-Fi 限制默认开启**是所有样本的共识（TikTok flow_id 2942、YouTube flow_id 2571 均如此），移动数据下载须用户在设置中手动解除限制，防止意外流量消耗。

**行业共识**：Netflix（flow_id 10578）/ Imprint（flow_id 5641）/ HBO Max（flow_id 10289）均以圆形进度环表示下载进度（而非线性 Progress Bar），因为下载图标本身是圆形，进度环视觉整合度更高；下载管理页以「系列」为折叠单位分组是视频流媒体的标准（Netflix / HBO Max），音乐 App 则以「专辑」为单位；「Clear All」或批量删除必须有 Dialog 确认（TikTok flow_id 2942 模式）。

**Entry**: 内容详情页 → 点击集数行的下载图标；或直接进入底部 Tab「下载」/ Library「Downloaded」筛选

```
Screen 1: 剧集列表（下载发起）
  主操作: 在内容详情页选择要下载的集数
  容器: 内容详情页内联（Stack Push 后的 Screen 2 延续，无需新页面）
  关键组件:
    - Section Header「剧集」: Season Picker（下拉选择季数）+ 话题简介
    - List（剧集行，每行）:
        缩略图（小，16:9）+ 集数标题 + 简介（2行截断）+ 时长
        右侧: 下载状态图标（三态）:
          未下载: ⬇️ 圆形空心图标（「下载此集」）
          下载中: 圆形进度环（品牌色，顺时针填充，中央显示「✕」可取消）
          已下载: ✓ 圆形实心图标（品牌色），点击弹出 Action Sheet（「删除此集下载」）
    - Section Footer（已有下载时）: Text「已下载 X 集 · 占用 X.XGB」
    - [可选] Button「下载全季」（置于 Season Picker 旁边，一键下载当前季所有集）
  → 点击空心图标（Wi-Fi 环境）: 开始下载，图标切换为进度环
  → 点击空心图标（移动数据环境）: Toast 弹出「使用移动数据下载？会消耗您的流量」+ Button「允许」/ Button「仅在 Wi-Fi 时下载」
  → 下载完成: 进度环动画完成 → 切换为实心对勾图标（无需用户操作）
  → 进入下载管理: 点击 TabBar「下载」→ Screen 2

Screen 2: Downloads / Library（已下载内容列表）
  主操作: 浏览和管理所有已下载内容
  容器: 独立 Tab（TabBar「下载」图标）或 Library Tab + Downloaded Chip 筛选
  关键组件（两种实现选一）:
    实现 A（独立 Downloads Tab，Netflix 模式）:
      - NavigationBar: 标题「下载」+ Button「编辑」（右上角，进入编辑模式）
      - 存储空间 Bar: 「已使用 [X.XGB] · 剩余 [Y.YGB]」（LinearProgressBar，占满宽度）
      - List（Series Card，每个系列一个折叠组）:
          系列封面图（左，64pt）+ 系列名称 + 「X 集 · X.XGB」
          右侧: 展开箭头「›」（折叠/展开集数列表）
          展开后显示: 每集行（集数 + 标题 + 时长 + 文件大小 + 单集删除按钮）
      - 空状态: 插图 + Text「还没有下载内容」+ Button「浏览内容」

    实现 B（Library + Downloaded 筛选，YouTube Music 模式）:
      - NavigationBar: 标题「我的库」+ 搜索图标
      - 横向 Category Chips（横向 ScrollView，可选）:
          Chip("全部") / Chip("播客") / Chip("专辑") / Chip("Downloaded ✓"，选中态高亮)
          点击「Downloaded」: 列表即时筛选，只显示离线内容
      - Grid 或 List（已下载内容）
  → 点击 Series Card: 展开集数列表 → 可删除单集
  → 点击「编辑」: 进入 Screen 3（编辑/批量删除模式）

Screen 3: 下载管理编辑模式
  主操作: 批量选择并删除下载内容
  容器: Screen 2 的编辑态（不需要新页面）
  关键组件:
    - NavigationBar: Button「取消」（左，退出编辑模式）+ 标题「选择」+ Button「全选」（右）
    - 存储空间 Bar（同 Screen 2，实时更新）
    - List（带 Checkbox 的 Series 列表）:
        每行左侧: Checkbox（空圆圈 → 点击变对勾选中态）
        选中态行: 高亮背景或对勾明显
    - 底部 ActionBar（固定在安全区域上方，选择 ≥1 项后激活）:
        Text「已选择 X 项（X.XGB）」
        Button「删除」（红色，全宽，→ Dialog 确认）
  → 选择所有: 全部 Checkbox 选中，底部显示总大小
  → 点击「删除」:
      Dialog 弹出:「删除 X 部下载内容？此操作无法撤销。」
      Button("删除"，red danger) / Button("取消")
  → Dialog 确认删除: 从列表移除，存储空间 Bar 实时更新
  → 「全选」+ 删除 = 清空所有下载: 列表变为空状态

Screen 4: Smart Downloads 设置
  主操作: 配置自动下载规则
  容器: 设置页（Profile Tab → 「下载设置」）或 Downloads Tab 底部入口
  关键组件:
    - Section「下载设置」:
        Row「仅在 Wi-Fi 下下载」: Switch（默认开启）
        Row「视频质量」: 右侧当前值（「标清 / 高清 / 超清」）+ 「›」→ Picker Sheet
    - Section「Smart Downloads」（自动下载功能）:
        Card 或 List Row: 「Smart Downloads」+ 说明文字「在 Wi-Fi 下自动下载下一集，观看完即删除旧集节省空间」
        Switch（开启 / 关闭）
        若已开启，展示子选项:
          Slider 或 Stepper「保留集数」（1-25 集，实时显示「预计占用 X.XGB」）
          Row「包含新剧集通知」: Switch（推送通知）
    - Section「存储管理」:
        LinearProgressBar（当前 App 占用 / 总设备存储）
        Button「清除所有下载」（红色文字按钮，→ Dialog 确认「清除所有下载内容？」）
        Button「查看下载内容」（→ Screen 2）
```

**Exit State**:

- ✅ 单集下载完成：剧集行图标动画完成变为实心对勾，无 Toast 打扰（静默完成）
- ✅ 整季下载完成：Push Notification「[系列名] 第 X 季已下载完成，可离线观看」
- ✅ 批量删除完成：列表更新，存储 Bar 实时收缩，若全部删除则显示空状态 + 「去发现内容」CTA
- ❌ 存储空间不足（< 500MB）：点击下载时 Toast「设备存储空间不足，请释放空间后再试」+ Button「管理存储」
- ❌ 移动数据下载被拒绝：Toast「已设为 Wi-Fi 下载，连接 Wi-Fi 后自动继续」，下载进入挂起状态（进度环 + 暂停图标）
- ↩ 取消下载中：点击进度环中央的「✕」→ 下载取消，图标恢复为空心下载图标

---

## Mobile Component Kit

按使用频率排序（基于研究样本观察）：

| 优先级 | 组件（H5 antd-mobile）| 组件（RN Gluestack/RN）| 具体用途 |
|---|---|---|---|
| ★★★ | `<video>` + 自定义控制层 | `react-native-video` | 视频播放器（核心功能）|
| ★★★ | Swiper / Carousel | `FlatList` horizontal + `Swiper` | 首页 Hero Carousel / Paywall Feature Carousel |
| ★★★ | Tab Bar / `Tabs` | `react-navigation Bottom Tabs` | App 主导航（Home / Search / Library / Profile）|
| ★★★ | 支付集成（Stripe/微信/支付宝）| `react-native-iap` / Stripe SDK | 订阅购买核心业务逻辑 |
| ★★★ | `Image` + LazyLoad | `FastImage` / `Image` | 内容封面图（Carousel / Grid / Detail Hero）|
| ★★★ | Full-screen Modal | `Modal` / `react-navigation Stack` | 视频播放器全屏 / Paywall 全屏 |
| ★★ | Stack Navigation | `react-navigation Stack` | 首页 → 内容详情 Push 导航 |
| ★★ | Bottom Sheet | `@gorhom/bottom-sheet` | Paywall Modal / 剧集列表 / Mini Player 展开 |
| ★★ | `ProgressBar` / `Slider` | `Slider`（@miblanchard）| 播放进度条 / 内容已看进度 |
| ★★ | Push Notifications | `expo-notifications` / FCM | 新剧集提醒 / 下载完成通知 |
| ★ | 横向 ScrollView | `FlatList` horizontal | 内容 Carousel（推荐/分类横向列表）|
| ★ | Action Sheet | `ActionSheet` | 字幕/音频轨道选择 / 播放速度选择 |
| ★ | 系统分享 / `navigator.share` | `react-native-share` | 分享内容链接 |
| ★ | Empty 空状态组件 | 自定义 Empty | 搜索无结果 / Library 空状态 |

---

## Anti-Patterns

基于研究样本中观察到的设计错误：

- **Paywall 页面没有「恢复购买」选项**：之前订阅过（换手机/卸载重装）的用户无法找回订阅；在原生 App 中还会导致审核被拒。→ 正确做法：Paywall 界面必须包含一个明显可见的「恢复购买」文字按钮，点击后触发平台或服务端检查历史购买（所有研究样本均有此按钮）。

- **Paywall 不可关闭（强制用户必须订阅才能继续）**：用户无法找到关闭按钮，感觉被困住，差评率极高；原生 App 中还违反平台审核规则。→ 正确做法：Paywall 必须有明显的 X 关闭按钮（右上角），或支持下滑手势关闭，允许用户在不订阅的情况下返回（行业共识：所有研究样本均可关闭 Paywall）。

- **Paywall 只展示价格，不展示功能价值**：用户看到「¥68/年」但不知道付费能解锁什么功能，转化率低。→ 正确做法：Paywall 必须先展示功能 Feature List 或 Carousel（3-6 个具体功能点：「无广告」「离线下载」「高清画质」等），再展示价格；功能说明是说服用户付费的关键（Breathwrk / Train Fitness / DailyArt 均有完整 Feature 展示）。

- **首页内容 Carousel 每行展示 4+ 列缩略图**：在手机上每张封面宽度不足 80pt，图片看不清楚，视觉吸引力极弱。→ 正确做法：标准封面 Carousel 每次可见 2.5 张（最右侧部分可见暗示横向可滑动），每张封面宽度约 140-150pt，清晰展示内容（Netflix / Spotify / Luminary 均如此）；「继续收看」Carousel 可用更宽的 16:9 缩略图（可见 1.5-2 张）。

- **视频播放控制栏始终显示，不自动隐藏**：控制栏一直覆盖在视频内容上，遮挡字幕和画面，严重影响观感。→ 正确做法：控制栏默认 3 秒无操作后自动淡出（CSS `opacity` 动画或 RN `Animated`），点击屏幕任意处重新显示；播放暂停时控制栏保持可见（Netflix 标准行为）。

- **音频播放没有 Mini Player，播放停止后无法轻松恢复**：用户切到其他 Tab 后，不知道播放是否继续，也无法快速暂停/跳转。→ 正确做法：任何音频播放 App 必须实现常驻底部 Mini Player（固定在 Tab Bar 上方，展示当前播放内容 + 暂停 + 下一首），用户在任意 Tab 均可控制播放（Spotify / Luminary 的行业标准）。

- **Annual 和 Monthly 计划视觉上平等展示，无推荐标记**：用户难以判断哪个方案更划算，犹豫后可能选 Monthly 或直接放弃。→ 正确做法：Annual 计划用高亮边框 + 填充背景 + 「最受欢迎」/ 「节省 X%」Badge 突出推荐，默认选中 Annual；Monthly 用轻描边作为备选（所有研究样本均如此，Breathwrk / Vinyls / Sky Guide 均将 Annual 作为视觉焦点）。
