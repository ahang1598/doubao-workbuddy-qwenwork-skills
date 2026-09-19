---
name: zhihuishu-teacher-query-skill
description: 智慧树教师端教学查询技能，可靠编排课程、班级、学生标签、分组方案、成绩和作业等只读 MCP 工具
description_zh: 智慧树教师端教学查询技能，可靠编排课程、班级、学生标签、分组方案、成绩和作业等只读 MCP 工具
description_en: Read-only Zhihuishu teacher queries for courses, classes, student tags, group plans, grades, and assignments with reliable MCP tool orchestration.
version: "1.0.4"
author: "智慧树"
---

# 智慧树教师查询 Skill

使用智慧树 Connector 提供的 MCP 工具，查询当前已授权教师自己的教学数据。

## 能力边界

仅执行以下只读查询：

- 当前业务用户和服务状态
- 教师授课课程及课程详情
- 教师管理的班级及学生明细
- 指定学生当前拥有的标签
- 课程分组方案列表
- 班级多维成绩
- 课程作业及完成统计

不要执行或承诺创建、编辑、删除、发布、批改、催交、打标、调组、成绩录入、权重设置、导入或导出。这些能力当前未由 Connector 提供。用户请求未支持的操作时，明确说明当前只支持查询，并指出可查询的相关信息。

## 核心规则

1. **身份只来自 OAuth**：不要询问或传递 `userNid`、`schoolId`、业务 Token、Authorization code 等身份凭证。服务端根据当前 Connector 授权确定用户和学校。
2. **先定位资源再查业务**：需要 `courseId` 时先调用 `search_my_courses`；需要 `classId` 时再调用 `search_my_classes`。不要猜测、拼接或复用其他用户的 ID。
3. **保持学期一致**：一次请求链路中的课程、班级、成绩、作业、标签和分组必须使用同一个 `term`。优先复用 `search_my_courses` 返回的 `term`，不要在中途切换学期。
4. **学期字段禁止推导**：后续调用必须逐字复用工具返回的 `term`，面向用户默认展示工具返回的 `termName`。只有用户询问学期编号或编号有助于消歧时才展示 `term`；一旦展示，必须复制原值，禁止根据自然年份推导、改写或“纠正”。若工具只返回其中一个，不补算另一个。例如工具返回 `term=20271`、`termName=2026年秋冬学期` 时，可以只写“2026年秋冬学期”；若同时展示编号，只能写成“2026年秋冬学期（20271）”，绝不能改成“2026年秋冬学期（20261）”。
5. **当前学期可省略**：用户说“当前”“本学期”且工具允许省略 `term` 时不要自行计算，交给服务端选择当前学期。下游工具强制要求 `term` 时，使用前序工具返回值。
6. **不能静默消歧**：同名课程、多个班级、同名学生或多个自定义考核项都必须让用户选择，除非用户已经提供足以唯一定位的条件。
7. **只使用实际可见结果**：宿主提供 `structuredContent` 时以其为事实来源；宿主只提供文本结果时，只使用文本中明确出现的字段。不要假定自己能读取未显示的结构化字段，也不要补造缺失数据或把空值解释为 0。
8. **成绩禁止重算**：直接展示 `query_class_scores` 返回的成绩和数据截止时间，不自行重算总成绩、权重、排名、平均分或及格率。
9. **最小化调用**：已有唯一 `courseId`、`classId`、`studentId` 或 `assessmentId` 时直接复用，不重复查询。不要为了“确认身份”在每次请求前调用 `get_current_business_user`。
10. **保护内部标识**：普通回答不展示内部 ID。只有需要用户从候选项中选择时，才保留 ID 供下一次工具调用使用；面向用户优先展示名称、学号、班级和学期。
11. **缺少串联 ID 时立即熔断**：前置工具的实际可见结果没有提供下游必填的 `courseId`、`classId`、`studentId` 或 `assessmentId` 时，停止调用并说明 Connector 结果缺少必要的串联字段。禁止把名称填入 ID 参数，禁止枚举或猜测数字、字符串和常见 ID，禁止并发探测候选 ID，也禁止调用其他工具旁路验证猜测。

