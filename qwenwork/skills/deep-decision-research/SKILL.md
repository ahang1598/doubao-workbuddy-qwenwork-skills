---
name: deep-decision-research
description: 主动触发型技能；仅当用户显式选择或明确调用本技能时使用。用于让 QoderWork 围绕一个明确决策目标搜索、研究、整理材料，并按内置 HTML 报告规范生成一份可在浏览器打开的自包含决策辅助报告。
install_source: official
install_method: download
skill_id: official_hn7Z3AOW
enabled_at: 1791893741262
version: 1.0.0
name_zh: 深度决策研究报告
---

# Deep Decision Research

## 核心定位

本 skill 当前是**QoderWork 研究 + 本地 HTML 决策报告生成器**。

它不依赖外部后端服务，不启动后台异步任务，不等待远程回调。QoderWork 先判断任务深度，再读取用户材料、按需搜索、整理证据和缺口，最后根据内置报告规范生成一个完整 HTML 文件。

目标：

```text
围绕一个明确决策目标，
让 QoderWork 完成搜索研究、材料整理和结构化判断，
最后按固定 HTML 报告规范一次性写出可汇报的漂亮报告文件。
```

## 运行深度选择

本 skill 必须先判断报告深度，再进入节点 B。不要把所有任务都当成深度研究任务。

```text
light：轻量决策报告
standard：标准决策报告
deep：深度研究报告
```

### light 模式

触发条件：

- 用户明确说“轻量、简单、不要太 deep、不要深度研究、快速判断、基于给定材料即可、不要搜索”。
- 任务材料已经给出，且用户只需要一个可读 HTML 决策报告。
- 评测或批处理场景要求控制耗时、token 或稳定性。

执行要求：

- 默认不做网页搜索；除非用户明确要求搜索。
- 主要基于用户材料和稳定通用常识。
- 研究计划控制在 2-4 个信息问题。
- 证据 2-4 条即可，可使用 `user_provided`、`estimated`、`uncertain`。
- 风险 2-4 条，假设/信息缺口 2-4 条，行动 3-5 条。
- HTML 目标长度 120-260 行；不要追求长报告。
- 写入完整 HTML 后，只做一次结构检查；如果已有 `<!DOCTYPE html>` 和 `</html>`，立即进入节点 D，不要删除、重写或清理临时文件。

### standard 模式

默认模式。适用于用户要求“完整报告/方案对比/可汇报”但没有明确要求深度行业研究。

- 允许 0-3 次搜索；用户材料足够时不搜索。
- 证据 4-6 条，风险 3-5 条，假设 3-5 条。
- HTML 目标长度 260-600 行。

### deep 模式

只有用户明确要求“深度研究、详细调研、全面分析、行业研究、竞品研究、尽可能完整”，或高风险复杂决策确实需要外部资料时启用。

- 用户显式要求 `deep`、深度研究、全面调研、行业/竞品系统分析、尽可能完整时，必须设置 `report_depth=deep`，不得降级为 `light` 或 `standard`。
- 允许 4-8 次搜索/工具查询。
- 使用完整研究材料包和完整 7 模块报告。
- HTML 可以较长，但仍必须一次性写入完整文件。

## 记忆策略

本 skill 以无记忆模式运行。

当本 skill 激活时：

- 不调用 `mcp__qw-builtin__memory` 或任何记忆相关工具。
- 不读取或更新 `USER.md`、`AGENTS.md`、`SOUL.md`、`MEMORY.md`、`memory/*.md`，除非用户明确要求本 skill 检查这些文件。
- 不依赖已记住的用户偏好、global profile、global soul、历史项目记忆或历史会话摘要。
- 如果 prompt 中已经注入了记忆上下文，本 skill 忽略它。
- 只使用当前用户请求、用户明确提供的输入、本轮检查过的文件，以及稳定通用知识。
- 本 skill 执行期间产生的信息不写入记忆。

