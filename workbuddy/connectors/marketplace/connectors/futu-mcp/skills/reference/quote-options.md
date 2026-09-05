# 衍生品工具参考

## quote_option_expiration_date — 期权到期日列表

获取标的物的期权到期日列表。支持港/美/日股票及指数期权。

**参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| symbol | string | 是 | 标的代码，如 `HK.00700`、`US.AAPL` |
| index_option_type | int | 否 | 指数期权类型（仅指数标的需传）：港股 1=HSI/2=HSCEI/3=小恒指/4=小国企/5=恒生科技；美股 1001=VIX/1003=XSP/1007=DJX/1020=RUT 等；日股 2001=N225/2002=N225M/2003=TOPIX |
| filter_standard | string | 否 | ALL/STANDARD/NON_STANDARD，默认 ALL |
| filter_expiration_cycles | string | 否 | 按到期周期筛选，逗号分隔，如 `MONTH,QUARTERLY` |

**返回 `data.expiration_list[]`：**

| 字段 | 类型 | 说明 |
|------|------|------|
| strike_time | string | 到期日（yyyy-MM-dd） |
| option_expiry_date_distance | int | 距到期日天数（负数=已过期） |
| expiration_cycle | string | 到期周期类型 |

---

## quote_option_chain — 期权链

获取标的在指定到期日范围内的期权合约列表（每条为单个 CALL 或 PUT）。

**参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| symbol | string | 是 | 标的代码 |
| start | string | 否 | 起始到期日 yyyy-MM-dd |
| end | string | 否 | 结束到期日 yyyy-MM-dd |
| index_option_type | int | 否 | 同上 |
| filter_standard | string | 否 | 同上 |

**返回 `data.option_chain[]`：**

| 字段 | 类型 | 说明 |
|------|------|------|
| code | string | 期权合约代码，如 `HK.TCH260528C230000` |
| stock_id | uint64 | 期权合约内部 ID |
| name | string | 合约英文名 |
| sc_name | string | 合约简体中文名 |
| tc_name | string | 合约繁体中文名 |
| lot_size | int | 每手合约数，如 100 |
| stock_type | string | 证券类型，固定为 `DRVT` |
| option_type | string | 期权方向：CALL / PUT |
| stock_owner | string | 标的正股代码，如 `HK.00700` |
| strike_time | string | 到期日（yyyy-MM-dd） |
| strike_price | number | 行权价（实际值） |
| index_option_type | string | 指数期权类型：NORMAL / SMALL / N/A |
| expiration_cycle | string | 到期周期 |
| option_standard_type | string | 规格类型：STANDARD / NON_STANDARD / N/A |

每次最多返回 20 个到期日（最近优先）。

---

## quote_option_volatility — 期权波动率分析

获取期权合约的 IV/HV 时序分析及统计摘要。

**参数：**
| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| symbol | string | 是 | — | 期权合约代码，如 `HK.TCH260528C230000` |
| query_time_period | int | 否 | 2 | 查询周期：1=1 周, 2=1 月, 3=3 月, 4=6 月, 5=1 年 |
| hv_time_period | int | 否 | 30 | 历史波动率计算天数，5~250 |

**返回 `data.item_list[]`：**

| 字段 | 类型 | 说明 |
|------|------|------|
| timestamp | int64 | 时间戳（毫秒） |
| implied_volatility | float | 隐含波动率（百分比，如 28.391 = 28.391%） |
| history_volatility | float | 历史波动率（百分比） |
| volatility_premium | float | 波动率溢价（IV - HV，百分比） |

**返回 `data.extra`：**

| 字段 | 类型 | 说明 |
|------|------|------|
| average_impvol | float | 期间平均隐含波动率（百分比） |
| impvol_status | string | 波动率状态：FLUCTUATING(震荡) / OVERVALUED(偏高) / UNDERVALUED(偏低) |
| analysis | string | 波动率分析文本（多行以 `\n` 分隔） |

---

## quote_option_exercise_probability — 期权行权概率

获取期权合约到期时为实值的历史概率时序。

**参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| symbol | string | 是 | 期权合约代码 |
| limit | int | 否 | 最大返回条数，1~1000 |

