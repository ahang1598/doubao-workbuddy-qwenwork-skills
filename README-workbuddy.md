# WorkBuddy Skills And Experts

本文件由 `scripts/sync_platform.py --platform workbuddy` 自动生成，整理 `workbuddy/` 下同步的技能、专家团和插件索引。

## 同步概览

- 平台目录：`workbuddy/`
- 定时任务：`WorkbuddySkillsDailySync`，每天 18:00 运行
- 当前索引条目数：492
- 当前索引文件数：15159
- 最近变更：[2026-09-03-180002](workbuddy/change-logs/2026-09-03-180002.md) - WorkBuddy 本次同步新增 9 个文件、修改 16 个文件、删除 0 个文件。 新增条目：connectors/marketplace/connectors/dnb-global-data, connectors/marketplace/connectors/intco-ai-platform。 受影响范围：connectors/marketpl...

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

### Connectors / Marketplace

| Name | Directory | Category | Files | Description |
| --- | --- | --- | ---: | --- |
| 铱云AI供应链 | `workbuddy/connectors/marketplace/connectors/77ircloud` | cli | 66 | 通过自然语言管理铱云供应链：支持订单全链路操作，以及客户、商品、仓库库存、员工组织、资金账户、数据导出、经营统计和预警明细的查询分析。 |
| AgentEarth | `workbuddy/connectors/marketplace/connectors/agent-earth` | mcp | 3 | AgentEarth 是 AI 助手调用全球专家级工具的统一平台。聚合 1400+ 专业 API，覆盖实时金融行情、电商与社媒数据、AI 生图与视频生成、学术论文与专利、地图与出行等真实业务场景。一次接入、自然语言调用。 Version: 1.0.0. |
| AI-HIVE | `workbuddy/connectors/marketplace/connectors/ai-hive` | connector | 29 | 连接全球 100+ 顶尖 AI 模型（Seedance 2.5、H3 (MiniMax)、Happyhorse、GPT-image、Nano-Banana、Deepseek、Kimi 等），一键搞定文本、图像、视频创作。 |
| 智慧记AI进销存 | `workbuddy/connectors/marketplace/connectors/ailit` | cli | 12 | 结合您的进销存业务数据，可实现成批量对账、销售开单和批量创建商品，覆盖销售、采购、库存、收银、对账及经营分析等多种业务场景。 Version: 0.8.1. |
| 思研平台 | `workbuddy/connectors/marketplace/connectors/aimoderator` | connector | 2 | 用自然语言快速创建 AI 访谈项目：提供标题、背景、大纲（及可选开场白），即可在思研平台生成访谈项目并返回可直接分享的访谈链接。 |
| Alpha派投研助手 | `workbuddy/connectors/marketplace/connectors/alphapai-lite-mcp` | mcp | 10 | Alpha派·Lite版是讯兔科技为金融工作者、投资者量身打造的AI助理，掌握深度行业、公司研究分析与大类资产、市场策略专业解读能力，并具备专业的写报告、画PPT、做图表、写纪要等金融白领必备技能。 Version: 1.0.0. |
| 腾讯健康全周期管理平台 | `workbuddy/connectors/marketplace/connectors/archive-hospital-mcp` | mcp | 2 | 全周期管理平台机构端的数据查询MCP连接器，覆盖医疗数据、管理任务、对话沟通等业务域的查询能力，所有数据仅在对话内分析、不落盘不导出。 Version: 2.0.0. |
| 向日葵远程控制 | `workbuddy/connectors/marketplace/connectors/awesun` | cli | 5 | 通过命令行管理远端设备，实时监测在线状态、秒级发起远程控制、快速传输文件及远程截屏。零部署、免更新，轻松实现智能批量运维。 |
| 百度网盘 | `workbuddy/connectors/marketplace/connectors/baidu-netdisk` | mcp | 2 | 连接百度网盘，支持文件与分类浏览、关键词及语义检索、文件和文件夹管理、创建分享链接、查询容量，以及保存文本内容或通过 URL 转存文件。 |
| 百晓智能 | `workbuddy/connectors/marketplace/connectors/baixiao-mcp` | mcp | 3 | 中英文学术检索: 搜索期刊论文、专著、政策文件；查阅最新基金招投标信息；核实参考文献真伪、追溯引用；推荐投稿期刊与审稿人。 Version: 1.0.0. |
| 八爪鱼 | `workbuddy/connectors/marketplace/connectors/bazhuayu` | mcp | 2 | 用自然语言驱动八爪鱼云采集：搜索模板、启动任务、查询进度、导出结构化数据，并管理已有任务。 |
| 北森AI · HR专家 | `workbuddy/connectors/marketplace/connectors/beisen-cli` | cli | 44 | 依托北森HR SaaS平台，把审批、招聘进展、员工档案、绩效履历、考勤假期、组织架构和企业制度等近百个人力场景装进Workbuddy，一句话查询人力数据、办理HR业务。 Version: 1.0.0. |
| BioBuddy 生物医药研究助手 | `workbuddy/connectors/marketplace/connectors/biobuddy` | mcp | 5 | BioBuddy 生物医药智能研究平台：一次连接 Gateway，即可发现并挂载已获授权的分子设计、转化研究、靶点发现与数据智能 MCP 工具。 Version: 1.0.3. |
| Bugly 质量概览 | `workbuddy/connectors/marketplace/connectors/bugly-token` | mcp | 3 | 查看产品的质量概览 包括崩溃率 anr率 foom（oom）率 启动耗时 |
| 财汇金融与风险数据 | `workbuddy/connectors/marketplace/connectors/caihui-mcp` | mcp | 2 | 财汇 MCP 提供专业金融与风险数据服务，覆盖境内企业工商、上市公司、债券、基金、金融机构、宏观与区域经济、监管与司法风险、新闻公告及法规等多维度数据，支撑金融数据查询、风险评估、分析研究、投资交易、舆情监测、投行尽调、信贷管理、合规审查等业务场景。 Version: 1.0.0. |
| 扫描全能王 | `workbuddy/connectors/marketplace/connectors/camscanner-mcp` | mcp | 6 | 智能文档转换与处理平台。支持图片/PDF格式转换（Word、Excel、Markdown、PDF）、图片增强（去阴影、锐化、高清化、老照片修复）、OCR文字识别、图片翻译、公式提取、水印处理、多图合并、发票/票据识别、云文档搜索、文档云端保存等。 |
| Canva可画 | `workbuddy/connectors/marketplace/connectors/canva` | mcp | 2 | 无缝调用Canva可画的设计能力。一句话生成海报、演示文稿、小红书封面等设计，通过文字描述调整尺寸、填充品牌模板及检索已有内容 |
| Canva可画 | `workbuddy/connectors/marketplace/connectors/canva-ai` | mcp | 2 | 无缝调用Canva可画的设计能力。一句话生成海报、演示文稿、小红书封面等设计，通过文字描述调整尺寸、填充品牌模板及检索已有内容 |
| 创客贴 AI 创作 | `workbuddy/connectors/marketplace/connectors/chuangkit` | cli | 2 | 一键调用创客贴强大的AI在线设计能力，一句话生成专业营销设计，覆盖海报、品牌logo、封面配图、小红书图文，电商等设计场景，支持图文分层可编辑，点选改字，让设计小白轻松做图做视频！ Version: 0.1.0. |
| 出海匠 | `workbuddy/connectors/marketplace/connectors/chuhaijiang` | mcp | 12 | 基于实时 TikTok Shop 数据完成选品、竞品分析、达人筛选与带货内容创作，并管理社媒账号、发布内容、运营评论和私信。 |
| 水滴征信 | `workbuddy/connectors/marketplace/connectors/cisp-mcp` | mcp | 3 | 通过水滴征信企业信息服务平台查询工商、知识产权、舆情、财务、土地、企业关联关系、关联方等企业多维信息，并支持企业二要素/三要素核验。 |
| 腾讯云 CloudBase | `workbuddy/connectors/marketplace/connectors/cloudbase` | connector | 136 | 腾讯云开发 CloudBase 全栈开发、部署、调试与排障连接器。覆盖 Web 应用、微信小程序、uni-app、原生 App HTTP API、云函数、CloudRun、NoSQL/MySQL 数据库、云存储、静态托管、身份认证、AI 大模型调用、AI Agent、资源巡检与 Spec 工作流。 |
| CNB | `workbuddy/connectors/marketplace/connectors/cnb-api` | cli | 2 | 通过自然语言管理 CNB 平台：仓库、Issue、PR、流水线、制品库等操作。 |
| COROS | `workbuddy/connectors/marketplace/connectors/coros` | mcp | 2 | 用自然语言查询 COROS 运动与健康数据：训练记录、活动分析、睡眠、心率、HRV、压力、体能评估与训练日程。 Version: 1.0.0. |
| DataBuddy | `workbuddy/connectors/marketplace/connectors/databuddy` | cli | 17 | 连接 DataBuddy 数据知识库，让 AI 基于企业真实数据作答——问数、报告、异动归因、预测、相关性等分析更可信，并可生成实时更新的仪表盘。 |
| 通联数据 | `workbuddy/connectors/marketplace/connectors/datayes-data` | mcp | 3 | 用自然语言查询金融数据：A股/港股、基金、债券、指数、期货期权、因子、实时行情、宏观、公告与政策法规。 |
| DCS Cloud | `workbuddy/connectors/marketplace/connectors/dcs-cloud` | mcp | 6 | 引导 dcs CLI（下载、自动更新、PAT 登录），之后直接执行 CLI 操作 DCS Cloud：项目、任务、工作流、计费、数据文件。用户需在云平台个人中心创建个人访问令牌(PAT)并粘贴到连接器。 Version: 2.0.0. |
| 深度智联·地产数据 | `workbuddy/connectors/marketplace/connectors/deeplink` | mcp | 3 | 由深度智联提供的地产 AI 数据服务。「问数」使用经克而瑞授权的中国房地产数据，覆盖新房、二手房、土地、企业、宏观、长租公寓、产城、康养、商办九大领域；「问知」提供地产、物业、银发三大领域专业知识问答。 Version: 3.0.0. |
| 美图设计室 AI设计 CLI | `workbuddy/connectors/marketplace/connectors/designkit-buddy-cli` | cli | 2 | 一句话轻松调用美图设计室Agent Teams，从市场策略洞察，到电商套图、营销视频、社媒图文、海报及品牌等视觉物料，零门槛完成商业设计的全流程。 Version: 1.0.2. |
| 钉钉 | `workbuddy/connectors/marketplace/connectors/dingtalk` | cli | 172 | 通过命令行管理钉钉全产品能力：AI 表格、考勤、日历、群聊与机器人、通讯录、开放平台文档、DING 消息、钉钉文档、钉钉云盘、AI 听记、邮箱、OA 审批、日志、待办。 |
| 深知可信工作台 | `workbuddy/connectors/marketplace/connectors/dknowc-mcp` | mcp | 2 | 深知可信工作台面向政策、法律、标准和公共服务场景，提供可信问答、权威检索、深度研究和材料整理能力。它可以帮助用户查询政策原文、办事条件、申报材料、补贴资质、法律法规和行业标准，梳理多地区、多时间范围的信息，并基于可追溯的权威来源形成清晰、可核验的结果。 |
| 邓白氏查全球 | `workbuddy/connectors/marketplace/connectors/dnb-global-data` | mcp | 3 | 通过自然语言查询邓白氏全球企业档案、财务数据、风险洞察、企业关联及最终受益人（UBO）等商业洞察。 |
| DramaBuddy | `workbuddy/connectors/marketplace/connectors/dramabuddy` | mcp | 3 | DramaBuddy（漫剧助手）是一个人人可用的通用漫剧制作工具——只需提供小说或创意，就能自动生成剧本、角色与分镜视频，轻松做出属于自己的漫剧。 Version: 0.1.0. |
| 夺冠蜂巢 | `workbuddy/connectors/marketplace/connectors/duoguan-fengchao` | mcp | 2 | 覆盖内容大脑、品牌画像、热点选题、口播与图文文案、配图、播客、配音、视频封装和多账号运营的一站式 AI 自媒体内容生产平台。 Version: 2.0.0. |
| 大智慧MCP | `workbuddy/connectors/marketplace/connectors/dzh-mcp` | mcp | 2 | 提供A股K线行情、A股实时行情、港美股K线行情、港美股实时行情、期货K线行情、期货实时行情、基金行情、公司简况资料、公司主营产品、公司股东、公司分红送转、公司财务（利润表）、公司财务（资产负债表）、公司财务（现金流量表）、股票题材概念、A股板块、研究报告、公司公告、新闻舆情、资金流向、机构调研、龙虎榜、融资融券、股票技术指标等数据查询工具，辅助投资决策。 |
| EdgeOne Makers | `workbuddy/connectors/marketplace/connectors/edgeone-pages` | mcp | 49 | 将项目部署到 EdgeOne Makers 并返回线上访问地址，支持全栈、云函数、AI Agent 等开发场景。 |
| 易方达基金 | `workbuddy/connectors/marketplace/connectors/efunds` | mcp | 2 | 接入易方达基金MCP服务，一句话查透基金画像——业绩、风险收益、持仓结构等核心指标一目了然，还能随时调阅易方达发布的投研观点、产品解读与市场洞察，助力您高效进行投资决策。 Version: 1.0.0. |
| 弹性MapReduce | `workbuddy/connectors/marketplace/connectors/emr-query` | cli | 52 | 通过CLI实现弹性 MapReduce 集群、节点、服务、作业、监控、YARN 调度、自动扩缩容、用户与配置等查询。 |
| EzyJoin智慧会议 | `workbuddy/connectors/marketplace/connectors/ezjoin-meeting` | mcp | 2 | 用自然语言管理 EzyJoin 智慧会议：预约会议室、创建/取消会议、查询会议日程与 AI 纪要。 |
| 法大大睿契 | `workbuddy/connectors/marketplace/connectors/fadada-richee` | mcp | 2 | 提供法律法规检索、类案检索、企业信息查询与合同审查能力，帮助用户快速查找相关法条、相似案例、核验企业信息并完成合同风险审查。 Version: 1.0.1. |
| 帆软增长谋士 | `workbuddy/connectors/marketplace/connectors/fanruan-growth-advisor` | mcp | 1 | 企业洞察与增长分析：查询企业经营风险、舆情、招投标、专利、资质、政策等公开商业数据，并调用已授权的 MOSS 增长谋士 Agent 生成分析与报告。 Version: 1.1.0. |
| 同花顺法律AI助手 | `workbuddy/connectors/marketplace/connectors/fazhi-law` | mcp | 36 | 查询中国法律法规、司法案例、裁判文书及互联网法律实务资讯，支持法条检索、类案检索、深度法律研究、法律文书起草与诉讼可视化。 Version: 1.0.0. |
| 福帮手 | `workbuddy/connectors/marketplace/connectors/fbs-connector` | connector | 8 | 福帮手人机协同连接器：识别当前身份与专家入口，匹配可执行场景方案，记录首值与继续使用进度，并查询乐包状态或衔接后续服务。 |
| 飞书 | `workbuddy/connectors/marketplace/connectors/feishu` | cli | 545 | 通过命令行管理飞书/Lark 全产品能力：即时通讯、邮箱、日历、云文档、电子表格、多维表格（Base）、幻灯片、画板、知识库、云空间、妙记、视频会议、任务、审批、考勤、通讯录、OKR 等。 |
| 分贝通 | `workbuddy/connectors/marketplace/connectors/fenbeitong` | mcp | 3 | 用自然语言查看当前分贝通账号和所属企业、切换企业，查询酒店、机票和火车票、规划行程，管理申请单与商旅订单，查询消费规则，归集发票与处理报销，并获取客服问答和问题处置支持。 |
| 粉笔 | `workbuddy/connectors/marketplace/connectors/fenbi-baokao-decision` | mcp | 8 | 粉笔AI公考助手，帮你查专业分类、完善报考简历、智能选岗与国考模拟选岗、了解考情与报考条件，还能练易混词与成语辨析积累，提供一站式公考备考服务，让备考更精准、更高效。 |
| 进门投研 | `workbuddy/connectors/marketplace/connectors/finenter` | mcp | 2 | 进门MCP覆盖券商、上市公司及资管机构的公开路演内容，整合内外资研报、券商点评等机构级观点，并提供实时行情、财务及量化因子等数据。经Data Agent清洗与结构化处理，减少Token消耗，提升回答准确率。 |
| Flova | `workbuddy/connectors/marketplace/connectors/flova` | mcp | 2 | Flova AI 视频与图片内容创作：支持剧本、短片、短剧、漫剧、电影、广告、商品 TVC 与视觉设计，覆盖文生图、文生视频、图生视频、素材生成、分镜、修改、审阅和导出。 Version: 1.1.1. |
| 福马AI外呼任务 | `workbuddy/connectors/marketplace/connectors/fuma-ai-callout` | mcp | 3 | 通过 WorkBuddy 查询福马AI手机智能体、成员列表，并创建 AI 外呼任务。 |
| 法研·法律法规检索 | `workbuddy/connectors/marketplace/connectors/fyopen-lawsearch` | mcp | 2 | 法研·法律法规检索，支持自然语言获取精准、现行有效的法规条文，将高质量、海量的法规知识库，无缝接入各类AI应用与工作流中。 |
| Gangtise投研 | `workbuddy/connectors/marketplace/connectors/gangtise-mcp` | mcp | 3 | Gangtise MCP汇聚机构级观点，研报，日程等另类数据，提供投研AI Agent预生成数据及全球行情/财务/估值/宏观行业等结构化数据。 Version: 1.0.8. |
| 高顿•实习就业助手 | `workbuddy/connectors/marketplace/connectors/gaodun-job` | mcp | 90 | 大学生实习就业全链路 AI 助手：智能推荐公考岗位，检索实习与校招职位，提供 MBTI、霍兰德等职业测评，简历诊断与 AI 优化改写，面试刷题与模拟面试评估报告，助你拿 offer。 |
| 广发证券 | `workbuddy/connectors/marketplace/connectors/gfsecurities` | connector | 2 | 通过广发证券 MCP，完成多维选股、深度研究、智能盯盘三大核心场景的智能投研服务，实现市场热点跟踪、资讯动态解读、标的筛选、投后复盘的智能投资闭环。 |
| 恒生聚源 MCP | `workbuddy/connectors/marketplace/connectors/gildata` | mcp | 5 | 连接恒生聚源 MCP，查询金融结构化数据、研究报告、公司公告、新闻资讯、条件选股、宏观行业、工商企业数据。支持基金经理观点持仓一致性分析、行业速报生成、金融资讯热点解读。 |
| GitHub | `workbuddy/connectors/marketplace/connectors/github` | connector | 2 | 在 GitHub 上克隆、推送代码，查看和管理仓库与 Pull Request，用自然语言完成代码协作。 |
| 腾讯公益机构服务平台 | `workbuddy/connectors/marketplace/connectors/gongyi-open-mcp` | mcp | 2 | 腾讯公益机构服务平台连接器：授权后可读取您机构的基本信息与资质证件、公益项目详情、筹款与拨付数据、财务披露记录及平台待办事项，用于为您提供机构运营分析与项目管理辅助服务。 Version: 1.0.0. |
| 新华三Cloudnet灵犀AI助手 | `workbuddy/connectors/marketplace/connectors/h3c-cloudnet` | mcp | 3 | 面向网络运维场景的 AI 助手，支持网络运行状态查询、网络问题分析、设备/AP 信息查询和无线终端故障排查，帮助用户快速定位网络异常并获取处理建议。 |
| 氚云 | `workbuddy/connectors/marketplace/connectors/h3yun-connector` | mcp | 3 | 通过氚云连接器，将日常业务快速构建为可配置、可协同、可追踪的数字化应用。支持快速创建应用表单、管理业务数据、以流程驱动审批与任务流转，适用于客户、项目、采购、库存、售后等多类业务管理场景。 |
| 汉仪字库 | `workbuddy/connectors/marketplace/connectors/hanyi-fonts` | mcp | 2 | 连接汉仪交付平台服务，在 WorkBuddy 中查询企业合同、字体权益以及字体预览。 Version: 0.1.0. |
| i人事AI·HR专家 | `workbuddy/connectors/marketplace/connectors/ihr-cli` | cli | 138 | 一键直接连接 i 人事。覆盖组织人事管理、劳动合同、考勤管理、薪酬管理、社保个税、智慧绩效OKRKPI、招聘管理、培训陪练、OA审批，AI面谈、数字人面试，蓝领面试，说一句话，就能查询分析人事、薪资、绩效、用工风险，提升敏捷管理水平，降低人力成本，还有自定义各类agent，SKILL，实现定制化管理要求。 Version: 0.1.2. |
| ima | `workbuddy/connectors/marketplace/connectors/ima-mcp` | connector | 2 | 腾讯AI知识管家，连接后支持搜索、读取和写入知识库资料，并可搜索和订阅教育、法律、财经、科技等20+行业专业知识 |
| 电商内容专家 | `workbuddy/connectors/marketplace/connectors/infimind-ecommerce-content` | mcp | 9 | 通过 OAuth 连接电商内容专家，创建智能精修、商品主图、商品详情页、爆款图复制、KOC 种草、图文带货、视频生成和爆款视频复制任务。 Version: 1.0.0. |
| 英科AI中台 | `workbuddy/connectors/marketplace/connectors/intco-ai-platform` | mcp | 2 | 统一访问英科内部业务系统、RPA、企业数仓及已授权的企业付费数据服务。 |
| 零信任安全 iOA | `workbuddy/connectors/marketplace/connectors/ioa` | mcp | 2 | 提供零信任接入、终端管控、安全防护、数据防泄密等核心安全能力的管理操作 Version: 1.0.31. |
| 亿欧数据MCP | `workbuddy/connectors/marketplace/connectors/iyiou-connector` | mcp | 3 | 接入亿欧数据MCP服务，用自然语言查透产业数据——企业投融资、产业链上下游、产业研报等核心数据一目了然，还能随时调阅亿欧发布的产业观点、企业解读与市场洞察，助力您高效进行商业决策。 Version: 1.0.0. |
| 简道云 | `workbuddy/connectors/marketplace/connectors/jiandaoyun` | mcp | 1 | 查询、整理和填写简道云数据。用自然语言查找表单记录、汇总业务进展、生成分析，并在确认后创建新记录。 Version: 1.0.0. |
| 金手指·AI广告投放 | `workbuddy/connectors/marketplace/connectors/jinshouzhi` | mcp | 2 | WorkBuddy 里的腾讯广告投放执行台：查数据、写需求单、生成投放深链、轻量调优。 |
| 金数据 | `workbuddy/connectors/marketplace/connectors/jinshuju` | mcp | 2 | 用自然语言在金数据（jinshuju.net）创建表单、表格、问卷、考试、报名、收款等各类场景应用：一句话生成表单与表格、批量处理数据、自动统计分析，零门槛快速搭建。 |
| 九数云BI | `workbuddy/connectors/marketplace/connectors/jiushuyun` | mcp | 1 | 上传 Excel 或 CSV 表格，一键生成原生的可视化数据分析报告、仪表板、图表。 |
| 金山文档 | `workbuddy/connectors/marketplace/connectors/kdocs` | mcp | 84 | 创建、搜索和管理金山文档（WPS 云文档）。支持新建多种文档类型（Word/Excel/PDF/PPT/智能表格/多维表格/智能文档）、读取与搜索文档内容、编辑更新、分享、移动重命名整理、标签收藏管理、知识库空间操作、网页剪藏，以及接龙转表格、AI PPT 生成等。 |
| Kling AI | `workbuddy/connectors/marketplace/connectors/kling-ai-plugin` | mcp | 13 | 一句话，让灵感从想法变成大片。可灵 AI 是面向创作者的 AI 生图与 AI 生视频连接器，可在 WorkBuddy 中直接用自然语言完成图片生成和视频生成，包括文生图、图生图、文生视频、图生视频、单镜头与多镜头视频。适合制作海报、插画、人像、商品图、电商主图、Listing 图、广告素材、产品展示视频、营销短片、电商短视频、种草视频、社交媒体视频和电影感创意视频，可用于淘宝、天猫、京东、拼多多、抖音、快手、小红书、TikTok、... |
| 同花顺快查企业数据 | `workbuddy/connectors/marketplace/connectors/kuaicha-search` | mcp | 3 | 查询中国企业工商、股权投资、经营司法风险、知识产权、招投标及新闻舆情数据。 |
| LemonClaw | `workbuddy/connectors/marketplace/connectors/lemonclaw` | cli | 2 | 连接柠檬云财务、进销存、业财和发票系统，支持查账、开票、业务查询、经营分析等企业经营场景。 |
| 乐享知识库 | `workbuddy/connectors/marketplace/connectors/lexiang` | connector | 28 | 搜索、创建和管理乐享知识库中的文档。支持导入 Markdown、按标签整理内容、追踪团队文档的更新动态。 |
| Linear | `workbuddy/connectors/marketplace/connectors/linear-mcp` | connector | 1 | 管理 Linear 中的 Issues、项目、文档和发布。支持创建和更新 Issue 并指派负责人与标签，评论与讨论串回复，创建项目和里程碑及进度报告，管理文档和附件，查看 Sprint 周期与团队状态，搜索和 Code Review PR 变更。 |
| 领星ERP | `workbuddy/connectors/marketplace/connectors/lingxing-mcp` | mcp | 3 | 使用自然语言查询和管理领星ERP中的店铺、库存、Listing、销售、利润、广告和运营数据。 |
| 零一运营 | `workbuddy/connectors/marketplace/connectors/lingyi-mcp` | mcp | 2 | 零一运营独家知识库：7大行业的视频号/私域的爆款内容案例库 + 零一300万份运营实战文档萃取。 Version: 1.4.0. |
| Linkfox 选品 | `workbuddy/connectors/marketplace/connectors/linkfox-product-selection` | mcp | 141 | 跨境电商选品一站式 AI 工具集，整合 竞品查询/ABA/Keepa/Sorftime/Jungle Scout/卖家精灵/SIF/极目/商业洞察/合规检测等 多项子能力，覆盖选品、关键词、竞品、评论、利基与趋势、合规检测。 |
| Lovrabet CLI | `workbuddy/connectors/marketplace/connectors/lovrabet-cli` | cli | 32 | 连接企业系统、数据和流程，让AI完成工作，交付结果 Version: 2.1.23. |
| MasterGo 莫高设计 | `workbuddy/connectors/marketplace/connectors/mastergo-vibe-mcp` | mcp | 2 | 连接 MasterGo 画布，让 AI 进行设计、修改、同步和获取 D2C 代码。 |
| 芒果灵创 CLI | `workbuddy/connectors/marketplace/connectors/mglc` | cli | 8 | 通过命令行调用芒果灵创 AI 视频创作能力：可使用 30+ 模型生成图片和视频，管理项目、剧本、美术设定与分镜故事板，跟踪任务状态和生成结果。 Version: 0.1.11. |
| 秒哒应用搭建 | `workbuddy/connectors/marketplace/connectors/miaoda` | cli | 2 | 通过自然语言对话，即可完成网页、微信小程序及移动 App 的创建、预览、修改与发布上线，实现智能化、自动化、规模化的应用开发。 |
| Moka HR 智能体 | `workbuddy/connectors/marketplace/connectors/moka` | mcp | 25 | 招聘和人事一体的 AI 同事，把查询与执行收进一个对话。人才推荐、招聘动态、考勤绩效、审批待办，一句话问清；候选人寻访、面试分析与面试官评估，一句话发起。 Version: 0.1.18. |
| 晨星 Morningstar | `workbuddy/connectors/marketplace/connectors/morningstar` | mcp | 2 | 接入晨星全球与中国基金数据，通过自然语言实现基金查询、筛选、分析与深度研究，以及组合穿透分析 |
| 东方财富妙想MCP | `workbuddy/connectors/marketplace/connectors/mx-ds-mcp` | mcp | 2 | 通过自然语言查询的金融投研 MCP 工具套件，依托东方财富数据源，提供A股、港股、美股、基金、债券、指数板块、宏观数据查询，具备多条件资产筛选、券商研报检索、全市场公告解析、金融资讯检索能力。 |
| 摩知轮商标查询 | `workbuddy/connectors/marketplace/connectors/mzl-trademark` | mcp | 2 | 用自然语言检索商标：按名称、申请人、申请号、注册号、尼斯类别、法律状态、日期范围查询，覆盖中国及 110+ 海外国家/地区商标局；并支持以图搜图的图形近似检索。 Version: 1.0.0. |
| 销售易CRM | `workbuddy/connectors/marketplace/connectors/neo-crm` | mcp | 2 | 用自然语言查客户、推商机、盘线索、领公海、写跟进，一句话打通销售工作闭环。 |
| 销售易·易启 | `workbuddy/connectors/marketplace/connectors/neo-eakey` | mcp | 1 | 面向个人的AI销售伙伴，一句话帮你看懂客户、评估商机、发现风险，并把判断转化为下一步行动。 |
| Notion | `workbuddy/connectors/marketplace/connectors/notion` | connector | 64 | 创建、搜索和管理 Notion 工作区。用自然语言读取页面、查询数据库、更新内容、整理知识库。 |
| 及刻智能·时空数据MCP | `workbuddy/connectors/marketplace/connectors/opendata` | mcp | 3 | 通过自然语言查询线下时空数据，提供区域热力、场景识别、客流分析、POI查询等能力，助力商业洞察、开店选址等应用场景。 |
| PandaData 金融数据 | `workbuddy/connectors/marketplace/connectors/pandadata` | mcp | 2 | 查询、整理和分析 A 股、期货、期权、港美股、基金、宏观经济及量化因子等金融数据，支持统计比较与趋势归纳。 |
| Repilot科研智能体 | `workbuddy/connectors/marketplace/connectors/paper-retrieval` | mcp | 2 | 课题申报书与PPT生成、快速文献检索、医学智能问答、综述报告生成，所有任务异步执行，支持状态轮询与取消。 Version: 2.0.1. |
| 智慧芽专利&文献融合检索 | `workbuddy/connectors/marketplace/connectors/patsnap-search` | mcp | 3 | 在智慧芽全球专利数据库和文献库中进行融合检索，支持自然语言、语义搜索、关键词检索和多维过滤，并获取专利或文献信息。 |
| Picset AI 电商设计 | `workbuddy/connectors/marketplace/connectors/picset-commerce-images` | mcp | 13 | Picset AI 电商设计：面向电商卖家、设计师和美工，提供三条独立功能线——电商套图（主图/详情图/套图/Listing/A+，含一张也走套图）、单图文生图/图生图（独立创意单图与图片编辑）、Agent Canvas（画布承接与图片返回），以及连接器统一充值面板。覆盖淘宝、天猫、京东、拼多多、抖音、1688、小红书、TikTok、Amazon、Shopify、Temu、OZON、Shopee、阿里巴巴国际站等主流平台，支持方案... |
| Picset AI 视频创作 | `workbuddy/connectors/marketplace/connectors/picset-video-generation` | mcp | 10 | Picset AI 视频创作连接器支持在 WorkBuddy 中通过密钥调用电商商品视频生成、爆款视频复刻和模特图生成能力，完成素材上传登记、脚本规划、视频脚本生成、积分预估、确认提交、异步生成和任务状态查询。MVP 支持 Seedance 2.0、Seedance 2.0 Fast、Seedance 2.0 Mini 三个模型，默认使用 Seedance 2.0。 |
| 北大法宝·法律智能检索 | `workbuddy/connectors/marketplace/connectors/pkulaw` | mcp | 2 | 检索 + 核验一体：语义（自然语言描述）与关键词双模式检索法规、法条与司法案例；并可把文本中的法条引用与案号回北大法宝库逐条比对、对齐标准名称，输出带 pkulaw.com 原文链接的可溯源结果，专治法律幻觉。 |
| Plaud | `workbuddy/connectors/marketplace/connectors/plaud` | mcp | 2 | 连接 Plaud 录音与 AI：浏览查找录音、读取转写和 AI 摘要、汇总会议纪要，并生成跟进邮件与待办事项。 Version: 1.0.0. |
| 智慧树·AI教学中心 | `workbuddy/connectors/marketplace/connectors/polymas-workbuddy-pre` | mcp | 2 | 查询教师自己的课程、班级、学生标签、分组方案、成绩和作业等智慧树教学数据。 Version: 1.0.4. |
| OpenBoost 跨境数据 | `workbuddy/connectors/marketplace/connectors/proboost` | mcp | 4 | 支持市场研究、选品分析、竞对监控、VOC洞察、关键词分析、listing生成等跨境电商应用场景 |
| 企查查 | `workbuddy/connectors/marketplace/connectors/qcc-company` | connector | 2 | 查询和核实企业工商登记信息。支持股东结构、实际控制人、受益所有人、高管团队、对外投资、财务数据、年报及上市信息查询，用自然语言快速完成企业身份核验与背景调查。 |
| 企查查·法律数据 | `workbuddy/connectors/marketplace/connectors/qcc-legal` | mcp | 2 | 检索与核验中国法律法规和司法案例。覆盖全量现行法律、行政法规、司法解释——法规级到法条级逐字正文，标注时效性与效力级别；海量裁判文书及 2.5 万+ 权威案例（最高法/最高检指导性案例、公报案例、典型案例）；并对文本中的法条与案号引用逐条回库核验、标注时效、生成可溯源超链。用自然语言完成法条依据查找、类案检索、原文调取与法律引用核验，从源头消除法条与案号幻觉。 Version: 1.0.0. |
| 轻流 | `workbuddy/connectors/marketplace/connectors/qingflow` | mcp | 2 | 轻流无代码平台连接器。通过自然语言创建应用、管理表单数据、处理审批流程、查询和导出数据，一站式连接轻流全部能力。 |
| 启信慧眼 | `workbuddy/connectors/marketplace/connectors/qixinhuiyan-mcp` | mcp | 1 | 通过启信慧眼 MCP 接入企业全景数据能力，支持用户用自然语言完成企业搜索、工商画像、风险识别、经营动态、知识产权等商业情报分析。 |
| QQ邮箱 | `workbuddy/connectors/marketplace/connectors/qq-mail` | connector | 2 | 收发、搜索和整理 QQ 邮件。用自然语言读取邮件内容、汇总邮件线程、管理文件夹。 |
| SalesNail 讲师 | `workbuddy/connectors/marketplace/connectors/salesnail-instructor` | mcp | 8 | 通过自然语言自助开通讲师试用、维护商业 Profile、生成客户方案，完成游戏创作、课程配置、实时带教，以及团队、学员、班级和商机的证据化分析与复盘。 Version: 0.6.5. |
| SalesTouch 经营执行 | `workbuddy/connectors/marketplace/connectors/salestouch` | mcp | 7 | 通过自然语言连接 SalesTouch，完成组织资料、部门、角色权限、员工邀请、下属管理范围与销售流程配置，并处理销售执行、非销售工作、绩效、内部调研和经营汇总。 |
| 致远互联协同办公服务 | `workbuddy/connectors/marketplace/connectors/seeyon-office-marketing-suite` | cli | 61 | 为企业提供协同办公、会议和业务协同能力，支持用户用自然语言完成会议创建与查询、协同发起与跟进、和业务数据分析。 Version: 1.0.0. |
| 用友智能服务（AI BaaS） | `workbuddy/connectors/marketplace/connectors/shanglv-mcp-gateway` | mcp | 2 | 通过用友银企联、税企联、商旅云等财务服务产品，为企业提供财务税务与银行资金数据服务，并提供企业商旅运营服务和行程服务。用自然语言完成企业的资金、税务、商旅的全面运营管理。 |
| 天财商龙餐饮SaaS | `workbuddy/connectors/marketplace/connectors/shanlong-claw` | cli | 13 | 天财商龙成立于1998年，是中国餐饮数字化整体解决方案服务商。连接器提供公司介绍与企业版能力范围说明；具体经营、会员、成本等业务分析请下载企业版，使用经营分析师、会员运营专家、成本管控专家及其技能完成。 Version: 1.0.165. |
| 纷享销客CRM | `workbuddy/connectors/marketplace/connectors/sharecrm` | mcp | 21 | 用自然语言查询客户、推进商机、写跟进记录、处理审批、建图表等，轻松搞定销售全链路工作。 |
| 上奇产业通-企业动态追踪 | `workbuddy/connectors/marketplace/connectors/sq-company-dynamic` | mcp | 3 | 实时追踪企业全生命周期动态，覆盖投资设立、股权变动、创新平台、中标、知识产权、排名、迁移、资质认定、工商变更、上市、标准制定、招聘、拿地等维度，并提供企业实体匹配。 Version: 1.0.1. |
| 森浦qeubee金融数据 | `workbuddy/connectors/marketplace/connectors/sumscope-data` | mcp | 3 | 查询森浦固定收益市场数据：债券基础信息、一级发行、票据行情、舆情信息、发行人财务报表、宏观指标和交易日历。 Version: 1.0.1. |
| 腾讯数字文化智能体 | `workbuddy/connectors/marketplace/connectors/tanyuan-assistant` | mcp | 2 | 基于文化可信知识库的智能体服务，提供世界遗产、博物馆藏品、甲骨文字形释义、学术文献等可溯源检索与创作辅助。覆盖申遗文本、考古数据、陶瓷基因库、纹样库等多模态知识，支持研究考据、策展辅助、文化科普与内容创作。 |
| TAPD | `workbuddy/connectors/marketplace/connectors/tapd` | connector | 2 | 管理需求、缺陷、任务和迭代。查询项目进度、拆分需求、流转状态、填写工时，覆盖需求到发布的研发全生命周期。 |
| 同程程心 | `workbuddy/connectors/marketplace/connectors/tc-chengxin` | cli | 35 | 同程程心可通过自然语言查询机票、火车票、酒店、景点、度假产品等旅行资源，支持火空联程、智能交通推荐、特价机票搜索、景区门票预订，以及完整行程规划，显著提升出行效率。 |
| NextB2B贸易通MCP | `workbuddy/connectors/marketplace/connectors/tct-business-expert` | mcp | 9 | NextB2B贸易通MCP。用自然语言查商机询盘、待跟进线索、客户资产家底与业务员业绩，并按老板/业务员视角解读，为商机跟进、客户经营与业绩自查提供数据；需完成 MCP 联合授权后使用。 Version: 0.10.3. |
| 通达信 | `workbuddy/connectors/marketplace/connectors/tdx-connector` | mcp | 2 | 通过通达信 MCP 查询全球股票行情数据、条件选股、研究报告、公告资讯和宏观信息。支持个股基本面分析、同行业对比和智能选股筛查。 |
| 企鹅教师助手 | `workbuddy/connectors/marketplace/connectors/teacher-assistant` | mcp | 1 | 企鹅教师助手负责处理基础性工作，基于课标和教学方法协助快速生成课程大纲、教案、课件及多模态教学资源，从而让教师腾出更多时间在课堂上进行创新 Version: 1.0.0. |
| Tec-Do 2.0 广告与增长情报 | `workbuddy/connectors/marketplace/connectors/tec-do` | mcp | 2 | 面向出海广告投放和增长团队的 AI 能力集合。 |
| 腾讯云数据湖计算 DLC | `workbuddy/connectors/marketplace/connectors/tencent-dlc` | connector | 2 | 通过 MCP 操作腾讯云数据湖计算（DLC）：执行 SQL / Spark SQL，浏览 Catalog、数据库、表与分区，管理 Spark 作业，查询任务与日志，诊断任务性能，查看引擎与用户权限。 |
| 腾讯文档 | `workbuddy/connectors/marketplace/connectors/tencent-docs` | connector | 1 | 创建、编辑和协作腾讯文档。用自然语言管理在线表格、文档和幻灯片，轻松完成内容查询、数据整理和团队协同。 |
| 腾讯文档企业版 | `workbuddy/connectors/marketplace/connectors/tencent-docs-oa` | connector | 1 | 创建、编辑和协作腾讯文档。用自然语言管理在线表格、文档和幻灯片，轻松完成内容查询、数据整理和团队协同。 |
| 腾讯健康NGES | `workbuddy/connectors/marketplace/connectors/tencent-health-nges` | mcp | 9 | 腾讯健康NGES MCP服务，支持智能问数和合规审核等功能 |
| 腾讯地图 | `workbuddy/connectors/marketplace/connectors/tencent-map` | mcp | 2 | 接入腾讯地图各类位置服务，包括地点搜索、路线规划（驾车/公交/步行/骑行）、地址正逆解析、沿途搜索和天气查询等。 |
| 腾讯地图·指南制作 | `workbuddy/connectors/marketplace/connectors/tencent-map-guide` | mcp | 2 | 用自然语言制作腾讯地图行程指南：创建、查询、更新、删除攻略。支持将攻略文本 / Markdown 内容智能转换为腾讯地图结构化行程指南数据格式（自动解析地点、补全 POI、生成路线），并一键保存同步到你的地图指南。 Version: 1.0.0. |
| 腾讯企点客服 | `workbuddy/connectors/marketplace/connectors/tencent-qidian-cs` | connector | 2 | 腾讯企点客服连接器：用自然语言处理工单（查询/创建/更新/状态变更）、查询坐席在线与实时接待、检索/拉取客户资料、拉取人工/大模型/文本机器人的会话记录和消息、查看客服实时监控、会话监控、客服满意度与响应度报表等数据。 |
| 腾讯问卷 | `workbuddy/connectors/marketplace/connectors/tencent-survey` | connector | 6 | 创建、管理和分析腾讯问卷。用自然语言快速生成问卷、查看回收数据、设置题目逻辑。 |
| 腾讯云数据仓库 TCHouse-C | `workbuddy/connectors/marketplace/connectors/tencent-tchouse-c` | mcp | 40 | 腾讯云数据仓库 TCHouse-C 智能运维与分析助手，用自然语言完成集群健康诊断、慢 SQL 分析、规格选型推荐、表结构设计与 NL2SQL 查询。 Version: 1.0.0. |
| 微云 | `workbuddy/connectors/marketplace/connectors/tencent-weiyun` | connector | 10 | 查看、下载、删除微云文件，并且提供上传文件到微云、生成分享链接能力，帮你管理微云文件 |
| 腾讯营销投放 | `workbuddy/connectors/marketplace/connectors/tencentads` | cli | 154 | 腾讯营销投放 Skill，为大模型赋予广告投放管理能力：支持广告账户授权、广告/智投项目的创建与更新、创意管理、广告数据查询与分析、推广内容资产管理，以及操作日志查询等完整的广告投放全链路操作。 |
| TextIn xParse·智能文档解析 | `workbuddy/connectors/marketplace/connectors/textin-xparse` | cli | 11 | 上传文件（PDF、图片、Word、Excel、PPT、扫描件等），即可将其解析为 Markdown 或结构化 JSON，可还原文档目录结构和复杂表格结构，适用于高精度高性能要求的文档处理OCR任务，每日免费1000页。 |
| TikTok for Business | `workbuddy/connectors/marketplace/connectors/tiktok` | connector | 1 | TikTok for Business MCP Server 是基于模型上下文协议（MCP）搭建的标准化桥梁，助力开发者与广告主将 AI 智能代理直接对接 TikTok 广告平台。它将广告核心能力⸺广告活动管理、效果报表、受众配置以及创意运营，封装为一套稳定、可投入生产环境使用的工具。AI智能代理仅通过简洁结构化指令，即可完成 TikTok 广告的管理、优化与数据依托这套工具报表查询工作。 |
| 腾讯会议 | `workbuddy/connectors/marketplace/connectors/tmeet` | cli | 11 | 通过命令行创建、查询和管理腾讯会议。支持快速发起会议、查看日程安排、管理参会人员。 |
| 今日水印相机 | `workbuddy/connectors/marketplace/connectors/today-watermark-camera` | connector | 3 | 用自然语言查询和导出今日水印相机的团队照片，通过对话辅助完成照片归档、考勤核对、台账整理和照片统计。 |
| 同舟金融研究 | `workbuddy/connectors/marketplace/connectors/tongzhou-fin-research` | mcp | 2 | 连接公开行情、研报检索、行业图谱与同舟投研材料，为股市研究提供可复核证据。 Version: 0.21.2. |
| 畅捷通T+ | `workbuddy/connectors/marketplace/connectors/tplus-api` | mcp | 2 | 畅捷通 T+Cloud 自然语言操作入口：查询/管理销售订单、采购订单、库存单据、生产工单、财务凭证、报表及基础档案。 Version: 1.0.0. |
| Tushare | `workbuddy/connectors/marketplace/connectors/tushare` | mcp | 3 | Tushare 金融数据服务，支持 A股、指数、ETF/基金、财务、估值、资金流、公告新闻、板块概念与宏观数据等研究工作。 Version: 1.0.0. |
| 天眼查 | `workbuddy/connectors/marketplace/connectors/tyc-mcp` | mcp | 2 | 通过天眼查 MCP 查询多维度企业数据。支持工商登记、股东结构、司法风险、知识产权、董监高、经营数据等 160+ 项企业数据能力，用自然语言完成企业尽调与商业情报分析。 |
| UU跑腿 | `workbuddy/connectors/marketplace/connectors/uupt` | cli | 2 | 通过自然语言使用 UU跑腿：同城配送与帮帮服务，支持询价、下单、查单、取消、跑男追踪和领取优惠券 Version: 1.1.0. |
| 企业微信 | `workbuddy/connectors/marketplace/connectors/wecom` | cli | 97 | 企业微信官方 CLI 套件，覆盖消息、邮件、文档、待办、日程、会议、微盘、通讯录等业务功能。支持机器人主动通知、新建与读取文档、文档搜索、新建管理日程、预约与获取会议信息、新建跟进待办、上传与获取微盘文件、邮件读取与发送等能力 |
| 微盛企微管家SCRM | `workbuddy/connectors/marketplace/connectors/weisheng-scrm` | mcp | 4 | 查询或管理企业微信中的客户信息、客户标签、客户群、营销素材、活码、群发、跟进记录、联系人、商机、汇报、抽奖、客户日程、聊天记录等业务能力。 |
| 腾讯自选股 | `workbuddy/connectors/marketplace/connectors/westock-mcp` | mcp | 2 | 直连腾讯自选股，实时掌握毫秒级行情与资金动态，用自然语言分析自选数据、设置股价提醒、管理模拟交易，轻松搞定盯盘与投资决策。 |
| Wind Alice 万得金融数据 | `workbuddy/connectors/marketplace/connectors/wind-finance` | mcp | 3 | 全量开放万得（Wind）金融数据与工具能力，覆盖沪深港美等全球60多个国家地区的股票、基金、债券、商品、指数、经济数据与万得金融模型与工具集。让WorkBuddy变身金融分析专家，成为具备数据穿透、投研分析、风险决策等多维金融能力的专业智能体。 Version: 1.2.0. |
| 百智WiseNote | `workbuddy/connectors/marketplace/connectors/wisenote` | mcp | 2 | 通过用户授权读取百智 WiseNote 会议列表、会议详情摘要和会议转写内容。 |
| 威科先行 | `workbuddy/connectors/marketplace/connectors/wk-workbuddy` | mcp | 2 | 威科先行依托全面、准确、及时更新的法规、案例等法律数据研发的MCP服务，支持语义检索、关键词检索等场景。 |
| 微脉体重管理 | `workbuddy/connectors/marketplace/connectors/wm-weight-manage` | mcp | 5 | 生成个性化成人体重管理方案，渲染为可打卡的独立 HTML 页面：分阶段目标、饮食运动建议、餐食照片热量分析、本地体重记录。 Version: 1.0.1. |
| 微盟 WOS CLI | `workbuddy/connectors/marketplace/connectors/woscli` | cli | 5 | 通过自然语言调用 woscli 操作微盟 WOS 业务能力：查询与管理订单、商品、客户资料、营销活动、数据看板等。 |
| WPS知识库 | `workbuddy/connectors/marketplace/connectors/wps-knowledgebase` | cli | 4 | 通过自然语言操作 WPS/zhishi 云端知识库：列出知识库、浏览文件树、智能问答、分享链接，以及文件/文件夹增删改查。 |
| 小鹅通 | `workbuddy/connectors/marketplace/connectors/xiaoe-cloud-cli` | connector | 2 | 用自然语言管理小鹅通店铺：查询课程与学员，创建和编辑课程，查看订单，并查找或上传图片、音频、电子书和文档素材。 |
| 天创信用星图MCP | `workbuddy/connectors/marketplace/connectors/xingtu-claw-risk` | mcp | 2 | 企业风险 AI 分析助手，用自然语言识别企业所属行业、分析企业间关联方关系（股权/实控人/担保/共同投资）。 |
| 迪安智能科研云 | `workbuddy/connectors/marketplace/connectors/xmed-figure-mcp` | mcp | 2 | 科研数据可视化：火山图、PCA、富集分析、生存分析，自动匹配发表级输出 Version: 1.0.10. |
| 盈米MCP | `workbuddy/connectors/marketplace/connectors/yingmi-mcp` | mcp | 3 | 查询基金与市场数据，完成基金研究、组合分析、财富规划及金融内容生成。 |
| 智客AI · 对公(To B)营销助手 | `workbuddy/connectors/marketplace/connectors/youshu-bd-mate` | mcp | 2 | 对公营销助手是基于企业全维数据构建的对公营销智能助手，提供从生成访前一页纸、访前客情报告、产品找客、关键人画像、营销话术及按企荐品的完整展业闭环能力。 Version: 2.0.1. |
| 华宇元典法律数据 | `workbuddy/connectors/marketplace/connectors/yuandian-mcp` | mcp | 1 | 华宇元典法律数据为智能体提供法律法规、案例文书、企业信息 MCP 工具能力。 |
| 云客AI工作手机 | `workbuddy/connectors/marketplace/connectors/yunke-cli` | cli | 2 | 提供真实手机的数据读取与设备控制能力。AI 自动采集通话与录音，沉淀全量沟通数据驱动销售分析；同时允许 AI 直接操控手机拨打电话、发短信、操作 APP，把实体手机变成 Agent 的硬件执行单元。 |
| 云帐房 | `workbuddy/connectors/marketplace/connectors/yzf-general-mcp-server` | mcp | 6 | 一句话把票开了、税报了、政策理清了，省的是钱，更是心。 Version: 1.1.1. |
| 云帐房AI开票 | `workbuddy/connectors/marketplace/connectors/yzf-invoice-mcp-server` | mcp | 4 | 通过自然语言使用云帐房 AI 开票能力，完成开票信息识别，并前往电子税局开票。 |
| 中兴新云AI智报 | `workbuddy/connectors/marketplace/connectors/zfs-fssc-ai` | mcp | 3 | 财务云 AI 报销助手：用自然语言完成报销申请、发票查询识别、报销单查询与费用审批等操作。 |
| 知识星球 | `workbuddy/connectors/marketplace/connectors/zsxq` | cli | 2 | 用自然语言管理知识星球：浏览星球内容、发帖评论、搜索主题、回答问题、管理笔记、查看用户信息。 |

