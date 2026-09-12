# 场景十：跳过被考核人（跳过考核）

> **阅读提示：** 本文档为场景十的详细步骤，通用约定见 [`common.md`](common.md)。命中本场景后严格按下列步骤执行，不得跳过、不得自行发明等价命令序列。

## 适用场景与触发话术

- 用户话术示例（含同义表达）：
  - 「帮我跳过张三在考核方案 cli-test1（2） 里的考核」
  - 「把李四从XX方案里跳过，这轮不用考核」
  - 「跳过XXX员工的考核」「XXX这轮免考核，跳过她」
- 关键词：跳过、跳过考核、跳过被考核人、免考核、不参加本轮考核。

> **注意区分（易混淆）：** 本场景跳过被考核人（`batchSkipAssessee`），**员工保留在方案名单中**，跳过其当前环节的待办（待办标记 `skipStatus=3` 管理员手动跳过）；[场景七](sop-scene7.md)终止被考核人（`batchTerminateAssessee`，**可逆**，可 `batchRestartAssessee` 恢复，员工移出考核流程，`assesseeStatus=1`）；[场景九](sop-scene9.md)删除被考核人（`deleteAssessee`，**不可逆**，删除名单记录）。用户说「跳过/免考核」走本场景，说「终止」走七，说「删除/删掉」走九。

## 接口说明

| 接口 | CLI 命令 | path | 用途 |
|------|----------|------|------|
| 跳过被考核人预览 | `xrxs-cli appraisal skipAssesseePreview` | `ajax-skip-assessee-preview.json` | 预览操作摘要，供用户确认 |
| 批量跳过被考核人 | `xrxs-cli appraisal batchSkipAssessee` | `ajax-skip-assessee.json` | 正式执行跳过 |

- 均为 `POST`，`Content-Type: application/json`，请求体用 `--request-body '{"...": ...}'` 传递。

### 请求体参数（两接口完全相同）

| 参数 | 必填 | 类型 | 说明 |
|------|------|------|------|
| `planId` | 是 | string | 方案ID |
| `assesseeEmpIds` | 是 | array\<string\> | 被考核人ID列表（员工ID），≤100 个，超 100 分批 |

```json
{"planId": "<方案ID>", "assesseeEmpIds": ["<员工ID1>", "<员工ID2>"]}
```

### 返回结构

- **预览**：`data` 含 `detailData`/`summaryData` + `detailHeaderShowField`/`summaryHeaderShowField`（与终止/删除预览同结构），按字段顺序渲染确认卡片。
- **执行**：`data` 含 `totalNum`（总操作人数）、`successNum`（成功人数）、`failNum`（失败人数）、`failDetails[]`（每项 `assesseeEmpId` + `reason`）。

### 跳过状态参考（`currEmpTodoInfo.currEmpTodoList[].skipStatus`）

0-正常处理 / 1-缺省跳过 / 2-重复跳过 / **3-管理员手动跳过** / 4-完成值跳过 / 5-校准人是本人-自动跳过 / 6-员工拒绝操作-跳过

## 前置信息

| 信息 | 必填 | 说明 |
|------|------|------|
| 方案ID | 是 | **优先取上下文已有方案**（对话中已定位或用户点名），直接用、不重复查询；仅上下文完全缺失时才补查一次 |
| 被考核人（姓名/手机号/工号/员工ID） | 是 | **优先取上下文已有员工ID**；缺失时用 `employee.searchEmployee` 按姓名/手机号搜员工即可，无需查方案名单；可多人批量 |
| 跳过范围确认 | 是 | 无需理由参数，但执行前必须与用户确认「跳哪些人、共 N 人」，不自行扩大范围 |

## 执行步骤

**步骤 1 — 确认跳过对象（上下文优先，尽量零查询）**

- 方案ID与员工ID**直接取自上下文**（用户点名方案/员工，或前序步骤已定位过），**不执行任何定位查询**。
- 仅当上下文缺少员工ID时，用**员工搜索**按姓名/手机号/工号定位（`employee.searchEmployee`，无需 `queryAssesseeInfos` 查方案名单）：
  ```bash
  xrxs-cli employee searchEmployee --fields "employeeId,employeeName,jobNumber,mobile" --request-body '{"keyword":"<姓名/手机号/工号>","status":0,"pageNo":1,"pageSize":20}'
  ```
  - `keyword` 支持姓名/手机号/工号模糊搜索；`status:0` 在职（跳过多为进行中方案的员工）。
  - 命中多个同名候选时按手机号/工号区分，列候选让用户确认，不猜。
- 仅当上下文缺少方案ID时，才补一次 `batchQueryPlanInfos` 按进行中+关键词定位方案。
- 多人批量：确认名单后，一次性放入 `assesseeEmpIds`（≤100）。

**步骤 2 — 预览 + 用户确认（核心）**

先执行权限检查，决定是否走预览确认：

```bash
xrxs-cli permission check appraisal-batchSkipAssessee
```

- 返回 `true`（已授权）→ 可直接执行 `batchSkipAssessee`（仍向用户说明操作范围）。
- 返回 `false`（或命令不可用）→ 必须先 `skipAssesseePreview` 渲染确认卡片，**等用户明确确认后**再执行：

```bash
xrxs-cli appraisal skipAssesseePreview --request-body '{"planId":"<planId>","assesseeEmpIds":["<员工ID1>","<员工ID2>"]}'
```

**步骤 3 — 执行并反馈**

```bash
xrxs-cli appraisal batchSkipAssessee --request-body '{"planId":"<planId>","assesseeEmpIds":["<员工ID1>","<员工ID2>"]}'
```

- 参数与预览完全相同（`planId` + `assesseeEmpIds`）。
- 执行结果即最终反馈：按 `successNum`/`failNum` 汇报成功人数，`failNum > 0` 时附 `failDetails`（人员+原因）；报错如实反馈，不掩盖。
- 反馈时说明：员工保留在方案名单中，本环节待办已标记为「管理员手动跳过」。

## 异常分支

| 异常情况 | 处理方式 |
|----------|----------|
| 上下文无方案/员工信息且补查不到 | 列出候选让用户确认，不猜、不强行执行 |
| 跳过人数超过 100 | 按 100 人/批分批预览与执行，逐批反馈 |
| 预览/执行报错 | 如实反馈（如方案状态不允许、人员状态不允许、无权限等），不掩盖 |
| `failNum > 0` | 附 `failDetails` 如实反馈，成功部分照常汇报 |

## 输出模板

```markdown
## 跳过被考核人 — <方案名称>（<方案ID>）

✅ 已跳过：<员工姓名>（工号）等 <successNum> 人，本轮免考核。
**说明**：员工保留在方案名单中，当前环节待办已标记为「管理员手动跳过」。
```