## 固定执行节点

QoderWork 只按下面 4 个节点执行。每个节点只做写明的动作，下一步按节点 Map 进入。

```text
节点 A：确认目标
输入：用户原话
动作：最多追问 2 个问题；整理报告目标
产出：报告目标文本
下一步：节点 B

节点 B：准备材料
输入：报告目标、用户材料
动作：先确定 light/standard/deep 深度；制定相应研究计划；按需做搜索/工具查询；抽取证据；生成并验收研究材料包
产出：研究材料包文本
下一步：节点 C

节点 C：生成 HTML 报告
输入：报告目标、研究材料包、内置 HTML 报告规范
动作：读取 `~/.qwenworkcn/skills/deep-decision-research/references/decision-report-prompt-spec.md`；按深度提炼合规清单；一次性写入完整 HTML 文件；轻量模式只做一次结构检查，标准/深度模式按清单自检并必要时修正
产出：outputs/deep-decision-research/<run_id>/<topic>-decision-report.html
下一步：节点 D

节点 D：交付结果
输入：HTML 文件路径
动作：给用户一句话结论、关键依据、主要风险和 HTML 文件路径
产出：最终用户回复
```

## 关键规范入口

生成 HTML 前，节点 C 读取：

```text
~/.qwenworkcn/skills/deep-decision-research/references/decision-report-prompt-spec.md
```

这份文件是唯一报告规范来源。QoderWork 先按“运行深度选择”确定 light/standard/deep，再按其中对应要求生成报告：

- 输出一个完整、自包含、可直接在浏览器打开的 HTML 文件。
- HTML 必须包含完整 `<!DOCTYPE html>`、`<html>`、`<head>`、单一 `<style>`、`<body>` 结构。
- 所有 CSS 写在 `<head>` 的单一 `<style>` 块里。
- standard/deep 报告必须包含 7 个模块，顺序固定：
  1. 决策摘要
  2. 推荐方案
  3. 多维对比矩阵
  4. 证据支撑
  5. 风险登记册
  6. 假设清单
  7. 行动建议
- light 报告可以合并或简化模块，但必须包含：决策摘要、方案对比、主要理由、风险与信息缺口、下一步行动、免责声明。
- 文件一次性完整写入，不分段 append。

重要：这份规范不是“参考样式”，而是节点 C 的执行合同。但合同必须按深度执行；light 模式不应套用 deep 模式的搜索量、证据数量和长报告要求。

节点 C 开始前，先从规范中提炼一份内部合规清单，至少覆盖：

- HTML 完整结构、单一 `<style>`、一次性写入。
- 深色 Header、标题、副标题、4 个 KPI 横条，KPI 数字使用等宽字体。
- `:root` 中声明规范要求的 CSS 变量。
- 7 个必选模块按固定顺序出现。
- 每个模块使用明确的 section 视觉系统：编号、标题、容器、卡片。
- 首选方案高亮、多维对比矩阵颜色编码。
- 证据数量、风险数量、假设数量、行动步骤数量满足规范下限。
- 风险项左侧有红/橙/绿竖条。
- 页脚免责声明完整。
- 信息层次完整：每个模块都要有“结论/判断 -> 证据/数据 -> 影响/含义 -> 行动/边界”的展开，不得只堆事实或只写建议。
- 信息密度足够：报告要像可交付研究报告，而不是对话摘要；优先使用多卡片、多表格、多层级说明承载信息。
- 渐进式披露清晰：先展示结论和关键 KPI，再展示方案理由，最后展开证据、风险、假设和行动细节。

如果任一项无法满足，节点 C 继续修正 HTML，不进入节点 D。

## 使用前提

只有用户显式选择或明确调用本技能时使用。

适合：

- 用户希望生成一份可汇报的决策 HTML 报告。
- 任务属于方案推荐、可行性分析、风险评估、项目规划、多方案对比。
- 用户提供了材料，或允许 QoderWork 做搜索、工具查询和材料研究。

