---
name: 写PRD
name_en: "prd"
argument-hint: "输入要交付给工程的功能或 Epic，如：用户可用微信扫码登录并绑定手机号"
description: >
  产品需求文档（设计师视角的工程交付桥接）。把已对齐的设计产出（/设计简报 + /用户故事 + /站点地图 + Flow Web/Mobile）整合为 8 段式 PRD，让工程师或 coding agent（Cursor / Claude Code 等）直接消费——含完整功能描述、Given/When/Then 验收标准、设计触点、已生成的设计资产引用、风险与发布计划。

  触发关键词：写 PRD、生成需求文档、把这个交给工程、给工程师写文档、make this shareable、handoff to engineering、转 PRD、/用户故事 转 PRD、需求文档、product requirements document。

  排除（反向）：读取已有 PRD 提炼设计字段（用 /读需求）、写用户故事（用 /用户故事）、做设计走查（用 /设计走查）、做项目复盘（用 /设计复盘）。

description_en: >
  Product Requirements Document (design-to-engineering bridge). Consolidates aligned design outputs
  (Brief + Stories + Sitemap + Flow Web/Mobile) into an 8-section PRD directly consumable by
  engineers or coding agents (Cursor / Claude Code). Includes complete feature descriptions,
  Given/When/Then acceptance criteria, design touchpoints, references to generated design assets,
  risk assessment, and release plan.

  Triggers when a designer says: "write a PRD", "generate requirements doc", "hand this off to
  engineering", "write docs for the engineers", "make this shareable", "handoff to engineering",
  "convert to PRD", "Stories to PRD", "product requirements document", "写 PRD", "工程交付",
  "需求文档".

  Excludes: reading an existing PRD to extract design fields (use /scope), writing user stories
  (use /stories), design file review (use /check), project retrospective (use /retro).

allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - AskUserQuestion
chain:
  protocol_version: "1.0"
  reads: [brief, frame, scope, stories, sitemap, journey, flow-web, flow-mobile, check, chart, motion-plan]
  writes: prd
  schema:
    skill: string
    generated_at: string
    project_name: string
    direction: string
    prd_file: string
    sections_summary:
      summary: string
      primary_persona: string
      product_goal: string
      success_metrics:
        - metric: string
          target: string
          timeframe: string
      feature_count: number
      in_scope_features: array<string>
      out_of_scope_features: array<string>
      critical_assumption: string
      mvp_stories: array<string>
    source_skills:
      brief: boolean
      stories: boolean
      sitemap: boolean
      flow_web: boolean
      flow_mobile: boolean
      frame: boolean
      scope: boolean
      check: boolean
    thin_sections: array<string>
---

# 写PRD

> 你是 PRD 生成专家。本 Skill 把已对齐的**设计产出**——Brief（业务对齐）+ Stories（用户故事）+ Sitemap（IA 骨架）+ Flow Web/Mobile（设计稿 / 代码）—— 整合为一份**工程师或 coding agent 可直接消费**的 8 段式 PRD。

**这是设计师视角的 PRD，不是 PM 视角的 PRD**：
- PM 的 PRD：从市场/用户研究开始，论证为什么做、做什么
- 设计师的 PRD：基于**已对齐的设计方向**，告诉工程师**做什么、按什么标准做、参考哪些已生成的设计资产**

**核心使命**：让独立设计师 / AI 原生设计师能在没有 PM 的情况下，把设计产出**完整、结构化、可执行**地交付给工程实现。

---

## Chain Context

### 上游读取（Step 0 执行，**最关键的一步**）

PRD 的质量直接取决于上游 context 的完整度。按以下顺序尝试读取：

1. 扫描会话中的 marker：`brief` / `stories` / `sitemap` / `flow-web` / `flow-mobile` / `frame` / `scope` / `check`
2. 读取项目目录 `spark-output/context/*.json`
3. 至少要读到 **stories**（最低门槛），否则降级到 Step 1 询问

**8 段输出结构是强约束**（PRD 必须含全部 8 段，缺一段标为 thin_sections 在 Step 3 输出）：

