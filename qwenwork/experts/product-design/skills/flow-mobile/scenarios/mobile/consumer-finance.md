# Scenario: Mobile Consumer Finance（消费者金融 App）

> **研究来源**：基于对 PayPal、Revolut、Wise、UGLYCASH、Copilot 等 5 个真实 iOS 产品 flow 和页面的横向分析抽象，不代表任何单一产品的具体实现。

---

## Identity

**Platform**: Mobile (H5 / React Native)
**Definition**: 以账户余额查看、转账汇款、交易记录为核心的移动端消费者金融应用，用户通过生物识别验证身份完成转账，多货币账户管理，查看分类消费记录。

**Canonical Examples**: PayPal iOS、Revolut iOS、Wise iOS

**Not this scenario if**:
- 以加密货币交易为主（Coinbase/币安，改用 Web3 & Crypto 场景）
- 以投资理财为主（股票/基金，属于投资类应用）
- 以企业收款/POS 为主（B2B 收款工具，如 Square、Stripe Terminal）
- 主要在 Web 端使用（改用 web/fintech）
- 以信贷/贷款为核心产品（如 Klarna 先买后付，属于 BNPL 子场景）

---

## User Profile

| 维度 | 内容 |
|---|---|
| **主要角色** | 个人用户（日常收付款）/ 跨境用户（国际汇款）/ 多货币用户（持有多国货币）|
| **核心目标** | 快速查看余额 / 向联系人转账 / 确认某笔交易详情 |
| **心智模型** | 期待银行级别的安全感（生物识别确认大额操作）；期待汇率透明（实时转换）；期待即时反馈（余额变化、转账确认）|
| **使用频率** | 中频（每天 1-3 次）：早晨查余额 / 收付款时使用 / 月底对账 |
| **决策模式** | 任务驱动型：有明确的转账目标（「给朋友还钱」「查上周那笔消费」），不做探索 |
| **容错期望** | 转账前可查看费率摘要 / 确认页二次确认；生物识别失败可用密码兜底；已完成转账无法撤销（需展示明确警告）|

---

## IA Template

**导航模式**: Tab Bar（底部 Tab Bar，4-5 项，各产品差异较大）

典型结构（以 Revolut 为代表）：
```
Tab 1: 首页 / Home   — 账户余额 + 快速操作 + 最近交易
Tab 2: 转账 / Transfers — 转账 / 汇款入口
Tab 3: 卡片 / Card   — 虚拟/实体卡管理
Tab 4: 加密 / Crypto — (部分产品)
Tab 5: 我的 / Profile — 账户设置 + 安全 + KYC
```

典型结构（以 Wise 为代表）：
```
Tab 1: 首页 / Home   — 多货币账户概览
Tab 2: 卡片 / Card   — 实体/虚拟卡
Tab 3: 转账 / Send   — 中央突出，大圆形按钮
Tab 4: 收款人 / Recipients — 联系人列表
Tab 5: 管理 / Manage — 账户设置
```

**页面层级**: 3 级
```
L1: Tab 根页（Home / Transfers / Activity）
L2: 转账流程（多步骤 Wizard）/ 交易详情
L3: 操作面板（金额输入 / 收款人选择 / 费率确认）
```

**权限流结构**（移动端通用，金融 App 权限较少但有特殊需求）:
```
生物识别（设备解锁 / 支付确认）:
  → 首次触发高安全级操作（转账、设置修改）→ 浏览器 Web Authentication API / Expo LocalAuthentication 弹窗（自动触发，无需自定义说明页）
  → 失败兜底: 密码输入弹窗（系统级）

Contacts（联系人快速选择收款人）:
  → 首次点击「转账给联系人」→ Pattern G 说明页 → 浏览器 Contacts API / Expo Contacts 权限弹窗

Notifications（交易完成提醒 / 安全提醒）:
  → 首次完成转账后 → 说明页（「转账到账提醒 / 异常安全通知」）→ 浏览器 Notifications API / Expo Notifications 权限弹窗

Camera（KYC 证件扫描）:
  → 首次 KYC 身份验证时 → 浏览器 MediaDevices API / Expo Camera 权限弹窗（通常已在 onboarding 完成）
```

