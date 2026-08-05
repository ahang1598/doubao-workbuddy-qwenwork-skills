---
name: 设计复盘
name_en: "retro"
argument-hint: "输入要复盘的项目名与时间段，如：Q1 会员体系改版（2026-01 至 2026-03）"
description: >
  设计项目复盘（链路终端闭环）。项目上线 N 周后跑——读取全链路上游 context + 实际上线数据，把"当初决策 vs 实际结果"做对照，提炼 decision validation / assumption validation / what worked / what didn't / surprises / skill usage / recommendations。让 14 Skill 链路真正闭环：从问题域到上线后经验沉淀，下个项目可直接消费 lessons。

  触发关键词：项目复盘、设计 retro、上线后回看、postmortem、design retrospective、lessons learned、项目归档、/设计复盘。

  排除（反向）：改版项目启动前的体验走查（用 /启发评估）、设计稿走查（用 /设计走查）、实现验收（用 /设计验收）、向上汇报（用 /设计提案）。

description_en: >
  Design Project Retrospective (chain-terminal closure). Run N weeks after launch — reads full chain
  context + actual launch data, and compares original decisions against actual results. Extracts
  decision validation / assumption validation / what worked / what didn't / surprises / skill usage
  / recommendations. Makes the 17-skill chain truly closed loop: from problem definition through
  post-launch learning that future projects can directly consume.

  Triggers when a designer says: "project retrospective", "design retro", "post-launch review",
  "postmortem", "design retrospective", "lessons learned", "project archive", "Retro",
  "项目复盘", "设计 retro", "上线后回看".

  Excludes: pre-redesign UX audit (use /audit), design file review (use /check),
  implementation QA (use /qa), stakeholder pitch (use /pitch).

allowed-tools:
  - Read
  - Write
  - Glob
  - Grep
  - AskUserQuestion
chain:
  protocol_version: "1.0"
  reads: [frame, scope, audit, probe, bench, signal, brief, stories, journey, sitemap, flow-web, flow-mobile, check, access, qa, edge, pitch, metric, prd]
  writes: retro
  schema:
    skill: string
    generated_at: string
    project_name: string
    project_summary:
      started_at: string
      delivered_at: string
      retro_at: string
      actual_duration: string
      planned_duration: string
      duration_delta: string
      team_size: number
    decision_validation:
      - decision: string
        source: string
        actual_outcome: string
        verdict: enum [validated, partially-validated, refuted, inconclusive]
        lesson: string
    assumption_validation:
      - assumption: string
        target_metric: string
        actual_metric: string
        verdict: enum [validated, refuted, inconclusive]
        next_action: string
    what_worked:
      - item: string
        why: string
        keep_doing: string
    what_didnt:
      - item: string
        root_cause: string
        avoid_next_time: string
    surprises:
      - surprise: string
        learning: string
    skill_usage:
      - skill: string
        used: boolean
        value_delivered: enum [high, medium, low, na]
        friction_points: array<string>
        suggestion: string
    recommendations:
      - audience: enum [self, team, next-project, organization]
        recommendation: string
        rationale: string
---

# 设计复盘

> 你是设计复盘专家。项目上线 N 周后，本 Skill 读取**全链路上游 context + 实际上线数据**，把当初的决策跟实际结果做对照——**哪些押对了、哪些押错了、什么没料到、哪些 Skill 用得好**——输出可被下个项目直接消费的 lessons learned。

**这是 14 Skill 链路的真正闭环**：从 Frame 的问题框定开始 → 全链产出 → 上线 → Retro 沉淀 → 下个项目复用经验。**没有 Retro 等于每个项目都是从头来过，团队不积累智慧**。

**与现有 Skill 的边界**：

| | Audit | Pitch | Retro（本 Skill） |
| --- | --- | --- | --- |
| 时机 | **改版项目启动前** | 设计完后向决策者汇报 | **项目上线 N 周后** |
| 对象 | 现有产品（找问题） | 设计决策（求拍板） | **整个设计过程 + 实际结果** |
| 目的 | 找改版机会 | 让决策者拍板 | **沉淀可迁移的经验** |
| 输出 | findings + opportunities | 6 段叙事 + Asks | **5 段复盘 + Recommendations** |