## 标准调用流程

1. 从用户请求提取业务意图、课程、学期、班级、学生、成绩维度、作业名称和时间范围。
2. 如果请求仅涉及当前用户或连接状态，调用 `get_current_business_user`。
3. 如果业务工具需要课程，调用 `search_my_courses` 定位课程并取得 `courseId` 和 `term`。
4. 如果业务工具需要班级，调用 `search_my_classes` 定位班级并取得 `classId`。
5. 调用目标业务工具前，确认其所有必填 ID 都明确存在于实际可见的前序结果中；缺少任一 ID 时按熔断规则停止。
6. 调用目标业务工具，并复用同一链路已经确认的资源 ID 和 `term`。
7. 若返回 `needs_selection`，仅在结果同时提供候选 ID 时展示有辨识度的信息并等待用户选择；候选 ID 不可见时按熔断规则停止。
8. 使用清晰的列表或表格呈现结果，同时说明学期、筛选条件、数据截止时间和分页情况。

## 意图路由

| 用户意图 | 目标工具 | 必要的前置工具 |
|---|---|---|
| 我是谁、连接是否正常 | `get_current_business_user` | 无 |
| 我教哪些课、按名称找课程 | `search_my_courses` | 无 |
| 查看某门课程简介或基本信息 | `get_my_course_detail` | `search_my_courses` |
| 查询课程班级、学生人数或学生明细 | `search_my_classes` | `search_my_courses` |
| 查询某名学生的标签 | `query_student_tags` | `search_my_courses`，必要时 `search_my_classes` |
| 查询课程分组方案 | `list_group_plans` | `search_my_courses` |
| 查询总成绩、考勤、平时、作业、考试或考核项成绩 | `query_class_scores` | `search_my_courses` → `search_my_classes` |
| 查询课程作业、截止时间或完成情况 | `search_course_homework` | `search_my_courses` |

## 可用工具

### `get_current_business_user` - 获取当前业务用户

仅用于用户询问当前身份、连接状态，或其他工具明确返回身份无效时的诊断。不要在普通查询前例行调用。

无参数。返回当前 OAuth Bearer Token 对应的教师显示名和业务服务状态。

### `search_my_courses` - 查询我的课程

查询当前教师自己的授课课程，也是其他课程相关工具的资源入口。

| 参数 | 类型 | 必填 | 说明 |
|---|---|:---:|---|
| `term` | integer | 否 | 五位学期编号；省略时查询当前学期 |
| `courseName` | string | 否 | 课程名称关键词，最长 100 字符，支持模糊查询 |
| `pageNum` | integer | 否 | 页码，从 1 开始，默认 1 |
| `pageSize` | integer | 否 | 每页数量，1-50，默认 20 |

处理规则：

- 用户只说“我的课程”时，不传 `courseName`。
- 用户指定课程名称时传入原始关键词，不擅自改写课程名。
- 回答中的学期名称使用结果顶层的 `termName`；需要展示学期编号时复制顶层的 `term`，不要从课程项、当前日期或编码规则反推。
- 结果有多个课程时，按课程名、课程类型、学期等可见字段列出候选，让用户选择。
- 需要遍历全部课程时，根据返回的 `pageNum`、`pages` 和 `total` 逐页查询；普通请求不要无条件拉取全部分页。
- 后续工具必须复用所选课程的 `courseId` 和结果中的 `term`。
- 课程结果没有实际提供 `courseId` 时，不调用课程详情、班级、标签、分组、成绩或作业工具；不要把课程名称当作 `courseId`，也不要测试猜测的 ID。

### `get_my_course_detail` - 查看我的课程详情

查看当前教师有权访问的一门课程的基本信息。

