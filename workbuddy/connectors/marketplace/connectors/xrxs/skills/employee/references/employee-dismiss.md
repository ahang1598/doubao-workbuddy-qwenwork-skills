---
name: employee-dismiss
description: 员工离职相关操作，包括离职记录查询、交接触发、离职表单保存与预览
---

# 员工离职

## 调用前准备

### 关于 `--request-body json`

本文档中部分 CLI 命令以 `--request-body json` 结尾，例如：

```bash
xrxs-cli employee saveDismissForm --request-body json
```

这里的 `json` **不是参数值**，而是声明该接口需要以 **JSON 格式**传入请求体。具体 JSON 结构请查看对应接口下方的「请求体说明」。

### 查看接口完整信息

本文档未覆盖的命令，可通过以下方式查看该接口的入参、返回值及使用明细（何时需要查 schema 的分级规则见 ../SKILL.md「查看接口完整信息」）：

```bash
xrxs-cli schema employee.<method>
```

例如：

```bash
xrxs-cli schema employee.saveDismissForm
```

这样可以获取该接口的字段类型、必填校验、示例值、返回结构等完整信息。

> ⚠️ **离职命令 schema 约定（实测，2026-08-10）**：
> 1. `saveDismissForm` 与 `saveDismissFormPreview` **请求体结构完全相同**（见下两节字段说明），`schema employee.saveDismissFormPreview` 与 `schema employee.saveDismissForm` 二者**只需查一次**（查 preview 即可，正式接口同构无需再查）。
> 2. **禁止 `--help`**：schema 已返回全部字段/示例后，严禁再对同一命令执行 `--help` 或重复 schema（违反「同一命令最多检查一次」，纯浪费）。schema 输出虽大（60KB+），但一次足以覆盖 preview 与正式两个接口。

### 操作命令前置要求

本文档中的写入/提交类操作命令（如 `saveDismissForm`、`triggerHandover` 等）涉及人事变动，执行前必须确认用户意图。其中 `saveDismissForm` 带有 preview 接口，需按「预览接口」中的权限检查规则执行：用户已永久授权则可直接调用；未授权则必须先调用 preview 接口展示摘要，经用户确认后再执行。

## 表单数据与提交说明

`getDismissFormData` 返回两部分数据：

- `setting`：表单设置，即纯表单结构，包含 `formId`、`formCode`、`formName`、`groups` 等元信息，**不含员工实际字段值**。
- `values`：各员工的字段值列表，顺序与入参 `employeeIds` 一致；每个元素含 `employeeId` 与 `groups`，`groups` 中的 `fields`/`groupRecords` 携带该员工当前已填写的字段值。

提交类命令（`saveDismissFormPreview`、`saveDismissForm`）构造请求体时：

1. 以 `setting` 中的表单结构为模板，确认字段清单、必填项、字段类型等；
2. 按 `employeeId` 从 `values` 中定位该员工的 `groups`，将其作为提交数据的基础；
3. 将用户需要修改的员工信息按 `fieldId` 覆盖到对应字段；
4. 最终请求体为 `{"employeeId": "<员工ID>", "groups": [<处理后的分组字段值>]}` 的数组。

## 预览接口

以下 preview 接口用于在正式提交前向用户展示操作摘要。调用对应正式操作前，建议先执行权限检查判断用户是否已永久授权：

```bash
xrxs-cli permission check employee-saveDismissForm
```

- 若返回 `true`，说明用户已授权，可直接调用正式操作 `saveDismissForm`。
- 若返回 `false`，说明用户未授权，必须先调用 `saveDismissFormPreview` 展示操作摘要，等用户确认后再调用 `saveDismissForm`。

- `saveDismissFormPreview` → 对应正式操作 `saveDismissForm`

## saveDismissFormPreview / 批量离职预览

**描述**：批量离职预览。请求体需从 `getDismissFormData` 返回的 `setting` 获取表单结构、从 `values` 获取各员工字段值后拼接而成，并覆盖用户本次需要修改的员工信息；预览明细中预计离职日期从入参表单取（与保存同源，按 fieldName=dismissionDate 提取）。

