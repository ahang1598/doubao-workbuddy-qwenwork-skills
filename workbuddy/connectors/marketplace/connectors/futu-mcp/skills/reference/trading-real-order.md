# 真实交易 — 下单/改单/撤单/确认

## 下单

### trading_order_place — 真实下单

提交证券交易订单，支持多种订单类型和交易时段。

**参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| acc_id | string | 是 | 账户 ID（路径参数） |
| code | string | 是 | 代码格式 `交易所.代码`（如 `US.AAPL`、`SEHK.00700`、`US.AAPL250926C235000`）；多腿单（order_class=MLEG）时不填 |
| side | string | 是 | 方向：`BUY`/`SELL`/`SELL_SHORT`/`BUY_BACK` |
| order_type | string | 是 | 订单类型：`LIMIT`/`MARKET`/`AUCTION`/`AUCTION_LIMIT`/`STOP`/`STOP_LIMIT`/`MARKET_IF_TOUCHED`/`LIMIT_IF_TOUCHED` |
| qty | string | 是 | 数量（期权/期货单位为"张"） |
| price | string | 否 | 限价单价格；证券账户精度 4 位小数，期货 9 位小数，超出四舍五入 |
| aux_price | string | 否 | 触发价；STOP/STOP_LIMIT/MARKET_IF_TOUCHED/LIMIT_IF_TOUCHED 时必填；证券 3 位小数，期货 9 位小数 |
| time_in_force | string | 是 | 有效期：`DAY`(当日有效)/`GTC`(撤单前有效) |
| session | string | 否 | 交易时段（仅美股）：`RTH`/`RTH+Pre/Post-Mkt`/`OVERNIGHT`/`ALL_DAY`；市价单仅支持 RTH |
| lot_type | string | 否 | 整手/碎股（仅港股）：`ROUND`/`ODD` |
| remark | string | 否 | 备注，UTF-8 编码最大 64 字节 |
| order_class | string | 否 | 多腿单传 `MLEG` |
| multi_leg_info | object | 否 | 多腿单信息（order_class=MLEG 时必填） |

**交易所代码：** US=美股, SEHK=港交所, SGX=新加坡, SSE=上交所/沪股通, SZSE=深交所/深股通, JP=日本, KR=韩国, CA=加拿大, CME/CBOT/NYMEX/COMEX=美期货, CBOE=美期权, HKFE=港期

**成功返回：**

| 字段 | 类型 | 说明 |
|------|------|------|
| s | string | `"ok"` |
| d.order_id | string | 新订单 ID |

**失败返回：**

| 字段 | 类型 | 说明 |
|------|------|------|
| s | string | `"error"` |
| errcode | int | 错误码 |
| errmsg | string | 错误信息 |
| jump_url | string | 跳转链接 |
| need_order_confirm | bool | 是否需要二次确认（为 true 时须调用 trading_order_confirm） |
| confirm_id | string | 确认 ID（需二次确认时使用） |

**特殊行为：**
- `need_order_confirm=true` 时订单未生效，须使用 `confirm_id` 调用确认接口完成二次确认
- 市价单仅支持 `RTH` 时段

**错误码：**
| errcode | 触发条件 | 处理建议 |
|---------|----------|----------|
| -1200 | 通用错误 | 根据 errmsg 内容处理 |

---

## 改单

### trading_order_replace — 真实改单

修改已提交订单的价格、数量或条件参数。不支持 A 股改单。

**参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| acc_id | string | 是 | 账户 ID（路径参数） |
| order_id | string | 是 | 订单 ID（路径参数） |
| exchange | string | 是 | 交易所标识：US/SEHK/SGX/SSE/SZSE/JP/KR/CA/CME/CBOT/NYMEX/COMEX/CBOE/HKFE |
| qty | string | 是 | 新数量（期权/期货单位为"张"） |
| price | string | 是 | 新价格；期货精确到 9 位小数，其他证券 4 位小数，超出截断 |
| aux_price | string | 否 | 新触发价；STOP/STOP_LIMIT/MARKET_IF_TOUCHED/LIMIT_IF_TOUCHED 时必填；证券 3 位小数，期货 9 位小数 |

**成功返回：**

| 字段 | 类型 | 说明 |
|------|------|------|
| s | string | `"ok"` |

**失败返回：**

| 字段 | 类型 | 说明 |
|------|------|------|
| s | string | `"error"` |
| errcode | int | 错误码（如 `-1200`） |
| errmsg | string | 错误信息 |
| jump_url | string | 跳转链接 |
| need_order_confirm | bool | 是否需要二次确认（为 true 时须调用 trading_order_confirm） |
| confirm_id | string | 确认 ID（需二次确认时使用） |

**特殊行为：**
- 不支持 A 股改单
- `need_order_confirm=true` 时改单未生效，须使用 `confirm_id` 调用 `trading_order_confirm` 完成二次确认
- `price` 超出精度位数时截断（非四舍五入）

**错误码：**
| errcode | 触发条件 | 处理建议 |
|---------|----------|----------|
| -1200 | 通用错误 | 根据 errmsg 内容处理 |

---

## 撤单

### trading_order_cancel — 真实撤单

撤销指定的未成交或部分成交订单。

**参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| acc_id | string | 是 | 账户 ID（路径参数） |
| order_id | string | 是 | 订单 ID（路径参数） |
| exchange | string | 是 | 交易所标识（查询参数）：US/SEHK/SGX/SSE/SZSE/JP/KR/CA/CME/CBOT/NYMEX/COMEX/CBOE/HKFE |

**成功返回：**

| 字段 | 类型 | 说明 |
|------|------|------|
| s | string | `"ok"` |

**失败返回：**

| 字段 | 类型 | 说明 |
|------|------|------|
| s | string | `"error"` |
| errcode | int | 错误码（如 `-1200`） |
| errmsg | string | 错误信息 |

**特殊行为：**
- 请求无 body，参数通过路径和查询字符串传递
- 仅未成交或部分成交的订单可撤

**错误码：**
| errcode | 触发条件 | 处理建议 |
|---------|----------|----------|
| -1200 | 通用错误 | 根据 errmsg 内容处理 |

---

## 二次确认

### trading_order_confirm — 订单风控确认

当下单（trading_order_place）或改单（trading_order_replace）返回 `need_order_confirm=true` 时必须调用，完成二次确认后订单才会生效。

**参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| acc_id | string | 是 | 账户 ID（路径参数） |
| confirm_id | string | 是 | 下单/改单接口返回的确认 ID |
| exchange | string | 否 | 交易所标识 |
| confirm_operate | int | 否 | 确认操作类型 |
| batch_confirm_type | int[] | 否 | 批量确认类型列表 |
| operate_req | string | 否 | 操作请求数据（base64 编码） |
| security_type | int | 否 | 证券类型 |

**成功返回：**

| 字段 | 类型 | 说明 |
|------|------|------|
| s | string | `"ok"` |
| d.order_id | string | 确认后的订单 ID |

**失败返回：**

| 字段 | 类型 | 说明 |
|------|------|------|
| s | string | `"error"` |
| errcode | int | 错误码（如 `-1200`） |
| errmsg | string | 错误信息 |

**特殊行为：**
- `confirm_id` 仅来源于紧邻的下单/改单响应，一次性有效
- 未调用确认接口时订单不会生效

**错误码：**
| errcode | 触发条件 | 处理建议 |
|---------|----------|----------|
| -1200 | 通用错误 | 根据 errmsg 内容处理 |
