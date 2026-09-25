# WorkBuddy Skills And Experts

本文件由 `scripts/sync_platform.py --platform workbuddy` 自动生成，整理 `workbuddy/` 下同步的技能、专家团和插件索引。

## 同步概览

- 平台目录：`workbuddy/`
- 定时任务：`WorkbuddySkillsDailySync`，每天 18:00 运行
- 当前索引条目数：633
- 当前索引文件数：17591
- 最近变更：[2026-09-25-085343](workbuddy/change-logs/2026-09-25-085343.md) - WorkBuddy 本次同步新增 593 个文件、修改 108 个文件、删除 9 个文件。 新增条目：connectors/marketplace/connectors/chainlon-geo-mcp, connectors/marketplace/connectors/duoguan-course, connectors/marketplace/c...

## 数据来源

- `experts` <= `/mnt/c/Users/15805/.workbuddy/plugins/marketplaces/experts/plugins`
- `official_experts/external_plugins` <= `/mnt/c/Users/15805/.workbuddy/plugins/marketplaces/codebuddy-plugins-official/external_plugins`
- `official_experts/plugins` <= `/mnt/c/Users/15805/.workbuddy/plugins/marketplaces/codebuddy-plugins-official/plugins`
- `cb_teams_experts/plugins` <= `/mnt/c/Users/15805/.workbuddy/plugins/marketplaces/cb_teams_marketplace/plugins`
- `cb_teams_experts/plugins_analysis_company_analysis.md` <= `/mnt/c/Users/15805/.workbuddy/plugins/marketplaces/cb_teams_marketplace/plugins_analysis_company_analysis.md`
- `skills` <= `/mnt/c/Users/15805/.workbuddy/skills`
- `connectors/marketplace` <= `/mnt/c/Users/15805/.workbuddy/connectors-marketplace`
- `connectors/default/mcp.json` <= `/mnt/c/Users/15805/.workbuddy/connectors/default/mcp.json`

## 导航文件

各同步目录根部的 `SUMMARY.md` 提供按用途分组的场景导航，便于快速定位：

- [Marketplace Experts](workbuddy/experts/SUMMARY.md) — `experts/` 功能导航
- [Official Experts / External Plugins](workbuddy/official_experts/external_plugins/SUMMARY.md) — `official_experts/external_plugins/` 功能导航
- [Official Experts / Plugins](workbuddy/official_experts/plugins/SUMMARY.md) — `official_experts/plugins/` 功能导航
- [CB Teams Experts](workbuddy/cb_teams_experts/plugins/SUMMARY.md) — `cb_teams_experts/plugins/` 功能导航
- [Skills](workbuddy/skills/SUMMARY.md) — `skills/` 功能导航
- [Connectors / Marketplace](workbuddy/connectors/marketplace/SUMMARY.md) — `connectors/marketplace/` 功能导航

## 分类索引

### Marketplace Experts

| Name | Directory | Category | Files | Description |
| --- | --- | --- | ---: | --- |
| A股研究团队 | `workbuddy/experts/a-share-analysis` | 08-FinanceInvestment | 38 | 8位研究专家支持多步骤工作流编排，覆盖宏观策略、盘面解读、个股深度、估值定价、产业链映射、资金追踪、风险诊断 |
| AI CMO | `workbuddy/experts/ai-cmo` | 06-ContentCreative | 16 | 3 位专家接力协作，跑通账号定位、选题脚本、涨粉变现全链路，含数据复盘与反哺选题的闭环。 |
| 内容创作专家团 | `workbuddy/experts/ai-content-creator-team` | 06-ContentCreative | 25 | AI驱动的多模态内容生产团队，从创意策划到成品交付全覆盖，涵盖品牌定位、情绪板、广告方向、文案创作、视频生成、图片设计、精修合成和素材改编。 |
| 智数分析专家团 | `workbuddy/experts/ai-data-copilot` | 04-DataAI | 22 | 6人AI数据分析团队，擅长自然语言转SQL、Python建模、RAG知识问答、仪表盘可视化与报告生成 |
| AI大模型专家团 | `workbuddy/experts/ai-expert-studio` | 06-ContentCreative | 36 | 一个人搞不定的创意全案？5 人专家团从策划到成片成稿，一站式交付，省心省力不踩坑。 |
| AICoding 架构专家团 | `workbuddy/experts/aicoding-architecture-expert-team` | 02-Engineering | 289 | 面向复杂系统架构设计，协同完成资料摄入、调研、业务、系统、部署、安全与用户故事全流程交付。 |
| 组小学 | `workbuddy/experts/antibody-structure-opt-team` | 04-DataAI | 15 | 专注抗体药物设计与结构优选，协同IgGM、Protenix或Boltz完成候选生成、结构预测与排序。 |
| 财报研析团 | `workbuddy/experts/bank-retail-analyst` | 08-FinanceInvestment | 147 | 六成员财报分析专家团：自动下载年报、提取零售数据，做同业对标与战略治理穿透分析，一键交付三份专业报告。 |
| 法大大·睿契提供的破产业务专家 | `workbuddy/experts/bankruptcy-business-expert` | 11-SecurityCompliance | 407 | 【法大大·睿契】面向破产管理人和破产律师，覆盖清算、重整与和解全流程的债权审查、资产追收、分配方案与重整计划编制。 |
| 相信光么 | `workbuddy/experts/believe-in-light` | 08-FinanceInvestment | 26 | 光模块产业链信号监控专家团。主理人 + 6位成员Agent 三端采集信号，因果验证+权重校准，三层嵌套输出景气度评级。 |
| 汽车行业内容创作专家团 | `workbuddy/experts/content-creation-expert-prod` | 06-ContentCreative | 31 | 汽车行业垂类图文创作团队，5 人协作完成选题、撰写、智能配图与质检，一键交付懂车帝、小红书等风格图文 |
| 全域内容分发专家团 | `workbuddy/experts/content-distribution-team` | 06-ContentCreative | 36 | 一站式多平台内容分发方案，覆盖12+全球社交媒体平台，提供发布规则适配、排期管理、批量发布编排和跨平台数据分析能力 |
| 内容变现商业化专家团 | `workbuddy/experts/content-monetization-team` | 05-MarketingGrowth | 19 | 5人专家团协作覆盖CPS带货分佣、CPE/CPM效果广告、创作者-品牌交易撮合与收益分析，助力内容创作者和品牌方实现商业化价值最大化 |
| 腾讯电子签合同法务专家 | `workbuddy/experts/contract-legal-expert` | 13-TencentZone | 17 | 腾讯电子签合同法务专家擅长合同起草、审查、对比、法规检索，能在线发起签署，劳动/租赁/买卖全场景覆盖 |
| 对公贷前尽调专家团 | `workbuddy/experts/credit-due-diligence-report` | 08-FinanceInvestment | 24 | 对公信贷尽调专家团：信息核查、财务分析、报告撰写、合规校验四角色协作，产出尽调报告，行内数据待补充。 |
| 法大大·睿契提供的刑事辩护专家 | `workbuddy/experts/criminal-defense-expert` | 11-SecurityCompliance | 663 | 【法大大·睿契】面向刑辩律师，按阶段调度材料分析、辩护研究、文书起草、庭审质证与成果校验，覆盖侦查至二审全流程。 |
| 出海海 | `workbuddy/experts/cross-border-ecommerce-expert` | 05-MarketingGrowth | 10 | 精通亚马逊Shopify等国际电商平台，助力品牌出海全球 |
| 法大大·睿契提供的跨境法律专家 | `workbuddy/experts/cross-border-legal-expert` | 11-SecurityCompliance | 346 | 【法大大·睿契】面向涉外律师与出海/外资企业法务的专家团：外国法与多法域比较、ECLI/CELEX 精确引用核验、境外许可牌照、英文/双语合同审查与真实红线、ODI/FDI 与跨境并购架构、制裁与出口管制筛查、数据出境合规及独立交付校验；主 Agent 快速沟通入口，按风险分级组队。 |
| 客户销售增长专家团 | `workbuddy/experts/customer-sales-intelligence-team` | 07-SalesCommerce | 28 | 协同完成客户评分、赛道与场景分析、销售话术、客户匹配和分阶段攻坚，输出可直接执行的客户增长方案。 |
| 文档达 | `workbuddy/experts/document-generation-expert` | 10-ProjectQuality | 85 | 自动化生成各类业务文档，大幅提升文档创建效率 |
| 科研专家团 | `workbuddy/experts/empirical-research-team` | 04-DataAI | 35 | 覆盖实证研究全流程的专家团：因果推断、稳健性检验、出版级表图与降AIGC，高效完成可复现学术论文 |
| 法大大·睿契提供的劳动人事专家团 | `workbuddy/experts/employment-legal-advisor` | 11-SecurityCompliance | 71 | 【法大大·睿契】覆盖劳动争议诊断、用工合规体检、补偿赔偿测算、劳动文书起草与成果核验的中国大陆劳动用工法律专家团队。 |
| 工程保障团队 | `workbuddy/experts/engineering-assurance-team` | 02-Engineering | 16 | 由工程总监领导的 5 人工程专家团队：代码审查师（安全/性能/正确性）、架构师（系统设计/ADR）、SRE 工程师（事故响应/部署）、测试专家（测试策略/覆盖率）和技术文档师（文档/Runbook）。处理从代码审查到事故响应的复杂工程工作流。 |
| 企业法务专家团 | `workbuddy/experts/enterprise-legal-team` | 11-SecurityCompliance | 211 | 面向企业法务的多角色专家团，覆盖合同、交易、隐私、产品、监管、AI 治理、雇佣与知识产权分诊。 |
| equity-research | `workbuddy/experts/equity-research` | agent | 35 | Comprehensive equity research toolkit: earnings analysis, initiating coverage, DCF/comps valuation, long-short pitches, investment memos, event-driven analysis, portfolio risk management, and full research workflows |
| ETF投资顾问专家团 | `workbuddy/experts/etf-advisor-team` | 08-FinanceInvestment | 144 | 自上而下定配置中枢与再平衡纪律，自下而上诊断持仓、择优替换工具，宏观技术风控协同输出多角度调仓分析参考。 |
| 福帮手 | `workbuddy/experts/fbsir-eight-seat-board` | 12-IndustryConsultant | 82 | 福帮手经营决策独立审议专家团｜按案组建必要席位，独立判断、交叉质询、保留异议，交付可追溯行动备忘录 |
| 营销通·搞懂用户专家团 | `workbuddy/experts/find-users-team` | 05-MarketingGrowth | 16 | 从你的第一批真实用户出发，找到更多可能需要产品的人，再用内容触达陌生用户。适合产品做出来了、但不知道给谁看的人。 |
| 鹏城信息AI专家 | `workbuddy/experts/game-development-studio` | 03-GameSpatial | 17 | 统筹策划、技术、美术、音频、质量、运营六大专业成员，以七阶段工作流驱动游戏从概念到上线流程协同开发。 |
| 专业高考顾问 | `workbuddy/experts/gaokao-advisor` | 12-IndustryConsultant | 41 | 检索高考真题作文、高校专业信息，查批次线与一分一段；提供全流程志愿填报引导，产出带冲稳保的志愿报告 |
| 金手指 · 广告投放专家团 | `workbuddy/experts/goldfinger-ads` | 05-MarketingGrowth | 150 | 金手指广告投放专家团：需求评估、媒介策略、素材规划、投放执行与复盘、规则咨询，一站式搞定腾讯广告。 |
| 深度研究团队 | `workbuddy/experts/gpt-researcher-team` | 04-DataAI | 17 | 7 位专业角色分 5 阶段协作完成深度研究：初始调研 → 规划大纲 → 逐章深度研究（审稿修订循环）→ 撰写报告框架 → 发布输出。支持完整 / 快速 / 单章三种模式。适用于行业研究、竞品分析、技术综述、学术文献综述等场景，产出带多源超链接引用的专业研究报告。 |
| HR 运营团队 | `workbuddy/experts/hr-operations-team` | 09-OperationsHR | 14 | 由 HR 总监领导的 4 人人力资源专家团队：招聘专家（招聘漏斗/面试设计/Offer 起草）、薪酬分析师（市场对标/薪酬带分析/股权建模）、组织发展顾问（组织规划/绩效评估/人员分析）和 HR 运营专员（入职引导/政策查询/合规）。覆盖完整的员工生命周期。 |
| 花叔数据分析专家团 | `workbuddy/experts/huashu-data-pro` | 04-DataAI | 11 | 「一人公司」本地数据分析专家团。一份 Excel 进，趋势 / 结构 / 异常三专家并行分析，交付网页、Excel、PPT 三格式报告，数据不出本地。 |
| 卡尔的人感PPT专家团 | `workbuddy/experts/humanize-ppt-team` | 06-ContentCreative | 342 | 把原始资料梳理成人感PPT大纲，调度HTML生成、演讲模式、视频动效与交付质检，形成可演示成果。 |
| 救火队 | `workbuddy/experts/incident-response-commander` | 02-Engineering | 79 | 系统故障时冷静指挥团队快速定位处理和恢复，是终极救火队长 |
| 鹏城信息AI专家 | `workbuddy/experts/interview-simulator` | 09-OperationsHR | 5 | 模拟任意职位真实面试官，覆盖技术产品销售人事等全岗位，逐题评分、详细反馈与录用建议，助你备战面试。 |
| 法大大·睿契提供的投融资顾问 | `workbuddy/experts/investment-financing-legal-advisor` | 11-SecurityCompliance | 495 | 【法大大·睿契】面向企业法务与投融资律师，按 L0-L3 分层路由调度法律尽调、法规研究、交易文件起草、交割管理与独立核验，覆盖股权投资与并购全流程。 |
| 投资大师专家团 | `workbuddy/experts/investment-masters-team` | 08-FinanceInvestment | 51 | 13位传奇投资哲学家 + 6位专业分析师并行分析，风险管理师评估约束，投资组合经理信号聚合投票，多角度投资分析参考 |
| 智能发票专家团 | `workbuddy/experts/invoice-verify-workbuddy` | 11-SecurityCompliance | 29 | 五位AI专家接力协作，通过上传文件、表格或文件夹，完成识别、税局验真、信用核查与归档 |
| 法大大·睿契提供的知识产权专家 | `workbuddy/experts/ip-expert-team` | 11-SecurityCompliance | 133 | 【法大大·睿契】面向知识产权律师，按领域调度商标注册、商标维权、商标诉讼、专利分析与著作权侵权分析，覆盖知产全流程。 |
| 求职陪跑团 | `workbuddy/experts/job-companion-team` | 12-IndustryConsultant | 21 | 5 角色陪跑型专家团，7 阶段接力覆盖自我盘点、目标定位、简历打磨、面试陪练、谈薪决策与入职复盘全流程。 |
| KET备考专家团 | `workbuddy/experts/ket-prep-team` | 12-IndustryConsultant | 16 | 剑桥认证考官领衔，为小学生提供KET全流程备考：学情测评、词汇语法地基、听说读写专项提分、考前冲刺模考，助力Merit（优秀）/Distinction（卓越）达标。 |
| LinkFox | `workbuddy/experts/linkfox-expert-team-amazon-product-selection` | 07-SalesCommerce | 771 | 26位亚马逊选品专家协同，覆盖市场扫描、关键词、VOC、货源、利润、库存、竞品监控与侵权风险。 |
| 营销战役团队 | `workbuddy/experts/marketing-campaign-team` | 05-MarketingGrowth | 14 | 由营销总监领导的 4 人营销专家团队：内容创作者（博客/邮件/社媒/品牌声音）、活动策划师（战役策略/受众/渠道/预算）、SEO 专家（技术审计/内容优化/效果分析）和品牌分析师（竞品定位/品牌审核）。覆盖完整营销生命周期。 |
| 营销增长专家团 | `workbuddy/experts/marketing-growth-team` | 05-MarketingGrowth | 85 | fCMO 级全栈营销增长团队：转化率优化、SEO 与内容策略、增长工程、数据归因分析与策略规划，全方位助力 SaaS 产品增长 |
| 领券下单找我 | `workbuddy/experts/meituan-living-assistant` | 07-SalesCommerce | 18 | 帮您一键领取美团优惠券，搜索附近团购美食并下单，探索今日活动，覆盖餐饮饮品等生活服务，省钱省心。 |
| MVP开发专家团 | `workbuddy/experts/mvp-dev-expert-team` | 02-Engineering | 54 | 说出你的想法，8位专家从调研、设计、编码、测试到部署全流程协作，帮你快速开发MVP产品 |
| 计算机等级考试专家团 | `workbuddy/experts/ncre-expert` | 02-Engineering | 15 | NCRE一至四级专家团，覆盖Office、编程、数据库与网络安全，分工协作，量身定制备考方案。 |
| 一人公司专家团 | `workbuddy/experts/opc-team` | 12-IndustryConsultant | 53 | 基于由Easy创作的《一人企业方法论》，9位专家陪你走完从资源盘点、利基定位到MVP、转化、复盘的一人公司全流程共创 |
| 专业文档生成团队 | `workbuddy/experts/openspec-doc-team` | 10-ProjectQuality | 11 | 4 位专业角色分 6 阶段协作完成企业级长文档生成：需求分析 → 知识检索 → 内容生成 → 质量审核（循环）→ 整合汇编 → 交付输出。适用于施工图设计说明、技术方案、招投标文件、维修手册、API/系统文档等场景。 |
| 研报复现因子挖掘回测审计 | `workbuddy/experts/pandaai-ai-quant-research-team` | 08-FinanceInvestment | 147 | 五位独立专家完成研报复现、因子设计、PandaAI大赛实跑、过拟合审计与绩效报告，缺少真实证据即阻断。 |
| 热点题材与资金联合研判 | `workbuddy/experts/pandaai-hot-theme-team` | 08-FinanceInvestment | 62 | 五位专家联合复盘市场、题材热度和资金变化，筛选核心候选并通过风险闸门，输出可追溯的统一会诊结论。 |
| 万方数据 | `workbuddy/experts/paper-topic-selection` | 12-IndustryConsultant | 26 | 帮你做论文选题：检索文献、推荐方向、评估新颖性、生成标题、出领域报告。说学科方向即可。 |
| 踏歌行专利智多星专家团 | `workbuddy/experts/patent-expert-team` | 12-IndustryConsultant | 317 | 13位专利专家，从文献检索、交底书、权要优化到附图、合规、答审与打包，产出CNIPA合规申报包。 |
| 产品战略团队 | `workbuddy/experts/product-strategy-team` | 01-ProductDesign | 16 | 由产品总监领导的 5 人产品专家团队：需求分析师（PRD/功能规格书）、用户研究员（调研综合分析）、竞品分析师（竞争情报）、数据分析师（指标追踪）和路线图规划师（路线图管理/迭代规划）。覆盖从构思到上线的完整产品生命周期。 |
| 袋鼠帝宣传片创作团队 | `workbuddy/experts/promo-creator-team` | 06-ContentCreative | 20 | 6位专业角色分6阶段协作完成产品宣传片全流程制作：创意简报、逐镜头分镜、素材生产、HyperFrames剪辑合成、BGM设计与交付，从产品URL到可发布的60-90秒宣传片MP4 |
| 闪造造 | `workbuddy/experts/rapid-prototyping-engineer` | 02-Engineering | 82 | 以极快速度将创意转化为可工作的原型，让团队快速验证想法 |
| 小红书增长专家团 | `workbuddy/experts/redfox-xiaohongshu-ops-team` | 06-ContentCreative | 118 | 一支专注小红书增长的多角色团队：从爆款灵感到笔记创作、账号诊断、素材下载，覆盖运营全链路。 |
| Rightly 合规辅助专业版 | `workbuddy/experts/rightly-compliance-assistant-pro` | 11-SecurityCompliance | 44 | 隐私合规专家团，解读政策与通报条目，分析违规详情，结合专业版 Rightly 数据输出整改方案。 |
| 资本市场路演研究团 | `workbuddy/experts/roadshow-research-team` | 08-FinanceInvestment | 32 | 多专家协作标的研报：多源解析、行业对比、财报三表（上市+未上市）、路演研报、股价关联，模板出报告。 |
| 销售作战团队 | `workbuddy/experts/sales-battle-team` | 07-SalesCommerce | 14 | 由销售总监领导的 4 人销售专家团队：客户研究员（公司/潜客情报）、外联策略师（邮件起草/电话准备）、竞争情报分析师（赢单/丢单分析/Battle Card）和销售预测分析师（Pipeline 评审/预测）。覆盖从研究到成交的完整销售周期。 |
| 吴八哥 | `workbuddy/experts/senior-developer` | 02-Engineering | 118 | 10年以上全栈经验，精通多种语言和框架，是团队的技术中坚 |
| SEO 内容营销团队 | `workbuddy/experts/seo-content-team` | 05-MarketingGrowth | 21 | 7位专业角色分5阶段协作：关键词研究、SEO长文创作、技术优化、内容编辑、链接策略、转化率分析，全流程自动化产出高质量SEO内容 |
| 思研·市场研究专家团 | `workbuddy/experts/sia-research-team` | 05-MarketingGrowth | 36 | 从一个模糊的生意想法开始，先摸市场判断能不能做，再出访谈大纲问卷去问真实用户，最后把数据变成能拍板的结论。一人公司也能跑完整条链。 |
| 组小学 | `workbuddy/experts/small-molecule-rd-team` | 04-DataAI | 12 | 专注小分子一体化研发，协同开展性质建模、连接体设计、骨架跃迁与逆合成规划，输出优选结构及合成路线。 |
| 营销通·社媒内容专家团 | `workbuddy/experts/social-content-team` | 06-ContentCreative | 43 | 帮自媒体和品牌号搞定起号涨粉、爆款拆解、投流和变现，个人和小团队都能找到自己的做法。 |
| 社媒互动增长专家团 | `workbuddy/experts/social-engagement-team` | 05-MarketingGrowth | 19 | 通过智能化互动自动化、AI评论运营、高转化信号挖掘和品牌舆情监控，安全高效提升社交媒体互动效果，覆盖14+全球主流平台 |
| software-company | `workbuddy/experts/software-company` | team | 7 | Software Development Team - Optimized multi-agent SOP workflow for fast software delivery |
| 腾讯自选股股票投研专家团 | `workbuddy/experts/stock-partner-team` | 08-FinanceInvestment | 39 | 六位投研专家团，兼擅产业策略、信号捕捉、估值定价、逆向布局、基本面与短线，基于实时行情多视角研判。 |
| 财税合规专家团 | `workbuddy/experts/tax-compliance-team` | 11-SecurityCompliance | 19 | 覆盖票据处理、记账核算、报表编制、税务申报、合规审计五大环节的企业财税合规全链路管理专家团 |
| 跳跃视界 | `workbuddy/experts/tiaoyue-screenplay-team` | 06-ContentCreative | 23 | 依托麦芽生态与跳跃视界AI工具打造的短剧全链路创作专家团。对话内一站式完成题材策划、剧本生成、角色场景资产生成到分镜生成预览，完整覆盖短剧创作全流程。 |
| 腾讯公益今日待办专家团 | `workbuddy/experts/today-todo-assistant` | 09-OperationsHR | 79 | 专家团模式协助机构处理今日待办，涵盖留言运营、证件备案更新与票据处理，智能分派任务一站式完成。 |
| 交易分析团队 | `workbuddy/experts/trading-agent` | 08-FinanceInvestment | 17 | 13位专业角色分5阶段协作完成投资分析：技术面、基本面、新闻面、情绪面数据采集 → 多空辩论 → 交易决策 → 三方风险评估 → 最终报告，输出 BUY/SELL/HOLD 建议及完整操作方案 |
| 像素君 | `workbuddy/experts/ui-designer` | 01-ProductDesign | 144 | 精通设计系统和组件库，追求像素级完美，打造无障碍用户界面 |
| 苍何视频解剖 | `workbuddy/experts/video-dissection` | 06-ContentCreative | 19 | 专业拆解火爆抖音视频拍摄手法的专家团。输入抖音链接，自动提取视频、转录文案、分析景别运镜、剪辑节奏、色调风格，生成完整拍摄脚本拆解文档，并提供可落地的仿拍建议。 |
| 苍何视频生成团队 | `workbuddy/experts/video-gen-team` | 06-ContentCreative | 18 | 三位一体的AI视频创作团队：灵阅负责采集AI/科技热点，灵枢负责策划选题与脚本，灵映负责渲染MP4视频成品（配音+字幕）。全流程自动化，60秒短视频一键生成。 |
| 小程达 | `workbuddy/experts/we-chat-mini-program-developer` | 02-Engineering | 192 | 精通微信小程序开发框架和生态，打造流畅微信原生体验应用 |
| 号运运 | `workbuddy/experts/wechat-official-account-expert` | 06-ContentCreative | 38 | 精通公众号内容策略和粉丝增长，打造10万+品牌自媒体矩阵 |
| 腾讯云大数据 | `workbuddy/experts/workbuddy-data-expert-team` | 04-DataAI | 73 | 融合业务分析与数据治理能力，支持智能问数、经营报告、指标口径解释、血缘影响和质量根因定位 |
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
| deep-research | `workbuddy/cb_teams_experts/plugins/deep-research` | 金融和商业分析 | 6 | 深度研究框架 |
| design-to-code | `workbuddy/cb_teams_experts/plugins/design-to-code` | 技术开发工具 | 15 | Figma 设计转代码 |
| dockerfile-gen | `workbuddy/cb_teams_experts/plugins/dockerfile-gen` | 技术开发工具 | 2 | Dockerfile 生成 |
| document-skills | `workbuddy/cb_teams_experts/plugins/document-skills` | 文件处理和通用工具 | 76 | 文档处理 |
| equity-research | `workbuddy/cb_teams_experts/plugins/equity-research` | 金融和商业分析 | 22 | 股票研究 |
| executing-marketing-campaigns | `workbuddy/cb_teams_experts/plugins/executing-marketing-campaigns` | 营销和内部运营 | 15 | 营销活动管理 |
| finance | `workbuddy/cb_teams_experts/plugins/finance` | 金融和商业分析 | 13 | 财务与会计 |
| finance-data | `workbuddy/cb_teams_experts/plugins/finance-data` | 金融和商业分析 | 22 | 金融数据检索（209 个 API） |
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
| paper-reader | `workbuddy/skills/paper-reader` | skill | 1 | 基于论文文本的通用读论文助手。用户提供论文文本（文件路径或直接粘贴），解答各类读论文需求——总结、精读、内容问答、概念解释、批判性分析等，并将结果以 Markdown 写入当前工作目录。触发词：读论文、论文总结、精读这篇论文、帮我分析这篇论文、这篇论文讲了什么、论文问答、论文笔记。输入为纯文本/Markdown 论文内容；不做论文检索下载、不做扫描件 OCR、不做论文写作降重。 |
| paper-rebuttal | `workbuddy/skills/paper-rebuttal` | skill | 4 | 以论文作者身份完成学术审稿 rebuttal 全流程。当用户提供审稿意见（reviewer comments / reviews / meta-review）和论文文件（PDF/LaTeX/DOCX/Markdown），需要分析审稿意见、判断是否需要修改论文、修改论文并撰写给审稿人的逐条回复（rebuttal / response letter / author response）时使用。触发词包括：rebuttal、审稿意见回复... |
| paper-reviewer | `workbuddy/skills/paper-reviewer` | skill | 3 | 专业学术论文审稿 skill。以领域专家视角对学术论文（本地 PDF、arXiv ID/URL、粘贴文本）进行系统评审，自动识别论文学科与贡献类型并切换对应领域专家标准，输出顶会 OpenReview 风格（NeurIPS/ICLR/ICML）的标准 review 意见：Summary、Strengths、Weaknesses、Questions to Authors、Overall Score (1-10)、Confidence... |
| prompt-engineering-expert | `workbuddy/skills/prompt-engineering-expert` | skill | 12 | Advanced expert in prompt engineering, custom instructions design, and prompt optimization for AI agents |
| research-lineage-map | `workbuddy/skills/research-lineage-map` | skill | 4 | 绘制研究领域或技术主题的谱系脉络与历史演进图，可视化思想的演化路径，展示早期工作中的技术难题如何被后续研究逐步解决。当用户想了解某个主题的发展轨迹、某个模型或技术的"家族树"（family tree）、某条研究线索在多年间的演进路线、技术迭代脉络、论文/模型谱系，或询问"X 是如何一步步发展来的""X 解决了前人的什么问题""梳理 X 的发展历史"时触发。产出为嵌入 Mermaid 图表的 Markdown 文件（演进图 + 节点... |
| skillhub-daily | `workbuddy/skills/skillhub-daily` | skill | 13 | 'SkillHub 每日推荐 - 扫描 skillhub.cn 全站 Top100 + 7 大分类各 Top20（共 240 个 Skill）， |
| tencent-yuanbao-standard-search | `workbuddy/skills/tencent-yuanbao-standard-search` | skill | 4 | Search the web using TencentCloud Web Search API (WSA). Prioritize using it when you need to retrieve network information. |
| wechat-article-pro | `workbuddy/skills/wechat-article-pro` | skill | 2 | 微信公众号文章发布专业版。功能：1)联网搜索热点信息 2)AI生成微信公众号封面图 3)撰写3000-5000字深度文章 4)使用公众号AI配图功能自动生成并上传封面 5)参考刘润公众号风格写作 6)自动排版 7)不加话题标签 |
| wedding-handcard-creator | `workbuddy/skills/wedding-handcard-creator` | skill | 5 | 根据婚礼主持稿生成可直接打印的主持人手卡。输出 A5 竖版拼版（每张 A5 纸上下各一张小卡，对半裁开即得 12 张手卡），支持 HTML 和 PDF 两种格式，正面为台词+动作提示+页号，背面为红金囍字封面。适用于：用户要求制作婚礼主持手卡、把主持稿转成可打印卡片、生成司仪手卡/提词卡、设计婚礼手卡封面、输出 PDF，或已有主持稿需要配套现场手持卡片的场景。 |

