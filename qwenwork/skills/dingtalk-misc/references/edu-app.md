# 家校应用 (edu-app) 命令参考

## 命令总览

### message (消息管理)

| 命令 | 用途 | 必填参数 |
|------|------|----------|
| `message summary-list` | 查询消息摘要列表 | `--class-id`, `--cid`, `--target-role`, `--status` |

> `--target-role`: guardian(家长) / student(学生)
> `--status`: 0(未处理) / 1(已处理)

### task (任务管理)

| 命令 | 用途 | 必填参数 |
|------|------|----------|
| `task publish-list` | 查询发布的家校任务列表（仅老师） | 无（均可选） |
| `task all-list` | 查询全部家校任务列表（仅老师） | `--biz-id`(班级ID) |
| `task student-list` | 查询学生待办任务列表 | `--students`(JSON数组) |
| `task family-list` | 查询家校任务列表（家长侧） | `--class-id`, `--cid`, `--target-role` |

> `--task-sources` 可选值（逗号分隔）: EDU_HOMEWORK, EDU_CARD, EDU_NOTICE, EDU_SR, EDU_DIPLOMA
> `task family-list --status`: 可选任务状态过滤

### report (成绩单管理)

| 命令 | 用途 | 必填参数 |
|------|------|----------|
| `report get` | 获取成绩单列表 | `--ids`(逗号分隔整数) |
| `report by-teacher` | 查询老师创建的成绩单 | 无（均可选） |
| `report by-class` | 查询班级学生成绩明细 | `--report-id`, `--class-id` |
| `report by-student-list` | 查询学生收到的成绩单 | `--class-id`, `--student-id` |
| `report by-student-detail` | 查询学生成绩明细 | `--report-id`, `--student-id`, `--class-id` |
| `report create-report` | 创建成绩单 | `--identifier`, `--exam-title`, `--class-list`(JSON), `--subject-list`(JSON) |
| `report save-report-detail` | 保存成绩单明细 | `--report-id`, `--class-detail-list`(JSON) |
| `report delete-report` | 删除成绩单（破坏性，需 `--yes`） | `--report-id` |
| `report trend-by-student` | 查询学生成绩趋势 | `--student-id`, `--report-detail-id`, `--class-id` |

> `report create-report --class-list`: JSON 数组，格式 `[{"classId":"xxx","className":"xxx"}]`
> `report create-report --subject-list`: JSON 数组，格式 `[{"name":"语文","score":100}]`
> `report create-report --score-type`: SCORE(数值) / LEVEL(等级)
> `report save-report-detail --class-detail-list`: 深层嵌套 JSON，含 classId/className/studentDetailList（含 studentId/studentName/subjectList 等）
> `report trend-by-student --trend-type`: score(分数趋势) / rank(班级排名趋势) / gradeRank(年级排名趋势)，缺省 score
> `report trend-by-student --report-detail-id`: 从 `report by-student-detail` 响应中获取
> `report trend-by-student --subject-name`: 可选，缺省查总分趋势

### notice (通知管理)

| 命令 | 用途 | 必填参数 |
|------|------|----------|
| `notice create` | 创建并发布通知 | `--identifer`, `--content` |
| `notice get` | 查询通知详情 | `--notice-id` |
| `notice list-by-teacher` | 查询老师发布的通知列表 | 无（均可选） |
| `notice list-by-student` | 查询学生通知列表 | `--student-id`, `--class-id` |
| `notice confirm` | 确认收到通知 | `--notice-id`, `--student-id` |
| `notice confirm-status` | 查询通知确认状态 | `--notice-id`, `--class-id` |
| `notice delete` | 删除通知（破坏性，需 `--yes`） | `--notice-id` |

> `notice create` 的幂等字段拼写为 `--identifer`（少一个 i），与上游字段 `input.identifer` 一致，不要写成 `--identifier`
> `notice create --target-role`: guardian / student；`--is-signed true` 表示需要签收

### circle (班级圈)

| 命令 | 用途 | 必填参数 |
|------|------|----------|
| `circle posts` | 查询学生班级圈动态 | `--class-id`, `--student-id`, `--target-role` |
| `circle class-posts` | 查询班级圈动态列表 | `--class-id` |

> `--target-role`: guardian(家长视角) / student(学生视角)
> 返回动态的文字内容、图片URL列表、发布者姓名、发布时间、评论数、点赞数等。
> `circle class-posts --cursor` 为分页游标（毫秒时间戳），首次不传默认当前时间；`--count` 每页数量，默认 20，最大 300

