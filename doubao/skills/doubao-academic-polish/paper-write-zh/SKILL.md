---
name: paper-write-zh
description: 中文学术论文正文写作。用于从想法、证据、材料或草稿起草、续写、扩写、补写中文整篇论文、章节或段落，以及实际移动段落或改变主张、证据、章节职责、段落归属和内容取舍的实质性修订，并完成来源核验、引用、学科结构、格式和交付。独立提纲、结构方案或纯语言润色转paper-shape；英文正文写作转paper-write-en；研究价值、稿件质量和投稿可行性评估转/doubao-academic-evaluator；独立系统性文献调研转/doubao-literature-research。
---

# 中文论文写作 workflow

本 workflow 用 Makefile 驱动，不靠你自觉记流程。你只做两件事：**写正文内容**、**按 make 的提示补文件**。阶段顺序、前置依赖、什么算完成，全部由 `make` 强制，你不要自己判断走到哪一步。

## IRON RULES（最高优先级，共 10 条）

1. **只认 make**：不自行判断当前阶段，不凭记忆推进。每次不确定就运行 `make`，它会告诉你现在唯一该做的事。
2. **内容写进文件**：正文写入 `.workflow/paper_draft.md`，不在对话里交付正文。文件存在且通过检查才算做完。
3. **来源先行**：涉及文献、法条、案例、史料、政策、数据、实验、指南、访谈时，先把来源写入 `.workflow/source_pool.md`，每条含题录、核验状态、核验依据与可访问 URL；只有已核验条目可计数、引用，不凭记忆写事实。
4. **文献性判断必须文内引用**：综述、研究现状、引言、相关工作、理论框架、法学规范论证，必须显式文内引用，不能只列参考文献。
5. **Final 不留缺口**：Final 模式正文不得残留待补、待核验、mock、模拟数据、PLANNING DATA。
6. **正文干净**：正文不得残留 `**` `__` 加粗、`_..._` 斜体、emoji、HTML 上下标、AI 提示词、过程说明、用户指令。
7. **学科分流**：技术、医学、法学、人文社科实证、人文学科思辨、综述按各自结构写，禁止把文科论文套成理工实验结构。
8. **不碰门禁**：不修改 `scripts/` 下任何检查脚本、不改阈值、不注释检查、不手动编造 `.workflow/` 下的检查报告让流程通过。检查失败就改正文，不是改检查。
9. **交付只报三态**：完成度以 `make status` 的结论为准，只报 `PASS` / `BLOCKED` / `DRAFT_ONLY`，不自我总结“已完成”。
10. **不派子Agent**：语义写作由你自己完成，不委派其他代理代写正文。

前 7 条脚本会强制拦截，第 8 到 10 条靠你遵守。绕过检查不会让论文变好，只会把问题藏到用户眼前的交付物里。

## 怎么运行（唯一入口）

在 `paper-write-zh` 目录下，任何时候运行：

```bash
make
```

`make`默认等于`make deliver`，它会沿依赖链自动检查：准备是否就绪 → 正文是否合格 → 按`output_target`交付。**停在哪一步，就按它打印的提示做那一步**，做完再运行一次`make`。不要跳过它直接写下一阶段。

单独运行某阶段检查：

```bash
make prepare   # 校验 meta.json 与来源池
make write     # 校验正文形态（会先要求 prepare 通过）
make deliver   # 生成终稿，并按 output_target 决定是否创建、校验飞书（默认目标）
make status    # 打印 PASS / BLOCKED / DRAFT_ONLY
```

交付目标只认 `.workflow/meta.json` 的 `output_target`：用户只要 Markdown 时写 `markdown_only`，需要 Markdown 与飞书时写 `markdown_and_lark`。不存在命令行跳过变量，`make deliver` 与 `make status` 必须读取同一目标，避免元数据与实际交付分叉。

用户明确提出篇幅要求时，把`min_chars`和`max_chars`写入`.workflow/meta.json`，使后续`make deliver`和`make status`沿用同一合同。`MIN_CHARS`、`MAX_CHARS`只用于同一次make调用的临时覆盖，例如：

```bash
make write MIN_CHARS=3000 MAX_CHARS=6000
```

分阶段运行时不得依赖上一次命令行变量。没有明确篇幅要求时省略meta中的这两个可选字段，由`check_draft.py`以`task_scope`为主、`paper_type`为辅选择宽范围默认值。具体默认范围只能在脚本维护，文档与Makefile不得复制一套阈值形成双重来源。

## 三阶段与产物

状态即文件。没有 handoff.json，没有你手动维护的 state.json。

| 阶段 | make 目标 | 你要产出的文件 | 通过后脚本生成 |
|---|---|---|---|
| 准备 | `prepare` | `.workflow/meta.json`、（需引用时）`.workflow/source_pool.md` | `prepare_check.json` |
| 写作 | `write` | `.workflow/paper_draft.md` | `draft_check.json` |
| 交付 | `deliver` | 无需手写，Makefile按目标生成终稿并按需建飞书 | `paper_final.md`、按需生成`lark_check.json` |

### 准备阶段要做什么

1. 判断并写 `.workflow/meta.json`，字段取值必须落在枚举内：

