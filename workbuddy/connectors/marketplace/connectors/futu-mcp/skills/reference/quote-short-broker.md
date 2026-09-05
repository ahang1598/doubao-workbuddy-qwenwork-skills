# 卖空/经纪商/股票基本信息
## quote_short_interest — 空头持仓

获取股票的做空未平仓数据。港股返回空头仓位详情；美股返回月度空头报告。数据按时间倒序排列。

**支持市场：** 仅 HK/US 普通股及 ETF。其他市场/品类返回 unsupported。

**参数：**
| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| symbol | string | 是 | — | 股票代码，如 `HK.00700`、`US.AAPL` |
| count | int | 否 | 30 | 记录数，范围 1~90 |

**返回 `data.items[]`（港股）：**

| 字段 | 类型 | 说明 |
|------|------|------|
| timestamp | int64 | 数据时间戳（**毫秒**） |
| timestamp_str | string | 数据日期（yyyy-MM-dd） |
| aggregated_short | string | 空头未平仓股数（int64 序列化为字符串） |
| aggregated_short_ratio | float | 占流通股比例（%） |
| close_price | float | 当日收盘价 |
| last_close_price | float | 前一交易日收盘价 |
| avg_cost | float | 空头平均持仓成本 |
| avg_daily_short_volume | string | 日均做空成交量 |

**返回 `data.items[]`（美股）：**

| 字段 | 类型 | 说明 |
|------|------|------|
| timestamp | int64 | 数据时间戳（**毫秒**） |
| timestamp_str | string | 数据日期（yyyy-MM-dd） |
| shares_short | string | 做空未平仓股数（int64 序列化为字符串） |
| short_percent | float | 做空比例（%） |
| avg_daily_share_volume | string | 日均成交量 |
| days_to_cover | float | 回补天数 |
| close_price | float | 收盘价 |
| last_close_price | float | 前一交易日收盘价 |
| avg_daily_short_volume | string | 日均做空成交量 |

**港股 vs 美股字段差异：**
| 差异 | 港股 | 美股 |
|------|------|------|
| 空头股数 | `aggregated_short` | `shares_short` |
| 比例 | `aggregated_short_ratio` | `short_percent` |
| 平均成本 | `avg_cost`（有） | 无 |
| 回补天数 | 无 | `days_to_cover`（有） |
| 日均成交量 | 无 | `avg_daily_share_volume`（有） |
| 公共字段 | `timestamp`, `timestamp_str`, `close_price`, `last_close_price`, `avg_daily_short_volume` | 同左 |

**错误码：**
| ret_code | 触发条件 | 处理建议 |
|----------|----------|----------|
| -3 | count 超范围或 symbol 格式无效 | 修正参数重试 |
| -7 | symbol 格式合法但证券不存在 | 确认代码 |
| -8 | 市场或品类不在支持范围 | 仅对 HK/US 普通股和 ETF 调用 |
| -10 | 证券有效但无空头数据 | 正常空结果 |
| -5 | 网关/后端内部错误 | 可重试 |

---

## quote_daily_short_volume — 日度做空成交

获取每日做空成交数据（港股为成交维度，美股为持仓维度）。数据按时间倒序排列。

**支持市场：** 仅 HK/US 可卖空证券（普通股、ETF、REIT 等）。期权、期货、窝轮、指数不支持。

**参数：**
| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| symbol | string | 是 | — | 股票代码，如 `HK.00700`、`US.AAPL` |
| count | int | 否 | 30 | 记录数，范围 1~90 |

**返回 `data` 顶层字段（港股）：**

| 字段 | 类型 | 说明 |
|------|------|------|
| market | string | 市场标识，固定为 `HK` |
| aggregated_short | int | 累计空头持仓股数 |
| aggregated_short_ratio | float | 累计空头占流通股比例（%） |
| new_time | string | 数据更新时间（dd/MM/yyyy） |

**返回 `data.items[]`（港股）：**

