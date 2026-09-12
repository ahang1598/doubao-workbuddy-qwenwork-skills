---
name: employee-basic
description: 员工基础信息查询能力，包括国家、人事规则、筛选字段、员工搜索与详情
---

# 员工基础能力

## 调用前准备

### 关于 `--request-body json`

本文档中部分 CLI 命令以 `--request-body json` 结尾，例如：

```bash
xrxs-cli employee searchEmployee --request-body json
```

这里的 `json` **不是参数值**，而是声明该接口需要以 **JSON 格式**传入请求体。具体 JSON 结构请通过 `xrxs-cli schema employee.<method>` 获取完整参数说明。

### 查看接口完整信息

本文档未覆盖的命令，可通过以下方式查看该接口的入参、返回值及使用明细（何时需要查 schema 的分级规则见 ../SKILL.md「查看接口完整信息」）：

```bash
xrxs-cli schema employee.<method>
```

例如：

```bash
xrxs-cli schema employee.searchEmployee
```

这样可以获取该接口的字段类型、必填校验、示例值、返回结构等完整信息。

## getHumanRules / 获取公司人事规则列表

**描述**：获取公司人事规则列表

**CLI 命令示例**：
```bash
xrxs-cli employee getHumanRules
```

## getAllCountry / 获取所有国家

**描述**：获取所有国家

**CLI 命令示例**：
```bash
xrxs-cli employee getAllCountry --keyword 张三
```

**参数说明**：
- `keyword` (string, 选填): 国家名关键字，为空返回全部

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
xrxs-cli employee getEmployeeFilterFields --filterBizType 1 --keyword 张三
```

> **keyword 筛选建议**：`getEmployeeFilterFields` 返回的字段数量通常很多。如果只需要查询某个字段，建议加上 `--keyword <字段名/关键词>` 进行筛选，避免返回过多无关字段。特别是当需要查询以下关键词相关字段时，优先使用 keyword 筛选：**入职日期、转正日期、离职日期、调动日期、转正方式、考核方式、考核结果**。

**参数说明**：
- `filterBizType` (string, 选填): 业务类型：1-员工搜索 2-入职记录 3-转正记录 4-调岗记录 5-离职记录
- `keyword` (string, 选填): 筛选项关键字，为空不过滤

## searchEmployee / 搜索员工

**描述**：搜索员工

**CLI 命令示例**：
```bash
xrxs-cli employee searchEmployee --request-body json
```

**请求体说明**：
- `pageNo` (integer): 页码，从1开始，默认1
- `status` (integer): 员工状态 @see com.xrxs.client.cornerstone.enums.EEmployeeStatus
0-在职 1-离职 2-待入职，默认 0（在职）。
- `filters` (array): 筛选条件，结构与「获取员工过滤条件」接口返回值一致。请先调用 `getEmployeeFilterFields --filterBizType 1` 获取员工搜索筛选字段，并按其返回的字段配置填值后作为本接口的 `filters` 入参回传。`getEmployeeFilterFields` 返回的 FilterFieldModel 仅为筛选项「配置」(values/dateValues 为空)，调用方按下方规则填值：
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
- `keyword` (string): 搜索关键字（姓名/手机号/工号等）
- `pageSize` (integer): 每页条数，默认20，上限100

## getEmployeeDetail / 获取员工详情

**描述**：获取员工详情

**CLI 命令示例**：
```bash
xrxs-cli employee getEmployeeDetail --employeeId 1001
```

**参数说明**：
- `employeeId` (string, 必填): 员工id
