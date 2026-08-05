---
name: 用户旅程
name_en: "journey"
argument-hint: "输入目标用户与典型场景，如：电商商家完成一次新品上架的完整体验"
description: >
  用户旅程地图（User /用户旅程 Map）。基于 /问题框定.persona + /设计简报 等上游产出，按用户全生命周期阶段（Awareness → Consideration → Onboarding → Activation → Engagement → Retention → Advocacy）输出一张 HTML /用户旅程 Map 图——含每 stage 的 user goal / touchpoints / emotion curve / pain points / opportunities，可导出 PNG 作为设计师阶段性交付物。

  触发关键词：用户旅程、/用户旅程 Map、用户体验地图、Customer /用户旅程、CX Map、用户全生命周期、touchpoint、情感曲线、痛点地图。

  排除（反向）：单一场景的用户故事（用 /用户故事）、人物锚点（用 frame.persona）、IA 骨架（用 /站点地图）、流程图（用 flow-web/mobile）、改版前体验走查（用 /启发评估）。

description_en: >
  User Journey Map. Based on Frame.persona + Brief and other upstream outputs, generates an HTML
  Journey Map across the full user lifecycle (Awareness → Consideration → Onboarding → Activation
  → Engagement → Retention → Advocacy) — including user goals, touchpoints, emotion curve, pain
  points, and opportunities per stage. Exportable as PNG for design deliverables.

  Triggers when a designer says: "user journey", "Journey Map", "user experience map", "customer
  journey", "CX map", "user lifecycle", "touchpoint", "emotion curve", "pain point map",
  "journey".

  Excludes: single-scenario user stories (use /stories), persona anchor (use /frame),
  IA structure (use /sitemap), flow diagrams (use /flow-web or /flow-mobile),
  pre-redesign UX audit (use /audit).

allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - AskUserQuestion
chain:
  protocol_version: "1.0"
  reads: [frame, scope, audit, probe, signal, brief]
  writes: journey
  schema:
    skill: string
    generated_at: string
    project_name: string
    persona:
      name: string
      description: string
      jtbd: string
    journey_type: enum [end-to-end, onboarding-focused, retention-focused, recovery-focused, specific-flow]
    stages:
      - name: string
        emoji: string
        order: number
        user_goal: string
        touchpoints: array<string>
        actions: array<string>
        thoughts: array<string>
        emotion: enum [😊, 🙂, 😐, 😕, 😞, 😡]
        pain_level: number
        quotes: array<string>
        pain_points: array<string>
        opportunities: array<string>
    emotion_curve:
      - stage_order: number
        pain_level: number
    key_moments:
      - stage_order: number
        type: enum [moment-of-truth, dropout-risk, delight, recovery]
        description: string
    journey_file: string
---

# 用户旅程

> 你是用户旅程地图专家。基于上游的 persona + opportunities + audit findings，把用户跟产品的**全生命周期**（从听说到推荐）画成一张**HTML Journey Map 图**——含 emotion curve / touchpoints / pain points / opportunities——让设计师 / PM / 业务方一眼看到"用户在哪些 stage 流失、哪些 touchpoint 体验断、哪些 stage 有设计机会"。

**Journey 的核心价值不是 persona 的延伸**——而是把 persona 的"静态描述"扩展为"**用户跟产品互动的动态时间轴**"。

**与现有 Skill 的边界**：

| | Frame.persona | Stories | Sitemap | **Journey** |
| --- | --- | --- | --- | --- |
| 时间维度 | 单一时刻（who） | 单个任务（task） | 静态结构（pages） | **全生命周期（stages）** |
| 视角 | 用户是谁 | 用户做什么 | 系统有什么 | **用户在每 stage 想 / 感 / 触** |
| 输出 | 人物卡 | Story 文档 | 站点树 | **HTML 旅程图（可导出 PNG）** |

