# Flow Structure Protocol

> **文件用途**：定义 Spark Design Flow Skills 中「Flow」的结构规范与代码输出协议。
> SKILL.md 在 Step 4 GENERATE 阶段必须读取本文件，确保所有输出格式一致。

---

## 一、Flow 的定义

Flow 是一段**有名称、有起点、有终态**的多屏用户任务序列。

| 要素 | 规则 |
|---|---|
| **名称** | 动词 + 名词，英文首字母大写。例：`Create Project`、`Complete Checkout`、`Invite Team Member` |
| **屏幕数** | 最少 2 屏，最多 6 屏。超过 6 屏必须拆分为两个独立 flow |
| **必含要素** | 入口条件 / 屏幕序列 / 分支规则 / 终态（成功 / 错误 / 放弃） |
| **粒度** | 一个 flow = 一个完整的用户任务。不拆子步骤，不跨任务合并 |

---

## 二、Flow 的解剖结构

```
Flow: [Flow Name]
│
├── Entry Condition          ← 什么操作触发这个 flow？（点击 CTA / URL 直达 / 系统事件）
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
| 中等任务（多步骤，单目标） | 3–4 屏 | 创建项目、邀请成员、连接集成 |
| 复杂任务（多步骤，多决策点） | 4–6 屏 | 完成结账、SaaS 注册引导、合同审批 |
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
   ------------------------------------------------
   ENTRY:  [上一屏的哪个操作跳转到这里]
   EXIT:   [本屏的主 CTA → 下一屏 / 终态]
   BRANCH: [可选，分支跳转说明]
   ================================================ */
```

**示例：**

```tsx
/* ================================================
   FLOW: Invite Team Member
   SCREEN 2 of 3: Set Role & Permissions
   ------------------------------------------------
   ENTRY:  Email validated on Screen 1 → "Next" clicked
   EXIT:   "Send Invite" → Screen 3 (Success)
   BRANCH: "Back" → Screen 1 (retain entered email)
   ================================================ */
```

### 4.2 屏幕间的跳转注释（强制）

两个屏幕代码块之间，用单行注释标注跳转关系：

```tsx
{/* → User clicks "Next" → SCREEN 2: Set Role & Permissions */}
```

```tsx
{/* → User clicks "Send Invite" → SCREEN 3: Success Confirmation */}
{/* → User clicks "Back" → SCREEN 1: Enter Email (email retained) */}
```

### 4.3 状态变体注释（必须覆盖）

每个屏幕的关键交互状态需在代码中用注释标注：

```tsx
{/* STATE: default — form empty, submit disabled */}
{/* STATE: filled — form valid, submit enabled */}
{/* STATE: submitting — submit button loading, inputs disabled */}
{/* STATE: error — field-level validation messages shown */}
```

不需要为每个状态写完整代码，但必须在注释中声明状态列表，并实现 default + error 两个状态的代码。

### 4.4 输出结构示例（完整 flow）

```tsx
// =============================================
// FLOW: Create Project (3 screens)
// =============================================

/* ================================================
   FLOW: Create Project
   SCREEN 1 of 3: Basic Info
   ------------------------------------------------
   ENTRY:  "New Project" button on Projects List page
   EXIT:   "Next" → SCREEN 2: Configure Settings
   BRANCH: "Cancel" → Projects List (no changes saved)
   ================================================ */
export function Screen1_BasicInfo() {
  return (
    // ... 组件代码
  )
}

{/* → "Next" clicked with valid form → SCREEN 2: Configure Settings */}

/* ================================================
   FLOW: Create Project
   SCREEN 2 of 3: Configure Settings
   ------------------------------------------------
   ENTRY:  Basic info validated on Screen 1
   EXIT:   "Create Project" → SCREEN 3: Success
   BRANCH: "Back" → SCREEN 1 (retain entered data)
   ================================================ */
export function Screen2_ConfigureSettings() {
  return (
    // ... 组件代码
  )
}

{/* → "Create Project" clicked → SCREEN 3: Success */}

/* ================================================
   FLOW: Create Project
   SCREEN 3 of 3: Success
   ------------------------------------------------
   ENTRY:  Project created successfully
   EXIT:   "Go to Project" → Project Dashboard (exits flow)
           "Create Another" → SCREEN 1 (new flow instance)
   ================================================ */
export function Screen3_Success() {
  return (
    // ... 组件代码
  )
}
```

