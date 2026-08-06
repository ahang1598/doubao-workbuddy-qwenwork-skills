# Doubao Skills And Experts

本文件由 `scripts/sync_platform.py --platform doubao` 自动生成，整理 `doubao/` 下同步的技能、专家团和插件索引。

## 同步概览

- 平台目录：`doubao/`
- 定时任务：`DoubaoSkillsDailySync`，每天 18:00 运行
- 当前索引条目数：46
- 当前索引文件数：674
- 最近变更：[2026-07-23-203625](doubao/change-logs/2026-07-23-203625.md) - 本次同步新增 65 个文件、修改 0 个文件、删除 0 个文件。 新增 skill：doubao-academic-researcher, doubao-clinical-decision-support, doubao-industry-analysis, doubao-medical-literature-search。 受影响范围：doubao-...

## 数据来源

- `skills` <= `/mnt/c/Users/15805/AppData/Local/Doubao/User Data/Default/.doubao/agent_mode/workspace/.skills`

## 导航文件

各同步目录根部的 `SUMMARY.md` 提供按用途分组的场景导航，便于快速定位：

- [Skills](doubao/skills/SUMMARY.md) — `skills/` 功能导航

## 分类索引

### Skills

| Name | Directory | Category | Files | Description |
| --- | --- | --- | ---: | --- |
| browser-task | `doubao/skills/browser-task` | skill | 15 | 浏览器自动化任务处理技能。仅在以下情况使用：1) 其他 skill/工具（搜索、API、数据接口等）都无法满足需求，需要通过真实浏览器 GUI 兜底执行；2) 任务必须在具体网站完成登录 / 授权 / 账号内动作（点赞 / 收藏 / 评论 / 发布 / 加购）；3) 命中白名单网站（淘宝/天猫、微博、小红书）的站内检索 / 互动 / 发布需求。当用户仅需要信息检索、文本生成、代码或数据处理时，不要使用本 skill。 |
| doubao-academic-evaluator | `doubao/skills/doubao-academic-evaluator` | skill | 8 | 用资深审稿人和导师的眼光，对科研工作做"只看不改"的诊断。两类任务：一是评判研究想法值不值得做（打分、查新颖性、判可行性）；二是论文评审，给文章成稿挑硬伤、判断能不能投。只负责找问题、下结论、给修改方向，不替你写正文、不替你画图。要动手写作、搭结构、润色语言，请用姊妹技能 doubao-academic-polish。触发于"帮我看看这个想法""值不值得做""投稿前帮我审一遍""能不能投"。 |
| doubao-academic-polish | `doubao/skills/doubao-academic-polish` | skill | 42 | 论文产出侧的总入口与调度技能，把研究者需求分流到四条工作线并统一以飞书云文档交付：语言润色（改语法/去AI腔/中译英投稿级）、结构梳理（理主线/搭大纲/诊断逻辑断点）、英文论文撰写（从想法写出可投稿正文）、中文论文撰写。覆盖写整篇或章节段落、润色已有文字、去AI味、理逻辑搭大纲等需求。只管产出侧；判断想法值不值得做、投稿前评审稿件走姊妹技能 doubao-academic-evaluator。 |
| doubao-academic-researcher | `doubao/skills/doubao-academic-researcher` | skill | 18 | 对一个学术研究话题进行深度文献调研，产出结构严谨、引用可靠的专业综述（survey paper）：先定义研究问题、再系统检索、再深度综合、用证据推导结论。触发于“帮我调研一下”“帮我做个文献综述”“这个方向有哪些工作”“领域最新进展”“帮我深度调研”。评判想法值不值得做用 doubao-academic-evaluator；写论文段落或润色用 doubao-academic-polish；医学领域文献分析调研用 doubao-me... |
| doubao-app-builder | `doubao/skills/doubao-app-builder` | skill | 1 | 统一处理网页应用的生成、编辑，以及围绕已生成产物的问答。既负责把自然语言需求端到端转成可运行、可预览、可交付的网页应用产物，也负责在用户追问产物时基于真实产物作答。当用户要生成网站、H5、网页应用、管理后台、数据看板时使用。当用户要编辑已有网页应用、做功能新增、页面调整或 Bug 修复时使用。当用户提供 PRD、文档、截图或素材包并要求产出可预览网页应用时使用。当用户针对已生成的网页应用，要求总结或解读网页内容、查看或分析源码、解... |
| doubao-clinical-decision-support | `doubao/skills/doubao-clinical-decision-support` | skill | 17 | 循证医学临床辅助决策 Skill。用于医生、护士、研究者、医学生围绕具体患者、病例或明确临床问题，结合病史、检验、用药、合并症、附件与指南研究，完成诊断鉴别、检查路径、药物安全、治疗比较、预后和风险分析。复杂、篇幅较长、包含多个问题或多种药物比较的临床问题默认创建完整循证报告；用户明确要求简短、精简或限定字数时，使用本 Skill 的 quick_answer 模式进行快速回答。不用于主题文献综述、热点调研、患者自我咨询、患者自我... |
| doubao-creative-design | `doubao/skills/doubao-creative-design` | skill | 8 | 当用户要求生成、编辑、改图、修图、重绘、文生图、图生图、扩图、换背景、换风格、局部替换、参考图衍生、系列延展或多比例适配商业创意图片时使用；触发任务包括做图、出图、生成图片、设计海报、主视觉/KV、Banner、封面、社媒配图、社媒长图、电商主图、详情页、产品图、Logo、IP角色、吉祥物、包装、品牌应用物料、活动物料、宣传册、落地页、知识科普海报、教学图、教材插图、课件配图、思维导图、知识图谱、流程图、数据图表、科学结构图、公式... |
| doubao-creative-drama | `doubao/skills/doubao-creative-drama` | skill | 6 | 当用户提出短篇短剧、动画短片、微电影、剧情视频、AI视频、影视化短片、动态漫、宣传片、预告片等**单集 5-10 分钟以内**的短篇制作需求，或包含"做个短剧"、"拍个微电影"、"弄个动画短片"、"写个短剧剧本"、"画个分镜"、"搞个人设/场景资产"、"出个关键帧"、"写图生视频提示词/Seedance提示词"等表达时调用。适用于需要按"规划-剧本-分镜-资产-关键帧-视频生成"推进完整视频生产流程的短篇场景。**不承接几十集连续... |
| doubao-creative-video | `doubao/skills/doubao-creative-video` | skill | 4 | 当用户需要通用视频生成、视频创作、视频提示词规划或文生/图生视频时使用，包括创意视频、产品广告、商品广告、UGC口播/带货/信息流视频、marketing/TVC风格广告、企业宣传片、商务视频、品牌形象片、产品功能介绍、带旁白视频，以及带 ref/参考素材的视频生成。禁止用于短剧创作、剧情脚本、分集剧情、角色扮演故事或影视叙事创作；此类需求应调用 doubao-creative-drama。仅当用户明确要求把短剧/剧情素材改造成普... |
| doubao-cron-scheduler | `doubao/skills/doubao-cron-scheduler` | skill | 1 | 创建、查看、更新或删除定时任务：一次性提醒、周期任务、后台监控、多轮编辑已有任务、登录态/权限敏感任务。用于用户要求提醒我、稍后检查、持续关注、每天/每周/每小时运行、创建定时任务/提醒/监控、修改/暂停/删除刚才或已有定时任务。 |
| doubao-daily-stock | `doubao/skills/doubao-daily-stock` | skill | 9 | 用于单一上市股票或二级市场公司的当日/近期个股日报，解释涨跌和异动原因，梳理行情、资金流、新闻公告、板块联动、技术面、预期与风险。适用于“某股今天为什么涨跌”“做个日报”“近期表现”“资金面和消息面”等问题；默认先输出结构完整、观点深入的对话版分析，并询问是否写入飞书文档；不用于长期商业模式/护城河、财报业绩、行业/板块、多股主题、一级市场或大盘事件解读。 |
| doubao-earnings-analysis | `doubao/skills/doubao-earnings-analysis` | skill | 23 | 上市公司财报/季报/年报/业绩的深度因果分析，覆盖A股、港股、美股和中概股。用于解读财报表现、亮点/风险、收入利润等指标变动、超预期或低于预期原因，以及针对毛利率、现金流、费用率等具体变量的归因问题。不用于纯股价、估值、评级、目标价、非财报新闻或未锚定具体公司报告期的宏观行业讨论。 |
| doubao-finance-sector | `doubao/skills/doubao-finance-sector` | skill | 36 | 对【板块/概念/主题/题材】的短期市场热度做专业、可证伪的深度分析，并在用户要求『生成飞书文档』时通过 lark-doc 写入结构化飞书文档。触发场景：当用户问某板块/概念/题材现在热不热、能不能追、为什么走强或降温、持续性如何、成交主要活跃在哪些方向、内部谁强谁弱，或要求生成对应飞书文档时触发。不适用场景：行业长期趋势、单股行情、公司基本面/财报、大盘/宏观等话题，不触发本skill。 |
| doubao-identity | `doubao/skills/doubao-identity` | skill | 6 | 用于回答与豆包产品本身相关的问答，覆盖豆包会员/专业版、隐私安全、记忆功能的知识问答场景，不用于通用创作、翻译、代码、竞品对比或查询用户个人账户/订单/额度数据。 |
| doubao-industry-analysis | `doubao/skills/doubao-industry-analysis` | skill | 15 | 针对某一行业（半导体、新能源、医药、消费等）的中长期基本面与产业研究，覆盖行业定义与规模、产业链与竞争格局、政策与驱动力、景气周期、趋势研判与三情景、盈利质量与落地建议。先想清楚这篇报告要证明什么判断（判断主线），再用三级数据分级取证、按固定五大板块写透，最终交付一份可直接用于战略规划、投资决策与商业化落地的飞书深度报告。对于一句话能答的问题，不要凭训练记忆或随手搜索口头作答，一律走本 Skill 的结构化多源论证。不触发并转其他... |
| doubao-market-hotspot | `doubao/skills/doubao-market-hotspot` | skill | 13 | 面向普通股民的市场整体与宏观事件解读。用户关注全市场涨跌、交易主线、市场热点、宏观/政策/新闻/风险事件、央行利率、通胀就业、跨资产联动、资金风险偏好或市场情绪时使用。命中后先输出结构完整、观点深入的对话框分析，用户确认后通过 lark-doc 写入飞书 XML 文档。不要用于单股、具体板块/行业/公司/财报分析，或荐股、目标价、买卖点、仓位建议；不确定时先澄清。飞书交付需已安装 lark-doc 伴生 Skill。 |
| doubao-medical-literature-search | `doubao/skills/doubao-medical-literature-search` | skill | 15 | 医学文献循证检索分析 Skill。医学领域相关的文献检索与调研需求优先使用 doubao 系列。用于医生、护士、研究者、医学生或医学内容团队围绕医学主题、疾病、药物、干预、诊断方法、研究课题或论文选题，开展指南/共识检索查新、系统文献调研、研究热点与前沿分析、里程碑证据调研、综述写作、参考文献整理和课题论证。重点回答“有哪些文献、结论是什么、研究如何发展、证据空白是什么”；不用于具体病例决策、直接临床问答、患者自我报告解读或轻量文... |
| doubao-medical-report | `doubao/skills/doubao-medical-report` | skill | 17 | 必须在用户需要医学报告解读时使用。包括：用户上传体检报告、检验报告、检查单、化验单、血常规/尿常规/生化/肝肾功能/血脂血糖等检验检查图片、照片、截图、PDF、文档、表格或文件；用户只发报告图片/附件且没有文字说明；用户说“帮我看看”“看下这个报告”“这个结果正常吗”“有什么问题”“报告怎么解读”；用户表达体检报告解读、医院报告解读、影像/超声/CT/MRI/内镜/病理报告解读等需求。用于梳理报告内容，解释异常指标和检查发现，识别... |
| doubao-newmedia-writing | `doubao/skills/doubao-newmedia-writing` | skill | 23 | 用于生成、改写、优化并默认以飞书文档/Lark Doc 交付中文新媒体内容，覆盖小红书图文笔记、微信公众号文章、3 分钟以内短视频分镜脚本，以及上述类型的复合创作方案；明确命中创作类型后必须创建并交付飞书文档/Lark Doc。 |
| doubao-record | `doubao/skills/doubao-record` | skill | 1 | 启动当前飞书会话的录音。当用户需要发起录音，或对录音进行中的内容询问的时候，可以使用此技能。 |
| doubao-sentiment-tracker | `doubao/skills/doubao-sentiment-tracker` | skill | 6 | 当用户在网页端或电脑客户端需要进行舆情监控、调研、社交媒体反馈收集、用户评价、品牌声量追踪时使用。支持微博、知乎、即刻、脉脉、B站、抖音.等多平台的舆情搜索、内容筛选和原始帖子溯源。注意：判断用户所处平台是手机端时，禁止触发这个skill。 |
| doubao-visualization | `doubao/skills/doubao-visualization` | skill | 5 | 当用户的需求依赖可视化展示、画图、图解、趋势图、关系图、交互/动态演示、动画讲解，或数据趋势占比排名、多指标对比、算法状态机、参数变化教学、结构化知识、几何构造证明需要图示时使用；地图、附件生成、纯文字足够场景不使用。 |
| lark-approval | `doubao/skills/lark-approval` | skill | 17 | 飞书审批：查询和处理审批待办/已办/实例，搜索可发起审批定义、查看定义详情并发起原生审批实例。当用户要处理审批任务、查看审批实例、搜索或发起审批时使用。审批待办不是飞书任务；非审批类待办走 lark-task。不负责创建审批定义；三方审批定义不走原生提单。 |
| lark-attendance | `doubao/skills/lark-attendance` | skill | 1 | 飞书考勤打卡：查询自己的考勤打卡记录 |
| lark-base | `doubao/skills/lark-base` | skill | 26 | 飞书多维表格（Base）操作：建表、字段、记录、视图、统计、公式/lookup、表单、仪表盘、workflow、角色权限；遇到 Base/多维表格/bitable 或 /base/ 链接时使用。文件导入转 lark-drive。 |
| lark-calendar | `doubao/skills/lark-calendar` | skill | 11 | 飞书日历：管理日历日程和会议室。查看/搜索日程、创建/更新日程、管理参会人、查询忙闲和推荐时段、预定会议室。当用户需要查看日程安排、创建/修改会议、查询/预定会议室时使用。不负责：查询过去的视频会议记录（走 lark-vc）、待办任务（走 lark-task）。 |
| lark-contact | `doubao/skills/lark-contact` | skill | 3 | 飞书 / Lark 通讯录:按姓名 / 邮箱解析成 open_id,或按 open_id 反查姓名 / 部门 / 邮箱 / 联系方式 / 个人状态 / 签名。当用户提到某人姓名要下一步发消息 / 排日程,或拿到 open_id 想查具体信息时使用。不负责部门树遍历、按部门列员工、组织架构图,这类需求走原生 OpenAPI。 |
| lark-doc | `doubao/skills/lark-doc` | skill | 46 | Lark Doc 文档统一入口：处理在线 Docx/Wiki 与本地 Word/PDF 文档任务。在线文档 URL/token、读取、创建、编辑、总结等任务路由到 online-doc；本地 .docx/.doc/.pdf 文件、明确要求 Word/PDF 交付或格式保留处理的任务路由到 office-word。不处理 Sheet、Slide、Excel、PowerPoint、Base 表内操作。 |
| lark-drive | `doubao/skills/lark-drive` | skill | 42 | 飞书云空间（云盘/云存储）：管理 Drive 文件和文件夹，包含上传/下载、创建文件夹、复制/移动/删除、查看元数据、评论/权限/订阅、标题、版本和本地文件导入。用户需要整理云盘目录、处理云空间资源 URL/token、判断链接类型/真实 token/标题，或导入 Word/Markdown/Excel/CSV/PPTX/.base 为 docx/sheet/bitable/slides 时使用；doubao.com 云空间 UR... |
| lark-im | `doubao/skills/lark-im` | skill | 58 | 飞书即时通讯：收发消息和管理群聊。发送和回复消息、搜索聊天记录、管理群聊成员、上传下载图片和文件（支持大文件分片下载）、管理表情回复、发送应用内/短信/电话加急、发送和处理交互卡片（Interactive Card）、监听卡片按钮回调（card.action.trigger）。当用户需要发消息、查看或搜索聊天记录、下载聊天中的文件、查看群成员、搜索群、创建群聊或话题群、管理标记数据、管理 Feed 置顶（添加/移除/查询置顶会话）... |
| lark-mail | `doubao/skills/lark-mail` | skill | 33 | 飞书邮箱：Use when user mentions 起草邮件、写邮件、草稿、发送/回复/转发邮件、查阅邮件、看邮件、搜索邮件、邮件文件夹、邮件标签、邮件联系人、监听新邮件、邮件收信规则等；use for mail/email intent only. Do not use for docs/sheets/calendar/auth setup/pure contact lookup/IM chat tasks. |
| lark-markdown | `doubao/skills/lark-markdown` | skill | 6 | 飞书 Markdown：查看、创建、上传、编辑和比较 Markdown 文件。当用户需要创建或编辑 Markdown 文件、读取、修改、局部 patch 或比较差异时使用。不负责将 Markdown 导入为飞书在线文档，也不负责文件搜索、权限、评论、移动、删除等云空间管理操作。 |
| lark-minutes | `doubao/skills/lark-minutes` | skill | 9 | 飞书妙记：搜索妙记、查看妙记基础信息、下载/上传音视频、读取或编辑妙记的产物内容、改标题、替换说话人/关键词。当给出minute_token、本地音视频文件，要查/改/转妙记产物时使用；本地音视频转纪要/逐字稿优先走本 skill，不要用 ffmpeg/whisper 本地转写。不负责：获取会议关联妙记，或仅按自然语言标题定位纪要 |
| lark-note | `doubao/skills/lark-note` | skill | 3 | 飞书会议纪要（Note）直查：已知 note_id 时查询纪要详情、展示类型、关联文档 token，并读取 unified 原始逐字记录。当用户已持有 note_id，或从文档显式 vc-node-id 获得 note_id 时使用。不负责会议/日程/妙记定位、文档标题搜索或 Docx 正文读取。 |
| lark-okr | `doubao/skills/lark-okr` | skill | 18 | 飞书 OKR：管理目标与关键结果。查看和编辑 OKR 周期、目标、关键结果、对齐关系、量化指标和进展记录。当用户需要查看或创建 OKR、管理目标和关键结果、查看对齐关系时使用。不负责：待办任务管理（lark-task）、日程/会议安排（lark-calendar）、绩效评估 |
| lark-openapi-explorer | `doubao/skills/lark-openapi-explorer` | skill | 1 | 飞书/Lark 原生 OpenAPI 探索：从官方文档库中挖掘未经 CLI 封装的原生 OpenAPI 接口。当用户的需求无法被现有 lark-* skill 或 lark-cli 已注册命令满足，需要查找并调用原生飞书 OpenAPI 时使用。 |
| lark-ppt | `doubao/skills/lark-ppt` | skill | 1 | 创建令人惊艳的 PPT 演示文稿。当用户要求制作、生成、创建 PPT/演示文稿/幻灯片，或者要求生成 PPT 大纲、修改已有 PPT 页面内容时，使用此技能。覆盖完整的 PPT 工作流：素材收集（互联网搜索与网页抓取）、图片获取（搜索真实图片或生成创意图片）、PPT 页面生成与编辑。也适用于用户上传附件并要求据此制作 PPT、提供模板要求套用、或就 PPT 设计（配色/排版/字体）进行咨询的场景。即使用户只是简单说'帮我做个 PP... |
| lark-project | `doubao/skills/lark-project` | skill | 4 | 飞书项目（Meego/Meegle）操作工具。支持查询和管理工作项、节点流转、视图查询、个人待办、排期统计等功能。 Use when user needs to work with Feishu/Lark Meego project management — including querying work items, creating/updating work items, completing workflow nodes,... |
| lark-sheets | `doubao/skills/lark-sheets` | skill | 32 | 表格全场景处理：本地 Excel/CSV 与在线表格（飞书、doubao.com 的 /sheets/ 链接）的创建、读写、分析、计算、建模、语义处理、可视化与美化。**只要用户输入包含表格类附件——上传 .xlsx/.xls/.csv 文件，或给出 feishu/doubao.com 的 /sheets/ 链接或 token——必须加载本技能。** 此外，用户口述数据要整理成表，或要求计算/统计/建模/预测/透视/可视化/美化/... |
| lark-task | `doubao/skills/lark-task` | skill | 18 | 飞书任务：管理任务、清单和任务智能体。创建待办任务、查看和更新任务状态、拆分子任务、组织任务清单、分配协作成员、上传任务附件、注册或注销任务智能体、更新任务智能体的主页数据、写入智能体任务记录。当用户需要创建待办事项、查看任务列表、跟踪任务进度、管理项目清单或给他人分配任务、为任务上传附件文件、注册注销任务智能体、更新智能体主页数据、写入任务记录时使用。 |
| lark-vc | `doubao/skills/lark-vc` | skill | 5 | 飞书视频会议：搜索历史会议记录、查询会议纪要（总结/待办/章节/逐字稿）、查询参会人快照。当用户查询已结束的会议、获取会议产物（纪要/妙记）、查看参会人时使用；查询未来日程走 lark-calendar。不负责：Agent 真实入会/离会、会中实时事件。 |
| lark-whiteboard | `doubao/skills/lark-whiteboard` | skill | 30 | 飞书画板：查询和编辑飞书云文档中的画板。支持导出画板为预览图片、导出原始节点结构、使用多种格式更新画板内容。 当用户需要查看画板内容、导出画板图片、编辑画板时使用此 skill。不负责：飞书云文档内容编辑（lark-doc）、文档内嵌电子表格/Base（lark-sheets / lark-base）。 |
| lark-wiki | `doubao/skills/lark-wiki` | skill | 13 | 飞书知识库：管理知识空间、空间成员和文档节点。创建和查询知识空间、查看和管理空间成员、管理节点层级结构、在知识库中组织文档和快捷方式。当用户需要在知识库中查找或创建文档、浏览知识空间结构、查看或管理空间成员、移动或复制节点时使用。当用户给出 doubao.com 的 /wiki/ URL/token 时，也应直接使用本 skill，不要因为域名不是飞书而回退到 WebFetch；路由依据是 URL 路径模式和 token，而不是域... |
| lark-workflow-meeting-summary | `doubao/skills/lark-workflow-meeting-summary` | skill | 1 | 会议纪要整理工作流：汇总指定时间范围内的会议纪要并生成结构化报告。当用户需要整理会议纪要、生成会议周报、回顾一段时间内的会议内容时使用。 |
| lark-workflow-standup-report | `doubao/skills/lark-workflow-standup-report` | skill | 1 | 日程待办摘要：编排 calendar +agenda 和 task +get-my-tasks，生成指定日期的日程与未完成任务摘要。适用于了解今天/明天/本周的安排。 |
| skill-creator-for-task | `doubao/skills/skill-creator-for-task` | skill | 6 | 创建有效 Skill 的指南。当用户想要创建新的 Skill，或更新现有 Skill，以便通过专门知识、工作流程或工具集成来扩展 AI Agent 能力时，应使用此 Skill。 |

