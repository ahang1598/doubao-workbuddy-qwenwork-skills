# Contact field enrichment

用它把已有人员信息列补全为新的只读派生列。先用 `+field-list` 确认来源：`source_field` 可传字段 ID 或名称，但必须是现有的单值 `user`（`multiple: false`）或 `created_by` 字段，不能是另一列 enrichment。

`info_type` 只支持 `department`、`direct_manager`、`employee_number`、`job_title`、`employee_type`、`work_email`。同一张表内，相同来源字段与 `info_type` 的组合只能创建一次。

```jsonc
// 一个来源、一个补全项
{"enrichments":[{"source_field":"人员","info_type":"department"}]}
```

```jsonc
// 一个来源批量补全多项；source_field 也可以传 fld... ID
{"enrichments":[
  {"source_field":"fld_people","info_type":"direct_manager"},
  {"source_field":"fld_people","info_type":"work_email"}
]}
```

## 推荐命令

```bash
lark-cli base +contact-field-enrichment-create \
  --base-token <base_token> \
  --table-id <table_id> \
  --json '<上面的 JSON>' \
  --as user

lark-cli base +contact-field-enrichment-list \
  --base-token <base_token> \
  --table-id <table_id> \
  --as user
```

## API 入参详情

创建使用：

```
POST /open-apis/base/v3/bases/:base_token/tables/:table_id/contact_field_enrichments
```

查询使用：

```
GET /open-apis/base/v3/bases/:base_token/tables/:table_id/contact_field_enrichments
```

## 工作流

1. 先用 `+field-list` 确认表中存在符合条件的单值人员或创建人字段，并记录其字段 ID 或名称。
2. 按 `info_type` 白名单构造 `--json`；多个补全项可以放在同一个 `enrichments` 数组中。
3. 创建返回当前完整快照；随后使用 `+contact-field-enrichment-list` 读取关系，确认 `source_field`、`info_type` 和生成字段。

生成列在 enrichment 关系存在期间由系统维护且只读，不要通过 Record 或 CellValue 写入命令手动更新。若返回 `error_message`，表示该关系已停止更新，应先处理对应来源字段或权限问题。
