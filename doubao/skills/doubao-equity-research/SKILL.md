---
name: doubao-equity-research
description: 面向 A 股、港股、美股及其他上市证券的专业股票研究与飞书报告交付，覆盖基本面、财报前瞻与解读、盈利模型更新、市场预期、估值、股价与事件、催化剂与风险、同业比较、股票筛选、论点跟踪、组合风险、市场复盘及跨上市地相对价值。单家标的基本面请优先使用doubao-public-company-analysis；估值建模请调用 doubao‑finance‑model‑builder。
---

# 股票研究

## 第一步：设置 delivery_mode

在检索、分析或起草前读取 `references/lark-doc-delivery.md` 并锁定模式。默认使用 `LARK_DOC`；仅当 query 明确适合用一至三句无损回答一个事实、口径或决策问题，且不需要结构化比较、导航、情景、复杂证据链、图示或高级组件时，使用 `TEXT`。无法确定或用户要求飞书文档时使用 `LARK_DOC`；query 很短本身不构成 `TEXT` 理由。

`TEXT` 条件失效或已生成高级组件时，立即升级为 `LARK_DOC`。不得因耗时、命令、认证或权限问题降级；阻塞时保持未完成。

在工作记录中建立交付清单，并在开始时运行 `scripts/delivery_gate.py --phase plan`。`LARK_DOC` 模式在完整正文起草和高级组件生成前，先按线上最新版 `lark-doc` 完成认证检查并创建文档骨架；最终写入、拉取复核后运行 `scripts/delivery_gate.py --phase final`。未通过最终门禁不得把任务表述为完成。

## 初始化与研究范围

设置 `delivery_mode` 后读取 `references/research-standards.md`、`references/writing-quality.md`、`references/accounting-basis-analysis.md` 和 `references/core-financial-snapshot.md`，锁定证券身份、信息截止日、分析窗口、币种、会计口径、用户要做的判断和正文信息预算。凡分析具体上市证券、公司、板块、股票池或组合，默认同时读取 `references/capability-financial-data-retrieval.md` 并建立核心金融与财务数据快照；只有确信这些数据不会改变答案时才可省略，并在交付清单记录理由。

取数后、比较前建立关键指标口径登记。IFRS/Non-IFRS、GAAP/Non-GAAP、reported/adjusted、归母/集团、基本/摊薄 EPS、单季/累计、FY/CY/TTM、实际/固定汇率等相似名称不得混写。完整调节表可得时运行 `scripts/accounting_basis_bridge.py`；不可得时并列展示法定与调整后口径并明确缺口，不猜测调节项。

## 选择能力

先把 query 拆成需要回答的决策问题，再选择能回答这些问题的最小能力集合。多个能力可以并行取证，最后合并结论；不要为追求全面机械加载全部文件。

| 决策问题 | 读取能力 |
|---|---|
| 标准化财务、行情、估值、一致预期、股本、公司行动或批量证券数据 | `references/capability-financial-data-retrieval.md` |
| 大盘、概念/板块、近期公司新闻、监管新闻、供应链/国际事件、美股与日韩市场传导 | `references/capability-market-news-context.md` |
| 行业景气、周期、产业链、竞争格局、公司行业位置 | `references/capability-sector-competition.md` |
| 公司如何赚钱、客户价值、单位经济、护城河 | `references/capability-business-model.md` |
| 收入利润、分部、利润率、现金流、资产负债表、ROIC、财报变化 | `references/capability-fundamentals.md` |
| 市场在预期什么、beat/miss、预期修正、非共识判断 | `references/capability-expectations.md` |
| 财报后模型更新、预测修订、指引或假设变化、旧新估值桥 | `references/capability-model-update.md` |
| 相对估值、内在价值、SOTP、反向 DCF、隐含假设 | `references/capability-valuation.md` |
| 区间涨跌、相对表现、事件窗口、量价与原因归因 | `references/capability-price-action.md` |
| 催化剂、风险、证伪条件、情景与赔率 | `references/capability-catalysts-risks.md` |
| 同业横向比较、可比公司差异 | `references/capability-peer-comparison.md` |
| 大样本候选排序、股票池筛选 | `references/capability-equity-screening.md` |
| 持仓集中、相关性、流动性、压力测试、对冲 | `references/capability-portfolio-risk.md` |
| 原投资逻辑复核、指标跟踪、状态和版本维护 | `references/capability-thesis-monitoring.md` |
| A/H 折溢价、H 股相对价值、跨上市地价差及所谓“套利”可执行性 | `references/capability-cross-listing-relative-value.md` |