### card (打卡管理)

| 命令 | 用途 | 必填参数 |
|------|------|----------|
| `card update` | 修改打卡标题或内容（仅创建者） | `--card-id`, `--identifier`, `--title`/`--content` |
| `card end` | 提前结束打卡任务（仅创建者） | `--card-id` |
| `card list` | 查询打卡列表（学生/家长） | `--status`(FINISH/UNFINISH) |
| `card user-statistic` | 查询班级打卡完成/未完成人员（老师/班主任） | `--card-id`, `--task-code`, `--class-id` |
| `card finish-info` | 查询打卡详情及完成进度 | `--card-id`, `--card-biz-id` |
| `card create` | 创建打卡任务（仅老师） | `--identifier`, `--title`, `--content`, `--class-ids`, `--card-cycle` |
| `card create-comment` | 创建打卡评论 | `--identifier`, `--card-id`, `--card-biz-id`, `--post-id`, `--content` |
| `card ranking` | 查询打卡排行榜 | `--card-id`, `--class-id` |
| `card student-records` | 查询学生打卡记录 | `--card-id`, `--class-id`, `--card-biz-id`, `--student-user-id` |
| `card submit` | 提交打卡 | `--card-id`, `--card-task-id`, `--card-biz-id` |

> `card list --status`: FINISH(已完结) / UNFINISH(进行中)
> `card finish-info --target-role`: teacher / headmaster / guardian / student，未传时按 uid 真实身份自动推断
> `card finish-info --student-id`: 当 targetRole 为 guardian 时，用于指定查看某个孩子的进度
> `card create --card-cycle`: 打卡周期天数；`--card-frequency`: 打卡频次，逗号分隔 1-7 代表周一至周日
> `card create-comment --post-id`: 学生打卡记录 ID（整数）
> `card submit --reissue-card`: 非当天提交时建议设为 true
> `card student-records --cursor` / `--page-size`: 分页参数

### countdown (倒计时管理)

| 命令 | 用途 | 必填参数 |
|------|------|----------|
| `countdown check-open` | 检查倒计时是否已开启 | `--cid` |
| `countdown open` | 开启倒计时 | `--cid`, `--goal`, `--deadline` |
| `countdown close` | 关闭倒计时 | `--cid` |
| `countdown detail` | 查询倒计时详情 | `--cid` |
| `countdown update` | 更新倒计时目标或截止日期 | `--cid` |

> `countdown open --goal`: 倒计时目标文字；`--deadline`: 截止日期
> `countdown open --daily-msg-open` / `--open-ai-encourage`: 可选开关
> `countdown update` 仅传需要修改的字段（`--goal` / `--deadline`）

### homework (作业管理)

| 命令 | 用途 | 必填参数 |
|------|------|----------|
| `homework create` | 创建并发布作业 | `--identifier`, `--hw-content` |
| `homework get` | 查询作业详情 | `--homework-id` |
| `homework list-by-teacher` | 查询老师作业列表 | 无（均可选） |
| `homework list-by-student` | 查询学生作业列表 | `--student-id`, `--class-id`, `--user-name` |
| `homework class-by-homework` | 查询作业的班级提交情况 | `--homework-id` |
| `homework class-detail` | 查询班级作业详情 | `--homework-id`, `--class-id`, `--user-name` |
| `homework submit-statistics` | 查询作业提交统计 | `--homework-id`, `--class-id` |
| `homework student-detail` | 查询学生作业详情 | `--homework-id`, `--student-id`, `--class-id` |
| `homework submit` | 提交作业 | `--hw-content-detail-id` |
| `homework create-comment` | 创建作业评语 | `--comment`, `--hw-content-detail-id` |
| `homework delete` | 删除作业（破坏性，需 `--yes`） | `--homework-id` |
| `homework external-url` | 获取作业附件外部访问 URL | `--media-id` |
| `homework content-detail` | 查询作业内容详情 | `--homework-id`, `--student-id` |
| `homework unfinished-list` | 查询未完成作业列表 | `--student-id` |

> 作业正文用 `--hw-content`（不是 `--content`）；`--hw-title` 为可选标题
> `homework submit` 与 `homework create-comment` 定位到具体作业内容用 `--hw-content-detail-id`
> `homework external-url --media-id`: 逗号分隔的媒体 ID 列表
> `homework unfinished-list --time-range`: 时间范围过滤（如 TODAY）

### diploma (奖状管理)

