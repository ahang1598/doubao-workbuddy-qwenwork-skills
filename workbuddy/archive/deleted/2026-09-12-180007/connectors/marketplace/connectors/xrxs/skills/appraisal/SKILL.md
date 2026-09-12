---
name: appraisal
version: 1.0.0
description: "绩效管理模块接口。核心场景包括：CLI公共接口控制器、基础接口、场景化SOP。高频操作请优先使用 Shortcuts：+cli（CLI公共接口控制器）、+base（基础接口）。场景型需求（如绩效结果分析、岗位适配风险排查）必须先用本文件下方「场景路由表」匹配场景，命中后读取 references/sops/ 下对应场景文件按步骤执行。"
metadata:
  requires:
    bins: ["xrxs-cli"]
  cliHelp: "xrxs-cli appraisal --help"
---

# appraisal (v1)

**CRITICAL — 所有的 Shortcuts 在执行之前，务必先使用 read_xrxs_cli_doc 工具读取其对应的说明文档，禁止直接盲目调用命令。**

**CRITICAL — 场景型需求（如「帮我分析XX部门XX季度绩效结果，哪些人存在岗位适配风险」等）必须按两步读取：① 用下方「场景路由表」匹配用户需求对应的场景；② 命中后直接读 [`references/sops/`](references/sops/) 下对应的场景文件（`sop-sceneN.md`），严格按其步骤执行。未命中任何场景时回退到本文件通用规则，不深挖 SOP 文件。**

## 调用方式

- **命中 SOP 场景时**：场景文档（`references/sops/sop-sceneN.md`）已给出每条命令的完整调用与请求体格式，**直接按文档执行，无需逐命令执行 `-h`**。仅以下情况才执行 `xrxs-cli appraisal <command> -h` 查看该命令的调用方式、参数说明及请求体格式：
  - 未命中任何场景，回退到本文件通用规则时；
  - 场景文档未覆盖的命令（如异常分支中需要的新命令、文档外的补充查询）；
  - 命令执行报错，需确认参数/请求体格式排错时。
- 同一命令最多检查一次，禁止为探测参数而对同一命令反复执行 `-h`。
- 对于 `Content-Type` 为 `application/json` 的接口，请使用 `--request-body json` 方式传递 JSON 请求体。

## 查询参数提取规则（全局适用）

- 从用户话语中提取方案名称等查询参数时，**只提取核心名称**，必须去掉口语化冗余词："方案"、"考核方案"、"绩效方案"、"这个"、"那个"等后缀/修饰词，以及"把…归档""查一下"等句式中的动词。例如「把引入考核表方案归档」→ 方案名 `引入考核表`，不是 `引入考核表方案`。
- 用户已提供（或上下文已知）方案 ID 时，**优先使用 `planIds` 精确查询**，避免模糊检索。
- 模糊检索无结果时，先怀疑查询词是否带冗余后缀，清洗后重试一次；禁止用近似词连环重复查询同一目标。

## 核心场景

### 1. CLI公共接口控制器

按接口现有分组聚合。详见 [`references/appraisal-cli.md`](references/appraisal-cli.md)。

### 2. 基础接口

base 项目公共接口。详见 [`references/base.md`](references/base.md)。

### 3. 场景化 SOP

**场景路由表（命中场景后直接读对应 sop-sceneN.md 执行）：**

