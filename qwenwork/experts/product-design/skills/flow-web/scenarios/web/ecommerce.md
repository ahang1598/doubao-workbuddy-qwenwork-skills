# Scenario: 电商 / E-commerce

## Identity
**Platform**: Web
**Definition**: 面向消费者的商品浏览、选购、结账全链路产品——核心价值在于将"发现商品→决策购买→完成交易"的转化漏斗最大化。
**Canonical Examples**: ASOS、ZARA、Lulu and Georgia（服装电商）；LEGO、West Elm（品牌直营电商）；Farfetch（多品牌精品电商）
**Not this scenario if**:
- 主要任务是卖家/商家管理商品和订单（→ 用 SaaS 管理后台场景）
- 纯内容/订阅付费没有实物 SKU（→ 用营销网站场景）
- B2B 采购/询价流程（→ 用内部运营工具场景）

---

## User Profile

| 维度 | 内容 |
|---|---|
| 主要角色 | 消费者（End User / Shopper）|
| 核心目标 | 找到符合需求的商品并以最小摩擦完成购买 |
| 心智模型 | 消费级 App，期望"像 Amazon 一样顺畅"；对不熟悉的品牌有信任门槛 |
| 使用频率 | 低频（单次购买）到中频（季节性复购）；忠实用户高频 |
| 决策模式 | 探索发现（发现新品）+ 任务驱动（搜索特定商品）双模式混合 |

---

## IA Template

**导航模式**: Top Nav（固定顶部，含 Logo + 分类菜单 + 搜索 + 心愿单图标 + 购物袋角标）
> 理由：电商商品分类扁平且多，Sidebar 会占据宝贵的商品展示面积；Top Nav 是全行业共识，用户零学习成本。

**页面层级**: Home/Landing → Category (PLP) → Product Detail (PDP) → Cart → Checkout（多步骤）→ Order Confirmation

**权限角色**: 单一消费者角色；已登录用户可见已保存地址/支付方式/订单历史；游客可完成完整购买（Guest Checkout）

**数据密度**: 中（商品 Grid 卡片为主）+ 局部高（结账表单、订单详情）
> 说明：PLP 用 2-4 列 Grid 展示商品卡片；结账用结构化表单+右侧 Summary 摘要

**主要容器模式**:
- Cart Drawer（右侧滑出）：加购确认 + 预览购物车
- Filter Panel（侧边 Overlay 或底部 Sheet）：分面过滤
- 多步骤结账（Information → Shipping → Payment）：逐步收集交易信息
- 全屏 Order Confirmation：交易终态，情感化确认

### 导航骨架图（ASCII）

```
┌────────────────────────────────────────────────────────────────┐
│  Logo  [Women] [Men] [New In] [Sale]    [🔍] [♡] [🛍 2]       │  ← 固定 Top Nav（购物袋含数量角标）
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  ┌─ Filter Panel ─┐  ┌─────────────────────────────────────┐  │
│  │ CATEGORY       │  │  Sort: Recommended ▾   [Filters (2)]│  │  ← PLP
│  │ SIZE           │  │  ┌───┐ ┌───┐ ┌───┐ ┌───┐           │  │
│  │ COLOR          │  │  │   │ │   │ │   │ │   │           │  │
│  │ PRICE ──●────  │  │  └───┘ └───┘ └───┘ └───┘           │  │
│  │ BRAND          │  │  ┌───┐ ┌───┐ ┌───┐ ┌───┐           │  │
│  │                │  │  │   │ │   │ │   │ │   │           │  │
│  │ [View 83 Results]  └─────────────────────────────────────┘  │
│  └────────────────┘                                           │
│                                                                │
├────────────────────────────────────────────────────────────────┤
│  Product Detail Page (PDP)                                     │
│  ┌──────────────────┐  ┌──────────────────────────────────┐   │
│  │  [大图 Hero]     │  │ Brand / Product Name             │   │
│  │  [缩略图导览]    │  │ $129.00                          │   │
│  │                  │  │ Color: ● ● ● ○                   │   │
│  │                  │  │ Size: [XS][S][M̲][L][XL]          │   │
│  │                  │  │ ⚠ Only 2 left                    │   │
│  │                  │  │ [  Add to Bag  ] [♡ Wishlist]    │   │
│  └──────────────────┘  └──────────────────────────────────┘   │
│                                                                │
├────────────────────────────────────────────────────────────────┤
│  Checkout（Stripped Header: Logo + 🔒 + Return to Cart）       │
│  Breadcrumb: Cart > Information > Shipping > Payment           │
│  ┌──────────────────────────────────┐  ┌─────────────────┐    │
│  │ [Express: Shop Pay][PayPal][APay]│  │ Order Summary   │    │
│  │──────────────────────────────────│  │ ┌──┐ Item 1 $79 │    │
│  │ Contact:  email@...              │  │ └──┘ Item 2 $50 │    │
│  │ Ship To:  [地址表单]             │  │ Subtotal  $129  │    │
│  │           地址自动填充建议下拉   │  │ Shipping  TBD   │    │
│  │           内联错误高亮           │  │ Tax       TBD   │    │
│  │ [Continue to Shipping ─────────►]│  │ Total     $129  │    │
│  └──────────────────────────────────┘  └─────────────────┘    │
│                      (Payment 步骤类似，右侧 Summary 持久)     │
├────────────────────────────────────────────────────────────────┤
│  Order Confirmation                                            │
│          ✓ Order Confirmed! Thank you, Alex!                   │
│          Order #EC-2847-X                                      │
│          📧 Confirmation sent to email@example.com            │
│          [○]──[●]──[○]──[○]  Reviewed / Paid / Shipped / ETA  │
│          [ Continue Shopping ]                                 │
└────────────────────────────────────────────────────────────────┘
```

