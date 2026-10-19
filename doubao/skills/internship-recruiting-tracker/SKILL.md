---
name: internship-recruiting-tracker
description: "当用户请求实习或校园招聘跟踪、职位描述匹配、截止日期提醒、申请计划、简历差距审查、跟进消息或实习校招提醒时，使用本技能。"
---

# 实习校招提醒

## 概述
把实习校招从零散刷信息变成“目标画像、岗位漏斗、截止提醒、简历面试迭代”的求职作战台。

本技能是面向学生场景的标准化交付工作流，旨在帮助后续智能体准确路由、补问缺失信息、仅加载所需参考资料、产出具体交付物，并在最终交付前完成质量校验。
## 使用场景
- 当用户的请求匹配本技能标题、同义场景或下方 `适用场景` 中的触发词时调用。
- 只处理本技能原有能力、交付产物和个性化输出结构；相邻任务按 `不适用场景` 和 `路由决策` 转交。
- 信息不足时先追问或显式标注假设，不能为了补齐成品而编造学校政策、官方节点、个人经历或结果承诺。
## 适用场景
- 用户要找实习、校招、暑研、管培、项目制岗位或建立投递跟踪表。
- 用户要岗位优先级、职位描述匹配、截止提醒、简历改写、面试准备、周报复盘、录用通知决策。
- 用户有目标公司、岗位链接、简历经历、城市/签证/远程限制，需要形成求职漏斗。
- 输入里出现“投递计划”“岗位匹配”“简历关键词”“在线测评/面试准备”“校招提醒”等触发词。
## 不适用场景
- 只要奖学金/科研项目申报材料，转 `competition-scholarship-application`。
- 只要竞选演讲或面试自我介绍稿，转 `speech-campaign-intro-coach`。
- 只要校园活动推广和大使招募运营，转 `campus-content-operator`。
- 用户要求伪造经历、虚构指标、绕过平台规则、传播受保护面试题时，拒绝该部分。
## Routing Decision
1. 先看最终交付是否围绕“岗位漏斗 + 简历/面试迭代”；是则用本 skill。
2. 如果用户只要一段自我介绍或行为面试口播稿，转演讲 skill。
3. 如果岗位信息没有来源，必须标注来源缺失和更新时间待确认，不能编造开放状态。
4. 如果涉及签证、就业资格或劳动合同，只能做问题清单，不能给官方法律结论。

## Execution Structure
1. 用户画像：专业、年级、方向、城市、限制、能力证据、缺口。
2. 来源台账：岗位、链接/来源、更新时间、开放状态、截止风险、可验证性；截止必须写原始时区、当地时间、北京时间和剩余小时。
3. 排序模型：匹配度、截止紧迫度、成长性、准备成本和风险说明。
4. 限投排除：保留过期/排除岗位编号、原因、冷却结束日、禁投截止日和剩余机会。
5. 简历映射：JD 关键词、已有证据、缺口、可改 bullet、补证动作；诊断需覆盖 PII、ATS、成果量化、AI 润色失真等权威就业指导维度。
6. 投递漏斗：待投、已投、OA、面试、offer/拒绝、复盘、下次跟进。
7. 合规自检：不承诺 offer、不伪造经历、不泄露题、不抓取未授权数据。

## Required Inputs
- 专业、年级、城市、目标方向
- 简历或经历素材
- 目标公司/岗位 JD
- 可投递时间、限制条件

## Output Contract
- 岗位周报
- 投递计划
- 简历修改建议
- 面试题库
- 跟进提醒清单

Every answer must include a finished artifact, missing facts if any, and a compact self-check. For tables or plans, include owners, dates, status, or acceptance criteria whenever the task implies execution.

## 核心流程
1. 判定是否匹配本 Skill 的使用场景、输出合同和不适用边界。
2. 抽取用户已给事实，列出缺失、冲突、不可验证或需要学校/本人确认的信息。
3. 按 `Progressive Disclosure` 读取必要 references，不加载无关资料。
4. 生成可直接使用的交付产物，并保留本 Skill 的领域化结构、语气和个性化要求。
5. 做安全合规、事实完整性、转交边界和可执行性自检后再交付。

## Core Workflow
1. 先建立用户画像：方向、城市、年级、能力证据、限制条件。
2. 对岗位按匹配度、截止时间、成长性和准备成本排序。
3. 针对每个高优岗位输出简历改写点、关键词、作品/项目证据和面试准备。
4. 面试包至少包含每人/每岗位 8 题、2 个 STAR、AI 面试高频题和复盘跟进表。
5. 维护投递漏斗：待投、已投、笔试、面试、offer、拒绝和复盘。
6. 所有岗位信息必须标注来源和更新时间；不确定则要求用户确认。

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