金融数据检索是跨模块能力，不替代其他分析能力。股票相关分析默认选择它并优先调用 `/seed_finance_search`；不能因为用户没有逐项点名财务数据、报告篇幅有限或文档结构复杂而跳过。可省略边界和行业指标替换见 `core-financial-snapshot.md`。

## 默认组合

用户问题宽泛时使用以下默认组合，避免因措辞简短而漏掉关键维度：

- **公司分析、个股研究、基本面分析、深度研究**：核心金融与财务快照 + 市场与新闻环境（精简）+ 行业与竞争 + 商业模式 + 基本面 + 预期 + 估值 + 催化剂与风险。
- **一页纸、公司快照、会前准备**：核心金融与财务快照 + 近期重大新闻、行业/产业链位置、商业模式、估值和风险的内部检查；正文只保留最能改变判断的信息，不为覆盖维度扩写。
- **财报前瞻、业绩预览**：核心金融与财务快照 + 预期 + 基本面基线 + 催化剂与风险；冻结披露前预期快照，突出最影响股价反应的 3–5 个指标和情景。只有数据可靠时才补历史财报反应或期权隐含波动。
- **财报分析**：核心金融与财务快照 + 基本面 + 预期；先统一并清楚区分法定与调整后口径，必要时增加 IFRS/Non-IFRS 或 GAAP/Non-GAAP 差异桥、调整持续性和估值口径分析；用户关心财报后市场反应时再加价格归因。
- **盈利模型或预测更新**：模型更新 + 基本面 + 预期 + 估值；从旧预测到实际再到新预测建立修订桥，解释驱动变化和估值影响。涉及财报后价格反应时再加价格归因。
- **多空、买方投资逻辑或非共识判断**：行业与竞争 + 商业模式 + 基本面 + 预期 + 估值 + 催化剂与风险；先还原一致预期或价格隐含假设，再写差异认知、价值影响、催化剂和证伪条件。
- **股价为何涨跌/股价路径/事件窗口**：价格归因 + 核心金融与财务快照 + 市场与新闻环境；默认获取 OHLC，按数据门禁脚本生成 K 线或股价 HTML 并设为 `LARK_DOC`，仅按 `capability-price-action.md` 的明确例外退出；涉及行业共振时加行业与竞争，涉及盈利修正时加预期。
- **市场晨报/收盘复盘/周报**：市场与新闻环境；只展开能解释本地资产定价的板块、监管、国际和海外市场信息。
- **行业研究**：行业与竞争 + 市场与新闻环境；需要落到公司时加商业模式和基本面，需要横向选择时加同业比较。
- **股票筛选**：股票筛选；筛出候选后，需要解释相对差异时加同业比较，需要完整论证时再补公司分析能力。
- **A/H 或 H 股“套利”**：跨上市地相对价值 + 核心金融与财务快照 + 催化剂与风险；涉及价差历史路径时加价格归因。

若用户只问一个明确变量，只选相关能力。例如“净负债是否恶化”只需基本面；“当前价格隐含多少增长”只需估值，必要时补基本面输入。输出长短不改变能力选择。

默认组合只规定内部需要检查的能力，不按能力逐项设置正文栏目。调查范围可以较宽，公开正文只保留通过信息准入门槛的结论与证据。

