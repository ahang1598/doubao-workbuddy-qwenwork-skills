# PandaData 已登记接口契约

本文件由包内 PandaData 接口文档生成，是本专家已登记业务接口的本地契约。
任务能映射到下列方法时，直接调用 `call_pandadata`；不要先调用 `search_methods` 或
`get_method_doc`。只有接口未登记、方法不受支持或 Connector 明确报告契约失效时，
才进入动态发现或单方法契约修复流程。接口返回 0 行不是动态检索条件。

日期通常使用 `YYYYMMDD`；A 股代码通常使用 `000001.SZ` / `600000.SH`。具体以每个
方法的参数表为准。调用时把方法名与 `params` 对象传给 `call_pandadata`，不要添加
未列出的参数或顶层行数限制。

## `get_last_trade_date`

用途：获取最新交易日

### 入参

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `exchange` | Optional[string] | 否 | 交易所代码，默认为 "SH"，目前支持"SH"，"HK"和"US" |

### 返回字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `date` | string | 最新交易日，格式 "YYYYMMDD"，如果没有则返回None |

## `get_trade_cal`

用途：获取交易日历

### 入参

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `start_date` | Optional[string] | 否 | 开始日期，格式为 YYYYMMDD |
| `end_date` | Optional[string] | 否 | 结束日期，格式为 YYYYMMDD |
| `exchange` | Optional[string] | 否 | 交易所代码，默认为 "SH"，目前支持"SH"，"HK"和"US" |
| `is_trading_day` | Optional[integer] | 否 | 是否为交易日，1=交易日，0=非交易日，None=全部 |
| `fields` | Optional[Union[string, List[string]]] | 否 | 需要返回的字段列表 |

### 返回字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `nature_date` | integer | 日期，格式为YYYYMMDD |
| `exchange` | string | 交易所代码 |
| `is_trade` | integer | 是否为交易日，1表示交易日，0表示非交易日 |
| `pretrade_date` | string | 当前日期前一个交易日 |
| `next_trade_date` | string | 当前日期后一个交易日 |

## `get_trade_list`

用途：获取指定日期的在售股票列表

WorkBuddy 网关实测注意：2026-08-14 WorkBuddy 实测中，`exchange="SH"` 仍返回沪深两市代码。调用时必须传 `date`；若任务只需要单一交易所或板块，应按返回代码后缀和股票基本信息继续过滤，不要把 `exchange` 当作已生效的沪深过滤条件。

### 入参

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `date` | Union[string, List[string]] | 是 | 日期,eg:"20250702" |
| `exchange` | Optional[string] | 否 | 交易所代码，默认为 "SH"，目前支持"SH"，"HK"和"US" |

### 返回字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `symbol` | string | 股票代码 |
| `date` | string | 日期 |

## `get_stock_detail`

用途：获取股票基本信息

### 入参

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `symbol` | Optional[Union[string, List[string]]] | 否 | 股票代码 |
| `fields` | Optional[Union[string, List[string]]] | 否 | 返回字段 |
| `status` | Optional[integer] | 否 | 是否在市，1 -在市，0 -退市，-1 -未知 |

### 返回字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `symbol` | string | 股票代码 |
| `market_tplus` | integer | 交易制度 |
| `name` | string | 股票名称 |
| `special_type` | string | 特别处理状态 |
| `status` | integer | 股票状态 |
| `de_listed_date` | string | 退市日期 |
| `listed_date` | string | 上市日期 |
| `sector_code_name` | string | 以当地语言为标准的板块代码名 |
| `abbrev_symbol` | string | 股票的名称缩写 |
| `sector_code` | string | 板块缩写代码 |
| `min_order_amount` | float | 一手对应多少股 |
| `trading_hours` | string | 产品最新交易时间 |
| `board_type` | string | 板块类别 |
| `issue_price` | float | 该证券发行价 |
| `trading_code` | string | 交易代码 |
| `office_address` | string | 公司地址 |
| `province` | string | 省份 |
| `purchasedate` | string | 申购日期 |

## `get_stock_daily`

用途：获取A股日线数据

