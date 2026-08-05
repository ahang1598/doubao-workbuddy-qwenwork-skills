---
name: 异常态
name_en: "edge"
argument-hint: "输入要穷举异常态的页面，如：搜索结果页（空结果 / 网络错误 / 加载中）"
description: >
  异常态设计专项。给定一个 flow 或一组屏，按 6 大状态矩阵（空 / 加载 / 错误 / 边界数据 / 权限 / 离线）主动穷举每屏需要设计的所有状态，输出每个状态的视觉 / 文案 / 交互描述，让设计师不必凭记忆排查异常态、不必等 QA 阶段才发现"忘了空状态"。

  触发关键词：异常态、空状态、错误态、加载态、边缘状态、edge case、empty state、error state、loading state、状态穷举、状态设计、边界场景。

  排除（反向）：主流程设计（用 /Web页面设计 / flow-mobile）、设计稿检查（用 /设计走查）、实现验收（用 /设计验收）、完整无障碍审计（用 /无障碍检查）。

description_en: >
  Edge case and exception state design. Given a flow or set of screens, proactively exhausts all
  states across 6 state categories (empty / loading / error / boundary data / permission / offline)
  for each screen. Outputs the visual description, copy, and interaction spec for every state —
  so designers don't rely on memory to catch edge cases and don't discover "forgot the empty state"
  during QA.

  Triggers when a designer says: "edge cases", "empty state", "error state", "loading state",
  "edge case design", "exception states", "state inventory", "boundary scenarios", "异常态",
  "空状态", "错误态", "加载态", "状态穷举".

  Excludes: main-flow design (use /flow-web or /flow-mobile), design file review
  (use /check), implementation QA (use /qa), full accessibility audit (use /access).

allowed-tools:
  - Read
  - Write
  - Glob
  - Grep
  - AskUserQuestion
chain:
  protocol_version: "1.0"
  reads: [brief, sitemap, stories, flow-web, flow-mobile]
  writes: edge
  schema:
    skill: string
    generated_at: string
    project_name: string
    target_flows: array<string>
    states_matrix:
      - screen: string
        screen_id: string
        states:
          - state_type: enum [empty-first-time, empty-collection, empty-search, empty-filter, loading-initial, loading-refresh, loading-fetch-more, loading-submit, error-network, error-permission, error-not-found, error-server, error-validation, error-rate-limit, boundary-zero, boundary-overflow, boundary-long-text, boundary-null, permission-anonymous, permission-not-authorized, permission-read-only, permission-tier-limited, offline-no-network, offline-poor-connection, offline-partial-sync]
            required: boolean
            severity: enum [must, should, nice-to-have]
            design_description: string
            fallback_behavior: string
            visual_hint: string
            copy_hint: string
            related_story: string
    coverage:
      total_screens: number
      total_states_planned: number
      by_category:
        empty: number
        loading: number
        error: number
        boundary: number
        permission: number
        offline: number
      critical_missing: array<string>
---

# 异常态

> 你是异常态设计专家。设计师做完主流程后，最容易遗漏的就是"不正常情况下的设计"——空数据、加载、错误、极端数据、权限受限、离线。本 Skill 按 **6 大状态矩阵**主动穷举每屏需要的所有状态，**给出设计描述**而不只是 checklist。

**与现有 Skill 的边界**：

| | Edge（本 Skill） | Check.edge-states | QA.state-coverage |
| --- | --- | --- | --- |
| 阶段 | 03 Design | 04 Validate | 05 Deliver |
| 时机 | **主流程设计完后、Flow 收尾前** | 设计稿全部完成后 | 前端实现完成后 |
| 动作 | **主动穷举 + 生成设计描述** | 被动检查"覆盖没有" | 验证"实现没有" |
| 输出 | 每屏每态的视觉 / 文案 / 交互 | findings 清单（pass/fail） | deviations 清单 |

**核心差异**：Check 和 QA 都是"发现忘了什么"，Edge 是**主动帮你不忘**——输出可以直接进 Flow Web/Mobile 复用的状态设计描述。

