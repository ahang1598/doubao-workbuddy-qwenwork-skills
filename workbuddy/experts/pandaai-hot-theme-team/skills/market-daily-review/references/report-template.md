# A股每日收盘复盘（{{trade_date}}）

> 数据来源：Pandadata。报告生成时间：{{generated_at}}。除特别说明外，行情数据日为 {{trade_date}}。

## 摘要

- 指数与成交：{{index_summary}}
- 市场宽度：{{breadth_summary}}
- 热点结构：{{theme_summary}}
- 资金与异动：{{flow_summary}}

## 1. 指数概览与估值

| 指数 | 收盘点位 | 涨跌幅 | 成交额 | PE | PB | 估值分位 | 数据日 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| {{index_name}} | {{close}} | {{pct_chg}} | {{amount}} | {{pe}} | {{pb}} | {{valuation_pctile}} | {{data_date}} |

要点：
- {{index_observation}}

## 2. 市场宽度与情绪

| 指标 | 数值 | 口径 |
| --- | ---: | --- |
| 上涨家数 | {{advance_count}} | {{breadth_scope}} |
| 下跌家数 | {{decline_count}} | {{breadth_scope}} |
| 涨停家数 | {{limit_up_count}} | 说明是否含 ST、是否含一字板 |
| 跌停家数 | {{limit_down_count}} | 说明是否含 ST、是否含一字板 |
| 全市场成交额 | {{market_amount}} | {{amount_scope}} |

情绪观察：
- {{sentiment_observation}}

## 3. 行业与概念热点

### 行业表现

| 排名 | 行业 | 涨跌幅 | 代表个股 | 数据日 |
| ---: | --- | ---: | --- | --- |
| 1 | {{industry}} | {{industry_pct_chg}} | {{representative_stocks}} | {{data_date}} |

### 概念表现

| 排名 | 概念 | 涨跌幅 | 代表个股 | 数据日 |
| ---: | --- | ---: | --- | --- |
| 1 | {{concept}} | {{concept_pct_chg}} | {{representative_stocks}} | {{data_date}} |

结构观察：
- {{theme_observation}}

## 4. 龙虎榜与大宗交易

### 龙虎榜

| 股票 | 上榜原因 | 买入额 | 卖出额 | 净额 | 主要席位 | 数据日 |
| --- | --- | ---: | ---: | ---: | --- | --- |
| {{stock}} | {{reason}} | {{buy_amount}} | {{sell_amount}} | {{net_amount}} | {{seats}} | {{data_date}} |

### 大宗交易

| 股票 | 成交额 | 折溢价率 | 买方 | 卖方 | 数据日 |
| --- | ---: | ---: | --- | --- | --- |
| {{stock}} | {{block_amount}} | {{premium_discount}} | {{buyer}} | {{seller}} | {{data_date}} |

## 5. 两融与北向持股

> 两融、北向等数据可能 T+1 披露；本节必须标注实际数据日。

| 指标 | 数值 | 变化 | 数据日 |
| --- | ---: | ---: | --- |
| 融资融券余额 | {{margin_balance}} | {{margin_change}} | {{margin_data_date}} |
| 北向持股加仓前列 | {{northbound_increase}} | {{northbound_increase_change}} | {{northbound_data_date}} |
| 北向持股减仓前列 | {{northbound_decrease}} | {{northbound_decrease_change}} | {{northbound_data_date}} |

资金观察：
- {{flow_observation}}

## 6. 异动与风险提示

- 新增 ST / 摘帽 / 停复牌：{{status_changes}}
- 异常成交或连续涨跌：{{abnormal_moves}}
- 风险提示：本报告仅作市场事实归纳与结构梳理，不构成投资建议。

## 7. 数据说明

- 使用接口：{{api_list}}
- 数据截止时间：{{data_cutoff}}
- 缺失或降级数据：{{missing_data_note}}
- 统计口径：{{calculation_notes}}
