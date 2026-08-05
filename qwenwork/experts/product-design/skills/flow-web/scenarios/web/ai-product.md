# Scenario: AI Product（AI 产品）

> **研究来源**：基于对 ChatGPT、Cohere、Raycast AI、ElevenLabs、Washington Post AI Assistant、MonoDesk、Microsoft Copilot、Google Bard 等 8 个真实产品 flow 的横向分析抽象，不代表任何单一产品的具体实现。

---

## Identity

**Definition**: AI 对话工具——产品的核心交互界面是与 AI 的对话，包括独立 AI chat 产品（如 ChatGPT、Claude）和嵌入 SaaS 应用中的 AI 助手（如 ElevenLabs support chat、MonoDesk Nexus、Raycast AI）。

**Canonical Examples**: ChatGPT、Claude.ai、Cohere Chat

**Not this scenario if**: AI 只是辅助功能（如写作建议气泡、代码补全），对话不是产品主界面；或产品核心是数据可视化（改用 data-analytics）。

---

## User Profile

| 维度 | 内容 |
|---|---|
| **主要角色** | End User（终端用户，提交任务给 AI）/ Power User（高频，上传文件、配置模型） |
| **核心目标** | 快速获得 AI 生成的答案、内容、代码或分析结果，并能继续对话迭代 |
| **心智模型** | 即时消息应用（WhatsApp、iMessage）——期待连续对话，左边历史、右边输入 |
| **使用频率** | 高频日常（核心用户每天多次），单次任务也可一次性使用 |
| **决策模式** | 探索发现型：问题往往是模糊的，通过对话逐步澄清 |
| **容错期望** | 中：AI 偶尔出错可接受，但界面操作错误（误删对话、文件上传失败）容错期望低 |

---

## IA Template

**导航模式**: Sidebar（左侧可折叠，存放对话历史）+ Main Chat Area（右侧主区域）
- 无传统顶部导航；模型切换和对话操作在顶部 bar 内联实现
- Sidebar 默认展开（宽屏），可折叠以扩大对话区域（Cohere 模式）
- 移动端：Sidebar 折叠为汉堡菜单或底部 Sheet

**页面层级**: 2 级（扁平，远比 SaaS 后台浅）
```
L1: Home / New Chat（空白输入态 + 建议 chips）
L2: Active Conversation（消息线程 + Composer）
（无 L3：设置等功能在全屏 Dialog 或 Settings 页）
```

**权限角色结构**:
```
（大多数 AI 产品无角色分级）
Free User  → 有用量上限，部分模型不可用
Pro User   → 全模型访问，更高速率，文件上传
Team/API   → 自定义系统提示，管理成员（进入 SaaS 管理后台模式）
```

**数据密度**: 低
- 主视图：消息气泡（单列，宽松行间距）
- 辅助视图：Sidebar 对话列表（紧凑，按日期分组）
- 不使用：Table、复杂表单、多列布局

**主要容器模式**:
| 场景 | 容器 |
|---|---|
| 文件上传 | Composer 内联 Chip + 附件预览 |
| 模型切换 | 顶部 DropdownMenu（内联，不打断对话） |
| 对话操作（重命名/删除/分享） | ContextMenu（右键或 ··· 菜单）→ AlertDialog（删除确认） |
| 用量限制 / Upgrade 提示 | Banner（非阻断）或 Dialog（阻断式 Paywall） |
| AI 设置（系统提示、温度） | 右侧 Sheet 或 Settings 全页 |

**导航骨架图（ASCII）**:
```
┌──────────────────────────────────────────────────────────────┐
│  [≡]  ModelName ▾                           [Share] [···]    │
├──────────────┬───────────────────────────────────────────────┤
│              │                                               │
│  + New Chat  │  ┌──────────────────────────────────────┐    │
│              │  │  [AI Avatar]  User message bubble     │    │
│  ─────────── │  │                                       │    │
│  Today       │  │  AI response (streaming text)         │    │
│  › Chat 1    │  │  [Copy] [Retry] [👍] [👎]             │    │
│  › Chat 2    │  │                                       │    │
│              │  │  [AI Avatar]  Next AI turn...         │    │
│  Yesterday   │  └──────────────────────────────────────┘    │
│  › Chat 3    │                                               │
│  › Chat 4    │  ─────────────────────────────────────────── │
│              │  [📎] [🔍] [Ask anything...      ] [🎤] [→]  │
└──────────────┴───────────────────────────────────────────────┘

Home / New Chat（空白态）：
┌──────────────────────────────────────────────────────────────┐
│  [≡]  ChatGPT ▾                              [Get Plus]      │
├──────────────┬───────────────────────────────────────────────┤
│              │                                               │
│  + New Chat  │         What's on your mind today?           │
│              │                                               │
│  ─────────── │   ┌─────────────────────────────────────┐    │
│  Today       │   │ [📎] Ask anything...         [🎤][→] │    │
│  › Chat 1    │   └─────────────────────────────────────┘    │
│  Yesterday   │                                               │
│  › Chat 2    │   [Summarize text] [Get advice] [Analyze ▾]  │
│              │                                               │
└──────────────┴───────────────────────────────────────────────┘
```

