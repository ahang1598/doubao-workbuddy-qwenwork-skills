# Spark Design Component Map（NPM 模式 · v5.5 校正版）

> **文件用途**：定义 Spark Design Flow Skills 中可使用的 Spark Design 组件清单，说明各组件的适用场景、正确 import 路径、子组件用法，以及常用组合模式。
> 本文件已对照 `spark-qoder-design` 原始仓库（`registry/basic/`、`registry/agent-manifest.json`）深度核验，所有 API 均以源码为准。
> SKILL.md 在 Step 4 GENERATE 阶段参考本文件，确保组件选用有规范依据。

---

## ⚡ 高频运行时错误速查（代码生成前必读）

> 以下两类错误在历次生成中复现率极高，生成代码前必须核对。

### 错误 A：DataTable 白屏（`TypeError: Cannot read properties of undefined (reading 'original')`）

**根因**：将 TanStack Table 的 `cell` 写法错误套用到 Spark DataTable。

```tsx
// ❌ 禁止：TanStack Table 风格，Spark DataTable 不认识 row.original
{ accessorKey: 'date', cell: ({ row }) => row.original.date }

// ✅ 正确：Spark DataTable 的 cell 直接接收数据行对象本身
{ key: 'date', cell: (row) => row.date }
```

### 错误 B：SidebarMenu 点击无响应 / active 高亮不更新

**根因**：Prop 名称与实际 API 不匹配。

| ❌ 错误写法 | ✅ 正确写法 |
|---|---|
| `activeId` | `selectedId` |
| `onSelect` | `onItemClick` |
| items 里带 `href` 字段 | items 无 `href`，路由跳转在 `onItemClick` 中用 `navigate()` 实现 |

---

### 错误 C：Tag `color="default"` 导致中性标签变成 primary 绿色

**根因**：Spark Tag 的 `color` 有效值为 16 种具名颜色，不包含 `"default"`。传入无效值时 CVA 忽略该 variant，回退到基础样式——在 mint 主题下基础样式是 primary 绿色。

```tsx
// ❌ 禁止
<Tag color="default">已关闭</Tag>
<Tag>新投递</Tag>          {/* 无 color prop 同样回退到 primary */}

// ✅ 正确：中性/灰色标签用 "slate"
<Tag color="slate">已关闭</Tag>
```

**16 种有效 color 速查**：

| 语义色 | 中性色 | 彩色装饰 |
|---|---|---|
| `primary` `success` `error` `warning` `info` `link` | `slate` `mauve` `lavender` `sage` | `blue` `teal` `orange` `pink` `purple` `yellow` |

---

### 错误 D：Tag `size` prop 不存在，`size="sm"` 完全无效

**根因**：Spark Tag 只有 `appearance` 和 `color` 两个 variant，无 `size` prop。传入 `size` 会被浏览器当作普通 HTML attribute 忽略，尺寸不变。

```tsx
// ❌ 禁止
<Tag size="sm">标签</Tag>

// ✅ 正确：需要更小字号时用 className 覆盖
<Tag color="slate" className="text-xs">标签</Tag>
```

---

### 错误 E：异步按钮用 `disabled` + 文字切换，未使用 `loading` prop

**根因**：Spark Button 内置 `loading` prop，自动渲染 spinner 并禁用交互。跳过此 prop 时按钮缺少视觉反馈，用户无法感知操作进行中。

```tsx
// ❌ 禁止
<Button disabled={isLoading}>{isLoading ? '发布中...' : '确认发布'}</Button>

// ✅ 正确：使用内置 loading prop，文字固定不变
<Button loading={isLoading}>确认发布</Button>
```

---

## 一、组件使用原则

1. **统一从 `sparkdesign` 包 import**。所有 Spark 组件均来自 `npm install sparkdesign`，import 格式：`import { Button, Tag } from 'sparkdesign'`
2. **语义优先**。按交互语义选组件，而非视觉相似度。
3. **主题一致性**。所有组件必须在 `<ThemeStyleProvider>` 内部渲染，否则颜色 token 无法解析。
4. **子组件必须完整**。复合组件（Select、Tabs、Dialog 等）必须使用完整的子组件链，不可只用根组件。
5. **禁止旧版路径**。不使用 `@/components/ui/basic/[component]`（v3 CLI 模式的路径，已废弃）。

---

## 二、已知组件清单（已对照 index.d.ts 验证）

所有组件 import 格式：

```tsx
import { Button, Tag, Select, SelectTrigger, SelectContent, SelectItem, /* ... */ } from 'sparkdesign'
```

### 2.1 基础操作

| 组件名 | 核心 Props | 适用场景 |
|---|---|---|
| `Button` | `variant="primary\|secondary\|tertiary\|outline\|ghost\|text"`, `size`, `disabled`, `loading`, `prefixIcon`, `suffixIcon` | 所有可点击操作 |
| `IconButton` | `variant="primary\|secondary\|tertiary\|ghost\|iconOnly"`, `size`, `disabled` | 只有图标、无文字的操作按钮 |
| `Switch` | `checked`, `onCheckedChange`, `disabled`, `size="md\|lg"` | 开关类设置（即时生效） |
| `Toggle` | `pressed`, `onPressedChange` | 单个二态切换按钮 |
| `ToggleGroup` + `ToggleGroupItem` | `type="single\|multiple"` | 互斥或多选的按钮组 |

**Button variant 说明：**

| variant | 用途 |
|---|---|
| `primary` | 主操作（提交、确认、保存）— 每个决策面只用一个 |
| `secondary` | 次操作（取消、返回） |
| `tertiary` | 三级辅助操作（更次级，无边框有背景） |
| `outline` | 轮廓按钮（带边框，无背景填充） |
| `ghost` | 幽灵按钮（工具栏图标按钮、行内操作） |
| `text` | 纯文字按钮（最轻量，无边框无背景） |

