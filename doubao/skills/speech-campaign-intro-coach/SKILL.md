---
name: speech-campaign-intro-coach
description: "当用户请求演讲、竞选介绍、新生自我介绍、班委竞选、社团面试、答辩、项目推介、课堂发言或模拟问答辅导时，使用本技能。"
---

# 演讲/竞选自我介绍

## 概述
把学生表达场景拆成“身份定位、经历证据、听众期待、结构节奏、问答预案”，让发言真诚、有记忆点、能落到行动。

本技能是面向学生场景的标准化交付工作流，旨在帮助后续智能体准确路由、补问缺失信息、仅加载所需参考资料、产出具体交付物，并在最终交付前完成质量校验。
## 使用场景
- 当用户的请求匹配本技能标题、同义场景或下方 `适用场景` 中的触发词时调用。
- 只处理本技能原有能力、交付产物和个性化输出结构；相邻任务按 `不适用场景` 和 `路由决策` 转交。
- 信息不足时先追问或显式标注假设，不能为了补齐成品而编造学校政策、官方节点、个人经历或结果承诺。
## 适用场景
- 用户要自我介绍、竞选演讲、社团面试回答、奖学金答辩开场、项目路演口播或尖锐 问答。
- 用户要把真实经历整理成定位句、支撑点、行动承诺、口播稿、问答策略和表达训练。
- 用户担心经历普通、失败经历不好讲、时长卡不住、被质疑、表达太书面。
- 输入里出现“90 秒”“3 分钟”“竞选”“自我介绍”“尖锐问题”“口播”“肢体语音”等触发词。
## 不适用场景
- 需要完整课程演示文稿 结构、逐页讲稿和图表，转 `course-presentation-builder`。
- 需要奖学金/竞赛申报规则、材料清单和项目陈述，转 `competition-scholarship-application`。
- 需要学生组织活动执行、通知、排班、纪要，转 `student-leader-workbench`。
- 用户要求虚构经历、攻击对手、冒充身份、操纵投票或承诺不可控结果时，拒绝该部分。
## Routing Decision
1. 先看最终交付是否是“人对人表达的口播稿或 Q&A”；是则用本 skill。
2. 如果用户要整套申报材料，本 skill 只负责口播/答辩表达，材料主体转申报 skill。
3. 如果用户要课堂汇报整套页内容，转课程汇报 skill；只要开场或答辩口播时才用本 skill。
4. 如果经历证据不足，必须用“真实事实 + 可承诺行动”替代夸张包装。

## Execution Structure
1. 场景定位：确认身份、岗位/奖项、听众、时长、目标和禁忌。
2. 证据抽取：列真实经历、可证明成果、失败经历、限制和不可写内容。
3. 表达骨架：形成 1 个定位句、2-3 个支撑点、1 个行动承诺。
4. 口播版本：在对话中直接输出完整稿件或核心段落，按时长标注字数、节奏、停顿和删减点。
5. 场景模板：答辩重合规/资格/证据链，路演重故事弧/数据局限/团队贡献，竞选重承诺可控性，面试重身份定位和高压 Q&A。
6. 压力问答：生成尖锐问题、回答稿、证据回链和避坑提醒。
7. 训练自检：声音、语速、眼神、手势、计时和合规边界。

## Required Inputs
- 场景、时长、听众和目标
- 个人经历、优势、证据和真实限制
- 竞选岗位/社团/奖项要求
- 想要的语气：自然、正式、幽默、稳重

## Output Contract
- 自我介绍稿
- 竞选演讲稿
- 面试回答
- 答辩 Q&A
- 表达优化建议

Every answer must include a finished artifact, missing facts if any, and a compact self-check. For tables or plans, include owners, dates, status, or acceptance criteria whenever the task implies execution.

## 核心流程
1. 判定是否匹配本 Skill 的使用场景、输出合同和不适用边界。
2. 抽取用户已给事实，列出缺失、冲突、不可验证或需要学校/本人确认的信息。
3. 按 `Progressive Disclosure` 读取必要 references，不加载无关资料。
4. 生成可直接使用的交付产物，并保留本 Skill 的领域化结构、语气和个性化要求。
5. 做安全合规、事实完整性、转交边界和可执行性自检后再交付。

## Core Workflow
1. 先确认场景、时长、听众、目标和禁忌表达。
2. 抽取真实经历证据，形成 1 个定位句、2-3 个支撑点和 1 个行动承诺。
3. 按时长生成可口播版本，避免书面腔和过度夸张。
4. 针对竞选、面试、答辩、路演生成差异化追问和回答策略。
5. 给出合规替代表述，覆盖编造成果、越权承诺、标签化/卖惨表达、拉踩对手和隐私暴露。
6. 输出前检查是否虚构经历、贬低他人、承诺不可控结果。

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