不适合：

- 简单事实问答。
- 一句话建议。
- 不需要报告文件的轻量任务。

## 节点 A：确认目标

节点 A 把用户问题压成一个报告目标。

报告目标包含：

```text
报告标题：
用户要解决的核心决策：
目标读者：
使用场景：
候选方案：
时间范围：
地域/平台范围：
已知约束：
```

如果用户问题太泛，QoderWork 最多追问 2 个问题，用来确定报告目标；之后进入节点 B。

优先追问：

1. 你希望最终报告解决哪个核心决策？
2. 有哪些候选方案、范围、约束或已有材料？

用户要求直接开始时，用合理默认假设进入节点 B，并在报告的假设清单中写明。

## 节点 B：搜索研究与材料整理

节点 B 是研究阶段。QoderWork 要先按运行深度决定材料整理强度，再读取材料、按需搜索、整理证据，最后进入节点 C 生成报告。

节点 B 不是可选前置，也不是搜索摘要。没有完成与当前深度匹配的材料包，不得进入节点 C 写 HTML。

节点 B 固定拆成 4 步，但每步规模由运行深度决定：

```text
B0 深度选择：确定 light / standard / deep。
B1 研究计划：light 2-4 个信息问题；standard 3-5 个；deep 4-8 个。
B2 搜索执行：light 默认不搜索；standard 0-3 次；deep 4-8 次。
B3 证据抽取：从材料中抽取 KPI、候选方案、证据、风险、假设、行动和缺口。
B4 材料包验收：检查材料包是否足以支撑 HTML 报告；不足则补搜或标记缺口。
```

### B0 深度选择

先根据用户请求写下内部变量 `report_depth`：

```text
report_depth = light | standard | deep
```

选择规则：

- 明确出现“轻量、简单、不要太 deep、快速、少量、不需要深度研究、不要搜索、基于给定材料”等表达时，必须选 `light`。
- 用户没有指定深度，但只给了一个清晰小决策和少量材料时，默认选 `light` 或 `standard`，不得直接进入 `deep`。
- 只有用户明确要求深度研究、全面调研、竞品/行业/市场系统分析，或任务天然高风险且缺乏关键资料时，才选 `deep`。
- 如果用户同时表达“深度/全面/竞品/行业研究”和“可控制篇幅/不要太长”，仍然选择 `deep`，但可以压缩 HTML 篇幅；不得把深度研究意图误判为 `light`。

后续节点 B/C/D 都必须遵守 `report_depth`。用户要求轻量时，不能因为规范里有 deep 模式下限而偷偷升级。

### B1 研究计划

进入搜索前，先生成内部研究计划，不输出给用户。研究计划必须覆盖：

```text
1. 市场/行业规模或趋势问题
2. 用户决策目标相关的候选方案问题
3. 关键成本、收益、效率或增长指标问题
4. 用户/客户/消费者行为问题
5. 供应链、执行可行性或资源约束问题
6. 竞争、替代方案或平台规则问题
7. 风险、合规、失败案例问题
8. 信息缺口和需要用户补充的问题
```

不是所有任务都需要 8 个问题。light 模式 2-4 个即可；standard 模式 3-5 个；deep 模式至少 4 个。每个信息问题都要能服务最终报告中的某个模块。

### B2 搜索执行

研究动作只做这 6 类：

- 使用 QoderWork 自带的 WebSearch 能力搜索公开资料。
- 使用 QoderWork 已有工具获取可用信息。
- 读取用户上传的文档、表格、截图、网页内容。
- 使用多模态能力理解用户提供的后台截图或报告截图。
- 请求用户补充关键材料。
- 将材料提炼成候选方案、证据、风险、假设、行动建议和已知缺口。

搜索不是默认动作，而是按深度和材料缺口决定：

