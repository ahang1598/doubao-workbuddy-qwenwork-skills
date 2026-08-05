# Scenario: Mobile Marketplace（电商 & 本地生活）

> **研究来源**：基于对 ASOS、SSENSE、On、TikTok Shop、Klarna、Target、Drinkit 等 7 个真实 iOS 产品 flow 和页面的横向分析抽象，不代表任何单一产品的具体实现。

---

## Identity

**Platform**: Mobile (H5 / React Native)
**Definition**: 以商品浏览、购物车管理和在线支付为核心的移动端购物应用，用户通过商品目录浏览、筛选、查看详情，加入购物车后完成地址填写和支付；本地生活子场景（外卖/咖啡）追加距离筛选和实时订单追踪。

**Canonical Examples**: ASOS iOS、SSENSE iOS、TikTok Shop iOS、On Running iOS、Drinkit（外卖子场景）

**Not this scenario if**:
- 以 C2C 二手交易为主（如 Depop、Poshmark，属于 Peer-to-Peer Marketplace）
- 以订阅式电商为主（如美妆盒子，重在订阅管理流程）
- 以 B2B 采购为主（企业采购/工厂批发，属于 web/saas-management 变体）
- 主要在 Web 端使用（改用 web/ecommerce）
- 以外卖平台为单独主业（DoorDash 类，本文件只覆盖食饮外卖作为子场景）

---

## User Profile

| 维度 | 内容 |
|---|---|
| **主要角色** | 休闲购物者（发现 + 冲动购买）/ 目标购物者（有明确商品需求）/ 外卖用户（即时配送，知道想要什么）|
| **核心目标** | 找到心仪商品 / 对比选择后下单 / 确认订单并追踪物流 |
| **心智模型** | 期待图片大而清晰（移动端看商品细节困难，图片是首要决策因素）；期待流畅的结账体验（支付宝/微信/Apple Pay 快速支付）；期待价格/尺码/库存透明（避免结账时惊喜）|
| **使用频率** | 中频（每周 2-5 次）：碎片时间逛商品 / 有购物计划时集中浏览 / 外卖场景为高频日常 |
| **决策模式** | 混合型：浏览时探索发现（刷 Feed，看推荐），有具体目标时搜索驱动（搜「Nike Air Max 90」）|
| **容错期望** | 加入购物车不等于购买（可随时修改/清空）；结账前可应用优惠码；已支付订单通常不可撤销（需明确说明退换货政策）|

---

## IA Template

**导航模式**: Tab Bar（底部 Tab Bar，4-5 项）

典型结构：
```
Tab 1: 首页 / Home    — 推荐商品 + 品牌 Banner + 个性化 Feed
Tab 2: 搜索 / Search  — 搜索框 + 分类导航 + 热门搜索
Tab 3: 购物车 / Cart  — 购物车列表（或 Bag / Basket，各产品叫法不同）
Tab 4: 收藏 / Saved   — 愿望清单（Wishlist / Favorites）
Tab 5: 我的 / Profile — 订单历史 + 账户信息 + 设置
```

On Running 模式（品牌直营 D2C，简化版）：
```
Tab 1: 首页           — 分类入口 + 新品推荐
Tab 2: 搜索/发现      — 商品目录（核心入口）
Tab 3: 购物车（Bag）  — 购物车
Tab 4: 我的           — 账户 + 订单 + 收藏
浮动 Menu CTA         — 主分类导航（悬浮圆形 Pill 按钮）
```

**页面层级**: 3 级
```
L1: Tab 根页（Home / Search / Cart / Profile）
L2: 商品列表（Category List）/ 商品详情（Product Detail）/ 购物车（Cart）
L3: 操作面板（尺码选择 Sheet / 地址填写页 / 支付方式选择 / 订单确认）
```

**权限流结构**（购物 App 权限较少）:
```
Location（附近门店 / 外卖配送范围）:
  → 首次点击「附近门店」/ 「立即点单」→ Pattern G 说明页 → 浏览器 Geolocation API / Expo Location 权限弹窗

Notifications（促销提醒 / 订单状态更新）:
  → 首次完成订单后 → 说明页（「订单状态、物流更新」）→ 浏览器 Notifications API / Expo Notifications 权限弹窗

Camera（AR 试穿 / 扫码）:
  → 首次使用 AR 功能 → 浏览器 MediaDevices API / Expo Camera 权限弹窗

生物识别（快速支付认证）:
  → 首次使用快捷支付（支付宝人脸 / 设备生物识别）→ 系统级认证弹窗（自动触发）
```

**数据密度**: 低-中（商品列表 2 列 Grid 低密度，购物车中密度，订单详情中密度）
- 核心视图：2列商品卡片 Grid（懒加载）+ 商品图片
- 辅助视图：`List`（购物车列表 / 订单历史）
- 不使用：多列 Table（数据库工具专属）

