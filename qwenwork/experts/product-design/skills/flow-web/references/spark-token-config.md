# Spark Design Token 配置规范（NPM 模式）

> **文件用途**：定义 Spark Design NPM 模式的安装流程、token 系统、Tailwind CSS 4 语义类使用规范，以及项目脚手架配置模板。
> SKILL.md 在 Step 4 Phase A 读取本文件，生成代码时必须遵循本文档的 token 规范。

---

## 一、主题系统核心原则

1. **所有颜色必须引用 Spark token**：优先使用 Tailwind 语义类（`bg-bg-base`），次选 inline style 引用 CSS 变量（`style={{ color: 'var(--color-text)' }}`）
2. **禁止硬编码颜色值**（如 `bg-white`、`text-black`、`#000000`、`rgb(255,255,255)`）
3. **亮/暗色模式通过 `ThemeStyleProvider` 的 `appearance` prop 切换**，而非手动 `useEffect`
4. **视觉风格通过 `ThemeStyleProvider` 的 `style` prop 控制**（如 `"soft"`）
5. **token 通过 `sparkdesign/theme.css` + `sparkdesign/scale.css` 引入**，在 `src/index.css` 中用 `@import`，不得手动修改

---

## 二、主题初始化（必须）

Spark Design NPM 模式使用 `ThemeStyleProvider` 统一管理主题。**所有 Spark 组件必须在 `<ThemeStyleProvider>` 内部渲染**，否则颜色 token 无法解析。

```tsx
import { ThemeStyleProvider } from 'sparkdesign'
import { useState } from 'react'

export function AppRoot() {
  const [appearance, setAppearance] = useState<'light' | 'dark'>('light')

  return (
    <ThemeStyleProvider
      appearance={appearance}   // 'light' | 'dark'，控制亮/暗
      theme="mint"             // Spark 主题名，当前可用：'mint'、'parchment'
      style="soft"              // 视觉风格：见下方说明
    >
      {/* 全部应用内容 */}
    </ThemeStyleProvider>
  )
}
```

**ThemeStyleProvider Props 说明**：

| Prop | 类型 | 说明 |
|---|---|---|
| `appearance` | `'light' \| 'dark'` | 亮/暗色模式，响应 state 变化实时切换 |
| `theme` | `string` | Spark 主题名，决定主色调，当前可用：`mint`（默认）、`parchment` |
| `style` | `string` | 视觉风格，见下方说明 |

> ⚠️ **`data-theme` 实际值与 `theme` prop 不同**：`ThemeStyleProvider` 内部会根据 `appearance` + `theme` 组合计算 `data-theme`，不要手动在 HTML 上写 `data-theme="mint"`（该值不存在）。对应关系：
>
> | `appearance` + `theme` | 实际 `data-theme` 值 |
> |---|---|
> | `light` + `mint` | `"light"` |
> | `dark` + `mint` | `"dark"` |
> | `light` + `parchment` | `"light-parchment"` |
> | `dark` + `parchment` | `"dark-parchment"` |

**`style` 可用值（5 种）**：

| style | 特点 | 推荐场景 |
|---|---|---|
| `neutral` | 平衡默认，圆角适中 | 通用产品、内容站 |
| `compact` | 紧凑间距，信息密度高 | 工具类后台、运营系统 |
| `soft` | 大圆角、宽松间距 | 消费类产品、AI 产品 |
| `sharp` | 直角利落，无圆角 | 金融、开发者工具 |
| `dense` | 最小留白、最高密度 | 数据密集型 BI、监控大屏 |

> ⚠️ **不同 theme 的 token 含义不同**：`mint` 主题下 `bg-bg-highlight` 为深色（接近黑色 #080807），不可用作浅色卡片背景。通用卡片/面板背景请使用 `bg-fill-secondary`。

---

## 三、index.css 标准结构（NPM 模式）

> ⚠️ **严禁在项目 index.css 中添加 `@theme` 或 `@theme inline` 块。**
> `sparkdesign/theme.css` 内部已通过 `theme-base.css` 完整注册了所有 Tailwind 颜色 token（`@theme { --color-primary: var(--token-color-primary); ... }`）。
> 若项目层面再加一遍 `@theme inline { --color-primary: var(--color-primary); }`，会产生**自引用循环**，Tailwind 将变量值解析为 `unset`，导致所有颜色归零、组件样式完全丢失。

