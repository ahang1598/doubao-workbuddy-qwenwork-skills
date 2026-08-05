---
name: 设计度量
name_en: "metric"
argument-hint: "输入要度量的产品或功能，如：会员注册流程的转化漏斗指标体系"
description: >
  设计度量蓝图（跨界补充：数据意识）。在设计阶段就把度量定好——把 /设计简报 的设计标准翻译为可追踪事件 + 指标公式 + 仪表盘字段 + 埋点缺口清单。输出四级度量结构（North Star /设计度量 + Driver Metrics + Counter Metrics + Health Metrics），让设计师从"做出来"上升到"做出来能度量、能复盘"。

  触发关键词：设计度量、design metrics、北极星指标、North Star /设计度量、KPI、埋点、Instrumentation、数据追踪、上线后怎么知道做对了、怎么量化、定指标。

  排除（反向）：设计稿走查（用 /设计走查）、可用性测试（用 test）、实现验收（用 /设计验收）、完整商业模型分析（PM 职责）。

description_en: >
  Design Metrics Blueprint (cross-discipline: data awareness). Defines measurement in the design
  phase — translates Brief's design standards into trackable events + metric formulas + dashboard
  fields + instrumentation gap inventory. Outputs a four-tier measurement structure (North Star
  Metric + Driver Metrics + Counter Metrics + Health Metrics), elevating designers from "ship it"
  to "ship it, measure it, learn from it".

  Triggers when a designer says: "design metrics", "North Star Metric", "KPI", "instrumentation",
  "analytics tracking", "how do I know if this worked", "how to quantify success",
  "define metrics", "设计度量", "埋点", "上线后怎么知道做对了".

  Excludes: design file review (use /check), usability testing (use test),
  implementation QA (use /qa), full business model analysis (PM responsibility).

allowed-tools:
  - Read
  - Write
  - Glob
  - Grep
  - AskUserQuestion
chain:
  protocol_version: "1.0"
  reads: [brief, stories, frame, sitemap, flow-web, flow-mobile, pitch, qa]
  writes: metric
  schema:
    skill: string
    generated_at: string
    project_name: string
    analytics_baseline:
      tool: string
      existing_events_count: number
      coverage_estimate: enum [strong, partial, none]
    north_star_metric:
      name: string
      formula: string
      target: string
      timeframe: string
      business_alignment: string
      why_this_one: string
    driver_metrics:
      - name: string
        relation_to_nsm: string
        formula: string
        target: string
        timeframe: string
        slice_dimensions: array<string>
        events_needed: array<string>
        instrumentation_status: enum [exists, partial, missing]
        related_story: string
        related_strategy_dimension: string
    counter_metrics:
      - name: string
        what_to_prevent: string
        formula: string
        threshold: string
    health_metrics:
      - name: string
        what_it_protects: string
        threshold: string
        alert_when: string
    instrumentation_gaps:
      - event: string
        where_to_add: string
        priority: enum [must, should, nice-to-have]
        related_metric: string
    dashboard:
      primary_view: array<string>
      drill_down_dimensions: array<string>
      review_cadence: enum [daily, weekly, biweekly, monthly]
      owner_role: string
---

# 设计度量

> 你是设计度量专家。设计师最常犯的错是**做之前没想清楚怎么知道做对了**——上线后才补埋点，结果数据回不来、复盘没素材、下一版还得拍脑袋。本 Skill 在设计阶段就把度量定好，把 Brief 的"设计标准"翻译为**可追踪事件 + 指标公式 + 仪表盘字段 + 埋点缺口清单**。

**Metric 是跨界补充**——传统设计师不擅长数据，本 Skill 帮设计师"像 PM / Data 一样思考度量"，且**只覆盖设计师必须 own 的部分**，不替代完整商业建模。

**与现有 Skill 的边界**：

| | Brief.design_criteria | Pitch.success_metric | Metric（本 Skill） |
| --- | --- | --- | --- |
| 详细度 | 粗略列出标准 | 一句话 NSM | **完整度量蓝图（含埋点）** |
| 用户 | 设计师对齐 | 决策者拍板 | **设计师 + 数据团队 + 工程师** |
| 时机 | 设计开始前 | 设计完后汇报 | **设计完成、上线前** |
| 输出 | quantitative + qualitative 短列表 | 1 个核心数字 | **NSM + Driver + Counter + Health 四级 + 事件清单** |