### 入参

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `start_date` | string | 是 | 开始日期,eg:"20250702"，与结束日期间不超过5年 |
| `end_date` | string | 是 | 结束日期,eg:"20250702"，与开始日期间不超过5年 |
| `symbol` | Optional[Union[string, List[string]]] | 否 | 股票代码 |
| `fields` | Optional[Union[string, List[string]]] | 否 | 返回字段 |
| `indicator` | Optional[string] | 否 | 股票池，参考本文档数据概述部分中的股票池说明，默认为空表示查询所有 |
| `st` | Optional[bool] | 否 | 是否包含ST股，默认True表示包含。仅在type为stock时有效 |

### 返回字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `date` | string | 日期 |
| `symbol` | string | 股票代码 |
| `name` | string | 股票名称 |
| `open` | float | 当日开盘价 |
| `close` | float | 当日收盘价 |
| `high` | float | 当日最高价 |
| `low` | float | 当日最低价 |
| `volume` | float | 当日成交量 |
| `amount` | float | 当日成交额 |
| `pre_close` | float | 昨收价 |
| `limit_up` | float | 当日涨停价 |
| `limit_down` | float | 当日跌停价 |
| `trade_status` | integer | 当日是否停牌（0表示当日不停牌） |

## `get_stock_daily_post`

用途：获取A股后复权日线数据

### 入参

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `start_date` | string | 是 | 开始日期,eg:"20250702"，与结束日期间不超过5年 |
| `end_date` | string | 是 | 结束日期,eg:"20250702"，与开始日期间不超过5年 |
| `symbol` | Optional[Union[string, List[string]]] | 否 | 股票 |
| `fields` | Optional[Union[string, List[string]]] | 否 | 返回字段 |
| `indicator` | Optional[string] | 否 | 股票池，参考本文档数据概述部分中的股票池说明，默认为空表示查询所有 |
| `st` | Optional[bool] | 否 | 是否包含ST股，默认True表示包含。仅在type为stock时有效 |

### 返回字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `date` | string | 日期 |
| `symbol` | string | 股票代码 |
| `name` | string | 股票名称 |
| `open` | float | 当日开盘价 |
| `close` | float | 当日收盘价 |
| `high` | float | 当日最高价 |
| `low` | float | 当日最低价 |
| `volume` | float | 当日成交量 |
| `pre_close` | float | 昨收价 |
| `limit_up` | float | 当日涨停价 |
| `limit_down` | float | 当日跌停价 |
| `trade_status` | integer | 当日是否停牌（0表示当日不停牌） |

## `get_fina_reports`

用途：获取财务季度报告

### 入参

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `symbol` | Optional[Union[string, list]] | 否 | 股票名称 |
| `start_quarter` | string | 是 | 起始季度，格式为 "YYYYqN" |
| `end_quarter` | string | 是 | 结束季度，格式为 "YYYYqN" |
| `date` | Optional[string] | 否 | 公告日期,返回该日期及之前的数据 |
| `is_latest` | Optional[bool] | 否 | True：返回最新披露数据，False：返回全部。默认为True |
| `fields` | Optional[Union[string, list]] | 否 | 返回字段 |

### 返回字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `symbol` | string | 股票代码 |
| `fields` | float | 财务字段，详见下载文件 |
| `quarter` | string | 季度 |
| `if_adjusted` | integer | 是否为当期财报数据，0为当期，1为非当期 |

## `get_fina_performance`

用途：获取财务快报数据

WorkBuddy 网关实测注意：2026-08-14 WorkBuddy 实测中，网关拒绝了文档列出的 `end_quarter`。常规快报查询优先用 `symbol`、`info_date` 和 `fields`；需要严格季度范围时改用已登记的 `get_fina_reports`，不要循环试参或改搜港美股财务接口。

### 入参

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `symbol` | Optional[Union[string, List[string]]] | 否 | 股票代码，可以是单个字符串或字符串列表 |
| `fields` | Optional[Union[string, List[string]]] | 否 | 需要返回的字段列表 |
| `info_date` | Optional[string] | 否 | 信息发布日期，格式为 "YYYYMMDD" |
| `end_quarter` | Optional[string] | 否 | 报告季度，格式为 "YYYYqN" |