**数据密度**: 中（余额展示大字体低密度，交易列表中密度）
- 核心视图：余额大字（≥48pt）+ 快速操作按钮行 + 交易 List
- 辅助视图：`List`（交易记录）+ `Chart`（消费趋势）
- 不使用：多列 Table（金额输入用自定义 Numpad，非 Table）

**主要容器模式**:
| 场景 | 容器 |
|---|---|
| 转账金额输入 | 全屏页面（Stack Push）+ 自定义 Numpad |
| 账户/货币选择 | Bottom Sheet（中/大尺寸） |
| 费率详情说明 | Bottom Sheet（中尺寸） |
| 转账确认 | 全屏 Review 页（Stack Push）+ 生物识别弹窗 |
| 交易详情 | Stack Push |
| 取消/撤销转账请求 | Dialog（「此操作将通知对方，确认取消？」）|
| 收款人选择 | Bottom Sheet + 可搜索 List |
| 支付方式选择 | Bottom Sheet（中尺寸） |

**导航骨架图（ASCII，Revolut 模式）**:
```
┌────────────────────────────────────┐
│  Status Bar（时间 / 信号 / 电量）    │
├────────────────────────────────────┤
│ [👤] [搜索框               ] [📊][💳]│  ← 顶部操作栏
│                                    │
│  Main · GBP         ← 账户标签 pill │
│  ┌──────────────────────────────┐  │
│  │   £2,450.00                  │  │  ← 大余额字体（≥48pt）
│  │   Accounts ▾                │  │
│  └──────────────────────────────┘  │
│                                    │
│  [+加钱]  [↔兑换]  [≡明细]  [···]  │  ← 4个快速操作圆形按钮
│                                    │
│  最近交易                            │
│  ┌─ Starbucks  Today -£4.20 ──────┐│
│  ├─ Salary   Yesterday +£3,500 ──┤│
│  └─ Netflix  Mon -£9.99 ──────── ┘│
│                                    │
├───┬──────┬──────┬──────┬───────────┤
│ 🏠 │  💳  │  ↗↙  │  ₿  │  👤       │  ← TabBar
└───┴──────┴──────┴──────┴───────────┘
```

---

## 该场景独有的 IA/UX 决策

1. **金额输入必须使用品牌定制 Numpad（12 按键 Grid），不可用系统键盘** — 系统数字键盘在金融场景有三个缺陷：① 不同 locale 设置下小数点/千位符行为不一致；② 系统键盘弹出后遮挡页面上方的实时汇率换算区域；③ 按键尺寸由系统固定，无法保证 ≥48pt 的可触面积（转账场景用户通常存在焦虑，大按键减少误触）。自定义 Numpad（0-9 + 小数点 + 删除，按键 ≥48pt）可固定布局并同屏展示实时汇率——PayPal（flow_id 7263 / 7235）和 Revolut 均采用品牌定制 Numpad，是消费者金融 App 区别于普通 Web 转账表单（`<input type="number">`）的核心 UI 差异。

2. **转账必须经历 Review 全页面再触发生物识别，不可用 Dialog 直接确认** — 转账确认必须是「Review 全页面（Stack Push）→ 生物识别 → 处理中 → 成功」的完整四步，而非 Web 端的单页表单提交。Review 页必须同屏展示全部关键信息：发送金额 / 对方收到金额（含汇率换算）/ 手续费 / 预计到账时间 / 支付来源——用户在点击「确认发送」之前需要一次性看到所有信息。「确认发送」再触发浏览器 Web Authentication API / Expo LocalAuthentication，生物识别验证成功后才发起转账请求——Dialog 二次确认无法承载 5 条关键信息的同屏展示，也无法与生物识别集成（PayPal flow_id 7263 的 Review Modal 是行业基准）。

3. **余额必须支持隐私遮蔽（单击切换 ••••），字号 ≥48pt 等宽字体防抖动** — 余额展示有两个强制要求：① 字号 ≥48pt 等宽字体（tabular-nums 字体特性），防止数字宽度变化引起余额卡片布局抖动，且确保用户 2-3 秒内完成「账户安全确认」；② 余额隐私一键切换（单击余额区域替换为「••••.••」，附触觉反馈），防止公共场合（地铁/咖啡厅）泄露账户金额——Revolut / UGLYCASH 均实现了 Balance Concealment，是消费者金融区别于工具类 App 的隐私设计标准。