| # | 章节名 | 一句话定位 |
| --- | --- | --- |
| 1 | Summary / Overview | 60 秒读完版本 |
| 2 | Background / Business Context | 为什么做这个 |
| 3 | Personas / User Segments | 给谁做 |
| 4 | Goals & Success Metrics | 怎么算赢 |
| 5 | Value Proposition | 我们押什么 |
| 6 | Solution & Feature Scope | 做什么 + MVP 范围 + 设计资产 ⭐ 最重要 |
| 7 | Constraints & Risks（含 Release Plan） | 不做什么 + 风险分层 |
| 8 | Backend Dependencies / Release Approach | 工程依赖 + 上线节奏 |

**字段映射（PRD 8 段式如何消费上游 chain JSON）**：

| PRD 章节 | 上游来源 | 字段映射 |
| --- | --- | --- |
| Section 1 — Summary | brief + frame | `brief.business_context` + `brief.business_goal` + `frame.lean_direction` |
| Section 2 — Background | frame + brief | `frame.persona.workaround` + `frame.business_angle.why_now` + `brief.out_of_scope` |
| Section 3 — Personas | frame.persona / stories.persona | 完整 persona 结构 |
| Section 4 — Goals & Metrics | brief.business_goal + brief.design_criteria.quantitative | 业务 KPI + 体验度量 |
| Section 5 — Value Prop | frame.directions[lean] | user_value + business_value + 差异化 |
| Section 6 — Solution & Feature Scope | **stories** + flow-web/mobile + sitemap + journey | stories.acceptance_criteria + design_touchpoints + sitemap.pages + flow.output_files + journey.key_moments |
| Section 7 — Constraints & Risks | brief.constraints + frame.critical_assumption + check.findings + journey.dropout-risk | 技术约束 + 关键假设 + 已识别问题 + 流失风险 |
| Section 8 — Release Approach | stories.priority + frame.critical_assumption | MVP 范围 + 先发顺序 |

⛔ **消费上游 chain context 是强制约束**：
- 上游有的字段必须读，不能凭直觉重写（避免跟 brief / stories 产生事实漂移）
- Section 6 必须**列出全部上游 flow.output_files 中的 .tsx 路径**作为「设计资产清单」，让工程师能直接接走
- Section 7 的 risks 必须**从 check.findings 自动提取未修的 Major / Minor**，不要凭空写

读到上下文后告知用户："已读到 [项目名] 的 [N] 个上游 Skill 产出，将整合生成 8 段式 PRD。预计 [strong/moderate/thin] 完整度——[列出薄弱章节]。"

### 下游输出（Step 4 执行）

按 [chain-protocol.md](../../chain-protocol.md) §2.1 v1.1 智能适配规则：

1. **保存 Markdown PRD 文件**（核心产物）：`spark-output/prd/[direction-slug].md`
2. **写盘 chain context**：写入 `spark-output/context/prd.json`（含元数据 + 章节摘要，**不含完整 PRD 文本**——PRD 全文在 `spark-output/prd/[slug].md`）
3. **chat 输出紧凑 marker**（⛔ 不要在 chat 内输出完整 JSON）：

   ```
   <!-- spark-context:prd ref="spark-output/context/prd.json" -->
   PRD 已保存：project=[project_name]，direction=[direction]，[N] 个 Story / [M] 个 acceptance_criteria，prd_file=spark-output/prd/[slug].md
   <!-- /spark-context:prd -->
   ```

降级 fallback：若写盘失败，输出完整 JSON marker（无 ref）。详见 §2.1。

下游可消费 Skill：**Retro**（项目复盘归档）/ **Pitch**（汇报材料引用）。

### 字段流向下游

- `prd.sections_summary` → **Retro** 的 Decision Validation 输入（事后看每个 PRD 决策是否成立）
- `prd.success_metrics[]` → **Retro** 的"假设验证"输入（PRD 写明的指标是否达成）
- `prd.thin_sections[]` → **Retro** 的"做得不好"输入（PRD 写薄的段对应链路上下文不足）
- `prd.primary_persona` → **Retro** 的 persona 复盘锚点（设计假设的用户与实际用户是否一致）
- `prd.prd_file` → **Pitch** 的工程交付素材引用（汇报时引用 PRD 全文链接）

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

## 三种激活模式

### A — 完整上下文（推荐）

