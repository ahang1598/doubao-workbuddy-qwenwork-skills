# WeStock Data - 详细命令用法

> 本文档包含所有命令的完整语法、参数说明、使用示例。
> 按功能分组组织，便于快速查找。

> ⚙️ **示例约定**：下文 `westock-data <命令>` 为简写，实际执行 `npx -y westock-data-skillhub@1.0.5 <命令>`（skillhub 包名：`westock-data-skillhub`）。

> 📌 **配套文档**：
> - 路由规则、高频意图对照、能力差异速查 → [routing-guide.md](./routing-guide.md)
> - 完整分析场景模板 → [scenarios-guide.md](./scenarios-guide.md)
> - 返回字段说明 → [ai_usage_guide.md](./ai_usage_guide.md)
>
---

## 一、行情

> 价格序列、技术指标、筹码成本。含单标的时序数据（`kline`/`technical`/`chip`）。

### K 线与搜索

```bash
westock-data search 腾讯控股                    # 默认仅搜股票（A股/港股/美股，排除 ETF/可转债/板块/指数等）
westock-data search 沪深300 --type etf          # 搜索 ETF
westock-data search 银行 --type sector          # 搜索板块
westock-data search 黄金 --type futures         # 搜索期货
westock-data search 离岸 --type forex           # 搜索外汇
westock-data kline sh600000 --period day --limit 20    # K线（m1/m5/m15/m30/m60/m250/day/week/month/season/year）
westock-data kline sz000001 --period day --limit 60 --fq qfq    # 复权（qfq/hfq/bfq，最大2000条）
westock-data kline sh600000 --start 2025-01-01 --end 2025-12-31    # 按日期范围查K（优先级高于 --limit）
westock-data kline sh600000 --start 2025-06-01                     # 仅指定起始日（end=今天）
```

> **K 线说明**：`kline` 返回历史 K 线序列，**数据有延迟，不代表盘中实时价**；展示时必须标注数据日期，勿称「实时行情」。
> `search` 不支持多代码批量；`fund flow` 跨市场须分开查。完整列表见 [SKILL.md](../SKILL.md) 或 [routing-guide.md §六/§九](./routing-guide.md)。
> **K线日期范围**：`kline` 支持 `--start` / `--end`（YYYY-MM-DD），优先级高于 `--limit`；范围模式下 `--limit` 仅作为返回条数上限保护，默认放宽到 2000。仅指定 `--start` 时 `end` 默认今天；仅指定 `--end` 时自动按周期回溯一段窗口。**期货/外汇 K 线暂不支持日期范围**，传入会自动降级到 `--limit` 模式并提示。
> **统一 `search`**：**默认仅搜股票**（A股/港股/美股个股）；用 `--type etf|bond|sector|index|futures|forex` 切换到其它类型（**不会跨类型 fan-out**）。

### 技术指标与筹码

```bash
westock-data technical sh600000 --indicator macd,rsi   # 技术指标（ma/macd/kdj/rsi/boll/bias/wr/dmi/all）
westock-data technical sh600000 --indicator macd --start 2026-02-01 --end 2026-03-01    # 历史区间
westock-data chip sh600519                         # 筹码成本（仅沪深京A股）
```

> 技术指标输出截面或历史区间数据；筹码成本仅支持沪深京A股，用于分析获利盘/套牢盘比例。

---

## 二、市场

> 全市场截面/总览/指数/互联互通。含龙虎榜、指数成份股、市场总览（A 股大盘画像）、涨跌分布、沪深港通成份股。

### 龙虎榜（仅A股）

```bash
westock-data lhb --type institution,hotmoney    # 龙虎榜（机构榜/游资榜/活跃席位/高胜率买入/高胜率席位）
westock-data lhb --type activeseat --date 2026-03-20
```

> 龙虎榜仅支持A股。

### 指数数据

```bash
westock-data index constituent sh000300        # A股指数成份股
westock-data index constituent hkHSI           # 港股指数成份股（恒生指数）
westock-data index constituent hkHSCEI,hkHSTECH # 多个港股指数
westock-data index list                         # 指数清单（支持 --limit/--offset 分页）
westock-data search 沪深300 --type index        # 搜索指数（统一 search 入口）
```

**常用指数**：`sh000001`(上证)、`sz399001`(深证成指)、`sz399006`(创业板)、`hkHSI`(恒生)、`us.IXIC`(纳斯达克)、`us.INX`(标普500)

### 市场总览（A 股大盘画像）

> `market-overview` 是 A 股大盘的"宏观体检"：8个维度（画像总评/收盘/区间/技术/涨跌分布/两融/估值/风格）共用同一组 `market_statis_*` 后端清单。
> 不带 type 时默认输出 **summary 画像总评**（14 维度得分 + 状态文案，含估值/情绪/技术/趋势/风格轮动等），
> 是给 LLM 做"市场点评"最直接的入口。

