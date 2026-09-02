# WeStock Data - 常见分析场景详解

> **定位**：本文档是 SKILL.md 的 **L3 层补充材料**，提供完整的分析场景示例和详细操作步骤。
>
> **使用方式**：AI 在遇到不确定的分析场景时按需加载本文档。命令列表和基本用法请参见
> [SKILL.md](../SKILL.md)。
>
> **场景总数**：共 70+ 个场景，按 15 个功能分组组织。

---

## 一、行情（价格序列/技术指标/筹码）

> 命令：`kline` `technical` `chip`（**K 线有延迟，非实时行情**）

### 1.1 分析成交量趋势

```
用户："分析牧原股份近20天的成交量"
→ westock-data search 牧原股份 → westock-data kline sz002714 --period day --limit 20 → 从表格中提取volume → 计算统计指标 → 输出分析报告
```

### 1.2 多股对比（使用批量查询）

```
用户："对比贵州茅台和格力电器近半年走势、财务、资金面"
→ 一次批量（各 1 条；不要 kline/technical 按股拆开）：
   westock-data kline sh600519,sz000651 --period day --limit 120
   westock-data technical sh600519,sz000651 --indicator macd
   westock-data finance sh600519,sz000651 --num 4
   westock-data fund flow sh600519,sz000651
   westock-data fund north-holding sh600519,sz000651
```

### 1.3 指数/板块K线分析

```
用户："上证指数近一个月的走势"
→ westock-data kline sh000001 --period day --limit 30 → 解析K线数据 → 计算区间涨跌幅 → 输出趋势分析

用户："半导体板块近一周的K线走势"
→ westock-data search 半导体 --type sector → 获取板块代码（如 pt01801081）
→ westock-data kline pt01801081 --period day --limit 5 → 解析K线 → 输出走势

用户："茅台 2025 年全年的日K"（按日期范围）
→ westock-data kline sh600519 --start 2025-01-01 --end 2025-12-31 → 解析K线 → 输出年度走势
（提示：--start/--end 优先级高于 --limit；仅指定 --start 时 end 默认今天）
```

### 1.5 筹码成本分析

```
用户："分析一下茅台的筹码分布情况"

AI 步骤：
1. 搜索股票：westock-data search 贵州茅台 → sh600519
2. 查询筹码数据：westock-data chip sh600519
3. 解析筹码盈利率（chipProfitRate）→ 判断获利盘/套牢盘比例
4. 对比收盘价与平均成本（chipAvgCost）→ 判断当前价位相对筹码成本的位置
5. 分析集中度（chipConcentration90/70）→ 集中度越低，筹码越集中
6. 输出筹码分析结论
```

### 1.6 筹码趋势分析

```
用户："看看招商银行近一个月的筹码变化趋势"

AI 步骤：
1. 搜索股票：westock-data search 招商银行 → sh600036
2. 查询历史筹码：westock-data chip sh600036 --start 2026-02-10 --end 2026-03-10
3. 解析 items[] 中每日的筹码数据
4. 分析趋势：
   - 盈利率趋势（上升 = 获利盘增加）
   - 平均成本趋势（上升 = 筹码成本抬升，主力可能在建仓）
   - 集中度趋势（下降 = 筹码趋于集中，可能有主力控盘）
5. 输出筹码变化趋势分析
```

---

## 二、市场（全市场截面/总览/指数/互联互通/新股）

> 命令：`lhb` `index` `market-overview` `connect` `ipo`（近几日涨跌可参考 `kline --period day --limit 5`；**K 线有延迟，勿当实时价**）

### 2.1 查询个股近几日行情（日 K）

```
用户："腾讯控股最近走势怎么样"

→ westock-data search 腾讯控股 → hk00700
→ westock-data kline hk00700 --period day --limit 5
→ 取最近一根 K 线的收盘价及区间涨跌 → 标注港元与数据日期（勿称实时）
```

### 2.2 指数行情查询

```
用户："上证指数最近表现如何"

→ westock-data kline sh000001 --period day --limit 5
→ 解析最近几根日 K 的涨跌幅、成交额 → 标注数据日期
（更广视角：westock-data market-overview 取 summary / updown 维度）
```

### 2.3 多指数对比

```
用户："对比沪深两市最近的表现"

→ westock-data kline sh000001,sz399001 --period day --limit 5
→ 对比上证与深证成指近期涨跌幅 → 输出分析（标注各 K 线日期）
```

### 2.4 跨市场指数对比

```
用户："对比恒生指数和纳斯达克最近的表现"

AI 步骤：
1. 批量查日 K：westock-data kline hkHSI,us.IXIC --period day --limit 5
2. 分别解析各指数近期涨跌幅
3. 对比涨跌幅（标注数据日期，勿称实时）
4. 输出跨市场指数对比分析
```
用户："对比恒生指数和纳斯达克今天的表现"

AI 步骤：
2. 分别解析各指数的行情数据
3. 对比涨跌幅
4. 输出跨市场指数对比分析
```

### 2.5 新股申购分析

```
用户："最近有什么新股可以申购？"

AI 步骤：
1. 查询沪深新股：westock-data ipo --market hs
   → 格式化输出按状态分类（即将发行/今日可申购/即将上市/中签号公布/已上市），含发行价、市盈率、申购代码、上市日、可比公司、风险提示等
2. 可选：查询港股新股：westock-data ipo --market hk
   → 格式化输出按申购日/上市日分类，含入场费、认购倍数、募集金额等
3. 可选：查询美股新股：westock-data ipo --market us
   → 格式化输出按状态分组（注册中/已定价/已提交等），含行业、发行价、价格区间、承销商等
4. 直接基于格式化输出，输出新股申购机会分析
```

### 2.6 今日市场点评（market-overview summary）

```
用户："今天 A 股市场怎么样？"

AI 步骤：
1. 一键拉取大盘画像：westock-data market-overview （默认 type=summary）
2. 解析 14 维度得分（估值/情绪/技术/趋势/风格轮动 等）+ 状态文案
3. 综合给出今日市场点评，标注偏强/偏弱维度
4. 如需补充，叠加 --type updown（涨跌停/红绿盘）/ --type margin（两融）/ --type valuation（中证全指 PE 百分位）
```

### 2.7 沪深港通成份股查询（connect）

```
用户："沪股通有哪些标的"

AI 步骤：
1. 拉沪股通成份股：westock-data connect --exchange sh
2. 分页拉全量：westock-data connect --exchange sh --limit 100 --offset 0
3. 拉深股通：westock-data connect --exchange sz
4. 输出标的池（注意：connect 是"标的池"列表，不是资金流量；查北向日度资金流量请用 `fund flow sh600000`；查北向季度持仓请用 `fund north-holding sh600519`；查申万行业北向分布请用 `fund north-holding <板块代码>`）
```

> ⚠️ **职责边界**：`connect` = 沪深港通**标的池**（标的列表）；`fund flow` = 日度资金流量；`fund north-holding` = 北向季度持仓（个股或申万行业）；三者不要混用。

### 2.8 查询指数成份股

```
用户："沪深300有哪些成份股？"