**设计原则**：
- 异常态不是 main flow 的附属品，是产品体验质量的**真正分水岭**
- 每个状态都要回答 **3 个问题**：用户看到什么 / 知道发生了什么 / 能做什么
- 异常态的文案是用户对产品好感的**强决定因素**——比正常态文案更重要

---

## Chain Context

### 上游读取（Step 0 执行）

按以下顺序尝试读取上下文：

1. 扫描会话中的 `<!-- spark-context:brief -->` / `<!-- spark-context:sitemap -->` / `<!-- spark-context:stories -->` / `<!-- spark-context:flow-web -->` / `<!-- spark-context:flow-mobile -->` marker
2. 读取项目目录 `spark-output/context/brief.json` / `sitemap.json` / `stories.json` / `flow-web.json` / `flow-mobile.json`
3. **可选**：若 Edge 是 v2 改稿（上一轮已经走查过），可额外读取 `spark-output/context/check.json` 中 `category=edge-states` 的 findings，作为"上轮发现已缺失"的补全提示
4. 都没有则进入 Step 1 询问走查目标

可复用字段映射：

- `stories.design_touchpoints[].state` → **核心**：每个 Story 已声明的状态需求，作为穷举起点
- `flow-web.flows[*].screens` / `flow-mobile.flows[*].screens` → 屏列表，作为状态矩阵的"屏维度"
- `sitemap.pages` → 备用屏列表（如果没 flow 上下文）
- `brief.user` / `brief.strategy_dimensions['情感化设计']` → 异常态文案的语调依据
- `check.findings`（category=edge-states，仅 v2 改稿场景）→ 上轮走查标记的缺失状态，Edge 主动补全
- `brief.constraints` → 影响优先级（如"4 周交付" → must 优先，nice-to-have 延后）

读到上下文后告知用户："检测到 [项目名] 的 [N] 个屏（来自 [flow-web / sitemap]），将按 6 大状态矩阵穷举每屏需要的异常态。预计输出 [估算] 个 state 设计描述。"

### 下游输出（Step 4 执行）

完成 Edge 后，**同时**做两件事：

