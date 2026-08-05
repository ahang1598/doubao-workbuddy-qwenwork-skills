# Component Concept Map — 三库横向组件对照表

> **文件用途**：定义与组件库无关的抽象功能概念，并映射到 shadcn/ui、Spark Design、Ant Design 三个库的具体实现。  
> Scenario 文件的 Component Kit 使用本文件中的「功能概念」列命名，不绑定任何特定组件库。  
> Phase B 代码生成时，根据用户选择的 `TECH_STACK` 查询对应列，取准确的组件名和子组件链。

---

## 使用方式

1. 在 Scenario 文件的 Component Kit 中找到「功能概念」名称（如「状态标签」）
2. 根据当前 `TECH_STACK` 查找对应列的组件名
3. 按本文件中的「子组件链 / 用法说明」生成代码

---

## 一、操作类

| 功能概念 | shadcn/ui | Spark Design | Ant Design |
|---|---|---|---|
| **操作按钮** | `Button` | `Button` | `Button` |
| **图标按钮** | `Button`（size="icon"） | `IconButton` | `Button`（icon only） |
| **开关** | `Switch` | `Switch` | `Switch` |
| **二态切换按钮** | `Toggle` | `Toggle` | `Button`（type="default", active 状态手动控制） |
| **互斥/多选按钮组** | `ToggleGroup` + `ToggleGroupItem` | `ToggleGroup` + `ToggleGroupItem` | `Radio.Group`（button style）/ `Segmented` |

> ⚠️ **交互型切换 / 过滤场景选择规则**（按优先级）：
> 1. **视图切换 / 状态分组筛选**（切换后有对应内容区域）→ **首选 `Tabs`**（`TabsList` + `TabsTrigger` + `TabsContent`）
> 2. **无内容面板的互斥过滤 Pill**（如时间维度选择、类型切换）→ **`ToggleGroup` + `ToggleGroupItem`**
> 3. **二态按钮**（开启/关闭、A/B 模式）→ **`Toggle`**
> 4. **`Tag` 是只读展示组件，禁止添加 `onClick`**。凡需要点击触发状态变化的场景，一律走上方 1–3 规则，不得使用 `Tag`。

---

## 二、数据展示类

| 功能概念 | shadcn/ui | Spark Design | Ant Design |
|---|---|---|---|
| **状态标签** | `Badge` | `Tag`（color="default\|success\|error\|warning\|info"） | `Tag`（color） |
| **计数角标** | `Badge`（数字内容） | `Tag`（数字内容） | `Badge`（count / dot） |
| **进度条** | `Progress` | `Progress` | `Progress`（percent） |
| **气泡提示** | `Tooltip` + `TooltipTrigger` + `TooltipContent` + **`TooltipProvider`**（必须） | `Tooltip`（content prop，无需 Provider） | `Tooltip`（title prop） |
| **加载骨架屏** | `Skeleton` | `Skeleton` | `Skeleton`（active） |
| **加载旋转器** | Lucide `<Loader2>` + animate-spin | `Spinner` | `Spin` |
| **基础数据表格** | `Table` + `TableHeader` + `TableBody` + `TableRow` + `TableHead` + `TableCell` | `Table` + 子组件 | `Table`（columns, dataSource） |
| **高级数据表格**（排序/筛选/分页） | TanStack Table（手动实现） | `DataTable`（columns, data） | `Table`（内置 sorter / filter / pagination） |
| **用户头像** | `Avatar` + `AvatarImage` + `AvatarFallback` | `Avatar` + `AvatarImage` + `AvatarFallback` | `Avatar`（src，children 为 fallback） |
| **内容卡片** | `Card` + `CardHeader` + `CardTitle` + `CardDescription` + `CardContent` + `CardFooter` | `Card` + 子组件 | `Card`（title, extra, children） |
| **数字统计卡** | 手写 `<div>` | 手写 `<div>` | `Statistic`（title, value） |
| **分隔线** | `Separator` | `Separator` | `Divider` |
| **空状态** | 手写（无内置） | `Empty` + `EmptyHeader` + `EmptyTitle` + `EmptyDescription` + `EmptyContent` | `Empty`（description, image） |
| **操作完成全屏反馈** | 手写 | 手写 | `Result`（status, title, subTitle） |

---

## 三、表单与输入类

