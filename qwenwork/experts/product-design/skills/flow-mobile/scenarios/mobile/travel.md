# Scenario: Mobile Travel（出行 & 旅游）

> **研究来源**：基于对 Tripsy、Omio、Airbnb、FocusFlight、Mozi、Google Maps 等 6 个真实 iOS 产品 flow 和页面的横向分析抽象，不代表任何单一产品的具体实现。

---

## Identity

**Platform**: Mobile (H5 / React Native)
**Definition**: 以行程规划和交通/住宿预订为核心的移动端旅行应用，用户通过搜索出发地/目的地查找交通（航班/火车/大巴），选择日期和座位后完成支付；同时管理多条行程，查看登机牌/车票，使用地图探索目的地附近住宿。

**Canonical Examples**: Airbnb iOS、Booking.com iOS、Omio iOS（多交通方式）、Tripsy iOS（行程管理）

**Not this scenario if**:
- 以网约车/即时打车为主（Uber/滴滴，属于即时出行，缺少「提前预订」环节）
- 以导航为主（Google Maps/Apple Maps，属于地图 & 导航场景）
- 以企业商务出行管理为主（差旅报销/审批，属于 web/internal-ops 变体）
- 主要在 Web 端操作（改用 web/ecommerce 结账流程）

---

## User Profile

| 维度 | 内容 |
|---|---|
| **主要角色** | 休闲旅行者（假期行程规划）/ 商务旅行者（频繁出差，注重效率）/ 背包旅行者（弹性路线，多段行程）|
| **核心目标** | 搜索并预订合适的交通/住宿 / 查看已有行程安排 / 出发时快速访问登机牌/车票 |
| **心智模型** | 期待「一站式」管理（同一 App 内查航班 + 管行程 + 查酒店）；期待价格透明（总价含税费，无隐藏费用）；期待高可靠性（旅行关键时刻不能 App 崩溃）|
| **使用频率** | 低-中频（计划阶段：每天查几次；出行当天：高频查登机牌/行程）|
| **决策模式** | 任务驱动型：有明确出发地/目的地/日期；日期和价格是关键决策因素 |
| **容错期望** | 预订前可自由取消（未付款行程）；已付款预订需显示明确退改政策；登机牌/车票支持离线查看（无网络也能使用）|

---

## IA Template

**导航模式**: Tab Bar（底部 Tab Bar，3-4 项）

Tripsy（行程管理工具）模式：
```
Tab 1: 我的行程 / My Trips — 行程卡片列表
Tab 2: 发现 / Explore     — 目的地灵感 + 推荐内容
Tab 3: 我的 / Profile     — 账户 + 订阅状态
```

Omio（多交通方式预订）模式：
```
Tab 1: 搜索 / Search     — 搜索框（出发地/目的地/日期）
Tab 2: 行程 / Trips      — 已预订行程列表 + 车票
Tab 3: 收藏 / Saved      — 保存的路线/价格提醒
Tab 4: 我的 / Account    — 账户 + 设置
```

**页面层级**: 3 级
```
L1: Tab 根页（My Trips / Search / Explore）
L2: 行程详情（Trip Detail：每日行程）/ 搜索结果列表
L3: 操作面板（添加事件 Sheet / 日期选择 / 座位地图 / 预订确认）
```

**权限流结构**（旅行 App 权限集中）:
```
Location（定位附近机场/自动填充出发地）:
  → 首次打开搜索页 → 自定义说明页（「自动填充离你最近的机场」）
  → 浏览器 Geolocation API / Expo Location（whenInUse）
  → 部分 App 后续申请后台位置（后台航班追踪）→ 系统二次弹窗

Notifications（航班变更/值机提醒/行程推送）:
  → 首次完成预订后 → 说明页（「航班延误提醒、出发前通知」）
  → 系统 Notifications 权限弹窗

登机牌/车票数字凭证:
  → H5: 下载 PDF / 添加到 Apple Wallet（Safari 支持）/ 发邮件
  → RN: 生物识别 / 密码确认后展示 QR Code 凭证

Camera（扫描护照/文件 - 部分 App）:
  → 系统 Camera 权限弹窗
```

**数据密度**: 中（搜索结果中密度列表，行程详情低-中密度 Timeline）
- 核心视图：`List`（搜索结果 / 行程事件 Timeline）+ 地图（MapKit / Leaflet / Google Maps）
- 辅助视图：Grid（目的地图片 Grid）
- 特殊元素：日历选择器（Date Picker）/ 出发地-目的地 pill 输入组件

**主要容器模式**:
| 场景 | 容器 |
|---|---|
| 出发地/目的地搜索 | Bottom Sheet（large）+ 搜索框（Suggestions 实时列表）|
| 日期选择（出发/返回）| Bottom Sheet（medium/large）+ 日历组件 |
| 过滤器（航班/火车筛选）| Bottom Sheet（large）+ 多维度过滤 |
| 添加行程事件 | Bottom Sheet（large）表单 |
| 座位地图 | Stack Push（全页面）|
| 登机牌/车票查看 | Stack Push（全页面，支持离线）|
| 取消预订确认 | Dialog（「取消后退款将在 X 工作日到账」）|
| 价格提醒设置 | Bottom Sheet（medium）|