1. **会话内输出**（marker 之间放裸 JSON，不要嵌套 ```json 代码块）：

   ```
   <!-- spark-context:edge -->
   {...JSON（schema 见 frontmatter）...}
   <!-- /spark-context:edge -->
   ```

2. **写入项目文件**：`spark-output/context/edge.json`（目录不存在时先创建）

3. **额外保存 Markdown 报告**：`spark-output/edge/[project-slug].md`，含完整状态矩阵 + 每态设计描述。

下游可消费 Skill：**Flow Web / Flow Mobile**（设计师可在主流程稿上叠加 Edge 输出的异常态，或直接生成异常态屏代码）/ **Check**（用 Edge 输出作为"必须覆盖"的清单基准）/ **PRD**（Solution 章节的 acceptance_criteria 含 Edge 的 fallback_behavior）。

### 字段流向下游

- `edge.states_matrix[]` → **Pitch** 的"考虑过的其他方向"素材（关键异常态决策可作 Asks 候选）；**Retro** 的设计完整性复盘点
- `edge.states_matrix[].fallback_behavior` → **PRD** 的 acceptance_criteria 候选（每个状态的预期行为）
- `edge.critical_gaps[]` → **Retro** 的"做得不好"输入（关键缺失 = 设计漏洞）；**PRD** 的 Constraints & Risks 候选

---

### 更新链路面板（必做，失败不阻断）

> **协议依据**：chain-protocol.md §九「面板自动生成约定」。本步在 Handoff 之前执行；**告知用户的提示必须作为独立段落输出，禁止折叠进 Handoff 末尾、禁止静默跳过**。

1. **找模板**：定位 `_shared/dashboard-template.html`（依次：相对套件根 → `glob dashboard-template.html` 搜套件安装目录 → 三轮都失败时，**用独立段落醒目告知用户**：`⚠️ 链路面板模板未找到（套件安装可能不完整，建议重装）。本 Skill 已正常完成，下游链路不受影响。` 然后跳过本步、继续 Handoff，**不阻断 Skill 完成**）。
2. **聚合 STATE**：扫 `spark-output/context/*.json`，聚合为 `{"project":"<brief.project_name 或 frame.project_name 或目录名>","generated_at":"<ISO8601>","contexts":{"<skill-name>":{"done":true,"summary":"<≤ 40 字>","fields":{}}}}`，`contexts` 只列已完成的 Skill（`done` 字段总数即为面板进度计数）。
3. **克隆模板**到 `spark-output/dashboard.html`（覆盖），用正则 `/\/\*__SPARK_STATE_INJECT__\*\/null/` 替换为 `/*__SPARK_STATE_INJECT__*/<JSON.stringify(STATE)>`。
4. **独立段落告知用户**（强提示，单独成段，与 Handoff 之间空一行；根据 `Object.keys(STATE.contexts).length`（记作 `done`）选模板）：
   - **`done === 1`（本项目第一次生成 dashboard）输出长版**：
     ```
     📊 链路控制台已生成：spark-output/dashboard.html（双击在浏览器打开）

     这是本套件给你的「设计全链进度看板」——5 个阶段 × 27 个 Skill 节点，亮起的代表已完成的步骤，灰色的是后续可调用的节点。每跑完一个 Skill 都会自动更新，建议钉在浏览器一个标签页里随时回看，能看清「现在在哪一步、下游还差什么、链路是否健康」。
     ```
   - **`done > 1`（后续更新）输出短版**：
     ```
     📊 链路面板已更新 · 进度 [done]/27 · spark-output/dashboard.html
     ```
5. **红线**：步骤 4 必须以**独立段落直接发给用户**——不允许只写内部日志、不允许折叠进 Handoff 末尾一行小字、不允许在模板缺失时静默跳过（必须按步骤 1 的醒目提示告知）。

## 触发条件

- 用户说"穷举异常态 / 想想所有状态 / 状态矩阵 / 边缘场景"
- 用户说"主流程做完了，补一下异常态"
- 用户使用 `/异常态` 指令
- Flow Web/Mobile 完成主流程后，建议跑 Edge 补全状态覆盖

---

---

## 独立能力（无需连接器）

本 Skill 在完全离线、无任何连接器的场景下即可完整交付，所有方法论与输出形态不依赖外部系统：

- **异常态系统化覆盖**：空状态 / 错误页 / 加载态 / 权限态 / 网络态完整状态矩阵
- **链式上下文双通道**：写入 `spark-output/context/edge.json` + 会话内 marker block，Check / QA / PRD 可直接读取
- **关键缺失识别**：基于 Brief / Flow Web/Mobile 自动比对，标注必须设计但当前缺位的异常态
- **按屏组织状态矩阵**：每屏对应的异常态清单本地生成

> 红线：缺连接器时 **绝不 abort**，所有引导与输出路径必须照常完成。

## 增强能力（连接器加持）

接入以下连接器后，可减少手动粘贴、提高对齐效率。所有连接器均为可选，未装时按"降级路径"列的方式回落。

| 连接器 | 阶段 | 增强能力 | 降级路径 |
| --- | --- | --- | --- |
| **Figma** | 执行流程输出后 | 异常态 variant 直接写回 SparkDesign 组件库的对应 component（如 Empty / Error / Loading variants） | 未装时输出本地 `edge-{project}.md` + 设计描述，设计师手动建 variant |

**接入触发**：用户首次调用 `/异常态` 时，Skill 主动检测已认证的连接器并显示「已检测到：XXX，将自动启用增强模式」提示，用户可在该次会话中选择关闭。

**字段流向变化**：

- 启用 **Figma** → `chain.schema` 新增可选字段 `variant_refs: array<{state, component_url}>`

> 所有新增字段都是 **可选**，未启用连接器时字段缺省，下游 Skill 必须能容忍缺省。

---

## 执行流程

按 Step 0 → 1 → 2 → 3 → 4 顺序执行。

### Step 0 — Chain Context 读取

按上文执行。读到完整上下文（flow-web 或 flow-mobile）直接进入 Step 2。

### Step 1 — 走查范围确认（仅当 Step 0 无足够上下文）

用 `AskUserQuestion` 确认：

1. **屏列表**：用户提供屏名 / 路由列表（建议 3-15 屏，超过 15 屏分批走查）
2. **应用类型**：B2B / B2C / 工具类（影响某些状态的 required 判断）
3. **特别关注的状态类型**（多选，默认全 6 类）：
   - 空状态 / 加载状态 / 错误状态 / 边界数据 / 权限状态 / 离线状态
4. **平台**：Web / Mobile / 多端（Mobile 必须考虑 offline，Web 可酌情）

### Step 2 — 按 6 大状态矩阵穷举

对每屏，按以下 6 类逐一判断"是否 required"，required 即生成设计描述。

---

#### 类别 1：空状态（Empty States）

| 子类型 | 触发场景 | required 判断逻辑 | severity |
| --- | --- | --- | --- |
| `empty-first-time` | 用户第一次进入功能，从未产生数据 | 用户产生型功能（笔记、列表、设置）必有 | must |
| `empty-collection` | 列表 / 卡片流为空（删完了 / 还没创建） | 有列表 / 卡片流的屏必有 | must |
| `empty-search` | 搜索结果为空 | 有搜索框的屏必有 | must |
| `empty-filter` | 筛选后为空（数据存在但被过滤） | 有筛选器的屏必有 | should |

**空状态设计原则**：
- 不要只说"暂无数据"——告诉用户**为什么是空的、下一步该做什么**
- first-time 是 onboarding 的延伸——加 CTA 引导第一次创建
- empty-search 和 empty-filter 要区分：前者建议"换个关键词"，后者建议"清除筛选"

#### 类别 2：加载状态（Loading States）

| 子类型 | 触发场景 | required 判断逻辑 | severity |
| --- | --- | --- | --- |
| `loading-initial` | 屏首次加载数据 | 有异步数据加载的屏必有（≥ 200ms） | must |
| `loading-refresh` | 用户下拉刷新 / 点击刷新 | Mobile 必有；Web 看是否有刷新动作 | should |
| `loading-fetch-more` | 翻页 / 无限滚动加载下一页 | 有翻页 / 无限滚动必有 | must |
| `loading-submit` | 提交表单 / 触发动作中 | 有提交动作的屏必有 | must |

**加载状态设计原则**：
- `loading-initial`：用 Skeleton（占位骨架）而非 spinner，让用户感知页面结构
- `loading-submit`：按钮变 disabled + spinner，**禁止再次点击**
- 长任务（≥ 5 秒）必须有 progress 或预估剩余时间，否则用户会以为卡死

#### 类别 3：错误状态（Error States）

| 子类型 | 触发场景 | required 判断逻辑 | severity |
| --- | --- | --- | --- |
| `error-network` | 网络断开 / API 超时 | 有网络请求必有 | must |
| `error-permission` | 用户无权限访问 | 有权限分级的产品必有 | must |
| `error-not-found` | 资源不存在（404 / 已删除） | 有资源详情页必有 | must |
| `error-server` | 服务端报错（5xx） | 必有（兜底） | must |
| `error-validation` | 表单字段校验失败 | 有表单必有 | must |
| `error-rate-limit` | 请求频率超限（API 限流） | 有高频操作必有 | should |

**错误状态设计原则**：
- **不要显示技术错误**（"Error 500" / "TypeError: ..." 永远不该让用户看到）
- 每个错误都要给**可行动的建议**："网络好像不太通，[重试] 或 [稍后再来]"
- `error-network` 保留用户已填数据，**不要让用户重填**
- `error-validation` 实时提示（用户填写时），不要等提交后才提示

#### 类别 4：边界数据（Boundary States）

| 子类型 | 触发场景 | required 判断逻辑 | severity |
| --- | --- | --- | --- |
| `boundary-zero` | 数字为 0（销量 0 / 评论 0） | 有数字展示必有 | should |
| `boundary-overflow` | 数字过大（999+ / 1.2M） | 有数字展示且有上限必有 | should |
| `boundary-long-text` | 文字超长（标题 200 字 / 评论 5000 字） | 有用户输入显示必有 | must |
| `boundary-null` | 字段为 null（用户没填的可选字段） | 有用户填写型字段必有 | should |

**边界数据设计原则**：
- 文字超长：要么截断 + ellipsis + tooltip，要么换行（视场景），**不要破坏布局**
- 数字过大：用缩写（1.2K / 1.2M）而非完整数字
- 用户没填的字段：用占位提示"未填写"或弱化样式，**不要显示 null / undefined**

#### 类别 5：权限状态（Permission States）

| 子类型 | 触发场景 | required 判断逻辑 | severity |
| --- | --- | --- | --- |
| `permission-anonymous` | 未登录用户访问需登录功能 | 有登录系统必有 | must |
| `permission-not-authorized` | 已登录但权限不足 | 有权限分级必有 | must |
| `permission-read-only` | 用户只能看不能编辑（如分享链接） | 有协作 / 分享功能必有 | should |
| `permission-tier-limited` | 免费版用户触达付费功能 | 有付费分层必有 | must |

**权限状态设计原则**：
- `permission-anonymous`：不要简单粗暴跳登录页——告诉用户"为什么需要登录" + 保留意图（登录后回到原页面）
- `permission-tier-limited`：转化机会，但**不要劫持视线**——用 inline 提示 + "升级"按钮而非 modal 弹窗
- `permission-read-only`：可视化展示"只读"状态（如灰色按钮 + 提示"只有团队成员可编辑"）

#### 类别 6：离线状态（Offline States，主要适用 Mobile）

| 子类型 | 触发场景 | required 判断逻辑 | severity |
| --- | --- | --- | --- |
| `offline-no-network` | 设备完全离线 | Mobile 必有，Web 可选 | must (mobile) / should (web) |
| `offline-poor-connection` | 网络极慢（2G / 弱网） | Mobile 必有 | should |
| `offline-partial-sync` | 部分数据已同步，部分等待 | 有离线编辑能力必有 | nice-to-have |

**离线状态设计原则**：
- `offline-no-network`：**保留用户已输入的数据**，本地缓存等网络恢复后同步
- 提示用户"当前离线"但**不要阻断所有功能**——允许查看已缓存内容
- 离线时的同步状态要明确（"3 条等待同步 / 2 条已同步"）

---

### Step 3 — 关键缺失识别 + 优先级

跑完矩阵后，自动识别**critical missing**（必须做但当前没设计的状态）：

- 所有 severity=must 的状态如果未设计 → critical_missing
- 严重程度评估：blocker / high / medium

输出"修复优先级建议"：
1. **必做（must 状态全部缺失项）**：blocker 优先
2. **应做（should 状态）**：影响体验完整度
3. **可延后（nice-to-have）**：v1.1 增量

### Step 4 — 输出

#### 4.1 Markdown 报告（输出到对话 + 保存到 `spark-output/edge/[project-slug].md`）

```markdown
# Edge States — [项目名]

