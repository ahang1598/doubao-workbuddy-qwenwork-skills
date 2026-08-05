---
name: 设计走查
name_en: "check"
argument-hint: "输入要走查的页面或代码文件路径，如：src/pages/checkout.tsx"
description: >
  设计走查（Design Review Checklist）。在设计稿 / 多屏 Flow / 落地页等设计产物完成后、上线或交付前进行自检，逐项发现问题并给出修复建议。

  触发关键词：设计走查、design review、自检、/设计走查、走查清单、上线前检查、交付前检查、看一下我的设计有什么问题、检查设计稿、找问题、Vibe Coding 自检。

  排除（反向）：仅做无障碍专项检查（用 /无障碍检查）、仅做前端实现还原度（用 /设计验收）、仅做可用性测试（用 test）。

description_en: >
  Design Review Checklist. After completing a design file, multi-screen flow, or landing page —
  and before shipping or handoff — runs a systematic self-review, identifies issues per category,
  and provides fix recommendations.

  Triggers when a designer says: "design review", "self-check", "pre-launch check",
  "pre-handoff review", "Check", "review checklist", "find issues with my design",
  "check the design file", "find problems", "vibe coding self-check", "设计走查", "自检".

  Excludes: accessibility-only audit (use /access), frontend implementation fidelity
  (use /qa), usability testing (use test).

allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
  - AskUserQuestion
chain:
  protocol_version: "1.0"
  reads: [brief, flow-web, flow-mobile, sitemap, stories]
  writes: check
  schema:
    skill: string
    generated_at: string
    project_name: string
    target: string
    findings:
      - category: enum [flow-continuity, ia, components, visual-hierarchy, edge-states, copy, responsive, feedback, accessibility, brief-consistency]
        severity: enum [blocker, major, minor]
        description: string
        suggestion: string
        location: string
    summary:
      blocker: number
      major: number
      minor: number
      pass: number
---

# 设计走查

> 你是设计走查专家。本 Skill 在设计产物完成后做系统性自检，按 10 个类别逐条核对，输出**结构化发现清单**（含严重度、问题描述、修复建议、出现位置），帮设计师在上线 / 交付前抓住容易遗漏的问题。

**使用边界**：本 Skill 不做"是否好看"的主观审美评判，只做**可观察、可判断的问题识别**。审美评估请用 Pitch / Board。

---

## Chain Context

### 上游读取（Step 0 执行，先于 Step 1）

按以下顺序尝试读取上下文：

1. 扫描会话中的 `<!-- spark-context:brief -->` / `<!-- spark-context:flow-web -->` / `<!-- spark-context:flow-mobile -->` / `<!-- spark-context:sitemap -->` / `<!-- spark-context:stories -->` marker
2. 读取项目目录 `spark-output/context/brief.json` / `flow-web.json` / `flow-mobile.json` / `sitemap.json` / `stories.json`
3. 都没有则跳过，进入 Step 1 询问走查目标

可复用字段映射：

- `brief.design_criteria` → 核对的"通过标准"基线（替换默认通用标准）
- `brief.business_goal` / `user` → 一致性检查的依据（设计是否服务于业务目标 / 主用户？）
- `brief.strategy_dimensions` → 优先检查 Brief 提到的设计策略维度
- `brief.constraints` / `out_of_scope` → 范围核查（是否做了 out_of_scope 里的内容？）
- `flow-web.flows` / `flow-mobile.flows` → 走查目标范围（要检查的 flow 列表）
- `flow-web.output_files` / `flow-mobile.output_files` → 实际要 Read 的文件路径列表
- `sitemap` → IA 一致性核对依据
- `stories.acceptance_criteria` → 验收标准核对依据

读到上下文后告知用户："检测到 [项目名] 的 Brief + [Flow Web/Mobile] 上下文，将基于 [N 个] flow 文件 + Brief 的 [N 条] 设计标准做走查。如需缩小范围请说明，否则进入 Step 2 开始走查。"

### 下游输出（Step 4 执行）

完成走查后，**同时**做两件事：

1. **会话内输出**：

   ```
   <!-- spark-context:check -->
   {...JSON（schema 见 frontmatter）...}
   <!-- /spark-context:check -->
   ```

