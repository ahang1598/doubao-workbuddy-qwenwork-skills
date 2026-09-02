---
{
  "actionCode": "GET_DOM",
  "fields": {
    "selector": { "type": "string", "required": false },
    "mode": { "type": "string", "required": false, "enum": ["structure", "a11y", "full"] },
    "maxDepth": { "type": "number", "required": false },
    "maxNodes": { "type": "number", "required": false },
    "extractField": { "type": "string", "required": false }
  }
}
---

# GET_DOM

DOM 结构快照。Part 2 诊断工具，GET_PAGE_INFO 确认页面健康后使用。

## 参数

| 参数 | 类型 | 必须 | 说明 |
|---|---|---|---|
| `selector` | string | 否 | 限定快照范围的 CSS 选择器，如 `#ppd` |
| `mode` | string | 否 | `structure`（默认）/ `a11y` / `full` |
| `maxDepth` | number | 否 | 树最大深度，默认 10 |
| `maxNodes` | number | 否 | 最大节点数，默认 200 |
| `extractField` | string | 否 | 返回数据的 key |

## 示例

```json
{ "actionCode": "GET_DOM", "selector": "#ppd", "mode": "full", "maxDepth": 3, "maxNodes": 100, "extractField": "dom", "tabKey": "tabKey666" }
```