**适用场景**：
- 🌐 **SaaS / 复杂产品**：含 onboarding + 持续使用 + retention 多阶段
- 🔁 **改版项目**：在 Audit 之后用，把"现状问题"放进 journey 上更直观
- 📊 **跨部门对齐**：向业务方 / 客户成功团队展示用户完整旅程
- ⚠️ **不适合**：3 屏小工具 / 一次性使用产品 / MVP 早期

---

## Chain Context

### 上游读取（Step 0 执行）

按以下顺序尝试读取上下文：

1. 扫描会话中的 `<!-- spark-context:frame -->` / `<!-- spark-context:scope -->` / `<!-- spark-context:audit -->` / `<!-- spark-context:probe -->` / `<!-- spark-context:signal -->` / `<!-- spark-context:brief -->` marker
2. 读取项目目录 `spark-output/context/frame.json` / `scope.json` / `audit.json` 等
3. 都没有则进入 Step 1 询问基本信息

可复用字段映射：

- `frame.persona` → Journey 的 persona 锚点（必有）
- `frame.jtbd` → 决定 journey_type（onboarding-focused 重 Activation / retention-focused 重 Engagement+Retention）
- `frame.opportunities` → 分布到对应 stage 的 opportunities
- `audit.findings` → 改版项目时直接 map 到 stage 的 pain_points
- `signal.top_pain_points` → 工单分析的高频问题 map 到 stage
- `probe.themes` → 用户访谈洞察补充 pain_points / quotes
- `brief.business_goal` → 决定 key_moments 的标注重点（如 retention 目标 → 重点标 dropout-risk）

读到上下文后告知用户："读到 [N] 个上游 Skill 产出。Journey 将基于 [project_name] 的 persona [name] + [M] 个机会点 + [K] 条 audit findings 生成。预计 [N] stage。"

### 下游输出（Step 5 执行）

完成 Journey 后，**同时**做三件事：

1. **保存 HTML Journey Map 文件**（核心可视产物）：`spark-output/journey/[project-slug].html`
2. **会话内输出 chain context marker**（marker 之间放裸 JSON）：

   ```
   <!-- spark-context:journey -->
   {...JSON（schema 见 frontmatter，含 journey_file 引用 + stages 完整数据）...}
   <!-- /spark-context:journey -->
   ```

3. **写入项目文件**：`spark-output/context/journey.json`（含元数据 + stage 数据）

下游可消费 Skill：
- **Brief.strategy_dimensions** ← 每个 stage 高优先级 opportunity 转设计策略候选维度
- **Sitemap.pages** ← touchpoints 转 page 候选
- **Edge** ← 每个 stage 的异常态（如 onboarding-fail / activation-blocked）
- **Stories** ← 每个 stage 的 user actions 转候选 story

### 字段流向下游

- `journey.persona.jtbd` → **Stories** 的 JTBD 锚点；**PRD** 的 Personas 段输入
- `journey.stages[].sentiment` → **Stories** 的情感型 acceptance（"用户应感到放心"）；**PRD** 的体验目标段
- `journey.stages[].pain_points` → **Stories** 的修复型故事来源；**PRD** 的 Constraints & Risks
- `journey.stages[].touchpoints` → **Sitemap** 的页面候选；**Edge** 的状态矩阵覆盖范围
- `journey.stages[].opportunities` → **Brief** 的 strategy_dimensions 候选维度（仅高优先级 opportunity）
- `journey.key_moments[]` → **Stories** 的核心 story 候选；**PRD** 的 Solution 重点

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

- 用户说"画个 Journey Map / 用户旅程 / 体验地图 / customer journey"
- 用户说"画用户全流程 / 跨阶段体验 / touchpoint 地图"
- 用户使用 `/用户旅程` 指令
- 跑完 Frame / Audit 后，用户希望可视化用户全周期

---

---

## 独立能力（无需连接器）

