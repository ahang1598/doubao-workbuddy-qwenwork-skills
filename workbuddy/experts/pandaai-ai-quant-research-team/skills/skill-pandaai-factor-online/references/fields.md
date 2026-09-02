# PandaAI Data Fields / 可用字段

> Field-name index compiled from the official list. Field names are case-insensitive in formula mode.
> 字段索引。公式模式中字段名大小写均可。
> Source / 出处: https://www.pandaai.online/community/article/176

8 price/volume fields + 340 fundamental fields (348 total).

## Backtest factor catalog / 回测因子目录

A larger catalog exported from the platform's backtest factor list — 949 entries across fourteen
tables. Availability in formula mode can differ from the data API, so validate an unfamiliar field
on a short window before building on it.

The platform's list also contains an alpha101 table, deliberately not mirrored here: those
expressions are public, every model already knows them, and in a competition they are the most
crowded starting point there is. Ask for them by name if you want them.

平台回测因子清单导出的更大目录，十四张表共 949 条。公式模式下的可用性可能与数据接口不同，
用到陌生字段时先在短区间验证一次再往上搭。

平台清单里还有一张 alpha101 表，这里刻意没有收录：那些表达式是公开的，模型本来就会背，
而且在比赛里是最拥挤的起点。需要的话直接点名要。

| File | Table | Entries |
|---|---|---|
| [fields-cashflow-statement.md](fields-cashflow-statement.md) | 现金流量表 / Cash flow statement | 70 |
| [fields-balance-sheet.md](fields-balance-sheet.md) | 资产负债表 / Balance sheet | 156 |
| [fields-income-statement.md](fields-income-statement.md) | 利润表 / Income statement | 91 |
| [fields-valuation.md](fields-valuation.md) | 估值 / Valuation ratios | 37 |
| [fields-cashflow-derived.md](fields-cashflow-derived.md) | 现金流衍生 / Derived cash-flow metrics | 26 |
| [fields-financial-derived.md](fields-financial-derived.md) | 财务指标衍生 / Derived financial metrics | 111 |
| [fields-growth-derived.md](fields-growth-derived.md) | 增长指标衍生 / Derived growth metrics | 33 |
| [fields-operating-derived.md](fields-operating-derived.md) | 经营指标衍生 / Derived operating metrics | 94 |
| [fields-ma-indicators.md](fields-ma-indicators.md) | 均线类指标 / Moving-average indicators | 15 |
| [fields-oscillators.md](fields-oscillators.md) | 超买超卖指标 / Overbought / oversold indicators | 23 |
| [fields-volume-indicators.md](fields-volume-indicators.md) | 能量指标 / Volume and energy indicators | 14 |
| [fields-barra.md](fields-barra.md) | Barra因子 / Barra risk factors | 9 |
| [fields-cal-date.md](fields-cal-date.md) | cal_date因子 / Daily calculated factors | 230 |
| [fields-cal-mins.md](fields-cal-mins.md) | cal_mins因子 / Intraday calculated factors | 40 |

Financial-statement tables also carry derived fields: append `_mrq_n` (n = 1–12) to a base field to
read the value from the n-th most recent report before the query date, with the bare field being the
current period.
财报三张表还带衍生字段：在原字段后加 `_mrq_n`（n 为 1–12）表示查询日往前第 n 期财报中的该字段值，
不带后缀即当期。

---

## Formula-mode base fields / 公式模式基础字段

## Price & volume / 量价

| Field | 中文名称 |
| --- | --- |
| `open` | 开盘价 |
| `close` | 收盘价 |
| `high` | 最高价 |
| `low` | 最低价 |
| `volume` | 成交量 |
| `amount` | 成交额 |
| `turnover` | 换手率 |
| `market_cap` | 市值 |

## Fundamentals / 基本面

Fundamental fields carry a period suffix: `_lyr` = last fiscal year, `_ttm` = trailing twelve months.
基本面字段带期间后缀：`_lyr` 为上一会计年度，`_ttm` 为滚动 12 个月。

