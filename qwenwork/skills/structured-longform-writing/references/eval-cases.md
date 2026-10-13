# Evaluation Cases

此文件用于 structured-longform-writing Skill 的触发验收和质量验收。每个 case 包含用户原始请求、预期是否触发、预期文档类型、预期行为和质量关注点。

## should_trigger

### case: ST-001

- user_prompt: 请写一篇中文技术博客，主题是《为什么 Agent 长文写作不能只靠一次性 Prompt》，面向 Agent 产品和工程团队。
- expected_trigger: true
- expected_doc_type: blog
- expected_behavior: 触发 Skill，读取 blog-template、workflow、quality-rubric、style-guide，生成有中心观点、结构清楚、有例子的技术博客。
- quality_focus: 中心观点、可读性、非空泛程度、技术读者匹配。

### case: ST-002

- user_prompt: 帮我写一份分析报告，主题是《QoderWork长文写作能力现状与改进方向》，面向产品和技术负责人，不能编造用户数据。
- expected_trigger: true
- expected_doc_type: report
- expected_behavior: 触发 Skill，读取 report-template、workflow、quality-rubric、style-guide，输出背景、问题定义、原因分析、竞品经验、改进建议和风险。
- quality_focus: 事实安全、分析框架、结论、建议。

### case: ST-003

- user_prompt: 生成一份《QoderWork结构化长文创作 Skill 建设方案》，用于内部评审，MVP 只覆盖博客、报告、方案。
- expected_trigger: true
- expected_doc_type: proposal_or_plan
- expected_behavior: 触发 Skill，读取 proposal-template、workflow、quality-rubric、style-guide，输出背景、目标、范围、方案设计、实施路径、验收标准和风险。
- quality_focus: 可落地性、范围边界、验收标准、风险应对。

### case: ST-004

- user_prompt: 根据下面这些零散笔记整理成一份完整方案：长文效果差；用户常说空泛；需要大纲、模板、质量门；先做本地 Skill；后续接入QoderWork Agent Loop。
- expected_trigger: true
- expected_doc_type: proposal_or_plan
- expected_behavior: 触发 Skill，将笔记扩展为结构化方案，声明缺失信息和合理假设。
- quality_focus: 材料使用、结构完整、假设声明。

### case: ST-005

- user_prompt: 帮我做一份竞品分析，看看 Claude Skills、Codex Skills、Manus Skills 对我们做长文写作 Skill 有什么启发。
- expected_trigger: true
- expected_doc_type: competitive_analysis
- expected_behavior: 触发 Skill，按报告结构输出分析对象、对比维度、关键发现和对QoderWork的建议；如无法检索，不编造最新事实。
- quality_focus: 分析框架、事实安全、关键发现、建议。

### case: ST-006

- user_prompt: 写一个面向老板的内部汇报文档，说明为什么我们要把长文写作做成 Skill，而不是继续调 prompt。
- expected_trigger: true
- expected_doc_type: internal_briefing
- expected_behavior: 触发 Skill，采用管理层语气，结论前置，强调问题、判断、方案、投入和风险。
- quality_focus: 受众匹配、结论前置、管理层可读性。

### case: ST-007

- user_prompt: 请把这份会议纪要扩展成一篇完整的项目计划，包含目标、范围、里程碑、风险和验收标准。
- expected_trigger: true
- expected_doc_type: proposal_or_plan
- expected_behavior: 触发 Skill，按方案结构生成项目计划，缺少会议纪要内容时提示需要补充或给可填框架。
- quality_focus: 信息缺失处理、可落地性。

### case: ST-008

- user_prompt: Draft a long-form product strategy memo about improving QoderWork's report writing quality. The audience is product and engineering leadership.
- expected_trigger: true
- expected_doc_type: internal_briefing
- expected_behavior: Trigger the skill, infer English output, use report/proposal hybrid structure, and avoid fabricated metrics.
- quality_focus: audience match, structure, factual safety, recommendations.

### case: WOU-001

- user_prompt: 我在QoderWork里上传了一份会议纪要和几条补充 bullet，请帮我整理成面向老板的阶段汇报，要求结论前置，包含进展、风险、下阶段计划和需要支持的事项。
- expected_trigger: true
- expected_doc_type: internal_briefing
- expected_behavior: 触发 Skill，按QoderWork线上用户材料整理路径处理，优先使用用户材料，不编造进展或指标，输出可直接给管理层看的汇报。
- quality_focus: 受众匹配、材料使用、结论前置、风险和请求清晰。

### case: WOU-002

- user_prompt: 根据这段线上问题排查记录，写一份QoderWork问题复盘分析报告，包含现象、影响、根因假设、修复动作、防复发措施和验证方式，不要编造影响人数。
- expected_trigger: true
- expected_doc_type: report
- expected_behavior: 触发 Skill，按复盘/RCA 报告组织，区分事实、根因假设和待验证信息。
- quality_focus: 事实安全、根因证据、修复动作、验证方式。

### case: WOU-003

- user_prompt: 帮我写一份QoderWork线上长文写作 Skill 灰度方案，包含目标、范围、灰度节奏、回滚策略、风险和验收标准。
- expected_trigger: true
- expected_doc_type: proposal_or_plan
- expected_behavior: 触发 Skill，按线上方案结构输出，不虚构灰度比例或日期，缺失信息放到关键假设或待确认问题。
- quality_focus: 可落地性、范围边界、风险、验收标准。

### case: WOU-004