---

#### 图 2：关键状态对比图（Key State Variations）

```
左：PLP 正常态（有商品）                 右：PLP 空状态（过滤后零结果）

┌───────────────────────────────┐  ┌───────────────────────────────┐
│ Sort: Recommended ▾           │  │ Sort: Recommended ▾           │
│ [Blue ×][Size M ×] [Clear All]│  │ [Blue ×][Size M ×][$0-$100 ×] │
│ Showing 83 results            │  │ [Clear All]                   │
├───────────────────────────────┤  │ 0 results found               │
│ ┌────┐ ┌────┐ ┌────┐ ┌────┐  │  ├───────────────────────────────┤
│ │ 商 │ │ 商 │ │ 商 │ │ 商 │  │  │                               │
│ │ 品 │ │ 品 │ │ 品 │ │ 品 │  │  │      [空态插图 / Icon]        │
│ └────┘ └────┘ └────┘ └────┘  │  │                               │
│ ┌────┐ ┌────┐ ┌────┐ ┌────┐  │  │  No results found             │
│ │ 商 │ │ 商 │ │ 商 │ │ 商 │  │  │  for your filters.            │
│ │ 品 │ │ 品 │ │ 品 │ │ 品 │  │  │                               │
│ └────┘ └────┘ └────┘ └────┘  │  │  [Adjust Filters]             │
│  ··· （更多商品 Grid）        │  │                               │
└───────────────────────────────┘  │  You might also like:         │
                                   │  ┌────┐ ┌────┐ ┌────┐        │
                                   │  │    │ │    │ │    │        │
                                   │  └────┘ └────┘ └────┘        │
                                   └───────────────────────────────┘
```

---

#### 图 3：覆层层级图（Overlay Hierarchy）

