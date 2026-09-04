---
name: recruitment-interview
description: 招聘面试管理，包括安排面试、修改面试、撤销面试、面试配置查询、面试官日程冲突校验及面试提醒等。
---

# 招聘 - 面试管理

本场景覆盖招聘面试的安排、修改、撤销，以及面试所需的评价表、轮次设置、面试地址、面试官日程、邮件通知、候选人提醒等辅助查询能力。

### 查看接口完整信息

调用命令前，优先参考本文档中对该命令的入参、请求体格式及返回值的说明。如果文档已经描述得足够清晰、能够直接构造调用，则**不需要再执行** `xrxs-cli schema recruitment.<command>`。只有当文档中对某个命令的入参或返回值描述不明确、不足以完成调用时，才对该命令执行一次 `xrxs-cli schema recruitment.<command>` 进行确认。**仅对将要实际调用的命令做此检查**，同一命令最多检查一次；禁止为排查字段而批量轮询多个无关命令的 schema

例如：
```bash
xrxs-cli schema recruitment.addInterview
```

---

## getResumeInterviewList

- **接口名称**：`getResumeInterviewList`
- **描述**：获取候选人面试轮次列表（修改/撤销面试前查询，含可撤销标志）
- **CLI 命令示例**：
  ```bash
  xrxs-cli recruitment getResumeInterviewList --resume-id RESUME_123456
  ```
- **参数说明**：
  - `--resume-id`（string，可选）：简历 ID，引用 `getResumeList` / `getTalentResumeList` 结果中的 `data.data.resumeId`。

---

## getResumeApplyJob

- **接口名称**：`getResumeApplyJob`
- **描述**：获取简历应聘职位（安排面试 interviewJob 来源）
- **CLI 命令示例**：
  ```bash
  xrxs-cli recruitment getResumeApplyJob --resume-id RESUME_123456
  ```
- **参数说明**：
  - `--resume-id`（string，可选）：简历 ID，引用 `getResumeList` / `getTalentResumeList` 结果中的 `data.data.resumeId`。

**返回关键字段**：
- `jobId`（string）：应聘职位 ID，安排面试时填入 `interviewJob`。
- `jobName`（string）：应聘职位名称。

---

## getInterviewFeedbackTemplateList

- **接口名称**：`getInterviewFeedbackTemplateList`
- **描述**：获取面试评价表列表（用于选择评价表）
- **CLI 命令示例**：
  ```bash
  xrxs-cli recruitment getInterviewFeedbackTemplateList
  ```
- **参数说明**：无。

**返回关键字段**：
- `templateId`（string）：评价表模板 ID，安排面试时填入 `judgementTemplateId`。
- `name`（string）：评价表名称。
- `isDefault`（integer）：是否默认评价表，`1` 是，`0` 否。

---

## getOpenRoundsSetting

- **接口名称**：`getOpenRoundsSetting`
- **描述**：获取公司所有开启的面试轮次设置（用于选择轮次）
- **CLI 命令示例**：
  ```bash
  xrxs-cli recruitment getOpenRoundsSetting --custom-process-id 1001
  ```
- **参数说明**：
  - `--custom-process-id`（string，可选）：招聘流程 ID，按流程过滤。

**返回关键字段**：
- `interviewRoundsSettingId`（string）：轮次设置 ID，安排面试时填入 `roundsSettingId`。
- `roundsName`（string）：轮次名称。
- `status`（integer）：状态，`1` 开启，`0` 关闭。

---

## getInterviewAddressList

- **接口名称**：`getInterviewAddressList`
- **描述**：获取公司面试地址列表（用于选择线下面试地址）
- **CLI 命令示例**：
  ```bash
  xrxs-cli recruitment getInterviewAddressList --keyword 总部
  ```
- **参数说明**：
  - `--keyword`（string，可选）：搜索关键字，按地址名称模糊匹配。

**返回关键字段**：
- `interviewAddressId`（string）：面试地址 ID，安排面试时填入 `interviewAddressId`。
- `addressName`（string）：地址名称。
- `addressDetail`（string）：详细地址。
- `contactName`（string）：联系人姓名。
- `contactMobile`（string）：联系电话。

---

## getCandidateNotifySwitch

- **接口名称**：`getCandidateNotifySwitch`
- **描述**：获取候选人面试提醒默认开关（决定 smsInterviewee/emailInterviewee 默认值）
- **CLI 命令示例**：
  ```bash
  xrxs-cli recruitment getCandidateNotifySwitch
  ```