**CLI 命令示例**：
```bash
xrxs-cli employee saveDismissFormPreview --request-body json
```

**请求体说明**：
JSON 数组，元素类型为 object
数组元素包含以下字段：
- `employeeId` (string): 员工id
- `groups` (array): 表单字段值分组
  结构与 `getDismissFormData` 返回的 `values[].groups` 一致，提交前需将用户修改按 `fieldId` 覆盖到对应字段。
  JSON 数组，元素类型为 object
  数组元素包含以下字段：
  - `fields` (array): 顶部字段值列表
    JSON 数组，元素类型为 object
    数组元素包含以下字段：
    - `fieldId` (string): 字段id
    - `fieldValue` (string): 字段值
    - `fieldValueDesc` (string): 字段视图值（展示用）
  - `formGroupId` (integer): 表单分组id（运行时层）
  - `groupRecords` (array): 明细记录值列表
    JSON 数组，元素类型为 object
    数组元素包含以下字段：
    - `changeType` (integer): 更改类型 0-不变 1-新增 2-更改 3-删除
    - `groupFields` (array): 组字段值列表
      JSON 数组，元素类型为 object
      数组元素包含以下字段：
      - `fieldId` (string): 字段id
      - `fieldValue` (string): 字段值
      - `fieldValueDesc` (string): 字段视图值（展示用）
    - `recordId` (string): 分组记录id
  - `libGroupId` (string): 字段库组id；与结构侧 `libGroupId` 对齐

## getDismissFormData / 批量获取员工离职表单数据

**描述**：批量获取员工离职表单数据。返回结果分为两部分：`setting` 为表单设置（纯表单结构，不含员工值），`values` 为各员工的字段值列表（顺序与入参 `employeeIds` 一致）。提交表单时需从 `setting` 取表单结构、从 `values` 取员工字段值拼接后，再覆盖用户修改。

> ⚠️ **首次调用即带 `--jq` 提取字段（实测，2026-08-10）**：本接口全量返回可达 42KB+（一整个离职表单 JSON），直接全量拉取会污染上下文，且极易导致二次重拉。**必须一步到位**，用下方 `--jq` 形式提取所需字段（labelName、fieldName、require、readonly、type、fieldValue、fieldValueId 等），据此判断必填项（如离职类型 dimissionType、离职日期 dismissionDate）与表单填写。

**CLI 命令示例**（推荐，一步到位）：
```bash
xrxs-cli employee getDismissFormData --employeeIds 1001,1002,1003 --jq '.data[0].data.formModel | {formCode, formName, employeeId, formRecordId, businessScenesType, groups: [.groups[] | {groupName: .groupName, isHide, index, fields: [.fields[] | {labelName, fieldName, require, readonly, type, fieldValue, fieldValueId, dicCode, placeholder, position}]}]}'
```

**参数说明**：
- `employeeIds` (string, 必填): 员工id列表，必填，最多 50 个

## getDismissPendingIssueTotal / 获取员工离职待处理事项

**描述**：获取员工离职待处理事项

**CLI 命令示例**：
```bash
xrxs-cli employee getDismissPendingIssueTotal --employeeId 1001 --dismissDate 2026-07-21
```

