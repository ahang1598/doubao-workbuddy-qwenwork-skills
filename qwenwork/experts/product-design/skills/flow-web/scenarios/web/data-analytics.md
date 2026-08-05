# Scenario: Data Analytics / BI（数据分析 / 商业智能）

> **研究来源**：基于对 Shopify、Zendesk、GlossGenius、TravelPerk、Mercury、n8n、Maze、Chargetrip、Dub、Stellate 等 10+ 个真实产品 flow 的横向分析抽象，不代表任何单一产品的具体实现。

---

## Identity

**Platform**: Web  
**Definition**: 面向数据消费者（分析师、管理者、运营人员）的分析型产品，核心目标是让用户通过交互式 Dashboard、维度钻取和报表导出理解业务数据、发现规律、驱动决策。  
**Canonical Examples**: Mixpanel、Tableau、Metabase  
**Not this scenario if**: 侧重数据输入和业务操作（改用 web/saas-management.md）；仅展示单一 KPI 摘要的 Widget（改用 saas-management Dashboard 区块）；以代码 / SQL 为主的数据工程工具（改用 web/developer-tools.md）。

---

## User Profile

| 维度 | 内容 |
|---|---|
| **主要角色** | 数据分析师（Analyst）/ 业务管理者（Business Manager）/ 运营专员（Operator） |
| **核心目标** | 快速了解业务状态 → 发现异常或趋势 → 钻取到维度细节 → 导出数据供外部分析 |
| **心智模型** | Excel / Google Analytics 用户：习惯时间维度切换、多维筛选、图表+表格结合；对数据实时性有期望 |
| **使用频率** | 高频日常（每日查看 Dashboard）+ 周期性深度分析（每周导出报表）|
| **决策模式** | 数据驱动：先定时间范围 → 对比基准 → 下钻维度 → 输出结论 |
| **容错期望** | 中：允许筛选条件复杂，但不接受数据错误或加载超时；期望操作可撤销（Undo）|

---

## IA Template

**导航模式**: 左侧 Sidebar（固定，一级导航）  
**理由**: BI 产品数据层级深，用户需在 Overview / Reports / Segments 之间频繁切换，Bottom Tab 容量不足，Top Nav 在宽屏下浪费空间。

**页面层级**: 3 级——Overview（聚合仪表盘）→ Dimension View（维度筛选视图）→ Detail / Export（明细或导出）

**权限角色**:  
- Viewer：只读 Dashboard，无法修改或导出  
- Analyst：可筛选、钻取、导出  
- Admin：可定制 Dashboard 结构、管理数据接入

**数据密度**: 高——KPI 卡片 Bento Grid + 图表 + 数据表格三层共存

**主要容器模式**:  
- 全页面：Dashboard 主视图、报表列表  
- 抽屉（Sheet）：复合筛选条件配置  
- 弹窗（Dialog）：导出配置、Dashboard 定制进入点  
- 分步向导：报表导出三段式（筛选 → 列选择 → 下载）

### 导航骨架图（ASCII）

```
┌─────────────────────────────────────────────────────────┐
│ Sidebar         │ Main Content Area                      │
│                 │                                        │
│ ○ Overview      │ [Time Range Picker]  [+ Filter]        │
│ ○ Reports       │ ┌──────┐ ┌──────┐ ┌──────┐           │
│ ○ Segments      │ │ KPI  │ │ KPI  │ │ KPI  │  ← 英雄指标│
│ ○ Exports       │ └──────┘ └──────┘ └──────┘           │
│ ─────           │ ┌──────────────┐ ┌──────┐             │
│ ○ Settings      │ │   Chart      │ │ KPI  │             │
│                 │ │              │ │      │             │
│                 │ └──────────────┘ └──────┘             │
│                 │ ┌────────────────────────────────┐    │
│                 │ │       Data Table               │    │
│                 │ │  [Sort] [Filter] [Export]       │    │
│                 │ └────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘

层级导航：
Overview → [维度筛选] → Dimension View（页内切换，非跳转）
Overview → [点击行] → Detail Page → [导出] → Export Modal
Reports → [选报表] → Report Config → Download
```

---

### 图 2：关键状态对比图（Key State Variations）

