# 场景一：员工转正记录查询与分析

> **阅读提示：** 本文档为 [`../sop-summary.md`](../sop-summary.md) 场景一的详细步骤，通用约定见 [`common.md`](common.md)。命中本场景后严格按下列步骤执行，不得跳过、不得自行发明等价命令序列。

## 适用场景与触发话术

- 用户话术示例（含同义表达）：
  - 「帮我查一下未来一周应转正的员工」
  - 「最近有哪些员工逾期转正了，帮我分析一下原因」
  - 「查一下已超期未转正的员工名单」
  - 「看看本月有哪些人要转正，他们的转正审批状态是什么」
  - 「转正记录里哪些人是到期自动转正的」
- 关键词：转正、应转正、待转正、已转正、逾期、超期、转正记录、转正审批、转正方式、考核。

> **原则：** 凡是用户询问与「员工转正记录」相关的问题，无论带不带时间窗口、无论要不要分析原因、无论是否按状态查名单，**统一走本场景**，不再拆分为多个转正子场景。

## 前置信息

| 信息 | 必填 | 说明 |
|------|------|------|
| 时间窗口 / 状态条件 | 否 | 用户给出则按条件过滤；未给出则全量拉取转正记录后本地分析 |
| 具体员工姓名/工号 | 否 | 用户给出时作为 `keyword` 传入；未给出时按窗口/状态汇总 |

## 执行步骤

> **零详情查询约束（重要）**>
> 本场景默认只做**列表级查询与分析**。只要用户没有明确说「查询明细」「查某个员工的转正详情/表单」「看某人的转正资料」等，**一律只调用 `searchRegularRecord` 返回的列表字段进行分析**，禁止调用 `getRegularFormData`、`getEmployeeDetail`、`getProbationTasks`、`getProbationParticipants` 等单个/批量员工详情或表单接口，禁止调用 `workflow` 审批流接口。

### 步骤 1 — 获取转正记录筛选字段

```bash
xrxs-cli employee getEmployeeFilterFields --filterBizType 3 --keyword 转正
```

> **keyword 筛选建议**：`getEmployeeFilterFields` 返回的字段数量通常很多，全量返回容易超过上下文长度限制。本场景需用到「预计转正日期」「转正记录状态」「转正审批状态」「转正方式」等字段，优先使用 `--keyword 转正` 一次获取这些相关字段定义，避免返回全部无关字段导致截断。
>
> 若只需按单个字段（如仅按「预计转正日期」）过滤，可改用更精确的 `--keyword 转正日期`；**禁止用不同 `--keyword` 反复轮询**。

- `filterBizType=3` 对应「转正记录」；确认「预计转正日期」「转正记录状态」「转正审批状态」等字段的完整结构，**以返回为准，不猜字段名**。
- 该接口一次返回全部筛选字段定义，禁止用不同 `--keyword` 反复轮询。

### 步骤 2 — 搜索转正记录

```bash
xrxs-cli employee searchRegularRecord --request-body json
```

请求体示例（按时间窗口过滤）：

```json
{
  "filters": [
    {
      "fieldId": "<取自步骤1的fieldId>",
      "listGroupId": "<取自步骤1的listGroupId>",
      "documentType": "<取自步骤1的documentType>",
      "dicType": "<取自步骤1的dicType>",
      "dataSource": "<取自步骤1的dataSource>",
      "fieldName": "<预计转正日期字段名>",
      "fieldFilterType": 1,
      "dateValues": ["<yyyy/MM/dd>", "<yyyy/MM/dd>"]
    }
  ],
  "keyword": "",
  "pageNo": 1,
  "pageSize": 100
}
```

