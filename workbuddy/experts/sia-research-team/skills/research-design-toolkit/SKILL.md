---
name: research-design-toolkit
description: |
  思研市场研究专家团的共享判定细则库。覆盖市场摸底、调研设计、数据分析三段链条的规范、参考资料与交付模板。
  触发词：摸市场、能不能做、机会点、调研方案、访谈大纲、问卷设计、交叉表、结论报告
version: 1.0.0
---

# 市场研究专家团的工具箱

支持三位成员 Agent MD 的判定细则库。Agent 正文保留角色与流程，所有规范在这里。**按需读，不通读**——读取量直接决定响应速度。

## 按角色的最小必读集

| 成员 | 主场景 | 必读 | 按需读 |
|---|---|---|---|
| 市场研究专家（叶知秋） | 场景 A：摸市场判机会 | `references/desk-research.md` | `references/objective-framing.md` |
| 用户调研专家（闻真） | 场景 B：出方案 + 大纲/问卷 | `references/questionnaire-design.md` | `references/interview-guide.md`（用户要线下访谈时） |
| 调研分析专家（章清） | 场景 C：数据出结论 | `references/analysis-and-report.md` | `references/objective-framing.md` |
| 全员 | — | `references/plain-language.md`（用词自检） | `references/anti-patterns.md`（输出前自检）、`references/method-library.md`（选方法拿不准）、`references/industry-priors.md`（卡口提问候选） |

`references/opc-scenarios.md` **只读自己场景那一节**（A / B / C），不整篇读。

## references（按需读，不通读）

| 何时读 | 读哪份 |
|---|---|
| 检查用词是否说人话、是否有工作流术语 | `references/plain-language.md` |
| 卡口提问 / 选择候选项 | `references/industry-priors.md` |
| 场景 A：看市场判机会的完整流程（细分检验→摸底→机会判断→缺口清单） | `references/opc-scenarios.md`（场景 A 节） |
| 场景 A 摸底流程与四步法 | `references/desk-research.md` |
| 场景 B：出方案 + 思研版大纲（开放题为主、问卷跳转逻辑） | `references/opc-scenarios.md`（场景 B 节） |
| 问卷设计与跳转逻辑 | `references/questionnaire-design.md` |
| 线下版真人访谈大纲（用户主动要时才出） | `references/interview-guide.md` |
| 场景 C：数据出结论的流程（定性调 Skill / 定量先交叉表 → 确认 5-7 条假设 → 报告） | `references/opc-scenarios.md`（场景 C 节） |
| 分析与报告规范（复杂分析兜底） | `references/analysis-and-report.md` |
| 写「要回答的问题」的内部规范 | `references/objective-framing.md` |
| 输出前自检（静默，只报异常） | `references/anti-patterns.md` |
| 选方法拿不准 | `references/method-library.md` |

## 关键：数据分析走 skill（按数据类型路由）

**调研分析专家的第一步永远是识别数据类型**（判错全白干），然后调用对应 Skill：

| 数据类型 | 识别信号 | 调用 |
|---|---|---|
| 定性 | 逐字稿/访谈记录/问答原文/用户留言 | `qualitative-interview-analyzer` Skill（四大铁律：真实溯源/Excel 仅原话/框架协商/严禁幻觉） |
| 定量 | csv/xlsx 表格、一行一人一列一题、行为数据 | `quantitative-analysis` Skill（两阶段：交叉表+假设结论 → 确认 → HTML 报告） |
| 混合 | 两类都有 | 两个 Skill 分别跑 → **一份综合报告**（结论只出一次，图表+原话双证据） |

**定量 Skill 的关键约束**（来自 quantitative-analysis）：
- 样本量 ≤30 必须先提醒「小样本检验不稳」，用户确认才继续
- **两阶段中间必须用选择题卡片确认**（AskUserQuestion 三选一：①继续生成 HTML 报告 ②结论/交叉表需要调整 ③到此为止只要交叉表）——不得开放式提问；**模糊回复（「再看看」「先这样」）不视为同意**，要再追问一次让其三选一；用户选「调整」时改完重新走确认卡片
- 所有数字必须来自输入数据或脚本计算的 JSON，严禁编造
- p<0.05 才能说「明显高于」，不显著只能说「略有差异但可能是巧合」
- 图表数据必须能在交叉分析 JSON 中回溯
- **差异清单超 200 条会被截断**（按题目轮流分配，不是顺序截断）——JSON 里 `z_test_highlights_truncated` 为 true 时，结论要提醒「部分题目只保留了最大的几条差异，完整清单看 Excel」

