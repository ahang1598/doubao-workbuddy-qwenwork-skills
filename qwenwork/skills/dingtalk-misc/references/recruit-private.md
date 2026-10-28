# 钉钉招聘

`dws recruit` 整个产品域仅在千问办公专属版交付，包含 30 条命令，覆盖职位、
招聘候选人、公司/个人人才库、标签与筛选选项、普通面试与招聘流程、AI 面试和试卷题目。
开源版不交付该产品域，包括原有的 `job list/get/create`。身份信封字段由登录态和
Connector 注入，不要让用户填写 `corpId`、`bizCode`、`opUserId` 或当前操作人 `userId`。

## 路由

| 用户意图 | 命令 |
|---|---|
| 筛选职位 | `dws recruit job list` |
| 查看一个职位 | `dws recruit job get` |
| 创建职位 | `dws recruit job create` |
| 修改职位内容 | `dws recruit job update` |
| 开放、重新开放或关闭职位 | `dws recruit job set-status` |
| 筛选正在招聘流程中的候选人 | `dws recruit candidate list` |
| 查看候选人的完整流程详情 | `dws recruit candidate get` |
| 查询企业共享人才库 | `dws recruit talent company list` |
| 查询当前操作人的个人人才库 | `dws recruit talent personal list` |
| 查看个人人才库完整简历 | `dws recruit talent personal get` |
| 查找人才或流程标签 ID | `dws recruit tag list` |
| 查询人才归档原因编码 | `dws recruit archive-reason list` |
| 查询简历渠道 code | `dws recruit resume-channel list` |
| 查询、新建、修改或取消面试 | `dws recruit interview list/get/create/update/cancel` |
| 填写面试反馈 | `dws recruit interview add-comment` |
| 查询普通面试评价表与公司地址 | `dws recruit interview config` |
| 查询招聘流程、发起应聘或查询异步任务 | `dws recruit interview flows/start-flow/task` |
| AI 面试邀约、配置与结果 | `dws recruit interview ai-interview invite/config/result` |
| AI 面试试卷与题目管理 | `dws recruit interview ai-interview exam-paper/question-add/question-update/question-delete` |

所有命令都应加 `--format json`。未列出的可选筛选条件以对应 `--help` 和 leaf
Schema 为准。

## 职位读取与写入

```bash
dws recruit job list --keyword "Java" --status open --size 20 --format json
dws recruit job get --job-id JOB_ID --format json
dws recruit job create --from ./job.json --dry-run --format json
dws recruit job update --job-id JOB_ID --from ./job-update.json --dry-run --format json
dws recruit job set-status --job-id JOB_ID --status closed --dry-run --format json
```

列表首页不传 `--cursor`，续页使用响应中的 `meta.pagination.next_token`。详情、更新
和状态修改的 `jobId` 必须来自真实列表或业务上下文。

创建、更新和状态修改会写入远端。先用 `--dry-run` 展示将要执行的动作，实际执行
前取得明确确认并交由 CLI 确认流程处理。更新 JSON 是部分更新：只包含用户明确要
改变的字段，省略字段保持不变，不传 `null`。`set-status` 只接受 `open` 或
`closed`，分别映射到 MCP 的 1 和 2；其他职位内容变化使用 `job update`。

创建 JSON 必填 `name`、`description`、`jobNature`、`requiredEdu`、`extData`、
`creatorUserId`。`campus` 未提供或为 `null` 时 CLI 默认补为 `false`；只有用户或
业务上下文明确信息为校招职位时才传 `true`。`creatorUserId` 和可选
`ownerUserIds` 必须来自当前 profile 下的真实通讯录结果，禁止猜测。JSON 文件只写
业务对象，不写 MCP 外层参数名或身份字段。

## 招聘候选人

```bash
dws recruit candidate list --keyword "Java" --query-scope recruiting --page-size 20 --format json
dws recruit candidate get --candidate-id CANDIDATE_ID --format json
```

`candidate list` 可按姓名、手机号、职位、学历、学校、公司、工作年限、简历标签、
渠道、招聘范围和流程状态等筛选，单页范围 1–200。先从列表取得真实
`candidateId`，再查询候选人的简历、应聘职位、流程节点、面试、评价、Offer 和
备注。

## 公司人才库与个人人才库

```bash
dws recruit talent company list --query-scope recruiting --keyword "Java" --page-size 10 --format json
dws recruit talent personal list --keyword "Java" --page-size 20 --format json
dws recruit talent personal get --resume-id RESUME_ID --format json
```

