# Scenario: Marketing Site（营销网站 / 注册转化）

> **研究来源**：基于对 Intercom、Replo、Homerun、Tella、GlossGenius、Lemni、Voicenotes、Column、Navan、Metaview 等 10+ 个真实产品 flow 的横向分析抽象，不代表任何单一产品的具体实现。

---

## Identity

**Platform**: Web
**Definition**: 面向潜在用户的公开营销网站，核心目标是将访客转化为注册用户（或付费用户），包含从 hero landing page 到注册完成的完整漏斗。

**Canonical Examples**: Intercom 官网、Notion 官网、Linear 官网

**Not this scenario if**: 产品已登录（改用 web/saas-management.md）；以展示内容为主而非转化（改用 blog/docs 场景）；主要面向企业销售团队而非自助注册（改用 enterprise sales 场景）。

---

## User Profile

| 维度 | 内容 |
|---|---|
| **主要角色** | 潜在用户（Prospect）/ 决策者（Decision Maker）/ 团队管理员（Admin，代表团队评估） |
| **核心目标** | 了解产品价值 → 决定是否注册 → 完成注册 → 进入产品 |
| **心智模型** | 消费者体验期望：快速、低摩擦、免信用卡试用；对产品价值有好奇但尚未建立信任 |
| **使用频率** | 一次性（注册完成后此场景结束，进入 SaaS 管理后台或 AI 产品场景） |
| **决策模式** | 探索发现 → 价值评估 → 行动转化；受社交证明和免费门槛强烈影响 |
| **容错期望** | 高容错：注册摩擦每增加一步都会造成流失；期望可随时回头或跳过 |

---

## IA Template

**导航模式**: Top Navigation（顶部固定导航）
- 进入注册流后切换为**极简无导航**（仅保留 Logo，无法跳出）
- 注册成功后 Dashboard 首次出现左侧 Sidebar 导航

**页面层级**: 2 级（营销层 → 注册流）
```
L1: 营销页面（Hero / Pricing / About / Features）
L2: 注册流（Signup → Email Verify → Onboarding 问卷 → Dashboard）
```

**权限角色结构**: 无（访客身份，注册后进入 SaaS 管理后台的角色体系）

**数据密度**: 低（大图、短文案、CTA 按钮为主）

**主要容器模式**:
| 场景 | 容器 |
|---|---|
| 注册表单 | 全页面（或左内容+右表单分栏） |
| Onboarding 问卷 | 全屏步进向导（单屏单问题） |
| 升级付费（产品内触发） | Modal（不跳转独立页面） |
| 支付结账 | Stripe 嵌入式表单（在 Modal 内） |
| 成功确认 | Modal 或全页 |

**导航骨架图（ASCII）**:
```
┌──────────────────────────────────────────────────────────────────┐
│  [Logo]  产品 ▾  解决方案 ▾  定价  资源         登录  [Start Free →]│
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ████████████████████  HERO SECTION  ████████████████████████   │
│                                                                  │
│    Headline: 一句核心价值主张                                       │
│    Sub-headline: 补充说明                                          │
│    [Start for Free]    [Watch Demo]                              │
│                                                                  │
│    Product Screenshot / Animation                                │
│                                                                  │
├──────────────────────────────────────────────────────────────────┤
│  Logo Wall: [Brand] [Brand] [Brand] [Brand] [Brand]              │
├──────────────────────────────────────────────────────────────────┤
│  功能介绍区块 × 3                                                  │
├──────────────────────────────────────────────────────────────────┤
│  Testimonials: Quote Cards / Twitter Embed                       │
├──────────────────────────────────────────────────────────────────┤
│  Pricing: [Free] [Pro ★ Most Popular] [Enterprise]               │
│           [月付 ○] [年付 ○] Toggle                                │
├──────────────────────────────────────────────────────────────────┤
│  Final CTA: Headline + [Start for Free]                          │
├──────────────────────────────────────────────────────────────────┤
│  Footer                                                          │
└──────────────────────────────────────────────────────────────────┘

注册流（进入后无顶部导航）：
┌──────────────────────────────────────────────────────────────────┐
│  [Logo]                                          [Step 1 of 4]  │
│  ────────────────────────────────────────────────────────────   │
│                                                                  │
│                    Sign Up                                       │
│                                                                  │
│    [G] Continue with Google                                      │
│    ─────────────── or ───────────────                            │
│    Name ________________________                                  │
│    Email _______________________                                  │
│    Password ____________________                                  │
│                                                                  │
│    [Create Account →]                                            │
│    Already have an account? Log in                               │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

### 图 2：关键状态对比图（Key State Variations）

```
左：Landing Page Hero（访客态）              右：注册流 Step 1（转化漏斗入口）

