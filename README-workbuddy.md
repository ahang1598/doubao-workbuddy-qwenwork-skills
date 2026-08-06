# WorkBuddy Skills And Experts

本文件由 `scripts/sync_platform.py --platform workbuddy` 自动生成，整理 `workbuddy/` 下同步的技能、专家团和插件索引。

## 同步概览

- 平台目录：`workbuddy/`
- 定时任务：`WorkbuddySkillsDailySync`，每天 18:00 运行
- 当前索引条目数：303
- 当前索引文件数：8431
- 最近变更：[2026-08-05-230159](workbuddy/change-logs/2026-08-05-230159.md) - WorkBuddy 本次同步新增 8434 个文件、修改 0 个文件、删除 0 个文件。 新增条目：cb_teams_experts/a-share-analysis, cb_teams_experts/agent-sdk-dev, cb_teams_experts/ai-hedge-fund, cb_teams_experts/ardot-desig...

## 数据来源

- `experts` <= `/mnt/c/Users/15805/.workbuddy/plugins/marketplaces/experts/plugins`
- `official_experts/external_plugins` <= `/mnt/c/Users/15805/.workbuddy/plugins/marketplaces/codebuddy-plugins-official/external_plugins`
- `official_experts/plugins` <= `/mnt/c/Users/15805/.workbuddy/plugins/marketplaces/codebuddy-plugins-official/plugins`
- `cb_teams_experts/plugins` <= `/mnt/c/Users/15805/.workbuddy/plugins/marketplaces/cb_teams_marketplace/plugins`
- `cb_teams_experts/plugins_analysis_company_analysis.md` <= `/mnt/c/Users/15805/.workbuddy/plugins/marketplaces/cb_teams_marketplace/plugins_analysis_company_analysis.md`
- `skills` <= `/mnt/c/Users/15805/.workbuddy/skills`

## 导航文件

各同步目录根部的 `SUMMARY.md` 提供按用途分组的场景导航，便于快速定位：

- [Marketplace Experts](workbuddy/experts/SUMMARY.md) — `experts/` 功能导航
- [Official Experts / External Plugins](workbuddy/official_experts/external_plugins/SUMMARY.md) — `official_experts/external_plugins/` 功能导航
- [Official Experts / Plugins](workbuddy/official_experts/plugins/SUMMARY.md) — `official_experts/plugins/` 功能导航
- [CB Teams Experts](workbuddy/cb_teams_experts/plugins/SUMMARY.md) — `cb_teams_experts/plugins/` 功能导航
- [Skills](workbuddy/skills/SUMMARY.md) — `skills/` 功能导航

## 分类索引

### Marketplace Experts

