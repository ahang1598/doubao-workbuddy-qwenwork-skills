# 脚本清单与调用指南

> **本文件定位**：etf-advisor-team v1.6.0 内置脚本与 westock-data skill 的完整清单，按分类组织，标注用途、优先级与调用方式。
>
> **v1.6.0 结构变化**：原 96 个根脚本中 **17 个可完全替代的采集脚本已删除**，由内置 `skills/westock-data`（腾讯自选股数据命令集，`npx` 调用、无需鉴权）承接；保留 **79 个根脚本 + 5 个 quant 子模块**（不可替代或仅部分替代，作兜底链路）。
>
> **调用原则**：数据获取**第一优先用 westock-data skill 命令**（结构化、口径统一）；westock 不覆盖的场景用保留脚本兜底；两者皆无再降级 WebSearch/WebFetch。**所有决策由 AI 成员推导**，脚本与命令只采集数据与做客观计算，不产出决策。

---

## 环境准备

```bash
pip install -r requirements.txt
# 核心：requests + beautifulsoup4
# 渲染：openpyxl + jinja2 + markdown + markupsafe + urllib3
# 可选：pytdx（通达信协议）
# 可选：playwright + html2text（web_fetcher.py 的 JS 渲染抓取，动态页面场景需要）

# westock-data skill（第一优先数据源）：
npx -y westock-data-skillhub@1.0.5 <命令> [参数]
# 需要 nodejs ≥ 18 与网络；无需安装、无需鉴权
```

所有保留脚本自带 UTF-8 bootstrap（`_utf8_bootstrap.py`），Windows GBK 终端下安全输出中文+emoji，幂等。

---

## 零、westock-data 内置 skill（第一优先数据源）⭐

命令语法与字段详见 `skills/westock-data/SKILL.md` 与 `skills/westock-data/references/commands.md`。**v1.6.0 删除的 17 个脚本与替代命令对照**：

| 已删除脚本 | westock-data 替代命令 | 覆盖内容 |
|-----------|----------------------|---------|
| etf_detail_scraper.py | `etf detail <代码>` + `etf financial` / `etf holders` | 规模/费率/份额变动/折溢价/4级分类/经理/Top20持仓（实测 60+ 字段） |
| etf_flow_scraper.py | `etf detail`（sharesChg/sharesChgRatio 字段） | 份额变动/资金流方向 |
| fund_detail_md.py / fund_info_scraper.py / fund_risk_checker.py | `etf detail` / `etf company` | 基金详情/公司信息/清盘流动性判断（规模/成交额字段） |
| market_overview_scraper.py | `market-overview --type all`（8 维度） | 大盘画像/收盘统计/涨跌分布/两融/估值/风格轮动 |
| sector_scraper.py | `sector ranking` + `fund flow pt*` | 板块涨幅榜/资金流入/北向热门板块 |
| capital_flow_scraper.py | `fund flow <代码>`（A股/港股/板块，支持区间） | 主力/散户/超大单资金流 |
| stock_quote_scraper.py | `kline <代码> --period day --limit 2000 --fq qfq` | A股/港/美/ETF/期货/外汇/可转债 K 线 |
| index_membership_scraper.py | `index constituent sh000300,hkHSTECH` | 指数成分股（支持批量） |
| macro_data_scraper.py | `macro indicator cn_core / cn_cpi_ppi / cn_pmi / cn_lpr` 等 32 个中国指标 | PMI/CPI/PPI/M2/社融/LPR/消费/投资/财政 |
| money_market_rate_scraper.py | `macro indicator cn_fundcost --year <年>` | SHIBOR 全期限/回购利率（实测 155 条序列） |
| us_macro_scraper.py | `macro indicator us_employment / us_eco_growth / us_confidence` 等 | 美国就业/通胀/信心/货币/财政/能源/地产 |
| us_inflation_expectation_scraper.py | `macro indicator us_inflation --date <日期>` | CPI/PCE/PPI + 通胀预期（实测 253 条） |
| industry_report_scraper.py | `report list pt<行业代码>` + `report detail <id>` | 行业/个股研报列表与全文 |
| stock_fundamental_scraper.py | `finance <代码> --num 4`（三大报表批量） | 利润/资产负债/现金流 |
| macro_batch_runner.py | `macro indicator` 系列按需组合调用 | 宏观批量采集（原编排器已删） |