---

## 五、分支表达规范

### 5.1 Happy Path（主路径）

用 `→` 表示，写在注释头的 `EXIT` 行：

```
EXIT: "Confirm" → SCREEN 3: Review Order
```

### 5.2 Error Branch（错误分支）

错误分支通常回到当前屏，带错误状态：

```
BRANCH: Validation failed → SCREEN 2 (error state, fields highlighted)
BRANCH: Server error → SCREEN 2 (toast error, form re-enabled)
```

### 5.3 Conditional Branch（条件分支）

根据用户选择走不同路径：

```
BRANCH: Role = Admin → SCREEN 4A: Admin Setup
BRANCH: Role = Member → SCREEN 4B: Member Welcome
```

### 5.4 Skip / Optional Screen

某些屏幕在特定条件下可跳过：

```
EXIT: "Next" → SCREEN 3 (if org has billing) | SCREEN 4 (if new org, billing required)
```

---

## 六、终态规范（Exit State）

每个 flow 必须在最后一屏结束后声明三种终态处理：

### ✅ Success State

- 用户完成任务后看到什么（确认页 / toast / 自动跳转）
- 系统发生了什么（数据写入 / 邮件发送 / 状态变更）
- 推荐的下一步操作（引导用户继续使用产品）

### ❌ Unrecoverable Error

- 系统级错误（网络断开 / 服务不可用）
- 处理方式：全页错误提示 + 重试 / 联系支持 CTA
- 不应使用：仅 toast 提示后消失

### ↩ Abandon（用户中途退出）

- 用户关闭浏览器 / 点击 Back / 跳转其他页
- 须明确：数据是否保存为草稿？是否提示「未保存更改」？
- 推荐：超过 2 屏的 flow 保存草稿；2 屏及以下可直接丢弃

---

## 七、DS Coverage Notes（每个 flow 结束后必须输出）

生成完 flow 代码后，在最后添加：

```markdown
## DS Coverage Notes

### shadcn Components Used
| 组件 | 用途 | Spark DS 规划对应 |
|---|---|---|
| Dialog | 创建表单弹层 | SparkDialog |
| Form + Input | 表单字段 | SparkForm |
| Button | CTA 按钮 | SparkButton |

### Patterns to Add to Spark DS
- [ ] [pattern 名称]: [描述，为什么这个 pattern 应该进 DS]

### Components Missing from Spark DS
- [ ] [组件名]: [当前用 shadcn xxx 替代，建议添加到 Spark DS]
```

---

## 八、快速检查清单

生成 flow 后，逐项验证：

```
Flow 结构
- [ ] 屏幕数在 2-6 范围内
- [ ] 每屏有标准注释头（FLOW / SCREEN N of M / ENTRY / EXIT）
- [ ] 屏幕间有跳转注释
- [ ] 有 Happy Path、至少 1 个 Error Branch
- [ ] 定义了三种 Exit State（Success / Error / Abandon）

代码质量
- [ ] 所有 Spark 组件均 import from 'sparkdesign'，无旧版 @/components/ui/basic/ 路径
- [ ] 所有颜色 / 间距来自 Tailwind 或 CSS 变量，无硬编码值
- [ ] 表单有 loading 和 disabled 状态
- [ ] 空状态（Empty State）有处理

输出完整性
- [ ] DS Coverage Notes 已输出
- [ ] 缺失组件已标注
- [ ] 推荐添加到 Spark DS 的 pattern 已列出
```
