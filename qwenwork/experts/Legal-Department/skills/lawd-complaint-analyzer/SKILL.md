---
name: 起诉状分析与攻防策略
name_en: lawd-complaint-analyzer
displayName: 起诉状分析与攻防策略
description_en: "Complaint analysis and attack-defense strategy with two modes: Mode A dissects the plaintiff's claims item by item from the defendant's perspective, scores claim risks, spots evidence weaknesses, and produces a defense action checklist; Mode B identifies core disputes, decomposes legal elements, and simulates courtroom attack and defense. Use when a user receives a complaint and asks for risk assessment, response strategy, or dispute-focus analysis. Delivers a complaint risk analysis report and/or a dispute-focus analysis report."
argument-hint: 起诉状、答辩状及证据材料
description: "起诉状分析与攻防策略技能，含两个模式：模式A 从被告及应诉方视角逐项拆解原告诉讼请求、评估各项诉请风险、识别原告证据薄弱点与抗辩空间并生成防御行动清单；模式B 从起诉状、答辩状、证据材料和当事人主张中识别核心争议、拆解法律要件、归纳双方分歧并进行攻防推演，交付完整版或简易版争议焦点分析报告。当用户收到起诉状并要求分析、评估风险、判断怎么应诉、研究原告胜算或制定初步防御方案（即使只说“帮我看看这份起诉状”）时走模式A；当用户要求梳理争议焦点、法律争点、核心争议、诉讼请求要件、要件拆解、双方攻防或庭审争点时走模式B；两类需求同时提出时按模式A→模式B 连做。不用于代替用户起草起诉状、答辩状或上诉状（文书起草请用对应文书技能）；不适用于仅需合同条款修改的纯文书工作（律师合同预审）、案件结案后的办案小结（律师办案小结）、仅需查询企业信息（律师企业尽调报告）；仅需类案检索不需要争议焦点分析时使用类案检索（律师类案检索与报告）。"
---

# 起诉状分析与攻防策略

> 本技能为「律师办案助手」套件单元 9，由「起诉状深度解析」与「律师争议焦点分析」合并而成：对外一个入口，内部按用户意图分流到模式A / 模式B。

---

## 一、能力总述

本技能面向中国执业律师，围绕「对方打过来的诉请」与「法庭要查明的争点」两条主线，提供一体化的攻防分析能力：

- **模式A 起诉状风险分析**：以被告及应诉方视角，对起诉状逐项诉请做五维度风险评分，做原告证据脆弱性分析（三性 + 四关筛查 + 证据链缺口），产出可执行的防御行动清单（紧急事项 / 证据收集 / 法律研究 / 程序策略）。支持 11 种高频民事案由的专用分析维度。
- **模式B 争议焦点分析**：以请求权基础分析法为核心，拆解法律要件、归纳双方分歧、排序焦点优先级、对核心焦点做多轮法庭辩论推演，交付**完整版（8 章）**或**简易版（3 章叙述体）**争议焦点分析报告（Word）。
- **两模式连做**：先用模式A 摸清对方攻击路径与我方风险敞口，再用模式B 把风险敞口升格为法庭层面的争点体系与攻防路线。

共同底线：**不编造法条、不虚构案例、不预测案件结果**；所有事实引用可溯源；未取得检索结果时不得罗列法条或案例。

### 法律合规声明

1. **管辖范围**：中国大陆（不含港澳台）
2. **输出性质**：所有输出均为分析报告，仅供律师参考，不构成法律意见
3. **不保证结果**：案件结果取决于多方面因素，不做胜败预测
4. **法条时效**：法律依据基于截至 2026-03-01 的现行法律法规；引用法规须标注年份版本号
5. **不编造**：严禁编造法条、案例、伪造证据评估，严禁对无依据事实作确定性判断

---

## 二、触发与分流

### 2.1 用户意图 → 模式 路由表

