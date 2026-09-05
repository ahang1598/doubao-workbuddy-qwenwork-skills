# 资金流向工具参考

## quote_capital_flow — 分时资金流向

获取当日分钟级资金净流入时序数据。

**参数：**
| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| symbol | string | 是 | — | 股票代码，如 `HK.00700` |
| section | string | 否 | NORMAL | 交易时段：NORMAL（港股自动含暗盘）/FULL/PREMARKET/AFTERHOURS |

**返回 `data`：**

| 字段 | 类型 | 说明 |
|------|------|------|
| flow_list[] | array | 数据点列表（按时间升序），无数据时为空数组 |
| last_valid_time | int64 | 最后有效数据时间（毫秒时间戳），无数据时为 null |

**flow_list[] 元素：**

| 字段 | 类型 | 说明 |
|------|------|------|
| capital_flow_item_time | int64 | 数据点时间（毫秒时间戳） |
| in_flow | double | 整体净流入（正=净流入，负=净流出，本地币种） |
| super_in_flow | double | 超大单净流入 |
| big_in_flow | double | 大单净流入 |
| mid_in_flow | double | 中单净流入 |
| sml_in_flow | double | 小单净流入 |

**关系：** `in_flow = super_in_flow + big_in_flow + mid_in_flow + sml_in_flow`

仅当日数据，非交易时段返回空列表。分时接口不返回主力净流入和涨跌幅字段。

---

## quote_capital_flow_history — 历史资金流向

获取日/周/月级别的历史资金净流入数据。

**参数：**
| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| symbol | string | 是 | — | 股票代码 |
| period_type | string | 否 | DAY | 周期：DAY/WEEK/MONTH |
| start | string | 否 | — | 起始日期 yyyy-MM-dd |
| end | string | 否 | 今天 | 结束日期 yyyy-MM-dd |
| count | int | 否 | 365 | 最大返回条数，1~1000 |

**返回 `data`：**

| 字段 | 类型 | 说明 |
|------|------|------|
| flow_list[] | array | 数据点列表（按时间升序） |

**分页：**

| 字段 | 类型 | 说明 |
|------|------|------|
| pagination.has_more | bool | 是否有更早的数据可继续翻页 |

**flow_list[] 元素：**

| 字段 | 类型 | 说明 |
|------|------|------|
| capital_flow_item_time | int64 | 时间（毫秒时间戳，按 period_type 对齐到日/周/月） |
| in_flow | double | 整体净流入（正=净流入，负=净流出） |
| main_in_flow | double | 主力净流入（超大单+大单） |
| super_in_flow | double | 超大单净流入 |
| big_in_flow | double | 大单净流入 |
| mid_in_flow | double | 中单净流入 |
| sml_in_flow | double | 小单净流入 |
| main_deal_ratio | double | 主力成交占比（如 0.123 表示 12.3%），后端未提供时省略 |
| acc_main_in_flow | double | 累计主力净流入，后端未提供时省略 |

---

## quote_capital_distribution — 资金分布

获取当日按大/中/小单的累计资金流入流出汇总快照。

**参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| symbol | string | 是 | 股票代码 |

**返回 `data`：**

| 字段 | 类型 | 说明 |
|------|------|------|
| capital_in_super | double | 超大单累计流入 |
| capital_in_big | double | 大单累计流入 |
| capital_in_mid | double | 中单累计流入 |
| capital_in_small | double | 小单累计流入 |
| capital_out_super | double | 超大单累计流出 |
| capital_out_big | double | 大单累计流出 |
| capital_out_mid | double | 中单累计流出 |
| capital_out_small | double | 小单累计流出 |
| update_time | int64 | 数据更新时间（毫秒时间戳） |

**净流入计算：** 各档净流入 = `capital_in_*` - `capital_out_*`

仅当日快照，非交易时段全部为 0。