AI 步骤：
1. 查询沪深300成份股：westock-data index constituent sh000300
2. 解析返回的成份股列表
3. 输出成份股列表
4. 可按行业分布统计
```

---

## 三、板块（搜索/成份股/信息/行情榜/经营/估值/预测/财务）

> 命令：`search --type sector` / `sector constituent/info/ranking/oper/valuation/forecast/finance`

### 3.1 板块行情分析

```
用户："半导体板块今天的涨跌情况"
```

### 3.2 查询概念股列表（⚠️ 常见易错场景）

```
用户："华为概念有哪些股票？"
用户："AI概念股有哪些？"
用户："新能源汽车概念股"

⚠️ 错误做法：默认 `search 华为` 只搜股票，搜不到板块；或用外部搜索工具
✅ 正确做法：用 `search <关键词> --type sector` 两步查询

AI 步骤：
1. 搜索概念板块代码：westock-data search 华为 --type sector
   → 返回匹配的板块列表（如 style_pt01801517 华为概念）
2. 用板块代码查成份股：westock-data sector constituent style_pt01801517
   → 返回华为概念的全部成份股列表
3. 输出概念股列表（代码、名称）
```

> **关键区分**：
> - `search 华为 --type sector` → 拿到板块代码后，用 `kline`/ 查板块行情
> - `search 华为 --type sector` → 再用 `sector constituent <代码>` 查成份股

### 3.3 查询行业成份股

```
用户："电子行业有哪些成份股？"

AI 步骤：
1. 查询申万一级电子行业成份股：westock-data sector constituent pt01801080
2. 解析返回的成份股列表
3. 输出成份股列表（代码、名称）
4. 可补充成份股数量统计
```

### 3.4 板块成份 + 行情联动分析

```
用户："帮我看看半导体板块的成份股，并查看涨幅前5的行情"

AI 步骤：
1. 查询申万二级半导体成份股：westock-data sector constituent pt01801081
2. 取返回的成份股代码列表
4. 按涨跌幅排序取前5
5. 输出板块成份 + 涨幅排行分析
```

### 3.5 板块成份股查询

```
用户："半导体板块有哪些成份股"

AI 步骤：
1. 搜索板块代码 → pt01801081
2. 拉取成份股：westock-data sector constituent pt01801081
3. 输出成份股清单（含代码/名称/涨跌/成交额等）
```

> ⚠️ 易混淆：用户问"板块成份股"用 `sector constituent <代码>`；问"板块估值/盈利预测/财务"用 `sector valuation/forecast/finance <代码>`；问"板块概况"用 `sector info <代码>`。

### 3.6 申万行业基本面三连

```
用户："银行行业现在估值怎么样？盈利前景如何？"
用户："帮我分析一下半导体行业的基本面：财报、估值和一致预期"
用户："电子和银行哪个行业估值更低、盈利增速更好？"

⚠️ 错误做法：
- 用 `finance sh600036`（个股三大表）回答行业问题
- 用 `consensus`（个股一致预期）代替行业预测
- 用 `market-overview --type valuation`（全市场中证全指）代替单行业估值
- 对概念/地域板块（如海南、华为概念）调 `sector forecast` / `sector finance`

✅ 正确做法：finance（已披露）→ valuation（贵不贵）→ forecast（未来预期）

AI 步骤：
1. 若用户未给代码：westock-data search 银行 --type sector
   → 取申万行业 pt 代码（如 pt01801780 银行一级）
2. 同一轮并行查询三条（深研单行业）：
   westock-data sector finance pt01801780
   westock-data sector valuation pt01801780
   westock-data sector forecast pt01801780
3. 解读链条：
   - finance：`revenueTTM` / `netProfitTTM` / `roeTTM` / `debtRatio` → 当下盈利与杠杆
   - valuation：`PeTTM` + `PeTTMPct` 等百分位 → 相对历史贵不贵
   - forecast：未来 3 年 `netProfitYoy` / `pe` / `peg` → 机构一致预期增速与估值
4. 可选历史：westock-data sector finance pt01801780 --start 2020-01-01 --end 2026-03-31
   或 westock-data sector valuation pt01801780 --start 2026-01-01 --end 2026-06-25
5. 多行业对比：截面命令支持逗号批量
   westock-data sector valuation pt01801780,pt01801080
   westock-data sector forecast pt01801780,pt01801080
   westock-data sector finance pt01801780,pt01801080
6. 输出：基本面→估值→预期三段分析，指出增速与估值是否匹配

> **职责边界**：`sector oper` = 行业经营指标（产量/库存等，传行业中文名）；`sector finance/valuation/forecast` = 申万行业财报/估值/一致预期（传 pt 代码）。
```

### 3.7 行业板块行情分析

```
用户："最近哪些行业板块涨得好？资金在流向哪里？"

AI 步骤：
1. 查询板块行情榜：westock-data sector ranking
2. 直接基于格式化输出，输出行业板块资金面和涨幅分析
```

---

## 四、研究（评分/评级/预期/研报）

> 命令：`score` `rating` `consensus` `report`

### 4.1 机构评级与一致预期分析

```
用户："看看茅台的机构评级和一致预期"

AI 步骤：
1. 搜索股票：westock-data search 贵州茅台 → sh600519
2. 查询评级数据：westock-data rating sh600519
   → 解析机构评级分布（买入/增持/中性/减持/卖出）
3. 查询一致预期：westock-data consensus sh600519
   → 解析 EPS/净利润/营收的一致预期值和增长率
4. 查询评分：westock-data score sh600519
   → 解析综合评分、细分维度评分
5. 输出机构研究综合报告
```

### 4.2 研报查询

```
用户："看看最近有哪些关于茅台的研报"

AI 步骤：
1. 搜索股票：westock-data search 贵州茅台 → sh600519
2. 查询研报列表：westock-data report list sh600519 --limit 10
   → 解析研报标题、机构、分析师、评级、发布时间
   → 解析核心观点、投资建议、目标价
4. 输出研报摘要和核心观点
```

---

## 五、事件（风险事件/投资日历/停复牌）

> 命令：`risk` `calendar` `suspension`

### 5.1 投资日历查询

```
用户："本周有哪些重要的财经事件？"

AI 步骤：
1. 查询有事件的日期：westock-data calendar
   → 格式化输出月历视图，★ 标记有事件的日期
2. 从月历中筛选本周日期
3. 逐日查询事件详情：westock-data calendar 2026-03-10 --limit 30
   → 格式化输出事件列表（按重要性排序），含星级、时间、国家、内容、前值/预测/实际值
4. 可按地区筛选：westock-data calendar 2026-03-10 --limit 30 --market hs
5. 可按指标筛选：westock-data calendar 2026-03-10 --limit 30 --market hs --indicator 1
6. 直接基于格式化输出，输出本周财经事件日历
```

### 5.3 风险细查（risk）

```
用户："看看 sh600519 有没有质押风险"

AI 步骤：
1. 查询风险明细：westock-data risk sh600519 --types pledge,unlock
2. 解析质押率 / 解禁规模 / 解禁日期
3. 输出风险细节
```
用户："看看 sh600519 有没有质押风险"

AI 步骤：
2. 若含质押/解禁标签，用 risk 钻取明细：
   westock-data risk sh600519 --types pledge,unlock
3. 解析质押率（已修复 100 倍单位错误）/ 解禁规模 / 解禁日期
4. 输出风险细节
```

### 5.4 高管变动 / 增减持 / 评级变动监控（risk 新类型）

```
用户："最近哪些高管在减持茅台"

AI 步骤：
1. 拉取高管增减持明细：westock-data risk sh600519 --types executivetransfer
   （别名 executive 也可：--types executive）
2. 解析每条增减持记录：高管姓名、变动数量、变动方向、变动后持股
3. 输出增减持汇总
```