本 Skill 在完全离线、无任何连接器的场景下即可完整交付，所有方法论与输出形态不依赖外部系统：

- **体验断点识别 + 情感曲线**：完整方法论与 HTML 可视化模板内置
- **链式上下文双通道**：写入 `spark-output/context/journey.json` + 会话内 marker block，下游 Brief / Stories / Flow Web/Mobile 可直接读取
- **HTML 一键导出**：本地浏览器即可生成 PNG / PDF 分享
- **多触点串联**：跨设备 / 跨场景体验路径本地可绘

> 红线：缺连接器时 **绝不 abort**，所有引导与输出路径必须照常完成。

## 增强能力（连接器加持）

接入以下连接器后，可减少手动粘贴、提高对齐效率。所有连接器均为可选，未装时按"降级路径"列的方式回落。

| 连接器 | 阶段 | 增强能力 | 降级路径 |
| --- | --- | --- | --- |
| **Notion / 飞书文档** | 执行流程输出后 | Journey HTML 一键写入团队 wiki，下游 Skill 可通过 wiki 链接反查 | 未装时输出本地 `journey-{project}.html`，提示手动上传 |
| **Figma** | 执行流程（触点关联阶段） | 每个触点直接引用对应设计稿 frame（含缩略图），评审时可一键跳转 | 未装时仅文字描述触点位置 |

**接入触发**：用户首次调用 `/用户旅程` 时，Skill 主动检测已认证的连接器并显示「已检测到：XXX，将自动启用增强模式」提示，用户可在该次会话中选择关闭。

**字段流向变化**：

- 启用 **Notion / 飞书文档** → `chain.schema` 新增可选字段 `wiki_page_url: string`
- 启用 **Figma** → `chain.schema` 新增可选字段 `touchpoint_refs: array<{stage, frame_url, thumbnail}>`

> 所有新增字段都是 **可选**，未启用连接器时字段缺省，下游 Skill 必须能容忍缺省。

---

## 执行流程

按 Step 0 → 1 → 2 → 3 → 4 → 5 顺序执行。

### Step 0 — Chain Context 读取

按上文执行。读到完整 Frame 上下文直接进入 Step 1 简化版。

### Step 1 — Journey Type + Stage 范围确认

用 `AskUserQuestion` 询问：

1. **Journey Type**：
   - **End-to-end**（完整 7 stage：Awareness → Consideration → Onboarding → Activation → Engagement → Retention → Advocacy）
   - **Onboarding-focused**（聚焦前 3 stage：Awareness → Consideration → Onboarding/Activation）
   - **Retention-focused**（聚焦 Engagement → Retention → Advocacy）
   - **Recovery-focused**（聚焦流失用户的回归路径）
   - **Specific-flow**（单个核心任务的细分 micro-journey，4-6 步）
2. **Stage 数量**：4-7（少于 4 信息不足，多于 7 视觉拥挤）

推荐：根据 `brief.business_goal` 自动建议——
- "提升新用户激活率" → onboarding-focused
- "降低 churn" → retention-focused
- "找设计机会" → end-to-end

### Step 2 — 每 Stage 数据填充

对每个 stage 填充以下字段（按上游字段映射 + 用户补充）：

**基础字段**（必填）：
- **name**：stage 名（中文 / 英文）
- **emoji**：1 个 emoji 视觉标识
- **user_goal**：用户在这个 stage 想完成什么（一句话）
- **touchpoints**：用户接触产品 / 信息的渠道 / 屏（3-5 条）
- **actions**：用户做了什么（动词起头，3-5 条）

**情感字段**（必填）：
- **thoughts**：用户的内心想法（2-3 条，第一人称："这功能怎么用？"）
- **emotion**：6 档 emoji（😊 喜悦 / 🙂 满意 / 😐 平淡 / 😕 困惑 / 😞 沮丧 / 😡 愤怒）
- **pain_level**：1-5 数字（用于绘制 emotion curve）

