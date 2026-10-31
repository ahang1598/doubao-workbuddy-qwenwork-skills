# 高级权限角色管理命令

## 适用范围与阅读依赖

开关/状态见[高级权限模式命令](permission-commands.md)。

## 命令与适用范围

|命令|规则|
|---|---|
|`+role-list`|角色摘要|
|`+role-get`|完整配置；更新/删除判断前读取|
|`+role-create`|仅 `custom_role`；先读[配置协议](permission-role-config.md)|
|`+role-update`|按[合并规则](#读取与更新角色)提交|
|`+role-delete`|仅自定义角色|
|`lark-cli drive +member-list/add/remove`|按[系统角色协作者](permission-role-members.md#系统角色协作者)管理系统编辑者/阅读者|

## 角色 JSON 输入

JSON 输入方式以具体子命令的 `--help` 为准。默认用内联 JSON；只有该命令明确支持时才用文件或 stdin。记录命令的 `@file` 写法不适用于角色命令；`@` 被当作 JSON 字面量拒绝时，先改输入方式再重试。

## 角色读取结果

`+role-list` 含系统/自定义角色摘要，`+role-get` 返回完整配置。list/get/create 的 `data.data` 是字符串化 JSON：jq 用 `fromjson`，Python 用 `json.loads`；不得把包装层/字符串当角色对象。

list 解码为 `{"base_roles":["<又一层 JSON 字符串>",...]}`；列角色：
```bash
--jq '.data.data | fromjson | .base_roles[] | fromjson | {role_id,role_name,role_type}'
```

## 读取与更新角色

先用 `+role-get` 读取当前 `role_name`、`role_type`、权限结构。`+role-update` 必带前两项和 `--yes`；仅传 `table_rule_map` 报 `API error [1]`。

1. 未传的 `base_rule_map`、`table_rule_map`、`dashboard_rule_map`、`docx_rule_map` 等模块不变。
2. `table_rule_map` 按表增量合并：未传表不变；所传 `table_rule_map.<table>` 整体替换，不递归合并。
3. 读取、修改、提交目标表完整 `TableRule`；无需带其他表。

`+role-delete` 仅删自定义角色；系统角色可在权限上限内调整，不可删除。

## 常用示例

数据表、字段、记录、仪表盘、文档、筛选权限见[角色配置协议](permission-role-config.md)。改名用 `+role-update --role-id "<role_id>" --yes`，保留类型：`--json '{"role_name":"负责人","role_type":"custom_role"}'`。

### 从零建角色的命令序列

以下为成功调用；只换 token、表名、权限：
```bash
lark-cli base +base-get --base-token "<base_token>" --as user --jq '.data.base.is_advanced'
lark-cli base +advperm-enable --base-token "<base_token>" --as user # 仅 is_advanced=false；不收 --yes
lark-cli base +role-create --base-token "<base_token>" --as user \
  --jq '.data.data | fromjson | .role_id' \
  --json '{"role_name":"负责人","role_type":"custom_role","base_rule_map":{"copy":false,"download":false},
"table_rule_map":{"订单表":{"perm":"edit","view_rule":{"allow_edit":true,"visibility":{"all_visible":true}},
"record_rule":{"record_operations":["add","delete"],"other_record_all_read":true},"field_rule":{"field_perm_mode":"all_edit"}},
"客户表":{"perm":"read_only","view_rule":{"allow_edit":false,"visibility":{"all_visible":true}},
"record_rule":{"record_operations":[],"other_record_all_read":true},"field_rule":{"field_perm_mode":"all_read"}}}}'
lark-cli base +role-get --base-token "<base_token>" --role-id "<role_id>" --as user --jq '.data.data | fromjson'
lark-cli base +role-update --base-token "<base_token>" --role-id "<role_id>" --as user --yes \
  --json '{"role_name":"负责人","role_type":"custom_role","table_rule_map":{"客户表":{"perm":"no_perm"}}}'
# 仅用户点名具体人员时添加；当前用户是 Base Owner，不能加入自定义角色（返回 MsgCannotSpread）
# lark-cli base +role-member-add --base-token "<base_token>" --role-id "<role_id>" --user-id "<点名人员的 open_id>" --as user
```

`+role-create` 报 `API error [1]` 的实测原因：
- `table_rule_map`、`dashboard_rule_map` 或 `field_perms` 引用了不存在的表名、看板名、字段名（表要用名字，不用 table_id）；
- `perm` 取了非法值；
- 表项缺 `perm`、`view_rule`、`record_rule`、`field_rule` 中任一项（`read_only` 也要齐全）；
- 角色名与已有角色重复。

提交前用 `+table-list`、`+dashboard-list`、`+field-list` 取真实名字，用 `+role-list` 查重名。实测不会触发：`perm:"manage"`、真实看板的 `dashboard_rule_map`、`specify` 仅列部分字段、省略 `base_rule_map`。

无 `+permission-*`、`+advperm-get`。加成员仅有 `--user-id`/`--department-id`/`--chat-id`；用户点名人员才执行；搭建系统只建角色不加人。
