# 盘口/逐笔/分时/市场状态
## quote_order_book — 买卖盘/盘口

获取股票实时买卖盘（深度），需订阅。深度档位取决于用户行情权限（LV1/LV2/LV3）和证券品类。

**参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| code | string | 是 | 股票代码，格式 `{market}.{code}`，如 `HK.00700` |
| num | int | 否 | 档位上限 1~60，省略取权限允许的最大深度 |

**返回 `data[]`：**

注意：`data` 始终为数组（即使只查询单个代码）。

| 字段 | 类型 | 说明 |
|------|------|------|
| code | string | 标的代码 |
| name | string | 英文名 |
| sc_name | string | 简体中文名 |
| tc_name | string | 繁体中文名 |
| books[] | array | 盘口数组（美股 LV3 有多个交易所，其他品类单元素） |

**books[] 元素：**

| 字段 | 类型 | 说明 |
|------|------|------|
| exchange | string | 交易所标识（美股 LV3: `NASDAQ`/`ARCA`；其他为空字符串） |
| bid_flag | int | 买盘有效标志：1=有效 / 0=无效 |
| ask_flag | int | 卖盘有效标志：1=有效 / 0=无效 |
| exchange_data_time_ms | int64 | 交易所数据生成时间（毫秒时间戳） |
| server_send_to_client_time_ms | int64 | 服务端发送到客户端的时间（毫秒时间戳） |
| order_volume_precision | int | 数量精度 n（volume 已按 10^n 缩放） |
| difference | float | 买卖价差（仅外汇 FX 返回） |
| bid_list[] | array | 买盘列表（按价格从高到低） |
| ask_list[] | array | 卖盘列表（按价格从低到高） |

**bid_list[] / ask_list[] 元素：**

| 字段 | 类型 | 说明 |
|------|------|------|
| price | double | 该档价格 |
| volume | int64 | 该档数量（需结合 order_volume_precision 还原） |
| order_count | int | 该档订单数（部分市场/权限为 0） |

**深度档位规则（由行情权限决定）：**

| 市场/品类 | LV1 | LV2 | LV3 |
|-----------|-----|-----|-----|
| 港股正股/窝轮/牛熊/界内证 | 1 档 | 10 档 | — |
| 港股期权/期货 | 1 档 | 10 档 | — |
| 美股（含 ETF） | 1 档 | 60 档（合并盘） | 每交易所 60 档（NASDAQ/ARCA） |
| 美股期权 | 1 档 | — | — |
| 美股期货 | — | 40 档 | — |
| A 股（SH/SZ） | 5 档 | — | — |
| 新加坡 | — | 40 档 | — |
| 马来西亚 | 3 档 | 5 档 | 10 档 |
| 日本 | — | 10 档 | 40 档 |
| 其他市场 | 1 档 | — | — |

**错误码：**
| ret_code | 触发条件 | 处理建议 |
|----------|----------|----------|
| 0 | 成功 | — |
| -3 | code 缺失或 num 超范围 | 修正参数重试 |
| -4 | 代码无法解析或参数组装失败 | 确认证券代码有效 |
| -6 | 网关内部错误 | 可重试 |
| -7 | 代码格式合法但证券不存在 | 通过搜索接口确认代码 |

---

## quote_rt_ticker — 逐笔成交

获取股票逐笔成交数据（最新 N 笔），需订阅。仅返回最新 N 笔，不支持时间范围过滤。

**支持市场：** HK（正股/信托/REIT/窝轮/牛熊/界内证/指数/板块/ETF/期权）、US（正股/ETF/指数）、SH/SZ（正股/ETF/指数/板块）、BJ（正股/指数）

**参数：**
| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| symbol | string | 是 | — | 股票代码，如 `HK.00700` |
| num | int | 否 | 500 | 笔数，范围 1~750 |
| period | string | 否 | 全部时段 | 时段过滤，可重复传参（如 `?period=BEFORE&period=AFTER`）：NORMAL/BEFORE/AFTER/OVERNIGHT |

**返回 `data`：**

| 字段 | 类型 | 说明 |
|------|------|------|
| code | string | 标的代码 |
| name | string | 英文名 |
| sc_name | string | 简体中文名 |
| tc_name | string | 繁体中文名 |
| last_close | float | 昨收价（用于计算涨跌） |
| volume_precision | int | 成交量精度 n（volume 已按 10^n 缩放；正股通常为 0，事件/永续合约可能 >0） |
| ticker_list[] | array | 逐笔成交列表 |

