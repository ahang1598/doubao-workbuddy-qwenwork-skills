# 股东与公司行为工具参考

## quote_shareholders_overview — 股东概览

获取公司持股概况，含前 5 大股东、持有人类型分布及可查报告期列表。

**支持市场：** HK / US / SG / CA / AU / JP — 仅正股。A 股（SH/SZ/BJ）无数据，ETF/窝轮/期权/指数返回空数组。

**参数：**
| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| symbol | string | 是 | — | 股票代码（路径参数），如 `HK.00700` |
| period_id | int | 否 | 0 | 报告期 ID；当前后端忽略此参数，始终返回最新期，仅允许传 0 |

**返回 `data`：**

| 字段 | 类型 | 说明 |
|------|------|------|
| main_holder[] | array | 前 5 大股东 + "其他"汇总行 |
| holder_type[] | array | 按持有人类别分布 |
| holding_period[] | array | 可查询的报告期列表 |

**main_holder[] 元素：**

| 字段 | 类型 | 说明 |
|------|------|------|
| name | string | 股东名称 |
| holder_pct | double | 持股比例（%） |
| holder_id | int/null | 股东 ID；"其他"行为 null |
| static_date | int | 数据时间戳（秒） |
| static_date_str | string | 统计日期（yyyy-MM-dd） |

**holder_type[] 元素：**

| 字段 | 类型 | 说明 |
|------|------|------|
| name | string | 持有人类别名称（如"传统投资经理"、"风险资本/私募股权投资"、"个人"、"其他"） |
| holder_pct | double | 占比（%） |
| holder_id | null | 始终为 null |

**holding_period[] 元素：**

| 字段 | 类型 | 说明 |
|------|------|------|
| period_id | int | 报告期 ID（用于 holder_detail 等接口查询） |
| period_text | string | 期别文本，格式 `YYYY/QN`（如 `2026/Q2`） |

**错误码：**
| ret_code | 触发条件 | 处理建议 |
|----------|----------|----------|
| 0 | 成功（含空数组） | — |
| -3 | period_id 非法 | 修正参数重试 |
| -7 | symbol 无法解析为有效证券 | 通过搜索接口确认代码 |
| -2/-4/-6 | 网关内部错误 | 可重试 |

---

## quote_shareholders_holder_detail — 股东持仓明细

获取指定股票的股东持仓明细列表，支持按持有人类型、报告期、股东 ID 筛选和排序。

**支持市场：** HK / US / SG / JP / CA / AU — 仅正股。A 股（SH/SZ/BJ）、ETF、指数、窝轮、期权、期货不支持。

**参数：**
| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| symbol | string | 是 | — | 股票代码（路径参数），如 `HK.00700` |
| request_type | int | 否 | 1000 | 持有人类型过滤（见下方枚举） |
| period_id | int | 否 | 0 | 报告期 ID（从 overview 的 holding_period 获取），0=最新 |
| holder_id | int | 否 | 0 | 指定股东 ID；非 0 时仅返回该股东跨期持仓，sort_column 被忽略，按 period_id 升序 |
| sort_column | int | 否 | 61 | 排序字段：61=持股数量, 62=持股变动数 |
| sort_type | int | 否 | 0 | 0=降序, 1=升序 |
| limit | int | 否 | 10 | 每页条数，最大 50 |
| next_key | string | 否 | — | 分页游标；首次留空，后续传回 `pagination.next_key` |

**request_type 枚举（OwnershipType）：**
| 值 | 含义 | 值 | 含义 |
|----|------|----|------|
| 1000 | 全部（默认） | 7 | 保险公司 |
| 1 | 其他机构 | 8 | 银行/投行 |
| 2 | 传统投资经理 | 9 | 家族办公室/信托 |
| 3 | 对冲基金经理 | 10 | 主权基金 |
| 4 | VC/PE 公司 | 11 | REIT |
| 5 | 企业养老金 | 12 | 结构化融资池管理人 |
| 6 | 基金会赞助人 | 13 | 工会养老金 |
| 14 | 政府养老金 | 100 | 个人 |
| 15 | 捐赠基金 | 200 | ADR |
| 300 | 上市公司 | 400 | 私人公司 |
| 500 | 国有股 | | |