> ⚠️ **`danger` variant 不存在**。危险操作（删除、清空）使用 `AlertDialog` 确认 + `Button variant="primary"` 或 `variant="ghost"` 触发，样式通过 `className="text-error"` 表达语义。

---

### 2.2 数据展示

| 组件名 | 核心 Props | 适用场景 |
|---|---|---|
| `Tag` | `appearance="filled\|outline"`, `color`, `closable`, `onClose` | 状态标签、分类标记、可关闭标签 |
| `Progress` | `value` (0–100), `size` | 任务进度、文件上传、引导步骤 |
| `Tooltip` | `content`, `placement` | 图标按钮说明、截断文本完整内容 |
| `Skeleton` | `className` | 数据加载中的占位 |
| `Spinner` | `size` | 全页加载 / 按钮内 loading 态 |
| `Table` + 子组件 | `TableHeader`, `TableBody`, `TableRow`, `TableHead`, `TableCell` | 轻量数据表（行数少、无排序需求） |
| `DataTable` | `columns`, `data` | 有排序/筛选/分页的复杂数据表（推荐优先使用）— ⚠️ column schema 见下方，与 TanStack Table 不同 |
**DataTable column schema（必须遵循，与 TanStack Table 完全不同）：**

> ⚠️ **最常见错误**：把 TanStack Table 的 `accessorKey` + `cell: ({ row }) => row.original.xxx` 风格套用到 Spark DataTable。Spark DataTable 的 `cell` 回调**直接接收 row 对象本身**，没有 `original` 包装层。

```tsx
import { DataTable } from 'sparkdesign'

// Spark DataTable column schema（来自 DataTableColumn<TData> 接口）：
// {
//   key: string           ← 唯一 key（不是 accessorKey）
//   header: ReactNode     ← 列标题
//   cell?: (row: TData, index: number) => ReactNode  ← 直接收 row，不是 { row }
//   accessor?: keyof TData  ← 可选，简单取值时用（替代 cell）
// }

// ✅ 正确写法
const columns = [
  {
    key: 'date',
    header: '日期',
    cell: (row) => <span>{row.date}</span>,         // row 就是数据对象本身
  },
  {
    key: 'amount',
    header: '金额',
    cell: (row) => <span className="text-text">{row.amount}</span>,
  },
  {
    key: 'status',
    header: '状态',
    cell: (row) => <Tag color={row.status === 'success' ? 'success' : 'error'}>{row.status}</Tag>,
  },
]

<DataTable columns={columns} data={records} />

// ❌ 错误写法（TanStack Table 风格，不适用于 Spark）
const wrongColumns = [
  { accessorKey: 'date', header: 'Date', cell: ({ row }) => row.original.date },
]
```

| `Avatar` + `AvatarImage` + `AvatarFallback` | `src`, `alt` | 用户头像展示，支持 fallback 首字母 |
| ~~`Badge`~~ | — | ❌ **不存在**。计数标记用 `Tag`，无独立 Badge 组件 |

**Tag color 与 appearance 说明：**

`appearance` 控制填充样式，`color` 控制语义色：

| appearance | 说明 |
|---|---|
| `filled`（默认） | 有背景填充 |
| `outline` | 透明背景，只有边框 |

`color` 完整 16 色：

| color | 用途 |
|---|---|
| `primary` | 主品牌色标签 |
| `success` | 成功/激活状态 |
| `error` | 错误/失败状态 |
| `warning` | 警告状态 |
| `info` | 信息提示 |
| `link` | 链接样式（下划线） |
| `pink` `purple` `yellow` `orange` `teal` `blue` | 装饰性彩色标签 |
| `mauve` `slate` `lavender` `sage` | 中性/柔和彩色标签 |

---

### 2.3 表单与输入

> ⚠️ **sparkdesign 无 `Form` 组件**。表单容器和校验状态使用 `Field` 系列组件。

| 组件名 | 适用场景 |
|---|---|
| `Field` + `FieldLabel` + `FieldError` + `FieldDescription` | 表单字段容器（替代 `Form`），统一处理标签、校验提示、描述 |
| `FieldSet` + `FieldLegend` + `FieldGroup` | 多字段分组 |
| `Input` | 单行文本、邮箱、数字输入 |
| `Textarea` | 多行文本、描述、备注 |
| `Select`（复合） | 单选下拉，子组件见下方 |
| `Checkbox` | 多选项、同意条款 |
| `RadioGroup` + `RadioGroupItem` | 互斥单选（选项 ≤ 6 个） |
| `InputOTP` + `InputOTPGroup` + `InputOTPSlot` | 验证码输入（短信/邮件 OTP）— ⚠️ 旧名 `OtpInput` 已废弃 |
| `DatePicker` | 日期选择、日期范围选择 |
| `Slider` | 范围选择（价格区间、音量） |

**Select 子组件用法（必须完整）：**

```tsx
import { Select, SelectTrigger, SelectValue, SelectContent, SelectGroup, SelectItem } from 'sparkdesign'

<Select value={value} onValueChange={setValue}>
  <SelectTrigger>
    <SelectValue placeholder="请选择..." />
  </SelectTrigger>
  <SelectContent>
    <SelectGroup>
      <SelectItem value="a">选项 A</SelectItem>
      <SelectItem value="b">选项 B</SelectItem>
    </SelectGroup>
  </SelectContent>
</Select>
```

**Field 表单字段用法：**

