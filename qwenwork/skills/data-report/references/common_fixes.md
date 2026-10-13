# 常见错误最小修复


**❌ 多 sheet 文件只分析了第一个**
- 根因:`pd.read_excel(path)` 默认只读 sheet[0]
- 修:看 INSPECT `sheet_dims`,`if len(sheet_dims) > 1: 循环读`;不确定先问

**❌ 报告读起来像流水账,没业务洞察**
- 根因:每条洞察只有"X 列均值 3.2"(数字搬运)
- 修:按"数字事实 / 原因 / 该做什么"三段写,只有第一段的删

**❌ KPI 数字对不上源文件**
- 根因 ①:INSPECT 报了 `data_traps` 但没按 `suggested_read_code` 读 → 抄
- 根因 ②:Validate 报错后重写整张 HTML 想绕过 → 错误通常是单点(dom_id / fstring / JSON),只改报错的那行

**❌ 模型按 INSPECT 提示用 `data_only=True` 读跨 sheet 公式,拿到全 None**
- 根因:汇总 sheet 公式 cache 缺失(源文件从未在 Excel 打开保存过)
- 修:放弃 cache,从明细 sheet 用 `pd.read_excel` + `groupby().sum()` 重算

**❌ HTML 有 N 个 `<div id="chart-X">` 但只 init 了 K 个 (K < N), 用户看到 N-K 个白图位**
- 根因:写 HTML 模板时占了所有 chart 位,但写 `echarts.init().setOption({})` 时只写了前几个(token budget 不够 / 顾此失彼)
- 检测:`validate-html` runtime 报 `orphan_chart_div: N 个 chart 容器未渲染: [chart-X1, chart-X2, ...]`
- 修:**给报错列出的每个 id 都补 `echarts.init(document.getElementById('<id>')).setOption({...})`** — 不能保留 div 占位而不渲染

**❌ spot check 只对了均值/中位数,没对总聚合,漏检 raw_stats 字段错位 bug**
- 根因:raw_stats 给出的字段对应可能错乱(例如 "员工总数" 字段实际填了 "薪资中位数"),但均值/中位数往往恰好都对,偏差小
- 修:**优先对账 sum/total/GMV/总额** 类聚合 KPI,这类最容易撞 raw_stats 字段错位。偏差 ≥ 0.1% 取 pandas 重算值,写 HTML 用 pandas