```bash
westock-data market-overview                                          # 默认 = summary（市场画像总评）
westock-data market-overview --type trade                             # 三大指数收盘统计 + 两市成交额多周期均值
westock-data market-overview --type interval                          # 三大指数 5/10/20/60/120/250D 涨跌 + 52W 高低
westock-data market-overview --type technical                         # 大盘 MACD/KDJ/RSI/BOLL/MA + 神奇九转
westock-data market-overview --type updown                            # A 股涨跌停/红绿盘/多周期新高新低数
westock-data market-overview --type margin                            # 两融余额多周期变动
westock-data market-overview --type valuation                         # 中证全指 PE/PB/PS + 历史百分位（数据通常滞后 1~4 个交易日）
westock-data market-overview --type rotation                          # 沪深300/中证1000/成长/价值 风格轮动
westock-data market-overview --type technical,updown                  # 多类一次拉
westock-data market-overview --type all --date 2026-05-18             # 全部 8 类
westock-data market-overview list                                     # 列出全部 type
```

### 沪深港通成份股（互联互通）

```bash
westock-data connect --exchange sh                              # 沪股通成份股（北向 / 陆股通标的池）
westock-data connect --exchange sz --limit 50 --offset 50       # 深股通成份股（统一用 --limit/--offset 分页）
```

> ⚠️ **职责边界**：`connect` = 沪深港通**标的池**（标的列表）；`fund flow sh600000` = 北向资金流量（金额数据）；二者不要混用。

### 新股日历

```bash
westock-data ipo --market hs                    # 新股日历（--market hs/hk/us）
```

> 新股日历查询新股申购与上市信息，支持沪深/港股/美股三个市场。

### A 股交易日历

```bash
westock-data trade-calendar                                    # 默认当月
westock-data trade-calendar --date 2026-06-09                  # 单日是否交易日
westock-data trade-calendar --start 2026-06-01 --end 2026-06-30  # 区间
westock-data trade-calendar --year 2026 --trading-only         # 全年仅交易日
```

> ⚠️ **`trade-calendar` vs `calendar`**：`trade-calendar` 查**交易所开市/休市**（清单 `calendar_hsj`）；`calendar` 查**个股投资事件**（分红/财报/新股等）。二者不可混用。

### 市场涨跌分布

```bash
westock-data changedist                         # 沪深A股涨跌分布（涨跌/涨跌停/停牌家数 + 上涨占比情绪 + 涨跌幅区间分布 + 两市成交额）
westock-data changedist --raw                   # 输出 JSON
```

> 涨跌分布为沪深A股全市场截面（实时）：概览含上涨/下跌/平盘、涨停/跌停、停牌家数与上涨占比情绪文案；明细为 11 个涨跌幅区间（涨停→>7%→…→平→…→跌停）的家数分布，并附两市成交额及其较上日变动。

---

## 三、板块

> 板块/概念股查询（搜索/成份股/信息/行情榜/经营/估值）。

### 板块成份股（含概念股查询）

> ⚠️ **概念股查询**："华为概念股"、"AI 概念股"等问法 → 用 `search <关键词> --type sector` → `sector constituent <代码>` 两步查询。

```bash
westock-data search 华为 --type sector            # 搜索板块代码（华为/AI/新能源等概念）
westock-data sector constituent pt01801080        # 板块成份股
```

> **板块代码**：使用 `search --type sector` 返回的 code（如 `pt01801080`、`pt02GN2328`）。

> **`sector constituent <代码>` vs `sector info <代码>`**：
> - `sector constituent <代码>`：返回板块**全部成份股**（含 SectorCode 字段，可逐只展开分析）
> - `sector info <代码>`：返回板块**基础信息 + 区间交易数据**（名称、板块类型、成份股数量、区间涨跌幅、区间成交额等）。**不含成份股**，适合用户问"XX板块怎么样"等总览类问题。
>
> ⚠️ **查个股所属行业/板块**（如"茅台属于哪个板块"）→ 用 `profile <代码>`，**不要**用 `sector constituent`（方向相反，且不接受 sh/sz 个股代码）。

### 行业经营数据（价格/产量/销量等）

> 查询各行业经营指标的历史序列数据，覆盖20+行业。数据包括价格、产量、销量、收入等经营指标。

```bash
westock-data sector oper 煤炭
westock-data sector oper 煤炭 --date 2026-06-15
westock-data sector oper --list               # 列出所有支持经营数据的行业
```

> **行业标识**（非板块代码 pt*）：`media`(传媒) / `elec`(电力设备) / `eltn`(电子) / `re`(房地产) / `text`(纺织服饰) / `nbfin`(非银金融) / `steel`(钢铁) / `utils`(公用事业) / `dfnse`(国防军工) / `env`(环保) / `mach`(机械设备) / `chem`(基础化工) / `comp`(计算机) / `happl`(家用电器) / `bmat`(建筑材料) / `bldg`(建筑装饰) / `trans`(交通运输) / `coal`(煤炭) / `cosm`(美容护理) / `agri`(农林牧渔) / `auto`(汽车) / `trade`(商贸零售) / `socsv`(社会服务) / `petro`(石油石化) / `food`(食品饮料) / `comm`(通信) / `pharm`(医药生物) / `bank`(银行) / `metal`(有色金属)

