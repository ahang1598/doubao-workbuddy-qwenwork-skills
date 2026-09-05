# 估值/评级/公司研究
## quote_valuation_detail — 估值分析

获取 PE/PB/PS 估值趋势及历史百分位。

**参数：**
| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| symbol | string | 是 | — | 股票或指数代码 |
| valuation_type | int | 否 | 1 | 1=PE, 2=PB, 3=PS |
| interval_type | int | 否 | 3 | 时间跨度：1=3 月, 2=6 月, 3=1 年, 4=3 年, 5=2019 年 5 月至今, 6=5 年, 7=10 年, 8=2 年, 9=20 年, 10=30 年 |

**返回 `data`：**

| 字段 | 类型 | 说明 |
|------|------|------|
| valuation_type | int | 估值类型 |
| last_update_time | int64 | 最后更新时间戳（秒） |
| last_update_time_str | string | 更新时间字符串 |
| trend | object | 趋势数据 |
| market_distribution | object | 市场分布 |
| plate_distribution | object | 板块内分布（仅个股） |
| profit_growth_rate | object | 盈利增长率（仅个股） |

**trend 子对象：**

| 字段 | 类型 | 说明 |
|------|------|------|
| current_value | double | 当前估值 |
| average_value | double | 均值 |
| avg_plus_std | double | 均值+1σ |
| avg_minus_std | double | 均值-1σ |
| forward_value | double | 前瞻估值（仅个股） |
| valuation_percentile | double | 百分位 |
| historical_items[] | array | 历史数据点 |

**historical_items[] 元素：**

| 字段 | 类型 | 说明 |
|------|------|------|
| time | int64 | 时间戳 |
| time_str | string | 日期字符串 |
| value | double | 估值 |
| plate_value | double | 板块均值（仅个股） |

**market_distribution 子对象：**

| 字段 | 类型 | 说明 |
|------|------|------|
| sections[] | array | 分布区间 |
| total | int | 股票总数 |
| ranking | int | 排名 |
| average_value | double | 市场均值 |
| median_value | double | 市场中位数 |

**plate_distribution 子对象（仅个股）：**

| 字段 | 类型 | 说明 |
|------|------|------|
| plate_symbol | string | 板块代码 |
| plate_name | string | 板块名称 |
| plate_average | double | 板块均值 |
| ranking | int | 板块内排名 |
| total | int | 板块成分股数 |
| stock_items[] | array | 板块内各股估值 |

**profit_growth_rate 子对象（仅个股）：**

| 字段 | 类型 | 说明 |
|------|------|------|
| financial_ttm_multiple | double | TTM 财务倍数 |
| market_cap_multiple | double | 市值倍数 |
| year_count | int | 统计年数 |
| conclusion_detailed | string | 结论文本 |
| profit_data[] | array | 历年盈利数据 |

---

## quote_research_analyst_consensus — 分析师一致预期

获取综合评级与目标价。

**支持市场：** HK、US、CN（SH/SZ/BJ）、SG、CA、AU、JP、MY（仅有分析师覆盖的正股；无覆盖时返回空 `data: {}`）

### 请求参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| symbol | string | 是 | 股票代码，如 `HK.00700`、`US.AAPL` |

### 返回结构

| 字段 | 类型 | 说明 |
|------|------|------|
| rating | int | 综合评级：1=卖出, 2=减持, 3=持有, 4=买入, 5=强烈买入 |
| total | int | 覆盖分析师总数 |
| strong_buy | float | 强烈买入占比（%） |
| buy | float | 买入占比（%）**仅 HK/CN/SG/MY/AU/JP 返回** |
| hold | float | 持有占比（%） |
| underperform | float | 减持占比（%）**仅 HK/CN/SG/MY/AU/JP 返回** |
| sell | float | 卖出占比（%） |
| average | float | 平均目标价 |
| highest | float | 最高目标价 |
| lowest | float | 最低目标价 |
| num_of_target_analysts | int | 给出目标价的分析师数量 |
| update_time | int | 更新时间戳（秒） |
| update_time_str | string | 更新日期（yyyy-MM-dd） |

> **评级分层差异：** HK/CN/SG/MY/AU/JP 返回 5 档（strong_buy/buy/hold/underperform/sell）；US/CA 仅返回 3 档（strong_buy/hold/sell）。

### 错误码

| ret_code | 触发条件 | 处理建议 |
|----------|----------|----------|
| -3 | symbol 格式无效 | 修正参数重试 |
| -7 | symbol 无法解析 | 通过搜索接口确认代码 |
| -2/-4/-6 | 网关内部错误 | 可重试 |

---

## quote_research_rating_summary — 评级详情

按机构或分析师维度的评级汇总（含目标价、推荐日期）。

**支持市场：** 仅 US、CA（其他市场返回空列表）

