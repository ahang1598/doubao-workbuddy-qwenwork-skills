# Scenario: Real Estate（房产平台）

> **研究来源**：基于对 Trulia、Zillow、Rightmove、Apartments.com 等真实产品 flow 的横向分析抽象，不代表任何单一产品的具体实现。

---

## Identity

**Platform**: Web
**Definition**: Consumer-facing web platform for browsing, filtering, and evaluating property listings (sale or rental), with map-based search, photo galleries, and agent/landlord contact or tour booking flows.

**Canonical Examples**: Zillow（美国买房/租房）、Trulia（美国房产搜索）、Rightmove（英国房产）、Apartments.com（美国租房）

**Not this scenario if**: 产品是商业地产管理后台（改用 web/saas-management）；产品是短期度假租房（改用 web/ecommerce 变体）；产品是移动端原生 App（改用 ios/real-estate）；产品是纯房贷/金融服务（改用 web/fintech）。

---

## User Profile

| 维度 | 内容 |
|---|---|
| **主要角色** | House Hunter / Renter（购房者/租客，消费者端）；Agent / Landlord（房源发布方，通常在独立后台操作）|
| **核心目标** | 找到符合条件的房源 → 深入了解 → 安排看房或联系中介 |
| **心智模型** | 熟悉地图搜索（Google Maps）+ 电商浏览模式（图片主导的卡片列表）|
| **使用频率** | 中低频（买房季节性强，租房周期性强），每次会话较长（30~60 分钟）|
| **决策模式** | 探索驱动型：条件模糊 → 不断缩小 → 重点对比 → 联系；非即时决策 |
| **容错期望** | 中：筛选条件改变需即时反馈；联系/预约操作有明确确认才放心 |

---

## IA Template

**导航模式**: Top Nav（搜索栏突出 + Logo + 用户入口）+ 左侧 Filter Bar + 双视图切换（List + Map）

- **Top Nav**：Logo + 搜索框（位置/地址/邮编）+ 买房/租房切换 + 用户头像（收藏列表、搜索历史）
- **Filter Bar**：价格区间 / 卧室数 / 房屋类型 / 更多筛选（独立 More Filter Modal）
- **双视图**：List View（左侧 ~60% 卡片网格）+ Map View（右侧 ~40% 互动地图），默认双栏并存
- **底部状态栏**：结果数量（「找到 243 套房源」）+ 视图切换按钮（List Only / Map Only / Split）

**页面层级**: 3 级
```
L1: Search Results（搜索结果，双栏 List+Map）
L2: Property Detail（房源详情：图库 + 描述 + 周边 + 右侧 Tour Panel）
L3: Schedule Tour / Contact Agent（预约/联系，Modal 或 Detail 内 Drawer）
```

注：与电商不同，Real Estate 没有购物车概念；核心转化行为是「联系/预约」而非「加购结账」。

**权限角色结构**:
```
Visitor（未登录）  → 浏览列表 + 查看详情，无法收藏或直接联系（需注册）
Registered User → 收藏房源 + 联系中介 + 预约看房 + 查看联系电话
Agent / Owner   → 发布/管理房源（独立后台，不在本 scenario 范围内）
```

**数据密度**: 中
- 搜索结果：Card（图片主导，Price + Beds + Baths + Sqft + Address）
- 房源详情：半高密度（图库 + 关键指标 + 描述段落 + 周边信息表格）
- 不使用：复杂 Table 或多列数据表格

**主要容器模式**:
| 场景 | 容器 |
|---|---|
| 高级筛选（More Filters） | Modal（全屏或中等宽度，多分组筛选器）|
| 预约看房 | 详情页右侧内嵌 Panel 或 Sticky Sheet |
| 联系中介 | 详情页右侧 Contact Form（内嵌，不弹窗）|
| 贷款资格确认 | Modal（Qualification Check，联系后触发）|
| 图片浏览 | Lightbox（全屏覆盖，键盘导航）|
| 登录/注册 | Modal（非独立页面，保留当前浏览上下文）|