**返回 `data.item_list[]`：**

| 字段 | 类型 | 说明 |
|------|------|------|
| timestamp | int64 | 时间戳（毫秒） |
| security_price | float | 标的资产价格 |
| strike_probability | float | 行权概率（百分比，如 97.915 = 97.915%） |

---

## quote_option_screen — 期权筛选器

跨市场多维度筛选期权合约，支持按标的、合约属性、行情指标等多维度组合筛选，带排序和分页。

**参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| strategy | object | 是 | 筛选策略（见下方详细说明） |
| field_filter | object | 否 | 指定返回字段（int 字段设为 1，string 字段如 option_name/product_code 设为字符串，嵌套对象如 underlying_info 用子对象）。省略时仅返回 volume/price/chg_ratio/implied_volatility + option_id |
| sort_obj | object | 否 | 排序：`{sort_field: {<字段名>: 1}, is_asc: 0或非0}`。sort_field 中设恰好一个字段为 1。省略按 volume 降序 |
| limit | int | 否 | 每页条数，默认 100，最大 1000；可为 0（仅计数，配合 request_exact_data=0） |
| next_key | string | 否 | 分页游标，首次为空，后续传 pagination.next_key，直到 has_more=false |
| request_exact_data | int | 否 | 1=返回详情列表(默认)，0=仅返回 has_more+total（option_list 为空） |

### strategy 结构

```json
{
  "market_category_list": [0],
  "filter_group_list": [
    {"underlying_list": [{"indicator_type": 101, "indicator_value": {"value_list": [205189]}}]},
    {"option_list": [{"indicator_type": 1003, "indicator_value": {"value_list": [1]}}]},
    {"option_list": [{"indicator_type": 1002, "indicator_value": {"value_interval": {"min_value": 7, "max_value": 45}}}]}
  ]
}
```

**market_category_list** — 市场类别数组（取并集）：
- 0=US_STOCK, 1=US_INDEX, 2=US_FUTURE, 3=HK_STOCK, 4=HK_INDEX, 5=JP_STOCK, 6=JP_INDEX

**filter_group_list** — 条件组数组，组间 AND 关系。每组含以下之一：`underlying_list` / `option_list` / `chain_list` / `combo_list`。组内多条件取 OR；跨指标需 AND 时各放独立组。

每个条件结构：

| 字段 | 类型 | 说明 |
|------|------|------|
| indicator_type | int | 指标类型编号（见下方枚举表） |
| indicator_value | object | 匹配值，二选一填写 `value_list` 或 `value_interval` |
| indicator_value.value_list | int[] | 离散值匹配（如期权类型 1=CALL） |
| indicator_value.value_interval | object | 区间匹配 |
| indicator_value.value_interval.min_value | int | 区间下界（省略则无下界） |
| indicator_value.value_interval.max_value | int | 区间上界（省略则无上界） |
| indicator_value.value_interval.exclude_min | bool | 是否排除下界（默认 false） |
| indicator_value.value_interval.exclude_max | bool | 是否排除上界（默认 false） |
| sub_indicator_list | array | 子指标列表（仅 §SUB 标记的复合指标需要，结构同本表）|

**离散值示例（筛选 CALL）：**
```json
{"indicator_type": 1003, "indicator_value": {"value_list": [1]}}
```

**区间示例（剩余 7~45 天）：**
```json
{"indicator_type": 1002, "indicator_value": {"value_interval": {"min_value": 7, "max_value": 45}}}
```

### underlying_list indicator_type

| indicator_type | 说明 | 值说明 |
|---|---|---|
| 101 | 标的代码(精确匹配) | value_list 传 stock_id |
| 102 | 自选/筛选器 ID | value_list 传策略 ID |
| 103 | 板块 | 需额外 plate_list 字段 |
| 201 | 总期权成交量 | value_interval |
| 202 | 总未平仓量 | value_interval |
| 203 | IV×1e3 | value_interval |
| 204 | HV×1e3 | value_interval |
| 205 | IV_Rank×1e3 | value_interval |
| 206 | IV百分位×1e3 | value_interval |
| 207 | IV变化×1e3 | value_interval |
| 208 | IV变化率×1e3 | value_interval |
| 209 | IV/HV×1e3 | value_interval |
| 210 | IV-HV×1e3 | value_interval |
| 301 | 财报时间戳(秒) | value_interval |
| 302 | IV_CRUSH均值×1e3 | §SUB |
| 401 | 市值×1e3 | value_interval |
| 402 | 标的价格×1e9 | value_interval |
| 403 | 涨跌幅×1e3 | value_interval |