┌─────────────────────────────────────┐  ┌─────────────────────────────────────┐
│ Logo  产品▾ 解决方案▾ 定价  登录    │  │ Logo                   [Step 1 of 4]│
│                          [Start →] │  │ ──────────────────────────────────  │
├─────────────────────────────────────┤  ├─────────────────────────────────────┤
│                                     │  │                                     │
│  ████████████████████████████████  │  │           Sign Up                   │
│                                     │  │                                     │
│    核心价值主张（大标题）             │  │   [G] Continue with Google          │
│    补充说明文字（小标题）             │  │   ─────────────── or ─────────────  │
│                                     │  │   Name __________________________   │
│    [Start for Free] [Watch Demo]   │  │   Email _________________________   │
│                                     │  │   Password ______________________   │
│    [产品截图 / 演示动画]             │  │                                     │
│                                     │  │   [  Create Account →  ]            │
│  ─────────────────────────────────  │  │   Already have an account? Log in   │
│  [Brand] [Brand] [Brand] [Brand]   │  │                                     │
└─────────────────────────────────────┘  └─────────────────────────────────────┘
  访客态：完整 Top Nav + 品牌 Logo Wall     注册流：无导航 + 步骤进度指示
```

---

### 图 3：覆层层级图（Overlay Hierarchy）

```
                  Onboarding 全屏向导（进入注册流后，Top Nav 消失）
┌───────────────────────────────────────────────────────────────────────────┐
│  Logo                                                      [Step 2 of 4] │ ← 无顶部导航
├───────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│              How would you describe your team?                            │
│              ●  Just me — solo creator                                    │
│              ○  Small team (2-10 people)                                  │
│              ○  Mid-size team (11-50)                                     │
│              ○  Large organization (50+)                                  │
│                                                                           │
│              [Continue →]    Skip                                         │
└───────────────────────────────────────────────────────────────────────────┘

                  进入产品后触发升级：两层嵌套 Modal（z 层叠关系）
┌───────────────────────────────────────────────────────────────────────────┐
│  Dashboard（背景，Dim）                                                    │
│                                                                           │
│      ┌─────────────────────────────────────────────────────────────┐     │
│      │  Pricing Modal（层 1）z-index: 200                           │     │
│      │  [月付 ○] [年付 ○ Save 20%]                                  │     │
│      │  ┌────────┐  ┌────────────┐  ┌────────────┐                │     │
│      │  │  Free  │  │ Pro ★ Hot  │  │ Enterprise │                │     │
│      │  │  $0/mo │  │ $19/mo     │  │ 联系销售   │                │     │
│      │  │[当前]  │  │[升级 Pro]  │  │[Contact]   │                │     │
│      │  └────────┘  └────────────┘  └────────────┘                │     │
│      │  [功能对比 ▾ 展开]                          [×] 关闭         │     │
│      │                                                              │     │
│      │      ┌─────────────────────────────────────────┐           │     │
│      │      │  Checkout 嵌入 Modal（层 2）z-index:300  │           │     │
│      │      │  Pro Plan · $19/month                   │           │     │
│      │      │  ┌──────────────────────────────────┐  │           │     │
│      │      │  │  Card Number  [Stripe Element]   │  │           │     │
│      │      │  │  Expiry  CVV                     │  │           │     │
│      │      │  └──────────────────────────────────┘  │           │     │
│      │      │  [Credit Card]  [Google Pay]            │           │     │
│      │      │  ☑ I agree to the Terms of Service     │           │     │
│      │      │  [← Back]     [Start Pro Subscription] │           │     │
│      │      │  🔒 Secured by Stripe                   │           │     │
│      │      └─────────────────────────────────────────┘           │     │
│      └─────────────────────────────────────────────────────────────┘     │
└───────────────────────────────────────────────────────────────────────────┘
  ┌────────────────────────────────────────────────┐
  │  🎉 You're now on Pro! Enjoy unlimited access   │  ← Toast（z-400，升级成功）
  └────────────────────────────────────────────────┘