| 功能概念 | shadcn/ui | Spark Design | Ant Design |
|---|---|---|---|
| **表单容器（含校验）** | `Form` + `FormItem` + `FormLabel` + `FormControl` + `FormMessage`（react-hook-form） | `Field` + `FieldLabel` + `FieldError` + `FieldDescription`（无 Form 包裹层） | `Form` + `Form.Item`（name + rules） |
| **单行文本输入** | `Input` | `Input` | `Input` |
| **密码输入** | `Input`（type="password"） | `Input`（type="password"） | `Input.Password` |
| **多行文本输入** | `Textarea` | `Textarea` | `Input.TextArea` |
| **数字输入** | `Input`（type="number"） | `Input`（type="number"） | `InputNumber` |
| **选择下拉** | `Select` + `SelectTrigger` + `SelectValue` + `SelectContent` + `SelectGroup` + `SelectItem` | `Select` + `SelectTrigger` + `SelectValue` + `SelectContent` + `SelectGroup` + `SelectItem` | `Select`（options prop） |
| **多选框** | `Checkbox` | `Checkbox` | `Checkbox` / `Checkbox.Group` |
| **单选组** | `RadioGroup` + `RadioGroupItem` | `RadioGroup` + `RadioGroupItem` | `Radio.Group` + `Radio` |
| **OTP 验证码输入** | `InputOTP` + `InputOTPGroup` + `InputOTPSlot` | `InputOTP` + `InputOTPGroup` + `InputOTPSlot` | `Input.OTP`（antd 5.16+） |
| **日期选择器** | Calendar + Popover（无内置 DatePicker） | `DatePicker` | `DatePicker` |
| **日期范围选择** | Calendar（range mode）+ Popover | `DatePicker`（range mode） | `DatePicker.RangePicker` |
| **范围滑块** | `Slider` | `Slider` | `Slider` |
| **文件上传** | 手写 `<input type="file">` | 手写 `<input type="file">` | `Upload`（dragger 模式支持拖拽） |

---

## 四、布局与导航类

| 功能概念 | shadcn/ui | Spark Design | Ant Design |
|---|---|---|---|
| **标签页切换** | `Tabs` + `TabsList` + `TabsTrigger` + `TabsContent` | `Tabs` + `TabsList` + `TabsTrigger` + `TabsContent` | `Tabs`（items prop，含 key/label/children） |
| **面包屑导航** | `Breadcrumb` + `BreadcrumbList` + `BreadcrumbItem` + `BreadcrumbLink` + `BreadcrumbPage` + `BreadcrumbSeparator` | 同 shadcn（API 相同） | `Breadcrumb`（items prop） |
| **分页控件** | `Pagination` + `PaginationContent` + `PaginationItem` + `PaginationPrevious` + `PaginationNext` | `Pagination` + 子组件 | `Pagination`（通常内置在 Table 的 pagination prop） |
| **侧边导航** | `Sidebar`（shadcn 0.8+，子组件树） | `SidebarMenu`（items prop，data-driven） | `Layout.Sider` + `Menu`（items prop） |
| **顶部导航栏** | 手写 `<header>` | 手写 `<header>` | `Layout.Header` |
| **单个可折叠区域** | `Collapsible` + `CollapsibleTrigger` + `CollapsibleContent` | `Collapsible` + `CollapsibleTrigger` + `CollapsibleContent` | `Collapse`（单 item） |
| **可折叠列表** | `Accordion` + `AccordionItem` + `AccordionTrigger` + `AccordionContent` | `Collapse` + `CollapseItem` + `CollapseTrigger` + `CollapseContent` | `Collapse`（items prop） |
| **可滚动区域** | `ScrollArea` + `ScrollBar` | `ScrollArea` + `ScrollBar` | CSS overflow 或虚拟滚动 |
| **分步向导步骤指示** | `Progress` + 手写 step count | `Progress`（步骤数 2–4）/ `SidebarMenu`（步骤数 5–6） | `Steps`（items prop） |
| **全局页面布局骨架** | 手写 flex/grid | 手写 flex/grid + `ThemeStyleProvider` 包裹 | `Layout` + `Layout.Sider` + `Layout.Header` + `Layout.Content` |

---

## 五、覆盖层与反馈类

