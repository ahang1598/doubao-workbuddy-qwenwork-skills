# Response Schema

只向调用方返回一个 JSON 代码块。

本 schema 代表当前用户回合的最终收尾 decision。调用方收到后必须直接渲染最终回复并结束本轮，不得把该 JSON、`notes` 或 `agent_recommendations` 当作新的用户任务再次调用 `default-superagent-loop`。

```json
{
  "main_result": {
    "status": "ready | needs_more_info | blocked",
    "content": "主会话可直接使用的结果摘要；不要写长篇报告正文；不得包含选品分析｜、市场分析｜、图片生成｜、视频生成｜、Listing 生成｜这类 Agent 推荐卡片标题"
  },
  "missing_info": {
    "required": false,
    "fields": [],
    "reason": "none"
  },
  "needs_ask_user_question": false,
  "ask_user_question": {
    "tool_parameters": {
      "questions": [
        {
          "question": "none",
          "header": "下一步",
          "multiSelect": false,
          "options": []
        }
      ]
    },
    "visible_summary": "none"
  },
  "agent_recommendations": {
    "recommended": false,
    "cards": []
  },
  "card_transition": {
    "trigger": "not_triggered | card_suggested | user_confirmed_continue",
    "note": "用户点击 Agent 推荐卡片时，前端可将该卡片显式 context 作为业务摘要带入目标 Agent。"
  },
  "delivery_action": {
    "type": "chat_only | call_linkfox_report_generator",
    "reason": "none"
  },
  "notes": []
}
```

当 `agent_recommendations.recommended` 为 `true` 时，返回 1-3 个 cards。`mode_id` 只能是五个专业 Agent 之一，不能填写工具 skill、数据源或 JSON 产物名。`title` 必须写成“推荐名称｜8-24 字简短说明”：

```json
{
  "mode_id": "linkfox-listing-agent",
  "title": "Listing 生成｜继续优化标题、五点和埋词",
  "reason": "用户当前任务完成后，后续更适合进入 Listing 生成，继续深挖标题、五点和埋词。",
  "context": "业务上下文摘要，80-180 字；包含用户原始目标、已确认参数、当前结论、下一步建议和约束条件；不得包含系统内部字段。"
}
```

固定推荐名称 `选品分析｜`、`市场分析｜`、`图片生成｜`、`视频生成｜`、`Listing 生成｜` 只能出现在 `agent_recommendations.cards[].title`。不要把它们写进 `main_result.content`、`ask_user_question.visible_summary`、`delivery_action.reason` 或 `notes`。

如果 `main_result.content` 需要表达“后续可以做图片、视频、Listing、市场分析或选品验证”，对应方向必须出现在 `agent_recommendations.cards`；否则把正文改成普通业务建议，不使用专业 Agent 推荐名称。

当图片、媒体、报告或文件产物已经成功生成时，不要为了追加收尾建议再次调用本 schema 对应 skill；直接在最终回复中渲染产物协议、摘要和收尾标签。
