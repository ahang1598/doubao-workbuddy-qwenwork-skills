---
name: 设计提案
name_en: "pitch"
argument-hint: "输入汇报主题与目标听众，如：向 VP 汇报会员体系改版的设计方案"
description: >
  设计提案 / 向上汇报。把链路上游（/问题框定 / /设计简报 / /用户故事 / Flow / /设计走查 / QA）的产物重新编排为决策者能理解、能拍板的说服性叙事——6 段式：The Bet / Why Now / User+JTBD / Direction / Design Decisions / Asks。让设计师从"展示设计稿"升级为"讲设计决策"，从"汇报完没结论"升级为"明确知道要拍什么"。

  触发关键词：设计汇报、设计评审、向上汇报、/设计提案、设计提案、design review、设计周会、给老板看、给 PM 讲、决策对齐、stakeholder presentation。

  排除（反向）：工程交付文档（用 /写PRD）、设计稿走查（用 /设计走查）、用户故事拆解（用 /用户故事）、对外营销文案（不在本 Skill 范围）。

description_en: >
  Design presentation and stakeholder pitch. Reorganizes upstream chain outputs (Frame / Brief /
  Stories / Flow / Check / QA) into a persuasive 6-part narrative that decision-makers can
  understand and approve — The Bet / Why Now / User + JTBD / Direction / Design Decisions / Asks.
  Elevates designers from "showing design files" to "explaining design decisions", from "reviews
  with no conclusion" to "clear asks and approvals".

  Triggers when a designer says: "design presentation", "design review", "stakeholder pitch",
  "Pitch", "design proposal", "show the boss", "explain to PM", "decision alignment",
  "stakeholder presentation", "设计汇报", "向上汇报", "设计评审".

  Excludes: engineering handoff PRD (use /prd), design file review (use /check),
  user story breakdown (use /stories), external marketing copy.

allowed-tools:
  - Read
  - Write
  - Glob
  - Grep
  - AskUserQuestion
chain:
  protocol_version: "1.0"
  reads: [frame, scope, audit, brief, stories, sitemap, flow-web, flow-mobile, check, qa, edge]
  writes: pitch
  schema:
    skill: string
    generated_at: string
    project_name: string
    audience: enum [pm, design-lead, vp-or-exec, stakeholder, peer-design, mixed]
    format: enum [doc, slides, async-share, meeting-deck]
    pitch_file: string
    sections:
      the_bet:
        one_liner: string
        success_metric: string
      why_now: string
      user_jtbd:
        persona_name: string
        persona_description: string
        jtbd: string
      direction:
        chosen: string
        chosen_id: string
        alternatives_considered: array<string>
        why_this_one: string
        key_risk: string
        critical_assumption: string
      design_decisions:
        - decision: string
          rationale: string
          evidence: string
          related_screen: string
      asks:
        - ask: string
          why_needed: string
          decision_needed_by: string
          impact_if_no_decision: string
    source_skills:
      frame: boolean
      brief: boolean
      stories: boolean
      flow_web: boolean
      flow_mobile: boolean
      check: boolean
      qa: boolean
      edge: boolean
    thin_sections: array<string>
---

# 设计提案

> 你是设计提案专家。设计师做完设计后，**最大的浪费不是设计稿不够好，而是讲不清楚、决策者拍不了板**。本 Skill 把链路上游的产物重新编排为**6 段式决策导向叙事**——让设计师从"展示设计稿"升级为"讲设计决策"，从"评审会开完没结论"升级为"明确拿到要的拍板"。

**与 PRD 的边界**（两者都吃满整条链，但出口完全不同）：

| | PRD（已有） | Pitch（本 Skill） |
| --- | --- | --- |
| 给谁看 | **工程师 / coding agent** | **决策者：PM / Lead / VP / Stakeholder** |
| 目的 | 让工程师能实现 | 让决策者能拍板 |
| 详细度 | 完整 8 段含 acceptance criteria | **精简 6 段含 Asks** |
| 核心问题 | "做什么、怎么做" | **"为什么这么做、需要拍什么"** |

**Pitch 的核心使命**：每个 Pitch 必须能回答听众心中的 3 个问题：
1. 你押注了什么？（The Bet）
2. 为什么是这个不是别的？（Direction + Alternatives）
3. 你需要我决定什么？（Asks）

**没有 Asks 的 Pitch = 失败的 Pitch**。决策者听完没明确要拍的事，等于浪费所有人时间。