| 功能概念 | shadcn/ui | Spark Design | Ant Design |
|---|---|---|---|
| **模态对话框** | `Dialog` + `DialogTrigger` + `DialogContent` + `DialogHeader` + `DialogTitle` + `DialogDescription` + `DialogFooter` + `DialogClose` | 同 shadcn（API 相同） | `Modal`（onOk / onCancel） |
| **危险操作确认** | `AlertDialog` + `AlertDialogTrigger` + `AlertDialogContent` + `AlertDialogHeader` + `AlertDialogTitle` + `AlertDialogDescription` + `AlertDialogFooter` + `AlertDialogCancel` + `AlertDialogAction` | 同 shadcn（API 相同） | `Modal.confirm()`（命令式调用） |
| **侧边面板/抽屉** | `Sheet` + `SheetTrigger` + `SheetContent` + `SheetHeader` + `SheetTitle` + `SheetFooter` + `SheetClose` | 同 shadcn（API 相同） | `Drawer`（title, onClose, open） |
| **锚定浮层** | `Popover` + `PopoverTrigger` + `PopoverContent` | `Popover` + `PopoverTrigger` + `PopoverContent` | `Popover`（content / title prop） |
| **下拉操作菜单** | `DropdownMenu` + `DropdownMenuTrigger` + `DropdownMenuContent` + `DropdownMenuItem` + `DropdownMenuSeparator` | 同 shadcn（API 相同） | `Dropdown`（menu={{ items }}） |
| **操作通知（Toast）** | `Toaster`（渲染一次）+ `toast()` / `toast.success()` / `toast.error()`（sonner） | `Toaster`（渲染一次）+ `toast()` / `toast.success()` / `toast.error()` | `message.success()` / `message.error()` / `notification.open()` |
| **页面级警告横幅** | `Alert` + `AlertTitle` + `AlertDescription` | `Alert` + 子组件 | `Alert`（type / message / description） |
| **全局主题包裹** | `ThemeProvider`（next-themes）+ useEffect class toggle | `ThemeStyleProvider`（appearance / theme / style） | `ConfigProvider`（theme: { algorithm }） |

---

## 六、AI / Chat 类（Spark Design 专属）

> 以下组件仅 Spark Design 内置。shadcn 和 Ant Design 需手写实现（使用 `div` + `Textarea` + `Button` 组合）。

| 功能概念 | shadcn/ui | Spark Design | Ant Design |
|---|---|---|---|
| **AI 对话输入框** | 手写 | `ChatInputRoot` + `ChatInputBox` + `ChatInputInput` + `ChatInputActions` + `ChatInputActionsRight` + `ChatInputSendButton` | 手写 |
| **AI 回复气泡** | 手写 `<div>` | `Response`（支持 streaming / thinking / steps） | 手写 `<div>` |
| **用户消息气泡** | 手写 `<div>` | `UserMessage` | 手写 `<div>` |
| **AI 思考中动画** | 手写 | `ThinkingIndicator` | 手写 |
| **流式 Markdown 渲染** | 手写（react-markdown） | `StreamingMarkdownBlock` | 手写 |

---

## 七、重点差异速查

> 以下概念在三个库中差异最大，生成代码前务必确认。

| 功能概念 | 差异说明 |
|---|---|
| **交互型切换 vs 只读展示** | **必读**：`Tag` 是只读展示组件，禁止加 `onClick`。视图切换/状态筛选首选 `Tabs`；无内容面板的互斥 Pill 用 `ToggleGroup`；二态按钮用 `Toggle`。见第一节规则。 |
| **状态标签** | shadcn 叫 `Badge`；Spark 和 antd 都叫 `Tag`，但 color 值不同 |
| **可折叠列表** | shadcn 叫 `Accordion`；Spark 叫 `Collapse`；antd 叫 `Collapse`（items prop） |
| **表单容器** | shadcn 用 `Form`（react-hook-form）；Spark 用 `Field` 系列（无 Form 包裹）；antd 用 `Form` + `Form.Item` |
| **气泡提示** | shadcn 必须有 `TooltipProvider` 包裹；Spark 直接用 `content` prop；antd 用 `title` prop |
| **侧边导航** | shadcn `Sidebar` 子组件树；Spark `SidebarMenu` data-driven items；antd `Sider` + `Menu` |
| **操作通知** | shadcn/Spark 都用 `toast()` 函数；antd 用 `message.success()` 命令式 API |
| **危险操作确认** | shadcn/Spark 用 `AlertDialog` 组件；antd 用 `Modal.confirm()` 命令式 |
| **侧边面板** | shadcn/Spark 都叫 `Sheet`；antd 叫 `Drawer` |
| **分隔线** | shadcn/Spark 叫 `Separator`；antd 叫 `Divider` |
| **空状态** | shadcn 无内置；Spark 有完整 `Empty` 系列；antd 有 `Empty` |
| **高级数据表格** | shadcn 需手写 TanStack Table；Spark 内置 `DataTable`；antd `Table` 原生支持 |