```tsx
import { Field, FieldLabel, FieldError, FieldDescription, Input } from 'sparkdesign'

<Field>
  <FieldLabel>邮箱地址</FieldLabel>
  <Input type="email" value={email} onChange={...} />
  <FieldDescription>用于接收通知邮件</FieldDescription>
  {error && <FieldError>{error}</FieldError>}
</Field>
```

---

### 2.4 布局与导航

| 组件名 | 适用场景 |
|---|---|
| `Tabs`（复合） | 同一页面内的内容切换（最多 6 个 tab） |
| `Breadcrumb`（复合） | 3 级及以上页面层级路径指示 |
| `Pagination`（复合） | 超过 20 条数据的列表分页 |
| `SidebarMenu` | B2B 后台一级导航 — ⚠️ 旧名 `Sidebar` 已废弃，接受 `items` prop |
| `Card`（复合） | 内容分组、统计数据、列表项卡片 — 子组件：`CardHeader` `CardTitle` `CardDescription` `CardAction` `CardContent` `CardFooter` |
| `Separator` | 内容区块视觉分隔 |
| `ScrollArea` + `ScrollBar` | 固定高度容器内的可滚动内容 |
| `Collapse` + `CollapseItem` + `CollapseTrigger` + `CollapseContent` | 多个可折叠项的分组 — ⚠️ `Accordion` 不存在，用 `Collapse` 系列替代 |
| `Collapsible` + `CollapsibleTrigger` + `CollapsibleContent` | 单个可折叠内容区 |
| `CollapsibleCard` | 带标题的可折叠卡片容器 |

**Tabs 子组件用法（必须完整）：**

```tsx
import { Tabs, TabsList, TabsTrigger, TabsContent } from 'sparkdesign'

<Tabs defaultValue="overview">
  <TabsList>
    <TabsTrigger value="overview">概览</TabsTrigger>
    <TabsTrigger value="details">详情</TabsTrigger>
  </TabsList>
  <TabsContent value="overview">概览内容</TabsContent>
  <TabsContent value="details">详情内容</TabsContent>
</Tabs>
```

**Breadcrumb 子组件用法（无 items prop，必须用子组件）：**

```tsx
import { Breadcrumb, BreadcrumbList, BreadcrumbItem, BreadcrumbLink, BreadcrumbPage, BreadcrumbSeparator } from 'sparkdesign'

<Breadcrumb>
  <BreadcrumbList>
    <BreadcrumbItem>
      <BreadcrumbLink href="/dashboard">首页</BreadcrumbLink>
    </BreadcrumbItem>
    <BreadcrumbSeparator />
    <BreadcrumbItem>
      <BreadcrumbLink href="/users">用户管理</BreadcrumbLink>
    </BreadcrumbItem>
    <BreadcrumbSeparator />
    <BreadcrumbItem>
      <BreadcrumbPage>用户详情</BreadcrumbPage>
    </BreadcrumbItem>
  </BreadcrumbList>
</Breadcrumb>
```

**SidebarMenu 用法（data-driven，非子组件树）：**

> ⚠️ **Prop 名称易错**：正确是 `selectedId`（不是 `activeId`）和 `onItemClick`（不是 `onSelect`）。  
> ⚠️ **`SidebarMenuItem` 没有 `href` 字段**，路由跳转必须在 `onItemClick` 回调里手动用 `navigate()` 实现。

```tsx
import { SidebarMenu } from 'sparkdesign'
import type { SidebarMenuItem } from 'sparkdesign'
import { useNavigate, useLocation } from 'react-router-dom'

// items 里没有 href 字段
const items: SidebarMenuItem[] = [
  { id: 'dashboard', label: '概览', icon: <LayoutDashboard size={16} /> },
  { id: 'users', label: '用户管理', icon: <Users size={16} /> },
  { id: 'settings', label: '设置', icon: <Settings size={16} /> },
]

// id → path 的映射单独维护
const NAV_ROUTES: Record<string, string> = {
  dashboard: '/dashboard',
  users: '/users',
  settings: '/settings',
}

function Sidebar() {
  const navigate = useNavigate()
  const location = useLocation()
  const activeId = Object.entries(NAV_ROUTES).find(([, path]) => location.pathname.startsWith(path))?.[0] ?? 'dashboard'

  return (
    <SidebarMenu
      items={items}
      selectedId={activeId}           // ← 不是 activeId
      onItemClick={(item) => navigate(NAV_ROUTES[item.id])}  // ← 不是 onSelect
    />
  )
}
```

**Collapse（Accordion 替代）用法：**

```tsx
import { Collapse, CollapseItem, CollapseTrigger, CollapseContent } from 'sparkdesign'

<Collapse type="single" collapsible>
  <CollapseItem value="item-1">
    <CollapseTrigger>什么是 Spark Design？</CollapseTrigger>
    <CollapseContent>Spark Design 是一套 React 组件库...</CollapseContent>
  </CollapseItem>
  <CollapseItem value="item-2">
    <CollapseTrigger>如何安装？</CollapseTrigger>
    <CollapseContent>使用 npm install sparkdesign 安装。</CollapseContent>
  </CollapseItem>
</Collapse>
```

---

### 2.5 覆盖层与反馈

| 组件名 | 适用场景 | 不适用场景 |
|---|---|---|
| `Dialog`（复合） | 需确认的操作、字段 ≤ 5 个的创建表单 | 信息量大的复杂表单（用 Sheet） |
| `Sheet`（复合） | 从边缘滑出的详情/筛选面板、较长表单 | 简单确认（用 Dialog） |
| `Drawer`（复合） | 从边缘滑出的抽屉，移动端优先 | 桌面端大面板（用 Sheet） |
| `AlertDialog`（复合） | 不可逆操作二次确认（删除、清空） | 普通信息展示 |
| `Popover`（复合） | 锚定于触发元素的轻量浮层 | 大量内容（用 Sheet） |
| `DropdownMenu`（复合） | 操作菜单（行内 "..." 菜单、头像菜单） | 导航 |
| `Toaster` + `toast()` | 操作结果的非阻断性反馈 — ⚠️ 用法见下方，非组件渲染 | 错误（用 Field/Alert inline 提示） |
| `Alert`（复合） | 页面级警告/信息横幅，`variant="default\|info\|success\|warning\|destructive"` | 操作反馈（用 toast） |
| `Empty`（复合） | 空数据状态的标准展示容器 | — |

