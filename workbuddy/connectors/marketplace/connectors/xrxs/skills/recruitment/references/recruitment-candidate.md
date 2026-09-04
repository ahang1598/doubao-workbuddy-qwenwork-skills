---
name: recruitment-candidate
description: 候选人简历管理，包括候选人/人才库列表查询、简历详情、筛选字段定义、简历可操作列表、简历推荐预览与正式推荐、人才库恢复与重新分配。
---

# 招聘 - 候选人简历

本场景覆盖候选人简历与人才库简历的查询、详情查看、筛选字段获取、操作前预判以及简历推荐能力。

### 查看接口完整信息

调用命令前，优先参考本文档中对该命令的入参、请求体格式及返回值的说明。如果文档已经描述得足够清晰、能够直接构造调用，则**不需要再执行** `xrxs-cli schema recruitment.<command>`。只有当文档中对某个命令的入参或返回值描述不明确、不足以完成调用时，才对该命令执行一次 `xrxs-cli schema recruitment.<command>` 进行确认。**仅对将要实际调用的命令做此检查**，同一命令最多检查一次；禁止为排查字段而批量轮询多个无关命令的 schema


例如：

```bash
xrxs-cli schema recruitment.getResumeList
```

---

## getResumeList

- **接口名称**：`getResumeList`
- **描述**：获取候选人列表（当前公司简历）
- **CLI 命令示例**：
  ```bash
  xrxs-cli recruitment getResumeList --request-body json
  ```
- **参数说明**（JSON body）：
  - `source`（integer，必填）：来源，`0` 全局搜索，`1` 待分配，`2` 候选人，`3` 人才库，`4` 人才推荐；默认 `0`。
  - `keyword`（string，可选）：搜索关键字（支持多词，用逗号或空格分隔，命中任一即匹配；如 `"设计 C++ 渲染 UI"`，一次查询覆盖多个关键词，避免多次调用）。
  - `pageNum`（integer，可选）：页码，缺省默认 `1`。
  - `pageSize`（integer，可选）：每页条数，缺省默认 `20`，最大支持 `100`。返回 `data.count` 为总条数，可据此动态调整分页：`count≤100` 可一次拉全，`count>100` 建议按 `100`/页分页拉取。
  - `sortMode`（integer，可选）：排序模式，`1` 智能排序，`2` 投递时间排序。
  - `queryTime`（integer，可选）：查询时间（详情页切换数据用）。
  - `stageType`（integer，可选）：自定义阶段类型，`0` 待分配，`1` 初筛，`2` 面试，`3` offer，`4` 入职，`5` 待入职，`6` 录用审批，`7` 业务筛选，`8` 背调，`9` 测评，`10` 考试，`900` 其他类型。引用 `xrxs-cli recruitment getProcessSettingDetail` 结果中的 `data.stages[].stageType`（描述见 `stageTypeDesc`）。
  - `customStageId`（integer，可选）：自定义阶段 ID，引用 `xrxs-cli recruitment getProcessSettingDetail` 结果中的 `data.stages[].stageId`。
  - `customProcessId`（integer，可选）：自定义流程 ID，引用 `xrxs-cli recruitment getProcessSettingList` 结果中的 `data.data.customProcessId`。
  - `talentCategory`（integer，可选）：人才库分类，`-1` 全部人才库，`0` 人才储备，`1` 已淘汰，`2` 黑名单，`3` 系统人才库，`6` 已入职。
  - `talentCompanyId`（string，可选）：分类所在公司（人才库公司 ID），仅 `getTalentResumeList` 使用时需传，`getResumeList` 不传。
  - `resumeLibraryStatus`（integer，可选）：简历状态，`-1` 其他，`0` 待分配，`6` 已入职，`7` 已转正，`8` 已离职，`9` 已归档，`10` 未处理，`11` 待定，`12` 已推荐，`13` 推荐通过，`14` 推荐未通过，`15` 待推荐，`16` 推荐已过期，`30` offer 待确认，`31` offer 已接受，`32` offer 已过期，`33` offer 已拒绝，`34` offer 已入职，`37` offer 待发送，`40` 背调待发起，`41` 背调中，`42` 背调已完成，`43` 背调已取消，`44` 背调失败，`50` 待入职，`52` 待入职已过期，`60` 审批中，`61` 审批通过，`62` 审批未通过，`63` 审批已撤销，`64` 审批待发起，`71` 测评待安排，`72` 测评中，`73` 测评已完成，`74` 测评已终止，`75` 测评未开始，`81` 考试待安排，`82` 考试已安排，`83` 考试通过，`84` 考试未通过，`2000` 待面试，`2001` 面试中，`2002` 面试未通过，`2003` 面试通过，`2004` 待约面。
  - `filters`（object[]，可选）：过滤条件数组，构造规则详见下述 `filters` 字段说明。
  - `sortOrders`（object[]，可选）：排序字段。
  - `defaultSortOrder`（object，可选）：默认排序。
  - `fields`（string，可选）：返回字段白名单（逗号分隔，只返回指定字段以减少传输）。不传时默认返回核心字段：`resumeId,name,mobile,degreeDesc,school,major,workAge,lastCompany,lastJob,industry,applyJobName,resumeLibraryStatusDesc,workCity,currentStatus`。支持字段见下方 **fields 白名单字段**。