```text
light：默认 0 次搜索。用户明确要求不搜索时，禁止搜索。
standard：用户材料足够时 0 次搜索；需要补充常识或时效信息时 1-3 次。
deep：需要系统研究时 4-8 次搜索/工具查询。
```

用户明确要求不搜索时，直接整理用户材料，并把无法验证的信息写入 `known_gap`。不得为了凑证据数量而搜索。

搜索查询必须有分工，不要只换同义词重复搜索。建议至少覆盖：

```text
1. 行业/市场规模/趋势
2. 价格/成本/利润/ROI
3. 用户/消费者/客户行为
4. 竞品/替代方案/标杆案例
5. 风险/合规/失败案例
6. 执行路径/供应链/工具/渠道
```

所有材料按下面方式记录：

```text
公开搜索结果 -> sourceLayer=L1_public_search
第三方授权/购买/合作数据 -> sourceLayer=L2_third_party
用户上传/截图/后台导出/对话补充 -> sourceLayer=L3_user_owned
拿不到的数据 -> known_gap
```

### B3 证据抽取

每条材料不得只写摘要，必须抽取成结构化证据。证据字段如下：

```text
evidenceId:
sourceLayer: L1_public_search | L2_third_party | L3_user_owned
sourceName:
sourceUrl:
sourceTime:
evidenceType: verified | estimated | user_provided | uncertain
claim:
specificFactOrNumber:
decisionMeaning:
supportsModule: kpi | recommendation | matrix | evidence | risk | assumption | action
confidence: high | medium | low
limitation:
```

字段要求：

- `claim` 是这条证据支撑的判断。
- `specificFactOrNumber` 必须尽量包含数字、事实、案例、时间或来源；没有具体事实就不要当作强证据。
- `decisionMeaning` 必须回答“这条证据对用户决策意味着什么”。
- `limitation` 写明数据限制，例如来源间接、时间较旧、样本不明、只适用于某平台。

严禁把无法验证的泛泛说法写成已验证证据。拿不到数据时写入 `known_gap`。

研究材料包格式：

```text
一、报告目标
<节点 A 的报告目标>

二、用户原始问题
<用户原话>

三、候选方案
方案 1：
name:
positioning:
targetUser:
priceOrCostRange:
pros:
cons:
bestFor:
switchCondition:

方案 2：
...

四、Header KPI 候选
KPI 1：
label:
value:
explanation:
sourceEvidenceId:
confidence:

五、结构化证据
证据 1：
evidenceId:
sourceLayer:
sourceName:
sourceUrl:
sourceTime:
evidenceType:
claim:
specificFactOrNumber:
decisionMeaning:
supportsModule:
confidence: high | medium | low
limitation:

六、风险清单
风险 1：
title:
level: high | medium | low
probabilityImpact:
mechanism:
impactDimensions:
mitigation:
sourceEvidenceId:

七、关键假设
假设 1：
assumption:
ifNotTrue:
affectedConclusion:

八、行动建议
行动 1：
title:
ownerOrObject:
details:
timebox:
acceptanceMetric:

九、已知缺口
<哪些数据没有拿到，以及对结论的影响>

十、报告生成要点
推荐倾向：
核心证据：
主要风险：
关键假设：
建议行动：
```

### 节点 B 的信息密度要求

节点 B 不是简单搜索摘要，而是为报告准备可展开的研究材料。进入节点 C 前，研究材料包必须达到当前深度的下限。

light 模式：

```text
1. 2-3 个 KPI 或关键判断指标，可以来自用户材料或估算。
2. 2-3 个候选方案；用户没有给候选时，提炼 2 个可行动路径。
3. 2-4 条证据/依据；允许以用户材料为主。
4. 2-4 条风险或信息缺口。
5. 2-4 条关键假设。
6. 3-5 条行动建议。
```

standard/deep 模式尽量具备下面这些要素：

