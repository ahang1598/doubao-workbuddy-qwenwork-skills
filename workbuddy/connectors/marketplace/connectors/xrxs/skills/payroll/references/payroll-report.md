# payroll 薪酬核算与工资报表

> **前置条件：** 先阅读 [`../SKILL.md`](../SKILL.md) 了解全局能力。

薪酬核算、工资报表相关操作。包括计算报表、获取计算结果、查看异常、归档/冻结/解冻报表、导出报表、查询部门/岗位、获取报表字段等。

## 适用场景

- calculateActiveReportData：计算活动报表 备注 极端当前月活动报表 计算活动报表数据
- getCalcResult：获取计算结果 备注 获取当前工资最细一次报表计算结果  false为计算中   ture为计算结束
- getReportTag：获取报表异常数据 备注 获取当前活动报表 上方异常奇数标签
- getReportFields：获取报表字段 备注 获取当前活动报表中都有哪些字段
- getEmployeeReportInfo：获取单个员工的报表中的特定字段
- getEmployeeInfo：获取权限内得员工 备注 根据姓名或手机号获取当前管理员工资组权限范围内的某个员工
- getReportCalculateSalaryGroupList：获取计算工资组 备注 获取 计算工资组列表，主要用于计算报表时选择工资组
- archiveReport：归档报表 备注 归档当前活动月工资报表 归档工资报表
- archiveReportPreview：获取归档报表预览 备注 归档之前获取归档预览弹窗
- createLedger：新建报表 备注 新建账套（新建薪酬月）
- frozenSalaryGroupList：获取冻结/解冻弹窗的工资组列表 备注 点击冻结/解冻按钮，弹出冻结/解冻弹窗
- frozenReportPreview：获取冻结弹窗 备注 冻结预览
- unfreezeReportPreview：获取解冻弹窗 备注 解冻预览
- freezeReport：冻结报表 备注 冻结已归档工资组报表
- unfreezeReport：解冻报表 备注 解冻已归档工资组报表
- getReportNumber：获取当前报表中的人数 备注 归档之前获取可以归档得工资组列表
- getPayrollField：获取导出报表得弹窗 获取可导出字段
- exportNewActiveReport：导出工资全数据报表(增加筛选) 备注 来自 PayrollController 的 xrxs-cli payroll exportNewActiveReport 接口导出工资活动报表 导出活动报表
- searchDepartment：搜索部门（keyword 必填，limit 可选）
- getJobsNew：获取所有实时的岗位列表
- exportResult：获取导出活动报表任务的结果<br> 备注<br> 导出活动报表
- getPayrollArchivesForReport：获取工资归档列表(报表归档导出查看使用)

## 推荐命令

### calculateActiveReportData

计算活动报表
备注 极端当前月活动报表
计算活动报表数据

```bash
xrxs-cli payroll calculateActiveReportData
  --salaryGroupIds <salaryGroupIds>
```

> 请求方式：`GET`。无请求体，参数通过 `--<name> <value>` 传递。

参数：

| 参数 | 必填 | 类型 | 说明 |
|------|------|------|------|
| `--salaryGroupIds` | 否 | string | 需要计算得工资组id 逗号分隔 来源 xrxs-cli payroll getReportCalculateSalaryGroupList 接口返回值中得 salaryGroupId属性 |

返回：

- `code`：状态码
- `status`：是否成功：true.是、false.否
- `message`：异常信息
- `data`：返回结果集

### getCalcResult

获取计算结果
备注 获取当前工资最细一次报表计算结果  false为计算中   ture为计算结束

```bash
xrxs-cli payroll getCalcResult
```

> 请求方式：`POST`。无请求体，参数通过 `--<name> <value>` 传递。

返回：

- `code`：状态码
- `status`：是否成功：true.是、false.否
- `message`：异常信息
- `data`：返回结果集

### getReportTag

获取报表异常数据
备注 获取当前活动报表 上方异常奇数标签

```bash
xrxs-cli payroll getReportTag
```

> 请求方式：`POST`。无请求体，参数通过 `--<name> <value>` 传递。

返回：

- `code`：状态码
- `status`：是否成功：true.是、false.否
- `message`：异常信息
- `data`：返回结果集