### fields 白名单字段

不传 `fields` 时按接口默认返回；传入时只返回指定字段，多个字段用英文逗号分隔。

| 字段 | 含义 |
|---|---|
| `resumeId` | 简历 ID |
| `name` | 姓名 |
| `mobile` | 手机号 |
| `email` | 邮箱 |
| `wechat` | 微信号 |
| `headImage` | 头像 URL |
| `currentStatus` | 当前状态（离在职等） |
| `age` | 年龄 |
| `sex` | 性别（`0` 未知 `1` 男 `2` 女） |
| `sexDesc` | 性别描述 |
| `school` | 毕业院校 |
| `degree` | 学历（`0` 无 `1` 初中 `2` 高中 `3` 中专 `4` 大专 `5` 本科 `6` 硕士 `7` 博士 `8` 其他） |
| `degreeDesc` | 学历描述 |
| `major` | 专业 |
| `workAge` | 工作年限（年） |
| `birthPlaceId` | 生源地 ID |
| `birthPlaceDesc` | 生源地描述 |
| `workCityId` | 工作城市 ID |
| `workCity` | 工作城市 |
| `workStartDate` | 工作开始时间 |
| `lastCompany` | 上一家公司 |
| `lastJob` | 上一份职位 |
| `lastSalary` | 上一份薪资 |
| `industry` | 行业 |
| `applyJobName` | 应聘职位名称 |
| `applyJobId` | 应聘职位 ID |
| `applyJob` | 应聘职位 |
| `customProcessId` | 自定义流程 ID |
| `customProcessDesc` | 自定义流程描述 |
| `customStageId` | 自定义阶段 ID |
| `customStageDesc` | 自定义阶段描述 |
| `stageType` | 自定义阶段类型 |
| `stageTypeDesc` | 自定义阶段类型描述 |
| `resumeLibraryStatus` | 简历状态 |
| `resumeLibraryStatusDesc` | 简历状态描述 |
| `archiveStageId` | 归档阶段 ID |
| `archiveStageDesc` | 归档阶段描述 |
| `talentCategory` | 人才库分类 |
| `talentCategoryDesc` | 人才库分类描述 |
| `talentTime` | 人才库时间 |
| `giveUpReasonDesc` | 放弃原因描述 |
| `jobPositionName` | 职位名称 |
| `jobDepartmentName` | 部门名称 |
| `demandName` | 需求名称 |
| `gatePlanId` | 门户计划 ID |
| `channelType` | 渠道类型 |
| `channelDesc` | 渠道描述 |

示例：`{"fields":"resumeId,name,degreeDesc,applyJobName"}`。

### filters 字段构造规则