**Toast 正确用法（容器渲染一次 + 函数调用触发）：**

```tsx
// App Shell 内渲染一次 Toaster 容器：
import { Toaster } from 'sparkdesign'

<ThemeStyleProvider ...>
  <Toaster />
  {/* 其余内容 */}
</ThemeStyleProvider>

// 任意组件内触发 toast（函数调用，非 JSX）：
import { toast } from 'sparkdesign'

toast('操作成功')
toast.success('保存成功')
toast.error('操作失败，请重试')
```

**Empty 用法：**

```tsx
import { Empty, EmptyHeader, EmptyTitle, EmptyDescription, EmptyContent } from 'sparkdesign'

<Empty>
  <EmptyHeader>
    <EmptyTitle>暂无成员</EmptyTitle>
    <EmptyDescription>邀请成员加入，开始协作</EmptyDescription>
  </EmptyHeader>
  <EmptyContent>
    <Button variant="primary">邀请成员</Button>
  </EmptyContent>
</Empty>
```

**Dialog 子组件用法：**

```tsx
import { Dialog, DialogTrigger, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter, DialogClose } from 'sparkdesign'

<Dialog>
  <DialogTrigger asChild>
    <Button variant="primary">新建资源</Button>
  </DialogTrigger>
  <DialogContent>
    <DialogHeader>
      <DialogTitle>新建资源</DialogTitle>
      <DialogDescription>填写资源基本信息</DialogDescription>
    </DialogHeader>
    {/* 表单内容 */}
    <DialogFooter>
      <DialogClose asChild><Button variant="secondary">取消</Button></DialogClose>
      <Button variant="primary">创建</Button>
    </DialogFooter>
  </DialogContent>
</Dialog>
```

**Sheet 子组件用法：**

```tsx
import { Sheet, SheetTrigger, SheetContent, SheetHeader, SheetTitle, SheetFooter, SheetClose } from 'sparkdesign'

<Sheet>
  <SheetTrigger asChild>
    <Button variant="ghost">筛选</Button>
  </SheetTrigger>
  <SheetContent side="right">
    <SheetHeader>
      <SheetTitle>筛选条件</SheetTitle>
    </SheetHeader>
    {/* 筛选表单 */}
    <SheetFooter>
      <SheetClose asChild><Button variant="secondary">重置</Button></SheetClose>
      <Button variant="primary">应用</Button>
    </SheetFooter>
  </SheetContent>
</Sheet>
```

**AlertDialog 子组件用法：**

```tsx
import { AlertDialog, AlertDialogTrigger, AlertDialogContent, AlertDialogHeader, AlertDialogTitle, AlertDialogDescription, AlertDialogFooter, AlertDialogCancel, AlertDialogAction } from 'sparkdesign'

<AlertDialog>
  <AlertDialogTrigger asChild>
    <Button variant="danger">删除</Button>
  </AlertDialogTrigger>
  <AlertDialogContent>
    <AlertDialogHeader>
      <AlertDialogTitle>确认删除？</AlertDialogTitle>
      <AlertDialogDescription>此操作不可撤销，数据将永久删除。</AlertDialogDescription>
    </AlertDialogHeader>
    <AlertDialogFooter>
      <AlertDialogCancel>取消</AlertDialogCancel>
      <AlertDialogAction>确认删除</AlertDialogAction>
    </AlertDialogFooter>
  </AlertDialogContent>
</AlertDialog>
```

### 2.6 主题管理

| 组件名 | 核心 Props | 说明 |
|---|---|---|
| `ThemeStyleProvider` | `appearance`, `theme`, `style` | 必须包裹整个应用，管理主题和暗色模式 |

**Props 速查**：

| Prop | 可用值 | 说明 |
|---|---|---|
| `appearance` | `'light' \| 'dark'` | 亮/暗色模式 |
| `theme` | `'mint'`（默认）、`'parchment'` | 主题色调（`qoder` 不存在，禁止使用） |
| `style` | `'neutral' \| 'compact' \| 'soft' \| 'sharp' \| 'dense'` | 视觉密度风格 |

---

### 2.7 AI / Chat 专属组件（AI 产品场景优先使用）

> sparkdesign 内置了完整的 AI 对话 UI 组件，AI 产品场景应优先使用，而非手动用 div 构建。

| 组件名 | 适用场景 |
|---|---|
| `ChatInputRoot` + `ChatInputAbove` + `ChatInputBox` + `ChatInputAttachments` + `ChatInputInput` + `ChatInputActions` + `ChatInputActionsLeft` + `ChatInputActionsRight` + `ChatInputSendButton` + `ChatInputFooterLeft` | AI 对话输入框完整组合 |
| `Response` | AI 回复气泡，支持 streaming、thinking、steps 阶段 |
| `UserMessage` | 用户消息气泡 |
| `MarkdownBody` | 渲染 Markdown 格式内容 |
| `StreamingMarkdownBlock` | 流式 Markdown 渲染（边输出边显示） |
| `ThinkingIndicator` | AI 思考中动画占位 |
| `GenerationStatusBar` | 生成状态进度条 |
| `ReasoningStep` | 推理步骤展示 |
| `FileCard` + `FileAttachment` + `ImageAttachment` | 附件/图片展示卡片 |
| `ToolInvocationCard` | 工具调用状态卡片 |
| `PermissionCard` | 权限请求确认卡片 |
| `ConversationAnchorNav` | 对话历史锚点导航 |