**主要容器模式**:
| 场景 | 容器 |
|---|---|
| 尺码/款式选择 | Bottom Sheet（中/大尺寸） |
| Sort & Filter | Bottom Sheet（大尺寸） |
| 购物车（简版） | Bottom Sheet（大尺寸）或独立 Tab |
| 地址填写 | Stack Push（全页面 Form）|
| 支付方式选择 | Bottom Sheet（中尺寸） |
| 优惠码输入 | 内联 TextInput（结账页 Form 内，无需独立页面）|
| 删除购物车商品 | Swipe Action（左滑删除，无需 Dialog）|
| 取消订单确认 | Dialog（「取消后无法恢复，确认取消？」）|
| 外卖快捷结账 | Bottom Sheet（大尺寸，Cart Review Modal）|

**导航骨架图（ASCII，ASOS 模式）**:
```
┌────────────────────────────────────┐
│  Status Bar（时间 / 信号 / 电量）    │
├────────────────────────────────────┤
│  [☰] [ASOS logo       ] [🔍] [🛍2]│  ← 顶部导航
├────────────────────────────────────┤
│  [Women] [Men] [Beauty] [Sale]     │  ← 分类 Chips（横向可滚动）
│                                    │
│  ┌────────┐  ┌────────┐            │
│  │ [图片] │  │ [图片] │  ← 2列商品 Grid
│  │ Product│  │ Product│
│  │ $89.99 │  │ $45.00 │
│  │  [♥]  │  │  [♥]  │
│  └────────┘  └────────┘
│  ┌────────┐  ┌────────┐
│  │ [图片] │  │ [图片] │
│  │ Product│  │ Product│
│  │ $62.00 │  │ $28.50 │
│  └────────┘  └────────┘
│                                    │
├───┬────┬──────┬──────┬─────────────┤
│ 🏠 │ 🔍 │ 🛍(2)│  ♥   │  👤          │  ← TabBar
└───┴────┴──────┴──────┴─────────────┘
```

---

## 该场景独有的 IA/UX 决策

1. **结账必须优先呈现快捷支付，将多步表单降至最少操作** — 移动端电商平台最大的转化优势是快捷支付（支付宝免密支付 / Apple Pay / 微信支付）——标准结账（ASOS flow 2824，33屏）需经历地址输入 / 卡号输入 / CVC / 确认等多步表单，快捷支付将整个流程压缩为「单击支付按钮 → 生物识别 → 完成」。移动端原生 App 必须将快捷支付按钮置于 CTA 区域最显眼位置，作为主付款方式，信用卡/其他方式作为次选——Web 端通常无法集成到同等深度，这是移动端电商的核心留存优势（On flow 9601 / SSENSE flow 7108 均将快捷支付作为首选支付入口）。

2. **商品图片使用全屏横向翻页 Carousel，不可用缩略图点击切换** — 移动端电商商品详情的图片浏览是手势驱动的——用户习惯左右滑动浏览多张商品图，对应 Carousel/Swiper 全宽展示（附底部页面指示点），而非 Web 端的「主图 + 下方缩略图行」点击切换模式。全宽横滑让每张图占满屏幕，最大化商品展示效果，同时触控面积大（整个屏幕均可滑动），误触概率极低——On（flow 9590）的 Product Detail 和 SSENSE 均采用此横滑图片浏览模式，是移动端电商与 Web 端图片浏览体验最显著的 UX 差异。

3. **尺码 / 规格选择用中尺寸 Bottom Sheet 展示，不可用内联 Picker 或跳转新页** — 商品加购的关键阻力是尺码/颜色选择——内联 Picker（Dropdown）在移动端点击目标小且布局紧张；跳转新页会让用户离开商品详情上下文，降低「此刻加购」的冲动转化率。正确做法是点击「选择尺码」触发中尺寸 Bottom Sheet 从底部弹出，在商品详情仍可见的情况下完成规格确认再加入购物车——ASOS（flow 2821）展示了「Product Detail → Size Sheet → 加购成功」的完整三步，保持商品图与规格选择的视觉连续性，是行业共识（On / SSENSE 均用 Sheet 或 Modal 处理规格选择）。

4. **筛选 / 排序必须用大尺寸 Bottom Sheet 叠于商品列表之上，筛选应用后立即预览结果数量** — Web 电商的筛选通常是侧边栏或独立筛选页（用户离开商品列表）；移动端电商用大尺寸 Bottom Sheet 让筛选面板从底部弹出，商品列表仍在背景中隐约可见——关键 UX 原则是：修改筛选条件时，页面顶部实时显示「符合条件的商品数量」（如「查看 238 件商品」），让用户在确认前了解结果规模，避免应用筛选后发现空状态的挫败感（ASOS Filter Sheet 是此模式的行业参照）。筛选 Sheet 关闭后商品列表即时更新，保持连续浏览心流。