```
┌──────────────────────────────────────────────────────────────────────┐
│  Logo  [Women] [Men] [New In] [Sale]      [🔍][♡][🛍 2]              │ ← Top Nav（z-100）
├──────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────┐           ┌──────────────────────────────┐ │
│  │ ← Filter Panel（左） │           │      Cart Drawer（右）→     │ │
│  │  z-index: 200        │  主页面   │  z-index: 200               │ │
│  │  CATEGORY  [ ] [ ]  │  商品 Grid│  Added to bag ✓              │ │
│  │  SIZE      [ ] [ ]  │  ┌──┐┌──┐ │  ┌──┐ Item 1  Blue/M  $79  │ │
│  │  COLOR     ● ○ ○    │  │  ││  │ │  Subtotal  $129              │ │
│  │  PRICE  ──●──       │  └──┘└──┘ │  [  View My Bag  ]          │ │
│  │                      │           │  [ Continue Shopping ]       │ │
│  │  [View 83 Results]  │           └──────────────────────────────┘ │
│  └──────────────────────┘                                            │
│         ▲ 触发："All Filters"                 触发："Add to Bag" ▲  │
│         左侧滑入，背景 Dim                     右侧滑入，背景 Dim    │
│                                                                      │
│              ┌────────────────────────────────┐                      │
│              │    Size Selector Modal（中）    │ ← z-index: 300（最高）│
│              │    Please select a size        │                      │
│              │    [XS][S][ M ][ L ][XL ⊗]    │                      │
│              │    ⚠ Only 2 left in stock      │                      │
│              │    [Cancel]  [Add to Bag]      │                      │
│              └────────────────────────────────┘                      │
│              ▲ 触发：点击"Add to Bag"未选尺码，居中弹出              │
└──────────────────────────────────────────────────────────────────────┘
  ┌──────────────────────────────────────────────────────┐
  │  ✓ Added to wishlist   [Undo]                         │  ← Toast（底部，z-400）
  └──────────────────────────────────────────────────────┘
  ▲ 触发：收藏 / 删购物车商品 / 优惠码应用，4-5 秒自动消失

触发关系说明:
- Filter Panel（左）: 点击"All Filters"触发，左侧滑入，z-200，背景 Dim；关闭留 Active Chips
- Cart Drawer（右）: 点击"Add to Bag"或购物袋图标触发，右侧滑入，z-200，背景 Dim
- Size Modal（中）: 未选尺码点击"Add to Bag"触发，居中弹出，z-300（高于 Filter/Cart）
- Toast（底）: 收藏成功 / 商品删除 Undo / 优惠码应用触发，z-400，自动消失
```

---

## 该场景独有的 IA/UX 决策

> 以下 5 条记录电商场景与其他 Web 场景（SaaS、AI 产品、营销网站）的本质 IA/UX 差异。

1. **商品变体前置门控（Pre-Cart Variant Selection）**：尺码/颜色/规格必须在 Add to Cart 之前完成选择，影响 SKU 和库存。Add to Bag CTA 在未选完时必须禁用或强制触发选择器——这是电商独有的"决策门控"模式。SaaS 选 Plan 选项固定，AI 产品无此概念。

2. **运费延迟显示（Deferred Shipping Cost Reveal）**：运费依赖收货地址（跨境/国内/快递/标准）无法在 Cart 阶段确定，Cart 和 Information 步骤均显示"Calculated at next step"，只有地址+运输方式双重确认后才显示最终 Total。这是电商独有的"价格不透明期"，需通过持久 Order Summary 右栏降低焦虑。

3. **Order Summary 右侧全程持久（Persistent Order Rail）**：结账跨 4-6 步，所有主流电商均将 Order Summary（含商品明细/小计/运费/税/Total）固定于右侧，不随步骤切换消失。购物车可有 10+ SKU 和多种优惠叠加，这种复杂性要求始终可见的明细——SaaS 结账通常只有"Plan: Pro $49/mo"一行，不需要此 pattern。

4. **双路径并行结账（Express vs Stepwise Checkout）**：Cart 和 Checkout 入口同时提供两条路径：① Shop Pay / PayPal / Apple Pay 一键跳过全部表单；② 传统分步表单（Contact→Shipping→Payment）。这种"两叉口"设计服务回头客（已有支付绑定）和新用户（手动填写）的混合受众，在 SaaS 中不存在。

5. **Cart Drawer 兼做再营销平面（Add-to-Cart as Sales Surface）**：加购成功后，Cart Drawer 同时承担三角色：确认反馈 + 购物清单预览 + "Complete the Look"交叉销售推荐。这是电商特有的"确认=再营销"机制——SaaS 成功态是跳 Dashboard，AI 产品是显示结果，均无需在确认时做交叉销售。

---

## Canonical Flows

> 以下 flow 基于对真实产品的横向分析抽象而来，代表该场景的高频用户任务。

### Flow 1: Browse and Add to Cart

**在此场景的特殊性**: 电商的浏览→加购是反复循环的非线性过程——用户可能多次进出 PDP、多次加购不同商品。Cart Drawer（右侧滑出，非页面跳转）是维持"浏览上下文"的核心 IA 决策，使用户加购后可立即继续浏览。变体选择（尺码/颜色）是加购门控，SaaS/AI 场景无此概念。