触发关系说明:
- Onboarding 全屏向导: 注册完成后全屏渲染，无覆层，无 z-index 竞争；无法跳出（无导航）
- Pricing Modal（层 1）: 点击受限功能触发，z-200，Dim 背景，可按 × 关闭
- Checkout 嵌入 Modal（层 2）: 点击「升级 Pro」后在 Pricing Modal 上叠加，z-300；返回可回到层 1
- Toast（底部）: 升级成功 / 邀请发送等轻量反馈，z-400，3-5 秒自动消失
```

---

## 该场景独有的 IA/UX 决策

> 以下是营销网站/注册转化场景区别于其他场景的核心设计判断，基于跨产品横向研究归纳。

**1. 注册门槛与价值承诺的时序博弈**
主流策略是「先注册，后付费」——让用户先进入产品，再在 dashboard 内触发升级 CTA，而非在注册流中插入付费步骤。在注册流中插入支付的策略（GlossGenius、Breathwrk）仅在前序价值承诺非常充分时才有效。**关键决策：是否在注册流内插入支付，取决于产品核心价值能否在前序步骤中充分传递。**

**2. Onboarding 问卷应以「配置产品」而非「填写调研」的框架呈现**
注册后的 3–5 个问题同时服务于「分段营销」和「产品个性化配置」两个目的。Replo 和 Homerun 均采用「告诉我们你的品牌」「帮你定制工作区」的措辞，而非「请填写以下调研」——前者接受率远高于后者，因为它让用户感知到即时收益而非单方面付出。

**3. 定价页功能对比表应折叠，首屏只展示方案卡片**
「Most Popular」标签几乎普遍用于中间价位的 Pro 方案，配合视觉强调（边框高亮/背景色/CTA 颜色），利用锚定效应引导选择。但更重要的 IA 决策是：**功能对比表放在方案卡片下方，需要用户主动滚动或展开**——这是刻意降低初次决策认知负担的设计，避免信息过载导致决策瘫痪。

**4. 升级付费用 Modal 而非独立页面，降低退出感知**
产品内触发的升级流（Lemni、Voicenotes、Intercom）普遍选择在 Modal 内完成整个支付流程，而非跳转到独立 /upgrade 页面。这减少了「离开当前产品上下文」的心理摩擦，且支付成功后用户立即感知到界面状态变化（按钮文案更新、计划标签变化），强化行动-反馈闭环。

**5. 社交证明遵循「信任建立顺序」，而非简单放在 Hero 下方**
营销页的社交证明按以下梯队排列效果最佳：**Logo Wall（可信度锚定）→ 功能介绍（产品理解）→ 用户 Quote/故事（情感共鸣）→ G2/Capterra 评级徽章（第三方验证）→ Final CTA**。打破这个顺序（如在 Logo Wall 之前放 CTA）会造成信任感断裂，降低转化率。

---

## Canonical Flows

> 以下 flow 基于 12 个真实产品样本的横向分析抽象。括号内标注「行业共识」表示 3 个以上产品采用相同模式。

---

### Flow 1: Visitor Sign Up（访客注册 — 低摩擦型）

**在此场景的特殊性**: 与 SaaS 管理后台的「邀请成员」不同，此 flow 的主角是未经认证的陌生访客，核心设计目标是最小化每一步的摩擦。Social Auth 必须排第一位（Intercom、Tella、Homerun 均如此）。注册流进入后应切换为极简无导航模式（仅保留 Logo），防止用户在注册中途跳出。Email 验证几乎是强制步骤，但必须提供「打开 Gmail / Outlook」快捷按钮降低等待摩擦。

**行业共识**：Social Auth 首位、单屏单问题问卷、Email 验证 + 快捷跳转按钮，出现在全部 12 个样本产品中。

**前置条件**: 无（任何访客均可进入注册流，无需预先登录或邀请码）
**若前置条件不满足**: 邮箱已被注册 → Sign Up Gate 显示 inline 错误「该邮箱已注册，请直接登录」；企业版仅接受企业邮箱（见 Flow 3）

**Entry**: 营销页 Hero 区域「Start for Free」CTA 按钮

```
Screen 1: Sign Up Gate
  主操作: 选择注册方式
  关键组件: Button（Google OAuth，首位，full-width）
            Divider「or」
            Input（邮箱）, Input（密码）, Input（姓名，可选）
            Button（Create Account, primary, full-width）
            Link（已有账户？登录）
  → Social Auth 点击: 跳转 OAuth 授权 → 授权成功后直接进 Screen 3
  → 表单提交: 进 Screen 2（Email 验证）
  → 表单验证失败: inline 错误提示（邮箱格式、密码强度）

