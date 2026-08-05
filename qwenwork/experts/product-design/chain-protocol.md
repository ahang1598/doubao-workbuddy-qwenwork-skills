# SparkSkillsHub Chain Protocol

> **本文档用途：** 给 Skill 作者看的协议规范。它**不是运行时被加载的注册表**——SparkSkillsHub 的 Skill 是设计为可以独立安装到 Claude Code / Cursor / Qoderwork 等 IDE/Agent 工具中使用的，因此每个 Skill 在运行时都必须自包含。
>
> 本文档存在的意义：(1) 让 Skill 作者抄写协议片段时有标准来源；(2) 维护字段词典避免漂移；(3) 提供链路全景图便于设计新 Skill 时找到挂载点。

---

## 一、为什么需要协议

SparkSkillsHub 的核心差异化是**链式上下文**：每个 Skill 可读取前序 Skill 的产出，设计师不必重复填写项目信息。要让多个 Skill 协作而不互相耦合，需要一份统一的传递协议。

协议必须满足两个约束：

1. **每个 Skill 自包含。** 用户可能只安装其中几个 Skill，或将单个 Skill 与其他来源的 Skill 混合使用。Skill 不能依赖中央注册表。
2. **跨会话可传递。** 既要支持 Cowork 等对话场景（会话内传递），也要支持 IDE / vibe coding 场景（跨会话持久）。

为此协议采用**双通道传递**。

---

## 二、协议核心

### 2.1 双通道传递规则（智能适配版 · v1.1）

每个 Skill 完成产出后，按以下**优先顺序**做：

#### Step 1 · 写盘到项目目录（必做，主持久化通道）

在用户当前项目目录写入完整 JSON：

```
.spark/context/[skill-name].json
```

适用场景：所有支持文件系统的平台（IDE：Cursor / Claude Code / Qoderwork 等）。这是**默认主通道**——跨会话持久 + 多人协作可 commit 到 git 共享 + chat 干净。

#### Step 2 · 会话内输出"紧凑 marker"（必做，仅作为下游 Skill 的发现锚点）

⛔ **重要：写盘成功时，chat 内绝不输出完整 JSON**——只输出**紧凑形式**（含 `ref=` 属性指向已写盘的 JSON 文件）：

```
<!-- spark-context:[skill-name] ref=".spark/context/[skill-name].json" -->
[一行摘要：≤ 80 字，含项目名 + 2-3 个核心字段值]
<!-- /spark-context:[skill-name] -->
```

**紧凑形式示例**：

```
<!-- spark-context:brief ref=".spark/context/brief.json" -->
Brief 已保存：project=多 Agent 混合协作平台，persona=李楠，3 个 strategy_dimensions（信息架构 / 交互设计 / 视觉设计）
<!-- /spark-context:brief -->
```

#### Step 3 · 降级（仅当 Step 1 写盘失败）

如果检测到平台无文件系统访问（如 Cowork / Coderwork / Claude.ai 等纯对话场景），Step 1 写盘会失败——此时降级到**完整 JSON marker**：

```
<!-- spark-context:[skill-name] -->
{
  "skill": "[skill-name]",
  "generated_at": "ISO8601",
  ...完整 JSON...
}
<!-- /spark-context:[skill-name] -->
```

这是 chat-only 平台的唯一持久化通道。**优先级低于 Step 1 + 2**。

#### marker 格式约束（适用所有形式）

⛔ **marker 之间不得嵌套 ```json 代码块**：

- ✅ 正确（紧凑）：`<!-- spark-context:brief ref="..." -->\n[摘要]\n<!-- /spark-context:brief -->`
- ✅ 正确（降级完整）：`<!-- spark-context:brief -->\n{...裸 JSON...}\n<!-- /spark-context:brief -->`
- ❌ 错误：`<!-- spark-context:brief -->\n` + ` ```json ` + `\n{...}\n` + ` ``` ` + `\n<!-- /spark-context:brief -->`

原因：(1) 下游 Skill 用正则 `<!-- spark-context:[name](\s+ref="([^"]*)")?\s*-->\n([\s\S]*?)\n<!-- /spark-context:[name] -->` 抓取后处理；嵌套 ```json 会让捕获组带语言标签需二次清洗；(2) 三反引号代码块内展示该示例时，内层 ```json 会破坏 Markdown 嵌套层级。

#### 为什么这样设计

| 场景 | 行为 | chat 体验 |
| --- | --- | --- |
| IDE（QoderWork / Cursor / Claude Code） | Step 1 写盘 + Step 2 紧凑 marker | ✅ chat 干净，文件持久 |
| Chat-only 平台（Cowork / Claude.ai） | Step 1 失败 → Step 3 完整 JSON marker | ✅ 完整 JSON 在 chat 内可被下游解析 |

