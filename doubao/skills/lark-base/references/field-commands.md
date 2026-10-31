# 字段管理命令 Reference

## 目录

- [调用与边界](#调用与边界)；[字段查找与完整性](#字段查找与完整性)；[删除字段与主字段限制](#删除字段与主字段限制)
- [计算字段阅读确认](#计算字段阅读确认)；[创建字段](#base-field-create)；[更新字段](#base-field-update)
- [批量创建部分成功](#批量创建部分成功)；[更新结果异常](#更新结果异常)；[签字字段异常](#签字字段异常)

## 调用与边界

列、查、删字段使用 `+field-list/get/delete/search-options`；均依赖目标表权限。

## 字段查找与完整性

用 `+field-list --base-token <base_token> --table-id <table_id>` 读取 `data.fields` 和 `data.total`。逐页查找时使用兼容参数 `--offset`、`--limit`（上限 300）：

```bash
lark-cli base +field-list \
  --base-token "<base_token>" --table-id "<table_id>" --offset 0 --limit 200 \
  --jq '.data | {total, page_count: (.fields | length), fields: [.fields[] | {id, name, type}]}'
```

- 在返回数据中逐字比对字段名；不得把字段名或其他外部文本拼入 shell/JQ 表达式。
- 找齐目标即停止。仍缺失时，仅当 `page_count > 0` 且 `offset + page_count < total`，才以两者之和作为下一页 `--offset`。
- 遇到空页、offset 未增长或第二次出现同一 offset，停止、报告读取不完整且不重复请求；穷尽分页前不得判定字段不存在。
- 上述投影仅含身份和类型。查配置或选项时读取完整字段详情；`+field-list` 最多返回 50 个选项，完整值域用 `+field-search-options`。

### 计算字段回读

`+field-get` 返回字段定义；公式表达式是展示表达式，不含逐条记录的计算结果。用 `+record-list` 读取 Formula / Lookup 实际值；筛选、投影、限制和分页见[记录读取契约](record-read.md)。
定义与实际值分别用于 [Formula / Lookup Scene 验收](../scenes/field-formula-lookup.md#回读验收)；定义不得替代计算结果。

## 删除字段与主字段限制

`+field-delete` 删除底层字段及已有值。主字段不可删除，服务端返回 `800080207`；不得反复删除主字段来修正初始 schema。
表单题目移除不等于底层字段删除；参数和保留语义见[删除题目协议](form-questions.md#删除题目form-questions-delete)，授权范围见 [Form Scene](../scenes/form.md#移除题目与底层字段保护)。

## 计算字段阅读确认

`+field-create` / `+field-update` 的 `type` 为 `formula` 或 `lookup` 时，先完成 [Scene 阅读前置](../scenes/field-formula-lookup.md#阅读前置)，再传隐藏参数 `--i-have-read-guide`；传参不得代替阅读。
缺参时 CLI 拒绝并提示兼容入口 [Formula](lark-base-field-formula.md) / [Lookup](lark-base-field-lookup.md)。该确认不替代更新所需的 `--yes` 或完整定义。

<a id="base-field-create"></a>

## 创建字段：+field-create

创建一个或多个字段；Formula / Lookup 同时遵守[计算字段阅读确认](#计算字段阅读确认)。

### 参数与接口

| 参数 | 必填 | 值 |
|---|---|---|
| `--base-token` | 是 | `<token>` |
| `--table-id` | 是 | `<id_or_name>` |
| `--json` | 是 | 单个字段对象或字段对象非空数组 |

`POST /open-apis/base/v3/bases/:base_token/tables/:table_id/fields`

### JSON 值规范

- `--json` 顶层直接传单个对象或非空数组，不套 `fields`；每个对象至少含 `name`、`type`，且必须合法。
- 数组按序创建，首个失败即停止且不自动回滚。`created`、`failed`、`not_attempted` 分别表示已创建、失败、未执行项；`hint` 给出修正提示。部分成功按[批量创建恢复](#批量创建部分成功)处理。
- 所有类型均可传纯文本或 Markdown 链接 `description`。要求默认值时传对应 CellValue `default_value`；`datetime` / `user` 动态填充用 `$slot`。完整规则见 [field-config.md](field-config.md)。
- `select`：`multiple` 控制多选；`options` 与 `dynamic_options_source` 分别定义静态和动态来源，二选一且不得同传；JSON、默认值和限制见[选项配置协议](field-options.md)。
- `link`：必传 `link_table`；可传 `bidirectional`、`bidirectional_link_field_name`。
- `formula`：必传 `expression`，见[表达式契约](field-formula-expression.md)。
- `lookup`：必传 `from`、`select`、`where`，见[查找引用契约](field-lookup-config.md)。
- 签字字段没有 `"type":"signature"`；用 `attachment` + `style.type:"signature"`，见[附件字段配置](field-config.md#attachment-字段)。接口拒绝该 style 时不得降为普通附件重试，按[签字字段异常](#签字字段异常)处理。

### 调用示例

```bash
lark-cli base +field-create --base-token "<base_token>" --table-id "<table_id>" --json '{"name":"金额","type":"number","style":{"type":"currency","precision":2,"currency_code":"CNY"}}'
lark-cli base +field-create --base-token "<base_token>" --table-id "<table_id>" \
  --json '{"name":"状态","type":"select","multiple":false,"options":[{"name":"A","hue":"Blue","lightness":"Lighter"},{"name":"B","hue":"Green","lightness":"Light"},{"name":"C","hue":"Orange"},{"name":"D","hue":"Red"}]}'
lark-cli base +field-create --base-token "<base_token>" --table-id "<table_id>" --json '{"name":"负责人","type":"user","multiple":false,"description":"参考[字段约定](https://example.com/field-spec)"}'
lark-cli base +field-create --base-token "<base_token>" --table-id "<table_id>" --json '[{"name":"备注","type":"text"},{"name":"金额","type":"number","style":{"type":"currency","precision":2,"currency_code":"CNY"}}]'
lark-cli base +field-create --base-token "<base_token>" --table-id "<table_id>" --as user --json '{"name":"关联客户","type":"link","link_table":"客户表","bidirectional":true,"bidirectional_link_field_name":"关联订单"}'
# formula 不收 style；lookup 必带 where；两者先阅读再确认
lark-cli base +field-create --base-token "<base_token>" --table-id "<table_id>" --as user --i-have-read-guide --json '{"name":"日期状态","type":"formula","expression":"IF(AND([状态]!=\"已完成\",[日期]<TODAY()),\"是\",\"否\")"}'
lark-cli base +field-create --base-token "<base_token>" --table-id "<table_id>" --as user --i-have-read-guide \
  --json '{"name":"客户状态","type":"lookup","from":"客户表","select":"状态","where":{"logic":"and","conditions":[["客户名称","intersects",{"type":"field_ref","field":"关联客户"}]]}}'
```

### 返回重点

- 单对象成功返回 `field`、`created:true`；数组成功返回 `fields`、`total`、`created:true`。
- `field_get_recommended:false` 且 `next_step:"done"` 表示简单字段创建；`field_get_recommended:true` 或 `next_step:"field_get"` 表示回读，`verification_hint` 给出核验提示。
- `field_get_recommended:false` 仅表示命令不要求额外 `+field-get`，不得替代[结构验收](../scenes/field.md#结构验收矩阵)。

<a id="base-field-update"></a>

## 更新字段：+field-update

更新一个已有字段。命令以 `PUT` 全量更新；改变类型或关键配置可能影响整列已有数据的解释、展示或可用性，必须传 `--yes`。
用 `--field-id` 定位字段；JSON 的 `name` 不得代替它。Formula / Lookup 同时遵守[计算字段阅读确认](#计算字段阅读确认)。

### 参数与接口

| 参数 | 必填 | 值 |
|---|---|---|
| `--base-token` | 是 | `<token>` |
| `--table-id` | 是 | `<id_or_name>` |
| `--field-id` | 是 | `<id_or_name>` |
| `--json` | 是 | 字段属性对象 |
| `--yes` | 是 | 确认高风险更新 |

`PUT /open-apis/base/v3/bases/:base_token/tables/:table_id/fields/:field_id`

当 `--json.type` 为 `auto_number` 时仍用该 v3 接口。更新规则会默认应用到已有编号；要求修改已有编号时直接执行 `+field-update`，不得添加额外开关或 JSON 参数触发重排。

### JSON 值规范

- 顶层必须直接传对象。`PUT` 是全量配置更新，不得只传片段；至少显式含 `name`、`type` 并补齐该类型关键配置。
- 所有类型均可传纯文本或 Markdown 链接 `description`。要求默认值时传对应 CellValue `default_value`；传 `null` 清空，省略表示不修改。完整规则见 [field-config.md](field-config.md)。
- `select` 选项形状、来源限制和存量值影响见[选项协议](field-options.md)；`link` 类型与方向限制见[关联字段](field-config.md#link-字段)；`auto_number` 规则和既有编号重算见[自动编号](field-config.md#auto_number-字段)。
- 更新签字字段（`attachment` + `style.type:"signature"`）时必须写回 `style`；漏传会按 `plain` 转成普通附件并丢失签字配置。
- 底层 `attachment -> signature` 会清空该列附件值；签字单元格无法通过 API 写回。误降级按[签字字段异常](#签字字段异常)处理。

### 调用示例

```bash
lark-cli base +field-update --base-token "<base_token>" --table-id "<table_id>" --field-id "<field_id>" \
  --json '{"name":"编号","type":"auto_number","style":{"rules":[{"type":"text","text":"TASK-"},{"type":"created_time","date_format":"yyyyMM"},{"type":"text","text":"-"},{"type":"incremental_number","length":4}]}}' --yes
```

### 返回重点

- 返回 `field`、`updated:true`。它仅表示请求成功，不表示字段结构、已有记录值或下游能力已验证。命令不知道更新前类型，因此成功响应会要求执行 `+field-get`。
- API 判定没有任何变更（no-op）时，命令如实返回该错误。响应类型不匹配或 no-op 按[更新结果异常](#更新结果异常)处理。

## 批量创建部分成功

数组创建在首个失败处停止且不回滚。保留 `created` 项；按 `hint` 修正 `failed` 项，再把它与 `not_attempted` 项按依赖顺序提交；不得重复创建已成功字段。

## 更新结果异常

- 响应 `field.type` 与提交的 `type` 不一致时，标记为待核验的类型不匹配；不得返回完成态或仅按任一类型推断成功。
- no-op 通常表示目标已是期望状态；不得机械重试同一份 `+field-update`。执行 `+field-get` 确认完整状态；发生类型转换时仍须回读并验证完成态，不得以 no-op 代替回读。

## 签字字段异常

- **创建被拒**：使用 `attachment` + `style.type:"signature"`。接口拒绝该 style 时，停止并报告当前环境尚未支持；不得删除 `style` 重试，否则会创建普通附件字段。
- **更新误降级**：漏传 `style` 会按 `plain` 转成普通附件并丢失签字配置。不得再 `PUT` 回 `signature` 自动恢复，因为转换会清空该列附件值。
  不得“新建字段 + 迁移”，因为签字单元格无法通过 API 写回。误降级后停止后续写操作、报告数据风险；恢复方案必须单独验证后再执行。
