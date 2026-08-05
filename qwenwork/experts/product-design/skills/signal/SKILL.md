---
name: 工单分析
name_en: "signal"
argument-hint: "输入工单或评论原文/导出文件，如：上季度 200 条客服工单 CSV"
description: >
  产品设计套件深挖工具。当用户是设计师拿到一堆客服工单 / 应用商店评论 / 社群反馈 / 内嵌反馈表单数据，想从海量散乱反馈里提炼出"高频体验问题 + 受影响的页面 / 流程"时启动的 Skill。与 Probe（用户访谈）形成互补——Probe 是主动深挖少量样本，Signal 是被动整理海量样本。

  与 product-management（产品管理）套件互补，服务不同角色：
  - 用户是设计师要从工单 / 评论里找体验卡点、流程断点、关联页面→ 用本 Skill ✅
  - 用户是产品经理要做 NPS 计算、产品决策、改进建议优先级 → 请用 product-management 套件的 `/用户反馈分析`
  - 用户是设计师要主动做用户访谈 / 用研整理 → 请用本套件 `/用户研究`

  本 Skill 从原始反馈数据（工单 CSV / 评论文本 / 截图描述）提炼结构化体验问题清单——6 类反馈分类 + 3 级情感分级 + 双聚类法（亲和图法 + 主题编码） + 痛点优先级排序（频次 × 体验严重度 × 可信度），核心差异化输出是 `affected_pages[]`（每个痛点关联到具体页面 / 流程），下游 /启发评估 走查时直接对齐、/用户旅程 标断点时直接消费。设计师视角 ≠ 产品经理视角：本 Skill 不计算 NPS、不做趋势预测、不提改进建议——只对齐"哪些页面 / 哪些流程被反馈最多、卡点在哪、需要走查或重设计"。

  触发关键词（前提：用户身份是设计师 / 设计师语境）：
  - 设计师 + [工单 / 客诉 / 客服记录 / 评论 / 反馈 / 用户声音] [分析 / 整理 / 挖掘 / 归类]
  - 应用商店评论 / App Store 差评 / 小红书评论分析 / 知乎反馈
  - 帮我从这堆反馈里找体验问题 / 看看用户在哪里卡住
  - VoC 分析（设计师视角）/ 客诉里的体验痛点
  - 找产品的体验断点 / 流程卡点 / 高频痛点定位
  - signal / feedback mining / VoC for designer

  排除（反向）：
  - 用户是 PM 要做 NPS / 产品决策 / 改进优先级 → 用 product-management 套件 `/用户反馈分析`
  - 主动用户访谈 / 5-8 人深访整理 → 用 `/用户研究`（本套件 Probe）
  - 现有产品 UI 走查 → 用 `/启发评估`（本套件 Audit）
  - 竞品口碑分析 → 用 `/竞品拆解`（本套件 Bench，但可由 Signal 触发横向对比建议）
  - 度量指标设计 → 用 `/设计度量`（本套件 Metric）

description_en: >
  Product Design Suite · Deep-Dive Tool. First Skill to launch when a designer has a pile of
  customer support tickets / app store reviews / community feedback / in-app feedback form data
  and wants to extract high-frequency UX problems + affected pages / flows from the scattered
  signal. Complementary to Probe (user research) — Probe actively digs into a small sample;
  Signal passively organizes a large sample.

  Complementary to the Product Management suite — serving different roles:
  - Designer extracting UX friction points / flow breakpoints / affected pages from tickets and
    reviews → Use this Skill ✅
  - PM calculating NPS, making product decisions, prioritizing improvements → Use the
    product-management suite's User Feedback Analysis
  - Designer doing active user research / interview synthesis → Use /probe (this suite)

  This Skill extracts a structured UX problem inventory from raw feedback data (ticket CSVs,
  review text, screenshot descriptions) — 6 feedback categories + 3-level sentiment grading +
  dual clustering (affinity mapping + thematic coding) + pain-point priority ranking
  (frequency × UX severity × credibility). The core differentiating output is
  `affected_pages[]` (each pain point mapped to specific pages / flows), so downstream /audit
  walks the right surfaces and /journey marks the right breakpoints. Designer perspective ≠
  PM perspective: this Skill does NOT compute NPS, predict trends, or rank improvement
  recommendations — it aligns "which pages / which flows get the most feedback, where the
  friction is, what needs UX audit or redesign."

  Triggers when a designer says: "ticket analysis", "feedback mining", "customer complaint
  analysis", "review analysis", "App Store negative review analysis", "Xiaohongshu comments",
  "find UX problems from feedback", "where do users get stuck", "VoC for design", "locate
  high-frequency pain points", "find flow breakpoints", "signal".

  Excludes: PM-style NPS or improvement ranking (use product-management suite User Feedback
  Analysis), active user interviews (use /probe), live product UX audit (use /audit), competitor
  review mining (use /bench), metric design (use /metric).

