# WorkBuddy / Skills 功能导航

本文件由 `scripts/sync_platform.py --platform workbuddy` 自动生成，是 `workbuddy/skills/` 下条目的使用导航。平台总索引见 [README-workbuddy.md](../../README-workbuddy.md)。

## 概览

- 目录：`workbuddy/skills/`
- 来源：`/mnt/c/Users/15805/.workbuddy/skills`
- 条目数：16
- 文件数：155
- 最近同步：2026-09-04 18:00:01 +0800

## 场景导航（按用途）

### 文档/表格/PPT
- **paper-rebuttal** — 以论文作者身份完成学术审稿 rebuttal 全流程。当用户提供审稿意见（reviewer comments / reviews / meta-review）和论文文件（PDF/LaTeX/DOCX/Markdown），需要分析审稿意见、判断是否需要修改论文、修改论文并撰写给审稿人的逐条回复（rebuttal / response letter / author response）时使用。触发词包括：rebuttal、审稿意见回复...
- **paper-reviewer** — 专业学术论文审稿 skill。以领域专家视角对学术论文（本地 PDF、arXiv ID/URL、粘贴文本）进行系统评审，自动识别论文学科与贡献类型并切换对应领域专家标准，输出顶会 OpenReview 风格（NeurIPS/ICLR/ICML）的标准 review 意见：Summary、Strengths、Weaknesses、Questions to Authors、Overall Score (1-10)、Confidence...

### 设计可视化
- **research-lineage-map** — 绘制研究领域或技术主题的谱系脉络与历史演进图，可视化思想的演化路径，展示早期工作中的技术难题如何被后续研究逐步解决。当用户想了解某个主题的发展轨迹、某个模型或技术的"家族树"（family tree）、某条研究线索在多年间的演进路线、技术迭代脉络、论文/模型谱系，或询问"X 是如何一步步发展来的""X 解决了前人的什么问题""梳理 X 的发展历史"时触发。产出为嵌入 Mermaid 图表的 Markdown 文件（演进图 + 节点...

### 研究/调研
- **arxiv-reader** — 利用python，指定某个arxiv_id/url， 基于 LLM Agent 对这篇arxiv论文进行分类与深度阅读，直接print打印阅读笔记
- **arxiv-watcher** — Search and summarize papers from ArXiv. Use when the user asks for the latest research, specific topics on ArXiv, or a daily summary of AI papers.
- **deep-research** — Structured deep research workflow with human-in-the-loop control. Use /research to generate research outline, /research-deep for parallel web search across items, /research-report to compile markdown reports. Supports...
- **paper-quick-reader** — AI 论文速读 Skill：三档深度（裸读 / 引导 / 精读）+ 页码级 Provenance 防幻觉 + 多篇对比。 触发词：论文速读、读这篇论文、抓核心观点、论文对比、多篇对比、与我研究方向的关联、 第几页提到 X、这篇论文的数据集怎么构造的、论文精读、 paper summary、summarize this paper、compare these papers、literature skim、extract method...
- **paper-reader** — 基于论文文本的通用读论文助手。用户提供论文文本（文件路径或直接粘贴），解答各类读论文需求——总结、精读、内容问答、概念解释、批判性分析等，并将结果以 Markdown 写入当前工作目录。触发词：读论文、论文总结、精读这篇论文、帮我分析这篇论文、这篇论文讲了什么、论文问答、论文笔记。输入为纯文本/Markdown 论文内容；不做论文检索下载、不做扫描件 OCR、不做论文写作降重。
- **paper-rebuttal** — 以论文作者身份完成学术审稿 rebuttal 全流程。当用户提供审稿意见（reviewer comments / reviews / meta-review）和论文文件（PDF/LaTeX/DOCX/Markdown），需要分析审稿意见、判断是否需要修改论文、修改论文并撰写给审稿人的逐条回复（rebuttal / response letter / author response）时使用。触发词包括：rebuttal、审稿意见回复...
- **paper-reviewer** — 专业学术论文审稿 skill。以领域专家视角对学术论文（本地 PDF、arXiv ID/URL、粘贴文本）进行系统评审，自动识别论文学科与贡献类型并切换对应领域专家标准，输出顶会 OpenReview 风格（NeurIPS/ICLR/ICML）的标准 review 意见：Summary、Strengths、Weaknesses、Questions to Authors、Overall Score (1-10)、Confidence...
- **research-lineage-map** — 绘制研究领域或技术主题的谱系脉络与历史演进图，可视化思想的演化路径，展示早期工作中的技术难题如何被后续研究逐步解决。当用户想了解某个主题的发展轨迹、某个模型或技术的"家族树"（family tree）、某条研究线索在多年间的演进路线、技术迭代脉络、论文/模型谱系，或询问"X 是如何一步步发展来的""X 解决了前人的什么问题""梳理 X 的发展历史"时触发。产出为嵌入 Mermaid 图表的 Markdown 文件（演进图 + 节点...