| Name | Directory | Category | Files | Description |
| --- | --- | --- | ---: | --- |
| A股研究团队 | `workbuddy/experts/a-share-analysis` | 08-FinanceInvestment | 38 | 8位研究专家支持多步骤工作流编排，覆盖宏观策略、盘面解读、个股深度、估值定价、产业链映射、资金追踪、风险诊断 |
| 内容创作专家团 | `workbuddy/experts/ai-content-creator-team` | 06-ContentCreative | 25 | AI驱动的多模态内容生产团队，从创意策划到成品交付全覆盖，涵盖品牌定位、情绪板、广告方向、文案创作、视频生成、图片设计、精修合成和素材改编。 |
| 智数分析专家团 | `workbuddy/experts/ai-data-copilot` | 04-DataAI | 22 | 6人AI数据分析团队，擅长自然语言转SQL、Python建模、RAG知识问答、仪表盘可视化与报告生成 |
| AICoding 架构专家团 | `workbuddy/experts/aicoding-architecture-expert-team` | 02-Engineering | 289 | 面向复杂系统架构设计，协同完成资料摄入、调研、业务、系统、部署、安全与用户故事全流程交付。 |
| 相信光么 | `workbuddy/experts/believe-in-light` | 08-FinanceInvestment | 26 | 光模块产业链信号监控专家团。主理人 + 6位成员Agent 三端采集信号，因果验证+权重校准，三层嵌套输出景气度评级。 |
| 汽车行业内容创作专家团 | `workbuddy/experts/content-creation-expert-prod` | 06-ContentCreative | 31 | 汽车行业垂类图文创作团队，5 人协作完成选题、撰写、智能配图与质检，一键交付懂车帝、小红书等风格图文 |
| 全域内容分发专家团 | `workbuddy/experts/content-distribution-team` | 06-ContentCreative | 36 | 一站式多平台内容分发方案，覆盖12+全球社交媒体平台，提供发布规则适配、排期管理、批量发布编排和跨平台数据分析能力 |
| 内容变现商业化专家团 | `workbuddy/experts/content-monetization-team` | 05-MarketingGrowth | 19 | 5人专家团协作覆盖CPS带货分佣、CPE/CPM效果广告、创作者-品牌交易撮合与收益分析，助力内容创作者和品牌方实现商业化价值最大化 |
| 腾讯电子签合同法务专家 | `workbuddy/experts/contract-legal-expert` | 13-TencentZone | 17 | 腾讯电子签合同法务专家擅长合同起草、审查、对比、法规检索，能在线发起签署，劳动/租赁/买卖全场景覆盖 |
| 出海海 | `workbuddy/experts/cross-border-ecommerce-expert` | 05-MarketingGrowth | 10 | 精通亚马逊Shopify等国际电商平台，助力品牌出海全球 |
| 文档达 | `workbuddy/experts/document-generation-expert` | 10-ProjectQuality | 85 | 自动化生成各类业务文档，大幅提升文档创建效率 |
| 科研专家团 | `workbuddy/experts/empirical-research-team` | 04-DataAI | 35 | 覆盖实证研究全流程的专家团：因果推断、稳健性检验、出版级表图与降AIGC，高效完成可复现学术论文 |
| 工程保障团队 | `workbuddy/experts/engineering-assurance-team` | 02-Engineering | 16 | 由工程总监领导的 5 人工程专家团队：代码审查师（安全/性能/正确性）、架构师（系统设计/ADR）、SRE 工程师（事故响应/部署）、测试专家（测试策略/覆盖率）和技术文档师（文档/Runbook）。处理从代码审查到事故响应的复杂工程工作流。 |
| 企业法务专家团 | `workbuddy/experts/enterprise-legal-team` | 11-SecurityCompliance | 211 | 面向企业法务的多角色专家团，覆盖合同、交易、隐私、产品、监管、AI 治理、雇佣与知识产权分诊。 |
| equity-research | `workbuddy/experts/equity-research` | agent | 35 | Comprehensive equity research toolkit: earnings analysis, initiating coverage, DCF/comps valuation, long-short pitches, investment memos, event-driven analysis, portfolio risk management, and full research workflows |
| 福帮手 | `workbuddy/experts/fbsir-eight-seat-board` | 12-IndustryConsultant | 82 | 福帮手经营决策独立审议专家团｜按案组建必要席位，独立判断、交叉质询、保留异议，交付可追溯行动备忘录 |
| 鹏城信息AI专家 | `workbuddy/experts/game-development-studio` | 03-GameSpatial | 17 | 统筹策划、技术、美术、音频、质量、运营六大专业成员，以七阶段工作流驱动游戏从概念到上线流程协同开发。 |
| 专业高考顾问 | `workbuddy/experts/gaokao-advisor` | 12-IndustryConsultant | 41 | 检索高考真题作文、高校专业信息，查批次线与一分一段；提供全流程志愿填报引导，产出带冲稳保的志愿报告 |
| 深度研究团队 | `workbuddy/experts/gpt-researcher-team` | 04-DataAI | 17 | 7 位专业角色分 5 阶段协作完成深度研究：初始调研 → 规划大纲 → 逐章深度研究（审稿修订循环）→ 撰写报告框架 → 发布输出。支持完整 / 快速 / 单章三种模式。适用于行业研究、竞品分析、技术综述、学术文献综述等场景，产出带多源超链接引用的专业研究报告。 |
| HR 运营团队 | `workbuddy/experts/hr-operations-team` | 09-OperationsHR | 14 | 由 HR 总监领导的 4 人人力资源专家团队：招聘专家（招聘漏斗/面试设计/Offer 起草）、薪酬分析师（市场对标/薪酬带分析/股权建模）、组织发展顾问（组织规划/绩效评估/人员分析）和 HR 运营专员（入职引导/政策查询/合规）。覆盖完整的员工生命周期。 |
| 花叔数据分析专家团 | `workbuddy/experts/huashu-data-pro` | 04-DataAI | 11 | 「一人公司」本地数据分析专家团。一份 Excel 进，趋势 / 结构 / 异常三专家并行分析，交付网页、Excel、PPT 三格式报告，数据不出本地。 |
| 卡尔的人感PPT专家团 | `workbuddy/experts/humanize-ppt-team` | 06-ContentCreative | 342 | 把原始资料梳理成人感PPT大纲，调度HTML生成、演讲模式、视频动效与交付质检，形成可演示成果。 |
| 救火队 | `workbuddy/experts/incident-response-commander` | 02-Engineering | 79 | 系统故障时冷静指挥团队快速定位处理和恢复，是终极救火队长 |
| 鹏城信息AI专家 | `workbuddy/experts/interview-simulator` | 09-OperationsHR | 5 | 模拟任意职位真实面试官，覆盖技术产品销售人事等全岗位，逐题评分、详细反馈与录用建议，助你备战面试。 |
| 投资大师专家团 | `workbuddy/experts/investment-masters-team` | 08-FinanceInvestment | 51 | 13位传奇投资哲学家 + 6位专业分析师并行分析，风险管理师评估约束，投资组合经理信号聚合投票，多角度投资分析参考 |
| 智能发票专家团 | `workbuddy/experts/invoice-verify-workbuddy` | 11-SecurityCompliance | 29 | 五位AI专家接力协作，通过上传文件、表格或文件夹，完成识别、税局验真、信用核查与归档 |
| 求职陪跑团 | `workbuddy/experts/job-companion-team` | 12-IndustryConsultant | 21 | 5 角色陪跑型专家团，7 阶段接力覆盖自我盘点、目标定位、简历打磨、面试陪练、谈薪决策与入职复盘全流程。 |
| KET备考专家团 | `workbuddy/experts/ket-prep-team` | 12-IndustryConsultant | 16 | 剑桥认证考官领衔，为小学生提供KET全流程备考：学情测评、词汇语法地基、听说读写专项提分、考前冲刺模考，助力Merit（优秀）/Distinction（卓越）达标。 |
| 营销战役团队 | `workbuddy/experts/marketing-campaign-team` | 05-MarketingGrowth | 14 | 由营销总监领导的 4 人营销专家团队：内容创作者（博客/邮件/社媒/品牌声音）、活动策划师（战役策略/受众/渠道/预算）、SEO 专家（技术审计/内容优化/效果分析）和品牌分析师（竞品定位/品牌审核）。覆盖完整营销生命周期。 |
| 营销增长专家团 | `workbuddy/experts/marketing-growth-team` | 05-MarketingGrowth | 85 | fCMO 级全栈营销增长团队：转化率优化、SEO 与内容策略、增长工程、数据归因分析与策略规划，全方位助力 SaaS 产品增长 |
| 计算机等级考试专家团 | `workbuddy/experts/ncre-expert` | 02-Engineering | 15 | NCRE一至四级专家团，覆盖Office、编程、数据库与网络安全，分工协作，量身定制备考方案。 |
| 一人公司专家团 | `workbuddy/experts/opc-team` | 12-IndustryConsultant | 53 | 基于由Easy创作的《一人企业方法论》，9位专家陪你走完从资源盘点、利基定位到MVP、转化、复盘的一人公司全流程共创 |
| 专业文档生成团队 | `workbuddy/experts/openspec-doc-team` | 10-ProjectQuality | 11 | 4 位专业角色分 6 阶段协作完成企业级长文档生成：需求分析 → 知识检索 → 内容生成 → 质量审核（循环）→ 整合汇编 → 交付输出。适用于施工图设计说明、技术方案、招投标文件、维修手册、API/系统文档等场景。 |
| 万方数据 | `workbuddy/experts/paper-topic-selection` | 12-IndustryConsultant | 26 | 帮你做论文选题：检索文献、推荐方向、评估新颖性、生成标题、出领域报告。说学科方向即可。 |
| 产品战略团队 | `workbuddy/experts/product-strategy-team` | 01-ProductDesign | 16 | 由产品总监领导的 5 人产品专家团队：需求分析师（PRD/功能规格书）、用户研究员（调研综合分析）、竞品分析师（竞争情报）、数据分析师（指标追踪）和路线图规划师（路线图管理/迭代规划）。覆盖从构思到上线的完整产品生命周期。 |
| 袋鼠帝宣传片创作团队 | `workbuddy/experts/promo-creator-team` | 06-ContentCreative | 20 | 6位专业角色分6阶段协作完成产品宣传片全流程制作：创意简报、逐镜头分镜、素材生产、HyperFrames剪辑合成、BGM设计与交付，从产品URL到可发布的60-90秒宣传片MP4 |
| 闪造造 | `workbuddy/experts/rapid-prototyping-engineer` | 02-Engineering | 82 | 以极快速度将创意转化为可工作的原型，让团队快速验证想法 |
| 小红书增长专家团 | `workbuddy/experts/redfox-xiaohongshu-ops-team` | 06-ContentCreative | 118 | 一支专注小红书增长的多角色团队：从爆款灵感到笔记创作、账号诊断、素材下载，覆盖运营全链路。 |
| Rightly 合规辅助专业版 | `workbuddy/experts/rightly-compliance-assistant-pro` | 11-SecurityCompliance | 44 | 隐私合规专家团，解读政策与通报条目，分析违规详情，结合专业版 Rightly 数据输出整改方案。 |
| 资本市场路演研究团 | `workbuddy/experts/roadshow-research-team` | 08-FinanceInvestment | 32 | 多专家协作标的研报：多源解析、行业对比、财报三表（上市+未上市）、路演研报、股价关联，模板出报告。 |
| 销售作战团队 | `workbuddy/experts/sales-battle-team` | 07-SalesCommerce | 14 | 由销售总监领导的 4 人销售专家团队：客户研究员（公司/潜客情报）、外联策略师（邮件起草/电话准备）、竞争情报分析师（赢单/丢单分析/Battle Card）和销售预测分析师（Pipeline 评审/预测）。覆盖从研究到成交的完整销售周期。 |
| 吴八哥 | `workbuddy/experts/senior-developer` | 02-Engineering | 118 | 10年以上全栈经验，精通多种语言和框架，是团队的技术中坚 |
| SEO 内容营销团队 | `workbuddy/experts/seo-content-team` | 05-MarketingGrowth | 21 | 7位专业角色分5阶段协作：关键词研究、SEO长文创作、技术优化、内容编辑、链接策略、转化率分析，全流程自动化产出高质量SEO内容 |
| 社媒互动增长专家团 | `workbuddy/experts/social-engagement-team` | 05-MarketingGrowth | 19 | 通过智能化互动自动化、AI评论运营、高转化信号挖掘和品牌舆情监控，安全高效提升社交媒体互动效果，覆盖14+全球主流平台 |
| software-company | `workbuddy/experts/software-company` | team | 7 | Software Development Team - Optimized multi-agent SOP workflow for fast software delivery |
| 腾讯自选股股票投研专家团 | `workbuddy/experts/stock-partner-team` | 08-FinanceInvestment | 38 | 六位投研专家团，兼擅产业策略、信号捕捉、估值定价、逆向布局、基本面与短线，基于实时行情多视角研判。 |
| 财税合规专家团 | `workbuddy/experts/tax-compliance-team` | 11-SecurityCompliance | 19 | 覆盖票据处理、记账核算、报表编制、税务申报、合规审计五大环节的企业财税合规全链路管理专家团 |
| 交易分析团队 | `workbuddy/experts/trading-agent` | 08-FinanceInvestment | 17 | 13位专业角色分5阶段协作完成投资分析：技术面、基本面、新闻面、情绪面数据采集 → 多空辩论 → 交易决策 → 三方风险评估 → 最终报告，输出 BUY/SELL/HOLD 建议及完整操作方案 |
| 像素君 | `workbuddy/experts/ui-designer` | 01-ProductDesign | 144 | 精通设计系统和组件库，追求像素级完美，打造无障碍用户界面 |
| 苍何视频解剖 | `workbuddy/experts/video-dissection` | 06-ContentCreative | 19 | 专业拆解火爆抖音视频拍摄手法的专家团。输入抖音链接，自动提取视频、转录文案、分析景别运镜、剪辑节奏、色调风格，生成完整拍摄脚本拆解文档，并提供可落地的仿拍建议。 |
| 苍何视频生成团队 | `workbuddy/experts/video-gen-team` | 06-ContentCreative | 18 | 三位一体的AI视频创作团队：灵阅负责采集AI/科技热点，灵枢负责策划选题与脚本，灵映负责渲染MP4视频成品（配音+字幕）。全流程自动化，60秒短视频一键生成。 |
| 小程达 | `workbuddy/experts/we-chat-mini-program-developer` | 02-Engineering | 192 | 精通微信小程序开发框架和生态，打造流畅微信原生体验应用 |
| 号运运 | `workbuddy/experts/wechat-official-account-expert` | 06-ContentCreative | 38 | 精通公众号内容策略和粉丝增长，打造10万+品牌自媒体矩阵 |
| 小台 | `workbuddy/experts/workspace-builder` | 02-Engineering | 6 | 为不同人群定制专属数字工作台，覆盖学习备考、职场效率、自媒体创作、宝妈育儿、生活管理五大场景，PC/移动端双适配，一键部署即用 |

### Official Experts / External Plugins