**ChatInput 基础用法：**

```tsx
import { ChatInputRoot, ChatInputBox, ChatInputInput, ChatInputActions, ChatInputActionsRight, ChatInputSendButton } from 'sparkdesign'

<ChatInputRoot>
  <ChatInputBox>
    <ChatInputInput
      placeholder="输入消息..."
      value={input}
      onChange={(e) => setInput(e.target.value)}
    />
    <ChatInputActions>
      <ChatInputActionsRight>
        <ChatInputSendButton
          disabled={!input.trim() || isStreaming}
          onClick={handleSend}
        />
      </ChatInputActionsRight>
    </ChatInputActions>
  </ChatInputBox>
</ChatInputRoot>
```

---

### 2.8 补充实用组件（v5.4 新增，已对照 src/components/index.ts 确认）

| 组件名 | 适用场景 |
|---|---|
| `ButtonGroup` + `ButtonGroupSeparator` + `ButtonGroupText` | 横排多操作按钮组（如 Bold / Italic / Underline 工具栏） |
| `EllipsisText` | 单行溢出截断，比 CSS `truncate` 更可控，支持自定义省略内容 |
| `InputGroup` + `InputGroupAddon` + `InputGroupButton` | 带前后缀的输入框（如 URL 输入带 `https://` 前缀、搜索框带按钮） |
| `HoverCard` + `HoverCardTrigger` + `HoverCardContent` | 悬停卡片，内容比 Tooltip 更丰富（用户 profile 预览、链接预览） |
| `Command` + `CommandDialog` + `CommandInput` + `CommandList` + `CommandItem` | 命令面板（⌘K 场景、全局搜索、快捷操作入口） |
| `Combobox` | 可搜索的组合下拉框（选项多、需要过滤时替代 Select） |
| `FunctionSwitch` | 分段多值切换器（类似 SegmentedControl，≥ 3 个互斥选项） |
| `AvatarGroup` + `AvatarGroupCount` | 堆叠头像组（展示多人协作者列表，溢出时显示 +N） |
| `CollapsibleSection` | 带标题栏的可折叠区块（比 `Collapsible` 多标题，比 `Collapse` 更轻量） |

**InputGroup 用法示例：**

```tsx
import { InputGroup, InputGroupAddon, InputGroupButton, Input, Button } from 'sparkdesign'

// 带前缀文本
<InputGroup>
  <InputGroupAddon>https://</InputGroupAddon>
  <Input placeholder="your-domain.com" />
</InputGroup>

// 带后缀按钮
<InputGroup>
  <Input placeholder="搜索..." value={q} onChange={(e) => setQ(e.target.value)} />
  <InputGroupButton>
    <Button variant="primary">搜索</Button>
  </InputGroupButton>
</InputGroup>
```

**AvatarGroup 用法示例：**

```tsx
import { AvatarGroup, AvatarGroupCount, Avatar, AvatarImage, AvatarFallback } from 'sparkdesign'

<AvatarGroup>
  <Avatar><AvatarImage src="/alice.png" /><AvatarFallback>A</AvatarFallback></Avatar>
  <Avatar><AvatarImage src="/bob.png" /><AvatarFallback>B</AvatarFallback></Avatar>
  <Avatar><AvatarImage src="/carol.png" /><AvatarFallback>C</AvatarFallback></Avatar>
  <AvatarGroupCount>+5</AvatarGroupCount>
</AvatarGroup>
```

---



### Pattern A：列表页工具栏（List Toolbar）

```tsx
import { Button, Input, Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from 'sparkdesign'

<div className="flex items-center gap-3">
  <Input placeholder="搜索..." value={search} onChange={(e) => setSearch(e.target.value)} />
  <Select value={filter} onValueChange={setFilter}>
    <SelectTrigger className="w-40">
      <SelectValue placeholder="全部状态" />
    </SelectTrigger>
    <SelectContent>
      <SelectItem value="all">全部状态</SelectItem>
      <SelectItem value="active">运行中</SelectItem>
      <SelectItem value="stopped">已停止</SelectItem>
    </SelectContent>
  </Select>
  <Button variant="primary">+ 新建</Button>
</div>
```

---

### Pattern B：表格行操作（Table Row Actions）

```tsx
import { Button, DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator } from 'sparkdesign'

// 操作 ≤ 2 个：直接展示 ghost 按钮
<Button variant="ghost" size="sm">编辑</Button>

// 操作 ≥ 3 个：收入 DropdownMenu，危险操作用 className="text-error"
<DropdownMenu>
  <DropdownMenuTrigger asChild>
    <Button variant="ghost" size="sm">···</Button>
  </DropdownMenuTrigger>
  <DropdownMenuContent align="end">
    <DropdownMenuItem>编辑</DropdownMenuItem>
    <DropdownMenuItem>复制</DropdownMenuItem>
    <DropdownMenuSeparator />
    <DropdownMenuItem className="text-error">删除</DropdownMenuItem>
  </DropdownMenuContent>
</DropdownMenu>
```

---

### Pattern C：创建/编辑表单（Create / Edit Form）