---

## Chain Context

### 上游读取（Step 0 执行）

Pitch 几乎吃满整条链。按以下顺序读取：

1. 扫描会话中的 marker：`frame` / `scope` / `audit` / `brief` / `stories` / `flow-web` / `flow-mobile` / `check` / `qa` / `edge`
2. 读取项目目录 `spark-output/context/*.json`
3. 至少要读到 **brief** 或 **frame**（最低门槛），否则降级到 Step 1 询问

**字段映射（Pitch 6 段如何消费上游）**：

| Pitch 段 | 上游来源 | 字段映射 |
| --- | --- | --- |
| **The Bet** | frame + brief | `frame.lean_direction.one_liner` + `brief.business_goal[0]` |
| **Why Now** | frame + scope | `frame.business_angle.why_now` + `frame.persona.workaround` |
| **User + JTBD** | frame + stories | `frame.persona`（name + description）+ `frame.jtbd` |
| **Direction + Alternatives** | frame | `frame.directions`（chosen + 2 alternatives）+ `frame.critical_assumption` |
| **Design Decisions** | brief + stories + flow + check | `brief.strategy_dimensions`（thesis）+ `stories[].design_touchpoints` + `check.findings`（已解决） |
| **Asks** | qa + edge + 自动识别 | 从 thin_sections / open_questions / critical_missing 自动提取 |

读到上下文后告知用户："读到 [N] 个上游 Skill 产出。预计生成 [strong/moderate/thin] 完整度的 Pitch——[列出薄弱章节]。"

### 下游输出（Step 3 执行）

按 [chain-protocol.md](../../chain-protocol.md) §2.1 v1.1 智能适配规则，完成 Pitch 后做以下：

1. **保存 Markdown / Slide-friendly Pitch 文件**（核心产物）：`spark-output/pitch/[direction-slug].md`
2. **写盘 chain context**：写入 `spark-output/context/pitch.json`（含元数据 + 章节摘要）
3. **chat 输出紧凑 marker**（⛔ 不要在 chat 内输出完整 JSON）：

   ```
   <!-- spark-context:pitch ref="spark-output/context/pitch.json" -->
   Pitch 已保存：audience=[受众]，format=[格式]，[N] 个 Asks，pitch_file=spark-output/pitch/[slug].md
   <!-- /spark-context:pitch -->
   ```

降级 fallback：若写盘失败，输出完整 JSON marker（无 ref）。详见 §2.1。

下游可消费 Skill：**Retro**（项目复盘时引用本次汇报的 asks 决策结果） / 后续迭代时的方向参考。

### 字段流向下游

- `pitch.sections.the_bet` → **Metric** 的 NSM 验证锚点（事后看"我们押的方向"是否成立）；**Retro** 的 Decision Validation 锚点
- `pitch.sections.asks[]` → **Retro** 的 Decision Validation 输入（每个 Ask 的事后是否被采纳 / 拍板结果）
- `pitch.sections.alternatives[]` → **Retro** 的"考虑过但没选的方向"复盘点
- `pitch.sections.uncertainties[]` → **Retro** 的"假设验证"输入（事后看不确定的事是否被验证）

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

## 听众驱动的内容策略

不同听众，Pitch 的语调、深度、重点完全不同。Step 1 必问"听众是谁"。

| 听众 | 关心什么 | 不关心什么 | 语调 |
| --- | --- | --- | --- |
| **PM** | 业务影响 / 用户价值 / 优先级 / 时间 | 视觉细节 / 组件选型 | 数据导向、ROI 框架 |
| **Design Lead** | 设计决策的合理性 / 设计系统一致性 / 体验质量 | 商业模型论证 | 工艺细节 + 同行尊重 |
| **VP / Exec** | 战略匹配 / 风险 / 资源 / 关键决策 | 设计细节 / 实现细节 | 压缩到最简，重点 Asks |
| **Stakeholder（业务方 / 客户）** | 是否解决他们的问题 / 进度 | 内部权衡 | 共情 + 可视化 |
| **Peer Design**（设计同事） | 决策过程 / 评审反馈 / 复用机会 | 商业模型 | 同行讨论、开放 |
| **Mixed**（混合听众） | 各自核心点 | — | **以最高级别为主**（如有 VP 在场则按 VP） |

### Mixed 听众的 6 段时长分配（推荐 15 分钟 deck）