**返回 `data`：**

| 字段 | 类型 | 说明 |
|------|------|------|
| holders[] | array | 股东列表 |
| pagination.has_more | bool | 是否有更多 |
| pagination.next_key | string | 下页游标 |

**holders[] 元素：**

| 字段 | 类型 | 说明 |
|------|------|------|
| holder_id | int | 股东 ID |
| name | string | 股东名称 |
| period_text | string | 报告期（YYYY/QN 格式） |
| holder_quantity | int | 持股数量 |
| holder_quantity_change | int | 持股变动数（正=增持，负=减持） |
| holder_pct | float | 持股比例（%） |
| holder_pct_change | float | 持股比例变动（%） |
| holding_date | int64 | 持仓日期（毫秒时间戳） |
| holding_date_str | string | 持仓日期（yyyy-MM-dd） |
| close_price | float | 期间收盘价 |
| price_change_pct | float | 价格变动比例（%） |
| source_group_name | string | 数据来源（如 "Annual Report"） |
| update_time | int64 | 数据更新时间（毫秒时间戳） |
| update_time_str | string | 数据更新时间（格式化字符串） |

**特殊行为：**
- `holder_id` 非 0 时，返回该股东在所有报告期的持仓记录，`sort_column` 被忽略，结果按 period_id 升序排列
- `period_id=0` 表示最新报告期，可从 `shareholders_overview` 的 `holding_period` 获取历史期别

**错误码：**
| ret_code | 触发条件 | 处理建议 |
|----------|----------|----------|
| 0 | 成功 | — |
| -3 | 参数类型错误/枚举值非法/超范围 | 修正参数重试 |
| -7 | symbol 无法解析为有效证券 | 通过搜索接口确认代码 |
| -10 | 有效请求但无股东数据 | 确认证券和筛选条件在支持范围内 |
| -2/-4/-6 | 网关内部错误 | 可重试 |
| portfolio_ratio | double | 该股占组合比例 |

---

## quote_shareholders_holding_changes — 持仓变动

获取股东持仓增减变动记录，支持多维度排序和方向筛选。

**支持市场：** HK / US / JP / SG / CA / AU — 仅正股。A 股无数据。

**参数：**
| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| symbol | string | 是 | — | 股票代码（路径参数），如 `HK.00700` |
| holder_category | string | 否 | INSTITUTIONS | 持有人范围（见下方枚举） |
| filter_type | int | 否 | 0 | 增减方向筛选（见下方枚举） |
| sort_column | int | 否 | 1 | 排序字段（见下方枚举） |
| sort_type | int | 否 | 0 | 0=降序, 1=升序 |
| limit | int | 否 | 30 | 每页条数，最大 50 |
| next_key | string | 否 | — | 分页游标；首次留空，后续传回 `pagination.next_key` |

**holder_category 枚举：**
| 值 | 含义 |
|----|------|
| INSTITUTIONS | 机构（默认，OwnershipType 1-15） |
| INDIVIDUALS | 个人 |
| CORPORATIONS | 企业法人 |
| ALL | 全部 |

**filter_type 枚举：**
| 值 | 含义 |
|----|------|
| 0 | 不筛选 |
| 1 | 增持 |
| 2 | 减持 |
| 3 | 新建仓 |
| 4 | 清仓 |

**sort_column 枚举：**
| 值 | 含义 |
|----|------|
| 1 | 变动数量 |
| 2 | 持仓日期 |
| 3 | 变动比例 |
| 4 | 变动金额 |
| 5 | 持股比例 |

**返回 `data`：**

| 字段 | 类型 | 说明 |
|------|------|------|
| changes[] | array | 变动记录列表 |
| pagination.has_more | bool | 是否有更多 |
| pagination.next_key | string | 下页游标 |

**changes[] 元素：**