```
其他新增 risk 类型：
- westock-data risk <code> --types leaderchange     # 高管变动（任免）
- westock-data risk <code> --types bondrating       # 评级信息（如 AAA/AA+）
```

---

## 六、公告（公告原文）

> 命令：`notice list/detail`

### 6.1 公告全文查询

```
用户："查看贵州茅台最近的财务公告内容"

AI 步骤：
1. 搜索股票：westock-data search 贵州茅台 → sh600519
2. 查询公告列表：westock-data notice list sh600519 --type 1
3. 从列表中获取公告ID（如 nos1224809143）
4. 查询公告内容：westock-data notice detail nos1224809143
   → 格式化输出标题、发布时间、关联股票、相关链接（PDF/原文/翻译），A股/北交所直接展示正文内容，港股/美股展示PDF下载链接
5. 直接基于格式化输出，输出公告内容摘要
```

## 七、资金（二级市场资金）

> 命令：`fund flow` / `fund short` / `fund margin` / `fund block` / `fund north-holding`

### 7.1 批量资金流向分析

```
用户："对比腾讯和美团的资金流向"
→ westock-data fund flow hk00700,hk03690 --date 2026-03-10 → 一次查询两只 → 解析批量查询结果 → 对比资金面
```

### 7.2 A股资金流向分析

```
用户："分析中芯国际的资金面"
→ westock-data fund flow sh688981 → 解析 MainNetFlow/JumboNetFlow → 输出资金面判断
```

### 7.3 港股资金与卖空分析

```
用户："腾讯控股的资金流向情况"
→ westock-data fund flow hk00700 → 解析 TotalNetFlow/MainNetFlow/RetailNetFlow → 输出资金分析

用户："腾讯控股的卖空情况如何"
→ westock-data fund short hk00700 → 解析 ShortShares/ShortAmount/ShortRatio → 卖空比率>15%需关注
```

### 7.4 美股卖空数据分析

```
用户："苹果公司的卖空情况"
→ westock-data fund short usAAPL → 解析 ShortRatio/ShortShares/ShortRecoverDays → ShortRatio>10%或ShortRecoverDays>5天需关注
```

### 7.5 北向持仓查询

```
用户："贵州茅台北向资金持仓情况怎么样？"
→ westock-data fund north-holding sh600519
→ 解析最新季 + 次新季：HoldingCap/HoldingRatio/HoldingShares/CapChgQ/CapChgY
→ 输出季度对比表（持股市值、持股比例、季年变动）

用户："电子行业北向持仓分布如何？"
→ 若用户未给代码：westock-data search 电子 --type sector → 取板块代码
→ westock-data fund north-holding pt01801080
→ 解析 HoldingCap/CapChgQ/CapChgY
→ 注意：仅支持申万行业，概念/地域板块不支持

用户："今天北向成交最活跃的股票有哪些？"
→ 不在本 Skill：改用 westock-tool ranking north_active_d（固定 Top20 日榜）
```

---

## 八、简况（公司基本信息/股东/分红/回购）

> 命令：`profile` `shareholder` `dividend list/calendar` `buyback`

### 8.1 分红数据查询

```
用户："贵州茅台的分红情况如何？"
→ westock-data search 贵州茅台 → 获取 sh600519
→ westock-data dividend list sh600519 → 解析分红明细（reportEndDate, dividendPlan, cashDiviRMB 等）
→ 输出分红情况分析
```

### 8.2 跨市场分红历史对比

```
用户："对比腾讯和苹果近3年的分红记录"
→ westock-data dividend list hk00700,usAAPL --years 3
→ 解析批量查询结果 中各股票的 plans[]
→ 注意货币差异：港股 cashDivPerShare（港元）、美股 dividend（美元）
→ 输出跨市场分红对比分析
```

### 8.3 A股分红历史查询

```
用户："查看贵州茅台近5年的分红记录"

AI 步骤：
1. 搜索股票：westock-data search 贵州茅台 → sh600519
2. 查询分红历史：westock-data dividend list sh600519 --years 5
3. 解析 plans[] 中的分红方案（reportEndDate, cashDiviRMB, dividendPlan）
4. 注意：A股分红数据为"每10股派息"（cashDiviRMB）
5. 分析每年分红趋势（分红金额、分红频次、股利支付率变化）
6. 输出分红历史趋势分析
```

### 8.4 港股分红历史查询

```
用户："查看腾讯近几年的分红记录"

AI 步骤：
1. 查询分红历史：westock-data dividend list hk00700 --years 5
2. 解析 plans[] 中的分红方案
3. 分析每年分红趋势（每股派息、合计派现、分红频次）
4. 输出分红历史趋势分析
```

### 8.5 分红历史自定义年数

```
用户："查看苹果近10年的分红记录"

AI 步骤：
1. 查询分红历史：westock-data dividend list usAAPL --years 10
2. 解析 plans[] 中的分红方案
3. 分析美股季度分红特征（每季度分红金额、年度累计）
4. 注意：美股可能包含 splitInfo（拆合股信息）
5. 输出长期分红趋势分析
```

### 8.6 跨市场分红历史对比

```
用户："对比贵州茅台、腾讯和苹果近3年的分红情况"

AI 步骤：
1. 批量查询分红历史：westock-data dividend list sh600519,hk00700,usAAPL --years 3
2. 解析批量查询结果 中各股票的 plans[]
3. 注意各市场数据格式差异：
   - A股：cashDiviRMB（每10股派息，元）
   - 港股：cashDivPerShare（每股派息，港元）
   - 美股：dividend（每股分红，美元）
4. 统一换算为每股派息金额进行对比
5. 输出跨市场分红对比分析
```

### 8.7 分红除权日查询

```
用户："苹果什么时候除权派息？"

AI 步骤：
1. 搜索股票：westock-data search 苹果 → usAAPL
2. 查询分红历史：westock-data dividend list usAAPL --years 5
3. 解析 plans[] 中的除权日列表
4. 展示每次的除权日、支付日、每股分红
5. 输出分红除权日历
```

### 8.8 股东研究分析

```
用户："查一下茅台的十大股东"

AI 步骤：
1. 搜索股票：westock-data search 贵州茅台 → sh600519
2. 查询股东数据：westock-data shareholder sh600519
3. 解析 top10Shareholders（十大股东）和 top10FloatShareholders（十大流通股东）
4. 解析 shareholderNum（股东户数）→ 总户数/A股户数/环比变动/户均持股
5. 分析持股集中度、机构/个人占比、持股变动趋势
6. 输出股东结构分析报告
```

### 8.9 港股股东与机构持仓分析

```
用户："腾讯的机构持仓情况怎么样？"

AI 步骤：
1. 查询股东数据：westock-data shareholder hk00700
2. 解析 shareholderInfo（持股股东）→ 主要股东持股比例
3. 解析 shareholderDist（股东分布）→ 各类机构持股情况
4. 解析 instHoldingStats（机构持仓统计）→ 机构数量变化、增减持趋势
5. 输出机构持仓分析
```

### 8.10 公司回购查询

```
用户："查看小米最近的回购情况"

AI 步骤：
1. 搜索股票：westock-data search 小米集团 → hk01810
2. 查询回购数据：westock-data buyback hk01810
3. 解析回购明细：日期、回购股份、回购金额、回购均价
4. 计算累计回购金额、平均回购价格
5. 输出回购分析
```

