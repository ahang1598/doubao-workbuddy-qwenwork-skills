# payroll 基础接口

> **前置条件：** 先阅读 [`../SKILL.md`](../SKILL.md) 了解全局能力。

基础接口。包括词典选项、城市/国家、员工详情、部门/岗位/职级/成本中心搜索等通用能力。

## 适用场景

- getDicOption：获取词典选项信息（CLI 版）
- getAreaV2tree：获取城市信息树（CLI 版）。
- searchCitys：根据关键字搜索城市
- getEmployeeDetail：获取员工详情
- getAllCountry：获取所有国家
- getEmployeeFilterFields：获取员工搜索过滤条件字段（配合 searchEmployee 使用）
- searchEmployee：搜索员工
- searchDepartment：搜索部门
- searchJob：搜索岗位
- searchRank：搜索职级
- searchCostCenter：搜索成本中心

## 推荐命令

### getDicOption

获取词典选项信息

获取词典选项信息（CLI 版）

```bash
xrxs-cli payroll getDicOption
  --dicCode <dicCode>
```

> 请求方式：`GET`。无请求体，参数通过 `--<name> <value>` 传递。

参数：

| 参数 | 必填 | 类型 | 说明 |
|------|------|------|------|
| `--dicCode` | 否 | string | 词典编码 |

返回：

- `code`：状态码
- `status`：是否成功
- `message`：提示信息

`data` 主要字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `data.dicCode` | string | 词典编码 |
| `data.dicName` | string | 词典名 |
| `data.initType` | string | 初始化类型。1=系统预置，2=客户复制，3=客户创建,默认为1 |
| `data.optionList` | array<object> | 选项列表 |
| `data.optionList[].status` | integer | 状态，0-启用，1-禁用 |
| `data.optionList[].optionKey` | string | 选项key |
| `data.optionList[].optionValue` | string | 选项值 |
| `data.optionList[].optionEnValue` | string | 选项值 |
| `data.optionList[].childOptionList` | array<object> |  |
| `data.optionList[].childOptionList[].status` | integer | 状态，0-启用，1-禁用 |
| `data.optionList[].childOptionList[].optionKey` | string | 选项key |
| `data.optionList[].childOptionList[].optionValue` | string | 选项值 |
| `data.optionList[].childOptionList[].optionEnValue` | string | 选项值 |
| `data.optionList[].childOptionList[].childOptionList` | array<object> |  |
| `data.optionList[].childOptionList[].optionValueDicId` | string | 选项多语言字典id |
| `data.optionList[].childOptionList[].optionValueLangs` | object | 选项多语言值 |
| `data.optionList[].optionValueDicId` | string | 选项多语言字典id |
| `data.optionList[].optionValueLangs` | object | 选项多语言值 |
| `data.optionDepth` | integer | 选项深度，默认为1级 |
| `data.optionKeyType` | string | 选项Key类型<br>选项key类型，1-数字，2-文本，默认为1 |

### getAreaV2tree

获取城市信息树

获取城市信息树（CLI 版）。

```bash
xrxs-cli payroll getAreaV2tree
```

> 请求方式：`GET`。无请求体，参数通过 `--<name> <value>` 传递。

返回：

- `code`：状态码
- `status`：是否成功
- `message`：提示信息

`data` 主要字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `data.mainlandList` | array<object> | 中国大陆城市树 |
| `data.mainlandList[].name` | string |  |
| `data.mainlandList[].value` | integer |  |
| `data.mainlandList[].areaType` | integer |  |
| `data.mainlandList[].children` | array<object> |  |
| `data.mainlandList[].children[].name` | string |  |
| `data.mainlandList[].children[].value` | integer |  |
| `data.mainlandList[].children[].areaType` | integer |  |
| `data.mainlandList[].children[].children` | array<object> |  |
| `data.mainlandList[].children[].namePinyin` | string |  |
| `data.mainlandList[].children[].nameEnglish` | string |  |
| `data.mainlandList[].children[].nameInitialsPinyin` | string |  |
| `data.mainlandList[].children[].nameInitialsEnglish` | string |  |
| `data.mainlandList[].namePinyin` | string |  |
| `data.mainlandList[].nameEnglish` | string |  |
| `data.mainlandList[].nameInitialsPinyin` | string |  |
| `data.mainlandList[].nameInitialsEnglish` | string |  |
| `data.overseasList` | array<object> | 海外（港澳台国际）城市树 |
| `data.overseasList[].name` | string |  |
| `data.overseasList[].value` | integer |  |
| `data.overseasList[].areaType` | integer |  |
| `data.overseasList[].children` | array<object> |  |
| `data.overseasList[].children[].name` | string |  |
| `data.overseasList[].children[].value` | integer |  |
| `data.overseasList[].children[].areaType` | integer |  |
| `data.overseasList[].children[].children` | array<object> |  |
| `data.overseasList[].children[].namePinyin` | string |  |
| `data.overseasList[].children[].nameEnglish` | string |  |
| `data.overseasList[].children[].nameInitialsPinyin` | string |  |
| `data.overseasList[].children[].nameInitialsEnglish` | string |  |
| `data.overseasList[].namePinyin` | string |  |
| `data.overseasList[].nameEnglish` | string |  |
| `data.overseasList[].nameInitialsPinyin` | string |  |
| `data.overseasList[].nameInitialsEnglish` | string |  |

