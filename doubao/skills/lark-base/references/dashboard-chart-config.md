# 图表与数据组件配置

多数据源配置见 [Dashboard 多数据源配置](dashboard-multi-source.md)；组件标题、背景、图例、标签及字体等按 [自定义样式](dashboard-style.md) 选择适用字段。

## 对象与入口

`data_config` 随 `type` 变化；普通图表为扁平单数据源。

图表联动是与 `data_config` 平级的顶层 `linkage`，通过 `--linkage` 更新。配置同源目标、追加或清除前读取 [图表联动](dashboard-linkage.md)；不得放入 `data_config`。

## 支持的组件类型（`type` 枚举）

| type | 说明 | type | 说明 | type | 说明 |
|---|---|---|---|---|---|
| `column` | 柱状 | `bar` | 条形 | `line` | 折线 |
| `pie` | 饼 | `ring` | 环形 | `area` | 面积 |
| `combo` | 组合 | `scatter` | 散点 | `funnel` | 漏斗 |
| `wordCloud` | 词云 | `radar` | 雷达 | `ranking` | 排行榜 |
| `statistics` | 指标卡 | `pivotTable` | 透视表 | `nps` | NPS 图 |
| `slicer` | 单表单字段离散值切片器 | `countdown` | 固定时间或日期字段倒计时 | `progress` | 数值／日期；嵌套 `progress` 配置，见 [进度图](dashboard-progress.md) |
| `view` | 筛选、分组、排序、可见字段 | `text` | Markdown 文本；见 [配置](dashboard-block-commands.md#text-类型特殊结构) | `button` | 按钮；见 [配置](dashboard-button-binding.md#按钮组件配置) |

## 普通图表 data_config 结构

本节适用普通图表；`pivotTable`、`nps` 见下文专属协议。`slicer`、`view` 无需指标；`view` 不受图表分组数限制。

| 字段 | 类型与规则 |
|---|---|
| `table_name` | 数据表名称，如 `订单表`；不是 `table_id` |
| `series` | `[{"field_name":"金额","rollup":"SUM"}]`；指标/Y 轴；与 `count_all` 二选一；`rollup`：`SUM` / `MAX` / `MIN` / `AVERAGE` |
| `count_all` | boolean；COUNTA 记录数；与 `series` 二选一；只写顶层 `true`，不存在 `rollup:"COUNT"` |
| `group_by` | `[{"field_name":"状态","mode":"integrated","sort":{...}}]`；X 轴；每项必须是对象 |
| `filter` | `{"conjunction":"and","conditions":[{"field_name","operator","value"}]}`；不是 record-list 的 `logic` 形态；值规则见 [条件协议](dashboard-filter-conditions.md) |

### 字段所属表边界

`series`、`group_by`、`filter.conditions` 的 `field_name` 必须逐字存在于 `table_name` 对应表。不得以 `关联字段.目标字段` 等点号路径跨表，也不得使用其他表的 field ID 或缓存旧 field ID。

### group_by 详细说明

#### mode 枚举

| mode | 规则 |
|---|---|
| `integrated` | 聚合分组；非多值字段默认使用 |
| `enumerated` | 拆分多值独立统计；多选、人员等多值字段默认 |

#### sort 排序

`sort.type` 取 `group`（按横轴值）、`value`（按纵轴值）或 `view`（按数据源记录顺序）；`sort.order` 取 `asc` / `desc`。传 `sort` 时明确方向。`value` 必须传 `order`；`group` / `view` 缺失时 CLI 补 `order:"asc"`。

### 筛选字段与操作符

- 构造 `filter` 前必须读取 [字段类型与操作符速查](dashboard-filter-conditions.md#字段类型与操作符速查)：`conjunction` 取 `and` / `or`；按类型选 `operator`、值形状、日期条件；除 `isEmpty` / `isNotEmpty` 外必须传 `value`。
- `value`：文本/单选为 string，数字为 number，多选/人员为 string[]，复选框为 boolean；日期为 `["ExactDate", Unix 毫秒时间戳]` 或受支持的相对日期关键字，不得传裸时间戳，见 [日期筛选](dashboard-filter-conditions.md#日期筛选)。
- 选项值必须来自字段真实候选值，不得猜测；读取方式见 [字段查找与完整性](field-commands.md#字段查找与完整性)。不存在的选项、空字符串或空数组通常不报错，但组件静默无数据，界面显示筛选项均未勾选。
- 公式字段按返回类型选操作符和值，不按“公式”外层类型套等于条件。

### 时间粒度与范围辅助字段

- 月粒度无法稳定保留时，以已创建的 `TEXT([日期字段], "YYYY-MM")` 文本公式字段作 `group_by`，按 `group` 升序；表达式见 [Formula 表达式](field-formula-expression.md)。
- 年度 datetime 筛选无法稳定表达时，聚合动态 helper measure `IF(YEAR([日期字段]) = YEAR(TODAY()), [指标字段], "")`；当年返回指标，非当年为空。不得持久化当前四位年份常量或用未经验证的 Formula filter 代替年度范围。
- 周度／每周先建 `WEEKNUM([日期])` 周次字段并分组；“本周”仅为附加筛选，不产生周维度。

### 常用形态示例

字段名逐字取自 `+field-list`。前两行仅用于 `--type statistics`；`column` / `bar` / `pie` / `line` 携带 `number_format` 会被拒。

```json
{"table_name":"订单表","count_all":true,"number_format":{"formatName":"digital","precision":0}}
{"table_name":"订单表","series":[{"field_name":"金额","rollup":"SUM"}],"number_format":{"formatName":"cyn_rounded","precision":2}}
{"table_name":"订单表","count_all":true,"group_by":[{"field_name":"渠道","mode":"integrated","sort":{"type":"value","order":"desc"}}],"filter":{"conjunction":"and","conditions":[{"field_name":"状态","operator":"is","value":"已完成"}]}}
```

## 更新语义

普通图表按顶层 patch：未传项保留；传入项整体替换；`number_format` 按子字段合并。特殊组件不得套用：倒计时见 [更新协议](dashboard-countdown.md#更新语义)，视图见 [更新协议](dashboard-view.md#更新)，`ranking`、`pivotTable` 见下文。

## 专属图表协议

### statistics 指标卡数值格式 number_format（可选）

仅 `statistics` 支持 `data_config.number_format`。不传时服务端补 `{"formatName":"digital"}`，省略 `precision`。其他类型 create 时 CLI 拒绝，`--no-validate` 可跳过；update 无 `--type`，由服务端按现有类型裁决。

| 键 | 规则 |
|---|---|
| `formatName` | 可选 string；精确匹配下列 5 值且区分大小写；不自动转大写，`DIGITAL` 被拒 |
| `precision` | 可选 integer `0..9`；非整数被本地拒绝 |

| 值 | 含义；`precision=2` 示例 |
|---|---|
| `digital` | 千分位、服务端默认；`1,234.56` |
| `digital_without_separator` | 无千分位；`1234.56` |
| `percentage_rounded` | 百分比；`1,234.56%` |
| `cyn_rounded` | 人民币；`¥1,234.56` |
| `dollar_rounded` | 美元；`$1,234.56` |

比例小数按百分比保留一位用 `{"formatName":"percentage_rounded","precision":1}`；先区分比例小数与已乘 100 的百分数。

更新按子字段合并：现有 `digital, precision:2`，传 `{"number_format":{"precision":0}}` 后得到 `digital, precision:0`。

### ranking 排行榜专属契约

公开字段仅 `table_name`、`series` / `count_all`、`group_by`、`filter`、`limit_size`。

| 键 | 规则 |
|---|---|
| `group_by` | 必填且长度严格为 1；`mode` 仅 `integrated` / `enumerated`；排序只写 `[0].sort`，`type` 仅 `value`，`order` 为 `asc` / `desc`；create 缺排序时默认指标值降序 |
| `series` / `count_all:true` | 二选一；`series` 长度严格为 1，`rollup` 仅 `SUM` / `MAX` / `MIN` / `AVERAGE` |
| `limit_size` | Top N；整数 `1..500`；create 缺省为 `10` |
| 禁止 | 顶层 `sort`、公开 `ranking` 对象、头像开关 |

更新为顶层 patch：单传 `limit_size`、`group_by`、`series` / `count_all:true`、`filter` 仅替换该项。换表须同传新 `table_name`、`group_by` 和 `series` 或 `count_all:true`；未传 `filter` / `limit_size` 则保留。

```json
{"table_name":"订单表","series":[{"field_name":"金额","rollup":"SUM"}],"group_by":[{"field_name":"负责人","mode":"integrated","sort":{"type":"value","order":"desc"}}],"limit_size":10}
```

### nps 评分图专属契约

| 键 | 规则 |
|---|---|
| `group_by` | 必填且长度 1；字段必须是 Base 评分字段；Dashboard 服务端识别其 `Rating` 语义，它不属于通用筛选类型 |
| `series` / `count_all` | 禁止 `series`；`count_all` 可省略且只能为 `true` |
| `category_range` | `[min,detractorMax,passiveMax,max]`；仅 `nps`；可省略，由服务端按 Rating 量程生成；显式传入须长度 4，首尾等于字段最小、最大值 |

CLI 仅做轻量 JSON 校验；服务端按字段元数据校验字段类型、量程、首尾匹配。

```json
{"table_name":"订单表","group_by":[{"field_name":"评分","mode":"integrated"}],"category_range":[0,6,8,10]}
```

### pivotTable 类型特殊结构

使用 `rows` / `columns` / `values`，不用 `series` / `group_by` / `count_all`。Create 必须传 `table_name`；三组缺省为 `[]`；字段名须来自真实表。

```json
{"table_name":"订单表","rows":[{"field_name":"状态","group_type":"RAW"}],
"columns":[{"field_name":"日期","group_type":"DATE_YEAR_MONTH"}],
"values":[{"field_name":"金额","rollup":"SUM","name":"金额合计"}],
"sort":[{"group_ref":{"area":"rows","index":0},"sort_type":"VALUE",
"value_ref":{"area":"values","index":0},"order":"desc"}]}
```

| 键 | 规则 |
|---|---|
| `group_type` | `RAW`、`DATE_YEAR`、`DATE_YEAR_QUARTER`、`DATE_YEAR_MONTH`、`DATE_YEAR_MONTH_DAY`、`DATE_YEAR_WEEK`、`DATE_MONTH_DAY`、`DATE_QUARTER`、`DATE_MONTH`、`DATE_WEEKDAY` |
| `rollup` | `SUM`、`COUNT`、`COUNT_DISTINCT`、`AVERAGE`、`MAX`、`MIN`、`MEDIAN` |
| `field_key` | 稳定标识，不替代 `field_name`；Create 三组只传 `field_name`，禁止 `field_key` |
| `sort` | 数组；可多条字段/指标排序，`[]` 清空；Create 用 `{area,index}` 引用请求数组项；Update 用 `group_field_key` / `value_field_key` 或 `{area,index}`，同一引用位置只能选一种 |
| Update | 顶层局部更新；传入的三组各自整体替换；换 `table_name` 必须显式传三组 |
| `view_name` / `filter` | 互斥；传 `null` 清除对应数据源约束 |

Update 保留项时传 Get 返回的 `field_key`、`field_name`、当前 `group_type` 或 `rollup`；替换字段、分组或聚合时省略原 `field_key`，由服务端生成。读取结果按 [图表结果协议](dashboard-chart-result.md) 的二维聚合结构验收。

## 约束与本地校验

| 类型 | 必填 | 禁止／限制 |
|---|---|---|
| 普通图表 | `table_name`；`series` / `count_all` 二选一且至少一个 | `group_by` 最多 2 个，每项须有 `field_name` |
| `ranking` / `nps` / `pivotTable` | 按各自专属契约 | 按各自专属契约 |
| `slicer` | `table_name`、恰好一个 `group_by` | 禁止 `series` / `count_all`；见 [契约](dashboard-slicer.md) |
| `countdown` | [fixed/field 专属结构](dashboard-countdown.md) | — |
| `text` | `text` | 禁止 `series`、`count_all`、`group_by`、`filter` |
| `button` | 不要求 `table_name`、`series`、`count_all` | 专属字段由服务端校验 |

CLI 规范化：`series[].rollup` 转大写（`sum` → `SUM`）；`group_by[].sort.type/order` 转小写；`group` / `view` 缺 `order` 补 `asc`，`value` 不补。`--no-validate` 时不规范化，原样透传。

本地校验（`--no-validate` 可跳过）：

- `+dashboard-block-create` 轻量校验 `data_config`，聚合错误并给修复动作。
- create、update 拒绝顶层 `timebar`、`card`，包括 `{}` / `null`；`view_type` 和读取行为不变。
- `+dashboard-block-update` 无 `--type`，通常不按类型强校验；检测到透视表字段时校验行列、指标、排序引用。
- update 校验可解析 `filter` 的 `conjunction`、字段引用、`operator`、必需 `value`；与 create 同样拦截非法 `number_format` 子字段。
- `data_config` 必须是合法 JSON 对象，使用 `--no-validate` 也如此；CLI 不改写业务含义。

## 普通图表配置示例

| 形态 | 动作 |
|---|---|
| 柱／条形／散点 | `series` + 一个 `integrated group_by`，表达 Y 指标、X 维度 |
| 饼／环形／词云 | `count_all:true` + 一个分类/文本 `group_by` |
| 折线／面积（月趋势） | `series` + 时间 `group_by` + `sort:{"type":"group","order":"asc"}` |
| 组合／雷达 | 多项 `series` + 一个 `group_by` |
| 限定范围排名 | 用 `value desc`；渠道、状态、时间范围写入本组件 `filter`；另建筛选视图不作用于组件 |
| 各维度比率 | 先建 `IF([状态]="<达标值>",1,0)` 公式字段，以 `AVERAGE` 按维度聚合；计数是记录数，不是比率 |
| 按周汇总 | `count_all:true` + 周次 `group_by` + `sort:{"type":"group","order":"asc"}` |

### 宽表多指标横向对比（多个数值字段本身就是要比较的对象）

已确定用汇总表时，分别聚合待比较的数值字段，写入两列汇总表，每个原字段一行，再按“对象”列分组建图：

```text
对象 | 平均值
字段A | <avg_字段A>
字段B | <avg_字段B>
字段C | <avg_字段C>
```

```json
{"table_name":"平均值汇总","series":[{"field_name":"平均值","rollup":"AVERAGE"}],"group_by":[{"field_name":"对象","mode":"integrated","sort":{"type":"view","order":"asc"}}]}
```

### 漏斗图（流程转化）

- 当前数量：`count_all:true` + 状态 `group_by`。
- 累计数量：使用已准备的阶段汇总表；累计数量字段以 `SUM` 聚合，阶段字段用 `sort:{"type":"view","order":"asc"}` 按行序展示。

### 多表需求与聚合失败的恢复边界

用户明确要求把多张表的数据放进同一个图表（含漏斗图）时，先按 [多数据源协议](dashboard-multi-source.md) 构造 `data_sources`，逐源核对真实表、字段、聚合与阶段／维度。多源不是物理 JOIN，同一阶段能否汇总仍要核对实际结果。不要默认复制记录、新建辅助汇总表或把全部指标改从一张表读取来模拟多源；辅助表只用于源表及已支持的多源聚合确实无法表达的派生口径，不能冒充用户点名的来源。

遇到 `SUM not supported by field` 等拒绝时，核对原字段及公式／查找引用的实际返回类型、单位和目标环境支持的聚合：不因外层是公式就认定非数值，也不因样例像数字就认定可求和。只按错误定位做有界修正并回读；不用 `--no-validate` 绕过服务端限制，不把公式改成手填常量。只有用户要记录数时才可改为 `count_all`，金额不能改成计数。无法保留指定来源与指标口径时，报告受阻的表、字段、聚合及错误，不悄悄删去数据源或宣称完成。进度图不使用普通图表的 `data_sources`，两侧来源遵循进度图协议。

## 常见错误与修复

| 错误／现象 | 修复 |
|---|---|
| `series` 与 `count_all` 同时存在；后端／本地报互斥 | 二选一 |
| 缺 `table_name`；本地报缺必填 | 传表名，不传表 ID |
| `series[].rollup` 枚举非法 | 用 `SUM` / `MAX` / `MIN` / `AVERAGE`；输入不区分大小写，CLI 转大写；计数用 `count_all:true` |
| `group_by` 超 2 个或字段名空 | 保留前 2 个或补 `field_name` |
| 排序枚举非法 | `sort.type` 仅 `group` / `value` / `view`；`order` 仅 `asc` / `desc` |
| `filter` 形态非法 | `conjunction` 用 `and` / `or`；按 [操作符规则](dashboard-filter-conditions.md#filter-格式规则) 选 `operator`；除 `isEmpty` / `isNotEmpty` 外传 `value` |
