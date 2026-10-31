# 高级权限角色配置契约

## 目录

职责与阅读依赖｜顶层结构｜角色类型｜Base 级权限｜数据表权限｜仪表盘权限｜文档权限

## 职责与阅读依赖

`+role-create`、`+role-update` 构造 `AdvPermBaseRoleConfig --json`，`+role-get` 读取。先读[JSON 输入](permission-role-commands.md#角色-json-输入)和[更新语义](permission-role-commands.md#读取与更新角色)，确定默认权限、`field_perms` 目标态。

## 顶层结构 (AdvPermBaseRoleConfig)

```
{"role_name":"角色A","role_type":"custom_role","base_rule_map":{"copy":false,"download":false},"table_rule_map":{},"dashboard_rule_map":{},"docx_rule_map":{}}
```

- 必填：非空 `role_name`(string)、`role_type`(string，[RoleType](#角色类型-roletype))。
- `base_rule_map`(map\<string,bool\>)：Base 级权限；新建必填，更新按需。
- 选填：`table_rule_map`(map\<string,TableRule\>，表名为键)、`dashboard_rule_map`(map\<string,DashboardRule\>，仪表盘名为键)、`docx_rule_map`(map\<string,DocxRule\>，仅单品模式，文档名为键)。

## 角色类型 (RoleType)

- `editor`：系统编辑者；仅 `+role-update`；权限可改，受高级权限能力封顶。
- `reader`：系统阅读者；仅 `+role-update`；任一权限不得超过仅可阅读，不得编辑、新增、删除。
- `custom_role`：自定义角色；`+role-create` 仅支持此值；`+role-update` 支持。

## Base 级权限 (BaseRuleMap)

必填性见[顶层结构](#顶层结构-advpermbaseroleconfig)；更新省略模块即保留，见[更新协议](permission-role-commands.md#读取与更新角色)。下例非默认值。

```
{"base_rule_map":{"copy":true,"download":false}}
```

`copy` 允许复制多维表格内容；`download` 允许创建副本、下载、打印多维表格。

## 数据表权限 (TableRule)

普通 `edit` 默认允许新增、删除记录和管理视图，使用下列完整结构。仅明确禁止时才把 `record_operations` 收窄为 `[]` 或 `allow_edit` 设为 `false`。

```
{
  "table_rule_map": {
    "订单表": {
      "perm": "edit",
      "view_rule": {"allow_edit":true,"visibility":{"all_visible":true}},
      "record_rule": {"record_operations":["add","delete"],"other_record_all_read":true},
      "field_rule": {"field_perm_mode":"all_edit"}
    }
  }
}
```

类型：`perm`=string；其余三项依次为 ViewRule、RecordRule、FieldRule。

- `manage`（可管理）/`no_perm`（无权限）：后端不要求三项嵌套规则，不得为校验补造；`no_perm` 不得设置视图、记录、字段权限。
- `edit`（可编辑）：三项必须完整，缺一即失败；默认按上例，明确限制才收窄。
- `read_only`（仅可阅读）：三项必须完整；用 `allow_edit:false`、`record_operations:[]`、全部可见、`field_perm_mode:all_read`。

`+role-update` 按[完整单表更新协议](permission-role-commands.md#读取与更新角色)提交；TableRule 不是递归合并补丁。

### 视图权限 (ViewRule)

```
{"view_rule":{"allow_edit":true,"visibility":{"all_visible":false,"visible_views":["表格视图","看板视图"]}}}
```

`allow_edit`(bool) 允许增删改视图：`edit` 默认 `true`，`read_only` 或明确禁止时为 `false`。`visibility`(object) 必填；其 `all_visible`(bool) 表示是否全部可见，`visible_views`([]string) 填视图名称而非 view ID，且 `all_visible=false` 时至少一个。

`view_rule` 必须含 `allow_edit`、`visibility`，缺一即失败；全部可见也写 `"visibility":{"all_visible":true}`。管理指定视图：`allow_edit:true`、`all_visible:false` 并列出视图。`biz_type=query_form_view` 不得放入 `visible_views`，不能配置可见性。

### 字段权限 (FieldRule)

```
{"field_rule":{"field_perm_mode":"specify","field_perms":{"金额":"edit","日期":"read","状态":"no_perm"},"allow_edit_and_modify_option_fields":[],"allow_edit_and_download_file_fields":[]}}
```

`field_perm_mode`(string)：`all_edit`=全可编辑但不可增删改选项；`all_read`=全可读；`specify`=按字段；`no_perm`=无权限。`field_perms`(map\<string,string\>) 仅 `specify` 有效。

`allow_edit_and_modify_option_fields`、`allow_edit_and_download_file_fields` 均为 []string，分别列允许增删改选项、下载附件的字段名。

`field_perms`：`edit`=可编辑（含新增、阅读）；`create`=仅新增时填写，提交后不可修改（含阅读）；`read`=可读；`no_perm`=无权限。

#### 字段类型与同步表限制

- 按字段操作接口返回的真实 `type` 校验，不按名称猜测。
- 系统字段及 `formula`、`lookup`、`auto_number` 只能为 `read` 或 `no_perm`，不得为 `edit` 或 `create`。
- `field_perms` 必须包含除 4 个系统字段外的所有字段。
- 同步表（`is_sync=true`）的字段不得为 `edit` 或 `create`。

#### 选项与附件权限字段

- `allow_edit_and_modify_option_fields` 仅支持 `select`；无获授权字段时必须为 `[]`。
- `allow_edit_and_download_file_fields` 仅在 `field_perm_mode=specify` 时设置；无对应授权时省略。

#### 新增记录与部分字段持续编辑的组合

允许新增且仅金额、日期可持续修改时，其他可写字段用 `create`，自动编号用 `read`；仍须按 [TableRule](#数据表权限-tablerule) 补齐。

```
{"perm":"edit","record_rule":{"record_operations":["add"]},"field_rule":{"field_perm_mode":"specify","field_perms":{"状态":"create","金额":"edit","日期":"edit","自动编号":"read"},"allow_edit_and_modify_option_fields":[]}}
```

### 记录权限 (RecordRule)

下例兼作 FilterRuleGroup/FilterRule/Filter 结构；完整 TableRule 仍须满足[必填约束](#数据表权限-tablerule)。

```
{
  "record_rule": {
    "record_operations": ["add"],
    "edit_filter_rule_group": {"conjunction":"and","filter_rules":[{"conjunction":"and","filters":[{"field_name":"状态","operator":"is","filter_values":["完成"]}]}]},
    "other_record_all_read": true
  }
}
```

- `record_operations`([]string)：仅 `TablePerm=edit`；`add`=新增，`delete`=删除。
- `edit_filter_rule_group`(FilterRuleGroup)：可编辑范围；全部记录时为空。
- `other_record_all_read`(bool)：全部可读为 `true`，否则 `false`。
- `read_filter_rule_group`(FilterRuleGroup)：仅阅读与编辑范围不同时设置，且要求 `other_record_all_read=false`。

#### 记录操作与同步表限制

- `perm=read_only` 时，`record_operations` 只能为空。
- 同步表（`is_sync=true`）严禁新增、删除记录。

#### 可读范围字段

阅读与编辑范围相同：不得额外生成 `read_filter_rule_group`，设 `other_record_all_read=false`、`read_filter_rule_group=null`；不同时按上表设置。

### 筛选条件 (FilterRuleGroup)

#### 可筛选字段与条件范围

| 项目 | 范围 |
|---|---|
| 条件含义 | 为本人、等于、不等于、大于、大于等于、小于、小于等于、包含、不包含、为空、非空 |
| 支持类型 | 数字、货币、评分、进度、单选、多选、阶段、人员、创建人，以及结果为这些类型的公式、查找引用 |
| 不支持类型 | 文本、日期、复选框、电话、链接、邮箱、附件、关联字段 |

“为本人”遵守[强约束](#字段类型与筛选算子的强约束关系)。

#### 请求结构与字段

- FilterRuleGroup：必填 `conjunction`(string，`and`/`or`)和 `filter_rules`([]FilterRule)。
- FilterRule：`conjunction`(string，选填 `and`/`or`，默认 `and`)；`filters`([]Filter，必填)。
- Filter 必填：`field_name`(string，仅 `can_filter=true`；当前用户类条件按 API 返回结构)、`operator`(string，见下表)。
- Filter 选填：`field_type`(string，按 `+field-list`/字段接口 `type` 判断；常见 `select`、`user`、`created_by`、`number`、部分 `formula`/`lookup`)；`is_invalid`(bool，条件是否无效)。
- Filter 条件字段：公式/引用必须填 `reference_type`(string)，其他字段不得填；`field_ui_type`(string) 有值时必须填；`filter_values`([]string) 在 `isEmpty`/`isNotEmpty` 和 `user` 时不设置，其他必须设置，选项填 `name`。

`operator`：`is`=等于，`isNot`=不等于，`contains`=包含，`doesNotContain`=不包含，`isEmpty`=为空，`isNotEmpty`=不为空，`isGreater`=大于，`isGreaterEqual`=大于等于，`isLess`=小于，`isLessEqual`=小于等于。

创建/更新时，服务端 `filterFiller` 补全 `field_type`、`field_ui_type`、`reference_type`；客户端通常只传 `field_name`、`operator`、`filter_values`。

#### 字段类型与筛选算子的强约束关系

- `user`/`created_by`：仅用 `contains`，不得用 `is`、`isNot` 等精确匹配；这是当前成员匹配，省略 `filter_values`，不得填姓名或用户 ID；回读可能为 `null`。
- 只有上述类型正确、回读 `is_invalid=false`，且无 `other_record_all_read=true` 或其他全表读取规则覆盖，才能证明当前成员隔离。
- `select`（`multiple=false`）：单一选项等于/不等于必须用 `is`/`isNot` 且只能一个值；匹配多个选项集合必须用 `contains`/`doesNotContain`，多值为“或”。
- `select`（`multiple=true`）：`is`/`isNot` 可填多个选项；`is` 加 A、B 表示同时包含 A 和 B（A&B），不是 A 或 B。
- “包含任一”用 `contains`，或拆成多个 `is` 条件并设 `filter_rules.conjunction=or`。`contains`/`doesNotContain` 多值按任一匹配；“等于 A 或 B”拆成多条条件并用“或”。

#### 百分比字段

仅快照中 `Number` 且 `percentage=true` 的字段按 0~1 小数存储。先解析单位：“六成”=60%=0.6；百分数 N（含裸值 60）写 N/100；明确给出存储小数时不重复换算。

大于 60、大于 20%、小于 60 分别写大于 0.6、大于 0.2、小于 0.6。非 percentage 字段保留原值。

#### 筛选字段的 field_perms 权限约束

- 除系统字段外，筛选字段不得遗漏，至少为 `read`；筛选不要求字段只读。
- 当且仅当 `record_operations` 含 `add` 时，筛选字段至少为 `create`，保证新增时可写；仅可阅读不触发此下限。
- 不得取消或降低上述系统下限。`edit` 不是筛选机制强制下限，是否可编辑按权限目标决定；此下限不构成额外授权。

## 仪表盘权限 (DashboardRule)

`dashboard_rule_map` 不会开启跟随访问者权限统计。另用[仪表盘跟随访问者权限统计开关](dashboard-permission-statistics.md)管理 `is_adv_perm_enable`。

```
{"dashboard_rule_map":{"数据看板":{"perm":"read_only"},"内部看板":{"perm":"no_perm"}}}
```

`perm` 为 string：`read_only`=仅可阅读；`no_perm`=无权限。

## 文档权限 (DocxRule)

仅在单品模式（`is_base_solo=true`）可用。

```
{"docx_rule_map":{"文档A":{"perm":"edit","allow_download":true},"文档B":{"perm":"read_only"}}}
```

`perm`(string) 必填：`edit`=可编辑，`read_only`=仅可阅读，`no_perm`=无权限。`allow_download`(bool) 选填，表示是否允许下载/导出。