**核心使命**：让设计师**在交付前**就把这 4 个问题回答清楚：
1. 上线后用一个数字判断成功，是哪个？（North Star）
2. 推动这个数字的关键中间指标是什么？（Drivers）
3. 哪个数字涨上来反而是坏事？（Counter）
4. 哪个数字不能跌破？（Health）

---

## Chain Context

### 上游读取（Step 0 执行）

按以下顺序尝试读取上下文：

1. 扫描会话中的 marker：`brief` / `stories` / `frame` / `sitemap` / `flow-web` / `flow-mobile` / `pitch` / `qa`
2. 读取项目目录 `spark-output/context/*.json`
3. 至少要读到 **brief** 或 **frame**（最低门槛），否则降级到 Step 1 询问

**字段映射（度量四级如何消费上游）**：

| Metric 段 | 上游来源 | 字段映射 |
| --- | --- | --- |
| **North Star Metric** | brief + frame | `frame.business_angle.strategic_intent`（growth/retention/defensive）+ `brief.business_goal[0]` |
| **Driver Metrics** | brief + stories | `brief.design_criteria.quantitative` 每条 + `stories[].acceptance_criteria` 可观察项 |
| **Counter Metrics** | brief + pitch | `brief.out_of_scope` 反推（不该被优化的方向）+ `pitch.sections.asks` 中的"防止 over-optimization"类 |
| **Health Metrics** | qa + check | `qa.deviations`（如响应式 / 性能差异）反推性能基线 + `check.findings` 中的 blocker 反推系统稳定性 |
| **Events Needed** | stories.design_touchpoints + flow-web/mobile.flows | 每个 design_touchpoint state 转 1-2 个埋点事件 |
| **Slice Dimensions** | brief.user + frame.persona | persona 分群 + 平台 + tier |

读到上下文后告知用户："读到 [N] 个上游 Skill。已识别 [M] 条来自 Brief design_criteria 的度量需求 + [K] 条来自 Stories acceptance_criteria 的可观察项。预计输出 NSM + [n] 个 Drivers + [n] 个 Counter + [n] 个 Health metrics。"

### 下游输出（Step 6 执行）

完成 Metric 后，**同时**做两件事：

按 [chain-protocol.md](../../chain-protocol.md) §2.1 v1.1 智能适配规则：

1. **写盘到 `spark-output/context/metric.json`**（必做，主持久化通道；目录不存在先创建）
2. **chat 输出紧凑 marker**（⛔ 不要在 chat 内输出完整 JSON）：

   ```
   <!-- spark-context:metric ref="spark-output/context/metric.json" -->
   Metric 已保存：NSM=[name]，[N] Drivers / [M] Counters / [K] Health，[G] 个 must 埋点缺口待补
   <!-- /spark-context:metric -->
   ```

降级 fallback：若写盘失败，输出完整 JSON marker（无 ref）。详见 §2.1。

3. **额外保存 Markdown 报告**：`spark-output/metric/[project-slug].md`，含度量蓝图 + 埋点清单 + 仪表盘建议。

下游可消费 Skill：**Retro**（项目复盘时对照实际数据 vs 设计阶段定的指标） / **PRD**（PRD 的 Section 4 Goals & Metrics 可引用 Metric 输出的完整指标体系替代 Brief 简版） / **Pitch**（汇报时引用更详细的指标）。

### 字段流向下游

- `metric.north_star_metric` → **Retro** 的 Decision Validation 锚点（项目结束后看 NSM 是否达标）
- `metric.driver_metrics[]` → **Retro** 的"假设验证"输入（每个 Driver 是否真的牵引了 NSM）
- `metric.counter_metrics[]` → **Retro** 的"What Didn't"输入（Counter 异常 = 设计副作用）
- `metric.instrumentation_gaps[severity=must]` → **PRD** 的工程交付段（如未完结，转下一迭代 PRD）

---

## 触发条件

