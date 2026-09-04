# 场景：计算报表

> **前置条件：** 先阅读 [`../SKILL.md`](../SKILL.md) 了解全局能力与安全规则。

## 场景描述

计算当月工资报表数据。完整流程：获取可计算工资组 → 选择工资组 → 触发计算 → 轮询计算结果 → （可选）查看异常标签 → （可选）查看员工报表字段。

> **本文档自含全部所需命令与参数，无需再读其他参考文档，也无需执行 `xrxs-cli schema` 查询。**

### 标准执行序列（按此执行，可并行的合并到同一轮）

1. 第 1 轮（并行）：`permission check payroll-calculateActiveReportData` + `getReportCalculateSalaryGroupList`
2. 第 2 轮：`calculateActiveReportData --salaryGroupIds <全部选中的ID，逗号分隔>`（多个工资组合并一次调用）
3. 第 3 轮：轮询 `getCalcResult`（每 3 秒一次，直到 `data=true`）
4. `getCalcResult` 返回 `true` 即计算完成，**直接向用户汇报结果，不要额外再调命令复核**；仅当用户明确要求查看异常或员工明细时，才执行步骤 4-6 的可选命令。

## 操作流程

### 步骤 1：获取可计算的工资组列表

```bash
xrxs-cli payroll getReportCalculateSalaryGroupList
```

- 请求方式：`GET`，无请求体。
- 返回 `data` 为数组，每项包含：
  - `salaryGroupId` — 工资组 ID（后续步骤使用）
  - `salaryGroupName` — 工资组名称
  - `employeeCount` — 工资组人数
  - `frozenStatus` — 冻结状态（0=未冻结，1=已冻结）
  - `lastCalculateTime` — 最后计算时间

**展示建议：** 以表格形式展示工资组名称、人数、冻结状态、上次计算时间，供用户选择需要计算的工资组。

### 步骤 2：计算活动报表

```bash
xrxs-cli payroll calculateActiveReportData \
  --salaryGroupIds <逗号分隔的工资组ID>
```

- 请求方式：`GET`，无请求体。
- 参数：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--salaryGroupIds` | 否 | 需要计算的工资组 ID，逗号分隔。来源：步骤 1 返回的 `salaryGroupId`。不传则计算全部。 |

- 返回 `status=true` 表示触发成功。

### 步骤 3：轮询计算结果

```bash
xrxs-cli payroll getCalcResult
```

- 请求方式：`POST`，无参数。
- 返回 `data` 为 `boolean`：
  - `false` — 计算中，需继续轮询（建议间隔 3~5 秒）
  - `true` — 计算完成

**轮询策略：** 每 3 秒调用一次，直到 `data=true` 或超时（建议上限 5 分钟）。`data=true` 即计算完成，直接汇报结果即可，无需再调用其他接口复核状态。

### 步骤 4-6（可选，仅用户明确要求时执行）：查看异常与明细

以下命令默认不执行；仅当用户明确要求查看异常标签或员工报表字段时才调用。

### 步骤 4（可选）：获取报表异常标签

计算完成后，查看报表是否有异常数据。

```bash
xrxs-cli payroll getReportTag
```

- 请求方式：`POST`，无参数。
- 返回异常标签信息。

### 步骤 5（可选）：获取报表字段列表

```bash
xrxs-cli payroll getReportFields
```

- 请求方式：`POST`，无参数。
- 返回当前活动报表中的所有字段，每项包含 `fiedldId` 和 `fiedldName`。

### 步骤 6（可选）：查询指定员工的报表字段值

```bash
xrxs-cli payroll getEmployeeReportInfo \
  --employeeId <员工ID> \
  --fields <逗号分隔的字段ID>
```

- 请求方式：`GET`，无请求体。
- 参数：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--employeeId` | 否 | 员工 ID。可通过 `xrxs-cli payroll getEmployeeInfo --keyword <关键字>` 按姓名/手机号搜索获取。 |
| `--fields` | 否 | 字段 ID，逗号分隔。来源：步骤 5 返回的 `fiedldId`。 |

### 辅助命令：搜索员工

```bash
xrxs-cli payroll getEmployeeInfo \
  --keyword <姓名或手机号关键字>
```

- 请求方式：`GET`，无请求体。
- 返回匹配的员工列表，包含 `employeeId`、姓名等信息。

## 注意事项

- 计算报表为异步操作，触发后需轮询等待完成。
- 多个工资组必须合并进同一次 `calculateActiveReportData` 调用，禁止逐个循环。
- `getCalcResult` 返回 `true` 后直接汇报结果，不要额外复核；可选步骤 4-6 仅在用户明确要求时执行。
- 汇报结果保持简洁（工资组、状态、人数用表格），避免冗长描述。
- 已冻结的工资组（`frozenStatus=1`）不可计算，需先解冻。
- 写入/删除操作前必须确认用户意图。
- 不要将 xrxs-cli 执行的命令返回给用户。


## 参考

- [payroll](../SKILL.md) — 全部命令
- [payroll-report](payroll-report.md) — 薪酬核算接口详情
