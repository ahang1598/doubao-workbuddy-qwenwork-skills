# 公式表达式契约

## 目录

数据形状｜数据类型｜运算符｜CurrentValue｜函数调用｜关联与跨表｜硬性约束｜公式模式｜字段 JSON 示例｜错误用法

## 数据形状：标量与列表

写公式前先确定数据形状。

| 语法 | 含义／类型 |
|---|---|
| `[Field]` | 当前行字段值；标量 |
| `[TableName].[Field]` | 目标表该列全部值；列表 |
| `[TableName]` | 整表；表引用，可作 `FILTER`／`COUNTIF` 范围。表名优先于同名字段；同名关联字段会解析为整表，使逐行聚合变成整表聚合 |

- 标量直接运算；列表先用 `SUM()`、`ARRAYJOIN(",")`、`FIRST()`／`LAST()`／`NTH()` 处理。
- `[LinkField].[TargetField]` 返回关联值列表；逐行聚合用 `COUNTA([LinkField])`、`[LinkField].[Field].SUM()`。与表同名时改名，或用 `[Table].FILTER(CurrentValue.[BackLink] = [Key]).[Field].SUM()`／`.[Field].COUNTA()`。
- 表级 `FILTER` 返回记录行；末尾投影字段再聚合，不能将未投影结果包在 `COUNTA(...)` 中。回读见[字段回读契约](field-commands.md#计算字段回读)。
- `FILTER` 结果列为多值字段（`multiple=true` 的 `select`、`link`）时产生二维数组，必须 `.LISTCOMBINE()`；单值列（`number`、`text`）可省略，添加也不报错：

```text
[Table].FILTER(CurrentValue.[Field] = [Value]).[Tags].LISTCOMBINE()
```

## 数据类型与类型转换

### 字段存储类型

| 类型 | 存储与操作 |
|---|---|
| `number` | 数学运算、比较；拼接时转字符串 |
| `text` | 字符串操作；数字内容可参与数学运算，否则报错 |
| `datetime` | 日期函数、与数字加减；`&` 转默认格式，控制输出先用 `TEXT` |
| `select`（`multiple=true`） | 列表；列表函数、`CONTAIN` |
| `link` | 关联记录；`[LinkField].[Field]` 返回列表 |
| `checkbox` | `TRUE`／`FALSE`；逻辑运算；与数字比较时自动转数字 |

### 隐式类型转换

| 场景 | 结果 |
|---|---|
| 数字 + 小数 | 小数 |
| 日期 ± 数字 | 日期，增减天数；整天用 `+`／`-`，时／分／秒用 `DURATION()` |
| 日期 - 日期 | 可含小数的经过天数；乘 24 得小时 |
| 布尔值与数字比较 | `TRUE=1`、`FALSE=0` |
| `&` | 两端转字符串 |

### 比较时的类型一致性

`>`、`>=`、`<`、`<=`、`=`、`!=` 两端必须同类型；否则显式转换：

| 比较／计算 | 处理 |
|---|---|
| `number` 与 `text` | 用 `VALUE()` 将文本转数字 |
| 日期与日期文本 | 按业务格式解析成同类型日期；只按日相等时统一日期格式；展示字符串不能比较日期先后 |
| `datetime` 按天相等 | 时间部分会使直接 `=` 不等；用 `TEXT([DateA], "YYYY/MM/DD") = TEXT([DateB], "YYYY/MM/DD")` |
| `select`、`user` | 与同类型值或文本比较 |
| `text` 数值聚合 | `SUM`／`AVERAGE`／`MIN`／`MAX` 前用 `VALUE()`；`FILTER` 结果用 `.MAP(VALUE(CurrentValue)).SUM()` |

### 计算类型与导出展示

区分三层证据：`+field-get` 字段及结果类型、表达式形状及元素类型、Record JSON 物理类型。NDJSON 可将 Formula、Lookup、日期导出为字符串；`physical_type=string|null` 或日期文本只说明导出格式，不能证明公式内 Lookup 是文本标量。

- 按 [Scene 输出目标](../scenes/field-formula-lookup.md#输出与聚合目标)确认唯一匹配或指定聚合。取首项前证明唯一性或顺序；无匹配时按业务处理空值。
- 先得到标量再转换类型。禁止 `TEXT([日期], "YYYY-MM-DD") <= [日期Lookup]` 或用 `FIRST()` 任取多个日期。函数见[日期与列表函数](field-formula-functions.md#日期函数)；保存后核值。

<a id="typed-blank-branches-in-conditional-formulas"></a>

### 条件公式中与结果类型兼容的空分支

数字结果的空分支必须兼容结果类型：

```text
IF([Condition], [NumericExpression], "")
IF([Condition], [NumericExpression], VALUE(""))
```

- `""`（或 `" "`）是已确认写法：数字与空值并存、两个分支都是文本时都可用。
- 需要保持数值结果类型时，`VALUE("")` 是候选写法；类型兼容性与空值结果以实际值为准，定义被接受不等于有效。
- `BLANK()`、`NULL`、`NaN()` 不在支持的函数清单中，不用来构造空值。验收及缺少代表数据的处理见 [Scene 回读验收](../scenes/field-formula-lookup.md#回读验收)。

#### 空分支异常的定向修正

修复及恢复预算见 [Scene 异常恢复](../scenes/field-formula-lookup.md#异常恢复)：

- 假分支实际返回 `0`、错误，或结果类型被解析为不符合目标的文本：检查保存的表达式与结果类型，在两候选间切换。
- 两分支均为 `null`：先查空分支和类型兼容性；条件、关联遍历、算术已验证时保留，只修正类型问题。

## 运算符

只用下列运算符；禁用 `like`、`in`、`<>`、`**`、`^`。

| 类别 | 运算符 | 规则 |
|---|---|---|
| 算术 | `+` `-` `*` `/` `%` | 加减乘除取模；`%` 等价于 `MOD()` |
| 比较 | `>` `>=` `<` `<=` `=` `!=` | 相等用 `=`，不用 `==`；不等用 `!=`，不用 `<>` |
| 逻辑 | `&&` `\|\|` | 与、或；也支持 `AND()`／`OR()` |
| 拼接 | `&` | 非文本转字符串；不用 `+` |

## CurrentValue

`CurrentValue` 是 `FILTER`／`MAP`／`COUNTIF`／`SUMIF` 的当前项，只能在其条件或映射参数内。

| 范围 | 当前项／访问 |
|---|---|
| 表 `[TableName]` | 行；`CurrentValue.[FieldName]` |
| 列 `[TableName].[Field]` | 字段值；`CurrentValue` |
| 多选 `[Tags]`（`select`，`multiple=true`） | 选项；`CurrentValue` |
| `LIST` 列表 | 元素；`CurrentValue` |

列／列表不能用 `CurrentValue.[FieldName]`；条件中的 `[FieldName]` 是公式行值，不是其属性。

## 函数调用约定

| 方式 | 格式 | 规则 |
|---|---|---|
| 函数式 | `FUNC(arg1, arg2)` | 适用于所有函数 |
| 链式 | `arg1.FUNC(arg2)` | 第一个参数移到 `.` 前 |

- 零参数函数 `NOW()`、`TODAY()`、`PI()`、`TRUE()`、`FALSE()` 不能链式调用。
- `SORTBY` 只能链式：`[Table].SORTBY([Table].[SortCol]).[OutputCol]`。排序列写原表列 `[TableName].[Field]`；`FILTER` 结果由引擎对齐记录行。
- `FILTER` 用链式：`[Table].FILTER(condition).[OutputCol]`。

### FILTER / SORTBY 的结果列规则

- 表范围返回表引用，链尾必须 `.[Field]`：`[Orders].FILTER(condition).SORTBY([Orders].[SortCol]).[Customer]`。
- 列／列表范围直接返回列表，无须结果列：`[Orders].[Amount].FILTER(CurrentValue > 100)`。
- 指定结果列后先 `.LISTCOMBINE()` 再链式聚合：`[Orders].FILTER(CurrentValue.[Amount] > 100).[Amount].LISTCOMBINE().SUM()`。

<a id="section-5-link-fields-and-cross-table-references"></a>

## 关联字段与跨表引用

- `FieldName: Link [target table: X, foreign key: Y]` 表示以字段 Y 为关联键连接目标表 X。
- `[LinkField].[TargetField]` 返回全部关联目标值；可继续 `[LinkA].[LinkB].[Field]`。
- 等价展开：多值关联用 `[TargetTableX].FILTER([LinkField].CONTAIN(CurrentValue.[Y])).[TargetField].LISTCOMBINE()`；单值关联用 `[TargetTableX].FILTER(CurrentValue.[Y] = [LinkField]).[TargetField].LISTCOMBINE()`。
- 目标字段为多值时必须 `.LISTCOMBINE()`；单值时可选。
- 关联列表可能为空；取单值用 `SUM`／`MAX`、`ARRAYJOIN` 或 `FIRST`／`LAST`／`NTH`。
- 跨表查询不在 `FILTER` 内嵌套 `FILTER`，优先用关联字段链式访问。

<a id="section-7-hard-constraints"></a>

## 硬性约束

1. `FILTER`／`SUMIF`／`COUNTIF`／`MAP` 不得出现在彼此的条件或映射参数内。禁用 `[Table1].FILTER(CurrentValue.[Col] = [Table2].FILTER(...).[Col])`、`[Table].MAP([Table2].MAP(...))`；链式 `[Table].FILTER(cond1).[Col].FILTER(cond2)` 不算嵌套。
2. 只用[函数白名单](field-formula-functions.md)及本文[运算符](#运算符)。
3. 表名、字段名与 `+table-get` 返回值逐字一致，不改名、不加空格。
4. 字符串用双引号 `"`；不支持单引号。
5. 不用 `LOOKUP`；统一改写为 `FILTER`。
6. 请求体必须含 `"type": "formula"`。

<a id="section-11-common-formula-patterns"></a>

## 常见公式模式

<a id="match-keys-in-patterns-1-3"></a>

### 模式 1～3 的匹配键

- 两端必须为单值。`link`／`DuplexLink`、多选 `select` 是列表；`=` 只匹配完全相同的列表。公式可保存且数字貌似合理，但多关联行会少计。
- 按 [Scene 前置检查](../scenes/field-formula-lookup.md#前置检查)取真实结构；含列表时左列表、右标量：

```text
错误：[Table].COUNTIF(CurrentValue.[LinkField] = [LinkField])
正确：[Table].COUNTIF(CurrentValue.[LinkField].CONTAIN([ScalarKey]))
```

`[ScalarKey]` 是当前行主字段文本、ID 或提取单值的辅助公式，不能用关联字段。也可按 [Scene 选定 Lookup](../scenes/field-formula-lookup.md#长期结果与字段选型)，目标表计数后用 `lookup` 带回；详见 [Lookup 配置](field-lookup-config.md)。

| 模式 | 公式／规则 |
|---|---|
| 1 跨表条件计数 | `[TargetTable].COUNTIF(CurrentValue.[MatchField] = [CurrentTableField])` |
| 2 跨表条件求和 | `[TargetTable].FILTER(CurrentValue.[MatchField] = [CurrentTableField]).[NumCol].LISTCOMBINE().SUM()`；仅涉及该列时用 `SUMIF([TargetTable].[NumCol], CurrentValue > 100)` |
| 3 跨表取值 | `[TargetTable].FILTER(CurrentValue.[MatchCol] = [CurrentTableField]).[ReturnCol]` |
| 5 条件文本拼接 | `IF([Condition], "prefix" & [Field] & "suffix", "default text")` |
| 6 日期差 | `DATEDIF([StartDate], [EndDate], "D") & " days"`；`DAYS([EndDate], [StartDate])`；直接相减得保留时间、可含小数的天数；`ROUND(([EndDate]-[StartDate])*24,2)`：同日 09:30 到 12:00 得 2.5 小时 |
| 7 列表元素映射 | `[MultiSelectField].MAP(CurrentValue & " tag")`；`SPLIT([TextField], ",").MAP(TRIM(CurrentValue))` |
| 8 跨表排序 | `[TargetTable].SORTBY([TargetTable].[SortCol],FALSE).[OutputCol]`；筛选后排序：`[TargetTable].FILTER(CurrentValue.[Field]=[Value]).SORTBY([TargetTable].[SortCol]).[OutputCol]`；第二参数 `TRUE` 为升序 |

`COUNTIF` 可用整表，无须列。`SUMIF` 范围必须是数值列；`CurrentValue` 是标量，不能访问 `.[OtherField]`。跨字段条件用表范围 `FILTER`。

#### 多字段匹配与取值

对 [Scene 匹配键](../scenes/field-formula-lookup.md#来源匹配关系与筛选范围)逐个比较单值并以 `&&` 合取；沿用[匹配键约束](#match-keys-in-patterns-1-3)。日期按天匹配时以 `TEXT` 统一两端格式。`FIRST()` 不证明唯一。

```text
[对方表].FILTER(CurrentValue.[字段A]=[字段A] && CurrentValue.[字段B]=[字段B]).[要带出的字段].FIRST()
[对方表].COUNTIF(CurrentValue.[字段A]=[字段A] && CurrentValue.[字段B]=[字段B])>0
```

### 模式 4：关联字段取值与聚合

```text
SUM([LinkField].[NumField])
[LinkField].[TextField].UNIQUE().ARRAYJOIN(",")
[订单].[金额].FIRST()
[OrderItems].[Product].[ProductName].UNIQUE().ARRAYJOIN(",")
```

## 字段 JSON 示例

外层结构见[字段 JSON](field-config.md#39-formula)。`expression` 是字符串，公式中的双引号进入 JSON 后转义为 `\"`；不得把表达式当 JSON 对象或数组提交。命令参数与更新语义见[字段命令](field-commands.md)。

当前表 `Customers`（文本 `CustomerID`），目标表 `Orders`（文本 `CustomerID`、数字 `Total`）。需求：有订单时输出 `Sold N orders`，否则输出 `No sales records`。

```json
{
  "type": "formula",
  "name": "Order Summary",
  "expression": "IF([Orders].COUNTIF(CurrentValue.[CustomerID] = [CustomerID]) >= 1, \"Sold \" & [Orders].COUNTIF(CurrentValue.[CustomerID] = [CustomerID]) & \" orders\", \"No sales records\")"
}
```

`[Orders].COUNTIF(...)` 以整张 `Orders` 表为范围；`CurrentValue.[CustomerID]` 是目标表行的值，`[CustomerID]` 是公式所在 `Customers` 行的值。

跨表筛选、排序后取首项时用函数式包裹链式结果：`FIRST([Tasks].FILTER(CurrentValue.[Project] = [ProjectName]).SORTBY([Tasks].[Priority], TRUE).[TaskName])`。

<a id="section-12-anti-pattern-collection"></a>

## 错误用法汇总

| # | 错误 → 恢复（原因） |
|---|---|
| 1 | `[Table].[Col].MAP([Table2].[Col], CurrentValue + 1)` → `[Table].[Col].MAP(CurrentValue + 1)`（`MAP` 无查找范围参数） |
| 2 | `condition.[Table].FILTER()` → `[Table].FILTER(condition).[ResultCol]`（范围在前；表范围投影列） |
| 3 | `SUMIF([Orders].[Amount], CurrentValue.[Owner]=[Owner])` → `[Orders].FILTER(CurrentValue.[Owner]=[Owner]).[Amount].LISTCOMBINE().SUM()`（列当前项是标量；跨字段用表范围） |
| 4 | `[Orders].FILTER(CurrentValue.[Amount]>100)` → `[Orders].FILTER(CurrentValue.[Amount]>100).[Customer]`（表范围投影列） |
| 5 | `[Table1].FILTER(CurrentValue.[ID]=[Table2].FILTER(...).[ID])` → `[Table1].FILTER(CurrentValue.[ID]=[Key]).[OutputCol]`（禁止互嵌；拆步骤或用关联字段） |
| 6 | `[Table].SORTBY([Table].[Col])` → `[Table].SORTBY([Table].[Col]).[OutputCol]`（末尾投影列） |
| 7 | `[Table].SORTBY([Col]).[OutputCol]` → `[Table].SORTBY([Table].[Col]).[OutputCol]`（排序列带表名） |
| 8 | `CONTAIN([Text],"value")` → `CONTAINTEXT([Text],"value")`（前者匹配列表／多选完整值；文本子串用后者） |
| 9 | `"Date: "&[Date]` → `"Date: "&TEXT([Date],"YYYY-MM-DD")`（直接拼接不报错但用默认格式） |
| 10 | `DAYS([StartDate],[EndDate])` → `DAYS([EndDate],[StartDate])`（第一参数是结束日；结束日较晚时前者为负、后者为正） |
| 11 | `TODAY.DAYS([Date])` → `TODAY().DAYS([Date])`（零参数函数带括号） |
| 12 | `[Table].[Col].FILTER(CurrentValue.[Col]>0)` → `[Table].[Col].FILTER(CurrentValue>0)`（列当前项是标量） |
| 13 | `[Table].FILTER(CurrentValue>100)` → `[Table].FILTER(CurrentValue.[Amount]>100).[Amount]`（表当前项是一行） |
| 14 | 顶层 `CurrentValue+1` → 放入 `MAP`／`FILTER` 等遍历函数（只能在遍历函数内使用） |