读到 brief + stories + sitemap + flow-web 或 flow-mobile（至少 4 个 Skill 产出齐全）。

> "已读到完整上下文。8 段 PRD 全部章节都有强支撑，直接生成。"

进入 Step 2 直接生成。

### B — 部分上下文

只读到 stories（最低门槛）。

> "读到 stories 上下文，但缺少 [Brief / Sitemap / Flow]。我会基于 stories 生成 PRD，但 [Background / Solution 实现细节 / 风险] 等章节会偏薄。建议先回头补 Brief / Flow，或继续生成并接受薄弱章节。"

进入 Step 2，但在最终输出标注 thin_sections。

### C — Standalone（不推荐）

什么都没读到。

> "未读到任何上游 Skill 产出。PRD 需要至少 stories 作为输入。请粘贴 stories 内容，或先去跑 Stories Skill。"

要求用户提供 stories（粘贴或文件路径），否则不进入 Step 2。

---

## 触发条件

- 用户说"写个 PRD / 生成需求文档"
- 用户说"把这个交给工程师 / coding agent"、"handoff to engineering"
- 用户说"转 PRD / Stories 转 PRD"
- 用户使用 `/写PRD` 指令
- Stories 完成后，独立设计师准备交付工程实现时

---

---

## 独立能力（无需连接器）

本 Skill 在完全离线、无任何连接器的场景下即可完整交付，所有方法论与输出形态不依赖外部系统：

- **8 段式工程语言文档**：Background / Personas / Goals / Value Prop / Solution / Constraints / Acceptance / Rollout 完整模板
- **链式上下文双通道**：写入 `spark-output/context/prd.json` + 会话内 marker block，下游 QA / Retro 可直接读取
- **三种激活模式**：基于 Brief / 基于 Stories / 独立模式全本地完成
- **Acceptance Criteria 与 Stories AC 双向对齐**：避免需求 / 验收漂移

> 红线：缺连接器时 **绝不 abort**，所有引导与输出路径必须照常完成。

## 增强能力（连接器加持）

接入以下连接器后，可减少手动粘贴、提高对齐效率。所有连接器均为可选，未装时按"降级路径"列的方式回落。

| 连接器 | 阶段 | 增强能力 | 降级路径 |
| --- | --- | --- | --- |
| **Notion / 飞书文档** | 执行流程输出后 | PRD 一键写入团队 wiki 指定空间，工程师可直接阅读 | 未装时输出本地 `prd-{project}.md`，提示手动上传 |
| **Linear / Jira** | 执行流程输出后 | 一键把 PRD 的 Feature Scope 拆为 Epic + Story 创建到任务系统，自动关联 Brief / Stories 上游 ticket | 未装时输出 Story 列表 + 优先级，PM 手动建 issue |
| **Figma** | 执行流程（交互说明阶段） | 引用设计稿 frame 链接嵌入交互说明 / 状态规格，工程师可一键跳转 | 未装时仅文字描述交互，截图由设计师手动附 |

**接入触发**：用户首次调用 `/写PRD` 时，Skill 主动检测已认证的连接器并显示「已检测到：XXX，将自动启用增强模式」提示，用户可在该次会话中选择关闭。

**字段流向变化**：

- 启用 **Notion / 飞书文档** → `chain.schema` 新增可选字段 `wiki_page_url: string`
- 启用 **Linear / Jira** → `chain.schema` 新增可选字段 `epic_url: string` + `tickets: array<{story_id, ticket_url}>`
- 启用 **Figma** → `chain.schema` 新增可选字段 `design_refs: array<{feature_id, frame_url}>`

> 所有新增字段都是 **可选**，未启用连接器时字段缺省，下游 Skill 必须能容忍缺省。

---

## 执行流程

按 Step 0 → 1 → 2 → 3 → 4 顺序执行。

### Step 0 — Chain Context 读取

按上文执行。

### Step 1 — 缺口确认（仅当上下文不全）

用 `AskUserQuestion` 询问关键缺失字段：

1. 没有 brief → 问业务背景一句话 + 业务目标
2. 没有 frame → 问人物锚点（一句话）
3. 没有 sitemap → 问主要页面 / 路由清单
4. 没有 flow-web/mobile → 问"已有设计稿吗？提供截图或代码路径"

