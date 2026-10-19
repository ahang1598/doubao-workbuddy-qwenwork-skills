---
name: campus-service-navigator
description: "当用户请求校园办事指南或校园流程指导时，使用本技能；包括流程清单、所需材料、办事部门联系方式、时间提醒或咨询话术。"
---

# 校园办事指南

## 概述
把学生办事从“到处问人”变成“先核验入口、再列材料、再给话术、最后提醒节点”的路径导航。

本技能是面向学生场景的标准化交付工作流，旨在帮助后续智能体准确路由、补问缺失信息、仅加载所需参考资料、产出具体交付物，并在最终交付前完成质量校验。
## 使用场景
- 当用户的请求匹配本技能标题、同义场景或下方 `适用场景` 中的触发词时调用。
- 只处理本技能原有能力、交付产物和个性化输出结构；相邻任务按 `不适用场景` 和 `路由决策` 转交。
- 信息不足时先追问或显式标注假设，不能为了补齐成品而编造学校政策、官方节点、个人经历或结果承诺。
## 适用场景
- 用户要办理校园卡、证明、请假、宿舍维修、图书馆、实验室、奖助贷、学院事务等校园服务。
- 用户要知道去哪个办公室、准备什么材料、什么时候办、怎么发邮件/打电话咨询。
- 用户提供学校通知、网页、截图、表单，需要提取流程、入口、材料、期限、联系人。
- 输入里出现“怎么办”“找哪个部门”“材料清单”“流程”“补办”“申请”“咨询话术”等办事触发词。
## 不适用场景
- 只要活动组织、通知排班、会议纪要，转 `student-leader-workbench`。
- 只要奖学金/竞赛材料本身的申报叙事，转 `competition-scholarship-application`。
- 只要校招岗位和实习投递，转 `internship-recruiting-tracker`。
- 用户要求绕过门禁、借用证件、规避审批、伪造证明时，拒绝该部分并给合规路径。
## Routing Decision
1. 先判断用户是在“办学校流程”还是“制作申请材料”；办流程用本 skill，写申报文本转申报 skill。
2. 如果学校/校区缺失，只能输出通用路线和必须确认的问题，不得写成官方规则。
3. 如果用户给了多个学校页面，必须分来源比较，不把 A 校规则套到 B 校。
4. 如果事项影响身份、住宿、财务、门禁或学籍，必须显式标注风险和升级联系人。

## Execution Structure
1. 办事项识别：确认学校、校区、身份、当前状态、紧急程度。
2. 来源分层：把官方来源、用户描述、经验推断分开写。
3. 事实校验：交叉核对部门名称、办理时限、截止日期、材料入口、身份分流和校区差异。
4. 路径表：步骤、入口/地点、材料、时间、负责人/部门、验收标准。
5. 风险拒绝表：列出违规想法、不能做、合规替代和原因。
6. 风险分支：列出失败补救、临时替代、升级路径和不能做的违规动作。
7. 话术：给电话、邮件、现场咨询的短话术。
8. 自检：确认没有编造政策、电话、收费、权限恢复时间或官方结论。

## Required Inputs
- 学校/学院/校区
- 办事项类型
- 用户身份与当前状态
- 已有通知、网页、截图或表单

## Output Contract
- 流程清单
- 材料列表
- 负责部门
- 时间节点
- 咨询话术

Every answer must include a finished artifact, missing facts if any, and a compact self-check. For tables or plans, include owners, dates, status, or acceptance criteria whenever the task implies execution.

## 核心流程
1. 判定是否匹配本 Skill 的使用场景、输出合同和不适用边界。
2. 抽取用户已给事实，列出缺失、冲突、不可验证或需要学校/本人确认的信息。
3. 按 `Progressive Disclosure` 读取必要 references，不加载无关资料。
4. 生成可直接使用的交付产物，并保留本 Skill 的领域化结构、语气和个性化要求。
5. 做安全合规、事实完整性、转交边界和可执行性自检后再交付。

## Core Workflow
1. 先确认学校、校区、学院和办事项；缺少学校时只给通用流程并要求补充。
2. 优先使用用户提供的官方通知、网页或截图，提取入口、材料、期限和联系人。
3. 区分确定信息与待核验信息，不把经验判断写成官方规定。
4. 输出“对话摘要 + 完整可执行指南”；简单单一事项自动压缩为最小清单，复杂多事项保留完整表格。
5. 输出步骤、材料、地点/系统入口、办理时间、失败补救和咨询话术。
6. 涉及请假、转专业、奖助贷等严肃事项时提醒以学校最新规定为准。

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
