# 高校通讯录 (college-contact) 命令参考

## 命令总览

### dept (部门管理)

| 命令 | 用途 | 必填参数 |
|------|------|----------|
| `dept get-standard-structure` | 查询高校标准架构信息（组织 ID/行政架构部门 ID 映射） | 无 |
| `dept get-detail` | 查询部门详情 | `--dept-id` |
| `dept get-chain` | 查询部门链（根节点到当前部门） | `--dept-id` |
| `dept search` | 按关键词搜索通讯录（人员/部门/角色） | `--dept-id`, `--keyword` |
| `dept create` | 创建部门 | `--super-id`, `--stru-dept-id`, `--name`, `--dept-type`, `--create-dept-group` |
| `dept update` | 更新部门 | `--dept-id`, `--dept-type` |
| `dept delete` | 删除部门 ⚠️ | `--dept-id` |
| `dept batch-update-type` | 批量修改部门类型 | `--dept-ids`(逗号分隔), `--target-dept-type` |
| `dept overview` | 查询高校概览统计 | 无 |

### employee (员工管理)

| 命令 | 用途 | 必填参数 |
|------|------|----------|
| `employee get-detail` | 查询员工详情 | `--staff-id` |
| `employee add` | 添加员工（返回成功/失败数量及邮箱初始密码） | `--emp-type`, `--main-dept-id`, `--exclusive-account` |
| `employee remove` | 移除员工 ⚠️ | `--staff-ids`(逗号分隔) |
| `employee change-type` | 变更员工类型 | `--staff-id`, `--emp-type` |
| `employee change-dept` | 变更员工部门 | `--staff-id`, `--target-dept-id` |
| `employee send-active-sms` | 发送激活短信 | `--dept-id` |
| `employee list-employees` | 查询部门员工列表 | `--dept-id` |
| `employee list-unaccepted` | 查询未接受邀请的员工列表 | `--dept-id` |
| `employee list-unactive` | 查询未激活的员工列表 | `--dept-id` |
| `employee upgrade-status` | 查询高校通讯录升级状态 | 无 |
| `employee start-upgrade` | 启动高校通讯录升级 | 无 |

### alumni (校友管理)

| 命令 | 用途 | 必填参数 |
|------|------|----------|
| `alumni get-dept-tree` | 查询校友部门树 | `--alumni-dept-id` |
| `alumni get-info` | 查询校友部门详情 | `--alumni-dept-id` |
| `alumni list` | 查询校友列表 | `--alumni-dept-id`, `--order-field`, `--ordering` |
| `alumni query` | 查询单个校友详情 | `--staff-id` |
| `alumni search` | 搜索校友 | `--keyword` |
| `alumni list-unaccepted` | 查询未接受邀请的校友列表 | `--alumni-dept-id` |
| `alumni get-group` | 查询校友群信息 | `--alumni-dept-id` |
| `alumni create-dept` | 创建校友子部门 | `--alumni-dept-id`, `--dept-name` |
| `alumni update-dept` | 更新校友部门名称 | `--alumni-dept-id`, `--dept-name` |
| `alumni delete-dept` | 删除校友部门 ⚠️ | `--alumni-dept-id` |
| `alumni update-managers` | 设置校友部门负责人 | `--alumni-dept-id`, `--admin-user-ids`(逗号分隔) |
| `alumni add-alumnus` | 添加校友 | `--name`, `--mobile`, `--dept-ids`(逗号分隔) |
| `alumni update-alumnus` | 更新校友信息 | `--staff-id`, `--name`, `--dept-ids`(逗号分隔) |
| `alumni remove-alumnus` | 删除校友 ⚠️ | `--staff-id`, `--alumni-dept-id` |
| `alumni cancel-invite` | 取消校友邀请 ⚠️ | `--alumni-dept-id`, `--staff-ids`(逗号分隔) |
| `alumni create-group` | 创建校友群 | `--alumni-dept-id` |
| `alumni disband-group` | 解散校友群 ⚠️ | `--alumni-dept-id` |
| `alumni get-alumni-org-from-graduate` | 查询毕业生校友组织 | 无入参 |
| `alumni create-alumni-org` | 创建校友会组织 | `--org-name` |
| `alumni add-alumni-org-main-admins` | 添加校友会组织管理员 | `--admin-user-ids`(逗号分隔) |

### graduate (毕业年级管理)