**导航骨架图（ASCII）**:
```
┌─────────────────────────────────────────────────────────────────┐
│  Logo  [🔍 City, neighborhood, ZIP code_______]  Buy│Rent  [☰▾]│
├─────────────────────────────────────────────────────────────────┤
│  Price ▾  Beds ▾  Home Type ▾  [More Filters]   243 results     │
├──────────────────────────────────┬──────────────────────────────┤
│  [Card] $850K  3bd 2ba 1,450sqft │                              │
│  123 Maple St, Austin TX         │         MAP VIEW             │
│  [Card] $920K  4bd 3ba 2,100sqft │   📍 📍    📍                │
│  456 Oak Ave, Austin TX          │      📍  📍                  │
│  [Card] $680K  2bd 2ba 980sqft   │         📍                   │
│  789 Pine Blvd, Austin TX        │   [selected pin highlighted] │
│  ────────────────────────────── │                              │
│  [Pagination: ← 1 2 3 →]        │                              │
└──────────────────────────────────┴──────────────────────────────┘
```

---

### 图 2：关键状态对比图（Key State Variations）

```
左：Property Detail 正常态（图库 + 右侧 Sticky Panel）  右：搜索无结果空状态（筛选过严）

┌────────────────────────────────────┐  ┌────────────────────────────────────┐
│ [图库主图 16:9]   [+2张缩略图]      │  │ Price▾  Beds▾  Type▾  [Filters]    │
│                    [查看全部 38张]  │  ├────────────────────────────────────┤
├──────────────────────┬─────────────┤  │                 │                  │
│ $850,000             │ 预约看房    │  │                 │     MAP VIEW     │
│ 3bd 2ba 1,450 sqft   │ ─────────  │  │                 │   (no pins)      │
│ 123 Maple St, TX     │ [In Person] │  │  🏠             │                  │
│ ─────────────────── │ [Video]     │  │  暂无符合条件的  │                  │
│ 描述文字...          │ 姓名 ___    │  │  房源            │                  │
│ [房屋信息] [学区]    │ 电话 ___    │  │                  │                  │
│ [周边地图]           │ [Schedule]  │  │ [扩大搜索范围]   │                  │
└──────────────────────┴─────────────┘  └────────────────────────────────────┘
```

---

### 图 3：覆层层级图（Overlay Hierarchy）

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Logo  [🔍 City, neighborhood, ZIP_____________]  Buy│Rent     [☰ ▾]     │ ← Top Nav（z-100）
├──────────────────────────────────────────────────────────────────────────┤
│  Price ▾  Beds ▾  Home Type ▾  [More Filters]                243 results │
├──────────────────────────────────────┬───────────────────────────────────┤
│  [Card] $850K  3bd  123 Maple St    │                                   │
│  [Card] $920K  4bd  456 Oak Ave     │          MAP VIEW                 │
│  [Card] $680K  2bd  789 Pine Blvd   │    📍 $850K   📍 $920K            │
│                                      │        📍 $680K                   │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  More Filters Modal（中）z-index: 300                             │   │
│  │  Price: ├──────●────────────┤ $200K – $1.2M                     │   │
│  │  Type:  ☑ House ☑ Condo ☐ Townhouse ☐ Multi-family              │   │
│  │  Must-have: ☐ Pool ☑ Garage ☐ A/C ☑ Pet-friendly                │   │
│  │  [Reset All]                         [Apply Filters (47)]        │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│    ▲ 触发: Filter Bar [More Filters] 按钮                                 │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  Photo Gallery Lightbox（全屏）z-index: 300                       │   │
│  │  Kitchen / Bedroom / Bathroom / Exterior          [12 / 38]  ✕  │   │
│  │  ┌────────────────────────────────────────────────────────────┐  │   │
│  │  │              [房间照片 全屏主图]                             │  │   │
│  │  └────────────────────────────────────────────────────────────┘  │   │
│  │  ←                [缩略图横向滚动条]                          →   │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│    ▲ 触发: Property Detail 图库图片点击 或 「查看全部 38 张照片」          │
│                                                                          │
│  ┌────────────────────────────────────┐                                  │
│  │  Share Property Modal（中）z-index:300│                               │
│  │  Share this home                   │                                  │
│  │  [email_________________________]  │                                  │
│  │  [Send email]                      │                                  │
│  │  ─── or ───                        │                                  │
│  │  [Copy link]  [WhatsApp] [FB]      │                                  │
│  │  [Cancel]                          │                                  │
│  └────────────────────────────────────┘                                  │
│    ▲ 触发: Property Detail [Share] 按钮（flow_id 6716）                   │
│                                                                          │
│  ┌────────────────────────────────────┐                                  │
│  │  Login Modal（中）z-index: 350      │                                  │
│  │  Sign in to save homes             │                                  │
│  │  [Email] [Password]  [Sign In]     │                                  │
│  │  New here? [Create account]        │                                  │
│  └────────────────────────────────────┘                                  │
│    ▲ 触发: 未登录用户点击 ♡ 收藏按钮                                      │
└──────────────────────────────────────────────────────────────────────────┘
  ┌──────────────────────────────────────────────────────┐
  │  ♡ Added to Saved Homes   [Undo]  [×]                │  ← Toast（z-500）
  └──────────────────────────────────────────────────────┘

