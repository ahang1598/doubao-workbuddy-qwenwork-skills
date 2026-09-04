---
name: recruitment-base
description: 招聘模块基础通用接口，包括词典选项、城市树、国家、部门、岗位、职级、成本中心、员工详情及员工搜索过滤条件等公共数据查询。
---

# 招聘 - 基础通用接口

本文件收录 `isBase=true` 的基础接口，供招聘主流程在构造入参时引用。

### 查看接口完整信息

调用命令前，优先参考本文档中对该命令的入参、请求体格式及返回值的说明。如果文档已经描述得足够清晰、能够直接构造调用，则**不需要再执行** `xrxs-cli schema recruitment.<command>`。只有当文档中对某个命令的入参或返回值描述不明确、不足以完成调用时，才对该命令执行一次 `xrxs-cli schema recruitment.<command>` 进行确认。**仅对将要实际调用的命令做此检查**，同一命令最多检查一次；禁止为排查字段而批量轮询多个无关命令的 schema

例如：

```bash
xrxs-cli schema recruitment.getDicOption
```

---

## getDicOption - 获取词典选项信息（CLI 版）

- **接口名称**：`getDicOption` / 获取词典选项信息（CLI 版）
- **描述**：获取词典选项信息（CLI 版）
- **CLI 命令示例**：
  ```bash
  xrxs-cli recruitment getDicOption --dic-code EDU_GRADE
  ```
- **参数说明**：
  - `--dic-code`（string，可选）：词典编码，如 `EDU_GRADE`、`RECRUIT_TYPE` 等。

---

## getAreaV2tree - 获取城市信息树（CLI 版）。

- **接口名称**：`getAreaV2tree` / 获取城市信息树（CLI 版）。
- **描述**：获取城市信息树（CLI 版）。
- **CLI 命令示例**：
  ```bash
  xrxs-cli recruitment getAreaV2tree
  ```
- **参数说明**：无。

---

## searchCitys - 根据关键字搜索城市

- **接口名称**：`searchCitys` / 根据关键字搜索城市
- **描述**：根据关键字搜索城市
- **CLI 命令示例**：
  ```bash
  xrxs-cli recruitment searchCitys --name 上海
  ```
- **参数说明**：
  - `--name`（string，可选）：城市名称关键字，为空时返回全部。

---

## searchDepartment - 搜索部门

- **接口名称**：`searchDepartment` / 搜索部门
- **描述**：搜索部门
- **CLI 命令示例**：
  ```bash
  xrxs-cli recruitment searchDepartment --keyword 研发 --limit 20
  ```
- **参数说明**：
  - `--keyword`（string，必填）：搜索关键字。
  - `--limit`（string，可选）：返回结果最大条数，默认 `50`，最大 `100`（超过夹紧为 `100`）。

**返回关键字段**：
- `id`（string）：部门 ID。
- `name`（string）：部门名称。
- `code`（string）：部门编码。
- `path`（string）：部门中文名路径（如：总公司/研发部/前端组）。

---

## searchJob - 搜索岗位

- **接口名称**：`searchJob` / 搜索岗位
- **描述**：搜索岗位
- **CLI 命令示例**：
  ```bash
  xrxs-cli recruitment searchJob --keyword Java --limit 20
  ```
- **参数说明**：
  - `--keyword`（string，必填）：搜索关键字。
  - `--limit`（string，可选）：返回结果最大条数，默认 `50`，最大 `100`。

**返回关键字段**：
- `jobId`（string）：岗位 ID。
- `name`（string）：岗位名称。
- `code`（string）：岗位编码。
- `type`（integer）：岗位类型，`0` 岗位分类，`1` 岗位实体。

---

## searchRank - 搜索职级

- **接口名称**：`searchRank` / 搜索职级
- **描述**：搜索职级
- **CLI 命令示例**：
  ```bash
  xrxs-cli recruitment searchRank --keyword 高级 --limit 20
  ```
- **参数说明**：
  - `--keyword`（string，必填）：搜索关键字。
  - `--limit`（string，可选）：返回结果最大条数，默认 `50`，最大 `100`。

**返回关键字段**：
- `rankId`（string）：职级 ID。
- `name`（string）：职级名称。
- `levelId`（string）：职级类别 ID。

---

## searchCostCenter - 搜索成本中心