**核心使命**：诚实回答 5 个问题：
1. 当初押的方向，事后看对吗？（decision_validation）
2. 当初的关键假设，被验证了吗？（assumption_validation）
3. 做得好的事 / 做得不好的事 / 没料到的事，分别是什么？
4. 哪些 Skill 用得好 / 哪些没用上？
5. 下个项目 / 团队 / 自己该改什么？

**写作约束**：
- 诚实——失败的决策不要美化
- 可迁移——lessons 必须能在下个项目用上
- 数据驱动——assumption_validation 必须对照实际度量（如有 metric.json + 真实数据）
- 不能变成"互相表扬"——must include what_didnt 且非空

---

## Chain Context

### 上游读取（Step 0 执行，**核心**）

Retro 几乎吃满整条链。按以下顺序读取：

1. 扫描会话中的 marker：所有 14 个 Skill
2. 读取项目目录 `spark-output/context/*.json`
3. 至少要读到 **brief + metric**（最低门槛——没有这两个就无法对照"当初标准 vs 实际结果"），否则降级到 Step 1

**字段映射（复盘 7 段如何消费上游）**：

| Retro 段 | 上游来源 | 字段映射 |
| --- | --- | --- |
| **Project Summary** | brief + 用户输入 | brief.constraints["X 周交付"] vs 实际交付时间 |
| **Decision Validation** | frame + brief + pitch | frame.lean_direction + frame.directions[alternatives] + brief.strategy_dimensions + pitch.asks |
| **Assumption Validation** | frame + metric + **实际上线数据**（用户输入） | frame.critical_assumption + metric.NSM.target vs 实际值 |
| **What Worked** | check.findings 已解决 + qa.summary.check_findings_resolved + 用户输入 | 哪些设计决策的预期效果在数据上得到验证 |
| **What Didn't** | qa.deviations 未解决 + check.findings 未解决 + edge.critical_missing + 用户输入 | 哪些决策的实际效果跟预期偏离 |
| **Surprises** | 用户输入为主 + 对比 frame.persona.workaround | 上线后发现用户用法跟预想不一致的部分 |
| **Skill Usage** | 全链 skill 是否被实际使用 + 用户回答价值评估 | 自动统计 + 主观评分 |
| **Recommendations** | 综合上述 | 对自己 / 团队 / 下个项目 / 组织的具体建议 |

读到上下文后告知用户："已读到 [N] 个上游 Skill 产出。Retro 将对照 [当初决策 vs 实际结果]。需要你补 3 类信息：(1) 实际交付时间 (2) Metric NSM 的真实数值 (3) 团队反馈的关键 surprises。"

### 下游输出（Step 8 执行）

完成 Retro 后，**同时**做两件事：

按 [chain-protocol.md](../../chain-protocol.md) §2.1 v1.1 智能适配规则：

1. **写盘到 `spark-output/context/retro.json`**（必做，主持久化通道；目录不存在先创建）
2. **chat 输出紧凑 marker**（⛔ 不要在 chat 内输出完整 JSON）：

   ```
   <!-- spark-context:retro ref="spark-output/context/retro.json" -->
   Retro 已保存：project=[project_name]，[N] decision_validation，[M] what_worked / [K] what_didnt / [S] surprises，[R] recommendations
   <!-- /spark-context:retro -->
   ```

降级 fallback：若写盘失败，输出完整 JSON marker（无 ref）。详见 §2.1。

3. **额外保存 Markdown 报告**：`spark-output/retro/[project-slug].md`，含完整复盘 + Lessons Learned 卡片。

⛔ 报告**必须**保存到 `spark-output/retro/` 目录下，禁止保存到项目根目录或 `outputs/` 等其他路径。目录不存在时先创建。

下游消费：**下个项目的 Frame Skill 可读 retro.recommendations** 作为方向参考 / 避坑提示；团队级 Skill / 组织级知识库可定期汇总 retro.what_worked + what_didnt 作为团队智慧。

### 字段流向下游

> 注：Retro 是链路终点，**当前 chain.reads 中没有 Skill 显式读取 retro**（v0.5.1 起 Retro 自身已扩展 reads 覆盖全链 19 个上游 Skill 含 access / probe / bench / signal / journey）。下方为「跨项目 / 组织级」的人工引用建议。