### 返回字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `symbol` | string | 股票代码 |
| `info_date` | string | 信息发布日期 |
| `end_date` | string | 报告日期 |
| `operating_revenue` | float | 营业收入或主营业务收入(元) |
| `gross_profit` | float | 主营业务利润(元) |
| `operating_profit` | float | 营业利润(元) |
| `total_profit` | float | 利润总额(元) |
| `net_profit_parent` | float | 归属母公司净利润(元) |
| `net_profit_excluding_nonrecurring` | float | 扣除非经常性损益后净利润(元) |
| `net_cash_flow_operating` | float | 经营活动现金流量净额(元) |
| `total_assets` | float | 总资产(元) |
| `equity_parent_common` | float | 归属母公司普通股东权益(元) |
| `equity_parent` | float | 归属母公司股东权益(元) |
| `total_shares` | float | 总股本(股) |
| `basic_eps` | float | 基本每股收益 |
| `eps_weighted` | float | 每股收益(加权)(元) |
| `eps_excluding_nonrecurring` | float | 每股收益(扣除)(元) |
| `eps_excluding_nonrecurring_weighted` | float | 每股收益(扣除加权)(元) |
| `roe_diluted` | float | 净资产收益率(摊薄)(%) |
| `roe_weighted` | float | 净资产收益率(加权)(%) |
| `roe_excluding_nonrecurring_diluted` | float | 净资产收益率(扣除摊薄)(%) |
| `roe_excluding_nonrecurring_weighted` | float | 净资产收益率(扣除加权)(%) |
| `cf_operating_per_share` | float | 每股经营活动现金流量净额(元) |
| `bvps` | float | 每股净资产(元) |
| `operating_revenue_yoy` | float | 主营业务收入同比(%) |
| `gross_profit_yoy` | float | 主营业务利润同比(%) |
| `operating_profit_yoy` | float | 营业利润同比(%) |
| `total_profit_yoy` | float | 利润总额同比(%) |
| `net_profit_parent_yoy` | float | 归属母公司净利润同比(%) |
| `net_profit_excluding_nonrecurring_yoy` | float | 扣除非经常性损益后净利润同比(%) |
| `net_cash_flow_operating_yoy` | float | 经营活动现金流量净额同比(%) |
| `total_assets_growth_rate` | float | 总资产较期初比(%) |
| `equity_parent_growth_rate` | float | 归属母公司股东权益较期初比(%) |
| `basic_eps_yoy` | float | 每股收益(摊薄) 同比(%) |
| `eps_weighted_yoy` | float | 每股收益(加权) 同比(%) |
| `eps_excluding_nonrecurring_yoy` | float | 每股收益(扣除) 同比(%) |
| `eps_excluding_nonrecurring_weighted_yoy` | float | 每股收益(扣除加权) 同比(%) |
| `roe_diluted_yoy` | float | 净资产收益率(摊薄) 同比(%) |
| `roe_weighted_yoy` | float | 净资产收益率(加权) 同比(%) |
| `roe_excluding_nonrecurring_diluted_yoy` | float | 净资产收益率(扣除摊薄) 同比(%) |
| `roe_excluding_nonrecurring_weighted_yoy` | float | 净资产收益率(扣除加权) 同比(%) |
| `cf_operating_per_share_yoy` | float | 每股经营活动现金流量净额同比(%) |
| `bvps_growth_rate` | float | 每股净资产较期初比(%) |

## `get_fina_forecast`

用途：获取业绩预告数据

### 入参

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `symbol` | Optional[Union[string, List[string]]] | 否 | 股票代码，可以是单个字符串或字符串列表 |
| `fields` | Optional[Union[string, List[string]]] | 否 | 需要返回的字段列表 |
| `info_date` | Optional[string] | 否 | 信息发布日期，格式为 "YYYYMMDD" |
| `end_quarter` | Optional[string] | 否 | 报告季度，格式为 "YYYYqN" |

### 返回字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `symbol` | string | 股票代码 |
| `info_date` | string | 信息发布日期 |
| `end_date` | string | 报告日期 |
| `forecast_type` | string | 整体业绩预期 |
| `forecast_description` | string | 业绩预期时间段描述 |
| `forecast_growth_rate_floor` | float | 最小预期增长幅度 |
| `forecast_growth_rate_ceiling` | float | 最大预期增长幅度 |
| `forecast_earning_floor` | float | 最小预期收入 |
| `forecast_earning_ceiling` | float | 最大预期收入 |
| `forecast_np_floor` | float | 最小预期净利润 |
| `forecast_np_ceiling` | float | 最大预期净利润 |
| `forecast_eps_floor` | float | 最小预期每股 |
| `forecast_eps_ceiling` | float | 最大预期每股收益 |
| `net_profit_yoy_const_forecast` | float | 一致预期净利润增幅 |
| `forecast_ne_ceiling` | float | 最小预测归母股东权益 |
| `forecast_ne_floor` | float | 最大预测归母股东权益 |

