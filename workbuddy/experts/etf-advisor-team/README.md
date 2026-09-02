# ETF投资顾问专家团（ETF Investment Advisory Team）

根据用户当前的 ETF 持仓，多角色协同输出接下来的 ETF 买卖调仓建议。

## 类型

Team 型（多角色协作团队，1 主理人 + 4 成员）

## 功能

用户只需提供 ETF 持仓明细（代码+份额/金额+成本价）与投资风格（稳健/均衡/积极），专家团按标准 SOP 协作：

- **Phase 0** 主理人（甄权衡/首席配置官）收集持仓与投资风格，缺失必追问；并**当场推导战略配置中枢**（权益/防御/跨境商品目标比例 + 核心-卫星框架，数值由 AI 依据用户画像与市场环境推导，无预设固定比例），作为一切调仓的锚
- **Phase 1** 三路并行：持仓诊断师（康持盈）做组合结构体检、红线初筛与**同赛道工具择优替换**（流动性一票否决/跟踪精度/费率/特殊品类约束）；行情技术分析师（马图南）逐只给出趋势/估值分位/资金信号与关键价位；宏观行业研究员（洪观远）定位宏观周期、给出**战术偏离建议**（幅度由其按周期置信度与资产性价比自行推导）、排序行业景气度、评估 QDII 跨境环境与债券久期结构
- **Phase 2** 风险合规官（严守成）终审：红线一票否决、**止损止盈纪律（触发线由其按标的波动率与用户回撤容忍当场推导，最高优先级）**、交易成本约束、风格匹配与仓位纪律裁定（所有限值当场推导并写明理由）、合规措辞把关，逐条给出"通过/降仓通过/否决"裁决
- **Phase 3** 主理人汇编《ETF 交易建议书》：配置中枢与偏离度 + **信号融合表**（结构/宏观/技术三方信号 + 冲突仲裁）+ 逐只操作卡（结论/目标仓位/价位区间/分批计划/止盈止损/触发条件）+ 调仓执行顺序（含成本估算）+ 风险提示 + **三类再平衡触发规则**（定期/阈值/事件驱动，频率与阈值由主理人推导，成本管控优先）

核心理念：**一切决策数值由 AI 专家当场推导并说明理由，不设人工定死的止盈止损规则与配置比例**——同一用户在不同时点、不同标的上得到的纪律数值可以也应该不同。

另设 **Workflow D 建议复盘与归因**：对比历史建议与实际结果，归因到资产配置/行业轮动/工具选品/执行纪律四个来源，胜率低的信号后续降权。

覆盖 A 股场内 ETF/LOF（宽基、行业主题、策略、债券、商品、跨境 QDII）。所有结论明确唯一可执行，禁止模糊表述；关键数据标注来源与时间。

## v1.6.0 修订：数据源替代——删除 17 个可替代爬取脚本，内置 westock-data skill

**动机**：公开发布的专家包中爬取脚本越少越好。经逐命令实测验证，17 个采集脚本的能力可由 **westock-data**（腾讯自选股数据命令集，公共 npm 包 `westock-data-skillhub`，`npx` 调用、无需鉴权、仅需 nodejs ≥ 18 与网络）完全覆盖，v1.6.0 将其删除并在包内新增 `skills/westock-data` 作为第一优先数据源。

**已删除 17 个脚本**（替代命令映射见 `references/scripts_guide.md` 零节）：

`etf_detail_scraper` / `etf_flow_scraper` / `fund_detail_md` / `fund_info_scraper` / `fund_risk_checker` / `market_overview_scraper` / `sector_scraper` / `capital_flow_scraper` / `stock_quote_scraper` / `index_membership_scraper` / `macro_data_scraper` / `money_market_rate_scraper` / `us_macro_scraper` / `us_inflation_expectation_scraper` / `industry_report_scraper` / `stock_fundamental_scraper` / `macro_batch_runner`（该编排器引用了不存在的 global_market_scraper，属陈旧断链，一并删除）

**保留脚本的理由**（现 79 个根脚本 + 5 个 quant 子模块）：
- **无替代**：期权 IV/PCR、中金所持仓、期货基差、实时五档盘口、AH 溢价、REITs、碳市场/药监/半导体等细分行业高频、部委政策原文、Playwright 动态页抓取
- **部分替代**：逐只指数估值分位（csindex）、6大宽基估值（market_valuation）、两融明细、北向 Smart Money、场外基金筛选/估值、黄金 SPDR 持仓
- **本地计算**：图表渲染、质量校验（GATE 门禁）、量化评分、个股依赖链

