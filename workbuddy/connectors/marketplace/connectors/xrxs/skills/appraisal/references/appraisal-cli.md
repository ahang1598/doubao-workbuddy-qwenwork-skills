# appraisal CLI公共接口控制器

> **前置条件：** 先阅读 [`../SKILL.md`](../SKILL.md) 了解全局能力。

CLI公共接口控制器相关操作。

## 适用场景

- 获取方案周期枚举定义
- 返回值示例：{"value":1,"desc":"绩效考核"},{"value":2,"desc":"试用期考核"},{"value":3,"desc":"组织绩效"}
- 返回值示例：{"value":0,"desc":"未开始"},{"value":1,"desc":"进行中"},{"value":3,"desc":"终止考核"},{"value":4,"desc":"已归档"}

## 推荐命令

### getPlanPeriodDefinitions

获取方案周期枚举定义

> **禁止调用该接口**：周期枚举已内联，直接查下表；场景一文档 [`sops/sop-scene1.md`](sops/sop-scene1.md) 步骤 2 亦有同名枚举表。

| planPeriod | 含义 | planPeriod | 含义 |
|---|---|---|---|
| -1 | 试用期 | 14 | 七月八月 |
| 1 | 年度 | 15 | 八月九月 |
| 2 | 上半年 | 16 | 九月十月 |
| 3 | 下半年 | 17 | 十月十一月 |
| 4 | 第一季度 | 18 | 十一月十二月 |
| 5 | 第二季度 | 19 | 十二月一月 |
| 6 | 第三季度 | 20 | 一月 |
| 7 | 第四季度 | 21 | 二月 |
| 8 | 一月二月 | 22 | 三月 |
| 9 | 二月三月 | 23 | 四月 |
| 10 | 三月四月 | 24 | 五月 |
| 11 | 四月五月 | 25 | 六月 |
| 12 | 五月六月 | 26 | 七月 |
| 13 | 六月七月 | 27~31 | 八月~十二月（27=八月 … 31=十二月） |

```bash
xrxs-cli appraisal getPlanPeriodDefinitions
```

> 请求方式：`GET`。无请求体，参数通过 `--<name> <value>` 传递。

### getPlanTypeDefinitions

返回值示例：{"value":1,"desc":"绩效考核"},{"value":2,"desc":"试用期考核"},{"value":3,"desc":"组织绩效"}

```bash
xrxs-cli appraisal getPlanTypeDefinitions
```

> 请求方式：`GET`。无请求体，参数通过 `--<name> <value>` 传递。

### getPlanStatusDefinitions

获取方案状态枚举定义

> **禁止调用该接口**：状态枚举已内联，直接查下表。

| value | 含义 |
|---|---|
| 0 | 未开始 |
| 1 | 进行中 |
| 3 | 终止考核 |
| 4 | 已归档 |

```bash
xrxs-cli appraisal getPlanStatusDefinitions
```

> 请求方式：`GET`。无请求体，参数通过 `--<name> <value>` 传递。

### terminateAssesseePreview

终止被考核人预览

```bash
xrxs-cli appraisal terminateAssesseePreview \
  --request-body json
```

> 请求方式：`POST`，`Content-Type: application/json`。JSON 请求体请使用 `--request-body json` 传递。

请求体参数（JSON）：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--planId` | 是 | 方案ID，必填 |
| `--stopReason` | 是 | 终止理由，必填 |
| `--assesseeEmpIds` | 是 | 被考核人ID列表，必填，不超过100个 |

> **权限检查**：调用正式命令 `batchTerminateAssessee` 前，先执行 `xrxs-cli permission check appraisal-batchTerminateAssessee` 判断用户是否已授权永久允许执行该命令：返回 `true` 说明已授权，可直接调用 `batchTerminateAssessee`；返回 `false` 说明未授权，必须先调用本预览命令展示操作摘要，等用户确认后再调用 `batchTerminateAssessee`。

### batchTerminateAssessee

批量终止被考核人

```bash
xrxs-cli appraisal batchTerminateAssessee \
  --request-body json
```

> 请求方式：`POST`，`Content-Type: application/json`。JSON 请求体请使用 `--request-body json` 传递。

请求体参数（JSON）：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--planId` | 是 | 方案ID，必填 |
| `--stopReason` | 是 | 终止理由，必填 |
| `--assesseeEmpIds` | 是 | 被考核人ID列表，必填，不超过100个 |

### restartAssesseePreview

重启被考核人预览

```bash
xrxs-cli appraisal restartAssesseePreview \
  --request-body json
```

> 请求方式：`POST`，`Content-Type: application/json`。JSON 请求体请使用 `--request-body json` 传递。

