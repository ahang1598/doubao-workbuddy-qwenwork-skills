# 公式函数签名与返回类型

## 逻辑函数

|签名→返回类型|事实|
|---|---|
|`IF(condition, true_val, [false_val])`→分支类型|`condition=TRUE` 返回 `true_val`，否则返回 `false_val`；省略假分支返回 `false`，不是 `null`。|
|`IFS(cond1, val1, cond2, val2, ...)`→分支类型|返回首个 `TRUE` 条件对应值。|
|`SWITCH(expr, match1, result1, [match2, result2, ...], [default])`→分支类型|匹配 `expr` 并返回对应结果。|
|`IFERROR(expr, fallback)`→分支类型|报错时返回 `fallback`。|
|`IFBLANK(expr, fallback)`→分支类型|空时返回 `fallback`；空含 `NULL`、`""`、空列表。|
|`AND(cond1, cond2, ...)`/`OR(cond1, cond2, ...)`/`NOT(condition)`→布尔|全真/任一真/取反。|
|`ISBLANK(value)`→布尔|`NULL`、`""`、`[]` 为真；`0`、`FALSE` 为假。|
|`ISNULL(value)`→布尔|仅 `NULL` 为真；`""`、`[]`、`0`、`FALSE` 为假。|
|`ISERROR(expr)`/`ISNUMBER(value)`→布尔|报错/数字判定。|
|`CONTAIN(search_range, value, ...)`/`CONTAINSALL(search_range, value, ...)`/`CONTAINSONLY(search_range, value, ...)`→布尔|用于列表或多选字段（`select` 且 `multiple=true`）：含指定值/全部/仅含；`CONTAIN` 不匹配文本子串。|
|`TRUE()`/`FALSE()`→布尔|返回 `TRUE`/`FALSE`。|
|`RECORD_ID()`→文本|当前行记录 ID。|
|`RANDOMBETWEEN(min_int, max_int, [keep_updating])`→数字；`RANDOMITEM(list, [keep_updating])`→元素类型|范围内随机整数/随机列表元素。|

### 条件函数组合

