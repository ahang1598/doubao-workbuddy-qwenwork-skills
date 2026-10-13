---
name: industry-analysis
description: "回答中文行业基本面问题，适用于行业、价值链环节、产品市场或技术路线的定义、空间、周期、竞争、利润迁移、传导、比较、进入与产业投资机会分析；不用于股票交易阶段研判或单家公司独立估值。"
---

# 行业分析

## 用途与路由

围绕用户真正要解决的问题回答行业基本面，而不是默认生成完整报告。先识别决策、对象和相互依赖关系，再选择最小充分层级：

- `direct`：一个局部定义、价值链位置、商业模式或边界明确的单一原因。直接回答并给必要限定，不展开全行业框架。
- `brief`：一个聚焦判断，需要说明决定性驱动、约束、因果机制和验证条件。只选择影响该判断的维度。
- `full`：周期、增长、竞争、跨行业比较或进入决策包含耦合关系，需要可比证据、替代解释、敏感性和条件情景。`deep` 是 `full` 的别名。

路由依据用户意图和推理依赖，不依据关键词或篇幅。答案、报告和文件是独立的交付选择；默认内联回答，`full` 也可以很简洁，且不自动意味着报告或文件。尊重用户明确限定的范围和简洁度。层级、停止和降级边界不清楚时，读取 [references/analysis-mode-implementation.json](references/analysis-mode-implementation.json)。

行业基本面包括银行和保险。系统研究任何股票板块的行情阶段、内部市场强弱或深层交易持续性属于 `finance-sector`；单板块日度简报可属于 `market-briefing`。行业价格、供需和库存周期仍属于本 Skill。公司案例可用于行业比较，单家公司质量或估值属于相邻公司研究范围；说明边界，不声称已调用其他 Skill。

## 专业方法

先把问题改写为可验证的判断：用户要知道什么、哪个结果会改变决策、什么证据会推翻结论？只固定与问题实质相关的时点、地区、对象、产品、单位和统计基础。

不同任务使用不同主线，不能套用统一章节：

- 周期：需求流量 → 生产商与渠道库存 → 有效产能与利用率 → 价格传导 → 利润恢复、停复产与退出条件。
- 长期空间：付款方与预算 → 用户或设备、渗透、频次、用量、价格或组合 → 历史基线 → 供应和制度约束。
- 竞争：同口径市场与分母 → 客户准入、成本、良率、技术、认证、转换或分销壁垒 → 进入退出与替代路线 → 优势验证。
- 市场进入：痛点与预算 → 技术、标准、认证和采购门槛 → 替代方案与分销 → 单位经济性和可复制性 → 分阶段证明与停止条件。
- 产业投资机会：瓶颈 → 受益或受压环节 → 利润由谁保留 → 资本、现金流和估值实现条件。

定义、利润迁移、政策或技术传导、路线比较及上述任务的完整判据，按当前问题读取 [references/industry-methods.md](references/industry-methods.md) 的对应小节，不通读无关任务。若用户要求报告，报告结构跟随该任务主线；否则直接作答。

解释机制时同时给出决定性驱动、阻断约束、最有力的替代解释和验证或证伪信号。事实缺口只降低依赖该事实的结论，不迫使无关部分一并失效，也不强制给出数字预测。

行业经济结构明确符合供应链、网络、资产负债表或单元门店模式时，才读取 [references/structure-lenses.md](references/structure-lenses.md) 的相应一节；不要把透镜变成固定模板。

## 证据与检索约束

在每个重大材料或证据节点，区分已观察事实、来源估计或预测、自有情景和推断。要求来源、发布日期、数据基期、口径、相关主张和方法可追溯；历史 `as-of` 只使用当时已发布的信息。涉及数值、预测、交易事件、跨来源比较或图表时，读取 [references/evidence-discipline.md](references/evidence-discipline.md) 的相关部分。

检索必须遵守随包提供的 [references/financial-search-policy.md](references/financial-search-policy.md)：公开金融数据优先 `seed_finance_search`，回退以及法规、政策检索使用 `general_search`。工具通道不改变主张确定性。不得虚构来源、缺失类别、汇率、平减因子、链接、图表或已经检索和验证的结果。

封闭材料只禁止外部搜索，不自动禁止用户已授权的离线读取、计算和文件生成。用户明确要求零工具时，不得调用任何工具、加载参考文件或执行脚本；只使用对话内材料，能够可靠完成的简单运算应展示公式，其余数字保持未知并披露限制。

<!-- finance-search-policy:start -->
## 数据获取与材料边界

优先已有材料，不因金融主题自动联网。材料充分、封闭材料或用户禁搜时为 `off`；私有材料缺失、无授权或对象/时点/法域歧义改变搜索方向时为 `blocked`，不搜索，必要时最多问三个方向性问题。公开数据不能替代私有材料。
- 工具：公开金融数据先用 `seed_finance_search`；未提供、失败或证据不合格时在剩余预算内回退 `general_search` 并说明原因；法规政策直接用后者查官方原文。只用宿主真实工具及 schema，不编造别名、参数或调用，不传入敏感信息。
- 预算：核心结论必要检索 `required` 最多 4 次，背景补充 `optional` 最多 2 次；`off` / `blocked` 为 0。两工具共享计数，失败、重试、回退均计次，切换路由不重置；证据充分即停。
- 证据：关键事实保留可追溯来源、时点和口径；无合格证据或冲突无法裁决时保留未知，只交付材料支持的部分，不把未检索写成已核验。
- 执行入口：首次搜索前读取[金融检索细则](references/financial-search-policy.md)，确认来源层级、降级与停止条件；同任务无需重复读取。无法读取时不搜索。