### 请求参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| symbol | string | 是 | — | 股票代码，如 `US.AAPL` |
| rating_dimension_type | int | 否 | 1 | 1=按机构, 2=按分析师 |
| limit | int | 否 | 10 | 每页条数，最大 20 |
| next_key | string | 否 | — | 分页游标，首次留空；`"-1"` 表示无更多数据 |

### 返回结构

**分页：**

| 字段 | 类型 | 说明 |
|------|------|------|
| pagination.has_more | bool | 是否有下一页 |
| pagination.next_key | string | 下页游标 |
| pagination.total | int | 该维度下评级总数 |

**机构维度（`rating_dimension_type=1`）→ `data.inst_rating_summary_list[]`：**

| 字段 | 类型 | 说明 |
|------|------|------|
| institution_info.institution_uid | string | 机构唯一 ID |
| institution_info.institution_name | string | 机构名称 |
| institution_info.institution_en_name | string | 机构英文名 |
| institution_info.institution_picture_url | string | 机构 logo URL |
| institution_info.update_time | int64 | 机构信息更新时间（毫秒） |
| rating_item_list[] | array | 该机构的评级记录列表 |

**分析师维度（`rating_dimension_type=2`）→ `data.analyst_rating_summary_list[]`：**

| 字段 | 类型 | 说明 |
|------|------|------|
| analyst_info.analyst_uid | string | 分析师唯一 ID |
| analyst_info.analyst_name | string | 分析师姓名 |
| analyst_info.num_of_stars | int | 星级评分（最高 5） |
| analyst_info.success_rate | float | 成功率（%） |
| analyst_info.excess_return | float | 超额收益（%） |
| rating_item_list[] | array | 该分析师的评级记录列表 |

**rating_item_list[] 元素（两种维度通用）：**

| 字段 | 类型 | 说明 |
|------|------|------|
| rating | int | 评级：1=卖出, 2=持有, 3=买入 |
| target_price | float | 目标价 |
| recommendation_date | int64 | 推荐日期时间戳（毫秒） |
| recommendation_date_str | string | 推荐日期（ISO 格式） |
| update_time | int64 | 更新时间戳（毫秒） |
| update_time_str | string | 更新时间（ISO 格式） |

### 错误码

| ret_code | 触发条件 | 处理建议 |
|----------|----------|----------|
| -3 | symbol 格式无效、rating_dimension_type 不在 [1,2]、limit>20 | 修正参数重试 |
| -7 | symbol 无法解析 | 通过搜索接口确认代码 |
| -2/-4/-6 | 网关内部错误 | 可重试 |

---

## quote_research_morningstar_report — 晨星报告

获取晨星综合评级报告（星级、公允价值、护城河、不确定性、资本配置、财务健康度，以及分析师评述）。

**参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| symbol | string | 是 | 股票代码，如 `HK.00700`、`US.AAPL` |

**返回 `data`：**

| 字段 | 类型 | 说明 |
|------|------|------|
| rating_type | int | 评级类型：1=量化评级，2=定性评级（分析师覆盖） |
| star_rating | int | 星级评级（1~5） |
| star_update_time | int | 星级更新时间（秒级时间戳） |
| star_update_time_str | string | 星级更新日期（yyyy-MM-dd） |
| fair_value | number | 公允价值（报告币种） |
| economic_moat_label | string | 护城河标签：Wide / Narrow / None |
| economic_moat_type | int | 护城河枚举：1=Wide, 2=Narrow, 3=None |
| uncertainty_label | string | 不确定性标签：Low / Medium / High / Very High / Extreme |
| uncertainty_type | int | 不确定性枚举：1=Low, 2=Medium, 3=High, 4=Very High, 5=Extreme |
| capital_allocation_label | string | 资本配置标签：Exemplary / Standard / Poor / Not Rated |
| capital_allocation_type | int | 资本配置枚举：1=Exemplary, 2=Standard, 3=Poor, 4=Not Rated |
| financial_health_label | string | 财务健康标签：Strong / Moderate / Weak |
| financial_health_type | int | 财务健康枚举：1=Strong, 2=Moderate, 3=Weak |
| analyst_report_by_line | array<string> | 分析师署名 |
| analyst_report_update_time | int | 分析师报告更新时间（秒级时间戳） |
| analyst_report_update_time_str | string | 分析师报告更新日期 |
| fair_value_content | object | 公允价值分析文本，含 context / update_time / update_time_str |
| economic_moat_content | object | 护城河分析文本（同上结构） |
| uncertainty_content | object | 不确定性分析文本（同上结构） |
| capital_allocation_content | object | 资本配置分析文本（同上结构） |
| financial_health_content | object | 财务健康分析文本（同上结构） |
| bull_say | array<object> | 看多观点列表，每项含 context / update_time / update_time_str |
| bear_say | array<object> | 看空观点列表（同 bull_say 结构） |
| ai_analysis | object | 晨星 AI 分析，含 summary / analysis |
| analyst_note_title | object | 分析师评述标题，含 context / update_time / update_time_str |