2. **写入项目文件**：`spark-output/context/check.json`（目录不存在时先创建）

下游可消费 Skill：QA（前端实现走查时引用）/ Pitch（汇报材料引用）/ Retro（复盘归档）。

### 字段流向下游

- `check.findings[].severity` → **QA** 的"Check Finding 核对"段（验收时确认 blocker 是否已修）；**Edge** 的状态补全清单
- `check.findings[].category` → **Access** 的合规优先级映射（accessibility 类直接转 Access 输入）；**PRD** 的 Constraints & Risks 分类
- `check.findings[].suggestion` → **PRD** 的 Constraints & Risks 候选；**Pitch** 的"我们最不确定的事"素材
- `check.opportunities[]` → **Retro** 的"做得不好"输入；**Pitch** 的 Asks 候选

---

## 触发条件

以下任意一种情况触发本 Skill：

- 用户说"做个设计走查 / design review / 自检"
- 用户说"上线前检查"、"交付前检查"
- 用户使用 `/设计走查` 指令
- 前序 Skill（Flow Web / Flow Mobile / Landing 等）完成后，用户希望验证

---

---

## 独立能力（无需连接器）

本 Skill 在完全离线、无任何连接器的场景下即可完整交付，所有方法论与输出形态不依赖外部系统：

- **Vibe Coding 自查 checklist**：Design Review 全套规则本地完成
- **链式上下文双通道**：写入 `spark-output/context/check.json` + 会话内 marker block，下游 QA / Edge / Retro 可直接读取
- **Findings 按严重度排序**：含修复优先级建议
- **自定义规则（进阶）**：支持项目级 checklist 扩展

> 红线：缺连接器时 **绝不 abort**，所有引导与输出路径必须照常完成。

## 增强能力（连接器加持）

接入以下连接器后，可减少手动粘贴、提高对齐效率。所有连接器均为可选，未装时按"降级路径"列的方式回落。

| 连接器 | 阶段 | 增强能力 | 降级路径 |
| --- | --- | --- | --- |
| **Figma** | 执行流程（对照阶段） | 直接读 Figma 设计稿与实现做并排对照，Findings 嵌入 frame 缩略图 | 未装时让用户提供设计稿截图或描述 |
| **GitHub** | 执行流程（实现侧阶段） | 读 PR diff 或 commit changeset 自动对照 Flow Web/Mobile 输出，识别实现偏差 | 未装时让用户粘贴代码片段或本地 diff |

**接入触发**：用户首次调用 `/设计走查` 时，Skill 主动检测已认证的连接器并显示「已检测到：XXX，将自动启用增强模式」提示，用户可在该次会话中选择关闭。

**字段流向变化**：

- 启用 **Figma** → `chain.schema` 新增可选字段 `design_refs: array<{frame_url, finding_ids}>`
- 启用 **GitHub** → `chain.schema` 新增可选字段 `pr_url: string` + `diff_refs: array<{file, finding_ids}>`

> 所有新增字段都是 **可选**，未启用连接器时字段缺省，下游 Skill 必须能容忍缺省。

---

## 执行流程

按 Step 0 → 1 → 2 → 3 → 4 顺序执行，每步完成后再进入下一步。

### Step 0 — Chain Context 读取

按上文 "Chain Context > 上游读取" 节执行。读取成功直接进入 Step 2，跳过 Step 1。

### Step 1 — 走查目标确认（仅当 Step 0 无上下文）

用 `AskUserQuestion` 确认走查目标：

1. **走查范围**：单个页面 / 多屏 flow / 整个项目
2. **设计产物形式**：代码文件（.tsx / .html / .vue 等）/ 设计稿（Figma 链接）/ 截图描述
3. **如果是代码文件**：让用户提供文件路径，本 Skill 会用 Read 工具实际读取
4. **是否有设计标准 / 业务目标**：让用户简述（用于一致性检查）

### Step 2 — 走查模式选择

根据 Step 0 / 1 的输入，选择走查模式：

**模式 A — 自动走查（默认，推荐）**