**ticker_list[] 元素：**

| 字段 | 类型 | 说明 |
|------|------|------|
| sequence | int64 | 逐笔序号（单调递增，可用于去重/增量拉取） |
| time | int64 | 成交时间（毫秒时间戳） |
| price | float | 成交价 |
| volume | int | 成交量（需结合 volume_precision 还原） |
| turnover | float | 成交额 |
| ticker_direction | string | 买卖方向（见下方枚举） |
| tick_type | string | 成交类型/撮合方式（见下方枚举） |
| period_type | string | 所在交易时段 |
| trade_type | string | 交易所成交类型（ASCII 字符，用于展示；美股如 `P`=盘前, `T`=Form-T, `U`=取消；港股/A股可能为空） |

**ticker_direction 枚举：**
| 值 | 含义 |
|----|------|
| BUY | 买入（主动买） |
| SELL | 卖出（主动卖） |
| NEUTRAL | 中性（方向不确定） |

**tick_type 枚举：**
| 值 | 含义 |
|----|------|
| UNKNOWN | 未知 |
| AUTO_MATCH | 自动对盘 |
| LATE | 迟到成交 |
| NON_AUTO_MATCH | 非自动对盘 |
| ODD_LOT | 碎股成交 |
| AUCTION | 竞价成交 |
| BULK | 大手成交 |
| OVERSEAS | 海外成交 |
| UNAUTO_MATCH_OFF | 非自动对盘（场外） |
| NON_DIRECT_OFF | 非直接（场外） |
| OVERSEAS_OFF | 海外（场外） |
| AUTO_MATCH_OFF | 自动对盘（场外） |
| BULK_OFF | 大手成交（场外） |
| LATE_OFF | 迟到成交（场外） |
| AUCTION_OFF | 竞价成交（场外） |
| ODD_LOT_OFF | 碎股成交（场外） |
| EVENING | 晚间交易 |
| ACCEPT_ELECTRONIC | 电子板接纳 |
| OUT_HOUR_CONTRACT | 收市后合约交易 |
| BANK_CHARGE | CCASS 收费 |
| ELECTRONIC | 电子交易 |
| HIGH_DENSITY | 高密度交易 |
| INTERMEDIATE_PRICE | 中间价交易 |
| AT_AUCTION | 竞价盘成交 |
| AUCTION_LIMIT | 竞价限价盘 |
| AT_AUCTION_LIMIT | 竞价限价盘成交 |
| ENHANCE_LIMIT | 增强限价盘 |
| HOT_QUOTE | 实时报价 |
| MARKET | 市价盘 |
| ROUND_LOT | 整手 |
| SPECIAL_LOT | 特别手 |
| ODD_AND_SPECIAL_LOT | 碎股及特别手 |

**错误码：**
| ret_code | 触发条件 | 处理建议 |
|----------|----------|----------|
| 0 | 成功 | — |
| -3 | symbol 格式非法、num 超范围、period 值无效 | 修正参数重试 |
| -5 | 网关/后端调用失败 | 可重试 |
| -7 | 代码格式合法但证券不存在 | 通过搜索接口确认代码 |
| >0 | 后端业务错误（无订阅/权限不足等） | 查看 ret_msg 详情 |

---

## quote_rt_data — 分时数据

获取当日分时（分钟级）数据，需订阅。仅返回当日数据，无跨日历史。

**支持市场：** HK（正股/信托/REIT/窝轮/牛熊/界内证/指数/板块/ETF/期权）、US（正股/ETF/指数）、SH/SZ（正股/ETF/指数/板块）、BJ（正股/指数）

**参数：**
| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| symbol | string | 是 | — | 股票代码，如 `HK.00700` |
| request_section | string | 否 | NORMAL | 交易时段过滤（见下方枚举） |

**request_section 枚举：**
| 值 | 含义 |
|----|------|
| NORMAL | 正常盘（默认；港股自动含暗盘） |
| FULL | 含盘前盘后（仅美股，不含夜盘） |
| PREMARKET | 美股盘前 |
| AFTERHOURS | 美股盘后 |
| HK_DARK | 港股暗盘 |
| OVERNIGHT | 美股夜盘 |