触发关系说明:
- More Filters Modal（中）: Filter Bar [More Filters] 触发，z-300，含 Apply 计数（「47 results」实时更新）
- Photo Gallery Lightbox（全屏）: 详情页图片或「查看全部」触发，z-300，ESC 或 ✕ 关闭，滚动位置保留
- Share Property Modal（中）: 详情页 [Share] 按钮触发，z-300，支持邮件发送和链接复制
- Login Modal（中）: 未登录用户点击 ♡ 收藏触发，z-350，不阻断浏览，登录后自动完成收藏
- Toast（z-500）: 「Added to Saved Homes」/ 「Link copied」轻量反馈，含 Undo，3-5 秒消失
```

---

## 该场景独有的 IA/UX 决策

1. **List + Map 双栏是搜索结果的唯一合理布局** — 房产搜索本质是地理选择，地图不是辅助信息，而是与卡片列表同等重要的主视图。两者必须同屏并存（约 60% List + 40% Map），筛选条件改变时地图 Pin 和列表同步刷新，Pin 与卡片双向联动（点击 Pin 高亮对应卡片，hover 卡片高亮对应 Pin）。通用电商不需要这种布局约束，房产平台无法简化为单列列表。

2. **地图 Pin 价格标注是实时比价的主要工具** — 与电商不同，房产地图的 Pin 上直接标注价格（「$850K」），让用户在不读卡片的情况下通过地理位置判断价格分布。悬停 Pin 时弹出 MiniCard Preview（首图 + 价格 + 基本参数 + 「查看详情」链接），给用户足够信息决定是否值得点进去——这是 Real Estate 特有的「悬停决策」机制，E-commerce 没有对应概念。

3. **右侧 Sticky Panel 是转化设计的核心布局约束** — 用户在房源详情页花大量时间阅读描述、看图库、查学区——整个过程中「Schedule Tour / Contact Agent」CTA 必须始终可见（Sticky，跟随滚动固定在右侧）。这要求详情页全程维持左侧内容 + 右侧 Sticky Panel 的两栏格局，无法随内容收起。与 EdTech / SaaS 的 Sticky Sidebar 不同，房产 Panel 本身承载表单（联系信息 + 日期选择），不只是导航。

4. **图库是购房决策的主要信息媒介，需要专有的浏览模式** — 购房者通过照片做 70% 以上的初步判断（价格合适但图片差 → 放弃；价格偏高但图片好 → 进一步考虑）。图库必须支持：全屏 Lightbox 浏览（键盘 ← / → 导航）、照片总数计数（「第 12 张 / 共 38 张」）、房间分类导航（Kitchen / Bedroom / Bathroom / Exterior）、Virtual Tour 入口。E-commerce 的商品图片仅需简单 Carousel，房产图库是独立的沉浸体验层。

5. **贷款预审的交叉销售必须在确认后触发，而非阻断流程** — 「Get Pre-qualified」（贷款资格确认）这类交叉销售入口只能在 Tour 预约提交成功后出现（如 Trulia 的 Qualification Modal 在确认页后弹出），不能作为预约流程中的必填步骤。用户在发起预约时处于探索评估阶段，强制在确认前要求提供财务信息会大幅提高放弃率——这与 SaaS Onboarding（用户已决策，步骤越多越接受）的心理阶段完全不同。

---

## Canonical Flows

### Flow 1: 搜索 + 过滤房源（Search & Filter Listings）

**在此场景的特殊性**: 与 E-commerce 筛选不同，Real Estate 的搜索是地理位置优先（用户输入城市/邮编，不是关键词）；筛选条件改变必须即时刷新结果（地图 Pin 和列表同步更新），不需要「Apply」按钮；地图 Pin 是结果的另一种视图（不是辅助信息），点击 Pin 后右侧列表高亮对应卡片（双向联动）

**前置条件**: 无（匿名用户可访问搜索结果）；浏览器可加载地图（第三方地图 SDK，需网络）
**若前置条件不满足**: 筛选后无结果 → 空状态显示「暂无符合条件的房源」+ 「扩大搜索范围」CTA；地图加载失败 → 地图区域显示错误占位图 + 「切换到列表视图」；搜索词无法识别 → 搜索框下方 inline 提示「未找到该位置，请检查输入」

**Entry**: 用户在 Top Nav 搜索框输入城市名/地址/邮编后回车，或从首页热门区域卡片进入

**Screens**:
```
Screen 1: Search Results（双栏视图）
  主操作: 浏览房源列表，调整筛选条件
  关键组件:
    - Filter Bar: Select（Price Range）, Select（Beds/Baths）, ToggleGroup（Home Types）, Button（More Filters）
    - 左侧 Card Grid: PropertyCard（首图 + 价格 + 卧室数/面积/地址 + 收藏按钮 + 状态 Badge）
    - 右侧 Map: 交互地图（房价 Pin，点击高亮列表），Cluster Pin（密集区域合并）
    - 结果数量 Badge（「找到 243 套房源」，筛选后实时更新）
    - 视图切换 ToggleGroup（List / Split / Map）
  → 改变任意筛选条件: 列表和地图即时刷新（无需点击「搜索」或「Apply」）
  → 点击地图 Pin: 列表左侧对应卡片高亮 + 显示 MiniCard Popover
  → 点击房源卡片: 进入 Screen 2（Property Detail）
  → 点击「More Filters」: 展开 Screen 1a（More Filters Modal）