以上是全局硬约束，不因位置后移而放宽。禁搜不自动禁止已授权的离线读取、计算和文件生成；用户明确零工具时不得调用任何工具，含补读参考文件。其他资源中的概括性禁工具描述服从本任务的实际授权边界。
<!-- finance-search-policy:end -->

## 确定性计算

仅当计算影响结论且允许执行本地脚本时，使用 `scripts/industry_metrics.py`。调用前统一对象、地区、单位、期间和统计基础；调用后先检查退出状态、结构化错误、`status`、单位和异常值，再解释结果。脚本不验证来源，也不自动换算或补全数据。完整输入、输出、单位、错误和限制见 [references/helper-input.md](references/helper-input.md)。简单定义或无需计算的问题不要运行脚本。

任务需要重复的期间-情景经济性、项目样本状态汇总、系统到设备构成桥接、数值决策门槛或多个明确请求项核对时，可改用可选的 `scripts/industry_workflow.py`，并只选择实际需要的独立分支。完整精确接口见 [references/workflow-input.md](references/workflow-input.md)。模型先从已授权材料提取显式事实、范围、期间、情景和依赖关系；脚本只验证结构化字段与确定性算术，不以元数据标签证明来源、指标语义或总体可比。

涉及源值换算、倍数或增长率时，先抄录源值和源单元格单位，再声明规范单位与显式正因子；源事实单位与声明单位不一致时停止换算。抽出的事实序列或残差处理可用 `claims` 核对；工作流计算结果形成的方向，必须按结果 ID 逐句核对，不能把计算结果回填成事实。存在明确回收目标且同一现金恒等式成立时，才用 `thresholds` 反解所需单位数或补贴率，并先核对净资本开支恒等式。用户要求空间路径、累计/新增关系或多期表时，才用 `path` 按期初、新增、退役、期末输出；退休未知只保留部分小计。封闭材料纪律独立触发，不因为使用表格或脚本而放宽。

执行前检查单位、基础、存量/流量、分母、价格基础及截止时点是否兼容；已知不兼容时不得聚合。执行后按结果 ID 复用同一数值到正文和表格，不独立重算标题数字。`missing`、`conflict`、`incompatible` 和 `infeasible` 只降低依赖它们的输出；已知部分只能作为明确的部分小计。没有数值目标或必要系数时给条件判断，不制造反向阈值。局部问题不承担全工作流开销。

## 停止与交付检查

在结论、机制、关键限定和验证条件已经回答用户问题后停止，不为了显得完整而增加行业通用章节。交付前确认：

- 回答的是用户的问题，而不是一个邻近但更容易的问题。
- 所有重大数字和时点可追溯，跨口径比较已有桥接或明确不可比。
- 结论强度没有超过证据，未知项和条件已经显式保留。
- 图表与正文使用相同来源、日期、单位和范围，自有情景已标记。
- 用户明确请求的每项输出已经回答，或给出具体且局部的证据限制；脚本覆盖结果不能替代与原问题和最终答案的人工逐项比对。
- 计算结果保留期间、情景、依赖、证据类别、单位和基础；样本未冒充总体，潜在可获得支出未冒充收入或利润，反向阈值和观察门槛通过同一前向关系与时间顺序检查。
- 源值和源单位同时可见；规模词、币种、存量/流量属性没有在换算中被静默删除。
- 全称方向或总括词被任一事实/结果 ID 推翻时，正文原句已改写；冲突并列，残差处理没有在后文改口。
- 未知退休、未知因子或其他缺失项没有被当成零；部分小计和完整结果明确区分。
- 回收期或其他阈值不达标时，已给出受同一恒等式支持的反解，或明确说明缺哪个变量；不发明其他反向变量。
- 多期路径不只给终点；期初、新增、退役和期末的勾稽关系对每个请求期间可见。
- 封闭材料中的每个数字都能追溯到授权材料或显式自有情景；减产、闲置和永久退出没有互相替代。
- 只有实际检查过请求的文件后才声称交付；不得推断交易、监控、安装、外部发布或上传授权。

<!-- analysis-modes:start -->
## Analysis Depth And Delivery

Contract: `3b7d6a0a727943dac100fdd7eb40aff237d63e2a96a16ddea6251dcc0259ed32`. Select `analysis_tier=direct|brief|full` (`deep` means `full`) independently of `output_form=answer|report|files` and business axes. Full means deeper reasoning, NOT an automatic report or file. Default to answering the question; generate reports/files only when requested. Respect safety/scope and explicit user choices, then semantic dependencies; choose the smallest sufficient tier. Do not route by prompt length or keyword counts. Brief handles a focused evidence chain; full handles coupled comparisons, competing explanations or scenario dependencies. All tiers share evidence quality, not mandatory chapters. Degrade only affected claims. Use inline routing without scripts; zero-tool tasks must not load extra files.

When detailed routing is needed read [mode rules](references/analysis-modes.md); for the selected tier's task-specific checks and conditional resources read [tier implementation](references/analysis-mode-implementation.json). Do not preload other tiers' references.
<!-- analysis-modes:end -->