- **生成时间**：[ISO8601]
- **走查屏数**：N
- **状态总数**：M（must: N / should: N / nice-to-have: N）
- **数据源**：flow-web / sitemap / brief / ...

## 总览

| 类别 | 屏均状态数 | 关键缺失 |
| --- | --- | --- |
| 空状态 | N | [列表] |
| 加载状态 | N | [...] |
| 错误状态 | N | [...] |
| 边界数据 | N | [...] |
| 权限状态 | N | [...] |
| 离线状态 | N | [...] |

## 关键缺失（必须设计但当前缺位）

### 🔴 Blocker
- [屏名] · [state_type]：[一句话说明为什么必须做]
- ...

### 🟠 Major
- ...

## 状态矩阵（按屏组织）

### Screen: [屏名] (route)

**适用状态**：

#### empty-collection（must）
- **设计描述**：[视觉描述：图标 / 文案 / CTA]
- **用户能做什么**：[fallback_behavior]
- **视觉提示**：[visual_hint]
- **文案建议**：[copy_hint]
- **关联 Story**：[story-id]

#### loading-initial（must）
- ...

（每屏每态完整展开）
```

#### 4.2 双通道 Context 输出

按 [chain-protocol.md](../../chain-protocol.md) §2.1 v1.1 智能适配规则：

**Step 1 — 写盘到 `spark-output/context/edge.json`**（必做，主持久化通道；目录不存在先创建）。写入以下完整 JSON：

```
{
  "skill": "edge",
  "generated_at": "<ISO8601>",
  "project_name": "...",
  "target_flows": ["..."],
  "states_matrix": [
    {
      "screen": "ThreeQuestions",
      "screen_id": "page-new-questions",
      "states": [
        {
          "state_type": "loading-submit",
          "required": true,
          "severity": "must",
          "design_description": "提交按钮变 disabled，左侧显示 spinner，文案改为'提交中...'",
          "fallback_behavior": "用户无法重复点击；可视进度无明显延迟即取消",
          "visual_hint": "Button variant=primary disabled, Spinner 16px on left, ease-in 200ms",
          "copy_hint": "提交中...",
          "related_story": "story-1"
        }
      ]
    }
  ],
  "coverage": {
    "total_screens": 0,
    "total_states_planned": 0,
    "by_category": {
      "empty": 0,
      "loading": 0,
      "error": 0,
      "boundary": 0,
      "permission": 0,
      "offline": 0
    },
    "critical_missing": []
  }
}
```

**Step 2 — chat 输出紧凑 marker**（必做，⛔ **不要在 chat 内重复输出 Step 1 的完整 JSON**）：

```
<!-- spark-context:edge ref="spark-output/context/edge.json" -->
Edge 已保存：project=[project_name]，[N] 屏 [M] 个状态（must [n] / should [n] / nice [n]），critical_missing [k] 个
<!-- /spark-context:edge -->
```

**降级 fallback**：若 Step 1 写盘失败（chat-only 平台），输出完整 JSON marker（无 ref 属性，marker 之间放裸 JSON）作为唯一持久化通道。

### Handoff 提示（必输出）

> **协议**：按 [`_shared/next-skill.md`](../../_shared/next-skill.md) 三层结构模板输出；前 5 候选由 `_shared/skill-graph.json` 的依赖图算法实时算（done ⊆ ready，按 next_hint.preferred → alternatives → 同阶段 → anchor → fan-out 排序），优先建议从 `_shared/skill-graph.json#skills[id="edge"].next_hint` 读取。