### searchCitys

根据关键字搜索城市

```bash
xrxs-cli payroll searchCitys
  --name <name>
```

> 请求方式：`GET`。无请求体，参数通过 `--<name> <value>` 传递。

参数：

| 参数 | 必填 | 类型 | 说明 |
|------|------|------|------|
| `--name` | 否 | string | 城市名称关键字，可为空 |

返回：

- `code`：状态码
- `status`：是否成功
- `message`：提示信息

`data` 主要字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `data[].id` | integer | 城市 id |
| `data[].name` | string | 城市名称 |

### getEmployeeDetail

```bash
xrxs-cli payroll getEmployeeDetail
  --employeeId <employeeId>
```

> 请求方式：`GET`。无请求体，参数通过 `--<name> <value>` 传递。

参数：

| 参数 | 必填 | 类型 | 说明 |
|------|------|------|------|
| `--employeeId` | 是 | string | 员工id |

返回：

- `code`：状态码
- `status`：是否成功
- `message`：提示信息

`data` 主要字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `data.age` | integer | 年龄 |
| `data.city` | integer | 工作城市 |
| `data.name` | string | 姓名 |
| `data.email` | string | 工作邮箱 |
| `data.jobId` | string | 岗位id |
| `data.costId` | string | 成本中心id |
| `data.gender` | integer | 性别（0:女 1:男） |
| `data.hrbpId` | string | HRBP id |
| `data.idcode` | string | 身份证号 |
| `data.mobile` | string | 手机号 |
| `data.rankId` | string | 职级id |
| `data.jobName` | string | 岗位名称 |
| `data.tutorId` | string | 导师id |
| `data.workAge` | string | 工龄 |
| `data.birthday` | string | 生日（yyyy-MM-dd） |
| `data.hireType` | integer | 聘用形式大类 @see com.xrxs.client.cornerstone.enums.employee.EHireType<br><ul><br>    <li>0: 正式</li><br>    <li>1: 非正式</li><br></ul> |
| `data.entryDate` | string | 入职日期（yyyy-MM-dd） |
| `data.jobNumber` | string | 工号 |
| `data.companyAge` | string | 司龄 |
| `data.contractId` | string | 合同id |
| `data.directorId` | string | 汇报对象id |
| `data.employeeId` | string | 员工id |
| `data.subjection` | integer | 归属主体 @see com.xrxs.client.cornerstone.enums.ESubjection<br><ul><br>    <li>0: 总部</li><br>    <li>1: 分城市</li><br></ul> |
| `data.englishName` | string | 英文名 |
| `data.regularDate` | string | 转正日期（yyyy-MM-dd） |
| `data.departmentId` | string | 部门id |
| `data.regularState` | integer | 转正状态（0:未转正 1:已转正） |
| `data.firstWorkDate` | string | 首次工作日期（yyyy-MM-dd） |
| `data.highestDegree` | integer | 最高学历 @see com.xrxs.client.cornerstone.enums.EDegree<br><ul><br>    <li>0: 无</li><br>    <li>1: 初中</li><br>    <li>2: 高中</li><br>    <li>3: 中专</li><br>    <li>4: 大专</li><br>    <li>5: 本科</li><br>    <li>6: 硕士</li><br>    <li>7: 博士</li><br>    <li>8: 其他</li><br>    <li>9: 小学</li><br>    <li>10: 中职</li><br>    <li>11: 中技</li><br>    <li>12: MBA</li><br>    <li>13: 博士后</li><br></ul> |
| `data.hireLaborType` | integer | 非正式类型（聘用形式细分）@see com.xrxs.client.cornerstone.enums.employee.EHireType<br>hireType=0（正式）时此字段为 0；<br>hireType=1（非正式）时取以下子类型：<br><ul><br>    <li>10: 实习</li><br>    <li>11: 劳务</li><br>    <li>12: 顾问</li><br>    <li>13: 返聘</li><br>    <li>14: 外包</li><br>    <li>15: 兼职</li><br>    <li>16: 灵活用工</li><br>    <li>17: 劳务派遣</li><br>    <li>18: 派遣</li><br>    <li>19: 见习</li><br>    <li>20: 临时工</li><br>    <li>21: 小时工</li><br></ul> |
| `data.personalEmail` | string | 个人邮箱 |
| `data.dismissionDate` | string | 离职日期（yyyy-MM-dd） |
| `data.dismissionType` | integer | 离职类型 @see com.xrxs.client.cornerstone.enums.EDismission<br><ul><br>    <li>0: 主动离职</li><br>    <li>1: 被动离职</li><br>    <li>2: 退休</li><br>    <li>3: 协商解除</li><br>    <li>999: 其他</li><br></ul> |
| `data.employeeStatus` | integer | 员工状态（0:在职 1:离职 2:待入职） |
| `data.ratepayingCity` | integer | 纳税城市 |
| `data.probationPeriod` | integer | 试用期（月） |
| `data.workScheduleType` | integer | 工作制 @see com.xrxs.client.cornerstone.enums.EWorkScheduleType<br><ul><br>    <li>1: 标准工时制</li><br>    <li>2: 综合工时制</li><br>    <li>3: 不定时工时制</li><br></ul> |
| `data.customFieldValues` | array<object> | 自定义字段值列表（仅公司启用的自定义字段） |
| `data.customFieldValues[].fieldId` | string | 字段id |
| `data.customFieldValues[].fieldType` | integer | 字段类型 |