| Name | Directory | Category | Files | Description |
| --- | --- | --- | ---: | --- |
| accessibility-compliance | `workbuddy/official_experts/external_plugins/accessibility-compliance` | official expert | 5 | WCAG 无障碍审计、合规性验证、屏幕阅读器 UI 测试、键盘导航和包容性设计 |
| agent-orchestration | `workbuddy/official_experts/external_plugins/agent-orchestration` | official expert | 4 | 多智能体系统优化、智能体改进工作流和上下文管理 |
| agents-blockchain-web3 | `workbuddy/official_experts/external_plugins/agents-blockchain-web3` | official expert | 3 | Specialized agents for blockchain development, smart contracts, and Web3 applications |
| agents-business-finance | `workbuddy/official_experts/external_plugins/agents-business-finance` | official expert | 5 | Agents for business analysis, financial modeling, and KPI tracking |
| agents-crypto-trading | `workbuddy/official_experts/external_plugins/agents-crypto-trading` | official expert | 6 | Expert agents for cryptocurrency trading, DeFi strategies, and market analysis |
| agents-data-ai | `workbuddy/official_experts/external_plugins/agents-data-ai` | official expert | 12 | Agents for data engineering, machine learning, and AI development |
| agents-design-experience | `workbuddy/official_experts/external_plugins/agents-design-experience` | official expert | 3 | Agents for UI/UX design, accessibility, and user experience optimization |
| agents-development-architecture | `workbuddy/official_experts/external_plugins/agents-development-architecture` | official expert | 12 | Expert agents for software architecture, backend development, and system design |
| agents-infrastructure-operations | `workbuddy/official_experts/external_plugins/agents-infrastructure-operations` | official expert | 9 | Agents for cloud infrastructure, DevOps, and database operations |
| agents-language-specialists | `workbuddy/official_experts/external_plugins/agents-language-specialists` | official expert | 13 | Expert agents for specific programming languages (Python, Go, Rust, etc.) |
| agents-quality-security | `workbuddy/official_experts/external_plugins/agents-quality-security` | official expert | 16 | Agents for code review, security audits, debugging, and quality assurance |
| agents-sales-marketing | `workbuddy/official_experts/external_plugins/agents-sales-marketing` | official expert | 7 | Agents for content marketing, customer support, and sales automation |
| agents-specialized-domains | `workbuddy/official_experts/external_plugins/agents-specialized-domains` | official expert | 42 | Domain-specific expert agents for research, documentation, and specialized tasks |
| all-agents | `workbuddy/official_experts/external_plugins/all-agents` | official expert | 118 | Complete collection of 117 specialized AI agents across 11 categories |
| all-commands | `workbuddy/official_experts/external_plugins/all-commands` | official expert | 176 | Complete collection of 174 slash commands across 22 categories |
| all-hooks | `workbuddy/official_experts/external_plugins/all-hooks` | official expert | 29 | Complete collection of 28 automation hooks for event-driven workflows |
| all-skills | `workbuddy/official_experts/external_plugins/all-skills` | official expert | 11 | Complete collection of 29 Claude Code skills for document processing, development, business productivity, and creative tasks |
| api-scaffolding | `workbuddy/official_experts/external_plugins/api-scaffolding` | official expert | 6 | REST 和 GraphQL API 脚手架、框架选择、后端架构设计与 API 生成 |
| api-testing-observability | `workbuddy/official_experts/external_plugins/api-testing-observability` | official expert | 3 | API 测试自动化、请求模拟、OpenAPI 文档生成、可观测性配置与监控 |
| application-performance | `workbuddy/official_experts/external_plugins/application-performance` | official expert | 5 | 应用性能工程专家代理，用于应用优化、可观测性和可扩展系统性能。包括 OpenTelemetry、分布式追踪、负载测试、多层缓存、Core Web Vitals 和全面的性能监控。 |
| arm-cortex-microcontrollers | `workbuddy/official_experts/external_plugins/arm-cortex-microcontrollers` | official expert | 2 | 面向 Teensy、STM32、nRF52 和 SAMD 的 ARM Cortex-M 固件开发，提供外设驱动和内存安全模式 |
| backend-api-security | `workbuddy/official_experts/external_plugins/backend-api-security` | official expert | 3 | API 安全加固、身份验证实现、授权模式、速率限制和输入验证 |
| backend-development | `workbuddy/official_experts/external_plugins/backend-development` | official expert | 24 | 后端 API 设计、GraphQL 架构、Temporal 工作流编排及测试驱动的后端开发 |
| blockchain-web3 | `workbuddy/official_experts/external_plugins/blockchain-web3` | official expert | 6 | 使用 Solidity 进行智能合约开发、DeFi 协议实现、NFT 平台和 Web3 应用架构 |
| brand-guidelines | `workbuddy/official_experts/external_plugins/brand-guidelines` | official expert | 3 | 将 Anthropic 官方品牌配色和排版应用于工件，确保视觉识别和专业设计标准的一致性。 |
| business-analytics | `workbuddy/official_experts/external_plugins/business-analytics` | official expert | 4 | 业务指标分析、KPI 跟踪、财务报告和数据驱动的决策制定 |
| c4-architecture | `workbuddy/official_experts/external_plugins/c4-architecture` | official expert | 6 | 全面的 C4 架构文档工作流,采用自底向上的代码分析、组件合成、容器映射和上下文图生成 |
| canvas-design | `workbuddy/official_experts/external_plugins/canvas-design` | official expert | 84 | 使用设计哲学和美学原则创建精美的视觉艺术作品，支持生成海报、设计稿和静态艺术品的 PNG 和 PDF 文档。 |
| changelog-generator | `workbuddy/official_experts/external_plugins/changelog-generator` | official expert | 2 | 自动从 git 提交历史生成面向用户的变更日志，将技术性的提交记录转换为易于理解的发布说明 |
| cicd-automation | `workbuddy/official_experts/external_plugins/cicd-automation` | official expert | 11 | CI/CD 流水线配置、GitHub Actions/GitLab CI 工作流设置及自动化部署流水线编排 |
| claude-hud | `workbuddy/official_experts/external_plugins/claude-hud` | official expert | 16 | Real-time statusline HUD for Claude Code - displays context usage, tool activity, agent tracking, and todo progress |
| cloud-infrastructure | `workbuddy/official_experts/external_plugins/cloud-infrastructure` | official expert | 17 | 云架构设计（AWS/Azure/GCP），Kubernetes 集群配置，Terraform 基础设施即代码，混合云网络，以及多云成本优化 |
| code-documentation | `workbuddy/official_experts/external_plugins/code-documentation` | official expert | 6 | 文档生成、代码解释和技术写作，支持自动化文档生成和教程创建 |
| code-refactoring | `workbuddy/official_experts/external_plugins/code-refactoring` | official expert | 6 | 代码清理、重构自动化和技术债务管理,支持上下文恢复 |
| code-review-ai | `workbuddy/official_experts/external_plugins/code-review-ai` | official expert | 3 | AI 驱动的架构审查和代码质量分析 |
| codebase-cleanup | `workbuddy/official_experts/external_plugins/codebase-cleanup` | official expert | 6 | 技术债务削减、依赖更新和代码重构自动化 |
| commands-api-development | `workbuddy/official_experts/external_plugins/commands-api-development` | official expert | 5 | Commands for designing and documenting REST and GraphQL APIs |
| commands-automation-workflow | `workbuddy/official_experts/external_plugins/commands-automation-workflow` | official expert | 2 | Commands for automating repetitive tasks and workflows |
| commands-ci-deployment | `workbuddy/official_experts/external_plugins/commands-ci-deployment` | official expert | 12 | Commands for CI/CD setup, containerization, and deployment automation |
| commands-code-analysis-testing | `workbuddy/official_experts/external_plugins/commands-code-analysis-testing` | official expert | 19 | Commands for code review, testing, and analysis |
| commands-context-loading-priming | `workbuddy/official_experts/external_plugins/commands-context-loading-priming` | official expert | 5 | Commands for loading context and priming Claude for specific tasks |
| commands-database-operations | `workbuddy/official_experts/external_plugins/commands-database-operations` | official expert | 4 | Commands for database schema design, migrations, and optimization |
| commands-documentation-changelogs | `workbuddy/official_experts/external_plugins/commands-documentation-changelogs` | official expert | 11 | Commands for generating documentation and managing changelogs |
| commands-framework-svelte | `workbuddy/official_experts/external_plugins/commands-framework-svelte` | official expert | 17 | Specialized commands for Svelte and SvelteKit development |
| commands-game-development | `workbuddy/official_experts/external_plugins/commands-game-development` | official expert | 2 | Commands for game development workflows |
| commands-integration-sync | `workbuddy/official_experts/external_plugins/commands-integration-sync` | official expert | 13 | Commands for integrating with external services and syncing data |
| commands-miscellaneous | `workbuddy/official_experts/external_plugins/commands-miscellaneous` | official expert | 4 | General-purpose utility commands |
| commands-monitoring-observability | `workbuddy/official_experts/external_plugins/commands-monitoring-observability` | official expert | 3 | Commands for setting up monitoring and observability |
| commands-performance-optimization | `workbuddy/official_experts/external_plugins/commands-performance-optimization` | official expert | 7 | Commands for optimizing build, bundle size, and performance |
| commands-project-setup | `workbuddy/official_experts/external_plugins/commands-project-setup` | official expert | 7 | Commands for initializing and setting up new projects |
| commands-project-task-management | `workbuddy/official_experts/external_plugins/commands-project-task-management` | official expert | 18 | Commands for task management and project tracking |
| commands-security-audit | `workbuddy/official_experts/external_plugins/commands-security-audit` | official expert | 5 | Commands for security auditing and vulnerability scanning |
| commands-simulation-modeling | `workbuddy/official_experts/external_plugins/commands-simulation-modeling` | official expert | 9 | Commands for scenario simulation and decision modeling |
| commands-team-collaboration | `workbuddy/official_experts/external_plugins/commands-team-collaboration` | official expert | 13 | Commands for team workflows, PR reviews, and collaboration |
| commands-typescript-migration | `workbuddy/official_experts/external_plugins/commands-typescript-migration` | official expert | 2 | Commands for migrating JavaScript projects to TypeScript |
| commands-utilities-debugging | `workbuddy/official_experts/external_plugins/commands-utilities-debugging` | official expert | 15 | General debugging and utility commands |
| commands-version-control-git | `workbuddy/official_experts/external_plugins/commands-version-control-git` | official expert | 13 | Commands for Git operations, commits, and PRs |
| commands-workflow-orchestration | `workbuddy/official_experts/external_plugins/commands-workflow-orchestration` | official expert | 10 | Commands for orchestrating complex workflows |
| competitive-ads-extractor | `workbuddy/official_experts/external_plugins/competitive-ads-extractor` | official expert | 2 | 从广告库中提取并分析竞争对手的广告,以了解能够引起共鸣的营销信息和创意方法。 |
| comprehensive-review | `workbuddy/official_experts/external_plugins/comprehensive-review` | official expert | 6 | 多维度代码分析,覆盖架构、安全性和最佳实践 |
| conductor | `workbuddy/official_experts/external_plugins/conductor` | official expert | 29 | 上下文驱动开发插件，将 Claude Code 转变为项目管理工具，采用结构化工作流：上下文 → 规格与计划 → 实施 |
| content-marketing | `workbuddy/official_experts/external_plugins/content-marketing` | official expert | 3 | 内容营销策略、网络调研和信息综合处理的营销运营工具 |
| content-research-writer | `workbuddy/official_experts/external_plugins/content-research-writer` | official expert | 2 | 协助撰写高质量内容，包括研究调查、添加引用、改进开篇、提供逐节反馈等功能。 |
| context-management | `workbuddy/official_experts/external_plugins/context-management` | official expert | 4 | 上下文持久化、恢复和长期对话管理 |
| customer-sales-automation | `workbuddy/official_experts/external_plugins/customer-sales-automation` | official expert | 3 | 客户支持工作流自动化、销售管道管理、邮件营销活动及客户关系管理系统集成 |
| data-engineering | `workbuddy/official_experts/external_plugins/data-engineering` | official expert | 9 | ETL管道构建、数据仓库设计、批处理工作流和数据驱动的功能开发 |
| data-validation-suite | `workbuddy/official_experts/external_plugins/data-validation-suite` | official expert | 2 | 模式验证、数据质量监控、流式验证管道以及后端API的输入验证 |
| database-cloud-optimization | `workbuddy/official_experts/external_plugins/database-cloud-optimization` | official expert | 6 | 数据库查询优化、云成本优化和可扩展性改进 |
| database-design | `workbuddy/official_experts/external_plugins/database-design` | official expert | 4 | 生产系统的数据库架构设计、模式设计和 SQL 优化 |
| database-migrations | `workbuddy/official_experts/external_plugins/database-migrations` | official expert | 5 | 数据库迁移自动化、可观测性和跨数据库迁移策略 |
| debugging-toolkit | `workbuddy/official_experts/external_plugins/debugging-toolkit` | official expert | 4 | 交互式调试、开发者体验优化和智能调试工作流 |
| dependency-management | `workbuddy/official_experts/external_plugins/dependency-management` | official expert | 3 | 依赖审计、版本管理和安全漏洞扫描 |
| deployment-strategies | `workbuddy/official_experts/external_plugins/deployment-strategies` | official expert | 3 | 部署模式、回滚自动化和基础设施模板 |
| deployment-validation | `workbuddy/official_experts/external_plugins/deployment-validation` | official expert | 3 | 部署前检查、配置验证和部署就绪性评估 |
| developer-essentials | `workbuddy/official_experts/external_plugins/developer-essentials` | official expert | 13 | 包含 Git 工作流、SQL 优化、错误处理、代码审查、端到端测试、身份认证、调试和 Monorepo 管理的核心开发技能集 |
| developer-growth-analysis | `workbuddy/official_experts/external_plugins/developer-growth-analysis` | official expert | 2 | 分析你最近的 Claude Code 聊天历史，识别编码模式、发现开发能力缺口和需要改进的领域，从 HackerNews 精选相关学习资源，并自动将个性化成长报告发送到你的 Slack 私信。 |
| distributed-debugging | `workbuddy/official_experts/external_plugins/distributed-debugging` | official expert | 4 | 分布式系统追踪与微服务调试工具 |
| documentation-generation | `workbuddy/official_experts/external_plugins/documentation-generation` | official expert | 10 | OpenAPI规范生成、Mermaid图表创建、教程编写、API参考文档 |
| domain-name-brainstormer | `workbuddy/official_experts/external_plugins/domain-name-brainstormer` | official expert | 2 | 为项目生成创意域名并检查多个顶级域名（包括 .com、.io、.dev 和 .ai 等）的可用性 |
| error-debugging | `workbuddy/official_experts/external_plugins/error-debugging` | official expert | 6 | 错误分析、堆栈追踪调试和多智能体问题诊断 |
| error-diagnostics | `workbuddy/official_experts/external_plugins/error-diagnostics` | official expert | 6 | 错误追踪、根因分析及生产系统智能调试 |
| framework-migration | `workbuddy/official_experts/external_plugins/framework-migration` | official expert | 10 | 框架升级、迁移规划与架构转型工作流 |
| frontend-design-pro | `workbuddy/official_experts/external_plugins/frontend-design-pro` | official expert | 18 | Advanced frontend design plugin with interactive wizard, trend research, moodboard creation, color/typography selection, and browser-based inspiration analysis |
| frontend-mobile-development | `workbuddy/official_experts/external_plugins/frontend-mobile-development` | official expert | 8 | 跨平台前端 UI 开发和移动应用实现 |
| frontend-mobile-security | `workbuddy/official_experts/external_plugins/frontend-mobile-security` | official expert | 5 | 前端和移动开发专业安全代理。包括 XSS 漏洞扫描、安全编码实践、WebView 安全、移动认证，以及专注安全的现代 React/Next.js 开发。 |
| full-stack-orchestration | `workbuddy/official_experts/external_plugins/full-stack-orchestration` | official expert | 6 | 编排全栈功能开发，配备测试自动化、性能工程、安全审计和部署的专业代理。支持 CI/CD 流水线、GitOps 工作流、可观测性和渐进式交付策略。 |
| functional-programming | `workbuddy/official_experts/external_plugins/functional-programming` | official expert | 3 | 函数式编程语言专家代理，包括 Haskell 和 Elixir。提供高级类型系统、纯函数式设计、OTP 模式、并发、容错分布式系统和高可靠性软件开发。 |
| game-development | `workbuddy/official_experts/external_plugins/game-development` | official expert | 5 | Unity游戏开发与C#脚本编程，Minecraft服务器插件开发（支持Bukkit/Spigot API） |
| git-pr-workflows | `workbuddy/official_experts/external_plugins/git-pr-workflows` | official expert | 5 | Git 工作流自动化、拉取请求增强和团队入职流程 |
| hooks-automation | `workbuddy/official_experts/external_plugins/hooks-automation` | official expert | 4 | Automation Hooks - Event-driven automation hooks |
| hooks-development | `workbuddy/official_experts/external_plugins/hooks-development` | official expert | 5 | Development Hooks - Event-driven automation hooks |
| hooks-formatting | `workbuddy/official_experts/external_plugins/hooks-formatting` | official expert | 3 | Formatting Hooks - Event-driven automation hooks |
| hooks-git | `workbuddy/official_experts/external_plugins/hooks-git` | official expert | 4 | Git Hooks - Event-driven automation hooks |
| hooks-notifications | `workbuddy/official_experts/external_plugins/hooks-notifications` | official expert | 11 | Notification Hooks - Event-driven automation hooks |
| hooks-performance | `workbuddy/official_experts/external_plugins/hooks-performance` | official expert | 2 | Performance Hooks - Event-driven automation hooks |
| hooks-security | `workbuddy/official_experts/external_plugins/hooks-security` | official expert | 4 | Security Hooks - Event-driven automation hooks |
| hooks-testing | `workbuddy/official_experts/external_plugins/hooks-testing` | official expert | 3 | Testing Hooks - Event-driven automation hooks |
| hr-legal-compliance | `workbuddy/official_experts/external_plugins/hr-legal-compliance` | official expert | 5 | 人力资源政策文档、法律合规模板（GDPR/SOC2/HIPAA）、雇佣合同及监管文件 |
| image-enhancer | `workbuddy/official_experts/external_plugins/image-enhancer` | official expert | 2 | 通过提升分辨率、锐度和清晰度来改善图像和截图质量，适用于专业演示文稿和文档制作。 |
| incident-response | `workbuddy/official_experts/external_plugins/incident-response` | official expert | 8 | 生产事故管理、分级处理工作流和自动化事故解决方案 |
| internal-comms | `workbuddy/official_experts/external_plugins/internal-comms` | official expert | 7 | 帮助撰写内部沟通文档，包括三要素更新（进展/计划/问题）、公司通讯、常见问题解答、状态报告和项目更新，遵循公司特定格式规范。 |
| interview | `workbuddy/official_experts/external_plugins/interview` | official expert | 2 | Interview command for fleshing out big feature plans and specifications |
| invoice-organizer | `workbuddy/official_experts/external_plugins/invoice-organizer` | official expert | 2 | 发票整理工具 |
| javascript-typescript | `workbuddy/official_experts/external_plugins/javascript-typescript` | official expert | 8 | JavaScript 和 TypeScript 开发，支持 ES6+、Node.js、React 及现代 Web 框架 |
| julia-development | `workbuddy/official_experts/external_plugins/julia-development` | official expert | 2 | 现代 Julia 开发工具，支持 Julia 1.10+ 版本、包管理、科学计算、高性能数值代码和生产环境最佳实践 |
| jvm-languages | `workbuddy/official_experts/external_plugins/jvm-languages` | official expert | 4 | JVM 语言开发，包括 Java、Scala 和 C#，涵盖企业级模式和框架 |
| kubernetes-operations | `workbuddy/official_experts/external_plugins/kubernetes-operations` | official expert | 19 | Kubernetes 清单生成、网络配置、安全策略、可观测性配置、GitOps 工作流和自动扩缩容 |
| lead-research-assistant | `workbuddy/official_experts/external_plugins/lead-research-assistant` | official expert | 2 | 通过分析您的产品、搜索目标公司并提供可行的联系策略，识别和筛选高质量潜在客户。 |
| llm-application-dev | `workbuddy/official_experts/external_plugins/llm-application-dev` | official expert | 23 | 构建生产就绪的 LLM 应用、高级 RAG 系统和智能代理。包括向量搜索、多模态 AI、代理编排、提示工程和企业 AI 集成，以及全面的 AI 开发工作流。 |
| machine-learning-ops | `workbuddy/official_experts/external_plugins/machine-learning-ops` | official expert | 6 | 完整的 MLOps 工具包，配备 ML 工程、MLOps 基础设施和数据科学专业代理。构建生产 ML 流水线、实验跟踪、模型注册和自动化训练/部署工作流。 |
| mcp-builder | `workbuddy/official_experts/external_plugins/mcp-builder` | official expert | 11 | 指导创建高质量的 MCP（模型上下文协议）服务器,用于将外部 API 和服务与大语言模型集成,支持 Python 和 TypeScript 开发 |
| mcp-servers-docker | `workbuddy/official_experts/external_plugins/mcp-servers-docker` | official expert | 1 | Docker-based MCP servers from the official Docker MCP registry - includes 199+ verified servers |
| meeting-insights-analyzer | `workbuddy/official_experts/external_plugins/meeting-insights-analyzer` | official expert | 2 | 分析会议记录以揭示行为模式，包括冲突回避、发言比例、填充词使用和领导风格。 |
| multi-platform-apps | `workbuddy/official_experts/external_plugins/multi-platform-apps` | official expert | 8 | 跨平台应用开发,协调 Web、iOS、Android 和桌面端的实现 |
| nextjs-expert | `workbuddy/official_experts/external_plugins/nextjs-expert` | official expert | 27 | Next.js development expertise with skills for App Router, Server Components, Route Handlers, Server Actions, and authentication patterns |
| observability-monitoring | `workbuddy/official_experts/external_plugins/observability-monitoring` | official expert | 11 | 指标收集、日志基础设施、分布式追踪、SLO 实施和监控仪表板 |
| obsidian-skills | `workbuddy/official_experts/external_plugins/obsidian-skills` | official expert | 4 | Skills for working with Obsidian files - Markdown, Bases, and Canvas formats |
| payload | `workbuddy/official_experts/external_plugins/payload` | official expert | 14 | 为 Payload 开发提供全面指导的 Claude Code 技能，包含 TypeScript 模式、字段配置、钩子、访问控制和 API 示例。 |
| payment-processing | `workbuddy/official_experts/external_plugins/payment-processing` | official expert | 6 | 支付网关集成,包含 Stripe 和 PayPal,实现结账流程、订阅计费和 PCI 合规性 |
| performance-testing-review | `workbuddy/official_experts/external_plugins/performance-testing-review` | official expert | 5 | 性能分析、测试覆盖率审查和 AI 驱动的代码质量评估 |
| python-development | `workbuddy/official_experts/external_plugins/python-development` | official expert | 10 | 现代 Python 开发工具，支持 Python 3.12+、Django、FastAPI、异步编程模式及生产环境最佳实践 |
| quantitative-trading | `workbuddy/official_experts/external_plugins/quantitative-trading` | official expert | 5 | 量化分析、算法交易策略、金融建模、投资组合风险管理和回测 |
| raffle-winner-picker | `workbuddy/official_experts/external_plugins/raffle-winner-picker` | official expert | 2 | 从列表、电子表格或 Google Sheets 中随机选择获奖者，用于抽奖和比赛，采用密码学安全的随机性确保公平。 |
| repomix-commands | `workbuddy/official_experts/external_plugins/repomix-commands` | official expert | 3 | 用于快速执行 Repomix 操作的斜杠命令。通过 /pack-local 和 /pack-remote 等简单命令打包本地和远程代码仓库。 |
| repomix-explorer | `workbuddy/official_experts/external_plugins/repomix-explorer` | official expert | 4 | 在 CodeBuddy Code 中使用 Repomix 能力探索和分析仓库结构 |
| repomix-mcp | `workbuddy/official_experts/external_plugins/repomix-mcp` | official expert | 2 | Repomix MCP 服务器，用于 AI 驱动的代码库分析。打包本地/远程仓库，搜索输出内容，读取文件并内置安全扫描。这是在 Claude Code 中启用所有 Repomix 功能的基础插件。 |
| scientific-skills | `workbuddy/official_experts/external_plugins/scientific-skills` | official expert | 929 | K-Dense 团队创建的 139 个即用型 Claude 科学技能综合集合。将 Claude 转变为您的 AI 研究助手，能够执行跨生物学、化学和医学等领域的复杂多步骤科学工作流程。 |
| security-compliance | `workbuddy/official_experts/external_plugins/security-compliance` | official expert | 3 | SOC2、HIPAA 和 GDPR 合规性验证、密钥扫描、合规性检查清单和监管文档 |
| seo-analysis-monitoring | `workbuddy/official_experts/external_plugins/seo-analysis-monitoring` | official expert | 4 | SEO 内容新鲜度分析、关键词竞食检测和权威建设 |
| seo-content-creation | `workbuddy/official_experts/external_plugins/seo-content-creation` | official expert | 4 | SEO 内容创作、规划与质量审计工具，支持 E-E-A-T 优化 |
| seo-technical-optimization | `workbuddy/official_experts/external_plugins/seo-technical-optimization` | official expert | 5 | 技术SEO优化,包括元标签、关键词、结构和精选摘要 |
| shell-scripting | `workbuddy/official_experts/external_plugins/shell-scripting` | official expert | 6 | 生产级 Bash 脚本编写，包含防御性编程、POSIX 合规性和全面测试 |
| skill-creator | `workbuddy/official_experts/external_plugins/skill-creator` | official expert | 19 | 提供创建高效 Claude 技能的指南,通过专业知识、工作流程和工具集成来扩展 AI 助手的能力 |
| slack-gif-creator | `workbuddy/official_experts/external_plugins/slack-gif-creator` | official expert | 8 | 创建针对 Slack 优化的动画 GIF,提供文件大小约束验证和可组合的动画基元。 |
| startup-business-analyst | `workbuddy/official_experts/external_plugins/startup-business-analyst` | official expert | 13 | 面向初创企业的综合业务分析工具，提供市场规模分析（TAM/SAM/SOM）、财务建模、团队规划和战略研究功能 |
| superpowers | `workbuddy/official_experts/external_plugins/superpowers` | official expert | 48 | Claude Code 核心技能库：包含测试驱动开发、系统化调试、协作模式和经过验证的技术方法 |
| superpowers-chrome | `workbuddy/official_experts/external_plugins/superpowers-chrome` | official expert | 32 | 超轻量级 Chrome DevTools Protocol MCP 服务器，支持自动捕获。通过 Chrome DevTools Protocol 实现直接浏览器控制，零依赖，API 简单易用。 |
| systems-programming | `workbuddy/official_experts/external_plugins/systems-programming` | official expert | 9 | 使用 Rust、Go、C 和 C++ 进行系统编程，适用于性能关键和底层开发 |
| tailored-resume-generator | `workbuddy/official_experts/external_plugins/tailored-resume-generator` | official expert | 2 | 分析职位描述并生成量身定制的简历，突出相关经验、技能和成就，最大化面试机会。 |
| taskmaster | `workbuddy/official_experts/external_plugins/taskmaster` | official expert | 53 | Claude Code 插件 - 基于AI的任务管理系统，提供命令、代理和 MCP 集成 |
| tdd-workflows | `workbuddy/official_experts/external_plugins/tdd-workflows` | official expert | 7 | 测试驱动开发方法论,提供红-绿-重构循环和代码审查 |
| team-collaboration | `workbuddy/official_experts/external_plugins/team-collaboration` | official expert | 4 | 团队工作流、问题管理、站会自动化和开发者体验优化 |
| template-skill | `workbuddy/official_experts/external_plugins/template-skill` | official expert | 2 | 一个演示如何创建新 Claude 技能的结构和格式的模板技能 |
| theme-factory | `workbuddy/official_experts/external_plugins/theme-factory` | official expert | 14 | 为演示文稿、文档、报告和 HTML 落地页等制品应用专业的字体和配色主题，提供 10 套预设主题方案。 |
| ui-ux-pro-max | `workbuddy/official_experts/external_plugins/ui-ux-pro-max-skill` | design | 31 | AI-powered UI/UX design system generator with 100+ industry-specific reasoning rules, 57 UI styles, 95+ color palettes, 56 font pairings, and intelligent design recommendations across 12 tech stacks. |
| unit-testing | `workbuddy/official_experts/external_plugins/unit-testing` | official expert | 4 | Python 和 JavaScript 的单元测试与集成测试自动化，支持调试功能 |
| video-downloader | `workbuddy/official_experts/external_plugins/video-downloader` | official expert | 3 | 从 YouTube 和其他平台下载视频，支持离线观看、编辑或存档，提供多种格式和画质选项。 |
| web-scripting | `workbuddy/official_experts/external_plugins/web-scripting` | official expert | 3 | 使用 PHP 和 Ruby 进行 Web 脚本开发，支持 Web 应用、CMS 开发和后端服务 |
| webapp-testing | `workbuddy/official_experts/external_plugins/webapp-testing` | official expert | 7 | 使用 Playwright 测试本地 Web 应用，支持验证前端功能、调试 UI 行为和捕获浏览器截图。 |