**核心原则**：chat 是用户看的（要干净），文件是 AI 看的（完整数据）。两者各司其职。

#### 执行顺序约束（v1.1.1，**强制**）

⛔ **Skill 完成产出时必须按以下顺序执行——不得颠倒**：

1. **先写盘**：调用 Write 工具把完整 JSON 写到 `.spark/context/[skill-name].json`
2. **输出自检行**：紧跟着在 chat 输出一行确认 `✅ [skill-name].json 已写盘到 .spark/context/[skill-name].json`（让用户和 AI 自己都能验证写盘动作真的发生了）
3. **渲染 Markdown 报告 / Persona Card / 其他可视化**（如有）
4. **输出紧凑 marker**（Step 2，ref 指向 Step 1 写的文件）
5. **Handoff 引导**
6. **更新链路面板**（v1.2 新增）：扫描 `.spark/context/*.json` 聚合最新 STATE，把 `_shared/dashboard-template.html` 克隆一份到 `.spark/dashboard.html`（覆盖更新），并把 STATE 注入到 `/*__SPARK_STATE_INJECT__*/null` 这个**单一注入点**。详见第九节「面板自动生成约定」。**面板生成失败不阻断 Skill 完成**（仅记录一条 warning），但应当在 Handoff 一并告知用户 `📊 链路面板已更新：.spark/dashboard.html`。

**为什么这个顺序是必须的**：经 OPC（2026-05-23）+ MuleTeam（2026-05-24）两次真实试用验证，**Phase X 最后才写盘**容易被 AI 跳过——尤其当 Phase X 同时要输出长 Markdown 报告 + Persona Card + Handoff 时，AI 注意力被前置的渲染内容吸走，写盘 step 被遗漏（已知 bug：MuleTeam 试用中 frame.json 唯独缺失，下游 11 个 Skill 全部正常写盘）。

**写盘失败时**：跳到 Step 3 降级形式（完整 JSON marker），同时在自检行明确告诉用户 `⚠️ 文件系统不可用，已降级为 chat-only marker`。**不允许静默跳过写盘步骤**。

#### JSON 内容安全规则（v1.2.1 新增，**强制**）

写入 `.spark/context/*.json` 时，**必须确保产出合法 JSON**。以下是已知的高频破坏源及处理方式：

