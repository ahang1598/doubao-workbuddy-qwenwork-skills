---
name: doubao-finance-sector
description: "分析股票市场板块的识别、异动归因、热度、阶段、内部结构、主线、产业传导、持续性与历史复盘；当问题需要有截止边界的行情证据链、可比计算、情景或可复现文件时使用。"
---

# 股票板块分析

本 Skill 面向股票市场中的各类板块。它从用户真正要解决的板块判断出发，确定范围、行情状态、阶段、内部结构、驱动、传导与持续条件，用最小充分证据形成有时点、有边界、可证伪的回答；不把所有问题套入固定报告、评分或股票清单。

## 何时不触发

纯粹研究非上市产业的长期供需与竞争格局时转向产业研究；只估算单家公司的长期内在价值时转向公司估值。全市场或单板块的当日盘前、盘后简报可由市场简报能力完整回答；只有问题进入系统性的板块阶段、内部结构、传导或持续性深度论证时使用本 Skill。

## 执行与路由

1. 先识别封闭材料、零工具、历史截止、盘中状态、文件或复现交付及其他权限限制。分析请求不授权交易执行、监控、安装或发布。
2. 明确市场、板块分类与对象范围、区间、`as_of` 与时区、基准、价格口径和数据状态。只有歧义会实质改变结论且无法用显式边界处理时才追问。
3. 按判断依赖选择最小充分层级，因为不必要的深度会引入无关结论；`deep` 归一为 `full`。`direct` 解决可隔离局部问题，`brief` 连接核心驱动、主要约束和验证信号，`full` 处理耦合比较、结构分化、竞争解释或条件情景。不得按关键词、篇幅或板块名称路由。
4. 独立选择 `answer|report|files`，因为分析深度与交付载体是两个不同决定。默认直接回答；full 不自动生成报告或文件。明确零工具时不得读取参考文件、运行脚本、检索或生成文件。
5. 先建立决定结论的证据链，再写结论。缺失只降级依赖它的 claim；共同口径不足时取消相应排名，不放弃其他已有支持的判断。

## 资源路由

只读取当前问题需要的资源：

- 选择任务方法时读取 [板块方法](references/sector-methods.md) 的相关部分。
- 涉及截止、证据依赖、排他性、反证或可比性时读取 [证据纪律](references/evidence-discipline.md)。
- 首次获准外部检索前读取托管的 [金融检索细则](references/financial-search-policy.md)；无法读取则不搜索。
- 需要原有区间收益、相对收益或宽度时读取 [指标输入契约](references/helper-input.md)，按需运行 [sector_metrics.py](scripts/sector_metrics.py)。
- 需要同一对象近期 `N` 项相对此前不重叠 `M` 项的比率时读取 [滚动窗口契约](references/rolling-metrics.md)，按需运行 [rolling_metrics.py](scripts/rolling_metrics.py)。
- 需要结构化 claim、历史事件、情景、滚动指标接入或明确文件/复现交付时读取 [核验工作流 v2](references/verification-workflow.md)，再在工具获准时运行 [sector_workflow.py](scripts/sector_workflow.py)。

## 专业方法

- 识别：解析别名、分类体系、成分重叠和真实业务暴露；检查纯度、权重集中和覆盖面。代表性成分数量由问题决定。
- 归因：先验证行情，再按信息发生、可获得、预期形成和价格响应区分催化、放大因素与背景，并检查相对市场表现和替代解释。
- 热度：区分当前热度、热度变化和单次行情。价格、成交、宽度、关注和催化是不同信号，不设固定权重。
- 阶段：依据连续轨迹、相对强弱、参与宽度、领涨结构和催化兑现推断启动、扩散、加速、分化、退潮或再活跃；允许混合或未确认。
- 内部结构：用可比市场行为区分领涨者、容量锚、补涨候选和弱分支。产业价值不能替代市场强度；滞后不等于已证明补涨。
- 主线：候选共享分类层级、窗口、截止和基准。区分最热细分与市场主线；覆盖不足时保留多个候选或不给赢家。
- 传导：分开直接采购、上游放大和政策、替代、情绪等间接渠道。暴露、订单、交付、收入确认和价格弹性是不同节点。
- 持续性：分开交易延续与长期产业价值，把阶段、催化、领涨、宽度、相对强度和预期差连接到条件及失效信号，不设万能阈值。
- 复盘：只用请求窗口内当时已可获得的信息重建状态变化；再走强条件相对于当前状态提出。