## 最近变更

| Date | Change Log | Summary |
| --- | --- | --- |
| 2026-09-03-180002 | [2026-09-03-180002](workbuddy/change-logs/2026-09-03-180002.md) | WorkBuddy 本次同步新增 9 个文件、修改 16 个文件、删除 0 个文件。 新增条目：connectors/marketplace/connectors/dnb-global-data, connectors/marketplace/connectors/intco-ai-platform。 受影响范围：connectors/marketpl... |
| 2026-09-02-223755 | [2026-09-02-223755](workbuddy/change-logs/2026-09-02-223755.md) | WorkBuddy 本次同步新增 4306 个文件、修改 171 个文件、删除 2 个文件。 新增条目：connectors/marketplace/connectors/deeplink, connectors/marketplace/connectors/dramabuddy, connectors/marketplace/connectors/h... |
| 2026-09-02-180002 | [2026-09-02-180002](workbuddy/change-logs/2026-09-02-180002.md) | WorkBuddy 本次同步新增 21 个文件、修改 27 个文件、删除 1 个文件。 新增条目：connectors/marketplace/connectors/shanlong-claw, connectors/marketplace/connectors/tencent-map-guide。 受影响范围：connectors/marketpla... |
| 2026-09-01-180001 | [2026-09-01-180001](workbuddy/change-logs/2026-09-01-180001.md) | WorkBuddy 本次同步新增 58 个文件、修改 31 个文件、删除 24 个文件。 新增条目：connectors/marketplace/connectors/aimoderator, connectors/marketplace/connectors/today-watermark-camera, connectors/marketplace... |
| 2026-08-31-180002 | [2026-08-31-180002](workbuddy/change-logs/2026-08-31-180002.md) | WorkBuddy 本次同步新增 26 个文件、修改 6 个文件、删除 10 个文件。 新增条目：connectors/marketplace/connectors/databuddy, connectors/marketplace/connectors/jinshouzhi。 移除条目已归档：connectors/marketplace/connec... |
| 2026-08-30-212148 | [2026-08-30-212148](workbuddy/change-logs/2026-08-30-212148.md) | WorkBuddy 本次同步新增 2677 个文件、修改 0 个文件、删除 0 个文件。 新增条目：connectors/default, connectors/marketplace/.codebuddy-connector, connectors/marketplace/connectors/77ircloud, connectors/market... |
| 2026-08-20-180002 | [2026-08-20-180002](workbuddy/change-logs/2026-08-20-180002.md) | WorkBuddy 本次同步新增 0 个文件、修改 1 个文件、删除 0 个文件。 受影响范围：skills/aihot__skillhub。 |
| 2026-08-13-180002 | [2026-08-13-180002](workbuddy/change-logs/2026-08-13-180002.md) | WorkBuddy 本次同步新增 13 个文件、修改 4 个文件、删除 235 个文件。 新增条目：skills/paper-reader, skills/paper-reader.zip, skills/paper-rebuttal, skills/paper-reviewer, skills/research-lineage-map。 移除条目已归... |
| 2026-08-11-180003 | [2026-08-11-180003](workbuddy/change-logs/2026-08-11-180003.md) | WorkBuddy 本次同步新增 54 个文件、修改 0 个文件、删除 0 个文件。 新增条目：experts/mvp-dev-expert-team。 受影响范围：experts/mvp-dev-expert-team。 |
| 2026-08-10-170319 | [2026-08-10-170319](workbuddy/change-logs/2026-08-10-170319.md) | WorkBuddy 本次同步新增 1 个文件、修改 0 个文件、删除 0 个文件。 新增条目：skills/.disable_to_model_invocation_migration.json。 受影响范围：skills/.disable_to_model_invocation_migration.json。 |
| 2026-08-09-180003 | [2026-08-09-180003](workbuddy/change-logs/2026-08-09-180003.md) | WorkBuddy 本次同步新增 0 个文件、修改 1 个文件、删除 0 个文件。 受影响范围：skills/aihot__skillhub。 |
| 2026-08-05-230159 | [2026-08-05-230159](workbuddy/change-logs/2026-08-05-230159.md) | WorkBuddy 本次同步新增 8434 个文件、修改 0 个文件、删除 0 个文件。 新增条目：cb_teams_experts/a-share-analysis, cb_teams_experts/agent-sdk-dev, cb_teams_experts/ai-hedge-fund, cb_teams_experts/ardot-desig... |
