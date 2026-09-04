# 场景：归档报表

> **前置条件：** 先阅读 [`../SKILL.md`](../SKILL.md) 了解全局能力与安全规则。

## 场景描述

归档当月工资报表。完整流程：获取当前报表中可归档的工资组列表及人数 → 调用预览接口获取归档预览数据 → 渲染确认卡片 → 用户确认后执行归档。

> **本文档自含全部所需命令与参数，无需再读其他参考文档，也无需执行 `xrxs-cli schema` 查询。**

### 标准执行序列（按此执行，可并行的合并到同一轮）

1. 第 1 轮（并行）：`permission check payroll-archiveReport` + `getReportNumber`
2. 第 2 轮：`archiveReportPreview --salaryGroupIds <全部待归档的ID，逗号分隔>`（**salaryGroupIds 必传，否则 400 报错**；多个工资组合并一次调用）→ 渲染 `<confirm-card>` 等用户确认
3. 第 3 轮：用户确认后 `archiveReport --salaryGroupIds <同上>`
4. 归档完成后**直接汇报结果**（工资组、归档结果、期间、人数、失败原因用表格），不要额外调用其他接口复核

## 操作流程

### 步骤 1：获取当前报表中可归档的工资组列表

```bash
xrxs-cli payroll getReportNumber
```

- 请求方式：`GET`，无参数。
- 返回 `data` 包含：
  - `total` — 总人数
  - `salaryGroups` — 工资组数组，每项包含：
    - `id` — 工资组 ID（后续归档使用）
    - `name` — 工资组名称
    - `count` — 工资组人数
    - `status` — 工资组报表状态（0=已计算，1=未计算，2=已冻结）
  - `payrollUnsetSum` — 未定薪人数
  - `insuranceNoDataSum` — 社保无数据人数
  - `attendanceNoDataSum` — 考勤无数据人数
  - `unusualAutoAdjustmentSum` — 转正自动调薪异常人数
  - `calculateBasePayTypeFile` — 计薪标准为 0 的员工文件下载地址

**展示建议：** 以表格展示各工资组名称、人数、状态，同时汇总展示异常数据（未定薪、社保无数据、考勤无数据等），供用户确认是否继续归档。

### 步骤 2：是否“确认归档报表”

选择工资组后，调用预览接口获取归档预览数据。

```bash
xrxs-cli payroll archiveReportPreview \
  --salaryGroupIds <逗号分隔的工资组ID>
```

- 请求方式：`GET`，无请求体。
- 参数：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--salaryGroupIds` | **是** | 工资组 ID，逗号分隔。来源：步骤 1 返回的 `salaryGroups[].id`。**不传会返回 400（Required parameter 'salaryGroupIds' is not present）**。 |

- 返回 `data` 为对象，包含：
  - `headId` — 头 ID
  - `accountId` — 账户 ID
  - `companyId` — 公司 ID
  - `summaryData` — 概览数据·     
  - `summaryHeaderMap` — 概览部分字段 key 与名称映射
  - `summaryHeaderShowField` — 概览部分展示的字段 key
  - `detailData` — 详情数据数组
  - `detailHeaderMap` — 详情部分字段 key 与名称映射
  - `detailHeaderShowField` — 详情部分展示的字段 key

- **预览接口返回的数据必须渲染为 `<confirm-card>` 确认卡片。** 卡片属性： 
  - `taskId` — 任务 ID
  - `summaryHeaderMap` — 摘要表头 JSON 字符串
  - `summaryData` — 摘要数据 JSON 字符串
  - `riskLevel` — 风险等级
  - `taskName` — 取 `originalName`

### 步骤 3：执行归档

用户确认预览卡片后，执行归档操作。

```bash
xrxs-cli payroll archiveReport \
  --salaryGroupIds <逗号分隔的工资组ID>
```

- 请求方式：`POST`，无请求体。
- 参数：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--salaryGroupIds` | 否 | 工资组 ID，逗号分隔。来源：步骤 1 返回的 `salaryGroups[].id`。 |

- 返回 `data` 包含归档结果详情：
  - `yearmo` — 归档年月
  - `successNum` — 成功人数
  - `failNum` — 失败人数
  - `reportIds` — 归档报表 ID 列表
  - `lastArchiveId` — 最后一个归档 ID
  - `beingAuditedSalaryGroups` — 正在审核的工资组
  - `reportEmptyDataSalaryGroups` — 报表无数据的工资组
  - `needTaxCalculationAgainSalaryGroups` — 个税数据与最后一次算税不一致的工资组
  - `taxCalculateDataDifferenceSalaryGroups` — 归档数据与已申报个税数据不一致的工资组

- **写操作，执行前必须确认用户意图。**

### 步骤 4（可选，仅用户明确要求时执行）：查看归档报表列表

归档完成后如需查看归档报表才调用，默认不执行。

```bash
xrxs-cli payroll getPayrollArchivesForReport \
  --yearmo <年月>
```

- 请求方式：`POST`，无请求体。
- 参数：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--yearmo` | 否 | 年月，如 `202505`。 |

- 返回 `data` 为数组，每项包含：
  - `name` — 报表名称
  - `type` — 报表类型（1=系统，21=上传）
  - `reportId` — 报表 ID（可用于导出）
  - `summaryReport` — 是否汇总大表（0=否，1=是）

## 注意事项

- 归档前必须先调用预览接口 `archiveReportPreview`（**必传 `--salaryGroupIds`**），并将返回数据渲染为 `<confirm-card>` 确认卡片，禁止直接展示 JSON。
- 多个工资组必须合并进同一次预览/归档调用，禁止逐个循环。
- 归档完成后直接汇报结果（表格形式，保持简洁），不要额外复核。
- 归档前建议先完成报表计算（参见 [计算报表](scenario-calculate-report.md)）。
- 未计算的工资组（`status=1`）不建议归档。
- 已冻结的工资组（`status=2`）不可归档。
- 归档结果中如有异常数据（算税不一致等），需告知用户。
- 写入/删除操作前必须确认用户意图。
- 不要将 xrxs-cli 执行的命令返回给用户。


## 参考

- [payroll](../SKILL.md) — 全部命令
- [计算报表](scenario-calculate-report.md) — 计算报表场景