`data` 主要字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `data.errorCount` | integer | 工资计算错误人数 |
| `data.reentryCount` | integer | 再入职人数 |
| `data.payrollUnsetCount` | integer | 未定薪人数 |
| `data.negativeSalaryCount` | integer | 负薪人数 |
| `data.insuranceNoDataCount` | integer | 社保无数据人数 |
| `data.attendanceNoDataCount` | integer | 考勤无数据人数 |

### getReportFields

获取报表字段
备注 获取当前活动报表中都有哪些字段

```bash
xrxs-cli payroll getReportFields
```

> 请求方式：`POST`。无请求体，参数通过 `--<name> <value>` 传递。

返回：

- `code`：状态码
- `status`：是否成功：true.是、false.否
- `message`：异常信息
- `data`：返回结果集

`data` 主要字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `data[].fiedldId` | string | 字段id |
| `data[].fiedldName` | string | 字段名称 |

### getEmployeeReportInfo

```bash
xrxs-cli payroll getEmployeeReportInfo
  --employeeId <employeeId>
  --fields <fields>
```

> 请求方式：`GET`。无请求体，参数通过 `--<name> <value>` 传递。

参数：

| 参数 | 必填 | 类型 | 说明 |
|------|------|------|------|
| `--employeeId` | 否 | string | 员工id  从 xrxs-cli payroll getEmployeeInfo 返回值中得 employeeId 属性获取 |
| `--fields` | 否 | string | 从 xrxs-cli payroll getReportFields 返回值中得 fiedldId 获取 逗号分割 |

返回：

- `code`：状态码
- `status`：是否成功：true.是、false.否
- `message`：异常信息
- `data`：返回结果集

`data` 主要字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `data[].fiedldId` | string | 字段id |
| `data[].fiedldName` | string | 字段名 |
| `data[].fieldValue` | string | 字段值 |

### getEmployeeInfo

获取权限内得员工
备注 根据姓名或手机号获取当前管理员工资组权限范围内的某个员工

```bash
xrxs-cli payroll getEmployeeInfo
  --keyword <keyword>
```

> 请求方式：`GET`。无请求体，参数通过 `--<name> <value>` 传递。

参数：

| 参数 | 必填 | 类型 | 说明 |
|------|------|------|------|
| `--keyword` | 否 | string | 用户输入 手机号活姓名得关键字 |

返回：

- `code`：状态码
- `status`：是否成功：true.是、false.否
- `message`：异常信息
- `data`：返回结果集

`data` 主要字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `data[].name` | string |  |
| `data[].mobile` | string |  |
| `data[].employeeId` | string |  |
| `data[].departmentName` | string |  |

### getReportCalculateSalaryGroupList

获取计算工资组
备注 获取 计算工资组列表，主要用于计算报表时选择工资组

```bash
xrxs-cli payroll getReportCalculateSalaryGroupList
```

> 请求方式：`GET`。无请求体，参数通过 `--<name> <value>` 传递。

返回：

- `code`：状态码
- `status`：是否成功：true.是、false.否
- `message`：异常信息
- `data`：返回结果集

`data` 主要字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `data[].frozenStatus` | integer | 必须 工资组冻结状态 0 未冻结 1已冻结 |
| `data[].employeeCount` | integer | 必须 工资组人数 |
| `data[].salaryGroupId` | string | 必须 工资组id |
| `data[].salaryGroupName` | string | 必须 工资组名称 |
| `data[].lastCalculateTime` | string | 必须 工资组最后计算时间 |

### archiveReportPreview

获取归档报表预览
备注 归档之前获取归档预览弹窗。返回数据需渲染为 `<confirm-card>` 确认卡片。

```bash
xrxs-cli payroll archiveReportPreview
```

> 请求方式：`GET`。无请求体，无参数。

返回：cli 预览通用结构，`data` 含 `summaryData`、`detailData`、`summaryHeaderMap`、`detailHeaderMap` 等。

### createLedger

新建报表（新建账套/新建薪酬月）

```bash
xrxs-cli payroll createLedger
```

> 请求方式：`POST`。无请求体，无参数。

返回：