| 命令 | 用途 | 必填参数 |
|------|------|----------|
| `diploma create` | 创建并颁发奖状 | `--identifier`, `--content`, `--user-name` |
| `diploma get` | 查询奖状详情 | `--diploma-id` |
| `diploma list-by-teacher` | 查询老师创建的奖状列表 | 无（均可选） |
| `diploma list-by-student` | 查询学生收到的奖状列表 | `--student-id`, `--class-id` |
| `diploma detail` | 查询奖状接收详情 | `--diploma-id` |
| `diploma student-detail` | 查询学生奖状接收详情 | `--diploma-id`, `--student-id`, `--class-id` |
| `diploma statistics` | 查询奖状阅读统计 | `--diploma-id` |
| `diploma read` | 标记奖状为已读 | `--diploma-id` |
| `diploma delete` | 删除奖状（破坏性，需 `--yes`） | `--diploma-id` |

> diploma 是「奖状」，不是毕业证书；`--tag` 用于奖状类别，`--template-url` 指定奖状模板

## 危险操作

以下三条为 `user_required` 破坏性命令，不加 `--yes` 会被确认门禁拦下（`category: validation`, `code: 3`, `reason: confirmation_required`，退出码 3）：

| 命令 | 后果 |
|------|------|
| `notice delete --notice-id <id> --yes` | 删除通知，家长/学生侧不可恢复 |
| `homework delete --homework-id <id> --yes` | 删除作业及其提交记录 |
| `diploma delete --diploma-id <id> --yes` | 删除已颁发的奖状 |
| `report delete-report --report-id <id> --yes` | 删除成绩单 |

其余命令均为读或普通写操作，不需要 `--yes`。

## 意图判断

用户说"消息/消息摘要" → message summary-list
用户说"家校任务/待办任务" → task 子命令
用户说"作业" → homework 子命令（发布→create，查详情→get，批改评语→create-comment，提交→submit，删除→delete + `--yes`）
用户说"成绩/成绩单" → report 子命令（创建→create-report，录入明细→save-report-detail，查询→get/by-teacher/by-class/by-student-list/by-student-detail，趋势→trend-by-student，删除→delete-report + `--yes`）
用户说"通知" → notice 子命令（发通知→create，查详情→get，签收/确认→confirm，查签收情况→confirm-status，删除→delete + `--yes`）
用户说"奖状/表彰/颁奖" → diploma 子命令（颁发→create，查详情→get，阅读统计→statistics，删除→delete + `--yes`）
用户说"班级圈/成长记录/学生动态" → circle posts / circle class-posts
用户说"打卡/打卡任务/打卡完成情况/卡片完成情况" → card 子命令
用户说"倒计时/考试倒计时" → countdown 子命令（开启→open，关闭→close，查详情→detail，检查→check-open，修改→update）

关键区分: homework(作业，独立命令组) vs task(家校任务聚合列表，含作业/打卡/通知/奖状等来源)
关键区分: circle(班级圈动态/成长记录) vs message(AI消息总结)
关键区分: diploma(奖状/表彰) vs report(成绩单)
老师视角用 `list-by-teacher`，学生/家长视角用 `list-by-student`，homework / notice / diploma 三组同构。

## 核心工作流

### 老师场景
1. 查看发布的任务 → `task publish-list --need-statistic -f json`
2. 查看某班全部任务 → `task all-list --biz-id <classId>`
3. 查看成绩单 → `report by-teacher --status 1`
3.1 创建成绩单 → `report create-report --identifier <orgId-staffId-UUID> --exam-title "期中考试" --class-list '[{"classId":"<classId>","className":"三班"}]' --subject-list '[{"name":"语文","score":100}]'`
3.2 录入成绩明细 → `report save-report-detail --report-id <id> --class-detail-list '[{"classId":"<classId>","className":"三班","studentDetailList":[{"studentId":"<uid>","studentName":"张三","subjectList":[{"name":"语文","score":95}]}]}]'`
4. 查看班级成绩明细 → `report by-class --report-id <id> --class-id <classId>`
4.1 查询学生成绩趋势 → `report trend-by-student --student-id <uid> --report-detail-id <detailId> --class-id <classId>`
5. 查看某班打卡完成情况 → `card user-statistic --card-id <cardId> --task-code <taskCode> --class-id <classId> --finish`
5.1 创建打卡任务 → `card create --identifier <orgId-staffId-UUID> --title "每日阅读" --content "阅读30分钟" --class-ids <classId> --card-cycle 30`
5.2 查看打卡排行榜 → `card ranking --card-id <cardId> --class-id <classId>`
6. 发布作业 → `homework create --identifier <orgId-staffId-UUID> --hw-content "第三章习题" --class-ids <classId>`
7. 查看作业提交统计 → `homework submit-statistics --homework-id <id> --class-id <classId>`
8. 批改作业写评语 → `homework create-comment --hw-content-detail-id <id> --comment "写得很好"`
9. 删除作业 → `homework delete --homework-id <id> --yes`
10. 发布通知 → `notice create --identifer <orgId-staffId-UUID> --content "明天放假" --class-ids <classId> --is-signed true`
11. 查看通知签收情况 → `notice confirm-status --notice-id <id> --class-id <classId>`
12. 删除通知 → `notice delete --notice-id <id> --yes`
13. 颁发奖状 → `diploma create --identifier <orgId-staffId-UUID> --content "三好学生" --user-name <老师姓名> --class-ids <classId>`
14. 查看奖状阅读统计 → `diploma statistics --diploma-id <id>`
15. 删除奖状 → `diploma delete --diploma-id <id> --yes`