Screen 2: Email Verification
  主操作: 输入 OTP 验证码
  关键组件: 6位 OTP Input（自动聚焦）
            Button（打开 Gmail, secondary）, Button（打开 Outlook, secondary）
            Link（重新发送，倒计时 60s 后激活）
            Text（已发送至 xxx@email.com）
  → OTP 输入正确: 自动跳转 Screen 3
  → OTP 错误: Input 显示错误状态 + 提示「验证码无效」
  → 超时: Link「重新发送」激活

Screen 3: Onboarding 问卷（每题独占一屏）
  主操作: 回答角色 / 使用场景 / 发现来源（每屏一题）
  关键组件: ProgressBar（顶部，如「2 of 3」）
            Heading（问题，以「帮助我们配置你的工作区」框架呈现）
            RadioGroup 或 ButtonGroup（选项，4–6 个）
            Button（Continue, primary）, Link（Skip, 次级）
  → 每题选择后自动进下一屏，无需手动点 Continue（可选设计）
  → 全部完成 / Skip: 进 Screen 4

Screen 4: Trial Activation Confirmation
  主操作: 确认试用已激活 → 进入产品
  关键组件: Illustration 或 Confetti 动效
            Heading（「你的 14 天试用已激活」）
            Text（「无需信用卡，随时取消」）
            Button（进入产品 / Get Started, primary, full-width）
  → 点击「进入产品」: 进 Screen 5

Screen 5: Dashboard 首次进入（空态 + 引导）
  主操作: 完成引导清单的第一步
  关键组件: Modal Overlay（欢迎语 + 3步任务清单）
            Sidebar 导航（首次出现）
            Empty State（主内容区）
  → 关闭 Modal: Checklist 收起至侧边栏，用户自由探索
```

**Exit State**:
- ✅ Success：进入 Dashboard，试用激活，引导清单展示
- ❌ Error（Email 已存在）：Sign Up Gate 显示 inline 错误「该邮箱已注册，请直接登录」+ 登录链接
- ↩ Abandon：任意步骤可关闭浏览器，注册进度可能丢失（部分产品支持 magic link 续签）

---

### Flow 2: Freemium Upgrade（产品内升级付费 — 功能限制触发型）

**在此场景的特殊性**: 与独立 Pricing Page 不同，此 flow 在产品内部触发，用户已有产品上下文，升级决策基于当前任务需求而非抽象比较。核心设计目标是「不打断工作流」：全程在 Modal 内完成，支付成功后立即返回原界面并解锁功能。「月付/年付 Toggle」和「实时价格更新」是行业共识（Lemni、Voicenotes、Intercom 均如此）。

**行业共识**：Modal 内完成支付（不跳转独立页面）、Most Popular 高亮中间方案、年付折扣 Badge，出现在全部升级样本中。

**前置条件**: 用户已注册并登录（Free 套餐用户）；触发了受限功能或主动进入升级路径
**若前置条件不满足**: 未登录访客触发受限功能 → 先跳 Sign Up Gate（Flow 1），注册完成后再触发升级

**Entry**: 用户点击受限功能 → inline banner 或 Tooltip：「升级 Pro 解锁此功能」→ 「查看方案」链接

```
Screen 1: Pricing Modal（计划选择）
  主操作: 选择目标计划
  关键组件: Dialog（全屏 Modal 或居中大 Modal）
            Toggle（月付 / 年付，年付显示「节省 X%」Badge）
            Card × 3（Free 标注「当前」/ Pro 标注「Most Popular」+ 边框高亮 / Enterprise「联系销售」）
            功能对比 Collapsible（折叠，需手动展开）
            Button（升级 Pro, primary）, Link（关闭 Modal）
  → 切换 Toggle: 价格实时更新
  → 点击「升级 Pro」: 进 Screen 2
  → 点击「联系销售」: 跳转 Calendly 或 mailto