**完全替换** `src/index.css` 为以下内容，不保留 Vite 默认 CSS：

```css
@import "tailwindcss";
@import 'sparkdesign/theme.css';
@import 'sparkdesign/scale.css';

body {
  margin: 0;
  font-family: system-ui, -apple-system, sans-serif;
  background-color: var(--color-bg-base);
  color: var(--color-text);
}
```

> **为什么用 `theme.css` + `scale.css` 而非 `tokens/index.css`？**
> `sparkdesign/theme.css` 和 `sparkdesign/scale.css` 在 `package.json` exports 中有明确映射，路径稳定可靠。`tokens/index.css` 是通配符路径，不同版本可能存在差异。

**token 三层链路说明**（只需理解，无需手动配置）：

```text
sparkdesign/theme.css（含内置主题 light-mint / dark-mint / light-parchment / dark-parchment）
  └─ :root, [data-theme="light"] { --token-color-primary: #8EE5A1; ... }  ← 原始色值
         ↓
theme-base.css（内含于 theme.css）
  └─ @theme { --color-primary: var(--token-color-primary); ... }           ← 注册 Tailwind 工具类
         ↓
Tailwind 生成工具类
  └─ .bg-primary { background-color: var(--color-primary); }               ← 可直接用
```

`sparkdesign/scale.css` 提供布局风格 token（圆角、间距节奏，对应 `data-style` 属性）。

**NPM 模式与 CLI 模式的关键区别**：

| 项目 | CLI 模式（v3，已废弃） | NPM 模式（v4，当前） |
|---|---|---|
| Token 注入 | `npx sparkdesign init` 写入约 900 行到 index.css | `@import 'sparkdesign/theme.css'` + `@import 'sparkdesign/scale.css'` 两行 |
| 需要 `@source` | ✅ 需要扫描本地组件文件 | ❌ 不需要（组件在 node_modules） |
| 组件安装 | `npx sparkdesign add button` | `npm install sparkdesign`（全部组件一次安装） |
| 组件 import | `@/components/ui/basic/button` | `from 'sparkdesign'` |
| 主题初始化 | `useEffect` 手动设 `data-theme` | `<ThemeStyleProvider>` 组件 |

---

## 四、Tailwind 语义类使用规范

`sparkdesign/tokens/index.css` 导入后，Tailwind 工具类由 sparkdesign 内部的 `theme-base.css` 自动注册，可直接在 className 中使用以下语义类（**无需任何额外配置**）。

**Token 使用原则（来自 ontology.json）：**

| 类别 | ✅ 推荐 | ❌ 禁止 |
|---|---|---|
| 颜色 | `text-text` `text-text-secondary` `bg-bg-base` `bg-bg-elevated` `bg-fill-secondary` `border-border` `bg-primary` `text-primary-foreground` | 硬编码 hex（`#fff`）、原生 `rgb()/rgba()`、shadcn token（`bg-background` `text-foreground`） |
| 间距 | `gap-*` `p-*` `px-*` `py-*` `var(--spacing-*)` | 任意 px/rem 间距（`p-[12px]`、`gap-[7px]`） |
| 圆角 | `rounded-sm` `rounded-md` `rounded-lg` `rounded-full` | 任意 px 圆角（`rounded-[10px]`） |
| 动效 | 简短功能性 transition（`transition-colors`）、Framer Motion 处理状态跳转 | 纯装饰性动效、无 `prefers-reduced-motion` 考量的复杂动画 |

### 4.1 背景色（Background）

#### 容器层级规范（必须按层级选 token）

> ⚠️ **`bg-fill-*` 是表单控件填充色，不是容器背景色**。将 `bg-fill-secondary` 用于 Card/Sidebar/Panel 是高频错误——它的色值 `#EFEFEF` 会让所有容器呈现明显灰色，视觉上像未加载完成的页面。容器背景必须用 `bg-bg-*` 系列。

| 容器类型 | ✅ 正确 token | mint 主题色值 | ❌ 常见错误 |
| --- | --- | --- | --- |
| 页面底层背景（`<body>` / 最外层 div） | `bg-bg-base` | `#FFFFFF` | `bg-fill-secondary` |
| Layout 区域（Sidebar / 顶部导航栏） | `bg-bg-layout` | `#FDFDFD` | `bg-fill-secondary` |
| Card / Panel 容器 | `bg-bg-container` | `#FFFFFF` | `bg-fill-secondary` |
| 次级悬浮层 / hover 背景 | `bg-bg-elevated` | `#F9F9F9` | `bg-fill-secondary` |
| 表单输入框填充（Input/Select 内部） | `bg-fill-secondary` | `#EFEFEF` | — |
| 表单控件默认填充 | `bg-fill` | `#DFDFDF` | — |

