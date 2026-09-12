# 期货/窝轮牛熊证
## quote_future_info — 期货合约信息

批量获取期货合约的静态属性。

**参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| code_list | string[] | 是 | 期货代码列表，如 `["HK.HSImain"]`，最多 400 |

**返回 `data.future_info_list[]`：**

| 字段 | 类型 | 说明 |
|------|------|------|
| code | string | 合约代码，如 `HK.HSImain` |
| name | string | 合约名称，如 `HSI Futures (JUN6)` |
| owner | string | 标的代码或品种代码（指数期货为指数代码，商品期货为品种名） |
| exchange | string | 交易所：HKEX / CME / CBOT / NYMEX / COMEX / CBOE / SGX / OSE |
| type | string | 合约类型：Equity Index / Single Stock / Metals / Energy / Agricultural / Interest Rates / Cryptocurrency / FX |
| size | float | 合约规模数值 |
| size_unit | string | 合约规模单位，如 `Index Points×HKD`、`barrels` |
| price_currency | string | 报价币种：HKD / USD / CNH / SGD / JPY |
| price_unit | string | 报价单位，如 `Index Point` |
| min_change | float | 最小变动价位数值 |
| min_change_unit | string | 最小变动单位，如 `Index Point`、`USD/barrels` |
| trade_time | string | 交易时段，如 `(09:15 - 12:00), (13:00 - 16:30), (17:15 - 03:00)` |
| time_zone | string | 交易所时区：CCT / ET / CT / SGT / JST |
| last_trade_time | int | 最后交易日（毫秒时间戳），主连/连续合约固定为 0 |
| exchange_format_url | string | 交易所合约规格页面链接 |
| delivery_type | string | 交割方式：UNKNOWN / PHYSICAL / CASH |

---

## quote_referencefuture_list — 关联期货

获取标的（通常为指数）的关联期货合约列表。

**参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| symbol | string | 是 | 标的代码，如 `HK.800000`（恒指） |

**返回 `data.reference_list[]`：**

| 字段 | 类型 | 说明 |
|------|------|------|
| code | string | 期货代码，如 `HK.HSImain`、`HK.HSI2606` |
| stock_name | string | 合约英文名 |
| sc_name | string | 合约简体中文名 |
| tc_name | string | 合约繁体中文名 |
| stock_type | string | 证券类型，固定为 `FUTURE` |
| lot_size | int | 每手规模（合约乘数），如 50 |
| future_valid | bool | 期货标识，固定为 true |
| future_main_contract | bool | 是否主连合约（true=主连，false=月份合约） |
| future_last_trade_time | string | 最后交易日（yyyy-MM-dd），主连合约为空字符串 |
| list_time | int | 上市时间（毫秒时间戳），无记录时为 0 |

---

## quote_warrant_screen — 窝轮/牛熊证筛选

窝轮筛选器，支持数十个筛选维度和多级排序。支持市场：港股(1)、新加坡(4)、马来西亚(15)。

**参数：**
| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| market_type | int | 否 | 1 | 1=港股, 4=新加坡, 15=马来西亚 |
| stock_owner | string | 否 | — | 正股代码快捷筛选（如 `HK.00700`），自动转为 screen_groups 条件 |
| screen_groups | object[] | 否 | — | 筛选条件列表 |
| sorts | object[] | 否 | — | 排序条件列表 |
| limit | int | 否 | 200 | 每页条数，最大 1000 |
| next_key | string | 否 | — | 分页游标，首次为空 |
| only_count | bool | 否 | false | 仅返回计数不返回详情 |
| is_delay | bool | 否 | false | 是否使用延迟数据 |

### screen_groups 元素结构

两种用法——离散选择（choices）或区间筛选（interval）：

| 字段 | 类型 | 说明 |
|------|------|------|
| field_id | int | 筛选字段编号（见下方枚举） |
| choices | object[] | 离散值匹配（多个为 OR），元素：`{"content_type": 1, "value": <int>}` |
| interval | object | 区间匹配 |
| interval.lower | object | 下界：`{"value": <int>, "is_included": true}` |
| interval.upper | object | 上界：`{"value": <int>, "is_included": true}` |

