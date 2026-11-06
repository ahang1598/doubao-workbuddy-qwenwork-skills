# XiaoyiWork / Skills 功能导航

本文件由 `scripts/sync_platform.py --platform xiaoyiwork` 自动生成，是 `xiaoyiwork/skills/` 下条目的使用导航。平台总索引见 [README-xiaoyiwork.md](../../README-xiaoyiwork.md)。

## 概览

- 目录：`xiaoyiwork/skills/`
- 来源：`/mnt/c/Users/15805/AppData/Roaming/xiaoyiwork/users/c50060f363c95837/xiaoyiwork/agent/workspace/skills`
- 条目数：33
- 文件数：598
- 最近同步：2026-11-06 12:07:45 +0800

## 场景导航（按用途）

### 金融研究
- **imap-smtp-email-win** — Read and send email via IMAP/SMTP. Check for new/unread messages, fetch content, search mailboxes, mark as read/unread, and send emails with attachments. Supports multiple accounts. Works with any IMAP/SMTP server inc...
- **xiaoyi-deep-research-win** — 用户出现以下任一情况时,立即读入本skill: (1)消息中出现"深度研究" 和 "deep research"这两个关键词 (2)提出以下类型的问题(即使你觉得自己能回答,也要读入skill): - 技术选型、方案对比(如"X和Y怎么选") - 行业调研、市场格局(如"某赛道有哪些玩家") - 投资、财务、政策分析判断(如"某板块值不值得配置") - 学术研究现状、文献综述(如"某方向研究进展如何") - 竞品调研、产品对标(如...

### 文档/表格/PPT
- **aigc-marker-win** — 为 Windows 小艺 Work 中已存在的 OOXML 文档与模板、UOF、PDF、OFD、Markdown、XMind、POSM/POSF、HTML、图片、音频和视频文件添加 AIGC 显式标识与隐式元数据。其他生成型 Skill 要求添加 AIGC 标识，或用户要求“添加 AI 生成标识”“添加 AIGC 标签”时使用。
- **dock-workbench-win** — 小艺Work 工作台插件访问工具：读取/操作右侧工作台当前任务里的页签内容——文件预览页签中用户拾取的元素（inspect：单元格/段落/图表引用）、页签清单（state：文件/表格/幻灯/网页标签概览）。当用户消息尾部出现「工作台元素」上下文块（用户在文件/表格/文档中拾取了元素）、或需要查询任务里打开的文件页签内容时使用。触发关键词：工作台、文件页签、拾取元素、单元格、选中内容、页签列表。浏览器页签的打开/点击/表单操作请用...
- **global-biblio-base** — 全球12亿文献知识库（8千万中文期刊可下载）——通过 SmartLib 开放平台 API 提供中外文学术文献检索与下载能力，覆盖 8000 万篇授权中文期刊全文 + 12.28 亿条全球文献元数据（期刊 7.19 亿 / 专利 2.15 亿 / 会议 7155 万 / 学位论文 2473 万 / 标准 268 万）。 能力：中英文关键词检索、文献详情、中文期刊 PDF 全文下载、外文 OA 文献十级渠道免费下载（不消耗配额）、智能...
- **markitdown-win** — Convert files and office documents to Markdown. Supports PDF, DOCX, PPTX, XLSX, images (with OCR), audio (with transcription), HTML, CSV, JSON, XML, ZIP, YouTube URLs, EPubs and more.
- **xiaoyi-doc-convert-win** — 文档格式综合转换技能。 适用情形：处理 Word(doc/docx)、PowerPoint(ppt/pptx)、Excel(xls/xlsx)、PDF、Markdown(md) 及 HTML 之间的相互转换。 当用户意图涉及“格式转换”或明确的转换指令（如“docx转pdf”、“md转word”、“网页转ppt”、“excel转pdf”等）时必须触发。支持单文件与批量处理，系统会自动识别各类格式的中英文及扩展名别名。 不适用情形：...
- **xiaoyi-docx-win** — Use this skill whenever you need to create, modify, or generate Word documents (.docx). This includes writing reports, creating formatted documents, generating tables, adding Table of Contents, handling Chinese/CJK fo...
- **xiaoyi-pdf-win** — PDF 综合处理技能，处理文档生成、编辑、安全与解析。 适用情形： 1. 创建与排版：从零生成报告、提案、简历等 PDF，或对现有文档重新排版美化； 2. 表单与水印：自动填写 PDF 表单字段，或添加文字/图片水印（如打水印、标机密）； 3. 页面管理：合并多个 PDF，或拆分、提取指定页码； 4. 安全控制：为 PDF 添加密码（加密）或移除密码（解密）； 5. 内容提取：从 PDF 中提取纯文本或导出表格数据。 只要用户诉求...
- **xiaoyi-ppt-win** — PPT/幻灯片综合处理技能，支持演示文稿的从零生成与现有文件的直接编辑。 适用情形： 1. 新建 PPT：根据给定的主题、上传的文档或网络检索内容，规划大纲并生成完整幻灯片； 2. 编辑 PPT：对已有的 PPTX 文件进行修改，包括调整排版、修改文本、增删与重排页面； 3. 模板套用：基于用户提供的模板 PPT 文件填入新内容。 只要用户意图涉及“做PPT”、“生成幻灯片”、“修改演示文稿”或“排版PPT”时必须触发。
- **xiaoyi-xlsx-win** — Create, edit, or fix spreadsheet files (.xlsx/.xlsm/.csv/.tsv). Trigger whenever the task produces or modifies a spreadsheet — even if the user never says 'Excel'. Covers: data analysis, sorting, filtering, pivot summ...

### 设计可视化
- **dock-workbench-win** — 小艺Work 工作台插件访问工具：读取/操作右侧工作台当前任务里的页签内容——文件预览页签中用户拾取的元素（inspect：单元格/段落/图表引用）、页签清单（state：文件/表格/幻灯/网页标签概览）。当用户消息尾部出现「工作台元素」上下文块（用户在文件/表格/文档中拾取了元素）、或需要查询任务里打开的文件页签内容时使用。触发关键词：工作台、文件页签、拾取元素、单元格、选中内容、页签列表。浏览器页签的打开/点击/表单操作请用...
- **xiaoyi-image-understanding-win** — 使用小艺图像理解API进行图像内容识别和描述，获取图像的详细文本描述。当用户需要分析图片内容、识别图像中的物体、场景理解、提取图像信息、图像问答、OCR文字识别、图表分析等任务时使用此技能。

### 研究/调研
- **aminer-data-search** — ACADEMIC PRIORITY: Activate this skill whenever the user's query involves academic, scholarly, or research-related topics — including but not limited to: papers, publications, citations, scholars, researchers, profess...
- **arxiv-search** — Search arXiv preprint repository for papers in physics, mathematics, computer science, quantitative biology, and related fields, Instructions for searching arXiv papers using Python script and shell tool. Read SKILL.m...
- **global-biblio-base** — 全球12亿文献知识库（8千万中文期刊可下载）——通过 SmartLib 开放平台 API 提供中外文学术文献检索与下载能力，覆盖 8000 万篇授权中文期刊全文 + 12.28 亿条全球文献元数据（期刊 7.19 亿 / 专利 2.15 亿 / 会议 7155 万 / 学位论文 2473 万 / 标准 268 万）。 能力：中英文关键词检索、文献详情、中文期刊 PDF 全文下载、外文 OA 文献十级渠道免费下载（不消耗配额）、智能...
- **read-arxiv-paper** — Use this skill when when asked to read an arxiv paper given an arxiv URL
- **paper-daily** — 搜索顶会顶刊最新论文，跟踪引用数变化，总结并上传 GitHub
- **xiaoyi-deep-research-win** — 用户出现以下任一情况时,立即读入本skill: (1)消息中出现"深度研究" 和 "deep research"这两个关键词 (2)提出以下类型的问题(即使你觉得自己能回答,也要读入skill): - 技术选型、方案对比(如"X和Y怎么选") - 行业调研、市场格局(如"某赛道有哪些玩家") - 投资、财务、政策分析判断(如"某板块值不值得配置") - 学术研究现状、文献综述(如"某方向研究进展如何") - 竞品调研、产品对标(如...
- **xiaoyi-report-win** — 从多源信息生成带引用的专业分析报告。当用户要求研究、调研、调查、分析某个主题，或需要搜索资料、收集信息时使用。支持学术研究、市场调研、竞品分析、技术调研、深度研究。相关请求示例：'帮我调研XXX'、'帮我分析XXX'、'写一份关于XXX的深度研究报告'、'深度分析XXX'。任务完成后主动将生成的HTML报告文件通过channel发送给用户查看。

### 营销/内容运营
- **seedance-video-gen-win** — 小艺视频创作，基于Seedance 2.0 mini实现视频生成。支持文本、图片、音频、视频多模态参考输入，可生成、编辑、延长4-15秒视频。适用于短视频创作、剧情片段、动画短片、电商产品展示等场景。触发词：生成视频、做视频、视频创作、小艺视频、续写视频、text-to-video、image-to-video。

### 协作/办公
- **xiaoyi-self-evolution-win** — 当用户要求小艺改变未来做事方式、工具选择、执行流程、项目规则或交付标准时，必须使用本技能并先审批后固化。未明确作用域时，必须让用户选择当前项目或用户全局，不得默认全局；有 ask_user 工具时必须调用。命中“记住”“请记住”“以后都这样做”“下次应该”“注意”“固化为规则”等表达，且内容是可执行行为规则或可复用经验时，必须优先于 celia_memory_store，禁止直接回复“已记住”。仅记录姓名、生日等个人事实时不使用本技能。

### 法务/合规
- **expert-manager-win** — 创建或更新 jiuwenswarm 专家/专家团文件包。当用户想要一个具备特定专长的 agent（例如"文案专家"、"数据分析专家"），或希望把现成材料改造成可复用的专家包时使用。触发词：创建专家、创建专家团、转化专家、生成专家包、导入专家、修改专家、检查专家包、专家合规。
- **global-biblio-base** — 全球12亿文献知识库（8千万中文期刊可下载）——通过 SmartLib 开放平台 API 提供中外文学术文献检索与下载能力，覆盖 8000 万篇授权中文期刊全文 + 12.28 亿条全球文献元数据（期刊 7.19 亿 / 专利 2.15 亿 / 会议 7155 万 / 学位论文 2473 万 / 标准 268 万）。 能力：中英文关键词检索、文献详情、中文期刊 PDF 全文下载、外文 OA 文献十级渠道免费下载（不消耗配额）、智能...

### 代码开发
- **paper-daily** — 搜索顶会顶刊最新论文，跟踪引用数变化，总结并上传 GitHub

### 通用工具/平台
- **cloud-drive-win** — 华为云空间云盘文件管理工具，支持文件上传、文件下载、创建文件夹、文件列表查询、云空间用量查询和文件存在性检查。当 AgentBot 需要处理云盘相关操作时使用，包括：(1) 将本地文件上传到云盘"小艺Work"目录，(2) 查询云盘文件列表和文件信息，(3) 查询云空间总空间、已用空间和可用空间，(4) 检查云盘是否存在指定文件。触发关键词：华为云空间、云空间、华为云盘、云盘、云空间云盘、文件上传、文件查询、备份文件。
- **dock-workbench-win** — 小艺Work 工作台插件访问工具：读取/操作右侧工作台当前任务里的页签内容——文件预览页签中用户拾取的元素（inspect：单元格/段落/图表引用）、页签清单（state：文件/表格/幻灯/网页标签概览）。当用户消息尾部出现「工作台元素」上下文块（用户在文件/表格/文档中拾取了元素）、或需要查询任务里打开的文件页签内容时使用。触发关键词：工作台、文件页签、拾取元素、单元格、选中内容、页签列表。浏览器页签的打开/点击/表单操作请用...
- **find-skills-win** — 主动或者被动的帮用户查询或者安装agent skill。只要出现用户提出的任务目标超出了当前已安装工具的能力范围时（主动查询）；或者用户明确要求查找、安装 Skill 时（被动查询）就一定需要使用本skill。
- **global-biblio-base** — 全球12亿文献知识库（8千万中文期刊可下载）——通过 SmartLib 开放平台 API 提供中外文学术文献检索与下载能力，覆盖 8000 万篇授权中文期刊全文 + 12.28 亿条全球文献元数据（期刊 7.19 亿 / 专利 2.15 亿 / 会议 7155 万 / 学位论文 2473 万 / 标准 268 万）。 能力：中英文关键词检索、文献详情、中文期刊 PDF 全文下载、外文 OA 文献十级渠道免费下载（不消耗配额）、智能...
- **markitdown-win** — Convert files and office documents to Markdown. Supports PDF, DOCX, PPTX, XLSX, images (with OCR), audio (with transcription), HTML, CSV, JSON, XML, ZIP, YouTube URLs, EPubs and more.
- **skill-creator-win** — Create or update AgentSkills. Use when designing, structuring, or packaging skills with scripts, references, and assets.
- **xiaoyi-self-evolution-win** — 当用户要求小艺改变未来做事方式、工具选择、执行流程、项目规则或交付标准时，必须使用本技能并先审批后固化。未明确作用域时，必须让用户选择当前项目或用户全局，不得默认全局；有 ask_user 工具时必须调用。命中“记住”“请记住”“以后都这样做”“下次应该”“注意”“固化为规则”等表达，且内容是可执行行为规则或可复用经验时，必须优先于 celia_memory_store，禁止直接回复“已记住”。仅记录姓名、生日等个人事实时不使用本技能。

### 其他
- **aihot** — AI HOT (aihot.virxact.com) 中文 AI 资讯查询 Skill。当用户想知道"今天 AI 圈有什么"、"AI 日报"、"AI HOT"、"AI 资讯"、"AI 热点"、"最近 AI"、"OpenAI/Anthropic/Google 最近发布了什么"、"AI hot today"、"AI news today"、"看一下 AI 行业动态"、"今天有什么大模型发布"、"昨天 AI 圈"、"看下精选条目"、"A...
- **article-writer** — 文章写作助手 - 根据选题生成高质量文章
- **minimax-music-gen-win** — 基于 MiniMax Music3.0 的音乐生成技能。当用户想要生成音乐、歌曲、音频时使用。 触发词包括："生成歌曲"、"写首歌"、"创作音乐"、"来一首歌"、"帮我做首歌"、 "生成歌词"、"写歌词" 等任何与音乐创作相关的请求。 也适用于用户已有歌词希望将其转化为歌曲，或描述场景/情绪想要背景音乐的场景。 即使是随意的请求如 "给我来点音乐" 或 "I want a chill beat" 也应触发此技能。 不用于：播放已有...
- **writing-inspiration** — Use when user needs help starting or continuing writing (not diary). Triggers include「不知道写什么」「帮我构思」「写游记」「记录 TIL」「写点什么」. For diary writing, use diary-assistant instead.
- **seedream-image-gen-win** — 
- **xiaoyi-HarmonyOSSmartHome-skill-win** — 鸿蒙智家家庭技能集合，支持房间数量查询、房间设备查询、设备查询、消息告警、控制记录、家庭信息、设备控制、路由器管理、门锁和智慧屏、智能购物顾问、宠物照护、车辆信息查询、意图场景联动控制、场景习惯记忆记录等全家智能管家服务。也适用于"家庭简报"、"家里怎么样"、"今天家里有什么状况"、"家里发生了什么"、"家里网络状态"、"摄像头/传感器报警"等家庭状态查询场景，以及"想买家电"等购物需求和用户表达生活方式意图（睡觉、起床、出门、回...
- **xiaoyi-health-cli-index** — 查询个人运动健康相关数据，提供分析解读。覆盖领域：心率、静息心率、HRV、心律（房颤/早搏）、血压；睡眠时长/阶段/质量、午睡；步数、活动量、锻炼时长、运动记录（跑步/骑行/健身）、VO2Max、体能趋势、训练负荷、恢复状态；压力、情绪、焦虑、倦怠；血氧（SpO2）；血糖、餐后血糖；体温、发烧；体重、BMI、体脂率；营养摄入、饮食热量；月经周期、经期、基础体温（BBT）、排卵；今日健康概览、每周健康总结；体重管理、减脂、增肌；饮食...
- **xiaoyi-image-search-win** — 图片搜索技能。支持搜索图片并直接下载到本地临时目录，返回本地路径而非URL链接。适用于为文档、PPT、报告等场景查找配图素材。
- **xiaoyi-vlog-gen-win** — 一键成片、vlog制作，支持批量导入多张图片，智能画面编排、自动匹配氛围感BGM、添加流畅转场与创意特效，一键渲染生成精美vlog短片。触发词：一键成片、vlog、照片剪辑、多图成片、图库生成视频。
- **xiaoyi-web-search-win** — 使用华为云AI联网搜索API进行网页内容检索，获取实时网络信息

## 完整目录表

| 名称 | 目录 | 类型 | 关键词 | 文件数 | 说明 |
| --- | --- | --- | --- | ---: | --- |
| aigc-marker-win | `xiaoyiwork/skills/aigc-marker-win` | 文档/表格/PPT | aigc-marker-win | 66 | 为 Windows 小艺 Work 中已存在的 OOXML 文档与模板、UOF、PDF、OFD、Markdown、XMind、POSM/POSF、HTML、图片、音频和视频文件添加 AIGC 显式标识与隐式元数据。其他生成型 Skill 要求添加 AIGC 标识，或用户要求“添加 AI 生成标识”“添加 AIGC 标签”时使用。 |
| aihot | `xiaoyiwork/skills/aihot` | 其他 | aihot | 4 | AI HOT (aihot.virxact.com) 中文 AI 资讯查询 Skill。当用户想知道"今天 AI 圈有什么"、"AI 日报"、"AI HOT"、"AI 资讯"、"AI 热点"、"最近 AI"、"OpenAI/Anthropic/Google 最近发布了什么"、"AI hot today"、"AI news today"、"看一下 AI 行业动态"、"今天有什么大模型发布"、"昨天 AI 圈"、"看下精选条目"、"A... |
| aminer-data-search | `xiaoyiwork/skills/aminer-data-search` | 研究/调研 | aminer-data-search | 6 | ACADEMIC PRIORITY: Activate this skill whenever the user's query involves academic, scholarly, or research-related topics — including but not limited to: papers, publications, citations, scholars, researchers, profess... |
| article-writer | `xiaoyiwork/skills/article-writer` | 其他 | article-writer | 3 | 文章写作助手 - 根据选题生成高质量文章 |
| arxiv-search | `xiaoyiwork/skills/arxiv-search` | 研究/调研 | arxiv-search | 3 | Search arXiv preprint repository for papers in physics, mathematics, computer science, quantitative biology, and related fields, Instructions for searching arXiv papers using Python script and shell tool. Read SKILL.m... |
| cloud-drive-win | `xiaoyiwork/skills/cloud-drive-win` | 通用工具/平台 | cloud-drive-win | 9 | 华为云空间云盘文件管理工具，支持文件上传、文件下载、创建文件夹、文件列表查询、云空间用量查询和文件存在性检查。当 AgentBot 需要处理云盘相关操作时使用，包括：(1) 将本地文件上传到云盘"小艺Work"目录，(2) 查询云盘文件列表和文件信息，(3) 查询云空间总空间、已用空间和可用空间，(4) 检查云盘是否存在指定文件。触发关键词：华为云空间、云空间、华为云盘、云盘、云空间云盘、文件上传、文件查询、备份文件。 |
| dock-workbench-win | `xiaoyiwork/skills/dock-workbench-win` | 文档/表格/PPT | dock-workbench-win | 3 | 小艺Work 工作台插件访问工具：读取/操作右侧工作台当前任务里的页签内容——文件预览页签中用户拾取的元素（inspect：单元格/段落/图表引用）、页签清单（state：文件/表格/幻灯/网页标签概览）。当用户消息尾部出现「工作台元素」上下文块（用户在文件/表格/文档中拾取了元素）、或需要查询任务里打开的文件页签内容时使用。触发关键词：工作台、文件页签、拾取元素、单元格、选中内容、页签列表。浏览器页签的打开/点击/表单操作请用... |
| expert-manager-win | `xiaoyiwork/skills/expert-manager-win` | 法务/合规 | expert-manager-win | 22 | 创建或更新 jiuwenswarm 专家/专家团文件包。当用户想要一个具备特定专长的 agent（例如"文案专家"、"数据分析专家"），或希望把现成材料改造成可复用的专家包时使用。触发词：创建专家、创建专家团、转化专家、生成专家包、导入专家、修改专家、检查专家包、专家合规。 |
| find-skills-win | `xiaoyiwork/skills/find-skills-win` | 通用工具/平台 | find-skills-win | 7 | 主动或者被动的帮用户查询或者安装agent skill。只要出现用户提出的任务目标超出了当前已安装工具的能力范围时（主动查询）；或者用户明确要求查找、安装 Skill 时（被动查询）就一定需要使用本skill。 |
| global-biblio-base | `xiaoyiwork/skills/global-biblio-base` | 文档/表格/PPT | global-biblio-base | 9 | 全球12亿文献知识库（8千万中文期刊可下载）——通过 SmartLib 开放平台 API 提供中外文学术文献检索与下载能力，覆盖 8000 万篇授权中文期刊全文 + 12.28 亿条全球文献元数据（期刊 7.19 亿 / 专利 2.15 亿 / 会议 7155 万 / 学位论文 2473 万 / 标准 268 万）。 能力：中英文关键词检索、文献详情、中文期刊 PDF 全文下载、外文 OA 文献十级渠道免费下载（不消耗配额）、智能... |
| imap-smtp-email-win | `xiaoyiwork/skills/imap-smtp-email-win` | 金融研究 | imap-smtp-email-win | 9 | Read and send email via IMAP/SMTP. Check for new/unread messages, fetch content, search mailboxes, mark as read/unread, and send emails with attachments. Supports multiple accounts. Works with any IMAP/SMTP server inc... |
| markitdown-win | `xiaoyiwork/skills/markitdown-win` | 文档/表格/PPT | markitdown-win | 10 | Convert files and office documents to Markdown. Supports PDF, DOCX, PPTX, XLSX, images (with OCR), audio (with transcription), HTML, CSV, JSON, XML, ZIP, YouTube URLs, EPubs and more. |
| minimax-music-gen-win | `xiaoyiwork/skills/minimax-music-gen-win` | 其他 | minimax-music-gen-win | 8 | 基于 MiniMax Music3.0 的音乐生成技能。当用户想要生成音乐、歌曲、音频时使用。 触发词包括："生成歌曲"、"写首歌"、"创作音乐"、"来一首歌"、"帮我做首歌"、 "生成歌词"、"写歌词" 等任何与音乐创作相关的请求。 也适用于用户已有歌词希望将其转化为歌曲，或描述场景/情绪想要背景音乐的场景。 即使是随意的请求如 "给我来点音乐" 或 "I want a chill beat" 也应触发此技能。 不用于：播放已有... |
| writing-inspiration | `xiaoyiwork/skills/nini-writing-inspiration` | 其他 | writing-inspiration | 4 | Use when user needs help starting or continuing writing (not diary). Triggers include「不知道写什么」「帮我构思」「写游记」「记录 TIL」「写点什么」. For diary writing, use diary-assistant instead. |
| read-arxiv-paper | `xiaoyiwork/skills/read-arxiv-paper` | 研究/调研 | read-arxiv-paper | 2 | Use this skill when when asked to read an arxiv paper given an arxiv URL |
| seedance-video-gen-win | `xiaoyiwork/skills/seedance-video-gen-win` | 营销/内容运营 | seedance-video-gen-win | 7 | 小艺视频创作，基于Seedance 2.0 mini实现视频生成。支持文本、图片、音频、视频多模态参考输入，可生成、编辑、延长4-15秒视频。适用于短视频创作、剧情片段、动画短片、电商产品展示等场景。触发词：生成视频、做视频、视频创作、小艺视频、续写视频、text-to-video、image-to-video。 |
| seedream-image-gen-win | `xiaoyiwork/skills/seedream-image-gen-win` | 其他 | seedream-image-gen-win | 6 |  |
| skill-creator-win | `xiaoyiwork/skills/skill-creator-win` | 通用工具/平台 | skill-creator-win | 8 | Create or update AgentSkills. Use when designing, structuring, or packaging skills with scripts, references, and assets. |
| paper-daily | `xiaoyiwork/skills/su-lan-paper-daily-skill` | 研究/调研 | paper-daily | 2 | 搜索顶会顶刊最新论文，跟踪引用数变化，总结并上传 GitHub |
| xiaoyi-HarmonyOSSmartHome-skill-win | `xiaoyiwork/skills/xiaoyi-HarmonyOSSmartHome-skill-win` | 其他 | xiaoyi-HarmonyOSSmartHome-skill-win | 84 | 鸿蒙智家家庭技能集合，支持房间数量查询、房间设备查询、设备查询、消息告警、控制记录、家庭信息、设备控制、路由器管理、门锁和智慧屏、智能购物顾问、宠物照护、车辆信息查询、意图场景联动控制、场景习惯记忆记录等全家智能管家服务。也适用于"家庭简报"、"家里怎么样"、"今天家里有什么状况"、"家里发生了什么"、"家里网络状态"、"摄像头/传感器报警"等家庭状态查询场景，以及"想买家电"等购物需求和用户表达生活方式意图（睡觉、起床、出门、回... |
| xiaoyi-deep-research-win | `xiaoyiwork/skills/xiaoyi-deep-research-win` | 金融研究 | xiaoyi-deep-research-win | 16 | 用户出现以下任一情况时,立即读入本skill: (1)消息中出现"深度研究" 和 "deep research"这两个关键词 (2)提出以下类型的问题(即使你觉得自己能回答,也要读入skill): - 技术选型、方案对比(如"X和Y怎么选") - 行业调研、市场格局(如"某赛道有哪些玩家") - 投资、财务、政策分析判断(如"某板块值不值得配置") - 学术研究现状、文献综述(如"某方向研究进展如何") - 竞品调研、产品对标(如... |
| xiaoyi-doc-convert-win | `xiaoyiwork/skills/xiaoyi-doc-convert-win` | 文档/表格/PPT | xiaoyi-doc-convert-win | 53 | 文档格式综合转换技能。 适用情形：处理 Word(doc/docx)、PowerPoint(ppt/pptx)、Excel(xls/xlsx)、PDF、Markdown(md) 及 HTML 之间的相互转换。 当用户意图涉及“格式转换”或明确的转换指令（如“docx转pdf”、“md转word”、“网页转ppt”、“excel转pdf”等）时必须触发。支持单文件与批量处理，系统会自动识别各类格式的中英文及扩展名别名。 不适用情形：... |
| xiaoyi-docx-win | `xiaoyiwork/skills/xiaoyi-docx-win` | 文档/表格/PPT | xiaoyi-docx-win | 8 | Use this skill whenever you need to create, modify, or generate Word documents (.docx). This includes writing reports, creating formatted documents, generating tables, adding Table of Contents, handling Chinese/CJK fo... |
| xiaoyi-health-cli-index | `xiaoyiwork/skills/xiaoyi-health-win` | 其他 | xiaoyi-health-cli-index | 20 | 查询个人运动健康相关数据，提供分析解读。覆盖领域：心率、静息心率、HRV、心律（房颤/早搏）、血压；睡眠时长/阶段/质量、午睡；步数、活动量、锻炼时长、运动记录（跑步/骑行/健身）、VO2Max、体能趋势、训练负荷、恢复状态；压力、情绪、焦虑、倦怠；血氧（SpO2）；血糖、餐后血糖；体温、发烧；体重、BMI、体脂率；营养摄入、饮食热量；月经周期、经期、基础体温（BBT）、排卵；今日健康概览、每周健康总结；体重管理、减脂、增肌；饮食... |
| xiaoyi-image-search-win | `xiaoyiwork/skills/xiaoyi-image-search-win` | 其他 | xiaoyi-image-search-win | 7 | 图片搜索技能。支持搜索图片并直接下载到本地临时目录，返回本地路径而非URL链接。适用于为文档、PPT、报告等场景查找配图素材。 |
| xiaoyi-image-understanding-win | `xiaoyiwork/skills/xiaoyi-image-understanding-win` | 设计可视化 | xiaoyi-image-understanding-win | 7 | 使用小艺图像理解API进行图像内容识别和描述，获取图像的详细文本描述。当用户需要分析图片内容、识别图像中的物体、场景理解、提取图像信息、图像问答、OCR文字识别、图表分析等任务时使用此技能。 |
| xiaoyi-pdf-win | `xiaoyiwork/skills/xiaoyi-pdf-win` | 文档/表格/PPT | xiaoyi-pdf-win | 47 | PDF 综合处理技能，处理文档生成、编辑、安全与解析。 适用情形： 1. 创建与排版：从零生成报告、提案、简历等 PDF，或对现有文档重新排版美化； 2. 表单与水印：自动填写 PDF 表单字段，或添加文字/图片水印（如打水印、标机密）； 3. 页面管理：合并多个 PDF，或拆分、提取指定页码； 4. 安全控制：为 PDF 添加密码（加密）或移除密码（解密）； 5. 内容提取：从 PDF 中提取纯文本或导出表格数据。 只要用户诉求... |
| xiaoyi-ppt-win | `xiaoyiwork/skills/xiaoyi-ppt-win` | 文档/表格/PPT | xiaoyi-ppt-win | 78 | PPT/幻灯片综合处理技能，支持演示文稿的从零生成与现有文件的直接编辑。 适用情形： 1. 新建 PPT：根据给定的主题、上传的文档或网络检索内容，规划大纲并生成完整幻灯片； 2. 编辑 PPT：对已有的 PPTX 文件进行修改，包括调整排版、修改文本、增删与重排页面； 3. 模板套用：基于用户提供的模板 PPT 文件填入新内容。 只要用户意图涉及“做PPT”、“生成幻灯片”、“修改演示文稿”或“排版PPT”时必须触发。 |
| xiaoyi-report-win | `xiaoyiwork/skills/xiaoyi-report-win` | 研究/调研 | xiaoyi-report-win | 8 | 从多源信息生成带引用的专业分析报告。当用户要求研究、调研、调查、分析某个主题，或需要搜索资料、收集信息时使用。支持学术研究、市场调研、竞品分析、技术调研、深度研究。相关请求示例：'帮我调研XXX'、'帮我分析XXX'、'写一份关于XXX的深度研究报告'、'深度分析XXX'。任务完成后主动将生成的HTML报告文件通过channel发送给用户查看。 |
| xiaoyi-self-evolution-win | `xiaoyiwork/skills/xiaoyi-self-evolution-win` | 协作/办公 | xiaoyi-self-evolution-win | 2 | 当用户要求小艺改变未来做事方式、工具选择、执行流程、项目规则或交付标准时，必须使用本技能并先审批后固化。未明确作用域时，必须让用户选择当前项目或用户全局，不得默认全局；有 ask_user 工具时必须调用。命中“记住”“请记住”“以后都这样做”“下次应该”“注意”“固化为规则”等表达，且内容是可执行行为规则或可复用经验时，必须优先于 celia_memory_store，禁止直接回复“已记住”。仅记录姓名、生日等个人事实时不使用本技能。 |
| xiaoyi-vlog-gen-win | `xiaoyiwork/skills/xiaoyi-vlog-gen-win` | 其他 | xiaoyi-vlog-gen-win | 17 | 一键成片、vlog制作，支持批量导入多张图片，智能画面编排、自动匹配氛围感BGM、添加流畅转场与创意特效，一键渲染生成精美vlog短片。触发词：一键成片、vlog、照片剪辑、多图成片、图库生成视频。 |
| xiaoyi-web-search-win | `xiaoyiwork/skills/xiaoyi-web-search-win` | 其他 | xiaoyi-web-search-win | 6 | 使用华为云AI联网搜索API进行网页内容检索，获取实时网络信息 |
| xiaoyi-xlsx-win | `xiaoyiwork/skills/xiaoyi-xlsx-win` | 文档/表格/PPT | xiaoyi-xlsx-win | 57 | Create, edit, or fix spreadsheet files (.xlsx/.xlsm/.csv/.tsv). Trigger whenever the task produces or modifies a spreadsheet — even if the user never says 'Excel'. Covers: data analysis, sorting, filtering, pivot summ... |