```
左：Dashboard 正常态（有数据 + 图表）         右：数据源未接入空状态（引导配置）

┌────────────────────────────────────┐  ┌────────────────────────────────────┐
│ [Last 30 days ▾]   [+ Filter]      │  │ [Last 30 days ▾]   [+ Filter]      │
├────────────────────────────────────┤  ├────────────────────────────────────┤
│ ┌──────────┐ ┌──────────┐         │  │                                    │
│ │ Revenue  │ │ Orders   │         │  │                                    │
│ │ $48,320  │ │  1,284   │         │  │         📊                         │
│ └──────────┘ └──────────┘         │  │   No data connected yet.           │
│ ┌──────────────────────────────┐  │  │   Connect a data source to start   │
│ │  ▁▃▅▆█▆▅▃▁  Revenue Trend   │  │  │   seeing your analytics.           │
│ └──────────────────────────────┘  │  │                                    │
│ ┌─────────────────────────────┐   │  │   [Connect Data Source]            │
│ │ Channel  Revenue  Conv%     │   │  │                                    │
│ │ Organic  $21,400  3.2%      │   │  │                                    │
│ │ Paid     $18,200  2.8%      │   │  │                                    │
│ └─────────────────────────────┘   │  │                                    │
└────────────────────────────────────┘  └────────────────────────────────────┘
```

---

### 图 3：覆层层级图（Overlay Hierarchy）

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Logo  [Cmd+K]                                           [Avatar ▾]       │ ← Top Bar（z-100）
├───────────┬──────────────────────────────────────────────────────────────┤
│           │  Overview  [Last 30 days ▾]  [+ Filter]   [Customize ✎]      │
│ Nav       ├──────────────────────────────────────────────────────────────┤
│           │  ┌──────────┐ ┌──────────┐ ┌──────────┐                      │
│ ● Overview│  │ Revenue  │ │ Orders   │ │ Conv%    │    ┌───────────────┐  │
│   Reports │  └──────────┘ └──────────┘ └──────────┘    │ Filter Sheet  │  │
│   Segments│  ┌──────────────────────────┐               │（右侧滑入）    │  │
│   Exports │  │  Revenue Trend Chart     │               │ z-index: 200  │  │
│           │  └──────────────────────────┘               │               │  │
│           │  ┌──────────────────────────┐               │ Date Range ▾  │  │
│           │  │  Data Table             │               │ Type       ▾  │  │
│           │  │  Channel Revenue Conv%  │               │ Dimension  ▾  │  │
│           │  └──────────────────────────┘               │ [Apply]       │  │
│           │                                             └───────────────┘  │
│           │  ┌──────────────────────────────────────────────────────────┐ │
│           │  │  Export Modal（中）3-Step Wizard    z-index: 300          │ │
│           │  │  Step 1: 时间范围 → Step 2: 列选择 → Step 3: 格式下载    │ │
│           │  │  [Cancel]                                    [Next →]    │ │
│           │  └──────────────────────────────────────────────────────────┘ │
│           │    ▲ 触发: 点击「Download Report」                             │
│           │                                                                │
│           │  ┌── Edit Mode Toolbar ─────────────────────────────────────┐ │
│           │  │  Editing Overview  [Reset to Default]  [Discard]  [Save] │ │ ← z-150（Edit 工具栏）
│ ┌─────────┤  └──────────────────────────────────────────────────────────┘ │
│ │ Widget  │  ┌──────────────────────────────────────────────────────────┐ │
│ │ Library │  │  Dashboard Grid（Edit Mode，Widget 可拖拽排序）           │ │
│ │  Rail   │  │  ┌─────────────────┐  ┌───────────────────┐             │ │
│ │ z-150   │  │  │ Revenue     [×] │  │  Drop zone ░░░░░  │             │ │
│ │         │  │  └─────────────────┘  └───────────────────┘             │ │
│ └─────────┤  └──────────────────────────────────────────────────────────┘ │
│           │    ▲ 触发: 点击顶部 [Customize ✎] 按钮                        │
└───────────┴────────────────────────────────────────────────────────────────┘
  ┌──────────────────────────────────────────────────────┐
  │  ✓ Revenue card removed · Undo  [×]                  │  ← Toast（底部，z-400）
  └──────────────────────────────────────────────────────┘