**导航骨架图（ASCII，Tripsy 行程管理模式）**:
```
┌────────────────────────────────────┐
│  Status Bar（时间 / 信号 / 电量）    │
├────────────────────────────────────┤
│  我的行程                    [+新建] │  ← Tab 1: My Trips
│                                    │
│  ┌──────────────────────────────┐  │
│  │ [目的地封面图]                │  │
│  │  🗺 Tokyo, Japan             │  │  ← 行程 Card（封面 + 名称）
│  │  Mar 15 – Mar 22 · 7 days   │  │
│  └──────────────────────────────┘  │
│                                    │
│  ┌──────────────────────────────┐  │
│  │ [目的地封面图]                │  │
│  │  🗺 Paris, France            │  │
│  │  Jun 1 – Jun 8 · 8 days     │  │
│  └──────────────────────────────┘  │
│                                    │
│  [+ 规划新行程]（CTA，空状态时显示） │
│                                    │
├───┬──────┬──────┬─────────────────┤
│行程│  发现  │  我的 │                  │  ← TabBar
└───┴──────┴──────┴─────────────────┘
```

---

## 该场景独有的 IA/UX 决策

1. **日期选择必须使用日历视图（内联日历），不可用文字输入框** — 旅行场景中「出发日期 / 入住日期 / 退房日期」的选择不仅是选择一个数字——用户需要同时看到星期几（周末价格更贵？）、节假日分布（国庆黄金周满房）、以及入住 + 退房日期的视觉范围（高亮区间）。Bottom Sheet 内弹出内联日历组件（H5 常见的 `react-day-picker` / `antd-mobile DatePicker`；RN `react-native-calendars`），支持日期范围连续高亮，不同日期可附 availability 标注（不可选 = 灰色）——Tripsy / Airbnb / Google Maps 均采用日历视图，体验比文字输入框直观且支持范围高亮。

2. **Location 权限必须先展示自定义说明页，用途说明需明确限定为「出发地自动填充」** — 旅行 App 请求位置权限（浏览器 Geolocation API / Expo Location，`whenInUse`）用于自动填入搜索表单的出发城市，而非 GPS 追踪——但用户看到「允许访问位置」系统弹窗时，第一反应是「这个 App 是否要持续追踪我的位置」，拒绝率极高。自定义说明页必须在系统弹窗前展示，明确说明「你的位置仅用于自动填写出发城市，不在后台持续追踪」，让用户理解是「一次性填充」而非「常驻监控」——Tripsy（flow 2326）/ Omio（flow 5154）均有此权限说明页，是旅行类 App 提升位置授权率的关键步骤。

3. **多交通方式搜索用顶部 Segmented Control 统一入口，不可分散为多个独立 Tab 或按钮** — 旅行 App 的用户在搜索时常处于「不确定交通方式」的状态（是坐火车还是坐飞机？价格差多少？时间差多少？）。Omio（flow 5154）的多交通 Tab（✈飞机 / 🚂火车 / 🚌大巴）是同一个搜索界面内的 Segmented Control，切换后出发地/目的地/日期输入框保持不变，只有结果列表刷新——如果每种交通方式是独立入口（需重新输入出发地/目的地），用户对比「火车 vs 飞机」要重复操作两次，摩擦极高。Segmented Control 统一入口使跨交通方式比价成为零成本操作，是旅行搜索区别于单一垂直预订工具（纯机票 / 纯酒店）的核心 IA 决策。

4. **行程管理用时间轴（Timeline List）展示每日计划，不可用普通卡片列表** — 旅行行程不是无序任务列表，而是有严格时间顺序的事件序列（「上午 9:00 登机 → 12:30 抵达 → 14:00 酒店 Check-in → 18:00 晚餐预约」）。移动端行程管理（Tripsy / Mozi）采用纵向时间轴结构：竖线连接各时间节点，每个节点显示时间 + 图标 + 标题（交通/住宿/活动三种图标区分），可一眼扫描当日行程密度——普通卡片列表无法传达「节点之间的时间间隔」和「行程紧张度」，是旅行场景区别于通用 To-Do App 的关键 IA 设计。时间轴通过 `FlatList` + 自定义 `TimelineView` 或 List + 竖线 `View` 实现，而非第三方图表库。

5. **预订确认后必须触发数字凭证保存 + 推送权限请求，提供离线凭证** — 移动端旅行 App 与 Web 旅行网站的核心原生差异是：预订完成时可将机票/酒店确认单保存为本地可离线访问的数字凭证（RN：离线缓存 QR Code；H5 / Safari iOS：支持「添加到 Apple Wallet」Pass；通用方案：下载 PDF + 本地缓存），用户到达机场/酒店时直接在 App 出示即可——Web 旅行预订只能发送 PDF 邮件或需登录网站查看，存在「忘记打印/信号差打不开网页」的实际风险。同时，预订完成是请求推送权限的最佳时机（「接收航班延误 / 酒店确认提醒」），用户此刻刚完成预订、关联感最强——Tripsy（flow 2326）的 onboarding 权限序列包含通知权限，是旅行类 App 推送授权率最高的触发节点。

