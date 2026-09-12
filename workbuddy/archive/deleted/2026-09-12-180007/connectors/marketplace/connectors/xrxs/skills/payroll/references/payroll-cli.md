# payroll 工资条 CLI 接口

> **前置条件：** 先阅读 [`../SKILL.md`](../SKILL.md) 了解全局能力。

工资条相关 CLI 接口。包括工资条发放、撤回、导出、确认提醒、批量发放方案、工资条列表与详情等。

## 适用场景

- getArchiveSalaryGroupList：根据年月获取归档工资组列表
- getSalaryPlanSimpleList：根据工资组ID查询对应工资条方案列表 salaryGroupId->引用 xrxs-cli payroll getArchiveSalaryGroupList
- batchSendSalarySlip：批量发放工资条
- getSalaryList：工资条列表 - 获取列表
- getFilterNum：获取工资条详情页的统计数字（已读、未读、已确认等）
- getSalaryBillList：获取工资条详情列表，支持筛选和分页
- hasPlanOrCanCreate：检查工资组是否已有方案或可以创建方案
- getQuickSendSalaryPlanList：获取快捷发放的工资条方案列表
- getPayrollArchives：获取工资归档列表 (发工资条初始页面)
- exportSalaryBills：触发工资条详情异步导出，返回本次导出产生的 summaryExportId 列表。数据按 DEFUALT_SPLIT_NUM 分片，每片一条导出记录、一个独立 ID；员工数 <= 分片阈值时返回单元素列表。 salaryReleaseId->引用 xrxs-cli payroll getSalaryList
- getSalaryBillAckRemindChannel：获取工资条确认提醒的通道列表 salaryReleaseId->引用 xrxs-cli payroll getSalaryList
- quickSendSalarySlip：工资报表页-快捷发放工资条
- sendSalaryBillAckRemind：参数同 xrxs-cli payroll sendSalaryBillAckRemindPreview
- cancelSalary：获取工资条列表，对目标工资条进行撤回 salaryReleaseId ->引用 xrxs-cli payroll getSalaryList
- salaryBillCancel：撤回单条工资条操作,选定工资条后确定其中需要撤回的员工，进行撤回操作 salaryBillId->引用 xrxs-cli payroll getSalaryList employeeId->引用 xrxs-cli payroll getSalaryBillList
- batchSendSalarySlipPreview：是否确认批量发放工资条 添加方案时先选择工资组，根据选择的工资组获取对应工资条方案 添加方案-工资组选项（salaryGroupId）->引用 xrxs-cli payroll getArchiveSalaryGroupList 添加方案-工资条方案（salaryPlanId）->引用 xrxs-cli payroll getSalaryPlanSimpleList
- sumSalaryBatchSend：批量发放工资条-计算发放人数 批量发放确认前调用，返回值为确认接口部分入参
- sumSalaryQuickSend：快捷发放工资条-计算方案人数 快捷发放二次确认前调用，返回值为确认接口的部分入参
- quickSendSalarySlipPreview：是否发送工资条（快捷发放预览）
- sendSalaryBillAckRemindPreview：先获取对应月份工资条列表；对目标工资条进行操作 salaryReleaseId->引用 xrxs-cli payroll getSalaryList channelTypes->引用 xrxs-cli payroll getSalaryBillAckRemindChannel

## 推荐命令

### getArchiveSalaryGroupList

获取对应月份归档工资组

根据年月获取归档工资组列表

```bash
xrxs-cli payroll getArchiveSalaryGroupList
  --yearmo <yearmo>
```

> 请求方式：`GET`。无请求体，参数通过 `--<name> <value>` 传递。

参数：

| 参数 | 必填 | 类型 | 说明 |
|------|------|------|------|
| `--yearmo` | 是 | string | 年月，如202506 |

返回：

- `code`：状态码，0=成功
- `status`：是否成功
- `message`：提示信息
- `data`：归档工资组列表

`data` 主要字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `data[].id` | string |  |
| `data[].name` | string |  |

### getSalaryPlanSimpleList

根据工资组查询对应工资条方案

