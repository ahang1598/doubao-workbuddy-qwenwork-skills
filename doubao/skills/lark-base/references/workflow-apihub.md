# 工作流 APIHub 集成节点契约

## 使用范围与依赖

`APIHubAction` 仅限下列 9 项；不得使用表外 `component_id`、参数、输出，或套用 OpenAPI、MCP 工具、节点捷径。

## 节点公共结构

- 节点用 `type: "APIHubAction"`；`meta.component_id` 取下表标识，参数放 `data.params`。
- `params[].key` 大小写敏感：保留 `endTime`、`userList`，禁改为 `end_time`、`user_list`；每个参数只出现一次。
- `params[].value` 始终为数组，元素为 `{ "value_type": "...", "value": ... }`。
- `meta` 与 `data` 同级。更新前 get 完整工作流，保留节点 `meta` 和连线。
- 作为主链动作时用 `next` 串联；作为 Agent 工具时通过 `slot/tool` 挂载，见 [AI Agent](workflow-ai-agent.md)。
- 可选参数可整项省略；回读的空数组/默认值不表示不支持该字段。
- `CustomAction` 节点捷径协议不同，禁复用其组件标识、表单参数。

## 当前支持的组件

| 能力 | component_id | 必填参数 | 可选参数 |
|---|---|---|---|
| 创建任务 | Automation_Create_Task | rich_summary | collaborator_ids、endTime、rich_description、follower_ids |
| 完成任务 | Automation_Complete_Task | task_id | — |
| 取消完成任务（重启） | Automation_Uncomplete_Task | task_id | — |
| 删除任务 | Automation_Delete_Task | task_id | — |
| 创建日程 | Automation_Create_Schedule | startTime、endTime、calendarId | summary、attendees、description、location、needNotification |
| 删除日程 | Automation_Delete_Schedule | calendarId、eventId | needNotification |
| 创建群组 | Automation_Create_Group | name、userList、owner | description、topBase |
| 添加群成员 | Automation_Add_Group_Member | group、userList | — |
| 移除群成员 | Automation_Delete_Group_Member | group、userList | — |

## 参数值类型

`ref` 引用前置步骤输出，如 `{ "value_type": "ref", "value": "$.create_task.taskId" }`。

| 参数 | value_type | 值与约束 |
|---|---|---|
| rich_summary、rich_description、summary、name、description、location | text/ref | text：字符串；任务标题、群名称必填 |
| startTime、endTime | date/ref | date：日期时间串，如 `2026-09-30 18:00`；结束须晚于开始；禁用未定义相对时间对象 |
| collaborator_ids、follower_ids、userList、owner | user/ref | user：`{ "id": "ou_...", "name": "..." }`；owner 单选 |
| attendees | user/group/ref | 可含人员或群组 |
| group | group/ref | `{ "id": "oc_...", "name": "..." }`，单选；动态 ref 引建群输出 group/group_chat，禁引文本字段、groupShareLink |
| needNotification、topBase | boolean/ref | JSON true/false，禁字符串 |
| task_id、删除日程的 calendarId/eventId | text/ref | 真实 ID/前置输出；禁名称、URL、臆造 ID |
| 创建日程的 calendarId | 仅 option | `{ "id": "真实日历ID", "name": "日历名称" }`；禁 text、纯 ref |

- “取消完成”把原任务恢复为未完成，不新建任务。
- 删除日程、删除任务、移除群成员都作用于真实对象，必须明确目标。移除成员不等于解散群。
- `topBase` 表示把当前多维表格加到群顶部标签页。
- 创建任务：`collaborator_ids` 是负责人，`follower_ids` 是关注人，角色不同，可同时填。`endTime`（截止时间）、`rich_description`（描述）用户未要求时可省略。标题、描述可混排常量与前置字段引用。可选参数与 `rich_summary` 同放 `data.params`，人员替换为真实查询结果：

```json
[{"key":"collaborator_ids","value":[{"value_type":"user","value":{"id":"<负责人open_id>","name":"<姓名>"}}]},
{"key":"endTime","value":[{"value_type":"date","value":"2026-09-30 18:30"}]}]
```

## 资源查询与标识

查询前以相应命令 `--help` 或 `schema` 确认参数；ID 取查询结果/工作流输出。

| 资源 | 查询入口 | 节点保存内容 |
|---|---|---|
| 人员 | `lark-cli contact +search-user`；当前用户：`contact +get-user` | open_id、名称；禁内部数字 ID |
| 已有群组/成员 | `lark-cli im +chat-search`、`im +chat-members-list` | chat_id、名称 |
| 日历 | `lark-cli calendar calendars primary` / `calendar calendars list` / `calendar calendars search` | 日历 ID、名称 |
| 已有日程 | `lark-cli calendar +search-event` / `calendar +agenda` / `calendar +get` | 日历 ID、日程 ID |
| 已有任务 | `lark-cli task +search` / `task +get-my-tasks` | 任务 ID |

## 输出引用

仅引用当前节点前、执行路径可用的输出；路径大小写不变。

| 创建节点 | 可引用输出 | 后续用途 |
|---|---|---|
| 创建任务 | `$.<stepId>.taskId`、`$.<stepId>.applink`、`creator`、`createTime` | `task_id` 引 `taskId`；消息/记录的详情链接引 `applink` |
| 创建日程 | `$.<stepId>.calendarId`、`scheduleId`、`meetingUrl`、`creator` | 删除时 `eventId` 引 `scheduleId`，`calendarId` 引同名输出 |
| 创建群组 | `$.<stepId>.group`、`groupShareLink` | 添加/移除成员的 `group` 引群对象 |

- `applink` 是创建任务返回的任务 AppLink，禁用 `taskId` 拼接。
- 其余 6 项无可引用业务输出。禁自拼 `.data`/`.output`/`.result` 层或推测 creator/group 下钻字段；以服务端返回、校验为准。
- `group` 须引群对象。若 `pathType "1"` 不匹配允许类型 `[23, baseGroup, groupList]`：先以 `+field-list` 核对字段类型，再按[群字段](field-config.md#36-user--group_chat)改引群对象；写回按 [RecordFieldValue](workflow-values.md#recordfieldvalue) 构造。类型不匹配≠平台不支持，禁以通知替代群成员变更。

## 记录结果读取

查看工作流写入的记录时，`+record-list` 用 `--format json`；按 `data.fields` 列顺序读 `data.data` 行数组，禁按 `row.fields` 解析。以 `offset` 分页；全量核对须读到 `has_more=false`。

## 示例

### 完整示例：新增记录时创建任务

先查询并替换真实表名、监控字段名；每次创建生成新 `client_token`。示例不设负责人，避免加入未指定的人。

```json
{"client_token":"<唯一值>","title":"新增记录时创建任务","steps":[
{"id":"new_record","type":"AddRecordTrigger","title":"新增记录","data":{"table_name":"订单表","watched_field_name":"状态"},"next":"create_task"},
{"id":"create_task","type":"APIHubAction","title":"创建任务","meta":{"component_id":"Automation_Create_Task"},"data":{"params":[{"key":"rich_summary","value":[{"value_type":"text","value":"处理记录"}]}]}}]}
```
