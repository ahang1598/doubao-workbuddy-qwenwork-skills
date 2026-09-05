# 基本面与研究工具参考

## quote_financials_statements — 财务报表

获取利润表/资产负债表/现金流量表/关键指标。

**支持市场：** HK、US、SH、SZ、BJ、SG、JP、AU、CA（仅有公开财报的公司类证券；指数、板块、ETF、基金、权证、期权、期货、外汇、加密货币返回 no_data）

### 请求参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| symbol | string | 是 | — | 股票代码，如 `HK.00700`、`US.AAPL` |
| statement_type | int | 否 | 1 | 报表类型（见下方枚举） |
| financial_type | int | 否 | 10 | 财务期间选择器（见下方枚举） |
| limit | int | 否 | 10 | 每页条数，范围 1~50 |
| next_key | string | 否 | — | 分页游标，首次请求留空，后续传回上页 `pagination.next_key` |
| currency_code | string | 否 | — | ISO 4217 币种代码（省略则用报表原始币种），如 `USD`/`HKD`/`CNY` |

### statement_type 枚举

| 值 | 含义 |
|----|------|
| 1 | 利润表（Income Statement） |
| 2 | 资产负债表（Balance Sheet） |
| 3 | 现金流量表（Cash Flow Statement） |
| 4 | 主要指标（Key Financial Indicators） |

### financial_type 枚举

此枚举同时用于请求入参和返回出参，部分值仅作为入参的多期选择器。

**具体期间（入参+出参均可）：**

| 值 | 含义 | 说明 |
|----|------|------|
| 1 | Q1 | 第一季度单季 |
| 2 | Q2 | 第二季度单季 |
| 3 | Q3 | 第三季度单季 |
| 4 | Q4 | 第四季度单季 |
| 5 | Q6 累计 | 中期报告（上半年累计） |
| 6 | Q9 累计 | 前三季度累计 |
| 7 | 年报 | 全年（Annual/FY） |
| 70 | 马来西亚单季 | period_text 后缀 SQ |
| 71 | 马来西亚累计季 | period_text 后缀 CQ |

**多期选择器（仅入参）：**

| 值 | 含义 | 适用接口 |
|----|------|----------|
| 0 | 自动匹配 | `revenue_breakdown`（按 date 自动匹配期类型） |
| 8 | 聚合季报 | `revenue_breakdown`（仅美股，用于区分 Q4 与 FY） |
| 9 | 全部单季 | `statements`（返回 Q1~Q4） |
| 10 | 单季+年报 | `statements`（默认值，返回 Q1~Q4 及年报） |
| 11 | 全部累计 | `statements`（返回 Q1、Q6、Q9、年报） |
| 102 | 全部累计 | `operational_efficiency`（返回 Q1、Q6、Q9、年报） |

### 返回结构

**顶层 `data`：**

| 字段 | 类型 | 说明 |
|------|------|------|
| report_list[] | array | 报表列表 |
| pagination.has_more | bool | 是否有更多数据 |
| pagination.next_key | string | 下页游标（`has_more=false` 时停止翻页） |

**report_list[] 元素：**

| 字段 | 类型 | 说明 |
|------|------|------|
| date_time | int64 | 报告期截止时间戳（**毫秒**） |
| fiscal_year | int | 财年，如 2026 |
| financial_type | int | 该报告的具体期间类型（值含义同请求参数枚举） |
| structure | int | 报表结构编号（市场×行业），见下方枚举 |
| structure_name | string | 结构名称，如 `NORMAL_HK` |
| period_text | string | 期间文本，如 `"2024/FY"`、`"2024/Q1"` |
| currency_code | string | 币种代码，如 `CNY` |
| accounting_standards | string | 会计准则，如 `IAS`（IFRS）、`US_GAAP` |
| auditor_report | string | 审计意见（可能为 null） |
| item_list[] | array | 报表科目列表 |

**item_list[] 元素：**

| 字段 | 类型 | 说明 |
|------|------|------|
| field_id | int | 科目 ID（不同 structure 下科目集不同） |
| display_name | string | 科目英文名称，如 `Total Revenue`、`Net Income` |
| value_type | string | 值类型：`amount`=金额, `percent`=百分比 |
| data | number | 科目值（金额单位为原始币种的最小单位） |
| yoy | number | 同比增长率（%） |
| qoq | number | 环比增长率（%） |

### structure（报表结构）枚举