- user_prompt: 写一篇面向QoderWork用户的最佳实践博客，主题是如何提供材料让 Agent 生成更好的长文，要有具体例子，不要写成产品宣传稿。
- expected_trigger: true
- expected_doc_type: blog
- expected_behavior: 触发 Skill，按用户可读文章结构输出，强调观点、例子和可操作建议。
- quality_focus: 观点清晰、线上用户视角、非营销化表达。

### case: WOU-005

- user_prompt: 请写一份QoderWork浏览器自动化连接链路的技术设计文档，覆盖模块边界、数据流、异常处理、降级策略和验收标准。
- expected_trigger: true
- expected_doc_type: technical_design
- expected_behavior: 触发 Skill，按技术设计结构输出，缺少具体接口时不编造字段，标注待确认项。
- quality_focus: 技术结构、边界清晰、事实安全、验证方案。

### case: WOU-006

- user_prompt: 帮我把这些客户访谈摘录整理成一份客户版解决方案材料，突出场景、价值、方案路径和限制说明，不能暴露内部项目代号。
- expected_trigger: true
- expected_doc_type: proposal_or_plan
- expected_behavior: 触发 Skill，按客户材料模式输出，避免内部术语和未提供的客户案例。
- quality_focus: 客户视角、边界说明、事实安全、可发送性。

### case: WOU-007

- user_prompt: 写一份本月工作总结，材料只有这些：完成文档生成体验优化；处理 3 个线上反馈；下月继续做稳定性。请先给一版可用稿，不确定的地方放到关键假设。
- expected_trigger: true
- expected_doc_type: report
- expected_behavior: 触发 Skill，在材料不足但可合理假设时输出可用总结，并明确假设和待补充数据。
- quality_focus: 弱上下文处理、总结结构、假设声明。

## should_not_trigger

### case: SNT-001

- user_prompt: 帮我把这句话润色一下：我们正在优化QoderWork的长文写作体验。
- expected_trigger: false
- expected_doc_type: none
- expected_behavior: 不触发 Skill，直接给出短句润色。
- quality_focus: 避免误触发。

### case: SNT-002

- user_prompt: 翻译成英文：结构化长文创作 Skill 可以提升生成质量。
- expected_trigger: false
- expected_doc_type: none
- expected_behavior: 不触发 Skill，直接翻译。
- quality_focus: 避免把翻译任务扩展成长文。

### case: SNT-003

- user_prompt: 给《QoderWork长文写作能力建设方案》起 10 个标题。
- expected_trigger: false
- expected_doc_type: none
- expected_behavior: 不触发 Skill，直接给标题候选。
- quality_focus: 避免标题任务误触发。

### case: SNT-004

- user_prompt: 写一条群通知，告诉大家下午三点评审长文写作 Skill。
- expected_trigger: false
- expected_doc_type: none
- expected_behavior: 不触发 Skill，直接写短通知。
- quality_focus: 避免短消息误触发。

### case: SNT-005

- user_prompt: 把这句话润色得更自然：QoderWork长文写作 Skill 已上线灰度。
- expected_trigger: false
- expected_doc_type: none
- expected_behavior: 不触发 Skill，直接给短句润色。
- quality_focus: 避免短句润色误触发。

### case: SNT-006

- user_prompt: 给《QoderWork长文写作能力分析报告》起 5 个标题。
- expected_trigger: false
- expected_doc_type: none
- expected_behavior: 不触发 Skill，直接给标题候选。
- quality_focus: 避免标题任务误触发。

### case: SNT-007

- user_prompt: 用 3 条 bullet 总结这段内容，不超过 80 字。
- expected_trigger: false
- expected_doc_type: none
- expected_behavior: 不触发 Skill，直接做短摘要。
- quality_focus: 避免短摘要误触发。

### case: SNT-008

- user_prompt: 帮我回复一句：收到，我今天处理。
- expected_trigger: false
- expected_doc_type: none
- expected_behavior: 不触发 Skill，直接给短回复。
- quality_focus: 避免短回复误触发。

## missing_info_but_assumable

### case: MIA-001

- user_prompt: 帮我写一篇关于 Agent Skill 提升长文质量的博客。
- expected_trigger: true
- expected_doc_type: blog
- expected_behavior: 触发 Skill，默认受众为 Agent 产品和工程相关读者，输出中等篇幅博客，并在末尾说明关键假设。
- quality_focus: 合理假设、中心观点、可读性。

### case: MIA-002

- user_prompt: 写一份长文写作 Skill 的建设方案。
- expected_trigger: true
- expected_doc_type: proposal_or_plan
- expected_behavior: 触发 Skill，默认面向内部评审，声明范围假设，输出可执行方案。
- quality_focus: 方案完整性、范围边界、假设声明。

## missing_info_need_questions

### case: MINQ-001

- user_prompt: 帮我写一份报告。
- expected_trigger: true
- expected_doc_type: report
- expected_behavior: 触发 Skill，但信息严重不足，应先询问 3-5 个关键问题，或给出可填充报告框架。
- quality_focus: 避免无根据生成。

### case: MINQ-002

- user_prompt: 写一个对外发布的行业白皮书，要专业一点。
- expected_trigger: true
- expected_doc_type: report
- expected_behavior: 触发 Skill，但对外白皮书事实风险高，应询问主题、受众、数据来源、行业范围、发布目的等关键问题，或给出框架。
- quality_focus: 事实安全、高风险场景处理。
