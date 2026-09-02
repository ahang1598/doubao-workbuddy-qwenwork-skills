---
{
  "actionCode": "EXTRACT",
  "fields": {
    "selector": { "type": "string|string[]", "required": true },
    "extractField": { "type": "string", "required": true },
    "extractType": { "type": "string", "required": true, "enum": ["text", "attribute", "list", "list_items"] },
    "attribute": { "type": "string|string[]", "required": { "when": { "extractType": "attribute" } } },
    "itemSchema": { "type": "array", "required": false },
    "onFailure": {
      "type": "object",
      "required": false,
      "schema": {
        "actionCode": { "type": "string", "required": true, "const": "FIND_SELECTOR" },
        "field": { "type": "string", "required": false },
        "hint": { "type": "string", "required": false },
        "thenRetry": { "type": "boolean", "required": false }
      }
    }
  }
}
---

# EXTRACT

从页面 DOM 元素提取数据。

## 参数

| 参数 | 类型 | 必须 | 说明 |
|---|---|---|---|
| `selector` | `string` 或 `string[]` | 是 | 数组时依次尝试，第一个命中的即生效 |
| `extractField` | string | 是 | 返回数据的 key |
| `extractType` | string | 是 | `text` — textContent；`attribute` — HTML 属性值（需配 `attribute`）；`list` — 所有匹配元素的数组；`list_items` — 结构化列表（需配 `itemSchema`）|
| `attribute` | `string` 或 `string[]` | 条件 | `extractType=attribute` 时必填。数组时依次尝试，第一个取到值的即生效 |
| `itemSchema` | array | 否 | `extractType=list_items` 时必填。子字段数组，每项含 `selector`（在容器内查找）、`extractType`（text/attribute/image/link/exists）、`extractField`（字段名）、`attribute`（extractType=attribute 时）|
| `onFailure` | object | 否 | 失败时自动 FIND_SELECTOR 自愈：`{ "actionCode": "FIND_SELECTOR", "field": "title", "thenRetry": true }` |

## 示例

```json
{ "actionCode": "EXTRACT", "selector": "span#productTitle", "extractField": "title", "extractType": "text", "tabKey": "tabKey666" }
```