5. **外卖 / 本地即时消费必须使用常驻购物车浮层 + Slide-to-Pay，不可用传统多步结账页** — F&B / 本地即时消费（Drinkit，flow 11012）与标准电商的根本差异在于时间压力和高频复购——用户下单外卖时不需要「地址确认 → 支付方式 → 订单摘要 → 确认」的完整结账 Wizard，需要的是「加购 → 一键支付」的最短路径。正确做法是 Safe Area 内常驻购物车摘要栏（显示总价 + 商品数量），用 Slide-to-Pay 手势（拖动滑块）替代「立即支付」按钮——滑动手势需要有意识操作，防止误触，同时比 Dialog 确认更流畅（Drinkit flow 11012 是此场景的行业参照）。

---

## Canonical Flows

> 以下 flow 基于 7 个真实产品样本横向分析抽象。括号内标注「行业共识」表示 3 个以上产品采用相同模式。

---

### Flow 1: Browse & Discover Products（商品浏览 + 商品详情）

**在此场景的特殊性**: 移动端电商 App 的商品列表与 Web 端最大的区别是**2 列商品卡片 Grid**——所有研究样本（ASOS / SSENSE / On / Target）均采用 2 列等宽商品卡片网格（非 3 列或 1 列），每张卡片包含图片（主导）+ 品牌名 + 商品名 + 价格 + 心形收藏图标。**分类过滤 Chips** 在列表顶部横向排列（可滚动），On Running（flow 9592）完整记录了 4步过滤路径（All → Shoes → Running → Road），每步即时刷新列表。**Sort & Filter** 统一用大尺寸 Bottom Sheet 从底部弹出（ASOS / Instagram 均如此），而非独立筛选页面。**商品详情**的 Size/Variant 选择同样用中尺寸 Bottom Sheet 弹出（ASOS flow 2821 3 屏记录），而非跳转到独立选择页面——用户选完尺码直接返回商品详情页，不丢失浏览上下文。

**行业共识**：ASOS / On / SSENSE 均使用 2 列 Grid + 心形收藏直接在卡片上操作；Size 选择用 Bottom Sheet 而非独立页（ASOS flow 2821 确认）。

**Entry**: 首页推荐 → 点击分类 / 搜索框输入

```
Screen 1: 商品列表（Category Listing / Search Results）
  主操作: 浏览商品 / 筛选排序 / 点击商品
  关键组件:
    - NavBar（标题分类名或搜索词 + 右上角购物袋图标（带角标计数））
    - 过滤行（横向可滚动）:
        Chip("全部"，选中深色) / Chip("女款") / Chip("新品")...
        Button(排序，.bordered)（→ Sort Sheet）
        Button(过滤，.bordered)（→ Filter Sheet）
    - 2列商品 Grid（每格 ProductCard，懒加载）:
        每个 ProductCard:
          Image（商品主图，aspectRatio 3:4，cover）
          Button(♥ 收藏, borderless)（右上角绝对定位）
          Text(品牌名，caption，灰色）
          Text(商品名，footnote，粗体）
          Text(价格，caption，品牌色）
          [可选] Badge("NEW" / "SALE"，小徽章样式)
    - 下拉刷新（PullToRefresh）
  → 点击分类 Chip: 列表即时过滤更新
  → 点击排序按钮: 大尺寸 Bottom Sheet 弹出 Screen 1-A Sort Sheet
  → 点击商品卡片: Stack Push → Screen 2
  → 点击 ♥ 收藏: 心形填充（已收藏状态），触觉反馈

Screen 1-A: Sort & Filter Sheet
  触发条件: 点击「过滤/排序」按钮
  主操作: 选择排序方式 / 设置过滤条件
  关键组件:
    - Bottom Sheet（大尺寸）
    - 标题「排序」+ 「筛选」Tab 切换或分组 List
    - Sort 选项 List（单选）:
        「推荐」（默认）/ 「价格从低到高」/ 「价格从高到低」/ 「最新上架」
    - Filter 选项（折叠区块）:
        「尺码」（多选 Chip Grid）
        「颜色」（彩色圆形多选）
        「价格范围」（RangeSlider）
    - Button("应用过滤"，主要按钮样式)（全宽，底部固定）
    - Button("清除全部"，次要按钮样式)
  → 点击应用: Sheet 关闭，列表重新渲染

Screen 2: 商品详情（Product Detail）
  主操作: 查看商品信息 → 选择尺码 / 颜色 → 加入购物车
  关键组件:
    - 透明叠加图片的顶部导航栏
    - Carousel/Swiper（横向全宽图片轮播 + 页码指示点）
    - 商品信息区:
        Text(品牌名，caption，灰色）
        Text(商品名，title，粗体）
        Text(价格，title，品牌色）
        [可选] Text("原价 $XX.XX"，caption，删除线，灰色)（折扣展示）
    - 颜色选择（圆形色块横排，单选）
    - 尺码入口（「选择尺码 ▾」，→ Screen 2-A Size Sheet）
    - 商品描述（可展开折叠区块）
    - 评分区: 星级 + 评分数 + 「查看全部评论」链接
    - 底部固定操作区（Safe Area 内）:
        Button("加入购物车"，主要按钮样式)（全宽，已选尺码时激活）
        Button(♥ 收藏，次要按钮样式)（与加购并排）
  → 点击「选择尺码」: 中尺寸 Bottom Sheet 弹出 Screen 2-A
  → 点击「加入购物车」（已选尺码）: Toast Banner「已加入购物车」+ 购物袋图标计数 +1
  → 点击「加入购物车」（未选尺码）: 自动弹出 Screen 2-A

Screen 2-A: 尺码选择（Size Selector Sheet）
  触发条件: 点击「选择尺码」或直接点「加入购物车」未选尺码时
  主操作: 选择尺码 → 点击「加入购物车」
  关键组件:
    - Bottom Sheet（中尺寸）
    - 商品缩略图 + 名称 + 价格（Sheet 顶部 Header）
    - 尺码 Chip Grid（3列或横向排列）:
        每个 Chip: Text（尺码，S/M/L/XL 或 38/39/40）
        禁用态 + 灰色斜线（售罄尺码）
        选中状态: 深色填充
    - Button("加入购物车"，主要按钮样式)（全宽，未选中时禁用）
  → 选中尺码 + 点击「加入购物车」: Sheet 关闭 + Toast Banner 确认
```

