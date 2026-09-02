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

## `get_lhb_detail`

用途：获取股票龙虎榜明细数据

### 入参

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `symbol` | Optional[Union[string, List[string]]] = None | 否 | 股票代码，如 "000001.SZ" |
| `type` | Optional[Union[string, List[string]]] | 否 | 龙虎榜类型 |
| `start_date` | string | 是 | 开始日期，格式 "YYYYMMDD" |
| `end_date` | string | 是 | 结束日期，格式 "YYYYMMDD" |
| `side` | Optional[string] | 否 | 买卖方向，可选值为 "buy" 或 "sell" 或 "cum"，其中"cum"类型记录发生严重异常时的累计数据，与具体买卖方向无关 |
| `fields` | Optional[Union[string, List[string]]] | 否 | 需要返回的字段列表 |

### 返回字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `symbol` | string | 股票代码 |
| `date` | string | 龙虎榜日期 |
| `type` | string | 龙虎榜类型(同前) |
| `side` | string | 买卖方向 |
| `rank` | integer | 龙虎榜排名 |
| `agency` | string | 营业部名称 |
| `b_value` | float | 买入金额 |
| `s_value` | float | 卖出金额 |
| `reason` | string | 龙虎榜原因 |

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

## `get_block_trade`

用途：获取A股大宗交易信息

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
| `date` | string | 交易日期 |
| `price` | float | 成交价 |
| `volume` | float | 成交量 |
| `amount` | float | 成交额 |
| `buyer` | string | 买方营业部 |
| `seller` | string | 卖方营业部 |
| `sequence_id` | integer | 序列号 |

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

## `get_stock_industry`

用途：获取指定股票所属的行业信息

### 入参

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `stock_symbol` | string | 是 | 股票代码，如"000001.SZ" |
| `level` | Optional[string] | 否 | 行业级别，可选值："L1"(一级)、"L2"(二级)、"L3"(三级) |

### 返回字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `stock_symbol` | string | 股票代码 |
| `industry_code` | string | 行业代码 |
| `industry_name` | string | 行业名称 |
| `parent_code` | string | 上级行业代码 |
| `parent_name` | string | 上级行业名称 |
| `parent_l1_code` | string | 一级行业名称 |
| `parent_l1_name` | string | 一级行业名称 |
| `parent_l2_code` | string | 二级行业名称 |
| `parent_l2_name` | string | 二级行业名称 |

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