### getAllCountry

```bash
xrxs-cli payroll getAllCountry
  --keyword <keyword>
```

> 请求方式：`GET`。无请求体，参数通过 `--<name> <value>` 传递。

参数：

| 参数 | 必填 | 类型 | 说明 |
|------|------|------|------|
| `--keyword` | 否 | string | 国家名关键字，为空返回全部 |

返回：

- `code`：状态码
- `status`：是否成功
- `message`：提示信息

`data` 主要字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `data[].id` | integer | 国家id |
| `data[].name` | string | 国家名 |

### getEmployeeFilterFields

```bash
xrxs-cli payroll getEmployeeFilterFields
  --filterBizType <filterBizType>
  --keyword <keyword>
```

> 请求方式：`GET`。无请求体，参数通过 `--<name> <value>` 传递。

参数：

| 参数 | 必填 | 类型 | 说明 |
|------|------|------|------|
| `--filterBizType` | 否 | string | 业务类型：1-员工搜索 2-入职记录 3-转正记录 4-调岗记录 5-离职记录 |
| `--keyword` | 否 | string | 筛选项关键字，为空不过滤 |

获取员工搜索的过滤条件字段配置。返回的 FilterFieldModel 仅为筛选项「配置」（`values`/`dateValues` 为空），调用方按规则填值后，作为 `searchEmployee` 的 `filters` 入参回传。

返回：

- `code`：状态码
- `status`：是否成功
- `message`：提示信息
- `data`：过滤条件字段配置数组（含 `fieldId`、`fieldName`、`labelName`、`fieldFilterType`、`unit`、`values`、`dateValues` 等，结构与 `searchEmployee` 的 `filters` 一致）

### searchEmployee

```bash
xrxs-cli payroll searchEmployee \
  --request-body '{
    "pageNo": 1,
    "pageSize": 20,
    "keyword": "<姓名/手机号/工号等关键字，可选>",
    "status": <员工状态，可选>,
    "filters": [<筛选条件，结构与 getEmployeeFilterFields 返回值一致，可选>]
  }'
```

> 请求方式：`POST`。请求体为 JSON 对象，通过 `--request-body '<JSON>'` 传递。

参数：

| 参数 | 必填 | 类型 | 说明 |
|------|------|------|------|
| `pageNo` | 否 | integer | 页码，从 1 开始，默认 1 |
| `pageSize` | 否 | integer | 每页条数，默认 20，上限 100 |
| `keyword` | 否 | string | 搜索关键字（姓名/手机号/工号等） |
| `status` | 否 | integer | 员工状态 |
| `filters` | 否 | array<object> | 筛选条件，结构与 `getEmployeeFilterFields` 返回值一致（含 `fieldId`、`fieldFilterType`、`values`、`dateValues`、`dicCode` 等） |

