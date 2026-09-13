# QwenWork Skills And Experts

本文件由 `scripts/sync_platform.py --platform qwenwork` 自动生成，整理 `qwenwork/` 下同步的技能、专家团和插件索引。

## 同步概览

- 平台目录：`qwenwork/`
- 定时任务：`QwenworkSkillsDailySync`，每天 18:00 运行
- 当前索引条目数：45
- 当前索引文件数：2245
- 最近变更：[2026-09-13-180003](qwenwork/change-logs/2026-09-13-180003.md) - QwenWork 本次同步新增 274 个文件、修改 3 个文件、删除 607 个文件。 新增条目：skills/.dws-skill-state.json, skills/dingtalk-aisearch, skills/dingtalk-aitable, skills/dingtalk-calendar, skills/dingtalk-chat...

## 数据来源

- `experts` <= `/mnt/c/Users/15805/.qwenworkcn/plugins`
- `skills` <= `/mnt/c/Users/15805/.qwenworkcn/skills`

## 导航文件

各同步目录根部的 `SUMMARY.md` 提供按用途分组的场景导航，便于快速定位：

- [Experts](qwenwork/experts/SUMMARY.md) — `experts/` 功能导航
- [Skills](qwenwork/skills/SUMMARY.md) — `skills/` 功能导航

## 分类索引

### Experts

