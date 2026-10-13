# 家庭群 (edu-familygroup) 命令参考

## 命令总览

### group (家庭群查询)

| 命令 | 用途 | 必填参数 |
|------|------|----------|
| `group check-exists` | 检查家庭群是否存在 | `--uid`, `--group-name` |
| `group list-children` | 查询家长绑定的孩子列表 | `--uid` |

### manage (家庭群管理)

| 命令 | 用途 | 必填参数 |
|------|------|----------|
| `manage create` | 创建家庭群 | `--uid`, `--children` |
| `manage invite-parent` | 短信邀请家长加入家庭群 | `--org-id`, `--uid`, `--mobile` |
| `manage add-child` | 为家庭群添加孩子 | `--org-id`, `--uid`, `--name`, (`--mobile` 或 `--students`) |
| `manage toggle-app` | 开启或关闭学生应用权限 | `--org-id`, `--uid`, `--child-staff-id`, `--app-type`, `--open` |

## 意图判断

用户说"家庭群存在/有没有家庭群" → group check-exists
用户说"孩子列表/我的孩子" → group list-children
用户说"创建家庭/建群" → manage create
用户说"邀请家长/拉家长入群" → manage invite-parent
用户说"添加孩子/加娃" → manage add-child
用户说"应用权限/小天地/学习视频" → manage toggle-app

## 核心工作流

1. 检查家庭群是否存在 → `group check-exists --uid <uid> --group-name <name>`
2. 如不存在，创建家庭群 → `manage create --uid <uid> --children '<json>'`
3. 查看已绑定孩子 → `group list-children --uid <uid>`
4. 邀请其他家长 → `manage invite-parent --org-id <orgId> --uid <uid> --mobile <phone>`
5. 添加孩子 → `manage add-child --org-id <orgId> --uid <uid> --name <name> --mobile <phone>`
6. 管理应用权限 → `manage toggle-app --org-id <orgId> --uid <uid> --child-staff-id <id> --app-type XIAOTIANDI --open true`

## 参数说明

### manage create --children 格式

```json
[{"name":"小明","students":[{"corpId":"dingxxx","staffId":"stu001"}]}]
```

每个孩子必填 name + students 数组（含 corpId、staffId），可选 birthday/gender/nick/avatar/period/grade/mobile。

### manage add-child --students 格式

```json
[{"schoolOrgId":111,"studentStaffId":"stu001"}]
```

每项必填 schoolOrgId（整数）+ studentStaffId（字符串）。

### manage toggle-app --app-type 可选值

- `XIAOTIANDI`：小天地（学生圈）
- `LEARNING_VIDEO`：学习视频

## 上下文传递表

| 操作 | 从返回中提取 | 用于 |
|------|-------------|------|
| `manage create` | `orgId`, `cid` | invite-parent / add-child 的 --org-id |
| `group list-children` | 孩子 staffId | toggle-app 的 --child-staff-id |
| `dws edu-contact family parents` | 家长 uid | 所有 edu-familygroup 命令的 --uid |