```tsx
import { Dialog, DialogTrigger, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogClose } from 'sparkdesign'
import { Field, FieldLabel, FieldError, Input, Select, SelectTrigger, SelectValue, SelectContent, SelectItem, Textarea, Button } from 'sparkdesign'

// 字段 ≤ 5 个 → Dialog；字段 > 5 个 → Sheet；字段复杂多分区 → 全页面表单

<Dialog>
  <DialogTrigger asChild>
    <Button variant="primary">新建</Button>
  </DialogTrigger>
  <DialogContent>
    <DialogHeader>
      <DialogTitle>新建资源</DialogTitle>
    </DialogHeader>

    <div className="flex flex-col gap-4">
      <Field>
        <FieldLabel>名称</FieldLabel>
        <Input placeholder="请输入名称" value={name} onChange={(e) => setName(e.target.value)} />
        {nameError && <FieldError>{nameError}</FieldError>}
      </Field>

      <Field>
        <FieldLabel>类型</FieldLabel>
        <Select value={type} onValueChange={setType}>
          <SelectTrigger><SelectValue placeholder="选择类型" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="server">云服务器</SelectItem>
            <SelectItem value="storage">对象存储</SelectItem>
          </SelectContent>
        </Select>
      </Field>

      <Field>
        <FieldLabel>描述</FieldLabel>
        <Textarea placeholder="可选描述" />
      </Field>
    </div>

    <DialogFooter>
      <DialogClose asChild><Button variant="secondary">取消</Button></DialogClose>
      <Button variant="primary" loading={isSubmitting}>创建</Button>
    </DialogFooter>
  </DialogContent>
</Dialog>
```

---

### Pattern D：详情页头部（Detail Page Header）

```tsx
import { Avatar, AvatarImage, AvatarFallback, Tag, Button } from 'sparkdesign'
import { Breadcrumb, BreadcrumbList, BreadcrumbItem, BreadcrumbLink, BreadcrumbPage, BreadcrumbSeparator } from 'sparkdesign'

<div>
  <Breadcrumb>
    <BreadcrumbList>
      <BreadcrumbItem><BreadcrumbLink href="/users">用户管理</BreadcrumbLink></BreadcrumbItem>
      <BreadcrumbSeparator />
      <BreadcrumbItem><BreadcrumbPage>用户详情</BreadcrumbPage></BreadcrumbItem>
    </BreadcrumbList>
  </Breadcrumb>

  <div className="flex items-center justify-between mt-4">
    <div className="flex items-center gap-3">
      <Avatar>
        <AvatarImage src={user.avatar} alt={user.name} />
        <AvatarFallback>{user.initials}</AvatarFallback>
      </Avatar>
      <h1 className="text-text font-semibold">{user.name}</h1>
      <Tag color="success">Active</Tag>
    </div>
    <div className="flex gap-2">
      <Button variant="secondary">编辑</Button>
      <Button variant="danger">删除</Button>
    </div>
  </div>
</div>
```

---

### Pattern E：空状态（Empty State）

```tsx
import { Empty, EmptyHeader, EmptyTitle, EmptyDescription, EmptyContent } from 'sparkdesign'
import { Button } from 'sparkdesign'
import { Users } from 'lucide-react'

<Empty>
  <EmptyHeader>
    <div className="text-text-secondary mb-2"><Users size={40} /></div>
    <EmptyTitle>暂无成员</EmptyTitle>
    <EmptyDescription>邀请成员加入，开始协作</EmptyDescription>
  </EmptyHeader>
  <EmptyContent>
    <Button variant="primary">邀请成员</Button>
  </EmptyContent>
</Empty>
```

---

### Pattern F：分步向导（Step Wizard）

```tsx
import { Progress, Button } from 'sparkdesign'

// 步骤数 2–4：顶部 Progress；步骤数 5–6：SidebarMenu 步骤导航
// 每步底部必须有「返回上一步」

<div className="flex flex-col gap-6">
  <Progress value={(currentStep / totalSteps) * 100} />
  <p className="text-text-secondary text-sm">第 {currentStep} 步，共 {totalSteps} 步</p>

  <div className="flex gap-3 justify-between">
    {currentStep > 1 && (
      <Button variant="secondary" onClick={handleBack}>返回上一步</Button>
    )}
    <Button variant="primary" loading={isSubmitting} onClick={handleNext}>
      {currentStep === totalSteps ? '提交' : '下一步'}
    </Button>
  </div>
</div>
```

---

### Pattern G：AI 对话界面（Chat Interface）

```tsx
import { ScrollArea } from 'sparkdesign'
import { ChatInputRoot, ChatInputBox, ChatInputInput, ChatInputActions, ChatInputActionsRight, ChatInputSendButton } from 'sparkdesign'
import { Response, UserMessage, ThinkingIndicator } from 'sparkdesign'

// 优先使用 sparkdesign 内置 chat 组件，而非 div 手写消息气泡
<div className="flex h-screen bg-bg-base">
  <main className="flex-1 flex flex-col">
    <ScrollArea className="flex-1 p-4">
      {messages.map((msg) =>
        msg.role === 'user'
          ? <UserMessage key={msg.id} content={msg.content} />
          : <Response key={msg.id} content={msg.content} phase={msg.phase} />
      )}
      {isStreaming && <ThinkingIndicator />}
    </ScrollArea>

    <div className="p-4 border-t border-fill">
      <ChatInputRoot>
        <ChatInputBox>
          <ChatInputInput
            placeholder="输入消息..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSend()}
          />
          <ChatInputActions>
            <ChatInputActionsRight>
              <ChatInputSendButton disabled={!input.trim() || isStreaming} onClick={handleSend} />
            </ChatInputActionsRight>
          </ChatInputActions>
        </ChatInputBox>
      </ChatInputRoot>
    </div>
  </main>
</div>
```

---

### Pattern H：Toast 带操作按钮（Toast with Action）