**参数说明**：
- `employeeId` (string, 选填): 员工id
- `dismissDate` (string, 选填): 离职日期（yyyy-MM-dd，可选，考勤校验需要）

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
xrxs-cli employee getEmployeeFilterFields --filterBizType 5 
```

> **keyword 筛选建议**：`getEmployeeFilterFields` 返回的字段数量通常很多。如果只需要查询某个字段，建议加上 `--keyword <字段名/关键词>` 进行筛选，避免返回过多无关字段。特别是当需要查询以下关键词相关字段时，优先使用 keyword 筛选：**入职日期、转正日期、离职日期、调动日期、转正方式、考核方式、考核结果**。

**参数说明**：
- `filterBizType` (string, 选填): 业务类型：1-员工搜索 2-入职记录 3-转正记录 4-调岗记录 5-离职记录
- `keyword` (string, 选填): 筛选项关键字，为空不过滤

## getEmployeeFormData / 批量获取员工表单数据

**描述**：批量获取员工表单数据。返回结果分为两部分：`setting` 为表单设置（纯表单结构，不含员工值），`values` 为各员工的字段值列表（顺序与入参 `employeeIds` 一致）。

**CLI 命令示例**：
```bash
xrxs-cli employee getEmployeeFormData --employeeIds 1001,1002,1003 --formCode PERSONAL_FORM
```

**参数说明**：
- `employeeIds` (string, 必填): 员工id列表，必填，最多 50 个
- `formCode` (string, 必填): 表单编码，必填。可选值：PERSONAL_FORM(个人信息)、JOB_FORM(岗位信息)、DISMISION_FORM(离职信息)

## getMatchedHandoverPlan / 获取员工匹配的离职交接方案

**描述**：获取员工匹配的离职交接方案。

**CLI 命令示例**：
```bash
xrxs-cli employee getMatchedHandoverPlan --employeeId 1001
```

**参数说明**：
- `employeeId` (string, 选填): 员工id

## saveDismissForm / 批量员工离职提交

**描述**：批量员工离职提交。请求体需从 `getDismissFormData` 返回的 `setting` 获取表单结构、从 `values` 获取各员工字段值后拼接而成，并覆盖用户本次需要修改的员工信息。

> 📌 **请求体与 `saveDismissFormPreview` 完全相同**（结构见「saveDismissFormPreview / 批量离职预览」一节的字段说明），**不要再单独查 `schema employee.saveDismissForm`**——preview 的 schema 已覆盖本接口。

**CLI 命令示例**：
```bash
xrxs-cli employee saveDismissForm --request-body json
```

**请求体说明**：
JSON 数组，元素类型为 object
数组元素包含以下字段：
- `employeeId` (string): 员工id
- `groups` (array): 表单字段值分组
  结构与 `getDismissFormData` 返回的 `values[].groups` 一致，提交前需将用户修改按 `fieldId` 覆盖到对应字段。
  JSON 数组，元素类型为 object
  数组元素包含以下字段：
  - `fields` (array): 顶部字段值列表
    JSON 数组，元素类型为 object
    数组元素包含以下字段：
    - `fieldId` (string): 字段id
    - `fieldValue` (string): 字段值
    - `fieldValueDesc` (string): 字段视图值（展示用）
  - `formGroupId` (integer): 表单分组id（运行时层）
  - `groupRecords` (array): 明细记录值列表
    JSON 数组，元素类型为 object
    数组元素包含以下字段：
    - `changeType` (integer): 更改类型 0-不变 1-新增 2-更改 3-删除
    - `groupFields` (array): 组字段值列表
      JSON 数组，元素类型为 object
      数组元素包含以下字段：
      - `fieldId` (string): 字段id
      - `fieldValue` (string): 字段值
      - `fieldValueDesc` (string): 字段视图值（展示用）
    - `recordId` (string): 分组记录id
  - `libGroupId` (string): 字段库组id；与结构侧 `libGroupId` 对齐

> 📝 正式提交前，请先调用 `saveDismissFormPreview` 预览并确认操作摘要。

> ⚠️ 写入/删除操作前必须确认用户意图。

## searchDismissRecord / 搜索员工离职记录

**描述**：搜索员工离职记录

**CLI 命令示例**：
```bash
xrxs-cli employee searchDismissRecord --request-body json
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

## triggerHandover / 发起员工离职交接

**描述**：发起员工离职交接

**CLI 命令示例**：
```bash
xrxs-cli employee triggerHandover --request-body json
```

**请求体说明**：
JSON 对象，包含以下字段：
- `planId` (integer): 交接方案id（可选，不传则按员工匹配的默认方案）
- `employeeId` (string [必填]): 员工id（必填）
- `dimissionTime` (string [必填]): 离职时间（必填，yyyy-MM-dd）
- `dimissionType` (integer): 离职类型，默认 0
0-主动离职 1-被动离职 2-退休 3-协商解除 999-其他

> ⚠️ 写入/删除操作前必须确认用户意图。
