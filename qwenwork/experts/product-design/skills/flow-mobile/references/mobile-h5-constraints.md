# H5 路径约束（Ant Design Mobile v5）

> 本文件由 SKILL.md Phase B（H5 路径）和 Phase C 引用。

---

## 技术约束

- 使用 antd-mobile 组件，不引入其他 UI 库
- CSS 变量控制主题色（`var(--adm-color-primary)`），不硬编码十六进制颜色
- 间距使用 `8px` / `12px` / `16px` / `24px` 等 4px 倍数
- 图标使用 `antd-mobile-icons` 或内联 SVG，不引入第三方图标库
- 触摸目标最小 44×44px
- 路由使用 `react-router-dom v6`（`<Routes>` + `<Route>`）

---

## B1 — 图标名称（antd-mobile-icons 实际导出为准）

```
常用映射：
- 首页：AppOutline（❌ HomeOutline）
- 购物车：ShopbagOutline（❌ ShoppingCartOutline）
- 搜索：SearchOutline
- 个人中心：UserOutline
- 新增：AddOutline

验证方式：node -e "console.log(Object.keys(require('antd-mobile-icons')))"
```

Phase C App Shell 的 TabBar 图标必须直接引用 Phase B 已输出的「UI 元素→组件映射声明表」，禁止重新猜测图标名称。

---

## B2 — Empty 组件不接受 children

```tsx
// ✅ 正确：CTA 用外层 div 并排放置
<div style={{ textAlign: 'center' }}>
  <Empty description="暂无数据" />
  <Button>去逛逛</Button>
</div>

// ❌ 错误（TS 报错）
<Empty description="暂无数据">
  <Button>去逛逛</Button>
</Empty>
```

---

## B3 — 禁止生成未使用变量

```
- useState 只解构实际用到的值和 setter，不用的 setter 省略：
  const [count] = useState(0)           // ✅
  const [count, setCount] = useState(0) // ❌ 如果 setCount 从未调用
- import 列表只包含当前 flow 实际渲染的组件，禁止预先 import 备用组件
```

---

## D1 — 副作用 Hook 约束

```tsx
// ❌ 错误：useState 不执行副作用，cleanup 永远不调用
useState(() => {
  const timer = setTimeout(() => navigate('/today'), 3200)
  return () => clearTimeout(timer)
})

// ✅ 正确：所有副作用必须在 useEffect 内
useEffect(() => {
  const timer = setTimeout(() => navigate('/today'), 3200)
  return () => clearTimeout(timer)
}, [])
```

---

## 每屏注释头格式

```tsx
/* ================================================
   FLOW: [Flow Name]
   SCREEN [N] of [Total]: [Screen Name]
   PLATFORM: H5 (Ant Design Mobile)
   ------------------------------------------------
   ENTRY:  [上一屏哪个操作跳转到这里]
   EXIT:   [本屏主 CTA → 下一屏名称 / 终态]
   BRANCH: [可选，分支跳转规则]
   ================================================ */
```

---

## 常用组件引用

```tsx
import { NavBar, TabBar, List, Button, Form, Input, Popup,
         Dialog, Toast, SwipeAction, PullToRefresh,
         InfiniteScroll, Image, ImageViewer, Swiper,
         Badge, Empty, SpinLoading, ProgressBar,
         Picker, Stepper, Switch, SearchBar, Selector, CheckList,
         SafeArea } from 'antd-mobile'
import { useNavigate } from 'react-router-dom'
```

---

## 视觉质量规范

```tsx
// 1. 文字层级用 opacity，不用多种颜色
<div style={{ color: 'var(--adm-color-text)' }}>标题</div>
<div style={{ color: 'var(--adm-color-text)', opacity: 0.8 }}>正文</div>
<div style={{ color: 'var(--adm-color-text)', opacity: 0.6 }}>辅助说明</div>

// 2. 价格 / 统计数字加 tabular-nums
<span style={{ fontVariantNumeric: 'tabular-nums', fontWeight: 600 }}>¥1,234.56</span>

// 3. 阴影用品牌色调，不用纯黑
// ❌ 错误
boxShadow: '0 2px 8px rgba(0,0,0,0.15)'
// ✅ 正确
boxShadow: '0 2px 12px rgba(22,119,255,0.10)'

// 4. 已知选项优先用 Selector / CheckList / Radio.Group，不用 Input
// ❌ 错误
<Input placeholder="请输入职位" />
// ✅ 正确
<Selector options={[{ label: '前端', value: 'fe' }]} onChange={setRole} />
```

---

## TabBar 布局铁律（Phase C）

```tsx
// ✅ 正确：flex 列布局，TabBar 天然与内容等宽
<div style={{
  width: '100%', maxWidth: 430, margin: '0 auto',
  height: '100%', minHeight: '100vh',
  display: 'flex', flexDirection: 'column',
}}>
  <div style={{ flex: 1, overflowY: 'auto' }}>
    {renderContent()}
  </div>
  <div style={{ flexShrink: 0 }}>
    <TabBar />
  </div>
</div>

// ❌ 错误（position:fixed，viewport 居中 ≠ 容器居中，必错位）
<TabBar style={{ position: 'fixed', bottom: 0, left: '50%', transform: 'translateX(-50%)' }} />
```

附加规则：
- 嵌入 AppShell 的 Tab 组件**不得声明 `minHeight:100vh`**，由父容器 `flex:1` 统一控制高度
- `App.tsx` 只负责单层 `maxWidth` 容器，AppShell 内不再嵌套 `maxWidth`

---

## C.2-H5 验证流程（Phase C 完成后执行）

```text
执行顺序：
1. npm run dev —— 确认开发模式能启动
2. npx vite build —— 抓取生产构建错误（比浏览器 HMR overlay 更可靠）
   - 若构建报错：优先检查 import 缺失（tslib 未装、图标名拼写错误）
   - 若构建成功但页面白屏：grep "useState(() =>" 检查副作用误用（见 D1）

白屏优先排查顺序：
  Step 1: npx vite build → 看构建报错
  Step 2: 浏览器控制台 Console → 看 JS 运行时报错
  Step 3: grep "useState(() =>" → 检查是否将副作用写入 useState
```
