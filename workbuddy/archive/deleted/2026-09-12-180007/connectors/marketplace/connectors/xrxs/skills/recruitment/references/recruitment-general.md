---
name: recruitment-general
description: 招聘通用查询能力，包括职位、招聘需求、招聘渠道、招聘流程等通用查询接口。
---

# 招聘 - 通用查询

本场景覆盖招聘职位、需求、渠道、流程等通用查询接口，以及接口数较少的查询能力合并项。

### 查看接口完整信息

调用命令前，优先参考本文档中对该命令的入参、请求体格式及返回值的说明。如果文档已经描述得足够清晰、能够直接构造调用，则**不需要再执行** `xrxs-cli schema recruitment.<command>`。只有当文档中对某个命令的入参或返回值描述不明确、不足以完成调用时，才对该命令执行一次 `xrxs-cli schema recruitment.<command>` 进行确认。**仅对将要实际调用的命令做此检查**，同一命令最多检查一次；禁止为排查字段而批量轮询多个无关命令的 schema


例如：

```bash
xrxs-cli schema recruitment.getMyJobList
```

---

## getMyJobList

- **接口名称**：`getMyJobList`
- **描述**：获取当前人员负责的职位列表（按管理范围/权限过滤）
- **CLI 命令示例**：
  ```bash
  xrxs-cli recruitment getMyJobList --keyword Java --hire-status 0
  ```
- **参数说明**：
  - `--page-num`（string，可选）：页码。
  - `--page-size`（string，可选）：每页条数。
  - `--keyword`（string，可选）：职位名关键词。
  - `--hire-status`（string，可选）：职位状态，`0` 进行中，`1` 已关闭。
  - `--department-id`（string，可选）：部门 ID，来自员工模块部门接口。
  - `--custom-process-id`（string，可选）：招聘流程 ID，引用 `getProcessSettingList` 结果中的 `data.data.customProcessId`。
  - `--demand-id`（string，可选）：需求 ID，引用 `getBriefDemandList` 结果中的 `data.demandId`。

---

## getJobDetail

- **接口名称**：`getJobDetail`
- **描述**：获取职位详情
- **CLI 命令示例**：
  ```bash
  xrxs-cli recruitment getJobDetail --job-id JOB_123456
  ```
- **参数说明**：
  - `--job-id`（string，可选）：职位 ID，引用 `getMyJobList` 结果中的 `data.data.jobId`。

---

## getBriefDemandList

- **接口名称**：`getBriefDemandList`
- **描述**：获取公司的需求列表（按权限过滤，只含 id/name 等简要字段）
- **CLI 命令示例**：
  ```bash
  xrxs-cli recruitment getBriefDemandList
  ```
- **参数说明**：
  - `--module`（string，可选）：模块标识。

---

## getChannelList

- **接口名称**：`getChannelList`
- **描述**：获取来源渠道列表（公司全部渠道）
- **CLI 命令示例**：
  ```bash
  xrxs-cli recruitment getChannelList
  ```
- **参数说明**：无。

---

## getProcessSettingList

- **接口名称**：`getProcessSettingList`
- **描述**：获取公司的招聘流程列表
- **CLI 命令示例**：
  ```bash
  xrxs-cli recruitment getProcessSettingList --status 1
  ```
- **参数说明**：
  - `--page-num`（string，可选）：页码。
  - `--page-size`（string，可选）：每页条数。
  - `--status`（string，可选）：状态，`1` 启用，`0` 未启用，`null` 全部。

---

## getProcessSettingDetail

- **接口名称**：`getProcessSettingDetail`
- **描述**：获取招聘流程详情
- **CLI 命令示例**：
  ```bash
  xrxs-cli recruitment getProcessSettingDetail --custom-process-id 1001
  ```
- **参数说明**：
  - `--custom-process-id`（string，可选）：流程 ID，引用 `getProcessSettingList` 结果中的 `data.data.customProcessId`。