---

## Canonical Flows

> 以下 flow 基于 6 个真实产品样本横向分析抽象。括号内标注「行业共识」表示 3 个以上产品采用相同模式。

---

### Flow 1: Search & Book Transportation（搜索 + 预订交通）

**在此场景的特殊性**: 移动端旅行 App 的搜索表单与 Web 端最大的区别是**出发地/目的地 Pill 输入组件**（两个圆角 Token，中间有 ⇄ 互换按钮）——这是旅行搜索的行业标准 UI，移动端通常将整个搜索区域设计为可点击的 Summary Row，点击后弹出 Bottom Sheet（Tripsy flow 2352 验证）。**日期选择**统一使用内联日历（而非文本输入），支持范围选择（出发日 → 返回日 高亮区间）。**搜索结果排序**默认按「最便宜」或「最快」，Filter Chip（直飞/经停/座位等级）横向可滚动（Omio flow 5154 确认）。**登机牌/车票数字凭证**（离线可访问 QR Code / Apple Wallet Pass）是移动端旅行 App 区别于 Web 旅行网站的核心体验价值。

**行业共识**：Tripsy / Omio / FocusFlight 均使用「出发地-目的地 pill → 日期 → 搜索结果 → 确认」4 步结构；Omio（flow 5154）确认了「通知 + 位置」双权限在 onboarding 末尾依次请求的模式。

**Entry**: 首页搜索栏 → 点击搜索区域 → 或 Tab Bar 搜索 Tab

```
Screen 1: 搜索表单（Search Form）
  主操作: 设置出发地 / 目的地 / 日期 → 发起搜索
  关键组件:
    - 交通类型 Segmented Control（机票 / 火车 / 大巴 / 全部）（Omio 多交通方式）
    - 出发地-目的地 Pill 行:
        横向排列:
          Button(出发地 Pill: 「北京 PEK」or「选择出发地」, 次要，圆角)
          Button(⇄ 互换, 图标按钮, SF Symbol/图标 "arrow.left.arrow.right")
          Button(目的地 Pill: 「东京 NRT」or「选择目的地」, 次要，圆角)
        → 点击出发地/目的地 Pill: Bottom Sheet（large）弹出 Screen 1-A 地点搜索
    - 日期选择行:
        Button(「出发: 3月15日」, 次要)（→ Bottom Sheet（medium）内联日历）
        Button(「返回: 3月22日」, 次要，单程时显示「单程」Toggle）
    - 乘客/座位级别 Button（「1 成人 经济舱 ▾」→ Bottom Sheet（medium）Stepper 弹窗）
    - Button("搜索", 主色，全宽，disabled 直到出发地和目的地均已选择)
  → 所有字段填写完成点击「搜索」: Stack Push → Screen 2

Screen 1-A: 地点搜索 Sheet
  触发条件: 点击出发地或目的地 Pill
  主操作: 输入地名 / 选择机场/车站
  关键组件:
    - Bottom Sheet（large）+ 搜索框（自动聚焦，键盘弹起）
    - 位置权限已授权时: 「📍 使用当前位置」置顶（快捷选项）
    - 实时 Suggestions List（输入 ≥ 1 字符后展示）:
        每行: 城市/机场名 + 机场代码（如「北京首都国际机场 PEK」）
    - 热门目的地（空搜索时显示: 横向城市 chip 列表）
  → 点击某城市/机场: 返回 Search Form，更新对应 Pill

Screen 2: 搜索结果列表（Results List）
  主操作: 浏览结果 → 筛选 → 选择
  关键组件:
    - 页面标题（「北京 → 东京 · 3/15 · 1人」）
    - 过滤器行（横向 ScrollView）:
        Button("⚙️ 全部过滤", 次要)（→ Filter Sheet）
        Button("直飞", chip 样式，选中状态深色)
        Button("价格从低到高", chip 样式)
        Button("时长最短", chip 样式)
    - List（结果列表，下拉刷新）:
        每行 ResultCard:
          航空/铁路公司 Logo + 名称
          出发时间（粗体）- 航行时长 - 到达时间（粗体）+ 「直飞/1经停」label
          价格（大字，品牌色）+ 「/人」+ 仓位类型
          左滑: Button("价格提醒 ⏰", 次要)
    - Empty（无结果: 「未找到该日期航班」+ 「查看相邻日期」CTA）
  → 点击某结果: Stack Push → Screen 3

Screen 3: 预订详情 & 确认（Booking Detail & Payment）
  主操作: 查看详情 → 填写乘客信息 → 支付
  关键组件:
    - 行程摘要（出发 ↔ 到达信息，中转信息，总时长）
    - 表单（乘客信息）:
        TextInput("姓名（拼音，如护照）")
        TextInput("手机号")
        [国际航班] TextInput("护照号")
        Toggle("保存乘客信息供下次使用")
    - 行李选择（可选，Bottom Sheet 弹出行李选项列表 + 价格）
    - 座位选择（可选，Button → Screen 3-A 座位地图）
    - 价格汇总（机票 + 行李 + 服务费 = 合计）
    - Button("Apple Pay / 微信支付", 主色，首选支付）
    - Button("其他支付方式", 次要)（→ 信用卡/支付宝等）
  → 点击支付: 平台支付授权（生物识别 / 密码确认）→ Screen 4

Screen 3-A: 座位地图（Seat Map）
  触发条件: 点击「选择座位」
  主操作: 可视化选座
  关键组件:
    - Stack Push（全页面）
    - 飞机舱位示意图（Grid: 按 A/B/C/D/E/F 列，每行一排）
    - 座位颜色状态:
        绿色（可选）/ 灰色（已占用）/ 黄色（额外收费）/ 蓝色（已选中）
    - 图例（Legend: 颜色说明）
    - Button("确认座位 X排Y列", 主色)
  → 选中 + 确认: 返回 Screen 3，预订摘要更新

Screen 4: 订单确认（Order Confirmation）
  主操作: 查看确认 / 保存凭证
  关键组件:
    - 大图标（成功 checkmark，绿色）
    - Text("预订成功！"）
    - 订单摘要（航班信息 + 座位 + 乘客）
    - Button("添加到 Apple Wallet / 下载 PDF", Wallet 图标 / 下载图标)
    - Button("查看行程", 次要)（→ Flow 2 行程详情）
    - 系统分享按钮（分享行程给同伴）
```