4. **多货币账户用 pill 切换器（Bottom Sheet 列表）原地切换，不可用多 Tab 或独立页面** — 多货币用户（USD / GBP / EUR）如果每种货币占一个 Tab，查看和对比不同货币余额必须来回切换 Tab，每次丢失当前页面上下文。正确做法是顶部 pill 标签选择器（「Main · GBP ▾」），点击弹出中尺寸 Bottom Sheet 展示所有货币账户列表，选中后 Home 页原地更新余额，无跳转无 Tab 浪费——Wise iOS 是此模式的标准参照，Revolut 同样采用 pill 切换，一屏完成账户视角切换，保持交易列表等周边信息的上下文连续性。

5. **P2P 收款详情必须提供 Emoji 快捷反应 + 回消息，社交化货币互动是留存关键差异** — 消费者金融 App 与 B2B 工具的根本区别在于 P2P 转账的社交属性：收到朋友还款/红包后，用户有天然的「表达谢意」需求。交易详情页的 Emoji 快捷反应行（👍 ❤️ 😂 等 5-6 个常用表情）+ 「发消息」入口，让金融操作完成后自动延伸至社交互动——PayPal flow_id 7262 完整展示了「交易详情 → Emoji 反应 → 消息回复」的交互链路。这是 PayPal / Venmo 多年验证的留存设计，纯 B2B 金融工具（如 Wise Business）没有此功能，是消费者金融场景独有的 UX 模式，不应按「通用交易详情」设计而缺失。

---

## Canonical Flows

> 以下 flow 基于 5 个真实产品样本横向分析抽象。括号内标注「行业共识」表示 3 个以上产品采用相同模式。

---

### Flow 1: View Account Balance & Quick Actions（查看余额 + 快速操作）

**在此场景的特殊性**: 消费者金融 App 的 Home 页面与其他类别 App 的最大区别是**大余额数字**（≥48pt，等宽字体）是绝对的视觉焦点——这是信任感的核心信号。Revolut、Wise、UGLYCASH 均将余额放在屏幕上方 1/3 处，主色调与品牌渐变配合，使用户第一眼就能确认「我的钱还在」。**快速操作按钮行**（Add Money / Send / Exchange / More 4个圆形图标）是所有研究样本的共识模式，让用户无需进入 Tab 就能完成最高频操作。**账户选择器**（多货币用户）通过小 pill 标签（如「Main · GBP」）切换，点击弹出账户列表 Bottom Sheet，而非独立页面。**余额隐私切换**（点击余额即遮蔽显示 ••••）是 Revolut、UGLYCASH 均有的安全设计，防止公共场合泄露。

**行业共识**：Revolut / Wise / UGLYCASH 均将余额 + 快速操作行 + 最近交易作为 Home 页的三段式标准结构；账户选择器用 pill 标签而非独立页面（PayPal flow_id 7236 确认）。

**Entry**: App 启动后自动进入（通过生物识别解锁 App，或上次使用后台挂起恢复）

```
Screen 1: 首页 / Home（已登录状态）
  主操作: 查看余额 / 点击快速操作
  关键组件:
    - NavBar（顶部: 头像 Avatar + 搜索框 + 图表图标 + 卡片图标）
    - 账户标签 pill（「Main · GBP」下拉选择账户，点击 → Bottom Sheet 账户切换器）
    - Text（余额大字：「£2,450.00」，≥48pt 等宽字体（tabular-nums），品牌渐变或深色背景）
    - [可选] Button（余额隐私，点击切换显示 / 遮蔽）
    - 快速操作行（4 个圆形按钮，各带图标+标签）:
        Button(「+ 加钱」，次要圆形按钮)
        Button(「↗ 转账」，主要圆形按钮，primary accent)
        Button(「↔ 兑换」，次要圆形按钮)
        Button(「··· 更多」，次要圆形按钮)
    - List（最近交易，分组「今天 / 本周 / 更早」Section Header）:
        每行: 商户图标 + 商户名 + 时间 + 金额（红色支出 / 绿色收入）
    - Button("查看全部"，次要按钮样式)（跳转交易记录列表）
  → 点击「+ 加钱」: Stack Push → 充值页
  → 点击「↗ 转账」: Stack Push → 转账 Flow 2
  → 点击余额数字: 切换显示 / 遮蔽（触觉反馈 + 替换为 ••••.••）
  → 点击账户 pill: Bottom Sheet 弹出账户选择器（多货币账户列表）
  → 点击交易行: Stack Push → Flow 3 交易详情

Screen 2: 账户选择器（多货币 Bottom Sheet）
  触发条件: 点击账户 pill（多货币用户）
  主操作: 切换账户 / 添加新货币账户
  关键组件:
    - Bottom Sheet（中尺寸）
    - List（货币账户列表）:
        每行: 国旗图标 + 货币全名 + 余额（本币）
        勾选标记（当前选中账户）
    - Button("添加货币账户"，次要按钮样式)（底部）
  → 点击账户: Home 余额切换至该账户余额，Sheet 关闭
```

