---
name: paper-write-en
description: 英文学术论文正文写作。用于从想法、证据、材料或草稿起草、续写、扩写、补写英文整篇论文、章节或段落，以及实际移动段落或改变主张、证据、章节职责、段落归属和内容取舍的实质性修订，并完成来源核验、引用、格式和交付。独立提纲、结构方案、纯语言润色或不新增研究内容的中译英转paper-shape；中文正文写作转paper-write-zh；研究价值、稿件质量和投稿可行性评估转/doubao-academic-evaluator；独立系统性文献调研转/doubao-literature-research。
---

# 学术英文论文写作 workflow

本 workflow 用 Makefile 驱动，不靠自觉记流程。你只做两件事：**写英文正文**、**按 make 的提示补文件**。阶段顺序、前置依赖、什么算完成，全部由 `make` 强制，不由你判断走到哪一步。

## IRON RULES（最高优先级，共 10 条）

1. **只认 make**：不自行判断阶段，不凭记忆推进。不确定就运行 `make`，它会告诉你现在唯一该做的事。
2. **内容写进文件**：英文正文写入 `.workflow/paper_draft.md`，不在对话里交付正文。文件存在且通过检查才算做完。
3. **文献先验真**：需要引用时，候选文献写入 `.workflow/candidates.json`，由 `make prepare` 调 verify_literature 真实性核验，只有 A/B 级、通过 title/author/doi 校验的文献才可进正文。不凭记忆写文献。
4. **不编造**：不编造文献、数据、DOI、访谈、问卷结果、统计显著性、实验发现。构造/模拟数据必须标注。
5. **文内引用 + References**：正文文献性判断必须挂文内引用（作者-年份或编号），文末必须有 References，按体例（默认 APA 7）。
6. **正文连贯论述**：英文正文不用有序/无序列表；类别、变量、步骤改用表格。
7. **正文干净**：正文不得残留验真中间字段（scout_handoff、code_trace、authority_signal 等）、占位符、AI 过程说明。
8. **不碰门禁**：不修改 `scripts/` 下检查脚本、不改阈值、不注释检查、不手改 `.workflow/` 检查报告让流程通过。检查失败就改正文。
9. **交付只报三态**：完成度以 `make status` 结论为准，只报 PASS / BLOCKED / DRAFT_ONLY，不自我总结“已完成”。
10. **不派子 Agent**：语义写作自己完成。

前 7 条脚本会强制拦截，第 8 到 10 条靠遵守。

## 怎么运行（唯一入口）

在 `paper-write-en` 目录下，任何时候运行：

```bash
make
```

`make` 默认等于 `make deliver`，沿依赖链自动检查：准备（含文献验真）→ 正文 → 交付飞书。**停在哪一步就按它打印的提示做那一步**，做完再运行一次 `make`。

单独运行某阶段：

```bash
make prepare   # 校验 meta.json + 候选文献验真
make write     # 校验英文正文（引用体例/章节顺序/词数）
make deliver   # 按 meta.output_target 生成终稿或交付飞书（默认目标）
make status    # 打印 PASS / BLOCKED / DRAFT_ONLY
```

`OFFLINE=1`只适用于`needs_citation=no`的无引用任务。需要引用时必须完成联网验真，离线或联网降级会阻断prepare。交付目标只读取`.workflow/meta.json`中的`output_target`；不要用环境变量覆盖它。用户不要飞书时必须在prepare前把`output_target`设为`markdown_only`。

用户、学校或期刊给出明确篇幅时，把`min_words`和`max_words`写入`.workflow/meta.json`，使后续`make deliver`和`make status`沿用同一合同。`MIN_WORDS`和`MAX_WORDS`只用于同一次make调用的临时覆盖，不作为跨命令状态。未设置时，由`check_draft.py`按`task_scope`和`paper_type`选择宽范围的完整性门槛；不得把摘要、单节、期刊论文和学位论文统一套同一上限。

## 三阶段与产物

状态即文件。没有 handoff.json，没有你手动维护的 state.json。

| 阶段 | make 目标 | 你要产出的文件 | 通过后脚本生成 |
|---|---|---|---|
| 准备 | `prepare` | `.workflow/meta.json`、（需引用时）`.workflow/candidates.json` | `prepare_check.json`、`verified_refs.json` |
| 写作 | `write` | `.workflow/paper_draft.md` | `draft_check.json` |
| 交付 | `deliver` | 无需手写，make按meta生成终稿并按需建飞书 | `paper_final.md`、`lark_check.json`、飞书交付时的`lark_permission.json` |