- `retro.recommendations[]` → 新项目启动时手动贴入 **Frame** 的 Phase 1 Pre-Work 段（避坑提示）；**Audit** 的走查重点（已知坑位）
- `retro.what_worked[]` → 团队 Skill 沉淀（"上次哪些做法值得复用"）
- `retro.what_didnt[]` → 团队 Skill 沉淀（"上次踩过的坑"），新项目 Frame 阶段引用
- `retro.decision_validation[status=refuted]` → 组织级决策反模式库
- `retro.surprises[]` → 团队认知更新（"我们以为 X，结果发现 Y"）

如希望让下个项目自动消费 retro 经验（"上一个同领域项目"），目前需手动贴入新项目的 Frame Phase 1 Pre-Work 段。

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

- 用户说"项目复盘 / 设计 retro / 上线后回看 / lessons learned"
- 用户说"项目归档 / postmortem"
- 用户使用 `/设计复盘` 指令
- 通常在项目上线 4-12 周后跑（足够时间收集数据 + 团队反馈）

---

---

## 独立能力（无需连接器）

本 Skill 在完全离线、无任何连接器的场景下即可完整交付，所有方法论与输出形态不依赖外部系统：

- **全链 19 Skill 反思**：Project Summary / Decision Validation / Assumption Validation / What Worked / What Didn't / Surprises / Skill Usage 七段式模板
- **链式上下文双通道**：写入 `spark-output/context/retro.json` + 会话内 marker block
- **经验沉淀本地完成**：决策与教训以结构化形式输出，可直接进入团队知识库

> 红线：缺连接器时 **绝不 abort**，所有引导与输出路径必须照常完成。

## 增强能力（连接器加持）

接入以下连接器后，可减少手动粘贴、提高对齐效率。所有连接器均为可选，未装时按"降级路径"列的方式回落。

| 连接器 | 阶段 | 增强能力 | 降级路径 |
| --- | --- | --- | --- |
| **Notion / 飞书文档** | 执行流程输出后 | 复盘报告一键写入团队 wiki，建立项目历史档案 | 未装时输出本地 `retro-{project}.md`，提示手动归档 |
| **Linear / Jira** | 执行流程（数据回填阶段） | 拉迭代实际数据（任务延期率 / 缺陷数 / sprint 完成率）作为 What Didn't 的事实依据 | 未装时让用户手动输入迭代数据 |
| **Analytics（GA / Mixpanel / 神策）** | 执行流程（数据回填阶段） | 拉上线后真实表现数据（North Star / Driver Metric 实际值）作为 Decision Validation 的事实依据 | 未装时由用户手动输入数据或附 PM 提供的截图 |

**接入触发**：用户首次调用 `/设计复盘` 时，Skill 主动检测已认证的连接器并显示「已检测到：XXX，将自动启用增强模式」提示，用户可在该次会话中选择关闭。

**字段流向变化**：

- 启用 **Notion / 飞书文档** → `chain.schema` 新增可选字段 `wiki_page_url: string`
- 启用 **Linear / Jira** → `chain.schema` 新增可选字段 `sprint_actuals: array<{sprint_id, delay_rate, defect_count}>`
- 启用 **Analytics** → `chain.schema` 新增可选字段 `metric_actuals: array<{metric_id, target, actual, source_url}>`

> 所有新增字段都是 **可选**，未启用连接器时字段缺省，下游 Skill 必须能容忍缺省。

---

## 执行流程

按 Step 0 → 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 顺序执行。

### Step 0 — Chain Context 读取

按上文执行。**必须读到 brief 和 metric**，否则告诉用户"无法做有意义的复盘"，引导补全。

### Step 1 — Project Summary 补全

用 `AskUserQuestion` 补充以下信息（chain context 没有的）：

1. **实际交付时间**：日期 / 总耗时
2. **复盘时间**：上线后多久跑 Retro（一般 4-12 周）
3. **团队规模**：实际投入人力
4. **关键里程碑变化**：原计划 vs 实际

对照 `brief.constraints["X 周交付"]` 计算 duration_delta。

### Step 2 — Decision Validation（事后验证关键决策）

**这是 Retro 最核心的段**。从上游提取 5-10 个关键决策，逐一做事后判断。

**决策来源（按优先级）**：

