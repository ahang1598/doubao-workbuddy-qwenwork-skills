---
name: 数据可视化
name_en: "chart"
argument-hint: "输入要可视化的数据场景，如：销售 Dashboard 首屏（KPI 卡 + 月度趋势 + 区域分布）"
description: >
  数据可视化设计规格。给定一个 Dashboard / 报表页 / 数据卡片的需求，按"意图分类 → 数据约束 → 选型 → 视觉规范 → 异常态 → 响应式降级"六步产出可交付的图表设计规格文档（不是临时画图工具）。每张图含选型理由、design token 映射、SparkDesign 组件契约、色盲安全校验、Mobile 降级方案。让设计师不必凭直觉选图、不必反复对齐主题色、不必到 QA 阶段才发现"图表在手机上挤成一团"。

  触发关键词：数据可视化、图表设计、Dashboard、报表、数据卡片、KPI 卡、图表选型、chart design、dashboard design、data viz、可视化规格、图表规范。

  排除（反向）：临时生成一张图（用 AI 直接画 / chart-visualization 工具）、产品数据指标定义（用 PM 套件 /产品指标复盘）、设计度量指标体系（用 /设计度量）、图表组件库实现（属于 SparkDesign 仓库工作，不在本 Skill）。

description_en: >
  Data visualization design specification. Given a dashboard, report page, or data card requirement,
  produces a deliverable chart design spec through 6 steps: intent classification → data constraints →
  chart selection → visual spec → empty/error states → responsive degradation. Every chart includes
  selection rationale, design token mapping, SparkDesign component contract, colorblind-safe palette check,
  and mobile degradation plan. So designers don't pick charts by gut, don't re-align theme colors repeatedly,
  and don't discover at QA stage that charts collapse on mobile.

  Triggers when a designer says: "data viz", "chart design", "dashboard", "KPI card", "report page",
  "chart selection", "visualization spec", "数据可视化", "图表选型", "Dashboard 设计".

  Excludes: one-off chart rendering (use AI / chart-visualization tool), product metric definition
  (use PM-suite /metric-review), design measurement metrics (use /metric), chart component library
  implementation (lives in SparkDesign repo, not this Skill).

allowed-tools:
  - Read
  - Write
  - Glob
  - Grep
  - Bash
  - AskUserQuestion
chain:
  protocol_version: "1.0"
  reads: [brief, sitemap, flow-web, flow-mobile, board]
  writes: chart
  schema:
    skill: string
    generated_at: string
    project_name: string
    surface: enum [dashboard, report-page, data-card, embedded-chart, mixed]
    charts:
      - chart_id: string
        screen: string
        screen_id: string
        intent: enum [comparison, trend, part-of-whole, distribution, relationship, flow, hierarchy, single-value]
        chart_type: enum [bar, column, line, area, dual-axes, pie, donut, treemap, scatter, bubble, heatmap, histogram, boxplot, funnel, radar, sankey, waterfall, kpi-card, sparkline, gauge, table]
        rationale: string
        data_shape:
          dimensions: number
          series: number
          data_points: number
          time_granularity: string
          has_target: boolean
          has_benchmark: boolean
        visual_spec:
          width_token: string
          height_token: string
          palette: enum [categorical, sequential, diverging, single-hue, brand-accent]
          palette_tokens: array<string>
          y_axis_start: enum [zero, auto, custom]
          annotation: array<string>
          direct_label: boolean
          legend_position: enum [none, top, right, bottom, inline]
        interaction:
          hover: string
          click: string
          filter: string
        states:
          empty: string
          loading: string
          error: string
          single_point: string
          overflow: string
        responsive:
          desktop: string
          tablet: string
          mobile_degradation: enum [simplify, swap-chart-type, table, sparkline, hide]
          mobile_spec: string
        accessibility:
          colorblind_safe: boolean
          contrast_ratio_pass: boolean
          aria_label: string
          keyboard_navigable: boolean
        sparkdesign_contract:
          component: string
          tokens_used: array<string>
          gap_to_fill: string
        preview:
          generated: boolean
          provider: enum [antv-gpt-vis, none]
          antv_type: string
          request_body: object
          image_url: string
          generated_at: string
          fallback_reason: string
    dashboard_layout:
      grid: string
      reading_path: enum [F-shape, Z-shape, top-down, custom]
      density: enum [sparse, balanced, dense]
      sections:
        - section: string
          purpose: string
          charts: array<string>
    palette_policy:
      categorical_tokens: array<string>
      sequential_token_set: string
      diverging_token_set: string
      colorblind_check: enum [pass, fail, na]
    coverage:
      total_charts: number
      by_intent:
        comparison: number
        trend: number
        part-of-whole: number
        distribution: number
        relationship: number
        flow: number
        hierarchy: number
        single-value: number
      mobile_degraded: number
      a11y_pass: number
      sparkdesign_gaps: array<string>
    implementation_recommendation:
      detected_stack:
        framework: enum [react, vue, svelte, react-native, vanilla, unknown]
        ui_library: enum [shadcn, antd, mui, chakra, element-plus, naive-ui, sparkdesign, custom, none, unknown]
        existing_chart_libs: array<string>
        data_scale: enum [small, medium, large, huge]
        special_needs: array<string>
        detection_sources: array<string>
      candidates:
        - library: string
          score: number
          pros: array<string>
          cons: array<string>
          bundle_kb_gzip: number
      recommended:
        library: string
        rationale: string
        install_command: string
        bundle_impact: string
        sparkdesign_alignment: enum [official, compatible, neutral, conflict, na]
      switch_triggers: array<string>
      confidence: enum [high, medium, low]
---

# 数据可视化

> 你是数据可视化设计专家。设计师做 Dashboard / 报表 / 数据卡片时最常踩三个坑：**选错图**（用饼图画 12 个分类）、**画好看了但失真**（柱图 y 轴不从 0 / 双 Y 轴乱配对）、**到 Mobile 全垮**。本 Skill 按 "**意图 → 约束 → 选型 → 规格 → 状态 → 响应式**" 六步，把每张图变成可直接进入 Flow Web/Mobile 复用的**设计规格条目**，并强制对齐 SparkDesign token 与色盲安全调色板。
>
> **v1 范围**：核心是"选型 + 视觉规格 + 链路接入"，产出纯 Markdown 规格文档，覆盖 80% 设计师场景。
>
> **v1.1 增量**：叠加 **AntV GPT-Vis API 一键 mock 预览**——每个图表规格条目可选生成一张预览图 URL，写回 chart.json 的 `preview.image_url`，让设计师 / PM / 工程师在评审时直接看图，不必脑补"line 图大致长这样"。预览是**可选**的，不影响 v1 的规格文档主流程。
>
> **v1.2 增量**（本版本）：新增 **Step 3.6 工程实现库智能推荐**——基于检测到的技术栈（React/Vue/RN × shadcn/antd/自研 × 已安装的 chart 库 × 数据规模）给出**至少 2 个候选 + 1 个首选 + 切换触发条件**，避免 AI 在 React+shadcn 项目里盲推 AntV、在 React+antd 项目里盲推 Recharts。SparkDesign / 公司战略偏好可注入为加分项。