| 源字符 | 处理方式 | 说明 |
| --- | --- | --- |
| `“` `”`（U+201C / U+201D 中文弯引号） | **替换为** `「` `」` | 最常见破坏源：AI 生成中文文案时自然携带的引号，写入 JSON 字符串后会被部分编辑器 / Write 工具存储为 ASCII `"`（0x22），导致 JSON 结构断裂 |
| `"`（ASCII 双引号，在字符串值内部出现） | **转义为** `\"` | 标准 JSON 转义规则 |
| 裸换行符（`\n` 未转义） | **转义为** `\\n` 或拆为数组 | JSON 字符串不允许跨行 |
| 反斜杠 `\`（非转义用途） | **转义为** `\\` | 避免意外转义后续字符 |

**自检规则**（Step 1 写盘后立即执行）：

```bash
python3 -c "import json; json.load(open('.spark/context/[skill-name].json'))"
```

解析失败时**不得跳过、不得继续后续步骤**——必须定位问题字符、修复后重新写盘，直到验证通过。

> **设立背景**：v0.5.8 测试（2026-06-08）中，Brief 写入的 `brief.json` 因 `business_context` 字段内含中文弯引号 `"看不懂数据"` 而导致 JSON 解析失败，下游 Dashboard 更新脚本崩溃、Journey Skill 读取失败，修了 6 次才修好。此规则防止同类问题再发。

#### 项目根路径锚定规则（v1.2.1 新增，**强制**）

`.spark/` 目录的父目录即为**项目根（Project Root）**。一旦首个 Skill 在某目录创建了 `.spark/context/`，后续本项目所有 Skill **必须**使用同一个 `.spark/` 路径——不得在子目录或其他位置另建 `.spark/`。

**锚定发现顺序**（每个 Skill 在 Step 0 / Step 1 执行前做）：

1. **向上查找**：从当前工作目录向上逐级查找含 `.spark/context/` 的目录（最多上溯 3 级）
2. **向下查找**：当前目录的直接子目录中是否有 `.spark/context/`（覆盖 monorepo / workspace 嵌套项目场景）
3. **找到即锚定**：后续所有 `.spark/` 操作（读 context、写 context、写产物、写 dashboard）都基于该已有 `.spark/` 的父目录
4. **找不到时创建**：在当前工作目录创建 `.spark/context/`——此目录即成为项目根

**禁止事项**：

- ❌ 同一项目出现多个 `.spark/context/` 实例（如果发现已有，必须复用而非新建）
- ❌ 不同 Skill 把 context 写到不同目录（会导致 Dashboard 状态丢失 + 下游 Skill 读不到上游产出）
- ❌ 未检测就直接在 cwd 创建 `.spark/`（必须先做发现步骤）

> **设立背景**：v0.5.8 测试中，Brief / Journey / Stories 在目录 A 创建了 `.spark/context/`，后续 Board → Retro 在目录 B 另建了 `.spark/context/`，导致 Dashboard 永远看不到前三个 Skill 的完成状态（显示 7/27 而非 10/27），Retro 也无法读到 Brief 做量化对照。

### 2.2 上游读取规则（智能适配版 · v1.1）

下游 Skill 在 Step 0 / Phase 0.5 按以下顺序尝试读取上下文：

1. **优先扫描当前会话** 是否含 `<!-- spark-context:[upstream] ...` marker。找到后判断 marker 形式：
   - **紧凑形式**（含 `ref="..."` 属性）→ 从该 ref 指向的文件读取完整 JSON
   - **完整形式**（无 ref）→ 直接解析 marker 内裸 JSON
2. **没有 marker 时检查文件** `.spark/context/[upstream].json` 是否存在，有则读取。
3. **都没有** 则跳过，按无上下文流程执行（不报错，不阻塞）。

**抓取正则**（参考实现）：

```regex
<!-- spark-context:(\w[\w-]*)(?:\s+ref="([^"]*)")?\s*-->\n([\s\S]*?)\n<!-- /spark-context:\1 -->
```

- 捕获组 1：skill-name
- 捕获组 2：ref 路径（如有；空则为紧凑形式但未指定 ref，需 fallback 到 `.spark/context/[name].json`）
- 捕获组 3：marker body（完整形式时是 JSON；紧凑形式时是摘要字符串）

**冲突处理**：会话 marker（紧凑形式 ref 指向文件）与同名文件直接存在时，**以 ref 指向的为准**（链路最新一致）。

**告知用户**：读到后告知 "检测到 [upstream] 上下文（来自 [文件 / 会话 marker]），已沿用以下字段：[字段列表]，可继续或修改。"

### 2.3 命名约定

- `[skill-name]` 全部小写，连字符分隔，如 `brief`、`flow-web`、`flow-mobile`、`frame`、`stories`、`check`。
- skill-name 必须与 SKILL.md frontmatter 的 `name` 字段一致。
- 不允许两个 Skill 写入同名 context（一个 skill-name 对应唯一 producer）。

---

## 三、SKILL.md 接入协议的方式

每个 Skill 的 SKILL.md 必须包含以下两部分：

### 3.1 frontmatter 中声明 chain 字段

```yaml
---
name: brief
description: ...
chain:
  reads: [frame, scope]        # 上游 skill 名数组，可空 []
  writes: brief                  # 本 skill 的 context 名（与 name 一致）
  schema:
    project_name: string
    project_type: string         # 详见下方字段词典
    business_goal: string
    user: string
    # ... 完整 schema 内联，不引用外部
---
```

### 3.2 SKILL.md 主体含 "Chain Context" 章节

紧跟 frontmatter 后，加一节标准内容（可整段抄写）：

```markdown
## Chain Context

### 上游读取（Step 0 / Phase 0.5 执行）

按以下顺序尝试读取上下文，找到即提取可复用字段并告知用户已沿用：

1. 扫描会话中的 `<!-- spark-context:[upstream] -->` marker
2. 读取项目目录 `.spark/context/[upstream].json`
3. 都没有则跳过，按无上下文流程执行

本 Skill 关注的上游 context：[列出 reads 中的 skill 名]

### 下游输出（Skill 完成时执行）

完成产出后，**同时**做以下两件事：

1. **会话内输出**：

   ```
   <!-- spark-context:[skill-name] -->
   {...JSON...}
   <!-- /spark-context:[skill-name] -->
   ```

2. **写入项目文件**：`.spark/context/[skill-name].json`

   若 `.spark/context/` 目录不存在，先创建。