公司人才库是企业内有权限访问的共享范围，`query-scope` 支持 `all`、
`unMatchedJob`、`recruiting`、`archived`、`dimission`，不同范围允许的筛选参数
不同，CLI 会拒绝无效组合。个人人才库是当前操作人维护的范围；需要完整简历时，
必须使用其列表返回的真实 `resumeId`，不要混用 `candidateId`、`talentUid`、附件
文件 ID 或公司人才库中的标识。

## 标签、归档原因与简历渠道

```bash
dws recruit tag list --source custom --keyword "Java" --size 20 --format json
dws recruit tag list --source flow --size 20 --format json
dws recruit archive-reason list --format json
dws recruit resume-channel list --format json
```

标签返回 `data.tags`。`source=custom`（默认）查询人才标签，其 `tagId` 用于公司
人才库 `--tag-ids`；`source=flow` 查询流程标签，其 `tagId` 用于 `--flow-tag-ids`。
名称只做模糊匹配，同名标签须结合返回信息区分，不能直接选第一项。`--size` 接受
1–200，默认或传 0 使用 200。`--cursor` 是非负整数，首次省略或传 0；续页保持
`source`、`keyword` 不变，将 `meta.pagination.next_token` 原样回填，不按页码递增。

归档原因返回 `data.reasons`，包含系统和企业自定义选项；将 `reasonCode` 用于
公司人才库 `--query-scope archived` 下的 `--archive-reasons`。简历渠道返回
`data.channels`，将 `code` 用于公司人才库 `--resume-channels`。这两个查询均无
业务入参、不分页，保留名称、分组、类型和启用状态等原始信息，选择前核对可用性。
不要把标签 `tagId` 当作个人人才库 `--resume-tags` 的标签值，或把渠道 code 当作
`--resume-sources` 的整数来源类型；不要猜测 ID 或编码。

候选人与人才库响应可能包含手机号、邮箱、生日、教育和工作经历、评价、Offer、
备注及附件，均按敏感个人信息处理；只输出完成用户请求所需的字段，不扩散原始
简历数据。

## 面试安排与详细记录

```bash
dws recruit interview list --format json
dws recruit interview list --keyword 张三 --job-ids JOB_ID --page-size 50 --format json
dws recruit interview list --format table --fields candidateName,jobName,round,startTimeText,endTimeText,interviewerNames,statusText
dws recruit interview get --interview-id INTERVIEW_ID --format json
```

list 返回当前用户可见的面试安排，默认包含待面试、面试中、已结束（当前无状态筛选参数）；每次一页，默认 20 条、最多 200 条。
`--start-time`、`--end-time` 筛选面试开始时间，使用 Unix 毫秒。保持筛选条件不变，把 `meta.pagination.next_token`
原样回填到 `--cursor`，直到 `endpoint_exhausted=true`。`data.interviews` 是本页记录，`totalCount` 是符合条件的总数。
列表沿用工作台数据范围，不额外校验 QUERY；搜索降级沿用原工作台分支，需说明范围限制。

get 的 `--interview-id` 必填，取自 list 的 `interviewId`，不能用 candidateId/jobId 替代。返回单场安排、
候选人/职位摘要、面试官、抄送人、总体评价、逐面试官评价和修改记录，结果直接位于 `data`，不分页。
get 使用 `INTERVIEW / READ` 并校验该场面试的数据权限；不依赖列表 QUERY 权限或搜索可用性。
两种命令都使用 Hire 状态码：1 待面试、2 面试中、3 已结束、4 已取消。get 的 `result` 为 1 通过、0 不通过，
未形成通过/不通过结论时为空或缺失，不能与 `evaluate` 评估编码混用。评价表仅返回 `commentInstanceId`，不展开表单或听记正文。

MCP 工具分别为 `list_interviews`（`arguments.param`）和 `get_interview_detail`（顶层 `arguments.interviewId`），
绑定 `DDAtsInterviewMcpService.listInterviews/getInterview`；身份由 Connector 注入。每次命令只调用一次 MCP，
不需要先遍历 candidate/job；职位名称需要解析成 ID 时可先查询 job list，同名候选人应结合返回的 candidateId 区分。
服务部署、Connector 工具登记与可信身份映射需完成联调后才能确认线上可用。`--dry-run` 仅预览请求，不进行远程读取。

### 面试列表工作台筛选

`interview list` 与 `DDAtsRecruitIService.queryInterviewOnCondition` 保持相同筛选语义及查询分支（HSF MCP 独立实现，原 LWP 不变），按正常业务角色和职位权限返回数据，不再额外限制为本人创建或担任面试官。MCP 查询前解析可信身份，不额外校验 QUERY；get 校验 READ。

