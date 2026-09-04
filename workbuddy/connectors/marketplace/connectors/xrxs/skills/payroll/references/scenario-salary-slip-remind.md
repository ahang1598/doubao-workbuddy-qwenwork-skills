# 场景：工资条确认提醒

> **前置条件：** 先阅读 [`../SKILL.md`](../SKILL.md) 了解全局能力与安全规则。

## 场景描述

对已发放的工资条发送确认提醒，通知未确认的员工进行确认。完整流程：获取工资条列表 → 获取可用提醒通道 → 提醒预览 → 发送提醒。

## 操作流程

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

- 返回 `data.result` 数组，每项包含：
  - `id` — 工资发放 ID（`salaryReleaseId`）
  - `name` — 工资条方案名称
  - `yearmo` — 报表月份
  - `showRemindBtn` — 是否显示提醒按钮（`0`=不显示，`1`=显示）
  - `unConfirmNumber` — 未确认人数
  - `confirmNumber` — 确认人数
  - `recipientNumber` — 接收人数

**展示建议：** 仅展示 `showRemindBtn=1` 的工资条，以表格展示名称、月份、未确认人数等。

### 步骤 2：获取可用提醒通道

```bash
xrxs-cli payroll getSalaryBillAckRemindChannel \
  --salaryReleaseId <工资发放ID>
```

- 请求方式：`GET`，无请求体。
- 参数：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--salaryReleaseId` | 是 | 工资发放 ID。来源：步骤 1 的 `result[].id`。 |

- 返回 `data` 为数组，每项包含：
  - `channelId` — 通道 ID
  - `channelName` — 通道名称
  - `channelType` — 通道类型

**展示建议：** 以列表展示可用通道，供用户选择提醒渠道。

通道类型对照：
| channelType | 说明 |
|-------------|------|
| `app` | 薪人薪事员工端 |
| `personEmail` | 在职员工个人邮箱 |
| `workEmail` | 工作邮箱 |
| `dismissionPersonEmail` | 离职员工个人邮箱 |
| `dtalk` | 钉钉 |
| `qywx` | 企业微信 |
| `yzj` | 云之家 |
| `lark` | 飞书 |
| `weaver` | 泛微 |

### 步骤 3：提醒预览

```bash
xrxs-cli payroll sendSalaryBillAckRemindPreview \
  --request-body '{
    "salaryReleaseId": 3981,
    "channelTypes": ["app", "personEmail", "workEmail", "dismissionPersonEmail"]
  }'
```

- 请求方式：`POST`，`Content-Type: application/json`。
- 请求体字段说明：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `salaryReleaseId` | integer | 是 | 工资发放 ID。来源：步骤 1 的 `result[].id`。 |
| `channelTypes` | array | 是 | 渠道类型数组。来源：步骤 2 返回的 `channelType`。 |

- 返回预览数据（cli 预览通用结构），包含：
  - `summaryData` — 概览（工资月份、方案数、提醒员工总数）
  - `detailData` — 详情（各工资条明细及提醒渠道）
  - `summaryHeaderMap` / `detailHeaderMap` — 表头映射

- **预览接口返回的数据必须渲染为 `<confirm-card>` 确认卡片。** 卡片属性：
  - `taskId` — 任务 ID
  - `summaryHeaderMap` — 摘要表头 JSON 字符串
  - `summaryData` — 摘要数据 JSON 字符串
  - `riskLevel` — 风险等级
  - `taskName` — 取 `originalName`

### 步骤 4：发送确认提醒

预览确认后，执行实际发送。

```bash
xrxs-cli payroll sendSalaryBillAckRemind \
  --request-body '{
    "salaryReleaseId": 3981,
    "channelTypes": ["app", "personEmail", "workEmail", "dismissionPersonEmail"]
  }'
```

- 请求方式：`POST`，`Content-Type: application/json`。
- 请求体参数同步骤 3 预览接口。
- 返回发送结果：`status=true` 表示成功。

- **写操作，执行前必须确认用户意图。**

## 注意事项

- 发送前必须先调用预览接口，并将预览结果渲染为确认卡片。
- 仅 `showRemindBtn=1` 的工资条支持发送提醒。
- 可根据企业配置的通道类型选择提醒渠道。
- 写入/删除操作前必须确认用户意图。
- 不要将 xrxs-cli 执行的命令返回给用户。


## 参考

- [payroll](../SKILL.md) — 全部命令
- [payroll-cli](payroll-cli.md) — 工资条 CLI 接口详情
- [工资条信息](scenario-salary-slip-info.md) — 工资条信息场景