> **参数说明**：
> - `<行业>`：支持中文名称（如"煤炭"）或标识（如 `coal`），**不要**传板块代码（如 `pt02021291`）
> - `--list`/`-l`：列出所有支持经营数据的行业
> - `--date`：查询日期 YYYY-MM-DD（默认今天）

---

### 板块行情榜（涨幅 / 资金流入）

```bash
westock-data sector ranking                     # 板块行情榜（行业涨幅 Top10 + 概念涨幅 Top10 + 行业资金流入 Top5 + 北向热门板块）
```

> **`sector ranking` vs `sector constituent/info` 区分**：
> - `sector ranking`：**全市场板块行情榜**（行业涨幅 + 概念涨幅 + 资金流入 + 北向热门），用于"今天哪些板块在涨/资金在流入"类问题
> - `sector constituent/info`：**按代码精查**（成份股 / 画像 / 区间交易），用于"消费板块成份股有哪些 / 半导体板块怎么样"类问题
> - 决策入口：泛问"市场上哪些板块涨得多/资金流向" → `sector ranking`；指定"XX 板块的成份股/画像" → `sector constituent/info`

### 板块估值（PE/PB/PS/PCF/DIV + 历史百分位）

```bash
westock-data sector valuation pt01801080
westock-data sector valuation pt01801080,pt01801081
westock-data sector valuation pt01801080 --start 2026-01-01 --end 2026-06-25
```

> **参数说明**：
> - 仅支持 **板块代码**（`pt*`）
> - `--date`：单日精查；`--start` + `--end`：历史序列（每次单板块）

### 行业未来盈利预测

```bash
westock-data sector forecast pt01801780
westock-data sector forecast pt01801780,pt01801081
westock-data sector forecast pt01801780 --date 2026-06-25
```

> **参数说明**：
> - 仅支持 **申万一级/二级行业**板块代码（`pt*`）
> - 输出未来 3 年一致预期表，列含 `year | revenue | netProfit | netAssets | revenueYoy | netProfitYoy | netProfitCagr2Y | pe | pb | ps | roe | peg`（字段说明见 `ai_usage_guide.md` §sector forecast）

### 行业财务指标

```bash
westock-data sector finance pt01801780
westock-data sector finance pt01801780,pt01801080
westock-data sector finance pt01801780 --start 2020-01-01 --end 2026-03-31
```

> **参数说明**：
> - 支持申万 **一级/二级/三级**行业（`pt*`）
> - 默认最新财务截面；`--start` + `--end` 查询同业内历史变动
> - 聚源概念/地域不支持；字段说明见 `ai_usage_guide.md` §sector finance

---

## 四、研究

> 评分/评级/一致预期/研报。覆盖个股的多维度评估视角。

### 评估与研究

```bash
westock-data score sh600519                        # 个股评分（综合/资金/基本面/风险/技术 + 周/月/季变动）
                                                   # ↑ 单股查询；评分排行选股请用 westock-tool ranking CompScore
westock-data esg sh600519                          # ESG 评级（默认中证+聚源双源）
westock-data esg sh600519 --source csi             # 仅中证 ESG
westock-data rating hk00700                       # 机构评级（港股/美股，3段：目标价&评级 / 评级月度趋势 / 价格 vs 目标价）
westock-data consensus sh600519                    # 一致预期（A股、港股，自动分发）
westock-data report list sh600000 --limit 20       # 个股研报列表
westock-data report list pt01801080 --limit 20     # 行业/板块研报列表（支持个股代码与行业代码）
westock-data report detail <研报ID>                # 研报详情（ID 从研报列表获取）
```

> **`report` 命令使用流程**：
> 1. 先通过 `westock-data report list sh600000`（个股）或 `westock-data report list pt01801080`（行业）获取研报列表
> 2. 从列表中复制研报 ID（如 `res832471322631`）
> 3. 使用 `westock-data report detail res832471322631` 查看完整研报内容

---

## 五、事件

> 风险事件、投资日历、停复牌。

### 投资日历

查询投资日历，按事件类型分组输出。

```bash
westock-data calendar                                          # 今天所有类型事件
westock-data calendar --date 2026-06-04                      # 指定日期
westock-data calendar --event dividend                          # 只看分红派息
westock-data calendar --event financial_report --market hs     # 财报发布（沪深）
westock-data calendar --event ipo --market hk                # 新股发行（港股）
westock-data calendar --event trading_halt,meeting,lockup_release  # 多类型（逗号分隔）
westock-data calendar --event all --market us --limit 30     # 美股所有事件，限制30条
```

