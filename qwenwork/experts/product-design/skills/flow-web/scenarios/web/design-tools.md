# Scenario: Design Tools（设计/创意工具）

> **研究来源**：基于对 Glorify、Canva、Butter、Modyfi、Replo 等 5 个真实产品 flow 的横向分析抽象，不代表任何单一产品的具体实现。

---

## Identity

**Platform**: Web
**Definition**: Browser-based design or creative editing tool where users create visual assets (graphics, videos, presentations, web pages) using a canvas-centric editor with templates, layers, and export capabilities.

**Canonical Examples**: Canva（通用图形设计）、Figma（UI/协作设计）、Adobe Express / Glorify（品牌物料设计）

**Not this scenario if**: 产品是文档/写作工具（改用 web/ai-product 或 saas-management）；产品是代码编辑器或 IDE（改用 web/developer-tools）；产品是仅展示静态内容的网站（改用 web/marketing-site）；产品是移动端原生设计 App（改用 ios/design-tools）。

---

## User Profile

| 维度 | 内容 |
|---|---|
| **主要角色** | Designer / Creator（专业设计师或内容创作者）；Non-designer（无设计背景的市场/运营人员，依赖模板）|
| **核心目标** | 创建视觉物料 → 编辑完善 → 导出/分享 |
| **心智模型** | 熟悉 Photoshop/PowerPoint 的层级操作概念；对画布编辑、图层、属性面板有基本认知 |
| **使用频率** | 中频（按项目节奏，每次会话 30 分钟~数小时）|
| **决策模式** | 任务驱动型：有明确的输出目标（社交图片、演示文稿、Logo）|
| **容错期望** | 低：操作需要 Undo/Redo 支持；Auto-save 失败 = 严重损失 |

---

## IA Template

**导航模式**: 三栏 Canvas Editor 布局（Left Panel + Canvas Center + Right Panel）+ Top Bar

- **Top Bar**：项目标题（可编辑）+ 工具选项 + Auto-save 状态 + Export/Share 按钮 + 用户头像
- **Left Panel**：Layers（图层面板）/ Assets（素材库）/ Templates（模板库）—— 通过 Tab 切换
- **Canvas Center**：主编辑区域，底部有工具选择 Toolbar（Select / Draw / Text / Shape）
- **Right Panel**：Properties（属性面板，随选中对象变化：颜色 / 尺寸 / 字体 / 动画）

**页面层级**: 2 级
```
L1: Dashboard（项目列表，Recent designs + 创建入口）
L2: Canvas Editor（三栏编辑器，单屏全功能）
```

注：与大多数 SaaS 产品不同，Design Tools 的核心工作在 L2 完成，页面层级极浅。

**权限角色结构**:
```
Owner       → 创建 / 编辑 / 导出 / 分享 / 删除
Editor      → 编辑 + 导出，不能删除他人设计
Commenter   → 仅查看 + 留评论（不可编辑画布）
Viewer      → 仅查看，通过分享链接访问
```

**数据密度**: 低（Dashboard：卡片式缩略图；Canvas Editor：工作区主导，面板信息密度中等）

**主要容器模式**:
| 场景 | 容器 |
|---|---|
| 选择模板/尺寸 | Modal（Create Design Modal，Dashboard 触发）|
| 导出设置 | Sheet / Popover（从 Top Bar Export 展开）|
| 分享/邀请协作者 | Modal（Share Modal，含权限设置）|
| 素材/图片上传 | Left Panel 内嵌（不跳转独立上传页）|
| 图层/对象 Context Menu | 右键 ContextMenu 或 Canvas Toolbar Popover |

