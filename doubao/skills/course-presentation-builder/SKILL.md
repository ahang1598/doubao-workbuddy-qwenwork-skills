---
name: course-presentation-builder
description: "当用户希望根据主题、笔记、论文或研究材料制作课程汇报演示文稿时，使用本技能；包括大纲、逐页文案、演讲者备注或答辩问答。"
---

# 课程汇报 PPT

## 概述
把课程展示从“堆资料”升级成“有论点、有证据、有节奏、有答辩预案”的汇报生产线。

本技能是面向学生场景的标准化交付工作流，旨在帮助后续智能体准确路由、补问缺失信息、仅加载所需参考资料、产出具体交付物，并在最终交付前完成质量校验。
## 使用场景
- 当用户的请求匹配本技能标题、同义场景或下方 `适用场景` 中的触发词时调用。
- 只处理本技能原有能力、交付产物和个性化输出结构；相邻任务按 `不适用场景` 和 `路由决策` 转交。
- 信息不足时先追问或显式标注假设，不能为了补齐成品而编造学校政策、官方节点、个人经历或结果承诺。
## 适用场景
- 用户要做课程展示、研讨课展示、读书报告、论文汇报、调研展示、小组汇报或课堂答辩。
- 用户要把论文、报告、课堂笔记、调查数据压缩成 演示文稿结构、逐页内容、讲稿、图表和 问答。
- 用户遇到材料堆砌、论点不清、时间超限、分工混乱、老师追问无法准备等问题。
- 输入里出现“12 分钟汇报”“逐页讲稿”“演示文稿大纲”“图表建议”“答辩问题”等触发词。
## 不适用场景
- 只要海报、封面、横幅或视觉主图，转 `campus-poster-cover-generator`。
- 只要竞选演讲、自我介绍或面试口播，转 `speech-campaign-intro-coach`。
- 只要奖学金/竞赛申报材料，转 `competition-scholarship-application`。
- 用户要求编造研究数据、引用不存在论文、隐瞒人工智能使用要求时，拒绝该部分并给合规替代。
## Routing Decision
1. 先看最终交付物是否是课堂展示/汇报页和讲稿；是则用本 skill。
2. 如果用户同时要“PPT + 海报”，本 skill 负责汇报结构和逐页讲稿，海报转视觉 skill。
3. 如果用户只要开场 90 秒口播而非整套汇报，转演讲 skill。
4. 如果输入来源多且结论冲突，必须先建立论点-证据-边界表。

## Execution Structure
1. 汇报定位：确认课程、题目、时长、听众、评分标准和小组分工。
2. 材料压缩：形成 1 个中心论点、3-5 个支撑模块、局限和结论。
3. 初稿诊断：若用户给了学生初稿，先指出流水账、概念混用、证据强度混淆、相关当因果等问题，再重组页面。
4. 页序规划：按时长估算页数，为每页分配时间和负责人。
5. 逐页交付：每页给观点标题、页面正文、讲稿、图表口径、来源边界。
6. 成品分支：用户要可展示成果时，文字包之后继续生成实际 PPT/飞书幻灯片；无法生成时明确给可导入页表。
7. 答辩准备：输出 8-12 个追问和回答要点，分配负责人。
8. 自检：检查不堆资料、不伪造数据、不把背景来源当因果证据。

## Required Inputs
- 课程主题与展示时长
- 老师要求、评分标准或模板
- 论文/调研/课堂材料
- 听众背景与小组分工

## Output Contract
- PPT 结构
- 逐页标题与正文
- 演讲稿
- 答辩问题
- 素材缺口清单

Every answer must include a finished artifact, missing facts if any, and a compact self-check. For tables or plans, include owners, dates, status, or acceptance criteria whenever the task implies execution.

## 核心流程
1. 判定是否匹配本 Skill 的使用场景、输出合同和不适用边界。
2. 抽取用户已给事实，列出缺失、冲突、不可验证或需要学校/本人确认的信息。
3. 按 `Progressive Disclosure` 读取必要 references，不加载无关资料。
4. 生成可直接使用的交付产物，并保留本 Skill 的领域化结构、语气和个性化要求。
5. 做安全合规、事实完整性、转交边界和可执行性自检后再交付。

## Core Workflow
1. 先确认汇报目标：知识讲解、论文精读、调研汇报、方案路演或课堂展示。
2. 把材料压缩成中心论点、3-5 个支撑模块和结论，不允许直接堆原文摘录。
3. 按时长估算页数和讲述节奏，默认每分钟 1-1.5 页。
4. 逐页输出标题、页面要点、讲述稿和可视化建议；涉及数据时给图表口径。
5. 对文献综述、研究方法、调研策略类汇报，按场景扩展对比矩阵维度，不得被固定模板压缩掉关键维度。
6. 最后生成老师可能追问的 8-12 个问题与回答要点。

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
