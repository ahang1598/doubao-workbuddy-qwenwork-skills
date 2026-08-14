# 摘要关键词撰写与全篇整合审查指南

## 用途

本文件有两个用途。

第一，根据已经完成的论文部分撰写或修订 Abstract 和 Keywords。适用于用户已经提供或已经生成 introduction、literature review、theoretical framework、methodology、analysis/discussion、conclusion 等主体内容后，需要补写论文开头的摘要和关键词。

第二，当英文论文已经完成多个部分的撰写、重写、扩写或润色后，进行 final integration review。适用于完整 research paper、journal article、term paper、master's thesis、conference paper、proposal 或完整章节组合稿。

本文件不负责重新撰写 literature review、theoretical framework、methodology、analysis/discussion、conclusion 等具体主体章节，也不替代格式 sub-skill。它的任务是基于已完成内容生成论文前置部分，并检查整篇论文合并后是否像一篇完整论文，而不是几个单独生成的部分拼接在一起。

## 核心定位

本文件是全文完成后的前置部分撰写与质量门禁指南。当前格式合同要求Abstract或Keywords时，根据正文已有问题、方法、材料、发现和边界准确撰写；未要求时不添加。同时检查结构、逻辑、证据、章节职责、术语一致性、引用格式和输出规范。

需要撰写Abstract和Keywords时，应优先保证下列要求：

- Abstract 是全文压缩，而不是 Introduction 改写。
- Abstract 只使用正文已经支撑的信息，不编造 findings。
- Keywords数量服从当前格式合同；未规定时采用最少充分数量。
- Keywords 覆盖研究对象、理论/方法、研究情境和关键概念。
- 非英语术语和英文译名与全文保持一致。

执行整篇文章审查时，应优先修复下列问题：

- 各部分之间逻辑断裂。
- 章节职责错位。
- 同一内容在多个部分重复。
- 研究问题、理论框架、方法和分析无法对齐。
- 文献综述没有真正支撑研究空白。
- Methodology 写入了局限、意义、贡献或方法评价。
- Analysis 使用了 methodology 没有交代的数据、材料、变量或编码。
- Discussion 只是重复 findings，没有解释意义和阐述论文局限。
- Conclusion 引入新证据或重复摘要。

## 执行前提

开始撰写 Abstract 和 Keywords 或进行整合审查前，应确认下列信息：

- 论文类型和目标读者。
- 用户要求的是完整论文还是完整论文的局部组合稿。
- 指定引用格式；未指定时默认 APA 7，并读取 `format-guide.md`。
- 研究问题是否集中，默认围绕一个核心研究问题。
- 输出形式；用户指定文件格式时优先遵循用户指令，未指定时默认通过`lark-cli`输出飞书文档。
- 是否存在用户明确要求保留的结构、标题或内容。

本文件只处理已经进入 `paper-write-en` 的完整论文、多章节组合稿或实质性修订。此类任务不能只做语言润色，必须同步修复结构、逻辑、证据、格式和章节职责问题。用户只要求对已有文本做语法、行文、学术表达或中译英润色时，应转同级 `paper-shape`，不适用本条。

## 具体撰写与审查标准

### 全篇逻辑审查

整合后的论文必须形成一条清楚的学术链路，但不强制固定目录。Introduction引出研究问题；需要综述时由Literature review说明研究脉络；只有论文确实采用理论框架时才单列或合并Theoretical framework；Methodology说明研究如何执行；Analysis呈现材料或发现；需要解释时由Discussion处理意义与边界；Conclusion按证据收束。

