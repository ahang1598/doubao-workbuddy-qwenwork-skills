# shadcn/ui 快速通道（Setup Guide）

> **文件用途**：当用户明确指定使用 shadcn/ui 时，提供完整可靠的安装、配置和代码生成规范。
> 与 Spark Design NPM 模式并列，作为技术栈的第二通道。

---

## 一、shadcn vs Spark 的选择参考

| 维度 | Spark Design（默认） | shadcn/ui |
|---|---|---|
| 安装方式 | `npm install sparkdesign`（一行） | `npx shadcn@latest init` + 按需 add |
| 组件管理 | 全部在 `sparkdesign` 包内 | 组件写入 `src/components/ui/`，可直接修改 |
| 主题系统 | `ThemeStyleProvider` + Spark token | CSS 变量 + `next-themes` 或手动 class |
| 文档与社区 | 较小 | 极为丰富，AI 熟悉度高 |
| 适合场景 | 需要 Spark DS 一致性的项目 | 开源项目、需要高度自定义组件逻辑的项目 |

**触发 shadcn 通道的条件**：用户明确说「用 shadcn」「shadcn/ui」或「我想用 shadcn」。

---

## 二、脚手架安装流程

```bash
# 1. 创建 Vite + React + TypeScript 项目
npm create vite@latest [project-name] -- --template react-ts
cd [project-name]
npm install

# 2. 初始化 shadcn（交互式，选 Vite + TypeScript）
npx shadcn@latest init
# 提示选择时：
#   - Style: Default（或 New York）
#   - Base color: Slate（或用户指定）
#   - CSS variables: Yes

# 3. 安装常用组件（可按需调整）
npx shadcn@latest add button input form dialog sheet card table tabs badge
npx shadcn@latest add select textarea checkbox switch avatar progress skeleton
npx shadcn@latest add dropdown-menu alert-dialog popover tooltip toast
npx shadcn@latest add separator scroll-area breadcrumb pagination accordion

# 4. 安装路由和图标
npm install react-router-dom lucide-react
```

**shadcn 安装的优势**：每个 `npx shadcn add [component]` 会将组件文件写入 `src/components/ui/`，100% 可验证，不存在"组件没装"的不确定性。

---

## 三、Vite 配置

### vite.config.ts

```ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
})
```

> `npx shadcn@latest init` 会自动配置 `tsconfig.json` 的路径别名，但 vite.config 需要手动确认 `@` 别名已添加。

---

## 四、样式体系与 Tailwind 配置

shadcn 使用 **Tailwind CSS 3**（不是 CSS 4）。`init` 会自动生成：

- `tailwind.config.js`：包含 shadcn 的 CSS 变量扩展
- `src/index.css`：包含 `:root` 和 `.dark` CSS 变量定义

### 颜色使用规范（shadcn 语义类）

| 语义类 | 用途 |
|---|---|
| `bg-background` | 页面主背景 |
| `bg-card` | 卡片背景 |
| `bg-muted` | 次级区域背景 |
| `text-foreground` | 主要文字 |
| `text-muted-foreground` | 辅助文字 |
| `text-primary` | 主色文字 |
| `border-border` | 边框颜色 |
| `bg-primary` + `text-primary-foreground` | 主色按钮 |
| `bg-destructive` + `text-destructive-foreground` | 危险操作 |

**❌ 禁止**：在 shadcn 模式下使用 Spark token 类（`bg-bg-base`、`text-text` 等），两套体系不可混用。

---

## 五、暗色模式配置

shadcn 使用 `class` 切换暗色，而非 `data-theme`。有两种方式：

### 方式 A：手动切换（简单，推荐用于 Flow 原型）

```tsx
// src/App.tsx
import { useState, useEffect } from 'react'

function App() {
  const [isDark, setIsDark] = useState(false)

  useEffect(() => {
    document.documentElement.classList.toggle('dark', isDark)
  }, [isDark])

  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* 应用内容 */}
    </div>
  )
}
```

### 方式 B：next-themes（生产推荐）