### Connectors / Marketplace

| Name | Directory | Category | Files | Description |
| --- | --- | --- | ---: | --- |
| 24好玩 互动营销资料库 | `workbuddy/connectors/marketplace/connectors/24haowan` | mcp | 2 | 24好玩（24haowan）的匿名只读 MCP 服务，8 个工具：实时查询互动营销 H5 活动模板库、真实客户案例库、帮助中心知识库，以及来自平台真实活动的行业基准数据（中奖率 / 奖池档位 / 活动周期 / 玩家行为）。免注册、无 API Key、只读无副作用。 Version: 1.0.0. |
| 24好玩 · 方案空间 | `workbuddy/connectors/marketplace/connectors/24haowan-space` | mcp | 3 | 24好玩·方案空间（space.24haowan.com）：Agent 原生的 B2B 售前方案沟通平台，21 个工具。把做好的方案（PDF / PPTX / 网页 Deck / Markdown）发布成客户专属的微信可读链接，读回客户看了哪几页、停留多久、有什么反馈，把会议意见记回方案，改稿出新版原链接自动更新。需微信扫码登录授权。 Version: 1.0.0. |
| 3Chat 私域客户运营 | `workbuddy/connectors/marketplace/connectors/3chat-customer-growth` | mcp | 3 | 面向使用AI客服、销售智能体开展私域运营和客户转化的企业与商家。可在WorkBuddy中，通过自然语言查找、筛选和理解微信、企业微信、小红书、抖音等渠道中的真实客户，获取客户画像、历史沟通、兴趣偏好、购买意向和成交阶段，并执行单客户触达、批量营销、客户激活和精准跟进。客户回复后，可由3Chat AI客服/销售智能体继续自动接待、回答咨询、识别高意向客户、处理销售异议并推进成交，形成客户洞察、精准触达、AI接待、持续跟进、成交转化的... |
| 51社保 | `workbuddy/connectors/marketplace/connectors/51shebao-hr-tools` | mcp | 2 | 查询各城市社保、公积金缴费基数、比例、办理截止日、最低工资、社平工资与产假天数，检索社保政策原文与政策分析报告，附政策依据原文链接。 Version: 1.0.1. |
| 千图 AI | `workbuddy/connectors/marketplace/connectors/58pic-qiantu-ai` | mcp | 2 | 在 WorkBuddy 中搜索正版素材、生成图片和视频、运行可编辑工作流，并管理创意资产。 |
| 铱云AI供应链 | `workbuddy/connectors/marketplace/connectors/77ircloud` | cli | 115 | 通过自然语言管理铱云供应链：支持订单全链路操作，以及客户、商品、仓库库存、员工组织、资金账户、数据导出、经营统计和预警明细的查询分析。 Version: 1.0.2. |
| AgentEarth 金融电商社媒工具集 | `workbuddy/connectors/marketplace/connectors/agent-earth` | mcp | 3 | 专业金融股票行情、电商社媒数据、内容生成、搜索抓取、学术论文与专利信息、地图信息等。只需一次注册便可调用不同领域专业数据，无需逐一配置各类服务，价格相对官方有大幅折扣。目前已覆盖以下领域：金融： 查询 A股、美股股票行情、股价、K线、成交量、公司财务、财报及基本面数据，覆盖基金、ETF、外汇、汇率、比特币和加密货币，辅助股票与公司研究、投资分析和市场跟踪。接入 Tushare、CoinGecko 等金融数据服务。内容生成： 支持.... |
| Aholo Lux3D | `workbuddy/connectors/marketplace/connectors/aholo-lux3d` | mcp | 3 | 通过文字或图片创建 3D 资产，为模型重绘材质、补齐视角、转换格式，并查询任务和获取结果。 Version: 0.1.1. |
| AI-HIVE | `workbuddy/connectors/marketplace/connectors/ai-hive` | connector | 29 | 连接全球 100+ 顶尖 AI 模型（Seedance 2.5、H3 (MiniMax)、Happyhorse、GPT-image、Nano-Banana、Deepseek、Kimi 等），一键搞定文本、图像、视频创作。 |
| 腾讯未来教室 | `workbuddy/connectors/marketplace/connectors/aiclass-teaching` | mcp | 2 | 接入腾讯未来教室（aiclass）：查询未来教室课程列表、把 AI 生成的图片以「教学打卡」发布到未来教室小程序、对输出结果提交反馈。 Version: 0.1.0. |
| AI尽调助手 | `workbuddy/connectors/marketplace/connectors/aidd-saas` | mcp | 2 | 银行对公授信尽调智能分析平台，提供进件识别、行业分析、企业画像、经营分析、财务分析和报告生成等主要环节支持。 Version: 1.0.1. |
| 智慧记AI进销存 | `workbuddy/connectors/marketplace/connectors/ailit` | cli | 12 | 结合您的进销存业务数据，可实现成批量对账、销售开单和批量创建商品，覆盖销售、采购、库存、收银、对账及经营分析等多种业务场景。 Version: 0.8.3. |
| 思研·AI调研平台 | `workbuddy/connectors/marketplace/connectors/aimoderator` | connector | 2 | 用自然语言快速创建 AI 访谈项目：提供标题、背景、大纲（及可选开场白），即可在思研平台生成访谈项目并返回可直接分享的访谈链接。 |
| Alpha派投研助手 | `workbuddy/connectors/marketplace/connectors/alphapai-lite-mcp` | mcp | 10 | Alpha派·Lite版是讯兔科技为金融工作者、投资者量身打造的AI助理，掌握深度行业、公司研究分析与大类资产、市场策略专业解读能力，并具备专业的写报告、画PPT、做图表、写纪要等金融白领必备技能。 Version: 1.0.0. |
| 腾讯健康全周期管理平台 | `workbuddy/connectors/marketplace/connectors/archive-hospital-mcp` | mcp | 2 | 全周期管理平台机构端的数据查询MCP连接器，覆盖医疗数据、管理任务、对话沟通等业务域的查询能力，所有数据仅在对话内分析、不落盘不导出。 Version: 2.0.0. |
| 向日葵远程控制 | `workbuddy/connectors/marketplace/connectors/awesun` | cli | 5 | 通过命令行管理远端设备，实时监测在线状态、秒级发起远程控制、快速传输文件及远程截屏。零部署、免更新，轻松实现智能批量运维。 |
| 百度网盘 | `workbuddy/connectors/marketplace/connectors/baidu-netdisk` | mcp | 2 | 连接百度网盘，支持文件与分类浏览、关键词及语义检索、文件和文件夹管理、创建分享链接、查询容量，以及保存文本内容或通过 URL 转存文件。 |
| 百积木 | `workbuddy/connectors/marketplace/connectors/baijimu-enterprise-ai` | cli | 2 | 连接百积木工作区、智能体、工作流、应用与受治理的企业服务。 Version: 1.0.0. |
| 百晓智能 | `workbuddy/connectors/marketplace/connectors/baixiao-mcp` | mcp | 3 | 中英文学术检索: 搜索期刊论文、专著、政策文件；查阅最新基金招投标信息；核实参考文献真伪、追溯引用；推荐投稿期刊与审稿人。 Version: 1.0.0. |
| 八爪鱼 | `workbuddy/connectors/marketplace/connectors/bazhuayu` | mcp | 2 | 用自然语言驱动八爪鱼云采集：搜索模板、启动任务、查询进度、导出结构化数据，并管理已有任务。 |
| BeatDesign 本地创作工作台 | `workbuddy/connectors/marketplace/connectors/beatapi-beatdesign` | mcp | 2 | 通过自然语言操作本地 BeatDesign 画布、素材、生成任务、视频时间线和字幕。 Version: 0.2.3. |
| 北森AI · HR专家 | `workbuddy/connectors/marketplace/connectors/beisen-cli` | cli | 44 | 依托北森HR SaaS平台，把审批、招聘进展、员工档案、绩效履历、考勤假期、组织架构和企业制度等近百个人力场景装进Workbuddy，一句话查询人力数据、办理HR业务。 Version: 1.0.0. |
| BioBuddy 生物医药研究助手 | `workbuddy/connectors/marketplace/connectors/biobuddy` | mcp | 5 | BioBuddy 生物医药智能研究平台：一次连接 Gateway，即可发现并挂载已获授权的分子设计、转化研究、靶点发现与数据智能 MCP 工具。 Version: 1.0.3. |
| BizMuse AI 音乐视频 | `workbuddy/connectors/marketplace/connectors/bizmuse-ai-music-video` | mcp | 2 | 根据一首歌曲、参考图片和创作方向生成完整的 AI 音乐视频。支持叙事、演唱、舞蹈、抽象等内容风格，可选画幅比例、清晰度与口型同步，并可查询生成任务进度与获取成片。 Version: 0.3.0. |
| Bugly 质量概览 | `workbuddy/connectors/marketplace/connectors/bugly-token` | mcp | 3 | 查看产品的质量概览 包括崩溃率 anr率 foom（oom）率 启动耗时 |
| 财汇金融与风险数据 | `workbuddy/connectors/marketplace/connectors/caihui-mcp` | mcp | 2 | 财汇 MCP 提供专业金融与风险数据服务，覆盖境内企业工商、上市公司、债券、基金、金融机构、宏观与区域经济、监管与司法风险、新闻公告及法规等多维度数据，支撑金融数据查询、风险评估、分析研究、投资交易、舆情监测、投行尽调、信贷管理、合规审查等业务场景。 Version: 1.0.0. |
| 扫描全能王 | `workbuddy/connectors/marketplace/connectors/camscanner-mcp` | mcp | 8 | 智能文档转换与处理平台。支持图片/PDF转Word、Excel、Markdown，图片转PDF，Word/Excel/PPT转PDF，Office文档格式升级（DOC→DOCX等），图片增强（去阴影、锐化、高清化、老照片修复），OCR文字识别、图片翻译、公式提取、水印处理、多图合并，以及云文档保存/搜索/下载/移动/文件夹管理等。 |
| 餐道.数智经营 | `workbuddy/connectors/marketplace/connectors/candao-age` | mcp | 10 | 一句话掌握餐厅外卖口碑：查询授权门店、评价指标、差评原因与趋势，快速生成评价分析报告。 Version: 1.0.1. |
| Canva可画 | `workbuddy/connectors/marketplace/connectors/canva` | mcp | 2 | 无缝调用Canva可画的设计能力。一句话生成海报、演示文稿、小红书封面等设计，通过文字描述调整尺寸、填充品牌模板及检索已有内容 |
| 链龙 GEO 可见度检测 | `workbuddy/connectors/marketplace/connectors/chainlon-geo-mcp` | mcp | 2 | 查询品牌在 AI 搜索里是否被提到、生成关键词矩阵、输出 GEO 综合诊断与行动建议；数据来自真实检索，未配置数据源时如实提示降级，绝不编造分数与排名。 Version: 1.0.0. |
| 订单门店查询 | `workbuddy/connectors/marketplace/connectors/charge-order-query` | mcp | 2 | 按手机号查询共享充电宝租借订单，按经纬度查询附近门店，用自然语言即可查询订单明细与最近网点。 Version: 1.0.0. |
| 创客贴 AI 创作 | `workbuddy/connectors/marketplace/connectors/chuangkit` | cli | 2 | 一键调用创客贴强大的AI在线设计能力，一句话生成专业营销设计，覆盖海报、品牌logo、封面配图、小红书图文，电商等设计场景，支持图文分层可编辑，点选改字，让设计小白轻松做图做视频！ Version: 0.1.0. |
| 出海匠 | `workbuddy/connectors/marketplace/connectors/chuhaijiang` | mcp | 12 | 基于实时 TikTok Shop 数据完成选品、竞品分析、达人筛选与带货内容创作，并管理社媒账号、发布内容、运营评论和私信。 |
| 水滴征信 | `workbuddy/connectors/marketplace/connectors/cisp-mcp` | mcp | 3 | 通过水滴征信企业信息服务平台查询工商、知识产权、舆情、财务、土地、企业关联关系、关联方等企业多维信息，并支持企业二要素/三要素核验。 |
| 腾讯云 CloudBase | `workbuddy/connectors/marketplace/connectors/cloudbase` | connector | 156 | 腾讯云开发 CloudBase 全栈开发、部署、调试与排障连接器。覆盖 Web 应用、微信小程序、uni-app、原生 App HTTP API、云函数、CloudRun、NoSQL/MySQL 数据库、云存储、静态托管、身份认证、AI 大模型调用、AI Agent、资源巡检与 Spec 工作流。 |
| 云之家 | `workbuddy/connectors/marketplace/connectors/cloudhub` | cli | 15 | 通过自然语言操作云之家：知识库文档、多维表格、日历日程、通讯录、IM 消息与文件管理。 Version: 0.6.1. |
| 云MALL运营 | `workbuddy/connectors/marketplace/connectors/cloudmall-operations` | mcp | 4 | 在 WorkBuddy 中用自然语言查询云MALL订单、商品与会员数据。连接运营账号后，按你当前的权限执行只读查询，结果实时返回，无需切换后台。 |
| CNB | `workbuddy/connectors/marketplace/connectors/cnb-api` | cli | 2 | 通过自然语言管理 CNB 平台：仓库、Issue、PR、流水线、制品库等操作。 |
| 连接器工坊 | `workbuddy/connectors/marketplace/connectors/connector-workshop` | mcp | 2 | 探测远程 MCP 端点能力，起草并校验 WorkBuddy 连接器配置，产出符合规范的连接器 zip 包。 Version: 1.0.0. |
| COROS | `workbuddy/connectors/marketplace/connectors/coros` | mcp | 2 | 用自然语言查询 COROS 运动与健康数据：训练记录、活动分析、睡眠、心率、HRV、压力、体能评估与训练日程。 Version: 1.0.0. |
| 达秘-TikTok批量建联&达人管理工具 | `workbuddy/connectors/marketplace/connectors/dami-external-mcp` | mcp | 3 | 通过自然语言批量管理 TikTok 达人建联、邀约、私信和店铺/商品/达人查询。 |
| DataBuddy | `workbuddy/connectors/marketplace/connectors/databuddy` | cli | 18 | 连接腾讯云大数据 DataBuddy 数据知识库，让 AI 基于企业真实数据作答——问数、报告、异动归因、预测、相关信号分析更可信，并可生成实时更新的仪表盘。 Version: 0.1.2. |
| DataHub | `workbuddy/connectors/marketplace/connectors/datahub` | mcp | 2 | 用自然语言发现并运行 Data App，跟踪执行状态与费用，读取结构化结果并管理历史运行。 Version: 1.0.0. |
| 通联数据 | `workbuddy/connectors/marketplace/connectors/datayes-data` | mcp | 3 | 用自然语言查询金融数据：A股/港股、基金、债券、指数、期货期权、因子、实时行情、宏观、公告与政策法规。 |
| DCS Cloud | `workbuddy/connectors/marketplace/connectors/dcs-cloud` | mcp | 6 | DCS CLI，连接后通过个人访问令牌（PAT）登录认证，即可操作 DCS 云平台：支持项目管理、组学数据检索与传输、离线分析任务投递与查询、工作流管理等。使用前需在云平台个人中心创建 PAT，并粘贴至连接器完成绑定。 |
| 克而瑞地产数据 | `workbuddy/connectors/marketplace/connectors/deeplink` | mcp | 2 | 克而瑞地产数据依托经克而瑞授权、积累近 20 年的中国不动产数据。「问数」覆盖新房、二手房、土地、企业、宏观、长租公寓、产城、康养、商办九大领域，支持自然语言查询、排行、趋势与多城对比；「问知」提供地产、物业、银发领域的政策、研究、企业、法规和运营知识问答。 Version: 4.0.2. |
| 得理法律数据 | `workbuddy/connectors/marketplace/connectors/deli-mcp` | mcp | 1 | 得理法律数据 MCP 连接器，提供权威法律数据检索，覆盖 1.7 亿+裁判文书与 300 万+法律法规。支持自然语言案例检索、法规检索与法律问答，可按案情描述、争议焦点、法规名称或条款内容语义检索，并获取案例/法规详情与效力状态。 Version: 1.0.0. |
| 美图设计室 AI设计 CLI | `workbuddy/connectors/marketplace/connectors/designkit-buddy-cli` | cli | 2 | 一句话轻松调用美图设计室Agent Teams，从市场策略洞察，到电商套图、营销视频、社媒图文、海报及品牌等视觉物料，零门槛完成商业设计的全流程。 Version: 1.0.2. |
| 订单豹 | `workbuddy/connectors/marketplace/connectors/dingdanbao` | mcp | 8 | 面向批发业务员的订单豹助手，覆盖代客下单、客户运营、库存、采购、催款与业绩简报。 Version: 1.0.0. |
| 钉钉 | `workbuddy/connectors/marketplace/connectors/dingtalk` | cli | 188 | 通过命令行管理钉钉全产品能力：AI 表格、考勤、日历、群聊与机器人、通讯录、开放平台文档、DING 消息、钉钉文档、钉钉云盘、AI 听记、邮箱、OA 审批、日志、待办。 |
| 深知可信工作台 | `workbuddy/connectors/marketplace/connectors/dknowc-mcp` | mcp | 2 | 深知可信工作台聚焦法律、政策、标准等可信知识服务，并覆盖产业研究和公共服务场景。支持将复杂问题拆解为可验证的检索任务，综合多来源材料交叉验证，追溯权威原文及依据，形成来源清晰、可核验的问答、检索与研究结果。 |
| 邓白氏查全球 | `workbuddy/connectors/marketplace/connectors/dnb-global-data` | mcp | 3 | 通过自然语言查询邓白氏全球企业档案、财务数据、风险洞察、企业关联及最终受益人（UBO）等商业洞察。 |
| 龙易查 | `workbuddy/connectors/marketplace/connectors/dnb-longyicha-workbuddy` | mcp | 2 | 通过自然语言访问邓白氏中国企业数据。本服务提供企业基础信息与结构化档案数据索引，支持主体识别与匹配（通过多条件模糊检索快速定位目标企业）及构建企业基础画像（覆盖注册信息、股权结构、人员结构等核心维度） Version: 1.1.0. |
| 阅文漫剧助手 | `workbuddy/connectors/marketplace/connectors/dramabuddy` | mcp | 3 | 阅文漫剧助手（DramaBuddy）是一个人人可用的通用漫剧制作工具——只需提供小说或创意，就能自动生成剧本、角色与分镜视频，轻松做出属于自己的漫剧。 Version: 0.1.2. |
| 创意兔微课 | `workbuddy/connectors/marketplace/connectors/duoguan-course` | mcp | 3 | 对接创意兔微课平台，输入目标人群、客户痛点、转化产品与自身优势，自动完成课程策划、PPT 制作、口播稿撰写，一键制作微课并发布上线，适用于知识获客、私域营销、企业内训等场景。 |
| 夺冠蜂巢 | `workbuddy/connectors/marketplace/connectors/duoguan-fengchao` | mcp | 2 | 覆盖内容大脑、品牌画像、热点选题、口播与图文文案、配图、播客、配音、视频封装和多账号运营的一站式 AI 自媒体内容生产平台。 Version: 2.0.0. |
| 夺冠 GEO | `workbuddy/connectors/marketplace/connectors/duoguan-ge` | mcp | 2 | 通过自然语言查询和管理 GEO 总览、内容、发布、网站、关键词及租户相关数据。 Version: 0.1.0. |
| 大智慧MCP | `workbuddy/connectors/marketplace/connectors/dzh-mcp` | mcp | 2 | 提供A股K线行情、A股实时行情、港美股K线行情、港美股实时行情、期货K线行情、期货实时行情、基金行情、公司简况资料、公司主营产品、公司股东、公司分红送转、公司财务（利润表）、公司财务（资产负债表）、公司财务（现金流量表）、股票题材概念、A股板块、研究报告、公司公告、新闻舆情、资金流向、机构调研、龙虎榜、融资融券、股票技术指标等数据查询工具，辅助投资决策。 |
| 易智魔方 | `workbuddy/connectors/marketplace/connectors/easymofang` | mcp | 3 | 商品文案/图片商标侵权检测，以及电商套图生成与重绘。 Version: 1.0.0. |
| 易仓跨境对账 | `workbuddy/connectors/marketplace/connectors/eccang-reconcile` | mcp | 2 | 发一份平台结算 Excel，自动核对 TikTok Shop / Tokopedia 账单与易仓结算数据：比对订单数与结算金额，标出金额差异、单边订单，并生成可对外的对账报告。 Version: 1.0.2. |
| EdgeOne Makers | `workbuddy/connectors/marketplace/connectors/edgeone-pages` | mcp | 49 | 将项目部署到 EdgeOne Makers 并返回线上访问地址，支持全栈、云函数、AI Agent 等开发场景。 |
| Edu Next | `workbuddy/connectors/marketplace/connectors/edu-next` | mcp | 3 | 面向清华大学环境学院课程的 AI 教学平台，支持课程、学习任务、教学资料、成果草稿、评价反馈与学习进展协作。 Version: 1.0.0. |
| 易方达基金 | `workbuddy/connectors/marketplace/connectors/efunds` | mcp | 2 | 接入易方达基金MCP服务，一句话查透基金画像——业绩、风险收益、持仓结构等核心指标一目了然，还能随时调阅易方达发布的投研观点、产品解读与市场洞察，助力您高效进行投资决策。 Version: 1.0.0. |
| eMES AI 助手 | `workbuddy/connectors/marketplace/connectors/emes-ai` | mcp | 2 | 鼎华 eMES AI 助手，连接 eMES OPENAPI，提供生产数据查询、派工、设备报修、委外加工、报工等智能能力。 Version: 1.0.0. |
| 弹性MapReduce | `workbuddy/connectors/marketplace/connectors/emr-query` | cli | 52 | 通过CLI实现弹性 MapReduce 集群、节点、服务、作业、监控、YARN 调度、自动扩缩容、用户与配置等查询。 |
| 二号人事部 | `workbuddy/connectors/marketplace/connectors/erhao-hr` | mcp | 9 | 通过自然语言查询人事、组织、考勤与薪酬四域数据：员工花名册/异动/合同、组织架构与维度分布、考勤/假期/加班、薪资核算/成本/个税，为人力分析提供数据支撑。 Version: 0.1.9. |
| 腾讯云 Elasticsearch Service | `workbuddy/connectors/marketplace/connectors/es` | connector | 24 | 通过 MCP 操作腾讯云 Elasticsearch Service（ES）：查询实例列表，查看集群健康、节点、分片与线程池状态，浏览索引配置与 Mapping，查询监控指标与集群日志，诊断集群性能与分片未分配问题，并管理集群（节点/磁盘变配、重启、索引 Rollover、别名、Kibana 访问、Logstash 管道）。 |
| EzyJoin智慧会议 | `workbuddy/connectors/marketplace/connectors/ezjoin-meeting` | mcp | 2 | 用自然语言管理 EzyJoin 智慧会议：预约会议室、创建/取消会议、查询会议日程与 AI 纪要。 |
| EZR 全域CRM | `workbuddy/connectors/marketplace/connectors/ezr-crm` | mcp | 2 | 连接 EZR 全域 CRM，把会员、销售、活动、企微运营、券分析、商城运营、人群圈选和 MA 画布监控等能力带入智能体，帮助品牌用自然语言完成经营查询、运营分析和策略洞察。 Version: 1.0.1. |
| 法大大睿契 | `workbuddy/connectors/marketplace/connectors/fadada-richee` | mcp | 2 | 提供法律法规检索、类案检索、企业信息查询与合同审查能力，帮助用户快速查找相关法条、相似案例、核验企业信息并完成合同风险审查。 Version: 1.0.1. |
| 帆软增长谋士 | `workbuddy/connectors/marketplace/connectors/fanruan-growth-advisor` | mcp | 1 | 企业洞察与增长分析：查询企业经营风险、舆情、招投标、专利、资质、政策等公开商业数据，并调用已授权的 MOSS 增长谋士 Agent 生成分析与报告。 Version: 1.1.0. |
| FastMoss | `workbuddy/connectors/marketplace/connectors/fastmoss` | mcp | 9 | FastMoss 官方出品的 TikTok Shop 数据分析工具，覆盖商品、达人、店铺、MCN、短视频、直播、广告、类目市场与榜单数据，支持爆品挖掘、选品研究、达人筛选、竞品分析、店铺诊断、内容策略和投放效果评估。 Version: 1.0.0. |
| 同花顺法律AI助手 | `workbuddy/connectors/marketplace/connectors/fazhi-law` | mcp | 75 | 查询中国法律法规、司法案例、裁判文书及互联网法律实务资讯，支持法条检索、类案检索、深度法律研究、法律文书起草与诉讼可视化。 Version: 1.0.0. |
| 福帮手 | `workbuddy/connectors/marketplace/connectors/fbs-connector` | connector | 26 | 福帮手连接器：协助确认服务身份、匹配场景方案、记录已完成进度并查询乐包。实际能力以当前服务与授权范围为准。 |
| 飞书 | `workbuddy/connectors/marketplace/connectors/feishu` | cli | 551 | 通过命令行管理飞书/Lark 全产品能力：即时通讯、邮箱、日历、云文档、电子表格、多维表格（Base）、幻灯片、画板、知识库、云空间、妙记、视频会议、任务、审批、考勤、通讯录、OKR 等。 |
| 分贝通 | `workbuddy/connectors/marketplace/connectors/fenbeitong` | mcp | 4 | 用自然语言查看和切换分贝通账号与企业，查询和管理企业差旅、消费规则、发票与报销，分析消费洞察、合规风险和降本机会，并获取客服支持。 |
| 粉笔 | `workbuddy/connectors/marketplace/connectors/fenbi-baokao-decision` | mcp | 8 | 粉笔AI公考助手，帮你查专业分类、完善报考简历、智能选岗与国考模拟选岗、了解考情与报考条件，还能练易混词与成语辨析积累，提供一站式公考备考服务，让备考更精准、更高效。 |
| 进门投研 | `workbuddy/connectors/marketplace/connectors/finenter` | mcp | 2 | 进门MCP覆盖券商、上市公司及资管机构的公开路演内容，整合内外资研报、券商点评等机构级观点，并提供实时行情、财务及量化因子等数据。经Data Agent清洗与结构化处理，减少Token消耗，提升回答准确率。 |
| Flova | `workbuddy/connectors/marketplace/connectors/flova` | mcp | 2 | Flova AI 视频与图片内容创作：支持剧本、短片、短剧、漫剧、电影、广告、商品 TVC 与视觉设计，覆盖文生图、文生视频、图生视频、素材生成、分镜、修改、审阅和导出。 Version: 1.1.1. |
| 福马AI外呼任务 | `workbuddy/connectors/marketplace/connectors/fuma-ai-callout` | mcp | 3 | 通过 WorkBuddy 查询福马AI手机智能体、成员列表，并创建 AI 外呼任务。 |
| 法研·法律法规检索 | `workbuddy/connectors/marketplace/connectors/fyopen-lawsearch` | mcp | 2 | 法研·法律法规检索，支持自然语言获取精准、现行有效的法规条文，将高质量、海量的法规知识库，无缝接入各类AI应用与工作流中。 |
| Gangtise投研 | `workbuddy/connectors/marketplace/connectors/gangtise-mcp` | mcp | 3 | Gangtise MCP汇聚机构级观点，研报，日程等另类数据，提供投研AI Agent预生成数据及全球行情/财务/估值/宏观行业等结构化数据。 Version: 1.0.8. |
| 稿定 | `workbuddy/connectors/marketplace/connectors/gaoding` | cli | 8 | 连接稿定创作、素材、模型与编辑器能力，用自然语言完成设计工作。 Version: 0.1.0. |
| 高顿•实习就业助手 | `workbuddy/connectors/marketplace/connectors/gaodun-job` | mcp | 90 | 大学生实习就业全链路 AI 助手：智能推荐公考岗位，检索实习与校招职位，提供 MBTI、霍兰德等职业测评，简历诊断与 AI 优化改写，面试刷题与模拟面试评估报告，助你拿 offer。 |
| 得到大脑（原 Get 笔记） | `workbuddy/connectors/marketplace/connectors/getnote` | mcp | 6 | 连接得到大脑与 AI：随手保存文字、网页和图片，语义查找个人笔记，读取录音转写与会议待办，并用标签、文件夹和知识库整理长期信息。 Version: 1.0.0. |
| 广发证券 | `workbuddy/connectors/marketplace/connectors/gfsecurities` | connector | 2 | 通过广发证券 MCP，完成多维选股、深度研究、智能盯盘三大核心场景的智能投研服务，实现市场热点跟踪、资讯动态解读、标的筛选、投后复盘的智能投资闭环。 |
| 恒生聚源 MCP | `workbuddy/connectors/marketplace/connectors/gildata` | mcp | 5 | 连接恒生聚源 MCP，查询金融结构化数据、研究报告、公司公告、新闻资讯、条件选股、宏观行业、工商企业数据。支持基金经理观点持仓一致性分析、行业速报生成、金融资讯热点解读。 |
| GitHub | `workbuddy/connectors/marketplace/connectors/github` | connector | 2 | 在 GitHub 上克隆、推送代码，查看和管理仓库与 Pull Request，用自然语言完成代码协作。 |
| 共鞋ERP | `workbuddy/connectors/marketplace/connectors/gongxie-erp` | mcp | 3 | 查询并管理共鞋ERP中的仓库、库存、商品、订单及出入库业务。 Version: 1.0.0. |
| 腾讯公益机构服务平台 | `workbuddy/connectors/marketplace/connectors/gongyi-open-mcp` | mcp | 2 | 腾讯公益机构服务平台连接器：用自然语言连接并使用腾讯公益机构服务平台的功能。 Version: 1.0.0. |
| 设备云维保 | `workbuddy/connectors/marketplace/connectors/gt-generate-sql-data` | mcp | 2 | 通过自然语言查询设备信息、故障报修、维修保养、备件库存及出入库记录，支持统计、趋势分析、分类对比和明细下钻。 Version: 1.0.0. |
| 观思动-AI开发部署企业应用 | `workbuddy/connectors/marketplace/connectors/guansd` | cli | 3 | 把需求做成公司同事能登录使用的企业应用：建应用、写代码、部署开发版、平台真机验收、发布正式版；自带企业微信登录、功能权限、数据库、文件上传和定时任务。 Version: 1.0.2. |
| 新华三Cloudnet灵犀AI助手 | `workbuddy/connectors/marketplace/connectors/h3c-cloudnet` | mcp | 3 | 面向网络运维场景的 AI 助手，支持网络运行状态查询、网络问题分析、设备/AP 信息查询和无线终端故障排查，帮助用户快速定位网络异常并获取处理建议。 |
| 氚云 | `workbuddy/connectors/marketplace/connectors/h3yun-connector` | mcp | 2 | 通过氚云连接器，将日常业务快速构建为可配置、可协同、可追踪的数字化应用。支持快速创建应用表单、管理业务数据、以流程驱动审批与任务流转，适用于客户、项目、采购、库存、售后等多类业务管理场景。 Version: 1.0.1. |
| 海尔智能体 | `workbuddy/connectors/marketplace/connectors/haier-assistant` | mcp | 45 | 海尔、卡萨帝、统帅家电的选购推荐、型号对比、参数与价格咨询、购买渠道与门店查询，以及售后服务知识解答。 Version: 0.1.0. |
| 汉仪字库 | `workbuddy/connectors/marketplace/connectors/hanyi-fonts` | mcp | 2 | 连接汉仪交付平台服务，在 WorkBuddy 中查询企业合同、字体权益以及字体预览。 Version: 0.1.0. |
| 合肥便民通告 | `workbuddy/connectors/marketplace/connectors/hefei-city-alerts` | mcp | 1 | 查询合肥本地天气与预警、停水停电、燃气检修、交通管制、政府公告等实时民生信息。 Version: 0.1.0. |
| HOSE AI Assistant | `workbuddy/connectors/marketplace/connectors/hose-ai-assistant` | mcp | 1 | 连接合思差旅服务，提供身份校验、短信登录以及企业实时机票、酒店和火车票查询能力。 Version: 1.0.0. |
| 慧獭进销存 | `workbuddy/connectors/marketplace/connectors/huita-ims` | mcp | 1 | 慧獭进销存一体化 MCP 连接器：商品/库存（多店多仓、批号效期）、销售与采购开单、往来对账、经营分析。提供 14 个只读 + 6 个分析 + 12 个写工具（preview→commit 两阶段写），数据与慧獭桌面端/收银台实时同步。 Version: 1.0.1. |
| 慧择保险产品推荐 | `workbuddy/connectors/marketplace/connectors/huize-insurance-product-recommendation` | mcp | 2 | 根据年龄、人群、职业、预算和保障需求，从慧择内部产品推荐库中筛选并比较保险产品。 Version: 0.1.0. |
| 同花顺iFinD金融数据查询 | `workbuddy/connectors/marketplace/connectors/ifind-mcp` | connector | 1 | 同花顺iFinD金融数据查询，查询股票、基金、宏观经济、行业经济、新闻公告、债券、港美股、指数板块及期货期权数据；通过内置智能问数算法，仅少量工具即可覆盖海量投研级金融数据指标，其中A股、中国公募基金、债券交易所、国内指数共4类市场支持日内高频/实时行情的level1数据，同时支持智能选股、选基、宏观行业经济指标搜索、金融公告资讯搜索等服务 |
| i人事AI·HR专家 | `workbuddy/connectors/marketplace/connectors/ihr-cli` | cli | 138 | 一键直接连接 i 人事。覆盖组织人事管理、劳动合同、考勤管理、薪酬管理、社保个税、智慧绩效OKRKPI、招聘管理、培训陪练、OA审批，AI面谈、数字人面试，蓝领面试，说一句话，就能查询分析人事、薪资、绩效、用工风险，提升敏捷管理水平，降低人力成本，还有自定义各类agent，SKILL，实现定制化管理要求。 Version: 0.1.2. |
| ima | `workbuddy/connectors/marketplace/connectors/ima-mcp` | connector | 2 | 腾讯AI知识管家，连接后支持搜索、读取和写入知识库资料，并可搜索和订阅教育、法律、财经、科技等20+行业专业知识 |
| 电商内容专家 | `workbuddy/connectors/marketplace/connectors/infimind-ecommerce-content` | mcp | 9 | 通过 OAuth 连接电商内容专家，创建智能精修、商品主图、商品详情页、爆款图复制、KOC 种草、图文带货、视频生成和爆款视频复制任务。 Version: 1.0.0. |
| 英科AI中台 | `workbuddy/connectors/marketplace/connectors/intco-ai-platform` | mcp | 2 | 统一访问英科内部业务系统、RPA、企业数仓及已授权的企业付费数据服务。 |
| 今日投资金融数据 | `workbuddy/connectors/marketplace/connectors/investoday-finance-data` | mcp | 1 | 查询 A 股、港股、基金、指数、行情、财务、公告、研报、宏观经济、板块主题和产业链等金融数据与投研信息。 Version: 1.0.0. |
| 零信任安全 iOA | `workbuddy/connectors/marketplace/connectors/ioa` | mcp | 2 | 提供零信任接入、终端管控、安全防护、数据防泄密等核心安全能力的管理操作 Version: 1.0.31. |
| 亿欧数据MCP | `workbuddy/connectors/marketplace/connectors/iyiou-connector` | mcp | 3 | 接入亿欧数据MCP服务，用自然语言查透产业数据——企业投融资、产业链上下游、产业研报等核心数据一目了然，还能随时调阅亿欧发布的产业观点、企业解读与市场洞察，助力您高效进行商业决策。 Version: 1.0.0. |
| 简道云 | `workbuddy/connectors/marketplace/connectors/jiandaoyun` | mcp | 1 | 简道云零代码平台连接器，自然语言对话创建企业应用、沉淀表单、数据、处理流程审批，查询企业业务数据进行深度分析，帮助企业快速基于真实业务数据进行AI改造 Version: 1.0.0. |
| 金手指·AI广告投放 | `workbuddy/connectors/marketplace/connectors/jinshouzhi` | mcp | 2 | WorkBuddy 里的腾讯广告投放执行台：查数据、写需求单、生成投放深链、轻量调优。 |
| 金数据 | `workbuddy/connectors/marketplace/connectors/jinshuju` | mcp | 2 | 用自然语言在金数据（jinshuju.net）创建表单、表格、问卷、考试、报名、收款等各类场景应用：一句话生成表单与表格、批量处理数据、自动统计分析，零门槛快速搭建。 |
| 纠错大师 | `workbuddy/connectors/marketplace/connectors/jiucuodashi` | mcp | 2 | 连接纠错大师账号，查询授权孩子的最近错题，并自动生成单学科可打印的错题复习试卷。 Version: 1.0.0. |
| 九数云BI | `workbuddy/connectors/marketplace/connectors/jiushuyun` | mcp | 1 | 上传 Excel 或 CSV 表格，一键生成原生的可视化数据分析报告、仪表板、图表。 |
| JoyRead 双语绘本 | `workbuddy/connectors/marketplace/connectors/joyread-english` | mcp | 3 | 浏览 JoyRead 双语英语绘本库：按级别或主题找书，逐页点读原声朗读，支持亲子陪读、词汇复习、睡前故事三种陪读模式，并可将绘本导出为带朗读和双语字幕的 MP4 视频。 Version: 1.0.0. |
| 聚法-法律数据智能服务 | `workbuddy/connectors/marketplace/connectors/jufa-mcp-server` | mcp | 3 | 检索聚法司法案例、法律法规、检察文书、合同模板、招投标及企业风险数据。 Version: 1.0.0. |
| 天使医生 | `workbuddy/connectors/marketplace/connectors/jumper-kpi` | mcp | 4 | 通过自然语言查询当前天使医生账号有权限的医院经营指标、渠道分布、同比环比及人员 KPI 完成情况。 Version: 1.0.0. |
| 金山文档\|WPS云文档 | `workbuddy/connectors/marketplace/connectors/kdocs` | mcp | 571 | 金山文档官方 Skill。对话即操作——知识一键存入、碎片内容整理、接龙转表格、文档转 Markdown、表格美化、收发表生成，全在一句话内完成。 |
| 小蝶记账 | `workbuddy/connectors/marketplace/connectors/kingbot-xiaodie` | mcp | 21 | 小微企业智能经营连接器：支持自然语言录入销售、采购等业务数据、经营数据查询与分析、销售趋势洞察 Version: 1.0.0. |
| Kiwi 采购询价 | `workbuddy/connectors/marketplace/connectors/kiwi-sourcing` | mcp | 5 | 发现供应商、跨商家询价、比较报价并协商非绑定采购条款。 Version: 1.0.0. |
| Kling AI | `workbuddy/connectors/marketplace/connectors/kling-ai-plugin` | mcp | 14 | 一句话，让灵感从想法变成大片。可灵 AI 是面向创作者的 AI 生图与 AI 生视频连接器，可在 WorkBuddy 中直接用自然语言完成图片生成和视频生成，包括文生图、图生图、文生视频、图生视频、单镜头与多镜头视频。适合制作海报、插画、人像、商品图、电商主图、Listing 图、广告素材、产品展示视频、营销短片、电商短视频、种草视频、社交媒体视频和电影感创意视频，可用于淘宝、天猫、京东、拼多多、抖音、快手、小红书、TikTok、... |
| 同花顺快查企业数据 | `workbuddy/connectors/marketplace/connectors/kuaicha-search` | mcp | 2 | 查询中国企业工商、股权投资、经营司法风险、知识产权、招投标及新闻舆情数据。 |
| KUKA库卡专家 | `workbuddy/connectors/marketplace/connectors/kuka-service` | mcp | 2 | 库卡官方智能客服：把用户关于库卡工业机器人、协作机器人、自动化方案、产品选型、型号参数等问题，转交库卡智能问答客服并返回解答。 Version: 1.0.0. |
| 来也智能文档专家 | `workbuddy/connectors/marketplace/connectors/laiye-adp` | mcp | 7 | 让 Agent 直接读懂并处理任何业务文档。对话上传发票、订单、合同等文件即可完成内容识别、关键信息抽取并输出结构化结果。支持中国 30+ 票据（含验真）、海外多语言发票及 11 种常用证件，覆盖 PDF、图片、Word、Excel、OFD 等格式。 |
| 法保·全栈法律智能服务 | `workbuddy/connectors/marketplace/connectors/lawyerone` | mcp | 14 | 一站式垂类法律 AI 能力服务，支持法规检索、案例检索、合同智能审查、合同/单方文书生成、智能法律咨询、裁判结果预测、文件脱敏，实现法律文书处理、法律资料检索等全链路智能化。 Version: 1.0.0. |
| 询盘云CRM | `workbuddy/connectors/marketplace/connectors/leads-cloud-crm` | mcp | 3 | 通过 MCP 查询线索、客户、联系人、商机、订单、跟进、触点画像与 WhatsApp 会话。 Version: 1.0.0. |
| 乐檬零售 | `workbuddy/connectors/marketplace/connectors/lemon-agi` | mcp | 3 | 连接乐檬零售 AGI 能力平台，通过自然语言查询零售、批发、进销存、WMS、基础资料等业务数据。 Version: 1.0.0. |
| LemonClaw | `workbuddy/connectors/marketplace/connectors/lemonclaw` | cli | 2 | 连接柠檬云财务、进销存、业财、云代账和发票系统，支持查账、开票、业务查询、经营分析等企业经营场景。 |
| 乐享知识库 | `workbuddy/connectors/marketplace/connectors/lexiang` | connector | 28 | 搜索、创建和管理乐享知识库中的文档。支持导入 Markdown、按标签整理内容、追踪团队文档的更新动态。 |
| 猎隼AI智聘 | `workbuddy/connectors/marketplace/connectors/liesun` | mcp | 2 | 连接猎隼，科学选人、精准选人。人选对比、面试录音分析、在招进展和招聘漏斗，一句话快速评估还要不要往下推。 Version: 1.2.2. |
| 领星ERP | `workbuddy/connectors/marketplace/connectors/lingxing-mcp` | mcp | 3 | 使用自然语言查询和管理领星ERP中的店铺、库存、Listing、销售、利润、广告和运营数据。 |
| 零一运营 | `workbuddy/connectors/marketplace/connectors/lingyi-mcp` | mcp | 2 | 零一运营独家知识库：7大行业的视频号/私域的爆款内容案例库 + 零一300万份运营实战文档萃取。 Version: 1.4.0. |
| LinkFox | `workbuddy/connectors/marketplace/connectors/linkfox` | mcp | 140 | 跨境电商AI运营助手，涵盖竞品查询、市场调研、内容生成、营销广告、店铺运营、合规检测等多个子能力，提供多平台多数据源的跨境电商服务。 |
| ListingGood AI 推荐引擎 | `workbuddy/connectors/marketplace/connectors/listinggood` | mcp | 3 | 让亚马逊的 AI 主动推荐你的商品。提供 Listing 合规预检、AI 推荐就绪度评分、一句话生成高转化文案、深度合规扫描、差评根因分析与 POA 申诉信生成。 |
| Lovrabet CLI | `workbuddy/connectors/marketplace/connectors/lovrabet-cli` | cli | 33 | 连接企业系统、数据和流程，让AI完成工作，交付结果 Version: 2.1.23. |
| 励销CRM | `workbuddy/connectors/marketplace/connectors/lxcloud` | mcp | 1 | 用自然语言查询和录入励销CRM线索、客户、商机、合同、产品、回款开票、跟进记录等业务数据，轻松搞定销售全链路工作。 |
| 腾讯企点营销云 | `workbuddy/connectors/marketplace/connectors/magic-agent-token` | mcp | 3 | 腾讯企点营销云：人群圈选、选品配券、营销内容生成、企微运营与业务分析。当前连接器暂不提供完整营销活动策划流程。 Version: 1.1.1. |
| 条码生成器 | `workbuddy/connectors/marketplace/connectors/masocloud-barcode-generator` | mcp | 4 | 生成一维条形码、二维码与标签预览图，支持 CODE128、QR、DataMatrix、PDF417 等 9 种条码与 .alb 标签模板预览，可自定义尺寸、DPI、容错等级与是否显示文字。 Version: 1.0.0. |
| MasterGo 莫高设计 | `workbuddy/connectors/marketplace/connectors/mastergo-vibe-mcp` | mcp | 2 | 连接 MasterGo 画布，让 AI 进行设计、修改、同步和获取 D2C 代码。 |
| DRG/DIP 工具包（MedGroup） | `workbuddy/connectors/marketplace/connectors/medgroup-drgdip-toolkit` | mcp | 2 | 连接 MedGroup，查询 DRG/DIP 城市与规则、检索 ICD 编码、完成分组、结算测算及 CC/MCC 查询。 Version: 1.0.0. |
| 医脉通医学问答 | `workbuddy/connectors/marketplace/connectors/medlive-medical-qa` | mcp | 2 | 面向医生的医学问答连接器：用自然语言提问并获取带文献依据的完整答案，支持多轮追问、文档问答与历史回看。 Version: 1.0.0. |
| MeituHub AI影像创作 | `workbuddy/connectors/marketplace/connectors/meitu-ai` | cli | 3 | 在 WorkBuddy 中使用 MeituHub 完成图片与视频生成编辑、营销和电商内容创作，并运行自定义工作流。 Version: 0.1.3. |
| 美图 · 开拍 | `workbuddy/connectors/marketplace/connectors/meitu-kaipai` | cli | 4 | 美图公司出品的AI视频创作工具，支持一键网感剪辑、动态字幕和AI封面，让口播视频更有网感；还提供画质修复、水印消除、字幕消除、音频降噪等功能，轻松处理视频创作中的常见问题。 Version: 1.0.0. |
| 美团企业版 | `workbuddy/connectors/marketplace/connectors/meituan-for-business` | cli | 2 | 连接美团企业版账号，完成授权登录并在本机维护登录态，供后续企业服务能力复用。 Version: 1.0.2. |
| 萌啦数据Ozon-选品数据分析 | `workbuddy/connectors/marketplace/connectors/menglar-ozon` | mcp | 3 | 萌啦数据Ozon-选品数据分析提供 Ozon 类目、商品、关键词、品牌、店铺与大盘趋势等大数据查询能力，帮助跨境卖家完成选品与运营分析。 Version: 1.0.1. |
| 出海精灵·小元 | `workbuddy/connectors/marketplace/connectors/meo-xiaoyuan` | mcp | 6 | 面向中国外贸企业的 AI 出海助手：搜买家、盘客户、查同行、看市场数据，给出买家清单与跟进建议。 Version: 1.0.2. |
| MergerInfo 海外并购情报 | `workbuddy/connectors/marketplace/connectors/mergerinfo` | mcp | 4 | 查询海外待售标的、并购事件与巨头动向，以及指定企业近一年的交易动态。 Version: 0.2.0. |
| 芒果灵创 CLI | `workbuddy/connectors/marketplace/connectors/mglc` | cli | 10 | 通过命令行调用芒果灵创 AI 视频创作能力：可使用 30+ 模型生成图片、音频（音乐、音效、配音）和视频，管理音色库、项目、剧本、美术设定与分镜故事板，跟踪任务状态和生成结果。 Version: 0.1.13. |
| 秒哒应用搭建 | `workbuddy/connectors/marketplace/connectors/miaoda` | cli | 2 | 通过自然语言对话，即可完成网页、微信小程序及移动 App 的创建、预览、修改与发布上线，实现智能化、自动化、规模化的应用开发。 |
| Miki Cursor 素材库 | `workbuddy/connectors/marketplace/connectors/miki-cursor-catalog` | mcp | 2 | 查询 Miki Cursor 最新发布的光标样式、光标轨迹、光标宠物，以及不同宠物拥有的动作。 Version: 1.0.0. |
| 明白律师·合同风险审查 | `workbuddy/connectors/marketplace/connectors/mindbye-contract-review` | mcp | 2 | 基于头部律所40余年合同审查与争议处理实战经验沉淀，面向劳动、离婚、租赁、委托、买卖等中文合同，自动识别关键法律与交易风险，并生成规范审查报告、修改建议和 Word 批注版，提升审查效率和签署安全性。 Version: 1.0.0. |
| Moka HR 智能体 | `workbuddy/connectors/marketplace/connectors/moka` | mcp | 25 | 招聘和人事一体的 AI 同事，把查询与执行收进一个对话。人才推荐、招聘动态、考勤绩效、审批待办，一句话问清；候选人寻访、面试分析与面试官评估，一句话发起。 Version: 0.1.18. |
| 晨星 Morningstar | `workbuddy/connectors/marketplace/connectors/morningstar` | mcp | 2 | 接入晨星全球与中国基金数据，通过自然语言实现基金查询、筛选、分析与深度研究，以及组合穿透分析 |
| 东方财富妙想MCP | `workbuddy/connectors/marketplace/connectors/mx-ds-mcp` | mcp | 2 | 通过自然语言查询的金融投研 MCP 工具套件，依托东方财富数据源，提供A股、港股、美股、基金、债券、指数板块、宏观数据查询，具备多条件资产筛选、券商研报检索、全市场公告解析、金融资讯检索能力。 |
| 明源云客 | `workbuddy/connectors/marketplace/connectors/myunker-mcp` | mcp | 1 | 明源云客 AI 智能服务平台，以房地产营销垂直大模型为底座，统一整合客户、案场、渠道、视频营销全线产品数据，打通 AI 内容创作、直播获客、线索承接至成交全业务闭环。 |
| 摩知轮商标查询 | `workbuddy/connectors/marketplace/connectors/mzl-trademark` | mcp | 2 | 用自然语言检索商标：按名称、申请人、申请号、注册号、尼斯类别、法律状态、日期范围查询，覆盖中国及 110+ 海外国家/地区商标局；并支持以图搜图的图形近似检索。 Version: 1.0.0. |
| 销售易CRM | `workbuddy/connectors/marketplace/connectors/neo-crm` | mcp | 2 | 用自然语言查客户、推商机、盘线索、领公海、写跟进，一句话打通销售工作闭环。 |
| 销售易·易启 | `workbuddy/connectors/marketplace/connectors/neo-eakey` | mcp | 1 | 面向个人的AI销售伙伴，一句话帮你看懂客户、评估商机、发现风险，并把判断转化为下一步行动。 |
| NeoData金融数据库 | `workbuddy/connectors/marketplace/connectors/neodata` | mcp | 2 | 一键安装，免费使用，面向投研分析的专业金融数据服务。由腾讯金融科技链接各大权威来源，集成100+金融数据工具，覆盖股票、指数、板块、基金、债券、期货、期权、宏观、外汇、大宗商品等资产标的，提供行情报价、财务报表、资金流向、研报评级、盈利预测、舆情与事件公告等机构级数据，支持 A股 / 港股 / 美股 / 英股 / 日股 / 韩股 多市场与实时、历史双时效，口径统一、可溯源。 |
| Notion | `workbuddy/connectors/marketplace/connectors/notion` | connector | 64 | 创建、搜索和管理 Notion 工作区。用自然语言读取页面、查询数据库、更新内容、整理知识库。 |
| NovAI Studio | `workbuddy/connectors/marketplace/connectors/novai-studio` | mcp | 5 | 通过自然语言管理 AI 画布和素材，生成图片、视频和音频，并查询任务进度。 Version: 1.0.0. |
| NoxInfluencer 红人数据与营销运营 | `workbuddy/connectors/marketplace/connectors/noxinfluencer-cli` | cli | 8 | 通过自然语言调用 NoxInfluencer 的红人数据与营销运营能力：在 YouTube、TikTok、Instagram 上搜索并筛选红人，分析受众画像、内容表现与合作信号，获取联系方式，追踪内容数据，并管理 Campaign、CRM、邮件触达、品牌监测与导出任务，同时可查看配额与计费。 Version: 0.1.1. |
| NVIDIA App 本地助手（Windows） | `workbuddy/connectors/marketplace/connectors/nvapp-windows-local` | mcp | 8 | 用自然语言操作 NVIDIA App：查驱动更新、启动游戏、选择支持的画质与性能预设、录制游戏、截图、保存即时回放或显示帧率，也能管理支持的省电和静音功能。需在 Windows 上安装兼容的 NVIDIA App。 |
| OFD 文档转换 | `workbuddy/connectors/marketplace/connectors/ofdh-doc-convert` | mcp | 3 | 调用 ofdh.cn 在线转换服务，支持 OFD 与 PDF、Word、图片互转，并可提取 OFD 正文文本，适用于政务、企业等国产版式文档场景。 Version: 1.2.2. |
| OiiOii | `workbuddy/connectors/marketplace/connectors/oiioii` | cli | 2 | OiiOii 是全球首个 AI 动画/真人视频创作 Agent。只需描述创意，OiiOii 的影视级专业 Agents 团队就会即刻将零散的想法转化为完整的故事、广告成片；同时，OiiOii 还深度整合短漫剧工作流，无论是视频转绘出海、剧本本土化出海、多剧集拆分到成片，都能一键完成。 Version: 1.0.0. |
| 独行录 | `workbuddy/connectors/marketplace/connectors/opcmenu` | mcp | 4 | 让你的 Agent 在独行录找合作、筛选报名机会、跟进报名结果，并帮助主办方处理报名名单。 Version: 1.1.0. |
| 及刻智能·时空数据MCP | `workbuddy/connectors/marketplace/connectors/opendata` | mcp | 3 | 通过自然语言查询线下时空数据，提供区域热力、场景识别、客流分析、POI查询等能力，助力商业洞察、开店选址等应用场景。 |
| 东证期货 | `workbuddy/connectors/marketplace/connectors/orientfutures-mobile-knowledge-base` | mcp | 35 | 接入东证期货MCP服务，一句话检索经审核的期货知识、交易制度、风险投教、合约资料和开户注册说明，助力您高效进行投资决策。 Version: 0.4.4. |
| PandaData 金融数据 | `workbuddy/connectors/marketplace/connectors/pandadata` | mcp | 2 | 查询、整理和分析 A 股、期货、期权、港美股、基金、宏观经济及量化因子等金融数据，支持统计比较与趋势归纳。 |
| Repilot科研智能体 | `workbuddy/connectors/marketplace/connectors/paper-retrieval` | mcp | 2 | 课题申报书与PPT生成、快速文献检索、医学智能问答、综述报告生成，所有任务异步执行，支持状态轮询与取消。 Version: 2.0.1. |
| 智慧芽专利&文献融合检索 | `workbuddy/connectors/marketplace/connectors/patsnap-search` | mcp | 3 | 在智慧芽全球专利数据库和文献库中进行融合检索，支持自然语言、语义搜索、关键词检索和多维过滤，并获取专利或文献信息。 |
| Picset AI 电商设计 | `workbuddy/connectors/marketplace/connectors/picset-commerce-images` | mcp | 16 | Picset AI 电商设计：面向电商卖家、设计师和美工，提供四条独立功能线——电商套图（主图/详情图/套图/Listing/A+，含一张也走套图）、单图文生图/图生图（独立创意单图与图片编辑）、风格复刻（参考风格与商品图，含复刻电商主图）、Agent Canvas（画布承接与图片返回），以及连接器统一充值面板。覆盖淘宝、天猫、京东、拼多多、抖音、1688、小红书、TikTok、Amazon、Shopify、Temu、OZON、S... |
| Picset AI 视频创作 | `workbuddy/connectors/marketplace/connectors/picset-video-generation` | mcp | 10 | 用于 Picset AI 视频创作和独立人物三视图生成，包括商品带货视频生成、爆款视频复刻、有人物参考图或无人物参考图的正面/侧面/背面三视图生成。支持 UGC 种草、产品口播、带货短剧、产品演示、开箱种草、痛点解决、TVC 品牌广告等类型，并支持有声或静音视频、参考音频、固定模特和多条视频生成。该 Skill 会路由到生成视频、复刻视频或人物三视图子 Skill，根据用户提供的商品图、唯一主目标视频、人物素材和创作要求，完成用户... |
| 北大法宝·法律智能检索 | `workbuddy/connectors/marketplace/connectors/pkulaw` | mcp | 2 | 检索 + 核验一体：语义（自然语言描述）与关键词双模式检索法规、法条与司法案例；并可把文本中的法条引用与案号回北大法宝库逐条比对、对齐标准名称，输出带 pkulaw.com 原文链接的可溯源结果，专治法律幻觉。 |
| Plaud | `workbuddy/connectors/marketplace/connectors/plaud` | mcp | 2 | 连接 Plaud 录音与 AI：浏览查找录音、读取转写和 AI 摘要、汇总会议纪要，并生成跟进邮件与待办事项。 Version: 1.0.0. |
| 质数幻方·企业数据 | `workbuddy/connectors/marketplace/connectors/primematrix-company` | mcp | 3 | 提供企业主体的身份识别与基础信息查询服务，包含企业模糊搜索、受益所有人结果、企业基本信息、变更信息、企业联系方式、主要人员信息、企业股东信息等工具。 Version: 1.0.0. |
| OpenBoost 跨境数据 | `workbuddy/connectors/marketplace/connectors/proboost` | mcp | 4 | OpenBoost 跨境数据连接器：TikTok 达人/商品/视频分析、Amazon 选品与市场分析、全球专利检索一站式 MCP 工具集。 |
| 卓越智慧物业云平台 | `workbuddy/connectors/marketplace/connectors/property-saas` | mcp | 2 | 连接 V8 智慧物业云平台，提供业主/租户检索、档案查询、欠费查询、报修工单查询与缴费核销能力，服务物业客服与收费场景。 Version: 1.0.0. |
| 企查查 | `workbuddy/connectors/marketplace/connectors/qcc-company` | connector | 2 | 查询和核实企业工商登记信息。支持股东结构、实际控制人、受益所有人、高管团队、对外投资、财务数据、年报及上市信息查询，用自然语言快速完成企业身份核验与背景调查。 |
| 企查查·法律数据 | `workbuddy/connectors/marketplace/connectors/qcc-legal` | mcp | 2 | 检索与核验中国法律法规和司法案例。覆盖全量现行法律、行政法规、司法解释——法规级到法条级逐字正文，标注时效性与效力级别；海量裁判文书及 2.5 万+ 权威案例（最高法/最高检指导性案例、公报案例、典型案例）；并对文本中的法条与案号引用逐条回库核验、标注时效、生成可溯源超链。用自然语言完成法条依据查找、类案检索、原文调取与法律引用核验，从源头消除法条与案号幻觉。 Version: 1.0.0. |
| 企百科 | `workbuddy/connectors/marketplace/connectors/qibook-mcp` | mcp | 2 | 查询企业工商登记数据，支持企业模糊搜索、企业基本信息、受益所有人、股东、实际控制人、工商变更、联系方式、主要人员、分支机构、对外投资、年报、上市公司相关信息等企业尽职调查场景。 Version: 1.0.0. |
| 轻流 | `workbuddy/connectors/marketplace/connectors/qingflow` | mcp | 2 | 轻流无代码平台连接器。通过自然语言创建应用、管理表单数据、处理审批流程、查询和导出数据，一站式连接轻流全部能力。 |
| 青虎AI | `workbuddy/connectors/marketplace/connectors/qinghu-ai` | mcp | 3 | 连接青虎AI电商 SaaS，覆盖数据研究、选品与运营分析，以及 LinkPix 商品图、详情页、广告素材和短视频创作。 |
| 七色米进销存 | `workbuddy/connectors/marketplace/connectors/qisemierp` | mcp | 3 | 通过自然语言连接七色米进销存系统，随时查询商品、库存、客户、供应商及销售、采购、出入库等业务单据；支持销售统计、欠款对账、单据创建等操作，让业务数据问答即得。 Version: 1.0.0. |
| 启信慧眼 | `workbuddy/connectors/marketplace/connectors/qixinhuiyan-mcp` | mcp | 1 | 通过启信慧眼 MCP 接入企业全景数据能力，支持用户用自然语言完成企业搜索、工商画像、风险识别、经营动态、知识产权等商业情报分析。 |
| 启元机器人执行器 | `workbuddy/connectors/marketplace/connectors/qiyuan-robot-executor` | mcp | 3 | 让启元 Q1 机器人播报文字，并在现场安全确认后执行比心或向前走动作。 Version: 0.3.0. |
| QQ邮箱 | `workbuddy/connectors/marketplace/connectors/qq-mail` | connector | 2 | 收发、搜索和整理 QQ 邮件。用自然语言读取邮件内容、汇总邮件线程、管理文件夹。 |
| QVeris | `workbuddy/connectors/marketplace/connectors/qveris` | mcp | 3 | 通过一个 MCP 连接，发现、检查并调用 10,000+ 个实时数据、工具与外部服务能力。 Version: 1.0.0. |
| 企智多 | `workbuddy/connectors/marketplace/connectors/qzd-connector` | mcp | 2 | 接入企智多企业数据服务，支持通过自然语言查询企业基本概况等企业信息，快速了解企业背景。 Version: 1.0.0. |
| RealTrace 电商与社媒数据 | `workbuddy/connectors/marketplace/connectors/realtrace` | mcp | 3 | 查询与分析全球主流电商和社媒平台的商品、评论、内容、创作者与趋势数据。 Version: 1.0.1. |
| 睿答 | `workbuddy/connectors/marketplace/connectors/replygen` | mcp | 1 | 跨境电商多店铺客服 AI 连接器（Shopee 等）：用自然语言做每日买家问题总结、多店经营汇总、工单处理统计、会话洞察与订单快照报表。提供 25+ 只读/分析工具，跨店铺跨语种，买家隐私数据经脱敏后输出。 Version: 1.0.0. |
| 报告驿站 | `workbuddy/connectors/marketplace/connectors/reportgem-research` | mcp | 2 | 聚合数百家全球研究机构的千万级研报，并整合全球公司公告、美国SEC 文件，全球公司业绩会、学术论文，公开路演及图表，双语资料。经 RAG 结构化处理，减少 Token 消耗，提升检索效率和投研回答准确率。 Version: 1.0.0. |
| SalesNail AI 销售沙盘 | `workbuddy/connectors/marketplace/connectors/salesnail-instructor` | mcp | 8 | 为销售内训、销售年会和经销商大会定制 AI 大客户销售沙盘，支持分组演练、讲师带教与证据化复盘，帮助销售、售前和交付团队练习客户决策链分析与协同推进。 Version: 0.6.7. |
| SalesTouch 经营执行 | `workbuddy/connectors/marketplace/connectors/salestouch` | mcp | 8 | 通过自然语言连接 SalesTouch，完成组织资料、部门、角色权限、员工邀请、下属管理范围与销售流程配置，并处理 B2B/B2C 销售执行、非销售工作、绩效、内部调研和经营汇总。 |
| 致远互联协同办公服务 | `workbuddy/connectors/marketplace/connectors/seeyon-office-marketing-suite` | cli | 61 | 为企业提供协同办公、会议和业务协同能力，支持用户用自然语言完成会议创建与查询、协同发起与跟进、和业务数据分析。 Version: 1.0.0. |
| 聚宝赞 | `workbuddy/connectors/marketplace/connectors/sesunfox-gateway` | mcp | 3 | 通过自然语言查询聚宝赞的订单、商品、门店、优惠券、退款单、直播间和云仓库存数据。 Version: 1.0.1. |
| 用友智能服务（AI BaaS） | `workbuddy/connectors/marketplace/connectors/shanglv-mcp-gateway` | mcp | 2 | 通过用友银企联、税企联、商旅云等财务服务产品，为企业提供财务税务与银行资金数据服务，并提供企业商旅运营服务和行程服务。用自然语言完成企业的资金、税务、商旅的全面运营管理。 |
| VZOOM商易通-企业信息查询 | `workbuddy/connectors/marketplace/connectors/shangyitong` | mcp | 3 | 通过商易通 MCP 查询企业工商、股权与人员、上市信息、司法风险等企业数据，用自然语言做企业尽调、风险核查、客户画像。 Version: 1.0.1. |
| 天财商龙餐饮SaaS | `workbuddy/connectors/marketplace/connectors/shanlong-claw` | cli | 55 | 天财商龙成立于1998年，是中国餐饮数字化整体解决方案服务商。连接器提供公司介绍，以及会员数据概览、用户画像、消费、储值、复购、卡券、积分与营销活动分析（仅 CRM8）；并负责 CLI 安装与账号认证。业务查询使用当前账号权限范围内的固定只读接口。 Version: 1.0.168. |
| 纷享销客CRM | `workbuddy/connectors/marketplace/connectors/sharecrm` | mcp | 21 | 用自然语言查询客户、推进商机、写跟进记录、处理审批、建图表等，轻松搞定销售全链路工作。 |
| 知虾选品数据-Shopee虾皮大数据分析 | `workbuddy/connectors/marketplace/connectors/shopee-market-intelligence` | mcp | 3 | 通过知虾数据查询 Shopee 站点、类目、商品、店铺、品牌、趋势和热搜词，支持只读市场分析。 Version: 1.0.0. |
| 水滴信用-企业尽调 | `workbuddy/connectors/marketplace/connectors/shuidi-credit` | mcp | 1 | 水滴信用企业大数据全维度洞察，输入企业名称即可获取工商照面、股东股权、实控人穿透、司法风险、知识产权、招投标、税务信用、科创评分等全维度企业信息。适用于供应商准入尽调、企业背景核查、实控人与关联方穿透、风险预警监控、投资标的风险筛查等场景。 Version: 1.0.0. |
| 水滴信用-企业发现 | `workbuddy/connectors/marketplace/connectors/shuidi-discovery` | mcp | 1 | 基于企业数据仓库，面向企业发现与筛选场景：支持按工商信息、司法风险、荣誉资质、招投标、股权关系等多维条件组合筛选企业清单，可一键剔除失信/被执行/行政处罚等风险主体，也可从已知企业出发穿透挖掘关联企业群。适用于获客名单挖掘、供应商准入筛选、风险排查、区域产业分析等场景。 Version: 1.0.0. |
| 数字农人 | `workbuddy/connectors/marketplace/connectors/shunong-assistant` | cli | 3 | 连接数字农人，使用企业账号完成授权，查询登录状态，切换或退出当前连接。 Version: 0.1.1. |
| Sif MCP | `workbuddy/connectors/marketplace/connectors/sif-mcp` | mcp | 2 | 精准洞察亚马逊市场、流量与广告：适用于市场研究、选品调研、流量分析、广告架构拆解、竞品监控、反查流量词等亚马逊运营核心场景。不只返回数据，更直接给出分析与判断。由 Sif（sif.com）官方提供。 Version: 1.0.1. |
| eRoad·市场人才薪酬数据 | `workbuddy/connectors/marketplace/connectors/smartsalary` | mcp | 2 | 连接薪智（SmartSalary），把外部人才与薪酬市场数据带入现有工作流。随手查询竞品招聘变化、岗位人才供给、市场薪酬和人效指标，为招聘策略、岗位定薪及人才规划获得更清晰的外部参照，让招聘、定薪和人才规划不再只凭经验。 Version: 1.0.0. |
| 上奇产业通-企业动态追踪 | `workbuddy/connectors/marketplace/connectors/sq-company-dynamic` | mcp | 3 | 实时追踪企业全生命周期动态，覆盖投资设立、股权变动、创新平台、中标、知识产权、排名、迁移、资质认定、工商变更、上市、标准制定、招聘、拿地等维度，并提供企业实体匹配。 Version: 1.0.1. |
| scnet·科学文献洞察智能体 | `workbuddy/connectors/marketplace/connectors/sugon-scinsight-agent` | mcp | 2 | 学术文献检索 Connector：用于查论文、找文献、搜索相关研究和文献调研。对于明确的学术检索请求，优先使用 searchAcademicLiterature MCP 工具，聚合运行时已配置并启用的学术数据源，并返回可追溯的结构化文献元数据。 Version: 2.1.0. |
| 森浦qeubee金融数据 | `workbuddy/connectors/marketplace/connectors/sumscope-data` | mcp | 3 | 查询森浦固定收益市场数据：债券基础信息、一级发行、票据行情、舆情信息、发行人财务报表、宏观指标和交易日历。 Version: 1.0.1. |
| 医疗器械注册查询 | `workbuddy/connectors/marketplace/connectors/sungo-device-registry` | mcp | 2 | 输入公司名，查它在中国 NMPA、欧盟 EUDAMED、美国 FDA、英国 MHRA、加拿大、巴西、台湾、韩国、俄罗斯等 14 个官方注册库的注册数量、风险等级分布与器械明细。收录 68,000+ 家企业，每条记录逐条回查过厂商名。免费每天 100 次，领密钥后不限次。 Version: 1.0.0. |
| 辛孚物性库 | `workbuddy/connectors/marketplace/connectors/syspetro-service-22065846` | mcp | 6 | 辛孚物性库连接器：按名称、分子式或 CAS 检索化学组分，查询身份详情与分子量、纯组分基础物性，以及二元混合物物性数据可用性。 Version: 1.0.0. |
| 腾讯数字文化智能体 | `workbuddy/connectors/marketplace/connectors/tanyuan-assistant` | mcp | 2 | 基于文化可信知识库的智能体服务，提供世界遗产、博物馆藏品、甲骨文字形释义、学术文献等可溯源检索与创作辅助。覆盖申遗文本、考古数据、陶瓷基因库、纹样库等多模态知识，支持研究考据、策展辅助、文化科普与内容创作。 |
| TAPD | `workbuddy/connectors/marketplace/connectors/tapd` | connector | 2 | 管理需求、缺陷、任务和迭代。查询项目进度、拆分需求、流转状态、填写工时，覆盖需求到发布的研发全生命周期。 |
| TapNow | `workbuddy/connectors/marketplace/connectors/tapnow` | mcp | 2 | WorkBuddy 里的视觉创意工作室：由 TapNow Creative OS 多模型生成管线驱动，覆盖从创意构思到视觉设计的完整流程，产出直接可用、可继续编辑。适用于办公、营销、自媒体等场景。 Version: 0.1.2. |
| 同程程心 | `workbuddy/connectors/marketplace/connectors/tc-chengxin` | cli | 36 | 同程程心可通过自然语言查询机票、火车票、酒店、景点、度假产品等旅行资源，支持火空联程、智能交通推荐、特价机票搜索、景区门票预订，以及完整行程规划，显著提升出行效率。 |
| NextB2B贸易通MCP | `workbuddy/connectors/marketplace/connectors/tct-business-expert` | mcp | 9 | NextB2B贸易通MCP。用自然语言查商机询盘、待跟进线索、客户资产家底与业务员业绩，并按老板/业务员视角解读，为商机跟进、客户经营与业绩自查提供数据；需完成 MCP 联合授权后使用。 Version: 0.10.3. |
| TDengine | `workbuddy/connectors/marketplace/connectors/tdengine` | mcp | 28 | 连接 TDengine，管理工业数据，建立分析，监控事件，创建可视化面板，用 AI 问数与根因分析驱动工业决策。 Version: 1.0.1. |
| 通达信 | `workbuddy/connectors/marketplace/connectors/tdx-connector` | mcp | 2 | 通过通达信 MCP 查询全球股票行情数据、条件选股、研究报告、公告资讯和宏观信息。支持个股基本面分析、同行业对比和智能选股筛查。 |
| 企鹅教师助手 | `workbuddy/connectors/marketplace/connectors/teacher-assistant` | mcp | 1 | 企鹅教师助手负责处理基础性工作，基于课标和教学方法协助快速生成课程大纲、教案、课件及多模态教学资源，从而让教师腾出更多时间在课堂上进行创新 Version: 1.0.0. |
| Tec-Do 2.0 广告与增长情报 | `workbuddy/connectors/marketplace/connectors/tec-do` | mcp | 2 | 面向出海广告投放和增长团队的 AI 能力集合。 |
| 腾讯云数据湖计算 DLC | `workbuddy/connectors/marketplace/connectors/tencent-dlc` | connector | 2 | 通过 MCP 操作腾讯云数据湖计算（DLC）：执行 SQL / Spark SQL，浏览 Catalog、数据库、表与分区，管理 Spark 作业，查询任务与日志，诊断任务性能，查看引擎与用户权限。 |
| 腾讯文档 | `workbuddy/connectors/marketplace/connectors/tencent-docs` | connector | 1 | 创建、编辑和协作腾讯文档。用自然语言管理在线表格、文档和幻灯片，轻松完成内容查询、数据整理和团队协同。 |
| 腾讯文档企业版 | `workbuddy/connectors/marketplace/connectors/tencent-docs-oa` | connector | 1 | 创建、编辑和协作腾讯文档。用自然语言管理在线表格、文档和幻灯片，轻松完成内容查询、数据整理和团队协同。 |
| 腾讯健康NGES | `workbuddy/connectors/marketplace/connectors/tencent-health-nges` | mcp | 12 | 腾讯健康NGES医药营销智能助手，支持拜访与会议等业务数据洞察分析、医生画像查询、访前准备、访后记录写入及话术合规审核。 Version: 1.0.0. |
| 腾讯地图 | `workbuddy/connectors/marketplace/connectors/tencent-map` | mcp | 2 | 接入腾讯地图各类位置服务，包括地点搜索、路线规划（驾车/公交/步行/骑行）、地址正逆解析、沿途搜索和天气查询等。 |
| 腾讯地图·指南制作 | `workbuddy/connectors/marketplace/connectors/tencent-map-guide` | mcp | 2 | 用自然语言制作腾讯地图行程指南：创建、查询、更新、删除攻略。支持将攻略文本 / Markdown 内容智能转换为腾讯地图结构化行程指南数据格式（自动解析地点、补全 POI、生成路线），并一键保存同步到你的地图指南。 Version: 1.0.0. |
| 腾讯营销 | `workbuddy/connectors/marketplace/connectors/tencent-marketing-solution` | mcp | 2 | 连接腾讯营销，支持账户授权、组织与广告主管理、报表查询、创意审核与素材修复、广告知识库搜索、创意灵感推荐和视频号直播数据等能力，实现广告投放全链路智能化操作。 Version: 1.0.0. |
| 腾讯企点客服 | `workbuddy/connectors/marketplace/connectors/tencent-qidian-cs` | connector | 2 | 腾讯企点客服连接器：用自然语言处理工单（查询/创建/更新/状态变更）、查询坐席在线与实时接待、检索/拉取客户资料、拉取人工/大模型/文本机器人的会话记录和消息、查看客服实时监控、会话监控、客服满意度与响应度报表等数据。 |
| 腾讯问卷 | `workbuddy/connectors/marketplace/connectors/tencent-survey` | connector | 6 | 创建、管理和分析腾讯问卷。用自然语言快速生成问卷、查看回收数据、设置题目逻辑。 |
| 腾讯云数据仓库 TCHouse-C | `workbuddy/connectors/marketplace/connectors/tencent-tchouse-c` | mcp | 40 | 腾讯云数据仓库 TCHouse-C 智能运维与分析助手，用自然语言完成集群健康诊断、慢 SQL 分析、规格选型推荐、表结构设计与 NL2SQL 查询。 Version: 1.0.0. |
| 微云 | `workbuddy/connectors/marketplace/connectors/tencent-weiyun` | connector | 10 | 查看、下载、删除微云文件，并且提供上传文件到微云、生成分享链接能力，帮你管理微云文件 |
| 腾讯健康药箱企业数据洞察 | `workbuddy/connectors/marketplace/connectors/tencent-yaoxiang-bi` | mcp | 12 | 通过药箱企业数据洞察 MCP，查询合作药企的药箱品牌主页数据，按九大维度进行数据分析与洞察，生成 HTML 数据洞察报告，指引品牌宣传及运营策略。 Version: 1.0.1. |
| 腾讯营销投放 | `workbuddy/connectors/marketplace/connectors/tencentads` | cli | 154 | 腾讯营销投放 Skill，为大模型赋予广告投放管理能力：支持广告账户授权、广告/智投项目的创建与更新、创意管理、广告数据查询与分析、推广内容资产管理，以及操作日志查询等完整的广告投放全链路操作。 |
| TextIn xParse·智能文档解析 | `workbuddy/connectors/marketplace/connectors/textin-xparse` | cli | 11 | 支持 PDF、图片、Word、Excel、PPT、扫描件等文档的高精度高性能OCR/文字识别、解析、格式转换、提取与结构化抽取，可识别表格、公式、手写体并输出 Markdown 或 JSON，支持复杂表格版式还原和批量处理，每日免费 1000 页。更可支持文档图像鉴伪，精准判定图片真假。 |
| ThinkingAI AE | `workbuddy/connectors/marketplace/connectors/thinkingai-ae-cli` | cli | 633 | 通过自然语言查询和分析数据，并管理所选 ThinkingAI AE 环境中的业务资产。 Version: 1.0.0. |
| TikTok for Business | `workbuddy/connectors/marketplace/connectors/tiktok` | connector | 1 | TikTok for Business MCP Server 是基于模型上下文协议（MCP）搭建的标准化桥梁，助力开发者与广告主将 AI 智能代理直接对接 TikTok 广告平台。它将广告核心能力⸺广告活动管理、效果报表、受众配置以及创意运营，封装为一套稳定、可投入生产环境使用的工具。AI智能代理仅通过简洁结构化指令，即可完成 TikTok 广告的管理、优化与数据依托这套工具报表查询工作。 |
| 腾讯会议 | `workbuddy/connectors/marketplace/connectors/tmeet` | cli | 13 | 通过命令行创建、查询和管理腾讯会议。支持快速发起会议、查看日程安排、管理参会人员。 |
| 今日水印相机 | `workbuddy/connectors/marketplace/connectors/today-watermark-camera` | connector | 3 | 用自然语言查询和导出今日水印相机的团队照片，通过对话辅助完成照片归档、考勤核对、台账整理和照片统计。 |
| 同舟金融研究 | `workbuddy/connectors/marketplace/connectors/tongzhou-fin-research` | mcp | 2 | 连接公开行情、研报检索、行业图谱与同舟投研材料，为股市研究提供可复核证据。 Version: 0.21.2. |
| 畅捷通T+ | `workbuddy/connectors/marketplace/connectors/tplus-api` | mcp | 2 | 畅捷通 T+Cloud 自然语言操作入口：查询/管理销售订单、采购订单、库存单据、生产工单、财务凭证、报表及基础档案。 Version: 1.0.0. |
| 途牛旅行 | `workbuddy/connectors/marketplace/connectors/tuniu-travel` | cli | 2 | 通过 tuniu CLI 调用途牛开放平台旅行服务，支持机票、酒店、门票、火车票、邮轮、度假产品和打包订。 |
| Tushare | `workbuddy/connectors/marketplace/connectors/tushare` | mcp | 3 | Tushare 金融数据服务，支持 A股、指数、ETF/基金、财务、估值、资金流、公告新闻、板块概念与宏观数据等研究工作。 Version: 1.0.0. |
| 天眼查 | `workbuddy/connectors/marketplace/connectors/tyc-mcp` | mcp | 2 | 通过天眼查 MCP 查询多维度企业数据。支持工商登记、股东结构、司法风险、知识产权、董监高、经营数据等 160+ 项企业数据能力，用自然语言完成企业尽调与商业情报分析。 |
| 优品・AI投顾工作台 | `workbuddy/connectors/marketplace/connectors/uptgai-manager` | mcp | 1 | 连接优品・AI投顾工作台，查询推荐股票与投顾策略，跟踪自选股与持仓表现，辅助完成选股、复盘和客户服务。 Version: 1.0.0. |
| UU跑腿 | `workbuddy/connectors/marketplace/connectors/uupt` | cli | 2 | 通过自然语言使用 UU跑腿：同城配送与帮帮服务，支持询价、下单、查单、取消、跑男追踪和领取优惠券 Version: 1.1.0. |
| 飞常准 | `workbuddy/connectors/marketplace/connectors/variflight-mcp` | mcp | 7 | 查询航班动态、运行分析、逐航班机票与价格、机场与航司服务，以及当前用户的行程、统计和航班关注信息。用户身份由 C 端 MCP Key 确定。 Version: 1.2.2. |
| 予非AI知识大脑 | `workbuddy/connectors/marketplace/connectors/verya-knowledgebase` | mcp | 3 | 连接后支持搜索、读取和总结予非AI知识大脑中的知识资料，融合知识图谱关联分析，通过自然语言快速定位文档、洞察实体关系并梳理知识脉络。 Version: 1.0.0. |
| viaim | `workbuddy/connectors/marketplace/connectors/viaim` | mcp | 2 | 连接 viaim App，查询或按关键词搜索录音记录，读取转写内容与 AI 摘要，查看最近更新的记录，并整理会议纪要和待办事项。 Version: 1.0.1. |
| VibeKnow CLI | `workbuddy/connectors/marketplace/connectors/vibeknow-cli` | cli | 6 | 把文档、网页、PPT，或直接粘在对话里的一段文字，变成带旁白的成片。五种创作模式：灵活创作、图解视频、PPT 逐页讲解、手绘动画、一键成片，也可锁定原稿逐字照念。生成过程可分段查看进度，成片后能免费读取讲稿、调整字幕与背景音乐，并把导出的 mp4 直接发回对话。 Version: 0.9.1. |
| VOKO智能体商店 | `workbuddy/connectors/marketplace/connectors/voko-guest` | mcp | 2 | 发现或查找适合的 AI 智能体，了解其能力、发送消息并读取回复，借助外部智能体完成任务。 Version: 1.0.0. |
| 旺小宝 | `workbuddy/connectors/marketplace/connectors/wangxiaobao` | cli | 34 | 用自然语言查询旺小宝业务数据：客户、来访、录音、关注点/抗性点、知识库、量子看板 KPI 与问数。 Version: 1.0.0. |
| WaveNote | `workbuddy/connectors/marketplace/connectors/wavenote-audio` | mcp | 2 | 读取 WaveNote 录音、转写及总结内容，并为指定录音发起转写和总结任务。 Version: 1.0.0. |
| 泛微eteams数智办公云平台 | `workbuddy/connectors/marketplace/connectors/weaver-eteams-connector` | cli | 177 | 用自然语言办理泛微 eteams 上的日常办公事务。覆盖流程审批、日程会议、邮件消息、周报月报、项目任务、客户商机、人事考勤、费控发票、档案与资产。 Version: 1.0.0. |
| 企业微信 | `workbuddy/connectors/marketplace/connectors/wecom` | cli | 97 | 企业微信官方 CLI 套件，覆盖消息、邮件、文档、待办、日程、会议、微盘、通讯录等业务功能。支持机器人主动通知、新建与读取文档、文档搜索、新建管理日程、预约与获取会议信息、新建跟进待办、上传与获取微盘文件、邮件读取与发送等能力 |
| 微伴助手 | `workbuddy/connectors/marketplace/connectors/weiban-agent-mcp` | mcp | 3 | 通过自然语言查询授权范围内的员工、客户、消息存档和工单，获取业务上下文并执行经确认的受控操作。 Version: 1.3.0. |
| 微盛企微管家SCRM | `workbuddy/connectors/marketplace/connectors/weisheng-scrm` | mcp | 4 | 查询或管理企业微信中的客户信息、客户标签、客户群、营销素材、活码、群发、跟进记录、联系人、商机、汇报、抽奖、客户日程、聊天记录等业务能力。 |
| 微生活 AI 工作台 | `workbuddy/connectors/marketplace/connectors/welife-ai-workbench-connector` | mcp | 4 | 连接微生活 AI 工作台，在授权范围内查询餐饮商户经营指标、六类标准经营报告、一键经营诊断和营销活动数据，支持门店对比、消费趋势、会员增长与流失风险分析。 Version: 2.1.1. |
| 腾讯自选股 | `workbuddy/connectors/marketplace/connectors/westock-mcp` | mcp | 2 | 直连腾讯自选股，实时掌握毫秒级行情与资金动态，用自然语言分析自选数据、设置股价提醒、管理模拟交易，轻松搞定盯盘与投资决策。 |
| Wind Alice 万得金融数据 | `workbuddy/connectors/marketplace/connectors/wind-finance` | mcp | 3 | 全量开放万得（Wind）金融数据与工具能力，覆盖沪深港美等全球60多个国家地区的股票、基金、债券、商品、指数、经济数据与万得金融模型与工具集。让WorkBuddy变身金融分析专家，成为具备数据穿透、投研分析、风险决策等多维金融能力的专业智能体。 Version: 1.2.0. |
| 百智WiseNote | `workbuddy/connectors/marketplace/connectors/wisenote` | mcp | 2 | 通过用户授权读取百智 WiseNote 会议列表、会议详情摘要和会议转写内容。 |
| 威科先行 | `workbuddy/connectors/marketplace/connectors/wk-workbuddy` | mcp | 2 | 威科先行依托全面、准确、及时更新的法规、案例等法律数据研发的MCP服务，支持语义检索、关键词检索等场景。 |
| 微脉体重管理 | `workbuddy/connectors/marketplace/connectors/wm-weight-manage` | mcp | 5 | 生成个性化成人体重管理方案，渲染为可打卡的独立 HTML 页面：分阶段目标、饮食运动建议、餐食照片热量分析、本地体重记录。 Version: 1.0.1. |
| WorkRally | `workbuddy/connectors/marketplace/connectors/workrally1` | mcp | 265 | 用 WorkRally MCP 做剧集前期、批量生图、画布整理、字幕烧制与资产验收。 Version: 0.5.1. |
| 微盟 WOS CLI | `workbuddy/connectors/marketplace/connectors/woscli` | cli | 5 | 通过自然语言调用 woscli 操作微盟 WOS 业务能力：查询与管理订单、商品、客户资料、营销活动、数据看板等。 |
| 腾讯数电发票 | `workbuddy/connectors/marketplace/connectors/wpe-general-connector` | mcp | 22 | 一站式数电发票开具、交付、查验、入账等，助力企业高效开展发票业务。 Version: 1.0.2. |
| WPS知识库 | `workbuddy/connectors/marketplace/connectors/wps-knowledgebase` | cli | 4 | 通过自然语言操作 WPS/zhishi 云端知识库：列出知识库、浏览文件树、智能问答、分享链接，以及文件/文件夹增删改查。 |
| 华尔街见闻 | `workbuddy/connectors/marketplace/connectors/wscnmcp-token` | mcp | 3 | 华尔街见闻MCP —— 提供 A 股大涨股异动归因与华尔街见闻全球财经资讯查询能力。支持查询近两个月的大涨个股（含上涨原因、关联板块、板块异动描述，自动按板块归类），以及华尔街见闻全球资讯列表与文章详情，帮助快速抓住当日市场主线、追踪财经热点。 Version: 1.0.0. |
| 新华财经资讯MCP | `workbuddy/connectors/marketplace/connectors/xhcj-mcp-announcements-news-policy` | mcp | 3 | 公告、新闻、政策数据，包含股票资讯、板块资讯、热点新闻、资讯搜索、大宗快讯、外汇快讯、股票快讯、公告关键词检索、政策向量检索等 Version: 1.0.0. |
| 小鹅通 | `workbuddy/connectors/marketplace/connectors/xiaoe-cloud-cli` | connector | 2 | 用自然语言管理小鹅通店铺：查询课程与学员，创建和编辑课程，查看订单，并查找或上传图片、音频、电子书和文档素材。 |
| 小裂变 SCRM | `workbuddy/connectors/marketplace/connectors/xiaoliebian-scrm` | mcp | 3 | 小裂变SCRM连接器，帮你查询企业微信中的私域客户、客户群数据，制定朋友圈发布任务、群发触达任务，自动统计员工聊天排行榜，总结员工和客户聊天内容，小裂变SCRM&WorkBuddy帮你做好企业微信私域运营 |
| 小律同学 AI 法律检索 | `workbuddy/connectors/marketplace/connectors/xiaolv-law-search` | mcp | 2 | 检索国内/国际法律法规、司法解释、量刑标准、指导案例（覆盖 168 国家/地区），支持法律文书起草（697 类模板）、编辑与合同审查。适合法律咨询、跨境合规、量刑赔偿计算、文书生成等场景。每次调用消耗积分，新用户注册即送 1688 积分。 Version: 1.0.0. |
| 法国协会网 | `workbuddy/connectors/marketplace/connectors/xiehui-fr` | mcp | 2 | 查询法国内政部官方登记库收录的 3,640 家华人协会，可按名称、城市、类型搜索，查看认证状态与登记信息，联系前先核实。 |
| 天创信用星图MCP | `workbuddy/connectors/marketplace/connectors/xingtu-claw-risk` | mcp | 2 | 企业风险 AI 分析助手，用自然语言识别企业所属行业、分析企业间关联方关系（股权/实控人/担保/共同投资）。 |
| 新客来了数据分析企业版 | `workbuddy/connectors/marketplace/connectors/xinke-laile-analytics-enterprise` | mcp | 3 | 通过自然语言分析企业自己的线索趋势、渠道来源和推送效果。 Version: 1.0.0. |
| 迪安智能科研云 | `workbuddy/connectors/marketplace/connectors/xmed-figure-mcp` | mcp | 2 | 科研数据可视化：火山图、PCA、富集分析、生存分析，自动匹配发表级输出 Version: 1.0.10. |
| Xmind思维导图 | `workbuddy/connectors/marketplace/connectors/xmind` | mcp | 2 | 通过 AI 对话创建、读取和编辑 Xmind 在线思维导图。 Version: 1.0.0. |
| 薪人薪事 | `workbuddy/connectors/marketplace/connectors/xrxs` | mcp | 4 | 通过自然语言管理薪人薪事员工入职、离职及考勤月度报表归档等 HR 场景。 Version: 1.0.0. |
| 选片PRO云档期 | `workbuddy/connectors/marketplace/connectors/xuanpian-schedule` | mcp | 3 | 连接影楼选片系统，通过自然语言查询拍摄档期：支持整月每日可约汇总、单日各时间段档位明细，并支持使用绑定码绑定选片系统账号。 |
| 言序 | `workbuddy/connectors/marketplace/connectors/yanxu` | mcp | 2 | 通过自然语言创作并发布微信公众号文章：查询已绑定的公众号与样式主题、按主题排版建稿、一键推送到公众号草稿箱。 Version: 1.0.1. |
| 易查云贸易数据 | `workbuddy/connectors/marketplace/connectors/yichayun-trade-data` | mcp | 2 | 全球海关贸易数据智能查询:按产品找海外采购商与供应商,分析市场趋势与伙伴国份额,查企业画像与资信。数据来自提单与官方统计原始记录,带明确时间口径,可追溯、可对账。 |
| 盈米MCP | `workbuddy/connectors/marketplace/connectors/yingmi-mcp` | mcp | 3 | 查询基金与市场数据，完成基金研究、组合分析、财富规划及金融内容生成。 |
| 翼小客 | `workbuddy/connectors/marketplace/connectors/yixiaoke` | mcp | 2 | 用自然语言查客户、商机、订单，写跟进、处理待办审批，查通话/短信/微信记录，管设备工牌，看风控统计，打通销售全链路。 Version: 1.0.0. |
| 智客AI · 对公(To B)营销助手 | `workbuddy/connectors/marketplace/connectors/youshu-bd-mate` | mcp | 2 | 对公营销助手是基于企业全维数据构建的对公营销智能助手，提供从生成访前一页纸、访前客情报告、产品找客、关键人画像、营销话术及按企荐品的完整展业闭环能力。 Version: 2.0.2. |
| 有赞 | `workbuddy/connectors/marketplace/connectors/youzan-workbuddy` | mcp | 19 | 通过 MCP 查询有赞店铺商品、订单、会员、营销、供应链、流量等 16 个业务域数据，支持订单、会员等原始数据导出，全部能力只读。 |
| 生意专家 | `workbuddy/connectors/marketplace/connectors/yuanbei-hub` | mcp | 3 | 连锁门店经营数据助手，支持销售排名、库存补货、会员分析和经营诊断等查询 Version: 1.0.0. |
| 华宇元典法律数据 | `workbuddy/connectors/marketplace/connectors/yuandian-mcp` | mcp | 1 | 华宇元典法律数据为智能体提供法律法规、案例文书、企业信息 MCP 工具能力。 |
| 云净透析中心CRM与经营管理系统 | `workbuddy/connectors/marketplace/connectors/yunjing-crm-analytics` | mcp | 3 | 在当前 CRM 权限范围内查询脱敏的经营、患者、客户、工单及中心运营汇总数据。 Version: 0.1.0. |
| 云客AI工作手机 | `workbuddy/connectors/marketplace/connectors/yunke-cli` | cli | 2 | 提供真实手机的数据读取与设备控制能力。AI 自动采集通话与录音，沉淀全量沟通数据驱动销售分析；同时允许 AI 直接操控手机拨打电话、发短信、操作 APP，把实体手机变成 Agent 的硬件执行单元。 |
| 云图外贸工作台 | `workbuddy/connectors/marketplace/connectors/yuntu-ft-workbench` | mcp | 1 | 把 WorkBuddy 技能生成的外贸开发结果（买家报告/全球搜索/情报卡/跟进）自动写回「云图外贸工作台」工作台，基于 H5 + EdgeOne KV 云存储，数据主权归属用户（BYOC）。 |
| 云之校园号 | `workbuddy/connectors/marketplace/connectors/yunzhi-campus` | mcp | 2 | 查询校园号教师本人的请假记录，包括请假时间、类型、原因、审批状态与当前审批节点，并查看所在学校可用的请假流程。 Version: 1.0.1. |
| 云指建站MCP服务 | `workbuddy/connectors/marketplace/connectors/yunzhi-mcp` | mcp | 2 | 通过 MCP 服务创建/修改网站页面，管理网站的产品、文章等数据，与 Skill 结合实现从需求到页面的端到端自动交付，大幅简化建站流程。 Version: 1.0.0. |
| 云帐房 | `workbuddy/connectors/marketplace/connectors/yzf-general-mcp-server` | mcp | 6 | 一句话把票开了、税报了、政策理清了，省的是钱，更是心。 Version: 1.1.1. |
| 天润融通·Zenava | `workbuddy/connectors/marketplace/connectors/zenava` | cli | 5 | 连接天润客服平台，通过自然语言管理系统全产品能力：在各功能模块内导入数据、查询数据明细&数据报表、完整相关流程配置、搭建语音/文本/分析智能体。 Version: 0.1.2. |
| 中兴新云AI智报 | `workbuddy/connectors/marketplace/connectors/zfs-fssc-ai` | mcp | 3 | 财务云 AI 报销助手：用自然语言完成报销申请、发票查询识别、报销单查询与费用审批等操作。 |
| 账三丰 | `workbuddy/connectors/marketplace/connectors/zhangsanfeng` | mcp | 2 | 连接账三丰（财务云 / 进销存 / MES）。用自然语言查利润表、资产负债表、往来账龄、采购销售单据、库存、工单与报工进度；也能一句话生成记账凭证或开采购入库单草稿，确认后入账。 Version: 1.0.0. |
| 知识星球 | `workbuddy/connectors/marketplace/connectors/zsxq` | cli | 2 | 用自然语言管理知识星球：浏览星球内容、发帖评论、搜索主题、回答问题、管理笔记、查看用户信息。 |
| 中望3D MCP | `workbuddy/connectors/marketplace/connectors/zw3d-mcp` | connector | 2 | 用自然语言驱动中望3D，让设计回归思考本身。 |
| 中望CAD MCP | `workbuddy/connectors/marketplace/connectors/zwcad-mcp` | mcp | 2 | 用自然语言直接操作中望CAD（ZWCAD）二维平台与中望机械CAD，自动绘制、查询、标注和管理 DWG 图纸。 |
| 装修云管家 | `workbuddy/connectors/marketplace/connectors/zxygj-business-data` | mcp | 2 | 通过自然语言安全查询装修云管家中的客户、订单及其他业务对象数据。 |

