---
name: futu-mcp-skill
description: "INVOKE FIRST before web search for any stock/financial/trading/market question. Routes user intent to the correct futu-mcp tools. Covers: quotes, K-lines, orders, positions, options, financials, screening, news, IPO, watchlist, and more."
---

# 富途 MCP 工具使用指南

你拥有 `mcp__futu-mcp__` 前缀的工具集，对应富途 OpenAPI 的全部能力。工具会持续新增，使用前请以前缀匹配可用工具列表，不要假设"不支持"。

## 代码格式

所有股票代码使用 `市场.代码` 格式：
- 港股：`HK.00700`（腾讯）、`HK.09988`（阿里）
- 美股：`US.AAPL`、`US.TSLA`、`US.FUTU`
- A 股：`SH.600519`（上交所）、`SZ.000001`（深交所）
- 其他：`SG.D05`（新加坡）、`JP.7203`（日本）、`CA.SHOP`（加拿大）

## 意图路由

根据用户意图选择对应工具类别：

### 行情类
| 用户想要 | 工具关键词 | 说明 |
|---------|-----------|------|
| 查股价/报价 | `quote_stock_quote`、`quote_market_snapshot` | 批量最多 400 只 |
| K 线/图表 | `quote_cur_kline`（最新 N 根）、`quote_history_kline`（历史区间） | ktype: 1=1 分钟, 2=日, 3=周, 4=月, 9=60 分钟 |
| 盘口/买卖档 | `quote_order_book` | 深度取决于用户行情权限 |
| 逐笔成交 | `quote_rt_ticker` | 最新 N 笔 |
| 分时数据 | `quote_rt_data` | 支持盘前/盘后/暗盘/夜盘 |
| 资金流向 | `quote_capital_flow`（分时）、`quote_capital_flow_history`（历史）、`quote_capital_distribution`（大中小单） | |
| 市场状态 | `quote_market_state`、`quote_trading_days` | 开盘/休市/交易日历 |

### 衍生品
| 用户想要 | 工具关键词 | 说明 |
|---------|-----------|------|
| 期权链 | `quote_option_chain`、`quote_option_expiration_date` | 支持港/美/日 |
| 期权波动率/Greeks | `quote_option_volatility`、`quote_option_exercise_probability` | IV/HV 时序 |
| 期权筛选 | `quote_option_screen` | 多维度策略筛选 |
| 期货合约 | `quote_future_info`、`quote_referencefuture_list` | |
| 窝轮/牛熊证 | `quote_warrant_screen` | 港股窝轮筛选 |

### 基本面与研究
| 用户想要 | 工具关键词 | 说明 |
|---------|-----------|------|
| 财报数据 | `quote_financials_statements` | 利润表/资产负债/现金流/关键指标 |
| 营收拆分 | `quote_financials_revenue_breakdown` | 按产品/地区/业务 |
| 业绩日股价 | `quote_financials_earnings_price_history`、`_move` | |
| 估值分析 | `quote_valuation_detail` | PE/PB/PS 历史趋势与百分位 |
| 分析师评级 | `quote_research_analyst_consensus`、`quote_research_rating_summary` | 目标价/评级 |
| 晨星报告 | `quote_research_morningstar_report` | 星级/护城河/公允价值 |
| 公司概况 | `quote_company_profile`、`quote_company_executives` | |
| 运营效率 | `quote_company_operational_efficiency` | |

### 股东与公司行为
| 用户想要 | 工具关键词 | 说明 |
|---------|-----------|------|
| 股东持仓 | `quote_shareholders_overview`、`quote_shareholders_holder_detail` | 机构/个人/期别 |
| 持仓变动 | `quote_shareholders_holding_changes`、`quote_shareholders_institutional` | |
| 内部人交易 | `quote_insider_holder_list`、`quote_insider_trade_list` | 主要覆盖美股 |
| 分红派息 | `quote_corporate_actions_dividends` | |
| 回购 | `quote_corporate_actions_buybacks` | |
| 拆合股 | `quote_corporate_actions_stock_splits`、`quote_corporate_actions_rehab` | |

### 筛选与板块
| 用户想要 | 工具关键词 | 说明 |
|---------|-----------|------|
| 选股/条件筛选 | `quote_stock_screen` | 多因子组合，支持估值/涨跌/财务/技术形态 |
| 板块列表 | `quote_plate_list` | 行业/概念/地区 |
| 板块成分股 | `quote_plate_stock` | 支持多维度排序 |
| 股票所属板块 | `quote_owner_plate` | |