- 用户说"定指标 / 度量蓝图 / 北极星指标 / 怎么衡量上线效果"
- 用户说"上线前先把指标定了 / 跟数据团队对齐"
- 用户使用 `/设计度量` 指令
- Brief 完成后或 PRD 完成前，设计师 / PM 准备进入数据对齐时

---

---

## 独立能力（无需连接器）

本 Skill 在完全离线、无任何连接器的场景下即可完整交付，所有方法论与输出形态不依赖外部系统：

- **指标体系四件套**：North Star / Driver / Counter / Health Metrics 完整方法论
- **链式上下文双通道**：写入 `spark-output/context/metric.json` + 会话内 marker block，下游 Retro / PRD 可直接读取
- **埋点缺口清单（给工程师）**：本地生成可直接交付
- **Dashboard 建议**：与 Chart Skill 配合本地完成

> 红线：缺连接器时 **绝不 abort**，所有引导与输出路径必须照常完成。

## 增强能力（连接器加持）

接入以下连接器后，可减少手动粘贴、提高对齐效率。所有连接器均为可选，未装时按"降级路径"列的方式回落。

| 连接器 | 阶段 | 增强能力 | 降级路径 |
| --- | --- | --- | --- |
| **Linear / Jira** | 执行流程（指标对齐阶段） | 拉 sprint 任务量 / 完成率作为 Driver Metric 的输入参考 | 未装时让用户手动输入 sprint 数据 |
| **Analytics（GA / Mixpanel / 神策）** | 执行流程输出后 | 上线后自动拉真实数据填充 Dashboard，闭环 Metric → 实际表现 | 未装时只输出指标定义 + 埋点清单，数据由 PM / 数据分析师后续手动填 |

**接入触发**：用户首次调用 `/设计度量` 时，Skill 主动检测已认证的连接器并显示「已检测到：XXX，将自动启用增强模式」提示，用户可在该次会话中选择关闭。

**字段流向变化**：

- 启用 **Linear / Jira** → `chain.schema` 新增可选字段 `sprint_signals: array<{sprint_id, throughput, completion_rate}>`
- 启用 **Analytics** → `chain.schema` 新增可选字段 `data_source: {provider, dashboard_url, query_refs}`，Retro 可直接拉读上线后表现

> 所有新增字段都是 **可选**，未启用连接器时字段缺省，下游 Skill 必须能容忍缺省。

---

## 执行流程

按 Step 0 → 1 → 2 → 3 → 4 → 5 → 6 顺序执行。

### Step 0 — Chain Context 读取

按上文执行。

### Step 1 — 度量基线确认

用 `AskUserQuestion` 询问：

1. **使用的数据工具**：
   - Mixpanel / Amplitude / GA4 / 自建埋点 / PostHog / 飞书数据 / 神策 / 其他
2. **现有埋点覆盖度**：
   - Strong（核心 flow 都有埋点）
   - Partial（部分埋点，主要靠 GA pageview）
   - None（什么都没有）
3. **数据复盘节奏**：daily / weekly / biweekly / monthly
4. **谁是数据 Owner**：设计师自己 / PM / Data Analyst / 没人

这些影响后续 instrumentation_gaps 的优先级和 dashboard 的复杂度。

### Step 2 — North Star Metric 推导

**核心规则**：一个项目只有 1 个 North Star（不能有"双北极星"——那叫没北极星）。

**推导逻辑**：

1. 读 `frame.business_angle.strategic_intent`：
   - `growth` → NSM 候选：新用户激活 / 周活跃用户数 / 关键动作完成率
   - `retention` → NSM 候选：N 日留存 / 周活跃 / 流失率
   - `defensive` → NSM 候选：NPS / 卸载率 / 关键路径成功率
   - `cost-center` → NSM 候选：人均成本 / 自助率 / 工单减少率

2. 对照 `brief.business_goal`：从候选中选**最直接对应业务目标**的那个

3. 检查 `brief.design_criteria.quantitative`：如果 design_criteria 里就有一个明确的"完成 / 留存"类指标，直接采纳

**NSM 必须满足 5 个条件**（缺一即不合格）：