**参数说明**：

| 参数 | 说明 | 默认值 |
| --- | --- | --- |
| `--date` | 查询日期 YYYY-MM-DD | 今天 |
| `--event` | 事件类型过滤，可选值见下表 | `all` |
| `--market` | 市场：`hs`（沪深）/ `hk`（港股）/ `us`（美股） | `hs` |
| `--limit` | 返回条数 | 10 |

**`--event` 可选值**：

| 英文术语 | 中文标签 | API 短码 |
| --- | --- | --- |
| `financial_report` | 财报发布 | cbfb |
| `dividend` | 分红派息 | fh |
| `ipo` | 新股发行 | xg |
| `trading_halt` | 停复牌 | tfp |
| `meeting` | 会议 | hy |
| `lockup_release` | 限售解禁 | jj |
| `rights_issue` | 增发 | zf |
| `all` | 全部（不筛选） | all |

> 输出按中文标签分组（财报发布/分红派息/新股发行/停复牌/会议/限售解禁/增发）。

### 风险事件（仅A股，8 种类型）

```bash
westock-data risk sh600000                            # 全部风险事件
westock-data risk sz000001 --types pledge,unlock      # 仅指定类型
westock-data risk sh600000,sz000001 --types pledge    # 批量
```

**8 种类型**：`specialtrade`(ST)、`pledge`(质押)、`unlock`(解禁)、`lawsuit`(诉讼)、`seasonedissue`(增发)、`leaderchange`(高管变动)、`executivetransfer`(高管增减持)、`bondrating`(评级)。

**别名**：`st`/`special`→specialtrade、`addition`→seasonedissue、`leader`→leaderchange、`executive`→executivetransfer、`rating`→bondrating。

### 停复牌信息

```bash
westock-data suspension --market hs             # 停复牌信息（--market hs/hk/us）
```

---

## 六、公告

> 公告与原文。

### 公告

```bash
westock-data notice list sh600000 --type 1              # 公告列表（--type：0全部/1财务/2配股/3增发/4股权变动/5重大/6风险/7其他）
westock-data notice detail nos1224809143                # 公告全文（nos沪深→纯文本；nok港股/nou美股→PDF URL）
```

> 公告详情：`notice detail` 返回全文（沪深纯文本；港美 PDF URL）。

---

## 七、资金

> 二级市场资金数据。含个股资金、卖空数据、融资融券、大宗交易、北向持仓。

### 资金流向（个股/板块）

```bash
# A股：主力资金（单日 / --start..--end 区间）
westock-data fund flow sh600000
westock-data fund flow sh600000,sz000001 --start 2026-05-01 --end 2026-05-20

# A股板块：资金流向（支持 pt 开头板块代码）
westock-data fund flow pt01801081

# 港股：资金流向
westock-data fund flow hk00700

# 港股：卖空数据（单日 / --start..--end 区间）
westock-data fund short hk00700
westock-data fund short hk00700 --start 2026-05-01 --end 2026-05-20

# 美股：卖空数据（单日 / --start..--end 区间）
westock-data fund short usAAPL
westock-data fund short usAAPL --start 2026-05-01 --end 2026-05-20

# 大宗交易（仅沪深）
westock-data fund block sh600519
westock-data fund block sh600519,sz000651

# 融资融券（仅沪深）
westock-data fund margin sh600519
westock-data fund margin sh600519,sz000651

# 北向持仓（个股季度明细 / 申万行业分布）
westock-data fund north-holding sh600519              # 单股：最新季 + 次新季
westock-data fund north-holding sh600519,sz000651    # 多股批量
westock-data fund north-holding pt01801080            # 板块裸码（自动识别 sw 级别）
westock-data fund south-holding hk00700,hk03690       # 港股南下持仓
```

> ⚠️ **美股限制**：美股不支持 `fund flow`（资金流向），只支持 `fund short`（卖空数据）

> ⚠️ **命令区分**：`flow` = 资金流向（主力/散户）；`short` = 卖空；`block` = 大宗交易；`margin` = 融资融券；`north-holding` = A股北向**季度持仓**；`south-holding` = 港股南下**持仓快照**

> ⚠️ **北向数据职责边界**：
> - `connect` = 陆股通**标的池**（哪些股票可被北向交易）
> - `fund flow sh600000` = 个股日度**资金流向**
> - `fund north-holding sh600519` = A股**季度北向持仓**（最新季 + 次新季）
> - `fund south-holding hk00700` = 港股**南下持仓**（持有比例/日季变动）
> - `fund north-holding pt…` = 申万行业**北向持仓分布**
> - `sector ranking` = 全市场**北向热门板块**榜（当日/5日/20日）
> - 北向**成交活跃股 / 上榜频次**全市场榜单 → `westock-tool ranking north_active_*` / `north_appear_*`（固定 Top20，不支持 `--limit`）