**记忆口诀**：`bg-*` 是布局背景，`fill-*` 是控件填充，两者语义层完全不同，不可混用。

#### Border 层级规范

| 使用场景 | ✅ 正确 token | mint 主题色值 |
|---|---|---|
| 重要分割线（Section 之间） | `border-border` | `#BCBBBA` |
| Card / Panel 边框 | `border-border-secondary` | `#DDDDDD` |
| 表格行分割 / 轻量边框 | `border-border-tertiary` | `#E6E6E6` |

#### 完整背景 token 参考

| 语义类 | 对应 token | 用途 |
|---|---|---|
| `bg-bg-base` | `--color-bg-base` | 页面/应用主背景 |
| `bg-bg-layout` | `--color-bg-layout` | 侧边栏 / 顶部导航区域背景 |
| `bg-bg-container` | `--color-bg-container` | Card、Panel 容器背景 |
| `bg-bg-elevated` | `--color-bg-elevated` | 悬停背景 / 次级浮层 |
| `bg-bg-spotlight` | `--color-bg-spotlight` | 高亮聚焦区域 |
| `bg-bg-highlight` | `--color-bg-highlight` | ⚠️ 主题相关，见下方警告 |
| `bg-primary` | `--color-primary` | 主色背景（主按钮） |
| `bg-fill` | `--color-fill` | 表单控件默认填充色（Input 背景） |
| `bg-fill-secondary` | `--color-fill-secondary` | 表单控件次级填充色（Select hover 等） |
| `bg-success-bg` | `--color-success-bg` | 成功状态背景 |
| `bg-error-bg` | `--color-error-bg` | 错误状态背景 |
| `bg-warning-bg` | `--color-warning-bg` | 警告状态背景 |
| `bg-info-bg` | `--color-info-bg` | 信息状态背景 |

> ⚠️ **`bg-bg-highlight` 主题陷阱（高频问题）**：在 `mint` 主题下此 token 为深色（`#080807`，接近纯黑），**不可用作任何容器背景**。遇到"卡片显示为黑色"问题时，立即检查是否误用了 `bg-bg-highlight`。

**❌ 禁止使用**：`bg-white`、`bg-gray-100`、`bg-background`（shadcn 类）、`bg-[#fff]`、**`bg-fill-secondary` 作为 Card/Sidebar/Panel 背景**

---

### 4.2 文字色（Text）

| 语义类 | 对应 token | 用途 |
|---|---|---|
| `text-text` | `--color-text` | 主要文字（标题、正文） |
| `text-text-secondary` | `--color-text-secondary` | 辅助文字、说明、占位符 |
| `text-text-on-primary` | `--color-text-on-primary` | 主色背景上的文字 |
| `text-success` | `--color-success` | 成功状态文字 |
| `text-error` | `--color-error` | 错误状态文字 |
| `text-warning` | `--color-warning` | 警告状态文字 |
| `text-info` | `--color-info` | 信息状态文字 |

**❌ 禁止使用**：`text-black`、`text-gray-500`、`text-foreground`（shadcn 类）、`text-[#333]`

---

### 4.3 状态色组合（Status Color Sets）

每种状态有三个配套 token，组合使用：

```tsx
/* 成功状态 */
<div className="bg-success-bg text-success border border-success-border rounded-md p-3">
  操作成功
</div>

/* 错误状态 */
<div className="bg-error-bg text-error border border-error-border rounded-md p-3">
  操作失败
</div>
```

---

### 4.4 间距（Spacing）

优先使用 Tailwind 默认 scale，**禁止自定义像素值**：

| 类别 | 推荐值 | 说明 |
|---|---|---|
| **Padding** | `p-2`、`p-3`、`p-4`、`p-6` | 8px、12px、16px、24px |
| **Margin** | `m-2`、`m-3`、`m-4`、`mb-4` | 同上 |
| **Gap** | `gap-2`、`gap-3`、`gap-4`、`gap-6` | Flex/Grid 间距 |

