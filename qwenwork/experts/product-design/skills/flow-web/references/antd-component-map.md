# Ant Design Component Map

> **文件用途**：定义 Spark Design Flow Skills 中可使用的 Ant Design 组件清单，说明各组件的适用场景、Props 规范，以及组件间的常用组合模式。
> SKILL.md 在 Step 4 GENERATE 阶段参考本文件，确保组件选用有规范依据。

---

## ⚡ 高频运行时错误速查（代码生成前必读）

| 错误现象 | 根因 | 修复方式 |
|---|---|---|
| Table 报 key Warning | `dataSource` 无 `key` 字段，或 `rowKey` 指向不存在的字段 | `rowKey={(record) => record.userId}` 或确保每条数据有唯一 `key` |
| Form.Item 校验不触发 | `Form.Item name` 绑定的同时，Input 又手动绑了 `value`/`onChange` 造成双重受控冲突 | 移除 Input 上的受控 props，让 Form 接管数据流 |
| Modal 关闭后表单数据残留 | `destroyOnClose` 默认 `false`，关闭后组件未卸载 | `<Modal destroyOnClose>` 或在 `onCancel` 里调用 `form.resetFields()` |
| Drawer + Form 提交后 loading 不消失 | 异步操作无 `finally` 块，loading 只在成功时重置 | 所有异步操作必须在 `finally` 里调用 `setLoading(false)` |
| antd 与 Tailwind preflight 冲突（Button padding 异常） | Tailwind preflight CSS reset 覆盖了 antd 的基础样式 | 见第十节（antd-setup.md）的共存方案 |

---

## 一、组件使用原则

1. **统一从 `antd` import**。所有 Ant Design 组件来自 `npm install antd`，格式：`import { Button, Table } from 'antd'`
2. **图标统一用 `lucide-react`**，不安装 `@ant-design/icons`，避免额外依赖。
3. **主题通过 `ConfigProvider` 管理**，不手动操作 DOM class 或 CSS 变量。
4. **表单必须用 `Form` + `Form.Item`**，不自行实现 state 校验逻辑。
5. **布局用 antd `Layout` 组件**，不用纯 div 手写 sidebar。
6. **组合有规则**。常见的 2–3 个组件组合在第三节统一定义，不自行发明组合。

---

## 二、组件清单（按功能分类）

所有组件 import 格式：

```tsx
import { Button, Table, Form, Modal, Drawer, Layout, Menu, /* ... */ } from 'antd'
```

### 2.1 基础操作

| 组件名 | 核心 Props | 适用场景 |
|---|---|---|
| `Button` | `type="primary\|default\|dashed\|text\|link"`, `danger`, `loading`, `disabled`, `size` | 所有可点击操作 |
| `Switch` | `checked`, `onChange`, `disabled`, `loading` | 开关类设置（即时生效） |
| `Dropdown` | `menu={{ items }}`, `trigger` | 操作菜单、头像下拉菜单 |

**Button type 说明：**

| type | 用途 |
|---|---|
| `primary` | 主操作（提交、确认、保存） |
| `default` | 次操作（取消、返回） |
| `dashed` | 虚线按钮（新增占位项） |
| `text` | 文字按钮（工具栏图标按钮、行内操作） |
| `link` | 链接样式（跳转类操作） |
| `danger` + 任意 type | 危险操作（删除、清空），与 type 叠加使用 |

---

### 2.2 数据展示

| 组件名 | 核心 Props | 适用场景 | 不适用场景 |
|---|---|---|---|
| `Table` | `columns`, `dataSource`, `rowKey`, `pagination`, `loading`, `rowSelection` | 结构化数据列表（用户、订单、日志等） | 行数超 50 须配 pagination |
| `Tag` | `color="success\|error\|warning\|processing\|default"` | 状态标签、分类标记 | 计数角标（用 Badge） |
| `Badge` | `count`, `dot`, `status` | 计数角标、状态圆点 | 状态标签（用 Tag） |
| `Avatar` | `src`, `size`, `shape` | 用户头像，支持 fallback 到首字母 | logo、图标 |
| `Progress` | `percent`, `status`, `type` | 任务进度、文件上传进度 | 数据占比（用图表） |
| `Tooltip` | `title`, `placement` | 图标按钮说明、截断文本完整内容 | 错误提示 |
| `Skeleton` | `active`, `paragraph`, `avatar` | 数据加载中的占位 | 全页加载（用 Spin） |
| `Spin` | `spinning`, `size` | 全局 / 区块加载遮罩 | 局部数据加载（用 Skeleton） |
| `Statistic` | `title`, `value`, `prefix`, `suffix` | 数字统计卡（KPI、概览数据） | 普通文本展示 |
| `Empty` | `description`, `image` | 空状态展示，需配合 CTA Button | 不可只展示文字 |
| `Collapse` | `items`, `defaultActiveKey` | 可折叠内容（FAQ、高级筛选、日志详情） | — |