根据工资组ID查询对应工资条方案列表
salaryGroupId->引用 xrxs-cli payroll getArchiveSalaryGroupList

```bash
xrxs-cli payroll getSalaryPlanSimpleList
  --salaryGroupId <salaryGroupId>
```

> 请求方式：`GET`。无请求体，参数通过 `--<name> <value>` 传递。

参数：

| 参数 | 必填 | 类型 | 说明 |
|------|------|------|
| `--salaryGroupId` | 是 | string | 工资组ID |

返回：

- `code`：状态码，0=成功
- `status`：是否成功
- `message`：提示信息
- `data`：工资条方案列表

`data` 主要字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `data[].id` | string |  |
| `data[].name` | string |  |

### batchSendSalarySlip

```bash
xrxs-cli payroll batchSendSalarySlip
  --request-body json
```

> 请求方式：`POST`，`Content-Type: application/json`。JSON 请求体请使用 `--request-body json` 传递。

请求体字段：

| 字段 | 必填 | 类型 | 说明 |
|------|------|------|------|
| `headId` | 否 | string |  |
| `yearmo` | 否 | integer |  |
| `accountId` | 否 | string |  |
| `companyId` | 否 | string |  |
| `schemeList` | 否 | array<object> | 工资组及对应工资条方案 |
| `accountName` | 否 | string |  |

返回：

- `code`：状态码
- `status`：是否成功：true.是、false.否
- `message`：异常信息
- `data`：返回结果集

`data` 主要字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `data.isAllError` | boolean | 是否全部异常 |
| `data.errorSelfMailList` | array<string> | 异常邮箱列表 |

### getSalaryList

```bash
xrxs-cli payroll getSalaryList
  --year <year>
  --page <page>
```

> 请求方式：`GET`。无请求体，参数通过 `--<name> <value>` 传递。

参数：

| 参数 | 必填 | 类型 | 说明 |
|------|------|------|------|
| `--year` | 否 | string | 年份名称 |
| `--page` | 否 | string | 页码 默认1 |
| `--pageSize` | 否 | string | 每页条数 默认10 |

返回：

- `code`：状态码
- `status`：是否成功：true.是、false.否
- `message`：异常信息
- `data`：返回结果集

`data` 主要字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `data.page` | integer |  |
| `data.total` | integer |  |
| `data.result` | array<object> |  |
| `data.result[].id` | integer |  |
| `data.result[].name` | string |  |
| `data.result[].yearmo` | string |  |
| `data.result[].addtime` | integer |  |
| `data.result[].reportId` | string | 报表ID |
| `data.result[].companyId` | string |  |
| `data.result[].dataSource` | string | 工资条数据源 |
| `data.result[].addtimeDesc` | string |  |
| `data.result[].operateType` | integer |  |
| `data.result[].confirmNumber` | string | 确认人数 |
| `data.result[].showRemindBtn` | integer | 是否显示提醒按钮 0-不显示 1-显示 |
| `data.result[].recipientNumber` | integer | 接受人数 |
| `data.result[].sendAccountName` | string | 发放人姓名 |
| `data.result[].unConfirmNumber` | string | 未确认人数 |
| `data.result[].alreadyReadNumber` | string | 已读人数 |
| `data.result[].salaryBillSettingId` | integer | 工资条设置方案ID |
| `data.pageSize` | integer |  |

### getFilterNum

工资条详情页-获取统计数字

获取工资条详情页的统计数字（已读、未读、已确认等）

```bash
xrxs-cli payroll getFilterNum
  --salaryReleaseId <salaryReleaseId>
  --type <type>
```

> 请求方式：`GET`。无请求体，参数通过 `--<name> <value>` 传递。

参数：

| 参数 | 必填 | 类型 | 说明 |
|------|------|------|------|
| `--salaryReleaseId` | 是 | string | 工资发放ID |
| `--type` | 是 | string | 类型 |

返回：

- `code`：状态码，0=成功
- `status`：是否成功
- `message`：提示信息
- `data`：统计数字