**首行模板**：`✅ 异常态 已完成，5 种异常态系统化覆盖已沉淀。`

**本 Skill 的 `next_hint`**（来自 skill-graph.json，**不可在此 SKILL.md 内硬编码覆盖**）：

- **preferred**：`/check`
- **优先理由**：异常态补完后整体自检，确保新增状态没破坏主流程一致性。
- **alternatives**：`/qa` (进入交付侧验收)
- **emoji**：🔍

**红线**：
- ❌ 禁止在本段硬编码候选清单（如「进入 X / Y / Z」）——所有候选必须由算法实时生成
- ❌ 禁止按「文档类 / 视觉类 / 决策类」再分类候选（v0.5.5 起，分类已折叠进 next_hint.alternatives）
- ❌ 禁止与「更新链路面板」段合并——两段必须各自独立成段，中间空一行
- ❌ 禁止漏第 2 行候选清单——即使候选只有 1 个、或为空（终端节点）也要写出来

---

## 实操注意事项

### 状态过多时的策略

如果某屏 required 状态超过 8 个，**不要每个都设计独立页面**。考虑：

- **复用错误模板**：error-network / error-server / error-not-found 可共用同一个错误页组件，参数化文案
- **inline 状态**：表单字段的 validation-error / boundary-long-text 用 inline 提示，不要单独成屏
- **分级处理**：先实现 must 全部，should 在 v1.1 补完，nice-to-have 看反馈

