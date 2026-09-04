# 场景五：批量操作 Excel（教育经历、工作经历、培训经历、证书、联系人、手机号、兼职、自定义分组、子女信息、员工、成长记录、期权、离职、待入职、奖惩等）

> **阅读提示：** 本文档为 [`../sop-summary.md`](../sop-summary.md) 场景五的详细步骤，通用约定见 [`common.md`](common.md)。命中本场景后严格按下列步骤执行，不得跳过、不得自行发明等价命令序列。

**目标**：根据用户指定的批量类型，通过上传 Excel 完成批量添加/更新操作。正式提交前必须向用户确认意图。

**支持的批量类型**：`EmployeeEducationAdd`、`EmployeeWorkAdd`、`EmployeeTrainingAdd`、`EmployeeCertificateAdd`、`EmployeeContactsAdd`、`EmployeeEducationUpdate`、`EmployeeWorkUpdate`、`EmployeeTrainingUpdate`、`EmployeeCertificateUpdate`、`EmployeeContactsUpdate`、`EmployeeMobileUpdate`、`EmployeePartJobUpdate`、`EmployeePartJobAdd`、`EmployeeCustomGroupAdd`、`EmployeeCustomGroupUpdate`、`EmployeeChildrenInfoAdd`、`EmployeeChildrenInfoUpdate`、`EmployeeAdd`、`EmployeeModify`、`EmployeeCareerAdd`、`EmployeeStockAdd`、`EmployeeDismissAdd`、`EmployeeDismissUpdate`、`EmployeePreEntryAdd`、`EmployeeModifyMobile`、`EmployeeRewardPunishAdd`。

**权限检查（permission check）**：调用正式上传接口 `batchUploadBatch` 前，先执行权限检查判断用户是否已授权永久允许执行该命令：

```bash
xrxs-cli permission check employee-batchUploadBatch
```

- 若返回 `true`，说明用户已授权，可直接调用 `batchUploadBatch`。
- 若返回 `false`，说明用户未授权，必须先调用 `batchUploadBatchPreview` 展示操作摘要，等用户确认后再调用 `batchUploadBatch`。

**调用流程**：

### 步骤 1：确认批量类型并获取系统字段定义

1. **获取支持的批量业务类型**

   ```bash
   xrxs-cli employee batchListBizTypes
   ```

   从返回的 `data` 中找到用户指定的业务，记录其 `type` 与 `groupId`（固定字段组可能为空，自定义字段组必填）。

2. **批量初始化，获取系统字段定义**

   ```bash
   xrxs-cli employee batchInit --type <type> --groupId <groupId>
   ```

   记录返回的 `headerName`，结构为 `{英文 key: 中文列名}`，这是「系统字段定义」。

### 步骤 2：下载并解析用户 Excel

3. **根据文件 ID 下载 Excel 到本地**

   用户需提供 Excel 文件的 `fileId`，调用辅助工具 `download_file_for_cli`（参数为 `fileId`），工具将文件下载到服务器本地并返回本地绝对路径。

   > 注意：`download_file_for_cli` 是工具调用，不是 `xrxs-cli` 命令。调用方式相当于传入参数 `{"fileId": "<fileId>"}`，返回 `"/path/to/local/excel.xlsx"`。

4. **解析 Excel**

   ```bash
   xrxs-cli employee batchParseExcel --type <type> --request-body json
   ```

   请求体示例：

   ```json
   {
     "file": "/path/to/local/excel.xlsx"
   }
   ```

   记录返回的 `key`、`userHeader`（结构为 `{header0/header1...: 中文列名}`）和 `totalRow`。

   > ⚠️ 若返回没有 `key`，或 `totalRow == 0`，立即终止流程并告知用户：Excel 为空或解析失败，无法继续上传。

### 步骤 3：构造 headerMap 并执行上传

5. **构造 `headerMap`**

   用步骤 1 得到的 `headerName`（`英文 key: 中文列名`）与步骤 2 得到的 `userHeader`（`headerN: 中文列名`）按「中文列名」做匹配：

   - 匹配成功 → `{headerN: 英文 key}`
   - 匹配不到 → `{headerN: "unselect"}`

   最终 `headerMap` 形如：

   ```json
   {
     "header0": "employeeName",
     "header1": "mobile",
     "header2": "unselect"
   }
   ```

6. **上传提交**

   先执行权限检查：

   ```bash
   xrxs-cli permission check employee-batchUploadBatch
   ```

   - **已授权（`true`）**：直接调用 `batchUploadBatch`

     ```bash
     xrxs-cli employee batchUploadBatch --request-body json
     ```

     请求体示例：

     ```json
     {
       "key": "<batchParseExcel 返回的 key>",
       "type": "<batchListBizTypes 返回的 type>",
       "groupId": "<batchListBizTypes 返回的 groupId>",
       "headerMap": {
         "header0": "employeeName",
         "header1": "mobile",
         "header2": "unselect"
       }
     }
     ```

   - **未授权（`false`）**：先 preview 再提交

     1. 调用 preview：

        ```bash
        xrxs-cli employee batchUploadBatchPreview --request-body json
        ```

        请求体与 `batchUploadBatch` 相同。

     2. 向用户展示 preview 返回的摘要（如 `totalCount`、明细等），取得明确确认。

     3. 用户确认后调用正式提交：

        ```bash
        xrxs-cli employee batchUploadBatch --request-body json
        ```

        请求体与 preview 保持一致。

   > ⚠️ `batchUploadBatch` 为写入操作，执行前必须向用户确认意图；preview 或提交异常时，先处理后再执行正式提交。

### 步骤 4：轮询上传结果

7. **轮询查询批量结果**

   ```bash
   xrxs-cli employee batchQueryBatchResult --cacheKey <key> --type <type>
   ```

   每隔 **3 秒** 轮询一次，直到返回的 `data.status == true` 结束。

   - 若 `data.success == 1`：导入成功，向用户汇报成功结果。
   - 否则：将 `errors`、`excelErrorDataList`、`errorRowNums`、`warnings` 一并整理后返回给用户，并说明失败原因。

**关键约束**：

- **必须按顺序执行**：先 `batchListBizTypes` → `batchInit` → `download_file_for_cli` → `batchParseExcel` → `batchUploadBatchPreview/batchUploadBatch` → `batchQueryBatchResult`。
- **`headerMap` 构造必须基于中文列名匹配**：禁止直接按列顺序或猜测字段名映射；未匹配列必须填 `"unselect"`。
- **`batchParseExcel` 返回无 `key` 或 `totalRow == 0` 时必须终止**：不进入后续上传步骤。
- **轮询必须有退出条件**：以 `data.status == true` 为结束条件；禁止无限轮询。
- **同一 `key` 的上传不要重复提交**：preview/正式提交使用同一个 `key`，用户确认后仅执行一次正式上传。

**安全规则**：

- `batchUploadBatch` 为写入操作，执行前必须向用户确认意图。
- preview 或提交异常时，先根据错误信息处理（如补充必填字段、修正 Excel 等），再重新 preview 或提交。
