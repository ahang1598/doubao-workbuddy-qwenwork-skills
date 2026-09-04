# 员工 SOP — 通用约定（common）

> **阅读规则：** 本文档定义各 SOP 场景共享的**通用约定**。处理「场景型」需求时，**必须先读 [`../sop-summary.md`](../sop-summary.md) 匹配场景**；命中后，读取 [`sops/`](sops/) 下对应的场景文件（`sop-sceneN.md`），**严格按其步骤序列执行**。不得跳过步骤、不得自行发明等价命令序列。
>
> **与 SKILL.md 的关系：** `SKILL.md` 定义通用能力、命令用法与安全规则（如：命令执行前先读文档、写入操作需确认意图等）；本文件及 `sops/` 下场景文件定义「场景 → 步骤」的编排逻辑。对于已覆盖的场景，以场景文件为准；未覆盖的需求，回退到 SKILL.md 的通用规则。
>
> **只读/写入：** 场景一~二、四为**只读分析**；场景三（批量入职）、场景五（批量操作 Excel）为**写入操作**，须用户明确确认后执行。

---

## 通用约定

### 1. 参数收集

- 执行任何场景前，先确认场景所需的「前置信息」是否齐全（见各场景章节）。缺失的向用户追问，**不猜测、不编造**。
- 用户话语中的枚举值（业务类型 filterBizType、状态码、字段枚举等），如需确认含义，先调用 `getEmployeeFilterFields` 等字段定义类命令查看，再作映射。

### 2. 命令使用前检查

- **命中 SOP 场景时**：场景文档（`sop-sceneN.md`）已给出每条命令的完整调用与请求体格式，**直接按文档执行，无需再执行 `xrxs-cli schema employee.<command>`**；场景文档已注明的参数/格式即为执行依据。
- 仅以下情况才执行 `xrxs-cli schema employee.<command>` 查看参数与请求体格式：
  - 未命中任何场景，回退到 `SKILL.md` 通用规则时；
  - 场景文档未覆盖的命令（如异常分支中需要的新命令、文档外的补充查询）；
  - 命令执行报错，需确认参数/请求体格式排错时。
- **同一命令最多检查一次**；禁止为排查字段而批量轮询多个无关命令的 schema（字段定义用一次 `getEmployeeFilterFields` 即可确认）。
- 请求体为 `application/json` 的接口，使用 `--request-body json` 或 `--request-body` 传 JSON 字符串；参数型接口用 `--<name> <value>` 传参。
- 分页接口必须循环拉全数据，禁止只取第一页就下结论。
- **同一请求体（同参数组合）最多拉取一次**；需要不同视角的数据时，基于已拉取的结果本地变换，禁止重复请求相同数据。
- **分页停止条件**：递增 `pageNo` 逐页拉取，当某页返回条数 < `pageSize` 或返回为空时停止；禁止 `pageNo` 不递增的重复请求，同一分页序列最多完整拉一次。
- **filters 回传规则（重要，实测验证）**：filters 中的每个筛选条件必须**原样回传 `getEmployeeFilterFields` 返回的完整条目**（含 `fieldId`/`listGroupId`/`documentType`/`dicType`/`dataSource` 等全部字段），仅填充 `values`（选项类：`[{"key":"<选项key>"}]`，多选多个元素）或 `dateValues`（日期类：`["yyyy/MM/dd","yyyy/MM/dd"]` 字符串，单边留空用 `""`）。
  - ⚠️ 只传最小结构（如仅 `fieldName`+`fieldFilterType`+`values`）或 `dateValues` 用毫秒时间戳 → 服务端报 `111005000 未知错误`（实测）；**`searchEntryRecord` 用毫秒时间戳实测返回空结果（不报错，易误判为"该周期无人入职"）**，一律使用 `yyyy/MM/dd` 字符串。
  - ✅ 已实测：转正记录按状态过滤（`regularRecordStatus` 完整条目 + `values:[{"key":"3"}]`）一次返回已超期名单；`regularRecordStatus`+`employeeStatus` 双条件过滤亦可。
- **searchRegularRecord 拉取策略（统一）**：按状态/时间查询转正记录时，**优先**按[场景一](sops/sop-scene1.md)「完整配置 filters 直接过滤」一次查出；仅当过滤报错（111005000）或返回混入其他状态时，回退 `filters: []` + `pageSize: 100` 全量拉取、结果内按 `regularRecordStatus`（1待转正/2已转正/3已超期/4未通过）与 `regularDate` 本地过滤。**禁止试探 pageSize**（5→100→25 这类）；**禁止未经 `getEmployeeFilterFields` 确认就猜 filters 字段名**。
- **状态查询场景（场景一）零补查（重要）**：用户只要「按状态查名单」（如已超期/待转正/未通过），**只展示 `searchRegularRecord` 返回的人员信息**，**不需要查询任何额外信息**（如部门、岗位、入职日期、试用期任务、考核参与人、转正表单、审批记录等），禁止 `schema`，禁止先 `filters: []` 全量试探——全流程 CLI 调用最多 2 次（getEmployeeFilterFields + searchRegularRecord 各 1 次）。返回里没有的字段直接不展示。**禁止把名单数据重新抄写进 `run_python_code` 计算**（搬运易抄漏致名单不完整且耗时 40s+），直接基于返回结果组织答案。
- **不要将执行的命令原样返回给用户**，只呈现分析结果。

### 3. 数据可信度

- 所有数据以 xrxs-cli 实际返回为准。返回字段缺失时，先判断是否为字段名不同（可调用字段定义类命令确认），确认缺失后再走对应场景的「异常分支」，**禁止用编造数据填充**。
- 日期类筛选使用 `getEmployeeFilterFields` 返回的字段定义填值（`fieldFilterType` 按 1-日期规则填 `dateValues`，值为 `yyyy/MM/dd` 字符串，**不是毫秒时间戳**；完整条目回传要求见通用约定「filters 回传规则」）。
