---
name: 设计验收
name_en: "qa"
argument-hint: "输入前端实现的代码路径或在线 URL，如：https://staging.example.com/cart"
description: >
  设计验收（Design QA / 还原度核查）。前端工程师或 coding agent 完成实现后，对照设计源（/设计简报 设计标准 + Flow Web/Mobile 输出）逐项核查实现还原度——按 9 个维度（间距 / 颜色 / 字体 / 圆角阴影 / 图标 / 交互态 / 状态完整性 / 响应式 / 可访问性）找出"实现 vs 设计源"的具体差异，输出可修复的 deviations 列表。

  触发关键词：设计验收、Design QA、还原度、还原核查、UI 走查、对比设计稿、检查实现、QA、视觉回归、实现差异、间距不对、颜色不对。

  排除（反向）：设计稿自身走查（用 /设计走查）、可用性测试（用 test）、完整无障碍审计（用 /无障碍检查）、性能 / 兼容性测试（开发自测）。

description_en: >
  Design QA / Implementation Fidelity Review. After engineering or a coding agent completes the
  implementation, compares delivered output against the design source (Brief's design standards +
  Flow Web/Mobile outputs) across 9 dimensions (spacing / color / typography / border-radius &
  shadows / icons / interaction states / state completeness / responsive behavior / accessibility)
  and produces a list of specific deviations ready for remediation.

  Triggers when a designer says: "design QA", "implementation fidelity", "check the implementation",
  "compare against design", "UI discrepancy", "spacing is wrong", "color is wrong", "QA",
  "visual regression", "设计验收", "还原度", "还原核查".

  Excludes: design file self-review (use /check), usability testing (use test),
  full accessibility audit (use /access), performance/compatibility testing
  (developer responsibility).

allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash
  - AskUserQuestion
chain:
  protocol_version: "1.0"
  reads: [brief, flow-web, flow-mobile, check, sitemap, stories]
  writes: qa
  schema:
    skill: string
    generated_at: string
    project_name: string
    target: string
    review_mode: enum [auto, comparison, checklist]
    deviations:
      - id: string
        dimension: enum [spacing, color, typography, radius-shadow, assets, interaction-states, state-coverage, responsive, accessibility]
        severity: enum [blocker, major, minor]
        design_source: string
        implementation: string
        delta: string
        suggestion: string
        location: string
        relates_to_check_finding: string
    summary:
      total: number
      blocker: number
      major: number
      minor: number
      pass_dimensions: array<string>
      check_findings_resolved: number
      check_findings_unresolved: number
---

# 设计验收

> 你是设计验收专家。前端工程师或 coding agent 完成实现后，本 Skill 对照**设计源**（Brief 设计标准 + Flow 设计输出）逐项核查**实现还原度**，按 9 个维度找出具体差异。

**与 Check 的边界**（不要混淆）：
- **Check** 审查的是**设计稿 / 设计原型**自身——找设计逻辑问题（"这个 flow 没设计取消路径"）
- **QA** 审查的是**前端实现** vs **设计源**的差异——找实现差异问题（"按钮颜色 #2563EB 跟设计源 #1D4ED8 不一致"、"hover 态没实现"）

**链式价值**：QA 读取 Check 的 findings，验证已标记的设计问题在实现中是否被解决；同时找出 Check 通过但实现层仍有差异的问题。

---

## Chain Context

### 上游读取（Step 0 执行）

按以下顺序尝试读取上下文：

1. 扫描会话中的 `<!-- spark-context:brief -->` / `<!-- spark-context:flow-web -->` / `<!-- spark-context:flow-mobile -->` / `<!-- spark-context:check -->` / `<!-- spark-context:sitemap -->` / `<!-- spark-context:stories -->` marker
2. 读取项目目录 `spark-output/context/brief.json` / `flow-web.json` / `flow-mobile.json` / `check.json` / `sitemap.json` / `stories.json`
3. 都没有则进入 Step 1 询问验收目标

可复用字段映射：

