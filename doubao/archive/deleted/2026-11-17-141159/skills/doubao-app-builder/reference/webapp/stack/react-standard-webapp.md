# 默认技术栈：妙搭官方 react-standard-webapp 模板

用官方脚手架建出来的工程走这套约定。**工程建好后、动手写代码前完整读一遍**——模板自带件、目录、门禁、常见坑都在这里，不读就动手必然重复造轮子或 import 不存在的路径。

🔴🔴🔴 **先看 §9 再写代码**：手写路径一律用 `MIAODA_CLIENT_BASE_PATH` 拼，不用 `BASE_URL`、不写裸根路径。这是本模板最高频、且本地永远测不出来的错。

链路方法论（工作流、交付、发布）见 [`webapp-develop.md`](../../webapp-develop.md)；用户点名了别的技术栈时本文不适用，只有那边的通用约束照常生效。

---

## 1. 模板已经给了什么（不要重复造）

### 1.1 文件

| 文件 | 是什么 | 你该怎么做 |
|---|---|---|
| `src/app.tsx` | 路由注册，`<Route element={<Layout />}>` 包 index + `*` | 只改 `<Routes>` 内部的 `<Route>`，不动外层结构 |
| `src/components/Layout.tsx` | **默认就是 `return <Outlet />;` 纯透传** | 需要全局 chrome 时往里加 Header / Sidebar；**不需要时保持原样**，不要自己套带高度的 div 壳 |
| `src/components/ui/image.tsx` | 见下方 §1.2 | 直接 import 用，**禁止自己写一个覆盖它** |
| `src/components/ErrorFallback.tsx` | 配合 `react-error-boundary` 的错误兜底 | 直接用 |
| `src/lib/utils.ts` | 导出 `cn`（clsx + tailwind-merge） | `import { cn } from '@/lib/utils'`，不要再单独 import clsx |
| `src/hooks/use-mobile.ts` | 导出 **`useIsMobile`**（注意不叫 `useMobile`） | 直接用 |
| `src/pages/HomePage` / `NotFoundPage` / `ExamplePage` | 示例页 | HomePage 改成真首页。**`ExamplePage` 用不上就不管它**——不引用就不会进产物，删它要多跑一次删除加一次验证，白花时间 |
| `src/index.css` / `src/tailwind-theme.css` / `src/typography.css` | 主题变量与排版 | 定好的配色字体写进这里，之后不再改 |
| `src/components/ui/*` | 55 个 shadcn 组件，见 §2 | 直接 import，**严禁 `npx shadcn add` 重装** |

### 1.2 `ui/image.tsx` 的真实行为（重要）

业务代码里的图片一律 `import { Image } from '@/components/ui/image'`，不用原生 `<img>`。

它的行为分两种：src 命中平台存储路径（`/runtime/api/v1/storage/object/` 等）时自动加尺寸 / 质量 / webp 参数生成 `srcSet`；**其他 src 直接渲染原生 `<img>`**，只保留 `loading="lazy"` + `decoding="async"` 和一个浅色渐变底。

本链路的图片都在 `public/` 下按相对路径引，**落在第二种**——所以它等于「带懒加载的 img」，**没有加载失败兜底**。首屏 hero 这类挂了会很难看的位置，自己在调用处补 `onError` 换占位，别指望组件兜。

装饰性图片 `alt=""`；承载信息的图片必须写真实 alt。

### 1.3 已装的依赖（直接用，不用 install）

`react@19` · `react-router-dom@7` · `tailwindcss@4` · `lucide-react` · `sonner` · `date-fns` · `zod` · `react-hook-form` + `@hookform/resolvers` · `framer-motion` · `gsap` + `@gsap/react` · `@formkit/auto-animate` · `tw-animate-css` · `echarts` + `echarts-for-react` · `recharts` · `react-markdown` + `remark-gfm` · `next-themes` · `react-error-boundary` · `embla-carousel-react` · `react-day-picker` · `react-resizable-panels` · `input-otp` · `cmdk` · `vaul` · `class-variance-authority` · `clsx` · `tailwind-merge`

PDF 预览、地图、csv / xlsx 解析、日历排期、拖拽排序模板没带，**该装就装**，选型见下文「依赖选型」。

---

## 2. 模板自带的 55 个 shadcn 组件

`accordion` `alert` `alert-dialog` `aspect-ratio` `avatar` `badge` `breadcrumb` `button` `button-group` `calendar` `card` `carousel` `chart` `checkbox` `collapsible` `command` `context-menu` `dialog` `drawer` `dropdown-menu` `empty` `field` `form` `hover-card` `image` `input` `input-group` `input-otp` `item` `kbd` `label` `menubar` `native-select` `navigation-menu` `pagination` `popover` `progress` `radio-group` `resizable` `scroll-area` `select` `separator` `sheet` `sidebar` `skeleton` `slider` `sonner` `spinner` `switch` `table` `tabs` `textarea` `toggle` `toggle-group` `tooltip`