**导航骨架图（ASCII）**:
```
┌────────────────────────────────────────────────────────────────┐
│  ← Projects  |  [Project Title ✏]  [Saved ✓]  [Export▾] [Share] [Avatar▾] │
├──────────────┬──────────────────────────────┬──────────────────┤
│              │                              │  Properties      │
│  Layers  ▼  │                              │  ─────────────── │
│  ─ Frame 1  │                              │  W: 1080  H:1920 │
│    ├ Image  │       CANVAS                 │  X: 0     Y: 0   │
│    ├ Text   │                              │  ─────────────── │
│    └ Badge  │    [selected element]        │  Fill: ██ #FF0000│
│             │    □─────────────────□       │  Opacity: 100%   │
│  Assets  ▼  │    │                 │       │  ─────────────── │
│  Templates  │    │                 │       │  Font: Inter     │
│  Uploads    │    │                 │       │  Size: 24px      │
│  Stock      │    □─────────────────□       │  Weight: Bold    │
│             │                              │                  │
│             │  ╔══╗ T  ◇  ✏  🔷  ⎘       │  Animation  ▼   │
└──────────────┴──────────────────────────────┴──────────────────┘
```

---

### 图 2：关键状态对比图（Key State Variations）

```
左：Canvas Editor 有设计元素（选中态）           右：Dashboard 空状态（引导创建第一个设计）

┌────────────────────────────────────┐  ┌────────────────────────────────────┐
│← Projects│[My Design ✏][✓ Saved]  │  │ My Designs              [+ Create] │
├────────────┬───────────────────────┤  ├────────────────────────────────────┤
│ Layers  ▼  │                       │  │                                    │
│ ─ Frame 1  │   [Object Selected]   │  │                                    │
│   ├ Image  │   □───────────────□   │  │          🎨                        │
│   ├ Text   │   │  Hello World  │   │  │  You haven't created any           │
│   └ Badge  │   □───────────────□   │  │  designs yet.                      │
│            │                       │  │                                    │
│ Assets  ▼  │     W: 320  H: 80    │  │  [Create your first design]        │
│ Templates  │     Fill: ██ #FF5500  │  │                                    │
└────────────┴───────────────────────┘  └────────────────────────────────────┘
```

---

### 图 3：覆层层级图（Overlay Hierarchy）

```
┌──────────────────────────────────────────────────────────────────────────┐
│  ← Projects  [Project Title ✏]  [✓ Saved]         [Export▾]  [Share]    │ ← Top Bar（z-100）
├──────────────┬───────────────────────────────────────┬───────────────────┤
│  Left Panel  │         Canvas（主编辑区）              │  Properties       │
│              │                                        │                   │
│  Layers  ▼   │   [Element Selected]                   │  W: 320  H: 80    │
│  ─ Frame 1   │   □────────────────────────────────□   │  Fill: ██ #FF5500 │
│    ├ Image   │   │  Design content                │   │  Opacity: 100%    │
│    └ Text    │   □────────────────────────────────□   │  Font: Inter 24px │
│              │                                        │                   │
│  Assets  ▼   │   ┌──────────────────────────────────┐ │                   │
│              │   │  Export Settings Sheet（右侧滑入） │ │                   │
│              │   │  z-index: 200                    │ │                   │
│              │   │  File type: ○PNG ●JPG ○PDF ○SVG  │ │                   │
│              │   │  Quality: ████████░░  80%        │ │                   │
│              │   │  Size: ○1x ●2x ○3x               │ │                   │
│              │   │  [Download]                      │ │                   │
│              │   └──────────────────────────────────┘ │                   │
│              │     ▲ 触发: Top Bar [Export▾] 展开      │                   │
│              │                                        │                   │
│              │   ┌──────────────────────────────────────────────────┐    │
│              │   │  Create Design Modal（中）z-index: 300            │    │
│              │   │  [Social] [Presentation] [Video] [Custom]        │    │
│              │   │  [Instagram 1:1] [Story 9:16] [YouTube 16:9] ... │    │
│              │   │  [Cancel]                  [Create design]       │    │
│              │   └──────────────────────────────────────────────────┘    │
│              │     ▲ 触发: Dashboard [+ Create a design]                  │
│              │                                                            │
│              │   ┌──────────────────────────────────────────────────┐    │
│              │   │  Share Modal（中）z-index: 300                    │    │
│              │   │  Anyone with link ▾      [View only ▾][Copy Link]│    │
│              │   │  Invite: [email____] [Can edit▾]  [Send Invite]  │    │
│              │   │  ─────────────────────────────────────────────── │    │
│              │   │  Alex Wang  alex@co  [Editor ▾]  [Remove]        │    │
│              │   └──────────────────────────────────────────────────┘    │
│              │     ▲ 触发: Top Bar [Share] 按钮                           │
│              │                                                            │
│              │   ┌──────────────────────────────────────┐                │
│              │   │  Canvas ContextMenu（z-400）           │                │
│              │   │  Cut / Copy / Paste                   │                │
│              │   │  Group selection                      │                │
│              │   │  Bring to front / Send to back        │                │
│              │   │  Delete                               │                │
│              │   └──────────────────────────────────────┘                │
│              │     ▲ 触发: 画布元素右键点击                               │
└──────────────┴────────────────────────────────────────────────────────────┘
  ┌────────────────────────────────────────┐
  │  ✓ Link copied to clipboard   [×]      │  ← Toast（z-500）
  └────────────────────────────────────────┘

触发关系说明:
- Export Settings Sheet（右侧）: Top Bar [Export▾] 触发，右侧滑入，z-200，背景 Canvas 保持可见
- Create Design Modal（中）: Dashboard [+ Create] 触发，z-300，选模板/尺寸后进入编辑器
- Share Modal（中）: Top Bar [Share] 触发，z-300，链接分享与成员邀请在同一 Modal 内
- Canvas ContextMenu（z-400）: 画布元素右键触发，元素级操作（层级 / 编组 / 删除）
- Toast（z-500）: 「Link copied」/ 「Invite sent」/ 「Export complete」轻量反馈，3-5 秒消失
```