**Exit State**:
- ✅ 预订成功：确认页 + 邮件通知 + 可保存数字凭证
- ❌ 支付失败：内联错误 + Button("重试") + Button("换支付方式")
- ⚠️ 无库存/舱位已满（选座时）：对应座位置灰 + Toast「该座位已被选走」

---

### Flow 2: Create & Manage Trip Itinerary（创建 + 管理行程）

**在此场景的特殊性**: 移动端旅行行程管理 App 的「行程卡片」（Trip Card）是与 Web 端行程规划最大的 UX 差异——每个行程用大封面图 Card（目的地照片 + 名称 + 日期范围）展示，而非 Web 的表格/列表行，视觉上像相册。行程内部按天（Day 1 / Day 2...）分 Section，每 Section 内的事件（航班/酒店/活动）按时间排序形成 **Timeline**（时间轴），这与其他类型 App 的 List 有根本不同。**航班信息添加**支持两种方式：手动填写（航班号 + 日期）或搜索（Tripsy flow 2352 展示的搜索 Sheet）。**系统分享行程**（Mozi flow 4142 确认）生成富链接预览（Rich Card）可在 Messages/微信等直接预览行程，是移动端原生分享的标准用法。

**行业共识**：Tripsy（flow 2326 / 2352）展示了「My Trips 封面卡片 → 行程 Timeline → 添加事件 Sheet」的完整行程管理结构；系统分享是移动端旅行 App 分享的行业标准（Mozi 确认）。

**Entry**: Tab Bar「我的行程」Tab → 点击「+」新建行程 / 点击已有行程卡片

```
Screen 1: 我的行程列表（My Trips）
  主操作: 查看所有行程 / 新建行程
  关键组件:
    - 页面标题「我的行程」+ 右上角「+」新建 Button
    - List / FlatList（行程卡片列表，下拉刷新）:
        每个 Trip Card:
          封面图（目的地图片，16:9，圆角）
          目的地名（粗体）
          日期范围（小字灰色）+ 天数
          长按 Context Menu: 编辑 / 分享 / 删除（触发 Dialog）
    - Empty（无行程: 插图 + 「规划你的第一次旅行」CTA）
  → 点击某行程 Card: Stack Push → Screen 2
  → 点击「+」新建: Bottom Sheet（large）→ Screen 1-A 新建行程

Screen 1-A: 新建行程
  主操作: 设置行程基本信息
  关键组件:
    - Bottom Sheet（large）+ 页面标题「新建行程」+ 「取消」+ 「添加」
    - 表单:
        TextInput("目的地名称（如「东京之旅」）")
        Button("选择目的地" → 搜索 Sheet 搜索城市)
        日期选择（出发日 → 返回日，内联日历或 Compact 样式）
    - Button("添加行程", 主色，全宽，字段完整后激活)

Screen 2: 行程详情（Trip Detail / Timeline）
  主操作: 查看按天安排 / 添加事件 / 查看已有事件
  关键组件:
    - 页面标题（行程名）
    - 顶部 Hero（目的地图片 + 日期范围 + 分享按钮）
    - 右上角: 分享 + 「编辑」按钮
    - 按天分组 Section List:
        Section Header（「Day 1 · 3月15日 周五」）
        每个 EventRow（行程事件）:
          时间（小字灰色）
          类型图标（✈️ 航班 / 🏨 酒店 / 🗺 活动）
          事件名称（粗体）
          副标题（如「CA1234 北京PEK → 东京NRT」）
          → 点击: Stack Push → 事件详情
        Button("+ 添加事件", 文字按钮)（Section 末尾，→ Screen 3 事件添加）
    - [空 Section] Empty（「本日暂无安排，点击 + 添加」）

Screen 3: 添加行程事件（Add Event Sheet）
  主操作: 选择事件类型 → 填写信息
  关键组件:
    - Bottom Sheet（large）
    - 事件类型选择（顶部 Segmented Control / Grid）:
        ✈️ 航班 / 🏨 酒店 / 🚌 交通 / 🗺 活动 / 🍽 餐厅 / 📄 其他
    - [航班类型] 表单:
        TextInput("航班号（如 CA1234）")
        搜索 Button（→ Screen 1-A Flight Search Sheet 查找具体航班）
        出发/到达时间选择器
        TextInput("出发机场 / 到达机场")
    - [酒店类型] 表单:
        TextInput("酒店名称")
        入住 DatePicker + 退房 DatePicker
        TextInput("确认号（可选）")
    - Button("保存", 主色，全宽)
```

