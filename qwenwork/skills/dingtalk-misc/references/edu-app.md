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

> `--task-sources` 可选值（逗号分隔）: EDU_HOMEWORK, EDU_CARD, EDU_NOTICE, EDU_SR, EDU_DIPLOMA

### report (成绩单管理)

| 命令 | 用途 | 必填参数 |
|------|------|----------|
| `report get` | 获取成绩单列表 | `--ids`(逗号分隔整数) |
| `report by-teacher` | 查询老师创建的成绩单 | 无（均可选） |
| `report by-class` | 查询班级学生成绩明细 | `--report-id`, `--class-id` |
| `report by-student-list` | 查询学生收到的成绩单 | `--class-id`, `--student-id` |
| `report by-student-detail` | 查询学生成绩明细 | `--report-id`, `--student-id`, `--class-id` |

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

> `--target-role`: guardian(家长视角) / student(学生视角)
> 返回动态的文字内容、图片URL列表、发布者姓名、发布时间、评论数、点赞数等。

### card (打卡管理)

| 命令 | 用途 | 必填参数 |
|------|------|----------|
| `card update` | 修改打卡标题或内容（仅创建者） | `--card-id`, `--identifier`, `--title`/`--content` |
| `card end` | 提前结束打卡任务（仅创建者） | `--card-id` |
| `card list` | 查询打卡列表（学生/家长） | `--status`(FINISH/UNFINISH) |
| `card user-statistic` | 查询班级打卡完成/未完成人员（老师/班主任） | `--card-id`, `--task-code`, `--class-id` |
| `card finish-info` | 查询打卡详情及完成进度 | `--card-id`, `--card-biz-id` |

> `card list --status`: FINISH(已完结) / UNFINISH(进行中)
> `card finish-info --target-role`: teacher / headmaster / guardian / student，未传时按 uid 真实身份自动推断
> `card finish-info --student-id`: 当 targetRole 为 guardian 时，用于指定查看某个孩子的进度

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

> 作业正文用 `--hw-content`（不是 `--content`）；`--hw-title` 为可选标题
> `homework submit` 与 `homework create-comment` 定位到具体作业内容用 `--hw-content-detail-id`

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

其余命令均为读或普通写操作，不需要 `--yes`。

## 意图判断

用户说"消息/消息摘要" → message summary-list
用户说"家校任务/待办任务" → task 子命令
用户说"作业" → homework 子命令（发布→create，查详情→get，批改评语→create-comment，提交→submit，删除→delete + `--yes`）
用户说"成绩/成绩单" → report 子命令
用户说"通知" → notice 子命令（发通知→create，查详情→get，签收/确认→confirm，查签收情况→confirm-status，删除→delete + `--yes`）
用户说"奖状/表彰/颁奖" → diploma 子命令（颁发→create，查详情→get，阅读统计→statistics，删除→delete + `--yes`）
用户说"班级圈/成长记录/学生动态" → circle posts
用户说"打卡/打卡任务/打卡完成情况/卡片完成情况" → card 子命令

关键区分: homework(作业，独立命令组) vs task(家校任务聚合列表，含作业/打卡/通知/奖状等来源)
关键区分: circle(班级圈动态/成长记录) vs message(AI消息总结)
关键区分: diploma(奖状/表彰) vs report(成绩单)
老师视角用 `list-by-teacher`，学生/家长视角用 `list-by-student`，homework / notice / diploma 三组同构。

## 核心工作流

### 老师场景
1. 查看发布的任务 → `task publish-list --need-statistic -f json`
2. 查看某班全部任务 → `task all-list --biz-id <classId>`
3. 查看成绩单 → `report by-teacher --status 1`
4. 查看班级成绩明细 → `report by-class --report-id <id> --class-id <classId>`
5. 查看某班打卡完成情况 → `card user-statistic --card-id <cardId> --task-code <taskCode> --class-id <classId> --finish`
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
5. 查看孩子进行中打卡 → `card list --status UNFINISH`
6. 查看孩子作业列表 → `homework list-by-student --student-id <uid> --class-id <classId> --user-name <家长姓名>`
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
| `report by-teacher` | `schoolReportId` | report get/by-class/by-student-detail 的 --report-id |
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