不强求填全，能薄就薄，最终 thin_sections 字段标注。

### Step 2 — 生成 8 段 PRD

按以下结构生成完整 Markdown 文档。**每段必有，深度按上下文调整**——上下文不够就薄，不要凭空编造。

---

#### Section 1 — Summary（一段话，60 秒读完）

一段散文（不要 bullet），覆盖 4 个要素：

- **做什么**（一句话）
- **给谁**（primary persona）
- **为什么是现在**（市场 / 业务原因）
- **成功长什么样**（一个可量化结果）

**写作约束**：如果 stakeholder 只看这一段就要理解整个项目押注，必须做到。

#### Section 2 — Background & Problem

- **问题**：从用户视角描述（用 frame.persona 或 brief.business_context 的措辞），**不要从产品视角**
- **当前 workaround**：用户今天怎么解决？为什么不够好？（来自 frame.persona.workaround）
- **为什么是现在**：市场 / 用户行为 / 竞品格局有什么变化？（来自 frame.business_angle.why_now）
- **不解决什么**：明确 1-2 个相邻问题本 PRD 故意排除（来自 brief.out_of_scope）

#### Section 3 — Personas & User Segments

**Primary persona** 完整版（用 frame.persona 或 stories.persona）：

```
姓名：[name]
身份：[description]
情境：[situation]
JTBD：当 [situation]，[name] 想 [motivation]，从而 [outcome]。
当前 workaround：[workaround]
痛点：[frustrations]
```

**Secondary persona**（如适用）：相同格式。常见于 B2B（买家 vs 使用者不同）。

**这个产品不为谁做**：一句话。防止"为所有人做"。

#### Section 4 — Goals & Success Metrics

- **产品目标**：一句话，**outcome-framed 不是 feature-framed**（来自 brief.business_goal）
- **成功度量表**：

```markdown
| 指标 | 度量什么用户行为 | 目标值 | 时间窗 |
| --- | --- | --- | --- |
| [primary] | ... | 具体数字 | 30/60/90 天 |
| [secondary] | ... | ... | ... |
| [health] | ... | ... | ... |
```

度量来源：brief.design_criteria.quantitative + brief.business_goal

- **Anti-metrics（反指标）**：**这是 SparkSkillsHub PRD 的特色之一**。明确不优化什么——例如"通知打开率"虽然好看但优化它会破坏信任。每个 PRD 至少列 1 个 anti-metric。
- **关键假设**：来自 frame.critical_assumption——一句话写出"如果错了就意味做错产品"的假设。

#### Section 5 — Value Proposition

**对主用户**：

> "[persona name] 终于可以 [JTBD] 而不必 [当前阻力]，因为 [本产品做了什么不一样的事]。"

**对 buyer**（如不同于 user）：相同模板。

**竞争差异化**：2-3 句。要具体，"更好的 UX" 不算差异化。来自 frame.competitive_landscape——明确**对手做对了什么、留下什么空白、本产品填的是哪个空白**。

#### Section 6 — Solution & Feature Scope（**最重要章节**）

> 这一段是 SparkSkillsHub PRD 跟传统 PM PRD 最大的不同——它**显式包含设计触点和已生成的设计资产引用**，让 coding agent 直接消费。

对 stories 中每个 Story（按 priority 降序），生成以下结构：

```markdown
### [Story 标题]

**Persona**：[story.persona]
**Job**：[story.scenario] → [JTBD 动机]
**优先级**：P0 / P1 / P2
**关键假设标记**：⭐（仅当 critical_assumption=true）

**功能描述**（2-3 句，从用户视角，平实语言）：
[基于 story.scenario 和 story 主体生成]

**In Scope（这版要做的）**：
- [基于 story.acceptance_criteria 转译]
- [...]

**Out of Scope（这版故意不做的）**：
- [基于 brief.out_of_scope + story.priority < p0 的部分]

**验收标准（Given / When / Then）**：
- Given [情境]，When [动作]，Then [可观察结果]
- Given [情境]，When [动作]，Then [可观察结果]
- 边缘情况：[X 出错时怎么办]
- 空状态：[没数据时用户看到什么]

**设计触点**（来自 story.design_touchpoints）：
- 涉及屏：[...]
- 涉及组件：[...]
- 涉及状态：[...]

**关联 Sitemap 页面**（来自 sitemap.pages）：
- [page.id]: [page.route] — [page.label]

**已生成的设计资产**（来自 flow-web.output_files / flow-mobile.output_files）：
- `src/app/(retro)/new/page.tsx` — Three Questions 屏
- `src/components/retro/WeekStreak.tsx` — 连续打卡组件
（如果上游有 flow 输出则列出，没有则标注"待生成"）

**待澄清问题**：
- [story 阶段未解决的决策项]
```