**❌ 禁止使用**：`p-[12px]`、`m-[20px]`、`gap-[15px]`

---

### 4.5 圆角（Radius）

| 语义类 | 对应 token | 用途 |
|---|---|---|
| `rounded-sm` | `--radius-sm` | 小元素、标签 |
| `rounded` | `--radius-DEFAULT` | 默认按钮、输入框 |
| `rounded-md` | `--radius-md` | 卡片、面板 |
| `rounded-lg` | `--radius-lg` | 大型容器、弹层 |
| `rounded-full` | `--radius-full` | 头像、圆形按钮、标签 |

**❌ 禁止使用**：`rounded-[6px]`、`rounded-[10px]`

---

## 五、代码示例（正确 vs 错误）

### ✅ 正确示例

```jsx
// 页面背景容器
<div className="min-h-screen p-6 bg-bg-base text-text">

// 卡片
<div className="bg-bg-highlight rounded-md p-4">
  <p className="text-text">主要内容</p>
  <p className="text-text-secondary">辅助说明</p>
</div>

// 状态提示
<div className="bg-error-bg text-error rounded p-3">表单校验错误提示</div>

// Spark 组件（from 'sparkdesign'）
import { Button, Tag } from 'sparkdesign'
<Button variant="primary">主操作</Button>
<Button variant="secondary">次操作</Button>
<Button variant="ghost">幽灵按钮</Button>
<Tag color="success">成功</Tag>
```

### ❌ 错误示例

```jsx
// ❌ 硬编码颜色
<div className="bg-white text-black border-gray-200">...</div>

// ❌ shadcn 语义类
<div className="bg-background text-foreground bg-card text-muted-foreground">...</div>

// ❌ 自定义像素值
<div className="p-[12px] m-[20px] rounded-[6px]">...</div>

// ❌ 旧版 CLI 模式 import 路径（v3 格式，已废弃）
import { Button } from '@/components/ui/basic/button'

// ❌ 在 index.css 中添加 @theme inline（会导致循环引用，全部颜色归零）
// @theme inline {
//   --color-primary: var(--color-primary);  ← 自引用，CSS 引擎解析为 unset
// }
```

---

## 六、快速检查清单

生成代码后，必须验证：

```
环境配置
- [ ] src/index.css 只有 @import "tailwindcss" + @import 'sparkdesign/theme.css' + @import 'sparkdesign/scale.css' + body，无任何 @theme 块
- [ ] vite.config.js 包含 @tailwindcss/vite 插件
- [ ] src/main.jsx 第一行是 import 'sparkdesign/style'，import './index.css' 放在最后（App import 之后）
- [ ] App Shell 已用 <ThemeStyleProvider> 包裹所有内容
- [ ] App Shell 内有 <ErrorBoundary> 包裹（白屏时可定位错误原因）

组件合规（对照 spark-component-map.md 验证）
- [ ] Spark 组件 import 均来自 'sparkdesign' 包，无旧版 @/components/ui/basic/ 路径
- [ ] 未使用不存在的组件：Form（改用 Field 系列）、Accordion（改用 Collapse 系列）、Badge（改用 Tag）
- [ ] 未使用废弃名称：OtpInput（改用 InputOTP）、Sidebar（改用 SidebarMenu）
- [ ] Toast 未作为 JSX 渲染，而是 App Shell 放 <Toaster />，其他地方调用 toast() 函数
- [ ] 复合组件已使用完整子组件链（Select/Tabs/Dialog/Breadcrumb 等不可只写根组件）
- [ ] 空状态使用 Empty 系列组件，AI 场景使用 ChatInput/Response/UserMessage 系列

样式规范
- [ ] 无 bg-white、bg-black、text-gray-500 等硬编码颜色
- [ ] 无 bg-background、text-foreground、bg-card 等 shadcn 语义类
- [ ] 无 p-[12px]、m-[20px]、rounded-[6px] 等自定义像素值
- [ ] 卡片/面板背景未使用 bg-bg-highlight（mint 主题下为深色 #080807）
- [ ] **容器背景未使用 bg-fill-* 系列**：Sidebar→bg-bg-layout，Card/Panel→bg-bg-container，hover→bg-bg-elevated（bg-fill-secondary 仅限表单控件填充）
- [ ] **容器 border 按层级**：Card 边框用 border-border-secondary，表格行分割用 border-border-tertiary，重要分割线才用 border-border
- [ ] 间距使用 Tailwind scale（p-4、m-2、gap-3）
- [ ] 圆角使用语义类（rounded、rounded-md、rounded-lg）
```

