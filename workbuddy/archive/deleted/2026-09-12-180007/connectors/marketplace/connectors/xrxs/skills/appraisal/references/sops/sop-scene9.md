# 场景九：删除被考核人

> **阅读提示：** 本文档为场景九的详细步骤，通用约定见 [`common.md`](common.md)。命中本场景后严格按下列步骤执行，不得跳过、不得自行发明等价命令序列。

## 适用场景与触发话术

- 用户话术示例（含同义表达）：
  - 「帮我删除87号员工在考核方案 cli-test1（2） 里的被考核记录」
  - 「把张三从XX考核方案中删掉」
  - 「XX员工在XX方案里的考核名单删除了吗，帮我删掉」
- 关键词：删除被考核人、删除考核记录、把XX从方案删除、移除名单。

> **注意区分：** 本场景删除的是**方案中的被考核人记录**（`deleteAssessee`，**不可逆、无恢复命令**）；[场景七](sop-scene7.md)终止被考核人（`batchTerminateAssessee`，**可逆**，可用 `batchRestartAssessee` 恢复）。两者操作对象相同但性质不同：**删除前必须先确认该员工已终止，未终止的必须先走终止流程**。用户说「终止」走七，说「删除/删掉」走九。

## 前置信息

| 信息 | 必填 | 说明 |
|------|------|------|
| 方案名称（或方案 ID） | 是 | 用于定位方案（**进行中**） |
| 被考核人（姓名/工号等关键词） | 是 | 用于在方案名单中定位待删除人员 |
| 删除原因 | 是 | `deleteReason` 必填，用户未提供时先追问，不自行编造 |

> **不可逆性：** 删除被考核人**不可恢复**（无恢复命令），执行前**必须**通过 `deleteAssesseePreview` 向用户展示操作摘要并明确确认；与终止（可恢复）不同，反馈时不要提示"可恢复"。

## 执行步骤

**步骤 1 — 定位方案（仅进行中）**

```bash
xrxs-cli appraisal batchQueryPlanInfos --request-body '{"planType":1,"planStatus":1,"planName":"<方案名关键词>"}'
```

- 复用[场景二](sop-scene2.md)步骤 1/2 的定位与候选确认逻辑（最多重试 1 次，搜不到/多个候选 → 列候选让用户选择，不自行猜测）。

**步骤 2 — 定位被考核人并判断终止状态（关键分支）**

```bash
xrxs-cli appraisal queryAssesseeInfos --fields "planId,planName,planType,assessBizId,employeeId,employeeName,jobNumber,department,flowName,inspectionStatus,assesseeStatus" --request-body '{"searchMode":"PLAN_SUBJECTS","planId":"<planId>","stage":{"mode":"ALL"},"keyword":"<员工姓名/工号>","pageNum":1,"pageSize":100}'
```

- **必须带 `--fields` 压缩**：`queryAssesseeInfos` 全字段返回极大（实测 37 人 ≈ 110KB），不带 `--fields` 会触发工具层 50KB 截断，模型会把截断误判为「接口服务内部错误」。
- **新范式核心：`searchMode:"PLAN_SUBJECTS"` + `planId` + `stage.mode:"ALL"`（全部）**，可加 `keyword` 精确定位（完整规则见 [`query-assessee-infos-guide.md`](../query-assessee-infos-guide.md)）。
- 一次请求即可定位（实测命中返回 1 行 ≈ 140 字节），**无需** `getPlanFlowList` 逐环节查询。
- `keyword` 查不到时：先不带 `keyword`、保留 `--fields` 再拉一次全名单（37 人 ≈ 9KB），本地按姓名匹配；仍查不到 → 走异常分支，不猜。
- 确认该员工确实在方案名单中，记录其 `employeeId`、`flowName`（所在环节）、**`assesseeStatus`（0-正常 / 1-已终止）**，并据此分情况：

| assesseeStatus | 含义 | 下一步 |
|----------------|------|--------|
| **1（已终止）** | 已被终止过 | **直接走步骤 5（删除流程）**，无需再终止 |
| **0（未终止）** | 仍在考核中 | **先执行步骤 3-4（先终止）**，终止成功后再走删除流程 |