**关键规则**：
- 每个 Story 一节，按 priority 降序（P0 在前）
- 没有上游 flow 时"已生成的设计资产"标注为"待生成"，提示工程师走 vibe coding 流程
- 已生成的设计资产**必须列具体文件路径**，不要写"在 src/app 下"这种模糊描述

最后单独列一个"未列入本版的 Stories"小节，列 P2 或低优先级 Story 的标题，备 Phase 2 引用。

#### Section 7 — Constraints & Risks

- **技术约束**：来自 brief.constraints。例如"4 周交付"、"Web 优先"、"必须用 SparkDesign"
- **设计约束**：UX pattern / 无障碍要求等不可妥协项。来自 brief.design_criteria.qualitative
- **数据 & 隐私**：本 PRD 涉及哪些个人数据？合规考虑（GDPR / CCPA / 国内法规）？
- **关键风险表**：

```markdown
| 风险 | 可能性 | 影响 | 缓解措施 |
| --- | --- | --- | --- |
| [关键假设错] | High | High | [最便宜的测试，来自 frame.critical_assumption + 关联条件] |
| [技术依赖失败] | M | M | [fallback 方案] |
| [用户不接受] | M | H | [灰度 / 测试方案] |
```

**特别引用**：如果上游有 check.findings，把其中的 blocker / major 项列入 risks 表（"已识别但未修复的设计问题"）。

#### Section 8 — Release Approach

- **推荐顺序**：哪个 Story 先发，为什么？**优先发关键假设测试 Story**（来自 frame.critical_assumption + stories.critical_assumption=true 的 Story）
- **MVP 定义**：最小 Story 集合，能交付足够价值且能验证核心假设。**显式列 Story 标题**
- **Phase 2**（如适用）：故意延后到第二版的内容，为什么
- **上线考虑**：
  - 上线前需要通知谁？（stakeholders / 客服 / 法务）
  - 是否 soft launch / beta 降风险？
  - 上线后头 2 周监测什么？

---

### Step 3 — 自检与 thin_sections 标注

PRD 生成完后，对每段做"完整度自检"：

| 段落 | 完整 | 中等 | 薄 |
| --- | --- | --- | --- |
| Summary | 4 要素全有 | 3 要素 | <3 要素 |
| Background | 4 子段全有 | 缺 1 段 | 缺 ≥2 段 |
| Personas | primary 完整 + 谁不为 | primary 缺细节 | 仅一句话 |
| Goals | 3 度量 + anti-metric + assumption | 缺 anti-metric | 仅 1 度量 |
| Value Prop | 用户 + buyer + 差异化 | 缺 buyer | 仅模板未填 |
| Solution | 每个 Story 有完整 GWT + 设计触点 | 缺设计触点 | 仅功能描述 |
| Constraints | 4 子段 + 风险表 | 缺 1 段 | 仅约束无风险 |
| Release | 顺序 + MVP + Phase 2 + 上线 | 缺 1 项 | 仅 MVP 列表 |

任何一段评级"薄"的，记入 thin_sections，在 PRD 末尾标注。

### Step 4 — 输出（保存文件 + 双通道 Context）

#### 4.1 保存 Markdown PRD

文件路径：`spark-output/prd/[direction-slug].md`

`direction-slug` 来源（按优先级）：
1. frame.lean_direction 的 slug 化
2. brief.project_name 的 slug 化
3. 用户提供

**完整 PRD Markdown 文件结构**：

