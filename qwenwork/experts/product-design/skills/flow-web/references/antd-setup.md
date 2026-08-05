# Ant Design 快速通道（Setup Guide）

> **文件用途**：当用户在 Q_tech 选择 Ant Design 时，提供完整的安装、配置和代码生成规范。
> SKILL.md Step 4 Phase A 按本文件执行安装与配置。

---

## 一、Ant Design vs 其他组件库的选择参考

| 维度 | shadcn/ui | Spark Design | Ant Design |
|---|---|---|---|
| 安装方式 | `npx shadcn@latest init` + 按需 add | `npm install sparkdesign` | `npm install antd`（一行） |
| 组件数量 | ~50 个 | Spark DS 范围内 | 60+ 个，覆盖完整企业场景 |
| Table 组件 | 基础，手动渲染列 | 基础 | 功能强大，内置排序/过滤/分页 |
| Form 组件 | react-hook-form 驱动 | 基础 | 内置校验、联动、动态表单 |
| 主题系统 | CSS 变量 + Tailwind | Spark token | Design Token + ConfigProvider |
| 适合场景 | 通用 Web 应用 | Spark DS 项目 | 数据密集型后台、企业内部系统 |

**触发 Ant Design 通道的条件**：用户在 Q_tech 选择「Ant Design」，或触发语明确提到「antd」「Ant Design」。

---

## 二、脚手架安装流程

```bash
# 1. 创建 Vite + React + TypeScript 项目
npm create vite@latest [project-name] -- --template react-ts
cd [project-name]

# 2. 安装 Ant Design 和路由、图标
npm install antd react-router-dom lucide-react
```

**antd v5 开箱即用**：无需额外配置 CSS，antd v5 采用 CSS-in-JS，样式自动注入，无需手动引入任何样式文件。

---

## 三、Vite 配置

```ts
// vite.config.ts（无需特殊配置，保留 Vite 默认即可）
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

同时更新 `tsconfig.json` 添加路径别名：

```json
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  }
}
```

---

## 四、主题系统

antd v5 通过 `ConfigProvider` 管理主题，支持亮/暗色模式和 Design Token 定制。

### 基础用法

```tsx
import { ConfigProvider, theme } from 'antd'

// 亮色模式（默认）
<ConfigProvider>
  <App />
</ConfigProvider>

// 暗色模式
<ConfigProvider theme={{ algorithm: theme.darkAlgorithm }}>
  <App />
</ConfigProvider>
```

### 动态切换亮/暗色

```tsx
import { useState } from 'react'
import { ConfigProvider, theme } from 'antd'

export function AppRoot() {
  const [isDark, setIsDark] = useState(false)

  return (
    <ConfigProvider
      theme={{
        algorithm: isDark ? theme.darkAlgorithm : theme.defaultAlgorithm,
        token: {
          colorPrimary: '#6366f1',  // 自定义主色（可选）
          borderRadius: 6,
        },
      }}
    >
      {/* 所有应用内容 */}
    </ConfigProvider>
  )
}
```

### ConfigProvider Token 常用定制

| Token | 说明 | 示例值 |
|---|---|---|
| `colorPrimary` | 主色 | `'#6366f1'` |
| `colorSuccess` | 成功色 | `'#22c55e'` |
| `colorError` | 错误色 | `'#ef4444'` |
| `colorWarning` | 警告色 | `'#f59e0b'` |
| `borderRadius` | 基础圆角（px） | `6` |
| `fontSize` | 基础字号（px） | `14` |

---

## 五、组件 import 规范

所有 antd 组件从 `antd` 统一 import，**不需要**单独引入样式文件：

```tsx
// 基础操作
import { Button, Switch } from 'antd'

// 数据展示
import { Table, Tag, Badge, Progress, Tooltip, Avatar } from 'antd'

// 表单输入
import { Form, Input, Select, Checkbox, Radio, DatePicker, InputNumber, Switch, Upload } from 'antd'

// 布局导航
import { Layout, Menu, Tabs, Breadcrumb, Pagination, Steps } from 'antd'
const { Header, Sider, Content, Footer } = Layout

// 覆盖层反馈
import { Modal, Drawer, Popover, Dropdown, message, notification, Alert, Spin, Skeleton } from 'antd'

// 图标（来自 lucide-react，不用 @ant-design/icons）
import { Settings, Users, BarChart2, Plus, Search, Moon, Sun } from 'lucide-react'
```

> **注意**：图标统一使用 `lucide-react`，而非 `@ant-design/icons`，避免额外安装依赖。

---

## 六、核心组件用法模式

### Button

```tsx
<Button type="primary">主要操作</Button>
<Button>次要操作</Button>
<Button type="text">文字按钮</Button>
<Button type="primary" danger>危险操作</Button>
<Button type="primary" loading={isLoading}>提交</Button>
<Button type="primary" disabled>禁用</Button>
```

### Form（antd 内置校验）

```tsx
import { Form, Input, Button } from 'antd'

