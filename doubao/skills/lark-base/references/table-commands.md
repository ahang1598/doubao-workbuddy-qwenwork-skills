# 数据表生命周期命令

本页维护数据表的查询、创建、重命名、删除和复制命令、输入与返回结构，以及异步复制的恢复方式。任务选择、建表决策和业务验收见 [Table Scene](../scenes/table.md)；从本页进入时也须完成其适用前置与验收。

## 管理数据表

| 操作 | 命令 |
|---|---|
| 列出 | `+table-list` |
| 详情 | `+table-get` |
| 创建 | `+table-create` |
| 重命名 | `+table-update` |
| 删除 | `+table-delete` |
| 复制 | `+table-copy` |
| 查询复制状态 | `+table-copy-status` |

命令使用 `--base-token`；已有表通过 `--table-id` 指定，可接受当前 Base 内的表 ID 或名称。创建、重命名和复制使用 `--name` 指定目标名称；`+table-update` 只重命名表，字段变更使用 [字段命令](field-commands.md)。

读取表列表需要 `base:table:read`；`+table-get` 同时读取字段与视图，还需要 `base:field:read` 和 `base:view:read`。删除属于高风险写入，已获相应授权后携带 `--yes`。参数不确定时按主入口读取精确子命令帮助。

## 创建时的初始字段