- **参数说明**：无。

**返回关键字段**：
- `smsInterviewee`（integer）：是否默认短信通知候选人，`1` 是，`0` 否。
- `emailInterviewee`（integer）：是否默认邮件通知候选人，`1` 是，`0` 否。

---

## getEmailSenderList

- **接口名称**：`getEmailSenderList`
- **描述**：获取发件箱列表（邮件通知时填入 emailId）
- **CLI 命令示例**：
  ```bash
  xrxs-cli recruitment getEmailSenderList
  ```
- **参数说明**：无。

**返回关键字段**：
- `id`（integer）：发件箱 ID，安排面试 `emailInterviewee=1` 时填入 `emailId`。
- `email`（string）：发件邮箱地址。
- `senderName`（string）：发件人名称。
- `status`（integer）：状态，`1` 启用，`0` 停用。

---

## getEmailTemplateList

- **接口名称**：`getEmailTemplateList`
- **描述**：获取邮件模板列表（邮件通知时填入 emailTemplateId）
- **CLI 命令示例**：
  ```bash
  xrxs-cli recruitment getEmailTemplateList --type 1
  ```
- **参数说明**：
  - `--type`（string，必填）：模板类型，见 Web 端邮件模板类型枚举。

**返回关键字段**：
- `templateId`（string）：邮件模板 ID，安排面试 `emailInterviewee=1` 时填入 `emailTemplateId`。
- `templateName`（string）：模板名称。

---

## getInterviewerScheduleCalendar

- **接口名称**：`getInterviewerScheduleCalendar`
- **描述**：获取面试官日程日历（查时间范围内面试官的面试/考勤/第三方日程，按天分组，仅展示不做冲突判断）
- **CLI 命令示例**：
  ```bash
  xrxs-cli recruitment getInterviewerScheduleCalendar --request-body json
  ```
- **参数说明**（JSON body）：
  - `startDate`（string，必填）：查询范围开始日期，格式 `yyyy-MM-dd`。
  - `endDate`（string，必填）：查询范围结束日期，格式 `yyyy-MM-dd`。
  - `interviewers`（object[]，必填）：面试官列表。
    - `interviewerId`（string）：面试官员工 ID。
    - `companyId`（string）：所属公司 ID。
    - `interviewDate`（string）：面试日期。
  - `interviewTime`（string，必填）：面试时间，格式 `yyyy-MM-dd HH:mm`（冲突校验必填，日程展示本身可不依赖）。
  - `duration`（integer，必填）：面试时长（分钟）（冲突校验必填，日程展示本身可不依赖）。
  - `roundsId`（string，可选）：轮次 ID，排除该轮次自身的面试。

**返回关键字段**：
- `startDate`（string）：查询范围开始日期 `yyyy-MM-dd`。
- `endDate`（string）：查询范围结束日期 `yyyy-MM-dd`。
- `days`（object[]）：按天分组的面试官日程，按日期升序。
  - `date`（string）：日期 `yyyy-MM-dd`。
  - `interviewers`（object[]）：当天各面试官日程，每个面试官一条，无日程则为空列表。
    - `interviewerId`（string）：面试官 ID。
    - `interviewerName`（string）：面试官姓名。
    - `schedules`（object[]）：当天日程列表，按开始时间升序。
      - `scheduleType`（integer）：日程类型，`1` 面试，`2` 请假，`3` 外出，`4` 外勤，`5` 出差，`6` 钉钉日程，`7` 飞书日程。
      - `scheduleStartTime`（integer）：日程开始时间（时间戳，单位秒）。
      - `scheduleEndTime`（integer）：日程结束时间（时间戳，单位秒）。
      - `scheduleTips`（string）：日程提示。
      - 面试日程特有字段：
        - `candidateName`（string）：候选人姓名。
        - `applyJob`（string）：应聘职位。
        - `roundName`（string）：面试轮次名。
        - `interviewWay`（integer）：面试方式，`0` 现场面试，`2` 电话面试，`5` 腾讯会议，`6` 钉钉视频，`7` 飞书视频，`8` 其他视频，`9` 企业微信。
        - `interviewWayDesc`（string）：面试方式文案，如 "现场面试"、"腾讯会议"。
        - `interviewStatus`（integer）：面试状态，`200` 邀约待确认，`201` 邀约已接受，`202` 邀约已拒绝，`211` 已签到，`220` 面试通过，`221` 面试未通过，`222` 面试待确认，`223` 未面试，`224` 面试结果待定，`225` 未评价，`226` 部分评价，`230` 面试已撤销。
        - `interviewStatusDesc`（string）：面试状态文案，如 "邀约待确认"、"面试通过"。
        - `interviewPlace`（string）：面试地点，现场面试为地址名，线上视频面试为会议链接，电话面试为空。
      - 考勤日程特有字段：
        - `attendanceStatus`（integer）：考勤状态，`5` 请假，`6` 外出，`10` 外勤，`16` 出差。
        - `attendanceStatusDesc`（string）：考勤状态文案，如 "请假"、"外出"。