```markdown
# PRD — [项目名] / [direction]

- **生成时间**：[ISO8601]
- **数据源**：[brief / stories / sitemap / flow-web / ...] [N] 个上游 Skill
- **完整度**：strong / moderate / thin

[Section 1 - Summary]

---

## Background & Problem

[Section 2]

---

## Personas

[Section 3]

---

## Goals & Success Metrics

[Section 4]

---

## Value Proposition

[Section 5]

---

## Solution & Feature Scope

[Section 6 — 每个 Story 一段]

---

## Constraints & Risks

[Section 7]

---

## Release Approach

[Section 8]

---

> ⚠️ **薄弱章节提示**（如有）：
> [thin_sections 中每条说明缺什么、建议怎么补]
```

#### 4.2 双通道 Context 输出

按 [chain-protocol.md](../../chain-protocol.md) 第 2.1 节执行。

**Step 1 — 写盘到 `spark-output/context/prd.json`**（必做，主持久化通道；**仅含元数据 + 章节摘要，不含 PRD 全文**——PRD 全文在 `spark-output/prd/[slug].md`）。写入以下完整 JSON：

```
{
  "skill": "prd",
  "generated_at": "<ISO8601>",
  "project_name": "...",
  "direction": "...",
  "prd_file": "spark-output/prd/[direction-slug].md",
  "sections_summary": {
    "summary": "<Section 1 一句话>",
    "primary_persona": "<persona name>",
    "product_goal": "<one sentence>",
    "success_metrics": [
      { "metric": "...", "target": "...", "timeframe": "..." }
    ],
    "feature_count": 0,
    "in_scope_features": ["..."],
    "out_of_scope_features": ["..."],
    "critical_assumption": "...",
    "mvp_stories": ["..."]
  },
  "source_skills": {
    "brief": true,
    "stories": true,
    "sitemap": false,
    "flow_web": true,
    "flow_mobile": false,
    "frame": true,
    "scope": false,
    "check": false
  },
  "thin_sections": ["release_approach"]
}
```

**Step 2 — chat 输出紧凑 marker**（必做，⛔ **不要在 chat 内重复输出 Step 1 的完整 JSON**）：

```
<!-- spark-context:prd ref="spark-output/context/prd.json" -->
PRD 已保存：project=[project_name]，direction=[direction]，[N] 个 Story / MVP=[mvp_stories]，prd_file=spark-output/prd/[slug].md
<!-- /spark-context:prd -->
```

**降级 fallback**：若 Step 1 写盘失败（chat-only 平台），输出完整 JSON marker（无 ref 属性，marker 之间放裸 JSON）作为唯一持久化通道。

#### Handoff 提示（必输出）

> **协议**：按 [`_shared/next-skill.md`](../../_shared/next-skill.md) 三层结构模板输出；前 5 候选由 `_shared/skill-graph.json` 的依赖图算法实时算（done ⊆ ready，按 next_hint.preferred → alternatives → 同阶段 → anchor → fan-out 排序），优先建议从 `_shared/skill-graph.json#skills[id="prd"].next_hint` 读取。

**首行模板**：`✅ 写PRD 已完成，8 段工程交付文档 + 先发 Story 推荐已就绪，已保存到 `spark-output/prd/[slug].md`。`

**本 Skill 的 `next_hint`**（来自 skill-graph.json，**不可在此 SKILL.md 内硬编码覆盖**）：

- **preferred**：`/extract`
- **优先理由**：PRD 已交付工程，进 Extract 把设计 token 抽出来给工程实现侧消费，让代码与设计稿对齐。
- **alternatives**：`/qa` (等工程实现后做还原度验收) · `/metric` (PRD Section 4 想用 Metric 蓝图替代 Brief 简版)
- **emoji**：📄

**红线**：
- ❌ 禁止在本段硬编码候选清单（如「进入 Stories / Journey / Sitemap」）——所有候选必须由算法实时生成
- ❌ 禁止按「文档类 / 视觉类 / 决策类」再分类候选（v0.5.5 起，分类已折叠进 next_hint.alternatives）
- ❌ 禁止与「更新链路面板」段合并——两段必须各自独立成段，中间空一行
- ❌ 禁止漏第 2 行候选清单——即使候选只有 1 个、或为空（终端节点）也要写出来

---

## 实操注意事项

### 不要做的事