---

## 该场景独有的 IA/UX 决策

1. **三栏 Canvas Editor 是设计工具的专属 IA 约束，所有操作在单一页面内完成** — 与 SaaS 产品「Dashboard → List → Detail → 表单」的多页层级结构不同，设计工具只有两级页面层级：L1 Dashboard（入口）和 L2 Canvas Editor（工作区）。所有任务在 L2 内完成——模板选择用 Modal、素材上传用 Left Panel、属性调整用 Right Panel、导出用 Sheet——没有「跳转到独立设置页」的逃逸路径。如果任何操作需要跳出 Canvas 到新页面，则意味着用户离开了工作上下文（已编辑的画布），会引发强烈的「找回原状态」焦虑。

2. **Right Properties Panel 是「内容感知型」面板，而非静态设置栏** — Properties Panel 的内容必须随用户画布选中状态实时切换：选中文字 → 字体/大小/行高/对齐；选中图片 → 裁剪/滤镜/不透明度；选中形状 → 填充颜色/描边/圆角；多选 → 编组/对齐工具；无选中 → 画布尺寸/背景色。这与 SaaS 的 Settings Panel（内容固定由页面决定）根本不同——Properties Panel 的状态由用户在画布的「点击选中行为」驱动，而非由路由决定。这要求 Right Panel 设计多套内容状态，且切换必须无感知（< 100ms）。

3. **Auto-save + Undo/Redo 是设计工具的双重安全网，两者不可替代** — Auto-save 解决「关闭页面 / 断网」导致的数据丢失；Undo/Redo（Ctrl+Z / Ctrl+Y）解决「操作后悔」。两者服务不同的焦虑场景：用户可能撤销 30 步操作找回状态，但 Auto-save 不会因此丢失这 30 步之前的内容。Top Bar 必须持续显示「Saved ✓」/ 「Saving...」/ 「Connection lost」三种明确状态；任何模糊状态（不显示、只在失败时显示）都会导致用户强迫性手动保存或刷新页面——而刷新恰好会导致更多潜在丢失。

4. **AI 功能必须作为画布内嵌操作，不能跳出到独立 AI 工具页** — Canva 的 Magic Animate（flow_id 8048）是典型示范：Page Animations 入口 → AI 分析画布 → 推荐风格 + 备选方案（在画布上方叠加展示）→ 用户选择 → 动画效果直接应用到当前画布并在 Timeline 实时更新——整个流程在 Canvas Editor 内完成，从未跳出。AI 生成图片/文字/动画的结果必须能「一键插入当前画布层」，而非要求用户从独立页面下载后再手动上传。设计工具的 AI 功能是编辑流程的内嵌加速器，不是独立功能模块。

