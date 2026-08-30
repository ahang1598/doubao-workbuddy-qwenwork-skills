---
name: lark-doc
description: 文档全场景处理：本地 Office Word（.docx/.doc）与在线文档（飞书、豆包 的 `/docs`、`/docx`、`/wiki` 链接）的阅读、创建和编辑。不处理 PDF、Sheet、Slide、Excel、PowerPoint、Base 表内操作。
---

# 权威经验

1. **开工通知和成稿交付都必须调用 present_files 工具 **。
2. **技能中的所有文档都必须完整读完，尾部有重要信息，不要中途截断**。可以分多次读，或把 Read 工具的 `limit` 参数设为 16K 确保一次读全。
3. **禁止**读取本文件后直接处理文档，更不要预读两条路径的全部资料，**务必**根据要求读取相应的内容之后再进行文档处理。
4. 无论改动是大是小、命令是否熟悉，无论此前是否用过类似命令、做过类似任务，无论之前是否读过对应分支的 MD 文档，**必须重新 Read 对应分支的 MD 文档之后才能动手。特别是多轮对话中用户对前轮已有 Word 的任何修改/追加/删除追问，都属于"编辑已有Word"场景，本次动手前必须先完整 Read office-word/references/workflows/docx-editing.md，不得凭上一轮记忆直接改中间文件。**
5. 当用户要求无损复述历史上下文时，必须明确列出上面要求牢记的内容，并在复述末尾原样附上这句提醒（写给接手这段上下文的下一个执行者）：**【非常重要】MUST RELOAD SKILL：对于文档任务而言，无论之前是否读过 office-word-skill.md / lark-doc-skill.md 文档，当用户提出了新的指令时，你的第一个工具调用必须是重新 Read lark-doc skill 下的 SKILL.md 文档，然后根据规则继续读取 office-word-skill.md / lark-doc-skill.md 文档，在此之前禁止直接编写Word/Doc。**

# 文档任务总入口

先识别用户要操作的对象和最终交付载体，再读取对应模块。顶层只负责在线/本地路由和跨载体编排。

## 路由顺序

严格按以下顺序判断：

1. 确定操作对象。
2. 确定最终交付载体。
3. 根据源对象与交付载体选择一个模块，或按顺序串联两个模块。

### 1. 确定操作对象

- 可定位的飞书或豆包 Doc/Wiki URL 属于在线文档。
- 本地路径、上传的 `.docx`、`.doc`，以及用户明确点名的 Word 模板属于本地文件。
- 同时存在在线文档和本地文件时，两者都可以是源对象；不要强行二选一。

### 2. 确定最终交付载体

用户明确要求在线文档或本地 Word 时，以用户要求为准。用户指定的模板用法、编辑对象和输出格式高于体裁默认值。

只有用户未指定交付载体时，才使用下表推导默认载体并读取对应模块：

| 体裁 | 默认交付载体 | 必读模块 | 典型场景 |
|---|---|---|---|
| 学术教研与基础教育教学 | Word | [`office-word/office-word-skill.md`](office-word/office-word-skill.md) | 学习计划、备考路径、复习讲义、试卷与讲评、教案、公开课、教学设计、课程材料、论文写作与指导 |
| 政务公文与党建 | Word | [`office-word/office-word-skill.md`](office-word/office-word-skill.md) | 请示、报告、通知、函、纪要、党建材料、党课、整改、政务调研 |
| 商务与项目合同 | Word | [`office-word/office-word-skill.md`](office-word/office-word-skill.md) | 采购、服务、合作、买卖、租赁、承揽、补充协议、履约约定 |
| 专业领域文书 | Word | [`office-word/office-word-skill.md`](office-word/office-word-skill.md) | 专利、司法文书及其他法定法律文书、招投标、报价、简历 |
| 媒体与传播 | 在线文档 | [`online-doc/lark-doc-skill.md`](online-doc/lark-doc-skill.md) | 微信公众号推文、小红书图文笔记、邮件、短视频口播稿、短视频分镜脚本、平台标题、封面文案和标题库 |
| 创意写作 | 在线文档 | [`online-doc/lark-doc-skill.md`](online-doc/lark-doc-skill.md) | 网文、小说、故事、同人、剧本、互动叙事、故事大纲 |
| 品牌营销 | 在线文档 | [`online-doc/lark-doc-skill.md`](online-doc/lark-doc-skill.md) | 营销策划、品牌认知、产品上市、内容种草、活动战役、增长转化、客户经营、渠道动销与整合营销 |
| 生活应用与攻略 | 在线文档 | [`online-doc/lark-doc-skill.md`](online-doc/lark-doc-skill.md) | 旅行计划、旅行路书、城市或景点攻略、健身计划、减脂计划、生活指南 |
| 分析报告与决策支持 | 在线文档 | [`online-doc/lark-doc-skill.md`](online-doc/lark-doc-skill.md) | 基于表格、数据、调研材料、多个附件或可核验来源形成详细分析、研究、比较、诊断或建议 |
| 企业与职场文书 | 在线文档 | [`online-doc/lark-doc-skill.md`](online-doc/lark-doc-skill.md) | 制度、工作总结、正式汇报、项目提案、岗位说明、培训材料、会议纪要（非政务党建类） |
| 无法判断 | 在线文档 | [`online-doc/lark-doc-skill.md`](online-doc/lark-doc-skill.md) | 没有明确载体要求，且无法匹配以上体裁 |