const [form] = Form.useForm()

<Form
  form={form}
  layout="vertical"
  onFinish={(values) => console.log(values)}
>
  <Form.Item
    label="邮箱"
    name="email"
    rules={[
      { required: true, message: '请输入邮箱' },
      { type: 'email', message: '邮箱格式不正确' },
    ]}
  >
    <Input placeholder="you@example.com" />
  </Form.Item>
  <Form.Item>
    <Button type="primary" htmlType="submit">提交</Button>
  </Form.Item>
</Form>
```

### Table（数据驱动）

```tsx
import { Table, Tag } from 'antd'
import type { ColumnsType } from 'antd/es/table'

interface DataType {
  key: string
  name: string
  status: 'active' | 'inactive'
}

const columns: ColumnsType<DataType> = [
  {
    title: '名称',
    dataIndex: 'name',
    sorter: (a, b) => a.name.localeCompare(b.name),
  },
  {
    title: '状态',
    dataIndex: 'status',
    render: (status) => (
      <Tag color={status === 'active' ? 'success' : 'default'}>
        {status === 'active' ? '启用' : '禁用'}
      </Tag>
    ),
  },
]

<Table
  columns={columns}
  dataSource={data}
  rowKey="key"
  pagination={{ pageSize: 10 }}
/>
```

### Modal / Drawer

```tsx
// Modal
import { Modal } from 'antd'

<Modal
  title="确认删除"
  open={isOpen}
  onOk={handleConfirm}
  onCancel={() => setIsOpen(false)}
  okText="确认"
  cancelText="取消"
  okButtonProps={{ danger: true }}
>
  <p>此操作不可撤销，确认继续？</p>
</Modal>

// Drawer（侧滑面板，适合编辑表单）
import { Drawer } from 'antd'

<Drawer
  title="编辑资源"
  open={isOpen}
  onClose={() => setIsOpen(false)}
  width={480}
  footer={
    <div className="flex justify-end gap-2">
      <Button onClick={() => setIsOpen(false)}>取消</Button>
      <Button type="primary" onClick={handleSave}>保存</Button>
    </div>
  }
>
  {/* 表单内容 */}
</Drawer>
```

### Layout（Sidebar 导航模式）

```tsx
import { Layout, Menu } from 'antd'
const { Header, Sider, Content } = Layout

<Layout style={{ minHeight: '100vh' }}>
  <Sider width={240} theme="light">
    <div className="p-4 font-semibold text-base">产品名称</div>
    <Menu
      mode="inline"
      selectedKeys={[activeKey]}
      items={[
        { key: 'dashboard', label: '概览', icon: <BarChart2 size={16} /> },
        { key: 'members', label: '成员管理', icon: <Users size={16} /> },
      ]}
      onClick={({ key }) => setActiveKey(key)}
    />
  </Sider>
  <Layout>
    <Content className="p-6">
      {/* 页面内容 */}
    </Content>
  </Layout>
</Layout>
```

---

## 七、App Shell 模板（Ant Design 版）

```tsx
// src/flows/[feature-name]/[feature-name].tsx
import { useState } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { ConfigProvider, Layout, Menu, Button, theme } from 'antd'
import { Moon, Sun, BarChart2, Users, Settings } from 'lucide-react'
import { Flow1_[Name] } from '../flow-1/flow1-[name]'
import { Flow2_[Name] } from '../flow-2/flow2-[name]'

const { Sider, Content } = Layout