**前置条件**: 无（任何访客均可进入，无需登录）
**若前置条件不满足**: N/A——浏览和加购对游客完全开放；仅 Wishlist 收藏需要登录，届时触发登录 Sheet

**Entry**: 用户点击顶部分类导航（Women / New In / Sale）或在搜索框输入关键词

**Screens**:

```
Screen 1: Product Listing Page (PLP)
  主操作: 浏览商品 Grid，点击商品进入详情
  关键组件:
    - 顶部 Category Tabs / Horizontal Chips + Sort By 下拉
    - "All Filters"按钮（含已选过滤数量角标）
    - 商品 Grid（2-4 列）：图片 / 名称 / 价格 / 颜色 Swatch
    - 每卡心形 Wishlist 图标（未登录触发登录 Sheet）
    - 左侧（桌面）Accordion Filter 面板：分类/尺寸/颜色/价格/品牌
    - Filter 面板底部固定："View N Results"按钮（实时更新计数）
  → 点击商品卡片: Screen 2
  → 点击 Filter: Filter Overlay 展开（留在当前页）
  → 点击 Wishlist: 收藏成功 Toast（留在当前页）

Screen 2: Product Detail Page (PDP)
  主操作: 选择变体（尺码/颜色）→ Add to Bag
  关键组件:
    - 左侧: 大图 Hero + 垂直 Thumbnail 导览（Zoom on Hover）
    - 右侧: 品牌名 / 商品名 / 价格
    - 颜色 Swatch 行（选中态高亮 + 颜色名称）
    - 尺码 Grid（售罄置灰 + 删除线；"Size Guide"链接）
    - 库存提醒 Badge："Only 2 left in stock"
    - Add to Bag 按钮（未选尺码: 禁用态 or 点击触发 Size Selector Modal）
    - Wishlist 次要按钮
    - 商品详情 Accordion（Description / Materials / Shipping & Returns）
    - 下方: "Complete the Look" / "You May Also Like" 推荐 Grid
  → 选完变体 + 点击 Add to Bag: Screen 3（Cart Drawer 滑出）
  → 未选尺码点击 Add to Bag: Size Selector Modal 弹出（留在 Screen 2）
  → 点击推荐商品: 跳转至该商品 Screen 2

Screen 3: Cart Drawer（右侧滑入覆层）
  主操作: 确认加购 → 继续购物 or 前往购物袋
  关键组件:
    - 顶部确认文案:"Added to your bag ✓"
    - 已加商品卡：缩略图 / 名称 / 变体（颜色+尺码）/ 数量 / 价格
    - Subtotal（小计）
    - "View My Bag"主 CTA（实线大按钮）
    - "Continue Shopping"关闭 Drawer 链接
    - 背景页面 Dim（Overlay），不离开当前页
    - "You May Also Like"推荐（3-6 件，Complete the Look 逻辑）
  → 点击"View My Bag": → Cart Review 页（进入 Flow 2 Screen 1）
  → 点击"Continue Shopping" / 点击背景关闭: 返回 Screen 2
  → 点击推荐商品: 进入该商品 Screen 2
```

**Exit State**: 用户前往 Cart Review 开始结账，或关闭 Drawer 继续浏览
**Empty State**: Cart Drawer 在购物袋为空时显示"Your bag is empty"+ 推荐商品 Grid + "Start Shopping"CTA

---

### Flow 2: Complete Checkout

**在此场景的特殊性**: 电商结账需收集物理收货地址（不同于 SaaS 的账单信息）、展示运输方式选择（影响最终价格和到货时间）、支持多种支付工具（信用卡/PayPal/BNPL）。"运费延迟显示"和"Order Summary 右侧全程持久"是区别于其他场景的核心 IA 决策。Express Checkout 快速路径必须与分步表单并存。

**前置条件**: 购物车内有 ≥1 件商品且均有库存；用户已选择商品变体（尺码/颜色）
**若前置条件不满足**: Cart 为空 → 重定向至空购物袋页（"Your bag is empty"）；商品缺货 → Cart 行灰显 + 提示移除后才可结账