**Exit State**:
- ✅ 行程创建/事件添加：Timeline 即时更新，按时间自动排序
- ↩ 放弃新建（点取消）：Dialog 确认「放弃未保存的更改？」
- ✅ 分享行程：系统分享面板 → Messages / 微信 / 复制链接，富链接预览展示目的地图

---

### Flow 3: Explore Nearby & Discover Accommodation（地图探索 + 住宿搜索）

**在此场景的特殊性**: 移动端旅行 App 的住宿搜索与 Web 端最大的差异是**地图与列表的双视图联动**——移动端上通常把地图嵌在上半屏（约 55% 高度），列表/Carousel 嵌在下半屏，或提供列表/地图两种独立视图切换（Airbnb 模式）。**地图标注价格 Pin**（MapAnnotation 显示价格气泡，如「¥800」）是旅行住宿地图的独有元素，让用户直接在地图上比较价格分布。**入住/退房日期选择**使用内联日历，支持范围选中高亮（入住日 → 退房日之间的日期变色）。**多平台价格对比**（Google Maps 酒店页面展示 Expedia / Booking.com / 官网 价格）是聚合类 App 的特色，与直连 OTA 体验不同。

**行业共识**：Google Maps 酒店搜索展示了「地图上方 + 过滤器 + 下方酒店 Carousel」三段式布局；价格气泡 Pin 是旅行住宿 App 的行业标准（Airbnb / Google Hotels 均如此）。

**Entry**: 首页 → 「发现/探索」Tab → 或搜索结果后点击「地图」视图

```
Screen 1: 地图探索（Map + Accommodation Search）
  主操作: 在地图上搜索住宿 / 查看价格分布
  关键组件:
    - 地图组件（RN: `react-native-maps`；H5: Leaflet / Google Maps JS）占据上方约 55% 屏幕
    - 价格气泡 Marker（白底圆角矩形 `Text("¥800")`，随缩放显示/隐藏）
    - 选中 Marker（更大，品牌色边框）
    - 搜索区域 Toolbar（地图上方 overlay）:
        「目的地」输入框（当前城市，可修改）
        DateRange Button（「3/15 – 3/22」，→ 日期 Sheet）
        「⚙️ 过滤」Button（→ Filter Sheet：价格范围/星级/设施）
    - 下方 Carousel（横向可滚动，当价格 Marker 被点击时高亮对应卡片）:
        每张 PropertyCard:
          封面图（圆角）
          酒店名（粗体）
          ⭐ 评分 + 评价数量
          价格「¥800/晚」（品牌色）
    - 「列表视图」/ 「地图视图」切换 Button（浮动，pill 样式）
  → 点击 Marker / Carousel Card: Stack Push → Screen 2
  → 点击「搜索此区域」（地图拖动后弹出）: 重新查询当前地图范围

Screen 2: 住宿详情（Property Detail）
  主操作: 查看详情 → 检查可用性 → 预订
  关键组件:
    - Stack Push（页面标题酒店名）
    - 图片轮播（Swiper/Carousel，16:9 或 4:3）
    - 酒店信息区:
        酒店名（粗体大字）
        ⭐ 评分（large）+ 「4.5」+ 「(996 条评价)」（小字）
        地址 / 距市中心 X km（小字灰色）
    - 价格/可用性检查（日期 + 人数 → 显示「¥800/晚 · 3晚 ¥2400」）
    - 房型 List（多房型比较，每行: 房型名 + 面积 + 床型 + 价格 + 预订 Button）
    - 设施标签（横向 Chips: 免费WiFi / 停车 / 游泳池 / 早餐...）
    - [价格聚合 App] 价格对比 List（Expedia / Booking.com / 官网，各自价格）
    - 评价 Section（前 3 条 + 「查看全部 XX 条」链接）
    - 小地图（点击 → 系统地图 App 导航）
    - 底部固定 CTA: Button("查看可用房间 ¥XXX起", 主色)
  → 点击「查看可用房间」: Stack Push → 房间选择 → 支付流程（同 Flow 1 Screen 3）
```

**Exit State**:
- ✅ 预订成功：确认页 + 「添加到日历」+ 「保存数字凭证」
- ⚠️ 所选日期无空房：提示「该日期已满」+ 「查看附近日期」CTA
- ↩ 返回地图：Stack Pop，地图状态保留，已选 Marker 保持高亮