Screen 1a: More Filters Modal（覆盖在搜索结果上）
  主操作: 设置高级筛选条件
  关键组件:
    - Slider（Price Range 双端拖拽，实时显示价格区间）
    - CheckboxGroup（Property Type: House / Condo / Townhouse / Multi-family）
    - RadioGroup（Listing Status: For Sale / Open House / New Listing / Price Reduced）
    - Select（Square Footage）, Select（Year Built）
    - Checkbox（Must-haves: Pool / Garage / A/C / Pet-friendly）
    - Button「Apply Filters」（主 CTA，显示「Apply (X)」含命中数量）, Button「Reset All」
  → 点击「Apply Filters」: 关闭 Modal，搜索结果刷新
  → 点击「Reset All」: 清空所有高级筛选，结果展示全量
  → 关闭 Modal: 返回搜索结果，筛选不生效
```

**Exit State**: 筛选条件持久显示在 Filter Bar（Active Filter Chip），用户可随时删除某个条件
**Empty State**: 筛选后无结果时显示：「这个区域暂无符合条件的房源」+ 建议操作（「扩大搜索范围」Button + 「调整价格区间」Link）

---

### Flow 2: 查看房源详情（Property Detail）

**在此场景的特殊性**: 与 E-commerce 商品详情不同，Real Estate 详情页的图库是核心内容（用户决策依据）；关键指标（价格/卧室/面积）需在首屏完整可见；右侧 Schedule Tour / Contact Agent 区块必须 Sticky（随页面滚动固定，永远可操作）；周边设施信息（学区/通勤时间/噪音评分）是独立的高价值内容板块

**前置条件**: 无（匿名用户可查看房源详情）；房源状态为 Active/For Sale（非下架状态）
**若前置条件不满足**: 房源已售出/下架 → 详情页显示「This home is no longer for sale」Banner，Play 按钮变为 disabled；未登录用户点击收藏 → 触发 Login Modal（保留当前上下文）；图片加载失败 → 显示灰色占位图 + 图片计数

**Entry**: 用户从搜索结果列表点击房源卡片，或点击地图 Pin 后在 MiniCard 上点击「View Details」

**Screens**:
```
Screen 1: Property Detail Page
  布局: 左侧主内容（~65%）+ 右侧 Sticky Panel（~35%）
  
  左侧主内容（从上到下）:
    - 图库区域: 主图（全宽）+ 右侧 2 张缩略图网格，点击进入 Lightbox 全屏浏览
    - 关键指标行: 价格 + 卧室数 + 浴室数 + 建筑面积 + 地块面积
    - 地址 + Breadcrumb（城市 > 区域 > 街道）
    - 描述段落（房源简介，含「Read more」展开）
    - 房屋信息 Table（建造年份 / 车库 / 供暖类型 / 冷却系统等）
    - 学区信息（School District Rating + 对应学校列表，含 Rating Badge）
    - 周边地图（步行分 / 通勤分 / Bikeable 分，第三方 Walk Score 组件）
    - 相似房源 Carousel
  
  右侧 Sticky Panel（跟随滚动固定）:
    - 价格摘要（大字体展示）
    - Tabs（Schedule Tour / Request Info）
    - Schedule Tour Tab: 日期 Chip 横排（最近 5 天），时段 RadioGroup（Morning/Afternoon），Tour 类型 ToggleGroup（In Person / Video Chat）
    - Contact Form: Input（姓名）, Input（电话）, Input（邮箱）, Textarea（留言）
    - Button「Schedule Tour」（主 CTA）
    - 中介信息摘要（头像 + 姓名 + 公司）
  
  关键组件:
    - Lightbox（图库全屏浏览，含「X 张照片」计数，键盘/手势导航）
    - Badge（房源状态：For Sale / New Listing / Price Drop 等）
    - Button（收藏：Heart 图标，未登录时触发登录 Modal）
    - Tabs（房屋详情 / 价格历史 / 周边 / 学区）
  
  → 点击图库主图或「查看全部 X 张照片」: → Screen 2（图库全屏浏览）
  → 点击「Schedule Tour」: → Flow 3 Screen 1（预约看房）
  → 点击收藏（未登录）: 触发登录/注册 Modal，保留返回上下文

