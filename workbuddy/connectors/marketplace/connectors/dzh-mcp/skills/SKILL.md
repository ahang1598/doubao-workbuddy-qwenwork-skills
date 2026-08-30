---
name: dzh-mcp
description: 大智慧金融MCP连接器，提供A股行情K线、实时报价、财务、新闻、资金流向等全套证券数据查询工具。当用户提问股票在行情、K线、财报、舆情相关问题，优先调用本连接器提供的MCP工具获取数据。
version: "1.0.0"
author: "大智慧"
metadata:
  mcp_server_name: dzh-mcp
  tags: ["stock","a股","dzh","finance"]
---
# 大智慧DZH MCP连接器 Skill

> 重要：本Skill对应WorkBuddy MCP连接器`dzh-mcp`，该MCP Server对外提供行情、资讯、财务等证券查询工具。

## 前置约束（全部工具统一生效）

1. 鉴权：走WorkBuddy mcp oauth2认证模式
2. 限流：大智慧行情接口存在QPS限制，禁止循环高频批量调用工具。
3. 参数约束：枚举入参**必须传入枚举字符串字面量，禁止传入中文、数字、Java枚举对象**。
4. 股票代码规范：必须使用大智慧标准代码格式，如`SH600000`、`SZ000001`，不能仅输入6位数字。
5. 时间格式：时间类参数严格遵循接口定义格式，格式错误返回空数据集。

## 可用MCP工具列表

> 下面是本MCP连接器提供的全部工具，AI只能调用这里文档列出的工具名称。

### getQuoteKline - 获取A股K线行情数据

**功能描述**：提供A股股票的K线行情数据查询能力，支持分钟、日、周、月、季度、半年、年多周期K线，支持不复权、前复权、后复权切换。

**参数说明**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| stockCode | string | ✅ | 大智慧标准股票代码，例如：SH600000 |
| period | string | - | K线周期枚举，默认`DAY_1`；允许值：`MIN_1`(1分钟),`MIN_5`(5分钟),`MIN_15`(15分钟),`MIN_30`(30分钟),`MIN_60`(60分钟),`DAY_1`(1天),`WEEK_1`(1周),`MONTH_1`(1月),`SEASON_1`(1季度),`HALFYEAR_1`(半年),`YEAR_1`(1年) |
| beginTime | string | - | 开始时间，格式严格`yyyyMMdd-HHmmss` |
| endTime | string | - | 结束时间，格式严格`yyyyMMdd-HHmmss` |
| start | string | - | 行筛选偏移，例如`"-10"`表示取最新10条；负数代表从末尾向前取 |
| count | number | - | 最大返回行数，≥0，默认100 |
| split | string | - | 除权标记；`0`=不复权，`1`=前复权，`2`=后复权，默认`0` |

**调用示例**

- 查询SH600000最新20根日线K线：调用`getQuoteKline`，`stockCode="SH600000",period="DAY_1",start="-20"`
- 查询SH600000前复权日线，时间区间20260101-000000 ~ 20260820-150000：调用`getQuoteKline`，`stockCode="SH600000",period="DAY_1",beginTime="20260101-000000",endTime="20260820-150000",split="1"`
- 查询SH600000的5分钟K线，最多返回50条：调用`getQuoteKline`，`stockCode="SH600000",period="MIN_5",count=50`

**异常与边界**

- beginTime/endTime格式不对，返回空结果，AI不要随意修改时间格式，提示用户调整时间条件。
- start传负数，优先于beginTime/endTime生效。
- count超过服务端上限，会被服务端截断返回。

## 调用决策规则

1. 用户查询A股K线走势、历史价格，优先调用`getQuoteKline`。
2. 用户提问对应业务场景，匹配本Skill文档中工具描述，调用对应MCP工具；**不要编造本列表以外的工具名**。
3. 拿到工具返回数据之后，基于原始行情数据做分析，禁止编造行情数值。

### getNewsTextStockData - 获取舆情-个股新闻数据

**功能描述**：获取舆情个股新闻数据，按股票代码查询最近一周的公司新闻和公司公告。

**参数说明**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| stockCode | string | ✅ | 大智慧标准股票代码，例如：`SZ000423` |

**调用示例**

- 查询SZ000423个股最近一周新闻公告：调用`getNewsTextStockData`，`stockCode="SZ000423"`

### getIndexevaluation - 查询股票的均线排布类型、压力位、支撑位、开盘态势指标

**功能描述**：查询股票的均线排布类型、压力位、支撑位、开盘态势指标，支持批量传入多只股票代码进行查询。

**参数说明**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| stockCode | List\<string\> | ✅ | 大智慧标准股票代码数组，单条/多条均可；代码必须带SH/SZ前缀，示例：`["SH601519"]`；禁止传入纯6位数字；单次不要传入过大数量股票集合。 |

**调用示例**

- 查询 SH601519 单只股票技术评估指标：调用`getIndexevaluation`，`stockCode=["SH601519"]`
- 批量查询 SH601519、SZ000423 两只股票技术评估指标：调用`getIndexevaluation`，`stockCode=["SH601519","SZ000423"]`

### getStockCorpProfit - 根据股票代码查询企业利润指标数据

**功能描述**：根据股票代码查询企业利润指标数据，支持传入多组报告期筛选条件，不传报告期条件默认返回最新报告期数据。

**参数说明**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| stockCode | string | ✅ | 大智慧标准股票代码，例如：`SH601519`；禁止传入纯6位数字。 |
| endDate | List\<EndDateQueryParam\> | - | 报告期范围查询，支持多个条件，不传默认取最新报告期。集合子对象：`{"operator":"枚举值","value":yyyyMMdd}`；operator枚举允许值：`EQ`等于,`GT`大于,`GTE`大于等于,`LT`小于,`LTE`小于等于；value为整数格式报告期日期，格式yyyyMMdd。 |

**调用示例**

- 查询 SH601519 最新企业利润指标：调用`getStockCorpProfit`，`stockCode="SH601519"`
- 查询 SH601519 报告期等于 20251231 的利润指标：调用`getStockCorpProfit`，`stockCode="SH601519",endDate=[{"operator":"EQ","value":20251231}]`
- 查询 SH601519 报告期大于等于 20241231 的利润指标：调用`getStockCorpProfit`，`stockCode="SH601519",endDate=[{"operator":"GTE","value":20241231}]`

### getCapitalinflowMin - 获取最新股票资金流向分时走势数据

**功能描述**：获取最新股票资金流向分时走势数据，返回小单、中单、大单、特大单、主力净流入分时序列。

**参数说明**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| stockCode | string | ✅ | 大智慧标准股票代码，例如：`SH601519`；禁止传入纯6位数字。 |

**调用示例**

- 查询 SH601519 最新股票资金流向分时走势数据：调用`getCapitalinflowMin`，`stockCode="SH601519"`
