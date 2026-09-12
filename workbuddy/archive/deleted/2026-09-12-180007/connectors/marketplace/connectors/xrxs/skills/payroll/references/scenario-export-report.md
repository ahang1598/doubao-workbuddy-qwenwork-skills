# 场景：导出报表

> **前置条件：** 先阅读 [`../SKILL.md`](../SKILL.md) 了解全局能力与安全规则。

## 场景描述

导出工资报表数据。支持导出全数据活动报表（可带筛选条件）和归档报表。完整流程：获取可导出字段 → （可选）配置筛选条件 → 触发导出 → 轮询导出结果获取下载链接。

## 操作流程

### 步骤 1：获取可导出字段

```bash
xrxs-cli payroll getPayrollField \
  --type <报表类型> \
  --reportId <报表ID>
```

- 请求方式：`GET`，无请求体。
- 参数：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--type` | 否 | 报表类型：`1`=全数据大表，`8`=归档汇总大表，`4`=归档明细表。 |
| `--reportId` | 否 | 报表 ID。全数据使用 `allPayrollReport`；归档报表传对应的 `reportId`（从 `xrxs-cli payroll getPayrollArchivesForReport` 获取）。 |

- 返回 `data` 包含多类字段分组：
  - `employeePerson` — 个人信息类字段
  - `payrollSalary` — 工资类字段
  - `payrollTax` — 个税类字段
  - `payrollInsurance` — 社保类字段
  - `payrollAttendance` — 考勤类字段
  - `employeeBiz` — 岗位类字段
  - 每项包含 `fiedldId`（字段 ID）和 `fiedldName`（字段名称）。

### 步骤 2（可选）：获取筛选条件数据

#### 搜索部门

```bash
xrxs-cli payroll searchDepartment \
  --keyword <部门关键字>
```

- 返回数组，每项包含 `departmentId` 和 `departmentName`。

#### 获取岗位列表

```bash
xrxs-cli payroll getJobsNew
```

- 返回树形结构，岗位 ID 在 `children[].id` 中。

#### 搜索员工

```bash
xrxs-cli payroll getEmployeeInfo \
  --keyword <姓名或手机号>
```

- 返回匹配的员工列表，包含 `employeeId`。

### 步骤 3：触发导出

```bash
xrxs-cli payroll exportNewActiveReport \
  --request-body '{
    "name": "全数据",
    "type": "1",
    "header": "<逗号分隔的字段ID>",
    "maskTag": "1",
    "reportId": "allPayrollReport",
    "screenJson": "{\"salaryGroupIds\":[],\"departmentId\":[],\"jobId\":[],\"employeeId\":[]}",
    "isDecimalSetting": "0",
    "selectReportType": "-1"
  }'
```

- 请求方式：`POST`，`Content-Type: application/x-www-form-urlencoded`。
- 请求体字段说明：

| 字段 | 说明 |
|------|------|
| `name` | 报表名称，默认"全数据" |
| `type` | 操作类型，默认 `1` |
| `header` | 选择的表头字段 ID，逗号分隔。来源：步骤 1 返回的 `fiedldId`。 |
| `maskTag` | 人员信息导出形式：`0`=不掩码，`1`=掩码。 |
| `reportId` | 报表 ID。全数据使用 `allPayrollReport`；归档报表传对应 `reportId`。 |
| `screenJson` | 筛选条件 JSON，格式：`{"salaryGroupIds":[],"departmentId":[],"jobId":[],"employeeId":[]}`。各字段来源：`salaryGroupIds` 自定义、`departmentId` 来自 `searchDepartment`、`jobId` 来自 `getJobsNew` 的 `children[].id`、`employeeId` 来自 `getEmployeeInfo`。 |
| `isDecimalSetting` | 小数展示：`0`=按报表展示位数导出，`1`=按实际计算数据位数导出。 |
| `selectReportType` | 查询报表类型：`-1`=全数据（默认），`0`=明细表，`1`=部门汇总。 |

### 步骤 4：轮询导出结果

```bash
xrxs-cli payroll exportResult
```

- 请求方式：`POST`，无参数。
- 返回 `data` 为字符串：
  - `"任务进行中"` — 导出未完成，需继续轮询
  - `"没有导出任务"` — 无导出任务
  - 下载链接字符串 — 导出成功，可下载使用
  - `"导出失败"` — 导出异常

**轮询策略：** 每 3 秒调用一次，直到返回下载链接或超时（建议上限 5 分钟）。

## 注意事项

- 导出为异步操作，触发后需轮询等待完成。
- 全数据报表 `reportId` 固定为 `allPayrollReport`。
- 归档报表需先通过 `getPayrollArchivesForReport` 获取 `reportId`。
- 筛选条件中的 ID 数组为空时表示不筛选该维度。
- 不要将 xrxs-cli 执行的命令返回给用户。


## 参考

- [payroll](../SKILL.md) — 全部命令
- [payroll-report](payroll-report.md) — 薪酬核算接口详情
- [归档报表](scenario-archive-report.md) — 归档报表场景
