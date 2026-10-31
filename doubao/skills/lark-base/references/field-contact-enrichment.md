# 通讯录补全关系 Reference

<a id="职责与前置条件"></a>

## 能力与来源限制

<a id="调用与边界"></a>

**通讯录字段补全**

从人员字段生成只读通讯录派生列，普通 `+field-create` 不能建立此关系。`source_field` 可传字段 ID 或名称，来源必须是现有的单值 `user`（`multiple: false`）或 `created_by` 字段，不能是另一列 enrichment。

`info_type` 只支持 `department`、`direct_manager`、`employee_number`、`job_title`、`employee_type`、`work_email`。同一张表内，相同来源字段与 `info_type` 的组合只能创建一次。

## JSON 结构与示例

带注释的独立 JSON 值。

```jsonc
// 一个来源、一个补全项
{"enrichments":[{"source_field":"人员","info_type":"department"}]}
```
带注释的独立 JSON 值。

```jsonc
// 一个来源批量补全多项；source_field 也可以传 fld... ID
{"enrichments":[
  {"source_field":"fld_people","info_type":"direct_manager"},
  {"source_field":"fld_people","info_type":"work_email"}
]}
```

<a id="推荐命令"></a>

## 创建与查询命令

命令：+contact-field-enrichment-list / +contact-field-enrichment-create。

```bash
lark-cli base +contact-field-enrichment-create \
  --base-token "<base_token>" \
  --table-id "<table_id>" \
  --json '<上面的 JSON>' \
  --as user

lark-cli base +contact-field-enrichment-list \
  --base-token "<base_token>" \
  --table-id "<table_id>" \
  --as user
```

<a id="api-入参详情"></a>

## 接口

创建使用：

```
POST /open-apis/base/v3/bases/:base_token/tables/:table_id/contact_field_enrichments
```

查询使用：

```
GET /open-apis/base/v3/bases/:base_token/tables/:table_id/contact_field_enrichments
```

## 返回与技术限制

- 创建返回当前完整关系快照；关系包含来源 `source_field`、补全类型 `info_type` 及生成字段信息，异常信息由 `error_message` 表示。
- 生成列在 enrichment 关系存在期间由系统维护且只读；Record 或 CellValue 写入不能替代派生关系。
- 若返回 `error_message`，表示该关系已停止更新。
- 普通 `+field-update` 使用全量 PUT；仅提交 `type` 和 `name` 不能证明补全关系会被保留。
