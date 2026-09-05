# 模拟交易工具参考

## 账户查询

### sim_trade_account_list — 模拟账户列表

获取当前登录用户的模拟交易账户列表。首次调用时后端自动创建账户。

**参数：** 无（uid 通过登录态透传）

**返回 `data.accounts[]`：**

| 字段 | 类型 | 说明 |
|------|------|------|
| account_id | string | 业务账户 ID（后续模拟交易接口的 acc_id） |
| broker_id | int | 经纪商 ID |
| market_id | int | 市场 ID（见下方枚举） |
| intra_account_id | int | 内部账户短号 |
| account_type | int | 账户类型 |
| account_title | string | 账户名称（如 `"港股模拟账户"`） |

**market_id 枚举：**
| 值 | 含义 |
|----|------|
| 1 | 港股 (HK) |
| 2 | 美股 (US) |
| 3 | 美期权 (US_OPTION) |
| 9 | A 股通 (HKCC) |
| 18 | 加拿大 (CA) |


---

## 资金与持仓

### sim_trade_cash_info — 模拟账户资金

获取模拟交易账户的资金详情，含现金余额、冻结资金、购买力、持仓市值及盈亏。

**参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| acc_id | string | 是 | 模拟账户 ID（路径参数） |

**返回 `data`：**

| 字段 | 类型 | 说明 |
|------|------|------|
| balance | string | 现金结余 |
| hold | string | 冻结资金 |
| max_power_long | string | 最大购买力 |
| total_asset | string | 资产净值 |
| mv | string | 持仓市值 |
| long_mv | string | 多头市值 |
| short_mv | string | 空头市值 |
| unrealized_profit | string/null | 未实现盈亏（无数据时为 null） |
| realized_profit | string/null | 已实现盈亏（无数据时为 null） |

**特殊行为：**
- 所有金额字段均为字符串类型
- `unrealized_profit`/`realized_profit` 可能为 null（非空字符串）


---

### sim_trade_position_list — 模拟持仓

获取模拟交易账户的持仓列表（代码、方向、数量、成本、市值、盈亏）。

**参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| acc_id | string | 是 | 模拟账户 ID（路径参数） |
| market | int | 否 | 市场过滤：1=港股, 100=美股, 3=美期权, 4=A股通 |

**返回 `data.positions[]`：**

| 字段 | 类型 | 说明 |
|------|------|------|
| pstn_id | string | 持仓 ID |
| pstn_type | int | 持仓方向：0=多仓, 1=空仓 |
| market | int | 市场 |
| symbol | string | 代码（不含市场前缀，如 `00700`） |
| stock_name | string | 名称 |
| qty | string | 数量 |
| qty_avbl | string | 可用数量 |
| cost_price | string | 成本价 |
| buy_avg_price | string | 均买价 |
| cur_price | string | 现价 |
| mv | string | 市值 |
| profit | string | 盈亏额 |
| profit_ratio | string | 盈亏比（小数形式，如 `-0.0446` 表示 -4.46%） |

**特殊行为：**
- 所有金额/数量字段均为字符串类型
- `profit_ratio` 为小数形式（非百分比）
- 省略 `market` 时返回该账户全部持仓

---

## 交易容量

### sim_trade_max_buy_sell — 模拟最大可买卖

查询模拟交易中指定证券的最大可买入/可卖出数量。

**参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| acc_id | string | 是 | 模拟账户 ID（路径参数） |
| symbol | string | 是 | 代码（不含市场前缀，如 `00700`） |
| order_type | int | 是 | 订单类型：1=限价, 3=市价 |
| price | string | 否 | 价格；限价单（order_type=1）时必填 |
| order_id | string | 否 | 改单时原订单 ID |

**返回 `data`：**

| 字段 | 类型 | 说明 |
|------|------|------|
| max_cash_buy_qty_round_lot | string | 现金可买数量（整手） |
| max_margin_buy_qty_round_lot | string/null | 融资可买数量（整手）；不适用时为 null |
| max_sell_qty_round_lot | string | 可卖数量（整手） |
| max_sell_short_qty | string | 可卖空数量 |
| max_buy_back_qty | string | 需补回数量 |
| required_im_long | string/null | 期货多头初始保证金；不适用时为 null |
| required_im_short | string/null | 期货空头初始保证金；不适用时为 null |

**特殊行为：**
- 买卖数量按整手返回（符合市场最小交易单位）
- `max_margin_buy_qty_round_lot`/`required_im_long`/`required_im_short` 在融资或期货不适用时返回 null

---

## 下单

### sim_trade_input_order — 模拟下单

模拟交易下单。限价单需传 price；委托价高于市价时立即成交。港股数量须为每手倍数。

**参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| acc_id | string | 是 | 模拟账户 ID（路径参数） |
| market | int | 是 | 市场（对应账户列表的 market_id：1=港股, 100=美股, 3=美期权 等） |
| symbol | string | 是 | 代码（不含市场前缀，如 `00700`） |
| order_type | int | 是 | 订单类型：1=限价, 3=市价 |
| order_side | int | 是 | 买卖方向：1=买入, 2=卖出, 3=卖空, 4=买回 |
| qty | string | 是 | 数量 |
| price | string | 否 | 价格（限价单 order_type=1 时必填） |
| text | string | 否 | 备注（最大 100 字节） |

**返回 `data`：**

| 字段 | 类型 | 说明 |
|------|------|------|
| order_id | string | 新订单 ID |

---

## 改单

### sim_trade_modify_order — 模拟改单

修改模拟交易中未成交订单的数量或价格。仅 status=2（已提交）的订单可改单。

**参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| acc_id | string | 是 | 模拟账户 ID（路径参数） |
| order_id | string | 是 | 订单 ID（路径参数） |
| new_qty | string | 否 | 新数量（须为整手倍数） |
| new_price | string | 否 | 新价格 |

> `new_qty` 和 `new_price` 至少需提供一个。

**成功返回：**

| 字段 | 类型 | 说明 |
|------|------|------|
| ret_code | int | 返回码（0=成功） |
| ret_msg | string | 返回信息 |
| data.order_id | string | 改单后的订单 ID |

**失败返回：**

| 字段 | 类型 | 说明 |
|------|------|------|
| ret_code | int | 非零错误码 |
| ret_msg | string | 错误描述 |

**特殊行为：**
- 仅 status=2（已提交）的订单可改单
- `new_qty` 须为整手倍数（符合市场最小交易单位）
- 可仅改数量、仅改价格、或同时修改

---

## 撤单

### sim_trade_cancel_order — 模拟撤单

撤销模拟交易中未成交的订单。仅 status=2（已提交）的订单可撤单。

**参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| acc_id | string | 是 | 模拟账户 ID（路径参数） |
| order_id | string | 是 | 订单 ID（路径参数） |

> 请求体为空 JSON `{}`。

**成功返回：**

| 字段 | 类型 | 说明 |
|------|------|------|
| ret_code | int | 返回码（0=成功） |
| ret_msg | string | 返回信息 |
| data.order_id | string | 被撤销的订单 ID |

**失败返回：**

| 字段 | 类型 | 说明 |
|------|------|------|
| ret_code | int | 非零错误码 |
| ret_msg | string | 错误描述 |

**特殊行为：**
- 仅 status=2（已提交）的订单可撤单
- 请求体须为空 JSON `{}`（Content-Type: application/json）
