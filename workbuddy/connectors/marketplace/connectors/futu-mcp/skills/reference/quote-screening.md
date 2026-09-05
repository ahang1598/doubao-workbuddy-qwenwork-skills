# 筛选与板块工具参考

## quote_stock_screen — 条件选股

多因子组合筛选全市场股票，支持估值/涨跌/财务/技术形态/经纪商持仓/期权等维度，分页返回匹配结果及指定因子值。

**支持市场：** HK/US/CN/SG/CA/AU/JA/MY（不支持 KR）

**参数：**
| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| screen_queries | object[] | 是 | — | 筛选条件数组，多条件为 AND 关系（每个元素填且仅填 11 种查询类型之一） |
| retrieve_queries | object[] | 否 | — | 返回列定义（每个元素填且仅填 9 种检索类型之一），响应 results[] 与此数组对齐 |
| sort | object | 否 | — | 单字段排序；与 sorts 互斥，sorts 优先 |
| sorts | object[] | 否 | — | 多字段排序，数组顺序即优先级 |
| limit | int | 否 | 200 | 每页条数，最大 300 |
| next_key | string | 否 | — | 分页游标；首次留空，后续传回 `pagination.next_key` |
| user_stock_list_mode | int | 否 | 0 | 0=不限, 1=仅自选股, 2=仅持仓 |
| watchlist_stock_ids | int[] | 否 | — | 自选股 stock_id 列表；配合 `user_stock_list_mode=1` |
| holding_stock_ids | int[] | 否 | — | 持仓 stock_id 列表；配合 `user_stock_list_mode=2` |

**返回 `data`：**

| 字段 | 类型 | 说明 |
|------|------|------|
| items[] | array | 筛选结果列表 |
| pagination.total | int | 总匹配数 |
| pagination.has_more | bool | 是否有更多 |
| pagination.next_key | string | 下页游标 |

**items[] 元素：**

| 字段 | 类型 | 说明 |
|------|------|------|
| code | string | 股票代码（市场.代码，如 `HK.00700`） |
| name | string | 英文名 |
| sc_name | string | 简体中文名 |
| tc_name | string | 繁体中文名 |
| results[] | array | 返回值列表（与 retrieve_queries 对齐） |

**results[] 元素：**

每个元素是对应 retrieve_queries 类型的结果包装：

| 字段 | 类型 | 说明 |
|------|------|------|
| res.ival | string(int64) | 原始整型值（已乘精度因子） |
| res.dval | float | 浮点值 |
| res.sval | string | 字符串值（如名称） |
| result_type | int | 1=double, 2=int, 3=string |
| value | string | 原始值字符串形式 |

---

### screen_queries 条件类型（11 种，每个元素选一种）

**1. simple_field_query — 离散值筛选（IN）**
```json
{"simple_field_query": {"simple_field": 1, "screen_value_list": [2]}}
```

| simple_field | 含义 | screen_value_list 取值 |
|---|---|---|
| 1 | 市场 | 1=HK, 2=US, 3=CN, 4=SG, 5=CA, 6=AU, 7=JA, 8=MY |
| 2 | 交易所 | 交易所 ID |
| 3 | 指数成分 | 指数 ID |
| 4 | 使用自选股 | — |
| 5 | 有 ADR | 0/1 |
| 6 | 有期权 | 0/1 |
| 7 | 有窝轮 | 0/1 |
| 8 | 有期货 | 0/1 |
| 9 | 有 AH 股 | 0/1 |
| 10 | 伊斯兰合规 | 0/1 |
| 11 | 北向持股 ID | — |
| 12 | 做市商专属 ID | — |

**2. plate_query — 板块筛选**
```json
{"plate_query": {"plate_list": [{"parent_plate_id": 0, "plate_id_list": [12345]}]}}
```

**3. simple_property_query — 行情/估值区间**
```json
{"simple_property_query": {"property": {"name": 2303}, "upper": {"value": 1500000, "includes": true}}}
```

| name | 含义 | 精度因子 |
|------|------|----------|
| 2201 | 最新价 | ×1e3 |
| 2301 | 总市值 | ×1e3 |
| 2302 | 静态 PE | ×1e5 |
| 2303 | PE_TTM | ×1e5 |
| 2304 | PB | ×1e5 |
| 2305 | 股息率 | ×1e3 |
| 2306 | 上市时间戳（秒） | — |