**Exit State**:
- ✅ 加购成功：Toast「已加入购物车」（3 秒后自动消失）+ Tab Bar 购物车角标计数 +1
- ⚠️ 商品售罄（该尺码）：尺码 Chip 显示灰色斜线 + 「暂时售罄」提示 + 「通知我补货」CTA
- 空状态（搜索无结果）：Empty State「未找到匹配商品」+ 「查看热门推荐」CTA

---

### Flow 2: Cart Review & Checkout（购物车 + 完整结账）

**在此场景的特殊性**: 移动端电商的结账流程与 Web 端最大的差异是**快捷支付的主导地位**——所有研究样本（ASOS flow 2824 / On flow 9601 / SSENSE flow 7108）均将快捷支付作为首要展示的支付方式（置于支付方式列表最顶部），快捷支付一键完成无需填写地址和卡号，极大简化结账步骤。**地址自动补全**（On flow 9601 完整展示 6 步：输入 → 建议列表 → 自动填充城市/邮编）是移动端减少输入摩擦的关键设计，触摸输入比桌面端更需要此功能。**优惠码内联验证**（On flow 9604：loading 状态 + 无效提示 + 总价更新）是结账页常见复杂状态，需 3 种展示：输入中 / loading / success 或 error。**「结账多步」统一用 Stack Push 全页面**（而非 Sheet Wizard），确保用户可以通过返回按钮逐步回退修改。

**行业共识**：ASOS（33 屏）/ SSENSE（16 屏）/ On（11 屏）均使用「Cart → Checkout → 地址 → 配送方式 → 支付 → 确认」6 段式 Stack 流程；快捷支付置于支付方式顶部是行业共识。

**Entry**: Tab Bar 购物车 Tab → 点击「前往结账」