## `get_stock_cash_dividend`

用途：获取股票现金分红数据

### 入参

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `symbol` | Optional[Union[string, List[string]]] | 否 | 股票代码，可以是单个字符串或字符串列表 |
| `market` | Optional[string] | 否 | 市场代码，当前仅支持 "cn"，默认为 "cn" |
| `fields` | Optional[Union[string, List[string]]] | 否 | 需要返回的字段列表 |
| `start_date` | string | 是 | 信息发布日期，格式为 "YYYYMMDD" |
| `end_date` | string | 是 | 信息发布日期，格式为 "YYYYMMDD" |

### 返回字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `symbol` | string | 股票代码 |
| `announcement_date` | string | 分红预案公告日期 |
| `div_cash_gross` | float | 税前每股现金分红 |
| `record_date` | string | 股权登记日 |
| `ex_date` | string | 除权除息日 |
| `payment_date` | string | 派息日 |
| `round_lot` | float | 分红基准单位 |
| `meeting_date` | string | 股东大会日期 |
| `quarter` | string | 对应财报期 |

## `get_stock_dividend_amount`

用途：获取股票分红总额数据

### 入参

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `symbol` | Optional[Union[string, List[string]]] | 否 | 股票代码，可以是单个字符串或字符串列表 |
| `market` | Optional[string] | 否 | 市场代码，当前仅支持 "cn"，默认为 "cn" |
| `fields` | Optional[Union[string, List[string]]] | 否 | 需要返回的字段列表 |
| `start_date` | string | 是 | 信息发布日期，格式为 "YYYYMMDD" |
| `end_date` | string | 是 | 信息发布日期，格式为 "YYYYMMDD" |

### 返回字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `symbol` | string | 股票代码 |
| `announcement_date` | string | 公告日期 |
| `event_stage` | string | 事项阶段（如董事会预案等） |
| `total_div_amount` | float | 分红总额 |
| `quarter` | string | 对应财报期 |

## `get_holder_count`

用途：获取股东数量

### 入参

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `symbol` | Optional[Union[string, List[string]]] | 否 | 股票代码 |
| `start_date` | Optional[string] | 否 | 开始日期,eg:"20250702" |
| `end_date` | Optional[string] | 否 | 结束日期,eg:"20250702" |
| `fields` | Optional[Union[string, List[string]]] | 否 | 返回字段列表 |

### 返回字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `symbol` | string | 股票代码 |
| `date` | string | 公告日期 |
| `end_date` | string | 截止日期 |
| `a_holders` | string | A股股东户数 |
| `avg_a_holders` | string | A股股东户均持股数 |
| `avg_circulation_holders` | float | 无限售A股股东户均持股数 |
| `avg_holders` | float | 户均持股数 |
| `holders` | string | 股东户数 |

## `get_stock_pledge_stat`

用途：获取股票质押信息统计

### 入参

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `start_date` | string | 是 | 开始日期,eg:"20250702" |
| `end_date` | string | 是 | 结束日期,eg:"20250702" |
| `fields` | Optional[Union[string, List[string]]] | 否 | 返回字段列表 |

### 返回字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `data_source` | string | 数据来源 |
| `pledge_begin_date` | string | 起始日期 |
| `pledge_end_date` | string | 结束日期 |
| `unrestricted_avg_pledge_ratio` | float | 无限售条件股份平均质押率 |
| `restricted_avg_pledge_ratio` | float | 有限售条件股份平均质押率 |
| `pledge_number` | float | 质押笔数 |
| `pledge_volume` | float | 质押数量 |
| `init_amount` | float | 初始交易金额 |
| `repurchase_amount` | float | 购回交易金额 |

## `get_stock_shareholder_change`

用途：获取股东增减持计划

### 入参

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `symbol` | Optional[Union[string, List[string]]] | 否 | 股票代码 |
| `start_date` | string | 是 | 开始日期,eg:"20250702" |
| `end_date` | string | 是 | 结束日期,eg:"20250702" |
| `fields` | Optional[Union[string, List[string]]] | 否 | 返回字段列表 |