**不在这个清单里的 shadcn 组件，模板里没有**——要么换个已有的组件实现，要么自己在 `src/components/` 下写一个，不要 import 一个不存在的路径。

组件的具体导出名见下文「shadcn 组件导出名速查」。

**`toast` / `use-toast` 不存在**（shadcn 已废弃）：消息提示一律 `import { toast } from 'sonner'`。

配置口径（`components.json`）：style `new-york`、baseColor `neutral`、cssVariables 开、图标库 lucide。

---

## 3. 模板私有的 CSS 类：`hover-elevate` / `active-elevate-2`

这两个类定义在模板的 `src/tailwind-theme.css` 里，**不是 Tailwind 也不是 shadcn 的标准类**，换到别的项目就没有。

- `Button` 的 base class 已含 `hover-elevate active-elevate-2`，`Badge` 已含 `hover-elevate`——**不用自己加**。
- 原理是 `::after` 叠一层半透明遮罩，所以宿主元素需要能承载定位。
- 要关掉某个元素的默认效果，用逃生舱 `no-default-hover-elevate` / `no-default-active-elevate`。
- 还有 `hover-elevate-2` / `active-elevate` 两个变体可用。

**迁移提醒**：把代码从本模板搬去别的工程时，这几个类会静默失效（不报错，只是没效果），要换成常规 hover 样式。

---

## 4. 脚本与门禁

```json
// package.json
"dev": "vite"  ·  "build": "vite build"  ·  "typecheck": "tsc -p tsconfig.app.json"
"lint": "concurrently npm:typecheck npm:lint:eslint"  ·  "lint:eslint": "eslint src"

// spark.json —— 模板自带的原始内容，命令以它为准（但 port 必须改，见下）
{ "stack": "react-standard-webapp",
  "dev":   { "command": ["npm","run","dev"], "port": 5173 },
  "build": { "command": ["npm","run","build"], "output": "dist/output" } }
```

**不要用模板默认的 5173**——起服务时在 20000–39999 里随机挑一个，用 `npm run dev -- --port <端口>` 启动并同步改 `spark.json` 的 `dev.port`（判据见 [`../../webapp-develop.md`](../../webapp-develop.md)「交付与发布」）。端口被占用时 Vite 会自动顺延，**实际地址以终端输出为准**。

**交付前只跑这一条**：

```bash
npm run lint
```

🔴 **只看 error，不追 warning。** 模板把 `no-unused-vars` / `no-explicit-any` / `no-empty-object-type` 都关掉了，它们根本不进门禁。**看到 `0 errors` 就是过了，立刻往下走**——未使用的 import / 变量、`any` 这些一个都不要清理，「顺手改一下」也不行，每改一处都要重跑十几秒的检查。唯一例外是 `exhaustive-deps`（真会拿到旧值）。

🔴 **就这一条，不要拆开跑。** `lint` 内部已经并跑了 `typecheck` 和 `lint:eslint`——**再单独跑 `npm run typecheck` 或 `npm run lint:eslint` 就是把同样的活干第二遍**，每条都要十几秒。也不用 `npx tsc --noEmit`。

**也不用跑 `npm run build`**：构建比 lint 慢，而类型问题 `lint` 里的 `typecheck` 已经查过了（`vite build` 本身也不做类型检查，跑它并不会多查出什么）。`build` 留给发布那一步（见 [`publish.md`](../../publish.md)）。

⚠️ **这条命令跑一次约 15-20 秒**，是所有工具调用里最贵的。所以**写完全部文件再跑第一次**，拿到报错一次改完再跑第二次——不要改一处重跑一次——跑八九次就是一分半的纯等待，那段时间你什么也做不了。

模板的 ESLint 配置偏宽松（typescript-eslint recommended + react-hooks + react-refresh，`no-unused-vars` / `no-explicit-any` / `no-empty-object-type` 都关着，`src/components/ui/` 整个忽略）。**宽松不等于可以乱写**——§12「本模板下的高频坑」那几条照样要守，它们不靠 lint 拦，靠你一次写对。

---

## 5. 🔴 把定好的配色**改进**主题变量文件，不是新增

模板的 `tailwind-theme.css` 自带一整套默认色值（primary 是 `hsl(221 83% 53%)` 这种）。定好的色板**必须逐个覆盖进去**——**改这些变量的值**，不是在别处新增同名变量、也不是留着默认值不动。

要改的变量就这些（**只改值，不加新变量名**）：

```text
--background          --foreground
--card                --card-foreground
--popover             --popover-foreground
--primary             --primary-foreground
--secondary           --secondary-foreground
--muted               --muted-foreground
--accent              --accent-foreground
--destructive         --destructive-foreground
--border   --input   --ring
--chart-1  --chart-2  --chart-3  --chart-4  --chart-5
```