**Tag color 说明：**

| color | 用途 |
|---|---|
| `success` | 成功 / 启用 / 已完成 |
| `error` | 错误 / 失败 / 禁用 |
| `warning` | 警告 / 待处理 |
| `processing` | 进行中 / 同步中（带动画） |
| `default` | 中性标签 / 分类 |

---

### 2.3 表单与输入

| 组件名 | 适用场景 | 必须配合使用 |
|---|---|---|
| `Form` | 所有表单容器，处理校验逻辑 | 配合 `Form.useForm()` |
| `Form.Item` | 单个字段包裹，绑定 `name` + `rules` | 必须在 `Form` 内使用 |
| `Input` | 单行文本、邮箱 | 在 `Form.Item` 内使用 |
| `Input.Password` | 密码输入，自带显/隐切换 | 在 `Form.Item` 内使用 |
| `Input.TextArea` | 多行文本、描述、备注 | 在 `Form.Item` 内使用 |
| `InputNumber` | 数字输入，带步进控制 | 在 `Form.Item` 内使用 |
| `Select` | 单选 / 多选下拉（选项 ≤ 50 个） | 在 `Form.Item` 内使用 |
| `Checkbox` | 多选项、同意条款 | — |
| `Checkbox.Group` | 成组多选 | — |
| `Radio.Group` | 互斥单选（选项 ≤ 6 个） | 超过 6 个改用 `Select` |
| `DatePicker` | 日期选择 | — |
| `DatePicker.RangePicker` | 日期范围选择 | — |
| `Upload` | 文件上传，支持拖拽 | — |
| `Slider` | 范围选择（价格区间、进度） | — |

---

### 2.4 布局与导航

| 组件名 | 适用场景 | 备注 |
|---|---|---|
| `Layout` | 页面整体骨架容器 | 与 `Sider`、`Header`、`Content` 组合使用 |
| `Layout.Sider` | 侧边栏，B2B 后台一级导航 | `theme="light"` 亮色 / `theme="dark"` 暗色 |
| `Layout.Header` | 顶部导航栏 | Top Nav 导航模式使用 |
| `Layout.Content` | 主内容区 | — |
| `Menu` | 导航菜单，支持多级 | 配合 `Sider` 或 `Header` 使用 |
| `Tabs` | 同一页面内的内容切换 | 最多 6 个 tab，超出用 Select |
| `Breadcrumb` | 3 级及以上页面层级路径指示 | — |
| `Pagination` | 超过 20 条数据的列表分页 | 通常内置在 `Table` 的 `pagination` prop 中 |
| `Steps` | 分步向导步骤指示器 | 配合多屏 flow 的进度展示 |
| `Divider` | 内容区块视觉分隔 | — |

---

### 2.5 覆盖层与反馈

| 组件名 | 适用场景 | 不适用场景 |
|---|---|---|
| `Modal` | 需确认的操作、信息量 ≤ 1 表单的创建 | 信息量大的复杂表单（用 Drawer） |
| `Modal.confirm` | 不可逆操作的快速二次确认（删除、清空） | 普通信息展示 |
| `Drawer` | 从边缘滑出的详情 / 筛选 / 较长表单面板 | 简单确认（用 Modal） |
| `Popover` | 锚定于触发元素的轻量浮层 | 大量内容 |
| `message` | 操作结果的全局轻提示（顶部居中） | 错误（用 inline 或 Alert） |
| `notification` | 需要标题 + 描述的系统通知（右上角） | 简单操作反馈（用 message） |
| `Alert` | 页面级警告 / 信息横幅 | 操作反馈（用 message） |
| `Result` | 操作完成的全屏反馈页（Success / Error / 403 / 404） | 局部状态反馈 |

---

## 三、常用组件组合（Composition Patterns）

### Pattern A：列表页工具栏（List Toolbar）

```tsx
import { Input, Select, Button, Space } from 'antd'
import { Search, Plus } from 'lucide-react'

// 搜索框在左，筛选 Select 居中，主 CTA 在右
<div className="flex items-center justify-between mb-4">
  <Space>
    <Input
      prefix={<Search size={14} />}
      placeholder="搜索..."
      style={{ width: 240 }}
      allowClear
    />
    <Select placeholder="筛选状态" style={{ width: 160 }} allowClear>
      <Select.Option value="active">启用</Select.Option>
      <Select.Option value="inactive">禁用</Select.Option>
    </Select>
  </Space>
  <Button type="primary" icon={<Plus size={14} />}>新建</Button>
</div>
```

