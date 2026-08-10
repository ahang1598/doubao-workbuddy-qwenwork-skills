# WorkBuddy / Skills 功能导航

本文件由 `scripts/sync_platform.py --platform workbuddy` 自动生成，是 `workbuddy/skills/` 下条目的使用导航。平台总索引见 [README-workbuddy.md](../../README-workbuddy.md)。

## 概览

- 目录：`workbuddy/skills/`
- 来源：`/mnt/c/Users/15805/.workbuddy/skills`
- 条目数：12
- 文件数：143
- 最近同步：2026-08-10 17:03:19 +0800

## 场景导航（按用途）

### 研究/调研
- **arxiv-reader** — 利用python，指定某个arxiv_id/url， 基于 LLM Agent 对这篇arxiv论文进行分类与深度阅读，直接print打印阅读笔记
- **arxiv-watcher** — Search and summarize papers from ArXiv. Use when the user asks for the latest research, specific topics on ArXiv, or a daily summary of AI papers.
- **deep-research** — Structured deep research workflow with human-in-the-loop control. Use /research to generate research outline, /research-deep for parallel web search across items, /research-report to compile markdown reports. Supports...
- **paper-quick-reader** — AI 论文速读 Skill：三档深度（裸读 / 引导 / 精读）+ 页码级 Provenance 防幻觉 + 多篇对比。 触发词：论文速读、读这篇论文、抓核心观点、论文对比、多篇对比、与我研究方向的关联、 第几页提到 X、这篇论文的数据集怎么构造的、论文精读、 paper summary、summarize this paper、compare these papers、literature skim、extract method...

### 营销/内容运营
- **wechat-article-pro** — 微信公众号文章发布专业版。功能：1)联网搜索热点信息 2)AI生成微信公众号封面图 3)撰写3000-5000字深度文章 4)使用公众号AI配图功能自动生成并上传封面 5)参考刘润公众号风格写作 6)自动排版 7)不加话题标签

### 通用工具/平台
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
| prompt-engineering-expert | `workbuddy/skills/prompt-engineering-expert` | 其他 | prompt-engineering-expert | 12 | Advanced expert in prompt engineering, custom instructions design, and prompt optimization for AI agents |
| skillhub-daily | `workbuddy/skills/skillhub-daily` | 通用工具/平台 | skillhub-daily | 13 | 'SkillHub 每日推荐 - 扫描 skillhub.cn 全站 Top100 + 7 大分类各 Top20（共 240 个 Skill）， |
| tencent-yuanbao-standard-search | `workbuddy/skills/tencent-yuanbao-standard-search` | 其他 | tencent-yuanbao-standard-search | 4 | Search the web using TencentCloud Web Search API (WSA). Prioritize using it when you need to retrieve network information. |
| wechat-article-pro | `workbuddy/skills/wechat-article-pro` | 营销/内容运营 | wechat-article-pro | 2 | 微信公众号文章发布专业版。功能：1)联网搜索热点信息 2)AI生成微信公众号封面图 3)撰写3000-5000字深度文章 4)使用公众号AI配图功能自动生成并上传封面 5)参考刘润公众号风格写作 6)自动排版 7)不加话题标签 |