只定了 9 个角色时，其余从 4 个锚点色派生：primary 管 primary / primary-foreground / ring，accent 管 accent / accent-foreground / secondary / secondary-foreground，background 管 background / card / popover / muted / border / input，text 管 foreground / card-foreground / popover-foreground / muted-foreground。destructive 固定红色系。

字体如果选了 Google Fonts，**走自托管镜像 `https://miaoda.feishu.cn/fonts/css2`**（查询语法与 Google 的 `css2` 端点完全一致），`@import` 写进 `src/index.css` **第一行**，并把字体名加到 `--font-sans` 的最前面。⚠️ **不要直连 `fonts.googleapis.com` / `fonts.gstatic.com`**——部分地区不可达，产物会静默落回系统字体，而这一点 lint 和本地开发都发现不了。

改完**回读一遍确认生效**：`grep -- "--primary:" src/tailwind-theme.css` 出来的值要跟你定的一字不差。**主题文件跟模板原样一致就说明这一步没做**——那样整个视觉方向等于白定，产出的是模板默认皮肤。

---

## 6. 路由与 Layout 的具体写法

通用原则见 [`webapp-develop.md`](../../webapp-develop.md)「路由与导航」，这里是默认栈下怎么落。

`app.tsx` **只能改 `<Routes>` 内部**。禁止覆盖文件结构、加 `BrowserRouter`（外层已配）、改 `<Routes>` 外的 JSX、inline 定义并行 Layout。

```tsx
<Routes>
  <Route path="/" element={<Layout />}>
    <Route index element={<HomePage />} />
    {/* 首页等同某具名路由时：<Route index element={<Navigate to="/kanban" replace />} /> */}
    <Route path="kanban" element={<KanbanPage />} />
  </Route>
  <Route path="*" element={<NotFoundPage />} />
</Routes>
```

- 全局导航写在 `src/components/Layout.tsx`，`<Outlet />` 渲染页面。
- **导航项用 `NavLink`**（`react-router-dom`），禁止 `<a>` / `Link` / `Button` 充当导航项；根路径的 NavLink 必须加 `end`。
- active 判断从配置读 path：`item.path === '/' ? pathname === '/' : pathname.startsWith(item.path)`。
- **锚点导航不能用 `NavLink` / `Link`**——BrowserRouter 下不会滚动到锚点。自建 `AnchorLink`，实现见下文「锚点导航组件」。

## 7. 本模板的类型与 export 约定

- 业务实体 interface 用 `IXxx`（I 前缀 + 大驼峰）；Props interface 用 `XxxSectionProps`，不加 I。**严禁脑补 `XxxType` / `IXxxItem` 这类没定义过的名字。**
- **业务文件**（自写的 `components/`、`pages/**`）一律 `export default` + 默认 import。**直觉写 named 是错的**——跟模板的 `ui/*` 混用会反复挂在 `[MISSING_EXPORT]`。
- **shadcn `ui/*` 保持 named export**，不要给它包一层 default re-export。
- 类型定义文件首部写**带字段**的清单注释，跨文件用时 grep 一次就够，不用打开文件：

  ```ts
  // EXPORTS: IMember{id,name,role,email,avatarColor}, MOCK_MEMBERS
  ```

- **hooks 依赖数组**列全用到的外部值；改 state 用函数式更新就能留空依赖（`setItems((prev) => [item, ...prev])`），读了 `items` 却给空依赖既报警告又拿到旧值。
- 🔴 **导出了组件的文件，就不能再导出任何非组件**（`react-refresh/only-export-components`，error 级）。常量、工具函数、`createContext`、类型别名——**一个都不行**，全部挪到独立文件。Context 拆两个文件：一个放 `createContext` + hook + 类型，另一个只导出 Provider 组件。**写页面时顺手在文件底部导出一个常量或 helper，是这条最常见的踩法。**

## 8. 目录约定

```
src/app.tsx                        路由注册
src/index.tsx · index.css · tailwind-theme.css · typography.css
src/components/                    跨页面 chrome（Header / Footer / Sidebar / Layout）
src/components/ui/                 shadcn 组件，不要手改
src/pages/{Page}/{Page}.tsx        页面；sections/ 放该页独有的 Section
src/hooks/ · lib/ · data/          hooks · 工具函数 · 业务类型与 mock
src/api/                           接口封装（有真实接口时才建）
public/data/                       用户给的 csv / json / xlsx
```

路径别名 `@/` → `src/`，已在 `tsconfig` 和 `vite.config.ts` 配好。

---

## 9. 🔴🔴🔴 路径铁律

声明了 CDN 时，构建把产物拆成两处：`public/` 下的文件和 `index.html` 进**同源**目录，JS / CSS 进 **CDN** 目录。两个变量分别对应：