### Official Experts / Plugins

| Name | Directory | Category | Files | Description |
| --- | --- | --- | ---: | --- |
| agent-browser | `workbuddy/official_experts/plugins/agent-browser` | official expert | 8 | 基于 Vercel agent-browser CLI 的浏览器自动化插件。首次使用时自动安装，让 CodeBuddy 能够进行网页交互、截图、表单填写等浏览器操作。 |
| agent-sdk-dev | `workbuddy/official_experts/plugins/agent-sdk-dev` | official expert | 5 | CodeBuddy Agent SDK Development Plugin - Create and verify CodeBuddy Agent SDK applications |
| agent-team-agile-workflow | `workbuddy/official_experts/plugins/agent-team-agile-workflow` | official expert | 9 | 完整的 BMAD 敏捷工作流插件，包含角色化代理（PO、架构师、SM、开发、QA）和交互式审批流程 |
| algorithmic-art | `workbuddy/official_experts/plugins/algorithmic-art` | official expert | 5 | 使用 p5.js 创建算法艺术，支持种子随机性和交互式参数探索。适用于生成艺术、流场、粒子系统等代码艺术创作。 |
| atuin | `workbuddy/official_experts/plugins/atuin` | official expert | 5 | 自动拦截 AI 的高危操作，自动阻止 AI 使用有漏洞的组件。腾讯玄武实验室出品。让 AI 编程更安全。 |
| chainguard | `workbuddy/official_experts/plugins/chainguard` | official expert | 4 | AI 编程供应链安全防护，自动拦截依赖安装操作进行安全审计，检测漏洞组件、License 合规及 SBOM 白名单。 |
| clangd-lsp | `workbuddy/official_experts/plugins/clangd-lsp` | official expert | 4 | C/C++ 语言服务器(clangd)，提供代码智能提示 |
| cloudbase | `workbuddy/official_experts/plugins/cloudbase` | official expert | 44 | CloudBase AI 开发插件，提供 Web、小程序、云函数、CloudRun、数据库（NoSQL/MySQL）、云存储、AI 模型、UI 设计等全栈开发能力。 |
| code-simplifier | `workbuddy/official_experts/plugins/code-simplifier` | official expert | 2 | 专注于简化代码以提升清晰度、一致性和可维护性的智能代理,在保留完整功能的前提下优化代码结构。主要关注最近修改的代码。 |
| codebuddy-md-management | `workbuddy/official_experts/plugins/codebuddy-md-management` | official expert | 9 | 用于维护和改进 CODEBUDDY.md 文件的工具 - 审核质量、捕获会话学习内容，并保持项目记忆最新。 |
| commit-commands | `workbuddy/official_experts/plugins/commit-commands` | official expert | 6 | Git 提交工作流命令，包括提交、推送和创建拉取请求 |
| context7 | `workbuddy/official_experts/plugins/context7` | official expert | 2 | Upstash Context7 MCP 服务器，用于查找最新文档。可直接从源代码仓库拉取特定版本的文档和代码示例到 LLM 上下文中。 |
| csharp-lsp | `workbuddy/official_experts/plugins/csharp-lsp` | official expert | 4 | C# 语言服务器，提供代码智能提示和诊断 |
| development-essentials | `workbuddy/official_experts/plugins/development-essentials` | official expert | 18 | 核心开发命令集，包含编码、调试、测试、优化和文档生成等常用开发工作流 |
| doc-coauthoring | `workbuddy/official_experts/plugins/doc-coauthoring` | official expert | 2 | 引导用户通过结构化工作流协作撰写文档。适用于编写文档、提案、技术规格、决策文档等结构化内容，帮助高效传递上下文、迭代优化内容并验证文档的可读性。 |
| docx | `workbuddy/official_experts/plugins/docx` | official expert | 62 | 全面的 Word 文档创建、编辑和分析工具，支持修订跟踪、评论、格式保留和文本提取。用于处理专业 Word 文档(.docx) |
| feature-dev | `workbuddy/official_experts/plugins/feature-dev` | official expert | 7 | 全面的功能开发工作流，配备专门的智能体用于代码库探索、架构设计和质量审查 |
| find-skills | `workbuddy/official_experts/plugins/find-skills` | official expert | 2 | 帮助用户发现和安装 AI Agent 技能，支持从 Vercel Skills 和 ClawHub 两个技能仓库搜索和安装 |
| firebase | `workbuddy/official_experts/plugins/firebase` | official expert | 2 | Google Firebase MCP 集成。管理 Firestore 数据库、身份验证、云函数、托管服务和存储。直接从开发工作流中构建和管理 Firebase 后端。 |
| frontend-design | `workbuddy/official_experts/plugins/frontend-design` | official expert | 3 | 创建独特的生产级前端界面,具有高设计质量。生成富有创意、精致的代码,避免千篇一律的AI审美。 |
| github | `workbuddy/official_experts/plugins/github` | official expert | 2 | 官方 GitHub MCP 服务器，用于仓库管理。可直接在 Claude Code 中创建议题、管理拉取请求、审查代码、搜索仓库以及调用 GitHub 完整 API。 |
| gitlab | `workbuddy/official_experts/plugins/gitlab` | official expert | 2 | GitLab DevOps 平台集成。管理代码仓库、合并请求、CI/CD 流水线、问题和 Wiki。全面访问 GitLab 的 DevOps 生命周期工具。 |
| godot-mcp | `workbuddy/official_experts/plugins/godot-mcp` | official expert | 168 | Godot 4 MCP 集成插件，通过 AI 对话直接操作 Godot Editor。支持场景管理、节点操作、脚本编辑、项目运行等功能。 |
| gopls-lsp | `workbuddy/official_experts/plugins/gopls-lsp` | official expert | 4 | Go 语言服务器，提供代码智能提示和重构功能 |
| hookify | `workbuddy/official_experts/plugins/hookify` | official expert | 24 | 通过分析对话模式或显式指令轻松创建自定义钩子，防止不希望的行为。使用简单的 Markdown 文件定义规则。 |
| hot-skills | `workbuddy/official_experts/plugins/hot-skills` | productivity | 72 | 精选热门 AI Agent 技能合集，汇集社区高下载量技能于一处。 |
| jdtls-lsp | `workbuddy/official_experts/plugins/jdtls-lsp` | official expert | 4 | Java 语言服务器（Eclipse JDT.LS），提供代码智能和重构功能 |
| lexiang-knowledge | `workbuddy/official_experts/plugins/lexiang-knowledge-plugins` | official expert | 25 | 乐享知识库, 企业协同知识库，提供获取文档内容与元数据、搜索文档内容、查询知识库与目录结构、创建/编辑/移动文档、管理标签与评论、上传文件及维护附件等知识库操作能力。 |
| lua-lsp | `workbuddy/official_experts/plugins/lua-lsp` | official expert | 4 | 为 Lua 语言提供代码智能和诊断的语言服务器 |
| lucide-icons | `workbuddy/official_experts/plugins/lucide-icons` | official expert | 9 | 搜索、下载和自定义 Lucide 图标（1000+ 精美 SVG 图标），支持生成 React 组件 |
| magicai-hub | `workbuddy/official_experts/plugins/magicai-hub` | 游戏开发 | 21 | Godot 4.x 游戏开发 AI 技能工具包。提供 GDScript 代码生成、数据驱动配置、场景/资源文件格式解析、资产路径修复、无头验证、工具函数库等专业能力，帮助 AI 更高效地协助 Godot 项目开发。 |
| oh-my-codebuddy | `workbuddy/official_experts/plugins/oh-my-codebuddy` | official expert | 61 | 完整的 OMC (Oh My CodeBuddy) 插件，包含 agents、commands、skills、hooks、tools 和 MCP servers。提供多代理编排、深度研究、代码分析等功能。 |
| pdf | `workbuddy/official_experts/plugins/pdf` | official expert | 13 | 全面的 PDF 处理工具包，支持提取文本和表格、创建新 PDF、合并/拆分文档、表单填写、加密解密、OCR 扫描等功能 |
| php-lsp | `workbuddy/official_experts/plugins/php-lsp` | official expert | 4 | PHP 语言服务器（Intelephense），提供代码智能和诊断 |
| playwright-cli | `workbuddy/official_experts/plugins/playwright-cli` | testing | 15 | Automates browser interactions for web testing, form filling, screenshots, and data extraction. Use when the user needs to navigate websites, interact with web pages, fill forms, take screenshots, test web application... |
| plugin-dev | `workbuddy/official_experts/plugins/plugin-dev` | official expert | 61 | 用于开发 CodeBuddy Code 插件的综合工具包。包含 7 个专家技能,涵盖钩子、MCP 集成、命令、代理和最佳实践。支持 AI 辅助的插件创建和验证。 |
| plugin-finder | `workbuddy/official_experts/plugins/plugin-finder` | official expert | 21 | 智能插件发现和管理助手 - 支持智能搜索、多插件并行对比、多插件协同工作流（sequence-run）、插件信息详解、许愿新插件等功能 |
| ppt-writer | `workbuddy/official_experts/plugins/ppt-writer` | official expert | 6 | AI驱动的PPT创作助手，支持智能内容生成、多格式导出和专业模板 |
| pptx | `workbuddy/official_experts/plugins/pptx` | official expert | 60 | PowerPoint 演示文稿创建、编辑和分析技能。支持创建新演示文稿、修改内容、处理布局、添加注释或演讲者备注等操作 |
| pr-review-toolkit | `workbuddy/official_experts/plugins/pr-review-toolkit` | official expert | 10 | 全面的 PR 审查代理工具集,专注于代码注释、测试覆盖、错误处理、类型设计、代码质量和代码简化 |
| pyright-lsp | `workbuddy/official_experts/plugins/pyright-lsp` | official expert | 4 | Python 语言服务器（Pyright），提供类型检查和代码智能提示 |
| ralph-loop | `workbuddy/official_experts/plugins/ralph-loop` | official expert | 9 | 用于迭代开发的交互式自引用AI循环，实现Ralph Wiggum技术。Claude重复执行同一任务，查看之前的工作，直到完成为止。 |
| requirements-driven-workflow | `workbuddy/official_experts/plugins/requirements-driven-workflow` | official expert | 6 | 需求驱动开发工作流，包含 90% 质量门控的实用功能实现流程 |
| rust-analyzer-lsp | `workbuddy/official_experts/plugins/rust-analyzer-lsp` | official expert | 4 | Rust 语言服务器，提供代码智能和分析功能 |
| security-guidance | `workbuddy/official_experts/plugins/security-guidance` | official expert | 3 | 安全提醒钩子，在编辑文件时警告潜在的安全问题，包括命令注入、XSS 和不安全的代码模式 |
| security-rules | `workbuddy/official_experts/plugins/security-rules` | official expert | 4 | 腾讯云鼎实验室出品，将安全专家经验融入代码生成过程，实时对常见漏洞的防护规则和安全函数约束，让 AI 直接生成安全代码，从源头保障代码安全质量。 |
| security-scan | `workbuddy/official_experts/plugins/security-scan` | security | 93 | 腾讯云鼎实验室出品，专业的代码安全审计插件。支持 Fast（极速扫描）、Light（快速扫描）和 Deep（深度扫描）三种模式。基于 SQLite 语义索引 + 5 Agent 专业化架构，5维深度验证保障结果可信。全链路 --auto 无人值守模式 + POC 多维差异验证 + 安全门禁与 Git Hook 自动化。 |
| serena | `workbuddy/official_experts/plugins/serena` | official expert | 2 | 语义代码分析 MCP 服务器，通过语言服务器协议集成提供智能代码理解、重构建议和代码库导航功能。 |
| skills-security-check | `workbuddy/official_experts/plugins/skills-security-check` | official expert | 2 | 腾讯云鼎实验室出品，Skill安全审查工具。本skill用于对用户指定的skill.md文件、及其配套的文档、程序、脚本等做安全审查，确保引用安全 |
| supabase | `workbuddy/official_experts/plugins/supabase` | official expert | 2 | Supabase MCP 集成，用于数据库操作、身份验证、存储和实时订阅。管理您的 Supabase 项目，运行 SQL 查询，并直接与后端交互。 |
| swift-lsp | `workbuddy/official_experts/plugins/swift-lsp` | official expert | 4 | Swift 语言服务器（SourceKit-LSP），提供代码智能支持 |
| testbuddy | `workbuddy/official_experts/plugins/testbuddy` | 测试工具 | 55 | 文本测试用例生成插件。主要用于文本测试用例生成、文本测试用例框架生成、脑图用例生成、召回、需求分析等文本测试用例生成 |
| tmap-lbs-plugin | `workbuddy/official_experts/plugins/tmap-lbs-plugin` | 开发工具 | 225 | 腾讯地图位置服务开发插件，提供 JavaScript GL 地图开发指南和 Web 服务 API（POI搜索、路径规划、旅游规划、轨迹可视化等）能力。 |
| typescript-lsp | `workbuddy/official_experts/plugins/typescript-lsp` | official expert | 4 | TypeScript/JavaScript 语言服务器，提供增强的代码智能功能 |
| web-artifacts-builder | `workbuddy/official_experts/plugins/web-artifacts-builder` | official expert | 6 | 使用现代前端技术（React、Tailwind CSS、shadcn/ui）创建复杂多组件 HTML 工件的工具套件。适用于需要状态管理、路由或 shadcn/ui 组件的复杂工件。 |
| weixin-minigame-helper | `workbuddy/official_experts/plugins/weixin-minigame-helper` | development | 9 | 微信小游戏AI调试、预览、运行、真机测试上传发布微信小游戏 |
| xlsx | `workbuddy/official_experts/plugins/xlsx` | official expert | 55 | 全面的电子表格创建、编辑和分析工具，支持公式、格式化、数据分析和可视化。适用于 .xlsx、.xlsm、.csv、.tsv 等表格文件的处理 |