`data` 主要字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `data.total` | integer |  |
| `data.readNum` | integer |  |
| `data.unreadNum` | integer |  |
| `data.confirmedNum` | integer |  |
| `data.unconfirmedNum` | integer |  |

### getSalaryBillList

工资条详情页-获取详情列表

获取工资条详情列表，支持筛选和分页

```bash
xrxs-cli payroll getSalaryBillList
  --salaryReleaseId <salaryReleaseId>
  --selectType <selectType>
  --selectValue <selectValue>
```

> 请求方式：`GET`。无请求体，参数通过 `--<name> <value>` 传递。

参数：

| 参数 | 必填 | 类型 | 说明 |
|------|------|------|------|
| `--salaryReleaseId` | 是 | string | 工资发放ID |
| `--selectType` | 否 | string | 筛选类型，默认0，手机：1，邮箱：2，姓名：3 |
| `--selectValue` | 否 | string | 筛选值，默认空 |
| `--filterType` | 否 | string | 过滤类型，默认0 |
| `--filterFailMail` | 否 | string | 失败邮箱过滤，默认空 |
| `--type` | 否 | string | 类型，默认0 |
| `--page` | 否 | string | 页码，默认1 |
| `--pageSize` | 否 | string | 每页条数，默认10 |

返回：

- `code`：状态码，0=成功
- `status`：是否成功
- `message`：提示信息
- `data`：工资条详情列表

`data` 主要字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `data.page` | integer |  |
| `data.total` | integer |  |
| `data.result` | array<object> |  |
| `data.result[].email` | string |  |
| `data.result[].amount` | string |  |
| `data.result[].employeeId` | string |  |
| `data.result[].readStatus` | integer |  |
| `data.result[].employeeName` | string |  |
| `data.result[].salaryBillId` | integer |  |
| `data.result[].confirmStatus` | integer |  |
| `data.pageSize` | integer |  |

### hasPlanOrCanCreate

快捷发放-是否有方案或可创建

检查工资组是否已有方案或可以创建方案

```bash
xrxs-cli payroll hasPlanOrCanCreate
  --salaryGroupId <salaryGroupId>
```

> 请求方式：`GET`。无请求体，参数通过 `--<name> <value>` 传递。

参数：

| 参数 | 必填 | 类型 | 说明 |
|------|------|------|------|
| `--salaryGroupId` | 是 | string | 工资组ID |

返回：

- `code`：状态码，0=成功
- `status`：是否成功
- `message`：提示信息
- `data`：true=有方案或可创建，false=不可创建

### getQuickSendSalaryPlanList

快捷发放-获取方案列表

获取快捷发放的工资条方案列表

```bash
xrxs-cli payroll getQuickSendSalaryPlanList
  --pageNo <pageNo>
  --pageSize <pageSize>
  --dataSourceType <dataSourceType>
  --reportId <reportId>
  --salaryGroupId <salaryGroupId>
```

> 请求方式：`GET`。无请求体，参数通过 `--<name> <value>` 传递。

参数：

| 参数 | 必填 | 类型 | 说明 |
|------|------|------|------|
| `--pageNo` | 是 | string | 页码 |
| `--pageSize` | 是 | string | 每页条数 |
| `--dataSourceType` | 是 | string | 数据来源类型 |
| `--reportId` | 是 | string | 报表ID |
| `--salaryGroupId` | 否 | string | 工资组ID（可选） |

返回：

- `code`：状态码，0=成功
- `status`：是否成功
- `message`：提示信息
- `data`：快捷发放方案列表

`data` 主要字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `data.list` | array<object> |  |
| `data.list[].planId` | string |  |
| `data.list[].planName` | string |  |
| `data.list[].salaryGroupId` | string |  |
| `data.total` | integer |  |

### getPayrollArchives

```bash
xrxs-cli payroll getPayrollArchives
  --year <year>
  --type <type>
```

> 请求方式：`GET`。无请求体，参数通过 `--<name> <value>` 传递。

参数：