### option_list indicator_type

| indicator_type | 说明 | 值说明 |
|---|---|---|
| 1001 | 行权价×1e9 | value_interval |
| 1002 | 剩余天数 | value_interval |
| 1003 | 期权类型 | value_list: 1=CALL, 2=PUT |
| 1004 | 行权方式 | value_list: 0=美式, 1=欧式, 2=百慕大 |
| 1005 | 到期类型 | value_list: 0=月, 1=周, 2=月末, 3=季 |
| 1006 | 产品代码 | value_list 传字符串 |
| 1007 | 到期日时间戳(秒) | value_interval |
| 2001 | 价内(0/1) | value_list |
| 2002 | 价格×1e9 | value_interval |
| 2003 | 中间价×1e9 | value_interval |
| 2004 | 买一价×1e9 | value_interval |
| 2005 | 卖一价×1e9 | value_interval |
| 2006 | 买卖价差×1e9 | value_interval |
| 2007 | 买一量 | value_interval |
| 2008 | 卖一量 | value_interval |
| 2009 | 买卖比×1e3 | value_interval |
| 2010 | 涨跌幅×1e3 | value_interval |
| 2011 | 成交量 | value_interval |
| 2012 | 成交额×1e3 | value_interval |
| 2013 | 未平仓量 | value_interval |
| 2014 | 未平仓价值×1e3 | value_interval |
| 2015 | 未平仓变化 | §SUB |
| 2016 | 成交量变化率×1e3 | §SUB |
| 2017 | 未平仓变化率×1e3 | §SUB |
| 2018 | 成交量/未平仓×1e3 | value_interval |
| 2019 | 均量×1e3 | §SUB |
| 2020 | 均未平仓×1e3 | §SUB |
| 2021 | 溢价×1e9 | value_interval |
| 3001 | IV×1e3 | value_interval |
| 3002 | HV×1e3 | value_interval |
| 3003 | IV/HV×1e3 | value_interval |
| 3004 | Delta×1e5 | value_interval |
| 3005 | Gamma×1e5 | value_interval |
| 3006 | Vega×1e5 | value_interval |
| 3007 | Theta×1e5 | value_interval |
| 3008 | Rho×1e5 | value_interval |
| 3009 | 杠杆×1e5 | value_interval |
| 3010 | 有效杠杆×1e5 | value_interval |
| 3011 | 买入打和涨幅×1e3 | value_interval |
| 3012 | 卖出打和跌幅×1e3 | value_interval |
| 3013 | 买入盈利概率×1e3 | value_interval |
| 3014 | 卖出盈利概率×1e3 | value_interval |
| 3019 | 到期行权概率×1e3 | value_interval |
| 3021 | 卖出年化收益×1e3 | value_interval |
| 3022 | 卖出区间收益×1e3 | value_interval |
| 3023 | 买入打和价×1e9 | value_interval |
| 4001 | 财报后首个到期(0/1) | value_list |

### chain_list indicator_type

| indicator_type | 说明 |
|---|---|
| 20000 | 预期波动×1e3 |
| 20001 | IVx×1e3 |
| 20002 | Call成交量 |
| 20003 | Put成交量 |
| 20004 | 总成交量 |

### field_filter 示例

