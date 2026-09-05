# 真实交易 — 账户/资金/持仓/订单/成交


### account_authorized_trd_accs — 授权账户列表

获取当前登录用户被授权操作的所有业务账户列表。

**参数：** 无

**响应信封：**
| 字段 | 类型 | 说明 |
|------|------|------|
| s | string | 状态：`"ok"`=成功, `"error"`=失败 |
| d.accounts[] | array | 授权账户列表（成功时） |
| errcode | int | 错误码（失败时） |
| errmsg | string | 错误信息（失败时） |

**accounts[] 元素：**

| 字段 | 类型 | 说明 |
|------|------|------|
| account_id | string | 业务账户 ID（后续交易接口的 acc_id） |
| security_firm | string | 券商标识（如 `FUTUINC`） |
| enable_market | int[] | 支持的交易市场列表（见下方枚举） |
| acc_type | string | 账户类型：`cash`=现金账户, `margin`=保证金账户 |
| univs_account_card_number | string | 综合账户卡号（16 位） |
| account_card_number | string | 业务账户卡号（16 位） |

**enable_market 枚举：**
| 值 | 含义 | 值 | 含义 |
|----|------|----|------|
| 1 | 港股 | 9 | 外汇 |
| 2 | 美股 | 10 | 债券 |
| 4 | A 股通 | 11 | 马来西亚 |
| 5 | 期货 | 12 | 加拿大 |
| 6 | 新加坡 | 14 | 基金 |
| 7 | 加密货币 | 15 | 日本 |
| 8 | 澳洲 | 16 | 结构性票据 |
| 17 | 事件驱动合约 | 18 | 韩国 |

**错误码：**
| errcode | 触发条件 | 处理建议 |
|---------|----------|----------|
| -1200 | 通用错误（详见 errmsg） | 根据 errmsg 内容处理 |

## 资金与持仓

### account_funds — 账户资金

获取交易账户资金详情，含购买力、总资产、现金、市值、盈亏、保证金等。

**参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| acc_id | string | 是 | 账户 ID（路径参数） |
| currency | string | 是 | 结算币种：HKD/USD/CNH/JPY/SGD/KRW；仅期货账户和综合证券账户生效，其他账户类型忽略此参数 |

**响应信封：**
| 字段 | 类型 | 说明 |
|------|------|------|
| s | string | 状态：`"ok"`=成功, `"error"`=失败 |
| d | object | 资金数据（成功时） |
| errcode | int | 错误码（失败时） |
| errmsg | string | 错误信息（失败时） |

**返回字段（d 内）：**

| 字段 | 类型 | 说明 |
|------|------|------|
| power | string | 最大购买力 |
| max_power_short | string | 做空购买力 |
| total_assets | string | 总净资产 |
| securities_assets | string | 证券资产 |
| funds_assets | string | 基金资产 |
| cash | string | 现金 |
| market_val | string | 证券市值 |
| long_mv | string | 多头市值 |
| short_mv | string | 空头市值 |
| pending_asset | string | 在途资产 |
| frozen_cash | string | 冻结资金 |
| max_withdrawal | string | 最大可提现 |
| currency | string | 查询币种 |
| available_funds | string | 可用资金 |
| unrealized_pl | string | 未实现盈亏 |
| realized_pl | string | 已实现盈亏 |
| risk_status | string | 风险状态：NONE/LEVEL1~LEVEL9 |
| initial_margin | string | 初始保证金 |
| margin_call_margin | string | 追保保证金 |
| maintenance_margin | string | 维持保证金 |
| hk_cash | string | 港币现金 |
| hk_avl_withdrawal_cash | string | 港币可提现 |
| hk_net_cash_power | string | 港币现金购买力 |
| us_cash | string | 美元现金 |
| us_avl_withdrawal_cash | string | 美元可提现 |
| us_net_cash_power | string | 美元现金购买力 |
| jp_cash | string | 日元现金 |
| jp_avl_withdrawal_cash | string | 日元可提现 |
| jp_net_cash_power | string | 日元现金购买力 |
| cn_cash | string | 人民币现金 |
| cn_avl_withdrawal_cash | string | 人民币可提现 |
| cn_net_cash_power | string | 人民币现金购买力 |
| sg_cash | string | 新加坡元现金 |
| sg_avl_withdrawal_cash | string | 新加坡元可提现 |
| sg_net_cash_power | string | 新加坡元现金购买力 |
| kr_cash | string | 韩元现金 |
| kr_avl_withdrawal_cash | string | 韩元可提现 |
| kr_net_cash_power | string | 韩元现金购买力 |