- `code`：状态码
- `status`：是否成功：true.是、false.否
- `message`：异常信息
- `data`：返回结果集（string）

> 写操作，执行前必须确认用户意图。

### archiveReport

归档报表
备注 归档当前活动月工资报表
归档工资报表

```bash
xrxs-cli payroll archiveReport
  --salaryGroupIds <salaryGroupIds>
```

> 请求方式：`POST`。无请求体，参数通过 `--<name> <value>` 传递。

参数：

| 参数 | 必填 | 类型 | 说明 |
|------|------|------|------|
| `--salaryGroupIds` | 否 | string | 工资组id 逗号分割 来自 xrxs-cli payroll getReportNumber 接返回值中  salaryGroups 属性的 id |

返回：

- `code`：状态码
- `status`：是否成功：true.是、false.否
- `message`：异常信息
- `data`：返回结果集

`data` 主要字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `data.yearmo` | integer |  |
| `data.failNum` | integer | 失败人数 |
| `data.nsrsbhs` | array<object> |  |
| `data.nsrsbhs[].nsrsbh` | string | 纳税人识别号 |
| `data.nsrsbhs[].status` | integer | 0-不可用，1-可用 |
| `data.nsrsbhs[].errorInfo` | string | 错误信息 |
| `data.nsrsbhs[].obligorId` | string | 扣缴义务人id |
| `data.nsrsbhs[].contractId` | string | 主体编码 |
| `data.nsrsbhs[].nsrsbhName` | string | 纳税人名称 |
| `data.nsrsbhs[].contractName` | string | 主体名称 |
| `data.nsrsbhs[].withholdCycle` | integer | 累计预扣周期 |
| `data.nsrsbhs[].usersInternetSystem` | string | 网税系统用户名 |
| `data.nsrsbhs[].electronicAccountNumber` | string | 电子报税账户号 |
| `data.reportIds` | array<string> |  |
| `data.successNum` | integer | 成功人数 |
| `data.lastArchiveId` | string | 最后一个归档id（多个工资组同时归档，返回最后一个工资组归档id） |
| `data.differentDataList` | array<object> | 算税数据与申报数据不一致的员工数据 |
| `data.isTaxCalculationAgain` | integer | 是否需要税款计算 1-需要,0-不需要 |
| `data.differentDataHeaderSet` | array<string> | ///////////////生成算税数据不一致excel 开始/////////////////// |
| `data.beingAuditedSalaryGroups` | array<string> | 正在审核的工资组 |
| `data.reportEmptyDataSalaryGroups` | array<string> | 报表无数据的工资组 |
| `data.taxDeclareDifferenceFileUrl` | string | 不一致扣缴义务人信息 |
| `data.isTaxCalculateDateDifference` | integer |  |
| `data.taxDeclareDifferenceDataMapList` | array<object> | ///////////////生成算税数据不一致excel 结束/////////////////// |
| `data.needTaxCalculationAgainDetailUrl` | string | 不一致信息详情 |
| `data.needTaxCalculationAgainSalaryGroups` | array<string> | 个税数据与最后一次算税不一致 |
| `data.taxCalculateDataDifferenceSalaryGroups` | array<string> | 归档数据与已申报个税数据不一致 |

### frozenSalaryGroupList

获取冻结/解冻弹窗的工资组列表
备注 点击冻结/解冻按钮，弹出冻结/解冻弹窗

```bash
xrxs-cli payroll frozenSalaryGroupList
  --popType <popType>
```

> 请求方式：`GET`。无请求体，参数通过 `--<name> <value>` 传递。

参数：

| 参数 | 必填 | 类型 | 说明 |
|------|------|------|------|
| `--popType` | 否 | string | 弹窗状态 1-冻结弹窗；0-解冻弹窗 |

返回：

- `code`：状态码
- `status`：是否成功：true.是、false.否
- `message`：异常信息
- `data`：返回结果集

`data` 主要字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `data[].status` | integer | 1 未归档 2已归档 3已冻结 |
| `data[].salaryGroupId` | string | 工资组id |
| `data[].lastArchiveTime` | string | 上次归档时间 |
| `data[].salaryGroupName` | string | 工资组名称 |
| `data[].archiveEmployeeCount` | integer | 当前算薪归档人数 |