**返回 `data`：**

| 字段 | 类型 | 说明 |
|------|------|------|
| volume_precision | int | 成交量精度 n（volume 已按 10^n 缩放；正股通常为 0，事件合约可能 >0） |
| section_list[] | array | 交易时段数组 |

**section_list[] 元素：**

| 字段 | 类型 | 说明 |
|------|------|------|
| code | string | 标的代码 |
| name | string | 英文名 |
| sc_name | string | 简体中文名 |
| tc_name | string | 繁体中文名 |
| trade_section | string | 时段类型（见下方枚举） |
| last_close | float | 该段参考对比价/昨收 |
| point_list[] | array | 分钟数据点 |

**trade_section 枚举（响应）：**
| 值 | 含义 |
|----|------|
| AUCTION | 港股竞价时段 |
| MORNING | 港股上午盘 |
| AFTERNOON | 港股下午盘 |
| NIGHT | 夜盘 |
| US_PREMARKET | 美股盘前 |
| US_REGULAR | 美股正常交易时段 |
| US_AFTERHOURS | 美股盘后 |
| US_OVERNIGHT | 美股夜盘 |
| HK_DARK | 港股暗盘 |
| FUT_PART1 | 期货第一节 |
| FUT_PART2 | 期货第二节 |
| STIB_AFTERHOURS | 科创板盘后 |
| DEFAULT | 默认（通用市场） |
| REGULAR | 正常交易时段 |
| US_INDEX_OPT_REGULAR | 美股指数期权正常时段 |
| US_INDEX_OPT_GLOBAL | 美股指数期权全球时段 |
| US_INDEX_OPT_CURB | 美股指数期权 CURB 时段 |
| JP_INDEX_OPT_NIGHT | 日本指数期权夜盘 |
| JP_INDEX_OPT_REGULAR | 日本指数期权正常时段 |

**point_list[] 元素：**

| 字段 | 类型 | 说明 |
|------|------|------|
| time | int64 | 时间（毫秒时间戳） |
| open | float | 开盘价 |
| high | float | 最高价 |
| low | float | 最低价 |
| cur_price | float | 当前价（该分钟收盘价） |
| volume | int | 成交量（需除以 10^volume_precision 还原） |
| turnover | float | 成交额 |

**特殊行为：**
- 非交易日、未订阅证券或不支持品类返回空 `section_list`，ret_code 仍为 0
- `request_section=NORMAL` 时，港股自动包含暗盘数据
- `request_section=FULL` 仅美股有效，含盘前盘后但不含夜盘

**错误码：**
| ret_code | 触发条件 | 处理建议 |
|----------|----------|----------|
| 0 | 成功（含空 section_list） | — |
| -3 | symbol 缺失或 request_section 非法 | 修正参数重试 |
| -4 | 代码无法解析或参数组装失败 | 确认市场前缀有效 |
| -5 | 后端调用失败（网络/超时） | 可重试 |
| -6 | 网关响应转换失败 | 可重试 |
| >0 | 后端业务错误（无权限/风控/限流等） | 查看 ret_msg 详情 |

---

## quote_market_state — 市场状态

批量获取股票所属市场的当前交易状态（开盘/收盘/盘前/盘后/夜盘等）。市场级状态，不反映个股停牌。

**支持市场前缀：** HK、US、SH、SZ、BJ、SG、JP、CA、AU、CC（加密货币）。不支持的市场前缀返回 `market_state="NONE"`，不影响同批次其他有效代码。

**参数：**
| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| code_list | string[] | 是 | — | 股票代码列表，格式 `{market}.{code}`，最多 400 个 |
| is_contain_ba | bool | 否 | false | 是否含美股盘前盘后；为 true 时盘前/盘后开启后 trade_section 切换为下一交易日时段 |
| is_contain_overnight | bool | 否 | false | 是否含美股夜盘；为 true 时夜盘开启后 trade_section 切换为下一交易日时段 |
| is_need_crypto_multi_broker | bool | 否 | false | 是否返回加密货币多经纪商数据；为 true 时同一 market_id 按经纪商展开为多条记录 |

**返回 `data.market_state_list[]`：**