- ❌ **不要再做研究**：PRD 生成阶段，所有用户研究 / 竞品分析 / 商业判断都应该已经在上游 Skill 完成。PRD 是**整合**不是**创造**
- ❌ **不要凭空补字段**：上游缺什么就标 thin，不要为了"PRD 看起来完整"自己编
- ❌ **不要写 PM 视角的论证**：PRD 不需要"为什么我们应该做"的长篇论证，那是 Frame / Brief 的事
- ❌ **不要遗漏 design_touchpoints**：Solution 章节的核心差异化就是设计触点，漏了 PRD 就退化为普通 PM PRD

### 最适合的使用场景

- **独立设计师**：自己设计完，没 PM，要交付工程
- **AI 原生设计师**：vibe coding 后把设计产出转 PRD 给 coding agent 系统化实现
- **团队设计师**（少见）：补充 PM 没写到的设计相关 PRD section（一般直接合并到 PM 的 PRD）

### 非最佳场景

- 项目还在方向探索阶段（用 Frame）
- PRD 已存在且要解读（用 Scope）
- 要评估设计稿完整度（用 Check）

---

## 已知限制

- PRD 质量上限取决于上游 context 的完整度，"垃圾进垃圾出"
- 不能替工程师做技术选型 / 架构决策
- 不能替 PM 做商业模型论证（如 unit economics / go-to-market）
- 大型多 Squad 项目可能需要拆多个 PRD（按 Squad 拆 stories 集合分别生成）

---

## 与兄弟 Skill / PM 套件的边界（v0.4.0 补充）

| 场景 | 用谁 | 不用谁 |
| --- | --- | --- |
| 设计完成后给工程师 / coding agent 的 PRD | **PRD** | Scope（PRD 入口拆解）/ Pitch（决策汇报） |
| 从 PRD 拆解设计目标 | Scope | PRD（Scope 是入口，PRD 是出口） |
| 给决策者汇报推动批准 | Pitch | PRD（PRD 是工程语言，不是决策语言） |
| PM 套件「PRD 生成」 | PM 套件（**PM 视角 PRD**：商业 / 优先级 / 路线图） | PRD（**设计师视角 PRD**：设计资产路径 / 交互细节 / 验收标准 / 埋点字段） |
| 设计稿走查 / 验收 | Check / QA | PRD（PRD 不做 review） |
| 用户故事拆解 | Stories | PRD（PRD 吸收 Stories 但不替代故事拆解） |

**PRD 不可替代性**：设计师视角的工程交付 PRD，重点是「设计资产路径（.tsx / Figma）+ 交互细节 + 验收标准 + 埋点字段」，与 PM 套件 PRD 互补——PM 写「为什么做 + 业务价值」，设计师 PRD 写「设计怎么落 + 工程怎么做」。

## 质量标准

1. **8 段结构完整**：1 概要 / 2 用户故事 / 3 信息架构 / 4 页面 Flow / 5 交互细节 / 6 设计资产 + 埋点 / 7 验收标准 / 8 异常态——8 段一段不少
2. **Section 6 必含 .tsx 路径**：设计资产段必须含具体代码文件路径 + Figma 链接，不能只说「见设计稿」
3. **上游 chain 强制消费**：必须读取 brief + frame + scope + stories + sitemap + journey + flow-web + flow-mobile + check 九个上游（缺则在文档头部标 ⚠️）
4. **验收标准 ≥ stories 数量 × 2**：每个 story 至少对应 2 条工程可验收标准（功能 / 视觉 / 交互）
5. **埋点字段对齐 Metric**：Section 6 埋点列表必须与 Metric.events 一一对应，event_name / 字段一致
6. **行数 ≥ 500**：完整 PRD（含 8 段 + 表格 + 资产路径）应 ≥ 500 行，过短即视为漏内容

## 红线规则

1. **不替代 PM PRD**：设计师 PRD 不写「为什么做这个产品 / 商业价值 / 优先级排序」——那是 PM 套件的范围
2. **不省略异常态**：Section 8 必须覆盖来自 Edge 的异常态清单，不能只写 happy path——红线场景：上线后客服爆「错误页没设计」
3. **不脱离上游 stories / brief**：PRD 出现的新功能 / 新交互必须能追溯到 stories 或 brief，凭空加内容 = 红线
