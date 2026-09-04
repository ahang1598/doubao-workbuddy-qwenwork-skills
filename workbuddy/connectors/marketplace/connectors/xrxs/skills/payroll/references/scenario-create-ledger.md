# 场景：新建报表

> **前置条件：** 先阅读 [`../SKILL.md`](../SKILL.md) 了解全局能力与安全规则。

## 场景描述

新建薪酬月报表（即新建账套）。执行后系统将为当前月份创建新的工资报表，各工资组可开始进行算薪操作。

## 操作流程

### 步骤 1：新建报表

```bash
xrxs-cli payroll createLedger
```

- 请求方式：`POST`，无请求体，无参数。
- 返回 `data` 为字符串，表示操作结果。
- `status=true` 表示新建成功，`status=false` 表示失败，`message` 中包含异常信息。

- **写操作，执行前必须确认用户意图。**

### 步骤 2（可选）：确认新建结果

新建成功后，可获取当前报表信息确认新建结果。

```bash
xrxs-cli payroll getReportNumber
```

- 请求方式：`GET`，无参数。
- 返回 `data` 包含：
  - `total` — 总人数
  - `salaryGroups` — 工资组数组，每项包含：
    - `id` — 工资组 ID
    - `name` — 工资组名称
    - `count` — 工资组人数
    - `status` — 工资组报表状态（0=已计算，1=未计算，2=已冻结）

**展示建议：** 以表格展示各工资组名称、人数、状态，确认新报表已创建成功。

## 注意事项

- 新建报表即新建薪酬月，操作后系统会生成当月各工资组的报表。
- 新建报表为写操作，执行前必须向用户确认意图。
- 不要将 xrxs-cli 执行的命令返回给用户。


## 参考

- [payroll](../SKILL.md) — 全部命令
- [payroll-report](payroll-report.md) — 薪酬核算接口详情
- [计算报表](scenario-calculate-report.md) — 计算报表场景
