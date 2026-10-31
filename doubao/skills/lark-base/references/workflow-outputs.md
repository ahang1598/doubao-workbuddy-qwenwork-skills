# 工作流输出与引用契约

## 目录

使用范围与依赖｜引用路径格式｜字段引用与路径校验｜节点输出能力总览｜触发器节点输出

操作节点输出｜分支节点输出｜循环节点输出｜人员字段引用｜字段属性下钻

## 使用范围与依赖

`value_type=ref` 的 `value` 指向前置输出。含条件、赋值或 `ref` 时，完整读取[值类型与条件](workflow-values.md)及本页路径、校验、所用节点输出。
人员接收人另读本页人员章节和[接收人约束](workflow-actions.md#接收人约束)；查找后循环取关联人员不得只读通用路径或触发器输出。输入按对应协议构造。

## 引用路径格式

```text
$.{stepId}
$.{stepId}.{pathId}
$.{stepId}.{pathId}.{childPathId}
$.{stepId}.{pathId}.{childPathId}.{grandChildPathId}
```

`{stepId}` 为前置 `WorkflowStep.id`，`{pathId}` 为输出路径 ID；可多层下钻，如 `$.step_1.fldXXX.name`。下文 `pathId=X` 即 `$.{stepId}.X`。

## 字段引用与路径校验

字段路径用真实 field ID，不用展示名。以各表 `+field-list` / `+field-get` 取 ID、类型；`+workflow-get` 的字段 `ref` 仅有 ID，按各表清单映射名称。条件、消息等 `ref` 均用服务端可用路径。

遇 `path does not exist` 或 pathType 不兼容，检查前置 step ID、字段 ID、输出类型，按错误列出的路径修正；不得改用展示名、当前用户或静态文本规避。

## 节点输出能力总览

下文逐节点列出输出契约。`Delay`、`LarkMessageAction`、`IfElseBranch`、`SwitchBranch` 无输出；`TimerTrigger`、`GenerateAiTextAction`、`AIAnalysisAction`、`AIClassificationBranch` 输出是静态的。涉及 AI Agent 或 APIHub 时，按[AI Agent 输出与引用](workflow-ai-agent.md#输出与引用)、[APIHub 输出引用](workflow-apihub.md#输出引用)执行。

## 触发器节点输出

### 记录触发器（AddRecordTrigger / ChangeRecordTrigger / SetRecordTrigger / ReminderTrigger）

| pathId | 含义 |
|---|---|
| `{fieldId}` | 配置表全部字段或指定字段 ID 的字段值；可下钻属性 |
| `{fieldId}.fieldId` / `{fieldId}.fieldName` | 字段 ID / 字段名 |
| `startTime` | 触发时间戳 |
| `recordId` / `recordLink` | 记录 ID / 记录链接 |
| `recordCreatedUser` / `recordCreatedTime` | 创建者 / 创建时间 |
| `recordModifiedUser` / `recordModifiedTime` | 修改者 / 修改时间 |

读取配置表全部字段，每字段生成 `pathId=fieldId`。关联字段 children 为关联表全部字段，仅一层、不递归；字段属性见末节。
配置表后，`recordLink` children 为全部视图，每项 `{ pathId: viewId, pathName: viewName, pathType: 'string' }`；引用 `$.{stepId}.recordLink.{viewId}`。

### ButtonTrigger（按钮触发器）

| `button_type` | pathId：含义 |
|---|---|
| `buttonField` | `{fieldId}`（配置表全部/指定字段值，可下钻）；`.fieldId` / `.fieldName`（ID / 名称） |
| `buttonField` | `recordId` / `recordLink`（记录 ID / 链接）；`recordCreatedUser`（创建者） |
| `buttonField` | `recordModifiedUser` / `recordModifiedTime`（修改者 / 修改时间） |
| 两者 | `time` / `user` / `buttonName`（触发时间 / 人 / 按钮名） |

`buttonElement` 只有 `time`、`user`、`buttonName`。

### TimerTrigger（定时触发器）

`scheduleTime`：定时触发时间。

### LarkMessageTrigger（飞书消息触发器）

| pathId | 含义 |
|---|---|
| `Sender` / `AtUser`；`SenderGroup` | 发送者 / 被 @ 用户；所在群（仅群聊） |
| `MessageSendTime` / `MessageContent` | 发送时间 / 正文 |
| `MessageType` / `MessageID`；`MessageLink` | 类型 / 唯一 ID；链接（仅群聊） |
| `ParentID` / `ThreadID`；`Attachments` | 回复 ID / 话题 ID；附件 |

`receive_scene="Chat"`（单聊）时，`SenderGroup`、`MessageLink` 不可用。

## 操作节点输出

### FindRecordAction（查找记录）

| pathId | 说明 |
|---|---|
| `fieldRecords` | 全部找到的记录；可供 Loop 遍历 |
| `firstfieldsRecord` | 第一条匹配记录 |
| `firstfieldsRecord.{fieldId}` | 首条记录字段值；可下钻属性 |
| `firstfieldsRecord.recordId` | 记录 ID 数组 |
| `fields` | 所有记录某列值；不支持直接引用 |
| `fields.{fieldId}` | 用户选择的字段 |
| `fields.{fieldId}.fieldId` / `fields.{fieldId}.fieldName` | 所选字段的 ID 数组 / 名称数组 |
| `fields.recordId` | 记录 ID 数组 |
| `recordNum` | 找到的记录总数 |

### AddRecordAction（新增记录）

`{fieldId}` 是用户配置字段值，可下钻；`.fieldId` / `.fieldName` 是字段 ID / 名称；`recordId` / `recordLink` 是新增记录 ID / URL。

### SetRecordAction（更新记录）

`{fieldId}` 是用户配置字段值，可下钻；`.fieldId` / `.fieldName` 是字段 ID / 名称；`recordId` 是记录 ID 数组（可能更新多条）。

### HTTPClientAction（HTTP 请求）

| `response_type` | 引用与限制 |
|---|---|
| `none` | 无可引用输出 |
| `text` | `$.{stepId}` 引用整个响应文本 |
| `json` | `$.{stepId}.body` 引用整个 JSON body；`$.{stepId}.body.<字段名>` 仅引用 `response_value` 声明字段；`$.{stepId}.status_code` 引用 HTTP 状态码；`response_value` 必填 |

```json
{"id":"step_http_1","type":"HTTPClientAction","data":{"response_type":"json","response_value":"{\"success\":true,\"message\":\"ok\"}"}}
```

其后只能引用 `$.step_http_1.body`、`$.step_http_1.body.success`、`$.step_http_1.body.message`、`$.step_http_1.status_code`；不能引用未声明的 `$.step_http_1.body.data`、`$.step_http_1.body.request_id`。

### GenerateAiTextAction（AI 生成文本）

仅整体引用 `$.{stepId}`，不支持下钻。

### AIAnalysisAction（AI 分析）

结果为 string；仅整体引用 `$.{stepId}`，不支持下钻。

### AIAgentAction

文本模式：`$.{stepId}`；JSON/form：`$.{stepId}.字段名`。JSON 对象数组字段可接 Loop，如 `$.{stepId}.items`；顶层数组不能以根引用接 Loop。配置见 [AI Agent](workflow-ai-agent.md)。不得引用内部 LLM/记忆步骤或假定工具必调用。

### 无输出的操作节点

`Delay`（延时等待）、`LarkMessageAction`（发送飞书消息）不产生可引用输出。

## 分支节点输出

`AIClassificationBranch` 输出 `category`（匹配分类名称，string），引用 `$.{stepId}.category`；分类子节点和 `next` 公共后续节点均可引用。`IfElseBranch`、`SwitchBranch` 无输出。

## 循环节点输出

### Loop（循环）

输出 `item`（当前元素）、`index`（从 0 开始）。`item` 类型由数据源推断：

- 数据源为 `record`（如 FindRecordAction 的 `fieldRecords`）时，`item` 是 `record`：当前记录用 `$.{loopStepId}.item`，字段用 `$.{loopStepId}.item.{fieldId}`，number 索引用 `$.{loopStepId}.index`。
- 数据源为附件、人员等多值字段时，`item` 继承源字段类型并可下钻：当前元素用 `$.{loopStepId}.item`，人员姓名用 `$.{loopStepId}.item.name`，索引用 `$.{loopStepId}.index`。

## 人员字段引用

按人员字段所在表和执行路径引用；消息接收人还须满足[接收人约束](workflow-actions.md#接收人约束)。

| 位置与路径 | 引用/动作 |
|---|---|
| 本表人员，记录触发 | `$.<trigger_step>.<person_field_id>` |
| 本表人员，`FindRecordAction + Loop` | `$.<loop_step>.item.<person_field_id>` |
| 关联记录人员，记录触发 | 直接 ref `$.<trigger_step>.<关联字段id>.<目标表人员字段id>` |
| 关联记录人员，`FindRecordAction + Loop` | 不支持沿关联字段直接下钻；按下文查目标表 |

循环体先 `FindRecordAction` 查目标表。仅单关联且主字段唯一时，以主字段 `is` ref `$.<loop_step>.item.<关联字段id>`；`recordNum == 1` 后取 `$.<查找步骤>.firstfieldsRecord.<人员字段id>`；多关联按下文。

要求唯一目标时，零匹配进缺失分支，多匹配进歧义分支，均不得发给任意首条。姓名不是唯一身份；优先用协议支持的稳定业务键，仅主字段唯一且单关联时用下例。
合法多人关联须遍历真实记录集合，按真实人员 ID 核对范围和重复投递；不能表达集合或去重语义时保留缺口，不得假定未文档化的去重参数。记录存在但人员字段为空仍未就绪。

零匹配无需后续处理时设 `should_proceed_when_no_results=false`；需要记录零匹配结果时设 `true`，再显式按数量分支。完整结构见[跨表唯一定位与更新](workflow-examples.md#跨表唯一定位与更新)；查找成功不等于唯一匹配。

记录触发直接取关联人员时，将下列属性放入消息动作 `data`，不得单独提交；两个 ID 来自两表的 `+field-list`：

```jsonc
"receiver":[{"value_type":"ref","value":"$.step_trigger.fld客户.fld负责人"}]
```

最小独立查找步骤（之后须判断数量，不得直接发送）：

```jsonc
{
  "id":"f","type":"FindRecordAction","title":"按关联查客户","next":"c",
  "data":{"table_name":"客户表","field_names":["客户名称","负责人"],"should_proceed_when_no_results":false,
    "filter_info":{"conjunction":"and","conditions":[
      {"field_name":"客户名称","operator":"is","value":[{"value_type":"ref","value":"$.loop.item.fld客户"}]}
    ]}}
}
```

`c` 用 IfElseBranch 判断 `$.f.recordNum is number 1`；`if_true` 才进消息节点，`receiver` 为 `[{"value_type":"ref","value":"$.f.firstfieldsRecord.fld负责人"}]`；`if_false` 进歧义处理、不发送。

完整图须有数量判断、两个独立分支、消息节点。检查已有或已授权样例的同名不同 ID、空关联、多关联、空人员字段；分别验收保存的动态路径和实测接收结果。

## 字段属性下钻

所有字段支持 `fieldId:string`（唯一 ID）、`fieldName:string`（显示名）；部分字段另支持：

| 字段类型 | 额外属性 `pathId:pathType`；说明 |
|---|---|
| 人员 `user` / `created_by` / `updated_by` | `name:string` 姓名 |
| 日期 `datetime` / `created_at` / `updated_at` | `timestamp:number` 时间戳 |
| 附件 `attachment` | `fileName:string` 文件名；`fileType:string` MIME；`size:number` 字节数；`fileToken:string` token |
| 超链接文本 `text` 且 `style.type=url` | `text:string` 链接文本；`link:string` URL |
| 自动编号 `auto_number` | `sequence:number` 纯数字序号 |
| 关联 `link` | `{fieldId}` 下钻关联表字段；`pathType` 为 `-` |

`text`、`number`、`checkbox`、`select`、`location`、`formula`、`lookup` 等其他类型仅支持 `fieldId`、`fieldName`。

| 引用 | 结果 |
|---|---|
| `$.{stepId}.{fieldId}` | 字段值 |
| `...fieldId` / `...fieldName` | 字段 ID / 名称，string |
| `...name` / `...unionId` | 人员姓名 / unionId 列表，array\<string>；仅人员字段 |
| `...timestamp` | 时间戳，array\<number>；仅日期字段 |
| `...fileName` / `...fileToken` | 文件名 / Token 列表，array\<string>；仅附件字段 |