触发关系说明:
- Filter Sheet（右）: 点击 [+ Filter] 触发，右侧滑入，z-200，主 Dashboard 仍可见
- Export Modal（中）: 点击「Download Report」触发，三段式向导，z-300，分步完成后自动关闭
- Edit Mode（全局）: 点击顶部 [Customize ✎] 触发，工具栏变化 + 左侧 Widget Library Rail 弹出（z-150），退出时需 Save/Discard
- Toast（底）: 移除 Widget、保存布局等操作的轻量反馈，z-400，3-5 秒消失
```

---

## 该场景独有的 IA/UX 决策

**1. 时间是第一优先级筛选器（Time as First-Class Filter）**  
用户心智是「先定时间，再看数据」。日期 picker 必须锚定在页面顶部，优先级高于所有维度筛选器。预设选项（Today / Last 7 days / This month / Custom）必须 1 步可达；Custom 模式需双日历 picker。改变时间 = 刷新全部数据，这是全局控件，而非单 widget 内部控件。

**2. 聚合→维度钻取是双层模型，在页内切换而非跳转（Aggregate-to-Dimension Drill-Down）**  
第一层显示全量聚合指标（All）；用户通过维度选择器（人员/来源/标签/状态）下钻后，全部 KPI 实时重算。导航行为是「视角切换」，不是跳转新页面。这与 SaaS 后台的「行→详情页」模式完全不同。

**3. Dashboard 定制需专用 Edit Mode，不可内联编辑（Dedicated Edit Mode）**  
View 模式和 Edit 模式必须明确分离：进入 Edit 时工具栏变化、左侧 Library Panel 出现，退出时有「Save / Discard」确认。用户在查看数据时不能误触发编辑行为。Edit Mode 支持：DnD 排序、Widget Library 添加、Reset to Default。

**4. 报表导出三段式 Modal（Configure → Select Columns → Download）**  
用户需要在下载前「预知文件内容」，三段流程是必要的认知步骤：  
- Step 1：时间范围 + 数据维度筛选  
- Step 2：列/字段选择（按类别分组 checkbox，含已选计数器如「64/80 selected」，有全选/全清快捷操作）  
- Step 3：格式选择（CSV / Excel）→ 下载触发 → Loading → Toast 确认  
不可简化为单一 Download 按钮，否则用户不知道文件包含哪些字段。

**5. 空状态必须回答「为什么空」并给出主动建议（Contextual Empty State）**  
BI 场景的空状态三种成因完全不同，UI 必须区分：  
- 筛选条件过严 → 建议「放宽时间范围」或「清除筛选」  
- 该时间段无数据 → 提示「数据生成周期」或「切换周期」  
- 数据源未接入 → 引导至数据接入设置  
通用的「No data found」不可接受。

---

## Canonical Flows

### Flow 1: View Dashboard with Time-Range Filtering（查看仪表盘 + 时间维度切换）

**在此场景的特殊性**: 时间筛选是全局控件（影响所有 widget），而非表格内的列排序；切换时间不跳转页面，而是整页数据重载。

**前置条件**: 用户已登录且具有 Viewer 以上角色；至少有一个数据源已完成接入（否则进入数据源空状态引导）
**若前置条件不满足**: 未接入数据源 → Dashboard 显示「Connect your data source to get started」+ [Connect Data Source] CTA；无 Viewer 权限 → 跳转登录或权限不足页

**Entry**: 用户从 Sidebar 点击「Analytics」或「Overview」

**Screens**:

```
Screen 1: Analytics 主仪表盘（默认时间：本月）
  主操作: 切换时间范围
  关键组件:
    - 顶部 Time Range Picker（pill 样式，显示当前选中范围）
    - Hero KPI 卡（最大字号，如「本月总收入」）
    - KPI Bento Grid（2-3 列次级指标卡）
    - 折线图 / 柱状图（趋势）
    - 数据表格（可展开）
  → 点击时间 pill: Screen 2
  → 点击维度筛选: Flow 2

Screen 2: 时间范围选择器（Dropdown / Popover）
  主操作: 选择预设 or 自定义时间
  关键组件:
    - Preset List（Today / Last 7 days / Last 30 days / This quarter / YTD / Custom）
    - Custom 模式：双日历 picker（Start date + End date）
    - 「Currently viewing」说明文字
    - Apply / Cancel 按钮
  → 选择预设: 直接应用，返回 Screen 1（数据刷新）
  → 选择 Custom + Apply: 返回 Screen 1（数据刷新）
  → Cancel: 返回 Screen 1（无变化）