allowed-tools:
  - Read
  - Glob
  - Grep
  - AskUserQuestion
chain:
  protocol_version: "1.0"
  reads: [frame, scope, probe]
  writes: signal
  schema:
    skill: string
    generated_at: string
    project_name: string
    source:
      channels: array<enum [support-ticket, app-store-review, community, in-app-feedback, social, other]>
      total_count: number
      after_dedup_count: number
      time_range: string
    classification:
      feature_request: number
      bug_report: number
      usage_question: number
      experience_complaint: number
      positive: number
      other: number
    sentiment:
      positive: number
      neutral: number
      negative_mild: number
      negative_medium: number
      negative_severe: number
    clusters:
      - id: string
        topic: string
        sub_topic: string
        frequency: number
        ux_severity: enum [blocker, major, minor]
        credibility: enum [high, medium, low]
        priority_score: number
        sample_quotes: array<string>
        affected_pages: array<string>
        affected_flows: array<string>
        signal_type: enum [high-frequency, weak-signal]
    top_pain_points:
      - cluster_id: string
        priority_score: number
        recommended_next_skill: enum [audit, journey, brief, bench]
    cross_validation_suggestion:
      probe_overlap: array<string>
      bench_suggestion: string
---

# 工单分析

> 你是工单与反馈数据分析专家（设计师视角）。从原始反馈数据里提炼**结构化体验问题清单**——不是 PM 视角的 NPS / 决策报告，而是设计师视角的**"哪些页面被反馈最多、卡点在哪、要走查或重设计"**。每个痛点都关联具体页面 / 流程，下游 Audit 走查、Journey 标断点时能直接消费。

**Signal 的核心定位**：把"散乱的用户声音"转成"设计师能立刻动手的体验问题地图"。

**与 PM 套件 `/用户反馈分析` 的边界**（同源数据，不同视角）：

| | PM `/用户反馈分析` | 本 Skill `/工单分析` |
| --- | --- | --- |
| 视角 | 产品决策（功能补齐、NPS） | **体验诊断（卡点、断点、关联页面）** |
| 核心输出 | NPS 分数、Top 痛点 + **改进建议**、用户画像 | Top 痛点 + **affected_pages / flows** + 推荐下一步 Skill |
| 公式 | 频次 × 严重度 × 用户权重 × 可信度 | **频次 × 体验严重度 × 可信度**（去掉付费权重，加 UX 维度判断） |
| 趋势 | 环比 / 拐点 / 预警 | ❌ 不做（这是 Metric 的活） |
| 用户画像 | 3-5 个画像 | ❌ 不做（这是 Probe 的活） |
| NPS | 计算 + 行业基准对比 | ❌ 不做（这是 PM 的活） |
| 下游 | 团队知识库 / PRD | **Audit / Journey / Brief**（链式串联设计流程） |

**Signal 的"affected_pages 映射"是核心差异化**——它不仅告诉你"用户抱怨什么"，更告诉你"在哪些屏 / 哪些步骤抱怨"。

**与 Probe 的互补**：

| | Probe（用户研究） | Signal（工单分析） |
| --- | --- | --- |
| 数据来源 | **主动**深访 5-8 人 | **被动**整理已有 100-1000+ 条反馈 |
| 样本量 | 少而深 | 多而浅 |
| 洞察类型 | 动机 / JTBD / 情感曲线 | 高频卡点 / 流程断点 |
| 证据链 | 完整 quote + 上下文 | 频次 + 代表性 quote |
| 触发时机 | 项目初期定方向 | 改版前定位问题 / 持续监测 |