| 字段 | 类型 | 说明 |
|------|------|------|
| name | string | 股东名称 |
| holder_id | int | 股东 ID |
| holder_type | string | 股东类型（英文文本） |
| holder_type_id | int | 股东类型 ID |
| period_text | string | 报告期（YYYY/QN 格式） |
| holding_date | int64 | 持仓日期（毫秒时间戳） |
| holding_date_str | string | 持仓日期（yyyy-MM-dd） |
| share_change_num | int | 持股变动数（正=增持，负=减持） |
| share_num | int | 当前持股数量 |
| share_ratio | float | 持股比例（%） |
| share_ratio_change | float | 持股比例变动（%） |
| shares_change_price | int | 变动参考金额 |

**错误码：**
| ret_code | 触发条件 | 处理建议 |
|----------|----------|----------|
| 0 | 成功 | — |
| -3 | symbol 格式非法或参数超范围 | 修正参数重试 |
| -7 | 代码格式合法但证券不存在 | 通过搜索接口确认代码 |
| -10 | 有效证券但无持仓变动数据 | 正常空结果，无需重试 |

---

## quote_shareholders_institutional — 机构持仓统计

获取按报告期汇总的机构持仓统计，含机构数量、持股总量、环比变化及期间价格。

**支持市场：** HK / US / CA / AU / SG / JP — 仅普通股（部分 DR/REIT/ETF/基金/窝轮有覆盖）。A 股、指数、期货、期权、债券无数据。

**参数：**
| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| symbol | string | 是 | — | 股票代码（路径参数），如 `HK.00700` |
| limit | int | 否 | 10 | 每页报告期数，最大 50 |
| next_key | string | 否 | — | 分页游标；首次留空，后续传回 `pagination.next_key`；`"-1"` 表示无更多 |

**返回 `data`：**

| 字段 | 类型 | 说明 |
|------|------|------|
| holders[] | array | 各期汇总列表 |
| pagination.has_more | bool | 是否有更多 |
| pagination.next_key | string | 下页游标 |

**holders[] 元素：**

| 字段 | 类型 | 说明 |
|------|------|------|
| period_text | string | 报告期文本（YYYY/QN 格式，如 `2026/Q2`） |
| institution_quantity | int | 机构数量 |
| institution_quantity_change | int | 机构数量环比变化 |
| holder_quantity | int | 机构持股总量（股） |
| holder_quantity_change | int | 持股总量环比变化（股） |
| holder_pct | float | 机构持股比例（%） |
| holder_pct_change | float | 持股比例环比变化（%） |
| close_price | float | 期间收盘价 |
| open_price | float | 期间开盘价 |
| last_close_price | float | 期间前收盘价 |
| update_time | int64 | 数据更新时间（毫秒时间戳） |
| update_time_str | string | 数据更新时间（格式化字符串） |

**特殊行为：**
- 期别文本通过将季末时间戳推后约 45 天计算得出（落入下一季度）
- 有效证券但无机构数据时返回 ret_code=-10

**错误码：**
| ret_code | 触发条件 | 处理建议 |
|----------|----------|----------|
| 0 | 成功 | — |
| -3 | symbol 格式非法或 limit 超范围 | 修正参数重试 |
| -7 | 代码格式合法但证券不存在 | 通过搜索接口确认代码 |
| -10 | 有效证券但无机构持仓数据 | 正常空结果，无需重试 |

---

## quote_insider_holder_list — 内部人持仓

获取公司内部人（高管/董事）持仓列表及汇总统计。

**支持市场：** 主要覆盖 US；JP/AU/CA 普通股也有数据。HK/A 股/ETF 等无内部人披露制度的市场返回空列表。

**参数：**
| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| symbol | string | 是 | — | 股票代码（路径参数），如 `US.AAPL` |
| limit | int | 否 | 10 | 每页条数，最大 30 |
| next_key | string | 否 | — | 分页游标；首次留空，后续传回 `pagination.next_key` |

**返回 `data`：**

| 字段 | 类型 | 说明 |
|------|------|------|
| insiders[] | array | 内部人列表 |
| pagination.total | int | 内部人总数 |
| pagination.has_more | bool | 是否有更多 |
| pagination.next_key | string | 下页游标；`"-1"` 表示无更多 |

**insiders[] 元素：**