---

## 七、常见问题 FAQ

**Q: 暗色模式下组件颜色不正确？**
A: 检查 `<ThemeStyleProvider appearance={appearance}>` 是否包裹了所有组件。Tooltip、Dialog 等 portal 类组件也需要在 Provider 内部渲染（Spark NPM 版本的 ThemeStyleProvider 已处理 portal 的主题继承）。

**Q: 为什么不能用 `bg-white`？**
A: `bg-white` 在暗色模式下仍是白色，破坏主题切换。应使用 `bg-bg-base`，它会跟随 `appearance` prop 自动切换。

**Q: 卡片背景颜色异常（在某些主题下显示为黑色）？**
A: `bg-bg-highlight` 在不同主题下含义不同（如 `mint` 主题下是深色）。遇到此问题，在 DevTools 检查 `--color-bg-highlight` 的实际 computed value，改用 `bg-bg-container` 作为卡片背景（注意：不是 `bg-fill-secondary`，fill 系列是表单控件填充色，用于卡片会产生灰色外观）。

**Q: 不同 theme 参数有哪些？**
A: sparkdesign 0.4.x 当前可用 theme 为 `mint`（默认）和 `parchment`。**`qoder` 已从可用列表移除**（token 文件不存在，不可使用）。如需确认当前版本支持的 theme，查看 `node_modules/sparkdesign/dist/tokens/themes/` 目录下的文件名。

**Q: 修复 tslib 后浏览器仍报同样的 import 错误？**
A: Vite 在 tslib 缺失时已预打包了 sparkdesign 的依赖缓存，安装 tslib 后 Vite 未感知变化，继续使用旧缓存。修复后必须清除缓存再重启：

```bash
rm -rf /absolute/path/[project]/node_modules/.vite
# 然后重启 dev server
npm run dev
```

**Q: inline style 什么时候用？**
A: 需要动态赋值或 Tailwind 工具类不覆盖的场景：`style={{ backgroundColor: 'var(--color-primary)' }}`。注意直接引用 `--color-*` 变量（由 sparkdesign 的 `@theme` 注册），而非原始的 `--token-color-*`。

---

## 八、脚手架配置模板（NPM 模式）

> Phase A 生成新项目时，按以下模板配置文件。

### 安装命令（完整序列）

> ⚠️ **执行规则**：分三次独立 Bash 调用，全部使用绝对路径。
> Bash tool 的 `cd` 不跨调用持久化，若依赖 `cd` 后分次执行，npm 会在错误目录安装依赖。

```bash
# 第一次 Bash 调用：创建项目
npm create vite@latest [project-name] -- --template react
```

```bash
# 第二次 Bash 调用：全链式安装（必须在同一次调用中完成，不得拆分）
cd /absolute/path/to/[project-name] && npm install && npm install sparkdesign && npm install tslib && npm install -D tailwindcss @tailwindcss/vite && npm install react-router-dom lucide-react
```

```bash
# 第三次 Bash 调用：验证 tslib（必须用绝对路径确认）
ls /absolute/path/to/[project-name]/node_modules/tslib
```

> ⚠️ **为什么要单独验证 tslib**：`npm install sparkdesign tslib` 链式写法中，`tslib` 作为 sparkdesign 的 peer dependency 可能被 npm 静默跳过，导致 `npm run build` 报 `Rolldown failed to resolve import "tslib"` 错误。
>
> **若第三次验证显示 `No such file or directory`，执行修复命令**：
>
> ```bash
> npm install tslib --prefix /absolute/path/to/[project-name]
> ls /absolute/path/to/[project-name]/node_modules/tslib  # 再次确认
> rm -rf /absolute/path/to/[project-name]/node_modules/.vite  # 清除 Vite 缓存
> ```

### vite.config.js

```js
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { '@': '/src' },
  },
})
```

### src/main.jsx

> **注意**：`import 'sparkdesign/style'` 必须是**绝对第一行**。`import './index.css'` 应放在**最后**（App import 之后），让 Tailwind utility class 在 CSS 层叠中排在组件样式之后，确保语义类能正确覆盖组件默认值。