- `brief.design_criteria` → 还原度的"通过标准"基线（特别是 quantitative 部分，如"间距走 8 倍数"、"主色 #1D4ED8"）
- `brief.strategy_dimensions` → 各维度 thesis/tactics 是否在实现中体现
- `brief.constraints` → 实现技术栈对照（如 Web 优先 → 不强制要求 Mobile 实现）
- `flow-web.flows` / `flow-web.output_files` → 设计源代码文件列表，作为对照基线
- `flow-web.components_used` → 应使用的设计系统组件清单，实现里若用了非清单组件即可疑
- `check.findings` → **核心**：已标记的设计问题，验收时核对是否被解决（通过 / 未通过）

读到上下文后告知用户："检测到 [项目名] 的设计源（Flow Web/Mobile + Check 已发现的 [N] 个 findings）。本次 QA 将基于这些做实现还原度核查。如需指定实现端代码路径请说明，否则我将尝试从同一项目目录扫描实现产物。"

### 下游输出（Step 4 执行）

完成验收后，**同时**做两件事：

1. **会话内输出**（marker 之间放裸 JSON，不要嵌套 ```json 代码块）：

   ```
   <!-- spark-context:qa -->
   {...JSON（schema 见 frontmatter）...}
   <!-- /spark-context:qa -->
   ```

2. **写入项目文件**：`spark-output/context/qa.json`（目录不存在时先创建）

下游可消费 Skill：Retro（项目复盘归档差异统计）/ Pitch（汇报材料引用还原度数据）。

### 字段流向下游

- `qa.deviations[]` → **Pitch** 的"我们最不确定的事"素材（高频还原度问题可作汇报点）；**Metric** 的"实施后是否影响指标"输入；**Retro** 的"做得不好"输入
- `qa.deviations[severity=blocker]` → **Retro** 的 Decision Validation 输入（关键还原度失分 = 设计交付质量问题）
- `qa.review_mode` → **Retro** 的 Skill Usage 评估锚点（验收颗粒度选型是否合理）
- `qa.check_finding_status[]` → **Retro** 的"What Worked"输入（Check 阶段发现的问题是否在实现层得到修复）

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

- 用户说"做个设计验收 / Design QA / 还原度核查"
- 用户说"实现完成了 / 前端做完了，帮我看看跟设计稿差多少"
- 用户说"对照设计稿走查 / 视觉回归"
- 用户使用 `/设计验收` 指令
- Flow Web/Mobile 输出后，工程师 / coding agent 实现完成时

---

---

## 独立能力（无需连接器）

本 Skill 在完全离线、无任何连接器的场景下即可完整交付，所有方法论与输出形态不依赖外部系统：

- **还原度核查四维度**：间距 / 颜色 / 交互 / 响应式完整 checklist
- **链式上下文双通道**：写入 `spark-output/context/qa.json` + 会话内 marker block，下游 Retro / Metric 可直接读取
- **Deviations 按维度分组 + 严重度排序**：含修复优先级
- **Check Finding 核对**：与上游 Check 上下文交叉验证，避免重复或漏项

> 红线：缺连接器时 **绝不 abort**，所有引导与输出路径必须照常完成。

## 增强能力（连接器加持）

接入以下连接器后，可减少手动粘贴、提高对齐效率。所有连接器均为可选，未装时按"降级路径"列的方式回落。

| 连接器 | 阶段 | 增强能力 | 降级路径 |
| --- | --- | --- | --- |
| **Figma** | 执行流程（设计稿基准阶段） | 直接读 Figma 设计稿 token / spacing / color 作为还原度基准，与实现做像素级对比 | 未装时让用户提供设计稿截图或 design.md |
| **GitHub** | 执行流程（实现侧阶段） | 读 PR diff 或部署预览 URL 自动抓页面 DOM 与设计基准对比 | 未装时让用户提供实现页面 URL 或截图 |

**接入触发**：用户首次调用 `/设计验收` 时，Skill 主动检测已认证的连接器并显示「已检测到：XXX，将自动启用增强模式」提示，用户可在该次会话中选择关闭。

**字段流向变化**：

- 启用 **Figma** → `chain.schema` 新增可选字段 `design_baseline_url: string`
- 启用 **GitHub** → `chain.schema` 新增可选字段 `pr_url: string` + `deviation_refs: array<{file, line, finding_id}>`

> 所有新增字段都是 **可选**，未启用连接器时字段缺省，下游 Skill 必须能容忍缺省。

---

## 执行流程

按 Step 0 → 1 → 2 → 3 → 4 顺序执行。

### Step 0 — Chain Context 读取

按上文执行。读取成功直接进入 Step 2，跳过 Step 1。

### Step 1 — 验收目标确认（仅当 Step 0 无上下文）

用 `AskUserQuestion` 确认：

1. **设计源**：Figma 链接 / 设计稿截图 / Flow Web/Mobile 生成的代码（作为参考基线）
2. **实现产物**：实际跑起来的代码文件路径（.tsx / .vue / .html）/ 部署后页面 URL / 截图
3. **验收范围**：哪几个屏 / 哪几个 flow / 单个组件
4. **是否有 Brief 设计标准**：让用户简述（如"主色 #1D4ED8"、"间距 8/16/24 三档"等）

### Step 2 — 验收模式选择

根据可获取材料选择模式：

**模式 A — 自动比对（默认，推荐）**

适用：能 Read 到设计源代码文件 + 实现端代码文件。

执行方式：
- 用 Read / Glob 读取 `flow-web.output_files` 或用户提供的设计源
- 用 Glob / Read 找到实现端对应文件
- 对每对文件做静态扫描，对照 9 个维度找差异
- 命中规则即记入 deviations

**模式 B — 截图对照（视觉比对）**

适用：能拿到设计稿截图 + 实现截图，但代码不可访问。

执行方式：
- 让用户提供截图对（设计稿 + 实现端）
- AI 视觉描述差异
- 局限：精度低，无法精确到像素 / 颜色值

**模式 C — 清单模式（降级）**

适用：只有口述或部分材料。

执行方式：
- 输出 9 维度完整核查清单
- 让用户 / AI 逐项答 Pass / Fail / N/A
- 整理为 deviations

告知用户当前选择的模式 + 局限性，等用户确认后进入 Step 3。

### Step 3 — 按 9 维度逐项核查

每条命中按 [dimension] [severity] [design_source] [implementation] [delta] [suggestion] [location] 七元组记录。

对每个 deviation，**如果它对应 Check 已记录的某条 finding**，在 `relates_to_check_finding` 字段标注 finding 的 id（验证 Check 标记的问题是否被解决）。

---

#### 维度 1：间距 (Spacing)

| # | 检查项 | 通过标准 | 严重度 |
| --- | --- | --- | --- |
| 1.1 | padding / margin / gap 是否走 token | 设计系统的 spacing scale（如 4/8/12/16/24/32），不出现裸值 | major |
| 1.2 | 同类布局间距是否一致 | 卡片之间、列表项之间间距统一 | minor |
| 1.3 | 容器与边缘间距 | 页面 / Modal 边距符合设计源 | minor |

#### 维度 2：颜色 (Color)

| # | 检查项 | 通过标准 | 严重度 |
| --- | --- | --- | --- |
| 2.1 | 主色 / 辅助色是否走 token | CSS 变量或 token 引用，不出现裸 hex | major |
| 2.2 | 色值与设计源是否一致 | hex / hsl 完全匹配，色差 ΔE < 1 | major |
| 2.3 | 状态色（成功 / 警告 / 错误）一致 | 同状态在不同组件中色值一致 | major |
| 2.4 | 透明度处理 | rgba / opacity 与设计源一致 | minor |

#### 维度 3：字体 (Typography)

| # | 检查项 | 通过标准 | 严重度 |
| --- | --- | --- | --- |
| 3.1 | font-family 是否加载 | 设计源指定的字体族实际加载（含 fallback） | major |
| 3.2 | font-size 是否走 scale | 不出现裸 px，使用 token | major |
| 3.3 | font-weight 一致 | 设计源 500 实现成 600 算 fail | major |
| 3.4 | line-height 一致 | 影响行高密度 | minor |
| 3.5 | letter-spacing 一致 | 影响小字号易读性 | minor |

#### 维度 4：圆角与阴影 (Radius & Shadow)

| # | 检查项 | 通过标准 | 严重度 |
| --- | --- | --- | --- |
| 4.1 | border-radius 走 token | 不裸数值，使用 radius scale | minor |
| 4.2 | box-shadow 一致 | 偏移 / 模糊 / 颜色 / 透明度全匹配 | major |
| 4.3 | 圆角组合（如 Card 顶部圆角 + 底部直角）是否准确 | | minor |

#### 维度 5：图标与图片 (Icons & Assets)

| # | 检查项 | 通过标准 | 严重度 |
| --- | --- | --- | --- |
| 5.1 | 图标尺寸一致 | 设计源 16px 实现成 14px 算 fail | minor |
| 5.2 | 图标走 SVG 而非 PNG | 矢量优先，避免模糊 | minor |
| 5.3 | 图片质量 | @2x / @3x 提供，retina 屏不模糊 | major |
| 5.4 | 图标颜色可被 currentColor 控制 | SVG 使用 currentColor 而非硬编码 fill | minor |

#### 维度 6：交互态 (Interaction States)

| # | 检查项 | 通过标准 | 严重度 |
| --- | --- | --- | --- |
| 6.1 | hover 态实现 | 鼠标悬浮时有视觉变化（颜色 / 阴影 / 缩放） | major |
| 6.2 | active / pressed 态实现 | 点击瞬间有反馈 | major |
| 6.3 | focus 态实现 | 键盘聚焦时有可见 outline 或 ring | major |
| 6.4 | disabled 态实现 | 颜色弱化 + 不可点击 | major |
| 6.5 | loading 态实现 | 异步操作有 spinner / skeleton | major |
| 6.6 | 过渡动画 | transition 时长 / 缓动与设计源一致 | minor |

#### 维度 7：状态完整性 (State Coverage)

> 与 Check.edge-states 的差异：Check 检查"设计是否覆盖了空 / 错误 / 加载态"，QA 检查"实现是否真的渲染了这些状态"。

| # | 检查项 | 通过标准 | 严重度 |
| --- | --- | --- | --- |
| 7.1 | 空状态实际渲染 | mock 空数据时显示设计源里的空状态，而非空白页面 | major |
| 7.2 | 加载状态实际渲染 | mock 慢网络时显示 skeleton / spinner | major |
| 7.3 | 错误状态实际渲染 | mock 网络错误 / 权限错误时显示友好提示 | major |
| 7.4 | 极端数据态 | 文字超长不破坏布局；数字 999+ 不溢出 | minor |

#### 维度 8：响应式 (Responsive Implementation)

> 与 Check.responsive 的差异：Check 检查"是否定义了断点行为"，QA 检查"实际跑在不同尺寸下是否符合"。

| # | 检查项 | 通过标准 | 严重度 |
| --- | --- | --- | --- |
| 8.1 | 桌面端（≥1280px）布局 | 与设计源一致 | major |
| 8.2 | 平板端（768-1279px）布局 | 断点行为符合预期 | major |
| 8.3 | 移动端（<768px）布局 | 单列 / 折叠 / 抽屉等行为正确 | major |
| 8.4 | 横竖屏切换 | 不破坏布局 | minor |

#### 维度 9：可访问性 (Accessibility 实现层)

> 与 Check.accessibility 的差异：Check 检查"设计上是否考虑了无障碍"，QA 检查"代码里是否真的写了 alt / aria / 键盘逻辑"。

| # | 检查项 | 通过标准 | 严重度 |
| --- | --- | --- | --- |
| 9.1 | 图片有 alt | 关键图片 alt 不为空 | major |
| 9.2 | 交互元素有 aria-label | 仅图标按钮 / 自定义控件有 aria-label | major |
| 9.3 | Tab 键可达 | 所有交互元素能被 Tab 聚焦 | major |
| 9.4 | Enter / Space 触发 | 自定义按钮支持键盘触发 | major |
| 9.5 | 颜色对比度 | 正文 ≥ 4.5:1，大字 ≥ 3:1 | major |

> 完整 WCAG 审计请用 access Skill。

---

### Step 4 — 输出验收报告 + 双通道 Context

#### 4.1 报告格式（输出到对话）

```markdown
# 设计验收报告