| 字段 | 类型 | 说明 |
|------|------|------|
| timestamp | int64 | 数据时间戳（**毫秒**） |
| timestamp_str | string | 数据日期（yyyy-MM-dd） |
| shares_traded | int | 当日总成交股数 |
| turnover | float | 当日总成交额（HKD） |
| short_sell_shares_traded | int | 当日做空成交股数 |
| short_sell_turnover | float | 当日做空成交额（HKD） |
| open_price | float | 开盘价 |
| close_price | float | 收盘价 |
| last_close_price | float | 前一交易日收盘价 |
| daily_trade_avg_ratio | float | 日均成交比率（%） |

**返回 `data.items[]`（美股）：**

| 字段 | 类型 | 说明 |
|------|------|------|
| timestamp | int64 | 数据时间戳（**毫秒**） |
| timestamp_str | string | 数据日期（yyyy-MM-dd） |
| total_shares_short | int | 当日做空总股数 |
| nasdaq_shares_short | int | NASDAQ 做空股数 |
| nyse_shares_short | int | NYSE 做空股数 |
| short_percent | float | 做空成交占比（%） |
| volume | int | 当日总成交量 |
| close_price | float | 收盘价 |
| last_close_price | float | 前一交易日收盘价 |
| daily_trade_avg_ratio | float | 日均成交比率（%） |

**港股 vs 美股字段差异：**
| 差异 | 港股 | 美股 |
|------|------|------|
| 数据维度 | 成交维度 | 持仓维度 |
| data 顶层额外字段 | `aggregated_short`, `aggregated_short_ratio`, `new_time` | 无 |
| 做空量字段 | `short_sell_shares_traded`, `short_sell_turnover` | `total_shares_short`, `nasdaq_shares_short`, `nyse_shares_short`, `short_percent` |
| 成交额 | `turnover`（HKD） | 无（用 `volume` 代替） |
| 开盘价 | `open_price`（有） | 无 |
| 公共字段 | `timestamp`, `timestamp_str`, `close_price`, `last_close_price`, `daily_trade_avg_ratio` | 同左 |

**错误码：**
| ret_code | 触发条件 | 处理建议 |
|----------|----------|----------|
| -3 | count 超范围或 symbol 格式无效 | 修正参数重试 |
| -7 | symbol 无法解析 | 确认代码 |
| -8 | 市场或品类不支持 | 仅对 HK/US 可卖空证券调用 |
| -10 | 证券有效但无做空成交数据 | 正常空结果 |

---

## quote_top_ten_brokers — 十大经纪商（实时）

获取当日十大净买入/净卖出经纪商（仅港股），含经纪商 ID、净量及均价。实时数据仅在港股交易时段返回。

**支持市场：** 仅港股普通股、ETF、REIT。

**参数：**
| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| symbol | string | 是 | — | 港股代码，如 `HK.00700` |
| date | string | 否 | 最新交易日 | 交易日，格式 YYYY-MM-DD |

**返回 `data`：**

| 字段 | 类型 | 说明 |
|------|------|------|
| is_real_time | bool | `true`=实时数据，`false`=历史数据 |
| data_time | int64 | 数据更新时间戳（**毫秒**） |
| data_time_str | string | 数据更新时间（可读字符串） |
| sec_volume | int | 当日总成交量（股） |
| sec_turnover | float | 当日总成交额 |
| buy_brokers[] | array | 净买入经纪商列表（最多 10） |
| sell_brokers[] | array | 净卖出经纪商列表（最多 10） |

**buy_brokers[] / sell_brokers[] 元素（实时）：**

| 字段 | 类型 | 说明 |
|------|------|------|
| broker_id | int | 经纪商 ID |
| net_vol | int | 净量（buy 为正，sell 为负） |
| avg_price | float | 平均成交价 |

---

## quote_top_ten_brokers_history — 十大经纪商（历史）

获取指定历史交易日的十大净买入/净卖出经纪商持仓。

**支持市场：** 仅港股普通股、ETF、REIT。

**参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| symbol | string | 是 | 港股代码，如 `HK.00700` |
| days_before | int | 是 | 距当前交易日的天数，必须 >0，范围 1~365 |