### frozenReportPreview

获取冻结弹窗（冻结预览）。返回数据需渲染为 `<confirm-card>` 确认卡片。

```bash
xrxs-cli payroll frozenReportPreview
  --salaryGroupIds <salaryGroupIds>
```

> 请求方式：`GET`。无请求体，参数通过 `--<name> <value>` 传递。

参数：

| 参数 | 必填 | 类型 | 说明 |
|------|------|------|------|
| `--salaryGroupIds` | 否 | string | 工资组 id，逗号分割。来自 xrxs-cli payroll frozenSalaryGroupList 返回值中 salaryGroupId 属性 |

返回：cli 预览通用结构，`data` 含 `summaryData`、`detailData`、`summaryHeaderMap`、`detailHeaderMap` 等。

### unfreezeReportPreview

获取解冻弹窗（解冻预览）。返回数据需渲染为 `<confirm-card>` 确认卡片。

```bash
xrxs-cli payroll unfreezeReportPreview
  --salaryGroupIds <salaryGroupIds>
```

> 请求方式：`GET`。无请求体，参数通过 `--<name> <value>` 传递。

参数：

| 参数 | 必填 | 类型 | 说明 |
|------|------|------|------|
| `--salaryGroupIds` | 否 | string | 工资组 id，逗号分割。来自 xrxs-cli payroll frozenSalaryGroupList（popType=0）返回值中 salaryGroupId 属性 |

返回：cli 预览通用结构，`data` 含 `summaryData`、`detailData`、`summaryHeaderMap`、`detailHeaderMap` 等。

### freezeReport

冻结报表
备注 冻结已归档工资组报表

```bash
xrxs-cli payroll freezeReport
  --salaryGroupIds <salaryGroupIds>
```

> 请求方式：`GET`。无请求体，参数通过 `--<name> <value>` 传递。

参数：

| 参数 | 必填 | 类型 | 说明 |
|------|------|------|------|
| `--salaryGroupIds` | 否 | string | 来自 xrxs-cli payroll frozenSalaryGroupList 返回值中 salaryGroupId属性  逗号分割 |

返回：

- `code`：状态码
- `status`：是否成功：true.是、false.否
- `message`：异常信息
- `data`：返回结果集

### unfreezeReport

解冻报表
备注 解冻已归档工资组报表

```bash
xrxs-cli payroll unfreezeReport
  --salaryGroupIds <salaryGroupIds>
```

> 请求方式：`GET`。无请求体，参数通过 `--<name> <value>` 传递。

参数：

| 参数 | 必填 | 类型 | 说明 |
|------|------|------|------|
| `--salaryGroupIds` | 否 | string |  |

返回：

- `code`：状态码
- `status`：是否成功：true.是、false.否
- `message`：异常信息
- `data`：返回结果集

### getReportNumber

获取当前报表中的人数
备注 归档之前获取可以归档得工资组列表

```bash
xrxs-cli payroll getReportNumber
```

> 请求方式：`GET`。无请求体，参数通过 `--<name> <value>` 传递。

返回：

- `code`：状态码
- `status`：是否成功：true.是、false.否
- `message`：异常信息
- `data`：返回结果集

`data` 主要字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `data.total` | integer | 总数 |
| `data.salaryGroups` | array<object> | 工资组人数 |
| `data.salaryGroups[].id` | string |  |
| `data.salaryGroups[].code` | string |  |
| `data.salaryGroups[].name` | string |  |
| `data.salaryGroups[].count` | integer |  |
| `data.salaryGroups[].status` | integer | 工资组报表状态 0已计算 1未计算 2已冻结 |
| `data.salaryGroups[].archiveTime` | string |  |
| `data.salaryGroups[].payrollUnsetCount` | integer | 未定新人数 |
| `data.salaryGroups[].insuranceNoDataSum` | integer | 社保无数据 |
| `data.salaryGroups[].attendanceNoDataSum` | integer | 考勤无数据 |
| `data.salaryGroups[].removeEmployeeCount` | integer | 本月移除人数 |
| `data.salaryGroups[].unusualAutoAdjustmentCount` | integer | 自动调薪失败人数 |
| `data.payrollUnsetSum` | integer | 未定薪人数 |
| `data.insuranceNoDataSum` | integer | 社保无数据 |
| `data.attendanceNoDataSum` | integer | 考勤无数据 |
| `data.calculateBasePayTypeFile` | string | 计薪标准为0的员工文件下载地址 |
| `data.unusualAutoAdjustmentSum` | integer | 转正自动调薪异常人数 |

