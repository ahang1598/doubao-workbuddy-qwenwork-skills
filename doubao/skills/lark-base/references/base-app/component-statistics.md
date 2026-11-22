---
name: app-component-statistics
description: App 指标卡的原子尺寸、统计粒度、比率、同环比与趋势。
---

# 指标卡 statistics

必读 [公共数据](app-data-common.md)。ChartDataConfig与标准族共享，但不允许group_by或sort，只表达单个聚合值；一行一对象才count_all，字段指标series与count_all二选一。用户指定指标卡时不因“率”换成progress；用户明确要进度条则读 [progress](component-progress.md#点名进度条时保留组件与口径)，不套本页替换组件。

默认同行均分宽×6，推荐W8～24、H5～12；不默认宽高fill。按 [页面布局](../../scenes/app-mode/layout.md) 成组，一行≤5、等高、均分、连续铺满，多行数量差≤1，每行含尾行按实际数量重新分配宽度并铺满所属区域，遵守[满行与不串行约束](../../scenes/app-mode/layout.md#画布会向上补洞不能用空位占行)。默认指标组不拆出孤立单卡行；用户明确只要一张卡时占满所属区域，不增卡凑数。用户合法尺寸、模板与组规则优先。

## 默认字号

新建默认自定义字号：数据说明16、数字48、同环比说明14、同环比数字16；同行保持一致。使用
`--display-config '{"font_size":{"title":16,"number":48,"compareDesc":14,"compareNumber":16}}'`。四个子键遵循公开fontSize方法，不用text_styles或单个font_size数值代替。独立block-get核 `display_config.font_size`，布局/渲染另验；不因字号配置开启无数据依据的同环比。局部未点名字号时保留，用户明确字号优先。

## 口径与比较

先保留用户指标、聚合与已发生范围，不能因标题含“总量”机械SUM。比率先明确分子、分母、范围及字段实际含义，按公共数据检查数值粒度；缺字段交Table依赖，补齐后回读再生成原指标卡。仅改名称用外层name，可见description用正式display_config方法，不重配数据。

写前按 [业务词映射](app-data-common.md#从业务词到配置) 记录字段实际含义：比率保留完整分母，去重活跃保留对象与时间粒度，余额／净额保留持续计算来源，跨层级统计保持目标实体粒度。写后同时比对聚合、状态、业务日期与实际值，名称相符或当前值偶然相等都不证明口径正确。

新建或修改都评估period_comparison与trend_chart：真实兼容日期、各期相同口径、可靠可比较时间段/连续时间点齐备时分别开启；没有证据保留基础卡，不机械同时开启。

display_config.period_comparison接受友好对象：
`{"compareOnField":"日期","compareType":"MonthOnMonth","calcMethod":"diff_rate","currentTimeRange":["CurrentMonth"]}`。
compareType为DateOnDate/WeekOnWeek/MonthOnMonth/YearOnYear/RangeDate；calcMethod为diff_rate/diff_value/original_value，自定义区间为`["RangeDate",startMs,endMs]`，compareRange/description按协议使用。

trend_chart为`{"groupByField":"日期","timeRange":["LatestHalfYearEndDay"]}`，字段用真实名称/ID，不填解析后的内部fieldType。

时间标签：Today、CurrentWeek、CurrentWeekEndDay、CurrentMonth、CurrentMonthEndDay、CurrentQuarter、CurrentQuarterEndDay、CurrentYear、CurrentYearEndDay、Yesterday、LastWeek、LastMonth、LastQuarter、LastYear、LatestOneWeek、LatestTwoWeek、LatestOneMonth、LatestThreeMonthEndDay、LatestHalfYearEndDay、LatestOneYear。趋势不支持Today/Yesterday；最近六个月不是LatestSixMonth。

显式关闭用对应层clear_fields中的period_comparison/trend_chart，省略保留；适用方法及数组参数见 [页面API](app-page-api.md)。百分比/货币/精度/千分位走 [标准格式](component-charts.md)。独立回读组件类型、真实字段、聚合、范围、格式、比较配置、矩形和实际值。
