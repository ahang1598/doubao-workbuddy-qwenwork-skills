# 场景三：安排面试

> **阅读提示：** 本文档为 [`../sop-summary.md`](../sop-summary.md) 场景三的详细步骤，通用约定见 [`common.md`](common.md)。命中本场景后严格按下列步骤执行，不得跳过、不得自行发明等价命令序列。

## 适用场景与触发话术

- 用户话术示例（含同义表达）：
  - 「给张三安排面试」
  - 「帮李四约一面」
  - 「修改王五的面试时间」
  - 「把赵六的面试改到下周」
  - 「换个面试官」
- 关键词：安排面试、约面试、安排一面、预约面试、修改面试、调整面试时间、改面试、换面试官。

> **原则：** 凡是用户希望「为候选人安排/修改面试」的需求，**统一走本场景**；本场景为写入操作，正式调用前必须向用户确认意图。

## 前置信息

| 信息 | 必填     | 说明                                                                                     |
|------|----------|------------------------------------------------------------------------------------------|
| 目标简历 | 是       | 可直接提供 32 位 UUID 简历 ID，或提供姓名/手机号由 `getResumeList` 定位                  |
| 面试官 | 是       | 可直接提供 32 位 UUID 员工 ID，或提供姓名/手机号由 `searchEmployee` 定位；支持多个面试官 |
| 面试时间 | 是       | 格式 `yyyy-MM-dd HH:mm`，用户未给出时必须追问                                            |
| 面试时长 | 否       | 单位分钟,用户未给出时默认30分钟                                                          |
| 面试轮次 | 是       | 通过 `getOpenRoundsSetting` 选择，用户未给出时必须追问                                   |
| 评价表 | 是       | 通过 `getInterviewFeedbackTemplateList` 选择，用户未给出时必须追问                       |
| 面试形式/地址 | 是       | 现场/电话/视频等；线下面试需选择地址                                                     |
| 应聘职位 | 条件必填 | 用户说明安排到某职位时通过 `getResumeApplyJob` 获取                                      |
| 通知方式 | 条件必填 | 用户说明短信/邮件通知候选人时，调用相关开关与模板接口                                    |

## 执行步骤

### 步骤 1 — 识别目标简历与面试官

先判断用户提供的是 32 位 UUID 还是自然标识（姓名/手机号等）。

**若提供的是 UUID（32 位字符串）：**

- 直接作为 `resumeId` / `interviewerEmployeeId` 使用。
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
- 定位完成后，提取真实的 `resumeId` 与面试官 `employeeId`。

### 步骤 2 — 操作前预判

```bash
xrxs-cli recruitment getResumeDetailOperations --resume-id <resume-id>
```

- 检查返回的 `operations` 列表：
  - 安排面试检查是否存在安排面试操作（`operationCode=11`，以实际返回为准）且 `available=true`。
  - 修改面试检查是否存在修改面试操作且 `available=true`。
- 若对应操作不可用，向用户说明 `disabledReason`，停止流程。

### 步骤 3 — 判断操作类型

根据用户话术判断：

- 用户说「安排」「约」「预约」「新增」等 → **安排面试**（`addInterview`）。
- 用户说「修改」「调整」「改」「换」等 → **修改面试**（`updateInterview`）。
- 以用户明确意图为准；若无法判断，向用户确认是新增还是修改。

### 步骤 4 — 修改时查询现有面试（updateInterview 时）

```bash
xrxs-cli recruitment getResumeInterviewList --resume-id <resume-id>
```

- 获取该简历的面试轮次列表。
- 提取需要修改的 `interviewId` 与轮次 `uuid`。
- 返回为空时，告知用户该候选人暂无面试记录，无法修改。

### 步骤 5 — 查询面试配置

并行调用以下接口获取面试所需配置：

```bash
xrxs-cli recruitment getOpenRoundsSetting
```

```bash
xrxs-cli recruitment getInterviewFeedbackTemplateList
```

```bash
xrxs-cli recruitment getInterviewAddressList --keyword 总部
```

- `getOpenRoundsSetting`：获取可用面试轮次，`interviewRoundsSettingId` 填入 `roundsSettingId`。
- `getInterviewFeedbackTemplateList`：获取评价表，`templateId` 填入 `judgementTemplateId`。
- `getInterviewAddressList`：获取面试地址，`interviewAddressId` 用于线下面试。

### 步骤 6 — 条件查询

**若用户说明将候选人安排到某个职位：**

```bash
xrxs-cli recruitment getResumeApplyJob --resume-id <resume-id>
```

- 返回 `jobId` 作为 `interviewJob`。

**若用户说明要给候选人发短信/邮件通知：**

```bash
xrxs-cli recruitment getCandidateNotifySwitch
```

```bash
xrxs-cli recruitment getEmailTemplateList --type 1
```