```json
{
  "hp_strike_price": 1,
  "option_name": "x",
  "product_code": "x",
  "option_type": 1,
  "exercise_type": 1,
  "expiration_type": 1,
  "in_the_money": 1,
  "left_day": 1,
  "price": 1,
  "mid_price": 1,
  "bid_price": 1,
  "ask_price": 1,
  "bid_ask_spread": 1,
  "change_ratio": 1,
  "volume": 1,
  "turnover": 1,
  "open_interest": 1,
  "implied_volatility": 1,
  "delta": 1,
  "gamma": 1,
  "vega": 1,
  "theta": 1,
  "rho": 1,
  "leverage_ratio": 1,
  "underlying_info": {"price": 1, "iv": 1, "hv": 1, "iv_rank": 1, "volume": 1, "open_interest": 1}
}
```

### sort_obj 示例

```json
{"sort_field": {"volume": 1}, "is_asc": 0}
```
- `sort_field`：恰好一个字段设为 1（如 `{"volume":1}`、`{"implied_volatility":1}`、`{"open_interest":1}`、`{"delta":1}`）
- `is_asc`：非 0=升序，0/省略=降序(默认)

**返回 `data.option_list[]` + `pagination`：**

| 字段 | 类型 | 说明 |
|------|------|------|
| pagination.total | int | 总数（request_exact_data=0 时上限 9999） |
| pagination.has_more | bool | 是否有更多 |
| pagination.next_key | string | 下页游标（`"-1"` 表示无更多） |

**option_list[] 合约基础字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| code | string | 合约代码，如 `US.AAPL260115C00200000` |
| option_name | string | 合约名称，如 `AAPL 260526 312.50C` |
| strike_price | double | 行权价（原始值÷1e9） |
| strike_date | string | 到期日（yyyyMMdd） |
| strike_date_timestamp | int64 | 到期日时间戳（毫秒） |
| option_type | string | 方向：CALL / PUT |
| exercise_type | string | 行权风格：AMERICAN / EUROPEAN |
| expiration_type | string | 到期类型：WEEK / MONTH / QUARTER 等 |
| in_the_money | string | 价值状态：IN_THE_MONEY / OUT_OF_THE_MONEY |
| left_day | int | 距到期天数 |
| multiplier | double | 合约乘数（÷1e9） |
| contract_share_size | double | 每张合约股数（÷1e9） |
| product_code | string | 期权链产品代码 |

**option_list[] 行情与盘口字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| price | double | 最新价（÷1e9） |
| mid_price | double | 买卖中间价（÷1e9） |
| bid_price | double | 买一价（÷1e9） |
| ask_price | double | 卖一价（÷1e9） |
| bid_ask_spread | double | 买卖价差（÷1e9） |
| bid_volume | int | 买一量 |
| ask_volume | int | 卖一量 |
| change_ratio | double | 涨跌幅百分比（÷1e5） |
| volume | int | 成交量 |
| turnover | double | 成交额（÷1e3） |
| open_interest | int | 未平仓量 |

**option_list[] 波动率与 Greeks 字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| implied_volatility | double | 隐含波动率百分比（÷1e5） |
| history_volatility | double | 历史波动率百分比（÷1e5） |
| delta | double | Delta（÷1e5） |
| gamma | double | Gamma（÷1e5） |
| vega | double | Vega（÷1e5） |
| theta | double | Theta（÷1e5） |
| rho | double | Rho（÷1e5） |
| leverage_ratio | double | 杠杆比率（÷1e5） |

**option_list[].underlying_info — 标的统计子对象：**

| 字段 | 类型 | 说明 |
|------|------|------|
| stock_id | uint64 | 标的内部 ID |
| volume | int | 标的全部期权总成交量 |
| open_interest | int | 标的全部期权总未平仓 |
| iv | double | 标的 IV 百分比（÷1e5） |
| hv | double | 标的 30 日 HV 百分比（÷1e5） |
| iv_rank | double | IV Rank 百分比（÷1e5） |
| price | double | 标的最新价（÷1e9） |
| change_ratio | double | 标的涨跌幅百分比（÷1e5） |

**常用 filter 条件（filter_group_list 中）：**
- option_list: 行权价(1001)、剩余天数(1002)、期权类型(1003, 1=CALL/2=PUT)、到期日(1007)、价格(2002)、成交量(2011)、未平仓(2013)、IV(3001)、Delta(3004)
- underlying_list: 标的代码(101)、总成交量(201)、IV(203)

---