---

### 图 2：关键状态对比图（Key State Variations）

```
左：Active Chat 有消息（正常对话态）         右：New Chat 空白首页（冷启动态）

┌──────────────────────────────────────┐  ┌──────────────────────────────────────┐
│ [≡]  GPT-4o ▾           [Share][···]│  │ [≡]  ChatGPT ▾            [Get Plus] │
├──────────────┬───────────────────────┤  ├──────────────┬───────────────────────┤
│ + New Chat   │  ┌─────────────────┐  │  │ + New Chat   │                       │
│ ─────────── │  │ 👤 Summarize... │  │  │ ─────────── │   What's on your      │
│ Today        │  └─────────────────┘  │  │ Today        │   mind today?         │
│ › Chat 1  ●  │  ┌─────────────────┐  │  │ › Chat 1     │                       │
│ › Chat 2     │  │ 🤖 Here's a     │  │  │ › Chat 2     │  ┌──────────────────┐ │
│ Yesterday    │  │    summary of   │  │  │ Yesterday    │  │ [📎] Ask anything│ │
│ › Chat 3     │  │    the article: │  │  │ › Chat 3     │  │           [🎤][→]│ │
│ › Chat 4     │  │    1. Point A   │  │  │              │  └──────────────────┘ │
│              │  │    2. Point B   │  │  │              │                       │
│              │  │ [Copy][Retry]   │  │  │              │  [Summarize text]     │
│              │  └─────────────────┘  │  │              │  [Write code]         │
│              │  ─────────────────── │  │              │  [Get advice]         │
│              │  [📎] Follow up... → │  │              │  [Analyze data]       │
└──────────────┴───────────────────────┘  └──────────────┴───────────────────────┘
```

---

### 图 3：覆层层级图（Overlay Hierarchy）

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  [≡]  GPT-4o ▾                                         [Share]  [···]        │ ← Top Bar（z-100）
├──────────────┬───────────────────────────────────────────────────────────────┤
│  SIDEBAR     │                                        ┌─────────────────────┐ │
│  z-auto      │                                        │ Settings Sheet（右）│ │
│  + New Chat  │  ┌─────────────────────┐               │ z-index: 200        │ │
│  ─────────  │  │ 👤 Hey, analyze...  │               │                     │ │
│  Today       │  └─────────────────────┘               │ Model:  [GPT-4o ▾] │ │
│  › Chat 1 ●  │  ┌─────────────────────┐               │ System Prompt:      │ │
│  › Chat 2 ···│  │ 🤖 Here's the       │               │ ┌─────────────────┐ │ │
│  Yesterday   │  │    analysis...      │               │ │ You are a helpful│ │ │
│  › Chat 3    │  │                     │               │ │ assistant...     │ │ │
│  › Chat 4    │  │ [Copy][Retry][👍][👎]│              │ └─────────────────┘ │ │
│              │  └─────────────────────┘               │ Temperature: ──●──  │ │
│              │                                        └─────────────────────┘ │
│              │  ┌───────────────────────────────┐    ▲ 触发: 顶部 [···] Settings │
│              │  │   AlertDialog（中）z-index:300 │                               │
│              │  │   Delete conversation?        │                               │
│              │  │   This cannot be undone.      │                               │
│              │  │   [Cancel]   [Delete]         │                               │
│              │  └───────────────────────────────┘                               │
│              │   ▲ 触发: Sidebar ··· → Delete                                   │
│              │                                                                   │
│              │   ┌──────┐  ← Attachment Popover（z-200）                        │
│              │   │📄 File│  触发: 点击 Composer 左侧 [+]                        │
│              │   │🖼 Photo│                                                      │
│              │   │☁ Drive│                                                      │
│              │   └──────┘                                                       │
│              │  ─────────────────────────────────────────────────────────────  │
│              │  [+]  [📎 report.pdf ×]  Follow up...               [🎤]  [→]  │
└──────────────┴───────────────────────────────────────────────────────────────┘
  ┌──────────────────────────────────────────────────┐
  │  ✓ Link copied to clipboard   [×]                 │  ← Toast（底部，z-400）
  └──────────────────────────────────────────────────┘

