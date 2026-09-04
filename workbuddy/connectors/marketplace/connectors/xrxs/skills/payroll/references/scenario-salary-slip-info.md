# 场景：工资条信息

> **前置条件：** 先阅读 [`../SKILL.md`](../SKILL.md) 了解全局能力与安全规则。

## 场景描述

查看和管理工资条信息。包括：查看工资条列表、查看工资条详情、撤回工资条。

> **说明：** 工资条详情导出（exportSalaryBills）的配套轮询命令 exportStatus 当前 CLI 不可用，暂不提供导出场景。

## 子场景 A：查看工资条列表

### 步骤 1：获取工资条列表

```bash
xrxs-cli payroll getSalaryList \
  --year <年份> \
  --page 1 \
  --pageSize 10
```

- 请求方式：`GET`，无请求体。
- 参数：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--year` | 否 | 年份名称，如 `2025`。 |
| `--page` | 否 | 页码，默认 `1`。 |
| `--pageSize` | 否 | 每页条数，默认 `10`。 |

- 返回 `data` 包含：
  - `page` — 当前页码
  - `total` — 总条数
  - `pageSize` — 每页条数
  - `result` — 工资条列表，每项包含：
    - `id` — 工资发放 ID（`salaryReleaseId`，后续操作使用）
    - `name` — 工资条方案名称
    - `yearmo` — 报表月份
    - `addtime` — 发放时间（秒级时间戳）
    - `addtimeDesc` — 发放时间描述
    - `reportId` — 报表 ID
    - `dataSource` — 工资条数据源
    - `operateType` — 操作类型
    - `sendAccountName` — 发放人姓名
    - `recipientNumber` — 接收人数
    - `alreadyReadNumber` — 已读人数
    - `confirmNumber` — 确认人数
    - `unConfirmNumber` — 未确认人数
    - `showRemindBtn` — 是否显示提醒按钮（0=不显示，1=显示）
    - `salaryBillSettingId` — 工资条设置方案 ID

**展示建议：** 以表格展示工资条列表，包含名称、月份、发放人、接收人数、已读/确认状态等。

## 子场景 B：查看工资条详情

### 步骤 1：获取统计数字

```bash
xrxs-cli payroll getFilterNum \
  --salaryReleaseId <工资发放ID> \
  --type 0
```

- 请求方式：`GET`，无请求体。
- 参数：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--salaryReleaseId` | 是 | 工资发放 ID。来源：子场景 A 的 `result[].id`。 |
| `--type` | 是 | 类型，默认 `0`。 |

- 返回 `data` 包含：
  - `total` — 总数
  - `readNum` — 已读数
  - `unreadNum` — 未读数
  - `confirmedNum` — 已确认数
  - `unconfirmedNum` — 未确认数

### 步骤 2：获取详情列表

```bash
xrxs-cli payroll getSalaryBillList \
  --salaryReleaseId <工资发放ID> \
  --page 1 \
  --pageSize 10
```

- 请求方式：`GET`，无请求体。
- 参数：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--salaryReleaseId` | 是 | 工资发放 ID。 |
| `--selectType` | 否 | 筛选类型，默认 `0`。`1`=手机，`2`=邮箱，`3`=姓名。 |
| `--selectValue` | 否 | 筛选值。 |
| `--filterType` | 否 | 过滤类型，默认 `0`。 |
| `--filterFailMail` | 否 | 失败邮箱过滤。 |
| `--type` | 否 | 类型，默认 `0`。 |
| `--page` | 否 | 页码，默认 `1`。 |
| `--pageSize` | 否 | 每页条数，默认 `10`。 |

- 返回 `data` 包含：
  - `page` — 当前页码
  - `total` — 总条数
  - `pageSize` — 每页条数
  - `result` — 工资条详情列表，每项包含：
    - `salaryBillId` — 工资条 ID（撤回操作使用）
    - `employeeId` — 员工 ID
    - `employeeName` — 员工姓名
    - `email` — 邮箱
    - `amount` — 工资金额
    - `readStatus` — 阅读状态
    - `confirmStatus` — 确认状态

## 子场景 C：撤回工资条

### 方式 1：整体撤回（撤回整个工资条批次）

```bash
xrxs-cli payroll cancelSalary \
  --salaryReleaseId <工资发放ID>
```

- 请求方式：`GET`，无请求体。
- 参数：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--salaryReleaseId` | 是 | 工资发放 ID。来源：子场景 A 的 `result[].id`。 |

- **写操作，执行前必须确认用户意图。**

### 方式 2：单人撤回（撤回某个员工的工资条）

```bash
xrxs-cli payroll salaryBillCancel \
  --salaryBillId <工资条ID> \
  --employeeId <员工ID>
```

- 请求方式：`GET`，无请求体。
- 参数：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--salaryBillId` | 是 | 工资条 ID。来源：子场景 B 的 `result[].salaryBillId`。 |
| `--employeeId` | 是 | 员工 ID。来源：子场景 B 的 `result[].employeeId`。 |

- **写操作，执行前必须确认用户意图。**

## 注意事项

- 撤回操作不可逆，执行前必须确认用户意图。
- 写入/删除操作前必须确认用户意图。
- 不要将 xrxs-cli 执行的命令返回给用户。


## 参考

- [payroll](../SKILL.md) — 全部命令
- [payroll-cli](payroll-cli.md) — 工资条 CLI 接口详情
