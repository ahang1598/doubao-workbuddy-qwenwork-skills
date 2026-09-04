---
name: employee
version: 1.0.0
description: 员工信息查询更新 、入转调离等业务：支持员工入职、转正、调岗、离职及基础信息查询与更新。场景型需求（如应转正员工风险排查、离职阻塞清单等）必须先读取 references/sop-summary.md 匹配场景，命中后读取 references/sops/ 下对应场景文件按步骤执行。
metadata:
  requires:
    bins: ["xrxs-cli"]
  cliHelp: "xrxs-cli employee --help"
---

# 员工信息查询更新 、入转调离等业务

**CRITICAL — 场景匹配是第一步，任何员工业务需求（含查询类）都必须先做：① 读 [`references/sop-summary.md`](references/sop-summary.md) 用用户话术匹配场景索引；② 命中 → 再读 [`references/sops/`](references/sops/) 下对应 `sop-sceneN.md`，严格按步骤执行；未命中 → 回退本文件通用规则。**

> ⚠️ **常见误区（必须避免）**：
> - **"看起来像简单查询"也要先匹配**：「检查本月入职人员信息」「查转正记录」「查离职记录」「查调岗记录」「扫描离职阻塞」等都是 SOP 场景，**禁止**跳过 summary 直接按 shortcut 文档自行摸索。
> - **禁止**在命中场景后执行 `schema` 查参数（场景文档已给完整请求体）；**禁止**反复用不同 `status` 试探同一接口（场景文档已指定取值，如 status=0 在职）。
> - 若你已读了 shortcut 文档（employee-entry/basic/base/update 等）却未读 sop-summary.md，**说明匹配步骤被跳过**，请立即补读 summary 再继续。

## 产品能力

员工信息查询更新 、入转调离等业务 提供员工全生命周期管理能力，核心场景包括：

- **员工基础能力**：员工基础信息查询能力，包括国家、人事规则、筛选字段、员工搜索与详情
- **员工离职**：员工离职相关操作，包括离职记录查询、交接触发、离职表单保存
- **员工入职**：员工入职相关操作，包括入职记录查询、待入职员工录入与校验、入职表单获取
- **员工转正**：员工转正相关操作，包括转正记录查询、试用期任务/参与人查询、转正保存
- **员工调岗**：员工调岗相关操作，包括调岗记录查询、调岗保存与表单获取
- **员工更新**：员工信息更新相关操作，包括字段更新、校验与表单获取
- **基础支撑接口**：基础支撑与引用接口，包括数据词典、地区城市、部门岗位职级成本中心查询

## 核心 Shortcuts

- `employee-basic` → [员工基础能力](references/employee-basic.md)
- `employee-dismiss` → [员工离职](references/employee-dismiss.md)
- `employee-entry` → [员工入职](references/employee-entry.md)
- `employee-regular` → [员工转正](references/employee-regular.md)
- `employee-transfer` → [员工调岗](references/employee-transfer.md)
- `employee-update` → [员工更新](references/employee-update.md)
- `employee-base` → [基础支撑接口](references/employee-base.md)

## 调用前准备

### 关于 `--request-body json`

references 文档中部分 CLI 命令以 `--request-body json` 结尾，例如：

```bash
xrxs-cli employee saveDismissForm --request-body json
```

这里的 `json` **不是参数值**，而是声明该接口需要以 **JSON 格式**传入请求体。具体 JSON 结构请查看对应接口下方的「请求体说明」，或通过下面的 `xrxs-cli schema` 命令获取完整示例。

### 查看接口完整信息

**命中 SOP 场景时**：场景文档（`references/sops/sop-sceneN.md`）已给出每条命令的完整调用与请求体格式，**直接按文档执行，无需逐命令执行 schema**。仅以下情况才通过 schema 查看该接口的入参、返回值及使用明细：

- 未命中任何场景，回退到本文件通用规则时；
- 场景文档未覆盖的命令（如异常分支中需要的新命令、文档外的补充查询）；
- 命令执行报错，需确认参数/请求体格式排错时。

```bash
xrxs-cli schema employee.<method>
```

例如：

```bash
xrxs-cli schema employee.saveDismissForm
```

这样可以获取该接口的字段类型、必填校验、示例值、返回结构等完整信息。同一命令最多检查一次，禁止为排查字段而批量轮询多个无关命令的 schema。

### 权限预检（permission check）

员工模块的写入/提交类操作命令在执行前，建议先判断用户是否已永久授权：

```bash
xrxs-cli permission check employee-<command>
```

- 若返回 `true`，说明用户已授权，可直接调用 `<command>`。
- 若返回 `false`，说明用户未授权，必须先调用对应的 `<PreviewCommand>` 展示操作摘要，等用户确认后再调用 `<command>`。

涉及预览接口的命令包括：