### 返回字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `symbol` | string | 股票代码 |
| `name` | string | 股票名 |
| `info_date` | string | 公告日期 |
| `first_info_date` | string | 首次公告日期 |
| `progress` | string | 进度 |
| `begin_date` | string | 增减持计划起始日期 |
| `end_date` | string | 增减持计划截止日期 |
| `shareholder_name` | string | 股东名称 |
| `shareholder_type` | string | 股东类型 |
| `direction` | string | 变动方向 |
| `before_hold` | float | 变动前持股数 |
| `change_up_limit` | float | 变动数量上限 |
| `ratio_up_limit` | float | 占总股本比例上限 |
| `reason` | string | 变动原因 |
| `value_up_limit` | float | 预计金额上限 |
| `value_down_limit` | float | 预计金额下限 |
| `ratio_down_limit` | float | 占总股本比例下限 |
| `change_down_limit` | float | 变动数量下限 |
| `price_down_limit` | float | 价格下限 |
| `price_up_limit` | float | 价格上限 |
| `trigger_condition` | string | 触发条件说明 |
| `trigger_price` | float | 触发价格 |
| `trigger_days` | float | 连续天数 |

## `get_top_holders`

用途：获取A股股东信息

### 入参

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `symbol` | Optional[Union[string, List[string]]] | 否 | 股票代码 |
| `start_date` | string | 是 | 开始日期,eg:"20250702" |
| `end_date` | string | 是 | 结束日期,eg:"20250702" |
| `fields` | Optional[Union[string, List[string]]] | 否 | 返回字段列表 |
| `market` | Optional[string] | 否 | 市场,默认"cn"为中国内地市场 |
| `start_rank` | Optional[integer] | 否 | 排名开始值 |
| `end_rank` | Optional[integer] | 否 | 排名结束值 |
| `stock_type` | Optional[string] | 否 | 股票种类, flow基于持有A股流通股;total基于所有发行出的A股 |

### 返回字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `date` | string | 信息发布日期 |
| `stock_type` | string | 股票类型 |
| `rank` | integer | 排名 |
| `symbol` | string | 股票代码 |
| `end_date` | string | 截止日期 |
| `freeze` | float | 股权冻结涉及股数（股） |
| `hold_percent_float` | float | 占流通A股比例（%） |
| `hold_percent_total` | float | 占股比例(%) |
| `holder_attr` | string | 股东属性 |
| `holder_kind` | string | 股东性质 |
| `holder_name` | string | 股东名称 |
| `holder_type` | float | 股东类别 |
| `pledge` | float | 股权质押涉及股数 |

## `get_hsgt_hold`

用途：获取沪深股通持股信息

### 入参

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `symbol` | Optional[Union[string, List[string]]] | 否 | 股票代码 |
| `start_date` | string | 是 | 开始日期,eg:"20250702" |
| `end_date` | string | 是 | 结束日期,eg:"20250702" |
| `fields` | Optional[Union[string, List[string]]] | 否 | 返回字段列表 |

### 返回字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `date` | string | 日期 |
| `shares_num` | float | 持股数量 |
| `symbol` | string | 股票代码 |
| `adjusted_holding_ratio` | float | 调整后持股比例 |
| `holding_ratio` | float | 持股比例 |

## `get_margin`

用途：获取融资融券信息

### 入参

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `symbol` | Optional[Union[string, List[string]]] | 否 | 股票代码 |
| `start_date` | string | 是 | 开始日期,eg:"20250702" |
| `end_date` | string | 是 | 结束日期,eg:"20250702" |
| `fields` | Optional[Union[string, List[string]]] | 否 | 返回字段列表 |
| `margin_type` | Optional[string] | 否 | 买卖方向，"stock" 代表融券卖出，"cash" 代表融资买入 |

### 返回字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `short_sell_quantity` | float | 融券卖出量 |
| `buy_on_margin_value` | float | 融资买入额 |
| `date` | string | 日期 |
| `margin_repayment` | float | 融券偿还额 |
| `short_balance` | float | 融券余额 |
| `margin_balance` | float | 融资余额 |
| `symbol` | string | 股票代码 |
| `short_balance_quantity` | float | 融券余量 |
| `short_repayment_quantity` | float | 融券偿还量 |
| `margin_type` | string | 买卖方向，"stock" 代表融券卖出，"cash" 代表融资买入 |
| `total_balance` | float | 总余额 |

## `get_lhb_list`

用途：获取股票龙虎榜数据