Screen 2: Photo Gallery Lightbox（图库全屏浏览）
  触发条件: 点击详情页任意图片或「查看全部 X 张照片」按钮
  主操作: 全屏浏览所有房源照片，按房间分类筛选
  关键组件:
    - 全屏黑色遮罩覆盖层（z-index 最高，保留 ESC 关闭）
    - 主图区（居中，16:9 或原始比例，占视口约 80%）
    - 导航按钮: 左/右箭头（← →）+ 键盘方向键支持
    - 照片计数: 「12 / 38」（当前位置 / 总数，左上角）
    - 关闭按钮: 「✕」（右上角，或按 ESC 返回详情页）
    - 房间分类导航（顶部横向 Tab Row，点击跳转至对应分类首张）:
        All Photos / Living Room / Kitchen / Bedroom / Bathroom / Exterior / Floor Plan
    - 底部缩略图条（横向 Scroll，当前图高亮边框，点击跳转）
    - Virtual Tour 入口（如有）: Button「360° Virtual Tour」（浮于右下角）
  → 键盘 ← / →: 切换上一张 / 下一张
  → 点击分类 Tab: 跳转至该分类第一张
  → 点击缩略图: 跳转至对应图片
  → 点击「✕」或按 ESC: 关闭 Lightbox，返回 Property Detail 页（滚动位置保持）
