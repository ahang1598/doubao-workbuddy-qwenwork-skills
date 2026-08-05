# Scenario: 金融科技 / Fintech Web Platform

## Identity
**Platform**: Web
**Definition**: 面向个人或企业用户的 Web 端金融服务平台，核心功能涵盖账户余额查看、货币转账、交易记录管理与对账单导出
**Canonical Examples**: Wise（国际汇款）、Mercury（企业银行）、Copperx（加密支付）
**Not this scenario if**:
- 纯加密货币交易所（价格图表 + 挂单簿是核心，非转账向导）
- 保险/理财产品配置工具（无交易记录检索核心需求）
- 内部财务报销系统（审批流为主，见 internal-ops.md）

---

## User Profile

| 维度 | 内容 |
|---|---|
| 主要角色 | 个人用户（汇款/收款）/ 企业财务人员（账单管理 + 对账）|
| 核心目标 | 安全准确地发出/接收资金，并能随时查阅和导出交易记录 |
| 心智模型 | 「网银」— 用户对操作步骤、确认提示、二次验证有强烈预期；对错误操作零容忍 |
| 使用频率 | 偶尔到中频（周 1-3 次），企业财务月末高频集中 |
| 决策模式 | 任务驱动（我要发一笔钱 / 我要查一条记录），不探索 |

---

## IA Template

**导航模式**: Sidebar（左侧固定，约 1/6 宽度）+ 顶部 Topbar（账户切换 + 通知 + 用户头像）
**页面层级**: Dashboard → 功能模块（Send / Activity / Wallet）→ 操作向导（多步 Form）→ 成功确认
**权限角色**: 单角色（个人）/ 双角色（Owner + Team Member，控制转账限额与审批权）
**数据密度**: 中（交易列表为主，卡片 + 行列表混合；无超高密度表格）
**主要容器模式**: 多步向导（Send Flow）+ 右侧 Side Sheet（Filter Panel）+ Modal（Confirm / Export）

### 导航骨架图（ASCII）

```
┌─────────────┬──────────────────────────────────────────────┐
│  SIDEBAR    │  TOPBAR: Logo · 账户选择下拉 · 通知 · Avatar │
│             ├──────────────────────────────────────────────┤
│ ● Dashboard │                                              │
│   Send      │  [主内容区]                                  │
│   Wallets   │                                              │
│   Activity  │  Dashboard:                                  │
│   Settings  │  ┌──────────────────────────────────────┐   │
│             │  │ 余额卡：总额 · 货币 · 变化           │   │
│             │  │ 快捷操作：[Send] [Add] [Receive]     │   │
│             │  └──────────────────────────────────────┘   │
│             │  最近交易列表（3-5 行预览）                  │
│             │                                              │
│             │  Activity（/transactions）:                  │
│             │  搜索栏 · Filter 图标 · Download 图标         │
│             │  ┌ Active Filter Chips ─────────────────┐   │
│             │  │ 交易行 × N（按日期分组）             │   │
│             │  └──────────────────────────────────────┘   │
│             │                              [Side Sheet →] │
└─────────────┴──────────────────────────────────────────────┘
```

---

#### 图 2：关键状态对比图（Key State Variations）