- 全文应保留用户的研究主题和核心立场，除非用户要求重新设计题目。
- Introduction 应自然包含研究问题、选题原因和研究意义，但不应提前给出完整研究结论。不要把 `Research Question`、`Research Gap` 或 `Significance` 默认写成小标题；这些功能通常应融入正文推进。
- 如果论文需要单独交代 Context、Background、Doctrinal Background、Institutional Background、Case Background 或政策/历史语境，该部分必须位于 Introduction 之后、Literature Review 之前，并且只负责对象语境，不承担文献综述、理论框架或方法设计职责。
- Literature review 应综合相关领域研究，而不是按“一篇文献一个段落”罗列。它应展示研究之间的共识、分歧、方法差异、理论脉络和未解决问题，并自然导向本文定位。
- 只有当前论文需要Theoretical framework时，才说明理论选择、适配性、核心概念和操作化方式；纯测量、描述、工程实现、数据集或方法短文可省略独立理论框架。
- Methodology 只写研究如何执行。它可以说明 research design、corpus、sample、data source、selection criteria、coding、variables、analytical procedure、tools、validity/reliability/trustworthiness 和 ethics，**但不得讨论方法局限、研究局限、适用边界、推广限制、样本不足、数据不足、方法弱点、取舍评价或 future research**。相关内容只能放入 discussion 。
- Analysis、results 或 findings 只能使用 methodology、corpus 说明或数据呈现部分已经交代过的数据、材料、变量、编码、模型、实验或文本。普通文献型、概念型或政策文本研究在 methodology 说明来源、corpus 和筛选逻辑后可以直接进入 analysis；编码型、系统综述型、定量型、访谈/问卷/实验型、工程或数据科学研究应先呈现必要的数据结果、编码结果、样本结构、变量表、描述统计、材料分布或证据矩阵。
- Discussion 应解释 findings 的理论意义、经验意义、实践意义、政策意义、边界条件或局限。它不应只是重复 analysis，也不应引入没有在前文分析过的新证据。
- Conclusion 应综合全文核心贡献，回答研究问题，不引入新文献、新数据、新概念或复杂新论证。结论可以指出未来研究方向，但不应以自我贬损或大量局限讨论收尾。

### 事实核查

必须对整合后的论文进行全篇事实核查，避免出现事实性错误。核查时，可以进行联网搜索，通过权威期刊、学术数据库和主流媒体等信源，确认研究事实性内容的真实性。

其中，特别要注意以下几点：
- 引用文献必须真实存在，且引用内容的具体信息不得有误，包括作者姓名、文献名称、年份、卷号、期号、页码等，特别要注意页码、标号等细节处不得出现偏差。
- 涉及文献综述、理论探讨的，必须参照权威期刊、学术数据库的信息，对各类理论、学说、流派的学术观点和影响力进行准确恰当的描述，不得编造内容或夸大、贬低影响力。
- 必须核查所使用的实证证据的真实性，其中，涉及探究因果机制的，在确保证据真实性的基础上，还需要审查其推理链条是否合逻辑。

### Abstract 和 Keywords 撰写与回写

只有用户、作业、学校或目标期刊要求Abstract和keywords时才生成；需要时在全文主体完成后写作或最终修订，并检查其准确压缩全文。

Abstract的篇幅、结构和组件服从当前已核实模板；模板未规定时采用最小充分长度。只覆盖正文已有的问题、材料或方法、主要发现或中心判断及必要边界，不强制理论框架、贡献或实践意义。

若全文尚未形成明确 findings，不得编造研究结果。可以使用谨慎表述概括论文将如何论证，或标注需要根据最终 findings 回写；若是完整论文最终交付，应优先补足正文 findings 后再回写 abstract。

需要Keywords时按当前模板确定位置和数量；模板未规定时只保留最少充分的核心研究对象、方法或情境词，不设固定3至5个。

Keywords 不应把题目中的所有名词机械搬入，也应避免近义词重复。例如同一概念不要同时列 `discretionary admission`、`autonomous admission` 和 `independent enrollment`。若涉及非英语术语，应使用正文已经确定的统一英文译名；必要时可保留规范化的斜体拼音术语，但不要重复解释。

### 格式审查

格式、正文列表禁令、标题、非英语术语、表格和图、正文引用、References/Works Cited/Bibliography、输出格式，应读取并执行 `format-guide.md`。整合审查只判断这些规则是否已经落实，不在本文件重复展开格式细节。