| 变量 | 指向 | 谁用 |
|---|---|---|
| `import.meta.env.BASE_URL` | 资源基址，**有 CDN 时是 CDN 域名** | vite 内部处理 JS / CSS，你不碰 |
| `import.meta.env.MIAODA_CLIENT_BASE_PATH` | 应用根路径 `/app/app_xxx` | **你手写的每一条路径** |

**你写的路径引用的东西——`public/` 下的数据文件、PDF、图片、同源接口——全在同源目录**，拿 `BASE_URL` 拼，一旦配了 CDN 就必然 404。**不用去查这个工程配没配 CDN**：用 `MIAODA_CLIENT_BASE_PATH` 两种情况都对，用 `BASE_URL` 只在没配时侥幸能跑。

```ts
const BASE = (import.meta.env.MIAODA_CLIENT_BASE_PATH || '').replace(/\/$/, '') + '/';  // 注入值 /app/app_xxx 结尾无斜杠，补上

await fetch(`${BASE}data/sales.csv`);                          // ✅ 数据文件
<iframe src={`${BASE}docs/report.pdf`} className="w-full h-full" />  // ✅ PDF，原生预览不用装库
<img src={`${BASE}images/hero.png`} />                         // ✅ 图片
await fetch(`${BASE}api/customers`);                           // ✅ 同源接口

fetch(`${import.meta.env.BASE_URL}data/x.csv`);                // ❌ 有 CDN 就 404
fetch('/data/x.csv');                                          // ❌ 裸根路径，子路径下 404
```

- 🔴 **生成能力返回的 CDN URL 要先下载到 `public/` 再引**（`curl` 一下），然后按上面的 `BASE` 拼相对路径——不要把平台 CDN 链接直接写进代码。
- 路由 basename 模板已在 `src/index.tsx` 配好，不要动。
- csv 用 `papaparse`、xlsx 用 `xlsx`，都要自己装；PDF 用上面的 `<iframe>`，只有要页码控制 / 文字选取才装 `react-pdf`。

⚠️ **dev 下根本拿不到真实前缀**（`MIAODA_CLIENT_BASE_PATH` 是 `undefined`，归一化后就是 `/`），所以本地怎么点都正常——别指望自测发现，写的时候就得对。

## 10. 这些是模板自带件，别去改

看到下面这些不要当成缺陷去"修"——它们本来就该长这样：

- `src/components/ui/` 下的 shadcn 组件——无状态展示件，ESLint 也整个忽略该目录
- `src/data/*.ts` 里有意声明为示例数据的常量
- `ErrorFallback.tsx` / `useIsMobile` 等模板自带件
- lucide-react 图标的 kebab-case 命名（如 `chevron-down`），那是官方规范

---

## 11. shadcn 组件导出名速查（严禁脑补）

**要哪个组件的导出名就查这张表，不要去读 `src/components/ui/*` 的源码**——批量 `cat` / `sed` 那些文件既慢又占上下文。表里没列到的才去翻源码。

**Hooks** (`@/hooks/*`):
- `@/hooks/use-mobile` → `{ useIsMobile }` (注意是 useIsMobile, 不是 useMobile; 装 shadcn sidebar 时一并生成)
- ❌ `@/hooks/use-toast` 不存在
- ❌ `@/hooks/use-media-query` 不存在

**Lib utils** (`@/lib/*`):
- `@/lib/utils` → `{ cn }` (shadcn 初始化时生成, 内部是 clsx + tailwind-merge, 直接 `import { cn } from '@/lib/utils'` 即可, 不要再单独 import clsx)

**Toast / 消息**:
- ❌ `@/components/ui/toast` 不存在
- ❌ `useToast` 不存在
- ✅ **走 sonner**: `import { toast } from 'sonner'` 然后 `toast.success / toast.error / toast.info`

**shadcn UI 组件** (`@/components/ui/*`) 常用导出:
- `button` → `Button, buttonVariants` **`Button` 会把 `className` 合并进 cva，尺寸 / 圆角覆盖有效。`type` 是原生属性，非提交动作在 form 内要写 `type="button"`。普通 Button 不写定位类；Overlay Button 用父容器 `relative` + `!absolute`（不是 `absolute`）+ `z-20`。本模板的 Button 另含私有的 hover / active 遮罩类，见 §3。**
- `card` → `Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle`
- `dialog` → `Dialog, DialogClose, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger`
- `sheet` → `Sheet, SheetClose, SheetContent, SheetDescription, SheetFooter, SheetHeader, SheetTitle, SheetTrigger`
- `dropdown-menu` → `DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem, ...`
- `select` → `Select, SelectTrigger, SelectValue, SelectContent, SelectItem, SelectGroup, SelectLabel, ...`
- `tabs` → `Tabs, TabsList, TabsTrigger, TabsContent`
- `table` → `Table, TableBody, TableCaption, TableCell, TableFooter, TableHead, TableHeader, TableRow`
- `form` → `Form, FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage, useFormField`
- `input` → `Input` / `textarea` → `Textarea` / `label` → `Label` / `checkbox` → `Checkbox`
- `input-group` → `InputGroup, InputGroupAddon, InputGroupButton, InputGroupInput, InputGroupTextarea, InputGroupText` (带 inline addon/button 的输入框组合; 搜索提交按钮 MUST 用 `InputGroupButton type="submit"`)
- `badge` → `Badge, badgeVariants`（**没有 `BadgeProps`**，import 它直接 TS2305） (variant 仅 default/outline/destructive/secondary, 严禁 success/warning. **普通 Badge 不写定位类；Overlay Badge 用父容器 `relative` + `!absolute` + `z-20`。**)
- 🔴 `alert` 和 `alert-dialog` **是两个组件，别看串**——确认对话框在后者里：
  - `alert` → `Alert, AlertDescription, AlertTitle`（页面内的提示条）
  - `alert-dialog` → `AlertDialog, AlertDialogTrigger, AlertDialogContent, AlertDialogHeader, AlertDialogTitle, AlertDialogDescription, AlertDialogFooter, AlertDialogAction, AlertDialogCancel`（确认弹窗）
  - 从 `@/components/ui/alert` 里 import `AlertDialog*` 会一口气报十几个 `TS2305`，是高频错
