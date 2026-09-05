# 资讯、日历与其他工具参考

## quote_news_search — 新闻搜索

搜索文章/公告/研报。

**参数：**
| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| symbol | string | 是 | — | 搜索关键词（必填） |
| news_type | int | 否 | — | 1=文章, 2=公告, 3=研报；省略返回全部 |
| sort_type | int | 否 | — | 0=默认, 1=按浏览量, 2=按时间 |
| size | int | 否 | 10 | 结果数，1~50 |
| lang | string | 否 | — | zh-CN/zh-HK/en/ja |

**返回 `data.news_list[]`：**

| 字段 | 类型 | 说明 |
|------|------|------|
| news_id | string | 新闻 ID |
| news_type | string | 类型：POST(文章)/NOTICE(公告)/REPORT(研报) |
| title | string | 标题 |
| publish_time | int64 | 发布时间（秒时间戳） |
| url | string | 原文链接 |
| img_url | string | 配图链接（可选） |

---

## quote_community_search — 社区搜索

搜索社区帖子/话题/直播。

**参数：**
| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| symbol | string | 是 | — | 搜索关键词 |
| community_type | int | 否 | — | 1=帖子, 2=话题, 3=直播 |
| sort_type | int | 否 | — | 0=默认, 1=按热度, 2=按时间 |
| size | int | 否 | 10 | 结果数，1~50 |
| lang | string | 否 | — | zh-CN/zh-HK/en/ja |

**返回 `data.community_list[]`：**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | 内容 ID |
| community_type | string | 类型：FEED/TOPIC/LIVE |
| title | string | 标题 |
| publish_time | int64 | 发布时间（秒时间戳） |
| url | string | 链接 |
| img_url | string | 配图链接（可选） |

---

## quote_stock_feed — 个股动态

获取指定股票相关的社区帖子。

**参数：**
| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| symbol | string | 是 | — | 股票名称（如"腾讯"、"AAPL"） |
| size | int | 否 | 10 | 结果数，1~50 |

**返回 `data.feed_list[]`：**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | 帖子 ID |
| title | string | 标题 |
| publish_time | int64 | 发布时间（秒时间戳） |
| desc | string | 摘要描述 |

---

## quote_economic_calendar_hot — 热门经济数据

获取指定日期的热门/推荐经济数据列表，按重要性排序。返回当日主要经济指标（如 CPI、GDP、非农、央行利率决议等），含前值、预期值、公布值及星级重要性。

**参数：**
| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| date | string | 否 | 今天 | 查询日期，格式 `yyyyMMdd`，如 `20260618` |
| limit | int | 否 | 10 | 每页条数，范围 1~20 |
| next_key | string | 否 | — | 分页游标，首次留空；后续传回 `pagination.next_key`；值为 `"-1"` 时无更多数据 |
| timezone | string | 否 | Asia/Shanghai | 时区，如 `America/New_York` |

**返回：**

顶层 `data` 为数组（非对象），`pagination` 与 `data` 同级。

| 字段 | 类型 | 说明 |
|------|------|------|
| data[] | array | 经济数据事件列表 |
| pagination.has_more | bool | 是否有更多 |
| pagination.next_key | string | 下页游标（`"-1"` 表示无更多） |

**data[] 元素：**

| 字段 | 类型 | 说明 |
|------|------|------|
| event_text | string | 事件内容，如 `"美国至6月17日美联储利率决定(上限)"` |
| previous | string | 前值，如 `"3.75"` |
| predictive | string | 预期/一致预期值，如 `"3.75"` |
| announce | string | 公布/实际值；未公布时为空字符串 |
| star | int | 重要性星级，范围 1~5（5=最重要，如央行利率决议） |
| event_time | int64 | 事件发布时间（秒级时间戳） |
| country | string | 国家/地区，如 `"美国"`、`"日本"` |
| currency | string | 相关币种，可能为 null |
| unit | string | 数据单位，如 `"%"`、`"万人"`，可能为 null |
| unique_id | string | 唯一标识，如 `"calendar_economic:103384299"`，可能为 null |
| detail_url | string | 详情页跳转链接 |

**错误码：**
| ret_code | 触发条件 | 处理建议 |
|----------|----------|----------|
| 0 | 成功（含空列表） | 检查 data 数组长度判断是否有数据 |
| -3 | limit 超出 1~20 范围 | 修正参数重试 |
| -4 | 后端业务错误 | 可重试 |

---

