---
name: market-briefing
description: "围绕指定市场或关注领域生成问题驱动的盘前、盘后、盘中或区间市场简报，在明确时点、证据层和验证命题下解释变化并给出可复核观察；不用于交易执行、独立估值或系统性行业深研。"
---

# 市场简报

## 用途

围绕用户真正要判断的问题生成有证据边界的金融市场简报，而不是强制输出固定日报。结论前置，连接事实、市场传导、竞争解释、风险和后续验证；信息量与实际有效证据匹配。

## 适用范围

处理指定市场或自选板块、主题、资产、公司的盘前、盘后、盘中、区间及非交易日市场解释。范围为 `whole_market` 或 `custom_domains`；日度任务可再识别 `pre_market` 或 `post_market`，其他市场状态保持原义。

保留盘前全市场、盘前自选领域、盘后全市场、盘后自选领域四条路由。单一板块的完整日度简报在范围内。系统性板块阶段或内部强度研究、长期行业研究、独立公司估值、交易执行、提醒和账户操作按[范围与转向](references/scope-routing.md)处理，不因提到板块或选择完整深度而自动扩展任务。

## 专业方法

1. 先锁定用户问题、市场、时区、目标时段或区间、实际可用 `as-of`、发布版本和市场状态。关键时间歧义不能可靠消解时澄清或显式降级，不虚构当前时间、交易日或日程。
2. 选择业务路由，再选择最小充分分析层级。`direct` 回答局部判断，`brief` 解决相关问题链，`full` 处理耦合判断、可比分析或情景；`deep` 视为 `full`。篇幅、关键词和交付形式不能单独决定层级。
3. 用户点名必填要素、计算或文件时，先从当前 query 独立抽出预期要求。列了几项就验收几项；缺失项保持未知并说明缺口，不补模板项，也不把自报 `present` 当作完成证明。
4. 只纳入会改变结论、风险或观察计划的信息。按直接相关性、增量影响和确定性排序，合并同一事件的重复报道；安静时段允许没有明确主线。
5. 对重要方向建立内部命题：目标、范围、时间尺度、前提、证据、支持观察、证伪观察、替代解释及结论变化。风险缓解不自动等于整体看多；正面、负面、中性和混合观点采用同一方法。
6. 先分析直接影响；只有抵消性的二阶影响可能改变结论时才展开，并保持对象、范围和尺度一致。事实、有来源的共识、自身推断和因果结论分开。
7. 每份重要证据只保留一个当前状态与版本。最终决定性使用绑定当前命题、证据、信号、指标和条件 ID；修订后废弃旧绑定。已公开不等于已计价，价格反应也不能单独证明部分计价、资金来源、投资者意图或唯一因果。
8. 指标只定义一次对象、样本、运算、单位、窗口、基准和来源；条件只定义一次谓词及 `AND` / `OR` 关系。正文和文件引用规范 ID，不各自重写口径。缺失输入为未知，不填零；当前水平、单期变化、窗口均值、比率和复合收益保持不同身份。
9. 区分市场反应、参与、实际实施和经济传导。价格与成交可以验证反应或参与，不能单独确认政策、订单、需求、成本、融资或经营效果。需要实施或经营层证据而材料没有提供时，传导假说保持未知。
10. 使用共同截止、分类、样本和指标做比较。成交额或成交量不是净流入；广度必须有分母和样本；排序必须从已验收表或计算回读。
11. 交付形式与分析层级独立。默认直接回答；只有用户要求且权限允许时生成报告、文件或图表。正文保留决定性限定，不能把全部不确定性藏进附件或内部台账。

执行时先建立任务坐标和预期要求，再建立证据状态、规范指标与命题，完成语义裁决后写正文。只对实际适用部分检查时间、算术、引用、计数、要求、文件和哈希，并分别记录覆盖范围。最后从实际正文和重开文件回读；正文变化后废弃受影响的旧计数、哈希和绑定。

零工具任务仍在当前上下文内完成要素抽取、命题方向、时间尺度、指标身份、传导分层和最终语义回读，但不加载额外参考文件、不执行脚本、不生成虚假文件。简单事实短答不建立完整命题台账。

## 按需读取