```

---

## 四、字段词典（共享字段标准）

跨多个 Skill 使用的通用字段统一定义在此。**Skill 作者写自己的 schema 时，请直接复制对应字段定义贴进 SKILL.md frontmatter，不要自创变体。**

### 4.1 项目元字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `project_name` | string | 项目名 |
| `project_type` | enum | 见下方枚举值 |
| `project_subtype` | string | 子类型，详见 Brief Phase 1 |
| `business_context` | string | 业务背景，≤ 100 字 |
| `business_goal` | array<string> | 业务目标 / KPI，≤ 4 条，每条 ≤ 22 字 |
| `generated_at` | string | ISO 8601 时间戳 |
| `skill` | string | 产出本 context 的 skill-name |

`project_type` 枚举值（与 Brief 一致）：

```
"产品设计" | "营销与传播" | "品牌设计" | "研究与评估" | "系统与资产" | "特殊介质" | "管理类"
```

### 4.2 用户字段

```yaml
user: array<string>              # 主要受众 + 核心使用场景，≤ 4 条，每条 ≤ 25 字
```

更详细的人物锚点（Frame 用研类 Skill 输出，下游可读取并降维使用）：

```yaml
# Frame 输出的完整 persona（含 7 个字段）
persona:
  name: string                   # 真实姓名
  description: string            # 一句话描述（年龄/职业/关键场景特征）
  situation: string              # 问题发生的情境
  goal: string                   # 想达成什么
  workaround: string             # 当前怎么解决
  frustrations: array<string>    # 痛点
  what_good_looks_like: string   # "搞定"对他/她长什么样
```

JTBD 句式（独立字段，配合 persona 使用）：

```yaml
jtbd: string                     # 当 [situation]，[name] 想 [motivation]，从而 [outcome]。
```

Stories 输出的简化 persona（subset of Frame's persona + jtbd 直接内嵌）：

```yaml
# Stories 内嵌的简化 persona（3 字段）
persona:
  name: string
  description: string
  jtbd: string
```

**降维规则**：下游 Skill（Brief、Flow Web/Mobile）从 Frame.persona 读取时，可只取 `name + description + situation + goal` 等所需子集；要写入自己的字段（如 Brief.user）时，可以串联为单字符串："[description]，在 [situation] 想 [goal]"。

### 4.3 设计策略字段（Brief 主输出）

```yaml
strategy_dimensions:
  - dimension: string            # 维度名（信息架构 / 交互设计 / 视觉设计 等）
    thesis: string               # 主张，≤ 22 字
    tactics: array<string>       # 手法，2–3 条，每条 ≤ 16 字
    rationale: string            # 依据，≤ 25 字，可空
```

### 4.4 设计标准字段

```yaml
design_criteria:
  quantitative: array<string>    # 定量标准
  qualitative: array<string>     # 定性标准
```

### 4.5 约束字段

```yaml
constraints: array<string>       # 边界约束
out_of_scope: array<string>      # 不做什么
```

### 4.6 视觉字段（Brief 视觉输出）

```yaml
style: string                    # chalk / parchment / script / noir / frame / onyx / stone / slate / terminal
ratio: enum                      # "16-9" | "4-3" | "1-1"
scale: enum                      # "sm" | "md" | "lg"
```

### 4.7 机会点字段（Frame / HMW 输出）

```yaml
opportunities:
  - title: string                # 机会点标题
    problem: string              # 对应的问题
    hmw: string                  # How Might We 句式
    priority: enum               # "high" | "medium" | "low"
```

### 4.8 用户故事字段（Stories 输出）

```yaml
stories:
  - title: string                # 故事标题
    persona: string              # 关联人群锚点
    scenario: string             # 使用场景
    acceptance_criteria: array<string>   # 可观察的验收标准
    risk: string                 # 风险或假设
    priority: enum               # "p0" | "p1" | "p2"
```

### 4.9 走查发现字段（Check 输出）

```yaml
findings:
  - category: enum               # 见下方 10 个 enum 值；JSON 用英文，Markdown 报告本地化
    severity: enum               # "blocker" | "major" | "minor"
    description: string          # 问题描述
    suggestion: string           # 修复建议
    location: string             # 出现位置（页面 / 组件）
```

`category` 枚举值（与 Check Skill 一致）：

```
"flow-continuity"   # 链路通畅性
"ia"                # 信息架构
"components"        # 组件使用
"visual-hierarchy"  # 视觉层级
"edge-states"       # 异常态覆盖
"copy"              # 内容文案
"responsive"        # 响应式 / 多端
"feedback"          # 反馈与交互
"accessibility"     # 无障碍基础
"brief-consistency" # 与 Brief 一致性
```

### 4.10 设计 Token 字段（Board 输出）

```yaml
# Board.color
color:
  primary: string                  # 主色 hex（如 #7C4DFF）
  secondary: string                # 辅色 hex
  neutral: object                  # { "50":"#F9FAFB","100":"...","500":"...","900":"..." }

# Board.typography
typography:
  heading_font: string             # 标题字体名（如 Space Grotesk）
  body_font: string                # 正文字体名（如 Inter）