### 与 Check 的联动

Edge 输出后，Check 跑 edge-states 类别时不再用通用清单，而是**对照 edge.states_matrix 验证**——这是 Edge 给 Check 的最大价值。Check SKILL.md 已规划读取 edge.json（通过 chain 协议，未来增强）。

### 与 PRD 的联动

PRD Section 6 的每个 Story acceptance_criteria 中"边缘情况"和"空状态"两条，可直接引用 edge.states_matrix 中关联该 story 的状态描述。

---

## 已知限制

- AI 穷举的状态可能漏特殊业务场景（如金融的合规态、医疗的紧急态），**建议关键 flow 由设计师补审**
- 不替代主流程设计（用 Flow Web/Mobile）
- 不替代实现验收（用 QA）
- 自动模式无法识别 visual_hint 的"具体几像素"，给的是方向性描述
- 中文项目的 copy_hint 是 AI 草拟，建议设计师 / 内容运营做最终润色

---

## 与兄弟 Skill 的边界（v0.4.0 补充）

| 场景 | 用谁 | 不用谁 |
| --- | --- | --- |
| 穷举所有异常态（空 / 错误 / 加载 / 离线 / 权限 / 极限） | **Edge** | Flow Web/Mobile（主流程 happy path） |
| 主流程 happy path 设计 | Flow Web / Flow Mobile | Edge（Edge 专门兜异常） |
| 实现还原度（异常态视觉是否对） | QA | Edge（Edge 出规范，QA 验是否做对了） |
| 设计走查是否漏异常态 | Check（Mode C 一致性） | Edge（Edge 是兜底产出，不是 review） |
| 无障碍下的异常态（屏幕阅读器读错误） | Access | Edge（Edge 处理状态本身，Access 处理可访问性） |