Screen 2: Checkout（支付方式）
  主操作: 填写支付信息 → 确认订阅
  关键组件: Stripe 嵌入式表单（CardElement 或 PaymentElement）
            Tabs（信用卡 / Google Pay / Apple Pay）
            订单摘要（右侧或底部：方案名 / 价格 / 周期）
            Checkbox（同意订阅条款，含链接）
            Button（开始订阅 / Start Pro, primary）, Button（返回, ghost）
            Text（🔒 通过 Stripe 安全加密）
  → 点击「开始订阅」: 进 Screen 3（处理中）
  → 支付失败: inline 错误提示（卡被拒、余额不足等）

Screen 3: Processing
  主操作: 等待支付处理（自动跳转，无需用户操作）
  关键组件: Spinner 或 Progress 动效
            Text（「正在激活你的 Pro 账户...」）
  → 处理成功（约 1–3s）: 自动进 Screen 4

Screen 4: Upgrade Confirmation
  主操作: 确认升级成功 → 返回产品
  关键组件: Icon（✓ 或 Confetti 动效）
            Heading（「你现在是 Pro 用户」）
            List（已解锁的核心功能，3–5条）
            Button（返回产品 / Get Started, primary）
  → 点击「返回产品」: 关闭 Modal，原界面功能立即解锁（按钮文案变化、限制提示消失）
```

**Exit State**:
- ✅ Success：Modal 关闭，用户回到原任务界面，功能已解锁，顶部显示「Pro」标签
- ❌ Error（支付失败）：Screen 2 显示 inline 错误，表单保留已填内容，用户可修改后重试
- ↩ Abandon：任意步骤可关闭 Modal，不产生任何费用，回到原界面

---

### Flow 3: Enterprise Signup（企业级注册 + 工作区配置 — 高意图型）

**在此场景的特殊性**: 区别于轻量注册，企业场景的注册人通常代表团队评估产品，注册目的是「建立工作区」而非「个人试用」。**必须拒绝个人邮箱（Gmail/Outlook）**，仅接受企业邮箱——这是 B2B SaaS 的常见做法（Navan、Column 均有 inline 提示）。问卷深度更高（5–7 题），分屏布局（左侧进度预览 + 右侧表单）是该类产品的行业共识。

**行业共识**：企业邮箱校验、分屏布局问卷向导、邀请团队成员步骤，出现在 Navan、Homerun、Column 等企业级产品中。

**前置条件**: 无（任何访客均可发起企业注册流程）；但必须使用企业邮箱（非 Gmail/Outlook/Yahoo 等个人邮箱域名）
**若前置条件不满足**: 输入个人邮箱 → inline 错误「请使用工作邮箱」，按钮不可点击；该企业域名已有工作区 → 提示联系管理员加入

**Entry**: 营销页「申请试用」或「联系销售」CTA（双入口，自助注册为主）

```
Screen 1: Sign Up Form（企业信息收集）
  主操作: 填写企业信息
  关键组件: Input（工作邮箱，实时校验是否为企业邮箱）
            Input（姓名、公司名、职位）
            Button（继续, primary）
  → 输入个人邮箱（@gmail/@outlook）: inline 错误「请使用工作邮箱」
  → 提交: 进 Email 验证

Screen 2: Email Verification（同 Flow 1 Screen 2）

Screen 3: Workspace Setup Wizard（分屏布局，共 4–5 步）
  布局: 左侧（固定）进度步骤 + 当前配置预览 / 右侧（滚动）逐步表单
  主操作: 依次填写工作区配置
  问题序列:
    Step 1: 公司规模（RadioGroup，如 1–10 / 11–50 / 51–200 / 200+）
    Step 2: 团队类型 / 主要职能（RadioGroup 或 MultiSelect）
    Step 3: 主要使用目标（MultiSelect，如 提升团队效率 / 统一数据 / 审批流管理）
    Step 4: 目前使用的工具（MultiSelect，含 Logo，如 Notion / Jira / Slack）
    Step 5（可选）: 工作区名称 + Logo 上传
  关键组件: ProgressSteps（左侧），RadioGroup / MultiSelect / Input / FileUpload（右侧）
            Button（下一步, primary）, Button（上一步, ghost）, Link（跳过此步）
  → 全部完成: 进 Screen 4