**调用优先级**：westock-data 命令 → 保留脚本兜底 → WebSearch/WebFetch 降级。

## v1.4.3 修订：修复成员 spawn 故障（Task agent not available）

**故障现象**：主理人按原协作规则（`subagent_type` 直传成员 Agent ID）spawn 成员时，三个成员任务全部瞬时失败（0-3ms），报错 `Task agent etf-XXX is not available`。

**根因**：平台运行时的 Agent 工具只识别内置 agent 类型 + 项目 `.codebuddy/agents/` 目录注册的自定义 agent，**不扫描专家包 `agents/` 目录**——team-spec 的调度规范与运行时能力存在平台级缺口，非本专家包配置错误（plugin.json 的 agents/teamInfo/members 均合规）。

**修复**：主理人 MD「协作规则」第 5 条改为——`subagent_type` 固定传 `"general-purpose"`，`name` 传成员 Agent ID 作通信标识，且 **spawn 前必须读取成员 `agents/{Agent ID}.md` 全文，将角色定义提炼注入 prompt 开头**（再接任务简报：用户画像/统一数据底稿/配置中枢/具体任务）。已在真实会话验证可行（宏观研究员以该方式成功产出完整报告）。若未来平台支持专家包成员作为 subagent_type，可回退直传方式以省去角色注入。

## v1.4.2 修订：恢复 web_fetcher.py，保留 Playwright JS 渲染抓取能力

v1.4.2 恢复 `scripts/web_fetcher.py`（Playwright 无头浏览器抓取，788行）——它是脚本层唯一能处理 JS 渲染页面（CME FedWatch / 东方财富动态报表等）、Cloudflare 挑战、表格结构化提取的工具，WorkBuddy 自带的 WebFetch（LLM 层）返回 AI 摘要而非原始 HTML，无法在脚本层替代。`web_searcher.py` 不恢复（搜索由 WorkBuddy 自带 WebSearch 工具替代）。playwright + html2text 作为**可选依赖**保留。

## v1.4.0 新增：脚本库（后经 v1.6.0 精简）

v1.4.0 为 `scripts/` 目录扩充 96 个 Python 脚本 + 5 个 quant 子模块（去重整合、语法校验全部通过）；**v1.6.0 删除其中 17 个可由 westock-data skill 替代的脚本，现存 79 个根脚本 + 5 个 quant 子模块 + 1 个内置 skill**，覆盖：

| 分类 | 脚本数 | 核心脚本 |
|------|--------|---------|
| 共享基础设施 | 4 | _utf8_bootstrap / web_fetcher（Playwright，可选）/ assertion_runner / output_index_builder |
| ETF/基金专属兜底 | 4 | etf_screener / fund_screener / fund_detail_scraper / fund_valuation_scraper |
| 指数估值采集 | 3 | csindex_valuation_scraper / market_valuation_scraper |
| 宏观与政策采集 | 4 | pbc_policy_scraper / gov_policy_scraper / fed_treasury_scraper / financial_regulator_scraper |
| 市场与情绪采集 | 3 | market_sentiment_scraper / a_share_sentiment_scraper / risk_index_scraper |
| 资金面采集 | 8 | margin_balance_scraper / northbound_smart_money_classifier / option_iv_scraper |
| 行业景气度采集 | 16 | industry_rotation_scorer / semiconductor_scraper / pharma_approval_scraper |
| 行情技术采集 | 6 | realtime_quote_enhanced / technical_indicator / ah_premium_scraper |
| 图表与渲染 | 5 | chart_generator / md2html_report |
| 质量校验 | 9 | report_quality_checker / numeric_consistency_auditor / data_freshness_auditor |
| 量化评分 | 1+quant包5 | quant_scorer / quant/ 子包 |
| 个股专属依赖 | 15 | 作为质量校验脚本的依赖保留 |
| 债券市场 | 1 | bond_market_scraper |

> ETF 详情/K线/技术指标/资金流/宏观指标/行业研报/个股财报等结构化数据**第一优先用内置 westock-data skill**（`npx -y westock-data-skillhub@1.0.5 <命令>`）。