- `filters` 必须原样回传步骤 1 返回的完整字段条目，仅填充 `values` 或 `dateValues`；只传最小结构会报 `111005000` 未知错误。
- 日期类 `dateValues` 使用 `yyyy/MM/dd` 字符串，**不是毫秒时间戳**。
- 分页拉全（遵守「分页停止条件」）。
- 若用户明确要按转正记录状态查（如「已超期」「待转正」），优先从步骤 1 获取 `regularRecordStatus` 筛选项并填入 `filters` 一次查出；若过滤报错或混入其他状态，再回退 `filters: []` + 全量拉取后本地过滤。

### 步骤 3 — 查询转正规则开关

```bash
xrxs-cli employee getHumanRules
```

- 目的：确认公司是否开启「必须考核通过才能转正」规则开关。
- 分析时将该开关与 `searchRegularRecord` 返回的 `appraisalStatus`（考核状态）结合使用。

### 步骤 4 — 基于转正方式、审批状态与规则开关分析

`searchRegularRecord` 返回的关键字段（以实际返回为准）：

| 字段 | 含义 |
|------|------|
| `name` | 姓名 |
| `employeeId` | 员工ID |
| `mobile` | 手机号 |
| `employeeStatus` | 员工状态 |
| `regularDate` | 应转正日期 |
| `regularRecordStatus` | 转正记录状态：`1` 待转正 / `2` 已转正 / `3` 已超期 / `4` 未通过 |
| `regularApprovalStatus` | 转正审批状态：`-1` 未发起 / `0` 审批中 / `1` 通过 / `2` 驳回 / `3` 撤销 |
| `regularForm` | 转正方式 |
| `appraisalStatus` | 考核状态 |

**分析规则：**

1. **到期自动转正**
   - 若 `regularForm` 表示「到期自动转正」，则该员工到转正日期后系统会自动完成转正，**不需要发起审批**。
   - 此时 `regularApprovalStatus` 通常为空或无效，分析结论应明确标注「到期自动转正，无需审批」。

2. **非自动转正（需审批）**
   - 根据 `regularApprovalStatus` 判断当前处于哪个阶段：
     - `-1` 未发起：尚未发起转正审批，若已到应转正日期则构成逾期风险。
     - `0` 审批中：审批流程正在进行。
     - `1` 通过：审批已通过，等待或已完成转正生效。
     - `2` 驳回 / `3` 撤销：审批被退回或撤销，需要重新处理。

3. **考核与规则开关**
   - 若 `getHumanRules` 返回「必须考核通过才能转正」开关为开启：
     - `appraisalStatus` 为未通过/无考核记录 → 构成转正阻断条件，应标注「需先完成考核」。
     - `appraisalStatus` 为已通过 → 考核不阻断。
   - 若开关未开启：
     - 考核状态作为参考信息，不直接构成阻断。

4. **逾期判定**
   - `regularRecordStatus = 3`（已超期）或 `regularDate < 今天` 且 `regularRecordStatus != 2` → 逾期。

### 步骤 5 — 组织输出

- 输出内容完全基于 `searchRegularRecord` 与 `getHumanRules` 的返回，**禁止编造字段**。
- 根据用户问题的侧重点组织答案：
  - 用户要名单 → 列出姓名、应转正日期、转正方式、审批状态、考核状态。
  - 用户要原因分析 → 对逾期/未通过/审批未发起等记录，结合转正方式和规则开关说明原因。
  - 用户只要状态统计 → 按 `regularRecordStatus` 或 `regularApprovalStatus` 分组计数。
- 返回为空时如实报告；返回多条且用户仅给姓名关键字时，列出候选供用户确认。

## 异常分支

| 异常情况 | 处理方式 |
|----------|----------|
| `searchRegularRecord` 返回为空 | 确认日期字段与 filters 格式无误后，如实报告无匹配转正记录 |
| 关键字段缺失 | 以实际返回字段为准，缺失字段不展示、不推导、不编造 |
| 用户问题同时涉及转正记录以外的操作（如批量办理转正） | 本场景只负责查询与分析；若需执行转正保存，回退到 `SKILL.md` 通用规则或 `employee-regular.md` 的写入流程 |
