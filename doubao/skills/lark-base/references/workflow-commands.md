# 工作流生命周期命令

## 使用说明

步骤请求体按[步骤图结构](workflow-schema.md)构造。`+workflow-list` 读 `data.items`；`+workflow-get` 的 `data` 直接含 `workflow_id`、`title`、`status`、`steps`，没有 `workflow` 外层。`+workflow-create` 成功后默认 `disabled`。

## 更新与启停

`+workflow-update` 是完整替换：以 `+workflow-get` 结果为基线，保留 `title`、`status`、`steps`，复制 `steps` 的全部嵌套内容，只改本次目标路径；不得只按常用字段重拼。
保留步骤 ID、`next`、分支连线、消息和动作内部配置、按钮文本和跳转目标；不回传响应外层元数据。节点附加要求见 [AI Agent](workflow-ai-agent.md)、[APIHub](workflow-apihub.md)。

请求体里的 `status` 不切换运行态；启停只用 `+workflow-enable`／`+workflow-disable`，随后用 get 验收。写后按步骤 ID 比较：目标值符合要求、其余配置不变；平台返回顺序和只读元数据变化不算业务变更。
额外差异无法解释时按[配置不符与停用恢复](../scenes/workflow.md#配置不符与停用恢复)处理，不启用。运行态单独验收；临时停用后的 `status` 无须等于最初启用态。

## 写入预检

`+workflow-create`／`+workflow-update` 提交前加 `--dry-run` 预览并做本地校验；dry-run 不调用服务端，不能证明资源存在、接收人有效、定义已保存或执行成功。

## 创建并启用示例

用于目标为 `enabled` 的新建任务：

```bash
lark-cli base +workflow-create --as user --base-token "<base_token>" --json @workflow.json
lark-cli base +workflow-get --as user --base-token "<base_token>" --workflow-id "<wkf_id>"
lark-cli base +workflow-enable --as user --base-token "<base_token>" --workflow-id "<wkf_id>"
lark-cli base +workflow-list --as user --base-token "<base_token>" --status enabled
lark-cli base +workflow-get --as user --base-token "<base_token>" --workflow-id "<wkf_id>"
```

get 预检时流程仍为 disabled、无触发副作用；预检和用户前提都满足才 enable；最后用 list 确认 enabled，用 get 核对定义。

## 最小请求体

来自成功调用，只换表名、字段和文案：

```bash
lark-cli base +workflow-create --base-token "<base_token>" --as user --json '{
"client_token":"<本次创建唯一，如 wkf-20261021-001>","title":"库存不足提醒","steps":[
{"id":"trigger_1","type":"ChangeRecordTrigger","title":"库存状态变为不足","next":"action_1","data":{"table_name":"商品表","condition_list":[{"conjunction":"and","conditions":[{"field_name":"库存状态","operator":"is","value":[{"value_type":"option","value":{"name":"不足"}}]}]}]}},
{"id":"action_1","type":"LarkMessageAction","title":"通知负责人","next":null,"data":{"receiver":[{"value_type":"ref","value":"$.trigger_1.<负责人字段 fld_id>"}],"send_to_everyone":false,"title":[{"value_type":"text","value":"库存不足"}],"content":[{"value_type":"text","value":"请及时补货"}],"btn_list":[]}}]}'
```

- 顶层键是 `client_token`、`title`、`steps`，不是 `name`、`workflow_name`、`trigger`、`actions`。同一 `client_token` 重提会报 `recommit request`，要换 token。
- 每个 step 必有 `id`、`type`、`title`、`data`；`next` 是字符串或 `null`；分支连线写 `children.links`。`AddRecordTrigger` 的 `data` 必带 `table_name` 和 `watched_field_name`（写主字段名）。
- `condition_list` 是数组。`FindRecordAction`／`SetRecordAction` 的 `filter_info` 写 `{"conjunction":"and","conditions":[...]}`，条件结构同上例；`value` 一律是数组。单选值写 `{"value_type":"option","value":{"name":"x"}}`，文本写 `{"value_type":"text","value":"x"}`。
- 接收人写 `[{"value_type":"ref","value":"$.<step_id>.<fld_id>"}]` 或 `[{"value_type":"user","value":{"id":"ou_xxx"}}]`，不能是字符串。
- 日期常量只有 `today`／`tomorrow`／`yesterday`／`now` 或具体日期；`ReminderTrigger` 的 `field_name` 必须是日期字段；分支条件不引用公式字段。

交付前按 [Workflow 开工必读](../scenes/workflow.md#开工必读) 的核对表逐项核对。

## 创建幂等与恢复

- 每个独立创建意图生成并随请求体保存一个唯一 `client_token`（如 UUID）；同一意图重试复用原 token。不照抄占位值，不靠换 token 绕过重复拦截。
- `recommit request`、超时或部分失败后：有 ID 先 get；无 ID 在目标 Base list 并回读。已创建就沿用该 ID，不再 create；同名不能证明是同一请求。
- 只有确认未创建且授权仍有效时，才恢复未完成请求。明确校验拒绝且确认未创建时，可修正请求体并生成、保存新 token；超时或重复提交不算确认。
- 无法确认时标记“不确定／未完成”，不换 token 盲建。一般失败按[通用调用恢复](shared-cli-invocation.md#通用恢复)分流，沿用主入口恢复预算。

## 常见错误速查

| 错误 | 原因 → 恢复 |
|---|---|
| path "xxx" does not exist in the output path tree | ref 路径或 stepId 错 → 确认 stepId 在 steps 中；路径以 `$.` 开头并用 fieldId：写 `$.step_1.fldXXX`，不写 `$.step_1.客户名称` |
| recordInfo.conditions must be non-empty | `condition_list` 写成 `[]` → `ChangeRecordTrigger` 必须写非空条件；其他触发器条件可选且本次不需要时写 `null` 或省略；见[触发器协议](workflow-triggers.md) |
| At least one of filter info and ref info is required | 缺定位 → SetRecordAction、FindRecordAction 的 `filter_info` 和 `ref_info` 二选一，另一项写 `null`；两者同时非空也错 |
| client token is empty | 缺 `client_token` → 生成唯一值；重试按上节 |
| valueType 'text' not allowed for fieldType '3' | select 格式错 → 改用 option |
| Undefined Step Type | StepType 不支持 → 用 AddRecordTrigger，不用 CreateRecordTrigger |
| prompt references an unknown reference from step | stepId 不存在 → 引用步骤须在同一 workflow 的 steps |
| [2200] Internal Error | ID 重复或 next/children.links 指向不存在步骤 → ID 唯一；检查引用 |
| 工作流结构不完整 | 缺 children → 按[协议](workflow-control-flow.md)配置 IfElseBranch、SwitchBranch、AIClassificationBranch、Loop；AIAgentAction 工具依 [AI Agent](workflow-ai-agent.md#节点关系)用 children.links 挂载；Trigger/普通 Action 不设置 |
| recordInfo.stepId ... is not a valid previous record step for table ... | `ref_info` 前序记录不属于目标表或不在可用路径 → 跨表先按关联值或唯一业务键查目标表，再引用查找结果更新，见[跨表定位示例](workflow-examples.md#跨表唯一定位与更新)；不得删写入动作改发通知 |