**特殊行为：**
- `currency` 参数仅对期货账户和综合证券账户生效，其他账户类型忽略
- 响应中各金额字段（除明确标注币种的 `hk_cash`/`us_cash` 等）按请求的 `currency` 进行换算
- 所有金额字段均为字符串类型（保留小数精度）

**错误码：**
| errcode | 触发条件 | 处理建议 |
|---------|----------|----------|
| -1200 | 通用错误 | 根据 errmsg 内容处理 |

---

### account_positions — 真实持仓

获取指定交易账户的持仓列表。

**参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| acc_id | string | 是 | 账户 ID（路径参数） |
| code | string | 否 | 按代码筛选；期货需传含月份的合约代码，不支持按主力合约代码过滤 |
| pl_ratio_min | string | 否 | 盈亏比例下限，传 `10` 表示 ≥+10% |
| pl_ratio_max | string | 否 | 盈亏比例上限，传 `20` 表示 ≤+20% |

**响应信封：**
| 字段 | 类型 | 说明 |
|------|------|------|
| s | string | 状态：`"ok"`=成功, `"error"`=失败 |
| d | array | 持仓列表（成功时） |
| errcode | int | 错误码（失败时） |
| errmsg | string | 错误信息（失败时） |

**d[] 元素：**

| 字段 | 类型 | 说明 |
|------|------|------|
| position_side | string | 持仓方向：`NONE`(未知)/`LONG`(多头,默认)/`SHORT`(空头) |
| code | string | 标的代码 |
| stock_name | string | 标的名称 |
| qty | string | 持仓数量 |
| can_sell_qty | string | 可卖数量 |
| currency | string | 交易币种 |
| nominal_price | string | 市价 |
| cost_price | string | 摊薄成本（证券账户）/ 平均开仓价（期货账户） |
| cost_price_valid | bool | 成本价是否有效 |
| market_val | string | 市值 |
| pl_ratio | string | 盈亏比例 |
| pl_ratio_valid | bool | 盈亏比例是否有效 |
| pl_val | string | 盈亏金额 |
| pl_val_valid | bool | 盈亏金额是否有效 |
| today_pl_val | string | 今日盈亏 |
| today_trd_val | string | 今日成交额 |
| today_buy_qty | string | 今日买入总量 |
| today_buy_val | string | 今日买入总额 |
| today_sell_qty | string | 今日卖出总量 |
| today_sell_val | string | 今日卖出总额 |
| unrealized_pl | string | 未实现盈亏 |
| realized_pl | string | 已实现盈亏 |

**特殊行为：**
- 省略 `code` 时返回全部持仓
- 所有金额字段均为字符串类型
- 有效性标志位（`*_valid`）为 false 时对应数值不可信

**错误码：**
| errcode | 触发条件 | 处理建议 |
|---------|----------|----------|
| -1200 | 通用错误 | 根据 errmsg 内容处理 |

---

## 订单查询

### account_orders_active — 当前活跃订单

获取指定账户的未完成订单列表。未完成订单包含：任何未完结订单，以及过去 24 小时内成交或撤销的订单。

**参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| acc_id | string | 是 | 账户 ID（路径参数） |
| trd_market | string | 是 | 交易市场：HK/US/HKCC/SG/CA/FUTURES/JP/KR |
| page_flag | string | 是 | 分页游标；首次传空字符串，后续传服务端返回的 `page_flag` |
| page_size | int | 否 | 每页条数，默认 50，范围 10~100 |

**响应信封：**
| 字段 | 类型 | 说明 |
|------|------|------|
| s | string | 状态：`"ok"`=成功, `"error"`=失败 |
| d | object | 数据（成功时） |
| errcode | int | 错误码（失败时） |
| errmsg | string | 错误信息（失败时） |

**d 内字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| orders[] | array | 订单列表（默认 50 条，按时间倒序） |
| page_flag | string | 下页分页游标 |
| completed | bool | `true` 时所有订单已返回完毕，停止翻页 |

**orders[] 元素：**