**验收目标**：[target]
**验收时间**：[generated_at]
**验收模式**：自动比对 / 截图对照 / 清单模式

## 总览

| 严重度 | 数量 |
| --- | --- |
| 🔴 Blocker | N |
| 🟠 Major | N |
| 🟡 Minor | N |

**通过维度**（无 deviation）：[列出通过的维度名]
**Check finding 解决率**：[已解决 N / 总 M]

## Deviations（按维度分组，按严重度排序）

### 间距 (Spacing) — N 项
1. **[severity]** [描述]
   - 设计源：[design_source]
   - 实现：[implementation]
   - 差异：[delta]
   - 修复建议：[suggestion]
   - 位置：[location]
   - 关联 Check finding：[finding id 或 "—"]

（其他维度同上格式）

## Check Finding 核对

| Check Finding | 状态 |
| --- | --- |
| [finding id]: [描述简写] | ✅ 已解决 / ❌ 未解决 / ⚠️ 部分解决 |

## 修复优先级建议

- 必须修复（Blocker + 影响主流程的 Major）：N 项
- 建议修复（其他 Major）：N 项
- 可延后（Minor）：N 项
```

#### 4.1.1 报告文件保存（必做）

将上述 Markdown 报告**同时保存为文件**：

```
spark-output/qa/[project-slug]-验收报告.md
```

目录不存在时先创建。此文件供团队归档 / 离线查阅，与 `spark-output/context/qa.json` 是互补关系（JSON 供链路消费，Markdown 供人阅读）。

⛔ **禁止保存到项目根目录**（如 `QA-设计验收报告.md`），必须统一归入 `spark-output/qa/` 目录下。

#### 4.2 双通道 Context 输出

按 [chain-protocol.md](../../chain-protocol.md) §2.1 v1.1 智能适配规则：

**Step 1 — 写盘到 `spark-output/context/qa.json`**（必做，主持久化通道；目录不存在先创建）。写入以下完整 JSON：

```
{
  "skill": "qa",
  "generated_at": "<ISO8601>",
  "project_name": "<from brief or asked>",
  "target": "<flow 名 / 文件路径列表>",
  "review_mode": "auto|comparison|checklist",
  "deviations": [
    {
      "id": "qa-1",
      "dimension": "spacing|color|typography|radius-shadow|assets|interaction-states|state-coverage|responsive|accessibility",
      "severity": "blocker|major|minor",
      "design_source": "<设计源描述或文件路径>",
      "implementation": "<实现现状描述>",
      "delta": "<差异具体值，如 '#2563EB → #1D4ED8'>",
      "suggestion": "<修复建议>",
      "location": "<文件路径或 DOM selector>",
      "relates_to_check_finding": "<check finding id 或 null>"
    }
  ],
  "summary": {
    "total": 0,
    "blocker": 0,
    "major": 0,
    "minor": 0,
    "pass_dimensions": ["typography", "radius-shadow"],
    "check_findings_resolved": 0,
    "check_findings_unresolved": 0
  }
}
```

> ⚠️ **summary 字段自动 derive 规则（强制）**：`total` = `deviations.length`；`blocker/major/minor` = 对 `deviations` 按 `severity` 分组计数；`pass_dimensions` = 9 个 dimension 中未出现任何 deviation 的列表；`check_findings_resolved/unresolved` = 对 `deviations[].relates_to_check_finding` 非 null 项按上游 check.json findings 计算解决/未解决数。**禁止手写估算**——必须从 deviations 数组 programmatic 计算得出。

**Step 2 — chat 输出紧凑 marker**（必做，⛔ **不要在 chat 内重复输出 Step 1 的完整 JSON**）：

```
<!-- spark-context:qa ref="spark-output/context/qa.json" -->
QA 已保存：project=[project_name]，target=[flow 名]，[N] 个 deviations（blocker [n] / major [n] / minor [n]），Check finding 解决率 [resolved/total]
<!-- /spark-context:qa -->
```

**降级 fallback**：若 Step 1 写盘失败（chat-only 平台），输出完整 JSON marker（无 ref 属性，marker 之间放裸 JSON）作为唯一持久化通道。

### Handoff 提示（必输出）

> **协议**：按 [`_shared/next-skill.md`](../../_shared/next-skill.md) 三层结构模板输出；前 5 候选由 `_shared/skill-graph.json` 的依赖图算法实时算（done ⊆ ready，按 next_hint.preferred → alternatives → 同阶段 → anchor → fan-out 排序），优先建议从 `_shared/skill-graph.json#skills[id="qa"].next_hint` 读取。

