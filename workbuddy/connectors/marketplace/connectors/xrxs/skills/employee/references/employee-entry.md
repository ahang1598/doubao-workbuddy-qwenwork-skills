---
name: employee-entry
description: 员工入职相关操作，包括入职记录查询、待入职员工录入与校验、入职表单获取
---

# 员工入职

## 调用前准备

### 关于 `--request-body json`

本文档中部分 CLI 命令以 `--request-body json` 结尾，例如：

```bash
xrxs-cli employee entryPendingEmployee --request-body json
```

这里的 `json` **不是参数值**，而是声明该接口需要以 **JSON 格式**传入请求体。具体 JSON 结构请查看对应接口下方的「请求体说明」。

### 查看接口完整信息

本文档未覆盖的命令，可通过以下方式查看该接口的入参、返回值及使用明细（何时需要查 schema 的分级规则见 ../SKILL.md「查看接口完整信息」）：

```bash
xrxs-cli schema employee.<method>
```

例如：

```bash
xrxs-cli schema employee.entryPendingEmployee
```

这样可以获取该接口的字段类型、必填校验、示例值、返回结构等完整信息，但是也得参考当前文档里面的请求体说明，这里有一些特殊字段的使用说明。
### 操作命令前置要求

本文档中的写入/提交类操作命令涉及人事变动，执行前必须确认用户意图。调用正式操作前，需按「预览接口」中的权限检查规则执行：用户已永久授权则可直接调用正式接口；未授权则必须先调用 preview 接口展示摘要，经用户确认后再执行。

## 表单数据与提交说明

`getEntryPendingEmployeeForm` 返回两部分数据：

- `setting`：表单设置，即纯表单结构，包含 `formId`、`formCode`、`formName`、`groups` 等元信息，**不含员工实际字段值**。
- `values`：各员工的字段值列表，顺序与入参 `employeeIds` 一致；每个元素含 `employeeId` 与 `groups`，`groups` 中的 `fields`/`groupRecords` 携带该员工当前已填写的字段值。

提交类命令（`entryPendingEmployeePreview`、`entryPendingEmployee`、`validateEntryPendingEmployee`）构造请求体时：

1. 以 `setting` 中的表单结构为模板，确认字段清单、必填项、字段类型等；
2. 按 `employeeId` 从 `values` 中定位该员工的 `groups`，将其作为提交数据的基础；
3. 将用户需要修改的员工信息按 `fieldId` 覆盖到对应字段；
4. 最终请求体为 `{"employeeId": "<员工ID>", "groups": [<处理后的分组字段值>]}` 的数组。

> ⚠️ `preview` 与 `entryPendingEmployee` 必须携带从 `getEntryPendingEmployeeForm` 获取的完整表单数据（`setting` + `values` 拼接后），仅传 `{"employeeId":"xxx"}` 会导致返回 `totalCount: 0` 且接口耗时极长（实测可达 130s 以上）。

## 预览接口

以下 preview 接口用于在正式提交前向用户展示操作摘要。调用对应正式操作前，建议先执行权限检查判断用户是否已永久授权：

```bash
xrxs-cli permission check employee-entryPendingEmployee
```

- 若返回 `true`，说明用户已授权，可直接调用正式操作 `entryPendingEmployee`。
- 若返回 `false`，说明用户未授权，必须先调用 `entryPendingEmployeePreview` 展示操作摘要，等用户确认后再调用 `entryPendingEmployee`。

- `entryPendingEmployeePreview` → 对应正式操作 `entryPendingEmployee`

## entryPendingEmployeePreview / 批量待入职员工入职预览

**描述**：批量待入职员工入职预览。请求体需从 `getEntryPendingEmployeeForm` 返回的 `setting` 获取表单结构、从 `values` 获取各员工字段值后拼接而成，并覆盖用户本次需要修改的员工信息；preview 明细中姓名/手机号/入职日期/部门/聘用形式优先取提交表单数据，表单未提交时回退 ES。

**CLI 命令示例**：
```bash
xrxs-cli employee entryPendingEmployeePreview --request-body json
```

**请求体说明**：
JSON 数组，元素类型为 object。⚠️ **数组元素必须包含从 `getEntryPendingEmployeeForm` 拼接后的完整表单数据**；仅传 `{"employeeId":"xxx"}` 会导致返回 `totalCount: 0` 且接口耗时极长（实测可达 130s 以上）。

数组元素包含以下字段：
- `employeeId` (string): 员工id
- `groups` (array): 表单字段值分组
  结构与 `getEntryPendingEmployeeForm` 返回的 `values[].groups` 一致，提交前需将用户修改按 `fieldId` 覆盖到对应字段。
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

## entryPendingEmployee / 批量待入职员工入职

**描述**：批量待入职员工入职。请求体需从 `getEntryPendingEmployeeForm` 返回的 `setting` 获取表单结构、从 `values` 获取各员工字段值后拼接而成，并覆盖用户本次需要修改的员工信息。

