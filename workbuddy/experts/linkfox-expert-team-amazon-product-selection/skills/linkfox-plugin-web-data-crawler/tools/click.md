---
{
  "actionCode": "CLICK",
  "fields": {
    "selector": { "type": "string|string[]", "required": true }
  }
}
---

# CLICK

模拟点击页面元素。

## 参数

| 参数 | 类型 | 必须 | 说明 |
|---|---|---|---|
| `selector` | `string` 或 `string[]` | 是 | 数组时依次尝试，第一个命中的即被点击 |

## 示例

```json
{ "actionCode": "CLICK", "selector": "#productDescription_expander", "tabKey": "tabKey666" }
```