**与现有 Skill 的边界**：

| | Chart（本 Skill） | Flow Web / Flow Mobile | Edge | Metric | PM /产品指标复盘 |
| --- | --- | --- | --- | --- | --- |
| 阶段 | 03 Design | 03 Design | 03 Design | 04 Validate | PM 套件 |
| 关注 | **图表选型 + 视觉规格** | 页面整体 IA 与组件布局 | 异常态穷举 | 设计阶段定义跟踪指标 | 产品指标体系拆解 |
| 输入 | brief + sitemap + flow | brief + sitemap + stories | brief + sitemap + flow | brief + stories + flow | （PM 自有上下文） |
| 输出 | 每图选型理由 + 规格 + 降级 | 屏与导航结构 | 状态矩阵 | 指标定义 + 度量计划 | 指标拆解 + 复盘 |
| 不做 | 不定义"该看什么指标" | 不做单图视觉规格 | 不做主流程 | 不画图表 | 不画图表 |

**核心差异**：Metric / PM-指标复盘 关心**看哪些数（What）**；Chart 关心**怎么把数画对（How）**。Flow Web/Mobile 负责"页面里有几个图表区"；Chart 负责"每个图表区里到底放什么图、怎么画"。

**设计原则**（贯穿整个执行流程）：

- **Data-ink ratio 优先**：能少一根装饰线就少一根；用户记住的是数据本身，不是图表的装饰
- **直接标注 > 图例**：图上能直接写数值或类别就别用 legend，用户视线不必来回跳
- **简单胜过炫技**：能用 bar 解决就不用 radar；能用 table 解决就不用 heatmap
- **色彩有秩序**：连续 vs 发散 vs 分类三种调色板**绝对不能混用**
- **Mobile 不是 Desktop 的等比缩放**：超过 5 个数据点的图在 Mobile 上几乎都要换形

---

## Chain Context

### 上游读取（Step 0 执行）

按以下顺序尝试读取上下文：

1. 扫描会话中的 `<!-- spark-context:brief -->` / `<!-- spark-context:sitemap -->` / `<!-- spark-context:flow-web -->` / `<!-- spark-context:flow-mobile -->` marker
2. 读取项目目录 `spark-output/context/brief.json` / `sitemap.json` / `flow-web.json` / `flow-mobile.json`
3. **可选**：若已有 `spark-output/context/edge.json`，读取 `states_matrix` 中关联屏的 `empty / error / loading` 状态描述作为图表状态文案依据
4. 都没有则进入 Step 1 询问数据可视化场景

可复用字段映射：

- `brief.objective` → 业务意图分类的依据（增长型 / 监控型 / 诊断型）
- `brief.user.primary` → 阅读路径选择（C 端用户偏 F 形 + 大字号；运营/分析师可接受 dense 布局）
- `brief.strategy_dimensions['情感化设计']` / `brief.tone` → 调色板调性（保守 / 鲜明 / 品牌强调）
- `brief.constraints` → 影响 mobile 降级激进度（如"4 周上线" → mobile 直接用 table 降级，不做精细化图表）
- `sitemap.pages` → 定位 Dashboard / 报表页在哪个层级（决定信息密度上限）
- `flow-web.flows[*].screens` / `flow-mobile.flows[*].screens` → 图表所在屏的容器尺寸、上下文（独占屏 vs 卡片中嵌入）
- `edge.states_matrix[]`（可选）→ 屏级别的 empty / loading / error 描述，图表层复用

读到上下文后告知用户："检测到 [项目名] 的 [N] 个数据可视化承载屏（来自 [flow-web / sitemap]），将按意图 → 约束 → 选型六步产出每图规格，预计 [估算] 个图表条目。"

### 下游输出（Step 4 执行）

完成 Chart 后，**同时**做三件事：

1. **写盘到 `spark-output/context/chart.json`**（必做，主持久化通道；目录不存在先创建）
2. **会话内输出紧凑 marker**（带 ref，不重复 JSON）
3. **额外保存 Markdown 报告**：`spark-output/chart/[project-slug].md`，含每图完整规格 + Dashboard 布局图（文字版）+ SparkDesign gap 清单

下游可消费 Skill：**Flow Web / Flow Mobile**（在含图表区的屏上叠加 Chart 输出的规格）/ **Edge**（图表状态条目可作为 edge.states_matrix 的"图表级"细化补充）/ **Check**（验"图表选型理由是否站得住、调色板是否合规"）/ **Access**（强制校验色盲安全 + ARIA label）/ **QA**（验前端实现是否对齐 design token）/ **Metric**（图表里展示的字段反推度量计划）。

### 字段流向下游

- `chart.charts[].chart_type` + `rationale` → **Pitch** 的"考虑过的其他方向"素材（图表选型决策可作为 Asks 候选）
- `chart.charts[].visual_spec.palette_tokens` → **QA** 还原度核查清单的"颜色"维度基线
- `chart.charts[].accessibility` → **Access** WCAG 检查的图表专项条目（colorblind / contrast / ARIA / keyboard 四项直接对账）
- `chart.charts[].responsive.mobile_degradation` → **Flow Mobile** 的图表区改写依据；**Check** 跑响应式类别时的对照表
- `chart.charts[].states` → **Edge** 的 states_matrix 图表细化补充（screen 级别状态外，加 chart 级别状态）
- `chart.charts[].sparkdesign_contract.gap_to_fill` → **SparkDesign 仓库**的图表组件需求列表（设计系统层反向输入，孵化 AG-UI Design Spec 中的图表规范）
- `chart.dashboard_layout` → **PRD** 的"信息架构"章节素材
- `chart.coverage.sparkdesign_gaps` → **Retro** 的"工具债 / 系统债"输入

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

---

## 触发条件

- 用户说"做个 Dashboard / 报表 / 数据卡片 / KPI 卡"
- 用户说"这页要展示销售数据 / 用户增长 / 转化漏斗"
- 用户说"帮我选个图 / 这种数据用什么图好"
- 用户说"图表在手机上怎么放"
- 用户使用 `/数据可视化` 或 `/chart` 指令
- Flow Web/Mobile 完成主流程后，若屏内含 `chart-region` / `kpi-card` 组件位，建议接 Chart 出规格

---

---

## 独立能力（无需连接器）

