# appraisal 基础接口

> **前置条件：** 先阅读 [`../SKILL.md`](../SKILL.md) 了解全局能力。

基础接口相关操作。

## 适用场景

- 获取词典选项信息（CLI 版）
- 获取城市信息树（CLI 版）。
- 根据关键字搜索城市

## 推荐命令

### getDicOption

获取词典选项信息（CLI 版）

```bash
xrxs-cli appraisal getDicOption
```

> 请求方式：`GET`。无请求体，参数通过 `--<name> <value>` 传递。

参数：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--dic-code` | 否 | 词典编码 |

### getAreaV2tree

获取城市信息树（CLI 版）。

```bash
xrxs-cli appraisal getAreaV2tree
```

> 请求方式：`GET`。无请求体，参数通过 `--<name> <value>` 传递。

### searchCitys

根据关键字搜索城市

```bash
xrxs-cli appraisal searchCitys
```

> 请求方式：`GET`。无请求体，参数通过 `--<name> <value>` 传递。

参数：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--name` | 否 | 城市名称关键字，可为空 |

### searchDepartment

搜索部门

```bash
xrxs-cli appraisal searchDepartment \
  --keyword <keyword>
```

> 请求方式：`GET`。无请求体，参数通过 `--<name> <value>` 传递。

参数：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--keyword` | 是 | 搜索关键字（必填） |
| `--limit` | 否 | 返回结果最大条数，默认 50，最大 100（超过夹紧为 100） |

### searchJob

搜索岗位

```bash
xrxs-cli appraisal searchJob \
  --keyword <keyword>
```

> 请求方式：`GET`。无请求体，参数通过 `--<name> <value>` 传递。

参数：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--keyword` | 是 | 搜索关键字（必填） |
| `--limit` | 否 | 返回结果最大条数，默认 50，最大 100（超过夹紧为 100） |

### searchRank

搜索职级

```bash
xrxs-cli appraisal searchRank \
  --keyword <keyword>
```

> 请求方式：`GET`。无请求体，参数通过 `--<name> <value>` 传递。

参数：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--keyword` | 是 | 搜索关键字（必填） |
| `--limit` | 否 | 返回结果最大条数，默认 50，最大 100（超过夹紧为 100） |

### searchCostCenter

搜索成本中心

```bash
xrxs-cli appraisal searchCostCenter \
  --keyword <keyword>
```

> 请求方式：`GET`。无请求体，参数通过 `--<name> <value>` 传递。

参数：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--keyword` | 是 | 搜索关键字（必填） |
| `--limit` | 否 | 返回结果最大条数，默认 50，最大 100（超过夹紧为 100） |

### getAllCountry

获取所有国家

```bash
xrxs-cli appraisal getAllCountry
```

> 请求方式：`GET`。无请求体，参数通过 `--<name> <value>` 传递。

参数：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--keyword` | 否 | 国家名关键字，为空返回全部 |

### searchEmployee - 搜索员工

- **接口名称**：`searchEmployee` / 搜索员工
- **描述**：搜索员工
- **CLI 命令示例**：
  ```bash
  xrxs-cli appraisal searchEmployee --request-body json
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

### getEmployeeDetail

获取员工详情

```bash
xrxs-cli appraisal getEmployeeDetail \
  --employee-id <employeeId>
```

> 请求方式：`GET`。无请求体，参数通过 `--<name> <value>` 传递。

参数：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--employee-id` | 是 | 员工id |

## 注意事项

- 写入/删除操作，执行前必须确认用户意图。
- 可用 `--dry-run` 预览请求。

## 参考

- [appraisal](../SKILL.md) -- 全部命令