# Board.spacing / radius（设计系统基础尺度）
spacing: object                    # { xs/sm/md/lg/xl: "4px"~"32px" }
radius: object                     # { sm/md/lg/xl/full: "4px"~"9999px" }

# Board.component（4 类核心组件 token，下游 flow-web/mobile 直接落地）
component:
  button: object                   # { bg, color, padding, font_size }
  input: object                    # { border, bg, width }
  card: object                     # { border, padding, max_width }
  tag: object                      # { bg, color, font_size }

# Board.style_keywords（驱动 motion-plan archetype）
style_keywords: array<string>      # 4 个关键词（如 ["内敛","专业","可信","温润"]）

# Board.touchpoints（触点级 override，对接 journey）
touchpoints:
  - id: number
    name: string
    emotions: array<string>
    override:
      color: object                # 该触点局部覆写颜色
```

**降维规则**：下游 flow-web / flow-mobile 读取时通常只需 `color.primary + color.secondary + component.button + component.card`；motion-plan 主要消费 `typography + style_keywords`；chart 主要消费 `color.primary + color.secondary`。

---

## 五、链路全景图

> 手维护，新增 Skill 时同步更新。

```
01 Explore
  Frame ─────────┐  ✅
  Scope ─────────┤  ✅
  Audit ─────────┤  ✅ NEW
                 │
02 Define        ▼
  Journey ──→ Brief ────┐  ✅ NEW（HTML 用户体验地图）
  HMW ── (已并入 Frame Phase 3.5)
  Stories ──────────────┤
  Board ────────────────┤  ✅ NEW（视觉情绪板 / design-tokens 起点）
  Sitemap ──────────────┤
                        ▼
03 Design       ┌── Flow Web      ✅
                ├── Flow Mobile   ✅
                ├── Edge          ✅ NEW（异常态专项）
                ├── Pitch         ✅ NEW（给决策者）
                ├── Landing
                ├── Campaign
                ├── Chart
                ├── Avatar        ✅
                ├── Motion        ✅ NEW（动效规划 / motion-plan）
                └── Motion Apply  ✅ NEW（动效开发 / motion-apply，链式读 motion-plan）
                        │
04 Validate             ▼
  Check ←──── (设计产物 + Brief)  ✅
  Access ←─── (Brief + Flow + Check; WCAG 2.1 AA/AAA)  ✅ NEW
  Metric ←─── (Brief + Stories + Pitch)  ✅
  Test
                        │
05 Deliver              ▼
  PRD ←──── (Brief + Stories + Sitemap + Flow Web/Mobile + Frame + Check)  ✅ 已实现
  QA ←───── (Brief + Flow Web/Mobile + Check)  ✅ 已实现
  Retro ←── (吃满全链 19 Skill，链路终端闭环)  ✅ NEW
  Extract（未实现）