```bash
npm install next-themes
```

```tsx
// src/main.tsx
import { ThemeProvider } from 'next-themes'

createRoot(document.getElementById('root')!).render(
  <ThemeProvider attribute="class" defaultTheme="light">
    <App />
  </ThemeProvider>
)
```

---

## 六、组件 import 规范

```tsx
// shadcn 组件从本地 src/components/ui/ import
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '@/components/ui/alert-dialog'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from '@/components/ui/dropdown-menu'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { Progress } from '@/components/ui/progress'
import { Skeleton } from '@/components/ui/skeleton'
import { Separator } from '@/components/ui/separator'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Switch } from '@/components/ui/switch'
import { Checkbox } from '@/components/ui/checkbox'
import { Textarea } from '@/components/ui/textarea'
import { Slider } from '@/components/ui/slider'
```

---

## 七、App Shell 模板（shadcn 版）

```tsx
// src/flows/[feature-name]/[feature-name].tsx
import { useState, useEffect } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { Flow1_[Name] } from '../flow-1/flow1-[name]'
import { Flow2_[Name] } from '../flow-2/flow2-[name]'
import { Moon, Sun } from 'lucide-react'
import { Button } from '@/components/ui/button'

export function [ProductName]App() {
  const [isDark, setIsDark] = useState(false)
  const [isAuthenticated, setIsAuthenticated] = useState(false)

  useEffect(() => {
    document.documentElement.classList.toggle('dark', isDark)
  }, [isDark])

  if (!isAuthenticated) {
    return <Flow_Signup onComplete={() => setIsAuthenticated(true)} />
  }

  return (
    <div className="flex h-screen bg-background text-foreground">
      {/* 侧边栏 / 顶部导航（基于 Step 3 导航模式） */}
      <nav className="w-64 border-r bg-card flex flex-col">
        {/* Nav items */}
        <div className="mt-auto p-4">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setIsDark(d => !d)}
          >
            {isDark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </Button>
        </div>
      </nav>

      <main className="flex-1 overflow-auto">
        <Routes>
          <Route path="/" element={<Navigate to="/[flow-1-path]" replace />} />
          <Route path="/[flow-1-path]" element={<Flow1_[Name] />} />
          <Route path="/[flow-2-path]" element={<Flow2_[Name] />} />
        </Routes>
      </main>
    </div>
  )
}
```

---

## 八、shadcn 模式的技术约束

生成代码时，shadcn 模式下的规范：

```
- [ ] 颜色使用 shadcn 语义类（bg-background、text-foreground、bg-muted 等）
- [ ] 组件 import 来自 @/components/ui/[component]
- [ ] 暗色模式通过 document.documentElement.classList.toggle('dark') 切换
- [ ] Tooltip 必须有 TooltipProvider 包裹
- [ ] 表单使用 react-hook-form + shadcn Form 组件
- [ ] 不使用 Spark token 类（bg-bg-base、text-text 等）
- [ ] 不使用 ThemeStyleProvider（Spark 专用）
```

---

## 九、常见问题 FAQ

**Q: `npx shadcn@latest add` 和 `npx shadcn add` 有什么区别？**
A: `shadcn@latest` 保证使用最新版 CLI，推荐始终使用 `@latest`。

**Q: 组件 add 后如何确认安装成功？**
A: 检查 `src/components/ui/` 目录是否出现对应的 `.tsx` 文件。例如 `npx shadcn add button` 后应看到 `src/components/ui/button.tsx`。

**Q: shadcn 和 Tailwind CSS 4 兼容吗？**
A: 截至 2026 年初，shadcn 官方主要支持 Tailwind CSS 3。若需要 Tailwind CSS 4，目前建议在 shadcn 模式下保持使用 Tailwind CSS 3（`npm install tailwindcss`），而非 `@tailwindcss/vite`。

**Q: 如何自定义 shadcn 的主题色？**
A: 修改 `src/index.css` 中 `:root` 块的 HSL 值，不修改组件文件中的 className。