**westock-data 能力边界（超出时用保留脚本兜底）**：
- `kline` 为**历史/延时数据，非实时行情**——盘中现价与五档盘口用 `realtime_quote_enhanced.py`
- **ETF 级两融无数据**（实测）——市场级两融用 `market-overview --type margin`；明细用 `margin_balance_scraper.py`
- 逐只跟踪指数的 PE/PB 历史分位（如中证500指数本身）无直接命令——用 `csindex_valuation_scraper.py`；板块级分位可 `sector valuation pt*`
- `fund flow` 美股不支持（仅 `fund short`）；`chip` 筹码仅沪深 A 股个股
- 期权 IV/PCR、期货持仓/基差、REITs、AH 溢价、细分行业高频数据——无对应，用保留脚本
- 需要自然语言检索基金产品/资讯/研报时，若环境有 NeoData 等 connector 可用则用之（非内置，不强依赖）

---

## 一、共享基础设施（4 个）

| 脚本 | 用途 |
|------|------|
| `_utf8_bootstrap.py` | UTF-8 I/O 初始化，所有脚本自动加载 |
| `web_fetcher.py` | Playwright 无头浏览器抓取（JS 渲染/Cloudflare 挑战/表格提取，**可选依赖**：`pip install playwright html2text && playwright install chromium`）——westock 与保留脚本均无法处理的动态页面兜底 |
| `assertion_runner.py` | 断言运行器（校验用） |
| `output_index_builder.py` | 输出索引构建 |

---

## 二、ETF/基金专属兜底（4 个）⭐ 持仓诊断师

| 脚本 | 用途 | 调用示例 |
|------|------|---------|
| `etf_screener.py` | ETF 多条件筛选（westock 仅支持按名搜索） | `python etf_screener.py --type 行业 --min-size 2` |
| `fund_screener.py` | 场外基金多条件筛选（场外仅作附带参考） | `python fund_screener.py --type etf` |
| `fund_detail_scraper.py` | 场外/LOF 基金详情（天天基金 HTML，fund_screener 依赖） | `python fund_detail_scraper.py 510300` |
| `fund_valuation_scraper.py` | 场外基金估值 | `python fund_valuation_scraper.py 510300` |

> ETF/LOF 的详情、费率、持仓、净值、份额变动**一律优先 westock-data**（`etf detail/nav/holders/financial`）。

---

## 三、指数估值采集（3 个）⭐ 行情技术分析师

| 脚本 | 用途 |
|------|------|
| `csindex_valuation_scraper.py` | 中证指数公司估值分位（PE/PB 历史分位）——**逐只跟踪指数**估值权威源（westock 仅板块级分位） |
| `index_valuation_scraper.py` | 指数估值（多源） |
| `market_valuation_scraper.py` | 6 大宽基 PE/PB 分位 + ERP（westock market-overview valuation 仅中证全指；ERP 可用 `macro indicator cn_premium_value`） |

---

## 四、宏观与政策采集（4 个）⭐ 宏观行业研究员

| 脚本 | 用途 |
|------|------|
| `pbc_policy_scraper.py` | 央行政策原文动态（OMO/MLF 数值已由 westock `cn_mlf`/`cn_fundcost` 覆盖，保留原文清单能力） |
| `gov_policy_scraper.py` | 发改委/财政部/工信部政策原文 |
| `fed_treasury_scraper.py` | 美债收益率曲线/美联储（事件类可辅以 westock `us_monetary` + `macro expect --area usa`） |
| `financial_regulator_scraper.py` | 金融监管动态 |

> **宏观指标数据（PMI/CPI/PPI/M2/社融/LPR/SHIBOR/国债收益率/美国宏观）一律优先 westock `macro indicator` 系列**（实测覆盖完整）。