---

## verifyInterviewerSchedule

- **接口名称**：`verifyInterviewerSchedule`
- **描述**：校验面试官日程冲突（面试时间是否与面试官既有面试/考勤/第三方日程冲突），不是强校验，在安排面试的时候，如果时间有冲突，提示用户面试官有时间冲突，并让客户确认是否继续安排，如果继续安排就直接安排了。

- **CLI 命令示例**：
  ```bash
  xrxs-cli recruitment verifyInterviewerSchedule --request-body json
  ```
- **参数说明**（JSON body）：与 `getInterviewerScheduleCalendar` 一致。

**返回关键字段**：
- `timeConflict`（integer）：时间是否冲突，`1` 有冲突，`0` 无冲突。
- `crossDays`（integer）：面试时间是否跨天，`1` 跨天，`0` 未跨天。
- `alert`（string）：警告信息，无冲突时为空。

---

## addInterviewPreview

- **接口名称**：`addInterviewPreview`
- **描述**：安排面试预览（不实际保存，返回汇总 + 明细供确认）
- **CLI 命令示例**：
  ```bash
  xrxs-cli recruitment addInterviewPreview --request-body json
  ```
- **参数说明**（JSON body）：与 `addInterview` 一致。

---

## addInterview

> ⚠️ **写入操作**：调用前必须向用户确认面试时间、面试官、候选人及通知方式，避免误操作。
> 
> 本操作存在预览接口 `addInterviewPreview`。调用正式接口前，先执行 `xrxs-cli permission check recruitment-addInterview` 判断用户是否已授权永久允许执行该命令：
> - 若返回 `true`，说明用户已授权，可直接调用 `addInterview`。
> - 若返回 `false`，说明用户未授权。此时有两种处理方式：
>   - 若用户希望永久授权，执行 `xrxs-cli permission save recruitment-addInterview` 保存授权，之后即可直接调用 `addInterview`。
>   - 若用户仅想单次确认，先调用 `addInterviewPreview` 展示操作摘要，等用户确认后再调用 `addInterview`。

- **接口名称**：`addInterview`
- **描述**：安排面试
- **CLI 命令示例**：
  ```bash
  xrxs-cli recruitment addInterview --request-body json
  ```