本 Skill 在完全离线、无任何连接器的场景下即可完整交付，所有方法论与输出形态不依赖外部系统：

- **六步决策链**：意图 → 数据约束 → 选型 → 视觉规格 → 状态 → 响应式全本地完成
- **链式上下文双通道**：写入 `spark-output/context/chart.json` + 会话内 marker block，下游 Flow Web/Mobile / PRD / QA 可直接读取
- **AntV gpt-vis mock 预览（v1.1）**：一键 curl 生成静态预览图，与工程实现解耦
- **工程库智能推荐（v1.2）**：本地 package.json 检测 + 11 种栈映射 + score 打分公式
- **SparkDesign 反向输入清单**：Dashboard 通用组件需求本地汇总

> 红线：缺连接器时 **绝不 abort**，所有引导与输出路径必须照常完成。

## 增强能力（连接器加持）

接入以下连接器后，可减少手动粘贴、提高对齐效率。所有连接器均为可选，未装时按"降级路径"列的方式回落。

| 连接器 | 阶段 | 增强能力 | 降级路径 |
| --- | --- | --- | --- |
| **Figma** | 执行流程（视觉规格阶段） | 引用现有 Dashboard frame 作为视觉对照，校验 Chart 配色 / 字号 / 间距是否与全局一致 | 未装时仅引用 design token 文件，不做 frame 比对 |
| **GitHub** | 执行流程 Step 3.6（工程库推荐） | 扫远程仓库 package.json + 已有图表组件，提升推荐准确度（本地模式于 v0.5.1 patch 已设计） | 未装时退回本地仓库扫描，准确度略降但不阻断 |

**接入触发**：用户首次调用 `/数据可视化` 时，Skill 主动检测已认证的连接器并显示「已检测到：XXX，将自动启用增强模式」提示，用户可在该次会话中选择关闭。

**字段流向变化**：

- 启用 **Figma** → `chain.schema` 新增可选字段 `dashboard_refs: array<{frame_url, page}>`
- 启用 **GitHub** → 现有 `chart_library_recommendation` 字段的 `signal_source` 子段新增 `github_repo` 来源

> 所有新增字段都是 **可选**，未启用连接器时字段缺省，下游 Skill 必须能容忍缺省。

---

## 执行流程

按 Step 0 → 1 → 2 → 3 → 4 顺序执行。**核心是 Step 2 的"意图 → 约束 → 选型"两层决策**——选型不是看着图表库挑好看的，而是从用户想表达什么倒推。

### Step 0 — Chain Context 读取

按上文执行。读到完整上下文（brief + flow 任一）直接进入 Step 2。

### Step 1 — 场景确认（仅当 Step 0 无足够上下文）

用 `AskUserQuestion` 确认：

1. **可视化表面类型**（surface）：
   - Dashboard（多图组合主屏）
   - 报表页（单一深度分析）
   - 数据卡片（嵌入式 KPI / mini chart）
   - 嵌入式图表（在表单 / 详情页中辅助说明）
   - 混合（含以上多种）
2. **数据形态**（如不清楚，让用户描述前 3 个核心数据）：
   - 时间维度？有 / 无
   - 类别维度？数量？
   - 数值序列？数量？
   - 是否有目标值 / 基准线？
3. **核心读者**：管理层快速读数 / 运营深度分析 / 普通用户感知 / 多角色
4. **响应式范围**：仅 Desktop / 仅 Mobile / Desktop + Mobile / 多端
5. **图表数量预估**：3-5 / 6-10 / 10+

> 超过 10 个图表的 Dashboard 强烈建议分两屏或分两次跑 Chart，单次 Skill 输出过多规格不利于设计师消化。

### Step 2 — 每图"意图 → 约束 → 选型"两层决策

对每个图表区，按以下两层判断：

#### 第一层：意图分类（用户想表达什么）

| 意图 | 关键问题 | 典型场景 |
| --- | --- | --- |
| **comparison** 对比 | "谁多谁少 / 谁好谁差" | 各区域销售对比、产品功能矩阵 |
| **trend** 趋势 | "随时间怎么变" | 月度增长、日活曲线 |
| **part-of-whole** 占比 | "构成 100% 的各部分" | 流量来源、收入构成 |
| **distribution** 分布 | "数据散布形态" | 响应时间分布、用户年龄分布 |
| **relationship** 关系 | "两个变量是否相关" | 价格 vs 销量、广告投入 vs 转化 |
| **flow** 流向 | "从 A 到 B 怎么流" | 转化漏斗、用户路径桑基图 |
| **hierarchy** 层级 | "嵌套的占比 / 结构" | 产品类目销售、组织架构 |
| **single-value** 单值 | "一个核心数" | DAU 数、达成率、健康度 |

**先定意图，不要先想图表类型。** 同一份数据，意图不同选图就不同：
- 销售数据"想看哪个区域强" → comparison → bar
- 销售数据"想看月度涨没涨" → trend → line
- 销售数据"想看各区域占比" → part-of-whole → treemap（区域多）/ pie（区域少）

#### 第二层：数据约束（细化选型）

| 约束因子 | 影响 |
| --- | --- |
| **类别数量** | ≤ 5 用 pie，6-10 用 bar，10+ 用 treemap / 排序后 top N |
| **时间粒度** | 连续型 → line；离散周期型 → column |
| **维度数** | 单维 → bar/line；双维 → grouped bar / dual-axes（量纲不同）；多维 → heatmap / radar（≤ 6 维） |
| **目标值 / 基准线** | 有 → 加 reference line / bullet chart |
| **正负值并存** | 用 diverging palette + zero baseline 居中 |
| **数据稀疏度** | 稀疏 → scatter / dot；密集 → heatmap |
| **量级悬殊** | 考虑 log 轴（明确标注）或拆图，**不要用双 Y 轴硬凑** |

#### 选型决策表（高频场景速查）

| 场景 | 首选 | 备选 | 不要 |
| --- | --- | --- | --- |
| 多类别对比（≤ 10） | bar（横向，类别名长）/ column（纵向，类别名短） | dot plot | 3D 柱图、雷达图 |
| 多类别对比（> 10） | bar 取 top N + "其他" | treemap | pie |
| 单系列时间趋势 | line | area（强调累计量） | 柱图（除非离散周期如月度） |
| 多系列时间趋势 | 多 line（≤ 4 条） | small multiples | 堆叠柱图（除非求和有意义） |
| 占比（≤ 5 类） | donut（中间放总数） | pie | bar |
| 占比（> 5 类） | treemap / 排序 bar + 百分比标签 | stacked bar（单条） | pie |
| 两量纲对比 | dual-axes（必须双方都是同时间轴） | 拆两图 | 直接共用 Y 轴 |
| 相关性 | scatter + 趋势线 | bubble（加第三维） | 双 Y 轴 line |
| 分布形态 | histogram | box plot（含统计量） | line（误导为趋势） |
| 漏斗转化 | funnel | bar（横向递减） | pie |
| 流向 | sankey | chord diagram | 散点 |
| 单核心数 | kpi-card（数值 + 对比 + sparkline） | gauge（仅限达成率类） | pie（用饼图表达 80% 是噩梦） |