- `type`：字段类型，`1` 单选，`2` 多选，`3` 范围，`4` 多个范围。
- `field`：筛选字段 key，引用 `xrxs-cli recruitment getResumeFilterFields` 结果中的 `data.field`。
- `value`：`type=1` 时使用，单选值。
- `values`：`type=2` 时使用，多选值数组。
- `minValue`/`maxValue`：`type=3` 时使用，范围起始/结束值（日期为秒级时间戳）。
- `ranges`：`type=4` 时使用，多个范围（或关系），每项含 `minValue`/`maxValue`。

示例：
```json
[
  {"type":1, "field":"videoResumeMark", "value":1},
  {"type":2, "field":"sex", "values":[1]},
  {"type":3, "field":"applyTime", "minValue":1704038400, "maxValue":1719705600},
  {"type":4, "field":"age", "ranges":[{"minValue":25, "maxValue":30}]}
]
```

按职位筛选（多职位，或关系）：`field="applyJobIds"`，`type=2`，`values` 传多个职位 ID。
```json
[{"type":2, "field":"applyJobIds", "values":["职位ID1","职位ID2","职位ID3"]}]
```

---

## getTalentResumeList

- **接口名称**：`getTalentResumeList`
- **描述**：获取人才库候选人列表（查询集团人才库共享数据）
- **CLI 命令示例**：
  ```bash
  xrxs-cli recruitment getTalentResumeList --request-body json
  ```
- **参数说明**（JSON body）：与 `getResumeList` 一致，其中 `source` 通常为 `3`（人才库），`talentCompanyId` 必填。

---

## getResumeFilterFields

- **接口名称**：`getResumeFilterFields`
- **描述**：获取简历筛选字段定义（供 filters 构造参考）
- **CLI 命令示例**：
  ```bash
  xrxs-cli recruitment getResumeFilterFields
  ```
- **参数说明**：无。

---

## getResumeDetail

- **接口名称**：`getResumeDetail`
- **描述**：获取候选人详细信息（标准简历模型：基本信息 + 分组 + 自定义字段名值）
- **CLI 命令示例**：
  ```bash
  xrxs-cli recruitment getResumeDetail --resume-id RESUME_123456 --talent-company-id COMP_123
  ```
- **参数说明**：
  - `--resume-id`（string，可选）：简历 ID，引用 `getResumeList` / `getTalentResumeList` 结果中的 `data.data.resumeId`。
  - `--talent-company-id`（string，可选）：人才库公司 ID（共享人才库场景可选）。

---

## getResumeDetailOperations

- **接口名称**：`getResumeDetailOperations`
- **描述**：获取简历可操作列表（招聘操作前预判简历能否安排面试/推荐/发Offer 等）
- **CLI 命令示例**：
  ```bash
  xrxs-cli recruitment getResumeDetailOperations --resume-id RESUME_123456
  ```
- **参数说明**：
  - `--resume-id`（string，可选）：简历 ID，引用 `getResumeList` / `getTalentResumeList` 结果中的 `data.data.resumeId`。

**返回关键字段**：
- `operations`（object[]）：可操作列表。
  - `operationCode`（integer）：操作码，如 `11`=安排面试、`1`=推荐、`21`=录用审批、`31`=发送 Offer。
  - `operationName`（string）：操作名称。
  - `available`（boolean）：是否可用，`true` 可用，`false` 禁用（置灰）。
  - `disabledReason`（string）：禁用原因（可用时为空）。

---

## recommendResumePreview

- **接口名称**：`recommendResumePreview`
- **描述**：简历推荐预览（不实际推荐，返回汇总 + 明细供用户确认）
- **CLI 命令示例**：
  ```bash
  xrxs-cli recruitment recommendResumePreview --request-body json
  ```