```

**Exit State**: 用户完成信息浏览后，右侧 Panel 的 CTA 始终可见，随时可触发预约行为
**Empty State**: 不适用（已确认存在的房源详情页）

---

### Flow 3: 预约看房 / 联系中介（Schedule Tour & Contact Agent）

**在此场景的特殊性**: 与酒店/医疗预约不同，Real Estate 的预约通常不需要立即确认时段（中介会主动联系确认）；联系表单是首要路径（比日历选择更低门槛）；预约确认后通常有「贷款预审资格」的交叉销售入口（Trulia 的「Get Pre-qualified」Modal）；整个流程不需要离开详情页——在右侧 Panel 内完成

**前置条件**: 用户已登录（未登录用户可填写联系表单，但提交时触发注册流程）；房源状态为 Active/For Sale；右侧 Sticky Panel 已加载（Schedule Tour Tab 可见）
**若前置条件不满足**: 未登录用户填写表单后点击提交 → 弹出 Login Modal，登录后自动完成提交；房源下架 → Schedule Tour 按钮 disabled + 「This home is no longer available」提示；联系信息不完整 → 按钮保持 disabled 直到必填项全填

**Entry**: 用户在 Property Detail 页右侧 Sticky Panel 中点击「Schedule Tour」按钮

**Screens**:
```
Screen 1: Schedule Tour Panel（Property Detail 右侧 Panel 内）
  主操作: 选择看房日期和方式，填写联系信息
  关键组件:
    - 日期 Chip 横排（最近 7 天，含星期 + 日期，今天高亮）
    - Tour 类型 ToggleGroup（In Person / Video Chat，互斥选择）
    - Contact Form: Input（Full Name）, Input（Phone Number）, Input（Email）
    - Checkbox「我同意接收相关联系」
    - Button「Schedule Tour」（主 CTA，填写姓名+联系方式后激活）
  → 选择日期 + 填写联系信息: Button 从 disabled 变为 active
  → 点击「Schedule Tour」: 触发 Screen 2（Qualification Modal）

Screen 2: Qualification Modal
  主操作: 选择是否进行贷款预审（可选，不强制）
  关键组件:
    - Modal（中等尺寸，不全屏）
    - 标题：「You're one step away!」
    - 说明文字：「Connect with a lender to get pre-qualified and strengthen your offer」
    - 两个选择 Button:「Yes, get pre-qualified」（主 CTA）/ 「No, just contact agent」（次要 CTA，ghost）
  → 点击「No, just contact agent」: 关闭 Modal，进入 Screen 3（确认状态）
  → 点击「Yes, get pre-qualified」: 打开独立的贷款申请流程（外链或新 Tab，超出本 flow 范围）

Screen 3: Confirmation State（Property Detail 右侧 Panel 变为确认状态）
  主操作: 查看预约确认信息
  关键组件:
    - Success Icon（绿色勾）
    - 确认信息：「Tour request sent! [Agent Name] will contact you within 24 hours.」
    - 预约摘要：所选日期 + 联系方式 + Tour 类型
    - Link「Add to calendar」
    - Button「View more listings」（引导继续浏览）
  Exit: 用户可继续浏览详情页其他内容，或返回搜索结果