#### 选型理由必填

每图必须写一句 `rationale`，**不能只填 chart_type**。范例：

- ✅ `rationale: "区域销售对比，类别 8 个超出 pie 上限，纵向 bar 适配中文长类别名"`
- ❌ `rationale: "用了柱图"`

### Step 3 — 每图视觉规格 + 状态 + 响应式

对每个选定的图表，逐项填写 `visual_spec / interaction / states / responsive / accessibility / sparkdesign_contract`。

#### 视觉规格（visual_spec）

- **width / height token**：用 SparkDesign 的 size token（如 `size.chart.lg`），**不要硬编码 px**；未知就标 `gap_to_fill: "SparkDesign 待补 chart.size token"`
- **palette**：从下列五选一，**不能自创**：
  - `categorical`：分类（无序），用 SparkDesign 分类色板 tokens
  - `sequential`：单一色相浅 → 深，表达有序/数量级
  - `diverging`：双色相，中点对照（如盈亏）
  - `single-hue`：品牌色单系列（趋势 / KPI 推荐）
  - `brand-accent`：品牌强调色 + 中性灰背景对比
- **palette_tokens**：列出实际用的 token 名（如 `["color.chart.cat.1", "color.chart.cat.2"]`），不写 `#3B82F6`
- **y_axis_start**：bar/column 必须 `zero`；line/area 可 `auto`（但要在 `rationale` 解释）
- **direct_label**：≤ 5 数据点首选直接标注，省去 legend
- **legend_position**：超过 5 系列才考虑 legend，否则 `none`
- **annotation**：关键峰值 / 谷值 / 目标线 / 异常点必须文字标注

#### 交互（interaction）

至少声明三类：

- `hover`：tooltip 内容（建议含"数值 + 变化率 + 同环比"）
- `click`：跳转 / 钻取行为（或写"不可点击"）
- `filter`：是否参与全屏 filter 联动

#### 状态（states）—— 图表层细化，与 /edge 联动

每图必须给出五个状态描述（即使写"沿用屏级 empty 状态"也比留空好）：

- `empty`：无数据时如何呈现（推荐：保留坐标轴 + 中部 illustration + 引导文案）
- `loading`：< 1s 不必特殊处理；1-3s 用 skeleton（保留坐标轴形态）；> 3s 加 progress
- `error`：取数失败时如何呈现 + 重试 CTA
- `single_point`：只有 1 个数据点时怎么画（line 退化为 dot；bar 不强求条数）
- `overflow`：数据超过设计上限时（top N + "查看全部"）

#### 响应式（responsive）—— Mobile 不是缩放，是改写

`mobile_degradation` 必须从以下五选一：

| 策略 | 适用场景 | 范例 |
| --- | --- | --- |
| `simplify` | 数据点 < 10 | 减少 tick / 隐藏次要 series / 移除装饰 |
| `swap-chart-type` | 类别多或精度要求低 | grouped bar → stacked bar；pie → 横向 bar |
| `table` | 精度要求高，对比维度多 | 复杂 dashboard → 表格 + 筛选 |
| `sparkline` | KPI 卡场景 | 趋势线压缩为 mini sparkline |
| `hide` | 该图在 Mobile 价值低 | 整图隐藏，引导到 Desktop 看完整版 |

**红线**：≥ 5 系列的多 line 图、含 > 8 数据点的 pie 图、双 Y 轴图 —— 在 Mobile 上**不允许**简单等比缩放，必须 `swap-chart-type` 或 `table`。

#### 可访问性（accessibility）—— 接 /access 的图表专项

四项硬指标：

- `colorblind_safe: true`：调色板必须通过红绿色盲模拟（推荐用 Okabe-Ito 8 色或 ColorBrewer）
- `contrast_ratio_pass: true`：数据元素与背景对比 ≥ 3:1（WCAG AA 非文本元素）
- `aria_label`：图表必须有简短 aria-label 描述（如"2025 各区域销售柱状图，华东最高 1200 万"）
- `keyboard_navigable: true`：交互图表必须可 Tab 进入、方向键切换数据点

**仅靠颜色编码区分系列 = 不达标**，必须叠加 pattern / 形状 / 直接标注其中一项。

#### SparkDesign 契约（sparkdesign_contract）

**这是 SkillsHub 区别于社区 skill 的核心。** 每图必须声明：

- `component`：用 SparkDesign 的哪个组件（如 `<SparkChart variant="bar">`），没有就标 `"待补"`
- `tokens_used`：调用了哪些 design token（颜色 / 间距 / 字号）
- `gap_to_fill`：本图暴露的"SparkDesign 暂缺"项（如"缺 funnel 组件 / 缺 chart.size 系列 token"）

跑完所有图表后，`coverage.sparkdesign_gaps[]` 汇总所有缺口 —— **这就是 AG-UI Design Spec 体系下 SparkDesign 仓库的图表组件需求列表**，反推设计系统该建什么。

### Step 3.5 — 可选：生成 AntV mock 预览（v1.1）

**触发条件**（满足任一即询问用户是否生成）：

- 用户在调用时显式说"出预览图 / 生成 mock / 让我看看 / preview"
- 输出表面是 `surface=dashboard` 且图表数 ≤ 10（一次性全生成预览成本可控）
- 用户在 Step 1 提到"评审 / 提案 / 给 PM 看 / pitch"

**不触发**：用户明确说"只要规格不要图"、surface=embedded-chart 嵌入式（不需要独立预览）、图表数 > 10（建议挑核心图单独生成）。

执行逻辑：

1. 用 `AskUserQuestion` 二选一确认范围：「全部 N 图生成预览」/「只生成 [候选清单] 这几张」
2. 对选中的每图，按 **附录 A：chart_type → AntV 映射表** 转换 `chart.charts[]` 的字段为 AntV 请求体
3. 用 `Bash` 工具调用 `POST https://antv-studio.alipay.com/api/gpt-vis`（curl）
4. 解析 `resultObj` 为图片 URL，写回该图的 `preview` 字段：

   ```json
   "preview": {
     "generated": true,
     "provider": "antv-gpt-vis",
     "antv_type": "column",
     "request_body": { ... },
     "image_url": "https://...",
     "generated_at": "<ISO8601>"
   }
   ```