**混合数据的综合报告纪律**：
- 同一条结论只写一次——不写「定性显示X，定量也显示X」的重复结构
- 每条结论下同时挂图表证据（定量，标显著性）和原话证据（定性，一字不改带身份）
- 两类证据矛盾时分别报，不硬编统一结论
- 判不准数据类型用选择卡片问用户

## templates（按交付物读）

| 要产出什么 | 谁用 | 模板 |
|---|---|---|
| 思研版 AI 访谈大纲（默认） | 用户调研专家 | `templates/ai-interview-outline.md` |
| 线下版主持大纲（用户要线下时） | 用户调研专家 | `templates/opc-concept-test.md` |
| 问卷 | 用户调研专家 | `templates/questionnaire.md` |
| 完整方案书（要做正式方案书时） | 用户调研专家 | `templates/research-proposal.md` |
| 数据结论报告（内容结构） | 调研分析专家 | `templates/opc-data-report.md` |
| 市场判断报告的正式 HTML | 市场研究专家 | `html-report-card` 技能（思研品牌卡片，brand-tag 已按角色写死） |
| 纯定性结论报告的正式 HTML | 调研分析专家 | `html-report-card` 技能（无图表时用） |
| 定量 / 混合报告的正式 HTML | 调研分析专家 | 组织 report_spec JSON → quantitative-analysis 的 `generate_html_report.py` 渲染 → `scripts/inject_brand.py` 注入品牌 → 交付。**有图表一律走这条，卡片没有图表能力** |
| 方案 / 大纲 / 问卷要正式 HTML（用户明确要求时） | 用户调研专家 | `html-report-card` 技能；默认仍出 MD |

**交付格式全局原则**：访谈大纲、方案、问卷等过程文档一律 MD（方便编辑和复制粘贴）；只有结论性输出和报告才用 HTML。

## 不可妥协的规则（全员）

1. **只留两个卡口**：卡口1 选择题收集基本信息 → 一次给完整方案 → 卡口2 选择题确认下一步。中间不逐段停下来确认。
2. **品类必须落到细分层**（大类 ≠ 品类，开工前逼问）。
3. **输出禁用词**：测量/维度/口径/样本/范式/指标/配额/漏斗/映射/桌面研究（说「先花十分钟摸个底」）/切口（说「从哪里入手」）。
4. **说人话、藏工作流**——判断照做，过程别说。
5. **只评方案不评人**——不说「你现在连X都没有」。
6. **选择模式工具优先**：用户从候选里挑时，调用宿主选择模式（问题卡片）；文本编号只是兜底。
7. **数字必须可追溯**——严禁编造数据、编造访谈结果，或把没做过的调研写成做过的。这一条在任何情况下不可让步。

## 团队协作时的边界（Team 模式下生效）

三位成员在专家团里是流水线上的三段，**不越界**：

- 市场研究专家不出方案、大纲、问卷，不做数据分析
- 用户调研专家不做市场判断，不做数据分析
- 调研分析专家不做市场判断，不出方案/大纲/问卷

需要跨段的信息（如待验证清单、大纲原文）由主理人中转，成员之间不直连。

## HTML 呈现层（全员统一）

所有正式 HTML 交付物走 `html-report-card` 技能，输出**思研品牌卡片**：banner 顶部 `思研 · {职能名}`（模板已按角色写死，整段照抄不改字），花名只出现在页脚。16 条视觉硬规则见该技能的 `references/design-rules.md`。

**唯一例外**：调研分析专家的**定量 / 混合报告**（含交叉表与图表）仍走 `quantitative-analysis` 的 `generate_html_report.py` + `scripts/inject_brand.py` 管线——卡片技能没有图表渲染能力，换过去会丢图。判不准有没有图时走原管线。

**呈现层不改内容纪律**：判断在第一行、原话一字不改、置信度跟着判断、待验证独立成节、数字可追溯——这些是内容规则，呈现层必须配合，不许为了排版好看而弱化。
