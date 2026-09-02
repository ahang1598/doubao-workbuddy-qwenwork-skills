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

## `get_macro_ci`

用途：中国宏观-景气指数

### 入参

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `symbol` | Optional[Union[string, List[string]]] | 否 | 指标代码，完整指标码表见文件下载 |
| `start_date` | string | 是 | 开始日期 YYYYMMDD |
| `end_date` | string | 是 | 结束日期 YYYYMMDD |
| `fields` | Optional[Union[string, List[string]]] | 否 | 返回字段 |

### 返回字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `symbol` | string | 指标代码 |
| `period_date` | string | 数据期 |
| `data_value` | float | 指标数值 |

## `get_macro_pi`

用途：中国宏观-价格指数

### 入参

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `symbol` | Optional[Union[string, List[string]]] | 否 | 指标代码，完整指标码表见文件下载 |
| `start_date` | string | 是 | 开始日期 YYYYMMDD |
| `end_date` | string | 是 | 结束日期 YYYYMMDD |
| `fields` | Optional[Union[string, List[string]]] | 否 | 返回字段 |

### 返回字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `symbol` | string | 指标代码 |
| `period_date` | string | 数据期 |
| `data_value` | float | 指标数值 |

## `get_macro_pm`

用途：中国宏观-区域宏观

### 入参

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `symbol` | Optional[Union[string, List[string]]] | 否 | 指标代码，完整指标码表见文件下载 |
| `start_date` | string | 是 | 开始日期 YYYYMMDD |
| `end_date` | string | 是 | 结束日期 YYYYMMDD |
| `fields` | Optional[Union[string, List[string]]] | 否 | 返回字段 |

### 返回字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `symbol` | string | 指标代码 |
| `period_date` | string | 数据期 |
| `data_value` | float | 指标数值 |

## `get_macro_fi`

用途：中国宏观-财政

### 入参

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `symbol` | Optional[Union[string, List[string]]] | 否 | 指标代码，完整指标码表见文件下载 |
| `start_date` | string | 是 | 开始日期 YYYYMMDD |
| `end_date` | string | 是 | 结束日期 YYYYMMDD |
| `fields` | Optional[Union[string, List[string]]] | 否 | 返回字段 |

### 返回字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `symbol` | string | 指标代码 |
| `period_date` | string | 数据期 |
| `data_value` | float | 指标数值 |

## `get_macro_mb`

用途：中国宏观-货币与银行

### 入参

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `symbol` | Optional[Union[string, List[string]]] | 否 | 指标代码，完整指标码表见文件下载 |
| `start_date` | string | 是 | 开始日期 YYYYMMDD |
| `end_date` | string | 是 | 结束日期 YYYYMMDD |
| `fields` | Optional[Union[string, List[string]]] | 否 | 返回字段 |

### 返回字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `symbol` | string | 指标代码 |
| `period_date` | string | 数据期 |
| `data_value` | float | 指标数值 |

## `get_macro_ir`

用途：中国宏观-利率汇率

### 入参

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `symbol` | Optional[Union[string, List[string]]] | 否 | 指标代码，完整指标码表见文件下载 |
| `start_date` | string | 是 | 开始日期 YYYYMMDD |
| `end_date` | string | 是 | 结束日期 YYYYMMDD |
| `fields` | Optional[Union[string, List[string]]] | 否 | 返回字段 |

### 返回字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `symbol` | string | 指标代码 |
| `period_date` | string | 数据期 |
| `data_value` | float | 指标数值 |

## `get_index_daily`

用途：获取指数日线

### 入参

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `start_date` | string | 是 | 开始日期,eg:"20250702"，与结束日期间不超过5年 |
| `end_date` | string | 是 | 结束日期,eg:"20250702"，与开始日期间不超过5年 |
| `symbol` | string | 否 | 指数代码 |
| `fields` | string | 否 | 返回字段 |

### 返回字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `symbol` | string | 指数代码 |
| `date` | string | 日期 |
| `open` | float | 开盘价 |
| `close` | float | 收盘价 |
| `high` | float | 最高价 |
| `low` | float | 最低价 |
| `volume` | float | 成交量 |
| `pre_close` | float | 昨日结算价 |
| `amount` | float | 成交额 |

## `get_index_indicator`

用途：获取指数估值指标数据

### 入参

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `symbol` | Optional[Union[string, List[string]]] | 否 | 指数代码 |
| `start_date` | Optional[string] | 否 | 开始日期,eg:"20250702" |
| `end_date` | Optional[string] | 否 | 结束日期,eg:"20250702" |
| `fields` | Optional[Union[string, List[string]]] | 否 | 返回字段列表 |

### 返回字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `date` | string | 日期 |
| `symbol` | string | 指数代码 |
| `pb_lf` | float | 市净率(LF) |
| `pb_lyr` | float | 市净率(LYR) |
| `pb_ttm` | float | 市净率(TTM) |
| `pe_lyr` | float | 市盈率(LYR) |
| `pe_ttm` | float | 市盈率(TTM) |

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

## `get_concept_list`

用途：获取概念列表

### 入参

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `concept` | Optional[Union[string, List[string]]] | 否 | 概念名称 |
| `start_date` | Optional[string] | 否 | 开始时间 |
| `end_date` | Optional[string] | 否 | 结束时间 |

### 返回字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `name` | string | 概念名称 |
| `date` | string | 概念纳入日期 |

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

## `get_option_underlying_volatility`

用途：获取期权标的历史波动率

### 入参

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `start_date` | string | 是 | 开始日期,eg:"20250702"，与结束日期间不超过5年 |
| `end_date` | string | 是 | 结束日期,eg:"20250702"，与开始日期间不超过5年 |
| `symbol` | Optional[Union[string, List[string]]] | 否 | 期权标的代码 |
| `fields` | Optional[Union[string, List[string]]] | 否 | 返回字段 |
| `exchange` | Optional[Union[string, List[string]]] | 否 | 交易市场 |
| `period` | integer | 否 | 历史波动率期限（5/10/30/60/90/120/180/250/500日） |

### 返回字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `date` | string | 日期 |
| `symbol` | string | 期权标的代码 |
| `ticker_symbol` | float | 期权标的简称 |
| `exchange` | string | 交易市场 |
| `is_adj` | integer | 是否为复权数据 |
| `close` | float | 收盘价 |
| `period` | integer | 历史波动率期限（5/10/30/60/90/120/180/250/500日） |
| `historical_volatility` | float | 历史波动率 |

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

## `get_stock_status_change`

用途：获取合约特殊处理数据

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
| `date` | string | 信息发布日期 |
| `change_date` | string | 特别处理（或撤销）实施日期 |
| `description` | string | 特别处理（或撤销）事项描述 |
| `name` | string | 股票名称 |
| `type` | string | 特别处理（或撤销）类别 |

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
