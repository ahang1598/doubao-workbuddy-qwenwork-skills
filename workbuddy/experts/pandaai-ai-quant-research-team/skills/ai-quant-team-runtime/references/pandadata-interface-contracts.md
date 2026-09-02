# WorkBuddy PandaData MCP 已登记接口契约

本文件只适用于 WorkBuddy 适配包。正式金融数据只能通过已连接的 `pandadata`
Connector 获取。调用顺序固定为：先 `auth_status`，再使用 `call_pandadata`
调用已登记业务方法。

当任务能映射到本文件中的方法时，禁止先调用 `search_methods` 或
`get_method_doc`。只有 Connector 明确报告方法不存在、不受支持或参数契约失效时，
才允许分别调用一次动态发现或单方法文档修复。接口返回 0 行不是动态检索条件。

日期一般使用 `YYYYMMDD`；A 股代码一般使用 `000001.SZ` / `600000.SH`。
`call_pandadata` 必须传入业务方法名及 `params` 对象，不得添加契约外参数或顶层行数限制。

## 固定任务路由

| 数据任务 | 不可跳过的最低调用顺序 |
|---|---|
| 研报或论文策略复现 | `get_last_trade_date` → `get_trade_list` → `get_stock_daily_post` → `get_adj_factor` → `get_factor` → `get_index_daily` |
| 基本面策略复现 | `get_last_trade_date` → `get_trade_list` → `get_fina_reports` → `get_stock_daily_post` → `get_index_daily` |
| 价格量价因子研究 | `get_last_trade_date` → `get_trade_list` → `get_stock_daily_post` → `get_factor` → `get_index_daily` |
| 基准或绩效补充 | `get_last_trade_date` → `get_index_daily` |

任务同时命中多行时，执行各行方法的并集。某接口只有在明确不适用并在数据调用回执中
说明事实理由时才可跳过。

## 已登记业务方法

### `get_last_trade_date`

- 用途：获取最新交易日。
- 必填参数：无。
- 可选参数：`exchange`，支持 `SH`、`HK`、`US`，默认 `SH`。
- 关键返回字段：`date`。

### `get_trade_cal`

- 用途：获取交易日历并复查空结果。
- 必填参数：无。
- 可选参数：`start_date`、`end_date`、`exchange`、`is_trading_day`、`fields`。
- 关键返回字段：`nature_date`、`exchange`、`is_trade`、`pretrade_date`、`next_trade_date`。

### `get_trade_list`

- 用途：获取指定日期的在售股票列表。
- 必填参数：`date`。
- 可选参数：`exchange`。
- 关键返回字段：`symbol`、`date`。
- 网关实测差异：`exchange="SH"` 可能仍返回沪深两市代码；需要单一交易所时按代码后缀
  继续过滤，不能把 `exchange` 当作已经生效的沪深过滤器。

### `get_stock_daily`

- 用途：获取 A 股未复权日线。
- 必填参数：`start_date`、`end_date`，区间不超过五年。
- 可选参数：`symbol`、`fields`、`indicator`、`st`。
- 关键返回字段：`date`、`symbol`、`name`、`open`、`close`、`high`、`low`、
  `volume`、`amount`、`pre_close`、`limit_up`、`limit_down`、`trade_status`。

### `get_stock_daily_post`

- 用途：获取 A 股后复权日线。
- 必填参数：`start_date`、`end_date`，区间不超过五年。
- 可选参数：`symbol`、`fields`、`indicator`、`st`。
- 关键返回字段：`date`、`symbol`、`name`、`open`、`close`、`high`、`low`、
  `volume`、`pre_close`、`limit_up`、`limit_down`、`trade_status`。

### `get_adj_factor`

- 用途：获取复权因子。
- 必填参数：无。
- 可选参数：`symbol`、`start_date`、`end_date`、`fields`。
- 关键返回字段：`symbol`、`ex_date`、`ex_cum_factor`、`ex_factor`、
  `ex_end_date`、`announcement_date`。

### `get_factor`

- 用途：获取股票或期货回测因子。
- 必填参数：`start_date`、`end_date`、`factors`。
- 可选参数：`symbol`、`type`、`index_component`。
- 关键返回字段：`date`、`symbol`、`name`、`open`、`close`、`high`、`low`、
  `volume`、`amount`、`market_cap`、`turnover`；期货还可能返回 `dominant_id`、
  `exchange`、`trading_code`、`underlying_symbol`、`open_interest`、`settlement`。

### `get_fina_reports`

- 用途：获取 A 股财务季度报告。
- 必填参数：`start_quarter`、`end_quarter`，格式为 `YYYYqN`。
- 可选参数：`symbol`、`date`、`is_latest`、`fields`。
- 关键返回字段：`symbol`、`quarter`、`if_adjusted` 及请求的财务字段。

### `get_fina_performance`

- 用途：获取 A 股财务快报。
- 必填参数：无。
- 可选参数：`symbol`、`fields`、`info_date`、`end_quarter`。
- 关键返回字段：`symbol`、`info_date`、`end_date` 及收入、利润、现金流、资产、
  股本、EPS、ROE 等请求字段。
- 网关实测差异：若 `end_quarter` 被拒绝，常规快报查询改用 `symbol`、`info_date`
  和 `fields`；严格季度范围改用 `get_fina_reports`，禁止循环试参。

### `get_index_daily`

- 用途：获取指数日线。
- 必填参数：`start_date`、`end_date`，区间不超过五年。
- 可选参数：`symbol`、`fields`。
- 关键返回字段：`symbol`、`date`、`open`、`close`、`high`、`low`、`volume`、
  `pre_close`、`amount`。

## 空数据复查协议

只有 `call_pandadata` 的真实结果为 0 行，才可启动复查，并且必须真实重试至少一次：

1. 用 `get_last_trade_date` 或 `get_trade_cal` 校验交易日，规范股票、指数和基金代码。
2. 放宽一次日期窗口；事件类可从短窗口放宽到一年，仍为空时可放宽到三年。
3. 移除一个非必填过滤条件。
4. 使用本文件登记的备用参数重试；只有明确契约错误才调用一次 `get_method_doc`。
5. 第二次仍为 0 行，才可报告“无数据”，并保留初次和复查两条调用回执。

## 强制调用回执

最终结果必须附带下表，覆盖最低路由和全部补充调用：

| 接口 | 实际参数 | 状态 | 行数 | 数据日期范围 | 关键字段 |
|---|---|---|---:|---|---|

状态只能来自真实工具结果，例如 `成功`、`复查后为空`、`权限不足` 或 `调用失败`。
没有完整回执、最低路由未完成或 `DATA_GATE` 未打开时，任务不得宣称完成。
