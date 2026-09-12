# 场景七：终止被考核人

> **阅读提示：** 本文档为场景七的详细步骤，通用约定见 [`common.md`](common.md)。命中本场景后严格按下列步骤执行，不得跳过、不得自行发明等价命令序列。

## 适用场景与触发话术

- 用户话术示例（含同义表达）：
  - 「帮我终止87号员工在考核方案 cli-test1（2） 里的考核，终止理由：员工已离职」
  - 「XX员工离职了，把TA在XXX方案里的考核终止掉」
  - 「把张三从XX考核方案中终止考核」
- 关键词：终止考核（某人）、终止被考核人、把XX移出考核、离职终止、停掉某人的考核。

> **注意区分：** 本场景终止的是**方案中的部分被考核人**（`batchTerminateAssessee`，可批量，每次最多 100 人）；用户说「终止XX**方案**」走[场景二](sop-scene2.md)（`stopPlan`，终止整个方案）。两者操作对象不同，不要混淆。

## 前置信息

| 信息 | 必填 | 说明 |
|------|------|------|
| 方案名称（或方案 ID） | 是 | 用于定位方案（**进行中**） |
| 被考核人（姓名/工号等关键词） | 是 | 用于在方案名单中定位待终止人员 |
| 终止理由 | 是 | `stopReason` 必填，用户未提供时先追问，不自行编造 |

> **可逆性：** 终止被考核人是可逆操作，终止后可用 `batchRestartAssessee`（重启被考核人）恢复。反馈结果时可顺带提示用户。

## 执行步骤

**步骤 1 — 定位方案（仅进行中）**

```bash
xrxs-cli appraisal batchQueryPlanInfos --request-body '{"planType":1,"planStatus":1,"planName":"<方案名关键词>"}'
```

- 复用[场景二](sop-scene2.md)步骤 1/2 的定位与候选确认逻辑（最多重试 1 次，搜不到/多个候选 → 列候选让用户选择，不自行猜测）。

**步骤 2 — 定位被考核人（新范式，单方案 + keyword 一次定位）**

```bash
xrxs-cli appraisal queryAssesseeInfos --fields "planId,planName,planType,assessBizId,employeeId,employeeName,jobNumber,department,flowName,inspectionStatus,assesseeStatus" --request-body '{"searchMode":"PLAN_SUBJECTS","planId":"<planId>","stage":{"mode":"ALL"},"keyword":"<员工姓名/工号>","pageNum":1,"pageSize":100}'
```

- **必须带 `--fields` 压缩**：`queryAssesseeInfos` 全字段返回极大（实测 37 人 ≈ 110KB），不带 `--fields` 会触发工具层 50KB 截断，模型会把截断误判为「接口服务内部错误」。
- **新范式核心：`searchMode:"PLAN_SUBJECTS"` + `planId` + `stage.mode:"ALL"`（全部）**，可加 `keyword` 精确定位（完整规则见 [`query-assessee-infos-guide.md`](../query-assessee-infos-guide.md)）。
- 一次请求即可定位（实测命中返回 1 行 ≈ 140 字节），**无需** `getPlanFlowList` 逐环节查询，避免漏查环节。
- `keyword` 查不到时：先不带 `keyword`、保留 `--fields` 再拉一次全名单（37 人 ≈ 9KB），本地按姓名匹配；仍查不到 → 走异常分支，不猜。
- 确认该员工确实在方案名单中，记录其 `employeeId`、`flowName`（所在环节）、`assesseeStatus`；同一次终止多人时合并 `employeeId` 列表。
- 兜底（新范式仍报参数校验错误时）：自查是否误传旧参数，修正后重试 1 次；仍失败则如实反馈，不强行执行。

**步骤 4 — 收集终止理由**

- 追问用户终止理由（`stopReason` 必填），不自行编造。

**步骤 5 — 预览确认**

**权限检查（permission check）**：调用正式命令 `batchTerminateAssessee` 前，先执行权限检查判断用户是否已授权永久允许执行该命令：

```bash
xrxs-cli permission check appraisal-batchTerminateAssessee
```

- 若返回 `true`，说明用户已授权，可直接调用 `batchTerminateAssessee`。
- 若返回 `false`（或命令不可用），必须先调用 `terminateAssesseePreview` 展示操作摘要，等用户确认后再调用 `batchTerminateAssessee`。

```bash
xrxs-cli appraisal terminateAssesseePreview --request-body '{"planId":"<planId>","stopReason":"<终止理由>","assesseeEmpIds":["<employeeId>"]}'
```

- 预览返回的 `<confirm-card>` 确认卡片（含 `taskId`）必须渲染给用户，**等用户明确确认后**才进入下一步；未确认不得提交。

**步骤 6 — 执行终止**

```bash
xrxs-cli appraisal batchTerminateAssessee --request-body '{"planId":"<planId>","stopReason":"<终止理由>","assesseeEmpIds":["<employeeId>"]}'
```

- `assesseeEmpIds` 为被考核人 ID 列表，不超过 100 个；一次终止多人时全部放入列表。
- 命令返回成功后再继续；若报错，如实反馈报错信息，不掩盖。

**步骤 7 — 复查验证**

- 用步骤 2 的同一命令（`searchMode:"PLAN_SUBJECTS"` + `planId` + `stage.mode:"ALL"` + `keyword` + `--fields`）**再查一次**，确认该员工已不在方案名单中（查不到 = 终止成功）。
- **复查一次即可，不轮询**：若仍在名单或命令报错，如实反馈失败原因，不编造成功。

**步骤 8 — 反馈**

- 向用户报成功，说明：员工、方案、终止时所在环节、终止理由。
- 反馈时只提示**系统已支持**的后续操作：如需恢复该员工的考核，可执行「重启被考核人」（`batchRestartAssessee`）。

## 异常分支

| 异常情况 | 处理方式 |
|----------|----------|
| 方案搜不到（进行中） | 最多重试 1 次，仍搜不到列出候选让用户确认；无进行中方案则如实告知（终止被考核人仅对进行中方案有效） |
| 员工不在方案名单 | 如实告知：该员工可能不在该方案或已终止；不猜、不强行执行 |
| 终止理由缺失 | 追问用户补充，不自行编造理由 |
| batchTerminateAssessee 执行报错 | 如实反馈报错信息（如员工已终止、方案状态不允许、无权限等），不掩盖 |
| 复查仍在名单 | 反馈终止未生效，请用户确认方案/员工状态后重试；**不自行轮询等待** |

## 输出模板

```markdown
## 终止被考核人 — <方案名称>（<方案ID>）

✅ 已终止：<员工姓名>（工号）在 <方案名称> 的考核已终止（原处于<环节名>环节），共 N 人。
**终止理由**：<stopReason>

> 如需恢复该员工的考核，可执行「重启被考核人」操作（batchRestartAssessee）。
```