5. **失败兜底**：API 超时 / 返回 success=false / 映射表标记 `不支持` → 写 `preview.generated=false` + `fallback_reason`（如 "AntV 无 heatmap 类型，建议 v1.2 接 ECharts 兜底"），**不阻断主流程**
6. 预览图 URL 在 4.1 Markdown 报告每图条目末尾以 `![chart-N 预览](URL)` 形式插入

**红线**：

- 预览图是**辅助评审**，**不是设计交付物本身**。规格文档 + design token 仍是工程师消费的唯一权威源；预览图随时可能失效（外链）
- 不要因为 AntV 渲染好看就反向修改 chart_type / palette—— v1.1 是规格 → 预览单向流，预览结果不回写规格

### Step 3.6 — 工程实现库智能推荐（v1.2，必做）

**目的**：避免 AI 在不了解项目栈的情况下盲推某个图表库（如在 React+shadcn 项目里推 AntV、在 antd 项目里推 Recharts）。本步**强制执行**——每个 Chart 输出必须含 implementation_recommendation 段，给出**至少 2 个候选 + 1 个首选 + 切换触发**。

#### 3.6.1 技术栈检测（按以下信号源依次扫描）

| 优先级 | 信号源 | 提取字段 |
| --- | --- | --- |
| **1** | 项目根 `package.json`（用 Read / Glob 扫描）| `dependencies` 里已安装的图表库（recharts / echarts / @antv/* / chart.js / d3 / visx / plotly / victory）+ framework（react / vue / svelte / react-native）+ UI 库（shadcn 不在 deps 里，扫 `components/ui/` 目录 / @radix-ui-* / antd / @mui/* / @chakra-ui/* / element-plus / naive-ui） |
| **2** | `flow-web.json` / `flow-mobile.json` 的 `framework` / `ui_library` 字段 | 同上备援 |
| **3** | `brief.constraints` | "体积限制 < Xkb" / "公司技术栈是 X" / "禁止用 X" |
| **4** | 询问用户（仅当 1-3 全部失败） | 用 AskUserQuestion 二选一关键问题（框架 / UI 库） |
| **加分项** | SparkDesign 偏好（如本仓库 README / CLAUDE.md 明确"AntV-first / AG-UI 战略对齐"）| 写入 `sparkdesign_alignment = official` 给 AntV 系候选加分 |

数据规模判断（影响候选打分）：

- `small`：单次渲染 < 100 数据点（默认）
- `medium`：100-1000
- `large`：1K-10K（卡顿风险，倾向 canvas 渲染）
- `huge`：> 10K（必须 ECharts / WebGL 类）

#### 3.6.2 候选库矩阵（按检测到的栈映射）

| 检测到的栈 | 首选 | 备选 | 不建议 | 关键理由 |
| --- | --- | --- | --- | --- |
| **React + shadcn / Radix** | Recharts | Visx · AntV G2 | @ant-design/charts（antd 强耦合）| 同源 React、声明式 JSX、与 Tailwind 适配好、~150KB |
| **React + antd** | @ant-design/charts (G2Plot) | ECharts · AntV G2 | Recharts | antd 同源 token 互通、视觉一致 |
| **React + MUI / Chakra** | Recharts | Nivo · Visx | 任一 antd 强耦合库 | 中性、与多种 UI 库共存 |
| **React + SparkDesign** | **看 SparkDesign 官方推荐**（sparkdesign_alignment=official）；无明确推荐时 Recharts | AntV G2（若 AG-UI 战略对齐）| — | SparkDesign 契约优先；战略层倾向 AntV 系 |
| **Vue 3** | ECharts (vue-echarts) | @antv/g2 · Chart.js | Recharts（React only） | Vue 生态主流、社区支持厚 |
| **Svelte** | Layer Cake | ECharts · Chart.js | Recharts | Svelte 原生 |
| **React Native** | Victory Native | react-native-svg-charts · react-native-chart-kit | 任何 Web-only 库 | RN 渲染兼容 |
| **Vanilla / 无框架** | ECharts | Chart.js · AntV G2 | Recharts | 与框架解耦、体积可裁剪 |
| **大数据量 (data_scale=large/huge)** | ECharts (canvas) | Plotly · regl-based | Recharts (SVG 卡顿) | 渲染性能 |
| **关系图 / 桑基 / 大图分析** | AntV G6 | D3 · Cytoscape | Recharts | G6 专攻图分析 |
| **3D / WebGL** | Three.js（自渲染）| Plotly 3D · deck.gl | 标准 chart 库 | 不擅长 3D |

#### 3.6.3 已安装库强制复用规则（红线）

- 如 `existing_chart_libs` 非空 → **首选必须从已安装列表里选**，理由写"复用既有依赖避免双重打包"，候选可列其他但**必须把已安装库标 score 加 +30**
- 例：项目已装 ECharts → 即使是 React+shadcn 也优先推 ECharts（除非已装库与当前需求严重不匹配，需在 rationale 说明并标 `switch_triggers`）
- 严禁推荐**第三个**图表库新依赖（项目已装 1 个就只用那个；已装 2 个也尽量复用）

#### 3.6.4 候选打分逻辑（每个候选 0-100）

```
score = 框架适配度(0-40) + UI 库适配度(0-20) + 已安装加分(0-30) + SparkDesign 战略加分(0-10) - 体积惩罚 - 维护风险惩罚
```

- 框架不匹配 → 直接淘汰（如 React 项目不列 vue-echarts）
- 已安装 → +30（最强信号）
- SparkDesign 战略对齐（sparkdesign_alignment=official）→ +10
- 体积 > 500KB gzip → -5 / 1MB+ → -15
- 库已停止维护 → -20

#### 3.6.5 输出 implementation_recommendation

填充 schema 中的 `implementation_recommendation` 块：

- `detected_stack.detection_sources`：列出信号源（如 `["package.json", "flow-web.framework"]`），便于设计师追溯
- `candidates`：至少 2 个，按 score 降序；每个含 pros / cons / bundle_kb_gzip
- `recommended.library`：score 最高且无红线冲突的
- `recommended.rationale`：一句话说明（如"项目已装 recharts，复用避免新增 150KB 依赖"）
- `recommended.install_command`：若已安装写 `已安装，无需新增`；否则给出 `pnpm add recharts` 等
- `recommended.bundle_impact`：估算 gzip 增量（已安装 = 0）
- `recommended.sparkdesign_alignment`：official / compatible / neutral / conflict / na
- `switch_triggers`：明确"什么情况下应该换库"，例：`["数据量超过 10K 点 → 换 ECharts", "新增关系图需求 → 加 AntV G6"]`
- `confidence`：信号源齐全 high / 缺一两项 medium / 全靠询问用户 low

#### 3.6.6 与 Step 3.5 mock 预览的关系

注意区分：

- **Step 3.5 的 AntV**：用于评审 mock，**永远是 AntV gpt-vis**（与本步推荐的工程库无关）
- **Step 3.6 的推荐**：工程实现库，按技术栈来，可能是 Recharts / ECharts / @ant-design/charts / 任意

两者**互不冲突**：设计师可以用 AntV 出预览图给老板看，工程实现用 Recharts 写代码。规格条目里 `preview.image_url`（评审用）和 `implementation_recommendation.recommended.library`（工程用）是两套独立信息。

### Step 4 — 输出

#### 4.1 Markdown 报告（输出到对话 + 保存到 `spark-output/chart/[project-slug].md`）

```markdown
# Chart Spec — [项目名]

- **生成时间**：[ISO8601]
- **表面类型**：[surface]
- **图表总数**：N（comparison: n / trend: n / part-of-whole: n / ...）
- **Mobile 降级**：N 图（simplify n / swap n / table n / sparkline n / hide n）
- **可访问性通过率**：N/M
- **SparkDesign 缺口**：[列表]
- **数据源**：brief / sitemap / flow-web / flow-mobile

## Dashboard 布局总图

- 阅读路径：[F-shape / Z-shape / top-down]
- 密度：[sparse / balanced / dense]
- 网格：[如 12-col, 4 行]

### 分区结构

| 分区 | 用途 | 含图表 |
| --- | --- | --- |
| 顶部 KPI 行 | 一眼读数 | chart-1, chart-2, chart-3 |
| 中部趋势区 | 时间趋势 | chart-4, chart-5 |
| ... | ... | ... |

## 调色板策略

- **categorical**：[token 列表]
- **sequential**：[token set]
- **diverging**：[token set]
- **色盲检查**：pass / fail

## 图表清单（按 chart_id 组织）

### chart-1 · [图表标题]

- **所在屏**：[screen]
- **意图**：[comparison / trend / ...]
- **图表类型**：[bar / line / ...]
- **选型理由**：[一句话，必填]
- **数据形态**：维度 N / 系列 N / 数据点 N / 时间粒度 [...] / 有目标值 [Y/N]
- **视觉规格**：
  - 尺寸：[width_token × height_token]
  - 调色板：[palette]（tokens: [...]）
  - Y 轴：[zero / auto] · 直接标注 [Y/N] · 图例 [position]
  - 标注：[annotation 列表]
- **交互**：hover [...] · click [...] · filter [...]
- **状态**：empty / loading / error / single_point / overflow
- **响应式**：
  - Desktop：[spec]
  - Mobile：[degradation 策略] · [spec]
- **可访问性**：colorblind [✓/✗] · contrast [✓/✗] · aria [...] · keyboard [✓/✗]
- **SparkDesign 契约**：组件 [...] · tokens [...] · gap [...]

### chart-2 · ...

（每图完整展开）

## 工程实现库推荐（v1.2）

- **检测到的栈**：framework=[...] · ui_library=[...] · 已装图表库=[...] · data_scale=[...] · 信号源=[...]
- **置信度**：[high / medium / low]
- **候选**（按 score 降序）：

  | 库 | score | 优点 | 缺点 | gzip |
  | --- | --- | --- | --- | --- |
  | [推荐项] | [n] | [...] | [...] | [n]KB |
  | [备选] | [n] | [...] | [...] | [n]KB |

- **首选**：[library] —— [rationale]
- **安装**：`[install_command]` · 体积增量：[bundle_impact]
- **SparkDesign 对齐**：[official / compatible / neutral / conflict / na]
- **切换触发**（什么情况下换库）：
  - [trigger 1]
  - [trigger 2]

## SparkDesign 反向输入清单

跑完本次 Chart 暴露的 SparkDesign 缺口（按出现频次排序）：

1. [gap 描述] · 影响图表数：N · 建议补法
2. ...
```

#### 4.2 双通道 Context 输出

按 [chain-protocol.md](../../chain-protocol.md) §2.1 v1.1 智能适配规则：

**Step 1 — 写盘到 `spark-output/context/chart.json`**（必做，主持久化通道；目录不存在先创建）。写入完整 JSON（schema 见 frontmatter）。

**Step 2 — chat 输出紧凑 marker**（必做，⛔ **不要在 chat 内重复输出 Step 1 的完整 JSON**）：

```
<!-- spark-context:chart ref="spark-output/context/chart.json" -->
Chart 已保存：project=[project_name]，surface=[surface]，[N] 图（trend n / comparison n / part n / ...），mobile 降级 [n]，a11y 通过 [n/N]，SparkDesign 缺口 [k] 项
<!-- /spark-context:chart -->
```

**降级 fallback**：若 Step 1 写盘失败（chat-only 平台），输出完整 JSON marker（无 ref 属性，marker 之间放裸 JSON）作为唯一持久化通道。

### Handoff 提示（必输出）

> **协议**：按 [`_shared/next-skill.md`](../../_shared/next-skill.md) 三层结构模板输出；前 5 候选由 `_shared/skill-graph.json` 的依赖图算法实时算（done ⊆ ready，按 next_hint.preferred → alternatives → 同阶段 → anchor → fan-out 排序），优先建议从 `_shared/skill-graph.json#skills[id="chart"].next_hint` 读取。

**首行模板**：`✅ 数据可视化 已完成，图表规格 + AntV mock + 工程库推荐已沉淀。`

**本 Skill 的 `next_hint`**（来自 skill-graph.json，**不可在此 SKILL.md 内硬编码覆盖**）：

- **preferred**：`/flow-web`
- **优先理由**：图表规格已就绪，回主流程把图表组件嵌回页面 Flow。
- **alternatives**：`/edge` (图表的空 / 加载 / 错态需要单独覆盖) · `/check` (页面 + 图表完整后整体自检)
- **emoji**：📊

**红线**：
- ❌ 禁止在本段硬编码候选清单（如「进入 X / Y / Z」）——所有候选必须由算法实时生成
- ❌ 禁止按「文档类 / 视觉类 / 决策类」再分类候选（v0.5.5 起，分类已折叠进 next_hint.alternatives）
- ❌ 禁止与「更新链路面板」段合并——两段必须各自独立成段，中间空一行
- ❌ 禁止漏第 2 行候选清单——即使候选只有 1 个、或为空（终端节点）也要写出来

---

## 实操注意事项

### 图表过多时的策略

单个 Dashboard 超过 10 张图，几乎可以肯定**违反了 Data-ink ratio 与认知负荷**。处理方式：

- **拆分 Dashboard**：按角色 / 任务拆成多屏（管理者总览 vs 运营详情）
- **chart 合并**：多张 KPI 单值合并为 KPI Row（横向卡片组）
- **降级为表格**：高密度数据本质就是表格，不要硬画图

### 双 Y 轴的红线

双 Y 轴 **只在以下两种情况合理**：

1. 两个序列时间轴完全一致，且业务上需要直接对比相关性（如成本 vs 收入）
2. 一个柱图 + 一个折线图，量纲明显不同且各自有独立含义

其他场景一律拆两图。强行用双 Y 轴会让用户错读相关性，是数据可视化最常见的"骗自己"。

### 与 chart-visualization 工具的关系

`.agents/skills/chart-visualization` 是**纯执行规格**（AntV API 调用 + data schema），v1 不在本 Skill 调用范围。设计师如果只想"快速 mock 一张图给 PM 看"，可以单独用 chart-visualization；本 Skill 产出的是**可交付的设计规格文档**，给工程师 / Cursor / Claude Code 消费，不是临时画图工具。

v2 计划：把 chart-visualization 的 API 规格作为 Chart Skill 的可选附录段，让 `chart.charts[]` 可一键导出 AntV 请求体做预览。

### 与 PM 套件 /产品指标复盘 的边界

| 场景 | 用谁 |
| --- | --- |
| "我们 Q3 应该关注哪些指标？怎么拆 OKR？" | PM /产品指标复盘 |
| "Dashboard 上要放哪几张图？每张图什么意图？" | **Chart**（本 Skill） |
| "上线后怎么追踪设计是否成功？" | /设计度量（metric） |
| "前端把柱图实现错了" | /设计验收（qa） |

Chart 不定义"看什么数"，只解决"怎么把数画对"。PM 给出的 KPI 列表是 Chart 的输入，Chart 决定每个 KPI 在 Dashboard 上的视觉承载形式。

---

## 已知限制（v1）

- **预览仅作评审辅助**：v1.1 的 AntV 预览是 mock 工具，**不是工程实现的规格**；工程师消费的仍是 chart.json + design token，不要把预览 URL 当成"最终视觉对账图"
- **AntV 不覆盖全部 chart_type**：heatmap / bubble / kpi-card / gauge / sparkline 五类在 v1.1 内无 AntV 对应，自动走 fallback（详见附录 A）；可在 v1.2 接 ECharts 或 SparkDesign 自有渲染补齐
- **工程图表库推荐≠强制**：v1.2 起 Skill 会根据技术栈给出 implementation_recommendation（首选 + 候选 + 切换触发），但**前端团队仍有最终决定权**；规格文档（每图 visual_spec / palette_tokens / a11y）与最终选用的库无关，换库不需重做规格
- **栈检测依赖 package.json 可读性**：仓库无 package.json / 权限不足读不到时，confidence 降为 low，需用户在调用时显式说明栈（如"项目是 React + shadcn"）；否则可能误推
- **不做"美化建议"**：审美层面（如"这个 dashboard 看起来高级吗"）需配合 /board 视觉情绪板
- **SparkDesign 图表组件库可能未全**：本 Skill 会显式输出 `gap_to_fill`，但暴露的缺口需 SparkDesign 仓库另行补建
- **极端数据集（10M+ 数据点）的渲染策略不在本范围**：本 Skill 解决"选什么图、怎么画"，不解决"如何性能优化渲染百万点"
- **地理可视化 (map / choropleth) 未覆盖**：v1 不包含地图类，需在 v1.1 增量
- **动态时序播放 / 动画类**未覆盖：建议配合 /motion

---

## 与兄弟 Skill 的边界（v0.4.0 范本对齐）

| 场景 | 用谁 | 不用谁 |
| --- | --- | --- |
| 选图表类型 + 视觉规格 + Dashboard 布局 | **Chart** | Flow Web/Mobile（页面 IA 层不到图表细节）、chart-visualization（无设计判断） |
| Dashboard 所在页面的 IA 与导航 | Flow Web / Flow Mobile | Chart（不做页面级 IA） |
| 图表层 empty/loading/error 文案 | Chart（图表层）+ Edge（屏层） | 任一单独 |
| 临时画一张图给 PM 看 | chart-visualization（.agents/skills） | Chart（重型规格文档，不适合临时） |
| 上线后跟踪指标体系 | Metric | Chart（Chart 解决展示，Metric 解决度量） |
| 配色 / token 校验 | Chart（设计阶段）+ Check（走查）+ QA（实现） | 任一单独 |
| 图表无障碍校验 | Chart（标 a11y 项）+ Access（专项审计） | Chart 单独可初判，AA/AAA 完整审计要走 Access |

**Chart 不可替代性**：意图分类 → 数据约束 → 图表选型 → 调色板规则 → Mobile 降级 → SparkDesign 契约的六维链路，是设计师**做 Dashboard / 报表前**的唯一系统化规格工具——其他 Skill 都假设"图表已经画好了"在做下游工作。

## 质量标准

1. **选型理由必填且站得住**：每图 `rationale` ≥ 一句完整话，能回答"为什么不是其他相邻图表类型"
2. **调色板纯一**：单个 Dashboard 内 categorical / sequential / diverging 不能混用；交叉使用必须显式声明分区
3. **Y 轴零起点纪律**：所有 bar / column 图 `y_axis_start = zero`；其他图若非 zero 必须在 rationale 内解释
4. **Mobile 降级率 ≥ 80%**：含 ≥ 5 数据点的图表，必须有 mobile_degradation 策略（不能 default 缩放）
5. **可访问性四项全过**：colorblind_safe / contrast_ratio_pass / aria_label / keyboard_navigable 任一项 fail 视为该图未达交付标准
6. **SparkDesign 契约显式**：每图必填 component / tokens_used / gap_to_fill，不能空着糊
7. **意图 → 类型映射有依据**：每图的 intent 与 chart_type 组合必须在 Step 2 选型决策表内或在 rationale 明确解释为何破例
8. **状态五件套不省**：empty / loading / error / single_point / overflow 一个都不能省（即使写"沿用屏级"也比空着好）

## 红线规则

1. **禁止 3D 图表**：3D bar / 3D pie 在任何场景都是反模式，扭曲数据视觉
2. **禁止双 Y 轴乱配对**：仅允许同时间轴 + 直接相关性场景，否则一律拆两图
3. **禁止饼图类别 > 6**：> 6 自动改 treemap / bar，不接受"凑合用 pie"
4. **禁止仅用颜色编码区分系列**：必须叠加 pattern / 形状 / 直接标注其中一项（直接对接 Access 红线）
5. **禁止硬编码颜色十六进制**：palette_tokens 必须用 SparkDesign token，找不到对应 token 也要标 `gap_to_fill` 而非写死 `#3B82F6`
6. **禁止 Mobile 等比缩放复杂图**：≥ 5 系列多 line / > 8 类 pie / 双 Y 轴 在 Mobile 必须改写
7. **禁止把 Chart 当画图工具用**：本 Skill 产出规格文档；如果用户只想画一张临时图，引导去 chart-visualization 或直接让 AI 画，不要走 Chart 全流程
8. **禁止跳过选型理由**：rationale 留空或写"用了 X 图"视为未完成
9. **禁止忽略 package.json 已装库**：检测到 `existing_chart_libs` 非空时，首选必须从已装列表选；推不同库必须在 rationale 内说明已装库为何不合适（v1.2）
10. **禁止跨框架推荐**：React 项目不推 vue-echarts，Vue 不推 Recharts，RN 不推 Web-only 库（v1.2）
11. **禁止"无视栈"盲推**：implementation_recommendation 是必填段，confidence=low 时必须显式标 "建议用户确认栈后重跑"，不能糊一个推荐了事（v1.2）

---

## 附录 A：AntV GPT-Vis API 映射（v1.1 mock 预览）

> 本附录为 Step 3.5 提供"规格条目 → AntV 请求体"的转换规则。**只在用户选择生成预览时才用到**；不生成预览的图表无需消费本附录。

### A.1 接口

```
POST https://antv-studio.alipay.com/api/gpt-vis
Content-Type: application/json

请求体（公共）：
{
  "type": "<chart_type>",
  "source": "product-design-chart",
  "data": [...],
  "title": "<可选>",
  "theme": "default | academy | dark",
  "width": <number, 默认 600>,
  "height": <number, 默认 400>,
  "axisXTitle": "<可选>",
  "axisYTitle": "<可选>"
}

返回：
{ "success": true, "resultObj": "https://..." }
```

> ⚠️ `source` 字段在 chart-visualization 工具中是 `chart-visualization-skills`，本 Skill 使用 `product-design-chart` 作为来源标识，便于 SparkDesign 团队追溯调用来源。

### A.2 chart_type → AntV type 映射表

| 本 Skill chart_type | AntV type | 数据结构（data 字段） | 特殊参数 | fallback 策略 |
| --- | --- | --- | --- | --- |
| `bar` | `bar` | `[{category, value, group?}]` | `stack` / `group` | — |
| `column` | `column` | `[{category, value, group?}]` | `group: true` 默认 | — |
| `line` | `line` | `[{time, value, group?}]` | `stack: false` | — |
| `area` | `area` | `[{time, value, group?}]` | `stack: true` 默认 | — |
| `dual-axes` | `dual-axes` | `categories: string[]`<br>`series: [{type, data, axisYTitle}]` | series.type ∈ {column, line} | — |
| `pie` | `pie` | `[{category, value}]` | — | — |
| `donut` | `pie` | `[{category, value}]` | `innerRadius: 0.5` | — |
| `treemap` | `treemap` | `[{name, value, children?}]` ≤ 3 层 | — | — |
| `scatter` | `scatter` | `[{x, y, group?}]` | — | — |
| `bubble` | `scatter` | `[{x, y, group?}]` | 第三维 size 暂不支持 | `fallback_reason: "AntV scatter 不支持 size 维度，预览仅显示二维"` |
| `heatmap` | — | — | — | `generated: false`, `fallback_reason: "AntV gpt-vis 无 heatmap，建议接 ECharts 兜底"` |
| `histogram` | `histogram` | `number[]` | `binNumber` | — |
| `boxplot` | `boxplot` | `[{category, value, group?}]` | — | — |
| `funnel` | `funnel` | `[{category, value}]` | — | — |
| `radar` | `radar` | `[{name, value, group?}]` | — | — |
| `sankey` | `sankey` | `[{source, target, value}]` | `nodeAlign` | — |
| `waterfall` | `waterfall` | `[{category, value?, isTotal?}]` | — | — |
| `kpi-card` | — | — | — | `generated: false`, `fallback_reason: "KPI 卡建议直接用 SparkDesign 组件，无需 mock 预览"` |
| `sparkline` | `line` | `[{time, value}]` | `width: 200, height: 60`<br>关闭坐标轴 | 降级为 mini line |
| `gauge` | `liquid` | `percent: number (0-1)` | `shape: "circle"` | 近似替代 |
| `table` | `spreadsheet` | `Record<string, string\|number>[]` | `rows / columns / values` | — |

**映射核心原则**：

- 能 1:1 映射就直接映射（90% 场景）
- 视觉等价的降级允许（如 sparkline → 简化 line）
- 完全不支持的，写 `fallback_reason` 而非硬塞，让评审者知道"为什么这张没图"

### A.3 调用模板（curl）

```bash
curl -s -X POST https://antv-studio.alipay.com/api/gpt-vis \
  -H "Content-Type: application/json" \
  -d '{
    "type": "column",
    "source": "product-design-chart",
    "data": [
      {"category": "华东", "value": 1200},
      {"category": "华北", "value": 980},
      {"category": "华南", "value": 1450}
    ],
    "title": "2025 各区域销售对比",
    "axisXTitle": "区域",
    "axisYTitle": "销售额（万）",
    "theme": "default",
    "width": 800,
    "height": 400
  }'
```

期望响应：

```json
{"success": true, "resultObj": "https://antv-studio.alipay.com/results/xxx.png"}
```

异常处理：

- 网络超时 / 5xx → 等 2s 重试一次；仍失败写 `fallback_reason: "API 不可达"`
- `success: false` → 写 `fallback_reason: <错误 message>`
- 响应 URL 不可访问（HEAD 校验失败）→ 写 `fallback_reason: "返回 URL 不可访问"`

### A.4 字段映射注意事项

- **AntV theme 与 SparkDesign 主题不一致**：v1.1 预览统一用 `theme: "default"`，预览只追求"形对"，颜色对账以 chart.json `palette_tokens` 为权威源
- **AntV 不接受 design token**：调用时 palette / 字号 / 间距均用 AntV 默认；如需"品牌色预览"可在 request_body 加 `colors: ["#...", ...]`（但只在评审需要时用，规格本身仍用 token）
- **title 来源**：取 chart.charts[].chart_id 对应的图表标题（Markdown 报告里的 `### chart-N · [标题]`），非 chart_id 本身
- **轴标题**：dual-axes / scatter / line / bar / column 必填 axisXTitle / axisYTitle，否则预览图无法理解

### A.5 v1.2 计划（待办）

- heatmap / kpi-card / gauge：接 ECharts 或 SparkDesign 自渲染补齐
- bubble：等 AntV gpt-vis 支持 size 维度
- 预览图本地缓存：避免反复调用同一份数据
- SparkDesign 主题色注入 AntV：实现真正的"品牌色预览"