请求体参数（JSON）：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--planId` | 是 | 方案ID，必填 |
| `--sendTodo` | 否 | 是否重新生成待办并发送提醒，0-不发送(默认) 1-发送 |
| `--assesseeEmpIds` | 是 | 被考核人ID列表，必填，不超过100个 |

> **权限检查**：调用正式命令 `batchRestartAssessee` 前，先执行 `xrxs-cli permission check appraisal-batchRestartAssessee` 判断用户是否已授权永久允许执行该命令：返回 `true` 说明已授权，可直接调用 `batchRestartAssessee`；返回 `false` 说明未授权，必须先调用本预览命令展示操作摘要，等用户确认后再调用 `batchRestartAssessee`。

### batchRestartAssessee

批量重启被考核人

```bash
xrxs-cli appraisal batchRestartAssessee \
  --request-body json
```

> 请求方式：`POST`，`Content-Type: application/json`。JSON 请求体请使用 `--request-body json` 传递。

请求体参数（JSON）：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--planId` | 是 | 方案ID，必填 |
| `--sendTodo` | 否 | 是否重新生成待办并发送提醒，0-不发送(默认) 1-发送 |
| `--assesseeEmpIds` | 是 | 被考核人ID列表，必填，不超过100个 |

### addAssessee

添加被考核对象

```bash
xrxs-cli appraisal addAssessee \
  --request-body json
```

> 请求方式：`POST`，`Content-Type: application/json`。JSON 请求体请使用 `--request-body json` 传递。

请求体参数（JSON）：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--planId` | 是 | 方案ID，必填 |
| `--assessBizIds` | 否 | 被考核对象ID集合，个人绩效传员工ID，组织绩效传组织ID |
| `--assessmentId` | 是 | 考核表ID，必填 |

### deleteAssesseePreview

删除被考核对象预览（写入操作前置确认，必须先调用此命令展示影响面，等用户确认后再执行 `deleteAssessee`）

```bash
xrxs-cli appraisal deleteAssesseePreview \
  --request-body json
```

> 请求方式：`POST`，`Content-Type: application/json`。JSON 请求体请使用 `--request-body json` 传递。

请求体参数（JSON）：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--planId` | 是 | 方案ID，必填 |
| `--deleteReason` | 是 | 删除原因，必填 |
| `--assesseeEmpId` | 是 | 被考核对象ID，必填 |

> **权限检查**：调用正式命令 `deleteAssessee` 前，先执行 `xrxs-cli permission check appraisal-deleteAssessee` 判断用户是否已授权永久允许执行该命令：返回 `true` 说明已授权，可直接调用 `deleteAssessee`；返回 `false` 说明未授权，必须先调用本预览命令展示操作摘要，等用户确认后再调用 `deleteAssessee`。

### deleteAssessee

删除被考核对象

```bash
xrxs-cli appraisal deleteAssessee \
  --request-body json
```

> 请求方式：`POST`，`Content-Type: application/json`。JSON 请求体请使用 `--request-body json` 传递。

请求体参数（JSON）：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--planId` | 是 | 方案ID，必填 |
| `--deleteReason` | 是 | 删除原因，必填 |
| `--assesseeEmpId` | 是 | 被考核对象ID，必填 |

### queryAssesseeBaseInfo

查询被考核人基础信息

```bash
xrxs-cli appraisal queryAssesseeBaseInfo \
  --request-body json
```

> 请求方式：`POST`，`Content-Type: application/json`。JSON 请求体请使用 `--request-body json` 传递。

请求体参数（JSON）：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--planId` | 否 | 方案ID |
| `--assesseeEmpId` | 否 | 被考核人ID，个人绩效为员工ID，组织绩效为部门ID |

### rejectAssesseePreview

驳回被考核人预览

```bash
xrxs-cli appraisal rejectAssesseePreview \
  --request-body json
```

> 请求方式：`POST`，`Content-Type: application/json`。JSON 请求体请使用 `--request-body json` 传递。

请求体参数（JSON）：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--planId` | 是 | 方案ID，必填 |
| `--reason` | 是 | 驳回理由，必填 |
| `--assesseeEmpId` | 是 | 被考核人ID，必填，单个 |
| `--targetInspectionStatus` | 是 | 希望驳回到的目标环节标识，必填，必须是该被考核人当前可驳回的环节之一 |

> **权限检查**：调用正式命令 `rejectAssessee` 前，先执行 `xrxs-cli permission check appraisal-rejectAssessee` 判断用户是否已授权永久允许执行该命令：返回 `true` 说明已授权，可直接调用 `rejectAssessee`；返回 `false` 说明未授权，必须先调用本预览命令展示操作摘要，等用户确认后再调用 `rejectAssessee`。

### rejectAssessee

驳回被考核人到指定环节

```bash
xrxs-cli appraisal rejectAssessee \
  --request-body json
```

> 请求方式：`POST`，`Content-Type: application/json`。JSON 请求体请使用 `--request-body json` 传递。

请求体参数（JSON）：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--planId` | 是 | 方案ID，必填 |
| `--reason` | 是 | 驳回理由，必填 |
| `--assesseeEmpId` | 是 | 被考核人ID，必填，单个 |
| `--targetInspectionStatus` | 是 | 希望驳回到的目标环节标识，必填，必须是该被考核人当前可驳回的环节之一 |