## quote_economic_calendar_search — 经济日历搜索

按关键词搜索经济日历数据，支持四种类型：经济数据（CPI/GDP/非农等）、休市、经济事件（央行讲话/会议）、权益（分红/拆股）。返回分页、可按时间排序的事件列表。

**参数：**
| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| keyword | string | 是 | — | 搜索关键词，如 `CPI`、`美联储`、`GDP` |
| search_type | int | 是 | — | 搜索类型：1=经济数据, 2=休市, 3=经济事件, 4=权益(分红/拆股) |
| limit | int | 否 | 20 | 每页条数，范围 1~30 |
| next_key | string | 否 | — | 分页游标，首次留空；后续传回 `pagination.next_key` |
| time_order_type | int | 否 | 0 | 排序：0=升序(ASC), 1=降序(DESC)；**仅对 search_type=2 和 3 生效** |

**返回：**

顶层 `data` 为数组（非对象），`pagination` 与 `data` 同级。

| 字段 | 类型 | 说明 |
|------|------|------|
| data[] | array | 匹配的事件列表 |
| pagination.has_more | bool | 是否有更多 |
| pagination.next_key | string | 下页游标 |

**data[] 元素：**

| 字段 | 类型 | 说明 |
|------|------|------|
| event_text | string | 事件内容；匹配关键词用 `<em>` 标签高亮，如 `加拿大5月<em>CPI</em>月率` |
| previous | string | 前值；search_type=3 时为 null |
| predictive | string | 预期/一致预期值；search_type=3 时为 null |
| announce | string | 公布/实际值；未公布时为 null；search_type=3 时为 null |
| star | int | 重要性星级，范围 1~5 |
| event_time | int64 | 事件发布时间（秒级时间戳） |
| country | string | 国家/地区 |
| currency | string | 相关币种，可能为 null |
| unit | string | 数据单位，可能为 null |
| unique_id | string | 唯一标识，如 `"calendar_economic:155416319"`、`"calendar_event:83109"` |
| detail_url | string | 详情链接；search_type=3 时可能为 null |

**各 search_type 特殊说明：**
- **search_type=1（经济数据）：** `previous`/`predictive` 通常有值；`announce` 在正式公布前为 null
- **search_type=3（经济事件）：** `previous`、`predictive`、`announce`、`detail_url` 均为 null
- **关键词高亮：** `event_text` 中每个匹配字符/词段用 `<em>` 包裹（中日韩文字为字符级高亮）

**错误码：**
| ret_code | 触发条件 | 处理建议 |
|----------|----------|----------|
| 0 | 成功（含空列表） | 检查 data 数组长度判断是否有结果 |
| -3 | 缺少 keyword 或 search_type；search_type 不在 1~4；limit 超范围 | 修正参数重试 |
| -4 | 后端业务错误 | 可重试 |

---

## quote_ipo_list_hk / _us / _cn / _sg / _my — IPO 列表

五个市场各自独立接口，返回近期可认购及即将上市的新股（不含历史 IPO）。数据来源于当前用户的主经纪商，若用户无对应市场经纪商可能返回空列表。

### 请求参数

**港股 / 美股 / 新加坡 / 马来西亚：**
| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| request_type | int | 否 | 11 | 9=认购中, 10=待上市, 11=即将上市（含认购中+待上市） |

**A 股：**
| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| request_type | int | 否 | 4 | 1=IPO 预告, 2=申购中, 3=中签公布, 4=待上市, 5=全部 |

### 返回 `data.list[]`

#### 港股 (HK)