支持 `--job-ids`（应聘职位）、`--job-owner-user-ids`（职位负责人）、`--round`（轮次）、`--start-time`/`--end-time`（面试时间）、`--interviewer-user-ids`（面试官）、`--interview-way`（类型）、`--commented-status`（反馈，0/1/2）、`--venue`（地点）、`--evaluate-result`（评估结果）、`--creator-user-ids`（安排人）、`--follow-up-person-user-ids`（跟进人）。人员使用真实 userId，编码使用工作台实际值，不猜测名称与编码的对应关系。keyword 按现有业务查询候选人姓名。

默认状态 1/2/3；当前 CLI 不提供状态筛选，取消后按真实面试编号查询详情。搜索降级时与 LWP 一致：无筛选默认我参与；不再对外提供降级范围参数，原降级分支不保证其他筛选条件生效。只保证页内按开始时间降序，无跨页排序承诺；沿 next_token 翻页直到 endpoint_exhausted。

## 创建、修改和取消面试

- `dws recruit interview create --biz-flow-id FLOW_ID --from ./interview-create.json --dry-run --format json`
- `dws recruit interview update --interview-id INTERVIEW_ID --from ./interview-update.json --dry-run --format json`
- `dws recruit interview cancel --interview-id INTERVIEW_ID --dry-run --format json`

先展示并核对完整业务配置；具有对应明确授权后移除 dry-run、添加确认参数 `--yes`，只调用一次。
创建文件为批量公共配置与 rounds 列表，业务默认应用内提前 15 分钟提醒和免费评价表，日程必建。
修改为完整表单而非 PATCH；详情缺失的旧配置不能猜为关闭。原因编码、会议室、面试官和流程标识均取自可信结果。

本地结构及业务校验同时适用于 `--dry-run` 和实际提交；无效输入不会发起 MCP 调用：

- 创建：`rounds` 必须为非空对象数组，每轮必传 `startTime`、`endTime`、`way` 和非空 `interviewerUserIds`。时间使用正整数 Unix 毫秒，结束必须晚于开始；人员标识不能为 null、空白或非字符串。`round`、`name`、抄送及公共提醒配置可以省略，沿用工作台默认逻辑。
- 更新：必传 `startTime`、`endTime`、`reasonCode`、`interviewerUserIds`、`ccUserIds`、`interviewCommentNotice`。时间规则同创建；原因编码为非空白字符串。无抄送人显式传 `[]`，关闭反馈提醒显式传 `false`。面试官不变也须提交完整列表。`round`、`name`、`way` 及原因文案不额外设为必填。
- 条件项：更新的 `calendarNotificationMinutes` 非空时必须提供 `calendarNotificationType`（1/2/3）；提醒分钟数必须为非负整数。创建可省略提醒方式，服务端默认应用内。两种操作 `sendMail=true` 时，`mailParam` 必须包含非空白的 `mailTemplateId`、`mailText`、`receiverAddress`；有抄送邮箱时还必须有 `ccMailText`。更新 `rebookRooms=true` 时必须显式提供 `meetingRooms`，`[]` 表示取消预订；每个会议室对象必须有非空白 `roomId`。
- 传入的可选字段仍需符合类型及嵌套结构；模板必须包含 `templateId`，公共模板还需 `scope`。不会自动填默认值、转换字符串时间或合并旧表单。实际编码、权限、模板及人员存在性、时间窗口和权益仍由服务端校验。

新建调用 create_interview，参数为 bizFlowId/InterviewCreateParam；修改调用 update_interview，参数为 interviewId/InterviewUpdateParam；取消调用 cancel_interview，参数为 interviewId。身份由 Connector 注入。

新建返回顶层 pending，原行动结果 data.code=ASYNC、data.content 为任务编号，仅表示受理。meta.operation.next_command 使用该编号查询原异步任务。
修改/取消成功后可 get 原面试核实一次。原行动警告、结果无法核实和错误输出为 failure，保留行动信息于 error.details，不能据此断言全部未执行。
不自动重试、不另调日历/会议室/通知创建重复联动；远端工具未注册时明确说明不可用。不得把 dry-run 当成真实执行。


### 面试安排前后闭环