| Field | 中文名称 |
| --- | --- |
| `revenue` | 营业总收入 |
| `operating_revenue` | 营业收入 |
| `net_interest_income` | 利息净收入 |
| `net_commission_income` | 手续费及佣金净收入 |
| `commission_income` | 手续费及佣金收入 |
| `commission_expense` | 手续费及佣金支出 |
| `net_proxy_security_income` | 代理买卖证券业务净收入 |
| `sub_issue_security_income` | 证券承销业务净收入 |
| `net_trust_income` | 受托客户资产管理业务净收入 |
| `earned_premiums` | 已赚保费 |
| `premiums_income` | 保险业务收入 |
| `reinsurance_income` | 分保费收入 |
| `reinsurance` | 分出保费 |
| `unearned_premium_reserve` | 未到期责任准备金 |
| `total_expense` | 营业总成本 |
| `refunded_premiums` | 退保金 |
| `compensation_expense` | 赔付支出 |
| `amortization_expense` | 摊回赔付支出 |
| `premium_reserve` | 保险责任准备金 |
| `amortization_premium_reserve` | 摊回保险责任准备金 |
| `policy_dividend_payout` | 保单红利支出 |
| `reinsurance_cost` | 分保费用 |
| `other_operating_revenue` | 其他经营收入 |
| `other_operating_cost` | 其他经营成本 |
| `r_n_d` | 研发费用 |
| `other_net_income` | 非经营性净收益 |
| `net_open_hedge_income` | 净敞口套期收益 |
| `other_revenue` | 其他收益 |
| `credit_asset_impairment` | 信用资产减值损失 |
| `o_n_a_expense` | 业务及管理费用 |
| `amortization_reinsurance_cost` | 摊回分保费用 |
| `insurance_commission_expense` | 保险手续费及佣金支出 |
| `disposal_income_on_asset` | 资产处置收益 |
| `cost_of_goods_sold` | 营业成本 |
| `sales_tax` | 营业税 |
| `gross_profit` | 主营业务利润 |
| `selling_expense` | 销售费用 |
| `ga_expense` | 管理费用 |
| `financing_expense` | 财务费用 |
| `financing_interest_income` | 利息收入(财务费用) |
| `financing_interest_expense` | 利息支出(财务费用) |
| `exchange_gains_or_losses` | 兑汇损益 |
| `profit_from_operation` | 营业利润 |
| `invest_income_associates` | 对联营合营企业的投资收益 |
| `fair_value_change_income` | 公允价值变动净收益 |
| `investment_income` | 投资收益 |
| `asset_impairment` | 资产减值损失 |
| `interest_income` | 利息收入 |
| `interest_expense` | 利息支出 |
| `non_operating_revenue` | 营业外收入 |
| `non_operating_expense` | 营业外支出 |
| `disposal_loss_on_asset` | 非流动资产处置净损失 |
| `other_effecting_total_profits_items` | 影响利润总额的其他科目 |
| `profit_before_tax` | 利润总额 |
| `income_tax` | 所得税 |
| `other_effecting_net_profits_items` | 影响净利润的其他科目 |
| `net_profit` | 净利润 |
| `non_recurring_pnl` | 非经常性损益 |
| `net_profit_deduct_non_recurring_pnl` | 扣除非经常性损益后的净利润 |
| `classified_by_continuity_operation` | 按经营持续性分类 |
| `continuous_operation_net_profit` | 持续经营净利润 |
| `discontinued_operation_net_profit` | 终止经营净利润 |
| `classified_by_ownership` | 按所有权归属分类 |
| `net_profit_parent_company` | 归属母公司净利润 |
| `minority_profit` | 少数股东损益 |
| `other_income` | 其他综合收益 |
| `other_income_unclassified_income_statement` | 以后不能重分类进损益表的其他综合收益 |
| `remearsured_other_income` | 重新计量设定收益计划净负债或净资产的变动 |
| `other_income_equity_unclassified_income_statement` | 权益法下在被投资单位不能重分类进损益表的其他综合收益中享有的份额 |
| `other_equity_instruments_change` | 其他权益工具投资公允价值变动 |
| `corporate_credit_risk_change` | 企业自身信用风险公允价值变动 |
| `other_income_classified_income_statement` | 以后能重分类进损益表的其他综合收益 |
| `other_income_equity_classified_income_statement` | 权益法下在被投资单位能重分类进损益表的其他综合收益中享有的份额 |
| `financial_asset_available_for_sale_change` | 可供出售金融资产公允价值变动损益 |
| `financial_asset_hold_to_maturity_change` | 持有至到期投资重分类为可供出售金融资产损益 |
| `cash_flow_hedging_effective_portion` | 现金流量套期损益的有效部分 |
| `foreign_currency_statement_converted_difference` | 外币财务报表分析折算差额 |
| `others` | 其他 |
| `other_debt_investment_change` | 其他债权投资公允价值变动 |
| `assets_reclassified_other_income` | 金融资产重分类计入其他综合收益的金额 |
| `other_debt_investment_reserve` | 其他债权投资信用减值准备 |
| `other_income_minority` | 归属于少数股东的其他综合收益总额 |
| `total_income` | 综合收益总额 |
| `total_income_parent_company` | 归属于母公司所有者的综合收益总额 |
| `total_income_minority` | 归属于少数股东的综合收益总额 |
| `basic_earnings_per_share` | 基本每股收益 |
| `fully_diluted_earnings_per_share` | 稀释每股收益 |
| `adjust_asset_impairment` | 资产减值损失 |
| `adjust_credit_asset_impairment` | 信用减值损失 |
| `cash_received_from_sales_of_goods` | 销售商品、提供劳务收到的现金 |
| `refunds_of_taxes` | 收到的税费返还 |
| `net_deposit_increase` | 客户存款和同业存放款项净增加额 |
| `net_increase_from_central_bank` | 向中央银行借款净增加额 |
| `net_increase_from_other_financial_institutions` | 向其他金融机构拆入资金净增加额 |
| `draw_back_canceled_loans` | 收回已核销贷款 |
| `cash_received_from_interests_and_commissions` | 收取利息、手续费及佣金的现金 |
| `net_increase_from_disposing_financial_assets` | 处置交易性金融资产净增加额 |
| `net_increase_from_repurchasing_business` | 回购业务资金净增加额 |
| `cash_received_from_original_insurance` | 收到原保险合同保费取得的现金 |
| `cash_received_from_reinsurance` | 收到再保业务现金净额 |
| `net_increase_from_insurer_deposit_investment` | 保户储金及投资款净增加额 |
| `net_increase_from_financial_institutions` | 拆入资金净增加额 |
| `cash_received_from_proxy_security` | 代理买卖证券收到的现金净额 |
| `cash_received_from_sub_issue_security` | 代理承销证券收到的现金净额 |
| `cash_from_other_operating_activities` | 收到其它与经营活动有关的现金 |
| `cash_from_operating_activities` | 经营活动现金流入小计 |
| `cash_paid_for_goods_and_services` | 购买商品、接受劳务支付的现金 |
| `assets_depreciation_reserves` | 资产减值准备 |
| `exchange_rate_change_effect` | 汇率变动对现金及现金等价物的影响 |
| `other_effecting_cash_equivalent_items` | 影响现金及现金等价物的其他科目 |
| `cash_equivalent_increase` | 现金及现金等价物净增加额 |
| `begin_period_cash_equivalent` | 期初现金及现金等价物余额 |
| `end_period_cash_equivalent` | 期末现金及现金等价物余额 |
| `cash_paid_for_employee` | 支付给职工以及为职工支付的现金 |
| `cash_paid_for_taxes` | 支付的各项税费 |
| `net_increase_from_loans_and_advances` | 客户贷款及垫款净增加额 |
| `net_increase_from_central_bank_and_banks` | 存放中央银行和同业款项净增加额 |
| `net_increase_from_lending_capital` | 拆出资金净增加额 |
| `cash_paid_for_comissions` | 支付手续费及佣金的现金 |
| `cash_paid_for_orignal_insurance` | 支付原保险合同赔付款项的现金 |
| `cash_paid_for_reinsurance` | 支付再保业务现金净额 |
| `cash_paid_for_policy_dividends` | 支付保单红利的现金 |
| `net_increase_from_trading_financial_assets` | 为交易目的而持有的金融资产净增加额 |
| `net_increase_from_operating_buy_back` | 返售业务资金净增加额(经营) |
| `cash_paid_for_other_operation_activities` | 支付其他与经营活动有关的现金 |
| `cash_paid_for_operation_activities` | 经营活动现金流出小计 |
| `cash_flow_from_operating_activities` | 经营活动产生的现金流量净额 |
| `cash_received_from_investment` | 取得投资收益收到的现金 |
| `cash_received_from_disposal_of_asset` | 处置固定资产、无形资产和其他长期资产收回的现金净额 |
| `cash_received_from_other_investment_activities` | 收到其他与投资活动有关的现金 |
| `cash_received_from_investment_activities` | 投资活动现金流入小计 |
| `cash_paid_for_asset` | 购建固定资产、无形资产和其他长期资产所支付的现金 |
| `cash_paid_to_acquire_investment` | 投资支付的现金 |
| `cash_paid_for_other_investment_activities` | 支付其他与投资活动有关的现金 |
| `cash_paid_for_investment_activities` | 投资活动现金流出小计 |
| `cash_flow_from_investing_activities` | 投资活动产生的现金流量净额 |
| `cash_received_from_investors` | 吸收投资收到的现金 |
| `cash_received_from_minority_invest_subsidiaries` | 子公司吸收少数股东投资收到的现金 |
| `cash_received_from_issuing_security` | 发行债券收到的现金 |
| `cash_received_from_financial_institution_borrows` | 取得借款收到的现金 |
| `cash_received_from_issuing_equity_instruments` | 发行其他权益工具收到的现金 |
| `net_increase_from__financing_buy_back` | 回购业务资金净增加额(筹资) |
| `cash_received_from_other_financing_activities` | 收到其他与筹资活动有关的现金 |
| `cash_received_from_financing_activities` | 筹资活动现金流入小计 |
| `cash_paid_for_debt` | 偿还债务支付的现金 |
| `cash_paid_for_dividend_and_interest` | 分配股利、利润或偿付利息支付的现金 |
| `dividends_paid_to_minority_by_subsidiaries` | 子公司支付给少数股东的股利、利润或偿付的利息 |
| `cash_paid_for_other_financing_activities` | 支付其他与筹资活动有关的现金 |
| `cash_paid_to_financing_activities` | 筹资活动现金流出小计 |
| `cash_flow_from_financing_activities` | 筹资活动产生的现金流量净额 |
| `net_cash_deal_from_sub` | 处置子公司及其他营业单位收到的现金净额 |
| `net_cash_payment_from_sub` | 取得子公司及其他营业单位支付的现金净额 |
| `net_increase_in_pledge_loans` | 质押贷款净增加额 |
| `net_increase_from_investing_buy_back` | 返售业务资金净增加额(投资) |
| `net_inc_cash_and_equivalents` | 现金及现金等价物净增加额 |
| `fixed_asset_depreciation` | 固定资产折旧 |
| `deferred_expense_amortization` | 长期待摊费用摊销 |
| `intangible_asset_amortization` | 无形资产摊销 |
| `financial_asset_held_for_trading` | 交易性金融资产 |
| `cash_equivalent` | 货币资金 |
| `client_deposits` | 客户资金存款 |
| `bill_receivable` | 应收票据 |
| `dividend_receivable` | 应收股利 |
| `bill_accts_receivable` | 应收票据及应收账款 |
| `interest_receivable` | 应收利息 |
| `bad_debt_reserve` | 坏账准备 |
| `net_accts_receivable` | 应收账款净额 |
| `contract_assets` | 合同资产 |
| `prepayment` | 预付账款 |
| `financial_receivable` | 应收款项融资 |
| `financial_lease_receivable` | 应收融资租赁款 |
| `other_equity_investment` | 其他权益工具投资 |
| `other_illiquidy_financial_assets` | 其他非流动金融资产 |
| `non_current_asset_due_one_year` | 一年内到期的非流动资产 |
| `other_receivables_interest_dividend` | 其他应收款(含利息和股利) |
| `inventory` | 存货 |
| `consumable_biological_assets` | 消耗性生物资产 |
| `deferred_expense` | 待摊费用 |
| `assets_hold_for_sale` | 划分为持有待售的资产 |
| `contract_work` | 工程施工 |
| `other_current_assets` | 其他流动资产 |
| `current_assets` | 流动资产合计 |
| `financial_asset_available_for_sale` | 可供出售金融资产 |
| `non_current_liability_due_one_year` | 一年内到期的非流动负债 |
| `debt_investment` | 债权投资 |
| `other_debt_investment` | 其他债权投资 |
| `financial_asset_hold_to_maturity` | 持有至到期投资 |
| `real_estate_investment` | 投资性房地产 |
| `long_term_receivables` | 长期应收款 |
| `net_long_term_equity_investment` | 长期股权投资净额 |
| `accumulated_depreciation` | 累计折旧 |
| `depreciation_reserve` | 固定资产减值准备 |
| `net_fixed_assets` | 固定资产净额 |
| `total_fixed_assets` | 固定资产合计 |
| `engineer_material` | 工程物资 |
| `construction_in_progress` | 在建工程 |
| `total_construction_in_progress` | 在建工程合计 |
| `fixed_asset_to_be_disposed` | 固定资产清理 |
| `capitalized_biological_assets` | 生产性生物资产 |
| `oil_and_gas_assets` | 油气资产 |
| `intangible_assets` | 无形资产 |
| `seat_costs` | 交易席位费 |
| `impairment_intangible_assets` | 开发支出 |
| `use_right_assets` | 使用权资产 |
| `goodwill` | 商誉 |
| `long_term_deferred_expenses` | 长期待摊费用 |
| `deferred_income_tax_assets` | 递延所得税资产 |
| `other_non_current_assets` | 其他非流动资产 |
| `non_current_assets` | 非流动资产合计 |
| `loan_account_receivables` | 投资-贷款及应收款项 |
| `fund_providing` | 融出资金 |
| `reinsurance_reserve_receivable` | 应收分保合同准备金 |
| `settlement_provision` | 结算备付金 |
| `client_provision` | 客户备付金 |
| `interbank_deposits` | 存放同业款项 |
| `precious_metals` | 贵金属 |
| `lend_capital` | 拆出资金 |
| `derivative_financial_assets` | 衍生金融资产 |
| `resale_financial_assets` | 买入返售金融资产 |
| `loans_advances_to_customers` | 发放贷款和垫款 |
| `insurance_receivable` | 应收保费 |
| `subrogation_fee_receivable` | 应收代位追偿款 |
| `reinsurance_receivable` | 应收分保账款 |
| `unearned_reserve_receivable` | 应收分保未到期责任准备金 |
| `unclaimed_reserve_receivable` | 应收分保未决赔款准备金 |
| `life_reserve_receivable` | 应收分保寿险责任准备金 |
| `health_reserve_receivable` | 应收分保长期健康险责任准备金 |
| `insurer_mortgage_loan` | 保户质押贷款 |
| `fixed_deposits` | 定期存款 |
| `refundable_deposits` | 存出保证金 |
| `refundable_capital_deposits` | 存出资本保证金 |
| `independent_account_assets` | 独立账户资产 |
| `other_assets` | 其他资产 |
| `other_accts_receivable` | 其他应收款(原值) |
| `total_assets` | 总资产 |
| `mortgaged_loan` | 质押借款 |
| `short_term_loans` | 短期借款 |
| `financial_liabilities` | 交易性金融负债 |
| `notes_payable` | 应付票据 |
| `accts_payable` | 应付账款 |
| `bill_accts_payable` | 应付票据及应付账款 |
| `contract_liabilities` | 合同负债 |
| `advance_from_customers` | 预收账款 |
| `payroll_payable` | 应付职工薪酬 |
| `dividend_payable` | 应付股利 |
| `tax_payable` | 应交税费 |
| `interest_payable` | 应付利息 |
| `other_fees_payable` | 其他应交款 |
| `other_payable` | 其他应付款 |
| `other_payable_interest_dividend` | 其他应付款(含利息和股利) |
| `short_term_debt` | 应付短期债券 |
| `accrued_expense` | 预提费用 |
| `liabilities_hold_for_sale` | 划分为持有待售的负债 |
| `estimated_liabilities` | 预计负债 |
| `deferred_income` | 递延收益 |
| `long_term_liabilities_due_one_year` | 一年内到期的长期负债 |
| `other_current_liabilities` | 其他流动负债 |
| `current_liabilities` | 流动负债合计 |
| `long_term_loans` | 长期借款 |
| `bond_payable` | 应付债券 |
| `preference_shares` | 优先股 |
| `perpetual_bond` | 永续债(应付债券) |
| `long_term_payable` | 长期应付款 |
| `accrued_staff_costs` | 长期应付职工薪酬 |
| `grants_received` | 专项应付款 |
| `housing_revolving_funds` | 住房周转金 |
| `deferred_income_tax_liabilities` | 递延所得税负债 |
| `lease_liabilities` | 租赁负债 |
| `financial_lease_payable` | 应付融资租赁款 |
| `other_non_current_liabilities` | 其他非流动负债 |
| `non_current_liabilities` | 非流动负债合计 |
| `borrowings_from_central_banks` | 向中央银行借款 |
| `deposits_of_interbank` | 同业及其他金融机构存放款项 |
| `borrowings_capital` | 拆入资金 |
| `derivative_financial_liabilities` | 衍生金融负债 |
| `buy_back_security_proceeds` | 卖出回购金融资产款 |
| `deposits` | 吸收存款 |
| `proxy_security_proceeds` | 代理买卖证券款 |
| `sub_issue_security_proceeds` | 代理承销证券款 |
| `security_deposits_received` | 存入保证金 |
| `advance_insurance` | 预收保费 |
| `comission_payable` | 应付手续费及佣金 |
| `reinsurance_payable` | 应付分保账款 |
| `compensation_payable` | 应付赔付款 |
| `policy_dividend_payable` | 应付保单红利 |
| `deposits_from_interbank` | 吸收存款及同业存款 |
| `insurance_contract_reserve` | 保险合同准备金 |
| `insurer_deposit_investment` | 保户储金及投资款 |
| `uncertained_premium_reserve` | 未到期责任准备金 |
| `unclaimed_indemnity_reserve` | 未决赔款准备金 |
| `life_insurance_reserve` | 寿险责任准备金 |
| `health_insurance_reserve` | 长期健康险责任准备金 |
| `independent_account_liabilities` | 独立账户负债 |
| `other_liabilities` | 其他负债 |
| `deferred_revenue` | 递延收益(长期负债) |
| `total_liabilities` | 负债合计 |
| `paid_in_capital` | 实收资本(或股本) |
| `other_equity_instruments` | 其他权益工具 |
| `equity_preferred_stock` | 权益部分的优先股 |
| `perpetual_equity_debt` | 永续债(其他权益工具) |
| `capital_reserve` | 资本公积金 |
| `surplus_reserve` | 盈余公积 |
| `undistributed_profit` | 未分配利润 |
| `treasury_stock` | 库存股 |
| `equity_parent_company` | 归属于母公司所有者权益合计 |
| `total_equity` | 股东权益合计 |
| `general_reserve` | 一般风险准备 |
| `trade_risk_allowances` | 交易风险准备 |
| `foreign_currency_converted_difference` | 外币报表折算差额 |
| `uncertained_impairment_losses` | 未确认投资损失 |
| `other_reserves` | 其他储备 |
| `specific_reserve` | 专项储备 |
| `minority_interest` | 少数股东权益 |
| `total_equity_and_liabilities` | 负债和股东权益总计 |
| `pb_ratio_lyr` | 市净率lyr,当前股票总市值 |
| `pb_ratio_ttm` | 市净率ttm,当前股票总市值 |
| `pb_ratio_lf` | 市净率lf,当前股票总市值 |
| `book_to_market_ratio_lyr` | 账面市值比lyr,归属母公司股东权益合计lyr |
| `book_to_market_ratio_ttm` | 账面市值比 ttm,归属母公司股东权益合计ttm |
| `book_to_market_ratio_lf` | 账面市值比lf,归属母公司股东权益合计mrq |
| `dividend_yield_ttm` | 股息率ttm,连续四季度报表公布股利之和 |
| `peg_ratio_lyr` | PEG值lyr,市盈率lyr |
| `peg_ratio_ttm` | PEG值ttm,市盈率ttm |
| `ps_ratio_lyr` | 市销率lyr,总市值 |
| `ps_ratio_ttm` | 市销率ttm,总市值 |
| `sp_ratio_lyr` | 销售收益率lyr,营利收入lyr |
| `sp_ratio_ttm` | 销售收益率ttm,营利收入ttm |
| `market_cap_3` | 总市值 |
| `a_share_market_val` | A股市值,A股市值 = A股股本 x A股未复权收盘价 |
| `a_share_market_val_in_circulation` | 流通A股市值,流通A股市值 = 流通A股 * A股未复权收盘价 |
| `ev_lyr` | 企业价值lyr,总市值 + 负债合计lyr |
| `ev_ttm` | 企业价值ttm,总市值 + 负债合计ttm |
| `ev_lf` | 企业价值lf,总市值 + 负债合计mrq |
| `ev_no_cash_lyr` | 企业价值(不含货币资金)lyr |
| `ev_no_cash_ttm` | 企业价值(不含货币资金)ttm |
| `ev_no_cash_lf` | 企业价值(不含货币资金)lf |
| `ev_to_ebitda_lyr` | 企业倍数lyr,企业价值lyr |
| `ev_to_ebitda_ttm` | 企业倍数ttm,企业价值ttm |
| `ev_no_cash_to_ebit_lyr` | 企业倍数(不含货币资金)lyr,企业价值lyr |
| `ev_no_cash_to_ebit_ttm` | 企业倍数(不含货币资金)ttm,企业价值ttm |