---

---

### Flow 4: Online Check-in & Boarding Pass（在线值机 + 登机牌）

**在此场景的特殊性**: 在线值机是旅行 App 与 Web 航空官网最有竞争力的差异化功能——用户不需要找邮件、打开浏览器、重新登录，直接在 App 内完成值机并获取可离线展示的数字登机牌。FocusFlight（flow_id 8602，5 屏）展示了登机牌 UI 的最高规范实现：**折叠态**（行程摘要卡片）→ 点击/拖拽**展开**（完整登机牌：出发地机场代码 + 目的地机场代码 + 座位号 + 姓名）→ **Barcode 撕票动效**（Barcode 区域从卡片下半部分渐进分离，模拟物理撕票体验）→ **Barcode 全屏单独展示**（大 QR Code，亮度自动最高，方便扫描仪识别）。FocusFlight（flow_id 8608）确认了值机 CTA 的状态机模式：「Check-in」CTA → 完成值机后切换为「Boarding」CTA（同位置，不同文案/颜色），让用户清晰感知状态。Omio（flow_id 5231）确认「添加到 Apple Wallet」必须是登机牌页面的第一优先级主 CTA（使用 Apple 官方黑色 Wallet 按钮样式）。**值机时间窗口（通常起飞前 24-48 小时）必须主动推送通知**——用户不应该靠记忆知道「现在可以值机了」，Push Notification 是触发值机的核心入口（Deep Link 直达值机流程）。

**行业共识**：FocusFlight（flow_id 8602 / 8608）/ Omio（flow_id 5231）均将登机牌设计为「上半乘客信息 + 锯齿穿孔分割线 + 下半 QR/Barcode」的票据样式，与物理登机牌视觉语言一致——这是用户在机场扫码前识别「这是我的登机牌」的关键视觉线索。Omio（flow_id 5188 / 5185）确认了「支付 → Processing → Retrieve ticket → QR 展示」的取票动画三步是旅行 App 的行业标准过渡模式。

**Entry**: Push Notification「您的航班值机已开放」→ Deep Link 直达；或 My Trips → 航班卡片 → 点击「Check-in」CTA