适用于：能 Read 到代码文件的情况（来自 Flow Web/Mobile chain，或用户提供路径）。

执行方式：
- 用 Read 工具逐个读取 `flow-web.output_files` 或用户提供的代码文件
- 对每个文件按 Step 3 的 10 个类别做静态检查
- 命中规则即记入 findings

**模式 B — 清单模式（降级）**

适用于：只有截图描述、Figma 链接、或用户口述设计的情况。

执行方式：
- 输出完整检查清单（10 类共 ~50 项）到对话
- 让用户 / AI 逐项回答"通过 / 未通过 / N/A"
- 用户回答后整理为 findings

**模式 C — 定向验证模式（chain-driven，⭐ 链路最强时优先用）**

适用于：**检测到完整上游 chain context**（brief + stories + journey 至少有 2 个），或**用户给了"特别关注点"**（例如"重点看 strategy_dimensions 是否在 flow 里落地"、"验证 Journey 里的 repair_strategies 都实现了"）。

**为什么需要这个模式**：通用 10 类清单是"通用 sanity check"，但当 chain 完整时，最有价值的检查不是"按 Nielsen 跑一遍"，而是**"上游承诺要做的事 → 下游做了吗"**——避免漏掉项目特定的设计决策。

执行方式（**不走通用 10 类清单，改为 3 个定向核对表**）：

**C.1 — Brief Strategy Dimensions 逐项验证**

对 `brief.strategy_dimensions` 每个 dimension（通常 5 个：IA / 交互 / 视觉 / 内容 / 用户引导），核对下游 flow 是否落地：

| 维度 | thesis（来自 Brief） | 落地位置（Flow 哪些屏） | 判定 |
| --- | --- | --- | --- |
| 信息架构 IA | 客户工作区为核心 | flow3-dashboard.tsx（卡片列表平铺） | ✅ 通过 |
| 交互设计 | 5 分钟首体验，3 步内完成 | flow2-activation（4 屏 wizard） | 🟡 部分通过（实际 4 步，比 thesis 多 1 步） |
| 视觉设计 | 专业工具感为主 | 全 flow 使用 Spark theme | ✅ 通过 |
| 内容设计 | 直接、技术人语气 | 文案待人工核对 | ⏳ 待确认 |
| 用户引导 | 渐进式，不一次性塞满 | flow1-onboarding-welcome.tsx | ✅ 通过 |

**C.2 — Stories Acceptance Criteria 三态核对**

对每个 `stories[].acceptance_criteria`，核对是否在 flow-web 里实现：

| Story | acceptance_criteria | 实现位置 | 判定（✅ 通过 / 🟡 部分 / ❌ 未通过） |
| --- | --- | --- | --- |
| story-1 | OAuth 1-click 登录 | flow1-github-auth.tsx | ✅ 通过 |
| story-2 | Stripe 内嵌 checkout（不跳出） | flow2-stripe-setup.tsx | 🟡 部分（跳出新 tab） |
| ... | ... | ... | ... |

**C.3 — Journey Repair Strategies 实现确认**（当 journey.json 有 `dropout-risk` 阶段 + `repair_strategies` 时）

| Journey 阶段 | dropout-risk | repair_strategy | 实现位置 | 判定 |
| --- | --- | --- | --- | --- |
| Activation | 4 个 dropout 原因 | "拆为 3 步检查清单 + 进度可视化" | flow2-activation（4 屏 + Progress 组件） | ✅ 通过 |
| ... | ... | ... | ... | ... |

**输出格式**：把 C.1 / C.2 / C.3 三张表作为「**优先确认**」区块放在 findings 之前，让 reviewer 一眼看到 chain 一致性。然后再补充通用 10 类里有发现的 findings。

**Mode C 适用条件总结**：

| 上游 chain 完整度 | 用户给关注点 | 推荐模式 |
| --- | --- | --- |
| brief + stories + journey 都有 | 是 / 否 | **Mode C ⭐** |
| 只有 flow-web，无 brief | — | Mode A |
| 只有截图 | — | Mode B |
| 全无上下文 | — | Mode A 兜底（用户给的代码） |