| 用户意图 / 典型指令 | 路由 | 说明 |
|---|---|---|
| "帮我看看这份起诉状"、"解析/分析这份起诉状" | **模式A** | 起诉状为唯一材料且目标是摸清对方攻击路径 |
| "这份起诉状有什么风险"、"逐项评估诉请风险" | **模式A** | 逐项诉请风险评分是模式A 的核心 |
| "收到起诉状怎么应诉"、"制定防御方案" | **模式A** | 输出防御行动清单；若用户明说"写答辩状"→ 见 2.3 |
| "原告胜算多大"、"原告能赢吗" | **模式A** | 以风险等级 + 置信度回答，不做胜败预测 |
| "梳理下争议焦点"、"本案法律争点有哪些" | **模式B** | 焦点识别与归纳 |
| "核心争议是什么"、"庭审争点预判" | **模式B** | 含焦点优先级排序 |
| "要件怎么拆"、"请求权基础和构成要件分析" | **模式B** | 请求权基础分析法（Phase 1.1） |
| "双方攻防怎么打"、"辩论推演"、"攻防路线图" | **模式B（full）** | 必须执行 Phase 4 辩论推演 |
| "争点摘要"、"简易版/简要梳理争议焦点" | **模式B（simplified）** | 3 章叙述体 |
| "既要评估起诉状风险，也要归纳争点"、"看完起诉状再帮我把争点和攻防理出来" | **模式A + 模式B 连做** | 见 2.2 |
| 由 `庭前准备整合助手（律师庭前准备）` 作为「争议焦点分析」子模块调用 | **模式B（被整合调用）** | 按上游透传的 `report_profile`，见 §B.3 第 6 条 |

**分流判定纪律**：

1. 有起诉状但用户目标是「争点 / 要件 / 攻防」→ 走**模式B**（材料仅有起诉状时按 §B.2 标明材料局限，不得因材料不全拒绝执行）。
2. 用户目标是「逐项评估这份起诉状的诉请风险」→ 走**模式A**（本条即原争议焦点分析技能 description 中"若用户的唯一目标是从被告视角逐项评估一份起诉状的诉请风险，且当前环境已有更专门的起诉状分析能力，应优先使用专门能力"的落地：该专门能力现已内化为本技能模式A）。
3. 意图含糊、两种解读都成立时，**先问一句**："您是要（1）逐项评估这份起诉状的诉请风险与应诉方向，还是（2）梳理本案争议焦点与攻防路线？两者都要也可以。"用户不回复时按材料判断：仅有起诉状 → 模式A；已有答辩状/证据清单/双方主张 → 模式B。
4. **禁止**在同一次交付里混用两套报告模板（模式A 的《起诉状风险分析报告》七部分 vs 模式B 的争议焦点报告 8 章/3 章）。连做时按 2.2 分别成文。

### 2.2 模式A + 模式B 连做（衔接关系）

触发条件：用户同时要求「评估起诉状风险」与「归纳争点 / 攻防」。

执行顺序与数据衔接：

| 顺序 | 动作 | 向下游传递什么 |
|---|---|---|
| 1 | 执行**模式A** 全流程（Phase A1–A5），产出起诉状风险分析报告 | ① 结构化诉请清单（编号 + 请求权基础 + 引用法条）② 每项诉请的**法律要件清单**及覆盖状况 ③ 原告证据三性评估与证据链缺口 ④ 程序性抗辩机会 |
| 2 | 进入**模式B**，跳过重复劳动 | Phase 1.1 请求权基础分析**直接复用**模式A 的要件清单，不重新拆解；Phase 1.2 证据审查**直接复用**模式A 的证据脆弱性分析结论；Phase 1.0 案由匹配仍需执行（补充典型焦点清单） |
| 3 | 模式B 按 `report_profile` 完成 Phase 2–4 并出 Word | 争点体系以模式A 的「要件未满足/有争议项」为主干，逐项转化为争议焦点 |
| 4 | 交付前分别跑门禁脚本（§五）：模式A 报告按 `--mode a`，模式B 报告按 `--mode b` | 两份均通过才可交付 |

