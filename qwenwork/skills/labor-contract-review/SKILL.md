---
name: labor-contract-review
description: 面向中文劳动合同签署、修订和模板复核场景，帮助用户快速识别关键用工风险、修改优先级和谈判边界，并形成可执行的审查意见。
install_source: official
install_method: download
skill_id: official_9s4SpPyM
enabled_at: 1791893788366
version: 1.0.0
name_zh: 劳动合同专项审查
---

# 劳动合同专项审查 Skill 说明

## 用户价值

本 skill 面向处理中文劳动合同的企业 HR、法务、业务负责人、律师助理及合同初筛团队，重点解决签约前和模板复用前的核心问题：合同能否签、哪些条款必须修改、哪些事项可以谈判、签署前需要补齐哪些材料和留痕。

核心价值包括：

- **签约前风险判断**：快速识别劳动合同是否存在明显用工风险，判断能否继续签署、哪些条款必须先改、哪些事项需要补充确认。
- **模板复核与口径统一**：帮助企业统一社保、工时、岗位地点、薪酬、违约责任、送达地址、离职交接等关键条款和配套管理口径。
- **形成可落地的修订与谈判意见**：输出可直接转给业务、HR 或律师使用的审查意见，明确必须坚持的条款、可让步边界，以及签署前需补齐的材料和证据留痕。

## 适用场景

适用于劳动合同签署前审查、企业模板复核、已有合同修订、谈判准备、甲方用工管理留痕检查，以及基于 `docx` 原件生成合同批注版。

## 交付目标

交付结果应直接支持用户决策和合同修改，而不是泛泛提示法律风险。用户应能快速看到：

- 合同整体是否适合继续签署，以及主要风险集中在哪些条款。
- 哪些问题属于必须修改项，哪些属于优化项，哪些需要补充确认。
- 每个风险点为什么重要、应该怎么改，以及可直接参考或替换进合同的修改文本。
- 作为甲方模板使用时，签署前、入职后、离职时需要配套完成哪些管理动作和留痕。
- 如用户提供 `docx` 原件，应优先生成可在原文位置查看批注的 Word 批注版。

## 交付原则

- 先给结论：用户应能在报告开头看到整体风险等级、必须修改项和一句话总结。
- 只展示真实命中的风险：不要输出逐规则通过/未通过记录，不要用规则编号堆砌过程。
- 完整审查明细按合同原文条款顺序输出风险，不按高/中/低风险分组。
- 修改建议要能落地：每个风险点都应说明怎么改，并尽量提供可替换的示例文本。
- 批注要挂在原文：能定位到合同原文时，优先生成 Word 批注版；不能生成时，不在正文里展开技术原因。
- 默认按甲方立场审查，除非用户明确指定乙方或均势审查；修改建议应在合法底线内优先保护企业管理弹性、举证能力和成本可控性。
- 最终对话输出必须直接展示完整正式报告正文，不能只输出摘要、交付成果或文件链接；正式报告必须从 `# 劳动合同审查报告` 开始，并遵守 `references/output-contract.md` 和 `references/report-template.md`。
- 附件区表格不能把纯文本文件名伪装成可下载链接；批注版必须作为平台真实文件附件交付。确认文件已生成并可交付时，表格中可写 Markdown 文件链接，或写“见下方附件卡片”；未生成时写 `未提供`。

## 目录说明

- `references/`：规则库、边界处理、输出契约、报告模板和示例文件。
- `scripts/`：报告渲染与批注后处理脚本，用于从报告反解析 `issues` 并生成 Word 批注版。
- `labor_contract_review/`：Python 包，包含字段解析、报告校验、批注锚点匹配和 `docx` 批注写入逻辑。
- `agents/openai.yaml`：OpenAI Agent 配置。

## 审查依据与资源

- 触发条件：用户请求审查中文劳动合同、生成劳动合同审查报告，或基于 `docx` 劳动合同生成批注版 Word。
- 默认立场：甲方，除非用户明确指定乙方或均势审查。
- 详细边界按 `references/boundary-rules.md` 执行。
- 输出契约按 `references/output-contract.md` 执行。
- 实体规则按 `references/labor-contract-rules.md` 执行。
- 报告模板按 `references/report-template.md` 执行。
- `HFR001-HFR015` 高频败诉风险属于常规审查范围，与 `LCR001-LCR017` 一样输出正式风险项和批注。
- 只要用户提供了 `docx` 附件，就默认视为批注原件可用。