```json
{
  "mode": "draft|final",
  "task_scope": "full_paper|chapter|section|paragraph|revise|check",
  "paper_type": "journal|degree|course|conference|review|proposal|other",
  "discipline_branch": "technical|medical|law|hss_empirical|hss_humanities|review",
  "needs_citation": "yes|no",
  "output_target": "markdown_and_lark|markdown_only",
  "citation_style": "gbt7714_numeric|author_year|footnote|apa|chicago|mla|template"
}
```

`task_scope=revise`用于会改变结构、证据安排、章节职责或内容取舍的实质性修订。进入write前把用户原稿原样保存为`.workflow/original_draft.md`，并创建`.workflow/revision_contract.json`：

`task_scope=check`只检查当前正文写作过程中的来源、引用、格式和确定性门禁，不承担研究价值、研究设计质量、稿件硬伤或投稿可行性评审；后者转`/doubao-academic-evaluator`。

```json
{
  "preserve": ["必须保留的术语、限定语或核心表述"],
  "approved_changes": [
    {"from": "含张三（2020）的完整原行", "to": "获批的完整新行", "reason": "修改原因", "user_authorized": true}
  ]
}
```

脚本自动保护原稿中的编号、括号引用、数字及`preserve`字面锚点。任何含受保护引用、数字或preserve锚点的完整行只要发生改写，都必须把完整原行和完整新行写入`approved_changes`并记录理由与用户授权；片段、跨行拼接或不存在的上下文不能授权。该门禁只证明确定性字面信息及其所在行未被静默改写，不证明引用支持关系、因果、机制或方法解释正确，语言收尾后仍须按`paper-shape/references/polish.md`做语义保真复读。

- 模式：用户说写一篇、初稿、先出完整稿 → `draft`；说终稿、投稿前、可提交、最终版 → `final`，但缺材料时降级为 `draft` 或阻塞。
- 学科分支：technical 工程计算机等；medical 医学生物临床；law 法条案例裁判；hss_empirical 政治经济管理社会教育传播的实证研究；hss_humanities 文史哲艺术马理论的思辨研究；review 综述述评。
- `needs_citation` 为 `yes` 时，必须建来源池。

2. 需要引用时，把已核验来源写入 `.workflow/source_pool.md`，建议表格：

```markdown
| ID | 来源 | 类型 | 证据层级 | 可支持的事实 | 可写入正文的判断 | 适用位置 | 风险 | 核验状态 | 核验依据 | URL |
|---|---|---|---|---|---|---|---|---|---|---|
```

`核验状态`只接受能区分“已核验”与“未核验”的明确值；只有“已核验”条目计入最低来源数并可进入正文与参考文献。中文CNKI文献只有取得知网导出引用原文，或用户提供等价可追溯的完整引用与页面证据，才能标记已核验；仅有页面题名、作者、来源、年份或摘要时仍标记待核验。`核验依据`填写实际查看的页面、数据库导出、用户材料及页码/段落/记录定位，不能只写“网络检索”或“已确认”。未核验条目可以留在池中继续处理，但不得凑数或支持正文判断。

只拿到题名或元数据的文献只能支持元数据层判断，不能写具体研究结论。中文文献没有可核验页面证据、导出引用或用户回填来源时，不得进入正式参考文献。各学科来源范围：technical 核验基础方法/模型/指标/数据集原始文献与实验材料；medical 核验指南/共识/原始研究与伦理注册样本统计报告规范；law 法条案号判决结果必须有可核验来源；hss_empirical 核验核心文献与数据问卷访谈案例政策；hss_humanities 核验原典/译本/史料/档案版本页码；review 说明检索范围/数据库/检索词/筛选标准。

### 写作阶段要做什么

先在脑子里定结构再落笔，把正文写入 `.workflow/paper_draft.md`（单文件，含标题、摘要关键词若需要、正文各章节、表格、图占位、参考文献）。

写完整论文、章节或实质性续写前，读取 `../paper-shape/references/structure.md`，按其中工作流把研究问题、材料、方法、主张和结论关系理清，再落正文。正文完成后读取 `../paper-shape/references/polish.md` 做中文语言收尾，检查段落思路、句子节奏和信息保真；不借收尾新增材料或改写研究结论。独立提纲和已有文本的单纯润色不进入本 Makefile，交给同级 `paper-shape`。

下列内容是各学科常见的**功能清单**，不是必须照搬的目录。章节顺序、合并和省略先服从 `../paper-shape/references/structure.md` 推导的论证路径，再服从用户、学校或期刊模板。

- technical：题目、摘要、关键词、引言、相关工作、方法、实验与结果、讨论、结论、参考文献。方法章有数据流与本文决策，实验章有指标基线数据与结果边界。
- medical：按研究类型选 IMRaD 或对应报告规范（CONSORT/STROBE/PRISMA/STARD/CARE/ARRIVE），列出伦理注册样本统计。
- law：问题提出、现行规定及不足、解释路径或案例评析、域外比较、完善建议、结语。区分规范解释、案例评价、制度建议，建议须回到前文问题与证据。
- hss_empirical：问题提出、文献综述、理论框架与假设、数据来源、结果分析、讨论与结论。说明变量材料样本方法边界。
- hss_humanities：问题提出、核心概念与理论视角、文本史料分析、分论点递进、总体判断。必须有中心论点，不堆材料摘录。
- review：研究问题、检索与筛选、主题综述、比较分析、主要争议、研究不足、未来方向、参考文献。按主题与争议组织，不逐年罗列。