| 参数 | 类型 | 必填 | 说明 |
|---|---|:---:|---|
| `courseId` | string | 是 | 从 `search_my_courses` 结果取得 |
| `term` | integer | 否 | 五位学期编号；优先复用课程查询返回值 |

返回可能包含课程类型、课程层次、学时、学科、分类、简介和封面。字段缺失时省略，不写“无”或猜测内容。

### `search_my_classes` - 查询教师管理的班级

查询指定课程的班级、学生数量和学生明细，可用于定位后续成绩查询所需的 `classId`。

| 参数 | 类型 | 必填 | 说明 |
|---|---|:---:|---|
| `courseId` | string | 是 | 从 `search_my_courses` 结果取得 |
| `term` | integer | 否 | 五位学期编号；省略时查询当前学期 |
| `className` | string | 否 | 班级名称关键词，支持子串匹配 |
| `studentName` | string | 否 | 学生姓名关键词，支持子串匹配 |
| `studentNo` | string | 否 | 学号关键词，支持子串匹配 |

处理规则：

- 用户查询课程下所有班级时只传 `courseId` 和已确认的 `term`。
- 查询学生时优先传用户给出的姓名或学号，不要把姓名猜成学号。
- 多个班级满足条件且后续工具需要唯一 `classId` 时，让用户选择班级。
- 不使用本工具创建、修改、导出班级或调整班级成员。

### `query_student_tags` - 查询学生标签

查询指定课程和学期内某名已入班学生当前拥有的标签。

| 参数 | 类型 | 必填 | 说明 |
|---|---|:---:|---|
| `courseId` | string | 是 | 从 `search_my_courses` 结果取得 |
| `term` | integer | 是 | 已确认的五位学期编号 |
| `studentName` | string | 条件必填 | 未提供学生 ID 时必填 |
| `classId` | string | 条件必填 | 从候选项取得，必须与 `studentId` 同时传入 |
| `studentId` | string | 条件必填 | 从候选项取得，必须与 `classId` 同时传入 |

处理规则：

- 第一次调用通常传 `courseId`、`term` 和 `studentName`。
- 返回 `needs_selection` 时，按学生姓名、学号、班级展示 `candidates`，让用户选择。
- 用户选择后，从候选项取出匹配的 `classId` 和 `studentId` 再次调用；两者不可只传一个。
- `tags` 为空时说明“该学生当前暂无标签”，不要误报为查询失败。
- 不查询课程标签全集，也不创建、修改、删除标签或给学生打标。

### `list_group_plans` - 查询分组方案列表

查询指定课程和学期下的分组方案列表。

| 参数 | 类型 | 必填 | 说明 |
|---|---|:---:|---|
| `courseId` | string | 是 | 从 `search_my_courses` 结果取得 |
| `term` | integer | 是 | 已确认的五位学期编号 |
| `keyword` | string | 否 | 分组方案名称关键词，支持模糊搜索 |

结果可展示方案名称、分组方式、组数、学生数、关联作业数和截止日期。当前仅支持列表，不查询方案详情、组内成员或未进组学生，也不创建、编辑或删除分组。

### `query_class_scores` - 查询教师多维成绩

查询指定课程、班级和学期的一个成绩维度。

| 参数 | 类型 | 必填 | 说明 |
|---|---|:---:|---|
| `dimension` | string | 是 | `total`、`attendance`、`usual`、`homework`、`exam` 或 `assessment` |
| `courseId` | string | 是 | 从 `search_my_courses` 结果取得 |
| `classId` | string | 是 | 从 `search_my_classes` 结果取得 |
| `term` | integer | 是 | 已确认的五位学期编号 |
| `studentId` | string | 否 | 仅查询单个学生平时成绩详情时使用 |
| `assessmentId` | string | 条件必填 | 查询多个自定义考核项中的一个时使用 |
| `keyword` | string | 否 | 学生姓名或学号关键词 |
| `pageNum` | integer | 否 | 页码，从 1 开始，默认 1 |
| `pageSize` | integer | 否 | 每页数量，1-1000，默认 50 |
| `sortType` | integer | 否 | 考勤、作业、考试、考核项排序；`0` 默认，`1` 倒序 |
| `studentNoSortType` | integer | 否 | 平时成绩按学号排序；`0` 默认，`1` 倒序 |
| `studyProgressSortType` | integer | 否 | 平时成绩按学习进度排序；`0` 默认，`1` 倒序 |
| `interactionCountSortType` | integer | 否 | 平时成绩按互动次数排序；`0` 默认，`1` 倒序 |
| `interactionTotalScoreSortType` | integer | 否 | 平时成绩按互动总分排序；`0` 默认，`1` 倒序 |