```

**Exit State**: 右侧 Panel 显示确认状态；用户邮箱/电话收到确认信息；详情页主内容保持完整可浏览
**Empty State**: 不适用

---

---

### Flow 4: 收藏房源与管理已保存清单（Save & Manage Saved Homes）

**在此场景的特殊性**: Real Estate 的「收藏」功能与 E-commerce 的「加购」完全不同：用户通常会收藏 10–30 套房源、历经数周反复比较，最终才决定联系中介。收藏列表不只是临时书签，而是购房决策的主工作区。因此，Saved Homes 页面需要支持：批注（备注想法）、状态追踪（价格变动提醒）、排序/筛选（按价格、收藏时间）、批量删除。分享 Modal（flow_id 6716）也常从 Saved Homes 或 Property Detail 触发，作为「发给配偶/朋友讨论」的协同决策工具。

**行业共识**: Trulia（flow_id 6716，6717）展示了 Share Modal 和 Schedule Tour Panel 的核心交互；Zillow 的「Saved Searches」和「Saved Homes」双列表模式是业界标准。

**前置条件**: 用户已登录（收藏功能需要账号，未登录点击收藏触发 Login Modal）；已至少收藏过 1 套房源（否则进入 Saved Homes 页面展示空状态）
**若前置条件不满足**: 未登录点击 ♡ → 弹出 Login Modal，登录后自动完成收藏；Saved Homes 列表为空 → 空状态「You haven't saved any homes yet」+ 「Start searching」CTA；房源已下架 → 已保存列表中对应卡片显示「Sold / No longer available」Badge

**Entry**: 用户在搜索结果卡片或房源详情页点击 ♡ 收藏按钮；或从导航进入「Saved Homes」页面

```text
Screen 1: 收藏触发（搜索结果 / 详情页）
  主操作: 点击 ♡ 收藏按钮（卡片或详情页右上角）
  关键组件:
    - ♡ Heart 图标（灰色描边 → 红色填充，Optimistic Toggle，即时响应）
    - 未登录时: 点击触发 Login Modal（Screen 1a）
    - 已登录时: 即时收藏 + Toast「♡ Added to Saved Homes  [View] [Undo]」（3 秒）
  → 已登录 + 点击收藏: Toast 出现 → 可点击 [View] 跳转 Screen 2
  → 未登录 + 点击收藏: Screen 1a（Login Modal）

Screen 1a: Login Modal（未登录用户触发，不离开当前页）
  主操作: 登录或注册，完成后自动执行收藏动作
  关键组件: Email + Password 输入框、[Sign In]、「New here? Create account」链接
  → 登录成功: Modal 关闭，收藏动作自动完成，Toast 出现
  → 关闭 Modal: 返回当前页，房源未被收藏，♡ 保持空心

Screen 2: Saved Homes 列表页
  主操作: 浏览已收藏房源，排序/筛选，管理列表
  关键组件:
    - 页面标题「Saved Homes（N）」
    - 排序 Select:「Date saved / Price: Low to High / Price: High to Low / Newest listings」
    - 房源卡片列表（横向宽卡，含首图 + 价格 + 参数 + 地址 + 收藏时间）:
        每张卡片右上角「···」菜单: [Add note] / [Share] / [Remove]
        价格变动提醒 Badge（「Price dropped $20K since saved」橙色）
        已下架 Badge（「No longer available」灰色）
    - 空状态（无已保存房源）:「You haven't saved any homes yet」+ [Start searching]
    - 批量操作（Checkbox 多选 → 底部 Selection Bar）:「Remove N」
  → 点击房源卡片: 跳转 Property Detail 页（Flow 2）
  → 点击「···」→ [Add note]: Screen 3（备注 Drawer）
  → 点击「···」→ [Share]: Share Property Modal（flow_id 6716）
  → 点击「···」→ [Remove] 或 批量 Remove: 即时删除 + Toast「Removed · [Undo]」（5 秒）

Screen 3: 添加备注（Add Note — Inline Panel 或小型 Dialog）
  主操作: 为收藏房源添加个人备注
  关键组件:
    - Textarea（占位符「Add your notes about this property...」，200 字上限）
    - 已有备注时：展示上一次备注内容（可编辑）
    - [Cancel] + [Save note]（主 CTA）
  → 点击 Save note: 关闭 Panel，卡片上显示「📝 Note added」小 Badge
  → 点击 Cancel: 关闭 Panel，备注不保存
