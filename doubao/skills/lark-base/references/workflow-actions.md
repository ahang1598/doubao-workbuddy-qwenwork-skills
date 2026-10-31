# 工作流普通动作参数契约

## 目录

- 新增记录（AddRecordAction）、更新记录（SetRecordAction）、查找记录（FindRecordAction）
- 发送消息（LarkMessageAction）、发送邮件（LarkEmailAction）、HTTP 请求（HTTPClientAction）
- 延迟（Delay）、生成文本（GenerateAiTextAction）、分析数据（AIAnalysisAction）

## 新增记录（AddRecordAction）

必填：`table_name`（目标数据表名）；`field_values`（RecordFieldValue[]）。

```json
{"table_name":"订单表","field_values":[
  {"field_name":"客户名称","value":[{"value_type":"text","value":"客户A"}]},
  {"field_name":"金额","value":[{"value_type":"number","value":100}]},
  {"field_name":"创建人","value":[{"value_type":"ref","value":"$.trigger_1.fieldIdxxx"}]}
]}
```

输出：[节点输出](workflow-outputs.md#addrecordaction新增记录)。

## 更新记录（SetRecordAction）

必填：`table_name`（目标数据表名）；`field_values`（RecordFieldValue[]）。

可选：`max_set_record_num`（最大更新数，默认 100，范围 1-15000）；互斥的 `filter_info`（RecordFilterInfo）或 `ref_info`（RefInfo，引用前置步骤记录）。

按目标选一个完整 `data`。替换真实表名、字段和选项。按条件更新：

```json
{"table_name":"订单表","max_set_record_num":10,
 "field_values":[{"field_name":"状态","value":[{"value_type":"option","value":{"name":"已完成"}}]}],
 "filter_info":{"conjunction":"and","conditions":[{"field_name":"状态","operator":"is","value":[{"value_type":"option","value":{"name":"待处理"}}]}]}}
```

引用前置触发记录更新：`ref_info` 步骤必须在同一流程前序链中，且记录属于目标表。

```json
{"table_name":"订单表","max_set_record_num":1,
 "field_values":[{"field_name":"状态","value":[{"value_type":"option","value":{"name":"已完成"}}]}],
 "ref_info":{"step_id":"step_trigger"}}
```

输出：[节点输出](workflow-outputs.md#setrecordaction更新记录)。

## 查找记录（FindRecordAction）

必填：`table_name`（目标数据表名）；`field_names`（检索字段名列表，至少一个）。

可选：`should_proceed_when_no_results`（无结果时是否继续后续步骤，默认 `true`）；互斥的 `filter_info`（RecordFilterInfo）或 `ref_info`（RefInfo）。

`ref_info.step_id` 必须来自目标表的有效前序记录步骤，不会沿关联字段自动跳表。跨表时，用 `filter_info` 按真实关联值或稳定业务键定位目标，并按业务要求检查 `recordNum`；取得目标表记录后，后续更新才能引用该查找步骤。

`max_set_record_num=1` 仅限制数量，不证明查找唯一或对象正确。完整路径见[跨表唯一定位与更新](workflow-examples.md#跨表唯一定位与更新)。

```jsonc
{"table_name":"客户表","field_names":["客户名称","状态"],
 "should_proceed_when_no_results":true,
 "filter_info":{/* RecordFilterInfo */}}
```

输出：[节点输出](workflow-outputs.md#findrecordaction查找记录)。

## 发送消息（LarkMessageAction）

必填：`receiver`（ValueInfo[]）；`send_to_everyone`（是否发给所有人，须与 `receiver` 分别核对，不得只检查指定对象）；`content`（TextRefItem[]）；`btn_list`（ButtonConfig[]，不需要时传 `[]`）。可选：`title`（TextRefItem[]）。

`ButtonConfig`：`text`（string 按钮文字）；`btn_action`（string：`addRecord` / `setRecord` / `openLink`）；`link`（ValueInfo[]，用于 `openLink`）；`table_name`（string，用于 `addRecord`）；`record_values`（RecordFieldValue[]，用于 `addRecord` / `setRecord`）。

### 接收人约束

- 人员、群常量使用 [ValueInfo](workflow-values.md#基础值valueinfo) 的真实身份标识。查人员运行 `lark-cli contact +search-user`；查当前用户运行 `lark-cli contact +get-user`，不传 `--user-id`，读取 `.data.user.open_id`。
- 动态人员接收人引用普通或系统人员字段；各执行路径见[人员字段引用](workflow-outputs.md#人员字段引用)。关联字段不能作为接收人，须取关联记录的人员字段。
- 不得用公式或查找引用字段作接收人：它们可能通过创建校验，但运行时不发送。
- `receiver` 报 path 不存在时，按 `+field-list` 的字段 ID 修正 `ref` 路径。本轮新建的触发表没有该职责的人员字段时，先加 `{"type":"user"}` 字段并填值，不得改成当前用户的 open_id。

以下示例仅用于已唯一解析的具体人员常量。职责人动态通知按上述约束选择 `ref`，结构见[人员引用示例](workflow-outputs.md#人员字段引用)，不得沿用固定 `receiver`。

```json
{"receiver":[{"value_type":"user","value":{"id":"ou_xxxx"}}],"send_to_everyone":false,
 "title":[{"value_type":"text","value":"订单通知"}],
 "content":[{"value_type":"text","value":"客户 "},{"value_type":"ref","value":"$.trigger_1.fldCustomerName"},{"value_type":"text","value":" 创建了订单"}],
 "btn_list":[{"text":"查看详情","btn_action":"openLink","link":[{"value_type":"text","value":"https://example.com"}]}]}
```

输出：[节点输出](workflow-outputs.md#无输出的操作节点)。

## 发送邮件（LarkEmailAction）

发送飞书邮件；与 `LarkMessageAction` 同属普通 Action，可通过 `next` 串联工作流主链，也可作 AI Agent 工具。发件人由服务端按工作流创建者初始化，无切换发件人的 CLI 参数。

data：`to` 为收件人数组，邮箱为 `{"value_type":"text","value":"name@example.com"}`，也支持已解析的 user/group 或合法 ref；`cc` / `bcc` 为抄送/密送，格式同 `to`；`subject` / `content` 为主题/纯文本正文，使用 text/ref 数组。

`attachments` 为附件值数组，使用已确认的附件值或上游附件引用，不得填本地文件路径；`show_source` 为是否展示来源的布尔值。

收件范围、附件类型、邮箱授权和额度由服务端校验。Agent 工具挂载和调用见[普通 Action 工具](workflow-ai-agent.md#普通-action-工具)。

## HTTP 请求（HTTPClientAction）

必填：`url`（ValueInfo[]，支持 `text` / `ref` 拼接）。

可选：`method`（`GET` / `POST` / `PUT` / `PATCH` / `DELETE`，默认 `POST`）；`queries`（KeyValue[] 查询参数）；`headers`（KeyValue[] 请求头）；`body_type`（`none` / `raw` / `form-data` / `form-urlencoded`，默认 `raw`）。

`raw_body`（ValueInfo[]）仅用于 `body_type=raw`；`form_body`（KeyValue[]）仅用于 `body_type=form-data` 或 `body_type=form-urlencoded`；`response_type` 可为 `none` / `text` / `json`，默认 `json`；`response_value` 是 JSON 字符串形式的响应示例，仅 `response_type=json` 时必填。

`KeyValue`：`key` 为 string 参数名/请求头名；`value` 为 ValueInfo[] 参数值/请求头值，支持 `text` / `ref`。

```json
{"method":"POST","url":[{"value_type":"text","value":"https://api.example.com/webhook"}],
 "queries":[{"key":"source","value":[{"value_type":"text","value":"workflow"}]}],
 "headers":[{"key":"Content-Type","value":[{"value_type":"text","value":"application/json"}]}],
 "body_type":"raw","raw_body":[{"value_type":"text","value":"{\"record_id\":\""},{"value_type":"ref","value":"$.step_1.recordId"},{"value_type":"text","value":"\"}"}],
 "response_type":"json","response_value":"{\"success\":true,\"message\":\"data fetched successfully\"}"}
```

输出：[节点输出](workflow-outputs.md#httpclientactionhttp-请求)。

## 延迟（Delay）

必填：`duration`（延迟分钟数，范围 [1, 120]）。

```json
{"duration":30}
```

输出：[节点输出](workflow-outputs.md#无输出的操作节点)。

## 生成文本（GenerateAiTextAction）

必填：`prompt`（TextRefItem[]，支持 `text` / `ref`）。

```json
{"prompt":[{"value_type":"text","value":"请总结以下内容："},{"value_type":"ref","value":"$.step_1.fieldxxx"}]}
```

输出：[节点输出](workflow-outputs.md#generateaitextactionai-生成文本)。

## 分析数据（AIAnalysisAction）

必填：`analysis_task`（TextRefItem[]，支持 `text` / `ref` 混排，至少一项有效内容）；`identity_type`（`maker` 固定流程身份 / `triggerPersonal` 流程触发者）。

可选：`analysis_table_names`（string[]，`[]` 或省略表示当前 Base 全部数据表）；`output_instruction`（仅支持纯文本）。

```json
{"analysis_task":[{"value_type":"text","value":"分析订单趋势"}],
 "analysis_table_names":["订单表","客户表"],"identity_type":"maker",
 "output_instruction":"先给结论"}
```

输出：[节点输出](workflow-outputs.md#aianalysisactionai-分析)。
