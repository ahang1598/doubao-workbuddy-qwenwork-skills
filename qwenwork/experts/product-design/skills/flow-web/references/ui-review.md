# UI 质量审查规范（Web 端）

> **文件用途**：SKILL.md Phase D.3 的检查依据，同时作为 Review Mode 的独立执行手册。
> 职责定位：**质量层**（生成物好不好看、好不好用、可访问性是否达标），与 component-map 的 API 正确性层相互独立，不重叠。
> 适用范围：仅覆盖 Web 端，不含 iOS/Android 原生平台规则。

---

## P1 · CRITICAL — 生成前必须满足

> 以下条目如有违反，直接输出对应 TECH_STACK 的修复代码片段，不可只说"建议修改"。

### P1-1 异步操作按钮有 loading 状态，提交期间 inputs disabled

| 库 | 正确写法 |
|---|---|
| **shadcn** | `<Button disabled={isLoading}>{isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}提交</Button>` |
| **Spark** | `<Button loading={isLoading}>提交</Button>` |
| **antd** | `<Button type="primary" loading={isLoading}>提交</Button>` |

违反征兆：点击按钮后可重复点击、按钮无视觉反馈、表单在提交期间仍可修改。

---

### P1-2 表单错误信息紧邻字段显示，不只是顶部 toast

| 库 | 正确写法 |
|---|---|
| **shadcn** | `<FormMessage />` 组件放在 `<FormField>` 内，紧随 input 之下 |
| **Spark** | `<FieldError>` 手动放置在 `<Field>` 内，紧随 `<FieldInput>` 之下 |
| **antd** | `Form.Item rules` + `validateTrigger="onBlur"` 自动处理，无需额外写 |

违反征兆：错误只在顶部出现 toast 或 Alert，用户不知道哪个字段有问题；提交后表单没有任何 inline 错误标记。

---

### P1-3 空状态有说明文字 + 引导 CTA，不只是空白区域

| 库 | 正确写法 |
|---|---|
| **shadcn** | 自定义 `<div className="flex flex-col items-center gap-3 py-16">` + `<p>暂无数据</p>` + `<Button>新建</Button>` |
| **Spark** | `<Empty><EmptyHeader>[标题]</EmptyHeader><EmptyContent>[描述]</EmptyContent><Button>新建</Button></Empty>` |
| **antd** | `<Empty description="暂无数据"><Button type="primary">新建</Button></Empty>` |

违反征兆：列表、表格、搜索结果区在无数据时只显示一片空白，没有任何引导。

---

### P1-4 图标按钮有 `aria-label`（通用，三库相同）

```tsx
// ❌ 禁止
<Button variant="ghost"><Settings size={16} /></Button>

// ✅ 正确
<Button variant="ghost" aria-label="打开设置"><Settings size={16} /></Button>
```

适用所有纯图标按钮（无文字标签、无 Tooltip 文字补充的场合）。

---

### P1-5 不可逆操作有二次确认 Dialog（通用）

删除、清空、退出工作区、撤销权限等操作必须有 AlertDialog 或 Modal.confirm 二次确认，且：
- 确认按钮使用危险色（`variant="destructive"` / `type="primary" danger` / `variant="error"`）
- Dialog 中明确说明操作后果，不只是"确认继续？"

---

### P1-6 禁用态同时用 opacity + cursor，不只靠颜色区分（通用）

```tsx
// 通用 Tailwind 写法
className={cn("...", isDisabled && "opacity-50 cursor-not-allowed pointer-events-none")}
```

- antd / Spark / shadcn 的 `disabled` prop 已内置，但**自定义禁用状态**必须手动补 class。
- 禁止只用深浅颜色区分禁用态（色盲用户无法识别）。

---

## P2 · HIGH — 交付前必须满足

> 以下条目为 CSS / 概念层检查，无需三库对照。发现违反项，直接写出修复后的 className 或结构调整。

### P2-1 每屏只有 1 个 primary CTA，其他操作视觉降级

- 一屏内 `type="primary"` / `variant="primary"` 的按钮最多 1 个
- 次级操作使用 `secondary` / `default` / `outline` / `ghost`
- 违反示例：表格每行都有蓝底"编辑"按钮 → 改为 `type="link"` 或 `variant="ghost"`

---

### P2-2 导航 active 状态清晰可见，不只靠颜色区分

active 导航项必须至少满足以下之一：
- 文字加粗（`font-semibold` 或 `font-medium` 区别于未激活）
- 左侧或底部指示条（`border-l-2 border-primary` 或 `border-b-2`）
- 背景色变化（配合以上任意一项使用）

单纯颜色变化（如蓝字 vs 灰字）不足以满足可访问性要求。

---

### P2-3 内容区有 `max-w` 限制，避免超宽屏内容过散