- `avatar` → `Avatar, AvatarFallback, AvatarImage`
- `tooltip` → `Tooltip, TooltipContent, TooltipProvider, TooltipTrigger`
- `accordion` / `collapsible` / `popover` / `hover-card` / `command` / `scroll-area` / `separator` / `skeleton` / `progress` / `breadcrumb` / `pagination` / `navigation-menu`
- `sidebar` → `Sidebar, SidebarContent, SidebarFooter, SidebarGroup, SidebarHeader, SidebarMenu, SidebarMenuButton, SidebarMenuItem, SidebarProvider, SidebarTrigger, SidebarInset, useSidebar`
- `chart` → `ChartConfig, ChartContainer, ChartLegend, ChartLegendContent, ChartTooltip, ChartTooltipContent`
- `carousel` → `Carousel, CarouselContent, CarouselItem, CarouselNext, CarouselPrevious`
- `calendar` → `Calendar`
- `toggle` → `Toggle` / `toggle-group` → `ToggleGroup, ToggleGroupItem`

**第三方库**:
- `lucide-react` — icons (LayoutDashboard / Users / Calendar / Settings / Home / Search / Filter / Bell / User / Plus / X / ChevronDown / ChevronRight / ArrowRight / ArrowUp / ArrowDown / Check / Edit / Trash / 等通用 UI 图标).
  - 使用 lucide-react 时，严禁使用 `Dashboard` icon（该名已删除），应使用 `LayoutDashboard` 替代。
  - **图标名基本是单数**，别凭感觉加 s（`Mountain` / `Heart` / `Book` / `Cloud`；`Swords` / `Users` / `Files` / `Folders` 是少数单复数都有的例外；**没有 `Stars`**，星星特效用 `Sparkles`）。`SearchOff` 不存在，搜索无结果用 `SearchX`。不确定就用 `Circle` / `Square` 这类几何图标兜底。
  - 社交媒体场景用 inline SVG (参考 simpleicons.org 的 viewBox + path data), 或者退化用通用 icon (`Mail` / `Link` / `Share2` / `MessageCircle`) 兜底.
- `framer-motion` — `motion.div / AnimatePresence`
- `react-router-dom` — `Link, NavLink, useNavigate, useParams, useLocation, Outlet, Routes, Route`
- `sonner` — toast 见上
- `date-fns` — `format, parseISO, addDays`
- `zod` + `react-hook-form` + `@hookform/resolvers/zod` — 表单验证
- `echarts-for-react` — `import ReactECharts from 'echarts-for-react'` (default import)

**🔴🔴🔴 chart 颜色喂图表库铁律** (违反 → 数据系列黑色/透明/无颜色 → 图表渲染失败):

ECharts/recharts/visx 等图表库的 `color` / `fill` / `stroke` / `backgroundColor` props **走 SVG/Canvas 原生 attribute, 不解析 CSS variable**. 主题变量里的 `--chart-1..5` 要转成 `hex` 字面量再喂图表库:

- ✅ `<ReactECharts option={{ color: ['#5D8A72', '#C9A87C', '#8BA4B0', '#B08C7A', '#96A88C'], series: [...] }} />`
- ✅ `<Cell fill="#5D8A72" />` / `<Line stroke="#C9A87C" />` (recharts)
- ✅ chart-1..5 hex **MUST 跟主题变量里的 `--chart-1..5` 完全一致**（直接抄，不重新调色）