Screen 4: Invite Team Members
  主操作: 邀请团队成员（可跳过）
  关键组件: Input（批量邮箱输入，逗号分隔 或 一行一个）
            Select（为所有被邀请者设置默认角色）
            Button（发送邀请, primary）
            Link（跳过，稍后邀请）
            Text（试用说明：「被邀请成员共享你的 14 天试用」）
  → 点击「发送邀请」/ 跳过: 进 Screen 5

Screen 5: Dashboard（工作区已建立）
  主操作: 完成引导清单的第一步
  关键组件: Sidebar 导航（含工作区 Logo + 名称）
            欢迎 Banner（横向，含管理员名字）
            Onboarding Checklist（右侧浮动或侧边，3–5 步，显示完成进度）
  → 关闭 Checklist 需二次确认（Alert：「确定关闭引导吗？随时可在设置中重新开启」）
```

**Exit State**:
- ✅ Success：工作区建立，Dashboard 展示，引导清单激活，邀请邮件已发出（如有）
- ❌ Error（企业邮箱已注册）：Screen 1 inline 提示「该域名已有工作区，请联系管理员加入」+ 联系管理员链接
- ↩ Abandon：注册中途可随时离开；若 Email 验证已完成，magic link 可恢复进度

---

### Flow 4: Password Reset（密码重置 — 认证恢复型）

**在此场景的特殊性**: 密码重置是最成熟的行业共识 flow，几乎所有 Web 产品均以相同模式实现，但细节决定转化率：重置邮件必须提供「打开 Gmail / Outlook」快捷按钮（与 Email OTP 验证一致）；重置表单的密码强度指示器是安全性与 UX 的平衡点；重置成功后应自动登录而非要求用户再手动输入新密码——这一步省略可减少约 40% 的重置后放弃率。该 flow 是 marketing-site 场景独有的，因为 SaaS 管理后台（已登录）没有此路径，AI 产品通常通过 OAuth 避开密码。

**前置条件**: 用户已有注册账号（邮箱+密码方式，非 OAuth 注册）；用户当前处于未登录状态，在登录页无法记起密码
**若前置条件不满足**: OAuth 注册用户（通过 Google 注册）无密码可重置 → 提示「您通过 Google 登录，请使用 Google 继续」；账号不存在 → 出于安全，发送「该邮箱无账号」的邮件提示，不在前端暴露账号是否存在

**Entry**: 登录页「Forgot password?」链接

**Screens**:

```
Screen 1: Forgot Password（邮箱输入）
  视觉状态: 极简页面，仅 Logo + 标题 + 邮箱输入框（无导航）
  关键组件:
    - 页面标题: 「Forgot your password?」
    - 说明文案: 「Enter your email and we'll send you a reset link.」
    - Email Input（自动填充友好，预填 localStorage 中的上次登录邮箱）
    - [Send Reset Link]  主 CTA
    - [← Back to Login]  次级链接
  → 输入邮箱 + 点击 Send: Screen 2
  → 邮箱格式错误: inline 错误「请输入有效的邮箱地址」

Screen 2: Email Sent（确认发送）
  视觉状态: 成功状态页面，引导用户去邮箱查收
  关键组件:
    - 图标/插图（信封 + 发送动效）
    - 标题: 「Check your email」
    - 说明: 「We sent a reset link to alex@example.com. It expires in 15 minutes.」
    - [Open Gmail]  主 CTA（检测 @gmail.com 域名自动显示）
    - [Open Outlook]  次要 CTA（检测 Outlook/Hotmail 域名自动显示）
    - [Resend email]  链接（倒计时 60 秒后激活）
    - [← Use a different email]  次级链接
  → 用户点击邮件中的 Reset Link: Screen 3（新 Tab 打开）

Screen 3: Reset Password Form（新密码输入）
  视觉状态: 无顶部导航的独立页面；URL 含一次性 Token
  关键组件:
    - 标题: 「Create a new password」
    - New Password Input（含显示/隐藏密码 Eye 图标）
    - 密码强度指示器（Weak / Fair / Strong，颜色条形）
    - Confirm Password Input（重复输入，实时匹配验证）
    - 密码要求 Checklist:
        ✓ 至少 8 个字符
        ✓ 包含大写字母
        ✓ 包含数字或符号
    - [Reset Password]  主 CTA（两次输入匹配且强度 ≥ Fair 才激活）
    - Token 过期处理: 若 URL Token 无效 → 页面显示「此重置链接已过期」+ [Request new link] CTA
  → 点击 Reset Password + 成功: Screen 4

