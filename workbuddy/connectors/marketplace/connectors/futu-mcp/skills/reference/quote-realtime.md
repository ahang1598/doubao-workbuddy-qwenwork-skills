# 实时行情工具参考

## quote_stock_quote — 实时报价

批量获取股票实时报价，需订阅。

**参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| code_list | string[] | 是 | 股票代码列表，如 `["HK.00700","US.AAPL"]`，最多 400 只 |

**返回 `data.quote_list[]`：**

| 字段 | 类型 | 说明 |
|------|------|------|
| code | string | 标的代码 |
| name | string | 英文名 |
| sc_name | string | 简体中文名 |
| tc_name | string | 繁体中文名 |
| data_time | int64 | 行情交易所时间（毫秒时间戳） |
| data_date | string | 行情交易日（市场时区 YYYY-MM-DD） |
| last_price | double | 最新价 |
| open_price | double | 今开 |
| high_price | double | 今高 |
| low_price | double | 今低 |
| prev_close_price | double | 昨收 |
| volume | int64 | 成交量（股/张） |
| turnover | double | 成交额 |
| turnover_rate | double | 换手率（百分比，0.353 表示 0.353%） |
| amplitude | double | 振幅（百分比） |
| sec_status | string | 证券状态 |
| suspension | bool | 是否停牌 |
| dark_status | string | 暗盘状态 |
| listing_date | string | 上市日期（YYYY-MM-DD） |

**option_ex_data 子对象（仅期权）：**

| 字段 | 类型 | 说明 |
|------|------|------|
| strike_price | double | 行权价 |
| contract_size | int64 | 合约规模 |
| open_interest | int64 | 未平仓量 |
| implied_volatility | double | 隐含波动率（百分比） |
| premium | double | 期权金 |
| delta | double | Δ |
| gamma | double | Γ |
| vega | double | ν |
| theta | double | Θ |
| rho | double | ρ |
| net_open_interest | int64 | 净未平仓 |
| contract_nominal_value | double | 合约名义价值 |
| owner_lot_multiplier | int64 | 正股每手乘数 |
| contract_multiplier | int64 | 合约乘数 |
| option_type | string | 期权方向 |
| index_option_type | int32 | 指数期权类型 |
| expiry_date_distance | int64 | 距到期日天数（负数=已过期） |
| option_area_type | string | 行权类型 |

**future_ex_data 子对象（仅期货）：**

| 字段 | 类型 | 说明 |
|------|------|------|
| last_settle_price | double | 上一结算价 |
| position | int64 | 持仓 |
| position_change | int64 | 持仓变化 |

**pre_market / after_market / overnight 子对象：**

| 字段 | 类型 | 说明 |
|------|------|------|
| price | double | 时段价 |
| high_price | double | 时段高 |
| low_price | double | 时段低 |
| volume | int64 | 时段成交量 |
| turnover | double | 时段成交额 |
| change_val | double | 涨跌额 |
| change_rate | double | 涨跌幅（百分比） |
| amplitude | double | 振幅（百分比） |

---

## quote_market_snapshot — 市场快照

字段最全的报价接口，含 52 周高低、市值、PE、PB、股息率、窝轮/信托/期权/期货/盘前盘后/夜盘字段。返回 `data.snapshot_list[]`。

**支持市场：** HK（正股/信托/REIT/窝轮/牛熊/界内证/指数/板块/ETF/期权）、US（正股/ETF/指数）、SH/SZ（正股/ETF/指数/板块）、BJ（正股/指数）

**参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| code_list | string[] | 是 | 股票代码列表，1~400 个，如 `["HK.00700", "US.AAPL"]` |

**返回 `data.snapshot_list[]` — 通用字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| code | string | 标的代码 |
| name / sc_name / tc_name | string | 英文/简中/繁中名 |
| update_time | int64 | 行情更新时间（**毫秒**时间戳） |
| data_date | string | 行情交易日（市场时区 YYYY-MM-DD） |
| last_price | double | 最新价 |
| open_price | double | 今开 |
| high_price | double | 今高 |
| low_price | double | 今低 |
| prev_close_price | double | 昨收 |
| close_price_5min | double | 最近 5 分钟收盘价 |
| volume | int64 | 成交量 |
| turnover | double | 成交额 |
| turnover_rate | double | 换手率（%） |
| amplitude | double | 振幅（%） |
| volume_ratio | double | 量比 |
| bid_ask_ratio | double | 委比（%，正=买盘强，负=卖盘强） |
| sec_status | string | 证券状态 |
| dark_status | string | 暗盘状态 |
| listing_date | int64 | 上市日期（**毫秒**时间戳）；无上市日为 0 |
| bid_price / ask_price | double | 买一/卖一价 |
| bid_vol / ask_vol | int64 | 买一/卖一量 |
| price_spread | double | 价差 |
| highest52weeks_price | double | 52 周最高（未复权） |
| lowest52weeks_price | double | 52 周最低（未复权） |
| highest_history_price | double | 历史最高（未复权） |
| lowest_history_price | double | 历史最低（未复权） |
| suspension | bool | 是否停牌 |
| avg_price | double | 均价 |
| lot_size | int64 | 每手股数 |