| 命令 | 用途 | 必填参数 |
|------|------|----------|
| `graduate query-graduate-years` | 查询毕业年级列表 | 无入参 |
| `graduate query-graduate-depts` | 查询待毕业部门列表 | `--dept-id`, `--graduate-year`(可选) |
| `graduate query-graduate-sub-depts` | 查询毕业子部门列表 | `--dept-id` |
| `graduate query-page-graduate-users` | 分页查询待毕业学生列表 | `--dept-id`, `--graduate-year`/`--offset`/`--size`(可选) |
| `graduate get-task-result` | 查询异步任务执行结果 | `--request-no`, `--type`(可选) |
| `graduate get-alumni-org` | 查询校友组织信息 | 无入参 |
| `graduate query-restore-sub-depts` | 查询可恢复子部门列表 | `--dept-id` |
| `graduate query-dept-deleted-emps` | 查询部门可恢复员工列表 | `--dept-id`, `--offset`/`--size`(可选) |
| `graduate search-graduate` | 搜索毕业部门与员工 | `--keyword`, `--offset`/`--size`(可选) |
| `graduate commit-graduate` | 提交毕业 ⚠️ | `--graduate-dept-ids`(逗号分隔), `--graduate-year`, `--request-no`(可选) |
| `graduate all-graduate` | 全部毕业 ⚠️ | `--graduate-year`, `--request-no`(可选) |
| `graduate batch-graduate` | 批量毕业 ⚠️ | `--dept-id`, `--staff-ids`(逗号分隔) |
| `graduate delete-and-graduate` | 删除并毕业 ⚠️ | `--dept-id`, `--staff-ids`(逗号分隔) |
| `graduate batch-delete-pending` | 批量删除待毕业学生 ⚠️ | `--dept-id`, `--staff-ids`(逗号分隔) |
| `graduate batch-update-pending` | 批量更新待毕业学生 ⚠️ | `--dept-id`, `--staff-ids`(逗号分隔), `--graduate-year` |
| `graduate commit-restore` | 提交恢复 ⚠️ | `--graduate-dept-ids`(逗号分隔), `--request-no`(可选) |

### group (规则管理)

| 命令 | 用途 | 必填参数 |
|------|------|----------|
| `group query-group-rule` | 查询规则 | `--name`(可选), `--offset`(可选), `--size`(可选) |
| `group get-group-rule-schedule` | 查询规则调度 | 无参数 |
| `group query-preview-data` | 查询规则预览数据 | `--offset`(可选), `--size`(可选) |
| `group create-group-rule` | 创建规则 | `--name`, `--tag-code`, `--dept-type`, `--auto-admin`(可选,true/false) |
| `group delete-group-rule` | 删除规则 ⚠️ | `--rule-id` |
| `group enable-group-rule` | 启用规则 | `--rule-id` |
| `group disable-group-rule` | 停用规则 | `--rule-id` |
| `group set-group-rule-schedule` | 设置规则调度 | `--cron`(可选) |
| `group execute-group-rule` | 立即执行规则 ⚠️ | 无参数 |

## 常用参数说明

- `--emp-type`：员工类型，取值 `college_student`（学生）/ `college_teacher`（教职工）
- `--dept-type`：部门类型（如 `contact_grade_dept` 年级 / `contact_class_dept` 班级 / `contact_major_dept` 专业）
- `--staff-id` 单个员工 staffId；`--staff-ids` 为逗号分隔的批量列表
- 列表类命令支持 `--offset` / `--size` 分页与 `--order-field` / `--ordering`(asc/desc) 排序
- `--exclusive-account`、`--create-dept-group`、`--send-active-sms` 为布尔参数（true/false）

## 意图判断

用户说"高校架构/组织架构/学院/系/部门" → dept 子命令
用户说"搜人/找某某老师/找某某同学" → `dept search`
用户说"师生/教职工/学生/员工/辅导员" → employee 子命令
用户说"激活/邀请/未激活账号" → `employee list-unactive` / `list-unaccepted` / `send-active-sms`
用户说"通讯录升级" → `employee upgrade-status` / `start-upgrade`
用户说"校友/校友会/校友部门/添加校友" → alumni 子命令
用户说"毕业年级/毕业年份/待毕业学生/毕业操作" → graduate 子命令
用户说"群规则/建群规则/自动建群" → group 子命令

## 核心工作流

1. 查标准架构 → `dept get-standard-structure`（提取 deptId）
2. 查看部门详情 → `dept get-detail --dept-id <deptId>`
3. 查看部门员工 → `employee list-employees --dept-id <deptId>`
4. 查看员工详情 → `employee get-detail --staff-id <staffId>`

## 上下文传递表

| 操作 | 从返回中提取 | 用于 |
|------|-------------|------|
| `dept get-standard-structure` | `deptId` | dept/employee 子命令的 --dept-id |
| `employee list-employees` | `staffId` | get-detail/change-type/change-dept 的 --staff-id、remove 的 --staff-ids |
| `dept create` | `deptId` | update/delete 的 --dept-id |
| `alumni get-dept-tree` | `alumniDeptId` | alumni 子命令的 --alumni-dept-id |
| `alumni list` | `staffId` | update-alumnus/remove-alumnus 的 --staff-id |
| `graduate query-graduate-depts` | `deptId` | graduate 子命令的 --dept-id |
| `group query-group-rule` | `ruleId` | delete/enable/disable-group-rule 的 --rule-id |

## 危险操作

- `dept delete`、`employee remove`、`alumni delete-dept`、`alumni remove-alumnus`、`alumni cancel-invite`、`alumni disband-group`、`graduate commit-graduate`、`graduate all-graduate`、`graduate batch-graduate`、`graduate delete-and-graduate`、`graduate batch-delete-pending`、`graduate batch-update-pending`、`graduate commit-restore`、`group delete-group-rule`、`group execute-group-rule` 不可逆：非 --dry-run 预览时必须显式传入 --yes 才会真实执行，未传 --yes 会直接拒绝。执行前必须向用户展示操作摘要并获得明确同意，确认后再追加 --yes。