## 标准工作流

1. 读取 `references/boundary-rules.md`、`references/output-contract.md`、`references/labor-contract-rules.md` 和 `references/report-template.md` 中与当前任务有关的内容。
2. 先完成合同审查，直接产出正式 Markdown 报告。报告格式、风险识别和风险排序不因是否生成批注版而改变。
3. 如存在 `docx` 原件，报告输出后再执行一个后处理脚本，由脚本从报告风险卡片反解析 `issues` 并挂载到原文段落生成批注版 Word。
4. 最终对用户直接展示完整正式报告正文；如后处理脚本生成批注版成功，应上传/附加真实 Word 文件，并在 `## 六、附件下载` 表格中写可点击 Markdown 文件链接或“见下方附件卡片”，不另起“交付成果”小节替代报告。

## 异常处理与状态管理

- 本技能为无状态设计，所有中间结果通过报告 Markdown、临时文件和后处理脚本参数传递，不依赖长期记忆或会话状态。
- 参数缺失（未提供 `docx` 原件）时，仅输出 Markdown 报告，附件表格写 `未提供`。
- 文件读取失败时，停止生成批注版；仍交付 Markdown 报告，附件表格写 `未提供`。
- 大文件或复杂文档处理超时时，可分块提取文本或提示用户简化合同；不得虚构完整审查或附件。
- 批注脚本执行失败时，在报告附件表格中写 `未提供`，仍以 Markdown 报告作为可用成果。

## 结构化 JSON 最低要求

- 顶层可直接是风险项数组，或包含 `issues` 数组的对象。
- 如需同时携带报告正文，可额外包含 `report_markdown`、`report`、`markdown` 等字段。
- 每个风险项至少应能解析出以下信息：
  - `rule_id`
  - `clause_title`
  - `clause_position`
  - `risk_level`
  - `risk_type`
  - `original_excerpt`
  - `risk_message`
  - `risk_analysis`
  - `revision_suggestion`
  - `revised_text_example`
  - `comment_title`
  - `comment_author`
- 风险项字段允许使用别名；实际解析规范以 `labor_contract_review/review_result.py` 中的 `FIELD_ALIASES` 为准。
- 生成 Word 批注时，至少必须有：
  - `risk_message`
  - `risk_analysis`
  - `revision_suggestion`

## 批注版生成流程

### 推荐方式：报告输出后生成批注版

先输出正式 Markdown 报告，再运行一条后处理命令：

```bash
python3 scripts/annotate_report_docx.py --report <report.md> --document <contract.docx> [--output <annotated.docx>]
```

执行结果：

- 校验报告 Markdown 格式。
- 从 `### 2. 按合同条款顺序的风险问题` 的风险卡片反解析结构化风险项。
- 读取原始 `docx`。
- 根据 `paragraph_id`、原文摘录或位置描述定位批注锚点。
- 输出批注版 `docx`。
- 未显式传 `--output` 时，默认命名为：`原文件名-批注版-年月日.docx`。

这个脚本只改变批注版生成步骤，不改变报告正文、风险识别、风险等级或排序。

### 兼容方式：从审查 JSON 生成报告和 issues

如已有 AI 审查结果 JSON，可继续运行：

```bash
python3 scripts/render_review_outputs.py --input <review.json> --output-dir <output-dir> [--file-name <原合同文件名.docx>]
```

随后也可以继续用旧批注脚本：

```bash
python3 scripts/annotate_docx.py --document <contract.docx> --issues-json <output-dir/*_issues.json> [--output <annotated.docx>]
```

### 最终附件填写规则

- 批注版生成成功：将真实存在的 `docx` 作为平台文件附件交付，并在 `## 六、附件下载` 表格中写 Markdown 文件链接，或写 `见下方附件卡片`。
- 批注版未生成：附件表格仅写 `未提供`。
- 批注脚本执行失败：记录失败原因，继续交付 Markdown 报告，附件表格写 `未提供`。
- 如合同无风险、无需批注，可明确提示“合同无风险，无需生成批注版”，附件表格仍写 `未提供`。
- 不得根据预期命名、报告文字或计划结果虚构 Word 附件。
- 不允许在附件表格中写过程性占位词。
