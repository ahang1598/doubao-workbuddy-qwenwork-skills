---
name: competition-scholarship-application
description: "当用户请求竞赛、奖学金、科研、大创或项目申报帮助时，使用本技能；包括时间线、证据矩阵、材料草稿、答辩稿或缺口清单。"
---

# 竞赛奖学金申报

## 概述
把奖学金、竞赛、大创、科研申报拆成节点、证据、叙事、答辩四条线，降低漏材料和临时拼材料的风险。

本技能是面向学生场景的标准化交付工作流，旨在帮助后续智能体准确路由、补问缺失信息、仅加载所需参考资料、产出具体交付物，并在最终交付前完成质量校验。
## 使用场景
- 当用户的请求匹配本技能标题、同义场景或下方 `适用场景` 中的触发词时调用。
- 只处理本技能原有能力、交付产物和个性化输出结构；相邻任务按 `不适用场景` 和 `路由决策` 转交。
- 信息不足时先追问或显式标注假设，不能为了补齐成品而编造学校政策、官方节点、个人经历或结果承诺。
## 适用场景
- 用户要准备奖学金、竞赛、大创、科研基金、荣誉称号、项目申报或答辩材料。
- 用户要规则拆解、资格核对、材料清单、时间线、证据映射、个人陈述、项目摘要、答辩稿。
- 用户材料里有论文、奖项、志愿服务、项目、推荐人、预算、成果证明，需要判断强弱证据。
- 输入里出现“申报”“评审标准”“材料缺口”“推荐信”“答辩”“不能夸大经历”等触发词。
## 不适用场景
- 只要校园办事流程、提交入口或咨询部门，转 `campus-service-navigator`。
- 只要竞选演讲、自我介绍、口播 问答，转 `speech-campaign-intro-coach`。
- 只要课程汇报或课堂演示文稿，转 `course-presentation-builder`。
- 用户要求伪造成果、虚构论文、夸大志愿影响、代写不实推荐内容时，拒绝该部分。
## Routing Decision
1. 先看核心任务是否是“获得评审认可的申请材料”；是则用本 skill。
2. 如果用户同时问“怎么提交 + 怎么写材料”，本 skill 负责材料策略和文本，提交流程只给待核验办事清单。
3. 如果规则原文缺失，必须先生成规则待确认清单，不能替用户做官方资格结论。
4. 如果经历证据不完整，输出必须分强证据、弱证据、不可写成事实三类。

## Execution Structure
1. 规则抽取：硬性资格、材料组件、截止时间、评审维度、提交渠道；优先核对官方通知/赛事规则，不能联网或无原文时标注 `待核验`。
2. 证据映射：逐条把经历映射到评审维度，并标注证据强度和缺口。
3. 风险分级：识别一票否决项、高风险、中风险，并给具体改写或补证动作。
4. 材料计划：倒排到具体日期，标出最长瓶颈、负责人、待补证明、版本状态、验收标准。
5. 文本生成：陈述、摘要、预算说明、答辩稿必须回到可证明事实；需要答辩时给全文稿和 PPT 逐页大纲。
6. 追问准备：生成评委可能质疑的问题和证据化回答。
7. 合规自检：检查未发表、未获奖、口头评价、影响数据是否被过度包装。

## Required Inputs
- 申报类型与规则原文
- 个人/团队经历与成果
- 成绩、证书、论文、项目材料
- 截止时间与提交渠道

## Output Contract
- 申报时间线
- 材料清单
- 个人/项目陈述
- 答辩稿
- 材料缺口表

Every answer must include a finished artifact, missing facts if any, and a compact self-check. For tables or plans, include owners, dates, status, or acceptance criteria whenever the task implies execution.

## 核心流程
1. 判定是否匹配本 Skill 的使用场景、输出合同和不适用边界。
2. 抽取用户已给事实，列出缺失、冲突、不可验证或需要学校/本人确认的信息。
3. 按 `Progressive Disclosure` 读取必要 references，不加载无关资料。
4. 生成可直接使用的交付产物，并保留本 Skill 的领域化结构、语气和个性化要求。
5. 做安全合规、事实完整性、转交边界和可执行性自检后再交付。

## Core Workflow
1. 先读取申报规则并核对官方通知/赛事规则；不能确认的规则只列待核验，不作最终资格结论。
2. 把用户经历映射到评分维度，区分强证据、弱证据和缺口。
3. 经费/票据场景必须逐张审核票据，列问题、处理方式、能否报销、补证责任人。
4. 生成材料清单与倒排时间线，标注必须人工补齐的证明文件和最长瓶颈。
5. 撰写陈述时必须基于用户提供事实，不得虚构奖项、数据、身份或导师意见。
6. 生成答辩稿全文、PPT 逐页大纲和可能追问，回答必须回到规则和证据。

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