```text
1. 4 个可放入 Header 的关键 KPI 或定量指标。
2. 2-4 个候选方案；用户没有给候选时，QoderWork 根据材料提炼。
3. 每个候选方案至少 3 条支持或反对理由。
4. 6-10 条证据材料；每条包含数据/事实、来源、置信度、可支撑的结论。
5. 4-6 条风险；至少 1 条高风险，每条包含成因、影响和应对动作。
6. 3-6 条关键假设；每条包含“如果不成立”的替代判断。
7. 3-5 条行动建议；每条包含时间节点、动作对象、验证指标。
8. 重要信息缺口；说明缺什么、为什么影响结论、怎么补。
```

如果公开搜索拿不到足够数据，不要虚构；将不足写入 `known_gap`，但仍要把已有材料结构化到上述槽位。light 模式不要为了满足 deep 模式数量而补搜。

### B4 材料包验收

进入节点 C 前，QoderWork 必须用对应清单自检。自检不输出给用户，但必须实际执行。

light 清单：

```text
- [ ] 已确定 report_depth=light。
- [ ] 已读取用户材料或确认没有用户材料。
- [ ] 已明确是否搜索；用户要求不搜索时未搜索。
- [ ] 至少 2 个候选方案或行动路径。
- [ ] 至少 2 条依据，允许 user_provided / estimated / uncertain。
- [ ] 至少 2 条风险或信息缺口。
- [ ] 至少 3 条下一步行动。
- [ ] 所有无法确认的数据没有伪装成 verified。
```

standard/deep 清单：

```text
- [ ] 至少 4 个信息问题已经被搜索、用户材料或 known_gap 覆盖。
- [ ] 至少 4 个 KPI 候选，每个都有来源证据或明确标注估算。
- [ ] 至少 2 个候选方案，每个都有适用场景和切换条件。
- [ ] 至少 6 条结构化证据；材料不足时至少 4 条，并明确缺口。
- [ ] 每条证据都有 claim、specificFactOrNumber、decisionMeaning、confidence。
- [ ] 至少 3 条风险，且至少 1 条高风险。
- [ ] 至少 3 条假设，每条都有 ifNotTrue。
- [ ] 至少 3 条行动建议，每条都有 timebox 和 acceptanceMetric。
- [ ] 所有无法确认的数据没有伪装成 verified。
- [ ] 已知缺口说明了“缺什么、影响什么、怎么补”。
```

如果 light 验收失败，优先整理用户材料并降低置信度，不要自动补搜。standard/deep 验收失败时，可以补搜一次或整理用户材料；仍失败时，带着明确 `known_gap` 进入节点 C，并在报告里降低置信度。

## 节点 C：生成 HTML 报告

节点 C 读取内置规范并生成 HTML 文件。

执行规则：

```text
1. 读取 `~/.qwenworkcn/skills/deep-decision-research/references/decision-report-prompt-spec.md`。
2. 从规范中按 report_depth 提炼内部合规清单，不输出给用户。
3. 根据报告目标和研究材料包，生成完整 HTML；light 模式生成短 HTML。
4. 在当前 workspace 下创建目录：outputs/deep-decision-research/<run_id>/。
5. 文件名使用：<topic>-decision-report.html。
6. 一次性写入完整 HTML 文件。
7. 写入后只做必要结构检查：文件存在、包含 `<!DOCTYPE html>`、包含 `<style>`、包含 `</html>`。
8. light 模式：结构检查通过后立即进入节点 D；不删除、不重写、不清理临时脚本、不继续优化视觉。
9. standard/deep 模式：按合规清单检查；最多修正 1 次。仍不完美时，只要 HTML 完整，就交付并在最终回复说明缺口。
```

### 节点 C 的产物稳定性规则

这些规则优先级高于视觉增强：