**4. cumulative_property_query — 累计涨跌/换手**
```json
{"cumulative_property_query": {"property": {"name": 3102, "days": 5}, "lower": {"value": 5000, "includes": true}}}
```

| name | 含义 | 精度因子 |
|------|------|----------|
| 3101 | 涨跌额 | ×1e3 |
| 3102 | 涨跌幅 | ×1e3 |
| 3103 | 振幅 | ×1e3 |
| 3104 | 均量 | — |
| 3105 | 均额 | ×1e3 |
| 3106 | 换手率 | ×1e3 |

- `days`: 天数（默认 1，如 5=5 日涨跌幅）
- `period_average`: bool，是否取日均值

**5. financial_property_query — 财务指标**
```json
{"financial_property_query": {"property": {"name": 4110, "term": 100}, "lower": {"value": 15000, "includes": true}}}
```

| name | 含义 | 精度因子 |
|------|------|----------|
| 4101 | 净利润 | ×1e3 |
| 4102 | 利润增速 | ×1e3 |
| 4105 | 营收 | ×1e3 |
| 4106 | 营收增速 | ×1e3 |
| 4107 | 净利率 | ×1e3 |
| 4108 | 毛利率 | ×1e3 |
| 4109 | 负债率 | ×1e3 |
| 4110 | ROE | ×1e3 |
| 4801 | 基本 EPS | ×1e3 |
| 4903 | 流通市值 | ×1e3 |
| 4904 | PS_TTM | ×1e5 |

- `term`: 1=Q1, 2=Q2, 3=Q3, 4=Q4, 6=中期, 9=Q9 累计, 10=最近单季, 100=年报, 200~204=超预期
- `year`: 指定年份（可选）
- `duration`: 持续期（可选）
- `period_average`: 是否取日均（可选）
- `future_duration`: 未来期数（可选）

**6. indicator_positional_query — 技术指标位置关系**

```json
{"indicator_positional_query": {"first_indicator_name": 11, "second_indicator_name": 12, "period_type": 11, "position": 3}}
```

| 字段 | 说明 |
|------|------|
| first_indicator_name | 第一指标（见下方枚举） |
| second_indicator_name | 第二指标 |
| period_type | K 线周期：1=1分, 2=3分, 3=5分, 4=15分, 5=1时, 6=30分, 11=日, 21=周, 31=月 |
| position | 1=上方, 2=下方, 3=上穿, 4=下穿 |
| continuous_period | 持续周期数（可选） |

指标枚举：1=PRICE, 11~17=MA(5/10/20/30/60/120/250), 21~27=EMA(5/10/20/30/60/120/250), 31/32/33=KDJ(K/D/J), 41/42/43=MACD(DIF/DEA/MACD), 51=RSI, 61/62/63=BOLL(上/中/下)

**7. indicator_pattern_query — 技术形态**

```json
{"indicator_pattern_query": {"name": 1, "period_type": 11}}
```

| name | 含义 |
|------|------|
| 1 | MA 多头排列 |
| 2 | MA 空头排列 |
| 3 | EMA 多头排列 |
| 4 | EMA 空头排列 |
| 11/12 | KDJ 金叉/死叉 |
| 13/14 | KDJ 顶/底背离 |
| 21/22 | MACD 金叉/死叉 |
| 23/24 | MACD 顶/底背离 |
| 31/32 | RSI 上穿/下穿 |
| 33/34 | RSI 顶/底背离 |
| 41/42 | 布林上穿上轨/下穿下轨 |
| 43/44 | 布林上穿中轨/下穿中轨 |
| 100 | 看涨形态组 |
| 101 | 看跌形态组 |

**8. featured_property_query — 特色指标**
```json
{"featured_property_query": {"property": {"name": 5203}, "intervals": [{"lower": {"value": 80000}, "upper": {"value": 120000}}]}}
```

| name | 含义 | 精度因子 |
|------|------|----------|
| 5101 | 筹码获利比例 | ×1e3 |
| 5102 | 筹码集中度 | ×1e3 |
| 5203 | Beta | ×1e5 |
| 5211 | 交易热度 | ×1e5 |
| 5212 | 搜索热度 | ×1e5 |
| 5214 | 综合热度 | ×1e5 |
| 5320 | 机构持仓比例 | ×1e3 |
| 5401 | 分析师评级 | — |
| 5403 | 目标价 | ×1e9 |
| 5407 | 晨星评级 | — |