| 值 | structure_name | 适用场景 |
|----|----------------|----------|
| 1 | NORMAL_KCB | 科创板 - 一般 |
| 2 | BANK_KCB | 科创板 - 金融 |
| 3 | NORMAL_A | A 股 - 一般 |
| 4 | BANK_A | A 股 - 金融 |
| 5 | NORMAL_HK | 港股 - 一般 |
| 6 | BANK_HK | 港股 - 银行 |
| 7 | INSURANCE_HK | 港股 - 保险 |
| 8 | NORMAL_MSTAR | 美股/新/加/澳 - 一般 |
| 9 | BANK_MSTAR | 美股/新/加/澳 - 银行 |
| 10 | INSURANCE_MSTAR | 美股/新/加/澳 - 保险 |
| 11 | NONNORMAL_MSTAR | 美股/新/加/澳 - 一般(非标) |
| 12 | NONBANK_MSTAR | 美股/新/加/澳 - 银行(非标) |
| 13 | NONINSURANCE_MSTAR | 美股/新/加/澳 - 保险(非标) |
| 14 | NORMAL_MAIN_INDEX_US | 美股主要指标 - 一般 |
| 15 | BANK_MAIN_INDEX_US | 美股主要指标 - 银行 |
| 16 | INSURANCE_MAIN_INDEX_US | 美股主要指标 - 保险 |
| 17 | NORMAL_MAIN_INDEX_MSTAR | 新/加/澳主要指标 - 一般 |
| 18 | BANK_MAIN_INDEX_MSTAR | 新/加/澳主要指标 - 银行 |
| 19 | INSURANCE_MAIN_INDEX_MSTAR | 新/加/澳主要指标 - 保险 |

### 错误码

| ret_code | 触发条件 | 处理建议 |
|----------|----------|----------|
| -3 | 参数无效（缺 symbol、statement_type 不在 [1,2,3,4]、limit>50） | 修正参数重试 |
| -7 | symbol 无法解析 | 通过搜索接口确认代码 |
| -10 | 证券有效但无该报表/期间数据 | 正常空结果，无需重试 |
| -4/-6 | 网关内部错误 | 可重试 |

---

## quote_financials_revenue_breakdown — 营收构成

获取公司按产品/行业/地区/业务的营收明细。仅返回有数据的维度。

**支持市场：** HK、US、SH、SZ、BJ、SG、CA、AU（仅权益类证券）

### 请求参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| symbol | string | 是 | — | 股票代码，如 `HK.00700` |
| date | int | 否 | 0 | 财务期间截止时间戳（**秒**），0=最新期间。可从返回的 `screen_date_list` 中选取 |
| financial_type | int | 否 | 0 | 财务期间类型：0=后端自动匹配（非美股市场用 0）；仅美股有效：7=年报, 8=累计季报（用于区分同一时间戳的 Q4 和 FY） |
| currency_code | string | 否 | — | ISO 4217 币种代码（省略则用报表原始币种） |

### 返回结构

**顶层 `data`：**

| 字段 | 类型 | 说明 |
|------|------|------|
| period | string | 当前期间文本，如 `"2025/FY"`、`"2025/H1"` |
| currency_code | string | 币种代码 |
| breakdown_list[] | array | 各维度营收拆分（仅有数据的维度会返回） |
| screen_date_list[] | array | 可选报告期下拉列表 |

**breakdown_list[] 元素：**

| 字段 | 类型 | 说明 |
|------|------|------|
| type | int | 拆分维度（见下方枚举） |
| item_list[] | array | 该维度下的各项明细 |

### 拆分维度 type 枚举

| 值 | 含义 | 典型覆盖市场 |
|----|------|-------------|
| 1 | 按产品（Product） | A 股、港股 |
| 2 | 按行业（Industry） | A 股 |
| 4 | 按地区（Region） | A 股、港股、美股/新/加/澳 |
| 8 | 按业务（Business） | 港股、美股/新/加/澳 |

**item_list[] 元素：**

| 字段 | 类型 | 说明 |
|------|------|------|
| name | string | 项目名称 |
| main_oper_income | number | 营业收入（原始币种单位） |
| ratio | number | 营收占比（%） |

**screen_date_list[] 元素：**

| 字段 | 类型 | 说明 |
|------|------|------|
| date | int | 财务期间截止时间戳（秒） |
| period_text | string | 期间文本，如 `"2025/FY"` |
| financial_type | int | 期间类型 |

### 错误码

| ret_code | 触发条件 | 处理建议 |
|----------|----------|----------|
| -3 | symbol 格式无效或 financial_type 非法 | 修正参数重试 |
| -7 | symbol 无法解析 | 通过搜索接口确认代码 |
| -10 | 证券有效但无营收拆分数据 | 确认是否为支持市场的权益类证券 |
| -5 | 网关/后端异常 | 可重试 |

---

## quote_financials_earnings_price_history — 业绩日股价表现

获取每个历史业绩披露日前后的股价序列（披露日 ±15 天共 30 个数据点），含期权隐含波动率预期及 IV Crush。

**支持市场：** HK、US、SH、SZ（仅正股；ETF、指数、权证、期权返回 no_data）

### 请求参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| symbol | string | 是 | 股票代码，如 `HK.00700`、`US.AAPL` |

### 返回结构

返回 `data.records[]`，每个业绩期间生成 **30 条记录**（`schedule_delta` 从 -15 到 +14），提供以披露日为中心的完整价格窗口。

**records[] 元素 — 业绩期间标识：**