- ❌ **严禁** `color: ['var(--chart-1)', ...]` — 图表库不解析 `var()`, 渲染黑色
- ❌ **严禁** `color: ['hsl(var(--chart-1))', ...]` — 双层包裹, 图表库不解析
- ❌ **严禁** `fill="hsl(var(--chart-1))"` 给 SVG 元素 — SVG attribute 不解析 CSS var (style 属性可以, 但 fill attribute 不行)
- ❌ **严禁** 自己重新调一组 chart hex — 必须跟主题变量一致, 保证全站图表色统一
- ⚠️ 主题变量里**没有** chart-1..5 时：从 primary / accent 衍生一组五个可区分的 hex，**同时补写回主题变量文件**，让后续迭代有唯一出处。不要在各个页面里各编一组。

**例外**: shadcn 的 `<ChartContainer config={...}>` 内部已实现 CSS var → inline style 注入, 用它时可以 `config={{ data: { label: '...', color: 'var(--chart-1)' } }}`. 但**直接** `ReactECharts option.color` 或 recharts `<Cell fill>` 仍 MUST 用 hex.

**严禁脑补**:
- ❌ `@/components/ui/toast` / `@/components/ui/use-toast` (走 sonner)
- ❌ MUI 命名 (CardActions / CardMedia / DialogActions / FormHelperText)
- ❌ antd 命名 (Statistic / Descriptions / Table.Column / Form.Item)
- ❌ Badge variant=`success` / `warning` (只 default/outline/destructive/secondary)

---

## 12. 本模板下的高频坑

### 12.1 handler 必须真实现

每个 button / link / form / select MUST 真实现:
- 路由跳转：`navigate(\`/product/\${item.id}\`)`（动态 slug 来自 mock 数据）
- 状态切换: `setActiveTab(tab)` / `setSelected(item)` / `setOpen(true)`
- 数据更新: `setItems(prev => [...prev, newItem])` / `setItems(prev => prev.filter(i => i.id !== id))`
- 反馈: `toast.success('已提交') + reset()` (mock 异步: `await new Promise(r => setTimeout(r, 800))`)
- 滚动: `document.getElementById('xxx')?.scrollIntoView({ behavior: 'smooth', block: 'start' })`

**表单额外守两条**：`react-hook-form` 用 `disabled={isSubmitting}` 防双击、`<form onSubmit={handleSubmit(onSubmit)} noValidate>`（自动 preventDefault）、提交后 `reset()`；**严禁** `<button onClick={onSubmit}>` 配 `<form onSubmit={onSubmit}>`（双触发）。

**严禁兜底**:
- `onClick={() => {}}` 空函数
- `onClick={() => toast.info('xxx 即将开放')}` 假装实现
- `<button disabled>` 占位
- `<a href="#">` 死链接

### 12.2 这几处类型摩擦，第一次就按下面写

它们不是你写错了，是 TypeScript 与库的类型签名对不上——**不提前写对，`tsc` 会报一串嵌套类型错误**（单个错误能有七八行），光读报错就要花掉几百 token，然后回来改，再跑一次门禁。

🔴 **贯穿全部类型问题的一条**：**类型是读来的，不是想出来的**。传 Props、接回调参数、收窄联合类型之前，**先打开定义它的那个文件把字段和签名看一遍**——数据实体看 data 文件，组件 Props 看组件文件，库的类型看速查表（§11）。凭记忆写字段名、给回调参数补一个"看起来对"的类型、把联合类型当成其中一支用，是这一类报错的全部来源。

**a) `Object.keys()` 遍历以 union 为 key 的常量对象**

`Object.keys()` 的返回类型永远是 `string[]`，不是你的 union：

```tsx
// ❌ 报错：string 不能作为索引 / 不能赋给 CustomerStatus
{Object.keys(CUSTOMER_STATUS_META).map((key) => <SelectItem value={key}>…</SelectItem>)}
// ✅
{(Object.keys(CUSTOMER_STATUS_META) as CustomerStatus[]).map((key) => …)}
```

**b) 🔴 zod + react-hook-form：schema 里有 `.default()` / `.catch()` / `.transform()` / `.pipe()` / `z.coerce` 时，必须处理 input/output 分裂**

这是本栈**最容易吃掉整段返工时间**的一个坑——不预防的话，光是读它那串嵌套类型报错就要花掉几百 token，改完还要重跑一次门禁。

**为什么会错**：这些方法让 zod 的两个类型分家（`.optional()` **不会**——它的 input 和 output 都是 `T | undefined`，不用管）——`z.input` 里这些字段是可选的，`z.output` 里是必填的。而 `zodResolver` 返回的 `Resolver` 按 input 推、`useForm<T>` 按 output 推，两边对不上，`TFieldValues` 就退化成 `FieldValues`，于是 `Control` / `SubmitHandler` / `FormField` 全线报 `TS2322`。

**报错长什么样**：一个表单文件连报五六个 `TS2322`，每个错误七八行嵌套类型，末尾是 `Type 'FieldValues' is missing the following properties from type '{...}'`。看到这个形状就是它，别再逐个字段查。