- **参数说明**（JSON body）：
  - `resumeId`（string，必填）：简历 ID，引用 `getResumeList` / `getTalentResumeList` 结果中的 `data.data.resumeId`。
  - `interviewJob`（string，必填）：应聘职位 ID，引用 `getMyJobList` 结果中的 `data.data.jobId`。
  - `form`（integer，可选）：面试形式，`0` 现场面试，`2` 电话面试，`5` 腾讯会议，`6` 钉钉视频，`7` 飞书视频，`8` 其他视频，`9` 企业微信；不传默认 `0`。
  - `interviewRounds`（object[]，必填）：面试轮次列表，至少一个轮次。
    - `interviewDateTime`（string，必填）：面试时间，格式 `yyyy-MM-dd HH:mm`。
    - `duration`（integer，必填）：面试时长（分钟）。
    - `interviewerEmployeeIds`（string[]，必填）：面试官员工 ID 列表，至少一个，引用员工模块搜索接口结果中的员工 ID。
    - `roundsSettingId`（string，必填）：轮次设置 ID，引用 `getOpenRoundsSetting` 结果中的 `interviewRoundsSettingId`。
    - `judgementTemplateId`（string，必填）：评价表模板 ID，引用 `getInterviewFeedbackTemplateList` 结果中的 `data.templateId`。
    - `form`（integer，可选）：面试形式，同顶层 `form`。
    - `meetingLink`（string，可选）：会议链接。
    - `platformName`（string，可选）：平台名称。
    - `meetingNumber`（string，可选）：会议号。
    - `meetingPassword`（string，可选）：入会密码。
  - `interviewAddressId`（string，可选）：面试地址 ID，线下面试时填写，引用 `getInterviewAddressList` 结果中的 `interviewAddressId`。
  - `interviewerViewSetting`（object，可选）：面试官查看内容设置。
    - `originResume`（integer）：原始简历。
    - `standardResume`（integer）：标准简历。
    - `deliveryAnalysis`（integer）：投递分析。
    - `evaluation`（integer）：测评。
    - `registerInfo`（integer）：面试登记表。
    - `attachments`（integer）：附件。
    - `comments`（integer）：留言及推荐反馈。
    - `viewSensitive`（integer）：敏感字段。
  - `remark`（string，可选）：备注。
  - `smsInterviewee`（integer，可选）：是否给候选人发送短信，`0` 否，`1` 是，默认 `0`。
  - `smsMobile`（string，`smsInterviewee=1` 时填写）：短信联系方式。
  - `smsName`（string，`smsInterviewee=1` 时填写）：短信联系人姓名。
  - `smsSite`（string，`smsInterviewee=1` 时填写）：面试地点。
  - `emailInterviewee`（integer，可选）：是否给候选人发送邮件，`0` 否，`1` 是，默认 `0`。
  - `emailId`（integer，`emailInterviewee=1` 时填写）：发件箱 ID，引用 `getEmailSenderList` 结果中的 `data.id`。
  - `emailTemplateId`（string，`emailInterviewee=1` 时填写）：邮件模板 ID，引用 `getEmailTemplateList` 结果中的 `templateId`。
  - `emailTitle`（string，`emailInterviewee=1` 时填写）：邮件标题。
  - `emailContent`（string，`emailInterviewee=1` 时填写）：邮件正文。
  - `ccEmail`（string，可选）：抄送邮箱，多个用逗号分隔。
  - `notifiers`（object[]，可选）：通知人列表，缺省为空列表。
    - `id`（string，必填）：通知人员工 ID，引用 `searchEmployee` 结果中的 `data.list[].employeeId`。
    - `name`（string，可选）：通知人姓名。
    - `email`（string，可选）：通知人邮箱。
  - `meetingLink`（string，可选）：会议链接。
  - `platformName`（string，可选）：平台名称。
  - `meetingNumber`（string，可选）：会议号。
  - `meetingPassword`（string，可选）：入会密码。

**返回关键字段**：
- `interviewId`（integer）：面试 ID。
- `rounds`（object[]）：面试轮次列表（含轮次标识，用于后续修改/撤销）。
  - `uuid`（string）：轮次标识（UUID）。
  - `roundsSettingId`（string）：轮次设置 ID。

**调用前确认项**：
1. 请确认候选人简历 ID 及应聘职位。
2. 请确认面试时间、轮次、面试官。
3. 请确认面试形式（线上/线下）及对应地址或会议链接。
4. 请确认是否短信/邮件通知候选人及通知内容。

---

## updateInterviewPreview

- **接口名称**：`updateInterviewPreview`
- **描述**：修改面试预览（不实际保存，返回汇总 + 明细供确认）
- **CLI 命令示例**：
  ```bash
  xrxs-cli recruitment updateInterviewPreview --request-body json
  ```
- **参数说明**（JSON body）：与 `updateInterview` 一致。

---

## updateInterview

> ⚠️ **写入操作**：调用前必须向用户确认修改内容，特别是时间、面试官变更可能影响候选人及面试官日程。
> 
> 本操作存在预览接口 `updateInterviewPreview`。调用正式接口前，先执行 `xrxs-cli permission check recruitment-updateInterview` 判断用户是否已授权永久允许执行该命令：
> - 若返回 `true`，说明用户已授权，可直接调用 `updateInterview`。
> - 若返回 `false`，说明用户未授权。此时有两种处理方式：
>   - 若用户希望永久授权，执行 `xrxs-cli permission save recruitment-updateInterview` 保存授权，之后即可直接调用 `updateInterview`。
>   - 若用户仅想单次确认，先调用 `updateInterviewPreview` 展示操作摘要，等用户确认后再调用 `updateInterview`。