### 准备阶段

1. 判定并写 `.workflow/meta.json`，字段取值须落在枚举内：

```json
{
  "mode": "draft|final",
  "task_scope": "full_paper|section|revise|abstract",
  "paper_type": "research_article|review_article|term_paper|journal_article|conference_paper|thesis|proposal|other",
  "citation_style": "apa7|mla9|chicago18_author_date",
  "needs_citation": "yes|no",
  "output_target": "lark|markdown_only"
}
```

有明确篇幅要求时再增加数值字段，例如`"min_words": 4000`和
`"max_words": 8000`；没有明确要求时省略。

`mode=draft`允许清楚标注的拟议设计或模拟数据，但必须说明其非真实证据；
`mode=final`不得保留simulated、constructed、hypothetical或placeholder data。
用户要求投稿版、可提交终稿或最终版时使用final；缺真实数据时不得以draft内容冒充final。

`task_scope: revise`只用于需要重新处理结构、证据或章节职责的实质性修订。进入write前把用户原稿原样保存为`.workflow/original_draft.md`，并创建`.workflow/revision_contract.json`：

```json
{
  "preserve": ["必须保留的术语、限定语或核心表述"],
  "approved_changes": [
    {"from": "含Smith (2020)的完整原行", "to": "获批的完整新行", "reason": "修改原因", "user_authorized": true}
  ]
}
```

脚本自动保护原稿中的编号、括号引用、数字及`preserve`字面锚点。任何含受保护引用、数字或preserve锚点的完整行只要发生改写，都必须把完整原行和完整新行写入`approved_changes`并记录理由与用户授权；片段、跨行拼接或不存在的上下文不能授权。该门禁只证明确定性字面信息及其所在行未被静默改写，不证明引用支持关系、因果、机制或方法解释正确，语言收尾后仍须按`paper-shape/references/polish.md`做语义保真复读。已有文本只改语法、行文或学术表达时，不进入本流程，转同级`paper-shape`。

2. 需要引用时，在运行 `make prepare` 前先按 `subskill/literature-review-guide.md` 的范围、检索和筛选规则建立候选池，只完成候选选择，不写综述正文。把候选文献写入 `.workflow/candidates.json`（结构见 `scripts/references.sample.json`），每条至少含 title、first_author、url，尽量含 doi、container_title、year。`make prepare` 会调 verify_literature 联网核验真实性与质量凭据，只有 A/B 级进入 `verified_refs.json` 的 core_literature；正文综合在prepare通过后进行。核验方法见 `subskill/verification-guide.md`。

### 写作阶段

按需读取 subskill 各 guide 写英文正文到 `.workflow/paper_draft.md`：

- 写完整论文、章节或实质性改写前，读取 `../paper-shape/references/structure.md`，先形成与材料和证据一致的论证骨架；不把内部骨架打印进正式正文。
- 完整论文常见功能清单（不是固定顺序）：Title、Abstract、Keywords、Introduction、Literature Review、Theoretical/Conceptual Framework、Methodology、Analysis/Results/Findings、Discussion、Conclusion、References。实际顺序、合并和省略先服从 `structure.md` 推导的论证依赖，再服从目标期刊或用户模板。
- 文献选择/综述：`subskill/literature-review-guide.md`
- 理论框架：`subskill/theoretical-framework-guide.md`
- 方法：`subskill/methodology-guide.md`
- 分析与讨论（含章节实质性改写）：`subskill/analysis-discussion-guide.md`
- 结论：`subskill/conclusion-guide.md`
- 摘要、关键词与全篇整合审查、语言收尾：`subskill/integration-review-guide.md`
- 格式、标题、非英语术语、References、表格图：`subskill/format-guide.md`、`reference/*.md`
- 正文完成后读取 `../paper-shape/references/polish.md` 做英文语言收尾，只修表达和段落节奏，不借收尾新增证据、结论或贡献。

写作硬约束（脚本会查）：只用 verified_refs 里的文献；章节顺序符合功能序；正文连贯不用列表；默认 APA 7，不得用编号脚注/Id./Ibid.；不残留验真中间字段。

格式硬约束（脚本查不到，但必须遵守）：

