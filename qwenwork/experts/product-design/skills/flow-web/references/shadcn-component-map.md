# shadcn Component Map

> **文件用途**：定义 Spark Design Flow Skills 中可使用的 shadcn/ui 组件清单，说明各组件的适用场景、使用规范，以及与 Spark DS 未来组件的对应关系。
> SKILL.md 在 Step 4 GENERATE 阶段读取本文件，确保组件选用有规范依据。

---

## 一、组件使用原则

1. **只用已定义的组件**。本文件未列出的 shadcn 组件，使用前须在 DS Coverage Notes 中标注「建议评估引入」。
2. **语义优先**。按交互语义选组件，而非视觉相似度。弹窗用 `Dialog`，抽屉用 `Sheet`，不混用。
3. **组合有规则**。常见的 2–3 个组件组合在第三节统一定义，不自行发明组合。
4. **Spark DS 路线图意识**。每次使用 shadcn 组件，都在心里对应一个未来的 Spark DS 组件名，并在 DS Coverage Notes 中输出。
5. **主题一致性**。所有组件的样式必须使用 shadcn 默认主题的 CSS 变量，详见 `references/shadcn-theme-config.md`。

---

## 二、组件清单（按功能分类）

### 2.1 布局与容器

| shadcn 组件 | Spark DS 规划名 | 适用场景 | 不适用场景 |
|---|---|---|---|
| `Card` | `SparkCard` | 内容分组、统计数据展示、列表项卡片 | 不用于主页面容器，不用于表单容器 |
| `Separator` | `SparkDivider` | 内容区块的视觉分隔 | 不替代间距，不在表格内用 |
| `ScrollArea` | `SparkScrollArea` | 固定高度容器内的可滚动内容 | 不用于整页滚动 |
| `ResizablePanelGroup` | `SparkSplitPanel` | 可拖拽分割的双栏/三栏布局 | 移动端不使用 |
| `AspectRatio` | `SparkAspectRatio` | 媒体内容（图片/视频）的比例锁定 | 非媒体内容不使用 |

---

### 2.2 导航

| shadcn 组件 | Spark DS 规划名 | 适用场景 | 备注 |
|---|---|---|---|
| `NavigationMenu` | `SparkNavMenu` | 顶部主导航，含下拉子菜单 | 营销网站、顶部 nav 型产品 |
| `Tabs` | `SparkTabs` | 同一页面内的内容切换（详情页分区、设置分类） | 最多 6 个 tab，超出用 Select |
| `Breadcrumb` | `SparkBreadcrumb` | 3 级及以上页面层级的路径指示 | 2 级以内不需要 |
| `Pagination` | `SparkPagination` | 超过 20 条数据的列表分页 | 无限滚动场景不使用 |
| `Sidebar` *(shadcn)* | `SparkSidebar` | B2B 后台的一级导航、设置页的分类导航 | 移动端折叠为抽屉 |

---

### 2.3 数据展示

| shadcn 组件 | Spark DS 规划名 | 适用场景 | 备注 |
|---|---|---|---|
| `Table` | `SparkTable` | 结构化数据列表（用户列表、订单列表、日志等） | 行数超过 50 须分页或虚拟滚动 |
| `Badge` | `SparkBadge` | 状态标签（Active / Pending / Error）、计数标记 | 不用于操作按钮，不用于主要导航 |
| `Avatar` | `SparkAvatar` | 用户头像展示，支持 fallback 到首字母 | 不用于 logo、不用于图标 |
| `Progress` | `SparkProgress` | 任务完成度、文件上传进度、引导步骤进度 | 不表示数据占比（用图表） |
| `Skeleton` | `SparkSkeleton` | 数据加载中的占位（卡片、列表行、文本块） | 全页加载用 Spinner，局部加载用 Skeleton |
| `Tooltip` | `SparkTooltip` | 图标按钮的说明文字、截断文本的完整内容 | 不用于错误提示，不用于必要信息 |
| `HoverCard` | `SparkHoverCard` | 悬停展示用户卡片、链接预览等富文本预览 | 不用于操作触发 |
| `Collapsible` | `SparkCollapsible` | 可折叠的内容区（FAQ、高级筛选、日志详情） | — |
| `Accordion` | `SparkAccordion` | 多个可折叠项的分组（设置分区、FAQ 列表） | — |

---

### 2.4 表单与输入