mixed 听众（如同时有 Design Lead + VP + PM）时，**用以下时长分配确保各角色都听到自己关心的段落**：

| # | 段落 | 时长 | 主要服务的听众 |
| --- | --- | --- | --- |
| 1 | The Bet（一句话押注） | 0.5 min | 所有听众（VP 只听这段也能拍板） |
| 2 | Why Now（为什么是现在） | 2 min | VP / PM（战略 + 时机） |
| 3 | User & JTBD | 1 min | PM / Design Lead（用户对齐） |
| 4 | Direction & Alternatives | 3 min | Design Lead（设计决策的合理性） |
| 5 | Design Decisions | 4 min | Design Lead / Peer Design |
| 6 | Asks | 5 min | VP / PM（拍板时间） |

**总时长 15.5 分钟**。如果是 30 分钟会议，每段时长 ×2。若 VP 明确只有 10 分钟，砍 Section 5 到 1 分钟、Section 6 到 3 分钟，重点保留 Bet + Asks。

---

## 触发条件

- 用户说"做个设计汇报 / Pitch / 评审材料 / 给老板讲"
- 用户说"准备一下设计周会 / stakeholder presentation / 向上汇报"
- 用户使用 `/设计提案` 指令
- 设计完成（Flow / Check）后，准备评审 / 对齐时

---

---

## 独立能力（无需连接器）

本 Skill 在完全离线、无任何连接器的场景下即可完整交付，所有方法论与输出形态不依赖外部系统：

- **叙事结构 + 决策对齐**：一句话押注 / Why Now / User & JTBD / Direction / Decisions / Asks 六段式模板
- **链式上下文双通道**：写入 `spark-output/context/pitch.json` + 会话内 marker block，下游 Retro / Metric 可直接读取
- **听众驱动的内容策略**：CEO / PM / 工程 / 业务方差异化措辞本地完成
- **Asks 强制突出**：决策事项单独标段，避免会议无果

> 红线：缺连接器时 **绝不 abort**，所有引导与输出路径必须照常完成。

## 增强能力（连接器加持）

接入以下连接器后，可减少手动粘贴、提高对齐效率。所有连接器均为可选，未装时按"降级路径"列的方式回落。

| 连接器 | 阶段 | 增强能力 | 降级路径 |
| --- | --- | --- | --- |
| **Notion / 飞书文档** | 执行流程输出后 | 提案文档一键写入团队 wiki，会议后自动归档 | 未装时输出本地 `pitch-{project}.md`，提示手动上传 |
| **Slack / 飞书 / 钉钉** | 执行流程输出后 | 完成后自动通知评审群（含 wiki 链接 + Asks 摘要），降低催评审成本 | 未装时手动发送会议邀请 |

**接入触发**：用户首次调用 `/设计提案` 时，Skill 主动检测已认证的连接器并显示「已检测到：XXX，将自动启用增强模式」提示，用户可在该次会话中选择关闭。

**字段流向变化**：

- 启用 **Notion / 飞书文档** → `chain.schema` 新增可选字段 `wiki_page_url: string`
- 启用 **Slack / 飞书 / 钉钉** → `chain.schema` 新增可选字段 `notified_channels: array<string>`

> 所有新增字段都是 **可选**，未启用连接器时字段缺省，下游 Skill 必须能容忍缺省。

---

## 执行流程

按 Step 0 → 1 → 2 → 3 顺序执行。

### Step 0 — Chain Context 读取

按上文执行。

### Step 1 — 听众与格式确认

用 `AskUserQuestion` 询问：

1. **听众**：PM / Design Lead / VP-or-Exec / Stakeholder / Peer Design / Mixed
2. **输出格式**：
   - **Doc**：Markdown 文档（最详细，async 分享）
   - **Slides**：每段对应 1-2 张幻灯片大纲（meeting deck 友好）
   - **Async-share**：精简版（适合 Slack / Lark / 邮件分享）
   - **Meeting-deck**：现场讲 + 简短稿（讲稿 + bullet points）
3. **时长约束**（仅 meeting-deck）：5 分钟 / 15 分钟 / 30 分钟（影响 design_decisions 的数量）

不强求填全，能凭上游推断的不问。

### Step 2 — 按 6 段式生成 Pitch

按以下结构生成完整 Pitch。**每段必有**，深度按听众和格式调整。

---

#### Section 1 — The Bet（一句话押注 + 一个成功度量）

