# 场景二：推荐简历给用人部门

> **阅读提示：** 本文档为 [`../sop-summary.md`](../sop-summary.md) 场景二的详细步骤，通用约定见 [`common.md`](common.md)。命中本场景后严格按下列步骤执行，不得跳过、不得自行发明等价命令序列。

## 适用场景与触发话术

- 用户话术示例（含同义表达）：
  - 「把张三的简历推荐给李经理」
  - 「推荐这份简历给用人部门」
  - 「把候选人推荐给面试官」
  - 「将这份简历转发给招聘负责人」
- 关键词：推荐简历、推荐给人、推荐给用人部门、推荐给面试官、转发简历、把 xx 推荐给 xx。

> **原则：** 凡是用户希望「把某份简历推荐给某个人/部门」的需求，**统一走本场景**；本场景为写入操作，正式调用前必须向用户确认意图。

## 前置信息

| 信息 | 必填 | 说明 |
|------|------|------|
| 目标简历 | 是 | 可直接提供 32 位 UUID 简历 ID，或提供姓名/手机号由 `getResumeList` 定位 |
| 接收人 | 是 | 可直接提供 32 位 UUID 员工 ID，或提供姓名/手机号由 `searchEmployee` 定位；支持多个接收人 |

## 执行步骤

### 步骤 1 — 识别目标简历与接收人

先判断用户提供的是 32 位 UUID 还是自然标识（姓名/手机号等）。

**若提供的是 UUID（32 位字符串）：**

- 直接作为 `resumeId` / `employeeId` 使用。
- 用户明确说「简历 ID 是 xxx」「员工 ID 是 xxx」时，也可直接作为对应 ID。

**若提供的是自然标识：**

并行调用以下两个接口定位：

```bash
xrxs-cli recruitment getResumeList --request-body json
```

```bash
xrxs-cli recruitment searchEmployee --request-body json
```

- `getResumeList` 请求体示例：

```json
{
  "source": 0,
  "keyword": "张三",
  "pageNum": 1,
  "pageSize": 20
}
```

- `searchEmployee` 请求体示例：

```json
{
  "keyword": "李经理",
  "pageNo": 1,
  "pageSize": 20,
  "status": 0
}
```

- 若任一接口返回多条匹配记录，列出候选供用户确认，**禁止批量猜测**。
- 定位完成后，提取真实的 `resumeId` 与 `employeeId`。

### 步骤 2 — 操作前预判

```bash
xrxs-cli recruitment getResumeDetailOperations --resume-id <resume-id>
```

- 检查返回的 `operations` 列表中是否存在推荐操作（`operationCode=1`，以实际返回为准）。
- 确认该操作的 `available=true`。
- 若推荐不可用，向用户说明 `disabledReason`，停止推荐流程。

### 步骤 3 — 确认推荐意图

正式调用写入接口前，必须向用户确认以下信息：

1. 要推荐的简历 ID 列表及对应候选人。
2. 接收人员工 ID（支持多个，逗号分隔）。
3. 有效期、敏感字段/附件/留言/投递分析权限等（如用户有明确要求）。

### 步骤 4 — 权限预检

```bash
xrxs-cli permission check recruitment-recommendResume
```

- 若返回 `true`，说明用户已授权，可直接执行步骤 6。
- 若返回 `false`，说明用户未授权，可选择：
  - 执行 `xrxs-cli permission save recruitment-recommendResume` 保存永久授权，之后直接执行步骤 6。
  - 先执行步骤 5 预览，用户确认后再执行步骤 6。

### 步骤 5 — 推荐预览（未授权且未保存授权时）

```bash
xrxs-cli recruitment recommendResumePreview --request-body json
```

请求体示例：

```json
{
  "resumeIds": "RESUME_123456",
  "employeeIds": "EMP_123456"
}
```

- 向用户展示预览返回的摘要与明细。
- 等待用户明确确认后，再执行步骤 6。

### 步骤 6 — 正式推荐

```bash
xrxs-cli recruitment recommendResume --request-body json
```

请求体示例：

```json
{
  "resumeIds": "RESUME_111,RESUME_222",
  "employeeIds": "EMP_111,EMP_222",
  "resumeType": 0,
  "validityDay": 7,
  "viewSensitive": 1,
  "attachments": 1,
  "comments": 1,
  "deliveryAnalysis": 1,
  "remark": ""
}
```

- `resumeIds`：简历 ID，多个用逗号分隔。
- `employeeIds`：接收人员工 ID，多个用逗号分隔。
- 其他字段按用户需求填充，无明确要求时使用接口默认值。

## 异常分支

| 异常情况 | 处理方式 |
|----------|----------|
| 自然标识定位到多条记录 | 列出候选供用户确认，禁止批量猜测 |
| `getResumeDetailOperations` 显示推荐不可用 | 向用户说明 `disabledReason`，停止推荐 |
| 用户未确认推荐意图 | 不调用 `recommendResume` |
| 命令执行报错 | 可执行一次 `xrxs-cli schema recruitment.recommendResume` 排错 |
| 用户希望改为只展示匹配清单 | 回退到场景一（人岗推荐） |