### skipAssesseePreview

跳过被考核人预览

```bash
xrxs-cli appraisal skipAssesseePreview \
  --request-body json
```

> 请求方式：`POST`，`Content-Type: application/json`。JSON 请求体请使用 `--request-body json` 传递。

请求体参数（JSON）：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--planId` | 是 | 方案ID，必填 |
| `--assesseeEmpIds` | 是 | 被考核人ID列表，必填，不超过100个 |

> **权限检查**：调用正式命令 `batchSkipAssessee` 前，先执行 `xrxs-cli permission check appraisal-batchSkipAssessee` 判断用户是否已授权永久允许执行该命令：返回 `true` 说明已授权，可直接调用 `batchSkipAssessee`；返回 `false` 说明未授权，必须先调用本预览命令展示操作摘要，等用户确认后再调用 `batchSkipAssessee`。

### batchSkipAssessee

批量跳过被考核人

```bash
xrxs-cli appraisal batchSkipAssessee \
  --request-body json
```

> 请求方式：`POST`，`Content-Type: application/json`。JSON 请求体请使用 `--request-body json` 传递。

请求体参数（JSON）：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--planId` | 是 | 方案ID，必填 |
| `--assesseeEmpIds` | 是 | 被考核人ID列表，必填，不超过100个 |

### distributeResultAssesseePreview

单个被考核人发放结果预览（写入操作前置确认，必须先调用此命令展示操作摘要，等用户确认后再执行 `distributeResultAssessee`）

```bash
xrxs-cli appraisal distributeResultAssesseePreview \
  --request-body json
```

> 请求方式：`POST`，`Content-Type: application/json`。JSON 请求体请使用 `--request-body json` 传递。

请求体参数（JSON）：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--planId` | 否 | 方案ID。 |
| `--assesseeEmpId` | 否 | 被考核人员工ID。 |

> **权限检查**：调用正式命令 `distributeResultAssessee` 前，先执行 `xrxs-cli permission check appraisal-distributeResultAssessee` 判断用户是否已授权永久允许执行该命令：返回 `true` 说明已授权，可直接调用 `distributeResultAssessee`；返回 `false` 说明未授权，必须先调用本预览命令展示操作摘要，等用户确认后再调用 `distributeResultAssessee`。

### distributeResultAssessee

单个被考核人发放结果

```bash
xrxs-cli appraisal distributeResultAssessee \
  --request-body json
```

> 请求方式：`POST`，`Content-Type: application/json`。JSON 请求体请使用 `--request-body json` 传递。

请求体参数（JSON）：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--planId` | 否 | 方案ID。 |
| `--assesseeEmpId` | 否 | 被考核人员工ID。 |

### getCanRejectProcessList

查询被考核人可退回环节列表

```bash
xrxs-cli appraisal getCanRejectProcessList \
  --request-body json
```

> 请求方式：`POST`，`Content-Type: application/json`。JSON 请求体请使用 `--request-body json` 传递。

请求体参数（JSON）：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--planId` | 否 | 方案ID。 |
| `--assesseeEmpId` | 否 | 被考核人员工ID。 |

### queryAssesseeInfos

搜索获取被考核人明细列表页。

> **请求体使用 `searchMode + stage + filters` 业务化范式**。完整编排规则见 [`query-assessee-infos-guide.md`](query-assessee-infos-guide.md)，**调用前必须先读**。

```bash
xrxs-cli appraisal queryAssesseeInfos \
  --fields "<返回字段列表>" \
  --request-body json
```

> 请求方式：`POST`，`Content-Type: application/json`。JSON 请求体请使用 `--request-body json` 传递。

请求体参数（JSON）：

| 参数 | 必填 | 说明 |
|------|------|------|
| `searchMode` | 是 | `PLAN_SUBJECTS`（单方案）/ `PERSONAL_PERFORMANCE_RECORDS`（跨方案个人绩效） |
| `planId` | 条件必填 | 仅 `PLAN_SUBJECTS` 用，精确方案 ID |
| `planIds` | 否 | 仅跨方案用，限定个人方案（≤100）；不传表示权限范围内跨全部个人方案 |
| `planTypes` | 否 | 仅跨方案用，允许 `[1]`/`[2]`/`[1,2]`，不允许 `3` |
| `stage` | 否 | 阶段条件：`{"mode":"ALL"|"COMPLETED"|"TERMINATED"}` 或 `{"mode":"FLOW","flowId":"<真实flowId>"}`；默认 ALL |
| `keyword` | 否 | 最长 50 字符，匹配姓名/部门/岗位等 |
| `filters` | 否 | 业务化筛选对象（`departmentIds`/`finalScore`/`todoEmployeeIds` 等），见 guide 第 6 节 |
| `sortOrders` | 否 | 仅跨方案模式支持 |
| `pageNum` / `pageSize` | 否 | 默认 1 / 100，pageSize 最大 100 |

**参数约束：** 单方案传 `planId`，跨方案传 `planIds`，二者不混用；组织绩效只能单方案；`pageSize` 最大 100。

### batchQueryAssesseeDimensionScores

批量查询被考核人维度得分

```bash
xrxs-cli appraisal batchQueryAssesseeDimensionScores \
  --request-body json
