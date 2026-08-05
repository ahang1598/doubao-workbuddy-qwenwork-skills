# Flow Structure Protocol — Mobile

> **文件用途**：定义 SparkFlow Mobile Skill 中「Flow」的结构规范与 JSX 代码输出协议。
> SKILL.md 在 Step 4 GENERATE 阶段必须读取本文件，确保所有输出格式一致。
> 本协议同时适用于 H5（Ant Design Mobile）和 React Native（Expo + Gluestack UI）两条路径，仅语法细节不同。

---

## 一、Flow 的定义

Flow 是一段**有名称、有起点、有终态**的多屏用户任务序列。

| 要素 | 规则 |
|---|---|
| **名称** | 动词 + 名词，英文首字母大写。例：`Browse & Checkout`、`Send Transfer`、`Complete Lesson` |
| **屏幕数** | 最少 2 屏，最多 6 屏。超过 6 屏必须拆分为两个独立 flow |
| **必含要素** | 入口条件 / 屏幕序列 / 分支规则 / 终态（成功 / 错误 / 放弃） |
| **粒度** | 一个 flow = 一个完整的用户任务。不拆子步骤，不跨任务合并 |

---

## 二、Flow 的解剖结构

```
Flow: [Flow Name]
│
├── Entry Condition          ← 什么操作触发这个 flow？（点击 CTA / 路由跳转 / 系统事件）
│
├── Screen 1: [Screen Name]
│   ├── Primary Action: [用户在此屏的核心操作]
│   ├── Key Components: [组件列表]
│   ├── → Happy Path: Screen 2
│   ├── → Cancel / Back: [返回位置]
│   └── → Error: Screen 1（带错误状态）
│
├── Screen N: [Screen Name]
│   ├── Primary Action: [核心操作]
│   ├── Key Components: [组件列表]
│   └── → [下一步 / 终态]
│
└── Exit State
    ├── ✅ Success: [用户看到什么，发生了什么]
    ├── ❌ Error (unrecoverable): [系统级错误的处理]
    └── ↩ Abandon: [用户中途退出时的保存/提示策略]
```

---

## 三、屏幕数量决策规则

| 任务复杂度 | 屏幕数 | 典型示例 |
|---|---|---|
| 简单操作（单对象 CRUD） | 2–3 屏 | 创建标签、修改个人资料、删除确认 |
| 中等任务（多步骤，单目标） | 3–4 屏 | 发帖、添加联系人、连接账户 |
| 复杂任务（多步骤，多决策点） | 4–6 屏 | 完成结账、订阅 Paywall、转账确认 |
| 超复杂任务 | 拆分 | 拆为 2 个独立 flow，用「前置 flow → 后置 flow」标注关系 |

**判断依据**：如果一个 flow 里有超过 2 个「用户需要做决定的节点」，优先拆分。

---

## 四、代码输出协议

### 4.1 每屏的注释头（强制）

每个屏幕的代码块必须以标准注释头开始，格式固定，不可省略：

```tsx
/* ================================================
   FLOW: [Flow Name]
   SCREEN [N] of [Total]: [Screen Name]
   PLATFORM: [H5 (Ant Design Mobile) | React Native (Expo + Gluestack UI)]
   ------------------------------------------------
   ENTRY:  [上一屏的哪个操作跳转到这里]
   EXIT:   [本屏的主 CTA → 下一屏 / 终态]
   BRANCH: [可选，分支跳转说明]
   ================================================ */
```

**示例（H5）**：

```tsx
/* ================================================
   FLOW: Cart Review & Checkout
   SCREEN 2 of 4: Shipping Address
   PLATFORM: H5 (Ant Design Mobile)
   ------------------------------------------------
   ENTRY:  "前往结账" tapped on Screen 1 (Cart)
   EXIT:   "保存并继续" → Screen 3 (Payment)
   BRANCH: "返回" → Screen 1 (Cart, retain items)
   ================================================ */
```

**示例（React Native）**：