**Entry**: 从 Cart Drawer 点击"View My Bag"，或直接点击顶部购物袋图标

**Screens**:

```
Screen 1: Cart Review（购物袋总览）
  主操作: 检查商品 → 开始结账
  关键组件:
    - 商品列表行: 缩略图 / 名称 / 变体 / 数量步进器（Stepper）/ 删除 / Save for Later
    - 库存提示（"Only 1 left"）/ 缺货提示（灰显）
    - 优惠码 / 礼品卡输入框 + Apply 按钮（内联成功/失败反馈）
    - Order Summary 右侧面板:
        Subtotal  $179.00
        Shipping  Calculated at checkout
        Tax       Calculated at checkout
        ─────────────────────────────
        Estimated Total  $179.00
    - Express Checkout 区: [Shop Pay] [PayPal] [Apple Pay] [Google Pay]（分隔线 + "OR"）
    - 主 CTA: "Checkout Securely 🔒"（实线大按钮）
    - 下方: "You May Also Like"商品 Carousel
  → 点击主 CTA: Screen 2
  → 点击 Express 按钮: 跳至对应支付方 OAuth（Flow 在该方侧结束）
  → 修改数量: 小计实时更新
  → 删除商品: Undo Toast（5秒可恢复）
  → Save for Later: 移至 Wishlist（Cart 计数减少）

Screen 2: Checkout — Information（联系方式 + 收货地址）
  主操作: 填写收货地址
  关键组件:
    - Stripped Header: Logo + "Secure Checkout 🔒" + "Return to Cart"链接
    - 面包屑进度: Cart > Information > Shipping > Payment（当前步骤高亮）
    - Express Checkout 二次入口（折叠，可展开）
    - Contact 区: 已登录显示邮箱 + "Log out"；未登录显示邮箱输入框 + "Sign in"链接
    - Shipping Address: 国家下拉（首位） / First Name / Last Name / Address Line 1 / Line 2（可选）/ City / State / ZIP / Phone
    - 地址自动填充: 输入时弹出 Google Places 建议列表，点选后自动填充所有字段
    - 内联错误: 字段边框变红 + 字段下方红色错误文案（不等提交才显示）
    - "Save this information"勾选框（已登录用户显示）
    - 右侧持久 Order Summary: 商品列表 + Subtotal + Shipping "Calculated" + Total（此时 Total = Subtotal）
    - 底部: "Continue to Shipping"按钮
  → 地址填写完毕 + 点击 Continue: Screen 3
  → 字段验证失败: 内联错误高亮（不跳页，不清空已填内容）
  → 点击面包屑"Cart": 返回 Screen 1

Screen 3: Checkout — Shipping Method（首次显示运费）
  主操作: 选择运输方式（运费在此首次确定）
  关键组件:
    - Contact / Ship To 信息摘要区（单行显示 + "Change"链接）
    - Shipping Method Radio Group:
        ○ Standard Shipping (5-7 business days)  $6.95
        ● Express Shipping (2-3 business days)   $14.95
        ○ Free Standard (orders over $150)        FREE  ← 未达门槛则置灰提示
    - 选中后 Order Summary 实时更新运费和 Total
    - 右侧持久 Order Summary: 商品 + Subtotal + Shipping（已计算）+ Tax TBD + Total（已含运费）
    - 底部: "Continue to Payment"按钮
  → 选择运输方式 + 点击 Continue: Screen 4

Screen 4: Checkout — Payment（支付信息）
  主操作: 输入支付方式 → 确认下单
  关键组件:
    - Contact / Address / Shipping 三行摘要（均有"Change"链接）
    - 支付方式 Radio Tabs: 💳 Credit/Debit Card | PayPal | Afterpay | Klarna
    - 信用卡区（默认展开）:
        卡号（16位，实时品牌图标识别 Visa/MC/Amex）
        持卡人姓名
        有效期（MM/YY）+ CVV（含 Tooltip 说明）
    - 已登录用户: 已保存卡列表（末4位 + 有效期，单选）+ "Use different card"
    - Billing Address: "Same as shipping address ☑"勾选框（取消勾选展开新地址表单）
    - "Save payment info for next time"勾选框
    - 优惠码二次入口（已应用则显示绿色已应用状态）
    - 右侧持久 Order Summary: 商品 + Subtotal + Shipping + Tax（已计算）+ ─── + **Total $194.90**
    - 主 CTA: "Place Order — $194.90"（金额直接显示在按钮内）
    - 法律文本（小字）: "By placing your order you agree to our Terms of Service and Privacy Policy"
  → 点击"Place Order"+ 支付成功: Screen 5
  → 支付失败（卡被拒）: 内联错误 Banner（保留全部已填信息）+ "Try different payment method"CTA
  → 点击任意"Change": 返回对应步骤（地址 → Screen 2，运输 → Screen 3）

Screen 5: Order Confirmation
  主操作: 确认订单详情 → 继续购物 or 追踪订单
  关键组件:
    - 情感化大标题（品牌化）: "Order Confirmed! 🎉" / "Thank you, Alex!"
    - 订单号: #EC-2847-X（可复制）
    - 确认邮件发送提示: "Confirmation sent to alex@email.com"
    - 状态时间线（4节点）: ✓ Received → ✓ Payment Confirmed → ○ Shipped → ○ Delivered (Est. Apr 18-20)
    - 已购商品列表（商品缩略图 + 名称 + 变体 + 数量 + 价格）
    - 配送地址摘要
    - 支付方式摘要（末4位）+ 订单金额
    - "Track Your Order"次要按钮（跳至物流追踪）
    - "Continue Shopping"主 CTA（返回 PLP）
    - Newsletter 注册引导（可选 Banner，可关闭）
  → 点击"Continue Shopping": 返回 PLP
  → 点击"Track Your Order": 物流追踪页（Flow 结束）
```