```
左：Dashboard 正常态（有余额 + 交易）       右：新账户空状态（激活引导）

┌────────────────────────────────────┐  ┌────────────────────────────────────┐
│ TOPBAR: Acme Corp ▾  🔔  Avatar   │  │ TOPBAR: Alex ▾  🔔  Avatar        │
├────────────────────────────────────┤  ├────────────────────────────────────┤
│ ┌──────────────────────────────┐   │  │ ┌──────────────────────────────┐   │
│ │ Total Balance                │   │  │ │ Total Balance                │   │
│ │ $12,480.52  USD              │   │  │ │ $0.00  USD                   │   │
│ │ ↑ +$1,200 this month        │   │  │ │ Get started with your wallet │   │
│ └──────────────────────────────┘   │  │ └──────────────────────────────┘   │
│ [Send] [Add Money] [Receive]       │  │                                    │
│                                    │  │         [空态插图]                 │
│ Recent Transactions                │  │                                    │
│ ── Apr 26 ──────────────────────  │  │  No transactions yet.              │
│  🏢 Shopify  +$4,200.00  ✓        │  │  Add money to get started.        │
│  🧑 Alice Wu  -$350.00   ✓        │  │                                    │
│ ── Apr 24 ──────────────────────  │  │  [Add Money]  [Receive Payment]   │
│  🌐 Wise     -$820.00   ✓        │  │                                    │
└────────────────────────────────────┘  └────────────────────────────────────┘
```

---

#### 图 3：覆层层级图（Overlay Hierarchy）

```
┌──────────────────────────────────────────────────────────────────────────┐
│  TOPBAR: Acme Corp ▾  [Notifications]  Avatar                            │ ← z-100
├─────────────┬────────────────────────────────────────────────────────────┤
│  SIDEBAR    │  Activity  [Search...]  [Filters ⊟]  [Download ↓]          │
│             │  ─────────────────────────────────────────────────────── │
│ ● Dashboard │  [USD ×][Completed ×][Apr 2025 ×] [Clear All]              │
│   Send      │                                              ┌────────────┐ │
│   Wallets   │  ── Apr 26 ───────────────────────────────  │ Filter     │ │
│   Activity  │   Shopify  +$4,200   ✓ Completed           │ Side Sheet │ │
│   Settings  │   Alice Wu  -$350   ✓ Completed            │（右侧滑入） │ │
│             │  ── Apr 24 ─────────────────────────────── │ z-index:200│ │
│             │   Wise  -$820  ⏳ Pending                   │            │ │
│             │                                              │ Date Range │ │
│             │                                              │ Type  ▾    │ │
│             │  ┌────────────────────────────────────┐     │ Status ▾   │ │
│             │  │    Confirm Modal（中）z-index: 300  │     │ Currency ▾ │ │
│             │  │  Send $350.00 to Alice Wu?         │     │[Apply]     │ │
│             │  │  Rate: 1 USD = 0.92 EUR            │     └────────────┘ │
│             │  │  Fee: $2.50  · Total: $352.50      │        ▲ 触发:     │
│             │  │  [Cancel]        [Confirm Send]    │     点击 Filters   │
│             │  └────────────────────────────────────┘                    │
│             │         ▲ 触发：转账向导 Screen 5 提交前弹出               │
│             │                                                             │
│             │  ┌────────────────────────────────────┐                    │
│             │  │    Export Modal（中）z-index: 300   │                    │
│             │  │  Date Range: [Last 30 Days ▾]     │                    │
│             │  │  Type: [All Transactions ▾]       │                    │
│             │  │  [Download PDF]  [Download CSV]   │                    │
│             │  └────────────────────────────────────┘                    │
│             │         ▲ 触发：点击 Download → Download Statement          │
└─────────────┴────────────────────────────────────────────────────────────┘
  ┌─────────────────────────────────────────────────────┐
  │  ✓ Your statement is being downloaded   [×]          │  ← Toast（底部，z-400）
  └─────────────────────────────────────────────────────┘
  ▲ 触发：导出成功 / 转账成功 / 操作确认，3-5 秒自动消失

触发关系说明:
- Filter Side Sheet（右）: 点击 Filters 图标触发，右侧滑入，z-200，主列表半透明可见
- Confirm Modal（中）: 转账向导最终 Screen 提交前触发，居中弹出，z-300，阻断操作
- Export Modal（中）: 点击 Download Statement 触发，居中弹出，z-300，选完格式后自动关闭
- Toast（底）: 导出成功、转账成功等轻量反馈，z-400，3-5 秒自动消失
```

---