**覆盖范围：** 仅个股有晨星评级（ETF、指数、期权、期货、外汇无数据）。已观察到覆盖的市场：HK、US、SH、SZ、AU、CA。未覆盖个股返回 ret_code=-10 (no_data)。

**错误码：**
| ret_code | 触发条件 | 处理建议 |
|----------|----------|----------|
| -3 | symbol 缺失或格式无效 | 修正代码格式重试 |
| -7 | 格式合法但无法找到该证券 | 确认代码是否存在 |
| -10 | 证券有效但无晨星覆盖 | 无报告可用，不重试 |
| -2/-4/-6 | 网关内部错误 | 可重试 |

---

## quote_company_profile — 公司概况

获取公司详情标签（概览、上市信息、关键指标等），以 name/value 标签对形式返回。ETF/REIT 会自动路由到基金数据源。

**支持市场：** HK、US、SH、SZ、BJ、AU、CA、JP、SG（权益类、ETF、REIT）。期货/期权返回 unsupported；板块/场外债券/场外基金返回 invalid_symbol。

**参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| symbol | string | 是 | 股票代码，如 `HK.00700`、`US.AAPL` |

**返回 `data.items[]`：**

| 字段 | 类型 | 说明 |
|------|------|------|
| name | string | 本地化显示标签（如 "Symbol"、"Company Name"、"Website"） |
| value | string | 标签值 |
| field_type | int | 布局类型：0=文本, 1=链接, 2=独立标题（长文本块） |
| attribute_type | int | 语义类型（稳定的机器可读 key）。ETF/REIT 路径不返回此字段 |

**attribute_type 枚举：**

| 值 | 含义 | 值 | 含义 |
|----|------|----|------|
| 1 | A 股简称 | 28 | 邮箱 |
| 2 | A 股代码 | 29 | 公司简介 |
| 3 | B 股简称 | 30 | CEO |
| 4 | B 股代码 | 31 | 证券类型 |
| 5 | H 股简称 | 32 | ADS 转换比率 |
| 6 | H 股代码 | 33 | 省份（A 股） |
| 7 | Symbol | 34 | 州（美股） |
| 8 | ISIN | 35 | 主营业务 |
| 9 | 公司名称 | 36 | 经营范围 |
| 10 | 上市日期 | 37 | 董事长 |
| 11 | 发行价 | 38 | 法定代表人 |
| 12 | 发行量 | 39 | 董事会秘书 |
| 13 | 成立日期 | 40 | 营业执照编号 |
| 14 | 上市交易所 | 41 | 会计师事务所 |
| 15 | 市场 | 42 | 证券事务代表 |
| 16 | 电话 | 43 | 法律顾问 |
| 17 | 财年终止月 | 44 | 公司类别 |
| 18 | 员工人数 | 45 | 核数师 |
| 19 | 公司地址 | 46 | 审计机构 |
| 20 | 办公地址 | 47 | 注册办事处 |
| 21 | 办公地址邮编 | 48 | 总部及主要营业地点 |
| 22 | 注册地址 | 49 | 投资者关系链接 |
| 23 | 公司网站 | 50 | 行业 |
| 24 | 城市 | 51 | 地区 |
| 25 | 国家 | 52 | 总经理 |
| 26 | 邮编 | 53 | 股份过户登记处（目前仅 AU） |
| 27 | 传真 | | |

**错误码：**
| ret_code | 触发条件 | 处理建议 |
|----------|----------|----------|
| -3 | symbol 缺失或格式无效 | 检查代码拼写和格式 |
| -7 | 无法解析为有效证券 | 确认是否为支持市场的权益/ETF 代码 |
| -8 | 不支持的品类（期货/期权） | 改为查询对应标的正股 |
| -10 | 证券有效但无公司数据 | 无需重试 |

---

## quote_company_executives — 管理层列表

获取公司高管/董事列表，含姓名、职位、性别、年龄、任职起始日期、学历、持股数及年薪。

**支持市场：** HK、US、SH、SZ、BJ、CA、AU、JP、SG（权益类、基金）。指数、外汇等返回 no_data。

**参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| symbol | string | 是 | 股票代码，如 `HK.00700`、`US.AAPL` |

**返回 `data.executives[]`：**

