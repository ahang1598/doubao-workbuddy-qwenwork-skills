# 场景三：催办有待办的员工并发放已确认的考核结果

> **阅读提示：** 本文档为场景三的详细步骤，通用约定见 [`common.md`](common.md)。命中本场景后严格按下列步骤执行，不得跳过、不得自行发明等价命令序列。

## 适用场景与触发话术

- 用户话术示例（含同义表达）：
  - 「帮我催办未提交自评的员工，并发放已确认的考核结果」
  - 「XX方案还有谁没自评？催一下；确认完的把结果发了」
  - 「催办未自评的人，然后发放已确认的结果」
  - 「对XX（员工姓名）进行催办」「催办XX的考核」（指定员工）
- 关键词：催办、提醒、自评、待办、未提交、未确认、发放、公开结果、已确认。

> **催办口径（重要）：** 催办的对象是**当前环节有待办**的被考核人/审批人——未提交自评只是待办的一种（还有未确认结果等环节待办）。判断依据以 `queryAssesseeInfos` 返回的 `existTodoEmp`/`flowTodoStatus`/`todoAddTime` 字段为准，**不限定为「未提交自评」**；只要有待办即可催办。

> **执行关系：** 两个动作都做，**先催办、后发放**，各自独立确认，互不阻塞。本场景包含两个写入子流程（A 催办 / B 发放），分别按下方步骤执行。

## 前置信息

| 信息 | 必填 | 说明 |
|------|------|------|
| 方案名称（或方案 ID） | 是 | 用于定位方案（必须为**进行中**） |

> **安全规则提醒（与 SKILL.md 一致）：** 催办与发放均为影响员工的写入操作，执行前必须向用户展示名单/范围并取得明确确认。

## 子流程 A — 催办（两条独立业务路线，按用户入口选择，非同一流程的二选一）

> **路线判定（第一步先定路线，不是中途分流）：**
> - 用户**点名员工**（「对XX催办」「催办张三、李四」）→ **路线一：催办指定员工**，从员工维度进入。
> - 用户**点名方案/部门**（「催办XX方案」「催办XX部门的考核待办」）→ **路线二：催办某方案/部门**，从方案维度进入。
> - 两条路线查询方向相反（员工→反查方案；方案→查名单）、前置信息不同（要员工 id vs 要方案 id）、确认内容不同（员工+方案列表 vs 方案内待办名单），**不可互相替换**。

---

### 路线一 — 催办指定员工（入口：员工姓名/工号）

**步骤 A1-0 — 获取员工 id**

用户点名催办某员工（只给了姓名/工号，未给 id）时，先拿到员工 id：

- 若对话上下文/前端已注入该员工的 `employeeId`（如用户消息携带员工卡片），直接使用，跳过本步。
- 否则用员工搜索接口按姓名查 id（appraisal-agent 可直接调用 employee 模块）：

```bash
xrxs-cli employee searchEmployee --request-body '{"status":0,"pageNo":1,"pageSize":20,"keyword":"<员工姓名>"}'
```

- `keyword` 填员工姓名（模糊匹配）；`status:0` 表示在职（催办对象一般为在职员工）。
- 从返回记录中取 `employeeId`（员工ID），并用 `employeeName`/`jobNumber`（工号）核对是否目标员工；返回字段名以 `xrxs-cli schema employee.searchEmployee` 为准。
- **同名多人** → 列出候选（姓名 + 工号 + 部门）让用户确认，禁止凭猜测选人。
- **查不到** → 如实反馈，请用户提供工号/更多信息后重试，禁止编造 id 或随意放宽 status。
- ⚠️ 实测：`searchEmployee` 的 `keyword` 参数当前网关返回 404（2026-08-11 复现，见测试指南），若失败可改用「路线二 + keyword 定位」（在目标方案内用 `queryAssesseeInfos` 带 keyword 定位员工），或请用户提供工号/员工卡片。

**步骤 A1-1 — 反查该员工参与的全部进行中方案**

```bash
xrxs-cli appraisal queryAssesseePlanInfos --employee-id '<员工id>' --plan-status 1
```

