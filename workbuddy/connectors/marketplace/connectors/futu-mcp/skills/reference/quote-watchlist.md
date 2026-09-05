# 自选股工具参考

## quote_user_security_group — 自选分组列表

获取用户的自选股分组列表，含系统预设分组和用户自定义分组。

**参数：**
| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| group_type | string | 否 | ALL | 分组类型过滤（区分大小写）：`ALL`=全部, `CUSTOM`=用户自定义, `SYSTEM`=系统预设 |

**返回 `data.group_list[]`：**

| 字段 | 类型 | 说明 |
|------|------|------|
| group_name | string | 分组名称；系统分组为英文（如 All/Favorites/HK/US/CN/Options 等），自定义分组为用户原始命名 |
| group_type | string | 类型：`SYSTEM` / `CUSTOM` |

**系统分组名称（最多 19 个）：** All, Favorites, HK, US, CN, HK Options, US Options, Options, Futures, Index, Bonds, Notes, Crypto, SG, JP, MY, AU, CA

**特殊行为：**
- 不含持仓/外汇/基金分组
- 隐藏分组不返回
- `group_type` 参数区分大小写，必须为大写

**错误码：**
| ret_code | 触发条件 | 处理建议 |
|----------|----------|----------|
| 0 | 成功 | — |
| -3 | group_type 值不在 [ALL, CUSTOM, SYSTEM] 内 | 修正参数重试 |
| -9 | 用户身份缺失或无效 | 确认用户身份信息 |
| -5 | 后端自选股服务调用失败 | 可重试 |

---

## quote_user_security — 自选股列表

获取指定分组内的自选股列表，含代码、名称、每手、证券类型及衍生品信息。

**参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| group_name | string | 是 | 分组名称（需 URL 编码，最多 100 字符），重名时取第一个匹配；可通过 `user_security_group` 获取 |

**返回 `data.security_list[]`：**

| 字段 | 类型 | 说明 |
|------|------|------|
| code | string | 股票代码，如 `US.AAPL` |
| name | string | 英文名 |
| sc_name | string | 简体中文名 |
| tc_name | string | 繁体中文名 |
| lot_size | int | 每手股数（期权=合约股数，期货=合约乘数） |
| stock_type | string | 证券类型：`STOCK`/`ETF`/`WARRANT`/`IDX`/`DRVT`/`FUTURE`/`FOREX`/`CRYPTO`/`BOND` 等 |
| stock_child_type | int | 证券子类型数值 |
| stock_owner | string | 标的正股代码（衍生品）；非衍生品为空字符串 |
| option_type | string | 期权方向：`ALL`(非期权)/`CALL`/`PUT` |
| strike_time | string | 期权行权日期（yyyy-MM-dd）；非期权为空字符串 |
| strike_price | double | 期权行权价；非期权为 0 |
| listing_date | string | 上市日期（yyyy-MM-dd）；无数据时为空字符串 |
| stock_id | int64 | 内部数字标识 |
| main_contract | bool | 是否期货主力连续合约；非期货始终为 false |
| last_trade_time | string | 期权/期货最后交易日期（yyyy-MM-dd）；其他类型为空字符串 |

**特殊行为：**
- 空分组返回空 `security_list` 数组，ret_code 仍为 0
- 停牌/退市证券不返回
- `group_name` 需 URL 编码

**错误码：**
| ret_code | 触发条件 | 处理建议 |
|----------|----------|----------|
| 0 | 成功（含空数组） | — |
| -3 | group_name 缺失、超 100 字符或分组不存在 | 通过 user_security_group 确认分组名 |
| -9 | 用户身份缺失或无效 | 确认用户身份信息 |
| -5 | 网关/后端内部错误 | 可重试 |

---

## quote_modify_user_security — 修改自选股

增加、删除或移出自选股。仅支持操作自定义分组，不支持系统/虚拟分组。

**参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| op | string | 是 | 操作类型：`ADD`=添加到指定分组, `DEL`=从所有分组删除, `MOVE_OUT`=从指定分组移出 |
| code_list | string[] | 是 | 股票代码列表，1~200 个，如 `["HK.00700","US.AAPL"]` |
| group_name | string | 条件必填 | 自定义分组名称（最多 100 字符）；`ADD` 和 `MOVE_OUT` 时必填，`DEL` 时可选（被忽略）；重名时取第一个匹配 |

**返回 `data`：**

| 字段 | 类型 | 说明 |
|------|------|------|
| result_code | int | 操作结果码，成功为 0 |

**特殊行为：**
- `ADD`/`MOVE_OUT` 仅支持自定义分组，对系统分组操作返回 -8
- `DEL` 与分组无关，从所有分组中删除该证券
- 所有市场和证券类型均可操作

**错误码：**
| ret_code | 触发条件 | 处理建议 |
|----------|----------|----------|
| 0 | 成功 | — |
| -3 | op 缺失/非法、code_list 为空或超 200、group_name 超 100 字符、ADD/MOVE_OUT 缺少 group_name、分组不存在、代码格式错误 | 修正参数重试 |
| -7 | code_list 中代码格式合法但证券不存在 | 通过搜索接口确认代码 |
| -8 | 对系统/虚拟分组执行增删操作 | 仅使用自定义分组 |
| -9 | 用户身份缺失或无效 | 确认用户身份信息 |
| -5 | 网关/后端内部错误 | 可重试 |