| 参数 | 必填 | 类型 | 说明 |
|------|------|------|------|
| `--year` | 否 | string | 年份 |
| `--type` | 否 | string | 归档类型 |
| `--divisionId` | 否 | string | 事业部ID |
| `--needSummary` | 否 | string | 是否需要汇总大表（1=需要，0=不需要） |
| `--isReportList` | 否 | string | 是否是报表列表 |

返回：

- `code`：状态码
- `status`：是否成功：true.是、false.否
- `message`：异常信息
- `data`：返回结果集

### getSalaryBillAckRemindChannel

获取工资条确认提醒通道

获取工资条确认提醒的通道列表
salaryReleaseId->引用 xrxs-cli payroll getSalaryList

```bash
xrxs-cli payroll getSalaryBillAckRemindChannel
  --salaryReleaseId <salaryReleaseId>
```

> 请求方式：`GET`。无请求体，参数通过 `--<name> <value>` 传递。

参数：

| 参数 | 必填 | 类型 | 说明 |
|------|------|------|------|
| `--salaryReleaseId` | 是 | string | 工资发放ID |

返回：

- `code`：状态码，0=成功
- `status`：是否成功
- `message`：提示信息
- `data`：确认提醒通道列表

`data` 主要字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `data[].channelId` | string |  |
| `data[].channelName` | string |  |
| `data[].channelType` | string |  |

### quickSendSalarySlip

```bash
xrxs-cli payroll quickSendSalarySlip
  --request-body json
```

> 请求方式：`POST`，`Content-Type: application/json`。JSON 请求体请使用 `--request-body json` 传递。

请求体字段：

| 字段 | 必填 | 类型 | 说明 |
|------|------|------|------|
| `headId` | 否 | string | 总公司ID |
| `yearmo` | 否 | integer | 报表所在月份 |
| `reportId` | 否 | string | 工资报表ID |
| `accountId` | 否 | string | 管理员 - 账号ID |
| `companyId` | 否 | string | 公司ID |
| `isAutoSeed` | 否 | integer | 是否自动发放 |
| `reportName` | 否 | string | 工资报表名称 |
| `accountName` | 否 | string | 管理员 - 名字 |
| `salaryPlans` | 否 | array<object> | 方案列表 |
| `salaryGroupId` | 否 | string | 工资组id |

返回：

- `code`：状态码
- `status`：是否成功：true.是、false.否
- `message`：异常信息
- `data`：返回结果集

`data` 主要字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `data.isAllError` | boolean | 是否全部异常 |
| `data.errorSelfMailList` | array<string> | 异常邮箱列表 |

### sendSalaryBillAckRemind

发送工资条确认提醒

参数同 xrxs-cli payroll sendSalaryBillAckRemindPreview

```bash
xrxs-cli payroll sendSalaryBillAckRemind
  --request-body json
```

> 请求方式：`POST`，`Content-Type: application/json`。JSON 请求体请使用 `--request-body json` 传递。

请求体字段：

| 字段 | 必填 | 类型 | 说明 |
|------|------|------|------|
| `channelType` | 否 | string |  |
| `salaryReleaseId` | 否 | integer |  |

返回：

- 无 data 字段，仅返回状态码与提示信息。

### cancelSalary

工资条列表-撤回操作

获取工资条列表，对目标工资条进行撤回
salaryReleaseId ->引用 xrxs-cli payroll getSalaryList

```bash
xrxs-cli payroll cancelSalary
  --salaryReleaseId <salaryReleaseId>
```

> 请求方式：`GET`。无请求体，参数通过 `--<name> <value>` 传递。

参数：

| 参数 | 必填 | 类型 | 说明 |
|------|------|------|------|
| `--salaryReleaseId` | 是 | string | 工资发放ID |

返回：

- `code`：状态码，0=成功
- `status`：是否成功
- `message`：提示信息
- `data`：空字符串

### salaryBillCancel

工资条详情页-个人撤回操作

撤回单条工资条操作,选定工资条后确定其中需要撤回的员工，进行撤回操作
salaryBillId->引用 xrxs-cli payroll getSalaryList
employeeId->引用 xrxs-cli payroll getSalaryBillList

