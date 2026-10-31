# 记录写入与删除命令

## 适用范围与公共限制

`+record-upsert`、`+record-batch-create`、`+record-batch-update` 写入及 `+record-delete` 删除需要相应权限。构造值前读取 [CellValue 协议](record-cell-values.md)；字段标识、可写类型、选项值依该协议，附件依 [专用协议](record-attachments.md)。

- 写入只用 `--json`，不得生成 `--records` 或外包 `fields`；三个写命令的外层 JSON 各不相同。
- 批量创建、更新每批最多 200 条；同表连续写入必须串行。冲突处理见 [通用恢复](shared-cli-invocation.md#通用恢复)。

## 命令选择与公共参数

|命令|操作；`--json` 形状|
|---|---|
|`+record-upsert`|无 `--record-id` 创建，有则更新；顶层为字段映射|
|`+record-batch-create`|批量创建；`create_records` 为记录字段对象数组|
|`+record-batch-update`|批量更新；`update_records` 为记录 ID 到字段更新对象的映射|
|`+record-delete`|删除明确指定的记录；参数见命令帮助|

写命令均须传 `--base-token <token>`（Base Token）和 `--table-id <id_or_name>`（表 ID 或表名）。其他参数见下文。

## 单条创建或更新：+record-upsert

有 `--record-id <id>` 时一定更新并调用 `PATCH /records/:record_id`；不传时一定创建并调用 `POST /open-apis/base/v3/bases/:base_token/tables/:table_id/records`，不会查重或按业务键 upsert。须传 `--json <body>`：顶层必须是 `Map<FieldNameOrID, CellValue>` JSON object，key 为字段名或字段 ID，value 为该字段 `CellValue`。

```bash
# 创建
lark-cli base +record-upsert --base-token "<base_token>" --table-id "<table_id>" --json '{"状态":["进行中"]}'
# 更新
lark-cli base +record-upsert --base-token "<base_token>" --table-id "<table_id>" --record-id "<record_id>" --json '{"状态":"完成","日期":"2026-03-24 10:00:00"}'
```

创建返回 `record`、`created: true`；更新返回 `record`、`updated: true`；可选 `ignored_fields` 见 [CellValue 只读边界](record-cell-values.md#只读字段与附件边界)。

## 批量创建：+record-batch-create

用于 CSV/Excel、外部系统批量导入新数据。将每条输入映射为独立字段对象后放入 `create_records`；各记录可提交不同字段。必须传 `--json <body>` JSON 对象，可直接传字符串或用 `@<file_path>` 读文件。

- API：`POST /open-apis/base/v3/bases/:base_token/tables/:table_id/records/batch_create`
- `create_records`：必填 `Array<Map<FieldNameOrID, CellValue>>`，上限见公共限制。

```bash
lark-cli base +record-batch-create --base-token "<base_token>" --table-id "<table_id>" --json '{"create_records":[{"状态":["Open"]},{"状态":["Done"],"金额":20}]}'
lark-cli base +record-batch-create --base-token "<base_token>" --table-id "<table_id>" --json @batch-create.json
```

返回 `record_id_list` 和可选 `ignored_fields`。

## 批量更新：+record-batch-update

必须传 `--json <body>` JSON 对象，可直接传字符串或用 `@<file_path>` 读文件。

- API：`POST /open-apis/base/v3/bases/:base_token/tables/:table_id/records/batch_update`
- `update_records`：必填 `Map<RecordID, Map<FieldNameOrID, CellValue>>`；各记录可更新不同字段，上限见公共限制。

```bash
lark-cli base +record-batch-update --base-token "<base_token>" --table-id "<table_id>" --json '{"update_records":{"<record_id_a>":{"状态":["完成"]},"<record_id_b>":{"金额":20}}}'
lark-cli base +record-batch-update --base-token "<base_token>" --table-id "<table_id>" --json @batch-update.json
```

成功响应只含可选 `ignored_fields`；无忽略字段时 `data` 是空对象，不返回记录列表。请求不预检 record ID 是否存在；用请求目标 ID 回读，不得等待响应提供 ID，也不得以空 `data` 判定目标存在。命令不转换字段/行映射，原样发送；超限会被接口拒绝。`ignored_fields` 边界与含义见 [CellValue](record-cell-values.md#只读字段与附件边界)。

## 删除记录：+record-delete

删除明确指定的 `record_id`：`--record-id <id1> --record-id <id2> --yes`（可重复，没有 `--record-ids`）；其他参数按 `+record-delete --help`。命令有 CLI confirmation gate。

## 字段与记录错误

|错误|恢复|
|---|---|
|`1254045` 字段名不存在|重新 `+field-list`，使用真实字段名或字段 ID；核对空格、大小写、跨表字段|
|`1254015` 或日期／人员／超链接格式错误|先用 `+field-list` 确认真实类型，再按 [CellValue](record-cell-values.md) 构造值|
|`ignored_fields` / `READONLY`|所列只读字段未更新，其他字段可能已写入；按 [只读边界](record-cell-values.md#只读字段与附件边界) 修正可写字段，不得重试相同 payload|
|`1254104` 超过批量上限|按公共上限拆分；冲突或未知结果按 [通用恢复](shared-cli-invocation.md#通用恢复) 处理|