**衔接一致性硬要求**：连做时模式A 报告中的每一项「要件未满足 / 有争议」都必须在模式B 的争点体系中有归属（悬空要件会被门禁脚本拦截）；模式B 新增的、模式A 未覆盖的争点须注明来源（如"源自答辩状抗辩"）。

### 2.3 NOT FOR（引导至其他技能）

| 用户意图 | 引导方向 |
|---|---|
| "写起诉状" | 起诉状生成技能（`起诉状生成`） |
| "写答辩状" / "帮我答辩" | `答辩状一键起草` |
| "写代理词" | `代理词生成` |
| "全面分析报告"（不含起诉状、不以争点为目标） | `案情法律分析报告` |
| "查法条" | 法规检索（`律师法规检索`） |
| **仅需类案检索不需要争议焦点分析** | **使用 `类案检索（律师类案检索与报告）`** |
| 仅需合同条款修改的纯文书工作 | `律师合同预审` |
| 案件结案后的办案小结 | `律师办案小结` |
| 仅需查询企业信息 | `律师企业尽调报告` |
| 仅需发问策略 / 交叉询问设计 | `律师庭前准备 模式B` |

---

## 三、模式工作流

### 模式A ｜ 起诉状风险分析

以被告及应诉方视角拆解起诉状：逐项诉请五维度风险评分、原告证据脆弱性分析（三性 + 四关筛查 + 证据链缺口）、生成可执行的防御行动清单，支持 11 种高频民事案由专用分析维度；产出七部分《起诉状风险分析报告》（默认 Markdown）。完整工作流（A.0 提示与原则 / A.1 适用场景 / A.2 输入参数 / A.3 处理流程 Phase A1–A5 / A.4 反幻觉 / A.5 质量标准 / A.6 上下游串联 / A.7 系统提示语）已一字未删外移至参考文件。

> ⛔ 执行模式A 前，必须先完整读取 [references/mode-a-workflow.md](./references/mode-a-workflow.md)，严格按其流程执行，不得跳步。

### 模式B ｜ 争议焦点分析

以请求权基础分析法为核心，从起诉状、答辩状、证据材料和当事人主张中识别核心争议、拆解法律要件、归纳双方分歧、排序焦点优先级、对核心焦点做多轮法庭辩论推演，交付**完整版（8 章）**或**简易版（3 章叙述体）**争议焦点分析报告（Word）。完整工作流（B.1 执行顺序 Step 0–7 / B.2 案件信息收集 / B.3 约束原则 / B.4 工作流程 Phase 1–4（含要件—争点映射表）/ B.5 异常处理 / B.6 输出流程）已一字未删外移至参考文件。

> ⛔ 执行模式B 前，必须先完整读取 [references/mode-b-workflow.md](./references/mode-b-workflow.md)，严格按其流程执行，不得跳步。

> 本节及全文引用的模式A 小节号（A.0–A.7、Phase A1–A5）与模式B 小节号（B.1–B.6、Step 0–7）均对应上述两个工作流文件内的章节。

---

## 四、数据源

本单元**不直接调用外部数据连接器**。检索类依赖全部通过**兄弟技能**获得，调用方式保持不变：

| 能力 | 通过哪个兄弟技能获得 | 使用模式 | 强制性 |
|---|---|---|---|
| 类案检索（案例、裁判要旨） | `类案检索（律师类案检索与报告）` | 模式B | `full`：强制并完整写入报告「专业检索指引」；`simplified`：可选，仅供内部校验，正文不展开引用块 |
| 法规检索（法条、效力核验） | `法规检索（律师法规检索）` | 模式B | 同上 |
| 类案检索结果（增强司法实践维度） | 上游 `案情法律分析报告` 输出复用 | 模式A | 可选；无则标注"基于一般裁判经验" |

**为何不改连接器**：这两个检索技能自身正在被另一并行任务改造为走 MCP 连接器（按《SKILL 连接器写法指南》三铁律）。本单元只需继续按能力语义调用兄弟技能，连接器探测 / 匹配 / 降级由被调技能内部负责；在本 SKILL.md 里重复写连接器探测会造成双重实现与写冲突。