> ⚠️ **市场限制**：`block`/`margin` 仅支持沪深（sh/sz）；`short` 支持港股和美股；`flow` 支持沪深和港股（美股请用 `fund short`）

> 沪深港通成份股（北向 / 陆股通标的池）属于"市场"分组，见第二章；不在资金流量数据范围内。

---

## 八、简况

> 公司基本信息/股东/分红/回购。

### 公司基本信息

```bash
westock-data profile sh600000                  # 公司简况
westock-data shareholder sh600519              # 股东结构（A股：十大股东/十大流通/股东户数；港股：持股股东+机构持仓）
westock-data disclosure sh600519               # 财报披露日历（财报发布前的预约披露日）
```

### 分红数据

```bash
westock-data dividend list sh600519 --years 5                           # 分红派息（A股/港股/美股）
westock-data dividend list sh600519 --all                               # 含未实施的分红方案
```

> ⚠️ **货币单位**：港股返回港元/美元，美股返回美元，展示时必须标注正确货币单位

### 公司回购

```bash
westock-data buyback sh600519                 # 公司回购（A股/港股）
westock-data buyback sh600519,hk01810         # 批量回购（A/H 混批分表输出）
westock-data buyback hk01810 --start 2026-03-01 --end 2026-04-14
```

---

## 九、财务

> 三大报表/财报披露日历。

### 财务数据

**默认行为**：省略 `--type` 时拉取 `income` + `balance` + `cashflow` 三大报表（单股/批量均支持）。显式 `--type` 时只拉一张表。

**支持参数**：`--type`（`income` \| `balance` \| `cashflow`）、`--num`（期数）、`--start` / `--end`（日期区间，与 `--num` 互斥）

| `--type` | 含义 | A股 | 港股 | 美股 |
|----------|------|-----|------|------|
| （省略） | 三大报表 | 利润表+资产负债+现金流 | 同左 | 同左 |
| `income` | 利润表 | 利润表 | 综合损益表 | Income Statement |
| `balance` | 资产负债表 | 资产负债表 | 资产负债表 | Balance Sheet |
| `cashflow` | 现金流量表 | 现金流量表 | 现金流量表 | Cash Flow |

```bash
westock-data finance sh600000                         # 三大表，最新 1 期
westock-data finance sh600519,sz000651 --num 4        # 批量三大表（同市场）
westock-data finance hk01810,hk00700 --num 1          # 港股批量三大表
westock-data finance sh600000 --type income --num 8   # 仅利润表
westock-data finance hk00700 --type income --num 4    # 仅综合损益表

# 按日期区间（与 --num 互斥）
westock-data finance sh600000 --start 2024-01-01 --end 2024-12-31              # 三大表区间
westock-data finance sh600000 --type income --start 2024-01-01 --end 2024-12-31
```

> 跨市场批量对比须**同一市场**（字段口径不同）。

> **参数说明**：`--num`（期数）与 `--start`/`--end`（日期区间）互斥，请只指定其中一组。日期格式：YYYY-MM-DD。

### 财报披露日历

```bash
westock-data disclosure sh600519               # 财报披露日历（A股/港股/美股；又称业绩预约披露日）
```

---

## 十、ETF

> ETF 全维度。含详情/持仓/净值/公司/持有人/财务指标。
>
> ⚠️ **路由强信号**：用户问 ETF 全维度信息时一律用 `etf detail`，**不要**用 `kline`/`etf nav` 拼凑。

```bash
westock-data etf detail sh510300                                       # ETF 详情（含 4 级分类、基金经理历史、Top20 持仓）
westock-data etf holdings sh510300                                     # ETF 持仓明细
westock-data etf nav sh510300 --start 2026-01-01 --end 2026-03-31      # 净值历史
westock-data etf company sh510300                                      # 基金公司信息
westock-data etf holders sh510300                                      # 持有人结构
westock-data etf financial sh510300                                    # 财务指标
```

> `etf detail` 输出 5 段表格：主体行情/规模/费率 → **详细分类**（资产类别/投资风格/细分领域/具体方向/跟踪标的）→ 基金经理 → **基金经理历史**（当前在任/首任/任职最长/全部历任）→ 持仓 Top20。

> 详细字段说明见 [references/ai_usage_guide.md](./ai_usage_guide.md)

---

## 十一、宏观

> 宏观经济指标。覆盖中国（GDP/CPI/PMI/货币/财政/估值/专项）+ 美/港/日/欧主题宏观日历 + 36 个地区海外预期日历。

### 子命令总览

```bash
# 列出指标（可按 region 过滤）
westock-data macro list                                       # 列全部
westock-data macro list --region cn                           # 中国（32 个）
westock-data macro list --region us                           # 美股（8 个）
westock-data macro list --region jp                           # 日本（6 个）
westock-data macro list --region eu                           # 欧元区（6 个）
westock-data macro list --region hk                           # 港股（4 个）
westock-data macro list --region global                       # 海外预期 36 个地区
westock-data macro expect list                                # 仅列 36 个地区

# 主题型指标查询（cn/us/hk/jp/eu）
westock-data macro indicator <短名[,短名...]> [--year Y | --date D | --start S --end E]
westock-data macro indicator --region <r> [--date D]          # 一键拉某 region 全套

# 海外预期日历（按地区 iso3，按年）
westock-data macro expect --area <iso3> [--year Y | --start S --end E]
```

