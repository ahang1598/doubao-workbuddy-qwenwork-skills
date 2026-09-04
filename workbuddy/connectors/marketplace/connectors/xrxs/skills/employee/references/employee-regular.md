---
name: employee-regular
description: 员工转正相关操作，包括转正记录查询、试用期任务/参与人查询、转正保存与预览
---

# 员工转正

## 调用前准备

### 关于 `--request-body json`

本文档中部分 CLI 命令以 `--request-body json` 结尾，例如：

```bash
xrxs-cli employee saveRegular --request-body json
```

这里的 `json` **不是参数值**，而是声明该接口需要以 **JSON 格式**传入请求体。具体 JSON 结构请查看对应接口下方的「请求体说明」。

### 查看接口完整信息

本文档未覆盖的命令，可通过以下方式查看该接口的入参、返回值及使用明细（何时需要查 schema 的分级规则见 ../SKILL.md「查看接口完整信息」）：

```bash
xrxs-cli schema employee.<method>
```

例如：

```bash
xrxs-cli schema employee.saveRegular
```

这样可以获取该接口的字段类型、必填校验、示例值、返回结构等完整信息。

### 操作命令前置要求

本文档中的写入/提交类操作命令涉及人事变动，执行前必须确认用户意图。调用正式操作前，需按「预览接口」中的权限检查规则执行：用户已永久授权则可直接调用正式接口；未授权则必须先调用 preview 接口展示摘要，经用户确认后再执行。

## 表单数据与提交说明

`getRegularFormData` 直接返回每个员工的审批表单数据，结构为数组，每个元素含 `employeeId` 与 `groups`；`groups` 中的 `fields` 已包含当前字段值（含 `fieldValue`、`fieldValueId`、`fieldOldValue` 等）。

提交类命令（`saveRegularPreview`、`saveRegular`）构造请求体时：

1. 从 `getRegularFormData` 返回的 `data[]` 中按 `employeeId` 找到该员工的 `groups`；
2. 将用户需要修改的员工信息按 `fieldId` 覆盖到对应字段；
3. 最终请求体为 `{"employeeId": "<员工ID>", "groups": [<处理后的审批表单分组>]}` 的数组。

## 预览接口

以下 preview 接口用于在正式提交前向用户展示操作摘要。调用对应正式操作前，建议先执行权限检查判断用户是否已永久授权：

```bash
xrxs-cli permission check employee-saveRegular
```

- 若返回 `true`，说明用户已授权，可直接调用正式操作 `saveRegular`。
- 若返回 `false`，说明用户未授权，必须先调用 `saveRegularPreview` 展示操作摘要，等用户确认后再调用 `saveRegular`。

- `saveRegularPreview` → 对应正式操作 `saveRegular`

## saveRegularPreview / 批量转正预览

**描述**：批量转正预览。请求体需从 `getRegularFormData` 返回的 `groups` 为基础，覆盖用户本次需要修改的员工信息后提交；预览明细中部门名、预计转正日期优先从入参表单 `groups` 字段中取，表单未提交时回退 ES。

**CLI 命令示例**：
```bash
xrxs-cli employee saveRegularPreview --request-body json
```

**请求体说明**：
JSON 数组，元素类型为 object
数组元素包含以下字段：
- `employeeId` (string): 员工id
- `groups` (array): 审批表单分组列表
  结构与 `getRegularFormData` 返回的 `data[].groups` 一致，提交前需将用户修改按 `fieldId` 覆盖到对应字段。
  JSON 数组，元素类型为 object
  数组元素包含以下字段：
  - `groupId` (string): 分组id
  - `groupName` (string): 分组名称
  - `groupType` (integer): 分组类型
  - `fields` (array): 组字段列表
    JSON 数组，元素类型为 object
    数组元素包含以下字段：
    - `fieldId` (string): 字段id
    - `fieldName` (string): 字段名称
    - `fieldValue` (string): 字段值
    - `fieldValueId` (string): 字段值id
    - `fieldOldValue` (string): 变更前字段值
    - `fieldOldValueId` (string): 变更前字段值id
    - `labelName` (string): 字段显示名称
    - `require` (integer): 是否必填
    - `type` (integer): 字段类型
    - `files` (array): 附件列表（type=11 附件字段），每项含 fileKey/fileName/fileUrl；提交时按 fieldId 覆盖回模板字段的 files