## 最近变更

| Date | Change Log | Summary |
| --- | --- | --- |
| 2026-09-25-085343 | [2026-09-25-085343](workbuddy/change-logs/2026-09-25-085343.md) | WorkBuddy 本次同步新增 593 个文件、修改 108 个文件、删除 9 个文件。 新增条目：connectors/marketplace/connectors/chainlon-geo-mcp, connectors/marketplace/connectors/duoguan-course, connectors/marketplace/c... |
| 2026-09-23-180002 | [2026-09-23-180002](workbuddy/change-logs/2026-09-23-180002.md) | WorkBuddy 本次同步新增 540 个文件、修改 9 个文件、删除 196 个文件。 新增条目：connectors/marketplace/connectors/beatapi-beatdesign, connectors/marketplace/connectors/cloudhub, connectors/marketplace/conne... |
| 2026-09-22-180002 | [2026-09-22-180002](workbuddy/change-logs/2026-09-22-180002.md) | WorkBuddy 本次同步新增 679 个文件、修改 62 个文件、删除 2 个文件。 新增条目：connectors/marketplace/connectors/aholo-lux3d, connectors/marketplace/connectors/meituan-for-business, connectors/marketplace/c... |
| 2026-09-21-180001 | [2026-09-21-180001](workbuddy/change-logs/2026-09-21-180001.md) | WorkBuddy 本次同步新增 20 个文件、修改 42 个文件、删除 0 个文件。 新增条目：connectors/marketplace/connectors/3chat-customer-growth, connectors/marketplace/connectors/charge-order-query, connectors/market... |
| 2026-09-20-180005 | [2026-09-20-180005](workbuddy/change-logs/2026-09-20-180005.md) | WorkBuddy 本次同步新增 22 个文件、修改 19 个文件、删除 63 个文件。 新增条目：connectors/marketplace/connectors/gt-generate-sql-data, connectors/marketplace/connectors/kuka-service, connectors/marketplace/... |
| 2026-09-19-180006 | [2026-09-19-180006](workbuddy/change-logs/2026-09-19-180006.md) | WorkBuddy 本次同步新增 292 个文件、修改 242 个文件、删除 158 个文件。 新增条目：connectors/marketplace/connectors/candao-age, connectors/marketplace/connectors/dami-external-mcp, connectors/marketplace/co... |
| 2026-09-16-180007 | [2026-09-16-180007](workbuddy/change-logs/2026-09-16-180007.md) | WorkBuddy 本次同步新增 413 个文件、修改 70 个文件、删除 36 个文件。 新增条目：connectors/marketplace/connectors/51shebao-hr-tools, connectors/marketplace/connectors/connector-workshop, connectors/marketpl... |
| 2026-09-13-180003 | [2026-09-13-180003](workbuddy/change-logs/2026-09-13-180003.md) | WorkBuddy 本次同步新增 5 个文件、修改 0 个文件、删除 0 个文件。 新增条目：skills/wedding-handcard-creator。 受影响范围：skills/wedding-handcard-creator。 |
| 2026-09-12-180007 | [2026-09-12-180007](workbuddy/change-logs/2026-09-12-180007.md) | WorkBuddy 本次同步新增 443 个文件、修改 190 个文件、删除 96 个文件。 新增条目：cb_teams_experts/finance-data, connectors/marketplace/connectors/24haowan, connectors/marketplace/connectors/24haowan-space,... |
| 2026-09-05-180002 | [2026-09-05-180002](workbuddy/change-logs/2026-09-05-180002.md) | WorkBuddy 本次同步新增 31 个文件、修改 13 个文件、删除 1 个文件。 新增条目：connectors/marketplace/connectors/aidd-saas, connectors/marketplace/connectors/futu-mcp, connectors/marketplace/connectors/tence... |
| 2026-09-04-180001 | [2026-09-04-180001](workbuddy/change-logs/2026-09-04-180001.md) | WorkBuddy 本次同步新增 94 个文件、修改 19 个文件、删除 0 个文件。 新增条目：connectors/marketplace/connectors/laiye-adp, connectors/marketplace/connectors/magic-agent-token, connectors/marketplace/connect... |
| 2026-09-03-180002 | [2026-09-03-180002](workbuddy/change-logs/2026-09-03-180002.md) | WorkBuddy 本次同步新增 9 个文件、修改 16 个文件、删除 0 个文件。 新增条目：connectors/marketplace/connectors/dnb-global-data, connectors/marketplace/connectors/intco-ai-platform。 受影响范围：connectors/marketpl... |
| 2026-09-02-223755 | [2026-09-02-223755](workbuddy/change-logs/2026-09-02-223755.md) | WorkBuddy 本次同步新增 4306 个文件、修改 171 个文件、删除 2 个文件。 新增条目：connectors/marketplace/connectors/deeplink, connectors/marketplace/connectors/dramabuddy, connectors/marketplace/connectors/h... |
| 2026-09-02-180002 | [2026-09-02-180002](workbuddy/change-logs/2026-09-02-180002.md) | WorkBuddy 本次同步新增 21 个文件、修改 27 个文件、删除 1 个文件。 新增条目：connectors/marketplace/connectors/shanlong-claw, connectors/marketplace/connectors/tencent-map-guide。 受影响范围：connectors/marketpla... |
| 2026-09-01-180001 | [2026-09-01-180001](workbuddy/change-logs/2026-09-01-180001.md) | WorkBuddy 本次同步新增 58 个文件、修改 31 个文件、删除 24 个文件。 新增条目：connectors/marketplace/connectors/aimoderator, connectors/marketplace/connectors/today-watermark-camera, connectors/marketplace... |
| 2026-08-31-180002 | [2026-08-31-180002](workbuddy/change-logs/2026-08-31-180002.md) | WorkBuddy 本次同步新增 26 个文件、修改 6 个文件、删除 10 个文件。 新增条目：connectors/marketplace/connectors/databuddy, connectors/marketplace/connectors/jinshouzhi。 移除条目已归档：connectors/marketplace/connec... |
| 2026-08-30-212148 | [2026-08-30-212148](workbuddy/change-logs/2026-08-30-212148.md) | WorkBuddy 本次同步新增 2677 个文件、修改 0 个文件、删除 0 个文件。 新增条目：connectors/default, connectors/marketplace/.codebuddy-connector, connectors/marketplace/connectors/77ircloud, connectors/market... |
| 2026-08-20-180002 | [2026-08-20-180002](workbuddy/change-logs/2026-08-20-180002.md) | WorkBuddy 本次同步新增 0 个文件、修改 1 个文件、删除 0 个文件。 受影响范围：skills/aihot__skillhub。 |
| 2026-08-13-180002 | [2026-08-13-180002](workbuddy/change-logs/2026-08-13-180002.md) | WorkBuddy 本次同步新增 13 个文件、修改 4 个文件、删除 235 个文件。 新增条目：skills/paper-reader, skills/paper-reader.zip, skills/paper-rebuttal, skills/paper-reviewer, skills/research-lineage-map。 移除条目已归... |
| 2026-08-11-180003 | [2026-08-11-180003](workbuddy/change-logs/2026-08-11-180003.md) | WorkBuddy 本次同步新增 54 个文件、修改 0 个文件、删除 0 个文件。 新增条目：experts/mvp-dev-expert-team。 受影响范围：experts/mvp-dev-expert-team。 |