## 该场景独有的 IA/UX 决策

1. **双币种并列显示**：转账金额输入区同时展示「我发送」和「对方收到」两个数值，实时联动更新，下方展示汇率 + 手续费明细 — 金融转账最高风险点是金额错误，双币可见性让用户在提交前完成心理核验

2. **付款类型前置声明**：用户在提交前须明确选择「商品与服务」或「亲友转账」，不同选项对应不同费率和买家保护策略，提前声明确保合规并让用户知情

3. **过滤面板用 Side Sheet 而非弹层**：交易历史多维过滤采用从右滑入的 Panel，主列表仍可见背景 — 允许用户在配置过滤条件时参考已有交易上下文，降低「过滤后意外空结果」的认知风险

4. **空状态即激活引导**：余额为零或无交易时，界面搭配插画 + 明确 CTA（「Add」/「Receive」/「Deposit」），将空状态转化为首次存款的转化节点

5. **定期付款内嵌在确认步骤**：Mercury 的「Recurring toggle」内嵌于支付确认屏，用户无需跳转额外页面即可设置重复规则 + 截止条件，并实时预览未来付款日期列表 — B2B 场景定期账单高频，内嵌降低功能发现成本

---

## Canonical Flows

> 以下 flow 基于对真实产品的横向分析抽象而来，代表该场景的高频用户任务。

### Flow 1: 发起货币转账

**在此场景的特殊性**: 相较通用表单提交，Web 端转账强制插入「安全验证（SMS/2FA）」和「资金来源选择」两个中间步骤；金额输入屏必须同时展示发送金额和接收金额（双币视图），且在 Confirm 屏前有独立 Modal 兜底防误操作

**前置条件**: 用户已登录；账户内有可用余额或已绑定付款方式（银行卡/钱包）；2FA 已启用（部分平台强制）
**若前置条件不满足**: 余额不足 → 在资金来源选择步骤显示「Insufficient balance」提示，需先 Add Money；无付款方式 → 跳转添加付款方式向导

**Entry**: Dashboard 余额区正下方的「Send / Transfer」按钮，或顶部导航「Send and Request」标签

**Screens**:

```
Screen 1: 收款方选择
  主操作: 从联系人搜索或列表选择收款人
  关键组件: 搜索输入框（支持邮件/用户名/手机号）、最近联系人列表（头像 + 名称）
  → 选择联系人: Screen 2
  → 取消: 返回 Dashboard

Screen 2: 金额输入 + 货币选择
  主操作: 输入发送金额，选择发送货币和接收货币
  关键组件: 双栏金额卡（You Send / Recipient Gets 实时联动）、货币选择器 Modal、
             汇率 + 手续费说明文字、备注可选输入框、Next 按钮
  → Next: Screen 3
  → 返回: Screen 1

Screen 3: 安全验证
  主操作: 输入 SMS 验证码或完成 2FA
  关键组件: 验证方式说明、6位数字验证码输入框、「重新发送」链接、Verify 按钮
  → 验证成功: Screen 4
  → 验证失败: 停留 + 内联错误提示

Screen 4: 资金来源 + 付款类型
  主操作: 选择扣款账户/卡，确认付款性质
  关键组件: 资金来源 Select（银行卡列表）、付款类型单选卡（商品服务/亲友）、
             费用汇总（Fee / Total）、Continue 按钮
  → Continue: Screen 5
  → 返回修改金额: Screen 2

Screen 5: 确认 Modal
  主操作: 最终确认并提交
  关键组件: Confirm Modal（金额 + 收款方 + 费用摘要）、Send 主按钮、Cancel 链接
  → 提交成功: Screen 6
  → Cancel: 关闭 Modal 回到 Screen 4

Screen 6: 转账成功
  主操作: 查看确认摘要，选择下一步
  关键组件: 成功状态文案（「You've sent X to Y」）、「Send More」CTA、「View Summary」链接
  → 结束
```