Screen 3: 刷新后的仪表盘（新时间范围）
  主操作: 继续分析 or 下钻维度
  关键组件:
    - Time Range Pill 更新为新选择
    - 所有 KPI 卡数值重算（含对比基准线，如 vs. 上期）
    - 图表 X 轴重绘
    - 数据表格重新排序
```

**Exit State**: 仪表盘显示新时间范围数据，Time Range Pill 反映当前选择  
**Empty State**: 该时间段无数据 → 显示「该时段暂无数据，建议查看过去 30 天」+ 快速切换链接

---

### Flow 2: Dimension Drill-Down Analysis（维度钻取分析）

**在此场景的特殊性**: 这是「视角切换」而非「导航跳转」——用户不离开 Dashboard 页面，而是通过维度选择器切换数据视角，所有 KPI 实时重算。

**前置条件**: 用户为 Analyst 以上角色（Viewer 维度选择器 disabled）；当前 Dashboard 已有聚合数据；时间范围内有可按维度拆分的数据记录
**若前置条件不满足**: Viewer 角色 → 维度选择器 disabled + Tooltip「需要 Analyst 权限才能筛选」；时间段内无维度数据 → 选择器可用但切换后显示维度空状态（不禁用入口）

**Entry**: 用户在 Dashboard 上点击维度选择器（如「All Staff」dropdown）

**Screens**:

```
Screen 1: 聚合总览（All 状态）
  主操作: 打开维度选择器
  关键组件:
    - 维度选择器 Dropdown（显示「All [维度名]」，如「All Staff / All Sources」）
    - Hero KPI（全量聚合值）
    - KPI Bento Grid（次级指标）
    - 对比基准线（如团队平均值、上期值）
  → 点击维度 Dropdown: Screen 2

Screen 2: 维度选择器（Dropdown 展开）
  主操作: 选择特定维度成员
  关键组件:
    - 快速搜索 Input（过滤列表）
    - 维度列表（含头像/Icon + 名称 + 摘要数值）
    - 当前选中项 Checkmark
    - 「All [维度名]」重置选项
  → 选择某维度成员: Screen 3
  → 选择「All」: 返回 Screen 1

Screen 3: 维度过滤后的仪表盘
  主操作: 查看专项 KPI 或进一步钻取明细
  关键组件:
    - 维度筛选标签（显示当前选中，可点击 × 清除）
    - 全部 KPI 卡实时重算（仅显示该维度数据）
    - 对比基准线（如与团队均值对比）
    - 「View Details →」入口
  → 点击「View Details」: Screen 4
  → 点击 × 清除筛选: 返回 Screen 1

Screen 4: 维度明细列表（Detail Table）
  主操作: 查看行级记录，排序
  关键组件:
    - 面包屑导航（Overview > [维度名]）
    - 数据表格（可多列排序，行级可展开）
    - 行级操作（如 Export Row、View Profile）
    - 分页 Pagination
  → 面包屑返回: Screen 1（Overview）
  → 导出: 触发 Flow 3
```

**Exit State**: 用户获得维度专项数据，可继续分析或导出  
**Empty State**: 该维度无数据 → 「[维度名] 在当前时间范围内无数据，建议扩大时间范围」

---

### Flow 3: Custom Report Export（自定义报表导出）

**在此场景的特殊性**: 导出不是简单的下载按钮——用户需经历「配置 → 列选择 → 格式选择」三段，在下载前预知文件内容。这是 BI 场景独有的导出 UX，不可简化。

**前置条件**: 用户为 Analyst 以上角色（Viewer 无导出权限）；所选时间范围内至少有 1 条数据记录
**若前置条件不满足**: Viewer 角色 → 「Download Report」按钮 disabled + Tooltip「需要 Analyst 权限才能导出」；无数据 → Step 3 下载按钮 disabled，显示「当前筛选条件下无数据，请返回调整」

**Entry**: 用户从 Sidebar 点击「Reports」，或在 Dashboard 点击「Download Report」

**Screens**:

```
Screen 1: Reporting 概览页
  主操作: 选择报表类型，进入导出配置
  关键组件:
    - 报表类型卡片列表（如 Revenue / Staff Performance / Customer Activity）
    - 每张卡片含：报表名、字段数、上次导出时间
    - 右上角「Download Report」主 CTA
    - 顶部时间 Dropdown（影响所有报表的默认时间范围）
  → 点击报表卡片或「Download Report」: Screen 2