**文档生成**：`docx` skill 为首选；不可用时降级 `dws doc create`（钉钉文档）。这不是法律检索命令，不受连接器改造影响。

### 检索失败与结果不足的分级降级（沿用模式B 现行规则）

| 情形 | 处理 |
|---|---|
| 检索返回**空结果 / 结果明显不足** | 报告中明确注明"类案检索和法规检索结果不足，以下分析仅基于用户提供的案件材料，分析深度受限"；不强行生成基于检索结果的结论；建议用户调整关键词重试或补充案件信息（见 B.3 §5.5） |
| 检索技能**调用失败 / 服务不可用** | 告知"检索服务暂时不可用，请稍后重试"；可基于用户材料做基础争点分析，但报告中标注"检索服务不可用，分析深度受限"（见 B.5） |
| 被 `律师庭前准备` 整合调用且上游已提供检索结果 | 直接复用上游结果，不再自行调用检索技能（见 B.3 §6） |

**门禁语义（硬约束，任何模式均适用）**：

1. **未取得检索结果时，不得罗列未核验法条**——禁止以引用块/清单形式成批罗列未经检索核验的法条；确需 inline 提及法律依据的，**必须逐条标注"（待核验）"**（如"《中华人民共和国民法典》第五百七十七条（待核验）"），且引用后应尽快通过法规检索能力核验现行性。示例文件（example.md / defense-checklist-template.md）中的法条均为定位提示，直接照抄而不加标注等同违规。
2. **未取得检索结果时，不得虚构案例**——严禁编造案件名称、案号、法院、裁判人员、裁判日期或裁判要旨；无检索结果时该章节写明"未取得类案检索结果"，不得以"一般裁判倾向"之名编造具体案例。
3. **不得用 WebSearch 或模型内置知识冒充检索结果**——法律检索属"准确性即价值"场景，只允许标注降级、不允许无标注兜底。
4. 违反上述任一条，等同交付事故；门禁脚本的法条格式校验（§五）是最低机械防线，不能替代人工核验。

---

## 五、门禁脚本

**脚本**：`scripts/validate_analysis_report.py`（独立可运行，无第三方依赖，Python 3.8+）

**用途**：对即将交付的分析报告（Markdown / 纯文本）做机械校验，拦截漏项、断号、悬空要件、法条格式不合规。

**用法**：

```bash
# 查看帮助
python3 scripts/validate_analysis_report.py --help

# 模式A 报告（可显式给出原告诉请数，脚本亦会自行从风险总表推断）
python3 scripts/validate_analysis_report.py 起诉状风险分析报告.md --mode a --claims 3

# 模式B 报告
python3 scripts/validate_analysis_report.py 争议焦点分析报告.md --mode b

# 自动判定模式（按报告标题/章节特征）
python3 scripts/validate_analysis_report.py report.md
```

**校验项**：

| # | 校验项 | 适用模式 | 拦截条件 |
|---|---|---|---|
| 1 | 争点编号连续、无重复 | B（A 报告若含争点章节亦校验） | 编号不是从一开始的连续序列，或出现重复编号 |
| 2 | 要件 ↔ 争点映射完整 | B、A+B | 缺少「要件—争点映射表」；或存在要件的「对应争议焦点」为空 / "无" / "—" / "未归属"（悬空要件）；或映射引用了不存在的争点编号 |
| 3 | 逐项回应数 ≥ 原告诉请数 | A | 逐项诉请分析章节数 < 应逐项分析的诉请数（= 风险评级总表诉请数 − 总表内显式标注「随主请求 / 不单独评估」的附随请求数；或 `--claims` 给定数），即存在**静默漏项**；总表缺失且未给 `--claims` 时亦拦截 |
| 4 | 法条引用带法律名 + 条号 | A、B | 出现"第X条"但其前方未出现《法律名称》（裸条号）；或出现《法律名称》第X条以外的残缺引用形式 |

**自测样例（用于回归脚本本身）**：