**最佳实践**：Probe 和 Signal **交叉印证**——访谈中提到的痛点是否在工单里也高频？工单里高频问题是否在访谈中能挖到根因？

---

## Chain Context

### 上游读取（Step 0 执行）

按 [chain-protocol.md](../../chain-protocol.md) §2.1 v1.1 智能适配规则：

1. 扫描会话中的 `<!-- spark-context:frame -->` / `<!-- spark-context:scope -->` / `<!-- spark-context:probe -->` marker
2. 读取项目目录 `spark-output/context/frame.json` / `scope.json` / `probe.json`
3. 都没有则按 standalone 模式启动

可复用字段映射：

- `frame.project_name` / `scope.project_name` → 用于 `signal.project_name`，避免用户重填
- `frame.users[]` / `scope.target_users[]` → 帮助分类时判断"反馈是否来自目标用户"
- `frame.problem_statement` → 帮助判断哪些反馈与项目核心问题相关（vs 噪声）
- `probe.pain_points[]` → **关键交叉验证锚点**：访谈中提到的痛点是否在工单里也高频？输出时标注"已与 Probe 交叉验证"

### 下游输出（Step 6 执行）

完成 Signal 后，**同时**做两件事：

1. **写盘**：`spark-output/context/signal.json`（目录不存在先创建）
2. **会话内输出紧凑 marker**（不重复输出完整 JSON）：

   ```
   <!-- spark-context:signal ref="spark-output/context/signal.json" -->
   Signal 已保存：project=[name]，[N] 条反馈 → [M] 个聚类痛点（blocker [n] / major [n]），[K] 个 affected_pages
   <!-- /spark-context:signal -->
   ```

3. **降级 fallback**：若写盘失败（chat-only 平台），输出完整 JSON marker 作为唯一持久化通道

### 字段流向下游

Signal 的输出主要服务于 Audit / Journey / Brief：

- `signal.clusters[].affected_pages` → **Audit 的走查目标清单**（让 Audit 优先扫被反馈最多的页面）
- `signal.clusters[].affected_flows` → **Journey 的断点候选**（每个断点标"工单反馈 N 次"）
- `signal.top_pain_points` → **Brief 的 constraints 候选**（"改版后必须解决的高频痛点"）
- `signal.cross_validation_suggestion.bench_suggestion` → 触发用户去跑 `/竞品拆解` 做横向对比

下游 Skill：**Audit**（reads: [..., signal, ...]，走查时优先关注 signal 反馈最多的页面）/ **Journey**（reads: [..., signal, ...]，断点标注引用 signal 频次）/ **Brief**（reads: [..., signal 间接, ...]，通过 Audit 进入策略）。

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

- 用户说"帮我分析这堆工单 / 反馈 / 评论"
- 用户说"我有 200 条客服记录想看看高频问题"
- 用户说"从用户反馈里找体验痛点"
- 用户说"VoC 分析 / 客诉分析 / 反馈聚类"（设计师语境）
- 用户使用 `/工单分析` 指令

---

---

## 独立能力（无需连接器）

本 Skill 在完全离线、无任何连接器的场景下即可完整交付，所有方法论与输出形态不依赖外部系统：

- **高频痛点提炼**：按 priority_score（frequency × severity × business_impact）排序
- **链式上下文双通道**：写入 `spark-output/context/signal.json` + 会话内 marker block，下游 Brief / Probe / Frame 等可直接读取
- **affected_pages 热力图**：本地生成，定位高频痛点的页面分布
- **弱信号识别**：低频但严重的工单单独标记，避免被高频淹没
- **Probe 交叉验证**：若有上游 Probe 上下文，自动做主动 / 被动数据对照

> 红线：缺连接器时 **绝不 abort**，所有引导与输出路径必须照常完成。

## 增强能力（连接器加持）

接入以下连接器后，可减少手动粘贴、提高对齐效率。所有连接器均为可选，未装时按"降级路径"列的方式回落。

| 连接器 | 阶段 | 增强能力 | 降级路径 |
| --- | --- | --- | --- |
| — | — | — | — |