```
Screen 1: 航班卡片（值机前 / 值机可用状态切换）
  主操作: 查看即将出发的航班，发起值机
  容器: 行程详情页（Flow 2 Trip Detail Timeline）内的航班 EventRow，点击展开
  关键组件:
    - 行程 Timeline 中航班 EventRow（展开态）:
        出发机场代码（大字，3字母，如「PEK」）→「–」→ 到达机场代码（「NRT」）
        出发时间 + 到达时间 + 航班号 + 出发日期
        座位号（值机后显示）/ 「待值机」（值机前灰色）
    - 值机状态 CTA（底部，状态机三态）:
        态 1「值机未开放」（出发前 > 48h）: Button("还有 XX 时开放", disabled 灰色)
        态 2「立即值机」（出发前 24-48h）: Button("立即值机 →", 主色填充，Active)
        态 3「查看登机牌」（已值机）: Button("查看登机牌 ↓", 品牌色)
    - 值机倒计时 Banner（态 1 到态 2 转换前 1 小时显示）:
        「⏰ 值机将于 X 分钟后开放」（橙色 Info Banner）
  → 点击「立即值机」: Stack Push → Screen 2（值机流程）
  → 点击「查看登机牌」（已值机）: Stack Push → Screen 3（登机牌展示）

Screen 2: 值机流程（Check-in Flow）
  主操作: 确认乘客信息 → 选座 → 完成值机
  容器: 独立全屏页面（Stack Push）
  关键组件:
    - NavigationBar: 「← 返回」+ 标题「在线值机」
    - Section「航班信息」（只读确认区）:
        大字机场代码行（PEK → NRT）+ 航班号 + 出发时间
    - Section「乘客信息」（只读确认，已预订时预填）:
        姓名（拼音护照格式）+ 护照号（末 4 位脱敏）+ 联系手机
        行 → 如信息有误: Text Link「联系客服修改」
    - Section「座位选择」:
        [已选座位] Row: 「当前座位: 12C 经济舱 靠窗」+ Button("更换座位 →")
        → 点击「更换座位」: Bottom Sheet（large）→ Screen 2-A（值机选座图）
        [未选座位] Button("选择座位", 主色文字)（→ Screen 2-A）
    - Section「附加服务」（可选）:
        Row「特殊餐食」: Selector（普通 / 素食 / 清真 / 儿童）
        Row「特殊需求」: Toggle（轮椅辅助 / 优先登机）
    - Checkbox「我确认以上信息正确」（必须勾选才激活提交）
    - Button("完成值机", 主色，全宽，disabled 直到 Checkbox 勾选)
  → 点击「完成值机」: Loading（「正在连接航空公司系统...」圆形 Loading）→ Screen 3

Screen 2-A: 值机选座图（Seat Map Sheet）
  主操作: 重新选择座位（值机阶段免费换座）
  容器: Bottom Sheet（large，可向上拉至全屏）
  关键组件:
    - Sheet Header: 「选择座位」+ Button「✕」关闭
    - 快速选座 Chips（横向, 可选）:
        Chip("靠窗") / Chip("靠走道") / Chip("前排") / Chip("出口排")（快速筛选可用座位）
    - 飞机座位图（可缩放，双指捏合）:
        机舱分区 Label（头等舱 / 商务舱 / 经济舱）
        每排座位（按 A/B/C + 走道 + D/E/F）
        颜色: 绿色（可选）/ 灰色（已占）/ 蓝色（当前选中）/ 黄色（出口排/额外空间，值机免费）
    - 底部固定 Bar:
        「已选: 第 12 排 C 座（靠窗）」
        Button("确认座位", 主色，全宽)
  → 点击可用绿色座位: 即时高亮为蓝色选中态 + 底部更新座位信息
  → 点击「确认座位」: Sheet 关闭，Screen 2 座位信息更新

Screen 3: 登机牌展示（Boarding Pass Display）
  主操作: 出示登机牌 / 添加到 Apple Wallet / 截图保存
  容器: 独立全屏页面（Stack Push，Tab Bar 隐藏）
  布局: 黑色/深色全屏背景（增强 QR Code 对比度）
  关键组件:
    顶部操作区:
      - NavigationBar: 「← 我的行程」+ Button("..." 更多，右上角)
      - 屏幕亮度: 自动调至最高（`expo-brightness` / `UIScreen.main.brightness = 1.0`）

    登机牌卡片（白色，圆角，居中展示，约屏幕 90% 宽）:
      上半部分（乘客 + 航班信息区）:
        出发机场（大字 3 字母代码「PEK」+ 城市名小字）
        → 「—————————→」箭头
        到达机场（大字 3 字母代码「NRT」+ 城市名小字）
        乘客姓名（粗体）/ 航班号 / 座位（大字显眼）/ 出发时间 / 登机口
        状态 Badge:「登机中」（绿色）/「准时」（蓝色）/「延误」（橙色）

      穿孔分割线（虚线 + 两侧锯齿缺口，模拟物理撕票线）

      下半部分（凭证区）:
        QR Code / Barcode（居中，尽可能大）
        Text「扫描此码通过安检 / 登机」（小字灰色）
        订单确认号（「Booking: XYZABC」）

    交互: 点击 QR Code 区域 → 「撕票」动效（Barcode 区域向下分离，全屏放大展示 QR Code）
      全屏 QR Code 态:
        纯白背景 + 超大 QR Code（屏幕 80% 宽）
        返回触发: 点击 QR Code 或下滑手势

    底部操作区:
      - Button("添加到 Apple Wallet", 黑色，Apple 官方样式，带 Wallet 图标)（主 CTA）
      - Button("分享登机牌", 次要，系统分享面板，可发送给同行者）
      - Text Link("下载 PDF 副本"，小字，备用）

Screen 4: 已有登机牌列表（多人/多程管理）
  主操作: 管理同一行程的多张登机牌
  触发条件: 一个行程有多名乘客（家庭出行）或多段航班
  容器: 独立页面（Screen 3 顶部「← 我的行程」旁有「全部登机牌 (3)」按钮时）
  关键组件:
    - NavigationBar: 「← 返回」+ 标题「登机牌（3）」
    - List（每张登机牌一行）:
        乘客姓名（粗体）+ 座位号 + 航班号 + 状态 Badge
        右侧: 「查看」Button（→ 对应 Screen 3）
    - Section 分组（多段航班）:
        Section Header:「第 1 段 PEK → NRT」/ 「第 2 段 NRT → SFO」
    - 空状态（所有登机牌已添加到 Wallet）:
        Text「全部登机牌已保存到 Apple Wallet」+ Wallet 图标（绿色）
```

**Exit State**:

- ✅ 值机成功：航班 EventRow 更新座位号，CTA 切换为「查看登机牌」；Push Notification「值机成功，出发前 3 小时提醒您准备登机」
- ✅ 添加到 Apple Wallet：系统 Wallet App 打开，登机牌出现在 Passes 列表；Toast「已添加到 Apple Wallet」；离线时 Wallet 直接可用（无需打开旅行 App）
- ✅ 登机牌离线可用：值机完成时 QR Code 数据立即缓存本地（无网络也能展示）
- ❌ 值机系统不可用（航空公司接口故障）：Toast「值机服务暂时不可用，请稍后再试或前往机场柜台」+ 客服联系 Button
- ❌ 座位已被占用（实时冲突）：Toast「该座位刚刚被他人选取，请重新选择」，返回选座图

---

## Mobile Component Kit

按使用频率排序（基于研究样本观察）：

