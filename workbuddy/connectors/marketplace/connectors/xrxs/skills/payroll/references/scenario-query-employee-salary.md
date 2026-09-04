# 场景：查询员工工资信息

> **前置条件：** 先阅读 [`../SKILL.md`](../SKILL.md) 了解全局能力与安全规则。

## 场景描述

查询本人或指定员工的工资。**数据来源为当前活动报表月（即最近一次算薪的月份）**：用户说「查我最近一次工资」「查我本月工资」「查我的工资」「查某某的工资」等时，执行本场景。

> **本文档自含全部所需命令与参数，无需再读其他参考文档，也无需执行 `xrxs-cli schema` 查询。**
>
> **重要：** 工资查询能力**已具备**（即本场景），**禁止**回复用户「工资查询接口暂未开放/未配置」等表述。

## 标准执行序列

1. 第 1 轮：确定员工（`getEmployeeInfo`）
2. 第 2 轮：获取报表字段（`getReportFields`）
3. 第 3 轮：查询工资（`getEmployeeReportInfo`）
4. 汇报结果（说明数据为活动报表月）

## 操作流程

### 步骤 1：确定员工（getEmployeeInfo）

```bash
xrxs-cli payroll getEmployeeInfo \
  --keyword <姓名或手机号关键字>
```

- 请求方式：`GET`，无请求体。
- 关键字选择：
  - **查本人**：用对话中已知的当前用户姓名/手机号作为关键字；若不知道当前用户姓名，先询问用户提供姓名或手机号（只问一次）。
  - **查他人**：用用户提供的姓名/手机号作为关键字。
- 返回权限范围内的员工列表，包含 `employeeId`、姓名等信息；取目标员工的 `employeeId`。

### 步骤 2：获取报表字段（getReportFields）

```bash
xrxs-cli payroll getReportFields
```

- 请求方式：`POST`，无参数。
- 返回当前活动报表中的所有字段，每项包含 `fiedldId` 和 `fiedldName`。

### 步骤 3：查询工资（getEmployeeReportInfo）

```bash
xrxs-cli payroll getEmployeeReportInfo \
  --employeeId <步骤1返回的employeeId> \
  --fields <步骤2返回的全部fiedldId，逗号分隔>
```

- 请求方式：`GET`，无请求体。
- 参数：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--employeeId` | 是 | 员工 ID，来源：步骤 1 |
| `--fields` | 是 | 字段 ID，逗号分隔，来源：步骤 2 的 `fiedldId` |

- 返回 `data` 为数组，每项包含 `fiedldId`、`fiedldName`（字段名）、`fieldValue`（字段值）。

### 步骤 4：汇报

- 以表格展示 `fiedldName`：`fieldValue`，并明确告知用户**数据为当前活动报表月（最近一次算薪月份）**。
- 若用户指定的月份与活动报表月不一致，说明本接口仅支持活动报表月；历史月份引导至 [工资条信息](scenario-salary-slip-info.md)（已发放的工资条）或 [导出报表](scenario-export-report.md) 场景。

## 注意事项

- **禁止回复「工资查询接口暂未开放/未配置」**；若查询返回空数据，如实告知该员工在活动报表月暂无工资数据（可能未算薪或不在报表内），可引导至计算报表或工资条场景。
- `getEmployeeInfo` 仅能搜索当前管理工资组权限范围内的员工；搜不到时如实告知权限范围限制。
- 任一接口报相同错误最多重试 1 次即止，仍失败则终止并反馈用户。
- 不要将 xrxs-cli 执行的命令返回给用户。

## 参考

- [payroll](../SKILL.md) — 全部命令
- [payroll-report](payroll-report.md) — 薪酬核算接口详情