**品类标志字段（用于判断下方分类字段是否有意义）：**

| 字段 | 类型 | 说明 |
|------|------|------|
| equity_valid | bool | 是否正股 |
| index_valid | bool | 是否指数 |
| plate_valid | bool | 是否板块 |
| wrt_valid | bool | 是否窝轮/牛熊/界内证 |
| trust_valid | bool | 是否信托/基金/REIT |
| option_valid | bool | 是否期权 |
| future_valid | bool | 是否期货 |

**正股字段（equity_valid=true）：**

| 字段 | 类型 | 说明 |
|------|------|------|
| issued_shares | int64 | 总股本 |
| total_market_val | double | 总市值 |
| outstanding_shares | int64 | 流通股本 |
| circular_market_val | double | 流通市值 |
| pe_ratio | double | 静态 PE |
| pe_ttm_ratio | double | PE_TTM |
| pb_ratio | double | PB |
| dividend_ttm | double | TTM 每股股息 |
| dividend_ratio_ttm | double | TTM 股息率（%） |
| dividend_lfy | double | 上一财年每股股息 |
| dividend_lfy_ratio | double | 上一财年股息率（%） |
| net_asset | double | 净资产 |
| net_asset_per_share | double | 每股净资产 |
| net_profit | double | 净利润 |
| ey_ratio | double | 收益率 EY（%） |
| earning_per_share | double | EPS |

**指数字段（index_valid=true）：**

| 字段 | 类型 | 说明 |
|------|------|------|
| index_raise_count | int64 | 上涨家数 |
| index_fall_count | int64 | 下跌家数 |
| index_equal_count | int64 | 平盘家数 |

**窝轮/牛熊证字段（wrt_valid=true）：**

| 字段 | 类型 | 说明 |
|------|------|------|
| wrt_maturity_date | int64 | 到期日（**秒**级时间戳） |
| wrt_end_trade | int64 | 最后交易日（**秒**级时间戳） |

**信托/基金/REIT 字段（trust_valid=true）：**

| 字段 | 类型 | 说明 |
|------|------|------|
| trust_aum | double | AUM |
| trust_dividend_yield | double | 股息率（%） |
| trust_outstanding_units | int64 | 流通单位数 |
| trust_netAssetValue | double | 单位净值 NAV |
| trust_premium | double | 溢价（%） |
| trust_assetClass | string | 资产类别：`STOCK`/`BOND`/`COMMODITY`/`CURRENCY_MARKET`/`FUTURE`/`SWAP` |

**期权字段（option_valid=true）：**

| 字段 | 类型 | 说明 |
|------|------|------|
| option_strike_price | double | 行权价 |
| option_contract_size | int64 | 合约规模 |
| option_open_interest | int64 | 未平仓合约数 |
| option_implied_volatility | double | 隐含波动率（%） |
| delta | double | Delta |
| gamma | double | Gamma |
| vega | double | Vega |
| theta | double | Theta |
| rho | double | Rho |
| option_net_open_interest | int64 | 净未平仓 |
| option_contract_nominal_value | double | 合约名义价值 |
| option_owner_lot_multiplier | double | 标的每手乘数 |
| option_type | string | 期权方向：`CALL`/`PUT` |
| option_contract_multiplier | int64 | 合约乘数 |
| index_option_type | int32 | 指数期权类型 |
| option_expiry_date_distance | int64 | 距到期天数（负数=已到期） |
| option_area_type | string | 行权类型：`AMERICAN`/`EUROPEAN`/`BERMUDA` |

**期货字段（future_valid=true）：**

| 字段 | 类型 | 说明 |
|------|------|------|
| future_last_settle_price | double | 前结算价 |
| future_position | int64 | 持仓量 |
| future_position_change | int64 | 持仓变动 |

