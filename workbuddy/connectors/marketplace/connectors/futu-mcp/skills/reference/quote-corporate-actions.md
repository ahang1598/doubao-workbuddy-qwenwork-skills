# 公司行为（分红/回购/拆合股/复权）
## quote_corporate_actions_dividends — 分红历史

获取股票的分红派息历史记录，按时间倒序排列，最多 100 条，无分页。

**支持市场：** HK / US / SH / SZ / SG / CA / AU / JP — 主要为正股。ETF/债券/窝轮/期权/期货/指数无分红事件返回空列表。

**参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| symbol | string | 是 | 股票代码（路径参数），如 `HK.00700` |

**返回 `data`：**

| 字段 | 类型 | 说明 |
|------|------|------|
| total_dividend_count | int | 累计历史派息次数 |
| total_dividend_money | double | 累计历史派息总金额（报告币种） |
| dividend_list[] | array | 分红记录列表（最多 100 条） |

**dividend_list[] 元素：**

| 字段 | 类型 | 可用市场 | 说明 |
|------|------|----------|------|
| fiscal_year | string | HK/A 股 | 财年 |
| statement | string | 全部 | 分红方案描述文本（如 `"Cash Dividend: 5.30000 HKD Per Share"`） |
| dividend_per_share | double | HK/US | 每股现金股息（报告币种） |
| currency | string | HK/US | 股息币种（如 `HKD`、`USD`） |
| payout_ratio | double | A 股 | 派息率（%） |
| dividend_type | string | 晨星市场(SG/CA/AU/JP)/ETF | 分红类型 |
| process | string | HK/A 股 | 方案进度状态（见下方枚举） |
| ex_date | string | 全部 | 除权除息日（yyyy/MM/dd） |
| record_date | string | 全部 | 股权登记日 |
| dividend_payable_date | string | 全部 | 派息日 |
| pub_date | string | 全部 | 公告日 |

**process 枚举：**
| 值 | 含义 |
|----|------|
| Implementation | 已实施 |
| Plan | 预案 |

**各市场字段差异：**
| 字段 | HK | US | A 股(SH/SZ) | 晨星市场(SG/CA/AU/JP) |
|------|----|----|-------------|------------------------|
| fiscal_year | 有 | 无 | 有 | 无 |
| dividend_per_share | 有 | 有 | 无 | 无 |
| currency | 有 | 有 | 无 | 无 |
| payout_ratio | 无 | 无 | 有 | 无 |
| dividend_type | 无 | 无 | 无 | 有 |
| process | 有 | 无 | 有 | 无 |

**错误码：**
| ret_code | 触发条件 | 处理建议 |
|----------|----------|----------|
| 0 | 成功（含空列表） | — |
| -3 | symbol 格式非法 | 修正参数重试 |
| -7 | 代码格式合法但证券不存在 | 通过搜索接口确认代码 |
| -2/-4/-6 | 网关内部错误 | 可重试 |

---

## quote_corporate_actions_buybacks — 回购记录

获取公司股份回购历史记录。根据 symbol 所属市场返回港股或 A 股数据。

**支持市场：** HK / SH / SZ — 仅普通股。美股及其他市场返回成功但列表为空。ETF/期权/窝轮等无回购数据。

**参数：**
| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| symbol | string | 是 | — | 股票代码（路径参数），如 `HK.00700` |
| limit | int | 否 | 10 | 每页条数，最大 50 |
| next_key | string | 否 | — | 分页游标；首次留空，后续传回 `pagination.next_key` |

**返回 `data`：**

| 字段 | 类型 | 说明 |
|------|------|------|
| hk_buy_back_list[] | array/null | 港股回购记录列表（symbol 为港股时填充，否则为 null） |
| a_buy_back_list[] | array/null | A 股回购记录列表（symbol 为 A 股时填充，否则为 null） |

**分页（与 data 同级）：**

| 字段 | 类型 | 说明 |
|------|------|------|
| pagination.has_more | bool | 是否有更多 |
| pagination.next_key | string | 下页游标 |

**hk_buy_back_list[] 元素（港股）：**