### 数据、引用与证据审查

所有重要学术断言都应有合适引用支撑。不得编造作者、标题、期刊、DOI、URL、数据集、访谈、问卷结果、统计显著性或实验发现。只有`mode=draft`可保留清楚标注的模拟、假设、构造或占位数据；`mode=final`发现此类内容必须阻断。
需要确认文献已通过 `make prepare` 的验真门（见 `subskill/verification-guide.md`），只有进入 `.workflow/verified_refs.json` core_literature 的 A/B 级文献可留在正文。若整合阶段发现有正文引用的文献不在 verified_refs 里，必须**强制打回并联动修改**受影响的正文段落（如替换证据、重写论点），以保持全篇逻辑和证据链的完整性。

### 输出审查

1. 用户未指定输出格式时，按 `format-guide.md` 的输出格式规则处理。
2. 正式论文输出应是 polished academic English。用户用中文提问时，可以用中文简要说明修改情况，但论文正文应保持英文，除非用户明确要求中文或双语。
3. 输出时不要长篇解释写作过程。若用户要求的是最终论文，交付正文或文档链接即可；若用户要求的是审查报告，先列关键问题和修复建议，再给简短总结。

## 审查执行方式

本文件可以有两种执行方式。

如果任务是撰写 Abstract 和 Keywords，应先读取或概括已完成论文部分，提取研究背景、研究问题、理论框架或方法、数据/语料/案例/研究对象、主要 findings 或中心论点，以及意义。随后直接输出正式论文中的 Abstract 和 Keywords 两个部分，不要输出审查报告、思考过程、scope/source logic、高亮块或分割线。

如果任务是生成完整论文，应在最终交付前静默执行整合审查，并直接修复发现的问题。不要把审查过程写入论文正文。

如果任务是整篇文章审查或整合润色，应同时检查是否需要补写、压缩或重写 Abstract 和 Keywords，并将它们作为最终论文的一部分处理。

## 最终通过标准

一篇通过整合审查的论文应满足以下标准：

- 研究问题具体、集中且可回答。
- 研究空白来自文献和材料，而非主观宣称。
- 当前任务要求Abstract时，其准确压缩全文，不是introduction改写，不包含正文没有出现的新信息。
- 当前任务要求Keywords时，其数量符合格式合同，覆盖必要对象、方法或情境且不存在近义词堆叠。
- 实际存在的Abstract、keywords和introduction与全文一致。
- 当前论文实际使用的literature review、theoretical framework、methodology、analysis、discussion和conclusion等功能职责清楚；未触发的功能不为凑目录补写。
- Methodology 没有局限、贡献、意义或方法评价。
- Methodology 中没有任何 limitations、generalizability、weakness、future research、sample/data insufficiency 或方法取舍评价；这些内容如有必要只出现在 discussion 或 conclusion。
- Analysis 使用的数据、材料或证据在 methodology 或数据说明中已经交代。
- Discussion 解释发现的意义，并能处理局限或边界条件。
- Conclusion 不引入新证据。
- 已通过 `format-guide.md` 检查格式、正文呈现、非英语术语、表格、图和输出要求。
- 引用和 References 双向匹配且可验证。
- 用户未指定引用格式时，文末参考文献必须为 APA 7：标题为 `References`，不得使用 `Works Cited`、`Bibliography`、`Notes`、编号脚注列表、分章节参考文献清单或 MLA/Chicago 条目格式。
- 最终章节顺序服从 `paper-shape/references/structure.md` 推导的论证依赖以及用户或目标期刊模板。通用检查只要求方法先于其对应结果、结果先于解释、结论不先于主体证据、References位于正文之后；不强制Literature Review、Framework和Context采用唯一顺序。
- 输出产物符合用户指定文件格式；用户未指定输出文件格式时，已通过`lark-cli`生成或更新为飞书文档，并能向用户提供飞书文档链接或可定位文档信息。