- **接口名称**：`searchCostCenter` / 搜索成本中心
- **描述**：搜索成本中心
- **CLI 命令示例**：
  ```bash
  xrxs-cli recruitment searchCostCenter --keyword 上海 --limit 20
  ```
- **参数说明**：
  - `--keyword`（string，必填）：搜索关键字。
  - `--limit`（string，可选）：返回结果最大条数，默认 `50`，最大 `100`。

**返回关键字段**：
- `costId`（string）：成本中心 ID。
- `name`（string）：成本中心名称。
- `code`（string）：成本中心编码。

---

## getAllCountry - 获取所有国家

- **接口名称**：`getAllCountry` / 获取所有国家
- **描述**：获取所有国家
- **CLI 命令示例**：
  ```bash
  xrxs-cli recruitment getAllCountry --keyword 中国
  ```
- **参数说明**：
  - `--keyword`（string，可选）：国家名关键字，为空返回全部。

---

## getEmployeeFilterFields - 获取员工数据搜索过滤条件字段

- **接口名称**：`getEmployeeFilterFields` / 获取员工数据搜索过滤条件字段返回的 FilterFieldModel 仅为筛选项「配置」(values/dateValues 为空)
- **描述**：获取员工数据搜索过滤条件字段返回的 FilterFieldModel 仅为筛选项「配置」(values/dateValues 为空)
- **CLI 命令示例**：
  ```bash
  xrxs-cli recruitment getEmployeeFilterFields --filter-biz-type 1
  ```
- **参数说明**：
  - `--filter-biz-type`（string，可选）：业务类型，`1` 员工搜索，`2` 入职记录，`3` 转正记录，`4` 调岗记录，`5` 离职记录。
  - `--keyword`（string，可选）：筛选项关键字，为空不过滤。

**按 `fieldFilterType` 填值规则**：
- `1` 日期：填 `dateValues`，2 个元素 `[开始, 结束]`，格式为 yyyy/MM/dd 时间戳，单边留空用空串 `""`。
- `2` 数字：填 `values`，1 个元素，key 格式 `"min~max"`，分隔符支持半角 `~` 或全角 `～`，单边留空如 `"25~"`。
- `3` 文本：填 `values`，1 个元素，key 为关键词原文（模糊匹配）。
- `4` 选项：填 `values`，1 个或多个元素，key 取 `dataSource` 候选项的 key，多选取多个。
- `6` 地区（城市）、`7` 地区（县）：填 `values`，key 为地区 id。
- `8` 部门、`9` 虚拟部门：填 `values`，key 为部门 id，可多个。
- `10` 岗位：填 `values`，key 为岗位 id，可多个。
- `11` 员工：填 `values`，key 为员工 id，可多个。
- `12` 职级：填 `values`，key 为职级 id，可多个。
- `23` 多选：填 `values`，多个元素，key 取 `dataSource` 候选项的 key。
- `24` 多级单选：填 `values`，1 个元素，key 为所选层级值。
- `25` 多级多选：填 `values`，多个元素，key 为所选层级值。

---

## searchEmployee - 搜索员工

- **接口名称**：`searchEmployee` / 搜索员工
- **描述**：搜索员工
- **CLI 命令示例**：
  ```bash
  xrxs-cli recruitment searchEmployee --request-body json
  ```
- **参数说明**（JSON body）：
  - `keyword`（string，可选）：搜索关键字（姓名/手机号/工号等）。
  - `pageNo`（integer，可选）：页码，从 `1` 开始，默认 `1`。
  - `pageSize`（integer，可选）：每页条数，默认 `20`，上限 `100`。
  - `status`（integer，可选）：员工状态，`0` 在职，`1` 离职，`2` 待入职，默认 `0`。
  - `filters`（object[]，可选）：筛选条件数组，结构与 `getEmployeeFilterFields` 返回值一致，填值规则见该接口说明。

**返回关键字段**：
- `employeeId`（string）：员工 ID。
- `name`（string）：姓名。
- `email`（string）：工作邮箱。
- `mobile`（string）：手机号。
- `status`（integer）：员工状态。
- `departmentId`（string）：主部门 ID。

---

## getEmployeeDetail - 获取员工详情

- **接口名称**：`getEmployeeDetail` / 获取员工详情
- **描述**：获取员工详情
- **CLI 命令示例**：
  ```bash
  xrxs-cli recruitment getEmployeeDetail --employee-id EMP_123456
  ```
- **参数说明**：
  - `--employee-id`（string，必填）：员工 ID。