Screen 2: 导出配置 Modal — Step 1（时间与筛选）
  主操作: 设定导出数据的范围
  关键组件:
    - Modal 标题（「Export [报表名]」）
    - Step 指示器（1 of 3）
    - 时间范围选择器（继承当前 Dashboard 时间，可修改）
    - 数据基准选择（如「按发生日期」vs「按结算日期」）
    - + Add Filter 展开复合筛选
    - Next → 按钮
  → Next: Screen 3
  → Cancel: 关闭 Modal

Screen 3: 导出配置 Modal — Step 2（列/字段选择）
  主操作: 精选需要导出的数据字段
  关键组件:
    - Step 指示器（2 of 3）
    - 分组 Checkbox 列表（按字段类别折叠，如 Basic Info / Financial / Custom Fields）
    - 已选计数器（如「64 / 80 selected」，实时更新）
    - 全选 / 全清快捷操作
    - 字段搜索 Input
    - ← Back / Next → 按钮
  → Next: Screen 4
  → Back: 返回 Screen 2

Screen 4: 导出配置 Modal — Step 3（格式选择与下载）
  主操作: 选择格式，触发文件生成
  关键组件:
    - Step 指示器（3 of 3）
    - 格式选择（Download CSV / Download Excel，Radio 或双按钮）
    - 数据预览摘要（「将导出 1,234 行 × 64 列」）
    - 下载触发按钮（点击后变为 Loading spinner）
    - ← Back 按钮
  → 点击下载: 文件生成 → Loading → Toast 确认（「✓ 报表已生成，正在下载」）
  → Back: 返回 Screen 3
```

**Exit State**: 文件下载到本地，Toast 显示「报表已生成」（含 Undo 选项，3秒消失）  
**Empty State**: 筛选条件导致 0 行数据 → Step 3 禁用下载按钮，显示「当前筛选条件下无数据，请返回调整」

---

---

### Flow 4: Dashboard 定制（Edit Mode）

**在此场景的特殊性**: BI 场景的 Dashboard 定制与 SaaS 后台设置完全不同——用户不是修改系统配置，而是个性化数据视图的空间布局。关键模式：View/Edit 双模式严格分离（防止浏览数据时误触发编辑）；左侧 Widget Library Rail 提供可添加的指标卡；DnD 排序在 Grid 内进行；移除 Widget 有即时 Undo Toast（误删指标的代价高）。Shopify（flow_id 5425）是 10 屏完整参考：进入 Customize → 从左侧 Library 添加 → DnD 排序 → Save 保存。Mercury（flow_id 11030）是轻量版：Widget 右上角「···」菜单 → Hide Widget → Snackbar Undo。

**行业共识**: 出现在 Shopify（flow_id 5425）、Mercury（flow_id 11030）、Zendesk（flow_id 1390）等多个样本中。

**前置条件**: 当前用户为 Admin 角色（Viewer 和 Analyst 无法修改 Dashboard 布局）；Dashboard 已完成初始数据接入（非空状态）；当前未处于数据加载中
**若前置条件不满足**: Viewer/Analyst 角色 → 顶部「Customize」按钮不显示或 disabled + Tooltip「需要 Admin 权限」；Dashboard 空状态（无数据源）→「Customize」按钮 disabled（无内容可编辑）

**Entry**: Dashboard Overview 右上角「Customize ✎」按钮

```text
Screen 1: Dashboard Overview（View 模式）
  主操作: 点击「Customize ✎」进入编辑
  关键组件: 顶部工具栏（Time Range Picker + [+ Filter] + [Customize ✎]）
            KPI 卡 Grid、折线图、数据表格（均为只读态）
  → 点击「Customize ✎」: Screen 2

