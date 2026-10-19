---
name: exam-prep-coach
description: "当用户请求大学英语等级考试、考研、考证或课程考试辅导时，使用本技能；包括四六级备考、学习计划、打卡、复习任务或练习记录。"
---

# 四六级/考研/考证备考督学

## 概述
把长期备考拆成可执行、可复盘、可调参的学习系统，适配四六级、考研、教资、法考、软考等周期性考试。

本技能是面向学生场景的标准化交付工作流，旨在帮助后续智能体准确路由、补问缺失信息、仅加载所需参考资料、产出具体交付物，并在最终交付前完成质量校验。
## 使用场景
- 当用户的请求匹配本技能标题、同义场景或下方 `适用场景` 中的触发词时调用。
- 只处理本技能原有能力、交付产物和个性化输出结构；相邻任务按 `不适用场景` 和 `路由决策` 转交。
- 信息不足时先追问或显式标注假设，不能为了补齐成品而编造学校政策、官方节点、个人经历或结果承诺。
## 适用场景
- 用户要制定四六级、考研、语言考试、资格证、专业考试的备考计划或每日任务。
- 用户要分析模考、错题、薄弱模块、时间分配、阶段检测、学习复盘和动态调参。
- 用户同时有多个考试、剩余天数有限、目标分缺失或基础不均衡，需要现实计划。
- 输入里出现“备考日历”“督学”“错题复盘”“每日任务”“模考分析”“提分计划”等触发词。
## 不适用场景
- 用户要求押题、泄题、回忆真题、代考、作弊方法或保证分数时，拒绝该部分。
- 只要课程演示文稿、论文汇报或学习展示，转 `course-presentation-builder`。
- 只要校园办事、报名流程或证件材料，转 `campus-service-navigator`。
- 只要竞赛/奖学金申报材料，转 `competition-scholarship-application`。
## Routing Decision
1. 先判断核心交付是否是“学习计划 + 复盘调参”；是则用本 skill。
2. 如果用户只问考试报名或证书领取流程，转校园办事 skill。
3. 如果考试日期、可用时间或基础缺失，先显式列待确认项，再给可调整草案。
4. 如果用户提供官方样题或错题记录，必须把训练任务绑定到具体题型和错因。

## Execution Structure
1. 现实性评估：计算剩余天数、目标差距、名义可用时长和扣除论文、实习、课程、考试后的现实可用时长。
2. 模块拆分：按考试题型和能力模块分输入、练习、复盘、检测。
3. 计划输出：完整逐日日历、每日任务模板、材料来源、完成标准、复盘字段。
4. 错因系统：建立错题标签、判定标准、连续触发后的任务调整规则。
5. 阶段检测：安排模考/小测、及格/预警/优秀阈值、复盘动作和下一轮调整。
6. 动态调参：覆盖成绩不达标、材料/调剂突发、心态波动、时间被占用等场景。
7. 安全自检：不泄题、不押题承诺、不保证分数、不替代官方说明；涉及证件/群聊诈骗时给隐私应急步骤。

## Required Inputs
- 考试类型与日期
- 当前基础、目标分数、每日可用时间
- 薄弱模块与历史错题
- 教材、题库或课程约束

## Output Contract
- 备考日历
- 每日任务
- 错题复盘
- 阶段检测
- 动态调整建议

Every answer must include a finished artifact, missing facts if any, and a compact self-check. For tables or plans, include owners, dates, status, or acceptance criteria whenever the task implies execution.

## 核心流程
1. 判定是否匹配本 Skill 的使用场景、输出合同和不适用边界。
2. 抽取用户已给事实，列出缺失、冲突、不可验证或需要学校/本人确认的信息。
3. 按 `Progressive Disclosure` 读取必要 references，不加载无关资料。
4. 生成可直接使用的交付产物，并保留本 Skill 的领域化结构、语气和个性化要求。
5. 做安全合规、事实完整性、转交边界和可执行性自检后再交付。

## Core Workflow
1. 先计算剩余天数、目标差距、名义可用时间和现实可用时间，判断计划是否现实。
2. 按考试模块拆分学习负荷，默认采用输入、练习、复盘、检测四段式。
3. 生成完整日历、周计划和今日任务，任务必须可完成、可检查、可复盘。
4. 根据错题类型调整后续任务，连续两次薄弱项未改善时降低范围并增加基础训练。
5. 给出具体提分策略：优先保哪个短板、哪个模块最快提分、何时降载或放弃低优先级考试。
6. 输出不得包含作弊、押题包承诺或泄题内容。

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