成绩维度映射：

| 用户表达 | `dimension` |
|---|---|
| 总成绩、综合成绩 | `total` |
| 考勤成绩、出勤 | `attendance` |
| 平时成绩、学习进度、互动 | `usual` |
| 作业成绩 | `homework` |
| 考试成绩 | `exam` |
| 自定义考核项、考核成绩 | `assessment` |

处理规则：

- 用户没有说明成绩维度时，先询问需要查询哪一种，不默认使用 `total`。
- 查询单个学生时可先用 `search_my_classes` 定位学生；只有 `usual` 维度支持通过 `studentId` 查询平时成绩详情。
- `dimension=assessment` 返回 `needs_selection` 时，展示 `assessmentCandidates` 中的考核项名称、分值和类型，让用户选择后携带 `assessmentId` 再次调用。
- 原样使用返回的 `data` 和 `dataCutoffTime`。不要跨维度合并后重新计算成绩。

### `search_course_homework` - 查询教师课程作业

查询指定课程和学期的作业列表、配置、关联班级、截止时间及完成统计。

| 参数 | 类型 | 必填 | 说明 |
|---|---|:---:|---|
| `courseId` | string | 是 | 从 `search_my_courses` 结果取得 |
| `term` | integer | 是 | 已确认的五位学期编号 |
| `homeworkName` | string | 否 | 作业名称关键词 |
| `className` | string | 否 | 班级名称关键词 |
| `createStart` | string | 否 | 创建时间范围开始，格式 `yyyy-MM-dd HH:mm:ss` |
| `createEnd` | string | 否 | 创建时间范围结束，格式 `yyyy-MM-dd HH:mm:ss` |
| `updateStart` | string | 否 | 更新时间范围开始，格式 `yyyy-MM-dd HH:mm:ss` |
| `updateEnd` | string | 否 | 更新时间范围结束，格式 `yyyy-MM-dd HH:mm:ss` |
| `endStart` | string | 否 | 截止时间范围开始，格式 `yyyy-MM-dd HH:mm:ss` |
| `endEnd` | string | 否 | 截止时间范围结束，格式 `yyyy-MM-dd HH:mm:ss` |

处理规则：

- “最近创建”使用 `createStart/createEnd`，“最近更新”使用 `updateStart/updateEnd`，“即将截止”使用 `endStart/endEnd`，不要混用时间字段。
- 时间条件必须能转换为明确的本地时间边界；用户表达有歧义时先询问，不擅自扩大范围。
- 返回为空时说明当前筛选条件下没有相关作业。
- 不批改、提交、发布、打回、催交、编辑、创建或导出作业。

## 消歧与连续调用

### 同名课程

调用 `search_my_courses` 后，如果多个结果都匹配，列出课程名、课程类型和学期等可见差异。等待用户选择，不要按返回顺序默认选第一项。

### 多个班级

调用 `search_my_classes` 后，如果成绩查询等后续动作需要唯一班级，列出班级名和学生数等差异。用户说“所有班级”时可以逐班查询，但要控制调用数量并分别标注结果。

### 同名学生

遵循 `query_student_tags` 的 `needs_selection` 流程。不要仅凭姓名选择学生，优先展示学号和班级帮助用户判断。