```

**Exit State**: 收藏成功：♡ 图标变为红色填充，Toast 确认；Saved Homes 页面新增该房源卡片（排序最前）；删除：卡片即时消失 + Toast 含 Undo 按钮（5 秒内可撤销）
**Empty State**: Saved Homes 页面无房源时显示「You haven't saved any homes yet」+ [Start searching] CTA（引导回搜索，不显示空卡片骨架）

---

## Component Kit

按使用频率排序：

| 功能概念 | 具体用途 |
|---|---|
| 内容卡片 | 房源卡片（图片 + 价格 + 基本参数 + 收藏按钮），搜索结果的基本单元 |
| 范围滑块 | 价格区间双端拖拽（More Filters Modal 内），实时更新结果数 |
| 模态对话框 | More Filters Modal（多分组筛选器）；登录/注册 Modal；Qualification Modal |
| 状态标签 | 房源状态标签（For Sale / New / Price Drop）；学区评分标签 |
| 标签页切换 | Property Detail 内容分区（Overview / Price History / Neighborhood / Schools）；Schedule Tour / Request Info 切换 |
| 互斥/多选按钮组 | 视图切换（List / Split / Map）；Tour 类型选择（In Person / Video Chat）|
| 单选组 | 时段选择（Morning / Afternoon / Evening）；贷款选择 |
| 多选框 | 房屋特征筛选（Pool / Garage / Pet-friendly）；同意接收联系 Checkbox |
| 单行文本输入 | 搜索框（位置输入）；联系表单字段（姓名/电话/邮箱）；留言 Textarea |
| 操作通知（Toast）| 收藏成功确认（「Added to Saved Homes」+ Undo）；分享链接复制确认 |
| 横向滚动内容行（手写）| 相似房源横向滚动（Property Detail 底部）；图库缩略图浏览 |
| 进度条 | 图库浏览进度指示（「12 of 38 photos」）|

---

## Anti-Patterns

- **强制注册才能查看联系方式（Login gate before contact info）**: 用户在未登录状态无法查看中介电话或发起联系，必须先注册 → 正确做法：允许填写联系表单和发送 Tour 请求，登录/注册仅在「保存收藏」时触发（不在浏览和联系环节设 Gate）
- **地图和列表是两个独立页面（Map and List as separate routes）**: 用户在列表页无法参考地理位置，在地图页无法查看完整房源信息 → 正确做法：默认双栏并存（List + Map 同屏），提供「List Only / Map Only」切换但不跳转路由，地图 Pin 与列表卡片双向联动
- **筛选条件改变触发页面跳转（Filter change navigates to new page）**: 每次修改价格区间都刷新页面，用户失去当前滚动位置和浏览上下文 → 正确做法：筛选操作原地刷新结果（地图 Pin 和列表同步更新），不改变 URL 路由（或用 query string 更新而不触发页面重载）
- **预约日期不显示可用时段（Date picker without availability）**: 用户选择日期后才发现「该时段已满」，导致多次重选 → 正确做法：日期 Chip 上显示可用性状态（Available / Limited / Unavailable），让用户在选择前即可判断

- **图库截断至前 5 张，隐藏其余照片（Gallery truncated without count）**: 详情页只展示 4-5 张图，其余照片藏在「更多」按钮后，用户不知道还有多少张 → 正确做法：始终展示总张数（「查看全部 38 张照片」），主图区右下角叠加计数标签，点击任意一张立即进入全屏 Lightbox 浏览全量图库

- **电话号码默认隐藏需二次点击（Phone number hidden behind reveal click）**: 联系中介的电话号码需要点击「显示电话」才能查看（通常是为了统计点击量），但这为用户增加了一步摩擦 → 正确做法：电话号码直接展示（除非法规要求），点击即可拨打；若因统计需要保留「显示」交互，该按钮视觉上必须非常明显，不能让用户以为无法联系