**注意：** interval 的 value 必须预乘精度因子（如杠杆 10~100 → value 10000~100000）。

### sorts 元素结构

| 字段 | 类型 | 说明 |
|------|------|------|
| sort_field_id | int | 排序字段编号（同 field_id） |
| sort_flag | bool | true=降序, false=升序 |

### 请求示例

```json
{
  "market_type": 1,
  "limit": 5,
  "screen_groups": [
    {"field_id": 6, "choices": [{"content_type": 1, "value": 1}]},
    {"field_id": 5, "choices": [{"content_type": 1, "value": 54047868453564}]},
    {"field_id": 19, "choices": [{"content_type": 1, "value": 0}]},
    {"field_id": 52, "choices": [{"content_type": 1, "value": 1}]},
    {"field_id": 16, "interval": {"lower": {"value": 10000, "is_included": true}, "upper": {"value": 100000, "is_included": true}}}
  ],
  "sorts": [{"sort_field_id": 16, "sort_flag": true}]
}
```

### field_id 枚举

| field_id | 名称 | 说明 | 类型 | 精度 |
|----------|------|------|------|------|
| 4 | ISSUER_ID | 发行人 ID | choice | — |
| 5 | STOCK_OWNER | 正股 ID | choice (value=stock_id) | — |
| 6 | WARRANT_TYPE | 窝轮类型 | choice: 1=认购,2=认沽,3=牛证,4=熊证,5=界内证 | — |
| 7 | CONVERSION_RATIO | 换股比率 | interval | ×1e3 |
| 8 | CURRENT_PRICE | 现价 | interval | ×1e3 |
| 9 | STREET_RATIO | 街货比% | interval | ×1e3 |
| 10 | VOLUME | 成交量 | interval | — |
| 11 | MATURITY_DATE | 到期日 | interval (秒时间戳) | — |
| 12 | STRIKE_PRICE | 行权价 | interval | ×1e3 |
| 13 | PREMIUM | 溢价%（可为负） | interval | ×1e5 |
| 14 | RECOVERY_PRICE | 收回价（牛熊证） | interval | ×1e3 |
| 15 | IMPLIED_VOLATILITY | 引伸波幅% | interval | ×1e2 |
| 16 | LEVERAGE_RATIO | 杠杆比率 | interval | ×1e3 |
| 17 | PRICE_RECOVERY_RATIO | 正股距收回价% | interval | ×1e5 |
| 18 | DELTA | Delta | interval | ×1e3 |
| 19 | STATUS | 状态 | choice: 0=正常,2=停牌,3=待上市 | — |
| 20 | IPO_TIME | 上市时间 | interval (秒时间戳) | — |
| 21 | BUY_VOL | 买一量 | interval | — |
| 22 | SELL_VOL | 卖一量 | interval | — |
| 23 | EFFECTIVE_LEVERAGE | 有效杠杆 | interval | ×1e3 |
| 24 | LAST_CLOSE_PRICE | 昨收价 | interval | ×1e3 |
| 25 | TURNOVER | 成交额 | interval | — |
| 26 | SELL_PRICE | 卖一价 | interval | ×1e3 |
| 27 | BUY_PRICE | 买一价 | interval | ×1e3 |
| 28 | HIGH_PRICE | 最高价 | interval | ×1e3 |
| 29 | LOW_PRICE | 最低价 | interval | ×1e3 |
| 30 | RATIO_ITM_OTM | 价内/价外% | interval | ×1e5 |
| 31 | BREAK_EVEN_POINT | 打和点 | interval | ×1e5 |
| 32 | AMPLITUDE | 振幅% | interval | ×1e5 |
| 33 | SCORE_FAXING | 法兴评分 | interval | ×1e5 |
| 34 | LAST_TRADE_DATE | 最后交易日 | interval (秒时间戳) | — |
| 35 | STREET_VOLUME | 街货量 | interval | — |
| 36 | LOT_SIZE | 每手股数 | interval | — |
| 37 | ISSUE_SIZE | 发行量 | interval | — |
| 38 | IPO_PRICE | 发行价 | interval | ×1e3 |
| 39 | LOWER_STRIKE_PRICE | 下界行权价(界内证) | interval | ×1e3 |
| 40 | UPPER_STRIKE_PRICE | 上界行权价(界内证) | interval | ×1e3 |
| 41 | IW_PRICE_STATUS | 界内/界外状态 | choice: 0=界内,1=上界外,2=下界外 | — |
| 42 | SENSITIVITY | 敏感度 | interval | ×1e3 |
| 43 | CONVERSION_PRICE | 换股价 | interval | — |
| 44 | CHANGE_RATE | 涨跌幅% | interval | ×1e3 |
| 45 | CHANGE_VALUE | 涨跌额 | interval | — |
| 51 | SCORE | 综合评分 | interval | ×1e5 |
| 52 | FILTER_NO_TRADE | 过滤零交易 | choice: 0=不过滤,1=过滤 | — |
| 53 | CURRENCY_CODE | 币种 | interval | — |
| 54 | STOCK_OWNER_PRICE | 正股价格 | interval | ×1e3 |