### CB Teams Experts

| Name | Directory | Category | Files | Description |
| --- | --- | --- | ---: | --- |
| a-share-analysis | `workbuddy/cb_teams_experts/plugins/a-share-analysis` | finance | 28 | A股投资分析技能集，覆盖宏观研究、市场结构、个股深度、行业比较、资金行为、风险管理等 21 个专业分析 skill 和 6 个编排 agent。 |
| agent-sdk-dev | `workbuddy/cb_teams_experts/plugins/agent-sdk-dev` | 技术开发工具 | 5 | CodeBuddy Agent SDK 开发 |
| ai-hedge-fund | `workbuddy/cb_teams_experts/plugins/ai-hedge-fund` | team expert | 23 | AI 对冲基金投资分析系统：19位投资大师并行分析 + 风险管理 + 投资组合决策的全流程投资分析。涵盖巴菲特、芒格、林奇、伯里、塔勒布、伍德、格雷厄姆等13位传奇投资哲学家 + 6位专业分析师，通过信号聚合投票输出 BUY/SELL/HOLD 建议。数据源使用 NeoData 金融数据服务。 |
| ardot-design-generator | `workbuddy/cb_teams_experts/plugins/ardot-design-generator` | team expert | 30 | Ardot设计工具：在Ardot中生成高质量设计稿，移动端UI，网站页面，web应用，幻灯片等设计稿 |
| codebuddy-chat-web | `workbuddy/cb_teams_experts/plugins/codebuddy-chat-web` | 技术开发工具 | 42 | Web 聊天应用 |
| data | `workbuddy/cb_teams_experts/plugins/data` | 金融和商业分析 | 16 | 数据分析平台 |
| data-analysis | `workbuddy/cb_teams_experts/plugins/data-analysis` | 金融和商业分析 | 58 | Excel/数据分析 |
| deep-research | `workbuddy/cb_teams_experts/plugins/deep-research` | 金融和商业分析 | 6 | 深度研究框架 |
| design-to-code | `workbuddy/cb_teams_experts/plugins/design-to-code` | 技术开发工具 | 15 | Figma 设计转代码 |
| dockerfile-gen | `workbuddy/cb_teams_experts/plugins/dockerfile-gen` | 技术开发工具 | 2 | Dockerfile 生成 |
| document-skills | `workbuddy/cb_teams_experts/plugins/document-skills` | 文件处理和通用工具 | 253 | 文档处理 |
| equity-research | `workbuddy/cb_teams_experts/plugins/equity-research` | 金融和商业分析 | 22 | 股票研究 |
| executing-marketing-campaigns | `workbuddy/cb_teams_experts/plugins/executing-marketing-campaigns` | 营销和内部运营 | 15 | 营销活动管理 |
| finance | `workbuddy/cb_teams_experts/plugins/finance` | 金融和商业分析 | 13 | 财务与会计 |
| financial-analysis | `workbuddy/cb_teams_experts/plugins/financial-analysis` | 金融和商业分析 | 31 | 财务建模（DCF、LBO、Comps） |
| 专业高考顾问 | `workbuddy/cb_teams_experts/plugins/gaokao-advisor` | 12-IndustryConsultant | 41 | 辅助检索高考知识库并调用分数线、一分一段能力，整理带来源的真题、高校专业和志愿参考；同时提供全流程志愿填报引导，产出可转发的腾讯文档志愿报告 |
| general-skills | `workbuddy/cb_teams_experts/plugins/general-skills` | 文件处理和通用工具 | 40 | 通用技能集 |
| internal-comms | `workbuddy/cb_teams_experts/plugins/internal-comms` | 营销和内部运营 | 7 | 内部沟通 |
| investment-banking | `workbuddy/cb_teams_experts/plugins/investment-banking` | 金融和商业分析 | 16 | 投资银行（M&A、融资） |
| lseg | `workbuddy/cb_teams_experts/plugins/lseg` | 金融和商业分析 | 10 | 资本市场分析 |
| modern-webapp | `workbuddy/cb_teams_experts/plugins/modern-webapp` | 技术开发工具 | 118 | 现代 Web 应用框架 |
| ppt-implement | `workbuddy/cb_teams_experts/plugins/ppt-implement` | 文件处理和通用工具 | 718 | PowerPoint 实现 |
| private-equity | `workbuddy/cb_teams_experts/plugins/private-equity` | 金融和商业分析 | 11 | 私募股权投资 |
| product-management | `workbuddy/cb_teams_experts/plugins/product-management` | 营销和内部运营 | 13 | 产品管理 |
| remotion-video-generator | `workbuddy/cb_teams_experts/plugins/remotion-video-generator` | 文件处理和通用工具 | 77 | 视频生成 |
| sheetagent | `workbuddy/cb_teams_experts/plugins/sheetagent` | team expert | 28 | 由腾讯文档团队出品的电子表格智能助手，支持通过自然语言创建、查询与编辑 xlsx 表格 |
| skill-creator | `workbuddy/cb_teams_experts/plugins/skill-creator` | 文件处理和通用工具 | 6 | 自定义技能创建 |
| spglobal | `workbuddy/cb_teams_experts/plugins/spglobal` | 金融和商业分析 | 14 | 公司分析和财报 |
| trading-agent | `workbuddy/cb_teams_experts/plugins/trading-agent` | 金融和商业分析 | 15 | 投资分析和交易决策 |
| wealth-management | `workbuddy/cb_teams_experts/plugins/wealth-management` | 金融和商业分析 | 8 | 财务规划和投资组合 |
| webapp-testing | `workbuddy/cb_teams_experts/plugins/webapp-testing` | 技术开发工具 | 3 | Web 应用测试 |