```

**Brief 是核心锚点**：01 阶段产出汇聚到 Brief，03/04/05 阶段从 Brief 读取上下文。

---

## 六、版本与兼容性

- 协议版本：`v1.0`（2026-05-22）
- Skill 在 frontmatter `chain` 字段下可加 `protocol_version: "1.0"` 显式声明遵循的协议版本
- 协议升级（破坏性变更）时，老版本 Skill 仍能产出 v1.0 context，新版本 Skill 应能向下兼容读取 v1.0
- 字段词典追加新字段不算破坏性变更；修改已有字段类型 / 枚举值算破坏性变更

---

## 七、新 Skill 接入清单

写新 Skill 时按以下顺序：

- [ ] 在 SKILL.md frontmatter 加 `chain.reads / writes / schema` 字段
- [ ] 复制粘贴第三节的 "Chain Context" 章节模板到 SKILL.md 主体（替换占位符）
- [ ] schema 中字段优先复用第四节字段词典；自创字段需说明
- [ ] 在 Skill 流程的 Step 0 / Phase 0 实现"上游读取"逻辑
- [ ] 在 Skill 流程的最后一步实现"双通道下游输出"——**强制按 §2.1 Step 1→6 顺序**（先写盘、再 marker、再 Handoff、最后刷新链路面板）
- [ ] **加入「字段流向下游」段**（v0.5.0 新增）：在 Chain Context 章节末尾说明本 Skill 的关键字段如何被下游 Skill 消费，使用 `skill.field[]` → 下游 Skill 用途 的可机读语法（参考 frame / scope / audit / brief 等范本）
- [ ] **加入「更新链路面板」段**（v0.5.1 新增）：在 Step 6 写明扫 `.spark/context/*.json` → 克隆 `_shared/dashboard-template.html` 到 `.spark/dashboard.html` → 注入 STATE → Handoff 告知用户。详见第九节
- [ ] 更新本文件第五节链路全景图，把新 Skill 标上去
- [ ] **加入"能力矩阵 / 输入要求 / 质量规范"三段式标准章节**（详见第八节）
- [ ] 跑 `python3 dist/validate-chain.py` 校验 reads/writes 一致性，必须通过才能打包

---

## 八、SKILL.md 标准章节三段式（v1.2 强制规范）

> **设立背景**：对标 QoderWork 官方技能套件后，发现我们的约束散落各处、信息完整度判断隐含在自然语言里、用户感知不到"独立 vs 链式"差异。三段式标准化是 v1.2 必须接入的规范。**Brief 已作为样板完成改造，新 Skill 必须遵循；存量 16 个 Skill 按需补齐。**

### 8.1 能力矩阵（放 SKILL.md 开篇，紧跟一句话简介后）

显式标注 Skill 的运行模式分层，让用户和 AI 都能立即理解"装了什么会得到什么"。

**标准模板**：

```markdown
## 能力矩阵

本 Skill 的三种运行模式，可单独运行也可叠加。最常见路径：[填本 Skill 最常见的触发路径]。

| 模式 | 触发条件 | 产出特征 |
| --- | --- | --- |
| 🟢 **独立模式** | 无前序上下文，直接调用 | [描述无上游时的产出形态] |
| 🔵 **链式模式** | 检测到 `.spark/context/[上游 skill].json` | [描述有上游时跳过哪些步骤] |
| 🟣 **增强模式** | [可选：装了 SparkDesign / Figma MCP / 其他集成时] | [描述产出形态的增强部分] |

> 说明本 Skill 三种模式下产出物的差异（或一致性）。
```

**规则**：
- 独立 / 链式两栏**必填**；增强栏**可选**（无明确增强场景时可省略行）
- 触发条件要给具体文件名 / marker 名，不要写"如有"这种模糊词
- 产出特征要描述"差异点"，不是重复 Skill 整体说明

### 8.2 输入要求表（放能力矩阵下方）

把"信息完整度判断"从自然语言固化为结构化表格，提升 AI 执行的稳定性和确定性。

**标准模板**：

```markdown
## 输入要求

| 输入项 | 必填？ | 来源优先级 | 缺失时行为 |
| --- | --- | --- | --- |
| `[字段名]` | ✅ / ⭕ | [链式上游字段] > 用户输入 | [追问 / 标注未提供 / 取默认值] |
| ... | ... | ... | ... |

**信息完整度判断**：必填项任一缺失 → [Skill 特定的引导追问行为]；仅可选项缺失 → [Skill 特定的降级行为]。
```

**规则**：
- ✅ = 必填（缺失阻断执行）；⭕ = 可选（缺失不阻断，标注或取默认值）
- "来源优先级"用 `>` 表示降级顺序，例如 `链式 frame.persona > 链式 scope.target_users > 用户输入`
- "缺失时行为"要写**具体动作**（"Phase 3 追问" / "取默认值 chalk"），不要写"提示用户"这种模糊词
- 字段名必须与 frontmatter `chain.schema` 中的字段名完全一致

### 8.3 质量规范三段式（放 SKILL.md 文末，作为收口判断）

把散落在 Phase 各处的约束**集中收口**为高层判定标准，与 Phase 内部的执行级约束互补。

**标准模板**：

```markdown
## 质量规范

> 本章节是 Skill 完成度的**高层判定标准**，与 Phase X 内部的执行级约束互补。Phase X 是"该怎么做"，本章节是"做对了没有"。

### 🚫 红线规则（违反即任务失败，无降级空间）

- [硬约束 1：违反就失败的最强规则，比如"必须基于模板克隆"]
- [硬约束 2：双通道输出是否符合 chain-protocol §2.1]
- [硬约束 3：核心 DOM / 字段结构是否符合规范]
- ...

### ⚠️ 反模式（常见错误，需主动规避）

- ❌ [常见错误 1：实际执行中已观察到的偏差]
- ❌ [常见错误 2：容易混淆的概念辨析]
- ❌ [常见错误 3：跳步 / 顺序颠倒 / 漏环节]
- ...

### ✅ 质量标准（通过条件，全部满足才算交付）

**内容完整性**：
- [字段完整度判断]
- [字数 / 数量约束]

**[产物类型] 完整性**：
- [文件大小 / 结构 / 关键 DOM 等可量化标准]
- [自检清单是否通过]

**链路接入正确性**：
- `.spark/context/[skill].json` 文件已写入且 schema 符合 frontmatter 定义
- chat marker 含 `ref=` 属性
- 下游 Skill 调用时能正确读取本 Skill 上下文
- 已输出符合 Phase 7 Handoff 模板的下一步建议
```

**规则**：
- 红线规则数量 5-8 条，太多会失去"红线"的严肃感
- 反模式必须基于**实际观察到的错误**（OPC / MuleTeam 等真实试用反馈），不要凭想象写
- 质量标准分 3 大类：**内容完整性 / 产物完整性 / 链路接入正确性**——前两类 Skill 特定，第三类所有 Skill 通用

### 8.4 接入优先级

| Skill 类型 | 接入要求 |
| --- | --- |
| **新写的 Skill**（v1.2 后） | 必须包含三段式，否则不算完成 |
| **核心节点 Skill**（Brief / Stories / Flow Web / Flow Mobile / Check / PRD） | 高优先级补齐，影响下游链路稳定性 |
| **其他存量 Skill** | 按需补齐，不强制 |

**样板参考**：[Brief SKILL.md](./2-Define/Brief/SKILL.md) 是 v1.2 三段式的首个完整样板。

---

## 九、面板自动生成约定（v1.2 新增）

> **设立背景**：20 个 Skill 串成链路，但用户在 chat 里看不到"我现在跑到哪了 / 还差什么 / 下一步该做哪个"。借助 QoderWork 已支持的"本地 HTML 文件预览"能力，每个 Skill 完成时刷新一份 `.spark/dashboard.html`——五阶段链路全景视图，让用户一眼看清当前位置。**不新增 slash 命令**，避免增加用户认知负担。

### 9.1 模板与单注入点

模板路径（套件内）：`_shared/dashboard-template.html`

模板中含且仅含**一个注入点**，用注释包裹便于正则定位：

```js
const STATE = /*__SPARK_STATE_INJECT__*/null;
```

生成时把 `null` 替换为序列化后的 STATE JSON（保留前后注释包裹），不要改动模板其他部分。这种「单注入点 + 注释守卫」的模式避免大段字符串替换的脆弱性，模板可以独立预览（STATE 为 null 时显示"未注入"占位）。

### 9.2 STATE schema

```json
{
  "project": "项目名（取 brief.project_name 或 frame.project_name；都没有时取 .spark/ 所在目录名）",
  "description": "项目一句话简述（≤ 60 字，可选）",
  "generated_at": "ISO8601",
  "contexts": {
    "<skill-name>": {
      "done": true,
      "summary": "≤ 40 字摘要（取 Skill 自己输出的紧凑 marker 摘要）",
      "fields": { "可选字段...": "..." }
    }
  }
}
```

`contexts` 的 key 必须是 `chain.writes` 中的 skill-name；只列出**已完成**的 Skill（done: true）。未完成的 Skill 模板侧会自动渲染为「先做 /xxx」灰态。

### 9.3 生成流程（Skill 完成时的 Step 6 展开）

> **v1.3 变更**：从「只扫重建」改为「读旧合并 + 扫新覆盖」。旧协议在工作目录变更（如 flow-web Phase A 新建工程目录）时，扫不到旧目录的 context 文件，导致已完成的 Skill 从面板上消失。新协议先读已有面板的 STATE 作为基线，再用当前目录的 context 文件覆盖，保证历史状态不丢。

1. 检查 `_shared/dashboard-template.html` 是否存在（套件分发时会带）。找不到则跳过本步并打 warning。
2. **读取已有 STATE（基线）**：若 `.spark/dashboard.html` 已存在，用正则 `/\/\*__SPARK_STATE_INJECT__\*\/(.*?);/` 提取当前 STATE JSON，解析其 `contexts` 作为 `old_contexts`。读取失败或文件不存在则 `old_contexts = {}`。
3. **扫描当前 context 文件**：遍历 `.spark/context/*.json`，聚合 `new_contexts`：
   - `project / description` 优先级：`brief.project_name` > `frame.project_name` > `scope.project_name` > 目录名
   - `new_contexts[name] = { done: true, summary: <从该 JSON 顶层 summary 字段或前 40 字截取>, fields: <可选挑几个核心字段> }`
4. **合并**：`merged_contexts = { ...old_contexts, ...new_contexts }`（新覆盖旧，保留旧里有但新目录没文件的 Skill）。
5. 用 `merged_contexts` 构造完整 STATE JSON。
6. 把**模板**（不是已有 dashboard）克隆到 `.spark/dashboard.html`（覆盖）。
7. 用正则 `/\/\*__SPARK_STATE_INJECT__\*\/null/` 替换为 `/*__SPARK_STATE_INJECT__*/<JSON.stringify(STATE)>`。
8. 写盘成功后在 Handoff 输出一行：`📊 链路面板已更新 · 进度 N/28 · .spark/dashboard.html`

#### 9.3.1 参考实现（Python）

> AI 生成 Step 6 代码时**必须遵循此模式**，不得自行编写 ad-hoc 脚本。可以用 Python 或 Node.js，但合并逻辑必须一致。

```python
import os, json, re, glob