---

### Pattern B：表格行操作（Table Row Actions）

```tsx
import { Button, Dropdown, Modal } from 'antd'
import { MoreHorizontal } from 'lucide-react'

// 操作 ≤ 2 个：直接展示文字按钮
<Button type="link" size="small">编辑</Button>
<Button type="link" danger size="small">删除</Button>

// 操作 ≥ 3 个：收入 Dropdown
const items = [
  { key: 'edit', label: '编辑' },
  { key: 'duplicate', label: '复制' },
  { type: 'divider' },
  { key: 'delete', label: '删除', danger: true },
]

<Dropdown menu={{ items, onClick: ({ key }) => handleAction(key, record) }}>
  <Button type="text" icon={<MoreHorizontal size={16} />} />
</Dropdown>
```

---

### Pattern C：创建 / 编辑表单（Create / Edit Form）

```tsx
import { Modal, Drawer, Form, Input, Select, Button } from 'antd'

const [form] = Form.useForm()

// 字段 ≤ 5 个 → Modal
<Modal
  title="新建成员"
  open={isOpen}
  onCancel={() => { form.resetFields(); setIsOpen(false) }}
  footer={[
    <Button key="cancel" onClick={() => setIsOpen(false)}>取消</Button>,
    <Button key="submit" type="primary" loading={isLoading} onClick={() => form.submit()}>
      确认
    </Button>,
  ]}
>
  <Form form={form} layout="vertical" onFinish={handleSubmit}>
    <Form.Item label="邮箱" name="email" rules={[{ required: true }, { type: 'email' }]}>
      <Input placeholder="you@example.com" />
    </Form.Item>
    <Form.Item label="角色" name="role" rules={[{ required: true }]}>
      <Select>
        <Select.Option value="admin">Admin</Select.Option>
        <Select.Option value="member">Member</Select.Option>
      </Select>
    </Form.Item>
  </Form>
</Modal>

// 字段 > 5 个 → Drawer
<Drawer
  title="编辑资源"
  open={isOpen}
  onClose={() => setIsOpen(false)}
  width={480}
  footer={
    <div className="flex justify-end gap-2">
      <Button onClick={() => setIsOpen(false)}>取消</Button>
      <Button type="primary" loading={isLoading} onClick={() => form.submit()}>保存</Button>
    </div>
  }
>
  <Form form={form} layout="vertical" onFinish={handleSubmit}>
    {/* 多字段 */}
  </Form>
</Drawer>
```

---

### Pattern D：详情页头部（Detail Page Header）

```tsx
import { Breadcrumb, Avatar, Tag, Button, Space } from 'antd'

<>
  <Breadcrumb items={[{ title: '成员管理' }, { title: '张三' }]} className="mb-4" />
  <div className="flex items-center justify-between">
    <Space size="middle">
      <Avatar size={48} src={user.avatar}>{user.initials}</Avatar>
      <div>
        <div className="font-semibold text-base">{user.name}</div>
        <Tag color="success">启用</Tag>
      </div>
    </Space>
    <Space>
      <Button>编辑</Button>
      <Button danger>删除</Button>
    </Space>
  </div>
</>
```

---

### Pattern E：空状态（Empty State）

```tsx
import { Empty, Button } from 'antd'
import { Plus } from 'lucide-react'

// 空状态必须有 CTA，不允许只显示「暂无数据」
<div className="flex flex-col items-center justify-center py-16">
  <Empty description="暂无成员">
    <Button type="primary" icon={<Plus size={14} />} onClick={() => setIsOpen(true)}>
      邀请成员
    </Button>
  </Empty>
</div>
```

---

### Pattern F：分步向导（Step Wizard）

```tsx
import { Steps, Button, Form } from 'antd'

// Steps 组件作为顶部步骤指示器
<Steps
  current={currentStep}
  items={[
    { title: '基本信息' },
    { title: '权限配置' },
    { title: '确认提交' },
  ]}
  className="mb-8"
/>

{/* Screen 1–N：每屏底部 */}
<div className="flex justify-between mt-6">
  {currentStep > 0 && (
    <Button onClick={() => setCurrentStep(s => s - 1)}>上一步</Button>
  )}
  <Button
    type="primary"
    onClick={currentStep < total - 1
      ? () => setCurrentStep(s => s + 1)
      : handleSubmit
    }
  >
    {currentStep < total - 1 ? '下一步' : '提交'}
  </Button>
</div>
```

