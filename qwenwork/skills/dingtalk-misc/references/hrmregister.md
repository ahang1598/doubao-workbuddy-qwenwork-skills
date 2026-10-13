# 人事员工数据 (hrm) 命令参考

`dws hrm` 提供薪酬、绩效数据源与员工记录的三个只读命令。当前命令范围不包含入职、转正、调岗、离职办理及花名册查询或修改。

## 路由与查询顺序

- 查询薪资主数据、工资条、人力成本，或指定人事 MCP 数据源的绩效记录，使用本产品。组织大脑的档案绩效模块、人才池、职业历程仍使用 `dws hrbrain`；不要将两种来源的结果混为同一份记录。
- 按姓名找人时先通过 AI 搜问唯一定位员工，再使用返回的组织内 `userId`。
- 薪酬、绩效先查询对应类型的数据源，再使用返回的 `sourceId` 查询目标员工。`sourceId` 与 `sourceType/entityCode` 必须匹配；CLI 不会额外查询数据源来验证匹配关系。
- 普通通讯录详情、部门、角色仍使用 `dws contact`。

## 命令与接口

| CLI 命令 | MCP 接口 | 用途 |
|---|---|---|
| `dws hrm data-sources` | `list_employee_data_sources` | 查询指定类别的可访问数据源 |
| `dws hrm salary` | `query_employee_salary_data` | 查询指定员工的薪资主数据、工资条或人力成本 |
| `dws hrm performance` | `query_performance_records` | 查询指定员工的绩效记录 |

命令、参数与安全声明以当前二进制的叶子 Help 和 Schema 为准。确需核对参数时读取精确叶子，例如：

```bash
dws hrm salary --help
dws schema --cli-path "hrm salary" --compact --format json
```

## 数据源

`dws hrm data-sources` 必须指定 `--source-type` 与 `--entity-code`，允许的组合为：

| `--source-type` | `--entity-code` | 查询内容 |
|---|---|---|
| `SALARY` | `base` | 薪资主数据源 |
| `SALARY` | `payslip` | 工资条数据源 |
| `SALARY` | `laborCost` | 人力成本数据源 |
| `PERFORMANCE` | `base` | 绩效数据源 |

```bash
dws hrm data-sources --source-type SALARY --entity-code laborCost --format json
dws hrm data-sources --source-type PERFORMANCE --entity-code base --format json
```

数据源可见或 `hasData=true` 只说明来源层面的状态，不证明目标员工有数据。

## 薪酬与绩效

| 参数 | `hrm salary` | `hrm performance` |
|---|---|---|
| `--source-id` | 必填，来自对应薪酬类型的数据源查询 | 必填，来自绩效数据源查询 |
| `--user-ids` | 必填，逗号分隔的员工 `userId`，去重后 1–100 个 | 同左 |
| `--entity-code` | 必填，`base`、`payslip` 或 `laborCost` | 不提供此参数 |
| `--salary-months` | 仅 `laborCost` 支持，逗号分隔的 `YYYY-MM` 月份 | 不提供此参数 |
| `--effect-start-date`、`--effect-end-date` | 仅 `base` 支持，必须成对提供，格式 `YYYY-MM-DD`，开始不晚于结束 | 不提供此参数 |
| `--offset` | 非负偏移量，默认 `0` | 同左 |
| `--size` | 每页 `1–100` 条，默认 `20` | 同左 |

`payslip` 和绩效查询目前没有日期筛选参数；不要把月份或日期拼入未知参数。单次命令只请求一页，不会自动拉取全部记录。

下列示例中的数据源、员工 ID 必须替换为前序查询返回的真实值：

```bash
dws hrm salary --source-id "SOURCE_ID_FROM_LIST" --user-ids "RESOLVED_USER_ID" --entity-code laborCost --salary-months 2026-08 --offset 0 --size 20 --format json
dws hrm performance --source-id "PERFORMANCE_SOURCE_ID_FROM_LIST" --user-ids "RESOLVED_USER_ID" --offset 0 --size 20 --format json
```

## 结果与分页

所有命令使用 `--format json`。框架输出统一结果，`data.response` 保留服务端业务 JSON。当前三个接口均未提供 `outputSchema`，CLI 不推测员工明细字段、总数或分页结束标志。

- `records=[]` 表示本次请求没有返回记录，不表示工资为零、绩效为零或全组织没有数据。
- 分页依据服务端实际返回的记录和分页信息继续；没有完整性证据时，不把当前页描述为“全部”。
- 组合薪酬和绩效时分别呈现已返回事实，缺失侧标记“未返回”；不能把缺失值补零后形成联合结论。
- 权限拒绝、参数错误、服务异常与成功空结果分别处理，保留服务端错误码和 Trace 便于排查。

## 接入与本地预览

三个命令绑定内置的 `hrmregister`（智能人事）MCP 服务，使用当前 DWS 登录身份。先通过 `dws auth login` 登录，再按授权范围查询；无需配置额外的私有 MCP 插件。

所有命令支持 `--dry-run`，只做本地参数校验及请求组装，不访问远端，不验证真实权限、员工数据或身份注入。例如：

```bash
dws hrm salary --source-id "SOURCE_ID_FROM_LIST" --user-ids "RESOLVED_USER_ID" --entity-code base --effect-start-date 2026-08-01 --effect-end-date 2026-08-31 --dry-run --format json
```

预览结果包含目标工具、请求参数与 `executed=false`。本地预览、模拟测试、Schema 检查通过，不能代替选定数据源与员工范围后的真实业务查询验收。
