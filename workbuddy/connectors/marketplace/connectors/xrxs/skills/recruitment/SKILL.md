---
name: recruitment
version: 1.0.0
description: 招聘管理产品，支持职位、招聘需求、候选人简历、人才库、招聘流程与渠道查询，以及简历推荐、面试安排等协作操作。
metadata:
  requires:
    bins: ["xrxs-cli"]
  cliHelp: "xrxs-cli recruitment --help"
---

**CRITICAL — 场景匹配是第一步，任何人岗推荐等场景化招聘需求（含查询类）都必须先做：① 读 [`references/sop-summary.md`](references/sop-summary.md) 用用户话术匹配场景索引；② 命中 → 再读 [`references/sops/`](references/sops/) 下对应场景文件按步骤执行；未命中 → 回退本文件通用规则。**

> ⚠️ **常见误区（必须避免）**：
> - **"看起来像简单查询"也要先匹配**：「帮我推荐候选人」「根据职位推荐简历」等都是 SOP 场景，**禁止**跳过 summary 直接按 shortcut 文档自行摸索。
> - **禁止**在命中场景后执行 `schema` 查参数（场景文档已给完整请求体）；**禁止**反复用不同 `status` 试探同一接口（场景文档已指定取值）。
> - 若你已读了 shortcut 文档（recruitment-general/candidate/interview 等）却未读 sop-summary.md，**说明匹配步骤被跳过**，请立即补读 summary 再继续。

# recruitment（招聘）

## 产品能力

`recruitment` 是招聘管理模块，面向 HR、招聘负责人与面试官，提供从职位/需求管理、候选人筛选、简历详情查看到简历推荐、面试安排的全流程招聘协作能力。核心能力包括：

- **职位与需求查询**：查看当前负责的职位、职位详情、公司招聘需求。
- **候选人/人才库查询**：按阶段、状态、渠道、自定义流程等多维度筛选候选人，支持集团人才库共享数据查询。
- **简历详情查看**：获取标准简历模型，包括基本信息、工作经历、教育经历、自定义字段等。
- **招聘操作预判**：在安排面试、推荐等操作前，查询简历当前可执行的操作及可用状态。
- **简历推荐**：将候选人推荐给招聘负责人或面试官，支持先预览再正式提交。
- **面试安排**：为候选人安排、修改、撤销面试，查询面试官日程与冲突，选择面试地址、评价表、邮件模板等。
- **招聘流程与渠道**：查询公司招聘流程阶段、简历来源渠道等基础配置。
- **基础数据引用**：查询词典、城市、国家、部门、岗位、职级、成本中心、员工等公共数据，用于构造业务入参。

## 核心 Shortcuts

### 职位与通用查询

- `xrxs-cli recruitment getMyJobList` — 获取当前人员负责的职位列表（按管理范围/权限过滤）。
- `xrxs-cli recruitment getJobDetail --job-id <job-id>` — 获取职位详情。
- `xrxs-cli recruitment getBriefDemandList` — 获取公司的需求列表（按权限过滤，只含 id/name 等简要字段）。
- `xrxs-cli recruitment getChannelList` — 获取来源渠道列表（公司全部渠道）。
- `xrxs-cli recruitment getProcessSettingList` — 获取公司的招聘流程列表。
- `xrxs-cli recruitment getProcessSettingDetail --custom-process-id <custom-process-id>` — 获取招聘流程详情。

### 候选人简历