```tsx
// ❌ schema 里有 .default() 时这样写必报错
const schema = z.object({ name: z.string(), note: z.string().optional().default('') });
const form = useForm<z.infer<typeof schema>>({ resolver: zodResolver(schema), … });

// ✅ 解法一：显式给三个泛型，让 input 和 output 各归各位
const form = useForm<z.input<typeof schema>, unknown, z.output<typeof schema>>({
  resolver: zodResolver(schema),
  defaultValues: { … },
});

// ✅ 解法二：断言（改动最小）
import type { Resolver } from 'react-hook-form';
type FormValues = z.infer<typeof schema>;
const form = useForm<FormValues>({
  resolver: zodResolver(schema) as Resolver<FormValues>,
  defaultValues: { … },
});
```

`onSubmit` 的参数按 output 类型标注（`z.output<typeof schema>`），提交拿到的是补完默认值的数据。

**c) shadcn `Select` 的 `onValueChange` 给的是 `string`**

state 是 union 类型时要断言回去：

```tsx
// ❌ string 不能赋给 TimeFilter
<Select value={timeFilter} onValueChange={setTimeFilter}>
// ✅
<Select value={timeFilter} onValueChange={(v) => setTimeFilter(v as TimeFilter)}>
```

配合 `<FormField>` 用时 `field.onChange` 已经是宽松签名，可以直接传，不用断言。

### 12.3 Tailwind v4 的 arbitrary value 里空格写成 `_`

- ❌ `grid-cols-[max-content,auto]`（v4 移除了 `grid-cols-*` / `grid-rows-*` / `object-*` 里「逗号当空格」的兼容）
- ✅ `grid-cols-[max-content_auto]`；颜色写 `bg-[rgb(31_35_41)]` / `bg-[rgb(31_35_41_/_0.15)]`
- ℹ️ 任意值里的逗号本身照常透传，`shadow-[0_35px_35px_rgba(0,0,0,0.25)]` 是合法的
- ✅ 更推荐直接用 token：`bg-foreground/15` / `bg-border` / `bg-card`

### 12.4 复刻场景不要用 iframe 套壳

把上传 / 抓取来的整份 HTML 塞进 `public/` 再 `<iframe src>` 套壳是反模式——**要提取重写为组件 + Section**（文案、结构、配色照抄，图片下载进 `public/` 后按相对路径引）。路径规则见 §9。

### 12.5 组件 props：不要空 interface，不要 React.FC

- ❌ `interface IHomePageProps {}` + `React.FC<...>`（空 interface 没有意义，直接删掉 props 类型；这条 lint 不拦，靠你不写）
- ✅ 无 props 直接 `export default function HomePage() {}`
- ✅ 有 props：`export default function HeroSection({ title }: HeroSectionProps) {}`
- **永远不用 `React.FC`**（隐式 children 早已废弃，泛型组件也写不了）
- Props interface 命名 `XxxSectionProps`，**不加 I 前缀**（业务实体才用 `IXxx`）

### 12.6 localStorage 必须带项目命名空间

多个产物可能部署在同一域名下，裸 key 会互相覆盖：

```ts
const NS = 'sales-dashboard';   // = 任务目录名，全项目唯一
export const store = {
  get<T>(k: string, fb: T): T {
    try { const v = localStorage.getItem(`${NS}:${k}`); return v ? (JSON.parse(v) as T) : fb; } catch { return fb; }
  },
  set(k: string, v: unknown) {
    try { localStorage.setItem(`${NS}:${k}`, JSON.stringify(v)); } catch { /* 隐私模式静默降级 */ }
  },
};
```

⚠️ 读写**必须包 try/catch**：隐私模式 / 禁用站点数据时访问 `localStorage` 本身就会抛，没兜底会整页白屏。

### 12.7 🔴 render 期间必须是纯的（本模板最高频的门禁失败）

模板开了 React Compiler 的整组 lint 规则，**全是 error 级、门禁直接挂**。它们看起来是五六条不同的报错，其实是同一条要求：**组件函数体（不含 effect 和事件回调）必须纯**。记住这一条，那几类报错都不会出现：

- **不改任何外部东西**：不 `setState`、不写 `ref.current`、不改模块级变量、不 `push` 外部数组
- **不读 `ref.current`**——要读只能在 effect 或事件回调里
- **不做有副作用的调用**：`Math.random()`、`Date.now()`、日志、请求，都不能出现在函数体里（要随机值或时间戳，在事件回调里算或用 state 存）
- **组件定义只写在模块顶层**，不在函数体里现造一个组件 return 出去

两条配套的：

- **effect 里不要同步 `setState`**。能在 render 里直接算出来的值就直接算（派生状态不用存），要响应用户操作的放事件回调；effect 只留给「跟外部系统同步」。
- **不要手写 `useMemo` / `useCallback` 做性能优化**：Compiler 会自动 memo，做得比手写准。手写而依赖不全会报 `Existing memoization could not be preserved`。只在「值要传给靠引用相等优化的子组件」或「计算确实昂贵」时才手写，且依赖写全。