---

## 九、财务（三大报表/财报披露日历）

> 命令：`finance` `disclosure`

### finance 能力速查

- `finance <代码>` / `finance <代码1>,<代码2>`：默认三大报表（`income` + `balance` + `cashflow`），支持 `--num` 或 `--start` / `--end`
- `finance <代码> --type income|balance|cashflow`：仅拉指定单表

### 9.1 财务分析

```
用户："分析贵州茅台的盈利能力"
→ westock-data finance sh600519 → 提取关键指标 → 计算同比/环比 → 输出分析结论
```

### 9.2 多股财报对比（三大表）

```
用户："对比小米和腾讯的财报"
→ westock-data finance hk01810,hk00700 --num 1
→ 解析批量三大表 → 输出对比分析
```

### 9.3 单表多期对比

```
用户："看看浦发银行和招商银行最近4期的利润表"
→ westock-data finance sh600000,sh600036 --type income --num 4
→ 解析批量查询结果 → 提取各期营收、净利润、毛利率
→ 计算同比/环比增长率 → 输出两家银行盈利能力对比

用户："查看腾讯最近4期的综合损益表"
→ westock-data finance hk00700 --type income --num 4
```

### 9.4 财报披露日查询

```
用户："茅台什么时候发财报？"

AI 步骤：
1. 搜索股票：westock-data search 贵州茅台 → sh600519
2. 查询财报披露日历：westock-data disclosure sh600519
3. 解析 items[] 中的披露日列表
4. 区分已披露和预约披露日期
5. 输出最近的财报披露日历
```

---

## 十、ETF（ETF 全维度）

> 命令：`etf detail/holdings/nav/company/holders/financial`

### 10.1 ETF 全景分析

```
用户："分析一下沪深300ETF的基本情况"

AI 步骤：
1. 搜索 ETF：westock-data search 沪深300ETF --type etf → sh510300
2. 查询 ETF 详情：westock-data etf detail sh510300
3. 解析基本信息：类别、成立日期、管理人、托管人、跟踪指数
4. 解析 classification（4 级详细分类）：资产类别 / 投资风格 / 细分领域 / 具体方向 / 跟踪标的
5. 解析 managerHistory（基金经理历史）：当前在任 / 首任 / 任职最长 / 全部历任
6. 解析费用：认购费率、管理费率、托管费率、销售服务费
7. 解析净值/规模：单位净值、溢折率、规模、份额、净申购
8. 解析收益：今年以来、近1月/3月/6月/1年/3年收益率
9. 解析回撤：最大回撤指标
10. 输出 ETF 全景分析报告
```

### 10.2 ETF 持仓分析

```
用户："沪深300ETF的重仓股有哪些？"

AI 步骤：
1. 搜索 ETF：westock-data search 沪深300ETF --type etf → sh510300
2. 查询 ETF 详情：westock-data etf detail sh510300
3. 解析 topStockChanges（重仓股票涨跌幅）→ 股票代码、名称、占比、涨跌幅、较上期变化
4. 解析 holdings（持仓明细）→ 完整持仓列表
5. 分析持仓集中度、行业分布、重仓股涨跌表现
6. 输出 ETF 持仓分析
```

### 10.3 ETF 净值趋势分析

```
用户："沪深300ETF近一个月净值走势如何？"

AI 步骤：
1. 搜索 ETF：westock-data search 沪深300ETF --type etf → sh510300
2. 查询净值历史：westock-data etf nav sh510300 --start 2026-02-10 --end 2026-03-10
3. 解析每日净值、涨跌幅
4. 计算区间收益率、最大回撤
5. 输出净值趋势分析
```

### 10.4 ETF 费用对比

```
用户："对比沪深300ETF和创业板ETF的费用"

AI 步骤：
1. 搜索 ETF：westock-data search 沪深300ETF --type etf → sh510300
2. 搜索 ETF：westock-data search 创业板ETF --type etf → sz159915
3. 批量查询详情：westock-data etf detail sh510300,sz159915
4. 对比费用：认购费率、管理费率、托管费率、销售服务费
5. 对比规模、份额、流动性
6. 输出 ETF 费用对比分析
```

### 10.5 ETF 溢折率分析

```
用户："分析一下沪深300ETF的溢折率情况"

AI 步骤：
1. 查询 ETF 详情：westock-data etf detail sh510300
2. 解析 disc（溢折率）、discountRatioCurve（溢折率曲线）、avgDiscountRatioCurve（同指数平均溢折率）
3. 判断溢价/折价程度及与同类 ETF 的对比
4. 输出溢折率分析
```

### 10.6 ETF 基金经理稳定性分析

```
用户："沪深300ETF的基金经理稳定吗？历任都有谁？"

AI 步骤：
1. 查询 ETF 详情：westock-data etf detail sh510300
2. 解析 managerHistory：
   - current（当前在任）：与 first（首任）一致 → 经理"超长稳定"
   - longest（任职最长）数组里的人是否仍在 current 内 → 老将仍在岗
   - history（全部历任）数量 → 历任更换次数（少 = 稳定，多 = 频繁更换）
3. 结合 managers 数组（含 intro / experienceYears / returnDuringTenure）补充任职履历和任内回报
4. 输出经理稳定性结论（如"自成立以来仅 1 任经理，柳军任职超 12 年"）
```

---

## 十二、宏观（宏观指标）

> 命令：`macro list/indicator`

### 12.1 查看最新核心宏观指标

```
用户："当前宏观经济面怎么样？"

AI 步骤：
1. 查询最新核心宏观指标：westock-data macro indicator cn_core
2. 解析返回的各项核心指标数据（会自动返回 p1 和 p2 两个数据集）
3. 从 GDP 增速、CPI/PPI、PMI、社融、M2 等维度综合分析
4. 输出宏观经济面全景概览
```

### 12.2 PMI 趋势分析

```
用户："看看最近半年PMI走势"

AI 步骤：
1. 查询 PMI 区间数据：westock-data macro indicator cn_pmi --start 2024 --end 2025
2. 提取每月 PMI 数值（制造业/非制造业/综合）
3. 分析 PMI 是否连续处于荣枯线（50）以上
4. 结合子项（新订单、生产、就业等）分析经济景气度变化
5. 输出 PMI 趋势分析报告
```

### 12.3 GDP 全景分析

```
用户："分析一下最新的GDP数据"

AI 步骤：
1. 查询全部 GDP 相关指标：westock-data macro indicator cn_gdp,cn_cpi_ppi,cn_consumption,cn_investment --year 2025
2. 解析 GDP 增速（实际 vs 名义）
3. 分析 CPI/PPI 价格走势（通胀/通缩信号）
4. 分析消费和投资数据（内需强弱）
5. 输出 GDP 多维度分析报告
```

### 12.4 货币政策环境判断

```
用户："当前货币政策环境如何？"

AI 步骤：
1. 查询货币指标：westock-data macro indicator cn_financing,cn_fundquantity,cn_fundcost --year 2025
2. 分析社融规模（financing）→ 实体经济融资需求
3. 分析 M1/M2 增速（fundquantity）→ 货币供应宽松度
4. 分析利率水平（fundcost）→ 资金成本变化
5. 综合判断货币政策取向（宽松/中性/偏紧）
6. 输出货币政策环境分析
```