Screen 2: Edit Mode 激活
  主操作: 查看可用操作 — 移除 Widget、从 Library 添加、拖拽排序
  关键组件:
    - Edit Mode 工具栏（替换顶部，含「Reset to Default」「Discard」「Save」）
    - 左侧 Widget Library Rail（滑入，宽约 240px，按类别分组列出未添加的 Metric Cards）
    - 现有 Widget 右上角出现「×」移除按钮和拖拽 Handle（⠿）
    - Dashboard Grid 背景显示 Drop Zone（虚线边框提示可放置区域）
  → 点击现有 Widget「×」: 即时移除 + Toast「[Widget 名] 已移除 · Undo」（5秒）
  → 从 Library 拖拽或点击「+」: Screen 3
  → 在 Grid 内拖拽 Widget Handle: Widget 跟随移动，放置后 Grid 重排
  → 点击「Save」或「Discard」: Screen 4

Screen 3: 从 Widget Library 添加 Widget
  主操作: 将 Metric Card 添加到 Dashboard Grid
  关键组件:
    - Widget Library Rail（分组：Revenue / Customer / Operations / Custom）
    - Grid 高亮可用 Drop Zone（虚线 + 「拖至此处」提示）
    - Toast「[Widget 名] 已添加」（3秒，含 Undo）
  → 放置成功: Widget 出现在 Grid，Library 中该项变为「已添加」disabled 态
  → 继续操作: 回到 Screen 2（可继续移除/排序）

Screen 4: Save / Discard 确认
  主操作: 保存定制布局或放弃更改
  关键组件:
    - 点击「Save」→ Loading spinner → 自动退出 Edit Mode → Toast「Dashboard 已更新」
    - 点击「Discard」→ AlertDialog「放弃所有更改？此操作不可撤销」
      - [确认放弃]: 还原到编辑前布局 → 退出 Edit Mode
      - [继续编辑]: 关闭 AlertDialog，保持 Edit Mode
    - 点击「Reset to Default」→ AlertDialog「将布局还原为系统默认？」→ 确认后重置并 Save
```

**Exit State**:

- ✅ 保存成功：Toast「Dashboard 已更新」，退出 Edit Mode，新布局立即生效
- ↩ Discard：AlertDialog 确认后还原布局，退出 Edit Mode，无变更
- 🔄 Reset to Default：AlertDialog 确认 → 还原系统默认布局 → Toast「已还原为默认布局」

---

## Component Kit

按使用频率排序，标注用途：

| 功能概念 | 具体用途 |
|---|---|
| 内容卡片 | KPI 卡片容器（Hero 指标 + 次级指标）|
| 日期范围选择 | 时间范围双日历选择器 |
| 选择下拉 | 维度选择器（人员/标签/来源）|
| 高级数据表格 | 数据明细表格（含排序、分页）|
| 模态对话框 | 导出配置三段式 Modal |
| 多选框 | 字段列表多选（含全选逻辑）|
| 进度条 + 状态标签 | 已选计数器（64/80 selected）|
| 面包屑导航 | 维度钻取导航（Overview > 维度名）|
| 侧边面板/抽屉 | 左侧可收起复合筛选面板 |
| 加载骨架屏 | 数据加载态（防止 Layout Shift）|
| 操作通知（Toast） | 操作确认（导出成功 / Undo）|
| 标签页切换 | Overview / Reports / Segments 切换 |
| 分隔线 | 筛选面板分组分割线 |

---

## Anti-Patterns

> 该场景中真实存在的常见设计错误，基于研究观察。

- **时间筛选放在 Widget 内部**：每个图表各自有独立的时间选择器 → 全局操作变成重复劳动。正确做法：时间是全局控件，锚定页面顶部，统一驱动所有数据刷新。

- **钻取用跳转新页替代视角切换**：点击维度后跳转到新 URL，用户失去上下文，无法快速对比 → 维度钻取应在当前 Dashboard 页内通过选择器切换，保持全局指标可见。

- **导出简化为单一下载按钮**：直接触发下载，用户不知道文件包含哪些字段、多少行 → 必须有「列选择」步骤，让用户在下载前预知内容。

- **空状态使用通用文案**：「No data found」对用户毫无帮助 → 必须区分原因（条件过严/时间无数据/数据未接入）并给出主动操作建议。

- **Dashboard 支持内联编辑（无 Edit Mode）**：用户在查看数据时意外拖动 Widget → 必须有明确的 Edit Mode 入口和退出确认，View 和 Edit 状态在视觉上须可区分。