# ── 1. 读模板 ──
tpl_path = os.path.expanduser(
    '~/.qoderwork/plugins-custom/product-design/_shared/dashboard-template.html')
if not os.path.exists(tpl_path):
    print('⚠️ dashboard-template.html not found, skip'); exit(0)
with open(tpl_path, 'r', encoding='utf-8') as f:
    template = f.read()

# ── 2. 读旧 STATE（基线） ──
old_contexts = {}
dash_path = '.spark/dashboard.html'
if os.path.exists(dash_path):
    with open(dash_path, 'r', encoding='utf-8') as f:
        old_html = f.read()
    m = re.search(r'/\*__SPARK_STATE_INJECT__\*/(.*?);', old_html, re.DOTALL)
    if m:
        try:
            old_state = json.loads(m.group(1))
            old_contexts = old_state.get('contexts', {})
        except json.JSONDecodeError:
            pass  # 解析失败则从空开始

# ── 3. 扫当前 context 文件 ──
new_contexts = {}
for fp in sorted(glob.glob('.spark/context/*.json')):
    try:
        with open(fp, 'r', encoding='utf-8') as f:
            data = json.load(f)
        name = data.get('skill') or os.path.splitext(os.path.basename(fp))[0]
        summary = data.get('summary', '')[:80]
        new_contexts[name] = {'done': True, 'summary': summary, 'fields': {}}
    except Exception as e:
        print(f'⚠️ skip {fp}: {e}')

