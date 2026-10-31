# 工作流完整示例

先读[步骤图结构](workflow-schema.md)，再按索引取对应形态的完整示例；涉及具体节点、条件、赋值或引用时继续读对应协议。只列流程、读状态或改名称／文案时不加载示例。
每次独立创建时生成并保存新的 `client_token`，不提交占位符。把 `fld…` 换成 `+field-list` 返回的字段 ID；`ref` 引用 fieldId，不引用字段名。

## 示例索引

| 形态 | 示例 |
| --- | --- |
| 新增触发、消息 | [新增记录触发 + 发送消息](#新增记录触发--发送消息) |
| 条件分支、修改记录 | [条件分支（IfElseBranch）](#条件分支ifelsebranch) |
| 查找、唯一性判断、跨表更新 | [跨表唯一定位与更新](#跨表唯一定位与更新) |
| 多路分支、延时 | [多路分支（SwitchBranch）](#多路分支switchbranch) |
| 定时、查找、循环内分支、消息、AI 文本 | [组合场景](#组合场景定时查找循环分支消息) |
| 按钮、HTTP、新增记录 | [按钮触发 + 调用外部接口 + 写入同步日志](#按钮触发--调用外部接口--写入同步日志) |
| AI 分类 | [AI 分类（用户反馈自动分流）](#ai-分类用户反馈自动分流) |
| AI Agent 联网整理 | [workflow-ai-agent.md](workflow-ai-agent.md#示例联网整理输入写入结果表) |
| APIHub 创建任务 | [workflow-apihub.md](workflow-apihub.md#完整示例新增记录时创建任务) |

## 新增记录触发 + 发送消息

订单表新增记录时给负责人发消息。只有用户说“通知我”时，才把接收人写成当前用户常量 `{"value_type":"user","value":{"id":"<contact +get-user 的 open_id>"}}`。

```json
{
  "client_token": "<唯一 token>", "title": "新订单通知",
  "steps": [
    {"id":"t","type":"AddRecordTrigger","title":"新增订单","next":"m","data":{"table_name":"订单表","watched_field_name":"订单号","condition_list":null}},
    {"id":"m","type":"LarkMessageAction","title":"发送通知","next":null,"data":{
      "receiver":[{"value_type":"ref","value":"$.t.fldOwner"}],"send_to_everyone":false,
      "title":[{"value_type":"text","value":"新订单提醒"}],
      "content":[{"value_type":"text","value":"金额："},{"value_type":"ref","value":"$.t.fldAmount"}],
      "btn_list":[{"text":"查看订单","btn_action":"openLink","link":[{"value_type":"ref","value":"$.t.recordLink"}]}]
    }}
  ]
}
```

`AddRecordTrigger` 监控 `table_name` 表的 `watched_field_name`；`recordLink` 是触发器内置的记录链接。

## 条件分支（IfElseBranch）

金额至少 `10000` 时通知审批人，否则改状态：

```json
{
  "client_token":"<唯一 token>","title":"金额判断",
  "steps":[
    {"id":"t","type":"AddRecordTrigger","title":"新增订单","next":"b","data":{"table_name":"订单表","watched_field_name":"金额"}},
    {"id":"b","type":"IfElseBranch","title":"判断金额","next":null,
      "children":{"links":[{"kind":"if_true","to":"m","label":"high","desc":"金额>=10000"},{"kind":"if_false","to":"s","label":"normal","desc":"金额<10000"}]},
      "data":{"condition":{"conjunction":"or","conditions":[{"conjunction":"and","conditions":[
        {"left_value":{"value_type":"ref","value":"$.t.fldAmount"},"operator":"isGreaterEqual","right_value":[{"value_type":"number","value":10000}]}
      ]}]}}
    },
    {"id":"m","type":"LarkMessageAction","title":"通知审批人","next":null,"data":{
      "receiver":[{"value_type":"ref","value":"$.t.fldApprover"}],"send_to_everyone":false,"title":[{"value_type":"text","value":"待审批"}],"content":[{"value_type":"ref","value":"$.t.fldAmount"}],"btn_list":[]}},
    {"id":"s","type":"SetRecordAction","title":"自动审核","next":null,"data":{"table_name":"订单表","ref_info":{"step_id":"t"},"field_values":[{"field_name":"状态","value":[{"value_type":"option","value":{"name":"已自动审核"}}]}]}}
  ]
}
```

- `children.links` 必须同时含 `if_true`、`if_false`。省略 `next` 或设为 `null`；两个分支尾部不得指向同一 step ID，每个分支维护独立链路。
- `condition` 是 OrGroup 结构（外层 or、内层 and），支持 `(A and B) or (C and D)`。分支内用 `ref_info` 引用触发记录，用 `filter_info` 批量筛选记录。

## 跨表唯一定位与更新

订单表新增后按客户编号在客户表定位并回写日期；零条或多条时只在源记录留异常。两表客户编号均为文本，两个日期均为日期字段；用真实数据核验业务键唯一性。
先以 `disabled` 保存并核验定义；启停按[目标运行态](../scenes/workflow.md#先确定目标运行态)决定。

```json
{
  "client_token":"<唯一 token>","title":"唯一定位并回写","status":"disabled",
  "steps":[
    {"id":"t","type":"AddRecordTrigger","title":"新增订单","next":"f","data":{"table_name":"订单表","watched_field_name":"订单号"}},
    {"id":"f","type":"FindRecordAction","title":"按编号查客户","next":"b","data":{"table_name":"客户表","field_names":["客户编号","日期"],"should_proceed_when_no_results":true,
      "filter_info":{"conjunction":"and","conditions":[{"field_name":"客户编号","operator":"is","value":[{"value_type":"ref","value":"$.t.fldCustomerNo"}]}]}}},
    {"id":"b","type":"IfElseBranch","title":"只更新唯一结果","next":null,
      "children":{"links":[{"kind":"if_true","to":"u","label":"unique","desc":"恰好一条"},{"kind":"if_false","to":"e","label":"unresolved","desc":"零条或多条"}]},
      "data":{"condition":{"conjunction":"or","conditions":[{"conjunction":"and","conditions":[
        {"left_value":{"value_type":"ref","value":"$.f.recordNum"},"operator":"is","right_value":[{"value_type":"number","value":1}]}
      ]}]}}},
    {"id":"u","type":"SetRecordAction","title":"回写目标日期","next":null,"data":{"table_name":"客户表","max_set_record_num":1,"ref_info":{"step_id":"f"},"field_values":[{"field_name":"日期","value":[{"value_type":"ref","value":"$.t.fldOrderDate"}]}]}},
    {"id":"e","type":"SetRecordAction","title":"记录源异常","next":null,"data":{"table_name":"订单表","max_set_record_num":1,"ref_info":{"step_id":"t"},"field_values":[{"field_name":"定位异常","value":[{"value_type":"text","value":"编号未唯一匹配，目标未更新"}]}]}}
  ]
}
```

- `f.filter_info` 引用源表业务键；`u.ref_info` 必须引用查到的目标记录，不得写成源表触发步骤。`should_proceed_when_no_results: true` 只为让零结果也进入数量判断；两个分支各自结束，异常分支不修改目标表。
- 分别用唯一、无匹配、重复编号核验：唯一时只改对应目标；零／多条时只记源异常；其他记录保持原值。分开报告定义保存与实际执行；真实触发按 Scene 实测授权。
- 此例只实现日期回写。若还要求累计字段或状态联动，按真实累计值和业务状态配置计算／动作，覆盖部分完成和全部完成；不得因日期更新成功就声称其他联动已实现。

## 多路分支（SwitchBranch）

按优先级 `P0`、`P1`、`P2`、其他分流：

```json
{
  "client_token":"<唯一 token>","title":"优先级分流",
  "steps":[
    {"id":"t","type":"AddRecordTrigger","title":"新增订单","next":"b","data":{"table_name":"订单表","watched_field_name":"优先级"}},
    {"id":"b","type":"SwitchBranch","title":"分类","next":null,
      "children":{"links":[{"kind":"case","to":"p0","label":"p0","desc":"P0"},{"kind":"case","to":"p1","label":"p1","desc":"P1"},{"kind":"case","to":"p2","label":"p2","desc":"P2"},{"kind":"case","to":"o","label":"other","desc":"其他"}]},
      "data":{"mode":"exclusive","no_match_action":"classifyToOther","child_branch_list":[
        {"name":"P0","condition":{"conjunction":"or","conditions":[{"conjunction":"and","conditions":[{"left_value":{"value_type":"ref","value":"$.t.fldPriority"},"operator":"is","right_value":[{"value_type":"option","value":{"name":"P0"}}]}]}]}},
        {"name":"P1","condition":{"conjunction":"or","conditions":[{"conjunction":"and","conditions":[{"left_value":{"value_type":"ref","value":"$.t.fldPriority"},"operator":"is","right_value":[{"value_type":"option","value":{"name":"P1"}}]}]}]}},
        {"name":"P2","condition":{"conjunction":"or","conditions":[{"conjunction":"and","conditions":[{"left_value":{"value_type":"ref","value":"$.t.fldPriority"},"operator":"is","right_value":[{"value_type":"option","value":{"name":"P2"}}]}]}]}}
      ]}},
    {"id":"p0","type":"LarkMessageAction","title":"立即处理","next":null,"data":{"receiver":[{"value_type":"ref","value":"$.t.fldOwner"}],"send_to_everyone":false,"title":[{"value_type":"text","value":"P0"}],"content":[{"value_type":"text","value":"立即处理"}],"btn_list":[]}},
    {"id":"p1","type":"SetRecordAction","title":"标记高优先级","next":null,"data":{"table_name":"订单表","ref_info":{"step_id":"t"},"field_values":[{"field_name":"状态","value":[{"value_type":"text","value":"高优先级待处理"}]}]}},
    {"id":"p2","type":"Delay","title":"延迟处理","next":null,"data":{"duration":60}},
    {"id":"o","type":"SetRecordAction","title":"标记其他","next":null,"data":{"table_name":"订单表","ref_info":{"step_id":"t"},"field_values":[{"field_name":"状态","value":[{"value_type":"text","value":"待分类"}]}]}}
  ]
}
```

- `kind: "case"` 的 `label` 按顺序对应 `child_branch_list` 的条件；`mode: "exclusive"` 表示第一个匹配分支执行后停止。
- `no_match_action: "classifyToOther"` 表示无匹配时走最后一个 `case`（兜底）；`"fail"` 表示无匹配时失败。

## 组合场景（定时+查找+循环+分支+消息）

每天 9 点查找昨天记录，在循环体内按金额分级通知负责人；循环后生成日报：

```json
{
  "client_token":"<唯一 token>","title":"每日分级通知",
  "steps":[
    {"id":"t","type":"TimerTrigger","title":"每天 9 点","next":"f","data":{"rule":"DAILY","start_time":"2025-01-01 09:00","is_never_end":true}},
    {"id":"f","type":"FindRecordAction","title":"查找昨天记录","next":"l","data":{"table_name":"订单表","field_names":["金额","负责人"],"should_proceed_when_no_results":false,
      "filter_info":{"conjunction":"and","conditions":[{"field_name":"创建时间","operator":"isGreaterEqual","value":[{"value_type":"date","value":"yesterday"}]}]}}},
    {"id":"l","type":"Loop","title":"遍历记录","next":"a","children":{"links":[{"kind":"loop_start","to":"b"}]},
      "data":{"loop_mode":"continue","max_loop_times":500,"data":[{"value_type":"ref","value":"$.f.fieldRecords"}]}},
    {"id":"b","type":"SwitchBranch","title":"按金额分类","next":null,
      "children":{"links":[{"kind":"case","to":"m1","label":"big","desc":">=100000"},{"kind":"case","to":"m2","label":"normal","desc":"<100000"}]},
      "data":{"mode":"exclusive","no_match_action":"fail","child_branch_list":[
        {"name":"大额","condition":{"conjunction":"or","conditions":[{"conjunction":"and","conditions":[{"left_value":{"value_type":"ref","value":"$.l.item.fldAmount"},"operator":"isGreaterEqual","right_value":[{"value_type":"number","value":100000}]}]}]}},
        {"name":"普通","condition":{"conjunction":"or","conditions":[{"conjunction":"and","conditions":[{"left_value":{"value_type":"ref","value":"$.l.item.fldAmount"},"operator":"isLess","right_value":[{"value_type":"number","value":100000}]}]}]}}
      ]}},
    {"id":"m1","type":"LarkMessageAction","title":"大额通知","next":null,"data":{
      "receiver":[{"value_type":"ref","value":"$.l.item.fldOwner"}],"send_to_everyone":false,"title":[{"value_type":"text","value":"大额"}],"content":[{"value_type":"ref","value":"$.l.item.fldAmount"}],"btn_list":[]}},
    {"id":"m2","type":"LarkMessageAction","title":"普通通知","next":null,"data":{
      "receiver":[{"value_type":"ref","value":"$.l.item.fldOwner"}],"send_to_everyone":false,"title":[{"value_type":"text","value":"普通"}],"content":[{"value_type":"ref","value":"$.l.item.fldAmount"}],"btn_list":[]}},
    {"id":"a","type":"GenerateAiTextAction","title":"生成日报","next":null,"data":{"prompt":[{"value_type":"text","value":"请生成昨日处理日报"}]}}
  ]
}
```

- `Loop.data` 中的 `data` 必须传 `ref` 数据源，通常为 `FindRecordAction.fieldRecords`；`children.links` 必须含 `kind: "loop_start"` 并指向循环体；`Loop.next` 指向循环结束后的节点。
- 循环体用 `$.{loopStepId}.item.{fieldId}` 引当前记录字段；用 `$.{loopStepId}.index` 取从 `0` 开始的索引。

## 按钮触发 + 调用外部接口 + 写入同步日志

点击客户表记录按钮后调用外部接口，再向日志表新增记录：

```json
{
  "client_token":"<唯一 token>","title":"按钮同步",
  "steps":[
    {"id":"t","type":"ButtonTrigger","title":"点击按钮","next":"h","data":{"button_type":"buttonField","table_name":"客户表"}},
    {"id":"h","type":"HTTPClientAction","title":"调用接口","next":"r","data":{
      "method":"POST","url":[{"value_type":"text","value":"https://api.example.com/v1/sync"}],
      "headers":[{"key":"Content-Type","value":[{"value_type":"text","value":"application/json"}]}],"body_type":"raw",
      "raw_body":[{"value_type":"text","value":"{\"name\":\""},{"value_type":"ref","value":"$.t.fldCustomer"},{"value_type":"text","value":"\",\"source_record_id\":\""},{"value_type":"ref","value":"$.t.recordId"},{"value_type":"text","value":"\"}"}],
      "response_type":"json","response_value":"{\"success\":true,\"message\":\"synced\"}"
    }},
    {"id":"r","type":"AddRecordAction","title":"写日志","next":null,"data":{"table_name":"同步日志表","field_values":[
      {"field_name":"客户名称","value":[{"value_type":"ref","value":"$.t.fldCustomer"}]},
      {"field_name":"来源记录ID","value":[{"value_type":"ref","value":"$.t.recordId"}]},
      {"field_name":"是否成功","value":[{"value_type":"ref","value":"$.h.body.success"}]},
      {"field_name":"结果说明","value":[{"value_type":"ref","value":"$.h.body.message"}]}
    ]}}
  ]
}
```

- `ButtonTrigger` 用于人工确认后再执行的场景，如同步外部系统、发起审批。`button_type: "buttonField"` 表示按钮挂在记录上，可直接引用当前记录字段和 `recordId`。`raw_body` 用 `text + ref + text` 拼接 JSON。
- `HTTPClientAction` 输出：`response_type=none` 时不可引用；`response_type=text` 时只用 `$.stepId` 引全文；`response_type=json` 时用 `$.stepId.body` 引 body、`$.stepId.body.字段名` 引字段；`$.stepId.status_code` 是 HTTP 状态码。
- 后续只能引用 `response_value` 声明的字段。

## AI 分类（用户反馈自动分流）

反馈表新增记录时 AI 分类为投诉或咨询，无法判断时进默认分支：

```json
{
  "client_token":"<唯一 token>","title":"反馈分类",
  "steps":[
    {"id":"t","type":"AddRecordTrigger","title":"新增反馈","next":"b","data":{"table_name":"反馈表","watched_field_name":"反馈内容"}},
    {"id":"b","type":"AIClassificationBranch","title":"AI 分类","next":null,
      "children":{"links":[{"kind":"case","to":"s1","label":"branch_1","desc":"投诉"},{"kind":"case","to":"s2","label":"branch_2","desc":"咨询"},{"kind":"case","to":"s3","label":"default","desc":"默认分支"}]},
      "data":{"classes":[{"name":"投诉","desc":"对订单或服务表达不满"},{"name":"咨询","desc":"询问订单进度或价格"}],
      "content":[{"value_type":"ref","value":"$.t.fldContent"}],
      "classification_rule":"有明确不满表述时归入投诉；信息不足时进入默认分支。"}},
    {"id":"s1","type":"SetRecordAction","title":"标记投诉","next":null,"data":{"table_name":"反馈表","ref_info":{"step_id":"t"},"field_values":[{"field_name":"分类","value":[{"value_type":"text","value":"投诉"}]}]}},
    {"id":"s2","type":"SetRecordAction","title":"标记咨询","next":null,"data":{"table_name":"反馈表","ref_info":{"step_id":"t"},"field_values":[{"field_name":"分类","value":[{"value_type":"text","value":"咨询"}]}]}},
    {"id":"s3","type":"SetRecordAction","title":"标记待复核","next":null,"data":{"table_name":"反馈表","ref_info":{"step_id":"t"},"field_values":[{"field_name":"分类","value":[{"value_type":"text","value":"待人工复核"}]}]}}
  ]
}
```

`classes` 按顺序对应 `label` 为 `branch_1`、`branch_2` 的 case；`desc` 与分类名一致，`to` 指向已定义的下游 step；`label: "default"` 是默认分支。
