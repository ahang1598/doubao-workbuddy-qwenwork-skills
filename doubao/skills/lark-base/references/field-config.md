# 字段定义 JSON 契约

## 目录

适用范围；通用 JSON 规则；创建与更新语义；字段类型转换；字段类型速查；各类型配置；暂不支持字段；易错点。

## 适用范围

适用命令：`lark-cli base +field-create`、`lark-cli base +field-update`；用 `--json` 写字段。

## 通用 JSON 规则（必须遵守）

- 字段对象写 `type`、`name`、类型特有字段。所有类型可写 `description`（纯文本或 Markdown 链接）。
- `default_value` 直接传对应 CellValue；仅 `text`、`number`、静态 `select`、`datetime`、`user` 支持。传 `null` 清空；省略则创建时不设置、更新时不修改。
- 禁用旧结构：`field_name`、`property`、`ui_type`、数字枚举 `type`。

## 创建与更新语义

JSON 顶层形状、批量执行、完整更新、确认参数见[创建协议](field-commands.md#创建字段field-create)和[更新协议](field-commands.md#更新字段field-update)；编号更新见[自动编号](#auto_number-字段)。

## 字段类型转换

下表不保证任意存量数据保留；目标类型接口限制仍优先。

| 目标 | 已列出的源/转换 | 结果 |
|---|---|---|
| `text` | `number`、`select`、`datetime`、`created_at`、`updated_at`、`location`、`auto_number`、`checkbox` | 留字符串，丢失原类型语义和结构；`location` 仅留 `full_address` |
| `number` | `text`、`number`、`datetime`、`created_at`、`updated_at`、`checkbox` | 留可解析数字；不可解析值变空；丢失文本格式 |
| `datetime` | `text`、`number`、`datetime`、`created_at`、`updated_at` | 留可解析时间字符串和时间戳；不可解析值变空；丢失文本格式 |
| `select` | `text -> select`、`number -> select`、`single select -> multi select` | 仅完全匹配目标选项名的值转成选项；未匹配值丢失 |
| 单值 `select` / `user` / `group_chat` | 对应多值字段改为单值 | 仅留第一个选项、人员或群；顶层 `type` 不变也会丢值 |

- `created_at`、`created_by`、`updated_at`、`updated_by`、`formula`、`lookup` 由系统或计算逻辑生成；转换会改变生成行为，且受目标类型限制。
- `link` 限制见[关联字段](#link-字段)；动态选项来源限制见[选项协议](field-options.md#动态选项)。可创建不等于可原地转换；help/dry-run 仅验证本地调用形状，不验证平台能力。
- 以下转换未保证支持或保值：其他类型转入 `checkbox`、`user`、`group_chat`、`attachment`、`location`；静态/动态选项来源切换；其他未列出的转换。来源切换先服从选项协议。

## 字段类型速查

所有类型最小必填 `type`、`name`；下表列额外必填和类型特有可选字段。

| 类型 | 额外必填 | 可选 |
|---|---|---|
| `text` | — | `style.type` `default_value` |
| `number` | — | `style` `default_value` |
| `select` | — | 见下文 |
| `datetime` | — | `style.format` `default_value` |
| `created_at` / `updated_at` | — | `style.format` |
| `user` / `group_chat` | — | `multiple`；仅 `user` 支持 `default_value` |
| `created_by` / `updated_by` | — | — |
| `link` | `link_table` | `bidirectional` `bidirectional_link_field_name` |
| `formula` | `expression` | — |
| `lookup` | `from` `select` `where` | `aggregate` |
| `auto_number` | — | `style.rules` |
| `attachment` | — | `style.type`（`plain` / `signature`） |
| `location` / `checkbox` | — | — |
| `button` | `button_config.title` | — |

`select` 配置为 `multiple` + `options` + 静态 `default_value`，或 `multiple` + `dynamic_options_source`；读[选项配置与更新限制](field-options.md)核对 JSON、默认值和更新限制。
`button` 创建或绑定时读[按钮字段与绑定协议](field-button-binding.md#313-button)。

## 各类型配置

### `text` 字段

电话、超链接、邮箱、条码均为 `text`。`style.type`：`plain`（默认）、`phone`、`url`、`email`、`barcode`。
`default_value` 为静态 Markdown 文本；`phone` 须为合法电话号码；`url` 传一个 Markdown 链接或裸 URL；`email` 须为合法邮箱，不得传 Markdown 链接或 `mailto:`。

`{"type":"text","name":"联系电话","description":"联系方式","style":{"type":"phone"},"default_value":"+8613800000000"}`

### `number` 字段

货币、进度、评分均为 `number`。所有样式的 `default_value` 均为静态 JSON number；精度、货币、进度、评分配置均放入 `style`，不得写顶层 `precision` 或混传不同样式字段。

#### `plain`

`precision` 取 `0..4`、默认 `2`，按已确定精度显式配置；`percentage`、`thousands_separator` 均默认 `false`。

`{"type":"number","name":"金额","style":{"type":"plain","precision":2,"percentage":false,"thousands_separator":true},"default_value":8}`

#### `currency`

`precision` 取 `0..4`、默认 `2`；`currency_code` 必填，如 `CNY`、`USD`、`EUR`。

`{"type":"number","name":"金额","style":{"type":"currency","precision":2,"currency_code":"CNY"}}`

#### `progress`

`percentage` 默认 `true`；`color` 必填，枚举：`Blue`、`Purple`、`DarkGreen`、`Green`、`Cyan`、`Orange`、`Red`、`Gray`、`WhiteToBlueGradient`、`WhiteToPurpleGradient`、`WhiteToOrangeGradient`、`GreenToRedGradient`、`RedToGreenGradient`、`BlueToPinkGradient`、`PinkToBlueGradient`、`SpectralGradient`。

`{"type":"number","name":"进度","style":{"type":"progress","percentage":true,"color":"Blue"},"default_value":0.65}`

#### `rating`

- `icon` 默认 `star`；枚举：`star`、`heart`、`thumbsup`、`fire`、`smile`、`lightning`、`flower`、`number`。
- `min` 取 `0..1`，默认 `1`。
- `max` 默认 `5`；常见或已文档化范围 `1..10`，但 CLI 不强制上限 `10`；CLI 接受请求形状不证明平台支持该范围。

`{"type":"number","name":"评分","style":{"type":"rating","icon":"star","min":1,"max":5}}`

### `datetime` 字段

手动填写日期/时间；系统时间用 `created_at` / `updated_at`。`default_value` 为静态时间字符串或 `{"$slot":"record_created_time"}`；后者自动填充可编辑单元格，`created_at` 是只读创建时间元信息。

`style.format` 默认 `yyyy/MM/dd`；枚举：`yyyy/MM/dd`、`yyyy/MM/dd HH:mm`、`yyyy/MM/dd HH:mm Z`、`yyyy-MM-dd`、`yyyy-MM-dd HH:mm`、`yyyy-MM-dd HH:mm Z`、`MM-dd`、`MM/dd/yyyy`、`dd/MM/yyyy`。它仅控制前端显示，最多到分钟；底层值仍可保留秒级精度。

`{"type":"datetime","name":"日期","style":{"format":"yyyy-MM-dd HH:mm"},"default_value":{"$slot":"record_created_time"}}`

### `created_at / updated_at` 字段

系统创建/更新时间；记录写入时只读。`style.format` 默认值和枚举同 `datetime`。

<a id="36-user--group_chat"></a>

### `user / group_chat` 字段

引用飞书群对象用 `group_chat`；群名称等描述文本用 `text`；两者的 `multiple` 默认 `true`。
`user.default_value` 为人员 CellValue 数组，元素用 `{"id":"ou_xxx"}` 或 `{"$slot":"current_user"}`；不得猜用户 ID。`group_chat` 不支持默认值。

`{"type":"user","name":"负责人","multiple":true,"default_value":[{"$slot":"current_user"},{"id":"ou_xxx"}]}`

### `created_by / updated_by` 字段

系统创建人/修改人；记录写入时只读。

### `link` 字段

- `link_table` 必填；不支持 `multiple`。关联数量由 link CellValue 的记录 ID 对象数组表达，见[关联单元格](record-cell-values.md#关联记录link)；单元格表示当前记录关联到的对侧表记录集合。
- `bidirectional` 默认 `false`；为 `true` 时在被关联表自动创建反向字段；任一侧关系变化同步另一侧对应记录。
- 未指定名称时，`name` 和仅双向使用的 `bidirectional_link_field_name` 写成 `关联<表名>`，不得与任何表同名；同名会使公式 `[名称].[字段]` 按表名解析并取整张表，而非关联记录。
- 关联字段筛选是 Base 前端的 UI-only 属性；OpenAPI 不支持，CLI 无法读取、创建、更新；不得因接口返回缺失判定未配置。

`{"type":"link","name":"关联订单表","link_table":"订单表","bidirectional":true,"bidirectional_link_field_name":"反向关联"}`

更新限制：`link` 不得与其他类型互转；现有 `link.bidirectional` 不得修改。

<a id="39-formula"></a>

### `formula` 字段

`expression` 必填。先完成[计算决策](../scenes/field-formula-lookup.md#计算决策)，再按[表达式](field-formula-expression.md)和[函数](field-formula-functions.md)构造；初始字段数组与单独创建使用同一入口。

`{"type":"formula","name":"合计","expression":"1+1"}`

### `lookup` 字段

先按上述计算决策确定来源和条件，再按[Lookup 配置](field-lookup-config.md)构造。
`from`、`select`、`where` 必填。`aggregate` 默认 `raw_value`（不聚合，返回 `select` 原始值）；枚举 `raw_value`、`sum`、`average`、`counta`、`unique_counta`、`max`、`min`、`unique`。
`where.logic` 默认 `and`，仅支持 `and` / `or`；`where.conditions` 至少 1 条，每项为 `[field, op, value?]`。

`{"type":"lookup","name":"状态汇总","from":"订单表","select":"状态","where":{"logic":"and","conditions":[["负责人","==",{"type":"field_ref","field":"当前负责人"}],["状态","non_empty",null]]},"aggregate":"raw_value"}`

### `auto_number` 字段

创建时省略 `style.rules` 使用默认规则 `NO.001`：`{"rules":[{"type":"text","text":"NO."},{"type":"incremental_number","length":3}]}`。
更新时必须显式提交目标 `style.rules`；`+field-update` 会把新规则重新用于已有编号，无需额外参数，不得添加底层实现参数。

`style.rules` 是 `1..9` 条规则：`text` 含 `text`；`incremental_number` 含 `length`（`1..9`）；`created_time` 含 `date_format`，枚举 `yyyyMMdd`、`yyyyMM`、`yyMM`、`MMdd`、`yyyy`、`MM`、`dd`。

`{"type":"auto_number","name":"编号","style":{"rules":[{"type":"text","text":"NO."},{"type":"created_time","date_format":"yyyyMMdd"},{"type":"incremental_number","length":4}]}}`

### `attachment` 字段

普通附件省略 `style`，等同 `style.type: "plain"`。签字是附件的 `style.type: "signature"`，不存在顶层 `"type":"signature"`。

`{"type":"attachment","name":"确认签字","style":{"type":"signature"}}`

签字单元格只读：写入、替换、清空均无效，签名只能由用户在飞书客户端完成。不得放入记录写入或调用 `+record-upload-attachment` / `+record-remove-attachment`。
这些操作返回成功，但字段进入 `ignored_fields`，`reason` 为 `SIGNATURE_READONLY`，不得视为写入成功。上传先传媒体再被追加接口忽略，媒体不自动回滚。读取、下载同普通附件。

### `location` 字段

写入必须用 `{lng,lat}`。读回含 `full_address`；筛选和 `location -> text` 转换按 `full_address` 字符串处理；仅公式能访问坐标。

### `checkbox` 字段

`{"type":"checkbox","name":"完成"}`

## 暂不支持字段

Object（对象字段）、Stage（流程字段）暂不受 CLI 支持；显示为 `not_support` 并受保护：不得修改、读取内容。

## 易错点

`select` 仅有一个类型；不得写 `single_select` / `multi_select`，用 `multiple` 控制单/多选。