**盘前字段（非盘前时段为 0）：**

| 字段 | 类型 | 说明 |
|------|------|------|
| pre_price | double | 盘前价 |
| pre_high_price | double | 盘前最高 |
| pre_low_price | double | 盘前最低 |
| pre_volume | int64 | 盘前成交量 |
| pre_turnover | double | 盘前成交额 |
| pre_change_val | double | 盘前涨跌额 |
| pre_change_rate | double | 盘前涨跌幅（%） |
| pre_amplitude | double | 盘前振幅（%） |

**盘后字段（非盘后时段为 0）：**

| 字段 | 类型 | 说明 |
|------|------|------|
| after_price | double | 盘后价 |
| after_high_price | double | 盘后最高 |
| after_low_price | double | 盘后最低 |
| after_volume | int64 | 盘后成交量 |
| after_turnover | double | 盘后成交额 |
| after_change_val | double | 盘后涨跌额 |
| after_change_rate | double | 盘后涨跌幅（%） |
| after_amplitude | double | 盘后振幅（%） |

**夜盘字段（非夜盘时段为 0）：**

| 字段 | 类型 | 说明 |
|------|------|------|
| overnight_price | double | 夜盘价 |
| overnight_high_price | double | 夜盘最高 |
| overnight_low_price | double | 夜盘最低 |
| overnight_volume | int64 | 夜盘成交量 |
| overnight_turnover | double | 夜盘成交额 |
| overnight_change_val | double | 夜盘涨跌额 |
| overnight_change_rate | double | 夜盘涨跌幅（%） |
| overnight_amplitude | double | 夜盘振幅（%） |

**特殊行为：** 部分代码无法解析时有效代码正常返回、无效代码静默跳过（ret_code 仍为 0）。

**错误码：**
| ret_code | 触发条件 | 处理建议 |
|----------|----------|----------|
| 0 | 成功（含部分无效代码被跳过） | 对比请求与返回的 code 列表识别无效项 |
| -3 | code_list 缺失/为空/超 400 | 修正请求体重试 |
| -7 | 全部代码均无法解析 | 确认市场前缀和代码有效性 |
| -4/-6 | 网关内部错误 | 可重试 |

---

## quote_cur_kline — 最新 K 线

获取指定标的最新 N 根 K 线，支持多周期和复权类型。返回相对当前时间的最近 N 根，无法指定历史时间窗口。

**支持市场：** HK（正股/信托/REIT/窝轮/牛熊/界内证/指数/板块/ETF/期权）、US（正股/ETF/指数）、SH/SZ（正股/ETF/指数/板块）、BJ（正股/指数）

**参数：**
| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| symbol | string | 是 | — | 股票代码，如 `HK.00700` |
| num | int | 是 | — | K 线根数，范围 1~370 |
| ktype | int | 否 | 2 | K 线周期（见下方枚举） |
| autype | int | 否 | 1 | 复权类型（见下方枚举） |
| extended_time | int | 否 | 0 | 盘前盘后/夜盘开关（见下方枚举） |

## quote_history_kline — 历史 K 线

获取指定时间范围内的历史 K 线数据，支持向更早数据翻页。优先股/SPAC/可转债/牛熊证返回空列表。

**支持市场前缀：** HK、US、SH、SZ、BJ、SG、CA、AU、FX、JP、CC 等。支持品类：正股、ETF、指数、期货、期权、加密货币。

**参数：**
| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| symbol | string | 是 | — | 股票代码，如 `HK.00700`、`US.FUTU` |
| end | string | 是 | — | 结束日期 yyyy-MM-dd（含） |
| start | string | 否 | — | 起始日期 yyyy-MM-dd（含）；省略则从 end 往前推 num 根 |
| num | int | 否 | 370 | K 线根数，范围 1~370 |
| ktype | int | 否 | 2 | K 线周期（同 cur_kline 枚举） |
| autype | int | 否 | 1 | 复权类型：0=不复权 / 1=前复权 / 2=后复权 |
| extended_time | int | 否 | 0 | 盘前盘后/夜盘开关（同 cur_kline 枚举） |

### ktype 枚举（K 线周期）

| 值 | 含义 | 值 | 含义 |
|----|------|----|------|
| 1 | 1 分钟 | 10 | 3 分钟 |
| 2 | 日（默认） | 11 | 季 |
| 3 | 周 | 14 | 120 分钟 |
| 4 | 月 | 15 | 240 分钟 |
| 5 | 年 | 26 | 10 分钟 |
| 6 | 5 分钟 | 29 | 180 分钟 |
| 7 | 15 分钟 | | |
| 8 | 30 分钟 | | |
| 9 | 60 分钟 | | |