| 字段 | 类型 | 说明 |
|------|------|------|
| order_id | string | 订单 ID |
| code | string | 证券代码（含市场前缀，如 `US.AAPL`） |
| stock_name | string | 证券名称 |
| security_type | string | 证券类型（如 `STOCK`） |
| side | string | 方向：BUY/SELL/SELL_SHORT/BUY_BACK |
| order_type | string | 订单类型：LIMIT/MARKET/STOP/STOP_LIMIT 等 |
| order_status | string | 订单状态（如 `FILLED_ALL`/`CANCELLED`/`PENDING` 等） |
| qty | string | 委托数量 |
| price | string | 委托价格 |
| aux_price | string | 辅助价格（如触发价） |
| dealt_qty | string | 已成交数量 |
| dealt_avg_price | string | 成交均价 |
| currency | string | 币种 |
| time_in_force | string | 有效期：DAY/GTC |
| session | string | 交易时段（如 `RTH`） |
| create_time | int64 | 创建时间（微秒时间戳） |
| updated_time | int64 | 最后更新时间（微秒时间戳） |
| last_err_msg | string | 最近错误信息（无则为空） |
| remark | string | 备注（无则为空） |
| trail_type | string | 追踪类型（如 `NONE`） |
| trail_value | string | 追踪值 |
| trail_spread | string | 追踪价差 |

**分页行为：**
- 首次请求 `page_flag` 传空字符串
- 后续传服务端返回的 `page_flag`
- `completed=true` 时停止翻页

**错误码：**
| errcode | 触发条件 | 处理建议 |
|---------|----------|----------|
| -1200 | 通用错误 | 根据 errmsg 内容处理 |

### account_orders_history — 历史订单

获取指定账户的历史订单列表。

**参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| acc_id | string | 是 | 账户 ID（路径参数） |
| trd_market | string | 是 | 交易市场：HK/US/HKCC/SG/CA/FUTURES/JP/KR |
| page_flag | string | 是 | 分页游标；首次传空字符串，后续传服务端返回的 `page_flag` |
| start | uint64 | 否 | 创建时间起始（微秒时间戳） |
| end | uint64 | 否 | 创建时间结束（微秒时间戳），须晚于 start |
| code | string | 否 | 按代码筛选，省略返回全部 |
| page_size | int | 否 | 每页条数，默认 50，范围 10~100 |

**start/end 组合规则：**
| start | end | 行为 |
|-------|-----|------|
| >0 | >0 | 使用指定的起止时间 |
| 0 | >0 | start 自动为 end 前 90 天 |
| >0 | 0 | end 自动为 start 后 90 天 |
| 0 | 0 | 默认查询最近 90 天 |

**返回 `d`：**

| 字段 | 类型 | 说明 |
|------|------|------|
| orders[] | array | 订单列表 |
| page_flag | string | 下页分页游标 |
| completed | bool | `true` 时所有订单已返回完毕，停止翻页 |

**orders[] 元素：** 与 `account_orders_active` 返回的订单结构相同（含 order_id/code/stock_name/security_type/side/order_type/order_status/qty/price/aux_price/dealt_qty/dealt_avg_price/currency/time_in_force/session/create_time/updated_time/last_err_msg/remark/trail_type/trail_value/trail_spread）

### account_orders_detail — 订单详情

批量获取指定订单的详细信息。同一请求中所有订单必须属于同一交易所。

**参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| acc_id | string | 是 | 账户 ID（路径参数） |
| order_ids | string[] | 是 | 订单 ID 列表，最多 50 个（请求体） |
| exchange | string | 是 | 交易所标识（请求体）；同一请求中所有订单须属同一交易所 |

**返回 `d[]`：** 订单详情数组，每个元素结构与 `account_orders_active` 的 orders[] 元素相同（含 order_id/code/stock_name/security_type/side/order_type/order_status/qty/price/aux_price/dealt_qty/dealt_avg_price/currency/time_in_force/session/create_time/updated_time/last_err_msg/remark/trail_type/trail_value/trail_spread）

**错误码：**
| errcode | 触发条件 | 处理建议 |
|---------|----------|----------|
| -1200 | 通用错误 | 根据 errmsg 内容处理 |

---

## 成交记录

### account_order_fills_today — 当日成交

获取指定账户当日的成交记录列表。

**参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| acc_id | string | 是 | 账户 ID（路径参数） |
| trd_market | string | 是 | 交易市场：HK/US/HKCC/SG/CA/FUTURES/JP/KR |
| page_flag | string | 是 | 分页游标；首次传空字符串，后续传服务端返回的 `page_flag` |
| page_size | int | 否 | 每页条数，默认 50，范围 10~100 |

**返回 `d`：**

| 字段 | 类型 | 说明 |
|------|------|------|
| order_fills[] | array | 成交记录列表（默认 50 条，按时间倒序） |
| page_flag | string | 下页分页游标 |
| completed | bool | `true` 时所有记录已返回完毕，停止翻页 |

