# QwenWork Skills And Experts

本文件由 `scripts/sync_platform.py --platform qwenwork` 自动生成，整理 `qwenwork/` 下同步的技能、专家团和插件索引。

## 同步概览

- 平台目录：`qwenwork/`
- 定时任务：`QwenworkSkillsDailySync`，每天 18:00 运行
- 当前索引条目数：265
- 当前索引文件数：4761
- 最近变更：[2026-10-15-192505](qwenwork/change-logs/2026-10-15-192505.md) - QwenWork 本次同步新增 0 个文件、修改 1 个文件、删除 0 个文件。 受影响范围：skills/wecom-unified。

## 数据来源

- `experts` <= `/mnt/c/Users/15805/.qwenworkcn/plugins`
- `skills` <= `/mnt/c/Users/15805/.qwenworkcn/skills`
- `connectors/mcp.json` <= `/mnt/c/Users/15805/.qwenworkcn/mcp.json`
- `connectors/market-metadata.json` <= `/mnt/c/Users/15805/.qwenworkcn/cache/mcp/market-metadata-cn.json`

## 导航文件

各同步目录根部的 `SUMMARY.md` 提供按用途分组的场景导航，便于快速定位：

- [Experts](qwenwork/experts/SUMMARY.md) — `experts/` 功能导航
- [Skills](qwenwork/skills/SUMMARY.md) — `skills/` 功能导航
- [Connectors / Installed Registry](qwenwork/connectors/SUMMARY.md) — `connectors/` 功能导航

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
| A股个股技术诊断 | `qwenwork/skills/a-stock-diagnosis` | 金融投研 | 2 | A股个股深度技术诊断工具。基于60日K线数据计算MA5/10/20/60均线、量价关系、 支撑压力位和风险信号，由 Agent 进行多维分析并输出结构化诊断报告。 Use when: (1) 用户说"帮我分析下这只股票""诊断下600519", (2) 用户问"XX技术面怎么样""趋势如何", (3) 用户要求"个股诊断""综合评估""支撑位在哪", (4) 用户要求多只股票对比分析。 Distinct from: a-stock... |
| A股实时行情与持仓 | `qwenwork/skills/a-stock-realtime` | 金融投研 | 4 | A股实时行情快查与持仓盈亏管理。秒级获取沪深A股现价、涨跌幅、成交量， 分析当日分时量能分布（早盘/尾盘放量）、主力抢筹/出货异常信号。 支持个人持仓管理（添加/更新/删除）和实时盈亏计算。 Use when: (1) 用户问"XX股票现在多少钱""查下600519价格", (2) 用户关注"主力动向""今天早盘放量了吗", (3) 用户说"看看我的持仓""加一只股票到持仓""持仓盈亏怎么样"。 Distinct from: a-... |
| 电商活动推荐 | `qwenwork/skills/activity-recommend` | 市场营销 | 2 | 营销托管活动智能推荐。根据商家的自然语言描述（如"我想找适合新品的活动"、"有没有流量补贴的活动"、"帮我推荐几个高转化的活动"），调用推荐接口获取匹配活动，解析并整理活动基本信息、起止时间、推荐介绍，以结构化列表返回给商家。当商家想找活动、选活动、了解有什么合适活动时使用。 |
| 千问办公任务台账 | `qwenwork/skills/agent-task-hub` | 沟通协作 | 24 | 把千问办公的 agent 任务沉淀到钉钉 AI表格，形成跨 agent、跨窗口的「任务台账 + 交接登记表」。 支持创建/初始化个人台账（定时增量同步）与团队接续台账（仅 handoff 触发写摘要，保护隐私）。 当用户需要创建团队 Agent 台账、创建个人任务台账、定时沉淀/同步任务、交接、交接分支/模块/任务给某人、接手交接任务、认领任务、续接、接着做、开新会话续接、handoff、resume、查询待接续任务时使用。 |
| AI表格数据可视化分析 | `qwenwork/skills/ai-table-data-analyzer` | 数据分析 | 4 | 数据可视化与可视化数据分析报告：将本地 Excel/CSV/TSV、钉钉在线电子表格(axls)或已有钉钉 AI 表格统一转为 AI 表格数据源，根据数据特征设计图表组合，在其上创建原生可视化仪表盘(dashboard：指标卡/趋势/构成/排名图表)，是"上传表格出数据可视化报告"(data-report 类)诉求的钉钉原生方案。 TRIGGER: 用户要求把 Excel/CSV/在线表格做成钉钉看板/仪表盘/数据大屏/数据可视化... |
| AI表格数据源插件生成器 | `qwenwork/skills/ai-table-datasource-plugin-generator` | 数据分析 | 65 | 快速生成、修改和调试钉钉 AI 表格数据源连接器插件，覆盖前后端项目初始化、 MySQL/PostgreSQL/SQL Server/Oracle 数据源代码生成、本地环境配置、账号代管接入和发布指导。 当用户提出创建数据源插件、生成 AI 表格连接器代码、改造或排查已有数据源插件、配置本地调试环境、 接入三方账号代管或了解插件发布流程时使用。 |
| AI表格插件开发 | `qwenwork/skills/ai-table-script-generator` | 开发工具 | 64 | 钉钉 AI 表格（多维表）插件开发专家，根据需求直接产出可运行的插件代码。 当用户提到“写 AI 表格脚本”“创建表格自动化脚本”“生成多维表代码”“做个边栏插件” “搭个表格插件界面”，或提到字段批量操作、记录增删改查、数据校验、按钮字段触发、 表格事件监听、选区联动等场景时使用。支持两种形态：脚本插件（TypeScript 自动化） 与边栏插件（React 双页架构）。 |
| AI表格数据分析助手 | `qwenwork/skills/ai-table-stats-query` | 数据分析 | 2 | 使用本机 dws CLI 准确回答指定 AI 表格中的计数、求和、平均值、分组统计、Top N、中位数、去重计数、完整率、比率、百分比、分位数、排名和数据分布问题。用户询问“多少家门店”“有索赔单的门店共有多少家”“多少个客户、商品或员工”等自然语言唯一实体计数时也应触发，即使只提供钉钉 AI 表格链接。整个任务只能读取上游绑定、人设 notable 引用或用户明确链接指定的唯一 Base；禁止列出、搜索、猜测或切换其他 Base... |
| AI表格搭建系统 | `qwenwork/skills/aitable-app-builder` | 数据分析 | 178 | 将业务需求设计并搭建为可实际使用的钉钉 AI 表格应用，也可诊断和完善已有应用。适用于客户管理、项目任务、信息收集、工单、库存、内容排期及其他结构化业务场景；负责数据模型、字段关系、视图、表单、自动化、权限、仪表盘、DWS 执行和读回验收。 |
| AI表格会议行动项追踪 | `qwenwork/skills/aitable-meeting-actions` | 数据分析 | 2 | 会议纪要转行动项追踪表。从钉钉 AI 听记中提取会议行动项，经适合度判断与责任人/截止时间解析后， 沉淀到钉钉 AI 表格的行动项追踪表中持续跟踪，并可选为责任人创建钉钉待办。 当用户提到会议行动项、会议待办入表、听记转追踪表、把周会任务沉淀到表格、会议纪要整理成任务时使用。 |
| AI表格汇报PPT | `qwenwork/skills/aitable-report-ppt` | 数据分析 | 171 | 从钉钉 AI 表格、多维表、数据表或已有 Word/PPT/HTML 生成内容先确认、可追溯、可下钻、可导出 PDF 的单文件 PPT 式可视化报告（默认固定 16:9 演示稿），图表可下钻回钉钉原始记录。 当用户提到把 AI 表格做成 PPT、汇报 PPT、管理报告、可视化报告、HTML 报告、仪表盘、数据汇报页面、下钻报告、打印报告，或只说"做个汇报PPT""做个汇报页面""把这个表可视化""生成仪表盘"时使用； 也用于把 P... |
| 阿里云一键部署工具 | `qwenwork/skills/alibabacloud-ecs-code-deploy` | 开发工具 | 10 | Install Alibaba Cloud CLI (aliyun) and deploy projects to Alibaba Cloud ECS using aliyun appmanager commands. Use when the user wants to deploy applications or AI agents to ECS, set up aliyun CLI, or use appmanager in... |
| 文档解析 | `qwenwork/skills/aliyun-dts-doc-parse` | 知识文档 | 7 | 通过阿里云 DTS-AI 端到端解析 PDF、DOCX、PPTX 和图片等本地文件，并将结果保存为 Markdown。用户提到 DTS-AI 文档解析，或需要把本地 PDF、Word、PowerPoint 或图片解析、转换、提取为 Markdown 时使用。 |
| 网页搜索与网页提取 | `qwenwork/skills/aliyun-dts-web-search` | 效率工具 | 7 | 通过阿里云 DTS-AI 搜索公开网页、发现相关来源并提取指定网页的内容。用户需要联网搜索、查询最新资料或新闻、开展产品或行业调研、查找官方网站或 URL、阅读或抓取网页、比较不同来源、核验事实、汇总网页信息并注明来源，或提到 DTS-AI、WebSearch、WebFetch 时使用。 |
| 标书撰写 | `qwenwork/skills/bid-document` | 知识文档 | 4 | 专业标书撰写技能体系，支持从招标文件解读到文档质量控制的全流程工作。 |
| 视频速读 | `qwenwork/skills/bilibili-summary` | 教育学习 | 1 | 当用户发送B站(bilibili.com)视频链接并要求"总结视频内容"、"帮我总结"、"总结一下这个视频/课程"时触发。生成美观的HTML学习报告+MD归档文件。自动识别单集(详细灵活分析)和多P系列(分组折叠+阶段总结)，支持上百集课程快速输出结构化报告。 |
| 商业计划书生成 | `qwenwork/skills/business-plan` | 市场营销 | 1 | 商业计划书：覆盖市场规模验证（TAM/SAM/SOM）、竞品对比矩阵、商业模式画布到财务预测与融资需求的全链路分析，输出结构化钉钉在线文档商业计划书。 |
| A股深度研究 | `qwenwork/skills/cn-stock-research` | 金融投研 | 1 | 对A股上市公司进行全流程深度研究，自动识别公司分析模式、路由选择合适的分析模块与行业叠加层，并合并为统一的有据可查研究框架。当用户需要对A股公司进行深度研究、个股分析、投资调研，或希望将模糊的"分析这只股票"请求转化为结构化研究工作流时使用。 |
| 公司调研 | `qwenwork/skills/company-research` | 金融投研 | 1 | 公司调研：基于官方与公开信息，输出公司概况、业务结构、竞争位置、经营与风险的结构化研究报告，保存为钉钉在线文档。 |
| 竞品分析 | `qwenwork/skills/competitive-analysis` | 市场营销 | 1 | 竞品分析：通过统一维度对比产品与市场信息，形成结构化对比结论与机会点，输出钉钉在线文档竞品分析报告。 |
| computer-use-guidance-windows | `qwenwork/skills/computer-use-guidance-windows` | 人力招聘 | 2 | Operation guidance for automating the Windows desktop via Computer Use: open apps, read on-screen state through the UIA accessibility tree, click / type / press shortcut keys / scroll / drag / invoke semantic UIA acti... |
| 文本风格转写 | `qwenwork/skills/content-rewriter` | 内容写作 | 5 | 内容改写工具，专注改写、扩写、缩写和风格语气迁移四种操作。当用户提供一段已有文本，要求对其进行改写（换一种说法）、扩写（补充展开）、缩写（压缩精简）、或迁移到指定风格/语气时触发本技能。TRIGGER when: 用户提供原文 + 明确指定操作类型（改写/扩写/缩写/风格迁移/语气调整）；或说\\"帮我改一下\\"\\"把这段扩展一下\\"\\"压缩到XXX字\\"\\"改成XX风格/语气\\"。DO NOT TRIGGER when: 用户要从... |
| 内容选题规划 | `qwenwork/skills/content-strategy` | 市场营销 | 3 | When the user wants to plan a content strategy, decide what content to create, or figure out what topics to cover. Also use when the user mentions "content strategy," "what should I write about," "content ideas," "blo... |
| 中文合同审查技能 | `qwenwork/skills/contract-review-cn` | 法律服务 | 10 | > 专业的中文合同风险识别与修订建议工具 |
| 营销文案润色 | `qwenwork/skills/copy-editing` | 市场营销 | 3 | When the user wants to edit, review, or improve existing marketing copy, or refresh outdated content. Also use when the user mentions 'edit this copy,' 'review my copy,' 'copy feedback,' 'proofread,' 'polish this,' 'm... |
| create-skill | `qwenwork/skills/create-skill` | 系统内置 | 3 | Guides users through creating effective Agent Skills for QwenWork. Use when the user wants to create, write, or author a new skill, or asks about skill structure, best practices, or SKILL.md format. |
| 客户沟通话术 | `qwenwork/skills/customer-communication-writing` | 沟通协作 | 6 | 客户沟通话术写作技能。用于生成、改写、润色、压缩、扩写、结构化中文或英文客户沟通话术，覆盖销售开发、拜访建联、续费挽回、报价异议、竞品对比、客户跟进、售后安抚、客服自动回复、FAQ、群消息、内部协作催办、电话开场白、微信私聊、客户群、邮件、语音提示等场景；尤其适用于用户要求可直接复制、短而自然、有共情、有证据、有下一步 CTA、多个版本或指定渠道语气的短文写作任务。 |
| 客户研究分析 | `qwenwork/skills/customer-research` | 市场营销 | 1 | Multi-source research on a customer question or topic with source attribution. Use when a customer asks something you need to look up, investigating whether a bug has been reported before, checking what was previously... |
| 电商客服话术生成 | `qwenwork/skills/customer-service-reply` | 市场营销 | 2 | 电商客服全场景话术生成技能，覆盖售前咨询、售中跟进、售后处理三大阶段，支持 Amazon/Shopee/AliExpress/TikTok Shop/Temu/Shopify/eBay/Lazada/Taobao/JD/Wish 等 12 大跨境及国内电商平台，内置 1400+ 话术模板并按 30+ 行业垂直适配，按场景匹配模板并填充变量，一键生成可直接发送的中英文客服回复。Use when 用户需要起草电商客服回复话术、处理退款... |
| 数据可视化 | `qwenwork/skills/data-report` | 数据分析 | 33 | 从表格文件 (.xlsx / .xlsm / .csv / .tsv) 生成自包含 HTML 数据分析报告。 含 KPI 卡片、ECharts 图表、文字洞察。数据 inline 嵌入。 TRIGGER: 用户上传表格文件 + 提出分析/出报告/看趋势/做可视化/出 KPI/同环比/ 排名/构成/异常/帕累托/漏斗/留存/归因/分群等诉求时立即触发, 包括"出份报告"/ "做个分析"/"看看数据"这类模糊表达。 PARTIAL:... |
| 去 AI 味写作 | `qwenwork/skills/de-ai-writing-cn` | 内容写作 | 2 | 去模板化写作技能，用于降低 AI 味、提升中文表达自然度与专业感。 |
| 深度决策研究报告 | `qwenwork/skills/deep-decision-research` | 金融投研 | 4 | 主动触发型技能；仅当用户显式选择或明确调用本技能时使用。用于让 QoderWork 围绕一个明确决策目标搜索、研究、整理材料，并按内置 HTML 报告规范生成一份可在浏览器打开的自包含决策辅助报告。 |
| 大厂设计系统 | `qwenwork/skills/design-md` | 设计创意 | 72 | AI UI 设计系统助手。当用户需要生成特定品牌风格的 UI、选择设计系统、应用设计规范、让页面看起来像某个知名网站、或提到 DESIGN.md 时使用。支持 68 个品牌风格（内置离线模板），包括 Stripe、Vercel、Airbnb、Apple、Tesla、Notion、Linear 等。 |
| dingtalk-aisearch | `qwenwork/skills/dingtalk-aisearch` | 沟通协作 | 4 | AI搜问：人员语义搜索、跨源内容定位与行为回溯。Use when 按姓名/工号/部门/职责/上下级找人，或在目标对象未知时按主题、语义、来源或行为发现相关内容。搜索结果用于候选定位；命中后需要读取、修改或验证原对象时切换到对象所属产品。完整手机号精确反查走 dingtalk-contact。命令前缀：dws aisearch。 |
| dingtalk-aitable | `qwenwork/skills/dingtalk-aitable` | 沟通协作 | 44 | 钉钉 AI 表格（多维表）。Use when 用户说 AI表格/多维表/数据表/base/table/应用模式/App 页面/Widget/建表/查记录/写数据/字段/记录增删改查/记录评论/评论回复/SQL/PostgreSQL/SELECT/JOIN/跨表关联查询/筛选/排序/公式/模板搜索/批量导入CSV或JSON/导出/仪表盘/图表/上传附件到表格/按字段类型建表/数据源/创建数据源/更新数据源配置/触发数据源同步/按任务... |
| dingtalk-calendar | `qwenwork/skills/dingtalk-calendar` | 沟通协作 | 8 | 钉钉日历与会议室。Use when 用户说 约会议/查日程/订会议室/查闲忙/加参会人/改期/取消会议/今天的日程/本周日程/共同空闲。不做视频会议发起/邀请入会/会中控制（走 dingtalk-misc）、AI 听记（走 dingtalk-minutes）、待办任务（走 dingtalk-todo）。命令前缀：dws calendar。 |
| dingtalk-chat | `qwenwork/skills/dingtalk-chat` | 沟通协作 | 19 | 钉钉群聊与消息。Use when 收发/搜索消息、建群、群治理、Bot/Webhook、文件，或仅限 IM 的消息谓词筛选。跨源主题/行为轨迹走 dingtalk-aisearch；DING/班级群走 dingtalk-misc；邮件走 dingtalk-mail。 |
| 聊天消息提取待办 | `qwenwork/skills/dingtalk-chat-to-todo` | 沟通协作 | 3 | 从钉钉群聊消息中识别与我相关的任务类内容，自动创建钉钉待办。 拉取全部消息作为上下文，重点识别 @我 和提到我名字的消息，结合前后文准确理解任务内容， 自动过滤即时性事务，只提取适合作为待办跟踪的任务。 Use when user mentions "群消息转待办", "聊天记录转任务", "把群里说的任务记下来", or asks to "提取群里的待办", "把@我的任务建起来", "聊天转待办". Distinct from... |
| dingtalk-contact | `qwenwork/skills/dingtalk-contact` | 沟通协作 | 7 | 钉钉通讯录精确查询。Use when 已有 userId 后查详情、部门、职位或邮箱，按完整手机号反查用户，或查询自己、部门成员及角色。姓名模糊搜索、工号、职责、上下级走 dingtalk-aisearch，拿到 userId 后用本 skill 补详情。命令前缀：dws contact。 |
| dingtalk-doc | `qwenwork/skills/dingtalk-doc` | 沟通协作 | 20 | 钉钉在线文字文档（adoc）内容：查找、创建、读取编辑、块、评论、媒体/附件、白板卡片容器、导入导出、版本、模板、权限、分享及 Markdown/JSONML。不做白板图形/原生 .md/电子表格（dingtalk-misc）、文档空间与钉盘存储（dingtalk-drive）、知识库组织（dingtalk-wiki）、AI 表格（dingtalk-aitable）。命令前缀：dws doc。 |
| dingtalk-drive | `qwenwork/skills/dingtalk-drive` | 沟通协作 | 5 | 钉钉文件管理（存储层，覆盖钉盘与文档空间）。Use when 用户说 钉盘/文档空间/我的文档中的普通文件或文件夹、查找/上传/下载/复制/移动/重命名/删除/回收站/权限/评论/元信息，或本地与钉盘文件夹比较、拉取、推送、双向同步；也承接在线文档节点的存储管理。文档正文编辑与导出走 dingtalk-doc；明确的知识库空间及空间内节点组织走 dingtalk-wiki。命令前缀：dws drive。 |
| 小红书学校舆情助手 | `qwenwork/skills/dingtalk-edu-xhs-keyword-spider` | 沟通协作 | 24 | 搜索小红书关键词相关笔记并生成可视化HTML舆情报告，主要用于获取学校在小红书上的舆情信息。当用户需要查学校小红书舆情、搜索小红书笔记、分析小红书趋势、学校口碑/关键词监控时使用。不要在需要搜索微博/抖音/知乎、创建教案、批改作业、管理课程表时触发。 |
| dingtalk-event | `qwenwork/skills/dingtalk-event` | 沟通协作 | 10 | 钉钉个人 IM、OA 审批、VoIP 通话邀请、待办与互动卡片回调事件长连接监听。Use when 用户说监听消息/@我/某人/某群/全部消息、已读/撤回/reaction、群成员加入/群成员退出/群状态变化，监听审批任务创建/完成/转交、审批实例发起/抄送/终止/完成、VoIP 通话邀请、待办创建/更新/删除，或互动卡片回调。命令前缀：dws event。 |
| dingtalk-mail | `qwenwork/skills/dingtalk-mail` | 沟通协作 | 8 | 钉钉邮箱读写、搜索、回复与转发。Use when 用户说发邮件/查邮件/回邮件/转发邮件/未读邮件/邮件搜索/邮箱附件。一句话发邮件时先用 dingtalk-contact 解析并确认收件人，再由本 skill 发送；不做钉钉消息（走 dingtalk-chat）、紧急通知（走 dingtalk-misc）。命令前缀：dws mail。 |
| dingtalk-minutes | `qwenwork/skills/dingtalk-minutes` | 沟通协作 | 12 | 钉钉 AI 听记。Use when 查询或修改听记摘要、完整逐字稿、关键词、标签、行动项、录音、上传、思维导图、发言人洞察、ASR 热词/识别词配置或分享权限。写文档走 dingtalk-doc；建待办走 dingtalk-todo；日程走 dingtalk-calendar。命令前缀：dws minutes。 |
| dingtalk-misc | `qwenwork/skills/dingtalk-misc` | 沟通协作 | 130 | 长尾产品集合技能，覆盖低频钉钉产品：OA审批查询与处理/法务智能合同/考勤/直播/DING紧急消息/开放平台应用与MCP开发/Agoal目标管理/日志日报周报/电子表格/开放平台文档搜索与OpenAPI逃生舱/独立及文档内嵌白板/钉钉招聘/DWS技能市场安装/人事薪酬绩效/组织大脑Hrbrain/原生Markdown/原生HTML/PAT行为授权/多组织profile。Use when 用户提到上述任一产品，尤其是 Agoal/目... |
| 聊天消息任务追踪-AI表格 | `qwenwork/skills/dingtalk-msg-task-tracker-aitable` | 沟通协作 | 2 | 汇总最近24小时(或指定窗口)钉钉里的双向任务流转,来源固定为5路:群里@我/我发出的单聊任务/别人发我的单聊任务/DING/待办。归类合并同一问题的跨轮讨论,跨天未闭环的问题更新原行不新建,生成日报摘要并推送Markdown卡片到钉钉。当用户说"看下今天钉钉里别人反馈给我的问题""汇总最近一天的反馈到表格""今天我派了什么任务给别人""收下24小时内的问题反馈""检索未完成任务+最新反馈"或类似需求时触发。 |
| dingtalk-shared | `qwenwork/skills/dingtalk-shared` | 沟通协作 | 15 | 钉钉(DingTalk) MultiSkill 的轻量共享入口。Use when 用户泛称 DWS/钉钉操作但未明确产品、请求跨产品编排、需要 URL 类型预检或产品边界消歧。清晰的单产品操作优先使用对应 dingtalk-* 子 skill；本 skill 只提供全局执行契约和按需 reference 导航，不承载产品命令全集。 |
| dingtalk-todo | `qwenwork/skills/dingtalk-todo` | 沟通协作 | 9 | 钉钉待办 / TODO。Use when 用户说 创建待办/TODO/任务提醒/指派任务/标记完成/查待办/紧急待办/循环待办/批量建待办/逾期待办。不做日报周报（走 dingtalk-misc）、审批（走 dingtalk-misc）、日程（走 dingtalk-calendar）。命令前缀：dws todo。 |
| dingtalk-wiki | `qwenwork/skills/dingtalk-wiki` | 沟通协作 | 6 | 钉钉知识库与空间管理。Use when 用户明确说 知识库/wiki/创建、查找或列出知识库/命名的团队知识空间/个人知识库/知识库成员/库内节点创建、列表、搜索、复制、移动、删除或知识库动态。仅说“文档空间/我的文档”不触发：普通存储管理与全局文件搜索走 dingtalk-drive；节点正文读写走 dingtalk-doc。命令前缀：dws wiki。 |
| docx | `qwenwork/skills/docx` | 知识文档 | 61 | Comprehensive Word (.docx) skill: create, read, edit, and manipulate Word documents end-to-end. Covers turning Markdown or structured text into polished Word output, filling reusable templates ({{token}} or reference-... |
| 抖音爆款口播文案 | `qwenwork/skills/douyin-viral-script` | 市场营销 | 3 | 根据话题或书籍生成钩子密集型的抖音爆款口播文案（约 600 字）。 掌握黄金 3 秒原则、钩子密集分布、情绪曲线调动、价值输出等抖音爆款逻辑。 当用户提到"帮我写个抖音文案"、"口播稿"、"爆款文案"、"短视频脚本"、 "抖音口播"、"写个能火的文案"时使用。 不用于长视频脚本、图文内容创作、广告投放文案或非抖音平台内容。 |
| ECharts 图表生成 | `qwenwork/skills/echart` | 数据分析 | 1 | 生成数据可视化图表，支持词云、折线图、柱状图、饼图、面积图及混合图表。 输出自包含 HTML 文件（引入 ECharts CDN），用户点击即可查看高质量图表。 支持导出 PNG 图片。当用户提到"生成图表"、"画个图"、"数据可视化"、 "柱状图"、"折线图"、"饼图"、"词云"、"图表展示数据"时使用。 不用于非 ECharts 的图表库（如 D3、Chart.js），不用于纯数据分析（无图表需求）。 |
| find-skills | `qwenwork/skills/find-skills` | 系统内置 | 4 | Do NOT invoke this skill as a routine first step. Do NOT invoke when any installed skill (see the available skills list) can handle the task, or when general capabilities (writing, coding, analysis, translation, web s... |
| FLYAI-飞猪旅行 | `qwenwork/skills/flyai` | 效率工具 | 10 | Search flights, hotels, attractions, concerts, and travel deals with natural language. FlyAI connects to Fliggy MCP for real-time search and booking across hotels, flights, cruises, visas, car rentals, and event ticke... |
| 十大命理综合 | `qwenwork/skills/fortune-master-pro` | 教育学习 | 17 | 全体系增强版智能命理师技能。支持八字/四柱、紫微斗数、塔罗、西方星盘、数字命理， 并新增道家玄学分流：奇门遁甲、六爻、梅花易数、风水与择时建议。 会先判断体系、问题和资料完整度，再输出完整、层次清晰、有真人老师感的解读。 Use when: 用户想做命理分析、占卜、关系合盘、流年运势、择时、风水建议， 或说"帮我看看命""综合分析一下"等综合类命理咨询。 Distinct from: cantian-bazi（纯排盘计算工具，不做... |
| 英语学习乐园 | `qwenwork/skills/fun-englishzone` | 教育学习 | 15 | 一位互动性强、趣味十足的英语老师，通过交互式教具、视觉游乐场和游戏化挑战创造引人入胜的英语学习体验。当你需要学习词汇、练习语法、训练发音、提升阅读理解或写作能力时使用此技能。涵盖从 A1 到 C2 的完整 CEFR 英语水平体系，支持个性化学习路径和即时反馈。 |
| 趣味数学课堂 | `qwenwork/skills/fun-mathclass` | 教育学习 | 14 | 一位互动性强、趣味十足的数学老师，通过交互式教具、视觉游乐场和游戏化挑战创造引人入胜的数学学习体验。当用户需要学习数学概念、练习数学题目、可视化理解数学原理、或进行游戏化数学挑战时使用此技能。涵盖从小学算术到大学微积分的完整知识体系，支持自适应难度和即时反馈。 |
| 生成 PPTX | `qwenwork/skills/generate-pptx` | 知识文档 | 8 | 通过多轮沟通收集需求、确认逐页结构、生成每页 SVG 幻灯片并输出 PPTX 文件。适用于用户要求生成 PPT/PPTX、制作演示文稿、把文案或提纲转成幻灯片、先确认页纲再出稿，或需要把模型生成的 SVG 幻灯片打包成可下载 PPTX 的场景。 |
| github工具 | `qwenwork/skills/github` | 开发工具 | 2 | 通过 `gh` CLI 与 GitHub 交互。支持 `gh issue`、`gh pr`、`gh run`、`gh api` 等命令，用于管理 Issue、PR、CI 运行和高级查询。不要在非 GitHub 场景（如 GitLab、Bitbucket、纯 git 操作）时触发。 |
| 公文格式 | `qwenwork/skills/gongwenformat` | 内容写作 | 13 | Format, review, or rewrite Chinese official documents according to the requirements in GB/T 9704-2012 and the local file `公文标准格式.doc`. Use this skill for 公文排版, 公文格式审查, 通知/请示/报告/函/纪要/命令（令）规范化, or when converting a draf... |
| 群聊内容摘要 | `qwenwork/skills/group-chat-summary` | 沟通协作 | 1 | 基于钉钉群聊的智能摘要与洞察生成能力。从指定群聊/时间范围的消息中提取关键信息，识别决策、行动项、风险，生成钉钉在线文档结构化摘要。 |
| AI文本优化 | `qwenwork/skills/humanizer-zh` | 内容写作 | 1 | 检测并去除中文文本中的 AI 生成痕迹，使其更像人类自然书写。 覆盖内容模式（夸大意义、宣传语言、模糊归因）、语言模式（AI 高频词、三段式、同义词循环）、 风格模式（破折号滥用、粗体堆砌、表情符号）三大类 24 种 AI 写作特征的识别与改写。 Use when user mentions "去除AI痕迹", "AI味太重", "文章太像ChatGPT写的", "人性化改写", "去机器感", "让文字更自然", "humani... |
| icon生成器 | `qwenwork/skills/icon-studio` | 设计创意 | 1 | Professional icon generator. Creates high-quality icons for Apps, websites, desktop software, games, brand logos, social avatars, and more. Supports 20+ styles (Minimal, Clay 3D, Neon, Glassmorphism, etc.) with style... |
| AI表格协同应答助手 | `qwenwork/skills/im-aitable-butler` | 效率工具 | 10 | AI 表格协同应答助手 · 让 IM、Agent 与 AI 表格协同响应你的钉钉消息。@机器人或@你本人， 千问办公 Agent 自动处理并回复（联网查资料 / 读文档 / 查日志 / 执行操作）；消息进度实时可见 （处理中→处理完成状态标签），所有消息自动沉淀到 AI 表格形成问题库（提问人 / 时间 / 来源 / 内容 / 结果 / 状态）。 支持多群 + 单聊监听、机器人 / 本人双身份回复。当用户要求部署钉钉消息监听、搭建... |
| 行业研究报告 | `qwenwork/skills/industry-research` | 金融投研 | 1 | 面向特定行业/赛道的**系统性深度研究**能力。从行业定义、市场规模、竞争格局、技术趋势、政策环境、投融资动态等多维度进行**广覆盖、深挖掘**的全面调研，输出结构化的行业研究报告。 |
| 互动学习卡片 | `qwenwork/skills/interactive-learning-cards` | 教育学习 | 8 | 为教师创建课堂专用的交互式学习应用。包含闪卡、测验和浏览模式。基于记忆科学原理设计，支持学生自主学习和课堂互动练习。当老师需要制作学科知识点卡片、课堂练习题、复习工具或家校共育学习资源时使用此技能。不要在简单文档生成、纯文本整理或非教学场景时触发。 |
| 知识库审计 | `qwenwork/skills/knowledge-audit` | 知识文档 | 4 | 对钉钉知识库进行系统性诊断审计，支持轻量级审计和深度审计两种模式， 输出文档健康度评估、分类规划和知识地图索引文档。 Use when user mentions "审计知识库", "知识库体检", "盘一盘文档", "文档太乱了", "帮我理一理文档", "哪些文档过期了", "建个文档索引", "生成知识地图", or asks to "诊断文档质量", "规划目录结构", "看看哪些文档该清理了". Distinct fro... |
| 劳动合同专项起草 | `qwenwork/skills/labor-contract-generator` | 法律服务 | 4 | 生成中国大陆标准劳动合同、空白劳动合同模板、可打印劳动合同和劳动合同 DOCX；支持固定期限、无固定期限、以完成一定工作任务为期限的劳动合同，以及试用期、保密、知识产权、培训服务期、竞业限制、文书送达、离职交接等条款生成，并可按销售岗、技术岗、高管岗、医疗岗、工厂/门店岗、驻外/外派岗输出强化版本。 |
| 劳动合同专项审查 | `qwenwork/skills/labor-contract-review` | 法律服务 | 22 | 面向中文劳动合同签署、修订和模板复核场景，帮助用户快速识别关键用工风险、修改优先级和谈判边界，并形成可执行的审查意见。 |
| lark-approval | `qwenwork/skills/lark-approval` | 沟通协作 | 1 | 飞书审批 API：审批实例、审批任务管理。 |
| lark-apps | `qwenwork/skills/lark-apps` | 沟通协作 | 7 | 把本地 HTML 文件或目录部署到飞书妙搭（Miaoda），生成一个公网可访问的应用及其链接（URL）。当用户要创建 HTML 或要把 HTML、静态网站或 Web demo 发布成公网可访问的链接 / 可分享链接、设置应用共享范围，或提到妙搭 / Miaoda 时使用。凡产出可独立访问的 HTML 产物都属本 skill 的潜在归宿，是否真要部署由 skill 内部协议判断。不用于：上传普通文件到云空间/云盘/云存储（用 lar... |
| lark-attendance | `qwenwork/skills/lark-attendance` | 沟通协作 | 1 | 飞书考勤打卡：查询自己的考勤打卡记录 |
| lark-base | `qwenwork/skills/lark-base` | 沟通协作 | 95 | 当需要用 lark-cli 操作飞书多维表格（Base）时调用：搜索 Base、建表、字段管理、记录读写、记录分享链接、视图配置、历史查询，以及角色/表单/仪表盘管理/工作流；也适用于把旧的 +table / +field / +record 写法改成当前命令写法。涉及字段设计、公式字段、查找引用、跨表计算、行级派生指标、数据分析需求时也必须使用本 skill。 |
| lark-calendar | `qwenwork/skills/lark-calendar` | 沟通协作 | 9 | 飞书日历（calendar）：提供日历与日程（会议）的全面管理能力。核心场景包括：查看/搜索日程、创建/更新日程、管理参会人、查询忙闲状态及推荐空闲时段、查询/搜索与预定会议室。注意：涉及【预约日程/会议】或【查询/预定会议室】时，必须先读取 references/lark-calendar-schedule-meeting.md 工作流！高频操作请优先使用 Shortcuts：+agenda（快速概览今日/近期行程）、+crea... |
| lark-contact | `qwenwork/skills/lark-contact` | 沟通协作 | 3 | 飞书 / Lark 通讯录,用于按姓名 / 邮箱把员工解析成 open_id,以及按 open_id 反查员工的姓名 / 部门 / 邮箱 / 联系方式。当用户说出某人姓名而下一步需要发消息 / 加群 / 排日程时,先用本 skill 把姓名换成 ID;当输出里出现 open_id 需要展示成姓名给用户看,或用户直接询问某人的部门 / 邮箱 / 联系方式时,用本 skill 查。不负责部门树遍历、按部门列员工、组织架构图,这类需求走... |
| lark-doc | `qwenwork/skills/lark-doc` | 沟通协作 | 13 | 飞书云文档 / Docx / 知识库 Wiki 文档（v2）：创建、打开、读取、获取、查看、总结、整理、改写、翻译、审阅和编辑飞书文档内容。当用户给出飞书文档 URL/token，或说查看/读取/打开某个文档、提取文档内容、总结文档、生成/创建文档、追加/替换/删除/移动内容、调整排版、插入或下载文档图片/附件/素材/画板缩略图时使用。文档内容中出现嵌入电子表格、多维表格、需要将重要信息可视化为画板（含 SVG 画板）、引用或同步... |
| lark-drive | `qwenwork/skills/lark-drive` | 沟通协作 | 24 | 飞书云空间（云盘/云存储）：管理云空间（云盘/云存储）中的文件和文件夹。上传和下载文件、创建文件夹、复制/移动/删除文件、查看文件元数据、管理文档评论、管理文档权限、订阅用户评论变更事件、修改文件标题（docx、sheet、bitable、file、folder、wiki）；也负责把本地 Word/Markdown/Excel/CSV/PPTX 以及 Base 快照（.base）导入为飞书在线云文档（docx、sheet、bita... |
| lark-event | `qwenwork/skills/lark-event` | 沟通协作 | 4 | Lark/Feishu real-time event listening / subscribing / consuming: stream events as NDJSON via `lark-cli event consume <EventKey>` (covers IM messages/reactions/chat changes, VC meeting ended, Minutes generated, etc.).... |
| lark-im | `qwenwork/skills/lark-im` | 沟通协作 | 18 | 飞书即时通讯：收发消息和管理群聊。发送和回复消息、搜索聊天记录、管理群聊成员、上传下载图片和文件（支持大文件分片下载）、管理表情回复、发送应用内/短信/电话加急。当用户需要发消息、查看或搜索聊天记录、下载聊天中的文件、查看群成员、搜索群、创建群聊或话题群、管理标记数据时使用。 |
| lark-mail | `qwenwork/skills/lark-mail` | 沟通协作 | 25 | 飞书邮箱 — draft, compose, send, reply, forward, read, and search emails; manage drafts, folders, labels, contacts, attachments, and mail rules. Use when user mentions 起草邮件, 写一封邮件, 拟邮件, 草稿, 发通知邮件, 发送邮件, 发邮件, 回复邮件, 转发邮件, 查... |
| lark-markdown | `qwenwork/skills/lark-markdown` | 沟通协作 | 6 | 飞书 Markdown：查看、创建、上传、编辑和比较 Markdown 文件。当用户需要创建或编辑 Markdown 文件、读取、修改、局部 patch 或比较差异时使用。 |
| lark-minutes | `qwenwork/skills/lark-minutes` | 沟通协作 | 6 | 飞书妙记：妙记相关基本功能。1.查询妙记列表（按关键词/所有者/参与者/时间范围）；2.获取妙记基础信息（标题、封面、时长 等）；3.下载妙记音视频文件；4.获取妙记相关 AI 产物（总结、待办、章节）；5.上传音视频生成妙记，也支持将本地音视频文件转成纪要、逐字稿、文字稿、撰写文字等产物；6.更新妙记标题（重命名妙记）；7.替换妙记逐字稿中的说话人。遇到这类请求时，应优先使用本 skill。飞书妙记 URL 格式: http(s... |
| lark-okr | `qwenwork/skills/lark-okr` | 沟通协作 | 11 | 飞书 OKR：管理目标与关键结果。查看和编辑 OKR 周期、目标（Objective）、关键结果（Key Result）、对齐关系、量化指标和进展记录。当用户需要查看或创建 OKR、管理目标和关键结果、查看对齐关系时使用。 |
| lark-openapi-explorer | `qwenwork/skills/lark-openapi-explorer` | 沟通协作 | 1 | 飞书/Lark 原生 OpenAPI 探索：从官方文档库中挖掘未经 CLI 封装的原生 OpenAPI 接口。当用户的需求无法被现有 lark-* skill 或 lark-cli 已注册命令满足，需要查找并调用原生飞书 OpenAPI 时使用。 |
| lark-shared | `qwenwork/skills/lark-shared` | 沟通协作 | 1 | Use when first setting up lark-cli, running auth login, switching user/bot identity (--as), handling permission denied or scope errors, needing to update lark-cli, or seeing _notice in JSON output. |
| lark-sheets | `qwenwork/skills/lark-sheets` | 沟通协作 | 11 | 飞书电子表格：创建和操作电子表格。支持创建表格、创建/复制/删除/更新工作表、读写单元格、追加行数据、查找内容、导出文件。当用户需要创建电子表格、管理工作表、批量读写数据、在已知表格中查找内容、导出或下载表格时使用。若用户是想按名称或关键词搜索云空间（云盘/云存储）里的表格文件，请改用 lark-drive 的 drive +search 先定位资源。当用户给出 doubao.com 的 /sheets/ URL/token 时，... |
| lark-skill-maker | `qwenwork/skills/lark-skill-maker` | 沟通协作 | 1 | 创建 lark-cli 的自定义 Skill。当用户需要把飞书 API 操作封装成可复用的 Skill（包装原子 API 或编排多步流程）时使用。 |
| lark-slides | `qwenwork/skills/lark-slides` | 沟通协作 | 69 | 飞书幻灯片：创建和编辑幻灯片，接口通过 XML 协议通信。创建演示文稿、读取幻灯片内容、管理幻灯片页面（创建、删除、读取、局部替换）。当用户需要创建或编辑幻灯片、读取或修改单个页面时使用。当用户给出 doubao.com 的 /slides/ URL/token 时，也应直接使用本 skill，不要因为域名不是飞书而回退到 WebFetch；路由依据是 URL 路径模式和 token，而不是域名。 |
| lark-task | `qwenwork/skills/lark-task` | 沟通协作 | 19 | 飞书任务：管理任务、清单和任务智能体。创建待办任务、查看和更新任务状态、拆分子任务、组织任务清单、分配协作成员、上传任务附件、注册或注销任务智能体、更新任务智能体的主页数据、写入智能体任务记录。当用户需要创建待办事项、查看任务列表、跟踪任务进度、管理项目清单或给他人分配任务、为任务上传附件文件、注册注销任务智能体、更新智能体主页数据、写入任务记录时使用。 |
| lark-vc | `qwenwork/skills/lark-vc` | 沟通协作 | 5 | 飞书视频会议：搜索历史会议、查询会议纪要产物（总结、待办、章节、逐字稿）、查询会议参会人快照。1. 查询已经结束的会议数量或详情时使用本技能（如历史日期｜昨天｜上周｜今天已经开过的会议等场景），查询未开始的会议日程使用 lark-calendar 技能。2. 支持通过关键词、时间范围、组织者、参与者、会议室等筛选条件搜索会议。3. 获取或整理会议纪要、逐字稿、录制产物时使用本技能。4. 查询“谁参加过某会议”“参会人列表”等参会人... |
| lark-vc-agent | `qwenwork/skills/lark-vc-agent` | 沟通协作 | 4 | 飞书视频会议：让机器人代当前用户加入/离开正在进行的会议，并读取会议期间的实时事件（参会人加入与离开、发言、聊天、屏幕共享等）。1. 用户提供 9 位会议号、要求代为入会或离会时使用 +meeting-join / +meeting-leave——会真实产生入会/离会记录。2. 会议进行中用户想知道“谁加入了”“谁离开了”“谁在发言”“有人共享屏幕吗”等会中动态时，机器人入会后用 +meeting-events 读取事件时间线。3... |
| lark-whiteboard | `qwenwork/skills/lark-whiteboard` | 沟通协作 | 28 | 飞书画板：查询和编辑飞书云文档中的画板。支持导出画板为预览图片、导出原始节点结构、使用 DSL（转成 OpenAPI 格式）、PlantUML/Mermaid 格式更新画板内容。 当用户需要查看画板内容、导出画板图片、编辑画板，或是需要可视化表达架构、流程、组织关系、时间线、因果、对比等结构化信息时使用此 skill，无论是否提及"画板"。 ⚠️ 原 `lark-whiteboard-cli` skill 已合并至本 skill，... |
| lark-wiki | `qwenwork/skills/lark-wiki` | 沟通协作 | 13 | 飞书知识库：管理知识空间、空间成员和文档节点。创建和查询知识空间、查看和管理空间成员、管理节点层级结构、在知识库中组织文档和快捷方式。当用户需要在知识库中查找或创建文档、浏览知识空间结构、查看或管理空间成员、移动或复制节点时使用。当用户给出 doubao.com 的 /wiki/ URL/token 时，也应直接使用本 skill，不要因为域名不是飞书而回退到 WebFetch；路由依据是 URL 路径模式和 token，而不是域名。 |
| lark-workflow-meeting-summary | `qwenwork/skills/lark-workflow-meeting-summary` | 沟通协作 | 1 | 会议纪要整理工作流：汇总指定时间范围内的会议纪要并生成结构化报告。当用户需要整理会议纪要、生成会议周报、回顾一段时间内的会议内容时使用。 |
| lark-workflow-standup-report | `qwenwork/skills/lark-workflow-standup-report` | 沟通协作 | 1 | 日程待办摘要：编排 calendar +agenda 和 task +get-my-tasks，生成指定日期的日程与未完成任务摘要。适用于了解今天/明天/本周的安排。 |
| 案情法律分析报告 | `qwenwork/skills/lawd-analysis-report` | 法律服务 | 12 | 生成深度法律分析报告（民商/行政/非诉）。基于录音转写文本或案件材料，自动识别事务类型，运行时探测并调用「案例检索」「法规检索」「企业工商信息查询」三类连接器能力做自动化增强，输出排版精美的 Word (.docx) 文档。适用于律师沟通后快速产出'合伙人级别'分析建议书。TRIGGER when: (1) 用户提供录音转写文本或案件材料要求出具法律分析报告 (2) 用户要求对案件进行全面分析并生成建议书 (3) 用户提及'分析报... |
| 律师类案检索与报告 | `qwenwork/skills/lawd-case-retrieval` | 法律服务 | 24 | 律师类案检索一体化技能，一个入口三种模式：模式A 类案检索（把案情、法律问题、案由或检索词改写为专业查询，调用案例检索连接器，核验并整理真实案例，形成基于当前检索样本的裁判观点、争议焦点、法规关注清单和案例列表）、模式B 按案号取裁判文书全文（已知案号时用浏览器能力登录中国裁判文书网检索文书详情并落盘 Markdown 与 PDF）、模式C 正式类案检索报告（把已核验案例数据编排为经脚本校验的 .docx 五部分正式报告）。TRI... |
| 上诉状生成 | `qwenwork/skills/lawd-civil-appeal-petition-generator` | 法律服务 | 8 | 民事上诉状生成技能。根据用户提供的一审判决书、庭审材料、证据目录、质证意见及案件事实，生成或优化专业民事上诉状。TRIGGER when: (1) 用户提及\\"上诉状\\"、\\"民事上诉\\"、\\"二审上诉\\"、\\"不服一审判决\\"、\\"改判\\"、\\"发回重审\\"等关键词，(2) 用户要求起草/修改/润色上诉状，(3) 用户提供一审裁判文书并希望提炼上诉请求和上诉理由，(4) 用户需要将事实认定、证据采信、法律适用或程序问题转化为二审... |
| 起诉状生成 | `qwenwork/skills/lawd-civil-complaint` | 法律服务 | 90 | 民事起诉状起草技能。以资深民商事诉讼律师视角，按案由分流起草符合《民事诉讼法》第122条要素要求的民事起诉状，输出格式严谨的Word文档。TRIGGER when (1) 用户提及起诉状/民事起诉状/起诉书/诉状/起草起诉状/立案材料/准备起诉等关键词，(2) 用户描述纠纷事实并表达诉讼意愿，(3) 用户需要将仲裁/调解失败的案件转入诉讼程序。支持合同/侵权/婚姻家庭/劳动/公司及其他六大类民商事案由。合同纠纷必须全面阅读合同条款... |
| 综合证据策略 | `qwenwork/skills/lawd-civil-evidence-enhanced` | 法律服务 | 15 | 资深民商事诉讼律师证据专家，一个入口三种模式：综合证据分析（整体审查己方及对方证据，三性与证明力分析、举证责任分配、证据链缺口、补强方案、举证顺序、庭审证据应对）、逐份质证意见、证据链构建与举证要点映射（证据对应法律主张、缺口识别、证据目录编制）。TRIGGER when: 用户提及“证据分析”“证据审查”“证据梳理”“举证策略”“三性分析”“真实性合法性关联性”“证明力”“庭前证据准备”“举证责任”→模式A；“质证”“质证意见”... |
| 强制执行申请书 | `qwenwork/skills/lawd-civlit-enforcement-application` | 法律服务 | 13 | 强制执行申请书生成专家。根据生效法律文书+财产线索+必要附件，自动计算执行标的（含迟延履行利息），智能分类财产线索，生成强制执行申请书+财产保全申请书+计算明细表全套文书。支持六类执行依据：判决书、裁定书、调解书、仲裁裁决书、公证债权文书、支付令。TRIGGER when: (1) 用户提及\\"强制执行\\"\\"执行申请\\"\\"申请执行\\"\\"执行立案\\"\\"申请法院执行\\"\\"强执\\"等，(2) 用户持有生效法律文书需要申请强制执... |
| 律师模拟裁判报告 | `qwenwork/skills/lawd-civlit-judge-simulation` | 法律服务 | 7 | 模拟裁判报告——资深法官视角庭前预判助手。基于20年资深民商事审判法官与资深诉讼律师的双重视角，模拟法庭裁判思路，预判裁判结果，帮助律师在庭前精准把握案件走向。TRIGGER when: (1) 用户提及模拟裁判、裁判预判、法官视角、裁判分析、胜诉概率、胜算分析、预判结果、能不能赢、胜诉几率、法官怎么判、案件走向、赢面多大、有没有把握、胜诉可能性、判决预测等关键词，(2) 用户需要从法官角度评估案件走向，(3) 用户需要预判裁判结... |
| 代理词生成 | `qwenwork/skills/lawd-civlit-pleading-brief` | 法律服务 | 12 | 民商事诉讼与仲裁代理词起草专家。综合事实、证据、法律意见与争点攻防，按庭审逻辑系统呈现己方主张。支持一审原告/被告、二审（上诉人/被上诉人）、仲裁（申请人/被申请人）。TRIGGER when: (1) 用户提及\\"代理词\\"\\"代理意见\\"\\"庭审发言\\"\\"法庭辩论\\"\\"辩论意见\\"\\"开庭陈述\\"\\"出庭意见\\"\\"仲裁代理意见\\"\\"二审代理词\\"\\"上诉代理词\\"等，(2) 用户需要基于案卷材料起草可提交的代理词，(3... |
| 律师庭前准备 | `qwenwork/skills/lawd-civlit-preparation` | 法律服务 | 15 | 律师庭前准备技能，融合资深民商事诉讼律师与资深员额法官双重视角，含两个模式：模式A 完整庭前准备报告（编排证据分析、争议焦点分析、庭审发问策略、模拟裁判四项工作，集中检索一次后统一整合去重，输出一份《庭前准备报告》）；模式B 庭审发问策略（双视角发问设计、法官发问预判、应答准备、禁止发问清单，输出独立《庭审发问策略报告》）。当用户提及“庭审准备”“庭前准备”“开庭准备”“准备开庭”“马上开庭”“全面准备”“庭前分析”“庭审材料准备... |
| 起诉状分析与攻防策略 | `qwenwork/skills/lawd-complaint-analyzer` | 法律服务 | 36 | 起诉状分析与攻防策略技能，含两个模式：模式A 从被告及应诉方视角逐项拆解原告诉讼请求、评估各项诉请风险、识别原告证据薄弱点与抗辩空间并生成防御行动清单；模式B 从起诉状、答辩状、证据材料和当事人主张中识别核心争议、拆解法律要件、归纳双方分歧并进行攻防推演，交付完整版或简易版争议焦点分析报告。当用户收到起诉状并要求分析、评估风险、判断怎么应诉、研究原告胜算或制定初步防御方案（即使只说“帮我看看这份起诉状”）时走模式A；当用户要求梳理... |
| 质证意见生成 | `qwenwork/skills/lawd-cross-examination-opinion-generator` | 法律服务 | 10 | 对方证据质证意见专项生成技能，用于针对对方提交的证据逐份形成可用于庭审的质证意见。当用户要求写质证意见、生成质证意见书、逐项质证、反驳对方证据，或从真实性、合法性、关联性和证明力角度逐份审查对方证据时应触发。核心交付物为逐项质证意见书，并可附证据初步判断和反证建议。不用于仅生成证据目录，也不用于没有明确质证需求的案件整体证据梳理。 |
| 答辩状一键起草 | `qwenwork/skills/lawd-defense-statement-draft` | 法律服务 | 20 | 当律师需要为被告起草民事答辩状时使用。支持买卖合同、民间借贷、劳动争议、离婚、交通事故、物业服务、金融借款、信用卡、融资租赁、保证保险、证券虚假陈述、教育培训合同共12种案由。默认输出传统叙事式答辩状 + 答辩辅助提示；律师要求时可附加输出法院要素式答辩状。输入可以是自然语言描述或上传起诉状；也可接收上游 Skill（如起诉状分析与攻防策略（lawd-complaint-analyzer 模式B）、综合证据策略（lawd-civi... |
| 超安全文件脱敏 | `qwenwork/skills/lawd-doc-redaction` | 法律服务 | 11 | 超安全文件脱敏技能。打开本地网页工具，在浏览器里把合同/判决书/证据/表格等文件的敏感信息（公司名、人名、身份证号、手机号、银行账号、统一社会信用代码、地址等）识别并替换为「某公司A」「某人甲」「【证件已脱敏】」等代号，支持粘贴文本、Word(docx)、Excel(xlsx)、PDF、图片五种输入，逐条确认、逐条撤销、框选补漏、涂抹，导出脱敏版（文本/Word/Excel/栅格化PDF）。全程不经大模型、文件不离开本机、断网可用... |
| 遗嘱起草与实操指引 | `qwenwork/skills/lawd-estate-planning` | 法律服务 | 40 | 面向千问办公的遗嘱起草公益技能：帮助用户系统整理遗嘱相关信息，生成待律师人工复核的 AI 遗嘱草案、简明执行指引、资产与债务清单、关系人与拟继承财产示意图（SVG 图片）等成果，其中检索报告与普法内容由用户选择，全部成果显著标注不可直接签署。区分三种调用场景：①人物与财产关系清晰简单的普通用户（简易模式，填写较少）；②财产种类多、家庭关系较复杂的当事人（完整模式，按人员、财产、分配、订立形式、遗嘱执行五大类系统填写）；③律师/法律... |
| 证据清单生成 | `qwenwork/skills/lawd-evidence-list-generator` | 法律服务 | 9 | 证据清单生成技能，用于将用户提供的案件材料整理为可提交、可编辑的标准证据清单。当用户要求生成证据清单、证据目录、证据列表，或整理证据名称、页码、原件状态和证明对象时应触发，即使用户只说“帮我把这些证据整理成表”。核心交付物为证据清单 Word 文档。不用于判断证据真实性、合法性、关联性和证明力，不负责举证策略、证据补强或质证意见。 |
| 证据时间线生成 | `qwenwork/skills/lawd-evidence-timeline-generator` | 法律服务 | 12 | 证据时间线生成技能。根据用户提供的证据材料，自动提取时间信息并按时间顺序整理，生成证据时间线 Markdown 文档和 HTML 思维导图文件。TRIGGER when: (1) 用户提及\\"时间线\\"、\\"时间轴\\"、\\"事件排序\\"、\\"证据时间线\\"、\\"案件时间线\\"等关键词，(2) 用户提供证据材料并要求按时间整理，(3) 用户需要可视化展示案件事件发展过程，(4) 用户准备诉讼材料需要梳理时间脉络。输出：证据时间线 M... |
| 咨询信息采集清单 | `qwenwork/skills/lawd-intake-checklist` | 法律服务 | 4 | 咨询信息采集清单生成器。根据法律问题类型（民事纠纷、劳动争议、婚姻家事等 8 大类型）自动生成定制化信息采集清单，含必问问题（按重要性排序、附追问提示）和必备材料（标注用途与来源指引）。TRIGGER when: 用户说首次咨询准备、咨询前信息采集、咨询中信息补全、委托前材料收集、生成咨询问题清单、案件信息缺口梳理时立即使用；输入为问题类型，可选案情描述。NOT for: 已完整采集后的信息整理、证据分析或事实认定、非中国法律场景... |
| 法律服务方案生成器 | `qwenwork/skills/lawd-lawyer-quotation-generator` | 法律服务 | 8 | 法律服务方案生成器。根据用户提供的案件类型、标的金额、服务阶段、收费模式等信息，生成专业的法律服务报价方案文档；支持多种报价模板（仅报价、报价+服务内容、服务内容+团队+价格、标准+费用、团队+费用）；输出符合律所商务规范的报价方案。TRIGGER when: (1) 用户提及「报价」「收费」「法律服务方案」「委托报价」「服务方案」「报价单」等关键词；(2) 用户需要为客户出具法律服务报价或收费方案；(3) 接案洽谈时需快速生成含... |
| 法律文书模板扫描 | `qwenwork/skills/lawd-legal-doc-template-scanner` | 法律服务 | 5 | 当用户上传自己的文书模板（Word/PDF/图片），需要从中提取文件类型要求、文本格式要求（字体字号行距等）和内容大纲结构时触发。提取结果形成「模板规格说明书」，供用户确认后作为后续文书生成的格式与结构规范。适用于律师/法务上传起诉状模板、合同模板、法律意见书模板、代理词模板等场景。NOT for：根据案情直接生成法律文书（用对应文书生成技能）、扫描目录批量枚举模板文件（本技能只解析用户提供的单份模板文件）、成品文书的纯格式转换（... |
| 诉讼风险与清偿评估 | `qwenwork/skills/lawd-litigation-risk` | 法律服务 | 17 | 诉讼风险与清偿评估（双模式：诉讼风险评估 / 债务清偿能力评估）。Use when 律师立案前评估对手方诉讼风险全景、企业司法状态、胜诉概率研判、执行风险评级、应诉策略制定，或诉前评估被告偿债能力、识别可执行资产、制定财产保全策略、测算追偿清偿率。TRIGGER when 用户提及诉讼风险/应诉策略/胜诉概率/执行风险/立案评估/对手方分析/司法状态/涉诉分析/诉前评估（→ 模式A 诉讼风险评估）；用户提及偿债能力/债务清偿/财产... |
| 律师法规检索 | `qwenwork/skills/lawd-regulation-retrieval` | 法律服务 | 7 | 中国法规检索技能。检索中国法律法规，支持智能Query改写、法规总结洞察。TRIGGER when: (1) 用户提及\\"查法规\\"、\\"查法律\\"、\\"法条检索\\"、\\"法律规定\\"、\\"法律依据\\"、\\"相关法条\\"等关键词，(2) 用户咨询涉及法律问题需要引用具体法条，(3) 用户询问法律责任、权利义务等问题，(4) 用户需要确认某项行为的法律后果，(5) 用户需要查找特定法律法规的具体条文。NOT for: 类案检索（应使... |
| 律师企业尽调报告 | `qwenwork/skills/lawding-company-info` | 法律服务 | 7 | 企业主体信息全能查询。Use when 用户提及企业信息查询、工商信息、查企业、尽调、背景调查,或询问某企业是否靠谱、合作风险、当事人企业背景,或要求出一份企业尽调报告。QoderWork 默认用原生企查查连接器（Qichacha，一键 OAuth）；天眼查需自定义 MCP 可选接入。TRIGGER keywords: 企业查询、工商、股东、风险、尽调、查公司、天眼查、企查查、企业背景。 |
| 律师合同预审 | `qwenwork/skills/lawding-contract-review-pro` | 法律服务 | 55 | 专业合同审核（三观四步法）。TRIGGER when: (1) 用户上传合同文件并要求审核/审查/把关 (2) 用户提及合同风险、条款合法性、修改建议、能否签署、谈判要点 (3) 典型问法：帮我看看合同、审一下合同、合同有没有问题、分析合同风险、修改合同条款、起草合同并同步审核。交付：对话框解读报告 + 审核意见书.docx + 原文批注版.docx。NOT for: 仅提取合同字段/要素（key-terms-extract）、仅... |
| 律师函撰写 | `qwenwork/skills/lawding-lawyer-letter` | 法律服务 | 8 | 资深民事律师函撰写技能。根据用户需求生成专业律师函，输出Word文档。TRIGGER when: (1) 用户提及\\"律师函\\"、\\"催告函\\"、\\"警告函\\"、\\"询问函\\"、\\"告知函\\"、\\"声明函\\"、\\"权利声明\\"等关键词，(2) 用户需要催促对方履行义务或协商，(3) 用户需要制止侵权/警告违约行为，(4) 用户需要中断诉讼时效、通知合同解除或声明权利归属，(5) 用户描述纠纷需要发函施压，(6) 用户说\\"帮我起草... |
| 法律服务方案生成器 | `qwenwork/skills/lawding-lawyer-quotation-generator` | 法律服务 | 6 | 法律服务方案生成器。根据用户提供的案件类型、标的金额、服务阶段、收费模式等信息，生成专业的法律服务报价方案文档；支持多种报价模板（仅报价、报价+服务内容、服务内容+团队+价格、标准+费用、团队+费用）；输出符合律所商务规范的报价方案。 |
| 中国法律合规 AI 技能包 | `qwenwork/skills/legal-compliance-bundle` | 法律服务 | 54 | > 50个AI驱动的法律合规自动化技能，覆盖合同、劳动、知产、数据、企业合规五大领域。 |
| 教案生成助手 | `qwenwork/skills/lesson-plan-assistant` | 教育学习 | 12 | 生成符合《义务教育课程标准（2022年版）》的专业教案，基于教学评一致性原则设计。当用户需要编写中小学各学科教案、教学设计、教学计划时使用。不要在非教学场景（如作文批改、试卷生成、学生管理）时触发。 |
| 文献深度研读 | `qwenwork/skills/literature-distiller` | 教育学习 | 8 | 论文文献速览与蒸馏助手。支持用户上传的 PDF 文件或在线链接，通过 4+2 深度蒸馏模型快速提取元数据、逻辑骨架、核心发现及批判性洞察，生成钉钉在线文档和原文PDF，并导入到知识库。适用于个人文献管理、快速浏览、知识收集等场景。 |
| 社媒创意专家 | `qwenwork/skills/marketing-ad` | 市场营销 | 7 | 当用户需要生成、迭代或批量产出国内平台营销文案时使用。支持的平台包括：小红书（穿搭笔记、种草文案）、微信公众号（软文、推文）、朋友圈（九宫格文案）、微博（热搜文案、话题文案）、抖音（短视频文案、评论区引导）、B站（动态文案）等。当用户提到'营销文案'、'小红书笔记'、'公众号软文'、'朋友圈文案'、'微博文案'、'种草文案'、'带货文案'、'推广文案'、'爆款标题'、'帮我写一篇推文'、'朋友圈九宫格'、'抖音文案'等关键词时触发... |
| 活动营销方案 | `qwenwork/skills/marketing-campaign-plan` | 市场营销 | 1 | 活动营销方案：明确目标人群、核心卖点、传播节奏、渠道矩阵、预算与风险，形成可执行方案。 |
| 营销策划 | `qwenwork/skills/marketing-ideas` | 市场营销 | 3 | When the user needs marketing ideas, inspiration, or strategies for their SaaS or software product. Also use when the user asks for 'marketing ideas,' 'growth ideas,' 'how to market,' 'marketing strategies,' 'marketin... |
| 视频号运营专家 | `qwenwork/skills/marketing-operations-wechat-channels` | 市场营销 | 25 | 微信视频号自动化技能集合。支持认证登录、视频发布。 **何时触发**（必须使用本技能）： - 用户提及"视频号/微信视频号/wechat channels"相关操作 - 用户要求发布视频到视频号、登录视频号 - 用户提供的链接包含 channels.weixin.qq.com 域名 - 用户询问"发视频号"、"上传视频号"等视频号运营场景 **禁止使用 browseruse**：微信视频号有反爬机制，browseruse 无法持久... |
| 营销心理分析 | `qwenwork/skills/marketing-psychology` | 市场营销 | 1 | When the user wants to apply psychological principles, mental models, or behavioral science to marketing. Also use when the user mentions 'psychology,' 'mental models,' 'cognitive bias,' 'persuasion,' 'behavioral scie... |
| media-generation | `qwenwork/skills/media-generation` | 设计创意 | 1 | Generate or edit images with automatic model selection or a supported model explicitly requested by the user, generate videos, or create music as asynchronous media artifacts. Use this skill when the user asks for tex... |
| media-generation-premium | `qwenwork/skills/media-generation-premium` | 设计创意 | 1 | Generate or edit images and generate videos or music for the enterprise premium media experience. Image, video, and music requests use official automatic model selection or organization-configured models exposed by th... |
| 新闻总结 | `qwenwork/skills/news-summary` | 市场营销 | 3 | 根据用户指定的主题和时间范围，多源检索新闻动态，经时间核验、去重、分类后生成结构化钉钉云文档动态报告。 Use when user mentions "新闻总结", "动态报告", "行业资讯", "最新消息", or asks to "帮我整理最近的AI新闻", "总结这周的行业动态", "追踪某某领域的最新消息". Distinct from competitive-analysis (竞品横向对比而非新闻动态汇总) and... |
| 通知函件写作 | `qwenwork/skills/official-document-writing` | 法律服务 | 12 | 官方公文写作技能。用于起草、改写、润色、校核、结构化或导出中文党政机关公文、事务文书、会议材料、汇报材料、通知通报、请示报告、函、纪要、方案、制度等正式文稿；尤其适用于需要按用户给定模板、单位口径、GB/T 9704-2012 基础格式或指定文种规范完成写作的场景。 |
| 宜搭应用 | `qwenwork/skills/openyida-app` | 项目管理 | 67 | 用自然语言创建或修改宜搭业务应用和管理系统，支持表单、审批流程、自定义页面、看板、报表、连接器、权限、自动化和数据功能。用户要求搭建客户管理、项目管理、活动报名、工单、审批、台账、运营工作台等系统，或完善已有宜搭应用时使用；查询、分析已有宜搭应用、表单、字段、记录、流程任务、指标、通讯录、业务关系、血缘，或通过预览确认链路办理已发布业务 Action 时也使用。 |
| 落地页生成器 | `qwenwork/skills/page-crafter` | 市场营销 | 1 | Professional high-end Landing Page generation tool. Creates visually stunning, Awwwards-level web pages with cinematic hero sections, modern animations. Trigger keywords: landing page, 落地页, web page, hero section, pro... |
| 学术论文深度研究 | `qwenwork/skills/paper-deepresearch` | 教育学习 | 1 | 面向学术论文的**原文级调研（Deep Research）**能力模块。适用于：用户指定某篇论文要求"读透 + 追踪背景 + 扩展最新相关工作"，或用户给出某个学术 topic 要求系统性深度调研与写作综述。 |
| pdf | `qwenwork/skills/pdf` | 知识文档 | 53 | Operates on PDF files: inspect/fill forms, merge/split, watermark, encrypt/decrypt, strip metadata, extract tables or images, compress, validate, render pages to images (so the agent can read scanned PDFs with vision)... |
| plugin-creator | `qwenwork/skills/plugin-creator` | 系统内置 | 1 | Create, customize, or modify QwenWork / QwenWorkCN expert plugins. Use when the user wants to create a new plugin, customize an existing plugin, or edit a plugin's skills/commands. |
| pptx | `qwenwork/skills/pptx` | 知识文档 | 103 | Use this skill any time a PowerPoint .pptx or legacy .ppt file is involved as input, output, or both. This includes creating decks; reading or extracting slide content; editing presentations; combining or splitting sl... |
| 产品定价策略 | `qwenwork/skills/pricing-strategy` | 市场营销 | 3 | When the user wants help with pricing decisions, packaging, or monetization strategy. Also use when the user mentions 'pricing,' 'pricing tiers,' 'freemium,' 'free trial,' 'packaging,' 'price increase,' 'value metric,... |
| 产品营销定位 | `qwenwork/skills/product-marketing-context` | 市场营销 | 1 | When the user wants to create or update their product marketing context document. Also use when the user mentions 'product context,' 'marketing context,' 'set up context,' 'positioning,' 'who is my target audience,' '... |
| 夸克网盘官方Skill | `qwenwork/skills/quarkclouddrive` | 效率工具 | 14 | 夸克网盘官方(Quark Drive)Skill，用于文件上传/下载（支持断点续传）、文件分享与转存、网盘文件搜索、相册整理、AI助手（文件总结与知识问答，支持万级文件）。当用户需要操作夸克网盘文件或进行身份验证时使用。 |
| 数据分析 | `qwenwork/skills/quickbi-smartq-chat` | 数据分析 | 41 | Quick BI-智能分析 技能，具备多种数据分析能力: 1. **数据集问数**：自然语言查询 Quick BI 平台数据集，自动智能选表匹配 2. **文件问数**：上传 Excel/CSV 文件，通过 Quick BI API 进行智能分析 3. **文档解析**：解析 PDF/Word/Excel/CSV/图片等文档，提取文本，并支持提取关键字段并生成结构化 Excel 4. **仪表板技能生成**：将 QuickBI 仪... |
| qw-pages | `qwenwork/skills/qw-pages` | 开发工具 | 1 | Publish static or dynamic HTML, websites, and web applications through QW Pages. Use when the user asks to publish, deploy, or make a webpage live. Combine with qw-pages-supabase only when the webpage needs persistent... |
| qw-pages-supabase | `qwenwork/skills/qw-pages-supabase` | 开发工具 | 1 | Prepare Supabase-compatible persistent storage for a dynamic QW Page. Use with qw-pages when a webpage needs database tables, server-side persistence, Supabase access, or database-backed APIs. |
| 千问办公客户端图标替换 | `qwenwork/skills/qwenwork-app-icon` | 设计创意 | 11 | Cross-platform (macOS + Windows) app icon replacement centered on the official QwenWork mascot "千仔" (Qianzai) — a flat-vector waving green octopus with two big round eyes. Auto-detects platform and routes accordingly.... |
| qwenwork-guidance | `qwenwork/skills/qwenwork-guidance` | 系统内置 | 7 | Routing guide for the built-in QwenWork Connector tools (mcp__qw-builtin__qw_query / mcp__qw-builtin__qw_action). Load ONLY right before calling them to view or manage QwenWork's OWN tasks/sessions or app configuratio... |
| 代码评审专家 | `qwenwork/skills/receiving-code-review` | 开发工具 | 1 | Use when receiving code review feedback, before implementing suggestions, especially if feedback seems unclear or technically questionable - requires technical rigor and verification, not performative agreement or bli... |
| 科研情报侦查 | `qwenwork/skills/research-collector` | 教育学习 | 7 | 立项初期的情报侦察与趋势分析引擎。通过引导式对话精准锁定调研边界，并行检索学术平台与行业资讯。最终不仅输出包含明细表格与宏观趋势的结构化报告，更自动构建专属钉钉知识库，实现从“信息搜集”到“知识沉淀”的一体化交付。适用于方向探索、行业追踪及可行性预研，为后续深度文献蒸馏提供高质量数据基座。 |
| 简历助手 | `qwenwork/skills/resume-helper` | 人力招聘 | 12 | 创作、美化、优化简历及生成面试准备方案。当用户说写简历、做简历、美化简历、优化简历、改简历、简历排版、导出简历、面试准备、生成面试题、模拟面试时触发。 |
| 职场sbti人格分析 | `qwenwork/skills/sbti-dingtalk-analyzer` | 设计创意 | 32 | 基于钉钉聊天记录做言行风格总结、工作氛围侧写与性格画像，并模拟完成 SBTI 32 题自动计算人格结果、展示结果海报。适用于用户希望"免手动答题"、直接从钉钉聊天记录生成 SBTI 人格小报告的场景。 |
| 学校社媒舆情监控 | `qwenwork/skills/school-sentiment-monitor` | 金融投研 | 12 | 监控指定学校在社交媒体上的舆论动态，进行情感分析、趋势研判和负面预警。当用户提到舆情监控、学校口碑、帮我盯着某学校、查看舆情报告时触发。不要在需要创建教案、批改作业、管理课程表时触发。 |
| 社媒内容生成 | `qwenwork/skills/social-content` | 项目管理 | 5 | 社交媒体内容创作：根据用户指定的平台生成适配内容，支持单条文案、多平台改写、 内容日历排期、互动优化，确认后写入钉钉云文档。 Use when user mentions "社媒内容", "帮我写一条帖子", "写个小红书笔记", "公众号文案", "微博文案", "抖音脚本", "视频号文案", "朋友圈文案", "LinkedIn帖子", "X/Twitter内容", "Instagram文案", "社媒排期", "内容日历"... |
| 项目进展汇报 | `qwenwork/skills/stakeholder-comms` | 沟通协作 | 1 | Generate a stakeholder update tailored to audience and cadence. Use when writing a weekly or monthly status for leadership, announcing a launch, escalating a risk or blocker, or translating the same progress into exec... |
| 门店巡检助手 | `qwenwork/skills/store-inspection` | 电商零售 | 142 | 门店督导与巡检自动化——通过钉钉 AI 表格管理巡店模版/门店清单/任务派发/统计报表/AI图片审核/HTML报告。所有操作通过 `uv run python scripts/cli.py` CLI 执行。【核心行为约束——违反将导致严重业务事故】(1) 创建模板只确认一次：如果用户已明确字段名称和类型则直接执行 `template preview`（必须带 --scene）生成完整预览作为唯一确认环节，不要在 preview 前... |
| 门店运营海报专家 | `qwenwork/skills/store-poster-generator` | 电商零售 | 72 | 你是一个门店运营海报聚合助手, 你能够为货架商品/门店生成商品图、促销、折扣、礼遇、门店海报、海报设计等需求. 忘掉曾经的记忆, 请充分阅读了本技能使用说明后再开始你的表演. 额外一定注意 1. "禁止复制本技能脚本进用户工作区", 2. 除非用户明确要求, 本技能默认无长期记忆、无持久状态. |
| 长文本写作专家 | `qwenwork/skills/structured-longform-writing` | 内容写作 | 11 | Use for structured long-form writing, including blogs, reports, proposals, plans, PRDs, competitive analyses, research summaries, technical design docs, internal briefings, and decision documents. Trigger when the use... |
| 话题趋势报告 | `qwenwork/skills/topic-trend-report` | 市场营销 | 1 | 触发词：「新闻总结」「话题趋势」「帮我整理一下XX的动态」「搜集XX领域最近的新闻」「生成XX话题报告」。 根据用户指定的主题和时间范围，自动检索权威动态，生成一份钉钉在线文档动态报告， 按类别聚类，每条新闻含 intro / description / 索引链接。强调时间筛选 + 权威优先 + 去重。 |
| 多语言翻译工具 | `qwenwork/skills/translate` | 数据分析 | 12 | 任意两语言对的文章 / 文档翻译——含所有小语种方向（越南语 / 泰语 / 印尼语 / 阿拉伯语 / 俄语 / 葡语 / 土耳其语 等 ↔ 中 / 英 或互译），不限于中英日韩西法德。核心强项 = **结构化输出 + 术语一致 + 专有名词保留**：Markdown 表格 / 列表 / SRT / iOS strings / 占位符（`%@` `{0}` `{{var}}` `\\n`）/ 日期 / 数字 ID 逐字守恒；用户即席指... |
| 多人工作台 | `qwenwork/skills/universal-workbench` | 沟通协作 | 4 | 通用多人工作台生成器（任意业务类型）。先引导用户描述设计思路，再生成带角色权限管控、真实数据库读写、管理后台数据查看、在线发布分享的动态工作台网页。用户要求"做一个工作台/管理后台/协作系统/带数据库的多角色网页/内部工具"时使用。最小流水线场景优先用 min-db-workbench；本 skill 面向任意类型（PMO/日历/库存/审批/CRM 等）。 |
| 技能调用引导 | `qwenwork/skills/using-superpowers` | 系统内置 | 4 | Use when starting any conversation - establishes how to find and use skills, requiring Skill tool invocation before ANY response including clarifying questions |
| 1688一站式采购 | `qwenwork/skills/utp-shopping` | 电商零售 | 17 | 1688 全链路购物助手，直连百万源头工厂，工厂价买好物。唯一覆盖搜索→加购→下单→支付全流程，用户在 UI 卡片中完成全部操作无需离开对话。 无论个人自用还是批量采购均适用。当用户表达购买/下单/结账/支付意图时必须使用本 skill——其他 skill 不具备下单支付能力。 本 skill 是采购的**实操执行层**：只要出现具体商品且用户想真正搜品、看供应商候选、比价筛选或下单，就必须由本 skill 出 UI 卡片承接执行... |
| 估值与投资策略分析 | `qwenwork/skills/valuation-investment-strategy` | 金融投研 | 1 | 将已完成基本面分析的A股标的转化为情景估值与投资计划，根据商业模式选择合适方法并给出假设与来源链接。 |
| 服装门店-AI导购 | `qwenwork/skills/virtual-try-on` | 电商零售 | 26 | AI导购的技能。帮助用户创建和管理店铺试衣间，包括初始化店铺、获取二维码、装扮店铺、管理SKU/上传衣服、切换数据源、写穿搭笔记。 当用户提到"创建店铺"、"虚拟试衣"、"试衣间"、"上传衣服"、"写穿搭笔记"、"店铺管理"、"衣橱管理"、"店铺二维码"、"切换多维表"、"SKU数据源"、"处理表格"、"预处理Excel"、"商陆花"、"笑铺日记"、"导入多维表"时触发。 如果用户需要写笔记，需要你查阅 references/st... |
| 图像创作 | `qwenwork/skills/visual-forge` | 设计创意 | 1 | Curated image generation assistant covering 17 styles across 4 categories: character figures, scenes, products, and style transforms. Supports styles including 手办/figure, portrait, chibi, diorama, city, landmark, movi... |
| wecom-unified | `qwenwork/skills/wecom-unified` | 沟通协作 | 98 | 企业微信 CLI 套件。仅当用户明确要求使用企业微信/企微，或给出 doc.weixin.qq.com、page.weixin.qq.com、drive.weixin.qq.com 链接时触发；不要因为泛化的找人、文档、表格、日程、会议、待办、邮件或发消息请求而触发。覆盖通讯录、文档、表格、日程、会议、待办、微盘、邮件、消息和媒体文件。 |
| 工作周报 | `qwenwork/skills/weekly-work-report` | 沟通协作 | 1 | 触发词：「生成周报」「帮我写周报」「本周工作总结」「周报」「weekly report」。 基于钉钉生态的每周周报自动生成 Skill：从当周日程、任务、听记、云文档中提取工作内容， 使用 `knowledge` 兜底补全遗漏信息，最终直接生成结构化的钉钉在线文档周报。 |
| 技术方案 | `qwenwork/skills/wukong-doc-technical-solution` | 设计创意 | 1 | 触发词：「技术方案」「系统设计」「架构方案」「技术选型」。 围绕业务目标与约束，输出架构设计、关键模块、技术选型、风险与实施计划的完整技术方案， 最终生成结构清晰的钉钉在线文档。 |
| xlsx | `qwenwork/skills/xlsx` | 知识文档 | 53 | Use this skill any time a spreadsheet file is the primary input or output. This means any task where the user wants to: open, read, edit, or fix an existing .xlsx, .xlsm, .csv, or .tsv file (e.g., adding columns, comp... |
| 云栖大会参会助手 | `qwenwork/skills/yunqi-agent` | 效率工具 | 4 |  |

### Connectors / Installed Registry

| Name | Directory | Category | Files | Description |
| --- | --- | --- | ---: | --- |
| 铱云AI供应链 | `qwenwork/connectors/mcp.json/mcp.json#77ircloud` | 电商零售 | 1 | 通过自然语言管理铱云供应链：支持订单全链路操作，以及客户、商品、仓库库存、员工组织、资金账户、数据导出、经营统计和预警明细的查询分析。 |
| 辰知教务 | `qwenwork/connectors/mcp.json/mcp.json#91chenzhi` | 教育学习 | 1 | 千问听懂安排，课表随需而动，一句话查空闲、找老师、调课表，让课表“动”起来。 |
| 数可捞 | `qwenwork/connectors/mcp.json/mcp.json#DataClawHub` | 电商零售 | 1 | 连接DataClawHub AI原生开源开放社区，支持搜索任务、制品、数据集、竞赛与工具，查询物流数据；在用户明确授权和确认后，可搜索公开任务、任务详情、读取制品、搜索AgentHub帖子、读取帖子评论和部分回复 |
| 美图设计室 | `qwenwork/connectors/mcp.json/mcp.json#Designkit` | 市场营销 | 1 | 美图设计室是美图旗下产品美图设计室 AI 设计能力在 办公场景中的应用。通过对话即可调用专业设计 Skill，无需学习复杂软件或编写 Prompt，轻松完成从市场策略洞察到电商套图、营销视频、社媒图文、海报、品牌等商业设计任务。 |
| FTShare 金融数据 | `qwenwork/connectors/mcp.json/mcp.json#FTShare` | 金融投研 | 1 | FTShare 金融数据与特色因子查询 MCP。根据用户关于股票、ETF、指数、基金、可转债、期货、港股、美股、资金流、财务、宏观经济或特色因子的需求，匹配并调用对应数据工具 |
| Hologrow | `qwenwork/connectors/mcp.json/mcp.json#Hologrow` | 电商零售 | 1 | Hologrow 将您分散在跨境电商平台、广告渠道和ERP中的数据连接起来，让您可以直接通过自然语言洞察经营表现、对比渠道成效、追踪变化原因并生成分析报告。 支持 Amazon Seller Central、Amazon Ads、Google Ads、GA4、Meta Ads 和GSC等多种平台。Hologrow 仅提供只读数据访问，不会修改您的广告活动、商品信息、订单或店铺设置等。 |
| 好多店 | `qwenwork/connectors/mcp.json/mcp.json#X-Store` | 金融投研 | 1 | 好多店连接器面向连锁品牌总部，提供门店运营管理场景下的查询与辅助分析能力，帮助品牌推进门店标准化落地。 连接后可以查询企业下所有门店数据，包括巡店记录、店务执行情况、检查失分项、整改工单及风险信息。可辅助生成区域月度复盘、单店问题诊断和整改专项分析，梳理重点门店、共性问题与待跟进事项。 |
| AI-HIVE | `qwenwork/connectors/mcp.json/mcp.json#ai-hive` | 设计创意 | 1 | 连接全球 100+ 顶尖 AI 模型（Seedance 2.5、Wan 3.0、H3、GPT-image2、Nano-Banana、Deepseek、Kimi 等），一键搞定文本、图片、视频创作，并查询余额与生成任务 |
| 钉钉假勤 | `qwenwork/connectors/mcp.json/mcp.json#attendance-leave-pro` | 开发工具 | 1 | 钉钉假勤 MCP 帮助企业高效完成考勤假勤的日常管理。支持批量初始化考勤组与班次，快速搭建考勤基础配置；排班规则的建立与批量调班、换班、复制排班；班次的新增、调整与临时安排；假期规则的设置，以及员工假期额度的发放与调整；并可按部门、人员快速查询考勤归属与请假信息。 |
| 百晓智能 | `qwenwork/connectors/mcp.json/mcp.json#baixiao-mcp` | 教育学习 | 1 | 中英文学术检索：搜索期刊论文、专著、政策文件；查阅最新基金招投标信息；核实参考文献真伪、追溯引用；推荐投稿期刊、相关文献、审稿人 |
| 草料二维码 | `qwenwork/connectors/mcp.json/mcp.json#caoliao` | 数据分析 | 1 | 读取并分析你组织在草料二维码里的数据：按指标出数、看分布趋势、下钻到具体记录，也能看码被扫了多少次、多少人扫，以及浏览码、表单与分区。只读不改数据，需组织管理员授权。 |
| 高德云图 | `qwenwork/connectors/mcp.json/mcp.json#cloudmap-gateway` | 数据分析 | 1 | 提供地图数据、商业洞察、选址经营等服务 |
| cue | `qwenwork/connectors/mcp.json/mcp.json#cue` | 知识文档 | 1 | 连接你的 cue 账号：用自己的智能体创建、发布和演示 cue 演示文稿与文档，管理分享和阅读记录。 |
| 融易算DeepTax | `qwenwork/connectors/mcp.json/mcp.json#deeptax` | 法律服务 | 1 | 完成登录授权并绑定公司后，可查看绑定公司与客户，进行智能开票、发票查询与统计，并查看银行流水、工资凭证、税种申报等账税数据。 |
| 叮当OKR | `qwenwork/connectors/mcp.json/mcp.json#dingteam-okr-mcp` | 项目管理 | 1 | 连接叮当OKR，读写目标与关键结果、同步进度，并生成 OKR 目标关系图。适用于目标制定、拆解、对齐与进度查询。 |
| 单小二 | `qwenwork/connectors/mcp.json/mcp.json#dxe-mcp-server` | 效率工具 | 1 | 帮助客户更快捷操作工单查询使用 |
| 亿贸AI | `qwenwork/connectors/mcp.json/mcp.json#easipass` | 法律服务 | 1 | 提供贸易合规审查、商品归类查询及贸易市场数据分析与智能解读服务。 |
| Elasticsearch连接器 | `qwenwork/connectors/mcp.json/mcp.json#elasticsearch-service` | 数据分析 | 1 | 连接 Elasticsearch 数据库 |
| 口岸高质量数据集 | `qwenwork/connectors/mcp.json/mcp.json#eptrade-hqd` | 法律服务 | 1 | 口岸贸易业务 MCP 服务，依托口岸高质量标准化数据集，对外输出标准化调用能力，核心包含两大模块：一是贸易合规码表查询，内置检验检疫名称、危险化学品目录、危险货物品名表、两用物项和技术进出口许可证管理目录、海关 HS 税则编码五类官方基准数据；二是贸易关务智能问答。服务覆盖报关通关、出口合规校验等航贸业务场景，底层数据完成标准化清洗与权威交叉校验，可支撑大模型问答、合规检索、编码匹配等 AI 应用落地，助力口岸贸易数字化转型。 |
| EverMe | `qwenwork/connectors/mcp.json/mcp.json#everme` | 知识文档 | 1 | EverMe 是一款以用户记忆为中心的个人 AI 数字分身产品，将日常对话沉淀为个人专属的记忆资产，实现多端共享的第二大脑。 |
| MOSS增长谋士 | `qwenwork/connectors/mcp.json/mcp.json#fanruan-growth-advisor` | 法律服务 | 1 | MOSS增长谋士是帆软软件有限公司面向企业打造的商业洞察智能体，拥有50多类企业级数据源，涵盖企业工商、招投标、关键人员、供应链图谱、企业诉讼与经营风险、全平台舆情等信息源，可以帮助企业解决市场行业研究、ToB线索商机挖掘、竞对情报分析、合作风险洞察等工作，助力企业增长。 |
| figma | `qwenwork/connectors/mcp.json/mcp.json#figma` | 设计创意 | 1 |  |
| Flova AI | `qwenwork/connectors/mcp.json/mcp.json#flova` | 设计创意 | 1 | 连接 Flova AI，在千问办公中创建和继续视频与图片创作项目。生成图片、视频、分镜等类型的素材，覆盖漫剧短剧、广告、短片与音乐 MV等场景的全流程创作与交付。 |
| google-calendar | `qwenwork/connectors/mcp.json/mcp.json#google-calendar` | 效率工具 | 1 |  |
| google-maps | `qwenwork/connectors/mcp.json/mcp.json#google-maps` | 效率工具 | 1 |  |
| 找客户 | `qwenwork/connectors/mcp.json/mcp.json#gtmos` | 市场营销 | 1 | 找客户是一款面向 B2B 销售、市场和创业者的 AI 客户线索连接器。用户只需说明销售的产品或服务，即可自动完成目标客户推断、作战方案生成、全网商机搜索、购买意向判断和联系方式下钻，并返回带有公司名称、地区、商机依据、来源链接、发现时间和联系方式状态的结构化客户线索。支持国内与海外市场、目标地域、产品优势以及综合排序、意向优先、日期优先和触达优先等策略。 |
| 用友好会计｜智能财税管理 | `qwenwork/connectors/mcp.json/mcp.json#hkj` | 数据分析 | 1 | 好会计 MCP 连接器：这是一个 Streamable HTTP MCP 服务。先调用 initialize 根据[账套]来建立会话；当用户没有指定账套时，根据[获取账套列表]工具查询默认账套；当用户指定账套时，使用模糊自然语言匹配账套来选择账套。支持好会计财务数据的查询与操作。 |
| 可灵AI | `qwenwork/connectors/mcp.json/mcp.json#https:/klingai.com` | 市场营销 | 1 | 一句话，让灵感从想法变成大片。可灵 AI 面向创作者、设计师、电商卖家、视频制作人和营销团队，可在千问办公中通过自然语言完成文生图、图生图、文生视频、图生视频、动作控制、参考图创作和多镜头视频。支持上传素材、查询额度、提交已确认的生成任务、跟踪进度并获取最终图片或视频。 |
| 极睿电商创作 | `qwenwork/connectors/mcp.json/mcp.json#infimind-ecommerce-content` | 电商零售 | 1 | 电商内容专家面向品牌、电商运营和内容团队，提供图片与视频一体化 AI 创作能力。通过统一连接器可创建智能精修、商品主图、商品详情页、爆款图复制、KOC 种草、图文带货、视频生成和爆款视频复制任务，并查询任务状态与结果。采用 OAuth 2.0 按用户授权，支持个人与企业空间的数据权限隔离。 |
| 简道云 | `qwenwork/connectors/mcp.json/mcp.json#jiandaoyun` | 数据分析 | 1 | 用于查询、整理和填写简道云数据，用自然语言查找表单记录、汇总业务进展、生成分析，并在确认后创建新记录。 |
| 金数据 | `qwenwork/connectors/mcp.json/mcp.json#jinshuju` | 数据分析 | 1 | 用自然语言在金数据（jinshuju.net）创建表单、表格、问卷、考试、报名、收款等各类场景应用：一句话生成表单与表格、批量处理数据、自动统计分析，零门槛快速搭建。 |
| 金智CRM | `qwenwork/connectors/mcp.json/mcp.json#jinzhi_mcp` | 市场营销 | 1 | 金智CRM是覆盖销售全流程的业务管理平台，通过连接器直接调取客户数据、执行制单与提醒，解决业务信息查询难、操作繁琐的问题。 |
| 同花顺快查·企业数据 | `qwenwork/connectors/mcp.json/mcp.json#kuaicha365` | 法律服务 | 1 | 涵盖中国企业金融股票、企业工商、股权投资、司法风险、知识产权、招投标、新闻舆情、法律法规、案件文书等数据，结果可溯源，避免幻觉。用自然语言快速完成企业身份核验与背景调查。 |
| line | `qwenwork/connectors/mcp.json/mcp.json#line` | 沟通协作 | 1 |  |
| Linear | `qwenwork/connectors/mcp.json/mcp.json#linear` | 项目管理 | 1 | 管理 Linear 问题、项目和团队 |
| Linkfox 跨境商品视频生成 | `qwenwork/connectors/mcp.json/mcp.json#linkfox-video` | 电商零售 | 1 | 面向跨境电商视频素材生产的 AI 工具链，覆盖品牌风格提炼、带货视频生成、带货口播、视频复刻、视频翻译等能力，帮助商家快速打造高质量、高转化的全链路电商视觉内容。 |
| 励销CRM | `qwenwork/connectors/mcp.json/mcp.json#lxcrm` | 法律服务 | 1 | 用自然语言查询和录入励销CRM线索、客户、商机、合同、产品、回款开票、跟进记录等业务数据，轻松搞定销售全链路工作。 |
| Moka HR | `qwenwork/connectors/mcp.json/mcp.json#moka` | 沟通协作 | 1 | 招聘和人事一体的 AI 同事，把查询与执行收进一个对话。人才推荐、招聘动态、考勤绩效、审批待办，一句话问清；候选人寻访、面试分析与面试官评估，一句话发起。 |
| MySQL连接器 | `qwenwork/connectors/mcp.json/mcp.json#mysql-service` | 数据分析 | 1 | 连接 MySQL 数据库进行 AI 数据分析、 AI 业务分析等场景 |
| Neon | `qwenwork/connectors/mcp.json/mcp.json#neon` | 数据分析 | 1 | 管理 Neon Serverless Postgres 数据库、分支和项目 |
| Notion | `qwenwork/connectors/mcp.json/mcp.json#notion` | 知识文档 | 1 | 读写和检索 Notion 页面与数据库 |
| ONES | `qwenwork/connectors/mcp.json/mcp.json#ones` | 数据分析 | 1 | 连接 ONES 企业级智能研发管理平台，让千问办公在用户授权范围内访问和操作项目与知识库数据。支持查询项目、需求、任务和缺陷，创建及更新工作项、推进状态、登记工时，以及检索、创建和更新 Wiki 文档，为进度跟踪、研发协作和知识整理提供数据与操作能力。 |
| Pixso | `qwenwork/connectors/mcp.json/mcp.json#pixso-remote-mcp` | 设计创意 | 1 | Pixso MCP 是一套远程设计协作协议，从设计稿生成与编辑、组件与样式资产管理，到布局校验、视觉核验、代码与设计双向转换及设计规范调用，用户均可在对话中一站式完成。 |
| 北大法宝·法律智能检索 | `qwenwork/connectors/mcp.json/mcp.json#pkulaw` | 法律服务 | 1 | 语义（自然语言描述） + 关键词（精确/模糊查询）双模式检索法规与案例，结果均带 pkulaw.com 原文链接，可追溯、可复核、可直接引用。 |
| 北极星绩效 | `qwenwork/connectors/mcp.json/mcp.json#polaris-pekhr` | 人力招聘 | 1 | 一键连接北极星绩效，快速获取个人绩效结果，汇总分析团队考核情况，直观呈现绩效分布。 |
| OpenBoost 跨境数据 | `qwenwork/connectors/mcp.json/mcp.json#proboost-tiktok-amazon-patent-mcp` | 电商零售 | 1 | 支持市场研究、选品分析、竞对监控、VOC洞察、关键词分析、listing生成等跨境电商应用场景 |
| 企查查 | `qwenwork/connectors/mcp.json/mcp.json#qcc-company` | 金融投研 | 1 | 查询和核实企业工商登记信息。支持股东结构、实际控制人、受益所有人、高管团队、对外投资、财务数据、年报及上市信息查询，用自然语言快速完成企业身份核验与背景调查。 |
| 企查查·法律数据 | `qwenwork/connectors/mcp.json/mcp.json#qcc-legal` | 法律服务 | 1 | 检索与核验中国法律法规和司法案例，覆盖全量现行法律、行政法规、司法解释——法规级到法条级逐字正文，标注时效性与效力级别；海量裁判文书及 2.5 万+ 权威案例（最高法/最高检指导性案例、公报案例、典型案例）；并对文本中的法条与案号引用逐条回库核验、标注时效、生成可溯源超链。用自然语言完成法条依据查找、类案检索、原文调取与法律引用核验，从源头消除法条与案号幻觉。 |
| 企百科 | `qwenwork/connectors/mcp.json/mcp.json#qibook` | 效率工具 | 1 | 提供企业主体的身份识别与基础信息查询服务，包含企业模糊搜索、受益所有人结果、企业基本信息、变更信息、企业联系方式、主要人员信息、企业股东、实际控制人等工具。 |
| 纷享销客CRM | `qwenwork/connectors/mcp.json/mcp.json#sharecrm` | 市场营销 | 1 | 用自然语言查询客户、推进商机、写跟进记录、处理审批、建图表等，轻松搞定销售全链路工作。 |
| 数联宝-铁路货运查询 | `qwenwork/connectors/mcp.json/mcp.json#shulian-railway` | 电商零售 | 1 | 查询铁路站点停卸装命令及生效时间，以及铁路专用线资料、办理范围和相关单位。 |
| Supabase | `qwenwork/connectors/mcp.json/mcp.json#supabase` | 数据分析 | 1 | 管理 Supabase 项目、数据库和边缘函数 |
| 淘宝闪购餐饮商家版 | `qwenwork/connectors/mcp.json/mcp.json#taobao-flash-sale-cli` | 电商零售 | 1 | 在千问办公沙箱中安装并连接淘宝闪购餐饮 CLI |
| 淘宝闪购零售商家版 | `qwenwork/connectors/mcp.json/mcp.json#taobao-flash-sale-retail` | 电商零售 | 1 | 连接淘宝闪购零售MCP能力 |
| 淘宝天猫商家端 | `qwenwork/connectors/mcp.json/mcp.json#taobao-open-platform` | 电商零售 | 1 | 连接生意参谋、阿里妈妈、淘宝直播商家后台、千牛等多个淘宝天猫商家后台数据MCP |
| 钉钉项目 | `qwenwork/connectors/mcp.json/mcp.json#teambition-mcp` | 项目管理 | 1 | 管理钉钉项目Teambition 项目、任务和团队。 |
| Vercel | `qwenwork/connectors/mcp.json/mcp.json#vercel` | 开发工具 | 1 | 管理 Vercel 项目、部署和 Serverless 函数 |
| 微博 | `qwenwork/connectors/mcp.json/mcp.json#weibo` | 市场营销 | 1 | 通过微博 MCP 连接器访问微博开放平台全部核心能力：微博查询与发布、评论互动、头条文章与V+付费专栏、点赞表态、用户资料与统计、粉丝深度画像、实时热搜榜单及影视综艺指数等。 |
| 万方数据 | `qwenwork/connectors/mcp.json/mcp.json#wfdata` | 教育学习 | 1 | 通过万方数据 MCP 查询学术期刊、学位论文、专利、标准等文献资源，支持智能检索、全文下载与引文分析。 |
| Wind Alice万得金融数据 | `qwenwork/connectors/mcp.json/mcp.json#wind` | 金融投研 | 1 | 全量开放万得（Wind）金融数据与工具能力，覆盖沪深港美等全球60多个国家地区的股票、基金、债券、商品、指数、经济数据与万得金融模型与工具集。让WorkBuddy变身金融分析专家，成为具备数据穿透、投研分析、风险决策等多维金融能力的专业智能体。 |
| 销帮帮CRM | `qwenwork/connectors/mcp.json/mcp.json#xbb-mcp-server` | 法律服务 | 1 | 提供销帮帮CRM客户、线索、商机、跟进记录、合同、回款等业务查询能力，快速获取权限范围内的业务数据。 |
| 小鹅通 | `qwenwork/connectors/mcp.json/mcp.json#xiaoe-mcp` | 电商零售 | 1 | 用自然语言管理小鹅通店铺：查询课程与学员，创建和编辑课程，查看订单，并查找或上传图片、音频、电子书和文档素材。 |
| 小裂变SCRM | `qwenwork/connectors/mcp.json/mcp.json#xiaoliebian` | 市场营销 | 1 | 帮助品牌商家查询企业微信中的私域客户、客户群数据，制定朋友圈发布任务、群发触达任务，自动统计员工聊天排行榜，总结员工和客户聊天内容，小裂变SCRM&千问办公帮你做好企业微信私域运营 |
| 销售易CRM | `qwenwork/connectors/mcp.json/mcp.json#xiaoshouyi` | 市场营销 | 1 | 用自然语言查客户、推商机、盘线索、领公海、写跟进，一句话打通销售工作闭环。 |
| TextIn xParse·智能文档解析 | `qwenwork/connectors/mcp.json/mcp.json#xparse-mcp` | 数据分析 | 1 | 支持 PDF、图片、Word、Excel、PPT、扫描件等文档的高精度高性能OCR/文字识别、解析、格式转换、提取与结构化抽取，可识别表格、公式、手写体并输出 Markdown 或 JSON，支持复杂表格版式还原和批量处理，每日免费 1000 页。更可支持文档图像鉴伪，精准判定图片真假。 |
| 薪人薪事 | `qwenwork/connectors/mcp.json/mcp.json#xrxs` | 人力招聘 | 1 | 通过自然语言管理薪人薪事：覆盖组织员工、考勤假期、招聘人才、绩效人效、薪酬个税等全模块 HR 场景，让 AI 助手成为懂业务的 HR 虚拟员工。 |
| 银泰商业开放平台 | `qwenwork/connectors/mcp.json/mcp.json#yintai-open-platform` | 电商零售 | 1 | 浙江莲荷科技有限公司 |
| 有赞 | `qwenwork/connectors/mcp.json/mcp.json#youzan` | 市场营销 | 1 | 通过自然语言查询有赞店铺数据，覆盖商品、订单、客户会员、营销活动、供应链、门店、员工、储值卡、企微等业务。 |
| 华宇元典法律数据 | `qwenwork/connectors/mcp.json/mcp.json#yuandian` | 法律服务 | 1 | 华宇元典法律数据为智能体提供法律法规、案例文书、企业信息 MCP 工具能力。 |
| 云听ConsumerLens | `qwenwork/connectors/mcp.json/mcp.json#yunting-consumerlens` | 市场营销 | 1 | 云听ConsumerLens 提供基于电商评论与消费者反馈数据的查询与分析能力，支持品类/品牌口碑洞察、竞品对比、问题发现及指标分析。 |
| 云图智影 | `qwenwork/connectors/mcp.json/mcp.json#yuntu-art` | 设计创意 | 1 | 云图智影 - 影视 AI 创作平台（MCP + Skills 连接器包） |
| 语忆Neosight | `qwenwork/connectors/mcp.json/mcp.json#yuyidata` | 电商零售 | 1 | 集成电商行业分析 Skill 与数据 MCP 连接器。对接对话、评价、订单、商品全域数据，自动完成数据加工、问题发现、原因归因与策略生成，覆盖客服质检、VOC 洞察、商品售后、经营分析等场景，直接输出可执行的行动建议，支撑企业级 AI 业务落地。 |
| 企享link·发票验真 | `qwenwork/connectors/mcp.json/mcp.json#zhengqiying` | 法律服务 | 1 | 为客户提供发票验真服务 |
| 证书管理 | `qwenwork/connectors/mcp.json/mcp.json#zzdingyun` | 数据分析 | 1 | 证书管理助手，为企业提供人员证书与企业证书的全流程数字化管控。涵盖证书台账、到期预警，能够直接查询、分析、管理企业的证书数据，自动识别证书缺口并给出补缺建议。适用于资质申报、投标校验、动态核查等场景。 |
| 天眼查 | `qwenwork/connectors/mcp.json/mcp.json#天眼查MCP` | 法律服务 | 1 | 天眼查 MCP 是天眼查官方推出的，面向智能体的企业商业信息连接服务，可通过标准 MCP 接口调用天眼查企业数据能力，覆盖企业主体检索、工商登记、股权结构、受益所有人、董监高、经营公示、风险诉讼、知识产权、上市公司信息、招投标与资产处置等维度。为企业核验、客户尽调、风险排查、供应商评估、投资研究、法务合规和经营分析等场景提供可信数据支撑。 |

## 最近变更

| Date | Change Log | Summary |
| --- | --- | --- |
| 2026-10-15-192505 | [2026-10-15-192505](qwenwork/change-logs/2026-10-15-192505.md) | QwenWork 本次同步新增 0 个文件、修改 1 个文件、删除 0 个文件。 受影响范围：skills/wecom-unified。 |
| 2026-10-13-204349 | [2026-10-13-204349](qwenwork/change-logs/2026-10-13-204349.md) | QwenWork 本次同步新增 2 个文件、修改 0 个文件、删除 0 个文件。 新增条目：connectors/market-metadata.json, connectors/mcp.json。 受影响范围：connectors/market-metadata.json, connectors/mcp.json。 |
| 2026-10-13-203506 | [2026-10-13-203506](qwenwork/change-logs/2026-10-13-203506.md) | QwenWork 本次同步新增 477 个文件、修改 0 个文件、删除 0 个文件。 新增条目：skills/computer-use-guidance-windows, skills/lark-approval, skills/lark-apps, skills/lark-attendance, skills/lark-base, skills/la... |
| 2026-10-13-202954 | [2026-10-13-202954](qwenwork/change-logs/2026-10-13-202954.md) | QwenWork 本次同步新增 1964 个文件、修改 120 个文件、删除 0 个文件。 新增条目：skills/a-stock-diagnosis, skills/a-stock-realtime, skills/activity-recommend, skills/agent-task-hub, skills/ai-table-data-anal... |
| 2026-09-13-180003 | [2026-09-13-180003](qwenwork/change-logs/2026-09-13-180003.md) | QwenWork 本次同步新增 274 个文件、修改 3 个文件、删除 607 个文件。 新增条目：skills/.dws-skill-state.json, skills/dingtalk-aisearch, skills/dingtalk-aitable, skills/dingtalk-calendar, skills/dingtalk-chat... |
| 2026-09-05-180002 | [2026-09-05-180002](qwenwork/change-logs/2026-09-05-180002.md) | QwenWork 本次同步新增 129 个文件、修改 246 个文件、删除 75 个文件。 受影响范围：skills/create-skill, skills/dws, skills/media-generation, skills/plugin-creator, skills/pptx。 |
| 2026-08-30-205640 | [2026-08-30-205640](qwenwork/change-logs/2026-08-30-205640.md) | QwenWork 本次同步新增 774 个文件、修改 10 个文件、删除 0 个文件。 新增条目：experts/amap-site-selection, experts/cn-family-law-expert-suite, experts/content-creation-suite, experts/proboost-amazon-operati... |
| 2026-08-24-180002 | [2026-08-24-180002](qwenwork/change-logs/2026-08-24-180002.md) | QwenWork 本次同步新增 103 个文件、修改 7 个文件、删除 11 个文件。 受影响范围：skills/pdf, skills/pptx。 |
| 2026-08-17-180001 | [2026-08-17-180001](qwenwork/change-logs/2026-08-17-180001.md) | QwenWork 本次同步新增 368 个文件、修改 0 个文件、删除 0 个文件。 新增条目：experts/Legal-Department, skills/qw-pages, skills/qw-pages-supabase。 受影响范围：experts/Legal-Department, skills/qw-pages, skills/qw-p... |
| 2026-08-10-160206 | [2026-08-10-160206](qwenwork/change-logs/2026-08-10-160206.md) | QwenWork 本次同步新增 0 个文件、修改 1 个文件、删除 0 个文件。 受影响范围：skills/dws。 |
| 2026-08-09-180003 | [2026-08-09-180003](qwenwork/change-logs/2026-08-09-180003.md) | QwenWork 本次同步新增 0 个文件、修改 1 个文件、删除 0 个文件。 受影响范围：skills/dws。 |
| 2026-08-08-180003 | [2026-08-08-180003](qwenwork/change-logs/2026-08-08-180003.md) | QwenWork 本次同步新增 401 个文件、修改 20 个文件、删除 1 个文件。 受影响范围：skills/create-skill, skills/dws。 |
| 2026-08-05-231200 | [2026-08-05-231200](qwenwork/change-logs/2026-08-05-231200.md) | QwenWork 本次同步新增 891 个文件、修改 0 个文件、删除 0 个文件。 新增条目：experts/ali1688-buyer-assistant, experts/ali1688-seller-assistant, experts/consulting-delivery, experts/contract-management, expe... |