```bash
xrxs-cli recruitment getEmailSenderList
```

- `getCandidateNotifySwitch`：获取默认短信/邮件通知开关，作为 `smsInterviewee`/`emailInterviewee` 默认值参考。
- `getEmailTemplateList`：获取邮件模板，`templateId` 填入 `emailTemplateId`。
- `getEmailSenderList`：获取发件箱，`id` 填入 `emailId`。

### 步骤 7 — 面试官日程弱提示

```bash
xrxs-cli recruitment getInterviewerScheduleCalendar --request-body json
```

请求体示例：

```json
{
  "startDate": "2026-08-15",
  "endDate": "2026-08-17",
  "interviewers": [
    {
      "interviewerId": "EMP_123456",
      "companyId": "",
      "interviewDate": "2026-08-16"
    }
  ],
  "interviewTime": "2026-08-16 14:00",
  "duration": 60
}
```

- 用户已给面试时间：查询当天及前后各 1 天。
- 用户未给面试时间：查询未来 7 天。
- **仅做参考提示**，向用户展示面试官已有日程，不做强制冲突拦截。
- 若用户根据日程重新选择时间，返回步骤 8 重新确认。

### 步骤 8 — 收集必填信息

以下信息为用户未提供时必须追问的必填项：

- 面试时间（`yyyy-MM-dd HH:mm`）
- 面试时长（分钟）
- 面试官（至少一个）
- 面试轮次（`roundsSettingId`）
- 评价表（`judgementTemplateId`）
- 面试形式（现场/电话/视频等）
- 线下面试地址（`interviewAddressId`）
- 应聘职位（`interviewJob`，用户说明安排到某职位时）
- 通知方式及相关字段（用户说明通知时）

**不自动填充默认值**，必须由用户明确确认。

### 步骤 9 — 权限预检

- 安排面试：

```bash
xrxs-cli permission check recruitment-addInterview
```

- 修改面试：

```bash
xrxs-cli permission check recruitment-updateInterview
```

- 返回 `true` → 直接执行步骤 11。
- 返回 `false` → 可选择：
  - 执行 `xrxs-cli permission save recruitment-addInterview`（安排）或 `xrxs-cli permission save recruitment-updateInterview`（修改）保存永久授权，之后直接执行步骤 11。
  - 先执行步骤 10 预览，用户确认后再执行步骤 11。

### 步骤 10 — 预览（未授权且未保存授权时）

- 安排面试：

```bash
xrxs-cli recruitment addInterviewPreview --request-body json
```

- 修改面试：

```bash
xrxs-cli recruitment updateInterviewPreview --request-body json
```

- 向用户展示预览返回的摘要与明细。
- 等待用户明确确认后，再执行步骤 11。

### 步骤 11 — 正式调用

- 安排面试：

```bash
xrxs-cli recruitment addInterview --request-body json
```

- 修改面试：

```bash
xrxs-cli recruitment updateInterview --request-body json
```

请求体示例（安排面试）：

```json
{
  "resumeId": "RESUME_123456",
  "interviewJob": "JOB_123456",
  "form": 0,
  "interviewRounds": [
    {
      "interviewDateTime": "2026-08-16 14:00",
      "duration": 60,
      "interviewerEmployeeIds": ["EMP_111", "EMP_222"],
      "roundsSettingId": "ROUND_123",
      "judgementTemplateId": "TEMPLATE_123",
      "form": 0
    }
  ],
  "interviewAddressId": "ADDR_123",
  "smsInterviewee": 0,
  "emailInterviewee": 0
}
```

修改面试请求体与上基本一致，额外需要：

```json
{
  "interviewId": "INTERVIEW_123",
  "interviewRounds": [
    {
      "uuid": "ROUND_UUID_123",
      "interviewDateTime": "2026-08-16 14:00",
      "duration": 60,
      "interviewerEmployeeIds": ["EMP_111", "EMP_222"],
      "roundsSettingId": "ROUND_123",
      "judgementTemplateId": "TEMPLATE_123"
    }
  ]
}
```

- 正式调用前，再次向用户确认面试时间、面试官、候选人、职位、通知方式等关键信息。

## 异常分支

| 异常情况 | 处理方式 |
|----------|----------|
| 自然标识定位到多条记录 | 列出候选供用户确认，禁止批量猜测 |
| `getResumeDetailOperations` 显示操作不可用 | 向用户说明 `disabledReason`，停止流程 |
| 用户未提供必填项 | 逐项追问，不自动填充 |
| 用户话术无法判断 add/update | 向用户确认是新增还是修改 |
| 修改时 `getResumeInterviewList` 返回为空 | 告知用户暂无面试记录，无法修改 |
| 命令执行报错 | 可执行一次 `xrxs-cli schema recruitment.addInterview` 或 `recruitment.updateInterview` 排错 |