5. **「发布到社交媒体」与「导出文件」是并行的两条出口，路径分叉后不应合并** — Canva flow_id 8046 展示了两条出口的分叉点：同一个「Share / Publish」按钮入口，下方分为「Download」（文件落到本地磁盘）和「Share to social」（通过 OAuth 直接 Post 到 Instagram/TikTok/LinkedIn，文件不落地）两条路径。「发布」路径还包含 Social Media Preset 选择（格式缩略图 + 分辨率标签，如 Instagram Reel 1080×1920 / 9:16），选中 Preset 后画布尺寸和 Timeline 自动重格式——这是导出路径没有的步骤。将两条路径混合成同一个流程会让非设计师用户看到「导出 JPG」和「分辨率」时困惑。

---

## Canonical Flows

### Flow 1: 从模板创建设计稿（Create Design from Template）

**在此场景的特殊性**: 与 SaaS 的「创建资源」不同，Design Tools 的创建入口是带「尺寸 + 模板」的专用 Modal，不是普通表单；模板选择是高视觉化的，用分类+缩略图网格展示；编辑器加载完成后 Auto-save 立即激活（用户无需手动保存）

**前置条件**: 用户已登录；账号处于正常状态（未欠费/未被禁用）
**若前置条件不满足**: 未登录用户点击 Create → 跳转注册/登录页；账号被禁用 → Dashboard 显示恢复账号提示，Create 按钮 disabled

**Entry**: 用户在 Dashboard 点击「+ Create a design」或「New Project」

**Screens**:
```
Screen 1: Dashboard
  主操作: 点击「+ Create a design」
  关键组件: Card（最近的设计稿缩略图）, Button（Create CTA）, Badge（上次编辑时间）
  → 点击 Create: 打开 Screen 2（Modal）
  → 点击已有 Card: 直接进入 Canvas Editor（Screen 3）

Screen 2: Create Design Modal
  主操作: 选择画布类型和模板
  关键组件:
    - Tabs（Social Media / Presentation / Video / Custom）
    - 尺寸选项卡片网格（带预览图：Instagram Post 1080×1080 / Story 1080×1920 等）
    - 搜索框（搜索模板名称或尺寸）
    - 自定义尺寸输入（Width × Height + 单位 px/cm/in）
  → 点击模板/尺寸: 进入 Screen 3（Canvas Editor 加载）
  → 点击 Cancel: 返回 Dashboard

Screen 3: Canvas Editor
  主操作: 在画布上编辑元素（添加文字/图片/形状/模板元素）
  关键组件:
    - Left Panel: Layers 面板（层级树）+ Assets Tab（素材库 + 上传）+ Templates Tab（模板库）
    - Center Canvas: 画布 + 对象选择框（Bounding Box + 控制手柄）
    - Right Properties Panel: 随选中对象切换（文字属性 / 图片属性 / 形状属性）
    - Top Bar: 项目标题（可编辑）+ Auto-save 状态（「Saved ✓」/ 「Saving...」）
    - Bottom Toolbar: 工具切换（Select / Text / Shape / Pen / Image）
    - Right-click Context Menu: 编组 / 复制 / 删除 / 调整层级
  → Auto-save 持续工作，Top Bar 显示「Saved」状态
  → 点击「←Projects」: 返回 Dashboard（设计已自动保存）
```

**Exit State**: 设计稿自动保存，Dashboard 中出现新设计稿缩略图（含项目标题和编辑时间）
**Empty State**: Dashboard 无设计稿时显示：「You haven't created any designs yet」+ 明确 CTA「Create your first design」

---

### Flow 2: 编辑并导出（Edit & Export）

**在此场景的特殊性**: 导出不是单一下载按钮，而是必须经过格式选择（PNG/JPG/PDF/MP4）+ 质量/分辨率设置 + 页面范围选择三步；导出过程中有进度指示（不是即时下载，大文件/视频需要处理时间）；导出完成后提供直接下载链接和「Export Again」选项

**前置条件**: 用户已登录；已在 Canvas Editor 中打开设计稿；用户角色为 Owner 或 Editor（Commenter/Viewer 无导出权限）
**若前置条件不满足**: Commenter/Viewer 角色 → Top Bar 无「Export」按钮，仅显示查看/评论工具；设计稿加载中 → Export 按钮 disabled 直到完全加载