- `xrxs-cli recruitment getResumeList --request-body '{...}'` — 获取候选人列表（当前公司简历）。
- `xrxs-cli recruitment getTalentResumeList --request-body '{...}'` — 获取人才库候选人列表（查询集团人才库共享数据）。
- `xrxs-cli recruitment getResumeFilterFields` — 获取简历筛选字段定义（供 filters 构造参考）。
- `xrxs-cli recruitment getResumeDetail --resume-id <resume-id>` — 获取候选人详细信息（标准简历模型：基本信息 + 分组 + 自定义字段名值）。
- `xrxs-cli recruitment getResumeDetailOperations --resume-id <resume-id>` — 获取简历可操作列表（招聘操作前预判简历能否安排面试/推荐/发Offer 等）。
- `xrxs-cli recruitment recommendResumePreview --request-body '{...}'` — 简历推荐预览（不实际推荐，返回汇总 + 明细供用户确认）。
- `xrxs-cli recruitment recommendResume --request-body '{...}'` — 简历推荐（把候选人推荐给招聘负责人/面试官）。
- `xrxs-cli recruitment recoverResumePreview --resume-id <resume-id>` — 人才库恢复到流程预览。
- `xrxs-cli recruitment recoverResume --resume-id <resume-id>` — 人才库恢复到流程中（将人才库简历恢复到招聘流程）。
- `xrxs-cli recruitment copyTalentResumePreview --request-body '{...}'` — 人才库重新分配职位预览。
- `xrxs-cli recruitment copyTalentResume --request-body '{...}'` — 人才库重新分配职位（将人才库简历备选到目标职位，生成新简历）。

### 面试管理

- `xrxs-cli recruitment getResumeInterviewList --resume-id <resume-id>` — 获取候选人面试轮次列表（修改/撤销面试前查询，含可撤销标志）。
- `xrxs-cli recruitment getResumeApplyJob --resume-id <resume-id>` — 获取简历应聘职位（安排面试 interviewJob 来源）。
- `xrxs-cli recruitment addInterviewPreview --request-body '{...}'` — 安排面试预览（不实际保存，返回汇总 + 明细供确认）。
- `xrxs-cli recruitment addInterview --request-body '{...}'` — 安排面试。
- `xrxs-cli recruitment updateInterviewPreview --request-body '{...}'` — 修改面试预览（不实际保存，返回汇总 + 明细供确认）。
- `xrxs-cli recruitment updateInterview --request-body '{...}'` — 修改面试。
- `xrxs-cli recruitment cancelInterviewPreview --request-body '{...}'` — 撤销面试预览（展示撤销操作影响的面试明细）。
- `xrxs-cli recruitment cancelInterview --request-body '{...}'` — 撤销面试。
- `xrxs-cli recruitment remindInterviewerFeedback --resume-id <resume-id> --interview-round-id <interview-round-id>` — 提醒面试官反馈（催未反馈的面试官提交评价）。
- `xrxs-cli recruitment getInterviewerScheduleCalendar --request-body '{...}'` — 获取面试官日程日历（查时间范围内面试官的面试/考勤/第三方日程，按天分组，仅展示不做冲突判断）。
- `xrxs-cli recruitment verifyInterviewerSchedule --request-body '{...}'` — 校验面试官日程冲突（面试时间是否与面试官既有面试/考勤/第三方日程冲突）。


## 典型场景（SOP）

场景型需求的编排步骤见 [`references/sop-summary.md`](references/sop-summary.md)（场景匹配索引）与 [`references/sops/`](references/sops/)（分场景详细步骤，通用约定见 [`references/sops/common.md`](references/sops/common.md)）。**任何招聘业务需求（含查询类）都必须先读 summary 匹配场景，命中后再读 sops/ 下对应场景文件执行，禁止跳过匹配直接按 shortcut 文档自行摸索。** 当前已收录 4 个场景：

- 场景一：人岗推荐（根据职位要求推荐匹配候选人，仅展示推荐清单）
- 场景二：推荐简历给用人部门（将候选人简历推荐给指定员工，写入操作需用户确认）
- 场景三：安排面试（为候选人安排或修改面试，写入操作需用户确认）
- 场景四：获取面试官日程（查询面试官日程并总结输出，只读）

## 查询效率与冗余调用提示

回答用户问题时，应优先判断已返回的数据是否足够。若一次查询已能提供用户所需的关键信息，则无需为了补充非必要字段而对每条记录发起级联详情调用。