写作硬约束（脚本会查）：只用来源池已有事实，不新增作者、年份、题名、法条、案号、实验数值、史实、理论归因；文内引用默认 GB/T 7714 顺序编码 `[1]`，若体例冻结为作者-年份/脚注/APA 等须全篇一致；结构化内容用表格，表题表注不与下一节标题粘连；图只写正式占位 `图X待绘制：图题。内容要求：...`，不写“此处插图”。Draft 模式的 mock 数据表注须写 `PLANNING DATA - replace before submission`；Final 模式不留任何缺口。

### 交付阶段做什么

正文通过`make write`后，`make deliver`按`meta.output_target`执行。`markdown_only`只生成终稿并按该目标判三态；`markdown_and_lark`执行：复制终稿 → 只用标题创建空飞书文档 → 查询并校验实际权限 → 权限合格后写入正文 → 读回XML → 校验正文 → 把权限状态合并进`lark_check.json` → 打印链接与三态。飞书文档保持学术风格，禁止callout高亮、彩色块、折叠块、大量emoji、装饰性卡片按钮分栏；允许标题、段落、表格、必要列表、公式块或可转LaTeX源、正式图占位。

默认私有路径不得依赖新建文档的默认权限，也不得自动执行高风险权限写入。创建后必须用`drive +permission-get-setting`查询`data.permission_public`，只有`external_access=false`且`link_share_entity=closed`才通过；否则写失败`lark_check.json`并判`BLOCKED`，说明当前文档权限不符合私有合同。收紧权限必须先向用户展示具体文档与目标档位，取得本轮明确确认后另行执行，不能因默认交付要求私有就静默追加`--yes`。

只有用户明确授权“本次新建文档允许互联网获得链接者阅读”这一具体档位时，才可在本次make命令行显式传入`PUBLIC_LARK=1`，继承自环境的同名变量无效。该变量授权的唯一写入是`external_access=true`、`link_share_entity=anyone_readable`，Makefile可据此为高风险命令追加`--yes`；写入后仍须只读查询并验证实际档位。其他公开范围或可编辑权限不由该变量代表，必须单独确认。

飞书创建、权限设置/查询、读回或`check_lark.py`失败时，必须生成`status=fail`的`lark_check.json`并立即调用`status.py`输出三态，不能让Shell错误成为唯一结果。若飞书权限或登录阻塞，终稿`paper_final.md`仍在，但只能如实报告`BLOCKED`或`DRAFT_ONLY`，不得宣称最终完成。

## 三态交付口径

最终回答的完成状态由 `make status` 给出，你只如实转述：

- **PASS**：正文检查通过，且完成`output_target`要求的交付；`markdown_and_lark`还必须通过权限与读回校验。
- **BLOCKED**：卡在某阶段，说明卡点与 `next` 指令。
- **DRAFT_ONLY**：正文存在但检查未过或未交付，明确标注这是未验收草稿，禁止说“已完成”“已交付”。

## 可用脚本（由 Makefile 调用，你一般不用手动跑）

- `scripts/check_prepare.py`：校验meta字段与来源池，只统计核验状态为“已核验”且核验依据、URL齐全的条目。
- `scripts/check_draft.py`：正文形态检查，按学科分支切规则；未收到命令行覆盖时，根据`task_scope`与`paper_type`选择宽范围篇幅默认值。
- `scripts/check_lark.py`：飞书读回XML内容校验；权限由Makefile按同一失败报告结构验证并合并进`lark_check.json`。
- `scripts/status.py`：只读物理产物，输出三态结论。

脚本是强制门卫，论文的学术质量、论证对错、来源真伪仍由 `references/` 方法论与人工审查负责，脚本不替代判断。

## 深入参考（按任务读取）

主入口写作阶段已经指定的`../paper-shape/references/structure.md`与`../paper-shape/references/polish.md`分别在规划和语言收尾时必读。其余文件按当前任务读取：中文正文语言和章节落笔的专门细则看`references/writing-core/SKILL.md`、`references/writing-chapters/SKILL.md`、`references/evidence-driven-writing/SKILL.md`；学科范式看`references/stem/SKILL.md`或`references/hss/SKILL.md`，HSS任务再按需读取`references/hss/section-templates.md`、`references/hss/citation-policy-examples.md`、`references/hss/formatting-output.md`、`references/hss/journal-formats.md`、`references/hss/review-question-framing.md`、`references/hss/submission-checklist.md`；来源检索和综述合成看`references/literature-search/SKILL.md`与`references/literature-review/SKILL.md`。

基于用户已有或prepare阶段已核验来源撰写论文内文献综述、related work或review article属于本线；需要独立执行系统检索、纳排、去重、质量评价和证据综合时转`/doubao-literature-research`。