**Entry**: 用户在 Canvas Editor 中点击 Top Bar 的「Export」或「Download」按钮

**Screens**:
```
Screen 1: Canvas Editor（当前状态，用户已完成编辑）
  主操作: 点击 Top Bar「Export / Download」
  关键组件: Top Bar Button「Export▾」（Dropdown 或直接 Sheet）
  → 点击 Export: 展开 Screen 2（Right Side Sheet 或 Dropdown Panel）

Screen 2: Export Settings（Side Panel / Popover，不离开 Canvas Editor）
  主操作: 配置导出参数
  关键组件:
    - 文件类型 RadioGroup（PNG / JPG / PDF / SVG / MP4 — 按设计类型决定可选项）
    - 质量 Slider（JPG: 1-100%；MP4: Low/Medium/High/4K）
    - 页面范围 Checkbox（All Pages / Current Page / Selected Pages）
    - 尺寸倍率 Select（1x / 2x / 3x，仅静态图片）
    - 预计文件大小（实时显示）
    - Button「Download」（主 CTA，点击触发导出）
  → 点击 Download: Screen 3（导出进行中）
  → 关闭 Panel: 返回 Canvas（不影响编辑）

Screen 3: Export Progress
  主操作: 等待导出完成（无需操作）
  关键组件: Progress Bar（百分比 + 预计时间）, 导出设置摘要（格式 / 质量）
  → 导出完成: Screen 4
  → 用户离开页面: 后台继续导出，完成后 Toast 通知

Screen 4: Export Completed
  主操作: 下载文件
  关键组件:
    - Success State（文件名 + 格式 + 大小）
    - Button「Download File」（主 CTA）
    - Link「Export Again」（修改参数重新导出）
    - 自动下载（如浏览器允许，无需点击按钮）
```

**Exit State**: 文件下载到本地；Export Panel 关闭；Canvas Editor 保持打开（用户可继续编辑）
**Empty State**: 不适用

---

### Flow 3: 分享与邀请协作（Share & Invite Collaborator）

**在此场景的特殊性**: 分享功能与导出功能入口相邻但目的不同（导出 = 输出文件，分享 = 邀请他人访问）；协作权限必须在分享时明确设置（View only / Can comment / Can edit）；分享链接生成后可随时关闭（Revoke），不是永久有效

**前置条件**: 用户已登录；已在 Canvas Editor 中打开设计稿；用户角色为 Owner（只有 Owner 可邀请协作者和管理分享权限）
**若前置条件不满足**: Editor 角色 → Share 按钮可见，但仅能复制链接，无法邀请新成员；Commenter/Viewer → 无 Share 按钮，仅能通过已有链接访问

**Entry**: 用户在 Canvas Editor 点击 Top Bar「Share」按钮

**Screens**:
```
Screen 1: Canvas Editor
  主操作: 点击「Share」按钮
  关键组件: Share Button（Top Bar，通常有品牌色高亮）
  → 点击 Share: 打开 Screen 2（Modal）

Screen 2: Share Settings Modal
  主操作: 设置分享权限并复制链接 / 邀请协作者
  关键组件:
    - Link Section: 「Anyone with link」+ 权限 Select（View only / Can comment / Can edit）+ 「Copy Link」Button
    - Invite Section: Email 输入框（支持多人，逗号分隔）+ 权限 Select + 「Send Invite」Button
    - 已邀请成员列表（Member Row：头像 + 名字 + 邮箱 + 权限 Badge + 移除）
    - 切换「Public」/ 「Only invited people」ToggleGroup（控制链接是否公开可访问）
  → 点击「Copy Link」: Toast「Link copied」，Modal 保持打开
  → 点击「Send Invite」: 邮件发出，成员出现在下方列表；Modal 保持打开
  → 关闭 Modal: 返回 Canvas Editor

Screen 3: Collaborator View（协作者视角）
  入口: 协作者点击邮件链接后进入
  关键组件:
    - 同一个 Canvas Editor，但根据权限不同：
      - Can edit：完整三栏布局，可修改画布
      - Can comment：Canvas 只读 + 评论浮层（点击画布任意位置添加 Pin 评论）
      - View only：只读画布，无评论/编辑工具
    - Top Bar 显示所有在线协作者头像（实时同步）
```