| shadcn 组件 | Spark DS 规划名 | 适用场景 | 必须配合使用 |
|---|---|---|---|
| `Form` | `SparkForm` | 所有表单容器，处理校验逻辑 | 必须配合 `react-hook-form` |
| `Input` | `SparkInput` | 单行文本输入、邮箱、数字 | 配合 `Form` 使用 |
| `Textarea` | `SparkTextarea` | 多行文本、描述、备注 | 配合 `Form` 使用 |
| `Select` | `SparkSelect` | 单选下拉（选项 ≤ 20 个） | 选项 > 20 改用 `Combobox` |
| `Combobox` | `SparkCombobox` | 带搜索的单选/多选（选项多、需过滤） | — |
| `Checkbox` | `SparkCheckbox` | 多选项（独立或组）、同意条款 | — |
| `RadioGroup` | `SparkRadioGroup` | 互斥单选（选项 ≤ 6 个） | 超过 6 个用 Select |
| `Switch` | `SparkSwitch` | 开关类设置（即时生效，无需提交） | 不用于表单内的 checkbox 替代 |
| `Slider` | `SparkSlider` | 范围选择（价格区间、音量、百分比） | — |
| `DatePicker` *(Calendar + Popover)* | `SparkDatePicker` | 日期选择、日期范围选择 | — |
| `InputOTP` | `SparkOTPInput` | 验证码输入（短信 / 邮件 OTP） | — |

---

### 2.5 覆盖层与反馈

| shadcn 组件 | Spark DS 规划名 | 适用场景 | 不适用场景 |
|---|---|---|---|
| `Dialog` | `SparkDialog` | 需要用户确认的操作（删除确认、表单提交）；信息量 ≤ 1 表单的创建 | 信息量大的复杂表单，改用全页面或 Sheet |
| `Sheet` | `SparkDrawer` | 从边缘滑出的详情面板、筛选面板、较长表单 | 不用于简单确认（改用 Dialog） |
| `AlertDialog` | `SparkAlertDialog` | 不可逆操作的二次确认（删除、清空、取消订阅） | 不用于普通信息展示 |
| `Popover` | `SparkPopover` | 锚定于触发元素的轻量浮层（日期选择、颜色选择、快捷操作） | 不用于大量内容 |
| `DropdownMenu` | `SparkDropdownMenu` | 操作菜单（行内 "..." 菜单、头像菜单） | 不用于导航 |
| `ContextMenu` | `SparkContextMenu` | 右键菜单（文件管理器、画布类产品） | 普通 Web 产品不使用 |
| `Toast` / `Sonner` | `SparkToast` | 操作结果的非阻断性反馈（保存成功、复制成功） | 不用于错误（错误用 inline 提示），不用于需要用户操作的提示 |
| `Alert` | `SparkAlert` | 页面级警告/信息横幅（账户欠费、功能限制、权限提示） | 不用于操作反馈 |
| `Command` | `SparkCommand` | 全局搜索、快捷命令面板（Cmd+K） | — |

---

### 2.6 操作与控制

| shadcn 组件 | Spark DS 规划名 | 适用场景 | 变体说明 |
|---|---|---|---|
| `Button` | `SparkButton` | 所有可点击操作 | variant: `default`（主）/ `secondary`（次）/ `outline`（边框）/ `ghost`（幽灵）/ `destructive`（危险） |
| `Toggle` | `SparkToggle` | 视图切换（列表/网格）、格式工具栏（加粗/斜体） | — |
| `ToggleGroup` | `SparkToggleGroup` | 互斥视图切换（多个 Toggle 组合） | — |

---

## 三、常用组件组合（Composition Patterns）

以下是经过验证的、高频出现的组件组合，使用时直接参考，不自行发明。

### Pattern A：列表页工具栏（List Toolbar）

```
Input(search) + Select(filter) + Button(primary CTA)
```

**用于**：数据列表页顶部的搜索、筛选、新建操作区。
**规则**：搜索框在左，筛选 Select 居中，主 CTA 在右。

---

### Pattern B：表格行操作（Table Row Actions）

```
DropdownMenu("...") → [Edit, Duplicate, ---separator---, Delete(destructive)]
```

**用于**：数据表格每行右侧的操作列。
**规则**：
- 操作 ≤ 2 个：直接展示为 `Button(ghost)` 文字按钮
- 操作 ≥ 3 个：收入 `DropdownMenu`，用 `Separator` 隔开「危险操作」

---

### Pattern C：创建/编辑表单（Create / Edit Form）

```
Dialog 或 Sheet
  └── Form
        ├── Input × N（主要字段）
        ├── Select × N（下拉字段）
        ├── Textarea（描述类）
        └── Button(submit) + Button(cancel, ghost)
```

**选择 Dialog 还是 Sheet**：
- 字段 ≤ 5 个 → `Dialog`
- 字段 > 5 个，或有分组 → `Sheet`（宽度 500px+）
- 字段复杂、多分区 → 全页面 Form