### 12.5 宏观数据 + 市场联动分析

```
用户："PMI下滑对A股有什么影响？"

AI 步骤：
1. 查询 PMI 趋势：westock-data macro indicator cn_pmi --start 2024 --end 2025
3. 对比 PMI 走势与指数走势的相关性
4. 分析 PMI 下行期间哪些板块受影响更大
5. 输出宏观-市场联动分析
```

### 12.6 通胀全景 + CPI/PPI 剪刀差

```
用户："最近通胀压力怎么样？"/"CPI和PPI差距说明什么？"

AI 步骤：
1. 查询价格指标：westock-data macro indicator cn_cpi_ppi --start 2024 --end 2025
2. 关注核心指标：
   - CPI_YOY（CPI 同比）vs CPI_YOY_CORE（核心 CPI，剔除食品和能源）
   - PPI_YOY（PPI 同比）、PPIRM_YOY（购进价格）
   - PRICE_SCISSORS_CPI_PPI（CPI-PPI 剪刀差）、PRICE_SCISSORS_PPI_PPIRM（PPI-PPIRM 剪刀差）
3. 专业研判：
   - CPI 上升 + 核心 CPI 平稳 → 食品/能源驱动型通胀（暂时性）
   - CPI > PPI（剪刀差为正）→ 下游议价能力强，消费类利润扩张
   - CPI < PPI（剪刀差为负）→ 上游成本压力，下游利润受挤压
   - PPI > PPIRM → 制造业利润率改善
4. 拆分分项：CPI_YOY_FOOD（食品）/ CPI_YOY_NON_FOOD（非食品）/ PPI_YOY_PRODUCE（生产资料）/ PPI_YOY_LIVE（生活资料）
5. 输出通胀压力评估 + 板块影响（消费/上游资源/中游制造）
```

### 12.7 国债收益率曲线与期限结构分析

```
用户："看看国债收益率曲线"/"长短端利差怎么样？"/"是牛陡还是熊平？"

AI 步骤：
1. 查询收益率曲线：westock-data macro indicator cn_yield_curve --year 2025
2. 查询期限利差与曲线形态：westock-data macro indicator cn_term_spread --date <最新>
3. 关注核心字段：
   - YTM_YIELD_2Y / 5Y / 10Y / 30Y（关键期限点位）
   - Yield10Y / Yield2Y、TermSpread（10Y-2Y 期限利差，bps）
   - CurveFormD/W/M/Q/Y（日/周/月/季/年形态：牛陡/牛平/熊陡/熊平）
   - LongDifD/W/M/Q/Y、ShortDifD/W/M/Q/Y（长短端多周期变动）
4. 形态语义：
   - **牛陡**（短端下行更快）→ 货币宽松预期、降息周期初期
   - **牛平**（长端下行更快）→ 经济衰退预期、避险买长债
   - **熊陡**（长端上行更快）→ 经济复苏 / 通胀预期上升
   - **熊平**（短端上行更快）→ 流动性收紧、加息周期
5. 期限利差判断：
   - 利差扩大（陡峭化）→ 经济预期改善
   - 利差收窄甚至倒挂 → 衰退信号（参考美债经验）
6. 输出曲线形态判断 + 货币政策含义 + 大类资产建议
```

### 12.8 股债性价比（风险溢价）与大类资产配置

```
用户："现在股票贵不贵？"/"股债怎么选？"/"红利股有性价比吗？"

AI 步骤：
1. 查询溢价率最新水平：westock-data macro indicator cn_premium_value --date <最新>
2. 查询溢价率历史曲线（约 2400 条日频）：westock-data macro indicator cn_premium_curve --date <最新>
3. 关注核心字段：
   - DividendPremium（红利溢价率：股息率 - 10Y 国债收益率）
   - EquityPremium（股债溢价率：1/PE - 10Y 国债收益率）
   - DprPct10Y / EprPct10Y（过去 10 年历史百分位）
4. 专业研判：
   - 股债溢价率 10Y 分位 > 80% → 股票相对债券极具吸引力（市场底部信号）
   - 股债溢价率 10Y 分位 < 20% → 股票相对债券偏贵（市场高估区）
   - 红利溢价率 10Y 分位 > 80% → 红利策略性价比高，适合配置高股息蓝筹
   - 红利溢价率持续走高 → 资金"避险"特征，关注银行/煤炭/电力/运营商
5. 历史曲线趋势：
   - 拐点识别：从历史高位回落 → 风险资产开始反攻
   - 持续走低 → 警惕股票泡沫，债券吸引力上升
6. 输出大类资产配置建议（股 vs 债 vs 红利）
```

### 12.9 流动性投放与货币市场利率

```
用户："央行最近在投放还是回笼？"/"MLF 利率怎么走？"

AI 步骤：
1. 查询公开市场操作 MLF：westock-data macro indicator cn_mlf --year 2025
2. 查询货币市场利率：westock-data macro indicator cn_fundcost --year 2025
3. 关注核心字段：
   - MLF_OPERATION_3M / 6M / 1Y（不同期限操作金额）
   - MLF_BALANCE_MONTH（月末余额）、MLF_DUE（到期量）、MLF_NET_INJECTION（净投放）
   - SHIBOR_OVERNIGHT / 1W / 1M / 3M / 1Y（同业拆借利率）
   - FDR007 / FR007（银行间回购定盘利率）
4. 专业研判：
   - MLF 净投放为正 + 短端利率下行 → 流动性宽松
   - MLF 净回笼 + SHIBOR 上行 → 流动性边际收紧
   - MLF 操作以 1Y 为主 → 央行引导中长期利率下行
   - SHIBOR 1Y 与 MLF 利差走扩 → 银行负债成本压力
5. 政策信号：
   - MLF 续作量 > 到期量 → 呵护流动性
   - 1Y MLF 利率下调 → 引导 LPR 下调，传导至实体融资成本
6. 输出货币政策操作意图 + 流动性松紧度评估
```

### 12.10 工业景气全景（5 维交叉验证）

```
用户："工业经济好不好？"/"看看制造业景气度"

AI 步骤：
1. 并行查询 5 个工业相关指标：
   - westock-data macro indicator cn_profit,cn_valueadded,cn_prosperity,cn_capacity_utilization,cn_power_consumption --year 2025
2. 关键字段交叉验证：
   - **量**：IAV_CUM_YOY（工业增加值累计同比）+ POWERUSE_ELEC_YTD_YOY（用电量累计同比）
   - **效**：ENTERPRISE_PROFIT_CUM_YOY（工业企业利润累计同比）
   - **能**：CAPU_CAPU（产能利用率）+ CAPU_CAPU_MFG（制造业产能利用率）
   - **景气**：ENT_BOOM_IDX_Q（企业景气指数）+ ENT_EXP_BOOM_IDX_Q（预期景气指数）
3. 行业分项对比：
   - 高景气：观察 IAV_CUM_YOY_HIGH_TEC（高技术）、IAV_CUM_YOY_TMT（电子）
   - 周期回暖：黑色金属（FERR）、有色金属（NFERR）、化工（CHEM）的产能利用率与利润同步走高
   - 需求验证：相关产品产量（如 PROD_OUT_STEEL_YOY 钢材产量、PROD_OUT_AUTO_YOY 汽车）
4. 专业研判：
   - 工业增加值 ↑ + 用电量 ↑ + 产能利用率 ↑ → 真实复苏（量价齐升）
   - 利润 ↑ 但产能利用率 ↓ → 价格驱动型（警惕涨价不可持续）
   - 当期景气 vs 预期景气背离 → 拐点信号
5. 输出工业景气评分 + 高景气子行业清单
```

