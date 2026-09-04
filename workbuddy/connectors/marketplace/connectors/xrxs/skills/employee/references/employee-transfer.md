---
name: employee-transfer
description: 员工调岗相关操作，包括调岗记录查询、调岗保存与表单获取
---

# 员工调岗

## 调用前准备

### 关于 `--request-body json`

本文档中部分 CLI 命令以 `--request-body json` 结尾，例如：

```bash
xrxs-cli employee saveTransfer --request-body json
```

这里的 `json` **不是参数值**，而是声明该接口需要以 **JSON 格式**传入请求体。具体 JSON 结构请查看对应接口下方的「请求体说明」。

### 查看接口完整信息

本文档未覆盖的命令，可通过以下方式查看该接口的入参、返回值及使用明细（何时需要查 schema 的分级规则见 ../SKILL.md「查看接口完整信息」）：

```bash
xrxs-cli schema employee.<method>
```

例如：

```bash
xrxs-cli schema employee.saveTransfer
```

这样可以获取该接口的字段类型、必填校验、示例值、返回结构等完整信息。

> ⚠️ **调岗命令 schema 约定（实测，2026-08-10）**：
> 1. `saveTransfer` 与 `saveTransferPreview` **请求体结构完全相同**（见下两节字段说明），`schema employee.saveTransferPreview` 与 `schema employee.saveTransfer` 二者**只需查一次**（查 preview 即可，正式接口同构无需再查）。
> 2. **禁止 `--help`**：schema 已返回全部字段/示例后，严禁再对同一命令执行 `--help` 或重复 schema（违反「同一命令最多检查一次」，纯浪费）。schema 输出虽大（130KB+），但一次足以覆盖 preview 与正式两个接口。

### 操作命令前置要求

本文档中的写入/提交类操作命令涉及人事变动，执行前必须确认用户意图。调用正式操作前，需按「预览接口」中的权限检查规则执行：用户已永久授权则可直接调用正式接口；未授权则必须先调用 preview 接口展示摘要，经用户确认后再执行。

## 表单数据与提交说明

`getTransferFormData` 直接返回每个员工的审批表单数据，结构为数组，每个元素含 `employeeId` 与 `groups`；`groups` 中的 `fields` 已包含当前字段值（含 `fieldValue`、`fieldValueId`、`fieldOldValue` 等）。

提交类命令（`saveTransferPreview`、`saveTransfer`）构造请求体时：

1. 从 `getTransferFormData` 返回的 `data[]` 中按 `employeeId` 找到该员工的 `groups`；
2. 将用户需要修改的员工信息按 `fieldId` 覆盖到对应字段；
3. 最终请求体为 `{"employeeId": "<员工ID>", "groups": [<处理后的审批表单分组>]}` 的数组。

## 预览接口

以下 preview 接口用于在正式提交前向用户展示操作摘要。调用对应正式操作前，建议先执行权限检查判断用户是否已永久授权：

```bash
xrxs-cli permission check employee-saveTransfer
```

- 若返回 `true`，说明用户已授权，可直接调用正式操作 `saveTransfer`。
- 若返回 `false`，说明用户未授权，必须先调用 `saveTransferPreview` 展示操作摘要，等用户确认后再调用 `saveTransfer`。

- `saveTransferPreview` → 对应正式操作 `saveTransfer`

## saveTransferPreview / 批量调岗预览

**描述**：批量调岗预览。请求体需以 `getTransferFormData` 返回的 `groups` 为基础，覆盖用户本次需要修改的员工信息后提交。

**CLI 命令示例**：
```bash
xrxs-cli employee saveTransferPreview --request-body json
```

**请求体说明**：
JSON 数组，元素类型为 object
数组元素包含以下字段：
- `employeeId` (string): 员工id
- `groups` (array): 审批表单分组列表
  结构与 `getTransferFormData` 返回的 `data[].groups` 一致，提交前需将用户修改按 `fieldId` 覆盖到对应字段。
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
xrxs-cli employee getEmployeeFilterFields --filterBizType 4
```

> **keyword 筛选建议**：`getEmployeeFilterFields` 返回的字段数量通常很多。如果只需要查询某个字段，建议加上 `--keyword <字段名/关键词>` 进行筛选，避免返回过多无关字段。特别是当需要查询以下关键词相关字段时，优先使用 keyword 筛选：**入职日期、转正日期、离职日期、调动日期、转正方式、考核方式、考核结果**。

**参数说明**：
- `filterBizType` (string, 选填): 业务类型：1-员工搜索 2-入职记录 3-转正记录 4-调岗记录 5-离职记录
- `keyword` (string, 选填): 筛选项关键字，为空不过滤

## getTransferFormData / 批量获取员工调岗表单数据

**描述**：批量获取员工调岗表单数据。返回结果为数组，每个元素含 `employeeId` 与 `groups`；`groups[].fields` 已包含当前字段值，提交 `saveTransfer` 时直接以其为基础覆盖用户修改即可。

> ⚠️ **首次调用即带 `--jq` 提取字段（实测，2026-08-10）**：本接口全量返回可达 60KB+（一整个调岗表单 JSON），直接全量拉取会污染上下文，且极易导致二次重拉。**必须一步到位**，用下方 `--jq` 形式提取所需字段（groupName/fields 的 labelName、fieldName、require、readonly、type、fieldValue、fieldValueId 等），据此判断必填项与表单填写。

**CLI 命令示例**（推荐，一步到位）：
```bash
xrxs-cli employee getTransferFormData --employeeIds 1001,1002,1003 --jq '.data[0].data.flowGroups[] | {groupName, index, isHide, fields: [.fields[] | {labelName, fieldName, require, readonly, type, fieldValue, fieldValueId, placeholder, position}]}'
```

**参数说明**：
- `employeeIds` (string, 必填): 员工id列表，必填，最多 50 个

## saveTransfer / 批量调岗保存提交

**描述**：批量调岗保存提交。请求体需以 `getTransferFormData` 返回的 `groups` 为基础，覆盖用户本次需要修改的员工信息后提交。

> 📌 **请求体与 `saveTransferPreview` 完全相同**（结构见「saveTransferPreview / 批量调岗预览」一节的字段说明），**不要再单独查 `schema employee.saveTransfer`**——preview 的 schema 已覆盖本接口。

**CLI 命令示例**：
```bash
xrxs-cli employee saveTransfer --request-body json
```

**请求体说明**：
JSON 数组，元素类型为 object
数组元素包含以下字段：
- `employeeId` (string): 员工id
- `groups` (array): 审批表单分组列表
  结构与 `getTransferFormData` 返回的 `data[].groups` 一致，提交前需将用户修改按 `fieldId` 覆盖到对应字段。
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

> 📝 正式提交前，请先调用 `saveTransferPreview` 预览并确认操作摘要。

> ⚠️ 写入/删除操作前必须确认用户意图。

## searchTransferRecord / 搜索员工调岗记录

**描述**：搜索员工调岗记录

**CLI 命令示例**：
```bash
xrxs-cli employee searchTransferRecord --request-body json
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