- ✅ **直接反映核心价值交换**（用户得到了什么 / 产品提供了什么）
- ✅ **可量化**（数字、百分比，不是"满意度"这种空话）
- ✅ **领先指标**（能预测下游业务，不是滞后指标）
- ✅ **可执行**（设计 / 产品改动能影响它）
- ✅ **不被过度优化反噬**（涨上去就是真好，不会反向坑用户）

**输出结构**：

```yaml
north_star_metric:
  name: "周激活率"
  formula: "本周完成首次回顾的用户 / 本周注册用户"
  target: "≥ 40%"
  timeframe: "60 天达成"
  business_alignment: "对应 brief.business_goal[2] '周留存率 ≥ 40%'"
  why_this_one: "DesignRetro 的核心价值是'设计师每周完成一次回顾'。激活率是这个价值是否成立的最直接信号。比绝对活跃数好，因为它消除规模噪音；比 NPS 好，因为它是行为而非态度；比留存率好，因为它是用户首次成功的领先指标。"
```

### Step 3 — Driver Metrics 设计

NSM 是结果，Drivers 是**推动结果的杠杆**。每个 Driver 必须有"如何推动 NSM"的明确逻辑。

**Driver 数量约束**：3-5 个（少于 3 个说明思考不充分；多于 5 个说明杠杆太散）

**Driver 来源**：

1. **Brief.design_criteria.quantitative 每条 → 一个 Driver**
2. **Stories.acceptance_criteria 中可观察项 → 候选 Driver**
3. **Frame.opportunities 高优先级 → 关键 Driver**

**每个 Driver 输出**：

```yaml
- name: "首屏到完成时长中位数"
  relation_to_nsm: "时长 > 3 分钟时用户放弃率显著上升，直接降低周激活率"
  formula: "median(submit_success.timestamp - welcome_loaded.timestamp)"
  target: "≤ 180 秒"
  timeframe: "30 天内验证"
  slice_dimensions: ["first_time_user vs returning", "mobile vs desktop", "team_size 分桶"]
  events_needed: ["welcome_loaded", "submit_clicked", "submit_success"]
  instrumentation_status: "missing"
  related_story: "story-1"
  related_strategy_dimension: "用户引导"
```

**关键约束**：
- 每个 Driver 必须有 `events_needed`（如果埋不了，Driver 就是空话）
- 每个 Driver 必须有 `slice_dimensions`（不切片的指标信号低，无法判断"为什么")
- `instrumentation_status` 必须如实标 — missing 的指标要进入 Step 4 的 gap 清单

### Step 4 — Counter Metrics 设计

**Counter Metric 的存在意义**：防止过度优化某个指标导致用户体验破坏。

**例子**：
- 优化"点击率" → 标题党 / 引诱点击（counter: bounce rate 不能涨）
- 优化"日活" → 推通知打扰（counter: 通知关闭率 / 卸载率不能涨）
- 优化"周激活率" → 强制 onboarding 完成（counter: NPS / 首次到第二次留存比不能跌）

**Counter Metric 来源**：

1. **brief.out_of_scope 反推**：标榜不做的事，对应需要保护的反指标
2. **Anti-metrics from PRD**（如果有）：PRD Section 4 已声明的 Anti-metrics 直接转
3. **每个 Driver 配一个潜在的反向风险**：问"这个 Driver 涨上去最坏情况是什么？"

**Counter 数量约束**：每个 Driver 至少 1 个对应的 Counter（不能 0）。

**输出**：

```yaml
- name: "强制完成率"
  what_to_prevent: "为了拉激活率，用 modal 弹窗强制用户完成 onboarding，破坏'3 分钟可控'的体验承诺"
  formula: "强制 modal 阻塞型 onboarding 引导次数 / 总 session 次数"
  threshold: "≤ 5%（超过即需重新评估 onboarding 设计）"
```

### Step 5 — Health Metrics + Instrumentation Gaps + Dashboard

#### 5.1 Health Metrics

**Health 是底线**——不直接反映成功，但跌破就是事故。

来源：
- 性能基线（来自 qa.deviations 中的性能问题）
- 错误率（来自 check.findings 中错误处理类问题）
- 兼容性（来自 qa.deviations 中响应式问题）

