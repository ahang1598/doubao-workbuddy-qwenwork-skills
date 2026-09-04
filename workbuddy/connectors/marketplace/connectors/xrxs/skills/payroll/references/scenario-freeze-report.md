# 场景：冻结/解冻报表

> **前置条件：** 先阅读 [`../SKILL.md`](../SKILL.md) 了解全局能力与安全规则。

## 场景描述

冻结或解冻已归档的工资组报表。完整流程：获取冻结/解冻弹窗的工资组列表 → 选择工资组 → 调用对应预览接口获取弹窗数据 → 渲染确认卡片 → 用户确认后执行冻结/解冻操作。

## 操作流程

### 步骤 1：获取冻结/解冻弹窗的工资组列表

```bash
xrxs-cli payroll frozenSalaryGroupList \
  --popType <1|0>
```

- 请求方式：`GET`，无请求体。
- 参数：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--popType` | 否 | 弹窗状态：`1`=冻结弹窗，`0`=解冻弹窗。 |

- 返回 `data` 为数组，每项包含：
  - `salaryGroupId` — 工资组 ID（后续预览与操作步骤使用）
  - `salaryGroupName` — 工资组名称
  - `status` — 状态（1=未归档，2=已归档，3=已冻结）
  - `lastArchiveTime` — 上次归档时间
  - `archiveEmployeeCount` — 当前算薪归档人数

**展示建议：** 以表格形式展示工资组名称、状态、归档人数、上次归档时间，供用户选择需要冻结/解冻的工资组。

### 步骤 2a：冻结预览（是否“确认冻结报表”）

用户选定工资组后，调用冻结预览接口获取冻结弹窗数据。

```bash
xrxs-cli payroll frozenReportPreview \
  --salaryGroupIds <逗号分隔的工资组ID>
```

- 请求方式：`GET`，无请求体。
- 参数：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--salaryGroupIds` | 否 | 工资组 ID，逗号分隔。来源：步骤 1 返回的 `salaryGroupId`。 |

- 返回 `data` 为对象（cli 预览通用结构），包含：
  - `headId` — 头 ID
  - `accountId` — 账户 ID
  - `companyId` — 公司 ID
  - `summaryData` — 概览数据
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

### 步骤 2b：解冻预览（是否“确认解冻报表”）

用户选定工资组后，调用解冻预览接口获取解冻弹窗数据。

```bash
xrxs-cli payroll unfreezeReportPreview \
  --salaryGroupIds <逗号分隔的工资组ID>
```

- 请求方式：`GET`，无请求体。
- 参数：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--salaryGroupIds` | 否 | 工资组 ID，逗号分隔。来源：步骤 1（`popType=0`）返回的 `salaryGroupId`。 |

- 返回 `data` 为对象（cli 预览通用结构），字段同步骤 2a。
- **预览接口返回的数据必须渲染为 `<confirm-card>` 确认卡片。** 卡片属性同步骤 2a。

### 步骤 3a：冻结报表

用户确认冻结预览卡片后，执行冻结操作。

```bash
xrxs-cli payroll freezeReport \
  --salaryGroupIds <逗号分隔的工资组ID>
```

- 请求方式：`GET`，无请求体。
- 参数：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--salaryGroupIds` | 否 | 工资组 ID，逗号分隔。来源：步骤 1 返回的 `salaryGroupId`。 |

- 返回 `status=true` 表示冻结成功。
- **写操作，执行前必须确认用户意图。**

### 步骤 3b：解冻报表

用户确认解冻预览卡片后，执行解冻操作。

```bash
xrxs-cli payroll unfreezeReport \
  --salaryGroupIds <逗号分隔的工资组ID>
```

- 请求方式：`GET`，无请求体。
- 参数：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--salaryGroupIds` | 否 | 工资组 ID，逗号分隔。来源：步骤 1（`popType=0`）返回的 `salaryGroupId`。 |

- 返回 `status=true` 表示解冻成功。
- **写操作，执行前必须确认用户意图。**

## 注意事项

- 必须先调用 `frozenSalaryGroupList` 获取工资组列表，再调用对应预览接口（冻结用 `frozenReportPreview`，解冻用 `unfreezeReportPreview`），并将预览返回数据渲染为 `<confirm-card>` 确认卡片，禁止直接展示 JSON。
- 预览与执行接口的 `salaryGroupIds` 均来源于 `frozenSalaryGroupList` 返回的 `salaryGroupId`。
- 冻结操作仅对已归档的工资组有效。
- 解冻后工资组可重新进行计算和归档。
- 写入/删除操作前必须确认用户意图。
- 不要将 xrxs-cli 执行的命令返回给用户。


## 参考

- [payroll](../SKILL.md) — 全部命令
- [payroll-report](payroll-report.md) — 薪酬核算接口详情