触发关系说明:
- Attachment Popover（输入框左上角）: 点击 [+] 触发，从按钮展开，z-200；选完自动关闭
- AlertDialog（中）: Sidebar ··· → Delete 触发，居中阻断，z-300；强制确认才可删除
- Settings Sheet（右）: 顶部 [···] → Settings 触发，右侧滑入，z-200，含模型/系统提示配置
- Toast（底）: 链接复制、对话删除成功等轻量反馈，z-400，3-5 秒自动消失
```

---

## 该场景独有的 IA/UX 决策

1. **Composer 是连续对话起点，不是一次性提交的表单字段** — AI 产品的输入区（Composer）在功能角色上等同于命令行/搜索框，而非普通文本表单。必须实现：自动扩展高度（随内容增长至约 8 行后出现内部滚动）、Enter 发送 / Shift+Enter 换行的快捷键约定（行业共识）、文件内联附件（通过 Chip 显示在输入区上方而非跳转上传页）。与 SaaS 表单最本质的区别：用户提交后 Composer 自动复位为「Follow up...」而非清空——这一措辞暗示对话可以继续，而不是「任务已完成，请重新开始」，是 AI 产品留存的关键体验细节。

2. **流式输出不是加载状态，是核心内容体验** — AI 产品必须实现逐字流式渲染（Streaming），让用户在 AI 生成过程中即可阅读。全页 Spinner 或骨架屏是错误做法——用户看不到任何内容，焦虑感与等待时间成正比。正确做法：生成开始后立即切换到文字渲染（即使只有几个字）；首次响应延迟 > 500ms 时允许用 Skeleton 占位，但一旦有内容必须立刻切换；Composer 内出现「Stop generating」⬛ 按钮，让用户可中断不满意的生成——ChatGPT、Raycast AI 均为行业共识实现。

3. **AI 错误必须内联在对话气泡位置，不能用 Toast** — AI 生成失败（网络超时、内容策略拒绝、模型过载）必须将错误渲染在 AI 气泡应出现的位置，附带 Retry 按钮，而非显示 3 秒后消失的 Toast。原因：①AI 对话是有序序列，错误消息是对话时间线的一部分，必须在时间线上可查；②Toast 消失后用户翻看对话才发现缺少了一条回复，造成「幻觉式」困惑（为什么对话在这里中断了？）；③Retry 按钮必须就在失败气泡附近，不需要用户重新输入完整内容。这是 AI 产品区别于所有其他 Web 场景错误处理的独有约定。

4. **对话历史是产品主导航，Sidebar 操作是高频任务** — AI 产品的 Sidebar 对话列表不是辅助功能——对于日活用户，切换历史对话、重命名、搜索是每天多次发生的操作。必须实现：Today / Yesterday / Past Week 日期分组（防止长列表无序化）；行 hover 显示「···」菜单（Rename / Share / Delete，不常驻以保持列表整洁）；Rename 使用 inline 编辑而非 Dialog（行业共识：ChatGPT、Cohere、Copilot 均如此）；Delete 使用 AlertDialog 二次确认 + Toast「Undo」。Sidebar 必须可折叠（Cohere 模式），让用户在长文档阅读或代码 Review 时将对话区扩展为全宽。

5. **空白 Home 必须提供任务建议 Chips，消解白纸效应** — AI 产品的 Home / New Chat 空白页如果只有 Composer 输入框，新用户面对空白不知道该问什么——「白纸效应」是 AI 产品冷启动的最大障碍。行业共识（ChatGPT、Washington Post AI 均如此）：Composer 下方提供 4–6 个任务型建议 Chips（如「Summarize text」「Write code」「Analyze data」「Get advice」），点击即填充 Composer 并等同于发送。Chips 的作用是示范「AI 能做什么」而非功能导航——它们必须是任务描述（动词+名词），不是功能模块名称（「文件上传」「设置」），目的是启发用户的第一个问题。

---

## Canonical Flows

> 以下 flow 基于 8 个真实产品样本的横向分析抽象。括号内标注「行业共识」表示 3 个以上产品采用相同模式。

---

### Flow 1: Send Message & Receive Response（发送消息并获得回复）

**在此场景的特殊性**: AI 产品的核心 flow 比 SaaS CRUD 更短（2-4 屏），但有独有的「流式输出」状态——AI 逐字渲染回复，用户在生成过程中即可阅读。所有样本均有「建议 Chips」降低首次使用门槛（Washington Post 的类别标签、ChatGPT 的任务 Chip）。提交后的 Loading 状态必须可见：Washington Post 用「Checking sources...」文字，Raycast 用「Thinking」气泡，ChatGPT 用打字动画。生成完成后，回复气泡底部固定出现操作图标（Copy / Retry / 👍👎），行业共识。

**行业共识**：出现在全部 8 个样本产品中，是 AI 产品最高频的用户任务。

**前置条件**: 无（未登录访客可使用有限次数的试用对话；已登录用户可访问完整功能）
**若前置条件不满足**: 试用次数耗尽的访客 → 触发注册引导 Modal；Free 用户配额耗尽 → 触发 Flow 4 Paywall

**Entry**: 打开产品（进入 Home / New Chat 页面）

```
Screen 1: Home / New Chat（空白输入态）
  主操作: 点击 Composer 输入文字 → 点击发送
  关键组件: Textarea（Composer，自动扩展高度）
            Button（Send，圆形或箭头图标，primary）
            [可选] Chips（任务建议，如「Summarize text / Get advice」）
            [可选] Button（Attach，📎 图标，见 Flow 2）
  → 点击发送: 进入 Screen 2（对话视图）
  → 点击建议 Chip: 填充 Composer → 等同于发送

