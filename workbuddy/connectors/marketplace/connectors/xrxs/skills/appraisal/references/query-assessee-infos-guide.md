# queryAssesseeInfos 统一查询编排规范

> **文档性质：** 供 AI Agent 执行的**精简编排规范**，是 `queryAssesseeInfos` 唯一权威调用依据。
> **适用命令：** `xrxs-cli appraisal queryAssesseeInfos`
> **对应接口：** `POST /appraisal/service/cli/kpi/assessee/ajax-query-assessee-infos.json`
>
> **读取规则：** 任何 SOP 场景（sop-scene1/3/6/7/9/10）需要查询被考核对象时，**必须按本规范判断模式、拼请求体**；场景文档已给出命令模板的，**优先按场景模板执行**；本规范是兜底与判模式依据。

---

## 1. 目标与硬性规则（防乱调用，必须先读）

本接口统一解决两类**只读**查询：

1. **单方案**：查一个考核方案下的被考核对象，支持绩效考核 / 试用期考核 / **组织绩效**。
2. **跨方案**：查多个或全部个人方案中的个人绩效记录，支持绩效考核 / 试用期考核，**不支持组织绩效**。

AI 必须遵守：

- 每次调用**显式传 `searchMode`**，请求体只使用 `searchMode` / `planId` / `planIds` / `stage` / `keyword` / `filters` / `sortOrders` / 分页字段这些新参数。
- **单方案传 `planId`；跨方案传 `planIds`；二者不混用。**
- 方案类型由服务端根据 `planId` 自动识别，无需传。
- 组织绩效走单方案模式；跨方案模式只支持个人绩效。
- 每次调用必须用 `--fields` 压缩返回字段，并按分页规则拉全。
- 查询结果受当前账号数据权限约束；**结果为空 ≠ 公司内绝对无数据**。

## 2. 模式选择（第一步判断，决定请求体骨架）

| 用户意图 | `searchMode` | 范围 | 组织绩效 |
|---|---|---|---|
| 「这个方案有哪些被考核人/部门」「已完成/已终止/在某环节的人」 | `PLAN_SUBJECTS` | 一个确定方案 | 支持 |
| 「张三历年的绩效记录」「查 2026 年所有个人绩效」 | `PERSONAL_PERFORMANCE_RECORDS` | 多个或全部个人方案 | 不支持 |
| 「这几个个人方案的人员与结果」 | `PERSONAL_PERFORMANCE_RECORDS` | `planIds` 指定的个人方案 | 不支持 |

**决策优先级：**
1. 用户指定**一个**方案（或问方案名单）→ `PLAN_SUBJECTS`。
2. 用户指定**多个**个人方案 / 明确要历史、跨方案、某年度全部绩效 → `PERSONAL_PERFORMANCE_RECORDS`。
3. 用户指定**多个组织绩效方案** → 逐个用 `PLAN_SUBJECTS` 查，Agent 合并，**不能放进一次跨方案请求**。
4. 用户同时指定个人 + 组织方案 → 个人方案合并一次跨方案请求；每个组织方案单独查；最后合并并标注对象类型。
5. 意图不明确且会改变查询口径 → 先用一句话问用户是「查某个方案名单」还是「跨方案个人绩效记录」。

**范围字段互斥表（防混用）：**

| 模式 | 必须传 | 禁止传 |
|---|---|---|
| `PLAN_SUBJECTS` | `planId` | `planIds`、`planTypes`、`sortOrders` |
| `PERSONAL_PERFORMANCE_RECORDS` | 无；可选 `planIds` | `planId`、组织绩效类型 `3` |

## 3. 前置定位（拿 planId）

- **用户已给 `planId`** → 直接用，不重复搜方案。
- **用户只给方案名** → 先 `batchQueryPlanInfos` 定位（话术含「组织绩效」用 `planType:3`、「试用期」用 `2`、否则 `1`；未给状态先搜进行中 `planStatus:1`，无结果再重试一次最可能状态；命中多候选 → 列方案让用户选，不猜）。

```bash
xrxs-cli appraisal batchQueryPlanInfos \
  --fields "planId,planName,planType,planTypeDesc,planStatus,planStatusDesc,planYear,planPeriodDesc" \
  --request-body '{"planType":1,"planStatus":1,"planName":"<方案名关键词>","pageNum":1,"pageSize":100}'
```

## 4. 请求体骨架（删除无用字段，不机械发 null）

```json
{
  "searchMode": "PLAN_SUBJECTS",
  "planId": "plan-id",
  "stage": { "mode": "ALL" },
  "keyword": null,
  "filters": null,
  "pageNum": 1,
  "pageSize": 100
}
```

## 5. `stage` 阶段条件