- **接口名称**：`updateInterview`
- **描述**：修改面试
- **CLI 命令示例**：
  ```bash
  xrxs-cli recruitment updateInterview --request-body json
  ```
- **参数说明**（JSON body）：与 `addInterview` 基本一致，其中：
  - `interviewId`（integer，必填）：面试 ID。
  - `interviewRounds` 中已有轮次的 `uuid` 必填，用于匹配待更新轮次。

---

## cancelInterviewPreview

- **接口名称**：`cancelInterviewPreview`
- **描述**：撤销面试预览。明细一场面试一行：候选人/应聘职位/面试轮次/面试时间/面试官。
- **CLI 命令示例**：
  ```bash
  xrxs-cli recruitment cancelInterviewPreview --request-body json
  ```
- **参数说明**（JSON body）：
  - `interviewRoundId`（string，必填）：面试轮次 ID（撤销粒度为轮次），引用 `getResumeInterviewList` 结果中的 `data.interviewRoundId`。
  - `cancelReason`（string，必填）：撤销原因，不超过 1000 个字符。
  - `form`（integer，必填）：面试形式，`0` 现场面试，`2` 电话面试，`5` 腾讯会议，`6` 钉钉视频，`7` 飞书视频，`8` 其他视频，`9` 企业微信；视频面试形式会同步撤销猿圈会议。

**返回关键字段**：
- `detailData`（object[]）：明细数据列表。
- `summaryData`（object）：汇总数据。
- `detailHeaderMap`（object）：明细表头（fieldName → 中文标签）。
- `summaryHeaderMap`（object）：汇总表头（fieldName → 中文标签）。
- `detailHeaderShowField`（string[]）：明细展示字段顺序。
- `summaryHeaderShowField`（string[]）：汇总展示字段顺序。

---

## cancelInterview

> ⚠️ **写入操作**：调用前必须向用户确认撤销原因及影响范围，撤销后可能需要重新安排面试。
> 
> 本操作存在预览接口 `cancelInterviewPreview`。调用正式接口前，先执行 `xrxs-cli permission check recruitment-cancelInterview` 判断用户是否已授权永久允许执行该命令：
> - 若返回 `true`，说明用户已授权，可直接调用 `cancelInterview`。
> - 若返回 `false`，说明用户未授权。此时有两种处理方式：
>   - 若用户希望永久授权，执行 `xrxs-cli permission save recruitment-cancelInterview` 保存授权，之后即可直接调用 `cancelInterview`。
>   - 若用户仅想单次确认，先调用 `cancelInterviewPreview` 展示操作摘要，等用户确认后再调用 `cancelInterview`。

- **接口名称**：`cancelInterview`
- **描述**：撤销面试
- **CLI 命令示例**：
  ```bash
  xrxs-cli recruitment cancelInterview --request-body json
  ```
- **参数说明**（JSON body）：
  - `interviewRoundId`（string，可选）：面试轮次 ID（撤销粒度为轮次），引用 `getResumeInterviewList` 结果中的 `data.interviewRoundId`。
  - `cancelReason`（string，必填）：撤销原因，不超过 1000 个字符。
  - `form`（integer，可选）：面试形式，视频面试形式会同步撤销猿圈会议。

**调用前确认项**：
1. 请确认要撤销的面试轮次 ID。
2. 请确认撤销原因。
3. 请确认撤销后是否需要重新安排面试。

---

## remindInterviewerFeedback

> ⚠️ **写入操作**：调用前必须向用户确认要催促的面试轮次及面试官，避免误操作。

- **接口名称**：`remindInterviewerFeedback`
- **描述**：提醒面试官反馈（催未反馈的面试官提交评价）
- **CLI 命令示例**：
  ```bash
  xrxs-cli recruitment remindInterviewerFeedback \
    --resume-id RESUME_123456 \
    --interview-round-id ROUND_123456
  ```
- **参数说明**：
  - `--resume-id`（string，可选）：简历 ID，引用 `getResumeList` / `getTalentResumeList` 结果中的 `data.data.resumeId`。
  - `--interview-round-id`（string，可选）：面试轮次 ID，引用 `getResumeInterviewList` 结果中的 `data.interviewRoundId`。

**调用前确认项**：
1. 请确认要催促的面试轮次 ID 及对应面试官。
2. 请确认简历 ID。