```text
1. 产物完整性 > 视觉精致度 > 信息密度。
2. 禁止分段 append 生成 HTML；如果模型一次写入受限，应生成更短的 HTML，而不是拆成多段。
3. 禁止先写半成品再删除重写的循环。
4. 禁止在 HTML 已完整后继续执行清理、删除、重写、二次生成等操作。
5. 若需要临时脚本生成 HTML，执行成功并确认 `</html>` 后，不要删除脚本；直接交付路径。
6. 单个任务最多生成一个最终 HTML 文件；不要同时维护 artifacts 和 confirmations 的多份不同版本。
7. 如果工具返回 `writing` 但文件已存在且包含 `</html>`，视为可交付，不继续等待或重写。
```

### 节点 C 的视觉最低实现要求

以下要求来自内置规范。light 模式使用 light 下限；standard/deep 使用完整下限。

light 模式视觉下限：

```text
1. HTML 结构完整，有单一 `<style>`。
2. 有清晰标题、结论卡片、方案对比表、风险/缺口列表、行动列表。
3. 不要求深色 hero、4 个 KPI 横条、复杂矩阵或大量卡片。
4. 目标 120-260 行；超过 350 行时应压缩，不要扩写。
```

standard/deep 模式视觉下限：

```text
1. 顶部必须是深色 hero/header，可使用渐变、网格纹理或光晕增强层次。
2. Header 必须包含报告标题、副标题和 4 个 KPI 横条。
3. 每个模块必须有 section 级视觉标题，包含 01/02/03... 编号徽标。
4. 主要内容必须使用卡片化结构，推荐使用 card / card-header / card-body 这类层级。
5. 多维对比矩阵必须突出首选方案列，并用绿/橙/红表达好/中/差。
6. Badge 必须按语义上色：已验证/成功/低风险为绿，估算/警告/中风险为橙，高风险为红，信息为蓝。
7. 风险登记册每条风险左侧必须有彩色竖条。
8. 证据支撑不得少于 4 条，其中已验证证据不得少于 2 条。
9. 风险不得少于 3 条，其中高风险不得少于 1 条。
10. 假设必须 3-6 条，且每条都有“如果不成立”。
11. 行动建议必须 3-5 条，且每条都有明确时间节点。
```

### 节点 C 的信息层次最低要求

弱模型容易只按字段填空。节点 C 必须按深度使用信息层次。

light 模式最低内容：

```text
1. 决策摘要：一句话结论、置信度、最大风险。
2. 方案对比：2-3 个方案，3-5 个维度即可。
3. 主要理由：2-3 条，每条说明来自用户材料、估算还是常识。
4. 风险与信息缺口：2-4 条。
5. 下一步行动：3-5 条，有时间节点或验收方式。
6. 免责声明：高风险场景必须出现。
```

standard/deep 模式内容层次：

```text
1. Header KPI：每个 KPI 必须包含指标名、数值、解释短句，不能只有数字。
2. 决策摘要：必须同时给出一句话结论、置信度、关键假设、最高风险、立即行动。
3. 推荐方案：首选方案必须有 3-5 条“基于数据的理由”；备选方案不少于 1 个，并写明适用场景和切换条件。
4. 对比矩阵：必须包含 6-10 个与本任务直接相关的维度；最后一行是综合评分，并说明权重逻辑。
5. 证据支撑：每条证据必须包含“证据标题、具体事实/数字、来源、数据类型、这条证据支撑什么判断”。
6. 风险登记册：每条风险必须包含“风险事件、概率影响等级、发生机制、影响维度、应对动作”。
7. 假设清单：每条假设必须包含“前提条件”和“如果不成立，结论如何变化/替代建议是什么”。
8. 行动建议：每条行动必须包含“动作、对象/工具、时间节点、验收指标”。
```

每个模块都要回答一个隐含问题：

```text
这件事对用户的决策意味着什么？
```

如果某段内容只是背景描述，不能支撑判断、风险或行动，就压缩或删除。

### 节点 C 的渐进式披露最低要求