- `period`/`range_period`/`first_custom_param`: 可选参数
- 使用 `intervals` 数组（区间列表）或 `value_set`（离散值列表）

**9. broker_holdings_query — 经纪商持仓（仅港股）**
```json
{"broker_holdings_query": {"property": {"name": 6101, "days": 5}, "intervals": [{"lower": {"value": 5000}}]}}
```

| name | 含义 |
|------|------|
| 6101 | 集中度 |
| 6102 | 经纪商变动 |
| 6103 | 经纪商数量 |
| 6104 | 经纪商排名 |
| 6105 | 经纪商持仓比例 |
| 6106 | CCASS 比例 |
| 6107 | CCASS 变动 |

**10. kline_shape_query — K 线图形（仅港股）**
```json
{"kline_shape_query": {"property": {"name": 1, "period": 11}}}
```

| name | 含义 | name | 含义 |
|------|------|------|------|
| 1 | W 底 | 1001 | W 顶 |
| 2 | 三重底 | 1002 | 三重顶 |
| 3 | 头肩底 | 1003 | 头肩顶 |
| 4 | 圆弧底 | 1004 | 圆弧顶 |
| 5 | 喇叭底 | 1005 | 喇叭顶 |
| 6 | 牛旗 | 1006 | 熊旗 |
| 7 | 多头对称三角 | 1007 | 空头对称三角 |
| 8 | 多头菱形 | 1008 | 空头菱形 |
| 9 | 多头楔形 | 1009 | 空头楔形 |
| 10 | 多头三角 | 1010 | 空头三角 |
| 2000 | 看涨组 | 2001 | 看跌组 |

- `period`: 11=日线, 5=1 小时（仅支持这两种）

**11. option_query — 期权指标**
```json
{"option_query": {"property": {"name": 1000}, "intervals": [{"lower": {"value": 200000}}]}}
```

| name | 含义 | 精度因子 |
|------|------|----------|
| 1000 | 标的 IV | ×1e6 |
| 1001 | IV Rank | — |
| 1002 | IV 百分位 | — |
| 1003 | 财报 IV | — |
| 1004 | IV 变化 | — |
| 1005 | IV 变化率 | — |
| 1006 | HV | — |
| 1007 | IV-HV | — |
| 1008 | IV/HV | — |
| 1009 | 期权成交量 | — |
| 1010 | 期权未平仓 | — |

---

### retrieve_queries 返回列（9 种类型）

每个元素填且仅填一种检索对象，响应 `items[].results[]` 与此数组顺序对齐：

```json
[{"basic_property": {"name": 1102}}, {"simple_property": {"name": 2303}}]
```

| 类型 | 结构 | 说明 |
|------|------|------|
| basic_property | `{name: int}` | 1101=代码, 1102=名称 |
| simple_property | `{name: int}` | 同 simple_property_query 的 name |
| cumulative_property | `{name: int, days: int, period_average?: bool}` | 同 cumulative_property_query |
| financial_property | `{name: int, term: int, year?: int, ...}` | 同 financial_property_query |
| featured_property | `{name: int, period?: int, range_period?: int, first_custom_param?: int}` | 同 featured_property_query |
| indicator_property | `{name: int, period: int, indicator_params?: [int]}` | 技术指标值 |
| broker_property | `{name: int, days: int, param?: int}` | 经纪商因子 |
| kline_shape_property | `{name: int, period: int}` | K 线形态 |
| option_property | `{name: int, param?: int, period?: int}` | 期权因子 |

---

### sort / sorts 排序

```json
{"sort": {"simple_property": {"name": 2301}, "direction": 2}}
```

排序对象可使用 `simple_property` / `cumulative_property` / `financial_property` / `featured_property`。

| direction | 含义 |
|-----------|------|
| 1 | 升序 |
| 2 | 降序 |
| 3 | 绝对值升序 |
| 4 | 绝对值降序 |

`sorts` 为数组，按数组顺序即排序优先级（与 `sort` 互斥，`sorts` 优先）。

---

### 区间值说明