```bash
python3 scripts/validate_analysis_report.py references/examples/sample-mode-a-pass.md --mode a              # 预期 exit 0
python3 scripts/validate_analysis_report.py references/examples/sample-mode-a-fail.md --mode a              # 预期 exit 1（静默漏项+裸条号）
python3 scripts/validate_analysis_report.py references/examples/sample-mode-b-full-pass.md --mode b         # 预期 exit 0
python3 scripts/validate_analysis_report.py references/examples/sample-mode-b-simplified-pass.md --mode b   # 预期 exit 0
python3 scripts/validate_analysis_report.py references/examples/sample-mode-b-fail.md --mode b              # 预期 exit 1（断号+重复+悬空要件+裸条号）
python3 scripts/validate_analysis_report.py references/example.md --mode a                    # 预期 exit 0（真实示例报告回归）
```

**交付纪律（强制）**：

- **交付前必须运行本脚本；未通过禁止交付。** 模式A 在 Phase A5 步骤 5.3 运行；模式B 在 Step 6 运行；A+B 连做时两份报告分别运行（`--mode a` / `--mode b`），两份均通过才可交付。
- 脚本通过时打印「通过清单」并以退出码 0 结束；存在拦截项时打印「拦截清单」并以**非零退出码**结束，此时必须修正内容后重跑，禁止带错交付、禁止绕过脚本。
- 脚本是机械底线，**不替代** A.5 质量标准与 B.3 §7 输出质量自检；两者都要执行。

---

## 六、交付物

| 模式 | 交付物 | 格式 | 关键格式要求 |
|---|---|---|---|
| **模式A** | 起诉状风险分析报告（七部分：案件基本信息 / 诉讼请求拆解与风险评级总表 / 逐项诉请深度分析 / 事实与理由分析 / 证据脆弱性分析 / 防御行动清单 / 后续建议） | 默认 Markdown（对话内交付）；用户明确要求 Word 时生成 `《XX案-起诉状风险分析报告》.docx` | 首行必须为 `=== 起诉状深度解析报告 ===`（下游识别标记）；按 [output-template.md](./references/output-template.md) 渲染；末尾附法律合规声明；Word 格式按 [docx-format-standard.md](./references/docx-format-standard.md) |
| **模式B（full）** | 争议焦点专项分析报告（8 章，含要件—争点映射表、攻防路线图、辩论推演、专业检索指引） | **仅 .docx** | 文件名 `《XX案-争议焦点专项分析报告》.docx`；按 [dispute-focus-output-format-template.md](./references/dispute-focus-output-format-template.md) 渲染 |
| **模式B（simplified）** | 争议焦点分析报告（简易版）（3 章叙述体：案件基本情况 / 本案核心争议焦点 / 简要结论） | **仅 .docx** | 文件名 `《XX案-争议焦点分析报告（简易版）》.docx`；按 [dispute-focus-output-format-template-simplified.md](./references/dispute-focus-output-format-template-simplified.md) 渲染；正文无 ★/☆、无表格、无类案法条引用块 |
| **模式B（both）** | 上述两份 Word 均交付 | **仅 .docx** ×2 | 分别通过各自硬校验后再分别调用 docx |
| **模式B（被 `律师庭前准备` 整合调用）** | 结构化争议焦点分析内容（供上游编排） | Markdown 结构化片段 | 不生成独立 Word；按上游 `report_profile` 控制展开长度 |
| **模式A + 模式B 连做** | 两份独立报告（模式A 报告 + 模式B 报告），并在模式B 报告开头一句说明衔接关系（"本报告在《起诉状风险分析报告》基础上，将其要件争议项升格为法庭争点"） | 见各模式 | 两份报告的要件编号与争点编号必须互相对应，无悬空要件 |

**降级**：`docx` 不可用时改用 `dws doc create` 生成钉钉文档，标题与上表文件名一致；`docx` 与 `dws doc create` 双重失败时提供纯文本版本并告知用户（见 B.5）。

**交付前检查（三道）**：① 模式对应的质量自检（A.5 / B.3 §7）→ ② 模式B 的 Step 6 渲染前硬校验 → ③ 门禁脚本 `validate_analysis_report.py`。三道全过方可交付。