```tsx
/* ================================================
   FLOW: Send Transfer
   SCREEN 2 of 3: Enter Amount
   PLATFORM: React Native (Expo + Gluestack UI)
   ------------------------------------------------
   ENTRY:  Recipient selected on Screen 1
   EXIT:   "下一步" → Screen 3 (Confirm & Biometrics)
   BRANCH: "返回" → Screen 1 (retain recipient)
   ================================================ */
```

### 4.2 屏幕间的跳转注释（强制）

两个屏幕代码块之间，用单行注释标注跳转关系：

```tsx
{/* → User taps "下一步" → SCREEN 2: Enter Amount */}
{/* → User taps "取消" → SCREEN 1: Select Recipient (retain data) */}
```

### 4.3 状态变体注释（必须覆盖）

每个屏幕的关键交互状态需在代码中用注释标注：

```tsx
{/* STATE: default — form empty, submit disabled */}
{/* STATE: filled — form valid, submit enabled */}
{/* STATE: submitting — button loading, inputs disabled */}
{/* STATE: error — inline validation messages shown */}
{/* STATE: empty — no data, Empty component with CTA */}
```

不需要为每个状态写完整代码，但必须在注释中声明状态列表，并实现 default + error 两个状态的代码。

### 4.4 输出结构示例（H5 完整 flow）

```tsx
// =============================================
// FLOW: Browse & Checkout (4 screens)
// Scenario: Mobile Marketplace
// Platform: H5 (Ant Design Mobile)
// =============================================

import { NavBar, List, Button, Form, Input, Toast, Popup,
         SwipeAction, SafeArea, SpinLoading, Empty } from 'antd-mobile'
import { useNavigate } from 'react-router-dom'

/* ================================================
   FLOW: Browse & Checkout
   SCREEN 1 of 4: Product List
   PLATFORM: H5 (Ant Design Mobile)
   ------------------------------------------------
   ENTRY:  App launch → Home Tab → Category selected
   EXIT:   Product card tapped → SCREEN 2: Product Detail
   BRANCH: Search icon → Search page (outside flow)
   ================================================ */
export function Screen1_ProductList() {
  const navigate = useNavigate()
  // STATE: default — grid of products
  // STATE: loading — SpinLoading centered
  // STATE: empty — Empty component + "去逛逛" CTA
  return (
    <div className="screen">
      <NavBar back={null}>女装</NavBar>
      {/* product grid ... */}
      {/* → User taps product card → SCREEN 2: Product Detail */}
    </div>
  )
}

{/* → Product tapped → SCREEN 2: Product Detail */}

/* ================================================
   FLOW: Browse & Checkout
   SCREEN 2 of 4: Product Detail
   ...
   ================================================ */
export function Screen2_ProductDetail() {
  // ...
}
```

### 4.5 输出结构示例（RN 完整 flow）

```tsx
// =============================================
// FLOW: Send Transfer (3 screens)
// Scenario: Mobile Consumer Finance
// Platform: React Native (Expo + Gluestack UI)
// =============================================

import { Box, VStack, HStack, Text, Button, ButtonText,
         Input, InputField, Pressable, Spinner } from '@gluestack-ui/themed'
import { SafeAreaView, FlatList } from 'react-native'
import { useRouter } from 'expo-router'

/* ================================================
   FLOW: Send Transfer
   SCREEN 1 of 3: Select Recipient
   PLATFORM: React Native (Expo + Gluestack UI)
   ------------------------------------------------
   ENTRY:  "转账" button on Home screen
   EXIT:   Recipient selected → SCREEN 2: Enter Amount
   BRANCH: "取消" → Home (stack pop)
   ================================================ */
export function Screen1_SelectRecipient() {
  const router = useRouter()
  // STATE: default — contact list
  // STATE: loading — Spinner centered
  // STATE: empty — Empty state + "添加收款人" CTA
  return (
    <SafeAreaView className="flex-1 bg-white">
      <VStack className="flex-1">
        {/* contact search + list */}
        {/* → Contact tapped → SCREEN 2: Enter Amount */}
      </VStack>
    </SafeAreaView>
  )
}
```

---

## 五、分支表达规范

### 5.1 Happy Path（主路径）

用 `→` 表示，写在注释头的 `EXIT` 行：

```
EXIT: "确认转账" → SCREEN 3: Biometric Confirm
```