**Exit State**: Order Confirmation 页，含订单号、预计到达时间、确认邮件通知
**Empty State**: 若用户直接访问 /checkout 而 Cart 为空，重定向至空购物袋页（"Your bag is empty"+ "Start Shopping"CTA + 推荐商品）

---

### Flow 3: Filter and Discover Products

**在此场景的特殊性**: 电商商品过滤是核心任务（找到合适 SKU），过滤维度多（尺寸/颜色/品牌/价格/库存/评分），且需实时更新结果计数（"View 83 Results"）防止用户陷入零结果死胡同。Active Filter Chips 必须常驻可见且可逐一移除。SaaS/AI 场景无此复杂的分面过滤需求。

**前置条件**: 无（任何访客均可进入 PLP 并使用过滤功能，无需登录）
**若前置条件不满足**: N/A——过滤属于纯客户端/无状态操作；若商品库为空则显示空 PLP 页

**Entry**: 用户在 PLP 点击"All Filters"按钮，或点击 Quick Filter Chip（Color / Size 等）

**Screens**:

```
Screen 1: Category Listing（未过滤）
  主操作: 发起过滤 or 使用 Quick Filter
  关键组件:
    - 顶部 Category Tabs 或 Horizontal Chips（Women/Men/Kids/Sale）
    - Sort By 下拉（推荐 / 最新 / 价格↑ / 价格↓ / 评分）
    - "All Filters"按钮（含已选数量角标，如"Filters (2)"）
    - Quick Filter Chips（Color / Size / Price 等高频维度，可直接点选应用）
    - 结果计数："Showing 1,240 results"
    - 商品 Grid（2-4 列）
  → 点击"All Filters": Screen 2
  → 点击 Quick Filter Chip: 直接应用并更新 Grid，计数实时刷新
  → 点击 Sort By: 排序选项 Dropdown

Screen 2: Filter Panel（Overlay / Sheet）
  主操作: 组合选择过滤条件
  关键组件:
    - 面板标题"All Filters" + Close ×
    - Accordion 分组（展开/折叠）:
        CATEGORY: 复选列表（Tops / Dresses / Jackets...）
        SIZE: 尺码 Grid（售罄置灰 + 删除线）
        COLOR: 色板方块 + 颜色名称（选中态: 勾号 + 高亮边框）
        PRICE: Range Slider（$0 — $500，含输入框精确输入）
        BRAND: 搜索框 + 品牌复选列表
        AVAILABILITY: "In Stock Only"切换开关
    - 已选条件: 复选框勾选高亮 + 可点 × 单独移除
    - 面板底部固定: "Clear All"链接 + "View [N] Results"主按钮（实时更新计数）
    - 桌面端: 左侧 Overlay 面板；移动端: 底部 Sheet
  → 点击"View Results": Screen 3
  → 点击"Clear All": 重置所有过滤，计数恢复总数
  → 点击 ×（单条）: 移除该条件，计数实时更新

Screen 3: Filtered Results（过滤后）
  主操作: 浏览过滤结果 → 点击商品进入 PDP
  关键组件:
    - 顶部 Active Filter Chips: 已选条件以 Pill 形式显示（"Blue ×""Size M ×"）+ "Clear All"
    - 结果计数更新:"Showing 83 results"
    - 商品 Grid 刷新（仅展示匹配商品）
    - （零结果态）: 插图 + "No results found" + "Clear Filters"CTA + "You Might Also Like"推荐区
  → 点击商品: 进入 PDP（Flow 1 Screen 2）
  → 点击 Active Chip ×: 移除该过滤，Grid 实时刷新
  → 点击"Clear All": 回到 Screen 1 无过滤状态
```