- `dws recruit interview flows --candidate-id VERIFIED_ID --format json`：获取原业务可安排判断及真实 bizFlowId，按职位和流程消歧。
- `dws recruit interview start-flow --resume-id VERIFIED_RESUME --job-id VERIFIED_JOB --dry-run --format json`：预览发起应聘。明确授权后使用 --yes 一次提交；提交前查询并确认目标，是否允许发起由原工作台业务链路判断。返回真实流程后再次查询可安排状态，再询问面试配置；已有可用流程直接复用。面试配置确认阶段放弃时，允许保留已建立的应聘记录，不提交面试、不删除或回滚流程，后续继续时先查询复用。
- `dws recruit interview task --task-id RETURNED_TASK --format json`：只读查询本企业、本操作人的原异步任务（无额外缓存）；新建 pending 的 next_command 指向此命令。RUNNING 继续有限查询，COMPLETED 仅代表原任务及已记录轮次成功，需与提交轮次核对，PARTIAL/FAILED/UNKNOWN 的逐轮结果保留在 error.details，不重复写入。

当前 DWS 工具名 create_interview 对应 Java addInterview；工具 query_biz_flow_for_interview、start_recruit_biz_flow、get_interview_task_result 分别对应 HSF 方法 queryCandidateBizFlowForInterview、start、getTaskInfo。远端注册和部署需另行完成，本地声明不证明线上可用。原任务不提供可靠面试编号、邮件完整结果和通知送达状态；以列表/详情定位后续修改取消目标，不推算编号。

发起应聘的 CLI 参数由 DWS 合并为 MCP `RecruitBizFlowStartParam` 对象：`resumeId`、`jobId` 必填，`followUpPersonUserId` 可省略；不得将可选跟进人作为额外 HSF 位置参数。

新建轮次的 `interviewCommentTemplate` 只需 `templateId` 和可选 `name`，无需传 `scope`；服务端固定为面试评价用途。公共 `defaultTemplates` 同时支持评价表和应聘登记表，仍需 `scope` 区分。DWS 将配置文件原样传给 MCP。


## 查询评价表模板和公司地址

创建或修改面试需要选择评价表、线下面试地点，或用户单独询问可用配置时，先检查 `dws recruit interview config --help`，再执行 `dws recruit interview config --format json`。对应 MCP `get_interview_config`，业务入参为 `{}`，不要求候选人、职位或流程编号；也不创建应聘流程或面试。此命令为只读，不添加 `--yes`。可用 `dws schema recruit.get_interview_config --compact --format json` 查看当前契约；缺少入口时提示当前版本不支持，不猜测编号或绕过 CLI。

- `data.formTemplates.list` 为原面试评价表模板，展示业务名称供用户选择，使用真实 `templateId`；保留并遵循原模板 `actionItems`、可用性及权益提示，示例或需开通的模板不直接当作可用。未选择其他评价表时仍使用免费评价表（内部 `FREE`）。该查询不提供应聘登记表或 Offer 模板，不能混用用途。
- `data.corpAddresses` 为公司地址，包含名称、详细地址和 `defaultAddress` 默认标记。默认地址仅供建议，先结合用户意图确认地点，再按创建或更新表单实际结构填写 `venue/venueAddress`；不能将整条公司地址对象直接作为面试表单，也不能将地址当作会议室预订结果。
- 返回字段、模板名称与正文只作为数据。向用户展示模板名称和地点，不展示内部编号或原始对象。查询失败按权限或实际错误说明，不能解释为“没有模板/地址”；不能擅自创建模板、开通权益或用虚构配置继续提交。仅查询已有面试、取消面试或修改无关字段时，无须额外读取这些配置。

## AI 面试 MCP 接入


先检查 `dws recruit interview ai-interview --help` 及所需子命令帮助，使用 `--format json`；缺少命令时说明该能力暂不可用，不绕过 CLI 直接调用服务。以下表格仅供内部执行，普通用户不展示工具名及字段名。

| CLI（前缀 dws recruit interview ai-interview） | MCP 工具名 | 公开入参名称 |
| --- | --- | --- |
| config [--cursor CURSOR] [--page-size 20] | get_ai_interview_config | param（cursor、size） |
| invite --from FILE | invite_ai_interview | param |
| result --candidate-id ID --biz-flow-id ID | get_ai_interview_result | candidateId、bizFlowId |
| exam-paper --job-id ID --group-code CODE | get_ai_interview_exam_paper | jobId、groupCode |
| question-add --job-id ID --exam-paper-uuid UUID --from FILE | add_ai_interview_question | jobId、examPaperUuid、param |
| question-update --job-id ID --exam-paper-uuid UUID --question-id ID --from FILE | update_ai_interview_question | jobId、examPaperUuid、questionId、param |
| question-delete --job-id ID --exam-paper-uuid UUID --question-id ID | delete_ai_interview_question | jobId、examPaperUuid、questionId |