### 12.11 财政发力强度评估

```
用户："今年财政力度怎么样？"/"专项债发了多少？"

AI 步骤：
1. 查询财政指标：westock-data macro indicator cn_fiscal --year 2025
2. 关注三大维度：
   - **收入端**：FISCAL_PUB_REV_YTD_YOY（公共预算收入累计同比）+ 税种结构
     - FISCAL_REV_TAX_VAT_YTD_YOY（增值税）→ 经济活跃度
     - FISCAL_REV_TAX_CIT_YTD_YOY（企业所得税）→ 企业盈利
     - FISCAL_REV_TAX_PIT_YTD_YOY（个人所得税）→ 居民收入
     - FISCAL_REV_TAX_SEC_YTD_YOY（证券交易印花税）→ 资本市场活跃度
   - **支出端**：FISCAL_PUB_EXP_YTD_YOY（公共预算支出累计同比）+ 重点领域
     - 民生：教育/医疗/社保（FISCAL_EXP_EDU/MED/SS_YTD_YOY）
     - 基建：交通/城乡（FISCAL_EXP_TRANS/URB_YTD_YOY）
     - 科创：科技（FISCAL_EXP_TECH_YTD_YOY）
   - **债务端**：FISCAL_LGB_ISS_YTD（地方债发行累计）+ FISCAL_LGB_SPC_ISS_YTD（专项债累计）
3. 政策研判：
   - 支出增速 > 收入增速 → 财政积极
   - 专项债前置发行（上半年发行进度高）→ 稳增长意图明确
   - FISCAL_DEFICIT_PRG_YTD（赤字进度）> 历年同期 → 财政力度加码
4. 板块联动：
   - 专项债加速 → 基建（建材/建筑）
   - 教育/医疗支出加速 → 教育/医药板块
   - 科技支出加速 → TMT/高端制造
5. 输出财政政策力度评估 + 受益板块
```

### 12.12 进出口数据深度解读

```
用户："出口怎么样？"/"贸易顺差是多少？"

AI 步骤：
1. 查询进出口指标：westock-data macro indicator cn_export --year 2025
2. 查询出口交货值（行业分项）：westock-data macro indicator cn_export_value --year 2025
3. 关注核心字段：
   - EXP_BALANCE_GOODS_SUM_CUM（货物贸易差额累计）
   - EXP_BAL_GOODS_SVC_SUM_CUM（货物+服务贸易差额）
   - EXP_EX_RESERVES_MONTHLY（外汇储备）/ EXP_GOLD_RESERVES_MONTHLY（黄金储备）
   - EDV_EDV_*_YTD_YOY（各行业出口交货值累计同比）
4. 行业出口结构：
   - 传统：纺织（TEXTL）/ 服装（APRL）/ 家具（FURN）
   - 中端制造：通用设备（GNEQ）/ 专用设备（SPEQ）/ 汽车（AUTO）
   - 高端：电气机械（ELEC）/ 电子信息（ICT）/ 仪器仪表（INSTR）
5. 专业研判：
   - 贸易顺差扩大 + 外汇储备稳定 → 国际收支健康
   - 高技术出口（ICT/ELEC）增速 > 传统（TEXTL）→ 出口结构升级
   - 服务贸易逆差收窄（旅行/运输）→ 内需复苏不及预期
   - 黄金储备增加 → 外汇储备多元化（去美元化趋势）
6. 输出出口景气度 + 受益出口链板块（机械/汽车/电子）
```

### 12.13 居民收入与消费分析（内需根基）

```
用户："老百姓收入涨了吗？"/"消费为什么疲软？"

AI 步骤：
1. 查询可支配收入：westock-data macro indicator cn_disposable_income --year 2025
2. 查询消费指标：westock-data macro indicator cn_consumption --year 2025
3. 关注核心字段：
   - PERCAP_DISP_INC_YTD_YOY（人均可支配收入累计同比）
   - PERCAP_DISP_INC_REAL_YTD_YOY（实际累计同比，剔除通胀）
   - PERCAP_DISP_INC_MED_YTD_YOY（中位数同比，反映分配公平度）
   - 收入结构：工资（WAGE）/ 经营（BIZ）/ 财产（PROP）/ 转移（TRSF）
   - PERCAP_CONS_EXP_YTD_YOY（人均消费支出同比）
   - 消费分项：食品（FOOD）/ 居住（HOUS）/ 交通通信（COMM）/ 教育文化娱乐（EDUC）/ 医疗（HLTH）
   - CONSUMP_CUR_YOY（社零当期同比）+ 各品类（汽车/化妆品/金银珠宝/家电...）
4. 专业研判：
   - 名义收入增速 > 实际收入增速差距 = 通胀侵蚀
   - 中位数增速 < 平均数增速 → 收入分化加剧
   - 工资性收入主导 → 就业稳定；财产性收入跌 → 资产价格压力
   - 消费/收入弹性：消费增速远低于收入 → 预防性储蓄上升（消费意愿弱）
   - 必选消费（食品/医疗）韧性 vs 可选消费（化妆品/金银珠宝）疲软 → 消费降级
5. 输出消费景气评估 + 受益板块（必选 vs 可选 vs 服务消费）
```

### 12.14 就业市场（含百度搜索指数高频）

```
用户："就业形势怎么样？"/"年轻人失业率高吗？"

AI 步骤：
1. 查询就业指标：westock-data macro indicator cn_employment --year 2025
2. 关注核心字段：
   - EMPLOY_UNEMP（城镇调查失业率）+ 同比 EMPLOY_UNEMP_YOY
   - 分年龄：EMPLOY_UNEMP_16_24（青年）/ 25_29 / 30_59
   - 分户籍：EMPLOY_UNEMP_MIGR（外来）/ EMPLOY_UNEMP_RURAL_MIGR（农民工）
   - EMPLOY_AVG_WORKHRS（周工作时长，反映用工密度）
   - EMPLOY_NEW_EMP_YTD_YOY（新增就业累计同比）
   - **高频先行指标**：百度搜索指数 EMPLOY_BDI_JOBSEEK（找工作）/ BDI_RECRUIT（招聘）/ BDI_UNEMP（失业）
3. 专业研判：
   - 16-24 岁失业率 > 整体失业率 2 倍 → 结构性失业（青年就业难）
   - 工作时长 < 47 小时 → 用工不足，警惕裁员
   - 新增就业累计同比转负 → 就业市场恶化
   - 百度搜索"找工作"指数大幅上升、"招聘"指数下降 → 求职难度加大（高频领先信号）
   - 农民工失业率 > 户籍失业率 → 灵活就业承压
4. 政策含义：
   - 失业率破阈值（5.5%/年青）→ 稳就业政策加码概率上升
   - 就业恶化 + 消费疲软 → 政策刺激窗口
5. 输出就业景气评估 + 政策预期
```

### 12.15 宏观日历驱动的事件预案