**Exit State**:
- ✅ 正常加载：余额和最近 5-10 条交易显示完整
- ⚠️ 网络断开：显示缓存余额（带「上次更新时间」标注）+ 顶部 Banner「网络连接已断开」
- 🔒 App 锁定（超时或后台返回）：生物识别 / 密码解锁界面遮盖 Home，验证成功后恢复

---

### Flow 2: Send Money to Contact（转账 + 生物识别确认）

**在此场景的特殊性**: 消费者金融 App 的转账 flow 与 Web 转账最大的差异是**自定义数字键盘**（Custom Numpad）——所有研究样本（PayPal flow 7263/7235、Revolut 截图）均使用品牌定制的数字键盘而非系统键盘，原因是系统键盘在货币输入场景下行为不一致（小数点位置、删除键位置等），且无法显示实时汇率。**实时货币换算**（「你发送 £100 → 对方收到 $126.45」）是所有跨境金融 App 的共识，两行同步更新（PayPal flow 7263 12 屏完整记录）。**生物识别确认大额转账**是移动端特有的安全设计——Web 端用密码二次验证，移动端用生物识别，通过浏览器 Web Authentication API / Expo LocalAuthentication 调用，用户无感知，秒速通过。转账前的**费率详情 Bottom Sheet**（手续费明细 + 预计到账时间）是合规必须（PayPal flow 7244 确认）。

**行业共识**：PayPal（flow 7263 / 7235）均使用「联系人建议 → 自定义 Numpad → Review 汇总 → 确认」4 步结构；Revolut 和 Wise 的转账 UI 模式相同。

**Entry**: Home 快速操作区 → 点击「↗ 转账」按钮