信息要丰富，但不能平铺成信息墙。light 模式只需“结论优先、理由随后、行动收尾”。standard/deep 模式按下面三层组织页面：

```text
第一层：首屏。只放报告标题、副标题、4 个 KPI、核心结论、最高风险、立即行动。
第二层：主体判断。放推荐方案、对比矩阵、关键证据摘要，让用户理解为什么。
第三层：细节展开。放完整证据、风险机制、假设边界、行动验收指标和信息缺口。
```

具体规则：

```text
1. 每个模块开头先给 1 句 takeaway，再展开细节。
2. 长内容必须拆成卡片、表格、标签、短段落，避免连续大段文字。
3. 可使用 HTML 原生 <details><summary>...</summary>...</details> 承载次级证据或补充说明，不依赖外部 JS。
4. 首屏不得塞入完整证据列表、完整风险列表或完整行动清单。
5. 证据/风险/假设/行动都要按重要性排序，先给最影响决策的信息。
6. 每个卡片优先展示标题、标签、关键数字/结论；解释和补充材料后置。
```

如果 light 页面能快速扫出“建议什么、为什么、最大风险、下一步”，即使不够华丽，也视为合格。standard/deep 页面如果内容多但用户无法快速扫出这些信息，才回到节点 C 修正一次。

### 节点 C 的反例判定

standard/deep 模式下，如果生成结果主要是下面形态，视为草稿，不可交付：

```text
浅色普通标题 + 若干 h2 + 简单白卡片 + 普通列表 + 少量表格
只有模块名，没有足够数据、证据、风险、假设、行动展开
只写“建议/总结”，没有说明数据依据和决策含义
所有信息平铺在页面上，没有首屏摘要、模块 takeaway 和细节后置
```

light 模式允许简单卡片和普通表格，只要结构完整、结论明确、路径可用。standard/deep 遇到这种结果，最多回到节点 C 修正一次。

`run_id` 格式建议：

```text
YYYYMMDD-HHMMSS-<short-topic>
```

`topic` 使用 2-6 个英文或拼音关键词，全部小写，用 `-` 连接，例如：

```text
coffee-coupon-decision-report.html
ecommerce-sku-decision-report.html
career-offer-decision-report.html
```

## 节点 D：交付结果

最终回复按固定结构输出：

```text
## 研究完成
基于当前材料，建议...

## 完整 HTML 报告
本地文件：outputs/deep-decision-research/<run_id>/<topic>-decision-report.html

## 关键依据
- ...
- ...
- ...

## 主要风险与信息缺口
- ...
- ...

## 下一步
- ...
```

不要把完整 HTML 源码贴在对话里。只给文件路径和简短摘要。

## Runtime Path Contract

QoderWork 运行时使用以下路径：

- 技能目录路径：`~/.qwenworkcn/skills/deep-decision-research/`。
- Workspace root：当前任务工作区；host 绝对路径不可访问。

路径规则：

- 报告规范从 `~/.qwenworkcn/skills/deep-decision-research/references/decision-report-prompt-spec.md` 读取。
- 运行产物统一写入 `outputs/deep-decision-research/<run_id>/...`。
- HTML 报告文件写在 workspace 下，不写回技能目录。

## Path Map

Skill-local files:

- `~/.qwenworkcn/skills/deep-decision-research/references/decision-report-prompt-spec.md`

Workspace files:

- `outputs/deep-decision-research/<run_id>/<topic>-decision-report.html`

## 停止节点

进入以下情况时，QoderWork 展示当前节点结果和下一步：

| 情况 | QoderWork 动作 |
|:---|:---|
| 用户问题为空 | 请用户补充问题 |
| 无法读取报告规范 | 提示 skill 包缺少 `~/.qwenworkcn/skills/deep-decision-research/references/decision-report-prompt-spec.md` |
| 无法写入 HTML 文件 | 提示写入失败和目标路径 |
| 用户明确要求停止 | 停止当前节点 |