```

> 请求方式：`POST`，`Content-Type: application/json`。JSON 请求体请使用 `--request-body json` 传递。

请求体参数（JSON）：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--needTargetScores` | 否 | 是否需要返回维度下的指标得分 |
| `--planAssesseeList` | 否 | 方案及被考核对象查询列表 |

### batchQueryAssesseeTargetScores

批量查询被考核人指标得分

```bash
xrxs-cli appraisal batchQueryAssesseeTargetScores \
  --request-body json
```

> 请求方式：`POST`，`Content-Type: application/json`。JSON 请求体请使用 `--request-body json` 传递。

请求体参数（JSON）：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--companyId` | 否 | 公司ID |
| `--planAssesseeList` | 否 | 方案及其被考核人查询列表 |

### batchUrgeRemindPreview

批量催办预览

```bash
xrxs-cli appraisal batchUrgeRemindPreview \
  --request-body '{"planIds":["<planId>"],"planType":1,"planFlow":[{"flowName":"员工自评","inspectionStatus":2}],"employeeIds":["<员工id1>","<员工id2>"]}'
```

> 请求方式：`POST`，`Content-Type: application/json`。JSON 请求体请使用 `--request-body json` 传递。

请求体参数（JSON）：

| 参数 | 必填 | 说明 |
|------|------|------|
| `planIds` | 是 | 方案ID列表，必填。**限制：需要催办多个方案时，必须一次传入全部方案ID（数组，如 `["id1","id2","id3"]`），不得按方案拆分多次预览/执行；若方案分属不同 `planType`，则按 `planType` 分组分别预览** |
| `planType` | 是 | 方案类型，必填（1-绩效考核，2-试用期考核，3-组织绩效） |
| `planFlow` | 否 | 催办环节列表 `[{"flowName":"环节名","inspectionStatus":环节类型值}]`；为空时催办所选范围内的全部当前待办 |
| `employeeIds` | 否 | 人员ID列表，与部门至少选择一项 |
| `departmentIds` | 否 | 部门ID列表，与人员至少选择一项 |

> **权限检查**：调用正式命令 `batchUrgeRemind` 前，先执行 `xrxs-cli permission check appraisal-batchUrgeRemind` 判断用户是否已授权永久允许执行该命令：返回 `true` 说明已授权，可直接调用 `batchUrgeRemind`；返回 `false` 说明未授权，必须先调用本预览命令展示操作摘要，等用户确认后再调用 `batchUrgeRemind`。

### batchUrgeRemind

批量催办

```bash
xrxs-cli appraisal batchUrgeRemind \
  --request-body '{"planIds":["<planId>"],"planType":1,"planFlow":[{"flowName":"员工自评","inspectionStatus":2}],"employeeIds":["<员工id1>","<员工id2>"]}'
```

> 请求方式：`POST`，`Content-Type: application/json`。JSON 请求体请使用 `--request-body json` 传递。

请求体参数（JSON）：

| 参数 | 必填 | 说明 |
|------|------|------|
| `planIds` | 是 | 方案ID列表，必填。**限制：需要催办多个方案时，必须一次传入全部方案ID（数组，如 `["id1","id2","id3"]`），不得按方案拆分多次预览/执行；若方案分属不同 `planType`，则按 `planType` 分组分别预览** |
| `planType` | 是 | 方案类型，必填（1-绩效考核，2-试用期考核，3-组织绩效） |
| `planFlow` | 否 | 催办环节列表 `[{"flowName":"环节名","inspectionStatus":环节类型值}]`；为空时催办所选范围内的全部当前待办 |
| `employeeIds` | 否 | 人员ID列表，与部门至少选择一项 |
| `departmentIds` | 否 | 部门ID列表，与人员至少选择一项 |

### queryAssesseePlanInfos

查询员工参与的全部方案及被考核对象基础信息（按员工维度反查方案）。

```bash
xrxs-cli appraisal queryAssesseePlanInfos \
  --employee-id '<员工id>'
```

> 请求方式：`GET`。参数通过 `--<name> <value>` 传递。

请求参数：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--employee-id` | 是 | 员工ID |
| `--plan-status` | 否 | 方案状态，可为空；为空时查询全部状态 |
| `--plan-types` | 否 | 方案类型，可多选；为空时默认查询个人绩效和试用期绩效 |

### getQueryFieldDefinitions

获取被考核人查询构建器支持的可查询字段。

```bash
xrxs-cli appraisal getQueryFieldDefinitions
```

> 请求方式：`GET`。无请求体，参数通过 `--<name> <value>` 传递。