- 日度盘前、盘后、自选领域、盘中、区间或非交易日任务：读取[业务路由](references/route-playbooks.md)。
- 当前或历史 `as-of`、跨市场日期、交易日、数据版本、发布状态或线索尺度会影响答案：读取[时间与证据边界](references/evidence-and-time.md)。
- 涉及归因、已计价、资金、广度、指数背离、行业比较、持续性或指标口径：读取[市场解释方法](references/market-reasoning.md)。
- 需要命题绑定、规范条件、实际计数或可复现文件：读取[命题验证与可复现交付](references/briefing-workflow.md)。只需既有观察检查时仍读取[助手输入契约](references/helper-input.md)并使用 `scripts/briefing_checks.py`；新能力按需使用 `scripts/briefing_workflow.py`。
- 可能越过日度简报、估值、交易、提醒或相邻研究边界：读取[范围与转向](references/scope-routing.md)。
- 需要选择或核对分析层级：读取[分析层级实现](references/analysis-mode-implementation.json)。
- 用户列举必填项、会话间隔或排序回读：读取[交付契约](references/delivery-contracts.md)。
- 用户指定报告、文件或图表：读取[交付方式](references/delivery.md)。

<!-- finance-search-policy:start -->
## 数据获取与材料边界

优先已有材料，不因金融主题自动联网。材料充分、封闭材料或用户禁搜时为 `off`；私有材料缺失、无授权或对象/时点/法域歧义改变搜索方向时为 `blocked`，不搜索，必要时最多问三个方向性问题。公开数据不能替代私有材料。
- 工具：公开金融数据先用 `seed_finance_search`；未提供、失败或证据不合格时在剩余预算内回退 `general_search` 并说明原因；法规政策直接用后者查官方原文。只用宿主真实工具及 schema，不编造别名、参数或调用，不传入敏感信息。
- 预算：核心结论必要检索 `required` 最多 4 次，背景补充 `optional` 最多 2 次；`off` / `blocked` 为 0。两工具共享计数，失败、重试、回退均计次，切换路由不重置；证据充分即停。
- 证据：关键事实保留可追溯来源、时点和口径；无合格证据或冲突无法裁决时保留未知，只交付材料支持的部分，不把未检索写成已核验。
- 执行入口：首次搜索前读取[金融检索细则](references/financial-search-policy.md)，确认来源层级、降级与停止条件；同任务无需重复读取。无法读取时不搜索。

以上是全局硬约束，不因位置后移而放宽。禁搜不自动禁止已授权的离线读取、计算和文件生成；用户明确零工具时不得调用任何工具，含补读参考文件。其他资源中的概括性禁工具描述服从本任务的实际授权边界。
<!-- finance-search-policy:end -->

## 交付检查

检查答案是否直接对应问题；时点、版本、字段、单位、基准、样本和缺失是否清楚；决定性判断是否绑定当前命题和证据；支持与证伪是否作用于同一对象、范围和尺度；市场反应、参与、实施和经营传导是否分开；规范指标和条件是否只定义一次；排序是否来自已验收行；文件是否由原始输入在新目录重建并重开；实际计数和哈希是否对应最终正文；确定性通过是否仍与语义和来源真实性审查分开。内部台账不作为普通用户交付物。

<!-- analysis-modes:start -->
## Analysis Depth And Delivery

Contract: `ab77698cd42257b8eafa67a8581b1397a2a3e20a6ebac4e255c9b7d67a84c39d`. Select `analysis_tier=direct|brief|full` (`deep` means `full`) independently of `output_form=answer|report|files` and business axes. Full means deeper reasoning, NOT an automatic report or file. Default to answering the question; generate reports/files only when requested. Respect safety/scope and explicit user choices, then semantic dependencies; choose the smallest sufficient tier. Do not route by prompt length or keyword counts. Brief handles a focused evidence chain; full handles coupled comparisons, competing explanations or scenario dependencies. All tiers share evidence quality, not mandatory chapters. Degrade only affected claims. Use inline routing without scripts; zero-tool tasks must not load extra files.

When detailed routing is needed read [mode rules](references/analysis-modes.md); for the selected tier's task-specific checks and conditional resources read [tier implementation](references/analysis-mode-implementation.json). Do not preload other tiers' references.
<!-- analysis-modes:end -->