告知用户当前选择的模式，等用户确认后进入 Step 3。**Mode C 时跳过 Step 3 的 10 类清单，直接按 C.1-C.3 输出**。

### Step 3 — 按 10 类逐项走查

对每个类别，逐条核对。命中问题时按 [severity] [category] [location] [description] [suggestion] 五元组记录。

---

#### 类别 1：链路通畅性（Flow Continuity）

| # | 检查项 | 通过标准 | 严重度（命中时） |
| --- | --- | --- | --- |
| 1.1 | 每个 flow 是否有清晰的入口屏 | 第一屏的 CTA / 触发点明确 | major |
| 1.2 | 每个 flow 是否有终点屏（成功 / 失败） | 用户能感知"流程已结束" | major |
| 1.3 | 是否存在断点（点击无响应 / 跳转目标缺失） | 所有交互元素都有明确的下一步 | blocker |
| 1.4 | 返回 / 取消 / 关闭路径是否完整 | 用户能从任意屏退出而不丢失数据 | major |
| 1.5 | 多步流程是否有进度提示 | ≥3 步时有 step indicator | minor |

#### 类别 2：信息架构（IA）

| # | 检查项 | 通过标准 | 严重度 |
| --- | --- | --- | --- |
| 2.1 | 导航命名是否一致 | 同一入口在不同位置文案一致 | major |
| 2.2 | 层级是否符合 Sitemap（如有 chain context） | 不超过 sitemap 定义的深度 | major |
| 2.3 | 是否存在孤立屏（无入口 / 无出口） | 每屏至少有 1 入 + 1 出 | blocker |
| 2.4 | TabBar / 主导航数量是否合理 | Mobile ≤5 项，Web ≤7 项 | minor |

#### 类别 3：组件使用（Design System）

| # | 检查项 | 通过标准 | 严重度 |
| --- | --- | --- | --- |
| 3.1 | 是否使用了设计系统组件 | 优先用 SparkDesign / shadcn / antd 等已选组件库，避免 ad-hoc div + style | major |
| 3.2 | 同类元素是否复用同一组件 | 所有 Button 用同一个 Button 组件，不混用 | major |
| 3.3 | 是否引入了组件库未涵盖的自定义样式 | 自定义部分 < 20%，且有理由 | minor |
| 3.4 | 颜色 / 字号 / 圆角是否走 token | 不出现裸的 `#xxx` 色值或 `font-size: 14px` 硬编码 | major |

#### 类别 4：视觉层级（Visual Hierarchy）

| # | 检查项 | 通过标准 | 严重度 |
| --- | --- | --- | --- |
| 4.1 | 主操作是否视觉突出 | 主 CTA 用 primary 色 / 加粗 / 大尺寸 | major |
| 4.2 | 是否同屏存在多个"主操作" | 一屏只有 1 个 primary 按钮 | minor |
| 4.3 | 标题层级是否清晰 | h1 > h2 > h3，不乱跳级 | minor |
| 4.4 | 留白是否合理 | 元素之间 ≥8px，不挤压 | minor |
| 4.5 | 对齐是否一致 | 同列元素左对齐 / 居中对齐统一 | minor |

#### 类别 5：异常态覆盖（Edge States）

| # | 检查项 | 通过标准 | 严重度 |
| --- | --- | --- | --- |
| 5.1 | 空状态是否设计 | 列表 / 卡片 / 数据看板有空数据提示 | major |
| 5.2 | 加载态是否设计 | 异步操作有 skeleton / spinner | major |
| 5.3 | 错误态是否设计 | 网络 / 表单 / 权限错误有友好提示 | major |
| 5.4 | 极端数据态是否考虑 | 文字超长 / 图片缺失 / 数据为 0 / 数据为 999+ 都不破坏布局 | minor |

#### 类别 6：内容文案（Copy）

| # | 检查项 | 通过标准 | 严重度 |
| --- | --- | --- | --- |
| 6.1 | 按钮文案是否动词开头 | "保存"、"提交"，而非"OK" | minor |
| 6.2 | 错误提示是否给出可行动指引 | 不只说"错了"，要说"怎么办" | major |
| 6.3 | 专业术语 / 行话是否一致 | 同一概念全文用同一个词 | minor |
| 6.4 | 是否有 placeholder 残留（"Lorem ipsum"、"待填"） | 无残留 | major |