### getAssesseeQueryConditionTypeDefinitions

返回单选、多选、范围、多个范围、模糊搜索等查询条件类型定义。

```bash
xrxs-cli appraisal getAssesseeQueryConditionTypeDefinitions
```

> 请求方式：`GET`。无请求体，参数通过 `--<name> <value>` 传递。

### queryAssessGroups

根据方案查询考核组。

```bash
xrxs-cli appraisal queryAssessGroups \
  --request-body json
```

> 请求方式：`POST`，`Content-Type: application/json`。JSON 请求体请使用 `--request-body json` 传递。

请求体参数（JSON）：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--planId` | 是 | 方案ID，必填 |

### getPlanFlowList

获取方案流程环节列表

```bash
xrxs-cli appraisal getPlanFlowList \
  --request-body json
```

> 请求方式：`POST`，`Content-Type: application/json`。JSON 请求体请使用 `--request-body json` 传递。

请求体参数（JSON）：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--planId` | 是 | 方案ID，必填 |

### getPlanFlowPeopleCount

返回结果包含总量、各环节人数、已完成人数、已终止人数

```bash
xrxs-cli appraisal getPlanFlowPeopleCount \
  --request-body json
```

> 请求方式：`POST`，`Content-Type: application/json`。JSON 请求体请使用 `--request-body json` 传递。

请求体参数（JSON）：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--planId` | 是 | 方案ID，必填 |

### archivePlan

仅进行中的方案才能归档，且不能存在进行中的绩效申诉记录

```bash
xrxs-cli appraisal archivePlan \
  --request-body json
```

> 请求方式：`POST`，`Content-Type: application/json`。JSON 请求体请使用 `--request-body json` 传递。

请求体参数（JSON）：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--planId` | 是 | 方案ID，必填 |
| `--closeAutoCreate` | 否 | 是否同时关闭自动创建，0-否(默认) 1-是 |

### archivePlanPreview

归档方案预览（写入操作前置确认，必须先调用此命令展示影响面，等用户确认后再执行 `archivePlan`）

```bash
xrxs-cli appraisal archivePlanPreview \
  --request-body json
```

> 请求方式：`POST`，`Content-Type: application/json`。JSON 请求体请使用 `--request-body json` 传递。

请求体参数（JSON）：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--planId` | 是 | 方案ID，必填 |
| `--closeAutoCreate` | 否 | 是否同时关闭自动创建，0-否(默认) 1-是 |

### stopPlanPreview

终止方案预览（写入操作前置确认，必须先调用此命令展示影响面，等用户确认后再执行 `stopPlan`）

```bash
xrxs-cli appraisal stopPlanPreview \
  --request-body json
```

> 请求方式：`POST`，`Content-Type: application/json`。JSON 请求体请使用 `--request-body json` 传递。

请求体参数（JSON）：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--planId` | 是 | 方案ID，必填 |
| `--stopReason` | 否 | 终止理由，可选 |

> **权限检查**：调用正式命令 `stopPlan` 前，先执行 `xrxs-cli permission check appraisal-stopPlan` 判断用户是否已授权永久允许执行该命令：返回 `true` 说明已授权，可直接调用 `stopPlan`；返回 `false` 说明未授权，必须先调用本预览命令展示操作摘要，等用户确认后再调用 `stopPlan`。

### stopPlan

仅进行中的方案才能终止

```bash
xrxs-cli appraisal stopPlan \
  --request-body json
```

> 请求方式：`POST`，`Content-Type: application/json`。JSON 请求体请使用 `--request-body json` 传递。

请求体参数（JSON）：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--planId` | 是 | 方案ID，必填 |
| `--stopReason` | 否 | 终止理由，可选 |

### restartPlanPreview

重启方案预览（写入操作前置确认，必须先调用此命令展示影响面，等用户确认后再执行 `restartPlan`）

```bash
xrxs-cli appraisal restartPlanPreview \
  --request-body json
```

> 请求方式：`POST`，`Content-Type: application/json`。JSON 请求体请使用 `--request-body json` 传递。

请求体参数（JSON）：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--planId` | 是 | 方案ID，必填 |
| `--sendTodo` | 否 | 是否重新生成待办并发送提醒，0-不发送(默认) 1-发送 |

> **权限检查**：调用正式命令 `restartPlan` 前，先执行 `xrxs-cli permission check appraisal-restartPlan` 判断用户是否已授权永久允许执行该命令：返回 `true` 说明已授权，可直接调用 `restartPlan`；返回 `false` 说明未授权，必须先调用本预览命令展示操作摘要，等用户确认后再调用 `restartPlan`。

### restartPlan

支持从终止或归档状态重启到进行中，startFlag为false时表示存在重复被考核对象冲突

```bash
xrxs-cli appraisal restartPlan \
  --request-body json
```

> 请求方式：`POST`，`Content-Type: application/json`。JSON 请求体请使用 `--request-body json` 传递。