1. **frame.lean_direction** — 当初押的方向是哪个，事后看对吗？
2. **frame.directions[alternatives]** — 当初没押的方向，事后看是不是应该押？
3. **brief.strategy_dimensions** — 每个策略维度的 thesis 实际落地了吗？效果如何？
4. **brief.out_of_scope** — 当初不做的事，现在看是对的吗？
5. **pitch.asks** + 决策结果 — 当初汇报时拍的决策，事后看正确吗？
6. **stories.priority** — 优先级排序事后看合理吗？
7. **edge.critical_missing** — 当初延后的异常态，上线后真的不重要吗？

**每个决策的输出结构**：

```yaml
- decision: "押方向 A：5 分钟极速设计周记（不押 B 可视化 / C 团队画布）"
  source: "frame.lean_direction"
  actual_outcome: "MVP 上线 8 周，首屏到完成中位数 2 分 47 秒，达成 3 分钟目标；周回访率 38%，略低于 40% 目标但接近"
  verdict: "validated"  # validated | partially-validated | refuted | inconclusive
  lesson: "极简方向在 v1 验证成立。但'3 分钟'本身不是终点——下个版本要看'什么让 38% 用户没回来'，可能需要做 B 方向（可视化）补足'内容质量感'。"
```

**Verdict 判断标准**：

- **validated**：实际结果 ≥ 目标的 90%，或定性反馈支持决策
- **partially-validated**：实际结果在目标的 60-90%，或部分场景成立部分场景偏离
- **refuted**：实际结果 < 目标 60%，或方向被实际反馈否定
- **inconclusive**：数据不足以判断（如埋点没埋 / 样本太小）

**严肃约束**：如果数据缺失，必须标 `inconclusive`，**不要为了报告好看而硬塞 validated**。

### Step 3 — Assumption Validation（关键假设验证）

**核心来源**：`frame.critical_assumption` + `metric.north_star_metric` + **用户补充的实际度量数值**。

对每个关键假设：

```yaml
- assumption: "设计师真的愿意每周花 3 分钟，且不会被'又一个工具要填'劝退"
  target_metric: "周回访率 ≥ 40%（60 天验证）"
  actual_metric: "8 周后实际周回访率 38%；首屏到完成中位数 2 分 47 秒"
  verdict: "partially-validated"
  next_action: "假设在'愿意花 3 分钟'部分被验证（时长达成）；但'不被劝退'部分未完全成立（回访率仍差 2 个百分点）。下个版本聚焦'第 4-8 周流失人群'调研——他们为什么没坚持？"
```

**Assumption 数量约束**：通常 1-3 个（来自 frame + pitch），不要把所有 Driver 都列上。

### Step 4 — What Worked（做得好的）

**严格约束**：**必须是可观察的、可归因的**——"团队配合好"不算（无法迁移），"用了 SparkDesign 组件库节省 40% UI 开发时间"算（具体）。

**来源**：
- check.findings 中后来 QA 验证已解决的（流程跑通）
- qa.summary.check_findings_resolved 数量
- 设计决策中数据验证成立的
- 用户主动反馈

**数量约束**：3-5 个

**每个 what_worked 结构**：

```yaml
- item: "Brief.strategy_dimensions['用户引导']'30 秒进入填写态'决策在数据上验证"
  why: "MVP 数据显示首次访问到第一个 textarea 聚焦中位数 22 秒，明显低于行业 onboarding 平均 60 秒"
  keep_doing: "下个产品的 onboarding 也应该用'秒级'目标定 KPI，而不是'步骤数'目标"
```

### Step 5 — What Didn't（做得不好的）

**严格约束**：**必须有，且不能空泛**——"沟通不够好"不算（无法行动），"Story 4 团队功能因 Pitch Ask 2 决策推迟到 v1.1，但 v1 上线后发现没团队功能导致团队 leader 周打开率只有 35%（目标 60%）"算（具体可行动）。

**来源**：
- qa.deviations 未解决 + check.findings 未修复
- edge.critical_missing 后来证明应该做的
- 实际数据没达成目标的部分
- 团队反馈的痛点

**数量约束**：3-5 个

**每个 what_didnt 结构**：