**Exit State**: 用户点击商品进入 PDP，进入 Flow 1
**Empty State**: 过滤结果为 0 时，显示空态插图 + "No results found for your filters" + "Adjust Filters"主 CTA + "You Might Also Like"推荐区（避免用户直接离开）

---

### Flow 4: 支付失败恢复

**在此场景的特殊性**: 支付失败是电商高频错误场景（卡被拒、余额不足、3DS 验证失败）。与其他错误场景不同，支付失败不能跳转新页面或清空表单——必须通过内联 Error Banner 在 Payment 页原地提示，保留所有已填信息（地址/运输方式/Order Summary），让用户可以最小摩擦换卡重试。SaaS 支付失败通常只影响账单设置，电商失败还涉及 SKU 库存锁定时限。

**前置条件**: 用户已完成 Information（地址）和 Shipping（运输方式）步骤，进入 Payment 页面并已填写支付卡信息；点击"Place Order"后后端返回支付失败（card declined / insufficient funds / 3DS required）
**若前置条件不满足**: 若用户尚未进入 Payment 步骤，则走 Flow 2 正常结账路径；若支付方式为 PayPal/Express 则由第三方处理错误（不走此 flow）

**Entry**: 用户在 Payment 页面点击"Place Order — $194.90"按钮，后端返回支付失败响应

**Screens**:

```
Screen 1: Payment → 支付处理中（Loading State）
  视觉状态: "Place Order"按钮变为 Loading Spinner，禁用全表单，右侧 Order Summary 继续可见
  关键组件:
    - 按钮文案变为"Processing..."+ Spinner 动画
    - 全页表单字段禁用（防止用户在处理中修改）
    - Order Summary 持续可见（商品 + 金额不变）
  → 支付成功: 直接跳至 Screen 4（Order Confirmation）
  → 支付失败（后端返回错误）: → Screen 2

Screen 2: Payment → 内联错误态（Card Declined）
  视觉状态: 表单恢复可编辑；顶部出现红色 Error Banner；卡号字段边框高亮红色
  关键组件:
    - 红色 Error Banner（表单顶部）:
        ⚠ Your payment was declined.
        Please check your card details or try a different payment method.
    - 卡号/CVV 字段红色边框高亮（提示填写位置）
    - 已保存卡列表（若已登录）高亮"Try different card"链接
    - 支付方式 Tab 仍可切换（PayPal / Afterpay 作为替代入口）
    - Order Summary 右侧持续可见（商品明细 + 金额不变，无需重新确认）
    - "Place Order"按钮恢复可点击状态
    - Contact / Address / Shipping 摘要行仍显示（含"Change"链接，无需重填）
  → 修改卡号重试: → Screen 3
  → 切换至 PayPal Tab: 跳至 PayPal OAuth（Flow 在该方侧结束）
  → 点击已保存卡"Switch": → Screen 3

Screen 3: Payment → 换卡 / 重新填写
  视觉状态: Error Banner 消失（用户已开始修改）；字段恢复正常边框
  关键组件:
    - Error Banner 消失（检测到用户开始编辑即清除）
    - 新卡号输入框（实时卡品牌图标识别）
    - CVV / 有效期重新填写
    - "Save this card"勾选框
    - Order Summary 持续可见（金额与步骤 2 完全一致）
    - "Place Order — $194.90"按钮（再次可点击）
  → 点击"Place Order"+ 支付成功: → Screen 4
  → 再次支付失败: 返回 Screen 2（Error Banner 再次出现，提示可联系支持）

Screen 4: Order Confirmation（支付成功）
  视觉状态: 与 Flow 2 Screen 5 完全一致
  关键组件:
    - "Order Confirmed! 🎉 Thank you, Alex!"
    - 新订单号（与之前失败尝试无关联）
    - 确认邮件提示
    - 状态时间线（Received → Paid → Shipped → Delivered）
    - "Continue Shopping"主 CTA
```