请求体参数（JSON）：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--planId` | 是 | 方案ID，必填 |
| `--sendTodo` | 否 | 是否重新生成待办并发送提醒，0-不发送(默认) 1-发送 |

### queryCanOpenFlowList

获取方案当前可开启的环节

```bash
xrxs-cli appraisal queryCanOpenFlowList \
  --request-body json
```

> 请求方式：`POST`，`Content-Type: application/json`。JSON 请求体请使用 `--request-body json` 传递。

请求体参数（JSON）：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--planId` | 是 | 方案ID，必填 |

### openPlanFlowPreview

开启方案指定环节预览

```bash
xrxs-cli appraisal openPlanFlowPreview \
  --request-body json
```

> 请求方式：`POST`，`Content-Type: application/json`。JSON 请求体请使用 `--request-body json` 传递。

请求体参数（JSON）：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--flowId` | 是 | 待开启的环节ID，必填 |
| `--planId` | 是 | 方案ID，必填 |

> **权限检查**：调用正式命令 `openPlanFlow` 前，先执行 `xrxs-cli permission check appraisal-openPlanFlow` 判断用户是否已授权永久允许执行该命令：返回 `true` 说明已授权，可直接调用 `openPlanFlow`；返回 `false` 说明未授权，必须先调用本预览命令展示操作摘要，等用户确认后再调用 `openPlanFlow`。

### openPlanFlow

开启后该方案下所有被考核人将自动推进到指定环节

```bash
xrxs-cli appraisal openPlanFlow \
  --request-body json
```

> 请求方式：`POST`，`Content-Type: application/json`。JSON 请求体请使用 `--request-body json` 传递。

请求体参数（JSON）：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--flowId` | 是 | 待开启的环节ID，必填 |
| `--planId` | 是 | 方案ID，必填 |

### getPlanManagerList

获取方案管理人员列表

```bash
xrxs-cli appraisal getPlanManagerList \
  --request-body json
```

> 请求方式：`POST`，`Content-Type: application/json`。JSON 请求体请使用 `--request-body json` 传递。

请求体参数（JSON）：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--planId` | 是 | 方案ID，必填 |
| `--planType` | 否 | 方案类型，可选 |
| `--copyPlanFlag` | 否 | 是否复制方案，可选 |

### deletePlanPreview

删除方案预览（写入操作前置确认，必须先调用此命令展示影响面，等用户确认后再执行 `deletePlan`）

```bash
xrxs-cli appraisal deletePlanPreview \
  --request-body json
```

> 请求方式：`POST`，`Content-Type: application/json`。JSON 请求体请使用 `--request-body json` 传递。

请求体参数（JSON）：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--planId` | 是 | 方案ID，必填 |
| `--version` | 否 | 版本，1-旧版KPI 2-新版KPI 3-新版KPI(自主上传) 4-360考核，默认2 |
| `--deleteReason` | 否 | 删除理由，可选 |

> **权限检查**：调用正式命令 `deletePlan` 前，先执行 `xrxs-cli permission check appraisal-deletePlan` 判断用户是否已授权永久允许执行该命令：返回 `true` 说明已授权，可直接调用 `deletePlan`；返回 `false` 说明未授权，必须先调用本预览命令展示操作摘要，等用户确认后再调用 `deletePlan`。

### deletePlan

支持删除新版KPI、旧版KPI、自主上传及360考核方案，通过version字段区分，默认version=2

```bash
xrxs-cli appraisal deletePlan \
  --request-body json
```

> 请求方式：`POST`，`Content-Type: application/json`。JSON 请求体请使用 `--request-body json` 传递。

请求体参数（JSON）：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--planId` | 是 | 方案ID，必填 |
| `--version` | 否 | 版本，1-旧版KPI 2-新版KPI 3-新版KPI(自主上传) 4-360考核，默认2 |
| `--deleteReason` | 否 | 删除理由，可选 |

### publishPlanResultPreview

发放方案结果预览（写入操作前置确认，必须先调用此命令展示影响面，等用户确认后再执行 `publishPlanResult`）

```bash
xrxs-cli appraisal publishPlanResultPreview \
  --request-body json
```

> 请求方式：`POST`，`Content-Type: application/json`。JSON 请求体请使用 `--request-body json` 传递。

请求体参数（JSON）：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--planId` | 是 | 方案ID，必填 |

> **权限检查**：调用正式命令 `publishPlanResult` 前，先执行 `xrxs-cli permission check appraisal-publishPlanResult` 判断用户是否已授权永久允许执行该命令：返回 `true` 说明已授权，可直接调用 `publishPlanResult`；返回 `false` 说明未授权，必须先调用本预览命令展示操作摘要，等用户确认后再调用 `publishPlanResult`。

### publishPlanResult

仅进行中且未发放结果的方案才能执行发放，发放后所有被考核人结果将被公开

```bash
xrxs-cli appraisal publishPlanResult \
  --request-body json
```