**Exit State**: 分享链接已生成，协作者收到邀请邮件；分享状态持久，可在 Share Modal 中随时管理或 Revoke
**Empty State**: 无已邀请成员时，Member 列表区域显示「Only you have access」

---

---

### Flow 4: 发布到社交媒体（Publish to Social Media）

**在此场景的特殊性**: 「发布到社交」与「导出文件」共用同一个 Share/Publish 入口，但在分叉菜单处明确拆分为两条独立路径——发布路径需要 Social Media Preset 选择（平台格式缩略图 + 分辨率，如 Instagram Reel 9:16）并自动重格式画布，文件不落到本地磁盘；导出路径则输出文件到本地，无需平台授权。两条路径的视觉分叉必须在同一展开面板内一步完成，不可合并为同一流程。Canva（flow_id 8046）是此模式的核心参考。

**行业共识**: Canva（flow_id 8046）展示了 Social Preset 选择 + 画布自动重格式的完整结构；Replo（flow_id 2056）展示了 Publish 面板被 Integration 门控的另一种实现。

**前置条件**: 用户已登录；已在 Canvas Editor 中打开设计稿；用户角色为 Owner 或 Editor；目标社交平台账号已完成 OAuth 授权（否则在流程内触发授权弹窗）
**若前置条件不满足**: Commenter/Viewer → 无 Share 按钮，无法触发发布路径；未授权社交平台 → 在 Screen 3 内触发 OAuth 授权弹窗，授权完成后继续流程

**Entry**: 用户在 Canvas Editor 点击 Top Bar「Share」→ 在分叉菜单中选择「Share to social」

```text
Screen 1: Share / Export 路径分叉（Dropdown 展开）
  主操作: 点击 Share 按钮，识别并选择「Share to social」路径
  关键组件:
    - 分叉 Dropdown（两个并列路径卡片）:
        「Download」: 图标 + 「Save a copy to your device」→ Flow 2（导出文件）
        「Share to social」: 图标 + 「Post directly to Instagram, TikTok, LinkedIn」→ 本 Flow
    - 两条路径各自独立，标题 + 描述副文本清楚区分目的
  → 选择「Share to social」: Screen 2
  → 选择「Download」: Flow 2 Screen 2（导出路径）

Screen 2: Social Media Preset 选择
  主操作: 选择目标平台和尺寸格式
  关键组件:
    - Preset 卡片网格（格式缩略图 + 平台名 + 分辨率标签）:
        Instagram Post（1:1，1080×1080）/ Instagram Reel（9:16，1080×1920）
        TikTok Video（9:16，1080×1920）/ LinkedIn Post（1.91:1，1200×627）
        Twitter / X Post（16:9，1600×900）
    - 选中 Preset 后画布自动重格式（尺寸变化 + Timeline 时长更新）
    - 说明文案：「Your canvas will be resized. Content may need repositioning.」
  → 选择 Preset: 画布重格式（后台静默执行），进入 Screen 3
  → Cancel: 返回 Canvas Editor（画布尺寸不变）

Screen 3: 发布账号选择 + 内容填写
  主操作: 选择发布目标账号，填写描述文案，点击发布
  关键组件:
    - 已连接账号列表（RadioGroup）: 平台图标 + 账号名 + 「Change account」链接
    - 「+ Connect another account」（触发 OAuth 授权弹窗，Screen 3a）
    - Caption 文本框（多行，字符计数器，如 2200 chars for Instagram）
    - Hashtag 建议行（AI 推荐，点击追加）
    - 发布时间 RadioGroup:「Publish now」（默认）/ 「Schedule for later」（时间 Picker）
    - Button「Publish now」（主 CTA，全宽）
  → 未连接任何账号: Screen 3a（OAuth 授权）
  → 点击「Publish now」: 发布中 Loading → Screen 4

Screen 3a: OAuth 社交平台授权（首次使用可选分支）
  主操作: 通过 OAuth 连接目标社交账号
  关键组件: 系统 OAuth 弹窗（浏览器新窗口），授权完成后窗口自动关闭，账号出现在 Screen 3 列表
  → 授权完成: 返回 Screen 3（账号已添加到列表）
  → 取消授权: 返回 Screen 3（账号未添加）

Screen 4: 发布成功确认
  主操作: 确认发布状态，可选查看已发布帖子
  关键组件:
    - 成功插图 + 标题「Published to [Platform]!」
    - 摘要（平台 + 账号名 + 发布时间）
    - 主 CTA:「View post」（在新标签页打开社交平台对应帖子）
    - 次 CTA:「Back to editor」（返回 Canvas Editor）
  → 点击「View post」: 新标签页打开社交平台链接
  → 点击「Back to editor」: 返回 Canvas Editor
```