**典型 Health 指标**：

```yaml
- name: "首屏加载时长 P95"
  what_it_protects: "Brief.design_criteria 隐含的可用性基线"
  threshold: "≤ 3 秒"
  alert_when: "连续 2 天 P95 > 3 秒"

- name: "提交失败率"
  what_it_protects: "用户完成动作的可达性"
  threshold: "≤ 1%"
  alert_when: "单日 > 3% 触发告警"

- name: "JS 错误率"
  what_it_protects: "整体稳定性"
  threshold: "≤ 0.5% session"
  alert_when: "单日新增错误 > 10 个"
```

Health 数量约束：3-5 个，不要列全部。

#### 5.2 Instrumentation Gaps（埋点缺口清单）

**这是 Metric Skill 给工程师的最直接产出**。把所有 Driver + Counter + Health 涉及但 `instrumentation_status: missing` 的事件汇总：

```yaml
instrumentation_gaps:
  - event: "welcome_loaded"
    where_to_add: "src/app/(retro)/new/welcome/page.tsx 顶部 useEffect"
    priority: "must"
    related_metric: "首屏到完成时长中位数"
  - event: "submit_clicked"
    where_to_add: "src/app/(retro)/new/preview/page.tsx Submit Button onClick"
    priority: "must"
    related_metric: "首屏到完成时长中位数 + 提交失败率"
  - event: "submit_success / submit_failure"
    where_to_add: "API 回调"
    priority: "must"
    related_metric: "周激活率 NSM + 提交失败率 Health"
  - event: "weekstreak_milestone_reached"
    where_to_add: "src/components/retro/WeekStreak.tsx"
    priority: "should"
    related_metric: "连续完成激励效果分析"
```

**优先级分级**：
- **must**：NSM / 任何 Driver / Health 需要的事件
- **should**：Counter 需要的事件
- **nice-to-have**：辅助分析事件（如组件曝光、悬停时长）

#### 5.3 Dashboard 建议

**primary_view**（看板首屏 4-6 个核心数字）：
- NSM
- 2-3 个最关键的 Driver
- 1 个 Counter
- 1 个 Health

**drill_down_dimensions**（钻取维度）：
- persona 分群
- 平台（mobile / desktop）
- 用户 tier
- 时间（按周 / 按月）

**review_cadence**：基于 Step 1 用户回答 + 项目阶段
- v1 上线后头 2 周：daily
- 稳定后：weekly

**owner_role**：基于 Step 1 用户回答；如果"没人"，强制标注"建议指定 owner，否则数据 = 没意义"。

### Step 6 — 输出

#### 6.1 Markdown 报告（输出到对话 + 保存到 `spark-output/metric/[project-slug].md`）

```markdown
# Metric Blueprint — [项目名]

- **生成时间**：[ISO8601]
- **数据工具**：[tool]
- **现有埋点覆盖**：strong / partial / none
- **复盘节奏**：[cadence]
- **Owner**：[role]

## 🌟 North Star Metric

**[name]** = [formula]

- 目标：[target]，[timeframe]
- 业务对齐：[business_alignment]
- 为什么是这个：[why_this_one]

## 🚀 Driver Metrics（N 个）

### Driver 1：[name]
- 推动 NSM：[relation_to_nsm]
- 公式：[formula]
- 目标：[target]
- 切片：[slice_dimensions]
- 需要事件：[events_needed]
- **埋点状态**：✅ exists / ⚠️ partial / ❌ missing

（重复每个 Driver）

## ⚠️ Counter Metrics

### Counter 1：[name]
- 防止什么：[what_to_prevent]
- 公式：[formula]
- 阈值：[threshold]

## 💊 Health Metrics

| 指标 | 保护什么 | 阈值 | 告警条件 |
| --- | --- | --- | --- |
| ... | ... | ... | ... |

## 🔧 埋点缺口清单（给工程师）

按优先级排序：

### 🔴 Must（NSM / Driver / Health 必须）

| 事件 | 位置 | 关联指标 |
| --- | --- | --- |
| welcome_loaded | src/app/...page.tsx | 首屏到完成时长 |
| ... | ... | ... |

### 🟠 Should（Counter 需要）
| ... |

### 🟡 Nice-to-have
| ... |

## 📊 Dashboard 建议

**首屏（4-6 个核心数字）**：
- 🌟 NSM
- 🚀 [Driver 1]
- 🚀 [Driver 2]
- ⚠️ [Counter 1]
- 💊 [Health 1]

**钻取维度**：[persona / 平台 / tier / 时间]
**复盘节奏**：[cadence]
**Owner**：[role]

## 下一步建议

- **跟数据团队对齐**：把"埋点缺口清单"部分给到数据工程师，确认埋点排期
- **更新 PRD Section 4**：用本 Metric Blueprint 替代 Brief 简版
- **设计 Pitch.asks 之一**：上线节奏是否等所有 must 埋点齐再上 vs 先上后补
```