> 请求方式：`POST`，`Content-Type: application/json`。JSON 请求体请使用 `--request-body json` 传递。

请求体参数（JSON）：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--planId` | 是 | 方案ID，必填 |

### batchQueryPlanInfos

必须传入 planStatus 和 planType 参数，否则将抛出参数校验异常。
planIds 可为空，为空时查询全部有权限的方案。
planName 可为空，非空时按方案名称模糊检索。

**planName 参数使用规则（必读）**：
- planName 只传**方案核心名称**，必须去掉口语化冗余词，包括但不限于："方案"、"考核方案"、"绩效方案"、"这个"、"那个"、动词（"把…归档"中的"归档"）等。
- 用户话语示例 → 正确参数：`"把引入考核表方案归档"` → `planName: "引入考核表"`；`"试一把灵听考核方案"` → `planName: "试一把灵听"`。
- 若上下文已明确方案 ID（如用户直接给出、或前序查询返回过），**优先使用 `planIds` 精确查询**，不要依赖 planName 模糊检索。
- 模糊检索无结果时：先确认是否带了冗余后缀导致漏匹配，去掉后缀重试一次；仍无结果再扩大 planStatus 范围，禁止用不同写法（如加"方案"二字）连环重复查询。

```bash
xrxs-cli appraisal batchQueryPlanInfos \
  --request-body json
```

> 请求方式：`POST`，`Content-Type: application/json`。JSON 请求体请使用 `--request-body json` 传递。

请求体参数（JSON）：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--planIds` | 否 | 方案ID列表 |
| `--planName` | 否 | 方案名称，支持模糊检索。 |
| `--planType` | 否 | 方案类型（必填）。
可选值参见{@link com.qjyd.appraisal.domain.kpiPlan.bean.enums.EKpiPlanType}：
1-绩效考核，2-试用期考核，3-组织绩效 |
| `--planStatus` | 否 | 方案状态（必填）。
可选值参见{@link com.qjyd.appraisal.domain.kpiPlan.bean.enums.EKpiPlanStatus}：
0-未开始，1-进行中，3-终止考核，4-已归档 |

### batchQueryPlanResultSettings

批量查询方案结果设置

```bash
xrxs-cli appraisal batchQueryPlanResultSettings \
  --request-body json
```

> 请求方式：`POST`，`Content-Type: application/json`。JSON 请求体请使用 `--request-body json` 传递。

请求体参数（JSON）：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--planIds` | 否 | 方案ID列表 |
| `--planName` | 否 | 方案名称，支持模糊检索。 |
| `--planType` | 否 | 方案类型（必填）。
可选值参见{@link com.qjyd.appraisal.domain.kpiPlan.bean.enums.EKpiPlanType}：
1-绩效考核，2-试用期考核，3-组织绩效 |
| `--planStatus` | 否 | 方案状态（必填）。
可选值参见{@link com.qjyd.appraisal.domain.kpiPlan.bean.enums.EKpiPlanStatus}：
0-未开始，1-进行中，3-终止考核，4-已归档 |

### getRemindSetting

查询公司自动提醒配置

```bash
xrxs-cli appraisal getRemindSetting
```

> 请求方式：`GET`。无请求体，参数通过 `--<name> <value>` 传递。

### updateRemindSetting

提醒时间仅支持整点，范围为 08:00 - 22:00

```bash
xrxs-cli appraisal updateRemindSetting \
  --request-body json
```

> 请求方式：`POST`，`Content-Type: application/json`。JSON 请求体请使用 `--request-body json` 传递。

请求体参数（JSON）：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--enabled` | 是 | 是否开启自动提醒：0-关闭 1-开启，必填 |
| `--remindTime` | 是 | 提醒时间，格式 HH:mm，仅支持整点，且范围为 08:00 - 22:00（如 "08:00"、"22:00"）。
开启自动提醒时必填。 |

### getPlanBasicInfo

获取方案基础信息。

```bash
xrxs-cli appraisal getPlanBasicInfo \
  --planId <planId>
```

> 请求方式：`GET`。无请求体，参数通过 `--<name> <value>` 传递。

参数：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--planId` | 是 | 方案ID |

### savePlanBasicInfo

保存方案基础信息，支持新建和编辑方案。

```bash
xrxs-cli appraisal savePlanBasicInfo \
  --request-body json