| 字段 | 类型 | 说明 |
|------|------|------|
| holder_id | int | 内部人 ID（用于 insider_trade_list 的 holder_id 筛选） |
| name | string | 姓名 |
| title | string | 职位/头衔 |
| holder_quantity | int | 持股数量 |
| holder_pct | float | 持股比例（%） |
| insider_total_count | int | 公司内部人总数 |
| insider_bought_count | int | 有买入记录的内部人数 |
| insider_sold_count | int | 有卖出记录的内部人数 |

**特殊行为：**
- ret_code=0 但 `insiders` 为空数组属正常情况（该证券无内部人数据）
- 港股/A 股无内部人披露制度，始终返回空列表

**错误码：**
| ret_code | 触发条件 | 处理建议 |
|----------|----------|----------|
| 0 | 成功（含空列表） | — |
| -3 | limit 超 30 或 symbol 格式非法 | 修正参数重试 |
| -7 | 代码格式合法但证券不存在 | 通过搜索接口确认代码 |

---

## quote_insider_trade_list — 内部人交易

获取公司内部人（董事/高管/5%+股东）交易记录，数据来源为美国 SEC 内部人申报（Form 3/4/144）。

**支持市场：** 主要覆盖 US 上市公司及其海外双重上市/ADR。A 股、大部分港股、ETF 等无此类披露数据，返回空数组。

**参数：**
| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| symbol | string | 是 | — | 股票代码（路径参数），如 `US.AAPL` |
| holder_id | int | 否 | 0 | 筛选指定内部人（从 insider_holder_list 获取），0=不筛选 |
| limit | int | 否 | 10 | 每页条数，最大 50 |
| next_key | string | 否 | — | 分页游标；首次留空，后续传回 `pagination.next_key` |

**返回 `data`：**

| 字段 | 类型 | 说明 |
|------|------|------|
| trades[] | array | 交易记录列表 |
| pagination.total | int | 交易记录总数 |
| pagination.has_more | bool | 是否有更多 |
| pagination.next_key | string | 下页游标；`"-1"` 表示无更多 |

**trades[] 元素：**

| 字段 | 类型 | 说明 |
|------|------|------|
| holder_id | int | 内部人 ID |
| name | string | 姓名 |
| title | string | 职位/头衔 |
| trade_shares | int | 交易股数（正=买入，负=卖出） |
| min_trade_date | int64 | 区间最早交易日期（毫秒时间戳） |
| max_trade_date | int64 | 区间最晚交易日期（毫秒时间戳） |
| min_trade_date_str | string | 最早交易日期（yyyy-MM-dd） |
| max_trade_date_str | string | 最晚交易日期（yyyy-MM-dd） |
| min_price | float | 区间最低交易价格 |
| max_price | float | 区间最高交易价格 |
| security_holder_quantity | int | 当前持股数量 |
| transaction_type | string | 交易类型（见下方枚举） |
| source_group_name | string | 数据来源申报类型（见下方枚举） |
| is_proposed_sale_of_securities | bool | 是否为拟售出证券（Form 144） |
| security_description | string | 证券描述（如 "Common Stock"） |

**transaction_type 枚举：**
| 值 | 含义 |
|----|------|
| Buy | 买入 |
| Sell | 卖出 |
| Exercise and Sell | 行权并卖出 |
| Other Acquisition | 其他获取 |

**source_group_name 枚举：**
| 值 | 含义 |
|----|------|
| Form 3 | 初始持股申报 |
| Form 4 | 持股变动申报 |
| Form 144 | 拟售出证券申报 |

**特殊行为：**
- 无内部人交易数据的证券返回空 `trades` 数组，ret_code 仍为 0
- `holder_id` 非 0 时仅返回该内部人的交易记录

**错误码：**
| ret_code | 触发条件 | 处理建议 |
|----------|----------|----------|
| 0 | 成功（含空数组） | — |
| -3 | limit 超 50 或 symbol 格式非法 | 修正参数重试 |
| -7 | 代码格式合法但证券不存在 | 通过搜索接口确认代码 |
| -2/-5/-6 | 网关/后端内部错误 | 可重试 |

---