---

## 五、市场与情绪采集（3 个）

| 脚本 | 用途 |
|------|------|
| `market_sentiment_scraper.py` | 市场情绪（破净率/换手率/两融占比——westock changedist/market-overview 部分覆盖） |
| `a_share_sentiment_scraper.py` | A 股情绪专项 |
| `risk_index_scraper.py` | 风险指数 |

> 大盘总览/涨跌分布/成交额**优先** `market-overview` 与 `changedist`。

---

## 六、资金面采集（8 个）⭐ 行情技术分析师+宏观行业研究员

| 脚本 | 用途 |
|------|------|
| `margin_balance_scraper.py` | 两融余额明细（市场级可用 `market-overview --type margin`；ETF 级明细保留脚本） |
| `option_iv_scraper.py` | 期权 IV/PCR/Skew（宽基 ETF 期权情绪）——**无替代** |
| `cffex_position_scraper.py` | 中金所股指期货前20席位持仓——**无替代** |
| `futures_basis_scraper.py` | 股指期货基差/升贴水——**无替代** |
| `northbound_smart_money_classifier.py` | 北向资金 Smart Money 分类（季度持仓可辅以 westock `fund north-holding`） |
| `northbound_seat_winrate.py` | 北向席位胜率 |
| `capital_tide_classifier.py` | 资金潮分类（上游数据优先 westock `fund flow`） |
| `main_force_cost_reverser.py` | 主力成本反推（上游数据优先 westock `fund flow`） |

> 个股/板块主力资金流**优先** `fund flow <代码|pt板块>`；北向板块持仓分布**优先** `fund north-holding pt<代码>`。

---

## 七、行业景气度采集（16 个）⭐ 宏观行业研究员核心

| 脚本 | 行业/用途 |
|------|----------|
| `industry_rotation_scorer.py` | 行业轮动评分（动量/资金/相对强弱；上游可由 `sector ranking`/`sector valuation` 供给） |
| `industry_chain_scraper.py` | 11 行业产业链高频数据（westock `sector oper` 覆盖 28 行业经营数据，部分重叠） |
| `agri_product_scraper.py` | 农产品价格（`sector oper agri` 部分覆盖） |
| `agriculture_scraper.py` | 农业综合 |
| `pharma_approval_scraper.py` | 药品审批/集采（医药 ETF）——**无替代** |
| `semiconductor_scraper.py` | 半导体设备/存储价（半导体 ETF）——**无替代** |
| `power_industry_scraper.py` | 电力行业（`macro indicator cn_installed_capacity` + `sector oper utils` 部分覆盖） |
| `carbon_market_scraper.py` | 碳市场（新能源/碳中和 ETF）——**无替代** |
| `metals_scraper.py` | 有色金属价格（LME 期货可辅 `search 有色 --type futures` + `kline hf_*`） |
| `gold_market_scraper.py` | 黄金市场（金价趋势可由 `kline fuGC` + `etf detail` 覆盖；SPDR 持仓/定盘价为本脚本独有） |
| `commodity_exchange_scraper.py` | 期货交易所数据 |
| `commodity_spot_scraper.py` | 大宗商品现货 |
| `eia_energy_scraper.py` | EIA 能源数据（能源 ETF；事件类可辅 westock `us_energy`） |
| `logistics_freight_scraper.py` | 物流运价（交运 ETF）——**无替代** |
| `reits_scraper.py` | REITs 数据——**无替代** |
| `china_property_scraper.py` | 中国房地产（`sector oper re` 部分覆盖） |

> 行业研报**一律优先** `report list pt<行业代码>` + `report detail <id>`；行业经营数据优先 `sector oper <行业>`；板块估值分位优先 `sector valuation pt<代码>`。

---

## 八、行情技术采集（6 个）⭐ 行情技术分析师