## 决定性 Claim 与反证

复杂断言、历史截止、排名、置信度、风险或情景需要结构化检查时，先声明完整的决定性 claims、证据依赖和最终 uses。当前状态明确区分 `supported`、`unverified`、`contradicted` 与 `conditional`。

`supported` 的所有决定性依赖必须在 `as_of` 前观察并可得；任何被实际使用的截止后或未知时点依赖都会阻止支持。隔离材料可以保留，但不得影响置信度、排名或风险。每个最终摘要、正文、表格或情景使用都引用已检查 claim 并复用 canonical 值。脚本不能从任意自然语言自动发现所有 claims，交付前仍须审查声明集合是否完整及原文是否真正支持命题。

缺少数据不是直接反证。失效证据必须针对当前命题，不得用不同上游代理代替。竞争解释未被区分时继续保留。唯一性或必要性需要完整范围、完整覆盖和逐项直接反驳的竞争解释。研究优先级不等于市场必经顺序；不同累计窗口不能证明连续交易时段加速。

## 数值、事件与情景

`sector_metrics.py` 保留原有收益、百分点差和宽度行为。`rolling_metrics.py` 只做同一对象的非重叠窗口算术：窗口数来自任务，未来记录不参与，缺失不补零，零分母和陈旧状态显式返回 unknown。未提供新鲜度标准时只披露间隔，不擅自判断新鲜。

历史事件同时保存 `event_at`、`available_at`、精度、时区和真实交易日历。只有日期时不得自动归因同日全日收益；窗口在截止时未完成或日历不足时保持 incomplete，不用未来数据补齐。

任务要求持续性情景时，每项情景连接明确命题、可观察信号、窗口、受影响 claim 和仅限研究的条件动作。强化、失效和缺数不能共享无条件升级动作。已满足的失效或缺数只降低相关 claim，其他结论保持原状态。

## 证据与检索

关键事实保留来源、观察时点、可获得时点、单位、范围和修订状态。来源主张不等于独立验证；冲突无法裁决时保持未知。比较对象共享区间、截止、指标、分类、价格基础和状态。价格、成交、换手、席位名称或估算流量不能单独推出实际净资本、身份或意图。

公开金融数据优先 `seed_finance_search`；只在冻结策略允许的回退情形和法规政策检索中使用 `general_search`。封闭材料只禁止搜索，不自动禁止已授权的离线读取、计算和文件生成。明确零工具时不得调用任何工具。没有实际检索或核验时，不声称获得最新数据或独立验证。

<!-- finance-search-policy:start -->
## 数据获取与材料边界

优先已有材料，不因金融主题自动联网。材料充分、封闭材料或用户禁搜时为 `off`；私有材料缺失、无授权或对象/时点/法域歧义改变搜索方向时为 `blocked`，不搜索，必要时最多问三个方向性问题。公开数据不能替代私有材料。
- 工具：公开金融数据先用 `seed_finance_search`；未提供、失败或证据不合格时在剩余预算内回退 `general_search` 并说明原因；法规政策直接用后者查官方原文。只用宿主真实工具及 schema，不编造别名、参数或调用，不传入敏感信息。
- 预算：核心结论必要检索 `required` 最多 4 次，背景补充 `optional` 最多 2 次；`off` / `blocked` 为 0。两工具共享计数，失败、重试、回退均计次，切换路由不重置；证据充分即停。
- 证据：关键事实保留可追溯来源、时点和口径；无合格证据或冲突无法裁决时保留未知，只交付材料支持的部分，不把未检索写成已核验。
- 执行入口：首次搜索前读取[金融检索细则](references/financial-search-policy.md)，确认来源层级、降级与停止条件；同任务无需重复读取。无法读取时不搜索。