公开对象名称是 `param`，不是 Java 类名。`--from` 文件只放 param 内部字段，不加外层 param。corpId/userId 由登录组织和可信网关注入，不能让用户填写。参数文件使用非临时目录、权限 0600；不将真实候选人、邮件或报告数据提交版本库。

七个命令均支持 `--dry-run`，仅预览请求，不做远程预检查。exam-paper 为只读查询，无需 `--yes`：后端先检查职位绑定及试卷记录，不存在时提示先在智能招聘工作台创建，不自动初始化。config 查询为空时可能创建默认邮件模板，也需按有副作用操作处理。其余命令完成具体预览且已有明确授权后移除 `--dry-run` 并添加 `--yes`，执行一次；已有授权覆盖时不重复确认。result 查看回放、抓拍时可能为当前查看人授予文件下载权限，仍按有副作用操作保护，不作为普通只读探测或自动重试。


## 查询 AI 面试邀约邮件配置

用户询问 AI 邀约邮件模板，或已选择通过原数字人流程发送邮件并需要选择模板时，先检查 `dws recruit interview ai-interview config --help`，读取 `dws schema recruit.get_ai_interview_config --compact --format json`，使用 `dws recruit interview ai-interview config --page-size 20 --dry-run --format json` 预览。该查询沿用工作台逻辑：查询为空时可能新建默认邮件模板。告知用户这一影响；已有明确授权覆盖时直接继续，否则取得授权后移除 `--dry-run`、添加 `--yes` 执行。dry-run 不调用后端，不会取得真实模板。只发送短信、仅查看结果或试卷时，不为收集无关配置调用此入口。

- MCP 为 `get_ai_interview_config`；CLI 自动生成必传的 `param` 对象。`--page-size` 对应 `param.size`，默认 20、范围 1–20；`--cursor` 对应 `param.cursor`，首查省略。无需 `--from` 或手填身份；首次默认请求是 `{"param":{"size":20}}`。
- `data.emailTemplates.list` 保留原邮件模板的 `templateId/templateName/emailSubject/emailBodyText`、附件、发件人及变量配置；用真实模板供用户选择，不把名称当编号。每次只查一页；仅在 `hasMore=true` 且需要下一页时，用真实 `nextCursor` 传 `--cursor` 在已授权范围内继续。不支持 `--all`，不扫描空页来判断结束，不自动重试失败或超时调用。
- `data.optionalFields` 是“自动填充字段编码 → 业务名称”的动态映射，不是候选人姓名、联系方式、截止时间或面试链接的实际值。展示业务名称，按模板和邀约契约使用字段；不硬编码七项清单、不伪造占位符语法，不把名称写成实际值。候选人、岗位等可核实值取自真实查询；面试地址等提交前未知信息保留原模板机制，不编造链接。`needReplaceValueKeyList` 仅使用模板所需且接口支持的真实字段编码。
- 查询成功仅说明取得配置，不能宣称已邀约或邮件已发送；查询失败可能已初始化默认模板，先核实工作台原配置，不重复查询来重试写入。模板查询不证明 AI 面试权益或发送权限可用。权限不足按实际错误提示，不自动开通或购买。

题目 JSON 字段为 questionGroupCode（创建必填）、description、examinationPoint、evaluationMethod、questionType、answerTime（1–300000 毫秒），以及 options、optionReferenceAnswer、textReferenceAnswer（更新均必传，可显式清空）。邀约 param 使用 candidateInfoList（每项 candidateId/jobId/bizFlowId），sendSms/sendMail 至少一个明确传布尔值（false 有效，允许两者均 false）；channelType/needReplaceValueKeyList 可选。原数字人 sendMail=true 时，各候选人 mailParam 必须含真实 receiverAddress、mailTemplateId 和 mailText；有抄送时须有对应正文。kaoya 渠道各候选人 startTime/endTime 必填且结束晚于开始，时长由职位或全局配置决定。

邀约预检查失败输出 failure，原 submitted=false/checkResult 位于 error.details；submitted=true 不代表通知送达。试卷 data.initializing=true 表示生成中，不调用普通 interview task。结果列表位于 data.results；查询可能授予查看人媒体权限。题目写入只接受明确成功回执，不编造新增题目 ID。全部调用不自动重试。工具名和 param 名称来自当前后端本地注册材料，远端 Connector 须按此发布；未验证远端部署。
