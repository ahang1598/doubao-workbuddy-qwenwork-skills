# 场景二：检查本周入职人员资料补齐情况

> **阅读提示：** 本文档为 [`../sop-summary.md`](../sop-summary.md) 场景二的详细步骤，通用约定见 [`common.md`](common.md)。命中本场景后严格按下列步骤执行，不得跳过、不得自行发明等价命令序列。

**目标**：检查从本周入职的人员，还有哪些必填资料尚未填写完整。

**调用流程**：

1. **获取入职记录筛选字段**

   ```bash
   xrxs-cli employee getEmployeeFilterFields --filterBizType 2
   ```

   > **keyword 筛选建议**：`getEmployeeFilterFields` 返回的字段数量通常很多。如果只需要查询某个字段，建议加上 `--keyword <字段名/关键词>` 进行筛选，避免返回过多无关字段。特别是当需要查询以下关键词相关字段时，优先使用 keyword 筛选：**入职日期、转正日期、离职日期、调动日期、转正方式、考核方式、考核结果**。
   >
   > `filterBizType=2` 对应「入职记录」。返回的字段仅作为筛选项配置，需按规则填值后作为 `filters` 入参回传。

2. **搜索本周的入职记录**

   ```bash
   xrxs-cli employee searchEntryRecord --request-body json
   ```

   请求体示例（本周待入职 + 本周已超期，二者均可能仍有资料待补齐）：

   ```json
   {
     "status": 0,
     "filters": [
       {
         "fieldName": "entryDate",
         "fieldFilterType": 1,
         "dateValues": ["本周开始时间戳", "本周结束时间戳"]
       }
     ],
     "keyword": "",
     "pageNo": 1,
     "pageSize": 100
   }
   ```

   > `searchEntryRecord` 是入职记录搜索接口，返回员工入职记录列表（含 `employeeId`、姓名、入职日期、部门、聘用形式等）。场景二需检查尚未完成入职的人员资料，因此必须按状态精确过滤并同时包含「待入职」和「已超期」两种状态——可从步骤 1 的筛选字段配置中获取对应 `key` 填入 `filters`（通常 `key: 1` 为待入职、`key: 3` 为已超期）。
   >
   > 具体 `fieldName`、`fieldFilterType` 及填值规则，以 `getEmployeeFilterFields --filterBizType 2` 的返回为准。
   >
   > ⚠️ 日期筛选值一律使用 `yyyy/MM/dd` 字符串（如 `["2026/08/10", "2026/08/16"]`），**不要用毫秒时间戳**——`searchEntryRecord` 用毫秒时间戳实测返回空结果（不报错，易误判为"该周期无人入职"），见 [`common.md`](common.md) 通用约定。

3. **批量获取员工入职表单数据**

   ```bash
   xrxs-cli employee getEntryPendingEmployeeForm --employeeIds <employeeIds> 
   ```


**判断逻辑**：

- 遍历第 2 步返回的员工列表，提取 `employeeIds`；
- 调用第 3 步批量获取表单，按 `setting`（表单结构）与 `values`（员工字段值）解析每位员工的字段；
- **读取每位员工的「聘用形式」字段**：
  - 若聘用形式为**正式**，则**非正式类型字段**即使 `required=1` 也视为非必填，不纳入缺失清单；
  - 若聘用形式为**非正式**（如实习、外包、劳务派遣等），则保持原有必填校验逻辑。
- 对每个员工，筛选出真正需要补齐的字段（`required=1` 且当前值为空，且未被正式聘用形式豁免）；
- 汇总输出「员工姓名 / 聘用形式 / 缺失字段名」清单。

**非正式类型字段识别：**

- 以 `getEntryPendingEmployeeForm` 返回的 `setting` 字段元数据为准（`values` 为员工值），满足以下任一条件即视为非正式类型字段：
  - 字段名（`fieldName`）、字段标签/显示名、或所属分组名中包含「非正式」「实习」「试用」「外包」「派遣」「劳务」等标识；
  - 字段配置中明确标注仅针对非正式聘用形式必填（如存在 `employmentForm` 作用范围且不含「正式」）。
- 若字段元数据无法明确判断是否属于非正式类型，则保守处理：仍按 `required=1` 校验，不在本次豁免。
