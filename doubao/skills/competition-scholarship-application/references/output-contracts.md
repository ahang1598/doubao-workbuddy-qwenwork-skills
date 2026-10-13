# Output Contracts

## Required Artifact Fields
- 申报时间线
- 材料清单
- 个人/项目陈述
- 答辩稿
- 材料缺口表
- 官方规则核验/待核验清单
- PPT 逐页大纲（答辩或路演场景）
- 逐张票据审核表（经费报销场景）

## Minimum Quality Bar
- The result must match the user's context and audience.
- The result must include concrete wording, table rows, schedule, or checklist items when applicable.
- The result must not be only a framework unless the user explicitly asks for a framework.
- The result must label unknown facts and assumptions.
- Rule-dependent conclusions must cite the provided rule, an official source, or be labeled `待核验`.
- Defense deliverables must include a full script, slide-by-slide PPT outline, and expert questions when the task includes defense, roadshow, or review presentation.
- Timeline must be reverse-planned to concrete dates when a deadline is known, with the longest bottleneck called out.
- Risk tables must distinguish `一票否决项`, `高风险`, and `中风险`.

## Final Review Checklist
- Trigger matched: yes/no.
- Required inputs complete or visibly marked.
- Deliverables present.
- Tone fits the audience.
- No fabricated fact.
- No unsafe or non-compliant instruction.
- User can take a next action immediately.
- Official-rule check or待核验 label is present.
- Defense/PPT and票据 details are included when relevant.