---

### Pattern G：侧边栏布局（Sidebar Layout）

```tsx
import { Layout, Menu } from 'antd'
import { BarChart2, Users, Settings } from 'lucide-react'

const { Sider, Content } = Layout

<Layout style={{ minHeight: '100vh' }}>
  <Sider width={240} theme="light">
    <div className="p-4 font-semibold text-base border-b">[产品名]</div>
    <Menu
      mode="inline"
      theme="light"
      selectedKeys={[activeKey]}
      items={[
        { key: 'dashboard', icon: <BarChart2 size={16} />, label: '概览' },
        { key: 'members', icon: <Users size={16} />, label: '成员管理' },
        { key: 'settings', icon: <Settings size={16} />, label: '设置' },
      ]}
      onClick={({ key }) => setActiveKey(key)}
    />
  </Sider>
  <Content className="p-6 overflow-auto bg-gray-50">
    {/* 页面内容 */}
  </Content>
</Layout>
```

---

## 四、场景 × 核心组件矩阵

| 场景 | 必用组件 | 常用组合 Pattern |
|---|---|---|
| SaaS 管理后台 | Layout+Sider+Menu, Table, Modal, Drawer, Tag, Form | A + B + C + G |
| AI 产品 | Input.TextArea, Button, Collapse, Tooltip, Spin | — |
| 营销网站 | Button, Card（自定义）, Divider, Collapse | — |
| 数据分析 / BI | Tabs, Statistic, Select, DatePicker.RangePicker, Skeleton | — |
| 电商 | Tag, Button, Drawer（购物车）, Modal.confirm | — |
| 开发者工具 | Tabs, Layout+Sider, message, Tag, Steps | A + G |
| 内部运营工具 | Table, Tag, Modal.confirm, Drawer, Steps | B + D + F |
| 金融科技 | Table, Modal.confirm, Tag, InputNumber, Steps | B + D |
| 社区 / 社交 | Avatar, Button, Input.TextArea, Dropdown | — |
| 医疗健康 | DatePicker, Form, Tag, Modal.confirm, Steps | C + F |
| 教育科技 | Progress, Tabs, Tag, Collapse, Steps | — |

---

## 五、禁止行为

- **不用 `div` 模拟组件**。需要按钮必须用 `Button`，不用 `<div onClick>`
- **不跳过 `Form` 直接用 `useState` 管理表单**。所有表单必须用 `Form` + `Form.Item` + `rules`
- **不用 `Table` 手写 `<tr>`/`<td>`**。必须用 `columns` 数据驱动模式
- **不省略空状态**。每个列表 / 数据区域必须有 `Empty` 组件（含 CTA）
- **不省略 Loading 状态**。按钮提交时必须有 `loading` prop，数据加载时必须有 `Skeleton` 或 `Spin`
- **不混用 Spark token 类或 shadcn 语义类**（`bg-bg-base`、`bg-background` 等）
- **不安装 `@ant-design/icons`**，统一使用 `lucide-react`
- **`message` / `notification` 不用于错误**。表单错误用 `Form.Item` inline 提示，系统错误用 `Alert`
- **不用 `Modal` 做复杂长表单**。字段 > 5 个改用 `Drawer`

---

### Pattern D：Table 高级模式

#### D-1：行选择 + 批量操作（Row Selection + Bulk Actions）

```tsx
import { Table, Button, Space, Popconfirm } from 'antd'
import { Trash2 } from 'lucide-react'

const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([])

const rowSelection = {
  selectedRowKeys,
  onChange: (keys: React.Key[]) => setSelectedRowKeys(keys),
}

<>
  {/* 批量操作栏：有选中行时出现 */}
  {selectedRowKeys.length > 0 && (
    <div className="flex items-center gap-3 mb-3 p-2 bg-blue-50 rounded-lg">
      <span className="text-sm text-blue-700">已选 {selectedRowKeys.length} 项</span>
      <Popconfirm
        title={`确认删除选中的 ${selectedRowKeys.length} 项？`}
        onConfirm={() => { handleBulkDelete(selectedRowKeys); setSelectedRowKeys([]) }}
        okText="删除"
        okButtonProps={{ danger: true }}
      >
        <Button size="small" danger icon={<Trash2 size={14} />}>批量删除</Button>
      </Popconfirm>
      <Button size="small" onClick={() => setSelectedRowKeys([])}>取消</Button>
    </div>
  )}
  <Table
    rowSelection={rowSelection}
    columns={columns}
    dataSource={data}
    rowKey="id"
  />
</>
```