**Exit State**: Toast「Published to [Platform] ✓」在 Canvas Editor 背景短暂显示；Canvas Editor 保持打开，设计稿无变化；社交平台帖子已发布或进入排期队列
**Empty State**: 未连接任何社交平台时，Screen 3 只显示平台连接入口列表（无已有账号），直接引导 OAuth 授权

---

## Component Kit

按使用频率排序：

| 功能概念 | 具体用途 |
|---|---|
| 标签页切换 | Left Panel 的 Layers / Assets / Templates 切换 |
| 范围滑块 | 导出质量控制（JPG 压缩率 / MP4 分辨率）；对象不透明度调节 |
| 下拉操作菜单（右键）| 画布右键菜单（编组 / 复制 / 删除 / 层级调整）|
| 模态对话框 | Create Design Modal（模板选择）；Share Modal |
| 侧边面板/抽屉 | Export Settings Panel（从 Top Bar 展开的侧边设置面板）|
| 选择下拉 | 导出格式选择（PNG/JPG/PDF/SVG/MP4）；协作权限选择 |
| 单选组 | 文件类型选择（互斥选项）；页面范围选择 |
| 进度条 | 导出进度条（含百分比和预计时间）|
| 状态标签 | 图层类型标签（Image / Text / Shape / Group）；协作者权限标签 |
| 操作通知（Toast）| 「Link copied」/ 「Invite sent」/ 「Saved」确认通知 |
| 用户头像 | 协作者头像（Top Bar 在线状态 + Member 列表）|
| 单行文本输入 | 项目标题可编辑（inline）；自定义画布尺寸；邀请邮箱输入 |

---

## Anti-Patterns

- **导出只有单一下载按钮（Export is a single download button）**: 用户不知道输出格式和质量 → 正确做法：Export 必须经过格式选择 + 质量/分辨率配置，导出大文件时必须有进度指示
- **无 Auto-save 指示（No Auto-save indicator）**: 用户不知道工作是否已保存，焦虑或频繁手动 Ctrl+S → 正确做法：Top Bar 始终显示「Saved ✓」/ 「Saving...」/ 「Unsaved changes」状态
- **图层面板显示平铺列表（Layers panel shows flat list）**: 组合元素无法识别父子关系 → 正确做法：图层面板必须显示树形层级（缩进 + 折叠/展开控件），Group 内部子元素可见
- **模板库跳转独立页面（Template library opens a new page）**: 用户丢失当前画布和编辑进度 → 正确做法：模板库/素材库在 Left Panel 内展示，通过 Tab 切换，不离开编辑器
- **AI 生成内容跳出到独立工具页（AI generation opens a separate page）**: 用户点击「AI Generate Image」后离开 Canvas Editor，在新页面生成结果后需要手动下载再上传回画布 → 正确做法：AI 生成面板作为 Left Panel 的 Tab 或画布内 Popover，生成结果可一键插入当前画布层，全程不离开 Canvas Editor（Canva Magic Animate / Magic Media 的范本）
- **「发布到社交」和「导出文件」合并为同一流程（Publish and Export merged）**: 用户在「导出到 JPG」的流程里看到「连接 Instagram 账号」的步骤，困惑自己是在下载文件还是发布内容 → 正确做法：Share/Export 按钮展开后明确分叉为「Download」（文件导出，配置格式/质量/分辨率）和「Share to social」（OAuth 连接平台直接发布）两条路径，各自有独立的步骤和 CTA 文案