```tsx
// 主内容区
<main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">

// 表单、文章等可读性要求高的内容
<div className="max-w-2xl">
```

- Dashboard / 管理后台：`max-w-7xl`
- 表单 / 详情页：`max-w-2xl` 或 `max-w-3xl`
- 文章 / 文档：`max-w-prose`（约 65 字符/行）

---

### P2-4 Table 在窄屏用 `overflow-x-auto` 包裹，不裁切内容

```tsx
<div className="overflow-x-auto rounded-lg border">
  <Table ... />
</div>
```

antd 的 `<Table scroll={{ x: 'max-content' }}` 也可使用，但外层包裹更通用。

---

### P2-5 覆层（Modal / Drawer）在移动端全宽或适配底部抽屉

- Modal：移动端宽度应接近 100%，避免出现两侧滚动条
  ```tsx
  // antd
  <Modal style={{ top: 'auto' }} className="sm:max-w-lg">
  // shadcn DialogContent 默认已适配，确认没有写死宽度
  ```
- Drawer：移动端从底部滑出，宽度 100%（`placement="bottom"` 或 CSS `@media` 切换）

---

### P2-6 数据加载 > 300ms 有 Skeleton 占位，不是空白页

| 场景 | 占位方式 |
|---|---|
| 表格首次加载 | `<Skeleton>` 行占位 × 5–8 行 |
| 统计卡片 | `<Skeleton className="h-24 w-full rounded-lg">` |
| 详情页 | Skeleton 段落占位（`<Skeleton className="h-4 w-3/4">` 多行） |
| 全页跳转 | `<Spin>` / 路由级 `<Suspense fallback={<PageSkeleton />}>` |

违反征兆：数据加载时页面空白超过 300ms，或出现内容"跳入"的布局偏移（CLS）。

---

### P2-7 正文行高 ≥ 1.5，描述段落必须显式设置

长篇正文（描述字段、说明段落、备注 Textarea 内容）必须有行高设置；UI 标签/标题不受此约束。

```tsx
// ❌ 缺失（浏览器默认行高约 1.2，阅读体验差）
<p className="text-sm text-text-secondary">{description}</p>

// ✅ 正确
<p className="text-sm text-text-secondary leading-relaxed">{description}</p>
// leading-relaxed = 1.625；leading-normal = 1.5（最低要求）
```

---

### P2-8 数字列使用 `tabular-nums`，防止数字宽度跳动

适用场景：价格列、数量列、时间戳、统计卡片数字。

```tsx
// ❌ 缺失（数字位数变化时列宽抖动）
<td>{row.amount}</td>
<p className="text-2xl font-bold">{stats.total}</p>

// ✅ 正确
<td className="tabular-nums">{row.amount}</td>
<p className="text-2xl font-bold tabular-nums">{stats.total}</p>
```

antd `<Statistic>` 和数字列均需显式添加 `className="tabular-nums"`。

---

## P3 · MEDIUM — 建议满足（以清单形式呈现，用户自行决定）

```
[ ] 覆层（Modal/Drawer）出现和消失有过渡动画
    antd 和 shadcn 默认已有，Spark 需确认 ThemeStyleProvider 的 transition 配置。
    如无：可用 Tailwind CSS animate-in / animate-out 或 framer-motion。

[ ] 列表项删除有退出动画，不是瞬间消失
    推荐：删除时先触发 opacity-0 + scale-95 过渡（150ms），然后从 DOM 移除。
    antd 的 Table 内置无此效果，需手动用 CSS transition 实现。

[ ] 标题层级顺序，不跨级
    h1 → h2 → h3，不允许从 h1 跳到 h3。
    屏幕内只有 1 个 h1（页面主标题）。

[ ] 图片有 alt 属性（有意义的图片写描述，装饰性图片写 alt=""）
    用户头像：alt={user.name}
    产品图：alt={product.title}
    背景装饰图：alt=""
```

---

## 使用说明

### Phase D.3 执行方式（由 SKILL.md 调用）

1. 逐条过 P1（6 条）：有违反 → 输出修复代码片段
2. 逐条过 P2（8 条）：有违反 → 输出修复 className 或结构调整
3. 以清单形式列出 P3（4 条）：每条标注当前生成物是否满足（✅ / ⬜）

### Review Mode 执行方式（独立 Review 请求）

1. 请用户提供待审查的代码或描述当前页面功能
2. 读取本文件
3. 按 P1 → P2 → P3 顺序扫描
4. 输出完整问题清单：
   ```
   ## UI 审查报告

   ### P1 违反项（必须修复）
   - [P1-X] [问题描述]
     修复：[对应 TECH_STACK 的代码片段]

   ### P2 违反项（建议修复）
   - [P2-X] [问题描述]
     修复：[className 或结构]

   ### P3 建议清单
   - [ ] [P3-X] ⬜ 未满足 / ✅ 已满足
   ```