### autype 枚举（复权类型）

| 值 | 含义 |
|----|------|
| 0 | 不复权 |
| 1 | 前复权（除息，默认） |
| 2 | 后复权（除息） |
| 3 | 前复权（含息） |
| 4 | 后复权（含息） |

### extended_time 枚举

| 值 | 含义 |
|----|------|
| 0 | 不含盘前盘后（默认） |
| 1 | 含盘前盘后（仅美股 1 分钟 K 有效） |
| 2 | 含夜盘（美股） |

### 返回 — cur_kline: `data.kline_list[]`

| 字段 | 类型 | 说明 |
|------|------|------|
| code | string | 标的代码 |
| name | string | 英文名 |
| sc_name | string | 简体中文名 |
| tc_name | string | 繁体中文名 |
| time_key | int64 | K 线时间戳（**毫秒**） |
| date | int | K 线日期（YYYYMMDD 整数；分钟 K 为交易日，日线及以上为本地日期） |
| open_price | float | 开盘价 |
| close_price | float | 收盘价（最新一根=当前最新价） |
| high_price | float | 最高价 |
| low_price | float | 最低价 |
| last_close_price | float | 前收盘价 |
| volume | int | 成交量（股） |
| turnover | float | 成交额 |
| turnover_rate | float | 换手率（%）；为 0 时可能省略 |
| pe | float | 市盈率 |
| change_rate | float | 涨跌幅（%）= (close - last_close) / last_close × 100 |

### 返回 — history_kline: `data`

**顶层额外字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| data.next_time | int64 | 下一页起始时间（毫秒时间戳）；翻页时将其转为日期传入 `end` |
| data.volume_precision | int | 成交量精度 n；volume 已按 10^n 缩放。正股/ETF/期货/期权通常为 0；加密货币/事件合约可能 >0 |

**`data.kline_list[]` 元素：**

| 字段 | 类型 | 说明 |
|------|------|------|
| time_key | int64 | K 线时间戳（**毫秒**） |
| date | int | K 线日期（YYYYMMDD） |
| time_zone | int | 时区偏移（分钟），如 480=HK，-300=美东夏令 |
| open | float | 开盘价 |
| close | float | 收盘价 |
| high | float | 最高价 |
| low | float | 最低价 |
| last_close | float | 前收盘价 |
| volume | int | 成交量（股） |
| turnover | float | 成交额 |
| turnover_rate | float | 换手率（%） |
| pe_ratio | float | 市盈率 |
| change_rate | float | 涨跌幅（%） |
| name | string | 英文名 |
| sc_name | string | 简体中文名 |
| tc_name | string | 繁体中文名 |
| open_interest | int | 未平仓合约数（仅期货/期权；其他品类为 0 或不返回） |
| settle_price | float | 结算价（仅期货/期权日线及以上；正股/ETF/指数会回填 close，应忽略） |
| implied_volatility | float | 隐含波动率（%）（仅期权；其他品类为 0 或不返回） |

**history_kline 与 cur_kline 字段名差异：**
| cur_kline | history_kline |
|-----------|---------------|
| open_price | open |
| close_price | close |
| high_price | high |
| low_price | low |
| last_close_price | last_close |
| pe | pe_ratio |

### 错误码

**cur_kline：**
| ret_code | 触发条件 | 处理建议 |
|----------|----------|----------|
| 0 | 成功 | — |
| -3 | 必填参数缺失、num>370、ktype/autype 枚举值无效 | 修正参数重试 |
| -4 | 代码无效或参数组装失败 | 确认证券代码存在 |
| -5 | 后端调用失败（网络/超时） | 可重试 |
| >0 | 后端业务错误透传（无权限/风控/限流等） | 查看 ret_msg 详情 |

**history_kline：**
| ret_code | 触发条件 | 处理建议 |
|----------|----------|----------|
| 0 | 成功（kline_list 为空表示有效但无数据） | — |
| -3 | 缺少 end、类型错误、ktype 超范围、日期格式不匹配 | 修正参数重试 |
| -7 | symbol 格式合法但证券不存在 | 通过搜索接口确认代码 |
| -8 | 市场前缀不在支持范围 | 确认市场前缀有效 |

---