### 入参

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `symbol` | Optional[Union[string, List[string]]] | 否 | 股票代码，如 "000001.SZ" |
| `type` | Optional[Union[string, List[string]]] | 否 | 龙虎榜类型 |
| `start_date` | Optional[string] | 否 | 开始日期，格式 "YYYYMMDD" |
| `end_date` | Optional[string] | 否 | 结束日期，格式 "YYYYMMDD" |
| `fields` | Optional[Union[string, List[string]]] | 否 | 需要返回的字段列表 |

### 返回字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `symbol` | string | 股票代码 |
| `date` | string | 龙虎榜日期 |
| `type` | string | 龙虎榜类型 |
| `reason` | string | 龙虎榜原因 |
| `amount` | float | 龙虎榜金额 |
| `volume` | float | 龙虎榜数量 |
| `amplitude` | float | 龙虎榜振幅 |
| `change_rate` | float | 龙虎榜涨跌幅 |
| `deviation` | float | 龙虎榜涨跌幅偏离值 |
| `turnover` | float | 龙虎榜换手率 |
| `start_date` | float | 异动开始日期 |
| `end_date` | string | 异动结束日期 |

## `get_restricted_list`

用途：获取股票限售解禁明细数据

### 入参

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `symbol` | Optional[Union[string, List[string]]] | 否 | 股票代码 |
| `start_date` | string | 是 | 开始日期,eg:"20250702" |
| `end_date` | string | 是 | 结束日期,eg:"20250702" |
| `fields` | Optional[Union[string, List[string]]] | 否 | 返回字段列表 |
| `market` | Optional[string] | 否 | 市场,默认"cn"为中国内地市场 |

### 返回字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `symbol` | string | 合约代码 |
| `date` | string | 限售解禁信息发布日期 |
| `relieve_date` | string | 解禁日期 |
| `shareholder` | string | 股东名 |
| `shareholder_type` | string | 股东类型 |
| `relieve_shares` | float | 解除限售股份数量(股) |
| `actual_relieve_shares` | float | 实际上市流通数量(股) |
| `relieve_reason` | string | 解禁原因 |

## `get_industry_constituents`

用途：获取行业成分股数据

### 入参

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `industry_code` | Optional[Union[string, List[string]]] | 否 | 行业代码，如"801010" |
| `stock_symbol` | Optional[Union[string, List[string]]] | 否 | 股票代码，如"000001.SZ" |
| `level` | Optional[string] | 否 | 行业级别，可选值："L1"(一级)、"L2"(二级)、"L3"(三级) |
| `fields` | Optional[Union[string, List[string]]] | 否 | 返回字段列表 |

### 返回字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `stock_symbol` | string | 股票代码 |
| `l1_code` | string | 一级行业代码 |
| `l2_code` | string | 二级行业代码 |
| `l3_code` | string | 三级行业代码 |
| `in_date` | string | 纳入时间 |
| `l1_name` | string | 一级行业名称 |
| `l2_name` | string | 二级行业名称 |
| `l3_name` | string | 三级行业名称 |
| `out_date` | string | 剔除时间 |
| `stock_name` | string | 股票名称 |

## `get_concept_constituents`

用途：获取概念成分股

### 入参

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `concept` | Optional[Union[string, List[string]]] | 否 | 概念名称 |
| `concept_stock` | Optional[Union[string, List[string]]] | 否 | 股票代码 |
| `start_date` | Optional[string] | 否 | 开始日期，格式 YYYYMMDD |
| `end_date` | Optional[string] | 否 | 结束日期，格式 YYYYMMDD |
| `date` | Optional[string] | 否 | 日期，返回该日期前被纳入对应概念的股票 |
| `fields` | Optional[Union[string, List[string]]] | 否 | 返回字段 |

### 返回字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `concept` | string | 概念名称 |
| `concept_stock` | string | 概念成分股 |
| `date` | string | 股票纳入概念日期 |

## `get_index_weights`

用途：获取指数权重信息数据

### 入参

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `index_symbol` | Optional[Union[string, List[string]]] | 否 | 指数代码 |
| `stock_symbol` | Optional[Union[string, List[string]]] | 否 | 成分股代码 |
| `start_date` | string | 是 | 开始日期,eg:"20250702" |
| `end_date` | string | 是 | 结束日期,eg:"20250702" |
| `fields` | Optional[Union[string, List[string]]] | 否 | 返回字段列表 |

### 返回字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `index_symbol` | string | 指数代码 |
| `date` | string | 日期 |
| `stock_symbol` | string | 股票代码 |
| `weight` | float | 权重 |