```bash
xrxs-cli payroll salaryBillCancel
  --salaryBillId <salaryBillId>
  --employeeId <employeeId>
```

> 请求方式：`GET`。无请求体，参数通过 `--<name> <value>` 传递。

参数：

| 参数 | 必填 | 类型 | 说明 |
|------|------|------|------|
| `--salaryBillId` | 是 | string | 工资条ID |
| `--employeeId` | 是 | string | 员工ID |

返回：

- `code`：状态码，0=成功
- `status`：是否成功
- `message`：提示信息
- `data`：空字符串

### exportSalaryBills

导出工资条详情

触发工资条详情异步导出，返回本次导出产生的 summaryExportId 列表。数据按 DEFUALT_SPLIT_NUM 分片，每片一条导出记录、一个独立 ID；员工数 <= 分片阈值时返回单元素列表。
salaryReleaseId->引用 xrxs-cli payroll getSalaryList

```bash
xrxs-cli payroll exportSalaryBills
  --salaryReleaseId <salaryReleaseId>
  --maskTag <maskTag>
  --verifyKey <verifyKey>
```

> 请求方式：`POST`。无请求体，参数通过 `--<name> <value>` 传递。

参数：

| 参数 | 必填 | 类型 | 说明 |
|------|------|------|------|
| `--salaryReleaseId` | 是 | string | 工资发放ID |
| `--maskTag` | 否 | string | 掩码标记（1=掩码，0=不掩码），默认1 |
| `--verifyKey` | 否 | string | 验证密钥，默认空 |

返回：

- `code`：状态码，0=成功
- `status`：是否成功
- `message`：提示信息
- `data`：本次导出产生的 summaryExportId 列表；数据分片导出时为 N 个 ID，整单导出时为 1 个 ID

> **注意：** 当前 CLI 未提供导出状态的轮询查询命令（exportStatus 不可用），拿到 summaryExportId 后暂无法通过 CLI 查询导出进度与下载链接，需告知用户此限制。

### sumSalaryBatchSend

批量发放工资条-计算发放人数

批量发放确认前调用，返回值为确认接口部分入参

```bash
xrxs-cli payroll sumSalaryBatchSend
  --request-body json
```

> 请求方式：`POST`，`Content-Type: application/json`。JSON 请求体请使用 `--request-body json` 传递。

请求体字段：

| 字段 | 必填 | 类型 | 说明 |
|------|------|------|------|
| `yearmo` | 是 | integer | 年月（工资月份），如202509 |
| `schemeList` | 是 | array<object> | 工资组及对应工资条方案 |
| `schemeList[].salaryPlanId` | 是 | integer | 工资条方案id |
| `schemeList[].salaryGroupId` | 是 | string | 工资组id |

返回：确认接口的部分入参（各方案发放人数等）。

### sumSalaryQuickSend

快捷发放工资条-计算方案人数

快捷发放二次确认前调用，返回值为确认接口的部分入参

```bash
xrxs-cli payroll sumSalaryQuickSend
  --request-body json
```

> 请求方式：`POST`，`Content-Type: application/json`。JSON 请求体请使用 `--request-body json` 传递。

请求体字段：

| 字段 | 必填 | 类型 | 说明 |
|------|------|------|------|
| `yearmo` | 是 | integer | 年月（工资月份），如202509 |
| `reportId` | 是 | string | 报表id |
| `planIdStr` | 是 | string | 方案id，多个用逗号分隔，如 "137973,137974" |

返回：确认接口的部分入参（各方案发放人数等）。

### quickSendSalarySlipPreview

是否发送工资条（快捷发放预览）。返回数据需渲染为 `<confirm-card>` 确认卡片。

```bash
xrxs-cli payroll quickSendSalarySlipPreview
  --request-body json
```

> 请求方式：`POST`，`Content-Type: application/json`。JSON 请求体请使用 `--request-body json` 传递。

请求体字段：