export function [ProductName]App() {
  const [isDark, setIsDark] = useState(false)
  const [activeKey, setActiveKey] = useState('flow1')
  const [isAuthenticated, setIsAuthenticated] = useState(false)

  if (!isAuthenticated) {
    return <Flow_Signup onComplete={() => setIsAuthenticated(true)} />
  }

  return (
    <ConfigProvider
      theme={{
        algorithm: isDark ? theme.darkAlgorithm : theme.defaultAlgorithm,
      }}
    >
      <Layout style={{ minHeight: '100vh' }}>
        <Sider width={240} theme={isDark ? 'dark' : 'light'}>
          <div className="p-4 font-semibold text-base">[产品名]</div>
          <Menu
            mode="inline"
            theme={isDark ? 'dark' : 'light'}
            selectedKeys={[activeKey]}
            items={[
              { key: 'flow1', label: '[Flow 1 名称]', icon: <BarChart2 size={16} /> },
              { key: 'flow2', label: '[Flow 2 名称]', icon: <Users size={16} /> },
            ]}
            onClick={({ key }) => setActiveKey(key)}
          />
          <div className="absolute bottom-4 left-4">
            <Button
              type="text"
              icon={isDark ? <Sun size={16} /> : <Moon size={16} />}
              onClick={() => setIsDark(d => !d)}
            />
          </div>
        </Sider>
        <Content className="p-6 overflow-auto">
          {activeKey === 'flow1' && <Flow1_[Name] />}
          {activeKey === 'flow2' && <Flow2_[Name] />}
        </Content>
      </Layout>
    </ConfigProvider>
  )
}
```

---

## 八、技术约束清单

生成代码时，Ant Design 路径下的强制规范：

```
- [ ] 组件 import 来自 'antd'，图标来自 'lucide-react'
- [ ] 主题通过 ConfigProvider + theme.darkAlgorithm 管理，不手动操作 DOM class
- [ ] 表单使用 Form + Form.Item + rules 校验，不用 react-hook-form
- [ ] Table 使用 columns 数据驱动模式，不手动渲染 <tr>/<td>
- [ ] 侧边栏布局使用 Layout + Sider + Menu，不手写 nav
- [ ] 不使用 Spark token 类（bg-bg-base、text-text 等）
- [ ] 不使用 shadcn 语义类（bg-background、text-foreground 等）
- [ ] 避免安装 @ant-design/icons，统一用 lucide-react
```

---

## 九、常见问题 FAQ

**Q: antd v5 需要引入样式文件吗？**
A: 不需要。antd v5 采用 CSS-in-JS，样式随组件自动注入，无需 `import 'antd/dist/reset.css'`（v4 才需要）。

**Q: antd 和 Tailwind CSS 可以共用吗？**
A: 可以，但注意 antd 的 reset 样式可能和 Tailwind 的 preflight 有冲突。建议在 `src/index.css` 加 `@layer base` 隔离，或不使用 Tailwind preflight。若只用 Tailwind 做间距/布局辅助（`p-4`、`flex`、`gap-3`），冲突较少。

**Q: antd Table 分页怎么配置？**
A: `<Table pagination={{ pageSize: 10, showSizeChanger: true, showTotal: (total) => \`共 ${total} 条\` }} />`

**Q: message 和 notification 怎么用？**
A: antd v5 推荐在组件内使用 `App.useApp()` 获取实例，或在顶层用静态方法 `message.success('操作成功')`。Flow 原型中可直接用静态方法。

---

## 十、antd + Tailwind CSS 共存规范

antd v5（CSS-in-JS）与 Tailwind CSS 可以共用，但 Tailwind 的 `preflight` reset 会覆盖 antd 的部分基础样式，导致 Button padding 异常、输入框边框消失等问题。选择以下方案之一解决：

### 方案 A（推荐）：关闭 Tailwind preflight，只用工具类

适合：只用 Tailwind 的 flex/grid/spacing 工具类，不依赖 Tailwind 的 `@layer base` 样式重置。

```js
// tailwind.config.js
export default {
  content: ['./src/**/*.{ts,tsx}'],
  corePlugins: {
    preflight: false,  // 关闭 preflight，保留 antd 的基础样式
  },
}
```

关闭 preflight 后，Tailwind 工具类（`p-4`、`flex`、`gap-3`、`max-w-7xl`）正常工作，但 `@layer base` 的全局 reset 不再生效。这对于大多数管理后台场景已足够。

### 方案 B：保留 preflight，手动修复关键冲突

适合：需要完整 Tailwind base reset（处理字体、行高、边距等），同时使用 antd 组件。

```css
/* src/index.css — 在 Tailwind 指令之后添加 */
@import "tailwindcss";

@layer base {
  /* 修复 preflight 导致的 box-sizing 冲突 */
  *,
  ::before,
  ::after {
    box-sizing: border-box;
  }
}
```

同时在 `ConfigProvider` 添加 `hashPriority="high"` 提升 antd CSS-in-JS 优先级：

```tsx
<ConfigProvider hashPriority="high">
  <App />
</ConfigProvider>
```

### 禁止行为

- ❌ 在 antd 组件的 `className` 上混用 Spark token（`bg-bg-base`、`text-text` 等）
- ❌ 在 antd 组件的 `className` 上混用 shadcn 语义类（`bg-background`、`text-foreground` 等）
- ❌ 在 `ConfigProvider` 里覆盖 Tailwind 已处理的样式（产生优先级冲突）
- ❌ 同时安装 `@tailwindcss/base` 和不关闭 preflight — 会产生难以追踪的样式优先级问题