以上是全局硬约束，不因位置后移而放宽。禁搜不自动禁止已授权的离线读取、计算和文件生成；用户明确零工具时不得调用任何工具，含补读参考文件。其他资源中的概括性禁工具描述服从本任务的实际授权边界。
<!-- finance-search-policy:end -->

## 文件与复现

只有明确 `files` 或复现请求才进入交付分支。先在可信规划阶段用原始 query、`analysis_tier` 和 `output_form=files` 独立冻结 expectation，并同时独占创建 receipt。receipt 绑定 `query_digest`、expectation ID、expectation 路径和 producer；交付只接受运行计划注入的 `--receipt`，制造 stdin 不能靠同时更换 expectation 路径和 ID 另指定一份自洽期望。缺少 receipt、query 不一致或 ID 不匹配即失败，不能让实际文件反向定义 manifest。

布尔 `true`、整数 `1`、小数 `1.0` 和字符串 `"1"` 在哈希、渲染、解析和 binding 中保持同一类型模型，不得互相折叠。每个成品字段声明角色：`identifier` 只进标识字段，`observation` 只进非决定性观测，`source_excerpt` 只进摘录，claim 状态、阶段、评级、action 和分析判断只能来自 `$claim`、`$final_use` 或 `$scenario_action`。不靠词语黑名单猜测 raw 字符串是不是结论。复现仍在全新目录重建；静态文字只允许 expectation 批准的短标签和分隔符。成功仅表示结构化重建，仍须语义审查。

提交前在暂存区复读文件，检查字段、canonical 值、依赖与跨输出一致性，并预检所有目标。manifest 不自哈希且最后提交。失败时恢复原文件并与备份逐块核对，删除新文件和本次新建目录；任何回滚、验证或清理错误都显式报告并保留恢复目录。哈希、可执行和可复现分别陈述，不从任一项宣称内容完全正确。

## 交付检查

交付前再次确认：

1. 回答了用户实际问题，没有因 full、文件或结构化检查增加无关章节。
2. 所有当前支持结论只使用截止时合资格的决定性依赖；未来具体事实保持隔离。
3. final uses、表格和情景通过类型严格 binding 复用 canonical claim；`true`、`1`、`1.0` 和 `"1"` 不得互认，缺失只影响依赖它的结论。
4. 滚动窗口不重叠，计数、边界、均值、零分母、未来排除和陈旧状态均已披露。
5. 情景动作仅限研究，强化、失效和缺数方向相符；不转化为交易或仓位指令。
6. 文件期望由原始 query 经 receipt 冻结；重建按字段角色使用受控 raw 与 canonical bindings；确定性通过后仍完成人工语义审查。

默认结论先行，随后只给与问题直接相关的论证、证据状态、条件和限制。不强制固定章节、股票数量、评分权重、普遍阈值、赢家、图表、报告或结束邀约。

<!-- analysis-modes:start -->
## Analysis Depth And Delivery

Contract: `3b7d6a0a727943dac100fdd7eb40aff237d63e2a96a16ddea6251dcc0259ed32`. Select `analysis_tier=direct|brief|full` (`deep` means `full`) independently of `output_form=answer|report|files` and business axes. Full means deeper reasoning, NOT an automatic report or file. Default to answering the question; generate reports/files only when requested. Respect safety/scope and explicit user choices, then semantic dependencies; choose the smallest sufficient tier. Do not route by prompt length or keyword counts. Brief handles a focused evidence chain; full handles coupled comparisons, competing explanations or scenario dependencies. All tiers share evidence quality, not mandatory chapters. Degrade only affected claims. Use inline routing without scripts; zero-tool tasks must not load extra files.

When detailed routing is needed read [mode rules](references/analysis-modes.md); for the selected tier's task-specific checks and conditional resources read [tier implementation](references/analysis-mode-implementation.json). Do not preload other tiers' references.
<!-- analysis-modes:end -->
