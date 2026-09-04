---
name: employee-batch
description: 批量 Excel 操作，包括批量导入、模板下载、解析、校验与结果查询
---

# 批量操作

## 调用前准备

### 关于 `--request-body json`

本文档中部分 CLI 命令以 `--request-body json` 结尾，例如：

```bash
xrxs-cli employee batchParseExcel --request-body json
```

这里的 `json` **不是参数值**，而是声明该接口需要以 **JSON 格式**传入请求体。具体 JSON 结构请通过 `xrxs-cli schema employee.<method>` 获取完整参数说明。

### 查看接口完整信息

本文档未覆盖的命令，可通过以下方式查看该接口的入参、返回值及使用明细（何时需要查 schema 的分级规则见 ../SKILL.md「查看接口完整信息」）：

```bash
xrxs-cli schema employee.<method>
```

例如：

```bash
xrxs-cli schema employee.batchParseExcel
```

这样可以获取该接口的字段类型、必填校验、示例值、返回结构等完整信息。

### 批量类型说明

以下批量接口均需提供 `type` 参数，取值及含义如下：

- `EmployeeEducationAdd`：批量添加教育经历
- `EmployeeWorkAdd`：批量添加工作经历
- `EmployeeTrainingAdd`：批量添加培训经历
- `EmployeeCertificateAdd`：批量添加证书
- `EmployeeContactsAdd`：批量添加联系人
- `EmployeeEducationUpdate`：批量更新教育经历
- `EmployeeWorkUpdate`：批量更新工作经历
- `EmployeeTrainingUpdate`：批量更新培训经历
- `EmployeeCertificateUpdate`：批量更新证书
- `EmployeeContactsUpdate`：批量更新联系人
- `EmployeeMobileUpdate`：批量更新手机号
- `EmployeePartJobUpdate`：批量更新兼职信息
- `EmployeePartJobAdd`：批量添加兼职信息
- `EmployeeCustomGroupAdd`：批量添加自定义分组
- `EmployeeCustomGroupUpdate`：批量更新自定义分组
- `EmployeeChildrenInfoAdd`：批量添加子女信息
- `EmployeeChildrenInfoUpdate`：批量更新子女信息
- `EmployeeAdd`：批量添加员工
- `EmployeeModify`：批量更新员工
- `EmployeeCareerAdd`：批量添加成长记录
- `EmployeeStockAdd`：批量添加期权
- `EmployeeDismissAdd`：批量添加离职员工
- `EmployeeDismissUpdate`：批量更新离职员工信息
- `EmployeePreEntryAdd`：批量添加待入职员工
- `EmployeeModifyMobile`：批量更新手机号
- `EmployeeRewardPunishAdd`：批量添加奖惩信息

## batchListBizTypes / 获取批量excel操作支持的业务

**描述**：获取批量excel操作支持的业务

**CLI 命令示例**：
```bash
xrxs-cli employee batchListBizTypes
```

**返回值说明**：
- `data` (array): 支持的批量业务列表
  - `name` (string): 业务类型名称
  - `type` (string): 批量类型（取值见 `com.xrxs.client.cornerstone.enums.EBatchType`，如 `EmployeeEducationAdd`、`EmployeeAdd` 等）
  - `groupId` (string): 字段组id（固定字段组可能为空，自定义字段组必填）
- `code` (integer): 状态码
- `status` (boolean): 业务状态
- `message` (string): 提示信息

## batchInit / 批量excel初始化

**描述**：批量excel初始化

**CLI 命令示例**：
```bash
xrxs-cli employee batchInit --type xxx --groupId xxx
```

**参数说明**：
- `type` (string, 必填): 批量类型（必填，取值见上方「批量类型说明」）
- `groupId` (string, 选填): 字段组id（可选，自定义字段组批量时必填）

## batchDownloadTemplate / 下载批量excel模板

**描述**：下载批量excel模板

**CLI 命令示例**：
```bash
xrxs-cli employee batchDownloadTemplate --type xxx --groupId xxx
```

**参数说明**：
- `type` (string, 必填): 批量类型（必填，取值见上方「批量类型说明」）
- `groupId` (string, 选填): 字段组id（可选，自定义字段组批量时必填）

## batchParseExcel / 解析批量excel

**描述**：解析批量excel

**CLI 命令示例**：
```bash
xrxs-cli employee batchParseExcel --type xxx --request-body json
```

**参数说明**：
- `type` (string, 必填): 批量类型（必填，取值见上方「批量类型说明」）

**请求体说明**：
- `file` (file): excel 文件（必填）

> ⚠️ 写入/删除操作前必须确认用户意图。

## batchPreCheckField / 批量excel预检字段

**描述**：批量excel预检字段

**CLI 命令示例**：
```bash
xrxs-cli employee batchPreCheckField --request-body json
```

**请求体说明**：
- `key` (string): 解析 excel 返回的缓存key
- `type` (string): 批量类型（必填，取值见上方「批量类型说明」）
- `headerMap` (object): 表头映射（key-表头字段，value-字段名）

## batchPreCheckBatch / 批量excel预检

**描述**：批量excel预检

**CLI 命令示例**：
```bash
xrxs-cli employee batchPreCheckBatch --request-body json
```

**请求体说明**：
- `key` (string): 解析 excel 返回的缓存key
- `type` (string): 批量类型（必填，取值见上方「批量类型说明」）
- `headerMap` (object): 表头映射（key-表头字段，value-字段名）

## batchUploadBatchPreview / 批量excel上传预览确认

**描述**：批量excel上传,预览确认

**CLI 命令示例**：
```bash
xrxs-cli employee batchUploadBatchPreview --request-body json
```

**请求体说明**：
- `key` (string): 解析 excel 返回的缓存key
- `type` (string): 批量类型（必填，取值见上方「批量类型说明」）
- `groupId` (string): 字段组id（可选，自定义字段组批量时必填）
- `headerMap` (object): 表头映射（key-表头字段，value-字段名）

## batchUploadBatch / 批量excel上传

**描述**：批量excel上传

**CLI 命令示例**：
```bash
xrxs-cli employee batchUploadBatch --request-body json
```

**请求体说明**：
- `key` (string): 解析 excel 返回的缓存key
- `type` (string): 批量类型（必填，取值见上方「批量类型说明」）
- `groupId` (string): 字段组id（可选，自定义字段组批量时必填）
- `headerMap` (object): 表头映射（key-表头字段，value-字段名）

> ⚠️ 写入/删除操作前必须确认用户意图。

## batchQueryBatchResult / 查询批量excel上传结果

**描述**：查询批量excel上传结果

**CLI 命令示例**：
```bash
xrxs-cli employee batchQueryBatchResult --cacheKey xxx --type xxx
```

**参数说明**：
- `cacheKey` (string, 选填): 缓存key（uploadBatch 返回）
- `type` (string, 必填): 批量类型（必填，取值见上方「批量类型说明」）