> v0.6 暂无强相关连接器（客服 / 工单系统平台分散，v0.7+ 评估 Zendesk / Intercom MCP 接入）。

**接入触发**：用户首次调用 `/工单分析` 时，Skill 主动检测已认证的连接器并显示「已检测到：XXX，将自动启用增强模式」提示，用户可在该次会话中选择关闭。

**字段流向变化**：

- （本 Skill 启用连接器不引入新的 chain.schema 字段，仅影响执行路径）

> 所有新增字段都是 **可选**，未启用连接器时字段缺省，下游 Skill 必须能容忍缺省。

---

## 执行流程

按 Step 0 → 1 → 2 → 3 → 4 → 5 → 6 顺序执行。

### Step 0 — Chain Context 读取

按上文执行。读到 frame / scope / probe 时告知用户："已读到 [上游 Skill] 上下文，分析时会重点交叉验证 [N] 个已知痛点 / 标注与目标用户相关的反馈。"

### Step 1 — 数据接入与清洗

用 `AskUserQuestion` 询问：

1. **数据形态**：
   - CSV / Excel 文件路径（用 Read 解析）
   - 粘贴的文本（直接处理）
   - 截图描述（用户口述内容）
   - 多源混合（标注每条来源渠道）
2. **数据规模判断**：
   - **≤ 20 条 → 精读模式**：逐条分析，输出详细解读 + 直接给到痛点清单，不做统计聚类
   - **> 20 条 → 统计模式**：自动分类 + 聚类 + 频次统计 + 输出聚合报告
3. **时间范围**（可空）：用于报告时效标注
4. **数据来源渠道**（多选）：support-ticket / app-store-review / community / in-app-feedback / social / other

**清洗规则**：

- 去除完全重复的反馈（精确匹配）
- 合并高度相似的反馈（相似度 > 90%），标注合并数量
- 超短反馈（< 5 字且无实质内容，如"好""差"）单独统计、不纳入深度分析
- 去除明显广告 / 灌水 / 与产品无关的反馈
- 识别反馈来源渠道并标注

输出清洗结果："共 [N] 条 → 去重合并后 [M] 条进入分析。"

### Step 2 — 反馈分类（6 大类）

每条反馈打主分类标签（不确定时标主+次）：

| 类别 | 判断标准 | 设计师视角的处理优先级 | 示例 |
| --- | --- | --- | --- |
| **feature_request** | 用户希望有但目前没有的功能 | 中（不是 Signal 重点，归到 PRD 候选） | "希望能支持批量导出" |
| **bug_report** | 功能存在但表现异常 | 高（关联具体页面，是 Audit 走查重点） | "点击保存后数据丢失了" |
| **usage_question** | 不知道怎么用，找不到功能 | **高**（强信号 → recognition / visibility 体验问题） | "怎么修改密码？" |
| **experience_complaint** | 功能有但体验不好 | **最高**（Signal 的核心目标） | "加载太慢""界面太复杂" |
| **positive** | 满意 / 好评 / 推荐 | 低（参考保留，不深入） | "这个功能很好用" |
| **other** | 无法归类或与产品无关 | 跳过 | 灌水 / 广告 / 闲聊 |

**设计师视角的重要提醒**：`usage_question` 在 PM 视角是"客服培训问题"，但在设计师视角是**强信号**——意味着用户找不到 / 看不到 / 记不住功能，对应 Nielsen 的 visibility / recognition / help-docs 维度。Signal 把它和 `experience_complaint` 一起作为重点分析对象。

### Step 3 — 情感分级（仅对 experience_complaint / bug_report）

| 情感 | 判断信号 | 校准规则 |
| --- | --- | --- |
| **positive** | 点赞 / 好评 / 推荐 / 感谢 | 仅陈述事实的好评（"功能可用"）判中性 |
| **neutral** | 陈述事实 / 提问 / 建议（语气平和） | 功能需求默认中性，除非带明显不满 |
| **negative_mild** | 语气平和的不满（"不太方便"） | 轻度负面 |
| **negative_medium** | 明确表达失望（"很失望""体验很差"） | 中度负面 |
| **negative_severe** | 威胁性表达（"再不修就卸载""要投诉"） | **重度负面 → 优先级 +1 级** |