---

### Pattern D：详情页头部（Detail Page Header）

```
Breadcrumb
Avatar + Title + Badge(status)
Button(Edit, secondary) + Button(Delete, destructive variant ghost)
```

**用于**：Record 详情页的顶部区域。
**规则**：Badge 紧跟 Title，操作按钮组靠右对齐。

---

### Pattern E：空状态（Empty State）

```
Card(centered content)
  ├── [Icon or Illustration placeholder]
  ├── Heading（说明为什么是空的）
  ├── Text（引导用户做什么）
  └── Button(primary CTA)（触发创建/导入动作）
```

**规则**：空状态必须有一个可操作的 CTA，不允许只显示「暂无数据」文字。

---

### Pattern F：分步向导（Step Wizard）

```
Progress(step indicator, custom)
  Screen 1: Form + Button("Next")
  Screen 2: Form + Button("Back", ghost) + Button("Next")
  Screen N: Review + Button("Back", ghost) + Button("Submit", primary)
  Confirmation: [Success state]
```

**规则**：
- 步骤数 2–4 步：顶部 Progress 显示步骤序号
- 步骤数 5–6 步：考虑 Sidebar 步骤导航
- 每步底部必须有「返回上一步」

---

### Pattern G：设置页（Settings Layout）

```
Sidebar(settings nav, compact)
  └── [Active Section Content]
        ├── Heading + Description
        ├── Separator
        ├── [Setting Item: label + Switch / Input / Select]
        └── Button("Save Changes", primary, sticky bottom or inline)
```

**规则**：
- 每个 Section 独立保存（不全局提交）或明确标注「保存全部」
- 修改未保存时，Save 按钮激活，页面标注「未保存更改」

---

### Pattern H：AI 对话界面（Chat Interface）

```
Sidebar(conversation history, optional)
Main Panel:
  ├── ScrollArea(message list)
  │     ├── [User Message bubble]
  │     └── [AI Response: streaming text + code blocks]
  └── Textarea(input) + Button("Send") + [Attachment / Voice controls]
```

**规则**：
- AI 回复流式输出时，Button("Send") 变为 Button("Stop", destructive)
- 代码块用 `pre + code` 加 `Button("Copy")`
- 历史对话用 `Sidebar`，可折叠

---

## 四、场景 × 核心组件矩阵

快速查阅各场景最常用的组件组合：

| 场景 | 必用组件 | 常用组合 Pattern |
|---|---|---|
| SaaS 管理后台 | Sidebar, Table, Dialog, Sheet, Badge, Form | A + B + C + G |
| AI 产品 | ScrollArea, Textarea, Button, Collapsible, Tooltip | H |
| 营销网站 | NavigationMenu, Button, Card, Separator, Accordion | — |
| 移动端引导 | Progress, Card, Button, Checkbox, Switch | F |
| 数据分析 / BI | Tabs, Card, Select, DatePicker, Skeleton | — |
| 电商 | Card, Badge, Button, Sheet(Cart), AlertDialog | — |
| 开发者工具 | Tabs, Sidebar, Command, Toast, Badge | A + G |
| 内部运营工具 | Table, Badge, AlertDialog, Sheet, Tabs | B + D + G |
| 金融科技 | Table, AlertDialog, Badge, InputOTP, Progress | B + D |
| 社区 / 社交 | Avatar, Card, Button, Textarea, DropdownMenu | — |
| 医疗健康 | Calendar, Form, Badge, AlertDialog, Progress | C + F |
| 教育科技 | Progress, Card, Tabs, Badge, Collapsible | — |

---

## 五、禁止行为

以下行为明确禁止，在 Flow 生成时不得出现：

- **不用 `div` 模拟组件**。需要一个按钮，必须用 `Button`，不用 `<div onClick>`
- **不硬编码颜色**。所有颜色必须用 Tailwind 语义类（`text-destructive`）或 CSS 变量（`bg-background`）
- **不混用 Dialog 和 Sheet 的语义**。确认框用 `AlertDialog`，表单弹层用 `Dialog` 或 `Sheet`
- **不在 Toast 里放错误**。表单错误用 inline 提示（`Form.Message`），系统错误用 `Alert`
- **不省略空状态**。每个列表页/数据区域必须有 Empty State 的处理（即使只是注释说明）
- **不省略 Loading 状态**。按钮提交时必须有 loading 状态，数据加载时必须有 Skeleton
- **不使用自定义像素值**。间距用 `p-4`、`m-2`，圆角用 `rounded-md`，不用 `p-[12px]`、`rounded-[6px]`
