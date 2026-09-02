---
{
  "actionCode": "VERIFY_SELECTOR",
  "fields": {
    "selector": { "type": "string|string[]", "required": true },
    "extractType": { "type": "string", "required": false },
    "attribute": { "type": "string", "required": false },
    "extractField": { "type": "string", "required": false }
  }
}
---

# VERIFY_SELECTOR

验证 CSS 选择器在当前页面的匹配情况。Part 2 诊断工具。

## 参数

| 参数 | 类型 | 必须 | 说明 |
|---|---|---|---|
| `selector` | string 或 string[] | 是 | 要验证的 CSS 选择器 |
| `extractType` | string | 否 | `text` / `attribute` |
| `extractField` | string | 否 | 返回数据的 key |

## 示例

```json
{ "actionCode": "VERIFY_SELECTOR", "selector": ".common-entry__top", "extractType": "list", "extractField": "panel_count", "tabKey": "tabKey666" }
```
