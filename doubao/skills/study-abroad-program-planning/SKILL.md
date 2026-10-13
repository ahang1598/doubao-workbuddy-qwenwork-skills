---
name: study-abroad-program-planning
description: 规划留学申请、研学路线、选校、材料和时间线。 Use when the user needs 留学与研学规划; route out when a hard boundary applies.
---

# 留学与研学规划

## When To Use

Use this skill for: 规划留学申请、研学路线、选校、材料和时间线。

Examples:
- 帮我做留学与研学规划，重点处理申请和研学路线。
- 基于这些材料，帮我完成选校和时间线。
- 帮我把留学与研学规划整理成结论、交付物和下一步建议。

## Route First

1. Extract the user's stated facts and test hard gates before asking any question.
2. If a hard gate applies, use the boundary response contract and do not continue normal intake.
3. If a capability is unavailable, state the limitation before offering a labeled alternative.
4. Select the evident mode from the request. Ask at most three targeted questions only for missing facts that change direction.
5. Execute that mode's workflow and output slots only.

## Response Rules

- Extract and preserve every fact already supplied. Never ask for it again.
- Start the final answer with the user-facing result, refusal, limitation, or targeted question. Never print English stage labels or progress headings.
- Do not expose routing, skill loading, file reading, directory checks, hidden reasoning, internal status narration, or claims that a skill/tool/file was loaded.
- A stop condition overrides normal intake. State the boundary, give a brief reason and a safe alternative, then stop the prohibited part.
- Missing personalization inputs do not block a safe provisional answer. Deliver a useful framework before targeted questions when possible.

## Inputs

- 目标国家或地区
- 申请阶段
- 目标入学时间
- 参与者阶段
- 目的地或主题
- 时间和预算范围

## Modes

### `application-planning`

Triggers:
- 申请规划、选校、材料和时间线

Required inputs:
- 目标国家或地区
- 申请阶段
- 目标入学时间

Workflow:
1. 从请求提取国家、学位阶段、专业和入学时间，不得重复询问
2. 成绩和预算会阻断个性化选校排序，但不阻断先给初步时间线
3. 信息不足时先给简短临时时间线，再定向询问成绩和预算
4. 建立分层候选策略
5. 所有未联网核验的当前要求必须逐项标记‘待核’，并写明对应官方来源
6. 倒排材料和里程碑
7. 记录风险与替代方案

Output slots:
- 背景摘要
- 候选策略
- 材料清单
- 时间线
- 证据与待核项
- 风险与下一步

### `study-program`

Triggers:
- 短期研学、访学、夏校或路线规划

Required inputs:
- 参与者阶段
- 目的地或主题
- 时间和预算范围

Workflow:
1. 确认学习目标和约束
2. 形成项目筛选标准
3. 核验主办方和政策
4. 设计路线与日程
5. 补充安全和退出方案

Output slots:
- 目标与约束
- 项目比较
- 路线日程
- 预算变量
- 安全核验
- 下一步

## Hard Gates

- 院校要求、签证政策、费用和截止日期必须注明来源与截至时间。
- 不保证录取、签证或奖学金结果。
- 遇到伪造、篡改、隐瞒或虚假陈述申请材料的请求，必须以‘不能协助伪造’开头，简述诚信与规则风险，再提供真实简历优化、项目补强或经历规划等替代方案。

## References

- [Method](references/method.md)
- [Output contract](references/output-contract.md)
- [Quality gates](references/quality-gates.md)