#### 类别 7：响应式 / 多端（Responsive）

| # | 检查项 | 通过标准 | 严重度 |
| --- | --- | --- | --- |
| 7.1 | Web 端是否定义了断点行为 | mobile / tablet / desktop 三档 | major |
| 7.2 | Mobile 端是否考虑 iPhone SE 小屏 | 320px 宽度下不溢出 | major |
| 7.3 | 横屏 / 竖屏切换是否处理 | Mobile 横屏不破坏布局 | minor |

#### 类别 8：反馈与交互（Feedback）

| # | 检查项 | 通过标准 | 严重度 |
| --- | --- | --- | --- |
| 8.1 | 按钮 / 链接是否有 hover / pressed 态 | 至少 hover + active 两态 | minor |
| 8.2 | 表单提交是否有反馈 | 成功 toast / 失败提示 | major |
| 8.3 | 不可逆操作是否有二次确认 | 删除 / 退出未保存等 | major |
| 8.4 | 长操作是否有取消通道 | 上传 / 下载可中断 | minor |

#### 类别 9：无障碍基础（Accessibility 基础）

| # | 检查项 | 通过标准 | 严重度 |
| --- | --- | --- | --- |
| 9.1 | 文字与背景对比度是否充分 | 正文 ≥4.5:1 | major |
| 9.2 | 仅靠颜色传达信息时是否有辅助标识 | 错误用 红色 + 图标 + 文字三重 | minor |
| 9.3 | 交互元素是否键盘可达 | Tab 能聚焦，Enter 能触发 | minor |
| 9.4 | 图片 / icon 是否有 alt / aria-label | 关键图无遗漏 | minor |

> 完整无障碍走查请用 access Skill。

#### 类别 10：与 Brief 一致性（仅当读到 brief context）

| # | 检查项 | 通过标准 | 严重度 |
| --- | --- | --- | --- |
| 10.1 | 设计是否服务于 `brief.business_goal` | 主路径直接通向业务目标 | major |
| 10.2 | 设计是否覆盖 `brief.user` 描述的核心场景 | 主用户的主任务可一气呵成 | major |
| 10.3 | 是否实现了 `brief.strategy_dimensions` 中声明的策略 | 每个维度的 thesis 都能在设计里观察到 | major |
| 10.4 | 是否做了 `brief.out_of_scope` 中声明不做的内容 | 完全不出现 | blocker |
| 10.5 | 设计标准（`brief.design_criteria`）是否可观察验证 | 定量标准能在交付物上度量；定性标准有对应表现 | major |

> 没有 brief context 时跳过本类别，并在最终报告里注明"未读到 Brief，未做一致性检查"。

---

### Step 4 — 输出走查报告 + 双通道 Context

#### 4.1 报告格式（输出到对话）

按以下结构输出 Markdown 报告：

```markdown
# 设计走查报告

**走查目标**：[target]
**走查时间**：[generated_at]
**走查模式**：自动走查 / 清单模式

## 总览

| 严重度 | 数量 |
| --- | --- |
| 🔴 Blocker | N |
| 🟠 Major | N |
| 🟡 Minor | N |
| ✅ Pass（默认通过未列） | — |

## Findings（按严重度排序）

### 🔴 Blocker
1. **[类别 X.Y]** [description]
   - 出现位置：[location]
   - 修复建议：[suggestion]

### 🟠 Major
（同上格式）

### 🟡 Minor
（同上格式）

## 修复优先级建议

- 必须修复（Blocker + Major 中影响主流程的项）：N 项
- 建议修复（其他 Major + 影响一致性的 Minor）：N 项
- 可延后（不影响功能的 Minor）：N 项
```

#### 4.1.1 报告文件保存（必做）

将上述 Markdown 报告**同时保存为文件**：

```
spark-output/check/[project-slug]-走查报告.md
```

目录不存在时先创建。此文件供团队归档 / 离线查阅，与 `spark-output/context/check.json` 是互补关系（JSON 供链路消费，Markdown 供人阅读）。