**写作约束**：
- The Bet **必须能在一句话内讲完**——超过一句话说明思考不够收敛
- 形式：`我们押 [方向] 来实现 [业务目标]，成功标准是 [一个可量化指标]`
- 数据来源：`frame.lean_direction.one_liner` + `brief.business_goal[0]` + `brief.design_criteria.quantitative[0]`

**示例**：
> "我们押 5 分钟极速设计周记，4 周内 MVP 上线，目标周留存率 ≥ 40%。"

**听众调整**：
- VP：必须包含数字 + 时间
- Design Lead：可加一句"为什么这个机会值得做"

---

#### Section 2 — Why Now（为什么是现在）

回答"为什么这个时刻做这件事"，不是"这件事有多重要"。

**3 个子要素**（必有，每条 1-2 句）：
- **市场变化**：哪些外部条件变了？（来自 `frame.business_angle.why_now`）
- **用户行为变化**：用户的痛点 / workaround 现在为什么忍受不下去了？（来自 `frame.persona.workaround` 的"为什么不够好"）
- **竞争窗口**：竞品有没有动？（来自 `frame.competitive_landscape`）

**写作约束**：
- 不要泛泛说"AI 时代很重要"——具体到**本产品 + 本时间窗的契机**
- 避免 hedge——明确说"现在不做的代价"

**示例**：
> 远程设计团队对 async 沟通需求 2024 年起明显上升；李楠这类设计师在 Notion + 周会的组合下越发拖延复盘；竞品 Linear / Wonder 都在做"团队周报"但都是工程视角，**设计师场景仍是空白窗口，现在不进就被通用工具吞掉**。

---

#### Section 3 — User & JTBD（用户与他们要完成的事）

**给一张人物锚点 + 一句 JTBD**，不要长篇 persona 描述。

数据来源：`frame.persona.name` + `frame.persona.description` + `frame.jtbd`

**结构**：

```markdown
### 我们为谁设计

**[姓名]**，[一句话身份描述]

JTBD：当 [情境]，[姓名] 想 [动机]，从而 [结果]。

**为什么不为其他人做**：[1 句话，来自 brief.out_of_scope 中的目标用户排除]
```

**听众调整**：
- VP：可省略 "为什么不为其他人做"，节省时间
- Stakeholder：persona 描述加更多共情细节
- Peer Design：可补 user_anchor 的 frustrations

---

#### Section 4 — Direction & Alternatives（我们押了什么 + 为什么不押其他）

**这是 Pitch 最关键的一段**——决策者听完这段，应该理解"为什么是这个方向不是另一个"。

**3 个子要素**：

- **押的方向（chosen）**：一句话 + 用户价值 + 业务价值（来自 `frame.directions[chosen]`）
- **考虑过的 alternatives**：列 2-3 个其他 directions（来自 `frame.directions` 中非 chosen 的）+ **每个为什么没押**（一句话）
- **关键风险**：押这个的最大假设（来自 `frame.critical_assumption`）+ 如果错了我们怎么知道（如何测试）

**写作约束**：
- **必须显式列 alternatives**——只讲 chosen 显得没思考过
- 每个 alternative 的"为什么不押"要诚实，不要假装"它们都很好但 chosen 更好"
- 关键风险不要软化——"我们最不确定的是 [X]" 比 "我们假设 [X]" 更诚实

**示例结构**：

```markdown
### 我们押方向 A：5 分钟极速设计周记

- **用户价值**：不打断设计工作流就能完成复盘
- **业务价值**：极简上手 = 强留存钩子

### 考虑过的其他方向

- **方向 B：可视化设计周记**（设计稿 + 文字 + 灵感卡片）
  → 不押：用户单次成本 15+ 分钟，违背"3 分钟"核心
- **方向 C：团队回顾画布**（多人汇总到看板）
  → 不押：依赖团队 leader 主动使用，承担"双边市场"启动难题

### 我们最不确定的事

**关键假设**：设计师真的愿意每周花 3 分钟，且不会被"又一个工具要填"劝退。

**如何测试**：MVP 上线 30 天内追踪首屏到完成中位数 + 周回访率。如果回访率 < 30%，假设可能错，需重新审视方向。
```

---

#### Section 5 — Design Decisions（3-5 个关键设计决策）

**不要展示所有屏**——展示 3-5 个**能体现核心方向**的设计决策。

**每个决策的结构**：