| 脚本 | 用途 |
|------|------|
| `realtime_quote_enhanced.py` | 增强实时行情（五档/盘口，四源融合）——**westock kline 为延时数据，实时场景必用本脚本** |
| `technical_indicator.py` | 技术指标本地计算（支撑压力/Fib/综合评分等增强项；标准指标 MACD/RSI/KDJ/BOLL **优先 westock `technical`**） |
| `ah_premium_scraper.py` | AH 股溢价（恒生科技/港股 ETF）——**无替代** |
| `fib_timing_alerter.py` | 斐波那契时序提醒（K线上游优先 westock `kline`，经 --kline-file 传入） |
| `volume_price_classifier.py` | 量价分类器（同上） |
| `volume_tier_analyzer.py` | 量级分析（同上） |

---

## 九、图表与渲染（5 个）

`chart_generator.py`（SVG 图表）/ `chart_injector.py`（图表注入 HTML）/ `md2html_report.py`（MD→HTML）/ `report_components.py` / `report_renderer.py`

## 十、质量校验（9 个）

| 脚本 | 用途 | ETF 适用性 |
|------|------|-----------|
| `report_quality_checker.py` | 报告质量门禁校验 | ⚠️ 含个股专属门禁，ETF 用需简化 |
| `report_quality_validator.py` | 报告质量验证 | ⚠️ 同上 |
| `numeric_consistency_auditor.py` | 数值一致性审计 | ✅ 通用 |
| `data_freshness_auditor.py` | 数据时效审计 | ✅ 通用 |
| `source_citation_auditor.py` | 信源引用审计 | ✅ 通用 |
| `gate_all.py` | GATE 编排（串行门禁） | ⚠️ 含个股专属阶段 |
| `html_gate.py` | HTML 产物终检 | ✅ 通用 |
| `prereg_validator.py` | 预注册校验 | ⚠️ 含个股专属 |
| `decision_writing_gate.py` | 决策写作门禁 | ⚠️ 含个股专属 |

## 十一、量化评分（1 + quant 子包 5 个）

`quant_scorer.py` + `quant/`（decision/factors/risk/valuation）

## 十二、个股专属依赖模块（15 个，作为质量校验脚本的依赖保留）

被质量校验脚本（report_quality_checker/gate_all 等）import，保留以确保 import 完整。ETF 团队**通常不直接调用**：

`chip_distribution_analyzer.py` / `calibration_review.py` / `why_chain_validator.py` / `decomposition_tree_validator.py` / `devils_advocate_validator.py` / `capital_allocation_validator.py` / `reverse_valuation_validator.py` / `behavioral_bias_detector.py` / `competition_evolution_validator.py` / `forecast_quality_validator.py` / `resonance_divergence_validator.py` / `cross_face_reconciliation_validator.py` / `derivation_chain_auditor.py` / `g_combination_verifier.py` / `stock_three_statement_projector.py`

## 十三、债券市场（1 个）

`bond_market_scraper.py`（债券 ETF 久期/收益率；国债收益率曲线**优先** westock `macro indicator cn_yield_curve` + `cn_term_spread`）

---

## 调用注意事项

### 1. 数据接口变更
- 2024-08-19 起沪深交易所停止实时披露北向资金个股买卖额 → `northbound_*` 脚本已做 fallback
- 东方财富 DataCenter 报表名不定期变更 → 保留脚本采用多报表名级联策略
- westock 命令失败或无数据时降级保留脚本 → 再降级 WebSearch/WebFetch

### 2. D 类伪信源禁令
- 严禁爬取付费墙数据（Wind/Bloomberg/iFinD/Choice 等）
- 付费数据通过 `web_search site:<域名>` + 第二信源双轨获取

### 3. 输出落盘
- 采集数据建议落盘到工作区 `FinancialData/` 目录
- 文件命名：`{code}_*.json` 或 `{topic}_*.md`
- 报告引用时标注原始公开 URL，不标本地路径

### 4. 决策铁律
脚本与 westock 命令只采集数据与做客观计算（如技术指标、估值分位），**不产出决策**。所有买卖/仓位/止盈止损数值由对应 AI 成员当场推导。