**研究素材字段**（可选，按上游有无填）：
- **quotes**：用户原话（来自 probe / signal），1-2 条
- **pain_points**：这个 stage 的具体痛点（2-4 条，来自 audit / signal / probe）
- **opportunities**：这个 stage 的设计机会（1-3 条，来自 frame.opportunities）

### Step 3 — Emotion Curve + Key Moments 标注

#### Emotion Curve

把每个 stage 的 pain_level 串成折线图数据：

```yaml
emotion_curve:
  - stage_order: 1
    pain_level: 2
  - stage_order: 2
    pain_level: 1
  - stage_order: 3
    pain_level: 4  ← 急剧下降，是 dropout-risk 关键点
  ...
```

#### Key Moments（关键标注）

自动识别 4 类关键时刻并标注：

| Type | 自动识别规则 |
| --- | --- |
| **moment-of-truth** | 决定用户去留的关键交互（通常是 Activation 阶段的"首次成功"） |
| **dropout-risk** | 连续 2 个 stage 的 pain_level 上升 ≥ 2 档 |
| **delight** | pain_level ≤ 1（满意度峰值） |
| **recovery** | 从 dropout-risk 之后又 pain_level 下降的 stage |

### Step 4 — 生成 HTML Journey Map

使用以下**内嵌模板**生成 `spark-output/journey/[project-slug].html`：

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <title>{{project_name}} — User Journey Map</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", sans-serif; }
    body { padding: 32px; background: #FAFAF7; color: #1F2937; }
    .header { margin-bottom: 24px; }
    .title { font-size: 28px; font-weight: 700; margin-bottom: 8px; }
    .subtitle { font-size: 14px; color: #6B7280; }
    .persona-card { display: inline-flex; align-items: center; padding: 12px 20px; background: white; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); margin: 16px 0 32px; }
    .persona-avatar { width: 40px; height: 40px; border-radius: 50%; background: linear-gradient(135deg, #6366F1, #EC4899); margin-right: 12px; display: flex; align-items: center; justify-content: center; color: white; font-weight: 600; }
    .persona-info { font-size: 13px; }
    .persona-info b { display: block; font-size: 15px; color: #111827; }
    .persona-info span { color: #6B7280; }
    .jtbd { font-style: italic; padding: 12px 16px; background: #FEF3C7; border-left: 4px solid #F59E0B; border-radius: 4px; margin-bottom: 32px; font-size: 14px; }
    .journey-grid { display: grid; grid-template-columns: 120px repeat({{stage_count}}, 1fr); gap: 1px; background: #E5E7EB; border-radius: 12px; overflow: hidden; }
    .grid-row { display: contents; }
    .row-label, .stage-cell { background: white; padding: 14px 12px; font-size: 12px; }
    .row-label { background: #F3F4F6; font-weight: 600; color: #4B5563; display: flex; align-items: center; }
    .stage-header { background: #1F2937; color: white; padding: 16px 12px; font-size: 13px; font-weight: 600; text-align: center; }
    .stage-header .emoji { font-size: 24px; display: block; margin-bottom: 4px; }
    .stage-cell ul { list-style: none; }
    .stage-cell li { padding: 4px 0; line-height: 1.4; }
    .stage-cell li:before { content: "·"; color: #9CA3AF; margin-right: 6px; }
    .emotion-cell { font-size: 28px; text-align: center; padding: 16px; }
    .pain-bar { height: 4px; background: linear-gradient(to right, #10B981, #F59E0B, #EF4444); border-radius: 2px; margin-top: 8px; }
    .pain-indicator { height: 8px; margin-top: 4px; display: flex; gap: 2px; }
    .pain-indicator span { flex: 1; height: 100%; background: #E5E7EB; border-radius: 1px; }
    .pain-indicator span.active { background: currentColor; }
    .key-moment-badge { display: inline-block; padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: 600; margin-top: 4px; }
    .key-moment-badge.truth { background: #EFF6FF; color: #2563EB; }
    .key-moment-badge.dropout { background: #FEE2E2; color: #DC2626; }
    .key-moment-badge.delight { background: #D1FAE5; color: #059669; }
    .key-moment-badge.recovery { background: #FEF3C7; color: #D97706; }
    .opportunity { background: #ECFDF5; padding: 6px 8px; border-radius: 4px; font-size: 11px; color: #047857; margin: 3px 0; }
    .quote { font-style: italic; color: #4B5563; padding: 6px 8px; background: #F9FAFB; border-left: 3px solid #D1D5DB; font-size: 11px; margin: 3px 0; }
    .curve-section { margin-top: 32px; padding: 24px; background: white; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
    .curve-title { font-size: 16px; font-weight: 600; margin-bottom: 16px; }
    .curve-svg { width: 100%; height: 120px; }
    .footer { margin-top: 24px; text-align: center; color: #9CA3AF; font-size: 11px; }
    @media print { body { padding: 16px; } .journey-grid { page-break-inside: avoid; } }
    .toolbar { position: fixed; top: 16px; right: 16px; display: flex; gap: 8px; }
    .toolbar button { padding: 8px 16px; background: #1F2937; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 13px; }
    .toolbar button:hover { background: #374151; }
  </style>
</head>
<body>
  <div class="toolbar">
    <button onclick="window.print()">打印 / PDF</button>
  </div>

  <div class="header">
    <div class="title">{{project_name}} — User Journey Map</div>
    <div class="subtitle">生成时间: {{generated_at}} · 数据源: {{source_skills}}</div>
  </div>

  <div class="persona-card">
    <div class="persona-avatar">{{persona_initial}}</div>
    <div class="persona-info">
      <b>{{persona_name}}</b>
      <span>{{persona_description}}</span>
    </div>
  </div>

  <div class="jtbd">{{jtbd}}</div>

  <div class="journey-grid" style="grid-template-columns: 120px repeat({{stage_count}}, 1fr);">
    <!-- 表头行 -->
    <div class="row-label"></div>
    {{#each stages}}
    <div class="stage-header">
      <span class="emoji">{{emoji}}</span>
      {{name}}
    </div>
    {{/each}}

    <!-- User Goal -->
    <div class="row-label">用户目标</div>
    {{#each stages}}<div class="stage-cell">{{user_goal}}</div>{{/each}}

    <!-- Actions -->
    <div class="row-label">用户行动</div>
    {{#each stages}}<div class="stage-cell"><ul>{{#each actions}}<li>{{this}}</li>{{/each}}</ul></div>{{/each}}

    <!-- Touchpoints -->
    <div class="row-label">触点</div>
    {{#each stages}}<div class="stage-cell"><ul>{{#each touchpoints}}<li>{{this}}</li>{{/each}}</ul></div>{{/each}}

    <!-- Thoughts -->
    <div class="row-label">用户心声</div>
    {{#each stages}}<div class="stage-cell"><ul>{{#each thoughts}}<li>"{{this}}"</li>{{/each}}</ul></div>{{/each}}

    <!-- Emotion -->
    <div class="row-label">情绪</div>
    {{#each stages}}
    <div class="stage-cell emotion-cell">
      {{emotion}}
      <div class="pain-indicator" style="color: {{pain_color}};">
        <span class="{{#if pain_1}}active{{/if}}"></span>
        <span class="{{#if pain_2}}active{{/if}}"></span>
        <span class="{{#if pain_3}}active{{/if}}"></span>
        <span class="{{#if pain_4}}active{{/if}}"></span>
        <span class="{{#if pain_5}}active{{/if}}"></span>
      </div>
      {{#if key_moment}}<span class="key-moment-badge {{key_moment_type}}">{{key_moment_label}}</span>{{/if}}
    </div>
    {{/each}}

    <!-- Pain Points -->
    <div class="row-label">痛点</div>
    {{#each stages}}<div class="stage-cell"><ul>{{#each pain_points}}<li>{{this}}</li>{{/each}}</ul></div>{{/each}}

    <!-- Quotes -->
    <div class="row-label">用户原话</div>
    {{#each stages}}<div class="stage-cell">{{#each quotes}}<div class="quote">"{{this}}"</div>{{/each}}</div>{{/each}}

    <!-- Opportunities -->
    <div class="row-label">设计机会</div>
    {{#each stages}}<div class="stage-cell">{{#each opportunities}}<div class="opportunity">💡 {{this}}</div>{{/each}}</div>{{/each}}
  </div>

  <div class="curve-section">
    <div class="curve-title">📈 情感曲线（Pain Level over Journey）</div>
    <svg class="curve-svg" viewBox="0 0 {{curve_width}} 120" preserveAspectRatio="none">
      <!-- 网格线 -->
      <line x1="0" y1="20" x2="{{curve_width}}" y2="20" stroke="#E5E7EB" stroke-dasharray="2" />
      <line x1="0" y1="60" x2="{{curve_width}}" y2="60" stroke="#E5E7EB" stroke-dasharray="2" />
      <line x1="0" y1="100" x2="{{curve_width}}" y2="100" stroke="#E5E7EB" stroke-dasharray="2" />
      <!-- 折线 -->
      <polyline
        points="{{curve_points}}"
        fill="none" stroke="#6366F1" stroke-width="3"
        stroke-linejoin="round" stroke-linecap="round" />
      <!-- 数据点 -->
      {{#each curve_dots}}
      <circle cx="{{x}}" cy="{{y}}" r="6" fill="{{color}}" stroke="white" stroke-width="2" />
      {{/each}}
    </svg>
  </div>

  <div class="footer">
    Generated by SparkSkillsHub Journey Skill · Persona: {{persona_name}} · {{stage_count}} stages
  </div>
</body>
</html>
```

**生成规则**：

1. 用 Read 读取本 SKILL.md 中的上述模板
2. **不要凭记忆重建**——必须读取模板再做字段替换
3. `{{#each stages}}` / `{{#if pain_X}}` 是简化模板语法，**生成时按 stage 数据展开**（不是 Handlebars 真渲染，是 AI 按规则填）
4. `{{persona_initial}}` 取 persona_name 的第一个字
5. `{{pain_color}}`：pain_level=1 → #10B981 / 2 → #34D399 / 3 → #F59E0B / 4 → #F97316 / 5 → #EF4444
6. `{{curve_points}}`：将 emotion_curve 转为 SVG polyline points 字符串。x 坐标 = (i / (stage_count-1)) * curve_width；y 坐标 = (pain_level - 1) * 25 + 10
7. `{{curve_dots}}`：每个数据点的圆，颜色按 pain_color
8. `{{key_moment_label}}` 映射：moment-of-truth → "关键时刻" / dropout-risk → "流失风险" / delight → "满意峰值" / recovery → "体验回升"
9. `{{curve_width}}` 默认 1200

最终输出 HTML 是**完整自包含文件**（CSS 内嵌，无外部依赖），可双击打开 / 打印 / 导出 PDF。

### Step 5 — 输出

#### 5.1 保存 HTML 文件

路径：`spark-output/journey/[project-slug].html`

告知用户："Journey Map HTML 已保存。双击打开可在浏览器查看；点'打印 / PDF'按钮可导出 PDF；如需 PNG 截图可用浏览器截图工具或 modern-screenshot 库。"

#### 5.2 双通道 Context 输出

按 [chain-protocol.md](../../chain-protocol.md) §2.1 v1.1 智能适配规则：

**Step 1 — 写盘到 `spark-output/context/journey.json`**（必做，主持久化通道；目录不存在先创建）。写入以下完整 JSON：

```
{
  "skill": "journey",
  "generated_at": "<ISO8601>",
  "project_name": "...",
  "persona": {
    "name": "...",
    "description": "...",
    "jtbd": "..."
  },
  "journey_type": "end-to-end|onboarding-focused|retention-focused|recovery-focused|specific-flow",
  "stages": [
    {
      "name": "Awareness",
      "emoji": "👀",
      "order": 1,
      "user_goal": "...",
      "touchpoints": ["..."],
      "actions": ["..."],
      "thoughts": ["..."],
      "emotion": "😐",
      "pain_level": 2,
      "quotes": ["..."],
      "pain_points": ["..."],
      "opportunities": ["..."]
    }
  ],
  "emotion_curve": [
    { "stage_order": 1, "pain_level": 2 }
  ],
  "key_moments": [
    { "stage_order": 4, "type": "moment-of-truth", "description": "..." },
    { "stage_order": 5, "type": "dropout-risk", "description": "..." }
  ],
  "journey_file": "spark-output/journey/[project-slug].html"
}
```

**Step 2 — chat 输出紧凑 marker**（必做，⛔ **不要在 chat 内重复输出 Step 1 的完整 JSON**）：

```
<!-- spark-context:journey ref="spark-output/context/journey.json" -->
Journey 已保存：project=[project_name]，persona=[name]，[N] stage（type=[end-to-end/...]），[K] 个 key_moments；HTML 已写到 spark-output/journey/[slug].html
<!-- /spark-context:journey -->
```

**降级 fallback**：若 Step 1 写盘失败（chat-only 平台），输出完整 JSON marker（无 ref 属性，marker 之间放裸 JSON）作为唯一持久化通道。

#### Handoff 提示（必输出）

> **协议**：按 [`_shared/next-skill.md`](../../_shared/next-skill.md) 三层结构模板输出；前 5 候选由 `_shared/skill-graph.json` 的依赖图算法实时算（done ⊆ ready，按 next_hint.preferred → alternatives → 同阶段 → anchor → fan-out 排序），优先建议从 `_shared/skill-graph.json#skills[id="journey"].next_hint` 读取。

**首行模板**：`✅ 用户旅程 已完成，[N] stage / [K] 个 key moments / [n] 个 dropout-risk / HTML 已写出。`

**本 Skill 的 `next_hint`**（来自 skill-graph.json，**不可在此 SKILL.md 内硬编码覆盖**）：

- **preferred**：`/stories`
- **优先理由**：旅程断点 + 情感低谷已识别，进 Stories 把每个触点拆成可执行用户故事。
- **alternatives**：`/sitemap` (想先搭 IA 骨架再回头做故事) · `/flow-web` (项目较紧、想直接进页面级设计)
- **emoji**：📋

**红线**：
- ❌ 禁止在本段硬编码候选清单（如「进入 Stories / Journey / Sitemap」）——所有候选必须由算法实时生成
- ❌ 禁止按「文档类 / 视觉类 / 决策类」再分类候选（v0.5.5 起，分类已折叠进 next_hint.alternatives）
- ❌ 禁止与「更新链路面板」段合并——两段必须各自独立成段，中间空一行
- ❌ 禁止漏第 2 行候选清单——即使候选只有 1 个、或为空（终端节点）也要写出来

---

## 实操注意事项

### Stage 数量决策

| Journey Type | 推荐 stage 数 |
| --- | --- |
| End-to-end | 6-7 |
| Onboarding-focused | 4-5 |
| Retention-focused | 4-5 |
| Specific-flow | 4-6 |

### 数据稀疏时的处理

如果上游只有 Frame（无 audit / probe / signal），quotes 和 pain_points 会比较稀疏。这种情况：

- 在 HTML 中显示"暂无用户原话——建议跑 Probe 补充"
- 在 chain context schema 中 quotes 字段允许为空数组
- 不要凭空编造 quotes（伪造用户声音 = 设计师最大的禁忌）

### Emotion Curve 的设计意义

情感曲线是 Journey Map 最有传播力的部分——业务方 / 高管能一眼看到"用户在第几 stage 体验最差"。请保证：

- 至少有 1 个 stage pain_level ≥ 3（否则曲线平淡无信息）
- 至少有 1 个 dropout-risk 标注（否则没有"哪里要改"的判断）
- 不要刻意美化曲线——真实的曲线才有指导价值

### 与 Audit 的强协同

改版项目跑 Audit 后，**强烈建议立即跑 Journey**——audit.findings 可以直接 map 到对应 stage 的 pain_points，让"诊断结果"变成"用户视角的故事"。

---

## 已知限制

- 不替代真实的用户研究（建议 Journey 之前跑 Probe）
- HTML 模板是单视图，不支持多 persona 对比（多 persona 项目需跑多次）
- 数据稀疏时 HTML 部分单元格会空（视觉接受度需用户判断）
- 中文长文案可能在表格单元格内溢出，必要时手工调字号
- 不支持 swimlane 多角色泳道（如需 leader/admin/user 多视角，跑多个 single-role journey 拼接）

---

## 与兄弟 Skill / PM 套件的边界（v0.4.0 补充）

| 场景 | 用谁 | 不用谁 |
| --- | --- | --- |
| 画用户旅程图（阶段 / 触点 / 情感曲线 / dropout） | **Journey** | Brief（一页纸对齐）/ Stories（拆故事） |
| 单个场景任务流（一条 happy path 多屏） | Flow Web / Flow Mobile | Journey（跨阶段 / 跨触点） |
| 体验断点的根因深挖（5-8 人访谈） | Probe | Journey（用 Probe 输入但不做访谈本身） |
| PM 套件「用户旅程地图」 | PM 套件（业务流程视角） | Journey（**体验视角**：情感曲线 / 体验断点 / 设计触点） |
| 战略机会点提炼（HMW 映射） | Frame Phase 3.5 / HMW | Journey（输出旅程不输出 HMW 卡片） |

**Journey 的不可替代性**：跨阶段 × 跨触点 × 情感曲线三维同时呈现，是设计师专属视角。PM 的「用户旅程」更偏业务流程节点，没有情感曲线 / dropout-risk 标注。

## 质量标准

1. **阶段划分清晰**：≥ 3 个阶段（如 Awareness / Consideration / Action / Retention），每阶段含目标 + 关键行为
2. **触点完整**：每阶段列出 user touchpoints（页面 / 渠道 / 设备），与 sitemap 可对齐
3. **情感曲线有据**：emotion score（-2 ~ +2）每个节点都标，且能引用上游证据（probe.painpoints / signal.top_issues / audit findings）
4. **dropout-risk 显式标注**：高风险节点必须打 ⚠️，并写出可能原因（≥ 1 条上游证据支撑）
5. **设计机会点反向链接**：每个 dropout / 低情感节点对应至少 1 个设计机会（指向 Brief.strategy_dimensions 或 HMW 卡片）
6. **HTML 可视化输出**：必须生成 `spark-output/journey/[slug].html`（含情感曲线 SVG / 阶段卡片 / 触点图标），不只是 markdown 表格

## 红线规则

1. **不凭空标情感曲线**：emotion score 必须有上游证据（Probe 访谈引用 / Signal 工单引用 / Audit findings），无证据时标灰并备注「待验证」
2. **不替代 Probe 用研**：Journey 是综合呈现层，不是访谈方法本身——没有 Probe 数据时只能产出 hypothesis journey，必须在 HTML 顶部标「假设性」红章
3. **不替代 Flow（任务流）**：Journey 跨阶段跨触点，Flow Web/Mobile 才是单场景多屏流程——两者粒度不同，不能互相覆盖