```markdown
### 决策 N：[一句话决策描述]

**为什么这么决定**：[来自 brief.strategy_dimensions[].thesis 或 stories[].rationale]

**证据**：[来自 stories.acceptance_criteria / flow-web.screens / check.findings 已解决]

**关联屏**：[1-2 个最能展示该决策的屏名]
```

**听众调整**：
- VP / Stakeholder：3 个决策，每个 ≤ 3 行
- Design Lead / Peer：5 个决策，每个可加视觉细节
- Meeting-deck（5 分钟）：仅 3 个决策；Meeting-deck（30 分钟）：5 个决策 + 屏幕截图

**选 3-5 个决策的优先级**：

1. **直接体现 Lean direction 的决策**（"3 分钟"如何在设计中体现）
2. **跟 alternatives 区分的决策**（为什么不做可视化、不做团队画布）
3. **关联关键假设的决策**（哪个设计选择是为了验证假设）
4. **解决 Check 已识别问题的决策**（来自 check.findings 已修复）

不要选：
- ❌ 通用的"好设计"（如间距对齐、颜色一致）——这些是基线不是决策
- ❌ 跟方向无关的细节（如某个图标用 SVG 还是 PNG）

---

#### Section 6 — Asks（需要决策者拍什么）⭐

**这是 Pitch 最容易被遗忘但最重要的一段**。没有 Asks 的 Pitch 是失败的 Pitch。

**每个 Ask 的结构（4 元强制字段，跟 schema.asks 一一对应）**：

```markdown
### Ask N：[需要决策者拍的具体事]   ← 对应 schema 字段 `ask`

- **为什么需要决定**：[这件事悬而未决会怎么样]   ← `why_needed`
- **决定时间**：[什么时候之前需要]                ← `decision_needed_by`
- **如果不决定的影响**：[block 什么 / 推迟什么]    ← `impact_if_no_decision`
```

⛔ **4 个字段缺一不可**——只有 `ask` 没有其他 3 项 = 这个 Ask 在决策会上拍不下来。`decision_needed_by` 不写时间窗 = 等于不要求决定。`impact_if_no_decision` 不写 = 决策者感受不到延迟成本，会自然拖延。

**Ask 的来源**（按优先级）：

1. **来自 PRD thin_sections**：上游 PRD 标的薄弱章节 → "需要 [角色] 补 [字段]"
2. **来自 stories[].待澄清问题**：Story 中未决的开放问题
3. **来自 edge.critical_missing**：必须设计但未做的状态 → 是否纳入 v1
4. **来自 qa.deviations 未解决项**：实现层未修复的差异 → 是否上线前必修
5. **来自 frame.critical_assumption**：是否同意以本方向测试这个假设

**Ask 数量约束**：3-5 个最关键的（不要把所有未决的事都列上）

**写作约束**：
- **每个 Ask 必须是"yes / no / 选 A 还是 B"形式**，不要"请大家讨论"
- 给决策时间窗（不给 deadline 等于不决定）
- 明确"如果不决定的影响"——让决策者知道延迟代价

**示例**：

```markdown
### Ask 1：是否同意以"3 分钟"作为 MVP 唯一定量验证目标？

- **为什么需要决定**：这是 critical assumption；如果不同意，需要换其他验证维度（如内容质量）
- **决定时间**：本周五前
- **如果不决定的影响**：影响 Flow Web 的字段数量控制（3 分钟 = 严控字段 / 不限定 = 灵活）

### Ask 2：v1 是否包含团队功能（Story 4：加入或创建团队）？

- **为什么需要决定**：影响 4 周 MVP 范围；个人版 vs 团队版交付物完全不同
- **决定时间**：本周内
- **如果不决定的影响**：工程师无法开始 sprint 0 规划
```

---

### Step 3 — 输出（保存文件 + 双通道 Context）

#### 3.1 保存 Markdown Pitch 文件

文件路径：`spark-output/pitch/[direction-slug].md`

**完整 Pitch Markdown 文件结构**：

```markdown
# Pitch — [项目名] / [direction]

- **生成时间**：[ISO8601]
- **听众**：[audience]
- **格式**：[format]
- **数据源**：[N] 个上游 Skill
- **完整度**：strong / moderate / thin

---

## 一句话押注 (The Bet)

[Section 1]

---

## 为什么是现在 (Why Now)

[Section 2]

---

## 我们为谁设计 (User & JTBD)

[Section 3]

---

## 方向 + 备选 (Direction & Alternatives)

[Section 4]

---

## 设计决策 (Design Decisions)

[Section 5 — 3-5 个]

---

## 需要决定的事 (Asks) ⭐

[Section 6]

---

> ⚠️ **薄弱章节提示**（如有）：[列出哪段缺什么、建议怎么补]
```