**依赖**：`pip install -r requirements.txt`（核心仅 requests + beautifulsoup4；web_fetcher.py 的 Playwright 抓取为可选依赖；网页搜索用 WorkBuddy 自带 WebSearch）

**调用原则**：脚本只采集数据与做客观计算，**不产出决策**。所有买卖/仓位/止盈止损数值由对应 AI 成员当场推导。完整清单见 `references/scripts_guide.md`。

## v1.3.0 新增：知识库与脚本

v1.3.0 新增 `references/` 知识库与 `scripts/` 目录，沉淀框架方法论，使团队从"方法论全塞在 agent .md"升级为"框架沉淀复用 + 决策当场推导"双层架构。

### references/ 知识库（10 个文件）

| 文件 | 用途 |
|------|------|
| `data_sources.md` | ETF/指数/宏观/行业/资金面数据源注册表 |
| `macro_analysis_framework.md` | 宏观周期定位/周期-资产映射/战术偏离推导/跨境与债券结构 |
| `market_regime_signals.md` | 市场顶部/底部六大信号/ERP/政策力度打分 |
| `etf_selection_criteria.md` | ETF 量化筛选五级标准/工具替换候选表规范 |
| `sector_rotation_framework.md` | 行业景气度四维研判/景气度-估值匹配/风格轮动 |
| `quality_gate.md` | 质量门禁 GATE 0-3/自检清单/冲突仲裁规则 |
| `delivery_spec.md` | 对话vs报告模式/三段式/信源标注/合规措辞 |
| `output_template.md` | 《ETF 交易建议书》八模块结构化模板 |
| `scripts_guide.md` | 可用脚本盘点/ETF适用性/改造要点 |
| `industry_sources/` | 23行业专属信源库（5大类子目录+各类总览+README索引） |

### 主理人 SOP 新增 Phase 4

主理人（甄权衡）在 Phase 3 汇编建议书后，新增 **Phase 4 质量门禁自检**（GATE 0 格式骨架 → GATE 1 结构完整性 → GATE 2 内容闭环 → GATE 3 数据溯源与合规），报告模式下必须四道门禁全过方可交付。

### R9 合规设计

框架沉淀时严格区分：
- **可保留**：测量刻度（估值五档分位、政策力度打分维度、周期阶段判定标准）与客观市场事实判据（清盘线、流动性门槛、溢价率异常）
- **已剥离**：一切固定决策阈值（如"浮亏≥15%止损""±5%再平衡""≥60分积极布局"）——这些由对应成员结合用户画像与市场环境当场推导

## 使用示例

- 你好！请把你的ETF持仓发给我（代码+份额/金额+成本价），并告诉我你的投资风格（稳健/均衡/积极），我会组织团队为你出具接下来的买卖调仓建议。
- 这是我当前的ETF持仓，帮我诊断组合结构是否健康，接下来该加仓还是减仓？
- 帮我看看手里的行业主题ETF（如半导体/恒生科技）现在该止盈还是继续持有？

## 头像

头像已自动生成在 `avatars/` 目录下。如需替换为自定义头像，要求：
- 格式：PNG（推荐）或 JPG
- 尺寸：512×512 px
- 大小：单张不超过 500KB

## 安装

将专家包目录（本目录的上一级 `etf-advisor-team/`）放置到 WorkBuddy 专家插件目录下：

```
<WorkBuddy专家插件目录>/etf-advisor-team/
```

> 例如：`C:\Users\<你的用户名>\.workbuddy\plugins\marketplaces\my-experts\plugins\etf-advisor-team\`

按需安装依赖：

```bash
# Python 脚本依赖（核心仅 requests + beautifulsoup4；Playwright 抓取为可选）
pip install -r requirements.txt

# westock-data skill（第一优先数据源，v1.6.0 起内置）
# 需要 nodejs ≥ 18 与网络，无需安装与鉴权：
npx -y westock-data-skillhub@1.0.5 market-overview   # 验证示例
```

## 打包分享

```bash
zip -r etf-advisor-team.zip etf-advisor-team/
```

> ⚠️ 以上内容由 AI 基于公开信息整理生成，仅供参考，不构成任何投资建议或个股推荐。投资有风险，决策需谨慎。