## getEmployeeFilterFields / 获取员工数据搜索过滤条件字段

**描述**：获取员工数据搜索过滤条件字段返回的 FilterFieldModel 仅为筛选项「配置」(values/dateValues 为空)，
调用方按下方规则填值后，作为搜索接口(如 searchEmployee)的 filters 入参回传。
填值字段说明：
  values     - List<DataSourceBO>，通用填值字段，value 放 DataSourceBO.key
  dateValues - List<String>，仅日期类型使用
按 fieldFilterType 填值规则(@see EEmployeeListFieldFilterType)：
  1  日期        - 填 dateValues，2 个元素 [开始, 结束]，格式 yyyy/MM/dd 时间戳，单边留空用空串 ""
  2  数字        - 填 values，1 个元素，key 格式 "min~max"，分隔符支持半角 ~ 或全角 ～，单边留空如 "25~"
  3  文本        - 填 values，1 个元素，key 为关键词原文(模糊匹配)
  4  选项        - 填 values，1 个或多个元素，key 取 dataSource 候选项的 key，多选取多个
  6  地区(城市)   - 填 values，key 为地区id
  7  地区(县)    - 填 values，key 为地区id
  8  部门        - 填 values，key 为部门id，可多个
  9  虚拟部门    - 填 values，key 为部门id，可多个
  10 岗位        - 填 values，key 为岗位id，可多个
  11 员工        - 填 values，key 为员工id，可多个
  12 职级        - 填 values，key 为职级id，可多个
  23 多选        - 填 values，多个元素，key 取 dataSource 候选项的 key
  24 多级单选    - 填 values，1 个元素，key 为所选层级值
  25 多级多选    - 填 values，多个元素，key 为所选层级值

**CLI 命令示例**：
```bash
xrxs-cli employee getEmployeeFilterFields --filterBizType 3 --keyword 转正
```

> **keyword 筛选建议**：`getEmployeeFilterFields` 返回的字段数量通常很多，全量返回容易超过上下文长度限制。转正相关查询通常需用到「预计转正日期」「转正记录状态」「转正审批状态」「转正方式」等字段，优先使用 `--keyword 转正` 一次获取这些相关字段定义，避免返回全部无关字段导致截断。
>
> 若只需按单个字段（如仅按「预计转正日期」）过滤，可改用更精确的 `--keyword 转正日期`；**禁止用不同 `--keyword` 反复轮询**。

**参数说明**：
- `filterBizType` (string, 选填): 业务类型：1-员工搜索 2-入职记录 3-转正记录 4-调岗记录 5-离职记录
- `keyword` (string, 选填): 筛选项关键字，为空不过滤

## getProbationParticipants / 获取员工试用期考核参与人列表。

**描述**：获取员工试用期考核参与人列表。

**CLI 命令示例**：
```bash
xrxs-cli employee getProbationParticipants --employeeId 1001
```

**参数说明**：
- `employeeId` (string, 选填): 员工id

## getProbationTasks / 获取员工试用期任务列表

**描述**：获取员工试用期任务列表（含任务对应的考核评价）

**CLI 命令示例**：
```bash
xrxs-cli employee getProbationTasks --employeeId 1001
```

**参数说明**：
- `employeeId` (string, 选填): 员工id

## getRegularFormData / 批量获取员工转正表单数据

**描述**：批量获取员工转正表单数据。返回结果为数组，每个元素含 `employeeId` 与 `groups`；`groups[].fields` 已包含当前字段值，提交 `saveRegular` 时直接以其为基础覆盖用户修改即可。

**CLI 命令示例**：
```bash
xrxs-cli employee getRegularFormData --employeeIds 1001,1002,1003
```

**参数说明**：
- `employeeIds` (string, 必填): 员工id列表，必填，最多 50 个

## regularPreCheck / 批量转正前置校验

**描述**：批量转正前置校验。请求体需以 `getRegularFormData` 返回的 `groups` 为基础，覆盖用户本次需要修改的员工信息后提交。

**CLI 命令示例**：
```bash
xrxs-cli employee regularPreCheck --request-body json
```