| 字段 | 类型 | 说明 |
|------|------|------|
| publ_date | int64 | 公告日期（毫秒时间戳） |
| publ_date_str | string | 公告日期（yyyy-MM-dd） |
| end_date | int64 | 回购结束日期（毫秒时间戳） |
| end_date_str | string | 回购结束日期（yyyy-MM-dd） |
| buy_back_money | double | 回购金额（币种见 currency 字段） |
| currency | string | 币种（如 `HKD`） |
| buy_back_sum | int | 回购股数 |
| percentage | double | 占总股本比例（%） |
| high_price | double | 最高回购价 |
| low_price | double | 最低回购价 |
| cumulative_sum | int | 年初至今累计回购股数 |
| cumulative_percentage | double | 年初至今累计占总股本比例（%） |
| share_type | string | 股份类别（如 `"Ordinary shares"`） |

**a_buy_back_list[] 元素（A 股）：**

| 字段 | 类型 | 说明 |
|------|------|------|
| advance_date | int64 | 预案公告日期（毫秒时间戳） |
| advance_date_str | string | 预案公告日期（yyyy-MM-dd） |
| start_date | int64 | 回购期间起始日期（毫秒时间戳） |
| start_date_str | string | 回购期间起始日期（yyyy-MM-dd） |
| end_date | int64 | 回购期间截止日期（毫秒时间戳） |
| end_date_str | string | 回购期间截止日期（yyyy-MM-dd） |
| event_proce_desc | string | 事件进展描述 |
| buy_back_mode | string | 回购方式 |
| buy_back_sum | int | 本次回购股数 |
| buy_back_money | double | 回购金额（CNY） |
| percentage | double | 占总股本比例（%） |
| value_floor | double | 计划回购资金总额下限 |
| value_ceiling | double | 计划回购资金总额上限 |
| price_floor | double | 计划回购价格下限 |
| price_ceiling | double | 计划回购价格上限 |

**特殊行为：**
- 根据 symbol 所属市场决定填充 `hk_buy_back_list` 还是 `a_buy_back_list`，另一个为 null
- ret_code=0 不保证有数据，有效代码无回购历史时返回空/null 列表

**错误码：**
| ret_code | 触发条件 | 处理建议 |
|----------|----------|----------|
| 0 | 成功（含空列表） | — |
| -3 | limit 超 50 或 symbol 格式非法 | 修正参数重试 |
| -7 | 代码格式合法但证券不存在 | 通过搜索接口确认代码 |
| -5/-6 | 网关/后端内部错误 | 可重试 |

---

## quote_corporate_actions_stock_splits — 拆合股

获取港股详细的拆合股事件记录（拆股/并股/先并后拆/先拆后并）。

**支持市场：** 仅 HK 普通股。其他市场返回空 `split_list`。

**参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| symbol | string | 是 | 股票代码（路径参数），如 `HK.00700` |

**返回 `data.split_list[]`：**

| 字段 | 类型 | 说明 |
|------|------|------|
| dir_deci_pub_date | int64 | 董事会决议公告日期（秒时间戳） |
| dir_deci_pub_date_str | string | 董事会决议公告日期（yyyy-MM-dd） |
| reform_type | string | 变动类型（见下方枚举） |
| rate | string | 拆合比例，箭头记法（如 `1→5` 表示 1 股变 5 股） |
| ex_date | int64 | 除权生效日期（秒时间戳） |
| ex_date_str | string | 除权生效日期（yyyy-MM-dd） |
| sm_deci_date | int64 | 股东大会决议日期（秒时间戳） |
| sm_deci_date_str | string | 股东大会决议日期（yyyy-MM-dd） |
| scheme_statement | string | 方案描述文本 |
| new_par_value | float | 新面值（报告币种） |
| temp_share_code | string | 临时证券代码 |
| temp_share_abbr_name | string | 临时证券简称 |
| new_trade_unit | int | 新每手股数 |
| shares_after_effect | float | 生效后总股本 |
| event_status | string | 事件状态（如 `"Plan Implementation"`） |

**reform_type 枚举：**
| 值 | 含义 |
|----|------|
| SPLIT | 拆股 |
| CONSOLIDATION | 并股 |
| CONSOLIDATION_THEN_SPLIT | 先并后拆 |
| SPLIT_THEN_CONSOLIDATION | 先拆后并 |