⛔ **禁止保存到项目根目录**（如 `Check-设计走查报告.md`），必须统一归入 `spark-output/check/` 目录下。

#### 4.2 双通道 Context 输出

按 [chain-protocol.md](../../chain-protocol.md) §2.1 v1.1 智能适配规则：

**Step 1 — 写盘到 `spark-output/context/check.json`**（必做，主持久化通道；目录不存在先创建）。写入以下完整 JSON：

```
{
  "skill": "check",
  "generated_at": "<ISO8601>",
  "project_name": "<from brief or asked>",
  "target": "<flow 名 / 文件路径列表>",
  "findings": [
    {
      "category": "flow-continuity|ia|components|visual-hierarchy|edge-states|copy|responsive|feedback|accessibility|brief-consistency",
      "severity": "blocker|major|minor",
      "description": "<问题描述>",
      "suggestion": "<修复建议>",
      "location": "<文件路径或屏幕名>"
    }
  ],
  "summary": {
    "blocker": 0,
    "major": 0,
    "minor": 0,
    "pass": 0
  }
}
```

> ⚠️ **summary 字段自动 derive 规则（强制）**：`blocker/major/minor` = 对 `findings` 按 `severity` 分组计数；`pass` = 10 个 category 中未出现任何 finding 的数量。**禁止手写估算**——必须从 findings 数组 programmatic 计算得出。若发现 summary 与 findings 不一致，以 findings 数组为准重新计算。

**category 字段必须使用以下 10 个英文 enum 值之一**（中文 label 仅在 Markdown 报告本地化展示，JSON 用英文便于程序消费）：

| Enum 值 | 中文 label |
| --- | --- |
| `flow-continuity` | 链路通畅性 |
| `ia` | 信息架构 |
| `components` | 组件使用 |
| `visual-hierarchy` | 视觉层级 |
| `edge-states` | 异常态覆盖 |
| `copy` | 内容文案 |
| `responsive` | 响应式 / 多端 |
| `feedback` | 反馈与交互 |
| `accessibility` | 无障碍基础 |
| `brief-consistency` | 与 Brief 一致性 |

**Step 2 — chat 输出紧凑 marker**（必做，⛔ **不要在 chat 内重复输出 Step 1 的完整 JSON**）：

```
<!-- spark-context:check ref="spark-output/context/check.json" -->
Check 已保存：project=[project_name]，target=[flow 名]，共 [N] findings（blocker [n] / major [n] / minor [n]）
<!-- /spark-context:check -->
```

**降级 fallback**：若 Step 1 写盘失败（chat-only 平台），输出完整 JSON marker（无 ref 属性，marker 之间放裸 JSON）作为唯一持久化通道。

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

---

### Handoff 提示（必输出）

> **协议**：按 [`_shared/next-skill.md`](../../_shared/next-skill.md) 三层结构模板输出；前 5 候选由 `_shared/skill-graph.json` 的依赖图算法实时算（done ⊆ ready，按 next_hint.preferred → alternatives → 同阶段 → anchor → fan-out 排序），优先建议从 `_shared/skill-graph.json#skills[id="check"].next_hint` 读取。

**首行模板**：`✅ 设计走查 已完成，10 类自查发现 Blocker / Major / Minor 已分级。`

**快捷修复提示**（首行之后、候选清单之前，独立成段）：

当 findings 中存在 blocker 或 major 级别问题时，输出：

```
🔧 发现 [blocker 数 + major 数] 个需修复的问题。输入「修复」我将根据上方建议逐条修改源文件；输入「跳过」直接进入下一步。
```

- 用户说"修复"→ 按 severity 从高到低，逐条 Read 目标文件 → Edit 应用 suggestion → 完成后输出简表
- 用户说"跳过"或继续其他指令 → 正常进入 Handoff 候选
- 若 findings 全部为 minor → 不输出此提示，直接进入候选清单

**本 Skill 的 `next_hint`**（来自 skill-graph.json，**不可在此 SKILL.md 内硬编码覆盖**）：