---

### 返回 `data.warrants[]` + `pagination`

**pagination：**

| 字段 | 类型 | 说明 |
|------|------|------|
| total | int | 匹配总数 |
| has_more | bool | 是否有下一页 |
| next_key | string | 下页游标（`"-1"` 表示无更多） |

**warrants[] 通用字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| code | string | 窝轮代码，如 `HK.18869` |
| name | string | 英文名 |
| sc_name | string | 简体中文名 |
| tc_name | string | 繁体中文名 |
| stock_owner | string | 正股代码，如 `HK.00700` |
| type | string | 类型：CALL/PUT/BULL/BEAR/INLINE/N/A |
| issuer | string | 发行人代码（2 字母，如 JP/GS/UB/HS） |
| status | string | 状态：NORMAL/STOP_TRADE/PENDING_LISTING/N/A |
| maturity_time | string | 到期日（yyyy-MM-dd） |
| maturity_timestamp | int | 到期日毫秒时间戳 |
| list_time | string | 上市日期（yyyy-MM-dd） |
| list_timestamp | int | 上市日毫秒时间戳 |
| last_trade_time | string | 最后交易日（yyyy-MM-dd） |
| last_trade_timestamp | int | 最后交易日毫秒时间戳 |
| lot_size | int | 每手股数 |
| issue_size | int | 发行量 |

**warrants[] 价格与成交：**

| 字段 | 类型 | 说明 |
|------|------|------|
| cur_price | float | 现价 |
| last_close_price | float | 昨收价 |
| high_price | float | 最高价 |
| low_price | float | 最低价 |
| bid_price | float | 买一价 |
| ask_price | float | 卖一价 |
| bid_vol | int | 买一量 |
| ask_vol | int | 卖一量 |
| volume | int | 成交量 |
| turnover | float | 成交额 |
| price_change_val | float | 涨跌额 |
| change_rate | float | 涨跌幅（%） |
| amplitude | float | 振幅（%） |

**warrants[] 衍生指标：**

| 字段 | 类型 | 说明 |
|------|------|------|
| strike_price | float | 行权价 |
| conversion_ratio | float | 换股比率 |
| conversion_price | float | 换股价 |
| break_even_point | float | 打和点 |
| premium | float | 溢价（%） |
| ipop | float | 价内/价外%（正=价内，负=价外） |
| leverage | float | 杠杆比率 |
| effective_leverage | float | 有效杠杆 |
| delta | float | Delta |
| implied_volatility | float | 引伸波幅（%） |
| score | float | 综合评分 |
| street_rate | float | 街货比（%） |
| street_vol | int | 街货量 |

**warrants[] 牛熊证/界内证专有：**

| 字段 | 类型 | 说明 |
|------|------|------|
| recovery_price | float | 收回价（仅牛熊证） |
| price_recovery_ratio | float | 正股距收回价%（仅牛熊证） |
| upper_strike_price | float | 上界行权价（仅界内证） |
| lower_strike_price | float | 下界行权价（仅界内证） |
| inline_price_status | string | 界内状态：WITH_IN/OUTSIDE/N/A |