**请求体说明**：
JSON 数组，元素类型为 object
数组元素包含以下字段：
- `employeeId` (string): 员工id
- `groups` (array): 审批表单分组列表
  结构与 `getRegularFormData` 返回的 `data[].groups` 一致，提交前需将用户修改按 `fieldId` 覆盖到对应字段。
  JSON 数组，元素类型为 object
  数组元素包含以下字段：
  - `groupId` (string): 分组id
  - `groupName` (string): 分组名称
  - `groupType` (integer): 分组类型
  - `fields` (array): 组字段列表
    JSON 数组，元素类型为 object
    数组元素包含以下字段：
    - `fieldId` (string): 字段id
    - `fieldName` (string): 字段名称
    - `fieldValue` (string): 字段值
    - `fieldValueId` (string): 字段值id
    - `fieldOldValue` (string): 变更前字段值
    - `fieldOldValueId` (string): 变更前字段值id
    - `labelName` (string): 字段显示名称
    - `require` (integer): 是否必填
    - `type` (integer): 字段类型
    - `files` (array): 附件列表（type=11 附件字段），每项含 fileKey/fileName/fileUrl；提交时按 fieldId 覆盖回模板字段的 files

> ⚠️ 写入/删除操作前必须确认用户意图。

## saveRegular / 批量转正保存提交

**描述**：批量转正保存提交。请求体需以 `getRegularFormData` 返回的 `groups` 为基础，覆盖用户本次需要修改的员工信息后提交。

**CLI 命令示例**：
```bash
xrxs-cli employee saveRegular --request-body json
```

**请求体说明**：
JSON 数组，元素类型为 object
数组元素包含以下字段：
- `employeeId` (string): 员工id
- `groups` (array): 审批表单分组列表
  结构与 `getRegularFormData` 返回的 `data[].groups` 一致，提交前需将用户修改按 `fieldId` 覆盖到对应字段。
  JSON 数组，元素类型为 object
  数组元素包含以下字段：
  - `groupId` (string): 分组id
  - `groupName` (string): 分组名称
  - `groupType` (integer): 分组类型
  - `fields` (array): 组字段列表
    JSON 数组，元素类型为 object
    数组元素包含以下字段：
    - `fieldId` (string): 字段id
    - `fieldName` (string): 字段名称
    - `fieldValue` (string): 字段值
    - `fieldValueId` (string): 字段值id
    - `fieldOldValue` (string): 变更前字段值
    - `fieldOldValueId` (string): 变更前字段值id
    - `labelName` (string): 字段显示名称
    - `require` (integer): 是否必填
    - `type` (integer): 字段类型
    - `files` (array): 附件列表（type=11 附件字段），每项含 fileKey/fileName/fileUrl；提交时按 fieldId 覆盖回模板字段的 files

> 📝 正式提交前，请先调用 `saveRegularPreview` 预览并确认操作摘要。

> ⚠️ 写入/删除操作前必须确认用户意图。

## searchRegularRecord / 搜索员工转正记录

**描述**：搜索员工转正记录

**CLI 命令示例**：
```bash
xrxs-cli employee searchRegularRecord --request-body json
```

**请求体说明**：
JSON 对象，包含以下字段：
- `pageNo` (integer): 页码，从1开始，默认1
- `filters` (array): 筛选条件，结构与「获取员工数据搜索过滤条件字段」接口返回值一致。
每个筛选项通过 values（多选/区间）/ dateValues（日期范围）携带选中值，转换复用员工列表筛选逻辑。
  JSON 数组，元素为筛选条件对象，结构请见 `getEmployeeFilterFields` 返回。
- `keyword` (string): 搜索关键字（姓名/手机号/工号等）
- `pageSize` (integer): 每页条数，默认20，上限100

> filters 字段需先从 `getEmployeeFilterFields` 获取筛选项配置，按规则填值后再作为本接口入参回传。

**返回字段枚举（重要）**：
- `regularRecordStatus` (integer): **转正记录状态**（@see ERegularRecordStatus）
  - `1` = 待转正
  - `2` = 已转正
  - `3` = 已超期
  - `4` = 未通过
- 排查逾期/应转正名单时，用 `regularRecordStatus != 2`（即待转正/已超期/未通过）筛选；`= 2` 表示已转正/已办结，应排除。
- 转正审批状态另有 `regularApprovalStatus` 字段，含义以 schema 实际返回为准。