| 字段 | 必填 | 类型 | 说明 |
|------|------|------|------|
| `yearmo` | 是 | integer | 所属月份，如202509 |
| `reportId` | 是 | string | 报表ID |
| `planIdStr` | 是 | string | 方案ID，多个逗号分隔（预览计算用） |
| `salaryPlans` | 是 | array<object> | 工资条方案列表（实际发放用） |
| `salaryPlans[].planId` | 是 | integer | 方案ID |
| `salaryPlans[].salaryReleaseName` | 是 | string | 工资条名称 |

返回：cli预览通用返回结构（概览+详情），`data` 含 `summaryData`、`detailData`、`summaryHeaderMap`、`detailHeaderMap` 等。

### batchSendSalarySlipPreview

是否确认批量发放工资条

可手动添加方案，添加方案时先选择工资组，根据选择的工资组获取对应工资条方案
添加方案-工资组选项（salaryGroupId）->引用 xrxs-cli payroll getArchiveSalaryGroupList
添加方案-工资条方案（salaryPlanId）->引用 xrxs-cli payroll getSalaryPlanSimpleList

```bash
xrxs-cli payroll batchSendSalarySlipPreview
  --request-body json
```

> 请求方式：`POST`，`Content-Type: application/json`。JSON 请求体请使用 `--request-body json` 传递。

请求体字段：

| 字段 | 必填 | 类型 | 说明 |
|------|------|------|------|
| `yearmo` | 是 | integer | 年月（工资月份），如202509 |
| `schemeList` | 是 | array<object> | 实际发放用 - 工资组及工资条方案详情 |
| `schemeList[].planId` | 是 | integer | 方案id |
| `schemeList[].planName` | 是 | string | 方案名称 |
| `schemeList[].reportId` | 是 | string | 报表id |
| `schemeList[].salaryGroupId` | 是 | string | 工资组id |
| `schemeList[].salaryGroupName` | 否 | string | 工资组名称 |
| `schemeList[].key` | 否 | string | 缓存key |
| `schemeList[].peopleNumber` | 否 | integer | 人数 |
| `schemeList[].successNumber` | 否 | integer | 成功人数 |
| `schemeList[].failNumber` | 否 | integer | 失败人数 |
| `previewSchemeList` | 是 | array<object> | 预览计算用 - 工资组及对应工资条方案 |
| `previewSchemeList[].salaryPlanId` | 是 | integer | 工资条方案id |
| `previewSchemeList[].salaryGroupId` | 是 | string | 工资组id |

返回：

- `code`：状态码，0=成功
- `status`：是否成功
- `message`：提示信息
- `data`：cli预览通用返回结构（概览+详情）

`data` 主要字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `data.headId` | string | headId |
| `data.accountId` | string | 账号ID |
| `data.companyId` | string | 公司ID |
| `data.detailData` | array<object> | 详情部分的具体数据 |
| `data.detailData[].key` | string | 缓存key |
| `data.detailData[].planId` | integer | 方案ID |
| `data.detailData[].planName` | string | 方案名称 |
| `data.detailData[].reportId` | string | 对应报表id |
| `data.detailData[].failNumber` | integer | 失败人数 |
| `data.detailData[].peopleNumber` | integer | 人数 |
| `data.detailData[].salaryGroupId` | string | 工资组id |
| `data.detailData[].successNumber` | integer | 成功人数 |
| `data.detailData[].salaryGroupName` | string | 工资组名称 |
| `data.summaryData` | object | 概览数据 |
| `data.summaryData.yearmo` | integer | 工资月份 |
| `data.summaryData.failNumberTotal` | integer | 失败人数 |
| `data.summaryData.planNumberTotal` | integer | 方案总数 |
| `data.summaryData.peopleNumberTotal` | integer | 总人数 |
| `data.summaryData.successNumberTotal` | integer | 成功人数 |
| `data.detailHeaderMap` | object | 详情部分的字段key和名称 |
| `data.summaryHeaderMap` | object | 概览部分的字段key和名称 |
| `data.detailHeaderShowField` | array<string> | 详情部分展示的字段key |
| `data.summaryHeaderShowField` | array<string> | 概览部分展示的字段key |