#### 6.2 双通道 Context 输出

按 [chain-protocol.md](../../chain-protocol.md) 第 2.1 节执行。

**Step 1 — 写盘到 `spark-output/context/metric.json`**（必做，主持久化通道；目录不存在先创建）。写入以下完整 JSON：

```
{
  "skill": "metric",
  "generated_at": "<ISO8601>",
  "project_name": "...",
  "analytics_baseline": {
    "tool": "Mixpanel|GA4|...",
    "existing_events_count": 0,
    "coverage_estimate": "strong|partial|none"
  },
  "north_star_metric": {
    "name": "...",
    "formula": "...",
    "target": "...",
    "timeframe": "...",
    "business_alignment": "...",
    "why_this_one": "..."
  },
  "driver_metrics": [...],
  "counter_metrics": [...],
  "health_metrics": [...],
  "instrumentation_gaps": [...],
  "dashboard": {
    "primary_view": ["..."],
    "drill_down_dimensions": ["..."],
    "review_cadence": "weekly",
    "owner_role": "..."
  }
}
```

**Step 2 — chat 输出紧凑 marker**（必做，⛔ **不要在 chat 内重复输出 Step 1 的完整 JSON**）：

```
<!-- spark-context:metric ref="spark-output/context/metric.json" -->
Metric 已保存：project=[project_name]，NSM=[name]（目标 [target]），[N] Drivers / [M] Counters / [K] Health，[G] 个 must 埋点缺口
<!-- /spark-context:metric -->
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

> **协议**：按 [`_shared/next-skill.md`](../../_shared/next-skill.md) 三层结构模板输出；前 5 候选由 `_shared/skill-graph.json` 的依赖图算法实时算（done ⊆ ready，按 next_hint.preferred → alternatives → 同阶段 → anchor → fan-out 排序），优先建议从 `_shared/skill-graph.json#skills[id="metric"].next_hint` 读取。

**首行模板**：`✅ 设计度量 已完成，NSM + Driver / Counter / Health 三层指标已定。`

**本 Skill 的 `next_hint`**（来自 skill-graph.json，**不可在此 SKILL.md 内硬编码覆盖**）：

- **preferred**：`/prd`
- **优先理由**：NSM + 埋点清单已定，进 PRD 把度量蓝图写入 Section 4 让工程一并交付。
- **alternatives**：`/retro` (上线后用 Metric 蓝图做复盘)
- **emoji**：📈

**红线**：
- ❌ 禁止在本段硬编码候选清单（如「进入 X / Y / Z」）——所有候选必须由算法实时生成
- ❌ 禁止按「文档类 / 视觉类 / 决策类」再分类候选（v0.5.5 起，分类已折叠进 next_hint.alternatives）
- ❌ 禁止与「更新链路面板」段合并——两段必须各自独立成段，中间空一行
- ❌ 禁止漏第 2 行候选清单——即使候选只有 1 个、或为空（终端节点）也要写出来

---

## 实操注意事项

### 不要做的事

- ❌ **不要列 10+ Drivers**：3-5 个是杠杆，10+ 个是仪表盘装饰
- ❌ **不要用"满意度 / 体验感"做指标**：除非有量化方式（如 NPS 分数 / SUS 评分），否则换成行为指标
- ❌ **不要省 Counter**：每个 Driver 必须配 Counter，否则会被 over-optimize
- ❌ **不要假设埋点已有**：哪怕 99% 已有，剩下 1% 也要在 gaps 标 missing，让工程师确认
- ❌ **不要让 Metric 替代 PM 的商业模型**：unit economics / LTV / CAC 是 PM 职责，Metric 只覆盖设计师 own 的部分