```tsx
import { toast } from 'sparkdesign'

// 基础用法
toast('操作成功')
toast.success('保存成功')
toast.error('操作失败，请重试')

// 带 Action 按钮（如 Undo）——注意第二个参数需类型断言
toast('已归档', {
  action: {
    label: '撤销',
    onClick: () => handleUndo(),
  },
} as Parameters<typeof toast>[1])

// 带描述文本
toast.success('邀请已发送', {
  description: '对方将收到邮件通知',
} as Parameters<typeof toast>[1])
```

> ⚠️ **为什么需要类型断言**：`toast()` 的第二个参数类型在当前版本中可能推断为 `never`，直接传对象会报 TypeScript 错误。使用 `as Parameters<typeof toast>[1]` 绕过，不影响运行时行为。

---

### Pattern I：RadioGroup 卡片式单选（Card-style RadioGroup）

```tsx
import { RadioGroup, RadioGroupItem } from 'sparkdesign'

// Spark RadioGroup 无内置卡片样式，选中态需通过 JS 条件判断 className 实现
// 不要依赖纯 CSS :checked 伪类，因为实际 input 被隐藏

const plans = [
  { value: 'starter', label: 'Starter', desc: '适合个人项目，5 个工作区' },
  { value: 'pro', label: 'Pro', desc: '适合团队协作，无限工作区' },
  { value: 'enterprise', label: 'Enterprise', desc: '定制化部署，SLA 保障' },
]

<RadioGroup value={selected} onValueChange={setSelected} className="flex flex-col gap-3">
  {plans.map((plan) => (
    <label
      key={plan.value}
      className={[
        'flex items-start gap-3 p-4 rounded-lg border cursor-pointer transition-colors',
        selected === plan.value
          ? 'border-primary bg-primary/5'       // 选中态：蓝边 + 淡背景
          : 'border-fill hover:border-fill-hover', // 未选中态
      ].join(' ')}
    >
      <RadioGroupItem value={plan.value} className="mt-0.5" />
      <div className="flex flex-col gap-0.5">
        <span className="text-text font-medium">{plan.label}</span>
        <span className="text-text-secondary text-sm">{plan.desc}</span>
      </div>
    </label>
  ))}
</RadioGroup>
```

> **关键原则**：卡片整体可点击（用 `<label>` 包裹）；选中状态通过 `selected === plan.value` 条件判断 className，而非依赖浏览器原生的 `:checked`。

---

### Pattern J：工具调用权限审批（Tool Approval Flow）

> 来源：`agent-manifest.json` recipes → `tool-approval-flow`
> 适用：AI agent 执行 shell / 文件 / 网络等高风险操作前，需用户明确授权

```tsx
import { PermissionCard, ToolInvocationCard, Alert, Button } from 'sparkdesign'

// 1. 工具执行前：展示 PermissionCard 请求授权
{status === 'pending' && (
  <PermissionCard
    title="执行 Shell 命令"
    description={`即将运行：${command}`}
    onApprove={() => setStatus('running')}
    onDeny={() => setStatus('denied')}
  />
)}

// 2. 授权后：ToolInvocationCard 展示执行状态
{(status === 'running' || status === 'success' || status === 'error') && (
  <ToolInvocationCard
    toolName="Shell"
    status={status}
    summary={status === 'success' ? '命令执行成功' : '命令执行失败'}
  />
)}

// 3. 失败时：Alert 展示错误
{status === 'error' && (
  <Alert variant="destructive">
    <AlertTitle>执行失败</AlertTitle>
    <AlertDescription>{errorMessage}</AlertDescription>
  </Alert>
)}
```

> ⚠️ **antiPatterns**：不要自动审批高风险操作；不要隐藏拒绝路径；不要在输出结果未就绪前标记为成功。

---

### Pattern K：Agent 文件变更审核（File Review Flow）

> 来源：`agent-manifest.json` recipes → `file-review-flow`
> 适用：AI agent 生成/修改文件后，需用户审查并决定是否接受

```tsx
import { FileReviewPart, PermissionCard, ToolInvocationCard, Alert } from 'sparkdesign'

// 1. 展示文件变更列表供用户审查
<FileReviewPart
  files={changedFiles}
  status={reviewStatus}
  onApprove={() => applyChanges()}
  onRequestChanges={() => setReviewStatus('changes-requested')}
/>

// 2. 应用变更前需再次 PermissionCard 确认（若涉及写入操作）
{awaitingApply && (
  <PermissionCard
    title="写入文件变更"
    description={`将修改 ${changedFiles.length} 个文件`}
    onApprove={commitChanges}
    onDeny={cancelApply}
  />
)}
```

> ⚠️ **antiPatterns**：不要用纯 Markdown 列表替代 FileReviewPart；不要把风险变更折叠到摘要里隐藏；不要用于通用数据表格。

---

## 四、场景 × 核心组件矩阵

| 场景 | 必用组件 | 常用组合 Pattern |
|---|---|---|
| SaaS 管理后台 | `SidebarMenu`, `DataTable`, `Dialog`, `Sheet`, `Tag`, `Field` + `Input` | A + B + C |
| AI 产品 | `ChatInputRoot`, `Response`, `UserMessage`, `ScrollArea`, `ThinkingIndicator` | Pattern G |
| 营销网站 | `Button`, `Card`, `Separator`, `Collapse` | — |
| 数据分析 / BI | `Tabs`, `Card`, `Select`, `DatePicker`, `Skeleton` | — |
| 电商 | `Card`, `Tag`, `Button`, `Sheet`（购物车）, `AlertDialog` | — |
| 开发者工具 | `Tabs`, `SidebarMenu`, `Toaster`+`toast()`, `Tag`, `DataTable` | A + Pattern G（设置） |
| 内部运营工具 | `DataTable`, `Tag`, `AlertDialog`, `Sheet`, `Tabs` | B + D |
| 金融科技 | `DataTable`, `AlertDialog`, `Tag`, `InputOTP`, `Progress` | B + D |
| 社区 / 社交 | `Avatar`+`AvatarImage`+`AvatarFallback`, `Card`, `Button`, `Textarea`, `DropdownMenu` | — |
| 医疗健康 | `DatePicker`, `Field`+`Input`, `Tag`, `AlertDialog`, `Progress` | C + F |
| 教育科技 | `Progress`, `Card`, `Tabs`, `Tag`, `Collapsible` | — |