开始取证前读取 `references/report-coverage-matrix.md`，按体裁判断大盘、板块、产业链、近期新闻、监管、海外和 A/H 是否应检查。矩阵是内部检查清单，不是正文目录：通过检查不等于必须写入；未达到 `writing-quality.md` 信息准入门槛的内容一律不进入报告。仅在工作记录中标为“不适用”“无重大影响”或“证据不足”，避免静默遗漏，也避免用低质量信息填充版面。

股票相关研究默认建立紧凑核心金融与财务快照。调查阶段可取更多字段，正文只保留 `core-financial-snapshot.md` 规定的 4–10 个高价值字段；若确实不相关，必须设置 `core_financial_data_status=not_relevant` 并给出具体理由。数据缺失时使用 `included_with_gaps`，不得把缺失等同于不相关。

## 合并结论

各能力先形成自己的结论、证据、边界和验证点，再回答跨模块传导：

`行业变量 → 公司业务与竞争位置 → 收入/利润/现金流 → 市场预期 → 估值 → 催化剂与风险`

先写总判断与成立条件，再按上面的因果链展开；每节使用“结论 → 证据 → 机制 → 含义/下一验证”顺序，避免按资料来源或检索顺序堆砌。只保留会改变用户判断的环节；结论冲突时并列高质量证据并说明采用理由，不强行统一。每个正文段落、表格和图必须映射到一个核心结论；无法映射、与前文重复或只有背景价值时删除。

起草交付物前读取 `references/suggested-writing-templates.md`。`LARK_DOC` 按体裁选择一个主模板并只嵌入必要模块，使用通用完整报告外壳完成交付；模板是可裁剪的写作骨架，不是固定目录或覆盖清单。`TEXT` 不使用报告模板，只给一至三句最核心结论。

## 数据获取

- 财务报表、分部数据、行情、复权价格、成交、估值、一致预期、分析师预测、股本、分红、公司行动和批量同业数据优先使用 `/seed_finance_search`。
- 公告原文、监管事实、管理层表述、会计附注和产品细节优先使用公司、交易所或监管机构的一手材料。
- 近期公司、监管、供应链和国际事件按 `capability-market-news-context.md` 记录事件发生日、首次公开日、信息可得日和对应交易时段；搜索摘要与匿名传闻只作线索。
- 跨市场分析对齐时区、交易日、币种和信息截止时刻；美股、日韩或海外期货只有存在可解释传导路径时才进入结论。
- A/H 数据必须核对股本类别、经济权益比例、汇率时点、交易日、公司行动、税费、融券与可转换性；不能把不可交割价差称为无风险套利。
- 数据库与一手披露冲突时，先核对证券、日期、财年、币种、单位、复权、合并范围和更新时间；法定事实以一手披露为准。
- 法定/报告口径与调整后口径冲突时不二选一：法定口径作为锚点，调整后口径按公司定义单列；统一期间、合并范围、税项、少数股东和股本基础后再计算差异、预期差或估值。
- `/seed_finance_search` 是获取方式，不是正文来源名称。引用结果中提供的数据集或来源标签，并记录查询截止日与字段口径。
- 按 `core-financial-snapshot.md` 先建立最小金融基线，再展开新闻、产业链、股价或估值解释；不得用纯叙事替代可得的规模、盈利、现金流/财务承受力与定价锚点。

## 计算与可视化工具

输入合同见 `references/script-usage.md`。先通过外部来源或 `/seed_finance_search` 取得数据，再将本地结构化输入交给脚本。只有计算会改变结论且输入充分时才运行；首次使用或修改后运行对应脚本的 `--self-test`。

- 市场与股价：`scripts/market_analysis.py`
- 组合风险：`scripts/portfolio_risk.py`
- 反向 DCF：`scripts/reverse_dcf.py`
- 股票筛选：`scripts/equity_screen.py`
- 事实校验和读者版引用：`scripts/report_pipeline.py`
- 飞书高级图表（股价、K 线、多象限 HTML block）：`scripts/lark_visuals.py`
- 会计口径调节桥（IFRS/Non-IFRS、GAAP/Non-GAAP、reported/adjusted）：`scripts/accounting_basis_bridge.py`
- 飞书扩展图表（趋势、瀑布、热力图、时间线、传导链 HTML block）：`scripts/lark_charts.py`
- A/H 与跨上市地折溢价：`scripts/cross_listing_spread.py`
- 交付模式计划/完成态校验：`scripts/delivery_gate.py`