| `stage.mode` | 含义 | `flowId` | 支持模式 |
|---|---|---|---|
| `ALL` | 全部被考核对象（含正常/已完成/已终止） | 不传 | 两种 |
| `COMPLETED` | 已完成且未终止 | 不传 | 两种 |
| `TERMINATED` | 已终止 | 不传 | 两种 |
| `FLOW` | 当前处于指定流程的未终止记录 | **必填**（来自 `getPlanFlowList`） | 仅 `PLAN_SUBJECTS` |

- `stage.mode=FLOW` 的 `flowId` **必须**先调 `getPlanFlowList` 拿真实值。
- `ALL`/`COMPLETED`/`TERMINATED` 直接用即可，无需额外传 `flowId`。

## 6. `filters` 常用业务化筛选

| 参数 | 类型 | 适用范围 | 说明 |
|---|---|---|---|
| `assesseeIds` | string[] | 两种 | 被考核对象 ID（个人=员工 ID，组织=组织对象 ID，优先用 `assessBizId`） |
| `departmentIds` | string[] | 两种 | 部门 ID，按路径匹配，个人绩效可覆盖下级部门 |
| `jobIds` / `rankIds` | string[] | 仅个人绩效 | 岗位 / 职级 ID（组织绩效传会报错） |
| `hireTypes` / `employeeStatuses` | integer[] | 仅个人绩效 | 聘用形式 / 员工状态，**只用业务定义接口返回的真实值，不猜编号** |
| `planStatuses` | integer[] | — | 0 未开始 / 1 进行中 / 3 终止 / 4 已归档 |
| `planYear` | integer | — | 方案年度，如 2026 |
| `planPeriods` | integer[] | — | 周期枚举，先 `getPlanPeriodDefinitions` 取真实值，**不把月份当枚举** |
| `todoEmployeeIds` | string[] | — | 当前待办人 ID（仅匹配当前仍待处理的待办） |
| `finalScore` / `selfScore` / `systemScore` / `confirmScore` | score range | — | `{"min":80,"max":100}` 闭区间；至少传一个；min≤max |
| `finalLevels` / `selfLevels` / `systemLevels` / `confirmLevels` | string[] | — | 等级名称，**只用用户给出或业务返回的精确名称，不臆造** |
| `readStatuses` / `communicationStatuses` / `calibrationChanges` 等 | integer[] | — | 状态类筛选，见编排文档第 7.5 节，值用真实定义 |

**规则：** 多字段之间「并且」；同字段数组内「任一匹配」。所有数组 ≤100 项，ID 数组不含空字符串。

## 7. `sortOrders`（仅跨方案模式）

```json
{"sortOrders":[{"field":"planStartTime","order":"desc"}]}
```

`field`：`subjectName` / `entryDate` / `planPeriod` / `planStartTime` / `finalScore`；`order` 仅 `asc`/`desc`；同字段不重复。方案内查询沿用页面稳定排序，不接受自定义排序。

## 8. 场景速查请求体

### 8.1 查某个人绩效方案全部名单（场景六核心）

```bash
xrxs-cli appraisal queryAssesseeInfos \
  --fields "planId,planName,planType,assessBizId,employeeId,employeeName,jobNumber,department,flowName,inspectionStatus,assesseeStatus" \
  --request-body '{"searchMode":"PLAN_SUBJECTS","planId":"<planId>","stage":{"mode":"ALL"},"pageNum":1,"pageSize":100}'
```

### 8.2 查某组织绩效方案全部组织对象

```bash
xrxs-cli appraisal queryAssesseeInfos \
  --fields "planId,planName,planType,assessBizId,departmentId,department,departmentPathNameList,departmentAdminName,flowName,inspectionStatus,assesseeStatus" \
  --request-body '{"searchMode":"PLAN_SUBJECTS","planId":"<组织绩效planId>","stage":{"mode":"ALL"},"pageNum":1,"pageSize":100}'
```

> 方案类型由服务端根据 `planId` 自动识别为组织绩效。

### 8.3 查方案中已完成对象

```json
{"searchMode":"PLAN_SUBJECTS","planId":"<planId>","stage":{"mode":"COMPLETED"},"pageNum":1,"pageSize":100}
```

### 8.4 查方案中指定流程对象（先 getPlanFlowList）

```json
{"searchMode":"PLAN_SUBJECTS","planId":"<planId>","stage":{"mode":"FLOW","flowId":"<真实flowId>"},"pageNum":1,"pageSize":100}
```

### 8.5 查全部跨方案个人绩效记录

```bash
xrxs-cli appraisal queryAssesseeInfos \
  --fields "planId,planName,planType,planStatus,planPeriod,assessBizId,employeeId,employeeName,department,jobName,rank,finalScore,finalLevel" \
  --request-body '{"searchMode":"PERSONAL_PERFORMANCE_RECORDS","stage":{"mode":"ALL"},"sortOrders":[{"field":"planStartTime","order":"desc"}],"pageNum":1,"pageSize":100}'
```

### 8.6 定位某员工（场景七/九/十，单方案 + keyword）