### 中国（cn）— 主题型指标

```bash
# 按年（GDP/价格/工业/消费/投资/货币/财政/预测/历史日历）
westock-data macro indicator cn_gdp --year 2025
westock-data macro indicator cn_cpi_ppi,cn_pmi --year 2025                 # 多指标
westock-data macro indicator cn_pmi --start 2023 --end 2025                # 区间趋势
westock-data macro indicator cn_fiscal --year 2025                          # 财政
westock-data macro indicator cn_yield_curve --year 2025                     # 国债收益率曲线
westock-data macro indicator cn_mlf --year 2025                             # MLF 操作

# 按日期（综合 / 估值 / 中国专项）
westock-data macro indicator cn_core --date 2026-06-09                      # 最新核心（一键 p1+p2）
westock-data macro indicator cn_premium_curve --date 2026-06-09             # 溢价率曲线
westock-data macro indicator cn_premium_value --date 2026-06-09             # 溢价率水平（10年分位）
westock-data macro indicator cn_term_spread --date 2026-06-09               # 期限利差
westock-data macro indicator cn_calendar_future --date 2026-06-09           # 宏观日历未来
westock-data macro indicator cn_lpr --date 2026-06-09                       # LPR
westock-data macro indicator cn_caixin_pmi --date 2026-06-09                # 财新 PMI
westock-data macro indicator cn_installed_capacity --date 2026-06-09        # 发电装机容量
```

### 美/港/日/欧 — 主题宏观（按日期，事件日历型）

```bash
# 美股
westock-data macro indicator us_employment --date 2026-06-09                # 美国就业
westock-data macro indicator us_inflation --date 2026-06-09                 # 美国通胀
westock-data macro indicator us_employment,us_inflation,us_monetary --date 2026-06-09  # 多指标
westock-data macro indicator --region us --date 2026-06-09                  # 一键拉美股 8 个

# 港股
westock-data macro indicator hk_eco_growth --date 2026-06-09
westock-data macro indicator --region hk --date 2026-06-09                  # 一键拉港股 4 个

# 日本
westock-data macro indicator jp_inflation --date 2026-06-09
westock-data macro indicator --region jp --date 2026-06-09                  # 一键拉日本 6 个

# 欧元区
westock-data macro indicator eu_monetary --date 2026-06-09
westock-data macro indicator --region eu --date 2026-06-09                  # 一键拉欧元区 6 个
```

> 主题型返回 schema：`IndicatorName / OccurDate / OccurTime / ActualValue / ForecastValue / FormerValue`，按日期降序展示。

### 海外预期日历（global）— 按地区 iso3，按年

```bash
westock-data macro expect list                                     # 列 36 个地区 iso3 代码
westock-data macro expect --area chn --year 2025                # 中国
westock-data macro expect --area usa --year 2025                # 美国
westock-data macro expect --area jpn --year 2025                # 日本
westock-data macro expect --area usa --start 2023 --end 2025    # 区间
```

> 海外预期 schema 在主题型基础上多一列 `Importance`（1=低 / 2=中 / 3=高）。

### 短名命名规则

- 中国主题：`cn_<topic>`（如 `cn_gdp`/`cn_lpr`/`cn_premium_curve`）
- 海外主题：`<region>_<topic>`（如 `us_employment`/`jp_inflation`）
- 海外预期：`expect_<iso3>`（共 36 个地区，由 `macro expect list` 列出）
- 聚合短名：`cn_core` 一键拉 `cn_core_p1 + cn_core_p2`



| 分组 | 短名 | 查询方式 |
|------|------|----------|
| GDP | cn_gdp / cn_cpi_ppi / cn_pmi / cn_profit / cn_valueadded / cn_consumption / cn_investment / cn_export / cn_prosperity / cn_fiscal / cn_power_consumption / cn_disposable_income / cn_capacity_utilization / cn_product_output / cn_export_value | `--year`（后端按 YYYY-01-01） |
| 货币 | cn_financing / cn_fundquantity / cn_fundcost / cn_yield_curve / cn_mlf | `--year` |
| 估值 | **cn_premium_curve** / **cn_premium_value** / **cn_term_spread** | `--date` |
| 综合 | **cn_core**（聚合，自动展开 p1+p2） / cn_forecast / cn_calendar_hist / cn_calendar_future / cn_employment | cn_forecast/cn_calendar_hist 按 `--year`；cn_core/cn_calendar_future/cn_employment 按 `--date` |
| 中国专项 | cn_lpr / cn_caixin_pmi / cn_installed_capacity | `--date` |
| 美股主题 | us_employment / us_eco_growth / us_inflation / us_confidence / us_monetary / us_fiscal / us_energy / us_realestate | `--date`（事件日历型） |
| 港股主题 | hk_eco_growth / hk_export_reserve / hk_monetary / hk_others | `--date` |
| 日本主题 | jp_eco_growth / jp_inflation / jp_employment / jp_confidence / jp_monetary / jp_export_reserve | `--date` |
| 欧元区主题 | eu_eco_growth / eu_inflation / eu_monetary / eu_confidence / eu_export_reserve / eu_employment | `--date` |
| 海外预期 | expect_<iso3>（共 36 个地区，独立子命令 `macro expect --area`） | `--year` 或 `--start --end` |