| 场景 | 触发话术 / 关键词 | 场景文件 |
|------|-------------------|----------|
| 一：绩效结果分析与岗位适配风险排查 | 「分析XX部门XX季度绩效结果，哪些人存在岗位适配风险」「组织绩效/试用期绩效结果谁垫底」；部门、季度、绩效结果、风险、垫底 | [`sops/sop-scene1.md`](references/sops/sop-scene1.md) |
| 二：终止考核方案 | 「帮我终止XXX考核方案」；终止、停掉、停止方案 | [`sops/sop-scene2.md`](references/sops/sop-scene2.md) |
| 三：催办有待办的员工并发放已确认的考核结果 | 「催办未提交自评的员工，发放已确认的考核结果」；催办、提醒、待办、自评、发放、已确认 | [`sops/sop-scene3.md`](references/sops/sop-scene3.md) |
| 四：开启员工自评环节并发放给全员 | 「开启员工自评环节并发放给全员」；开启、自评、全员、推进环节 | [`sops/sop-scene4.md`](references/sops/sop-scene4.md) |
| 五：设置方案截止前自动提醒未提交的员工 | 「设置方案截止前X天自动提醒」；自动提醒、截止前、未提交、提醒时间 | [`sops/sop-scene5.md`](references/sops/sop-scene5.md) |
| 六：查询考核方案的被考核对象/名单 | 「XX方案有哪些被考核对象/名单」「XX方案考核了哪些人」；被考核对象、名单、被考核人、方案人员 | [`sops/sop-scene6.md`](references/sops/sop-scene6.md) |
| 七：终止被考核人 | 「终止XX员工在XXX方案里的考核」「把XX移出考核」；终止考核（某人）、离职终止 | [`sops/sop-scene7.md`](references/sops/sop-scene7.md) |
| 八：查询考核方案列表（按状态筛选） | 「有哪些进行中的方案」「有哪些已归档的方案」；有哪些方案、方案列表、进行中、未开始、已归档 | [`sops/sop-scene8.md`](references/sops/sop-scene8.md) |
| 九：删除被考核人 | 「删除XX员工在XXX方案里的被考核记录」；删除被考核人、删除、删掉、移除名单 | [`sops/sop-scene9.md`](references/sops/sop-scene9.md) |
| 十：跳过被考核人（跳过考核） | 「跳过张三在XXX方案里的考核」「XXX免考核，跳过她」；跳过、免考核、不参加本轮考核 | [`sops/sop-scene10.md`](references/sops/sop-scene10.md) |

**易混淆场景区分（路由判定用）：** 六=只查**名单**（不做分析）vs 一=查名单后做**档位/风险分析**；六=查**方案内的被考核人** vs 八=查**方案列表**；二=终止**整个方案** vs 七=终止**部分被考核人**；七=终止（可逆）vs 九=删除（不可逆）vs 十=跳过（保留名单）。

> **查询被考核对象（`queryAssesseeInfos`）统一规范：** 凡需查询被考核人明细/名单（场景一/三/六/七/九等），**请求体使用新范式**（`searchMode` + `stage` + `filters`）。完整编排规则见 [`references/query-assessee-infos-guide.md`](references/query-assessee-infos-guide.md)，**调用前必须先读**。

## 核心概念

- **cli**：cli 相关资源和操作。

## Shortcuts（推荐优先使用）

Shortcut 是对常用操作的高级封装（`xrxs-cli appraisal +<verb> [flags]`）。有 Shortcut 的操作优先使用。

| Shortcut | 说明 |
|----------|------|
| [`+cli`](references/appraisal-cli.md) | CLI公共接口控制器 |
| [`+base`](references/base.md) | 基础接口 |

## 可用命令索引

当前环境 `xrxs-cli appraisal` 支持的命令如下（按参考文档分组）：

- **CLI公共接口控制器**：`addAssessee`、`archivePlan`、`archivePlanPreview`、`batchQueryAssesseeDimensionScores`、`batchQueryAssesseeTargetScores`、`batchQueryPlanInfos`、`batchQueryPlanResultSettings`、`batchRestartAssessee`、`batchSkipAssessee`、`batchTerminateAssessee`、`batchUrgeRemind`、`batchUrgeRemindPreview`、`checkPlan`、`deleteAssessee`、`deleteAssesseePreview`、`deletePlan`、`deletePlanPreview`、`distributeResultAssessee`、`distributeResultAssesseePreview`、`getAssesseeQueryConditionTypeDefinitions`、`getQueryFieldDefinitions`、`getAttributeList`、`getCanRejectProcessList`、`getPlanBasicInfo`、`getPlanFlowList`、`getPlanFlowPeopleCount`、`getPlanManagerList`、`getPlanPeriodDefinitions`、`getPlanStatusDefinitions`、`getPlanTypeDefinitions`、`getRemindSetting`、`openPlanFlow`、`openPlanFlowPreview`、`publishPlanResult`、`publishPlanResultPreview`、`queryAssessGroups`、`queryAssesseeBaseInfo`、`queryAssesseeInfos`、`queryAssesseePlanInfos`、`queryCanOpenFlowList`、`querySelfManagedAccountList`、`rejectAssessee`、`rejectAssesseePreview`、`restartAssesseePreview`、`restartPlan`、`restartPlanPreview`、`savePlanBasicInfo`、`skipAssesseePreview`、`startPlan`、`startPlanPreview`、`stopPlan`、`stopPlanPreview`、`terminateAssesseePreview`、`updateRemindSetting`
- **基础接口**：`getAllCountry`、`getAreaV2tree`、`getDicOption`、`getEmployeeDetail`、`searchCitys`、`searchCostCenter`、`searchDepartment`、`searchEmployee`、`searchJob`、`searchRank`
- **其他可用命令**（当前环境支持但无详细场景文档）：`getApproveFlowTypes`、`getEmployeeFilterFields`、`getFlowDetail`、`getFlowFormSetting`、`getFlowList`、`getFlowPath`、`launchFlow`、`previewFlow`