### getPayrollField

获取导出报表得弹窗
获取可导出字段

```bash
xrxs-cli payroll getPayrollField
  --type <type>
  --reportId <reportId>
```

> 请求方式：`GET`。无请求体，参数通过 `--<name> <value>` 传递。

参数：

| 参数 | 必填 | 类型 | 说明 |
|------|------|------|------|
| `--type` | 否 | string | 弹窗类型 全数据大表1  归档汇总大表8 归档明细表4 |
| `--reportId` | 否 | string | 报表id 活到报表全数据 默认给 allPayrollReport 归档报表的id从 xrxs-cli payroll getPayrollArchives 接口返回值中的 reportid获取 |

返回：

- `code`：状态码
- `status`：是否成功：true.是、false.否
- `message`：异常信息
- `data`：返回结果集

`data` 主要字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `data.payrollTax` | array<object> | 个税类信息 |
| `data.payrollTax[].fiedldId` | string | 字段id |
| `data.payrollTax[].fiedldName` | string | 字段名称 |
| `data.employeeBiz` | array<object> | 岗位类字段 |
| `data.employeeBiz[].fiedldId` | string | 字段id |
| `data.employeeBiz[].fiedldName` | string | 字段名称 |
| `data.payrollSalary` | array<object> | 工资类信息 |
| `data.payrollSalary[].fiedldId` | string | 字段id |
| `data.payrollSalary[].fiedldName` | string | 字段名称 |
| `data.employeePerson` | array<object> | 个人信息类字段 |
| `data.employeePerson[].fiedldId` | string | 字段id |
| `data.employeePerson[].fiedldName` | string | 字段名称 |
| `data.payrollInsurance` | array<object> | 社保类信息 |
| `data.payrollInsurance[].fiedldId` | string | 字段id |
| `data.payrollInsurance[].fiedldName` | string | 字段名称 |
| `data.payrollAttendance` | array<object> | 考勤类信息 |
| `data.payrollAttendance[].fiedldId` | string | 字段id |
| `data.payrollAttendance[].fiedldName` | string | 字段名称 |

### exportNewActiveReport

导出工资全数据报表(增加筛选)
备注 来自 PayrollController 的 xrxs-cli payroll exportNewActiveReport 接口导出工资活动报表
导出活动报表

```bash
xrxs-cli payroll exportNewActiveReport
  --request-body json
```

> 请求方式：`POST`，`Content-Type: application/x-www-form-urlencoded`。JSON 请求体请使用 `--request-body json` 传递。

请求体字段：

| 字段 | 必填 | 类型 | 说明 |
|------|------|------|------|
| `name` | 否 | string | 报表名字 默认全数据 |
| `type` | 否 | string | 操作类型 默认 1就可以 |
| `header` | 否 | string | 选择得 表头得id 从 xrxs-cli payroll getPayrollField 接口 返回值中得 header 中得 value 中得field 获取 然后逗号分割 |
| `maskTag` | 否 | string | 人员信息导出形式 0-不掩码导出 1-掩码导出 |
| `cacheKey` | 否 | string |  |
| `reportId` | 否 | string | 报表id 全数据使用 allPayrollReport  归档报表传对应的roportId 从 xrxs-cli payroll getPayrollArchives 接口中获取reportId |
| `screenJson` | 否 | string | 筛选条件 默认格式{"salaryGroupIds":[],"departmentId":[],"jobId":[],"employeeId":[]}<br>里面四个属性<br>salaryGroupIds-薪资组id数组<br>departmentId-部门id数组 来自 xrxs-cli payroll searchDepartment 返回值中得 id<br>jobId-岗位id数组 来自 xrxs-cli payroll getJobsNew 返回值中  children 下得id<br>employeeId-员工id数组 xrxs-cli payroll getEmployeeInfo 下得员工id |
| `isDecimalSetting` | 否 | string | 小数展示  0-按报表展示位数导出 1-按实际计算数据位数导出 |
| `selectReportType` | 否 | string | 查询报表类型：-1.全数据、0.明细表、1.部门汇总 (全数据默认给 -1) |

