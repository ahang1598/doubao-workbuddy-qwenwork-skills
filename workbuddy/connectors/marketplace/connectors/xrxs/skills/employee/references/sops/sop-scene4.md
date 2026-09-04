# 场景四：扫描指定周期内离职办理阻塞清单

> **阅读提示：** 本文档为 [`../sop-summary.md`](../sop-summary.md) 场景四的详细步骤，通用约定见 [`common.md`](common.md)。命中本场景后严格按下列步骤执行，不得跳过、不得自行发明等价命令序列。

**目标**：扫描指定周期内计划离职、今天离职以及已逾期尚未办结的员工，按紧急程度输出阻塞清单。

**调用流程**：

1. **获取离职记录筛选字段（可选但建议）**

   ```bash
   xrxs-cli employee getEmployeeFilterFields --filterBizType 5
   ```

   > **keyword 筛选建议**：`getEmployeeFilterFields` 返回的字段数量通常很多。如果只需要查询某个字段，建议加上 `--keyword <字段名/关键词>` 进行筛选，避免返回过多无关字段。特别是当需要查询以下关键词相关字段时，优先使用 keyword 筛选：**入职日期、转正日期、离职日期、调动日期、转正方式、考核方式、考核结果**。

2. **查询离职记录**

   ```bash
   xrxs-cli employee searchDismissRecord --request-body json
   ```

   请求体示例：

   ```json
   {
     "filters": [
       {
         "fieldName": "dismissDate",
         "fieldFilterType": 1,
         "dateValues": ["2026/07/15 00:00:00 时间戳", "2026/07/21 23:59:59 时间戳"]
       }
     ],
     "keyword": "",
     "pageNo": 1,
     "pageSize": 200
   }
   ```

   > 具体 `fieldName`、`fieldFilterType` 及时间戳格式，以 `getEmployeeFilterFields --filterBizType 5` 的返回为准。

3. **获取离职待处理事项**

   ```bash
   xrxs-cli employee getDismissPendingIssueTotal --employeeId <employeeId> --dismissDate <dismissDate>
   ```

   > 返回的待处理事项总数大于 0 的员工，即存在未办结事项。

**分类与紧急程度**：

| 优先级 | 分类 | 判定条件 |
|---|---|---|
| P0 最紧急 | 今天离职且仍有待处理事项 | 预计离职日期 = 今天，且 `getDismissPendingIssueTotal` 返回值 > 0 |
| P1 紧急 | 已逾期仍未办结 | 预计离职日期 < 今天，且待处理事项 > 0 |
| P2 提醒 | 计划离职有待处理事项 | 预计离职日期在指定周期内，且待处理事项 > 0 |
| 正常 | 无待处理事项 | 待处理事项 = 0 |

**输出建议**：

- 按 P0 → P1 → P2 分组输出；
- 每组内按预计离职日期升序排列；
- 每条记录包含：员工姓名、部门、预计离职日期、待处理事项数量、主要待办类型（若接口返回）。