所有区间 `lower`/`upper` 中的 `value` 必须预乘精度因子。例如：
- PE_TTM ≤ 15 → `upper.value = 1500000`（15 × 1e5）
- 涨跌幅 ≥ 5% → `lower.value = 5000`（5 × 1e3）
- `includes`: bool，是否包含边界值
- `lower`/`upper` 可单独使用（开区间）

---

### 错误码

| ret_code | 触发条件 | 处理建议 |
|----------|----------|----------|
| 0 | 成功（含空结果） | — |
| -3 | screen_queries 缺失；limit>300；next_key 非法；user_stock_list_mode 非 0/1/2 | 修正参数重试 |
| -5 | 后端拒绝（simple_field 枚举非法/property name 不存在/市场值超范围等） | 检查查询结构和因子名有效性 |
| -6 | 网关输出映射失败 | 可重试 |

---

## quote_plate_list — 板块列表

获取指定市场和板块类别下的所有板块/行业列表。板块代码（plate_code）本身是 stock_id，可用于订阅行情。

**支持市场：** HK / US / SH / SZ / SG / JP / AU / CA / MY / KR（SH 和 SZ 共享 A 股板块集）

**参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| market | string | 是 | 市场前缀：HK/US/SH/SZ/SG/JP/AU/CA/MY/KR |
| plate_class | string | 是 | 板块类别（见下方枚举，区分大小写） |

**plate_class 枚举：**
| 值 | 含义 |
|----|------|
| ALL | 所有板块类型 |
| INDUSTRY | 行业板块 |
| REGION | 地域板块（**仅 SH/SZ 支持**，其他市场返回 unsupported） |
| CONCEPT | 概念板块 |
| OTHER | 其他板块 |

**返回 `data.plate_list[]`：**

| 字段 | 类型 | 说明 |
|------|------|------|
| code | string | 板块代码（含市场前缀），如 `HK.LIST23618` |
| plate_id | string | 板块 ID（不含市场前缀），如 `LIST23618` |
| plate_name | string | 英文名 |
| sc_name | string | 简体中文名 |
| tc_name | string | 繁体中文名 |

**特殊行为：**
- 后端无数据时返回空 `plate_list` 数组，ret_code 仍为 0
- 参数值区分大小写（如 `INDUSTRY` 有效，`industry` 无效）

**错误码：**
| ret_code | 触发条件 | 处理建议 |
|----------|----------|----------|
| 0 | 成功（含空列表） | — |
| -3 | market 或 plate_class 缺失/值不在枚举内 | 修正参数重试 |
| -5 | 后端调用失败（网络/超时） | 可重试 |
| -8 | plate_class=REGION 但市场非 SH/SZ | 仅对 SH/SZ 使用 REGION |

---

## quote_plate_stock — 板块成分股

获取指定板块的成分股列表，支持约 120 种排序字段和分页。

**参数：**
| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| plate_code | string | 是 | — | 板块代码（从 plate_list 获取），如 `HK.LIST1045` |
| sort_field | string | 否 | NONE | 排序字段（见下方常用枚举；完整约 120 种定义于命名字典） |
| ascend | bool | 否 | true | true=升序, false=降序 |
| price_type | string | 否 | NORMAL | 价格排序口径：NORMAL/BEFORE/AFTER/OVERNIGHT（仅影响价格类排序字段） |
| leverage_direction | int | 否 | 0 | ETF 杠杆方向过滤（仅 ETF 板块有效）：0=全部, 1=多, 2=空 |
| leverage_multiple | int | 否 | 0 | ETF 杠杆倍数过滤（×1e3，如 2000=2x）；0=全部（仅 ETF 板块有效） |
| limit | int | 否 | 200 | 每页条数，最大 1000 |
| next_key | string | 否 | — | 分页游标；首次留空，后续传回 `pagination.next_key` |