返回：

- `code`：状态码
- `status`：是否成功
- `message`：提示信息

`data` 主要字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `data.list` | array<object> | 员工列表 |
| `data.list[].name` | string | 姓名 |
| `data.list[].email` | string | 工作邮箱 |
| `data.list[].mobile` | string | 手机号 |
| `data.list[].status` | integer | 员工状态 |

> 员工搜索建议流程：先调用 `getEmployeeFilterFields` 获取可用的筛选字段配置，按需填值后作为 `searchEmployee` 的 `filters` 传入；若仅按姓名/手机号/工号模糊查找，直接传 `keyword` 即可。

### searchDepartment

```bash
xrxs-cli payroll searchDepartment
  --keyword <keyword>
  --limit <limit>
```

> 请求方式：`GET`。无请求体，参数通过 `--<name> <value>` 传递。

参数：

| 参数 | 必填 | 类型 | 说明 |
|------|------|------|------|
| `--keyword` | 是 | string | 搜索关键字（必填） |
| `--limit` | 否 | string | 返回结果最大条数，默认 50，最大 100（超过夹紧为 100） |

返回：

- `code`：状态码
- `status`：是否成功
- `message`：提示信息

`data` 主要字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `data[].id` | string | 部门id |
| `data[].code` | string | 部门code |
| `data[].name` | string | 部门名称 |
| `data[].path` | string | 部门中文名路径（如：总公司/研发部/前端组） |

### searchJob

```bash
xrxs-cli payroll searchJob
  --keyword <keyword>
  --limit <limit>
```

> 请求方式：`GET`。无请求体，参数通过 `--<name> <value>` 传递。

参数：

| 参数 | 必填 | 类型 | 说明 |
|------|------|------|------|
| `--keyword` | 是 | string | 搜索关键字（必填） |
| `--limit` | 否 | string | 返回结果最大条数，默认 50，最大 100（超过夹紧为 100） |

返回：

- `code`：状态码
- `status`：是否成功
- `message`：提示信息

`data` 主要字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `data[].code` | string | 岗位编码 |
| `data[].name` | string | 岗位名称 |
| `data[].type` | integer | 岗位类型<br><ul><br>    <li>0: 岗位分类</li><br>    <li>1: 岗位实体</li><br></ul> |
| `data[].jobId` | string | 岗位id |

### searchRank

```bash
xrxs-cli payroll searchRank
  --keyword <keyword>
  --limit <limit>
```

> 请求方式：`GET`。无请求体，参数通过 `--<name> <value>` 传递。

参数：

| 参数 | 必填 | 类型 | 说明 |
|------|------|------|------|
| `--keyword` | 是 | string | 搜索关键字（必填） |
| `--limit` | 否 | string | 返回结果最大条数，默认 50，最大 100（超过夹紧为 100） |

返回：

- `code`：状态码
- `status`：是否成功
- `message`：提示信息

`data` 主要字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `data[].name` | string | 职级名称 |
| `data[].rankId` | string | 职级id |
| `data[].levelId` | string | 职级类别id（所属职级分类） |

### searchCostCenter

```bash
xrxs-cli payroll searchCostCenter
  --keyword <keyword>
  --limit <limit>
```

> 请求方式：`GET`。无请求体，参数通过 `--<name> <value>` 传递。

参数：

| 参数 | 必填 | 类型 | 说明 |
|------|------|------|------|
| `--keyword` | 是 | string | 搜索关键字（必填） |
| `--limit` | 否 | string | 返回结果最大条数，默认 50，最大 100（超过夹紧为 100） |

返回：

- `code`：状态码
- `status`：是否成功
- `message`：提示信息

`data` 主要字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `data[].code` | string | 成本中心编码 |
| `data[].name` | string | 成本中心名称 |
| `data[].costId` | string | 成本中心id |

## 注意事项

- 写入/删除操作，执行前必须确认用户意图。
- 预览接口（路径/命令名以 `-preview` 结尾）调用后，xrxs-cli 会返回 `taskId`、`summaryHeaderMap`、`summaryData`、`originalName`、`riskLevel`。必须将其渲染为 `<confirm-card>` 组件，属性为 `taskId`、`summaryHeaderMap`（JSON 字符串）、`summaryData`（JSON 字符串）、`riskLevel`、`taskName`（取 `originalName`），禁止直接展示 JSON。
- 不要将 xrxs-cli 执行的命令返回给用户。


## 参考

- [payroll](../SKILL.md) -- 全部命令
