# 文章格式与正文呈现指南

## 用途

当英文论文需要确定或检查 APA 7、MLA 9、Chicago 18 格式，处理标题层级、正文呈现、表格、图、正文引用、References/Works Cited/Bibliography 或输出格式时，使用本文件。

本文件负责格式选择和正文呈现硬规则；具体引用条目、标题层级、表格和图的细节必须读取对应 reference 文件。

## 格式选择

用户未指定格式时，默认使用 APA 7，并读取 `../reference/apa7-format-guide.md`。

用户指定 MLA 9 时，读取 `../reference/mla9-format-guide.md`。

用户指定 Chicago 18 author-date 时，读取 `../reference/chicago18-format-guide.md` 的author-date部分。当前workflow未实现Chicago Notes门禁，不得选择notes体例。

不得在同一篇论文中混用 APA 7、MLA 9 和 Chicago 18，除非用户明确要求比较不同格式。若用户、学校、期刊或课程说明给出格式要求，以用户提供的要求优先，再用对应 reference 文件补足细节。

## 正文列表禁令

论文正文输出禁止使用有序列表或无序列表作为正文表达方式。除非用户、学校、期刊或特定格式明确要求，正文中不得出现 `1.`、`2.`、`-`、`*`、`•` 等列表结构，也不得出现“编号 + 加粗关键词 + 冒号解释”的工作文档式写法，例如 `1. **Official policy documents:** ...`。

需要呈现类别、数据来源、文献类型、变量、编码维度、分析步骤或比较信息时，应改写为连贯自然段，或使用符合 APA 7、MLA 9 或 Chicago 18 的表格。References 条目、表格编号、图编号和正式标题编号不属于此禁令。

该规则适用于 abstract、introduction、literature review、theoretical framework、methodology、analysis/results/findings、discussion 和 conclusion 的正式正文。内部写作计划、审查清单或用户明确要求的说明性输出可以使用列表，但不得把列表保留在论文正文中。

## 标题和章节

默认不使用 `Chapter 1`、`Chapter 2` 等机械章节标题，除非用户、学校、期刊或模板明确要求。正式论文应使用自然学术标题，如 `Introduction`、`Literature Review`、`Theoretical Framework`、`Methodology`、`Analysis`、`Discussion`、`Conclusion` 和 `References`，或更贴合主题的实质性标题。

不要把内部功能默认写成小标题，例如 `Research Question`、`Research Gap`、`Limitations`、`Significance`。这些功能通常应自然融入正文推进。若目标格式、学校模板或用户明确要求单列，则可以保留，但标题和内容仍应符合指定格式。

## 非英语术语

英文论文中必须出现非英语术语时，专有名词或制度化术语应按英语学术写作习惯首字母大写，例如 *Gaokao*。其他非英语专有名词同理；普通描述性词汇除非学科惯例要求，不随意大写。

非英语术语只解释一次，避免重复释义。优先使用清楚的首次出现格式，例如 `the National College Entrance Examination (*Gaokao*)` 或 `*Gaokao* (China's National College Entrance Examination)`。不要写成 `the national college entrance examination, or *Gaokao* (national college entrance examination)` 这类重复结构。

若论文涉及英语之外的语言，必须为关键术语确定一个英文译名，并在标题、abstract、keywords、标题层级、正文、表格、图注和参考文献说明中保持一致。除非确有分析必要并已解释区别，不要在同一概念之间来回切换近义译法。

## 表格和图

必要时使用表格或图让信息更清晰。此规则适用于所有学科：人文社科可以用表格或图呈现理论框架、政策时间线、案例选择、编码表、证据矩阵或比较发现；理工科、数据科学、医学和定量研究可以用表格或图呈现数据集、变量、模型架构、实验设计、统计结果、评估指标、稳健性检验、工作流程或模拟结果。

所有表格和图必须符合所用引用格式，未指定时按 APA 7。务必调用 `../reference/table-figure-guide.md`。

不要把表格或图放入正文后完全不讨论。

## 引用和参考文献

正文引用和文末条目必须双向匹配。正文出现的每个引用都应在 References、Works Cited 或 Bibliography 中有对应条目；文末每个条目都应被正文实际引用。当前门禁不支持selected bibliography；用户另要推荐书目时，将其作为论文正文之外的独立清单交付，不混入通过检查的论文文件。

用户未指定引用格式时，必须按 APA 7 输出正文引用和参考文献列表，并读取 `../reference/apa7-format-guide.md`。默认 APA 7 输出的文末标题必须是 `References`，不得使用 `Works Cited`、`Bibliography`、`Notes`、编号脚注列表、分章节参考文献清单或 MLA/Chicago 条目格式。APA 7 References 条目应至少符合作者、年份、标题、来源信息和 DOI/URL 等规则：作者名使用 initials，文章、章节、报告和网页标题使用 sentence case，期刊标题使用 title case；具体来源类型格式以 `../reference/apa7-format-guide.md` 为准。

所有重要学术断言都应有合适引用支撑。不得编造作者、标题、期刊、DOI、URL、数据集、访谈、问卷结果、统计显著性或实验发现。无法核查的来源应删除、替换或标注需要人工确认。

## 输出格式

正式论文正文、完整章节、章节组合稿或最终整合稿需要输出文件时，必须优先遵循用户明确指定的文件格式。若用户未指定输出文件格式，默认调用 `lark-cli` 生成或更新飞书文档，并以飞书文档作为正式交付物。`lark-cli` 仅用于最终飞书文档的创建、更新和交付，不用于生成论文中的表格或图。不得只在对话中输出完整正文作为最终交付。

论文中的表格和图必须继续遵守 `../reference/table-figure-guide.md` 的原有规则生成，再嵌入最终飞书文档；不得使用 `lark-cli` 的表格或图形功能生成论文表格、图。

用户要求 Word、Markdown、纯文本、PDF 或其他格式时，优先按用户指定格式输出，并按主 `SKILL.md` 的复合需求路由规则处理超出本 skill 范围的部分。如果用户未指定格式且当前环境无法调用 `lark-cli`，必须明确告知用户失败原因，且不得声称已经完成飞书文档输出。