**Slides format 额外输出**：每段对应 1-2 张幻灯片大纲（标题 + 3-5 个 bullet）。

#### 3.2 双通道 Context 输出

按 [chain-protocol.md](../../chain-protocol.md) 第 2.1 节执行。

**Step 1 — 写盘到 `spark-output/context/pitch.json`**（必做，主持久化通道；目录不存在先创建）。写入以下完整 JSON：

```
{
  "skill": "pitch",
  "generated_at": "<ISO8601>",
  "project_name": "...",
  "audience": "pm|design-lead|vp-or-exec|stakeholder|peer-design|mixed",
  "format": "doc|slides|async-share|meeting-deck",
  "pitch_file": "spark-output/pitch/[direction-slug].md",
  "sections": {
    "the_bet": { "one_liner": "...", "success_metric": "..." },
    "why_now": "...",
    "user_jtbd": { "persona_name": "...", "persona_description": "...", "jtbd": "..." },
    "direction": {
      "chosen": "...",
      "chosen_id": "A",
      "alternatives_considered": ["B: ...", "C: ..."],
      "why_this_one": "...",
      "key_risk": "...",
      "critical_assumption": "..."
    },
    "design_decisions": [
      { "decision": "...", "rationale": "...", "evidence": "...", "related_screen": "..." }
    ],
    "asks": [
      {
        "ask": "...",
        "why_needed": "...",
        "decision_needed_by": "本周五前",
        "impact_if_no_decision": "..."
      }
    ]
  },
  "source_skills": {
    "frame": true, "scope": false, "audit": false, "brief": true,
    "stories": true, "flow_web": true, "flow_mobile": false,
    "check": true, "qa": false, "edge": false
  },
  "thin_sections": []
}
```

**Step 2 — chat 输出紧凑 marker**（必做，⛔ **不要在 chat 内重复输出 Step 1 的完整 JSON**）：

```
<!-- spark-context:pitch ref="spark-output/context/pitch.json" -->
Pitch 已保存：project=[project_name]，audience=[受众]，format=[格式]，the_bet=[一句话押注]，[N] 个 Asks，pitch_file=spark-output/pitch/[slug].md
<!-- /spark-context:pitch -->
```

**降级 fallback**：若 Step 1 写盘失败（chat-only 平台），输出完整 JSON marker（无 ref 属性，marker 之间放裸 JSON）作为唯一持久化通道。

#### Handoff 提示（必输出）

> **协议**：按 [`_shared/next-skill.md`](../../_shared/next-skill.md) 三层结构模板输出；前 5 候选由 `_shared/skill-graph.json` 的依赖图算法实时算（done ⊆ ready，按 next_hint.preferred → alternatives → 同阶段 → anchor → fan-out 排序），优先建议从 `_shared/skill-graph.json#skills[id="pitch"].next_hint` 读取。

**首行模板**：`✅ 设计提案 已完成，6 段叙事 + Asks 已成稿，已保存到 `spark-output/pitch/[slug].md`。`

**本 Skill 的 `next_hint`**（来自 skill-graph.json，**不可在此 SKILL.md 内硬编码覆盖**）：

- **preferred**：`/prd`
- **优先理由**：提案对齐决策后进 PRD 把方案落到工程交付文档。
- **alternatives**：`/flow-web` (提案获批后开始 / 继续执行页面设计) · `/metric` (提案 asks 含数据度量，先定指标体系) · `/retro` (项目阶段性结束做复盘)
- **emoji**：💼

**红线**：
- ❌ 禁止在本段硬编码候选清单（如「进入 Stories / Journey / Sitemap」）——所有候选必须由算法实时生成
- ❌ 禁止按「文档类 / 视觉类 / 决策类」再分类候选（v0.5.5 起，分类已折叠进 next_hint.alternatives）
- ❌ 禁止与「更新链路面板」段合并——两段必须各自独立成段，中间空一行
- ❌ 禁止漏第 2 行候选清单——即使候选只有 1 个、或为空（终端节点）也要写出来

---

## 实操注意事项

### 不要做的事