字段数组先按 [Field 决策](../scenes/field.md#字段决策) 选型；含派生结果时进入 [Formula / Lookup](../scenes/field-formula-lookup.md#计算决策)，批量创建不改变字段验收入口。

`+table-create` 的 `--fields` 是必填的非空字段 JSON 数组，元素复用 [字段创建协议](field-commands.md#创建字段field-create) 和 [字段定义 JSON 契约](field-config.md) 的对象结构；第一个元素成为主字段。当前 CLI 会拒绝省略、空白、空数组或非对象元素；`--fields` 不接受单个字段对象，也不额外套 `fields` 外层对象。

通过允许默认 schema 的 Base 创建路径，平台可能生成带 `文本`、`单选`、`日期`、`附件` 占位字段的初始表；不能依赖默认结构代替目标 schema，也不能在 `+table-create` 中传空字段获取默认表。主字段的删除限制见 [字段删除协议](field-commands.md#删除字段与主字段限制)，业务主字段选择见 [Table 建表决策](../scenes/table.md#记录粒度与初始结构)。

若 [Form Scene](../scenes/form.md#专用收集表与业务表) 已确定使用仅承接表单结果的新表，可采用下列初始字段；是否需要创建人字段由 Scene 的身份决策确定：

```json
[
  {"name":"序号","type":"auto_number"},
  {"name":"提交时间","type":"created_at"}
]
```

业务表的初始字段按实际 schema 构造，不套用上述专用表模板。

可选 `--view` 接受视图 JSON 对象或数组。CLI 先创建表，再逐个创建这些视图；部分成功按 [创建与维护恢复](#创建与维护恢复) 处理。

## 字段 JSON 模板

`+table-create --fields` 与 `+base-create --fields` 同格式。下面覆盖常用类型，照抄后只换名称、选项和关联表：

```bash
lark-cli base +table-create --base-token "<base_token>" --name "<表名>" --as user --fields '[
  {"name":"标题","type":"text"},
  {"name":"状态","type":"select","options":[{"name":"待处理","hue":"Orange"},{"name":"进行中","hue":"Blue"},{"name":"已完成","hue":"Green"}]},
  {"name":"标签","type":"select","multiple":true,"options":[{"name":"A"},{"name":"B"}]},
  {"name":"数量","type":"number","style":{"type":"plain","precision":0,"thousands_separator":true}},
  {"name":"金额","type":"number","style":{"type":"currency","precision":2,"currency_code":"CNY"}},
  {"name":"评分","type":"number","style":{"type":"rating","max":5}},
  {"name":"截止日期","type":"datetime","style":{"format":"yyyy/MM/dd"}},
  {"name":"联系电话","type":"text","style":{"type":"phone"}},
  {"name":"链接","type":"text","style":{"type":"url"}},
  {"name":"负责人","type":"user"},
  {"name":"编号","type":"auto_number","style":{"rules":[{"type":"text","text":"NO-"},{"type":"incremental_number","length":4}]}},
  {"name":"关联客户","type":"link","link_table":"客户表","bidirectional":true,"bidirectional_link_field_name":"关联订单"},
  {"name":"创建时间","type":"created_at","style":{"format":"yyyy/MM/dd HH:mm"}}
]'
```

- `style.type`：number 只有 `plain/currency/rating/progress`；text 只有 `plain/phone/url/email`。`hue` 只有 Red/Orange/Yellow/Lime/Green/Turquoise/Wathet/Blue/Carmine/Purple/Gray。
- 关联字段用 `link_table`（表名或 table_id），不是 `table_id`；字段名写 `关联<表名>`，不与任何表同名。`bidirectional: true` 时必带 `bidirectional_link_field_name: "关联<本表名>"`，否则对端反向字段以本表表名命名，公式会把它当整张表。
- 不支持 `property`、`formatter`、`field_name`+数字 type、`default_value`、`date`；`multiple` 只用于 `select`／`user`（其他类型带了报 `Unrecognized key 'multiple'`）；`link` 必带 `link_table`（缺了报 `invalid_request: Required.`）；`select` 可不带 `options`（空选项表）。公式、查找字段建表后用 `+field-create` 加。
- 返回：`+table-create` 取 `data.table.id`，`+base-create` 取 `data.base.base_token`。

## 复制数据表

`+table-copy` 只在当前 Base 内生成与源表并列的新表；复制整个 Base 使用 `+base-copy`。业务复制范围由 [Scene](../scenes/table.md#复制范围与副本保护) 确定，再按下表映射参数。

| 已确定的复制范围 | 参数与执行语义 |
|---|---|
| 仅结构 | `--range schema`，也是 CLI 默认值；同步返回，不接受等待参数 |
| 结构与记录 | `--range all --wait`；包含记录的复制可能异步执行，`--wait` 在本地等待任务完成。未等待时按返回的任务信息续查 |

`--wait` 只允许用于 `--range all`。`--timeout` 只在包含记录且等待时适用，默认 `5m`，须大于 0 且不超过 `30m`；到达等待时限不取消远端任务，完成判断和续查见下节。

## 复制状态与恢复

- `+table-copy` 和 `+table-copy-status` 返回 `data.table.id`、`data.state` 和 `data.completed`；异步任务另有 `data.task_id`，未完成时可能附带 `next_action`、`next_command`，等待超时另有 `timed_out`。
- `state` 为 `init` / `process` 时任务尚未完成；`state=success` 且 `completed=true` 才表示复制任务完成，之后仍须执行 Scene 的内容对账。命令退出成功或副本 ID 已生成不能替代完成状态。
- `+table-copy-status --base-token <base_token> --task-id <task_id>` 每次查询一次。任务 ID 原样取自提交返回，不自行构造；沿用提交时的身份。未完成时按返回提示在等待预算内续查，预算耗尽报告当前状态，不无限轮询。
- 等待超时或状态查询失败时，任务可能仍在运行；保留输出中的任务信息，恢复查询而不重新复制。提交阶段网络异常且未取得任务信息时，结果未知，先核对目标表是否已生成，不能自动重提。

## 返回解析

- `+table-list`：读取 `data.tables` 与 `data.total`；兼容分页参数为 `--offset` 和 `--limit`，默认 0 和 300，`limit` 范围 1–300。目标已找到可停止；需要全量列表或判定目标不存在时，从 offset 0 按实际返回条数推进，直到覆盖 total。尚未覆盖 total 却出现空页、offset 不增长或重复时，停止并报告读取不完整，不把单页当全量。
- `+table-get`：读取 `data.table`、`data.fields` 和 `data.views`；它不读取表内记录。创建返回 `data.table`，可能另有字段或所创建视图；重命名返回 `data.table` 和 `data.updated`。真实名称和 ID 取自返回对象，不凭输入推断写入结果。
- 配套的 `+field-list`：读取 `data.fields`，字段键为 `id/name/type`。

不猜 `items/field_id/field_name`，不以空数组掩盖解析失败。

## 创建与维护恢复

- 创建结果未知时先读取现状，结合写前对象、真实返回和目标结构识别本次产物；不能仅凭同名认领表，也不能未确认失败就再次创建。确认已创建则复用其 ID，缺少证据时报告结果未知。
- 带 `--view` 创建时，表已成功但后续视图创建失败，命令仍会报错。回读已生成的表与视图，只补失败步骤，不重跑整次创建。
- 重命名或删除响应丢失时，按写前保存的原表 ID 读取现状，再决定是否仍需执行；不能因旧名称查不到就认定删除成功。读取失败与目标不存在分别处理，身份或权限问题沿用主入口。
