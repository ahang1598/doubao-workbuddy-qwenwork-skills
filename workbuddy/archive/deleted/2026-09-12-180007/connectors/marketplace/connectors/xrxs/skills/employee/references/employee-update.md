---
name: employee-update
description: 员工信息更新相关操作，包括字段更新、校验与表单获取
---

# 员工更新

## 调用前准备

### 关于 `--request-body json`

本文档中部分 CLI 命令以 `--request-body json` 结尾，例如：

```bash
xrxs-cli employee updateEmployeeFields --request-body json
```

这里的 `json` **不是参数值**，而是声明该接口需要以 **JSON 格式**传入请求体。具体 JSON 结构请查看对应接口下方的「请求体说明」。

### 查看接口完整信息

本文档未覆盖的命令，可通过以下方式查看该接口的入参、返回值及使用明细（何时需要查 schema 的分级规则见 ../SKILL.md「查看接口完整信息」）：

```bash
xrxs-cli schema employee.<method>
```

例如：

```bash
xrxs-cli schema employee.updateEmployeeFields
```

这样可以获取该接口的字段类型、必填校验、示例值、返回结构等完整信息。

### 操作命令前置要求

本文档中的写入/提交类操作命令涉及人事变动，执行前必须确认用户意图。调用正式操作前，需按「预览接口」中的权限检查规则执行：用户已永久授权则可直接调用正式接口；未授权则必须先调用 preview 接口展示摘要，经用户确认后再执行。

## 表单数据与提交说明

`getEmployeeFormData` 返回两部分数据：

- `setting`：表单设置，即纯表单结构，包含 `formId`、`formCode`、`formName`、`groups` 等元信息，**不含员工实际字段值**。
- `values`：各员工的字段值列表，顺序与入参 `employeeIds` 一致；每个元素含 `employeeId` 与 `groups`，`groups` 中的 `fields`/`groupRecords` 携带该员工当前已填写的字段值。

`updateEmployeeFields` / `updateEmployeeFieldsPreview` 仅支持更新**顶部字段**（非分组字段），构造请求体时：

1. 以 `setting` 中的表单结构为模板，确认可更新的顶部字段清单；
2. 按 `employeeId` 从 `values` 中定位该员工的 `groups[].fields`，提取顶部字段值作为基础；
3. 将用户需要修改的字段按 `fieldId` 覆盖对应 `fieldValue`；
4. 最终请求体为 `{"employeeId": "<员工ID>", "fields": [{"fieldId": "...", "fieldValue": "...", ...}]}` 的数组。

## 预览接口

以下 preview 接口用于在正式提交前向用户展示操作摘要。调用对应正式操作前，建议先执行权限检查判断用户是否已永久授权：

```bash
xrxs-cli permission check employee-updateEmployeeFields
```

- 若返回 `true`，说明用户已授权，可直接调用正式操作 `updateEmployeeFields`。
- 若返回 `false`，说明用户未授权，必须先调用 `updateEmployeeFieldsPreview` 展示操作摘要，等用户确认后再调用 `updateEmployeeFields`。

- `updateEmployeeFieldsPreview` → 对应正式操作 `updateEmployeeFields`

## updateEmployeeFieldsPreview / 批量更新员工信息预览

**描述**：批量更新员工信息预览。请求体中的 `fields` 需从 `getEmployeeFormData` 返回的 `values[].groups[].fields` 获取顶部字段值，再覆盖用户本次需要修改的字段值。

**CLI 命令示例**：
```bash
xrxs-cli employee updateEmployeeFieldsPreview --request-body json
```

**请求体说明**：
JSON 数组，元素类型为 object
数组元素包含以下字段：
- `employeeId` (string): 员工id
- `fields` (array): 字段列表
  仅支持顶部字段（非分组字段），结构同 `getEmployeeFormData` 返回的 `values[].groups[].fields`，提交前需将用户修改按 `fieldId` 覆盖到对应字段。
  JSON 数组，元素类型为 object
  数组元素包含以下字段：
  - `fieldId` (string): 字段id
  - `fieldName` (string): 字段名称
  - `labelName` (string): 字段标签名称
  - `fieldValue` (string): 字段值
  - `fieldValueDesc` (string): 字段值描述

> 📝 正式提交前，请先调用 `updateEmployeeFieldsPreview` 预览并确认操作摘要。

## getEmployeeFormData / 批量获取员工表单数据

**描述**：批量获取员工表单数据。返回结果分为两部分：`setting` 为表单设置（纯表单结构，不含员工值），`values` 为各员工的字段值列表（顺序与入参 `employeeIds` 一致）。`updateEmployeeFields` 仅支持更新顶部字段，需从 `values[].groups[].fields` 中提取。

**CLI 命令示例**：
```bash
xrxs-cli employee getEmployeeFormData --employeeIds 1001,1002,1003 --formCode PERSONAL_FORM
```

**参数说明**：
- `employeeIds` (string, 必填): 员工id列表，必填，最多 50 个
- `formCode` (string, 必填): 表单编码，必填。可选值：PERSONAL_FORM(个人信息)、JOB_FORM(岗位信息)、DISMISION_FORM(离职信息)

## updateEmployeeFields / 批量更新员工信息

**描述**：批量更新员工信息，仅支持更新顶部字段（非分组字段）。请求体中的 `fields` 需从 `getEmployeeFormData` 返回的 `values[].groups[].fields` 获取顶部字段值，再覆盖用户本次需要修改的字段值。

**CLI 命令示例**：
```bash
xrxs-cli employee updateEmployeeFields --request-body json
```

**请求体说明**：
JSON 数组，元素类型为 object
数组元素包含以下字段：
- `employeeId` (string): 员工id
- `fields` (array): 字段列表
  仅支持顶部字段（非分组字段），结构同 `getEmployeeFormData` 返回的 `values[].groups[].fields`，提交前需将用户修改按 `fieldId` 覆盖到对应字段。
  JSON 数组，元素类型为 object
  数组元素包含以下字段：
  - `fieldId` (string): 字段id
  - `fieldName` (string): 字段名称
  - `labelName` (string): 字段标签名称
  - `fieldValue` (string): 字段值
  - `fieldValueDesc` (string): 字段值描述

> 📝 正式提交前，请先调用 `updateEmployeeFieldsPreview` 预览并确认操作摘要。

> ⚠️ 写入/删除操作前必须确认用户意图。

## validateEmployeeFields / 批量更新员工信息校验

**描述**：批量更新员工信息校验。请求体中的 `fields` 需从 `getEmployeeFormData` 返回的 `values[].groups[].fields` 获取顶部字段值，再覆盖用户本次需要修改的字段值。

**CLI 命令示例**：
```bash
xrxs-cli employee validateEmployeeFields --request-body json
```

**请求体说明**：
JSON 数组，元素类型为 object
数组元素包含以下字段：
- `employeeId` (string): 员工id
- `fields` (array): 字段列表
  仅支持顶部字段（非分组字段），结构同 `getEmployeeFormData` 返回的 `values[].groups[].fields`，提交前需将用户修改按 `fieldId` 覆盖到对应字段。
  JSON 数组，元素类型为 object
  数组元素包含以下字段：
  - `fieldId` (string): 字段id
  - `fieldName` (string): 字段名称
  - `labelName` (string): 字段标签名称
  - `fieldValue` (string): 字段值
  - `fieldValueDesc` (string): 字段值描述

> ⚠️ 写入/删除操作前必须确认用户意图。