```
Screen 1: 购物车（Cart / Bag）
  主操作: 查看已加购商品 / 修改数量 / 去结账
  关键组件:
    - NavBar（标题「购物车（3）」，带商品数量）
    - List（购物车商品列表）:
        每行: Image（商品缩略图，60×80pt）+ 商品名 + 尺码/颜色 + 单价
              Stepper（数量 -/+ 控制）
              左滑操作: Button("删除"，红色危险操作）
    - 折叠区块「应用优惠码」:
        TextInput("输入优惠码") + Button("应用")
    - 价格汇总（底部固定）:
        Row(「小计」, Text(金额))
        Row(「运费」, Text("免运费 / $X.XX"))
        Divider
        Row(「合计」, Text(总价，title，粗体))
    - Button("前往结账"，主要按钮样式)（全宽）
  → 点击「前往结账」: Stack Push → Screen 2
  → 商品数量归零（Stepper 减至 0）: 自动从 List 移除（带动画）

Screen 2: 结账 Review 页（Checkout Overview）
  主操作: 填写/确认收货地址 + 选择支付方式 → 下单
  关键组件:
    - NavBar（标题「结账」）
    - 商品摘要（折叠，顶部区块）:
        商品缩略图行 + 商品总数 + 小计
    - Section「配送地址」:
        Button("添加地址 +"，次要按钮样式)（无地址时）
        或 Row(已填地址摘要 + 「修改」链接)
      → 点击: Stack Push → Screen 3 地址填写
    - Section「配送方式」:
        List（标准配送 3-5 日 / 加急配送 1-2 日 + 各自费用，单选）
    - Section「支付方式」:
        Button("快捷支付"，主要按钮样式)（置顶优先，如 Apple Pay / 支付宝 / 微信）
        List（信用卡尾号 / 添加新卡 / PayPal...）
    - Section「优惠码」:
        TextInput + Button("应用")（内联，loading/error/success 三态）
    - 价格汇总（小计 + 运费 + 折扣 + 税 = 合计）
    - Button("确认下单"，主要按钮样式)（全宽，未填地址时禁用）
  → 点击快捷支付: 系统级支付弹窗 → Screen 5
  → 点击「确认下单」: 进入 Screen 4 支付处理

Screen 3: 地址填写（Shipping Address Form）
  触发条件: 点击「添加地址 +」
  主操作: 填写收货地址
  关键组件:
    - Stack Push（标题「添加地址」）
    - Form:
        TextInput("收件人姓名")
        TextInput("手机号码")
        TextInput("地址行 1")（输入时触发自动补全建议列表）
        自动补全 List（3-5 条建议，点击自动填充城市/省/邮编）
        TextInput("城市")（自动填充）
        TextInput("省/州")（自动填充）
        TextInput("邮政编码")（自动填充）
        Picker("国家/地区")
    - Button("保存地址"，主要按钮样式)（全宽，Stack Pop 返回）
  → 地址验证失败（无街道号）: 内联错误红色提示文字

Screen 4: 支付确认（Order Review & Pay）
  主操作: 最终确认 → 发起支付
  关键组件:
    - 完整订单摘要（商品列表 + 地址 + 配送方式 + 支付方式 + 最终金额）
    - Button("支付 $XX.XX"，主要按钮样式)（全宽，显示最终金额）
  → 点击「支付」: 触发支付 loading → Screen 5

Screen 5: 订单确认（Order Confirmation）
  主操作: 查看确认 / 继续购物
  关键组件:
    - 绿色大勾图标（成功状态）
    - Text("订单已确认！"，title，粗体）
    - Text(「订单号 #XXXXXX」，caption，可复制）
    - Text(「预计送达 [日期范围]」)
    - 订单商品缩略列表（2-3 条 + 「查看全部」链接）
    - Button("分享订单"）
    - Button("继续购物"，次要按钮样式)（返回首页 Home）
  Exit: Root Tab → Home，购物车清空
```

**Exit State**:
- ✅ 支付成功：订单确认页 + 邮件/通知 + 购物车清空
- ❌ 支付失败（卡号无效）：内联错误提示 + Button("换一种支付方式") + 返回修改（SSENSE / On 均展示了此错误态）
- ❌ 库存变动（结账时某商品售罄）：Banner 提示「X 件商品已售罄」+ 选项「移除并继续」/ 「返回购物车」

---

### Flow 3: Quick Order for Local / F&B（外卖 & 本地即时消费快速下单）

**在此场景的特殊性**: 外卖/本地即时消费子场景与常规电商最大的区别是**「浮动 Slide-to-Pay」结账控件**（Drinkit flow 11012 完整展示）——商品详情页底部有一个包含价格 + 支付方式图标的可上滑 Widget，将「查看商品信息 → 快速下单」压缩在同一个屏幕内，无需离开商品页进入独立购物车。**推荐加购（Upsell）** 在 Cart Review Sheet 内以横向 Carousel 形式展示（「再加一杯？」），比单独弹窗更自然。**小费选择**是外卖场景独有组件（Drinkit：0 / 15% / 20% / 25% 按钮组，自动计算金额）。**营业时间限制**（Drinkit flow 11007：店铺关闭时购物车底部 CTA 变为禁用「Not open yet」+ 红色 Banner 说明）是本地生活场景的独有状态，常规电商无此逻辑。

**行业共识**：Drinkit（flow 11012）展示了完整的 Float Checkout Widget → Cart Sheet → 支付 → 确认的 10 屏快速下单模式；营业状态（关闭/忙碌）影响 CTA 可用性是本地生活的行业标准。

**Entry**: 首页选择门店 → 点击某商品（App 内定位已授权）