- **preferred**：`/qa`
- **优先理由**：自检发现的 Blocker 已修，进 QA 做交付前还原度验收。
- **alternatives**：`/edge` (走查发现状态覆盖不全) · `/access` (走查触发了 WCAG 合规需要专项核查)
- **emoji**：✅

**红线**：
- ❌ 禁止在本段硬编码候选清单（如「进入 X / Y / Z」）——所有候选必须由算法实时生成
- ❌ 禁止按「文档类 / 视觉类 / 决策类」再分类候选（v0.5.5 起，分类已折叠进 next_hint.alternatives）
- ❌ 禁止与「更新链路面板」段合并——两段必须各自独立成段，中间空一行
- ❌ 禁止漏第 2 行候选清单——即使候选只有 1 个、或为空（终端节点）也要写出来

---

## 自定义规则（进阶）

如果项目有自己的设计规范文档（`spark-output/rules.md` 或 `design-guidelines.md`），Skill 在 Step 0 后会尝试读取，将其规则追加到对应类别的检查项中。规则文件格式：

```markdown
## [类别名]
- [检查项描述]：[通过标准]，severity: [blocker|major|minor]
```

未提供规则文件时，仅用本 Skill 的 10 类默认清单。

---

## 已知限制

- 本 Skill 不做"是否好看"的主观判断（请用 Pitch）
- 不做前端实现还原度核查（请用 QA Skill）
- 不做完整 WCAG 无障碍审计（请用 Access Skill）
- 不做可用性测试（请用 Test Skill）
- Mode B 清单模式下，AI 给出的判断带有主观性，建议结合人工评审

---

## 与兄弟 Skill 的边界（v0.4.0 补充）

| | Check（本 Skill） | Access | QA | Test（未来） |
| --- | --- | --- | --- | --- |
| 验证对象 | **设计稿本身** | 设计稿的合规性 | **前端实现还原度** | 真实用户行为 |
| 验证维度 | 10 类基础体检（IA / 一致性 / 反馈 / Edge / 性能感知等） | WCAG 2.1 AA/AAA 50+ 项 | 间距 / 颜色 / 交互 / 响应式 9 维 | 任务完成率 / 出错率 |
| 触发时机 | 设计完成后、Handoff 前 | 合规场景、政府/医疗/金融 | 前端实现完成后 | 上线后 / 灰度 |
| 输出 | findings 清单（按严重度） | WCAG 合规报告 + 法律风险 | deviations（差异点） | 测试结论 + 建议 |
| 是否需要用户 | ❌ | ❌（Audit 类） | ❌ | ✅ |

**典型衔接**：Flow Web/Mobile（出稿）→ **Check（自检 10 类）** → Access（合规场景再走 WCAG）→ Handoff → QA（验收实现）→ Test（用户验证）。

**Check Mode C 定向验证模式**：当 chain 完整时（brief + stories + journey），Check 自动切到「上游 → 下游一致性核对」，输出 strategy_dimensions / acceptance_criteria / repair_strategies 三张表，避免漏项目特定决策。

---

## 质量标准

1. **覆盖 10 类基础维度**：IA / 一致性 / 反馈 / 错误处理 / Edge / 性能感知 / 信息层级 / 文案 / 可点性 / 可达性入口；缺一类需明确标注"本次跳过 X 维度"
2. **每条 finding 必须含 severity + 修复建议**：blocker / major / minor 三档，不能只指出问题不给方向
3. **优先级排序输出**：findings 按 severity × 影响范围排序，让设计师能聚焦最关键的修复
4. **Mode C 必须做一致性核对**：上游有 brief / stories / journey 时，必须输出三张核对表
5. **不替代 Access 的完整 WCAG 审计**：Check 的可达性维度是抽样，合规场景必须跑 Access
6. **不替代 QA**：Check 走查设计稿，不验证前端实现 —— 那是 QA 的活

## 红线规则

1. **不下"设计很差"的整体评价**：只给具体维度的具体 finding，禁止主观情绪化评判
2. **不替代用户测试**：Check 是设计师自检，不能代替"真用户用了发现问题"
3. **不漏关键 finding**：Mode C 下若发现 brief 的 strategy_dimensions 在设计中缺失，必须标 blocker，禁止隐瞒