### 营销/内容运营
- **wechat-article-pro** — 微信公众号文章发布专业版。功能：1)联网搜索热点信息 2)AI生成微信公众号封面图 3)撰写3000-5000字深度文章 4)使用公众号AI配图功能自动生成并上传封面 5)参考刘润公众号风格写作 6)自动排版 7)不加话题标签

### 通用工具/平台
- **paper-reader** — 基于论文文本的通用读论文助手。用户提供论文文本（文件路径或直接粘贴），解答各类读论文需求——总结、精读、内容问答、概念解释、批判性分析等，并将结果以 Markdown 写入当前工作目录。触发词：读论文、论文总结、精读这篇论文、帮我分析这篇论文、这篇论文讲了什么、论文问答、论文笔记。输入为纯文本/Markdown 论文内容；不做论文检索下载、不做扫描件 OCR、不做论文写作降重。
- **skillhub-daily** — 'SkillHub 每日推荐 - 扫描 skillhub.cn 全站 Top100 + 7 大分类各 Top20（共 240 个 Skill），

### 其他
- **aihot** — AI HOT (aihot.virxact.com) 中文 AI 资讯查询 Skill。当用户想知道"今天 AI 圈有什么"、"AI 日报"、"AI HOT"、"AI 资讯"、"AI 热点"、"最近 AI"、"OpenAI/Anthropic/Google 最近发布了什么"、"AI hot today"、"AI news today"、"看一下 AI 行业动态"、"今天有什么大模型发布"、"昨天 AI 圈"、"看下精选条目"、"A...
- **ctrip-wendao** — 当用户发起任意旅行相关问询时，包含但不限于：预订酒店、机票查询、火车票查询、景点推荐、寻找当地特色玩乐、目的地查询、行程规划、美食住宿攻略、签证、查询旅游攻略、获取旅行建议等场景，自动触发此技能。当用户需要操作携程时使用此skill。
- **humanizer** — Remove signs of AI-generated writing from text. Use when editing or reviewing text to make it sound more natural and human-written. Detects and fixes patterns including: inflated symbolism, promotional language, super...
- **khazix-writer** — \|-
- **prompt-engineering-expert** — Advanced expert in prompt engineering, custom instructions design, and prompt optimization for AI agents
- **tencent-yuanbao-standard-search** — Search the web using TencentCloud Web Search API (WSA). Prioritize using it when you need to retrieve network information.

## 完整目录表