- `--plan-status` 可空（为空时返回该员工全部状态的方案）；催办只针对**进行中**方案，固定传 `1`。
- 一次返回该员工参与的全部进行中方案及被考核对象基础信息，`planIds` 直接取自返回的方案集合（`planId` + `planName`），**无需再 `batchQueryPlanInfos` 搜方案**。
- 反查为空 → 如实反馈该员工当前无进行中考核方案（异常分支）。

**步骤 A1-2 — 确认催办范围**

- 展示「员工 + 反查到的进行中方案列表」，确认催办全部方案还是指定方案（范围由 `employeeIds` + `planIds` 表达）。
- 可询问是否限定环节（如只催「员工自评」）；限定时用 `getPlanFlowList` 取环节定义（命令见路线二步骤 A2-1 附注）。
- 用户确认后进入共用「执行催办」。

---

### 路线二 — 催办某方案/部门全员（入口：方案名/部门名）

**步骤 A2-0 — 定位方案（仅进行中）**

```bash
xrxs-cli appraisal batchQueryPlanInfos --request-body '{"planType":1,"planStatus":1,"planName":"<方案名关键词>"}'
```

- 复用[场景二](sop-scene2.md)步骤 1/2 的定位与候选确认逻辑（最多重试 1 次，搜不到/多个 → 列候选让用户选）。
- **支持多方案**：用户提到多个方案（或「所有进行中方案」）时，一次定位后可催办多个，`planIds` 收集全部方案 ID。

**步骤 A2-1 — 确定催办范围与环节（决策点）**

按用户意图确认催办范围与是否限定环节：

| 用户意图 | 范围载体 | 后续步骤 |
|----------|----------|----------|
| 催办某方案内指定员工 | `employeeIds` | 走 A2-2 拉名单确认 |
| 催办某部门/多部门全部员工 | `departmentIds` | 跳过 A2-2，直接 A2-3 |
| 只催办「员工自评」等指定环节 | `planFlow`（环节名+环节类型值） | 需先 `getPlanFlowList` 拿环节定义（见下） |
| 不指定环节（催办范围内全部当前待办） | `planFlow` 留空 | 无需查环节，直接 A2-2/A2-3 |

- 需要限定环节时，用 `getPlanFlowList` 取环节定义：

```bash
xrxs-cli appraisal getPlanFlowList --request-body '{"planId":"<planId>","planType":1}'
```

- 从流程环节列表中找出目标环节对应的 `flowName` 与环节类型值（`inspectionStatus`），**以返回的环节定义为准，不猜环节名**。

**步骤 A2-2 — （仅精确到员工时）查询该方案有待办的员工名单**

- 按部门催办时**跳过本步**（范围由 `departmentIds` 表达，无需逐人拉名单）。
- 需限定环节催办时，先用 `getPlanFlowList`（见 A2-1）拿目标环节 `flowId`。

```bash
xrxs-cli appraisal queryAssesseeInfos --fields "planId,planName,planType,assessBizId,employeeId,employeeName,jobNumber,department,flowName,inspectionStatus,todoAddTime,existTodoEmp,communicationStatus,assesseeStatus,flowTodoTitle,flowTodoStatus" --request-body '{"searchMode":"PLAN_SUBJECTS","planId":"<planId>","stage":{"mode":"ALL"},"pageNum":1,"pageSize":100}'
```

- **必须带 `--fields` 压缩**：`queryAssesseeInfos` 全字段返回极大（实测 37 人 ≈ 110KB），不带 `--fields` 会触发工具层 50KB 截断，模型会把截断误判为「接口服务内部错误」。
- **新范式核心：`searchMode:"PLAN_SUBJECTS"` + `planId` + `stage.mode:"ALL"`**（完整规则见 [`query-assessee-infos-guide.md`](../query-assessee-infos-guide.md)）。
- 分页拉全（遵守「分页停止条件」），筛选有待办人员：以 `existTodoEmp`/`flowTodoStatus`/`todoAddTime` 判断「当前环节是否有待办」，**不限定「未提交自评」**（未确认结果等环节待办同样可催）；`--jq` 取员工姓名、部门、环节。
- 同一请求体只拉一次；必要时用 `--jq` 本地筛选（`--fields` 模式下为平铺列表，`--jq` 不带 `.data` 前缀），不重复请求。