```
Screen 1: 转账入口（Send & Request Hub）
  主操作: 选择收款人 / 选择转账类型
  关键组件:
    - NavBar（标题「转账」+ 返回按钮）
    - SearchBar（搜索联系人或输入账户/邮箱/手机号）
    - 联系人建议（最近交易联系人横向滚动，Avatar + 名字）
    - List 转账类型:
        「发送 / Send」→ Flow 2 核心路径
        「请款 / Request」→ 发起请款 flow
        「拆账 / Split Bill」→ 拆账 flow
    - [可选] Button("扫码转账"，次要按钮样式)（二维码扫描）
  → 点击联系人头像: 跳过搜索直接进入 Screen 2
  → 搜索并选择联系人: 进入 Screen 2

Screen 2: 金额输入（Amount Entry）
  主操作: 输入金额 → 查看实时换算
  关键组件:
    - 收款人信息（头部: Avatar + 姓名 + 账户标识）
    - 双行金额显示:
        Text(「你发送」，caption，灰色) + Text(「£ 0」，≥40pt，等宽字体，粗体)
        Text(「对方收到」，caption，灰色) + Text(「$ 0.00」，≥28pt，灰色等宽字体)
    - 汇率行: Text(「1 GBP = 1.2645 USD · 手续费 0.50 GBP」，caption + Button(「?」→ 费率详情 Sheet))
    - 自定义 Numpad（12 按键: 0-9 + 小数点 + 删除键，按键 ≥48pt）
    - Button("添加备注"，次要按钮样式)（可选消息）
    - Button("继续"，主要按钮样式)（全宽，金额为 0 时禁用）
  → 输入金额时: 两行金额同步实时更新，汇率重新计算
  → 点击「?」费率图标: 中尺寸 Bottom Sheet 弹出费率明细（手续费细则 + 预计到账时间）
  → 点击「继续」: 进入 Screen 3

Screen 3: 支付方式 + 转账类型确认（Review）
  主操作: 确认支付来源 / 选择转账类型 / 最终发送
  关键组件:
    - Stack Push（标题「确认转账」）
    - 摘要卡片（白色圆角矩形）:
        收款人头像 + 姓名
        金额大字: 「发送 £100.00 → 对方收到 $126.45」
        预计到账: 「1-2 个工作日」
    - 设置列表（右箭头，可点击进入子页修改）:
        「支付来源」: 默认账户（余额）或绑定卡（点击 → Screen 4 支付方式选择）
        「转账类型」: 「朋友和家人」/ 「商品和服务」（点击 → Action Sheet 选择）
        「备注」（可选）
    - 手续费行: 「手续费: £0.50」（小字，灰色）
    - Button("确认发送"，主要按钮样式)（全宽，触发生物识别）
  → 点击「确认发送」: 触发浏览器 Web Authentication API / Expo LocalAuthentication → Screen 5
  → 生物识别失败: 显示密码输入 fallback → 正确后进入 Screen 5

Screen 4: 支付方式选择（Bottom Sheet）
  触发条件: 点击「支付来源」进入
  主操作: 切换支付来源
  关键组件:
    - Bottom Sheet（中尺寸）
    - List（支付方式）:
        账户余额（显示可用余额）
        已绑定的银行卡（卡尾号 + 银行名）
        勾选标记（当前选中项）
    - Button("添加支付方式"，次要按钮样式)
  → 点击某项: 选中并关闭 Sheet，Review 页更新

Screen 5: 转账处理中 → 成功
  主操作: 等待处理完成
  关键组件:
    - ProgressIndicator（circular，居中，品牌色）
    - Text(「正在处理...」)
    → 成功（约 1-3 秒）: 切换为成功 UI:
        绿色大勾图标（≥60pt）
        Text(「已发送 £100.00」，大字）
        Text(「预计 [日期] 到账」，灰色小字）
        Button("完成"，主要按钮样式)（返回 Home）
        Button("查看详情"，次要按钮样式)（→ 交易详情页）
  → 错误（网络 / 余额不足）: 显示错误 UI + Button("重试") + Button("取消")
```

**Exit State**:
- ✅ 转账成功：成功 UI 显示 + Home Tab 余额即时减少 + 最近交易列表出现该笔记录
- ❌ 余额不足：Screen 3 「确认发送」禁用 + 余额不足提示
- ❌ 生物识别失败3次：锁定 15 分钟 + 提示用密码

---

### Flow 3: View Transaction History & Detail（查看交易记录与详情）

**在此场景的特殊性**: 消费者金融 App 的交易记录页与普通列表页最大的区别是**分类颜色 Chip**（Copilot 的彩色分类标签：FOOD/CAR/SUBSC 等）和**双层金额显示**（本币金额 + 等值另一货币换算）。搜索全文搜索和**日期范围过滤**是标准功能（PayPal 有按类型过滤下拉）。交易详情页的「**支付凭证动画**」（PayPal flow_id 7262 展示的 Payment Reveal：点击交易行有 reveal 动画展示金额）是消费者金融的特有设计，配合触觉反馈增强「钱已到账」的确定感。交易详情支持**Emoji 快捷反应 + 发消息给付款方**（PayPal 模式），这是消费者金融与 B2B 工具最明显的差异——社交化货币互动。

**行业共识**：PayPal（flow 7262）确认「交易详情 → 快捷 Emoji 反应 + 文字回复」是 P2P 收款场景的标准后续操作；Copilot 的分类颜色 Chip 是个人财务管理类 App 的行业规范。

**Entry**: Home 最近交易 → 点击某条记录 / Activity Tab 查看全部