### Step 4 — 主题聚类（双方法并行）

#### 方法 A：亲和图法（Affinity Mapping）

1. **拆分观察点**：每条反馈拆出独立观点为"卡片"
2. **自然聚类**：按相似性分组，**不预设标签**，让主题从数据中浮现
3. **命名主题**：为聚类命名（"支付流程繁琐""搜索结果不相关"）
4. **识别层级**：小聚类归入更大主题群（"支付繁琐"+"退款周期长" → "交易体验"）
5. **标注异常值**：无法归入任何聚类的反馈单独标注——可能是早期信号

#### 方法 B：主题编码（Thematic Coding）

1. **开放编码**：逐条打描述性标签（"加载慢""闪退""找不到入口"）
2. **轴心编码**：标签归类为更抽象主题（"加载慢"+"闪退" → "性能问题"）
3. **选择性编码**：识别核心主题，建立逻辑关系
4. **量化频次**：统计每个主题被提及的次数和占比

#### 双方法合并

两方法结果对比：

- **两方法都聚出同一主题** → 高可信度
- **只有一种方法聚出** → 中可信度
- **结果不一致** → 标注分歧、保留两种主题供下游判断

**每个聚类的输出结构**：

```yaml
- id: "signal-cluster-1"
  topic: "支付流程繁琐"
  sub_topic: "确认页步骤过多"
  frequency: 24  # 提及次数
  ux_severity: major  # 见 Step 5 判断
  credibility: high  # 双方法都识别 + 多渠道出现
  sample_quotes:
    - "[用户A][2026-03-15] 付款要点 5 次才到最后一步，太繁琐"
    - "[用户B][2026-03-22] 优惠券页面找不到入口"
  affected_pages:
    - "/checkout/confirm"
    - "/checkout/coupon-select"
  affected_flows:
    - "下单流程：购物车 → 确认页 → 支付"
```

### Step 5 — 痛点优先级排序

**Signal 优先级公式（简化版，去掉付费权重）**：

```
priority_score = frequency × ux_severity × credibility
```

| 维度 | 赋值标准 |
| --- | --- |
| **frequency** | 高频（> 10 次）= 3，中频（3-10 次）= 2，低频（< 3 次）= 1 |
| **ux_severity** | blocker（功能不可用 / 流程中断）= 3，major（核心流程体验严重受损）= 2，minor（细节体验问题）= 1 |
| **credibility** | high（双聚类法 + 多渠道一致）= 1.2，medium（部分一致）= 1.0，low（单源单方法）= 0.8 |

按 priority_score 降序输出 **Top 痛点列表**（不强制 Top 10，按实际拐点定）。

#### 弱信号识别（Tanguy Crusson 洞察启发）

⚠️ **不止看高频**——主动识别**低频但 ux_severity = blocker 的弱信号**：

- 出现频次低但每条都涉及"功能不可用 / 流程中断 / 数据丢失"
- 来自高价值用户群（如付费 / 长期使用 / 影响力账号）
- 与现有产品逻辑有结构性冲突

标记 `signal_type: weak-signal` 单独列出。这些不能因低频被忽视——可能是早期信号、可能是冰山下的系统性问题。

### Step 6 — 设计师视角输出 + 横向交叉建议

#### 6.1 affected_pages 映射（核心差异化）

每个 cluster 必须关联到**具体页面 / 流程**：

- **直接命名页面**：用户描述里直接提到的页面名 / URL / 模块名
- **从用户行为推断**：用户描述"我点了 X 然后…"→ 推断 X 所在页面
- **从功能名推断**：用户描述"批量导出找不到入口"→ 推断"批量导出"功能所在页面 + 推断"入口可见性问题"
- **多页面关联**：跨页面流程（如下单流）列出所有相关页面

无法确定的标"待用户确认"，不要瞎猜。

#### 6.2 推荐下一步 Skill

每个 Top 痛点附带**推荐的下一步 Skill**：

