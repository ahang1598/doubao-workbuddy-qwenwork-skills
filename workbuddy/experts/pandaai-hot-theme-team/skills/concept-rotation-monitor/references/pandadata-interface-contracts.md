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