| 优先级 | 组件（H5 antd-mobile）| 组件（RN Gluestack/RN）| 具体用途 |
|---|---|---|---|
| ★★★ | Leaflet / Google Maps JS API | `react-native-maps` | 住宿/景点地图 + 价格气泡 Pin |
| ★★★ | Stack Navigation | `react-navigation Stack` | 搜索 → 结果 → 详情 → 支付多步 Push |
| ★★★ | 日历组件（`react-day-picker` / antd-mobile DatePicker）| `react-native-calendars` | 出发/返回日期 + 入住/退房日期（范围选择）|
| ★★★ | Tab Bar / `Tabs` | `react-navigation Bottom Tabs` | App 主导航（行程/搜索/发现/我的）|
| ★★★ | 本地缓存 QR Code / PDF / Apple Wallet Pass | `expo-print` / `react-native-wallet` | 登机牌/车票数字凭证（离线可访问）|
| ★★ | Bottom Sheet | `@gorhom/bottom-sheet` | 地点搜索 / 日期选择 / 过滤器 / 添加事件 |
| ★★ | SearchBar / TextInput + 实时 Suggestions | `SearchBar` / `TextInput` + debounce | 出发地/目的地城市搜索（实时建议）|
| ★★ | `List` / `FlatList` | `FlatList` / `SectionList` | 搜索结果列表 / 行程 Timeline 事件 |
| ★★ | Swiper / Carousel | `react-native-snap-carousel` | 住宿/目的地图片轮播 |
| ★★ | `Image` + LazyLoad | `FastImage` | 目的地封面图 / 酒店图片 |
| ★★ | 浏览器 Geolocation API | `expo-location` | 获取当前位置自动填充出发地 |
| ★★ | Push Notifications | `expo-notifications` / FCM | 航班变更提醒 / 值机提醒 |
| ★ | 系统日历集成 | `expo-calendar` | 将行程添加到系统日历（可选功能）|
| ★ | 系统分享 / `navigator.share` | `react-native-share` | 行程分享（富链接预览）|
| ★ | `ProgressBar` | `ProgressBar` | 搜索 loading / 预订处理中 |
| ★ | Empty 空状态 | 自定义 Empty | 无行程空状态 / 搜索无结果 |
| ★ | Grid / `WingBlank + Flex` | `FlatList`（numColumns=2）| 目的地图片 Grid（发现页）|

---

## Anti-Patterns

基于研究样本中观察到的设计错误：

- **出发地/目的地使用两个独立 TextInput，无互换按钮**：用户经常需要查「去程」和「回程」，没有互换按钮时需要手动清除再重填，操作繁琐。→ 正确做法：出发地-目的地排列为横向 Pill 组合，中间放置 ⇄ 互换 Button（点击时动画交换两个值），这是 Omio / Tripsy 的行业标准（所有旅行搜索 App 均有此交互）。

- **日期选择使用系统默认 DatePicker 下拉，而非内联日历**：系统默认 DatePicker 在移动端交互体验差，且不支持直观的范围高亮选择。→ 正确做法：Bottom Sheet 内弹出内联日历组件，支持出发/返回日期范围高亮（选中区间着色），视觉直观；单日期选择也更清晰（Tripsy / FocusFlight 均如此）。

- **搜索结果不支持实时过滤，只能重新搜索**：用户想从「经济舱」切换到「商务舱」，或从「带早餐」切换到「不含早餐」，必须重新填写搜索表单发起搜索，流程过重。→ 正确做法：搜索结果页顶部提供横向 Filter Chips（直飞/经停 / 座位等级 / 时间区间），点击即时过滤结果列表（无需重新搜索），Filter Sheet 提供更完整的多维度筛选（Omio 模式）。

- **预订成功后不提供数字凭证保存**：移动端用户期待在 App 或钱包中管理登机牌/车票（支持离线查看），缺少此功能使 App 体验显著落后于竞品。→ 正确做法：预订确认页必须提供「保存数字凭证」选项（生成离线可访问的 QR Code / 下载 PDF / 添加到 Apple Wallet），让用户无需网络即可在机场出示票据。

- **行程事件仅用普通 List 展示，无时间轴 Timeline 视觉**：行程内所有事件平铺为普通列表，用户无法直观感知「一天内」各事件的时间顺序和间隔，与旅行「按时间安排」的心智模型冲突。→ 正确做法：行程详情按天（Day 1 / Day 2）分 Section，每 Section 内事件按时间排序，左侧时间轴连接线可选（Tripsy 样式），每个事件行显示时间 + 类型图标 + 事件名称（Timeline 而非纯 List）。

- **地图与列表结果完全分离（两个独立页面切换）**：用户需要分别进入地图页和列表页对比，无法同时感知地理位置和价格信息。→ 正确做法：地图视图（上 55%）+ 可上划的列表 Carousel / List（下 45%），两者联动：点击价格 Marker 高亮对应列表卡片，滑动列表卡片相应 Marker 聚焦（Google Maps 酒店搜索的双视图联动模式）。

- **离线状态下无法查看已有行程和票务信息**：用户在飞机上 / 无信号地区打开 App 时，显示错误页面而非缓存数据，旅行关键时刻失效。→ 正确做法：已预订的行程数据和票务信息（登机牌/车票 QR Code）必须缓存本地（AsyncStorage / SQLite / realm），无网络时可以正常查看；行程 Timeline 和票据支持完全离线展示（Tripsy 的离线优先设计）。