**sort_field 常用枚举：**
| 值 | 含义 | 值 | 含义 |
|----|------|----|------|
| NONE | 不排序 | CUR_PRICE | 最新价 |
| CODE | 代码 | CHANGE_RATE | 涨跌幅 |
| NAME | 名称 | VOLUME | 成交量 |
| TURNOVER | 成交额 | MARKET_VAL | 总市值 |
| PE | 市盈率 | PB | 市净率 |
| TURNOVER_RATIO | 换手率 | AMPLITUDE | 振幅 |
| PRICE_CHANGE_VAL | 涨跌额 | CIRC_MARKET_VALUE | 流通市值 |
| DIVIDEND_RATIO_TTM | TTM 股息率 | LIST_TIME | 上市时间 |
| CHANGE_RATIO_5_DAYS | 5 日涨幅 | CHANGE_RATIO_20_DAYS | 20 日涨幅 |
| CHANGE_RATIO_60_DAYS | 60 日涨幅 | CHANGE_RATIO_250_DAYS | 250 日涨幅 |
| HSG_HOLD_RATIO | 北向持股比例 | HSG_DAY_FLOW | 北向当日流入 |
| PRE_CUR_PRICE | 盘前价 | PRE_CHANGE_RATE | 盘前涨跌幅 |
| AFTER_CUR_PRICE | 盘后价 | AFTER_CHANGE_RATE | 盘后涨跌幅 |
| OVERNIGHT_PRICE | 夜盘价 | OVERNIGHT_CHANGE_RATE | 夜盘涨跌幅 |
| HOT | 热度 | ETF_LEVERAGE | ETF 杠杆 |

**返回 `data`：**

| 字段 | 类型 | 说明 |
|------|------|------|
| stock_list[] | array | 成分股列表 |
| pagination.total | int | 板块总成分股数 |
| pagination.has_more | bool | 是否有更多 |
| pagination.next_key | string | 下页游标 |

**stock_list[] 元素：**

| 字段 | 类型 | 说明 |
|------|------|------|
| code | string | 股票代码（含市场前缀），如 `HK.02337` |
| stock_id | int64 | 内部数字标识 |
| stock_name | string | 英文名 |
| sc_name | string | 简体中文名 |
| tc_name | string | 繁体中文名 |
| stock_type | string | 证券类型：STOCK/ETF/INDEX/DRVT 等 |
| lot_size | int | 每手股数（期权=合约股数，期货=合约乘数） |
| list_time | int64 | 上市时间戳（毫秒）；无数据为 0 |

**特殊行为：**
- `leverage_direction` 和 `leverage_multiple` 仅对 ETF 板块生效，其他板块传入也被忽略
- `price_type` 仅影响价格类排序字段的取值口径
- 有效板块但无成分股时返回空 `stock_list`，ret_code 仍为 0

**错误码：**
| ret_code | 触发条件 | 处理建议 |
|----------|----------|----------|
| 0 | 成功（含空列表） | — |
| -3 | plate_code 缺失/市场前缀无效/sort_field 非法/price_type 非法/limit>1000 | 修正参数重试 |
| -4 | 网关组装请求失败 | 可重试 |
| -7 | plate_code 无法解析为有效板块 | 通过 plate_list 接口重新获取有效板块代码 |

---

## quote_owner_plate — 股票所属板块

获取单只股票所属的行业/概念板块列表。仅支持正股和 ETF；指数/窝轮/期权/期货/债券通常无板块归属，返回空数组。

**支持市场：** HK / US / SH / SZ / SG / JP / AU / CA / MY

**参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| symbol | string | 是 | 股票代码（路径参数），如 `HK.00700`、`US.FUTU` |

**返回 `data.sectors[]`：**

| 字段 | 类型 | 说明 |
|------|------|------|
| name | string | 被查询证券英文名（非板块名） |
| sc_name | string | 被查询证券简体中文名 |
| tc_name | string | 被查询证券繁体中文名 |
| plate_code | string | 板块代码（含市场前缀，可用于订阅），如 `HK.LIST1284` |
| plate_name | string | 板块英文名 |
| plate_sc_name | string | 板块简体中文名 |
| plate_tc_name | string | 板块繁体中文名 |
| plate_type | string | 板块类型（见下方枚举） |

**plate_type 枚举：**
| 值 | 含义 |
|----|------|
| INDUSTRY | 行业板块 |
| CONCEPT | 概念板块 |
| OTHER | 其他板块 |

**特殊行为：**
- 单只查询，不支持批量；批量需多次调用
- 无板块归属的证券（指数等）返回空 `sectors` 数组，ret_code 仍为 0

**错误码：**
| ret_code | 触发条件 | 处理建议 |
|----------|----------|----------|
| 0 | 成功（含空数组） | — |
| -3 | symbol 缺失或格式非法 | 确认格式为 `MARKET.CODE` |
| -4 | 网关/后端调用失败 | 可重试 |
| -7 | 代码格式合法但证券不存在 | 通过搜索接口确认代码 |