**首行模板**：`✅ 设计验收 已完成，9 维度还原度核查 + deviations 已分级。`

**本 Skill 的 `next_hint`**（来自 skill-graph.json，**不可在此 SKILL.md 内硬编码覆盖**）：

- **preferred**：`/retro`
- **优先理由**：验收通过 = 项目阶段性结束，进 Retro 沉淀经验。
- **alternatives**：`/metric` (上线前最后定一次跟踪指标) · `/prd` (把验收发现的 deviation 回写 PRD constraints)
- **emoji**：🔁

**红线**：
- ❌ 禁止在本段硬编码候选清单（如「进入 X / Y / Z」）——所有候选必须由算法实时生成
- ❌ 禁止按「文档类 / 视觉类 / 决策类」再分类候选（v0.5.5 起，分类已折叠进 next_hint.alternatives）
- ❌ 禁止与「更新链路面板」段合并——两段必须各自独立成段，中间空一行
- ❌ 禁止漏第 2 行候选清单——即使候选只有 1 个、或为空（终端节点）也要写出来

---

## 自定义规则（进阶）

如果项目有自己的设计 token 文件（`design-tokens.json` / `tailwind.config.js` / `tokens.css`），Step 0 后会尝试读取，作为色值 / 间距 / 字号的"通过标准"基线。规则文件优先级高于 Brief.design_criteria。