- ❌ **不要展示所有屏**：Pitch 不是设计稿巡演。每张屏的展示必须服务于讲清某个决策
- ❌ **不要 hedge Asks**：".... 我想听听大家的意见" = 不算 Ask。Ask 必须是 yes/no/选 A 选 B
- ❌ **不要复述上游字段**：Pitch 是**重新编排**，每段都问"决策者听这段获得什么"
- ❌ **不要 5 段全详细**：根据时长和听众，决策密度应该是金字塔——Bet 1 句 / Why Now 3 句 / User 2 行 / Direction 3 段 / Decisions 5 段 / Asks 3-5 条

### 听众混合时的策略

如果听众是 Mixed（PM + Lead + VP 同时在），按以下原则：

1. **以最高级别（VP）为主**：The Bet + Asks 必须 VP 视角
2. **Design Decisions 段加一个"工艺细节" 子段**：给 Design Lead 看，但放最后
3. **Why Now 段加一句业务数据**：给 PM 看
4. **总时长按 VP 容忍度**：≤ 15 分钟

### 与 PRD 的协同

Pitch 和 PRD 可同时生成（吃同一批上游字段）。建议：

- **先 Pitch 后 PRD**：先用 Pitch 跟决策者对齐方向，拍板后再生成 PRD 给工程
- **如果同时已有 PRD**：Pitch 可在 Ask 段说"PRD 详见 `spark-output/prd/[slug].md`"，节省现场讲实现的时间

---

## 已知限制

- Pitch 质量取决于上游 context 完整度；frame + brief 是底线
- 不替代真人讲稿——AI 生成是骨架，最终现场表达需要设计师自己练
- 听众情绪 / 团队政治 / 历史矛盾这些 Pitch 不处理，需要设计师自己读空气
- 视觉化（图表、截图、设计稿嵌入）需要设计师手动补——Pitch 输出的是结构 + 文字

---

## 与兄弟 Skill / PM 套件的边界（v0.4.0 补充）

| 场景 | 用谁 | 不用谁 |
| --- | --- | --- |
| 设计完成后向决策者汇报 / 求批准 | **Pitch** | Brief（启动期对齐）/ Retro（项目结束后） |
| 工程交付文档（给开发者读） | PRD | Pitch（PRD 是工程语言，Pitch 是决策语言） |
| 项目结束后的复盘 | Retro | Pitch（Retro 不需要 Asks，Pitch 必须有 Asks） |
| PM 套件「需求评审材料」 | PM 套件 | Pitch（设计师叙事：问题 → 洞察 → 方案 → 风险 → Ask） |
| 跨部门一页纸同步（不要 ask） | Brief / Journey HTML | Pitch（Pitch 强制带 Ask 4 元字段） |

**Pitch 不可替代性**：6 段叙事结构（背景 / 问题 / 洞察 / 方案 / 风险 / Ask）+ 强制 Ask 4 元字段（ask / why_needed / decision_needed_by / impact_if_no_decision），专为设计师向上汇报、推动决策设计。

## 质量标准

1. **6 段叙事完整**：背景 / 问题 / 洞察 / 方案 / 风险 / Ask 一段不少，每段 200-500 字（看听众）
2. **Asks 4 元字段强制**：每个 Ask 必须含 ask / why_needed / decision_needed_by / impact_if_no_decision，缺一不可
3. **听众适配 6 段时长分配**：exec（5 分钟）/ design-team（20 分钟）/ mixed（10 分钟）三种听众有不同时长权重，自动算分钟
4. **关键数据可追溯**：每个 metric / quote / finding 标注来源（Brief / Probe / Signal / Audit / Metric 上游 ID）
5. **风险段不只列已知风险**：必须含 mitigation 和 owner，否则视为 incomplete
6. **不超过 1 个核心建议方案**：方案段聚焦 1 个推荐方案 + 1-2 个备选，备选必须写 trade-off

## 红线规则

1. **不出现没有 Ask 的 Pitch**：Pitch 的本质是推动决策——无 Ask 等于 status update，不是 Pitch（这种场景请用 Brief / Journey）
2. **不替代 PRD**：Pitch 是决策语言（问题 / 方案 / 风险），PRD 是工程语言（字段 / 接口 / 验收）——给开发的不要发 Pitch
3. **不夸大效果**：声称的设计影响必须有 Metric 上游证据或可观测指标，不能用「显著提升」「极大改善」这类无量化词