---

## 五、禁止行为

- **不用 `div` 模拟组件**。需要按钮必须用 `Button`，不用 `<div onClick>`
- **不硬编码颜色**。所有颜色必须引用 Spark token
- **不省略空状态**。每个列表/数据区域必须有 `Empty` 组件（含 CTA）
- **不省略 Loading 状态**。按钮提交时必须有 `loading` prop，数据加载时必须有 `Skeleton` 或 `Spinner`
- **不使用自定义像素值**。间距用 `p-4`、`m-2`，圆角用 `rounded-md`，不用 `p-[12px]`
- **不混用 Spark 和 shadcn 组件**（除非用户明确指定混用）
- **不使用旧版 CLI import 路径**（`@/components/ui/basic/[component]`）
- **不使用不存在的组件**：`Form`（用 `Field` 系列代替）、`Accordion`（用 `Collapse` 系列代替）、`Badge`（用 `Tag` 代替）
- **不使用不存在的 variant**：`Button` 无 `danger`；危险操作用 `AlertDialog` 确认 + `className="text-error"` 表达语义；`Alert` 危险 variant 是 `destructive` 不是 `danger`
- **不使用废弃名称**：`OtpInput`（改 `InputOTP`）、`Sidebar`（改 `SidebarMenu`）
- **Toast 不作为 JSX 渲染**。App Shell 渲染一次 `<Toaster />`，其他地方用 `toast()` 函数调用
- **不使用不存在的 Tag prop**：`size` 不存在（用 `className="text-xs"`），`color="default"` 无效（用 `color="slate"`）
- **表格元素必须先核验**：遇到 `<table>`/`<thead>`/`<th>`/`<tr>`/`<td>` 前，先 grep 确认 Spark Table/DataTable 是否可用，有则用组件，无则参照下方 token 对照手写

---

## 五·附：手写表格 Token 对照

> ⚠️ **首选方案永远是 Spark Table/DataTable 组件**。以下 token 仅供 Spark 组件无法覆盖的极端场景（如树形表格、固定多列等），或已核验组件不存在时的兜底参考。

| 元素 | ✅ 正确 token | ❌ 常见错误 token |
|---|---|---|
| `<thead>` 背景 | `bg-fill-tertiary`（更浅） | `bg-fill-secondary` |
| `<thead>` 边框 | `border-border-secondary`（更淡） | `border-border` |
| `<th>` 文字 | `font-semibold text-text` | `font-medium text-text-secondary` |
| `<tr>` 分隔线 | `border-border-tertiary`（更轻） | `border-border` |
| `<tr>` hover | `hover:bg-fill-tertiary`（更浅） | `hover:bg-fill-secondary` |

**最小正确写法**：

```tsx
<div className="overflow-x-auto rounded-lg border border-border-secondary">
  <table className="w-full min-w-[640px] text-sm">
    <thead className="bg-fill-tertiary border-b border-border-secondary">
      <tr>
        <th className="px-4 py-3 text-left font-semibold text-text">列名</th>
      </tr>
    </thead>
    <tbody>
      <tr className="border-b border-border-tertiary hover:bg-fill-tertiary transition-colors">
        <td className="px-4 py-3 text-text">单元格</td>
      </tr>
    </tbody>
  </table>
</div>
```

---

## 六、shadcn 组件对照（仅供参考）

> 若用户明确要求使用 shadcn，参考 `references/shadcn-component-map.md` 和 `references/shadcn-setup.md`。

| Spark Design 组件 | 对应 shadcn 组件 | 主要差异 |
|---|---|---|
| `Tag` | `Badge` | Spark Tag 提供 color 语义，shadcn Badge 用 variant |
| `Tooltip` | `Tooltip` + `TooltipProvider` | Spark Tooltip 无需 Provider，直接 `content` prop |
| `Switch` | `Switch` | API 基本相同 |
| `Progress` | `Progress` | API 基本相同 |
| `Button` | `Button` | variant 命名不同（primary vs default） |
| `Sheet` | `Sheet` | API 基本相同 |
| `Drawer` | `Drawer` | API 基本相同 |
| `Dialog` | `Dialog` | API 基本相同 |
| `Collapse` 系列 | `Accordion` 系列 | Spark 用 Collapse/CollapseItem，shadcn 用 Accordion/AccordionItem |
| `Field` + `FieldLabel` + `FieldError` | `Form` + `FormItem` + `FormLabel` + `FormMessage` | Spark 无 Form 组件，用 Field 系列代替 |
| `InputOTP` | `InputOTP` | API 基本相同 |
| `SidebarMenu` | `Sidebar`（shadcn 0.8+） | Spark 用 data-driven items prop，shadcn 用子组件树 |
| `ThemeStyleProvider` | `ThemeProvider`（next-themes） | Spark 一体化管理，shadcn 需搭配 next-themes |
| `Toaster` + `toast()` | `Toaster` + `toast()`（sonner） | API 基本相同，Spark 内置不需要安装 sonner |
| `Empty` 系列 | 无内置，需手写 | Spark 提供标准化空状态组件 |
| `DataTable` | 无内置，需 TanStack Table 手动实现 | Spark 内置高级表格 |
| `ChatInput` 等 chat/ 系列 | 无内置 | Spark 专属 AI 对话组件 |