**order_fills[] 元素：**

| 字段 | 类型 | 说明 |
|------|------|------|
| deal_id | string | 成交 ID |
| order_id | string | 关联订单 ID |
| code | string | 证券代码（含市场前缀，如 `US.AAPL`） |
| stock_name | string | 证券名称 |
| trd_side | string | 交易方向（如 `BUY`/`SELL`） |
| qty | string | 成交数量 |
| price | string | 成交价格 |
| create_time | int64 | 创建时间（微秒时间戳） |
| updated_time | int64 | 更新时间（微秒时间戳） |
| counter_broker_id | int | 对手经纪商 ID |
| counter_broker_name | string | 对手经纪商名称 |
| status | string | 成交状态（如 `OK`） |

**错误码：**
| errcode | 触发条件 | 处理建议 |
|---------|----------|----------|
| -1200 | 通用错误 | 根据 errmsg 内容处理 |

### account_fills_history — 历史成交

获取指定账户的历史成交记录列表。

**参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| acc_id | string | 是 | 账户 ID（路径参数） |
| trd_market | string | 是 | 交易市场：HK/US/HKCC/SG/CA/FUTURES/JP/KR |
| page_flag | string | 是 | 分页游标；首次传空字符串，后续传服务端返回的 `page_flag` |
| start | uint64 | 否 | 更新时间起始（微秒时间戳） |
| end | uint64 | 否 | 更新时间结束（微秒时间戳），须晚于 start |
| code | string | 否 | 按代码筛选，省略返回全部 |
| page_size | int | 否 | 每页条数，默认 50，范围 10~50 |

**start/end 组合规则：**
| start | end | 行为 |
|-------|-----|------|
| >0 | >0 | 使用指定的起止时间 |
| 0 | >0 | start 自动为 end 前 90 天 |
| >0 | 0 | end 自动为 start 后 90 天 |
| 0 | 0 | 默认查询最近 90 天 |

**返回 `d`：**

| 字段 | 类型 | 说明 |
|------|------|------|
| order_fills[] | array | 成交记录列表（默认 50 条，按时间倒序） |
| page_flag | string | 下页分页游标 |
| completed | bool | `true` 时所有记录已返回完毕，停止翻页 |

**order_fills[] 元素：** 与 `account_order_fills_today` 的 order_fills[] 元素结构相同（含 deal_id/order_id/code/stock_name/trd_side/qty/price/create_time/updated_time/counter_broker_id/counter_broker_name/status）

**错误码：**
| errcode | 触发条件 | 处理建议 |
|---------|----------|----------|
| -1200 | 通用错误 | 根据 errmsg 内容处理 |

---

## 交易容量

### account_trading_info — 最大可买卖

查询指定账户的最大可买入/可卖出数量，或查询指定订单的最大可改数量。

**参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| acc_id | string | 是 | 账户 ID（路径参数） |
| code | string | 是 | 代码，格式 `交易所.代码`（如 `US.AAPL`、`SEHK.00700`） |
| order_type | string | 是 | 订单类型：LIMIT/MARKET/AUCTION/AUCTION_LIMIT/STOP/STOP_LIMIT/MARKET_IF_TOUCHED/LIMIT_IF_TOUCHED |
| price | string | 否 | 参考价格（非市价单时填写）；证券账户精度 3 位小数，期货账户精度 9 位小数，超出截断 |
| order_id | string | 否 | 改单时原订单 ID；留空查询新单最大数量；填写时返回该订单最大可改数量 |

**返回 `d`：**

| 字段 | 类型 | 说明 |
|------|------|------|
| max_cash_buy | string | 现金可买数量 |
| max_cash_and_margin_buy | string | 融资可买数量 |
| max_position_sell | string | 持仓可卖数量 |
| max_sell_short | string | 可做空数量 |
| max_buy_back | string | 可买回/平空仓数量 |
| long_required_im | string | 买入一份合约所需初始保证金变动 |
| short_required_im | string | 卖出一份合约所需初始保证金变动 |

**特殊行为：**
- 查询改单最大数量（传 `order_id`）需在下单后间隔 0.5 秒以上再调用
- 不传 `order_id` 时查询新单最大可用数量

**错误码：**
| errcode | 触发条件 | 处理建议 |
|---------|----------|----------|
| -1200 | 通用错误 | 根据 errmsg 内容处理 |
