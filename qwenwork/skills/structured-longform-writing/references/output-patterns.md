# QoderWork Output Patterns

Use these patterns for QoderWork online-user deliverables. Select the pattern that matches the reader action, then adapt the section names to the user's topic.

## Report

Use when the user needs analysis, diagnosis, research summary, current-state review, or decision support.

Recommended structure:

```text
1. 摘要：最重要的结论和建议
2. 背景：为什么要分析这个问题
3. 分析范围：材料来源、时间范围、对象边界
4. 关键发现：从材料中得到的主要事实和现象
5. 原因分析：为什么会出现这些问题或机会
6. 影响判断：对用户、业务、产品、团队或项目的影响
7. 建议动作：下一步该做什么
8. 风险与待补充信息：哪些结论仍需验证
```

Quality bar:

- Start with judgment, not a long setup.
- Do not turn a report into a list of notes.
- Use "材料显示 / 可以判断 / 可能需要验证" to separate fact, judgment, and uncertainty.
- If data is missing, name the missing data instead of inventing it.

## Proposal Or Plan

Use when the user needs an executable plan, implementation proposal, project plan, product plan, or improvement plan.

Recommended structure:

```text
1. 方案摘要：解决什么问题、采用什么路径、交付什么结果
2. 背景与问题：为什么现在要做
3. 目标：期望达成的状态和可检查结果
4. 范围与边界：本次做什么，不做什么
5. 方案设计：核心模块、流程或动作
6. 实施路径：阶段、任务、依赖
7. 验收标准：如何判断完成和有效
8. 风险与应对：主要风险、影响、缓解动作
9. 下一步：最先启动的具体动作
```

Quality bar:

- Every action should connect back to a problem or goal.
- Avoid value words without mechanism, such as only saying "提升效率" or "加强管理".
- If no timeline is provided, use phases rather than fake dates.

## Blog Or Article

Use when the user needs a readable explanation, public-facing article, internal post, guide, or thought piece.

Recommended structure:

```text
1. 开头：用问题、场景或冲突引出主题
2. 核心观点：一句话说明本文要讲什么
3. 背景与现象：读者为什么会遇到这个问题
4. 分析展开：分层解释原因、机制或方法
5. 例子或场景：帮助读者理解如何使用
6. 方法建议：读者可以怎么做
7. 结尾：回到核心观点，给出清晰收束
```

Quality bar:

- The article needs a viewpoint, not only definitions.
- Avoid marketing slogans unless the user asks for marketing copy.
- Keep internal product or company details out of public-facing drafts unless supplied and intended for release.

## Internal Briefing

Use when the user writes for leaders, managers, project reviewers, or a cross-functional team.

Recommended structure:

```text
1. 结论先行：当前判断和建议决策
2. 背景：事情为什么重要
3. 现状：已知事实、进展、问题
4. 分析：影响、原因、取舍
5. 建议：推荐方案和替代方案
6. 风险：需要管理层关注的风险
7. 需要确认：希望读者决定或支持什么
```

Quality bar:

- Put the decision or recommendation near the top.
- Do not bury risks at the end without mitigation.
- Use concise paragraphs and tables when the reader needs fast comparison.

## Weekly, Monthly, Or Stage Summary

Use when the user needs a weekly report, monthly report, phase summary, project progress update, or work recap.

Recommended structure:

```text
1. 总体结论：本期状态和最重要结果
2. 本期进展：完成的关键事项
3. 结果与影响：产出、变化、价值机制
4. 问题与风险：阻塞、风险、需要支持的事项
5. 下期计划：下一阶段重点和交付物
6. 待确认事项：需要补充或决策的信息
```

Quality bar:

- Do not exaggerate results when no metrics are provided.
- Write progress as concrete completed work, not generic effort.
- If the audience is a leader, put risks and asks near the top.

## Review Or RCA

Use when the user needs a problem review, troubleshooting report, root-cause analysis, incident postmortem, or repair summary.

Recommended structure:

```text
1. 结论摘要：当前判断、影响、处理状态
2. 问题现象：用户或系统看到什么
3. 影响范围：已知影响和未确认范围
4. 时间线：关键发现、处理、恢复节点
5. 根因假设或根因：证据支持到什么程度
6. 修复动作：已做和待做
7. 防复发措施：机制、监控、流程或测试补强
8. 验证方式：如何确认问题已解决
```

Quality bar:

- Use "根因假设" when evidence is incomplete.
- Do not invent affected users, time windows, or severity levels.
- Every prevention action should map to a cause or failure mode.

## Technical Design

Use when the user asks for a technical design document, architecture proposal, implementation design, system design, or engineering review material.

Recommended structure:

```text
1. 背景与目标：要解决的技术问题
2. 约束：系统、性能、安全、兼容、交付限制
3. 总体设计：核心思路和边界
4. 模块拆分：职责、输入、输出
5. 数据流或调用链路：主要流程和异常路径
6. 接口或配置变化：对外可见的契约
7. 失败模式：错误、降级、重试、恢复
8. 验证方案：测试、灰度、监控、验收
```

Quality bar:

- Keep implementation details tied to requirements and constraints.
- Do not invent API fields, schemas, or performance numbers.
- If the user asks for a plan rather than a design, route to `proposal_or_plan` and include technical modules there.

## PRD Or Requirement Document

Use when the user needs product requirements or feature definition.

Recommended structure:

```text
1. 需求背景
2. 用户与场景
3. 问题定义
4. 目标与非目标
5. 功能范围
6. 用户流程
7. 关键规则
8. 数据与埋点需求
9. 验收标准
10. 风险与待确认问题
```

Quality bar:

- Define user behavior and product rules, not only feature names.
- Mark uncertain product decisions as `待确认问题`.
- Do not add metrics unless the user provides them or asks for suggested metric candidates.

## Customer Or External Material

Use when the user needs customer-facing proposals, partner briefings, official articles, public posts, or white-paper drafts.

Recommended structure:

```text
1. 读者问题：对方关心什么
2. 核心价值：这份材料要让对方相信什么
3. 场景与方案：适用场景、方案路径、边界
4. 收益机制：为什么能产生价值
5. 限制说明：前提、风险、适用边界
6. 下一步：建议沟通或行动
```

Quality bar:

- Avoid internal jargon unless the user asks for internal-facing material.
- Do not use private metrics, customer names, or unreleased roadmap unless supplied and approved by the user.
- For white papers, ask for sources or write a source-ready framework.

## Optional Ending Blocks

Use these blocks when they improve safety or usability:

- `关键假设`: reasonable assumptions made to complete the draft.
- `建议补充的数据/材料`: missing evidence that would strengthen the document.
- `待确认问题`: decisions or facts the user must confirm.
- `不确定信息说明`: claims that cannot be verified from available material.