- 凡涉及正文呈现、标题、非英语术语、引用格式、References、表格、图或输出文件格式，必须读取 `subskill/format-guide.md`。
- 表格和图必须读取并遵守 `reference/table-figure-guide.md`。数据表在 Markdown 源稿中使用原生表格，保持可编辑和可访问；图像只有在具备真实资产生成、上传和回读链路时才嵌入，否则使用合格图占位。
- References 条目按体例读对应指南：APA 7 读 `reference/apa7-format-guide.md`，MLA 9 读 `reference/mla9-format-guide.md`，Chicago 18 author-date 读 `reference/chicago18-format-guide.md`。Chicago Notes与Bluebook当前未实现完整门禁，不得在meta中选择。

### 交付阶段

正文过`make write`后，`make deliver`只按meta执行：

- `output_target=markdown_only`：生成终稿，不调用飞书；`status.py`直接读取该meta值判定交付要求。
- `output_target=lark`：生成终稿 → lark-cli只用标题创建空文档 → 读取并校验非公网/已授权公开档位 → 权限合格后写入正文 → 读回正文 → check_lark校验标题、正文完整性、引用、表格和禁用花哨块 → 打印链接与三态。

不得假设新建文档默认私有。未授权公开时，make不执行高风险权限写入，只用`lark-cli drive +permission-get-setting`读取`.workflow/lark_permission.json`；仅当`external_access=false`且`link_share_entity=closed`时继续，否则写失败`lark_check.json`并BLOCKED，等待用户针对该文档确认后另行收紧。只有用户已明确授权本次交付文档采用`anyone_readable`公网档位时，才可在本次make命令行显式传入`PUBLIC_LARK=1`；继承自环境的同名变量无效。该路径执行公开patch并再次读回验证。飞书文档保持学术风格，禁callout、彩色块、折叠块、emoji和装饰卡片。

创建、权限读取、公开patch、正文fetch或check_lark失败时，make会先写可被`status.py`识别的失败`lark_check.json`，再输出`BLOCKED`，不得把原始shell错误当作交付结论。权限快照路径和解析后的`data.permission_public`会保留在成功报告中，供后续校验脚本接管。

## 三态交付口径

最终回答状态由 `make status` 给出，你只如实转述：

- **PASS**：正文检查通过，且meta指定的飞书交付或Markdown交付已完成；同时如实说明meta中的draft/final模式。飞书目标附链接，draft不得表述为可投稿终稿。
- **BLOCKED**：卡在某阶段，说明卡点与 next 指令。
- **DRAFT_ONLY**：正文存在但检查未过或未交付，标注未验收草稿，禁止说“已完成”。

## 边界范围（不命中本 skill）

- 中文论文起草或完整中文写作 → 走 `paper-write-zh`。
- 已有中文学术文本只做中译英润色且不新增内容 → 走 `paper-shape`；需要基于中文材料重建、扩写英文论文内容时留在本线。
- 基于用户已提供或prepare阶段已验真的来源撰写英文review article或standalone literature review属于本线；需要先独立检索整个方向并产出survey时转`/doubao-literature-research`。
- 判断研究价值、稿件质量、研究设计是否成立或投稿可行性时转`/doubao-academic-evaluator`，不由正文写作线下评审结论。
- 单独搭提纲、理主线、重排结构，或只做语法、行文、学术表达、中译英润色 → 走同级 `paper-shape`。
- 仅选题/头脑风暴、独立参考文献制作/引用格式转换/排版美化。
- 非学术文案、营销文案、纯翻译、PPT、简历。

本线处理需要新增或重建论文内容的英文写作。已有中文或英文稿只要求改语言时，不进入完整 Makefile，交给 `paper-shape`。

## 可用脚本（由 Makefile 调用，一般不手动跑）

- `scripts/check_prepare.py`：校验 meta，编排文献验真。
- `scripts/verify_literature.py`：真实性核验引擎（Crossref/OpenAlex/Semantic Scholar 三源，DOI 反查、标题相似度、引述核对、质量凭据）。
- `scripts/check_draft.py`：英文正文形态检查（词数、章节顺序、引用体例、验真痕迹、禁列表）。
- `scripts/check_lark.py`：飞书读回校验。
- `scripts/status.py`：三态结论。

脚本是强制门卫；论文的学术质量、论证对错仍由 subskill 方法论与人工审查负责。
