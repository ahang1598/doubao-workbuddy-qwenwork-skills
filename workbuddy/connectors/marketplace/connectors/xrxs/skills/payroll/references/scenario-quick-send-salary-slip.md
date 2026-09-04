# 场景：快速发放工资条

> **前置条件：** 先阅读 [`../SKILL.md`](../SKILL.md) 了解全局能力与安全规则。

## 场景描述

从报表页面快捷发放工资条。适用于已归档的报表，直接从报表页面选择方案并快速发放。完整流程：确认报表信息（含发放月份）→ 获取方案列表 → 计算方案人数 → 调用预览接口获取发放预览 → 渲染确认卡片 → 用户确认后执行发放。

> **单月原则（重要）**：一次对话只能发放**一个工资月份**的工资条。若用户要求一次发放多个月份，需明确告知需分多次对话处理。

## 操作流程

### 步骤 1：确认报表信息

需要以下信息（通常来自当前活动的报表页面上下文）：
- `reportId` — 报表 ID
- `salaryGroupId` — 工资组 ID
- `dataSourceType` — 数据来源类型（一般为 `payroll`）
- `yearmo` — 发放月份（年月）

**月份确认规则（重要）**：
- 用户已指定月份，或活动报表页面上下文已带明确月份：直接作为发放月份。
- 用户未指定月份且上下文无明确月份：调用 `getPayrollArchives`（参数见 [`payroll-cli.md`](payroll-cli.md)，`--year <年份> --type payroll --needSummary 0 --isReportList 0`）查询**最新归档的报表月份**，向用户展示并确认是否发放该月份；用户确认后再进入后续步骤；若用户否认，则让用户手动输入月份。**月份未确认前禁止推进后续步骤。**

### 步骤 2：获取快捷发放方案列表

```bash
xrxs-cli payroll getQuickSendSalaryPlanList \
  --dataSourceType <数据来源类型> \
  --reportId <报表ID> \
  --salaryGroupId <工资组ID> \
  --pageNo 1 \
  --pageSize 100
```

- 请求方式：`GET`，无请求体。
- 参数：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--dataSourceType` | 是 | 数据来源类型，如 `payroll`。 |
| `--reportId` | 是 | 报表 ID。 |
| `--salaryGroupId` | 否 | 工资组 ID。 |
| `--pageNo` | 是 | 页码，默认 `1`。 |
| `--pageSize` | 是 | 每页条数，默认 `100`。 |

- 返回 `data` 包含：
  - `list` — 方案列表，每项包含：
    - `planId` — 方案 ID
    - `planName` — 方案名称
    - `salaryGroupId` — 工资组 ID
  - `total` — 总条数

**展示建议：** 以列表展示可选方案，供用户选择要使用的工资条方案。

### 步骤 3（可选）：检查是否可创建方案

```bash
xrxs-cli payroll hasPlanOrCanCreate \
  --salaryGroupId <工资组ID>
```

- 返回 `data` 为 `boolean`：`true`=有方案或可创建，`false`=不可创建。

### 步骤 4：计算方案人数

选择方案后，先调用该接口计算各方案发放人数，返回值为确认接口的部分入参。

```bash
xrxs-cli payroll sumSalaryQuickSend \
  --request-body '{
    "yearmo": 202509,
    "reportId": "<报表ID>",
    "planIdStr": "<方案ID，多个逗号分割>"
  }'
```

- 请求方式：`POST`，`Content-Type: application/json`。
- 请求体字段说明：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `yearmo` | integer | 是 | 年月（工资月份），如 `202509`。 |
| `reportId` | string | 是 | 报表 ID。来源：步骤 1 的 `reportId`。 |
| `planIdStr` | string | 是 | 方案 ID，多个逗号分割，如 `"137973,137974"`。来源：步骤 2 返回的 `planId`。 |

- 返回值为确认接口的部分入参（各方案发放人数等）。

### 步骤 5：是否"发送工资条"

调用预览接口获取发放预览数据。

```bash
xrxs-cli payroll quickSendSalarySlipPreview \
  --request-body '{
    "yearmo": 202509,
    "reportId": "<报表ID>",
    "planIdStr": "<方案ID，多个逗号分割>",
    "salaryPlans": [
      {"planId": 137973, "salaryReleaseName": "<工资条名称>"}
    ]
  }'