**步骤 3 — 先终止被考核人（仅 assesseeStatus=0 未终止时）**

- 复用[场景七](sop-scene7.md)步骤 4-6 的终止流程：
  - 追问终止理由（`stopReason` 必填，不编造）；
  - `permission check appraisal-batchTerminateAssessee` → 未授权先 `terminateAssesseePreview` 展示摘要，等用户确认；
  - 执行 `xrxs-cli appraisal batchTerminateAssessee --request-body '{"planId":"<planId>","stopReason":"<终止理由>","assesseeEmpIds":["<employeeId>"]}'`。
- **终止成功后再继续删除**；终止失败/被用户拒绝 → 停止，不做删除（未终止的记录删除可能被系统拒绝或造成数据异常）。

**步骤 4 — 收集删除原因**

- 追问用户删除原因（`deleteReason` 必填），不自行编造。

**步骤 5 — 删除预览 + 用户确认**

**权限检查（permission check）**：调用正式命令 `deleteAssessee` 前，先执行权限检查判断用户是否已授权永久允许执行该命令：

```bash
xrxs-cli permission check appraisal-deleteAssessee
```

- 若返回 `true`，说明用户已授权，可直接调用 `deleteAssessee`。
- 若返回 `false`（或命令不可用），必须先调用 `deleteAssesseePreview` 展示操作摘要，等用户确认后再调用 `deleteAssessee`。

```bash
xrxs-cli appraisal deleteAssesseePreview --request-body '{"planId":"<planId>","assesseeEmpId":"<employeeId>","deleteReason":"<删除原因>"}'
```

- 预览返回的 `<confirm-card>` 确认卡片（含 `taskId`）必须渲染给用户，**等用户明确确认后**才进入下一步；未确认不得提交。
- ⚠️ 删除**不可逆**，预览摘要务必向用户强调"删除后不可恢复"。

**步骤 6 — 执行删除**

```bash
xrxs-cli appraisal deleteAssessee --request-body '{"planId":"<planId>","assesseeEmpId":"<employeeId>","deleteReason":"<删除原因>"}'
```

- 参数与预览完全相同（`planId` / `assesseeEmpId` 单个 / `deleteReason`）。
- 命令返回成功后再继续；若报错，如实反馈报错信息，不掩盖。

**步骤 7 — 复查验证**

- 用步骤 2 的同一命令（`searchMode:"PLAN_SUBJECTS"` + `planId` + `stage.mode:"ALL"` + `keyword` + `--fields`）**再查一次**，确认该员工已不在方案名单中（查不到 = 删除成功）。
- **复查一次即可，不轮询**：若仍在名单或命令报错，如实反馈失败原因，不编造成功。

**步骤 8 — 反馈**

- 向用户报成功，说明：员工、方案、删除原因。
- ⚠️ 反馈时**不要**提示"可恢复"（删除不可恢复）；如需"保留考核记录但移出名单"应建议使用[场景七](sop-scene7.md)终止。

## 异常分支

| 异常情况 | 处理方式 |
|----------|----------|
| 方案搜不到（进行中） | 最多重试 1 次，仍搜不到列出候选让用户确认；无进行中方案则如实告知 |
| 员工不在方案名单 | 如实告知：该员工可能不在该方案或已被删除；不猜、不强行执行 |
| 员工未终止且用户拒绝先终止 | 说明"未终止的被考核人需先终止后才能删除"，不做强制；若用户坚持直接删除，先按实际状态提示风险并让其明确确认 |
| 删除原因缺失 | 追问用户补充，不自行编造理由 |
| deleteAssessee 执行报错 | 如实反馈报错信息（如未终止不允许删除、方案状态不允许、无权限等），不掩盖 |
| 复查仍在名单 | 反馈删除未生效，请用户确认方案/员工状态后重试；**不自行轮询等待** |

## 输出模板

```markdown
## 删除被考核人 — <方案名称>（<方案ID>）

✅ 已删除：<员工姓名>（工号）在 <方案名称> 的被考核记录已删除。
**删除原因**：<deleteReason>

> ⚠️ 删除操作不可恢复；如需移出名单但保留考核记录，可使用「终止被考核人」操作。
```
