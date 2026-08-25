# Doubao Skills And Experts

本文件由 `scripts/sync_platform.py --platform doubao` 自动生成，整理 `doubao/` 下同步的技能、专家团和插件索引。

## 同步概览

- 平台目录：`doubao/`
- 定时任务：`DoubaoSkillsDailySync`，每天 18:00 运行
- 当前索引条目数：104
- 当前索引文件数：2317
- 最近变更：[2026-08-25-205036](doubao/change-logs/2026-08-25-205036.md) - Doubao 本次同步新增 4 个文件、修改 11 个文件、删除 1 个文件。 新增条目：skills/doubao-enterprise-search。 受影响范围：skills/doubao-enterprise-search, skills/lark-doc, skills/lark-slides-pro。

## 数据来源

- `skills` <= `/mnt/c/Users/15805/AppData/Local/Doubao/User Data/Default/.doubao/agent_mode/workspace/.skills`

## 导航文件

各同步目录根部的 `SUMMARY.md` 提供按用途分组的场景导航，便于快速定位：

- [Skills](doubao/skills/SUMMARY.md) — `skills/` 功能导航

## 分类索引

### Skills

| Name | Directory | Category | Files | Description |
| --- | --- | --- | ---: | --- |
| artifact-preview | `doubao/skills/artifact-preview` | skill | 30 | >- |
| browser-task | `doubao/skills/browser-task` | skill | 15 | 浏览器自动化任务处理技能。仅在以下情况使用：1) 其他 skill/工具（搜索、API、数据接口等）都无法满足需求，需要通过真实浏览器 GUI 兜底执行；2) 任务必须在具体网站完成登录 / 授权 / 账号内动作（点赞 / 收藏 / 评论 / 发布 / 加购）；3) 命中白名单网站（淘宝/天猫、微博、小红书）的站内检索 / 互动 / 发布需求。当用户仅需要信息检索、文本生成、代码或数据处理时，不要使用本 skill。 |
| browser-use-automation | `doubao/skills/browser-use-automation` | skill | 10 | Control websites exclusively through the CNGC Browser Use stack: `computer_use_tool` with `plane=\\"bu\\"` and `seed_browser_use`. Use whenever the user asks to open or navigate a web page, inspect visible content or UI... |
| byted-mediakit-audio | `doubao/skills/byted-mediakit-audio` | skill | 4 | 面向音频文件或视频中的音轨，处理音频媒资信息探测以及人声与背景声分离等目标。若对象和目标族已明确属于音频媒资探测或音轨分离，但具体做法不确定，可先加载本 Skill 探索；若只说有音频而未说明业务目标，应先澄清。音频裁剪、拼接、调速、淡入淡出、混音、从视频提取音轨或音视频合流等编辑合成诉求应路由到 editing；字幕生成、提取字幕、语音转字幕、视频理解、视频增强等应路由到 video。 |
| byted-mediakit-editing | `doubao/skills/byted-mediakit-editing` | skill | 19 | 面向音频、视频或图片素材组成成片的编辑制作目标，适用于素材裁剪与拼接、速度和音量调整、转场、画面翻转、图片叠加、字幕压制、音视频提取与合流、音频混合、淡入淡出以及图转视频等操作。若对象和目标族已明确是对现有素材做剪辑、合成、叠加或混合，但具体做法不确定，可先加载本 Skill 探索；若只给出媒体类型而未说明要剪、合、叠、调还是分析，应先澄清。图像增强、抠图、OCR 或图像擦除应路由到 image；视频画质增强、内容理解、从视频提取... |
| byted-mediakit-image | `doubao/skills/byted-mediakit-image` | skill | 7 | 面向单张图片的视觉处理、质量优化、内容理解与 AI 编辑目标，适用于图像增强、文字或图标擦除、画质评估、文字识别以及背景移除。若对象和目标族已明确属于图片增强、图片理解或图片生成式编辑，但具体做法不确定，可先加载本 Skill 探索；若只说有图片而未说明业务目标，应先澄清。把多张图片做成视频或给视频叠图应路由到 editing；视频理解、视频增强或视频字幕擦除应路由到 video。 |
| byted-mediakit-shared | `doubao/skills/byted-mediakit-shared` | skill | 3 | MediaKit 是面向音视频与图像处理的专业工具集，覆盖音视频剪辑与合成、音频媒资探测与人声分离、视频理解与增强、图像增强与内容理解等工作流。用户明确提出叠加、字幕压制、提取字幕、语音转字幕、裁剪、拼接、调速、混音、音视频处理、图片增强或擦除、视频分析或画质增强目标时，先加载本 Skill，再按对象和目标选择 audio、editing、image 或 video；仅说明媒体类型而未说明处理目标时先澄清。不承担具体能力参数说明。 |
| byted-mediakit-video | `doubao/skills/byted-mediakit-video` | skill | 18 | 面向视频文件或其中音轨的智能处理、媒资理解和画质治理目标，适用于视频内容分析、剧情与高光理解、从视频提取字幕、语音转字幕、字幕识别与擦除、视频增强、人像或绿幕抠像、媒资探测、场景切分和画面文字识别。若对象和目标族已明确属于视频增强、视频分析理解、视频内容结构化、从视频提取字幕、语音转字幕、视频字幕识别或擦除、视频媒资探测或抠像，但具体能力不确定，可先加载本 Skill 探索；若只说有视频而未说明业务目标，应先澄清。明确要把字幕或图... |
| computer-use | `doubao/skills/computer-use` | skill | 1 | 用于操作本地电脑 GUI、浏览器原生界面或真实本地浏览器状态，包括桌面应用、系统设置、弹窗、安装器、文件选择器、专业软件、远程桌面，以及软件下载安装、更新、卸载和首次启动验证。 |
| doubao-academic-evaluator | `doubao/skills/doubao-academic-evaluator` | skill | 8 | 用资深审稿人和导师的眼光，对科研工作做"只看不改"的诊断。两类任务：一是评判研究想法值不值得做（打分、查新颖性、判可行性）；二是论文评审，给文章成稿挑硬伤、判断能不能投。只负责找问题、下结论、给修改方向，不替你写正文、不替你画图。要动手写作、搭结构、润色语言，请用姊妹技能 doubao-academic-polish。触发于"帮我看看这个想法""值不值得做""投稿前帮我审一遍""能不能投"。 |
| doubao-academic-polish | `doubao/skills/doubao-academic-polish` | skill | 53 | 学术论文正文写作、结构设计与语言润色总入口。完整起草、续写、扩写、补写或实质性修订各学科的中英文论文正文时，进入paper-write-zh或paper-write-en；只做提纲、结构诊断或重排方案时，进入paper-shape结构模式；只做忠实润色或不新增研究内容的中译英时，进入paper-shape润色模式。研究评价转/doubao-academic-evaluator；独立系统性文献调研转/doubao-literatur... |
| doubao-academic-researcher | `doubao/skills/doubao-academic-researcher` | skill | 21 | 通用学术文献调研Skill，面向研究者、学生和论文写作者在未锁定具体论文题目前摸清某学术方向、概念、机制、热点前沿、学术史或选题依据。执行系统检索、引用真实性核验、证据分级、主题聚类、交叉综合、争议与空白识别，产出结论先行、引用可追溯的结构化调研结果。触发于用户要求调研某方向、梳理研究现状或related work、查看最新进展、梳理热点前沿或学术史、找文献支撑、做选题依据、解释某概念或机制。只做文献调研与证据支撑，不产出摘要引言... |
| doubao-announcement-analysis | `doubao/skills/doubao-announcement-analysis` | skill | 27 | 搜索并解读上市公司公告，覆盖 A股（沪深北）、港股（HKEX）、美股（SEC EDGAR）三大市场。支持两种模式：①单条/多条具体公告的深度解读（拆解公告要点、判断重要性、给出多视角分析）；②按公司或时间段批量监控并生成公告摘要合集（时效优先、覆盖面广）。适用于业绩报告解读、重大合同/协议公告解读、股权变动（增减持/回购）解读、股权激励（期权/限制性股票/员工持股计划）解读、监管问询函/关注函及回复公告解读、停牌复牌与退市风险公告... |
| doubao-app-builder | `doubao/skills/doubao-app-builder` | skill | 1 | 统一处理网页应用的生成、编辑，以及围绕已生成产物的问答。既负责把自然语言需求端到端转成可运行、可预览、可交付的网页应用产物，也负责在用户追问产物时基于真实产物作答。当用户要生成网站、H5、网页应用、管理后台、数据看板时使用。当用户要编辑已有网页应用、做功能新增、页面调整或 Bug 修复时使用。当用户提供 PRD、文档、截图或素材包并要求产出可预览网页应用时使用。当用户针对已生成的网页应用，要求总结或解读网页内容、查看或分析源码、解... |
| doubao-book-writer | `doubao/skills/doubao-book-writer` | skill | 72 | 豆包办公里的非虚构长文档工作台。用于手册、白皮书、报告、培训材料、人物口述、家谱、资料型书稿等长文档的新建、续写、组装、改写、扩写、精修、去AI味、质检和交付。不用于小说、网文、剧本、诗歌、世界观设定、角色剧情创作、短问答、翻译或代码任务。 |
| doubao-clinical-decision-support | `doubao/skills/doubao-clinical-decision-support` | skill | 17 | 循证医学临床辅助决策 Skill。用户需要分析临床问题，解释临床表现，提供循证医学判断时使用，用于针对临床问题，结合病例资料，查阅指南和文献等循证依据，进行科学回答与诊疗决策，进行诊断鉴别、检查路径、用药安全、治疗比较、预后和风险分析。医学文献检索调研改用 doubao-medical-literature-search，单纯报告解读改用 doubao-medical-report，其他医学文献分析场景使用 doubao-medi... |
| doubao-compliance-assessment-public | `doubao/skills/doubao-compliance-assessment-public` | skill | 28 | 基于公开法律来源开展交互式合规评估并生成可审阅报告。用户要求评估业务法律风险、审阅 PRD、判断监管红线或生成合规报告时使用。 |
| doubao-contract-amendment | `doubao/skills/doubao-contract-amendment` | skill | 2 | 用于在已签原协议基础上，依据用户提供的新情况起草补充协议、变更协议或终止协议。先重建主体、标的、资金、条件、时间和文件构成的整体法律状态，再在用户明确授权范围内成文。仅处理既有协议的派生修改；不用于全新合同起草、既有合同风险审查、一般法律咨询或纯 Word 排版与纯文件处理，纯文档编辑改用 lark-doc。 |
| doubao-contract-drafting | `doubao/skills/doubao-contract-drafting` | skill | 24 | 直接起草中国大陆商业合同并生成无批注、无颜色、中文字体正确的可编辑 Word 文件。适用于采购、服务、营销、工程施工、软件许可、SaaS、委托开发、联合研发、知识产权、租赁、数据处理和保密等场景；读取题干及附件后完成交易信息拆解、风险识别、起草方标准条款与默认商业参数填充、合同生成与交付校验。涉及跨境交易、境外法域或境外争议解决安排时，需升级并要求复核。 |
| doubao-contract-reviewer | `doubao/skills/doubao-contract-reviewer` | skill | 4 | doubao-contract-reviewer 是面向大众用户的合同审查 Skill，适合在豆包/豆包 Turbo 中审查各类合同。用户上传合同或询问“帮我审合同、合同有没有问题、这份合同能不能签、合同风险、合同把关、legal review”时必须使用。本 Skill 强制输出比裸跑更有用的结构化审查：先判断我方立场，再按交易模块识别风险，区分“必改风险 / 可争取优化项 / 形式完善项”，并给出可直接替换或补充的修改文本。适... |
| doubao-creative-design | `doubao/skills/doubao-creative-design` | skill | 18 | 当用户要求从零生成、设计商业/社交媒体创意图片，或做系列延展、多比例适配时使用；触发任务包括做图、出图、生成图片、设计海报、主视觉/KV、Banner、封面、社媒配图、社媒长图、电商主图、详情页、产品图、Logo、IP角色、吉祥物、包装、品牌应用物料、活动物料、宣传册、落地页、知识科普海报、信息图、教学图、教材插图、课件配图、思维导图、知识图谱、流程图、数据图表、科学结构图、公式推导图、工程图纸、多资产视觉系统等图片设计场景 |
| doubao-creative-drama | `doubao/skills/doubao-creative-drama` | skill | 6 | 当用户提出短篇短剧、动画短片、微电影、剧情视频、AI视频、影视化短片、动态漫、宣传片、预告片等**单集 5-10 分钟以内**的短篇制作需求，或包含"做个短剧"、"拍个微电影"、"弄个动画短片"、"写个短剧剧本"、"画个分镜"、"搞个人设/场景资产"、"出个关键帧"、"写图生视频提示词/Seedance提示词"等表达时调用。适用于需要按"规划-剧本-分镜-资产-关键帧-视频生成"推进完整视频生产流程的短篇场景。**不承接几十集连续... |
| doubao-creative-video | `doubao/skills/doubao-creative-video` | skill | 4 | 当用户需要通用视频生成、视频创作、视频提示词规划或文生/图生视频时使用，包括创意视频、产品广告、商品广告、UGC口播/带货/信息流视频、marketing/TVC风格广告、企业宣传片、商务视频、品牌形象片、产品功能介绍、带旁白视频，以及带 ref/参考素材的视频生成。禁止用于短剧创作、剧情脚本、分集剧情、角色扮演故事或影视叙事创作；此类需求应调用 doubao-creative-drama。仅当用户明确要求把短剧/剧情素材改造成普... |
| doubao-critical-reading-companion | `doubao/skills/doubao-critical-reading-companion` | skill | 5 | 深度解读文章，把新闻、长评或宣传文案等非学术公共文本转成便于理解、可追溯的阅读地图；用于重建论证链、评价证据与推理、识别隐藏前提、补充替代解释、核查关键事实，并输出可追溯的阅读地图。适用于可信度判断、论证拆解、宣传分析、作者自检和行动决策。 |
| doubao-cron-scheduler | `doubao/skills/doubao-cron-scheduler` | skill | 1 | 创建、查看、更新或删除定时任务：一次性提醒、周期任务、后台监控、多轮编辑已有任务、登录态/权限敏感任务。用于用户要求提醒我、稍后检查、持续关注、每天/每周/每小时运行、创建定时任务/提醒/监控、修改/暂停/删除刚才或已有定时任务。 |
| doubao-cross-border-growth-content | `doubao/skills/doubao-cross-border-growth-content` | skill | 16 | Evidence-grounded cross-border ecommerce content operations for short-video and livestream scripts, UGC or creator briefs, multilingual captions, localized content angles, image/video briefs, content calendars, hook m... |
| doubao-customer-service | `doubao/skills/doubao-customer-service` | skill | 17 | >- |
| doubao-daily-stock | `doubao/skills/doubao-daily-stock` | skill | 9 | 用于单一上市股票的个股日报，解释涨跌和异动原因，梳理行情、资金流、新闻公告、板块联动、技术面、预期与风险。适用于“某股今天为什么涨跌”“做个日报”“近期表现”“资金面和消息面”等问题；默认先输出结构完整、观点深入的对话版分析，并询问是否写入飞书文档；不用于长期商业模式/护城河、财报业绩、行业/板块、多股主题、一级市场或大盘事件解读。 |
| doubao-data-analysis | `doubao/skills/doubao-data-analysis` | skill | 15 | 结构化业务数据分析：附件读取与口径核验、定向筛选、规则/阈值判定、指标异动归因、漏斗/留存/实验分析、经营复盘及可审计报告。当用户提供 Excel、CSV、PDF、图片或多份业务材料，要求查数、判异常、解释变化、比较方案或形成行动建议时使用。Use for evidence-grounded analysis of structured business data, including filtering, rule checks... |
| doubao-dpa-drafter | `doubao/skills/doubao-dpa-drafter` | skill | 15 | DPA数据处理协议专业起草；当用户需要起草数据处理协议、DPA协议、数据委托处理协议、数据共同处理协议或数据对外提供协议时使用。仅做数据合规类协议起草，通用商务合同或非数据类合同请改用对应 skill |
| doubao-earnings-analysis | `doubao/skills/doubao-earnings-analysis` | skill | 23 | 上市公司财报/季报/年报/业绩的深度因果分析，覆盖A股、港股、美股和中概股。用于解读财报表现、亮点/风险、收入利润等指标变动、超预期或低于预期原因，以及针对毛利率、现金流、费用率等具体变量的归因问题。不用于纯股价、估值、评级、目标价、非财报新闻或未锚定具体公司报告期的宏观行业讨论。 |
| doubao-ecommerce-compliance-tax-logistics | `doubao/skills/doubao-ecommerce-compliance-tax-logistics` | skill | 12 | Cross-border ecommerce compliance, tax, IP, customs, tariff, HS code, fulfillment, warehousing, China import, and clearance workflow for marketplace and independent-store sellers. Use when the user asks whether a prod... |
| doubao-ecommerce-proposal | `doubao/skills/doubao-ecommerce-proposal` | skill | 5 | 电商活动策划专家。用于生成、改写、优化完整电商活动策划方案，并默认交付一份已经本地落地、可用浏览器打开验证的 HTML 网页版方案。覆盖淘宝/天猫、抖音电商、京东、得物、拼多多、小红书、Amazon、TikTok Shop、Shopee、Lazada、eBay、Shopify/独立站等平台的节点大促、店铺活动、平台活动、直播间活动、品类活动、品牌日、上新、清仓、会员复购、内容种草到成交、站内外联动与跨境电商活动。若用户只要商品标题... |
| doubao-enterprise-search | `doubao/skills/doubao-enterprise-search` | skill | 1 | 判断是否调用 `enterprise_agentic_search` 工具前，必须先完整读取 `doubao-enterprise-search` skill。适用场景包括：用户显式使用 /doubao-enterprise-search；问题明确或高度可能依赖企业内部资料、内部口径、内部系统、业务背景、历史讨论、协作记录、制度流程、员工权益、差旅报销，或内部产品、项目、客户、业务数据及非飞书通讯录 ID/UID/账号/标识；用户... |
| doubao-finance-model-builder | `doubao/skills/doubao-finance-model-builder` | skill | 116 | 对 A 股、港股和美股上市公司执行中文、可审计且带机器阻断质量门的三表预测、DCF、LBO或可比公司估值。支持最新公告增量检索、除权除息和送转股等公司行动证据冻结、收入增速和多产品量价预测、三表勾稽、FCFF/WACC/终值、分层债务与回报、同行筛选和相对估值。用于财务预测、预算、目标价、杠杆回报或交易可比分析；不要用于自动下单、纯信用评级或并购法律意见。 |
| doubao-game-designer | `doubao/skills/doubao-game-designer` | skill | 74 | 把游戏创意、参考作品、现有方案、配置或试玩证据转化为玩法成立、规则闭合、数值可复算且能进入制作的 GDD、玩法方案与系统规格；需要验证关键玩法时，联合前端或开发能力交付可直接运行的 HTML 游戏 Demo。用于核心循环、战斗、成长、经济、关卡、引导、平衡、活动、版本设计、方案评审与修订，以及按需追加的立项、发行、商业和制作内容。 |
| doubao-headlines-calendar | `doubao/skills/doubao-headlines-calendar` | skill | 8 | 跨平台内容生成、改写、评估和A/B测试标题，并结合账号定位、受众、产能和节点规划可执行的周度或月度内容选题日历。用于爆款标题、多平台标题适配、标题优化、标题拆解、A/B标题、周选题、月度排期、栏目规划、热点日历和新媒体内容策划；不用于直接写完整文章、小说、脚本、PPT或其他成品。能力范围外或多意图任务先说明边界并提供可转化、分模块交付方案。除非用户明确指定其他格式，必须实际创建、写入并校验飞书/Lark文档后返回可访问链接；不得用... |
| doubao-human-signal | `doubao/skills/doubao-human-signal` | skill | 13 | 去除或避免文本中的 AI 味。用于用户强制调用本 Skill，或写作/改写时提到“不要有 AI 味”“不要太假”“真情实感”“有人感”，或对已有文本/上一轮输出反馈“太像 AI”“太空泛”“太模板”“太官方”“不像我说的”等场景。 |
| doubao-identity | `doubao/skills/doubao-identity` | skill | 6 | 用于回答与豆包产品本身相关的问答，覆盖豆包会员/专业版、隐私安全、记忆功能的知识问答场景，不用于通用创作、翻译、代码、竞品对比或查询用户个人账户/订单/额度数据。 |
| doubao-industry-analysis | `doubao/skills/doubao-industry-analysis` | skill | 15 | 针对某一行业（半导体、新能源、医药、消费等）的中长期基本面与产业研究，覆盖行业定义与规模、产业链与竞争格局、政策与驱动力、景气周期、趋势研判与三情景、盈利质量与落地建议。先想清楚这篇报告要证明什么判断（判断主线），再用三级数据分级取证、按固定五大板块写透，最终交付一份可直接用于战略规划、投资决策与商业化落地的飞书深度报告。对于一句话能答的问题，不要凭训练记忆或随手搜索口头作答，一律走本 Skill 的结构化多源论证。不触发并转其他... |
| doubao-journal-format | `doubao/skills/doubao-journal-format` | skill | 14 | 用于对学术论文类 Word/DOCX 文档进行期刊、学校、会议或课程要求的格式排版与修复。当用户需要把论文原稿套用.docx 模板或明确格式规则、或提到论文排版、期刊投稿格式、学位论文格式、会议论文模板、时使用；如果同一请求同时包含论文 Word 排版和任何非排版任务，必须先停止并询问用户选择“只做格式排版”还是“作为复合任务拆分处理”，在用户明确选择前不得执行排版。不用于论文写作、润色、降重、翻译、代写、文献检索、补引用、验证引... |
| doubao-listing-localization | `doubao/skills/doubao-listing-localization` | skill | 10 | Cross-border ecommerce Listing and Product Optimization for Amazon, TEMU, Walmart Marketplace, TikTok Shop, Shopify, AliExpress, Etsy, Google Shopping, Shopee, Lazada, Ozon, and other marketplace or independent-store... |
| doubao-market-hotspot | `doubao/skills/doubao-market-hotspot` | skill | 63 | 把宏观、政策、监管、供需、地缘、行业或公司事件转化为公司、行业与公开市场的因果影响分析，覆盖事件状态、基线、传导渠道、财务与估值影响、直接及高阶影响、priced-in判断、情景、监控与证伪。用于事件影响、政策冲击、跨资产传导和公司事件研究；不要用于无明确事件的公司基本面或普通新闻摘要。 |
| doubao-marketing-material-review | `doubao/skills/doubao-marketing-material-review` | skill | 1 | 营销素材审核。当用户上传待审核的广告宣传语、营销海报、社交媒体推广文案、直播话术等营销素材时，从虚假宣传、夸大宣传、绝对化用语、比较广告、引证数据真实准确性、价格违规、有奖营销、知识产权、风险行业违规宣传（如金融、医疗、三品一械、教育等特殊监管行业）、数据对外披露、不当承诺或表达等维度开展全面审查与风险扫描，对违规点归类、逐条分析判断并直接给出修改建议。当用户提到"营销素材审核""广告文案合规审查""宣传语合规""看看这段宣传/文... |
| doubao-marketing-plan | `doubao/skills/doubao-marketing-plan` | skill | 5 | 首席营销策划官。用于生成、改写、优化并默认以飞书文档/Lark Doc 交付，以首席营销策划官的全域营销能力，把用户模糊的业务诉求转化为资深操盘手会交付的实战级方案。 |
| doubao-medical-literature-interpretation | `doubao/skills/doubao-medical-literature-interpretation` | skill | 8 | 医学文献解读 Skill。用户上传或提供医学论文、指南等资料的片段、网页链接、DOI、aka 文件链接、PDF、表格或图片，并要求解读、总结、分析、问答或对比时使用；先阅读内容并判断是否属于医学文献。面向医学领域文献资料，对已给定的一篇或一组医学论文、指南的 PDF、网页、摘要、段落、表格或图片进行总结、问答、逐篇解读、横向比较及方法学评价。需主动检索或扩展文献时改用 doubao-medical-literature-searc... |
| doubao-medical-literature-monitoring | `doubao/skills/doubao-medical-literature-monitoring` | skill | 9 | 医学进展跟踪 Skill。用于医生、研究人员或医学内容团队对相关领域最新进展的跟踪和调研需求，当用户提出“查询最新进展、订阅监控进展更新、定期更新推送”等需求时，可以调用该技能跟踪相关医学主题的研究、预印本、指南/共识、监管、临床试验、会议和专业资讯进展，首次检索生成飞书进展报告，并邀请用户确认订阅定时监控推送，用户确认后创建定时任务，定时任务中需要强调后续推送时调用本 Skill 呈现新增进展变化。调研某领域最新医学进展需求使用... |
| doubao-medical-literature-search | `doubao/skills/doubao-medical-literature-search` | skill | 17 | 医学文献检索分析 Skill。用户需要查找临床指南、论文研究，或要求检索主流医学数据库时使用，满足文献检索、领域综述、选题分析、考试学习、方法调研等医学文献场景需求。用于查找指南、共识和研究，或围绕医学主题、疾病、药物、干预及课题开展文献综述与课题论证。具体病例决策改用 doubao-clinical-decision-support，其他医学文献分析场景使用 doubao-medical 系列。 |
| doubao-medical-literature-translation | `doubao/skills/doubao-medical-literature-translation` | skill | 11 | 医学文献翻译 Skill，面向医学领域文献资料翻译。用于英译中或中译英，覆盖论文、摘要、指南、临床试验、药品资料等医学文献的翻译需求；支持文本片段、指定章节、网页、PDF、飞书文件、文章全文的翻译，中译英只在不改变原意下使用常见医学学术表达。全文翻译默认创建飞书文档提供翻译结果，论文片段、短论文使用 quick answer 模式翻译后直接回答。仅做来源内语言转换，检索或综合多篇证据用医学文献检索技能，具体病例诊疗用临床诊疗与循证... |
| doubao-medical-report | `doubao/skills/doubao-medical-report` | skill | 17 | 必须在用户需要医学报告解读时使用。包括：用户上传体检报告、检验报告、检查单、化验单、血常规/尿常规/生化/肝肾功能/血脂血糖等检验检查图片、照片、截图、PDF、文档、表格或文件；用户只发报告图片/附件且没有文字说明；用户说“帮我看看”“看下这个报告”“这个结果正常吗”“有什么问题”“报告怎么解读”；用户表达体检报告解读、医院报告解读、影像/超声/CT/MRI/内镜/病理报告解读等需求。用于梳理报告内容，解释异常指标和检查发现，识别... |
| doubao-multiplatform-rewrite | `doubao/skills/doubao-multiplatform-rewrite` | skill | 12 | 基于用户提供的已有素材（母稿、文章、新闻稿、活动稿、产品稿、报告摘要、访谈素材、口播稿、散乱素材等），改写成可发布的多平台分发版本，标准场景为≥2个平台，有素材的单平台改写也可支持，覆盖微信公众号、短视频脚本、微博等平台。当用户提到"一稿多发""多平台分发""内容矩阵""跨平台改写""同一内容发多个平台""分发执行包"，或提供母稿并说"适合不同平台""不同平台都能发""平台化处理""适合平台传播""改成某平台版"时触发。不适用场景... |
| doubao-newmedia-writing | `doubao/skills/doubao-newmedia-writing` | skill | 23 | 用于生成、改写、优化并默认以飞书文档/Lark Doc 交付中文新媒体内容，覆盖小红书图文笔记、微信公众号文章、3 分钟以内短视频分镜脚本，以及上述类型的复合创作方案；明确命中创作类型后必须创建并交付飞书文档/Lark Doc。 |
| doubao-novel-writing | `doubao/skills/doubao-novel-writing` | skill | 10 | 用于网文小说创作、改写、续写、诊断、卖点包装、市场调查和编辑视角分析。当用户需要写或优化开篇、第一章、前三章、章节正文、大纲、设定、人设、CP、情节桥段、简介、导语、投稿文，或要求分析相似网文、研究题材市场、拆解公开作品、模拟网文编辑审稿、制定连载规划时使用。适用于女频、男频、短篇、长篇、爽文、甜宠、悬疑、玄幻、末世、无限流等网文任务。不用于范文批量入库、小说素材库维护、小红书运营或非小说类写作任务。 |
| doubao-oceanengine-adops-agent | `doubao/skills/doubao-oceanengine-adops-agent` | skill | 5 | 字节UG自动化投放Agent 的巨量引擎只读盯盘与数据分析 Skill。适用于查询已授权账户报表、分析核心投放指标、识别长尾候选和诊断效果问题；使用官方 Remote MCP，只输出观察与建议，不创建、暂停、开启、删除或调整广告。 |
| doubao-paper-close-reading | `doubao/skills/doubao-paper-close-reading` | skill | 2 | 用于用户提供一篇或少量学术论文后，进行专业深度精读，讲清研究问题、研究故事、方法或理论机制、关键证据、实验结果、可信边界、复现风险与研究启示，并生成高级 Markdown 报告和飞书文档。用户要求“论文精读”“深度解读”“分析方法与实验”“判断论文价值或局限”时使用。开放主题综述、单纯题录核验、论文代写或语言润色时不使用。 |
| doubao-patent-drafting | `doubao/skills/doubao-patent-drafting` | skill | 7 | 用户要求基于技术交底书撰写或修改中国发明、实用新型专利申请文件，或者审查已有权利要求书时使用。典型触发包括“专利撰写”“专利申请”“技术交底书”“权利要求”“说明书”“实用新型”“发明专利”。专利检索、FTO/侵权分析、无效宣告、审查意见答复、商标或著作权是相邻业务：用户只提这些时不适用本流程；与撰写需求混在一起提出时，撰写照常进行，但最终回复必须对其中每一项其他诉求逐一说明处理情况——漏掉任何一项，这次交付就是不完整的。 |
| doubao-pc-optimizer | `doubao/skills/doubao-pc-optimizer` | skill | 11 | 用户需要清理磁盘垃圾、释放空间、处理电脑卡顿或开机慢、优化 Windows/macOS 性能、提升游戏帧率、生成安全清理脚本，或提到 C 盘满、磁盘空间不足、掉帧、运行慢时使用。 |
| doubao-pdf | `doubao/skills/doubao-pdf` | skill | 14 | 用于处理所有 PDF 相关任务，包括读取、创建、编辑、转换、内容提取、页面处理、表单填写和扫描件解析。用户提供、提及或要求生成 PDF 时使用。 |
| doubao-personal-info-audit | `doubao/skills/doubao-personal-info-audit` | skill | 69 | 开展中国个人信息保护合规审计、审计触发判断、证据登记与证明力评价、事实和不确定性分析、数据分类、处理活动盘点、法律角色和处理情形识别、适用规则检索、上下位法与配套规范衔接、26模块107子项评价、风险与整改设计，并生成可追溯的Word审计报告和Excel底稿。用于个人信息保护法、网络数据安全、App/SDK、敏感个人信息、未成年人、人脸识别、自动化决策、AI、委托共享、数据出境、监管检查准备及整改复核任务。 |
| doubao-private-company | `doubao/skills/doubao-private-company` | skill | 163 | 评估一级市场、私募股权或创业项目的初步投资价值，基于BP、Deck、财务和访谈资料输出Screening Report、投资逻辑、红旗、情景、尽调缺口和初步建议。用于项目初筛、是否进入下一轮尽调或是否安排首次会议。不要替代完整尽调、法律意见或正式IC审批。 |
| doubao-product-analysis | `doubao/skills/doubao-product-analysis` | skill | 7 | 围绕具体产品、产品想法或存量方案，产出用于产品进入、定位、竞争策略、上市路径、能力建设与路线图决策的证据型分析报告。适用于“值不值得做或发布”“进入哪个细分”“目标用户和市场是否成立”“竞品为何这样设计”“该借鉴、差异化或放弃什么”“核心能力与 Roadmap 怎么定”“如何调整已有产品”等请求，也适用于将用户研究、市场信息、竞品实测、内部资料和业务约束整合为决策建议。支持 0→1、存量产品调整、竞品专项与组合分析；默认交付为可独... |
| doubao-product-content | `doubao/skills/doubao-product-content` | skill | 21 | 生成或优化电商商品标题、详情文案和商品页静态图片。 |
| doubao-product-manager | `doubao/skills/doubao-product-manager` | skill | 15 | 将产品想法、用户反馈、研究数据、云文档、附件和已有方案转化为有依据的产品判断、策略、MVP、优先级、Roadmap、PRD、用户故事、验收标准或方案评审。任务涉及产品决策、需求取舍、存量产品修改、范围变更、上线复盘或产品文档交付时使用，即使用户没有说‘产品经理’；纯转写、翻译、校对、格式转换、资料摘要或已定方案的技术实现不由本 Skill 主导，除非仍需产品判断。用户提供链接、文件、截图、脑图、表格、评论或旧产物时，先读取真实内容。 |
| doubao-product-qa | `doubao/skills/doubao-product-qa` | skill | 102 | 将 PRD、原型、网页、接口、代码、测试记录和多轮上下文转成可追踪的 QA 基线、风险用例、执行证据、Bug 与发布判断。适用于 Web/API/App/小程序测试、回归、热修复、测试方案、Bug 复核和 QA 收口。用户指定 Markdown、Office、豆包文档/表格/PPT 或飞书载体时严格服从；未指定时默认创建与内容匹配的豆包在线载体。纯开发实现、纯排版和无测试目标的数据分析不触发。 |
| doubao-product-selection | `doubao/skills/doubao-product-selection` | skill | 1 | 电商选品与品类机会分析技能。根据商家的预算、目标平台、货源优势，按"市场需求×竞争度×利润空间×季节性×复购率"五维打分，输出3-5个候选品类及切入建议。适用于新手不知道卖什么、老商家想拓新品类、想判断某个品值不值得进货的场景。 |
| doubao-public-company-analysis | `doubao/skills/doubao-public-company-analysis` | skill | 64 | 分析上市公司的商业模式、竞争优势、行业位置、财务质量、估值、风险与投资观点。用于用户要求公司基本面研究、公司深度分析、投资研究或提供公司名称/代码与关注点时。不要用于纯事件影响、批量选股、一级市场项目或个人财富规划。 |
| doubao-questionnaire-designer | `doubao/skills/doubao-questionnaire-designer` | skill | 6 | 用户研究一站式助手,覆盖四大能力:①问卷设计(按调研目标产出可落地问卷,含试填优化,交付 Word/飞书文档);②访谈提纲(题量按诉求动态确定、含追问轮次/方向/触发条件的深访提纲);③开放题原声打标(五步工作流建立标签体系并批量标注);④定量问卷分析(仅需回收数据,自动识别题型、自动清洗、直接出关键发现/画像/详细发现/原声引用报告)。触发词:设计问卷、写问卷、满意度调研、NPS、访谈提纲、深访提纲、开放题打标、原声编码、VOC... |
| doubao-record | `doubao/skills/doubao-record` | skill | 1 | 启动当前飞书会话的录音。当用户需要发起录音，或对录音进行中的内容询问的时候，可以使用此技能。 |
| doubao-reference-audit | `doubao/skills/doubao-reference-audit` | skill | 3 | 用于用户提交论文、学位论文或参考文献清单后，系统审查参考文献真实性、题录准确性、文内—文后对应关系以及正文主张是否得到被引文献支持，并生成专业、清晰、可直接指导修改的论文引用审计报告与飞书文档。用户要求“论文审计”“参考文献检查”“引用核对”“引用是否支持观点”“检查错引、过度推断或二手转引”时使用。开放主题综述、普通论文精读、论文代写或仅做语言润色时不使用。 |
| doubao-research-proposal | `doubao/skills/doubao-research-proposal` | skill | 14 | 用于国自然、国社科等基金申请、开题报告、博士后/人才计划、研究计划书等学术提案的撰写、审查和优化；当用户需要基于已有研究成果形成立项书、区分事实与 AI 建议、检查任务书一致性、补强论证逻辑时使用。 |
| doubao-sentiment-tracker | `doubao/skills/doubao-sentiment-tracker` | skill | 6 | 当用户在网页端或电脑客户端需要进行舆情监控、调研、社交媒体反馈收集、用户评价、品牌声量追踪时使用。支持微博、知乎、即刻、脉脉、B站、抖音.等多平台的舆情搜索、内容筛选和原始帖子溯源。注意：判断用户所处平台是手机端时，禁止触发这个skill。 |
| doubao-stock-screening | `doubao/skills/doubao-stock-screening` | skill | 49 | 用于 A 股、港股、美股及其他股票市场的股票筛选、候选股构建、指定股票比较、行业筛选、主题概念筛选、产业链环节筛选、策略风格筛选和龙头识别。适用于用户要求找股票、筛股票池、比较指定股票、识别行业或主题龙头、按市场/行业/主题/产业链/投资风格/透明指标排序候选标的等场景。强调动态检索、权威信源、业务证据验证、透明分组和可解释结论；禁止隐藏评分、不可解释排名和确定性投资建议。 |
| doubao-ultimate-guide | `doubao/skills/doubao-ultimate-guide` | skill | 64 | 统一攻略创作总控 Skill：根据用户需求路由到旅游攻略、健身攻略、美食烹饪教程、游戏攻略四个分支，默认先创建飞书/Lark 文档容器，再读取对应分支 Skill 生成内容并写入同一个文档。适用于旅行行程、训练健身、菜谱烹饪、游戏实战攻略等中文攻略类创作；不适用于泛资讯、商业分析、医疗诊断、金融投资、法律意见、纯文案包装、无明确攻略目标或不安全/违规请求。 |
| doubao-video-extract | `doubao/skills/doubao-video-extract` | skill | 22 | 可提取、下载、解析、理解在线视频或本地视频文件。在线视频包含抖音、快手、B 站、视频直链。可提取内容包含视频的音频、字幕、逐字稿、文案、脚本、总结、时间轴。可理解的视频内容包含画面、人物、物体、动作、界面等视觉元素。 |
| doubao-visualization | `doubao/skills/doubao-visualization` | skill | 28 | 当用户要求可视化、画图、图解、配图、信息图、趋势图、数据对比、原图标注、圈选连线、路径轨迹、动态图、动画讲解、交互演示、参数变化、关系图、流程图、时间线、结构图、知识科普或作品解读时使用；也用于判断图表、用户原图叠加、HTML/SVG 交互、基于原图二次生成或纯文字哪种表达最合适。地图、附件导出或纯文字明显更清楚时不强行可视化。 |
| doubao-wealth-planning | `doubao/skills/doubao-wealth-planning` | skill | 166 | 为个人或家庭构建目标导向的财富规划，覆盖现金流、应急资金、债务、保障、教育/养老等目标、资产配置、情景压力测试与行动清单。用于新规划、年度复盘或重大人生变化。必须先确认司法辖区和风险承受能力；不替代持牌投资、税务、保险或法律意见。 |
| lark-approval | `doubao/skills/lark-approval` | skill | 17 | 飞书审批：查询和处理审批待办/已办/实例，搜索可发起审批定义、查看定义详情并发起原生审批实例。当用户要处理审批任务、查看审批实例、搜索或发起审批时使用。审批待办不是飞书任务；非审批类待办走 lark-task。不负责创建审批定义；三方审批定义不走原生提单。 |
| lark-attendance | `doubao/skills/lark-attendance` | skill | 1 | 飞书考勤打卡：查询自己的考勤打卡记录 |
| lark-base | `doubao/skills/lark-base` | skill | 27 | 飞书多维表格（Base）：基于需求搭建系统和应用，或把已有数据、零散信息结构化，搭建成可持续记录、收集、整理、关联、协作、统计、提醒和流转的数据工具与管理系统。适用于个人、组织、企业的日常记录、清单登记、资料库、报名问卷、进度跟踪及项目/客户/订单/库存等系统和应用的生成需求；用户想把信息记下来、管起来、统计查看、持续更新或自动处理时使用，或提及 Base/多维表格/bitable、提供 Base 链接时使用；已有 Base 的查... |
| lark-calendar | `doubao/skills/lark-calendar` | skill | 11 | 飞书日历：管理日历日程和会议室。查看/搜索日程、创建/更新日程、管理参会人、查询忙闲和推荐时段、预定会议室。当用户需要查看日程安排、创建/修改会议、查询/预定会议室时使用。不负责：查询过去的视频会议记录（走 lark-vc）、待办任务（走 lark-task） |
| lark-contact | `doubao/skills/lark-contact` | skill | 4 | 飞书 / Lark 通讯录:按姓名 / 邮箱解析成 open_id,或按 open_id 反查姓名 / 部门 / 邮箱 / 联系方式 / 个人状态 / 签名,以及按关键词搜索当前用户可见的机器人 / 智能体(agent)。当用户提到一个名字要下一步发消息 / 排日程,或拿到 open_id 想查具体信息时使用。不负责部门树遍历、按部门列员工、组织架构图,这类需求走原生 OpenAPI。 |
| lark-doc | `doubao/skills/lark-doc` | skill | 62 | 文档全场景处理：本地 Office Word（.docx/.doc）与在线文档（飞书、doubao.com 的 `/docs`、`/docx`、`/wiki` 链接）的阅读、创建和编辑。当任务涉及本地 Word 或在线 Doc/Wiki 时使用。不处理 PDF、Sheet、Slide、Excel、PowerPoint、Base 表内操作。 |
| lark-drive | `doubao/skills/lark-drive` | skill | 61 | 飞书云空间（云盘/云存储）：管理 Drive 文件和文件夹，包含上传/下载、创建文件夹、复制/移动/删除、查看元数据、查询权限设置、评论/权限/订阅、标题、版本、飞书文档密级标签（secure labels）和本地文件导入。用户需要整理云盘目录、处理云空间资源 URL/token、判断链接类型/真实 token/标题，或导入 Word/Markdown/Excel/CSV/PPTX/.base 为 docx/sheet/bitab... |
| lark-im | `doubao/skills/lark-im` | skill | 58 | 飞书即时通讯：收发消息和管理群聊。发送和回复消息、搜索聊天记录、管理群聊成员、上传下载图片和文件、管理表情回复、发送应用内/短信/电话加急、发送交互卡片（Interactive Card）。当用户需要发消息、查看或搜索聊天记录、下载聊天中的文件、查看群成员、搜索群、创建群聊或话题群、管理标记数据、管理 Feed 置顶（添加/移除/查询置顶会话）、管理标签数据、发送交互卡片时使用。 |
| lark-mail | `doubao/skills/lark-mail` | skill | 33 | 飞书邮箱：Use when user mentions 起草邮件、写邮件、草稿、发送/回复/转发邮件、查阅邮件、看邮件、搜索邮件、邮件文件夹、邮件标签、邮件联系人、监听新邮件、邮件收信规则等；use for mail/email intent only. Do not use for docs/sheets/calendar/auth setup/pure contact lookup/IM chat tasks. |
| lark-markdown | `doubao/skills/lark-markdown` | skill | 6 | 飞书 Markdown：查看、创建、上传、编辑和比较 Markdown 文件。当用户需要创建或编辑 Markdown 文件、读取、修改、局部 patch 或比较差异时使用。不负责将 Markdown 导入为飞书在线文档，也不负责文件搜索、权限、评论、移动、删除等云空间管理操作。 |
| lark-minutes | `doubao/skills/lark-minutes` | skill | 10 | 飞书妙记：搜索妙记、查看妙记基础信息、下载/上传音视频、读取或编辑妙记的产物内容、改标题、替换说话人/关键词、申请妙记查看/编辑权限。当给出minute_token、本地音视频文件，要查/改/转妙记产物，或用户明确要主动申请妙记权限时使用；本地音视频转纪要/逐字稿优先走本 skill，不要用 ffmpeg/whisper 本地转写。不负责：获取会议关联妙记，或仅按自然语言标题定位纪要 |
| lark-note | `doubao/skills/lark-note` | skill | 3 | 飞书会议纪要（Note）直查：已知 note_id 时查询纪要详情、展示类型、关联文档 token，并读取 unified 原始逐字记录。当用户已持有 note_id，或从文档显式 vc-node-id 获得 note_id 时使用。不负责会议/日程/妙记定位、文档标题搜索或 Docx 正文读取。 |
| lark-okr | `doubao/skills/lark-okr` | skill | 19 | 飞书 OKR：管理目标与关键结果。查看和编辑 OKR 周期、目标、关键结果、对齐关系、量化指标和进展记录。当用户需要查看或创建 OKR、管理目标和关键结果、查看对齐关系时使用。不负责：待办任务管理（lark-task）、日程/会议安排（lark-calendar）、绩效评估 |
| lark-openapi-explorer | `doubao/skills/lark-openapi-explorer` | skill | 1 | 飞书/Lark 原生 OpenAPI 探索：从官方文档库中挖掘未经 CLI 封装的原生 OpenAPI 接口。当用户的需求无法被现有 lark-* skill 或 lark-cli 已注册命令满足，需要查找并调用原生飞书 OpenAPI 时使用。 |
| lark-sheets | `doubao/skills/lark-sheets` | skill | 39 | 表格全场景（本地 Excel/CSV 与飞书/doubao 在线表格）：创建、读写、分析、计算、建模、语义处理、可视化与美化。若用户上传附件、提供表格链接/token，或要求任何表格操作，必须加载。 |
| lark-slides-pro | `doubao/skills/lark-slides-pro` | skill | 39 | 飞书幻灯片：创建和编辑幻灯片。创建演示文稿、读取幻灯片内容、管理幻灯片页面（创建、删除、读取、局部替换）。当用户需要创建或编辑幻灯片、读取或修改单个页面时使用。 |
| lark-task | `doubao/skills/lark-task` | skill | 18 | 飞书任务：管理任务、清单和任务智能体。创建待办任务、查看和更新任务状态、拆分子任务、组织任务清单、分配协作成员、上传任务附件、注册或注销任务智能体、更新任务智能体的主页数据、写入智能体任务记录。当用户需要创建待办事项、查看任务列表、跟踪任务进度、管理项目清单或给他人分配任务、为任务上传附件文件、注册注销任务智能体、更新智能体主页数据、写入任务记录时使用。 |
| lark-vc | `doubao/skills/lark-vc` | skill | 8 | 飞书视频会议：查询进行中的会议列表（含会议 ID）、读取会中实时内容（发言、聊天、共享等）、发送会中消息，以及搜索历史会议、查询会议纪要（总结/待办/章节/逐字稿）和参会人快照。本技能不覆盖 Agent 真实入会/离会；查询未来日程走 lark-calendar |
| lark-whiteboard | `doubao/skills/lark-whiteboard` | skill | 31 | 飞书画板：查询和编辑飞书云文档中的画板。支持导出画板为预览图片、导出原始节点结构、使用多种格式更新画板内容。 当用户需要查看画板内容、导出画板图片、编辑画板时使用此 skill。不负责：飞书云文档内容编辑（lark-doc）、文档内嵌电子表格/Base（lark-sheets / lark-base）。 |
| lark-wiki | `doubao/skills/lark-wiki` | skill | 14 | 飞书知识库：管理知识空间、空间成员和文档节点。创建和查询知识空间、查看和管理空间成员、管理节点层级结构、在知识库中组织文档和快捷方式。当用户需要在知识库中查找或创建文档、浏览知识空间结构、查看或管理空间成员、移动或复制节点时使用。当用户给出 doubao.com 的 /wiki/ URL/token 时，也应直接使用本 skill，不要因为域名不是飞书而回退到 WebFetch；路由依据是 URL 路径模式和 token，而不是域... |
| lark-workflow-meeting-summary | `doubao/skills/lark-workflow-meeting-summary` | skill | 1 | 会议纪要整理工作流：汇总指定时间范围内的会议纪要并生成结构化报告。当用户需要整理会议纪要、生成会议周报、回顾一段时间内的会议内容时使用。 |
| lark-workflow-standup-report | `doubao/skills/lark-workflow-standup-report` | skill | 1 | 日程待办摘要：编排 calendar +agenda 和 task +get-my-tasks，生成指定日期的日程与未完成任务摘要。适用于了解今天/明天/本周的安排。 |
| multi-stock-comparison | `doubao/skills/multi-stock-comparison` | skill | 29 | 对两家及以上上市公司或股票进行横向研究，覆盖大盘与板块、外围市场、供应链、重要新闻与监管、商业模式、经营财务、成长、预期、估值、股价、组合以及 A/H 股与跨上市地相对价值。适用于公司比较、选股、财报或估值对比、股价与事件复盘、供应链或监管分析、组合适配、配对交易、H 股相对价值，以及需要飞书文档、高级金融图表或可复核多维报告的任务。 |
| seed-audio | `doubao/skills/seed-audio` | skill | 3 | 用自然语言描述生成目标音频。把一段场景描述（人声对话、环境声、音效、背景音乐等复合音频）一次性生成成音频。当用户描述一个声音场景、要求生成/合成/制作一段音频或声音、给出形如"角色：台词"的对话脚本要转成音频、或要按参考音频的音色说话时使用。支持两种模式：纯文本描述生成（T2A）和带参考音频生成（A2A，在描述中引用参考音频指定角色音色） |
| seedance-25 | `doubao/skills/seedance-25` | skill | 1 | 使用seedance2.5模型生成视频,使用 Seedance 2.5 按用户原始提示词生成视频，禁止改写提示词或切换模型，并在生成前补齐时长、比例和检索所得的必要信息后向用户确认原样透传提示词、不润色视频 prompt、不要改写后生成，或显式调用本 Skill 时使用。 |
| skill-creator-for-work | `doubao/skills/skill-creator-for-work` | skill | 6 | 创建有效 Skill 的指南。当用户想要创建新的 Skill，或更新现有 Skill，以便通过专门知识、工作流程或工具集成来扩展 AI Agent 能力时，应使用此 Skill。 |
| student-discount-application | `doubao/skills/student-discount-application` | skill | 13 | 办理豆包专业版学生优惠申请：引导用户绑定抖音、完成学生认证并领取权益。仅当用户明确提出申请、继续办理或查询申请状态时加载；单纯咨询优惠或诉求不明确时不加载。 |
| verifier-hub | `doubao/skills/verifier-hub` | skill | 18 | >- |