- **参数说明**（JSON body）：
  - `resumeIds`（string，必填）：简历 ID，多个用逗号分隔，引用 `getResumeList` 结果中的 `data.data.resumeId`。
  - `employeeIds`（string，必填/与 `emails` 至少传一个）：接收人员工 ID，多个用逗号分隔，引用员工模块搜索接口结果中的员工 ID。
  - `emails`（string，必填/与 `employeeIds` 至少传一个）：推荐邮箱，多个用逗号分隔。
  - `recommendJobId`（string，可选）：推荐到职位 ID，引用 `getMyJobList` 结果中的 `data.data.jobId`。
  - `resumeType`（integer，可选）：推荐简历类型，`0` 原始简历&标准简历，`1` 原始简历，`2` 标准简历。
  - `validityDay`（integer，可选）：有效期（天）。
  - `viewSensitive`（integer，可选）：敏感字段访问权限，`0` 无权限，`1` 有权限。
  - `attachments`（integer，可选）：查看附件权限，`0` 无权限，`1` 有权限。
  - `comments`（integer，可选）：查看留言权限，`0` 无权限，`1` 有权限。
  - `deliveryAnalysis`（integer，可选）：投递分析权限，`0` 无权限，`1` 有权限。
  - `remark`（string，可选）：备注。

---

## recommendResume

> ⚠️ **写入操作**：调用前必须向用户确认推荐意图、接收人、推荐职位及简历范围，避免误操作。
> 
> 本操作存在预览接口 `recommendResumePreview`。调用正式接口前，先执行 `xrxs-cli permission check recruitment-recommendResume` 判断用户是否已授权永久允许执行该命令：
> - 若返回 `true`，说明用户已授权，可直接调用 `recommendResume`。
> - 若返回 `false`，说明用户未授权。此时有两种处理方式：
>   - 若用户希望永久授权，执行 `xrxs-cli permission save recruitment-recommendResume` 保存授权，之后即可直接调用 `recommendResume`。
>   - 若用户仅想单次确认，先调用 `recommendResumePreview` 展示操作摘要，等用户确认后再调用 `recommendResume`。

- **接口名称**：`recommendResume`
- **描述**：简历推荐（把候选人推荐给招聘负责人/面试官）
- **CLI 命令示例**：
  ```bash
  xrxs-cli recruitment recommendResume --request-body json
  ```
- **参数说明**（JSON body）：与 `recommendResumePreview` 一致。

**调用前确认项**：
1. 请确认要推荐的简历 ID 列表及对应候选人。
2. 请确认接收人员工 ID 或接收邮箱。
3. 请确认是否推荐到具体职位（`recommendJobId`）。
4. 请确认有效期、敏感字段/附件/留言/投递分析权限。

---

## recoverResumePreview

- **接口名称**：`recoverResumePreview`
- **描述**：人才库恢复到流程预览。明细一名候选人一行：候选人/手机号/邮箱/部门/应聘职位/来源/恢复后归属/流程环节。
- **CLI 命令示例**：
  ```bash
  xrxs-cli recruitment recoverResumePreview --resume-id RESUME_123456
  ```
- **参数说明**：
  - `--resume-id`（string，必填）：简历 ID，引用 `getResumeList` / `getTalentResumeList` 结果中的 `data.data.resumeId`。

**返回关键字段**：
- `detailData`（object[]）：明细数据列表。
- `summaryData`（object）：汇总数据。
- `detailHeaderMap`（object）：明细表头（fieldName → 中文标签）。
- `summaryHeaderMap`（object）：汇总表头（fieldName → 中文标签）。
- `detailHeaderShowField`（string[]）：明细展示字段顺序。
- `summaryHeaderShowField`（string[]）：汇总展示字段顺序。

---

## recoverResume

> ⚠️ **写入操作**：调用前必须向用户确认要恢复的简历及目标流程，避免误操作。
> 
> 本操作存在预览接口 `recoverResumePreview`。调用正式接口前，先执行 `xrxs-cli permission check recruitment-recoverResume` 判断用户是否已授权永久允许执行该命令：
> - 若返回 `true`，说明用户已授权，可直接调用 `recoverResume`。
> - 若返回 `false`，说明用户未授权。此时有两种处理方式：
>   - 若用户希望永久授权，执行 `xrxs-cli permission save recruitment-recoverResume` 保存授权，之后即可直接调用 `recoverResume`。
>   - 若用户仅想单次确认，先调用 `recoverResumePreview` 展示操作摘要，等用户确认后再调用 `recoverResume`。