| 字段 | 类型 | 说明 |
|------|------|------|
| code | string | 标的代码（与请求对应） |
| stock_name | string | 英文名 |
| sc_name | string | 简体中文名 |
| tc_name | string | 繁体中文名 |
| market_state | string | 市场状态枚举（见下方） |
| time_date | string | 交易日期时间（北京时区 `YYYY-MM-DD HH:MM:SS`）；后端未提供时省略 |
| traded_seconds | int | 当前时段已交易秒数；后端未提供时省略 |
| total_seconds | int | 当前交易时段总秒数；后端未提供时省略 |
| trade_section[] | array | 当日交易时段切片（见下方）；后端未提供时省略 |
| broker_id | int | 经纪商 ID（仅加密货币 + `is_need_crypto_multi_broker=true`） |
| broker_ids | int[] | 该 market_id 下所有经纪商 ID（仅加密货币复合行情） |

**trade_section[] 元素：**

| 字段 | 类型 | 说明 |
|------|------|------|
| trade_section_type | int | 时段类型枚举 |
| begin_time | string | 时段开始时间（北京时区 `HH:MM:SS`） |
| end_time | string | 时段结束时间（北京时区 `HH:MM:SS`） |

**market_state 枚举（常见值）：**
| 值 | 含义 |
|----|------|
| NONE | 无状态/不支持的市场 |
| MORNING | 上午盘 |
| AFTERNOON | 下午盘 |
| REST | 午间休市 |
| PRE_MARKET_BEGIN | 盘前开始 |
| PRE_MARKET_END | 盘前结束 |
| AFTER_HOURS_BEGIN | 盘后开始 |
| AFTER_HOURS_END | 盘后结束 |
| OVERNIGHT_BEGIN | 夜盘开始 |
| OVERNIGHT_END | 夜盘结束 |
| CLOSING_AUCTION | 收盘竞价 |
| MARKET_CLOSE | 已收盘 |

**特殊行为：**
- 不支持的市场前缀（如 MY/DE/FR 等）返回 `market_state="NONE"`，不影响同批次有效代码
- 代码不含市场前缀（如 `"00700"`）触发参数错误
- `is_contain_ba` 和 `is_contain_overnight` 仅影响 US 市场条目
- 个股停牌不在此接口反映，需查看 `quote_market_snapshot` 的 `suspension` 字段

**错误码：**
| ret_code | 触发条件 | 处理建议 |
|----------|----------|----------|
| 0 | 成功 | — |
| -3 | code_list 缺失/为空/超 400/元素缺少市场前缀 | 修正请求体重试 |
| -5 | 后端业务错误 | 查看 ret_msg |
| -2/-4/-6 | 网关内部错误 | 可重试 |

---

## quote_trading_days — 交易日历

获取指定市场在 [start, end] 范围内的交易日历。非交易日（全天休市/周末/假期）自动过滤不返回。不按证券品类区分，返回整个市场级别的日历。

**支持市场：** HK / US / SH / SZ / BJ / SG / JP / CA / AU / JP_FUTURE / SG_FUTURE

**参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| market | string | 是 | 市场前缀：HK/US/SH/SZ/BJ/SG/JP/CA/AU/JP_FUTURE/SG_FUTURE |
| start | string | 是 | 起始日期（含），格式 `yyyy-MM-dd` |
| end | string | 是 | 结束日期（含），格式 `yyyy-MM-dd`；必须 >= start |

**返回 `data.trading_days[]`：**

| 字段 | 类型 | 说明 |
|------|------|------|
| time | string | 交易日期（`yyyy-MM-dd`） |
| trade_date_type | string | 交易日类型（见下方枚举） |
| trade_second | int | 当日总交易秒数；可用于识别半日交易（如港股圣诞前夕 ≈ 9000s，正常全天 = 19800s） |

**trade_date_type 枚举：**
| 值 | 含义 |
|----|------|
| WHOLE | 全日交易 |
| MORNING | 仅上午盘（半日） |

**特殊行为：**
- start 与 end 均含端点
- 非交易日自动过滤不出现在结果中
- 不按证券品类区分，同一市场内所有品种共享日历

**错误码：**
| ret_code | 触发条件 | 处理建议 |
|----------|----------|----------|
| 0 | 成功 | — |
| -3 | market/start/end 缺失；market 非法；日期格式错误；start > end | 修正参数重试 |
| -4/-6 | 网关内部错误 | 可重试 |
