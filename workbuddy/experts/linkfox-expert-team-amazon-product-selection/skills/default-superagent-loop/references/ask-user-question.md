# AskUserQuestion

当 loop 需要缺参收集、确认、多选项选择，或引导用户继续深挖时，读取本 reference。

关键缺参不要求一定是严格封闭选择。只要能给出 2-4 个常见示例、候选方向或“其他，我补充”的选项，就优先使用 `AskUserQuestion` 组件，而不是普通文本追问。

## Required Tool Shape

`ask_user_question.tool_parameters` 必须直接匹配 AskUserQuestion 工具输入：

```json
{
  "questions": [
    {
      "question": "保温杯方向初步判断给你了，接下来想怎么推进？",
      "header": "下一步",
      "multiSelect": false,
      "options": [
        "选品分析",
        "市场分析",
        "先补充目标价位和差异化想法",
        "先到这，不继续了"
      ]
    }
  ]
}
```

规则：

- `questions` 必填，且必须是非空数组。
- 每个 question 必须包含 `question`、`header`、`options` 和 `multiSelect`。
- 使用 2-4 个用户可见选项。
- 除非用户明确需要多选，否则 `multiSelect` 默认是 `false`。
- 只使用业务语言。
- 缺品类、站点、预算、时间范围、输出格式等执行前关键参数时，如果可以给出示例选项，必须用 `AskUserQuestion`。

缺品类示例：

```json
{
  "questions": [
    {
      "question": "你想搜索哪个品类的亚马逊热卖品？",
      "header": "选择品类",
      "multiSelect": false,
      "options": [
        "家居装饰",
        "宠物用品",
        "厨房收纳",
        "其他品类，我直接输入"
      ]
    }
  ]
}
```

多意图 + 缺 ASIN 示例：

```json
{
  "questions": [
    {
      "question": "你想先从哪个方向开始？执行前还需要补充具体 ASIN。",
      "header": "优先方向",
      "multiSelect": false,
      "options": [
        "先补充 ASIN，再做竞品分析",
        "先补充 ASIN，再优化 Listing",
        "先补充 ASIN，再规划图片",
        "先给我一个不依赖 ASIN 的流程建议"
      ]
    }
  ]
}
```

当用户同时提出多个任务并问“先从哪个开始 / 先做哪个 / 哪个优先”，必须用 `AskUserQuestion` 让用户选优先方向；即使还缺 ASIN、站点等关键参数，也不要只输出普通文本缺参追问。

## Forbidden Shape

不要返回没有顶层 `questions` 的裸 `question/options`；这会导致 `Invalid tool parameters`。

## Forbidden Visible Words

用户可见文案里不要出现：

- 系统内部字段
- 工具调用 JSON
- 协议字段
- 实现细节