```
Screen 1: 交易记录列表（Activity / Transactions）
  主操作: 查找、筛选交易记录
  关键组件:
    - NavBar（标题「交易记录」+ 右上角账户选择）
    - SearchBar（搜索商户名 / 金额 / 备注）
    - 过滤器行（横向可滚动）:
        Chip("全部"，选中状态深色)
        Chip("支出")
        Chip("收入")
        Chip("日期范围"，点击 DatePicker)
    - List（交易记录，下拉刷新）:
        分组: Section Header（「今天」「本周」「X月X日」）
        每行:
          商户图标（brand logo 或 category 图标）
          商户名（粗体）+ 日期（灰色小字）
          金额（右对齐，支出红色 / 收入绿色）
          [可选] 分类 Chip（彩色小 pill：FOOD / SHOPPING / SUBSC...）
    - Empty State（搜索无结果: 「未找到相关交易」）
  → 点击某条记录: Stack Push → Screen 2
  → 搜索: 列表过滤，高亮匹配关键词

Screen 2: 交易详情（Transaction Detail）
  主操作: 查看详情 / 回复付款方 / 举报
  关键组件:
    - NavBar（商户名，inline 样式）
    - 金额 Reveal 区域（顶部 featured card）:
        大金额文字（≥40pt）+ 状态（「已完成」绿色徽章 / 「处理中」灰色）
        商户/联系人信息
    - Details 列表（只读）:
        交易时间（完整时间戳）
        交易 ID（可复制）
        支付方式（卡尾号 或 账户余额）
        手续费（若有）
        备注（若有）
    - [P2P 收款场景] 快捷操作行:
        Emoji 快捷反应横排（👍 ❤️ 😂 ···）
        Button("回消息"，次要按钮样式)（弹出 TextInput）
    - 右上角菜单（「下载收据 PDF」/ 「举报问题」/ 「申请退款」）
    - [部分产品] Chart（支出与该商户的历史趋势小折线图，caption 尺寸）
  → 点击 Emoji: 触觉反馈 + Emoji 反应发给付款方 + Toast 确认
  → 点击「回消息」: TextInput 弹起，输入后发送 → 消息线程更新
  → 点击「申请退款 / Dispute」: 进入客服 / 退款流程（外链 or WebView）

[可选] Screen 3: 消费分析（Monthly Summary）
  触发条件: 交易列表顶部 Banner「查看本月消费分析」→ 点击进入
  主操作: 查看分类消费分布
  关键组件:
    - Chart（饼图或环形图，各分类占比）
    - List（分类明细: 分类名 + 分类颜色 Chip + 该月总支出 + 交易笔数）
    - 月份选择（← 上月 | 本月 | 下月 →）
  → 点击某分类: 筛选该分类所有交易 → 返回 Screen 1 已过滤状态
```

**Exit State**:
- ✅ 正常浏览：记录列表完整，可搜索/筛选
- ✅ P2P 反应发送：Toast「已回应」，付款方收到通知
- 空状态（新用户）：Empty State「还没有交易记录」+ 「发起第一笔转账」CTA

---

## Mobile Component Kit

按使用频率排序（基于研究样本观察）：

| 优先级 | 组件（H5 antd-mobile）| 组件（RN Gluestack/RN）| 具体用途 |
|---|---|---|---|
| ★★★ | `TabBar` | `BottomTabNavigator` | App 主导航（Home / Transfers / Card / Profile）|
| ★★★ | `NavBar` + `StackNavigator` | `StackNavigator` | 转账多步 Wizard（Amount → Review → Success）|
| ★★★ | 浏览器 Web Authentication API | `expo-local-authentication` | 生物识别转账确认 |
| ★★★ | 自定义 Numpad（Grid 布局） | 自定义 Numpad 组件（TouchableOpacity Grid） | 自定义数字键盘（品牌化金额输入）|
| ★★★ | `List` + `InfiniteScroll` | `FlatList`（分组） | 交易记录分组列表（today/week/month）|
| ★★ | `Popup` / `ActionSheet` | `BottomSheet` | 费率详情 / 账户选择 / 支付方式选择 |
| ★★ | `SearchBar` | `SearchBar` | 交易记录全文搜索 / 联系人搜索 |
| ★★ | `recharts` / `victory-native` | `victory-native` / `react-native-charts-wrapper` | 消费分析饼图 / 支出趋势折线图 |
| ★★ | `Text`（tabular-nums CSS 特性） | `Text`（fontVariant: ['tabular-nums']）| 余额 / 金额大字显示（防抖动）|
| ★★ | 浏览器 Notifications API | `expo-notifications` | 转账到账提醒 / 安全通知权限 |
| ★ | `ActionSheet` | `ActionSheet` | 转账类型选择（朋友&家人 / 商品&服务）|
| ★ | `PullToRefresh` | `RefreshControl` | 余额 / 交易记录下拉刷新 |
| ★ | `ErrorBlock` | Empty State 自定义 | 无交易记录空状态 / 搜索无结果 |
| ★ | Web Share API | `react-native-share` | 分享交易收据 / 支付链接 |
| ★ | `Badge` | `Badge` | 未读通知数量（Tab Bar 角标）|
| ★ | `Image` + `lazyload` | `Image` + `FastImage` | 商户品牌 Logo（联网加载）|

