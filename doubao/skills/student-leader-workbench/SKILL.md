---
name: student-leader-workbench
description: "当用户请求班级、社团或学生会的执行产物时，使用本技能；包括通知、活动方案、花名册、会议纪要、任务表、跟进安排或学生干部工作台。"
---

# 学生干部工作台

## 概述
把学生干部高频事务从临场写作变成可复用的组织协作 SOP，尤其适合班级、团支部、社团、学生会等轻量组织。

本技能是面向学生场景的标准化交付工作流，旨在帮助后续智能体准确路由、补问缺失信息、仅加载所需参考资料、产出具体交付物，并在最终交付前完成质量校验。
## 使用场景
- 当用户的请求匹配本技能标题、同义场景或下方 `适用场景` 中的触发词时调用。
- 只处理本技能原有能力、交付产物和个性化输出结构；相邻任务按 `不适用场景` 和 `路由决策` 转交。
- 信息不足时先追问或显式标注假设，不能为了补齐成品而编造学校政策、官方节点、个人经历或结果承诺。
## 适用场景
- 用户要处理班级、团支部、社团、学生会的通知、活动策划、分工、排班、会议纪要、催办和复盘。
- 用户给出群聊、名单、预算、志愿者时间、活动要求，需要整理成可执行台账。
- 用户要可直接发群的公告、报名表字段、主持稿、会后纪要、待办清单或催办话术。
- 输入里出现“班委/团支书/社团/学生会”“活动安排”“排班”“纪要”“通知”“谁负责”等触发词。
## 不适用场景
- 只要公众号/小红书/社群增长运营，转 `campus-content-operator`。
- 只要海报封面、视觉需求说明 或尺寸清单，转 `campus-poster-cover-generator`。
- 只要校园办事流程、材料、办公室和咨询话术，转 `campus-service-navigator`。
- 涉及法律、财务、学校官方审批结论时，只能列风险和待确认项，不给最终官方判断。
## Routing Decision
1. 先看最终交付物是否是组织执行物：通知、策划、排班、纪要、催办、复盘属于本 skill。
2. 如果用户同时要“活动执行 + 推文 + 海报”，本 skill 负责执行台账和通知，推文/海报分别交给对应 skill。
3. 如果任务主要是找学校部门办手续，转校园办事 skill；本 skill 只处理组织内部协作。
4. 如果输入事实互相冲突，必须先做事实/冲突台账，不能直接生成最终通知。

## Execution Structure
1. 事务判定：通知、活动、排班、纪要、复盘或多项组合。
2. 事实台账：确认对象、时间、地点、人数、预算、负责人、限制、缺失和冲突。
3. 执行设计：输出负责人、截止时间、交付物、确认方式四列执行表。
4. 风险约束：检查容量、审批、安全、无障碍、隐私、预算、雨天备用。
5. 明细保真：涉及评分、名单、补录、奖助、考核、违规台账时，先给逐人/逐项原始明细追溯表，再给分类汇总。
6. 发布物：给可直接发送的群公告、报名字段、纪要模板或催办话术。
7. 闭环自检：每项任务有状态、验收标准和下一步跟进。

## Required Inputs
- 组织类型、活动或事务背景
- 对象人群、时间地点、负责人
- 已有群聊记录、会议纪要、名单或表格
- 学校/学院格式要求、语气要求

## Output Contract
- 通知/群公告
- 活动策划案
- 排班表/分工表
- 会议纪要
- 执行清单与催办话术

Every answer must include a finished artifact, missing facts if any, and a compact self-check. For tables or plans, include owners, dates, status, or acceptance criteria whenever the task implies execution.

## 核心流程
1. 判定是否匹配本 Skill 的使用场景、输出合同和不适用边界。
2. 抽取用户已给事实，列出缺失、冲突、不可验证或需要学校/本人确认的信息。
3. 按 `Progressive Disclosure` 读取必要 references，不加载无关资料。
4. 生成可直接使用的交付产物，并保留本 Skill 的领域化结构、语气和个性化要求。
5. 做安全合规、事实完整性、转交边界和可执行性自检后再交付。

## Core Workflow
1. 先判定任务类型：通知、活动、排班、会议纪要、复盘总结或多项组合。
2. 抽取关键事实并标记缺口；缺少时间、地点、对象、负责人、截止时间时先向用户确认。
3. 按场景读取 references 中对应模板，生成可直接发布或执行的版本。
4. 涉及多人分工时，必须输出负责人、截止时间、交付物、确认方式四列。
5. 输出前检查称谓、时间、地点、报名方式、风险提示和隐私信息是否完整。

## Complex Task Hard Pattern
When a request combines 2+ of: event planning, notice, roster, budget, venue, guest logistics, risk, meeting minutes, or follow-up, do **not** answer with only prose. Produce an "执行作战台" with these blocks:

1. `事实/冲突台账`: list confirmed facts, conflicting facts, missing facts, and who must confirm each item. Explicitly catch relative-date conflicts such as "10 天后" vs a named date.
2. `约束校验`: capacity, budget, time limit, accessibility, approval, privacy, venue, food, and safety constraints. Mark pass/risk/fail.
3. `四列分工表`: every task row must include 负责人, 截止时间, 交付物, 确认方式. Do not rename or omit these four columns.
4. `排班/公平性检查`: for volunteer schedules, state constraints used, maximum continuous duty, conflicts, and unresolved gaps.
5. `发布物`: include final notice/copy if the user needs to send something.
6. `会后闭环`: minutes template, attendance/evidence collection, follow-up message, and review metrics.

If the user asks for a quick version, keep these blocks but compress rows; never drop conflict, constraint, or confirmation columns.

## Progressive Disclosure
- Read `references/trigger-boundaries.md` when the request is ambiguous or near another campus skill.
- Read `references/workflow-playbook.md` before generating the main artifact.
- Read `references/output-contracts.md` before finalizing a structured deliverable.
- Read `references/compliance-and-safety.md` when the request touches policy, personal data, claims, applications, recruiting, exams, or official procedures.
- Use `scripts/validate_request.py` to check required facts from a JSON request when the task has many fields.
- Use `scripts/render_checklist.py` to turn output requirements into a final review checklist.

## Hard Gates
- Never invent school policies, official deadlines, awards, grades, job postings, exam questions, authorizations, or personal achievements.
- If an input is required for correctness and is missing, ask a concise follow-up or mark the output as a draft with a visible assumption.
- If the user requests cheating, fabrication, bypassing procedures, impersonation, or guaranteed outcomes, refuse that part and offer a compliant alternative.
- Before final response, verify: trigger fit, input completeness, output contract, safety boundary, and usability.


## Revision Integrity
- Treat this source ZIP as the source of truth. Do not append platform-only repair notes, descriptions, or sections unless the same content is also present in this package.
- After uploading to Action Hub, verify that the platform name, description, visible body, and source version correspond to this ZIP before treating QC evidence as valid.
- This skill is a text workflow and does not require a bound Tool unless a future version explicitly adds one. If platform evidence does not expose Tool bindings, report that as missing platform evidence rather than inventing a Tool relationship.

## Verification
Run these commands from the Skill root after any source change:

```bash
python3 tests/run_contract_tests.py
python3 scripts/validate_request.py < sample_request.json
```

`tests/run_contract_tests.py` executes the validator help contract, the complete sample request, the missing-field fixture, malformed JSON, and routing-case presence check. It is the repeatable evidence for the source package. Action Hub Tool binding or full target-App routing evidence remains platform evidence and must be checked outside this ZIP when the platform exposes it.