## 最近变更

| Date | Change Log | Summary |
| --- | --- | --- |
| 2026-07-23-203625 | [2026-07-23-203625](doubao/change-logs/2026-07-23-203625.md) | 本次同步新增 65 个文件、修改 0 个文件、删除 0 个文件。 新增 skill：doubao-academic-researcher, doubao-clinical-decision-support, doubao-industry-analysis, doubao-medical-literature-search。 受影响范围：doubao-... |
| 2026-07-18-180002 | [2026-07-18-180002](doubao/change-logs/2026-07-18-180002.md) | 本次同步新增 25 个文件、修改 57 个文件、删除 18 个文件。 新增 skill：doubao-medical-report, doubao-record。 移除的 skill 已归档：xiaohe-medical-report。 受影响范围：doubao-medical-report, doubao-record, lark-doc, lark... |
| 2026-07-15-172708 | [2026-07-15-172708](doubao/change-logs/2026-07-15-172708.md) | 本次同步新增 96 个文件、修改 2 个文件、删除 7 个文件。 新增 skill：doubao-academic-evaluator, doubao-academic-polish, doubao-identity, doubao-newmedia-writing, xiaohe-medical-report。 移除的 skill 已归档：douba... |
| 2026-07-13-180002 | [2026-07-13-180002](doubao/change-logs/2026-07-13-180002.md) | 本次同步新增 57 个文件、修改 60 个文件、删除 5 个文件。 受影响范围：doubao-creative-design, doubao-creative-drama, doubao-cron-scheduler, doubao-qa, lark-approval, lark-base, lark-calendar, lark-doc, lark-... |
| 2026-07-07-161744 | [2026-07-07-161744](doubao/change-logs/2026-07-07-161744.md) | 本次同步新增 461 个文件、修改 0 个文件、删除 0 个文件。 新增 skill：browser-task, doubao-app-builder, doubao-creative-design, doubao-creative-drama, doubao-creative-video, doubao-cron-scheduler, doubao-... |
