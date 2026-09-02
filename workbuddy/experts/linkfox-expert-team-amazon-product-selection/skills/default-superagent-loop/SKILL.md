---
name: default-superagent-loop
description: Use once when LinkFox 主 Agent 在最终渲染前需要缺参判断、AskUserQuestion 准备、专业 Agent 推荐、多卡片推荐、长任务 intake 或点击卡片 context 生成。
---

# Default SuperAgent Loop

这是 `linkfox-superagent-main` 的单轮收尾决策 skill。

根据当前用户需求、主会话上下文和草稿结果，判断本轮应该在主会话完成、补充信息、准备 `AskUserQuestion`、推荐一个或多个专业 Agent 卡片、生成点击卡片携带的 `context`，还是进入 Skill 创作路径。

这个 skill 不直接面向用户。只返回结构化 loop decision；不要写最终报告正文，也不要替代 `CLAUDE.md`。它不可重入：同一用户回合调用一次后，调用方必须渲染结果并结束本轮，不得再次调用本 skill 做二次收尾。

## Reference Loading Map

只在当前判断需要时读取对应 reference：

- `AskUserQuestion` 参数结构和用户可见选项规则：`references/ask-user-question.md`
- 专业 Agent 卡片推荐和 Skill 创作路由：`references/workspace-routing.md`
- 点击卡片 `context` 边界：`references/temporary-transition-boundary.md`
- 严格 JSON 返回结构：`references/response-schema.md`

## Hard Rules

1. `CLAUDE.md` 是 SSOT；本 skill 只返回当前轮的收尾决策。
2. 单轮最多调用一次；如果当前回合已经调用过 `default-superagent-loop`，不得再次调用，必须直接渲染已有 decision。
3. 图片、媒体、报告、CSV、JSON、文件等业务产物已经成功生成后，不得为了“补一个收尾建议/推荐卡片”再次调用本 skill；调用方应直接渲染产物和收尾标签。若产物是视频、图片或 Listing 且后续仍围绕同类产物优化，调用方可直接输出对应专业 Agent 标签。
4. 只返回 JSON，不渲染 markdown 报告或长 checklist。
5. 不猜缺失字段；需要用户补充的信息标记给 `AskUserQuestion`。关键缺参只要能提供 2-4 个可选示例或候选方向，就优先准备 `AskUserQuestion`。
6. 不写长交付内容；长输出只在 `delivery_action` 中标记为 `linkfox-report-generator`。
7. 用户可见问题、选项、摘要和草稿里，不暴露内部协议词。
8. 专业 Agent 推荐是卡片；用户点击卡片后进入对应专业 Agent，并携带该卡片显式写明的 `context` 业务摘要。
9. 不生成系统内部数据、系统内部指令或实现细节。
10. 专业 Agent 推荐卡片的 `mode_id` 只能来自 `workspace-routing.md` 中的五个专业 Agent；不要把工具 skill、数据源、JSON 产物或任务产出卡片当作专业 Agent 推荐。
11. 专业 Agent 推荐卡片的 `title` 和最终标签正文必须写成“推荐名称｜8-24 字简短说明”，例如“Listing 生成｜继续优化标题、五点和埋词”，不要只写“Listing 生成”或“优化标题/五点”。
12. 最终渲染时，Agent 推荐只能作为 `<linkfox-suggestion-agent>` 标签输出；不要把推荐名称写成普通正文、列表项或裸文本。
13. `main_result.content`、`ask_user_question.visible_summary`、`delivery_action.reason` 和 `notes` 不得包含 `选品分析｜`、`市场分析｜`、`图片生成｜`、`视频生成｜`、`Listing 生成｜`。这些内容只能出现在 `agent_recommendations.cards[].title`。
14. 如果 `main_result.content` 想表达“后续可以做图片 / 视频 / Listing / 市场分析 / 选品验证”，必须同步生成对应 `agent_recommendations.cards`，或把正文改成不带专业 Agent 推荐名称的普通业务描述。

## Loop

1. 先做防循环检查：如果本回合已经调用过本 skill，或业务产物已经成功生成并进入最终渲染阶段，停止决策；调用方直接结束本轮。
2. 理解用户真实业务目标，以及主会话是否能先给出有用结果。
3. 准备紧凑的主会话结果：结论、草稿、框架、清单、风险、下一步或 blocker。
4. 如果需要公开或最新信息，在决策里标记应使用 `linkfox-tsearch-search`。
5. 只有主会话已经给出有用结果，或已完成长任务 intake 后，才推荐专业 Agent 卡片。
6. 如果用户正在创建或优化 Skill，进入 Skill creator 路径，不推荐五个专业 Agent。
7. 如果执行前必须让用户选择优先方向，准备 `AskUserQuestion`，不要用多 Agent 卡片代替必要确认。若同时缺少 ASIN、站点等关键参数，也要把缺参提示合并进 `AskUserQuestion`，不要退化成只用普通文本问缺参。
8. 如果当前任务已完成，且存在多个高置信度后续方向，准备 2-3 个专业 Agent 推荐。
9. 数据查询后若已经形成市场、竞品、趋势或可行性结论，且下一步需要 Keepa、卖家精灵、亚马逊搜索、竞品格局、销量价格带或评论深挖，必须准备市场分析卡片；若同时涉及入场判断、切入空间、预算或供应链验证，再准备选品分析卡片。
10. 每个推荐都生成简短 `context` 业务摘要：原始目标、已确认参数、当前结论、下一步和约束。
11. 按 `references/response-schema.md` 返回严格 JSON 结构。

## Acceptance Check

- 主会话没有退化成纯路由。
- 同一用户回合不会二次调用 `default-superagent-loop`。
- 已成功生成图片、媒体、报告或文件产物后，不再通过本 skill 追加收尾。
- 如果需要 `AskUserQuestion`，必须有顶层 `questions`。
- 用户可见文案只使用业务语言。
- 专业 Agent 推荐为 0-3 个唯一 `mode_id`。
- 推荐卡片只使用五个专业 Agent `mode_id`，不出现 `linkfox-sellersprite`、工具 skill 名或 JSON 产物名。
- 每个推荐卡片的 `title` 明确包含目标推荐名称和简短说明，中间使用 `｜`。
- 每个推荐都有简短业务 `context`，且不含系统内部字段。
- 最终回答里所有 `<linkfox-suggestion-agent>` 标签必须相邻，并作为最后一个区块输出；不要让正文、后续建议或其他内容插在多个 Agent 卡片之间。
- 不出现 `图片生成｜...`、`Listing 生成｜...` 这类未包裹 `<linkfox-suggestion-agent>` 的裸推荐文本。
- `main_result.content` 不把“后续建议”写成 `图片生成｜...` 或其他固定推荐名称；有推荐就放进 `agent_recommendations.cards`。
- `main_result.content` 提到的专业后续方向，与 `agent_recommendations.cards` 保持一致；不要正文提图片、底部只推荐 Listing。
- 不暴露系统内部字段、工具调用参数、协议细节或实现细节。
- 长交付已标记给 `linkfox-report-generator`。