```
用户："最近有什么重要数据要公布？"/"下周经济数据怎么预期？"

AI 步骤：
1. 查询未来宏观日历：westock-data macro indicator cn_calendar_future --date <今天>
2. 查询历史宏观日历（参考过往同类事件反应）：westock-data macro indicator cn_calendar_hist --year 2025
3. 查询机构预测：westock-data macro indicator cn_forecast --year 2025
4. 关注核心字段：
   - calendar_future：EventDate / EventType / EventDesc / Importance / ForecastValue / PreviousValue
   - forecast：FORECAST_GDP_FC_YOY / FORECAST_CPI_FC_YOY / FORECAST_PMI_FC / FORECAST_M2_FC_YOY 等机构一致预期
5. 专业研判（事件驱动框架）：
   - **数据公布前**：当前实际值 vs 机构预测值 → 预期差大小
   - **重要程度筛选**：Importance 高的事件（PMI / CPI / 社融 / 非农等）→ 重点关注
   - **事件分类**：
     - 经济数据（PMI/CPI/PPI/工业数据）→ 影响周期股
     - 央行操作（MLF/LPR/降准）→ 影响金融股、债市
     - 财政数据（财政收支/专项债）→ 影响基建链
   - **历史反应**：用 calendar_hist 找最近 3-5 次同类事件公布后市场反应（指数涨跌、板块轮动）
6. 输出事件清单 + 预期差判断 + 板块预案：
   - 公布前布局：预测值好于历史 → 提前布局相关板块
   - 公布后策略：实际值大幅偏离预测（>1 标准差）→ 短期波动加大，等待方向确认
```

### 12.16 中国专项指标（LPR / 财新 PMI / 装机容量）

```
用户："LPR 最近调整了吗？"/"财新 PMI 最新值？"/"风电光伏装机什么节奏？"

AI 步骤：
1. 一次性拉三个专项：westock-data macro indicator cn_lpr,cn_caixin_pmi,cn_installed_capacity --date <今天>
2. 关注：
   - cn_lpr：1Y/5Y LPR 当日值 vs 前值（看 ActualValue/FormerValue 列）
   - cn_caixin_pmi：财新制造业/服务业 PMI（与官方 PMI 互证；财新更偏中小企业）
   - cn_installed_capacity：发电装机容量（火电/水电/核电/风电/光伏 装机）
3. 与中国专项指标的"高频补充"价值：
   - LPR 是货币政策直接指标（实时影响利率敏感板块：地产/银行/消费）
   - 财新 PMI 与官方 PMI 分歧时往往揭示"中小企业 vs 大型央企"景气度差异
   - 装机容量映射新能源行业景气与"双碳"政策落地节奏
```

### 12.17 美股 / 港股 / 日本 / 欧元区 主题宏观（事件日历型）

```
用户："美国非农数据最新预期？"/"美联储加息节奏？"/"日本央行政策动向？"/"欧元区通胀压力？"

AI 步骤：
1. 一键拉某 region 全套：westock-data macro indicator --region us --date <今天>
   - 8 个主题：us_employment / us_eco_growth / us_inflation / us_confidence / us_monetary / us_fiscal / us_energy / us_realestate
2. 单主题精查：
   - westock-data macro indicator us_employment --date <今天>     # 美国就业
   - westock-data macro indicator us_inflation --date <今天>       # 美国通胀（CPI/PPI/核心 CPI）
   - westock-data macro indicator us_monetary --date <今天>        # 美联储利率/资产负债表
   - westock-data macro indicator jp_monetary --date <今天>        # 日本央行
   - westock-data macro indicator eu_inflation --date <今天>       # 欧元区通胀
3. 关注字段（统一 schema）：
   - IndicatorName：指标名（如"美国 5 月非农就业人口"）
   - OccurDate / OccurTime：发布日期与时间
   - ActualValue / ForecastValue / FormerValue：实际值/市场预测/前值
4. 专业研判：
   - 数据公布前：观察预测值（市场一致预期）
   - 公布后：实际 vs 预测 → 预期差驱动美元/美债/A 股短期联动
   - 美联储/ECB/BoJ 政策窗口前后关注 us_monetary/eu_monetary/jp_monetary 主题
```

### 12.18 海外预期日历（按地区 iso3，36 个地区）

```
用户："看看中国财经日历明年的关键事件"/"美国今年都公布了哪些重要数据？"

AI 步骤：
1. 列地区代码：westock-data macro expect list（共 36 个地区）
2. 单地区按年查：
   - westock-data macro expect --area chn --year 2025         # 中国
   - westock-data macro expect --area usa --year 2025         # 美国
   - westock-data macro expect --area jpn --year 2025         # 日本
3. 区间查询（多年趋势）：westock-data macro expect --area usa --start 2023 --end 2025
4. 关注字段（比 us_/jp_ 等主题型多一列 Importance）：
   - Importance：1=低 / 2=中 / 3=高（用于筛选重要事件）
5. 与 macro indicator 主题型差异：
   - 主题型：按 region 分主题切片（就业/通胀/货币...），适合"看美国通胀近期"
   - 海外预期：按地区分单地区全套日历，适合"看某地区某年所有重要事件"
```

### 12.19 美联储降息预期跟踪（投资视角）

```
用户："美联储最近会不会降息？"/"市场对下次 FOMC 会议的利率预期？"

AI 步骤：
1. 查询美联储利率历史 + FFR 预期：westock-data macro indicator us_monetary --date <今天>
   - 联邦基金利率目标上下限（当前/前值）
   - FFR 预期-当前年度 / 后面第 1/2/3 年 / 长期（点阵图含义）
2. 查询未来 FOMC 会议市场一致预期：westock-data macro expect --area usa --year <当年>
   - 筛 IndicatorName 含"联邦基金利率"的事件，看 ForecastValue
3. 三栏对比识别预期偏移：ActualValue（实际）vs ForecastValue（预测）vs FormerValue（前值）
4. 板块映射：
   - 鸽派偏移（降息空间打开）→ 利好成长股（科技/生科）/ 长久期资产（地产 REITs/公用）/ 黄金
   - 鹰派偏移（降息推迟）→ 利好金融股（净息差扩大）/ 价值股
5. 配合 us_inflation 综合判断：通胀粘性 → 降息空间被压缩
```

### 12.20 美国通胀压力多维评估（投资视角）

```
用户："美国通胀压力怎么样？CPI/PCE/PPI 最新数据如何？长期通胀预期上行了吗？"

AI 步骤：
1. 查询美国通胀全套：westock-data macro indicator us_inflation --date <今天>
2. 三层通胀拆解：
   - 当期通胀：CPI 月率/年率、核心 CPI、PCE 月率/年率、核心 PCE 月率/年率（美联储最关注）
   - 上游传导：PPI 月率（超预期跳升 = 上游成本传导风险）、核心 PPI
   - 通胀预期：纽约联储 1 年 / 密歇根大学 1 年 / 密歇根大学 5 年（脱离 2% 锚定 = 警讯）
3. 关键判断逻辑：
   - 核心 PCE 回落 + 通胀预期稳定 → 降息支撑
   - PPI 跳升 + 长期通胀预期上行（>3.5%） → 再通胀风险
4. 板块映射：
   - 通胀粘性高 → 价值股 / 能源 / 必选消费 / 银行
   - 通胀回落 → 长久期成长股 / 利率敏感板块
5. 配合 macro expect --area usa 看下一次 CPI/PPI 公布预期
```

### 12.21 中美宏观对比（跨市场配置）