| 字段 | 类型 | 说明 |
|------|------|------|
| fiscal_year | int | 财年 |
| financial_type | int | 业绩期间类型 |
| period_text | string | 期间文本，如 `"2025/Q4"` |
| is_current | bool | 是否为最近一期 |
| pub_trading_day | int64 | 披露对应交易日时间戳（**毫秒**） |
| pub_trading_day_str | string | 披露交易日（yyyy-MM-dd） |
| pub_time | int64 | 披露时间戳（**秒**） |
| pub_time_str | string | 披露时间（yyyy-MM-dd HH:mm:ss） |
| pub_type | int | 披露时间类型（盘前/盘后等） |

**records[] 元素 — 期权预期波动与 IV Crush：**

| 字段 | 类型 | 说明 |
|------|------|------|
| predict_vola_ratio_newest | float | 最新预期波动率（%） |
| predict_vola_ratio_highest | float | 最高预期波动率（%） |
| predict_vola_val_newest | float | 最新预期波动价格幅度 |
| predict_vola_val_highest | float | 最高预期波动价格幅度 |
| option_iv_crush | float | 业绩后 IV Crush（百分点） |
| option_strike_date_iv_crush | float | 业绩到期日 IV Crush（百分点） |

**records[] 元素 — 业绩对应交易日行情（OHLCV）：**

| 字段 | 类型 | 说明 |
|------|------|------|
| trading_day | int64 | 业绩对应交易日时间戳（**毫秒**） |
| trading_day_str | string | 交易日（yyyy-MM-dd） |
| open_price | float | 开盘价 |
| close_price | float | 收盘价 |
| highest_price | float | 最高价 |
| lowest_price | float | 最低价 |
| last_close_price | float | 前收盘价 |
| volume | int | 成交量（股） |

**records[] 元素 — 偏移日收盘价序列：**

| 字段 | 类型 | 说明 |
|------|------|------|
| schedule_delta | int | 相对披露日偏移天数（-15 到 +14，0=披露日） |
| schedule_close_price | float | 该偏移日的收盘价 |

### 错误码

| ret_code | 触发条件 | 处理建议 |
|----------|----------|----------|
| -3 | symbol 格式无效 | 修正参数重试 |
| -7 | symbol 无法解析 | 通过搜索接口确认代码 |
| -8 | 市场不在 HK/US/SH/SZ | 仅支持这四个市场的正股 |
| -10 | 证券有效但无业绩日价格数据 | 正常空结果，无需重试 |
| -6 | 网关内部错误 | 可重试 |

---

## quote_financials_earnings_price_move — 业绩日行情序列

获取多个业绩期间内以披露日为中心的日线行情序列（含 OHLCV 及期权 IV/HV），并汇总近 N 期业绩日平均涨跌。

**支持市场：** HK、US、SH、SZ、CA、AU（仅正股/ADR；期权、期货、外汇、指数返回 unsupported）

### 请求参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| symbol | string | 是 | — | 股票代码，如 `US.AAPL` |
| count | int | 否 | 10 | 返回最近 N 个业绩期间，范围 1~50 |
| overview_count | int | 否 | 8 | 用于计算均值的期间数，范围 1~50；实际取 min(overview_count, count) |

### 返回结构

**顶层 `data`：**

| 字段 | 类型 | 说明 |
|------|------|------|
| records[] | array | 各业绩期间的逐日行情记录（扁平列表，按期间+偏移日排列） |
| overview_recent_period_count | int | 实际参与概览统计的期间数 N |
| overview_avg_earnings_day_change_pct | float | 近 N 期业绩日平均涨跌幅（%），如 1.15 表示 +1.15% |

**records[] 元素：**

| 字段 | 类型 | 说明 |
|------|------|------|
| fiscal_year | int | 财年 |
| financial_type | int | 业绩期间类型 |
| period_text | string | 期间文本，如 `"2026/Q1"` |
| pub_trading_day | int | 披露日对应交易日时间戳（**秒**） |
| pub_trading_day_str | string | 披露交易日（yyyy-MM-dd） |
| pub_type | int | 披露时间类型（盘前/盘后等） |
| price_info_index | int | 披露日（day_offset=0）在该期间子序列中的索引位置 |
| day_offset | int | 相对披露日偏移天数（负=之前，0=披露日，正=之后） |
| trading_day | int | 当前行交易日时间戳（**秒**） |
| trading_day_str | string | 当前行交易日（yyyy-MM-dd） |
| open_price | float | 开盘价 |
| close_price | float | 收盘价 |
| highest_price | float | 最高价 |
| lowest_price | float | 最低价 |
| last_close_price | float | 前收盘价 |
| option_iv | float | 期权隐含波动率（%），无期权数据时为 0 |
| option_hv | float | 期权历史波动率（%），无期权数据时为 0 |
| volume | int | 成交量（股） |
| volume_precision | int | 量精度 n，实际量 = volume / 10^n（通常为 0） |

### 错误码

| ret_code | 触发条件 | 处理建议 |
|----------|----------|----------|
| 0 | 成功（含有效 symbol 但无数据时 records 为空） | — |
| -3 | 参数无效（count>50 等） | 修正参数重试 |
| -7 | symbol 无法解析 | 通过搜索接口确认代码 |
| -8 | 非权益类证券 | 仅支持正股 |
| -4/-6 | 网关内部错误 | 可重试 |

---
