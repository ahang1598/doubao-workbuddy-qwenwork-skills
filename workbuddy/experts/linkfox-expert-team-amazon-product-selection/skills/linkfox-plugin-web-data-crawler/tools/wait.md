---
{
  "actionCode": "WAIT",
  "fields": {
    "selector": { "type": "string|string[]", "required": false },
    "actionValue": { "type": "string|number", "required": false },
    "timeout": { "type": "number", "required": false }
  },
  "requires_one_of": [["selector", "actionValue"]]
}
---

# WAIT

等待 selector 命中或固定毫秒数。

## 参数

| 参数 | 类型 | 必须 | 说明 |
|---|---|---|---|
| `selector` | `string` 或 `string[]` | 条件 | 数组中任意一个命中即继续。与 `actionValue` 二选一 |
| `actionValue` | number 或 string | 条件 | 固定等待毫秒数（如 `1500` 或 `"1500"`）。与 `selector` 二选一 |
| `timeout` | number | 否 | selector 超时毫秒数，超时后不报错继续 |

## 示例

```json
{ "actionCode": "WAIT", "selector": "span#productTitle", "tabKey": "tabKey666" }
```