### 12.8 交付前清掉调试 console

开发时用 `console.log` 没问题，交付前逐个删掉；真要保留错误上报就写个薄封装集中一处。`catch` 里把 error 转成字符串再输出（`String(error)`）——直接扔 Error 对象在部分环境会打印成 `{}`。

---

## 13. 中后台横向 overflow（高频翻车）

**截图反例**: 表格列横向流出 main 容器盖到 Sidebar 上 — shadcn 常见坑.

**根因**: shadcn 的 `<Sidebar>` 是 `fixed/absolute` 定位 (不是 flex sibling). `<Table>` 自身带 `overflow-x-auto` 容器, **但父级 flex 子项没有 `min-w-0` 时这个容器会被内容直接撑宽**, 滚动条不出现, 表格 z 轴溢出跟 sidebar 重叠.

**MUST 做**（中后台 Table / 长内容容器 / 横向滚动 Card 列表）——**Table 三铁律**:
1. ✅ 表格所在的 flex 子项 **MUST 有 `min-w-0`**; 外层再包一层 `<div className="w-full overflow-x-auto">` 兜底
2. ✅ `<TableHead>` MUST `className="whitespace-nowrap"` (列名不换行, 长列名靠横向滚动展示)
3. ✅ 单元格内长文本 MUST `<span className="truncate block max-w-[200px]">` 或外层加 `max-w-*` (避免单元格内容把列撑爆)

**横向 flex 容器**：MUST `min-w-0`（允许子项收缩）+ `overflow-hidden` 兜底；子项里有可能很宽的内容（长表格 / 长 URL）时父容器 MUST `overflow-x-auto`。❌ 严禁给 main / Page root 加 `overflow-x-visible`（默认就是 visible，显式写会绕过 Layout 已设的兜底）。

**双层滚动反例**:
- ❌ Page root `min-h-screen` + `overflow-y-auto` (Layout 已有 main overflow-y-auto, Page 再加一层 → 内容滚动出主容器)
- ❌ Page root `h-screen` (Page 撑死视口, 内容超时直接滚出 SidebarInset 边界)
- ✅ 中后台 Page root **不带 h-/min-h-/overflow-** (Layout main 单独负责滚动)

---

## 14. 锚点导航组件（anchor 单页才需要）

`react-router-dom` 的 `Link` / `NavLink` 在 `BrowserRouter` 下**不会滚动到锚点**——anchor 单页最高频的 bug。自建 `AnchorLink` 统一处理，关键三点：

- 点击时 `e.preventDefault()` + `document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })`，再用 `history.replaceState` 同步地址栏（不走路由）
- active 态用 `IntersectionObserver` 算，`rootMargin: '-45% 0px -45% 0px'`——视口中带命中才算当前区块
- 各 Section 外层必须带对应 `id`，否则 observer 拿不到目标、active 永远 false；Header 是 sticky 时给目标区块加 `scroll-mt-16`

## 15. 依赖选型

| 用途 | 用什么 |
|---|---|
| UI 元素 | `@/components/ui/{kebab-name}`（shadcn，new-york 风格）。**不要**再引第二套 UI 库（antd / MUI / Chakra），视觉风格统一不了 |
| 图标 | `lucide-react` |
| Toast | `sonner`（`import { toast } from 'sonner'`，Provider 挂在 Layout） |
| 图表 | 复杂用 `echarts-for-react`，简单用 `recharts` —— **二选一，不混用** |
| 表单 | `react-hook-form` + `zod` + `@hookform/resolvers` + `@/components/ui/form` |
| 动画 | 90% 用 `framer-motion`；scroll-trigger / 复杂时间线用 `gsap` + `@gsap/react` |
| 路由 | `react-router-dom@7` |
| 时间日期 | `date-fns`；简单场景原生 `Date` 也够 |
| 工具函数 | `@/lib/utils` 的 `cn`（clsx + tailwind-merge） |
| 网络请求 | 原生 `fetch` 封装在 `src/api/*.ts`，统一处理 loading / error |
| 全局状态 | `useState` / Context 就够，这个体量用不到 redux / zustand |
| 按需装的 | PDF **优先原生 `<iframe>`，不装库**（要页码控制才 `react-pdf`，见 §9） · 地图 `leaflet`+`react-leaflet` · csv/xlsx `papaparse`/`xlsx` · 日历 `@fullcalendar/react` · 拖拽 `@dnd-kit/core` · 富文本 `@tiptap`（只在明确要求时引） |

**该装就装**——这条链路能引三方依赖是它相对 html 链路的核心优势，遇到 PDF / 地图 / 表格解析这类需求手搓一个残废版本是反模式。只守两条：脚手架和 shadcn 已提供的能力不重复引；每装一个都要在交付说明里能讲清为什么必须装。

---
