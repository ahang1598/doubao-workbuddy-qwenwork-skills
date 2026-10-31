# 数据查询 JSON DSL 契约

## 目录

- [职责与前置条件](#职责与前置条件)
- [限制](#限制)
- [调用与参数](#调用与参数)
- [常用聚合与示例](#常用聚合与示例)
- [API 入参详情](#api-入参详情)
- [CLI 出参详情](#cli-出参详情)
- [维度行与记录身份](#维度行与记录身份)
- [坑点](#坑点)
- [相关协议](#相关协议)
- [DSL 日期分段与均值核验](#dsl-日期分段与均值核验)

## 职责与前置条件

本页定义 `+data-query` 的 DSL、字段类型、操作符、参数、返回和局部错误诊断。先由 [Query](../scenes/query.md#任务导航与计算模式) 确定选路和结构前置；本页不授权回退或重试。
自然语言条件按 [共享统计规则](shared-statistics-rules.md#自然语言条件与字段充分性) 判定。原始记录筛选、全量导出和本地复算仅在当前路径允许时按 [Record](record-read.md) 执行。

## 限制

| 项 | 约束 |
|---|---|
| 权限 | 普通多维表格需文档阅读权限；高级权限多维表格需文档管理员的 FA（Full Access）；不足时返回权限错误 |
| 精度 | 数值聚合有精度限制；成功不代表满足精确十进制。复算触发、取数权限由 [Query](../scenes/query.md#精度与受控回退) 决定；误差、Decimal 输入、舍入见 [复算方法](shared-statistics-rules.md#精确十进制复算方法) |
| 执行端 | 云端执行 `filters`、`dimensions`、`measures`、`sort`、`pagination.limit`；limit 限制云端结果，不是本地分页扫描 |

## 调用与参数

URL 形如 `https://example.feishu.cn/base/<base_token>?table=<block_id>`。`table=` 是 Base 顶层块，可能为数据表、仪表盘、工作流、文件夹或文档，不得直接当数据表 ID。执行：

```bash
lark-cli base +url-resolve --url "<url>" --as user
```

以返回的 `base_token` 作 `--base-token`。仅当 `block_type=table` 时，以 `table_id` 作 `tableId`；其他类型按 `hint.next_step` 处理；仅有中性 `block_id` 时，用 `+base-block-list` 确认类型并选表。

| 参数 | 必填 | 说明 |
|---|---|---|
| `--base-token <token>` | 是 | Base Token（`base_token`） |
| `--dsl <json>` | 是 | LiteQuery Protocol JSON DSL |

## 常用聚合与示例

### 聚合选择与高频限制

- 聚合名只能是 `sum`、`avg`、`min`、`max`、`count`、`count_all`、`distinct_count`，不用 `average`、`distinct count` 等自然语言别名。
- 分类记录数用 `count_all`，包括分类字段为空的记录；字段非空数才用 `count`。状态为 `Done` 和空值各一条时，两组记录数均为 1；`count(状态)` 对空值组为 0，不代表该组无记录。
- 日期字段只支持 `is`、`isEmpty`、`isNotEmpty`、`isGreater`、`isLess`，不用 `isGreaterEqual` / `isLessEqual`。
- 以下是普通云端聚合，不保证精确十进制对账或边界舍入。触发复算时读取同一总体的原始数值；舍入可能改变聚合 TopN 成员时，仅云端胜者不是充分复算总体。
- 获准全量原始导出时按 [Record 输出契约](record-read.md#解析返回与完整分页)：优先 NDJSON；选 JSON 矩阵才用 JSON 分页规则。输出形式不改变选路或回退条件。

### 常用示例

按状态统计记录数：

```bash
lark-cli base +data-query --base-token "<base_token>" \
  --dsl '{"datasource":{"type":"table","table":{"tableId":"<table_id>"}},"dimensions":[{"field_name":"状态","alias":"status"}],"measures":[{"field_name":"状态","aggregation":"count_all","alias":"count"}],"shaper":{"format":"flat"}}'
```

筛选后按负责人汇总、降序取 Top 10：

```bash
lark-cli base +data-query --base-token "<base_token>" \
  --dsl '{"datasource":{"type":"table","table":{"tableId":"<table_id>"}},"dimensions":[{"field_name":"负责人","alias":"owner"}],"measures":[{"field_name":"金额","aggregation":"sum","alias":"total"}],
  "filters":{"type":1,"conjunction":"and","conditions":[{"field_name":"状态","operator":"is","value":["Done"]}]},"sort":[{"field_name":"total","order":"desc"}],"pagination":{"limit":10},"shaper":{"format":"flat"}}'
```

只知表名时以 `tableName` 代替 `tableId`：

```json
{"datasource":{"type":"table","table":{"tableName":"订单表"}},"measures":[{"field_name":"金额","aggregation":"sum","alias":"total"}]}
```

限定已有视图时传真实 `viewId`；服务端合并筛选，不复制 view filter：

```json
{"datasource":{"type":"table","table":{"tableId":"<table_id>","viewId":"<view_id>"}},"dimensions":[{"field_name":"状态","alias":"status"}]}
```

## API 入参详情

`POST /open-apis/base/v3/bases/:base_token/data/query`；Path 参数 `base_token` 必填。路径不是 `bitable/v1`，用错版本号返回 `[2200] Internal Error`。

### Request Body — DSL 结构

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| `datasource` | object | 是 | `type` 固定 `"table"`，含 `table` |
| `datasource.table.tableId` / `tableName` | string | 二选一 | 数据表 ID（如 `tblXXX`）/用户自定义显示名；不得混用 |
| `datasource.table.viewId` | string | 否 | 真实视图 ID；服务端合并筛选并限定记录范围 |
| `dimensions` | Dimension[] | 否* | GROUP BY；项含必填 `field_name:string`、可选 `alias:string` |
| `measures` | Measure[] | 否* | 项含必填 `field_name:string`、`aggregation:string`，可选 `alias:string` |
| `filters` | FilterGroup | 否 | WHERE |
| `sort` | Sort[] | 否 | 项含必填 `field_name:string`（字段名或 alias）、可选 `order`：`"asc"`（默认）/`"desc"` |
| `pagination` | object | 否 | `{"limit":N}`；N 为正整数，最大 5000，超限报错；省略用系统默认值；不支持 offset |
| `shaper` | object | 否 | 可省略；传入时必填 `format:"flat"`，返回扁平对象数组；不猜其他格式 |

\* `dimensions`、`measures` 至少填一个，否则 DSL 校验错误。alias 可用中英文，须全局唯一（两者间也不可重名）；排序引用时逐字一致。

### 聚合函数适用字段类型

| 聚合 | 类型/含义 |
|---|---|
| `sum` / `avg` | `number` |
| `min` / `max` | `number`、`datetime` |
| `count` | 全字段；非空值数 |
| `count_all` | 全字段；所有行数 |
| `distinct_count` | 全字段 |

`number` 包含 `style.type` 为 `progress` / `currency` / `rating` 等所有子类型。`ok=true` 但某个 `sum` / `avg` / `min` / `max` 的 `value` 为 `null` 时，按[聚合成功但 measure 为 null](#聚合成功但-measure-为-null) 处理。

### FilterGroup 与 Condition

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| `type` | int | 是 | 固定 `1` |
| `conjunction` | string | 否 | `"and"` / `"or"`，默认 `"and"` |
| `conditions` | Condition[] | 否 | 条件列表 |
| `conditions[].field_name` | string | 是 | 字段名 |
| `conditions[].operator` | string | 是 | 见下列映射 |
| `conditions[].value` | string[] | 是 | 条件值；`isEmpty` / `isNotEmpty` 必须为 `[]` |

运算符：`is` 等于；`isNot` 不等于；`contains` 包含；`doesNotContain` 不包含；`isEmpty` 为空；`isNotEmpty` 不为空；`isGreater` 大于；`isGreaterEqual` 大于等于；`isLess` 小于；`isLessEqual` 小于等于。

### 各字段类型的运算符与 value 格式

下表的“空”=`isEmpty` / `isNotEmpty`，value 均为 `[]`；“比较”=`isGreater` / `isGreaterEqual` / `isLess` / `isLessEqual`。

| 类型 | 非空运算符；value | 补充约束 |
|---|---|---|
| `text` | `is/isNot/contains/doesNotContain`；`["Hello"]` 仅 1 个；另支持空 | 不支持比较；覆盖 `style.type=plain`（默认）/`phone/url/email/barcode`；url 筛显示名称，不筛 URL |
| `number` | `is/isNot/比较`；`["23.4"]` 仅 1 个合法数字字符串；另支持空 | 覆盖 `plain`（默认）/`currency/progress/rating`；34%=0.34；rating 必须为整数 |
| `auto_number` | `is/isNot/contains/doesNotContain/比较`；`["00001"]` 仅 1 个；另支持空 | — |
| `select` | `is/isNot` 仅 1 个；`contains/doesNotContain` 可多个；另支持空 | 不支持比较；`multiple=false`（默认）为单选，`multiple=true` 为多选 |
| `user` / `created_by` / `updated_by` | `is/isNot/contains/doesNotContain` 均可多个；如 `["ou_aaa","ou_bbb"]`；另支持空 | 不支持比较；使用 `open_id`（`ou_`），接口自动转换 ID |
| `group_chat` | 同 user；如 `["oc_aaa","oc_bbb"]` | 不支持比较 |
| `link` | 同 user；如 `["recAAA","recBBB"]` | 不支持比较；传关联表 `record_id`；`bidirectional=true` 的双向关联规则相同 |
| `location` | `is/isNot/contains/doesNotContain`；full_address 字符串仅 1 个；另支持空 | 不支持比较和经纬度空间筛选；查城市/片区优先 `contains`，避免 `is` 匹配短地址词 |
| `checkbox` | 仅 `is`；`["true"]` / `["false"]` 仅 1 个 | 不支持其他运算符 |
| `attachment` | 仅空 | 不支持其他运算符 |
| `datetime` / `created_at` / `updated_at` | 仅 `is/isEmpty/isNotEmpty/isGreater/isLess`；见下节 | — |
| `formula` / `lookup` | 按结果类型套用本表 | 数字→number；日期→datetime；单选→select |

#### `datetime` / `created_at` / `updated_at`

value 首元素为大小写敏感的关键字；写错校验失败。

| 关键字 | 含义；value | 运算符 |
|---|---|---|
| `ExactDate` | 精确日期；`["ExactDate","1773187200000"]`（毫秒时间戳） | `is/isGreater/isLess` |
| `Today` / `Tomorrow` / `Yesterday` | 今天/明天/昨天；如 `["Today"]` | `is/isGreater/isLess` |
| `CurrentWeek` / `LastWeek` / `CurrentMonth` / `LastMonth` | 本周/上周/本月/上月；如 `["CurrentMonth"]` | 仅 `is` |
| `TheLastWeek` / `TheNextWeek` / `TheLastMonth` / `TheNextMonth` | 过去/未来七天、过去/未来三十天；如 `["TheLastWeek"]` | 仅 `is` |

- `ExactDate` 筛选时转为文档时区当天零点，跨时区可能偏移一天；不用“边界减 1 毫秒”猜测修复。
- 连续窗口按文档时区表达，不把 UTC 零点当本地边界。`isGreater` / `isLess` 是开区间；`> start` 且 `< next_start` 不等于 `[start,next_start)`，会排除起始边界记录。
- 本月、上月等受支持的完整日历范围用对应范围关键字和 `is`。
- 仅当所有候选值均为日期粒度零点值时，左边界可外移至前一天零点，右边界保持下一窗口起始日零点；含具体时刻时左移会混入前一天记录，不得套用。
- 日期无 `isGreaterEqual`。未验证等价表达前，不把两个开区间称为完整月份。由 Query 判断等价查询或完整原始值复算路径，否则报告边界限制；SQL 已失败时不得循环回退 SQL。

```json
{"type":1,"conjunction":"and","conditions":[{"field_name":"日期","operator":"isGreater","value":["ExactDate","<前一天文档时区零点毫秒>"]},{"field_name":"日期","operator":"isLess","value":["ExactDate","<下一窗口起始日文档时区零点毫秒>"]}]}
```

## CLI 出参详情

成功响应写 stdout，信封为 `{ok,identity,data}`。失败退出码非零；typed 错误写 stderr，信封为 `{ok:false,identity,error}`，`error` 在顶层。
未结构化错误按实际 stderr 报告，不当作空结果。按 [响应解析协议](shared-cli-invocation.md#响应解析) 判断成功、隔离并解析输出。

```json
{"ok":true,"identity":"user","data":{"main_data":[{"status":{"value":"Done"},"count":{"value":1}}]}}
```

```json
{"ok":false,"identity":"user","error":{"type":"api","subtype":"unknown","code":800004006,"message":"...does not exist in table schema","hint":"...","log_id":"..."}}
```

| 字段 | 类型 | 含义 |
|---|---|---|
| `ok` | bool | 是否成功 |
| `identity` | string | `user` / `bot` |
| `data.main_data` | []object | 成功结果行；未做输出投影也从此读取 |
| 行的 key | string | DSL alias；省略 alias 时为自动列名 |
| 行的 value | CellValue | `{"value":...}`；展示值（人员名称、选项名称、格式化日期等）或数值 |
| `error` | object | typed 错误：`type/subtype/code/message/hint/log_id` |

示例省略号是占位，不可提交。

### 聚合成功但 measure 为 null

`ok=true` 只表示 DSL 已执行。聚合列 `{"value":null}` 常因字段真实类型或 formula / lookup 结果类型不适用于该聚合，例如对文本化百分比、lookup 文本、附件或关联字段做 `avg` / `sum`。不得立即全量导出或打开 help 试错；依次执行：

1. 用 `+field-list` 确认真实 `type`、`style.type`、formula 表达式、lookup 来源和聚合配置；已读且仍有效时复用。
2. 对照[聚合函数适用字段类型](#聚合函数适用字段类型)：`sum` / `avg` 只用于 number；`min` / `max` 用于 number 或 datetime；计数用 `count` / `count_all` / `distinct_count`。
3. 有语义等价的底层 number 或分子/分母时，记录真实来源和类型；number/progress 用底层比例（34%=0.34），不平均展示文本。

交 [Query](../scenes/query.md#精度与受控回退) 决定改写或读取原始记录；不得从成功、null 或相近字段推断零值、业务等价或回退授权。获准后按 [Record 分页与字段映射](record-read.md#解析返回与完整分页) 读取。

## 维度行与记录身份

- 只传 `dimensions` 时返回按字段组合去重的维度行，不含 `record_id`，不等于逐条原始记录。
- 聚合或维度查询后需读取逐条记录时，先把业务编号字段作为 dimension，让 `+data-query` 返回可回查的业务 key。
- 超过 `pagination.limit` 或需全量原始记录时，不得把有限结果当全量；按已授权的 [Record 范围与分页](record-read.md#解析返回与完整分页) 处理。默认页 Record 只能证明已读范围；云端聚合或本地复算由 Query 决定。

## 坑点

- `field_name` 必须与表中名称精确匹配并区分大小写；不得猜测。先执行 `lark-cli base +field-list --base-token <base_token> --table-id <table_id>`。

## 相关协议

[Record](record-read.md)、[统计规则](shared-statistics-rules.md)、[CellValue](record-cell-values.md)、[字段类型与 JSON](field-config.md)

## DSL 日期分段与均值核验

本节仅诊断已获准 DSL 路径，不授权回退或原始记录读取。

- 按 [datetime 边界协议](#datetime--created_at--updated_at) 构造连续日历窗口，使公共边界恰归一个分段。相邻开区间会同时漏掉公共边界；不得因共用分界日就判定无遗漏。分开处理日期零点值例外和含时刻字段。
- 将各段计数和与分段并集的目标总窗口计数比较；保留相同非日期条件、最外层起止范围和空日期处理，只移除内部分段条件，不用移除所有日期过滤后的全历史总数。
  检查起点、公共边界、终点和空日期归属；不一致时交 Query 定向修正，证实覆盖前不得作全量结论。
- `avg` 已舍入且 `sum(field)`、`count(field)` 对应相同筛选和有效数值时，用二者之比恢复比较所需均值；count=0 时均值未定义；sum 也舍入时不能恢复原精度。将证据交 Query 判断是否触发完整原始值复算，本节不要求导出。