Screen 4: Reset Success + 自动登录
  视觉状态: 简短成功页，1-2 秒后自动跳转 Dashboard
  关键组件:
    - 图标: ✓（绿色勾选）
    - 标题: 「Password updated successfully」
    - 说明: 「You're being signed in...」
    - Progress Indicator（自动跳转倒计时）
    - [Continue to Dashboard]  主 CTA（不等倒计时立即跳转）
  → 自动重定向或用户点击: → Dashboard（已自动登录，无需再次输入密码）
```

**Exit State**:

- 成功 → 用户已设置新密码并自动登录，进入 Dashboard
- Token 过期 → Screen 3 提示链接已过期 + 重新申请重置链接入口
- 放弃 → 用户关闭页面，密码未更改，下次仍可重新发起重置

**Empty State**: N/A（此 flow 无空状态）

---

## Component Kit

按使用频率排序（基于研究样本观察）：

| 优先级 | 功能概念 | 具体用途 |
|---|---|---|
| ★★★ | 操作按钮 | 所有 CTA（Social Auth / 主操作 / 次级操作 / 链接型） |
| ★★★ | 单行文本输入 | 注册表单（邮箱、密码、姓名、公司名） |
| ★★★ | 表单容器（含校验） | 注册表单的校验与提交包装 |
| ★★★ | 模态对话框 | 升级付费流（Pricing Modal + Checkout + Confirmation） |
| ★★★ | 单选组 | Onboarding 问卷单选题、定价方案选择 |
| ★★ | 进度条 | 注册步骤进度指示 |
| ★★ | 状态标签 | 定价页「Most Popular」标签、年付「节省 X%」标签 |
| ★★ | 内容卡片 | 定价方案卡片、Testimonial 卡片、Onboarding 步骤卡片 |
| ★★ | 标签页切换 | 支付方式切换（信用卡 / Google Pay） |
| ★★ | 操作通知（Toast） | 邮件已发送、试用已激活等非阻断确认 |
| ★★ | 开关 | 月付 / 年付切换 |
| ★ | 可折叠列表 | 定价页功能对比表折叠展开 |
| ★ | 加载骨架屏 | 注册完成后 Dashboard 数据加载占位 |
| ★ | 多选框 | 订阅条款同意勾选 |
| ★ | OTP 验证码输入 | Email 验证 OTP 6位输入 |
| ★ | 页面级警告横幅 | 企业邮箱校验失败提示、工作区已存在提示 |

---

## Anti-Patterns

基于研究样本中观察到的设计错误：

- **注册流中保留完整顶部导航**：用户在填写一半时跳回营销页，注册进度丢失，转化率骤降。→ 正确做法：进入注册流后隐藏所有导航链接，仅保留 Logo（允许回到首页）。

- **Onboarding 问卷用「请填写调研」框架呈现**：用户感知为负担而非收益，跳过率极高。→ 正确做法：用「帮你配置工作区 / 个性化你的产品」框架，每题说明「这样我们才能…」。

- **Email OTP 输入框无快捷跳转**：用户需切换 App 查看邮件，放弃率是提供快捷按钮场景的 2–3 倍。→ 正确做法：提供「打开 Gmail」「打开 Outlook」快捷 Button，Magic Link 优于 OTP。

- **定价页功能对比表在首屏全部展开**：用户面对 30+ 行功能对比，产生决策瘫痪，直接关闭。→ 正确做法：首屏只展示 3 张方案卡片，功能对比表放在卡片下方并默认折叠，用户主动展开。

- **升级付费跳转独立 /upgrade 页面**：用户失去当前产品上下文，支付完成后不知道如何返回，功能解锁感知延迟。→ 正确做法：升级流在 Modal 内完成，支付成功后 Modal 关闭即见功能解锁效果。

- **注册成功页无明确下一步 CTA**：用户停留在「恭喜注册成功」页，不知道该做什么，沉默流失。→ 正确做法：成功页必须有明确 CTA（「进入产品 / Get Started」），同时触发引导 Checklist。

- **工作区配置问卷超过 7 题**：每增加一道必填题，完成率下降约 15%。→ 正确做法：必填题 ≤ 4 题，其余设为可跳过，配置可在 Settings 中随时补充。