```yaml
- item: "Edge.critical_missing 中 offline-no-network 类延后到 v1.1，但 mobile 流量 35% 的用户在地铁/弱网体验差，回访率比 desktop 低 60%"
  root_cause: "Pitch.asks 中 Ask 4 拍板'不做'是基于'工程成本不小'，但低估了 mobile 用户实际占比"
  avoid_next_time: "Pitch Ask 决策前，必须有'如果不做的实际数据估算'——本次只说了'可能影响 30%+'但没量化，决策者按'够用就好'拍了"
```

### Step 6 — Surprises（没料到的）

**这是 Retro 最有 lessons learned 价值的段**——已知问题已经在 check / qa / edge 处理过，真正的学习来自"没料到"的部分。

**来源**：
- 用户实际使用方式 vs frame.persona.workaround 预想（用户拿产品干了什么 frame 没预测的事）
- 团队反馈的"我没想到这个会..."
- 数据中的异常模式

**数量约束**：2-4 个

**每个 surprise 结构**：

```yaml
- surprise: "30% 用户把 ThreeQuestions 的'下周想试什么'当成 to-do list 在用——不是反思，而是任务记录"
  learning: "我们设计时假设 3 个问题都是反思类，但'下周想试'天然带有计划属性，被用户当 to-do 用是合理的。下个版本要么明确这一格的定位（是反思 vs 计划），要么允许用户自定义。"
```

### Step 7 — Skill Usage 复盘

**自动统计**（基于 Step 0 chain context 读取）：
- 实际跑过的 Skill 列表
- 没跑过的 Skill 列表（且为什么没跑）

**用户补 主观评估**：

```yaml
- skill: "Frame"
  used: true
  value_delivered: "high"
  friction_points: ["对话 8 轮才收敛到方向，对急性子用户有点长"]
  suggestion: "Frame Phase 3 之前可以增加一个 quick-mode：3 个问题直接出 3 个方向，跳过 Phase 2 的深入探索"

- skill: "Audit"
  used: false
  value_delivered: "na"
  friction_points: []
  suggestion: "v1 是全新产品没用上 Audit；v2 改版时一定要用，提前规划"
```

**14 Skill 全部评估**（含 used: false 的）。

### Step 8 — Recommendations + 输出

#### 8.1 Recommendations（给 4 类受众）

每条建议必须可行动，包含 audience / recommendation / rationale：

```yaml
- audience: "self"
  recommendation: "下次设计周回顾类产品，在 Frame Phase 2D 假设映射时增加'用户付费意愿'类假设——本次因为没显式列，导致 v1 Pitch 时商业模型论证不够"
  rationale: "本次 Retro 发现，Brief 的 business_goal 含'团队付费转化率'但 Frame.critical_assumption 没对这个做假设，导致整个链路对'用户为什么会付费'的论证缺位"

- audience: "team"
  recommendation: "团队应建立'mobile 流量数据'共享看板，所有 Web 优先项目启动时都能看到当前产品 mobile 比例"
  rationale: "本次 v1 mobile 体验问题部分源于团队对 mobile 流量的预估偏低；如有共享数据可避免"

- audience: "next-project"
  recommendation: "下个项目如果是 v1 → v2 改版，必须先跑 Audit（不能直接跑 Frame）；Audit.opportunities 自动喂给 Brief 比从零推方向快 3 倍"
  rationale: "Retro 显示 v1 上线 3 个月真实暴露的问题，比 Frame 凭对话推的方向更准；改版项目应以数据为主导"

- audience: "organization"
  recommendation: "Pitch Skill 的 Ask 决策结果应该在组织级别归档，下次类似项目可参考；建议公司层面建立'设计决策案例库'"
  rationale: "本次 Pitch.asks#2 '团队功能延后到 v1.1' 的决策后果（leader 打开率低）应该作为案例让其他团队参考"
```

**audience 优先级**：self > team > next-project > organization（前两个必有，后两个可选）

#### 8.2 Markdown 报告（输出到对话 + 保存到 `spark-output/retro/[project-slug].md`）