**Exit State**:

- 成功 → Order Confirmation 页（含新订单号和预计到达时间）
- 再次失败 → 保持 Screen 2 内联错误，新增"Contact Support"链接入口
- 取消 → 用户点击面包屑"Cart"退回购物袋（订单未创建，商品库存锁定自动释放）

**Empty State**: N/A（此 flow 无空状态，失败态即为"错误状态"）

---

## Component Kit

按使用频率排序：

| 功能概念 | 具体用途 |
|---|---|
| 内容卡片 | 商品 Grid 卡片（图片 + 名称 + 价格 + Swatch）|
| 状态标签 | 库存提醒（"Only 2 left"）/ 促销标签（"Sale"）/ 过滤数量角标 |
| 侧边面板/抽屉 | Cart Drawer（右侧加购确认）/ Filter Panel（移动端底部）|
| 可折叠列表 | Filter Panel 分组 / 商品详情（Description / Materials / Returns）|
| 单选组 | 运输方式选择 / 支付方式切换 |
| 操作按钮（自建数量步进器）| 购物车数量增减（+/−）|
| 分步向导步骤指示 | 结账步骤进度（Cart > Info > Shipping > Payment）|
| 选择下拉（搜索模式）| 地址自动填充（Google Places 建议列表）|
| 标签页切换 | Cart 内"Cart / Wishlist"/ Checkout 支付方式切换 |
| 分隔线 | Express Checkout 区 OR 分隔线 |
| 操作通知（Toast）| 加购成功确认 / 删除商品 Undo / 优惠码应用成功 |
| 模态对话框 | 尺码选择强制 Modal / 地址验证提示 / 登录要求 |
| 加载骨架屏 | 商品 Grid 加载占位 / 推荐 Carousel 加载 |
| 互斥/多选按钮组 | 颜色 Swatch 选择 / 尺码 Grid 选择 |
| 范围滑块 | 价格区间过滤 Range Slider |

---

## Anti-Patterns

> 该场景中真实存在的常见设计错误，基于研究观察。

- **强制注册才能结账（Forced Account Creation）**: 要求用户注册账号才能购买，导致大量放弃 → 正确做法：始终提供 Guest Checkout，购买成功后提示"注册即可追踪订单"作为软引导。

- **运费在最后一步才显示（Late Shipping Surprise）**: 在支付页才显示运费导致用户反感放弃 → 正确做法：Cart 页明确显示"Calculated at checkout"并在 Shipping 步骤第一时间显示运费，给用户决策机会。

- **加购后跳转至 Cart 页（Full-page Cart Redirect）**: 每次加购都跳转至 Cart 页面，打断浏览流 → 正确做法：使用 Cart Drawer 或 Toast 确认，保持用户在当前浏览上下文中。

- **过滤后零结果无引导（Empty Filter State Dead-end）**: 过滤条件过严导致零结果时只显示空态无出路 → 正确做法：零结果页提供"Adjust Filters" + "You Might Also Like"推荐区，防止用户直接离开。

- **Order Summary 只在最后一步显示（Hidden Running Total）**: 结账过程中不显示已购商品明细，用户填写表单时无法随时确认内容 → 正确做法：Order Summary 右侧全程持久，始终可见商品列表和动态更新的 Total。

- **尺码缺货不明确（Unclear Stock Status）**: 售罄尺码不置灰或不标注，用户加购后才发现缺货 → 正确做法：尺码 Grid 中售罄态使用删除线 + 置灰，PDP 右侧显示库存紧张提示（"Only 2 left"）。