```
Screen 1: 附近门店列表（Nearby Stores）
  触发条件: 首次使用时获取位置权限（Pattern G → 系统弹窗）
  主操作: 选择门店 / 查看营业状态
  关键组件:
    - SearchBar（搜索门店名或地址）
    - List（门店列表，下拉刷新）:
        每行:
          Image（门店图标 / 品牌 Logo）
          Text(门店名 + 地址)
          Text(距离：「500m」)
          Badge（「营业中」绿色 / 「9:00 开门」灰色 / 「忙碌」橙色）
    - Empty State（无附近门店：「周围没有门店」+ 「查看所有城市」CTA）
  → 点击营业中门店: Stack Push → Screen 2

Screen 2: 商品菜单 / 详情（Product Menu）
  主操作: 查看商品 → 选择规格 → 触发浮动结账
  关键组件:
    - ScrollView（商品列表，按分类分组：「咖啡」「特饮」「小食」）
    - 每个商品行: Image + 商品名 + 价格 + 描述
    - 浮动 Checkout Widget（Safe Area 底部，绝对定位）:
        Row(价格 Text + 支付方式图标 + 「上滑下单」提示箭头）
        可上拉 → 触发 Cart Review Sheet（Screen 3）
    - [商品详情] 点击商品行: 弹出商品详情 Bottom Sheet（尺寸/口味选择 + 备注 + 加入购物车）
  → 上拉 Checkout Widget: 大尺寸 Bottom Sheet 弹出 Screen 3

Screen 3: 购物车 Review Sheet（Cart Modal）
  主操作: 确认商品 / 加购推荐 / 选择小费 → 支付
  关键组件:
    - Bottom Sheet（大尺寸）
    - List（已加商品）:
        每行: 商品名 + 规格 + 单价 + Stepper(-/+)
    - 推荐加购区（Carousel）:
        小卡片（商品图 + 名 + 价格 + 「+」按钮）
    - 小费选择（4个按钮组: 「无」「15%」「20%」「25%」）
    - 价格汇总（小计 + 小费 = 合计）
    - 支付方式行（显示当前绑定卡，点击可切换）
    - Button("立即支付 $XX.XX"，主要按钮样式)（全宽）
    - [营业时间外] Button("Not open yet"，禁用态)（禁用态，红色 Banner 顶部说明）
  → 点击「立即支付」: 触发支付 → Screen 4

Screen 4: 订单确认（Order Received）
  关键组件:
    - 绿色大勾图标（成功状态）
    - Text("订单已收到！")
    - Text("预计 [X] 分钟后取餐 / 配送到达")
    - 订单号 + 商品列表摘要
    - Button("返回"，次要按钮样式)（返回门店首页）
```

**Exit State**:
- ✅ 下单成功：确认页 ETA + 订单号 + 通知（Notifications 已授权时）
- 🔒 店铺关闭：购物车 CTA 禁用 + 红色 Banner 告知营业时间
- ❌ 支付失败：错误提示 + Button("重试") + Button("更换支付方式")

---

### Flow 4: Order Tracking & Return Request（订单追踪 + 申请退换货）

**在此场景的特殊性**: 电商购后服务是移动端电商留存的核心环节——用户下单后的核心焦虑是「我的包裹在哪里」，而移动端的订单追踪与 Web 端最大的差别是**实时状态 Timeline**（而非跳转快递公司官网）。移动端标准模式是在订单详情页内嵌竖向 Timeline 组件（Processing → Packed → In Transit → Out for Delivery → Delivered），每个节点带时间戳，当前节点高亮（品牌主色圆点 + 加粗文字），已完成节点用灰色渐淡表示。**退换货**是仅次于追踪的高频购后操作——移动端退货流程必须在 App 内完成（不可跳转到 Web 端），标准步骤是：选择退货商品 → 选择原因（单选列表）→ 可选上传图片（仅部分品类要求）→ 确认退货方式（邮寄 / 就近门店）→ 生成退货码。PayPal（flow 7253）展示了通过邮件关联自动识别包裹、构建追踪视图的模式（9 屏），是「零手动输入追踪号」的行业最优路径。ASOS（flow 2824，33 屏结账）后续 My Orders 页面确认了「按状态分组的 SectionList」是订单列表的行业标准。

**行业共识**：ASOS / On / SSENSE 均在「Profile → My Orders」提供订单列表入口；所有主流移动电商 App 的订单追踪均内嵌 Timeline（不跳转快递官网）；退货原因选择统一用单选 Radio List，不用 Input 让用户自填。

**Entry**: Tab Bar → 「我的」→「我的订单」/ 订单确认通知点击进入