> **三种查询方式**：
> 1. **按年份**（`--year` 或 `--start --end`）：cn_gdp/cn_cpi_ppi/cn_pmi 等绝大多数中国指标，后端按 `YYYY-01-01` 查询
> 2. **按日期**（`--date`）：`cn_core`/`cn_premium_*`/`cn_term_spread`/`cn_calendar_future`/`cn_employment`/`cn_lpr` 等中国日频指标，以及**所有海外主题**（us_/hk_/jp_/eu_）
> 3. **海外预期独立子命令**：`macro expect --area <iso3> --year`（按地区归档，36 个地区）
>
> **聚合短名**：`cn_core` 一键拉 `cn_core_p1 + cn_core_p2`（同时返回 7 大核心指标，不要用多次单指标查询拼凑）
>
> **region 一键全套**：`macro indicator --region us --date <今天>` 一键拉该 region 全套主题（不传短名 + `--region`）
>
> **mode 校验**：传错 `--year` 给 mode=date 指标会报错；不确定时先 `macro list --region <r>` 查 mode

### 专业研究场景速查（指标组合）

> 按机构投研常用研究框架组织。每行对应 `scenarios-guide.md` 中的一个专业场景。

```bash
# 通胀全景（场景 59）：CPI/PPI 剪刀差、核心 CPI、上下游传导
westock-data macro indicator cn_cpi_ppi --start 2024 --end 2025

# 国债收益率曲线（场景 60）：期限结构 + 牛陡/熊平判断
westock-data macro indicator cn_yield_curve --year 2025
westock-data macro indicator cn_term_spread --date 2026-06-08

# 股债性价比 / 风险溢价（场景 61）：大类资产配置核心指标（含 10 年分位）
westock-data macro indicator cn_premium_value --date 2026-06-08
westock-data macro indicator cn_premium_curve --date 2026-06-08

# 流动性投放与货币市场（场景 62）：MLF 操作 + SHIBOR/回购利率
westock-data macro indicator cn_mlf --year 2025
westock-data macro indicator cn_fundcost --year 2025

# 工业景气全景（场景 63）：5 维交叉验证（量/效/能/景气/产量）
westock-data macro indicator cn_profit,cn_valueadded,cn_prosperity,cn_capacity_utilization,cn_power_consumption --year 2025
westock-data macro indicator cn_product_output --year 2025

# 财政发力强度（场景 64）：收支结构 + 专项债进度
westock-data macro indicator cn_fiscal --year 2025

# 进出口深度解读（场景 65）：贸易差额 + 行业出口结构
westock-data macro indicator cn_export --year 2025
westock-data macro indicator cn_export_value --year 2025

# 居民收入与消费（场景 66）：收入结构 + 消费分项
westock-data macro indicator cn_disposable_income --year 2025
westock-data macro indicator cn_consumption --year 2025

# 就业市场（场景 67）：失业率分组 + 百度搜索指数高频信号
westock-data macro indicator cn_employment --date 2026-06-08

# 宏观日历事件预案（场景 68）：未来事件 + 历史回放 + 机构预测
westock-data macro indicator cn_calendar_future --date 2026-06-08
westock-data macro indicator cn_calendar_hist --year 2025
westock-data macro indicator cn_forecast --year 2025

# 中国专项（场景 69）：LPR / 财新 PMI / 装机容量
westock-data macro indicator cn_lpr,cn_caixin_pmi,cn_installed_capacity --date 2026-06-08

# 海外宏观日历（场景 70）：美/港/日/欧 主题事件
westock-data macro indicator --region us --date 2026-06-08         # 美股一键全套
westock-data macro indicator us_employment,us_inflation --date 2026-06-08
westock-data macro indicator jp_monetary --date 2026-06-08         # 日本央行政策
westock-data macro indicator eu_inflation --date 2026-06-08         # 欧元区通胀

# 海外预期日历（场景 71）：按地区 iso3 查事件 actual/forecast/former
westock-data macro expect --area chn --year 2025                # 中国
westock-data macro expect --area usa --start 2023 --end 2025    # 美国（区间）
westock-data macro expect --area jpn --year 2025                # 日本

# 美联储降息预期跟踪（场景 72）：FFR 利率 + FOMC 一致预期
westock-data macro indicator us_monetary --date 2026-06-08
westock-data macro expect --area usa --year 2026                # 看 FOMC 事件 ForecastValue

# 美国通胀压力多维评估（场景 73）：CPI/PCE/PPI + 通胀预期
westock-data macro indicator us_inflation --date 2026-06-08

# 中美宏观对比（场景 74）：增长/通胀/货币三维度
westock-data macro indicator --region us --date 2026-06-08         # 美股一键
westock-data macro indicator cn_core --date 2026-06-08             # 中国核心一键

# 港股宏观（场景 75）：联系汇率制度下的双重驱动
westock-data macro indicator --region hk --date 2026-06-08
westock-data macro indicator us_monetary --date 2026-06-08         # 港币随美联储

# 全球三大央行流动性对比（场景 76）：美日欧政策路径
westock-data macro indicator us_monetary,jp_monetary,eu_monetary --date 2026-06-08
```