- `saveDismissForm` / `saveDismissFormPreview`
- `entryPendingEmployee` / `entryPendingEmployeePreview`
- `saveRegular` / `saveRegularPreview`
- `saveTransfer` / `saveTransferPreview`
- `updateEmployeeFields` / `updateEmployeeFieldsPreview`

## 安全规则

- 所有真正写入、更新、删除或触发人事变动的操作前，必须向用户确认意图。
- 不执行批量或无法撤销的破坏性操作，除非用户明确授权。
- 敏感字段（如个人身份信息、薪资等）查询结果仅用于当前会话上下文，不持久化。
- **已离职员工不得进行入职、转正、调岗、离职等人事变动操作；执行入转调离相关操作前，应先校验员工在职状态。**

## 错误处理

- 接口调用遇网络异常、超时、服务端 5xx 等**瞬时错误**，最多重试 2 次（共 3 次尝试），重试间稍作等待。
- 参数非法、权限不足、数据不存在、约束冲突（如已离职员工办理人事变动、入职/转正校验不通过）等**业务校验报错不重试**（重试结果不变）。
- 重试达上限仍失败、或遇业务校验报错时，**停止本次操作**且不再继续后续步骤；向用户报告操作失败，并附最后一次的错误信息（执行的命令、状态码、报错内容）。
- 上述重试上限对 `schema` 查询同样适用。
- 接口返回内容可能较大（如员工列表、批量表单数据），工具返回可能被截断（约 20000 字符，表现为 JSON 不完整）；**不要基于不完整数据下结论**，改用更聚焦的查询（分页/关键字/更小日期范围）或查看完整返回后再继续。
- 关键信息缺失（如查询结果被截断、缺少 employeeId、表单数据/校验结果不完整等）时，**停止**并向用户报告缺失项，不要猜测、不要继续后续步骤。

## 查询效率与冗余调用提示

回答用户问题时，应优先判断已返回的数据是否足够。若一次查询已能提供用户所需的信息，则无需为了补充非必要字段而对每条记录发起级联详情调用。

**员工场景示例**：

- 用户问“帮我查询今年三月到 5 月 3 日待入职的员工有哪些”时，调用 `xrxs-cli employee searchEntryRecord --request-body json` 返回的入职记录列表通常已包含姓名、预计入职日期、部门、聘用形式等关键信息，足以直接回答该问题，不必再对每个待入职员工调用 `getEntryPendingEmployeeForm` 获取表单详情。
- 用户只要「按状态查名单」（如已超期未转正员工，场景一）时，**只展示 `searchRegularRecord` 返回的人员信息**，其他信息（部门/岗位/入职日期等）一律不额外查询——即使返回看起来"不完整"也直接输出已有字段，不要发起任何额外查询。**也不要为了排序/算天数把名单数据抄写进 python 代码**（搬运易抄漏且耗时），直接基于返回结果组织答案。
- 用户或上下文已提供待入职员工 ID（如「给 ID 为 xxx、yyy 的两位员工办理入职」）时，直接调用 `xrxs-cli employee getEntryPendingEmployeeForm --employeeIds xxx,yyy` 批量获取表单即可，**不要**再用手机号/姓名去 `searchEmployee` 反查；一次批量查询已覆盖全部目标员工后，也禁止对单个员工重复调用 `getEntryPendingEmployeeForm`。
- 用户仅提供姓名/手机号/工号等关键字（如「给张三办理入职」）而未提供待入职员工 ID 时，应先调用 `xrxs-cli employee searchEntryRecord` 在**待入职记录列表**中搜索匹配人员，获取 `employeeId` 后再继续走 `getEntryPendingEmployeeForm` → `entryPendingEmployeePreview` → 用户确认 → `entryPendingEmployee`。**不要**用 `searchEmployee` 搜索在职员工列表来办理入职。
- 如果某个详情字段确实对回答至关重要，可以先针对一条记录调用一次 `getEntryPendingEmployeeForm` 评估其价值；若发现返回内容对当前问题帮助不大，应停止继续查询其余记录的详情，避免冗余调用。

简言之：**先判断已有数据是否足够，足够则不再发起额外查询；不足以回答时，再有针对性地补充查询。**

## 接口索引

### 员工基础能力 (`employee-basic`)

- `getHumanRules`：获取公司人事规则列表
- `getAllCountry`：获取所有国家
- `getEmployeeFilterFields`：获取员工数据搜索过滤条件字段返回的 FilterFieldModel 仅为筛选项「配置」(values/dateValues 为空)，
- `searchEmployee`：搜索员工
- `getEmployeeDetail`：获取员工详情

### 员工离职 (`employee-dismiss`)

- `saveDismissFormPreview`：批量离职预览明细中预计离职日期从入参表单取（与保存同源，按 fieldName=dismissionDate 提取）。
- `getDismissFormData`：批量获取员工离职表单数据
- `getDismissPendingIssueTotal`：获取员工离职待处理事项
- `getEmployeeFilterFields`：获取员工数据搜索过滤条件字段返回的 FilterFieldModel 仅为筛选项「配置」(values/dateValues 为空)，
- `getEmployeeFormData`：批量获取员工表单数据
- `getMatchedHandoverPlan`：获取员工匹配的离职交接方案。
- `saveDismissForm`：批量员工离职提交
- `searchDismissRecord`：搜索员工离职记录
- `triggerHandover`：发起员工离职交接