**步骤 A2-3 — 展示名单并确认**

- 精确到员工：展示有待办名单（姓名 + 部门 + 环节 + 待办事项，如「未提交自评」「未确认结果」），询问是否全部催办或指定催办哪些人。
- 按部门：展示部门范围（部门名 + 覆盖人数），并说明「催办范围内全部当前待办」或限定环节，请用户确认。
- 用户确认后进入共用「执行催办」。

---

### 共用 — 执行催办（两条路线均收敛于此）

**权限检查（permission check）**：调用正式催办命令 `batchUrgeRemind` 前，先执行权限检查判断用户是否已授权永久允许执行该命令：

```bash
xrxs-cli permission check appraisal-batchUrgeRemind
```

- 若返回 `true`，说明用户已授权，可直接调用 `batchUrgeRemind`。
- 若返回 `false`，说明用户未授权，必须先调用 `batchUrgeRemindPreview` 展示操作摘要，等用户确认后再调用 `batchUrgeRemind`。
- **预览与执行一致性**：`batchUrgeRemindPreview` 与 `batchUrgeRemind` 使用同一批 `planIds`（预览确认什么范围，执行就是什么范围）。

按路线确定的范围形态选择请求体（`planIds` + `planType` 必填；`employeeIds` 与 `departmentIds` **至少选一项**；`planFlow` 可空）：

```bash
# 形态 1：路线一（精确员工）+ 指定环节
xrxs-cli appraisal batchUrgeRemind --request-body '{"planIds":["<planId>"],"planType":1,"planFlow":[{"flowName":"<环节名>","inspectionStatus":<环节类型值>}],"employeeIds":["<员工id1>","<员工id2>"]}'

# 形态 2：按部门催办（可带 planFlow 限定环节，不带则催该部门全部当前待办）
xrxs-cli appraisal batchUrgeRemind --request-body '{"planIds":["<planId>"],"planType":1,"planFlow":[{"flowName":"<环节名>","inspectionStatus":<环节类型值>}],"departmentIds":["<部门id1>","<部门id2>"]}'

# 形态 3：多方案 + 按部门 + 催全部待办（planFlow 留空）
xrxs-cli appraisal batchUrgeRemind --request-body '{"planIds":["<planId1>","<planId2>"],"planType":1,"departmentIds":["<部门id1>"]}'
```

- **请求体字段（后端批量方案）**：`planIds`（方案ID列表，必填，**限制：需要催办多个方案时，必须一次传入全部方案ID（数组），不得按方案拆分多次预览/执行；若方案分属不同 `planType`，则按 `planType` 分组分别预览**）、`planType`（方案类型，必填，1-绩效考核，2-试用期考核，3-组织绩效）、`planFlow`（催办环节列表 `[{"flowName":"环节名","inspectionStatus":环节类型值}]`，可空，为空时催办所选范围内全部当前待办）、`employeeIds`（人员ID列表）与 `departmentIds`（部门ID列表）**至少选一项**。
- 用户确认后执行；完成后向用户反馈催办结果（催办对象数量、是否成功），不返回命令本身。

## 子流程 B — 发放已确认的考核结果

**步骤 B1 — 查询已确认结果的被考核人名单**

```bash
xrxs-cli appraisal queryAssesseeInfos --fields "planId,planName,planType,assessBizId,employeeId,employeeName,jobNumber,department,flowName,inspectionStatus,resultConfirmSignStatus,assesseeStatus" --request-body '{"searchMode":"PLAN_SUBJECTS","planId":"<planId>","stage":{"mode":"COMPLETED"},"pageNum":1,"pageSize":100}'
```