#### D-2：可展开行（Expandable Row）

```tsx
// 用于行内详情预览，避免打开 Drawer 的开销
<Table
  expandable={{
    expandedRowRender: (record) => (
      <div className="py-3 px-4 bg-gray-50 rounded">
        <p className="text-sm text-gray-600">{record.description}</p>
        <div className="flex gap-4 mt-2 text-sm">
          <span>创建时间：{record.createdAt}</span>
          <span>最后修改：{record.updatedAt}</span>
        </div>
      </div>
    ),
    rowExpandable: (record) => !!record.description,
  }}
  columns={columns}
  dataSource={data}
  rowKey="id"
/>
```

#### D-3：列内联编辑（Inline Cell Editing）

```tsx
// 点击行进入编辑模式，保存/取消按钮出现在行内
const [editingKey, setEditingKey] = useState<string>('')
const [form] = Form.useForm()

const isEditing = (record: DataType) => record.id === editingKey

const edit = (record: DataType) => {
  form.setFieldsValue({ name: record.name, role: record.role })
  setEditingKey(record.id)
}

const save = async (id: string) => {
  const values = await form.validateFields()
  // 调用 API 保存...
  setEditingKey('')
}

const editableColumns = [
  {
    title: '名称',
    dataIndex: 'name',
    render: (_: string, record: DataType) =>
      isEditing(record) ? (
        <Form.Item name="name" style={{ margin: 0 }} rules={[{ required: true }]}>
          <Input size="small" />
        </Form.Item>
      ) : record.name,
  },
  {
    title: '操作',
    render: (_: unknown, record: DataType) =>
      isEditing(record) ? (
        <Space size="small">
          <Button type="link" size="small" onClick={() => save(record.id)}>保存</Button>
          <Button type="link" size="small" onClick={() => setEditingKey('')}>取消</Button>
        </Space>
      ) : (
        <Button type="link" size="small" disabled={editingKey !== ''} onClick={() => edit(record)}>
          编辑
        </Button>
      ),
  },
]

<Form form={form} component={false}>
  <Table columns={editableColumns} dataSource={data} rowKey="id" />
</Form>
```

---

### Pattern E：Form 高级模式

#### E-1：动态增删字段（Form.List）

```tsx
import { Form, Input, Button, Space } from 'antd'
import { Plus, Trash2 } from 'lucide-react'

<Form.List name="emails">
  {(fields, { add, remove }) => (
    <>
      {fields.map(({ key, name, ...restField }) => (
        <Space key={key} className="flex mb-2" align="baseline">
          <Form.Item
            {...restField}
            name={[name, 'email']}
            rules={[{ required: true, type: 'email', message: '请输入正确邮箱' }]}
          >
            <Input placeholder="邮箱地址" style={{ width: 280 }} />
          </Form.Item>
          <Form.Item
            {...restField}
            name={[name, 'role']}
            rules={[{ required: true }]}
          >
            <Select placeholder="选择角色" style={{ width: 120 }}>
              <Select.Option value="admin">Admin</Select.Option>
              <Select.Option value="member">Member</Select.Option>
            </Select>
          </Form.Item>
          <Button
            type="text"
            danger
            icon={<Trash2 size={14} />}
            onClick={() => remove(name)}
          />
        </Space>
      ))}
      <Button
        type="dashed"
        onClick={() => add()}
        icon={<Plus size={14} />}
        className="w-full"
      >
        添加邮箱
      </Button>
    </>
  )}
</Form.List>
```

#### E-2：字段联动（Form.Item shouldUpdate）

```tsx
// 选择角色后，动态显示对应权限配置项
<Form.Item label="角色" name="role" rules={[{ required: true }]}>
  <Select placeholder="选择角色">
    <Select.Option value="admin">Admin</Select.Option>
    <Select.Option value="member">Member</Select.Option>
    <Select.Option value="viewer">Viewer</Select.Option>
  </Select>
</Form.Item>

{/* shouldUpdate 监听 role 字段变化 */}
<Form.Item shouldUpdate={(prev, cur) => prev.role !== cur.role}>
  {({ getFieldValue }) => {
    const role = getFieldValue('role')
    if (role === 'admin') {
      return (
        <Form.Item name="adminScope" label="管理范围" rules={[{ required: true }]}>
          <Checkbox.Group options={['成员管理', '账单管理', '数据导出']} />
        </Form.Item>
      )
    }
    return null
  }}
</Form.Item>
```