- 痛点 = 现有产品体验问题（高频 + 关联具体页面）→ **推荐 `/启发评估`** 系统走查关联页面
- 痛点 = 流程断点（用户卡在某步骤 / 流程中断）→ **推荐 `/用户旅程`** 把断点放进情感曲线
- 痛点 = 涉及功能缺失 / 改版方向 → **推荐 `/设计简报`** 把改版方向沉淀为一页纸
- 痛点 = 行业普遍现象（可疑）→ **推荐 `/竞品拆解`** 做横向对比

#### 6.3 横向交叉建议（Bench 触发）

报告末尾主动建议：

> 💡 想验证这些痛点是行业普遍现象还是只是本产品问题？建议下一步去**搜竞品的同类工单 / 评论**（应用商店、知乎、小红书），用 `/竞品拆解` 把对方的口碑反馈也拉进来做横向对比。例如：本产品工单中 [topic X] 出现 [N] 次——竞品 [Y] 用户是否也抱怨同样问题？

把 `cross_validation_suggestion.bench_suggestion` 字段填入。

#### 6.4 Markdown 报告

输出到对话 + 保存到 `spark-output/signal/[project-slug].md`：

```markdown
# Signal — [项目名]

- **生成时间**：[ISO8601]
- **数据来源**：[渠道列表，如"App Store 评论 + 客服工单"]
- **样本规模**：[N 条原始 → M 条去重合并]
- **时间范围**：[YYYY-MM-DD ~ YYYY-MM-DD]
- **分析模式**：精读 / 统计

## 总览

**分类分布**：

| 类别 | 数量 | 占比 |
| --- | --- | --- |
| 体验吐槽 | N | X% |
| Bug 报告 | N | X% |
| 使用咨询 | N | X% |
| 功能需求 | N | X% |
| 正面评价 | N | X% |
| 其他 | N | X% |

**情感分布**（仅 experience_complaint + bug_report）：

🟢 正面 X% · ⚪ 中性 Y% · 🟡 轻度负面 a% · 🟠 中度负面 b% · 🔴 重度负面 c%

## Top 痛点（按 priority_score 排序）

### 🥇 [topic 1]
- **频次**：N（占总反馈 X%）
- **UX 严重度**：major
- **可信度**：high（双聚类法一致 + 多渠道）
- **优先级分**：18.0
- **关联页面**：`/checkout/confirm`、`/checkout/coupon-select`
- **关联流程**：下单流程
- **代表性原文**：
  > "付款要点 5 次才到最后一步，太繁琐"（用户A · 2026-03-15）
  > "优惠券页面找不到入口"（用户B · 2026-03-22）
- **推荐下一步**：`/启发评估` 系统走查 `/checkout/*` 流程

### 🥈 [topic 2]
（同上）

## ⚠️ 弱信号（低频但严重）

### [topic X]
- **频次**：3（低）
- **UX 严重度**：blocker
- **关注理由**：3 条都涉及"数据丢失"——结构性问题
- **代表性原文**：
  > "..."

## affected_pages 热力图

| 页面 / 模块 | 关联痛点数 | 总反馈频次 |
| --- | --- | --- |
| /checkout/confirm | 3 | 32 |
| /search/results | 2 | 18 |

## 横向交叉建议

[bench_suggestion 字段内容]

## Probe 交叉验证（若有上游 Probe 上下文）

- Probe 提到的痛点 "[X]"：本次 Signal 中频次 [N]，**已交叉验证 ✅**
- Probe 提到的痛点 "[Y]"：本次 Signal 中未出现，**建议补充数据源或重做访谈**

## 下一步建议

- **走查关联页面**：基于 Top 痛点的 affected_pages，建议进入 `/启发评估`
- **标断点**：基于 affected_flows，建议进入 `/用户旅程` 标情感断点
- **横向对比**：基于交叉建议，建议进入 `/竞品拆解` 做行业对比
```

#### 6.5 双通道 Context 输出

按 [chain-protocol.md](../../chain-protocol.md) §2.1 v1.1 智能适配规则：

**Step 1 — 写盘到 `spark-output/context/signal.json`**（必做）：

```
{
  "skill": "signal",
  "generated_at": "<ISO8601>",
  "project_name": "...",
  "source": {
    "channels": ["support-ticket", "app-store-review"],
    "total_count": 200,
    "after_dedup_count": 187,
    "time_range": "2026-01-01 to 2026-03-31"
  },
  "classification": {
    "feature_request": 0,
    "bug_report": 0,
    "usage_question": 0,
    "experience_complaint": 0,
    "positive": 0,
    "other": 0
  },
  "sentiment": {
    "positive": 0,
    "neutral": 0,
    "negative_mild": 0,
    "negative_medium": 0,
    "negative_severe": 0
  },
  "clusters": [
    {
      "id": "signal-cluster-1",
      "topic": "...",
      "sub_topic": "...",
      "frequency": 0,
      "ux_severity": "blocker|major|minor",
      "credibility": "high|medium|low",
      "priority_score": 0,
      "sample_quotes": ["..."],
      "affected_pages": ["..."],
      "affected_flows": ["..."],
      "signal_type": "high-frequency|weak-signal"
    }
  ],
  "top_pain_points": [
    {
      "cluster_id": "signal-cluster-1",
      "priority_score": 18.0,
      "recommended_next_skill": "audit|journey|brief|bench"
    }
  ],
  "cross_validation_suggestion": {
    "probe_overlap": ["..."],
    "bench_suggestion": "..."
  }
}
```

> ⚠️ **统计字段自动 derive 规则（强制）**：`source.total_count` = 原始反馈条数；`source.after_dedup_count` = 去重后实际分析条数；`classification.*` = 对已分析反馈按类型分组计数（各项之和 = `after_dedup_count`）；`sentiment.*` = 对已分析反馈按情感分组计数（各项之和 = `after_dedup_count`）。**禁止手写估算**——必须从分析结果 programmatic 计算得出。若发现计数之和 ≠ `after_dedup_count`，重新计算修正。

**Step 2 — chat 输出紧凑 marker**（不重复输出完整 JSON）：

```
<!-- spark-context:signal ref="spark-output/context/signal.json" -->
Signal 已保存：project=[name]，[N] 条反馈 → [M] 个聚类痛点（blocker [n] / major [n]），[K] 个 affected_pages
<!-- /spark-context:signal -->
```

**降级 fallback**：若写盘失败（chat-only 平台），输出完整 JSON marker 作为唯一持久化通道。

### Handoff 提示（必输出）

> **协议**：按 [`_shared/next-skill.md`](../../_shared/next-skill.md) 三层结构模板输出；前 5 候选由 `_shared/skill-graph.json` 的依赖图算法实时算（done ⊆ ready，按 next_hint.preferred → alternatives → 同阶段 → anchor → fan-out 排序），优先建议从 `_shared/skill-graph.json#skills[id="signal"].next_hint` 读取。

**首行模板**：`✅ 工单分析 已完成，高频痛点 + affected_pages 映射已沉淀。`

**本 Skill 的 `next_hint`**（来自 skill-graph.json，**不可在此 SKILL.md 内硬编码覆盖**）：

- **preferred**：`/brief`
- **优先理由**：高频痛点 + affected_pages 已锁定，进 Brief 锚定本次改版的优先级。
- **alternatives**：`/journey` (想把工单证据并入旅程地图)
- **emoji**：📞

**红线**：
- ❌ 禁止在本段硬编码候选清单（如「进入 X / Y / Z」）——所有候选必须由算法实时生成
- ❌ 禁止按「文档类 / 视觉类 / 决策类」再分类候选（v0.5.5 起，分类已折叠进 next_hint.alternatives）
- ❌ 禁止与「更新链路面板」段合并——两段必须各自独立成段，中间空一行
- ❌ 禁止漏第 2 行候选清单——即使候选只有 1 个、或为空（终端节点）也要写出来

---

## 质量标准

1. **不过度推断**：20 条反馈中 3 条提到某问题，不能说"大量用户反馈" —— 用具体频次数字（"3/20 提及"）
2. **保留原文**：每个 cluster 必须附 ≥ 2 条代表性原文 quote（带用户标识 + 时间戳，可追溯）
3. **affected_pages 不瞎猜**：无法确定关联页面的标"待用户确认"，不要硬猜
4. **双聚类法都跑**：亲和图法和主题编码两方法都要执行，相互校验
5. **弱信号必须单独列**：低频高严重的反馈不能因频次低被埋没
6. **不计算 NPS / 不做趋势分析 / 不出改进建议**：这些是 PM 套件 `/用户反馈分析` 的事，越界了就模糊本 Skill 定位
7. **样本量 < 50 条时标注"样本量有限，结论仅供参考"**

## 红线规则

1. **不编造 quote**：所有 sample_quotes 必须来自原始数据，禁止 AI 改写或合成
2. **不虚构页面关联**：无法从反馈推断出页面 / 流程时，标 `[待用户确认]`，禁止硬编码默认页面
3. **不做趋势预测**：无历史数据时不做环比分析、不预测拐点 —— 那是 Metric 的活
4. **不替设计师做改进建议**：Signal 只输出"问题在哪、关联什么"，"怎么改"是 Audit / Brief / Stories 的活
5. **不替代正式可用性测试**：Signal 是被动数据整理，不能替代主动用户测试

---

## 反馈渠道参考

中国互联网产品常见反馈渠道（按设计师视角的数据质量排序）：

| 渠道 | 数据特点 | 设计师视角的适合分析维度 |
| --- | --- | --- |
| **产品内嵌反馈入口** | 使用中即时反馈，场景明确（含截图） | 功能体验优化（最高质量，能直接定位页面） |
| **微信客服 / 企业微信** | 即时反馈，语境完整，可追问 | 深度卡点分析（含上下文） |
| **400 热线 / 工单系统** | 结构化记录，紧急问题 | Bug 和 blocker 痛点 |
| **App Store / 应用宝评论** | 公开评分 + 文字，量大 | 高频体验吐槽 |
| **小红书评论 / 笔记** | 真实体验分享，含竞品对比 | 体验感知 + 横向对比触发 |
| **知乎问答 / 讨论** | 深度讨论，专业用户 | 深层 UX 模式问题 |
| **钉钉 / 飞书反馈群** | B 端用户为主，需求明确 | 功能需求提炼（不是 Signal 重点） |

---

## 输入不足处理

- **反馈 < 10 条**：输出逐条详细解读，不做统计分析（样本太少无统计意义）
- **无渠道 / 时间信息**：正常分析，但标注"缺少来源和时间信息，建议补充"
- **混杂多语言**：按语言分组分别分析
- **单一渠道数据**：正常分析，但标注"单一数据源，建议补充其他渠道做交叉验证"
- **反馈过短或灌水多**：先清洗，如清洗后剩余 < 10 条则建议补充数据

---

## 实操注意事项

### 与 Probe 的协作节奏

**理想流程**：先 Signal（被动整理已有数据，发现高频痛点候选）→ 再 Probe（针对 Top 痛点做 5-8 人深访挖根因）→ 两者结果交叉验证。

**反向也可**：先 Probe（小样本定性洞察）→ 再 Signal（大样本验证是否广泛存在）→ 标记交叉一致的痛点为"高置信度"。

### 与 Audit 的协作节奏

Signal 的 `affected_pages` 是 Audit 走查目标的最佳输入——避免 Audit "全产品扫一遍"的低效，聚焦真实被反馈最多的页面。

### 与 Bench 的横向触发

Signal 自身不做竞品分析，但**每次必输出 bench_suggestion**——把"行业普遍 vs 本产品独有"的判断委托给 Bench。

### 数据量级建议

| 反馈量 | 推荐处理方式 |
| --- | --- |
| < 10 条 | 精读模式（逐条详解） |
| 10-50 条 | 统计模式 + 标注"样本量有限" |
| 50-200 条 | 标准统计模式 |
| 200-1000 条 | 标准统计模式 + 强制双聚类法 |
| > 1000 条 | 建议分批处理（按时间 / 渠道切片），单批 < 1000 |

---

## 已知限制

- AI 聚类带主观性，**建议关键聚类配合人工 review**
- 短文本反馈（< 20 字）的情感判断准确率较低
- 跨语言混杂数据需分组处理，跨语言聚类暂不支持
- 不替代正式的用户研究（用 Probe）
- 不替代产品决策分析（用 PM 套件 `/用户反馈分析`）
- 不做趋势预测和指标度量（用 Metric）