| 字段 | 类型 | 说明 |
|------|------|------|
| code | string | 带市场前缀的代码，如 `HK.12233` |
| name | string | 英文名 |
| sc_name | string | 简体中文名 |
| tc_name | string | 繁体中文名 |
| list_time | string | 上市日期 yyyy-MM-dd；未确定为 `"--"` |
| list_timestamp | int64 | 上市时间戳（毫秒）；未确定为 0 |
| ipo_price_min | float | 招股价下限（HKD） |
| ipo_price_max | float | 招股价上限（HKD） |
| list_price | float | 最终发行价（HKD） |
| lot_size | int | 每手股数 |
| entrance_price | float | 入场费（HKD） |
| apply_start_timestamp | int64 | 认购开始时间戳（毫秒） |
| apply_end_time | string | 认购截止日期 yyyy-MM-dd |
| apply_end_timestamp | int64 | 认购截止时间戳（毫秒） |
| apply_countdown_secs | int | 认购截止倒计时（秒） |
| is_apply_started | bool | 是否已开始认购 |
| is_support_apply | bool | 是否支持认购 |
| is_subscribe_status | bool | 是否处于可认购状态 |
| apply_multiple | string | 认购倍数（超额倍率） |
| lucky_ratio | string | 一手中签率 |
| win_ratio_msg | string | 中签概率描述 |
| lucky_time | string | 公布结果日期 yyyy-MM-dd |
| lucky_timestamp | int64 | 公布结果时间戳（毫秒） |
| margin_fee_ratio | float | 融资认购利率（%） |
| margin_fee_ratio_min | float | 最低融资利率（%）；0=未提供 |
| margin_fee_ratio_max | float | 最高融资利率（%）；0=未提供 |
| margin_lever_ratio | float | 融资杠杆倍数 |
| real_margin_lever_ratio | float | 实际可用融资杠杆；0=未提供 |
| margin_rate | float | 保证金比率（4 位小数） |
| dark_trade_date | string | 暗盘交易日期；空字符串=无 |
| dark_trade_timestamp | int64 | 暗盘日期时间戳（毫秒）；0=无 |
| dark_trade_period | string | 暗盘交易时段，如 `16:15~18:30` |
| dark_trade_start_timestamp | int64 | 暗盘开始时间戳（毫秒）；0=无 |
| dark_trade_end_timestamp | int64 | 暗盘结束时间戳（毫秒）；0=无 |
| is_support_dark_trade | bool | 是否支持暗盘交易 |
| is_support_intl_placing | bool | 是否支持国际配售 |
| show_intl_placing_info | bool | 是否向当前用户展示国际配售信息 |
| intl_placing_apply_start_timestamp | int64 | 国际配售认购开始（毫秒）；0=无 |
| intl_placing_apply_end_timestamp | int64 | 国际配售认购截止（毫秒）；0=无 |
| intl_placing_apply_limit | float | 国际配售最低认购金额（HKD） |
| intl_placing_apply_limit_str | string | 国际配售最低金额（含千分位） |
| placing_countdown_secs | int | 国际配售截止倒计时（秒）；0=无 |
| offer_type | string | 发售类型（见枚举） |
| security_type | string | 证券类型（见枚举） |
| apply_status | string | 公开认购状态（见枚举） |
| placing_apply_status | string | 国际配售认购状态（同 apply_status 枚举） |

#### 美股 (US)

| 字段 | 类型 | 说明 |
|------|------|------|
| code | string | 带市场前缀的代码，如 `US.AAPL` |
| name | string | 英文名 |
| sc_name | string | 简体中文名 |
| tc_name | string | 繁体中文名 |
| list_time | string | 预计上市日期 yyyy-MM-dd |
| list_timestamp | int64 | 上市时间戳（毫秒） |
| ipo_price_min | float | 招股价下限（USD） |
| ipo_price_max | float | 招股价上限（USD） |
| issue_size | int | 发行股数 |
| apply_limit | float | 最低认购金额（USD） |
| apply_start_timestamp | int64 | 认购开始时间戳（毫秒） |
| apply_end_timestamp | int64 | 认购截止时间戳（毫秒） |
| lucky_timestamp | int64 | 预计公布结果时间戳（毫秒） |
| stock_status | string | IPO 状态：`PENDING` / `APPLYING` / `CLOSED` |
| is_user_applied | bool | 当前用户是否已认购 |
| offer_type | string | 发售类型（同港股枚举） |

#### A 股 (CN)

| 字段 | 类型 | 说明 |
|------|------|------|
| code | string | 带市场前缀的代码，如 `SZ.300728` |
| name | string | 英文名 |
| sc_name | string | 简体中文名 |
| tc_name | string | 繁体中文名 |
| list_time | string | 上市日期；未上市为 `"--"` |
| list_timestamp | int64 | 上市时间戳（毫秒）；未上市为 0 |
| apply_code | string | 申购代码 |
| apply_upper_limit | int | 申购上限（股） |
| ipo_price | float | 发行价（CNY） |
| winning_ratio | float | 中签率（%） |
| issue_pe_rate | float | 发行市盈率 |
| apply_timestamp | int64 | 申购时间戳（毫秒） |
| winning_time | string | 中签公布日期 yyyy-MM-dd |
| winning_timestamp | int64 | 中签公布时间戳（毫秒） |
| is_has_won | bool | 是否已公布中签结果 |

