# 角色成员与系统角色协作者

## 适用范围与阅读依赖

- 自定义：`base +role-member-*` 仅管 `role_type=custom_role`；须开启高级权限，用当前环境用户凭证且为 Base 管理员。
- 系统编辑者／阅读者：Drive/CCM 分享；`drive +member-list/add/remove` 按分享权限处理，无需 Base 管理员或高级权限。

## 自定义角色成员

### 参数与命令示例

`--user-id`、`--department-id`、`--chat-id` 可重复、可组合；每次 1–100 个成员，按类型和 ID 去重。

```
lark-cli base +role-member-list --base-token "<base_token>" --role-id "<role_id>" --page-size 50 --as user
lark-cli base +role-member-add --base-token "<base_token>" --role-id "<role_id>" --user-id "<user_open_id>" --department-id "<department_open_id>" --chat-id "<chat_open_id>" --as user
lark-cli base +role-member-remove --base-token "<base_token>" --role-id "<role_id>" --chat-id "<chat_open_id>" --as user --yes
```

### 返回与分页

检查 `data` 的 `items`、`has_more`、`page_token`，把游标传给下一页 `--page-token`；游标缺失或重复时停止翻页。

### 成员写入结果

- `failed_members` 非空即部分失败（HTTP 可成功）：stdout 为 `ok:false`、退出码非零，保留逐成员结果；其 `result_code` 是处理结果，其他成员可能已写入。
- 被拒绝且无 `failed_members` 时按普通错误处理；成功无内容时 `data` 为 `{}`。
- `+role-member-list` 返回成员清单，`+role-get` 不返回。

## 系统角色协作者

高级权限角色按返回的 `role_type` 判定，不得按显示名。编辑者（Editor）→`--perm edit`；阅读者（Reader）→`--perm view`。

确认目标后，`--member-type`：用户 `openid`、群聊 `openchat`、部门 `opendepartmentid`；部门须用户身份；批量添加至多 10 个同类型 ID，每次移除一个。

```
lark-cli drive +member-list --token "<base_token>" --type bitable --as user
lark-cli drive +member-add --token "<base_token>" --type bitable --member-type openchat --member-id "<chat_open_id>" --perm view --as user --yes
lark-cli drive +member-remove --token "<base_token>" --type bitable --member-type openchat --member-id "<chat_open_id>" --as user --yes
```

增删后用 `drive +member-list` 回读。

### Wiki 内 Base 的范围

用 Wiki 节点 token、`--type wiki`。只涉及该 Base 时，列出／添加／移除必须显式传 `--perm-type single_page`；添加／移除默认 `container`，会影响子页面。

移除 Drive 授权可能撤销文档访问，不只解除角色；其他授权、群组或继承权限仍可能生效。

参数和错误处理见 [Drive 成员列表](../../lark-drive/references/lark-drive-member-list.md)、[添加成员](../../lark-drive/references/lark-drive-member-add.md)、[移除成员](../../lark-drive/references/lark-drive-member-remove.md)。