---

## Anti-Patterns

基于研究样本中观察到的设计错误：

- **金额输入使用系统数字键盘**：系统键盘在货币场景下有多个问题：小数点位置不固定（不同语言区域差异）、无法在键盘上方展示实时汇率、删除键位置与品牌设计冲突。→ 正确做法：使用品牌定制的自定义 Numpad（12 按键 Grid：0-9 + 小数点 + 删除），固定布局，同屏显示实时汇率换算（PayPal / Revolut 均如此）。

- **转账确认只使用 Dialog 而不展示完整 Review 页**：用户无法在确认前查看手续费、预计到账时间、支付来源等关键信息。→ 正确做法：转账确认必须是独立的 Review 全页面（Stack Push），明确展示「你发送 / 对方收到」双行金额、手续费、预计到账，再由「确认发送」按钮触发生物识别（PayPal flow 7263 中的 Review 页包含 5 项关键信息）。

- **不使用生物识别，仅依赖按钮单击完成大额转账**：用户可能误触「发送」按钮，或他人借用手机时无授权操作。→ 正确做法：转账「确认」操作必须触发生物识别验证；失败后提供密码 fallback；金额超出阈值（如 1000 元）时即使在会话中也重新要求验证。

- **余额无隐私遮蔽功能**：用户在公共场所（地铁/咖啡厅）打开 App 时，账户余额对周围人可见。→ 正确做法：余额区域支持单击切换「显示 / ••••.••」（带触觉反馈），部分产品在锁屏通知中也默认遮蔽金额（Revolut / UGLYCASH 均实现了 Balance Concealment）。

- **多货币账户用独立 Tab 页展示，而非单页账户切换器**：用户每次查看不同货币余额都要切换 Tab，丢失当前浏览上下文。→ 正确做法：多货币账户用 pill 下拉选择器（点击「Main · GBP」→ Bottom Sheet 弹出账户列表），切换后 Home 页原位更新余额，无需跳转（Wise / Revolut 均采用此模式）。

- **交易记录只按时间排序，无搜索和分类过滤**：用户有 100+ 条记录时无法快速找到特定商户的消费。→ 正确做法：SearchBar 支持商户名 / 金额 / 备注全文搜索；横向可滚动 Filter Chips（支出 / 收入 / 日期范围 / 分类）；交易行显示彩色分类 Chip（Copilot 模式）帮助用户快速视觉扫描（如「哪些是订阅消费」）。

- **P2P 收款后无后续互动设计**：收到一笔朋友转账后，App 仅更新余额，无任何反馈机制，感觉「冷漠」。→ 正确做法：P2P 收款交易详情页提供 Emoji 快捷反应行（👍 ❤️ 😂 等 5-6 个常用表情）+ 「发送消息」按钮，让用户可以快速感谢付款方，增强产品社交粘性（PayPal flow_id 7262 完整展示了此交互）。

- **转账流程中断后无草稿保存，丢失已输入信息**：用户在「金额输入」步骤被打断（接电话）后返回，发现金额和收款人信息已清除，需要重新输入。→ 正确做法：转账流程中的已输入信息应在后台挂起时保留（存入组件状态 / Context），返回前台时自动恢复至中断步骤；若超过 15 分钟未操作，清除草稿并展示 Toast「转账已超时，请重新发起」。