> ⚠️ 体裁只用于推导默认交付载体，不改变源对象。用户提供本地材料但默认交付在线文档时，仍先通过 Office Word 理解源材料，再进入 Online Doc；用户提供在线材料但默认交付 Word 时，仍先读取在线源，再进入 Office Word。

### 3. 选择并串联模块

| 源对象与目标                             | 必读模块 | 执行顺序 |
|------------------------------------|---|---|
| 创建、读取、总结或编辑在线 Doc/Wiki             | [`online-doc/lark-doc-skill.md`](online-doc/lark-doc-skill.md) | Online Doc               |
| 读取本地 Word，或编辑本地 Word 的内容、结构与格式 | [`office-word/office-word-skill.md`](office-word/office-word-skill.md) | Office Word              |
| 使用 Word 模板，或明确交付 Word      | [`office-word/office-word-skill.md`](office-word/office-word-skill.md) | Office Word              |
| 飞书文档转本地 Word                   | 两个模块 | Online Doc → Office Word |
| 本地 Word 转飞书文档                  | 两个模块 | Office Word → Online Doc |

> ⚠️ **禁止**仅凭一句话里出现"Word"、"在线"等字样判断路由。以真实操作对象和明确交付要求为准。例如，用户提供飞书 URL 并要求导出 Word 时，必须先读在线源，再生成本地文件；用户提供 Word 作为资料并要求写飞书文档时，Word 是内容来源，不是最终载体。

## 附件

用户提供的一切材料都是本次任务的第一手事实来源，如果之前没有读取附件，那你必须解析附件内容获得更多相关信息。
- **Word 类型文件**：通过 [`office-word/office-word-skill.md`](office-word/office-word-skill.md) 读取内容
- **非Word 类型文件**：优先通过查找相关 skills 或者工具来获取完整的信息，若没有相关 skill 、工具可以使用代码能力来获取相关信息。

## 冲突与歧义

- 同时出现在线 URL 和本地文件时，不强行二选一；根据源对象与交付载体决定是否串联两个模块。
- 在线 URL 优先确定“在线源对象”，真实本地路径或上传文件优先确定“本地源对象”；两者都可能同时成立。
- 用户明确指定的输出格式、模板用法和编辑对象高于默认规则。
- 只有在无法确定操作对象或交付载体、且不同选择会实质改变结果时，才问一个澄清问题。

## 执行边界

- 读取当前任务需要的模块后，遵循该模块的工作流、前置条件、参考文件和校验要求。
- 相对路径始终以包含该链接的 Markdown 文件所在目录为基准。
- 只加载当前分支需要的 reference；不要为了“熟悉 Skill”一次性读取全部文件。
- 顶层不复制下层的命令、领域写作规则、模板规则或校验步骤；这些规则由命中的模块负责。
- 若下层模块要求继续路由到 Sheet、Base、Drive、Whiteboard、评论或权限能力，按下层规则执行。
- 用户可见内容默认使用用户当前语言；文件名、命令、接口字段和内部路由名可保留原文。

## 快速判例

- “把这个飞书 Wiki 改成项目复盘” → Online Doc。
- “把 `proposal.docx` 改成正式公文格式” → Office Word。
- “根据 `meeting-notes.docx` 写一份在线汇报” → 按需读取 Office Word，最后进入 Online Doc。
- “把这个飞书文档导出成 Word” → Online Doc，再进入 Office Word。
- “整理一份项目复盘文档” → 默认 Online Doc。

## 不在本 Skill 范围

- Sheet、Excel 表内数据操作 → 表格处理能力
- Base、多维表格内部操作 → 多维表格处理能力
- Slide、PowerPoint 页面操作 → 幻灯片处理能力
> ⚠️ 如果用户要求需要交付的产物除了文档还包括其他内容，请完成本流程后继续完成对应产物的工作