### 多个自定义考核项

遵循 `query_class_scores` 的 `needs_selection` 流程。不要合并不同考核项，也不要猜测用户想查哪一项。

## 认证与错误处理

- Connector 使用 OAuth 授权。不要要求用户粘贴 Token、authorization code、refresh token 或其他凭证。
- 仅当 MCP 连接本身不可用、MCP 返回 401、Connector 明确断开，或多个工具均表明 access token/当前业务用户无效时，才提示用户在 WorkBuddy 中重新连接智慧树 Connector。
- 若同一会话中其他工具刚刚成功，只有某个业务接口返回“拒绝访问”“未登录”或类似文案，不要断言 Connector OAuth 已失效，也不要要求用户重新授权。说明该业务接口未通过服务端凭证或登录态校验，停止调用并建议由 Connector 服务方检查接口鉴权。
- 批量查询多个班级或学生时按项顺序调用；第一项出现认证、权限或业务登录态错误后立即停止剩余调用，不要并发制造重复失败。用户明确要求重试时最多重试一次；相同错误再次出现后停止。
- 出现“当前授权不包含课程查询权限”等 scope 错误时，原样说明缺少权限并建议重新授权，不要改用其他工具绕过权限。
- 业务服务无响应、超时或暂时不可用时，说明查询未完成并建议稍后重试。不要把错误解释为空数据，也不要无限重试。
- 参数错误时修正可从上下文确定的参数；如果缺少课程、班级、学生、学期或成绩维度等关键选择，向用户询问。
- 工具结果缺少下一步必填 ID 时，说明 Connector 暂未返回继续查询所需的关联字段并停止。不要要求用户提供本应由 Connector 返回的内部 ID，也不要通过试错探测。

## 输出规范

- 开头直接给出查询结论，不描述内部调用过程。
- 列表类结果优先使用简洁表格；字段较少或只有一项时使用列表。
- 默认展示工具返回的 `termName`。用户询问学期编号或编号有助于消歧时，按“`termName`（`term`）”原样展示；不自行推导缺失字段。
- 明确标注实际筛选条件、总数、页码和 `dataCutoffTime`（若返回）。
- 课程、班级、学生、作业、考核项名称以及学期字段保持业务系统原文。
- 不展示 Token、授权码、请求头、`userNid` 等敏感或内部身份信息。
- 不把“未返回”“空值”“接口异常”表述为 0 或“不存在”。

## 示例

### 查询课程详情

用户：“查看茶艺鉴赏的课程详情。”

1. 调用 `search_my_courses(courseName="茶艺鉴赏")`。
2. 唯一匹配时取 `courseId` 和 `term`；多个匹配时先让用户选择。
3. 调用 `get_my_course_detail(courseId=..., term=...)`。

### 查询班级总成绩

用户：“查一下数据结构本学期 1 班的总成绩。”

1. 调用 `search_my_courses(courseName="数据结构")`。
2. 调用 `search_my_classes(courseId=..., term=..., className="1班")`。
3. 唯一匹配后调用 `query_class_scores(dimension="total", courseId=..., classId=..., term=...)`。
4. 展示业务返回成绩和数据截止时间，不重新计算总成绩。

### 查询学生标签

用户：“王明在大学英语这门课有什么标签？”

1. 调用 `search_my_courses(courseName="大学英语")`。
2. 调用 `query_student_tags(courseId=..., term=..., studentName="王明")`。
3. 若返回多个候选，让用户根据学号和班级选择，再携带对应 `classId`、`studentId` 调用一次。

### 查询即将截止的作业

用户：“高等数学未来七天有哪些作业截止？”

1. 调用 `search_my_courses(courseName="高等数学")`。
2. 按当前时区计算明确的七天起止时间。
3. 调用 `search_course_homework(courseId=..., term=..., endStart=..., endEnd=...)`。
4. 按截止时间展示作业、关联班级和完成统计。