返回：

- `code`：状态码
- `status`：是否成功：true.是、false.否
- `message`：异常信息
- `data`：返回结果集

### searchDepartment

搜索部门

```bash
xrxs-cli payroll searchDepartment
  --keyword <keyword>
  --limit <limit>
```

> 请求方式：`GET`。无请求体，参数通过 `--<name> <value>` 传递。

参数：

| 参数 | 必填 | 类型 | 说明 |
|------|------|------|------|
| `--keyword` | 是 | string | 搜索关键字（必填） |
| `--limit` | 否 | string | 返回结果最大条数，默认 50，最大 100（超过夹紧为 100） |

返回：

- `code`：状态码
- `status`：是否成功：true.是、false.否
- `message`：异常信息
- `data`：返回结果集

`data` 主要字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `data[].id` | string | 部门id |
| `data[].code` | string | 部门code |
| `data[].name` | string | 部门名称 |
| `data[].path` | string | 部门中文名路径（如：总公司/研发部/前端组） |

### getJobsNew

获取所有实时的岗位列表

```bash
xrxs-cli payroll getJobsNew
```

> 请求方式：`GET`。无请求体，参数通过 `--<name> <value>` 传递。

返回：

- `code`：状态码
- `status`：是否成功：true.是、false.否
- `message`：异常信息
- `data`：返回结果集

`data` 主要字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `data[].id` | string |  |
| `data[].type` | string |  |
| `data[].label` | string |  |
| `data[].children` | array<object> |  |
| `data[].children[].id` | string |  |
| `data[].children[].type` | string |  |
| `data[].children[].label` | string |  |
| `data[].children[].children` | array<object> |  |
| `data[].children[].fieldType` | integer |  |
| `data[].fieldType` | integer |  |

### exportResult

获取导出活动报表任务的结果

获取导出活动报表任务的结果<br>
备注<br>
导出活动报表

```bash
xrxs-cli payroll exportResult
```

> 请求方式：`POST`。无请求体，参数通过 `--<name> <value>` 传递。

返回：

- `code`：状态码
- `status`：是否成功：true.是、false.否
- `message`：异常信息
- `data`：返回结果集 任务进行中（代表任务还未结束）导出失败（代表导出有异常）  下载链接（导出成功 可以使用链接下载） 没有导出任务（代表无任务） 

### getPayrollArchivesForReport

```bash
xrxs-cli payroll getPayrollArchivesForReport
  --yearmo <yearmo>
```

> 请求方式：`POST`。无请求体，参数通过 `--<name> <value>` 传递。

参数：

| 参数 | 必填 | 类型 | 说明 |
|------|------|------|------|
| `--yearmo` | 否 | string | 年月 |

返回：

- `code`：状态码
- `status`：是否成功：true.是、false.否
- `message`：异常信息
- `data`：返回结果集

`data` 主要字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `data[].name` | string | 报表名字 |
| `data[].type` | integer | 报表类型 1 系统 21上传 |
| `data[].reportId` | string | 全数据的 reportId |
| `data[].summaryReport` | integer | 是否是汇总大表 0否 1是 |

## 注意事项

- 写入/删除操作，执行前必须确认用户意图。
- 预览接口（路径/命令名以 `-preview` 结尾）调用后，xrxs-cli 会返回 `taskId`、`summaryHeaderMap`、`summaryData`、`originalName`、`riskLevel`。必须将其渲染为 `<confirm-card>` 组件，属性为 `taskId`、`summaryHeaderMap`（JSON 字符串）、`summaryData`（JSON 字符串）、`riskLevel`、`taskName`（取 `originalName`），禁止直接展示 JSON。
- 不要将 xrxs-cli 执行的命令返回给用户。


## 参考

- [payroll](../SKILL.md) -- 全部命令