```markdown
# Retro — [项目名]

- **生成时间**：[ISO8601]
- **项目周期**：[started_at] → [delivered_at]（计划 [planned] vs 实际 [actual]，[delta]）
- **复盘时间**：上线后 [N] 周
- **团队规模**：[N] 人

## 📊 Project Summary

[Step 1 信息]

## ⚖️ Decision Validation（5-10 个关键决策的事后判断）

### ✅ Validated
| 决策 | 来源 | 实际结果 | Lesson |
| --- | --- | --- | --- |
| ... | ... | ... | ... |

### ⚠️ Partially Validated
| ... |

### ❌ Refuted
| ... |

### ❓ Inconclusive
| ... |

## 🎯 Assumption Validation（关键假设验证）

[逐条详细对照]

## ✨ What Worked（3-5 个）

[每条带 why + keep_doing]

## ⚠️ What Didn't（3-5 个）

[每条带 root_cause + avoid_next_time]

## 💡 Surprises（2-4 个）

[每条带 learning]

## 🛠 Skill Usage 评估

| Skill | 用了 | 价值 | 痛点 | 建议 |
| --- | --- | --- | --- | --- |
| Frame | ✅ | high | ... | ... |
| Scope | ❌ | n/a | — | — |
| ... |

## 🎯 Recommendations

### 给自己
- [...]

### 给团队
- [...]

### 给下个项目
- [...]

### 给组织（如适用）
- [...]

---

## Lessons Learned 卡片（一页摘要，可分享）

**核心 lesson 3 条**（最值得带到下个项目的）：

1. [一句话 lesson]
2. [...]
3. [...]
```

#### 8.3 双通道 Context 输出

按 [chain-protocol.md](../../chain-protocol.md) 第 2.1 节执行。

**Step 1 — 写盘到 `spark-output/context/retro.json`**（必做，主持久化通道；目录不存在先创建）。写入以下完整 JSON：

```
{
  "skill": "retro",
  "generated_at": "<ISO8601>",
  "project_name": "...",
  "project_summary": {...},
  "decision_validation": [...],
  "assumption_validation": [...],
  "what_worked": [...],
  "what_didnt": [...],
  "surprises": [...],
  "skill_usage": [...],
  "recommendations": [...]
}
```

**Step 2 — chat 输出紧凑 marker**（必做，⛔ **不要在 chat 内重复输出 Step 1 的完整 JSON**）：

```
<!-- spark-context:retro ref="spark-output/context/retro.json" -->
Retro 已保存：project=[project_name]，[N] decisions（[validated]/[refuted]/[inconclusive]），[M] what_worked / [K] what_didnt / [S] surprises，[R] recommendations
<!-- /spark-context:retro -->
```

**降级 fallback**：若 Step 1 写盘失败（chat-only 平台），输出完整 JSON marker（无 ref 属性，marker 之间放裸 JSON）作为唯一持久化通道。

#### Handoff 提示（必输出）

> **协议**：按 [`_shared/next-skill.md`](../../_shared/next-skill.md) 三层结构模板输出；前 5 候选由 `_shared/skill-graph.json` 的依赖图算法实时算（done ⊆ ready，按 next_hint.preferred → alternatives → 同阶段 → anchor → fan-out 排序），优先建议从 `_shared/skill-graph.json#skills[id="retro"].next_hint` 读取。

**首行模板**：`✅ 设计复盘 已完成，全链 19 Skill 反思 + [N] lessons + [N] recommendations 已沉淀。`

**本 Skill 的 `next_hint`**（来自 skill-graph.json，**不可在此 SKILL.md 内硬编码覆盖**）：

- **preferred**：（终端节点）
- **优先理由**：本项目链路已闭环。可考虑：归档 spark-output/ 到项目仓库 / 把 Retro 摘要复制到团队 wiki / 开启下一个项目（清空 spark-output/context/）。
- **alternatives**：（无）
- **emoji**：🔁

**红线**：
- ❌ 禁止在本段硬编码候选清单（如「进入 Stories / Journey / Sitemap」）——所有候选必须由算法实时生成
- ❌ 禁止按「文档类 / 视觉类 / 决策类」再分类候选（v0.5.5 起，分类已折叠进 next_hint.alternatives）
- ❌ 禁止与「更新链路面板」段合并——两段必须各自独立成段，中间空一行
- ❌ 禁止漏第 2 行候选清单——即使候选只有 1 个、或为空（终端节点）也要写出来

---

## 实操注意事项

### 必须有数据才跑

如果项目没有埋点 / 没有上线后数据 / 没有用户反馈，**不要跑 Retro**——会变成主观感受堆砌。等数据齐了再跑。最少要有：
- Brief.design_criteria 中至少 1 条 quantitative 的实际数值
- 至少 1 个用户访谈或定性反馈