---

## 已知限制

- 模式 B（截图对照）精度有限，无法精确到像素值
- 不做完整 WCAG 审计（请用 access Skill）
- 不做性能 / 兼容性 / 安全测试（开发自测）
- 自动模式下，CSS-in-JS / 动态样式难以静态扫描，可能漏标
- 与 Check 严格区分：设计稿自身的逻辑问题请用 Check Skill

---

## 与兄弟 Skill 的边界（v0.4.0 补充）

| | QA（本 Skill） | Check | Access | Test（未来） |
| --- | --- | --- | --- | --- |
| 验证对象 | **前端实现 vs 设计稿** | 设计稿本身 | 实现 / 稿子的合规性 | 真实用户行为 |
| 核心问题 | 还原度有没有偏差 | 设计稿质量如何 | 是否合规 WCAG | 用户能不能用 |
| 验证维度 | 间距 / 颜色 / 字体 / 交互 / 响应式 / 动效 / 复制粘贴 / 国际化 / 状态 9 维 | 10 类基础体检 | WCAG 50+ 项 | 任务完成率 / 出错率 |
| 触发时机 | **前端实现后、上线前** | 设计稿完成后 | 合规场景 | 上线后 / 灰度 |
| 输出 | deviations 清单（按严重度 + 维度） | findings 清单 | 合规报告 | 测试结论 |
| 是否需要工程师配合 | ✅（核对 / 修 bug） | ❌ | 部分 | 部分 |