**CLI 命令示例**：
```bash
xrxs-cli employee entryPendingEmployee --request-body json
```

**请求体说明**：
JSON 数组，元素类型为 object。⚠️ **数组元素必须包含从 `getEntryPendingEmployeeForm` 拼接后的完整表单数据**；仅传 `{"employeeId":"xxx"}` 会导致返回 `totalCount: 0` 且接口耗时极长（实测可达 130s 以上）。

数组元素包含以下字段：
- `employeeId` (string): 员工id
- `groups` (array): 表单字段值分组
  结构与 `getEntryPendingEmployeeForm` 返回的 `values[].groups` 一致，提交前需将用户修改按 `fieldId` 覆盖到对应字段。
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

> 📝 正式提交前，请先调用 `entryPendingEmployeePreview` 预览并确认操作摘要。

> ⚠️ 写入/删除操作前必须确认用户意图。

## validateEntryPendingEmployee 与 entryPendingEmployeePreview 的关系

- **`entryPendingEmployeePreview` 是正式提交前的必需步骤**：它既能生成用户确认所需的摘要，又能暴露表单校验问题。场景三（批量入职）应优先使用 preview 做最终检查。
- **`validateEntryPendingEmployee` 不是场景三的必需步骤**：该接口用于独立的批量校验，若 preview 已能返回有效摘要，则无需再调用 validate；若 preview 报字段错误，按错误提示补充信息后重新 preview 即可。
- **避免用 validate 替代 preview**：validate 成功不等于 preview/提交一定成功，且实测中 validate 对相同表单可能返回「添加员工参数为空」等不易定位的错误，不要陷入反复调用 validate 的循环。

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
xrxs-cli employee getEmployeeFilterFields --filterBizType 2
```

> **keyword 筛选建议**：`getEmployeeFilterFields` 返回的字段数量通常很多。如果只需要查询某个字段，建议加上 `--keyword <字段名/关键词>` 进行筛选，避免返回过多无关字段。特别是当需要查询以下关键词相关字段时，优先使用 keyword 筛选：**入职日期、转正日期、离职日期、调动日期、转正方式、考核方式、考核结果**。

**参数说明**：
- `filterBizType` (string, 选填): 业务类型：1-员工搜索 2-入职记录 3-转正记录 4-调岗记录 5-离职记录
- `keyword` (string, 选填): 筛选项关键字，为空不过滤

## getEntryPendingEmployeeForm / 批量获取待入职员工入职表单数据

**描述**：批量获取待入职员工入职表单数据。返回结果分为两部分：`setting` 为表单设置（纯表单结构，不含员工值），`values` 为各员工的字段值列表（顺序与入参 `employeeIds` 一致）。提交表单时需从 `setting` 取表单结构、从 `values` 取员工字段值拼接后，再覆盖用户修改。

**CLI 命令示例**：
```bash
xrxs-cli employee getEntryPendingEmployeeForm --employeeIds 1001,1002,1003
```

**参数说明**：
- `employeeIds` (string, 必填): 待入职员工id列表，必填，最多 50 个

## searchEntryRecord / 搜索员工入职记录

**描述**：搜索员工入职记录

**CLI 命令示例**：
```bash
xrxs-cli employee searchEntryRecord --request-body json
```

**请求体说明**：
JSON 对象，包含以下字段：
- `pageNo` (integer): 页码，从1开始，默认1
- `filters` (array): 筛选条件，结构与「获取员工数据搜索过滤条件字段」接口返回值一致。
每个筛选项通过 values（多选/区间）/ dateValues（日期范围）携带选中值，转换复用员工列表筛选逻辑。
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
  25 多级多选    - 填 values，多个元素，key 为所选层级值。
- `keyword` (string): 搜索关键字（姓名/手机号/工号等）
- `pageSize` (integer): 每页条数，默认20，上限100

> filters 字段需先从 `getEmployeeFilterFields` 获取筛选项配置，按规则填值后再作为本接口入参回传。

## validateEntryPendingEmployee / 批量待入职员工入职校验

**描述**：批量待入职员工入职校验。请求体需从 `getEntryPendingEmployeeForm` 返回的 `setting` 获取表单结构、从 `values` 获取各员工字段值后拼接而成，并覆盖用户本次需要修改的员工信息。

**CLI 命令示例**：
```bash
xrxs-cli employee validateEntryPendingEmployee --request-body json
```

**请求体说明**：
JSON 数组，元素类型为 object。⚠️ **数组元素必须包含从 `getEntryPendingEmployeeForm` 拼接后的完整表单数据**；仅传 `{"employeeId":"xxx"}` 会导致返回 `totalCount: 0` 且接口耗时极长（实测可达 130s 以上）。

数组元素包含以下字段：
- `employeeId` (string): 员工id
- `groups` (array): 表单字段值分组
  结构与 `getEntryPendingEmployeeForm` 返回的 `values[].groups` 一致，提交前需将用户修改按 `fieldId` 覆盖到对应字段。
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

> ⚠️ 写入/删除操作前必须确认用户意图。