**特殊行为：**
- 时间戳为秒级（非毫秒）
- ret_code=0 但无拆合股事件时返回空 `split_list` 数组

**错误码：**
| ret_code | 触发条件 | 处理建议 |
|----------|----------|----------|
| 0 | 成功（含空列表） | — |
| -3 | symbol 格式非法 | 修正参数重试 |
| -7 | 代码格式合法但证券不存在 | 通过搜索接口确认代码 |
| -2/-4/-6 | 网关内部错误 | 可重试 |

---

## quote_corporate_actions_rehab — 复权因子

获取除权除息事件明细及复权因子，用于客户端 K 线价格复权、分红回溯及公司行为时间线分析。

**支持市场：** HK / US / SH / SZ / CA / AU / JP / SG — 仅正股。指数/ETF/窝轮/期权/期货/债券通常返回空数组。

**参数：**
| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| symbol | string | 是 | — | 股票代码（路径参数），如 `HK.00700` |
| divi_mode | string | 否 | include_divi | 现金股息处理模式：`exclude_divi`=不含现金股息(Yahoo/Bloomberg 惯例), `include_divi`=含现金股息(A 股/富途惯例), `compat`=兼容模式(JP 不含/非 JP 含，已弃用) |

**返回 `data.rehabs[]`：**

| 字段 | 类型 | 说明 |
|------|------|------|
| ex_div_date | string | 除权除息日（yyyy-MM-dd） |
| action_types | string[] | 当日事件类型集合（见下方枚举） |
| desc_sc | string | 事件描述（简体中文） |
| desc_tc | string | 事件描述（繁体中文） |
| desc_en | string | 事件描述（英文；部分事件可能为空） |
| forward_adj_factorA | double | 当日前复权因子 A |
| forward_adj_factorB | double | 当日前复权因子 B |
| backward_adj_factorA | double | 当日后复权因子 A |
| backward_adj_factorB | double | 当日后复权因子 B |
| cum_forward_adj_factorA | double | 累计前复权因子 A（从上市至该事件） |
| cum_forward_adj_factorB | double | 累计前复权因子 B |
| cum_backward_adj_factorA | double | 累计后复权因子 A |
| cum_backward_adj_factorB | double | 累计后复权因子 B |
| split_ratio | double | 拆股/并股比例（<1=拆股如 0.25 表示 1 拆 4，>1=并股，=1=无变化） |
| join_ratio | double | 并股比例 |
| bonus_ratio | double | 送股比例（每 base 股送 N 股） |
| bonus_base | double | 送股基数 |
| transfer_ratio | double | 转增比例 |
| transfer_base | double | 转增基数 |
| transfer_ert | double | 转增事件标识值 |
| allotment_ratio | double | 配股比例 |
| allotment_price | double | 配股价格 |
| add_base | double | 增发基数 |
| add_ert | double | 增发事件标识值 |
| dividend | double | 每股现金股息（原始币种） |
| special_dividend | double | 每股特别股息（原始币种） |
| special_dividend_base | double | 特别股息基数 |
| spin_off_ratio | double | 分拆比例 |

**action_types 枚举：**
| 值 | 含义 |
|----|------|
| SPLIT | 拆股 |
| JOIN | 并股 |
| BONUS | 送股 |
| TRANSFER | 转增 |
| ALLOTMENT | 配股 |
| ADD | 增发 |
| DIVIDEND | 现金股息 |
| SPECIAL_DIVIDEND | 特别股息 |
| SPIN_OFF | 分拆上市 |

**特殊行为：**
- 返回自上市以来全部除权除息事件，无时间范围参数
- 结果按 `ex_div_date` 升序排列
- 复权因子已按 1e-9 缩放，调用方可直接使用浮点数值，无需再做处理

**错误码：**
| ret_code | 触发条件 | 处理建议 |
|----------|----------|----------|
| 0 | 成功（含空数组） | — |
| -3 | divi_mode 值不在枚举内 | 修正参数重试 |
| -7 | symbol 无法解析为有效证券 | 通过搜索接口确认代码 |