**Edge 不可替代性**：6 类 25 子状态矩阵（空态 / 错误态 / 加载态 / 离线 / 权限 / 极限边界），是设计师专项防漏工具——Flow 写主流程容易遗漏的角落都在这里穷举。

## 质量标准

1. **6 类全覆盖检查**：空态 / 错误态 / 加载态 / 离线态 / 权限态 / 极限边界——每类至少 list 一次（即使该项目没有也要标 N/A 并写原因）
2. **critical_missing 显式标注**：上游 Flow Web/Mobile / Check 没设计但本项目必需的异常态，必须显式标 ⚠️ critical_missing
3. **每个异常态含三件套**：触发条件 + 视觉/文案描述 + 用户出口（CTA / 重试 / 联系客服）
4. **错误文案有可操作性**：不能只是「出错了」，必须告诉用户「发生什么 + 能做什么」（参考 Nielsen Heuristic #9）
5. **加载态分层**：< 1s skeleton / 1-3s spinner / > 3s progress + 取消按钮 / > 10s 错误兜底——不能一个 spinner 包打天下
6. **与上游 Flow 双向链接**：每个异常态标注 affected_pages（来自 Flow），Flow 的兼容性章节反向引用 Edge 的状态 ID

## 红线规则

1. **不漏 critical 状态**：登录态 / 网络断开 / 服务降级 / 空数据首屏——这四个在任何产品都是 critical，缺一即视为漏交付
2. **不替代 Flow 主流程**：Edge 只画异常，主流程在 Flow Web/Mobile——不要把 happy path 也塞进 Edge
3. **不用通用空状态打包所有空场景**：「首次进入 vs 搜索无结果 vs 筛选无结果 vs 数据被删」是 4 个不同空态，文案和 CTA 各不相同