| Name | Directory | Category | Files | Description |
| --- | --- | --- | ---: | --- |
| 律师办案大管家 | `qwenwork/experts/Legal-Department` | legal | 366 | 面向执业律师的民商事诉讼办案助手，23 项能力覆盖接案→检索→分析→证据→文书→庭审→执行→结案。带办案中枢统一入口与流水线编排、5 分钟冷启动建立个人办案画像、案件管家管台账与诉讼期限。三大特点：①权威数据逐条核验——法规、案例、企业工商检索在用户于数据连接中启用相应连接器后，运行时按能力语义自动发现并多家灾备、逐条核验可溯源；未连接时套件仍可运行并按能力矩阵降级，其中法条与案例等权威引用拒绝降级、宁可停下也不编造；②规范 Wo... |
| 1688买家助手 | `qwenwork/experts/ali1688-buyer-assistant` | expert | 226 | 为1688买家提供选品找货、找商找厂、询盘寻源、分销铺货、88生意通等一站式采购服务，并新增UTP交易闭环（搜索→加购→下单→支付端内完成），让采购决策和生意经营更快、更准、更省心。 |
| 1688商家助手 | `qwenwork/experts/ali1688-seller-assistant` | expert | 113 | 从店铺诊断到商品运营，为1688商家提供一站式经营支持，帮助商家看清数据、优化商品、提升转化。 |
| 选址顾问 | `qwenwork/experts/amap-site-selection` | expert | 27 | 面向连锁品牌拓展与个体创业者的门店选址专家能力包。基于高德问店五维选址模型（客群聚集、潜客匹配、同行竞争、交通便利、商业成熟），覆盖商圈推荐、点位评估、多点位对比、立项报告四类完整任务。 |
| 婚姻家事法律专家 | `qwenwork/experts/cn-family-law-expert-suite` | expert | 46 | 面向中国大陆婚姻家事法律工作的端到端专家套件，覆盖分轮访谈、事实证据账本、财产债务与子女方案、现行法规和类案检索、婚前及婚内财产协议、离婚协议、同居协议、分家析产协议、成年意定监护协议、正式文档生成与法律质检。正式法律成果须经中国大陆执业律师实质复核批准。 |
| 咨询交付 | `qwenwork/experts/consulting-delivery` | expert | 12 | 管理咨询全流程工具，覆盖桌面调研、访谈纪要、方案框架、报告撰写、标杆对比、项目周报和CEO汇报七大场景。独立可用，连接文档协作平台后可将产出自动发布至钉钉文档、飞书文档、Notion或Google Docs。 |
| 内容创作专家 | `qwenwork/experts/content-creation-suite` | expert | 543 | 面向自媒体、内容创作者与市场运营的全流程内容创作工具箱，覆盖选题发现→爆款拆解→知识沉淀→风格学习→图文创作→视频编导→口播脚本→图片生成→智能排版→跨平台发布的完整创作链路。 |
| 合同管理 | `qwenwork/experts/contract-management` | expert | 12 | 合同全生命周期管理：审查合同风险（红黄绿分级）、起草合同初稿（Word输出）、两版合同红线对比、NDA快速分诊、法条速查、合同台账到期提醒。基于《民法典》合同编及配套司法解释，覆盖企业常见合同场景，支持北大法宝实时法条检索增强。 |
| 企业财税 | `qwenwork/experts/corporate-finance-tax` | expert | 14 | 企业财务和税务管理工具，覆盖财务分析、记账凭证、预算分析、增值税管理、汇算清缴、内部审计、财务报表编制和月结管理九大场景。适用于会计记账、税务申报、财务诊断、预算管控、合规审计、报表编制和月末关账。触发词："财务分析"、"杜邦分析"、"做凭证"、"记账"、"会计分录"、"增值税"、"税负率"、"进销项"、"汇算清缴"、"纳税调整"、"税前扣除"、"预算差异"、"预实对比"、"内部审计"、"审计底稿"、"内控评价"、"SOX审计"、... |
| 企业法务 | `qwenwork/experts/corporate-legal` | expert | 13 | 企业综合法务助手：起草法律文书（律师函/起诉状/答辩状/代理词）、生成公司决议及章程修正案（2024新《公司法》）、类案检索与胜率预判、多领域合规审查（个保/广告/资质/数据安全/跨境合规）、企业背景调查与量化风险评级、法律风险矩阵评估、法务日报/周报自动生成、电子签流程发起。独立运行覆盖全流程，连接北大法宝、旷湖企业信息、DocuSign、Gmail等服务后自动增强。 |
| 投研分析 | `qwenwork/experts/equity-research` | expert | 14 | 券商/基金投研全流程工具，覆盖深度报告、行业研究、年报解读、业绩快评、调研纪要、晨会纪要、研报摘要和可比公司分析八大场景。支持连接金融数据MCP自动拉取财务/行情数据，也可纯手动输入使用。 |
| 投行业务 | `qwenwork/experts/investment-banking` | expert | 11 | 投行全业务AI助手，覆盖IPO招股书起草、并购重组报告书、债券募集说明书、交易所问询回复、路演推介材料和财务建模六大核心场景。自动适配科创板/创业板/主板/北交所及交易所/银行间市场的差异化监管要求，内置注册制信披格式准则和合规检查。支持永续债、绿色债券、ABS等创新品种，以及SOTP分部估值和情景分析。 |
| 市场营销 | `qwenwork/experts/marketing` | expert | 14 | 市场营销全场景工具，覆盖营销文案、广告合规、竞品追踪、活动策划、社媒热点追踪、SEO优化、营销效果分析和品牌调性审查八大场景。独立可用，连接文档协作/数据表格/竞品情报/设计工具/待办工具 MCP 后能力增强。 |
| 股权投资 | `qwenwork/experts/pe-vc-investment` | expert | 14 | PE/VC股权投资全流程工具，覆盖项目筛选、尽调清单、条款审查、投决备忘录、收益测算和退出分析六大场景。适用于投资经理、投资总监、合伙人。触发词：看BP、筛项目、尽调清单、审条款、投决备忘录、测收益、退出分析、算IRR。 |
| 亚马逊运营助手 | `qwenwork/experts/proboost-amazon-operations-assistant` | expert | 18 | 使用OpenBoost数据，覆盖Amazon类目研究、选品、榜单机会、关键词、流量结构和ASIN诊断，输出可复查的机会清单与行动建议。 |
| 产品设计 | `qwenwork/experts/product-design` | expert | 115 | 设计师全流程工具箱，覆盖问题定义、用户研究、信息架构、交互流程、视觉规范、营销物料、动效开发、设计走查、可用性测试、工程交付和项目复盘十一大核心场景。28 个 Skill 串成链式工作流，每个 Skill 自动读取前序产出，避免重复填写项目信息。每个技能内置行业方法论、条件分支和输出模板，产出可直接交付。像一位资深设计搭子，带你从模糊需求一步步走到可交付方案，不掉链子、不漏环节。 |
| 产品管理 | `qwenwork/experts/product-management` | expert | 14 | 产品经理全流程工具箱，覆盖PRD撰写、用户故事拆解、竞品分析、需求优先级排序、用户反馈分析、产品指标复盘、路线图更新和产品脑暴八大核心场景。每个技能内置行业方法论、条件分支和输出模板，产出可直接交付。连接文档平台可将PRD和报告直接写入团队知识库，连接表格工具可读写需求池和反馈数据，连接任务工具可将拆解结果自动创建为待办任务，连接项目管理工具可自动同步迭代状态。 |
| 中国民商事诉讼工具箱 | `qwenwork/experts/qwenwork-cn-litigation` | legal | 57 | Full-lifecycle Chinese civil & commercial litigation toolkit for legal counsel and attorneys. 20 skills across four layers: routing (hub + onboarding interview + quick-config editor), document drafting (complaint, def... |
| 财富管理 | `qwenwork/experts/wealth-management` | expert | 11 | 财富管理全场景工具，覆盖市场速览、资产配置、基金分析、客户报告、理财规划和税务筹划六大场景。面向理财经理、私行客户经理、基金研究员和家族办公室，提供从市场动态跟踪、客户画像分析到配置落地、定期报告的完整工作流。 |
| 科技服务顾问 | `qwenwork/experts/yqx-tech-service-suite` | engineering | 44 | A full-chain technology service toolkit bridging demand and supply in a closed loop. The demand side covers tech demand mining, results search & matching, value assessment, deal plan generation, full-lifecycle project... |

### Skills

| Name | Directory | Category | Files | Description |
| --- | --- | --- | ---: | --- |
| create-skill | `qwenwork/skills/create-skill` | skill | 3 | Guides users through creating effective Agent Skills for QwenWork. Use when the user wants to create, write, or author a new skill, or asks about skill structure, best practices, or SKILL.md format. |
| dingtalk-aisearch | `qwenwork/skills/dingtalk-aisearch` | skill | 4 | AI搜问：人员语义搜索与跨源定位。Use when 按姓名/工号/部门/职责/上下级或手机号线索找人，跨文档/消息/邮件/听记检索，或回溯“我发过/收到过”。完整手机号反查走 dingtalk-contact；找到 userId 后由 contact 补详情。命令前缀：dws aisearch。 |
| dingtalk-aitable | `qwenwork/skills/dingtalk-aitable` | skill | 42 | 钉钉 AI 表格（多维表）。Use when 用户说 AI表格/多维表/数据表/base/table/建表/查记录/写数据/字段/记录增删改查/筛选/排序/公式/模板搜索/批量导入CSV或JSON/导出/仪表盘/图表/上传附件到表格/按字段类型建表/数据源/创建数据源/更新数据源配置/触发数据源同步/按任务 ID 查询同步状态/获取数据源配置/列出数据源可用来源/获取数据源可同步字段/审批数据同步。不做电子表格单元格读写（走 di... |
| dingtalk-calendar | `qwenwork/skills/dingtalk-calendar` | skill | 8 | 钉钉日历与会议室。Use when 用户说 约会议/查日程/订会议室/查闲忙/加参会人/改期/取消会议/今天的日程/本周日程/共同空闲。不做视频会议发起/邀请入会/会中控制（走 dingtalk-misc）、AI 听记（走 dingtalk-minutes）、待办任务（走 dingtalk-todo）。命令前缀：dws calendar。 |
| dingtalk-chat | `qwenwork/skills/dingtalk-chat` | skill | 18 | 钉钉群聊与消息。Use when 发消息、单聊/群聊、建群、群设置/成员、搜索/回复、机器人/Webhook、消息文件。DING 和班级群走 dingtalk-misc；邮件走 dingtalk-mail。前缀 dws chat。 |
| dingtalk-contact | `qwenwork/skills/dingtalk-contact` | skill | 7 | 钉钉通讯录精确查询。Use when 已有 userId 后查详情、部门、职位或邮箱，按完整手机号反查用户，或查询自己、部门成员及角色。姓名模糊搜索、工号、职责、上下级走 dingtalk-aisearch，拿到 userId 后用本 skill 补详情。命令前缀：dws contact。 |
| dingtalk-doc | `qwenwork/skills/dingtalk-doc` | skill | 20 | 钉钉在线文字文档（adoc）本体及其内容的操作：查找、创建、读取、文档信息、编辑、块、评论、附件与媒体、白板卡片容器插入删除、导入、导出(docx/markdown/pdf)、版本、模板、协作者权限、分享及Markdown/JSONML写入。不包括：白板/画布内的 OpenNodes 图形、文本、分组、连线、Vector 和布局读写（归 dingtalk-misc 的 Whiteboard）、文档空间与钉盘的文件管理（归 ding... |
| dingtalk-drive | `qwenwork/skills/dingtalk-drive` | skill | 5 | 钉钉文件管理（存储层，覆盖钉盘与文档空间）。Use when 用户说 钉盘/文档空间/我的文档中的普通文件或文件夹、查找/上传/下载/复制/移动/重命名/删除/回收站/权限/评论/元信息，或本地与钉盘文件夹比较、拉取、推送、双向同步；也承接在线文档节点的存储管理。文档正文编辑与导出走 dingtalk-doc；明确的知识库空间及空间内节点组织走 dingtalk-wiki。命令前缀：dws drive。 |
| dingtalk-event | `qwenwork/skills/dingtalk-event` | skill | 9 | 钉钉个人 IM、OA 审批、VoIP 通话邀请与待办事件长连接监听。Use when 用户说监听消息/@我/某人/某群/全部消息、已读/撤回/reaction、群成员加入/群成员退出/群状态变化，监听审批任务创建/完成/转交、审批实例发起/抄送/终止/完成、VoIP 通话邀请，或监听待办创建/更新/删除。命令前缀：dws event。 |
| dingtalk-mail | `qwenwork/skills/dingtalk-mail` | skill | 8 | 钉钉邮箱读写、搜索、回复与转发。Use when 用户说发邮件/查邮件/回邮件/转发邮件/未读邮件/邮件搜索/邮箱附件。一句话发邮件时先用 dingtalk-contact 解析并确认收件人，再由本 skill 发送；不做钉钉消息（走 dingtalk-chat）、紧急通知（走 dingtalk-misc）。命令前缀：dws mail。 |
| dingtalk-minutes | `qwenwork/skills/dingtalk-minutes` | skill | 10 | 钉钉 AI 听记。Use when 查询或修改听记摘要、完整逐字稿、关键词、行动项、录音、上传、思维导图、发言人洞察或分享权限。写文档走 dingtalk-doc；建待办走 dingtalk-todo；日程走 dingtalk-calendar。命令前缀：dws minutes。 |
| dingtalk-misc | `qwenwork/skills/dingtalk-misc` | skill | 112 | 长尾产品集合技能，覆盖低频钉钉产品：OA审批查询与处理/考勤/直播/DING紧急消息/开放平台应用管理/Agoal目标管理/日志日报周报/电子表格/开放平台文档搜索与OpenAPI逃生舱/文档内嵌白板/钉钉招聘/DWS技能市场安装/组织大脑Hrbrain/原生Markdown/PAT行为授权/多组织profile。Use when 用户提到上述任一产品，或查待审批/同意拒绝转交撤销审批/打卡/排班/OKR/日报周报/单元格读写/白... |
| dingtalk-shared | `qwenwork/skills/dingtalk-shared` | skill | 15 | 钉钉(DingTalk) MultiSkill 的轻量共享入口。Use when 用户泛称 DWS/钉钉操作但未明确产品、请求跨产品编排、需要 URL 类型预检或产品边界消歧。清晰的单产品操作优先使用对应 dingtalk-* 子 skill；本 skill 只提供全局执行契约和按需 reference 导航，不承载产品命令全集。 |
| dingtalk-todo | `qwenwork/skills/dingtalk-todo` | skill | 9 | 钉钉待办 / TODO。Use when 用户说 创建待办/TODO/任务提醒/指派任务/标记完成/查待办/紧急待办/循环待办/批量建待办/逾期待办。不做日报周报（走 dingtalk-misc）、审批（走 dingtalk-misc）、日程（走 dingtalk-calendar）。命令前缀：dws todo。 |
| dingtalk-wiki | `qwenwork/skills/dingtalk-wiki` | skill | 6 | 钉钉知识库与空间管理。Use when 用户明确说 知识库/wiki/创建、查找或列出知识库/命名的团队知识空间/个人知识库/知识库成员/库内节点创建、列表、搜索、复制、移动、删除或知识库动态。仅说“文档空间/我的文档”不触发：普通存储管理与全局文件搜索走 dingtalk-drive；节点正文读写走 dingtalk-doc。命令前缀：dws wiki。 |
| docx | `qwenwork/skills/docx` | skill | 61 | Comprehensive Word (.docx) skill: create, read, edit, and manipulate Word documents end-to-end. Covers turning Markdown or structured text into polished Word output, filling reusable templates ({{token}} or reference-... |
| find-skills | `qwenwork/skills/find-skills` | skill | 4 | Do NOT invoke this skill as a routine first step. Do NOT invoke when any installed skill (see the available skills list) can handle the task, or when general capabilities (writing, coding, analysis, translation, web s... |
| media-generation | `qwenwork/skills/media-generation` | skill | 1 | Generate or edit images with automatic model selection or a supported model explicitly requested by the user, generate videos, or create music as asynchronous media artifacts. Use this skill when the user asks for tex... |
| pdf | `qwenwork/skills/pdf` | skill | 53 | Operates on PDF files: inspect/fill forms, merge/split, watermark, encrypt/decrypt, strip metadata, extract tables or images, compress, validate, render pages to images (so the agent can read scanned PDFs with vision)... |
| plugin-creator | `qwenwork/skills/plugin-creator` | skill | 1 | Create, customize, or modify QwenWork / QwenWorkCN expert plugins. Use when the user wants to create a new plugin, customize an existing plugin, or edit a plugin's skills/commands. |
| pptx | `qwenwork/skills/pptx` | skill | 103 | Use this skill any time a PowerPoint .pptx or legacy .ppt file is involved as input, output, or both. This includes creating decks; reading or extracting slide content; editing presentations; combining or splitting sl... |
| qw-pages | `qwenwork/skills/qw-pages` | skill | 1 | Publish static or dynamic HTML, websites, and web applications through QW Pages. Use when the user asks to publish, deploy, or make a webpage live. Combine with qw-pages-supabase only when the webpage needs persistent... |
| qw-pages-supabase | `qwenwork/skills/qw-pages-supabase` | skill | 1 | Prepare Supabase-compatible persistent storage for a dynamic QW Page. Use with qw-pages when a webpage needs database tables, server-side persistence, Supabase access, or database-backed APIs. |
| qwenwork-guidance | `qwenwork/skills/qwenwork-guidance` | skill | 7 | Routing guide for the built-in QwenWork Connector tools (mcp__qw-builtin__qw_query / mcp__qw-builtin__qw_action). Load ONLY right before calling them to view or manage QwenWork's OWN tasks/sessions or app configuratio... |
| xlsx | `qwenwork/skills/xlsx` | skill | 53 | Use this skill any time a spreadsheet file is the primary input or output. This means any task where the user wants to: open, read, edit, or fix an existing .xlsx, .xlsm, .csv, or .tsv file (e.g., adding columns, comp... |

## 最近变更

| Date | Change Log | Summary |
| --- | --- | --- |
| 2026-09-13-180003 | [2026-09-13-180003](qwenwork/change-logs/2026-09-13-180003.md) | QwenWork 本次同步新增 274 个文件、修改 3 个文件、删除 607 个文件。 新增条目：skills/.dws-skill-state.json, skills/dingtalk-aisearch, skills/dingtalk-aitable, skills/dingtalk-calendar, skills/dingtalk-chat... |
| 2026-09-05-180002 | [2026-09-05-180002](qwenwork/change-logs/2026-09-05-180002.md) | QwenWork 本次同步新增 129 个文件、修改 246 个文件、删除 75 个文件。 受影响范围：skills/create-skill, skills/dws, skills/media-generation, skills/plugin-creator, skills/pptx。 |
| 2026-08-30-205640 | [2026-08-30-205640](qwenwork/change-logs/2026-08-30-205640.md) | QwenWork 本次同步新增 774 个文件、修改 10 个文件、删除 0 个文件。 新增条目：experts/amap-site-selection, experts/cn-family-law-expert-suite, experts/content-creation-suite, experts/proboost-amazon-operati... |
| 2026-08-24-180002 | [2026-08-24-180002](qwenwork/change-logs/2026-08-24-180002.md) | QwenWork 本次同步新增 103 个文件、修改 7 个文件、删除 11 个文件。 受影响范围：skills/pdf, skills/pptx。 |
| 2026-08-17-180001 | [2026-08-17-180001](qwenwork/change-logs/2026-08-17-180001.md) | QwenWork 本次同步新增 368 个文件、修改 0 个文件、删除 0 个文件。 新增条目：experts/Legal-Department, skills/qw-pages, skills/qw-pages-supabase。 受影响范围：experts/Legal-Department, skills/qw-pages, skills/qw-p... |
| 2026-08-10-160206 | [2026-08-10-160206](qwenwork/change-logs/2026-08-10-160206.md) | QwenWork 本次同步新增 0 个文件、修改 1 个文件、删除 0 个文件。 受影响范围：skills/dws。 |
| 2026-08-09-180003 | [2026-08-09-180003](qwenwork/change-logs/2026-08-09-180003.md) | QwenWork 本次同步新增 0 个文件、修改 1 个文件、删除 0 个文件。 受影响范围：skills/dws。 |
| 2026-08-08-180003 | [2026-08-08-180003](qwenwork/change-logs/2026-08-08-180003.md) | QwenWork 本次同步新增 401 个文件、修改 20 个文件、删除 1 个文件。 受影响范围：skills/create-skill, skills/dws。 |
| 2026-08-05-231200 | [2026-08-05-231200](qwenwork/change-logs/2026-08-05-231200.md) | QwenWork 本次同步新增 891 个文件、修改 0 个文件、删除 0 个文件。 新增条目：experts/ali1688-buyer-assistant, experts/ali1688-seller-assistant, experts/consulting-delivery, experts/contract-management, expe... |
