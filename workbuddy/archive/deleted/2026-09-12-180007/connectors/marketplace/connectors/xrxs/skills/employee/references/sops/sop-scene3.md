# 场景三：批量入职

> **阅读提示：** 本文档为 [`../sop-summary.md`](../sop-summary.md) 场景三的详细步骤，通用约定见 [`common.md`](common.md)。命中本场景后严格按下列步骤执行，不得跳过、不得自行发明等价命令序列。

**目标**：对目标员工批量完成入职操作。正式提交前必须向用户确认意图。

**权限检查（permission check）**：调用正式入职接口 `entryPendingEmployee` 前，先执行权限检查判断用户是否已授权永久允许执行该命令：

```bash
xrxs-cli permission check employee-entryPendingEmployee
```

- 若返回 `true`，说明用户已授权，可直接调用 `entryPendingEmployee`。
- 若返回 `false`，说明用户未授权，必须先调用 `entryPendingEmployeePreview` 展示操作摘要，等用户确认后再调用 `entryPendingEmployee`。

**调用流程**：

### 路径 A：已知目标员工 ID（推荐）

若用户或上游上下文已提供待入职员工的 `employeeId`（如「给 ID 为 xxx 和 yyy 的两位员工办理入职」），**直接获取表单**，跳过筛选字段与搜索步骤。

1. **批量获取入职表单数据（一次覆盖全部目标员工）**

   ```bash
   xrxs-cli employee getEntryPendingEmployeeForm --employeeIds <employeeIds>
   ```

   > 必须一次传入本次需要入职的**全部**员工 ID，禁止只查部分人后就进入后续步骤。返回结果中 `setting` 为表单结构，`values` 为各员工字段值，后续 preview/提交需从 `setting` 取结构、从 `values` 取值后拼接成完整表单。

2. **入职预览**

   ```bash
   xrxs-cli employee entryPendingEmployeePreview --request-body json
   ```

   > ⚠️ **preview 必须携带步骤 1 返回的完整 form 数据**：需从 `getEntryPendingEmployeeForm` 返回的 `setting` 获取表单结构、从 `values` 获取各员工字段值后拼接成完整表单，并覆盖用户本次需要修改的员工信息；仅传 `employeeId` 会导致返回 `totalCount: 0` 且耗时极长。preview 用于生成操作摘要供用户确认，同时暴露表单校验问题。

3. **正式批量入职**

   ```bash
   xrxs-cli employee entryPendingEmployee --request-body json
   ```

   > ⚠️ 写入操作，执行前必须向用户展示 preview 返回的待入职员工名单、入职日期等摘要，并取得明确确认。确认后使用与 preview 相同的完整 form 数据提交（即从 `setting` + `values` 拼接并覆盖修改后的表单数据）。

### 路径 B：按关键字在待入职列表中查找员工

若用户给出姓名/手机号/工号等关键字但未提供待入职员工 ID（如「给张三办理入职」），或仅说「批量入职待入职员工」但未给出具体人员，按以下步骤在**待入职记录列表**中查找：

1. **获取入职记录筛选字段**

   ```bash
   xrxs-cli employee getEmployeeFilterFields --filterBizType 2
   ```

   > **keyword 筛选建议**：`getEmployeeFilterFields` 返回的字段数量通常很多。如果只需要查询某个字段，建议加上 `--keyword <字段名/关键词>` 进行筛选，避免返回过多无关字段。特别是当需要查询以下关键词相关字段时，优先使用 keyword 筛选：**入职日期、转正日期、离职日期、调动日期、转正方式、考核方式、考核结果**。

2. **搜索待入职记录中的目标员工**

   ```bash
   xrxs-cli employee searchEntryRecord --request-body json
   ```

   请求体示例（同时匹配「待入职」和「已超期」，二者均属于待办理入职的未处理记录）：

   ```json
   {
     "filters": [],
     "keyword": "张三",
     "pageNo": 1,
     "pageSize": 100
   }
   ```

   > `searchEntryRecord` 是入职记录搜索接口，返回员工入职记录列表（含 `employeeId`、姓名、入职日期、部门、聘用形式等），**覆盖所有员工的入职记录**（含已入职、待入职、已超期等），不限于待入职。场景三需批量办理尚未正式入职的员工，因此必须按状态精确过滤并同时包含「待入职」和「已超期」两种状态——可从步骤 1 的筛选字段配置中获取对应 `key` 填入 `filters`（通常 `key: 1` 为待入职、`key: 3` 为已超期）。
   >
   > 若过滤后返回 0 条，说明待入职/已超期列表中无匹配人员，流程终止；若返回多条，列出候选信息（姓名、部门、入职日期、当前状态等）供用户确认，**不得继续猜测或批量操作全部结果**。

3. **批量获取入职表单数据**

   ```bash
   xrxs-cli employee getEntryPendingEmployeeForm --employeeIds <employeeIds>
   ```

4. **入职预览**

   ```bash
   xrxs-cli employee entryPendingEmployeePreview --request-body json
   ```

5. **正式批量入职**

   ```bash
   xrxs-cli employee entryPendingEmployee --request-body json
   ```

**关键约束**：

- **禁止重复获取表单**：`getEntryPendingEmployeeForm` 一次批量查询已返回全部目标员工的表单后，不得再对单个员工重复调用。
- **必须覆盖全部目标员工**：preview 和正式提交的 request-body 必须包含本次要入职的**所有**员工，不能只提交其中一部分。
- **不强制调用 `validateEntryPendingEmployee`**：场景三以 `entryPendingEmployeePreview` 作为最终校验与摘要生成步骤。若 preview 已返回可入职摘要，无需再额外调用 `validateEntryPendingEmployee`；若 preview 报字段错误，按错误提示补充信息后再 preview。

**安全规则**：

- `entryPendingEmployee` 为写入操作，执行前必须向用户确认意图；preview 或提交异常时，先处理后再执行正式提交。
