# 工作流值类型、赋值与条件契约

## 使用范围与依赖
含条件、字段赋值或 `ref` 时，完整读本页，再按[输出引用](workflow-outputs.md#使用范围与依赖)读公共路径和所用节点章节；动态接收人还要读人员引用和接收人约束。

## 基础值（ValueInfo）
用 value_type 区分：

|value_type|value 类型、约束、示例|
|---|---|
|text|string，如 `"文本"`|
|number|number，如 `100`|
|boolean|boolean，如 `true`|
|date|具体/相对时间 string；值见下|
|option|`{id,name}`，如 `{"id":"opt1","name":"已完成"}`|
|link|`{text,link}`；两项均为 text/ref ValueInfo 数组，如 `{"text":[{"value_type":"text","value":"详情"}],"link":[{"value_type":"ref","value":"$.step_1.fldXXX"}]}`|
|user|`{id,name}`；所有用户 value 的 ID 统一用 CLI 转换的 OpenID `ou_xxxx`|
|group|`{id,name}`；所有群 value 的 ID 统一用 CLI 转换的 ChatID `oc_xxxx`，如 `{"id":"oc_xxx","name":"群名"}`|
|ref|前置节点输出路径 string；格式见[引用路径格式](workflow-outputs.md#引用路径格式)|

date 值可以是具体时间 `"2025/01/01"`、`"2025/01/01 11:00"`，或相对时间：`now`、`today`、`yesterday`（这三个可加时刻，如 `"today 11:00"`），以及 `lastWeek`、`currentMonth`、`lastMonth`、`theLastWeek`、`theNextWeek`、`theLastMonth`、`theNextMonth`。

`lastWeek`／`lastMonth` 是上一个自然周／月；`theLastWeek`／`theLastMonth` 是截至今天的过去 7 天／30 天；`theNextWeek`／`theNextMonth` 是今天起的未来 7 天／30 天。用户说“上周”用 `lastWeek`，说“最近 7 天”才用 `theLastWeek`。

## 文本拼接与字段赋值
### TextRefItem
用数组混排文本、引用，构造消息等动态内容：
`[{"value_type":"text","value":"订单 "},{"value_type":"ref","value":"$.step_1.fieldxxx"},{"value_type":"text","value":" 已更新"}]`
### RecordFieldValue
`{"field_name":"客户名称","value":[{"value_type":"text","value":"名称"}]}`
### 字段值构造
按字段类型选 `value_type`：文本 `text`、数字 `number`、单选 `option`（value 写 `{"name":"已完成"}`）、人员 `user`（value 写 `{"id":"ou_xxxx"}`）、引用 `ref`。
### 关联字段赋值
`value_type: "link"` 表示文字加 URL，不是 Base 的 SingleLink／DuplexLink 记录关系；不要把普通 Record CellValue 的 `[{"id":"rec..."}]` 塞进这个 ValueInfo。

把触发记录本身写进关联字段时引用 `$.<触发步骤>.record`；`$.<触发步骤>.recordId` 是文本，Link 字段会拒收。

按业务键关联主档时，先用 `FindRecordAction` 精确匹配，再用 `IfElseBranch` 判断 `$.find_master.recordNum == 1`。只有唯一匹配分支执行下面的 `SetRecordAction.data`；0 条或多条走独立分支，不写关联。
`firstfieldsRecord.recordId` 是[查找节点](workflow-outputs.md#findrecordaction查找记录)的记录 ID 数组；未经唯一检查不得取首条掩盖重名。

`{"table_name":"订单表","max_set_record_num":1,"ref_info":{"step_id":"submit_trigger"},"field_values":[{"field_name":"关联记录","value":[{"value_type":"ref","value":"$.find_master.firstfieldsRecord.recordId"}]}]}`
前提：“关联记录”是指向查找表的真实 Link 字段；submit_trigger 是订单表记录触发器；find_master 已按输入业务键查找。替换表名、字段名、步骤 ID。
ref_info 定位本次记录，field_values 引用查得主档，不得互换。分支、筛选和完整图分别按[控制流](workflow-control-flow.md#条件分支ifelsebranch)、本页条件结构和[步骤图](workflow-schema.md)构造。

同一记录重复处理须写回同一目标集合；已有不同关联先核对冲突。保存后回读定义；触发后回读 Link、适用反向关系、派生结果。dry-run、定义保存或普通 Record 写入成功都不能证明自动关联成功。
授权与验收见 [Form Scene](../scenes/form.md#输入与业务关联)；当前环境拒绝该引用时报告能力边界，不改用 URL 或名称文本凑成功。

## 条件与记录定位
Workflow 条件用本节对象，不得套用 View 筛选 tuple。记录触发器的监听及修改前后条件位置见[记录触发器对比](workflow-triggers.md#记录触发器对比)。

### 条件值类型与非空约束
构造 FieldWatchItem、AndCondition、RecordFilterInfo、分支条件前，用 +field-list 查左值真实类型；右值须匹配：

|左值字段|右值 value_type|约束|
|---|---|---|
|number、数值型 formula/lookup|number|非空有限数字；禁 `""`、null、空数组|
|datetime/created_at/updated_at|date|合法日期/受支持相对时间；选日期可用 operator|
|select|option|名称或 ID 来自真实字段配置|
|user/group_chat|user/group 或类型匹配的 ref|禁未解析姓名、角色描述、示例 ID|
|text|text|需右值的 operator 禁空字符串|

isEmpty/isNotEmpty 不带业务右值；其他 operator 右值非空，禁 null、空数组、空字符串。数值边界写入 filter_info.conditions[].value 且匹配左值类型。
阈值丢失可能静默失败：右值保存成空数组或空字符串后，流程可能仍是 enabled 却永远匹配不到记录。创建成功和启用状态都不能代替保存后对完整条件的核对。

### AndCondition（Trigger 过滤条件）与 RecordFilterInfo
共用以下形态；RecordFilterInfo.conjunction 仅支持 and，“字段 X 等于 A 或 B”用 containsAny：
`{"conjunction":"and","conditions":[{"field_name":"状态","operator":"is","value":[{"value_type":"option","value":{"name":"进行中"}}]}]}`
### OrGroup（Branch 分支条件）
`{"conjunction":"or","conditions":[{"conjunction":"and","conditions":[{"left_value":{"value_type":"ref","value":"$.step_1.fieldxxx"},"operator":"isGreater","right_value":[{"value_type":"number","value":1000}]}]}]}`
operator 可选值：`is`、`isNot`、`containsAny`、`doesNotContainAny`、`containsAll`、`isEmpty`、`isNotEmpty`、`isGreater`、`isGreaterEqual`、`isLess`、`isLessEqual`。
### `select` 字段多值匹配
等于单个值用 `is` 加一个 option。匹配多个值（L2 或 L3）用 `containsAny`： `[{"value_type":"option","value":{"name":"L2"}},{"value_type":"option","value":{"name":"L3"}}]`。
不得用多个 is：它们按 OR 处理，不能实现 AND；用 containsAny。Select 条件 value_type 必须为 option；value 可只含真实 name，无需选项 ID。
### RefInfo
`{"step_id":"step_trigger"}`