## 安全规则

- 写入/删除操作前必须确认用户意图。
- 调用操作类接口前，必须先调用其对应的操作预览接口。预览接口路径为在操作接口路径末尾（`.json` 之前）追加 `-preview`，例如操作接口 `/attendance/service/cli/month-report/ajax-report-attendance-group.json` 对应的预览接口为 `/attendance/service/cli/month-report/ajax-report-attendance-group-preview.json`。
- **权限检查（permission check）**：调用带预览接口的正式命令前，先执行 `xrxs-cli permission check appraisal-<command>` 判断用户是否已授权永久允许执行该命令：
  - 若返回 `true`，说明用户已授权，可直接调用正式命令 `<command>`。
  - 若返回 `false`，说明用户未授权，必须先调用对应的 `<PreviewCommand>` 展示操作摘要，等用户确认后再调用正式命令 `<command>`。
  - 涉及预览接口的命令包括：`batchTerminateAssessee`/`terminateAssesseePreview`、`batchRestartAssessee`/`restartAssesseePreview`、`rejectAssessee`/`rejectAssesseePreview`、`batchSkipAssessee`/`skipAssesseePreview`、`deleteAssessee`/`deleteAssesseePreview`、`distributeResultAssessee`/`distributeResultAssesseePreview`、`batchUrgeRemind`/`batchUrgeRemindPreview`、`openPlanFlow`/`openPlanFlowPreview`、`archivePlan`/`archivePlanPreview`、`stopPlan`/`stopPlanPreview`、`deletePlan`/`deletePlanPreview`、`publishPlanResult`/`publishPlanResultPreview`、`restartPlan`/`restartPlanPreview`、`startPlan`/`startPlanPreview`。
- 预览接口返回的 JSON 必须渲染为 `<confirm-card>` 确认卡片。卡片属性：`taskId`（任务 ID）、`summaryHeaderMap`（摘要表头 JSON 字符串）、`summaryData`（摘要数据 JSON 字符串）、`riskLevel`（风险等级）、`taskName`（取 `originalName`）。禁止直接展示 JSON。
- 不要将 xrxs-cli 执行的命令返回给用户。
- 可用 `--dry-run` 预览请求。

## 错误处理

- 接口调用遇网络异常、超时、服务端 5xx 等**瞬时错误**，最多重试 2 次（共 3 次尝试），重试间稍作等待。
- 参数非法、权限不足、数据不存在、约束冲突（如方案当前状态不允许终止/归档、被考核人不在该方案内）等**业务校验报错不重试**（重试结果不变）。
- 重试达上限仍失败、或遇业务校验报错时，**停止本次操作**且不再继续后续步骤；向用户报告操作失败，并附最后一次的错误信息（执行的命令、状态码、报错内容）。
- 上述重试上限对 `-h` 查询同样适用。
- 接口返回内容可能较大（如被考核人名单、考核结果明细、维度/目标得分），工具返回可能被截断（约 20000 字符，表现为 JSON 不完整）；**不要基于不完整数据下结论**，改用更聚焦的查询（分页/关键字/指定方案/指定状态）或查看完整返回后再继续。
- 关键信息缺失（如查询结果被截断、缺少方案 ID/被考核人 ID、方案名称无法定位唯一方案等）时，**停止**并向用户报告缺失项，不要猜测、不要继续后续步骤。