### Retro 跑早跑晚的权衡

- **上线后 2 周**：太早，数据不稳，建议跳过
- **上线后 4-8 周**：最佳——数据稳定 + 团队记忆还新
- **上线后 12+ 周**：太晚，团队成员可能调岗、记忆模糊

### Retro 不是 postmortem

- **postmortem**（事故复盘）：聚焦"出了什么事，怎么避免"
- **Retro**（设计复盘）：聚焦"决策过程对吗，下次怎么做更好"

设计师项目通常不需要 postmortem（除非出了严重事故），跑 Retro 即可。

### 与传统 Sprint Retrospective 的区别

| | Sprint Retro | Design Retro（本 Skill） |
| --- | --- | --- |
| 频率 | 每 2 周 | **每个项目 1 次** |
| 关注 | 流程效率（什么慢了） | **设计决策（押对了吗）** |
| 输出 | action items | **lessons learned + recommendations** |
| 时间窗 | 上个 sprint | **从 Frame 到上线后 N 周整段** |

设计师可以两者都做，但本 Skill 不替代 Sprint Retro。

---

## 已知限制

- **数据完整度依赖 Metric 是否埋好**——如果埋点缺失，assumption_validation 都是 inconclusive
- **AI 无法替代真人反馈**——团队成员的 surprises 和 friction_points 需要用户主动输入
- **lessons learned 的迁移性需要时间验证**——本 Skill 提取的 recommendations 是候选，真正有效要看下个项目跑后再 Retro 才能确认
- **不替代正式的 user research**（用 Probe Skill）
- **不替代项目复盘会议**——本 Skill 是会议前的结构化材料，不是会议本身

---

## 与兄弟 Skill / PM 套件的边界（v0.4.0 补充）

| 场景 | 用谁 | 不用谁 |
| --- | --- | --- |
| 项目上线后 / 阶段结束后的设计复盘 | **Retro** | Pitch（汇报）/ QA（验收） |
| 单次设计决策的快速反思 | Brief 内迭代记录 | Retro（Retro 是链路终端，跑全链） |
| 上线后效果度量 / KPI 评估 | Metric | Retro（Retro 引用 Metric 数据但不取代度量本身） |
| PM 套件「项目复盘」 | PM 套件（业务视角 KPI / ROI） | Retro（**设计视角**：流程问题 / 设计决策回顾 / 方法可复用性） |
| 团队回顾（KPT / 4Ls） | 独立团队会议 | Retro（Retro 是设计师个人 / 设计团队产物，不是跨职能 ceremony） |

**Retro 不可替代性**：链式终端——可读全链 14 个上游 Skill 产物，能做"决策回溯"（Brief 假设 vs 上线结果）和"链路上一处差到一步差全程"的根因分析，PM 套件无法做这种设计链路级的回溯。

## 质量标准

1. **跑全链上游**：必须读取本项目所有已有 Skill 产物（reads 全链 14 个），不能只看自己印象
2. **决策回溯**：每个 Brief.strategy_dimension 必须有"假设 vs 实际"二元结论（验证 / 部分验证 / 推翻）+ Metric 数据支撑
3. **lessons learned ≥ 5 条**：每条含 situation / action / outcome / takeaway 四要素，少一个不算合格
4. **recommendations 可执行**：每条建议含「下一项目何时应用」「需要的工具 / 模板更新」「owner」
5. **不只夸奖 / 不只批评**：必须含 went-well / went-wrong / surprises 三类，比例不悬殊（如全是 went-well 视为糖衣）
6. **链路改进项反向链**：发现的方法 / 流程问题要反向链回到具体上游 Skill 的待改进点（如 sitemap 该补什么字段）

## 红线规则

1. **不甩锅给团队 / 个人**：复盘聚焦流程 / 方法 / 决策，不指名批评——出现「XXX 没做好」时改写为「流程 XXX 缺一步检查」
2. **不忽略已知数据**：Metric 已经报数的指标必须引用，不能选择性陈述（出现「我们做得很好」但 Metric.task_completion_rate 没达标 → 红线）
3. **不替代正式上线评估**：Retro 是设计视角复盘，不是公司层面的业务复盘——业务 KPI / 财务影响不是 Retro 范围
