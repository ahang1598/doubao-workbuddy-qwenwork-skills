---
{
  "actionCode": "IF",
  "fields": {
    "expression": { "type": "string", "required": true },
    "thenSteps": { "type": "array", "required": true },
    "elseSteps": { "type": "array", "required": false }
  }
}
---

# IF/ELSE

条件分支。表达式为 true 执行 `thenSteps`，否则执行 `elseSteps`（可选，无则跳过）。

## 参数

| 参数 | 类型 | 必须 | 说明 |
|---|---|---|---|
| `expression` | string | 是 | 条件表达式，支持 `{{}}` 模板变量 |
| `thenSteps` | `ScrapeStep[]` | 是 | true 分支 |
| `elseSteps` | `ScrapeStep[]` | 否 | false 分支，不提供时条件不满足则跳过 |

## 表达式语法

| 类别 | 语法 |
|------|------|
| 比较 | `==` `!=` `>` `<` `>=` `<=` |
| 逻辑 | `&&` `\|\|` `!` |
| 字面量 | `99`、`4.5`、`'active'`、`"soldout"`、`null` |
| 分组 | `()` |
| 变量 | `result.price`（`.` 嵌套访问 `context.results`），模板变量 `{{}}` 自动替换 |

**内置函数**：

| 函数 | 说明 |
|------|------|
| `exists(selector)` | 页面至少 1 个匹配 → true |
| `count(selector)` | 返回匹配元素数量 |
| `isEmpty(v)` | null 或空字符串 → true |
| `isNotEmpty(v)` | 非 null 且非空 → true |
| `contains(str, substr)` | str 包含 substr → true |
| `startsWith(str, prefix)` | str 以 prefix 开头 → true |
| `endsWith(str, suffix)` | str 以 suffix 结尾 → true |

## 示例

```json
{
  "actionCode": "IF",
  "expression": "result.availability != 'Currently unavailable.'",
  "thenSteps": [
    { "actionCode": "EXTRACT", "selector": "span.a-price span.a-offscreen", "extractField": "price", "extractType": "text", "tabKey": "tabKey666" }
  ],
  "elseSteps": [
    { "actionCode": "EXTRACT", "selector": "#outOfStock span", "extractField": "status", "extractType": "text", "tabKey": "tabKey666" }
  ]
}
```