### 5.2 Error Branch（错误分支）

错误分支通常回到当前屏，带错误状态：

```
BRANCH: Validation failed → SCREEN 2 (error state, field highlighted)
BRANCH: Network error → SCREEN 2 (Toast error, retry button)
```

### 5.3 Conditional Branch（条件分支）

根据用户选择走不同路径：

```
BRANCH: Guest checkout → SCREEN 3A: Guest Address Form
BRANCH: Logged in → SCREEN 3B: Saved Address Select
```

### 5.4 Bottom Sheet 分支（移动端常见）

部分操作通过底部弹层完成，不触发页面跳转：

```
EXIT: Size chip tapped → Size Selector Popup (within Screen 2)
EXIT: "加入购物车" confirmed in Popup → SCREEN 3: Cart
```

---

## 六、终态规范（Exit State）

每个 flow 必须在最后一屏结束后声明三种终态处理：

### ✅ Success State

- 用户完成任务后看到什么（Toast / 确认页 / 自动跳转）
- 系统发生了什么（数据写入 / 通知发送 / 状态变更）
- 推荐的下一步操作（引导用户继续使用产品）

### ❌ Unrecoverable Error

- 系统级错误（网络断开 / 服务不可用）
- 处理方式：全页错误提示 + 重试 / 联系支持 CTA
- 不应使用：仅 Toast 提示后消失

### ↩ Abandon（用户中途退出）

- 用户点击「返回」/ 关闭底部弹层 / 跳转其他页
- 须明确：数据是否保存为草稿？是否提示「未保存更改」？
- 推荐：超过 2 屏的 flow 保存草稿；2 屏及以下可直接丢弃

---

## 七、DS Coverage Notes（每个 flow 结束后必须输出）

生成完 flow 代码后，在最后添加：

```markdown
## DS Coverage Notes

### Ant Design Mobile Components Used（H5 路径）
| 组件 | 用途 | 备注 |
|---|---|---|
| NavBar | 顶部导航栏 | back prop 控制返回按钮 |
| Popup | 尺码选择底部弹层 | position="bottom" |
| Button | 主 CTA | color="primary" |

### Gluestack UI Components Used（RN 路径）
| 组件 | 用途 | 备注 |
|---|---|---|
| VStack | 垂直布局容器 | — |
| Button | 主 CTA | variant="solid" action="primary" |
| Input | 金额输入 | keyboardType="numeric" |

### Mobile-Specific Patterns Used
| Pattern | 说明 | 平台 |
|---|---|---|
| Bottom Sheet | 尺码/规格选择弹层 | 通用 |
| Pull to Refresh | 列表下拉刷新 | 通用 |
| Swipe to Delete | 左滑删除购物车商品 | 通用 |

### Components Missing from Library
- [ ] SizeSelector：当前用 Popup + Grid 实现，建议封装为业务组件
```

---

## 八、快速检查清单

生成 flow 后，逐项验证：

```
Flow 结构
- [ ] 屏幕数在 2-6 范围内
- [ ] 每屏有标准注释头（FLOW / SCREEN N of M / PLATFORM / ENTRY / EXIT）
- [ ] 屏幕间有跳转注释
- [ ] 有 Happy Path、至少 1 个 Error Branch
- [ ] 定义了三种 Exit State（Success / Error / Abandon）

代码质量（H5）
- [ ] 使用 antd-mobile 组件，无 ad-hoc 样式
- [ ] 颜色 / 间距来自 antd-mobile CSS 变量，无硬编码值
- [ ] NavBar + SafeArea 正确处理安全区
- [ ] 表单有 loading 和 disabled 状态
- [ ] 空状态用 Empty 组件，含 CTA

代码质量（RN）
- [ ] 使用 Gluestack UI + NativeWind，无裸 StyleSheet
- [ ] SafeAreaView 包裹根视图
- [ ] 触摸目标 ≥ 44pt
- [ ] 长列表用 FlatList，不用 ScrollView + map
- [ ] 空状态有 CTA，不只显示文字

输出完整性
- [ ] DS Coverage Notes 已输出
- [ ] 缺失组件已标注
- [ ] Anti-Pattern 检查已执行
```