**Exit State**: 成功页显示转账金额、收款方、系统通知确认文案，并提供「再次发款」和「查看摘要」两个出口
**Empty State**: 联系人列表为空时展示「没有联系人」+ 「通过邮件添加」CTA；资金来源为空时弹出「添加付款方式」引导向导

---

### Flow 2: 过滤与检索交易记录

**在此场景的特殊性**: Web 端采用右侧滑出 Side Sheet（而非 Modal）承载多维过滤，主内容仍可见背景；已应用的过滤以可移除 Chip 形式持续展示在列表上方，支持逐条移除；关键词搜索与条件过滤并行存在两条独立路径

**前置条件**: 用户已登录；Activity 页面已加载（无论是否有交易记录）
**若前置条件不满足**: 无（任何已登录用户均可进入 Activity 页并使用过滤功能，空账户显示空状态而非禁用过滤）

**Entry**: 进入「Activity / Transactions」页面，点击「Filters」图标或在搜索栏输入关键词

**Screens**:

```
Screen 1: 交易列表（默认态）
  主操作: 浏览交易记录，或发起搜索/过滤
  关键组件: 搜索栏（关键词/金额/参考号）、日期快速 Pill（默认近90天）、
             Filter 图标、Download 图标、按日期分组的交易行（头像 + 名称 + 金额 + 状态）
  → 点击 Filter 图标: Screen 2（Side Sheet 滑入）
  → 输入搜索词: Screen 1 内容实时过滤
  → 点击交易行: 交易详情页（独立路径）

Screen 2: 过滤面板（右侧 Side Sheet，背景列表半透明可见）
  主操作: 配置过滤维度
  关键组件: 日期范围预设下拉（近7天/近30天/近90天/自定义）、自定义日期双 Date Picker、
             交易类型多选、状态下拉（Completed/Pending/Failed）、货币下拉、
             「Apply Filters」主按钮、「Clear All」链接
  → Apply Filters: Screen 3
  → 点击背景 / 关闭: 返回 Screen 1（无变更）

Screen 3: 过滤结果列表
  主操作: 查看匹配结果，按需移除过滤条件
  关键组件: Active Filter Chips 行（每个 Chip 右侧有 × 可移除单项）、
             匹配交易列表（或空状态）、Download 按钮
  → 有结果: 展示交易列表，用户可继续浏览
  → 无结果: Screen 4

Screen 4: 空结果状态
  主操作: 调整或清除过滤条件
  关键组件: 「No results」插画 + 说明文案、「Try a new search」提示、「Clear Filters」链接
  → Clear Filters: 返回 Screen 1（默认态）
```

**Exit State**: 过滤后的交易列表，Active Filter Chips 持续可见，用户可逐条移除维度缩窄条件
**Empty State**: 「No transactions found」+ 「Try changing or clearing your filters」+ 「Clear Filters」按钮

---

### Flow 3: 导出交易对账单

**在此场景的特殊性**: 金融 Web 平台特有的合规需求场景，用户需为会计/税务生成格式化报告；Modal 同时提供 PDF（人类可读）和 CSV（可处理）双格式，并支持按交易类型细分（All / Deposits / Send / Withdrawals），而非仅按日期范围

**前置条件**: 用户已登录；所选时间范围内有至少 1 条交易记录
**若前置条件不满足**: 所选时间段内无交易 → Modal 内「No transactions in this period」提示，两个下载按钮禁用

**Entry**: 交易列表区域右上角的「Actions / ⚙」菜单 → 选择「Download Statement」

**Screens**:

```
Screen 1: 交易列表（带操作入口）
  主操作: 找到并触发导出入口
  关键组件: 交易列表主体、列表顶部右上角「Actions」菜单图标、菜单项「Download Statement」
  → 点击 Download Statement: Screen 2（Modal 弹出）

Screen 2: 对账单配置 Modal
  主操作: 选择时间范围和交易类型，点击导出格式按钮
  关键组件: 日期范围单选（Today / 本月 / 近7天 / 近30天 / 上月 / 自定义）、
             交易类型单选（All / Deposits / Send / Offramps）、
             双导出按钮并排（Download PDF 主 / Download CSV 次）、Cancel 链接
  → Download PDF 或 Download CSV: Screen 3

Screen 3: 下载成功反馈
  主操作: 文件开始下载，用户返回正常操作
  关键组件: 成功 Toast（「Your statement is being downloaded」，3秒自动消失）、
             Modal 自动关闭
  → 结束（回到 Screen 1）
```

**Exit State**: 浏览器触发文件下载，Toast 确认「下载已发起」，Modal 关闭，用户回到交易列表
**Empty State**: 所选时间范围内无交易时，Modal 内提示「No transactions in this period」并禁用两个下载按钮

---

### Flow 4: 转账 Pending 超时处理

**在此场景的特殊性**: 金融转账「Pending 超时」是电商无法复刻的场景——跨境汇款可能因银行处理延迟、合规审查、收款方账户问题而停留在 Pending 状态数小时乃至数天。与卡被拒的即时错误不同，超时是一种「等待中的不确定」，UI 必须提供明确的状态说明、预期时间框架、联系支持入口，以及「继续等待 or 主动取消」两条出路，避免用户重复发送导致双重扣款。

**前置条件**: 用户已完成转账（Flow 1 成功提交），系统返回「Pending」状态；该笔转账超过平台正常处理时间（通常 24-48 小时），用户在 Activity 列表中观察到超时 Pending 状态
**若前置条件不满足**: 转账即时完成（Completed）→ 无需此 flow；转账立即失败（Failed）→ 走即时错误处理（非此 flow）

**Entry**: Activity 页面中看到「⏳ Pending」状态的交易行，点击进入交易详情

**Screens**:

```
Screen 1: Activity 列表（含 Pending 交易）
  视觉状态: Pending 行以橙色/黄色 Badge 标注「Pending」，与 Completed 绿色 Badge 形成对比
  关键组件:
    - 交易行: 收款方头像 + 名称 + 金额 + 「⏳ Pending」Badge（橙色）
    - 正常 Completed 行：绿色「✓ Completed」Badge 对比
    - 可选 Banner（若超时）: 顶部黄色 Info Banner「Your transfer to Alice is taking longer than expected」
  → 点击 Pending 交易行: Screen 2

Screen 2: 交易详情页（Pending 超时状态）
  视觉状态: 状态时间线停留在中间节点；超时时显示黄色警告提示块
  关键组件:
    - 交易摘要: 金额 + 收款方 + 发起时间 + 参考号（可复制）
    - 状态时间线:
        ✓ Initiated (Apr 25, 09:31)
        ✓ Processing
        ⏳ Awaiting Bank Confirmation  ← 停在此节点
        ○ Completed
    - 黄色警告块:「This transfer is taking longer than usual. Most transfers complete within 1-3 business days.」
    - 预期完成时间说明（若可估算）:「Expected by Apr 28」
    - 操作按钮区:
        [Contact Support]（主按钮，打开 Support Chat 或跳支持页）
        [Cancel Transfer]（次要按钮，仅在可取消状态下显示；不可取消则禁用 + Tooltip 说明）
  → 点击 Contact Support: Screen 3
  → 点击 Cancel Transfer: Screen 4
  → 点击返回: Screen 1

Screen 3: 联系支持（Support Chat / Help Center）
  视觉状态: 支持聊天侧边栏滑入，或跳转 Help Center 页（含预填参考号）
  关键组件:
    - 预填上下文: 「I have a question about transfer #REF-2847-X (Pending since Apr 25)」
    - 支持渠道选项: Live Chat（在线）/ Email（异步）/ Knowledge Base 链接
    - 常见问题快捷链接: 「Why is my transfer pending?」「How long do international transfers take?」
  → 用户与支持沟通后: 等待后端处理，返回 Screen 2 查看最新状态
  → 问题解决: 交易最终变为 Completed，Screen 2 状态更新

Screen 4: 取消确认 Modal
  视觉状态: 居中弹出确认 Modal，说明取消后资金退回时间
  关键组件:
    - Modal 标题: 「Cancel this transfer?」
    - 说明文案: 「The $350.00 will be returned to your USD Wallet within 1-3 business days.」
    - 警告: 「This action cannot be undone.」
    - [Keep Transfer]（次要，关闭 Modal）
    - [Yes, Cancel Transfer]（主按钮，红色或危险色调）
  → 点击 Yes, Cancel: Screen 5
  → 点击 Keep Transfer: 关闭 Modal，返回 Screen 2

Screen 5: 取消成功
  视觉状态: 交易详情页状态更新为「Cancelled」（灰色 Badge）；Toast 出现在底部
  关键组件:
    - 状态 Badge 变为「Cancelled」（灰色）
    - 底部 Toast: 「Transfer cancelled. Refund expected within 1-3 business days.」
    - 交易时间线末节点追加: ✗ Cancelled (Apr 27, 14:22)
    - 返回 Activity 列表链接
  → 返回 Activity: Screen 1（该笔交易行显示「Cancelled」Badge）
```