例如：
- 用户问“我现在有哪些进行中的招聘岗位”时，调用 `xrxs-cli recruitment getMyJobList --hire-status 0` 返回的职位列表通常已包含职位名称、状态、部门等基础信息，足以直接回答该问题，不必再对每个职位调用 `getJobDetail`。
- 如果某个详情字段确实对回答至关重要，可以先尝试调用一次 `getJobDetail` 评估其价值；若发现返回内容对当前问题帮助不大，应停止继续查询其余记录的详情，避免冗余调用。

简言之：先判断已有数据是否足够，足够则不再发起额外查询；不足以回答时，再有针对性地补充查询。

### 面试相关问题优先使用面试接口

当用户问题明显与面试相关（如查询面试安排、面试官日程、安排/修改/撤销面试、面试评价表等）时，应优先使用面试管理相关接口，**不要习惯性地调用 `getResumeList`、`getTalentResumeList`、`getResumeDetail` 等简历列表或详情接口来补充信息**，除非当前问题确实需要这些接口才能获取必要信息。

常见场景：
- 用户问“李明的面试安排” → 只需 `getResumeInterviewList` 获取面试轮次，不必再调 `getResumeDetail` 查看完整简历。
- 用户问“王磊下周有没有空可以面试” → 只需 `getInterviewerScheduleCalendar` / `verifyInterviewerSchedule`，不必查询王磊的简历详情。
- 用户问“公司有哪些评价表” → 只需 `getInterviewFeedbackTemplateList`。
- 用户问“明天的面试官都有谁” → 只需查询面试官日程/面试列表，不必拉取候选人简历详情。

例外：当用户提供的候选人标识是姓名/手机号/邮箱等自然标识，且尚未定位到 `resumeId` 时，可以调用 `getResumeList` 等做一次定位查询，但定位到 `resumeId` 后应停止继续调用简历详情接口。

## 理解用户输入的标识值

用户提及候选人、简历或职位时，给出的值可能是手机号、邮箱、姓名等业务可读标识，而非系统生成的 `resumeId`、`jobId` 等标准 ID。不要默认将这些值直接当作 ID 入参使用。

处理原则：
- 若用户提供的值看起来像手机号、邮箱、姓名等自然标识，应先通过列表/搜索接口（如 `getResumeList`、`getTalentResumeList`）定位到对应记录，获取真实的 `resumeId` 后再执行推荐、安排面试等操作。
- 只有在用户明确说“简历 ID 是 xxx”“职位 ID 是 xxx”，或该值明显为系统 ID 格式时，才可以直接作为 `resumeId`、`jobId` 等入参。
- 例如用户说“把 18001197793 推荐给李京京”，应先将 `18001197793` 理解为候选人的手机号，通过简历查询接口找到对应 `resumeId`，而不是直接传入 `recommendResume --resume-id 18001197793`。

## 场景 Reference

按具体业务场景引用对应文档获取完整接口说明与示例：

- **`recruitment-general`**：通用查询（职位、需求、渠道、流程等）。需要完整接口定义时引用 `Skill: recruitment-general` 或查阅 `references/recruitment-general.md`。
- **`recruitment-candidate`**：候选人简历（候选人/人才库列表、简历详情、筛选字段、简历可操作列表、简历推荐预览/正式推荐、人才库恢复/重新分配）。需要完整接口定义时引用 `Skill: recruitment-candidate` 或查阅 `references/recruitment-candidate.md`。
- **`recruitment-interview`**：面试管理（面试轮次查询、安排/修改/撤销面试及对应预览、评价表、轮次设置、面试地址、面试官日程冲突、邮件通知、提醒面试官反馈）。需要完整接口定义时引用 `Skill: recruitment-interview` 或查阅 `references/recruitment-interview.md`。
- **`recruitment-base`**：基础通用接口（词典、城市、国家、部门、岗位、职级、成本中心、员工搜索过滤条件、员工详情等）。需要完整接口定义时引用 `Skill: recruitment-base` 或查阅 `references/base.md`。