#### 新加坡 (SG)

| 字段 | 类型 | 说明 |
|------|------|------|
| code | string | 带市场前缀的代码，如 `SG.1V2` |
| name | string | 英文名 |
| sc_name | string | 简体中文名 |
| tc_name | string | 繁体中文名 |
| list_time | string | 上市日期 yyyy-MM-dd |
| list_timestamp | int64 | 上市时间戳（毫秒） |
| ipo_price_min | float | 招股价下限（SGD） |
| ipo_price_max | float | 招股价上限（SGD） |
| offer_price_display | string | 发行价展示文本 |
| issue_size_display | string | 发行规模展示文本 |
| apply_limit | float | 最低认购金额（SGD） |
| apply_limit_display | string | 最低认购金额展示文本 |
| market_cap_display | string | 市值展示文本 |
| fund_amount_display | string | 募资金额展示文本 |
| industry_display | string | 行业信息 |
| managers_display | string | 承销商信息 |
| ipo_book_link | string | 招股书链接 |
| security_type | string | 证券类型（同港股枚举） |
| apply_start_timestamp | int64 | 认购开始时间戳（毫秒） |
| apply_end_timestamp | int64 | 认购截止时间戳（毫秒） |
| is_subscribe_status | bool | 是否处于可认购状态 |
| is_user_applied | bool | 当前用户是否已认购 |

#### 马来西亚 (MY)

| 字段 | 类型 | 说明 |
|------|------|------|
| code | string | 带市场前缀的代码，如 `BMS.MYIPO007` |
| name | string | 英文名 |
| sc_name | string | 简体中文名 |
| tc_name | string | 繁体中文名 |
| list_time | string | 上市日期 yyyy-MM-dd |
| list_timestamp | int64 | 上市时间戳（毫秒） |
| ipo_price | float | 发行价（MYR） |
| issue_size | int | 发行股数 |
| fund_amount | float | 募资总额（MYR） |
| market_cap | int | 市值（MYR） |
| currency | string | 币种代码，如 `MYR` |
| manager | string | 承销商信息 |
| industry_plate | string | 行业板块名称 |
| business | string | 公司介绍 |
| ipo_book_link | string | 招股书链接 |
| security_type | string | 证券类型（同港股枚举） |
| apply_start_timestamp | int64 | 认购开始时间戳（毫秒） |
| apply_end_timestamp | int64 | 认购截止时间戳（毫秒） |
| draw_timestamp | int64 | 散户抽签时间戳（毫秒） |
| lucky_timestamp | int64 | 公布结果时间戳（毫秒） |
| apply_limit | float | 最低认购金额（MYR） |
| is_subscribe_status | bool | 是否处于可认购状态 |
| is_user_applied | bool | 当前用户是否已认购 |
| support_leverage | bool | 是否支持杠杆认购 |

### 枚举值

**offer_type（发售类型）：**
| 值 | 含义 |
|----|------|
| UNSUPPORTED | 不支持 |
| PUBLIC_OFFER_ONLY | 仅公开发售 |
| INTERNATIONAL_PLACING_ONLY | 仅国际配售 |
| PUBLIC_AND_INTER_PLACING | 公开发售+国际配售 |

**security_type（证券类型）：**
| 值 | 含义 |
|----|------|
| NORMAL | 普通股票 |
| SPAC | 特殊目的收购公司 |
| HK_IBOND | 香港 iBond |
| HK_CLIMATE_BOND | 香港绿色债券 |
| HK_SILVER_BOND | 香港银色债券 |
| HK_ETF | 香港 ETF |
| SG_ETF | 新加坡 ETF |

**apply_status（认购状态）：**
| 值 | 含义 |
|----|------|
| NOT_APPLIED | 未申请 |
| APPLY_PENDING | 申请待处理 |
| APPLY_PROCESSING | 申请处理中 |
| APPLY_WON | 已中签 |
| APPLY_LOST | 未中签 |

**stock_status（美股 IPO 状态）：**
| 值 | 含义 |
|----|------|
| PENDING | 待开放认购 |
| APPLYING | 认购中 |
| CLOSED | 认购已截止 |

### 错误码

| ret_code | 触发条件 | 处理建议 |
|----------|----------|----------|
| 0 | 成功 | — |
| -3 | request_type 值无效 | 按各市场允许值修正后重试 |
| -5 | 后端调用失败/超时 | 稍后重试 |

---