### sendSalaryBillAckRemindPreview

发送工资条确认提醒-提醒预览

先获取对应月份工资条列表；对目标工资条进行操作
salaryReleaseId->引用 xrxs-cli payroll getSalaryList
channelTypes->引用 xrxs-cli payroll getSalaryBillAckRemindChannel

```bash
xrxs-cli payroll sendSalaryBillAckRemindPreview
  --request-body json
```

> 请求方式：`POST`，`Content-Type: application/json`。JSON 请求体请使用 `--request-body json` 传递。

请求体字段：

| 字段 | 必填 | 类型 | 说明 |
|------|------|------|------|
| `channelTypes` | 是 | array<string> | 渠道类型：app-薪人薪事员工端 personEmail-在职员工个人邮箱 workEmail-工作邮箱 dismissionPersonEmail-离职员工个人邮箱 dtalk-钉钉 qywx-企业微信 yzj-云之家 lark-飞书 weaver-泛微 |
| `salaryReleaseId` | 是 | integer | 工资发放ID |

返回：

- `code`：状态码，0=成功
- `status`：是否成功
- `message`：提示信息
- `data`：cli预览通用返回结构（概览+详情）

`data` 主要字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `data.headId` | string | headId |
| `data.accountId` | string | 账号ID |
| `data.companyId` | string | 公司ID |
| `data.detailData` | array<object> | 详情部分的具体数据 |
| `data.detailData[].id` | integer | 工资发放ID |
| `data.detailData[].name` | string | 工资条方案名称 |
| `data.detailData[].yearmo` | string | 报表月份 |
| `data.detailData[].addtime` | integer | 发送时间（秒级时间戳） |
| `data.detailData[].reportId` | string | 报表ID |
| `data.detailData[].companyId` | string | 公司ID |
| `data.detailData[].dataSource` | string | 数据源 |
| `data.detailData[].addtimeDesc` | string | 发送时间描述，格式yyyy.MM.dd/HH:mm:ss |
| `data.detailData[].operateType` | integer | 操作类型 |
| `data.detailData[].confirmNumber` | string | 确认人数，确认功能关闭时为-- |
| `data.detailData[].remindChannel` | string | 提醒渠道，多个以逗号分割 |
| `data.detailData[].showRemindBtn` | integer | 是否展示提醒按钮 1是 0否 |
| `data.detailData[].recipientNumber` | integer | 接收人数 |
| `data.detailData[].sendAccountName` | string | 发送人 |
| `data.detailData[].unConfirmNumber` | string | 提醒员工数（未确认人数），确认功能关闭时为-- |
| `data.detailData[].alreadyReadNumber` | string | 已读人数，-1时为-- |
| `data.detailData[].salaryBillSettingId` | integer | 工资条设置方案ID |
| `data.summaryData` | object | 概览数据 |
| `data.summaryData.yearmo` | integer | 工资月份 |
| `data.summaryData.planNumberTotal` | integer | 方案数 |
| `data.summaryData.remindEmployeeTotal` | integer | 提醒员工总数（未确认人数） |
| `data.detailHeaderMap` | object | 详情部分的字段key和名称 |
| `data.summaryHeaderMap` | object | 概览部分的字段key和名称 |
| `data.detailHeaderShowField` | array<string> | 详情部分展示的字段key |
| `data.summaryHeaderShowField` | array<string> | 概览部分展示的字段key |

## 注意事项

- 写入/删除操作，执行前必须确认用户意图。
- 预览接口（路径/命令名以 `-preview` 结尾）调用后，xrxs-cli 会返回 `taskId`、`summaryHeaderMap`、`summaryData`、`originalName`、`riskLevel`。必须将其渲染为 `<confirm-card>` 组件，属性为 `taskId`、`summaryHeaderMap`（JSON 字符串）、`summaryData`（JSON 字符串）、`riskLevel`、`taskName`（取 `originalName`），禁止直接展示 JSON。
- 不要将 xrxs-cli 执行的命令返回给用户。


## 参考

- [payroll](../SKILL.md) -- 全部命令