# ── 4. 合并（新覆盖旧） ──
merged = {**old_contexts, **new_contexts}

# ── 5. 构造 STATE ──
# project/description 优先级：brief > frame > scope > 目录名
project_name = None
for key in ['brief', 'frame', 'scope']:
    ctx_file = f'.spark/context/{key}.json'
    if os.path.exists(ctx_file):
        try:
            with open(ctx_file, 'r', encoding='utf-8') as f:
                d = json.load(f)
            project_name = d.get('project_name') or d.get('project')
            if project_name:
                break
        except Exception:
            pass
if not project_name:
    project_name = os.path.basename(os.getcwd())

from datetime import datetime, timezone
state = {
    'project': project_name,
    'generated_at': datetime.now(timezone.utc).isoformat(),
    'contexts': merged
}

# ── 6-7. 注入模板并写盘 ──
result = template.replace(
    '/*__SPARK_STATE_INJECT__*/null',
    '/*__SPARK_STATE_INJECT__*/' + json.dumps(state, ensure_ascii=False))
os.makedirs(os.path.dirname(dash_path) or '.', exist_ok=True)
with open(dash_path, 'w', encoding='utf-8') as f:
    f.write(result)
print(f'✅ Dashboard updated: {len(merged)}/{28} contexts')
```

> **禁止变体**：① 不得直接字符串编辑已有 dashboard.html 的 STATE 行（脆弱，依赖精确匹配）。② 不得跳过「读旧合并」步骤直接从 context 文件重建（会丢失跨目录历史）。③ `project_name` 不得硬编码，必须从 context 文件提取。

### 9.4 首次生成时机（AI 行为守则）

第一次面板生成**不等任何 Skill 跑完也可以做**——AI 在以下两种时机判断后主动生成一份「空状态」面板：

- **场景 A**：用户已经明确说出项目方向（"我想做一个 X 平台" / "PM 给我了一份 PRD" / "改版 Y 产品"），且距离即将触发的第一个 Skill 还有 ≥ 1 轮对话。
- **场景 B**：用户已经触发了任意一个 Skill 的 Step 0（识别项目类型 / 读取上游），但还没完成产出。

判定要点：**面板是引导工具，不是产物**——宁可早生成一份空面板让用户看清完整链路，也不要等跑完才给。空面板的 `contexts` 为空对象 `{}`，模板会全部渲染为"先做 /xxx"灰态，依然能传达"接下来要走哪 20 步"。

### 9.5 不做什么

- ❌ **不新增 slash 命令**（不要 `/dashboard` / `/状态` 之类）
- ❌ **不强制每个 Skill 写入完整 fields**（只要 summary 即可，fields 是 nice-to-have）
- ❌ **不在 chat 里嵌入完整 HTML**（用户用文件预览能力打开 `.spark/dashboard.html`）
- ❌ **不阻断 Skill 完成**（面板生成失败只打 warning，Skill 仍报完成）