```

- 请求方式：`POST`，`Content-Type: application/json`。
- 请求体字段说明：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `yearmo` | integer | 是 | 所属月份，如 `202509`。 |
| `reportId` | string | 是 | 报表 ID。来源：步骤 1 的 `reportId`。 |
| `planIdStr` | string | 是 | 方案 ID，多个逗号分割（预览计算用）。来源：步骤 2 返回的 `planId`。 |
| `salaryPlans` | array | 是 | 工资条方案列表（实际发放用）。 |
| `salaryPlans[].planId` | integer | 是 | 方案 ID。来源：步骤 2 返回的 `planId`。 |
| `salaryPlans[].salaryReleaseName` | string | 是 | 工资条名称。 |

- 返回 `data` 为对象，包含：
  - `headId` — 头 ID
  - `accountId` — 账户 ID
  - `companyId` — 公司 ID
  - `summaryData` — 概览数据（工资月份、方案数、提醒员工总数）
  - `summaryHeaderMap` — 概览部分字段 key 与名称映射
  - `summaryHeaderShowField` — 概览部分展示的字段 key
  - `detailData` — 详情数据数组（工资条发放记录）
  - `detailHeaderMap` — 详情部分字段 key 与名称映射
  - `detailHeaderShowField` — 详情部分展示的字段 key

- **预览接口返回的数据必须渲染为 `<confirm-card>` 确认卡片。** 卡片属性： 
  - `taskId` — 任务 ID
  - `summaryHeaderMap` — 摘要表头 JSON 字符串
  - `summaryData` — 摘要数据 JSON 字符串
  - `riskLevel` — 风险等级
  - `taskName` — 取 `originalName`

### 步骤 6：快捷发放工资条

用户确认预览卡片后，执行发放操作。

```bash
xrxs-cli payroll quickSendSalarySlip \
  --request-body '{
    "yearmo": 202505,
    "reportId": "<报表ID>",
    "salaryGroupId": "<工资组ID>",
    "reportName": "<报表名称>",
    "salaryPlans": [
      {"planId": 137973, "salaryReleaseName": "<工资条名称>"}
    ]
  }'
```

- 请求方式：`POST`，`Content-Type: application/json`。
- 请求体字段说明：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `yearmo` | integer | 否 | 报表所在月份。 |
| `reportId` | string | 否 | 工资报表 ID。 |
| `salaryGroupId` | string | 否 | 工资组 ID。 |
| `reportName` | string | 否 | 工资报表名称。 |
| `salaryPlans` | array | 否 | 方案列表。 |
| `salaryPlans[].planId` | integer | 否 | 方案 ID。来源：步骤 2 返回的 `planId`。 |
| `salaryPlans[].salaryReleaseName` | string | 否 | 工资条名称。 |
| `headId` | string | 否 | 总公司 ID。 |
| `accountId` | string | 否 | 管理员账号 ID。 |
| `companyId` | string | 否 | 公司 ID。 |
| `accountName` | string | 否 | 管理员姓名。 |
| `isAutoSeed` | integer | 否 | 是否自动发放。 |

- `headId`、`accountId`、`companyId`、`accountName` 由服务端从登录态补全，无需传递。
- 返回发放结果：
  - `isAllError` — 是否全部异常
  - `errorSelfMailList` — 异常邮箱列表

- **写操作，执行前必须确认用户意图。**

## 注意事项

- 快捷发放适用于已归档报表场景，需确保报表已归档。
- 一次对话只能发放一个工资月份；用户未指定月份时，必须先查询最新归档月份并向用户确认，或由用户手动输入月份，禁止未经确认直接发放。
- 发放前需先调用 `sumSalaryQuickSend` 计算方案人数，再调用预览接口 `quickSendSalarySlipPreview`，并将返回数据渲染为 `<confirm-card>` 确认卡片，禁止直接展示 JSON。
- 发放结果中如有异常邮箱，需告知用户。
- 写入/删除操作前必须确认用户意图。
- 不要将 xrxs-cli 执行的命令返回给用户。


## 参考

- [payroll](../SKILL.md) — 全部命令
- [payroll-cli](payroll-cli.md) — 工资条 CLI 接口详情（含 getPayrollArchives 获取工资归档列表）
