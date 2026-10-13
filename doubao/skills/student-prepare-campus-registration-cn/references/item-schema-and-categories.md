# 报到事项字段与分类

## 原子事项原则

一个事项只描述一个可完成动作。例如把“登录迎新系统、上传照片并缴费”拆成三个事项。每项必须能独立判断“完成、待办或不适用”。

## 阶段

- `before_arrival`：到校前；
- `arrival_day`：报到当天；
- `first_week`：入校首周；
- `after_registration`：报到后续；
- `unknown`：阶段尚未确认。

## 分类

- `admission_identity`：录取与身份核验；
- `online_onboarding`：迎新系统、账号激活、信息确认；
- `fees_and_payment`：学费、住宿费和其他明确费用；
- `documents_and_copies`：材料原件、复印件和照片；
- `student_records`：纸质或电子档案；
- `party_youth_relation`：党团组织关系；
- `residence_and_hukou`：户口迁移或居住登记；
- `financial_aid`：助学贷款、绿色通道和困难认定；
- `dormitory_checkin`：宿舍入住；
- `health_and_training`：体检、军训和保险告知；
- `campus_services`：校园卡、网络、图书馆等；
- `other`：无法归入上述类别的报到事项。

## 事项字段

每个事项使用以下字段：

- `id`：唯一、稳定、只含字母数字下划线或连字符；
- `title`：动词开头的短标题；
- `category`、`stage`；
- `requirement`：`required`、`conditional` 或 `recommended`；
- `evidence_status`：`confirmed`、`user_provided`、`to_verify` 或 `not_applicable`；
- `applies_to`：适用对象，未知时写“待确认”；
- `deadline`：年份为 2000-2100 的 ISO 8601 日期/时间或 `null`；
- `location`：地点或 `null`；
- `materials`：材料名称数组，不含证件号码；
- `actions`：按顺序排列的动作数组；
- `prerequisites`：前置条件数组；
- `completion_evidence`：完成后可核对的回执、状态或实物；
- `fallback`：失败或错过后的官方咨询/补救路径；
- `source_ids`：来源编号数组；
- `notes`：限制、冲突和原文保留说明；
- `risk_level`：`low`、`medium` 或 `high`。

## 关键规则

- `confirmed` 必须引用至少一个 `official: true` 且 `scope_context` 与当前任务相符的来源。
- 联网来源只有在 `access_method: public_web`、`authorization_status: authorized`、`retrieved_at` 有值且运行时 Tool 为 `available_authorized` 时才能支持 `confirmed`。用户提供或离线来源不得伪装成联网核验。
- 已确认的日期、地点或费用必须来自适用范围匹配的官方来源。
- 同阶段事项按截止时间的绝对时刻排序；带偏移量的时间统一换算为 UTC，无偏移量时按 `context.timezone` 解释。
- `required` 且状态不是 `not_applicable` 的事项，必须填写动作、完成证据和失败备选。
- `conditional` 必须说明条件；条件未知时状态只能为 `to_verify`。
- 只有材料名称可以进入 `materials`，禁止放入个人号码或账户数据。
- 多个事项引用同一来源是允许的，但每个事项仍要独立说明适用对象。

## 材料总表生成规则

从所有适用事项中合并同名材料，保留用途和份数原文。来源未写份数时，不自行补成“一份”或“多份”；显示“份数待确认”。原件与复印件必须分别记录。