## 最近变更

| Date | Change Log | Summary |
| --- | --- | --- |
| 2026-08-25-205036 | [2026-08-25-205036](doubao/change-logs/2026-08-25-205036.md) | Doubao 本次同步新增 4 个文件、修改 11 个文件、删除 1 个文件。 新增条目：skills/doubao-enterprise-search。 受影响范围：skills/doubao-enterprise-search, skills/lark-doc, skills/lark-slides-pro。 |
| 2026-08-22-165330 | [2026-08-22-165330](doubao/change-logs/2026-08-22-165330.md) | Doubao 本次同步新增 85 个文件、修改 21 个文件、删除 74 个文件。 新增条目：skills/byted-mediakit-audio, skills/byted-mediakit-editing, skills/byted-mediakit-image, skills/byted-mediakit-shared, skills/byte... |
| 2026-08-20-180002 | [2026-08-20-180002](doubao/change-logs/2026-08-20-180002.md) | Doubao 本次同步新增 63 个文件、修改 67 个文件、删除 2 个文件。 新增条目：skills/artifact-preview, skills/browser-use-automation, skills/verifier-hub。 受影响范围：skills/artifact-preview, skills/browser-use-auto... |
| 2026-08-14-222038 | [2026-08-14-222038](doubao/change-logs/2026-08-14-222038.md) | Doubao 本次同步新增 132 个文件、修改 162 个文件、删除 84 个文件。 新增条目：skills/computer-use, skills/lark-slides-pro。 移除条目已归档：skills/doubao-finance-sector, skills/lark-ppt。 受影响范围：skills/computer-use, s... |
| 2026-08-12-180003 | [2026-08-12-180003](doubao/change-logs/2026-08-12-180003.md) | Doubao 本次同步新增 17 个文件、修改 12 个文件、删除 2 个文件。 受影响范围：skills/doubao-creative-design, skills/student-discount-application。 |
| 2026-08-11-180003 | [2026-08-11-180003](doubao/change-logs/2026-08-11-180003.md) | Doubao 本次同步新增 1 个文件、修改 19 个文件、删除 0 个文件。 受影响范围：skills/doubao-academic-researcher, skills/doubao-finance-model-builder, skills/doubao-identity。 |
| 2026-08-10-155148 | [2026-08-10-155148](doubao/change-logs/2026-08-10-155148.md) | Doubao 本次同步新增 1543 个文件、修改 214 个文件、删除 39 个文件。 新增条目：skills/doubao-announcement-analysis, skills/doubao-book-writer, skills/doubao-compliance-assessment-public, skills/doubao-contr... |
| 2026-07-23-203625 | [2026-07-23-203625](doubao/change-logs/2026-07-23-203625.md) | 本次同步新增 65 个文件、修改 0 个文件、删除 0 个文件。 新增 skill：doubao-academic-researcher, doubao-clinical-decision-support, doubao-industry-analysis, doubao-medical-literature-search。 受影响范围：doubao-... |
| 2026-07-18-180002 | [2026-07-18-180002](doubao/change-logs/2026-07-18-180002.md) | 本次同步新增 25 个文件、修改 57 个文件、删除 18 个文件。 新增 skill：doubao-medical-report, doubao-record。 移除的 skill 已归档：xiaohe-medical-report。 受影响范围：doubao-medical-report, doubao-record, lark-doc, lark... |
| 2026-07-15-172708 | [2026-07-15-172708](doubao/change-logs/2026-07-15-172708.md) | 本次同步新增 96 个文件、修改 2 个文件、删除 7 个文件。 新增 skill：doubao-academic-evaluator, doubao-academic-polish, doubao-identity, doubao-newmedia-writing, xiaohe-medical-report。 移除的 skill 已归档：douba... |
| 2026-07-13-180002 | [2026-07-13-180002](doubao/change-logs/2026-07-13-180002.md) | 本次同步新增 57 个文件、修改 60 个文件、删除 5 个文件。 受影响范围：doubao-creative-design, doubao-creative-drama, doubao-cron-scheduler, doubao-qa, lark-approval, lark-base, lark-calendar, lark-doc, lark-... |
| 2026-07-07-161744 | [2026-07-07-161744](doubao/change-logs/2026-07-07-161744.md) | 本次同步新增 461 个文件、修改 0 个文件、删除 0 个文件。 新增 skill：browser-task, doubao-app-builder, doubao-creative-design, doubao-creative-drama, doubao-creative-video, doubao-cron-scheduler, doubao-... |