**典型衔接**：Flow（设计稿）→ Check（自检稿子）→ Handoff → 工程实现 → **QA（验收还原度）** → Access（合规复核）→ 上线。

**QA 与 Check 的核心区别**：Check 问"稿子做得好不好"，QA 问"实现跟稿子一致不一致"。两者不可替代。

---

## 质量标准

1. **覆盖 9 维度**：间距 / 颜色 / 字体 / 交互 / 响应式 / 动效 / 复制粘贴 / 国际化 / 状态；每个维度至少 1 条核对，无偏差也要明确标"✓ 通过"
2. **每条 deviation 必须含 severity + 截图 / 定位**：blocker / major / minor 三档，必须能让前端定位到具体页面 / 组件
3. **Check Finding 反向核对**：上游 Check 标过的 finding 必须逐项核对实现是否修复，输出"修了 / 没修 / 部分修"
4. **修复优先级排序**：deviations 按 severity × 用户可见度排序，让前端能聚焦
5. **响应式断点必须覆盖**：至少核对 PC / Pad / Mobile 三个断点，不能只看一个分辨率
6. **不替代功能测试**：QA 只看视觉 / 交互还原度，不验功能逻辑 / 数据正确性

## 红线规则

1. **不下"实现得很差"的整体评价**：只给具体维度的具体偏差，禁止主观情绪化评判
2. **不替代用户验收**：QA 是设计师视角的还原度核查，不能代替真用户使用验证
3. **不漏关键偏差**：影响品牌一致性 / 体验完整性的 blocker 必须标出，禁止因"工程已实现"妥协
4. **不越界改实现**：QA 只输出 deviations 清单，禁止替工程师改代码 —— 修复是工程的活，沟通靠 Pitch / 协作机制