```json
{"searchMode":"PLAN_SUBJECTS","planId":"<planId>","stage":{"mode":"ALL"},"keyword":"<员工姓名/工号>","pageNum":1,"pageSize":100}
```

### 8.7 指定方案 + 年度周期 + 分数范围

```json
{
  "searchMode": "PERSONAL_PERFORMANCE_RECORDS",
  "planIds": ["plan-1", "plan-2"],
  "stage": {"mode": "COMPLETED"},
  "filters": {"planYear": 2026, "planPeriods": [4,5,6,7], "finalScore": {"min":80,"max":100}},
  "sortOrders": [{"field":"finalScore","order":"desc"}],
  "pageNum": 1, "pageSize": 100
}
```

## 9. 返回字段与对象识别

- **个人绩效**：`planType` 为 1 或 2；用 `employeeId`/`employeeName`/`jobNumber`/`department`/`jobName`/`rank` 展示；`assessBizId` 对应员工业务 ID。
- **组织绩效**：`planType` 为 3；`employeeId`/`employeeName` 可能为空是**正常现象**；用 `assessBizId`（组织对象 ID）+ `departmentId`/`department`/`departmentPathNameList`/`departmentAdminName` 展示；**不得因员工字段为空丢弃组织绩效记录**。
- 分页外层：`status`/`code`/`message`/`data`/`recordsTotal`/`totalPageNum`。

### 9.1 字段值为星号（`*`）表示当前管理员无查看权限

返回结果中 `finalScore` / `selfScore` / `systemScore` / `confirmScore`（绩效分数）或 `finalLevel` / `selfLevel` / `systemLevel` / `confirmLevel`（绩效等级）等敏感字段，若显示为**星号（`*`）**，**不是数据缺失，也不是接口异常**，而是表示**当前登录的管理员对该被考核对象没有数据查看权限**（通常因为数据权限范围未覆盖该员工 / 部门）。

遇到星号时的处理规范：

- **照实展示星号**，不要臆造、猜测或回填分数 / 等级。
- **不要**据此断言该员工"未评分""等级未知"或"无绩效结果"——应明确向用户说明「该绩效分数 / 等级因当前账号权限限制不可见」。
- **不要**为了"补全"数据而调用其他接口换条件重查，或尝试切换账号查询。
- 若用户需要看到这些数据，提示其**联系有对应数据权限的管理员**，或确认并调整自身的数据权限范围。

> 注意区分两种不同情况：
> - **星号（`*`）**：有该被考核记录，但分数 / 等级字段因权限不可见（见本节）。
> - **返回为空**：当前账号权限与筛选条件下无匹配记录（见第 11 节「返回为空」），二者含义不同，不要混淆。

## 10. 分页拉全规则

1. 首次 `pageNum:1`、`pageSize:100`（最大 100）。
2. 当 `pageNum < totalPageNum` 时递增页码继续查。
3. 任一条件停止：当前页 `data` 空 / 条数 < pageSize / 页码达 totalPageNum / 累计达 recordsTotal。
4. 后续分页复用完全相同参数，只改 `pageNum`。
5. 合并时用 `planId + assessBizId` 去重（不能只按员工 ID，同一员工可在多个方案）。
6. 不得为"确认接口是否生效"重复请求同一页。

## 11. 异常与恢复

| 异常 | 处理 |
|---|---|
| 缺 `searchMode` | 按第 2 节重判，修正后只重试一次 |
| 单方案缺 `planId` | 先定位方案；不得改用空范围跨方案查询 |
| 跨方案传了 `planId` | 改 `planIds:[...]`；若只有一个确定方案且意图是名单 → 改 `PLAN_SUBJECTS` |
| 跨方案含组织绩效 | 组织方案拆成逐方案 `PLAN_SUBJECTS`；个人方案保留跨方案 |
| `FLOW` 缺 `flowId` | 调 `getPlanFlowList`，匹配唯一流程后重试 |
| 组织绩效传岗位/职级/聘用形式/员工状态 | 删除不适用条件；若该条件是用户核心意图则说明组织对象不支持 |
| 分数下限 > 上限 | 不执行，向用户指出冲突 |
| 返回为空 | 说明「当前账号权限和筛选条件下无结果」；不断言公司内无数据 |
| 返回被截断 | 检查是否漏 `--fields`；补上后重试当前页一次 |

## 12. 最终自检清单

- [ ] 已选唯一 `searchMode`。
- [ ] 单方案用 `planId`；跨方案用 `planIds`；未混用。
- [ ] 组织绩效未进跨方案模式。
- [ ] `FLOW` 的 `flowId` 来自 `getPlanFlowList`。
- [ ] 所有筛选在 `filters` 对应业务字段，枚举/ID/等级名称来自真实定义，没猜值。
- [ ] 已带 `--fields`，字段覆盖输出所需。
- [ ] 分页 ≤100，按停止条件拉全。
- [ ] 输出区分个人「人数」、组织「组织数」、跨方案「记录数」。
