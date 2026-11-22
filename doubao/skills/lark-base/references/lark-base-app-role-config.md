# BaseApp 权限 CLI 协议

覆盖角色 `+app-role-list/get/create/update/delete`、成员 `+app-role-member-list/add/remove`、分享与申请 `+app-advperm-share-get/update/apply`。配置前按 [Scene](../scenes/app-permission.md)确定目标；示例不提供授权依据。BaseApp 使用 `app_token`、`AdvPermBaseAppRoleConfig`，不得套普通 Base 的 `+role-*`、`table_rule_map` 或 Dashboard / Docx 顶层；`/app/` 链接先用 `+url-resolve` 取 token。

按需读 [角色 JSON](#角色-json-与字段取值)、[子规则](#表记录与字段)、[示例](#请求示例)、[更新](#更新请求与覆盖语义)、[返回](#角色命令的返回结构)、[回读](#回读与报错)；模板与成员见末尾。

## 操作对象边界（硬约束）

目标及关联 Base / 表全集按 [开工必读](../scenes/app-permission.md#开工必读操作对象边界)定位，不读其他 App 作参考，不用关联 Base 角色代替。

## 角色 JSON 与字段取值

| 字段 | 契约 |
|---|---|
| `role_name` | 创建时非空 |
| `role_type` | `editor` / `reader` / `custom_role`，创建仅 `custom_role` |
| `base_rule_map` | 当前仅 `copy` |
| `page_rule_map` | 页面名 → 页面 / 按钮规则 |
| `default_page_rule` | `perm: read_only\|no_perm`、`button_perm: allow\|deny` |
| `base_data_rule_map` | **关联 Base 名 → 表名 → 数据规则** |
| `default_table_rule` | `perm` 与 `record_operations` 两个维度；后者仅 `edit` 有意义，新建见 [动作规则](../scenes/app-permission.md#表档与动作)，更新保留未触及源值 |

- map key 均为目标 App 可解析的展示名（页、组件、按钮、Base、表），不写组件 / 按钮 ID。名称缺失或不唯一时停止报告，不猜近似对象。
- 页面 `perm` 仅 `read_only|no_perm`；`button_rule` 为 `all_visible` / `none_visible` / `partial`。仅 `partial` 带 `widget_rule_map`（组件名 → 按钮名 → `allow|deny`），不写 Dashboard 规则。
- `no_perm` 页不能带 `all_visible` 或含 `allow` 的 `partial`；已有 `partial` 全为 `deny` 无须改档。用户同时要求页面无权、按钮可见时说明冲突并停止本次角色写入，不擅改要求或试写。
- 表 `perm` 仅 `edit|read_only|no_perm`，无 `manage`、`view_rule`。只复用普通 Base 的 [RecordRule](permission-role-config.md#记录权限-recordrule)、[FieldRule](permission-role-config.md#字段权限-fieldrule)、[FilterRuleGroup](permission-role-config.md#筛选条件-filterrulegroup)子结构，不套其角色流程 / 顶层；App 未列字段语义以下文为准。筛选的 `field_type` / `field_ui_type` / `reference_type` 通常由服务端按目标表中唯一的 `field_name` 补全。
- 默认档回退覆盖未显式配置的既有及未来对象，Get 不展开隐式规则；只改未来默认先按 [更新流程](../scenes/app-permission.md#修改既有角色)保护存量。

## 表、记录与字段

### 表档与子规则

开放表（`edit` / `read_only`）必须同时带完整 `record_rule`、`field_rule`，缺项整请求拒绝且一次只报一表；`no_perm` 不带子规则。

| 表档 | 无额外限制时的子规则 |
|---|---|
| `edit` | `"record_rule":{"record_operations":["add","delete"]}, "field_rule":{"field_perm_mode":"all_edit"}` |
| `read_only` | `"record_rule":{"record_operations":[]}, "field_rule":{"field_perm_mode":"all_read"}` |

### 记录范围（行权限）

`record_rule` **只有以下六键**，不支持 `filter`、`row_filter`、`filter_rules`、`edit_filter_rule`：错误键报 `unknown field ...`，按 hint 修正，不删筛选绕过；旧服务端可能丢弃错误键并裸开所有记录。

| 键 | 含义 |
|---|---|
| `record_operations` | `add` / `delete` 子集，不含 `edit`。新建 edit 无增删排除项时显式写 `["add","delete"]`；`[]` / null 禁止两者，不表示“仅限制字段或本人范围”；更新保留未触及源值 |
| `edit_filter_rule_group` | 可编辑筛选范围，缺省所有记录 |
| `edit_member_scope` | 本人相关的可编辑范围，与编辑 filter 二选一 |
| `other_record_all_read` | 编辑范围外全可读；**仅在已配置有效的 `edit_filter_rule_group` / `edit_member_scope` 时才写入**。无编辑范围时省略本字段；无论 true / false 都不会限制全表编辑，不能代替本人范围 |
| `read_filter_rule_group` | 编辑表：`other_record_all_read: false` 时额外可读范围；只读表：可读范围本身 |
| `read_member_scope` | 本人相关的可读范围，与读 filter 二选一，作用同上 |

scope 示例 `{"creator":true,"fields":["处理人","提交人"]}`：创建人或任一勾选字段包含访问者即命中。`fields` 仅人员字段、结果为人员 / 创建人的公式或查找引用字段，用 `+field-list` 确认；创建人用 `creator`，不列入 `fields`。只看派给自己的报修单可用 `read_only`、`record_operations: []`、`read_member_scope: {"creator":false,"fields":["受理人"]}`（受理人为对应人员字段）。

filter 的人员 / 创建人条件只能 `contains`，**省略 `filter_values`** 表示当前访问者，不填姓名、ID 或 `current_user`。完整嵌套见组合示例，条件类型见 [FilterRuleGroup](permission-role-config.md#筛选条件-filterrulegroup)。只读表不带编辑范围，业务范围判断见 [Scene](../scenes/app-permission.md#记录范围)。

### 字段范围（列权限）

| `field_perm_mode` | 合法表档 | 行为 |
|---|---|---|
| `all_edit` | `edit` | 无自定义，字段随表 |
| `all_read` | `read_only` | 无自定义，字段随表 |
| `specify` | `edit` / `read_only` | 自定义，逐字段 `field_perms`，不得超过表档 |

禁止 `edit + all_read`、`read_only + all_edit`。仅无自定义要求、字段随表且无扩展限制时用前两档；自定义恰好全同档也不能折叠。

`specify` **未列字段无权限，主字段恒只读**；应可见 / 可写字段须从全集逐个列出。只读表字段仅 `read|no_perm`。公式、查找引用、自动编号、创建 / 修改时间、创建人 / 修改人最高 `read`（类型 `formula|lookup|auto_number|created_at|updated_at|created_by|updated_by`），写 `edit` 整请求报 `field ... is not editable, permission 'edit' is invalid`。生成决策见 [Scene 字段范围](../scenes/app-permission.md#字段范围)。

#### 直接生成字段 JSON

假设客户资料仅有主字段客户名称、联系电话、城市。「不让看联系电话」的表条目如下，列全其余可见字段，不能只写电话：

```json
"客户资料": {
  "perm": "read_only",
  "record_rule": {"record_operations": []},
  "field_rule": {
    "field_perm_mode": "specify",
    "field_perms": {"客户名称": "read", "联系电话": "no_perm", "城市": "read"}
  }
}
```

- 若仅「客户名称、联系电话能看」，仍为只读表，将 `field_perms` 换成 `{"客户名称":"read","联系电话":"read"}`；省略城市使其无权，不虚构默认字段参数。
- 若「表保持编辑、开启自定义、全部字段只读」，保留表 `edit`，用 `specify` 和 `{"客户名称":"read","联系电话":"read","城市":"read"}`，不能用 `all_read`；更新保留完整源记录规则及仍适用的扩展列表。

扩展能力只在 `specify` 下生效，两个数组的默认方向不同：

| 字段 | `specify` | `all_edit` / `all_read` |
|---|---|---|
| `allow_edit_and_download_file_fields` | 附件下载白名单；缺省 / `[]` / 回读 null 均全不可下载；列入且字段至少 `read` 才可下载 | 数组被忽略，所有附件可下载 |
| `allow_edit_and_modify_option_fields` | 列入且为 `edit` 的单选 / 多选可修改或新增选项；未提不设 | 均不能改选项 |

「可编辑 / 可读但附件不许下载」须 `specify` 列全字段、下载名单留空；先 `+field-list` 找出附件，在角色可访问的**每张含附件表**上配置，无附件表上的配置无效。只禁止点名附件时保留其他附件下载。回读 null 不代表失败，不用真实角色试写测试值临时开放下载。App 无 `manage`，允许改选项也须 `specify`。

## 请求示例

先按 [两轴判定](../scenes/app-permission.md#授权证据与两轴判定)取授权集合；页面零表述时为全部已有页。`ref` 仅是可配置表全集，不是允许集合，不能把页面数据源全转为表授权。

### 新建请求示例

「新增接单员，只能查看派给自己的报修单」，目标 App 仅有报修台、统计两页，关联运维 Base 的报修单表，受理人为人员字段，未提页面权限 / 复制 / 未来默认。完整请求保留 **Base 名这一层**：

```json
{
  "role_name": "接单员",
  "role_type": "custom_role",
  "base_rule_map": {"copy": true},
  "page_rule_map": {
    "报修台": {"perm": "read_only", "button_rule": "all_visible"},
    "统计": {"perm": "read_only", "button_rule": "all_visible"}
  },
  "default_page_rule": {"perm": "no_perm", "button_perm": "deny"},
  "base_data_rule_map": {
    "运维": {
      "报修单": {
        "perm": "read_only",
        "record_rule": {
          "record_operations": [],
          "read_member_scope": {"creator": false, "fields": ["受理人"]}
        },
        "field_rule": {"field_perm_mode": "all_read"}
      }
    }
  },
  "default_table_rule": {"perm": "no_perm", "record_operations": []}
}
```

保存 `role.json` 后 create，再 list / get。预期：已有两页及按钮全可见，仅本人受理的报修单只读，复制开启，未来页 / 表无权。若原话改为「仅看报修台，所有表无权」，则只保留报修台页面条目、`base_data_rule_map: {}`；统计和全部表随无权默认，不为页面补底表。

### 组合权限示例

「采购审批员可看采购申请页，仅申请列表的审批按钮可见，删除按钮不可见，其他页无权。采购申请表可新增、删除并编辑自己审批的记录，其余记录可读；仅审批意见可持续编辑，审批人新增可填、提交后只读，采购金额可读、预算备注隐藏。供应商表只读，其他表无权；未来页 / 表无权。」

假设该页仅申请列表的审批 / 删除两按钮；仅关联采购管理 Base 的采购申请表、供应商表；采购申请表全集为主字段申请标题、人员字段审批人、审批意见、采购金额、预算备注，无附件 / 选项扩展要求：

```json
{
  "role_name": "采购审批员",
  "role_type": "custom_role",
  "base_rule_map": {"copy": true},
  "page_rule_map": {
    "采购申请": {
      "perm": "read_only",
      "button_rule": "partial",
      "widget_rule_map": {
        "申请列表": {"审批": "allow", "删除": "deny"}
      }
    },
    "供应商管理": {"perm": "no_perm", "button_rule": "none_visible"}
  },
  "default_page_rule": {"perm": "no_perm", "button_perm": "deny"},
  "base_data_rule_map": {
    "采购管理": {
      "采购申请表": {
        "perm": "edit",
        "record_rule": {
          "record_operations": ["add", "delete"],
          "edit_filter_rule_group": {
            "conjunction": "and",
            "filter_rules": [
              {"conjunction": "and", "filters": [{"field_name": "审批人", "operator": "contains"}]}
            ]
          },
          "other_record_all_read": true
        },
        "field_rule": {
          "field_perm_mode": "specify",
          "field_perms": {"申请标题": "read", "审批人": "create", "审批意见": "edit", "采购金额": "read", "预算备注": "no_perm"}
        }
      },
      "供应商表": {
        "perm": "read_only",
        "record_rule": {"record_operations": []},
        "field_rule": {"field_perm_mode": "all_read"}
      }
    }
  },
  "default_table_rule": {"perm": "no_perm", "record_operations": []}
}
```

回读核对按钮明细、编辑本人 / 其余可读、增删、字段与默认档；审批人须保留 `create` 而非漏掉或升 `edit`，满足 [新增时筛选字段约束](permission-role-config.md#筛选字段的-field_perms-权限约束)。

```bash
lark-cli base +app-role-create --app-token <app_token> --json @role.json
lark-cli base +app-role-update --app-token <app_token> --role-id <role_id> --json '{"page_rule_map":{"采购申请":{"perm":"no_perm","button_rule":"none_visible"}}}' --yes
```

## 更新请求与覆盖语义

`+app-role-update` 按页 / 表条目合并，未提交项保留，**提交项整条覆盖，非字段 patch**。开放表须带完整目标记录、字段及扩展规则；目标先按 [Scene 更新流程](../scenes/app-permission.md#修改既有角色)计算。

撤回设备档案表权限、其余保持的示例（先 Get 源）：

```bash
lark-cli base +app-role-update --app-token <app_token> --role-id <role_id> --json '{"base_data_rule_map":{"巡检数据":{"设备档案":{"perm":"no_perm"}}}}' --yes --as user
lark-cli base +app-role-get --app-token <app_token> --role-id <role_id> --as user
```

`no_perm` 表不带子规则；省略表、删本地表项或空 map 均不撤权。

- 可读页必须带 `button_rule`，缺省报 `invalid button rule`（新建同样）；无权页省略时为 `none_visible`。
- 页面降无权：写 `none_visible`，不带 `widget_rule_map`。
- 页面保持可读、未改按钮：保留源档，源 `partial` 时携带完整明细；无权页新放开且没提按钮时 `all_visible`。

## 角色命令的返回结构

以下为 CLI 业务 `data` 层，不套后端 RPC 或通用列表的 `roles/items`：

| 命令 | 返回与处理 |
|---|---|
| list | `data.base_app_roles` 是 **JSON 字符串数组**，逐项解析含 `role_id/role_name/role_type`；`data.total` 为总数，无完整配置 |
| get | `data` 直接是单个完整角色对象，不再整体字符串解析，不读 `data.role` / `base_app_roles` |
| create | `data.role_name`，尽力回读成功还含 `role_id`；缺 ID 用 list 按名定位，不重复创建 |
| update / delete | 成功回执；更新后 get，删除后 list |

```json
{
  "ok": true,
  "identity": "user",
  "data": {
    "base_app_roles": [
      "{\"role_id\":\"rol_example\",\"role_name\":\"审校员\",\"role_type\":\"custom_role\"}"
    ],
    "total": 1
  }
}
```

```bash
lark-cli base +app-role-list --app-token <app_token> --as user --jq '.data.base_app_roles | map(fromjson) | map({role_id, role_name, role_type})'
```

字段缺失、任一项解析失败或 `total > 0` 却读到空，均未完成读取；保留原始 JSON 修正，不用兼容键、`// []` 或空打印吞成无角色。真实空列表须字段存在且为 `[]`；该 jq 不能用于 get。

## 回读与报错

验收见 [Scene](../scenes/app-permission.md#验收与交付)。以下差异不表示失败，按约定比较，不写测试值或读其他角色对照：

| Get 形式 | 等价语义 |
|---|---|
| `record_operations: null`（只读表恒为 null） | `[]`，不能增删 |
| `other_record_all_read` 缺省 | false |
| 读 / 编辑 filter group 缺省 | 所有记录；若存在对应 member scope 则按该档位原样返回 |
| `field_perms: null` | 非 `specify` |
| 两个字段扩展数组 null | `[]` |
| `no_perm` 表 | 只返回 `perm`，无记录 / 字段子规则 |
| 页面 `widget_rule_map` 缺省 | 无按钮级规则 |

`default_table_rule.record_operations` 空返回 `[]`，`base_rule_map.copy: false` 照常返回。

成员 `failed_members` 表示部分成功，先 member-list，再按失败项 `result_code` / `hint` 处理，不能整批重发：

- `800004006`：已有 App 管理权限（含 Owner），不受自定义角色约束，加入无效果，Web 也不可勾选；不重试、不降其文档权限，说明无需加入。
- `800004011`：外租户或对外分享管控拒绝，须先调整分享设置或换本租户成员，不原样重试。
- 其他同步错误确认原因后仅重试失败项。

`button metadata of page:<页名> is unavailable`：该页不能配 `partial`，但页面 / 数据 / 复制仍可配；按钮保留 `all_visible` 或源值，不改 `none_visible` 连带禁用未点名按钮，说明要求未落地。若回读报错，说明已存按钮明细无法读取，不重复提交“修正”。不得删除 / 重建页面组件或改无关分享来绕过报错，报告受阻页及原文。

## 模板 App 的权限边界

- 区分模板本体与其副本，仅按已确认模板状态应用限制，不凭名称、来源或 `enable_share` 推断；普通 App 分享开关不是 Base 高级权限开关。
- 模板仍可 list / get 预览角色，分享被拒不影响预览，不用 `+advperm-enable` 或关联 Base 角色处理。
- 模板不支持 `+app-advperm-share-get/update`；`code 2`、`sharing authorization is not supported for template BaseApp` 时说明无此开关并停止，不重试、换身份或原生 API 绕过。
- 模板访问申请用 [文档权限申请](../../lark-drive/references/lark-drive-apply-permission.md)的 `drive +apply-permission` 申请 `view|edit`，裸 token 用 `--type bitable`。不调用 `+app-advperm-apply`：旧版成功 / 卡片显示自定义角色也不证明授予该角色，审批仅映射文档协作者权限。申请通知 Owner，须明确申请意图，不能因报错自动发起。

## 成员、分享授权和申请

分享 / 申请示例仅适用非模板。

- 自定义角色用下列成员命令，每次 `--user-id`、`--department-id`、`--chat-id` 合计 1～100 个，按类型 + ID 去重。
- Editor / Reader 成员来自协作者，不走角色成员命令（报 `only custom role members can be changed`）。用 `drive +member-list/add/remove --token <app_token> --type bitable`，Editor `--perm edit`，Reader `--perm view`；用户 `--member-type openid`、群 `openchat`。不能用 `--type apps`（1063001）或 `/app/` 链接，写后 member-list 回读。

```bash
lark-cli base +app-role-member-list --app-token <app_token> --role-id <role_id> --page-size 50
lark-cli base +app-role-member-add --app-token <app_token> --role-id <role_id> --user-id <open_id>
lark-cli base +app-role-member-remove --app-token <app_token> --role-id <role_id> --chat-id <open_chat_id> --yes

lark-cli base +app-advperm-share-get --app-token <app_token>
lark-cli base +app-advperm-share-update --app-token <app_token> --enable-share=false
lark-cli base +app-advperm-apply --app-token <app_token> --message "申请配置权限"
```

分享更新显式 `true|false`，前后读取；成员写后 member-list。申请用当前申请人身份，成功仅为提交，不代表授权。
