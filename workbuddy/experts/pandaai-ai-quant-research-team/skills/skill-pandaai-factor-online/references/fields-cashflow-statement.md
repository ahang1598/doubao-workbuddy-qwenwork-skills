# 现金流量表 / Cash flow statement

> Field catalog exported from the PandaAI backtest factor list.
> PandaAI 回测因子清单导出的字段目录。

> 注:此表中的字段含有衍生字段
> 衍生字段命名规则如下：原字段+_mrq_n(n为1~12)
> 表示距离当期查询日的最近前n期（原始字段表示第0期即当期）的财报中的对应字段的值
> 例：cfs_cash_received_sales_mrq_7表示当期查询日的最近的前第7期的现金流量表中的销售商品、提供劳务收到的现金的值

| 字段 | 类型 | 描述 |
|---|---|---|
| `cfs_cash_received_sales` | double | 销售商品、提供劳务收到的现金 |
| `cfs_tax_refund` | double | 收到的税费返还 |
| `cfs_net_deposit_inc` | double | 客户存款和同业存放款项净增加额 |
| `cfs_net_inc_cb_borr` | double | 向中央银行借款净增加额 |
| `cfs_net_inc_oth_fi` | double | 向其他金融机构拆入资金净增加额 |
| `cfs_recovery_written_off_loans` | double | 收回已核销贷款 |
| `cfs_cash_received_int_comm` | double | 收取利息、手续费及佣金的现金 |
| `cfs_net_inc_dispose_fa` | double | 处置交易性金融资产净增加额 |
| `cfs_net_inc_repurchase` | double | 回购业务资金净增加额 |
| `cfs_cash_received_orig_ins` | double | 收到原保险合同保费取得的现金 |
| `cfs_cash_received_reins` | double | 收到再保业务现金净额 |
| `cfs_net_inc_ph_invest` | double | 保户储金及投资款净增加额 |
| `cfs_net_inc_borr_capital` | double | 拆入资金净增加额 |
| `cfs_cash_received_proxy_sec` | double | 代理买卖证券收到的现金净额 |
| `cfs_cash_received_uw_sec` | double | 代理承销证券收到的现金净额 |
| `cfs_cash_oth_operating` | double | 收到其它与经营活动有关的现金 |
| `cfs_cash_inflow_operating` | double | 经营活动现金流入小计 |
| `cfs_cash_paid_goods` | double | 购买商品、接受劳务支付的现金 |
| `cfs_asset_depr_reserve` | double | 资产减值准备 |
| `cfs_fx_effect` | double | 汇率变动对现金及现金等价物的影响 |
| `cfs_oth_affecting_cash` | double | 影响现金及现金等价物的其他科目 |
| `cfs_net_inc_cash_equiv` | double | 现金及现金等价物净增加额(主表) |
| `cfs_begin_cash_equiv` | double | 期初现金及现金等价物余额 |
| `cfs_end_cash_equiv` | double | 期末现金及现金等价物余额 |
| `cfs_cash_paid_employees` | double | 支付给职工以及为职工支付的现金 |
| `cfs_cash_paid_taxes` | double | 支付的各项税费 |
| `cfs_net_inc_loans_advances` | double | 客户贷款及垫款净增加额 |
| `cfs_net_inc_depos_cb` | double | 存放中央银行和同业款项净增加额 |
| `cfs_net_inc_lend_capital` | double | 拆出资金净增加额 |
| `cfs_cash_paid_commissions` | double | 支付手续费及佣金的现金 |
| `cfs_cash_paid_orig_ins` | double | 支付原保险合同赔付款项的现金 |
| `cfs_cash_paid_reins` | double | 支付再保业务现金净额 |
| `cfs_cash_paid_policy_div` | double | 支付保单红利的现金 |
| `cfs_net_inc_trad_fa` | double | 为交易目的而持有的金融资产净增加额 |
| `cfs_net_inc_oper_resale` | double | 返售业务资金净增加额(经营) |
| `cfs_cash_paid_oth_operating` | double | 支付其他与经营活动有关的现金 |
| `cfs_cash_outflow_operating` | double | 经营活动现金流出小计 |
| `cfs_net_cash_operating` | double | 经营活动产生的现金流量净额 |
| `cfs_cash_received_dispose_inv` | double | 收回投资收到的现金 |
| `cfs_cash_received_inv_income` | double | 取得投资收益收到的现金 |
| `cfs_cash_received_dispose_asset` | double | 处置固定资产等收回的现金净额 |
| `cfs_cash_oth_investing` | double | 收到其他与投资活动有关的现金 |
| `cfs_cash_inflow_investing` | double | 投资活动现金流入小计 |
| `cfs_cash_paid_asset` | double | 购建固定资产等所支付的现金 |
| `cfs_cash_paid_invest` | double | 投资支付的现金 |
| `cfs_cash_paid_oth_investing` | double | 支付其他与投资活动有关的现金 |
| `cfs_cash_outflow_investing` | double | 投资活动产生的现金流出小计 |
| `cfs_net_cash_investing` | double | 投资活动产生的现金流量净额 |
| `cfs_cash_received_investors` | double | 吸收投资收到的现金 |
| `cfs_cash_received_minority` | double | 子公司吸收少数股东投资收到的现金 |
| `cfs_cash_received_issue_bond` | double | 发行债券收到的现金 |
| `cfs_cash_received_borr` | double | 取得借款收到的现金 |
| `cfs_cash_received_issue_equity` | double | 发行其他权益工具收到的现金 |
| `cfs_net_inc_financing_repurchase` | double | 回购业务资金净增加额(筹资) |
| `cfs_cash_oth_financing` | double | 收到其他与筹资活动有关的现金 |
| `cfs_cash_inflow_financing` | double | 筹资活动现金流入小计 |
| `cfs_cash_paid_debt` | double | 偿还债务支付的现金 |
| `cfs_cash_paid_div_interest` | double | 分配股利、利润或偿付利息支付的现金 |
| `cfs_div_paid_minority` | double | 子公司支付给少数股东的股利等 |
| `cfs_cash_paid_oth_financing` | double | 支付其他与筹资活动有关的现金 |
| `cfs_cash_outflow_financing` | double | 筹资活动现金流出小计 |
| `cfs_net_cash_financing` | double | 筹资活动产生的现金流量净额 |
| `cfs_net_cash_dispose_sub` | double | 处置子公司收到的现金净额 |
| `cfs_net_cash_acquire_sub` | double | 取得子公司支付的现金净额 |
| `cfs_net_inc_pledge_loans` | double | 质押贷款净增加额 |
| `cfs_net_inc_invest_resale` | double | 返售业务资金净增加额(投资) |
| `cfs_net_inc_cash_equiv_note` | double | 现金及现金等价物净增加额(附注) |
| `cfs_fix_asset_depr` | double | 固定资产折旧 |
| `cfs_defer_exp_amort` | double | 长期待摊费用摊销 |
| `cfs_intan_asset_amort` | double | 无形资产摊销 |