## 预览接口

对于存在预览接口的写入操作，正式调用前应先通过 `xrxs-cli permission check <command>` 判断用户是否已对该命令授权永久允许执行：

- 若返回 `true`，说明用户已授权，可直接调用正式操作接口，无需再调预览接口。
- 若返回 `false`，说明用户未授权。此时有两种处理方式：
  - **永久授权**：若用户确认希望永久允许该命令，执行 `xrxs-cli permission save <command>` 保存授权，之后 `permission check` 会返回 `true`，可直接调用正式操作接口。
  - **单次确认**：先调用预览接口展示操作摘要，用户确认无误后再调用正式操作接口（不保存授权，下次调用前仍会触发 check）。

以 `recommendResume` 为例：先执行 `xrxs-cli permission check recruitment-recommendResume`；若未授权，可执行 `xrxs-cli permission save recruitment-recommendResume` 保存永久授权后直接调用 `recommendResume`，或先调用 `recommendResumePreview` 预览、用户确认后再调用 `recommendResume`。同理：
- 安排面试：`recruitment-addInterview` / `addInterviewPreview`
- 修改面试：`recruitment-updateInterview` / `updateInterviewPreview`
- 撤销面试：`recruitment-cancelInterview` / `cancelInterviewPreview`
- 人才库恢复：`recruitment-recoverResume` / `recoverResumePreview`
- 人才库重新分配职位：`recruitment-copyTalentResume` / `copyTalentResumePreview`

## 安全规则

- **写入/删除前确认**：所有写入类操作（如 `recommendResume`、`addInterview`、`updateInterview`、`cancelInterview`、`recoverResume`、`copyTalentResume`、`remindInterviewerFeedback`）执行前，必须明确提示用户并确认操作意图，包括影响范围、接收人、职位、面试时间/面试官、审批类型/内容等关键信息。
- **敏感字段权限**：涉及简历敏感字段（手机号、邮箱、身份证号等）的查询或推荐，必须按接口权限参数（`viewSensitive` 等）控制，避免越权访问。
- **预览/权限优先**：对于存在预览接口的操作（如简历推荐、安排面试、修改面试、撤销面试、人才库恢复/重新分配），正式执行前先调用 `xrxs-cli permission check <command>` 检查用户是否已永久授权；未授权时可选择执行 `xrxs-cli permission save <command>` 保存永久授权，或先调用预览接口展示汇总与明细、用户确认后再执行正式操作。
- **数据引用**：构造入参时，ID 类字段（`jobId`、`resumeId`、`employeeId`、`customProcessId`、`customStageId`、`interviewRoundId` 等）必须引用已有接口返回的真实数据，禁止凭空构造。

## 错误处理

- 接口调用遇网络异常、超时、服务端 5xx 等**瞬时错误**，最多重试 2 次（共 3 次尝试），重试间稍作等待。
- 参数非法、权限不足、数据不存在、约束冲突（如简历当前状态不可推荐/不可安排面试、面试时间与面试官日程冲突、职位已关闭）等**业务校验报错不重试**（重试结果不变）。
- 重试达上限仍失败、或遇业务校验报错时，**停止本次操作**且不再继续后续步骤；向用户报告操作失败，并附最后一次的错误信息（执行的命令、状态码、报错内容）。
- 接口返回内容可能较大（如候选人列表、面试官日程日历），工具返回可能被截断（约 20000 字符，表现为 JSON 不完整）；**不要基于不完整数据下结论**，改用更聚焦的查询（分页/关键字/更小日期范围）或查看完整返回后再继续。
- 关键信息缺失（如查询结果被截断、未定位到 `resumeId`/`jobId`、面试轮次信息不完整等）时，**停止**并向用户报告缺失项，不要猜测、不要继续后续步骤。