| 字段 | 类型 | 说明 |
|------|------|------|
| leader_name | string | 高管姓名（港股通常为中文如 `马化腾`；美股含敬称如 `Mr. Timothy D. Cook`）。用于 `executive_background` 查询时必须精确匹配此字段 |
| display_leader_name | string | 客户端显示名称 |
| position_name | string | 职位（英文），如 `Chairman of the Board, Chief Executive Officer` |
| leader_gender | string | 性别：`male` / `female` |
| leader_age | string | 年龄 |
| highest_education | string | 最高学历（英文），如 `Bachelor`、`Master`、`PhD` |
| begin_date | int64 | 任职开始时间戳（**毫秒**） |
| begin_date_str | string | 任职开始日期（yyyy-MM-dd） |
| issue_date | int64 | 信息发布时间戳（**毫秒**） |
| issue_date_str | string | 信息发布日期（yyyy-MM-dd） |
| shares | string | 持股数量 |
| annual_salary | string | 年薪金额 |
| annual_salary_currency | string | 年薪币种（ISO 4217） |

**错误码：**
| ret_code | 触发条件 | 处理建议 |
|----------|----------|----------|
| -3 | symbol 缺失或格式无效 | 检查代码格式 |
| -7 | 证券代码不存在 | 确认代码正确 |
| -10 | 证券有效但无高管数据 | 正常空结果，无需重试 |

---

## quote_company_executive_background — 高管背景

获取单个高管的详细背景传记。`leader_name` 须先从 `company_executives` 接口获取并精确匹配。

**支持市场：** HK、US（其他市场暂不支持）。仅权益类正股。

**参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| symbol | string | 是 | 股票代码，如 `HK.00700`、`US.AAPL` |
| leader_name | string | 是 | 高管姓名，必须与 `company_executives` 返回的 `leader_name` 字段完全一致（港股通常为中文如 `马化腾`；美股含敬称如 `Mr. Timothy D. Cook`）。不要传 `display_leader_name` |

**返回 `data`：**

| 字段 | 类型 | 说明 |
|------|------|------|
| brief_background | string | 高管背景传记长文本 |

**错误码：**
| ret_code | 触发条件 | 处理建议 |
|----------|----------|----------|
| -3 | 缺少 leader_name 参数 | 补充必填参数 |
| -7 | symbol 无法解析 | 通过搜索接口确认代码 |
| -10 | leader_name 不匹配或无背景数据 | 先调用 `company_executives` 获取精确的 `leader_name` |
| -4/-6 | 网关内部错误 | 可重试 |

---

## quote_company_operational_efficiency — 运营效率

获取公司历史运营效率指标（员工人数、人均营收/经营利润/净利润及同比增速），按财务期间返回。

**支持市场：** HK、US、SH、SZ、BJ、SG、JP、AU、CA（仅有公开财报的权益类证券）。非公司类证券返回 unsupported (-8)。

**参数：**
| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| symbol | string | 是 | — | 股票代码，如 `HK.00700` |
| financial_type | int | 否 | 7 | 7=年报；102=全部累计季报（返回 Q1/Q6/Q9/FY） |
| limit | int | 否 | 10 | 条数，最大 100 |
| next_key | string | 否 | — | 分页游标，首次留空；后续传回 `pagination.next_key`，`has_more=false` 时停止 |
| currency_code | string | 否 | — | ISO 4217 币种代码（省略则用最新财报币种） |

**返回 `data`：**

| 字段 | 类型 | 说明 |
|------|------|------|
| currency_code | string | 金额类指标的币种单位 |
| item_list[] | array | 各期运营效率数据 |
| pagination.has_more | bool | 是否有更多 |
| pagination.next_key | string | 下页游标 |

**item_list[] 元素：**

| 字段 | 类型 | 说明 |
|------|------|------|
| fiscal_year | int | 财年 |
| financial_type | int | 财务期间类型 |
| period_text | string | 期间文本，如 `"2025/FY"` |
| end_date | int64 | 财务期间截止时间戳（**毫秒**） |
| end_date_str | string | 截止日期（yyyy-MM-dd） |
| employee_num | int | 员工人数 |
| employee_num_yoy | double | 员工人数同比增速（%） |
| income_per_capita | double | 人均营收（报告币种） |
| income_per_capita_yoy | double | 人均营收同比增速（%） |
| profit_per_capita | double | 人均经营利润 |
| profit_per_capita_yoy | double | 人均经营利润同比增速（%） |
| net_profit_per_capita | double | 人均净利润 |
| net_profit_per_capita_yoy | double | 人均净利润同比增速（%） |

**错误码：**
| ret_code | 触发条件 | 处理建议 |
|----------|----------|----------|
| -3 | limit>100 / financial_type 不在 {7,102} / symbol 格式无效 | 修正参数重试 |
| -7 | symbol 无法解析 | 通过搜索接口确认代码 |
| -8 | 证券品类不在支持范围 | 仅对公司类权益证券调用 |
| -10 | 证券有效但无运营效率数据 | 正常空结果，无需重试 |