### 家长场景
1. 查看孩子待办 → `task student-list --students '[{"userId":"<uid>","bizId":"<classId>"}]'`
2. 确认通知 → `notice confirm --notice-id <id> --student-id <uid>`
3. 查看孩子收到的通知 → `notice list-by-student --student-id <uid> --class-id <classId>`
4. 查看孩子班级圈动态 → `circle posts --class-id <classId> --student-id <studentId> --target-role guardian`
4.1 查看班级圈动态列表 → `circle class-posts --class-id <classId>`
5. 查看孩子进行中打卡 → `card list --status UNFINISH`
5.1 提交打卡 → `card submit --card-id <cardId> --card-task-id <cardTaskId> --card-biz-id <bizId>`
5.2 查看孩子打卡记录 → `card student-records --card-id <cardId> --class-id <classId> --card-biz-id <bizId> --student-user-id <uid>`
6. 查看孩子作业列表 → `homework list-by-student --student-id <uid> --class-id <classId> --user-name <家长姓名>`
6.1 查看未完成作业 → `homework unfinished-list --student-id <uid>`
7. 查看孩子收到的奖状 → `diploma list-by-student --student-id <uid> --class-id <classId>`

### 学生场景
1. 查看自己的班级圈动态 → `circle posts --class-id <classId> --student-id <studentId> --target-role student`
2. 提交作业 → `homework submit --hw-content-detail-id <id> --content "已完成"`
3. 标记奖状已读 → `diploma read --diploma-id <id>`

## 上下文传递表

| 操作 | 从返回中提取 | 用于 |
|------|-------------|------|
| `dws edu-contact school class-list` | `deptId` | task all-list 的 --biz-id |
| `dws edu-contact class students` | `userId` | task student-list 的 students.userId |
| `dws edu-group class-group conversation-id` | `conversationId` | message summary-list 的 --cid |
| `report by-teacher` | `schoolReportId` | report get/by-class/by-student-detail/delete-report 的 --report-id |
| `report by-student-detail` | `schoolReportDetailId` | report trend-by-student 的 --report-detail-id |
| `report create-report` | `schoolReportId` | report save-report-detail 的 --report-id |
| `dws edu-contact family children` | `studentUserId`, `classId` | circle posts 的 --student-id, --class-id |
| `task publish-list` | `cardId` | card update/end/finish-info 的 --card-id |
| `task publish-list` | `taskCode` | card user-statistic 的 --task-code |
| `homework list-by-teacher` | `homeworkId` | homework get/delete/submit-statistics 的 --homework-id |
| `homework class-detail` | `hwContentDetailId` | homework submit / create-comment 的 --hw-content-detail-id |
| `notice list-by-teacher` | `noticeId` | notice get/confirm/confirm-status/delete 的 --notice-id |
| `diploma list-by-teacher` | `diplomaId` | diploma get/detail/statistics/delete 的 --diploma-id |

---

## SKILL 摘要（原 dingtalk-edu-app/SKILL.md 正文）

## 意图表

| 用户说 | 命令 |
|--------|------|
| "查班级消息摘要" | `dws edu-app message summary-list --class-id <id> --cid <id> --target-role guardian\|student --status 0\|1` |
| "查家校任务" | 见 [edu-app.md](./edu-app.md) `task` 章节 |

## 跨产品协作

- 师生群本身 → 见本包 references/edu-group.md
- 家校通讯录 → 见本包 references/edu-contact.md