### 用户没有数据工具时

如果 Step 1 答"什么都没有"，**降级 NSM 推荐**：

- 优先用 GA4 + Google Tag Manager（免费 + 即开即用）
- 或纯前端事件 → console.log → 周末手动看（v0 阶段够用）
- 不强求大公司级数据 stack

### 与 Brief.design_criteria 的关系

Brief.design_criteria.quantitative 是设计师**视角的初步度量**；Metric 把它升级为**可追踪 + 有埋点 + 有切片**的完整体系。两者不冲突：
- Brief 阶段先粗写（设计对齐用）
- Metric 阶段精细化（数据对齐用）
- Pitch 阶段反向用 NSM 一句话总结（汇报用）

---

## 已知限制

- 不替代完整商业建模（unit economics / LTV / CAC 等用专门工具）
- AI 推导的 NSM 是候选，**最终拍板需要跟 PM / 业务方对齐**
- 埋点排期与数据基础设施依赖工程团队，Metric 给的是清单不是执行
- 自动模式无法判断已有埋点是否真的能用（建议数据工程师 review）
- 中国大陆需考虑数据合规（不收集敏感字段），Metric 不主动规避，需用户在最终蓝图审一遍

---

## 与兄弟 Skill / PM 套件的边界（v0.4.0 补充）

| 场景 | 用谁 | 不用谁 |
| --- | --- | --- |
| 设计阶段定埋点 + NSM + 体验指标 | **Metric** | Retro（上线后复盘）/ Pitch（汇报数据） |
| 上线后效果度量 / KPI 复盘 | Retro 引用 Metric 数据 | Metric（Metric 不做事后分析，只定标准） |
| 给决策者汇报 + 用数据说服 | Pitch 引用 Metric | Metric（Metric 不写叙事） |
| PM 套件「产品指标 / 北极星」 | PM 套件（业务 / 商业指标） | Metric（**设计师视角**：体验指标 / 任务完成率 / NPS / 跳出率 / 埋点清单） |
| 工程实现埋点代码 | PRD Section 6（埋点字段） | Metric（Metric 出埋点清单，PRD 把它落到工程） |

**Metric 不可替代性**：从设计师视角定「体验指标 + 埋点清单 + NSM 映射」，与 PM 套件「商业指标 / 北极星」并列互补——PM 关心 GMV / DAU，Metric 关心任务完成率 / 错误率 / 满意度。

## 质量标准

1. **NSM（北极星）显式**：项目 NSM 必须显式声明，并标「为什么是这个指标」「与商业 KPI 关系」
2. **体验指标三层**：任务层（完成率 / 时长 / 错误率）+ 满意度层（NPS / CSAT）+ 行为层（留存 / 跳出 / 路径长度）——三层必须各有指标
3. **埋点清单 ≥ 9 项**：核心场景必须 ≥ 9 项埋点，每项含 event_name / 触发时机 / 字段（user / page / action / extra）/ 上报频率
4. **每个指标含目标值**：不能只列「跳出率」，必须标「跳出率 < 30%」目标值 + 「上线后 30 天复盘」时点
5. **与 stories.acceptance_criteria 反向链**：每个验收标准必须对应 ≥ 1 个可观测埋点，否则验收无法度量
6. **失败信号阈值**：必须标「什么数值视为失败 → 触发 rollback / iteration」（如 「task_completion_rate < 60% 视为方向错误」）

## 红线规则

1. **不替代商业指标**：Metric 是体验指标 / 埋点视角，GMV / ARPU / DAU 是 PM 套件——不要在 Metric 写「订单量目标」
2. **不只列指标不写埋点**：每个指标必须能落到具体埋点字段，纯指标列表（无埋点）= 不可执行 = 红线
3. **不替代数据分析**：Metric 是埋点定义阶段，上线后看数 / 归因分析在 Retro 或专门数据 Skill——Metric 不做事后分析