Screen 2: Generating Response（AI 生成中）
  主操作: 等待 AI 回复（Streaming / Loading State）
  关键组件: Message Bubble（用户消息，右对齐或带 Avatar）
            AI Response Bubble（左侧，逐字流式渲染，显示打字光标）
            [可选] Skeleton 或 Spinner（首次响应延迟 > 500ms 时）
            Button（Stop generating，⬛ 图标，出现在 Composer）
  → 生成完成: Screen 3

Screen 3: Response Delivered（回复完成）
  主操作: 阅读 / 复制 / 追问
  关键组件: AI Response Bubble（完整 Markdown 渲染：标题、列表、代码块）
            Action Bar（气泡底部：Copy 图标、Retry / Regenerate 图标、👍👎）
            [可选] Sources（引用来源链接，Washington Post 模式）
            Composer（重置为空，placeholder 变为「Follow up...」）
  → 用户继续输入: 循环回 Screen 2
  → 点击「New Chat」: 返回 Screen 1
```

**Exit State**:
- ✅ Success：完整 AI 回复渲染完成，Composer 复位可追问，对话自动保存至 Sidebar 列表
- ❌ Error（网络超时）：AI bubble 内显示 inline 错误 + Retry 按钮（不用 Toast）
- ↩ Stop：用户点击「Stop generating」，截断回复，Action Bar 出现「Continue」选项

**Empty State**:
- 空白 Composer + 建议 Chips（降低冷启动门槛）
- Sidebar 无历史时：仅显示「+ New Chat」，无「暂无对话」文字

---

### Flow 2: Attach File & Ask Question（上传文件并提问）

**在此场景的特殊性**: 文件附件不触发新页面，而是内联到 Composer 中——这是 AI 产品区别于表单式上传的核心 IA 决策。ChatGPT 10 屏样本显示：附件入口藏在 Composer 左侧的「+」图标后面，需要 Discovery 动作；上传后以小型 Chip/缩略图显示在 Composer 内；文件随消息一起发出（不是单独的「上传」步骤）。多文件支持：ChatGPT 允许连续添加，缩略图排列在输入框上方。Cohere 的文档对话（flow 3832）将已有文档作为会话上下文，并在右侧 Panel 持久展示「Referenced Files」。

**行业共识**：ChatGPT（图片）、Cohere（文档）、ElevenLabs（音频上下文）均采用 Composer 内联附件模式。

**前置条件**: 用户已登录；账户为 Pro/付费套餐（Free 用户通常不支持文件上传，或有严格限制）
**若前置条件不满足**: Free 用户点击 📎 → 提示「Upgrade to Pro to attach files」+ 升级入口；即触发 Flow 4

**Entry**: Chat 界面 → 点击 Composer 左侧「📎」或「+」图标

```
Screen 1: Attachment Menu
  主操作: 选择附件来源
  关键组件: Popover（从「+」按钮展开）
            Menu Items（本地文件 / 照片库 / Google Drive 等）
  → 选择「本地文件」: 系统文件选择器（原生） → Screen 2

