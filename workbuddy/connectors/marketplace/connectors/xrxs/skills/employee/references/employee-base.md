---
name: employee-base
description: 基础支撑与引用接口，包括数据词典、地区城市、部门岗位职级成本中心查询
---

# 基础支撑接口

## 调用前准备

### 查看接口完整信息

本文档未覆盖的命令，可通过以下方式查看该接口的入参、返回值及使用明细（何时需要查 schema 的分级规则见 ../SKILL.md「查看接口完整信息」）：

```bash
xrxs-cli schema employee.<method>
```

例如：

```bash
xrxs-cli schema employee.getEmployeeDetail
```

这样可以获取该接口的字段类型、必填校验、示例值、返回结构等完整信息。

## getDicOption / 获取词典选项信息

**描述**：获取词典选项信息（CLI 版）

**CLI 命令示例**：
```bash
xrxs-cli employee getDicOption --dicCode gender
```

**参数说明**：
- `dicCode` (string, 选填): 词典编码

## getAreaV2tree / 获取城市信息树

**描述**：获取城市信息树（CLI 版）。

**CLI 命令示例**：
```bash
xrxs-cli employee getAreaV2tree
```

## searchCitys / 根据关键字搜索城市

**描述**：根据关键字搜索城市

**CLI 命令示例**：
```bash
xrxs-cli employee searchCitys --name 北京
```

**参数说明**：
- `name` (string, 选填): 城市名称关键字，可为空

## getEmployeeDetail / 获取员工详情

**描述**：获取员工详情

**CLI 命令示例**：
```bash
xrxs-cli employee getEmployeeDetail --employeeId 1001
```

**参数说明**：
- `employeeId` (string, 必填): 员工id

## getAllCountry / 获取所有国家

**描述**：获取所有国家

**CLI 命令示例**：
```bash
xrxs-cli employee getAllCountry --keyword 张三
```

**参数说明**：
- `keyword` (string, 选填): 国家名关键字，为空返回全部

## searchDepartment / 搜索部门

**描述**：搜索部门

**CLI 命令示例**：
```bash
xrxs-cli employee searchDepartment --keyword 技术部 --limit 50
```

**参数说明**：
- `keyword` (string, 必填): 搜索关键字（必填）
- `limit` (string, 选填): 返回结果最大条数，默认 50，最大 100（超过夹紧为 100）

## searchJob / 搜索岗位

**描述**：搜索岗位

**CLI 命令示例**：
```bash
xrxs-cli employee searchJob --keyword 工程师 --limit 50
```

**参数说明**：
- `keyword` (string, 必填): 搜索关键字（必填）
- `limit` (string, 选填): 返回结果最大条数，默认 50，最大 100（超过夹紧为 100）

## searchRank / 搜索职级

**描述**：搜索职级

**CLI 命令示例**：
```bash
xrxs-cli employee searchRank --keyword P5 --limit 50
```

**参数说明**：
- `keyword` (string, 必填): 搜索关键字（必填）
- `limit` (string, 选填): 返回结果最大条数，默认 50，最大 100（超过夹紧为 100）

## searchCostCenter / 搜索成本中心

**描述**：搜索成本中心

**CLI 命令示例**：
```bash
xrxs-cli employee searchCostCenter --keyword 研发中心 --limit 50
```

**参数说明**：
- `keyword` (string, 必填): 搜索关键字（必填）
- `limit` (string, 选填): 返回结果最大条数，默认 50，最大 100（超过夹紧为 100）