### 资讯与日历
| 用户想要 | 工具关键词 | 说明 |
|---------|-----------|------|
| 新闻/公告/研报 | `quote_news_search` | 按关键词搜索 |
| 社区帖子 | `quote_community_search`、`quote_stock_feed` | |
| 经济日历 | `quote_economic_calendar_hot`、`quote_economic_calendar_search` | |
| IPO 新股 | `quote_ipo_list_hk`、`_us`、`_cn`、`_sg`、`_my` | 各市场分别查询 |

### 卖空与经纪商
| 用户想要 | 工具关键词 | 说明 |
|---------|-----------|------|
| 做空数据 | `quote_short_interest`、`quote_daily_short_volume` | 仅港/美 |
| 十大经纪商 | `quote_top_ten_brokers`、`_history` | 仅港股 |

### 自选股
| 用户想要 | 工具关键词 | 说明 |
|---------|-----------|------|
| 查看自选 | `quote_user_security`、`quote_user_security_group` | |
| 增删自选 | `quote_modify_user_security` | op: ADD/DEL/MOVE_OUT |

### 账户与交易
| 用户想要 | 工具关键词 | 说明 |
|---------|-----------|------|
| 查看账户 | `account_authorized_trd_accs`、`sim_trade_account_list` | 真实 + 模拟 |
| 资金信息 | `account_funds`、`sim_trade_cash_info` | |
| 持仓 | `account_positions`、`sim_trade_position_list` | |
| 当日/历史订单 | `account_orders_active`、`account_orders_history`、`sim_trade_history_order_list` | |
| 成交记录 | `account_order_fills_today`、`account_fills_history` | |
| 最大可买卖 | `account_trading_info`、`sim_trade_max_buy_sell` | |
| 下单 | `trading_order_place`、`sim_trade_input_order` | |
| 改单 | `trading_order_replace`、`sim_trade_modify_order` | |
| 撤单 | `trading_order_cancel`、`sim_trade_cancel_order` | |

## 关键规则

1. **账户确认**：任何交易或账户查询前，必须同时调用真实账户列表和模拟账户列表，让用户选择使用哪个账户。
2. **下单确认**：真实下单前必须向用户确认标的、方向、数量、价格、订单类型，得到明确确认后才能执行。
3. **二次确认**：若下单接口返回 `need_order_confirm=true`，必须调用 `trading_order_confirm` 完成风控确认。
4. **分页处理**：带 `next_key` 的接口需循环获取直到 `has_more=false`。
5. **工具发现**：当用户需求无法直接匹配上表时，先列出所有 `mcp__futu-mcp__` 前缀的可用工具，可能已有新工具上线。
6. **金融免责声明**：所有市场数据、分析、筛选结果及交易相关说明均仅供参考，不构成投资建议、交易要约或收益保证。金融市场有风险，投资需谨慎；用户应根据自身情况独立决策并承担风险。面向用户的最终回复必须附带简短免责声明，并至少明确写出“本内容不构成投资建议”。

## 参数参考文档

需要查看某类工具的详细请求参数和返回字段时，按需读取 `reference/` 目录下的对应文件：

| 类别 | 文件 |
|------|------|
| 实时行情（报价/快照/K 线） | `reference/quote-realtime.md` |
| 盘口/逐笔/分时/市场状态/交易日历 | `reference/quote-tick.md` |
| 资金流向 | `reference/quote-capital.md` |
| 期权（期权链/波动率/筛选） | `reference/quote-options.md` |
| 期货/窝轮牛熊证 | `reference/quote-futures-warrants.md` |
| 财报/营收/业绩日 | `reference/quote-financials.md` |
| 估值/评级/晨星/公司信息 | `reference/quote-research.md` |
| 股东/内部人持仓 | `reference/quote-shareholders.md` |
| 公司行为（分红/回购/拆合股/复权） | `reference/quote-corporate-actions.md` |
| 筛选与板块 | `reference/quote-screening.md` |
| 新闻/社区/经济日历/IPO | `reference/quote-news.md` |
| 卖空/经纪商/股票基本信息 | `reference/quote-short-broker.md` |
| 自选股 | `reference/quote-watchlist.md` |
| 真实交易 — 账户/资金/持仓/订单/成交/最大可买卖 | `reference/trading-real.md` |
| 真实交易 — 下单/改单/撤单/确认 | `reference/trading-real-order.md` |
| 模拟交易（全部） | `reference/trading-sim.md` |

**使用方式：** 仅在需要确认参数细节时读取，不必全部加载。