脚本输出属于计算方法，不是事实来源。正文引用必须回到公告、监管文件、数据库或其他可核验外部输入。

选择股价路径与事件归因能力时必须读取 `references/advanced-lark-visuals.md`。完整 OHLC 可得时运行 `lark_visuals.py kline`；只有收盘价或分时价格时运行 `lark_visuals.py price`，绝不根据收盘价伪造 OHLC。脚本生成的 `.html` 仅作为飞书 HTML block 的中间载荷：生成后必须按最新版 `lark-doc` 流程实际写入目标飞书文档，并拉取文档复核 block 的渲染。不得手写图表 HTML，不得把 `.html` 文件、附件、源码或本地链接当作交付物；脚本不能表达时改用合适的表格、段落或省略该图。

其他分析只要确实需要图表，也先读取 `advanced-lark-visuals.md`，按关系选择趋势、瀑布、热力图、时间线、象限或传导链，并优先使用 `lark_charts.py`/`lark_visuals.py` 生成 HTML block。每张图必须对应一个独立决策问题；小表或短段更清楚、与已有图重复、数据质量不足或只能起装饰作用时不生成。多象限分析不得用未解释的综合分数制造伪精确。

## 交付

执行任务开始时锁定的 `delivery_mode`：`TEXT` 只用一至三句给出最核心结论，不展开分析；`LARK_DOC` 将完整分析写入飞书文档，聊天中同样只给一至三句核心结论和文档链接。

创建或更新飞书文档前，必须读取当前线上环境中的最新版 `lark-doc` skill 及其对本次写入要求的引用文件，以确认命令、XML 和组件语法；未完成该步骤不得写入。不要依赖记忆、本文示例或随包快照替代在线读取。`LARK_DOC` 模式应在完整起草前先创建文档骨架，避免分析完成后再因交付步骤被遗漏。

完成全部正文与组件写入后，重新拉取最终文档，并按 `references/writing-quality.md` 做一次独立审阅和删稿：检查核心结论、因果链、数字口径、章节导航、引用和实际渲染，再删除低质量信息、重复结论、泛泛背景、无传导新闻、无用组件和不改变判断的段落。逐项核对聊天摘要、正文、表格、图表和附录中的关键数据；同一对象、期间、单位和口径不得出现不同数值。冲突时先采用更权威来源，权威性相当时采用截至信息截止日更新的数据，并从上游修正所有相关产物。若复核后有修改，写回并再次拉取确认无误。复杂文档应先锁定 `required_sections`，通过压缩节内表达和移除弱证据控制篇幅，不得仅因篇幅较长而删除、合并或降级承担不同分析功能的必需章节。

**最终交付硬门禁：**交付前将 `data_consistency_verified=true` 写入交付清单并运行 `scripts/delivery_gate.py --phase final`。所有模式都必须通过核心金融数据与跨产物数据一致性校验；`TEXT` 还须保持短回答条件且未生成高级组件。`LARK_DOC` 还须保留全部 `required_sections`、取得可访问链接、完成最后写入后的拉取复核并通过写作与视觉检查。任何 Markdown 无法保真表达的组件均要求 `LARK_DOC`；认证或写入失败时保持未完成，不得改用聊天文本或本地文件替代。完整规则见 `references/lark-doc-delivery.md` 的“最终交付门禁”。

完整报告或用户要求可复核引用时，建立 `facts.json` 和含 `{fact:claim_id}` 的源稿，再运行 `report_pipeline.py`。飞书文档可用 `--format lark-xml` 生成带读者引用的数据来源章节；Markdown 只是可选中间格式，不是交付上限。完整研究输出最后使用：`免责声明：本内容仅供研究与信息参考，不构成投资建议。`