### Skills

| Name | Directory | Category | Files | Description |
| --- | --- | --- | ---: | --- |
| aihot | `workbuddy/skills/aihot__skillhub` | skill | 3 | AI HOT (aihot.virxact.com) 中文 AI 资讯查询 Skill。当用户想知道"今天 AI 圈有什么"、"AI 日报"、"AI HOT"、"AI 资讯"、"AI 热点"、"最近 AI"、"OpenAI/Anthropic/Google 最近发布了什么"、"AI hot today"、"AI news today"、"看一下 AI 行业动态"、"今天有什么大模型发布"、"昨天 AI 圈"、"看下精选条目"、"A... |
| arxiv-reader | `workbuddy/skills/arxiv-reader` | skill | 42 | 利用python，指定某个arxiv_id/url， 基于 LLM Agent 对这篇arxiv论文进行分类与深度阅读，直接print打印阅读笔记 |
| arxiv-watcher | `workbuddy/skills/arxiv-watcher` | skill | 4 | Search and summarize papers from ArXiv. Use when the user asks for the latest research, specific topics on ArXiv, or a daily summary of AI papers. |
| ctrip-wendao | `workbuddy/skills/ctrip-wendao` | skill | 4 | 当用户发起任意旅行相关问询时，包含但不限于：预订酒店、机票查询、火车票查询、景点推荐、寻找当地特色玩乐、目的地查询、行程规划、美食住宿攻略、签证、查询旅游攻略、获取旅行建议等场景，自动触发此技能。当用户需要操作携程时使用此skill。 |
| deep-research | `workbuddy/skills/deep-research` | skill | 21 | Structured deep research workflow with human-in-the-loop control. Use /research to generate research outline, /research-deep for parallel web search across items, /research-report to compile markdown reports. Supports... |
| humanizer | `workbuddy/skills/humanizer` | skill | 3 | Remove signs of AI-generated writing from text. Use when editing or reviewing text to make it sound more natural and human-written. Detects and fixes patterns including: inflated symbolism, promotional language, super... |
| khazix-writer | `workbuddy/skills/khazix-writer` | skill | 4 | \|- |
| paper-quick-reader | `workbuddy/skills/paper-quick-reader` | skill | 31 | AI 论文速读 Skill：三档深度（裸读 / 引导 / 精读）+ 页码级 Provenance 防幻觉 + 多篇对比。 触发词：论文速读、读这篇论文、抓核心观点、论文对比、多篇对比、与我研究方向的关联、 第几页提到 X、这篇论文的数据集怎么构造的、论文精读、 paper summary、summarize this paper、compare these papers、literature skim、extract method... |
| prompt-engineering-expert | `workbuddy/skills/prompt-engineering-expert` | skill | 12 | Advanced expert in prompt engineering, custom instructions design, and prompt optimization for AI agents |
| skillhub-daily | `workbuddy/skills/skillhub-daily` | skill | 13 | 'SkillHub 每日推荐 - 扫描 skillhub.cn 全站 Top100 + 7 大分类各 Top20（共 240 个 Skill）， |
| tencent-yuanbao-standard-search | `workbuddy/skills/tencent-yuanbao-standard-search` | skill | 4 | Search the web using TencentCloud Web Search API (WSA). Prioritize using it when you need to retrieve network information. |
| wechat-article-pro | `workbuddy/skills/wechat-article-pro` | skill | 2 | 微信公众号文章发布专业版。功能：1)联网搜索热点信息 2)AI生成微信公众号封面图 3)撰写3000-5000字深度文章 4)使用公众号AI配图功能自动生成并上传封面 5)参考刘润公众号风格写作 6)自动排版 7)不加话题标签 |

## 最近变更

| Date | Change Log | Summary |
| --- | --- | --- |
| 2026-08-05-230159 | [2026-08-05-230159](workbuddy/change-logs/2026-08-05-230159.md) | WorkBuddy 本次同步新增 8434 个文件、修改 0 个文件、删除 0 个文件。 新增条目：cb_teams_experts/a-share-analysis, cb_teams_experts/agent-sdk-dev, cb_teams_experts/ai-hedge-fund, cb_teams_experts/ardot-desig... |
