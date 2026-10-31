# 工作流触发器参数契约

## 目录

记录触发器对比 · 记录触发条件 · 新增记录 · 记录满足条件 · 字段修改 · 定时触发 · 日期提醒 · 按钮触发 · 接收消息

## 记录触发器对比

| 触发器 | 事件 | 监听 | 修改前条件 | 当前/修改后条件 |
|---|---|---|---|---|
| AddRecordTrigger | 仅新增 | watched_field_name 必填；新增值须非空 | 不支持 | condition_list 可选，筛新增值 |
| SetRecordTrigger | 仅修改 | field_watch_info 必填；任一项匹配即触发 | record_watch_info 可选 | condition_list 可选，筛修改后值 |
| ChangeRecordTrigger | 新增；或条件字段被修改 | 自动监听 condition_list 字段，不监听其他字段 | 不支持 | condition_list 必填，筛新增值或修改后值 |
| Add + Set（两条 Workflow） | 新增；或任意可监听字段修改 | Add 监听指定字段；Set 监听当前环境支持的全部字段 | Set 可选 | 两者均可选；有条件时相同 |

## 记录触发条件

condition_list 为 AndCondition[]：条件组间 OR，组内 conditions 间 AND。只能比较字段与静态值，不能比较两个字段；字段间比较须先用公式字段表达结果，再以结果为条件，公式重算也会触发。
按[值类型与条件](workflow-values.md#条件与记录定位)构造。

trigger_control_list：Add 取 pasteUpdate / automationBatchUpdate / syncUpdate / appendImport / openAPIBatchUpdate；Change、Set 取前四项。

Add、Change、Set、Reminder 的输出见[节点输出](workflow-outputs.md#记录触发器addrecordtrigger--changerecordtrigger--setrecordtrigger--remindertrigger)。

## 新增记录（AddRecordTrigger）

下表及后文参数表中，`*` 表示必填，其余可选。

| 字段 | 约束 |
|---|---|
| table_name* | 监控的数据表名 |
| watched_field_name* | 监控字段名 |
| trigger_control_list | 取值见“记录触发条件” |
| condition_list | 见“记录触发条件” |

data（独立 JSON 值；无条件时写 null 或省略）：

```jsonc
{
  "table_name": "订单表",
  "watched_field_name": "状态",
  "trigger_control_list": ["pasteUpdate", "automationBatchUpdate"],
  "condition_list": null /* AndCondition[] | null */
}
```

## 记录满足条件（ChangeRecordTrigger）

| 字段 | 约束 |
|---|---|
| table_name* | 监控的数据表名 |
| trigger_control_list | 取值见“记录触发条件” |
| condition_list* | 不得为空；见“记录触发条件” |

```json
{
  "table_name": "订单表",
  "trigger_control_list": [],
  "condition_list": [{
    "conjunction": "and",
    "conditions": [{
      "field_name": "金额", "operator": "isGreater",
      "value": [{"value_type": "number", "value": 0}]
    }]
  }]
}
```

## 字段修改（SetRecordTrigger）

| 字段 | 约束 |
|---|---|
| table_name* | 监控的数据表名 |
| record_watch_info | 匹配修改前值的记录级过滤对象；不筛选则省略 |
| record_watch_info.conjunction | and / or；默认 and |
| record_watch_info.conditions | 使用记录过滤时必填 FieldCondition[]；不得把数组直接赋给 record_watch_info |
| field_watch_info* | 至少一个监听字段；仅监听变化时每项只填 field_name |
| trigger_control_list | 取值见“记录触发条件” |
| condition_list | 筛修改后值；见“记录触发条件” |

FieldWatchItem：

| 字段（类型） | 约束 |
|---|---|
| field_name（string） | 监听字段名 |
| operator（string） | 仅明确要求字段满足条件时填 |
| value（ValueInfo[]） | 触发值 |

data（独立 JSON 值）：

```jsonc
{
  "table_name": "订单表",
  "record_watch_info": {
    "conjunction": "and", "conditions": [ /* FieldCondition[] */ ]
  },
  "field_watch_info": [{
    "field_name": "状态", "operator": "is",
    "value": [{"value_type": "option", "value": {"name": "已完成"}}]
  }],
  "trigger_control_list": [],
  "condition_list": null
}
```

## 定时触发（TimerTrigger）

| 字段 | 约束 |
|---|---|
| rule* | NO_REPEAT / DAILY / WEEKLY / MONTHLY / YEARLY / WORKDAY / CUSTOM |
| start_time | 写入格式 yyyy-MM-dd HH:mm；WEEKLY / MONTHLY 必须显式填写 |
| interval | 仅 CUSTOM；[1,30] |
| unit | 仅 CUSTOM；当前页面可选 DAY / WEEK / MONTH / YEAR |
| sub_unit | WEEKLY：星期数组 0-6；MONTHLY：日期数组 1-31；受回读限制 |
| end_time | 结束时间 |
| is_never_end | 是否永不结束 |

### 回读与排期核对

- `+workflow-get` 把 start_time 渲染为 yyyy/MM/dd HH:mm；分隔符与写入格式不同属预期。
- WEEKLY / MONTHLY 触发日以 start_time 日期为准。换算真实星期或日期后核对，不得只看规则名或 sub_unit；不匹配时修正日期再提交。
- 两类规则的 get 只回读 rule、start_time，不返回 sub_unit、is_never_end。缺失属预期，不得据此重复提交，也不能据此证明多个触发日均生效。

```json
{"rule":"WEEKLY","start_time":"2025-01-06 09:00","sub_unit":[1,3,5],"is_never_end":true}
```

输出：[节点输出](workflow-outputs.md#timertrigger定时触发器)。

## 日期提醒（ReminderTrigger）

| 字段 | 约束 |
|---|---|
| table_name* | 数据表名 |
| field_name* | 日期字段名；类型必须为 datetime / created_at / formula / lookup |
| unit* | MINUTE / HOUR / DAY / WEEK / MONTH |
| offset* | 触发时间 = 日期字段时间 + offset × unit；负数提前，正数延后；范围见下表 |
| hour* | 0-23；默认 9 |
| minute* | 0-59；默认 0 |
| condition_list | 见“记录触发条件” |

| unit | offset 允许范围 |
|---|---|
| MINUTE | {0, 5, 15, 30, -5, -15, -30} |
| HOUR | [-6, -1] ∪ [1, 6] |
| DAY | [-7, 7] |
| WEEK / MONTH | [-7, -1] ∪ [1, 7] |

```json
{
  "table_name":"项目表", "field_name":"截止日期", "offset":-1,
  "unit":"DAY", "hour":9, "minute":0, "condition_list":null
}
```

上例在截止日期前 1 天 9:00 触发。“到期当天提醒”填 `"offset":0`；“超期/逾期未完成”填 `"offset":1`（截止日次日）并加“状态不是已完成”条件；日期之后 N 天填正数 N。

## 按钮触发（ButtonTrigger）

| 字段 | 约束 |
|---|---|
| button_type* | buttonField（表格按钮，可操作当前记录数据）/ buttonElement（仪表盘、应用页面按钮，可执行整体操作） |
| table_name | 仅 button_type=buttonField 时填绑定表名 |
| condition_list | 仅 buttonField 可用；只有用户明确要求筛当前记录时才填，规则见“记录触发条件”；否则省略 |

```json
{"button_type":"buttonField","table_name":"订单表"}
```

buttonField 与 buttonElement 输出能力不同，见 [ButtonTrigger 输出说明](workflow-outputs.md#buttontrigger按钮触发器)。

## 接收消息（LarkMessageTrigger）

| 字段 | 约束 |
|---|---|
| receive_scene* | group（群聊）/ chat（单聊） |
| receiver* | 来源：user / group / ref；单聊指可与机器人单聊的用户，群聊指接收信息的群组 |
| scope* | at（@提及）/ all（所有消息）；仅群聊有效，单聊不得指定 |
| filter* | MessageFilter |

MessageFilter：

| 字段（类型） | 约束 |
|---|---|
| conjunction（string） | and 满足全部 / or 满足任一 |
| content_contains（string[]） | 关键词列表 |
| sender_contains（ValueInfo[]） | 筛发送人；仅群聊且群组来源时生效，单聊不得指定 |
| is_new_message（boolean） | 仅新话题消息；仅群聊有效，单聊不得指定 |
| is_message_contain_attachment（boolean） | 是否仅附件消息触发 |

```json
{
  "receive_scene":"group",
  "receiver":[{"value_type":"group","value":{"id":"oc_xxxx","name":"群聊"}}],
  "scope":"all",
  "filter":{
    "conjunction":"and", "content_contains":["关键词"],
    "sender_contains":[{"value_type":"user","value":{"id":"ou_xxxx","name":""}}],
    "is_new_message":true, "is_message_contain_attachment":false
  }
}
```

输出：[节点输出](workflow-outputs.md#larkmessagetrigger飞书消息触发器)。