- **接口名称**：`recoverResume`
- **描述**：人才库恢复到流程中（将人才库简历恢复到招聘流程）
- **CLI 命令示例**：
  ```bash
  xrxs-cli recruitment recoverResume --resume-id RESUME_123456
  ```
- **参数说明**：
  - `--resume-id`（string，可选）：简历 ID，引用 `getResumeList` / `getTalentResumeList` 结果中的 `data.data.resumeId`。

**调用前确认项**：
1. 请确认要恢复的简历 ID 及对应候选人。
2. 请确认恢复后该简历将重新进入招聘流程流转。

---

## copyTalentResumePreview

- **接口名称**：`copyTalentResumePreview`
- **描述**：人才库重新分配职位预览。明细一名候选人一行：候选人/手机号/邮箱/原职位/目标职位。
- **CLI 命令示例**：
  ```bash
  xrxs-cli recruitment copyTalentResumePreview --request-body json
  ```
- **参数说明**（JSON body）：
  - `jobId`（string，必填）：目标职位 ID，引用 `getMyJobList` 结果中的 `data.data.jobId`。
  - `resumeId`（string，必填）：简历 ID，引用 `getResumeList` / `getTalentResumeList` 结果中的 `data.data.resumeId`。
  - `talentCompanyId`（string，可选）：人才库公司 ID（共享人才库场景传入）。
  - `traceId`（string，可选）：追踪 ID。
  - `operationLocation`（string，可选）：操作位置（埋点用）。
  - `recommendMatchingId`（string，可选）：推荐匹配 ID（人才推荐场景传入，不传按空串处理）。

**返回关键字段**：
- `detailData`（object[]）：明细数据列表。
- `summaryData`（object）：汇总数据。
- `detailHeaderMap`（object）：明细表头（fieldName → 中文标签）。
- `summaryHeaderMap`（object）：汇总表头（fieldName → 中文标签）。
- `detailHeaderShowField`（string[]）：明细展示字段顺序。
- `summaryHeaderShowField`（string[]）：汇总展示字段顺序。

---

## copyTalentResume

> ⚠️ **写入操作**：调用前必须向用户确认源简历、目标职位及操作意图，避免误操作。
> 
> 本操作存在预览接口 `copyTalentResumePreview`。调用正式接口前，先执行 `xrxs-cli permission check recruitment-copyTalentResume` 判断用户是否已授权永久允许执行该命令：
> - 若返回 `true`，说明用户已授权，可直接调用 `copyTalentResume`。
> - 若返回 `false`，说明用户未授权。此时有两种处理方式：
>   - 若用户希望永久授权，执行 `xrxs-cli permission save recruitment-copyTalentResume` 保存授权，之后即可直接调用 `copyTalentResume`。
>   - 若用户仅想单次确认，先调用 `copyTalentResumePreview` 展示操作摘要，等用户确认后再调用 `copyTalentResume`。

- **接口名称**：`copyTalentResume`
- **描述**：人才库重新分配职位（将人才库简历备选到目标职位，生成新简历）
- **CLI 命令示例**：
  ```bash
  xrxs-cli recruitment copyTalentResume --request-body json
  ```
- **参数说明**（JSON body）：
  - `jobId`（string，必填）：目标职位 ID，引用 `getMyJobList` 结果中的 `data.data.jobId`。
  - `resumeId`（string，必填）：简历 ID，引用 `getResumeList` / `getTalentResumeList` 结果中的 `data.data.resumeId`。
  - `talentCompanyId`（string，可选）：人才库公司 ID（共享人才库场景传入）。
  - `traceId`（string，可选）：追踪 ID。
  - `operationLocation`（string，可选）：操作位置（埋点用）。
  - `recommendMatchingId`（string，可选）：推荐匹配 ID（人才推荐场景传入，不传按空串处理）。

**调用前确认项**：
1. 请确认源简历 ID 及对应候选人。
2. 请确认目标职位 ID。
3. 请确认是否为共享人才库场景（如需传入 `talentCompanyId`）。