Screen 2: File Attached（附件预览态）
  主操作: 确认附件 + 输入问题 → 发送
  关键组件: Composer（扩展：文件缩略图 Chip 显示在输入区上方）
            Chip（含文件名、类型图标、× 删除按钮）
            Textarea（输入与文件相关的问题）
            Button（Send，primary）
  → 上传失败（文件太大 / 格式不支持）: Composer 内 inline 错误
  → 移除文件: 点击 Chip 上的 ×，恢复普通 Composer

Screen 3: Response with Context（含文件上下文的回复）
  主操作: 阅读 AI 对文件内容的分析 / 回答
  关键组件: User Message Bubble（含文件缩略图 inline 展示）
            AI Response Bubble（引用文件内容的格式化回复）
            [可选] References Panel（右侧：文件列表，Cohere 模式，适合多文档）
            Action Bar（Copy / Retry）
  → 继续追问: 循环回 Composer（文件已不再显示，属于对话上下文）
```

**Exit State**:
- ✅ Success：AI 回复包含对文件内容的分析；用户消息 bubble 内含文件缩略图
- ❌ Error（格式不支持）：Composer 内 inline 错误「不支持 .xxx 格式，请上传 PDF / PNG / JPG」
- ↩ Remove：点击 × 移除文件 Chip，Composer 恢复，无其他影响

**Empty State**:
- 首次使用文件附件：Tooltip 提示「支持 PDF、图片、Word 文档」

---

### Flow 3: Manage Conversation（管理对话历史）

**在此场景的特殊性**: AI 产品的「对话管理」入口藏在 Sidebar 的行 hover 操作里（···菜单），不像 SaaS 后台用 Table 行操作。研究样本（Microsoft Copilot flow 5524 / 5525、ChatGPT）显示：重命名对话是低频操作，通过 ContextMenu → inline 编辑或 Dialog；删除必须有二次确认（AlertDialog）；「分享」则触发独立 Modal（生成可分享链接）。重要区别：这些操作都不离开当前对话视图，只通过 Sidebar 右键或 ··· 触发，对主内容区零打扰。

**行业共识**：ChatGPT、Copilot、Google Bard、Cohere 均采用 Sidebar ··· hover 菜单触发对话操作。

**前置条件**: 用户已登录；Sidebar 中有至少 1 条历史对话记录
**若前置条件不满足**: 无历史对话时 Sidebar 仅显示「+ New Chat」，无可操作的列表项

**Entry**: Sidebar 对话列表 → hover 某条对话 → 点击「···」图标

```
Screen 1: Sidebar With Context Menu
  主操作: 选择要执行的操作
  关键组件: ContextMenu / DropdownMenu（条目：Rename / Share / Delete）
            Sidebar 对话列表（其余项变灰，当前项高亮）
  → 选择「Rename」: Screen 2A
  → 选择「Share」: Screen 2B
  → 选择「Delete」: Screen 2C

Screen 2A: Rename（内联重命名）
  主操作: 修改对话标题 → 按 Enter 确认
  关键组件: Sidebar 列表项变为 Input（inline，当前标题预填充）
            [无独立 Dialog——行业共识：内联编辑]
  → Enter / 失焦: 保存新标题，恢复列表项显示
  → Esc: 取消，恢复原标题

Screen 2B: Share（分享对话）
  主操作: 生成可分享链接 → 复制
  关键组件: Dialog（标题：「Share this conversation」）
            Link Input（只读，显示生成的链接）
            Button（Copy link, primary），Button（Close）
            [可选] Toggle（「公开链接」开关）
  → Copy: Toast「链接已复制」，Dialog 可保持打开
  → Close: 关闭 Dialog，无任何变更