---

## 附：参考文件索引

| 文件路径 | 适用模式 | 用途 |
|---|---|---|
| [references/mode-a-workflow.md](./references/mode-a-workflow.md) | A | 模式A 完整工作流（A.0–A.7、Phase A1–A5），执行模式A 前必读 |
| [references/mode-b-workflow.md](./references/mode-b-workflow.md) | B | 模式B 完整工作流（B.1–B.6、Step 0–7），执行模式B 前必读 |
| [references/output-template.md](./references/output-template.md) | A | 起诉状风险分析报告（律师版）输出模板 |
| [references/risk-scoring.md](./references/risk-scoring.md) | A | 风险评分方法论（五维度评估 + 权重 + 等级映射） |
| [references/evidence-vulnerability.md](./references/evidence-vulnerability.md) | A | 证据脆弱性分析框架（三性评估 + 四关筛查 + 证据链完整性） |
| [references/defense-checklist-template.md](./references/defense-checklist-template.md) | A | 防御行动清单模板 |
| [references/example.md](./references/example.md) | A | 完整示例（买卖合同纠纷起诉状解析） |
| `references/case-dimensions-<案由>.md` | A（连做时为要件主干） | 11 种案由专用分析维度（要件清单 / 常见抗辩 / 法条索引 / 权重调整） |
| [references/typical-disputes-by-case-type.md](./references/typical-disputes-by-case-type.md) | B（A 可参考） | 各案由典型争议焦点知识库（16 类案由） |
| [references/legal-elements-checklist.md](./references/legal-elements-checklist.md) | B（A 通用框架时可参考） | 请求权基础与要件事实检查清单（16 类请求权，含举证责任分配） |
| [references/evidence-checklist-by-focus.md](./references/evidence-checklist-by-focus.md) | B（A 可参考） | 分焦点证据清单 + 司法实践认定规则 |
| [references/dispute-focus-methodology-examples.md](./references/dispute-focus-methodology-examples.md) | B | 案由匹配法 / 请求权基础分析法 / 证据审查法详细示例 |
| [references/dispute-focus-debate-simulation-framework.md](./references/dispute-focus-debate-simulation-framework.md) | B（仅 full） | 辩论推演框架（立论 / 反驳预判 / 回应 / 最终陈述 + 法官关注预判 + 突发应对） |
| [references/dispute-focus-output-format-template.md](./references/dispute-focus-output-format-template.md) | B（full） | 完整版 8 章输出格式与模板规范 |
| [references/dispute-focus-output-format-template-simplified.md](./references/dispute-focus-output-format-template-simplified.md) | B（simplified） | 简易版 3 章输出格式与模板规范 |
| [references/examples/dispute-focus-simplified-sample.md](./references/examples/dispute-focus-simplified-sample.md) | B（simplified） | 简易版文风参考样例 |
| [references/docx-format-standard.md](./references/docx-format-standard.md) | A（Word 交付时）/ B | Word 文档格式规范（标题层级 / 正文 / 表格） |
| [scripts/validate_analysis_report.py](./scripts/validate_analysis_report.py) | A / B | 交付门禁脚本（争点编号 / 要件映射 / 逐项回应 / 法条格式） |

## 可选套件上下文（不影响独立使用）

1. 工作目录根存在 `套件运行规则.md` 时必须先读取并执行；不存在时以本技能硬规则为准，不影响独立使用。
2. 工作目录根存在 `办案画像.md` 时，只读取与当前任务有关的诉讼立场、风险偏好和文书风格；不存在时按本技能默认运行，不追问、不报错。
3. 仅当用户明确切换到某案或提供唯一案件路径时，读取 `cases/{案件简称}/案件画像.md`；不得猜测案件，不得跨案带入。
4. 画像只影响表达与偏好，不得覆盖事实、法律依据、必备结构、验证结果或本技能硬规则。
5. 已明确绑定唯一案件且案件管家可用时，成果完成后提交标准案件事件；无案件不建档、不回写，回写失败不得阻塞成果交付。