```

> 请求方式：`POST`，`Content-Type: application/json`。JSON 请求体请使用 `--request-body json` 传递。

请求体参数（JSON）：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--planId` | 否 | 方案ID；为空时新建，不为空时更新 |
| `--okrCycle` | 否 | 考核周期 |
| `--planName` | 否 | 方案名称 |
| `--planType` | 否 | 方案类型 |
| `--planYear` | 否 | 考核年度 |
| `--autoCreate` | 否 | 是否自动创建方案：0-否，1-是 |
| `--createRule` | 否 | 方案名称生成规则 |
| `--attributeId` | 否 | 方案属性ID |
| `--empAuthList` | 否 | 方案管理权限 |
| `--planEndTime` | 否 | 考核结束时间，格式：yyyy/MM/dd |
| `--autoCreateDay` | 否 | 自动创建日 |
| `--planStartTime` | 否 | 考核开始时间，格式：yyyy/MM/dd |
| `--assesseeRemark` | 否 | 考核说明 |
| `--autoAddEmployee` | 否 | 是否自动加入新员工：0-否，1-是 |
| `--autoCreateEndTime` | 否 | 自动创建结束时间，格式：yyyy/MM/dd |
| `--autoCreateDateUnit` | 否 | 自动创建日期单位 |
| `--curingPersonSwitch` | 否 | 实时更新参与人开关：0-固化，1-实时更新 |
| `--addEmployeeLimitDay` | 否 | 考核结束前允许自动加入员工的天数 |
| `--autoAddEmployeeType` | 否 | 自动加入员工类型：1-定时刷新，2-入职触发 |
| `--autoCreateStartPlan` | 否 | 自动创建后是否自动开启方案：0-否，1-是 |
| `--autoCreateStartTime` | 否 | 自动创建开始时间，格式：yyyy/MM/dd |
| `--assessVisibleAuthData` | 否 | 组织绩效可见配置 |

### getAttributeList

获取当前公司可用的考核属性列表。

```bash
xrxs-cli appraisal getAttributeList
```

> 请求方式：`GET`。无请求体，参数通过 `--<name> <value>` 传递。

### querySelfManagedAccountList

返回具有对应方案类型权限的自管账号；传入方案ID时，同时包含方案授权人员及方案创建人，
并补充符合条件的高管账号。

```bash
xrxs-cli appraisal querySelfManagedAccountList \
  --request-body json
```

> 请求方式：`POST`，`Content-Type: application/json`。JSON 请求体请使用 `--request-body json` 传递。

请求体参数（JSON）：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--planId` | 否 | 方案ID，可选；传入时追加方案授权人员及方案创建人 |
| `--planType` | 否 | 方案类型，可选；用于匹配对应类型的自管权限 |
| `--copyPlanFlag` | 否 | 是否复制方案，可选；0-否，1-是 |

### checkPlan

方案开启校验。

```bash
xrxs-cli appraisal checkPlan \
  --planId <planId>
```

> 请求方式：`POST`。无请求体，参数通过 `--<name> <value>` 传递。

参数：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--planId` | 是 | 方案ID |

### startPlanPreview

开启方案预览（写入操作前置确认，必须先调用此命令展示影响面，等用户确认后再执行 `startPlan`）

```bash
xrxs-cli appraisal startPlanPreview \
  --planId <planId>
```

> 请求方式：`POST`。无请求体，参数通过 `--<name> <value>` 传递。

参数：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--planId` | 是 | 方案ID |

> **权限检查**：调用正式命令 `startPlan` 前，先执行 `xrxs-cli permission check appraisal-startPlan` 判断用户是否已授权永久允许执行该命令：返回 `true` 说明已授权，可直接调用 `startPlan`；返回 `false` 说明未授权，必须先调用本预览命令展示操作摘要，等用户确认后再调用 `startPlan`。

### startPlan

开启方案。

```bash
xrxs-cli appraisal startPlan \
  --planId <planId>
```

> 请求方式：`POST`。无请求体，参数通过 `--<name> <value>` 传递。

参数：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--planId` | 是 | 方案ID |

## 注意事项

- 写入/删除操作，执行前必须确认用户意图。
- 预览接口（路径/命令名以 `-preview` 结尾）调用后，xrxs-cli 会返回 `taskId`、`summaryHeaderMap`、`summaryData`、`originalName`、`riskLevel`。必须将其渲染为 `<confirm-card>` 组件，属性为 `taskId`、`summaryHeaderMap`（JSON 字符串）、`summaryData`（JSON 字符串）、`riskLevel`、`taskName`（取 `originalName`），禁止直接展示 JSON。
- **权限检查（permission check）**：调用带预览接口的正式命令前，先执行 `xrxs-cli permission check appraisal-<command>` 判断用户是否已授权永久允许执行该命令：返回 `true` 说明已授权，可直接调用正式命令；返回 `false` 说明未授权，必须先调用对应的 `<PreviewCommand>` 展示操作摘要，等用户确认后再调用正式命令。涉及预览接口的命令对见上方各命令说明（`batchTerminateAssessee`/`batchRestartAssessee`/`rejectAssessee`/`batchSkipAssessee`/`deleteAssessee`/`distributeResultAssessee`/`batchUrgeRemind`/`openPlanFlow`/`archivePlan`/`stopPlan`/`deletePlan`/`publishPlanResult`/`restartPlan`/`startPlan` 及其对应 Preview）。
- 可用 `--dry-run` 预览请求。

## 参考

- [appraisal](../SKILL.md) -- 全部命令