### 员工入职 (`employee-entry`)

- `entryPendingEmployeePreview`：批量待入职员工入职预览明细中姓名/手机号/入职日期/部门/聘用形式优先取提交表单数据，表单未提交时回退 ES。
- `entryPendingEmployee`：批量待入职员工入职
- `getEmployeeFilterFields`：获取员工数据搜索过滤条件字段返回的 FilterFieldModel 仅为筛选项「配置」(values/dateValues 为空)，
- `getEntryPendingEmployeeForm`：批量获取待入职员工入职表单数据
- `searchEntryRecord`：搜索员工入职记录
- `validateEntryPendingEmployee`：批量待入职员工入职校验

### 员工转正 (`employee-regular`)

- `saveRegularPreview`：批量转正预览明细中部门名、预计转正日期优先从入参表单 flowGroups 字段中取，表单未提交时回退 ES。
- `getEmployeeFilterFields`：获取员工数据搜索过滤条件字段返回的 FilterFieldModel 仅为筛选项「配置」(values/dateValues 为空)，
- `getProbationParticipants`：获取员工试用期考核参与人列表。
- `getProbationTasks`：获取员工试用期任务列表（含任务对应的考核评价）
- `getRegularFormData`：批量获取员工转正表单数据
- `regularPreCheck`：批量转正前置校验
- `saveRegular`：批量转正保存提交
- `searchRegularRecord`：搜索员工转正记录

### 员工调岗 (`employee-transfer`)

- `saveTransferPreview`：批量调岗预览
- `getEmployeeFilterFields`：获取员工数据搜索过滤条件字段返回的 FilterFieldModel 仅为筛选项「配置」(values/dateValues 为空)，
- `getTransferFormData`：批量获取员工调岗表单数据
- `saveTransfer`：批量调岗保存提交
- `searchTransferRecord`：搜索员工调岗记录

### 员工更新 (`employee-update`)

- `updateEmployeeFieldsPreview`：批量更新员工信息预览
- `getEmployeeFormData`：批量获取员工表单数据
- `updateEmployeeFields`：批量更新员工信息仅支持更新顶部字段（非分组字段）
- `validateEmployeeFields`：批量更新员工信息校验

### 基础支撑接口 (`employee-base`)

- `getDicOption`：获取词典选项信息（CLI 版）
- `getAreaV2tree`：获取城市信息树（CLI 版）。
- `searchCitys`：根据关键字搜索城市
- `getEmployeeDetail`：获取员工详情
- `getAllCountry`：获取所有国家
- `searchDepartment`：搜索部门
- `searchJob`：搜索岗位
- `searchRank`：搜索职级
- `searchCostCenter`：搜索成本中心

### 批量操作 (`employee-batch`)

- `batchListBizTypes`：获取批量excel操作支持的业务
- `batchInit`：批量excel初始化
- `batchDownloadTemplate`：下载批量excel模板
- `batchParseExcel`：解析批量excel
- `batchPreCheckField`：批量excel预检字段
- `batchPreCheckBatch`：批量excel预检
- `batchUploadBatchPreview`：批量excel上传预览确认
- `batchUploadBatch`：批量excel上传
- `batchQueryBatchResult`：查询批量excel上传结果

## 典型场景（SOP）

场景型需求的编排步骤见 [`references/sop-summary.md`](references/sop-summary.md)（场景匹配索引）与 [`references/sops/`](references/sops/)（分场景详细步骤，通用约定见 [`references/sops/common.md`](references/sops/common.md)）。**任何员工业务需求（含查询类）都必须先读 summary 匹配场景，命中后再读 sops/ 下对应场景文件执行，禁止跳过匹配直接按 shortcut 文档自行摸索。** 当前已收录 5 个场景：

- 场景一：员工转正记录查询与分析（按时间窗口/状态/关键字查询，结合转正方式、转正审批状态与转正规则开关分析）
- 场景二：入职信息查询与资料补齐检查（已入职名单 / 待入职资料补齐）
- 场景三：批量入职
- 场景四：扫描指定周期内离职办理阻塞清单
- 场景五：批量操作 Excel（教育/工作/培训/证书/联系人/手机号/兼职/自定义分组/子女/员工/成长记录/期权/离职/待入职/奖惩等）

## 参考文档

- [员工基础能力](references/employee-basic.md)
- [员工离职](references/employee-dismiss.md)
- [员工入职](references/employee-entry.md)
- [员工转正](references/employee-regular.md)
- [员工调岗](references/employee-transfer.md)
- [员工更新](references/employee-update.md)
- [基础支撑接口](references/employee-base.md)