- **必须带 `--fields` 压缩**：`queryAssesseeInfos` 全字段返回极大（实测 37 人 ≈ 110KB），不带 `--fields` 会触发工具层 50KB 截断，模型会把截断误判为「接口服务内部错误」。
- **新范式核心：`searchMode:"PLAN_SUBJECTS"` + `planId` + `stage.mode:"COMPLETED"`（已完成未终止）**（完整规则见 [`query-assessee-infos-guide.md`](../query-assessee-infos-guide.md)）。

- 分页拉全（遵守「分页停止条件」），提取「已确认」状态的被考核人（姓名 + 部门）。
- 环节类型值以 `getPlanFlowList` 返回定义为准，不猜。

**步骤 B2 — 展示名单并确认发放范围**

- 展示已确认名单（姓名 + 部门）及人数，让用户确认发放范围（全部发放或指定人员）。

**步骤 B3 — 预览确认**

**权限检查（permission check）**：调用正式命令 `distributeResultAssessee` 前，先执行权限检查判断用户是否已授权永久允许执行该命令：

```bash
xrxs-cli permission check appraisal-distributeResultAssessee
```

- 若返回 `true`，说明用户已授权，可直接调用 `distributeResultAssessee`。
- 若返回 `false`（或命令不可用），必须先调用 `distributeResultAssesseePreview` 展示操作摘要（对 B2 确认名单中的对象调用，展示后作为整批发放的操作确认），等用户确认后再执行发放。

```bash
xrxs-cli appraisal distributeResultAssesseePreview --request-body '{"planId":"<planId>","assesseeEmpId":"<员工id>"}'
```

- 预览返回的 `<confirm-card>` 确认卡片（含 `taskId`）必须渲染给用户，**等用户明确确认后**才进入下一步；未确认不得提交。

**步骤 B4 — 逐个发放**

```bash
xrxs-cli appraisal distributeResultAssessee --request-body '{"planId":"<planId>","assesseeEmpId":"<员工id>"}'
```

- 对 B2 确认名单中的每个被考核人执行一次（每次请求体不同，属合法循环；名单确认后只发放一次，不重复发放）。
- **以 B2 的名单确认为意图确认**（未授权时叠加 B3 的预览确认）。

**步骤 B5 — 统计并反馈**

- 发放完成后汇总：成功 N 人 / 失败 M 人；失败的如实反馈（如该人结果状态不允许发放），不掩盖、不编造成功。

## 异常分支

| 异常情况 | 处理方式 |
|----------|----------|
| 方案搜不到（进行中） | 最多重试 1 次，仍搜不到列出候选让用户确认；无进行中方案则如实告知 |
| 员工查不到（searchEmployee 空结果或同名多人） | 如实反馈并列出候选（同名时）让用户确认，或请用户提供工号；禁止编造 id |
| 员工反查不到进行中方案（queryAssesseePlanInfos 空结果） | 如实反馈该员工当前无进行中考核方案，请用户确认是否放宽状态或换人 |
| 找不到「员工自评」环节 | 如实反馈 `getPlanFlowList` 返回的环节列表，请用户确认对应环节，不猜环节 |
| `employeeIds` 与 `departmentIds` 都未提供 | 后端参数校验失败（schema 要求至少选一项）；按 A2 决策回补范围载体后再请求 |
| 有待办名单为空 | 如实报告「该范围内无有待办的员工」，跳过子流程 A |
| 已确认名单为空 | 如实报告「无已确认结果的被考核人可发放」，跳过子流程 B |
| 执行报错 | 如实反馈报错信息（如方案状态、权限等），不掩盖 |
| 部分发放失败 | 汇总反馈成功/失败明细，失败的单独列出，不掩盖 |

## 输出模板

```markdown
## 催办与发放结果 — <方案名称>（<方案ID>）

### 一、催办有待办的员工
- 催办范围：<精确 N 人 / 部门 XX 全员 / 多方案>
- 有待办：N 人（已催办）
  - 张三（XX部）、李四（XX部）、…
- 催办结果：✅ 成功（N 人）

### 二、发放已确认的考核结果
- 已确认结果：N 人（已发放）
  - 王五（XX部）、赵六（XX部）、…
- 发放结果：✅ 成功 N 人；❌ 失败 M 人（失败明细：…）
```