| 名称 | 目录 | 类型 | 关键词 | 文件数 | 说明 |
| --- | --- | --- | --- | ---: | --- |
| aihot | `workbuddy/skills/aihot__skillhub` | 其他 | aihot | 3 | AI HOT (aihot.virxact.com) 中文 AI 资讯查询 Skill。当用户想知道"今天 AI 圈有什么"、"AI 日报"、"AI HOT"、"AI 资讯"、"AI 热点"、"最近 AI"、"OpenAI/Anthropic/Google 最近发布了什么"、"AI hot today"、"AI news today"、"看一下 AI 行业动态"、"今天有什么大模型发布"、"昨天 AI 圈"、"看下精选条目"、"A... |
| arxiv-reader | `workbuddy/skills/arxiv-reader` | 研究/调研 | arxiv-reader | 42 | 利用python，指定某个arxiv_id/url， 基于 LLM Agent 对这篇arxiv论文进行分类与深度阅读，直接print打印阅读笔记 |
| arxiv-watcher | `workbuddy/skills/arxiv-watcher` | 研究/调研 | arxiv-watcher | 4 | Search and summarize papers from ArXiv. Use when the user asks for the latest research, specific topics on ArXiv, or a daily summary of AI papers. |
| ctrip-wendao | `workbuddy/skills/ctrip-wendao` | 其他 | ctrip-wendao | 4 | 当用户发起任意旅行相关问询时，包含但不限于：预订酒店、机票查询、火车票查询、景点推荐、寻找当地特色玩乐、目的地查询、行程规划、美食住宿攻略、签证、查询旅游攻略、获取旅行建议等场景，自动触发此技能。当用户需要操作携程时使用此skill。 |
| deep-research | `workbuddy/skills/deep-research` | 研究/调研 | deep-research | 21 | Structured deep research workflow with human-in-the-loop control. Use /research to generate research outline, /research-deep for parallel web search across items, /research-report to compile markdown reports. Supports... |
| humanizer | `workbuddy/skills/humanizer` | 其他 | humanizer | 3 | Remove signs of AI-generated writing from text. Use when editing or reviewing text to make it sound more natural and human-written. Detects and fixes patterns including: inflated symbolism, promotional language, super... |
| khazix-writer | `workbuddy/skills/khazix-writer` | 其他 | khazix-writer | 4 | \|- |
| paper-quick-reader | `workbuddy/skills/paper-quick-reader` | 研究/调研 | paper-quick-reader | 31 | AI 论文速读 Skill：三档深度（裸读 / 引导 / 精读）+ 页码级 Provenance 防幻觉 + 多篇对比。 触发词：论文速读、读这篇论文、抓核心观点、论文对比、多篇对比、与我研究方向的关联、 第几页提到 X、这篇论文的数据集怎么构造的、论文精读、 paper summary、summarize this paper、compare these papers、literature skim、extract method... |
| paper-reader | `workbuddy/skills/paper-reader` | 研究/调研 | paper-reader | 1 | 基于论文文本的通用读论文助手。用户提供论文文本（文件路径或直接粘贴），解答各类读论文需求——总结、精读、内容问答、概念解释、批判性分析等，并将结果以 Markdown 写入当前工作目录。触发词：读论文、论文总结、精读这篇论文、帮我分析这篇论文、这篇论文讲了什么、论文问答、论文笔记。输入为纯文本/Markdown 论文内容；不做论文检索下载、不做扫描件 OCR、不做论文写作降重。 |
| paper-rebuttal | `workbuddy/skills/paper-rebuttal` | 文档/表格/PPT | paper-rebuttal | 4 | 以论文作者身份完成学术审稿 rebuttal 全流程。当用户提供审稿意见（reviewer comments / reviews / meta-review）和论文文件（PDF/LaTeX/DOCX/Markdown），需要分析审稿意见、判断是否需要修改论文、修改论文并撰写给审稿人的逐条回复（rebuttal / response letter / author response）时使用。触发词包括：rebuttal、审稿意见回复... |
| paper-reviewer | `workbuddy/skills/paper-reviewer` | 文档/表格/PPT | paper-reviewer | 3 | 专业学术论文审稿 skill。以领域专家视角对学术论文（本地 PDF、arXiv ID/URL、粘贴文本）进行系统评审，自动识别论文学科与贡献类型并切换对应领域专家标准，输出顶会 OpenReview 风格（NeurIPS/ICLR/ICML）的标准 review 意见：Summary、Strengths、Weaknesses、Questions to Authors、Overall Score (1-10)、Confidence... |
| prompt-engineering-expert | `workbuddy/skills/prompt-engineering-expert` | 其他 | prompt-engineering-expert | 12 | Advanced expert in prompt engineering, custom instructions design, and prompt optimization for AI agents |
| research-lineage-map | `workbuddy/skills/research-lineage-map` | 设计可视化 | research-lineage-map | 4 | 绘制研究领域或技术主题的谱系脉络与历史演进图，可视化思想的演化路径，展示早期工作中的技术难题如何被后续研究逐步解决。当用户想了解某个主题的发展轨迹、某个模型或技术的"家族树"（family tree）、某条研究线索在多年间的演进路线、技术迭代脉络、论文/模型谱系，或询问"X 是如何一步步发展来的""X 解决了前人的什么问题""梳理 X 的发展历史"时触发。产出为嵌入 Mermaid 图表的 Markdown 文件（演进图 + 节点... |
| skillhub-daily | `workbuddy/skills/skillhub-daily` | 通用工具/平台 | skillhub-daily | 13 | 'SkillHub 每日推荐 - 扫描 skillhub.cn 全站 Top100 + 7 大分类各 Top20（共 240 个 Skill）， |
| tencent-yuanbao-standard-search | `workbuddy/skills/tencent-yuanbao-standard-search` | 其他 | tencent-yuanbao-standard-search | 4 | Search the web using TencentCloud Web Search API (WSA). Prioritize using it when you need to retrieve network information. |
| wechat-article-pro | `workbuddy/skills/wechat-article-pro` | 营销/内容运营 | wechat-article-pro | 2 | 微信公众号文章发布专业版。功能：1)联网搜索热点信息 2)AI生成微信公众号封面图 3)撰写3000-5000字深度文章 4)使用公众号AI配图功能自动生成并上传封面 5)参考刘润公众号风格写作 6)自动排版 7)不加话题标签 |