单条件用 `IF`；顺序判断多组条件用 `IFS`；同一值匹配固定选项用 `SWITCH`；处理错误用 `IFERROR`，处理空结果用 `IFBLANK`，两者不等价。分支优先级与预期输出按[条件决策](../scenes/field-formula-lookup.md#条件边界与分支优先级)确定。

`IFS` 参数必须按“条件、结果”成对出现。所有条件都未命中需返回空字符串时，在末尾加 `TRUE(), ""`，不得只加空字符串：

```text
IFS([Value] = 1, "low", [Value] = 2, "medium", [Value] = 3, "high", TRUE(), "")
```

数值与空值混合时遵守[条件公式的空分支](field-formula-expression.md#typed-blank-branches-in-conditional-formulas)的类型约束。

<a id="82-numeric-functions"></a>

## 数值函数

|签名→返回类型|事实|
|---|---|
|`SUM(val1, val2, ...)`→数字|多个值或列表求和。|
|`AVERAGE(val1, val2, ...)`/`MAX(val1, val2, ...)`/`MIN(val1, val2, ...)`/`MEDIAN(val1, val2, ...)`→数字|平均值/最大值/最小值/中位数。|
|`COUNTA(val1, val2, ...)`→数字|非空值数量。|
|`COUNTIF(data_range, condition)`→数字|统计匹配项。范围可为表（`CurrentValue` 是记录行，用 `CurrentValue.[Field]`）或列（`CurrentValue` 是标量）。|
|`SUMIF(data_range, condition)`→数字|匹配求和；范围必须是数值列；`CurrentValue` 是标量，不得以 `CurrentValue.[Field]` 访问其他字段。跨字段改用 `FILTER` 后 `SUM`。|
|`ROUND(number, digits)`→数字|四舍五入；`digits` 为 1/0/-1 分别表示一位小数/整数/十位。|
|`ROUNDUP(number, digits)`/`ROUNDDOWN(number, digits)`→数字|向远离零/向零舍入；`digits` 同 `ROUND`。|
|`FLOOR(number, [base])`/`CEILING(number, [base])`→数字|向下/向上取 `base` 最近倍数；`base` 默认 1。|
|`ABS(number)`/`INT(number)`→数字/整数|绝对值/截断为整数。|
|`MOD(dividend, divisor)`/`POWER(base, exponent)`/`QUOTIENT(dividend, divisor)`→数字|取模/乘方/整数除法。|
|`VALUE(text)`→数字；`ISODD(number)`→布尔|文本转数字 / 判断奇数。|
|`RANK(value, search_range, [ascending])`→数字|范围排名，默认降序。|
|`SEQUENCE(start, end, [step])`→列表|生成数列。|
|`PI()`→数字|圆周率常量。|
|`SIN/COS/TAN/ASIN/ACOS/ATAN/ATAN2/SINH/COSH/TANH/ASINH/ACOSH/ATANH`；`func(radians_or_value)`→数字|三角、双曲函数；角度用弧度。|

## 文本函数

|签名→返回类型|事实|
|---|---|
|`CONCATENATE(text1, text2, ...)`→文本|连接多个文本，支持列表。|
|`LEN(text)`→数字|字符数。|
|`LEFT(text, [count])`/`RIGHT(text, [count])`→文本|从左/右提取，默认 1 个字符。|
|`MID(text, start, count)`→文本|从中间提取。|
|`FIND(search_val, search_range, [start])`→数字|区分大小写查找子串位置；未找到返回 -1。|
|`REPLACE(text, start, count, new_text)`/`SUBSTITUTE(text, old_text, new_text, [occurrence])`→文本|按位置/内容替换；后者可指定第几次出现。|
|`UPPER(text)`/`LOWER(text)`→文本|转大写/小写。|
|`TRIM(text)`→文本|移除首尾空格。|
|`TEXT(value, format)`→文本|格式化；日期格式：`"YYYY-MM-DD"`、`"YYYY/MM/DD hh:mm:ss"`；数字格式：`"00"`、`"000.00"`。|
|`CONTAINTEXT(text, search_text)`→布尔|判断文本包含子串。|
|`SPLIT(text, delimiter)`→列表；`TODATE(value)`→日期|按分隔符拆分文本 / 日期字符串转日期。|
|`CHAR(number)`→文本|ASCII 码转字符。|
|`FORMAT(template, [val1, val2, ...])`→文本|模板格式化，用 `{1}`、`{2}` 等占位符。|
|`HYPERLINK(url, [display_text])`→超链接；`ENCODEURL(text)`→文本|创建超链接/URL 编码。|
|`REGEXMATCH(text, regex)`→布尔；`REGEXEXTRACT(text, regex)`→列表|判断匹配/提取首个匹配捕获组。|
|`REGEXEXTRACTALL(text, regex)`→二维列表；`REGEXREPLACE(text, regex, replacement)`→文本|提取全部匹配/正则替换。|

## 日期函数

|签名→返回类型|事实|
|---|---|
|`NOW()`/`TODAY()`→日期|当前日期时间/当天零点。|
|`DATE(year, month, day)`→日期|构造日期。|
|`YEAR(date)`/`MONTH(date)`/`DAY(date)`→数字|提取年/月/日。|
|`HOUR(date)`/`MINUTE(date)`/`SECOND(date)`→数字|提取时/分/秒。|
|`WEEKDAY(date, [type])` / `WEEKNUM(date, [type])`→数字|星期序号 / 周序号。|
|`DAYS(end_date, start_date)`→数字|结束减开始的日历日整数差；忽略时分秒，可为负；结束日期在前。|
|`DATEDIF(start_date, end_date, unit)`→数字|非负整天/月/年差；`unit` 为 `"D"`/`"M"`/`"Y"`；开始晚于结束时报错。|
|`DURATION(days, [hours], [minutes], [seconds])`→时长|构造日期运算用时长。|
|`EDATE(date, months)`/`EOMONTH(date, [months])`→日期|指定月数后的日期/月末；后者 `months` 默认 0。|
|`WORKDAY(start_date, days, [holidays])`→日期|指定工作日数后的日期；跳过周末、节假日。|
|`NETWORKDAYS(start_date, end_date, [holidays])`→数字|两日期间工作日数，包含边界。|

<a id="85-list-functions"></a>

## 列表函数

|签名→返回类型|事实|
|---|---|
|`LIST(val1, val2, ...)`→列表|创建列表。|
|`FIRST(list)` / `LAST(list)` / `NTH(list, index)`→标量|首个 / 最后一个 / 指定索引元素；索引从 1 开始。|
|`[Table].FILTER(condition).[ResultCol]` 或 `[Table].[Col].FILTER(condition)`→列表|按条件筛选；表范围必须指定结果列，列/列表无须指定；条件用 `CurrentValue`；多值结果列加 `.LISTCOMBINE()`。|
|`data_range.MAP(mapping_expr)`→列表|逐元素映射；表达式用 `CurrentValue`。|
|`SORT(list, [ascending])`→列表|排序；默认升序（`TRUE`）。|
|`[Table].SORTBY([Table].[SortCol], [ascending]).[OutputCol]`→列表|按列排序后提取输出列；只能链式调用，必须指定输出列。|
|`UNIQUE(list)`→列表；`ARRAYJOIN(list, [delimiter])`→文本|去重 / 连接列表元素；后者默认逗号分隔。|
|`LISTCOMBINE(val1, [val2, ...])` 或 `list.LISTCOMBINE()`→列表|合并值/列表；链式时展平二维数组，用于 `FILTER` 多值结果列。|
|`DISTANCE(location1, location2)`→数字|两地理位置间距离，单位千米。|

## 易混淆函数

- 列表或多选字段用 `[Tags].CONTAIN("Urgent")`，文本子串用 `[Notes].CONTAINTEXT("completed")`；不得用 `CONTAIN` 匹配文本子串，也不得对列表用 `CONTAINTEXT`。
- 满 N 个月等完整周期用 `DATEDIF(start,end,"M")`；不得用 YEAR/MONTH 相减，否则会忽略日边界、提前一个月跨档。
- `DAYS` 只比日历日：`DAYS(TODATE("2026-10-13 12:00"), TODATE("2026-10-13 09:30")) = 0`，`DAYS(TODATE("2026-10-14 00:30"), TODATE("2026-10-13 23:30")) = 1`。
- 跨字段/多步用 `FILTER` 后聚合；仅同列条件可用 `COUNTIF`/`SUMIF` 简写，此时 `[Table].FILTER(cond).[Col].LISTCOMBINE().SUM()` 等价于 `SUMIF([Table].[Col], cond)`。