```
Screen 1: 我的订单列表（My Orders）
  主操作: 查看所有订单 / 按状态筛选
  关键组件:
    - NavBar（标题「我的订单」）
    - 状态 Tab 横排（可滑动）:
        Tab("全部") / Tab("处理中") / Tab("已发货") / Tab("已完成") / Tab("退款中")
    - SectionList（订单列表，按状态分组，或按时间倒序）:
        每行订单卡片:
          商品缩略图行（前 3 件横排，超出显示「+N 件」）
          Text(订单号 #XXXXXX, caption, 灰色)
          Text(下单日期)
          Badge(状态: 「已发货」绿色 / 「待付款」橙色 / 「退款处理中」蓝色)
          Text(订单总价, 粗体)
    - Empty State（无订单: 「暂无订单记录」+ Button("去购物")）
  → 点击订单卡片: Stack Push → Screen 2

Screen 2: 订单详情（Order Detail）
  主操作: 查看订单信息 + 追踪物流 + 发起售后
  关键组件:
    - NavBar（标题「订单详情」+ 右上角「联系客服」文字按钮）
    - 物流追踪 Timeline（竖向，核心组件）:
        节点行（从上到下）:
          ● 「已下单」— 时间戳（灰色，已完成）
          ● 「已打包」— 时间戳（灰色，已完成）
          ● ● 「运输中」— 时间戳（品牌色，当前节点，加粗）
          ○ 「派送中」— （空心，未到达，浅灰）
          ○ 「已送达」— （空心，未到达，浅灰）
        节点间用竖线连接（已完成段实线，未到达段虚线）
    - 快递信息行: 快递公司 + 运单号（可复制按钮）
    - Divider
    - 商品清单 Section:
        每行: Image（60pt）+ 商品名 + 尺码/颜色 + 数量 × 单价
    - 价格汇总 Section:
        小计 / 运费 / 折扣 / 合计
    - 收货地址 Section（收件人 + 地址摘要）
    - 底部操作区（Safe Area 内）:
        Button("申请退换货", 次要)（全宽，已发货或已完成状态时显示）
        Button("再次购买", 主色)（全宽，已完成状态时显示）
  → 点击「申请退换货」: Stack Push → Screen 3

Screen 3: 退换货申请（Return Form）
  主操作: 选择退货商品 + 选择原因 → 提交申请
  关键组件:
    - NavBar（标题「申请退换货」）
    - Section「选择商品」:
        CheckList（订单内商品，多选，每行: 缩略图 + 名称 + 尺码）
    - Section「退换原因」（选中商品后展开）:
        Radio List（单选）:
          「质量问题」/ 「尺码不符」/ 「与描述不符」/ 「不喜欢 / 改变主意」/ 「收到错误商品」
    - Section「上传图片（可选）」（质量问题时变为必填，其余可选）:
        ImagePicker Grid（最多 3 张，点击缩略图格子打开相册）
    - Section「退货方式」:
        Radio List（单选）:
          「快递寄回」（附上门取件说明）/ 「就近门店退货」（如有）
    - Button("提交申请", 主色)（全宽，商品和原因均选中时激活）
  → 点击「提交申请」: 加载中 → Screen 4

Screen 4: 申请成功（Return Confirmation）
  主操作: 查看退货凭证 / 后续步骤
  关键组件:
    - 绿色大勾图标
    - Text("退换货申请已提交！", title, 粗体)
    - Text(「退货单号 #RET-XXXXXX」，caption, 可复制)
    - 步骤说明（有序列表）:
        「1. 使用以下退货码打包商品」
        「2. 交给快递员 / 送至门店」
        「3. 我们收到商品后 3-5 个工作日退款」
    - 退货码区（大字，品牌色，带复制按钮）
    - Button("返回订单", 次要)（返回 Screen 1）
  Exit: 「我的订单」列表该订单状态更新为「退款处理中」
```

**Exit State**:

- ✅ 申请成功：退货码生成，订单状态变为「退款处理中」，邮件/推送通知用户
- ❌ 超过退货期限（如 30 天已过）：Button("申请退换货") 隐藏，替换为 Text("已超过退货期限")
- ❌ 提交失败（网络错误）：Toast「提交失败，请重试」+ Button("重试")，已填内容保留

---

## Mobile Component Kit

按使用频率排序（基于研究样本观察）：