**返回 `data`：**

| 字段 | 类型 | 说明 |
|------|------|------|
| is_real_time | bool | 固定为 `false` |
| data_time | int64 | 数据时间戳（**毫秒**） |
| data_time_str | string | 数据时间（可读字符串） |
| buy_brokers[] | array | 净买入经纪商列表（最多 10） |
| sell_brokers[] | array | 净卖出经纪商列表（最多 10） |

**buy_brokers[] / sell_brokers[] 元素（历史）：**

| 字段 | 类型 | 说明 |
|------|------|------|
| broker_name | string | 经纪商名称 |
| broker_code | string | 经纪商代码 |
| net_vol | int | 净量（buy 为正，sell 为负） |
| hold_ratio | float | 持仓占比（%） |

**实时 vs 历史字段差异：**
| 字段 | 实时 | 历史 |
|------|------|------|
| broker_id | 有 | 无 |
| broker_name | 无 | 有 |
| broker_code | 无 | 有 |
| avg_price | 有 | 无 |
| hold_ratio | 无 | 有 |
| sec_volume / sec_turnover | 有 | 无 |
| net_vol | 有（公共） | 有（公共） |

**错误码（两接口通用）：**
| ret_code | 触发条件 | 处理建议 |
|----------|----------|----------|
| -3 | symbol 格式无效或 days_before 超范围 | 修正参数重试 |
| -7 | symbol 无法解析 | 通过搜索接口确认代码 |
| -8 | 非港股市场 | 仅传入 HK 代码 |
| -2/-4/-6 | 网关内部错误 | 可重试 |

---

## quote_stock_basicinfo — 股票基本信息

批量获取股票/ETF/指数/窝轮/期权/期货/债券/外汇/基金等的静态参考信息。仅返回静态属性和停牌标志，不含行情/K 线/基本面。

**支持市场前缀：** HK、US、SH、SZ、SG、JP、AU、CA、MY、FX、CC、BMD、SGX、HKEX 等已注册市场。

**参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| code_list | string[] | 是 | 代码列表，1~400 个，如 `["HK.00700", "US.AAPL"]` |

**返回 `data.basic_list[]`：**

| 字段 | 类型 | 说明 |
|------|------|------|
| code | string | 股票代码，如 `HK.00700` |
| name | string | 英文名 |
| sc_name | string | 简体中文名 |
| tc_name | string | 繁体中文名 |
| stock_id | int64 | 内部数字标识 |
| lot_size | int | 每手股数（期权=合约股数；期货=合约乘数） |
| stock_type | string | 证券类型：`STOCK` / `DRVT`（衍生品/期权/窝轮） / `FUTURE` / 等 |
| listing_date | int64 | 上市时间戳（**毫秒**）；期货/期权/指数无上市日时为 0 |
| suspension | bool | 是否停牌（仅停牌标志；完整生命周期见 `state`） |
| state | string | 证券生命周期状态：`NORMAL` / 等 |
| contract_size | int\|null | 期权合约股数（对应标的每张合约股数）；非期权为 null |
| main_contract | bool | 是否主力连续合约（期货） |
| stock_child_type | string | 窝轮子类型：`N/A`=不适用 / 等 |
| stock_owner | string | 标的正股代码（窝轮/期权），如 `HK.00700`；非衍生品不返回此字段 |

**特殊行为：**
- 部分代码无法解析时，有效代码正常返回，无效代码静默跳过（ret_code 仍为 0）
- 全部代码无法解析时返回 ret_code=-7

**错误码：**
| ret_code | 触发条件 | 处理建议 |
|----------|----------|----------|
| 0 | 成功（含部分代码无效被跳过） | 对比请求与返回的 code 列表以识别无效项 |
| -3 | code_list 缺失、为空或超过 400 | 修正请求体重试 |
| -7 | 全部代码均无法解析 | 通过搜索接口确认代码有效性 |
| -2 | 后端异常 | 可重试 |