```
用户："对比一下中美宏观经济基本面"/"中美周期错位还是共振？"

AI 步骤：
1. 并行查询：
   - 美股：westock-data macro indicator --region us --date <今天>（一键 8 主题）
   - 中国：westock-data macro indicator cn_core --date <今天>（一键 7 大核心）
   - 补充：westock-data macro indicator cn_gdp,cn_cpi_ppi,cn_pmi --year <当年>
2. 三维度对比：
   - 增长：us_eco_growth（GDP/工厂订单/营建）vs cn_gdp + cn_pmi
   - 通胀：us_inflation（PCE/CPI/PPI）vs cn_cpi_ppi（CPI/PPI/核心 CPI）
   - 货币：us_monetary（联邦基金利率）vs cn_mlf + cn_fundcost（MLF/SHIBOR/LPR）
3. 周期识别：
   - 美强中弱（美 PMI>50 + 中 PMI<50）→ 美元强势 / 北向流出
   - 双弱 → 全球衰退风险，避险（美债/黄金/日元）
   - 中强美弱 → 人民币升值 / 北向回流 / 新兴市场跑赢
4. 跨市场资产含义：
   - 人民币汇率（USD/CNH）
   - 北向资金净流入趋势
   - A 股相对美股估值（恒生科技 PE vs 纳指 PE / EprPct10Y）
```

### 12.22 港股宏观环境（联系汇率制度下的双重驱动）

```
用户："港股的宏观环境怎么样？"/"香港经济和外储情况？"

AI 步骤：
1. 一键拉港股全套：westock-data macro indicator --region hk --date <今天>
   - hk_eco_growth（GDP/零售）/ hk_export_reserve（贸易/外储）/ hk_monetary（利率）/ hk_others
2. 联系汇率制度核心逻辑：
   - 港币挂钩美元（7.75-7.85 区间），HKMA 货币政策被动跟随美联储
   - 因此 hk_monetary（HIBOR/贴现窗）通常与 us_monetary 联动
3. 双重驱动：
   - 流动性端：受美联储影响（美降息 → 港股流动性宽松 → 估值修复）
   - 基本面端：受中国大陆影响（中国 PMI/出口 → 港股盈利）
4. 推荐组合查询：
   - westock-data macro indicator us_monetary --date <今天>（看美联储路径）
   - westock-data macro indicator cn_pmi --start <去年> --end <当年>（看中国基本面）
5. 板块映射：
   - 美降息 + 中复苏 → 港股双击（互联网科技/地产/银行）
   - 美鹰派 + 中弱 → 港股双杀（避险）
```

### 12.23 全球三大央行流动性对比

```
用户："全球主要央行流动性环境怎么样？"/"美日欧政策路径有什么差异？"

AI 步骤：
1. 并行调用三大央行政策：
   - westock-data macro indicator us_monetary --date <今天>（联邦基金利率 ~3.5-3.75%）
   - westock-data macro indicator jp_monetary --date <今天>（日本央行政策利率 ~0.5%）
   - westock-data macro indicator eu_monetary --date <今天>（ECB 政策利率 ~3-3.5%）
2. 政策方向识别：加息 / 持平 / 降息（看 ActualValue vs FormerValue）
3. 政策分化场景：
   - 美降日加：美日利差收窄 → 日元升值 → Carry trade 平仓 → 全球流动性回流日本
   - 美降欧降：协同宽松 → 全球流动性整体宽松 → 利好风险资产
   - 美鹰其它鸽：美元独强 → 新兴市场承压
4. 跨资产含义：
   - 美元指数（DXY）：三大央行利差驱动
   - 黄金：实际利率（名义利率 - 通胀预期）反向
   - 新兴市场流动性：美元强势→流出，弱势→流入
5. 配合 expect 看未来政策窗口：
   - westock-data macro expect --area usa（FOMC）
   - westock-data macro expect --area jpn（BoJ）
   - westock-data macro expect --area deu（代表欧元区，ECB）
```

---

## 十三、期货（外盘商品/金融期货 + 港股股指期货）

> 命令：`futures detail` + `search --type futures` + `kline`（支持期货代码）

### 13.1 期货行情查询（关键词→代码→行情）

```
用户："现在国际金价多少？"

AI 步骤：
1. 关键词找代码：westock-data search 黄金 --type futures → fuGC（COMEX黄金）
3. 解析最新价、涨跌幅、货币单位（USD）
4. 说明为延时行情（isDelayed），并给出生成时间
```

### 13.2 期货合约资料查询

```
用户："WTI原油期货的合约规格是怎样的？"

AI 步骤：
1. 关键词找代码：westock-data search 原油 --type futures → fuCL（WTI原油，NYMEX）
2. 查询合约资料：westock-data futures detail fuCL
3. 解析交易所、合约规模、货币币种、最小变动单位、交易时间、所在时区
4. 输出合约规格说明
```

---

## 十四、外汇（离岸人民币/主要货币对/美元指数）

> 命令：`forex list` + `search --type forex` + `kline`（支持外汇代码 `fx*`）

### 14.1 外汇行情查询（关键词→代码→行情）

```
用户："离岸人民币现在多少？"

AI 步骤：
1. 关键词找代码：westock-data search 离岸 --type forex → fxCNH（离岸人民币）
3. 解析最新价、涨跌幅
4. 给出生成时间
```

### 14.2 外汇走势查询（K线/分时）

```
用户："美元日元近一个月走势如何？"

AI 步骤：
1. 关键词找代码：westock-data search 美元日元 --type forex → fxUSDJPY
2. 查询日K：westock-data kline fxUSDJPY --period day --limit 30
3. 解析区间高低点、涨跌幅，描述趋势
4. 提示：外汇仅提供当日分时（minute），不支持五日分时
```

---

## 十五、债券（可转债 / 可交换债）

> 命令：`kline`（支持可转债代码 沪 `sh11xxxx`/`sh13xxxx`、深 `sz12xxxx`）+ `bond detail`（发行要素/条款/现金流）

### 15.1 可转债行情查询（价格 + 转债维度）

```
用户："兴业转债现在行情怎么样？转股价值和溢价率高不高？"

AI 步骤：
   （可转债走专属字段集，除价格/成交外额外返回转债维度，单只竖排「项目/内容」表展示）
2. 解析通用字段：最新价、涨跌幅、成交额
3. 解析转债维度：转股价值（bond_equity_value）、转股溢价率（bond_equity_premium）、
   双低（bond_double_low）、转股价（bond_convert_price）、正股代码（bond_stock_code）
4. 结合溢价率高低、双低值给出客观描述（不做投资建议）
5. 提示：行情接口不返回债券简称（name 为空），如需发行人/评级/条款用 bond detail
```

### 15.2 可转债基本面与条款（行情 + 详情联动）

```
用户："兴业转债的规模、到期日和赎回回售条款是什么？"

AI 步骤：
   → 总规模（bond_total_size）、剩余规模（bond_undue_size）、到期日（bond_due_date）、
     到期收益率（bond_ytm）、强赎触发价/回售触发价
2. 详情看完整发行要素与条款：westock-data bond detail sh113052
   → 发行人、票面利率、期限
3. 条款全文：westock-data bond detail sh113052 --terms
4. 利率变动/现金流/赎回回售明细：westock-data bond detail sh113052 --schedule
5. 综合行情与详情，客观说明规模、到期安排与赎回/回售触发条件
```

---

**记住**：westock-data 是数据查询工具，AI 负责数据分析和洞察！