**Exit State**:

- 等待成功 → 交易详情状态更新为「Completed」，时间线全绿，用户收到通知
- 取消成功 → 交易状态变为「Cancelled」，Toast 提示退款时间，资金返回钱包
- 联系支持后继续等待 → 保持 Pending 状态，Support 后续处理

**Empty State**: N/A（此 flow 针对已存在的 Pending 交易，无空状态）

---

## Component Kit

按使用频率排序：

| 功能概念 | 具体用途 |
|---|---|
| 内容卡片 | 余额展示卡、快捷操作区 |
| 操作按钮 | Send/Add/Receive 快捷操作、表单提交 |
| 单行文本输入 | 金额输入、收款方搜索、备注输入 |
| 选择下拉 | 货币选择、资金来源选择、过滤维度 |
| 模态对话框 | 确认弹层、对账单配置 |
| 侧边面板/抽屉 | 右侧 Filter Panel |
| 状态标签 | Active Filter Chips（可移除标签）|
| 标签页切换 | 付款类型单选（商品服务/亲友）|
| 基础数据表格 | 交易记录列表（分组展示）|
| 操作通知（Toast）| 下载成功通知、操作反馈 |
| 日期范围选择 | 自定义日期范围配置 |
| 加载骨架屏 | 交易列表加载态 |
| 用户头像 | 联系人头像、收款方标识 |
| 分隔线 | 费用明细分隔线 |

---

## Anti-Patterns

> 该场景中真实存在的常见设计错误，基于研究观察。

- **单币种金额输入**: 只显示发送金额，不实时展示接收方到账金额 → 应采用双栏联动设计，让用户在输入阶段就能看到对方收到多少

- **过滤用全屏 Modal 覆盖列表**: 打开过滤后看不到交易列表背景，用户无法参考现有数据调整条件 → 应用右侧 Side Sheet，保持主内容半透明可见

- **对账单只支持单一格式**: 只能导出 PDF 或只能导出 CSV，无法满足「阅读」和「处理」两种使用场景 → 应在同一 Modal 内提供两个并排按钮

- **空交易列表仅显示文字提示**: 「No transactions yet」纯文字无操作入口，用户不知道下一步 → 应搭配插画 + 明确 CTA（「Make your first transfer」），将空状态转化为激活引导

- **安全验证与业务向导分离**: 2FA 验证跳转到独立认证页再返回，导致用户丢失已填写的表单数据 → 应将验证步骤内嵌为多步向导中的一个 Screen，保持上下文连续性