---

## 十二、期货

> 外盘商品/金融期货（CME/COMEX/CBOT/NYMEX/LME 等）+ 港股股指期货。
> 标准代码前缀：`fu*`（外盘长版行情）、`hf_*`（LME 金属）、`r_hd*`（港股股指期货）。

### 合约搜索与资料

```bash
westock-data search 黄金 --type futures            # 关键词→合约代码（支持 名称/品类/交易所/代码）
westock-data search 贵金属 --type futures           # 按品类搜（贵金属/基本金属/能源化工/农产品/外汇/利率/股指/港股股指）
westock-data search 恒指 --type futures             # 港股股指期货
westock-data futures detail fuGC                   # 合约资料（交易所/规模/币种/最小变动/交易时间等）
```

### 期货 K 线

```bash
westock-data kline fuGC --period day --limit 30     # 黄金日K（含 OHLC/成交量/持仓量）
westock-data kline fuCN --period week --limit 20    # 周K（day/week/month/season/year）
westock-data kline r_hdHSImain --period day         # 恒指期货K线
```

> ⚠️ **期货限制**：外盘期货多为延时行情。`kline` 支持 `fu*`、`r_hd*` 合约；`hf_*`（LME）请用 `search --type futures` 找代码。期货不支持复权（`--fq` 无效）。

---

## 十三、外汇

> 离岸人民币、主要货币对、美元指数等即期现货汇率。
> 标准代码前缀：`fx*`（如 `fxCNH` 离岸人民币、`fxUSDJPY` 美元日元、`fxDINIW` 美元指数）。

### 品种搜索与列表

```bash
westock-data forex list                            # 列出全部外汇品种（代码/名称）
westock-data search 美元 --type forex              # 关键词→品种代码（匹配 名称/代码/裸代码）
westock-data search 离岸 --type forex              # 离岸人民币 → fxCNH
westock-data search 日元 --type forex              # 含日元的货币对（fxUSDJPY/fxEURJPY 等）
```

### 外汇 K 线

```bash
westock-data kline fxCNH --period day --limit 30    # 离岸人民币日K（day/week/month/season/year）
```

> ⚠️ **外汇限制**：外汇不支持复权。品种代码请用 `search --type forex` 或 `forex list`。

## 十四、债券（可转债 / 可交换债）

> 沪深可转债/可交换债。标准代码：沪市 `sh11xxxx`（110/111/113 可转债、118 科创板可转债）、`sh13xxxx`（132 可交换债）；深市 `sz12xxxx`（123/127/128 可转债、120 可交换债）。
> 行情/分时/K线沿用 sh/sz 前缀，直接复用个股通道，无需特殊命令。

### 可转债 K 线

```bash
westock-data kline sh113052 --period day --limit 30 # 日K（day/week/month/season/year）
```

> 可转债行情在通用价格/成交字段之外，额外返回**转债维度**：转股价值、纯债价值、转股/纯债溢价率、双低、总规模/剩余规模、评级、期限/剩余期限/到期日、到期收益率、是否转股、转股价/转股起始日、到期赎回价/强赎价/强赎触发价、回售触发价/回售起始日、正股 PB/正股代码。单只查询时以竖排「项目/内容」表展示，规模换算为亿元、日期规整为 `YYYY-MM-DD`。

### 可转债详情（bond detail）

```bash
westock-data bond detail sh113052                   # 核心要素：发行/规模/评级/期限利率/转股/赎回回售/关键日期
westock-data bond detail sh113052 --terms           # 追加条款全文（利率付息/转股价修正/赎回/回售/强赎等）
westock-data bond detail sh113052 --schedule        # 追加明细表（利率变动/现金流/赎回/回售/修正详情）
westock-data bond detail sh113052,sz123245          # 批量查询
```

> ⚠️ **可转债说明**：完整发行要素用 `bond detail`；K 线用 `kline`。

---