Screen 2C: Delete Confirmation（删除确认）
  主操作: 确认删除
  关键组件: AlertDialog（标题：「Delete conversation?」）
            描述文字（「This conversation will be permanently deleted.」）
            Button（Delete, destructive red），Button（Cancel, ghost）
  → Delete: 对话从 Sidebar 移除，如果正在查看该对话则重定向到 New Chat
  → Cancel: 关闭 AlertDialog，无变更
```

**Exit State**:
- ✅ Rename：Sidebar 标题即时更新，Toast 可选（通常无 Toast，内联更新即反馈）
- ✅ Share：对话链接已在剪贴板，Toast「链接已复制」
- ✅ Delete：对话从列表消失，Toast「对话已删除」（可选「撤销」，Copilot 模式）
- ↩ Cancel：任意步骤取消，无变更

---

### Flow 4: 用量上限触发升级

**在此场景的特殊性**: AI 产品的用量限制（Quota）是 Free→Pro 转化最高频的触发点——用户在最高参与度时刻（正在使用中）遭遇 Paywall，是转化率最高也最敏感的节点。与 marketing-site 场景的 Paywall 不同，AI 产品的 Paywall 是「中断式」（Interrupt）——用户发出消息后才触发，而非主动浏览定价页。关键设计原则：Paywall Dialog 必须保留已发送的消息和上下文（不能清空对话），升级完成后应自动继续处理被中断的请求。

**前置条件**: 用户为 Free 用户；已达到当月/当日用量上限（消息条数、文件上传次数或高级模型使用次数）
**若前置条件不满足**: Pro 用户不触发此 flow（即使使用频繁）；未登录访客触发的是注册引导 Modal，非此 flow

**Entry**: Free 用户在 Composer 发送消息后，后端返回配额耗尽响应，触发 Paywall

**Screens**:

```
Screen 1: Chat Interface → Quota Hit（配额耗尽触发）
  视觉状态: AI 气泡位置出现限制提示（非 Toast），对话历史仍完整可见
  关键组件:
    - 系统提示气泡（在 AI 应回复的位置）:
        「You've reached your free limit for today.」
        「Upgrade to continue chatting with GPT-4o.」
    - [Upgrade to Plus]  主 CTA 按钮（蓝色/品牌色）
    - [See what's included]  次要链接
    - Composer 变为禁用态（placeholder: 「Upgrade to continue...」）
    - 可选 Non-blocking Banner（顶部黄色）: 「You have 0 messages left today」
  → 点击 Upgrade to Plus: Screen 2

Screen 2: Paywall Modal（方案对比）
  视觉状态: 全屏居中 Dialog，背景对话可见但 Dim；展示 Free vs Pro 功能对比
  关键组件:
    - Modal 标题: 「Upgrade to ChatGPT Plus」
    - 方案卡片（Free vs Pro 并排对比）:
        Free: ✓ 基础模型  ✗ GPT-4o  ✗ 文件上传  ✗ 高速响应
        Plus（$20/mo）: ✓ GPT-4o  ✓ 文件上传  ✓ DALL·E  ✓ 高速响应
    - 计费周期切换（月付 / 年付，年付显示「Save 17%」Badge）
    - [Subscribe to Plus — $20/mo]  主 CTA
    - [Maybe later]  次要关闭链接（关闭 Modal，回到 Screen 1 受限态）
  → 点击 Subscribe: Screen 3
  → 点击 Maybe later: 关闭 Modal，Composer 仍禁用

Screen 3: Checkout（支付信息）
  视觉状态: 通常跳转至第三方支付页（Stripe Checkout）或内嵌支付表单
  关键组件:
    - 订单摘要: 「ChatGPT Plus · Monthly · $20.00」
    - 支付方式: 信用卡输入 / Apple Pay / Google Pay
    - [Subscribe]  主 CTA
    - 取消链接（返回 Modal）
    - 法律文本: 「You'll be charged $20 on the 27th of each month. Cancel anytime.」
  → 支付成功: Screen 4
  → 支付失败: 内联错误（卡被拒），保留表单，提示换卡

Screen 4: 升级成功 + 自动继续
  视觉状态: 返回 Chat 界面；Paywall 消失；Composer 恢复可用；已中断的对话自动重试
  关键组件:
    - 成功 Toast（底部）: 「🎉 Welcome to ChatGPT Plus! Enjoy unlimited access.」
    - Composer 恢复正常态（placeholder: 「Ask anything...」）
    - 原被中断的消息自动重新发送（或提示「Retry your last message?」）
    - 顶部 Header 右侧「Get Plus」按钮消失（改为账户 Avatar）
```

**Exit State**:

- 升级成功 → 返回对话，Composer 解锁，Toast 确认，原请求自动重试
- 支付失败 → 保持 Screen 3 内联错误，提示换卡，对话上下文保留
- 取消升级（Maybe later）→ 关闭 Modal，Free 配额限制仍生效，Composer 禁用

**Empty State**: N/A（此 flow 针对活跃对话中的配额中断，无空状态）

---

## Component Kit

按使用频率排序（基于研究样本观察）：

| 优先级 | 功能概念 | 具体用途 |
|---|---|---|
| ★★★ | AI 对话输入框 | AI Composer 输入框（自动扩展高度，支持快捷键提交） |
| ★★★ | 操作按钮 | 发送按钮（圆形 icon-only）、Stop、Retry、Copy 等所有操作 |
| ★★★ | 可滚动区域 | 消息线程区域（支持平滑滚动、自动滚动到底部） |
| ★★ | 加载骨架屏 | AI 回复首次加载时的骨架屏（3-4 行不定宽） |
| ★★ | 下拉操作菜单 | 模型切换（顶部 bar）、Sidebar ··· 操作菜单 |
| ★★ | 危险操作确认 | 删除对话的二次确认 |
| ★★ | 模态对话框 | 分享对话（生成链接）、Upgrade Paywall |
| ★★ | 气泡提示 | 操作图标说明（Copy / Retry / 👍👎 的 label） |
| ★★ | 操作通知（Toast） | 链接已复制、对话已删除 等非阻断确认 |
| ★ | 锚定浮层 | 附件类型选择菜单（从 + 按钮展开） |
| ★ | 状态标签 | Composer 内文件附件预览、建议 Chips |
| ★ | 侧边面板/抽屉 | AI 设置面板（系统提示 / 模型参数，右侧抽屉） |
| ★ | 单个可折叠区域 | Sidebar 左侧折叠控制（扩大对话区域，Cohere 模式） |
| ★ | 分隔线 | Sidebar 对话列表的日期分组分隔线 |

---

## Anti-Patterns

基于研究样本中观察到的设计错误：

- **全页 Spinner 替代流式输出**：AI 生成过程中用全页 loading 遮罩，用户无法阅读任何内容。→ 正确做法：流式逐字渲染（Streaming），始终给用户可读内容；至少显示「Thinking...」气泡，让用户知道 AI 在处理。

- **错误用 Toast 显示 AI 错误**：网络超时或模型错误时显示 Toast，3 秒后消失，用户不知道回复失败了。→ 正确做法：错误信息直接渲染在 AI 气泡位置（inline），附 Retry 按钮，用户可重试。

- **附件上传是独立页面流程**：文件上传跳转到独立的「上传页」，破坏对话连续感。→ 正确做法：附件内联到 Composer，通过 Chip 显示预览，随消息一起发送。

- **Home 空白页只有输入框**：新用户看到空白 Composer 不知道该怎么用。→ 正确做法：提供建议 Chips（任务型：Summarize / Analyze / Get advice），或示例对话，降低冷启动门槛（ChatGPT、Washington Post 均如此）。

- **Copy 按钮不在气泡上**：用户需要手动选中文字复制。→ 正确做法：每条 AI 回复气泡底部固定显示 Copy 图标（hover 显示或常驻），Cohere、Raycast、ChatGPT 均有。

- **对话删除无确认**：在 Sidebar ··· 菜单点击 Delete 立即删除，无法撤销。→ 正确做法：必须用 AlertDialog 二次确认，并提供 Toast「撤销」选项（Copilot 模式）。

- **Sidebar 无折叠功能**：Sidebar 始终占据 20-25% 宽度，小屏幕下压缩对话阅读区域。→ 正确做法：Sidebar 可折叠（Cohere 样本显示：折叠后对话区域扩展为全宽，适合长文档阅读场景）。

- **模型切换触发整页刷新**：切换 AI 模型时重载整个页面，丢失 Composer 中的草稿内容。→ 正确做法：模型切换在 header DropdownMenu 内联完成，仅影响下一次请求，不影响已有对话内容。