| 优先级 | 组件（H5 antd-mobile）| 组件（RN Gluestack/RN）| 具体用途 |
|---|---|---|---|
| ★★★ | `Grid`（2列） | `FlatList`（numColumns=2） | 商品目录列表（核心展示，性能关键）|
| ★★★ | `Image` + `lazyload` | `Image` + `FastImage` | 商品图片（目录 / 详情 / 购物车缩略图）|
| ★★★ | `Swiper` / `Carousel` | `FlatList`（horizontal）+ 指示点 | 商品详情图片轮播（ImageCarousel）|
| ★★★ | `NavBar` + `StackNavigator` | `StackNavigator` | 结账多步 Wizard（Cart → Checkout → 地址 → 支付）|
| ★★★ | `Popup` / `ActionSheet` | `BottomSheet` | 尺码选择 / Sort&Filter / Cart Modal / 外卖快捷结账 |
| ★★★ | 支付宝 / 微信 / WebPay SDK | `react-native-payments` | 快捷支付 |
| ★★ | `List` | `FlatList` | 购物车列表 / 订单历史 / 门店列表 |
| ★★ | `SwipeAction` | `Swipeable` | 购物车左滑删除商品 |
| ★★ | `Stepper` | 自定义 Stepper 组件 | 商品数量加减控制 |
| ★★ | `SearchBar` | `SearchBar` | 商品搜索 / 门店搜索 |
| ★★ | `TabBar` | `BottomTabNavigator` | App 主导航（Home / Search / Cart / Profile）|
| ★★ | `Badge` | `Badge` | 购物车商品数量角标 |
| ★★ | 浏览器 Notifications API | `expo-notifications` | 订单状态更新推送权限 |
| ★ | 浏览器 Geolocation API | `expo-location` | 附近门店定位 / 外卖配送范围 |
| ★ | `Collapse` | `Accordion` | 商品描述折叠展开 / 优惠码输入区 |
| ★ | `ErrorBlock` | Empty State 自定义 | 搜索无结果 / 周围无门店空状态 |
| ★ | Web Share API | `react-native-share` | 分享订单确认 / 商品链接 |
| ★ | `Slider`（RangeSlider） | `@react-native-community/slider` | 价格范围过滤 |

---

## Anti-Patterns

基于研究样本中观察到的设计错误：

- **尺码/规格选择跳转到独立页面而非 Bottom Sheet**：用户点击「选择尺码」离开商品详情页，到达一个新页面，选完后再返回，上下文割裂、步骤多余。→ 正确做法：Size Selector 必须是中尺寸 Bottom Sheet 从底部弹出（ASOS flow 2821 验证），选完尺码后 Sheet 关闭，用户仍在商品详情页，直接点击「加入购物车」即可。

- **加购后立即自动跳转到购物车页**：用户正在浏览商品列表，加了一件商品后被强制跳到购物车页，中断了继续浏览的意图（通常是「连续加多件商品」场景）。→ 正确做法：加购成功只展示 Toast Banner（「已加入购物车，查看购物车 →」，3 秒后消失），用户留在商品详情页；购物车入口更新角标计数（SSENSE / ASOS / On 均如此）。

- **不提供快捷支付，仅支持信用卡填写**：移动端用户已习惯快捷支付（生物识别确认，无需填写卡号/地址），强制手填表单大幅增加结账摩擦，放弃率高。→ 正确做法：快捷支付必须作为首选支付方式展示在支付列表顶部，其余方式（信用卡/PayPal）作为备选（On / SSENSE / ASOS 均如此）。

- **地址填写无自动补全**：用户在移动端软键盘上逐字输入街道、城市、邮编，容易出错且体验极差。→ 正确做法：地址首行 TextInput 接入地址自动补全服务，展示建议列表，选中后自动填充城市/省/邮编（On flow 9601 完整展示了 6 步地址补全）。

- **Filter/Sort 用独立全页面而非 Bottom Sheet**：点击「筛选」跳转到新页面，用户失去商品列表上下文，设置完后需返回才能看到结果。→ 正确做法：Sort & Filter 统一用大尺寸 Bottom Sheet 从底部弹出，顶部固定「应用/清除」操作按钮，关闭 Sheet 立即看到过滤后的结果（ASOS / Instagram Shop 均如此）。

- **购物车商品删除使用 Dialog 二次确认**：购物车删除是低风险的可逆操作（随时可重新加购），用 Dialog 弹窗反而打断流程。→ 正确做法：Swipe Action 左滑直接显示红色「删除」按钮，单击删除（带撤销 Toast「已移除，撤销」），无需 Dialog 确认（ASOS / 常见电商模式）。

- **外卖 App 不区分营业状态**：店铺已关闭但用户仍可将商品加入购物车，结账时才发现「门店未营业」报错，浪费用户精力。→ 正确做法：门店列表行显示营业状态 Badge（营业中/关闭/忙碌）；关闭状态下购物车内的结账 CTA 置为禁用，顶部展示 Banner 说明「该门店 XX:XX 开始营业」（Drinkit flow 11007 完整展示了此逻辑）。

- **商品列表只有单列**：在 375pt 宽的手机屏幕上，单列列表每个商品卡片宽度过大，一屏内只能展示 2-3 件商品，浏览效率极低。→ 正确做法：商品目录统一使用 2 列 Grid（列间距 12pt，每卡图片比例 3:4），每屏可展示 4-6 件商品，图片仍足够清晰识别（ASOS / On / SSENSE / Target 均如此）。