```jsx
import 'sparkdesign/style'       // ← 必须第一行：Spark 组件样式
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.jsx'
import './index.css'             // ← 最后：Tailwind + Spark token 语义类（确保 utility 优先级）

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
```

### src/index.css（完整替换，删除 Vite 默认内容）

> ⚠️ **不得添加 `@theme` 或 `@theme inline` 块**，否则导致循环引用、颜色全部归零。

```css
@import "tailwindcss";
@import 'sparkdesign/theme.css';
@import 'sparkdesign/scale.css';

body {
  margin: 0;
  font-family: system-ui, -apple-system, sans-serif;
  background-color: var(--color-bg-base);
  color: var(--color-text);
}
```

### src/App.tsx（应用入口，包裹 BrowserRouter）

```tsx
import './index.css'
import { BrowserRouter } from 'react-router-dom'
import { [ProductName]App } from '@/flows/[feature-name]/[feature-name]'

function App() {
  return (
    <BrowserRouter>
      <[ProductName]App />
    </BrowserRouter>
  )
}

export default App
```

### App Shell 结构模板（src/flows/[feature-name]/[feature-name].tsx）

```tsx
// =============================================
// [Product Name] — Main Application
// Integrates all [N] flows with [Layout Pattern]
// Scenario: [Scenario Name]
// =============================================

import { Component, useState } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { ThemeStyleProvider } from 'sparkdesign'
import { Flow1_[Name] } from '../flow-1/flow1-[name]'
import { Flow2_[Name] } from '../flow-2/flow2-[name]'
// ... import 所有 flow（此时所有文件已在 Phase B 生成完毕）
import { mock[Data] } from '../shared/mock-data'
import type { [Types] } from '../shared/types'

// ErrorBoundary：捕获 render 错误，避免白屏无信息
class ErrorBoundary extends Component<
  { children: React.ReactNode },
  { hasError: boolean; error: Error | null }
> {
  state = { hasError: false, error: null }
  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error }
  }
  render() {
    if (this.state.hasError) {
      return (
        <div className="p-8 bg-error-bg text-error rounded-md m-4">
          <p className="font-semibold mb-2">页面发生错误</p>
          <pre className="text-sm whitespace-pre-wrap">{String(this.state.error)}</pre>
        </div>
      )
    }
    return this.props.children
  }
}

export function [ProductName]App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [appearance, setAppearance] = useState<'light' | 'dark'>('light')

  return (
    <ThemeStyleProvider
      appearance={appearance}
      theme="mint"
      style="soft"
    >
      <ErrorBoundary>
        {!isAuthenticated ? (
          <Flow_Signup onComplete={() => setIsAuthenticated(true)} />
        ) : (
          <div className="flex h-screen bg-bg-base">
            <main className="flex-1 overflow-auto">
              <Routes>
                <Route path="/" element={<Navigate to="/[flow-1-path]" replace />} />
                <Route path="/[flow-1-path]" element={<Flow1_[Name] ... />} />
                <Route path="/[flow-2-path]" element={<Flow2_[Name] ... />} />
              </Routes>
            </main>
          </div>
        )}
      </ErrorBoundary>
    </ThemeStyleProvider>
  )
}
```

### SetupCheck 验证组件（Phase A 临时生成，验证后可删除）

```tsx
// src/SetupCheck.tsx
import { ThemeStyleProvider, Button, Tag, Progress } from 'sparkdesign'

export function SetupCheck() {
  return (
    <ThemeStyleProvider appearance="light" theme="mint" style="soft">
      <div className="p-8 flex flex-col gap-4 bg-bg-base min-h-screen">
        <h2 className="text-xl font-semibold text-text">Spark Design 环境验证</h2>
        <div className="p-4 bg-bg-highlight rounded-md text-text">
          ✅ 看到浅色背景 + 深色文字 → token 正常
        </div>
        <Button variant="primary">✅ 看到品牌色按钮 → 组件正常</Button>
        <div className="flex gap-2">
          <Tag color="success">✅ 绿色</Tag>
          <Tag color="error">✅ 红色</Tag>
          <Tag color="warning">✅ 橙色</Tag>
        </div>
        <Progress value={75} />
        <p className="text-text-secondary text-sm">
          以上元素均显示正常后，可删除此文件并回复「继续」
        </p>
      </div>
    </ThemeStyleProvider>
  )
}
```
